"""SCORE's landmark set (#70; CONTEXT.md "landmark set"; pure numpy): each landmark linked once to a point of the SOMA
mesh and to a point on MyoFullBody's bones (`LANDMARKS`), the joint centres the landmarks define, the same rule on
both models (`RULES`, `centre`), MyoFullBody's own joint centres (`CENTRES`, the measure's), each landmark found on a
person's mesh (`on_skin`) and skinned on the clip (`posed`), a sizing stretch's end (`point`), SOMA's own joints as
stretch ends for the measure and the masses (`soma_point`, `myo_parts`) and the links' and trusts' refinement over many
fitted bodies (`refined`).

How the set was found (landmark study, 2026-10-29, scripts kept with the study, not here): every MyoFullBody point by
its anatomical definition, an extreme-vertex rule on one bone mesh (ISB: Wu et al. 2002, 2005; Leardini 2007 for the
foot; Van Sint Jan 2007's atlas), no dataset's marker list read; each carried into SOMA's bind by its bone group's
aligned anatomical frames and length, then a ray along its outward direction met SOMA's skin (a tip: the nearest skin
vertex). A landmark's link is where the skin stood off the carried bone point on the template, turned into the body's
frame; its trust started at s0^2 / (s0^2 + slide^2 + placement^2), s0 5 mm (slide: its skin's move off a rigid point
when SOMA's skin plays the rig's clips), and both are refined over fitted bodies (`refined`). Measure-only (`solver`
False): the scapula's angles and trigonum (SOMA has no scapula: its back skin blends Chest and Shoulder), the greater
tubercle, the olecranon and the finger tips (SOMA has no finger joints, MyoFullBody's fingers are held)."""
import numpy as np

from landmarks._table import CENTRES, LANDMARKS

# The share of a hand's own vertices furthest from its joint whose mean is the hand's tip (its middle finger's end).
TIP_SHARE = 0.02
RAB_DROP = 0.17  # Rab et al. 2002: the glenohumeral centre this share of the acromions' distance below each acromion
# The joint centres the landmarks define (the same rule on SOMA's skin and on MyoFullBody's markers): ISB midpoints
# (Grood and Suntay 1983, Wu et al. 2002, 2005, Leardini 2007), Harrington et al. 2007's hips, Rab et al. 2002's
# shoulders, the sternoclavicular landmark itself; and the middles of pairs.
RULES = {**{f"{joint}_{side}": ("middle", (f"{one}_{side}", f"{other}_{side}"))
            for joint, (one, other) in {"knee": ("femur_lateral_epicondyle", "femur_medial_epicondyle"),
                                        "ankle": ("lateral_malleolus", "medial_malleolus"),
                                        "elbow": ("humerus_lateral_epicondyle", "humerus_medial_epicondyle"),
                                        "wrist": ("radial_styloid", "ulnar_styloid"),
                                        "mtp": ("MT1_head", "MT5_head")}.items() for side in "lr"},
         **{f"hip_{side}": ("harrington", ("ASIS_l", "ASIS_r", "PSIS_l", "PSIS_r")) for side in "lr"},
         **{f"glenohumeral_{side}": ("rab", ("acromion_l", "acromion_r", "jugular_notch", "spinous_C7", "xiphoid",
                                             "spinous_T8")) for side in "lr"},
         "hipmid": ("middle", ("hip_l", "hip_r")), "iliac_mid": ("middle", ("iliac_tubercle_l", "iliac_tubercle_r")),
         "head_mid": ("middle", ("head_side_l", "head_side_r"))}
# The landmarks whose markers hold their link (no move of their own, in the fit or the refinement): the plantar pads
# under the heel and the metatarsal heads (17 and 19 mm of SOMA's sole under the bone on the template; freed, a fit can
# drop the foot's bones through the sole).
HELD = tuple(f"{name}_{side}" for name in ("heel_plantar", "MT_plantar") for side in "lr")
TRUST_SPREAD = 0.005  # metres: s0, a landmark whose leftovers spread this far has half the trust of an exact one
# MyoFullBody centres that are the middle of two others (the measure's).
MIDDLE_CENTRES = {"hipmid": ("hip_l", "hip_r"), "mid_cervical": ("C7_T1", "C0_C1")}


def solver_marks():
    """The landmarks the solver takes, in LANDMARKS' order ([name])."""
    return [name for name, row in LANDMARKS.items() if row[7]]


def trust(name):
    """A landmark's trust (0 to 1): its weight among the solver's markers."""
    return float(LANDMARKS[name][6])


def marker(name, scale):
    """A landmark's marker on its MyoFullBody body (body-local metres): its bone point scaled with the body, then its
    link (not scaled)."""
    row = LANDMARKS[name]
    return np.asarray(row[4], dtype=float) * scale + np.asarray(row[5], dtype=float)


def on_skin(points, faces):
    """Each landmark on a mesh of SOMA's topology ({name: point}, the mesh's frame)."""
    points, faces = np.asarray(points, dtype=float), np.asarray(faces)
    return {name: np.asarray(row[1]) @ points[faces[row[0]]] for name, row in LANDMARKS.items()}


def posed(rig, segments, worlds, names=None):
    """Each of `names` (else the solver's landmarks) on the clip's own skin, every frame (frames x landmarks x 3, the
    person's frame): its face's corners skinned as SOMA skins them (linear blend: each corner the weighted sum of its
    joints' moves from the bind, `worlds` frames x segments x 4 x 4; the rig joints not in `segments` carry no
    weight), then its barycentric weights. `rig`: {"names", "bind", "faces", "weights", "points"}."""
    names_of = [str(joint) for joint in rig["names"]]
    rows = [LANDMARKS[name] for name in (solver_marks() if names is None else names)]
    corners = np.asarray(rig["faces"])[[row[0] for row in rows]]  # landmarks x 3
    joints = [names_of.index(segment) for segment in segments]
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


def rab(marks, side):
    """A glenohumeral centre: RAB_DROP of the acromions' distance below its acromion along the thorax's vertical (ISB,
    Wu et al. 2005: from the middle of the xiphoid and T8 to the middle of the jugular notch and C7)."""
    up = (marks["jugular_notch"] + marks["spinous_C7"]) / 2 - (marks["xiphoid"] + marks["spinous_T8"]) / 2
    up = up / np.linalg.norm(up)
    width = float(np.linalg.norm(marks["acromion_l"] - marks["acromion_r"]))
    return marks[f"acromion_{side}"] - RAB_DROP * width * up


def point(name, marks):
    """A landmark or the joint centre its rule gives (`RULES`), from landmark points `marks` ({name: point}, one frame,
    either model)."""
    if name not in RULES:
        return np.asarray(marks[name], dtype=float)
    kind, parts = RULES[name]
    if kind == "middle":
        return (point(parts[0], marks) + point(parts[1], marks)) / 2
    if kind == "harrington":
        return harrington(marks)[name]
    return rab(marks, name[-1])


def needed(name):
    """The landmarks a point reads ({name})."""
    if name not in RULES:
        return {name}
    return set().union(*(needed(part) for part in RULES[name][1]))


def soma_point(name, rig):
    """A bone group's end at SOMA's own joints (own frame, its bind; the measure's and the masses'): a rig joint,
    `hipmid` the hip joints' middle, `<Side>Hand tip` the mean of the TIP_SHARE of the hand's own vertices (skin weight
    over a half) furthest from its joint. `rig`: {"names", "bind" (joints x 4 x 4), "points", "weights"}."""
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
    """A MyoFullBody joint centre as weighted body points ([(body, local point (source model), weight)])."""
    if name in MIDDLE_CENTRES:
        return [(*CENTRES[part], 0.5) for part in MIDDLE_CENTRES[name]]
    return [(*CENTRES[name], 1.0)]


def refined(name, moves, leftovers):
    """A landmark's link and trust from its fits on many bodies (Cotton et al. 2026 weigh each marker by how small
    and consistent its leftovers are over many subjects; the idea taken, the rule ours): `moves` each body's fitted
    move off the link (bodies x 3, the body's frame, metres) and `leftovers` each body's target less its marker every
    frame (a list of frames x 3, the body's frame). Each body's offset is its move plus its mean leftover; the link
    moves by the bodies' mean offset (a HELD landmark's stays); the trust is s0^2 / (s0^2 + within^2 + between^2),
    s0 TRUST_SPREAD, within the leftovers' RMS about each body's mean, between the bodies' offsets' spread about
    theirs. Returns (link [3], trust)."""
    offsets = np.array([move + np.mean(left, axis=0) for move, left in zip(moves, leftovers)])
    within = np.sqrt(np.mean(np.concatenate([np.sum((left - np.mean(left, axis=0)) ** 2, axis=1)
                                             for left in leftovers])))
    between = np.sqrt(np.mean(np.sum((offsets - offsets.mean(axis=0)) ** 2, axis=1)))
    link = np.asarray(LANDMARKS[name][5], dtype=float) + (0.0 if name in HELD else offsets.mean(axis=0))
    return link, float(TRUST_SPREAD ** 2 / (TRUST_SPREAD ** 2 + within ** 2 + between ** 2))
