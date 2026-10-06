"""Lay one model's points onto another's: a turn by quarter turns, then a scaled rigid fit (job robust-exp,
2026-10-06). Used to carry a picture-aligned raw Pixal3D model onto its finished (upright) model, and a part
splitter's parts onto the model they split.

Points only (a scipy KD-tree): never split or build per-piece objects from a raw Pixal3D model here; doing so on a
950k-face model took 43.5 GB and brought WSL down on 2026-10-06.
"""
import itertools

import numpy as np
from scipy.spatial import cKDTree

ROUNDS = 40
KEEP_SHARE = 80  # percentile of pairs kept each round: the raw model's floaters have no partner


def quarter_turns():
    """The 24 proper rotations that map axes onto axes."""
    for order in itertools.permutations(range(3)):
        for signs in itertools.product((1, -1), repeat=3):
            matrix = np.zeros((3, 3))
            for row, (column, sign) in enumerate(zip(order, signs)):
                matrix[row, column] = sign
            if np.linalg.det(matrix) > 0:
                yield matrix


def robust_frame(points):
    """A point cloud's middle and size, ignoring its outer 2% each way."""
    low, high = np.percentile(points, 2, axis=0), np.percentile(points, 98, axis=0)
    return (low + high) / 2, np.linalg.norm(high - low)


def similarity(source, target):
    """Kabsch with scale: (scale, rotation, shift) so that scale * rotation @ source + shift ~ target."""
    source_middle, target_middle = source.mean(0), target.mean(0)
    centred_source, centred_target = source - source_middle, target - target_middle
    left, sigma, right = np.linalg.svd(centred_source.T @ centred_target)
    flip = np.eye(3)
    flip[2, 2] = np.sign(np.linalg.det(right.T @ left.T))
    rotation = right.T @ flip @ left.T
    scale = (sigma * np.diag(flip)).sum() / (centred_source ** 2).sum()
    return scale, rotation, target_middle - scale * rotation @ source_middle


def aligned(source_points, target_points, turns=True):
    """The 4x4 matrix laying `source_points` on `target_points`, and the median gap left (in target units)."""
    tree = cKDTree(target_points)
    source_middle, source_size = robust_frame(source_points)
    target_middle, target_size = robust_frame(target_points)
    scale = target_size / source_size
    best = None
    for rotation in (quarter_turns() if turns else [np.eye(3)]):
        moved = (source_points - source_middle) @ rotation.T * scale + target_middle
        cost = np.median(tree.query(moved)[0])
        if best is None or cost < best[0]:
            best = (cost, rotation)
    rotation = best[1]
    shift = target_middle - scale * rotation @ source_middle
    for _ in range(ROUNDS):
        moved = source_points @ rotation.T * scale + shift
        distance, index = tree.query(moved)
        keep = distance < np.percentile(distance, KEEP_SHARE)
        scale, rotation, shift = similarity(source_points[keep], target_points[index[keep]])
    matrix = np.eye(4)
    matrix[:3, :3] = rotation * scale
    matrix[:3, 3] = shift
    gap = float(np.median(tree.query(source_points @ matrix[:3, :3].T + shift)[0]))
    return matrix, gap
