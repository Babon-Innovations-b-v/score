"""The finish against NVIDIA's: the made model's parts held to the truth's material faces (each made face takes the
material of the nearest truth surface point, the made model set on the truth), by split_compare's ownership rule;
and each matched part's surface held to the truth's by the look-alike check's bounds."""
import numpy as np
from scipy.spatial import cKDTree

import score.stages.props.prop_data as prop_data

from . import _mesh

CARRY_POINTS = 200000  # truth surface points a made face's material is read from
CANDIDATES = 8  # truth triangles measured exactly per made face (those of its nearest truth points)
CARRY_CHUNK = 100000  # made faces carried at a time


def split_rule():
    """tools/props/library/split_compare.py: finishes_owned, OWN_PURITY, FINISH_LEAST."""
    with prop_data.tools("props/library", "props"):
        import split_compare
    return split_compare


def look_bounds():
    """tools/props/library/likeness/measure.py: passes (one view's measures within every bound)."""
    with prop_data.tools("props/library/likeness", "props/library", "props"):
        import measure
    return measure


def carried(truth, placed, made_faces):
    """Each made face's truth material: the material of the truth triangle nearest its middle, found exactly among
    the triangles of the CANDIDATES truth points (drawn by area, and every triangle's middle) nearest it. NVIDIA lays
    tape, decals and labels as a thin layer just over a box's own surface (box_flat_a10's tape 0.4 mm over its card);
    the nearest drawn point read either layer and blurred a strip's edges by the points' spacing (5 mm there), so an
    exact copy of box_flat_a10 held none of its tape (#163 calibration). A point nudged out along the normal read
    the tape's hidden underside as card, so none is."""
    import trimesh
    points, picked = _mesh.sampled(truth["vertices"], truth["faces"], CARRY_POINTS, seed=6)
    triangles = truth["vertices"][truth["faces"]]
    points = np.concatenate([points, triangles.mean(1)])
    picked = np.concatenate([picked, np.arange(len(triangles))])
    tree, material = cKDTree(points), np.asarray(truth["face_material"])
    asked = placed[made_faces].mean(1)
    found = np.empty(len(made_faces), dtype=material.dtype)
    for start in range(0, len(asked), CARRY_CHUNK):
        point = asked[start:start + CARRY_CHUNK]
        _, index = tree.query(point, k=CANDIDATES)
        candidate = picked[index]
        nearest = trimesh.triangles.closest_point(triangles[candidate].reshape(-1, 3, 3),
                                                  np.repeat(point, CANDIDATES, axis=0))
        distance = np.linalg.norm(nearest - np.repeat(point, CANDIDATES, axis=0), axis=1).reshape(-1, CANDIDATES)
        found[start:start + CARRY_CHUNK] = material[candidate[np.arange(len(point)), distance.argmin(1)]]
    return found


def finish_split(truth, placed, made_faces, made_parts):
    """{"owned": finishes owned of those counted, "held_mean", "held_least": each counted finish's share held in
    parts pure in it, "purity": area-weighted share of each made part in its main finish, "parts", "materials",
    "pairs": [{"part", "material", "area"}] each made part with its main truth material and its area share}."""
    rule = split_rule()
    area = _mesh.areas(placed, made_faces)
    finish = carried(truth, placed, made_faces)
    part_of = np.asarray(made_parts)
    table = np.zeros((int(part_of.max()) + 1, int(finish.max()) + 1))
    np.add.at(table, (part_of, finish), area)
    pure = table / np.maximum(table.sum(1, keepdims=True), 1e-12)
    counted = np.nonzero(table.sum(0) >= rule.FINISH_LEAST * area.sum())[0]
    held = [table[pure[:, number] >= rule.OWN_PURITY, number].sum() / table[:, number].sum() for number in counted]
    owned, _ = rule.finishes_owned(area, finish, part_of)
    truth_area = _mesh.areas(truth["vertices"], truth["faces"])
    materials = np.bincount(np.asarray(truth["face_material"]), weights=truth_area)
    parts = np.nonzero(table.sum(1) >= rule.FINISH_LEAST * area.sum())[0]  # a part as a finish is counted: 1% up
    counted_materials = int((materials >= rule.FINISH_LEAST * materials.sum()).sum())
    return {"owned": round(len(owned) / max(len(counted), 1), 4),
            "held_mean": round(float(np.mean(held)), 4), "held_least": round(float(np.min(held)), 4),
            "purity": round(float((table.max(1)).sum() / table.sum()), 4),
            "parts": int(len(parts)), "materials": counted_materials,
            "parts_per_material": round(len(parts) / max(counted_materials, 1), 3),
            "pairs": [{"part": int(part), "material": int(table[part].argmax()),
                       "area": round(float(table[part].sum() / table.sum()), 5)} for part in parts]}


def finish_likeness(looks):
    """{"alike": the area share whose surface holds every bound in every view and is of the truth's family,
    "within_bounds", "same_family"}; `looks` is [{"area", "views": {view: look-alike measures}, "family",
    "true_family"}], one a matched part (finish_split's pairs, drawn by tools/props/library/likeness)."""
    bounds = look_bounds()
    total = sum(look["area"] for look in looks)
    within = [all(bounds.passes(measured) for measured in look["views"].values()) for look in looks]
    family = [look["family"] == look["true_family"] for look in looks]
    def share(kept):
        return round(sum(look["area"] for look, keep in zip(looks, kept) if keep) / total, 4)
    return {"alike": share([one and other for one, other in zip(within, family)]),
            "within_bounds": share(within), "same_family": share(family)}
