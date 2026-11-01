"""Level 1's runner (#70): each evaluation runs levels 2 and 3 on every body of a side (the tuning bodies, or the
held-out check bodies) side by side, one process per SOMA body (`_case.py`, at most MOST at once, each under
systemd-run MemoryMax=6G with two threads, a new one started only while FREE_GB of memory is available), and reads
back each clip's honest measures (`_measure`: joint error, rotation error on the frozen calibration copy `fit._frozen`,
bones outside SOMA's skin by region), unrounded (`SOLVED`, the solver's; `rounded` makes m.json, the copy people
read). `case_score` and `side_score` sum them into one number for the log; `accepted` is the held-out rule: the
check bodies' score within 10 % of the tuning bodies'. The check bodies are scored, never used to choose. Each card
process (`measured_many`'s sets, `blocked`'s blocks) holds its own measured share of this PC's card queue
(`CardShares`, tools/cloud/backends/card_queue.py) at sim-body priority while it runs, never the run as a whole; the
seconds a body waited for its share are `CardShares.waited`, which level 1's clock leaves out. Standard library only
here; the worker needs Newton's Python."""
import importlib.util
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
SET_PROCESSES = 10  # bodies' set processes side by side (`measured_many`): every tuning body at once (2026-10-31, l1d's sets
# phase with 4: the card at 14 %, 3.3 GB, load 6 on 24 cores; a process holds ~2 GB of memory, `FREE_GB` still guards)
CHUNK = 12  # sets per chunk of the one card process: 32 tall sets peaked ~5.2-5.5 GB own (phase A ~2.6, +~2.7 per 32 in the constants phase; night/across c38), 12 keeps ~3.7 under 4
BLOCKS_WORKER = pathlib.Path(__file__).resolve().parents[1] / "tuning" / "_adjoint" / "_check_columns.py"  # one body's exact blocks
SAME_SEEDS = "--same-seeds"  # _card_sets: every set seeded from the seeds root, the base point's way
UNCONVERGED = "unconverged-{body}.txt"  # _card_sets: a set whose level 3 frame of `body` did not stop (its message)
SOLVED = "measures.json"  # a clip's unrounded measures, the solver's; m.json beside it is the rounded copy people read
SEEDS = "angles.npz"  # a clip's mink angles per frame (qpos, frames x nq): the card's seeds (fit._card._seeds)
LOOK_SECONDS = 2  # between asks of a body refused its card share (card_queue's own LOOK_SECONDS)
PLACES = 2  # decimals of the rounded copy
CARD_QUEUE = pathlib.Path(__file__).resolve().parents[5] / "tools" / "cloud" / "backends" / "card_queue.py"
PRIORITY = "sim-body"  # the card queue's first rank (owner, 2026-10-31: sim bodies before the film)
# Each card process's own card peak, GB (2026-11-01, tall_heavy's 15 clips, l1h's table, Newton's Python under a 1.4 GB
# share of the card queue beside l1h): warp's mempool high (wp.get_mempool_used_mem_high; its release threshold 0, so
# the card holds what is in use) plus a warp context's own 0.34 GB (the card's used memory before and after a bare
# context came up, the median of six; the card's total could not be read alone: l1h's ten processes beside it).
# The queue measures a share as its peak less the desktop, no margin: each is that peak rounded up to 0.1 GB.
SETS_CARD_GB = 1.4  # a `_card_sets` of one set: mempool 0.984 + 0.34 (189 s)
BLOCKS_CARD_GB = 0.9  # a `_check_columns` body: mempool 0.503 + 0.34 (359 s, 175 s of it level 2's host solve)
CHUNK_CARD_GB = 4.0  # a `_card_sets` of a full CHUNK of nudged sets: CHUNK's note (~3.7 own), not the queue's
TWO_WORD_MOTIONS = ("arms_raise", "sit_stand")  # motions whose name holds an underscore
SKIN_ROWS = False  # level 1 tunes on level 3 without its skin rows; the stage (sim_body.py) holds them (#70 2026-11-01:
# with them level 3 jumps between minima under small moves of level 1's unknowns, so its gradient cannot be checked)


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


class CardShares:
    """One kind of level 1's card processes in this PC's card queue: each body's process takes a share of `card_gb`
    (measured) at PRIORITY before it starts and gives it back when it ends; `waited` sums the seconds a body stood
    ready (a slot and memory free) with its share refused."""

    def __init__(self, kind, card_gb, queue=None):
        self.kind, self.card_gb, self.waited = kind, card_gb, 0.0
        self.queue = queue or card_queue()

    def take(self, body):
        """`body`'s share, watched (the queue measures it while held); None while the queue refuses it."""
        handle = self.queue.take(f"sim-body-l1 {self.kind} {body}", self.card_gb, PRIORITY)
        return None if handle is None else self.queue.watch(handle)

    def give_back(self, handle):
        """A share given back, its measure recorded."""
        self.queue.release(handle)


def card_queue():
    """This PC's card queue module (tools/cloud/backends/card_queue.py, standard library only), loaded from its file."""
    spec = importlib.util.spec_from_file_location("card_queue", CARD_QUEUE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_all(bodies, out, python, worker=WORKER, most=MOST, free_gb=FREE_GB, launch=None, shares=None):
    """Every body's worker, at most `most` at once and only while `free_gb` is available; {body: exit code}.
    `launch(body, cases)` starts one (default: `command` under its log out/<body>.log). With `shares` (CardShares)
    each starts only once it holds its card share, given back when it ends; the seconds a ready body waited for it
    go to `shares.waited`."""
    def started(body, cases):
        log = open(out / f"{body}.log", "w")
        return subprocess.Popen(command(python, worker, cases, out), stdout=log, stderr=subprocess.STDOUT)
    launch = launch or started
    waiting, running, held, codes = list(bodies), {}, {}, {}
    try:
        while waiting or running:
            began = time.time()
            for body, process in list(running.items()):
                if process.poll() is not None:
                    codes[body] = process.returncode
                    del running[body]
                    if body in held:
                        shares.give_back(held.pop(body))
            refused = False
            if waiting and len(running) < most and available_gb() >= free_gb:
                share = shares.take(waiting[0]) if shares else None
                refused = shares is not None and share is None
                if not refused:
                    body = waiting.pop(0)
                    if share is not None:
                        held[body] = share
                    running[body] = launch(body, bodies[body])
            time.sleep(LOOK_SECONDS if refused else 0.2 if running or waiting else 0)
            if refused:
                shares.waited += time.time() - began
    finally:
        for share in held.values():
            shares.give_back(share)
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


def read_back(folder, cases, codes, unconverged=False):
    """{case: unrounded measures} from folder/<case>/SOLVED; raises when any exit code is not 0 or a case has none.
    A set a body's level 3 did not stop on (an UNCONVERGED file, `_card_sets`) is None when `unconverged`, else raises
    with its message."""
    stuck = sorted(folder.glob(UNCONVERGED.format(body="*")))
    if stuck and not any(codes.values()):
        if unconverged:
            return None
        raise RuntimeError(f"{folder.name}: " + "; ".join(path.read_text() for path in stuck))
    missing = [case for case in cases if not (folder / case / SOLVED).exists()]
    if missing or any(codes.values()):
        raise RuntimeError(f"{folder.name}: failed {codes}, missing {missing}; logs in {folder}")
    return {case: json.loads((folder / case / SOLVED).read_text()) for case in cases}


def block_command(python, seeds_root, folder, cases):
    """One body's exact level 1 blocks (`tuning/_adjoint/_check_columns.py` at the set `folder`: level 2 once for the
    body, then each case's block saved to folder/<case>.npz), capped like every Python process on this PC."""
    return ["systemd-run", "--user", "--scope", "-p", "MemoryMax=6G", "-q", "env", "OMP_NUM_THREADS=2",
            "OPENBLAS_NUM_THREADS=2", "MKL_NUM_THREADS=2", str(python), "-B", str(BLOCKS_WORKER),
            str(BLOCKS_WORKER.parent), str(seeds_root), str(folder), str(folder),
            *[f"{case}={job}" for case, job in cases.items()]]


def blocked(rows, weights, rest, cases, out, python, seeds_root, launch=None, most=SET_PROCESSES, shares=None,
            **options):
    """{case: out/<case>.npz}, each case's exact block (rows x every unknown of `tuning.layout(ends=)`) at one set,
    one process a body side by side as `run_all` runs bodies (level 2 solved and factored once a body from all its
    clips, as the evaluations solve it; 2026-10-31: one process a case solved it from that case's clip alone, seven
    times a body), at most `most` side by side (SET_PROCESSES: every tuning body at once since 2026-11-01, MOST before); a failed body runs once more; raises when one still fails or a case misses its block.
    `launch(body, cases)` starts one (default: `block_command` under out/<body>.log); each holds its card share
    (`shares`, default CardShares("blocks", BLOCKS_CARD_GB)) while it runs."""
    shares = shares or CardShares("blocks", BLOCKS_CARD_GB)
    shutil.rmtree(out, ignore_errors=True)
    set_written(out, rows, weights, rest)

    def started(body, body_cases):
        log = open(out / f"{body}.log", "w")
        return subprocess.Popen(block_command(python, seeds_root, out, body_cases), stdout=log,
                                stderr=subprocess.STDOUT)
    bodies = by_body(cases)
    codes = run_all(bodies, out, python, launch=launch or started, most=most, shares=shares, **options)
    # a failed body runs once more: the card may refuse a context while the run beside it holds it (2026-10-31,
    # l1d: 3 of 70 blocks "Failed to acquire primary context for device cuda:0", and the whole step was lost)
    again = {body: bodies[body] for body, code in codes.items() if code}
    codes.update(run_all(again, out, python, launch=launch or started, most=most, shares=shares, **options)
                 if again else {})
    missing = [case for case in cases if not (out / f"{case}.npz").exists()]
    if missing or any(codes.values()):
        raise RuntimeError(f"{out.name}: blocks failed {codes}, missing {missing}; logs in {out}")
    return {case: out / f"{case}.npz" for case in cases}


def sets_command(python, seeds_root, out, cases):
    """One body's card process of `measured_many`, capped like every Python process on this PC."""
    return ["systemd-run", "--user", "--scope", "-p", "MemoryMax=6G", "-q", "env", "OMP_NUM_THREADS=2",
            "OPENBLAS_NUM_THREADS=2", "MKL_NUM_THREADS=2", str(python), "-B", str(SETS_WORKER), str(seeds_root),
            str(out), SAME_SEEDS, *[f"{case}={job}" for case, job in cases.items()]]


def measured_many(sets, cases, out, python, seeds_root, launch=None, chunk=None, most=SET_PROCESSES,
                  free_gb=FREE_GB, unconverged=False, shares=None):
    """[{case: honest measures}] for every set ([(rows, weights, rest)], as `measured` takes one): one card process a
    body (`_card_sets.py`, card build step 6a: every set of that body in it, its start-up kept), at most `most` side by
    side as `run_all` runs bodies (2026-10-31: one process for every body sat at ~1.3 cores, the card mostly idle, 37
    min a Jacobian on l1d), a failed one run once more (the card may refuse a context, as `blocked`'s). Each process
    runs the sets in chunks of at most `chunk` (default CHUNK, so its card memory stays bounded), one chunk after
    another, every set seeded from `seeds_root`'s angles. out/p000/s00000.. hold the sets; raises when a process fails
    or any set misses a case; a set some body's level 3 did not stop on is None when `unconverged` (a Jacobian's
    nudged set: `tuning._differences.jacobian` steps its columns the other way), else raises. `launch(body, cases)` starts one (default: `sets_command` under out/sets-<body>.log); each holds its card share
    (`shares`, default CardShares("sets", SETS_CARD_GB)) while it runs."""
    shares = shares or CardShares("sets", SETS_CARD_GB)
    shutil.rmtree(out, ignore_errors=True)
    chunk = chunk or CHUNK
    folders = [out / f"p{index // chunk:03d}" / f"s{index:05d}" for index in range(len(sets))]
    for folder, (rows, weights, rest) in zip(folders, sets, strict=True):
        set_written(folder, rows, weights, rest)

    def started(body, body_cases):
        log = open(out / f"sets-{body}.log", "w")
        return subprocess.Popen(sets_command(python, seeds_root, out, body_cases), stdout=log,
                                stderr=subprocess.STDOUT)
    bodies = by_body(cases)
    codes = run_all(bodies, out, python, launch=launch or started, most=most, free_gb=free_gb, shares=shares)
    again = {body: bodies[body] for body, code in codes.items() if code}
    codes.update(run_all(again, out, python, launch=launch or started, most=most, free_gb=free_gb, shares=shares)
                 if again else {})
    return [read_back(folder, cases, codes, unconverged) for folder in folders]


def case_score(found):
    """One clip's score (lower is better): the share of its bones outside the skin over 10 %, level 1's aim since
    2026-11-01 (the bones inside the person's skin; its least squares reads their depth, `tuning.case_residuals`).
    Turns and joints are not in it: `reported`. None for a clip with no unfolded skin frame (`fit._skin.unfolded`):
    its share is no measure, left out of `side_score` and counted in `reported`."""
    share = found["bones outside all %"]
    return None if share is None else share / 10


def reported(found):
    """What a side's evaluation reports beside its score, never tuned ({name: value}, means over its clips): the turns
    check (each SOMA segment drives one bone group, so about 0 by construction: the median and the worst group's root
    mean square, deg), the joint centres' error (median, mm) and the clips with no unfolded frame (`case_score`)."""
    cases = list(found.values())
    groups = sorted(cases[0]["per group rms deg"])
    by_group = {group: sum(case["per group rms deg"][group] for case in cases) / len(cases) for group in groups}
    worst = max(by_group, key=by_group.get)
    return {"turns median deg": round(sum(case["turns deg"][0] for case in cases) / len(cases), 3),
            "turns worst group": f"{worst} {by_group[worst]:.2f}",
            "joints median mm": round(sum(case["joints mm"][0] for case in cases) / len(cases), 3),
            "clips with no unfolded frame": sorted(case for case, value in found.items() if case_score(value) is None)}


def side_score(found):
    """The mean case score over a side's clips that have one (`case_score`); refused when none has."""
    scores = [score for score in map(case_score, found.values()) if score is not None]
    if not scores:
        raise ValueError(f"no clip of {sorted(found)} has an unfolded skin frame: no score")
    return sum(scores) / len(scores)


def accepted(check, tuning):
    """The held-out rule: the check bodies' score within HELD_OUT_SHARE of the tuning bodies'."""
    return check <= (1 + HELD_OUT_SHARE) * tuning
