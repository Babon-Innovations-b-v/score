"""A video's motion lands on the rig's own rest (retarget.py): each rig joint takes its mapped BVH joint's turn away
from that joint's rest on top of its own rest, keeps the rig's bone lengths and carries the root's travel on the
hips; a steady turn keeps its quaternions' sign, past half a round too, and the smoothing leaves it where it was
and takes out a one-frame jump without flipping a sign; the clip is resampled to 30 frames a second over the same
seconds, and the travel comes off with the gait's up and down kept.

One tiny synthetic sequence: a BVH written here in sam3dbody-cpp's channel orders, its elbow turning 3 degrees a
frame and its root moving 1 cm a frame, put on a small rig whose arm rests 40 degrees down, unlike the BVH's. Each
answer follows from those numbers (frame 7's elbow: 21 degrees; frame 10's forearm: 30 degrees on its own rest; 20
frames at 25 a second resampled at 30: 23 frames). The same text with its first elbow row read 30, 40, 0 gives the
channel order; beside the retargeted elbow, a bare joint turning 15 degrees a frame (through 180 and on to 285) is
the second row of the steady turns. No model, no machine.

Breaks that turn the test red (each applied once and seen red; the original six 2026-10-26, again 2026-11-13 on the
one merged test):
- the read-back: read_bvh's root `[listed.index(f"{axis}position") for axis in "XYZ"]` made `"ZYX"`.
- the channel order: read_bvh's `Rotation.from_euler(axes.upper(), ...)` made `axes.lower()` (extrinsic: the
  channel order applied the wrong way round).
- the sign past half a round: quaternions' `found[frame, flip] *= -1.0` dropped.
- the own rest and the travel: retarget's `turns[:, joint] = delta @ bind[joint, :3, :3]` made `= delta`; and, apart,
  the travel line `local[:, joint, :3, 3] += travel @ bind[parent, :3, :3]` dropped.
- the one-frame jump: smoothed's `gaussian_filter1d(quaternions(local), sigma, ...)` made `quaternions(local)` (no
  smoothing).
- 30 a second and on the spot: on_the_spot's `place -= np.linspace(...)[:, None] * drift` dropped; and, apart,
  resampled's `* rate)) + 1)` made `* rate)))`.
"""
import pathlib
import sys

import numpy as np
from scipy.spatial.transform import Rotation

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import retarget  # noqa: E402

FRAMES = 20
NAMES = ["Root", "Hips", "Spine1", "LeftArm", "LeftForeArm", "LeftHand"]
PARENTS = [-1, 0, 1, 2, 3, 4]


def bvh_text(first_elbow=(0.0, 0.0), fps=25.0):
    """hip > abdomen > lShldr > lForeArm, the elbow turning 3 degrees a frame about z, the root 1 cm a frame on x;
    frame 0's elbow reads (z, x) = first_elbow."""
    rows = []
    for frame in range(FRAMES):
        elbow = list(first_elbow) if frame == 0 else [frame * 3.0, 0]
        rows.append(" ".join(map(str, [frame * 1.0, 100.0, 0.0, 0, 0, 0, 0, 0, 0, 0, 0, 0, *elbow, 0])))
    return f"""HIERARCHY
ROOT hip
{{
  OFFSET 0 0 0
  CHANNELS 6 Xposition Yposition Zposition Zrotation Yrotation Xrotation
  JOINT abdomen
  {{
    OFFSET 0 10 0
    CHANNELS 3 Zrotation Xrotation Yrotation
    JOINT lShldr
    {{
      OFFSET 15 20 0
      CHANNELS 3 Zrotation Xrotation Yrotation
      JOINT lForeArm
      {{
        OFFSET 25 0 0
        CHANNELS 3 Zrotation Xrotation Yrotation
        End Site
        {{
          OFFSET 20 0 0
        }}
      }}
    }}
  }}
}}
MOTION
Frames: {FRAMES}
Frame Time: {1.0 / fps}
""" + "\n".join(rows) + "\n"


def placed(rotation, at):
    found = np.eye(4)
    found[:3, :3], found[:3, 3] = rotation, at
    return found


def rig_bind():
    """A rig whose rest turns differ from the BVH's (its arm chain turned down 40 degrees), in metres."""
    down = Rotation.from_euler("z", -40, degrees=True).as_matrix()
    return np.stack([placed(np.eye(3), [0, 0, 0]), placed(np.eye(3), [0, 1.0, 0]), placed(np.eye(3), [0, 1.1, 0]),
                     placed(down, [0.15, 1.3, 0]), placed(down, [0.34, 1.14, 0]), placed(down, [0.5, 1.0, 0])])


def world_of(local):
    """Each joint in the world, frame by frame, from the clip against its parents."""
    found = np.empty_like(local)
    for joint, parent in enumerate(PARENTS):
        found[:, joint] = local[:, joint] if parent < 0 else found[:, parent] @ local[:, joint]
    return found


def turn_about(axis, degrees):
    """A turn about x, y or z, written out by hand."""
    cosine, sine = np.cos(np.radians(degrees)), np.sin(np.radians(degrees))
    first, second = {"x": (1, 2), "y": (2, 0), "z": (0, 1)}[axis]
    found = np.eye(3)
    found[first, first] = found[second, second] = cosine
    found[first, second], found[second, first] = -sine, sine
    return found


def spin(step):
    """One bare joint turning `step` degrees a frame about z for FRAMES frames."""
    local = np.tile(np.eye(4), (FRAMES, 1, 1, 1))
    for frame in range(FRAMES):
        local[frame, 0, :3, :3] = turn_about("z", step * frame)
    return local


def worst_step(clip):
    """The forearm's largest turn from one frame to the next, in degrees."""
    turns = clip[:, 4, :3, :3]
    step = np.swapaxes(turns[:-1], -1, -2) @ turns[1:]
    return np.degrees(np.arccos(np.clip((np.trace(step, axis1=-2, axis2=-1) - 1) / 2, -1, 1))).max()


def test_motion_lands_on_the_rigs_rest():
    bvh = retarget.read_bvh(bvh_text())
    assert bvh["names"] == ["hip", "abdomen", "lShldr", "lForeArm"] and bvh["parents"] == [-1, 0, 1, 2]
    assert np.allclose(bvh["rotations"][7, 3], Rotation.from_euler("z", 21, degrees=True).as_matrix())
    assert np.allclose(bvh["root"][5], [5.0, 100.0, 0.0]) and abs(bvh["fps"] - 25.0) < 1e-9
    # Zrotation Xrotation Yrotation read 30, 40, 0: Z(30) then X(40) about the turned axes, the matrix Z(30) X(40)
    assert np.allclose(retarget.read_bvh(bvh_text((30.0, 40.0)))["rotations"][0, 3],
                       turn_about("z", 30) @ turn_about("x", 40))

    bind = rig_bind()
    local = retarget.retarget(bvh, NAMES, PARENTS, bind)
    world = world_of(local)
    bend = Rotation.from_euler("z", 30, degrees=True).as_matrix()  # frame 10
    assert np.allclose(world[10, 4, :3, :3], bend @ bind[4, :3, :3])  # the forearm: the delta on its own rest
    assert np.allclose(world[10, 5, :3, :3], bend @ bind[5, :3, :3])  # the hand, unmapped, follows the forearm
    assert np.allclose(world[10, 2, :3, :3], bind[2, :3, :3]) and np.allclose(world[:, 0], bind[0])
    hand_bone = np.linalg.norm(world[:, 5, :3, 3] - world[:, 4, :3, 3], axis=1)
    assert np.allclose(hand_bone, np.linalg.norm(bind[5, :3, 3] - bind[4, :3, 3]))  # bone lengths are the rig's
    assert np.allclose(world[:, 1, :3, 3] - bind[1, :3, 3], [[frame * 0.01, 0, 0] for frame in range(FRAMES)])
    present = {"hip", "abdomen", "lShldr", "lForeArm"}  # no lHand in this BVH: the hand takes the forearm's
    assert retarget.source_of(NAMES, PARENTS, present) == [None, "hip", "abdomen", "lShldr", "lForeArm", "lForeArm"]

    # steady turns: the retargeted forearm at 3 degrees a frame, a bare joint at 15 through 180 and on. Each turn's
    # quaternions stay on one side (each next to the one before: cos of half a step), and smoothing a steady turn
    # leaves its middle frames where they were
    for clip, joint, step in [(local, 4, 3.0), (spin(15.0), 0, 15.0)]:
        turns = retarget.quaternions(clip)[:, joint]
        assert ((turns[1:] * turns[:-1]).sum(-1) > np.cos(np.radians(step / 2)) - 1e-9).all(), f"{step} a frame"
        assert np.allclose(retarget.smoothed(clip, 1.0)[5:15], clip[5:15], atol=1e-3), f"{step} a frame"
    jumped = local.copy()
    jumped[10, 4, :3, :3] = local[10, 4, :3, :3] @ Rotation.from_euler("x", 40, degrees=True).as_matrix()
    calm = retarget.smoothed(jumped, 2.0)
    assert worst_step(jumped) > 39 and worst_step(calm) < 15
    assert np.allclose(np.swapaxes(calm[..., :3, :3], -1, -2) @ calm[..., :3, :3], np.eye(3), atol=1e-9)
    assert (np.diff(retarget.quaternions(calm), axis=0) ** 2).sum(axis=-1).max() < 0.1  # no sign flips

    again = retarget.resampled(local, 25.0)
    assert len(again) == 23 and np.allclose(again[0], local[0]) and np.allclose(again[12], local[10])  # 0.4 s
    still, drift, moved_back = retarget.on_the_spot(again, NAMES)
    hips = still[:, 1, :3, 3]
    assert drift > 0.18 and np.allclose(hips[0, [0, 2]], hips[-1, [0, 2]]) and np.allclose(hips[:, [0, 2]].mean(0), 0)
    assert np.allclose(hips[:, 1], again[:, 1, 1, 3])  # the height is the gait's, kept
