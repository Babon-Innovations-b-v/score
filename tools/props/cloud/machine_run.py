"""Runs on the rented machine: takes jobs from its queue and puts them through Pixal3D.

    /root/venv/bin/python machine_run.py <runs-per-card>

The runner at home drops a job in /root/batch/queue/ as <name>.json, a list of the generator's
arguments with this machine's paths, and its picture in /root/batch/in/ (the generator cuts it out
here). Each card runs
<runs-per-card> jobs at once, their starts spaced out; a machine with two cards runs twice as many.
When the runner writes /root/batch/closed and the queue is empty, the machine finishes what it is
running and stops.

The status file says each job's state and seconds, and each card's highest memory use, and is
rewritten after every change, so the runner can follow along and bring back what is finished.
Standard library only.
"""
import json
import os
import pathlib
import subprocess
import sys
import threading
import time

LAB = pathlib.Path("/root/lab")
PYTHON = "/root/venv/bin/python"
BATCH = pathlib.Path("/root/batch")
QUEUE = BATCH / "queue"
TAKEN = BATCH / "taken"
CLOSED = BATCH / "closed"
STATUS = BATCH / "status.json"
LOGS = BATCH / "logs"
# A card's first runs start this far apart, so they do not all load the weights at once.
SPACING_SECONDS = 30
LOOK_SECONDS = 2

lock = threading.Lock()
status = {"started": time.time(), "jobs": {}, "peak_gb": {}, "finished": False}


def save():
    """Write the status file whole, so a reader never sees half of it."""
    with lock:
        text = json.dumps(status, indent=1)
    partial = STATUS.with_suffix(".part")
    partial.write_text(text)
    partial.replace(STATUS)


def cards():
    """How many graphics cards this machine has."""
    listing = subprocess.run(["nvidia-smi", "-L"], capture_output=True, text=True, check=True)
    return len([line for line in listing.stdout.splitlines() if line.startswith("GPU ")])


def watch_memory():
    """Keep each card's highest memory use in the status, sampled every second."""
    command = ["nvidia-smi", "--query-gpu=index,memory.used", "--format=csv,noheader,nounits",
               "-lms", "1000"]
    with subprocess.Popen(command, stdout=subprocess.PIPE, text=True) as sampler:
        for line in sampler.stdout:
            card, _, used = line.partition(",")
            if used.strip().isdigit():
                with lock:
                    peaks = status["peak_gb"]
                    peaks[card.strip()] = max(peaks.get(card.strip(), 0.0), int(used) / 1024)


def take():
    """The next queued job, claimed by moving it out of the queue; None when the queue is empty.
    rsync writes a file under a hidden name and renames it, so a half-copied job is never seen."""
    for path in sorted(QUEUE.glob("[!.]*.json")):
        claimed = TAKEN / path.name
        try:
            path.replace(claimed)
        except FileNotFoundError:
            continue
        return json.loads(claimed.read_text()), claimed.stem
    return None


def run(arguments, name, card):
    """One job through the generator on `card`, its output in its own log."""
    with lock:
        status["jobs"][name] = {"state": "running", "card": card, "began": time.time()}
    save()
    environment = {**os.environ, "CUDA_VISIBLE_DEVICES": str(card)}
    with (LOGS / f"{name}.log").open("w") as log:
        done = subprocess.run([PYTHON, *arguments], cwd=LAB, stdout=log, stderr=subprocess.STDOUT,
                              env=environment)
    with lock:
        entry = status["jobs"][name]
        entry["state"] = "done" if done.returncode == 0 else "failed"
        entry["seconds"] = time.time() - entry["began"]
    save()


def slot(card, delay):
    """One of a card's places: wait `delay`, then run jobs one after another until the queue is
    closed and empty."""
    time.sleep(delay)
    while True:
        job = take()
        if job:
            run(job[0], job[1], card)
        elif CLOSED.exists():
            return
        else:
            time.sleep(LOOK_SECONDS)


def main():
    per_card = int(sys.argv[1])
    for folder in (QUEUE, TAKEN, LOGS):
        folder.mkdir(parents=True, exist_ok=True)
    save()
    threading.Thread(target=watch_memory, daemon=True).start()
    places = [threading.Thread(target=slot, args=(card, SPACING_SECONDS * place))
              for card in range(cards()) for place in range(per_card)]
    for place in places:
        place.start()
    for place in places:
        place.join()
    with lock:
        status["finished"] = True
    save()


if __name__ == "__main__":
    main()
