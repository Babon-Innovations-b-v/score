"""Finished jobs kept under their run's key, so a stopped or failed paid run's rerun pays only for the jobs it lacks
(owner, 2026-10-18: a stopped film render threw away its finished frames and the rerun bought them all again).

    waiting = kept.missing(jobs)    # each finished job of this key put back in place; the jobs still to run
    kept.keep(job)                  # after a job ended well: its outputs kept under the key

A job is a cloud runner's job ({"script", "args", "inputs", "outputs", ...}, blender_cloud.py's). It is kept under
`kept/<node>/<key>/<job>/` beside the store (SCORE_SPEND_STORE, else PROPS_HOME's store), the node and key from the
runner's ticket (SCORE_SPEND_TICKET), so only a rerun of the same node at the same key, the same inputs and code, ever
takes it. A make writes into a fresh folder each attempt (SCORE_MAKING, which the runner sets while a node makes), so
a job's name is its JSON with that folder written as `{making}`: the same job in the next attempt has the same name.
Its outputs are kept by their place under that folder, and a job counts as kept only once its `done` mark is written,
after every output, so a copy cut short is never taken. Outside a ticket, or for a job with an output outside the
making folder, nothing is kept and every job runs.

Imported only from the renting code (outside every stage's code key), so a change here moves no row.
"""
import hashlib
import json
import os
import pathlib
import shutil

TICKET = "SCORE_SPEND_TICKET"
STORE = "SCORE_SPEND_STORE"
MAKING = "SCORE_MAKING"
DONE = "done"


def making():
    """The folder the running node makes into, or None outside a make."""
    folder = os.environ.get(MAKING)
    return pathlib.Path(folder).resolve() if folder else None


def key_folder():
    """Where this run's finished jobs are kept, or None outside a runner's ticket."""
    named = os.environ.get(TICKET, "").split()
    if len(named) != 2:
        return None
    store = os.environ.get(STORE) or str(pathlib.Path(os.environ.get(
        "PROPS_HOME", pathlib.Path.home() / ".farm-factory-props")) / "store")
    node, key = named
    return pathlib.Path(store) / "kept" / node / key


def job_name(job, folder):
    """A job's name across attempts: the hash of its JSON with the making folder written as {making}."""
    text = json.dumps(job, sort_keys=True).replace(str(folder), "{making}")
    return hashlib.sha256(text.encode()).hexdigest()[:32]


def relative_outputs(job, folder):
    """The job's outputs as paths inside the making folder, or None when one lies outside it."""
    found = []
    for output in job.get("outputs", ()):
        path = pathlib.Path(output).resolve()
        if not path.is_relative_to(folder):
            return None
        found.append(path.relative_to(folder))
    return found


def copy(source, target):
    """A file or folder copied to `target`, any older copy there replaced."""
    if target.is_dir() and not target.is_symlink():
        shutil.rmtree(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        shutil.copytree(source, target)
    else:
        shutil.copy2(source, target)


def place_of(job):
    """(the job's keep folder, its outputs inside the making folder), or None when it cannot be kept."""
    folder, kept = making(), key_folder()
    if folder is None or kept is None:
        return None
    outputs = relative_outputs(job, folder)
    if outputs is None:
        return None
    return kept / job_name(job, folder), outputs


def keep(job):
    """Keep a job that ended well under its run's key, its `done` mark last; True when kept."""
    found = place_of(job)
    if found is None:
        return False
    place, outputs = found
    folder = making()
    if not all((folder / output).exists() for output in outputs):
        return False
    for output in outputs:
        copy(folder / output, place / "outputs" / output)
    (place / DONE).write_text(json.dumps(job, sort_keys=True))
    return True


def put_back(job):
    """Put a kept job's outputs back in place in this attempt's making folder; True when it was kept."""
    found = place_of(job)
    if found is None or not (found[0] / DONE).exists():
        return False
    place, outputs = found
    for output in outputs:
        copy(place / "outputs" / output, making() / output)
    return True


def missing(jobs):
    """Every finished job of this key put back in place; the jobs still to run, in their order."""
    return [job for job in jobs if not put_back(job)]
