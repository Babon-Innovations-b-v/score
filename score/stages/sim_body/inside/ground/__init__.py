"""The scene's ground as the sim body stands on it (pure numpy, the person's own frame, Y up): each point's ground (the
highest drawn triangle under it, at most REACH_UP over it, with HEADROOM free over it), its height over it, and each triangle's upward normal."""
import numpy as np

# Free height over a surface for a body to stand on it (metres): under less (a table top, a shelf) it is a block.
HEADROOM = 1.0
# How far over a point its ground may lie (metres): the cast's KNEE (score/stages/cast/measure.py; the test checks
# they agree), so a body the cast stands on a deck stands on the deck, not on the floor under it.
REACH_UP = 0.3


def _crossings(points, ground):
    """Where the triangles cross the upright line through each point (x, z): its point indices, heights and
    triangles."""
    corner, edge1, edge2 = ground[:, 0], ground[:, 1] - ground[:, 0], ground[:, 2] - ground[:, 0]
    det = edge1[:, 0] * edge2[:, 2] - edge1[:, 2] * edge2[:, 0]
    flat = np.abs(det) > 1e-12  # an upright triangle crosses no upright line
    corner, edge1, edge2, det = corner[flat], edge1[flat], edge2[flat], det[flat]
    triangles = np.flatnonzero(flat)
    low, high = ground[flat][:, :, [0, 2]].min(axis=1), ground[flat][:, :, [0, 2]].max(axis=1)
    order = np.argsort(points[:, 0])
    firsts = np.searchsorted(points[order, 0], low[:, 0], side="left")
    lasts = np.searchsorted(points[order, 0], high[:, 0], side="right")
    found_points, found_heights, found_triangles = [], [], []
    for index in range(len(corner)):
        mine = order[firsts[index]:lasts[index]]
        mine = mine[(points[mine, 2] >= low[index, 1]) & (points[mine, 2] <= high[index, 1])]
        dx, dz = points[mine, 0] - corner[index, 0], points[mine, 2] - corner[index, 2]
        one = (dx * edge2[index, 2] - dz * edge2[index, 0]) / det[index]
        two = (edge1[index, 0] * dz - edge1[index, 2] * dx) / det[index]
        inside = (one >= 0) & (two >= 0) & (one + two <= 1)
        found_points.append(mine[inside])
        found_heights.append(corner[index, 1] + one[inside] * edge1[index, 1] + two[inside] * edge2[index, 1])
        found_triangles.append(np.full(inside.sum(), triangles[index]))
    return np.concatenate(found_points), np.concatenate(found_heights), np.concatenate(found_triangles)


def standing(points, ground):
    """Each point's ground: the highest crossing at most REACH_UP over it with HEADROOM free over it, its height and
    its triangle (nan and -1 where none is)."""
    which, heights, triangles = _crossings(points, ground)
    order = np.lexsort((heights, which))
    which, heights, triangles = which[order], heights[order], triangles[order]
    above = np.append(heights[1:], np.inf)
    above[np.append(which[1:] != which[:-1], True)] = np.inf  # the top crossing of each point has nothing over it
    free = (above - heights >= HEADROOM) & (heights <= points[which, 1] + REACH_UP)
    found, under = np.full(len(points), np.nan), np.full(len(points), -1)
    which, heights, triangles = which[free], heights[free], triangles[free]
    top = which != np.append(which[1:], -1)  # the highest standing crossing of each point
    found[which[top]], under[which[top]] = heights[top], triangles[top]
    return found, under


def heights_over(points, ground):
    """Each point's height over its ground; nan where it has none."""
    return points[:, 1] - standing(points, ground)[0]


def normals(ground):
    """Each triangle's upward unit normal."""
    found = np.cross(ground[:, 1] - ground[:, 0], ground[:, 2] - ground[:, 0])
    found *= np.sign(found[:, 1:2]) + (found[:, 1:2] == 0)
    return found / np.maximum(np.linalg.norm(found, axis=1, keepdims=True), 1e-12)
