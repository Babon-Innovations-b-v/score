"""Measures a built body file at its joins and its stance, in every frame of every clip: no judgement.

    .venv/bin/python tools/characters/people/joins.py BODY.glb [BODY.glb ...] --out DIR [--record-only]

Exits 1 when any body fails a measure; the maker's chain runs it after each build with --record-only and keeps the
records in out/checks/.

**The joins.** Only the head and the hands of the body itself are drawn; everything else is clothes, so wherever an
end piece (a hand, a mitt, a glove, a boot, a shoe) does not reach into the clothes next to it the background shows
through (owner, 2026-10-09: "their hands aren't attached to their forearms"; the boots float under the trousers).
For each side, each outfit and each frame, a wrist is measured along the forearm (the forearm joint to the hand
joint) and an ankle down the shin (the shin joint to the foot joint), two ways. The overlap: how far the sleeve
reaches past where the hand begins, or the trouser leg past where the boot begins (its top); negative is a gap one
sees through. The opening: how far the hand's or boot's open end (its first START_BAND metres) lies from the sleeve
or trouser leg at its worst point, which shows a cuff or hem cut on a slant. Only the overlap is judged: loose
cloth stands 5 to 15 cm off a wrist or a boot in joins the renders show closed (the space suits; a crouch), so the
opening is recorded for a reader and never passes or fails a body. The clothes are measured over their
triangles, not only their corners; a hand or boot point pressed into the body's or another limb's clothes (folded
arms, a hand on the thigh) is hidden there and not counted.

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
from scipy.spatial import cKDTree

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
# A hand or a boot's open end: its first START_BAND metres along the limb.
START_BAND = 0.05
# The grid of points laid over each triangle of a sleeve or a trouser leg, this many a side.
SAMPLES_A_SIDE = 4
# A hand or boot point this close to the clothes of the body or another limb is hidden by them.
BURIED = 0.02
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
    strongest joint, and its triangles."""

    def __init__(self, name, points, joints, weights, faces):
        self.name = name
        self.points = points
        self.joints = joints.astype(int)
        self.weights = weights
        self.strongest = joints[np.arange(len(joints)), weights.argmax(axis=1)].astype(int)
        self.faces = faces


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


def start_of(inner_points, start, end, reach=REACH):
    """Where the inner piece (a hand, a boot) begins along the limb from `start` to `end`, and its points within
    START_BAND of that: its open end, never its fingers or its toe."""
    inner, near = along(inner_points, start, end, reach)
    if not near.any():
        return float("nan"), np.zeros((0, 3))
    begins = float(inner[near].min())
    return begins, inner_points[near & (inner < begins + START_BAND)]


def overlap(outer_points, begins, start, end, reach=REACH):
    """How far the outer piece (a sleeve, a trouser leg) reaches along the limb past `begins`, where the inner piece
    begins: positive when they overlap, negative a gap."""
    outer, near = along(outer_points, start, end, reach)
    if not near.any() or np.isnan(begins):
        return float("nan")
    return float(outer[near].max() - begins)


def opening(outer_points, inner_end, covered):
    """How far the inner piece's open end lies from the outer piece at its worst point, over the part of it the outer
    piece reaches past (`covered`; all of it where it reaches past none): a cuff or a hem cut on a slant reaches past
    the hand or the boot on one side and leaves it bare on the other."""
    if not len(inner_end) or not len(outer_points):
        return float("nan")
    distance, _ = cKDTree(outer_points).query(inner_end[covered] if covered.any() else inner_end)
    return float(distance.max())


def stance_ratio(joint_worlds, joint_names):
    """The ankles' spacing across the hips (along the line between the hip joints, on the floor) over the hip joints'
    spacing, for one frame's joint places: a step forward is not width."""
    place = {name: joint_worlds[joint_names.index(name), :3, 3] for name in ("LeftLeg", "RightLeg", "LeftFoot", "RightFoot")}
    hips = (place["LeftLeg"] - place["RightLeg"])[[0, 2]]
    hip_spacing = float(np.linalg.norm(hips))
    ankles = (place["LeftFoot"] - place["RightFoot"])[[0, 2]]
    return abs(float(ankles @ hips)) / hip_spacing / hip_spacing


def surface_samples(points, faces):
    """Points spread over each triangle (a grid of SAMPLES_A_SIDE a side), so a thinned cloth's few large triangles
    at a cuff are measured where they are, not only at their corners."""
    steps = SAMPLES_A_SIDE
    shares = np.array([(first, second, steps - first - second) for first in range(steps + 1)
                       for second in range(steps + 1 - first)], float) / steps
    return np.einsum("sc,fcd->fsd", shares, points[faces]).reshape(-1, 3)


def gather(part_points, chosen, surface=False):
    """The chosen points of each (part, which) pair, skinned already in `part_points`, as one array; with `surface`,
    points over the triangles all of whose corners are chosen as well."""
    pieces = []
    for part, which in chosen:
        moved = part_points[id(part)]
        pieces.append(moved[which])
        if surface:
            pieces.append(surface_samples(moved, part.faces[which[part.faces].all(axis=1)]))
    return np.concatenate(pieces) if pieces else np.zeros((0, 3))


def elsewhere(parts, part_points, side, chain, joint_names):
    """The clothes' points not on the side's limb `chain`: the body and the other limbs, which can hide a join."""
    mine = {joint_names.index(side + joint) for joint in chain if side + joint in joint_names}
    pieces = [part_points[id(part)][~np.isin(part.strongest, list(mine))]
              for part in parts if part.name in SLEEVES + TROUSERS]
    return np.concatenate(pieces) if pieces else np.zeros((0, 3))


def unburied(points, cover, within=BURIED):
    """The points not within `within` of any of `cover`'s: a hand tucked under the other arm (folded arms) or pressed
    into the chest shows no gap, wherever its own sleeve ends."""
    if not len(points) or not len(cover):
        return points
    low, high = points.min(axis=0) - within, points.max(axis=0) + within
    cover = cover[((cover >= low) & (cover <= high)).all(axis=1)]
    if not len(cover):
        return points
    nearest, _ = cKDTree(cover).query(points, distance_upper_bound=within)
    return points[~np.isfinite(nearest)]


def measure_join(outer, inner, start, end):
    """One join's (overlap, opening), NaN for both where either piece is missing."""
    if not len(outer) or not len(inner):
        return float("nan"), float("nan")
    begins, inner_end = start_of(inner, start, end)
    reaches = overlap(outer, begins, start, end)
    covered = along(inner_end, start, end, np.inf)[0] <= begins + reaches
    return reaches, opening(outer, inner_end, covered)


def joins_of_a_frame(parts, part_points, joint_places, joint_names):
    """One frame's joins, {"wrist_Left": overlap, "wrist_Left_opening": opening, ... ankle_Right ...}, NaN where the
    outfit has no such pieces."""
    found = {}
    for side in ("Left", "Right"):
        place = {name: joint_places[joint_names.index(side + name)] for name in ("ForeArm", "Hand", "Shin", "Foot")}
        hand = unburied(gather(part_points, points_of(parts, HANDS, side, ARM, joint_names)),
                        elsewhere(parts, part_points, side, ARM, joint_names))
        sleeve = gather(part_points, points_of(parts, SLEEVES, side, ARM, joint_names), surface=True)
        found[f"wrist_{side}"], found[f"wrist_{side}_opening"] = measure_join(sleeve, hand, place["ForeArm"],
                                                                              place["Hand"])
        boot = unburied(gather(part_points, points_of(parts, BOOTS, side, LEG, joint_names)),
                        elsewhere(parts, part_points, side, LEG, joint_names))
        trousers = gather(part_points, points_of(parts, TROUSERS, side, LEG, joint_names), surface=True)
        # Down the shin the trouser leg is the outer piece, reaching past where the boot begins (its top).
        found[f"ankle_{side}"], found[f"ankle_{side}_opening"] = measure_join(trousers, boot, place["Shin"],
                                                                              place["Foot"])
    return found


def worse(join, old, new):
    """The worse of two values of a join: the smaller overlap, the larger opening."""
    if old is None:
        return new
    return max(old, new) if join.endswith("_opening") else min(old, new)


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
                        worst[outfit][join] = worse(join, worst[outfit].get(join), value)
        for outfit in dressed:
            record["outfits"][outfit][animation["name"]] = {join: round(value, 4)
                                                            for join, value in sorted(worst[outfit].items())}
        if ratios:
            record["stance"] = {"clip": STANDING, "mean": round(float(np.mean(ratios)), 3),
                                "widest": round(float(np.max(ratios)), 3), "frames": len(ratios)}
    return record


def verdict(record):
    """The record's worst wrist and ankle over every outfit and clip (the least overlap, the widest opening), whether
    each overlap and the stance pass."""
    worst = {}
    for clips in record["outfits"].values():
        for joins in clips.values():
            for join, value in joins.items():
                kind = join.split("_")[0] + ("Opening" if join.endswith("_opening") else "Overlap")
                worst[kind] = worse(join, worst.get(kind), value)
    found = {}
    for kind in ("wrist", "ankle"):
        overlap_value, opening_value = worst.get(kind + "Overlap"), worst.get(kind + "Opening")
        found[kind] = None if overlap_value is None else {
            "worstOverlapMetres": round(overlap_value, 4), "worstOpeningMetres": round(opening_value, 4),
            "pass": overlap_value >= LEAST_OVERLAP}
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
