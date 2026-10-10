"""SOMA-X's skeleton placed inside a Pixal3D person and its skin weights moved onto the mesh: the prop route's rig
(owner, 2026-10-10: "soma is for the rig, not the mesh"). Plain CPU geometry on meshes on disk (numpy, scipy,
trimesh); no model runs, and no SOMA or SAM 3D Body surface is ever drawn or shapes the mesh.

    ~/.farm-factory-props/env/bin/python tools/characters/maker/prop_rig.py <mesh.glb> <rig.npz> <out folder>
        [--height 1.76]

`rig.npz` is prop_skeleton.py's (the mean skeleton's kept joints at their bind pose, the mean surface with its
weights). The steps:

1. The mesh is stood in the skeleton's frame: up +y, facing +z with +x its left (the way the toes point decides
   front), its soles on the floor, centred on its torso, scaled to `--height`.
2. Both bodies are measured the same way (`landmarks`): horizontal slices 1 cm apart, each cut into its separate
   pieces on a 1.5 cm grid; the crotch is where the two legs meet, the armpit where the arms leave the torso; each
   arm's and leg's axis is a line through its slices' centres, with its length and its median radius; the torso's
   centre, width and depth at every height. A mesh whose legs or arms never separate is refused.
3. Every joint is carried from the mean body into the mesh by those landmarks (`carried`): an arm or leg joint by
   its share along the limb's axis and its offset across it (scaled by the limbs' radii); a trunk joint by its height
   between the landmarks and its offset from the torso's centre (scaled by the torso's width and depth). The bind
   pose keeps the mean skeleton's rotations, each limb turned by the turn from the mean limb's axis to the mesh's, so
   the mesh is bound where it stands and Kimodo's clips (rotations against the parents) play unchanged.
4. The weights (Robust Skin Weights Transfer via Weight Inpainting, Abdrashitov, Raichstat, Monsen and Hill, SIGGRAPH
   Asia 2023 Technical Communications; reference code github.com/rin-23/RobustSkinWeightsTransferCode, MIT, Copyright
   (c) 2024 Rinat Abdrashitov; ported here with trimesh and scipy in place of libigl, whose bindings carry GPL-3.0):
   the mean surface is carried into the mesh the same way (`carried`, blended by each point's limb weights) as the
   source; a mesh vertex copies the source's weights where the closest source point lies within MATCH_DISTANCE and
   its normal within MATCH_DEGREES (an arm or leg vertex only from its own limb's source triangles); the rest is
   inpainted (the weights minimising the squared Laplacian energy with the matched ones fixed), then smoothed
   SMOOTH_STEPS times at SMOOTH_ALPHA within MATCH_DISTANCE of the unmatched ones. Loose cloth between the legs takes
   a blend of both instead of jumping to the nearer leg. A limb vertex keeps only its limb's joints and the joint above
   (the shoulder or the hips) at the end.

Writes rig.npz into the out folder (the joints' names, parents, fitted bind 4x4s and offsets against their parents,
the mesh's points and faces in the skeleton's frame, its weights, the carried mean surface, the frame's turn and
scale) and rig.json (the landmarks of both bodies, the share matched, and each limb's turn).
"""
import argparse
import json
import pathlib
import sys

import numpy as np
import trimesh
from scipy import ndimage, sparse
from scipy.sparse.csgraph import connected_components, dijkstra
from scipy.sparse.linalg import splu
from scipy.spatial import cKDTree

SLICE = 0.01
GRID = 0.015
MATCH_DISTANCE = 0.08
MATCH_DEGREES = 45.0
SMOOTH_STEPS = 10
SMOOTH_ALPHA = 0.2
SAMPLES = 200000
# How far a carried joint's offset across a limb or from the torso's centre may grow or shrink.
RATIO_RANGE = (0.5, 2.0)
SIDES = {"Left": 1.0, "Right": -1.0}
ARM = ("Arm", "ForeArm", "Hand")
LEG = ("Leg", "Shin", "Foot", "ToeBase", "ToeEnd")
# The hip joints sit in the pelvis, above where the legs part: they are placed by the trunk's map (their height
# between the crotch and the armpit), turned with their leg.
LIMB_ROOTS = ("LeftLeg", "RightLeg")


class RigError(ValueError):
    """A mesh the skeleton cannot be placed in."""


# --- the mesh in the skeleton's frame -------------------------------------------------------------------------------

def welded(mesh):
    """The mesh with coinciding vertices joined (Pixal3D repeats every vertex along its blocks' seams)."""
    rounded = np.round(mesh.vertices, 6)
    _, first, inverse = np.unique(rounded, axis=0, return_index=True, return_inverse=True)
    return trimesh.Trimesh(mesh.vertices[first], inverse.reshape(-1)[mesh.faces], process=False)


def stood(points, height):
    """The turn and scale that stand a person mesh in the skeleton's frame, as (turn 3x3, scale, shift): width along
    x, front +z (where the toes point), soles at y 0, centred over the torso, `height` tall."""
    extent = points.max(0) - points.min(0)
    turn = np.eye(3) if extent[0] >= extent[2] else np.array([[0.0, 0, 1], [0, 1, 0], [-1, 0, 0]])
    turned = points @ turn.T
    if toes_forward(turned) < 0:
        turn = np.diag([-1.0, 1.0, -1.0]) @ turn
        turned = points @ turn.T
    scale = height / float(turned[:, 1].max() - turned[:, 1].min())
    turned = turned * scale
    middle = turned[np.abs(turned[:, 1] - np.percentile(turned[:, 1], 60)) < 0.02]
    shift = np.array([-np.median(middle[:, 0]), -turned[:, 1].min(), -np.median(middle[:, 2])])
    return turn, scale, shift


def toes_forward(points):
    """The sign along z the feet point: the lowest 4 % of the body against the 10 to 20 % band above it."""
    low, high = points[:, 1].min(), points[:, 1].max()
    share = (points[:, 1] - low) / (high - low)
    return float(np.sign(points[share < 0.04, 2].mean() - points[(share > 0.1) & (share < 0.2), 2].mean()) or 1.0)


# --- landmarks ------------------------------------------------------------------------------------------------------

def pieces(points):
    """A slice's separate pieces on a GRID raster (8-connected after one cell of growth): each as (its points' indices
    into `points`, centre x, centre z, x low, x high)."""
    cells = np.floor((points[:, [0, 2]] - points[:, [0, 2]].min(0)) / GRID).astype(int) + 1
    occupied = np.zeros(cells.max(0) + 2, bool)
    occupied[cells[:, 0], cells[:, 1]] = True
    grown = ndimage.binary_dilation(occupied, structure=np.ones((3, 3)))
    labelled, _ = ndimage.label(grown, structure=np.ones((3, 3)))
    label = labelled[cells[:, 0], cells[:, 1]]
    found = []
    for number in np.unique(label):
        mine = np.flatnonzero(label == number)
        found.append((mine, float(points[mine, 0].mean()), float(points[mine, 2].mean()),
                      float(points[mine, 0].min()), float(points[mine, 0].max())))
    return found


def slices(points):
    """Every slice's height and pieces, from the floor up."""
    heights = np.arange(points[:, 1].min() + SLICE, points[:, 1].max(), SLICE)
    found = []
    for height in heights:
        index = np.flatnonzero(np.abs(points[:, 1] - height) < SLICE / 2)
        if len(index) >= 3:
            found.append((float(height), [(index[mine], *rest) for mine, *rest in pieces(points[index])]))
    return found


def legs_of(cut, height):
    """The slice's two legs (the largest piece on each side, near the middle), or None."""
    near = [piece for piece in cut if abs(piece[1]) < 0.2 * height]
    left = [piece for piece in near if piece[1] > 0]
    right = [piece for piece in near if piece[1] < 0]
    if not left or not right:
        return None
    return max(left, key=lambda piece: len(piece[0])), max(right, key=lambda piece: len(piece[0]))


def arms_of(cut):
    """The slice's torso (the piece over x 0) and an arm on each side of it, or None."""
    torso = [piece for piece in cut if piece[3] <= 0.0 <= piece[4]]
    if len(torso) != 1:
        return None
    torso = torso[0]
    left = [piece for piece in cut if piece[3] > torso[4]]
    right = [piece for piece in cut if piece[4] < torso[3]]
    if not left or not right:
        return None
    return torso, max(left, key=lambda piece: len(piece[0])), max(right, key=lambda piece: len(piece[0]))


def crotch_of(cuts, height):
    """The highest slice of the run of slices from a quarter of the height up whose legs stand apart."""
    found = None
    for level, cut in cuts:
        if level < 0.25 * height:
            continue
        if legs_of(cut, height) is None:
            break
        found = level
    if found is None:
        raise RigError("the legs never stand apart: refused before the split")
    return found


def armpit_of(cuts, crotch, height):
    """The highest slice under 85 % of the height whose arms stand apart from the torso."""
    for level, cut in reversed(cuts):
        if crotch < level < 0.85 * height and arms_of(cut) is not None:
            return level
    raise RigError("the arms never stand apart from the torso: refused before the split")


def axis_through(centres):
    """A line through points: its middle and its unit direction (largest spread), pointing down."""
    middle = centres.mean(0)
    direction = np.linalg.svd(centres - middle)[2][0]
    return middle, direction if direction[1] < 0 else -direction


def limb(points, centres, members, start_height):
    """A limb's axis from its slices' centres: its point at `start_height`, its direction (down), its length to the
    farthest of its points along it and its median radius."""
    middle, direction = axis_through(np.array(centres))
    start = middle + direction * (start_height - middle[1]) / direction[1]
    offsets = points[members] - start
    along = offsets @ direction
    across = np.linalg.norm(offsets - along[:, None] * direction, axis=1)
    return {"start": start, "direction": direction, "length": float(along.max()), "radius": float(np.median(across))}


def limb_slices(cuts, low, high, pick):
    """Each slice's piece `pick` chooses between heights `low` and `high`: their centres and points."""
    centres, members = [], []
    for level, cut in cuts:
        if low <= level <= high:
            piece = pick(cut)
            if piece is not None:
                centres.append((piece[1], level, piece[2]))
                members.append(piece[0])
    return centres, np.concatenate(members) if members else np.zeros(0, int)


def torso_profile(points, cuts, crotch):
    """The torso's centre x and z, width and depth at each slice from the crotch up (the piece over x 0)."""
    rows = []
    for level, cut in cuts:
        if level < crotch:
            continue
        over = [piece for piece in cut if piece[3] <= 0.0 <= piece[4]]
        if over:
            mine = points[over[0][0]]
            rows.append((level, over[0][1], over[0][2], np.ptp(mine[:, 0]), np.ptp(mine[:, 2])))
    return np.array(rows)


def landmarks(points):
    """The body's landmarks (step 2 of the header), from surface points in the skeleton's frame."""
    height = float(points[:, 1].max())
    cuts = slices(points)
    crotch = crotch_of(cuts, height)
    armpit = armpit_of(cuts, crotch, height)
    found = {"height": height, "crotch": crotch, "armpit": armpit,
             "torso": torso_profile(points, cuts, crotch), "samples": points,
             "limbs": limb_labels(points, cuts, crotch, armpit, height)}
    for side, sign in SIDES.items():
        index = 0 if sign > 0 else 1
        centres, members = limb_slices(cuts, 0.12 * height, crotch,
                                       lambda cut, index=index: (legs_of(cut, height) or (None, None))[index])
        found[side + "Leg"] = limb(points, centres, members, crotch)
        centres, members = limb_slices(cuts, 0.0, armpit,
                                       lambda cut, index=index: (arms_of(cut) or (None, None, None))[1 + index])
        found[side + "Arm"] = limb(points, centres, members, armpit)
    return found


# --- carrying the mean body into the mesh ---------------------------------------------------------------------------

def turn_between(first, second):
    """The rotation taking unit vector `first` onto `second`."""
    cross = np.cross(first, second)
    sine, cosine = np.linalg.norm(cross), float(first @ second)
    if sine < 1e-9:
        return np.eye(3)
    axis = cross / sine
    skew = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    return np.eye(3) + sine * skew + (1 - cosine) * skew @ skew


def ratio(new, old):
    return float(np.clip(new / old, *RATIO_RANGE))


def carried_on_limb(points, mean, fit):
    """Points carried along a limb: their share along the mean limb's axis onto the mesh limb's, their offset across
    it turned with the limb and scaled by the radii."""
    offsets = points - mean["start"]
    along = offsets @ mean["direction"]
    across = offsets - along[:, None] * mean["direction"]
    turn = turn_between(mean["direction"], fit["direction"])
    share = along / mean["length"]
    return (fit["start"] + (share * fit["length"])[:, None] * fit["direction"]
            + across @ turn.T * ratio(fit["radius"], mean["radius"]))


def height_knots(body):
    return np.array([0.0, body["crotch"], body["armpit"], body["height"]])


def carried_on_trunk(points, mean, fit):
    """Points carried on the trunk: their height between the landmarks, their offset from the torso's centre scaled
    by its width and depth there."""
    height = np.interp(points[:, 1], height_knots(mean), height_knots(fit))
    carried = np.empty_like(points)
    carried[:, 1] = height
    for axis, (centre_column, size_column) in ((0, (1, 3)), (2, (2, 4))):
        old_centre = np.interp(points[:, 1], mean["torso"][:, 0], mean["torso"][:, centre_column])
        new_centre = np.interp(height, fit["torso"][:, 0], fit["torso"][:, centre_column])
        old_size = np.interp(points[:, 1], mean["torso"][:, 0], mean["torso"][:, size_column])
        new_size = np.interp(height, fit["torso"][:, 0], fit["torso"][:, size_column])
        scale = np.clip(new_size / np.maximum(old_size, 1e-6), *RATIO_RANGE)
        carried[:, axis] = new_centre + (points[:, axis] - old_centre) * scale
    return carried


def chains(names):
    """Each joint's chain: "trunk", or a limb's landmark name ("LeftArm", "RightLeg", ...)."""
    found = []
    for name in names:
        chain = "trunk"
        for side in SIDES:
            if name.startswith(side) and name[len(side):] in ARM:
                chain = side + "Arm"
            if name.startswith(side) and name[len(side):] in LEG:
                chain = side + "Leg"
        found.append(chain)
    return found


def carried(points, chain_shares, chain_names, mean, fit):
    """Points carried by each chain's map, blended by their shares of each chain (rows summing to one)."""
    out = np.zeros_like(points)
    for column, chain in enumerate(chain_names):
        mine = chain_shares[:, column] > 1e-6
        if not mine.any():
            continue
        moved = (carried_on_trunk(points[mine], mean, fit) if chain == "trunk"
                 else carried_on_limb(points[mine], mean[chain], fit[chain]))
        out[mine] += chain_shares[mine, column, None] * moved
    return out


def chain_shares(weights, joint_chains, chain_names):
    """Each point's share of each chain, from its weights."""
    shares = np.zeros((len(weights), len(chain_names)))
    for joint, chain in enumerate(joint_chains):
        shares[:, chain_names.index(chain)] += weights[:, joint]
    return shares / np.maximum(shares.sum(1, keepdims=True), 1e-12)


def fitted_bind(bind, names, parents, mean, fit):
    """The fitted skeleton: every joint carried by its own chain, each limb's rotations turned with its axis. The
    bind 4x4s and every joint's offset against its parent's bind frame."""
    joint_chains = chains(names)
    chain_names = sorted(set(joint_chains))
    placed_by = ["trunk" if name in LIMB_ROOTS else chain for name, chain in zip(names, joint_chains)]
    shares = np.zeros((len(names), len(chain_names)))
    shares[np.arange(len(names)), [chain_names.index(chain) for chain in placed_by]] = 1.0
    places = carried(bind[:, :3, 3], shares, chain_names, mean, fit)
    out = bind.copy()
    out[:, :3, 3] = places
    for joint, chain in enumerate(joint_chains):
        if chain != "trunk":
            out[joint, :3, :3] = turn_between(mean[chain]["direction"], fit[chain]["direction"]) @ bind[joint, :3, :3]
    offsets = np.array([places[joint] if parents[joint] < 0
                        else out[parents[joint], :3, :3].T @ (places[joint] - places[parents[joint]])
                        for joint in range(len(names))])
    return out, offsets


# --- the weights (RSWT) ---------------------------------------------------------------------------------------------

def cotangent_laplacian(points, faces):
    """The cotangent Laplacian (negative semi-definite, as libigl's cotmatrix) and the lumped mass (a third of each
    triangle's area to each corner)."""
    corners = points[faces]
    rows, columns, values = [], [], []
    for corner in range(3):
        first, second = (corner + 1) % 3, (corner + 2) % 3
        edge_a = corners[:, first] - corners[:, corner]
        edge_b = corners[:, second] - corners[:, corner]
        cross = np.linalg.norm(np.cross(edge_a, edge_b), axis=1)
        cotangent = (edge_a * edge_b).sum(1) / np.maximum(cross, 1e-12)
        half = np.clip(cotangent, -1e3, 1e3) / 2
        rows += [faces[:, first], faces[:, second]]
        columns += [faces[:, second], faces[:, first]]
        values += [half, half]
    count = len(points)
    off = sparse.csr_matrix((np.concatenate(values), (np.concatenate(rows), np.concatenate(columns))),
                            shape=(count, count))
    laplacian = off - sparse.diags(np.asarray(off.sum(1)).ravel())
    area = np.linalg.norm(np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0]), axis=1) / 2
    mass = np.zeros(count)
    for corner in range(3):
        np.add.at(mass, faces[:, corner], area / 3)
    return laplacian.tocsr(), np.maximum(mass, 1e-12)


def closest_on(source, points):
    """The closest place on `source` to each point: its triangle, its barycentric shares and its squared distance."""
    nearest, distance, triangle = trimesh.proximity.closest_point(source, points)
    shares = trimesh.triangles.points_to_barycentric(source.triangles[triangle], nearest)
    shares = np.clip(shares, 0.0, None)
    return triangle, shares / shares.sum(1, keepdims=True), distance ** 2


def matched(source, source_weights, points, normals, distance, degrees):
    """RSWT's matches: each point's weights interpolated at its closest source place, and whether that place lies
    within `distance` with its normal within `degrees` of the point's."""
    triangle, shares, squared = closest_on(source, points)
    corners = source.faces[triangle]
    weights = np.einsum("pc,pcj->pj", shares, source_weights[corners])
    source_normals = np.einsum("pc,pcd->pd", shares, source.vertex_normals[corners])
    source_normals /= np.maximum(np.linalg.norm(source_normals, axis=1, keepdims=True), 1e-12)
    cosine = np.clip((source_normals * normals).sum(1), -1.0, 1.0)
    good = (squared <= distance ** 2) & (np.degrees(np.arccos(cosine)) <= degrees)
    return weights, good


def inpainted(points, faces, weights, known):
    """RSWT's inpainting: the weights of the unknown vertices minimising trace(W^T Q W), Q = -L + L M^-1 L, the known
    ones fixed. A piece of the mesh with no known vertex keeps its copied weights."""
    laplacian, mass = cotangent_laplacian(points, faces)
    laplacian = 2 * laplacian
    system = (-laplacian + laplacian @ sparse.diags(1 / mass) @ laplacian).tocsc()
    count, label = connected_components(abs(laplacian) > 0, directed=False)
    solvable = ~known & np.isin(label, np.unique(label[known]))
    unknown = np.flatnonzero(solvable)
    fixed = np.flatnonzero(known)
    out = weights.copy()
    if len(unknown):
        inner = system[unknown][:, unknown] + sparse.identity(len(unknown)) * 1e-10
        out[unknown] = splu(inner.tocsc()).solve(-(system[unknown][:, fixed] @ weights[fixed]))
    return out


def edge_graph(points, faces):
    """The mesh's edges as a symmetric sparse graph weighted by length."""
    edges = np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
    lengths = np.linalg.norm(points[edges[:, 0]] - points[edges[:, 1]], axis=1)
    graph = sparse.csr_matrix((lengths, (edges[:, 0], edges[:, 1])), shape=(len(points),) * 2)
    return graph.maximum(graph.T)


def smoothed(points, faces, weights, known, distance):
    """RSWT's smoothing: SMOOTH_STEPS rounds of each vertex moving SMOOTH_ALPHA towards its neighbours' mean, on the
    unknown vertices and every vertex within `distance` of one over the surface's edges."""
    graph = edge_graph(points, faces)
    reach = dijkstra(graph, indices=np.flatnonzero(~known), limit=distance, min_only=True) \
        if (~known).any() else np.full(len(points), np.inf)
    smooth = np.isfinite(reach)
    neighbours = (graph > 0).astype(float)
    neighbours = sparse.diags(1 / np.maximum(np.asarray(neighbours.sum(1)).ravel(), 1)) @ neighbours
    out = weights.copy()
    for _ in range(SMOOTH_STEPS):
        mean = neighbours @ out
        out[smooth] = (1 - SMOOTH_ALPHA) * out[smooth] + SMOOTH_ALPHA * mean[smooth]
    return out, smooth


def limb_labels(points, cuts, crotch, armpit, height):
    """Each surface point's limb ("LeftArm", ..., or "" for the trunk) from the slices' pieces: under the crotch the
    two legs and any piece beyond them (a hand hanging low), between the crotch and the armpit the pieces either side
    of the torso."""
    found = np.full(len(points), "", dtype=object)
    for level, cut in cuts:
        if level < crotch:
            legs = legs_of(cut, height)
            if legs is None:
                continue
            for side, leg in zip(SIDES, legs):
                found[leg[0]] = side + "Leg"
            for piece in cut:
                if piece[3] > legs[0][4]:
                    found[piece[0]] = "LeftArm"
                elif piece[4] < legs[1][3]:
                    found[piece[0]] = "RightArm"
        elif level <= armpit:
            parts = arms_of(cut)
            if parts is None:
                continue
            for piece in cut:
                if piece[3] > parts[0][4]:
                    found[piece[0]] = "LeftArm"
                elif piece[4] < parts[0][3]:
                    found[piece[0]] = "RightArm"
    return found


def limb_of_vertices(vertices, samples, labels, votes=8):
    """Each vertex's limb: the most common among its `votes` nearest labelled surface samples."""
    _, nearest = cKDTree(samples).query(vertices, k=votes)
    names, coded = np.unique(labels, return_inverse=True)
    coded = coded.reshape(labels.shape)[nearest]
    counts = np.stack([(coded == number).sum(1) for number in range(len(names))], axis=1)
    return names[counts.argmax(1)]


def allowed_joints(names, limb_name):
    """The joints a limb's vertex may hang from: its own chain and the joint it hangs from (shoulder or hips)."""
    side = limb_name[:-3]
    chain = ARM if limb_name.endswith("Arm") else LEG
    above = "Shoulder" if limb_name.endswith("Arm") else None
    allowed = [side + joint for joint in chain] + ([side + above] if above else ["Hips"])
    return np.isin(names, allowed)


def transferred(source, source_weights, mesh, names, fit, distance=MATCH_DISTANCE, degrees=MATCH_DEGREES):
    """RSWT onto the mesh with each limb's vertices matched only on its limb's source triangles: (weights, the
    share matched, the share smoothed)."""
    points, faces = mesh.vertices, mesh.faces
    limbs = limb_of_vertices(points, fit["samples"], fit["limbs"])
    weights, good = matched(source, source_weights, points, mesh.vertex_normals, distance, degrees)
    owner = source_weights.argmax(1)
    for limb_name in [name for name in np.unique(limbs) if name]:
        mine = limbs == limb_name
        keep = np.isin(owner, np.flatnonzero(allowed_joints(names, limb_name)))
        piece = trimesh.Trimesh(source.vertices, source.faces[keep[source.faces].all(1)], process=False)
        weights[mine], good[mine] = matched(piece, source_weights, points[mine], mesh.vertex_normals[mine], distance,
                                            degrees)
    filled = inpainted(points, faces, weights, good)
    filled, smooth = smoothed(points, faces, filled, good, distance)
    filled = np.clip(filled, 0.0, None)
    for limb_name in [name for name in np.unique(limbs) if name]:
        filled[np.ix_(limbs == limb_name, ~allowed_joints(names, limb_name))] = 0.0
    lost = filled.sum(1) <= 1e-9
    filled[lost] = weights[lost]
    return filled / filled.sum(1, keepdims=True), float(good.mean()), float(smooth.mean())


# --- the whole rig --------------------------------------------------------------------------------------------------

def sampled(mesh, count=SAMPLES, seed=0):
    """Surface points, seeded (trimesh ignores numpy's global seed)."""
    return trimesh.sample.sample_surface(mesh, count, seed=seed)[0]


def plain(found):
    """Landmarks as JSON."""
    return {key: (value.tolist() if isinstance(value, np.ndarray) else
                  {inner: (item.tolist() if isinstance(item, np.ndarray) else item) for inner, item in value.items()}
                  if isinstance(value, dict) else value)
            for key, value in found.items() if key not in ("torso", "samples", "limbs")}


def rig(mesh_path, rig_path, out, height):
    """The fitted skeleton and the mesh's weights into `out` (rig.npz, rig.json); the record."""
    mean_rig = np.load(rig_path)
    names, parents, bind = list(mean_rig["names"]), mean_rig["parents"], mean_rig["bind"]
    source = trimesh.Trimesh(mean_rig["points"], mean_rig["faces"], process=False)
    mesh = welded(trimesh.load(mesh_path, force="mesh", process=False))
    turn, scale, shift = stood(mesh.vertices, height)
    mesh = trimesh.Trimesh(mesh.vertices @ turn.T * scale + shift, mesh.faces, process=False)
    if mesh.volume < 0:
        mesh.invert()
    mean = landmarks(sampled(source))
    fit = landmarks(sampled(mesh))
    fitted, offsets = fitted_bind(bind, names, parents, mean, fit)
    joint_chains = chains(names)
    chain_names = sorted(set(joint_chains))
    shares = chain_shares(mean_rig["weights"], joint_chains, chain_names)
    carried_source = trimesh.Trimesh(carried(source.vertices, shares, chain_names, mean, fit), source.faces,
                                     process=False)
    weights, matched_share, smoothed_share = transferred(carried_source, mean_rig["weights"], mesh, np.array(names),
                                                         fit)
    out.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out / "rig.npz", names=np.array(names), parents=parents, bind=fitted, offsets=offsets,
                        mean_bind=bind, points=mesh.vertices, faces=mesh.faces, weights=weights,
                        source_points=carried_source.vertices, source_faces=source.faces, turn=turn, scale=scale,
                        shift=shift)
    record = {"mesh": str(mesh_path), "height": height, "scale": scale, "vertices": len(mesh.vertices),
              "matched_share": round(matched_share, 4), "smoothed_share": round(smoothed_share, 4),
              "mean": plain(mean), "fit": plain(fit),
              "limb_turn_degrees": {chain: round(float(np.degrees(np.arccos(np.clip(
                  mean[chain]["direction"] @ fit[chain]["direction"], -1, 1)))), 2)
                  for chain in chain_names if chain != "trunk"}}
    (out / "rig.json").write_text(json.dumps(record, indent=1))
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("mesh", type=pathlib.Path)
    parser.add_argument("rig", type=pathlib.Path)
    parser.add_argument("out", type=pathlib.Path)
    parser.add_argument("--height", type=float, help="the person's height in metres (the mean body's by default)")
    options = parser.parse_args()
    height = options.height or float(np.ptp(np.load(options.rig)["points"][:, 1]))
    record = rig(options.mesh, options.rig, options.out, height)
    print(f"rig: {record['vertices']} vertices, {record['matched_share']:.0%} matched, limb turns "
          f"{record['limb_turn_degrees']}; {options.out / 'rig.json'}", flush=True)


if __name__ == "__main__":
    sys.exit(main())
