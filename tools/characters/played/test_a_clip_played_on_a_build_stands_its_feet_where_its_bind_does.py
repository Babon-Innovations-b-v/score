"""played: a clip played on a build (a toy chain Root, Hips, LeftLeg, LeftFoot, RightFoot) keeps its rotations and its
travel, takes the build's bones whatever offsets the clip itself carries, and every clip is lifted so the standing
clip's first frame puts the feet where the build's bind does; the arithmetic is the people build's own (its copy in
`../maker/prop_build.py` gives the same worlds and lift, bit for bit).

Breaks (each applied once, seen red, reverted), 2026-10-29:
- laid's `moved[:, joint, :3, 3] = offsets[joint]` dropped: the clip's own 5 cm short leg is played, the foot 5 cm high.
- floor_lift's `bind[feet, 1, 3].min() - world[...]` made `0.0`: the standing foot stands where the short clip put it.
- clip_local's `*= scale` dropped: a build 1.1 times the rig travels as far as the rig.
- chained's `world[:, parents[joint]] @ local[:, joint]` made `local[:, joint] @ world[:, parents[joint]]`: a turned
  hip carries its leg the wrong way.
"""
import pathlib

import numpy as np
import pytest

from tools.characters import played

NAMES = ["Root", "Hips", "LeftLeg", "LeftFoot", "RightFoot"]
PARENTS = np.array([-1, 0, 1, 2, 1])
BIND_OFFSETS = np.array([[0.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.1, 0.0, 0.0], [0.0, -0.9, 0.0], [-0.1, -0.9, 0.0]])


def placed(offsets, turn_hips=0.0, frames=2, hips=1.0):
    """Frames x joints x 4 x 4 transforms against the parents at `offsets`, the Hips `hips` high, turned `turn_hips`
    about z and walking 0.1 m a frame along x."""
    local = np.tile(np.eye(4), (frames, len(NAMES), 1, 1))
    local[:, :, :3, 3] = offsets
    local[:, 1, 1, 3] = hips
    local[:, 1, 0, 3] = 0.1 * np.arange(frames)
    cos, sin = np.cos(turn_hips), np.sin(turn_hips)
    local[:, 1, :2, :2] = [[cos, -sin], [sin, cos]]
    return local


def toy():
    """The rig: its bind at BIND_OFFSETS; its clips posed on a body whose legs are 5 cm short, as people-clips-made's
    are (#70), with the Hips 3 cm under the bind's, the standing clip upright, the walking one turned 90 degrees at
    the hips."""
    short = BIND_OFFSETS.copy()
    short[3:, 1] += 0.05
    bind = played.chained(placed(BIND_OFFSETS, frames=1), PARENTS)[0]
    return {"bind": bind, "clip_standing": placed(short, hips=0.97), "clip_walking": placed(short, np.pi / 2, hips=0.97)}


def test_the_standing_feet_stand_where_the_bind_puts_them():
    rig = toy()
    bones = {"offsets": BIND_OFFSETS, "parents": PARENTS, "bind": rig["bind"]}
    lift = played.floor_lift(rig, bones, NAMES, 1.0)
    world = played.clip_world(rig, "standing", BIND_OFFSETS, PARENTS, 1.0, lift)
    assert world[0, [3, 4], 1, 3] == pytest.approx(rig["bind"][[3, 4], 1, 3])
    assert lift == pytest.approx(0.03)


def test_a_turned_hip_carries_its_leg_on_the_build_bones():
    rig = toy()
    world = played.clip_world(rig, "walking", BIND_OFFSETS, PARENTS, 1.0, 0.0)
    assert world[1, 2, :3, 3] == pytest.approx([0.1, 1.07, 0.0])  # the left leg 0.1 m along the turned hip's x: up
    assert world[1, 3, :3, 3] == pytest.approx([1.0, 1.07, 0.0])  # its foot 0.9 m down the hip's y: along +x


def test_a_bigger_build_travels_further():
    rig = toy()
    world = played.clip_world(rig, "standing", BIND_OFFSETS, PARENTS, 1.1, 0.0)
    assert world[1, 1, 0, 3] == pytest.approx(0.11)


def test_the_people_build_plays_the_same():
    """prop_build.py's own fk, clip_world and floor_lift, loaded by path without its heavy imports' module top run:
    its three functions' sources executed here against numpy give the same worlds and lift."""
    source = (pathlib.Path(__file__).resolve().parents[1] / "maker/prop_build.py").read_text()
    names = {"np": np, "TRAVELLING_JOINT": 1, "FEET": played.FEET}
    for function in ("def fk(", "def clip_world(", "def floor_lift("):
        start = source.index(function)
        exec(source[start:source.index("\n\n\n", start)], names)  # noqa: S102 - the repository's own file
    rig = toy()
    bones = {"offsets": BIND_OFFSETS, "parents": PARENTS, "bind": rig["bind"]}
    assert names["floor_lift"](rig, bones, NAMES, 1.1) == played.floor_lift(rig, bones, NAMES, 1.1)
    assert np.array_equal(names["clip_world"](rig, "walking", BIND_OFFSETS, PARENTS, 1.1, 0.02),
                          played.clip_world(rig, "walking", BIND_OFFSETS, PARENTS, 1.1, 0.02))
