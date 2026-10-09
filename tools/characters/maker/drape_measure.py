"""How well a drape hangs, in numbers that can be set beside another simulator's drape of the same pattern on the same
body: the trouser hem's height, how crumpled the cloth is, how far the legs balloon off the body, how the space suit
sits at the waist and how much cloth the people tools' belt finds.

    ~/.farm-factory-props/env/bin/python tools/characters/maker/drape_measure.py <drape folder> <body obj, cm> \
        <look folder> [--json out.json]

The drape folder holds <kind>_<n>_sim.obj (centimetres) and its _sim_segmentation.txt, as GarmentCode's and the
maker's drapes both do; the look folder is the person's (its joints.json places the belt band through
tools/characters/people/fit.py, as space_suit.py places it). Numpy and scipy only, seconds on any machine.

- hem_cm: the lowest trouser point of each leg above the floor (the body's lowest point), the mean of the two legs.
- crumple_deg: the mean bend between neighbouring cloth triangles, in degrees, over the whole garment (the same
  pattern at the same spacing bends the same where it hangs smoothly; crumples raise it).
- balloon_cm: the mean distance from the trouser cloth to the body between the ankle and the knee.
- waist_crumple_deg: crumple_deg in the band from the hips to the lowest ribs (where a gathered waist shows).
- torso_low_m, belt_band_m, belt_cloth_cm: the torso panels' lowest point, the belt band space_suit.py cuts
  (fit.y(1.005) to fit.y(1.062)) and how much of that band's height the torso cloth covers.
"""
import argparse
import importlib
import json
import os
import pathlib
import sys

import numpy as np
from scipy.spatial import cKDTree

PEOPLE = pathlib.Path(__file__).resolve().parents[1] / "people"
# The belt band space_suit.py cuts from the torso, in take C's heights (moved onto the person by fit.y).
BELT_BAND = (1.005, 1.062)
# The waist band where gathers are counted, in take C's heights: from the hips to the lowest ribs.
WAIST_BAND = (0.95, 1.12)


def read_obj(path):
    """Points (metres) and triangles of an obj written in centimetres."""
    points, faces = [], []
    for line in pathlib.Path(path).read_text().splitlines():
        if line.startswith("v "):
            points.append([float(value) for value in line.split()[1:4]])
        elif line.startswith("f "):
            corners = [int(token.split("/")[0]) - 1 for token in line.split()[1:]]
            faces.extend([corners[0], corners[index], corners[index + 1]] for index in range(1, len(corners) - 1))
    return np.array(points) / 100.0, np.array(faces, dtype=np.int64)


def drape_files(folder):
    """The cloth obj and its segmentation in a drape folder."""
    folder = pathlib.Path(folder)
    cloth = next(folder.glob("*_sim.obj"))
    return cloth, cloth.with_name(cloth.name.replace("_sim.obj", "_sim_segmentation.txt"))


def panel_labels(segmentation):
    """Each point's panel name; a point on a seam keeps the first stitch it names."""
    return np.array([line.split(",")[0] for line in pathlib.Path(segmentation).read_text().split("\n") if line.strip()])


def face_normals(points, faces):
    """Each triangle's unit normal."""
    normals = np.cross(points[faces[:, 1]] - points[faces[:, 0]], points[faces[:, 2]] - points[faces[:, 0]])
    return normals / np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-12)


def edge_bends(points, faces):
    """For every edge two triangles share: the bend between them in degrees, and the edge's middle height."""
    edges = np.sort(faces[:, [[0, 1], [1, 2], [2, 0]]].reshape(-1, 2), axis=1)
    owner = np.repeat(np.arange(len(faces)), 3)
    order = np.lexsort((edges[:, 1], edges[:, 0]))
    edges, owner = edges[order], owner[order]
    shared = np.all(edges[1:] == edges[:-1], axis=1)
    first, second = owner[:-1][shared], owner[1:][shared]
    normals = face_normals(points, faces)
    cosine = np.clip(np.sum(normals[first] * normals[second], axis=1), -1.0, 1.0)
    middle = points[edges[:-1][shared]].mean(axis=1)
    return np.degrees(np.arccos(cosine)), middle[:, 1]


def leg_mask(labels):
    """The trouser points (legs and cuffs)."""
    return np.char.startswith(labels, "pant")


def hem_height(points, labels, floor):
    """The mean over both legs of each leg's lowest trouser point above the floor, in metres."""
    lows = []
    for side in ("l", "r"):
        leg = np.array([label.startswith("pant") and (label.endswith(f"_{side}") or f"_{side}_" in label)
                        for label in labels])
        if leg.any():
            lows.append(points[leg, 1].min() - floor)
    return float(np.mean(lows)) if lows else None


def balloon(points, labels, body_tree, low, high):
    """The mean distance from the trouser points between two heights to the nearest body point, in metres."""
    keep = leg_mask(labels) & (points[:, 1] > low) & (points[:, 1] < high)
    if not keep.any():
        return None
    return float(body_tree.query(points[keep])[0].mean())


def fit_module(look):
    """tools/characters/people/fit.py reading this look's joints."""
    os.environ["MOTION_LOOK"] = str(pathlib.Path(look).resolve())
    sys.path.insert(0, str(PEOPLE))
    for name in ("paths", "fit"):
        sys.modules.pop(name, None)
    return importlib.import_module("fit")


def belt_numbers(points, labels, fit):
    """The torso's lowest point, the belt band and the band height the torso cloth covers, in metres."""
    torso = np.char.find(labels, "torso") >= 0
    if not torso.any():
        return {}
    low = float(points[torso, 1].min())
    bottom, top = float(fit.y(BELT_BAND[0])), float(fit.y(BELT_BAND[1]))
    return {"torso_low_m": round(low, 4), "belt_band_m": [round(bottom, 4), round(top, 4)],
            "belt_cloth_cm": round(100.0 * max(0.0, top - max(bottom, low)), 2)}


def measure(folder, body_obj, look):
    """Every number of the module's header for one drape."""
    cloth, segmentation = drape_files(folder)
    points, faces = read_obj(cloth)
    labels = panel_labels(segmentation)
    body_points, _ = read_obj(body_obj)
    floor = float(body_points[:, 1].min())
    fit = fit_module(look)
    joints = json.loads((pathlib.Path(look) / "joints.json").read_text())
    knee = np.mean([joints["LeftShin"][1], joints["RightShin"][1]])
    ankle = np.mean([joints["LeftFoot"][1], joints["RightFoot"][1]])
    bends, heights = edge_bends(points, faces)
    waist = (heights > fit.y(WAIST_BAND[0])) & (heights < fit.y(WAIST_BAND[1]))
    result = {"drape": str(cloth), "points": int(len(points)),
              "crumple_deg": round(float(bends.mean()), 3),
              "waist_crumple_deg": round(float(bends[waist].mean()), 3) if waist.any() else None}
    hem = hem_height(points, labels, floor)
    if hem is not None:
        result["hem_cm"] = round(100.0 * hem, 2)
        leg_balloon = balloon(points, labels, cKDTree(body_points), ankle + 0.05, knee)
        result["balloon_cm"] = round(100.0 * leg_balloon, 2) if leg_balloon is not None else None
    result.update(belt_numbers(points, labels, fit))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("drape", type=pathlib.Path)
    parser.add_argument("body", type=pathlib.Path)
    parser.add_argument("look", type=pathlib.Path)
    parser.add_argument("--json", type=pathlib.Path)
    options = parser.parse_args()
    result = measure(options.drape, options.body, options.look)
    text = json.dumps(result, indent=1)
    if options.json:
        options.json.write_text(text)
    print(text)


if __name__ == "__main__":
    main()
