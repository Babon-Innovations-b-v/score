"""landmarks: every landmark of SCORE's set resolves on both models (a face of SOMA's template topology with
barycentric weights, on a SOMA segment; a MyoFullBody body of that segment's bone group), every joint-centre rule reads
solver landmarks, each left landmark is its right one mirrored; a landmark is its face's barycentric point on a
person's mesh, and on the clip's skin its corners' skinned moves' (each corner its joints' weighted moves from the
bind); the joint centres it gives are the ISB midpoints, Harrington's hips and Rab's shoulders; a SOMA joint end is
its joint, the hip joints' middle or the hand's tip; and the refinement moves a link by the bodies' mean offset and
trusts it by its leftovers' spread (all worked out by hand; pure: the score venv runs it).

Breaks (each applied once, seen red, reverted):
- (2026-10-28) on_skin's `np.asarray(row[1]) @ points[faces[row[0]]]` made `points[faces[row[0]]].mean(axis=0)`:
  every landmark at its face's middle.
- (2026-10-28) harrington's `-0.30 * width - 0.0109` made `-0.30 * width`: the hips 10.9 mm high.
- (2026-10-28) harrington's `(("l", -1.0), ("r", 1.0))` made `(("l", 1.0), ("r", -1.0))`: the hips swap sides.
- (2026-10-28) soma_point's `1.0 - TIP_SHARE` made `0.5`: the hand's tip is its far half's middle.
- (2026-10-28) posed's `np.asarray(worlds, dtype=float) @ np.linalg.inv(bind)` made `np.asarray(worlds,
  dtype=float)`: a joint's move is its frame, not its move from the bind.
- (2026-10-28) posed's `np.einsum("lcs,flcsi->flci", weights, moved)` made `moved[..., 0, :]`: every corner moves
  with its first segment only.
- (2026-10-29) _table's ASIS_r bone point x `0` made `0.01`: the right ASIS is 1 cm off the left's mirror.
- (2026-10-29) _table's spinous_L4 body `lumbar4` made `lumbar3`: it no longer resolves in its segment's group.
- (2026-10-29) _table's MT1_head_l face `3570` made `9100`: past the template's faces.
- (2026-10-29) _table's MC3_head_r trust `0.098` made `0.099` (the study's own side): its trust is not the left's.
- (2026-10-29) rab's `- RAB_DROP * width * up` made `- RAB_DROP * width * np.array([0, 1.0, 0])`: the shoulder drops
  along own up, not the thorax's.
- (2026-10-29) point's middle `/ 2` made `/ 3`: the knee a third of the way.
- (2026-10-29) refined's `0.0 if name in HELD else` dropped: a held pad's link moves.
- (2026-10-29) refined's `- np.mean(left, axis=0)` (within) dropped: a body's steady offset counts as spread.

Run: .venv/bin/python score/stages/sim_body/inside/landmarks/test_every_landmark_resolves_on_both_models_where_worked_by_hand.py
"""
import pathlib
import sys

import numpy as np

INSIDE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(INSIDE))
import landmarks  # noqa: E402
from bone_groups import groups  # noqa: E402

TEMPLATE_FACES = 9006  # SOMA's template mesh (4505 vertices), whose topology every person's mesh shares


def a_landmark_is_its_faces_barycentric_point():
    """A mesh whose every face is the triangle (0, 0, 0), (1, 0, 0), (0, 1, 0): ASIS_l (weights 0.1252, 0.15773,
    0.71708) stands at (0.15773, 0.71708, 0)."""
    points = np.array([[0.0, 0, 0], [1, 0, 0], [0, 1, 0]])
    faces = np.zeros((10000, 3), dtype=int) + [0, 1, 2]
    found = landmarks.on_skin(points, faces)["ASIS_l"]
    return [] if np.allclose(found, [0.15773, 0.71708, 0.0]) else [f"ASIS_l at {found}"]


def a_skinned_landmark_is_its_corners_blended_moves():
    """Every face the triangle (0, 0, 0), (1, 0, 0), (0, 1, 0); corner 0 all Hips', corner 1 half Hips' half
    LeftLeg's, corner 2 all LeftLeg's (Root weighs nothing); LeftLeg's bind stands at (0, 1, 0). In a frame where Hips
    moves 1 along x and LeftLeg turns 90 degrees about z at its bind place, corner 0 is at (1, 0, 0), corner 1 at
    ((2, 0, 0) + (1, 2, 0)) / 2 and corner 2 stays: ASIS_l (weights 0.1252, 0.15773, 0.71708) at (0.361795, 0.87481,
    0)."""
    corners = np.array([[0.0, 0, 0], [1, 0, 0], [0, 1, 0]])
    bind = np.tile(np.eye(4), (3, 1, 1))
    bind[2, 1, 3] = 1.0
    rig = {"names": ["Root", "Hips", "LeftLeg"], "bind": bind, "points": corners,
           "faces": np.zeros((10000, 3), dtype=int) + [0, 1, 2],
           "weights": np.array([[0.0, 1.0, 0.0], [0.0, 0.5, 0.5], [0.0, 0.0, 1.0]])}
    hips, leg = np.eye(4), np.eye(4)
    hips[0, 3] = 1.0
    leg[:3, :3] = [[0.0, -1.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]]
    leg[1, 3] = 1.0
    found = landmarks.posed(rig, ["Hips", "LeftLeg"], np.array([[hips, leg]]))
    first = landmarks.solver_marks().index("ASIS_l")
    wanted = [0.361795, 0.87481, 0.0]
    return [] if np.allclose(found[0, first], wanted, atol=1e-6) else [f"ASIS_l skinned at {found[0, first]}"]


def the_hips_are_harringtons():
    """ASIS at (+-0.1, 1, 0.05), PSIS at (+-0.05, 1, -0.1) (+x left): width 0.2, depth 0.15; the left hip 0.0459 m
    back, 0.0709 down and 0.0733 left of the ASIS' middle: (0.0733, 0.9291, 0.0041), the right one mirrored."""
    marks = {"ASIS_l": np.array([0.1, 1, 0.05]), "ASIS_r": np.array([-0.1, 1, 0.05]),
             "PSIS_l": np.array([0.05, 1, -0.1]), "PSIS_r": np.array([-0.05, 1, -0.1])}
    found = landmarks.harrington(marks)
    wanted = {"hip_l": [0.0733, 0.9291, 0.0041], "hip_r": [-0.0733, 0.9291, 0.0041]}
    return [f"{hip} at {found[hip]}" for hip, place in wanted.items() if not np.allclose(found[hip], place, atol=1e-6)]


def a_joint_centre_is_its_landmarks_middle():
    """The left knee between its epicondyles at (0.15, 0.5, 0) and (0.05, 0.5, 0.02): (0.1, 0.5, 0.01)."""
    marks = {"femur_lateral_epicondyle_l": np.array([0.15, 0.5, 0]),
             "femur_medial_epicondyle_l": np.array([0.05, 0.5, 0.02])}
    found = landmarks.point("knee_l", marks)
    return [] if np.allclose(found, [0.1, 0.5, 0.01]) else [f"knee_l at {found}"]


def the_shoulders_are_rabs_along_the_thorax():
    """Acromions at (+-0.2, 1.4, 0), the jugular notch at (0, 1.4, 0.05), C7 at (0, 1.45, -0.1), the xiphoid at
    (0, 1.2, 0.1), T8 at (0, 1.2, -0.1): the thorax's vertical (0, 0.225, -0.025) / 0.226385, the drop 0.17 x 0.4 =
    0.068: the left glenohumeral centre at (0.2, 1.332416, 0.007509)."""
    marks = {"acromion_l": np.array([0.2, 1.4, 0]), "acromion_r": np.array([-0.2, 1.4, 0]),
             "jugular_notch": np.array([0, 1.4, 0.05]), "spinous_C7": np.array([0, 1.45, -0.1]),
             "xiphoid": np.array([0, 1.2, 0.1]), "spinous_T8": np.array([0, 1.2, -0.1])}
    found = landmarks.point("glenohumeral_l", marks)
    return [] if np.allclose(found, [0.2, 1.332416, 0.007509], atol=1e-6) else [f"glenohumeral_l at {found}"]


def every_landmark_resolves_on_both_models():
    """Each landmark's face is one of the template's, its weights none negative and summing to 1, its segment a bone
    group's and its MyoFullBody body one of that group's bodies; every rule reads landmarks the solver takes, every
    one trusted above 0."""
    table, problems = groups(), []
    for name, (face, weights, segment, body, _, _, trust, solver) in landmarks.LANDMARKS.items():
        if not 0 <= face < TEMPLATE_FACES or min(weights) < 0 or abs(sum(weights) - 1) > 1e-3:
            problems.append(f"{name}: face {face}, weights {weights}")
        if segment not in table or body not in table[segment][3]:
            problems.append(f"{name}: {body} is not in {segment}'s bone group")
        if solver and not 0 < trust <= 1:
            problems.append(f"{name}: trust {trust}")
    solver = set(landmarks.solver_marks())
    for name in landmarks.RULES:
        if not landmarks.needed(name) <= solver:
            problems.append(f"rule {name} reads {sorted(landmarks.needed(name) - solver)}")
    return problems


def a_stretch_end_is_a_joint_the_hips_middle_or_the_hands_tip():
    """A rig with LeftLeg at (0.1, 1, 0), RightLeg at (-0.1, 1, 0.02) and LeftHand at 0, its 100 own points along x
    at 0.01 to 1.00 m: hipmid (0, 1, 0.01); the hand's tip the 2% furthest, 0.99 and 1.00: (0.995, 0, 0)."""
    bind = np.tile(np.eye(4), (3, 1, 1))
    bind[0, :3, 3], bind[1, :3, 3] = [0.1, 1, 0], [-0.1, 1, 0.02]
    points = np.column_stack([np.arange(1, 101) / 100.0, np.zeros(100), np.zeros(100)])
    weights = np.zeros((100, 3))
    weights[:, 2] = 1.0
    rig = {"names": ["LeftLeg", "RightLeg", "LeftHand"], "bind": bind, "points": points, "weights": weights}
    problems = [] if np.allclose(landmarks.soma_point("hipmid", rig), [0, 1, 0.01]) else ["hipmid"]
    tip = landmarks.soma_point("LeftHand tip", rig)
    return problems + ([] if np.allclose(tip, [0.995, 0, 0]) else [f"the hand's tip at {tip}"])


def each_left_point_is_its_right_ones_mirror():
    """Every `_l` landmark and centre has its `_r` one on the other side's body (or the same middle body), its bone
    point and link mirrored across the body's z (MyoFullBody's sides mirror in z) within 2 mm, its trust and solver
    the same; hipmid is half of each hip."""
    problems = []
    for table, points, body_at in ((landmarks.LANDMARKS, (4, 5), 3), (landmarks.CENTRES, (1,), 0)):
        for name, row in table.items():
            if not name.endswith("_l"):
                continue
            other = table.get(name[:-2] + "_r")
            twin = row[body_at][:-2] + "_r" if row[body_at].endswith("_l") else row[body_at]
            if other is None or other[body_at] != twin:
                problems.append(f"{name} has no right twin")
                continue
            for at in points:
                if np.abs(np.asarray(row[at]) * [1, 1, -1] - other[at]).max() > 0.002:
                    problems.append(f"{name} {row[at]} against {other[at]}")
            if table is landmarks.LANDMARKS and row[6:] != other[6:]:
                problems.append(f"{name} trust {row[6:]} against {other[6:]}")
    weights = [part[2] for part in landmarks.myo_parts("hipmid")]
    return problems + ([] if weights == [0.5, 0.5] else [f"hipmid weights {weights}"])


def a_link_moves_by_the_bodies_mean_offset_and_trusts_its_spread():
    """ASIS_l fitted on two bodies: moves (1, 0, 0) and (3, 0, 0) mm, leftovers (0, +-1, 0) mm and twice (2, 0, 0) mm:
    offsets (1, 0, 0) and (5, 0, 0) mm, the link 3 mm on in x; within^2 0.5 mm^2, between^2 4 mm^2: trust 25 / 29.5.
    A held pad (heel_plantar_l) keeps its link."""
    moves = np.array([[0.001, 0, 0], [0.003, 0, 0]])
    leftovers = [np.array([[0, 0.001, 0], [0, -0.001, 0]]), np.array([[0.002, 0, 0], [0.002, 0, 0]])]
    link, trust = landmarks.refined("ASIS_l", moves, leftovers)
    wanted = np.asarray(landmarks.LANDMARKS["ASIS_l"][5]) + [0.003, 0, 0]
    problems = [] if np.allclose(link, wanted) else [f"ASIS_l link {link}, not {wanted}"]
    if abs(trust - 25 / 29.5) > 1e-6:
        problems.append(f"trust {trust}, not {25 / 29.5:.6f}")
    held, _ = landmarks.refined("heel_plantar_l", moves, leftovers)
    if not np.allclose(held, landmarks.LANDMARKS["heel_plantar_l"][5]):
        problems.append(f"heel_plantar_l's link moved to {held}")
    return problems


CHECKS = (every_landmark_resolves_on_both_models, a_landmark_is_its_faces_barycentric_point,
          a_skinned_landmark_is_its_corners_blended_moves, the_hips_are_harringtons, a_joint_centre_is_its_landmarks_middle,
          the_shoulders_are_rabs_along_the_thorax, a_stretch_end_is_a_joint_the_hips_middle_or_the_hands_tip,
          each_left_point_is_its_right_ones_mirror, a_link_moves_by_the_bodies_mean_offset_and_trusts_its_spread)


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[5] / "conftest.py"))["refuse_outside_sandbox"]()
    failures = [f"{check.__name__}: {problem}" for check in CHECKS for problem in check()]
    for failure in failures:
        print(failure)
    print("ok" if not failures else f"{len(failures)} failed")
    sys.exit(1 if failures else 0)
