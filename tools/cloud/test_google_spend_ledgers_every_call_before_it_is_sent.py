"""google_spend.py's invariants (2026-10-11, after a EUR 257 day; Google billed EUR 549 while the ledger held 30): every
Gemini call writes a `started` line before it is sent and then a `finished` line priced at Google's published prices
(tokens, thinking, images, service tier) or a `failed` line; the month counts finished calls and calls still going or
lost at their estimate; the cache answers the same request once, under a key that never moves (a change re-buys every
cached answer); an answer cut off is priced, never cached, and read as its finish reason, never as text; and no other
tracked file calls Google another way (the last a wording check guarding the owner's rule that every Gemini call goes
through google_spend: tools/cloud/CLAUDE.md).

Break that turns it red: in `generate` write the started line after `post` returns; cache a response whose
finishReason is not STOP; or drop `thoughtsTokenCount` from `dollars`.
"""
import json
import pathlib
import re
import subprocess
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import google_spend  # noqa: E402

JUDGE = "gemini-3.1-pro-preview"  # USD 2 a million tokens in, 12 out (thinking billed as output)
USAGE = {"promptTokenCount": 1000, "candidatesTokenCount": 100, "thoughtsTokenCount": 900}
USAGE_DOLLARS = (1000 * 2 + 1000 * 12) / 1e6


def answered(text, finish="STOP"):
    """A generateContent response: a thought, then `text`, ended for `finish`."""
    return {"usageMetadata": USAGE, "candidates": [{"finishReason": finish, "content": {"parts": [
        {"text": "thinking it over", "thought": True}, {"text": text}]}}]}


@pytest.fixture
def sent(tmp_path, monkeypatch):
    """The guard's ledger and cache in the test's folder; the posts it would have sent, each answered "{}"."""
    monkeypatch.setattr(google_spend, "LEDGER", tmp_path / "google-ledger.jsonl")
    monkeypatch.setattr(google_spend, "CACHE", tmp_path / "cache")
    posts = []
    monkeypatch.setattr(google_spend, "post", lambda model, body, key, timeout: posts.append(body) or answered("{}"))
    return posts


def lines():
    return [json.loads(line) for line in google_spend.LEDGER.read_text().splitlines()]


def test_prices_tokens_thinking_and_images():
    assert round(google_spend.dollars(JUDGE, USAGE), 6) == round(USAGE_DOLLARS, 6)
    picture = {"promptTokenCount": 500, "candidatesTokenCount": 1120,
               "candidatesTokensDetails": [{"modality": "IMAGE", "tokenCount": 1120}]}
    # USD 2 a million tokens in, 120 a million image tokens out
    assert round(google_spend.dollars("gemini-3-pro-image", picture), 4) == round(0.001 + 0.1344, 4)


def test_each_call_writes_a_started_line_before_it_is_sent_then_its_priced_line(sent, monkeypatch):
    seen = []
    monkeypatch.setattr(google_spend, "post", lambda model, body, key, timeout: seen.append(lines()) or answered("{}"))
    google_spend.generate(JUDGE, {"ask": 1}, "key", 5, caller="test")
    assert [line["state"] for line in seen[0]] == ["started"]
    begun, line = lines()
    assert begun["call"] == line["call"] and begun["estimate"] > 0
    assert line["state"] == "finished" and line["caller"] == "test" and line["thinking"] == 900
    assert line["day"] == google_spend.today() and line["euros"] == round(USAGE_DOLLARS, 6)


def test_the_service_tier_is_recorded_and_priced(sent, monkeypatch):
    monkeypatch.setattr(google_spend, "post",
                        lambda model, body, key, timeout: {"usageMetadata": {**USAGE, "serviceTier": "priority"}})
    google_spend.generate(JUDGE, {"ask": 1}, "key", 5, caller="test")
    line = lines()[-1]
    assert line["tier"] == "priority" and line["euros"] == round(USAGE_DOLLARS * 1.8, 6)  # priority: 1.8 times


def test_a_lost_call_counts_in_the_month_at_its_estimate(sent, monkeypatch):
    def lost(model, body, key, timeout):
        raise TimeoutError("read timed out")
    monkeypatch.setattr(google_spend, "post", lost)
    with pytest.raises(TimeoutError):
        google_spend.generate("gemini-3-pro-image", {"ask": 1}, "key", 5, caller="test")
    begun, failed = lines()
    assert (begun["state"], failed["state"]) == ("started", "failed")
    assert round(google_spend.month_euros(google_spend.today()[:7]), 6) == round(begun["estimate"], 6)


def test_the_month_adds_finished_calls_and_calls_still_going(sent):
    google_spend.generate(JUDGE, {"ask": 1}, "key", 5, caller="test")
    google_spend.started("gemini-3-pro-image", "killed")  # a process killed mid-call leaves only this line
    with google_spend.LEDGER.open("a") as ledger:  # a line from before started lines: no call id, no state
        ledger.write(json.dumps({"time": lines()[0]["time"], "model": JUDGE, "euros": 1.0}) + "\n")
    killed = next(line for line in lines() if line.get("caller") == "killed")
    assert round(google_spend.month_euros(google_spend.today()[:7]), 6) == round(
        USAGE_DOLLARS + killed["estimate"] + 1.0, 6)
    assert google_spend.month_euros("1999-01") == 0


def test_the_cache_answers_the_same_request_once_under_a_key_that_never_moves(sent):
    first = google_spend.generate(JUDGE, {"ask": "same"}, "key", 5, caller="test", cache=True)
    again = google_spend.generate(JUDGE, {"ask": "same"}, "key", 5, caller="test", cache=True)
    google_spend.generate(JUDGE, {"ask": "other"}, "key", 5, caller="test", cache=True)
    assert first == again and len(sent) == 2
    assert [line["state"] for line in lines()] == ["started", "finished"] * 2
    assert google_spend.cache_path(JUDGE, {"ask": 1}).name == \
        "110ee814120323f0f0e78303db99cc0134533a55c517c3d995a51cc5cfb44f62.json"


def test_an_answer_cut_off_is_priced_never_cached_and_read_as_its_finish_reason(sent, monkeypatch):
    cut = answered('{"surfaces": [{"colours": [\n        {', "MAX_TOKENS")
    monkeypatch.setattr(google_spend, "post", lambda model, body, key, timeout: sent.append(body) or cut)
    for _ in range(2):
        response = google_spend.generate(JUDGE, {"ask": "long"}, "key", 5, caller="test", cache=True)
    assert len(sent) == 2 and not google_spend.cache_path(JUDGE, {"ask": "long"}).exists()
    assert lines()[-1]["finish"] == "MAX_TOKENS" and lines()[-1]["euros"] > 0
    with pytest.raises(google_spend.Unfinished, match="MAX_TOKENS") as unfinished:
        google_spend.answer_text(response)
    assert "thinking 900" in str(unfinished.value)


def test_a_finished_answer_is_its_text_without_thoughts_and_no_answer_is_unfinished():
    assert google_spend.answer_text(answered('{"a": 1}')) == '{"a": 1}'
    for response in ({"promptFeedback": {"blockReason": "SAFETY"}}, answered("{}", "SAFETY")):
        with pytest.raises(google_spend.Unfinished, match="SAFETY"):
            google_spend.answer_text(response)


def test_an_unpriced_model_is_recorded_without_a_price(sent):
    google_spend.generate("gemini-unknown", {}, "key", 5, caller="test")
    assert lines()[-1]["euros"] is None


def test_no_module_calls_google_another_way():
    """Wording check guarding the owner's rule (tools/cloud/CLAUDE.md): only google_spend.py and google_batch.py (on
    its ledger) talk to generativelanguage.googleapis.com or load Google's own clients."""
    repo = pathlib.Path(__file__).resolve().parents[2]
    tracked = subprocess.run(["git", "-C", str(repo), "ls-files", "*.py", "*.sh"], capture_output=True, text=True,
                             check=True).stdout.split()
    direct = re.compile(r"generativelanguage\.googleapis|x-goog-api-key|google\.genai|from google import genai|"
                        r"google\.generativeai|google\.cloud\.aiplatform|vertexai")
    allowed = {"tools/cloud/google_spend.py", "tools/cloud/google_batch.py",  # the batch client on its ledger
               pathlib.Path(__file__).resolve().relative_to(repo).as_posix(),
               "tools/costs/test_paid_calls_go_through_the_ledgered_clients.py",  # its fixtures name Google's hosts
               "score/conductor/logs.py"}  # the log scrubber names the key header to blank it, calls nothing
    found = [path for path in tracked if not path.startswith("vendor/") and path not in allowed
             and (repo / path).is_file() and direct.search((repo / path).read_text(errors="replace"))]
    assert not found, f"call Google through google_spend.generate, not directly: {found}"
