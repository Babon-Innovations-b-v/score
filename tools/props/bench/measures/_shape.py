"""Shape against the truth, the made model already set on it: silhouettes from the likeness ring and from the input's
own view, both drawn by one camera framed on the truth (so size and place count, unlike compare.outline's boxed
masks), Chamfer and F-score on surface points, the rank of the truth among the kind's other assets, and the thin and
small parts drawn at DETAIL_SIDE: a part NVIDIA's model shows that the made one leaves out (`missing_part`) and the
outline's fine edge, its teeth, ribs and holes, kept (`outline_detail`)."""
import functools
import hashlib
import math

import numpy as np
from scipy import ndimage
from scipy.spatial import cKDTree

import score.stages.props.likeness as likeness

from . import _align, _mesh

SIDE = likeness.SIDE  # pixels across a silhouette
POINTS = 20000  # surface points each side for Chamfer and the F-score
REACH = 0.02  # the F-score's distance, a share of the truth's diagonal
CHUNK = 2_000_000  # pixel centres tested at a time when a mesh is drawn
# The thin and small parts (#159 r15: hand drill b01's crank arm and handle gone from its look, its gear's teeth, the
# tool cart's pegboard holes and the locker's vents melted): drawn at DETAIL_SIDE, where a 3 mm crank arm on the
# 0.29 m drill is about ten pixels wide and the cart's 6 mm pegboard holes about five across.
DETAIL_SIDE = 1024
# A pixel of NVIDIA's silhouette further than MISSING_REACH of the frame from the made one's is a part left out, so a
# made model a few per cent off in size or place (the size bar's 5%) leaves no sliver along its whole edge.
MISSING_REACH = 0.02


def ring():
    """tools/usd/compare.py: its YAWS ways round at ELEVATION degrees, FOV degrees across."""
    return likeness.candidate()


def camera(low, high, yaw, pitch, side=SIDE):
    """(eye, right, up, back, focal) of a camera `yaw` degrees round Z and `pitch` above level, fitted on the box, its
    picture `side` pixels across."""
    middle = (low + high) / 2
    radius = max(0.05, float(np.linalg.norm(high - low)) / 2)
    view = math.radians(ring().FOV)
    distance = radius / math.sin(view / 2) * 1.05
    turn, down = math.radians(yaw), math.radians(pitch)
    back = np.array([math.sin(turn) * math.cos(down), math.cos(turn) * math.cos(down), math.sin(down)])
    right = np.array([math.cos(turn), -math.sin(turn), 0.0])
    up = np.cross(right, back)
    return middle + back * distance, right, up, back, side / 2 / math.tan(view / 2)


def covered(corners, mask):
    """Mark on `mask` every pixel whose centre lies inside or on a triangle (corners (T, 3, 2) in pixels): one rule for
    a triangle of any size, so a mesh cut finer draws the same outline (the calibration's exact copies: drawing a
    sub-pixel triangle as dots at its corners left holes, a crate's copy at 0.89 from its input view)."""
    side = mask.shape[0]
    low = np.clip(np.ceil(corners.min(1) - 0.5), 0, side).astype(int)
    high = np.clip(np.floor(corners.max(1) - 0.5), -1, side - 1).astype(int)
    span = high - low + 1  # each triangle's box in pixels, across and down: a long thin one is tested in its box alone
    first, second, third = corners[:, 0], corners[:, 1], corners[:, 2]
    signed = (second - first)[:, 0] * (third - first)[:, 1] - (second - first)[:, 1] * (third - first)[:, 0]
    drawn = np.flatnonzero((span > 0).all(1))
    shapes, which = np.unique(span[drawn], axis=0, return_inverse=True)
    for kind, (wide, tall) in enumerate(shapes.tolist()):
        picked = drawn[which.ravel() == kind]
        step = max(1, CHUNK // (wide * tall))
        for start in range(0, len(picked), step):
            chosen = picked[start:start + step]
            columns = low[chosen, 0][:, None, None] + np.arange(wide)[None, None, :]
            rows = low[chosen, 1][:, None, None] + np.arange(tall)[None, :, None]
            point = np.stack(np.broadcast_arrays(columns + 0.5, rows + 0.5), -1)
            way = np.sign(signed[chosen])[:, None, None]
            inside = np.ones(point.shape[:3], dtype=bool)
            for start_corner, end_corner in ((first, second), (second, third), (third, first)):
                edge = (end_corner[chosen] - start_corner[chosen])[:, None, None]
                towards = point - start_corner[chosen][:, None, None]
                inside &= way * (edge[..., 0] * towards[..., 1] - edge[..., 1] * towards[..., 0]) >= 0
            inside &= way != 0
            mask[np.broadcast_to(rows, inside.shape)[inside], np.broadcast_to(columns, inside.shape)[inside]] = True
    return mask


def silhouette(vertices, faces, frame, yaw, pitch, side=SIDE):
    """The mesh's mask, `side` pixels square, from the camera fitted on `frame` (low, high): a pixel is the mesh's
    when its centre falls in one of its triangles."""
    eye, right, up, back, focal = camera(frame[0], frame[1], yaw, pitch, side)
    seen = vertices - eye
    depth = np.maximum(-seen @ back, 1e-6)
    pixels = np.stack([side / 2 + focal * (seen @ right) / depth, side / 2 - focal * (seen @ up) / depth], axis=1)
    return covered(pixels[faces], np.zeros((side, side), dtype=bool))


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


def detail_views(input_view):
    """The (yaw, pitch) ways the thin and small parts are drawn from: the ring's and the input's own."""
    views = ring()
    return [(360.0 * step / views.YAWS, views.ELEVATION) for step in range(views.YAWS)] + [tuple(input_view)]


def left_out(truth_mask, made_mask):
    """The largest connected piece of `truth_mask` lying further than MISSING_REACH of the frame from every pixel of
    `made_mask`, as a share of `truth_mask`."""
    reach = MISSING_REACH * truth_mask.shape[0]
    far = truth_mask & (ndimage.distance_transform_edt(~made_mask) > reach)
    pieces, count = ndimage.label(far)
    largest = np.bincount(pieces.ravel())[1:].max() if count else 0
    return float(largest / max(truth_mask.sum(), 1))


def edge_length(mask):
    """The pixels of `mask` beside one outside it (4-neighbours, the frame's border outside): its outline's length,
    holes' rims included."""
    padded = np.pad(mask, 1)
    inner = padded[1:-1, 1:-1] & padded[:-2, 1:-1] & padded[2:, 1:-1] & padded[1:-1, :-2] & padded[1:-1, 2:]
    return int((mask & ~inner).sum())


@functools.lru_cache(maxsize=4)
def truth_masks(digest, vertices, faces, views):
    """NVIDIA's silhouettes at DETAIL_SIDE from each of `views`, kept by its `digest` (`truth_keyed`): a truth is
    measured against both branches and the withdrawn models of its row, and drawn once."""
    frame = (vertices.array.min(0), vertices.array.max(0))
    return [silhouette(vertices.array, faces.array, frame, yaw, pitch, DETAIL_SIDE) for yaw, pitch in views]


class Keyed:
    """An array kept by the digest of its bytes, so a cache finds the same truth by its content."""

    def __init__(self, array):
        self.array = np.ascontiguousarray(array)
        self.digest = hashlib.sha1(self.array.tobytes()).hexdigest()

    def __hash__(self):
        return hash(self.digest)

    def __eq__(self, other):
        return isinstance(other, Keyed) and other.digest == self.digest


def thin_and_small(truth, placed, made_faces, input_view):
    """{"missing_part": the largest part NVIDIA's model shows that the made one leaves out (left_out) at its worst way,
    "missing_ways": each way's, "outline_detail": the made outline's length over NVIDIA's (edge_length) at its least
    way, "detail_ways": each way's}, both drawn at DETAIL_SIDE from detail_views."""
    frame = (truth["vertices"].min(0), truth["vertices"].max(0))
    views = tuple(tuple(float(angle) for angle in view) for view in detail_views(input_view))
    vertices, faces = Keyed(truth["vertices"]), Keyed(truth["faces"])
    masks = truth_masks((vertices.digest, faces.digest), vertices, faces, views)
    missing, detail = [], []
    for (yaw, pitch), theirs in zip(views, masks):
        ours = silhouette(placed, made_faces, frame, yaw, pitch, DETAIL_SIDE)
        missing.append(round(left_out(theirs, ours), 5))
        detail.append(round(edge_length(ours) / max(edge_length(theirs), 1), 4))
    return {"missing_part": max(missing), "missing_ways": missing, "outline_detail": min(detail),
            "detail_ways": detail}


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
