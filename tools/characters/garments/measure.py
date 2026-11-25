"""A person's body measured as GarmentCode measures a body (pygarment's 26 body measurements, centimetres), so its
sewing patterns are sized to the body that wears them (PRD #223, #225). Numpy and scipy only, in the score venv.

The body is the person's SOMA surface at its bind (A-pose, metres, y up, feet at 0, facing +z): its points, triangles,
skin weights and joints. What a tape or a level reads off it is measured here: the height, the neck base, the bust,
waist and hips (each its torso girth and level), the thigh and wrist girths, the arm's length and angle, the shoulder
width, the front's length from the waist over the bust to the neck's base. What a surface tape cannot read off a bare
mesh without landmarks (GarmentCode's armscye depth, bust and bum
points, back widths, slopes, the bust's vertical line, the neck's width) is GarmentCode's own mean body's number carried
to this body: scaled by the girth it follows (FOLLOWS), or by the height, and its angles kept (ANGLES). The mean body's
numbers are its measurement file (assets/bodies/mean_female.yaml or mean_male.yaml, MIT, from GarmentMeasurements' own
body model); no SMPL body file is read.
"""
import numpy as np
from scipy.spatial import ConvexHull

CENTIMETRES = 100.0
# Measurements GarmentCode keeps as angles of the body rather than lengths.
ANGLES = ("arm_pose_angle", "hip_inclination", "shoulder_incl")
# Widths and girths not read here that follow a girth read on both bodies rather than the height.
FOLLOWS = {"underbust": "bust", "back_width": "bust", "waist_back_width": "waist", "hip_back_width": "hips"}
LIMBS = ("Arm", "ForeArm", "Hand", "Shoulder", "Leg", "Shin", "Foot", "Toe")
SCAN = 25  # levels tried in each band a girth is looked for in
BIN_M = 0.005  # the height steps a front's profile is read at


def section(points, faces, origin, normal):
    """Where the plane through `origin` with `normal` cuts the triangles: the cut's points (m)."""
    normal = np.asarray(normal, dtype=float) / np.linalg.norm(normal)
    side = (points - origin) @ normal
    found = []
    for first, second in ((0, 1), (1, 2), (2, 0)):
        one, other = side[faces[:, first]], side[faces[:, second]]
        crossing = (one < 0) != (other < 0)  # a corner on the plane counts on its upper side
        share = one[crossing] / (one[crossing] - other[crossing])
        start, end = points[faces[crossing, first]], points[faces[crossing, second]]
        found.append(start + (end - start) * share[:, None])
    return np.concatenate(found) if found else np.zeros((0, 3))


def girth(points, faces, origin, normal):
    """A tape's girth round the cut (m): the perimeter of the cut's convex hull in its plane; 0 with no cut."""
    cut = section(points, faces, np.asarray(origin, dtype=float), normal)
    if len(cut) < 3:
        return 0.0
    normal = np.asarray(normal, dtype=float) / np.linalg.norm(normal)
    helper = np.array([1.0, 0.0, 0.0]) if abs(normal[0]) < 0.9 else np.array([0.0, 0.0, 1.0])
    first = np.cross(normal, helper)
    first /= np.linalg.norm(first)
    second = np.cross(normal, first)
    flat = np.stack([(cut - origin) @ first, (cut - origin) @ second], axis=1)
    return float(ConvexHull(flat).area)  # a hull's 'area' in two dimensions is its perimeter


def faces_of(faces, weights, names, keep):
    """The triangles whose corners' strongest joints all pass `keep` (a test on the joint's name)."""
    held = np.array([keep(names[joint]) for joint in np.asarray(weights).argmax(axis=1)])
    return faces[held[faces].all(axis=1)]


def is_torso(name):
    return not any(word in name for word in LIMBS)


def is_left_arm(name):
    return name.startswith("Left") and any(word in name for word in ("Arm", "ForeArm", "Hand"))


def is_left_leg(name):
    return name.startswith("Left") and any(word in name for word in ("Leg", "Shin"))


def level_girths(points, faces, low, high):
    """(girth, level) of each level from `low` to `high` (m) on the horizontal cut."""
    return [(girth(points, faces, [0.0, level, 0.0], [0.0, 1.0, 0.0]), level) for level in np.linspace(low, high, SCAN)]


def over_bust(points, faces, bust_level, waist_level, neck_level):
    """GarmentCode's waist_over_bust_line (m): the front's length from the waist level over the bust point up to the
    neck's base level (or the shoulder's top, when it is lower there), in the upright plane through each side's bust
    point (the bust level's most forward point that side), the mean of the two sides. Carried from the mean body by
    the height, a slim woman's bodice front was cut 6 cm longer than her front and bunched under the bust
    (2026-11-24)."""
    level = section(points, faces, np.array([0.0, bust_level, 0.0]), [0.0, 1.0, 0.0])
    lengths = []
    for side in (1.0, -1.0):
        mine = level[side * level[:, 0] > 0.0]
        apex = mine[mine[:, 2].argmax()]
        cut = section(points, faces, apex, [1.0, 0.0, 0.0])
        cut = cut[cut[:, 2] > 0.0]
        profile = []
        for height in np.arange(waist_level, neck_level + BIN_M / 2.0, BIN_M):
            near = cut[np.abs(cut[:, 1] - height) < BIN_M / 2.0]
            if len(near):
                profile.append((height, near[:, 2].max()))
        profile = np.asarray(profile)
        lengths.append(float(np.linalg.norm(np.diff(profile, axis=0), axis=1).sum()))
    return float(np.mean(lengths))


def measured(points, faces, weights, names, bind):
    """The body's own measurements (centimetres and degrees): height, head_l, bust, waist, hips, their lines, leg_circ,
    wrist, arm_length, arm_pose_angle, shoulder_w (between the shoulder joints) and waist_over_bust_line."""
    names = [str(name) for name in names]
    joint = {name: np.asarray(bind[names.index(name)])[:3, 3] for name in names}
    torso = faces_of(faces, weights, names, is_torso)
    no_arms = faces_of(faces, weights, names,
                       lambda name: not any(word in name for word in ("Arm", "Hand", "Shoulder")))
    floor, top = points[:, 1].min(), points[:, 1].max()
    strongest = np.asarray(weights).argmax(axis=1)
    # the neck's base: the top of the skin the chest and shoulders carry (the trapezius beside the neck)
    neck = points[np.isin(strongest, [names.index(name) for name in ("Chest", "LeftShoulder", "RightShoulder")]),
                  1].max()
    waist = min(level_girths(points, torso, joint["Hips"][1] + 0.02, joint["Chest"][1]))
    bust = max(level_girths(points, torso, joint["Chest"][1], (joint["Chest"][1] + joint["LeftArm"][1]) / 2.0))
    hips = max(level_girths(points, no_arms, joint["LeftLeg"][1] - 0.12, joint["Hips"][1]))
    thigh = max(level_girths(points, faces_of(faces, weights, names, is_left_leg), joint["LeftShin"][1] + 0.25,
                             joint["LeftLeg"][1] - 0.05))
    arm = joint["LeftHand"] - joint["LeftArm"]
    forearm = joint["LeftHand"] - joint["LeftForeArm"]
    arm_faces = faces_of(faces, weights, names, is_left_arm)
    wrist = min(value for value in (girth(points, arm_faces, joint["LeftForeArm"] + forearm * share, forearm)
                                    for share in np.linspace(0.7, 0.95, SCAN)) if value > 0)
    found = {"height": top - floor, "head_l": top - neck, "bust": bust[0], "waist": waist[0], "hips": hips[0],
             "bust_line": neck - bust[1], "waist_line": neck - waist[1], "hips_line": waist[1] - hips[1],
             "leg_circ": thigh[0], "wrist": wrist, "arm_length": float(np.linalg.norm(arm)),
             "shoulder_w": float(np.linalg.norm(joint["LeftArm"] - joint["RightArm"])),
             "waist_over_bust_line": over_bust(points, torso, bust[1], waist[1], neck)}
    found = {key: float(value) * CENTIMETRES for key, value in found.items()}
    found["arm_pose_angle"] = float(np.degrees(np.arcsin(-arm[1] / np.linalg.norm(arm))))
    return found


def below_knee(points, faces, weights, names, bind):
    """The lower leg's measures a trouser leg is tapered to (centimetres; the left leg, not one of GarmentCode's 26):
    `knee_circ` the girth at the knee joint, `knee_h` that joint's height over the sole, `calf_circ` the largest girth
    between the knee and the ankle and `calf_h` its height. GarmentCode's Pants run straight from the thigh to the hem,
    so a slim leg cut to its thigh and hem alone stood 15 cm wide of the knee and gathered at the calf (#225)."""
    names = [str(name) for name in names]
    joint = {name: np.asarray(bind[names.index(name)])[:3, 3] for name in ("LeftShin", "LeftFoot")}
    floor = points[:, 1].min()
    leg = faces_of(faces, weights, names, is_left_leg)
    knee = girth(points, leg, [0.0, joint["LeftShin"][1], 0.0], [0.0, 1.0, 0.0])
    calf = max(level_girths(points, leg, joint["LeftFoot"][1] + 0.05, joint["LeftShin"][1] - 0.04))
    found = {"knee_circ": knee, "knee_h": joint["LeftShin"][1] - floor, "calf_circ": calf[0], "calf_h": calf[1] - floor}
    return {key: float(value) * CENTIMETRES for key, value in found.items()}


def sized(mean, ours):
    """GarmentCode's 26 measurements for the body: each read here as it is, the rest the mean body's (`mean`,
    centimetres) carried over: an angle kept, a FOLLOWS width by its girth's ratio, any other length by the height's."""
    found = {}
    for key, value in mean.items():
        if key in ours:
            found[key] = ours[key]
        elif key in ANGLES:
            found[key] = value
        elif key in FOLLOWS:
            found[key] = value * ours[FOLLOWS[key]] / mean[FOLLOWS[key]]
        else:
            found[key] = value * ours["height"] / mean["height"]
    return {key: round(float(value), 4) for key, value in found.items()}
