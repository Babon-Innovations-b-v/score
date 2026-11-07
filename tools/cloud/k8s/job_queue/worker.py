"""The queue's worker loop, inside a warm worker's pod: job after job of its chain, each `score-job <run> <job>` in the
same pod, so the image's pull, the node's set-up and the environment's set-up are paid once a worker.

    /opt/score/venv/bin/python /score-worker/worker.py <box> <worker>

It reaches the job store through the runtime's store (the SCORE_STORE_* variables of the store Secret) and reads
`queue/<box>/assign/<worker>/<seq>.json` in order: a job is run once, `{"go": true}` ends the loop. Its beat,
`queue/<box>/beat/<worker>.json` (`{seq, at, job}`), names the assignment it took last and the job it is on (None while
it waits); it is written before a job starts, every BEAT_SECONDS while it runs and once it ends, whatever its exit, so
the queue tells a done job (its done.json) from a failed one. With nothing assigned for IDLE_EXIT_SECONDS (past the
queue's own WORKER_EXPECTED_SECONDS, so only a dead queue's worker gets there) it ends by itself.

The queue mounts this one file from a ConfigMap (`workers.configmap`), so it imports nothing at its top but the
standard library; the queue's side (`workers.py`) takes the store's keys from here.
"""
import json
import os
import subprocess
import sys
import time

POLL_SECONDS = 3  # between a waiting worker's looks at its folder
BEAT_SECONDS = 30  # between a running job's beats
IDLE_EXIT_SECONDS = 900  # past workers.WORKER_EXPECTED_SECONDS: a live queue has told an idle worker to go by then
JOB_COMMAND = ("score-job",)
RUNTIME = os.environ.get("SCORE_RUNTIME", "/opt/score/runtime")  # the image's job runtime, its store among it


def store_prefix(box):
    return f"queue/{box}"


def assignment_key(box, worker, seq):
    return f"{store_prefix(box)}/assign/{worker}/{seq:08d}.json"


def beat_key(box, worker):
    return f"{store_prefix(box)}/beat/{worker}.json"


class Worker:
    """One worker's place in its folder: the last assignment it took, and its beat."""

    def __init__(self, store, box, worker, command=JOB_COMMAND, clock=time.time):
        self.store, self.box, self.worker, self.command, self.clock = store, box, worker, list(command), clock
        self.seq, self.waiting_since = -1, clock()
        self.beat(None)

    def beat(self, job):
        self.store.write_bytes(beat_key(self.box, self.worker),
                               json.dumps({"seq": self.seq, "at": self.clock(), "job": job}).encode())

    def step(self):
        """Take the next assignment, if there is one: "go" when told to go, "ran" once its job ran, else None."""
        key = assignment_key(self.box, self.worker, self.seq + 1)
        if not self.store.exists(key):
            return None
        given = json.loads(self.store.read_bytes(key))
        if given.get("go"):
            return "go"
        self.seq += 1
        self.run_job(given["run"], given["job"])
        self.waiting_since = self.clock()
        return "ran"

    def run_job(self, run, job):
        """One job as its own process, beating while it runs; its exit is the job's own record (done.json or
        failed-<attempt>.json), so the worker goes on to the next whatever it was."""
        self.beat(f"{run}/{job}")
        try:
            child = subprocess.Popen([*self.command, run, job])
            while True:
                try:
                    child.wait(timeout=BEAT_SECONDS)
                    break
                except subprocess.TimeoutExpired:
                    self.beat(f"{run}/{job}")
        finally:
            self.beat(None)


def serve(worker, poll=POLL_SECONDS, idle_exit=IDLE_EXIT_SECONDS, sleep=time.sleep):
    """Take assignment after assignment until told to go ("go") or nothing came for `idle_exit` seconds ("idle")."""
    while True:
        taken = worker.step()
        if taken == "go":
            return "go"
        if taken is None:
            if worker.clock() - worker.waiting_since >= idle_exit:
                return "idle"
            sleep(poll)


def main(arguments=None):
    arguments = sys.argv[1:] if arguments is None else arguments
    if len(arguments) != 2:
        raise SystemExit("usage: worker.py <box> <worker>")
    sys.path.insert(0, RUNTIME)
    import store as stores  # the image's runtime (RUNTIME), only there in the pod

    box, worker = arguments
    ended = serve(Worker(stores.from_environment(), box, worker))
    print(f"[score-worker] {worker}: {ended}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
