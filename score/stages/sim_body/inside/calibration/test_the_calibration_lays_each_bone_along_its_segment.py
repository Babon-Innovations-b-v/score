"""calibration: `aligned` lays a MyoFullBody bone along its SOMA segment's (worked by hand), and the stored table keeps
the two models' symmetry: a middle group turns no body sideways, a right group is its left one with the body's half
turn about its z (MyoFullBody's right bodies are its left ones mirrored in z; measured on the table within 0.03
degrees, 2026-10-28). Pure: the score venv runs it.

Breaks (each applied once, seen red, reverted), 2026-10-28:
- aligned's `soma_turn.T @ frame(...)` made `frame(...)` (the segment's own turn dropped).
- frame's `np.cross(across, along)` made `np.cross(along, across)`: a left-handed frame.
- TABLE's RightLeg `(0.707106, 0.707106, ...)` made `(-0.707106, 0.707106, ...)` (the left's).
- TABLE's Spine2 `0.00165502` made `0.1`: the lumbar turned sideways.

Run: .venv/bin/python score/stages/sim_body/inside/calibration/test_the_calibration_lays_each_bone_along_its_segment.py
"""
import pathlib
import sys

import numpy as np

INSIDE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(INSIDE))
import calibration  # noqa: E402

TURN_Z = np.array([[0.0, -1.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]])  # 90 degrees about z


def a_hanging_bone_is_laid_along_its_segment():
    """A SOMA segment unturned, its bone along x, its reference z, and a body unturned, its bone hanging along -y,
    reference z: R_cal is 90 degrees about z ([[0, -1, 0], [1, 0, 0], [0, 0, 1]]), which lays the body's -y on the
    segment's x. The same bone hanging (along -y) in a segment turned -90 degrees about z, whose own x hangs: R_cal is
    the same, read in the segment's own frame. A bone along x with reference z has the axes x, y, z (right-handed)."""
    problems = [] if np.allclose(calibration.frame([2, 0, 0], [0.3, 0, 1]), np.eye(3)) else ["frame is not x, y, z"]
    found = calibration.aligned((np.eye(3), [1, 0, 0], [0, 0, 1]), (np.eye(3), [0, -1, 0], [0, 0, 1]))
    if not np.allclose(found, TURN_Z):
        problems.append(f"unturned: {np.round(found, 3).tolist()}")
    found = calibration.aligned((TURN_Z.T, [0, -1, 0], [0, 0, 1]), (np.eye(3), [0, -1, 0], [0, 0, 1]))
    if not np.allclose(found, TURN_Z):
        problems.append(f"turned: {np.round(found, 3).tolist()}")
    return problems


def the_table_keeps_both_sides_and_the_middle():
    """Every stored turn is a rotation; each Right group's is its Left one's times diag(-1, -1, 1) within 0.1
    degrees; each middle group (Hips to Head) keeps the sideways axis (|R[2, 2]| over cos 0.5 degrees)."""
    problems = []
    for group in calibration.TABLE:
        turn = calibration.turn(group)
        if group.startswith("Right"):
            mirrored = calibration.turn("Left" + group[len("Right"):]) @ np.diag([-1.0, -1.0, 1.0])
            angle = np.degrees(np.arccos(np.clip((np.trace(mirrored.T @ turn) - 1) / 2, -1, 1)))
            if angle > 0.1:
                problems.append(f"{group} is {angle:.2f} degrees off its left one mirrored")
        elif not group.startswith("Left") and abs(turn[2, 2]) < np.cos(np.radians(0.5)):
            problems.append(f"{group} turns its body sideways: R[2, 2] {turn[2, 2]:.4f}")
    return problems


CHECKS = (a_hanging_bone_is_laid_along_its_segment, the_table_keeps_both_sides_and_the_middle)


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[5] / "conftest.py"))["refuse_outside_sandbox"]()
    failures = [f"{check.__name__}: {problem}" for check in CHECKS for problem in check()]
    for failure in failures:
        print(failure)
    print("ok" if not failures else f"{len(failures)} failed")
    sys.exit(1 if failures else 0)
