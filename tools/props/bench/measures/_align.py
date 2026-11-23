"""The made model set on the truth: kept at the size its route laid it (the route's own uniform laying), turned by the
best of the cube's 24 axis turns about its box's middle, then moved by ICP (turn and move, never scale), so a size
error stays a size error and a lean shows as the turn it takes to stand it."""
import itertools

import numpy as np
import trimesh
from scipy.spatial import cKDTree

from . import _mesh

POINTS = 4000  # surface points each side for the turn and ICP
# Turns within this share of the best two-way distance are the same fit: the one leaning least is taken. Two samplings
# of one surface differ by up to 3% in it (the calibration's 0.5 x 0.4 x 0.8 m box cut again: its upside-down turn
# measured 0.01053 against upright's 0.01085), so 1% stood a perfect copy on its head (#163 calibration).
TIE = 0.05
ICP_ROUNDS = 40


def axis_turns():
    """The 24 turns that take the axes onto the axes (signed permutations with determinant +1)."""
    found = []
    for order in itertools.permutations(range(3)):
        for signs in itertools.product((1.0, -1.0), repeat=3):
            turn = np.zeros((3, 3))
            turn[range(3), order] = signs
            if np.linalg.det(turn) > 0:
                found.append(turn)
    return found


def two_way(points, tree, other, other_tree):
    """The mean of the two one-way mean nearest distances."""
    return (tree.query(other)[0].mean() + other_tree.query(points)[0].mean()) / 2


def up_error(matrix):
    """The degrees between up (+Z) and where the matrix turns it: how far the route's up is from the truth's."""
    return float(np.degrees(np.arccos(np.clip(matrix[2, 2], -1.0, 1.0))))


def aligned(truth, made):
    """(4x4 made-to-truth matrix, {"turn_distance", "up_error"}): the best axis turn about the boxes' middles, then
    ICP from it, of the made surface onto the truth's."""
    target, _ = _mesh.sampled(truth["vertices"], truth["faces"], POINTS, seed=1)
    source, _ = _mesh.sampled(made["vertices"], made["faces"], POINTS, seed=2)
    target_tree = cKDTree(target)
    target_middle = (truth["vertices"].min(0) + truth["vertices"].max(0)) / 2
    source_middle = (made["vertices"].min(0) + made["vertices"].max(0)) / 2
    tried = []
    for turn in axis_turns():
        matrix = np.eye(4)
        matrix[:3, :3] = turn
        matrix[:3, 3] = target_middle - turn @ source_middle
        placed = _mesh.moved(source, matrix)
        tried.append((two_way(target, target_tree, placed, cKDTree(placed)), matrix))
    best = min(distance for distance, _ in tried)
    start = min((up_error(matrix), distance, index) for index, (distance, matrix) in enumerate(tried)
                if distance <= best * (1 + TIE))
    matrix, _, _ = trimesh.registration.icp(source, target, initial=tried[start[2]][1], threshold=1e-9,
                                            max_iterations=ICP_ROUNDS, reflection=False, scale=False)
    return matrix, {"turn_distance": float(tried[start[2]][0]), "up_error": round(up_error(matrix), 3)}
