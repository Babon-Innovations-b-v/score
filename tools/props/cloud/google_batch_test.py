"""Checks for the Gemini batch client, with Google faked (no call leaves this PC): a request asked before is read back
free and the rest go into one job, each with a started line before the send; the answers are priced at the batch
tier and cached; a run cut off mid-wait picks up the same job and never sends it again; a job that fails and an
answer that is an error are failed lines and Unanswered; a send cut off is never sent again, a refusal is, and any
other HTTP status stops the caller.

Run: python3 tools/props/cloud/google_batch_test.py
"""
import io
import json
import pathlib
import sys
import tempfile
import urllib.error

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import google_batch  # noqa: E402
import google_spend  # noqa: E402

MODEL = "gemini-3.1-pro-preview"
USAGE = {"promptTokenCount": 1000, "candidatesTokenCount": 100, "thoughtsTokenCount": 900}


class FakeGoogle:
    """Google's batch endpoint faked: each send makes a job answering every request (`errors` as errors), done after
    `polls` polls in `state`; what was sent and polled is kept."""

    def __init__(self, state="JOB_STATE_SUCCEEDED", polls=1, errors=(), send_error=None):
        self.state, self.polls, self.errors, self.send_error = state, polls, set(errors), send_error
        self.sent, self.polled, self.ledger_at_send = [], [], []
        google_batch.send = self.send
        google_batch.status = self.status
        google_batch.time.sleep = lambda seconds: None

    def send(self, model, request, api_key):
        self.ledger_at_send.append(ledger())
        if self.send_error is not None:
            error, self.send_error = self.send_error, None
            raise error
        self.sent.append(request)
        return {"name": f"batches/{len(self.sent)}"}

    def status(self, name, api_key):
        self.polled.append(name)
        if len(self.polled) < self.polls:
            return {"name": name, "done": False}
        requests = self.sent[int(name.split("/")[1]) - 1]["batch"]["input_config"]["requests"]["requests"]
        answers = [{"metadata": item["metadata"], **({"error": {"code": 500}} if item["metadata"]["key"] in self.errors
                                                     else {"response": {"usageMetadata": USAGE, "asked": item["request"]}})}
                   for item in requests]
        return {"name": name, "done": True, "metadata": {"state": self.state},
                "response": {"inlinedResponses": {"inlinedResponses": answers}}}


def temporary_home():
    folder = pathlib.Path(tempfile.mkdtemp())
    google_spend.LEDGER, google_spend.CACHE = folder / "google-ledger.jsonl", folder / "cache"


def ledger():
    if not google_spend.LEDGER.exists():
        return []
    return [json.loads(line) for line in google_spend.LEDGER.read_text().splitlines()]


def test_one_job_for_the_new_requests_priced_at_the_batch_tier_and_cached():
    temporary_home()
    google_spend.keep(google_spend.cache_path(MODEL, {"ask": "old"}), {"kept": True})
    google = FakeGoogle(polls=3)
    found = google_batch.generate(MODEL, {"a": {"ask": "old"}, "b": {"ask": "b"}, "c": {"ask": "c"}}, "key", "test")
    assert found["a"] == {"kept": True} and found["b"]["asked"] == {"ask": "b"}, found
    assert len(google.sent) == 1 and len(google.polled) == 3
    keys = [item["metadata"]["key"] for item in google.sent[0]["batch"]["input_config"]["requests"]["requests"]]
    assert keys == ["b", "c"], keys
    assert [line["state"] for line in google.ledger_at_send[0]] == ["started", "started"]
    finished = [line for line in ledger() if line["state"] == "finished"]
    assert [line["tier"] for line in finished] == ["batch", "batch"], finished
    assert finished[0]["dollars"] == round(google_spend.dollars(MODEL, USAGE) * 0.5, 6), finished
    assert google_spend.cache_path(MODEL, {"ask": "c"}).exists()
    assert not list(google_spend.CACHE.glob("batch-*.json"))  # the job settled: nothing pending
    again = google_batch.generate(MODEL, {"b": {"ask": "b"}}, "key", "test")
    assert again["b"] == found["b"] and len(google.sent) == 1  # asked before: read back free


def test_a_run_cut_off_mid_wait_picks_up_the_same_job():
    temporary_home()
    google = FakeGoogle(polls=99)
    google_batch.POLL_FAULTS_MOST, kept = 2, google_batch.POLL_FAULTS_MOST
    calls = []

    def cut(name, api_key):
        calls.append(name)
        raise urllib.error.URLError("the line went down")
    google_batch.status = cut
    try:
        google_batch.generate(MODEL, {"a": {"ask": "a"}}, "key", "test")
    except urllib.error.URLError:
        pass
    else:
        raise AssertionError("a poll failing every time reaches the caller")
    finally:
        google_batch.POLL_FAULTS_MOST = kept
    assert len(calls) == 2 and list(google_spend.CACHE.glob("batch-*.json"))
    google.polls = 1
    google_batch.status = google.status
    found = google_batch.generate(MODEL, {"a": {"ask": "a"}}, "key", "test")
    assert "asked" in found["a"] and len(google.sent) == 1, (found, google.sent)
    assert [line["state"] for line in ledger()] == ["started", "finished"]


def test_a_failed_job_and_an_error_answer_are_unanswered_never_asked_again():
    temporary_home()
    google = FakeGoogle(state="JOB_STATE_EXPIRED")
    found = google_batch.generate(MODEL, {"a": {"ask": "a"}, "b": {"ask": "b"}}, "key", "test")
    assert all(isinstance(answer, google_batch.Unanswered) for answer in found.values()), found
    assert "EXPIRED" in str(found["a"]) and [line["state"] for line in ledger()].count("failed") == 2
    temporary_home()
    google = FakeGoogle(errors={"b"})
    found = google_batch.generate(MODEL, {"a": {"ask": "a"}, "b": {"ask": "b"}}, "key", "test")
    assert "asked" in found["a"] and isinstance(found["b"], google_batch.Unanswered), found
    assert not google_spend.cache_path(MODEL, {"ask": "b"}).exists()
    assert len(google.sent) == 1


def test_a_send_cut_off_is_not_sent_again_a_refusal_is_and_a_set_up_fault_stops():
    temporary_home()
    google = FakeGoogle(send_error=TimeoutError("The read operation timed out"))
    found = google_batch.generate(MODEL, {"a": {"ask": "a"}}, "key", "test")
    assert isinstance(found["a"], google_batch.Unanswered) and not google.sent, found
    assert [line["state"] for line in ledger()] == ["started", "failed"]
    temporary_home()
    google = FakeGoogle(send_error=urllib.error.HTTPError("url", 429, "busy", {}, io.BytesIO()))
    found = google_batch.generate(MODEL, {"a": {"ask": "a"}}, "key", "test")
    assert "asked" in found["a"] and len(google.sent) == 1, found
    temporary_home()
    FakeGoogle(send_error=urllib.error.HTTPError("url", 403, "forbidden", {}, io.BytesIO()))
    try:
        google_batch.generate(MODEL, {"a": {"ask": "a"}}, "key", "test")
    except urllib.error.HTTPError as error:
        assert error.code == 403
    else:
        raise AssertionError("a 403 is a set-up fault and stops the caller")
    assert [line["state"] for line in ledger()] == ["started", "failed"]


def test_a_500_or_504_at_the_send_is_sent_again_after_a_longer_wait():
    """Audit (2026-10-22): a 500 or 504 at the send was a set-up fault that stopped the caller."""
    waits = []
    for code in (500, 504):
        temporary_home()
        google = FakeGoogle(send_error=urllib.error.HTTPError("url", code, "failing", {}, io.BytesIO()))
        google_batch.time.sleep = waits.append
        found = google_batch.generate(MODEL, {"a": {"ask": "a"}}, "key", "test")
        assert "asked" in found["a"] and len(google.sent) == 1, (code, found)
    assert waits[0] == google_batch.REFUSED_WAIT, waits


def test_a_job_gone_at_a_poll_is_failed_at_once_and_never_polled_again():
    """Audit (2026-10-22): a job that answered 404 was polled POLL_FAULTS_MOST times, then raised, and its kept name
    made every later run wait on it again."""
    temporary_home()
    google = FakeGoogle()
    gone = []

    def missing(name, api_key):
        gone.append(name)
        raise urllib.error.HTTPError("url", 404, "not found", {}, io.BytesIO())
    google_batch.status = missing
    found = google_batch.generate(MODEL, {"a": {"ask": "a"}, "b": {"ask": "b"}}, "key", "test")
    assert len(gone) == 1 and len(google.sent) == 1, gone
    assert all(isinstance(answer, google_batch.Unanswered) and "404" in str(answer) for answer in found.values()), found
    assert [line["state"] for line in ledger()].count("failed") == 2
    assert not list(google_spend.CACHE.glob("batch-*.json"))  # the dead job's name is dropped


def test_requests_past_the_inline_limit_go_into_more_jobs():
    kept = google_batch.INLINE_MOST
    google_batch.INLINE_MOST = 30
    try:
        assert [sorted(chunk) for chunk in google_batch.chunks({"a": {"x": "1" * 20}, "b": {"x": "2" * 20}})] == [
            ["a"], ["b"]]
    finally:
        google_batch.INLINE_MOST = kept


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
