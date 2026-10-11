"""Checks for the Google spend guard: the price of a response, the day's cap refusing, and the cache answering.

Run: python3 tools/props/cloud/google_spend_test.py
"""
import json
import os
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import google_spend  # noqa: E402

JUDGE = "gemini-3.1-pro-preview"
USAGE = {"promptTokenCount": 1000, "candidatesTokenCount": 100, "thoughtsTokenCount": 900}


def in_temporary_home():
    """Point the guard's ledger, cap file and cache at a fresh folder; the posts it would have sent."""
    folder = pathlib.Path(tempfile.mkdtemp())
    google_spend.CLOUD, google_spend.LEDGER = folder, folder / "google-ledger.jsonl"
    google_spend.CAP_FILE, google_spend.CACHE = folder / "google-day-euros.txt", folder / "cache"
    sent = []
    google_spend.post = lambda model, body, key, timeout: sent.append(body) or {"usageMetadata": USAGE}
    return sent


def test_prices_tokens_thinking_and_images():
    assert round(google_spend.dollars(JUDGE, USAGE), 6) == round((1000 * 2 + 1000 * 12) / 1e6, 6)
    picture = {"promptTokenCount": 500, "candidatesTokenCount": 1120,
               "candidatesTokensDetails": [{"modality": "IMAGE", "tokenCount": 1120}]}
    assert round(google_spend.dollars("gemini-3-pro-image", picture), 4) == round(0.001 + 0.1344, 4)


def test_cap_refuses_and_ledger_counts():
    sent = in_temporary_home()
    os.environ.pop("SCORE_GOOGLE_DAY_EUROS", None)
    google_spend.CAP_FILE.write_text("0.1")
    google_spend.generate(JUDGE, {"ask": 1}, "key", 5, caller="test")
    line = json.loads(google_spend.LEDGER.read_text())
    assert line["caller"] == "test" and line["thinking"] == 900 and line["day"] == google_spend.today()
    try:
        google_spend.generate(JUDGE, {"ask": 2}, "key", 5, caller="test")
    except google_spend.SpendCapReached as refusal:
        assert "day cap" in str(refusal)
    else:
        raise AssertionError("a call past the day's cap was sent")
    assert len(sent) == 1
    os.environ["SCORE_GOOGLE_DAY_EUROS"] = "100"
    try:
        assert google_spend.day_cap() == 100
    finally:
        del os.environ["SCORE_GOOGLE_DAY_EUROS"]


def test_cache_answers_the_same_question_once():
    sent = in_temporary_home()
    first = google_spend.generate(JUDGE, {"ask": "same"}, "key", 5, caller="test", cache=True)
    again = google_spend.generate(JUDGE, {"ask": "same"}, "key", 5, caller="test", cache=True)
    google_spend.generate(JUDGE, {"ask": "other"}, "key", 5, caller="test", cache=True)
    assert first == again and len(sent) == 2
    assert len(google_spend.LEDGER.read_text().splitlines()) == 2


def test_unpriced_model_refused():
    in_temporary_home()
    try:
        google_spend.generate("gemini-unknown", {}, "key", 5, caller="test")
    except google_spend.SpendCapReached as refusal:
        assert "no price" in str(refusal)
    else:
        raise AssertionError("an unpriced model was called")


if __name__ == "__main__":
    for name, check in list(globals().items()):
        if name.startswith("test_"):
            check()
    print("google_spend: all checks pass")
