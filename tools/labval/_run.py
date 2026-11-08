"""A sim body run's own record (inside/sim_body.py's out.json and out.npz) read as LabValidation's reference is:
joint angles under LaiUhlrich2022's coordinate names, each foot's ground reaction force and centre of pressure, the
tibias' frames, the residual, the muscles' activations, every series on the run's own frame times.

MyoFullBody's legs are OpenSim's (myo_sim from Rajagopal et al. 2016, which Lai et al. 2017 and LaiUhlrich2022 build
on): its hip, knee, ankle, subtalar and mtp coordinates carry the same names, axes and signs, so they are taken as
they are (`<name>/coordinates`, radians). Its pelvis and torso bodies' frames are OpenSim's (x forward, y up, z to
the right at zero coordinates: the sacrum's and the pelvis' one turn, no turn on the lumbar levels or the torso), so
the pelvis' tilt, list and rotation and the lumbar's extension, bending and rotation are the intrinsic Z, X, Y angles
of the pelvis in the lab and of the torso on the pelvis, as LaiUhlrich2022's ground_pelvis and back joints turn.

The arms (MyoFullBody's are Holzbaur et al. 2005's, LaiUhlrich2022's Rajagopal et al. 2016's): at zero coordinates
both models' humerus, ulna and radius frames are the torso's (MyoFullBody's humerus within 0.05 degrees, through its
clavicle and scapula). So the shoulder's arm_flex, arm_add and arm_rot are the intrinsic Z, X, Y angles of the
humerus on the torso, as acromial_r turns (acromial_l's X and Y axes are -x and -y: the left's two negated); the
elbow's flexion is MyoFullBody's own, as it is (both models: the ulna on the humerus about the frame's near-z axis,
flexion positive, the two axes 10.3 degrees apart). The forearm's pro_sup is the same turn (the radius on the ulna
about the forearm's axis, the two 8.2 degrees apart, pronation positive), but its zero is another forearm:
LaiUhlrich2022's is full supination (its radial wrist marker lateral at zero, 0 to 120 degrees), MyoFullBody's is
neutral (its scaphoid forward at zero, -90 to 90), so only its offset-free measures are scored (`OWN_ZERO`).
Neither model's wrist is in LaiUhlrich2022's IK (radius_hand is welded)."""
import json
import pathlib

import numpy as np
from scipy.spatial.transform import Rotation

# MyoFullBody coordinate -> LaiUhlrich2022 coordinate, the legs (same names, axes and signs; module docstring).
LEGS = tuple(f"{stem}_{side}" for side in "rl" for stem in ("hip_flexion", "hip_adduction", "hip_rotation",
                                                             "knee_angle", "ankle_angle", "subtalar_angle",
                                                             "mtp_angle"))
PELVIS = ("pelvis_tilt", "pelvis_list", "pelvis_rotation")  # intrinsic Z, X, Y of the pelvis in the lab
LUMBAR = ("lumbar_extension", "lumbar_bending", "lumbar_rotation")  # intrinsic Z, X, Y of the torso on the pelvis
ELBOWS = ("elbow_flex_r", "elbow_flex_l")  # MyoFullBody's own, as they are (module docstring)
FOREARMS = ("pro_sup_r", "pro_sup_l")  # MyoFullBody's own, its zero neutral where LaiUhlrich2022's is supinated
OWN_ZERO = FOREARMS  # coordinates whose zero differs between the models: cMAE and r only, never MAE or RMSE
# The subject's own standing pose (its static trial's run, `labval.neutral`) taken as the model's neutral, as a static
# calibration does in motion capture: the pelvis turned about its own z axis by its standing tilt, the lumbar's
# extension and the elbows less their standing values. The subject's own video only, never the lab's angles.
NEUTRAL = ("pelvis_tilt", "lumbar_extension", *ELBOWS)
# side -> (humerus, LaiUhlrich2022's shoulder coordinates, the signs of its intrinsic Z, X, Y on the torso)
SHOULDERS = {"r": ("humerus_r", ("arm_flex_r", "arm_add_r", "arm_rot_r"), np.array([1.0, 1.0, 1.0])),
             "l": ("humerus_l", ("arm_flex_l", "arm_add_l", "arm_rot_l"), np.array([1.0, -1.0, -1.0]))}
FEET = {"right": "RightFoot", "left": "LeftFoot"}  # the run's touches, by its Foot segment's name
# The lab's force plates lie in its floor: a foot's push whose centre of pressure stands over OFF_FLOOR (a drop jump's
# box, `_supports.box`; the plates read 0 there, 2026-11-07) is not a plate's to measure.
OFF_FLOOR = 0.015  # m: half the least box `_supports.BOX_LOW` lays
TIBIAS = {"right": "tibia_r", "left": "tibia_l"}


def read(trial_folder):
    """(the run's one person's out.json entry, its arrays by their own names without the person's prefix, the run's
    rate): a trial's run folder holds out.json and out.npz with one person."""
    folder = pathlib.Path(trial_folder)
    run = json.loads((folder / "out.json").read_text())
    if len(run["people"]) != 1:
        raise ValueError(f"{folder}: {len(run['people'])} people in its run, a trial has one")
    (name, entry), = run["people"].items()
    with np.load(folder / "out.npz") as saved:
        arrays = {key[len(name) + 1:]: saved[key] for key in saved.files if key.startswith(f"{name}/")}
    return entry, arrays, float(run["rate"])


def body_turns(entry, arrays, body):
    """A drawn body's turn in the person's frame every frame (frames x 3 x 3), from `bones` ([x, y, z, qx, qy, qz,
    qw] in the order of the entry's `bones`)."""
    if body not in entry["bones"]:
        raise ValueError(f"no drawn body {body!r} in the run (its bones: {entry['bones'][:8]}...)")
    return Rotation.from_quat(arrays["bones"][:, entry["bones"].index(body), 3:]).as_matrix()


def body_places(entry, arrays, body):
    """A drawn body's origin in the person's frame every frame (frames x 3, m)."""
    return arrays["bones"][:, entry["bones"].index(body), :3].astype(float)


def heading(turns):
    """The mean heading (radians about up) of frames' forward (x) axes: Ry(heading) takes x to it."""
    forward = turns[:, :, 0]
    return float(np.arctan2(-forward[:, 2].sum(), forward[:, 0].sum()))


def about_up(angle):
    """The turn by `angle` (radians) about y."""
    return Rotation.from_euler("y", angle).as_matrix()


def zxy(turns):
    """Intrinsic Z, X, Y angles (degrees, frames x 3) of turns: OpenSim's CustomJoint order for the pelvis and back."""
    return np.degrees(Rotation.from_matrix(turns).as_euler("ZXY"))


def coordinate_column(names, name):
    """The column of MyoFullBody's coordinate `name` among the run's joint names: the name itself, or the one name
    that ends in `_<name>` (Newton names a joint by its body path, `..._femur_r__j0_hip_flexion_r`); None when none or
    several do."""
    if name in names:
        return names.index(name)
    ending = [column for column, found in enumerate(names) if found.endswith(f"_{name}")]
    return ending[0] if len(ending) == 1 else None


def angles(entry, arrays, lab_heading, neutral=None):
    """{LaiUhlrich2022 coordinate: degrees every frame}: the legs', elbows' and forearms' MyoFullBody coordinates as
    they are, the pelvis' angles once its mean heading is turned onto `lab_heading` (radians: the reference's,
    `heading`), the lumbar's of the torso on the pelvis, the shoulders' of each humerus on the torso. With `neutral`
    ({NEUTRAL coordinate: degrees}, the subject's standing pose) each is taken from its standing value: the pelvis
    turned about its own z by its standing tilt before its angles are read (so a heading either way along the lab
    keeps the tilt's sign), the lumbar's extension and the elbows less theirs. A run without `coordinates` raises: the
    run must save them (inside/sim_body.py)."""
    if "coordinates" not in arrays:
        raise ValueError("the run saved no coordinates (inside/sim_body.py's <name>/coordinates)")
    names = [str(name) for name in arrays["coordinate names"]]
    columns = {name: coordinate_column(names, name) for name in (*LEGS, *ELBOWS, *FOREARMS)}
    lacking = [name for name, column in columns.items() if column is None]
    if lacking:
        raise ValueError(f"the run's coordinates lack {lacking}")
    found = {name: np.degrees(arrays["coordinates"][:, column].astype(float)) for name, column in columns.items()}
    standing = neutral or {}
    pelvis = body_turns(entry, arrays, "pelvis")
    upright = pelvis @ Rotation.from_euler("z", -standing.get("pelvis_tilt", 0.0), degrees=True).as_matrix()
    turned = about_up(lab_heading - heading(upright)) @ upright
    found.update(zip(PELVIS, zxy(turned).T))
    torso = body_turns(entry, arrays, "torso")
    found.update(zip(LUMBAR, zxy(np.swapaxes(pelvis, 1, 2) @ torso).T))
    for humerus, coordinates, signs in SHOULDERS.values():
        found.update(zip(coordinates, (zxy(np.swapaxes(torso, 1, 2) @ body_turns(entry, arrays, humerus)) * signs).T))
    for name in ("lumbar_extension", *ELBOWS):
        found[name] = found[name] - standing.get(name, 0.0)
    return found


def pushes(entry):
    """{side: (force frames x 3 N, centre of pressure frames x 3 m)} of each foot on the lab's floor, the person's
    frame; zero (and the centre nan) on a frame the floor does not push it (no push, or one off the floor, OFF_FLOOR:
    a box's)."""
    found = {}
    for side, foot in FEET.items():
        rows = [frame["touches"].get(foot) or [0.0, 0.0, 0.0, np.nan, np.nan, np.nan] for frame in entry["frames"]]
        rows = np.array(rows, dtype=float)
        rows[rows[:, 4] > OFF_FLOOR] = [0.0, 0.0, 0.0, np.nan, np.nan, np.nan]
        found[side] = (rows[:, :3], rows[:, 3:])
    return found


def residuals(entry):
    """(force frames x 3 N, moment frames x 3 N m) on the pelvis every frame."""
    rows = np.array([frame["residual"] for frame in entry["frames"]], dtype=float)
    return rows[:, :3], rows[:, 3:]


def activations(entry):
    """{muscle: activation 0..1 every frame}."""
    rows = np.array([frame["activations"] for frame in entry["frames"]], dtype=float)
    return {name: rows[:, column] for column, name in enumerate(entry["muscles"])}
