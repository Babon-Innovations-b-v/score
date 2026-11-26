"""A generated person's clothes moved as cloth while she walks (#223; owner 2026-11-26, of the skinned walking sheet:
"moving creates a lot of warping"). TRELLIS.2 makes a person as one fused shell; still_rig skins it whole on the
dressed body's skeleton, so wide jeans fin at the passing step and a jacket stretches like skin. Here the shell is
split into its garments and the loose ones hang and swing on the body as cloth, on Newton's VBD
(score/stages/people_cloth/inside/cloth.py, the people cloth stage's own run, reused as it is).

1. `person_of`: still_rig's rigged person (body.glb, its own paint: rig it with a palette of no tokens) read back: its
   skeleton at the bind, its clips, its shell welded with each face's paint (its base colour map at the face's texture
   places, CIELAB) and each point's skin weights.
2. `kinds_of`: each face's kind (KINDS). still_rig's head part (face, hair, neck) stays the head; every other face is
   the kind whose colour, read off the person where only that kind can be (`seeds`: the upper sleeves the jacket, the
   shins the jeans, the soles' height the shoes, the chest's middle in front the T-shirt, the fingers the skin), lies
   nearest its own in that kind's spread, among the kinds its place allows (`allowed`: shoes only under the ankles,
   jeans never on the arms nor over the waist, the T-shirt only on the trunk). Settled by its neighbours (SETTLE
   rounds of votes over the faces' edges, so a cut runs along the paint's edge) and a piece under ISLAND_FACES of a
   kind given to the kinds round it.
3. `riding_of`: which points of a garment ride the skin (the rest hang as cloth): the jacket's collar and shoulder
   yoke (YOKE_M over its surface from where it meets the neck and hair) and its elastic cuffs (CUFF_M from the hands),
   the jeans' waistband (WAISTBAND_M from the T-shirt and the jacket).
3b. `sim_of`: the garment's sim mesh (`cloth_mesh.py`): the shell's own triangles are no cloth (round 1, 2026-11-26:
   a 2.7e-11 m^2 sliver's point went non-finite in the hang, and the run wrote NaNs on), so an even manifold mesh of
   1.2 cm edges is laid over the body onto the garment's broad shape, its rest shape the generated one (the shape
   TRELLIS.2 drew is the hang it is let settle from); its skin weights and riding are blended from the shell's
   garment, a piece of it with no riding point rides whole (people_cloth's rule: loose cloth hangs by an edge), and
   the garment's own surface (both walls, its folds and paint) is bound to it and rides along.
4. `body_under`: the collision body, the mean SOMA surface on the bind (still_rig.soma_on: the body the shell was
   fitted to), each point pushed in under the shell by MARGIN_M where it lies nearer than that (a slim woman over the
   SOMA mean: most of its skin outside her), the push smoothed over the body; cut into one piece a joint (each face
   to its corners' strongest joint), the head's and the feet's left out and the shell's own shoes laid on the feet
   instead (the jeans' hems fall on the shoes).
5. `job_of`: the run's job: the clip tiled over WARM_CYCLES and the clip's seconds (`tiled`: a walk's travel carried
   on from cycle to cycle), the whole person scaled to her own height (`--height`: the person's measured height, not
   the template body's), each garment's riding points skinned along, its cloth values the library's row
   (data/physics/cloth.json: the jeans `denim`; the puffer jacket has no row of its own and hangs as `denim`, the
   stiffest the table holds, named in the record).
6. `resampled` and `cloth_mesh.carried`: the run read back at the film's FPS from WARM_CYCLES on, each frame with the clip's time and the walk's
   travel taken out (the armature in Blender plays the clip in place), and the sheet's stride points (left foot
   ahead, passing, right foot ahead) in the last cycle, the drawn surface carried by the sim mesh; `measures`: each
   garment's deepest loose point inside the body (the sim mesh's and the drawn surface's), its largest stretch, its
   drift off the skin and its jitter.

    python -m tools.characters.generated.cloth <body.glb> <clips rig.npz> <out> --height <m>
           [--newton <python>] [--device cpu|cuda:0]

writes <out>/cloth.npz (what blender_cloth.py draws) and <out>/cloth.json (the kinds' faces, the garments' points and
riding share, the run's engine and seconds, the measures). `blender_cloth.py` draws it beside the skinned person.
"""
import argparse
import json
import pathlib
import subprocess
import sys
import time

import numpy as np
import trimesh
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components, dijkstra
from scipy.spatial import cKDTree
from skimage.color import rgb2lab

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE.parent / "still_rig"))
import still_rig  # noqa: E402  (still_rig's own import path brings skel_usd and prop_rig)
import skel_usd  # noqa: E402

sys.path.insert(0, str(REPO))
from tools.characters.generated import cloth_mesh  # noqa: E402

KINDS = ("head", "skin", "jacket", "shirt", "jeans", "shoes")
SIMULATED = ("jacket", "jeans")
ROWS = {"jacket": "denim", "jeans": "denim"}  # data/physics/cloth.json rows: no puffer row exists, denim the stiffest
THICKNESS_M = {"jacket": 0.006, "jeans": 0.003}  # drawn thickness (Blender's solidify) and twice the particle radius
INSIDE = REPO / "score/stages/people_cloth/inside/cloth.py"
CLOTH_TABLE = REPO / "data/physics/cloth.json"
NEWTON = pathlib.Path.home() / ".farm-factory-props/envs/newton_env/bin/python"
WELD = 1e-6  # metres: shell points this near are one point (still_rig's texture seams split them)
SETTLE = 4  # rounds of neighbour votes on each face's kind
ISLAND_FACES = 150  # a connected piece of a kind with fewer faces joins the kinds round it
KEEP_OWN = 1.5  # a face's own kind's weight in its neighbours' vote
SPREAD_LEAST = 4.0  # CIELAB: a kind's colour spread is never read tighter than this
ARMS = ("LeftArm", "LeftForeArm", "LeftHand", "RightArm", "RightForeArm", "RightHand", "LeftShoulder",
        "RightShoulder")
TRUNK = ("Hips", "Spine1", "Spine2", "Chest", "Neck1")
SKIN_JOINTS = ("LeftHand", "RightHand", "Neck1", "Neck2", "Head", "HeadEnd")
ANKLE_OVER_M = 0.05  # shoes lie at most this far over the ankle (the Foot joint)
SHIN_SEED_M = 0.12  # the jeans' colour is read on the shins this far over the ankle and higher
SHIRT_SEED = {"half_m": 0.035, "front_m": 0.03}  # the T-shirt's colour: this near the chest's middle, this far in front
SHIRT_HALF_M = 0.11  # the T-shirt shows only this near the chest's middle in front (the open jacket's gap): the
# glossy jacket's highlights read as white elsewhere
FINGER_SEED_M = 0.05  # the skin's colour: the hand faces this near the hand's furthest point
TUCKED_M = 0.12  # the T-shirt reaches this far under the Hips joint (tucked in)
YOKE_M = 0.16  # the jacket rides the skin this far over its surface from the neck and hair
CUFF_M = 0.04  # and this far from the hands (a puffer's elastic cuffs)
WAISTBAND_M = 0.08  # the jeans ride the skin this far from their top
MARGIN_M = 0.012  # the body lies at least this far under the shell
SMOOTH_ROUNDS = 10  # rounds the body's push is smoothed over its edges
LEFT_OUT = ("Head", "HeadEnd", "LeftFoot", "LeftToeBase", "LeftToeEnd", "RightFoot", "RightToeBase", "RightToeEnd")
FEET = ("LeftFoot", "LeftToeBase", "LeftToeEnd", "RightFoot", "RightToeBase", "RightToeEnd")
WARM_CYCLES = 1  # the clip's cycles run before the film starts (the cloth leaves its first frame's standstill)
SECONDS = 3.0  # the film
STANDING_S = 0.4  # the standing clip run after the hang, its last frame drawn
FPS = 24
GRAVITY = 9.81
SUBSTEPS = 20  # twice people_cloth's SUBSTEPS: a 1.2 cm mesh under denim's stiffness, each substep 1/600 s
ITERATIONS = 10  # people_cloth's ITERATIONS
MOST_SPEED = 10.0  # m/s: a loose point is held under this (a guard: a walk's hands swing at most about 5 m/s)
SETTLE_SPEED = 0.01  # m/s: people_cloth's REST_MOST
SETTLE_MOST_S = 3.0  # the hang's most seconds (people_cloth's HANG_MOST is 20 on the card)
CLOSED_DEGREES = 2.0  # a clip whose last frame turns every joint within this of its first repeats its first
LOOK_JOINT = "Hips"


# --- 1. the rigged person -------------------------------------------------------------------------------------------

def person_of(path):
    """still_rig's body.glb read back: {document, blob, names, bind, parents, points (welded shell), faces, head
    (each face from the head part), lab (each face's paint, CIELAB), weights (points x joints)}."""
    document, blob, names, bind, parents = still_rig.skeleton_of(path)
    node = next(node for node in document["nodes"] if node.get("name") == still_rig.OUTFIT)
    picture = None
    all_points, all_faces, all_weights, all_head, all_colours, count = [], [], [], [], [], 0
    for primitive in document["meshes"][node["mesh"]]["primitives"]:
        attributes = primitive["attributes"]
        points = skel_usd.accessor(document, blob, attributes["POSITION"]).astype(float)
        faces = skel_usd.accessor(document, blob, primitive["indices"]).reshape(-1, 3).astype(int)
        places = skel_usd.accessor(document, blob, attributes["TEXCOORD_0"]).astype(float)
        joints = skel_usd.accessor(document, blob, attributes["JOINTS_0"]).astype(int)
        shares = skel_usd.accessor(document, blob, attributes["WEIGHTS_0"]).astype(float)
        if picture is None:
            picture = base_picture(document, blob, primitive["material"])
        weights = np.zeros((len(points), len(names)))
        np.add.at(weights, (np.repeat(np.arange(len(points)), 4), joints.ravel()), shares.ravel())
        part = document["materials"][primitive["material"]]["extras"]["part"]
        all_points.append(points)
        all_faces.append(faces + count)
        all_weights.append(weights)
        all_head.append(np.full(len(faces), part == "head"))
        all_colours.append(face_paint(picture, places, faces))
        count += len(points)
    points, faces, index = welded(np.concatenate(all_points), np.concatenate(all_faces))
    weights = np.zeros((len(points), len(names)))
    weights[index] = np.concatenate(all_weights)
    kept = faces_kept(index, np.concatenate(all_faces))
    return {"document": document, "blob": blob, "names": names, "bind": bind, "parents": parents, "points": points,
            "faces": faces, "head": np.concatenate(all_head)[kept], "lab": np.concatenate(all_colours)[kept],
            "weights": weights}


def base_picture(document, blob, material):
    """A material's base colour map, (rows, columns, 3) in 0..1."""
    import io
    from PIL import Image
    texture = document["materials"][material]["pbrMetallicRoughness"]["baseColorTexture"]["index"]
    view = document["bufferViews"][document["images"][document["textures"][texture]["source"]]["bufferView"]]
    start = view.get("byteOffset", 0)
    return np.asarray(Image.open(io.BytesIO(blob[start:start + view["byteLength"]])).convert("RGB"), float) / 255.0


def face_paint(picture, places, faces):
    """Each face's paint in CIELAB: its base colour map read at its corners and middle, averaged."""
    corners = places[faces]
    reads = [still_rig.bilinear(picture, corners[:, corner]) for corner in range(3)]
    reads.append(still_rig.bilinear(picture, corners.mean(1)))
    return rgb2lab(np.clip(np.mean(reads, axis=0), 0.0, 1.0)[None])[0]


def welded(points, faces):
    """Points within WELD made one (texture seams split them): (points, faces, each old point's new index); faces
    that lost a corner dropped (`faces_kept` names the kept ones)."""
    keys = np.round(points / WELD).astype(np.int64)
    _, first, index = np.unique(keys, axis=0, return_index=True, return_inverse=True)
    index = index.ravel()
    joined = index[faces]
    return points[first], joined[faces_kept(index, faces)], index


def faces_kept(index, faces):
    """Which faces keep three distinct corners once welded."""
    joined = index[faces]
    return (joined[:, 0] != joined[:, 1]) & (joined[:, 1] != joined[:, 2]) & (joined[:, 0] != joined[:, 2])


# --- 2. the kinds ---------------------------------------------------------------------------------------------------

def joint_at(person, name):
    """A joint's place at the bind."""
    return person["bind"][person["names"].index(name), :3, 3]


def strongest_of(person):
    """Each face's strongest joint's name (its corners' weights summed)."""
    face_weights = person["weights"][person["faces"]].sum(1)
    return np.array(person["names"])[face_weights.argmax(1)]


def allowed(person, middles, strongest):
    """{kind: which faces its place allows} for the kinds read from paint (every kind but the head)."""
    ankle = max(joint_at(person, "LeftFoot")[1], joint_at(person, "RightFoot")[1])
    waist = joint_at(person, "Spine2")[1]
    hips = joint_at(person, "Hips")[1]
    neck = joint_at(person, "Neck2")[1]
    on_arms = np.isin(strongest, ARMS)
    chest = joint_at(person, "Chest")
    front = (np.abs(middles[:, 0] - chest[0]) < SHIRT_HALF_M) & (middles[:, 2] > chest[2])
    return {"skin": np.isin(strongest, SKIN_JOINTS),
            "jacket": middles[:, 1] > hips - TUCKED_M,
            "shirt": front & ~on_arms & (middles[:, 1] > hips - TUCKED_M) & (middles[:, 1] < neck),
            "jeans": ~on_arms & (middles[:, 1] < waist),
            "shoes": middles[:, 1] < ankle + ANKLE_OVER_M}


def seeds(person, middles, strongest):
    """{kind: the faces only that kind can be}, where its colour is read."""
    ankle = min(joint_at(person, "LeftFoot")[1], joint_at(person, "RightFoot")[1])
    chest = joint_at(person, "Chest")
    spine = joint_at(person, "Spine1")
    found = {"jacket": np.isin(strongest, ("LeftArm", "RightArm")),
             "jeans": np.isin(strongest, ("LeftShin", "RightShin")) & (middles[:, 1] > ankle + SHIN_SEED_M),
             "shoes": middles[:, 1] < ankle,
             "shirt": ((np.abs(middles[:, 0] - chest[0]) < SHIRT_SEED["half_m"])
                       & (middles[:, 2] > chest[2] + SHIRT_SEED["front_m"])
                       & (middles[:, 1] > spine[1]) & (middles[:, 1] < chest[1]))}
    skin = np.zeros(len(middles), bool)
    for side in ("Left", "Right"):
        hand = strongest == f"{side}Hand"
        if hand.any():
            reach = np.linalg.norm(middles - joint_at(person, f"{side}ForeArm"), axis=1)
            tip = middles[hand][reach[hand].argmax()]
            skin |= hand & (np.linalg.norm(middles - tip, axis=1) < FINGER_SEED_M)
    found["skin"] = skin
    return found


def kinds_of(person):
    """Each face's kind number (KINDS): the head part's faces the head, every other face the kind its paint and
    place say, settled by its neighbours."""
    faces = person["faces"]
    middles = person["points"][faces].mean(1)
    strongest = strongest_of(person)
    colour = person["lab"]
    places = allowed(person, middles, strongest)
    distance = np.full((len(faces), len(KINDS)), np.inf)
    for kind, seeded in seeds(person, middles, strongest).items():
        seeded = seeded & ~person["head"]
        if not seeded.any():
            continue
        centre = np.median(colour[seeded], axis=0)
        spread = max(SPREAD_LEAST, float(np.median(np.linalg.norm(colour[seeded] - centre, axis=1))))
        distance[:, KINDS.index(kind)] = np.where(places[kind], np.linalg.norm(colour - centre, axis=1) / spread,
                                                  np.inf)
    found = distance.argmin(1)
    found[person["head"]] = KINDS.index("head")
    return islands_joined(faces, settled(faces, found, ~person["head"]), ~person["head"])


def face_neighbours(faces):
    """Pairs of faces sharing an edge (both ways round)."""
    return trimesh.Trimesh(np.zeros((faces.max() + 1, 3)), faces, process=False).face_adjacency


def settled(faces, found, free, rounds=SETTLE):
    """Each `free` face's kind set to its neighbours' most common one (its own counted KEEP_OWN), `rounds` times."""
    pairs = face_neighbours(faces)
    for _ in range(rounds):
        votes = np.zeros((len(found), len(KINDS)))
        np.add.at(votes, (pairs[:, 0], found[pairs[:, 1]]), 1)
        np.add.at(votes, (pairs[:, 1], found[pairs[:, 0]]), 1)
        votes[np.arange(len(found)), found] += KEEP_OWN
        found = np.where(free, votes.argmax(1), found)
    return found


def islands_joined(faces, found, free, least=ISLAND_FACES):
    """Each connected piece of one kind with fewer than `least` faces (of `free` faces) given, face by face, to the
    kinds round it."""
    pairs = face_neighbours(faces)
    for _ in range(3):
        same = pairs[found[pairs[:, 0]] == found[pairs[:, 1]]]
        graph = coo_matrix((np.ones(len(same)), (same[:, 0], same[:, 1])), shape=(len(found), len(found)))
        _, piece = connected_components(graph, directed=False)
        small = free & (np.bincount(piece)[piece] < least)
        if not small.any():
            break
        votes = np.zeros((len(found), len(KINDS)))
        for pair in (pairs, pairs[:, ::-1]):
            outside = ~small[pair[:, 1]]
            np.add.at(votes, (pair[outside, 0], found[pair[outside, 1]]), 1)
        found = np.where(small & (votes.sum(1) > 0), votes.argmax(1), found)
        found = settled(faces, found, small, rounds=SETTLE * 2)
    return found


# --- 3. the garments ------------------------------------------------------------------------------------------------

def garment_of(person, kinds, kind):
    """One kind's surface: (its point numbers in the shell, its faces renumbered)."""
    faces = person["faces"][kinds == KINDS.index(kind)]
    used, renumbered = np.unique(faces, return_inverse=True)
    return used, renumbered.reshape(-1, 3)


def borders(person, kinds, kind, others):
    """The shell points where a face of `kind` meets a face of any of `others`."""
    pairs = face_neighbours(person["faces"])
    ours = kinds[pairs[:, 0]] == KINDS.index(kind)
    theirs = np.isin(kinds[pairs[:, 1]], [KINDS.index(other) for other in others])
    meeting = pairs[ours & theirs]
    shared = [np.intersect1d(person["faces"][one], person["faces"][other]) for one, other in meeting]
    return np.unique(np.concatenate(shared)) if shared else np.zeros(0, int)


def over_surface(points, faces, sources):
    """Each point's distance over the surface (its edges) from the nearest of `sources` (point numbers)."""
    edges = np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
    lengths = np.linalg.norm(points[edges[:, 0]] - points[edges[:, 1]], axis=1)
    graph = coo_matrix((lengths, (edges[:, 0], edges[:, 1])), shape=(len(points), len(points))).tocsr()
    if not len(sources):
        return np.full(len(points), np.inf)
    return dijkstra(graph, directed=False, indices=np.unique(sources), min_only=True)


def riding_of(person, kinds, kind, used, faces):
    """Which of a garment's points ride the skin: the jacket's yoke and cuffs, the jeans' waistband."""
    points = person["points"][used]
    local = {point: number for number, point in enumerate(used)}

    def from_border(others, low=None, high=None):
        found = borders(person, kinds, kind, others)
        if low is not None:
            found = found[person["points"][found, 1] < low]
        if high is not None:
            found = found[person["points"][found, 1] > high]
        return over_surface(points, faces, [local[point] for point in found if point in local])

    if kind == "jacket":
        chest = joint_at(person, "Chest")[1]
        return (from_border(("head", "skin"), high=chest) < YOKE_M) | (from_border(("skin",), low=chest) < CUFF_M)
    if kind == "jeans":
        return from_border(("shirt", "jacket", "skin")) < WAISTBAND_M
    return np.ones(len(used), bool)


# --- 4. the body under ----------------------------------------------------------------------------------------------

def body_under(person, rig, margin=MARGIN_M):
    """The collision body: (points, faces, weights) the SOMA mean on the bind, pushed under the shell by `margin`."""
    body, weights = still_rig.soma_on(rig, person["names"], person["bind"])
    points = np.asarray(body.vertices, float)
    pushed = points + pushes(points, body.faces, body.vertex_normals, person["points"], person["faces"], margin)
    return pushed, np.asarray(body.faces), weights


def pushes(points, faces, normals, shell_points, shell_faces, margin):
    """Each body point's move inward along its normal that leaves the shell at least `margin` over it (the shell's
    nearest point measured along the point's normal), smoothed over the body's edges (never outward)."""
    shell = trimesh.Trimesh(shell_points, shell_faces, process=False)
    nearest = trimesh.proximity.closest_point(shell, points)[0]
    over = np.einsum("pd,pd->p", nearest - points, normals)
    depth = np.maximum(0.0, margin - over)
    edges = np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
    graph = coo_matrix((np.ones(len(edges)), (edges[:, 0], edges[:, 1])), shape=(len(points), len(points))).tocsr()
    graph = graph + graph.T
    degree = np.asarray(graph.sum(1)).ravel()
    for _ in range(SMOOTH_ROUNDS):
        depth = np.maximum(depth, (graph @ depth) / np.maximum(degree, 1))
    return -depth[:, None] * normals


def segment_pieces(points, faces, weights, names, bind, extra=()):
    """The body cut into one piece a joint (each face to the joint most of its corners hang from most), each piece in
    its joint's bind frame; LEFT_OUT joints' pieces dropped and `extra` (points, faces, joint names a face) added:
    [{name, joint, points, faces}]."""
    owner = weights.argmax(1)
    face_owner = np.array([np.bincount(row, minlength=len(names)).argmax() for row in owner[faces]])
    gathered = {}
    for joint, name in enumerate(names):
        if name not in LEFT_OUT:
            gathered[joint] = [(points, faces[face_owner == joint])]
    for extra_points, extra_faces, extra_owner in extra:
        for joint in np.unique(extra_owner):
            gathered.setdefault(int(joint), []).append((extra_points, extra_faces[extra_owner == joint]))
    found = []
    for joint, sets in gathered.items():
        laid, laid_faces, count = [], [], 0
        for set_points, set_faces in sets:
            if not len(set_faces):
                continue
            used, renumbered = np.unique(set_faces, return_inverse=True)
            laid.append(set_points[used])
            laid_faces.append(renumbered.reshape(-1, 3) + count)
            count += len(used)
        if not laid:
            continue
        frame = np.linalg.inv(bind[joint])
        local = np.concatenate(laid) @ frame[:3, :3].T + frame[:3, 3]
        found.append({"name": names[joint], "joint": joint, "points": local, "faces": np.concatenate(laid_faces)})
    return found


# --- 5. the job -----------------------------------------------------------------------------------------------------

def clip_of(person, name):
    """A clip's joint worlds (frames, joints, 4, 4) and its rate (frames a second)."""
    document, blob = person["document"], person["blob"]
    animation = next(animation for animation in document["animations"] if animation["name"] == name)
    times = skel_usd.accessor(document, blob, animation["samplers"][0]["input"]).ravel()
    worlds = still_rig.clip_worlds(document, blob, animation, person["names"], person["parents"])
    return worlds, (len(times) - 1) / float(times[-1] - times[0])


def cycle_of(worlds):
    """(frames a cycle, the travel a cycle): a clip whose last frame turns every joint as its first repeats it."""
    turns = np.einsum("jab,jcb->jac", worlds[-1, :, :3, :3], worlds[0, :, :3, :3])
    angles = np.degrees(np.arccos(np.clip((np.trace(turns, axis1=1, axis2=2) - 1.0) / 2.0, -1.0, 1.0)))
    length = len(worlds) - 1 if angles.max() < CLOSED_DEGREES else len(worlds)
    step = worlds[-1, 0, :3, 3] - worlds[-2, 0, :3, 3]
    end = worlds[length, 0, :3, 3] if length < len(worlds) else worlds[-1, 0, :3, 3] + step
    travel = end - worlds[0, 0, :3, 3]
    travel[1] = 0.0
    return length, travel


def tiled(worlds, frames):
    """The clip played `frames` frames, cycle after cycle, its travel carried on: (worlds, each frame's clip frame,
    each frame's cycle)."""
    length, travel = cycle_of(worlds)
    number = np.arange(frames)
    cycle, inside = number // length, number % length
    found = worlds[inside].copy()
    found[:, :, :3, 3] += cycle[:, None, None] * travel
    return found, inside, cycle, travel


def scaled(worlds, scale):
    """Joint worlds (..., 4, 4) with their places scaled (the whole person sized)."""
    found = np.array(worlds, float)
    found[..., :3, 3] *= scale
    return found


def skinned(points, weights, moves):
    """Points carried by their weights over joint moves (frames, joints, 4, 4): (frames, points, 3)."""
    homogeneous = np.concatenate([points, np.ones((len(points), 1))], 1)
    blended = np.einsum("pj,fjab->fpab", weights, moves[:, :, :3, :])
    return np.einsum("fpab,pb->fpa", blended, homogeneous)


def sim_of(person, kinds, kind, body, scale, used, faces, riding):
    """A garment's sim mesh (module docstring step 3b), in metres: {points, faces, weights, riding, binding} (binding:
    the garment's shell points `used` bound to it)."""
    strongest = person["weights"][person["faces"]].sum(1).argmax(1)
    chosen = np.flatnonzero(kinds == KINDS.index(kind))
    laid = cloth_mesh.laid_over((body[0] * scale, body[1]), body[2].argmax(1),
                                (person["points"] * scale, person["faces"]), chosen, strongest[chosen],
                                (person["names"], person["parents"]))
    points, sim_faces = cloth_mesh.remeshed(*cloth_mesh.cleaned(*laid))
    shell = person["points"][used] * scale
    weights = cloth_mesh.blended(person["weights"][used], shell, faces, points)
    weights = np.maximum(weights, 0.0) / np.maximum(weights.sum(1, keepdims=True), 1e-12)
    rides = anchored(sim_faces, cloth_mesh.blended(riding.astype(float), shell, faces, points) > 0.5)
    return {"points": points, "faces": sim_faces, "weights": weights, "riding": rides,
            "binding": cloth_mesh.bound(shell, points, sim_faces)}


def anchored(faces, riding):
    """`riding` with every piece of the mesh that has no riding point made to ride whole."""
    piece = cloth_mesh.pieces_of(faces, len(riding))
    held = np.zeros(piece.max() + 1, bool)
    np.logical_or.at(held, piece, riding[faces].any(1))
    loose_piece = np.zeros(len(riding), bool)
    loose_piece[faces[~held[piece]].ravel()] = True
    return riding | loose_piece


def material_of(kind, points, faces):
    """Newton's cloth values for a garment from its cloth.json row (people_cloth's own conversion)."""
    from score.stages.people_cloth import material_of as stage_material
    row = json.loads(CLOTH_TABLE.read_text())["recipes"][ROWS[kind]]
    return stage_material(row, points, faces, THICKNESS_M[kind])


def job_of(person, kinds, body, clip, scale, out, device):
    """The run's job (job.json, motion.npz in `out`) for one clip; {kind: (used, faces, riding)} and the run's
    frames' clip frames and cycles."""
    worlds, rate = clip_of(person, clip)
    length, _ = cycle_of(worlds)
    frames = (length * WARM_CYCLES + int(np.ceil(SECONDS * rate)) + 2 if clip == "walking" else
              int(np.ceil(STANDING_S * rate)))
    played, inside, cycle, travel = tiled(worlds, frames)
    played = scaled(played, scale)
    bind = scaled(person["bind"], scale)
    moves = played @ np.linalg.inv(bind)
    points, faces, weights = body
    shoes_used, shoes_faces = garment_of(person, kinds, "shoes")
    shoe_owner = person["weights"][shoes_used].argmax(1)[shoes_faces].tolist()
    shoe_owner = np.array([max(set(row), key=row.count) for row in shoe_owner])
    pieces = segment_pieces(points * scale, faces, weights, person["names"], bind,
                            [(person["points"][shoes_used] * scale, shoes_faces, shoe_owner)])
    motion = {"woman/segments": played[:, [piece["joint"] for piece in pieces]]}
    parts, garments = [], {}
    for kind in SIMULATED:
        used, garment_faces = garment_of(person, kinds, kind)
        riding = riding_of(person, kinds, kind, used, garment_faces)
        sim = sim_of(person, kinds, kind, body, scale, used, garment_faces, riding)
        motion[f"woman/{kind}/skinned"] = skinned(sim["points"], sim["weights"], moves)
        parts.append({"name": kind, "rest": sim["points"].tolist(), "faces": sim["faces"].tolist(),
                      "free": (~sim["riding"]).tolist(), "material": material_of(kind, sim["points"], sim["faces"])})
        garments[kind] = (used, garment_faces, riding, sim)
    np.savez_compressed(out / f"{clip}_motion.npz", **motion)
    job = {"rate": rate, "gravity": GRAVITY, "substeps": SUBSTEPS, "iterations": ITERATIONS, "device": device,
           "most_speed": MOST_SPEED,
           "motion": str(out / f"{clip}_motion.npz"), "settle": {"speed": SETTLE_SPEED, "seconds": SETTLE_MOST_S},
           "people": [{"name": "woman", "segments": [{"name": piece["name"], "points": piece["points"].tolist(),
                                                      "faces": piece["faces"].tolist()} for piece in pieces],
                       "parts": parts}]}
    (out / f"{clip}_job.json").write_text(json.dumps(job))
    return garments, {"rate": rate, "length": length, "inside": inside, "cycle": cycle, "travel": travel * scale,
                      "moves": moves, "played": played}


def ran(newton, job, out):
    """inside/cloth.py run on `job` in Newton's own Python; its output and the seconds it took."""
    started = time.monotonic()
    subprocess.run([str(newton), str(INSIDE), str(job), str(out)], check=True)
    return dict(np.load(out)), round(time.monotonic() - started, 1)


# --- 6. read back ---------------------------------------------------------------------------------------------------

def at_times(sequence, positions):
    """`sequence` (frames, ...) read at fractional frame `positions`, linearly."""
    low = np.clip(np.floor(positions).astype(int), 0, len(sequence) - 1)
    high = np.clip(low + 1, 0, len(sequence) - 1)
    share = (positions - low).reshape(-1, *([1] * (sequence.ndim - 1)))
    return sequence[low] * (1.0 - share) + sequence[high] * share


def resampled(cloth, timing, start_frame, count):
    """The run read at FPS from `start_frame` for `count` film frames: (positions (count, points, 3) with each
    frame's travel taken out, each frame's clip time in seconds)."""
    rate, length = timing["rate"], timing["length"]
    positions = start_frame + np.arange(count) * rate / FPS
    found = at_times(cloth, positions)
    cycle = np.floor(positions / length)
    found = found - cycle[:, None, None] * timing["travel"][None, None]
    return found, (positions % length) / rate


def stride_points(person, timing):
    """The last cycle's frames with the left foot furthest ahead, the feet passing, the right furthest ahead (the
    person faces +z), as run frame numbers."""
    names = person["names"]
    played, length = timing["played"], timing["length"]
    last = np.arange(len(played) - 2 - length, len(played) - 2)
    reach = played[last, names.index("LeftFoot"), 2, 3] - played[last, names.index("RightFoot"), 2, 3]
    left, right = last[reach.argmax()], last[reach.argmin()]
    between = [frame for frame in last if min(left, right) < frame < max(left, right)]
    passing = min(between or list(last), key=lambda frame: abs(reach[frame - last[0]]))
    return {"left_ahead": int(left), "passing": int(passing), "right_ahead": int(right)}


def measures(cloth, sim, skinned_points, drawn, drawn_free, body_posed, body_faces):
    """A garment's numbers over the run: its sim mesh's loose points' deepest inside the body and the drawn
    surface's, the sim mesh's largest stretch past its built or skinned length, its largest drift off the skin and
    its loose points' frame-to-frame change of step (jitter: the 99th percentile and the most, metres a frame)."""
    from score.stages.people_cloth import depths, stretches
    free = ~sim["riding"]
    deep = depths(cloth[::3], free, (body_posed[::3], body_faces))
    deep_drawn = depths(drawn[::3], drawn_free, (body_posed[::3], body_faces))
    stretch = stretches(cloth, sim["points"], skinned_points, sim["faces"], free)
    speed = np.diff(cloth[:, free], axis=0)
    jitter = np.linalg.norm(np.diff(speed, axis=0), axis=2)
    return {"deepest_m": round(float(deep.max()), 4), "deepest_drawn_m": round(float(deep_drawn.max()), 4),
            "largest_stretch": round(float(stretch.max()), 4), "stretch_99": round(float(np.percentile(stretch, 99)), 4),
            "drift_most_m": round(float(np.linalg.norm(cloth[:, free] - skinned_points[:, free], axis=2).max()), 4),
            "jitter_99_m_per_frame2": round(float(np.percentile(jitter, 99)), 5),
            "jitter_most_m_per_frame2": round(float(jitter.max()), 5)}


def made(body_glb, rig_path, out, height, newton=NEWTON, device="cpu"):
    """The whole make: kinds, garments, body, the walking and standing runs, cloth.npz and cloth.json in `out`."""
    out.mkdir(parents=True, exist_ok=True)
    person = person_of(body_glb)
    kinds = kinds_of(person)
    rig = dict(np.load(rig_path))
    body = body_under(person, rig)
    scale = height / float(np.ptp(person["points"][:, 1]))
    saved = {"scale": scale, "kinds": kinds, "shell_points": person["points"], "shell_faces": person["faces"],
             "body_points": body[0], "body_faces": body[1], "body_weights": body[2],
             "joint_names": np.array(person["names"])}
    record = {"body": str(body_glb), "height_m": height, "scale": round(scale, 4),
              "faces": {kind: int((kinds == number).sum()) for number, kind in enumerate(KINDS)},
              "rows": {kind: ROWS[kind] for kind in SIMULATED},
              "note": "no puffer row in data/physics/cloth.json: the jacket hangs as denim, the stiffest row",
              "runs": {}}
    for clip in ("walking", "standing"):
        garments, timing = job_of(person, kinds, body, clip, scale, out, device)
        result, seconds = ran(newton, out / f"{clip}_job.json", out / f"{clip}_cloth.npz")
        start = timing["length"] * WARM_CYCLES
        count = int(SECONDS * FPS) if clip == "walking" else 1
        if clip == "standing":
            start = len(timing["played"]) - 3
        frames = {"film": start} if clip == "walking" else {"standing": start}
        if clip == "walking":
            frames.update(stride_points(person, timing))
        body_posed = skinned(body[0] * scale, body[2], timing["moves"])
        run = {"engine": str(result["engine"]), "seconds": seconds, "settled_s": float(result["settled"]),
               "rate": timing["rate"], "cycle_frames": timing["length"], "frames": frames, "garments": {}}
        for kind, (used, faces, riding, sim) in garments.items():
            cloth = result[f"woman/{kind}"]
            carried = skinned(sim["points"], sim["weights"], timing["moves"])
            drawn = cloth_mesh.carried(sim["binding"], cloth, sim["faces"])
            run["garments"][kind] = {"points": len(used), "sim_points": len(sim["points"]),
                                     "sim_faces": len(sim["faces"]),
                                     "riding_share": round(float(sim["riding"].mean()), 3),
                                     **measures(cloth, sim, carried, drawn, ~riding, body_posed, body[1])}
            saved[f"{kind}_used"], saved[f"{kind}_faces"], saved[f"{kind}_riding"] = used, faces, riding
            saved[f"{kind}_sim_points"], saved[f"{kind}_sim_faces"] = sim["points"] / scale, sim["faces"]
            for name, frame in frames.items():
                film, times = resampled(drawn, timing, frame, count if name == "film" else 1)
                saved[f"{clip}/{name}/{kind}"] = film / scale
                saved[f"{clip}/{name}/time"] = times
        record["runs"][clip] = run
    np.savez_compressed(out / "cloth.npz", **saved)
    (out / "cloth.json").write_text(json.dumps(record, indent=1))
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("body", type=pathlib.Path)
    parser.add_argument("rig", type=pathlib.Path)
    parser.add_argument("out", type=pathlib.Path)
    parser.add_argument("--height", type=float, required=True)
    parser.add_argument("--newton", type=pathlib.Path, default=NEWTON)
    parser.add_argument("--device", default="cpu")
    options = parser.parse_args()
    record = made(options.body, options.rig, options.out, options.height, options.newton, options.device)
    print(f"cloth: {record['faces']}; " + "; ".join(
        f"{clip} {run['seconds']} s: " + ", ".join(f"{kind} deepest {found['deepest_m']} m stretch "
                                                    f"{found['largest_stretch']}" for kind, found in
                                                    run["garments"].items()) for clip, run in record["runs"].items()),
          flush=True)


if __name__ == "__main__":
    main()
