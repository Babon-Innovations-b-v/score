"""The finish's stand (stand.stood_turn) keeps the picture's up for a shape its tightest box would tip, and stands
every other shape as glb_file.upright_turn does.

Every case is points whose answer is plain: a crate tilted 35 degrees fills its box and stands back up; a thin
desk lamp (a foot, a post and an arm reaching out and down) whose tightest box leans 45 degrees keeps its up, only
squared;
an asked stand (`long`) is never second-guessed.

Breaks that turn the test red (each applied once and seen red, 2026-11-08):
- `return tilt > NEAR_UP_DEGREES and fill < BOX_FILL` made `return False` in `kept_up` (the lamp is tipped by its box).
- `fill < BOX_FILL` made `fill < 2.0` in `kept_up` (the crate, too, keeps its tilt).
- `if not (long or feet or tube or flat) and kept_up(points):` made `if kept_up(points):` in `stood_turn` (an asked
  long stand is overridden).
"""
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import glb_file  # noqa: E402
import stand  # noqa: E402


def tilted(points, degrees, axis=(1.0, 0.0, 0.0)):
    """The points turned `degrees` about `axis` through the origin."""
    axis = np.asarray(axis, dtype=float) / np.linalg.norm(axis)
    angle = np.radians(degrees)
    skew = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    turn = np.eye(3) + np.sin(angle) * skew + (1 - np.cos(angle)) * skew @ skew
    return points @ turn.T


def about_z(degrees):
    """The turn of `degrees` about Z."""
    angle = np.radians(degrees)
    return np.array([[np.cos(angle), -np.sin(angle), 0.0], [np.sin(angle), np.cos(angle), 0.0], [0.0, 0.0, 1.0]])


def block(low, high, count=6):
    """A filled box of points between corners `low` and `high`."""
    axes = [np.linspace(low[index], high[index], count) for index in range(3)]
    return np.stack(np.meshgrid(*axes), -1).reshape(-1, 3)


def test_a_shape_its_box_would_tip_keeps_its_up_and_a_full_box_stands():
    crate = tilted(block((-0.5, -0.3, -0.4), (0.5, 0.3, 0.4)), 35)
    turn = stand.stood_turn(crate, long=False, feet=False, tube=False, flat=False)
    assert abs(np.ptp(crate @ turn.T, axis=0)[1] - 0.6) < 0.03  # it fills its box: stood back up
    assert np.allclose(turn, glb_file.upright_turn(crate))

    post = block((-0.02, 0.0, -0.02), (0.02, 1.0, 0.02))
    foot = block((-0.2, 0.0, -0.2), (0.2, 0.04, 0.2))
    reach = block((0.0, -0.02, -0.02), (1.0, 0.02, 0.02)) @ about_z(-45).T + np.array([0.0, 1.0, 0.0])
    lamp = np.vstack([foot, post, reach])  # a desk lamp: foot, post, an arm reaching out and down
    assert not np.allclose(glb_file.upright_turn(lamp)[1], [0.0, 1.0, 0.0], atol=0.1)  # its box tips it
    assert stand.kept_up(lamp), "the lamp fills little of its box and its box side leans: keep its up"
    turn = stand.stood_turn(lamp, long=False, feet=False, tube=False, flat=False)
    assert np.allclose(turn, glb_file.squared(lamp)) and np.allclose(turn[1], [0.0, 1.0, 0.0])  # turned about up only

    asked = stand.stood_turn(lamp, long=True, feet=False, tube=False, flat=False)
    assert np.allclose(asked, glb_file.upright_turn(lamp, long=True))
