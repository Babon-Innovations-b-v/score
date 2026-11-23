"""A made model set in a library model's frame (y up, metres): TRELLIS.2 gives a model in a unit box facing roughly
its picture's camera, so it is turned a quarter turn at a time, scaled uniformly and moved until it best covers the
model it replaces (the smallest two-way mean distance between points on both surfaces), standing where that one
stands; or, with no model to replace, scaled to a given height, or to a given size's longest side, and stood on y=0
at its centre.

    fitted_matrix(points, like_points) -> (matrix 4x4, {"yaw", "scale", "distance_m"})
    height_matrix(points, height)      -> matrix 4x4
    size_matrix(points, size)          -> matrix 4x4
"""
import numpy as np
from scipy.spatial import cKDTree

YAWS = (0.0, 90.0, 180.0, 270.0)


def yawed(degrees):
    """The 4x4 turn about y by `degrees`."""
    angle = np.radians(degrees)
    turn = np.eye(4)
    turn[0, 0], turn[0, 2], turn[2, 0], turn[2, 2] = np.cos(angle), np.sin(angle), -np.sin(angle), np.cos(angle)
    return turn


def applied(matrix, points):
    return points @ matrix[:3, :3].T + matrix[:3, 3]


def standing(points, like_low, like_high):
    """The 4x4 move that sets `points`' box centre (x, z) on the like box's and its floor on the like box's floor."""
    low, high = points.min(0), points.max(0)
    move = np.eye(4)
    move[:3, 3] = [(like_low[0] + like_high[0] - low[0] - high[0]) / 2, like_low[1] - low[1],
                   (like_low[2] + like_high[2] - low[2] - high[2]) / 2]
    return move


def distance(points, like_tree, like_points):
    """The two-way mean nearest distance between two point sets (metres)."""
    there = like_tree.query(points)[0].mean()
    back = cKDTree(points).query(like_points)[0].mean()
    return (there + back) / 2


def fitted_matrix(points, like_points):
    """The turn, uniform scale and move of `points` that best covers `like_points`; what was chosen. The scales tried
    are each box side's ratio and the box diagonal's, under each quarter turn."""
    like_low, like_high = like_points.min(0), like_points.max(0)
    tree = cKDTree(like_points)
    best = None
    for yaw in YAWS:
        turned = applied(yawed(yaw), points)
        size, like_size = np.ptp(turned, 0), like_high - like_low
        ratios = [like_size[axis] / size[axis] for axis in range(3) if size[axis] > 1e-6]
        ratios.append(np.linalg.norm(like_size) / np.linalg.norm(size))
        for scale in ratios:
            scaled = np.diag([scale, scale, scale, 1.0]) @ yawed(yaw)
            matrix = standing(applied(scaled, points), like_low, like_high) @ scaled
            gap = distance(applied(matrix, points), tree, like_points)
            if best is None or gap < best[0]:
                best = (gap, matrix, {"yaw": yaw, "scale": round(float(scale), 5), "distance_m": round(float(gap), 4)})
    return best[1], best[2]


def height_matrix(points, height):
    """The scale that makes `points` `height` metres tall, stood on y=0 centred on x and z."""
    scale = height / np.ptp(points[:, 1])
    scaled = np.diag([scale, scale, scale, 1.0])
    return standing(applied(scaled, points), np.zeros(3), np.zeros(3)) @ scaled


def size_matrix(points, size):
    """The uniform scale that makes `points`' longest side the longest of `size` (wide, deep, tall metres: the
    route's own laying, its other sides what the picture gave), stood on y=0 centred on x and z."""
    scale = max(float(side) for side in size) / np.ptp(points, 0).max()
    scaled = np.diag([scale, scale, scale, 1.0])
    return standing(applied(scaled, points), np.zeros(3), np.zeros(3)) @ scaled
