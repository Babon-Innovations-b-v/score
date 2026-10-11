"""The compute adapter: the only way a paid node reaches the cloud, over the job contract tools/cloud already has.

    ticket = compute.clearance(runner, node)        # refused unless the runner keys the node and the owner said yes
    compute.submit(runner, node, job_store, run, job, spec)   # tools/cloud/runtime/submit.write_job, after clearance

A node gets a key from the runner only when every earlier node it reads passed its gates and the owner accepted that
output (score.graph); the owner's yes to that very key's run is in the store (score.review spend). Without both,
nothing is submitted: a run that skips the runner cannot spend. The job carries its node and key, so the finish
record and the job can be matched. The machine path (tools/props/cloud) is reached the same way, through the
engine adapter (score.adapters.engines), which asks for clearance first.
"""
import pathlib
import sys

from score import graph

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "tools/cloud/runtime"))
import submit as job_contract  # noqa: E402


class Refused(Exception):
    """A paid run is refused: its node is blocked, or the owner has not said yes to this run."""


def clearance(runner, node):
    """The node's ticket ({node, key, after, yes}) when its prerequisites passed and are accepted and the owner said
    yes to this run; else Refused."""
    try:
        ticket = runner.ticket(node)
    except graph.Blocked as block:
        raise Refused(f"{node} is blocked: {block}") from block
    yes = runner.store.spend_yes(node, ticket["key"])
    if yes is None:
        raise Refused(f"{node}: the owner has not said yes to this run ({ticket['key'][:12]})")
    return {**ticket, "yes": yes}


def submit(runner, node, job_store, run, job, spec):
    """Put a cleared node's job in the job store (the existing contract); the job's key."""
    ticket = clearance(runner, node)
    return job_contract.write_job(job_store, run, job, {**spec, "node": node, "node_key": ticket["key"]})
