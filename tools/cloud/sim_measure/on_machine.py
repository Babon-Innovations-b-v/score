"""On the rented machine (tools/cloud/sim_measure/cloud.py's job): each measure folder's scripts/go.sh in turn, in this
Python (the Newton env the job names), on level 1's machine set-up (tools/cloud/level1/on_machine.py, loaded from
--repo, which the job carries up at its path): the card queue sized to this machine's card, its folder in this home,
no desktop, and the systemd-run stand-in where root has no user manager.

    <newton python> on_machine.py <folder> [<folder> ...] --minutes M --repo <repo>

- Each go.sh is given PY (this Python), REPO (--repo, the carried repo, wherever it landed: the card queue and
  PYTHONPATH are named from it, never a written path) and LANES (this machine's cores over THREADS, the threads each
  of its jobs takes), and its output goes to <folder>/machine.log and onto this process's output.
- A go.sh's own exit code is said and the next folder runs: its jobs' done markers say what was made, and a job
  that failed here fails the same way on this PC (a model that will not compile).
- At --minutes the running go.sh is stopped with its process group (level 1's `stop`) and no later folder starts; this
  exits 3, so the job reads as cut off, its folders brought back all the same. A signal here stops it the same way.
"""
import argparse
import importlib.util
import os
import pathlib
import shutil
import signal
import sys
import time

THREADS = 4  # each measure job's OMP_NUM_THREADS (the go scripts' LIMIT)
PYTHON3 = pathlib.Path.home() / "python3-shim"  # python3 for the go scripts where the machine has none


def level1_machine(repo):
    """tools/cloud/level1/on_machine.py from `repo`, under its own name."""
    spec = importlib.util.spec_from_file_location("level1_on_machine", repo / "tools/cloud/level1/on_machine.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def with_python3(path):
    """`path` with a python3 (this Python) first when it holds none: a go.sh runs the card queue as `python3`, and the
    cluster's newton image has only its own Python (2026-11-06: every job of a measure exited 127 at once)."""
    if shutil.which("python3", path=path):
        return path
    PYTHON3.mkdir(parents=True, exist_ok=True)
    link = PYTHON3 / "python3"
    if not link.is_symlink():
        link.symlink_to(sys.executable)
    return f"{PYTHON3}:{path}"


def environment(level1, repo):
    """The go scripts' environment on this machine, `repo` the carried repo's path."""
    return {**os.environ, "PATH": with_python3(level1.scope_path()), "SCORE_CARD_BUDGET_GB": str(level1.card_gb()),
            "SCORE_CARD_DESKTOP_GB": "0", "SCORE_CARD_QUEUE": str(level1.QUEUE), "PY": sys.executable,
            "REPO": str(repo), "LANES": str(max(1, (os.cpu_count() or THREADS) // THREADS)), "PYTHONUNBUFFERED": "1"}


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("folders", type=pathlib.Path, nargs="+")
    parser.add_argument("--minutes", type=float, required=True, help="stop after this many minutes")
    parser.add_argument("--repo", type=pathlib.Path, required=True, help="the repo's path, carried up by the job")
    given = parser.parse_args()
    ends = time.time() + given.minutes * 60
    level1 = level1_machine(given.repo)
    found = environment(level1, given.repo)
    current = [None]
    for number in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT):
        signal.signal(number, lambda *_: (current[0] and level1.stop(current[0]),
                                          sys.exit("stopped by signal; its process group stopped first")))
    for folder in given.folders:
        print(f"{level1.stamp()} {folder}: go.sh, {found['LANES']} lanes, card queue "
              f"{found['SCORE_CARD_BUDGET_GB']} GB", flush=True)
        code = level1.ran(["bash", str(folder / "scripts" / "go.sh")], folder, found, folder / "machine.log",
                          ends - time.time(), current)
        if code is None:
            print(f"{level1.stamp()} {folder}: stopped at the job's minutes; later folders not started", flush=True)
            return 3
        print(f"{level1.stamp()} {folder}: go.sh exit {code}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
