"""A rigged body's clips grown by the place clips (2099 #161): every clip of a clips rig (place_clips.py's, through
../maker/prop_skeleton.py) the body's file lacks, laid on its own skeleton by the people build's own steps, so a
player model or dressed body laid in a place carries the full set. Run in Kimodo's environment (people/body.py's
steps import the body model):

    <motion env>/bin/python clips_added.py <body.glb> <clips rig.npz> <out body.glb> [--report FILE]

The steps are prop_build.py's for a build's clips, on the file's own skeleton (its skin's bind, its joints' rest
offsets): the clip played on those bones (../played: its travel scaled by the hips' height over the rig's, lifted so the
rig's standing clip's first frame puts the feet where the bind does), the feet brought in (stance.narrowed, a clip
on its feet), each limb swung clear of the body's own skin (clearance.cleared, the file's shown mesh and weights), cut
to a loop and stood over the node (body.prepare_clip; a clip in people/clips.ONCE kept whole), keyed (body.add_clip).
A climb (place_clips.CLIMBS) has its height's run over the loop taken off too, as every clip's travel over the floor
is: the game carries the body up or down the flight, the clip keeps each step's lift. A clip the file has is never
replaced, so the clips it was built with stay byte for byte.
"""
import argparse
import json
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "people"))
sys.path.insert(0, str(HERE.parent / "maker"))
sys.path.insert(0, str(HERE.parent))

import glb  # noqa: E402
import place_clips  # noqa: E402
import played  # noqa: E402
import skel_usd  # noqa: E402

OUTFITS = ("work", "made")  # the shown mesh node: a rigged still's (still_rig.OUTFIT) or a dressed body's


def skeleton(document, blob):
    """The skin's joint names, parents, bind (world 4x4s, the mesh's frame) and rest offsets (each joint's place in its
    parent at the bind)."""
    joints = document["skins"][0]["joints"]
    names = [document["nodes"][joint]["name"] for joint in joints]
    inverse = skel_usd.accessor(document, blob, document["skins"][0]["inverseBindMatrices"]).reshape(-1, 4, 4)
    bind = np.linalg.inv(inverse.transpose(0, 2, 1).astype(float))
    parent = {child: number for number, node in enumerate(document["nodes"]) for child in node.get("children", [])}
    parents = np.array([joints.index(parent[joint]) if parent.get(joint) in joints else -1 for joint in joints])
    local = [bind[joint] if parents[joint] < 0 else np.linalg.inv(bind[parents[joint]]) @ bind[joint]
             for joint in range(len(joints))]
    offsets = np.array([held[:3, 3] for held in local])
    return names, parents, bind, offsets


def shown_skin(document, blob, count):
    """The shown mesh's points (bind pose), faces and weights (points x joints), all its primitives together."""
    node = next(node for node in document["nodes"] if node.get("name") in OUTFITS and "mesh" in node)
    points, faces, weights = [], [], []
    for primitive in document["meshes"][node["mesh"]]["primitives"]:
        held = skel_usd.accessor(document, blob, primitive["attributes"]["POSITION"]).astype(float)
        joints = skel_usd.accessor(document, blob, primitive["attributes"]["JOINTS_0"]).astype(int)
        shares = skel_usd.accessor(document, blob, primitive["attributes"]["WEIGHTS_0"]).astype(float)
        dense = np.zeros((len(held), count))
        np.add.at(dense, (np.repeat(np.arange(len(held)), joints.shape[1]), joints.ravel()), shares.ravel())
        faces.append(skel_usd.accessor(document, blob, primitive["indices"]).reshape(-1, 3).astype(int)
                     + sum(len(part) for part in points))
        points.append(held)
        weights.append(dense)
    return np.concatenate(points), np.concatenate(faces), np.concatenate(weights)


def in_rig_order(rig, names):
    """The clips rig with its joints in the file's skin order (prop_skeleton names the same joints)."""
    order = [list(map(str, rig["names"])).index(name) for name in names]
    moved = {key: rig[key] for key in rig.files}
    moved["bind"] = rig["bind"][order]
    for clip in map(str, rig["clips"]):
        moved[f"clip_{clip}"] = rig[f"clip_{clip}"][:, order]
    return moved


def level_climb(local, direction, frames_a_second):
    """A climb's hips with their height's run over the loop taken off (`direction` up 1, down -1); the rise a
    second the game carries the body, in metres."""
    local = local.copy()
    hips = local[:, played.TRAVELLING_JOINT, 1, 3]
    run = hips[-1] - hips[0]
    local[:, played.TRAVELLING_JOINT, 1, 3] = hips - np.linspace(0.0, 1.0, len(hips)) * run
    if run * direction <= 0:
        raise ValueError(f"the climb goes the wrong way: {run:+.3f} m over the loop")
    return local, float(run * frames_a_second / max(len(hips) - 1, 1))


def contents_of(document, blob):
    """The file's own numbers as the contents a written file starts from, so every slice it had keeps its place."""
    contents = glb.Contents()
    contents._blob = bytearray(blob)
    contents.views = list(document["bufferViews"])
    contents.accessors = list(document["accessors"])
    contents.images = list(document.get("images", []))
    return contents


def added(source, rig_path, out):
    """The file at `source` with every clip of the rig it lacks, written to `out`; the report per clip."""
    import body
    import clearance
    import clips
    import stance
    document, blob = skel_usd.read_glb(source)
    names, parents, bind, offsets = skeleton(document, blob)
    with np.load(rig_path) as held:
        rig = in_rig_order(held, names)
    points, faces, weights = shown_skin(document, blob, len(names))
    fit_rig = {"bind": bind, "offsets": offsets, "parents": parents, "points": points, "faces": faces,
               "weights": weights}
    scale = float(bind[played.TRAVELLING_JOINT, 1, 3] / rig["bind"][played.TRAVELLING_JOINT, 1, 3])
    lift = played.floor_lift(rig, fit_rig, names, scale)
    joint_node = dict(enumerate(document["skins"][0]["joints"]))
    had = {animation["name"] for animation in document["animations"]}
    contents = contents_of(document, blob)
    report = {"hips_scale": round(scale, 4), "floor_lift_m": round(lift, 4), "had": sorted(had), "clips": {}}
    for name in [str(name) for name in rig["clips"] if clips.in_game(str(name)) not in had]:
        world = played.clip_world(rig, name, offsets, parents, scale, lift)
        if name not in clips.OFF_THEIR_FEET:
            world = stance.narrowed(world, names, parents)
        world, swung = clearance.cleared(world, fit_rig, names, parents)
        local, notes = body.prepare_clip(world, parents, body.LEAST_FRAMES, name in clips.ONCE)
        if name in place_clips.CLIMBS:
            local, notes["rise_metres_a_second"] = level_climb(local, place_clips.CLIMBS[name],
                                                                  body.FRAMES_A_SECOND)
        notes["clearance"] = swung
        notes["seconds"] = round(body.add_clip(contents, document, clips.in_game(name), local, joint_node), 2)
        notes["frames"] = int(local.shape[0])
        report["clips"][name] = notes
    glb.write(out, document, contents)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("source", type=pathlib.Path)
    parser.add_argument("rig", type=pathlib.Path)
    parser.add_argument("out", type=pathlib.Path)
    parser.add_argument("--report", type=pathlib.Path)
    options = parser.parse_args()
    report = added(options.source, options.rig, options.out)
    if options.report:
        options.report.write_text(json.dumps(report, indent=1))
    print(f"{options.out}: {len(report['clips'])} clips added ({', '.join(report['clips'])}), "
          f"{len(report['had'])} kept", flush=True)


if __name__ == "__main__":
    main()
