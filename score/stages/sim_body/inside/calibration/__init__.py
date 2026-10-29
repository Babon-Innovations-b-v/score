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
# MuscleMimic 1.0.6, SOMA's template rig of people-clips-make).
TABLE = {
    "Hips": (0.663583, 0.748103, 0.000268687, -0.000290935),
    "Spine1": (0.756786, 0.653663, 0.000257497, -0.00029812),
    "Spine2": (0.596189, 0.802841, 0.00165502, 0.00162641),
    "Chest": (0.683552, 0.729902, 0.000118136, -0.000455094),
    "Neck1": (0.770799, 0.637077, -0.000728835, -0.00110972),
    "Neck2": (0.770799, 0.637077, -0.000728836, -0.00110972),
    "Head": (0.7035, 0.710695, 0.000156141, -0.000405753),
    "LeftShoulder": (-0.460702, -0.485753, 0.565895, 0.481207),
    "RightShoulder": (0.485804, -0.46066, -0.481248, 0.565852),
    "LeftArm": (-0.00349838, 0.0330295, 0.698869, 0.714478),
    "RightArm": (0.0330002, 0.00346837, 0.714478, -0.698871),
    "LeftForeArm": (-0.0687568, -0.0555397, 0.679171, 0.728639),
    "RightForeArm": (-0.0555991, 0.0686931, 0.728645, -0.679166),
    "LeftHand": (0.0132221, -0.189965, 0.674954, 0.712865),
    "RightHand": (-0.189264, -0.0123465, 0.712952, -0.675075),
    "LeftLeg": (-0.70709, 0.707102, 0.00266821, 0.00488039),
    "RightLeg": (0.707102, 0.70709, 0.00483335, -0.00262117),
    "LeftShin": (-0.698192, 0.715865, -0.00573602, -0.00559442),
    "RightShin": (0.715866, 0.698193, -0.00556864, 0.0057096),
    "LeftFoot": (0.985798, -0.16093, -0.0379763, -0.0293416),
    "RightFoot": (0.16092, 0.985791, 0.0295935, -0.0380175),
    "LeftToeBase": (0.994273, -0.030612, 0.0988721, -0.0266242),
    "RightToeBase": (0.0306151, 0.994272, 0.026656, 0.0988718),
}


def turn(group):
    """The group's calibration turn R_cal (3 x 3): the group body's frame in its SOMA segment's frame."""
    return Rotation.from_quat(TABLE[group]).as_matrix()


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
