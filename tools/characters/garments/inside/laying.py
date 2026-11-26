"""A garment's box mesh laid round the body before it is sewn, numpy and scipy only: imported by drape.py in Newton's
Python (its inside test the card's winding number) and by the garments test in score's (`winding`, on toy bodies).

GarmentCode lays each panel flat in its place round its own mean body; on another body a panel's points can stand
inside it (woman_stair's tee sleeves' fronts up to 5.7 cm inside her arms, her jeans' fronts 1.7 cm inside her
thighs, 2026-11-25). Moved straight off the skin point nearest them, as an outer layer's points were, such points went
deeper in. Laid here, a point inside the body is first put out through the skin nearest it; one that this leaves
inside (her jeans' front crotch curve laid 3 to 4 cm above her crotch, where the skin nearest it is a thigh's and
past it the other thigh, 2026-11-25) is moved instead the shortest way out along the body's six axes; then every
point is moved the layer's reach further off. A point the laying leaves inside refuses the garment (drape.py), never
sewn.

A box mesh laid round the body has the triangles beside each seam stretched across it (a seam's points are shared, so a
back panel's triangle at the shoulder reaches the front panel's edge: woman_stair_modern's tee 15 to 50 times its flat
panel's lengths, edges up to 39 cm on a 1.5 cm mesh). Resting at their flat panels from the first substep, those
triangles pulled their seams shut in two frames, crushed a shoulder seam's edge from 1.3 cm to 0.4 mm, and Newton's
float32 membrane read the area ratio of a triangle 23 times stretched and that flat as nothing (its J_s squared, the
difference of two numbers near 2.8e5, clamped to 1e-20): a force of 4e11 N, a hessian of 1e23, a NaN point and "the
cloth blew up sewing" (2026-11-25). Sewn here, each triangle rests first as laid and its rest goes over to its flat
panel's while the cloth sews (`rest_lengths`), so no triangle is ever far from its rest.

GarmentCode lays a trouser leg's front and back panels flat, their inseams together beside its crotch and the back
panel reaching far out to the side, so the laid leg's middle stood 12 cm outside woman_stair's own leg, the back
panel's inseam strip through her calf and knee: sewn, the leg's lower cloth was caught on the wrong side of the calf
and hung from it as a flap (#225 round 8; round 6's hems as well). Laid here, each leg's points are moved across to
stand over the body's own leg first (`over_legs`).
"""
import numpy as np
from scipy.spatial import cKDTree

INSIDE = 0.5  # a point's winding number past this is inside the body (1 inside a closed surface, 0 outside)
OUT_ROUNDS = 20  # steps of `clear` a point still inside is looked along each axis for the way out
AXES = np.array([[1.0, 0, 0], [-1.0, 0, 0], [0, 1.0, 0], [0, -1.0, 0], [0, 0, 1.0], [0, 0, -1.0]])
# A triangle whose rest as laid would be thinner than this share of its flat panel's area starts at its flat rest: a
# sliver rest (woman_stair_modern's jeans have laid triangles a thousandth of their flat area) turns a small opening of
# the cloth into a stretch past what float32 reads.
SLIVER = 0.5
LEVEL_M = 0.01  # the band a level's points and skin are read in (half its height)
LEG_LEVELS = 9  # levels of a leg's lower half its move across is read at
RING_WAYS = 360  # level ways out from a waistband's middle the skin's ring round her is read along
CROTCH_GAP_M = 0.01  # a leg moved in towards the crotch's middle keeps its points this far off it (the legs apart)
UNDER_FOOT_M = 0.03  # sewn cloth whose nearest skin lies this near a point's is the cloth over (or under) it
FACING_DEGREES = 45.0  # off a skin point's normal, the skin ahead of it that faces it is looked for


def winding(points, skin, faces):
    """Each point's generalized winding number about the body's triangles (Jacobson et al. 2013: the triangles'
    solid angles over 4 pi, Van Oosterom and Strackee's formula): about 1 inside, 0 outside, holes and all. All
    points against all triangles at once: for toy bodies (the card's winding number does the real one)."""
    towards = np.asarray(skin, dtype=float)[np.asarray(faces)][None] - np.asarray(points, dtype=float)[:, None, None]
    lengths = np.linalg.norm(towards, axis=3)
    one, two, three = towards[:, :, 0], towards[:, :, 1], towards[:, :, 2]
    volume = np.sum(one * np.cross(two, three), axis=2)
    below = (lengths[:, :, 0] * lengths[:, :, 1] * lengths[:, :, 2] + np.sum(one * two, axis=2) * lengths[:, :, 2]
             + np.sum(two * three, axis=2) * lengths[:, :, 0] + np.sum(three * one, axis=2) * lengths[:, :, 1])
    return np.arctan2(volume, below).sum(axis=1) / (2.0 * np.pi)


def leg_points(record):
    """A garment's leg points in its box mesh (GarmentCode's Pants panels `pant_<f|b>_<l|r>`): {+1: the left leg's
    (+x), -1: the right leg's}, each held by its own leg's panels alone, and the points both legs' panels hold (the
    crotch seam). Empty for a garment with no legs."""
    names = [str(name) for name in record["panel_names"]]
    box, panel = np.asarray(record["box"]), np.asarray(record["panel"])
    held = {}
    for side, tag in ((1, "l"), (-1, "r")):
        numbers = [number for number, name in enumerate(names) if name.startswith("pant_") and name.endswith(f"_{tag}")]
        held[side] = np.unique(box[np.isin(panel, numbers)])
    if not len(held[1]) or not len(held[-1]):
        return {}, np.zeros(0, dtype=np.int64)
    crotch = np.intersect1d(held[1], held[-1])
    return {side: np.setdiff1d(points, crotch) for side, points in held.items()}, crotch


def leg_middles(points, skin, side, middle, level):
    """The middles (x) of a leg's laid points and of the body's skin on the leg's side of `middle` at `level` (m),
    or None where either has nothing there."""
    laid = points[np.abs(points[:, 1] - level) < LEVEL_M, 0]
    body = skin[(np.abs(skin[:, 1] - level) < LEVEL_M) & (side * (skin[:, 0] - middle) > 0.0), 0]
    if not len(laid) or not len(body):
        return None
    return (laid.min() + laid.max()) / 2.0, (body.min() + body.max()) / 2.0


def over_legs(points, legs, crotch, skin):
    """A garment's legs (`leg_points`) moved across (x) to stand over the body's own legs: each leg by the median, over
    LEG_LEVELS levels of its lower half, of how far its laid middle stands from the middle of the skin on its side of
    the crotch there, in full from the top of that half down and going over to none at the crotch's lowest point (the
    crotch seam and all above it as GarmentCode lays them). A leg moved in stops short of the crotch's middle, each
    point no nearer it than CROTCH_GAP_M (or where it was laid, when nearer): GarmentCode's flat leg is twice as wide
    as her leg, and stood over it whole, the two legs' inseams were laid over each other at the middle. The lower
    half moves whole (its innermost point stopping there); a point above it moved past that is stopped alone."""
    points = np.array(points, dtype=float)
    if not len(crotch):
        return points
    skin = np.asarray(skin, dtype=float)
    lowest = crotch[np.argmin(points[crotch, 1])]
    top, middle = points[lowest, 1], points[lowest, 0]
    for side, mine in legs.items():
        hem = points[mine, 1].min()
        full = hem + (top - hem) / 2.0
        found = [leg_middles(points[mine], skin, side, middle, level)
                 for level in np.linspace(hem + LEVEL_M, full, LEG_LEVELS)]
        moves = [body - laid for laid, body in (pair for pair in found if pair is not None)]
        if not moves:
            continue
        across = float(np.median(moves))
        if side * across < 0.0:
            lower = mine[points[mine, 1] <= full]
            across = -side * min(-side * across, max(float(np.min(side * (points[lower, 0] - middle))) - CROTCH_GAP_M,
                                                     0.0))
        share = np.clip((top - points[mine, 1]) / (top - full), 0.0, 1.0)
        move = across * share
        room = np.maximum(side * (points[mine, 0] - middle) - CROTCH_GAP_M, 0.0)
        inward = side * move < 0.0
        move[inward] = -side * np.minimum(-side * move[inward], room[inward])
        points[mine, 0] += move
    return points


def laid_out(points, skin, reach, clear, inside):
    """A box mesh's points laid off the body (`inside`: points -> which stand inside it, a boolean per point): each
    point inside put `clear` (m) out through the skin point nearest it (along the way from the point to that skin
    point); one that leaves inside moved instead from where it was laid along whichever of the six axes reaches outside
    in the fewest steps of `clear` (at most OUT_ROUNDS, else left where it was laid); then every point moved `reach`
    (m) further from its nearest skin point (an outer garment's panels laid off the skin before it is sewn alone,
    drape.sewn_in_layers), but for one that move takes inside (in a fold of the skin), left where it was."""
    given = np.array(points, dtype=float)
    points = given.copy()
    skin = np.asarray(skin, dtype=float)
    tree = cKDTree(skin)
    inward = np.flatnonzero(inside(points))
    if len(inward):
        distance, nearest = tree.query(points[inward])
        out = (skin[nearest] - points[inward]) / np.maximum(distance, 1e-9)[:, None]
        points[inward] = skin[nearest] + out * clear
        inward = inward[inside(points[inward])]
    if len(inward):
        steps = np.arange(1, OUT_ROUNDS + 1) * clear
        tried = given[inward][:, None, None] + AXES[None, :, None] * steps[None, None, :, None]
        out = ~inside(tried.reshape(-1, 3)).reshape(tried.shape[:3])
        first = np.where(out.any(axis=2), out.argmax(axis=2), OUT_ROUNDS)
        axis = first.argmin(axis=1)
        found = first[np.arange(len(inward)), axis] < OUT_ROUNDS
        points[inward] = given[inward]
        points[inward[found]] = tried[np.flatnonzero(found), axis[found], first[found, axis[found]]]
    distance, nearest = tree.query(points)
    away = (points - skin[nearest]) / np.maximum(distance, 1e-9)[:, None]
    laid = skin[nearest] + away * (distance + max(reach, 0.0))[:, None]
    back = np.flatnonzero(inside(laid))
    laid[back] = points[back]
    return laid


def edge_lengths(points, faces):
    """Each triangle's edge lengths, in Newton's order: corner 0 to 1, 0 to 2, 1 to 2."""
    points = np.asarray(points, dtype=float)
    corners = points[np.asarray(faces)]
    return np.stack([np.linalg.norm(corners[:, 1] - corners[:, 0], axis=1),
                     np.linalg.norm(corners[:, 2] - corners[:, 0], axis=1),
                     np.linalg.norm(corners[:, 2] - corners[:, 1], axis=1)], axis=1)


def rest_shapes(lengths):
    """Triangles from their edge lengths (`edge_lengths`' order) as Newton's builder rests them (add_triangles): the
    corners 1 and 2 seen from corner 0 in the triangle's own frame (the first axis along corner 1), D = [[a, x],
    [0, y]]: (D's inverse per triangle, the areas)."""
    lengths = np.asarray(lengths, dtype=float)
    first, second, third = lengths[:, 0], lengths[:, 1], lengths[:, 2]
    along = (first ** 2 + second ** 2 - third ** 2) / (2.0 * first)
    across = np.sqrt(np.maximum(second ** 2 - along ** 2, 0.0))
    shapes = np.zeros((len(lengths), 2, 2))
    shapes[:, 0, 0], shapes[:, 0, 1], shapes[:, 1, 1] = first, along, across
    return np.linalg.inv(shapes), first * across / 2.0


def rest_lengths(laid, flat, share):
    """Each triangle's rest edge lengths `share` (0 to 1) of the way through its sewing: from the longer of its laid
    and its flat length, edge by edge (a seam's stretched triangle rests as laid, a squeezed one at its panel), to its
    flat panel's. Both ends and every share between keep the triangle inequality (a sum of valid triangles' lengths);
    a triangle whose start is thinner than SLIVER of its flat area starts flat."""
    laid, flat = np.asarray(laid, dtype=float), np.asarray(flat, dtype=float)
    start = np.maximum(laid, flat)
    _, start_area = rest_shapes(start)
    _, flat_area = rest_shapes(flat)
    thin = start_area < SLIVER * flat_area
    start[thin] = flat[thin]
    return start + (flat - start) * min(max(float(share), 0.0), 1.0)


def skin_normals(skin, faces):
    """Each skin point's outward normal (the body's triangles wind outward): the area-weighted sum of its triangles',
    unit length, as seated.normals (drape.py's Python has only this module)."""
    skin, faces = np.asarray(skin, dtype=float), np.asarray(faces)
    crossed = np.cross(skin[faces[:, 1]] - skin[faces[:, 0]], skin[faces[:, 2]] - skin[faces[:, 0]])
    found = np.zeros_like(skin)
    for corner in range(3):
        np.add.at(found, faces[:, corner], crossed)
    return found / np.maximum(np.linalg.norm(found, axis=1, keepdims=True), 1e-12)


def worn_skin(skin, faces, under, clear):
    """The skin as the cloth sewn on it wears it (`under`: that cloth's points): each skin point moved out along its
    normal to `clear` (m) past the furthest cloth whose nearest skin lies within UNDER_FOOT_M of it (each cloth point's
    height read along its nearest skin point's normal), but no further than half its `room_ahead`, a skin point with no
    cloth over it left. An outer layer is sewn
    alone on this skin (drape.sewn_in_layers), so it is sewn outside the cloth under it: sewn alone on the bare skin,
    a coat's sleeve backs crossed themselves where the arm meets the torso (a box mesh closes with no self contact), the
    shirt's under them crossed too, and moved out along the skin's normals from there (the arm's pointing into the
    torso, the torso's into the arm) the coat still crossed the shirt at 307 points 16 cm out (man_coat, 2026-11-26)."""
    skin = np.asarray(skin, dtype=float)
    normals = skin_normals(skin, faces)
    tree = cKDTree(skin)
    _, nearest = tree.query(under)
    height = np.sum((np.asarray(under, dtype=float) - skin[nearest]) * normals[nearest], axis=1)
    lift = np.zeros(len(skin))
    for index, near in enumerate(cKDTree(skin[nearest]).query_ball_point(skin, UNDER_FOOT_M)):
        if near:
            lift[index] = max(height[near].max() + clear, 0.0)
    lift = np.minimum(lift, room_ahead(skin, normals, 2.0 * lift) / 2.0)
    return skin + normals * lift[:, None]


def room_ahead(skin, normals, reach):
    """Each skin point's room along its normal (m): how far ahead of it the nearest skin facing it stands (a point
    within FACING_DEGREES of its normal whose own normal turns back towards it), looked for out to `reach` (m, one a
    point), infinite where none is. `worn_skin` lifts a point at most half its room, so skin that faces skin (an arm
    hanging against the torso, the thighs) meets in the middle rather than lifting each side through the other:
    lifted in full, man_coat's arm and torso stood inside each other's lifted skin under his shirt, and a coat point
    laid out of one into the other could not leave the two (3 left inside, 2026-11-26)."""
    room = np.full(len(skin), np.inf)
    ahead = np.flatnonzero(np.asarray(reach) > 0.0)
    slope = np.tan(np.radians(FACING_DEGREES))
    for index, near in zip(ahead, cKDTree(skin).query_ball_point(skin[ahead], np.asarray(reach)[ahead])):
        near = np.asarray(near, dtype=np.int64)
        way = skin[near] - skin[index]
        along = way @ normals[index]
        side = np.linalg.norm(way - along[:, None] * normals[index], axis=1)
        facing = (along > 0.0) & (side <= slope * along) & (normals[near] @ normals[index] < 0.0)
        if facing.any():
            room[index] = along[facing].min()
    return room


def top_ring(record, labels, scale):
    """A garment's held top ring in its box mesh, round in order: the points GarmentCode labels `labels` (its
    `lower_interface`) and the side seams' top points that close them into one ring, each with its edge's cut length
    to the next (m, `scale` m to the record's unit: the flat panel's, along the triangle that holds the edge). GarmentCode
    labels each band panel's top edge without its seam corners, so its front and back are two chains apart at the side
    seams, each closed by the point that joins its two ends along the shortest cut (the seam's top, not the point
    under it a diagonal away); held without those corners, woman_stair_modern's jeans' waistband had no held point for 16.5 cm at each
    side seam and its ends were pulled across the gap, up to 7 times their cut length (#225 round 8, 2026-11-25). A
    labelled top that is not one closed ring is refused."""
    held = set(np.unique(np.concatenate([record[f"label/{label}"] for label in labels])).tolist())
    box, faces, copies = np.asarray(record["box"]), np.asarray(record["faces"]), np.asarray(record["copies"])
    cut = {}
    for face in faces:
        for one, two in ((0, 1), (1, 2), (2, 0)):
            pair = tuple(sorted((int(box[face[one]]), int(box[face[two]]))))
            cut[pair] = float(np.linalg.norm(copies[face[one]] - copies[face[two]])) * scale
    neighbours = {}
    for one, two in cut:
        neighbours.setdefault(one, set()).add(two)
        neighbours.setdefault(two, set()).add(one)
    ring = lambda point: neighbours.get(point, set()) & held
    ends = {point for point in held if len(ring(point)) == 1}
    closing = {}
    for end in ends:
        for point in neighbours[end] - held:
            pair = tuple(sorted(neighbours[point] & ends))
            if len(pair) == 2:
                length = sum(cut[tuple(sorted((point, other)))] for other in pair)
                closing[pair] = min(closing.get(pair, (length, point)), (length, point))
    held |= {point for _, point in closing.values()}
    if any(len(ring(point)) != 2 for point in held):
        raise RuntimeError(f"a held top of {len(held)} points is not one closed ring")
    order = [min(held)]
    while len(order) < len(held):
        step = sorted(ring(order[-1]) - set(order))
        if not step:
            raise RuntimeError(f"a held top of {len(held)} points is more than one ring")
        order.append(step[0])
    order = np.asarray(order, dtype=np.int64)
    return order, np.array([cut[tuple(sorted((int(one), int(two))))] for one, two in zip(order, np.roll(order, -1))])


def level_hit(origin, towards, skin, faces):
    """Where the level way from `origin` along `towards` (unit, y 0) first meets the skin (Moller and Trumbore):
    (its triangle, its corners' weights, how far along), or None where it meets none."""
    corner = skin[faces[:, 0]]
    first, second = skin[faces[:, 1]] - corner, skin[faces[:, 2]] - corner
    across = np.cross(towards, second)
    determinant = np.sum(first * across, axis=1)
    usable = np.abs(determinant) > 1e-14
    inverse = 1.0 / np.where(usable, determinant, 1.0)
    offset = origin - corner
    one = np.sum(offset * across, axis=1) * inverse
    turned = np.cross(offset, first)
    two = (turned @ towards) * inverse
    along = np.sum(second * turned, axis=1) * inverse
    hit = usable & (one >= 0.0) & (two >= 0.0) & (one + two <= 1.0) & (along > 0.0)
    if not hit.any():
        return None
    found = np.flatnonzero(hit)[np.argmin(along[hit])]
    return found, np.array([1.0 - one[found] - two[found], one[found], two[found]]), float(along[found])


def worn_places(points, cut, skin, faces):
    """Where a waistband's held points (`points`, its box mesh's top ring as laid, round in order, `top_ring`) are
    worn: round the skin's ring at their level (where the level ways out from the ring's middle, its points' mean
    across x and z, first meet the skin, read every 360th of a turn), each as far round it as it is round the band's
    cut (`cut`: each point's edge length to the next), so the band is held round her evenly at the level its pattern
    cuts it for, as GarmentCode's drape attaches its `lower_interface` at the waist's level. The ring's turn round her
    is the mean of how far round each point stands where it was laid. (the skin triangle of each, its corners'
    weights). Carried to the skin point nearest them, the box's flat front and back panels, laid 7 to 15 cm off
    woman_stair's hips at one level, were worn on a line up to 6 cm higher at the back's sides (2026-11-25); each worn
    where its own level way to the middle met the skin, the flat panels' points crowded her front and back and left
    16.5 cm at each side seam, the band's ends there stretched up to 7 times their cut length (#225 round 8). A level
    way that meets no skin is refused."""
    points, skin, faces = np.asarray(points, dtype=float), np.asarray(skin, dtype=float), np.asarray(faces)
    middle = points.mean(axis=0)
    turns = np.linspace(0.0, 2.0 * np.pi, RING_WAYS, endpoint=False)
    ways = np.stack([np.cos(turns), np.zeros(RING_WAYS), np.sin(turns)], axis=1)
    reach = []
    for way in ways:
        found = level_hit(middle, way, skin, faces)
        if found is None:
            raise RuntimeError(f"the level way out from {np.round(middle, 3).tolist()} at {np.round(way, 3).tolist()} "
                               "meets no skin")
        reach.append(found[2])
    contour = middle + ways * np.asarray(reach)[:, None]
    round_at = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.roll(contour, -1, axis=0) - contour, axis=1))])
    whole = round_at[-1]
    laid_turn = np.mod(np.arctan2(points[:, 2] - middle[2], points[:, 0] - middle[0]), 2.0 * np.pi)
    laid_round = np.interp(laid_turn, np.append(turns, 2.0 * np.pi), round_at)
    cut = np.asarray(cut, dtype=float)
    share = np.concatenate([[0.0], np.cumsum(cut)[:-1]]) / cut.sum() * whole
    outline = points[:, [0, 2]] - middle[[0, 2]]
    if np.sum(outline[:, 0] * np.roll(outline[:, 1], -1) - np.roll(outline[:, 0], -1) * outline[:, 1]) < 0.0:
        share = -share  # the ring runs the other way round
    phase = np.angle(np.mean(np.exp(1j * 2.0 * np.pi * (laid_round - share) / whole))) / (2.0 * np.pi) * whole
    worn_turn = np.interp(np.mod(share + phase, whole), round_at, np.append(turns, 2.0 * np.pi))
    triangles, weights = np.zeros(len(points), dtype=np.int64), np.zeros((len(points), 3))
    for index, (point, turn) in enumerate(zip(points, worn_turn)):
        origin = np.array([middle[0], point[1], middle[2]])
        found = level_hit(origin, np.array([np.cos(turn), 0.0, np.sin(turn)]), skin, faces)
        if found is None:
            raise RuntimeError(f"a held point at {np.round(point, 3).tolist()} meets no skin on its level way")
        triangles[index], weights[index] = found[0], found[1]
    return triangles, weights


def edges_of(faces):
    """The mesh's edges, each once (point pairs, the lower first)."""
    found = np.sort(np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]]), axis=1)
    return np.unique(found, axis=0)


def through(points, edges, other, faces, edge_wise):
    """Which of the segments `edges` (on `points`) pass through which triangles `faces` (on `other`): (segment,
    triangle) index pairs. Candidates are the triangles near each segment (`edge_wise`: looked for round each
    segment, for long segments and small triangles; else round each triangle)."""
    middles, half = points[edges].mean(axis=1), np.linalg.norm(points[edges[:, 1]] - points[edges[:, 0]], axis=1) / 2.0
    centres = other[faces].mean(axis=1)
    sizes = np.linalg.norm(other[faces] - centres[:, None], axis=2).max(axis=1)
    if edge_wise:
        near = cKDTree(centres).query_ball_point(middles, half + sizes.max())
        segment = np.repeat(np.arange(len(edges)), [len(each) for each in near])
        triangle = np.fromiter((index for each in near for index in each), int, len(segment))
    else:
        near = cKDTree(middles).query_ball_point(centres, sizes + half.max())
        triangle = np.repeat(np.arange(len(faces)), [len(each) for each in near])
        segment = np.fromiter((index for each in near for index in each), int, len(triangle))
    start, along = points[edges[segment, 0]], points[edges[segment, 1]] - points[edges[segment, 0]]
    corner = other[faces[triangle, 0]]
    first, second = other[faces[triangle, 1]] - corner, other[faces[triangle, 2]] - corner
    across = np.cross(along, second)
    determinant = np.sum(first * across, axis=1)
    usable = np.abs(determinant) > 1e-14
    inverse = 1.0 / np.where(usable, determinant, 1.0)
    offset = start - corner
    one = np.sum(offset * across, axis=1) * inverse
    turned = np.cross(offset, first)
    two = np.sum(along * turned, axis=1) * inverse
    share = np.sum(second * turned, axis=1) * inverse
    hit = usable & (one >= 0.0) & (two >= 0.0) & (one + two <= 1.0) & (share >= 0.0) & (share <= 1.0)
    return segment[hit], triangle[hit]


def crossing_filters(points, triangles, edges):
    """The self contact pairs of a cloth that already crosses itself (`points`, its `triangles` and its contact
    `edges`, as point pairs, by number), left out of VBD's self contact as Newton's external filter maps: ({point:
    triangles}, {edge: edges}). Each edge through a triangle that shares no corner with it gives its two points against
    that triangle, the triangle's corners against the triangles on that edge, and the edge against the triangle's
    edges, both ways. VBD's self contact keeps a pair from passing through each other and so holds a pair that already
    has: woman_stair_modern's tee, its sleeve caps laid through its torso by GarmentCode's box mesh at both armholes,
    was held there while she walked, left 5 cm behind her body by walk frame 3 and blown up at frame 41 (2026-11-25);
    left out, it followed her."""
    triangles, edges = np.asarray(triangles), np.asarray(edges)
    every = edges_of(triangles)
    segment, triangle = through(np.asarray(points, dtype=float), every, points, triangles, edge_wise=True)
    apart = ~(every[segment][:, :, None] == triangles[triangle][:, None, :]).any(axis=(1, 2))
    segment, triangle = segment[apart], triangle[apart]
    numbered = {tuple(sorted(pair)): number for number, pair in enumerate(edges.tolist())}
    beside = {}
    for number, corners in enumerate(triangles.tolist()):
        for corner in range(3):
            beside.setdefault(tuple(sorted((corners[corner], corners[(corner + 1) % 3]))), []).append(number)
    points_to, edges_to = {}, {}
    for crossing, crossed in zip(every[segment].tolist(), triangle.tolist()):
        corners = triangles[crossed].tolist()
        for point in crossing:
            points_to.setdefault(int(point), set()).add(int(crossed))
        for point in corners:
            points_to.setdefault(int(point), set()).update(beside[tuple(sorted(crossing))])
        mine = numbered.get(tuple(sorted(crossing)))
        theirs = [numbered.get(tuple(sorted((corners[corner], corners[(corner + 1) % 3])))) for corner in range(3)]
        for other in theirs:
            if mine is not None and other is not None:
                edges_to.setdefault(mine, set()).add(other)
                edges_to.setdefault(other, set()).add(mine)
    return points_to, edges_to


def crossed_cloth(points, triangles):
    """Which points of a cloth (`points`, its `triangles`) stand where it crosses itself: both ends of each edge through
    one of its own triangles that shares no corner with it, and that triangle's corners (the cloth `crossing_filters`
    leaves out of self contact)."""
    points, triangles = np.asarray(points, dtype=float), np.asarray(triangles)
    every = edges_of(triangles)
    segment, triangle = through(points, every, points, triangles, edge_wise=True)
    apart = ~(every[segment][:, :, None] == triangles[triangle][:, None, :]).any(axis=(1, 2))
    found = np.zeros(len(points), dtype=bool)
    found[every[segment[apart]].ravel()] = True
    found[triangles[triangle[apart]].ravel()] = True
    return found


def crossings(points, faces, under_points, under_faces):
    """Where a cloth (`points`, `faces`) and the cloth under it pass through each other: ((edge, under triangle) pairs
    of the cloth's edges through the under cloth's triangles, (under edge, triangle) pairs the other way), each pair's
    points on the cloth and on the under cloth (as two lists of point arrays, a pair's to a row)."""
    edges, under_edges = edges_of(faces), edges_of(under_faces)
    segment, triangle = through(points, edges, under_points, under_faces, edge_wise=True)
    under_segment, pierced = through(under_points, under_edges, points, faces, edge_wise=False)
    pairs = (list(zip(segment.tolist(), triangle.tolist())), list(zip(under_segment.tolist(), pierced.tolist())))
    mine = (edges[segment], faces[pierced])
    theirs = (under_faces[triangle], under_edges[under_segment])
    return pairs, mine, theirs


def kept_clear(given, laid, faces, under_points, under_faces):
    """An outer garment's points as `laid` off its points as sewn alone (`given`), each point whose cloth the laying
    takes through the cloth under it (an edge-triangle pair either way that `given` did not have) put back where it was
    sewn, until none is: man_coat's coat, sewn alone outside his shirt where his shirt and coat do not cross themselves,
    was moved out along the skin's normals and the move took it through the shirt at 176 more pairs (100 as sewn),
    the arm's and the torso's normals pointing into each other in the armpit (2026-11-26); put back, 79 of its 629
    moved points, it crossed at the 100 it was sewn with."""
    given, laid = np.asarray(given, dtype=float), np.array(laid, dtype=float)
    before = [set(pairs) for pairs in crossings(given, faces, under_points, under_faces)[0]]
    while True:
        pairs, mine, _ = crossings(laid, faces, under_points, under_faces)
        new = [np.array([pair not in seen for pair in found], dtype=bool) for found, seen in zip(pairs, before)]
        back = np.unique(np.concatenate([points[fresh].ravel() for points, fresh in zip(mine, new)]))
        back = back[np.any(laid[back] != given[back], axis=1)]
        if not len(back):
            return laid
        laid[back] = given[back]


def held_crossings(points, faces, under_points, under_faces, crossed, under_crossed):
    """The points of a cloth whose crossings with the cloth under it VBD's self contact would hold (`crossings`): a
    pair with a point at cloth that crosses itself (`crossed`, `under_crossed`: `crossed_cloth` of each as sewn) is
    left out, as `crossing_filters` leaves it out of self contact. A sleeve sewn through its own torso at the armpit
    (GarmentCode's box mesh lays the sleeve caps through the torso panels: man_coat's shirt at 257 points, his coat at
    444) takes the cloth over or under it through with it: of the 267 points his coat still crossed his shirt at 16 cm
    out, 260 lay within 5 cm of where the coat crossed itself, and moving them further out only crossed more
    (2026-11-26)."""
    _, mine, theirs = crossings(points, faces, under_points, under_faces)
    held = [~(crossed[own].any(axis=1) | under_crossed[other].any(axis=1)) for own, other in zip(mine, theirs)]
    return np.unique(np.concatenate([own[keep].ravel() for own, keep in zip(mine, held)]))
