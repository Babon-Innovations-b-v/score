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
