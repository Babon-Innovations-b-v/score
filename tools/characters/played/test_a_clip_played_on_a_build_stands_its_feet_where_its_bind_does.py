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
Kimodo's own foot correction (`contacted`, #70, 2026-11-06): its skeleton is Kimodo's somaskel30 joint by joint (read
from vendor/kimodo's definitions.py), a SCORE rig maps onto it with its Root and end sites left out, a leg hung from
the wrong joint is refused, and a clip carried to Kimodo's motion and back is itself (MotionCorrection, whose prebuilt wheel `uv
sync` installs into the score venv, is not run here: the correction's numbers are on #70). Breaks, each applied once and seen red, reverted:
- kimodo_joints' parent check dropped: a RightFoot hung from the LeftShin passes.
- to_kimodo's `np.swapaxes(turns[:, parent], 1, 2) @` dropped: the clip comes back turned.
- to_kimodo's rest `bind[parents[own], :3, :3] @` dropped: the rest's ankle is not where the bind's is.
- foot_contacts' `CONTACT_CHANNELS[6]` made `(0, 1, 2, 3)`: the left toe end read as the right heel.
- contacted's `except ModuleNotFoundError` refusal dropped: a box without motion_correction says only its import.
A toe bent toward flat (`toward_flat`, #70, 2026-11-06) lies as the bind's toe does turned only as the clip turns it
about the upright, its base unmoved; a share of the way bends it that share. Breaks, each applied once, seen red,
reverted: its flat made the bind's turn alone (the clip's 40 degree turn about the upright lost); its share made 1
(half bends it all the way); its parent check dropped (a toe end hung from the foot passes).
"""
import ast
import pathlib
import sys

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


def turned(rng, count):
    """`count` random turns (count x 3 x 3)."""
    found, _ = np.linalg.qr(rng.normal(size=(count, 3, 3)))
    return found * np.sign(np.linalg.det(found))[:, None, None]


def tipped(degrees):
    """A turn of `degrees` about x: a foot along +z pitched down onto its toes."""
    angle = np.radians(degrees)
    return np.array([[1.0, 0.0, 0.0], [0.0, np.cos(angle), -np.sin(angle)], [0.0, np.sin(angle), np.cos(angle)]])


def kimodo_shaped():
    """A SCORE-shaped rig of Kimodo's joints (its Root, HeadEnd and toe ends besides, its jaw, eyes and hand ends
    not): names, parents, a bind of random turns, and a 4-frame clip of random turns on its offsets."""
    rng = np.random.default_rng(3)
    joints = [("Root", None)] + [(name, parent or "Root") for name, parent in played.KIMODO_SKELETON
                                 if name not in played.KIMODO_ONLY]
    joints += [("HeadEnd", "Head"), ("LeftToeEnd", "LeftToeBase"), ("RightToeEnd", "RightToeBase")]
    names = [name for name, _ in joints]
    parents = np.array([-1 if parent is None else names.index(parent) for _, parent in joints])
    bind = np.tile(np.eye(4), (len(names), 1, 1))
    bind[:, :3, :3] = turned(rng, len(names))
    bind[:, :3, 3] = rng.normal(size=(len(names), 3))
    local = np.tile(np.eye(4), (4, len(names), 1, 1))
    local[..., :3, :3] = turned(rng, 4 * len(names)).reshape(4, len(names), 3, 3)
    local[..., :3, 3] = rng.normal(size=(len(names), 3))
    return names, parents, bind, local


def test_the_standing_feet_stand_where_the_bind_puts_them(monkeypatch):
    rig = toy()
    bones = {"offsets": BIND_OFFSETS, "parents": PARENTS, "bind": rig["bind"]}
    lift = played.floor_lift(rig, bones, NAMES, 1.0)
    world = played.clip_world(rig, "standing", BIND_OFFSETS, PARENTS, 1.0, lift)
    assert world[0, [3, 4], 1, 3] == pytest.approx(rig["bind"][[3, 4], 1, 3])
    assert lift == pytest.approx(0.03)
    # Kimodo's own correction runs on the build's bones: its skeleton is Kimodo's own, a rig maps onto it joint by
    # joint, and a clip carried to Kimodo's motion and back is itself, the rest's feet where the bind puts them
    source = (pathlib.Path(__file__).resolve().parents[3] / "vendor/kimodo/kimodo/skeleton/definitions.py").read_text()
    tree = next(node for node in ast.walk(ast.parse(source)) if isinstance(node, ast.ClassDef)
                and node.name == "SOMASkeleton30")
    kimodo = next(node.value for node in tree.body if isinstance(node, ast.Assign)
                  and node.targets[0].id == "bone_order_names_with_parents")
    assert played.KIMODO_SKELETON == tuple(ast.literal_eval(kimodo))
    names, parents, bind, local = kimodo_shaped()
    joints = played.kimodo_joints(names, parents)
    assert [names[own] for own, _ in joints][:3] == ["Hips", "Spine1", "Spine2"] and len(joints) == 23
    wrong = parents.copy()
    wrong[names.index("RightFoot")] = names.index("LeftShin")
    with pytest.raises(ValueError, match="RightFoot hangs from LeftShin"):
        played.kimodo_joints(names, wrong)
    motion, hips, rest = played.to_kimodo(local, bind, joints, parents)
    back = played.from_kimodo(local, bind, joints, parents, motion, hips)
    assert back == pytest.approx(local, abs=1e-9)
    at_bind = np.array(local[:1])
    for joint, parent in enumerate(parents):
        above = np.eye(4) if parent < 0 else bind[parent]
        at_bind[0, joint, :3, :3] = above[:3, :3].T @ bind[joint, :3, :3]
    at_bind[0, 0] = bind[0]
    at_bind[0, names.index("Hips"), :3, 3] = np.linalg.inv(bind[0])[:3] @ np.r_[bind[names.index("Hips"), :3, 3], 1]
    ankle = played.chained(at_bind, parents)[0, names.index("LeftFoot"), :3, 3]
    assert rest[[names[own] for own, _ in joints].index("LeftFoot")] == pytest.approx(ankle)
    six = np.zeros((2, 6))
    six[:, 2] = 1.0  # the left toe end, which the correction does not hold
    six[:, 3] = 1.0  # the right heel
    assert played.foot_contacts(six).tolist() == [[0.0, 0.0, 1.0, 0.0]] * 2
    monkeypatch.setitem(sys.modules, "motion_correction", None)  # a box whose venv was never synced
    with pytest.raises(RuntimeError, match="needs motion_correction, its prebuilt wheel from vendor/kimodo/wheels"):
        played.contacted(local, names, parents, bind, np.zeros((4, 6)))
    # a toe the foot carried down (the foot pitched 30 degrees onto it and turned 40 about the upright) bent all the
    # way toward flat lies as the bind's toe does, turned only as the clip turns it; bent none of the way it is as it
    # was; half bends it half; a toe end hung from the wrong joint is refused
    toes = ["Root", "LeftFoot", "LeftToeBase", "LeftToeEnd"]
    hung = np.array([-1, 0, 1, 2])
    bind = np.tile(np.eye(4), (4, 1, 1))
    bind[1:, :3, 3] = [[0.0, 0.08, 0.0], [0.0, 0.02, 0.12], [0.0, 0.006, 0.17]]
    upright = np.radians(40.0)
    yawed = np.array([[np.cos(upright), 0.0, np.sin(upright)], [0.0, 1.0, 0.0], [-np.sin(upright), 0.0, np.cos(upright)]])
    clip = np.tile(np.eye(4), (1, 4, 1, 1))
    clip[0, 1:, :3, 3] = [[0.0, 0.1, 0.0], [0.0, -0.06, 0.12], [0.0, -0.014, 0.05]]
    clip[0, 1, :3, :3] = yawed @ tipped(30.0)
    for share, toe_turn in ((1.0, yawed), (0.0, yawed @ tipped(30.0)), (0.5, yawed @ tipped(15.0))):
        bent = played.chained(played.toward_flat(clip, toes, hung, bind, played.TOES[0], share), hung)
        assert bent[0, 2, :3, :3] == pytest.approx(toe_turn, abs=1e-9)
        assert bent[0, 2, :3, 3] == pytest.approx(played.chained(clip, hung)[0, 2, :3, 3])  # its base where it was
    with pytest.raises(ValueError, match="LeftToeEnd hangs from LeftFoot"):
        played.toward_flat(clip, toes, np.array([-1, 0, 1, 1]), bind, played.TOES[0], 1.0)


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
