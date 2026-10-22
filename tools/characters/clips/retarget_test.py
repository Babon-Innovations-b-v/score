"""The retarget seam on a tiny synthetic sequence: a BVH written here (sam3dbody-cpp's channel orders) read back, its
elbow bending and its root travelling, put onto a small rig whose rest differs from the BVH's; then the smoothing,
the resampling and the travel taken off. No model, no machine."""
import pathlib
import sys

import numpy as np
from scipy.spatial.transform import Rotation

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import retarget  # noqa: E402

FRAMES = 20
NAMES = ["Root", "Hips", "Spine1", "LeftArm", "LeftForeArm", "LeftHand"]
PARENTS = [-1, 0, 1, 2, 3, 4]


def bvh_text(fps=25.0):
    """hip > abdomen > lShldr > lForeArm, the elbow turning 3 degrees a frame about z, the root 1 cm a frame on x."""
    rows = []
    for frame in range(FRAMES):
        rows.append(" ".join(map(str, [frame * 1.0, 100.0, 0.0, 0, 0, 0, 0, 0, 0, 0, 0, 0, frame * 3.0, 0, 0])))
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


def test_the_bvh_reads_back_in_its_channel_order():
    bvh = retarget.read_bvh(bvh_text())
    assert bvh["names"] == ["hip", "abdomen", "lShldr", "lForeArm"] and bvh["parents"] == [-1, 0, 1, 2]
    assert np.allclose(bvh["rotations"][7, 3], Rotation.from_euler("z", 21, degrees=True).as_matrix())
    assert np.allclose(bvh["root"][5], [5.0, 100.0, 0.0]) and abs(bvh["fps"] - 25.0) < 1e-9


def test_a_bent_elbow_bends_the_rigs_elbow_from_its_own_rest_and_the_hips_travel():
    bind = rig_bind()
    local = retarget.retarget(retarget.read_bvh(bvh_text()), NAMES, PARENTS, bind)
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


def test_the_smoothing_takes_out_a_one_frame_jump_and_keeps_the_signs():
    local = retarget.retarget(retarget.read_bvh(bvh_text()), NAMES, PARENTS, rig_bind())
    jumped = local.copy()
    jumped[10, 4, :3, :3] = local[10, 4, :3, :3] @ Rotation.from_euler("x", 40, degrees=True).as_matrix()

    def worst_step(clip):
        turns = clip[:, 4, :3, :3]
        step = np.swapaxes(turns[:-1], -1, -2) @ turns[1:]
        return np.degrees(np.arccos(np.clip((np.trace(step, axis1=-2, axis2=-1) - 1) / 2, -1, 1))).max()
    calm = retarget.smoothed(jumped, 2.0)
    assert worst_step(jumped) > 39 and worst_step(calm) < 15
    assert np.allclose(np.swapaxes(calm[..., :3, :3], -1, -2) @ calm[..., :3, :3], np.eye(3), atol=1e-9)
    assert (np.diff(retarget.quaternions(calm), axis=0) ** 2).sum(axis=-1).max() < 0.1  # no sign flips


def test_resampled_to_30_a_second_and_put_on_the_spot():
    local = retarget.retarget(retarget.read_bvh(bvh_text(25.0)), NAMES, PARENTS, rig_bind())
    again = retarget.resampled(local, 25.0)
    assert len(again) == 23 and np.allclose(again[0], local[0]) and np.allclose(again[12], local[10])  # 0.4 s
    still, drift, moved_back = retarget.on_the_spot(again, NAMES)
    hips = still[:, 1, :3, 3]
    assert drift > 0.18 and np.allclose(hips[0, [0, 2]], hips[-1, [0, 2]]) and np.allclose(hips[:, [0, 2]].mean(0), 0)
    assert np.allclose(hips[:, 1], again[:, 1, 1, 3])  # the height is the gait's, kept
