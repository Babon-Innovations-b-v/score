"""gemini_judge.py's invariants: the answer is restricted to the question's own codes (plus `unknown`) at temperature
0, read without the model's thinking; an answer that is cut off or a question that hangs is written as a reply with
no verdict naming why (never a half JSON object, and a hang tried at most TIMEOUT_TRIES times); the same question is
asked once, priced on google_spend's ledger, and read back from its cache after; a question whose reply is no verdict
is asked again on the next run, one with an answer is not.

Break that turns it red: in `request_body` build the enum without the question's codes; in `answer_one` return the
answer's text when finishReason is not STOP; or in `to_ask` skip every question with an answer file.
"""
import json
import pathlib
import sys
import urllib.request

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import gemini_judge  # noqa: E402
import google_spend  # noqa: E402

QUESTION = "Which?\n- M1: Steel, grey\n- M2: Vinyl, brown\nChoose.\n\nAfter your thinking, answer with one JSON object"
USAGE = {"promptTokenCount": 1300, "candidatesTokenCount": 20, "thoughtsTokenCount": 500}


@pytest.fixture
def job(tmp_path, monkeypatch):
    """One question about one picture, its ledger lines and cached answers in a scratch folder."""
    monkeypatch.setattr(google_spend, "LEDGER", tmp_path / "google-ledger.jsonl")
    monkeypatch.setattr(google_spend, "CACHE", tmp_path / "cache")
    picture = tmp_path / "q.png"
    picture.write_bytes(b"\x89PNG")
    return {"name": "q", "text": QUESTION, "images": [str(picture)]}


def record():
    return gemini_judge.models.api_record(gemini_judge.KIND)


def test_the_answer_is_one_of_the_question_codes_or_unknown(job):
    config = gemini_judge.request_body(job, record())["generationConfig"]
    assert config["responseSchema"]["properties"]["material"]["enum"] == ["M1", "M2", "unknown"]
    assert config["temperature"] == 0


def test_an_answer_cut_off_gets_no_verdict_naming_why(job, monkeypatch):
    cut = {"candidates": [{"finishReason": "MAX_TOKENS", "content": {"parts": [{"text": '{"part": "le'}]}}],
           "usageMetadata": USAGE}
    monkeypatch.setattr(google_spend, "post", lambda model, body, key, timeout: cut)
    text = gemini_judge.answer_one(job, record(), "key")
    assert text.startswith(gemini_judge.FAILED) and "MAX_TOKENS" in text and "{" not in text


def test_a_question_that_hangs_on_every_try_gets_no_verdict_after_two(job, monkeypatch):
    asked = []

    def hang(request, timeout):
        asked.append(request)
        raise TimeoutError("read timed out")
    monkeypatch.setattr(urllib.request, "urlopen", hang)
    monkeypatch.setattr(gemini_judge, "BACKOFF_SECONDS", 0)
    text = gemini_judge.answer_one(job, {**record(), "tries": 5}, "key")
    assert text.startswith(gemini_judge.FAILED) and "{" not in text and len(asked) == 2


def test_the_same_question_is_asked_once_priced_and_read_without_thinking(job, monkeypatch):
    parts = [{"text": "hmm", "thought": True}, {"text": '{"part": "leg", "material": "M2"}'}]
    answer = {"candidates": [{"finishReason": "STOP", "content": {"parts": parts}}], "usageMetadata": USAGE}
    sent = []
    monkeypatch.setattr(google_spend, "post", lambda model, body, key, timeout: sent.append(body) or answer)
    first, again = (gemini_judge.answer_one(job, record(), "key") for _ in range(2))
    assert first == again == '{"part": "leg", "material": "M2"}' and len(sent) == 1
    lines = [json.loads(line) for line in google_spend.LEDGER.read_text().splitlines()]
    finished = [line for line in lines if line.get("euros")]
    assert len(finished) == 1 and finished[0]["caller"] == "gemini_judge" and finished[0]["euros"] > 0


def test_a_no_verdict_is_asked_again_and_an_answer_is_not(tmp_path):
    listing = tmp_path / "questions.json"
    listing.write_text(json.dumps([{"name": name, "text": "", "images": []} for name in ("a", "b", "c")]))
    answers = tmp_path / "answers"
    answers.mkdir()
    (answers / "a.txt").write_text('{"part": "leg", "material": "M1"}')
    (answers / "b.txt").write_text(f"{gemini_judge.FAILED} HTTP 429 on each of 5 tries")
    assert [question["name"] for question in gemini_judge.to_ask(listing, answers)] == ["b", "c"]
