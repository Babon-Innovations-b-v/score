"""labval: a synthetic LabValidation trial (its IK, plates, markers, EMG and metadata written in the dataset's own
formats) and a synthetic sim body run of it (a known time shift, a known 2 degree offset on the legs, the pelvis and
torso turned 40 degrees about up, the humeri at known shoulder angles on the torso, the elbows 2 degrees over, the
forearms on MyoFullBody's zero (90 degrees under LaiUhlrich2022's), the plates' own forces and knee lever arms) score as
built: the shift found to under a millisecond, the legs' and elbows' MAE 2 and centred MAE 0, the pelvis, lumbar and
shoulders 0, the forearms' centred MAE 0 with no MAE, the forces and the knee adduction
moment equal, the residual passing, the vasti on when the EMG says; the hand cases (a knee moment of 35 N m, a shank
from four markers, the bootstrap's bounds, an EMG channel's muscle, an envelope's r against a scaled and a mirrored copy, the † flag) give their worked answers; the shift is found as well
on an IK covering only a window of the run and 0.4 s off on one gait cycle, an empty third plate is left out and a loaded one refused; a GEM-X
SOMA body becomes the sim body's rig with its skin unmoved but for its height, the fingers' weight on the hand, the
bind on the template's frames and the float of 0.3 m taken off; the measure folder's go.sh runs only the trials not
yet done; a floor MoGe-2 sees 5 degrees off GEM-X's level is found so and levelled onto the world's up; a run's
generalized forces 1 %BW*ht over a reference ID score MAE 1 on all 19 coordinates, and the moments' peaks give their
worked answers; a drop jump's box and a sit-to-stand's seat lie under what rests on them and clear of the feet on the
floor, and the box's push is no plate's; MOTOR's tuning folders carry their settings, refuse a held-out subject and
learn the landmarks' weights as B3D's EM step. Synthetic inputs only: no number here is a result.

Breaks, each applied once, seen red, reverted (2026-11-06):
- _score.shift's `times + shift` made `times - shift`: the shift comes out -0.0123 s, the legs' MAE far over 2.
- _score.angle_measures' cmae `error - error.mean()` made `error`: the legs' centred MAE is 2.
- _score.knee_adduction's left sign dropped: the left knee's moment is -35 N m.
- _score.marker_shank's left `mknee - knee` made `knee - mknee`: the left shank points backward.
- _score.bootstrapped's `counts[picks].sum(axis=1)` made `counts.sum()`: the bounds leave 1 to 3.
- _soma.reframed's world `@ turn` dropped: the skin moves (the bind turned, the world not).
- _soma.merged's `+=` made `=`: the hand's points lose the thumb's share.
- _soma.floored's move dropped: the feet stand 0.3 m up.
- __init__.force_scores' `turn` made the identity: the anterior force is the 40 degree turned one's.
- _run.angles' `lab_heading - heading(pelvis)` made `lab_heading`: the pelvis' angles are the turned body's.
- _job.GO's `[ -f "${trial}out.json" ] ||` dropped: the done trial runs again.
- _files.forces' `lacking` check dropped: a plate without its left torque is read without a word.
- _files.forces' `and not np.any(values)` dropped (any unsided column left out): a loaded third plate is read.
- _files.forces' empty-plate `continue` dropped: the trial's empty third plate raises 'is no foot's force'.
- _score.centred_cost's `inside.sum() / shorter` made `inside.mean()`: the IK's window never covers the run.
- _score.OVERLAP made 0.8: on one gait cycle's 1.3 s the shift stops at 0.257 s, short of the 0.4 s built in.
- _files.ik's `name in TRANSLATIONS` made `name.startswith('pelvis_t')`: pelvis_tilt is left in radians.
- _files.WHERE's "metadata.yaml" dropped: the store copy's subject has no mass.
- _score.timing_measures' r `np.sqrt(...)` dropped (2026-11-07): the scaled copy's r is 0.0054, not 1, and the synthetic vasti's 0.17.
- cluster.line's `|| echo` dropped: one failed trial ends its job's later trials.
- cluster.job's `sum(clips(trial) ...)` made `len(trials)`: a 540-frame trial gets one clip's minutes (2026-11-07).
- cluster.job's outputs made each trial's out.json: a failed trial's missing file fails its whole job.
- cluster.main's `parallel=options.gpus` dropped: the run takes every card it can, not --gpus (2026-11-07).
- validate.ran_on_cluster's `"--gpus", str(options.gpus)` dropped: cluster.py runs at its own 24, not --gpus 7.
- _run.coordinate_column's `_<name>` ending dropped: a cluster run's Newton path names (`..._j2_knee_angle_r`) lack
  every leg coordinate.

Breaks, each applied once, seen red, reverted (2026-11-07, the arms):
- _run.SHOULDERS' left signs made [1, 1, 1]: arm_add_l and arm_rot_l come out negated.
- _run.angles' shoulder `np.swapaxes(torso, 1, 2) @` dropped: the shoulders are the humeri's turns in the lab.
- __init__.angle_scores' OWN_ZERO filter dropped: pro_sup scores an MAE of 90, the models' zeros' difference.

Breaks, each applied once, seen red, reverted (2026-11-07, a foot never pushed, #98):
- _score.stance_carried's `predicted[loaded]` made `predicted[inside]`: a foot lifted for three of four stance frames
  carries 0.4, not 0.25.
- __init__.pooled_forces' "r trials" made `len(trials)`: a foot the run never pushes counts as scored.

Breaks, each applied once, seen red, reverted (2026-11-07, the forces as OpenCap scored them, #98):
- _grf.scores' force `@ np.asarray(turn).T` dropped: the anterior-posterior and medial-lateral MAE are the 40 degree
  turned push's.
- _grf.directions' `np.cross(forward, up)` made `np.cross(up, forward)`: forward x reads to the subject's left.
- _grf.cutoff_of's Nyquist hold dropped: a 30 Hz run's drop jump is filtered at 30 Hz.
- _grf.stances' finite-neighbour check dropped: a stance begun before the plate's window counts as whole.

Breaks, each applied once, seen red, reverted (2026-11-08, MOTOR step 3's tuning folders, #98):
- motor_tune.made's held-out refusal dropped: subject7's trial is tuned on.
- motor_tune.learned's `middle / max(value, 1e-12)` made `max(value, 1e-12) / middle`: the worst landmark weighs most.
- _grf.stance_measures' centring dropped: the run's centre of pressure 0.3 m off the plate's reads 300 mm.
- _grf.pooled_group's "r trials" made `len(trials)`: a foot the run never pushes counts as scored.
- _grf.by_subject's finite filter dropped: a subject without a stance is drawn (squats' impulse CI came out nan).

Breaks, each applied once, seen red, reverted (2026-11-07, the joint moments, #98):
- _moments.early_peaks' first half made the whole stance: the early peak is the later 3.0, not 2.0.
- _moments.stances' whole-stance check dropped: the stance running off the record's end is kept.
- _moments.MOMENTS' lumbar_extension on L3_L4_FE: the lumbar is read off the decoy level (MAE 824 %BW*ht).
- _moments.peak_extension's sign turned and min made max: the peak is (-1.0, -2.0), not (4.0, 8.0).
- _moments.rising's RISE_SHARE dropped: the rising phase starts at the fastest frame (1.49 s).
- _moments.series_measures' 100 dropped: the 1 %BW*ht offset scores 0.01.

Breaks, each applied once, seen red, reverted (2026-11-07, the final validation's tables, #98):
- validate.groups_of's activity-and-camera groups dropped: no "walking | Cam1" group.
- validate.flattened's number leaf dropped: a group's r and range never reach its table.
- validate.timing_rows' `/ max(frames, 1)` dropped: a step's seconds per frame read its whole seconds.

Breaks, each applied once, seen red, reverted (2026-11-07, a foot seen standing, #98):
- _soma.seen_stance's `kinematic |` dropped: a foot GEM-X does not see static is never standing (the stage's own
  stance lost).
- _soma.seen_stance's `.any(axis=1)` over the ankle and foot made the ankle's alone: GEM-X's static left foot unseen.
- _score.emg_muscle's `NOT_MUSCLE` left out: the store's `soleus_l_activation` names no muscle (2026-11-07).
- _soma.bridged's `<= BRIDGE + 1` made `< 0`: the 6-frame gap is left (2026-11-07).
- _soma.undrifted's `drift[span] = support[span] - levels[-1]` made `0.0`: the drifting sole stands 60 mm up.
- _soma.flight's `rises or (...)` made `rises`: the box's sole is brought down to the floor.

Breaks, each applied once, seen red, reverted (2026-11-07, the chair and the box, #98):
- _supports.top's CLEAR filter dropped: the box reaches under the landed feet.
- _supports.seat's SEAT_HIGH made the seen skin's lowest: the seat stands at the Hips' skin.
- _supports.box's `on` not cut at the drop: the box stands at the whole clip's median sole, not 0.2 m.
- _run.pushes' OFF_FLOOR row dropped: a foot pushed by the box 0.25 m up reads 600 N on the lab's plates.

Breaks, each applied once, seen red, reverted (2026-11-06, the floor seen, #98):
- _floor.seen's `if normal[1] > 0:` flip dropped: the floor's normal may point down.
- _floor.levelled's `least_turn(mean, ...)` given `-mean`: the floor's normal laid on the world's down.
Breaks, each applied once, seen red, reverted (2026-11-08, the subject's own standing pose, #98):
- _run.angles' standing tilt `-standing.get(...)` made `+`: the standing pelvis reads 14 degrees, not 0.
- the pelvis turned about its own z made its tilt less the standing tilt: the standing pelvis heading the lab's other
  way reads -14 degrees (the tilt's sign flips with the heading).
- _score.angle_measures' bias `error.mean()` made `-error.mean()`: the legs, 2 degrees over, read 2 under.
- `labval.scored`'s `standing` not given to `_run.angles`: the trial's pelvis, lumbar and elbows read as without it.
"""
import ast
import json
import os
import pathlib
import subprocess

import numpy as np
from scipy.spatial.transform import Rotation

from tools import labval
from score.stages import sim_body
from tools.labval import _files, _grf, _job, _moments, _run, _score, _soma, cluster, validate

TAU, START, RATE, YAW = 0.0123, 0.5, 30.0, 40.0
WINDOW = (1.0, 1.8)  # s: an IK covering 40 % of the run, as LabValidation's covers its drop jumps' videos
NAMES = ["Root", "Hips", "Spine1", "Spine2", "Chest", "Neck1", "Neck2", "Head", "HeadEnd", "LeftShoulder", "LeftArm",
         "LeftForeArm", "LeftHand", "RightShoulder", "RightArm", "RightForeArm", "RightHand", "LeftLeg", "LeftShin",
         "LeftFoot", "LeftToeBase", "LeftToeEnd", "RightLeg", "RightShin", "RightFoot", "RightToeBase", "RightToeEnd"]
PARENTS = [-1, 0, 1, 2, 3, 4, 5, 6, 7, 4, 9, 10, 11, 4, 13, 14, 15, 1, 17, 18, 19, 20, 1, 22, 23, 24, 25]
OFFSETS = {"Hips": (0, 1.0, 0), "Spine1": (0, .1, 0), "Spine2": (0, .1, 0), "Chest": (0, .1, 0), "Neck1": (0, .2, 0),
           "Neck2": (0, .05, 0), "Head": (0, .05, 0), "HeadEnd": (0, .2, 0), "LeftShoulder": (.05, .1, 0),
           "LeftArm": (.15, 0, 0), "LeftForeArm": (.3, 0, 0), "LeftHand": (.25, 0, 0), "LeftLeg": (.1, -.05, 0),
           "LeftShin": (0, -.45, 0), "LeftFoot": (0, -.42, 0), "LeftToeBase": (0, -.06, .12),
           "LeftToeEnd": (0, 0, .06)}
OFFSETS.update({name.replace("Left", "Right"): (-x, y, z) for name, (x, y, z) in list(OFFSETS.items())
                if name.startswith("Left")})
EXTRA = [("LeftHandThumb1", "LeftHand"), ("LeftHandIndex1", "LeftHand"), ("Jaw", "Head")]


def storage_text(labels, rows, header=""):
    """An OpenSim storage file's text."""
    body = "\n".join("\t".join(f"{value:.8f}" for value in row) for row in rows)
    return f"trial\nversion=1\n{header}nRows={len(rows)}\nnColumns={len(labels)}\nendheader\n" \
           f"{chr(9).join(labels)}\n{body}\n"


def reference(times):
    """The trial's IK (degrees) at times: each leg coordinate a sine of its own, the pelvis' rotation steady."""
    found = {name: 20.0 * np.sin(2 * np.pi * (0.7 + 0.1 * index) * times + index) for index, name in
             enumerate(_run.LEGS)}
    found.update(pelvis_tilt=5 + 3 * np.sin(2 * np.pi * times), pelvis_list=2 * np.cos(2 * np.pi * times),
                 pelvis_rotation=np.full_like(times, 30.0), lumbar_extension=-10 + 4 * np.sin(3 * times),
                 lumbar_bending=3 * np.sin(2 * times), lumbar_rotation=2 * np.cos(2.5 * times))
    arms = [name for _, names, _ in _run.SHOULDERS.values() for name in names]
    found.update({name: 15.0 * np.sin(2 * np.pi * (0.6 + 0.1 * index) * times + index) + 5.0 * index for index, name
                  in enumerate(arms)})
    found.update({name: 40.0 + 30.0 * np.sin(2 * np.pi * 0.8 * times + index) for index, name in
                  enumerate(_run.ELBOWS)})
    found.update({name: 90.0 + 20.0 * np.sin(2 * np.pi * 0.9 * times + index) for index, name in
                  enumerate(_run.FOREARMS)})
    return found


def plates(times):
    """Each foot's plate force (N), centre of pressure (m) and free torque in the lab, at times."""
    right = np.stack([30 * np.sin(np.pi * times), 400 + 200 * np.sin(np.pi * times), 0 * times], axis=1)
    left = np.stack([-20 * np.cos(np.pi * times), 300 + 100 * np.cos(np.pi * times), 0 * times], axis=1)
    cops = {"right": np.tile([0.0, 0.0, -0.05], (len(times), 1)), "left": np.tile([0.0, 0.0, 0.05], (len(times), 1))}
    return {"right": (right, cops["right"]), "left": (left, cops["left"])}


def vasti_on(times):
    return (times >= 1.0) & (times <= 1.6)


def write_labval(root, window=(0.0, 3.0)):
    """subject2's files for walking1 in LabValidation's layout, its IK over `window` (s), its plate file with an
    empty third plate."""
    subject = root / "subject2"
    for folder in ("OpenSimData/Mocap/IK", "ForceData", "MarkerData/Mocap", "EMGData"):
        (subject / folder).mkdir(parents=True)
    (subject / "sessionMetadata.yaml").write_text("subjectID: subject2\nmass_kg: 70.0\nheight_m: 1.75\n")
    times = np.arange(0, 3.0, 0.01)
    ik_times = times[(times >= window[0]) & (times <= window[1])]
    ik = reference(ik_times)
    (subject / "OpenSimData/Mocap/IK/walking1.mot").write_text(storage_text(
        ["time", *ik], np.column_stack([ik_times, *[np.radians(values) for values in ik.values()]]), "inDegrees=no\n"))
    fine = np.arange(0, 3.0, 1 / 2000)
    pushed = plates(fine)
    labels, columns = ["time"], [fine]
    for side, letter in (("right", "R"), ("left", "L")):
        force, cop = pushed[side]
        for name, values in (("ground_force_v", force), ("ground_force_p", cop), ("ground_torque_", 0 * force)):
            labels += [f"{letter}_{name}{axis}" for axis in "xyz"]
            columns += list(values.T)
    labels += [f"3_ground_{name}{axis}" for name in ("force_v", "force_p", "torque_") for axis in "xyz"]
    columns += [0 * fine] * 9
    (subject / "ForceData/walking1_forces.mot").write_text(storage_text(labels, np.column_stack(columns)))
    markers = {"r_knee_study": (0, .5, .05), "r_mknee_study": (0, .5, -.05), "r_ankle_study": (0, .1, .04), "r_mankle_study": (0, .1, -.04),
               "L_knee_study": (0, .5, -.05), "L_mknee_study": (0, .5, .05), "L_ankle_study": (0, .1, -.04), "L_mankle_study": (0, .1, .04)}
    lines = ["PathFileType\t4\t(X/Y/Z)\twalking1.trc",
             "DataRate\tCameraRate\tNumFrames\tNumMarkers\tUnits\tOrigDataRate\tOrigDataStartFrame\tOrigNumFrames",
             f"100\t100\t{len(times)}\t{len(markers)}\tmm\t100\t1\t{len(times)}",
             "Frame#\tTime\t" + "\t\t\t".join(markers) + "\t\t", "\t\t" + "\t".join(
                 f"X{index}\tY{index}\tZ{index}" for index in range(1, len(markers) + 1)), ""]
    lines += ["\t".join([str(frame + 1), f"{time:.3f}", *[f"{1000 * value:.3f}" for place in markers.values()
                                                           for value in place]]) for frame, time in enumerate(times)]
    (subject / "MarkerData/Mocap/walking1.trc").write_text("\n".join(lines) + "\n")
    noise = np.random.default_rng(1).normal(size=len(fine))
    burst = noise * np.where(vasti_on(fine), 1.0, 0.02)
    (subject / "EMGData/walking1_EMG.sto").write_text(storage_text(["time", "R_VL", "trigger"],
                                                                   np.column_stack([fine, burst, 0 * fine])))
    return subject


def zxy_turns(angles):
    return Rotation.from_euler("ZXY", angles, degrees=True).as_matrix()


# LaiUhlrich2022's acromial_r and acromial_l: rotation1, 2 and 3's axes (arm_flex, arm_add, arm_rot), body-fixed.
ACROMIAL_AXES = (np.eye(3)[[2, 0, 1]], np.eye(3)[[2, 0, 1]] * [[1], [-1], [-1]])


def acromial(angles, axes):
    """The humerus' turns on the torso (frames x 3 x 3) of a CustomJoint's three angles (degrees, frames x 3) about
    its axes in turn, each about the frame the ones before it left."""
    turns = np.tile(np.eye(3), (len(angles), 1, 1))
    for column, axis in enumerate(axes):
        turns = turns @ Rotation.from_rotvec(np.radians(angles[:, [column]]) * axis).as_matrix()
    return turns


def write_run(folder):
    """A run of subject2_walking1_Cam1: the reference at the shifted times, the legs 2 degrees over, the whole body
    turned YAW about up, the plates' pushes and the knees where the markers put them."""
    folder.mkdir(parents=True)
    times = START + np.arange(60) / RATE
    at = times + TAU
    ik = reference(at)
    yaw = Rotation.from_euler("y", YAW, degrees=True).as_matrix()
    pelvis = yaw @ zxy_turns(np.stack([ik[name] for name in _run.PELVIS], axis=1))
    torso = pelvis @ zxy_turns(np.stack([ik[name] for name in _run.LUMBAR], axis=1))
    humeri = [torso @ acromial(np.stack([ik[name] for name in names], axis=1), axes)
              for (_, names, _), axes in zip(_run.SHOULDERS.values(), ACROMIAL_AXES)]
    knees = {"right": np.array([0, .5, 0]) @ yaw.T, "left": np.array([0, .5, 0]) @ yaw.T}
    bones = []
    for frame in range(len(times)):
        row = []
        for turn, place in ((pelvis[frame], [0, 1, 0]), (torso[frame], [0, 1.3, 0]), (yaw, knees["right"]),
                            (yaw, knees["left"]), (humeri[0][frame], [0, 1.4, .2]),
                            (humeri[1][frame], [0, 1.4, -.2])):
            row.append(np.r_[place, Rotation.from_matrix(turn).as_quat()])
        bones.append(row)
    pushed = plates(at)
    frames = []
    for frame, time in enumerate(at):
        touches = {_run.FEET[side]: [*(pushed[side][0][frame] @ yaw.T), *(pushed[side][1][frame] @ yaw.T)]
                   for side in ("right", "left")}
        frames.append({"touches": touches, "residual": [1, 2, 0, 0.5, 0, 0],
                       "activations": [1.0 if vasti_on(np.array([time]))[0] else 0.05, 0.1]})
    name = "subject2_walking1_Cam1"
    entry = {"bones": ["pelvis", "torso", "tibia_r", "tibia_l", "humerus_r", "humerus_l"], "muscles": ["vaslat_r", "soleus_r"],
             "weight N": 686.7, "com height": 1.0, "frames": frames}
    (folder / "out.json").write_text(json.dumps({"rate": RATE, "people": {name: entry}}))
    own = [*_run.LEGS, *_run.ELBOWS, *_run.FOREARMS]
    coordinates = np.radians(np.stack([ik[stem] + (-90.0 if stem in _run.FOREARMS else 2.0) for stem in own], axis=1))
    np.savez(folder / "out.npz", **{f"{name}/bones": np.array(bones), f"{name}/coordinates": coordinates,
                                    f"{name}/coordinate names": np.array(own)})
    (folder / "record.json").write_text(json.dumps({"name": name, "start": START}))


def scoring_faults(tmp):
    """The synthetic trial scored end to end, then pooled."""
    root = tmp / "LabValidation"
    write_labval(root)
    write_run(tmp / "run")
    found = labval.scored(tmp / "run", root)
    faults = []
    if abs(found["shift s"] - TAU) > 1e-3:
        faults.append(f"shift {found['shift s']}")
    windowed = labval.scored(tmp / "run", write_labval(tmp / "windowed", WINDOW).parent)
    if abs(windowed["shift s"] - TAU) > 1e-3:
        faults.append(f"the IK's window's shift {windowed['shift s']}")
    for name in (*_run.LEGS, *_run.ELBOWS):
        row = found["angles"][name]
        if abs(row["mae"] - 2.0) > 0.05 or abs(row["bias"] - 2.0) > 0.05 or row["cmae"] > 0.05 or row["r"] < 0.999:
            faults.append(f"{name} {row}")
    for name in _run.FOREARMS:
        row = found["angles"].get(name, {})
        if "mae" in row or "rmse" in row or "bias" in row or row.get("cmae", 1) > 0.05 or row.get("r", 0) < 0.999:
            faults.append(f"{name} {row}")
    shoulders = [name for _, names, _ in _run.SHOULDERS.values() for name in names]
    for name in (*_run.PELVIS, *_run.LUMBAR, *shoulders):
        if found["angles"][name]["mae"] > 0.05:
            faults.append(f"{name} {found['angles'][name]}")
    for side in ("right", "left"):
        for axis in ("vertical", "anterior"):
            if found["forces"][side][axis]["rmse %bw"] > 0.3:
                faults.append(f"{side} {axis} {found['forces'][side][axis]}")
        if found["forces"][side]["stance carried"] < 0.99:
            faults.append(f"{side} stance carried {found['forces'][side]['stance carried']}")
        knee = found["knee adduction"][side]
        if not knee["frames"] or knee["rmse %bw.ht"] > 0.05:
            faults.append(f"knee {side} {knee}")
    if not found["residual"]["passes"]:
        faults.append(f"residual {found['residual']}")
    vasti = found["emg"].get("vaslat_r", {})
    if vasti.get("on/off agreement", 0) < 0.9 or vasti.get("r", 0) < 0.9 or abs(vasti.get("lag s", 1)) > 0.1 or found["emg"]["not matched"] != [
            "trigger"]:
        faults.append(f"emg {found['emg']}")
    pooled = labval.pooled([found, {**found, "subject": "subject3"}])["all"]
    if pooled["trials"] != 2 or abs(pooled["angles"]["coordinates"]["knee_angle_r"]["mae"]["mean"] - 2.0) > 0.05:
        faults.append(f"pooled {pooled['trials']} {pooled['angles']['coordinates']['knee_angle_r']}")
    plate, lifted_foot = np.array([0.0, 500, 500, 500, 500, np.nan]), np.array([300.0, 500, 0, 0, 20, 500])
    carried = _score.stance_carried(lifted_foot, plate, 686.7)
    if carried != 0.25:
        faults.append(f"a foot lifted for three of four stance frames carries {carried}")
    lifted = {**found, "forces": {**found["forces"], "left": {
        "vertical": {**found["forces"]["left"]["vertical"], "r": float("nan")},
        "anterior": found["forces"]["left"]["anterior"], "stance carried": 0.0}}}
    feet = labval.pooled([found, {**lifted, "subject": "subject3"}])["all"]["forces"]
    if feet["left vertical"]["r trials"] != 1 or abs(feet["left stance carried"]["mean"] - 0.5) > 1e-9:
        faults.append(f"a foot never pushed pooled as {feet['left vertical']} {feet['left stance carried']}")
    for foot in ("right", "left", "both"):
        for axis in _grf.AXES:
            if found["grf"]["feet"][foot][axis]["mae %bw"] > 0.3:
                faults.append(f"grf {foot} {axis} {found['grf']['feet'][foot][axis]}")
    unpushed = {**found, "grf": {**found["grf"], "feet": {**found["grf"]["feet"], "left": {
        axis: {**row, "r": float("nan")} for axis, row in found["grf"]["feet"]["left"].items()}}}}
    grf = _grf.pooled([found, {**unpushed, "subject": "subject3", "camera": "Cam2"}])
    if grf["all"]["left vertical"]["r trials"] != 1 or set(grf) != {"all", "walking", "Cam1", "Cam2",
                                                                    "walking | Cam1", "walking | Cam2"}:
        faults.append(f"grf pooled as {sorted(grf)} {grf['all']['left vertical']}")
    return faults


def write_static(folder, tilt, lumbar, elbow, facing):
    """subject2's static standing run on Cam1: the pelvis tilted `tilt` about its own z and facing `facing` (degrees
    about up), the torso `lumbar` over it, the elbows at `elbow`, every other coordinate 0."""
    folder.mkdir(parents=True)
    pelvis = Rotation.from_euler("y", facing, degrees=True).as_matrix() @ zxy_turns([tilt, 0.0, 0.0])
    torso = pelvis @ zxy_turns([lumbar, 0.0, 0.0])
    row = [np.r_[place, Rotation.from_matrix(turn).as_quat()]
           for turn, place in ((pelvis, [0, 1, 0]), (torso, [0, 1.3, 0]), (torso, [0, 1.4, .2]), (torso, [0, 1.4, -.2]))]
    name = "subject2_static1_Cam1"
    entry = {"bones": ["pelvis", "torso", "humerus_r", "humerus_l"], "frames": [{}] * 20}
    (folder / "out.json").write_text(json.dumps({"rate": RATE, "people": {name: entry}}))
    own = [*_run.LEGS, *_run.ELBOWS, *_run.FOREARMS]
    coordinates = np.radians([[elbow if stem in _run.ELBOWS else 0.0 for stem in own]] * 20)
    np.savez(folder / "out.npz", **{f"{name}/bones": np.array([row] * 20), f"{name}/coordinates": coordinates,
                                    f"{name}/coordinate names": np.array(own)})


def neutral_faults(tmp):
    """The subject's own standing pose from its static run: read on its own heading, it is the model's zero whichever
    way along the lab a trial heads, and a trial scored with it is read from it (the synthetic trial's pelvis, lumbar
    and elbows, exact without it, then off by the standing pose); no static run, no neutral."""
    faults = []
    tilt, lumbar, elbow = 7.0, 4.0, 12.0
    write_static(tmp / "static" / "trials" / "subject2_static1_Cam1", tilt, lumbar, elbow, 130.0)
    standing = labval.neutral(tmp / "static" / "trials" / "subject2_static1_Cam1")
    expected = {"pelvis_tilt": tilt, "lumbar_extension": lumbar, "elbow_flex_r": elbow, "elbow_flex_l": elbow}
    if any(abs(standing[name] - value) > 1e-6 for name, value in expected.items()):
        faults.append(f"the static run's neutral {standing}")
    entry, arrays, _ = _run.read(tmp / "static" / "trials" / "subject2_static1_Cam1")
    for heading in (0.0, np.pi):
        upright = _run.angles(entry, arrays, heading, standing)
        if any(abs(upright[name][0]) > 1e-6 for name in _run.NEUTRAL):
            faults.append(f"standing, read from its own neutral heading {heading:.2f}: "
                          f"{ {name: upright[name][0] for name in _run.NEUTRAL} }")
    if labval.standing_of(None, "subject2", "Cam1") or labval.standing_of(tmp / "static", "subject2", "Cam2"):
        faults.append("a neutral without its static run")
    root = tmp / "LabValidation"
    write_labval(root)
    write_run(tmp / "run")
    found = labval.scored(tmp / "run", root, tmp / "static")
    if found["neutral"] != standing:
        faults.append(f"the trial scored on neutral {found['neutral']}")
    # the pelvis is turned about its own z, which the trial's steady 30 degree pelvis_rotation turns off the lab's
    off = {"pelvis_tilt": tilt * np.cos(np.radians(30.0)), "lumbar_extension": lumbar, "elbow_flex_r": elbow - 2.0, "elbow_flex_l": elbow - 2.0}
    for name, value in off.items():
        if abs(found["angles"][name]["mae"] - value) > 0.3:
            faults.append(f"{name} read from the standing pose: MAE {found['angles'][name]['mae']:.3f}, not {value}")
    return faults


def grf_faults():
    """OpenCap's cutoffs held under a 30 Hz run's Nyquist; the subject's right is forward x up; only a stance whose
    both neighbours the plate covers unloaded is whole; a stance's impulse and its centred centre of pressure."""
    faults = []
    if _grf.cutoff_of("drop jump", 30.0) != 12.0 or _grf.cutoff_of("walking", 30.0) != 6.0:
        faults.append(f"cutoffs {_grf.cutoff_of('drop jump', 30.0)} {_grf.cutoff_of('walking', 30.0)}")
    if not np.allclose(_grf.directions([1.0, 0.0, 0.0])[2], [0.0, 0.0, 1.0]):
        faults.append(f"forward x's right is {_grf.directions([1.0, 0.0, 0.0])[2]}")
    vertical = np.array([np.nan, 600, 600, 0, 0, 600, 600, 0, 600])
    if _grf.stances(vertical, 686.7) != [(5, 6)]:
        faults.append(f"stances {_grf.stances(vertical, 686.7)}")
    theirs = np.zeros((9, 3))
    theirs[5:7] = [686.7, 68.67, 0.0]
    travel = np.zeros((9, 3))
    travel[5:7, 1] = [0.0, 0.1]
    row = _grf.stance_measures(0.1, theirs * [1, 1, 0], theirs, travel + [0, 0.3, 0.3], travel, (5, 6), 686.7)
    if (abs(row["impulse"]["vertical"]["plate %bw.s"] - 20.0) > 1e-9 or abs(row["impulse"]["vertical"]["error %bw.s"])
            > 1e-9 or max(row["cop mae mm"].values()) > 1e-9 or row["cop frames"] != 2):
        faults.append(f"a stance {row}")
    stanceless = _grf.by_subject([{"subject": "subject2", "n": [1.0]}, {"subject": "subject3", "n": []}],
                                 lambda trial: trial["n"])
    if set(stanceless) != {"subject2"}:
        faults.append(f"a subject without a stance is drawn: {stanceless}")
    return faults


def hand_faults():
    """Worked by hand: a knee moment, a shank, a bootstrap's bounds, EMG names, the flag, a heading."""
    faults = []
    force, knee, forward = np.array([[0, 700.0, 0]]), np.array([[0, .5, 0]]), np.array([[1.0, 0, 0]])
    moments = [_score.knee_adduction(force, np.array([[0, 0, -.05]]), knee, forward, "right")[0],
               _score.knee_adduction(force, np.array([[0, 0, .05]]), knee, forward, "left")[0]]
    if not np.allclose(moments, [35.0, 35.0]):
        faults.append(f"knee moments {moments}")
    markers = {"L_knee_study": [[0, .5, -.05]], "L_mknee_study": [[0, .5, .05]], "L_ankle_study": [[0, .1, -.04]],
               "L_mankle_study": [[0, .1, .04]]}
    centre, axis = _score.marker_shank(markers, "left", labval.MARKERS)
    if not (np.allclose(centre, [[0, .5, 0]]) and np.allclose(axis, [[1, 0, 0]])):
        faults.append(f"left shank {centre} {axis}")
    boot = _score.bootstrapped({"a": [1.0, 1.0], "b": [3.0]}, draws=4000)
    if not (abs(boot["mean"] - 5 / 3) < 1e-12 and boot["low"] == 1.0 and boot["high"] == 3.0):
        faults.append(f"bootstrap {boot}")
    names = [_score.emg_muscle(channel) for channel in ("R_VL", "vastus_medialis_l", "trigger", "TA",
                                                              "glmed1_l_activation", "soleus_l_activation")]
    if names != ["vaslat_r", "vasmed_l", None, None, "glmed1_l", "soleus_l"]:
        faults.append(f"emg names {names}")
    wave = np.sin(np.linspace(0, 6, 120)) + 1.0
    rs = [_score.timing_measures(np.linspace(0, 1.2, 120), wave, other)["r"] for other in (3 * wave + 2, 1 - wave)]
    if abs(rs[0] - 1) > 1e-9 or abs(rs[1] + 1) > 1e-9:
        faults.append(f"emg r {rs}")
    flat = _score.angle_measures(np.linspace(0, 10, 50) + 3, np.linspace(0, 10, 50))
    if not (flat["dagger"] and abs(flat["mae"] - 3) < 1e-9 and flat["cmae"] < 1e-9):
        faults.append(f"small range {flat}")
    return [*faults, *gait_cycle_faults()]


def gait_cycle_faults():
    """A walking trial's one gait cycle: video and IK both 1.3 s, the IK 0.4 s later, the sides half a cycle apart."""
    def flexions(at):
        phase = 2 * np.pi * np.asarray(at) / 1.1
        return {f"{stem}_{side}": 30 * np.sin(phase + offset) + 20 for stem in ("hip_flexion", "knee_angle",
                                                                                "ankle_angle")
                for side, offset in (("r", 0.0), ("l", np.pi))}
    times, ik_times, lag = np.arange(0, 1.3, 1 / RATE), np.arange(0, 1.3, 0.01), 0.4
    found = _score.shift(times, flexions(times), ik_times, flexions(ik_times - lag))
    return [] if abs(found - lag) < 1e-3 else [f"one gait cycle's shift {found}, not {lag}"]


def loader_faults(tmp):
    """A plate file missing a torque column is refused; the IK in radians reads in degrees; the TRC in metres."""
    faults = []
    tmp.mkdir(parents=True)
    short = tmp / "short.mot"
    short.write_text(storage_text(["time", *[f"{side}_ground_force_v{axis}" for side in "RL" for axis in "xyz"],
                                   *[f"{side}_ground_force_p{axis}" for side in "RL" for axis in "xyz"],
                                   *[f"R_ground_torque_{axis}" for axis in "xyz"]], np.zeros((3, 16))))
    try:
        _files.forces(short)
        faults.append("a plate file without the left torque was read")
    except ValueError:
        pass
    loaded = tmp / "loaded.mot"
    labels = [f"{side}_ground_{name}{axis}" for side in "RL3" for name in ("force_v", "force_p", "torque_")
              for axis in "xyz"]
    loaded.write_text(storage_text(["time", *labels], np.column_stack([np.arange(3), np.ones((3, 27))])))
    try:
        _files.forces(loaded)
        faults.append("a plate file whose third plate carries a load was read")
    except ValueError:
        pass
    subject = write_labval(tmp / "loaders")
    _, ik = _files.ik(subject / "OpenSimData/Mocap/IK/walking1.mot")
    if abs(ik["pelvis_rotation"][0] - 30.0) > 1e-5:
        faults.append(f"IK in radians read as {ik['pelvis_rotation'][0]}")
    _, markers = _files.trc(subject / "MarkerData/Mocap/walking1.trc")
    if not np.allclose(markers["r_knee_study"][0], [0, .5, .05]):
        faults.append(f"TRC r_knee {markers['r_knee'][0]}")
    return faults


def toy_soma():
    """(a GEM-X SOMA body of the rig's joints and three dropped ones, frames floating 0.3 m and moving; the
    template)."""
    rng = np.random.default_rng(3)
    names = NAMES + [name for name, _ in EXTRA]
    parents = PARENTS + [names.index(parent) for _, parent in EXTRA]
    bind = np.tile(np.eye(4), (len(names), 1, 1))
    for joint, name in enumerate(names):
        offset = OFFSETS.get(name, (0.02, 0.0, 0.03))
        bind[joint, :3, 3] = (bind[parents[joint], :3, 3] if parents[joint] >= 0 else 0) + np.array(offset)
    bind[1:, :3, :3] = Rotation.random(len(names) - 1, random_state=4).as_matrix()
    template_bind = bind[:len(NAMES)].copy()
    template_bind[1:, :3, :3] = Rotation.random(len(NAMES) - 1, random_state=5).as_matrix()
    carriers = [joint for joint, name in enumerate(names) if name not in ("Root", "HeadEnd", "LeftToeEnd",
                                                                          "RightToeEnd")]
    points, weights = [], []
    for joint in carriers:
        for _ in range(4):
            points.append(bind[joint, :3, 3] + rng.normal(scale=0.02, size=3))
            weight = np.zeros(len(names))
            weight[joint] = 1.0
            weights.append(weight)
    hand, thumb = names.index("LeftHand"), names.index("LeftHandThumb1")
    weights[carriers.index(hand) * 4][[hand, thumb]] = [0.5, 0.5]
    frames = 30
    local = np.tile(np.eye(4), (frames, len(names), 1, 1))
    for joint, parent in enumerate(parents):
        rest = bind[joint] if parent < 0 else np.linalg.inv(bind[parent]) @ bind[joint]
        turns = Rotation.from_rotvec(0.1 * np.sin(np.arange(frames)[:, None] / 5 + joint) * np.array([1, .5, .2]))
        local[:, joint] = rest
        if joint:
            local[:, joint, :3, :3] = rest[:3, :3] @ turns.as_matrix()
    local[:, 1, 0, 3] += 0.03 * np.arange(frames)
    local[:, 1, 1, 3] += 0.3
    world = np.zeros_like(local)
    for joint, parent in enumerate(parents):
        world[:, joint] = local[:, joint] if parent < 0 else world[:, parent] @ local[:, joint]
    faces = np.array([[0, 1, 2], [2, 3, 4]])
    soma = {"names": np.array(names), "parents": np.array(parents), "bind": bind, "points": np.array(points),
            "faces": faces, "weights": np.array(weights), "world": world, "fps": 30.0, "start": 0.0}
    return soma, {"names": np.array(NAMES), "parents": np.array(PARENTS), "bind": template_bind, "faces": faces}


def skinned(weights, worlds, binds, points):
    moves = worlds @ np.linalg.inv(binds)
    return np.einsum("pj,fjab,pb->fpa", weights, moves[..., :3, :], np.c_[points, np.ones(len(points))])


def soma_faults():
    """The toy SOMA body as the sim body's person: skin, weights, bind frames, floor."""
    soma, template = toy_soma()
    rig, worlds, segments, record = _soma.person(soma, template)
    faults = []
    joints = [NAMES.index(name) for name in segments]
    before = skinned(soma["weights"], soma["world"], soma["bind"], soma["points"])
    after = skinned(rig["weights"][:, joints], worlds, rig["bind"][joints], rig["points"])
    names = [str(name) for name in soma["names"]]
    dropped = [names.index(name) for name, _ in EXTRA]
    own = ~soma["weights"][:, dropped].any(axis=1)  # a dropped joint's skin rides its carrier now, as in the route
    lift = before[:, own, 1] - after[:, own, 1]
    across = np.abs(before[:, own][..., [0, 2]] - after[:, own][..., [0, 2]]).max()
    if across > 1e-9 or np.ptp(lift, axis=1).max() > 1e-9:
        faults.append("the skin moved other than up or down")
    hand = soma["weights"][:, [names.index(name) for name in ("LeftHand", "LeftHandThumb1", "LeftHandIndex1")]].sum(
        axis=1)
    if not np.allclose(rig["weights"].sum(axis=1), 1.0) or not np.allclose(
            rig["weights"][:, NAMES.index("LeftHand")], hand):
        faults.append("the thumb's weight did not go to the hand")
    if not np.allclose(rig["bind"][:, :3, :3], template["bind"][:, :3, :3]):
        faults.append("the bind is not on the template's frames")
    feet = [index for index, weight in enumerate(rig["weights"]) if NAMES[int(weight.argmax())] in (
        "LeftFoot", "LeftToeBase", "RightFoot", "RightToeBase")]
    if abs(after[:, feet, 1].min()) > 0.005:
        faults.append(f"the feet's lowest point stands {after[:, feet, 1].min():.3f} m off the floor")
    local = np.repeat(_soma.against_parents(worlds_of(rig, worlds, segments), rig["parents"])[:1], 30, axis=0)
    local[10:20, 1, 1, 3] += 0.1  # standing still, but 10 cm up on frames 10 to 19: no stance of the stage's there
    logits = np.full((len(local), 6), -4.0)
    logits[10:20, 1] = 4.0  # GEM-X sees the left foot (its foot channel) static there, the right never
    seen = _soma.seen_stance({"static_conf_logits": logits}, rig, local)
    # the toy's right foot never stands (its sole over the left's)
    if rig["stance"].shape != (len(worlds), 2) or not seen[:, 0].all() or seen[:, 1].any():
        faults.append(f"the seen stance is not GEM-X's static foot or the stage's own stance: {seen.mean(axis=0)}")
    gappy = np.ones((30, 2), dtype=bool)
    gappy[5:11, 0] = False  # a 6-frame gap, bridged
    gappy[15:22, 1] = False  # a 7-frame swing, kept
    filled = _soma.bridged(gappy)
    if not filled[:, 0].all() or filled[15:22, 1].any():
        faults.append("a seen stance's 6-frame gap is not bridged, or its 7-frame swing is")
    return faults + drift_faults(rig, local[:1]) + supports_faults(rig, local[:1])


def drift_faults(rig, still):
    """`_soma.undrifted` on the toy standing still (`still`, one frame of it): drifting 60 mm up over 3 s, its sole
    held on the floor throughout (within 1 mm); standing 0.2 m up for 1 s, falling over 9 frames and standing on the
    floor after, both supports kept (the box within 5 mm of 0.2 m, the floor within 1 mm), the fall no drift."""
    from tools.characters import played
    faults = []
    drifting = np.repeat(still, 90, axis=0)
    drifting[:, played.TRAVELLING_JOINT, 1, 3] += np.linspace(0.0, 0.06, 90)
    found = sim_body.soles(rig, _soma.undrifted(rig, drifting)[0])[0].min(axis=1)
    if np.abs(found).max() > 0.001:
        faults.append(f"the drifting sole stands {1000 * np.abs(found).max():.1f} mm off the floor")
    dropping = np.repeat(still, 69, axis=0)
    dropping[:, played.TRAVELLING_JOINT, 1, 3] += np.r_[np.full(30, 0.2), np.linspace(0.2, 0.0, 11)[1:-1],
                                                       np.zeros(30)]
    found = sim_body.soles(rig, _soma.undrifted(rig, dropping)[0])[0].min(axis=1)
    if abs(found[:20].mean() - 0.2) > 0.005 or np.abs(found[-20:]).max() > 0.001:
        faults.append(f"the box's sole stands {1000 * found[:20].mean():.1f} mm, the floor's "
                      f"{1000 * np.abs(found[-20:]).max():.1f} mm")
    return faults


def covered(triangles, across):
    """Which of the points `across` (n x 2, x and z) lie under the flat triangles (n x 3 x 3)."""
    found = np.zeros(len(across), dtype=bool)
    for corner, first, second in triangles[:, :, [0, 2]]:
        edges = np.array([first - corner, second - corner]).T
        if abs(np.linalg.det(edges)) > 1e-12:
            share = np.linalg.solve(edges, (across - corner).T)
            found |= (share >= 0).all(axis=0) & (share.sum(axis=0) <= 1)
    return found


def supports_faults(rig, still):
    """`_supports.under` on the toy (`still`, one frame of it; its feet's and Hips' skin laid flat, the Hips' 0.25 m
    behind its heels as a seated body's): a drop jump standing 0.2 m up for 1 s and landing 0.15 m forward has its box
    at 0.2 m under its first feet and clear of where they land; a sit-to-stand its seat at SEAT_HIGH under the Hips,
    clear of the feet; a walk nothing."""
    from tools.characters import played
    from tools.labval import _supports
    points = np.array(rig["points"])
    for group in (_supports.FEET, _supports.SEAT_SEGMENTS):
        mine = _supports.carried_by(rig, group)
        points[mine, 1] = points[mine, 1].min()
    points[_supports.carried_by(rig, _supports.SEAT_SEGMENTS), 2] -= 0.25
    flat = dict(rig, points=points)
    faults = []
    dropping = np.repeat(still, 69, axis=0)
    dropping[:, played.TRAVELLING_JOINT, 1, 3] += np.r_[np.full(30, 0.2), np.linspace(0.2, 0.0, 11)[1:-1],
                                                       np.zeros(30)]
    dropping[39:, played.TRAVELLING_JOINT, 2, 3] += 0.15
    box, _ = _supports.under(flat, dropping, "drop jump")
    feet = _supports.skin(flat, dropping)[:, _supports.carried_by(flat, _supports.FEET)][..., [0, 2]]
    if not len(box) or np.abs(box[..., 1] - 0.2).max() > 0.005:
        faults.append(f"the box's top is {box[..., 1].ravel()[:1]} m, not 0.2")
    elif not covered(box, feet[0]).any() or covered(box, feet[-1]).any():
        faults.append(f"the box is under {covered(box, feet[0]).mean():.2f} of the first feet, "
                      f"{covered(box, feet[-1]).mean():.2f} of the landed ones")
    sitting = np.repeat(still, 30, axis=0)
    seat, _ = _supports.under(flat, sitting, "sit-to-stand")
    placed = _supports.skin(flat, sitting)
    hips = placed[0, _supports.carried_by(flat, _supports.SEAT_SEGMENTS)][:, [0, 2]]
    feet = placed[0, _supports.carried_by(flat, _supports.FEET)][:, [0, 2]]
    if not len(seat) or np.abs(seat[..., 1] - _supports.SEAT_HIGH).max() > 1e-9:
        faults.append(f"the seat's top is {seat[..., 1].ravel()[:1]} m, not {_supports.SEAT_HIGH}")
    elif not covered(seat, hips).all() or covered(seat, feet).any():
        faults.append(f"the seat is under {covered(seat, hips).mean():.2f} of the Hips, {covered(seat, feet).mean():.2f}"
                      " of the feet")
    if len(_supports.under(flat, sitting, "walking")[0]):
        faults.append("a walk rests on something besides its floor")
    on_box = _run.pushes({"frames": [{"touches": {"RightFoot": [0.0, 600.0, 0.0, 0.1, 0.25, 0.0],
                                                  "LeftFoot": [0.0, 600.0, 0.0, -0.1, 0.0, 0.0]}}]})
    if on_box["right"][0][0, 1] != 0.0 or on_box["left"][0][0, 1] != 600.0:
        faults.append(f"the plates read the box's push {on_box['right'][0][0, 1]} N or lose the floor's "
                      f"{on_box['left'][0][0, 1]} N")
    return faults


def worlds_of(rig, worlds, segments):
    """Every rig joint's world (frames x joints x 4 x 4) from the segments' (`worlds`): a joint no segment is (a toe's
    end) carried by its parent at the bind's offset."""
    names = [str(name) for name in rig["names"]]
    found = np.zeros((len(worlds), len(names), 4, 4))
    for joint, name in enumerate(names):
        if name in segments:
            found[:, joint] = worlds[:, segments.index(name)]
        else:
            parent = rig["parents"][joint]
            found[:, joint] = (found[:, parent] if parent >= 0 else np.eye(4)) @ np.linalg.inv(
                rig["bind"][parent] if parent >= 0 else np.eye(4)) @ rig["bind"][joint]
    return found


def go_faults(tmp):
    """The go.sh runs the trial not done and leaves the done one."""
    folder = tmp / "measure"
    tmp.mkdir(parents=True)
    for trial in ("done", "todo"):
        (folder / "trials" / trial).mkdir(parents=True)
    (folder / "trials/done/out.json").write_text("{}")
    script = _job.write_go(folder)
    repo, bin_folder = tmp / "repo", tmp / "bin"
    (repo / "tools/cloud/backends").mkdir(parents=True)
    (repo / "score/stages/sim_body/inside").mkdir(parents=True)
    bin_folder.mkdir()
    (repo / "tools/cloud/backends/card_queue.py").write_text(
        "import subprocess, sys\nsys.exit(subprocess.run(sys.argv[sys.argv.index('--') + 1:]).returncode)\n")
    (repo / "score/stages/sim_body/inside/sim_body.py").write_text(
        "import sys, pathlib\npathlib.Path(sys.argv[2]).write_text('ran')\n")
    (bin_folder / "systemd-run").write_text("#!/bin/sh\nwhile [ \"${1#-}\" != \"$1\" ]; do shift; done\nexec \"$@\"\n")
    (bin_folder / "systemd-run").chmod(0o755)
    environment = {**os.environ, "PY": "python3", "REPO": str(repo), "LANES": "2",
                   "PATH": f"{bin_folder}:{os.environ['PATH']}"}
    subprocess.run(["bash", str(script)], env=environment, check=True, timeout=60)
    states = [(folder / f"trials/{trial}/out.json").read_text() for trial in ("done", "todo")]
    return [] if states == ["{}", "ran"] else [f"go.sh left {states}"]


def unseen_faults():
    """_soma.UNSEEN is the people route's own (body.py)."""
    tree = ast.parse((pathlib.Path(__file__).resolve().parents[2] / "tools/characters/people/body.py").read_text())
    theirs = next(ast.literal_eval(node.value) for node in ast.walk(tree) if isinstance(node, ast.Assign)
                  and any(getattr(target, "id", "") == "UNSEEN" for target in node.targets))
    return [] if tuple(theirs) == _soma.UNSEEN else [f"UNSEEN {_soma.UNSEEN} against body.py's {theirs}"]


def cluster_faults(folder):
    """The store copy's layout is found, and the cluster's jobs keep each trial on its own: a failure said and the
    next trial run, every trial folder sent and brought back whole, the trials spread evenly over the jobs, a job's
    minutes by its trials' frames (a short trial one clip's)."""
    faults = []
    subject = folder / "subject2"
    (subject / "ik").mkdir(parents=True)
    (subject / "ik" / "walking1.mot").write_text("")
    (subject / "metadata.yaml").write_text("")
    if _files.found(subject, "metadata", "walking1") != subject / "metadata.yaml":
        faults.append("the store copy's metadata.yaml is not found")
    if _files.found(subject, "ik", "walking1") != subject / "ik" / "walking1.mot":
        faults.append("the store copy's ik/<trial>.mot is not found")
    trials = []
    for name in ("subject2_walking1_Cam1", "subject2_walking2_Cam1", "subject2_squats1_Cam1"):
        trial = folder / "measure" / "trials" / name
        trial.mkdir(parents=True)
        (trial / "job.json").write_text(json.dumps({"model": "/m", "people": [{"targets": str(trial / "t.npz")}]}))
        np.savez(trial / "t.npz", world=np.zeros((540 if name.endswith("walking1_Cam1") else 90, 1, 4, 4)))
        trials.append(trial)
    (trials[2] / "out.json").write_text("{}")
    waiting = cluster.waiting(folder / "measure")
    if waiting != trials[:2]:
        faults.append(f"waiting {waiting}")
    if [len(part) for part in cluster.batches(trials, 2)] != [2, 1]:
        faults.append("the trials are not spread over ceil(n / per_job) jobs")
    job = cluster.job(trials[:2])
    if job["inputs"] != [str(trial) for trial in trials[:2]] or job["outputs"] != job["inputs"]:
        faults.append(f"a job's trials go up or come back otherwise: {job['inputs']} {job['outputs']}")
    if job["command"][-1].count("|| echo") != 2 or "; " not in job["command"][-1]:
        faults.append(f"a failed trial ends its job: {job['command'][-1]}")
    if job["minutes"] != cluster.START_MINUTES + cluster.CLIP_MINUTES * 4:
        faults.append(f"a job of a 540-frame trial and a 90-frame one has {job['minutes']} minutes, not 3 clips and 1")
    return faults + gpu_cap_faults(folder / "measure")


def gpu_cap_faults(folder):
    """validate's --gpus 7 reaches cluster.py's command line, and cluster.py hands it to the run as its jobs at once."""
    import sys
    import types
    asked = {}
    saved = (validate.subprocess.run, sys.argv, sys.modules.get("keyed_jobs"))
    try:
        validate.subprocess.run = lambda command, **_: asked.update(command=command) or types.SimpleNamespace(
            returncode=0)
        validate.ran_on_cluster(types.SimpleNamespace(folder=folder, who="w", per_job=2, gpus=7, name=None))
        sys.argv = ["cluster", str(folder), "--who", "w", "--per-job", "2", "--gpus", "7"]
        sys.modules["keyed_jobs"] = types.SimpleNamespace(run=lambda *_, parallel=None, **__: asked.update(
            parallel=parallel) or [])
        cluster.main()
    finally:
        validate.subprocess.run, sys.argv = saved[:2]
        if saved[2] is None:
            sys.modules.pop("keyed_jobs", None)
        else:
            sys.modules["keyed_jobs"] = saved[2]
    command = asked.get("command", [])
    if "--gpus" not in command or command[command.index("--gpus") + 1] != "7" or asked.get("parallel") != 7:
        return [f"the GPU cap: validate asks {command}, cluster runs {asked.get('parallel')} at once, not 7"]
    return []


def path_name_faults():
    """A run's joint names as Newton gives them (the body path before the joint's own name) find each coordinate once;
    a look-alike (knee_angle_rotation2_r) is never taken for it."""
    names = ["Body_pelvis_femur_r__j0_hip_flexion_r", "tibia_r__j2_knee_angle_r", "tibia_r_knee_angle_rotation2_r"]
    found = [_run.coordinate_column(names, name) for name in ("hip_flexion_r", "knee_angle_r", "ankle_angle_r")]
    return [] if found == [0, 1, None] else [f"path names read as columns {found}"]


def floor_faults():
    """A camera 1.5 m over a floor it sees 5 degrees off its own level (MoGe-2's point map, OpenCV's axes), a person
    3 m ahead whose box hides part of it, GEM-X's world holding its camera level: `seen` finds the floor's normal 5
    degrees off GEM-X's up and pointing up, and `levelled` turns the clip so that normal is the world's up."""
    from tools.labval import _floor

    height, width, tilt = 120, 90, np.radians(5.0)
    up = np.array([0.0, -np.cos(tilt), np.sin(tilt)])  # the floor's normal in the camera, pointing up (y is down)
    rows, cols = np.indices((height, width))
    rays = np.stack([(cols - width / 2) / 100.0, (rows - height / 2) / 100.0, np.ones((height, width))], axis=-1)
    depth = -1.5 / (rays @ up)  # where each ray meets the plane n . x = -1.5 (the camera 1.5 m over it)
    below = depth > 0
    points = np.where(below[..., None], rays * depth[..., None], np.nan)
    moge = {"frames": np.array([0]), "stride": 1, "points": points[None], "mask": below[None],
            "normal": np.broadcast_to(up, (1, height, width, 3))}
    frames = 2
    flip = np.tile(Rotation.from_euler("z", 180, degrees=True).as_rotvec(), (frames, 1))  # GEM-X's world: y up
    world = np.tile(np.eye(4), (frames, 2, 1, 1))
    world[:, :, :3, 3] = [[0.0, -1.0, 3.0], [0.0, -0.5, 3.0]]  # Root on the floor under the Hips
    gemx = {"global_orient": flip, "incam_global_orient": np.zeros((frames, 3)), "joint_names": np.array(["Root", "Hips"]),
            "world_transforms": world, "root_translation": np.zeros((frames, 3)), "incam_transl": np.zeros((frames, 3)),
            "joints": world[:, :, :3, 3] + [[[0.0, 0.0, 0.0], [0.1, 0.3, 0.0]]], "source_frame": np.arange(frames),
            "K": np.tile([[100.0, 0.0, width / 2], [0.0, 100.0, height / 2], [0.0, 0.0, 1.0]], (frames, 1, 1)),
            "static_conf_logits": np.zeros((frames, 6))}
    faults = []
    floor = _floor.seen(moge, gemx)
    if floor is None or np.degrees(np.arccos(np.clip(np.dot(floor["normal"], up), -1, 1))) > 0.01:
        faults.append(f"the seen floor's normal is {floor and np.round(floor['normal'], 4)}, not {np.round(up, 4)}")
    elif abs(floor["tilt deg"][0] - 5.0) > 0.01:
        faults.append(f"the seen floor stands {floor['tilt deg'][0]:.3f} degrees off GEM-X's up, not 5")
    else:
        moved, angle, _ = _floor.levelled(world, gemx, floor["normal"])
        turned = moved[0, 0, :3, :3] @ _floor.camera_to_world(gemx)[0] @ np.asarray(floor["normal"])
        if np.abs(turned - [0.0, 1.0, 0.0]).max() > 1e-6 or abs(angle - 5.0) > 0.01:
            faults.append(f"levelled puts the floor's normal at {np.round(turned, 4)} ({angle:.3f} degrees), not up")
    return faults


def moment_curve(index, times):
    """A synthetic generalized force (N m) of MOMENTS' coordinate `index` at times."""
    return 40.0 * np.sin(2 * np.pi * (0.5 + 0.07 * index) * times + index)


def moment_faults(tmp):
    """The synthetic trial's moments scored end to end (the run's every coordinate 1 % of body weight times height
    over a reference npz in on_opensim's layout, its lumbar on the sacrum's joint beside a decoy lumbar level), then
    the peaks' hand cases."""
    root = tmp / "LabValidation"
    write_labval(root)
    write_run(tmp / "run")
    scale = 70.0 * _files.G * 1.75
    ref_times = np.arange(0.0, 3.0, 0.01)
    names = list(_moments.MOMENTS)
    np.savez(tmp / "subject2_walking1.npz", time=ref_times, names=np.array([f"{name}_moment" for name in names]),
             values=np.stack([moment_curve(index, ref_times) for index in range(len(names))], axis=1),
             kam_r=0 * ref_times, kam_l=0 * ref_times, external_kam_r=0 * ref_times, external_kam_l=0 * ref_times)
    out = tmp / "run" / "out.json"
    run = json.loads(out.read_text())
    entry = next(iter(run["people"].values()))
    lumbar = {"lumbar_extension": "sacrum_lumbar5__j0_flex_extension",
              "lumbar_bending": "sacrum_lumbar5__j0_lumbar5__j1_lat_bending",
              "lumbar_rotation": "sacrum_lumbar5__j0_lumbar5__j1_lumbar5_axial_rotation"}  # a cluster run's names
    entry["joints"] = ["lumbar4_lumbar3__j0_L3_L4_FE", "lumbar3__j1_L3_L4_LB", "lumbar3__j1_lumbar3_L3_L4_AR",
                       *(lumbar.get(name, f"Full_Body_pelvis__j0_{name}") for name in names)]
    at = START + np.arange(len(entry["frames"])) / RATE + TAU
    for frame, time in zip(entry["frames"], at):
        frame["torques"] = [9.9e3, 9.9e3, 9.9e3, *(moment_curve(index, time) + 0.01 * scale for index in range(len(names)))]
    out.write_text(json.dumps(run))
    found = labval.moments_scored(tmp / "run", root, tmp)
    faults = []
    for name in names:
        row = found["moments"]["moments"][name]
        if abs(row["mae %bw.ht"] - 1.0) > 0.02 or row["r"] < 0.999:
            faults.append(f"moment {name} {row}")
    pooled = _moments.pooled([found, {**found, "subject": "subject3"}])["all"]
    if abs(pooled["opencap 15 mae %bw.ht"]["mean"] - 1.0) > 0.02:
        faults.append(f"pooled moments {pooled['opencap 15 mae %bw.ht']}")
    clock = np.arange(16) * 0.05  # the second stance runs off the record's end
    loaded = np.array([0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 1, 1, 1, 1, 1, 1], dtype=bool)
    kam = np.array([0, 0, 1, 2, 1, 1, 3, 1, 0, 0, 1, 1, 1, 1, 1, 1], dtype=float) * scale / 100.0
    windows = _moments.stances(clock, loaded)
    peaks = _moments.early_peaks(clock, kam + 0.005 * scale, clock, kam, windows, scale)
    if len(windows) != 1 or not np.allclose(windows[0], (0.1, 0.35)) or peaks != [(2.5, 2.0)]:
        faults.append(f"early peaks {windows} {peaks}")
    knee = -np.array([1.0, 4.0, 2.0]) * scale / 100.0
    if _moments.peak_extension(knee, 2 * knee, scale) != (4.0, 8.0):
        faults.append(f"peak extension {_moments.peak_extension(knee, 2 * knee, scale)}")
    times = np.arange(0.0, 3.0, 0.01)
    phase = _moments.rising(times, 0.5 + 0.4 / (1 + np.exp(-(times - 1.5) * 10)))
    if not (phase[np.searchsorted(times, 1.25)] and not phase[np.searchsorted(times, 0.8)] and phase[-1]):
        faults.append(f"rising phase {times[phase][[0, -1]] if phase.any() else 'none'}")
    peaks = _moments.peak_pooled({"a": [(1.0, 1.5)], "b": [(2.0, 2.5)], "c": [(3.0, 3.5)]})
    if abs(peaks["mae %bw.ht"] - 0.5) > 1e-9 or abs(peaks["r2 of subject means"] - 1.0) > 1e-9:
        faults.append(f"peak pooled {peaks}")
    return faults


def validate_faults(tmp):
    """The final validation's groups, measure rows and per-step timing on hand-made trials and out.json."""
    faults = []
    trials = [{"activity": activity, "camera": camera} for activity in ("walking", "squats") for camera in ("Cam0",
                                                                                                          "Cam1")]
    groups = validate.groups_of(trials[:3])
    if sorted(groups) != sorted(["all", "walking", "squats", "Cam0", "Cam1", "walking | Cam0", "walking | Cam1",
                                 "squats | Cam0"]) or len(groups["Cam0"]) != 2:
        faults.append(f"validate groups {sorted(groups)}")
    grouped = {"all": {"trials": 2, "subjects": 1, "angles": {"coordinates": {"knee_angle_r": {
        "mae": {"mean": 4.0, "low": 3.0, "high": 5.0, "values": 2}, "r": 0.9}}, "matched mae": None}}}
    rows = validate.measure_rows(grouped, ("angles",))
    if [row[3:5] for row in rows[1:]] != [["angles coordinates knee_angle_r mae", "4.000"],
                                          ["angles coordinates knee_angle_r r", "0.900"]]:
        faults.append(f"validate rows {rows}")
    for name, frames in (("a", 10), ("b", 20)):
        (tmp / name).mkdir(parents=True)
        (tmp / name / "out.json").write_text(json.dumps({"card": "NVIDIA L4", "people": {"p": {
            "frames": [{}] * frames, "seconds": {"fit": 2.0 * frames, "total": 3.0 * frames}}}}))
    timing = {row[1]: row for row in validate.timing_rows([tmp / "a", tmp / "b"])[1:]}
    if timing["fit"][2:5] != ["2", "30.000", "20.000"] or timing["fit"][6] != "2.000" or timing["total"][6] != "3.000":
        faults.append(f"validate timing {timing}")
    return faults


def motor_tune_faults(tmp):
    """MOTOR step 3's tuning folders: a variant's job carries its settings, a held-out subject is refused, and the
    landmarks' learned weights are the median's over each one's pooled mean squared miss, inside WEIGHT_RANGE."""
    from tools.labval import motor_tune
    faults = []
    for name in ("subject2_walking1_Cam1", "subject7_walking1_Cam1"):
        trial = tmp / "source" / "trials" / name
        trial.mkdir(parents=True)
        for kept in ("targets.npz", "record.json"):
            (trial / kept).write_text("x")
        (trial / "job.json").write_text(json.dumps({"people": [{"targets": str(trial / "targets.npz")}]}))
    try:
        motor_tune.made(tmp / "source", tmp / "tuned", [("a", {"friction": 0.6})])
        faults.append("a held-out subject's trial tuned on")
    except SystemExit:
        pass
    (tmp / "source/trials/subject7_walking1_Cam1/job.json").unlink()
    folder, = motor_tune.made(tmp / "source", tmp / "tuned", [("a", {"friction": 0.6})])
    job = json.loads((folder / "trials/subject2_walking1_Cam1/job.json").read_text())
    if (job.get("motor"), job.get("motor settings")) != ("dynamics", {"friction": 0.6}) or not job["people"][0][
            "targets"].startswith(str(folder.resolve())):
        faults.append(f"the variant's job {job}")
    misses = [{"a": 1.0, "b": 2.0, "c": 4.0, "d": 100.0}, {"a": 1.0, "b": 2.0, "c": 4.0, "d": 100.0}]
    for index, miss in enumerate(misses):
        trial = tmp / "runs" / "trials" / f"subject{3 + index}_squats1_Cam1"
        trial.mkdir(parents=True)
        (trial / "out.json").write_text(json.dumps({"people": {"p": {"model": {"motor": {"dynamics": {
            "landmark errors mm": miss}}}}}}))
    weights = motor_tune.learned([tmp / "runs"])
    if weights != {"a": 5.0, "b": 2.5, "c": 0.625, "d": 0.2}:
        faults.append(f"the landmarks' learned weights {weights}")
    return faults


def test_a_labvalidation_trial_scores_the_errors_built_into_it(tmp_path):
    faults = [*scoring_faults(tmp_path / "scoring"), *hand_faults(), *loader_faults(tmp_path / "loaders"),
              *grf_faults(), *soma_faults(), *go_faults(tmp_path / "go"), *unseen_faults(),
              *cluster_faults(tmp_path / "cluster"), *path_name_faults(), *floor_faults(),
              *moment_faults(tmp_path / "moments"), *validate_faults(tmp_path / "validate"),
              *neutral_faults(tmp_path / "neutral"), *motor_tune_faults(tmp_path / "motor_tune")]
    assert not faults, faults
