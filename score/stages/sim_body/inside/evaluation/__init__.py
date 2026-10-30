"""Level 1's runner (#70): each evaluation runs levels 2 and 3 on every body of a side (the tuning bodies, or the
held-out check bodies) side by side, one process per SOMA body (`_case.py`, at most MOST at once, each under
systemd-run MemoryMax=6G with two threads, a new one started only while FREE_GB of memory is available), and reads
back each clip's honest measures (`_measure`: joint error, rotation error on the frozen calibration copy `fit._frozen`,
bones outside SOMA's skin by region), unrounded (`SOLVED`, the solver's; `rounded` makes m.json, the copy people
read). `case_score` and `side_score` sum them into one number for the log; `accepted` is the held-out rule: the
check bodies' score within 10 % of the tuning bodies'. The check bodies are scored, never used to choose. Standard library only here; the worker needs Newton's Python."""
import json
import pathlib
import shutil
import subprocess
import time

MOST = 6
FREE_GB = 12
HELD_OUT_SHARE = 0.10  # the check bodies' score may be at most this much worse than the tuning bodies'
WORKER = pathlib.Path(__file__).resolve().parent / "_case.py"
SETS_WORKER = pathlib.Path(__file__).resolve().parent / "_card_sets.py"  # every set of a Jacobian, one card process
SAME_SEEDS = "--same-seeds"  # _card_sets: every set seeded from the seeds root, the base point's way
SOLVED = "measures.json"  # a clip's unrounded measures, the solver's; m.json beside it is the rounded copy people read
SEEDS = "angles.npz"  # a clip's mink angles per frame (qpos, frames x nq): the card's seeds (fit._card._seeds)
PLACES = 2  # decimals of the rounded copy
TWO_WORD_MOTIONS = ("arms_raise", "sit_stand")  # motions whose name holds an underscore


def rounded(value, places=PLACES):
    """`value` (measures: dicts, lists, numbers) with every float rounded to `places`, the copy people read."""
    if isinstance(value, dict):
        return {key: rounded(item, places) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [rounded(item, places) for item in value]
    return round(value, places) if isinstance(value, float) else value


def body_of(case):
    """A case's SOMA body: its name less its motion (tall_heavy_kimodo -> tall_heavy, mean_sit_stand -> mean)."""
    for motion in TWO_WORD_MOTIONS:
        if case.endswith("_" + motion):
            return case[:-len(motion) - 1]
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


def measured(rows, weights, rest, cases, out, python, **options):
    """{case: honest measures} of levels 2 and 3 on `cases` with the landmark table `rows`, global `weights` and
    `rest` ({"centres": the group ends' offsets, "rig": SOMA's template rig the calibration is read at rest from},
    out/rest.json, the worker's); raises when any body fails or any clip has no measures."""
    shutil.rmtree(out, ignore_errors=True)
    set_written(out, rows, weights, rest)
    codes = run_all(by_body(cases), out, python, **options)
    return read_back(out, cases, codes)


def set_written(folder, rows, weights, rest):
    """folder/table.json, weights.json and rest.json: what a worker reads for one set of unknowns."""
    folder.mkdir(parents=True)
    (folder / "table.json").write_text(json.dumps(rows, indent=1))
    (folder / "weights.json").write_text(json.dumps(weights))
    (folder / "rest.json").write_text(json.dumps(rest, indent=1))


def read_back(folder, cases, codes):
    """{case: unrounded measures} from folder/<case>/SOLVED; raises when any exit code is not 0 or a case has none."""
    missing = [case for case in cases if not (folder / case / SOLVED).exists()]
    if missing or any(codes.values()):
        raise RuntimeError(f"{folder.name}: failed {codes}, missing {missing}; logs in {folder}")
    return {case: json.loads((folder / case / SOLVED).read_text()) for case in cases}


def sets_command(python, seeds_root, out, cases):
    """The one card process of `measured_many`, capped like every Python process on this PC."""
    return ["systemd-run", "--user", "--scope", "-p", "MemoryMax=6G", "-q", "env", "OMP_NUM_THREADS=2",
            "OPENBLAS_NUM_THREADS=2", "MKL_NUM_THREADS=2", str(python), "-B", str(SETS_WORKER), str(seeds_root),
            str(out), SAME_SEEDS, *[f"{case}={job}" for case, job in cases.items()]]


def launched(command, log):
    """Runs `command` to its end, its output into `log`; its exit code."""
    with open(log, "w") as file:
        return subprocess.call(command, stdout=file, stderr=subprocess.STDOUT)


def measured_many(sets, cases, out, python, seeds_root, launch=launched):
    """[{case: honest measures}] for every set ([(rows, weights, rest)], as `measured` takes one) in ONE card process
    (`_card_sets.py`, card build step 6a), every set seeded from `seeds_root`'s angles. out/s00000.. hold the sets;
    raises when the process fails or any set misses a case. `launch(command, log)` runs it (default `launched`)."""
    shutil.rmtree(out, ignore_errors=True)
    folders = [out / f"s{index:05d}" for index in range(len(sets))]
    for folder, (rows, weights, rest) in zip(folders, sets):
        set_written(folder, rows, weights, rest)
    code = launch(sets_command(python, seeds_root, out, cases), out / "sets.log")
    return [read_back(folder, cases, {"sets": code}) for folder in folders]


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


def warmed(solve, kept, body, tolerance):
    """`solve` (fit.constants) at `tolerance`: the body's first call cold, its "solved" kept in `kept[body]`; every
    later call warm from it. A later answer laid out differently from the kept one is refused."""
    def constants(fitting, recordings):
        if body not in kept:
            found = solve(fitting, recordings, tolerance=tolerance)
            kept[body] = found["solved"]
            return found
        found = solve(fitting, recordings, warm=kept[body], tolerance=tolerance)
        if [part.shape for part in found["solved"]] != [part.shape for part in kept[body]]:
            raise ValueError(f"{body}: level 2's unknowns laid out unlike the base point's, warm start refused")
        return found
    return constants
