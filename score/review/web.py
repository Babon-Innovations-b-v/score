"""The owner's accept and reject from a signed-in web user (the dashboard, score/dashboard), beside his terminal's.

    web.decide(store, node, output, "accept", by="joey", reason="", worse_reason=None)
    web.decide(store, node, output, "reject", by="joey", reason="the lamp floats")
    web.stop(store, "world1", 412.5, "checkout 7: fix-sound, fix-film-cut", by="joey")   # his checkout's money yes

The dashboard proves who the owner is by its own sign-in (the trusted proxy's single sign-on, or its owner account)
in place of the terminal check of `python -m score.review` (owner_at_terminal), and passes his user name as `by`.
`by` is never empty and never the runner's name: an accept by the runner skips the store's agent barrier. The store's
own barrier still refuses these writes in a process an agent started (Store.write_once), so a dashboard started from
an agent's shell records nothing. Waivers and spend yeses stay terminal-only.

`stop` is his money yes from the cockpit's checkout: the signed-in owner on the trusted cockpit counts as the owner
at his terminal (`python -m score.review stop`, C22), and the line is written by the same guard.set_line, which
refuses in any process an agent started, so no agent can trigger it by any route through here.
"""
from score import graph, review
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


def books_now():
    """The books as they stand ({month, bill, ledger, google}), read for a world's first stop line only."""
    from score.adapters import compute
    return compute.books_now()


def stop(store, world, euros, reason, by, books=books_now):
    """Write the world's new stop line at `euros` by the signed-in owner's name, his reason with it; the record. A
    world's first line counts its spend from `books()`. review.Refused for an empty or the runner's name;
    PermissionError in a process an agent started (guard.set_line)."""
    from score.adapters.compute import guard
    name = checked_by(by)
    baseline = None if guard.current(store, world) else books()
    return guard.set_line(store, world, euros, reason, name, graph.now(), baseline)
