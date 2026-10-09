"""Measures a built body file at its joins and its stance, in every frame of every clip: numpy only, no judgement.

    .venv/bin/python tools/characters/people/joins.py BODY.glb [BODY.glb ...] --out DIR [--record-only]

Exits 1 when any body fails a measure; the maker's chain runs it after each build with --record-only and keeps the
records in out/checks/.

**The joins.** Only the head and the hands of the body itself are drawn; everything else is clothes, so wherever an
end piece (a hand, a mitt, a glove, a boot, a shoe) does not reach into the clothes next to it the background shows
through (owner, 2026-10-09: "their hands aren't attached to their forearms"; the boots float under the trousers).
For each side, each outfit and each frame, a wrist is measured along the forearm (the forearm joint to the hand
joint) and an ankle down the shin (the shin joint to the foot joint): how far the sleeve reaches past where the hand
begins, and how far the trouser leg reaches past where the boot begins (its top). A negative overlap is a gap one
sees through. The hand begins at its open rim (the body's own hand, cut at the wrist), the boot at its top; the sleeve or the trouser leg ends at
its furthest, both measured in each wedge round the limb, since a slanted cuff or hem leaves a gap on one side
only, and the worst wedge is the join's number.

**The stance.** In the standing clip, the spacing of the two ankles (the foot joints) across the hips over the
spacing of the two hip joints (the thigh joints). McIlroy and Maki (1997, "Preferred placement of the feet during
quiet stance", Clinical Biomechanics 12(1):66-70) measured adults standing as they chose: heel centres 0.17 m apart
on average with 14 degrees between the feet. This skeleton's hip joints are 0.20 m apart, so a relaxed stance is a
ratio of about 0.85; `RELAXED_STANCE` keeps 0.55 to 1.2 (heels 0.11 to 0.24 m apart). The crew bodies the owner
approved are no reference here: they play the same Kimodo clips, and stand at 2.1.

The file is read as the engine reads it (the skin's own joints, inverse bind matrices and four weights a point), so
what this measures is what the game and the review renders draw.
"""
import argparse
import json
import pathlib
import struct
import sys

import numpy as np

_COMPONENTS = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
_WIDTH = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}

# The parts of an outfit by what they are at a join. A name is matched whole, or by its start where it ends in a side.
HANDS = ("skin_hands", "mitt_l", "mitt_r", "gloves")
SLEEVES = ("work_cloth", "cloth", "jacket", "wrist_ring_l", "wrist_ring_r")
BOOTS = ("work_boot_Left", "work_boot_Right", "boot_l", "boot_r", "shoe_Left", "shoe_Right")
TROUSERS = ("work_cloth", "cloth", "trousers")
AT_A_JOIN = set(HANDS + SLEEVES + BOOTS + TROUSERS)
# The joints a sleeve or a trouser leg hangs from at a join, by side; a point counts when its strongest joint is one.
ARM = ("ForeArm", "Hand")
LEG = ("Shin", "Foot", "ToeBase")
# How far from the limb's line a point of the clothes may be and still count as the sleeve or the trouser leg.
REACH = 0.15
# The wedges round a limb each measured on its own, round the middle of the inner piece's first BEGINNING metres.
BINS = 12
BEGINNING = 0.03
# The least a sleeve must reach past the hand, and a boot past the trouser leg, so nothing is seen between them from
# any side: a sleeve or a hem stands a centimetre or two off the arm or the boot.
LEAST_OVERLAP = 0.01
# The ankles' spacing over the hip joints' in a relaxed stance (the header says where it comes from).
RELAXED_STANCE = (0.55, 1.2)
STANDING = "standing"


# --- reading the file -----------------------------------------------------------------------------------------------

def read_glb(path):
    """The file as (document, its binary chunk)."""
    data = pathlib.Path(path).read_bytes()
    length = struct.unpack("<I", data[12:16])[0]
    document = json.loads(data[20:20 + length])
    rest = data[20 + length:]
    return document, rest[8:8 + struct.unpack("<I", rest[:4])[0]]


def accessor(document, blob, index):
    """One accessor's values as an array of (count, width), or (count,) for scalars."""
    found = document["accessors"][index]
    view = document["bufferViews"][found["bufferView"]]
    kind = np.dtype(_COMPONENTS[found["componentType"]])
    width = _WIDTH[found["type"]]
    start = view.get("byteOffset", 0) + found.get("byteOffset", 0)
    values = np.frombuffer(blob, kind, found["count"] * width, start).astype(np.float64)
    if found.get("normalized"):
        values = values / np.iinfo(kind).max
    return values.reshape(found["count"], width) if width > 1 else values


# --- posing ---------------------------------------------------------------------------------------------------------

def quaternion_matrices(quaternions):
    """Rotation matrices of (n, 4) quaternions given as x y z w."""
    x, y, z, w = (quaternions / np.linalg.norm(quaternions, axis=1, keepdims=True)).T
    return np.stack([
        np.stack([1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)], axis=-1),
        np.stack([2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)], axis=-1),
        np.stack([2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)], axis=-1)], axis=1)


def node_rest(document):
    """Every node's own rotation (x y z w), translation and scale, as the file holds them at rest."""
    nodes = document["nodes"]
    rotations = np.array([node.get("rotation", [0, 0, 0, 1]) for node in nodes], np.float64)
    translations = np.array([node.get("translation", [0, 0, 0]) for node in nodes], np.float64)
    scales = np.array([node.get("scale", [1, 1, 1]) for node in nodes], np.float64)
    return rotations, translations, scales


def clip_frames(document, blob, animation):
    """A clip's keyed values, frame by frame: (rotations, translations) of shape (frames, nodes, 4 or 3)."""
    rotations, translations, _ = node_rest(document)
    keyed = {}
    frames = 1
    for channel in animation["channels"]:
        path = channel["target"]["path"]
        if path not in ("rotation", "translation"):
            continue
        values = accessor(document, blob, animation["samplers"][channel["sampler"]]["output"])
        keyed[(channel["target"]["node"], path)] = values
        frames = max(frames, len(values))
    all_rotations = np.repeat(rotations[None], frames, 0)
    all_translations = np.repeat(translations[None], frames, 0)
    for (node, path), values in keyed.items():
        target = all_rotations if path == "rotation" else all_translations
        target[:len(values), node] = values
        target[len(values):, node] = values[-1]
    return all_rotations, all_translations


def parents_of(document):
    """Each node's parent, or -1."""
    parent = np.full(len(document["nodes"]), -1)
    for number, node in enumerate(document["nodes"]):
        for child in node.get("children", []):
            parent[child] = number
    return parent


def world_matrices(rotations, translations, scales, parent):
    """Every node's place in the world, (nodes, 4, 4), from its own transform and its parents'."""
    count = len(parent)
    local = np.zeros((count, 4, 4))
    local[:, :3, :3] = quaternion_matrices(rotations) * scales[:, None, :]
    local[:, :3, 3] = translations
    local[:, 3, 3] = 1.0
    world = np.zeros_like(local)
    done = np.zeros(count, bool)

    def place(node):
        if not done[node]:
            world[node] = local[node] if parent[node] < 0 else place(parent[node]) @ local[node]
            done[node] = True
        return world[node]

    for node in range(count):
        place(node)
    return world


def skinned(points, joints, weights, joint_worlds, inverse_bind):
    """Points moved as the engine moves them: four joints a point, the skin's joints' worlds times their inverse
    bind matrices."""
    moves = joint_worlds @ inverse_bind
    homogeneous = np.concatenate([points, np.ones((len(points), 1))], axis=1)
    out = np.zeros((len(points), 3))
    for slot in range(joints.shape[1]):
        out += weights[:, slot, None] * np.einsum("pij,pj->pi", moves[joints[:, slot]], homogeneous)[:, :3]
    return out


# --- the file's parts -----------------------------------------------------------------------------------------------

class Part:
    """One drawn surface of an outfit: its name, points, each point's four joints and weights (skin indices), its
    strongest joint, and which points lie on its open rim."""

    def __init__(self, name, points, joints, weights, faces):
        self.name = name
        self.points = points
        self.joints = joints.astype(int)
        self.weights = weights
        self.strongest = joints[np.arange(len(joints)), weights.argmax(axis=1)].astype(int)
        self.rim = on_the_rim(points, faces)


def on_the_rim(points, faces):
    """Which points lie on an edge only one triangle has: the open rim of a hand or a boot. Points at one place are
    taken as one first, since a painted part is split along its picture's seams."""
    _, welded = np.unique(np.round(points, 5), axis=0, return_inverse=True)
    welded = welded.ravel()[faces]
    edges = np.sort(np.concatenate([welded[:, [0, 1]], welded[:, [1, 2]], welded[:, [2, 0]]]), axis=1)
    unique, counts = np.unique(edges, axis=0, return_counts=True)
    open_places = np.zeros(welded.max() + 1, bool)
    open_places[unique[counts == 1].ravel()] = True
    _, place_of = np.unique(np.round(points, 5), axis=0, return_inverse=True)
    return open_places[place_of.ravel()]


def outfits(document, blob):
    """Every skinned node that is an outfit (not the bare distant body) with its parts: {node name: [Part]}."""
    found = {}
    for node in document["nodes"]:
        if "mesh" not in node or "skin" not in node or node.get("name") == "far":
            continue
        parts = []
        for primitive in document["meshes"][node["mesh"]]["primitives"]:
            attributes = primitive["attributes"]
            if "JOINTS_0" not in attributes or "material" not in primitive:
                continue
            parts.append(Part(document["materials"][primitive["material"]]["name"],
                              accessor(document, blob, attributes["POSITION"]),
                              accessor(document, blob, attributes["JOINTS_0"]),
                              accessor(document, blob, attributes["WEIGHTS_0"]),
                              accessor(document, blob, primitive["indices"]).astype(int).reshape(-1, 3)))
        if parts:
            found[node["name"]] = parts
    return found


def side_of(name):
    """"Left" or "Right" for a part named for one side, else None."""
    if name.endswith(("_l", "_Left")):
        return "Left"
    if name.endswith(("_r", "_Right")):
        return "Right"
    return None


def points_of(parts, names, side, chain, joint_names):
    """The points of the parts named in `names`, on `side`, whose strongest joint is one of the side's `chain`:
    (part, which points) pairs."""
    wanted = {joint_names.index(side + joint) for joint in chain if side + joint in joint_names}
    picked = []
    for part in parts:
        if part.name not in names or side_of(part.name) not in (None, side):
            continue
        mine = np.isin(part.strongest, list(wanted))
        if mine.any():
            picked.append((part, mine))
    return picked


# --- the measures ---------------------------------------------------------------------------------------------------

def along(points, start, end, reach):
    """Each point's distance along the line from `start` towards `end`, and whether it lies within `reach` of it."""
    axis = (end - start) / np.linalg.norm(end - start)
    offset = points - start
    distance = offset @ axis
    off_the_line = np.linalg.norm(offset - distance[:, None] * axis, axis=1)
    return distance, off_the_line < reach


def overlap(outer_points, inner_points, start, end, reach=REACH, bins=BINS):
    """How far the outer piece (a sleeve, a trouser leg) reaches past where the inner piece (a hand, a boot) begins,
    along the limb from `start` to `end`, on the worst side round it: positive when they overlap, negative a gap; NaN
    when either is not there. The limb is cut into `bins` wedges round a line along it through the middle of where
    the inner piece begins, and each wedge is measured on its own, since a slanted cuff or hem leaves a gap on one
    side only."""
    axis = (end - start) / np.linalg.norm(end - start)
    inner, near_inner = along(inner_points, start, end, reach)
    if not near_inner.any() or not len(outer_points):
        return float("nan")
    begins = near_inner & (inner < inner[near_inner].min() + BEGINNING)
    centre = inner_points[begins].mean(axis=0)
    across = np.cross(axis, [0.0, 1.0, 0.0] if abs(axis[1]) < 0.9 else [1.0, 0.0, 0.0])
    across /= np.linalg.norm(across)
    third = np.cross(axis, across)

    def wedges(points):
        distance, near = along(points, centre, centre + axis, reach)
        offset = points - centre
        wedge = ((np.arctan2(offset @ third, offset @ across) + np.pi) / (2 * np.pi) * bins).astype(int) % bins
        return distance[near], wedge[near]

    outer, outer_wedge = wedges(outer_points)
    inner, inner_wedge = wedges(inner_points)
    worst = float("inf")
    for wedge in range(bins):
        mine, theirs = outer_wedge == wedge, inner_wedge == wedge
        if mine.any() and theirs.any():
            worst = min(worst, outer[mine].max() - inner[theirs].min())
    return float(worst) if np.isfinite(worst) else float("nan")


def stance_ratio(joint_worlds, joint_names):
    """The ankles' spacing across the hips (along the line between the hip joints, on the floor) over the hip joints'
    spacing, for one frame's joint places: a step forward is not width."""
    place = {name: joint_worlds[joint_names.index(name), :3, 3] for name in ("LeftLeg", "RightLeg", "LeftFoot", "RightFoot")}
    hips = (place["LeftLeg"] - place["RightLeg"])[[0, 2]]
    hip_spacing = float(np.linalg.norm(hips))
    ankles = (place["LeftFoot"] - place["RightFoot"])[[0, 2]]
    return abs(float(ankles @ hips)) / hip_spacing / hip_spacing


def gather(part_points, chosen, rim=False):
    """The chosen points of each (part, which) pair, skinned already in `part_points`, as one array; with `rim`, only
    those on the part's open rim where it has one."""
    pieces = [part_points[id(part)][which & part.rim if rim and (which & part.rim).any() else which]
              for part, which in chosen]
    return np.concatenate(pieces) if pieces else np.zeros((0, 3))


def joins_of_a_frame(parts, part_points, joint_places, joint_names):
    """One frame's overlaps, {"wrist_Left": m, "wrist_Right": m, "ankle_Left": m, "ankle_Right": m}, NaN where the
    outfit has no such pieces."""
    found = {}
    for side in ("Left", "Right"):
        place = {name: joint_places[joint_names.index(side + name)] for name in ("ForeArm", "Hand", "Shin", "Foot")}
        hand = gather(part_points, points_of(parts, HANDS, side, ARM, joint_names), rim=True)
        sleeve = gather(part_points, points_of(parts, SLEEVES, side, ARM, joint_names))
        found[f"wrist_{side}"] = (overlap(sleeve, hand, place["ForeArm"], place["Hand"])
                                  if len(hand) and len(sleeve) else float("nan"))
        boot = gather(part_points, points_of(parts, BOOTS, side, LEG, joint_names))
        trousers = gather(part_points, points_of(parts, TROUSERS, side, LEG, joint_names))
        # Down the shin the trouser leg is the outer piece, reaching past where the boot begins (its top).
        found[f"ankle_{side}"] = (overlap(trousers, boot, place["Shin"], place["Foot"])
                                  if len(boot) and len(trousers) else float("nan"))
    return found


def measure_body(path):
    """Every clip's worst join per outfit and side, and the standing clip's stance: the body's record."""
    document, blob = read_glb(path)
    skin = document["skins"][0]
    skin_joints = skin["joints"]
    joint_names = [document["nodes"][node]["name"] for node in skin_joints]
    inverse_bind = accessor(document, blob, skin["inverseBindMatrices"]).reshape(-1, 4, 4).transpose(0, 2, 1)
    parent = parents_of(document)
    _, _, scales = node_rest(document)
    dressed = outfits(document, blob)
    record = {"body": str(path), "outfits": {}, "stance": None}
    for outfit, parts in dressed.items():
        record["outfits"][outfit] = {}
    for animation in document.get("animations", []):
        rotations, translations = clip_frames(document, blob, animation)
        worst = {outfit: {} for outfit in dressed}
        ratios = []
        for frame in range(len(rotations)):
            world = world_matrices(rotations[frame], translations[frame], scales, parent)
            joint_worlds = world[skin_joints]
            joint_places = joint_worlds[:, :3, 3]
            if animation.get("name") == STANDING:
                ratios.append(stance_ratio(joint_worlds, joint_names))
            for outfit, parts in dressed.items():
                part_points = {id(part): skinned(part.points, part.joints, part.weights, joint_worlds, inverse_bind)
                               for part in parts if part.name in AT_A_JOIN}
                for join, value in joins_of_a_frame(parts, part_points, joint_places, joint_names).items():
                    if not np.isnan(value):
                        worst[outfit][join] = min(worst[outfit].get(join, value), value)
        for outfit in dressed:
            record["outfits"][outfit][animation["name"]] = {join: round(value, 4)
                                                            for join, value in sorted(worst[outfit].items())}
        if ratios:
            record["stance"] = {"clip": STANDING, "mean": round(float(np.mean(ratios)), 3),
                                "widest": round(float(np.max(ratios)), 3), "frames": len(ratios)}
    return record


def verdict(record):
    """The record's worst wrist and ankle over every outfit and clip, and whether each and the stance pass."""
    worst = {"wrist": float("inf"), "ankle": float("inf")}
    for clips in record["outfits"].values():
        for joins in clips.values():
            for join, value in joins.items():
                kind = join.split("_")[0]
                worst[kind] = min(worst[kind], value)
    found = {}
    for kind, value in worst.items():
        found[kind] = None if value == float("inf") else {"worstOverlapMetres": round(value, 4),
                                                           "pass": value >= LEAST_OVERLAP}
    stance = record["stance"]
    found["stance"] = None if stance is None else {
        "ratio": stance["mean"], "pass": RELAXED_STANCE[0] <= stance["mean"] <= RELAXED_STANCE[1]}
    return found


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("bodies", nargs="+")
    parser.add_argument("--out", required=True, help="the folder each body's record is written to, as <name>.json")
    parser.add_argument("--record-only", action="store_true", help="write the records and exit 0 whatever they say")
    arguments = parser.parse_args()
    out = pathlib.Path(arguments.out)
    out.mkdir(parents=True, exist_ok=True)
    failed = []
    for body in arguments.bodies:
        record = measure_body(body)
        record["verdict"] = verdict(record)
        name = pathlib.Path(body).stem
        (out / f"{name}.json").write_text(json.dumps(record, indent=1))
        line = {kind: (None if value is None else
                       (value.get("worstOverlapMetres", value.get("ratio")), "ok" if value["pass"] else "FAIL"))
                for kind, value in record["verdict"].items()}
        print(name, line)
        if any(value is not None and not value["pass"] for value in record["verdict"].values()):
            failed.append(name)
    if failed:
        print("failed:", " ".join(failed))
        if not arguments.record_only:
            sys.exit(1)


if __name__ == "__main__":
    main()
