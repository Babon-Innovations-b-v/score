"""Build a person: the SOMA body mesh, its skeleton, and the Kimodo clips that move it.

    bash tools/crew/run.sh

Everything this needs was installed for #36 and is clear for a game that may one day be sold: the
body and the skeleton come from `nvidia/soma-x` (Apache 2.0, marked ready for commercial use) and
the movement from Kimodo clips generated on this box. Both are written onto the same skeleton by
the same vendor, so there is no retargeting step anywhere in here.

Four things this does that are easy to leave out and expensive to leave out:

**It takes the travel off.** The generated walk carries six metres of real travel inside it. Left
in, somebody working at a bench walks through a wall in five seconds. The body walks on the spot
and the game moves the node, which is how every engine does it. The spot is the node itself: the
body is moved back over it once the travel is off, or it is drawn wherever the cut began.

**It closes the loops.** No generated clip ends where it began, so it is cut to the two frames
that match each other best and the small remaining drift is taken out along the way.

**It drops the fingers.** Fifty of the body's seventy-eight joints are hands. Nothing in this game
is ever close enough to see a knuckle, and a crowd of people each carrying fifty finger joints is
paid for every frame. Their weight is merged into the wrist, so the hand is still a hand.

**It puts no material in the file.** A material in a glTF arrives in Godot carrying its own
colour, which this repo calls a bug: a mesh takes a shared material from `game/art/materials/`.
The file names its surfaces and says nothing about what colour they are.
"""
import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import glb  # noqa: E402
import numpy as np  # noqa: E402
import regions  # noqa: E402
import torch  # noqa: E402
from paths import BODIES, MOTIONS  # noqa: E402
from scipy.spatial.transform import Rotation  # noqa: E402

import soma.assets  # noqa: E402
from soma.body import SOMALayer  # noqa: E402

# The body model works in centimetres and the game in metres.
NATIVE_TO_METRES = 0.01
# What the motion model wrote, at the rate it wrote it.
FRAMES_A_SECOND = 30.0
# How many joints one vertex may hang from. glTF holds four in a set and Godot blends four
# without a second set; the run prints how much weight that throws away.
JOINTS_A_VERTEX = 4
# The joint the body model hangs the body's travel on. Joint 0 is a Root that never moves.
TRAVELLING_JOINT = 1
# The two levels of detail that ship: one for somebody in the room, one for somebody across the
# base or in a crowd.
LEVELS = {"near": "low", "far": "xlo"}
# Joints nothing in this game can see, whose weight is merged into whatever is left above them.
# There are no faces, so the jaw and the eyes go with the fingers.
UNSEEN = ("Thumb", "Index", "Middle", "Ring", "Pinky", "Jaw", "Eye")
# The shortest a cut clip may be, in frames. Below about a second a loop reads as a twitch.
LEAST_FRAMES = 30
# How much worse than the best a loop may be and still be taken for being longer. A short clip
# always closes more neatly than a long one, so without this every clip is cut to the minimum and
# a person standing still twitches once a second.
WORTH_THE_LENGTH = 1.6


def build_layer(level):
    """One body model with a plain, average build, ready to be asked for its rig."""
    layer = SOMALayer(data_root=soma.assets.get_assets_dir(), device="cpu",
                      identity_model_type="soma", lod=level, mode="dense")
    layer.prepare_identity(torch.zeros(1, layer.identity_model.num_identity_coeffs))
    return layer


def bind_pose(layer):
    """Where every joint sits before anything moves it, and the mesh hanging there, in metres."""
    world = layer.bind_pose_world[layer.public_transform_joint_indices]
    world = world.detach().numpy().astype(np.float64).copy()
    world[:, :3, 3] *= NATIVE_TO_METRES
    vertices = layer.bind_shape.detach().numpy().astype(np.float64)
    if vertices.ndim == 3:
        vertices = vertices[0]
    return world, vertices * NATIVE_TO_METRES


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


def as_the_engine_sees_them(weights):
    """The weights Godot actually gets: the four strongest a vertex, shared out again."""
    order, kept, _ = strongest_joints(weights, JOINTS_A_VERTEX)
    thinned = np.zeros_like(weights)
    np.put_along_axis(thinned, order, kept, axis=1)
    return thinned


def smooth_normals(vertices, faces):
    """One normal a vertex, from the triangles around it, weighted by how big each one is."""
    corners = vertices[faces]
    crossed = np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0])
    normals = np.zeros_like(vertices)
    for corner in range(3):
        np.add.at(normals, faces[:, corner], crossed)
    lengths = np.linalg.norm(normals, axis=1, keepdims=True)
    return normals / np.where(lengths > 0, lengths, 1.0)


def region_pull(weights, joint_names, surface_names):
    """How strongly each vertex belongs to each surface, from the joints holding it."""
    per_joint = regions.regions_of(joint_names)
    pull = np.zeros((weights.shape[0], len(surface_names)))
    for joint, region in enumerate(per_joint):
        pull[:, surface_names.index(region)] += weights[:, joint]
    return pull


def surface_of_each_triangle(faces, weights, joint_names, surface_names):
    """Which surface every triangle belongs to, from the joints its vertices hang from.

    A triangle whose three corners disagree three ways is settled by which surface pulls hardest
    across all three, not by whichever answer came out of a set first: python does not promise
    the same order for the same strings between runs, so the old way could put a triangle in one
    surface today and another tomorrow from the same inputs.

    Blurring the pull between neighbours was tried here, to straighten what looked like a ruff of
    spikes round the neck in a screenshot. It made the seam measurably worse (138 edges crossing
    it against 134), and the ruff turned out to be shading in the collar's crease, aliased by the
    software renderer this box draws with. Measure the seam before reaching for it again.
    """
    pull = region_pull(weights, joint_names, surface_names)
    per_vertex = pull.argmax(axis=1)
    picked = pull[faces].sum(axis=1).argmax(axis=1)
    chosen = []
    for triangle, fallback in zip(faces, picked):
        here = [per_vertex[corner] for corner in triangle]
        most = max(set(here), key=here.count)
        chosen.append(surface_names[most if here.count(most) > 1 else fallback])
    return chosen


def engine_skinning(bind_vertices, weights, world, inverse_bind):
    """Move the mesh the way Godot will: one matrix a joint, blended per vertex, nothing else."""
    bone = world @ inverse_bind
    padded = np.concatenate([bind_vertices, np.ones((len(bind_vertices), 1))], axis=1)
    moved = np.einsum("jab,vb->jva", bone, padded)[:, :, :3]
    return np.einsum("vj,jva->va", weights, moved)


def posed_by_the_model(layer, path):
    """One generated clip as the body model poses it: a joint transform a frame, plus its mesh."""
    raw = np.load(path)
    rotations = torch.from_numpy(raw["local_rot_mats"].astype(np.float32))
    travel = torch.from_numpy(raw["root_positions"].astype(np.float32))
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


def add_mesh(contents, document, bind_vertices, faces, weights, joint_names, surface_names):
    """Put one level of detail in the file, its triangles split between the surfaces.

    Each surface carries only the vertices its own triangles use. Sharing one vertex list between
    all three is legal and was what this did first, and it makes the engine load every vertex
    three times: Godot spent five minutes on the file and produced three surfaces of 4,505
    vertices each where 4,800 between them was the truth.
    """
    order, kept, lost = strongest_joints(weights, JOINTS_A_VERTEX)
    normals = smooth_normals(bind_vertices, faces)
    belongs_to = surface_of_each_triangle(faces, weights, joint_names, surface_names)

    primitives, counts = [], {}
    for surface in surface_names:
        mine = faces[[surface == where for where in belongs_to]]
        counts[surface] = len(mine)
        if not len(mine):
            continue
        used, rebuilt = np.unique(mine, return_inverse=True)
        primitives.append({
            "attributes": {
                "POSITION": contents.reading(
                    bind_vertices[used].astype(np.float32).ravel().tolist(),
                    "VEC3", glb.FLOAT, glb.ARRAY_BUFFER, with_bounds=True),
                "NORMAL": contents.reading(normals[used].astype(np.float32).ravel().tolist(),
                                           "VEC3", glb.FLOAT, glb.ARRAY_BUFFER),
                "JOINTS_0": contents.reading(order[used].astype(np.uint16).ravel().tolist(),
                                             "VEC4", glb.UNSIGNED_SHORT, glb.ARRAY_BUFFER),
                "WEIGHTS_0": contents.reading(kept[used].astype(np.float32).ravel().tolist(),
                                              "VEC4", glb.FLOAT, glb.ARRAY_BUFFER),
            },
            "indices": contents.reading(
                rebuilt.reshape(-1).astype(np.uint16).tolist(), "SCALAR",
                glb.UNSIGNED_SHORT, glb.ELEMENT_ARRAY_BUFFER),
            "material": surface_names.index(surface),
        })
    document["meshes"].append({"primitives": primitives})
    return len(document["meshes"]) - 1, counts, lost


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


def which_way_is_forward(world):
    """Which way the body walks, so the file can be turned to face the way the game does."""
    travelled = world[-1, TRAVELLING_JOINT, :3, 3] - world[0, TRAVELLING_JOINT, :3, 3]
    axis = int(np.argmax(np.abs(travelled)))
    return "xyz"[axis], float(travelled[axis])


def build(out_path, clip_names):
    layers = {level: build_layer(lod) for level, lod in LEVELS.items()}
    near = layers["near"]
    all_names = list(near.public_joint_names)
    all_parents = near.output_joint_parent_ids.detach().numpy().astype(int)
    kept, parents, carries = joints_worth_keeping(all_names, all_parents)
    joint_names = [all_names[old] for old in kept]
    parents = np.array(parents)
    print(f"skeleton: {len(joint_names)} joints kept of {len(all_names)}")

    bind_world, _ = bind_pose(near)
    bind_world = bind_world[kept]
    inverse_bind = np.linalg.inv(bind_world)
    surface_names = regions.surfaces(joint_names)

    axis, distance = which_way_is_forward(posed_by_the_model(near, MOTIONS / "walking.npz")[0])
    print(f"the walk travels {distance:+.2f} m along {axis}, so the file is turned to face -z")

    document = {
        "asset": {"version": "2.0", "generator": "farm-factory tools/crew"},
        "scene": 0, "scenes": [{"nodes": [0]}],
        "nodes": [], "meshes": [], "skins": [], "animations": [],
        # A material here carries no colour at all: it exists so that Godot names each surface,
        # and the scene puts a shared material from game/art/materials/ over every one of them.
        "materials": [{"name": name} for name in surface_names],
    }
    contents = glb.Contents()

    # Node 0 is the whole person, turned half a circle: the body model builds people facing +z
    # and everything in this game faces -z.
    document["nodes"].append({"name": "Person", "rotation": [0.0, 1.0, 0.0, 0.0], "children": []})
    standing, _ = posed_by_the_model(near, MOTIONS / "standing.npz")
    resting = against_parent(standing[0][kept], parents)
    joint_node = {}
    for joint, name in enumerate(joint_names):
        turn = Rotation.from_matrix(resting[joint, :3, :3]).as_quat()
        document["nodes"].append({"name": name,
                                  "translation": resting[joint, :3, 3].tolist(),
                                  "rotation": [float(value) for value in turn],
                                  "children": []})
        joint_node[joint] = len(document["nodes"]) - 1
    for joint in range(len(joint_names)):
        holder = (document["nodes"][0] if is_the_root(joint, parents)
                  else document["nodes"][joint_node[parents[joint]]])
        holder["children"].append(joint_node[joint])

    document["skins"].append({
        "inverseBindMatrices": contents.reading(
            inverse_bind.transpose(0, 2, 1).astype(np.float32).ravel().tolist(), "MAT4", glb.FLOAT),
        "joints": [joint_node[joint] for joint in range(len(joint_names))],
        "skeleton": joint_node[0],
    })

    report = {"joints": len(joint_names), "surfaces": {}, "levels": {}, "clips": {}}
    for level, layer in layers.items():
        _, vertices = bind_pose(layer)
        faces = layer.faces.detach().numpy().astype(np.uint32)
        weights = merge_weights(layer.public_skinning_weights().detach().numpy().astype(np.float64),
                                carries, len(joint_names))
        mesh, counts, lost = add_mesh(contents, document, vertices, faces, weights,
                                      joint_names, surface_names)
        document["nodes"].append({"name": level, "mesh": mesh, "skin": 0})
        document["nodes"][0]["children"].append(len(document["nodes"]) - 1)
        report["levels"][level] = {"vertices": len(vertices), "triangles": len(faces),
                                   "weightLost": round(lost, 5)}
        report["surfaces"][level] = counts
        print(f"{level:5s}: {len(vertices):5d} vertices, {len(faces):5d} triangles, {counts}, "
              f"worst vertex loses {lost*100:.2f}% of its weight")

    for name in clip_names:
        import clips
        world, _ = posed_by_the_model(near, MOTIONS / f"{name}.npz")
        local, notes = prepare_clip(world[:, kept], parents, LEAST_FRAMES, name in clips.ONCE)
        notes["seconds"] = round(
            add_clip(contents, document, clips.in_game(name), local, joint_node), 2)
        notes["frames"] = int(local.shape[0])
        report["clips"][name] = notes
        print(f"{name:9s}: {notes['frames']:3d} frames of {world.shape[0]}, {notes['seconds']}s, "
              f"took off {notes['travelledMetres']} m of travel, "
              f"moved back {notes['movedBackMetres']} m over the node, "
              f"loop gap {notes['loopGapWhole']} -> {notes['loopGapCut']}")

    _, near_vertices = bind_pose(near)
    near_weights = merge_weights(
        near.public_skinning_weights().detach().numpy().astype(np.float64), carries,
        len(joint_names))
    world, theirs = posed_by_the_model(near, MOTIONS / "walking.npz")
    thinned = as_the_engine_sees_them(near_weights)
    step = max(1, world.shape[0] // 12)
    gaps = np.concatenate([
        np.linalg.norm(
            engine_skinning(near_vertices, thinned, world[frame][kept], inverse_bind)
            - theirs[frame], axis=-1)
        for frame in range(0, world.shape[0], step)])
    hands = np.array([regions.region_of(joint_names[joint]) == regions.SKIN
                      and "Hand" in joint_names[joint]
                      for joint in thinned.argmax(axis=1)])
    everywhere = np.tile(~hands, gaps.shape[0] // len(hands))
    body_only = gaps[everywhere]
    report["skinningGapMillimetres"] = {
        "mean": round(float(gaps.mean()) * 1000, 2), "worst": round(float(gaps.max()) * 1000, 2),
        "meanOffTheHands": round(float(body_only.mean()) * 1000, 2),
        "worstOffTheHands": round(float(body_only.max()) * 1000, 2)}
    print(f"godot's skinning lands {gaps.mean()*1000:.1f} mm from the body model's on average "
          f"({gaps.max()*1000:.1f} mm worst); off the hands, whose fingers were dropped on "
          f"purpose, {body_only.mean()*1000:.1f} mm and {body_only.max()*1000:.1f} mm")

    glb.write(out_path, document, contents)
    report["bytes"] = pathlib.Path(out_path).stat().st_size
    report["height"] = round(float(near_vertices[:, 1].max() - near_vertices[:, 1].min()), 3)
    print(f"\nwrote {out_path}, {report['bytes']/1024:.0f} KB, person {report['height']} m tall")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", default=str(BODIES / "person_body.glb"))
    parser.add_argument("--report", help="where to write the run's numbers as JSON")
    parser.add_argument("--clips", nargs="*", help="which clips go in; the whole set by default")
    arguments = parser.parse_args()
    import clips as clip_names
    wanted = arguments.clips or [name for name in clip_names.SENTENCES
                                 if (MOTIONS / f"{name}.npz").exists()]
    report = build(arguments.out, wanted)
    if arguments.report:
        pathlib.Path(arguments.report).write_text(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
