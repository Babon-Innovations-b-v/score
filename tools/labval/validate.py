"""LabValidation's whole final validation after one command (#98): the measure folder prepared when it holds no trial
(`prepare`, every SOMA body of --soma, in --processes parts side by side), its sim body runs on the cluster
(`cluster.py`: every trial whose out.json is not here, jobs of --per-job trials, each on its own card; a named run
resumes), then every table into one output folder: the angles (legs, pelvis, lumbar and the arms), the forces and
GRF as OpenCap scored them, the joint moments (given the reference ID opensim_reference.py made), the EMG, each per
group (all, each activity, each camera, each activity and camera), and the sim body's per-step timing per card.

    SCORE_CLOUD=k8s SCORE_SPEND_TICKET=... .venv/bin/python -m tools.labval.validate <folder> \
        --labval <LabValidation root> --out <folder> --who "<session>" [--name <run>] [--per-job 15] [--gpus 24] \
        [--soma <folder of SOMA npz> --template <clips rig.npz> [--gemx <GEM-X out> [--moge <MoGe-2 out>]]] \
        [--reference <opensim_reference.py's folder>] [--processes 2] [--no-run]

Out: report.json (`score`'s, all trials), groups.json (`labval.pooled`'s measures per group), angles, forces, emg,
grf, moments (when --reference) and timing, each as .csv and an aligned .txt. Trials that did not come back are left
out and said; the exit is 1 when any did not (the tables still written from those that did)."""
import argparse
import concurrent.futures
import functools
import json
import pathlib
import subprocess
import sys

import numpy as np

from tools import labval
from tools.labval import _grf, cluster

REPO = pathlib.Path(__file__).resolve().parents[2]
# One measure's own rows inside a group's `labval.pooled` entry: (table, the entry's keys it reads).
TABLES = (("angles", ("angles",)), ("forces", ("forces", "knee adduction", "residual pass fraction")),
          ("emg", ("emg",)))


def groups_of(trials):
    """The trials per group: all, each activity, each camera, each activity and camera (as `_grf.pooled` groups)."""
    groups = {"all": trials}
    for key in ("activity", "camera"):
        for value in sorted({trial[key] for trial in trials}):
            groups[value] = [trial for trial in trials if trial[key] == value]
    for activity in sorted({trial["activity"] for trial in trials}):
        for camera in sorted({trial["camera"] for trial in trials}):
            mine = [trial for trial in trials if trial["activity"] == activity and trial["camera"] == camera]
            if mine:
                groups[f"{activity} | {camera}"] = mine
    return groups


def flattened(value, path=()):
    """(measure path, numbers) of every leaf under `value`: a bootstrapped {"mean", "low", "high", ...} as it is, any
    other number as its mean alone."""
    if isinstance(value, dict) and "mean" in value and "low" in value:
        yield " ".join(path), value
    elif isinstance(value, dict):
        for key, inner in value.items():
            yield from flattened(inner, (*path, str(key)))
    elif isinstance(value, (bool, int, float)) and value is not None:
        yield " ".join(path), {"mean": float(value)}


def measure_rows(grouped, keys):
    """A table (header first, every cell text) of each group's measures under `keys`: mean, 95% CI, subjects, n."""
    rows = [["group", "trials", "subjects", "measure", "mean", "ci low", "ci high", "n"]]
    for group, found in grouped.items():
        for key in keys:
            if found.get(key) is None:
                continue
            for name, numbers in flattened(found[key], (key,)):
                rows.append([group, str(found["trials"]), str(found["subjects"]), name, f"{numbers['mean']:.3f}",
                             f"{numbers['low']:.3f}" if "low" in numbers else "",
                             f"{numbers['high']:.3f}" if "high" in numbers else "", str(numbers.get("values", ""))])
    return rows


def timing_rows(runs):
    """Each step's wall seconds over the runs' out.json "seconds", per card: median, range, and per frame."""
    seen = {}
    for run in runs:
        out = json.loads((run / "out.json").read_text())
        for person in out["people"].values():
            frames = len(person["frames"])
            for step, spent in person.get("seconds", {}).items():
                seen.setdefault((out.get("card") or "processor", step), []).append((spent, spent / max(frames, 1)))
    rows = [["card", "step", "runs", "median s", "min s", "max s", "median s/frame", "min s/frame", "max s/frame"]]
    for (card, step), values in seen.items():
        spent, per_frame = np.array(values).T
        rows.append([card, step, str(len(values)), *(f"{number:.3f}" for number in (
            np.median(spent), spent.min(), spent.max(), np.median(per_frame), per_frame.min(), per_frame.max()))])
    return rows


def written(rows, folder, stem):
    """`rows` as <stem>.csv and an aligned <stem>.txt in `folder`."""
    (folder / f"{stem}.csv").write_text("\n".join(",".join(f'"{cell}"' for cell in row) for row in rows) + "\n")
    widths = [max(len(row[index]) for row in rows) for index in range(len(rows[0]))]
    (folder / f"{stem}.txt").write_text("\n".join("  ".join(cell.ljust(width) for cell, width in zip(row, widths))
                                                  .rstrip() for row in rows) + "\n")


def prepared(options):
    """Every SOMA body of --soma a trial of the measure folder (`prepare`), in --processes parts side by side."""
    bodies = sorted(str(path) for path in options.soma.glob("*.npz"))
    if not bodies:
        raise SystemExit(f"{options.soma}: no SOMA npz to prepare")
    base = [sys.executable, "-m", "tools.labval", "prepare", str(options.folder), "--labval", str(options.labval),
            "--template", str(options.template)]
    base += (["--gemx", str(options.gemx)] if options.gemx else []) + (["--moge", str(options.moge)] if options.moge
                                                                       else [])
    parts = [subprocess.Popen(base + bodies[start::options.processes], cwd=REPO) for start in range(options.processes)]
    if any(part.wait() for part in parts):
        raise SystemExit(f"{options.folder}: a prepare part failed")


def ran_on_cluster(options):
    """cluster.py over the measure folder (its own process: it reads its options); whether every trial came back."""
    command = [sys.executable, "-m", "tools.labval.cluster", str(options.folder), "--who", options.who,
               "--per-job", str(options.per_job), "--gpus", str(options.gpus)]
    command += ["--name", options.name] if options.name else []
    return subprocess.run(command, cwd=REPO, check=False).returncode == 0


def scored_runs(options):
    """Every trial whose run came back, scored (`labval.scored`), and their run folders."""
    runs = sorted(path.parent for path in options.folder.glob("trials/*/out.json"))
    with concurrent.futures.ProcessPoolExecutor(options.processes) as pool:
        trials = list(pool.map(functools.partial(labval.scored, root=options.labval), runs))
    return trials, runs


def moments_report(options, runs):
    """The runs' joint moments against the reference ID (`labval.moments_scored`), pooled; None without one."""
    found = [labval.moments_scored(run, options.labval, options.reference) for run in runs]
    trials = [trial for trial in found if trial]
    return {"gaps": labval._moments.GAPS, "trials": trials,
            "pooled": labval._moments.pooled(trials) if trials else None}


def tables(options, trials, runs):
    """Every table of the scored trials into the output folder."""
    out = options.out
    grouped = {group: labval.pooled(mine)["all"] for group, mine in groups_of(trials).items()}
    (out / "report.json").write_text(json.dumps({"trials": trials, "grf": _grf.pooled(trials)}, indent=1,
                                                default=float))
    (out / "groups.json").write_text(json.dumps(grouped, indent=1, default=float))
    for stem, keys in TABLES:
        written(measure_rows(grouped, keys), out, stem)
    written(_grf.table(_grf.pooled(trials)), out, "grf")
    written(timing_rows(runs), out, "timing")
    if options.reference:
        moments = moments_report(options, runs)
        (out / "moments.json").write_text(json.dumps(moments, indent=1, default=float))
        pooled = moments["pooled"] or {}
        written(measure_rows({group: {**row, "subjects": ""} for group, row in pooled.items()},
                             ("coordinates", "opencap 15 mae %bw.ht", "peaks")), out, "moments")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("folder", type=pathlib.Path)
    parser.add_argument("--labval", required=True, type=pathlib.Path)
    parser.add_argument("--out", required=True, type=pathlib.Path)
    parser.add_argument("--who", help="the session the cluster run is booked to (needed unless --no-run)")
    parser.add_argument("--name", help="the cluster run's name: the same name resumes it")
    parser.add_argument("--per-job", type=int, default=cluster.PER_JOB)
    parser.add_argument("--gpus", type=int, default=cluster.GPUS, help="at most this many cards (jobs) at once")
    parser.add_argument("--soma", type=pathlib.Path, help="the SOMA npz to prepare when the folder holds no trial")
    parser.add_argument("--template", type=pathlib.Path, help="the clips rig.npz `prepare` reads")
    parser.add_argument("--gemx", type=pathlib.Path, help="GEM-X's out folder (`prepare --gemx`)")
    parser.add_argument("--moge", type=pathlib.Path, help="MoGe-2's out folder (`prepare --moge`)")
    parser.add_argument("--reference", type=pathlib.Path, help="opensim_reference.py's folder: the moments' reference")
    parser.add_argument("--processes", type=int, default=2)
    parser.add_argument("--no-run", action="store_true", help="score and tabulate what came back, run nothing")
    options = parser.parse_args()
    options.folder = options.folder.resolve()
    if not options.no_run and not options.who:
        parser.error("--who is needed for the cluster run")
    if not list(options.folder.glob("trials/*/job.json")):
        if not (options.soma and options.template):
            parser.error(f"{options.folder} holds no trial: give --soma and --template to prepare it")
        prepared(options)
    whole = options.no_run or ran_on_cluster(options)
    trials, runs = scored_runs(options)
    if not trials:
        raise SystemExit(f"{options.folder}: no trial came back")
    options.out.mkdir(parents=True, exist_ok=True)
    tables(options, trials, runs)
    waiting = cluster.waiting(options.folder)
    print(f"{options.out}: {len(trials)} trials scored, {len(waiting)} did not come back; angles, forces, emg, grf, "
          f"timing{', moments' if options.reference else ''} tables written")
    return 0 if whole and not waiting else 1


if __name__ == "__main__":
    sys.exit(main())
