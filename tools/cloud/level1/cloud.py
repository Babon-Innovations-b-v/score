"""Sim body's level 1 (#70, score/stages/sim_body/inside/evaluation/level1.py) on a rented card machine instead of this
PC, through blender_cloud.py's machine path (the owner's limits, the watchdog, the self-delete, the delete, the ledger):
one batch a held job of at most BATCH_MINUTES, its outputs brought back every --bring-every minutes and at its end, the
next batch resuming from the checkpoint brought back.

    ~/.farm-factory-props/env/bin/python tools/cloud/level1/cloud.py <run dir> --seeds <seeds root> --who "<session>" \
        [--batches 1] [--minutes 230] [--every 3] [--bring-every 20] [--classes gpu-80gb-x2-48c,...] [--dry-run] [--detach]

Spending: it rents only inside a cleared run (SCORE_SPEND_TICKET, or the owner's spend yes under `override`), as every
renting call (score.adapters.compute.require_cleared); a batch past the owner's limits (4 h, EUR 60) is refused.

- Carried up, at the same absolute paths (blender_cloud: 8 MB and more through the object store, once): every entry of
  the run folder but LEFT_HERE (its latest evaluations, this PC's pid, the batches' job files) (its src/, the run's frozen code, which the machine runs), the seeds root, and every
  absolute path the cases' job.json files name, those under the cases' common data folder as that one folder (the
  MyoFullBody model folder on its own).
- Brought back (every --bring-every minutes while it runs, and at its end, also when it fails or is stopped):
  BROUGHT (checkpoint.jsonl, check.jsonl, steps.jsonl, level1.log, the results) and evals/; evaluation folders older
  than the newest KEEP_EVALS are then removed here, as level 1 removes them on its machine.
- The machine: kind `sim-body-l1` (capacity.py: the most cores beside a card first; level 1 is held by processor
  time, two threads a body), the job's env newton_env.sh (built there in a few minutes), its card queue sized to its
  card and every tuning body at once (`--processes`, when the run's own level1.py takes it): on_machine.py.
- Batches run one after another up to --batches; the chain ends early when held_out.json comes back (level 1 settled),
  when a batch fails, or when a batch added no checkpoint line (never a loop). `stop-batch` through the agents' door
  stops it like any batch: the job's outputs come back as it ends.
"""
import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import blender_cloud  # noqa: E402
import detached  # noqa: E402

KIND = "sim-body-l1"
CLASSES = ("gpu-80gb-x2-48c", "gpu-80gb-x2", "gpu-80gb")
ENV = blender_cloud.REPO / "score/stages/physics/inside/newton_env.sh"
LAUNCHER = HERE / "on_machine.py"
LEVEL1 = "score/stages/sim_body/inside/evaluation/level1.py"
# The owner's 4 h a batch less blender_cloud's SETUP_MINUTES and a little; level 1 stops STOP_EARLY minutes before
# the job's end, so its outputs come back before the machine must go.
BATCH_MINUTES = 230
STOP_EARLY = 15
BRING_EVERY = 20
LEFT_HERE = ("evals", "start.pid", "cloud")  # cloud/: the batches' job files here
BROUGHT = ("checkpoint.jsonl", "check.jsonl", "steps.jsonl", "level1.log", "result_table.json", "result_weights.json",
           "held_out.json")
KEEP_EVALS = 2


def named_paths(value):
    """Every absolute path a job.json's value names that exists here."""
    if isinstance(value, dict):
        return {path for item in value.values() for path in named_paths(item)}
    if isinstance(value, list):
        return {path for item in value for path in named_paths(item)}
    if isinstance(value, str) and value.startswith("/") and pathlib.Path(value).exists():
        return {pathlib.Path(value)}
    return set()


def carried(run, seeds):
    """What the machine reads, each at its path: the run's entries but LEFT_HERE, the seeds root, the cases' data
    folder (their job.json files' common folder) and every other path their job.json files name."""
    jobs = [pathlib.Path(path) for path in json.loads((run / "cases.json").read_text()).values()]
    data = pathlib.Path(os.path.commonpath([job.parent for job in jobs]))
    named = set().union(*(named_paths(json.loads(job.read_text())) for job in jobs))
    outside = {path for path in named if not path.is_relative_to(data)}
    entries = [path for path in sorted(run.iterdir()) if path.name not in LEFT_HERE]
    return [*entries, seeds, data, *sorted(outside)]


def processes(run):
    """Every tuning body at once, when the run's own level1.py takes --processes; None for a run frozen before."""
    takes = "--processes" in (run / "src" / LEVEL1).read_text()
    return len(json.loads((run / "split.json").read_text())["tuning"]) if takes else None


def job(run, seeds, minutes, every, bring_every):
    """The batch's one job for blender_cloud.py: on_machine.py in the Newton env, its outputs brought back as it runs."""
    arguments = [run, "--seeds", seeds, "--minutes", minutes - STOP_EARLY, "--every", every]
    wide = processes(run)
    found = blender_cloud.job_of(LAUNCHER, [*arguments, *(["--processes", wide] if wide else [])],
                                 carried(run, seeds), [*(run / name for name in BROUGHT), run / "evals"], minutes,
                                 env=ENV)
    return {**found, "bring_every": bring_every}


def lines(path):
    return len(path.read_text().splitlines()) if path.exists() else 0


def pruned(run):
    """The run's evaluation folders here but the newest KEEP_EVALS (and every other kind of folder) removed."""
    evaluations = sorted(path for path in (run / "evals").glob("e[0-9]*") if path.is_dir())
    for path in evaluations[:-KEEP_EVALS]:
        shutil.rmtree(path)


def batch(run, seeds, options):
    """One batch through blender_cloud.py; whether it ended well."""
    folder = run / "cloud"
    folder.mkdir(exist_ok=True)
    path = folder / f"{time.strftime('%Y%m%d-%H%M%S')}.json"
    path.write_text(json.dumps(job(run, seeds, options.minutes, options.every, options.bring_every), indent=1))
    command = [str(blender_cloud.cloud_python()), str(blender_cloud.HERE / "blender_cloud.py"), str(path), "--who",
               options.who, "--classes", options.classes, "--kind", KIND, *(["--dry-run"] if options.dry_run else [])]
    ended = subprocess.run(command).returncode == 0
    pruned(run)
    return ended


def chain(run, seeds, options, one=batch):
    """Up to --batches batches; why the chain ended."""
    for number in range(options.batches):
        before = lines(run / "checkpoint.jsonl")
        if not one(run, seeds, options):
            return f"batch {number + 1} failed: its log is under blender_cloud's batches"
        if options.dry_run:
            return "priced, nothing rented"
        if (run / "held_out.json").exists():
            return f"level 1 settled in batch {number + 1}: {run / 'held_out.json'}"
        if lines(run / "checkpoint.jsonl") <= before:
            return f"batch {number + 1} added no checkpoint line: stopped"
    return f"{options.batches} batches ran; resume with another call"


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("run", type=pathlib.Path)
    parser.add_argument("--seeds", type=pathlib.Path, required=True, help="the run's seeds root (level1.py --card)")
    parser.add_argument("--who", required=True)
    parser.add_argument("--batches", type=int, default=1)
    parser.add_argument("--minutes", type=float, default=BATCH_MINUTES, help="a batch's job minutes")
    parser.add_argument("--every", type=int, default=3)
    parser.add_argument("--bring-every", type=float, default=BRING_EVERY)
    parser.add_argument("--classes", default=",".join(CLASSES))
    parser.add_argument("--dry-run", action="store_true", help="price the first batch, rent nothing")
    parser.add_argument(detached.FLAG, action="store_true", help="progress to a log, one result line at the end")
    options = parser.parse_args()
    run = options.run.resolve()
    if options.detach:
        detached.relaunch(sys.argv, "level1-cloud", [run / name for name in BROUGHT])
    if not (run / "src" / LEVEL1).is_file():
        raise SystemExit(f"{run} holds no frozen code at src/{LEVEL1}: a level 1 run runs its own src")
    print(chain(run, options.seeds.resolve(), options), flush=True)


if __name__ == "__main__":
    main()
