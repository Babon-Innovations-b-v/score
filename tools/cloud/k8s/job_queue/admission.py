"""Admission for the box's job queue: which queued job goes first, which idle worker takes it, and whether a new worker
fits the room left. Pure functions over plain dicts, so the queue process and its test share them.

A queued job is a dict with `key` ("<run>/<job>"), `chain`, `band`, `priority` and `place`; a worker one with `id`,
`chain`, `band` and `last_place`. A chain is (image kind, image, code): a job goes only to a worker of its chain, so
an image pull, a node's set-up and an environment's set-up are paid once a chain, not once a job.
"""
import os
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

import submitter  # noqa: E402

CARD_BAND = "card"
# Runner workers by their requests, smallest first: a job takes the smallest band that holds its cores and memory.
BANDS = {"S": {"cpu": "4", "memory": "16Gi"}, "M": {"cpu": "8", "memory": "48Gi"},
         "L": {"cpu": "16", "memory": "120Gi"}}
BAND_ORDER = list(BANDS)
# SCORE_K8S_SHARES's names (gpu=24,cpu=400) as the quota's own resource names.
SHARE_NAMES = {"gpu": "requests.nvidia.com/gpu", "cpu": "requests.cpu", "memory": "requests.memory"}


def band_of(spec, cards):
    """A job's band: `card` for a card job, else the smallest processor band holding the spec's cpu and memory."""
    if cards:
        return CARD_BAND
    cores = submitter.quantity(spec.get("cpu") or 0)
    memory = submitter.quantity(spec.get("memory") or 0)
    for name in BAND_ORDER:
        if submitter.quantity(BANDS[name]["cpu"]) >= cores and submitter.quantity(BANDS[name]["memory"]) >= memory:
            return name
    return BAND_ORDER[-1]


def serves(worker_band, job_band):
    """Whether a worker of `worker_band` takes a job of `job_band`: its own band, or the next larger."""
    if worker_band == job_band:
        return True
    if CARD_BAND in (worker_band, job_band):
        return False
    return BAND_ORDER.index(worker_band) == BAND_ORDER.index(job_band) + 1


def ordered(queued, after):
    """The queued jobs in the order to serve them: higher priority first; within a priority, the places round robin,
    starting at the place after `after[priority]` (the last place served), each place's jobs in their own order."""
    by_priority = {}
    for job in queued:
        by_priority.setdefault(job["priority"], {}).setdefault(job["place"], []).append(job)
    order = []
    for priority in sorted(by_priority, reverse=True):
        places = sorted(by_priority[priority])
        last = after.get(priority)
        start = (places.index(last) + 1) % len(places) if last in places else 0
        lines = [list(by_priority[priority][place]) for place in places[start:] + places[:start]]
        while any(lines):
            for line in lines:
                if line:
                    order.append(line.pop(0))
    return order


def assignments(order, idle):
    """(job, worker) pairs: each job in `order` to an idle worker of its chain that serves its band, the one whose
    last job was at the same place when there is one (its inputs are in that node's cache). A worker takes one job."""
    free = list(idle)
    pairs = []
    for job in order:
        fitting = [worker for worker in free if worker["chain"] == job["chain"] and serves(worker["band"], job["band"])]
        if not fitting:
            continue
        same_place = [worker for worker in fitting if worker.get("last_place") == job["place"]]
        chosen = (same_place or fitting)[0]
        free.remove(chosen)
        pairs.append((job, chosen))
    return pairs


def shares(text=None):
    """This box's share of the namespace's quota, by the quota's resource names, from SCORE_K8S_SHARES
    ("gpu=24,cpu=400"); {} when unset (the quota alone)."""
    text = os.environ.get("SCORE_K8S_SHARES", "") if text is None else text
    found = {}
    for part in filter(None, (piece.strip() for piece in text.split(","))):
        name, _, value = part.partition("=")
        found[SHARE_NAMES.get(name.strip(), name.strip())] = submitter.quantity(value.strip())
    return found


def room_left(quota_room, share, own_use):
    """The room a new worker may take: the quota's room, and within this box's share what its own workers do not
    already ask (`own_use`, by the same names)."""
    room = dict(quota_room)
    for name, most in share.items():
        left = most - own_use.get(name, 0)
        room[name] = min(room.get(name, left), left)
    return room


def less(room, demand):
    """The room once a pod asking `demand` is in it."""
    return {name: left - demand.get(name, 0) for name, left in room.items()}
