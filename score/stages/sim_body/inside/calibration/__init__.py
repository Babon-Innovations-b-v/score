"""The static calibration table (#70; pure numpy): for each bone group, the fixed turn between SOMA's segment frame
and MyoFullBody's group frame (`turn`), so the group's body turns as R_body = R_segment @ R_cal. It is read once from
the two models' rest poses, SOMA's rest skeleton (its template rig's bind) against MyoFullBody's default pose (its
couplings applied: MyoSuite's `stand`), the same for every person and every clip, never fitted, so it cannot absorb a
person's posture such as a curved spine. `_measure.py` (Newton's Python) measures it again and prints `TABLE`.

`aligned` is the maths: each rest's anatomical axes (columns: the long axis, from the stretch's start to its end, the
reference axis crossed with it, and the reference axis made square to it; `frame`), in SOMA's segment frame (a_s)
and in the group body's frame (a_m), R_cal = a_s a_m^T: the body frame in the segment frame when the two rests' bones
lie along each other. The long axis runs between the group's two end joints, the same ends sizing measures (SOMA's
rig joints, MyoFullBody's joint centres). The reference fixes the twist about the bone (`REFERENCES`), from the same
landmarks on both models (since 2026-10-29, #70; before, SOMA's bind z of the forearm and shin and MyoFullBody's elbow
and knee axes, which left the upper arm turned about 9 degrees on every body): the humerus' epicondyles for upper arm
and forearm (the ulna's flexion axis: SOMA's forearm does not pronate), the femur's for the thigh, the malleoli for
the shin, MC5 head to MC2 head for the hand; the person's own x (left) for the trunk, feet and toes, own y (up) for the
shoulder.

Against taking SOMA's rest as MyoFullBody's default literally, it differs by the two rests' posture (measured
2026-10-28): the arms 48 degrees (SOMA's A-pose), toes 26, shin 12.6, shoulder 12, Spine2 12, Spine1 9.6, head 6.7,
hips 6.1, thigh 5.3, foot 7.2, chest 3.6. SOMA's bind has its knees bent about 15 degrees."""
import numpy as np
from scipy.spatial.transform import Rotation

# Each group's reference axis on SOMA and on MyoFullBody: "own x"/"own y" the person's own axis, "line <a> <b>" the
# line from landmark a to landmark b (`landmarks.LANDMARKS`: on SOMA its point on the template's skin, on MyoFullBody
# its bone point), the same two landmarks on both models.
_ELBOW = "line humerus_medial_epicondyle_{side} humerus_lateral_epicondyle_{side}"
_KNEE = "line femur_medial_epicondyle_{side} femur_lateral_epicondyle_{side}"
REFERENCES = {"Hips": ("own x", "own x"), "Spine1": ("own x", "own x"), "Spine2": ("own x", "own x"),
              "Chest": ("own x", "own x"), "Neck1": ("own x", "own x"), "Neck2": ("own x", "own x"),
              "Head": ("own x", "own x"), "{Side}Shoulder": ("own y", "own y"),
              "{Side}Arm": (_ELBOW, _ELBOW), "{Side}ForeArm": (_ELBOW, _ELBOW),
              "{Side}Hand": ("line MC5_head_{side} MC2_head_{side}",) * 2, "{Side}Leg": (_KNEE, _KNEE),
              "{Side}Shin": ("line medial_malleolus_{side} lateral_malleolus_{side}",) * 2,
              "{Side}Foot": ("own x", "own x"), "{Side}ToeBase": ("own x", "own x")}
# R_cal per bone group as a quaternion (x, y, z, w), printed by `_measure.py` on 2026-10-29 (MyoFullBody of
# MuscleMimic 1.0.6, SOMA's template rig of people-clips-make; the shoulders again that day, their start the
# sternoclavicular centre, no longer the landmark of that name; the hands again on 2026-11-01, MC5_head moved onto the
# little finger's knuckle: the hand turned 14.9 degrees about its long axis). INSIDE_GROUPS' rows read in the skin on
# 2026-11-01 (`_measure.table_rows`): Head 6.6 degrees off its line, Shins 5.5, Feet 1.5, Hips 0.2, ForeArms 0.1.
TABLE = {
    "Hips": (0.664729, 0.747084, 0.000268241, -0.000291347),
    "Spine1": (0.756786, 0.653663, 0.000257497, -0.00029812),
    "Spine2": (0.596189, 0.802841, 0.00165502, 0.00162641),
    "Chest": (0.683552, 0.729902, 0.000118136, -0.000455094),
    "Neck1": (0.770799, 0.637077, -0.000728835, -0.00110972),
    "Neck2": (0.770799, 0.637077, -0.000728836, -0.00110972),
    "Head": (0.743314, 0.668942, 0.000138584, -0.000408699),
    "LeftShoulder": (-0.446904, -0.498353, 0.576873, 0.468122),
    "RightShoulder": (0.498428, -0.446843, -0.46818, 0.576809),
    "LeftArm": (-0.00349838, 0.0330295, 0.698869, 0.714478),
    "RightArm": (0.0330002, 0.00346837, 0.714478, -0.698871),
    "LeftForeArm": (-0.0687563, -0.0554584, 0.679663, 0.728186),
    "RightForeArm": (-0.0555178, 0.0686927, 0.728193, -0.679658),
    "LeftHand": (-0.0829827, -0.0998119, 0.680886, 0.720795),
    "RightHand": (-0.0999123, 0.0829961, 0.720768, -0.680899),
    "LeftLeg": (-0.70709, 0.707102, 0.00266821, 0.00488039),
    "RightLeg": (0.707102, 0.70709, 0.00483335, -0.00262117),
    "LeftShin": (-0.674394, 0.737872, 0.0240203, 0.0126529),
    "RightShin": (0.737871, 0.674394, 0.0126778, -0.0240475),
    "LeftFoot": (0.986649, -0.158671, -0.0255066, -0.026405),
    "RightFoot": (0.158664, 0.986642, 0.0266571, -0.0255472),
    "LeftToeBase": (0.994273, -0.030612, 0.0988721, -0.0266242),
    "RightToeBase": (0.0306151, 0.994272, 0.026656, 0.0988718),
}

# The held fingers' rest turns (radians, each joint by its name without its side, both sides alike): MyoFullBody's
# finger and thumb joints turned so its hand at rest has SOMA's template hand's shape (SOMA has no finger joints, its
# hand one rigid shape; MyoFullBody's fingers are held where they stand, `fit`), each finger bone as deep in SOMA's
# skin as its joints' ranges let it with the hand laid by TABLE and moved as one body to where its palm stands least
# outside, as the fit holds it (`_measure.fingers_measured`); laid in the person's file by `myo._rested`. Never per
# person or per clip. Printed by `_measure.py` on 2026-11-01 (the hands' turns of that day): on the template, 67.6 %
# of the finger bones' vertices outside SOMA's skin at the published zero pose, 24.7 % at the first read (the hand at
# SOMA's Hand joint; the thumb 25 to 45 mm out before, inside after; the index stays out: SOMA's stands dorsal of where
# its metacarpal puts it, and its knuckle does not bend back, range 0 to 90 degrees). Read again with the hand placed
# (#70, 2026-11-01): the fingers bend 6 to 13 degrees more at the knuckles, the thumb's CMC 11 less; on the mean body's
# 15 clips the hand 9.43 -> 5.42 % outside (forearm 2.87 -> 4.27, shoulder 2.07 -> 1.51), all 6.95 -> 6.59 %, the turns
# 4.603 -> 4.587 degrees, joints 14.14 -> 13.43 mm; env1 standing all 13.48 -> 13.43 %, seated 13.82 -> 13.82 %.
FINGERS = {
    "cmc_abduction": -0.3119,
    "cmc_flexion": 0.1645,
    "ip_flexion": -0.0157,
    "mcp2_abduction": 0.0057,
    "mcp2_flexion": 0.0122,
    "mcp3_abduction": -0.0798,
    "mcp3_flexion": 0.1014,
    "mcp4_abduction": -0.046,
    "mcp4_flexion": 0.1215,
    "mcp5_abduction": -0.1579,
    "mcp5_flexion": 0.1115,
    "md2_flexion": 0.1043,
    "md3_flexion": 0.2321,
    "md4_flexion": 0.3481,
    "md5_flexion": 0.1303,
    "mp_flexion": -0.0643,
    "pm2_flexion": 0.025,
    "pm3_flexion": 0.0552,
    "pm4_flexion": 0.0436,
    "pm5_flexion": 0.0715,
}


def fingers():
    """FINGERS written out for both sides ({joint: rest turn})."""
    return {f"{stem}_{side}": angle for stem, angle in FINGERS.items() for side in "lr"}


def turn(group):
    """The group's calibration turn R_cal (3 x 3): the group body's frame in its SOMA segment's frame."""
    return Rotation.from_quat(TABLE[group]).as_matrix()


# The groups whose row is read by laying the group's bones in SOMA's skin at rest (`_measure.inside_measured`: its
# bones moved rigidly to their least depth outside SOMA's template skin, the turn kept; the owner and the coordinator,
# 2026-11-01, for the skull and jaw, then every group where it lowers the bones outside at rest without worsening the
# turns check on the mean body's 15 clips) instead of the landmark lines (#70). Each side named, both sides alike.
# Level 1's worker reads the other rows again from its centres (`remeasured`); these stay as written.
INSIDE_GROUPS = ("Head", "Hips", "LeftForeArm", "RightForeArm", "LeftShin", "RightShin", "LeftFoot", "RightFoot")

# A group end's shift read in SOMA's skin (`_measure.end_shift_measured`; m, the person's frame, Y up): the marker at
# that MyoFullBody centre is moved by -shift (`fit.end_marker`), so SOMA's rig joint holds the group's bones that far off
# it (#70, 2026-11-01). The head's: the skull and jaw laid at the Head row on SOMA's template, 20.6 % of their vertices
# outside its skin at its Head joint, 2.5 % at this shift; on the mean body's 15 clips the head 17.4 -> 13.0 %, env1's
# standing 6.7 -> 3.0 %, seated 5.4 -> 2.7 %, the turns within 0.01 degree. Static like the table: never per person.
END_SHIFTS = {"C0_C1": (0.0, 0.006, 0.008)}

MIRROR = np.diag([-1.0, -1.0, 1.0])  # a right body is its left one mirrored in z: R_right = R_left @ MIRROR


def remeasured(measured):
    """TABLE with `measured`'s rows ({group: quaternion}, the landmark lines read again) for every group but
    INSIDE_GROUPS', whose rows are read in the skin and kept."""
    return {group: TABLE[group] if group in INSIDE_GROUPS else tuple(quaternion)
            for group, quaternion in {**TABLE, **measured}.items()}


def turned(group, rotvec):
    """R_cal of `group` turned by `rotvec` (radians, about the group body's own axes), as a quaternion (x, y, z, w):
    TABLE's turn times exp(rotvec), a right group's rotvec its left one's mirrored (MIRROR @ rotvec), so one rotvec
    turns both sides alike and the table keeps its mirror."""
    rotvec = MIRROR @ np.asarray(rotvec, dtype=float) if group.startswith("Right") else np.asarray(rotvec, dtype=float)
    return Rotation.from_matrix(turn(group) @ Rotation.from_rotvec(rotvec).as_matrix()).as_quat()


def frame(long, reference):
    """Anatomical axes (3 x 3, columns): the long axis, the reference crossed with it, the reference made square."""
    along = np.asarray(long, dtype=float) / np.linalg.norm(long)
    across = np.asarray(reference, dtype=float) - (np.asarray(reference, dtype=float) @ along) * along
    across = across / np.linalg.norm(across)
    return np.column_stack([along, np.cross(across, along), across])


def aligned(soma, myo):
    """R_cal from each rest's (frame turn, long axis, reference axis), all in one shared frame: a_s a_m^T, a_s and
    a_m the anatomical axes in the segment's and the body's frame."""
    (soma_turn, soma_long, soma_reference), (body_turn, myo_long, myo_reference) = soma, myo
    return (soma_turn.T @ frame(soma_long, soma_reference)) @ (body_turn.T @ frame(myo_long, myo_reference)).T
