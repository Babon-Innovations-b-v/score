"""A body's motion read off a video, put onto the people's rig: SAM 3D Body's BVH (sam3dbody-cpp's offline extractor,
`video_motion.py`, on a rented card) retargeted onto SOMA-X's 27 kept joints, the rig every person's body plays
(rig.npz of people-clips-made: `names`, `parents`, `bind` world 4x4s in metres), smoothed, put on the spot and
written as a rig clip, the same as the rig's own `clip_<name>`: each joint against its parent, frame by frame, at 30
frames a second. Plain numpy and scipy, so it runs here and in the gate.

How a joint is moved: sam3dbody-cpp writes each joint's rotation against its parent as `inv(delta[parent]) .
delta[joint]`, where delta is the joint's turn away from MHR's rest in the world (its README, "BVH export"), so
walking down the chain gives each BVH joint's delta again. A rig joint takes the delta of the BVH joint MAP names
for it, else of its nearest mapped joint above it, and turns its own rest by it: its world turn is delta times its
bind turn. Its bone stays its bind length; the hips also travel as the BVH's root does. The BVH is Y up already
(bvh_writer.cpp flips the camera's Y and Z).

    read_bvh(text)                       -> {names, parents, offsets, rotations [F, N, 3, 3], root [F, 3] cm, fps}
    retarget(bvh, names, parents, bind)  -> [F, 27, 4, 4] against each parent, metres
    smoothed(local, sigma)               the turns and the hips' travel smoothed over time
    resampled(local, fps, rate)          the clip at `rate` frames a second
    on_the_spot(local)                   the travel taken off and the body over its node (people/body.py's rule)
"""
import numpy as np
from scipy.ndimage import gaussian_filter1d
from scipy.spatial.transform import Rotation, Slerp

# SOMA-X's kept joint -> the sam3dbody-cpp BVH joint (bvh/body_mhr.bvh's MakeHuman names) whose turn it takes. A joint
# not here takes its nearest mapped joint's above it: Root none, Spine2 the abdomen's, the head's and toes' ends
# their parents' (MHR predicts no toe turn).
MAP = {"Hips": "hip", "Spine1": "abdomen", "Chest": "chest", "Neck1": "neck", "Neck2": "neck1", "Head": "head",
       "LeftShoulder": "lCollar", "LeftArm": "lShldr", "LeftForeArm": "lForeArm", "LeftHand": "lHand",
       "RightShoulder": "rCollar", "RightArm": "rShldr", "RightForeArm": "rForeArm", "RightHand": "rHand",
       "LeftLeg": "lThigh", "LeftShin": "lShin", "LeftFoot": "lFoot",
       "RightLeg": "rThigh", "RightShin": "rShin", "RightFoot": "rFoot"}
TRAVELLING = "Hips"  # people/body.py's TRAVELLING_JOINT: the joint the travel hangs on
RATE = 30.0  # people/body.py's FRAMES_A_SECOND: the rig's clips' rate
CM = 0.01


def read_bvh(text):
    """A BVH file's skeleton and motion: each joint's name, parent (-1 for the root), offset, its rotation against
    its parent each frame (the channels' order, applied as written) and the root's position in centimetres."""
    tokens = text.split()
    names, parents, offsets, channels, stack, at = [], [], [], [], [], 0
    while tokens[at] != "MOTION":
        word = tokens[at]
        if word in ("ROOT", "JOINT"):
            names.append(tokens[at + 1])
            parents.append(stack[-1] if stack else -1)
            at += 2
        elif word == "End":  # an end site: its block has an offset and no channels
            stack.append(None)
            at += 2
        elif word == "{":
            if stack and stack[-1] is None and tokens[at - 2] == "End":
                at += 1
                continue
            stack.append(len(names) - 1)
            at += 1
        elif word == "}":
            stack.pop()
            at += 1
        elif word == "OFFSET":
            if stack and stack[-1] is not None and len(offsets) < len(names):
                offsets.append([float(value) for value in tokens[at + 1:at + 4]])
            at += 4
        elif word == "CHANNELS":
            count = int(tokens[at + 1])
            channels.append(tokens[at + 2:at + 2 + count])
            at += 2 + count
        else:
            at += 1
    frames, step = int(tokens[at + 2]), float(tokens[at + 5])
    values = np.array(tokens[at + 6:], dtype=np.float64).reshape(frames, -1)
    rotations, root, column = np.empty((frames, len(names), 3, 3)), np.zeros((frames, 3)), 0
    for joint, listed in enumerate(channels):
        block = values[:, column:column + len(listed)]
        column += len(listed)
        axes = "".join(name[0] for name in listed if name.endswith("rotation"))
        angles = block[:, [index for index, name in enumerate(listed) if name.endswith("rotation")]]
        rotations[:, joint] = Rotation.from_euler(axes.upper(), angles, degrees=True).as_matrix()
        if joint == 0:
            root = block[:, [listed.index(f"{axis}position") for axis in "XYZ"]]
    return {"names": names, "parents": parents, "offsets": np.array(offsets), "rotations": rotations, "root": root,
            "fps": 1.0 / step}


def world_deltas(bvh):
    """[F, N, 3, 3]: each BVH joint's turn away from its rest in the world, walked down from the root."""
    found = np.empty_like(bvh["rotations"])
    for joint, parent in enumerate(bvh["parents"]):
        found[:, joint] = bvh["rotations"][:, joint] if parent < 0 else found[:, parent] @ bvh["rotations"][:, joint]
    return found


def source_of(names, parents, present):
    """For each rig joint, the BVH joint name whose delta it takes (MAP, when the BVH has it, else its nearest such
    joint above), None for a joint with none (the Root)."""
    found = []
    for joint, name in enumerate(names):
        walk = joint
        while walk >= 0 and MAP.get(names[walk]) not in present:
            walk = parents[walk]
        found.append(MAP[names[walk]] if walk >= 0 else None)
    return found


def retarget(bvh, names, parents, bind):
    """The BVH's motion on the rig: [F, J, 4, 4], each rig joint against its parent, metres."""
    names, parents, bind = list(map(str, names)), [int(parent) for parent in parents], np.asarray(bind, float)
    deltas, index = world_deltas(bvh), {name: number for number, name in enumerate(bvh["names"])}
    frames = deltas.shape[0]
    turns = np.empty((frames, len(names), 3, 3))
    for joint, source in enumerate(source_of(names, parents, set(index))):
        delta = deltas[:, index[source]] if source else np.broadcast_to(np.eye(3), (frames, 3, 3))
        turns[:, joint] = delta @ bind[joint, :3, :3]
    local = np.zeros((frames, len(names), 4, 4))
    local[:, :, 3, 3] = 1.0
    travel = (bvh["root"] - bvh["root"][:1]) * CM
    for joint, parent in enumerate(parents):
        if parent < 0:
            local[:, joint, :3, :3], local[:, joint, :3, 3] = turns[:, joint], bind[joint, :3, 3]
            continue
        rest = np.linalg.inv(bind[parent]) @ bind[joint]
        local[:, joint, :3, :3] = np.swapaxes(turns[:, parent], 1, 2) @ turns[:, joint]
        local[:, joint, :3, 3] = rest[:3, 3]
        if names[joint] == TRAVELLING:  # the travel, in the parent's (unturned Root's) frame
            local[:, joint, :3, 3] += travel @ bind[parent, :3, :3]
    return local


def quaternions(local):
    """[F, J, 4] each joint's turn as a quaternion, each kept on the side of the frame before (no sign flips)."""
    frames, joints = local.shape[:2]
    found = Rotation.from_matrix(local[:, :, :3, :3].reshape(-1, 3, 3)).as_quat().reshape(frames, joints, 4)
    for frame in range(1, frames):
        flip = (found[frame] * found[frame - 1]).sum(axis=-1) < 0
        found[frame, flip] *= -1.0
    return found


def smoothed(local, sigma):
    """The clip with each joint's turn (quaternions, sign kept, normalised again) and every bone's offset smoothed
    by a Gaussian of `sigma` frames: SAM 3D Body reads each frame alone, so its turns jitter."""
    if sigma <= 0:
        return local.copy()
    quats = gaussian_filter1d(quaternions(local), sigma, axis=0, mode="nearest")
    quats /= np.linalg.norm(quats, axis=-1, keepdims=True)
    found = local.copy()
    found[:, :, :3, :3] = Rotation.from_quat(quats.reshape(-1, 4)).as_matrix().reshape(local.shape[:2] + (3, 3))
    found[:, :, :3, 3] = gaussian_filter1d(local[:, :, :3, 3], sigma, axis=0, mode="nearest")
    return found


def resampled(local, fps, rate=RATE):
    """The clip at `rate` frames a second: each turn slerped, each offset interpolated, over the same seconds."""
    frames = local.shape[0]
    if frames < 2 or abs(fps - rate) < 1e-6:
        return local.copy()
    times = np.arange(frames) / fps
    wanted = np.arange(int(np.floor(times[-1] * rate)) + 1) / rate
    found = np.zeros((len(wanted),) + local.shape[1:])
    found[:, :, 3, 3] = 1.0
    for joint in range(local.shape[1]):
        found[:, joint, :3, :3] = Slerp(times, Rotation.from_matrix(local[:, joint, :3, :3]))(wanted).as_matrix()
        for axis in range(3):
            found[:, joint, axis, 3] = np.interp(wanted, times, local[:, joint, axis, 3])
    return found


def on_the_spot(local, names):
    """The travel taken off and the body stood over its node, across the floor only (people/body.py's
    take_the_travel_off and stand_over_the_node, which import torch, so not imported here): the net drift out of the
    hips, then their mean place across the clip at the middle; the up and down is the gait, kept."""
    found, hips = local.copy(), list(map(str, names)).index(TRAVELLING)
    place = found[:, hips, :3, 3]
    drift = place[-1] - place[0]
    drift[1] = 0.0
    place -= np.linspace(0.0, 1.0, len(place))[:, None] * drift
    middle = place.mean(axis=0)
    middle[1] = 0.0
    place -= middle
    return found, float(np.linalg.norm(drift)), float(np.linalg.norm(middle))
