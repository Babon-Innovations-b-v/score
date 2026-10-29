"""Level 1's runner (#70): each evaluation runs levels 2 and 3 on every body of a side (the tuning bodies, or the
held-out check bodies) side by side, one process per SOMA body (`_case.py`, at most MOST at once, each under
systemd-run MemoryMax=6G with two threads, a new one started only while FREE_GB of memory is available), and reads
back each clip's honest measures (`_measure`: joint error, rotation error on the frozen calibration copy `fit._frozen`,
bones outside SOMA's skin by region). `case_score` and `side_score` sum them into one number for the log; `accepted`
is the held-out rule: the check bodies' score within 10 % of the tuning bodies'. The check bodies are scored, never
used to choose. Standard library only here; the worker needs Newton's Python."""
import json
import pathlib
import shutil
import subprocess
import time

MOST = 6
FREE_GB = 12
HELD_OUT_SHARE = 0.10  # the check bodies' score may be at most this much worse than the tuning bodies'
WORKER = pathlib.Path(__file__).resolve().parent / "_case.py"


def body_of(case):
    """A case's SOMA body: its name less the clip after the last underscore (tall_heavy_kimodo -> tall_heavy)."""
    return case.rsplit("_", 1)[0]


def picked(cases, split, side):
    """The cases ({case: job path}) whose body is on `side` of the split ({"tuning": [...], "check": [...]})."""
    return {case: job for case, job in cases.items() if body_of(case) in split[side]}


def by_body(cases):
    """{body: {case: job}}, every clip of a body together (level 2 solves a body once from all its clips)."""
    bodies = {}
    for case, job in cases.items():
        bodies.setdefault(body_of(case), {})[case] = job
    return bodies


def available_gb():
    """MemAvailable from /proc/meminfo, in GB."""
    for line in pathlib.Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable"):
            return int(line.split()[1]) / 2 ** 20
    raise RuntimeError("no MemAvailable in /proc/meminfo")


def command(python, worker, cases, out):
    """One body's worker command, capped like every Python process on this PC."""
    return ["systemd-run", "--user", "--scope", "-p", "MemoryMax=6G", "-q", "env", "OMP_NUM_THREADS=2",
            "OPENBLAS_NUM_THREADS=2", "MKL_NUM_THREADS=2", str(python), "-B", str(worker), str(out / "table.json"),
            str(out / "weights.json"), str(out), *[f"{case}={job}" for case, job in cases.items()]]


def run_all(bodies, out, python, worker=WORKER, most=MOST, free_gb=FREE_GB, launch=None):
    """Every body's worker, at most `most` at once and only while `free_gb` is available; {body: exit code}.
    `launch(body, cases)` starts one (default: `command` under its log out/<body>.log)."""
    def started(body, cases):
        log = open(out / f"{body}.log", "w")
        return subprocess.Popen(command(python, worker, cases, out), stdout=log, stderr=subprocess.STDOUT)
    launch = launch or started
    waiting, running, codes = list(bodies), {}, {}
    while waiting or running:
        for body, process in list(running.items()):
            if process.poll() is not None:
                codes[body] = process.returncode
                del running[body]
        if waiting and len(running) < most and available_gb() >= free_gb:
            body = waiting.pop(0)
            running[body] = launch(body, bodies[body])
        time.sleep(0.2 if running or waiting else 0)
    return codes


def measured(rows, weights, cases, out, python, **options):
    """{case: honest measures} of levels 2 and 3 on `cases` with the landmark table `rows` and global `weights`;
    raises when any body fails or any clip has no measures."""
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    (out / "table.json").write_text(json.dumps(rows, indent=1))
    (out / "weights.json").write_text(json.dumps(weights))
    codes = run_all(by_body(cases), out, python, **options)
    missing = [case for case in cases if not (out / case / "m.json").exists()]
    if missing or any(codes.values()):
        raise RuntimeError(f"{out.name}: failed {codes}, missing {missing}; logs in {out}")
    return {case: json.loads((out / case / "m.json").read_text()) for case in cases}


def case_score(found):
    """One clip's follow score (lower is better): mean joint error / 10 mm + mean group rotation error / 5 deg +
    bones outside the skin / 10 %."""
    joints = sum(value[0] for value in found["per joint mm"].values()) / len(found["per joint mm"])
    groups = sum(value[0] for value in found["per group deg"].values()) / len(found["per group deg"])
    return joints / 10 + groups / 5 + found["bones outside all %"] / 10


def side_score(found):
    """The mean case score over a side's clips."""
    return sum(case_score(value) for value in found.values()) / len(found)


def accepted(check, tuning):
    """The held-out rule: the check bodies' score within HELD_OUT_SHARE of the tuning bodies'."""
    return check <= (1 + HELD_OUT_SHARE) * tuning
