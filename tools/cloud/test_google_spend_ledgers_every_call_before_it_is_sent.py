"""google_spend.py's invariants (2026-10-11, after a EUR 257 day; Google billed EUR 549 while the ledger held 30): every
Gemini call writes a `started` line before it is sent and then a `finished` line priced at Google's published prices
(tokens, thinking, images, service tier) or a `failed` line; the month counts finished calls and calls still going or
lost at their estimate; the cache answers the same request once, under a key that never moves (a change re-buys every
cached answer); an answer cut off is priced, never cached, and read as its finish reason, never as text; and no other
tracked file calls Google another way (the last a wording check guarding the owner's rule that every Gemini call goes
through google_spend: tools/cloud/CLAUDE.md).

One test: a day of calls (the CALLS rows) goes through `generate` into one ledger and cache, each row naming what it
is sent, what Google answers and what the ledger and the answer's text must then hold; the month is then read from
that ledger, the cache key checked, and the tracked files searched for another way to Google.

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
PICTURE = "gemini-3-pro-image"  # USD 2 a million tokens in, 120 a million image tokens out
USAGE = {"promptTokenCount": 1000, "candidatesTokenCount": 100, "thoughtsTokenCount": 900}
USAGE_DOLLARS = (1000 * 2 + 1000 * 12) / 1e6


def answered(text, finish="STOP"):
    """A generateContent response: a thought, then `text`, ended for `finish`."""
    return {"usageMetadata": USAGE, "candidates": [{"finishReason": finish, "content": {"parts": [
        {"text": "thinking it over", "thought": True}, {"text": text}]}}]}


CUT = answered('{"surfaces": [{"colours": [\n        {', "MAX_TOKENS")
LOST = TimeoutError("read timed out")

# (row, model, body, cache, Google's answer or the error sending raises, the call's ledger lines' states (none: answered
# from the cache), what its last line holds, its answer's text or the Unfinished message it raises)
CALLS = [
    ("asked", JUDGE, {"ask": "same"}, True, answered("{}"), ["started", "finished"],
     {"euros": round(USAGE_DOLLARS, 6), "thinking": 900, "finish": "STOP", "tier": None}, "{}"),
    ("asked-again-is-cached", JUDGE, {"ask": "same"}, True, None, [], {}, "{}"),
    ("another-request", JUDGE, {"ask": "other"}, True, answered("{}"), ["started", "finished"],
     {"euros": round(USAGE_DOLLARS, 6)}, "{}"),
    ("priority-tier", JUDGE, {"ask": "priority"}, False, {"usageMetadata": {**USAGE, "serviceTier": "priority"}},
     ["started", "finished"], {"tier": "priority", "euros": round(USAGE_DOLLARS * 1.8, 6)},  # priority: 1.8 times
     "no finish reason"),
    ("cut-off", JUDGE, {"ask": "long"}, True, CUT, ["started", "finished"],
     {"finish": "MAX_TOKENS", "euros": round(USAGE_DOLLARS, 6)}, "MAX_TOKENS.*thinking 900"),
    ("cut-off-asked-again", JUDGE, {"ask": "long"}, True, CUT, ["started", "finished"],
     {"finish": "MAX_TOKENS", "euros": round(USAGE_DOLLARS, 6)}, "MAX_TOKENS.*thinking 900"),
    ("blocked-prompt", JUDGE, {"ask": "blocked"}, True, {"promptFeedback": {"blockReason": "SAFETY"}},
     ["started", "finished"], {"finish": "no finish reason (prompt SAFETY)", "euros": 0.0}, "SAFETY"),
    ("safety-stop", JUDGE, {"ask": "unsafe"}, False, answered("{}", "SAFETY"), ["started", "finished"],
     {"finish": "SAFETY", "euros": round(USAGE_DOLLARS, 6)}, "SAFETY"),
    ("finished-with-thoughts", JUDGE, {"ask": "text"}, False, answered('{"a": 1}'), ["started", "finished"],
     {"finish": "STOP"}, '{"a": 1}'),
    ("lost", PICTURE, {"ask": 1}, False, LOST, ["started", "failed"], {"error": repr(LOST)}, None),
    ("unpriced-model", "gemini-unknown", {}, False, answered("{}"), ["started", "finished"], {"euros": None}, "{}"),
]
TEXTS = {'{}', '{"a": 1}'}
# month: finished at price, the unpriced at its estimate (0.15), the lost and the killed started at their estimates
# (0.15 each), a line from before started lines at its euros
MONTH = USAGE_DOLLARS * 6 + USAGE_DOLLARS * 1.8 + 0.15 * 3 + 1.0

# (model, usageMetadata, USD, digits compared)
PRICED = [
    (JUDGE, USAGE, USAGE_DOLLARS, 6),
    (PICTURE, {"promptTokenCount": 500, "candidatesTokenCount": 1120,
               "candidatesTokensDetails": [{"modality": "IMAGE", "tokenCount": 1120}]}, 0.001 + 0.1344, 4),
]


def lines():
    return [json.loads(line) for line in google_spend.LEDGER.read_text().splitlines()] \
        if google_spend.LEDGER.exists() else []


def test_google_spend_ledgers_every_call_before_it_is_sent(tmp_path, monkeypatch):
    monkeypatch.setattr(google_spend, "LEDGER", tmp_path / "google-ledger.jsonl")
    monkeypatch.setattr(google_spend, "CACHE", tmp_path / "cache")
    replies = {}
    at_send = []

    def post(model, body, key, timeout):
        at_send.append(lines())
        reply = replies[json.dumps([model, body], sort_keys=True)]
        if isinstance(reply, BaseException):
            raise reply
        return reply

    monkeypatch.setattr(google_spend, "post", post)
    for model, usage, usd, digits in PRICED:
        assert round(google_spend.dollars(model, usage), digits) == round(usd, digits), model

    returned = {}
    for row, model, body, cache, reply, states, last, text in CALLS:
        replies[json.dumps([model, body], sort_keys=True)] = reply
        before, sends = lines(), len(at_send)
        if isinstance(reply, BaseException):
            with pytest.raises(type(reply)):
                google_spend.generate(model, body, "key", 5, caller=row, cache=cache)
        else:
            returned[row] = google_spend.generate(model, body, "key", 5, caller=row, cache=cache)
        new = lines()[len(before):]
        assert [line["state"] for line in new] == states, row
        assert len(at_send) - sends == (1 if states else 0), f"{row}: sent {len(at_send) - sends} times"
        if not states:
            continue
        begun, done = new
        assert at_send[-1] == before + [begun], f"{row}: the started line is not alone on the ledger when sent"
        assert begun["call"] == done["call"] and begun["estimate"] > 0, row
        assert {**done, **last} == done and done["caller"] == row and done["day"] == google_spend.today(), row
        if reply is not None and cache:
            assert google_spend.cache_path(model, body).exists() == (text in TEXTS), f"{row}: cached wrongly"
        if row in returned and text not in TEXTS:
            with pytest.raises(google_spend.Unfinished, match=text):
                google_spend.answer_text(returned[row])
        elif row in returned:
            assert google_spend.answer_text(returned[row]) == text, row
    assert returned["asked-again-is-cached"] == returned["asked"]

    google_spend.started(PICTURE, "killed")  # a process killed mid-call leaves only this line
    with google_spend.LEDGER.open("a") as ledger:  # a line from before started lines: no call id, no state
        ledger.write(json.dumps({"time": lines()[0]["time"], "model": JUDGE, "euros": 1.0}) + "\n")
    assert round(google_spend.month_euros(google_spend.today()[:7]), 6) == round(MONTH, 6)
    assert google_spend.month_euros("1999-01") == 0
    assert google_spend.cache_path(JUDGE, {"ask": 1}).name == \
        "110ee814120323f0f0e78303db99cc0134533a55c517c3d995a51cc5cfb44f62.json"

    # wording check guarding the owner's rule (tools/cloud/CLAUDE.md): only google_spend.py and google_batch.py (on
    # its ledger) talk to generativelanguage.googleapis.com or load Google's own clients
    repo = pathlib.Path(__file__).resolve().parents[2]
    tracked = subprocess.run(["git", "-C", str(repo), "ls-files", "*.py", "*.sh"], capture_output=True, text=True,
                             check=True).stdout.split()
    direct = re.compile(r"generativelanguage\.googleapis|x-goog-api-key|google\.genai|from google import genai|"
                        r"google\.generativeai|google\.cloud\.aiplatform|vertexai")
    allowed = {"tools/cloud/google_spend.py", "tools/cloud/google_batch.py",  # the batch client on its ledger
               pathlib.Path(__file__).resolve().relative_to(repo).as_posix(),
               "tools/costs/test_every_euro_is_ledgered_measured_and_adds_up_to_the_bill.py",  # its fixtures name Google's hosts
               "score/conductor/logs.py"}  # the log scrubber names the key header to blank it, calls nothing
    found = [path for path in tracked if not path.startswith("vendor/") and path not in allowed
             and (repo / path).is_file() and direct.search((repo / path).read_text(errors="replace"))]
    assert not found, f"call Google through google_spend.generate, not directly: {found}"
