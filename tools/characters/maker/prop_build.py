"""The prop route's build: a Pixal3D person, its parts and SOMA-X's fitted skeleton written as one skinned glTF with
Kimodo's clips, on the rented card in the motion environment (people/body.py's own clip steps, so the clips are cut,
stood over the node and narrowed exactly as the shipped route's):

    /root/envs/motion/bin/python prop_build.py <fit rig.npz> <mean rig.npz> <parts.npz> <far.npz> <out.glb> <report.json>
        [--outfit work] [--prints prints.npz]

`fit rig.npz` is prop_rig.py's (the fitted bind, every joint's offset against its parent, the mesh in the skeleton's
frame and its weights); `mean rig.npz` prop_skeleton.py's (the mean bind and each clip's joint transforms against their
parents); `parts.npz` prop_parts.py's (each face's part, the parts' names, roles and linear colours).

- **The clips play on the fitted bones.** A frame's rotation against the parent is the clip's own; each joint's
  offset is the fitted skeleton's; the hips' travel is scaled by the fitted hips' height over the mean's, and every
  clip is lifted so the standing clip's first frame puts the feet where the bind does. Then body.py's steps: the feet
  brought in (stance.narrowed), the clip cut to a loop and stood over the node (prepare_clip), keyed (add_clip).
- **Each part is a surface of its own** with one flat material: its name (joins.py's names), its library family's
  colour for this person (no picture colour), its family and material in `extras`; the two printed plates
  (prop_prints.py: the face from the close-up, the flag patch drawn) are the only pictures. A skin part, a boot and a
  mitt get a tuck under every border they share with a garment (tucks.py): the joins joins.py measures and the neck; a
  hard part elsewhere (a belt, a pack) sits on the cloth and needs none. Every hard part and the hair ride one joint
  rigidly (`rigid_joint`: a boot its foot, a mitt its hand, the hair the head, a belt, buckle, helmet or pack the joint
  its weights favour), and a garment within EASE_REACH of a hard part is eased onto that part's joint, so the trouser
  hem goes with the boot it covers.
- **The mesh is the thinned one** where prop_rig.py thinned it part by part (`part_of` in the fit rig), so the outfit
  stays within the shipped player's triangles.
- **The far body** is prop_far.py's (the whole mesh thinned to 1,220 triangles, thinned on the processor where it is
  made), in three surfaces (skin, clothes, boots) of the parts' colours, as body.py's far body is named.
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

import trimesh  # noqa: E402
from scipy.spatial import cKDTree  # noqa: E402
import tucks  # noqa: E402

JOINTS_A_VERTEX = 4
TRAVELLING_JOINT = 1
# How far from a hard part a garment's weights are eased towards its joint (eased_to_hard).
EASE_REACH = 0.06
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


def face_parts(fit_rig, parts):
    """Each fit face's part: the thinned mesh's own (prop_rig.py --parts) where it has one, else parts.npz's."""
    return fit_rig["part_of"] if "part_of" in fit_rig.files else parts["part_of"]


def split_parts(points, faces, weights, part_of):
    """The mesh cut into its parts, each with its own copies of its points: {part index: (points, faces, weights,
    the copied points' numbers in the whole mesh)}."""
    found = {}
    for part in np.unique(part_of):
        mine = faces[part_of == part]
        used, renumbered = np.unique(mine, return_inverse=True)
        found[int(part)] = (points[used], renumbered.reshape(-1, 3), weights[used], used)
    return found


def on_one_joint(count, names, joint):
    weights = np.zeros((count, len(names)))
    weights[:, names.index(joint)] = 1.0
    return weights


def rigid_joint(name, points, weights, names):
    """The one joint a hard part or the hair rides (plan step 3: boots, buckles, helmets, packs ride one joint
    rigidly; the review found the boots stretched 6.7 to 8.2 times on three joints, 2026-10-10): the hair the head, a
    boot its side's foot, a mitt its side's hand, any other the joint its transferred weights favour."""
    side = "Left" if points[:, 0].mean() > 0 else "Right"
    if name == "hair":
        return "Head"
    if name.startswith("boot"):
        return side + "Foot"
    if name.startswith("mitt"):
        return side + "Hand"
    return names[int(weights.sum(0).argmax())]


def eased_to_hard(points, weights, hard_points, hard_joints, names):
    """A garment's weights eased towards the joint of the hard part next to it: a point within EASE_REACH of a hard
    point takes that point's joint by 1 - distance / EASE_REACH, so a trouser leg's hem goes with the boot it covers
    and the cloth by the belt with the belt."""
    if not len(hard_points):
        return weights
    distance, nearest = cKDTree(hard_points).query(points)
    share = np.clip(1.0 - distance / EASE_REACH, 0.0, 1.0)[:, None]
    target = np.zeros_like(weights)
    target[np.arange(len(points)), [names.index(joint) for joint in hard_joints[nearest]]] = 1.0
    return weights * (1 - share) + target * share


SIDED = ("boot", "mitt")


def boot_names(pieces, names_of):
    """The boot parts and the mitt parts gathered by side, each triangle's side by x: one boot_l, boot_r, mitt_l and
    mitt_r each (a GeoSAM2 part can hold a piece of the other boot, whose own middle sent its tuck the wrong way)."""
    found, sided = {}, {}
    for part, (points, faces, weights, used) in pieces.items():
        if names_of[part] not in SIDED:
            found[(part, names_of[part])] = (points, faces, weights, used)
            continue
        for side, sign in ((names_of[part] + "_l", 1.0), (names_of[part] + "_r", -1.0)):
            keep = (sign * points[faces].mean(1)[:, 0]) > 0
            if keep.any():
                kept, renumbered = np.unique(faces[keep], return_inverse=True)
                sided.setdefault(side, []).append((part, points[kept], renumbered.reshape(-1, 3), weights[kept],
                                                   used[kept]))
    for side, bits in sided.items():
        offsets = np.cumsum([0] + [len(bit[1]) for bit in bits])
        found[(bits[0][0], side)] = (np.concatenate([bit[1] for bit in bits]),
                                     np.concatenate([bit[2] + offset for bit, offset in zip(bits, offsets)]),
                                     np.concatenate([bit[3] for bit in bits]), np.concatenate([bit[4] for bit in bits]))
    return found


def hard_things(rigid, pieces):
    """The rigid pieces grouped into things: pieces of one name that touch (share a point of the mesh) are one thing
    and ride one joint, so they never part (a belt's back from the split and its front from the close-up's region);
    pieces of one name apart (Nev's chest box and waist box) stay apart."""
    groups = []
    for key in rigid:
        joined = [group for group in groups if group[0][1] == key[1]
                  and any(np.intersect1d(pieces[other][3], pieces[key][3]).size for other in group)]
        merged = [key] + [other for group in joined for other in group]
        groups = [group for group in groups if group not in joined] + [merged]
    return groups


def printed_uv(prints, part, used, count):
    """A printed part's texture places for its points (`used`, their numbers in the whole mesh) and `count` points
    after them (its tucks): the print's own where the camera saw the point, else the plain texel's. None for a part
    not printed."""
    if prints is None or f"uv_{part}" not in prints.files:
        return None
    uv = prints[f"uv_{part}"][used]
    uv = np.where(np.isnan(uv), prints[f"plain_uv_{part}"], uv)
    return np.concatenate([uv, np.tile(prints[f"plain_uv_{part}"], (count - len(used), 1))])


def surfaces(fit_rig, parts, prints=None):
    """Every surface of the outfit: [(name, role, colour, points, faces, weights, tuck_from, uv, picture)], tucks
    added after a part's own points (`tuck_from` its first tuck point, None where it has no tuck); `uv` and `picture`
    (PNG bytes) for a printed part (prop_prints.py), else None."""
    names = list(fit_rig["names"])
    index = {int(part): number for number, part in enumerate(parts["parts"])}
    names_of = {part: str(parts["names"][number]) for part, number in index.items()}
    pieces = boot_names(split_parts(fit_rig["points"], fit_rig["faces"], fit_rig["weights"],
                                    face_parts(fit_rig, parts)), names_of)
    role_of = {key: str(parts["roles"][index[key[0]]]) for key in pieces}
    hard_points, hard_joints = [np.zeros((0, 3))], [np.zeros(0, dtype=object)]
    rigid = [key for key in pieces if role_of[key] == "hard" or key[1] == "hair"]
    joint_of = {}
    for group in hard_things(rigid, pieces):
        joint = rigid_joint(group[0][1], np.concatenate([pieces[key][0] for key in group]),
                            np.concatenate([pieces[key][2] for key in group]), names)
        joint_of.update({key: joint for key in group})
    for key in rigid:
        points, faces, weights, used = pieces[key]
        joint = joint_of[key]
        pieces[key] = (points, faces, on_one_joint(len(points), names, joint), used)
        if role_of[key] == "hard":
            hard_points.append(points)
            hard_joints.append(np.full(len(points), joint, dtype=object))
    hard_points, hard_joints = np.concatenate(hard_points), np.concatenate(hard_joints)
    for key, (points, faces, weights, used) in list(pieces.items()):
        if role_of[key] == "garment":
            pieces[key] = (points, faces, eased_to_hard(points, weights, hard_points, hard_joints, names), used)
    garment = [piece for key, piece in pieces.items() if role_of[key] == "garment"]
    whole = trimesh.Trimesh(fit_rig["points"], fit_rig["faces"], process=False)
    garment_points = np.concatenate([piece[0] for piece in garment])
    garment_weights = np.concatenate([piece[2] for piece in garment])
    found = []
    for (part, name), (points, faces, weights, used) in sorted(pieces.items(), key=lambda item: item[0][1]):
        role = role_of[(part, name)]
        tuck_from = None
        if role == "skin" or name.startswith(SIDED):
            tuck_from = len(points)
            points, faces, weights = tucks.tucked(points, faces, weights, garment_points, garment_weights,
                                                  bones_of(fit_rig), whole)
        uv = printed_uv(prints, part, used, len(points))
        picture = None if uv is None else prints[f"image_{part}"].tobytes()
        found.append((name, role, parts["colours"][index[part]], points, faces, weights, tuck_from, uv, picture))
    return found


def bones_of(fit_rig):
    """Each joint's bones at the bind pose, as (start, end) places: the bone into it from its parent and those out of
    it to its children."""
    places, parents = fit_rig["bind"][:, :3, 3], fit_rig["parents"]
    bones = {joint: [] for joint in range(len(parents))}
    for joint, parent in enumerate(parents):
        if parent >= 0:
            bones[joint].append((places[parent], places[joint]))
            bones[parent].append((places[parent], places[joint]))
    return {joint: found or [(places[joint], places[joint] + [0.0, 1e-3, 0.0])] for joint, found in bones.items()}


def material(name, role, colour, tuck_from=None, texture=None):
    """A surface's material: its name, role (and first tuck point) in `extras`, its flat colour, or its printed
    picture (`texture`, the document's texture number) over white."""
    extras = {"role": role} if tuck_from is None else {"role": role, "tuck_from": int(tuck_from)}
    shading = {"baseColorFactor": [float(value) for value in colour] + [1.0], "metallicFactor": 0.0,
               "roughnessFactor": 0.85}
    if texture is not None:
        shading.update(baseColorFactor=[1.0, 1.0, 1.0, 1.0], baseColorTexture={"index": texture})
        extras["print"] = True
    return {"name": name, "extras": extras, "pbrMetallicRoughness": shading}


def texture_of(contents, document, picture):
    """A printed picture (PNG bytes) as the document's next texture; its number."""
    image = contents.picture(picture)
    document.setdefault("samplers", [{"magFilter": 9729, "minFilter": 9987, "wrapS": 33071, "wrapT": 33071}])
    document.setdefault("textures", []).append({"source": image, "sampler": 0})
    return len(document["textures"]) - 1


def primitive(contents, body, glb, points, faces, weights, material_index, uv=None):
    """One surface as a glTF primitive with four joints a point (and its texture places, for a print)."""
    order, kept, _ = body.strongest_joints(weights, JOINTS_A_VERTEX)
    normals = body.smooth_normals(points, faces)
    found = {"attributes": {
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
    if uv is not None:
        found["attributes"]["TEXCOORD_0"] = contents.reading(uv.astype(np.float32).ravel().tolist(), "VEC2",
                                                             glb.FLOAT, glb.ARRAY_BUFFER)
    return found


def far_body(far_path):
    """prop_far.py's far body: [(surface, colour, points, faces, weights)] for skin, clothes, boots."""
    far = np.load(far_path)
    found = []
    for number, surface in enumerate(far["surfaces"]):
        mine = far["surface_of_face"] == number
        used, renumbered = np.unique(far["faces"][mine], return_inverse=True)
        found.append((str(surface), far["colours"][number], far["points"][used], renumbered.reshape(-1, 3),
                      far["weights"][used]))
    return found


def build(fit_path, mean_path, parts_path, far_path, out, outfit, prints_path=None):
    """The glTF and its report."""
    import body
    import clips
    import glb
    import stance
    from scipy.spatial.transform import Rotation
    fit_rig, mean_rig, parts = np.load(fit_path), np.load(mean_path), np.load(parts_path)
    prints = np.load(prints_path) if prints_path else None
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
    far = far_body(far_path)
    for surface, colour, points, faces, weights in far:
        document["materials"].append(material(surface, "far", colour))
        far_primitives.append(primitive(contents, body, glb, points, faces, weights, len(document["materials"]) - 1))
    document["meshes"].append({"primitives": far_primitives})
    document["nodes"].append({"name": "far", "mesh": len(document["meshes"]) - 1, "skin": 0})
    document["nodes"][0]["children"].append(len(document["nodes"]) - 1)
    report["levels"]["far"] = {"triangles": int(sum(len(item[3]) for item in far))}
    near = []
    for name, role, colour, points, faces, weights, tuck_from, uv, picture in surfaces(fit_rig, parts, prints):
        texture = None if picture is None else texture_of(contents, document, picture)
        document["materials"].append(material(name, role, colour, tuck_from, texture))
        near.append(primitive(contents, body, glb, points, faces, weights, len(document["materials"]) - 1, uv))
        entry = report["surfaces"].setdefault(name, {"role": role, "triangles": 0, "tuck_points": 0, "pieces": 0})
        entry["triangles"] += int(len(faces))
        entry["tuck_points"] += 0 if tuck_from is None else int(len(points) - tuck_from)
        entry["pieces"] += 1
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
    parser.add_argument("far", type=pathlib.Path, help="prop_far.py's far body")
    parser.add_argument("out", type=pathlib.Path)
    parser.add_argument("report", type=pathlib.Path)
    parser.add_argument("--outfit", default="work")
    parser.add_argument("--prints", type=pathlib.Path, help="prop_prints.py's printed plates")
    options = parser.parse_args()
    sys.argv = sys.argv[:1]
    report = build(options.fit, options.mean, options.parts, options.far, options.out, options.outfit,
                   options.prints)
    options.report.write_text(json.dumps(report, indent=1))
    print(f"built {options.out}: {report['levels']}, {len(report['clips'])} clips", flush=True)


if __name__ == "__main__":
    main()
