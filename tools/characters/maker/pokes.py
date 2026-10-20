"""The prop route's per-frame poke check of a built person: what shows through what, in every frame of every clip,
read from the built glTF as the engine skins it (people/joins.py's reader). Measures; it does not judge by eye.

    ~/.farm-factory-props/env/bin/python tools/characters/maker/pokes.py <body.glb> --out <pokes.json> [--every 1]
        [--against <the shipped body's pokes.json>]

- tuck_out_mm: each tuck (a band run on under a garment from a skin part, a boot or a mitt, tucks.py; its points from
  the material's `tuck_from`) point's distance outside the person's closed surface (every surface but the bands,
  welded back into the one watertight Pixal3D mesh they were cut from, in the frame's pose): a tuck showing through
  its sleeve, collar or trouser leg. Signed by the nearest face's normal instead, a band under a sleeve next to the
  bent wrist read out where the nearest face was the hand's own; by the nearest garment point's averaged normal, a
  collar's rim read a tuck under it as 2 cm out. Per clip the worst frame and how many frames have a point over POKE_MM.
- cloth_crossings: how many garment edges pass through a garment triangle they share no corner with
  (drape_measure.self_crossings, the garment parts welded where their borders meet), in the bind pose and in every `--every`-th frame (every CROSSING_EVERY-th by
  default): cloth gone through cloth. A Pixal3D surface may cross itself at rest; a frame is counted as poking where
  it crosses more than the rest does.
- rigid_stretch: each hard part's own edges (boots, belt, buckle, helmet, pack: role "hard", its tuck left out) at
  their longest against the bind pose, per clip the worst frame's largest ratio: a hard part riding one joint stays at
  1.0; the gate is RIGID_MOST (plan step 3; the review found the boots at 6.7 and 8.2, 2026-10-10).
- A settled body's garments carry morph targets keyed per clip (garment_bake.py); every frame is posed with them, as
  the engine plays it.
- A body built by the shipped route (no roles in its materials) is read the same way, its garments by joins.py's names
  and no tucks, so a candidate's crossings can be set beside the shipped body's.
- verdict: pass when no frame has a tuck point over POKE_MM outside, and (with `--against`, the shipped body's record)
  no clip's garments cross more often than the shipped body's in the same clip; without it, than at rest. The shipped
  player's garments cross 4,427 times at rest and 5,443 in a median clip's worst frame (its pockets and patches lie
  through its cloth), so "no more than at rest" fails every body; the shipped record is the bar.
"""
import argparse
import json
import pathlib
import sys

import numpy as np
import trimesh

MAKER = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(MAKER))
sys.path.insert(0, str(MAKER.parent / "people"))

import drape_measure  # noqa: E402
import joins  # noqa: E402

POKE_MM = 5.0
RIGID_MOST = 1.2
HARD = "hard"
WELD_DIGITS = 6
CROSSING_EVERY = 5
GARMENT = "garment"


def surfaces(document, blob, outfit=None):
    """The outfit's surfaces with their role and first tuck point: [(Part, role, tuck_from)]; only the node named
    `outfit` when given (a shipped body holds a work suit and a space suit, which cross each other at rest)."""
    found = []
    for number, node in enumerate(document["nodes"]):
        if "mesh" not in node or node.get("name") == "far" or outfit not in (None, node.get("name")):
            continue
        for primitive in document["meshes"][node["mesh"]]["primitives"]:
            extras = document["materials"][primitive["material"]].get("extras", {})
            attributes = primitive["attributes"]
            points = joins.accessor(document, blob, attributes["POSITION"])
            part = joins.Part(document["materials"][primitive["material"]]["name"], points,
                              joins.accessor(document, blob, attributes["JOINTS_0"]),
                              joins.accessor(document, blob, attributes["WEIGHTS_0"]),
                              joins.accessor(document, blob, primitive["indices"]).astype(int).reshape(-1, 3),
                              joins.morph_targets(document, blob, primitive, len(points)), number)
            found.append((part, extras.get("role") or role_by_name(part.name), extras.get("tuck_from")))
    return found


def role_by_name(name):
    """A surface's role where its material names none (a body the shipped route built): a garment when joins.py takes
    it for a sleeve or a trouser leg."""
    return GARMENT if name in joins.SLEEVES + joins.TROUSERS else None


def garment_surface(posed, garments):
    """The garments' posed points, triangles (one numbering) and point normals."""
    points, faces, offset = [], [], 0
    for part in garments:
        points.append(posed[id(part)])
        faces.append(part.faces + offset)
        offset += len(part.points)
    points, faces = np.concatenate(points), np.concatenate(faces)
    normals = np.zeros_like(points)
    crossed = np.cross(points[faces[:, 1]] - points[faces[:, 0]], points[faces[:, 2]] - points[faces[:, 0]])
    for corner in range(3):
        np.add.at(normals, faces[:, corner], crossed)
    return points, faces, normals / np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-12)


def weld_map(points):
    """Each point's number among the points at distinct places (rounded to WELD_DIGITS): the parts' copies along
    their shared borders are one point, so a seam between two garment parts is not counted as cloth crossing cloth."""
    return np.unique(np.round(points, WELD_DIGITS), axis=0, return_inverse=True)[1].reshape(-1)


def crossings(points, faces, welded):
    """drape_measure.self_crossings on the garment welded by `welded` (weld_map of its rest points)."""
    count = int(welded.max()) + 1
    places = np.zeros((count, 3))
    places[welded] = points
    return drape_measure.self_crossings(places, welded[faces])


def outer_welding(found):
    """How the surfaces' points weld back into the person's one closed surface (their copies along shared borders
    are one point; every band left out): each surface's own points' numbers, and the closed surface's triangles."""
    places, faces, offset = [], [], 0
    for part, _, tuck_from in found:
        own = len(part.points) if tuck_from is None else tuck_from
        places.append(part.points[:own])
        faces.append(part.faces[(part.faces < own).all(1)] + offset)
        offset += own
    welded = weld_map(np.concatenate(places))
    return welded, welded[np.concatenate(faces)]


def outer_surface(posed, found, welding):
    """The person's closed surface in a pose (outer_welding's numbering): copies along a border pose alike, as they
    carry the same weights."""
    welded, faces = welding
    places = np.zeros((int(welded.max()) + 1, 3))
    places[welded] = np.concatenate([posed[id(part)][:len(part.points) if tuck_from is None else tuck_from]
                                     for part, _, tuck_from in found])
    return trimesh.Trimesh(places, faces, process=False)


def winding(points, mesh):
    """The generalized winding number of a closed surface at each point (the solid angle its triangles span over
    4 pi, Van Oosterom and Strackee's formula): 1 inside, 0 outside, 2 inside two overlapping parts of it."""
    found = np.zeros(len(points))
    for index, point in enumerate(points):
        corners = mesh.triangles - point
        lengths = np.linalg.norm(corners, axis=2)
        first, second, third = corners[:, 0], corners[:, 1], corners[:, 2]
        top = np.einsum("ij,ij->i", first, np.cross(second, third))
        bottom = (lengths[:, 0] * lengths[:, 1] * lengths[:, 2] + np.einsum("ij,ij->i", first, second) * lengths[:, 2]
                  + np.einsum("ij,ij->i", second, third) * lengths[:, 0]
                  + np.einsum("ij,ij->i", third, first) * lengths[:, 1])
        found[index] = 2 * np.arctan2(top, bottom).sum() / (4 * np.pi)
    return found


def tuck_out(tuck_points, outer):
    """Each tuck point's distance outside the person's closed surface, in metres (negative: inside it, by its
    distance from it). Inside is inside any part of the surface: where a posed sleeve passes into the torso the two
    overlap, and a ray's even crossings (trimesh's contains) read a band under both as outside; such points are
    asked again by the winding number, and one inside either part is hidden (2026-10-10)."""
    if not len(tuck_points):
        return np.zeros(0)
    _, distance, _ = trimesh.proximity.closest_point(outer, tuck_points)
    inside = outer.contains(tuck_points)
    doubted = np.flatnonzero(~inside & (distance > POKE_MM / 1000))
    if len(doubted):
        inside[doubted] = np.abs(winding(tuck_points[doubted], outer)) >= 0.5
    return np.where(inside, -distance, distance)


def hard_edges(found):
    """Each hard part's own edges (its tuck left out) and their lengths at the bind pose: [(part, edges, lengths)]."""
    edges = []
    for part, role, tuck_from in found:
        if role != HARD:
            continue
        own = len(part.points) if tuck_from is None else tuck_from
        faces = part.faces[(part.faces < own).all(1)]
        pairs = np.unique(np.sort(np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]]), 1), axis=0)
        lengths = np.linalg.norm(part.points[pairs[:, 0]] - part.points[pairs[:, 1]], axis=1)
        keep = lengths > 1e-6
        edges.append((part, pairs[keep], lengths[keep]))
    return edges


def stretch(posed, edges):
    """The largest ratio of a hard edge's posed length to its bind length in one frame (1.0 with no hard part)."""
    worst = 1.0
    for part, pairs, lengths in edges:
        places = posed[id(part)]
        worst = max(worst, float((np.linalg.norm(places[pairs[:, 0]] - places[pairs[:, 1]], axis=1) / lengths).max()))
    return worst


def posed_all(found, joint_worlds, inverse_bind, shapes=None, frame=0):
    """Every part posed in one frame, its morph targets (the settled garments) at the frame's keyed weights
    (`shapes`: each node's weights frame by frame, from keyed_shapes)."""
    posed = {}
    for part, _, _ in found:
        keyed = (shapes or {}).get(part.node)
        points = joins.morphed(part, None if keyed is None else keyed[min(frame, len(keyed) - 1)])
        posed[id(part)] = joins.skinned(points, part.joints, part.weights, joint_worlds, inverse_bind)
    return posed


def keyed_shapes(document, blob, animation, found):
    """Each part's node's morph target weights in the clip, frame by frame ({node: (frames, targets)})."""
    nodes = {part.node for part, _, _ in found if part.targets is not None}
    return {node: joins.morph_weights(document, blob, animation, node) for node in nodes}


def measure(path, every, outfit=None):
    """The body's poke record (one outfit's, when named)."""
    document, blob = joins.read_glb(path)
    skin = document["skins"][0]
    inverse_bind = joins.accessor(document, blob, skin["inverseBindMatrices"]).reshape(-1, 4, 4).transpose(0, 2, 1)
    parent = joins.parents_of(document)
    _, _, scales = joins.node_rest(document)
    found = surfaces(document, blob, outfit)
    garments = [part for part, role, _ in found if role == GARMENT]
    tucked = [(part, tuck_from) for part, _, tuck_from in found if tuck_from is not None]
    rest = {id(part): part.points for part, _, _ in found}
    rest_points, rest_faces, _ = garment_surface(rest, garments)
    welded = weld_map(rest_points)
    rest_crossings = crossings(rest_points, rest_faces, welded)
    welding = outer_welding(found) if tucked else None
    rigid = hard_edges(found)
    record = {"body": str(path), "rest_crossings": rest_crossings, "clips": {}}
    for animation in document.get("animations", []):
        rotations, translations = joins.clip_frames(document, blob, animation)
        shapes = keyed_shapes(document, blob, animation, found)
        worst, poking, counts, stretched = 0.0, 0, [], 1.0
        for frame in range(len(rotations)):
            world = joins.world_matrices(rotations[frame], translations[frame], scales, parent)
            posed = posed_all(found, world[skin["joints"]], inverse_bind, shapes, frame)
            cloth, faces, _ = garment_surface(posed, garments)
            outer = outer_surface(posed, found, welding) if tucked else None
            outside = np.concatenate([tuck_out(posed[id(part)][start:], outer) for part, start in tucked]) \
                if tucked else np.zeros(0)
            height = float(outside.max()) * 1000 if len(outside) else 0.0
            worst = max(worst, height)
            poking += height > POKE_MM
            stretched = max(stretched, stretch(posed, rigid))
            if frame % every == 0:
                counts.append(crossings(cloth, faces, welded))
        record["clips"][animation["name"]] = {
            "frames": len(rotations), "worst_tuck_out_mm": round(worst, 2), "frames_tuck_over": int(poking),
            "rigid_stretch": round(stretched, 3),
            "most_crossings": int(max(counts)), "frames_crossing_more_than_rest":
                int(sum(count > rest_crossings for count in counts)), "frames_crossings_read": len(counts)}
    clips = record["clips"].values()
    record["verdict"] = {"tucks": all(clip["frames_tuck_over"] == 0 for clip in clips),
                         "rigid": all(clip["rigid_stretch"] <= RIGID_MOST for clip in clips),
                         "cloth_through_cloth": all(clip["frames_crossing_more_than_rest"] == 0 for clip in clips)}
    return record


def against(record, shipped):
    """The cloth verdict set against the shipped body's record: no clip crosses more than the shipped body's same
    clip (a clip the shipped body has not is held to the rest)."""
    worse = [name for name, clip in record["clips"].items()
             if clip["most_crossings"] > shipped["clips"].get(name, {}).get("most_crossings", record["rest_crossings"])]
    record["verdict"]["cloth_through_cloth"] = not worse
    record["cloth_worse_than_shipped"] = worse
    record["shipped"] = shipped["body"]
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("body", type=pathlib.Path)
    parser.add_argument("--out", required=True, type=pathlib.Path)
    parser.add_argument("--every", type=int, default=CROSSING_EVERY)
    parser.add_argument("--against", type=pathlib.Path, help="the shipped body's pokes record")
    parser.add_argument("--outfit", help="measure only this outfit's node")
    options = parser.parse_args()
    record = measure(options.body, options.every, options.outfit)
    if options.against:
        against(record, json.loads(options.against.read_text()))
    record["pass"] = all(record["verdict"].values())
    options.out.write_text(json.dumps(record, indent=1))
    print(f"pokes: {'pass' if record['pass'] else 'FAIL'} {record['verdict']}; {options.out}")


if __name__ == "__main__":
    main()
