"""A still model rigged as a player model (#128, owner 2026-11-18, of the paper's TRELLIS.2 astronaut: "why dont we use
these models for the astraunauts, that one looks way better"): a picture-made mesh with no skeleton put on a dressed
body's own skeleton, so it plays every clip and sim-body motion that body plays. Plain CPU geometry (numpy, scipy,
trimesh); no model runs.

    .venv/bin/python tools/characters/still_rig/still_rig.py <still.glb> <dressed body.glb> <clips rig.npz>
        <palette.json> <out folder> [--faces 60000]

The steps:

1. The skeleton is the dressed body's (people-dress-<look>'s body.glb): its joints, bind, rest and clips are kept as
   they are, so cast/driven, the walker peel and lay_walkers play it unchanged.
2. The SOMA surface (people-clips-made's rig.npz, the mean body and its weights) is moved onto that bind by its own
   weights (prop_rig.skinned_source): the body the still is fitted to and its weights' source, never drawn.
3. The still is stood (prop_rig.stood: up +y, facing +z, soles on the floor), centred over the body's hips, and sized
   to the height at which the least of the body's trunk, head, thighs and shoulders stands outside it
   (`fitted_height`); the still is its outer surface alone (`outer`: TRELLIS.2's shell has an inner layer facing the
   hollow): scale and align only, its geometry otherwise its own. It is thinned to about `--faces`
   triangles first (prop_rig.decimated, its borders kept).
4. Its parts (`parts_of`): the helmet (every face within HELMET_REACH of the head's middle above the neck), the visor
   (the helmet's dark faces in front, its own baked colour read only to find it, their largest connected piece alone:
   a dark seam at the helmet's rim is helmet), the backpack (behind the chest, more
   than PACK_OFF off the body) and the suit (the rest), each face's part settled to its neighbours'. Every open loop
   the outer cut left (the armpits behind the shoulders, the boots' tops and soles, where no sight line reached:
   black tears in the film) is closed by a fan from its middle (`closed`) after the fit (whose inside test the fans,
   reaching across the hollow, would mislead: 21% of the skin outside against 4%).
5. The weights: Robust Skin Weights Transfer from the SOMA surface (prop_rig.transferred: closest-surface matches
   within its distance and angle, each limb only from its own limb, the rest inpainted and smoothed), then the helmet
   and visor rigid on the head and the backpack rigid on the chest (`rigid`), the suit next to them eased onto their
   joint by its distance over the surface (`rigid`), so nothing tears where a hard part meets the cloth. Last, every
   cloth point within CLIFF_REACH of an edge across which the weights change faster than CLIFF (the crotch, where each
   leg's points may hang only from their own leg, and the shoulders' rims) is smoothed towards its neighbours
   (`eased_cliffs`), so a stride bends the cloth over a few centimetres instead of one edge (walking's worst edge 11.9
   times its length before, 9.1 after; its 99.9th percentile 3.7 and 2.5).
6. Every part's finish is a library surface (the root rule): the palette variant it names (`FINISHES`) in its own
   token or the one `TOKENS` names, a recipe entry's address and its spec's colour, roughness and metal on a flat material named for the variant; the still's
   baked texture is dropped.
7. The glTF (`written`): the dressed body's skeleton and clips (its corrective morph keys left out: the still has no
   targets), the still as its `work` node and a far body of FAR_TRIANGLES; `stretch` measures the longest edge's
   growth on every frame of every clip.

Writes <out>/body.glb, <out>/rig.json (the fit, the parts' triangles, the matched share, each clip's stretch).
"""
import argparse
import json
import pathlib
import sys

import numpy as np
import trimesh
from scipy.sparse.csgraph import connected_components, dijkstra
from scipy.spatial import cKDTree

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "maker"))
sys.path.insert(0, str(HERE.parent / "people"))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parents[1] / "props" / "library"))

import glb  # noqa: E402  (people/glb.py, the glTF writer)
import prop_rig  # noqa: E402
import skel_usd  # noqa: E402

FACES = 60000
FAR_TRIANGLES = 1220  # prop_far.FAR_TRIANGLES
JOINTS_A_VERTEX = 4
EDGE_LEAST = 0.002  # metres: a shorter edge is left out of the stretch
SIGHTS = 200  # directions the outer surface is looked for from (`seen_faces`: 100 to 600 found 34 to 35% of the suit)
SIGHT_SPACING = 0.0015  # the rays' spacing, in the still's own units (TRELLIS.2's are its height over one)
CLOSE_ROUNDS = 3  # rounds an unseen face between seen ones joins them
# The joints whose skin the fit holds inside the still (trunk_skin).
FIT_IN = ("Hips", "Spine1", "Spine2", "Head", "LeftLeg", "RightLeg", "LeftShoulder", "RightShoulder", "LeftArm",
          "RightArm")
HEIGHTS = np.arange(1.70, 1.951, 0.01)  # the heights the fit tries, metres
HELMET_REACH = 0.25  # metres from the head's middle (between Head and HeadEnd) a helmet face lies within (the
# suit's visor reaches 0.24 at its chin, the collar 0.26: at 0.21 the visor's lower half was cut off as suit cloth)
VISOR_DARK = 0.5  # a helmet face darker than this (its baked colour's mean; the suit's visor 0.43 to 0.47, its shell
# 0.6 and over) and VISOR_FRONT in front of the head's middle is the visor
VISOR_FRONT = 0.04
PACK_OFF = 0.05  # metres off the body behind the chest a backpack face stands at least
PARTS = ("suit", "helmet", "visor", "backpack")
RIGID = {"helmet": "Head", "visor": "Head", "backpack": "Chest"}
SEAM = 0.06  # metres either side of where two hard parts on different joints meet over which they share both
EASE_HOLD, EASE_REACH = 0.01, 0.08  # metres from a hard part over which the suit is eased onto its joint (`rigid`)
# Each part's palette variant (the place's surface library, scene_library.py) and the recipe entry it is drawn from.
FINISHES = {"suit": "suit_fabric", "helmet": "white_hard_case", "visor": "helmet_visor",
            "backpack": "suit_backpack_shell"}
# The palette token a part's variant is laid in where it is not the variant's own: the suit and helmet the palette's
# neutral white (case-white's warm cream read as skin under a Mars sun, as the paper's suit is a plain white), the
# visor its darkest (steel-dark's mid grey read as a grey band, the paper's visor dark glass).
TOKENS = {"suit": "label-white", "helmet": "label-white", "visor": "cable-black"}
CLIFF = 20.0  # per metre: the weights' summed difference across an edge (0 to 2) over its length above which the
# cloth round it is eased (a whole change of joint over 10 cm; the shoulder's 0.36 across 2.4 mm tore 11.8 times)
CLIFF_REACH = 0.05  # metres over the surface from such an edge the easing reaches
CLIFF_ROUNDS, CLIFF_ALPHA = 200, 0.5  # its rounds (about 3 cm of spread on 3 mm edges), and how far towards its
# neighbours' mean a point moves each round
OUTFIT = "work"  # the dressed body's own outfit node, which skel_usd shows (DEFAULT_WORN)


class StillError(ValueError):
    """A still the skeleton cannot be fitted in, or a dressed body that is not one."""


# --- the dressed body's skeleton ------------------------------------------------------------------------------------

def skeleton_of(dressed):
    """The dressed body's glTF (document, blob) and its skin: joint names in skin order, bind 4x4s (the mesh's frame,
    facing +z), parents."""
    document, blob = skel_usd.read_glb(dressed)
    if len(document.get("skins", [])) != 1:
        raise StillError(f"{dressed}: one skin expected")
    joints = document["skins"][0]["joints"]
    names = [document["nodes"][joint]["name"] for joint in joints]
    inverse = skel_usd.accessor(document, blob, document["skins"][0]["inverseBindMatrices"]).reshape(-1, 4, 4)
    bind = np.linalg.inv(inverse.transpose(0, 2, 1).astype(float))
    parent = {child: number for number, node in enumerate(document["nodes"]) for child in node.get("children", [])}
    parents = np.array([joints.index(parent[joint]) if parent.get(joint) in joints else -1 for joint in joints])
    return document, blob, names, bind, parents


def soma_on(rig, names, bind):
    """The mean SOMA surface moved onto `bind` by its own weights, its weights in the skin's joint order."""
    order = [list(map(str, rig["names"])).index(name) for name in names]
    weights = np.asarray(rig["weights"], float)[:, order]
    mean_bind = np.asarray(rig["bind"], float)[order]
    points = prop_rig.skinned_source(np.asarray(rig["points"], float), weights, mean_bind, bind)
    return trimesh.Trimesh(points, np.asarray(rig["faces"]), process=False), weights


# --- the still, stood and fitted ------------------------------------------------------------------------------------

def still_of(path):
    """The still's outer surface welded (`outer`), and each vertex's baked colour (its base colour map at its texture
    place), used only to find the visor."""
    mesh = trimesh.load(path, force="mesh", process=False)
    uv, picture = mesh.visual.uv, np.asarray(mesh.visual.material.baseColorTexture.convert("RGB"), float) / 255.0
    rows, columns = picture.shape[:2]
    across = np.clip(np.rint(uv[:, 0] * (columns - 1)).astype(int), 0, columns - 1)
    down = np.clip(np.rint((1 - uv[:, 1]) * (rows - 1)).astype(int), 0, rows - 1)
    colours = picture[down, across]
    welded = prop_rig.welded(trimesh.Trimesh(mesh.vertices, mesh.faces, process=False))
    welded = outer(welded)
    _, nearest = cKDTree(mesh.vertices).query(welded.vertices)
    return welded, colours[nearest]


def directions(count):
    """`count` directions spread evenly over the sphere (a Fibonacci lattice)."""
    steps = np.arange(count) + 0.5
    down, round_ = np.arccos(1 - 2 * steps / count), np.pi * (1 + 5 ** 0.5) * steps
    return np.c_[np.cos(round_) * np.sin(down), np.cos(down), np.sin(round_) * np.sin(down)]


def seen_faces(mesh, count=SIGHTS, spacing=SIGHT_SPACING):
    """Each face seen first by some ray of a parallel sheet `spacing` apart from each of `count` directions."""
    seen = np.zeros(len(mesh.faces), bool)
    centre, reach = mesh.bounds.mean(0), np.linalg.norm(mesh.extents) / 2 + spacing
    grid = np.arange(-reach, reach, spacing)
    across, along = [values.ravel() for values in np.meshgrid(grid, grid)]
    for towards in directions(count):
        side = np.cross(towards, [0.0, 1.0, 0.0] if abs(towards[1]) < 0.9 else [1.0, 0.0, 0.0])
        side /= np.linalg.norm(side)
        other = np.cross(towards, side)
        starts = centre - towards * reach * 1.5 + across[:, None] * side + along[:, None] * other
        first = mesh.ray.intersects_first(starts, np.repeat(towards[None], len(starts), 0))
        seen[first[first >= 0]] = True
    return seen


def outer(mesh, rounds=CLOSE_ROUNDS):
    """The still's outer surface: TRELLIS.2 makes a thin-walled shell, an outer layer facing out and an inner one
    facing the hollow 1 to 2 cm in (the suit's: 34% of its faces seen from outside, every one facing its ray), and
    the inner layer's normals face the body, so neither the fit's inside test nor the weights' normal match can read
    it. The faces seen from outside (seen_faces) are kept, and a face unseen between kept ones (two of its three
    neighbours kept, `rounds` times) joins them, so a crevice the rays missed is no hole."""
    kept = seen_faces(mesh)
    pairs = mesh.face_adjacency
    for _ in range(rounds):
        around = np.zeros(len(kept), int)
        np.add.at(around, pairs[:, 0], kept[pairs[:, 1]])
        np.add.at(around, pairs[:, 1], kept[pairs[:, 0]])
        kept = kept | (around >= 2)
    used, renumbered = np.unique(mesh.faces[kept], return_inverse=True)
    return trimesh.Trimesh(mesh.vertices[used], renumbered.reshape(-1, 3), process=False)


def thinned(mesh, faces):
    """The still thinned to about `faces` triangles (fast-simplification's quadric thinning, MIT) and welded: its outer
    surface's open seams leave prop_rig.decimated's border-keeping thinning folding at every try (161k triangles
    kept whole)."""
    import fast_simplification
    points, triangles = fast_simplification.simplify(mesh.vertices, mesh.faces,
                                                     target_reduction=max(0.0, 1.0 - faces / len(mesh.faces)))
    return prop_rig.welded(trimesh.Trimesh(points, triangles, process=False))


def closed(mesh):
    """The still with every open loop closed by a fan of triangles from the loop's middle, each turned as the face it
    borders (a border edge a to b gets the face b, a, middle): the outer cut's holes where no sight line reached."""
    edges = np.concatenate([mesh.faces[:, [0, 1]], mesh.faces[:, [1, 2]], mesh.faces[:, [2, 0]]])
    keys = edges[:, 0].astype(np.int64) * len(mesh.vertices) + edges[:, 1]
    back = edges[:, 1].astype(np.int64) * len(mesh.vertices) + edges[:, 0]
    border = edges[~np.isin(keys, back)]
    if not len(border):
        return mesh
    count = len(mesh.vertices)
    graph = sparse_graph(border, count)
    _, loop_of = connected_components(graph, directed=False)
    loops, numbered = np.unique(loop_of[border[:, 0]], return_inverse=True)
    middles = np.array([mesh.vertices[np.unique(border[numbered == number])].mean(0) for number in range(len(loops))])
    fan = np.c_[border[:, 1], border[:, 0], count + numbered]
    return trimesh.Trimesh(np.r_[mesh.vertices, middles], np.r_[mesh.faces, fan], process=False)


def open_edges(mesh):
    """How many of the mesh's edges border one face only."""
    edges = np.sort(np.concatenate([mesh.faces[:, [0, 1]], mesh.faces[:, [1, 2]], mesh.faces[:, [2, 0]]]), 1)
    return int((np.unique(edges, axis=0, return_counts=True)[1] == 1).sum())


def sparse_graph(edges, count):
    """`edges` as a symmetric unweighted sparse graph over `count` points."""
    from scipy import sparse
    graph = sparse.csr_matrix((np.ones(len(edges)), (edges[:, 0], edges[:, 1])), shape=(count, count))
    return graph.maximum(graph.T)


def outside_share(mesh, points):
    """The share of `points` outside `mesh` by its closest face's outward normal."""
    nearest, _, triangle = trimesh.proximity.closest_point(mesh, points)
    return float((np.einsum("ij,ij->i", points - nearest, mesh.face_normals[triangle]) > 0).mean())


def stood_at(mesh, height, body, names, bind):
    """The still stood `height` tall (prop_rig.stood), its legs' middle over the body's (x and z half way down the
    thighs, where neither the backpack nor the hands reach)."""
    turn, scale, shift = prop_rig.stood(mesh.vertices, height)
    points = mesh.vertices @ turn.T * scale + shift
    thigh = (bind[names.index("LeftLeg"), 1, 3] + bind[names.index("LeftShin"), 1, 3]) / 2
    level = np.abs(points[:, 1] - thigh) < 0.03
    body_level = np.abs(body.vertices[:, 1] - thigh) < 0.03
    centre = (points[level].min(0) + points[level].max(0)) / 2
    body_centre = (body.vertices[body_level].min(0) + body.vertices[body_level].max(0)) / 2
    points[:, [0, 2]] += (body_centre - centre)[[0, 2]]
    return trimesh.Trimesh(points, mesh.faces, process=False)


def trunk_skin(body, weights, names):
    """The body's skin the fit holds inside the still: the points whose strongest joint is one of FIT_IN (the
    gloves, boots, the backpack over the chest and the neck ring are shaped their own way: 23% of the shins' skin
    reads outside the boots at every height)."""
    return body.vertices[np.isin(np.array(names)[weights.argmax(1)], FIT_IN)]


def arms_turned(bind, names, parents, body, mesh):
    """The bind with each arm turned about its shoulder (its Arm joint) from the body's arm onto the still's, as the
    two bodies' slices find them (prop_rig.landmarks): TRELLIS.2's suit hangs its arms 10 to 12 degrees steeper than
    the dressed body's bind. Every joint down the arm turns with it; the bones keep their lengths. The bind and each
    arm's turn in degrees."""
    from scipy.spatial.transform import Rotation
    still_fit, body_fit = (prop_rig.landmarks(prop_rig.sampled(shape)) for shape in (mesh, body))
    out, turns = bind.copy(), {}
    for side in prop_rig.SIDES:
        chain = side + "Arm"
        start, end = still_fit[chain]["direction"], body_fit[chain]["direction"]
        axis = np.cross(end, start)
        angle = float(np.arccos(np.clip(start @ end, -1.0, 1.0)))
        turn = Rotation.from_rotvec(axis / max(np.linalg.norm(axis), 1e-12) * angle).as_matrix()
        pivot = bind[names.index(chain), :3, 3]
        moved = np.eye(4)
        moved[:3, :3], moved[:3, 3] = turn, pivot - turn @ pivot
        for joint in below(names.index(chain), parents):
            out[joint] = moved @ bind[joint]
        turns[side] = round(float(np.degrees(angle)), 2)
    return out, turns


def below(joint, parents):
    """The joint and every joint under it."""
    found = [joint]
    for child in range(len(parents)):
        if parents[child] >= 0 and parents[child] in found and child not in found:
            found.append(child)
    return found


def fitted_height(mesh, body, skin, names, bind):
    """The height of HEIGHTS at which the least of the body's `skin` (trunk_skin) lies outside the stood still (a
    shorter suit leaves the shoulders out, a taller one the head under its helmet: TRELLIS.2's suit, 9% and 5% at
    1.80 m against 17% and 12% at 1.74 m and 1.86 m) and each height's share."""
    tried = {round(float(height), 3): outside_share(stood_at(mesh, height, body, names, bind), skin)
             for height in HEIGHTS}
    return min(tried, key=tried.get), tried


# --- the parts ------------------------------------------------------------------------------------------------------

def parts_of(mesh, colours, body, names, bind):
    """Each face's part number (PARTS): helmet, visor, backpack, else suit."""
    middles = mesh.triangles_center
    head = (bind[names.index("Head"), :3, 3] + bind[names.index("HeadEnd"), :3, 3]) / 2
    neck = bind[names.index("Neck1"), 1, 3]
    chest = bind[names.index("Chest"), :3, 3]
    found = np.zeros(len(middles), int)
    helmet = (np.linalg.norm(middles - head, axis=1) < HELMET_REACH) & (middles[:, 1] > neck)
    dark = colours[mesh.faces].mean((1, 2)) < VISOR_DARK
    found[helmet] = PARTS.index("helmet")
    found[helmet & dark & (middles[:, 2] > head[2] + VISOR_FRONT)] = PARTS.index("visor")
    off = np.abs(trimesh.proximity.closest_point(body, middles)[1])
    hips = bind[names.index("Hips"), 1, 3]
    pack = (~helmet & (middles[:, 2] < chest[2]) & (off > PACK_OFF) & (middles[:, 1] > hips)
            & (np.abs(middles[:, 0] - chest[0]) < 0.25))
    found[pack] = PARTS.index("backpack")
    return one_visor(mesh, kept_pieces(mesh, found))


def one_visor(mesh, found):
    """`found` with only the visor's largest connected piece kept as visor, every other visor piece (a dark seam
    round the helmet's rim) helmet."""
    visor = np.flatnonzero(found == PARTS.index("visor"))
    if not len(visor):
        return found
    pairs = mesh.face_adjacency
    pairs = pairs[np.isin(pairs[:, 0], visor) & np.isin(pairs[:, 1], visor)]
    _, piece = connected_components(sparse_graph(pairs, len(found)), directed=False)
    largest = np.bincount(piece[visor]).argmax()
    found = found.copy()
    found[visor[piece[visor] != largest]] = PARTS.index("helmet")
    return found


def kept_pieces(mesh, found, rounds=3):
    """Each face's part settled to its neighbours' most common one `rounds` times, so a stray face of another part
    inside a part (a dark seam in the suit, a light fleck on the visor) joins the part round it."""
    neighbours = mesh.face_adjacency
    for _ in range(rounds):
        votes = np.zeros((len(found), len(PARTS)))
        np.add.at(votes, (neighbours[:, 0], found[neighbours[:, 1]]), 1)
        np.add.at(votes, (neighbours[:, 1], found[neighbours[:, 0]]), 1)
        votes[np.arange(len(found)), found] += 1.5
        found = votes.argmax(1)
    return found


# --- the weights ----------------------------------------------------------------------------------------------------

def rigid(points, faces, part_of, weights, names):
    """The hard parts' points on their one joint (RIGID) and the suit's points round them eased onto it by their
    distance over the surface from the nearest hard point: wholly within EASE_HOLD, less and less out to EASE_REACH.
    The still is one surface, so the ease reaches every suit point near a hard part, whatever joint it hangs from
    (prop_build's eased_to_hard eases only a garment on the hard joint's own limb, which on one surface left a cliff
    between the eased cloth and the arms and hips beside it: edges 8 times their length at the backpack's rim); over
    the surface, never straight across a gap, so an upper arm a few centimetres beside the backpack keeps its own
    joint (eased by straight distance it hung on the chest and tore 8 times its length at every swing)."""
    out = weights.copy()
    graph = prop_rig.edge_graph(points, faces)
    hard = np.zeros(len(points), bool)
    for part, joint in RIGID.items():
        used = np.unique(faces[part_of == PARTS.index(part)])
        out[used] = 0.0
        out[used, names.index(joint)] = 1.0
        hard[used] = True
    for joint in set(RIGID.values()):
        used = np.unique(faces[np.isin(part_of, [PARTS.index(part) for part, held in RIGID.items() if held == joint])])
        distance = dijkstra(graph, indices=used, limit=EASE_REACH, min_only=True)[~hard]
        share = np.clip(1.0 - (distance - EASE_HOLD) / (EASE_REACH - EASE_HOLD), 0.0, 1.0)[:, None]
        target = np.zeros((int((~hard).sum()), len(names)))
        target[:, names.index(joint)] = 1.0
        out[~hard] = out[~hard] * (1 - share) + target * share
    return seamed(points, faces, part_of, out, names)


def seamed(points, faces, part_of, weights, names):
    """Where two hard parts on different joints meet (the helmet's back rim on the backpack's top), each one's points
    within SEAM of the other shared between both joints, half and half at the seam and wholly their own SEAM off it,
    so a nod bends the rims a few millimetres rather than opening a crack between two rigid parts."""
    out = weights.copy()
    held = {}
    for part, joint in RIGID.items():
        held.setdefault(joint, []).append(PARTS.index(part))
    for joint, parts in held.items():
        mine = np.unique(faces[np.isin(part_of, parts)])
        for other, other_parts in held.items():
            if other == joint:
                continue
            theirs = np.unique(faces[np.isin(part_of, other_parts)])
            distance = cKDTree(points[theirs]).query(points[mine])[0]
            own = (0.5 + 0.5 * np.clip(distance / SEAM, 0.0, 1.0))[:, None]
            target = np.zeros((len(mine), len(names)))
            target[:, names.index(joint)], target[:, names.index(other)] = own[:, 0], 1 - own[:, 0]
            near = distance < SEAM
            out[mine[near]] = target[near]
    return out / out.sum(1, keepdims=True)


def eased_cliffs(points, faces, weights, fixed):
    """The weights smoothed on every point not `fixed` within CLIFF_REACH over the surface of an edge across which
    they change faster than CLIFF over its length: CLIFF_ROUNDS rounds of moving CLIFF_ALPHA towards the neighbours'
    mean, the fixed points (the hard parts) held. Rows sum to one."""
    graph = prop_rig.edge_graph(points, faces)
    first, second = graph.nonzero()
    jump = np.abs(weights[first] - weights[second]).sum(1) > CLIFF * np.asarray(graph[first, second]).ravel()
    if not jump.any():
        return weights
    reach = dijkstra(graph, indices=np.unique(np.r_[first[jump], second[jump]]), limit=CLIFF_REACH, min_only=True)
    smooth = np.isfinite(reach) & ~fixed
    neighbours = (graph > 0).astype(float)
    from scipy import sparse
    neighbours = sparse.diags(1 / np.maximum(np.asarray(neighbours.sum(1)).ravel(), 1)) @ neighbours
    out = weights.copy()
    for _ in range(CLIFF_ROUNDS):
        mean = neighbours @ out
        out[smooth] = (1 - CLIFF_ALPHA) * out[smooth] + CLIFF_ALPHA * mean[smooth]
    return out / out.sum(1, keepdims=True)


def hard_points(faces, part_of, count):
    """Whether each point belongs to a hard part (RIGID)."""
    hard = np.zeros(count, bool)
    hard[np.unique(faces[np.isin(part_of, [PARTS.index(part) for part in RIGID])])] = True
    return hard


def strongest(weights, how_many=JOINTS_A_VERTEX):
    """The `how_many` joints each point hangs from most and their weights shared out again (body.strongest_joints)."""
    order = np.argsort(-weights, axis=1)[:, :how_many]
    kept = np.take_along_axis(weights, order, axis=1)
    return order, kept / kept.sum(1, keepdims=True)


# --- the clips and the stretch --------------------------------------------------------------------------------------

def clip_worlds(document, blob, animation, names, parents):
    """One clip's joint worlds (frames, joints, 4, 4) in the mesh's frame, from its keys over the rest pose."""
    from scipy.spatial.transform import Rotation
    joints = document["skins"][0]["joints"]
    rest = []
    for joint in joints:
        node = document["nodes"][joint]
        local = np.eye(4)
        local[:3, :3] = Rotation.from_quat(node.get("rotation", [0, 0, 0, 1])).as_matrix()
        local[:3, 3] = node.get("translation", [0, 0, 0])
        rest.append(local)
    count = None
    keys = {}
    for channel in animation["channels"]:
        node, path = channel["target"]["node"], channel["target"]["path"]
        if node not in joints or path not in ("rotation", "translation"):
            continue
        values = skel_usd.accessor(document, blob, animation["samplers"][channel["sampler"]]["output"])
        keys[(joints.index(node), path)] = values
        count = len(values) if count is None else min(count, len(values))
    local = np.repeat(np.array(rest)[None], count, axis=0)
    for (joint, path), values in keys.items():
        if path == "rotation":
            local[:, joint, :3, :3] = Rotation.from_quat(values[:count]).as_matrix()
        else:
            local[:, joint, :3, 3] = values[:count]
    world = np.zeros_like(local)
    for joint in range(len(names)):
        world[:, joint] = local[:, joint] if parents[joint] < 0 else world[:, parents[joint]] @ local[:, joint]
    return world


def posed(points, order, kept, moves):
    """The points carried by their joints' moves from the bind (frames, joints, 4, 4): (frames, points, 3)."""
    blended = np.einsum("pk,fpkab->fpab", kept, moves[:, order])
    return np.einsum("fpab,pb->fpa", blended[..., :3, :], np.concatenate([points, np.ones((len(points), 1))], 1))


def stretch(points, faces, order, kept, moves):
    """Each frame's edge growth over its bind length (route_stretch's measure) on the edges at least EDGE_LEAST long
    (a thinned sliver's growth reads in hundreds): the most and the 99.9th percentile on each frame, and the worst
    edge's middle."""
    edges = np.unique(np.sort(np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]]), 1), axis=0)
    rest = np.linalg.norm(points[edges[:, 0]] - points[edges[:, 1]], axis=1)
    edges, rest = edges[rest >= EDGE_LEAST], rest[rest >= EDGE_LEAST]
    most, high, where = [], [], None
    for frame in range(len(moves)):
        moved = posed(points, order, kept, moves[frame:frame + 1])[0]
        growth = np.linalg.norm(moved[edges[:, 0]] - moved[edges[:, 1]], axis=1) / rest
        most.append(float(growth.max()))
        high.append(float(np.percentile(growth, 99.9)))
        if most[-1] == max(most):
            where = points[edges[growth.argmax()]].mean(0)
    return most, high, where


# --- the glTF -------------------------------------------------------------------------------------------------------

def finish_of(palette, part):
    """A part's library finish from the palette: its variant's spec (tools/props/library: recipe, colour, roughness,
    metal) in its TOKENS token, else the variant's own, and the recipe's entry address."""
    import library as surface_library
    variant = FINISHES[part]
    every = surface_library.variants(palette)
    if variant not in every:
        raise StillError(f"the palette holds no {variant} ({', '.join(sorted(every))})")
    token = TOKENS.get(part, every[variant]["token"])
    spec = surface_library.spec(palette, variant, token, surface_library.token_colours(palette))
    return spec, f"surface/{spec['recipe']}@1"


def material_of(palette, part):
    """A part's glTF material: named for its palette variant, its spec's flat colour, roughness and metal, the
    library address and spec in `extras`."""
    spec, address = finish_of(palette, part)
    return {"name": FINISHES[part], "extras": {"role": "hard" if part in RIGID else "garment", "part": part,
                                               "library": address, "variant": FINISHES[part], "token": spec["token"]},
            "pbrMetallicRoughness": {"baseColorFactor": [float(value) for value in spec["colour"]] + [1.0],
                                     "metallicFactor": float(spec.get("metal", 0.0)),
                                     "roughnessFactor": float(spec.get("roughness", 0.5))}}


def primitive(contents, points, faces, weights, material):
    """One surface as a skinned glTF primitive (four joints a point)."""
    order, kept = strongest(weights)
    normals = trimesh.Trimesh(points, faces, process=False).vertex_normals
    return {"attributes": {
        "POSITION": contents.reading(points.astype(np.float32).ravel().tolist(), "VEC3", glb.FLOAT, glb.ARRAY_BUFFER,
                                     with_bounds=True),
        "NORMAL": contents.reading(normals.astype(np.float32).ravel().tolist(), "VEC3", glb.FLOAT, glb.ARRAY_BUFFER),
        "JOINTS_0": contents.reading(order.astype(np.uint16).ravel().tolist(), "VEC4", glb.UNSIGNED_SHORT,
                                     glb.ARRAY_BUFFER),
        "WEIGHTS_0": contents.reading(kept.astype(np.float32).ravel().tolist(), "VEC4", glb.FLOAT, glb.ARRAY_BUFFER)},
        "indices": contents.reading(faces.reshape(-1).astype(np.uint32).tolist(), "SCALAR", glb.UNSIGNED_INT,
                                    glb.ELEMENT_ARRAY_BUFFER),
        "material": material}


def copied(contents, document, blob, index):
    """An accessor of the dressed body's file copied into the new file's contents; its new number."""
    found = document["accessors"][index]
    values = skel_usd.accessor(document, blob, index)
    component = {5126: glb.FLOAT, 5123: glb.UNSIGNED_SHORT, 5125: glb.UNSIGNED_INT, 5121: glb.UNSIGNED_BYTE}[
        found["componentType"]]
    number = contents.reading(np.asarray(values).ravel().tolist(), found["type"], component,
                              with_bounds="min" in found)
    return number


def pieces_of(points, faces, part_of, weights):
    """Each part's own points, faces and weights (renumbered)."""
    found = {}
    for part in np.unique(part_of):
        used, renumbered = np.unique(faces[part_of == part], return_inverse=True)
        found[int(part)] = (points[used], renumbered.reshape(-1, 3), weights[used])
    return found


def written(out, document, blob, bind, points, faces, part_of, weights, palette):
    """The glTF: the dressed body's Person node, joints, skin and clips (joint keys only), the still's parts as the
    OUTFIT node and its far body bound at `bind`; each part a library finish."""
    contents = glb.Contents()
    skin = document["skins"][0]
    joints = list(skin["joints"])
    keep = [document["scenes"][0]["nodes"][0]] + joints
    renumber = {old: new for new, old in enumerate(keep)}
    nodes = []
    for old in keep:
        node = {key: value for key, value in document["nodes"][old].items() if key not in ("mesh", "skin")}
        node["children"] = [renumber[child] for child in document["nodes"][old].get("children", []) if child in renumber]
        if not node["children"]:
            del node["children"]
        nodes.append(node)
    new = {"asset": {"version": "2.0", "generator": "score tools/characters/still_rig/still_rig.py"}, "scene": 0,
           "scenes": [{"nodes": [0]}], "nodes": nodes, "materials": [], "meshes": [], "animations": [],
           "skins": [{"inverseBindMatrices": contents.reading(np.linalg.inv(bind).transpose(0, 2, 1).astype(
               np.float32).ravel().tolist(), "MAT4", glb.FLOAT),
                      "joints": [renumber[joint] for joint in joints], "skeleton": renumber[joints[0]]}]}
    for animation in document.get("animations", []):
        samplers, channels = [], []
        for channel in animation["channels"]:
            if channel["target"]["path"] == "weights" or channel["target"]["node"] not in renumber:
                continue
            sampler = animation["samplers"][channel["sampler"]]
            samplers.append({"input": copied(contents, document, blob, sampler["input"]),
                             "output": copied(contents, document, blob, sampler["output"]),
                             "interpolation": sampler.get("interpolation", "LINEAR")})
            channels.append({"sampler": len(samplers) - 1,
                             "target": {"node": renumber[channel["target"]["node"]], "path": channel["target"]["path"]}})
        new["animations"].append({"name": animation["name"], "samplers": samplers, "channels": channels})
    for part in PARTS:
        new["materials"].append(material_of(palette, part))
    near = [primitive(contents, *piece, part) for part, piece in pieces_of(points, faces, part_of, weights).items()]
    whole = trimesh.Trimesh(points, faces, process=False)
    thin = whole.simplify_quadric_decimation(face_count=FAR_TRIANGLES)
    nearest_face = cKDTree(whole.triangles_center).query(thin.triangles_center)[1]
    far_weights = weights[cKDTree(points).query(thin.vertices)[1]]
    far = [primitive(contents, *piece, part) for part, piece in
           pieces_of(thin.vertices, thin.faces, part_of[nearest_face], far_weights).items()]
    for name, primitives in (("far", far), (OUTFIT, near)):
        new["meshes"].append({"name": name, "primitives": primitives})
        new["nodes"].append({"name": name, "mesh": len(new["meshes"]) - 1, "skin": 0})
        new["nodes"][0].setdefault("children", []).append(len(new["nodes"]) - 1)
    glb.write(out, new, contents)
    return {"far_triangles": int(len(thin.faces)), "triangles": int(len(faces))}


# --- the whole rig --------------------------------------------------------------------------------------------------

def rigged(still, dressed, rig_path, palette_path, out, faces=FACES):
    """The still rigged on the dressed body's skeleton into `out` (body.glb, rig.json); the record."""
    document, blob, names, dressed_bind, parents = skeleton_of(dressed)
    rig = np.load(rig_path)
    body, body_weights = soma_on(rig, names, dressed_bind)
    raw, colours = still_of(still)
    thin = thinned(raw, faces)
    skin = trunk_skin(body, body_weights, names)
    height, tried = fitted_height(thin, body, skin, names, dressed_bind)
    fitted = stood_at(thin, height, body, names, dressed_bind)
    bind, arm_turns = arms_turned(dressed_bind, names, parents, body, fitted)
    body, body_weights = soma_on(rig, names, bind)
    mesh = closed(fitted)
    colours = colours[cKDTree(raw.vertices).query(thin.vertices)[1]][cKDTree(fitted.vertices).query(mesh.vertices)[1]]
    part_of = parts_of(mesh, colours, body, names, bind)
    fit = prop_rig.landmarks(prop_rig.sampled(mesh))
    weights, matched, smoothed = prop_rig.transferred(body, body_weights, mesh, np.array(names), fit)
    weights = rigid(mesh.vertices, mesh.faces, part_of, weights, names)
    weights = eased_cliffs(mesh.vertices, mesh.faces, weights, hard_points(mesh.faces, part_of, len(mesh.vertices)))
    out.mkdir(parents=True, exist_ok=True)
    palette = json.loads(pathlib.Path(palette_path).read_text())
    sizes = written(out / "body.glb", document, blob, bind, mesh.vertices, mesh.faces, part_of, weights, palette)
    order, kept = strongest(weights)
    clips = {}
    for animation in document["animations"]:
        moves = clip_worlds(document, blob, animation, names, parents) @ np.linalg.inv(bind)
        most, high, where = stretch(mesh.vertices, mesh.faces, order, kept, moves)
        clips[animation["name"]] = {"stretch_most": round(max(most), 3), "stretch_999": round(max(high), 3),
                                    "frames": len(most), "where": np.round(where, 3).tolist()}
    record = {"still": str(still), "dressed": str(dressed), "rig": str(rig_path), "palette": str(palette_path),
              "height_m": round(height, 3), "heights_tried": tried, "arm_turns_degrees": arm_turns,
              "outside_share": round(outside_share(fitted, trunk_skin(body, body_weights, names)), 4),
              "outside_share_with_arms": round(outside_share(fitted, body.vertices[~np.isin(
                  np.array(names)[body_weights.argmax(1)], ["LeftHand", "RightHand", "LeftFoot", "RightFoot",
                                                            "LeftToeBase", "RightToeBase", "LeftToeEnd", "RightToeEnd",
                                                            "Head", "HeadEnd"])]), 4), "matched_share": round(matched, 4),
              "smoothed_share": round(smoothed, 4), **sizes,
              "open_edges": open_edges(mesh),
              "parts": {part: int((part_of == number).sum()) for number, part in enumerate(PARTS)},
              "finishes": {part: finish_of(palette, part)[1] + f" {FINISHES[part]}" for part in PARTS},
              "clips": clips}
    (out / "rig.json").write_text(json.dumps(record, indent=1))
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("still", type=pathlib.Path)
    parser.add_argument("dressed", type=pathlib.Path)
    parser.add_argument("rig", type=pathlib.Path)
    parser.add_argument("palette", type=pathlib.Path)
    parser.add_argument("out", type=pathlib.Path)
    parser.add_argument("--faces", type=int, default=FACES)
    options = parser.parse_args()
    record = rigged(options.still, options.dressed, options.rig, options.palette, options.out, options.faces)
    print(f"still rig: {record['height_m']} m, {record['triangles']} triangles, parts {record['parts']}, matched "
          f"{record['matched_share']:.0%}, stretch {({name: clip['stretch_most'] for name, clip in record['clips'].items()})}; "
          f"{options.out / 'rig.json'}", flush=True)


if __name__ == "__main__":
    main()
