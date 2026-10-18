"""Nothing advances unseen (owner, 2026-10-18): which step outputs the owner has looked at and advanced, and which
paid steps of a plan stay blocked because a step they read has not been advanced by him.

The marks live in the dashboard's own database and are written only from the owner's signed-in session (never in a
server an agent started). The gate holds the dashboard's launches; the runner itself does not read it (v1).
"""
from django.conf import settings

from score.dashboard.pages.models import Seen

NOT_SEEN, SEEN, ADVANCED = "not seen by owner", "seen, not advanced", "advanced"


def mark(node, output):
    """The owner's mark on one output: NOT_SEEN, SEEN or ADVANCED (with when)."""
    if not output:
        return None
    found = list(Seen.objects.filter(node=node, output=output, user=settings.SCORE_OWNER or "-"))
    advanced = [item for item in found if item.advanced]
    if advanced:
        return f"{ADVANCED} {advanced[0].at:%Y-%m-%d %H:%M}"
    return f"{SEEN} {found[0].at:%Y-%m-%d %H:%M}" if found else NOT_SEEN


def marks(nodes_outputs):
    """{node: mark} for many (node, output) pairs in one query."""
    owner = settings.SCORE_OWNER or "-"
    pairs = {(node, output) for node, output in nodes_outputs if output}
    found = {}
    for item in Seen.objects.filter(user=owner, output__in={output for _, output in pairs}):
        if (item.node, item.output) in pairs:
            best = found.get(item.node)
            if best is None or (item.advanced and not best.advanced):
                found[item.node] = item
    return {node: (f"{ADVANCED} {found[node].at:%Y-%m-%d}" if found[node].advanced else SEEN) if node in found
            else NOT_SEEN for node, output in nodes_outputs if output}


def looked(user, node, output):
    """Record that the owner opened the page of an output (once per output)."""
    if output and not Seen.objects.filter(node=node, output=output, user=user).exists():
        Seen.objects.create(node=node, output=output, user=user, advanced=False)


def advance(user, node, output):
    """Record the owner's advance of an output: the paid steps reading it may be launched."""
    return Seen.objects.create(node=node, output=output, user=user, advanced=True)


def advanced(node, output):
    return bool(output) and Seen.objects.filter(node=node, output=output, user=settings.SCORE_OWNER or "-",
                                                advanced=True).exists()


def unseen_reads(buys, reads_of, accepted_of):
    """[(paid node, read node)] of every paid node in `buys` whose read node's accepted output the owner has not
    advanced. `reads_of(node)` lists the nodes a node reads; `accepted_of(node)` its accepted output or None (a read
    with nothing accepted blocks the runner already, so it is left to it)."""
    found = []
    for buy in buys:
        for read in reads_of(buy["node"]):
            output = accepted_of(read)
            if output and not advanced(read, output):
                found.append((buy["node"], read))
    return found
