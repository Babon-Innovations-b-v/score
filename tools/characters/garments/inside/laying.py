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


def worn_places(points, skin, faces):
    """Where a waistband's held points (`points`, its box mesh's top ring as laid) are worn: each where the level way
    from it to the ring's middle (its points' mean, across x and z) first meets the skin, so the band's top is worn at
    the level its pattern cuts it for, as GarmentCode's drape attaches its `lower_interface` at the waist's level: (the
    skin triangle of each, its corners' weights). Carried to the skin point nearest them instead, the box's flat front
    and back panels, laid 7 to 15 cm off woman_stair's hips at one level, were worn on a line up to 6 cm higher at the
    back's sides (the skin nearest them up on the waist over her seat), longer than the band is cut; the side seams
    were held 6 to 15 cm open, the band stood 3.6 cm off her hips there, and the tee laid over it crossed it however
    far out (2026-11-25). A point whose level way meets no skin is refused."""
    points, skin, faces = np.asarray(points, dtype=float), np.asarray(skin, dtype=float), np.asarray(faces)
    middle = points.mean(axis=0)
    corner = skin[faces[:, 0]]
    first, second = skin[faces[:, 1]] - corner, skin[faces[:, 2]] - corner
    triangles, weights = np.zeros(len(points), dtype=np.int64), np.zeros((len(points), 3))
    for index, point in enumerate(points):
        towards = np.array([middle[0] - point[0], 0.0, middle[2] - point[2]])
        towards /= max(np.linalg.norm(towards), 1e-12)
        across = np.cross(towards, second)
        determinant = np.sum(first * across, axis=1)
        usable = np.abs(determinant) > 1e-14
        inverse = 1.0 / np.where(usable, determinant, 1.0)
        offset = point - corner
        one = np.sum(offset * across, axis=1) * inverse
        turned = np.cross(offset, first)
        two = (turned @ towards) * inverse
        along = np.sum(second * turned, axis=1) * inverse
        hit = usable & (one >= 0.0) & (two >= 0.0) & (one + two <= 1.0) & (along > 0.0)
        if not hit.any():
            raise RuntimeError(f"a held point at {np.round(point, 3).tolist()} meets no skin on its level way in")
        found = np.flatnonzero(hit)[np.argmin(along[hit])]
        triangles[index] = found
        weights[index] = [1.0 - one[found] - two[found], one[found], two[found]]
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
