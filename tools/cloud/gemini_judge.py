"""Ask the judge's question list of Google's Gemini API instead of rented cards: judge.py's interface and answers.

    python3 tools/cloud/gemini_judge.py <questions.json> <answers folder>

The model and its settings are the models adapter's record (score.adapters.models.api_record("gemini-judge")):
temperature 0 and a JSON answer whose "material" is one of the question's codes (M1, M2, ...) or "unknown". Each
reply is written whole as <answers folder>/<name>.txt, a question already answered there skipped, so
part_judge.answer_of and vote read it as they read the cards' replies. A question still unanswered after the record's
tries (a request that hangs past its timeout) is written as a reply with no verdict, which the judge's gate counts.
Its key is the secret `gemini-api-key`, read by name (secret_store.py), never written down. Refused outside a cleared
run (compute.require_cleared): every ask is paid, so each goes through google_spend: asked once (the same
pictures, question, model and settings read back from its cache) and priced on the Google ledger.
"""
import argparse
import base64
import concurrent.futures
import json
import pathlib
import re
import sys
import time
import urllib.error

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))

import google_spend  # noqa: E402
from score.adapters import compute, models  # noqa: E402

KIND = "gemini-judge"
KEY_SECRET = "gemini-api-key"
# The stored questions end by asking for thinking then a JSON object; that line is replaced by the schema's wording.
TAIL = "After your thinking, answer with one JSON object"
# A request the API refused or lost: its reply starts FAILED (no verdict), and to_ask asks it again. Measured on the
# surface test's 9,087 asks at 32 at once and 3 tries without waiting (2026-10-11): 446 replies HTTP 429, 204 HTTP 402,
# 43 timeouts, 7.6% with no verdict; between tries the asker now waits BACKOFF_SECONDS, doubling.
FAILED = "no verdict:"
BACKOFF_SECONDS = 5.0
# A request that hangs past its timeout is most likely still generated, and billed, on Google's side; a refusal (HTTP
# 429, 402, 5xx) is not. So a hang is asked again once, never for every try; the next run's to_ask asks it again.
TIMEOUT_TRIES = 2
ANSWER_LINE = ('Answer with one JSON object: {"part": what the outlined part is, in a few words, "material": one code '
               'from the list, or "unknown"}.')


# A box question (tools/props/scene/box_check.py's, a job with "answer": "box"): whether the box shows the thing, whether
# it is the main thing in it, and what the box is mostly drawn round.
BOX_SCHEMA = {"type": "OBJECT", "properties": {"shows": {"type": "BOOLEAN"}, "main": {"type": "BOOLEAN"},
                                               "what": {"type": "STRING"}},
              "required": ["shows", "main", "what"], "propertyOrdering": ["shows", "main", "what"]}
BOX_ANSWER_LINE = 'Answer with one JSON object: {"shows": true or false, "main": true or false, "what": a few words}.'
MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}


def codes_of(text):
    """The material codes a question lists ("- M1: ..." lines), in order."""
    return re.findall(r"^- (M\d+):", text, flags=re.M)


def request_body(job, record):
    """The generateContent request for one question: its pictures, its text and the enum-restricted answer (a box
    question's own: BOX_SCHEMA)."""
    pictures = [{"inline_data": {"mime_type": MIME.get(pathlib.Path(path).suffix.lower(), "image/png"),
                                 "data": base64.b64encode(pathlib.Path(path).read_bytes()).decode()}}
                for path in job["images"]]
    boxed = job.get("answer") == "box"
    schema = BOX_SCHEMA if boxed else {
        "type": "OBJECT", "properties": {"part": {"type": "STRING"},
                                         "material": {"type": "STRING", "enum": [*codes_of(job["text"]), "unknown"]}},
        "required": ["part", "material"], "propertyOrdering": ["part", "material"]}
    config = {"temperature": record["temperature"], "responseMimeType": "application/json", "responseSchema": schema}
    if record["thinking"] != "default":
        config["thinkingConfig"] = {"thinkingLevel": record["thinking"]}
    line = BOX_ANSWER_LINE if boxed else ANSWER_LINE
    return {"contents": [{"role": "user", "parts": [*pictures, {"text": job["text"].split(TAIL)[0] + line}]}],
            "generationConfig": config}


def reply_text(response):
    """The answer's text from a generateContent response (thought parts left out); empty when it gave none."""
    candidate = (response.get("candidates") or [{}])[0]
    return "".join(part.get("text", "") for part in candidate.get("content", {}).get("parts", [])
                   if not part.get("thought"))


def answer_one(job, record, key):
    """One question's reply text; a refused or lost request (HTTP 429 or 402 when the API is busy, a 5xx) is asked
    again after BACKOFF_SECONDS doubling, a timeout at most TIMEOUT_TRIES times; after that, a line starting FAILED,
    with no verdict. The same question (pictures, wording, answers, model, settings) is asked once: google_spend's
    cache answers it for every later line and rerun, and its cost goes on the Google ledger."""
    body = request_body(job, record)
    failure, attempt, timeouts = "", 0, 0
    while attempt < record["tries"] and timeouts < TIMEOUT_TRIES:
        if attempt:
            time.sleep(BACKOFF_SECONDS * 2 ** (attempt - 1))
        attempt += 1
        try:
            response = google_spend.generate(record["model"], body, key, compute.judge_timeout(),
                                             caller="gemini_judge", cache=True)
            return reply_text(response) or "the model gave no answer"
        except urllib.error.HTTPError as error:
            failure = f"HTTP {error.code}"
        except OSError as error:  # a timeout or a dropped connection: asked again
            failure = type(error).__name__
            timeouts += 1
    return f"{FAILED} {failure} on each of {attempt} tries"


def to_ask(path, answers):
    """The list's questions not yet answered in `answers`: no reply, or a request that failed (FAILED), asked again."""
    return [job for job in json.loads(pathlib.Path(path).read_text())
            if not (reply := answers / f"{job['name']}.txt").exists() or reply.read_text().startswith(FAILED)]


def ask(path, answers):
    """Answer the list's open questions into `answers`, the record's `parallel` at a time; how many were asked."""
    compute.require_cleared("Gemini judge asks")
    from secret_store import secret
    record = models.api_record(KIND)
    answers.mkdir(parents=True, exist_ok=True)
    jobs = to_ask(path, answers)
    key = secret(KEY_SECRET) if jobs else None
    with concurrent.futures.ThreadPoolExecutor(record["parallel"]) as pool:
        asked = {pool.submit(answer_one, job, record, key): job for job in jobs}
        for done in concurrent.futures.as_completed(asked):  # each reply written as it comes, not in list order
            (answers / f"{asked[done]['name']}.txt").write_text(done.result())
    return len(jobs)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("questions", type=pathlib.Path)
    parser.add_argument("answers", type=pathlib.Path)
    arguments = parser.parse_args()
    print(f"{ask(arguments.questions, arguments.answers)} questions asked of {models.api_record(KIND)['model']}")


if __name__ == "__main__":
    main()
