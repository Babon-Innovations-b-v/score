"""The prop route's per-frame poke check of a built person: what shows through what, in every frame of every clip,
read from the built glTF as the engine skins it (people/joins.py's reader). Measures; it does not judge by eye.

    ~/.farm-factory-props/env/bin/python tools/characters/maker/pokes.py <body.glb> --out <pokes.json> [--every 1]

- tuck_out_mm: each tuck (a skin or hard part's band run on under a garment, tucks.py; its points from the material's
  `tuck_from`) point's height outside the nearest garment surface, along that surface's normal: a tuck showing
  through its sleeve, collar or trouser leg. Per clip the worst frame and how many frames have a point over POKE_MM.
- cloth_crossings: how many garment edges pass through a garment triangle they share no corner with
  (drape_measure.self_crossings, the garment parts welded where their borders meet), in the bind pose and in every `--every`-th frame (every CROSSING_EVERY-th by
  default): cloth gone through cloth. A Pixal3D surface may cross itself at rest; a frame is counted as poking where
  it crosses more than the rest does.
- A body built by the shipped route (no roles in its materials) is read the same way, its garments by joins.py's names
  and no tucks, so a candidate's crossings can be set beside the shipped body's.
- verdict: pass when no frame has a tuck point over POKE_MM outside and no frame crosses more than the rest.
"""
import argparse
import json
import pathlib
import sys

import numpy as np
from scipy.spatial import cKDTree

MAKER = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(MAKER))
sys.path.insert(0, str(MAKER.parent / "people"))

import drape_measure  # noqa: E402
import joins  # noqa: E402

POKE_MM = 5.0
WELD_DIGITS = 6
CROSSING_EVERY = 5
GARMENT = "garment"


def surfaces(document, blob):
    """The outfit's surfaces with their role and first tuck point: [(Part, role, tuck_from)]."""
    found = []
    for node in document["nodes"]:
        if "mesh" not in node or node.get("name") == "far":
            continue
        for primitive in document["meshes"][node["mesh"]]["primitives"]:
            extras = document["materials"][primitive["material"]].get("extras", {})
            attributes = primitive["attributes"]
            part = joins.Part(document["materials"][primitive["material"]]["name"],
                              joins.accessor(document, blob, attributes["POSITION"]),
                              joins.accessor(document, blob, attributes["JOINTS_0"]),
                              joins.accessor(document, blob, attributes["WEIGHTS_0"]),
                              joins.accessor(document, blob, primitive["indices"]).astype(int).reshape(-1, 3))
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


def tuck_out(tuck_points, cloth_points, cloth_normals):
    """Each tuck point's height outside the nearest cloth point along its normal, in metres (negative: under it)."""
    if not len(tuck_points):
        return np.zeros(0)
    _, nearest = cKDTree(cloth_points).query(tuck_points)
    return ((tuck_points - cloth_points[nearest]) * cloth_normals[nearest]).sum(1)


def posed_all(found, joint_worlds, inverse_bind):
    return {id(part): joins.skinned(part.points, part.joints, part.weights, joint_worlds, inverse_bind)
            for part, _, _ in found}


def measure(path, every):
    """The body's poke record."""
    document, blob = joins.read_glb(path)
    skin = document["skins"][0]
    inverse_bind = joins.accessor(document, blob, skin["inverseBindMatrices"]).reshape(-1, 4, 4).transpose(0, 2, 1)
    parent = joins.parents_of(document)
    _, _, scales = joins.node_rest(document)
    found = surfaces(document, blob)
    garments = [part for part, role, _ in found if role == GARMENT]
    tucked = [(part, tuck_from) for part, _, tuck_from in found if tuck_from is not None]
    rest = {id(part): part.points for part, _, _ in found}
    rest_points, rest_faces, _ = garment_surface(rest, garments)
    welded = weld_map(rest_points)
    rest_crossings = crossings(rest_points, rest_faces, welded)
    record = {"body": str(path), "rest_crossings": rest_crossings, "clips": {}}
    for animation in document.get("animations", []):
        rotations, translations = joins.clip_frames(document, blob, animation)
        worst, poking, counts = 0.0, 0, []
        for frame in range(len(rotations)):
            world = joins.world_matrices(rotations[frame], translations[frame], scales, parent)
            posed = posed_all(found, world[skin["joints"]], inverse_bind)
            cloth, faces, normals = garment_surface(posed, garments)
            outside = np.concatenate([tuck_out(posed[id(part)][start:], cloth, normals) for part, start in tucked]) \
                if tucked else np.zeros(0)
            height = float(outside.max()) * 1000 if len(outside) else 0.0
            worst = max(worst, height)
            poking += height > POKE_MM
            if frame % every == 0:
                counts.append(crossings(cloth, faces, welded))
        record["clips"][animation["name"]] = {
            "frames": len(rotations), "worst_tuck_out_mm": round(worst, 2), "frames_tuck_over": int(poking),
            "most_crossings": int(max(counts)), "frames_crossing_more_than_rest":
                int(sum(count > rest_crossings for count in counts)), "frames_crossings_read": len(counts)}
    clips = record["clips"].values()
    record["verdict"] = {"tucks": all(clip["frames_tuck_over"] == 0 for clip in clips),
                         "cloth_through_cloth": all(clip["frames_crossing_more_than_rest"] == 0 for clip in clips)}
    record["pass"] = all(record["verdict"].values())
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("body", type=pathlib.Path)
    parser.add_argument("--out", required=True, type=pathlib.Path)
    parser.add_argument("--every", type=int, default=CROSSING_EVERY)
    options = parser.parse_args()
    record = measure(options.body, options.every)
    options.out.write_text(json.dumps(record, indent=1))
    print(f"pokes: {'pass' if record['pass'] else 'FAIL'} {record['verdict']}; {options.out}")


if __name__ == "__main__":
    main()
