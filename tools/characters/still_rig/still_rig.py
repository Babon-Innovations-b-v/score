"""A still model rigged as a player model (#128, owner 2026-11-18, of the paper's TRELLIS.2 astronaut: "why dont we use
these models for the astraunauts, that one looks way better"): a picture-made mesh with no skeleton put on a dressed
body's own skeleton, so it plays every clip and sim-body motion that body plays. Plain CPU geometry (numpy, scipy,
trimesh); no model runs.

    .venv/bin/python tools/characters/still_rig/still_rig.py <still.glb> <dressed body.glb> <clips rig.npz>
        <palette.json> <out folder> [--faces 60000] [--person] [--skin-stats <face skin stats.json>]

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
   A person's hands (`--person`; 2026-11-27: TRELLIS.2's fused hands read as claws and mittens curled against the
   coat and the thighs, and the skeleton has one joint a hand, so no weights can open them) are cut off
   (`hand_cut`: the arm's faces past the wrist, and its skin-painted ones up to the cuff, the skin read off the
   face, `face_skin`) and the whole route's relaxed hands with real fingers laid on in their place (`hands.py`'s
   file beside the clips rig; `hands_laid`: sized by the forearm, moved by their own weights onto the bind, and
   across the forearm into the middle of the sleeve's opening, `sleeve_offsets`; nothing left by the cut hanging
   from a hand or off the sleeve from the arm, `off_the_hands`; `with_hands`: the cut's holes closed with their rims
   smoothed, the lump's leftover skin paint on the cloth repainted, the hand part painted the photo's skin
   (`--skin-stats`, `photo_skin`; else the face's) with whole's flush and thin tones and its nails, `hand_paint`,
   `hand_roughness`), their stubs hidden in the sleeves.
6. The finish is the still's own paint (owner 2026-11-19, of the TRELLIS.2 astronaut beside the one laid in library
   surfaces a part: "this pure trellis is just so much better ... the segmentation of the visor isnt perf and the
   seams, all player models have this problem"; the library rule's written exception for player models): the rigged
   still is laid flat on one MAP map (`unwrapped`, xatlas), each texel reads the still's own base colour and metal and
   roughness nearest its point on the still's outer faces (`Source`, `own_maps`), so its seams, folds, panels and
   prints stay, and the base colour is graded toward the place's palette tokens as a made prop's paint is
   (score/stages/place_build/maker/grade.py). The parts keep only their joints and their `role`.
7. The glTF (`written`): the dressed body's skeleton and clips (its corrective morph keys left out: the still has no
   targets; a person's arms never brought in nearer its trunk than the still's own arms hang, `arms_kept_out`, and
   held further out a degree at a time while a hand goes into the clothes, `hands_cleared`), the
   still as its `work` node and a far body of FAR_TRIANGLES out of the file's default scene
   (people/glb.py levels_apart, #156); `stretch` measures the longest edge's
   growth on every frame of every clip.

Writes <out>/body.glb, <out>/rig.json (the fit, the parts' triangles, the matched share, the grade's colour groups,
each clip's stretch and, for a person, its hands' cut and skin and each clip's hands: the degrees raised and how deep
in the clothes).
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
sys.path.insert(0, str(HERE))

import glb  # noqa: E402  (people/glb.py, the glTF writer)
import prop_rig  # noqa: E402
import skel_usd  # noqa: E402
import hands as relaxed_hands  # noqa: E402  (still_rig/hands.py: the whole route's hands beside the clips rig)

GRADE = HERE.parents[2] / "score/stages/place_build/maker/grade.py"  # the made props' grade, loaded by its file

FACES = 60000
# fast-simplification's aggressiveness (its default 7): a generated person's garments are thin double sheets, and at 7
# the thinning folds them onto themselves (the stairwell woman's swapped model, 504k outer faces thinned to 100k: 11.7%
# of its edges folded past 150 degrees against 0.27% unthinned, drawn as fins and dark flecks over her puffer and
# jeans, round 5, 2026-11-27); 2 keeps 300k at 1.3%
THIN_AGGRESSION = 2
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
PARTS = ("suit", "helmet", "visor", "backpack", "head", "hand")
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
HAND_TIP_UNDER_WRIST = 0.20  # metres: the arm's points are labelled on down to the fingertips, this far under the wrist
HAND_HALF = 0.03  # metres: under the crotch, a point this near the arm's line or beyond it is the hand's (2026-11-27:
# a hand resting on the thigh, cut with it by every slice, was the leg's; 998 of the hoodie man's 1429 hand points
# and 267 of the older woman's 650 hung a fifth or more from the thighs and pulled the hands into the trousers)
# A person's clips keep each arm out as far from its trunk as the still's own arm hangs (`arms_kept_out`; 2026-11-27:
# the dressed body's walk brought the hands 3 to 6 degrees off the trunk, the coat's and overshirt's own sleeves hang
# 9 to 20 out, so the hands pressed into the coat and the thighs):
ARM_SOFT_DEGREES = 2.0  # the floor is a soft maximum this wide (no kink where the swing meets it)
ARM_HANGING = (0.5, 0.8)  # the arm's downward share (cosine) from which the floor starts to hold and holds whole
ARM_ACROSS_DEGREES = 5.0  # an arm brought across the trunk past straight down by this much is a pose (a hand on the
# far knee on the bench), never pushed out
CLIFF_ROUNDS, CLIFF_ALPHA = 200, 0.5  # its rounds (about 3 cm of spread on 3 mm edges), and how far towards its
# neighbours' mean a point moves each round
OUTFIT = "work"  # the dressed body's own outfit node, which skel_usd shows (DEFAULT_WORN)
# A person's hands (`hands_laid`, `hand_cut`; 2026-11-27: TRELLIS.2's fused hands read as claws and mittens curled
# against the coat and the thighs) are cut off the still and the whole route's relaxed hands (`hands.py`) laid on:
HAND_CUFF_OVER = 0.02  # metres above the wrist (the Hand joint) down from which the arm's faces may be the hand's
HAND_SLEEVE = (0.05, 0.15)  # metres above the wrist the sleeve's colour is read between (`cloth_round`)
HAND_AROUND = 0.15  # metres from the wrist the cloth beside the hand (off the arm) is read within
HAND_SETTLE = 3  # rounds of neighbours' votes on which faces are the hand's (`hand_pieces`)
HAND_PIECE = 30  # faces: a piece of hand smaller than this is a speck of skin paint on the cloth
SKIN_NEAR = 0.12  # a face whose paint lies this near the person's skin (RGB, 0 to 1) is skin
SLEEVE_RING = (-0.12, -0.02)  # metres along the forearm from the wrist the sleeve's paint is read between
PAINT_NEIGHBOURS = 12  # the kept points whose paint a point's is averaged over when told sleeve from cloth
TEAR_PASSES = 3
TEAR = 0.3  # a face whose corners' arm shares differ this much or more spans a sleeve and the cloth it touched
# (the hoodie man's fused sleeve points half on the forearm beside the thigh's: 0.49 apart, stretched 35 times)
ARM_LEFT_SHARE = 0.5  # a point keeps its own weights off the arm when this much or more of them is off the arms
CLOTH_NEIGHBOURS = 8  # the cloth points off the arms whose weights a point taken off the hand takes, averaged
HAND_RIM_REACH = 0.12  # metres from the wrist the sleeve's opening left by the cut is read within (`sleeve_offsets`)
FACE_HALF, FACE_FRONT = 0.03, 0.05  # metres: the face's middle strip the skin is read from (`face_skin`): its half
FACE_SPAN = (0.04, 0.06)  # width, how far before the Head joint, and how far under and over it
FACE_LEAST = 50  # points the strip holds at least
HAND_FLUSH_TINT = (0.05, -0.03, -0.03)  # the base colour's change at whole's full flush towards the fingertips
HAND_THIN_TINT = (-0.03, -0.01, 0.02)  # and at its full thin skin (the back of the hand, the inner wrist)
HAND_METAL_ROUGHNESS = (1.0, 0.55, 0.0)  # glTF's packing (occlusion, roughness, metal): skin
NAIL_METAL_ROUGHNESS = (1.0, 0.25, 0.0)  # and a nail's, glossier
NAIL_COLOUR = (0.93, 0.78, 0.74)  # a nail's pale pink over its bed
NAIL_SHARE = 0.45  # how far a nail's base colour goes from the skin's to NAIL_COLOUR
CUFF_SMOOTH_ROUNDS = 8  # rounds the cut holes' rims are smoothed along themselves (`smoothed_rims`)
RIM_SHARE = 0.5  # how far a rim point moves to its rim neighbours' middle each even round
RIM_BACK = 0.53  # and away from it each odd round
PATCH_REACH = 0.05  # metres from the cut a leftover patch of the lump's skin paint is looked for within
HAND_NEAR = 0.03  # metres: clothes within this of a hand point are read for its depth in them (`hands_in`)
HAND_FRAMES = 3  # every this many frames of a clip is read for the hands' depth
HAND_REACH = 0.45  # metres: the clothes this near a hand at the bind are the ones its depth is read in
HAND_CLEAR = 0.003  # metres: a hand this little in the clothes is out of them (the shell's own noise)
HAND_CLEAR_MOST = 12.0  # degrees at most a hanging arm is turned further out to bring its hand out


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
                                                     target_reduction=max(0.0, 1.0 - faces / len(mesh.faces)),
                                                     agg=THIN_AGGRESSION)
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


def abduction(worlds, bind, names, side):
    """Each frame's arm abduction in degrees (worlds: frames x joints x 4 x 4): the hand off its shoulder (the Arm
    joint) in the chest's frame as it is at the bind, its angle out from straight down across the trunk; and the
    arm's downward share (cosine)."""
    chest, arm, hand = (names.index(name) for name in ("Chest", side + "Arm", side + "Hand"))
    trunk = bind[chest, :3, :3] @ np.linalg.inv(worlds[:, chest, :3, :3])
    off = np.einsum("fab,fb->fa", trunk, worlds[:, hand, :3, 3] - worlds[:, arm, :3, 3])
    sign = prop_rig.SIDES[side]
    return (np.degrees(np.arctan2(sign * off[:, 0], -off[:, 1])),
            -off[:, 1] / np.maximum(np.linalg.norm(off, axis=1), 1e-12))


def arms_kept_out(worlds, bind, names, parents, extra=None):
    """A clip's joint worlds (frames x joints x 4 x 4) with each arm turned out across the trunk (about the chest's
    forward axis, at the shoulder) wherever it comes in nearer than the still's own arm hangs at the bind, and `extra`
    degrees further ({side: degrees}, `hands_cleared`)
    (`abduction`; a soft maximum ARM_SOFT_DEGREES wide, held only while the arm hangs down, ARM_HANGING, on its own
    side of the trunk, ARM_ACROSS_DEGREES), every joint
    under it turned along; and {Arm joint: its new local rotations as glTF quaternions (frames x 4)}. The dressed
    body's walk swung the hands 3 to 6 degrees off the trunk; the coat's and the overshirt's sleeves hang 9 to 20 out
    and the hands went into them (2026-11-27)."""
    from scipy.spatial.transform import Rotation
    out, locals_ = np.array(worlds, float), {}
    chest = names.index("Chest")
    for side, sign in prop_rig.SIDES.items():
        floor = float(abduction(bind[None], bind, names, side)[0][0])
        angle, hanging = abduction(out, bind, names, side)
        raised = floor + ARM_SOFT_DEGREES * np.logaddexp(0.0, (angle - floor) / ARM_SOFT_DEGREES)
        share = (np.clip((hanging - ARM_HANGING[0]) / (ARM_HANGING[1] - ARM_HANGING[0]), 0.0, 1.0)
                 * np.clip(1.0 + angle / ARM_ACROSS_DEGREES, 0.0, 1.0))
        turn = np.radians((raised - angle + (extra or {}).get(side, 0.0)) * share) * sign
        forward = np.einsum("fab,b->fa", out[:, chest, :3, :3] @ bind[chest, :3, :3].T, [0.0, 0.0, 1.0])
        arm = names.index(side + "Arm")
        moved = np.repeat(np.eye(4)[None], len(out), axis=0)
        moved[:, :3, :3] = Rotation.from_rotvec(forward * turn[:, None]).as_matrix()
        pivot = out[:, arm, :3, 3].copy()
        moved[:, :3, 3] = pivot - np.einsum("fab,fb->fa", moved[:, :3, :3], pivot)
        for joint in below(arm, parents):
            out[:, joint] = moved @ out[:, joint]
        parent = out[:, parents[arm], :3, :3]
        locals_[arm] = Rotation.from_matrix(np.einsum("fba,fbc->fac", parent, out[:, arm, :3, :3])).as_quat()
    return out, locals_


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
    SLEEVE_HALF of that line or beyond it the arm's, down to the fingertips (HAND_TIP_UNDER_WRIST; under the crotch
    within HAND_HALF: a hand resting on the thigh), the limbs prop_rig.transferred matches on the arm alone."""
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
        tip = bind[names.index(side + "Hand"), 1, 3] - HAND_TIP_UNDER_WRIST
        half = np.where(points[:, 1] > crotch, SLEEVE_HALF, HAND_HALF)
        sleeve = (sign * points[:, 0] > sign * middle_x - half) & (points[:, 1] <= top) & (
            points[:, 1] >= tip) & (sign * points[:, 0] > 0)
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


# --- a person's hands -----------------------------------------------------------------------------------------------

def hands_file(rig_path):
    """The relaxed hands written beside the clips rig (`hands.py`), read; refused, naming how to make them, when
    there are none."""
    path = pathlib.Path(rig_path).parent / relaxed_hands.FILE
    if not path.exists():
        raise StillError(f"{path}: no relaxed hands beside the clips rig; make them with "
                         f"`python -m tools.characters.still_rig.hands <face.npz> <body.npz> {rig_path}`")
    return np.load(path)


def hands_laid(hands, names, clips_bind, bind):
    """The relaxed hands (`hands.py`'s file, at the clips rig's bind `clips_bind` and in its joint order) laid on
    `bind`: each side's hand sized about its wrist by the forearm's length on `bind` over the clips rig's, then moved
    by its own weights (linear blend skinning) onto `bind`. {side: (points, faces, weights in `names`' order,
    tones)}."""
    order = [[str(name) for name in hands["names"]].index(name) for name in names]
    clips_bind = np.asarray(clips_bind, float)[order]
    found = {}
    for side in relaxed_hands.SIDES:
        hand, fore = names.index(side + "Hand"), names.index(side + "ForeArm")
        scale = (np.linalg.norm(bind[hand, :3, 3] - bind[fore, :3, 3])
                 / np.linalg.norm(clips_bind[hand, :3, 3] - clips_bind[fore, :3, 3]))
        weights = np.asarray(hands[f"{side}.weights"], float)[:, order]
        wrist = clips_bind[hand, :3, 3]
        sized = wrist + (np.asarray(hands[f"{side}.points"], float) - wrist) * scale
        found[side] = (prop_rig.skinned_source(sized, weights, clips_bind, bind),
                       np.asarray(hands[f"{side}.faces"], np.int64), weights, np.asarray(hands[f"{side}.tones"], float))
    return found


def face_skin(points, faces, part_of, colours, names, bind):
    """The person's own skin colour, read off the middle of its face (the head part's points within FACE_HALF of the
    head's middle line, FACE_FRONT before it, from FACE_SPAN under the Head joint to over it): the median. TRELLIS.2's
    hands are no place to read it: the hoodie man's lumps read near black (0.09) at their tips and the older woman's
    right hand as her coat's camel (2026-11-27)."""
    head = bind[names.index("Head"), :3, 3]
    on_head = np.zeros(len(points), bool)
    on_head[np.unique(faces[part_of == PARTS.index("head")])] = True
    strip = (on_head & (np.abs(points[:, 0] - head[0]) < FACE_HALF) & (points[:, 2] > head[2] + FACE_FRONT)
             & (points[:, 1] > head[1] - FACE_SPAN[0]) & (points[:, 1] < head[1] + FACE_SPAN[1]))
    if strip.sum() < FACE_LEAST:
        raise StillError(f"the face shows {int(strip.sum())} points to read the skin from")
    return np.median(colours[strip], axis=0)


def hand_cut(points, faces, colours, weights, names, bind, skin):
    """Which of the still's faces are its hands, to be cut off (TRELLIS.2's fused lumps): of the faces hanging wholly
    from a side's forearm and hand (strongest joint) and lying wholly under HAND_CUFF_OVER above the wrist or past it,
    those whose paint lies nearer the person's `skin` (`face_skin`) than the cloth round the hand (`cloth_round`),
    settled by their neighbours (`hand_pieces`). Cut by place alone, a ring of the older woman's coat and the hoodie man's
    trousers went with each hand, and the hollow inside showed black through the holes (2026-11-27)."""
    strongest = np.array(names)[weights.argmax(1)]
    paint = colours[faces].mean(1)
    middles = points[faces].mean(1)
    pairs = trimesh.Trimesh(points, faces, process=False).face_adjacency
    cut = np.zeros(len(faces), bool)
    for side in relaxed_hands.SIDES:
        wrist, elbow = (bind[names.index(side + joint), :3, 3] for joint in ("Hand", "ForeArm"))
        along = (points - wrist) @ ((wrist - elbow) / np.linalg.norm(wrist - elbow))
        arm = np.isin(strongest, [side + "ForeArm", side + "Hand"])[faces].all(1)
        if not (arm & (along[faces].min(1) > 0.0)).any():
            raise StillError(f"the {side.lower()} arm reaches no hand past its wrist")
        lying = arm & (along[faces].min(1) > -HAND_CUFF_OVER)
        hand = lying & (np.linalg.norm(paint - skin, axis=1) < cloth_distance(paint, cloth_round(
            paint, middles, arm, along[faces].mean(1), wrist, skin)))
        cut |= hand_pieces(hand, lying, pairs)
    return cut


def cloth_round(paint, middles, arm, along, wrist, skin):
    """The cloth colours round a hand: the sleeve's (the arm's faces HAND_SLEEVE above the wrist) and whatever lies
    beside the hand off the arm within HAND_AROUND of the wrist (a coat's flank, the trousers), their medians, a
    median within SKIN_NEAR of the `skin` left out (a bare leg is no cloth)."""
    sleeve = arm & (along < -HAND_SLEEVE[0]) & (along > -HAND_SLEEVE[1])
    beside = ~arm & (np.linalg.norm(middles - wrist, axis=1) < HAND_AROUND)
    found = [np.median(paint[place], axis=0) for place in (sleeve, beside) if place.any()]
    return [colour for colour in found if np.linalg.norm(colour - skin) >= SKIN_NEAR]


def cloth_distance(paint, cloths):
    """Each paint's distance to the nearest of `cloths` (infinite with none)."""
    if not cloths:
        return np.full(len(paint), np.inf)
    return np.min([np.linalg.norm(paint - cloth, axis=1) for cloth in cloths], axis=0)


def hand_pieces(hand, lying, pairs):
    """`hand` (faces) among the `lying` ones settled: HAND_SETTLE rounds of each lying face taking its and its
    neighbours' (face adjacency `pairs`) majority; then a hand piece under HAND_PIECE faces is cloth (a speck of skin
    paint on a sleeve), and a piece of cloth the hand closes round, touching no face but the hand's (a shaded crevice
    of the lump, its faces' paint between the two), is the hand's."""
    found = hand.copy()
    for _ in range(HAND_SETTLE):
        votes, counts = found.astype(float), np.ones(len(found))
        for first, second in ((pairs[:, 0], pairs[:, 1]), (pairs[:, 1], pairs[:, 0])):
            np.add.at(votes, first, found[second])
            np.add.at(counts, first, 1.0)
        found = np.where(lying, votes / counts > 0.5, found)
    for wanted in (True, False):
        members = lying & (found == wanted)
        inside = pairs[members[pairs].all(1)]
        _, piece = connected_components(sparse_graph(inside, len(found)), directed=False)
        if wanted:
            found[members & (np.bincount(piece[members], minlength=piece.max() + 1)[piece] < HAND_PIECE)] = False
            continue
        open_side = np.zeros(piece.max() + 1, bool)
        for first, second in ((pairs[:, 0], pairs[:, 1]), (pairs[:, 1], pairs[:, 0])):
            leaving = members[first] & ~members[second] & ~found[second]
            open_side[piece[first[leaving]]] = True
        found[members & ~open_side[piece]] = True
    return found & lying


def sleeve_offsets(points, faces, cut, weights, names, bind):
    """Where each sleeve's opening lies off its wrist, across the forearm (metres, {side: vector}): the middle of the
    open edges the `cut` leaves on that side's forearm and hand (strongest joint) within HAND_RIM_REACH of the wrist,
    less its part along the forearm; nought where there are none. The bind's wrist is the dressed body's, turned onto
    the sleeve's middle line up the arm (`arms_turned`), and the older woman's and the hoodie man's cuffs open 3 to 6
    cm in from it towards the body (2026-11-27): a hand laid at the joint stood beside its sleeve, its stub bare."""
    kept = faces[~cut]
    edges = np.sort(np.concatenate([kept[:, [0, 1]], kept[:, [1, 2]], kept[:, [2, 0]]]), axis=1)
    unique, counts = np.unique(edges, axis=0, return_counts=True)
    rims = unique[counts == 1]
    strongest = np.array(names)[weights.argmax(1)]
    found = {}
    for side in relaxed_hands.SIDES:
        wrist, elbow = (bind[names.index(side + joint), :3, 3] for joint in ("Hand", "ForeArm"))
        along = (wrist - elbow) / np.linalg.norm(wrist - elbow)
        mine = np.isin(strongest[rims], [side + "ForeArm", side + "Hand"]).all(1)
        middles = points[rims[mine]].mean(1)
        middles = middles[np.linalg.norm(middles - wrist, axis=1) < HAND_RIM_REACH]
        off = middles.mean(0) - wrist if len(middles) else np.zeros(3)
        found[side] = off - (off @ along) * along
    return found


def off_the_hands(points, faces, cut, weights, colours, names, bind):
    """The weights with nothing the `cut` leaves hanging from a hand joint (the hand is replaced) and no other garment
    hanging from the arm below the wrist; and which points were taken off the arm. Of each side's kept points hanging
    at all from its Hand, or from its ForeArm past the wrist, those whose paint (`colours`, each point's averaged over
    its PAINT_NEIGHBOURS nearest kept points: a plaid's dark stripes are no trousers) lies nearer the cloth beside the
    hand (`cloth_round`'s colours off the arm) than the sleeve's are taken off: they lose that forearm's and hand's
    weights, and keep the rest of their own when ARM_LEFT_SHARE or more of it is off every arm, else take the mean
    weights of their CLOTH_NEIGHBOURS nearest kept points hanging from no arm; the rest (the sleeve, and everything
    where the sleeve and the cloth beside it are one colour) ride the forearm, the hand's weight moved onto it. Taken
    off by place as well (off the sleeve's line), the older woman's camel coat, one colour with her sleeves and fused
    to them, kept its flanks but her cuffs tore off as flaps beside it and her hands hung bare below them; so a
    one-colour fused coat still swings its flanks with the arms (2026-11-27, an open gap). A fused person's arm is labelled down to its fingertips (`fused_landmarks`), so the
    trousers the hoodie man's hands rested on hung from the hands; with the lumps cut they swung out with the arm as
    dark wings at the hips (2026-11-27)."""
    names = [str(name) for name in names]
    found = weights.copy()
    kept = np.zeros(len(points), bool)
    kept[np.unique(faces[~cut])] = True
    arms = [names.index(side + joint) for side in relaxed_hands.SIDES for joint in ("Arm", "ForeArm", "Hand")
            if side + joint in names]
    clear = kept & (weights[:, arms].sum(1) < 0.1)
    tree = cKDTree(points[clear])
    kept_index = np.flatnonzero(kept)
    paint = np.zeros_like(colours)
    paint[kept] = colours[kept_index[cKDTree(points[kept]).query(points[kept], PAINT_NEIGHBOURS)[1]]].mean(1)
    strongest = weights.argmax(1)
    taken_off = np.zeros(len(points), bool)
    for side in relaxed_hands.SIDES:
        hand, fore = names.index(side + "Hand"), names.index(side + "ForeArm")
        wrist, elbow = bind[hand, :3, 3], bind[fore, :3, 3]
        along = (points - wrist) @ ((wrist - elbow) / np.linalg.norm(wrist - elbow))
        taken = kept & ((weights[:, hand] > 0.0) | ((weights[:, fore] > 0.0) & (along > 0.0)))
        sleeve_ring = kept & (strongest == fore) & (along > SLEEVE_RING[0]) & (along < SLEEVE_RING[1])
        beside = clear & (np.linalg.norm(points - wrist, axis=1) < HAND_AROUND)
        off = np.zeros(len(points), bool)
        if sleeve_ring.any() and beside.any():
            sleeve_paint, beside_paint = np.median(paint[sleeve_ring], 0), np.median(paint[beside], 0)
            if np.linalg.norm(sleeve_paint - beside_paint) >= SKIN_NEAR:  # two garments to tell apart
                off = taken & (np.linalg.norm(paint - beside_paint, axis=1) < np.linalg.norm(paint - sleeve_paint,
                                                                                            axis=1))
        sleeve = taken & ~off
        found[sleeve, fore] += found[sleeve, hand]
        found[sleeve, hand] = 0.0
        found[off, fore] = found[off, hand] = 0.0
        left = found.sum(1) - found[:, arms].sum(1) >= ARM_LEFT_SHARE  # this much of its own off every arm
        own = np.flatnonzero(off & left)
        found[own] /= found[own].sum(1, keepdims=True)
        cloth = np.flatnonzero(off & ~left)
        if len(cloth):
            _, nearest = tree.query(points[cloth], CLOTH_NEIGHBOURS)
            found[cloth] = weights[np.flatnonzero(clear)[nearest]].mean(1)
        taken_off |= off
    return found, taken_off


def arm_share(weights, names, joints=("Arm", "ForeArm", "Hand")):
    """Each point's weight on the arms' `joints` (both sides)."""
    names = [str(name) for name in names]
    return weights[:, [names.index(side + joint) for side in relaxed_hands.SIDES for joint in joints
                       if side + joint in names]].sum(1)


def torn(points, faces, weights, names, near, *per_point, passes=TEAR_PASSES):
    """The surface torn where a sleeve meets the cloth it was fused to (`off_the_hands` leaves the cliff sharp, and
    the fused arm's labels left others): a face whose corners' arm shares (`arm_share`) differ by TEAR or more, one
    of them TEAR or more on a forearm or hand, among the faces `near` (those touching what `off_the_hands` took off
    the arm: elsewhere a fused sleeve's blend into the coat is no tear, and torn there the older woman's sleeves tore
    into flaps), goes
    to the arm side when their mean is over the middle of their range, else to the cloth's, and its corners on the
    other side of that middle are copies of themselves taking the mean weights of its own side's corners; again, up
    to `passes` times, while a face spans TEAR (a corner between its two sides stays on one). Joined, every such face stretched with the swinging forearm: eased either way, the hoodie man's
    walk stretched edges by 15 cm (cloth half on the arm), or his cuffs hung half from his hips and his hands, turned
    out of his trousers, stood 5 cm beside them (2026-11-27). (points, faces, weights, [each of `per_point` with
    the copies' rows])."""
    share = arm_share(weights, names)
    corner = share[faces]
    low = (arm_share(weights, names, ("ForeArm", "Hand"))[faces] >= TEAR).any(1)
    bridge = np.flatnonzero((corner.max(1) - corner.min(1) >= TEAR) & low & near)
    if not len(bridge):
        return points, faces, weights, list(per_point)
    faces = faces.copy()
    middle = (corner[bridge].max(1) + corner[bridge].min(1)) / 2.0
    on_arm = corner[bridge].mean(1) >= middle
    copies, rows, new_weights = {}, [], []
    for face, arm, cut_at in zip(bridge, on_arm, middle):
        mine = (share[faces[face]] >= cut_at) == arm
        mean = weights[faces[face][mine]].mean(0)
        for slot in np.flatnonzero(~mine):
            key = (int(faces[face, slot]), bool(arm))
            if key not in copies:
                copies[key] = len(points) + len(rows)
                rows.append(key[0])
                new_weights.append(mean)
            faces[face, slot] = copies[key]
    rows = np.array(rows)
    found = (np.r_[points, points[rows]], faces, np.r_[weights, np.array(new_weights)],
             [np.r_[values, values[rows]] for values in per_point])
    return torn(*found[:3], names, near, *found[3], passes=passes - 1) if passes > 1 else found


def tears_closed(points, faces, part_of, weights, names, torn_from, *per_point):
    """The holes `torn` leaves closed on each side: its open edges between points it copied or copied from
    (`torn_from`, each point's original, itself where it is none), each edge the arm's when both its points hang half
    or more from a forearm or hand (`arm_share`), else the cloth's, each side's connected runs fanned from their middle
    (turned as the face they border, as `closed`), the middle hanging and painted as its run on average: open, the
    shell's hollow showed black through the older woman's coat and the hoodie man's trousers where they tore from the
    sleeves (2026-11-27). (points, faces, part_of, weights, [each of `per_point` with the middles' rows])."""
    involved = np.zeros(len(points), bool)
    involved[torn_from[torn_from != np.arange(len(points))]] = True
    involved[np.flatnonzero(torn_from != np.arange(len(points)))] = True
    edges = np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
    keys = edges[:, 0].astype(np.int64) * len(points) + edges[:, 1]
    back = edges[:, 1].astype(np.int64) * len(points) + edges[:, 0]
    border = edges[~np.isin(keys, back) & involved[edges].all(1)]
    if not len(border):
        return points, faces, part_of, weights, list(per_point)
    on_arm = (arm_share(weights, names)[border] >= 0.5).all(1)
    middles, fans, rows = [], [], []
    for side in (True, False):
        mine = border[on_arm == side]
        if not len(mine):
            continue
        _, run_of = connected_components(sparse_graph(mine, len(points)), directed=False)
        for run in np.unique(run_of[mine[:, 0]]):
            run_edges = mine[run_of[mine[:, 0]] == run]
            if len(run_edges) < 2:
                continue
            members = np.unique(run_edges)
            number = len(points) + len(middles)
            middles.append(points[members].mean(0))
            rows.append(members)
            fans += [[second, first, number] for first, second in run_edges]
    if not middles:
        return points, faces, part_of, weights, list(per_point)
    mean_of = lambda values: np.array([np.nanmean(values[members], axis=0) if np.isfinite(values[members]).any()
                                       else np.full(values.shape[1:], np.nan) for members in rows])  # noqa: E731
    return (np.r_[points, np.array(middles)], np.r_[faces, np.array(fans)],
            np.r_[part_of, np.full(len(fans), PARTS.index("suit"))], np.r_[weights, mean_of(weights)],
            [np.r_[values, mean_of(values)] for values in per_point])


def hand_paint(skin, tones):
    """A laid hand's base colour at each point: its skin's colour, flushed towards the fingertips and paler blue over
    the thin skin by whole's hand tones (flush, thin), and over a nail (the third tone, `hands.nails`, where there is
    one) NAIL_SHARE of the way to NAIL_COLOUR."""
    found = skin + tones[:, :1] * np.array(HAND_FLUSH_TINT) + tones[:, 1:2] * np.array(HAND_THIN_TINT)
    if tones.shape[1] > 2:
        found += tones[:, 2:3] * NAIL_SHARE * (np.array(NAIL_COLOUR) - found)
    return np.clip(found, 0, 1)


def hand_roughness(tones):
    """A laid hand's metal and roughness at each point (glTF's packing): skin's HAND_METAL_ROUGHNESS, a nail's
    NAIL_METAL_ROUGHNESS (the nail's third tone, where there is one)."""
    nail = tones[:, 2:3] if tones.shape[1] > 2 else np.zeros((len(tones), 1))
    return np.array(HAND_METAL_ROUGHNESS) + nail * (np.array(NAIL_METAL_ROUGHNESS) - np.array(HAND_METAL_ROUGHNESS))


def smoothed_rims(points, fans, rounds=CUFF_SMOOTH_ROUNDS):
    """`points` with the rim points of the fans closing the cut's holes (each fan face a rim edge and its loop's
    middle) moved RIM_SHARE of the way to their two rim neighbours' middle and then RIM_BACK away from it, `rounds`
    times (Taubin's smoothing: the jags go, the opening does not shrink): the cut ran along the still's own triangles,
    and the sleeve's edge stood jagged round the laid hand's wrist (2026-11-27)."""
    found = points.copy()
    rim = np.unique(fans[:, :2])
    for step in range(rounds):
        total, count = np.zeros_like(found), np.zeros(len(found))
        for first, second in ((fans[:, 0], fans[:, 1]), (fans[:, 1], fans[:, 0])):
            np.add.at(total, first, found[second])
            np.add.at(count, first, 1.0)
        middle = total[rim] / np.maximum(count[rim], 1.0)[:, None]
        found[rim] += (RIM_SHARE if step % 2 == 0 else -RIM_BACK) * (middle - found[rim])
    return found


def lump_patches(points, colours, cut_points, skin, sides):
    """Which of the kept still's points are leftover patches of a hand lump's skin paint (on the coat or the trousers
    beside the hand, crumpled pink on the older woman's coat, 2026-11-27): within PATCH_REACH of a point of the cut,
    and nearer the `skin` paint than the cloth round them there (the median paint of the points so near that side's
    cut, `sides` each cut point's side, that lie SKIN_NEAR or more from the skin)."""
    found = np.zeros(len(points), bool)
    if not len(cut_points):
        return found
    distance, nearest = cKDTree(cut_points).query(points)
    near = distance < PATCH_REACH
    clothy = np.linalg.norm(colours - skin, axis=1) >= SKIN_NEAR
    for side in np.unique(sides):
        mine = near & (sides[nearest] == side)
        if not (mine & clothy).any():
            continue
        cloth = np.median(colours[mine & clothy], axis=0)
        found |= mine & (np.linalg.norm(colours - skin, axis=1) < np.linalg.norm(colours - cloth, axis=1))
    return found


def with_hands(points, faces, part_of, weights, colours, cut, laid, skin, hand_skin=None):
    """The still with its `cut` faces off (points no face uses dropped), the holes they leave closed by fans
    (`closed`: where a lump joined the trousers or a coat's flank, and the sleeve's opening, which the laid hand's
    stub passes through; open, the shell's hollow showed black), their rims smoothed (`smoothed_rims`), each fan's
    middle hanging as its loop on average and painted as its loop's cloth (its points away from the `skin` paint: the
    lump's pink rim smeared the older woman's coat), a rim point in the skin paint painted so too, the lump's leftover
    skin patches (`lump_patches`) painted their nearest cloth point's paint, and the `laid` hands (`hands_laid`) added
    as the hand part, painted `hand_skin` (the person's photo skin; else `skin`, the face's paint) by `hand_paint`:
    (points, faces, part_of, weights, each point's laid paint or NaN where the still's own is read, each point's laid
    metal and roughness or NaN off the hands)."""
    used, renumbered = np.unique(faces[~cut], return_inverse=True)
    still = trimesh.Trimesh(points[used], renumbered.reshape(-1, 3), process=False)
    shut = closed(still)
    fans = shut.faces[len(still.faces):]
    middles = len(shut.vertices) - len(still.vertices)
    loop = fans[:, 2] - len(still.vertices)
    shut_points = smoothed_rims(shut.vertices, fans)
    rim_sum, rim_count = np.zeros((middles, 3)), np.zeros(middles)
    np.add.at(rim_sum, loop, shut_points[fans[:, 0]])
    np.add.at(rim_count, loop, 1.0)
    shut_points[len(still.vertices):] = rim_sum / rim_count[:, None]
    cloth = np.linalg.norm(colours[used] - skin, axis=1) >= SKIN_NEAR  # a rim point not in the lump's skin paint
    loop_weights, loop_paint = np.zeros((middles, weights.shape[1])), np.zeros((middles, 3))
    counts, cloth_counts = np.zeros(middles), np.zeros(middles)
    for corner in (0, 1):
        np.add.at(loop_weights, loop, weights[used][fans[:, corner]])
        np.add.at(counts, loop, 1.0)
        on_cloth = cloth[fans[:, corner]]
        np.add.at(loop_paint, loop[on_cloth], colours[used][fans[on_cloth, corner]])
        np.add.at(cloth_counts, loop[on_cloth], 1.0)
    loop_paint = np.where(cloth_counts[:, None] > 0, loop_paint / np.maximum(cloth_counts, 1.0)[:, None],
                          np.nan)
    paint = np.full((len(shut.vertices), 3), np.nan)
    paint[len(still.vertices):] = loop_paint
    for corner in (0, 1):
        rim = fans[:, corner]
        paint[rim] = np.where(cloth[rim][:, None], colours[used][rim], loop_paint[loop])
    cut_points = np.unique(faces[cut])
    if len(cut_points) and laid:
        hands_middles = np.array([hand[0].mean(0) for hand in laid.values()])
        sides = cKDTree(hands_middles).query(points[cut_points])[1]
        patch = lump_patches(points[used], colours[used], points[cut_points], skin, sides)
        source = np.flatnonzero(~patch & cloth)
        if patch.any() and len(source):
            paint[np.flatnonzero(patch)] = colours[used][source[cKDTree(points[used][source]).query(
                points[used][patch])[1]]]
    all_points, all_faces = [shut_points], [shut.faces]
    all_weights = [np.r_[weights[used], loop_weights / counts[:, None]]]
    all_paint, all_rough = [paint], [np.full((len(shut.vertices), 3), np.nan)]
    parts, count = [np.r_[part_of[~cut], np.full(len(fans), PARTS.index("suit"))]], len(shut.vertices)
    for side, (hand_points, hand_faces, hand_weights, tones) in laid.items():
        all_points.append(hand_points)
        all_faces.append(hand_faces + count)
        all_weights.append(hand_weights)
        all_paint.append(hand_paint(skin if hand_skin is None else hand_skin, tones))
        all_rough.append(hand_roughness(tones))
        parts.append(np.full(len(hand_faces), PARTS.index("hand")))
        count += len(hand_points)
    return (np.concatenate(all_points), np.concatenate(all_faces), np.concatenate(parts),
            np.concatenate(all_weights), np.concatenate(all_paint), np.concatenate(all_rough))


def hands_depth(points, faces, part_of, order, kept, names):
    """A reader of how deep the hands go into the clothes over a clip: `depth(moves)` gives {side: metres}, the most
    any of that hand's points lies under the nearest clothes point within HAND_NEAR of it along that point's normal
    (posed with it), on every HAND_FRAMES-th frame; the clothes on the hand's own arm left out (its sleeve holds the
    wrist's stub), and only the clothes within HAND_REACH of either hand at the bind read."""
    normals = trimesh.Trimesh(points, faces, process=False).vertex_normals
    hand = np.unique(faces[part_of == PARTS.index("hand")])
    clothes = np.setdiff1d(np.unique(faces[part_of != PARTS.index("hand")]), hand)
    clothes = clothes[np.isfinite(cKDTree(points[hand]).query(points[clothes], distance_upper_bound=HAND_REACH)[0])]
    joint_names = np.array(names)
    hand_side = np.where(np.char.startswith(joint_names[order[hand, 0]], "Left"), "Left", "Right")
    strongest_clothes = joint_names[order[clothes, 0]]
    own = {side: (hand[hand_side == side], clothes[~np.isin(strongest_clothes, [
        side + joint for joint in ("Arm", "ForeArm", "Hand")])]) for side in relaxed_hands.SIDES}
    read = np.union1d(hand, clothes)
    index = np.full(len(points), -1)
    index[read] = np.arange(len(read))

    def depth(moves):
        found = {side: 0.0 for side in relaxed_hands.SIDES}
        for frame in range(0, len(moves), HAND_FRAMES):
            blended = np.einsum("pk,pkab->pab", kept[read], moves[frame][order[read]])[:, :3]
            moved = np.einsum("pab,pb->pa", blended, np.c_[points[read], np.ones(len(read))])
            turned = np.einsum("pab,pb->pa", blended[:, :, :3], normals[read])
            turned /= np.maximum(np.linalg.norm(turned, axis=1, keepdims=True), 1e-12)
            for side, (mine, others) in own.items():
                if not len(mine) or not len(others):
                    continue
                distance, nearest = cKDTree(moved[index[others]]).query(moved[index[mine]],
                                                                        distance_upper_bound=HAND_NEAR)
                close = np.isfinite(distance)
                if close.any():
                    there = index[others[nearest[close]]]
                    sunk = -np.einsum("pa,pa->p", moved[index[mine[close]]] - moved[there], turned[there])
                    found[side] = max(found[side], float(sunk.max()))
        return found
    return depth


def hands_cleared(worlds, bind, names, parents, depth):
    """A person's clip with each arm held out far enough that its hand stays out of the clothes: turned out the
    fewest whole degrees more while it hangs (`arms_kept_out`'s `extra`, 0 to HAND_CLEAR_MOST, every one tried: the
    depth is not monotonic, the hoodie man's left hand stood 3 cm in at 0 and 1 degree and out at 8) after which its
    hand goes no deeper than HAND_CLEAR into them (`depth`, `hands_depth`'s reader), else the degrees it goes least
    deep at (a hand resting on a lap, where the arm does not hang). The relaxed hands' fingers curl towards the
    thigh: laid in the older woman's and the hoodie man's sleeves they went 2.5 to 3 cm into the coat and the
    trousers standing (2026-11-27). The clip's worlds, the arms' new local turns, {side: (degrees, deepest metres)}."""
    tried = {}
    for degrees in np.arange(0.0, HAND_CLEAR_MOST + 0.5, 1.0):
        kept, _ = arms_kept_out(worlds, bind, names, parents, {side: degrees for side in relaxed_hands.SIDES})
        tried[float(degrees)] = depth(kept @ np.linalg.inv(bind))
    chosen = {}
    for side in relaxed_hands.SIDES:
        clear = [degrees for degrees, found in tried.items() if found[side] <= HAND_CLEAR]
        chosen[side] = min(clear) if clear else min(tried, key=lambda degrees: (tried[degrees][side], degrees))
    kept, turned = arms_kept_out(worlds, bind, names, parents, chosen)
    return kept, turned, {side: (chosen[side], round(tried[chosen[side]][side], 4)) for side in relaxed_hands.SIDES}


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


def own_maps(points, faces, places, back, source, tokens, size=MAP, laid_paint=None, laid_rough=None):
    """The rigged still's own maps ({role: (size, size, 3) uint8}: base colour and, where the still has them, metal and
    roughness), each texel the still's own paint nearest its point taken back into the still's frame (`back`), the
    base colour graded toward the palette's `tokens` as the made props' paint is (grade.py); and the grade's groups.
    `laid_paint` (each point's base colour, NaN where none: a person's laid hands and the fans closing where its own
    were cut, `with_hands`) paints the faces whose every corner has one instead, nearest point's, after the grade,
    and `laid_rough` their metal and roughness where it has one (the hands' skin and nails, `hand_roughness`)."""
    rows, columns, found = texels_of(points, faces, places, size)
    paint = source.paint(back(found))
    filled = np.zeros((size, size), bool)
    filled[rows, columns] = True
    laid = None
    if laid_paint is not None and np.isfinite(laid_paint).all(1).any():
        painted = np.isfinite(laid_paint).all(1)
        laid_rows, laid_columns, laid_found = texels_of(points, faces[painted[faces].all(1)], places, size)
        nearest = np.flatnonzero(painted)[cKDTree(points[painted]).query(laid_found)[1]]
        laid = {"base_color": laid_paint[nearest]}
        if laid_rough is not None:
            laid["metal_roughness"] = laid_rough[nearest]
        filled[laid_rows, laid_columns] = True
    maps, report = {}, []
    for role, values in paint.items():
        picture = np.zeros((size, size, 3))
        picture[rows, columns] = values
        if role == "base_color" and tokens:
            chosen = np.random.default_rng(7).choice(len(values), min(GRADE_SAMPLES, len(values)), replace=False)
            picture, report = grade_module().graded(picture, values[chosen], tokens)
        if laid is not None and role in laid:
            values_laid = laid[role]
            known = np.isfinite(values_laid).all(1)
            picture[laid_rows[known], laid_columns[known]] = values_laid[known]
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


def written(out, document, blob, bind, laid, maps, turned=None):
    """The glTF: the dressed body's Person node, joints, skin and clips (joint keys only; `turned`: {clip: {joint:
    its local rotations}} written over the dressed body's keys, `arms_kept_out`), the still's parts as the
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
            joint = joints.index(channel["target"]["node"]) if channel["target"]["node"] in joints else None
            own = (turned or {}).get(animation["name"], {}).get(joint) if channel["target"]["path"] == "rotation" \
                else None
            output = (copied(contents, document, blob, sampler["output"]) if own is None else
                      contents.reading(np.asarray(own, np.float32).ravel().tolist(), "VEC4", glb.FLOAT))
            samplers.append({"input": copied(contents, document, blob, sampler["input"]),
                             "output": output,
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


def photo_skin(stats_path):
    """The person's skin colour off its close-up photo (sRGB, 0 to 1): the face skin step's (`generated/skin.py`)
    photo skin CIELAB in its stats.json (`paint_toned`'s `photo_lab`). The paint's face reads pinker than the photo's
    (the older woman's 0.80, 0.55, 0.51 against her photo's 0.80, 0.61, 0.53), and her hands in it read as pink
    rubber (2026-11-27)."""
    from skimage.color import lab2rgb
    lab = json.loads(pathlib.Path(stats_path).read_text())["paint_toned"]["photo_lab"]
    return np.clip(lab2rgb(np.asarray(lab, float)[None, None])[0, 0], 0.0, 1.0)


def rigged(still, dressed, rig_path, palette_path, out, faces=FACES, person=False, skin_stats=None):
    """The still rigged on the dressed body's skeleton into `out` (body.glb, rig.json); the record. A `person` has a
    head and clothes for parts (parts_of); its laid hands wear its photo's skin (`photo_skin`, from the face skin
    step's `skin_stats`) where it has one, else its face's paint."""
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
    laid_paint, laid_rough, hands_record = None, None, {}
    if person:
        skin = face_skin(mesh.vertices, mesh.faces, part_of, colours, names, bind)
        hand_skin = skin if skin_stats is None else photo_skin(skin_stats)
        cut = hand_cut(mesh.vertices, mesh.faces, colours, weights, names, bind, skin)
        laid = hands_laid(hands_file(rig_path), names, rig["bind"], bind)
        offsets = sleeve_offsets(mesh.vertices, mesh.faces, cut, weights, names, bind)
        weights, taken_off = off_the_hands(mesh.vertices, mesh.faces, cut, weights, colours, names, bind)
        laid = {side: (hand[0] + offsets[side], *hand[1:]) for side, hand in laid.items()}
        points, faces_now, part_of, weights, laid_paint, laid_rough = with_hands(
            mesh.vertices, mesh.faces, part_of, weights, colours, cut, laid, skin, hand_skin)
        near = np.zeros(len(faces_now), bool)  # with_hands keeps the uncut faces first, in their order
        near[:int((~cut).sum())] = taken_off[mesh.faces[~cut]].any(1)
        points, faces_now, weights, (laid_paint, laid_rough, torn_from) = torn(
            points, faces_now, weights, names, near, laid_paint, laid_rough, np.arange(len(points)))
        points, faces_now, part_of, weights, (laid_paint, laid_rough) = tears_closed(
            points, faces_now, part_of, weights, names, torn_from, laid_paint, laid_rough)
        weights = eased_cliffs(points, faces_now, weights, hard_points(faces_now, part_of, len(points)))  # the
        # cliffs left eased as the others, never across the tear
        mesh = trimesh.Trimesh(points, faces_now, process=False)
        hands_record = {"cut_faces": int(cut.sum()), "skin": np.round(skin, 3).tolist(),
                        "hand_skin": np.round(hand_skin, 3).tolist(),
                        "to_sleeve_m": {side: np.round(off, 3).tolist() for side, off in offsets.items()}}
    out.mkdir(parents=True, exist_ok=True)
    tokens = json.loads(pathlib.Path(palette_path).read_text()).get("tokens", {})
    normals = mesh.vertex_normals
    mapping, split_faces, places = unwrapped(mesh.vertices, mesh.faces, normals)
    maps, grade = own_maps(mesh.vertices[mapping], split_faces, places, taken_back(thin.vertices, fitted.vertices),
                           source, tokens, laid_paint=None if laid_paint is None else laid_paint[mapping],
                           laid_rough=None if laid_paint is None else laid_rough[mapping])
    laid = {"points": mesh.vertices, "faces": mesh.faces, "part_of": part_of, "weights": weights, "normals": normals,
            "mapping": mapping, "split_faces": split_faces, "places": places}
    order, kept = strongest(weights)
    clips, turned = {}, {}
    depth = hands_depth(mesh.vertices, mesh.faces, part_of, order, kept, names) if person else None
    for animation in document["animations"]:
        worlds = clip_worlds(document, blob, animation, names, parents)
        if person:
            worlds, turned[animation["name"]], cleared = hands_cleared(worlds, bind, names, parents, depth)
        moves = worlds @ np.linalg.inv(bind)
        most, high, where = stretch(mesh.vertices, mesh.faces, order, kept, moves)
        clips[animation["name"]] = {"stretch_most": round(max(most), 3), "stretch_999": round(max(high), 3),
                                    "frames": len(most), "where": np.round(where, 3).tolist()}
        if person:
            clips[animation["name"]]["hands"] = {side: {"raised_degrees": raised, "in_clothes_m": deepest}
                                                 for side, (raised, deepest) in cleared.items()}
    sizes = written(out / "body.glb", document, blob, bind, laid, maps, turned)
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
              "grade": grade, "hands": hands_record,
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
    parser.add_argument("--skin-stats", type=pathlib.Path,
                        help="a person's face skin step stats.json: its hands wear the photo's skin")
    options = parser.parse_args()
    record = rigged(options.still, options.dressed, options.rig, options.palette, options.out, options.faces,
                    options.person, options.skin_stats)
    print(f"still rig: {record['height_m']} m, {record['triangles']} triangles, parts {record['parts']}, matched "
          f"{record['matched_share']:.0%}, stretch {({name: clip['stretch_most'] for name, clip in record['clips'].items()})}; "
          f"{options.out / 'rig.json'}", flush=True)


if __name__ == "__main__":
    main()
