"""The compute adapter: the only way a paid node reaches the cloud, over the job contract tools/cloud already has.

    ticket = compute.clearance(runner, node, euros)  # refused unless the runner keys the node and the month has room
    compute.submit(runner, node, job_store, run, job, spec)   # tools/cloud/runtime/submit.write_job, after clearance

Clearance comes from the framework, not from a typed yes (the owner's answer of 2026-10-11: his picks are made, from
concept and style on everything runs automatically, no spend limit, spend logically). A node is cleared when the
runner keys it, which it does only when every earlier node it reads passed its gates (unknown blocks) and stands
accepted (score.graph), and when the month's ceiling (tools/props/cloud/ledger.py, MONTH_EUROS) has room for the
run's estimate (the spec's `euros`) over what the ledger holds for the month. The clearance is written to the store
(`clearances/<node>/<key>/`); without it nothing is submitted, so a run that skips the runner cannot spend. The job
carries its node and key, so the finish record and the job can be matched. The machine path (tools/props/cloud) is
reached the same way, through the engine adapter (score.adapters.engines), which asks for clearance first.

Every place that spends (tools/props/cloud/batch.py's `rent`, tools/cloud/k8s/submitter.py's `submit` and
clusters/scaleway.py's `up`, tools/props/closeup/pro.py's `draw`, tools/props/scene/marble.py's `generate` and
`paint`) asks `require_cleared` first, so the old paid entry points (blender_cloud.py, detached.py, the runners,
demo.py, make_jobs.py, the close-up stage) refuse to spend unless they run inside a cleared run:

    with compute.spending(ticket):         # SCORE_SPEND_TICKET="<node> <key>" for this process and its children
        ...                                # anything here may rent
    compute.require_cleared("a batch")     # at a rent point: Refused unless the runner cleared that node and key

Clearing is serialised, as lines run side by side (score.graph's drive): the month's check and the clearance are
made under one lock (`clearing.lock` beside the store), and every clearance holds a reservation of its estimate
(`reservations.json` beside it) until its run ends (`spending` releases it), or, for one handed to a job store, until
a batch's longest run (the ledger's BATCH_HOURS) has passed. The month's check counts the open reservations with the
ledger, which records a batch only once it is done, so two lines can never both spend the month's last euros.

The owner's override, an extra route he may use and never a requirement, is his yes for a run outside the runner:
he gives it from his own terminal for a name of his choosing (the review command's spend, node `override`, key
<name>, at his euros), and the run carries SCORE_SPEND_TICKET="override <name>". A rent point checks only that the
clearance or the yes exists; the ledger's own ceilings still apply there. A barrier, not a lock: an agent can name a
clearance given earlier, and every clearance names its node, key, estimate and time.
"""
import contextlib
import datetime
import json
import os
import pathlib
import sys

from score import graph
from score.store import RUNNER, Store, locked

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tools/cloud/runtime"))
import submit as job_contract  # noqa: E402

TICKET = "SCORE_SPEND_TICKET"
OVERRIDE = "override"


class Refused(Exception):
    """A paid run is refused: its node is blocked, or the month's ceiling has no room for it."""


def ledger():
    """tools/props/cloud/ledger.py, the month's ceiling and what the month has cost."""
    for folder in ("tools/props", "tools/props/cloud"):
        if str(REPO / folder) not in sys.path:
            sys.path.append(str(REPO / folder))  # appended: its modules must not shadow anyone else's
    import ledger as cloud_ledger
    return cloud_ledger


def month_refusal(euros, reserved=0.0):
    """Why a run estimated at `euros` would pass the month's ceiling, with `reserved` euros cleared for runs not yet
    in the ledger, or None when the month has room."""
    books = ledger()
    spent = books.month_total(books.this_month(), books.entries())
    if spent + reserved + euros > books.MONTH_EUROS:
        return (f"EUR {spent:.2f} spent this month and EUR {reserved:.2f} cleared for runs still going; EUR {euros} "
                f"more would pass the EUR {books.MONTH_EUROS:.0f} ceiling")
    return None


def clearing(reservations):
    """One clearing at a time across every process: the lock beside the reservations file."""
    return locked(reservations.with_name("clearing.lock"))


def open_reservations(reservations):
    """{clearance time: clearance} still open: not released, and younger than a batch's longest run."""
    found = json.loads(reservations.read_text()) if reservations.exists() else {}
    oldest = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=ledger().BATCH_HOURS)
    return {at: held for at, held in found.items() if datetime.datetime.fromisoformat(at) > oldest}


def keep_reservations(reservations, held):
    """Write the open reservations whole, so a reader never sees half a file."""
    partial = reservations.with_name(f"{reservations.name}.{os.getpid()}.partial")
    partial.write_text(json.dumps(held, indent=1))
    partial.replace(reservations)


def clearance(runner, node, euros):
    """Clear one paid run: the node's ticket ({node, key, after, clearance, reservations}) when the runner keys it (its
    inputs passed and stand accepted) and the month's ceiling has room for its estimate over the ledger and every open
    reservation; the clearance kept in the store and its estimate reserved, under the clearing lock. Else Refused."""
    if euros is None:
        raise Refused(f"{node}: a paid run needs its estimate in euros before the runner can clear it")
    try:
        ticket = runner.ticket(node)
    except graph.Blocked as block:
        raise Refused(f"{node} is blocked: {block}") from block
    reservations = runner.store.cache.parent / "reservations.json"
    with clearing(reservations):
        held = open_reservations(reservations)
        over = month_refusal(euros, sum(reserved["euros"] for reserved in held.values()))
        if over:
            raise Refused(f"{node}: {over}")
        cleared = {"node": node, "key": ticket["key"], "euros": euros, "by": RUNNER, "at": graph.now()}
        runner.store.write_clearance(node, ticket["key"], cleared)
        keep_reservations(reservations, {**held, cleared["at"]: cleared})
    return {**ticket, "clearance": cleared, "reservations": str(reservations)}


def release(ticket):
    """End a cleared run's reservation: its cost is in the ledger now, or it never rented."""
    reservations = pathlib.Path(ticket["reservations"])
    with clearing(reservations):
        held = open_reservations(reservations)
        held.pop(ticket["clearance"]["at"], None)
        keep_reservations(reservations, held)


def submit(runner, node, job_store, run, job, spec):
    """Put a cleared node's job in the job store (the existing contract); the job's key. The spec carries the run's
    estimate as `euros`."""
    ticket = clearance(runner, node, spec.get("euros"))
    return job_contract.write_job(job_store, run, job, {**spec, "node": node, "node_key": ticket["key"]})


@contextlib.contextmanager
def spending(ticket):
    """Name a cleared ticket's run in this process and the processes it starts, for the rent points to find; its
    reservation ends with the block."""
    before = os.environ.get(TICKET)
    os.environ[TICKET] = f"{ticket['node']} {ticket['key']}"
    try:
        yield
    finally:
        if "reservations" in ticket:
            release(ticket)
        if before is None:
            os.environ.pop(TICKET, None)
        else:
            os.environ[TICKET] = before


def require_cleared(what, store=None):
    """The runner's clearance (or the owner's override yes) for the run SCORE_SPEND_TICKET names; Refused when the
    variable is missing or names neither. `what` says what was about to be rented."""
    named = os.environ.get(TICKET, "").split()
    if len(named) != 2:
        raise Refused(f"{what}: nothing rents outside a cleared run. Run it through the runner (score.adapters "
                      f"compute or engines), or the owner's override (his yes under the node {OVERRIDE}, named "
                      f"here as {TICKET}=\"{OVERRIDE} <name>\")")
    node, key = named
    store = store or Store.default()
    found = store.clearances(node, key) or [store.spend_yes(node, key)]
    if found[-1] is None:
        raise Refused(f"{what}: {TICKET} names {node} {key[:12]}, which the runner did not clear")
    return found[-1]
