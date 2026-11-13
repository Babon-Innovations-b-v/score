"""The scene's ground as the sim body stands on it (pure numpy, the person's own frame, Y up): each point's ground (the
highest drawn triangle under it, at most REACH_UP over it, or over its body's lowest point or middle (`body_reach`), with
HEADROOM free over it, or what its body reaches over it where less (`body_top`), or within a knee of its body's lowest
point (`body_floor`), never one over the point with another between them), its height over it, and each triangle's
upward normal."""
import numpy as np

# Free height over a surface for a body to stand on it (metres): under less (a table top, a shelf) it is a block.
HEADROOM = 1.0
# How far over a point its ground may lie (metres): the cast's KNEE (score/stages/cast/measure.py; the test checks
# they agree), so a body the cast stands on a deck stands on the deck, not on the floor under it.
REACH_UP = 0.3
SAME = 1e-9  # metres: crossings closer than this are one (a point on an edge two triangles share)


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


def body_reach(points):
    """The highest a body's ground may lie: REACH_UP over its lowest point, or its middle (the median of its points'
    heights) where that is higher, so a roof over its head is never its ground and a seat under a seated body is
    (#98, 2026-11-07: a sit-to-stand's chair 0.40 m up, its feet on the floor, lay past REACH_UP)."""
    return max(points[:, 1].min() + REACH_UP, float(np.median(points[:, 1])))


def body_floor(points):
    """The highest a body's floor may lie whatever is over it: REACH_UP over its lowest point. The surface its feet
    stand on is its floor with a desk, a chair's seat or a railing over part of them (2026-11-13, greenhouse's
    astronaut_1 and astronaut_4: the deck under a chair and a tank, 0.42 m and less free over it, read as blocks, and
    the furniture's tops over the feet as their ground: 0.798 and 0.409 m into it)."""
    return points[:, 1].min() + REACH_UP


def body_top(points):
    """A body's highest point: a surface it sits or stands on needs no more free over it than the body reaches over it
    (`standing`'s `top`; 2026-11-13, quarters' person_bed seated on a lower bunk's mattress 0.546 m up, the upper
    bunk's underside 0.654 m over it, its head 1.14 m up: under HEADROOM the mattress read as a block, its centre of
    mass had no ground (nan) and RRA's moment limit with it, a NaN Cholesky)."""
    return float(points[:, 1].max())


def beneath(points, which, heights):
    """Whether each crossing (sorted by point, then height) lies over its point and over the lowest crossing over it:
    the point is under that solid (beneath a desk's top, its underside between), never in it. Crossings at one height
    (a point on the edge two triangles share) are one."""
    if not len(which):
        return np.zeros(0, dtype=bool)
    over = heights > points[which, 1]
    starts = np.flatnonzero(np.append(True, which[1:] != which[:-1]))
    lowest = np.minimum.reduceat(np.where(over, heights, np.inf), starts)  # each point's lowest crossing over it
    return over & (heights > np.repeat(lowest, np.diff(np.append(starts, len(which)))) + SAME)


def standing(points, ground, reach=None, floor=None, top=None):
    """Each point's ground: the highest crossing at most `reach` high (default REACH_UP over the point) with HEADROOM
    free over it, or as much as its body reaches over it where less (`top`, default none: a body's `body_top`), or at
    most `floor` high (default none: a body's `body_floor`), and not `beneath` it, its height and its triangle (nan and
    -1 where none is)."""
    reach = points[:, 1] + REACH_UP if reach is None else np.broadcast_to(reach, len(points))
    floor = np.full(len(points), -np.inf) if floor is None else np.broadcast_to(floor, len(points))
    tops = np.full(len(points), np.inf) if top is None else np.broadcast_to(top, len(points))
    which, heights, triangles = _crossings(points, ground)
    order = np.lexsort((heights, which))
    which, heights, triangles = which[order], heights[order], triangles[order]
    above = np.append(heights[1:], np.inf)
    above[np.append(which[1:] != which[:-1], True)] = np.inf  # the top crossing of each point has nothing over it
    room = np.minimum(HEADROOM, tops[which] - heights)  # the free height a surface needs: the body's own over it
    free = (((above - heights >= room) | (heights <= floor[which])) & (heights <= reach[which])
            & ~beneath(points, which, heights))
    found, under = np.full(len(points), np.nan), np.full(len(points), -1)
    which, heights, triangles = which[free], heights[free], triangles[free]
    top = which != np.append(which[1:], -1)  # the highest standing crossing of each point
    found[which[top]], under[which[top]] = heights[top], triangles[top]
    return found, under


def heights_over(points, ground, reach=None, floor=None, top=None):
    """Each point's height over its ground (`standing`'s reach, floor and top); nan where it has none."""
    return points[:, 1] - standing(points, ground, reach, floor, top)[0]


def normals(ground):
    """Each triangle's upward unit normal."""
    found = np.cross(ground[:, 1] - ground[:, 0], ground[:, 2] - ground[:, 0])
    found *= np.sign(found[:, 1:2]) + (found[:, 1:2] == 0)
    return found / np.maximum(np.linalg.norm(found, axis=1, keepdims=True), 1e-12)
