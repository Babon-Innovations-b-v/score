"""tools/labval's commands, in the score venv on this PC (nothing here runs a model: on_gemx.py and the sim body run on
rented cards).

    .venv/bin/python -m tools.labval prepare <folder> --labval <LabValidation root> --template <clips rig.npz> \
        [--gemx <GEM-X out> [--moge <MoGe-2 out>]] <soma.npz> [<soma.npz> ...]
    .venv/bin/python -m tools.labval score <folder> [<folder> ...] --labval <LabValidation root> --out <report.json> \
        [--processes N] [--static <folder>]
    .venv/bin/python -m tools.labval grf-tables <report.json> --out <folder>
    .venv/bin/python -m tools.labval moments <folder> [<folder> ...] --labval <root> --reference <made> --out <json>

prepare: each on_gemx.py npz, named subject<N>_<trial>_<Cam>.npz, as a trial of measure folder <folder> (its job
names the fetched MyoFullBody, sim_body.fetched: a free download once). score: every trial of <folder> whose run came
back (its out.json) scored against LabValidation and pooled (a trial in a later folder replaces its namesake in an
earlier one), with --static each trial's angles read from its subject's standing pose (`labval.neutral`, the static
trial's run on the same camera); one line said, the report written. grf-tables: the report's ground reaction forces as OpenCap scored
them (`_grf`), grf.csv and grf.txt per group (all, activity, camera, activity and camera) under <folder>. moments: the
same runs' joint moments against the reference ID opensim_reference.py made (`_moments`), pooled the same way."""
import argparse
import concurrent.futures
import functools
import json
import pathlib

import numpy as np

from score.stages import sim_body
from tools import labval
from tools.labval import _grf


def prepare(options):
    """Every given SOMA body a trial of the measure folder."""
    with np.load(options.template) as saved:
        template = {key: saved[key] for key in ("names", "parents", "bind", "faces")}
    model = sim_body.fetched()
    for path in options.soma:
        name = pathlib.Path(path).stem
        seen = {}
        if options.gemx:
            subject, trial, camera = labval.subject_of(name)
            with np.load(options.gemx / subject / trial / camera / "contact_ik.npz") as saved:
                seen["gemx"] = dict(saved)
        if options.moge:
            with np.load(options.moge / name / "moge.npz") as saved:
                seen["moge"] = dict(saved)
        with np.load(path) as saved:
            labval.prepared(dict(saved), template, options.labval, name, model, options.folder, **seen)
    print(f"{options.folder}: {len(options.soma)} trials prepared, scripts/go.sh written")


def score(options):
    """Every run that came back scored, then pooled, into the report."""
    runs = {path.parent.name: path.parent for folder in options.folder
            for path in sorted(pathlib.Path(folder).glob("trials/*/out.json"))}
    with concurrent.futures.ProcessPoolExecutor(options.processes) as pool:
        trials = list(pool.map(functools.partial(labval.scored, root=options.labval, static=options.static),
                               [runs[name] for name in sorted(runs)]))
    report = {"trials": trials, "pooled": labval.pooled(trials) if trials else None,
              "grf": _grf.pooled(trials) if trials else None}
    pathlib.Path(options.out).write_text(json.dumps(report, indent=1, default=float))
    matched = report["pooled"]["all"]["angles"]["matched mae"] if trials else None
    print(f"{options.out}: {len(trials)} trials scored"
          + (f", matched MAE {matched['mean']:.2f} deg (95% CI {matched['low']:.2f} to {matched['high']:.2f})"
             if matched else ""))


def grf_tables(options):
    """The report's GRF rows written as grf.csv and grf.txt."""
    report = json.loads(pathlib.Path(options.report).read_text())
    rows = _grf.table(report["grf"])
    options.out.mkdir(parents=True, exist_ok=True)
    (options.out / "grf.csv").write_text("\n".join(",".join(f'"{cell}"' for cell in row) for row in rows) + "\n")
    widths = [max(len(row[index]) for row in rows) for index in range(len(rows[0]))]
    (options.out / "grf.txt").write_text("\n".join("  ".join(cell.ljust(width) for cell, width in zip(row, widths))
                                                   .rstrip() for row in rows) + "\n")
    print(f"{options.out}: grf.csv and grf.txt, {len(rows) - 1} rows")


def moments(options):
    """Every run that came back with a reference ID scored on its joint moments, then pooled, into the report."""
    runs = sorted(path.parent for folder in options.folders for path in pathlib.Path(folder).glob("trials/*/out.json"))
    trials = [found for found in (labval.moments_scored(run, options.labval, options.reference) for run in runs)
              if found]
    report = {"gaps": labval._moments.GAPS, "trials": trials,
              "pooled": labval._moments.pooled(trials) if trials else None}
    pathlib.Path(options.out).write_text(json.dumps(report, indent=1, default=float))
    fifteen = report["pooled"]["all"]["opencap 15 mae %bw.ht"] if trials else None
    print(f"{options.out}: {len(trials)} of {len(runs)} runs scored on moments"
          + (f", OpenCap's 15 MAE {fifteen['mean']:.2f} %BW*ht (95% CI {fifteen['low']:.2f} to {fifteen['high']:.2f})"
             if fifteen else ""))


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    making = commands.add_parser("prepare")
    making.add_argument("folder", type=pathlib.Path)
    making.add_argument("soma", nargs="+", type=pathlib.Path)
    making.add_argument("--labval", required=True, type=pathlib.Path)
    making.add_argument("--template", required=True, type=pathlib.Path)
    making.add_argument("--gemx", type=pathlib.Path, help="GEM-X's out folder: each trial's Contact/IK result")
    making.add_argument("--moge", type=pathlib.Path, help="MoGe-2's out folder (moge_cluster.py): the floor seen")
    scoring = commands.add_parser("score")
    scoring.add_argument("folder", nargs="+", type=pathlib.Path)
    scoring.add_argument("--labval", required=True, type=pathlib.Path)
    scoring.add_argument("--out", required=True, type=pathlib.Path)
    scoring.add_argument("--processes", type=int, default=1)
    scoring.add_argument("--static", type=pathlib.Path, help="the measure folder of the subjects' static runs: each "
                         "trial's angles read from its subject's own standing pose on its camera")
    tables = commands.add_parser("grf-tables")
    tables.add_argument("report", type=pathlib.Path)
    tables.add_argument("--out", required=True, type=pathlib.Path)
    scoring_moments = commands.add_parser("moments")
    scoring_moments.add_argument("folders", nargs="+", type=pathlib.Path)
    scoring_moments.add_argument("--labval", required=True, type=pathlib.Path)
    scoring_moments.add_argument("--reference", required=True, type=pathlib.Path)
    scoring_moments.add_argument("--out", required=True, type=pathlib.Path)
    options = parser.parse_args()
    {"prepare": prepare, "score": score, "grf-tables": grf_tables, "moments": moments}[options.command](options)


if __name__ == "__main__":
    main()
