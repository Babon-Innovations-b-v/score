"""google_batch.py's invariants, with Google faked (no call leaves this PC): a request asked before is read back free
and the rest go into one job (more only past the inline limit), each with a started line on google_spend's ledger
before the send; the answers are priced at the batch tier (half price) and cached, a cut-off answer priced with its
finish reason and never cached; a run cut off mid-wait picks up the same job and never sends it again; a job that
fails, is gone (404) or answers an error is failed lines and Unanswered, never asked again; a send cut off is never
sent again, a refusal (429) and a 500 or 504 are, after a wait, and any other HTTP status stops the caller (#18, #21;
audit of 2026-10-22).

Break that turns it red: in `generate` send every request, cached or not; drop the batch tier from `settled`; or drop
the send's timeout from the cut-off case (it then reaches the caller instead of a failed line).
"""
import io
import json
import pathlib
import sys
import urllib.error

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import google_batch  # noqa: E402
import google_spend  # noqa: E402

MODEL = "gemini-3.1-pro-preview"  # USD 2 a million tokens in, 12 out (thinking billed as output)
# A batch answer names serviceTier "standard" in its usageMetadata (the real finish-route-list answer, 2026-10-22).
USAGE = {"promptTokenCount": 1000, "candidatesTokenCount": 100, "thoughtsTokenCount": 900, "serviceTier": "standard"}
BATCH_DOLLARS = (1000 * 2 + 1000 * 12) / 1e6 / 2


class FakeGoogle:
    """Google's batch endpoint faked: each send makes a job answering every request (`errors` as errors), done after
    `polls` polls in `state`; what was sent and polled is kept."""

    def __init__(self, monkeypatch, state="JOB_STATE_SUCCEEDED", polls=1, errors=(), send_error=None, cut=()):
        self.state, self.polls, self.errors, self.send_error = state, polls, set(errors), send_error
        self.cut = set(cut)  # keys answered cut off at the output limit
        self.sent, self.polled, self.ledger_at_send, self.waits = [], [], [], []
        monkeypatch.setattr(google_batch, "send", self.send)
        monkeypatch.setattr(google_batch, "status", self.status)
        monkeypatch.setattr(google_batch.time, "sleep", self.waits.append)

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
                                                     else {"response": self.answer(item)})}
                   for item in requests]
        return {"name": name, "done": True, "metadata": {"state": self.state},
                "response": {"inlinedResponses": {"inlinedResponses": answers}}}

    def answer(self, item):
        """A request's answer: finished, or cut off at the output limit mid-object for a key in `cut`."""
        finish = "MAX_TOKENS" if item["metadata"]["key"] in self.cut else "STOP"
        return {"usageMetadata": USAGE, "asked": item["request"],
                "candidates": [{"content": {"parts": [{"text": '{"a": ['}]}, "finishReason": finish}]}


@pytest.fixture
def fresh(tmp_path, monkeypatch):
    """A function that points google_spend's ledger and cache at a new empty folder."""
    count = []

    def home():
        count.append(1)
        folder = tmp_path / f"home-{len(count)}"
        monkeypatch.setattr(google_spend, "LEDGER", folder / "google-ledger.jsonl")
        monkeypatch.setattr(google_spend, "CACHE", folder / "cache")
    home()
    return home


def ledger():
    if not google_spend.LEDGER.exists():
        return []
    return [json.loads(line) for line in google_spend.LEDGER.read_text().splitlines()]


def http_error(code):
    return urllib.error.HTTPError("url", code, "said", {}, io.BytesIO())


def test_one_job_for_the_new_requests_priced_at_the_batch_tier_and_cached(fresh, monkeypatch):
    google_spend.keep(google_spend.cache_path(MODEL, {"ask": "old"}), {"kept": True})
    google = FakeGoogle(monkeypatch, polls=3)
    found = google_batch.generate(MODEL, {"a": {"ask": "old"}, "b": {"ask": "b"}, "c": {"ask": "c"}}, "key", "test")
    assert found["a"] == {"kept": True} and found["b"]["asked"] == {"ask": "b"}
    assert len(google.sent) == 1 and len(google.polled) == 3
    keys = [item["metadata"]["key"] for item in google.sent[0]["batch"]["input_config"]["requests"]["requests"]]
    assert keys == ["b", "c"]
    assert [line["state"] for line in google.ledger_at_send[0]] == ["started", "started"]
    finished = [line for line in ledger() if line["state"] == "finished"]
    assert [line["tier"] for line in finished] == ["batch", "batch"]
    assert finished[0]["dollars"] == round(BATCH_DOLLARS, 6)
    assert google_spend.cache_path(MODEL, {"ask": "c"}).exists()
    assert not list(google_spend.CACHE.glob("batch-*.json"))  # the job settled: nothing pending
    again = google_batch.generate(MODEL, {"b": {"ask": "b"}}, "key", "test")
    assert again["b"] == found["b"] and len(google.sent) == 1  # asked before: read back free


def test_requests_past_the_inline_limit_go_into_more_jobs(monkeypatch):
    monkeypatch.setattr(google_batch, "INLINE_MOST", 30)
    assert [sorted(chunk) for chunk in google_batch.chunks({"a": {"x": "1" * 20}, "b": {"x": "2" * 20}})] == [
        ["a"], ["b"]]


def test_a_run_cut_off_mid_wait_picks_up_the_same_job(fresh, monkeypatch):
    google = FakeGoogle(monkeypatch, polls=99)
    monkeypatch.setattr(google_batch, "POLL_FAULTS_MOST", 2)
    calls = []

    def cut(name, api_key):
        calls.append(name)
        raise urllib.error.URLError("the line went down")
    monkeypatch.setattr(google_batch, "status", cut)
    with pytest.raises(urllib.error.URLError):
        google_batch.generate(MODEL, {"a": {"ask": "a"}}, "key", "test")
    assert len(calls) == 2 and list(google_spend.CACHE.glob("batch-*.json"))
    google.polls = 1
    monkeypatch.setattr(google_batch, "status", google.status)
    found = google_batch.generate(MODEL, {"a": {"ask": "a"}}, "key", "test")
    assert "asked" in found["a"] and len(google.sent) == 1
    assert [line["state"] for line in ledger()] == ["started", "finished"]


def test_a_failed_job_and_an_error_answer_are_unanswered_never_asked_again(fresh, monkeypatch):
    FakeGoogle(monkeypatch, state="JOB_STATE_EXPIRED")
    found = google_batch.generate(MODEL, {"a": {"ask": "a"}, "b": {"ask": "b"}}, "key", "test")
    assert all(isinstance(answer, google_batch.Unanswered) for answer in found.values())
    assert "EXPIRED" in str(found["a"]) and [line["state"] for line in ledger()].count("failed") == 2
    fresh()
    google = FakeGoogle(monkeypatch, errors={"b"})
    found = google_batch.generate(MODEL, {"a": {"ask": "a"}, "b": {"ask": "b"}}, "key", "test")
    assert "asked" in found["a"] and isinstance(found["b"], google_batch.Unanswered)
    assert not google_spend.cache_path(MODEL, {"ask": "b"}).exists()
    assert len(google.sent) == 1


def test_a_job_gone_at_a_poll_is_failed_at_once_and_never_polled_again(fresh, monkeypatch):
    google = FakeGoogle(monkeypatch)
    gone = []

    def missing(name, api_key):
        gone.append(name)
        raise http_error(404)
    monkeypatch.setattr(google_batch, "status", missing)
    found = google_batch.generate(MODEL, {"a": {"ask": "a"}, "b": {"ask": "b"}}, "key", "test")
    assert len(gone) == 1 and len(google.sent) == 1
    assert all(isinstance(answer, google_batch.Unanswered) and "404" in str(answer) for answer in found.values())
    assert [line["state"] for line in ledger()].count("failed") == 2
    assert not list(google_spend.CACHE.glob("batch-*.json"))  # the dead job's name is dropped


def test_a_send_cut_off_is_not_sent_again_a_refusal_is_and_a_set_up_fault_stops(fresh, monkeypatch):
    google = FakeGoogle(monkeypatch, send_error=TimeoutError("The read operation timed out"))
    found = google_batch.generate(MODEL, {"a": {"ask": "a"}}, "key", "test")
    assert isinstance(found["a"], google_batch.Unanswered) and not google.sent
    assert [line["state"] for line in ledger()] == ["started", "failed"]
    for code in (429, 500, 504):
        fresh()
        google = FakeGoogle(monkeypatch, send_error=http_error(code))
        found = google_batch.generate(MODEL, {"a": {"ask": "a"}}, "key", "test")
        assert "asked" in found["a"] and len(google.sent) == 1, code
        assert google.waits and google.waits[0] > 0, code
    fresh()
    FakeGoogle(monkeypatch, send_error=http_error(403))
    with pytest.raises(urllib.error.HTTPError) as stopped:
        google_batch.generate(MODEL, {"a": {"ask": "a"}}, "key", "test")
    assert stopped.value.code == 403
    assert [line["state"] for line in ledger()] == ["started", "failed"]


def test_an_answer_cut_off_is_paid_with_its_finish_reason_and_never_cached(fresh, monkeypatch):
    FakeGoogle(monkeypatch, cut={"b"})
    found = google_batch.generate(MODEL, {"a": {"ask": "a"}, "b": {"ask": "b"}}, "key", "test")
    with pytest.raises(google_spend.Unfinished, match="MAX_TOKENS"):
        google_spend.answer_text(found["b"])
    assert not google_spend.cache_path(MODEL, {"ask": "b"}).exists()
    assert google_spend.cache_path(MODEL, {"ask": "a"}).exists()
    assert {line["finish"] for line in ledger() if line["state"] == "finished"} == {"STOP", "MAX_TOKENS"}
