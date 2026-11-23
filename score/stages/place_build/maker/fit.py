"""A made model set in a library model's frame (y up, metres): TRELLIS.2 gives a model in a unit box facing roughly
its picture's camera, so it is turned a quarter turn at a time, scaled uniformly and moved until it best covers the
model it replaces (the smallest two-way mean distance between points on both surfaces), standing where that one
stands; or, with no model to replace, scaled to a given height, or to a given size's longest side, and stood on y=0
at its centre. A model set at a size is first turned to its close-up's heading (`headed`): TRELLIS.2 lays a model with
its own heading (a desk's long side along x, #166), so the quarter turn, or its mirror, whose outline from the
close-up's camera best overlaps the picture's is the one laid.

    fitted_matrix(points, like_points) -> (matrix 4x4, {"yaw", "scale", "distance_m"})
    headed(points, cut, turn, down)    -> (matrix 4x4, {"yaw", "mirrored", "overlap"})
    height_matrix(points, height)      -> matrix 4x4
    size_matrix(points, size)          -> matrix 4x4
"""
import numpy as np
from scipy import ndimage
from scipy.spatial import cKDTree

YAWS = (0.0, 90.0, 180.0, 270.0)
OUTLINE = 64  # pixels across the square an outline is compared in, its longer side filling it
MIRROR_GAIN = 0.05  # a mirror is laid only when its overlap beats every quarter turn's by this (the picture says so)
TIE = 0.01  # an overlap within this of the best keeps the earlier turn (TRELLIS.2's own heading first): a box's
# half turns differ by under it (tc1's toaster: 0.897 and 0.894)


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


def view_axes(turn, down):
    """The close-up camera's right and up in a Y-up frame (front +z): turned `turn` degrees to the model's right from
    its front and looking down `down` degrees; straight down (90) has the front at the frame's foot (the prop route's
    flat row, seen from above with its back up)."""
    turn, down = np.radians(turn), np.radians(down)
    back = np.array([np.sin(turn) * np.cos(down), np.sin(down), np.cos(turn) * np.cos(down)])
    up = np.array([0.0, 0.0, -1.0]) if np.isclose(down, np.pi / 2) else np.array([0.0, 1.0, 0.0])
    right = np.cross(up, back)
    right /= np.linalg.norm(right)
    return right, np.cross(back, right)


def outline(across, upward):
    """Points (their across and upward places) drawn as a filled outline in an OUTLINE square, centred, its longer
    side filling it; closed by a pixel so a surface's sample spacing leaves no gaps."""
    across, upward = across - (across.min() + across.max()) / 2, upward - (upward.min() + upward.max()) / 2
    scale = (OUTLINE - 3) / max(np.ptp(across), np.ptp(upward), 1e-9)
    columns = np.clip(np.round(across * scale + OUTLINE / 2).astype(int), 0, OUTLINE - 1)
    rows = np.clip(np.round(OUTLINE / 2 - upward * scale).astype(int), 0, OUTLINE - 1)
    drawn = np.zeros((OUTLINE, OUTLINE), bool)
    drawn[rows, columns] = True
    return ndimage.binary_closing(drawn, iterations=1, border_value=0)


def cut_outline(cut):
    """A cut-out's opaque pixels (a boolean picture, rows down) as an outline (`outline`)."""
    rows, columns = np.nonzero(cut)
    return outline(columns.astype(float), -rows.astype(float))


def overlap(drawn, seen):
    """Intersection over union of two outlines."""
    return float((drawn & seen).sum() / max((drawn | seen).sum(), 1))


def headed(points, cut, turn, down):
    """The turn about y (a quarter turn, mirrored across x only when the picture says so, MIRROR_GAIN) that lays
    `points` (Y up) as the close-up `cut` (its opaque pixels) shows it from a camera turned `turn` degrees and looking
    down `down`; what was chosen."""
    right, up = view_axes(turn, down)
    seen = cut_outline(cut)
    best = {}
    for mirrored in (False, True):
        for yaw in YAWS:
            matrix = yawed(yaw) @ np.diag([-1.0 if mirrored else 1.0, 1.0, 1.0, 1.0])
            laid = applied(matrix, points)
            score = overlap(outline(laid @ right, laid @ up), seen)
            if mirrored not in best or score > best[mirrored][0] + TIE:
                best[mirrored] = (score, matrix, yaw)
    mirrored = best[True][0] > best[False][0] + MIRROR_GAIN
    score, matrix, yaw = best[mirrored]
    return matrix, {"yaw": yaw, "mirrored": mirrored, "overlap": round(score, 4)}
