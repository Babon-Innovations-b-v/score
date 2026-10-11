"""The compute adapter: the only way a paid node reaches the cloud, over the job contract tools/cloud already has.

    ticket = compute.clearance(runner, node, euros)  # refused unless the runner keys the node and the owner said yes
    compute.submit(runner, node, job_store, run, job, spec)   # tools/cloud/runtime/submit.write_job, after clearance

A node gets a key from the runner only when every earlier node it reads passed its gates and the owner accepted that
output (score.graph); the owner's yes to that very key's run is in the store (score.review spend), at an amount no
lower than the run's estimate (the spec's `euros`). Without all three, nothing is submitted: a run that skips the
runner cannot spend. The job carries its node and key, so the finish record and the job can be matched. The machine
path (tools/props/cloud) is reached the same way, through the engine adapter (score.adapters.engines), which asks
for clearance first.
"""
import pathlib
import sys

from score import graph

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "tools/cloud/runtime"))
import submit as job_contract  # noqa: E402


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
