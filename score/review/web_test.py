"""The owner's decision from a signed-in web user: an accept or reject by his own name, never empty, never the runner's;
a failing output is refused, a reject needs a reason and a worse output needs his written reason.

Run: .venv/bin/python -m pytest -q score/review/web_test.py
"""
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "score/review"))

import review_test  # noqa: E402  (the toy tally stage and its runs)

from score import review  # noqa: E402
from score.review import web  # noqa: E402

NODE = "tally@hangar"


def refusal(call):
    try:
        call()
    except review.Refused as refused:
        return str(refused)
    raise AssertionError("taken")


def test_a_passing_output_is_accepted_by_the_signed_in_user():
    store, _, output = review_test.made(1)
    web.decide(store, NODE, output, "reject", by="joey", reason="looked again later")
    assert store.accepted(NODE) is None
    written = web.decide(store, NODE, output, "accept", by="joey", reason="it reads right after all")
    assert written["by"] == "joey" and store.accepted(NODE) == output


def test_by_empty_or_the_runner_is_refused():
    store, _, output = review_test.made(1)
    for by in ("", "  ", None, "runner"):
        assert "signed-in owner's own name" in refusal(lambda: web.decide(store, NODE, output, "accept", by=by))


def test_a_failing_output_is_refused():
    store, _, output = review_test.made(5)
    assert "answered fail" in refusal(lambda: web.decide(store, NODE, output, "accept", by="joey"))


def test_a_reject_needs_a_reason():
    store, _, output = review_test.made(1)
    assert "needs a reason" in refusal(lambda: web.decide(store, NODE, output, "reject", by="joey", reason=" "))
    written = web.decide(store, NODE, output, "reject", by="joey", reason="the lamp floats")
    assert written["by"] == "joey" and store.accepted(NODE) is None


def test_a_worse_output_needs_the_worse_reason():
    store, data, first = review_test.made(1)
    _, _, second = review_test.made(2, store, data)
    assert "worse than the accepted one" in refusal(lambda: web.decide(store, NODE, second, "accept", by="joey"))
    written = web.decide(store, NODE, second, "accept", by="joey", worse_reason="two faults are fine")
    assert written["worse_reason"] == "two faults are fine" and store.accepted(NODE) == second


def test_an_unknown_decision_is_refused():
    store, _, output = review_test.made(1)
    assert "one of accept, reject" in refusal(lambda: web.decide(store, NODE, output, "waive", by="joey"))


def test_the_signed_in_checkout_writes_the_worlds_stop_line_never_in_an_agents_process():
    """C22 from the cockpit: his checkout is his money yes; the line is the guard's own, a first line counts from the
    books given; an empty name or the runner's is refused, and an agent's process writes nothing."""
    import os
    from score.adapters.compute import guard
    from score.store import AGENT_MARKERS
    store, _, _ = review_test.made(1)
    books = {"month": "2026-10", "bill": 50.0, "ledger": 40.0, "google": 0.0}
    saved = {name: os.environ.pop(name) for name in AGENT_MARKERS if name in os.environ}
    try:
        assert "signed-in owner's own name" in refusal(
            lambda: web.stop(store, "toy", 9.0, "films", by="runner", books=lambda: books))
        line = web.stop(store, "toy", 9.0, "checkout 1: fix-sound", by="joey", books=lambda: books)
        assert line["by"] == "joey" and line["baseline"] == books and guard.current(store, "toy")["euros"] == 9.0
        raised = web.stop(store, "toy", 12.0, "checkout 2", by="joey", books=lambda: {})
        assert raised["before"] == 9.0 and raised["baseline"] == books
        os.environ[AGENT_MARKERS[0]] = "1"
        try:
            web.stop(store, "toy", 99.0, "an agent's", by="joey", books=lambda: books)
            raise AssertionError("an agent's process wrote a stop line")
        except PermissionError:
            pass
        assert guard.current(store, "toy")["euros"] == 12.0
    finally:
        os.environ.pop(AGENT_MARKERS[0], None)
        os.environ.update(saved)
