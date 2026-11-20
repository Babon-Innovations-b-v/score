"""The 2099 prologue's smoker's right hand holding the cigarette between drags (#152), solved in code on a people
body as a score_lib pose: the right arm's joint rotations and where the cigarette sits in the hand joint's frame.

    .venv/bin/python tools/props/smoke_beat/hold/hold.py <character.usdc> <out folder>

Writes <out>/pose.json: `joints` {joint path: {"rotation": [w, x, y, z]}}, the local rotations of RightArm and
RightForeArm that replace the body's `standing` clip's at its start (CLIP, SECOND), and `hold` {"joint", "translate",
"rotation"}: the cigarette's frame (its mouth end at the origin, its lit end along +z, cigarette.py's) in RightHand's
own frame, so a reader lays it at that joint's posed transform.

The people's bodies (tools/characters/people/body.py) keep 27 of the SOMA skeleton's joints: the fingers are dropped
and their weight merged into the wrist, so the fingers are no pose here. The pose is the arm (the upper arm hanging
UPPER_FORWARD forward of straight down and UPPER_OUT out from the side, the elbow bent ELBOW, the wrist as the clip
holds it, palm in, fingers forward), and the cigarette is laid in the gap between the index and the middle finger of
the hand's own mesh: across the fingers at GRIP_SHARE of the hand's length from the wrist, a quarter of the hand's
breadth from its middle toward the thumb (four fingers across the breadth, the gap between the second and the third
from the little finger), through the hand's thickness, its lit end out on the back of the hand, gripped at the filter's
middle (GRIP_Z from the mouth end). Every angle and share is the builder's own: no source read gives a held
cigarette's arm (the flat's record said the same of the game's camera-hung one).
"""
import json
import pathlib
import sys

import numpy as np
from pxr import Gf, Usd, UsdSkel

CLIP, SECOND = "standing", 0.0
UPPER_FORWARD, UPPER_OUT, ELBOW = 15.0, 10.0, 90.0  # degrees
GRIP_SHARE = 0.7
GRIP_Z = 0.0235 / 2  # the filter's middle (cigarette.py's FILTER)
SKELETON = "/Character/Turned/Skeleton"
ARM, FOREARM, HAND = "RightArm", "RightForeArm", "RightHand"


def named(paths, name):
    """The joint path ending in `name`."""
    return next(path for path in paths if path.rsplit("/", 1)[-1] == name)


def clip_locals(asset):
    """(joint paths, {path: local 4x4 (row vectors)}) of the body's skeleton in its CLIP at SECOND."""
    skeleton = UsdSkel.Skeleton(asset.GetPrimAtPath(SKELETON))
    paths = [str(path) for path in skeleton.GetJointsAttr().Get()]
    clip = UsdSkel.Animation(asset.GetPrimAtPath(f"/Character/Animations/{CLIP}"))
    time = SECOND * asset.GetTimeCodesPerSecond()
    rotations, translations = clip.GetRotationsAttr().Get(time), clip.GetTranslationsAttr().Get(time)
    scales = clip.GetScalesAttr().Get(time)
    found = {}
    for index, path in enumerate(clip.GetJointsAttr().Get()):
        found[str(path)] = composed(rotations[index], translations[index], scales[index])
    rest = skeleton.GetRestTransformsAttr().Get()
    return paths, {path: found.get(path, np.asarray(rest[index])) for index, path in enumerate(paths)}


def composed(rotation, translation, scale):
    """A local 4x4 (row vectors) from a joint's rotation, translation and scale."""
    matrix = np.eye(4)
    matrix[:3, :3] = np.diag([float(value) for value in scale]) @ np.asarray(Gf.Matrix3d(Gf.Rotation(
        Gf.Quatd(rotation))))
    matrix[3, :3] = [float(value) for value in translation]
    return matrix


def skel_space(paths, locals_):
    """{path: 4x4} of every joint in the skeleton's space, each local times its parent's."""
    found = {}
    for path in paths:
        parent = path.rsplit("/", 1)[0] if "/" in path else None
        found[path] = locals_[path] @ found[parent] if parent in found else locals_[path]
    return found


def turned(angle, axis):
    """A 3x3 rotation (row vectors) of `angle` degrees about the unit `axis`."""
    return np.asarray(Gf.Matrix3d(Gf.Rotation(Gf.Vec3d(*map(float, axis)), float(angle))))


def between(start, end):
    """The shortest 3x3 rotation (row vectors) taking the unit `start` onto the unit `end`."""
    return np.asarray(Gf.Matrix3d(Gf.Rotation(Gf.Vec3d(*map(float, start)), Gf.Vec3d(*map(float, end)))))


def frame_of(paths, world):
    """(up, forward, right) of the body in the skeleton's space: hips to head, left arm to right, and square to both
    (the feet stand turned out, so they give no forward)."""
    position = {path: world[path][3, :3] for path in paths}
    up = unit(position[named(paths, "Head")] - position[named(paths, "Hips")])
    right = position[named(paths, "RightArm")] - position[named(paths, "LeftArm")]
    right = unit(right - (right @ up) * up)
    return up, unit(np.cross(up, right)), right


def unit(vector):
    return np.asarray(vector, dtype=float) / np.linalg.norm(vector)


def aimed(paths, locals_, joint, child, direction):
    """`locals_` with `joint`'s local rotation turned so the bone to `child` points along `direction` (skeleton
    space), the shortest turn."""
    world = skel_space(paths, locals_)
    bone = unit(world[child][3, :3] - world[joint][3, :3])
    turned_world = world[joint].copy()
    turned_world[:3, :3] = world[joint][:3, :3] @ between(bone, direction)
    parent = joint.rsplit("/", 1)[0]
    changed = dict(locals_)
    changed[joint] = turned_world @ np.linalg.inv(world[parent])
    return changed


def arm_pose(paths, locals_):
    """The clip's locals with the right arm set: the upper arm UPPER_FORWARD forward and UPPER_OUT out of straight
    down, the forearm bent ELBOW from it toward the front."""
    up, forward, right = frame_of(paths, skel_space(paths, locals_))
    down = -up
    upper = unit(down @ turned(UPPER_FORWARD, right) @ turned(-UPPER_OUT, forward))
    lower = unit(upper @ turned(ELBOW, unit(np.cross(upper, forward))))
    arm, forearm, hand = named(paths, ARM), named(paths, FOREARM), named(paths, HAND)
    posed = aimed(paths, locals_, arm, forearm, upper)
    return aimed(paths, posed, forearm, hand, lower)


def hand_points(asset, paths):
    """The body's points most weighted to RightHand, in that joint's own frame at its bind (the fingers' too: their
    weight is the wrist's)."""
    skeleton = UsdSkel.Skeleton(asset.GetPrimAtPath(SKELETON))
    binds = [np.asarray(matrix) for matrix in skeleton.GetBindTransformsAttr().Get()]
    hand = paths.index(named(paths, HAND))
    cache = UsdSkel.Cache()
    root = UsdSkel.Root(asset.GetPrimAtPath("/Character"))
    cache.Populate(root, Usd.TraverseInstanceProxies())
    found = []
    for binding in cache.ComputeSkelBindings(root, Usd.TraverseInstanceProxies()):
        for target in binding.GetSkinningTargets():
            if not target.GetPrim().GetPath().pathString.startswith("/Character/Turned/Body/work"):
                continue
            points = np.asarray(target.GetPrim().GetAttribute("points").Get(), dtype=float)
            indices, weights = target.ComputeVaryingJointInfluences(len(points))
            size = target.GetNumInfluencesPerComponent()
            indices, weights = np.asarray(indices).reshape(-1, size), np.asarray(weights).reshape(-1, size)
            order = target.GetJointOrder() or [str(path) for path in skeleton.GetJointsAttr().Get()]
            mapped = np.asarray([paths.index(str(path)) for path in order])[indices]
            strongest = mapped[np.arange(len(points)), weights.argmax(axis=1)]
            mine = points[strongest == hand]
            if len(mine):
                geom = np.asarray(target.GetGeomBindTransform())
                found.append(np.c_[mine, np.ones(len(mine))] @ geom @ np.linalg.inv(binds[hand]))
    return np.concatenate(found)[:, :3]


def hold_frame(points, hand_world, body_frame):
    """(the cigarette's 4x4 (row vectors) in the hand joint's frame, the hand's measures) from the hand's points in
    that frame and the hand joint's skeleton-space transform in the pose the thumb and palm sides are read in (the
    thumb's side faces forward, the palm the body's middle, as a hand hangs by the side)."""
    up, forward, right = body_frame
    centred = points - points.mean(axis=0)
    _, _, axes = np.linalg.svd(centred, full_matrices=False)
    along, across, through = axes
    along = along if (points @ along).mean() > 0 else -along
    to_skel = hand_world[:3, :3]
    across = across if (across @ to_skel) @ forward > 0 else -across  # the thumb's side faces forward
    palm = through if (through @ to_skel) @ -right > 0 else -through  # the palm faces the body's middle
    if np.cross(along, palm) @ across < 0:  # a right hand's thumb is its fingers crossed with its palm's face
        raise ValueError("the hand's thumb and palm sides read as a left hand's: no right hand to hold it in")
    length = float((points @ along).max())
    grip = GRIP_SHARE * length
    near = points[np.abs(points @ along - grip) < 0.1 * length]
    breadth = float(np.ptp(near @ across))
    middle = near.mean(axis=0)
    centre = (float((near @ across).min()) + float((near @ across).max())) / 2
    spot = middle + (grip - middle @ along) * along + (centre + breadth / 4 - middle @ across) * across
    lit = -palm
    frame = np.eye(4)
    frame[0, :3], frame[2, :3] = along, lit
    frame[1, :3] = np.cross(lit, along)
    frame[3, :3] = spot - lit * GRIP_Z
    return frame, {"hand_length": length, "breadth": breadth}


def quaternion(matrix):
    """[w, x, y, z] of a 4x4's (or 3x3's) rotation."""
    rotation = Gf.Matrix3d(*np.asarray(matrix)[:3, :3].flatten().tolist()).ExtractRotation().GetQuat()
    return [rotation.GetReal(), *rotation.GetImaginary()]


def pose(asset_path):
    """The pose record of the body at `asset_path`."""
    asset = Usd.Stage.Open(str(asset_path))
    paths, locals_ = clip_locals(asset)
    posed = arm_pose(paths, locals_)
    hanging = skel_space(paths, locals_)  # the clip's own pose: its hand hangs by the side
    frame, sizes = hold_frame(hand_points(asset, paths), hanging[named(paths, HAND)], frame_of(paths, hanging))
    return {"clip": CLIP, "second": SECOND,
            "joints": {path: {"rotation": quaternion(posed[path])} for path in (named(paths, ARM),
                                                                                named(paths, FOREARM))},
            "hold": {"joint": named(paths, HAND), "translate": frame[3, :3].tolist(), "rotation": quaternion(frame)},
            "angles": {"upper_forward": UPPER_FORWARD, "upper_out": UPPER_OUT, "elbow": ELBOW,
                       "grip_share": GRIP_SHARE, "grip_z": GRIP_Z}, "measured": sizes}


def written(asset_path, out):
    """pose.json written into `out`; its path."""
    out = pathlib.Path(out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "pose.json").write_text(json.dumps(pose(asset_path), indent=1) + "\n")
    return out / "pose.json"


if __name__ == "__main__":
    print(written(sys.argv[1], sys.argv[2]))
