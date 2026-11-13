"""google_batch.py's invariants, with Google faked (no call leaves this PC): a request asked before is read back free
and the rest go into one job (more only past the inline limit), each with a started line on google_spend's ledger
before the send; the answers are priced at the batch tier (half price) and cached, a cut-off answer priced with its
finish reason and never cached; a run cut off mid-wait picks up the same job and never sends it again; a job that
fails, is gone (404) or answers an error is failed lines and Unanswered, never asked again; a send cut off is never
sent again, a refusal (429) and a 500 or 504 are, after a wait, and any other HTTP status stops the caller (#18, #21;
audit of 2026-10-22). One table of worlds, each driven through `generate` and judged by the same checks.

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
FINISH = {"asked": "STOP", "cut": "MAX_TOKENS"}  # the finish reason a priced answer's ledger line carries


def http_error(code):
    return urllib.error.HTTPError("url", code, "said", {}, io.BytesIO())


def ledger():
    if not google_spend.LEDGER.exists():
        return []
    return [json.loads(line) for line in google_spend.LEDGER.read_text().splitlines()]


class FakeGoogle:
    """Google's batch endpoint faked: each send makes a job answering every request (`errors` as errors, `cut` cut
    off at the output limit), done after `polls` polls in `state`; `send_error` is raised by the first send and
    `poll_fault` by every poll; what was sent, polled and waited is kept."""

    def __init__(self, monkeypatch, state="JOB_STATE_SUCCEEDED", polls=1, errors=(), cut=(), send_error=None,
                 poll_fault=None):
        self.state, self.polls, self.errors, self.cut = state, polls, set(errors), set(cut)
        self.send_error, self.poll_fault = send_error, poll_fault
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
        if self.poll_fault is not None:
            raise self.poll_fault
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


def judged(found, asks, expected):
    """Each key's answer against its expected outcome: "kept" (what the cache holds for it), "asked" (answered and
    cached), "cut" (cut off at the output limit, never cached) or "unanswered:<why>" (Unanswered naming why)."""
    assert set(found) == set(expected)
    for key, outcome in expected.items():
        answer = found[key]
        if outcome == "kept":
            assert answer == json.loads(google_spend.cache_path(MODEL, asks[key]).read_text()), key
        elif outcome == "asked":
            assert answer["asked"] == asks[key], key
            assert google_spend.cache_path(MODEL, asks[key]).exists(), key
        elif outcome == "cut":
            with pytest.raises(google_spend.Unfinished, match="MAX_TOKENS"):
                google_spend.answer_text(answer)
            assert not google_spend.cache_path(MODEL, asks[key]).exists(), key
        else:
            assert isinstance(answer, google_batch.Unanswered) and outcome.split(":", 1)[1] in str(answer), key
            assert not google_spend.cache_path(MODEL, asks[key]).exists(), key


ABC = {"a": {"ask": "a"}, "b": {"ask": "b"}, "c": {"ask": "c"}}
ONE = {"a": {"ask": "a"}}
TWO = {"a": {"ask": "a"}, "b": {"ask": "b"}}
CASES = [
    pytest.param(dict(kept="a", google=dict(polls=3), asks={"a": {"ask": "old"}, "b": {"ask": "b"}, "c": {"ask": "c"}},
                      found={"a": "kept", "b": "asked", "c": "asked"}, jobs=[["b", "c"]], sends=1, polls=3,
                      ledger=["started", "started", "finished", "finished"],
                      again=dict(asks={"b": {"ask": "b"}}, found={"b": "kept"},
                                 ledger=["started", "started", "finished", "finished"])),
                 id="asked-before-read-back-free-the-rest-one-job-at-the-batch-tier"),
    pytest.param(dict(inline_most=30, asks={"a": {"x": "1" * 20}, "b": {"x": "2" * 20}},
                      found={"a": "asked", "b": "asked"}, jobs=[["a"], ["b"]], sends=2, polls=2,
                      ledger=["started", "finished", "started", "finished"]),
                 id="past-the-inline-limit-more-jobs"),
    pytest.param(dict(poll_faults_most=2, google=dict(poll_fault=urllib.error.URLError("the line went down")),
                      asks=ONE, raises=(urllib.error.URLError, None), pending=True, jobs=[["a"]], sends=1, polls=2,
                      ledger=["started"],
                      again=dict(asks=ONE, found={"a": "asked"}, ledger=["started", "finished"])),
                 id="cut-off-mid-wait-picks-up-the-same-job"),
    pytest.param(dict(google=dict(state="JOB_STATE_EXPIRED"), asks=TWO,
                      found={"a": "unanswered:EXPIRED", "b": "unanswered:EXPIRED"}, jobs=[["a", "b"]], sends=1,
                      polls=1, ledger=["started", "started", "failed", "failed"]),
                 id="failed-job-unanswered-never-asked-again"),
    pytest.param(dict(google=dict(errors={"b"}, cut={"c"}), asks=ABC,
                      found={"a": "asked", "b": "unanswered:error", "c": "cut"}, jobs=[["a", "b", "c"]], sends=1,
                      polls=1, ledger=["started", "started", "started", "finished", "failed", "finished"]),
                 id="error-answer-unanswered-cut-answer-priced-never-cached"),
    pytest.param(dict(google=dict(poll_fault=http_error(404)), asks=TWO,
                      found={"a": "unanswered:404", "b": "unanswered:404"}, jobs=[["a", "b"]], sends=1, polls=1,
                      ledger=["started", "started", "failed", "failed"]),
                 id="job-gone-at-a-poll-failed-at-once-never-polled-again"),
    pytest.param(dict(google=dict(send_error=TimeoutError("The read operation timed out")), asks=ONE,
                      found={"a": "unanswered:not sent again"}, jobs=[], sends=1, polls=0,
                      ledger=["started", "failed"]),
                 id="send-cut-off-not-sent-again"),
    *[pytest.param(dict(google=dict(send_error=http_error(code)), asks=ONE, found={"a": "asked"}, jobs=[["a"]],
                        sends=2, polls=1, ledger=["started", "finished"]),
                   id=f"refused-{code}-sent-again-after-a-wait") for code in (429, 500, 504)],
    pytest.param(dict(google=dict(send_error=http_error(403)), asks=ONE, raises=(urllib.error.HTTPError, 403),
                      pending=False, jobs=[], sends=1, polls=0, ledger=["started", "failed"]),
                 id="set-up-fault-at-the-send-stops-the-caller"),
]


@pytest.mark.parametrize("case", CASES)
def test_google_batch_sends_each_request_once(case, tmp_path, monkeypatch):
    monkeypatch.setattr(google_spend, "LEDGER", tmp_path / "google-ledger.jsonl")
    monkeypatch.setattr(google_spend, "CACHE", tmp_path / "cache")
    if "inline_most" in case:
        monkeypatch.setattr(google_batch, "INLINE_MOST", case["inline_most"])
    if "poll_faults_most" in case:
        monkeypatch.setattr(google_batch, "POLL_FAULTS_MOST", case["poll_faults_most"])
    if "kept" in case:
        google_spend.keep(google_spend.cache_path(MODEL, case["asks"][case["kept"]]), {"kept": True})
    google = FakeGoogle(monkeypatch, **case.get("google", {}))
    asks = case["asks"]
    if "raises" in case:
        kind, code = case["raises"]
        with pytest.raises(kind) as stopped:
            google_batch.generate(MODEL, asks, "key", "test")
        assert code is None or stopped.value.code == code
        assert bool(list(google_spend.CACHE.glob("batch-*.json"))) == case["pending"]
    else:
        found = google_batch.generate(MODEL, asks, "key", "test")
        judged(found, asks, case["found"])
        assert not list(google_spend.CACHE.glob("batch-*.json"))  # every job settled: nothing pending
    assert [[item["metadata"]["key"] for item in sent["batch"]["input_config"]["requests"]["requests"]]
            for sent in google.sent] == case["jobs"]
    assert len(google.ledger_at_send) == case["sends"] and len(google.polled) == case["polls"]
    first_chunk = len(case["jobs"][0]) if case["jobs"] else len(asks)
    assert [line["state"] for line in google.ledger_at_send[0]] == ["started"] * first_chunk  # started before send
    if case["sends"] > len(case["jobs"]) > 0:
        assert google.waits and google.waits[0] > 0  # a refusal is sent again only after a wait
    assert [line["state"] for line in ledger()] == case["ledger"]
    finished = [line for line in ledger() if line["state"] == "finished"]
    assert all(line["tier"] == "batch" and line["dollars"] == round(BATCH_DOLLARS, 6) for line in finished)
    expected_finish = [FINISH[outcome] for outcome in case.get("found", {}).values() if outcome in FINISH]
    assert sorted(line["finish"] for line in finished) == sorted(expected_finish)
    if "again" in case:
        again = case["again"]
        google.poll_fault, google.polls, sent_before = None, len(google.polled) + 1, len(google.sent)
        found_again = google_batch.generate(MODEL, again["asks"], "key", "test")
        judged(found_again, again["asks"], again["found"])
        assert len(google.sent) == sent_before  # read back or picked up, never sent again
        for key in found_again:
            assert key not in case.get("found", {}) or found_again[key] == found[key], key
        assert [line["state"] for line in ledger()] == again["ledger"]
