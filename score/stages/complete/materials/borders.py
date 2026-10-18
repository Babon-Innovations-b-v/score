"""Finish-border raggedness per part: where two finishes of one model meet across a smooth surface, the border should
run as a clean line; a model whose parts were split on a voxel remesh (tools/props/library/inside/make_chunky.py)
has borders that step along the voxel faces (the audit of 2026-10-18: 10 cm steps on the ship's hull).

Measured, for each finish (a GeomSubset per library surface) of each model: its border with every other finish, the
part of it that crosses a smooth surface (the faces either side within SHARP degrees; a border on a sharp edge
follows the shape and is left out), and that part's raggedness: its length over the length of the same border
smoothed over WINDOW points either side. A straight or gently curving border is 1.0; a staircase at 45 degrees is
about 1.4. RAGGED was set by eye on the 28 places' models (2026-10-18): the garage's wheel stand (1.02) and the lab's
instrument unit (1.05) read clean, the garage's workbench (1.07) and the cockpit's pilot seat (1.09) visibly step,
the hangar's ship 1.24 to 1.43. Judged: a finish whose smooth border is at least MIN_BORDER metres long and RAGGED
or more is a finding, one finding a model naming its ragged finishes.
"""
import collections

import numpy as np

RULE = "ragged finish border"
SHARP = 30.0
WINDOW = 3
RAGGED = 1.07
MIN_BORDER = 0.5
# Points closer than this (metres) are one point: a mesh split along its texture seams has each seam's points twice.
WELD = 1e-5


def welded(points, triangles):
    """The points with duplicates merged, and the triangles over them."""
    keys = np.round(points / WELD).astype(np.int64)
    _, first, inverse = np.unique(keys, axis=0, return_index=True, return_inverse=True)
    return points[first], inverse.reshape(-1)[triangles]


def face_labels(count, finishes):
    """Each triangle's finish number (-1 for none) and the finish names in that order."""
    names = sorted(finishes)
    labels = np.full(count, -1)
    for number, name in enumerate(names):
        labels[finishes[name]] = number
    return labels, names


def edge_faces(triangles):
    """{(low point, high point): [triangle numbers]} of every edge."""
    found = collections.defaultdict(list)
    for face, (first, second, third) in enumerate(triangles.tolist()):
        for start, end in ((first, second), (second, third), (third, first)):
            found[(min(start, end), max(start, end))].append(face)
    return found


def face_normals(points, triangles):
    """Each triangle's unit normal."""
    normals = np.cross(points[triangles[:, 1]] - points[triangles[:, 0]],
                       points[triangles[:, 2]] - points[triangles[:, 0]])
    return normals / (np.linalg.norm(normals, axis=1, keepdims=True) + 1e-12)


def border_edges(points, triangles, labels):
    """{finish number: [(edge, smooth)]} of every edge between two finishes, smooth when the faces either side lie
    within SHARP degrees of each other."""
    normals = face_normals(points, triangles)
    found = collections.defaultdict(list)
    for edge, faces in edge_faces(triangles).items():
        if len(faces) != 2 or labels[faces[0]] == labels[faces[1]]:
            continue
        cosine = float(np.clip(np.dot(normals[faces[0]], normals[faces[1]]), -1.0, 1.0))
        smooth = np.degrees(np.arccos(cosine)) < SHARP
        for label in (labels[faces[0]], labels[faces[1]]):
            if label >= 0:
                found[label].append((edge, smooth))
    return found


def chains(edges):
    """The edges joined into runs of points, each run ending where three or more edges meet or the border ends."""
    links = collections.defaultdict(list)
    for start, end in edges:
        links[start].append(end)
        links[end].append(start)
    used, found = set(), []
    starts = [point for point in links if len(links[point]) != 2] + list(links)
    for start in starts:
        for following in links[start]:
            if (min(start, following), max(start, following)) in used:
                continue
            run = [start, following]
            used.add((min(start, following), max(start, following)))
            while len(links[run[-1]]) == 2:
                ahead = [point for point in links[run[-1]] if (min(run[-1], point), max(run[-1], point)) not in used]
                if not ahead:
                    break
                used.add((min(run[-1], ahead[0]), max(run[-1], ahead[0])))
                run.append(ahead[0])
            found.append(run)
    return found


def lengths(line):
    """(length, smoothed length) of a run of points; a run too short to smooth is its own smoothed length."""
    length = float(np.linalg.norm(np.diff(line, axis=0), axis=1).sum())
    if len(line) < 2 * WINDOW + 2:
        return length, length
    kernel = np.ones(2 * WINDOW + 1) / (2 * WINDOW + 1)
    middle = np.stack([np.convolve(line[:, axis], kernel, mode="valid") for axis in range(3)], axis=1)
    smoothed = np.vstack([line[:1], middle, line[-1:]])
    return length, float(np.linalg.norm(np.diff(smoothed, axis=0), axis=1).sum())


def part_runs(mesh):
    """{finish name: [runs of points along its smooth border]} of one drawn mesh, with every finish's whole border
    length: ({name: runs}, {name: metres})."""
    if len(mesh.finishes) < 2:
        return {}, {}
    points, triangles = welded(mesh.points, mesh.triangles)
    labels, names = face_labels(len(triangles), mesh.finishes)
    runs, whole = {}, {}
    for label, edges in border_edges(points, triangles, labels).items():
        whole[names[label]] = float(sum(np.linalg.norm(points[start] - points[end]) for (start, end), _ in edges))
        runs[names[label]] = [points[run] for run in chains([edge for edge, smooth in edges if smooth])]
    return runs, whole


def measured_parts(drawn, scale=1.0):
    """[{part, border_m, smooth_m, ragged}] of a model's finishes, lengths at its laid scale."""
    found = []
    for mesh in drawn:
        runs, whole = part_runs(mesh)
        for name, lines in runs.items():
            totals = np.array([lengths(line) for line in lines] or [(0.0, 0.0)]).sum(axis=0)
            found.append({"part": name, "border_m": round(whole[name] * scale, 3),
                          "smooth_m": round(float(totals[0]) * scale, 3),
                          "ragged": round(float(totals[0] / totals[1]), 3) if totals[1] > 0 else 1.0})
    return found


def ragged_parts(model):
    """The parts of a measured model that are findings."""
    return [part for part in model["parts"] if part["smooth_m"] >= MIN_BORDER and part["ragged"] >= RAGGED]


def sentence(model, parts):
    """A finding in words."""
    worst = max(parts, key=lambda part: part["ragged"])
    named = ", ".join(f"{part['part']} {part['ragged']:.2f}" for part in parts[:4])
    more = f" and {len(parts) - 4} more" if len(parts) > 4 else ""
    return (f"{model['model']}'s finish borders step instead of running clean ({named}{more}; a clean border is 1.00, "
            f"worst {worst['ragged']:.2f} over {worst['smooth_m']:.1f} m)")


def findings(evidence):
    """One finding a model with a ragged finish border, the most seen (nearest a camera) first."""
    found = []
    for model in evidence["models"]:
        parts = sorted(ragged_parts(model), key=lambda part: -part["ragged"])
        if parts:
            found.append({"rule": RULE, "prim": model["prim"], "model": model["model"], "near": model.get("near"),
                          "parts": [part["part"] for part in parts], "worst": parts[0]["ragged"],
                          "sentence": sentence(model, parts)})
    unseen = float("inf")
    return sorted(found, key=lambda item: (item["near"] if item["near"] is not None else unseen, -item["worst"]))
