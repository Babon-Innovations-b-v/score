"""The compute adapter: the only way a paid node reaches the cloud, over the job contract tools/cloud already has.

    ticket = compute.clearance(runner, node, euros)  # refused unless the runner keys the node and the owner said yes
    compute.submit(runner, node, job_store, run, job, spec)   # tools/cloud/runtime/submit.write_job, after clearance

A node gets a key from the runner only when every earlier node it reads passed its gates and the owner accepted that
output (score.graph); the owner's yes to that very key's run is in the store (score.review spend), at an amount no
lower than the run's estimate (the spec's `euros`). Without all three, nothing is submitted: a run that skips the
runner cannot spend. The job carries its node and key, so the finish record and the job can be matched. The machine
path (tools/props/cloud) is reached the same way, through the engine adapter (score.adapters.engines), which asks
for clearance first.

Every place that spends (tools/props/cloud/batch.py's `rent`, tools/cloud/k8s/submitter.py's `submit` and
clusters/scaleway.py's `up`, tools/props/closeup/pro.py's `draw`, tools/props/scene/marble.py's `generate` and
`paint`) asks `require_cleared` first, so the old paid entry points (blender_cloud.py, detached.py, the runners,
demo.py, make_jobs.py, the close-up stage) refuse to spend unless they run inside a cleared run:

    with compute.spending(ticket):         # SCORE_SPEND_TICKET="<node> <key>" for this process and its children
        ...                                # anything here may rent
    compute.require_cleared("a batch")     # at a rent point: Refused unless that node and key carry the owner's yes

The owner's override, for a run outside the runner, is the same yes under the node `override`: he gives it from his
own terminal for a name of his choosing (the review command's spend, node `override`, key <name>, at his euros), and
the run carries SCORE_SPEND_TICKET="override <name>". The euros are checked where a node is cleared (`clearance`); a
rent point checks only that the yes exists, and the ledger's own ceilings still apply. A barrier, not a lock: an
agent can name a yes the owner gave earlier, and every yes names who gave it and when.
"""
import contextlib
import os
import pathlib
import sys

from score import graph
from score.store import Store

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "tools/cloud/runtime"))
import submit as job_contract  # noqa: E402

TICKET = "SCORE_SPEND_TICKET"
OVERRIDE = "override"


class Refused(Exception):
    """A paid run is refused: its node is blocked, or the owner has not said yes to this run."""


def clearance(runner, node, euros):
    """The node's ticket ({node, key, after, yes}) when its prerequisites passed and are accepted and the owner said
    yes to this run at no less than its estimate in euros; else Refused."""
    if euros is None:
        raise Refused(f"{node}: a paid run needs its estimate in euros before the owner's yes can clear it")
    try:
        ticket = runner.ticket(node)
    except graph.Blocked as block:
        raise Refused(f"{node} is blocked: {block}") from block
    yes = runner.store.spend_yes(node, ticket["key"])
    if yes is None:
        raise Refused(f"{node}: the owner has not said yes to this run ({ticket['key'][:12]})")
    if euros > yes["euros"]:
        raise Refused(f"{node}: the run is estimated at EUR {euros}, the owner said yes to EUR {yes['euros']}")
    return {**ticket, "yes": yes}


def submit(runner, node, job_store, run, job, spec):
    """Put a cleared node's job in the job store (the existing contract); the job's key. The spec carries the run's
    estimate as `euros`."""
    ticket = clearance(runner, node, spec.get("euros"))
    return job_contract.write_job(job_store, run, job, {**spec, "node": node, "node_key": ticket["key"]})


@contextlib.contextmanager
def spending(ticket):
    """Name a cleared ticket's run in this process and the processes it starts, for the rent points to find."""
    before = os.environ.get(TICKET)
    os.environ[TICKET] = f"{ticket['node']} {ticket['key']}"
    try:
        yield
    finally:
        if before is None:
            os.environ.pop(TICKET, None)
        else:
            os.environ[TICKET] = before


def require_cleared(what, store=None):
    """The owner's yes for the run SCORE_SPEND_TICKET names (a cleared node's key, or his override); Refused when the
    variable is missing or names no yes. `what` says what was about to be rented."""
    named = os.environ.get(TICKET, "").split()
    if len(named) != 2:
        raise Refused(f"{what}: nothing rents outside a cleared run. Run it through the runner (score.adapters "
                      f"compute or engines), or ask the owner for an override (his yes under the node {OVERRIDE}, "
                      f"named here as {TICKET}=\"{OVERRIDE} <name>\")")
    node, key = named
    yes = (store or Store.default()).spend_yes(node, key)
    if yes is None:
        raise Refused(f"{what}: {TICKET} names {node} {key[:12]}, which the owner has not said yes to")
    return yes
