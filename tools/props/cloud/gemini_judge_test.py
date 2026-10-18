"""The Gemini judge asks with an answer restricted to the question's codes, reads the answer without the thinking,
writes a hung question as a reply with no verdict after at most two hangs, and asks the same question only once.

Run: python3 tools/props/cloud/gemini_judge_test.py
"""
import json
import pathlib
import sys
import tempfile
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import gemini_judge  # noqa: E402
import google_spend  # noqa: E402

# Every check writes its ledger lines and cached answers to a scratch folder, never the real ones.
SCRATCH = pathlib.Path(tempfile.mkdtemp())
google_spend.LEDGER, google_spend.CACHE = SCRATCH / "google-ledger.jsonl", SCRATCH / "cache"

QUESTION = "Which?\n- M1: Steel, grey\n- M2: Vinyl, brown\nChoose.\n\nAfter your thinking, answer with one JSON object"


def job():
    picture = pathlib.Path(tempfile.mkdtemp()) / "q.png"
    picture.write_bytes(b"\x89PNG")
    return {"name": "q", "text": QUESTION, "images": [str(picture)]}


def test_the_answer_is_one_of_the_question_codes_or_unknown():
    body = gemini_judge.request_body(job(), gemini_judge.models.api_record(gemini_judge.KIND))
    config = body["generationConfig"]
    assert config["responseSchema"]["properties"]["material"]["enum"] == ["M1", "M2", "unknown"]
    assert config["temperature"] == 0 and "thinkingConfig" not in config
    assert "After your thinking" not in body["contents"][0]["parts"][-1]["text"]


def test_the_reply_leaves_the_thinking_out():
    response = {"candidates": [{"content": {"parts": [{"text": "hmm", "thought": True},
                                                      {"text": '{"part": "leg", "material": "M1"}'}]}}]}
    assert gemini_judge.reply_text(response) == '{"part": "leg", "material": "M1"}'


def test_a_question_that_hangs_on_every_try_gets_no_verdict():
    def hang(request, timeout):
        asked.append(request)
        raise TimeoutError("read timed out")
    asked = []
    record = {**gemini_judge.models.api_record(gemini_judge.KIND), "tries": 5}
    gemini_judge.BACKOFF_SECONDS, backoff = 0, gemini_judge.BACKOFF_SECONDS
    original, urllib.request.urlopen = urllib.request.urlopen, hang
    try:
        text = gemini_judge.answer_one(job(), record, "key")
    finally:
        urllib.request.urlopen, gemini_judge.BACKOFF_SECONDS = original, backoff
    assert text.startswith("no verdict") and "{" not in text and "2 tries" in text and len(asked) == 2


def test_the_same_question_is_asked_once_and_priced():
    answer = {"candidates": [{"content": {"parts": [{"text": '{"part": "leg", "material": "M2"}'}]}}],
              "usageMetadata": {"promptTokenCount": 1300, "candidatesTokenCount": 20, "thoughtsTokenCount": 500}}
    sent = []
    original = google_spend.post
    google_spend.post = lambda model, body, key, timeout: sent.append(body) or answer
    try:
        record = gemini_judge.models.api_record(gemini_judge.KIND)
        first, again = (gemini_judge.answer_one(job(), record, "key") for _ in range(2))
    finally:
        google_spend.post = original
    assert first == again == '{"part": "leg", "material": "M2"}' and len(sent) == 1
    line = json.loads(google_spend.LEDGER.read_text().splitlines()[-1])
    assert line["caller"] == "gemini_judge" and line["euros"] > 0


def test_a_failed_request_is_asked_again_and_an_answer_is_not():
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        listing = folder / "questions.json"
        listing.write_text(json.dumps([{"name": name, "text": "", "images": []} for name in ("a", "b", "c")]))
        answers = folder / "answers"
        answers.mkdir()
        (answers / "a.txt").write_text('{"part": "leg", "material": "M1"}')
        (answers / "b.txt").write_text(f"{gemini_judge.FAILED} HTTP 429 on each of 5 tries")
        assert [job["name"] for job in gemini_judge.to_ask(listing, answers)] == ["b", "c"]


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[3] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
