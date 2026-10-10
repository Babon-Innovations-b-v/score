"""The prop route's build: a Pixal3D person, its parts and SOMA-X's fitted skeleton written as one skinned glTF with
Kimodo's clips, on the rented card in the motion environment (people/body.py's own clip steps, so the clips are cut,
stood over the node and narrowed exactly as the shipped route's):

    /root/envs/motion/bin/python prop_build.py <fit rig.npz> <mean rig.npz> <parts.npz> <out.glb> <report.json>
        [--outfit work]

`fit rig.npz` is prop_rig.py's (the fitted bind, every joint's offset against its parent, the mesh in the skeleton's
frame and its weights); `mean rig.npz` prop_skeleton.py's (the mean bind and each clip's joint transforms against their
parents); `parts.npz` prop_parts.py's (each face's part, the parts' names, roles and linear colours).

- **The clips play on the fitted bones.** A frame's rotation against the parent is the clip's own; each joint's
  offset is the fitted skeleton's; the hips' travel is scaled by the fitted hips' height over the mean's, and every
  clip is lifted so the standing clip's first frame puts the feet where the bind does. Then body.py's steps: the feet
  brought in (stance.narrowed), the clip cut to a loop and stood over the node (prepare_clip), keyed (add_clip).
- **Each part is a surface of its own** with one flat material: its name (joins.py's names), its library family's
  colour for this person (no picture colour), its family and material in `extras`. A skin or hard part gets a tuck
  under every border it shares with a garment (tucks.py). Hard parts ride one joint: the hair the head, a boot its
  side's foot.
- **The far body** is the whole mesh thinned to FAR_TRIANGLES, in three surfaces (skin, clothes, boots) of the parts'
  colours, as body.py's far body is named.
"""
import argparse
import json
import pathlib
import sys

import numpy as np

MAKER = pathlib.Path(__file__).resolve().parent
PEOPLE = MAKER.parent / "people"
sys.path.insert(0, str(MAKER))
sys.path.insert(0, str(PEOPLE))

import tucks  # noqa: E402

FAR_TRIANGLES = 1220
JOINTS_A_VERTEX = 4
TRAVELLING_JOINT = 1
TUCKED_ROLES = ("skin", "hard")
FEET = ("LeftFoot", "RightFoot")


def fk(local, offsets, parents):
    """World transforms (frames, joints, 4, 4) from rotations against the parents (`local`, whose translations are
    used only for the travelling joint) and the fitted offsets."""
    frames, count = local.shape[:2]
    moved = local.copy()
    for joint in range(count):
        if joint != TRAVELLING_JOINT and parents[joint] >= 0:
            moved[:, joint, :3, 3] = offsets[joint]
    world = np.zeros_like(moved)
    for joint in range(count):
        world[:, joint] = moved[:, joint] if parents[joint] < 0 else world[:, parents[joint]] @ moved[:, joint]
    return world


def clip_world(mean_rig, name, offsets, parents, scale, lift):
    """One clip's world transforms on the fitted bones: its travel scaled, lifted by `lift`."""
    local = mean_rig[f"clip_{name}"].copy()
    local[:, TRAVELLING_JOINT, :3, 3] *= scale
    local[:, TRAVELLING_JOINT, 1, 3] += lift
    return fk(local, offsets, parents)


def floor_lift(mean_rig, fit_rig, names, scale):
    """How far the clips are raised so the standing clip's first frame puts the feet joints where the bind does."""
    world = clip_world(mean_rig, "standing", fit_rig["offsets"], fit_rig["parents"], scale, 0.0)
    feet = [names.index(name) for name in FEET]
    return float(fit_rig["bind"][feet, 1, 3].min() - world[0, feet, 1, 3].min())


def split_parts(points, faces, weights, parts):
    """The mesh cut into its parts, each with its own copies of its points: {part index: (points, faces, weights)}."""
    found = {}
    for part in np.unique(parts["part_of"]):
        mine = faces[parts["part_of"] == part]
        used, renumbered = np.unique(mine, return_inverse=True)
        found[int(part)] = (points[used], renumbered.reshape(-1, 3), weights[used])
    return found


def on_one_joint(count, names, joint):
    weights = np.zeros((count, len(names)))
    weights[:, names.index(joint)] = 1.0
    return weights


def rigid(name, points, weights, names):
    """A hard part's weights: the hair on the head, a boot on its side's foot, any other on its strongest joint."""
    if name == "hair":
        return on_one_joint(len(points), names, "Head")
    if name.startswith("boot"):
        side = "Left" if points[:, 0].mean() > 0 else "Right"
        return on_one_joint(len(points), names, side + "Foot")
    return on_one_joint(len(points), names, names[int(weights.sum(0).argmax())])


def boot_names(pieces, names_of):
    """The boot part split by side: each boot point's side by x, as boot_l and boot_r."""
    found = {}
    for part, (points, faces, weights) in pieces.items():
        if names_of[part] != "boot":
            found[(part, names_of[part])] = (points, faces, weights)
            continue
        for side, sign in (("boot_l", 1.0), ("boot_r", -1.0)):
            keep = (sign * points[faces].mean(1)[:, 0]) > 0
            used, renumbered = np.unique(faces[keep], return_inverse=True)
            found[(part, side)] = (points[used], renumbered.reshape(-1, 3), weights[used])
    return found


def surfaces(fit_rig, parts):
    """Every surface of the outfit: [(name, role, colour, points, faces, weights, tuck_from)], tucks added after a
    part's own points (`tuck_from` its first tuck point, None where it has no tuck)."""
    names = list(fit_rig["names"])
    index = {int(part): number for number, part in enumerate(parts["parts"])}
    names_of = {part: str(parts["names"][number]) for part, number in index.items()}
    pieces = boot_names(split_parts(fit_rig["points"], fit_rig["faces"], fit_rig["weights"], parts), names_of)
    garment = [piece for (part, _), piece in pieces.items() if parts["roles"][index[part]] == "garment"]
    garment_points = np.concatenate([piece[0] for piece in garment])
    garment_weights = np.concatenate([piece[2] for piece in garment])
    found = []
    for (part, name), (points, faces, weights) in sorted(pieces.items(), key=lambda item: item[0][1]):
        role = str(parts["roles"][index[part]])
        if role == "hard" or name == "hair":
            weights = rigid(name, points, weights, names)
        tuck_from = None
        if role in TUCKED_ROLES and name != "hair":
            tuck_from = len(points)
            points, faces, weights = tucks.tucked(points, faces, weights, garment_points, garment_weights)
        found.append((name, role, parts["colours"][index[part]], points, faces, weights, tuck_from))
    return found


def material(name, role, colour, tuck_from=None):
    """A surface's flat material: its name, role (and first tuck point) in `extras`, its colour."""
    extras = {"role": role} if tuck_from is None else {"role": role, "tuck_from": int(tuck_from)}
    return {"name": name, "extras": extras,
            "pbrMetallicRoughness": {"baseColorFactor": [float(value) for value in colour] + [1.0],
                                     "metallicFactor": 0.0, "roughnessFactor": 0.85}}


def primitive(contents, body, glb, points, faces, weights, material_index):
    """One surface as a glTF primitive with four joints a point."""
    order, kept, _ = body.strongest_joints(weights, JOINTS_A_VERTEX)
    normals = body.smooth_normals(points, faces)
    return {"attributes": {
        "POSITION": contents.reading(points.astype(np.float32).ravel().tolist(), "VEC3", glb.FLOAT, glb.ARRAY_BUFFER,
                                     with_bounds=True),
        "NORMAL": contents.reading(normals.astype(np.float32).ravel().tolist(), "VEC3", glb.FLOAT, glb.ARRAY_BUFFER),
        "JOINTS_0": contents.reading(order.astype(np.uint16).ravel().tolist(), "VEC4", glb.UNSIGNED_SHORT,
                                     glb.ARRAY_BUFFER),
        "WEIGHTS_0": contents.reading(kept.astype(np.float32).ravel().tolist(), "VEC4", glb.FLOAT,
                                      glb.ARRAY_BUFFER)},
        "indices": contents.reading(faces.reshape(-1).astype(np.uint32).tolist(), "SCALAR", glb.UNSIGNED_INT,
                                    glb.ELEMENT_ARRAY_BUFFER),
        "material": material_index}


def far_body(fit_rig, parts):
    """The whole mesh thinned to FAR_TRIANGLES: [(surface, colour, points, faces, weights)] for skin, clothes, boots."""
    import trimesh
    from scipy.spatial import cKDTree
    whole = trimesh.Trimesh(fit_rig["points"], fit_rig["faces"], process=False)
    thin = whole.simplify_quadric_decimation(face_count=FAR_TRIANGLES)
    nearest_face = cKDTree(whole.triangles_center).query(thin.triangles_center)[1]
    weights = fit_rig["weights"][cKDTree(whole.vertices).query(thin.vertices)[1]]
    names = [str(name) for name in parts["names"]]
    index = {int(part): number for number, part in enumerate(parts["parts"])}
    surface_of_part = {part: ("skin" if parts["roles"][number] in ("skin", "hair") and names[number] != "hair"
                              else "boots" if names[number] == "boot" else "clothes")
                       for part, number in index.items()}
    face_surface = np.array([surface_of_part[int(part)] for part in parts["part_of"][nearest_face]])
    found = []
    for surface in ("skin", "clothes", "boots"):
        mine = face_surface == surface
        if not mine.any():
            continue
        members = [index[part] for part, name in surface_of_part.items() if name == surface]
        colour = np.mean(parts["colours"][members], 0)
        used, renumbered = np.unique(thin.faces[mine], return_inverse=True)
        found.append((surface, colour, thin.vertices[used], renumbered.reshape(-1, 3), weights[used]))
    return found


def build(fit_path, mean_path, parts_path, out, outfit):
    """The glTF and its report."""
    import body
    import clips
    import glb
    import stance
    from scipy.spatial.transform import Rotation
    fit_rig, mean_rig, parts = np.load(fit_path), np.load(mean_path), np.load(parts_path)
    names, parents = [str(name) for name in fit_rig["names"]], np.array(fit_rig["parents"])
    scale = float(fit_rig["bind"][TRAVELLING_JOINT, 1, 3] / mean_rig["bind"][TRAVELLING_JOINT, 1, 3])
    lift = floor_lift(mean_rig, fit_rig, names, scale)
    contents = glb.Contents()
    document = {"asset": {"version": "2.0", "generator": "score tools/characters/maker/prop_build.py"},
                "scene": 0, "scenes": [{"nodes": [0]}], "nodes": [], "meshes": [], "skins": [], "animations": [],
                "materials": []}
    document["nodes"].append({"name": "Person", "rotation": [0.0, 1.0, 0.0, 0.0], "children": []})
    standing = stance.narrowed(clip_world(mean_rig, "standing", fit_rig["offsets"], parents, scale, lift), names,
                               parents)
    resting = body.against_parent(standing[0], parents)
    joint_node = {}
    for joint, name in enumerate(names):
        document["nodes"].append({"name": name, "translation": resting[joint, :3, 3].tolist(),
                                  "rotation": [float(value) for value in
                                               Rotation.from_matrix(resting[joint, :3, :3]).as_quat()],
                                  "children": []})
        joint_node[joint] = len(document["nodes"]) - 1
    for joint in range(len(names)):
        holder = document["nodes"][0] if parents[joint] < 0 else document["nodes"][joint_node[parents[joint]]]
        holder["children"].append(joint_node[joint])
    inverse_bind = np.linalg.inv(fit_rig["bind"])
    document["skins"].append({"inverseBindMatrices": contents.reading(
        inverse_bind.transpose(0, 2, 1).astype(np.float32).ravel().tolist(), "MAT4", glb.FLOAT),
        "joints": [joint_node[joint] for joint in range(len(names))], "skeleton": joint_node[0]})
    report = {"joints": len(names), "hips_scale": round(scale, 4), "floor_lift_m": round(lift, 4), "levels": {},
              "surfaces": {}, "clips": {}, "route": "prop"}
    far_primitives = []
    for surface, colour, points, faces, weights in far_body(fit_rig, parts):
        document["materials"].append(material(surface, "far", colour))
        far_primitives.append(primitive(contents, body, glb, points, faces, weights, len(document["materials"]) - 1))
    document["meshes"].append({"primitives": far_primitives})
    document["nodes"].append({"name": "far", "mesh": len(document["meshes"]) - 1, "skin": 0})
    document["nodes"][0]["children"].append(len(document["nodes"]) - 1)
    report["levels"]["far"] = {"triangles": int(sum(len(item[3]) for item in far_body(fit_rig, parts)))}
    near = []
    for name, role, colour, points, faces, weights, tuck_from in surfaces(fit_rig, parts):
        document["materials"].append(material(name, role, colour, tuck_from))
        near.append(primitive(contents, body, glb, points, faces, weights, len(document["materials"]) - 1))
        report["surfaces"][name] = {"role": role, "triangles": int(len(faces)),
                                    "tuck_points": 0 if tuck_from is None else int(len(points) - tuck_from)}
    document["meshes"].append({"primitives": near})
    document["nodes"].append({"name": outfit, "mesh": len(document["meshes"]) - 1, "skin": 0})
    document["nodes"][0]["children"].append(len(document["nodes"]) - 1)
    report["levels"][outfit] = {"triangles": int(sum(item["triangles"] for item in report["surfaces"].values()))}
    for name in [str(name) for name in mean_rig["clips"]]:
        world = clip_world(mean_rig, name, fit_rig["offsets"], parents, scale, lift)
        if name not in clips.OFF_THEIR_FEET:
            world = stance.narrowed(world, names, parents)
        local, notes = body.prepare_clip(world, parents, body.LEAST_FRAMES, name in clips.ONCE)
        notes["seconds"] = round(body.add_clip(contents, document, clips.in_game(name), local, joint_node), 2)
        notes["frames"] = int(local.shape[0])
        report["clips"][name] = notes
    glb.write(out, document, contents)
    report["bytes"] = pathlib.Path(out).stat().st_size
    report["height"] = round(float(np.ptp(fit_rig["points"][:, 1])), 3)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("fit", type=pathlib.Path)
    parser.add_argument("mean", type=pathlib.Path)
    parser.add_argument("parts", type=pathlib.Path)
    parser.add_argument("out", type=pathlib.Path)
    parser.add_argument("report", type=pathlib.Path)
    parser.add_argument("--outfit", default="work")
    options = parser.parse_args()
    sys.argv = sys.argv[:1]
    report = build(options.fit, options.mean, options.parts, options.out, options.outfit)
    options.report.write_text(json.dumps(report, indent=1))
    print(f"built {options.out}: {report['levels']}, {len(report['clips'])} clips", flush=True)


if __name__ == "__main__":
    main()
