"""Checks for the Google spend guard: the price of a response, its ledger lines (started before the call), the month
read back with unfinished calls, the cache answering, and no module calling Google another way.

Run: python3 tools/props/cloud/google_spend_test.py
"""
import json
import pathlib
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import google_spend  # noqa: E402

JUDGE = "gemini-3.1-pro-preview"
USAGE = {"promptTokenCount": 1000, "candidatesTokenCount": 100, "thoughtsTokenCount": 900}


def in_temporary_home():
    """Point the guard's ledger and cache at a fresh folder; the posts it would have sent."""
    folder = pathlib.Path(tempfile.mkdtemp())
    google_spend.LEDGER, google_spend.CACHE = folder / "google-ledger.jsonl", folder / "cache"
    sent = []
    google_spend.post = lambda model, body, key, timeout: sent.append(body) or {"usageMetadata": USAGE}
    return sent


def test_prices_tokens_thinking_and_images():
    assert round(google_spend.dollars(JUDGE, USAGE), 6) == round((1000 * 2 + 1000 * 12) / 1e6, 6)
    picture = {"promptTokenCount": 500, "candidatesTokenCount": 1120,
               "candidatesTokensDetails": [{"modality": "IMAGE", "tokenCount": 1120}]}
    assert round(google_spend.dollars("gemini-3-pro-image", picture), 4) == round(0.001 + 0.1344, 4)


def lines():
    return [json.loads(line) for line in google_spend.LEDGER.read_text().splitlines()]


def test_each_call_writes_a_started_line_then_its_priced_line():
    in_temporary_home()
    google_spend.generate(JUDGE, {"ask": 1}, "key", 5, caller="test")
    begun, line = lines()
    assert begun["state"] == "started" and begun["call"] == line["call"] and begun["estimate"] > 0
    assert line["state"] == "finished" and line["caller"] == "test" and line["thinking"] == 900
    assert line["day"] == google_spend.today() and line["euros"] == round(google_spend.dollars(JUDGE, USAGE), 6)


def test_the_started_line_is_written_before_the_call_is_sent():
    in_temporary_home()
    seen = []
    google_spend.post = lambda model, body, key, timeout: seen.append(lines()) or {"usageMetadata": USAGE}
    google_spend.generate(JUDGE, {"ask": 1}, "key", 5, caller="test")
    assert [line["state"] for line in seen[0]] == ["started"]


def test_a_lost_call_counts_in_the_month_at_its_estimate():
    in_temporary_home()

    def lost(model, body, key, timeout):
        raise TimeoutError("read timed out")
    google_spend.post = lost
    try:
        google_spend.generate("gemini-3-pro-image", {"ask": 1}, "key", 5, caller="test")
    except TimeoutError:
        pass
    else:
        raise AssertionError("the timeout must reach the caller")
    assert [line["state"] for line in lines()] == ["started", "failed"]
    month = google_spend.today()[:7]
    assert round(google_spend.month_euros(month), 6) == round(google_spend.estimate("gemini-3-pro-image"), 6)


def test_the_month_adds_finished_calls_and_calls_still_going():
    in_temporary_home()
    google_spend.generate(JUDGE, {"ask": 1}, "key", 5, caller="test")
    google_spend.started("gemini-3-pro-image", "killed")  # a process killed mid-call leaves only this line
    with google_spend.LEDGER.open("a") as ledger:  # a line from before started lines: no call id, no state
        ledger.write(json.dumps({"time": lines()[0]["time"], "model": JUDGE, "euros": 1.0}) + "\n")
    expected = google_spend.dollars(JUDGE, USAGE) + google_spend.estimate("gemini-3-pro-image") + 1.0
    assert round(google_spend.month_euros(google_spend.today()[:7]), 6) == round(expected, 6)
    assert google_spend.month_euros("1999-01") == 0


def test_the_service_tier_is_recorded_and_priced():
    in_temporary_home()
    google_spend.post = lambda model, body, key, timeout: {"usageMetadata": {**USAGE, "serviceTier": "priority"}}
    google_spend.generate(JUDGE, {"ask": 1}, "key", 5, caller="test")
    line = lines()[-1]
    assert line["tier"] == "priority"
    assert line["euros"] == round(google_spend.dollars(JUDGE, USAGE) * 1.8, 6)


def test_the_cache_key_of_a_request_stays_the_same():
    """Every paid Google row's cached answers are found by this key: a change to it re-buys every one of them."""
    assert google_spend.cache_path(JUDGE, {"ask": 1}).name == \
        "110ee814120323f0f0e78303db99cc0134533a55c517c3d995a51cc5cfb44f62.json"


def test_no_module_calls_google_another_way():
    """Only google_spend.py talks to generativelanguage.googleapis.com or loads Google's own clients."""
    repo = pathlib.Path(__file__).resolve().parents[3]
    tracked = subprocess.run(["git", "-C", str(repo), "ls-files", "*.py", "*.sh"], capture_output=True, text=True,
                             check=True).stdout.split()
    direct = re.compile(r"generativelanguage\.googleapis|x-goog-api-key|google\.genai|from google import genai|"
                        r"google\.generativeai|google\.cloud\.aiplatform|vertexai")
    allowed = {"tools/props/cloud/google_spend.py", "tools/props/cloud/google_spend_test.py",
               "tools/costs/paid_calls_test.py"}  # the paid-calls lint's fixtures name Google's hosts
    found = [path for path in tracked if not path.startswith("vendor/") and path not in allowed
             and (repo / path).is_file() and direct.search((repo / path).read_text(errors="replace"))]
    assert not found, f"call Google through google_spend.generate, not directly: {found}"


def test_cache_answers_the_same_question_once():
    sent = in_temporary_home()
    first = google_spend.generate(JUDGE, {"ask": "same"}, "key", 5, caller="test", cache=True)
    again = google_spend.generate(JUDGE, {"ask": "same"}, "key", 5, caller="test", cache=True)
    google_spend.generate(JUDGE, {"ask": "other"}, "key", 5, caller="test", cache=True)
    assert first == again and len(sent) == 2
    assert [line["state"] for line in lines()] == ["started", "finished"] * 2



def test_unpriced_model_recorded_without_a_price():
    in_temporary_home()
    google_spend.generate("gemini-unknown", {}, "key", 5, caller="test")
    assert lines()[-1]["euros"] is None


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[3] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, check in list(globals().items()):
        if name.startswith("test_"):
            check()
    print("google_spend: all checks pass")
