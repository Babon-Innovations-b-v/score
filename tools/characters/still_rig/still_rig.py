"""A still model rigged as a player model (#128, owner 2026-11-18, of the paper's TRELLIS.2 astronaut: "why dont we use
these models for the astraunauts, that one looks way better"): a picture-made mesh with no skeleton put on a dressed
body's own skeleton, so it plays every clip and sim-body motion that body plays. Plain CPU geometry (numpy, scipy,
trimesh); no model runs.

    .venv/bin/python tools/characters/still_rig/still_rig.py <still.glb> <dressed body.glb> <clips rig.npz>
        <palette.json> <out folder> [--faces 60000] [--person]

The steps:

1. The skeleton is the dressed body's (people-dress-<look>'s body.glb): its joints, bind, rest and clips are kept as
   they are, so cast/driven, the walker peel and lay_walkers play it unchanged.
2. The SOMA surface (people-clips-made's rig.npz, the mean body and its weights) is moved onto that bind by its own
   weights (prop_rig.skinned_source): the body the still is fitted to and its weights' source, never drawn.
3. The still is stood (prop_rig.stood: up +y, facing +z, soles on the floor), centred over the body's hips, and sized
   to the height at which the least of the body's trunk, head, thighs and shoulders stands outside it
   (`fitted_height`; a person, `--person`, at the body's own height); the still is its outer surface alone
   (`outer_kept`: TRELLIS.2's shell has an inner layer facing the hollow): scale and align only, its geometry
   otherwise its own. It is thinned to about `--faces` triangles first (prop_rig.decimated, its borders kept). A
   person's shoes are laid heel to toe on the dressed body's own feet (`feet_fitted`), whose soles the sim body stands.
4. Its parts (`parts_of`): the helmet (every face within HELMET_REACH of the head's middle above the neck), the visor
   (the helmet's dark faces in front, its own baked colour read only to find it, their largest connected piece alone:
   a dark seam at the helmet's rim is helmet), the backpack (behind the chest, more
   than PACK_OFF off the body) and the suit (the rest), each face's part settled to its neighbours'; a person's
   (`--person`) only its head (the helmet's faces: face and hair) and its clothes (the rest). Every open loop
   the outer cut left (the armpits behind the shoulders, the boots' tops and soles, where no sight line reached:
   black tears in the film) is closed by a fan from its middle (`closed`) after the fit (whose inside test the fans,
   reaching across the hollow, would mislead: 21% of the skin outside against 4%).
5. The weights: Robust Skin Weights Transfer from the SOMA surface (prop_rig.transferred: closest-surface matches
   within its distance and angle, each limb only from its own limb, the rest inpainted and smoothed; a person whose
   arms lie against the trunk all the way down has its arms read by `fused_landmarks`), nothing above a
   foot's ankle on that foot (`off_the_feet`: a wide trouser leg inpainted from its hem swung back from the calf at
   every push-off) and nothing well over a knee on that shin (`off_the_shins`: the same jeans hung thigh points from
   the shin and spiked 18 cm off the thigh at every stride), then the helmet and visor rigid on the head and the
   backpack rigid on the chest (`rigid`), the suit next to them eased onto their joint by its distance over the
   surface (`rigid`), so nothing tears where a hard part meets the cloth. Last, every cloth point within CLIFF_REACH
   of an edge across which the weights change faster than CLIFF (the crotch, where each leg's points may hang only
   from their own leg, and the shoulders' rims) is smoothed towards its neighbours (`eased_cliffs`), so a stride
   bends the cloth over a few centimetres instead of one edge (walking's worst edge 11.9 times its length before, 9.1
   after; its 99.9th percentile 3.7 and 2.5).
6. The finish is the still's own paint (owner 2026-11-19, of the TRELLIS.2 astronaut beside the one laid in library
   surfaces a part: "this pure trellis is just so much better ... the segmentation of the visor isnt perf and the
   seams, all player models have this problem"; the library rule's written exception for player models): the rigged
   still is laid flat on one MAP map (`unwrapped`, xatlas), each texel reads the still's own base colour and metal and
   roughness nearest its point on the still's outer faces (`Source`, `own_maps`), so its seams, folds, panels and
   prints stay, and the base colour is graded toward the place's palette tokens as a made prop's paint is
   (score/stages/place_build/maker/grade.py). The parts keep only their joints and their `role`.
7. The glTF (`written`): the dressed body's skeleton and clips (its corrective morph keys left out: the still has no
   targets), the still as its `work` node and a far body of FAR_TRIANGLES out of the file's default scene
   (people/glb.py levels_apart, #156); `stretch` measures the longest edge's
   growth on every frame of every clip.

Writes <out>/body.glb, <out>/rig.json (the fit, the parts' triangles, the matched share, the grade's colour groups,
each clip's stretch).
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

import glb  # noqa: E402  (people/glb.py, the glTF writer)
import prop_rig  # noqa: E402
import skel_usd  # noqa: E402

GRADE = HERE.parents[2] / "score/stages/place_build/maker/grade.py"  # the made props' grade, loaded by its file

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
FOOT_JOINTS = ("Foot", "ToeBase", "ToeEnd")  # a side's foot skin (feet_fitted), after Left or Right
SOLE_BIN, SOLE_OFF = 0.02, 0.01  # metres: a sole's bins along the foot, and how far over its line a bin is dropped
ANKLE_BLEND = 0.08  # metres over the body's ankle across which a person's shoe fit gives way to the leg
KNEE_BLEND = 0.06  # metres over the knee (the Shin joint) across which the shin's weights give way to the thigh's
HELMET_REACH = 0.25  # metres from the head's middle (between Head and HeadEnd) a helmet face lies within (the
# suit's visor reaches 0.24 at its chin, the collar 0.26: at 0.21 the visor's lower half was cut off as suit cloth)
VISOR_DARK = 0.5  # a helmet face darker than this (its baked colour's mean; the suit's visor 0.43 to 0.47, its shell
# 0.6 and over) and VISOR_FRONT in front of the head's middle is the visor
VISOR_FRONT = 0.04
PACK_OFF = 0.05  # metres off the body behind the chest a backpack face stands at least
PARTS = ("suit", "helmet", "visor", "backpack", "head")
RIGID = {"helmet": "Head", "visor": "Head", "backpack": "Chest"}
# A person (`--person`) has no helmet, visor or backpack: the faces the helmet would take are its head (face and
# hair), the rest its clothes; neither is rigid (hair resting on the shoulders is one surface with the shirt, and a
# rigid head eased over it hung the stairwell woman's sleeves from her head).
SEAM = 0.06  # metres either side of where two hard parts on different joints meet over which they share both
EASE_HOLD, EASE_REACH = 0.01, 0.08  # metres from a hard part over which the suit is eased onto its joint (`rigid`)
# Where on each of the still's faces its own paint is read (`Source`): the corners, the edges' middles, the middle and
# a point towards each corner (barycentric weights), about 1 mm apart on TRELLIS.2's 3 mm faces.
SPREAD = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1], [.5, .5, 0], [0, .5, .5], [.5, 0, .5], [1 / 3, 1 / 3, 1 / 3],
                   [2 / 3, 1 / 6, 1 / 6], [1 / 6, 2 / 3, 1 / 6], [1 / 6, 1 / 6, 2 / 3]])
MAP = 2048  # the rigged still's own maps' side (TRELLIS.2's own texture is 2048)
MAP_PADDING = 4  # texels round each chart, filled from the chart's rim (`bled`) so no seam shows
GRADE_SAMPLES = 20000  # the painted texels the grade reads its colour groups from (the maker's SAMPLES)
MAP_ROLES = ("base_color", "metal_roughness")  # the maps in the file's texture order (material_of reads 0 and 1)
# The library rule's written exception a player model's own paint is (data/checks/library-exceptions.json).
OWN_TEXTURE = "the still's own paint, graded toward its place's palette (library exception: player models, 2026-11-19)"
CLIFF = 20.0  # per metre: the weights' summed difference across an edge (0 to 2) over its length above which the
# cloth round it is eased (a whole change of joint over 10 cm; the shoulder's 0.36 across 2.4 mm tore 11.8 times)
CLIFF_REACH = 0.05  # metres over the surface from such an edge the easing reaches
# A person whose arms hang against the trunk all the way down (`fused_landmarks`; TRELLIS.2's hoodie man in an open
# overshirt and the older woman in a long coat, 2026-11-27: no slice parts sleeve from trunk), the arm is the sleeve
# at each side's outer edge:
SLEEVE_BAND = 0.10  # metres: a slice's outermost points this deep on a side are the sleeve its middle is read from
SLEEVE_HALF = 0.06  # metres: a point this near the sleeve's middle line, or beyond it, is the arm's
ARM_UNDER_SHOULDER = 0.08  # metres: the sleeve is read and labelled this far under the shoulder (the Arm joint) down
HAND_UNDER_WRIST = 0.10  # metres: and down to this far under the wrist (the Hand joint)
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

class Source:
    """The still's own paint where it lies: points spread over its outer faces (in the still's own frame), each with
    its base colour and, where the still has one, its metal and roughness (glTF's packing), read from its own maps at
    the point's texture place; `paint(points)` gives each of `points` the nearest sample's."""

    def __init__(self, mesh, faces):
        material = mesh.visual.material
        pictures = {"base_color": material.baseColorTexture, "metal_roughness": getattr(
            material, "metallicRoughnessTexture", None)}
        triangles = mesh.vertices[faces]
        coordinates = mesh.visual.uv[faces]
        self.points = np.einsum("sc,fcd->fsd", SPREAD, triangles).reshape(-1, 3)
        places = np.einsum("sc,fcd->fsd", SPREAD, coordinates).reshape(-1, 2)
        self.values = {role: bilinear(np.asarray(picture.convert("RGB"), float) / 255.0, places)
                       for role, picture in pictures.items() if picture is not None}
        self.tree = cKDTree(self.points)

    def paint(self, points):
        """{role: (n, 3) values} of the nearest sample to each point."""
        nearest = self.tree.query(points)[1]
        return {role: values[nearest] for role, values in self.values.items()}


def bilinear(picture, places):
    """`picture` (rows, columns, 3) read at glTF texture places (u right, v up), bilinearly, wrapping."""
    rows, columns = picture.shape[:2]
    across = (places[:, 0] % 1.0) * columns - 0.5
    down = (1.0 - places[:, 1] % 1.0) * rows - 0.5
    left, top = np.floor(across).astype(int), np.floor(down).astype(int)
    right_share, low_share = (across - left)[:, None], (down - top)[:, None]
    left, right = left % columns, (left + 1) % columns
    top, bottom = top % rows, (top + 1) % rows
    return ((picture[top, left] * (1 - right_share) + picture[top, right] * right_share) * (1 - low_share)
            + (picture[bottom, left] * (1 - right_share) + picture[bottom, right] * right_share) * low_share)


def still_of(path):
    """The still's outer surface welded (`outer_kept`), each vertex's baked colour (its base colour map at its texture
    place: finds the visor) and its own paint on those outer faces (`Source`, which the rigged still's maps are read
    from)."""
    mesh = trimesh.load(path, force="mesh", process=False)
    welded = prop_rig.welded(trimesh.Trimesh(mesh.vertices, mesh.faces, process=False))
    kept = outer_kept(welded)
    source = Source(mesh, mesh.faces[kept])
    used, renumbered = np.unique(welded.faces[kept], return_inverse=True)
    welded = trimesh.Trimesh(welded.vertices[used], renumbered.reshape(-1, 3), process=False)
    return welded, source.paint(welded.vertices)["base_color"], source


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


def outer_kept(mesh, rounds=CLOSE_ROUNDS):
    """Which faces are the still's outer surface: TRELLIS.2 makes a thin-walled shell, an outer layer facing out and an
    inner one facing the hollow 1 to 2 cm in (the suit's: 34% of its faces seen from outside, every one facing its
    ray), and the inner layer's normals face the body, so neither the fit's inside test nor the weights' normal match
    can read it. The faces seen from outside (seen_faces) are kept, and a face unseen between kept ones (two of its
    three neighbours kept, `rounds` times) joins them, so a crevice the rays missed is no hole."""
    kept = seen_faces(mesh)
    pairs = mesh.face_adjacency
    for _ in range(rounds):
        around = np.zeros(len(kept), int)
        np.add.at(around, pairs[:, 0], kept[pairs[:, 1]])
        np.add.at(around, pairs[:, 1], kept[pairs[:, 0]])
        kept = kept | (around >= 2)
    return kept


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


def feet_fitted(mesh, feet):
    """A person's shoes laid on the dressed body's feet (`--person`; `feet`, dressed_feet's): each foot of the stood
    still (its points below that foot's ankle plus ANKLE_BLEND, on its side) moved and stretched along its length (z)
    to the foot's heel and toe, moved across (x) to its middle and pitched onto its sole (`sole_line`), fully up to the
    ankle and less over ANKLE_BLEND above it, so the leg is left as it is. The sim body stands, lifts and clears its
    next step by the built body's soles, which the dressed body wears: a shoe past them sinks where they do not (the
    stairwell woman's TRELLIS.2 shoes reached 3.4 cm past her toes and stood 2 cm in every tread she stood on, 18 cm
    at a toe caught under the next step; laid on the SOMA mean's feet instead, 2.5 cm forward of her own, 1.2 cm)."""
    points = mesh.vertices.copy()
    middle = sum(float(skin[:, 0].mean()) for skin, _ in feet.values()) / 2
    for side, (skin, ankle) in feet.items():
        on_side = np.sign(points[:, 0] - middle) == np.sign(skin[:, 0].mean() - middle)
        foot = on_side & (points[:, 1] < ankle + ANKLE_BLEND)
        shoe = points[foot & (points[:, 1] < ankle)]
        if not len(shoe):
            raise StillError(f"the still has no {side.lower()} foot below the body's ankle ({ankle:.3f} m)")
        stretch = np.ptp(skin[:, 2]) / max(float(np.ptp(shoe[:, 2])), 1e-6)
        laid = points[foot].copy()
        laid[:, 2] = skin[:, 2].min() + (laid[:, 2] - shoe[:, 2].min()) * stretch
        laid[:, 0] += (skin[:, 0].min() + skin[:, 0].max()) / 2 - (shoe[:, 0].min() + shoe[:, 0].max()) / 2
        sole_of_shoe = sole_line(laid[points[foot, 1] < ankle])
        laid[:, 1] += np.polyval(sole_line(skin), laid[:, 2]) - np.polyval(sole_of_shoe, laid[:, 2])
        share = np.clip((ankle + ANKLE_BLEND - points[foot, 1]) / ANKLE_BLEND, 0.0, 1.0)[:, None]
        points[foot] += share * (laid - points[foot])
    return trimesh.Trimesh(points, mesh.faces, process=False)


def dressed_feet(document, blob, names):
    """The dressed body's own feet at its bind, {side: (points, ankle height)}: every point of its meshes whose
    strongest joint is one of the side's FOOT_JOINTS, and the highest of them on its Foot joint."""
    found = {side: [] for side in ("Left", "Right")}
    for mesh in document["meshes"]:
        for primitive in mesh["primitives"]:
            attributes = primitive["attributes"]
            if "JOINTS_0" not in attributes:
                continue
            points = skel_usd.accessor(document, blob, attributes["POSITION"]).reshape(-1, 3).astype(float)
            joints = skel_usd.accessor(document, blob, attributes["JOINTS_0"]).reshape(-1, 4)
            weights = skel_usd.accessor(document, blob, attributes["WEIGHTS_0"]).reshape(-1, 4)
            strongest = np.array(names)[joints[np.arange(len(joints)), weights.argmax(1)]]
            for side in found:
                mine = np.isin(strongest, [f"{side}{joint}" for joint in FOOT_JOINTS])
                found[side].append((points[mine], points[strongest == f"{side}Foot"]))
    feet = {}
    for side, pieces in found.items():
        skin, on_foot = (np.concatenate([piece[index] for piece in pieces]) for index in (0, 1))
        if not len(on_foot):
            raise StillError(f"the dressed body has no {side.lower()} foot")
        feet[side] = (skin, float(on_foot[:, 1].max()))
    return feet


def sole_line(points):
    """The line (height over length, np.polyfit's) under a foot's points: the lowest point of each SOLE_BIN along
    its length, fitted, and fitted again without the bins more than SOLE_OFF over the first line (a sparse bin's lowest
    point lies up the instep)."""
    bins = np.floor((points[:, 2] - points[:, 2].min()) / SOLE_BIN).astype(int)
    lowest = np.array([points[bins == number][points[bins == number, 1].argmin()] for number in np.unique(bins)])
    line = np.polyfit(lowest[:, 2], lowest[:, 1], 1)
    kept = lowest[lowest[:, 1] - np.polyval(line, lowest[:, 2]) <= SOLE_OFF]
    return np.polyfit(kept[:, 2], kept[:, 1], 1) if len(kept) >= 2 else line


def trunk_skin(body, weights, names):
    """The body's skin the fit holds inside the still: the points whose strongest joint is one of FIT_IN (the
    gloves, boots, the backpack over the chest and the neck ring are shaped their own way: 23% of the shins' skin
    reads outside the boots at every height)."""
    return body.vertices[np.isin(np.array(names)[weights.argmax(1)], FIT_IN)]


def arms_turned(bind, names, parents, body, mesh):
    """The bind with each arm turned about its shoulder (its Arm joint) from the body's arm onto the still's, as the
    two bodies' slices find them (prop_rig.landmarks): the shoulder's line through the middle of the body's arm turned
    onto its line through the middle of the still's (`arm_middle`), so the arm hangs in the sleeve, not beside it.
    TRELLIS.2's suit hangs its arms 10 to 12 degrees steeper than the dressed body's bind, and the stairwell woman's
    sleeves hang 10 cm before its arms: turned only parallel to them, the arms stayed behind the sleeves, whose
    upper half took her chest's weights and bulged at the shoulder when her arms came down. Every joint down the arm
    turns with it; the bones keep their lengths. The bind and each arm's turn in degrees."""
    from scipy.spatial.transform import Rotation
    still_fit = landmarks_of(prop_rig.sampled(mesh), bind, names)
    body_fit = prop_rig.landmarks(prop_rig.sampled(body))
    out, turns = bind.copy(), {}
    for side in prop_rig.SIDES:
        chain = side + "Arm"
        pivot = bind[names.index(chain), :3, 3]
        start, end = (arm_middle(fit[chain]) - pivot for fit in (still_fit, body_fit))
        start, end = start / np.linalg.norm(start), end / np.linalg.norm(end)
        axis = np.cross(end, start)
        angle = float(np.arccos(np.clip(start @ end, -1.0, 1.0)))
        turn = Rotation.from_rotvec(axis / max(np.linalg.norm(axis), 1e-12) * angle).as_matrix()
        moved = np.eye(4)
        moved[:3, :3], moved[:3, 3] = turn, pivot - turn @ pivot
        for joint in below(names.index(chain), parents):
            out[joint] = moved @ bind[joint]
        turns[side] = round(float(np.degrees(angle)), 2)
    return out, turns


def landmarks_of(points, bind, names):
    """The still's landmarks (prop_rig.landmarks) or, where its arms never stand apart from its trunk, the fused
    person's (`fused_landmarks`)."""
    try:
        return prop_rig.landmarks(points)
    except prop_rig.RigError as error:
        if "arms never stand apart" not in str(error):
            raise
    return fused_landmarks(points, bind, names)


def fused_landmarks(points, bind, names):
    """Landmarks of a still whose arms lie against its trunk from shoulder to hand (every slice one piece): its legs
    as prop_rig finds them, each arm's axis through the middles of each slice's outermost SLEEVE_BAND on its side, from
    ARM_UNDER_SHOULDER under the bind's shoulder down to HAND_UNDER_WRIST under its wrist, and its points within
    SLEEVE_HALF of that line or beyond it the arm's (the limbs prop_rig.transferred matches on the arm alone)."""
    height = float(points[:, 1].max())
    cuts = prop_rig.slices(points)
    crotch = prop_rig.crotch_of(cuts, height)
    limbs = prop_rig.limb_labels(points, cuts, crotch, crotch, height)
    found = {"height": height, "crotch": crotch, "samples": points, "limbs": limbs}
    for side, sign in prop_rig.SIDES.items():
        top = bind[names.index(side + "Arm"), 1, 3] - ARM_UNDER_SHOULDER
        low = bind[names.index(side + "Hand"), 1, 3] - HAND_UNDER_WRIST
        centres, members = [], []
        for level in np.arange(low, top, prop_rig.SLICE):
            band = np.flatnonzero((np.abs(points[:, 1] - level) < prop_rig.SLICE / 2) & (sign * points[:, 0] > 0))
            if not len(band):
                continue
            outer = band[sign * points[band, 0] > (sign * points[band, 0]).max() - SLEEVE_BAND]
            centres.append(points[outer].mean(0))
            members.append(outer)
        arm = prop_rig.limb(points, centres, np.concatenate(members), top)
        found[side + "Arm"] = arm
        along = (points[:, 1] - arm["start"][1]) / arm["direction"][1]
        middle_x = arm["start"][0] + along * arm["direction"][0]
        sleeve = (sign * points[:, 0] > sign * middle_x - SLEEVE_HALF) & (points[:, 1] <= top) & (
            points[:, 1] >= low) & (points[:, 1] > crotch) & (sign * points[:, 0] > 0)
        limbs[sleeve] = side + "Arm"
    return found


def arm_middle(arm):
    """The middle of a limb's axis (prop_rig.limb: its start, direction down and length)."""
    return np.asarray(arm["start"]) + np.asarray(arm["direction"]) * arm["length"] / 2


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

def parts_of(mesh, colours, body, names, bind, person=False):
    """Each face's part number (PARTS): helmet, visor, backpack, else suit; a `person`'s head, else suit."""
    middles = mesh.triangles_center
    head = (bind[names.index("Head"), :3, 3] + bind[names.index("HeadEnd"), :3, 3]) / 2
    neck = bind[names.index("Neck1"), 1, 3]
    chest = bind[names.index("Chest"), :3, 3]
    found = np.zeros(len(middles), int)
    helmet = (np.linalg.norm(middles - head, axis=1) < HELMET_REACH) & (middles[:, 1] > neck)
    if person:
        found[helmet] = PARTS.index("head")
        return kept_pieces(mesh, found)
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


def off_the_feet(points, weights, names, bind):
    """No point above a foot's ankle hangs from that foot: each side's Foot and toe weights moved onto its Shin,
    wholly ANKLE_BLEND over the Foot joint's bind height, less and less down to it. Cloth the surface match missed
    (a wide trouser leg standing off the shin) is inpainted from its matched neighbours, and the hem's on the shoe
    carried the foot up the leg: the generated stairwell woman's wide jeans hung a quarter of their points from the
    foot up to 0.5 m, and every push-off swung their calves back in a fin (2026-11-26)."""
    out = weights.copy()
    for side in ("Left", "Right"):
        ankle = bind[names.index(f"{side}Foot"), 1, 3]
        feet = [names.index(f"{side}{joint}") for joint in FOOT_JOINTS if f"{side}{joint}" in names]
        share = np.clip((points[:, 1] - ankle) / ANKLE_BLEND, 0.0, 1.0)
        moved = out[:, feet] * share[:, None]
        out[:, feet] -= moved
        out[:, names.index(f"{side}Shin")] += moved.sum(1)
    return out


def off_the_shins(points, weights, names, bind):
    """No point well over a knee hangs from that shin: each side's Shin weights moved onto its Leg (the thigh),
    wholly KNEE_BLEND over the Shin joint's bind height, less and less down to it. The generated stairwell woman's
    wide jeans hung 175 thigh points up to 27 cm over the knee wholly from the shin (inpainted down the wide leg), and
    every stride swung them 18 cm off the thigh in a spike (round 4 of the cloth, 2026-11-27)."""
    out = weights.copy()
    for side in ("Left", "Right"):
        shin = names.index(f"{side}Shin")
        share = np.clip((points[:, 1] - bind[shin, 1, 3]) / KNEE_BLEND, 0.0, 1.0)
        moved = out[:, shin] * share
        out[:, shin] -= moved
        out[:, names.index(f"{side}Leg")] += moved
    return out


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

def grade_module():
    """The made props' grade (score/stages/place_build/maker/grade.py: numpy and scipy only), loaded by its file."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("maker_grade", GRADE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def unwrapped(points, faces, normals, size=MAP):
    """The rigged still laid flat on one map of `size` (xatlas, MAP_PADDING round each chart): each new point's old
    point, the faces on the new points (in the old faces' order) and each new point's texture place (u right, v up,
    as trimesh reads a glTF's; `primitive` writes glTF's v down)."""
    import xatlas
    atlas = xatlas.Atlas()
    atlas.add_mesh(points.astype(np.float32), faces.astype(np.uint32), normals.astype(np.float32))
    packing = xatlas.PackOptions()
    packing.resolution, packing.padding, packing.bilinear = size, MAP_PADDING, True
    atlas.generate(pack_options=packing)
    if atlas.atlas_count != 1:
        raise StillError(f"the still's charts took {atlas.atlas_count} maps of {size}, not one")
    mapping, new_faces, places = atlas[0]
    widest = max(atlas.width, atlas.height)  # xatlas may pack a little past `size`: the whole laid into the square
    across, down = places[:, 0] * atlas.width / widest, places[:, 1] * atlas.height / widest
    return mapping.astype(np.int64), new_faces.astype(np.int64), np.c_[across, 1.0 - down]


def texels_of(points, faces, places, size=MAP):
    """Every texel whose middle lies in a face as laid on the map: its row, column and the point of the face there."""
    corners = np.stack([places[faces][..., 0] * size - 0.5, (1.0 - places[faces][..., 1]) * size - 0.5], -1)
    low = np.clip(np.floor(corners.min(1)).astype(int), 0, size - 1)
    high = np.clip(np.ceil(corners.max(1)).astype(int), 0, size - 1)
    spans = high - low + 1
    counts = spans[:, 0] * spans[:, 1]
    face = np.repeat(np.arange(len(faces)), counts)
    within = np.arange(counts.sum()) - np.repeat(np.cumsum(counts) - counts, counts)
    column = low[face, 0] + within % spans[face, 0]
    row = low[face, 1] + within // spans[face, 0]
    first, second, third = corners[face, 0], corners[face, 1], corners[face, 2]
    at = np.c_[column, row].astype(float)
    one, two, there = second - first, third - first, at - first
    area = one[:, 0] * two[:, 1] - one[:, 1] * two[:, 0]
    kept = np.abs(area) > 1e-12
    safe = np.where(kept, area, 1.0)
    towards_second = (there[:, 0] * two[:, 1] - there[:, 1] * two[:, 0]) / safe
    towards_third = (one[:, 0] * there[:, 1] - one[:, 1] * there[:, 0]) / safe
    shares = np.c_[1.0 - towards_second - towards_third, towards_second, towards_third]
    inside = kept & (shares >= -1e-6).all(1)
    found = np.einsum("nc,ncd->nd", shares[inside], points[faces[face[inside]]])
    return row[inside], column[inside], found


def bled(picture, filled):
    """`picture` with every texel no face covers given its nearest covered texel's value, so a chart's rim, read
    bilinearly or from a smaller mip, never takes the empty map's black."""
    from scipy.ndimage import distance_transform_edt
    nearest = distance_transform_edt(~filled, return_distances=False, return_indices=True)
    return picture[nearest[0], nearest[1]]


def own_maps(points, faces, places, back, source, tokens, size=MAP):
    """The rigged still's own maps ({role: (size, size, 3) uint8}: base colour and, where the still has them, metal and
    roughness), each texel the still's own paint nearest its point taken back into the still's frame (`back`), the
    base colour graded toward the palette's `tokens` as the made props' paint is (grade.py); and the grade's groups."""
    rows, columns, found = texels_of(points, faces, places, size)
    paint = source.paint(back(found))
    filled = np.zeros((size, size), bool)
    filled[rows, columns] = True
    maps, report = {}, []
    for role, values in paint.items():
        picture = np.zeros((size, size, 3))
        picture[rows, columns] = values
        if role == "base_color" and tokens:
            chosen = np.random.default_rng(7).choice(len(values), min(GRADE_SAMPLES, len(values)), replace=False)
            picture, report = grade_module().graded(picture, values[chosen], tokens)
        maps[role] = np.round(np.clip(bled(picture, filled), 0.0, 1.0) * 255).astype(np.uint8)
    return maps, report


def png(picture):
    """A (rows, columns, 3) uint8 picture encoded as PNG."""
    import io
    from PIL import Image
    encoded = io.BytesIO()
    Image.fromarray(picture, "RGB").save(encoded, "PNG")
    return encoded.getvalue()


def material_of(part, maps):
    """A part's glTF material: the still's own maps (texture 0 its base colour, 1 its metal and roughness when it has
    them), its part and role in `extras` and `own_texture` naming the library rule's written exception for it."""
    pbr = {"baseColorTexture": {"index": 0}, "metallicFactor": 0.0, "roughnessFactor": 1.0}
    if "metal_roughness" in maps:
        pbr.update(metallicRoughnessTexture={"index": 1}, metallicFactor=1.0)
    return {"name": f"own_{part}", "pbrMetallicRoughness": pbr,
            "extras": {"role": "hard" if part in RIGID else "garment", "part": part, "own_texture": OWN_TEXTURE}}


def primitive(contents, points, faces, weights, normals, places, material):
    """One surface as a skinned glTF primitive (four joints a point) with its texture places (`places` v up, written
    as glTF's v down)."""
    order, kept = strongest(weights)
    return {"attributes": {
        "POSITION": contents.reading(points.astype(np.float32).ravel().tolist(), "VEC3", glb.FLOAT, glb.ARRAY_BUFFER,
                                     with_bounds=True),
        "NORMAL": contents.reading(normals.astype(np.float32).ravel().tolist(), "VEC3", glb.FLOAT, glb.ARRAY_BUFFER),
        "TEXCOORD_0": contents.reading(np.c_[places[:, 0], 1.0 - places[:, 1]].astype(np.float32).ravel().tolist(),
                                       "VEC2", glb.FLOAT, glb.ARRAY_BUFFER),
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


def pieces_of(faces, part_of, *per_point):
    """Each part's own faces (renumbered) and its points' rows of every `per_point` array."""
    found = {}
    for part in np.unique(part_of):
        used, renumbered = np.unique(faces[part_of == part], return_inverse=True)
        found[int(part)] = (renumbered.reshape(-1, 3), *(values[used] for values in per_point))
    return found


def written(out, document, blob, bind, laid, maps):
    """The glTF: the dressed body's Person node, joints, skin and clips (joint keys only), the still's parts as the
    OUTFIT node and its far body bound at `bind`, every part in the still's own maps. `laid`: the still's welded
    `points`, `faces`, `part_of`, `weights` and `normals`, and its points split along the map's charts (`mapping`,
    each split point's welded one; `split_faces`; `places`)."""
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
    new["textures"] = [{"source": contents.picture(png(maps[role]))} for role in MAP_ROLES if role in maps]
    for part in PARTS:
        new["materials"].append(material_of(part, maps))
    points, faces, part_of, weights, normals = (laid[key] for key in ("points", "faces", "part_of", "weights",
                                                                       "normals"))
    mapping = laid["mapping"]
    near = [primitive(contents, piece_points, piece_faces, piece_weights, piece_normals, piece_places, part)
            for part, (piece_faces, piece_points, piece_weights, piece_normals, piece_places) in
            pieces_of(laid["split_faces"], part_of, points[mapping], weights[mapping], normals[mapping],
                      laid["places"]).items()]
    whole = trimesh.Trimesh(points, faces, process=False)
    thin = whole.simplify_quadric_decimation(face_count=FAR_TRIANGLES)
    nearest_face = cKDTree(whole.triangles_center).query(thin.triangles_center)[1]
    nearest_point = cKDTree(points).query(thin.vertices)[1]
    nearest_split = cKDTree(points[mapping]).query(thin.vertices)[1]
    far = [primitive(contents, piece_points, piece_faces, piece_weights, piece_normals, piece_places, part)
           for part, (piece_faces, piece_points, piece_weights, piece_normals, piece_places) in
           pieces_of(thin.faces, part_of[nearest_face], thin.vertices, weights[nearest_point], thin.vertex_normals,
                     laid["places"][nearest_split]).items()]
    for name, primitives in (("far", far), (OUTFIT, near)):
        new["meshes"].append({"name": name, "primitives": primitives})
        new["nodes"].append({"name": name, "mesh": len(new["meshes"]) - 1, "skin": 0})
        new["nodes"][0].setdefault("children", []).append(len(new["nodes"]) - 1)
    glb.write(out, glb.levels_apart(new, OUTFIT, "far"), contents)
    return {"far_triangles": int(len(thin.faces)), "triangles": int(len(faces))}


# --- the whole rig --------------------------------------------------------------------------------------------------

def taken_back(still_points, rig_points):
    """The map from the rig's frame back into the still's own (`stood_at` is a turn, a scale and a shift: solved from
    the still's points and the same points stood), where its own paint is read."""
    ones = np.c_[rig_points, np.ones(len(rig_points))]
    solved = np.linalg.lstsq(ones, still_points, rcond=None)[0]
    return lambda points: np.c_[points, np.ones(len(points))] @ solved


def rigged(still, dressed, rig_path, palette_path, out, faces=FACES, person=False):
    """The still rigged on the dressed body's skeleton into `out` (body.glb, rig.json); the record. A `person` has a
    head and clothes for parts (parts_of)."""
    document, blob, names, dressed_bind, parents = skeleton_of(dressed)
    rig = np.load(rig_path)
    body, body_weights = soma_on(rig, names, dressed_bind)
    raw, colours, source = still_of(still)
    thin = thinned(raw, faces)
    skin = trunk_skin(body, body_weights, names)
    # A person is a body, not a suit round one: stood at the body's own height, since a slimmer person than the SOMA
    # mean leaves most of its skin outside at every height and the fit stretches her (the stairwell woman: 58%
    # outside at 1.88 m, 66% at 1.78, her weights matched for 30% of her points)
    height, tried = ((round(float(np.ptp(body.vertices[:, 1])), 2), {}) if person else
                     fitted_height(thin, body, skin, names, dressed_bind))
    fitted = stood_at(thin, height, body, names, dressed_bind)
    if person:
        fitted = feet_fitted(fitted, dressed_feet(document, blob, names))
    bind, arm_turns = arms_turned(dressed_bind, names, parents, body, fitted)
    body, body_weights = soma_on(rig, names, bind)
    mesh = closed(fitted)
    colours = colours[cKDTree(raw.vertices).query(thin.vertices)[1]][cKDTree(fitted.vertices).query(mesh.vertices)[1]]
    part_of = parts_of(mesh, colours, body, names, bind, person)
    fit = landmarks_of(prop_rig.sampled(mesh), bind, names)
    weights, matched, smoothed = prop_rig.transferred(body, body_weights, mesh, np.array(names), fit)
    weights = off_the_shins(mesh.vertices, off_the_feet(mesh.vertices, weights, names, bind), names, bind)
    weights = rigid(mesh.vertices, mesh.faces, part_of, weights, names)
    weights = eased_cliffs(mesh.vertices, mesh.faces, weights, hard_points(mesh.faces, part_of, len(mesh.vertices)))
    out.mkdir(parents=True, exist_ok=True)
    tokens = json.loads(pathlib.Path(palette_path).read_text()).get("tokens", {})
    normals = mesh.vertex_normals
    mapping, split_faces, places = unwrapped(mesh.vertices, mesh.faces, normals)
    maps, grade = own_maps(mesh.vertices[mapping], split_faces, places, taken_back(thin.vertices, fitted.vertices),
                           source, tokens)
    laid = {"points": mesh.vertices, "faces": mesh.faces, "part_of": part_of, "weights": weights, "normals": normals,
            "mapping": mapping, "split_faces": split_faces, "places": places}
    sizes = written(out / "body.glb", document, blob, bind, laid, maps)
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
              "finish": OWN_TEXTURE, "maps": {role: list(picture.shape[:2]) for role, picture in maps.items()},
              "grade": grade,
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
    parser.add_argument("--person", action="store_true",
                        help="a person: a head and clothes, no helmet, visor or backpack")
    options = parser.parse_args()
    record = rigged(options.still, options.dressed, options.rig, options.palette, options.out, options.faces,
                    options.person)
    print(f"still rig: {record['height_m']} m, {record['triangles']} triangles, parts {record['parts']}, matched "
          f"{record['matched_share']:.0%}, stretch {({name: clip['stretch_most'] for name, clip in record['clips'].items()})}; "
          f"{options.out / 'rig.json'}", flush=True)


if __name__ == "__main__":
    main()
