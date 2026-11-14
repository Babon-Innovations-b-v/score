"""The scene's ground as the sim body stands on it (pure numpy, the person's own frame, Y up): each point's ground (the
highest drawn triangle under it, at most REACH_UP over it, or over its body's lowest point or middle (`body_reach`), with
HEADROOM free over it, or what its body reaches over it where less (`body_top`), or within a knee of its body's lowest
point (`body_floor`), never one over the point with another between them nor one of a closed piece the point is
under, not in (`outside`)), its height over it, and each triangle's upward normal."""
import numpy as np

# Free height over a surface for a body to stand on it (metres): under less (a table top, a shelf) it is a block.
HEADROOM = 1.0
# How far over a point its ground may lie (metres): the cast's KNEE (score/stages/cast/measure.py; the test checks
# they agree), so a body the cast stands on a deck stands on the deck, not on the floor under it.
REACH_UP = 0.3
# A drawn triangle whose upward normal's height is under this (steeper than 60 degrees) is a back, not a floor: a
# point is near it along its normal (`leaning`), not along the upright line (2026-11-14, cockpit's pilot: his chest
# and shoulder blades 0 to 3.5 mm into his seat's back, never pushed, so his weight, 8 mm behind the three skin points
# on his cushion, left 0.95 N m of residual over its 0.76 on frames 136 and 137).
STEEP = 0.5
CELL = 0.03  # metres: the grid `leaning` finds each point's steep triangles on
BIG_CELLS = 20_000  # a steep triangle whose box spans more CELLs than this is measured against the points directly
PAIRS = 4_000_000  # (point, triangle) pairs `leaning` measures at once
SAME = 1e-9  # metres: crossings closer than this are one (a point on an edge two triangles share)
CORNER = 1e-6  # metres: triangles with corners this near join into one piece (`pieces`)
_PIECES = {}  # id of a ground array: (the array, its triangles' pieces), worked out once (`pieces`)


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


def pieces(ground):
    """Each triangle's piece (an integer): the triangles joined through corners at one place (within a micron), so a
    closed mesh is one piece whatever its faces' own vertices. Worked out once for each ground array (`_PIECES`)."""
    kept = _PIECES.get(id(ground))
    if kept is not None and kept[0] is ground:
        return kept[1]
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    corners = np.round(np.asarray(ground, dtype=float).reshape(-1, 3) / CORNER).astype(np.int64)
    _, corner = np.unique(corners, axis=0, return_inverse=True)
    corner = corner.reshape(-1, 3)
    count = int(corner.max()) + 1 if len(corner) else 0
    rows, cols = np.concatenate([corner[:, 0], corner[:, 1]]), np.concatenate([corner[:, 1], corner[:, 2]])
    found = connected_components(coo_matrix((np.ones(len(rows)), (rows, cols)), shape=(count, count)),
                                 directed=False)[1][corner[:, 0]] if count else np.zeros(0, dtype=int)
    _PIECES[id(ground)] = (ground, found)
    return found


def outside(points, which, heights, triangles, ground):
    """Whether each crossing (sorted by point, then height) lies over its point with its piece (`pieces`) crossing
    the upright line over the point an even number of times: the point is outside that piece, under it (a desk's
    apron, a bunk's rail over a foot on the floor), never in it. Crossings of one piece at one height (an edge two
    of its triangles share) are one."""
    if not len(which):
        return np.zeros(0, dtype=bool)
    piece = pieces(ground)[triangles]
    over = heights > points[which, 1]
    key = which.astype(np.int64) * (int(piece.max()) + 1) + piece
    order = np.lexsort((heights, key))
    same = np.append(False, (key[order][1:] == key[order][:-1]) & (np.diff(heights[order]) <= SAME))
    counted = np.zeros(len(which), dtype=bool)
    counted[order] = over[order] & ~same
    keys, index = np.unique(key, return_inverse=True)
    crossed = np.bincount(index, weights=counted, minlength=len(keys))
    return over & (crossed[index] % 2 == 0)


def standing(points, ground, reach=None, floor=None, top=None):
    """Each point's ground: the highest crossing at most `reach` high (default REACH_UP over the point) with HEADROOM
    free over it, or as much as its body reaches over it where less (`top`, default none: a body's `body_top`), or at
    most `floor` high (default none: a body's `body_floor`), and neither `beneath` it nor of a piece it is `outside`
    of, its height and its triangle (nan and -1 where none is)."""
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
            & ~beneath(points, which, heights) & ~outside(points, which, heights, triangles, ground))
    found, under = np.full(len(points), np.nan), np.full(len(points), -1)
    which, heights, triangles = which[free], heights[free], triangles[free]
    top = which != np.append(which[1:], -1)  # the highest standing crossing of each point
    found[which[top]], under[which[top]] = heights[top], triangles[top]
    return found, under


def heights_over(points, ground, reach=None, floor=None, top=None):
    """Each point's height over its ground (`standing`'s reach, floor and top); nan where it has none."""
    return points[:, 1] - standing(points, ground, reach, floor, top)[0]


def leaning(points, ground, centres, within, floor):
    """Each point's back (a steep drawn triangle, its upward normal's height under STEEP: a seat's back, a wall, a
    console's front, which `standing` measures along the upright line and so never as near), the nearest one whose
    plane the point lies within `within` metres of, in front of it or in it, its foot on the plane inside the
    triangle: its distance from the plane towards its body's middle (`centres`, each point's, the side the back
    pushes it to; under 0 in it), its triangle, that unit normal and the foot (nan and -1 where it has none). A point
    at most `floor` high (each point's, its body's `body_floor`: a knee over its lowest point) has none: a riser or a
    console's foot the toe meets is no back, and a trip on it shows as residual."""
    points = np.asarray(points, dtype=float)
    centres = np.broadcast_to(np.asarray(centres, dtype=float), points.shape)
    raised = points[:, 1] > np.broadcast_to(floor, len(points)) if len(points) else np.zeros(0, dtype=bool)
    found, under = np.full(len(points), np.nan), np.full(len(points), -1)
    turned, feet = np.full((len(points), 3), np.nan), np.full((len(points), 3), np.nan)
    if not len(points) or not len(ground):
        return found, under, turned, feet
    up = normals(ground)
    candidates = np.flatnonzero(raised)
    if not len(candidates):
        return found, under, turned, feet
    pairs = _near_steep(points[candidates], ground, up, within)
    for point, triangle in pairs:
        corners = ground[triangle]
        normal = up[triangle] * np.where(np.einsum("ij,ij->i", centres[candidates[point]] - corners[:, 0],
                                                   up[triangle]) < 0.0, -1.0, 1.0)[:, None]
        distance = np.einsum("ij,ij->i", points[candidates[point]] - corners[:, 0], normal)
        close = np.abs(distance) <= within
        point, triangle, corners, normal, distance = (values[close] for values in
                                                      (point, triangle, corners, normal, distance))
        foot = points[candidates[point]] - distance[:, None] * normal
        edge1, edge2, offset = corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0], foot - corners[:, 0]
        dot11, dot12, dot22 = (np.einsum("ij,ij->i", one, two) for one, two in
                               ((edge1, edge1), (edge1, edge2), (edge2, edge2)))
        dot1, dot2 = np.einsum("ij,ij->i", offset, edge1), np.einsum("ij,ij->i", offset, edge2)
        det = dot11 * dot22 - dot12 ** 2
        flat = np.abs(det) > 1e-18  # a triangle with no area holds no foot
        safe = np.where(flat, det, 1.0)
        one, two = (dot22 * dot1 - dot12 * dot2) / safe, (dot11 * dot2 - dot12 * dot1) / safe
        inside = flat & (one >= 0) & (two >= 0) & (one + two <= 1)
        point, triangle, normal, distance, foot = (values[inside] for values in
                                                   (point, triangle, normal, distance, foot))
        if not len(point):
            continue
        order = np.lexsort((triangle, np.abs(distance), point))  # each point's nearest, then its first triangle
        first = order[np.append(True, point[order][1:] != point[order][:-1])]
        mine = candidates[point[first]]
        better = np.abs(distance[first]) < np.nan_to_num(np.abs(found[mine]), nan=np.inf)
        first, mine = first[better], mine[better]
        found[mine], under[mine] = distance[first], triangle[first]
        turned[mine], feet[mine] = normal[first], foot[first]
    return found, under, turned, feet


def _near_steep(points, ground, up, within):
    """The (point, triangle) pairs `leaning` measures, in chunks of at most PAIRS: each point with every steep
    triangle (STEEP) whose box, widened by `within`, holds the point's CELL of a grid over the points' box, near the
    triangle's plane; a triangle whose box spans over BIG_CELLS cells (a long slanted wall) with every point in its
    box within `within` of its plane, one triangle at a time."""
    low, high = points.min(axis=0) - within, points.max(axis=0) + within
    lows, highs = ground.min(axis=1) - within, ground.max(axis=1) + within
    steep = np.flatnonzero((up[:, 1] < STEEP) & (lows <= high).all(axis=1) & (highs >= low).all(axis=1))
    if not len(steep):
        return
    shape = np.floor((high - low) / CELL).astype(np.int64) + 1
    first_cell = np.floor((np.maximum(lows[steep], low) - low) / CELL).astype(np.int64)
    spans = np.floor((np.minimum(highs[steep], high) - low) / CELL).astype(np.int64) - first_cell + 1
    counts = spans.prod(axis=1)
    for triangle in steep[counts > BIG_CELLS]:
        boxed = np.flatnonzero(((points >= lows[triangle]) & (points <= highs[triangle])).all(axis=1))
        boxed = boxed[np.abs((points[boxed] - ground[triangle, 0]) @ up[triangle]) <= within]
        yield boxed, np.full(len(boxed), triangle)
    small = counts <= BIG_CELLS
    steep, first_cell, spans, counts = steep[small], first_cell[small], spans[small], counts[small]
    owner = np.repeat(np.arange(len(steep)), counts)
    local = np.arange(counts.sum()) - np.repeat(np.cumsum(counts) - counts, counts)
    deep, tall = spans[owner, 2], spans[owner, 1]
    cells = first_cell[owner] + np.stack([local // (tall * deep), (local // deep) % tall, local % deep], axis=1)
    # a cell whose middle stands further than `within` and half its diagonal off the triangle's plane holds no point
    # near it (a long slanted wall's box is the whole room)
    middles = low + (cells + 0.5) * CELL
    held = np.abs(np.einsum("ij,ij->i", middles - ground[steep[owner], 0], up[steep[owner]])) <= within + CELL * 0.87
    cells, owner = cells[held], owner[held]
    keys = (cells[:, 0] * shape[1] + cells[:, 1]) * shape[2] + cells[:, 2]
    order = np.argsort(keys, kind="stable")
    keys, triangles = keys[order], steep[owner[order]]
    mine = np.floor((points - low) / CELL).astype(np.int64)
    mine = (mine[:, 0] * shape[1] + mine[:, 1]) * shape[2] + mine[:, 2]
    starts, ends = np.searchsorted(keys, mine, side="left"), np.searchsorted(keys, mine, side="right")
    many = ends - starts
    near = np.flatnonzero(many)
    bounds = np.searchsorted(np.cumsum(many[near]), np.arange(PAIRS, many[near].sum() + PAIRS, PAIRS), side="right")
    for chunk in np.split(near, np.unique(bounds[:-1])):
        counted = many[chunk]
        point = np.repeat(chunk, counted)
        at = np.arange(counted.sum()) - np.repeat(np.cumsum(counted) - counted, counted) + np.repeat(starts[chunk],
                                                                                                    counted)
        yield point, triangles[at]


def normals(ground):
    """Each triangle's upward unit normal."""
    found = np.cross(ground[:, 1] - ground[:, 0], ground[:, 2] - ground[:, 0])
    found *= np.sign(found[:, 1:2]) + (found[:, 1:2] == 0)
    return found / np.maximum(np.linalg.norm(found, axis=1, keepdims=True), 1e-12)
