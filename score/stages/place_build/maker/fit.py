"""A made model set in a library model's frame (y up, metres): TRELLIS.2 gives a model in a unit box facing roughly
its picture's camera, so it is turned a quarter turn at a time, scaled uniformly and moved until it best covers the
model it replaces (the smallest two-way mean distance between points on both surfaces), standing where that one
stands; or, with no model to replace, scaled to a given height, or to a given size, and stood on y=0 at its centre.
A model set at a size is first turned to its close-up's heading (`headed`): TRELLIS.2 lays a model with its own heading
(a desk's long side along x, #166), so the quarter turn (never a mirror: TRELLIS.2 makes its picture's hand) whose
outline from the close-up's camera best overlaps the picture's is the one laid; turns its outline cannot tell apart (a
box's front and back) are left to the close-up's content (`pick`, front.picked, #192). It is then brought to each of
the size's sides (`size_matrix`, #170: a uniform scale kept TRELLIS.2's proportions, tc2's sign 13% too thick and its
desk 9% too wide), each axis at most STRETCH off the uniform scale that sets its longest side, so a part thin along an
axis is never thinned or thickened past it.

    fitted_matrix(points, like_points) -> (matrix 4x4, {"yaw", "scale", "distance_m"})
    headed(points, cut, turn, down, pick=None) -> (matrix 4x4, {"yaw", "overlap"[, "open", "front"]})
    height_matrix(points, height)      -> matrix 4x4
    size_matrix(points, size)          -> (matrix 4x4, {"stretch", "off"})
"""
import numpy as np
from scipy import ndimage
from scipy.spatial import cKDTree

YAWS = (0.0, 90.0, 180.0, 270.0)
OUTLINE = 64  # pixels across the square an outline is compared in, its longer side filling it
STRETCH = 0.25  # the most one axis is scaled off the uniform scale, either way: tc2's furthest was 13.4% (the sign's
# depth); past a quarter the row and the model disagree on what the thing is (a wrong heading or a wrong row), and a
# leg or a panel along that axis would come out a quarter thinner or thicker than TRELLIS.2 drew it
TIE = 0.01  # an overlap within this of the best keeps the earlier turn (TRELLIS.2's own heading first): a box's
# half turns differ by under it (tc1's toaster: 0.897 and 0.894)
FRONT_BAND = 0.05  # turns whose outline overlap is within this of the best are left to the close-up's content
# (front.picked, #192): tc4r's desk's 90 and 270 degree outlines 0.551 and 0.538 (the right one the lower), its
# fridge's four within 0.007; a chair's half turn shows another outline and stays out


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
    """The scale of each axis that brings `points` (Y up, front +z, already headed) to `size` (wide, deep, tall
    metres), each at most STRETCH off the uniform scale that makes its longest side the size's longest, stood on y=0
    centred on x and z; {"stretch": each axis' scale over that uniform one, "off": the laid box's furthest side from
    the size's, less one (0 when the bound held none)}, wide, deep, tall."""
    wide, deep, tall = (float(side) for side in size)
    wanted, sides = np.array([wide, tall, deep]), np.maximum(np.ptp(points, 0), 1e-12)
    uniform = wanted.max() / sides.max()
    scales = np.clip(wanted / sides, uniform / (1 + STRETCH), uniform * (1 + STRETCH))
    scaled = np.diag([*scales, 1.0])
    laid = sides * scales / wanted
    how = {"stretch": [round(float(scales[axis] / uniform), 4) for axis in (0, 2, 1)],
           "off": round(float(np.maximum(laid, 1 / laid).max() - 1), 4)}
    return standing(applied(scaled, points), np.zeros(3), np.zeros(3)) @ scaled, how


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


def headed(points, cut, turn, down, pick=None):
    """The quarter turn about y that lays `points` (Y up) as the close-up `cut` (its opaque pixels) shows it from a
    camera turned `turn` degrees and looking down `down`; what was chosen. Never a mirror (#159 r15: TRELLIS.2 makes
    its picture's hand, and hand drill b01, mirrored on a 0.05 better outline, laid its crank pointing at the camera
    behind its own knob, so no look drew it). Turns whose outline overlaps within FRONT_BAND of the best are open (a
    box-like object's front and back): `pick` (front.picked's way: the open turns' matrices in, an index and its reason
    out) decides between them from the close-up's content, else a later turn is kept over an earlier only when it
    beats it by TIE (TRELLIS.2's own heading first)."""
    right, up = view_axes(turn, down)
    seen = cut_outline(cut)
    tried = []
    for yaw in YAWS:
        laid = applied(yawed(yaw), points)
        tried.append((overlap(outline(laid @ right, laid @ up), seen), yawed(yaw), yaw))
    best = max(score for score, _, _ in tried)
    opened = [entry for entry in tried if entry[0] >= best - FRONT_BAND]
    if pick is not None and len(opened) > 1:
        index, reason = pick([matrix for _, matrix, _ in opened])
        score, matrix, yaw = opened[index]
        return matrix, {"yaw": yaw, "overlap": round(score, 4), "open": [entry[2] for entry in opened],
                        "front": reason}
    kept = tried[0]
    for entry in tried[1:]:
        if entry[0] > kept[0] + TIE:
            kept = entry
    score, matrix, yaw = kept
    return matrix, {"yaw": yaw, "overlap": round(score, 4)}
