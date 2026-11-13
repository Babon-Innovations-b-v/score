"""gemini_judge.py's invariants: the answer is restricted to the question's own codes (plus `unknown`) at temperature
0, read without the model's thinking; an answer that is cut off or a question that hangs is written as a reply with
no verdict naming why (never a half JSON object, and a hang tried at most TIMEOUT_TRIES times); the same question is
asked once, priced on google_spend's ledger, and read back from its cache after; a question whose reply is no verdict
is asked again on the next run, one with an answer is not.

One run of questions, each row a different reply from the API (an answer, a cut-off one, a hang, never asked), is
asked through `answer_one` against a fake endpoint, written, asked again where it has a verdict, and listed by `to_ask`.

Break that turns it red: in `request_body` build the enum without the question's codes; in `answer_one` return the
answer's text when finishReason is not STOP; or in `to_ask` skip every question with an answer file.
"""
import json
import pathlib
import sys
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import gemini_judge  # noqa: E402
import google_spend  # noqa: E402

USAGE = {"promptTokenCount": 1300, "candidatesTokenCount": 20, "thoughtsTokenCount": 500}
ANSWER = '{"part": "leg", "material": "M2"}'
# What the endpoint does for a question: its reply (None: it hangs).
REPLIES = {
    "answered": {"candidates": [{"finishReason": "STOP", "content": {"parts": [
        {"text": "hmm", "thought": True}, {"text": ANSWER}]}}], "usageMetadata": USAGE},
    "cut": {"candidates": [{"finishReason": "MAX_TOKENS", "content": {"parts": [{"text": '{"part": "le'}]}}],
            "usageMetadata": USAGE},
    "hang": None,
}
# name, the codes its question lists, how the endpoint replies (None: never asked), what the reply must hold,
# how many times the endpoint was called (a hang at most TIMEOUT_TRIES of 5 tries), asked again by to_ask.
ROWS = [
    ("answered", ["M1", "M2"], "answered", ANSWER, 1, False),
    ("cut", ["M1", "M2", "M3"], "cut", "MAX_TOKENS", 1, True),
    ("hang", ["M4"], "hang", "TimeoutError", 2, True),
    ("never", ["M1"], None, None, 0, True),
]


def question(name, codes):
    lines = "".join(f"- {code}: finish {code}\n" for code in codes)
    return f"Which? ({name})\n{lines}Choose.\n\nAfter your thinking, answer with one JSON object"


class Reply:
    def __init__(self, response):
        self.response = response

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self):
        return json.dumps(self.response).encode()


def test_each_question_gets_a_code_or_a_no_verdict_and_only_no_verdicts_are_asked_again(tmp_path, monkeypatch):
    monkeypatch.setattr(google_spend, "LEDGER", tmp_path / "google-ledger.jsonl")
    monkeypatch.setattr(google_spend, "CACHE", tmp_path / "cache")
    monkeypatch.setattr(gemini_judge, "BACKOFF_SECONDS", 0)
    picture = tmp_path / "q.png"
    picture.write_bytes(b"\x89PNG")
    jobs = {name: {"name": name, "text": question(name, codes), "images": [str(picture)]}
            for name, codes, *_ in ROWS}
    sent = {name: [] for name, *_ in ROWS}

    def endpoint(request, timeout):
        body = json.loads(request.data)
        name = next(name for name in sent if f"({name})" in body["contents"][0]["parts"][-1]["text"])
        sent[name].append(body)
        if REPLIES[name] is None:
            raise TimeoutError("read timed out")
        return Reply(REPLIES[name])
    monkeypatch.setattr(urllib.request, "urlopen", endpoint)

    record = {**gemini_judge.models.api_record(gemini_judge.KIND), "tries": 5}
    answers = tmp_path / "answers"
    answers.mkdir()
    replies = {}
    for name, _, reply, _, _, _ in ROWS:
        if reply:
            replies[name] = gemini_judge.answer_one(jobs[name], record, "key")
            (answers / f"{name}.txt").write_text(replies[name])
    for name, _, _, _, _, again in ROWS:
        if name in replies and not again:  # an answered question asked again is read back, not sent
            assert gemini_judge.answer_one(jobs[name], record, "key") == replies[name], name
    listing = tmp_path / "questions.json"
    listing.write_text(json.dumps(list(jobs.values())))
    asked_again = {job["name"] for job in gemini_judge.to_ask(listing, answers)}

    for name, codes, reply, holds, calls, again in ROWS:
        assert len(sent[name]) == calls, (name, len(sent[name]))
        for body in sent[name]:
            config = body["generationConfig"]
            assert config["responseSchema"]["properties"]["material"]["enum"] == [*codes, "unknown"], name
            assert config["temperature"] == 0, name
        if reply == "answered":
            assert replies[name] == holds, name
        elif reply:
            assert replies[name].startswith(gemini_judge.FAILED) and holds in replies[name], (name, replies[name])
            assert "{" not in replies[name], (name, replies[name])
        assert (name in asked_again) == again, name
    lines = [json.loads(line) for line in google_spend.LEDGER.read_text().splitlines()]
    priced = [line for line in lines if line.get("euros")]
    replied = sum(calls for _, _, reply, _, calls, _ in ROWS if reply and REPLIES[reply] is not None)
    assert len(priced) == replied and all(line["caller"] == "gemini_judge" and line["euros"] > 0 for line in priced)
