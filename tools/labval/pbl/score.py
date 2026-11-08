"""PBL's LabValidation results (on_pbl.py's pbl.npz) scored with tools/labval's own scorer, the same way as the chain
and MOTOR (#98): the time shift on both sides' hip, knee and ankle flexion (`_score.shift`), each coordinate's RMSE,
MAE, centred MAE and r against the lab's OpenSim IK (`labval.angle_scores`), the per-subject bootstrap
(`labval.pooled_angles`), the matched envelope's 15 coordinates (`labval.MATCHED`).

    .venv/bin/python -m tools.labval.pbl.score <pbl out> --labval <LabValidation root> --moge <MoGe-2 out> \
        --gemx <GEM-X out> --chain <the chain's validate report.json> --out <report.json> --evidence <file.txt>

The mapping (`MAPPED`, `UNMAPPED`): PBL's model, humanoid_torque.xml, is LocoMuJoCo's humanoid (MIT), OpenSim's
full-body model (Rajagopal et al. 2016, after gait2392) in MuJoCo: its joints carry OpenSim's coordinate names, axes
and order, each body's frame OpenSim's (x forward, y up, z right), the left side's adduction and rotation axes
negated as OpenSim's are. LaiUhlrich2022, the lab's model, builds on the same Rajagopal model, so every coordinate
both hold is taken by name, as it is, in degrees, except:

- the knee: PBL's knee_angle turns about +z with flexion negative (its range -160 to 10 degrees, gait2392's sign), the
  lab's is flexion positive, so it is negated;
- the pelvis: PBL fits a static camera in the camera's own frame (its world is the camera: no gravity), so its
  pelvis_tilt, _list and _rotation are angles against the camera. The pelvis body's turn in the camera's frame
  (on_pbl.py, MuJoCo's kinematics) is turned onto the up of the floor MoGe-2 sees (`_floor.seen`, the chain's own
  floor of the same video), its mean heading onto the lab's (`labval.reference_heading`, as the chain's is), and read
  as OpenSim's intrinsic Z, X, Y, as the lab's ground_pelvis joint turns (`_run.zxy`). The variant "camera up" takes
  the camera's own -y as up instead (PBL's frame as it comes, a level camera assumed);
- the forearms' pro_sup: the same axis as the lab's, but its zero is not shown to be the lab's (PBL's range -34 to
  180 degrees against the lab's 0 to 160), so it keeps only the offset-free measures (cMAE and r), as the chain's
  does (`_run.OWN_ZERO`).

Not mapped: the lab's knee_angle_r/l_beta (the patella's coupled coordinate, no PBL counterpart); PBL's wrist_flex,
wrist_dev (the lab's hands are welded) and neck (the lab's model has no neck coordinate); the pelvis translations
(PBL's are in the camera's frame and metres of a scaled body, the chain's are not scored either)."""
import argparse
import concurrent.futures
import json
import pathlib
import re

import numpy as np

from tools import labval
from tools.labval import _files, _floor, _run, _score

# lab coordinate -> (PBL joint, sign): every coordinate both models hold but the pelvis (module docstring).
MAPPED = {**{f"{stem}_{side}": (f"{stem}_{side}", 1.0) for side in "rl"
             for stem in ("hip_flexion", "hip_adduction", "hip_rotation", "ankle_angle", "subtalar_angle",
                          "mtp_angle", "arm_flex", "arm_add", "arm_rot", "elbow_flex", "pro_sup")},
          **{f"knee_angle_{side}": (f"knee_angle_{side}", -1.0) for side in "rl"},
          **{name: (name, 1.0) for name in _run.LUMBAR}}
UNMAPPED = {"knee_angle_r_beta": "the patella's coupled coordinate; PBL's knee has none",
            "knee_angle_l_beta": "the patella's coupled coordinate; PBL's knee has none",
            "wrist_flex_r/l, wrist_dev_r/l (PBL)": "the lab's hands are welded: no wrist in its IK",
            "neck_extension, neck_bending, neck_rotation (PBL)": "the lab's model has no neck coordinate",
            "pelvis_tx, pelvis_ty, pelvis_tz": "PBL's are in the camera's frame; translations are not scored"}
CAMERA_UP = np.array([0.0, -1.0, 0.0])  # OpenCV's axes: y down
# OpenCV's camera axes (y down, z forward) to a y-up camera frame: the half turn about x, so a near-level camera's up
# is a small least turn from +y (an up exactly opposite +y has no least turn).
Y_UP = np.diag([1.0, -1.0, -1.0])
NAME = re.compile(r"^(subject\d+)_(.+)_(Cam\d+)$")


def coordinates(saved, up, lab_heading):
    """{lab coordinate: degrees every frame} of one PBL result (pbl.npz's arrays): `MAPPED` by name and sign, the
    pelvis' tilt, list and rotation from its turn in the camera levelled onto `up` (the floor's normal, camera
    axes) with its mean heading on `lab_heading` (radians)."""
    names = [str(name) for name in saved["joint_names"]]
    qpos = np.asarray(saved["qpos"], dtype=float)
    found = {lab: sign * np.degrees(qpos[:, names.index(joint)]) for lab, (joint, sign) in MAPPED.items()}
    up = Y_UP @ (np.asarray(up, dtype=float) / np.linalg.norm(up))
    level = _floor.least_turn(up, np.array([0.0, 1.0, 0.0])) @ Y_UP
    pelvis = np.einsum("ab,fbc->fac", level, np.asarray(saved["pelvis_turns"], dtype=float))
    turned = _run.about_up(lab_heading - _run.heading(pelvis)) @ pelvis
    found.update(zip(_run.PELVIS, _run.zxy(turned).T))
    return found


def floor_up(moge, gemx):
    """The up of the floor MoGe-2 sees in a video (camera axes), the chain's own (`_floor.seen` of its MoGe-2 and
    GEM-X results); None when it saw too little floor."""
    with np.load(moge) as seen_map, np.load(gemx) as person:
        found = _floor.seen(dict(seen_map), dict(person))
    return None if found is None else np.array(found["normal"])


def scored(folder, root, up):
    """One video's angle measures, as `labval.scored` gives the chain's: the shift on the legs' flexions, the lab's
    heading on the shifted frames, then every mapped coordinate against the IK."""
    subject, trial, camera = NAME.match(folder.name).groups()
    with np.load(folder / "pbl.npz") as saved:
        saved = dict(saved)
    times = np.asarray(saved["times"], dtype=float)
    ik_times, ik_columns = _files.ik(_files.found(pathlib.Path(root) / subject, "ik", trial))
    lag = _score.shift(times, coordinates(saved, up, 0.0), ik_times, ik_columns)
    at = times + lag
    lab_heading = labval.reference_heading({name: _score.resampled(ik_times, ik_columns[name], at)
                                            for name in _run.PELVIS})
    return {"name": folder.name, "subject": subject, "trial": trial, "camera": camera,
            "activity": labval.activity_of(trial), "shift s": lag,
            "angles": labval.angle_scores(times, coordinates(saved, up, lab_heading), ik_times, ik_columns, lag)}


def both(folder, root, moge_root, gemx_root):
    """(the video's measures on the seen floor or None when it saw none, on the camera's up)."""
    subject, trial, camera = NAME.match(folder.name).groups()
    up = floor_up(pathlib.Path(moge_root) / folder.name / "moge.npz",
                  pathlib.Path(gemx_root) / subject / trial / camera / "raw.npz")
    return (None if up is None else scored(folder, root, up)), scored(folder, root, CAMERA_UP)


def matched(trials, metric):
    """The matched envelope's `metric` (mae or cmae) pooled over its 15 coordinates, bootstrapped by subject."""
    found = {}
    for trial in trials:
        found.setdefault(trial["subject"], []).extend(trial["angles"][name][metric] for name in labval.MATCHED
                                                       if name in trial["angles"])
    return _score.bootstrapped(found)


def envelope(trials):
    """The matched envelope's trials: Cam1, no drop jumps."""
    return [trial for trial in trials if trial["camera"] == "Cam1" and trial["activity"] != "drop jump"]


def shown(value):
    return f"{value['mean']:.2f} [{value['low']:.2f}, {value['high']:.2f}]"


def summary_rows(groups):
    """Lines of the matched MAE and cMAE of each (label, trials) group."""
    lines = [f"{'':44}{'trials':>7}{'subjects':>9}   {'matched MAE deg':<24}{'matched cMAE deg':<24}"]
    for label, trials in groups:
        lines.append(f"{label:44}{len(trials):>7}{len({trial['subject'] for trial in trials}):>9}   "
                     f"{shown(matched(trials, 'mae')):<24}{shown(matched(trials, 'cmae')):<24}")
    return lines


def coordinate_rows(columns):
    """Lines of each coordinate's MAE, cMAE and r for each (label, trials) column."""
    pooled = [(label, labval.pooled_angles(trials)["coordinates"]) for label, trials in columns]
    names = sorted({name for _, found in pooled for name in found})
    head = f"{'coordinate':22}" + "".join(f"{label + ' MAE':>16}{'cMAE':>7}{'r':>7}" for label, _ in pooled)
    lines = [head]
    for name in names:
        row = f"{name + (' *' if name in labval.MATCHED else ''):22}"
        for _, found in pooled:
            value = found.get(name, {})
            mae = f"{value['mae']['mean']:.2f}" if "mae" in value else "-"
            cmae = f"{value['cmae']['mean']:.2f}" if "cmae" in value else "-"
            r = f"{value['r']:.2f}{'†' if value.get('dagger') else ''}" if value else "-"
            row += f"{mae:>16}{cmae:>7}{r:>7}"
        lines.append(row)
    return lines


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("pbl", type=pathlib.Path)
    parser.add_argument("--labval", type=pathlib.Path, required=True)
    parser.add_argument("--moge", type=pathlib.Path, required=True)
    parser.add_argument("--gemx", type=pathlib.Path, required=True)
    parser.add_argument("--chain", type=pathlib.Path, required=True, help="the chain's validate report.json")
    parser.add_argument("--out", type=pathlib.Path, required=True)
    parser.add_argument("--evidence", type=pathlib.Path, required=True)
    parser.add_argument("--header", type=pathlib.Path, help="the evidence's opening lines (run, spend, coverage)")
    parser.add_argument("--processes", type=int, default=8)
    options = parser.parse_args()
    folders = sorted(path.parent for path in options.pbl.glob("*/pbl.done.json"))
    floor, camera, failed = [], [], {}
    with concurrent.futures.ProcessPoolExecutor(options.processes) as pool:
        futures = {pool.submit(both, folder, options.labval, options.moge, options.gemx): folder for folder in folders}
        for future in concurrent.futures.as_completed(futures):
            try:
                on_floor, on_camera = future.result()
            except Exception as error:  # one video's fault is said, the rest still scored
                failed[futures[future].name] = repr(error)
                continue
            camera.append(on_camera)
            if on_floor is None:
                failed[futures[future].name] = "MoGe-2 saw too little floor (scored on the camera's up only)"
            else:
                floor.append(on_floor)
    chain = list(json.loads(options.chain.read_text()).values())
    names = {trial["name"] for trial in floor}
    common_chain = [trial for trial in chain if trial["name"] in names]
    common_pbl = [trial for trial in floor if trial["name"] in {trial["name"] for trial in chain}]
    options.out.write_text(json.dumps({"floor": floor, "camera up": camera, "failed": failed}, default=float))
    lines = [*(options.header.read_text().splitlines() if options.header else []), "",
             f"Scored: {len(folders)} PBL results, {len(floor)} on the seen floor, {len(camera)} on the camera's up; "
             f"not scored on the floor: {len(failed)}" + "".join(f"\n  {name}: {why}" for name, why in
                                                                  sorted(failed.items())), "",
             "## matched envelope (Cam1, no drop jumps; the 15 coordinates of labval.MATCHED)",
             *summary_rows([("PBL, seen floor", envelope(floor)), ("PBL, camera up", envelope(camera)),
                            ("chain (labval-final-2026-11-07), all its", envelope(chain)),
                            ("PBL, seen floor, trials both have", envelope(common_pbl)),
                            ("chain, trials both have", envelope(common_chain))]),
             "OpenCap Monocular (Gilon et al. 2026, arXiv:2603.24733, as the paper cites it): 4.8 deg MAE on its matched set.", "",
             "## every camera and activity",
             *summary_rows([("PBL, seen floor", floor), ("PBL, camera up", camera), ("chain, all its", chain),
                            ("PBL, seen floor, trials both have", common_pbl), ("chain, trials both have", common_chain)]),
             "", "## each coordinate, matched envelope (* matched; † the reference's range under 15 deg)",
             *coordinate_rows([("PBL", envelope(floor)), ("chain", envelope(chain))]),
             "", "## each coordinate, every camera and activity",
             *coordinate_rows([("PBL", floor), ("chain", chain)]),
             "", "## mapping (tools/labval/pbl/score.py)",
             *(f"  {lab} <- PBL {joint}{' (negated)' if sign < 0 else ''}" for lab, (joint, sign) in MAPPED.items()),
             "  pelvis_tilt, pelvis_list, pelvis_rotation <- PBL's pelvis body turn in the camera, levelled on the "
             "seen floor, heading on the lab's, intrinsic ZXY",
             "  pro_sup_r, pro_sup_l: cMAE and r only (their zero not shown to be the lab's)",
             "not mapped:", *(f"  {name}: {why}" for name, why in UNMAPPED.items())]
    options.evidence.write_text("\n".join(lines) + "\n")
    print(f"pbl score: {len(floor)} trials on the floor, {len(camera)} on the camera's up, {len(failed)} said; "
          f"envelope matched MAE {matched(envelope(floor), 'mae')['mean']:.2f}; {options.evidence}")


if __name__ == "__main__":
    main()
