"""Checks `stance.py` on a pair of legs made here: wide feet are brought in to WIDEST, the legs keep their lengths, the
feet keep their turn and stay planted, and a stance already narrow is left alone. Numpy only; runs as a script or
under pytest."""
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import stance  # noqa: E402

NAMES = ["Hips", "LeftLeg", "LeftShin", "LeftFoot", "LeftToeBase", "RightLeg", "RightShin", "RightFoot",
         "RightToeBase"]
PARENTS = np.array([-1, 0, 1, 2, 3, 0, 5, 6, 7])


def legs(feet_out, frames=5, sway=0.0):
    """World transforms of standing legs, hips 0.2 m apart, each ankle `feet_out` out from its hip, the hips swaying
    `sway` metres sideways frame by frame while the feet stay put."""
    world = np.repeat(np.eye(4)[None, None], frames, axis=0).repeat(len(NAMES), axis=1)
    for frame in range(frames):
        drift = sway * frame
        places = {"Hips": [drift, 1.0, 0.0]}
        for side, sign in (("Left", 1.0), ("Right", -1.0)):
            hip = np.array([drift + sign * 0.1, 0.95, 0.0])
            ankle = np.array([sign * (0.1 + feet_out), 0.08, 0.0])
            places[side + "Leg"] = hip
            places[side + "Shin"] = (hip + ankle) / 2 + np.array([0.0, 0.0, 0.03])
            places[side + "Foot"] = ankle
            places[side + "ToeBase"] = ankle + np.array([0.0, -0.05, 0.12])
        for name, place in places.items():
            world[frame, NAMES.index(name), :3, 3] = place
    return world


def spacing(world):
    return world[:, NAMES.index("LeftFoot"), 0, 3] - world[:, NAMES.index("RightFoot"), 0, 3]


def bone(world, first, second):
    return np.linalg.norm(world[:, NAMES.index(first), :3, 3] - world[:, NAMES.index(second), :3, 3], axis=1)


def test_wide_feet_are_brought_in_to_hip_width():
    moved = stance.narrowed(legs(0.11), NAMES, PARENTS)
    assert np.allclose(spacing(moved), stance.WIDEST * 0.2, atol=1e-9)


def test_the_legs_keep_their_lengths_and_the_feet_their_turn():
    before = legs(0.11)
    after = stance.narrowed(before, NAMES, PARENTS)
    for first, second in (("LeftLeg", "LeftShin"), ("LeftShin", "LeftFoot"), ("RightLeg", "RightShin")):
        assert np.allclose(bone(after, first, second), bone(before, first, second))
    assert np.allclose(after[:, NAMES.index("LeftFoot"), :3, :3], before[:, NAMES.index("LeftFoot"), :3, :3])
    assert np.allclose(after[:, NAMES.index("LeftFoot"), 1, 3], before[:, NAMES.index("LeftFoot"), 1, 3])


def test_a_planted_foot_stays_planted_while_the_hips_sway():
    after = stance.narrowed(legs(0.11, sway=0.004), NAMES, PARENTS)
    ankle = after[:, NAMES.index("LeftFoot"), :3, 3]
    assert np.allclose(ankle, ankle[0])


def test_a_narrow_stance_is_left_alone():
    before = legs(0.0)
    assert stance.narrowed(before, NAMES, PARENTS) is before


if __name__ == "__main__":
    for name, check in list(globals().items()):
        if name.startswith("test_"):
            check()
            print("ok", name)
