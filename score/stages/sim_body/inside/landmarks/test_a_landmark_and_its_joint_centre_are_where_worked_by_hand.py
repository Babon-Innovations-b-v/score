"""landmarks: a landmark is its face's barycentric point on a person's mesh, the joint centres it gives are the ISB
midpoints and Harrington's hips, a stretch's end on SOMA is its joint, the hip joints' middle or the hand's tip, and
each left landmark's MyoFullBody point is its right one's mirrored (all worked out by hand; pure: the score venv
runs it).

Breaks (each applied once, seen red, reverted), 2026-10-28:
- on_skin's `np.asarray(row[1]) @ points[faces[row[0]]]` made `points[faces[row[0]]].mean(axis=0)`: every landmark
  at its face's middle.
- harrington's `-0.30 * width - 0.0109` made `-0.30 * width`: the hips 10.9 mm high.
- harrington's `(("l", -1.0), ("r", 1.0))` made `(("l", 1.0), ("r", -1.0))`: the hips swap sides.
- soma_point's `1.0 - TIP_SHARE` made `0.5`: the hand's tip is its far half's middle.
- _table's ASIS_r bone point x `0` made `0.01`: the right ASIS is 1 cm off the left's mirror.

Run: .venv/bin/python score/stages/sim_body/inside/landmarks/test_a_landmark_and_its_joint_centre_are_where_worked_by_hand.py
"""
import pathlib
import sys

import numpy as np

INSIDE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(INSIDE))
import landmarks  # noqa: E402


def a_landmark_is_its_faces_barycentric_point():
    """A mesh whose every face is the triangle (0, 0, 0), (1, 0, 0), (0, 1, 0): ASIS_l (weights 0.1252, 0.15773,
    0.71708) stands at (0.15773, 0.71708, 0)."""
    points = np.array([[0.0, 0, 0], [1, 0, 0], [0, 1, 0]])
    faces = np.zeros((10000, 3), dtype=int) + [0, 1, 2]
    found = landmarks.on_skin(points, faces)["ASIS_l"]
    return [] if np.allclose(found, [0.15773, 0.71708, 0.0]) else [f"ASIS_l at {found}"]


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
    marks = {name: np.zeros(3) for name in landmarks.MARKS}
    marks["lateral_epicondyle_l"], marks["medial_epicondyle_l"] = np.array([0.15, 0.5, 0]), np.array([0.05, 0.5, 0.02])
    marks.update(ASIS_l=np.array([0.1, 1, 0]), ASIS_r=np.array([-0.1, 1, 0]), PSIS_l=np.array([0.1, 1, -0.1]),
                 PSIS_r=np.array([-0.1, 1, -0.1]))
    found = landmarks.soma_centres(marks)["knee_l"]
    return [] if np.allclose(found, [0.1, 0.5, 0.01]) else [f"knee_l at {found}"]


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
    """Every `_l` landmark and centre has its `_r` one on the other side's body (or the same middle body), its bone point mirrored across the
    body's z (MyoFullBody's sides mirror in z) within 2 mm; hipmid is half of each hip."""
    problems = []
    for table, point in ((landmarks.MARKS, 4), (landmarks.CENTRES, 1)):
        for name, row in table.items():
            if not name.endswith("_l"):
                continue
            other = table.get(name[:-2] + "_r")
            body = row[3] if table is landmarks.MARKS else row[0]
            twin = body[:-2] + "_r" if body.endswith("_l") else body
            if other is None or (other[3] if table is landmarks.MARKS else other[0]) != twin:
                problems.append(f"{name} has no right twin")
            elif np.abs(np.asarray(row[point]) * [1, 1, -1] - other[point]).max() > 0.002:
                problems.append(f"{name} {row[point]} against {other[point]}")
    weights = [part[2] for part in landmarks.myo_parts("hipmid")]
    return problems + ([] if weights == [0.5, 0.5] else [f"hipmid weights {weights}"])


CHECKS = (a_landmark_is_its_faces_barycentric_point, the_hips_are_harringtons, a_joint_centre_is_its_landmarks_middle,
          a_stretch_end_is_a_joint_the_hips_middle_or_the_hands_tip, each_left_point_is_its_right_ones_mirror)


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[5] / "conftest.py"))["refuse_outside_sandbox"]()
    failures = [f"{check.__name__}: {problem}" for check in CHECKS for problem in check()]
    for failure in failures:
        print(failure)
    print("ok" if not failures else f"{len(failures)} failed")
    sys.exit(1 if failures else 0)
