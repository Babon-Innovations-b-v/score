"""The owner's accept and reject from a signed-in web user (the dashboard, score/dashboard), beside his terminal's.

    web.decide(store, node, output, "accept", by="joey", reason="", worse_reason=None)
    web.decide(store, node, output, "reject", by="joey", reason="the lamp floats")

The dashboard proves who the owner is by its own sign-in (the trusted proxy's single sign-on, or its owner account)
in place of the terminal check of `python -m score.review` (owner_at_terminal), and passes his user name as `by`.
`by` is never empty and never the runner's name: an accept by the runner skips the store's agent barrier. The store's
own barrier still refuses these writes in a process an agent started (Store.write_once), so a dashboard started from
an agent's shell records nothing. Waivers and spend yeses stay terminal-only.
"""
from score import review
from score.store import RUNNER

DECISIONS = ("accept", "reject")


def checked_by(by):
    """The owner's user name, refused when empty or the runner's."""
    name = (by or "").strip()
    if not name or name == RUNNER:
        raise review.Refused(f"a decision needs the signed-in owner's own name, not {by!r}")
    return name


def decide(store, node, output, decision, by, reason="", worse_reason=None):
    """Record the owner's accept or reject of one output of a node, by his signed-in name; what was written.
    review.Refused when the output may not be taken so (it did not pass, it is worse with no reason, a reject with no
    reason, it is not the accepted output)."""
    name = checked_by(by)
    if decision == "reject":
        return review.reject(store, node, output, name, reason)
    if decision == "accept":
        return review.accept(store, node, output, name, reason, worse_reason=worse_reason or None)
    raise review.Refused(f"a decision is one of {', '.join(DECISIONS)}, not {decision!r}")
