"""MOTOR step 3 (#98): the tuning of stage A's settings on LabValidation's training subjects, as measure folders.

    .venv/bin/python -m tools.labval.motor_tune make <source> <root> --variant NAME='{"foot_stiffness": 2e7}' ... \
        [--landmarks weights.json] [--held-out]
    .venv/bin/python -m tools.labval.motor_tune own <folder> <out>
    .venv/bin/python -m tools.labval.motor_tune weights <folder> ... --out weights.json

`make` writes one measure folder a variant under <root> (<root>/<NAME>/trials/<trial>/: the source's targets and
record, its job.json with "motor": "dynamics", the variant's "motor settings" and, with --landmarks, the learned
"motor landmarks"), each run on the cluster by `cluster.py` and scored by `validate --no-run`. Only the training
subjects (TRAINING) are tuned on: a held-out subject's trial is refused unless --held-out (the report's run, its
settings already chosen). `own` writes the folder whose pushes are stage A's own contact forces (its record's ground
force by side), so `validate` scores MOTOR's own GRF against the plates. `weights` is B3D's EM step for the landmarks
(Cotton et al. 2026): each landmark's weight 1 / its pooled mean squared miss over the training trials' solves
(stage A's "landmark errors mm"), over the landmarks' median, inside WEIGHT_RANGE; never against the lab's angles."""
import argparse
import json
import pathlib
import re
import shutil
import sys

import numpy as np

TRAINING = (2, 3, 4, 5)  # LabValidation's subjects tuned on; 7-11 are held out for the report
WEIGHT_RANGE = (0.2, 5.0)  # a landmark's learned weight against the median's, at most this far either way


def subject(name):
    """A trial's subject number (subject<N>_...)."""
    found = re.match(r"subject(\d+)_", name)
    if not found:
        raise ValueError(f"{name}: not a LabValidation trial name")
    return int(found.group(1))


def stage_a(out):
    """Every person's MOTOR stage A record in a run's out.json (its model's record: `motor` / `dynamics`), by name."""
    found = {}
    for name, entry in out["people"].items():
        dynamics = entry["model"].get("motor", {}).get("dynamics")
        if dynamics is None:
            raise ValueError(f"{name}: no MOTOR stage A record in its run")
        found[name] = dynamics
    return found


def made(source, root, variants, landmarks=None, held_out=False):
    """One measure folder a variant (name, settings) under `root` from the source's trials; their paths."""
    trials = sorted(path.parent for path in pathlib.Path(source).glob("trials/*/job.json"))
    refused = [trial.name for trial in trials if subject(trial.name) not in TRAINING]
    if refused and not held_out:
        raise SystemExit(f"held-out trials {refused}: tuning runs on subjects {TRAINING} only (--held-out to report)")
    folders = []
    for name, settings in variants:
        folder = pathlib.Path(root) / name
        for trial in trials:
            out = folder / "trials" / trial.name
            out.mkdir(parents=True, exist_ok=True)
            for kept in ("targets.npz", "record.json"):
                shutil.copy2(trial / kept, out / kept)
            job = json.loads((trial / "job.json").read_text().replace(str(pathlib.Path(source).resolve()),
                                                                       str(folder.resolve())))
            job["motor"], job["motor settings"] = "dynamics", settings
            if landmarks:
                job["motor landmarks"] = landmarks
            for person in job["people"]:
                if not person["targets"].startswith(str(folder.resolve())):
                    raise SystemExit(f"{trial.name}: its targets {person['targets']} outside {folder}")
            (out / "job.json").write_text(json.dumps(job))
        folders.append(folder)
    return folders


def owned(folder, out):
    """`out`: `folder`'s trials with each foot's push stage A's own contact force, the rest linked as it came."""
    from tools.labval import _run
    for trial in sorted(pathlib.Path(folder).glob("trials/*/out.json")):
        target = pathlib.Path(out) / "trials" / trial.parent.name
        target.mkdir(parents=True, exist_ok=True)
        run = json.loads(trial.read_text())
        records = stage_a(run)
        for name, entry in run["people"].items():
            for row, sides in zip(entry["frames"], records[name]["ground force by side N"]):
                for side, force in zip(("left", "right"), sides):  # sim_body.FEET_SIDES' order
                    row["touches"][_run.FEET[side]] = list(force) + [0.0, 0.0, 0.0]
        (target / "out.json").write_text(json.dumps(run))
        for other in ("out.npz", "record.json", "job.json"):
            if not (target / other).exists():
                (target / other).symlink_to((trial.parent / other).resolve())


def learned(folders):
    """Each landmark's weight from the training trials' stage A misses (`weights`' docstring), by its site's name."""
    pooled = {}
    for folder in folders:
        for trial in sorted(pathlib.Path(folder).glob("trials/*/out.json")):
            if subject(trial.parent.name) not in TRAINING:
                raise SystemExit(f"{trial.parent.name}: a held-out trial; the landmarks learn on {TRAINING} only")
            for record in stage_a(json.loads(trial.read_text())).values():
                for site, miss in record["landmark errors mm"].items():
                    pooled.setdefault(site, []).append(float(miss) ** 2)
    if not pooled:
        raise SystemExit(f"{[str(folder) for folder in folders]}: no stage A landmark misses")
    variance = {site: float(np.mean(squares)) for site, squares in pooled.items()}
    middle = float(np.median(list(variance.values())))
    return {site: round(float(np.clip(middle / max(value, 1e-12), *WEIGHT_RANGE)), 4)
            for site, value in sorted(variance.items())}


def variant(text):
    """NAME=<json settings> as (name, settings)."""
    name, _, settings = text.partition("=")
    if not name or not settings:
        raise argparse.ArgumentTypeError(f"{text}: give NAME='{{...}}'")
    return name, json.loads(settings)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    making = commands.add_parser("make")
    making.add_argument("source", type=pathlib.Path)
    making.add_argument("root", type=pathlib.Path)
    making.add_argument("--variant", type=variant, action="append", required=True)
    making.add_argument("--landmarks", type=pathlib.Path, help="`weights`' file: the learned landmark weights")
    making.add_argument("--held-out", action="store_true", help="the report's run: held-out trials allowed")
    owning = commands.add_parser("own")
    owning.add_argument("folder", type=pathlib.Path)
    owning.add_argument("out", type=pathlib.Path)
    weighing = commands.add_parser("weights")
    weighing.add_argument("folders", nargs="+", type=pathlib.Path)
    weighing.add_argument("--out", required=True, type=pathlib.Path)
    options = parser.parse_args()
    if options.command == "make":
        landmarks = json.loads(options.landmarks.read_text()) if options.landmarks else None
        folders = made(options.source, options.root, options.variant, landmarks, options.held_out)
        print(f"{len(folders)} variant folders under {options.root}: {', '.join(folder.name for folder in folders)}")
    elif options.command == "own":
        owned(options.folder, options.out)
        print(f"{options.out}: stage A's own contact as the pushes")
    else:
        weights = learned(options.folders)
        options.out.write_text(json.dumps(weights, indent=1))
        print(f"{options.out}: {len(weights)} landmark weights, {min(weights.values())} to {max(weights.values())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
