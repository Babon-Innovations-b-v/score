"""The SOMA body model, its skeleton, and the Kimodo clips that move it: the people route's pieces
(../maker/prop_skeleton.py, prop_shell.py, prop_build.py, prop_far.py and route_base.py read them; nothing is
built here).

The body and the skeleton come from `nvidia/soma-x` (Apache 2.0), shaped through Meta's MHR body (Apache 2.0)
where SAM 3D Body read a person's build, and the movement from Kimodo clips. Both are written onto the same skeleton
by the same vendor, so there is no retargeting step anywhere in here.

Three things a clip gets here that are easy to leave out and expensive to leave out (its feet are brought in first by
`stance.py`, owner 2026-10-09: "why do they stand so wide"):

**It takes the travel off.** The generated walk carries six metres of real travel inside it. Left
in, somebody working at a bench walks through a wall in five seconds. The body walks on the spot
and the game moves the node, which is how every engine does it. The spot is the node itself: the
body is moved back over it once the travel is off, or it is drawn wherever the cut began.

**It closes the loops.** No generated clip ends where it began, so it is cut to the two frames
that match each other best and the small remaining drift is taken out along the way.

**It drops the fingers.** Fifty of the body's seventy-eight joints are hands. Nothing in this game
is ever close enough to see a knuckle, and a crowd of people each carrying fifty finger joints is
paid for every frame. Their weight is merged into the wrist, so the hand is still a hand.
"""
import functools
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import glb  # noqa: E402
import numpy as np  # noqa: E402
import torch  # noqa: E402
from paths import MOTIONS  # noqa: E402
from person import WHO  # noqa: E402
from scipy.spatial.transform import Rotation  # noqa: E402

import soma.assets  # noqa: E402
from soma.body import SOMALayer  # noqa: E402

# The body model works in centimetres and the game in metres.
NATIVE_TO_METRES = 0.01
# What the motion model wrote, at the rate it wrote it.
FRAMES_A_SECOND = 30.0
# The joint the body model hangs the body's travel on. Joint 0 is a Root that never moves.
TRAVELLING_JOINT = 1
# Joints nothing in this game can see, whose weight is merged into whatever is left above them.
# There are no faces, so the jaw and the eyes go with the fingers.
UNSEEN = ("Thumb", "Index", "Middle", "Ring", "Pinky", "Jaw", "Eye")
# The shortest a cut clip may be, in frames. Below about a second a loop reads as a twitch.
LEAST_FRAMES = 30
# How much worse than the best a loop may be and still be taken for being longer. A short clip
# always closes more neatly than a long one, so without this every clip is cut to the minimum and
# a person standing still twitches once a second.
WORTH_THE_LENGTH = 1.6


def build_layer(level, identity=None):
    """One body model ready to be asked for its rig: a plain, average build, or, given the path
    of what SAM 3D Body read off a picture, that person's build (#100).

    SAM 3D Body answers in Meta's MHR body, which the body model takes as one of its identities
    and fits to its own skeleton, so every clip plays on the picture's body unchanged. Of MHR's
    204 model numbers the last 68 are part scales and 130 to 135 the bone lengths.
    """
    if identity is None:
        layer = SOMALayer(data_root=soma.assets.get_assets_dir(), device="cpu",
                          identity_model_type="soma", lod=level, mode="dense")
        layer.prepare_identity(torch.zeros(1, layer.identity_model.num_identity_coeffs))
        return layer
    read = np.load(identity)
    numbers = torch.from_numpy(read["mhr_model_params"]).float()[None]
    layer = SOMALayer(data_root=soma.assets.get_assets_dir(), device="cpu",
                      identity_model_type="mhr", lod=level, mode="dense")
    layer.prepare_identity(torch.from_numpy(read["shape_params"]).float()[None],
                           scale_params=numbers[:, -68:],
                           kwargs={"bone_length_flexibles": numbers[:, 130:136]},
                           global_scale=WHO["scale"])
    return layer


def bind_pose(layer, lift=None):
    """Where every joint sits before anything moves it, and the mesh hanging there, in metres.
    A person's own is stood on the floor, or raised by `lift`, the near body's, so their far
    body stands where the near one does."""
    if layer.identity_model_type == "soma" or WHO["average_body"]:
        return average_bind_pose(layer)
    return own_bind_pose(layer, lift)


def average_bind_pose(layer):
    """The plain average body's bind pose, from the body model's template buffers."""
    world = layer.bind_pose_world[layer.public_transform_joint_indices]
    world = world.detach().numpy().astype(np.float64).copy()
    world[:, :3, 3] *= NATIVE_TO_METRES
    vertices = layer.bind_shape.detach().numpy().astype(np.float64)
    if vertices.ndim == 3:
        vertices = vertices[0]
    return world, vertices * NATIVE_TO_METRES


def own_bind_pose(layer, lift=None):
    """A picture's person at rest: their own shape and fitted skeleton, which the body model
    caches in metres (#112).

    The template buffers `average_bind_pose` reads are the average body whatever the identity:
    read for a fitted person, they gave every build the same body and left the clips' skeleton
    10 mm off the mesh on average, 59 mm at worst (take C's build report, 2026-09-29). The fitted
    body hangs from its hips at the model's own height, its soles off the floor; mesh and joints
    are stood down together, which changes no skinning."""
    world = layer.public_bind_transforms_world()
    world = world[0] if world.ndim == 4 else world
    vertices = layer._cached_rest_shape
    vertices = vertices[0] if vertices.ndim == 3 else vertices
    world = world.detach().numpy().astype(np.float64).copy()
    vertices = vertices.detach().numpy().astype(np.float64).copy()
    lift = floor_lift(layer) if lift is None else lift
    vertices[:, 1] += lift
    world[:, 1, 3] += lift
    return world, vertices


def floor_lift(layer):
    """How far a person's own rest shape is raised to stand on the floor."""
    vertices = layer._cached_rest_shape.detach().numpy()
    return -float(vertices.reshape(-1, 3)[:, 1].min())


def is_the_root(joint, parents):
    """Whether a joint hangs from nothing.

    The body model marks its root joint by making it its own parent, not by giving it none. Read
    as "no parent" that is a joint which is its own child, which is a loop: written into a glTF
    file it makes Godot walk the skeleton for ever. Nothing measured here catches it, because
    every pose, every bone length and every vertex is still right; the file simply cannot be
    read. Found on #36 by Godot spending fifteen minutes at full tilt on a 600 KB file.
    """
    return parents[joint] < 0 or parents[joint] == joint


def joints_worth_keeping(joint_names, parents):
    """Which joints ship, and which kept joint each dropped one's weight goes to.

    Returns the kept joints in their old numbering, their parents in the new numbering, and a
    list saying, for every old joint, which new joint carries its weight.
    """
    keep = [not any(mark in name for mark in UNSEEN) for name in joint_names]
    new_number = {}
    for old, kept in enumerate(keep):
        if kept:
            new_number[old] = len(new_number)

    carries = []
    for old in range(len(joint_names)):
        walk = old
        while not keep[walk]:
            if is_the_root(walk, parents):
                raise ValueError(f"{joint_names[old]} hangs from nothing that is being kept")
            walk = parents[walk]
        carries.append(new_number[walk])

    kept_joints = [old for old, yes in enumerate(keep) if yes]
    new_parents = [-1 if is_the_root(old, parents) else new_number[parents[old]]
                   for old in kept_joints]
    return kept_joints, new_parents, carries


def merge_weights(weights, carries, kept_count):
    """Hand every dropped joint's weight to the joint that took its place."""
    merged = np.zeros((weights.shape[0], kept_count))
    for old in range(weights.shape[1]):
        merged[:, carries[old]] += weights[:, old]
    return merged


def kept_weights(layer, carries, kept_count):
    """The body model's skinning weights on the kept joints."""
    return merge_weights(layer.public_skinning_weights().detach().numpy().astype(np.float64), carries, kept_count)


def against_parent(world, parents):
    """Turn each joint's place in the world into its place against its parent, which is what
    glTF stores."""
    local = np.empty_like(world)
    for joint in range(len(parents)):
        local[joint] = (world[joint] if is_the_root(joint, parents)
                        else np.linalg.inv(world[parents[joint]]) @ world[joint])
    return local


def strongest_joints(weights, how_many):
    """The few joints each vertex hangs from most, with the rest of its weight shared out again.

    Returns the joint numbers, the weights, and how much weight the worst vertex lost.
    """
    order = np.argsort(-weights, axis=1)[:, :how_many]
    kept = np.take_along_axis(weights, order, axis=1)
    lost = 1.0 - kept.sum(axis=1)
    kept = kept / kept.sum(axis=1, keepdims=True)
    return order, kept, float(lost.max())


def smooth_normals(vertices, faces):
    """One normal a vertex, from the triangles around it, weighted by how big each one is."""
    corners = vertices[faces]
    crossed = np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0])
    normals = np.zeros_like(vertices)
    for corner in range(3):
        np.add.at(normals, faces[:, corner], crossed)
    lengths = np.linalg.norm(normals, axis=1, keepdims=True)
    return normals / np.where(lengths > 0, lengths, 1.0)


@functools.cache
def feet_lift(layer):
    """How far this build's clips must be raised to stand on the floor where the average body
    does (#112): the motion model writes the hips' height for the average body, so a longer leg
    sinks into the floor and a shorter one floats. Measured on the first standing frame."""
    if layer.identity_model_type == "soma" or WHO["average_body"]:
        return 0.0
    raw = np.load(MOTIONS / "standing.npz")
    rotations = torch.from_numpy(raw["local_rot_mats"][:1].astype(np.float32))
    travel = torch.from_numpy(raw["root_positions"][:1].astype(np.float32))
    average = build_layer(layer.lod)
    lowest = [float(model.pose(rotations, transl=travel, pose2rot=False).vertices[..., 1].min())
              for model in (average, layer)]
    lift = lowest[0] - lowest[1]
    print(f"feet lift for this build: {lift * 1000:+.1f} mm")
    return lift


def posed_by_the_model(layer, path):
    """One generated clip as the body model poses it: a joint transform a frame, plus its mesh,
    stood on the floor where the average body stands."""
    raw = np.load(path)
    rotations = torch.from_numpy(raw["local_rot_mats"].astype(np.float32))
    travel = raw["root_positions"].astype(np.float32).copy()
    travel[:, 1] += feet_lift(layer)
    travel = torch.from_numpy(travel)
    posed = layer.pose(rotations, transl=travel, pose2rot=False, return_transforms=True)
    return posed.transforms.detach().numpy().astype(np.float64), posed.vertices.detach().numpy()


def turns_of(local):
    """Every joint's turn in every frame, as one row a frame, for comparing two frames.

    A turn written as four numbers has two spellings: the numbers and all four negated mean the
    same turn. Two frames of the same pose spelled differently look two whole units apart, which
    is as far apart as two turns can be, so every frame is put on the same side as the first one
    before anything is compared. Reading the sign off one of the four numbers is not enough,
    because that number passes through zero.
    """
    frames, joints = local.shape[0], local.shape[1]
    flat = Rotation.from_matrix(local[:, :, :3, :3].reshape(-1, 3, 3)).as_quat()
    flat = flat.reshape(frames, joints, 4)
    same_side = np.sign((flat * flat[:1]).sum(axis=-1, keepdims=True))
    return (flat * np.where(same_side == 0, 1.0, same_side)).reshape(frames, -1)


def loop_gap(local):
    """How far the clip's last frame is from its first: what a player sees as a jump."""
    rows = turns_of(local)
    return float(np.linalg.norm(rows[-1] - rows[0]))


def best_loop(local, least_frames):
    """The stretch of the clip that runs round most neatly, preferring a longer one.

    A short stretch always closes more neatly than a long one, because there is less of it to
    drift. Taking the neatest would cut every clip to the minimum, so the neatest is found first
    and then the longest stretch that is nearly as neat is taken instead.
    """
    rows = turns_of(local)
    frames = rows.shape[0]
    runs = []
    for start in range(frames - least_frames):
        ends = np.arange(start + least_frames, frames)
        gaps = np.linalg.norm(rows[ends] - rows[start], axis=1)
        pick = int(np.argmin(gaps))
        runs.append((float(gaps[pick]), start, int(ends[pick])))
    neatest = min(run[0] for run in runs)
    allowed = [run for run in runs if run[0] <= max(neatest * WORTH_THE_LENGTH, neatest + 0.02)]
    gap, start, end = max(allowed, key=lambda run: run[2] - run[1])
    return (start, end), gap


def take_the_travel_off(local):
    """Walk on the spot: the net travel is taken out, the sway of each step is left in."""
    local = local.copy()
    hips = local[:, TRAVELLING_JOINT, :3, 3]
    drift = hips[-1] - hips[0]
    drift[1] = 0.0                      # the up and down is the gait, not travel
    steps = np.linspace(0.0, 1.0, len(hips))[:, None]
    local[:, TRAVELLING_JOINT, :3, 3] = hips - steps * drift
    return local, float(np.linalg.norm(drift))


def stand_over_the_node(local):
    """Put the body over its own node: the hips' average place across the clip, at the middle.

    Taking the travel off leaves the body wherever it had got to when the cut began, and a clip is
    cut from the middle of what the motion model wrote. The walk was being drawn 2.17 m in front
    of the point the game moves and the drag 0.69 m behind it, so somebody walking a round went
    round corners on a two-metre arm, into the walls, and jumped two metres every time they
    stopped to work (#36, found after the 2026-09-26 playtest). Only across the floor: the height
    is the body's own.
    """
    local = local.copy()
    hips = local[:, TRAVELLING_JOINT, :3, 3]
    off = hips.mean(axis=0)
    off[1] = 0.0
    local[:, TRAVELLING_JOINT, :3, 3] = hips - off
    return local, float(np.linalg.norm(off))


def prepare_clip(world, parents, least_frames, once=False):
    """One clip ready to ship: cut to a loop, standing still, against each joint's parent.

    A clip that plays once is kept whole: cutting it to a loop would cut out the very movement
    it was written for.
    """
    local = np.stack([against_parent(frame, parents) for frame in world])
    before = loop_gap(local)
    (start, end), _ = ((0, len(local)), 0.0) if once else best_loop(local, least_frames)
    local = local[start:end]
    local, travelled = take_the_travel_off(local)
    local, moved_back = stand_over_the_node(local)
    return local, {"cutFrom": start, "cutTo": end, "travelledMetres": round(travelled, 3),
                   "movedBackMetres": round(moved_back, 3),
                   "loopGapWhole": round(before, 4), "loopGapCut": round(loop_gap(local), 4)}


def the_body_at(layer, carries, kept_count):
    """The body at its bind pose: vertices in metres, triangles, and weights on the kept joints."""
    _, vertices = bind_pose(layer)
    faces = layer.faces.detach().numpy().astype(np.uint32)
    return vertices, faces, kept_weights(layer, carries, kept_count)


def add_clip(contents, document, name, local, joint_node):
    """Put one clip in the file: a turn a frame for every joint, and the body's own sway."""
    frames = local.shape[0]
    times = contents.reading([frame / FRAMES_A_SECOND for frame in range(frames)],
                             "SCALAR", glb.FLOAT)
    samplers, channels = [], []
    for joint in range(local.shape[1]):
        turns = Rotation.from_matrix(local[:, joint, :3, :3]).as_quat().astype(np.float32)
        samplers.append({"input": times, "interpolation": "LINEAR",
                         "output": contents.reading(turns.ravel().tolist(), "VEC4", glb.FLOAT)})
        channels.append({"sampler": len(samplers) - 1,
                         "target": {"node": joint_node[joint], "path": "rotation"}})
    sway = local[:, TRAVELLING_JOINT, :3, 3].astype(np.float32)
    samplers.append({"input": times, "interpolation": "LINEAR",
                     "output": contents.reading(sway.ravel().tolist(), "VEC3", glb.FLOAT)})
    channels.append({"sampler": len(samplers) - 1,
                     "target": {"node": joint_node[TRAVELLING_JOINT], "path": "translation"}})
    document["animations"].append({"name": name, "samplers": samplers, "channels": channels})
    return frames / FRAMES_A_SECOND
