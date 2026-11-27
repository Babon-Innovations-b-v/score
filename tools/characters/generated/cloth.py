"""A generated person's clothes moved as cloth while she walks (#223; owner 2026-11-26, of the skinned walking sheet:
"moving creates a lot of warping"). TRELLIS.2 makes a person as one fused shell; still_rig skins it whole on the
dressed body's skeleton, so wide jeans fin at the passing step and a jacket stretches like skin. Here the shell is
split into its garments and the loose ones swing and sag on the body as tethered cloth (`cloth_tether.py`: each sim
point simulated but held within a tether of its skinned place, as games move clothes). Two free runs on Newton's VBD
(round 1 and 2, 2026-11-26) tore: the jeans stretched 90 cm down to and between the shoes, 19 cm deep in the body,
and the jacket shredded; free cloth was stopped for the tether.

1. `person_of`: still_rig's rigged person (body.glb, its own paint: rig it with a palette of no tokens) read back: its
   skeleton at the bind, its clips, its shell welded with each face's paint (its base colour map at the face's texture
   places, CIELAB) and each point's skin weights.
2. `kinds_of`: each face's kind (KINDS). still_rig's head part (face, hair, neck) stays the head; every other face is
   the kind whose colour, read off the person where only that kind can be (`seeds`: the upper sleeves the jacket, the
   shins the jeans, the soles' height the shoes, the chest's middle in front the T-shirt, the fingers the skin; a
   scarf and the shirt under it where the open front shows two colours, one standing forward: `scarf_split`), lies
   nearest its own in that kind's spread, among the kinds its place allows (`allowed`: shoes only under the ankles,
   jeans never on the arms nor over the waist, the T-shirt only on the trunk, the jacket never on a face hanging from
   a leg: 47 such faces by the hands, bound to the jacket's sim mesh, hung 30 cm off their place as blue shards at
   the hem; round 4, 2026-11-27; unless a long coat's, above its hem read from the outside: `jacket_hem`), nor on a
   hand under its wrist. Settled by its neighbours (SETTLE
   rounds of votes over the faces' edges, so a cut runs along the paint's edge) and a piece under ISLAND_FACES of a
   kind given to the kinds round it.
3. `riding_of`: which points of a garment ride the skin (the rest hang as cloth): the jacket's collar and shoulder
   yoke (YOKE_M over its surface from where it meets the neck, hair or scarf) and its elastic cuffs (CUFF_M from the
   hands), the jeans' waistband (WAISTBAND_M from the T-shirt and the jacket), a scarf round the neck (SCARF_NECK_M).
3b. `sim_of`: the garment's sim mesh (`cloth_mesh.py`): the shell's own triangles are no cloth (round 1, 2026-11-26:
   a 2.7e-11 m^2 sliver's point went non-finite in the hang, and the run wrote NaNs on), so an even manifold mesh of
   1.2 cm edges is laid over the body onto the garment's broad shape, its rest shape the generated one (the shape
   TRELLIS.2 drew is the hang it is let settle from); its skin weights and riding are blended from the shell's
   garment, a piece of it with no riding point rides whole (people_cloth's rule: loose cloth hangs by an edge), and
   the garment's own surface (both walls, its folds and paint) is bound to it and rides along.
4. `body_under`: the collision body, the mean SOMA surface on the bind (still_rig.soma_on: the body the shell was
   fitted to), each point pushed in under the shell by MARGIN_M where it lies nearer than that (a slim woman over the
   SOMA mean: most of its skin outside her), the push smoothed over the body.
5. `garments_of`, `timing_of` and `moved`: each worn garment's tethers (none riding and at a hem near the shoes,
   rising over the loose cloth to the garment's longest: cloth_tether.TETHER_M's or `--tether KIND=M`, an open
   overshirt's fronts and a long coat's hem swinging further), the clip tiled over
   WARM_CYCLES and the clip's seconds (`tiled`: a walk's travel carried on from cycle to cycle), the whole person
   scaled to her own height (`--height`: the person's measured height, not the template body's), and the cloth run
   on its targets after SETTLE_S held on the first frame.
6. `resampled` and `cloth_mesh.displaced`: the run read back at the film's FPS from WARM_CYCLES on, each frame with
   the clip's time and the walk's travel taken out (the armature in Blender plays the clip in place), and the
   sheet's stride points (left foot ahead, passing, right foot ahead) in the last cycle, the drawn surface its own
   skinned place moved by as much as the sim mesh there stands off its target and shaded by its own smooth normals
   as skinning turns them (`skinned_normals`; the skinned person's own, so a cloth on its targets is drawn exactly
   as the skinned person is); `measures`: each garment's deepest loose point inside the body (the sim mesh's and
   the drawn surface's), its largest stretch, its drift off the skin and its jitter, beside the same numbers for
   plain skinning, and the jeans' flap at the passing step (`flap`: the farthest a lower-leg point stands off the
   body; `swing`: the farthest beyond its standoff at rest) and each garment's hem swing off its skinned place
   (`hem_swing`).

    python -m tools.characters.generated.cloth <body.glb> <clips rig.npz> <out> --height <m> [--tether KIND=M ...]

writes <out>/cloth.npz (what blender_cloth.py draws) and <out>/cloth.json (the kinds' faces, the garments' points and
riding share, the run's engine and seconds, the measures). `blender_cloth.py` draws it beside the skinned person.
"""
import argparse
import json
import pathlib
import sys
import time

import numpy as np
import trimesh
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components, dijkstra
from scipy.spatial import cKDTree
from skimage.color import lab2rgb, rgb2lab

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE.parent / "still_rig"))
import still_rig  # noqa: E402  (still_rig's own import path brings skel_usd and prop_rig)
import skel_usd  # noqa: E402

sys.path.insert(0, str(REPO))
from tools.characters.generated import cloth_mesh, cloth_tether  # noqa: E402

KINDS = ("head", "skin", "jacket", "shirt", "jeans", "shoes", "scarf")
SIMULATED = ("jacket", "jeans", "scarf")  # each moved as cloth where the person wears it (GARMENT_FACES or more)
GARMENT_FACES = 300
THICKNESS_M = {"jacket": 0.006, "jeans": 0.003, "scarf": 0.008}  # the cloth's thickness; half of it its clearance off the body
SETTLE_S = 1.0  # the cloth hangs this long on the first frame before the run
ENGINE = (f"tethered position-based cloth (cloth_tether, numpy on the processor, {cloth_tether.SUBSTEPS} substeps "
          f"a frame, {cloth_tether.ITERATIONS} iterations, deterministic)")
WELD = 1e-6  # metres: shell points this near are one point (still_rig's texture seams split them)
SETTLE = 4  # rounds of neighbour votes on each face's kind
ISLAND_FACES = 150  # a connected piece of a kind with fewer faces joins the kinds round it
KEEP_OWN = 1.5  # a face's own kind's weight in its neighbours' vote
SPREAD_LEAST = 4.0  # CIELAB: a kind's colour spread is never read tighter than this
ARMS = ("LeftArm", "LeftForeArm", "LeftHand", "RightArm", "RightForeArm", "RightHand", "LeftShoulder",
        "RightShoulder")
TRUNK = ("Hips", "Spine1", "Spine2", "Chest", "Neck1")
LEGS = ("LeftLeg", "RightLeg", "LeftShin", "RightShin")
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
SCARF_NECK_M = 0.10  # a scarf rides the skin this far from where it meets the neck, the head and the hair
# A jacket's hem (`jacket_hem`): a long coat or an overshirt hangs past the hips over the trousers; read down in bands
HEM_BAND_M = 0.02  # this tall from TUCKED_M under the hips, while
HEM_SHARE = 0.5  # of its HEM_SECTORS round the band's middle, this share has its outermost clothes face (not the
HEM_SECTORS = 24  # arms, hands, neck or head) nearer the jacket's paint than the jeans' (what is seen from outside: the
# trousers inside a coat and its dark inner wall are not)
# A scarf (`scarf_split`): in the open front over the chest, two colours apart from the jacket's, the one standing
# forward of the other is a scarf over the shirt (the older woman's cream knit over her black turtleneck)
SCARF_FROM_JACKET = 3.0  # a face's colour this many of the jacket's spreads from it is not the jacket's
SCARF_APART = 20.0  # CIELAB: the two colours at least this far apart
SCARF_FORWARD_M = 0.02  # the scarf's faces stand at least this much further forward than the shirt's (medians)
MARGIN_M = 0.012  # the body lies at least this far under the shell
SMOOTH_ROUNDS = 10  # rounds the body's push is smoothed over its edges
WARM_CYCLES = 1  # the clip's cycles run before the film starts (the cloth leaves its first frame's standstill)
SECONDS = 3.0  # the film
STANDING_S = 0.4  # the standing clip run after the hang, its last frame drawn
FPS = 24
CLOSED_DEGREES = 2.0  # a clip whose last frame turns every joint within this of its first repeats its first
LOOK_JOINT = "Hips"
HEM_SWING_M = 0.08  # a garment's hem (`hem_swing`): its loose sim points this near its lowest at rest


# --- 1. the rigged person -------------------------------------------------------------------------------------------

def person_of(path):
    """still_rig's body.glb read back: {document, blob, names, bind, parents, points (welded shell), faces, head
    (each face from the head part), lab (each face's paint, CIELAB), weights (points x joints), normals (the shell's
    own smooth normals, the ones the skinned person is shaded by, averaged where welded)}."""
    document, blob, names, bind, parents = still_rig.skeleton_of(path)
    node = next(node for node in document["nodes"] if node.get("name") == still_rig.OUTFIT)
    picture = None
    all_points, all_faces, all_weights, all_normals, all_head, all_colours, count = [], [], [], [], [], [], 0
    for primitive in document["meshes"][node["mesh"]]["primitives"]:
        attributes = primitive["attributes"]
        points = skel_usd.accessor(document, blob, attributes["POSITION"]).astype(float)
        faces = skel_usd.accessor(document, blob, primitive["indices"]).reshape(-1, 3).astype(int)
        places = file_places(skel_usd.accessor(document, blob, attributes["TEXCOORD_0"]).astype(float))
        joints = skel_usd.accessor(document, blob, attributes["JOINTS_0"]).astype(int)
        shares = skel_usd.accessor(document, blob, attributes["WEIGHTS_0"]).astype(float)
        all_normals.append(skel_usd.accessor(document, blob, attributes["NORMAL"]).astype(float))
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
    normals = np.zeros_like(points)
    np.add.at(normals, index, np.concatenate(all_normals))
    kept = faces_kept(index, np.concatenate(all_faces))
    return {"document": document, "blob": blob, "names": names, "bind": bind, "parents": parents, "points": points,
            "faces": faces, "head": np.concatenate(all_head)[kept], "lab": np.concatenate(all_colours)[kept],
            "weights": weights, "normals": normals / np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-12)}


def base_picture(document, blob, material):
    """A material's base colour map, (rows, columns, 3) in 0..1."""
    import io
    from PIL import Image
    texture = document["materials"][material]["pbrMetallicRoughness"]["baseColorTexture"]["index"]
    view = document["bufferViews"][document["images"][document["textures"][texture]["source"]]["bufferView"]]
    start = view.get("byteOffset", 0)
    return np.asarray(Image.open(io.BytesIO(blob[start:start + view["byteLength"]])).convert("RGB"), float) / 255.0


def file_places(places):
    """glTF texture places (v down from the picture's top) as still_rig.bilinear reads them (v up): read as they
    are, every face's paint came off the picture's mirror row (round 5, 2026-11-27: the stairwell woman's sage jacket and
    blue jeans read as one speckle, so her kinds were her places' alone; the older woman's coat read as trousers)."""
    return np.c_[places[:, 0], 1.0 - places[:, 1]]


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


def allowed(person, middles, strongest, hem=None):
    """{kind: which faces its place allows} for the kinds read from paint (every kind but the head). The jacket reaches
    down to `hem` (`jacket_hem`; TUCKED_M under the hips when None) and onto a leg only where it reaches past that
    (a long coat over the thighs; a short jacket's faces hanging from a leg are the hands' jeans), never on a hand
    under its wrist (the camel coat's paint read nearer the older woman's hands than her fingers' did)."""
    ankle = max(joint_at(person, "LeftFoot")[1], joint_at(person, "RightFoot")[1])
    waist = joint_at(person, "Spine2")[1]
    hips = joint_at(person, "Hips")[1]
    neck = joint_at(person, "Neck2")[1]
    on_arms = np.isin(strongest, ARMS)
    chest = joint_at(person, "Chest")
    front = (np.abs(middles[:, 0] - chest[0]) < SHIRT_HALF_M) & (middles[:, 2] > chest[2])
    short = hips - TUCKED_M
    hem = short if hem is None else min(hem, short)
    hand = np.zeros(len(middles), bool)
    for side in ("Left", "Right"):
        hand |= (strongest == f"{side}Hand") & (middles[:, 1] < joint_at(person, f"{side}Hand")[1])
    return {"skin": np.isin(strongest, SKIN_JOINTS),
            "jacket": (middles[:, 1] > hem) & (~np.isin(strongest, LEGS) | (hem < short)) & ~hand,
            "shirt": front & ~on_arms & (middles[:, 1] > hips - TUCKED_M) & (middles[:, 1] < neck),
            "jeans": ~on_arms & (middles[:, 1] < waist),
            "shoes": middles[:, 1] < ankle + ANKLE_OVER_M,
            "scarf": ~on_arms & (middles[:, 1] > hips - TUCKED_M) & (middles[:, 1] < neck)}


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
    seeded = {kind: found & ~person["head"] for kind, found in seeds(person, middles, strongest).items()}
    seeded.update(scarf_split(person, middles, strongest, seeded))
    read = {kind: centre_spread(colour[found]) for kind, found in seeded.items() if found.any()}
    hem = None
    if "jacket" in read and "jeans" in read:
        nearer = colour_distance(colour, read["jacket"]) < colour_distance(colour, read["jeans"])
        clothes = ~person["head"] & ~np.isin(strongest, ARMS + SKIN_JOINTS)
        hem = jacket_hem(middles, nearer, clothes, joint_at(person, "Hips")[1] - TUCKED_M)
    places = allowed(person, middles, strongest, hem)
    distance = np.full((len(faces), len(KINDS)), np.inf)
    for kind, centre in read.items():
        distance[:, KINDS.index(kind)] = np.where(places[kind], colour_distance(colour, centre), np.inf)
    found = distance.argmin(1)
    found[person["head"]] = KINDS.index("head")
    return islands_joined(faces, settled(faces, found, ~person["head"]), ~person["head"])


def centre_spread(colours):
    """A kind's colour read off its seed faces: (its median, its spread: the median distance from it, at least
    SPREAD_LEAST)."""
    centre = np.median(colours, axis=0)
    return centre, max(SPREAD_LEAST, float(np.median(np.linalg.norm(colours - centre, axis=1))))


def colour_distance(colours, read):
    """Each colour's distance from a kind's (`centre_spread`) in its spreads."""
    return np.linalg.norm(colours - read[0], axis=1) / read[1]


def jacket_hem(middles, nearer, clothes, start):
    """The jacket's hem: from `start` (TUCKED_M under the hips) down, the bottom of the last HEM_BAND_M band in an
    unbroken run seen from outside as the jacket (`outer_share` at least HEM_SHARE; `start` itself when the first
    band is not)."""
    hem = start
    while True:
        band = np.flatnonzero(clothes & (middles[:, 1] <= hem) & (middles[:, 1] > hem - HEM_BAND_M))
        if not len(band) or outer_share(middles[band], nearer[band]) < HEM_SHARE:
            return hem
        hem -= HEM_BAND_M


def outer_share(middles, nearer):
    """The share of HEM_SECTORS round the faces' middle (seen from above) whose outermost face is `nearer`."""
    offsets = middles[:, [0, 2]] - middles[:, [0, 2]].mean(0)
    sector = ((np.arctan2(offsets[:, 1], offsets[:, 0]) + np.pi) / (2 * np.pi) * HEM_SECTORS).astype(int) % HEM_SECTORS
    radius = np.linalg.norm(offsets, axis=1)
    order = np.lexsort((-radius, sector))
    first = order[np.r_[True, sector[order][1:] != sector[order][:-1]]]
    return float(nearer[first].mean())


def scarf_split(person, middles, strongest, seeded):
    """{"scarf": its seed faces, "shirt": the shirt's} when the open front over the chest (SHIRT_HALF_M of its
    middle, in front of it, from Spine1 to Neck2) shows two colours away from the jacket's (SCARF_FROM_JACKET) at least
    SCARF_APART apart, each on GARMENT_FACES faces or more, one standing SCARF_FORWARD_M forward of the other: that
    one is a scarf over the shirt. Else {} (the shirt is read where `seeds` reads it)."""
    from scipy.cluster.vq import kmeans2
    if not seeded["jacket"].any():
        return {}
    chest = joint_at(person, "Chest")
    colour = person["lab"]
    front = ((np.abs(middles[:, 0] - chest[0]) < SHIRT_HALF_M) & (middles[:, 2] > chest[2])
             & (middles[:, 1] > joint_at(person, "Spine1")[1]) & (middles[:, 1] < joint_at(person, "Neck2")[1])
             & ~person["head"] & ~np.isin(strongest, ARMS))
    apart = np.flatnonzero(front & (colour_distance(colour, centre_spread(colour[seeded["jacket"]]))
                                    > SCARF_FROM_JACKET))
    if len(apart) < 2 * GARMENT_FACES:
        return {}
    centres, label = kmeans2(colour[apart], 2, seed=0, minit="++")
    if min(np.bincount(label, minlength=2)) < GARMENT_FACES or np.linalg.norm(centres[0] - centres[1]) < SCARF_APART:
        return {}
    forward = [float(np.median(middles[apart[label == number], 2])) for number in (0, 1)]
    scarf = int(np.argmax(forward))
    if forward[scarf] - forward[1 - scarf] < SCARF_FORWARD_M:
        return {}
    found = {kind: np.zeros(len(middles), bool) for kind in ("scarf", "shirt")}
    found["scarf"][apart[label == scarf]] = True
    found["shirt"][apart[label != scarf]] = True
    return found


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


def under_colours(person, kinds):
    """The body under the clothes' colours, linear RGB (blender_cloth draws it where a gap shows it): the trunk the
    shirt's paint (the jacket's where none shows), the legs the jeans'; each its kind's median paint (round 5,
    2026-11-27: a fixed white T-shirt and blue denim showed as white and blue patches where the older woman's camel
    coat and the hoodie man's overshirt, fused to their arms, opened at the side)."""
    found = []
    for wanted in (("shirt", "jacket"), ("jeans",)):
        kind = next((kind for kind in wanted if (kinds == KINDS.index(kind)).any()), None)
        lab = np.median(person["lab"][kinds == KINDS.index(kind)], axis=0) if kind else np.array([50.0, 0.0, 0.0])
        srgb = np.clip(lab2rgb(lab[None, None])[0, 0], 0.0, 1.0)
        found.append(np.where(srgb <= 0.04045, srgb / 12.92, ((srgb + 0.055) / 1.055) ** 2.4))
    return np.array(found)


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
    """Which of a garment's points ride the skin: the jacket's yoke (under a scarf too) and cuffs, the jeans'
    waistband, a scarf round the neck."""
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
        return ((from_border(("head", "skin", "scarf"), high=chest) < YOKE_M)
                | (from_border(("skin",), low=chest) < CUFF_M))
    if kind == "scarf":
        return from_border(("head", "skin"), high=joint_at(person, "Chest")[1]) < SCARF_NECK_M
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


def skinned_normals(normals, weights, moves):
    """Unit normals turned by their points' blended joint turns over joint moves (frames, joints, 4, 4): (frames,
    points, 3), as the armature turns the skinned person's (a zero normal stays zero: Blender then shades the point
    from its faces, as it does the skinned person's)."""
    turns = np.einsum("pj,fjab->fpab", weights, moves[:, :, :3, :3])
    found = np.einsum("fpab,pb->fpa", np.linalg.inv(turns).transpose(0, 1, 3, 2), normals)
    return found / np.maximum(np.linalg.norm(found, axis=2, keepdims=True), 1e-12)


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


def timing_of(person, clip, scale):
    """A clip's run: the clip tiled over WARM_CYCLES and the film (a walk) or STANDING_S (standing), the person scaled;
    {rate, length, inside, cycle, travel, moves (frames, joints, 4, 4), played}."""
    worlds, rate = clip_of(person, clip)
    length, _ = cycle_of(worlds)
    frames = (length * WARM_CYCLES + int(np.ceil(SECONDS * rate)) + 2 if clip == "walking" else
              int(np.ceil(STANDING_S * rate)))
    played, inside, cycle, travel = tiled(worlds, frames)
    played = scaled(played, scale)
    moves = played @ np.linalg.inv(scaled(person["bind"], scale))
    return {"rate": rate, "length": length, "inside": inside, "cycle": cycle, "travel": travel * scale,
            "moves": moves, "played": played}


def garments_of(person, kinds, body, scale, reach):
    """{kind: (used, faces, riding, sim)} for the simulated garments the person wears (GARMENT_FACES or more), each
    sim mesh with its tethers (`reach`: each kind's longest, cloth_tether.TETHER_M's unless given)."""
    shoes_used, _ = garment_of(person, kinds, "shoes")
    shoes = person["points"][shoes_used] * scale
    garments = {}
    for kind in worn(kinds):
        used, garment_faces = garment_of(person, kinds, kind)
        riding = riding_of(person, kinds, kind, used, garment_faces)
        sim = sim_of(person, kinds, kind, body, scale, used, garment_faces, riding)
        held = cloth_tether.pinned(sim["points"], sim["riding"], shoes)
        sim["tether"] = cloth_tether.tethers(reach[kind], over_surface(sim["points"], sim["faces"],
                                                                         np.flatnonzero(held)))
        garments[kind] = (used, garment_faces, riding, sim)
    return garments


def worn(kinds):
    """The SIMULATED kinds the person wears (GARMENT_FACES faces or more)."""
    return [kind for kind in SIMULATED if (kinds == KINDS.index(kind)).sum() >= GARMENT_FACES]


def moved(sim, kind, timing, body_posed, body_faces):
    """A garment's sim mesh over the run, tethered to its targets (its skinned places), kept out of the body to half
    its thickness or as deep as the skinning draws it, after SETTLE_S held on the first frame; (positions (frames,
    points, 3), seconds)."""
    started = time.monotonic()
    targets = skinned(sim["points"], sim["weights"], timing["moves"])
    least = cloth_tether.allowances(targets, body_posed, body_faces, THICKNESS_M[kind] / 2)
    held = int(round(SETTLE_S * timing["rate"]))

    def led(values):
        return np.concatenate([np.repeat(values[:1], held, axis=0), values])

    gravity = cloth_tether.turned_gravity(sim["weights"], timing["moves"])
    run = cloth_tether.tethered(led(targets), sim["tether"], sim["faces"], led(body_posed), body_faces,
                                timing["rate"], led(least), led(gravity))
    return run[held:], round(time.monotonic() - started, 1)


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


def flap(positions, sim, names, body_posed):
    """The farthest a lower-leg point (mostly on the shin, foot and toes) stands off the posed body at one frame
    (metres): the wide leg's back panel swung up behind the calf as a fin at the passing step stands far off."""
    lower = [names.index(f"{side}{part}") for side in ("Left", "Right") for part in ("Shin", "Foot", "ToeBase",
                                                                                       "ToeEnd")]
    chosen = sim["weights"][:, lower].sum(1) > 0.5
    return round(float(cKDTree(body_posed).query(positions[chosen])[0].max()), 4)


def swing(positions, sim, names, body_posed, body_rest):
    """The farthest a lower-leg point (as `flap` chooses them) stands off the posed body at one frame beyond how far
    it stands off the body at rest (metres): `flap` alone is never under the wide hem's own standoff (12 cm round the
    ankle), so a leg that swings out is told from one that is only wide."""
    lower = [names.index(f"{side}{part}") for side in ("Left", "Right") for part in ("Shin", "Foot", "ToeBase",
                                                                                       "ToeEnd")]
    chosen = sim["weights"][:, lower].sum(1) > 0.5
    rest = cKDTree(body_rest).query(sim["points"][chosen])[0]
    return round(float((cKDTree(body_posed).query(positions[chosen])[0] - rest).max()), 4)


def hem_swing(cloth, carried, sim, passing):
    """How far a garment's hem (its loose sim points within HEM_SWING_M of its lowest at rest) swings off its skinned
    place (metres): the most over the run and at the passing step."""
    loose = ~sim["riding"]
    hem = loose & (sim["points"][:, 1] < sim["points"][loose, 1].min() + HEM_SWING_M) if loose.any() else loose
    if not hem.any():
        return {"hem_swing_most_m": 0.0, "hem_swing_passing_m": 0.0}
    off = np.linalg.norm(cloth[:, hem] - carried[:, hem], axis=2)
    return {"hem_swing_most_m": round(float(off.max()), 4), "hem_swing_passing_m": round(float(off[passing].max()), 4)}


def frames_of(person, timing, clip):
    """{name: run frame} drawn from a clip: the film's start and the stride points of a walk, standing's last."""
    if clip == "standing":
        return {"standing": len(timing["played"]) - 3}
    return {"film": timing["length"] * WARM_CYCLES, **stride_points(person, timing)}


def made(body_glb, rig_path, out, height, reach=None):
    """The whole make: kinds, garments, body, the walking and standing runs, cloth.npz and cloth.json in `out`; each
    garment measured as tethered cloth (`garments`) and as plain skinning (`skinned`). `reach`: a garment's longest
    tether where the person's clothes want other than cloth_tether.TETHER_M (an open overshirt's fronts, a long
    coat's hem)."""
    reach = {**cloth_tether.TETHER_M, **(reach or {})}
    out.mkdir(parents=True, exist_ok=True)
    person = person_of(body_glb)
    kinds = kinds_of(person)
    body = body_under(person, dict(np.load(rig_path)))
    scale = height / float(np.ptp(person["points"][:, 1]))
    saved = {"scale": scale, "kinds": kinds, "shell_points": person["points"], "shell_faces": person["faces"],
             "body_points": body[0], "body_faces": body[1], "body_weights": body[2],
             "joint_names": np.array(person["names"]), "kind_names": np.array(KINDS),
             "simulated": np.array(worn(kinds)), "under_colours": under_colours(person, kinds)}
    record = {"body": str(body_glb), "height_m": height, "scale": round(scale, 4),
              "faces": {kind: int((kinds == number).sum()) for number, kind in enumerate(KINDS)},
              "tether_m": {kind: reach[kind] for kind in worn(kinds)}, "runs": {}}
    garments = garments_of(person, kinds, body, scale, reach)
    for clip in ("walking", "standing"):
        timing = timing_of(person, clip, scale)
        frames = frames_of(person, timing, clip)
        body_posed = skinned(body[0] * scale, body[2], timing["moves"])
        run = {"engine": ENGINE, "seconds": 0.0, "rate": timing["rate"], "cycle_frames": timing["length"],
               "frames": frames, "garments": {}, "skinned": {}}
        for kind, (used, faces, riding, sim) in garments.items():
            cloth, seconds = moved(sim, kind, timing, body_posed, body[1])
            run["seconds"] = round(run["seconds"] + seconds, 1)
            carried = skinned(sim["points"], sim["weights"], timing["moves"])
            own = skinned(person["points"][used] * scale, person["weights"][used], timing["moves"])
            shape = {"points": len(used), "sim_points": len(sim["points"]), "sim_faces": len(sim["faces"]),
                     "riding_share": round(float(sim["riding"].mean()), 3)}
            for label, positions in (("garments", cloth), ("skinned", carried)):
                drawn = own + cloth_mesh.displaced(sim["binding"], positions, carried, sim["faces"])
                run[label][kind] = {**shape, **measures(positions, sim, carried, drawn, ~riding, body_posed, body[1])}
                if clip == "walking":
                    run[label][kind].update(hem_swing(positions, carried, sim, frames["passing"]))
                if kind == "jeans" and clip == "walking":
                    passing = frames["passing"]
                    run[label][kind]["flap_passing_m"] = flap(positions[passing], sim, person["names"],
                                                              body_posed[passing])
                    run[label][kind]["swing_passing_m"] = swing(positions[passing], sim, person["names"],
                                                                body_posed[passing], body[0] * scale)
            drawn = own + cloth_mesh.displaced(sim["binding"], cloth, carried, sim["faces"])
            normals = skinned_normals(person["normals"][used], person["weights"][used], timing["moves"])
            del own
            saved[f"{kind}_used"], saved[f"{kind}_faces"], saved[f"{kind}_riding"] = used, faces, riding
            saved[f"{kind}_sim_points"], saved[f"{kind}_sim_faces"] = sim["points"] / scale, sim["faces"]
            for name, frame in frames.items():
                count = int(SECONDS * FPS) if name == "film" else 1
                film, times = resampled(drawn, timing, frame, count)
                saved[f"{clip}/{name}/{kind}"] = film / scale
                turned = at_times(normals, frame + np.arange(count) * timing["rate"] / FPS)
                saved[f"{clip}/{name}/{kind}_normal"] = (
                    turned / np.maximum(np.linalg.norm(turned, axis=2, keepdims=True), 1e-12)).astype(np.float32)
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
    parser.add_argument("--tether", action="append", default=[], metavar="KIND=M",
                        help="a garment's longest tether in metres (cloth_tether.TETHER_M's otherwise)")
    options = parser.parse_args()
    reach = {kind: float(metres) for kind, metres in (given.split("=") for given in options.tether)}
    record = made(options.body, options.rig, options.out, options.height, reach)
    print(f"cloth: {record['faces']}; " + "; ".join(
        f"{clip} {run['seconds']} s: " + ", ".join(f"{kind} deepest {found['deepest_m']} m stretch "
                                                    f"{found['largest_stretch']}" for kind, found in
                                                    run["garments"].items()) for clip, run in record["runs"].items()),
          flush=True)


if __name__ == "__main__":
    main()
