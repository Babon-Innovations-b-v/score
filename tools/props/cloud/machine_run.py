"""Runs on the rented machine: every job in the batch through Pixal3D, a few at once.

    /root/venv/bin/python machine_run.py <jobs.json> <at-once>

jobs.json is a list of {"name", "arguments"}: the generator's arguments from pixal.py, with the
machine's paths. Starts are spaced a minute apart, as the two-at-once run on the owner's card was
measured. The status file says what is done, what failed, how long each took and the card's
highest memory use, and is rewritten after every change, so the runner at home can follow along
and bring back what is finished. Standard library only.
"""
import concurrent.futures
import json
import pathlib
import subprocess
import sys
import threading
import time

LAB = pathlib.Path("/root/lab")
PYTHON = "/root/venv/bin/python"
BATCH = pathlib.Path("/root/batch")
STATUS = BATCH / "status.json"
LOGS = BATCH / "logs"
SPACING_SECONDS = 60

lock = threading.Lock()
status = {"started": time.time(), "jobs": {}, "peak_gb": 0.0, "finished": False}


def save():
    """Write the status file whole, so a reader never sees half of it."""
    with lock:
        text = json.dumps(status, indent=1)
    partial = STATUS.with_suffix(".part")
    partial.write_text(text)
    partial.replace(STATUS)


def watch_memory():
    """Keep the card's highest memory use in the status, sampled every second."""
    command = ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits", "-lms", "1000"]
    with subprocess.Popen(command, stdout=subprocess.PIPE, text=True) as sampler:
        for line in sampler.stdout:
            if line.strip().isdigit():
                with lock:
                    status["peak_gb"] = max(status["peak_gb"], int(line) / 1024)


def run(job, delay):
    """One job through the generator, its output in its own log."""
    time.sleep(delay)
    name = job["name"]
    with lock:
        status["jobs"][name] = {"state": "running", "began": time.time()}
    save()
    with (LOGS / f"{name}.log").open("w") as log:
        done = subprocess.run([PYTHON, *job["arguments"]], cwd=LAB, stdout=log, stderr=subprocess.STDOUT)
    with lock:
        entry = status["jobs"][name]
        entry["state"] = "done" if done.returncode == 0 else "failed"
        entry["seconds"] = time.time() - entry["began"]
    save()


def main():
    jobs = json.loads(pathlib.Path(sys.argv[1]).read_text())
    at_once = int(sys.argv[2])
    LOGS.mkdir(parents=True, exist_ok=True)
    for job in jobs:
        status["jobs"][job["name"]] = {"state": "waiting"}
    save()
    threading.Thread(target=watch_memory, daemon=True).start()
    with concurrent.futures.ThreadPoolExecutor(at_once) as pool:
        for index, job in enumerate(jobs):
            pool.submit(run, job, SPACING_SECONDS * index if index < at_once else 0)
    with lock:
        status["finished"] = True
    save()


if __name__ == "__main__":
    main()
