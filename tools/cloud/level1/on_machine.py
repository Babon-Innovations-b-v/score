"""On the rented machine (tools/cloud/level1/cloud.py's job): sim body's level 1 (#70) of one run folder from that run's
own frozen code (<run>/src), resumed from its checkpoint, for at most --minutes, in this Python (the Newton env the job
names, newton_env.sh: numpy and scipy for level 1 itself, Newton, Warp and MuJoCo for its workers).

    <newton python> on_machine.py <run dir> --seeds <seeds root> --minutes M [--every 3] [--processes N]

- Its card queue (tools/cloud/backends/card_queue.py) holds this machine's card: SCORE_CARD_BUDGET_GB its first card's
  memory less CARD_MARGIN_GB, no desktop on it, the queue's folder in its home, so level 1's card processes fit as many
  side by side as that card holds (a run frozen before 2026-11-02 reads this PC's 13.5 GB whatever is set).
- Level 1's workers run under `systemd-run --user --scope` (MemoryMax=6G); where root has no user manager over ssh,
  a stand-in on PATH runs the command without the scope (the machine holds level 1 alone; said in the log).
- Level 1's output is appended to <run>/level1.log, as on this PC, and printed (the job's log here).
- At --minutes its process group is stopped (SIGTERM, SIGKILL after STOP_SECONDS) and this exits 0: the checkpoint
  holds every evaluation, and the next batch resumes from its best (tuning.resumed). A level 1 that ended by itself
  (settled: held_out.json written) gives its own exit code. A signal here stops level 1 the same way first.
"""
import argparse
import os
import pathlib
import signal
import subprocess
import sys
import threading
import time

LEVEL1 = "score/stages/sim_body/inside/evaluation/level1.py"
CARD_MARGIN_GB = 2.0  # each process's own CUDA context beside its measured share, as this PC keeps its desktop's
STOP_SECONDS = 60
QUEUE = pathlib.Path.home() / "score-card"  # /root on the machine
SHIM = pathlib.Path.home() / "level1-shim"
SHIM_SCRIPT = """#!/usr/bin/env bash
# systemd-run stand-in (tools/cloud/level1/on_machine.py): drops --user, --scope, -q and -p <property>, runs the rest.
while [ $# -gt 0 ]; do
  case "$1" in --user|--scope|-q) shift ;; -p) shift 2 ;; *) break ;; esac
done
exec "$@"
"""


def card_gb():
    """The first card's memory in GB (nvidia-smi), less CARD_MARGIN_GB."""
    found = subprocess.run(["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
                           check=True, capture_output=True, text=True).stdout.split()
    return round(int(found[0]) / 1024 - CARD_MARGIN_GB, 1)


def scope_path():
    """PATH with the systemd-run stand-in first when `systemd-run --user --scope` does not work here, else as it is."""
    tried = subprocess.run(["systemd-run", "--user", "--scope", "-q", "true"], capture_output=True)
    if tried.returncode == 0:
        return os.environ["PATH"]
    SHIM.mkdir(parents=True, exist_ok=True)
    (SHIM / "systemd-run").write_text(SHIM_SCRIPT)
    (SHIM / "systemd-run").chmod(0o755)
    print(f"systemd-run --user --scope does not work here ({tried.stderr.decode(errors='replace').strip()}): "
          "the workers run without their memory scope", flush=True)
    return f"{SHIM}:{os.environ['PATH']}"


def command(run, seeds, every, processes):
    """Level 1 from the run's own code, this Python for it and its workers, on the card, exact."""
    found = [sys.executable, "-B", str(run / "src" / LEVEL1), str(run), "--python", sys.executable, "--hours", "1000",
             "--every", str(every), "--card", str(seeds), "--exact"]
    return found + (["--processes", str(processes)] if processes else [])


def stop(child):
    """Level 1's process group stopped: SIGTERM, then SIGKILL after STOP_SECONDS."""
    if child.poll() is not None:
        return
    os.killpg(child.pid, signal.SIGTERM)
    try:
        child.wait(STOP_SECONDS)
    except subprocess.TimeoutExpired:
        os.killpg(child.pid, signal.SIGKILL)
        child.wait()


def copied(child, log):
    """Level 1's output line by line into its log and onto this process's output, until it ends."""
    with log.open("a") as kept:
        for line in child.stdout:
            kept.write(line)
            kept.flush()
            sys.stdout.write(line)
            sys.stdout.flush()


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("run", type=pathlib.Path)
    parser.add_argument("--seeds", type=pathlib.Path, required=True)
    parser.add_argument("--minutes", type=float, required=True, help="stop level 1 after this many minutes")
    parser.add_argument("--every", type=int, default=3)
    parser.add_argument("--processes", type=int, help="bodies' card processes side by side (level1.py --processes)")
    given = parser.parse_args()
    run = given.run.resolve()
    environment = {**os.environ, "PATH": scope_path(), "SCORE_CARD_BUDGET_GB": str(card_gb()),
                   "SCORE_CARD_DESKTOP_GB": "0", "SCORE_CARD_QUEUE": str(QUEUE), "OMP_NUM_THREADS": "8",
                   "OPENBLAS_NUM_THREADS": "8", "PYTHONUNBUFFERED": "1"}
    line = command(run, given.seeds, given.every, given.processes)
    with (run / "level1.log").open("a") as log:
        log.write(f"started {time.strftime('%Y-%m-%dT%H:%M:%S%z')} on a rented machine for {given.minutes:.0f} min "
                  f"(card queue {environment['SCORE_CARD_BUDGET_GB']} GB): {' '.join(line)}\n")
    child = subprocess.Popen(line, cwd=run, env=environment, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             text=True, start_new_session=True)
    for number in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT):
        signal.signal(number, lambda *_: (stop(child), sys.exit("stopped by signal; level 1 stopped first")))
    copier = threading.Thread(target=copied, args=(child, run / "level1.log"), daemon=True)
    copier.start()
    try:
        child.wait(given.minutes * 60)
    except subprocess.TimeoutExpired:
        stop(child)
        copier.join(10)
        with (run / "level1.log").open("a") as log:
            log.write(f"paused {time.strftime('%Y-%m-%dT%H:%M:%S%z')} at the batch's end: the next batch resumes from "
                      "checkpoint.jsonl's best\n")
        return 0
    copier.join(10)
    return child.returncode


if __name__ == "__main__":
    sys.exit(main())
