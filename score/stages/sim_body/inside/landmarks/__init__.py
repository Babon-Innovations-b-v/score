"""The SOMA mesh landmarks and the MyoFullBody points that match them (#70; pure numpy): the bony landmarks for the
virtual markers (`MARKS`: a SOMA mesh face and barycentric weights, the MyoFullBody body, its bone point and the
marker's starting point on it), MyoFullBody's joint centres (`CENTRES`), each landmark found on a person's own mesh
(`on_skin`), the joint centres the landmarks give on SOMA (`soma_centres`: ISB midpoints, Harrington's hip), a bone
group's stretch ends on SOMA (`soma_point`) and on MyoFullBody (`myo_parts`).

How the table was found (tables study, 2026-10-28, scripts kept with the study, not here): MyoFullBody's points are
LaiUhlrich2022's mocap markers (OpenCap, Apache-2.0) for ASIS, PSIS, the femoral epicondyles, malleoli, heel and MT5,
moved to the nearest bone vertex, and ISB landmarks (Wu et al. 2002, 2005) found on the bone meshes by extreme rules
for the rest. Each was carried into SOMA's rest by its bone group's aligned frames (the calibration table) and length,
then a ray along the landmark's outward direction met SOMA's skin. Confidence: high (soft tissue -8 to 25 mm), medium
(27 to 36 mm: spinous C7, T1-T5, L1, L2, L4, L5, S2, IJ), low (PSIS 44 mm, scapula's inferior angle, clavicle's end,
the MC heads: SOMA's fingers curl). The solver set (`solver` True) leaves out the low ones but PSIS, and the odd
thoracic spinous points. Landmark joint centres against SOMA's joints on the template: elbow 4.2 mm, wrist 4.5,
knee 8.1, ankle 20.6 (SOMA's ankle 19 mm below the malleoli's middle), hip 23.5 (SOMA's hips 19.6 mm wider each)."""
import numpy as np

from landmarks._table import CENTRES, MARKS

# The share of a hand's own vertices furthest from its joint whose mean is the hand's tip (its middle finger's end).
TIP_SHARE = 0.02
# ISB joint centres: the middle of two skin landmarks (Wu et al. 2002, 2005), each side.
MIDDLES = {"knee": ("lateral_epicondyle", "medial_epicondyle"), "ankle": ("lateral_malleolus", "medial_malleolus"),
           "elbow": ("humerus_lateral_epicondyle", "humerus_medial_epicondyle"),
           "wrist": ("radial_styloid", "ulnar_styloid")}
# MyoFullBody centres that are the middle of two others.
MIDDLE_CENTRES = {"hipmid": ("hip_l", "hip_r"), "mid_cervical": ("C7_T1", "C0_C1")}


def on_skin(points, faces):
    """Each landmark on a mesh of SOMA's topology ({name: point}, the mesh's frame)."""
    points, faces = np.asarray(points, dtype=float), np.asarray(faces)
    return {name: np.asarray(row[1]) @ points[faces[row[0]]] for name, row in MARKS.items()}


def solver_marks():
    """The landmarks the solver takes, in MARKS' order ([name])."""
    return [name for name, row in MARKS.items() if row[8]]


def posed(rig, segments, worlds):
    """Each solver landmark on the clip's own skin, every frame (frames x landmarks x 3, the person's frame): its
    face's corners skinned as SOMA skins them (linear blend: each corner the weighted sum of its joints' moves from the
    bind, `worlds` frames x segments x 4 x 4; the rig joints not in `segments` carry no weight), then its barycentric
    weights. `rig`: {"names", "bind", "faces", "weights"}."""
    names = [str(joint) for joint in rig["names"]]
    rows = [MARKS[name] for name in solver_marks()]
    corners = np.asarray(rig["faces"])[[row[0] for row in rows]]  # landmarks x 3
    joints = [names.index(segment) for segment in segments]
    weights = np.asarray(rig["weights"], dtype=float)[corners][:, :, joints]  # landmarks x 3 x segments
    bind = np.asarray(rig["bind"], dtype=float)[joints]
    points = np.asarray(rig["points"], dtype=float)[corners]
    moves = np.asarray(worlds, dtype=float) @ np.linalg.inv(bind)  # frames x segments x 4 x 4
    moved = np.einsum("fsij,lcj->flcsi", moves[..., :3, :3], points) + moves[:, None, None, :, :3, 3]
    skinned = np.einsum("lcs,flcsi->flci", weights, moved)
    return np.einsum("lc,flci->fli", np.array([row[1] for row in rows]), skinned)


def harrington(marks):
    """Each hip joint's centre ({"hip_l", "hip_r"}) from the ASIS and PSIS points (own frame: +x left, Y up): Harrington
    et al. 2007 (J Biomech 40:595), in the pelvis frame at the ASIS' middle (x forward, y up, z right), x = -0.24 PD
    - 9.9 mm, y = -0.30 PW - 10.9 mm, z = +-(0.33 PW + 7.3 mm), PW the ASIS' distance, PD the ASIS' middle to the
    PSIS' along x."""
    middle_front = (marks["ASIS_l"] + marks["ASIS_r"]) / 2
    right = marks["ASIS_r"] - marks["ASIS_l"]
    width = float(np.linalg.norm(right))
    right = right / width
    forward = middle_front - (marks["PSIS_l"] + marks["PSIS_r"]) / 2
    forward = forward - (forward @ right) * right
    depth = float(np.linalg.norm(forward))
    forward = forward / depth
    axes = np.column_stack([forward, np.cross(right, forward), right])
    return {f"hip_{letter}": middle_front + axes @ np.array([-0.24 * depth - 0.0099, -0.30 * width - 0.0109,
                                                              sign * (0.33 * width + 0.0073)])
            for letter, sign in (("l", -1.0), ("r", 1.0))}


def soma_centres(marks):
    """The joint centres the landmarks give ({"knee_l", ..., "hip_r"}): ISB midpoints, Harrington's hips."""
    found = {f"{joint}_{letter}": (marks[f"{one}_{letter}"] + marks[f"{other}_{letter}"]) / 2
             for joint, (one, other) in MIDDLES.items() for letter in "lr"}
    return {**found, **harrington(marks)}


def soma_point(name, rig):
    """A bone group's stretch end on SOMA (own frame, its bind): a rig joint, `hipmid` the hip joints' middle,
    `<Side>Hand tip` the mean of the TIP_SHARE of the hand's own vertices (skin weight over a half) furthest from its
    joint. `rig`: {"names", "bind" (joints x 4 x 4), "points", "weights" (points x joints)}."""
    names = [str(joint) for joint in rig["names"]]
    bind = np.asarray(rig["bind"], dtype=float)
    if name == "hipmid":
        return (bind[names.index("LeftLeg"), :3, 3] + bind[names.index("RightLeg"), :3, 3]) / 2
    if name.endswith(" tip"):
        hand = names.index(name[:-len(" tip")])
        own = np.asarray(rig["points"], dtype=float)[np.asarray(rig["weights"])[:, hand] > 0.5]
        away = np.linalg.norm(own - bind[hand, :3, 3], axis=1)
        return own[away >= np.quantile(away, 1.0 - TIP_SHARE)].mean(axis=0)
    return bind[names.index(name), :3, 3]


def myo_parts(name):
    """A MyoFullBody centre as weighted body points ([(body, local point (source model), weight)])."""
    if name in MIDDLE_CENTRES:
        return [(*CENTRES[part], 0.5) for part in MIDDLE_CENTRES[name]]
    return [(*CENTRES[name], 1.0)]
