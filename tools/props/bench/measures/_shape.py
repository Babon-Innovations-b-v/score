"""Shape against the truth, the made model already set on it: silhouettes from the likeness ring and from the input's
own view, both drawn by one camera framed on the truth (so size and place count, unlike compare.outline's boxed
masks), Chamfer and F-score on surface points, and the rank of the truth among the kind's other assets."""
import math

import numpy as np
from scipy.spatial import cKDTree

import score.stages.props.likeness as likeness

from . import _align, _mesh

SIDE = likeness.SIDE  # pixels across a silhouette
POINTS = 20000  # surface points each side for Chamfer and the F-score
REACH = 0.02  # the F-score's distance, a share of the truth's diagonal
CHUNK = 2_000_000  # pixel centres tested at a time when a mesh is drawn


def ring():
    """tools/usd/compare.py: its YAWS ways round at ELEVATION degrees, FOV degrees across."""
    return likeness.candidate()


def camera(low, high, yaw, pitch):
    """(eye, right, up, back, focal) of a camera `yaw` degrees round Z and `pitch` above level, fitted on the box."""
    middle = (low + high) / 2
    radius = max(0.05, float(np.linalg.norm(high - low)) / 2)
    view = math.radians(ring().FOV)
    distance = radius / math.sin(view / 2) * 1.05
    turn, down = math.radians(yaw), math.radians(pitch)
    back = np.array([math.sin(turn) * math.cos(down), math.cos(turn) * math.cos(down), math.sin(down)])
    right = np.array([math.cos(turn), -math.sin(turn), 0.0])
    up = np.cross(right, back)
    return middle + back * distance, right, up, back, SIDE / 2 / math.tan(view / 2)


def covered(corners, mask):
    """Mark on `mask` every pixel whose centre lies inside or on a triangle (corners (T, 3, 2) in pixels): one rule for
    a triangle of any size, so a mesh cut finer draws the same outline (the calibration's exact copies: drawing a
    sub-pixel triangle as dots at its corners left holes, a crate's copy at 0.89 from its input view)."""
    low = np.clip(np.ceil(corners.min(1) - 0.5), 0, SIDE).astype(int)
    high = np.clip(np.floor(corners.max(1) - 0.5), -1, SIDE - 1).astype(int)
    span = (high - low + 1).max(1)
    first, second, third = corners[:, 0], corners[:, 1], corners[:, 2]
    signed = (second - first)[:, 0] * (third - first)[:, 1] - (second - first)[:, 1] * (third - first)[:, 0]
    for reach in np.unique(span[span > 0]):
        picked = np.flatnonzero(span == reach)
        for start in range(0, len(picked), max(1, CHUNK // int(reach) ** 2)):
            chosen = picked[start:start + max(1, CHUNK // int(reach) ** 2)]
            steps = np.arange(int(reach))
            columns = low[chosen, 0][:, None, None] + steps[None, None, :]
            rows = low[chosen, 1][:, None, None] + steps[None, :, None]
            point = np.stack(np.broadcast_arrays(columns + 0.5, rows + 0.5), -1)
            way = np.sign(signed[chosen])[:, None, None]
            inside = np.ones(point.shape[:3], dtype=bool)
            for start_corner, end_corner in ((first, second), (second, third), (third, first)):
                edge = (end_corner[chosen] - start_corner[chosen])[:, None, None]
                towards = point - start_corner[chosen][:, None, None]
                inside &= way * (edge[..., 0] * towards[..., 1] - edge[..., 1] * towards[..., 0]) >= 0
            inside &= (way != 0) & (columns <= high[chosen, 0][:, None, None]) & (rows <= high[chosen, 1][:, None, None])
            mask[np.broadcast_to(rows, inside.shape)[inside], np.broadcast_to(columns, inside.shape)[inside]] = True
    return mask


def silhouette(vertices, faces, frame, yaw, pitch):
    """The mesh's mask from the camera fitted on `frame` (low, high): a pixel is the mesh's when its centre falls in
    one of its triangles."""
    eye, right, up, back, focal = camera(frame[0], frame[1], yaw, pitch)
    seen = vertices - eye
    depth = np.maximum(-seen @ back, 1e-6)
    pixels = np.stack([SIDE / 2 + focal * (seen @ right) / depth, SIDE / 2 - focal * (seen @ up) / depth], axis=1)
    return covered(pixels[faces], np.zeros((SIDE, SIDE), dtype=bool))


def iou(first, second):
    """Intersection over union of two masks."""
    union = np.logical_or(first, second).sum()
    return float(np.logical_and(first, second).sum() / union) if union else 0.0


def silhouettes(truth, placed, made_faces, input_view):
    """{"ring": mean IoU over the ring's ways, "ways": each, "input": the IoU from the input's (yaw, pitch)}."""
    frame = (truth["vertices"].min(0), truth["vertices"].max(0))
    views = ring()
    ways = [iou(silhouette(truth["vertices"], truth["faces"], frame, 360.0 * step / views.YAWS, views.ELEVATION),
                silhouette(placed, made_faces, frame, 360.0 * step / views.YAWS, views.ELEVATION))
            for step in range(views.YAWS)]
    seen = iou(silhouette(truth["vertices"], truth["faces"], frame, *input_view),
               silhouette(placed, made_faces, frame, *input_view))
    return {"ring": round(float(np.mean(ways)), 4), "ways": [round(way, 4) for way in ways], "input": round(seen, 4)}


def distances(truth_vertices, truth_faces, placed, made_faces):
    """{"chamfer": the two-way mean nearest distance over the truth's diagonal, "f_score": at REACH of it,
    "precision", "recall"}."""
    reach = _mesh.diagonal(truth_vertices)
    truth_points, _ = _mesh.sampled(truth_vertices, truth_faces, POINTS, seed=3)
    made_points, _ = _mesh.sampled(placed, made_faces, POINTS, seed=4)
    to_truth = cKDTree(truth_points).query(made_points)[0]
    to_made = cKDTree(made_points).query(truth_points)[0]
    precision = float((to_truth <= REACH * reach).mean())
    recall = float((to_made <= REACH * reach).mean())
    f_score = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"chamfer": round(float((to_truth.mean() + to_made.mean()) / 2 / reach), 5), "f_score": round(f_score, 4),
            "precision": round(precision, 4), "recall": round(recall, 4)}


def rank(made, f_score, others):
    """The truth's place among the kind's assets by the made model's F-score against each (1: none of the others
    is as near), with each other asset's F-score."""
    theirs = {}
    for other in others:
        matrix, _ = _align.aligned(other, made)
        theirs[other.get("id", str(len(theirs)))] = distances(other["vertices"], other["faces"],
                                                              _mesh.moved(made["vertices"], matrix),
                                                              made["faces"])["f_score"]
    return 1 + sum(1 for value in theirs.values() if value >= f_score), theirs
