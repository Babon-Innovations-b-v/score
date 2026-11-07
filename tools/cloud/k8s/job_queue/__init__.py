"""The box's job queue, its client side: a run's jobs handed to the one queue process of this box, which runs them on
warm workers of their image (`__main__.py`), and the wait for them.

    enqueue(run, kind, image, classes, specs)   # inbox/<run>.json, written whole
    wait(run)                                   # until state/<run>.json says the run is over; Stale when the queue is
    fresh()                                     # whether the queue's beat is newer than QUEUE_STALE_SECONDS
    cancel(run)                                 # cancel/<run>: a run its client took back, never assigned again
    spent()                                     # the box's euros so far as the queue counts them (money.json)
    start()                                     # start the queue process when it is not fresh (detached)

The queue's control files are small and live under `$PROPS_HOME/cloud/queue/`: `beat` (touched every tick), `lock`
(one queue a box), `inbox/`, `state/`, `cancel/`, `expected/<drive pid>.json` and the money figure. Nothing else is staged on
the conductor: the jobs' inputs and outputs are in the job store. A run's `priority` and `place` come from
SCORE_QUEUE_PRIORITY and SCORE_QUEUE_PLACE, which the drive sets for each node; environment variables are in no key.
"""
import json
import os
import pathlib
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import manifests  # noqa: E402
import submitter  # noqa: E402
from paths import HOME  # noqa: E402  (submitter puts tools/props on the path)

QUEUE = HOME / "cloud" / "queue"
QUEUE_STALE_SECONDS = 60
QUEUE_TAKEOVER_SECONDS = 180  # a waiting client whose queue is this stale takes its run back (S6: adopt or local)
POLL_SECONDS = 5


class Stale(RuntimeError):
    """The queue's beat stopped while a client waited on it."""


def root_of(root=None):
    return pathlib.Path(root) if root else QUEUE


def write_whole(path, value):
    """Write JSON to `path` whole: a partial file, then a rename, so a reader never sees half of it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(f".{path.name}.{os.getpid()}.partial")
    partial.write_text(json.dumps(value, indent=1, sort_keys=True))
    partial.replace(path)


def read_json(path):
    """A control file's JSON, or None while it is missing."""
    try:
        return json.loads(pathlib.Path(path).read_text())
    except FileNotFoundError:
        return None


def fresh(root=None, now=None):
    """Whether the queue process is alive: its beat is newer than QUEUE_STALE_SECONDS."""
    beat = root_of(root) / "beat"
    try:
        age = (now or time.time()) - beat.stat().st_mtime
    except FileNotFoundError:
        return False
    return age < QUEUE_STALE_SECONDS


def start(root=None):
    """Start this box's queue process, detached, when it is not fresh; True when one was started. Two clients that
    both start one leave one running: the process takes the queue's lock or exits."""
    if fresh(root):
        return False
    folder = root_of(root)
    folder.mkdir(parents=True, exist_ok=True)
    log = pathlib.Path("/tmp/score-detached") / f"queue-{time.strftime('%Y%m%d-%H%M%S')}.log"
    command = [sys.executable, str(HERE.parents[1] / "detached.py"), "--log", str(log), "--",
               sys.executable, str(HERE / "__main__.py"), "--root", str(folder)]
    subprocess.Popen(command, start_new_session=True, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL)
    return True


def enqueue(run, kind, image, classes, specs, stop_line=None, who=None, root=None):
    """Hand a run's jobs ({job id: job.json}) to the queue: `image` is the digest its workers run, `classes` the
    kind's classes in order, `stop_line` the euros this box's nodes may reach. The inbox file is written whole, and
    only for a cleared run (compute.require_cleared raises Refused): the queue rents the run's nodes for it."""
    submitter.compute.require_cleared(f"run {run} on the box's queue")
    entry = {"run": run, "kind": kind, "image": image, "classes": list(classes), "specs": specs,
             "priority": int(os.environ.get("SCORE_QUEUE_PRIORITY") or 0),
             "place": os.environ.get("SCORE_QUEUE_PLACE") or "", "box": manifests.box(), "who": who,
             "stop_line": stop_line, "at": time.time()}
    write_whole(root_of(root) / "inbox" / f"{run}.json", entry)
    return entry


def cancel(run, root=None):
    """Take a run back from the queue (its client adopts it, cluster_jobs.through_queue): `cancel/<run>`, which the
    queue reads before its inbox, so a queue that comes back drops the run and assigns none of its jobs again."""
    path = root_of(root) / "cancel" / run
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()


def spent(root=None):
    """The box's euros so far as the queue counts them (its money.json; 0 before its first tick), the base of a run's
    stop line."""
    return float((read_json(root_of(root) / "money.json") or {}).get("euros", 0.0))


def wait(run, root=None, poll=POLL_SECONDS, clock=time.time, sleep=time.sleep):
    """Wait until the queue says the run is over and return its state ({jobs: {job id: {state, ...}}, ...}). The
    process is marked in CLUSTER_WAITING while it waits, so its node holds no --jobs slot; Stale once the queue's beat
    has been stale QUEUE_TAKEOVER_SECONDS."""
    folder = root_of(root)
    mark = submitter.CLUSTER_WAITING / str(os.getpid())
    stale_since = None
    try:
        while True:
            mark.parent.mkdir(parents=True, exist_ok=True)
            mark.touch()
            state = read_json(folder / "state" / f"{run}.json")
            if state and state.get("over"):
                return state
            now = clock()
            if fresh(folder, now):
                stale_since = None
            else:
                stale_since = stale_since or now
                if now - stale_since >= QUEUE_TAKEOVER_SECONDS:
                    raise Stale(f"the queue at {folder} has been stale {now - stale_since:.0f} s; run {run} taken back")
            sleep(poll)
    finally:
        mark.unlink(missing_ok=True)
