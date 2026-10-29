"""_case.py <table.json> <weights.json> <out root> <case>=<job.json> ...: one SOMA body's levels 2 and 3 for level 1's
runner: the landmark set replaced in place by the table's rows and the global weights by the weights file's, each
group end's centre moved by <out root>/rest.json's offsets (the fit's targets, the sizing's lengths and the measure's
joints all read it) and the calibration table read again at rest from them (on SOMA's template rig), the
person constants solved once from every clip of the body together (held for its later clips), then each clip's pose
per frame, then per clip the honest measures (_measure.measures) and per landmark its leftover and its fitted move
off its link. Writes <out root>/<case>/measures.json (unrounded, the solver's) and m.json (its rounded copy, people's).
Newton's Python (mujoco); run by the runner, one process per body."""
import json
import pathlib
import sys
import time

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import calibration  # noqa: E402
import fit  # noqa: E402
import mujoco  # noqa: E402
import sim_body  # noqa: E402
from calibration import _measure as rest_measure  # noqa: E402
import evaluation  # noqa: E402
from evaluation import _measure  # noqa: E402
from fit import _frames  # noqa: E402
from landmarks import CENTRES, LANDMARKS, marker  # noqa: E402

FIELDS = ("face", "barycentric", "segment", "body", "bone point", "link", "trust", "solver")


def load_table(path):
    """Replace the landmark set in place (every module reads the same dict) by the table file's rows."""
    rows = json.loads(pathlib.Path(path).read_text())
    LANDMARKS.clear()
    LANDMARKS.update({name: tuple(tuple(row[key]) if isinstance(row[key], list) else row[key] for key in FIELDS)
                      for name, row in rows.items()})


def load_centres(offsets):
    """Move each group end's centre in place by its offset ({centre: [3]} m, its body's frame, source model): the
    landmark table's (`CENTRES`, every reader's) and the measure's frozen copy alike."""
    for table in (CENTRES, _measure.CENTRES):
        for name, offset in offsets.items():
            body, local = table[name]
            table[name] = (body, tuple(float(value) for value in np.asarray(local, dtype=float) + offset))


def recalibrated(folder, rig):
    """The calibration table read again at rest from the current centres (MyoFullBody's default pose in `folder`
    against SOMA's template `rig`), in place: a rest-pose table, never fitted to motion."""
    calibration.TABLE.update({group: tuple(quaternion) for group, quaternion in rest_measure.measured(folder, rig).items()})


def leftovers(model, angles, scales, points):
    """Per solver landmark: median and p95 over frames of |target - marker| (mm) and its move off its link (mm)."""
    data = mujoco.MjData(model)
    order = fit.solver_marks()
    sites = {name: mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, f"mark:{name}") for name in order}
    sites = {name: site for name, site in sites.items() if site >= 0}
    gaps = {name: [] for name in sites}
    locals_ = {name: [] for name in sites}
    for frame, qpos in enumerate(angles):
        data.qpos[:] = qpos
        mujoco.mj_kinematics(model, data)
        for name, site in sites.items():
            gap = points[frame, order.index(name)] - data.site_xpos[site]
            gaps[name].append(1000 * float(np.linalg.norm(gap)))
            turn = data.xmat[model.site_bodyid[site]].reshape(3, 3)
            locals_[name].append(1000 * turn.T @ gap)
    moves = {name: 1000 * float(np.linalg.norm(model.site_pos[site] - marker(name, scales[LANDMARKS[name][3]])))
             for name, site in sites.items()}
    return {name: {"median mm": round(float(np.median(gap)), 2), "p95 mm": round(float(np.percentile(gap, 95)), 2),
                   "move mm": round(moves[name], 2),
                   "mean body mm": [round(float(value), 3) for value in np.mean(locals_[name], axis=0)],
                   "body move mm": [round(1000 * float(value), 3) for value in
                                    model.site_pos[sites[name]] - marker(name, scales[LANDMARKS[name][3]])],
                   "mad mm": round(float(np.median(np.linalg.norm(np.asarray(locals_[name])
                                                                    - np.median(locals_[name], axis=0), axis=1))), 3)}
            for name, gap in gaps.items()}


def held_constants():
    """fit.constants solved on the body's first case, then given back unchanged (level 2 once per body)."""
    solve, kept = fit.constants, []

    def once(fitting, recordings):
        if not kept:
            kept.append(solve(fitting, recordings))
        return kept[0]
    fit.constants = once


def fitted_case(job_path, out, recordings):
    """One clip of the body: levels 2 (held) and 3, its follow measures and landmark leftovers into out/measures.json
    (unrounded, the solver's) and out/m.json (rounded, the copy people read)."""
    out.mkdir(parents=True, exist_ok=True)
    job = json.loads(job_path.read_text())
    person = job["people"][0]
    person["recordings"] = recordings
    targets = np.load(person["targets"])
    worlds = targets["world"]
    rig = {**person["rig"], "points": targets["points"], "faces": targets["faces"], "weights": targets["weights"]}
    began = time.time()
    record, scales, model, angles = sim_body.fitted_person(job, person, rig, worlds, out / f"{person['name']}.xml")
    seconds = time.time() - began
    found = _measure.measures(model, angles, rig, person["segments"], worlds, scales)
    _, points = fit.targets(rig, person["segments"], worlds, fit.followed(person["segments"]))
    found["landmarks"] = leftovers(model, angles, scales, points)
    found["fit seconds"] = round(seconds, 1)
    found["recordings"] = recordings
    found["constants"] = record["fit"]["constants"]
    (out / evaluation.SOLVED).write_text(json.dumps(found, indent=1))
    (out / "m.json").write_text(json.dumps(evaluation.rounded(found), indent=1))
    print("done", out, found["joints mm"], found["turns deg"], found["bones outside all %"], seconds, flush=True)


def load_weights(path):
    """Level 1's global weights ({"marker goal", "end weight"}) set where levels 2 and 3 read them at call time."""
    weights = json.loads(pathlib.Path(path).read_text())
    _frames.MARKER_GOAL = float(weights["marker goal"])
    fit.END_WEIGHT = float(weights["end weight"])


def main():
    table, weights, root = sys.argv[1], sys.argv[2], pathlib.Path(sys.argv[3])
    cases = dict(given.split("=", 1) for given in sys.argv[4:])
    load_table(table)
    load_weights(weights)
    rest = json.loads((root / "rest.json").read_text())
    load_centres(rest["centres"])
    recalibrated(json.loads(pathlib.Path(next(iter(cases.values()))).read_text())["model"], rest["rig"])
    held_constants()
    recordings = [json.loads(pathlib.Path(job).read_text())["people"][0]["targets"] for job in cases.values()]
    for case, job in cases.items():
        fitted_case(pathlib.Path(job), root / case, recordings)


if __name__ == "__main__":
    main()
