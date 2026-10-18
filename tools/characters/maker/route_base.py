"""The people route's base (owner, 2026-10-18, score #10): SOMA-X's body laid under the made look on the made
skeleton's bind, and SOMA-X's own pose correctives for every clip of the made body. A free prototype step: plain CPU
on the PC in the motion environment (SOMA-X is a body model and its correctives a small network shipped with it; no
card, no cloud).

    ~/.farm-factory-motion/env/bin/python route_base.py base <made rig.npz> <shell.json> <identity.npz> <base.npz>
    ~/.farm-factory-motion/env/bin/python route_base.py correctives <base.npz> <made body.glb> <correctives.npz>
        <identity.npz>

`base` writes two bodies on the same SOMA-X triangles: `shell_points`, the identity prop_shell.py fitted to the
OUTSIDE of the dressed look (its shell.json numbers, laid again exactly as prop_shell does), and `under_points`, the
person SAM 3D Body read off the owner's drawing (the look's identity.npz, the body under the clothes), laid the same
way; with their weights on the 27 kept joints and each point's blended turn from SOMA-X's bind onto the made bind
(`*_turns`, so a rest-space offset can be carried across).

`correctives` reads each clip of the made body's glTF frame by frame (its 27 joints' rotations against their parents;
the dropped finger, jaw and eye joints stay at their bind), asks SOMA-X's correctives network for its rest-space
offsets less its offsets at the bind (the look was made in the bind pose, and the network's offsets there are not
zero: 22 mm on the player's base), turns them onto the made bind with the under-the-clothes base's turns, and
writes them per clip (`clip_<name>`, frames x points x 3, float16, metres).
"""
import json
import pathlib
import sys

import numpy as np

MAKER = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(MAKER), str(MAKER.parent / "people")]
THREADS = 4
LEVEL = "low"


def soma_layer(identity_type):
    """A SOMA-X layer at the low level of detail with its correctives loaded."""
    import soma.assets
    import torch
    from soma.body import SOMALayer
    torch.set_num_threads(THREADS)
    return SOMALayer(data_root=soma.assets.get_assets_dir(), device="cpu", identity_model_type=identity_type,
                     lod=LEVEL, mode="dense")


def kept_joints(layer):
    """The kept joints (people/body.py's rule) in SOMA-X's numbering, and which kept joint carries each joint."""
    import body
    names = list(layer.public_joint_names)
    parents = layer.output_joint_parent_ids.detach().numpy().astype(int)
    kept, _, carries = body.joints_worth_keeping(names, parents)
    return kept, carries


def in_metres(world, vertices):
    """SOMA-X's bind and rest shape in metres (the model's native unit is centimetres)."""
    if np.ptp(vertices[:, 1]) > 10:
        world, vertices = world.copy(), vertices / 100
        world[:, :3, 3] /= 100
    return world, vertices


def rest_of(layer):
    """The layer's cached identity: its public bind (78, 4, 4) and rest shape, in metres."""
    world = layer.public_bind_transforms_world()
    world = (world[0] if world.ndim == 4 else world).detach().numpy().astype(np.float64).copy()
    vertices = layer._cached_rest_shape
    vertices = (vertices[0] if vertices.ndim == 3 else vertices).detach().numpy().astype(np.float64).copy()
    return in_metres(world, vertices)


def shell_identity(record):
    """The layer holding prop_shell.py's fitted identity (the body just inside the dressed look)."""
    import torch
    layer = soma_layer("soma")
    full = np.zeros(layer.identity_model.num_identity_coeffs)
    full[:len(record["coefficients"])] = record["coefficients"]
    layer.prepare_identity(torch.from_numpy(full).float()[None], global_scale=float(record["scale"]))
    return layer


def under_identity(identity_path):
    """The layer holding the body SAM 3D Body read off the drawing (people/body.py build_layer's MHR identity)."""
    import torch
    read = np.load(identity_path)
    numbers = torch.from_numpy(read["mhr_model_params"]).float()[None]
    layer = soma_layer("mhr")
    layer.prepare_identity(torch.from_numpy(read["shape_params"]).float()[None], scale_params=numbers[:, -68:],
                           kwargs={"bone_length_flexibles": numbers[:, 130:136]})
    return layer


def lay_moves(weights, soma_world, made_bind):
    """Each point's blended move from SOMA-X's bind onto the made bind (prop_shell.laid's blend), (points, 4, 4)."""
    moves = made_bind @ np.linalg.inv(soma_world)
    return np.einsum("pj,jab->pab", weights, moves)


def laid_points(vertices, blended):
    """Rest points moved by their blended moves."""
    return np.einsum("pab,pb->pa", blended[:, :3, :3], vertices) + blended[:, :3, 3]


def kept_weights(layer, carries, count):
    import body
    return body.kept_weights(layer, carries, count)


def laid_body(layer, made_bind):
    """One identity laid on the made bind: its points, its weights on the kept joints, its points' turns."""
    kept, carries = kept_joints(layer)
    world, vertices = rest_of(layer)
    weights = kept_weights(layer, carries, len(kept))
    blended = lay_moves(weights, world[kept], made_bind)
    return laid_points(vertices, blended), weights, blended[:, :3, :3]


def offsets_from(points, faces, look_points):
    """The look's points against a body: the share inside it (deeper than 3 mm) and the mean distance."""
    import trimesh
    body = trimesh.Trimesh(points, faces, process=False)
    closest, distance, triangle = trimesh.proximity.closest_point(body, look_points)
    side = np.sign(np.einsum("ij,ij->i", look_points - closest, body.face_normals[triangle]))
    signed = distance * np.where(side == 0, 1.0, side)
    return {"look_inside_body_share": round(float((signed < -0.003).mean()), 4),
            "look_to_body_mean_m": round(float(np.abs(signed).mean()), 4),
            "look_to_body_most_m": round(float(np.abs(signed).max()), 4)}


def base(rig_path, shell_path, identity_path, out):
    """Both bases laid on the made bind; their record against the made look's points."""
    rig = np.load(rig_path)
    shell = shell_identity(json.loads(pathlib.Path(shell_path).read_text()))
    shell_points, weights, shell_turns = laid_body(shell, rig["bind"])
    under_points, under_weights, under_turns = laid_body(under_identity(identity_path), rig["bind"])
    faces = shell.faces.detach().numpy().astype(np.int64)
    np.savez_compressed(out, faces=faces, weights=weights, under_weights=under_weights, shell_points=shell_points,
                        shell_turns=shell_turns, under_points=under_points, under_turns=under_turns)
    return {"shell": offsets_from(shell_points, faces, rig["points"]),
            "under": offsets_from(under_points, faces, rig["points"])}


def bind_locals(layer):
    """Every public joint's bind rotation against its parent (78, 3, 3): what a joint no clip moves holds."""
    world, _ = rest_of(layer)
    parents = layer.output_joint_parent_ids.detach().numpy().astype(int)
    local = world[:, :3, :3].copy()
    for joint, parent in enumerate(parents):
        if 0 <= parent != joint:
            local[joint] = world[parent, :3, :3].T @ world[joint, :3, :3]
    return local


def clip_rotations(document, blob, animation, joint_nodes):
    """A clip's rotations against the parents of the skin's joints, frame by frame (frames, joints, 3, 3)."""
    import joins
    rotations, _ = joins.clip_frames(document, blob, animation)
    picked = rotations[:, joint_nodes].reshape(-1, 4)
    return joins.quaternion_matrices(picked).reshape(len(rotations), len(joint_nodes), 3, 3)


def corrective_offsets(layer, absolute):
    """SOMA-X's correctives network's rest-space offsets, in metres, for absolute rotations (frames, 78, 3, 3)."""
    import torch
    with torch.no_grad():
        out = layer.correctives_model(torch.from_numpy(absolute).float())["out"]
    out = out * float(layer._cached_global_scale) if not isinstance(layer._cached_global_scale, torch.Tensor) \
        else out * layer._cached_global_scale.reshape(-1, 1, 1)
    offsets = out.detach().numpy().astype(np.float64)
    return offsets / 100 if np.abs(offsets).max() > 1.0 else offsets


def correctives(base_path, glb_path, out, identity_path):
    """Every clip's corrective offsets on the under-the-clothes base's points, turned onto the made bind."""
    import joins
    found = np.load(base_path)
    layer = under_identity(identity_path)
    kept, _ = kept_joints(layer)
    resting = bind_locals(layer)
    turns = found["under_turns"]
    at_bind = corrective_offsets(layer, resting[None])
    document, blob = joins.read_glb(glb_path)
    joint_nodes = document["skins"][0]["joints"]
    arrays, most = {}, {}
    for animation in document["animations"]:
        rotations = clip_rotations(document, blob, animation, joint_nodes)
        absolute = np.repeat(resting[None], len(rotations), 0)
        absolute[:, kept] = rotations
        moved = corrective_offsets(layer, absolute) - at_bind
        offsets = np.einsum("pab,fpb->fpa", turns, moved)
        arrays[f"clip_{animation['name']}"] = offsets.astype(np.float16)
        most[animation["name"]] = round(float(np.linalg.norm(offsets, axis=2).max()) * 1000, 1)
    np.savez_compressed(out, **arrays)
    return most


def main():
    step = sys.argv[1]
    if step == "base":
        print("route base:", json.dumps(base(*map(pathlib.Path, sys.argv[2:6]))), flush=True)
    elif step == "correctives":
        most = correctives(*map(pathlib.Path, sys.argv[2:6]))
        print("route correctives, most offset mm per clip:", json.dumps(most), flush=True)
    else:
        raise SystemExit(f"route_base.py: no step {step!r} (base, correctives)")


if __name__ == "__main__":
    main()
