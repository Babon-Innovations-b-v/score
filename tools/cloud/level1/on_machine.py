"""On the rented machine (tools/cloud/level1/cloud.py's job): sim body's level 1 (#70) of one run folder from that run's
own frozen code (<run>/src), resumed from its checkpoint, for at most --minutes, in this Python (the Newton env the job
names, newton_env.sh: numpy and scipy for level 1 itself, Newton, Warp and MuJoCo for its workers).

    <newton python> on_machine.py <run dir> --seeds <seeds root> --minutes M [--every 3] [--processes N]

- The seeds first, when the seeds root lacks a case's angles.npz: levels 2 and 3 (mink, on the processors) on every
  case of the run's cases.json from the run's own src, its table.json at its starts and its rig.npz
  (`evaluation.measured`, level1.py's set at zero unknowns, `level1.worker_set` where the run's own code has it), at most half this machine's cores in bodies at once, two
  threads each, inside the batch's --minutes (owner, 2026-11-02: seeds are built on the rented machine, never on his PC).
  Their log is <seeds root>/seeds.log; the job brings the seeds root back, so the next batch carries them up built.

- What it makes is kept in the run's slice of SCORE's store, <run>/home/store (SCORE_LEVEL1_STORE, for the seeds and
  level 1 alike: `evaluation.stored`), which the job brings back; a seed or evaluation the slice holds is not made again.
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
import json
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
SEED_SCRIPT = """import json, pathlib, sys
import numpy as np
run, seeds, most = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), int(sys.argv[3])
sys.path.insert(0, str(run / "src" / "score" / "stages" / "sim_body" / "inside"))
import evaluation, landmarks, tuning
table = json.loads((run / "table.json").read_text())
cases = json.loads((run / "cases.json").read_text())
own = run / "src" / "score" / "stages" / "sim_body" / "inside" / "evaluation" / "level1.py"
if own.is_file() and "def worker_set(" in own.read_text():  # a run frozen since 2026-11-03: level 1's own start set,
    from evaluation import level1  # its segment ends' shifts too
    entries = level1.laid_out(table)
    rows, weights, rest = level1.worker_set(np.zeros(len(entries)), entries, table, run / "rig.npz")
else:
    entries = tuning.layout(table, held=landmarks.HELD, joints=set())
    starts = {name: row["link"] for name, row in table.items()}
    rows, weights = tuning.applied(np.zeros(len(entries)), entries, starts, table, {"marker goal": 1.0, "end weight": 1.0})
    rest = {"centres": {}, "rig": str(run / "rig.npz")}
found = evaluation.measured(rows, weights, rest, cases, seeds, sys.executable, most=most)
print("seeds done", len(found), flush=True)
"""
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


def seeded(run, seeds):
    """Whether the seeds root holds every case's angles.npz (the card's seed, `fit._card._seeds.first`)."""
    return all((seeds / case / "angles.npz").exists() for case in json.loads((run / "cases.json").read_text()))


def seed_command(run, seeds):
    """The seeds' levels 2 and 3 from the run's own src, half this machine's cores in bodies at once."""
    return [sys.executable, "-B", "-c", SEED_SCRIPT, str(run), str(seeds), str(max(1, (os.cpu_count() or 2) // 2))]


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
    """A child's output (level 1's, the seeds') line by line into its log and onto this process's output, until it
    ends."""
    with log.open("a") as kept:
        for line in child.stdout:
            kept.write(line)
            kept.flush()
            sys.stdout.write(line)
            sys.stdout.flush()


def ran(line, cwd, environment, log, seconds, current):
    """`line` in its own process group, its output into `log` and onto this one's, stopped at `seconds`; its exit code,
    or None when it was stopped there. `current` holds it for the signal handler while it runs."""
    child = subprocess.Popen(line, cwd=cwd, env=environment, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             text=True, start_new_session=True)
    current[0] = child
    copier = threading.Thread(target=copied, args=(child, log), daemon=True)
    copier.start()
    try:
        child.wait(max(seconds, 0))
    except subprocess.TimeoutExpired:
        stop(child)
        copier.join(10)
        return None
    copier.join(10)
    return child.returncode


def stamp():
    """Now, as the logs write it."""
    return time.strftime('%Y-%m-%dT%H:%M:%S%z')


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("run", type=pathlib.Path)
    parser.add_argument("--seeds", type=pathlib.Path, required=True)
    parser.add_argument("--minutes", type=float, required=True, help="stop level 1 after this many minutes")
    parser.add_argument("--every", type=int, default=3)
    parser.add_argument("--processes", type=int, help="bodies' card processes side by side (level1.py --processes)")
    given = parser.parse_args()
    run, seeds = given.run.resolve(), given.seeds.resolve()
    ends = time.time() + given.minutes * 60
    environment = {**os.environ, "PATH": scope_path(), "SCORE_CARD_BUDGET_GB": str(card_gb()),
                   "SCORE_CARD_DESKTOP_GB": "0", "SCORE_CARD_QUEUE": str(QUEUE), "OMP_NUM_THREADS": "8",
                   "OPENBLAS_NUM_THREADS": "8", "PYTHONUNBUFFERED": "1",
                   "SCORE_LEVEL1_STORE": str(run / "home" / "store")}
    current = [None]
    for number in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT):
        signal.signal(number, lambda *_: (current[0] and stop(current[0]),
                                          sys.exit("stopped by signal; its process group stopped first")))
    if not seeded(run, seeds):
        seeds.mkdir(parents=True, exist_ok=True)
        line = seed_command(run, seeds)
        with (run / "level1.log").open("a") as log:
            log.write(f"seeds {stamp()}: the seeds root lacks cases' angles; levels 2 and 3 on every case first, "
                      f"{line[-1]} bodies at once, log {seeds / 'seeds.log'}\n")
        code = ran(line, run, {**environment, "OMP_NUM_THREADS": "2", "OPENBLAS_NUM_THREADS": "2"},
                   seeds / "seeds.log", ends - time.time(), current)
        if code != 0 or not seeded(run, seeds):
            with (run / "level1.log").open("a") as log:
                log.write(f"seeds {stamp()}: {'stopped at the batch end' if code is None else f'exit {code}'}, "
                          "not every case seeded: level 1 not started\n")
            return 1
    line = command(run, seeds, given.every, given.processes)
    with (run / "level1.log").open("a") as log:
        log.write(f"started {stamp()} on a rented machine for {(ends - time.time()) / 60:.0f} min "
                  f"(card queue {environment['SCORE_CARD_BUDGET_GB']} GB): {' '.join(line)}\n")
    code = ran(line, run, environment, run / "level1.log", ends - time.time(), current)
    if code is None:
        with (run / "level1.log").open("a") as log:
            log.write(f"paused {stamp()} at the batch's end: the next batch resumes from checkpoint.jsonl's best\n")
        return 0
    return code

if __name__ == "__main__":
    sys.exit(main())
