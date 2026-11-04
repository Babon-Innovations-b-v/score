"""The prop route's moving base (owner, 2026-10-12 21:40: "the SOMA mesh is the moving base; the Pixal3D look follows
it"): SOMA-X's body, its shape fitted to the outside of the dressed look, carries the look as a thin shell. Replaces
the weights RSWT moved over from the mean body (prop_rig.py), whose inpainted weights let the look warp.

    fit   (the card's motion environment, prop_chain.py `shell`):
          /root/envs/motion/bin/python prop_shell.py fit <fit rig.npz> <shell.npz>
          SOMA-X's identity (its first FITTED shape numbers and a global scale) chosen by damped Gauss-Newton (`fit`)
          so the body, laid on the fitted skeleton's bind (each kept joint's SOMA bind moved onto the fitted one, the
          surface by SOMA's own weights), lies just inside the look. SOMA's bone-length scales are not fitted: they
          cover only limb and finger segments, whose joints the laying already puts on the fitted skeleton's.
    bind  (the PC, the prop environment: plain geometry):
          ~/.farm-factory-props/env/bin/python prop_shell.py bind <fit rig.npz> <shell.npz> <out rig.npz> <shell.json>
              [<parts.npz>]
          every look point bound to its closest body triangle: its weights SOMA's at that point (the triangle's corners'
          weights by the point's barycentric place), its offset along the body's normal recorded; the fit rig written
          again with those weights (the RSWT ones kept as `rswt_weights`). Hard parts and hair still ride one joint
          each, and so do the hands (prop_build.py's rigid_joint). shell.json: per part the offsets' most, mean and
          depth inside and their count per whole millimetre (`offsets_mm`, so a gate can pool parts), and the fit's
          measures. Where the fitted body holds under REACH_SHARE of the look's soft points within REACH (a bulky
          suit the fit's scale and shape numbers cannot fill), the look is bound instead to that body drawn onto the
          suit's inside along its own normals (`drawn_to_suit`), recorded under shell.json's `suit`; a look the
          fitted body already holds is bound exactly as before.
"""
import json
import pathlib
import sys

import numpy as np

MAKER = pathlib.Path(__file__).resolve().parent
FITTED = 24
INSIDE_MARGIN = 0.003
SCALE_RANGE = (0.85, 1.25)
COEFF_RANGE = 5.0
SAMPLES = 6000
# The Gauss-Newton fit: its rounds, the steps its Jacobian takes on a shape number and on the scale, its starting
# damping, and the weight of the look's points reaching for the body against the body's points reaching inside.
ROUNDS = 12
COEFF_STEP = 0.25
SCALE_STEP = 0.01
DAMPING = 1.0
COVER_WEIGHT = 0.5
# The shell's reach and the share of the soft points it holds, as the body gate judges them
# (score/stages/people_bodies/bodies.py's OFFSET_MOST and SHELL_SHARE, named, not imported: the gate stays there).
REACH = 0.05
REACH_SHARE = 0.99
# A bulky suit (2026-11-04: the spacesuit's fit ran to the largest scale and every shape number to its bound and still
# stood 11 cm under the suit at the chest and 5 cm through it at the neck and hips, 91.3% of its soft points within
# REACH): the fitted body drawn onto the suit's inside along its own normals, by at most SUIT_MOST (a padded suit's
# thickness), in up to SUIT_ROUNDS rounds of SUIT_STEP of the way each, the best round kept. Measured on the
# spacesuit's own look and parts over the astronaut's fitted SOMA-X body laid on its skeleton (2026-11-04): 99.8% of
# its soft points within REACH, from 78%.
SUIT_MOST = 0.10
SUIT_ROUNDS = 40
SUIT_STEP = 0.5


def soma_layer():
    """SOMA-X's body model at the low level of detail, with its kept joints (people/body.py's)."""
    sys.path.insert(0, str(MAKER.parent / "people"))
    import body
    import soma.assets
    import torch
    from soma.body import SOMALayer
    layer = SOMALayer(data_root=soma.assets.get_assets_dir(), device="cpu", identity_model_type="soma", lod="low",
                      mode="dense")
    layer.prepare_identity(torch.zeros(1, layer.identity_model.num_identity_coeffs))
    names = list(layer.public_joint_names)
    parents_all = layer.output_joint_parent_ids.detach().numpy().astype(int)
    kept, _, carries = body.joints_worth_keeping(names, parents_all)
    return layer, body, kept, carries


def soma_bind(layer, coefficients, scale):
    """The body's bind: kept-joint-free world transforms (all public joints) and its vertices, in metres."""
    import torch
    count = layer.identity_model.num_identity_coeffs
    full = np.zeros(count)
    full[:len(coefficients)] = coefficients
    layer.prepare_identity(torch.from_numpy(full).float()[None], global_scale=float(scale))
    world = layer.public_bind_transforms_world()
    world = (world[0] if world.ndim == 4 else world).detach().numpy().astype(np.float64).copy()
    vertices = layer._cached_rest_shape
    vertices = (vertices[0] if vertices.ndim == 3 else vertices).detach().numpy().astype(np.float64).copy()
    if np.ptp(vertices[:, 1]) > 10:  # the model's native centimetres
        vertices, world[:, :3, 3] = vertices / 100, world[:, :3, 3] / 100
    return world, vertices


def laid(vertices, weights, soma_world, fit_bind):
    """The body moved onto the fitted skeleton's bind: each kept joint's SOMA bind onto the fitted one, blended by
    SOMA's own weights."""
    moves = fit_bind @ np.linalg.inv(soma_world)
    blended = np.einsum("pj,jab->pab", weights, moves)
    return np.einsum("pab,pb->pa", blended[:, :3, :3], vertices) + blended[:, :3, 3]


def vertex_normals(points, faces):
    corners = points[faces]
    face_normals = np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0])
    found = np.zeros_like(points)
    for corner in range(3):
        np.add.at(found, faces[:, corner], face_normals)
    return found / np.maximum(np.linalg.norm(found, axis=1, keepdims=True), 1e-12)


def fit(fit_path, out):
    """The identity whose body lies just inside the look, by damped Gauss-Newton on matched points (each round every
    body point is matched to the look's nearest point moved INSIDE_MARGIN in along its normal, and COVER_WEIGHT of the
    look's sampled points to the body's nearest point), the Jacobian by a step of each shape number: shell.npz. A
    least-squares fit on the summed nearest distances stopped after about 40 evaluations with only the scale moved
    (Bram's look 11 cm off, 2026-10-13)."""
    from scipy.spatial import cKDTree
    rig = np.load(fit_path)
    layer, body, kept, carries = soma_layer()
    weights = body.kept_weights(layer, carries, len(kept))
    faces = layer.faces.detach().numpy().astype(np.int64)
    look, look_normals = rig["points"], vertex_normals(rig["points"], rig["faces"])
    rng = np.random.default_rng(0)
    sampled = look[rng.choice(len(look), min(SAMPLES, len(look)), replace=False)]
    look_tree = cKDTree(look)
    fitted = min(FITTED, layer.identity_model.num_identity_coeffs)
    low = np.r_[np.full(fitted, -COEFF_RANGE), SCALE_RANGE[0]]
    high = np.r_[np.full(fitted, COEFF_RANGE), SCALE_RANGE[1]]
    steps = np.r_[np.full(fitted, COEFF_STEP), SCALE_STEP]

    def shell(variables):
        world, vertices = soma_bind(layer, variables[:-1], variables[-1])
        return laid(vertices, weights, world[kept], rig["bind"])

    def matched(points):
        """The residuals (body to its inside target, then weighted look samples to the body) and the points used."""
        _, nearest = look_tree.query(points)
        target = look[nearest] - look_normals[nearest] * INSIDE_MARGIN
        _, cover = cKDTree(points).query(sampled)
        return np.r_[(points - target).ravel(), np.sqrt(COVER_WEIGHT) * (points[cover] - sampled).ravel()], cover

    def offsets(points):
        near, _ = cKDTree(points).query(look)
        return float(near.mean()), float(near.max())

    variables = np.r_[np.zeros(fitted), 1.0]
    points = shell(variables)
    start = offsets(points)
    damping = DAMPING
    for _ in range(ROUNDS):
        residual, cover = matched(points)
        columns = []
        for number in range(len(variables)):
            moved = variables.copy()
            moved[number] = min(high[number], moved[number] + steps[number])
            change = (shell(moved) - points) / max(moved[number] - variables[number], 1e-9)
            columns.append(np.r_[change.ravel(), np.sqrt(COVER_WEIGHT) * change[cover].ravel()])
        jacobian = np.stack(columns, 1)
        normal = jacobian.T @ jacobian
        step = np.linalg.solve(normal + damping * np.diag(np.diag(normal) + 1e-9), -jacobian.T @ residual)
        trial = np.clip(variables + step, low, high)
        trial_points = shell(trial)
        if np.sum(matched(trial_points)[0] ** 2) < np.sum(residual ** 2):
            variables, points, damping = trial, trial_points, damping / 3
        else:
            damping *= 4
    mean, most = offsets(points)
    np.savez_compressed(out, points=points, faces=faces, weights=weights, coefficients=variables[:-1],
                        scale=variables[-1], loss_start=start[0], loss=mean)
    return {"start_mean_m": round(start[0], 4), "start_most_m": round(start[1], 4), "scale": round(float(variables[-1]), 4),
            "look_to_body_mean_m": round(mean, 4), "look_to_body_most_m": round(most, 4)}


def part_record(offsets, mine, rig):
    """A part's offsets: the most (and the joint nearest that point), the mean, the depth inside, and the count per
    whole millimetre (`offsets_mm`, so a gate can pool parts)."""
    reach = np.abs(offsets[mine])
    worst = rig["points"][mine][reach.argmax()]
    nearest = int(np.linalg.norm(rig["bind"][:, :3, 3] - worst, axis=1).argmin())
    return {"most_m": round(float(reach.max()), 4), "most_near": str(rig["names"][nearest]),
            "mean_m": round(float(reach.mean()), 4), "inside_m": round(float(-offsets[mine].min()), 4),
            "offsets_mm": np.bincount(np.round(reach * 1000).astype(int)).tolist()}


def bound(body, body_weights, points):
    """Each point bound to its closest body triangle: SOMA's weights there (the corners' by the point's barycentric
    place) and its offset along the body's normal, positive outside."""
    import trimesh
    closest, distance, triangle = trimesh.proximity.closest_point(body, points)
    corners = body.faces[triangle]
    places = trimesh.triangles.points_to_barycentric(body.vertices[corners], closest)
    places = np.clip(places, 0.0, None)
    places /= places.sum(axis=1, keepdims=True)
    weights = np.einsum("pc,pcj->pj", places, body_weights[corners])
    side = np.sign(np.einsum("ij,ij->i", points - closest, body.face_normals[triangle]))
    return weights, distance * np.where(side == 0, 1.0, side)


def soft_points(rig, parts):
    """The look's points not on a part that rides one joint (prop_build.py's rule: a hard part but a belt or a
    buckle, the hair, the bare hands), by the fit rig's own face parts (prop_build.face_parts' choice) and parts.npz's
    names and roles."""
    import prop_build
    index = {int(part): number for number, part in enumerate(parts["parts"])}
    rigid = {part for part, number in index.items()
             if (str(parts["roles"][number]) == "hard" and not prop_build.worn_as_cloth(str(parts["names"][number])))
             or str(parts["names"][number]) in prop_build.RIGID_NAMES or str(parts["roles"][number]) == "hair"}
    part_of = np.zeros(len(rig["points"]), int)
    part_of[rig["faces"].ravel()] = np.repeat(rig["part_of"] if "part_of" in rig else parts["part_of"], 3)
    return ~np.isin(part_of, sorted(rigid))


def held_share(offsets, soft):
    """The share of the soft points within REACH of the body (the body gate's measure)."""
    return float((np.abs(offsets[soft]) <= REACH).mean()) if soft.any() else 1.0


def neighbour_mean(field, faces):
    """Each vertex's value averaged with its edge neighbours' (one smoothing pass over the body's mesh)."""
    edges = np.r_[faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]]
    edges = np.r_[edges, edges[:, ::-1]]
    total, count = field.copy(), np.ones(len(field))
    np.add.at(total, edges[:, 0], field[edges[:, 1]])
    np.add.at(count, edges[:, 0], 1)
    return total / count[:, None]


def suit_rounds(points, faces, look_points, look_faces):
    """The fitted body drawn onto the inside of a bulky suit, round by round: each round every body vertex steps along
    its own normal, SUIT_STEP of the way to INSIDE_MARGIN under its nearest look surface and, averaged in, to the look
    points nearest it (so a suit's ridge no body vertex is nearest to still pulls one out); the steps smoothed over
    the body's mesh and the whole move held to SUIT_MOST. Only along the normal, so a point keeps the body's weights
    of the place straight under it. Yields each round's drawn points and each vertex's move in metres."""
    import trimesh
    from scipy.spatial import cKDTree
    look = trimesh.Trimesh(look_points, look_faces, process=False)
    inside = look_points - look.vertex_normals * INSIDE_MARGIN
    move = np.zeros_like(points)
    for _ in range(SUIT_ROUNDS):
        now = points + move
        closest, _, triangle = trimesh.proximity.closest_point(look, now)
        reach = closest - look.face_normals[triangle] * INSIDE_MARGIN - now
        _, nearest = cKDTree(now).query(inside)
        pulls, count = np.zeros_like(now), np.ones(len(now))
        np.add.at(pulls, nearest, inside - now[nearest])
        np.add.at(count, nearest, 1)
        normals = trimesh.Trimesh(now, faces, process=False).vertex_normals
        along = np.einsum("ij,ij->i", (reach + pulls) / count[:, None], normals)
        move = move + neighbour_mean(SUIT_STEP * along[:, None] * normals, faces)
        size = np.linalg.norm(move, axis=1, keepdims=True)
        move *= np.minimum(1.0, SUIT_MOST / np.maximum(size, 1e-12))
        yield points + move, np.linalg.norm(move, axis=1)


def drawn_to_suit(shell, rig, soft):
    """The round of `suit_rounds` that holds the most soft points within REACH (the rounds can overshoot a suit's
    ridges, so the last is not taken blindly): its weights and offsets, and its measures."""
    import trimesh
    best = None
    for drawn, moved in suit_rounds(shell["points"], shell["faces"], rig["points"], rig["faces"]):
        weights, offsets = bound(trimesh.Trimesh(drawn, shell["faces"], process=False), shell["weights"],
                                 rig["points"])
        share = held_share(offsets, soft)
        if best is None or share > best[0]:
            best = (share, weights, offsets, moved)
    share, weights, offsets, moved = best
    return weights, offsets, {"held_share": round(share, 4), "moved_most_m": round(float(moved.max()), 4),
                              "moved_mean_m": round(float(moved.mean()), 4)}


def bind(fit_path, shell_path, out, record_path, parts_path=None):
    """The look's points bound to the fitted body (`bound`); where the fitted body holds under REACH_SHARE of the soft
    points within REACH (a bulky suit; parts.npz names which points are soft), bound instead to the body drawn onto
    the suit's inside (`drawn_to_suit`), its measures recorded under `suit`; the rig and the record."""
    import trimesh
    rig, shell = dict(np.load(fit_path)), np.load(shell_path)
    body = trimesh.Trimesh(shell["points"], shell["faces"], process=False)
    weights, offsets = bound(body, shell["weights"], rig["points"])
    suit = None
    if parts_path is not None:
        soft = soft_points(rig, np.load(parts_path))
        fitted_share = held_share(offsets, soft)
        if fitted_share < REACH_SHARE:
            weights, offsets, drawn = drawn_to_suit(shell, rig, soft)
            suit = {"fitted_held_share": round(fitted_share, 4), **drawn}
    rig["rswt_weights"], rig["weights"], rig["shell_offsets"] = rig["weights"], weights, offsets
    np.savez_compressed(out, **rig)
    faces_of = np.zeros(len(rig["points"]), int)
    faces_of[rig["faces"].ravel()] = np.repeat(rig["part_of"], 3)
    parts = {int(part): part_record(offsets, faces_of == part, rig) for part in np.unique(faces_of)}
    record = {"scale": float(shell["scale"]), "coefficients": shell["coefficients"].round(4).tolist(),
              "loss_start": float(shell["loss_start"]), "loss": float(shell["loss"]),
              "offset_most_m": round(float(np.abs(offsets).max()), 4),
              "offset_mean_m": round(float(np.abs(offsets).mean()), 4), "parts": parts,
              **({} if suit is None else {"suit": suit})}
    pathlib.Path(record_path).write_text(json.dumps(record, indent=1))
    return record


def main():
    step = sys.argv[1]
    if step == "fit":
        print("shell fit:", fit(pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3])), flush=True)
    elif step == "bind":
        found = bind(*map(pathlib.Path, sys.argv[2:7]))
        print(f"shell bind: offsets most {found['offset_most_m']} m, mean {found['offset_mean_m']} m", flush=True)
    else:
        raise SystemExit(f"prop_shell.py: no step {step!r} (fit, bind)")


if __name__ == "__main__":
    main()
