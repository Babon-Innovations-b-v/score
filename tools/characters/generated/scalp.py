"""The scalp under the removed hair (`scalp_patch`): a smooth skull-shaped surface closing the hole the hair's triangles
leave, joined to the skin round it without a ridge. Where the hair hung behind the neck the model has no neck at all:
a direction that meets nothing there (down to NECK_LOWEST) is the hole too, and under it `neck_closed` closes the neck:
an upright elliptic tube as wide as the neck's own skin (between NECK_BAND_M under the eyes), its back meeting the
scalp's foot (`nape_of`), from NECK_BELOW_M under that band up into the scalp; its back half, and all round wherever
the hair was taken off the skin (the jaw's corner, behind the ear), running on under the skin's edge (round 13,
2026-11-28: the back half alone left the jaw's corner open, its inside showing as a dark notch in three quarters).

The head is read from its own middle (`origin`: the eyes' height plus ORIGIN_OVER_EYES_M, over the cap's middle) along
DIRECTIONS (an icosphere's corners): along each, the first skin and the first hair met (rays against the model). A
direction whose hair comes before any skin is the hole; RING steps round it into the skin are the seam, where the
scalp runs TUCK_M under the skin (no gap at the edge, no step over it). Over the hole the scalp's distance from the
origin is an ellipsoid fitted to the skin at the seam (the skull's shape) plus the seam's own difference from it spread
over the hole smoothly (harmonic, so the scalp meets the skin at the skin's own height all round), kept CLEAR_M inside
the hair's shell; then smoothed SMOOTH times with the seam held. A seam direction whose skin stands more than
EAR_OUT of the ellipsoid off it (an ear) is not held to its skin (nor fitted), unless it lies EAR_LOWEST_M under the
eyes within JAW_OUT (the jaw's corner: held, not fitted). Roots grow only on its `rooted` points: under the
shell's hair, or where nothing was met behind the head's middle (BEHIND: the neck the model never had); a
direction meeting nothing in front is a bust's open cut under the chin, never scalp.

The model's skin round the hole is then laid onto the scalp (`laid`): its points within LAY_M of the removed hair
moved along their ray from the head's middle to the scalp's height (LIFT_M over it), all the way at the hole's edge
and none LAY_M off it, so the skin meets the scalp with no edge standing (round 1's hairline stood as a torn lip of
the shell's foot over the scalp, its gaps showing the hollow head, 2026-11-26); a point further than LAY_MOST_M off
the scalp (an ear) stays.
"""
import numpy as np
import trimesh
from scipy.sparse import coo_matrix, diags
from scipy.sparse.linalg import spsolve
from scipy.spatial import cKDTree

ORIGIN_OVER_EYES_M = 0.02
SUBDIVISIONS = 6  # the icosphere's: 40 962 directions, some 1.5 mm apart at a skull's distance
REACH_M = 0.2  # a ray reads no farther than this
RING = 3
TUCK_M = 0.0008
CLEAR_M = 0.002
EAR_OUT = 0.12
EAR_LOWEST_M = 0.05  # under this far under the eyes a seam's skin standing out (up to JAW_OUT) is the jaw's corner,
# held all the same though never fitted (round 13, 2026-11-28: not held, the scalp lay 2 to 3 cm inside the jaw's corner
# and showed as a dark notch there)
JAW_OUT = 0.25  # further out under the ear is a shoulder or a collar, never held
SMOOTH = 20
SMOOTH_SHARE = 0.5
NECK_LOWEST = -0.87  # a direction meeting nothing (where the hair hung over a neck the model never had) is the
# hole too, down to 60 degrees under level; under it the neck's back (`neck_closed`) closes it
NECK_BAND_M = (0.13, 0.17)  # the neck's skin read this far under the eyes
NECK_DEPTH = 0.9  # the neck's depth front to back, a share of its width
NECK_BELOW_M = 0.03  # the tube reaches this far under the band (into the collar)
NECK_SPREAD = (10, 90)  # the neck's width between these percentiles of its skin's (the jaw's edge is not the neck)
NECK_TUCK = 0.9  # the tube this share of the neck skin's width, so its sides stay behind the skin
NECK_AROUND, NECK_UP = 96, 80
NAPE_COS = 0.85  # within some 30 degrees of straight back, where nothing is met, the tube is the ellipse meeting the
# nape (held: spread from the sides alone, the jaw's reach pushed the back 3 cm out past the scalp's foot)
JAW_KEPT_M = 0.07  # from this far under the eyes down the tube is kept all round, under the skin (round 14, 2026-11-28:
# kept in front only where the hair step's model meets nothing, it was missing under the stairwell woman's jaw's
# corner, where the swap gives the neck to the body and its own old hair hangs: the tube's far side showed through as
# a dark red line; under the swap's cut the drawing takes it off)
NECK_REACH = 1.6  # a skin or scalp met this far out (a share of the tube's distance) is what the neck runs under;
# further (a collar, a shoulder) is not
# the scalp's foot behind the neck: its points behind the head this near the middle, in their lowest band; the tube's
# back meets it (round 4, 2026-11-27: a tube 0.9 of the neck's width deep stood 5 cm inside an older woman's collar and
# the scalp's foot, and showed between her bob's ends and the collar as a dark strip)
NAPE = {"behind": 0.5, "half_width_m": 0.03, "band_m": 0.01}
OPEN_NECK = 50
HEAD_M = 0.25  # only the model's triangles this near the origin are read
BEHIND = 0.2  # a direction meeting nothing is the neck's back only this far behind level (its z, unit)
LAY_M = 0.006
LIFT_M = 0.0003
LAY_MOST_M = 0.012
LAY_DEGREES = 1.5  # a point is laid only where the scalp has a direction this near its own


def origin(frame):
    """The point the head is read from."""
    return np.array([frame["middle_x"], frame["eyes_middle"][1] + ORIGIN_OVER_EYES_M, frame["centre"][2]])


def first_hit(points, faces, start, directions):
    """Each direction's distance from `start` to the first of the triangles it meets (inf when none within
    REACH_M)."""
    mesh = trimesh.Trimesh(points, faces, process=False)
    found = np.full(len(directions), np.inf)
    where, ray, _ = mesh.ray.intersects_location(np.repeat(start[None], len(directions), axis=0), directions,
                                                multiple_hits=True)
    distance = np.linalg.norm(where - start, axis=1)
    np.minimum.at(found, ray, distance)
    found[found > REACH_M] = np.inf
    return found


def sphere_neighbours(sphere):
    """The icosphere's corners' neighbours as a sparse matrix (1 per edge)."""
    edges = np.asarray(sphere.edges_unique)
    count = len(sphere.vertices)
    ones = np.ones(len(edges) * 2)
    return coo_matrix((ones, (np.r_[edges[:, 0], edges[:, 1]], np.r_[edges[:, 1], edges[:, 0]])),
                      shape=(count, count)).tocsr()


def grown_ring(start, neighbours, steps):
    """The corners within `steps` edges of the `start` corners (a boolean mask)."""
    reached = start.copy()
    for _ in range(steps):
        reached = reached | (neighbours @ reached.astype(float) > 0)
    return reached


def ellipsoid_fit(directions, distances):
    """An axis-aligned ellipsoid round the origin through the points (least squares on 1/r^2 = sum d_i^2 / a_i^2, its
    height's axis held near the mean of the other two, which the seam alone hardly settles): the three 1/a_i^2."""
    rows = directions ** 2
    wanted = 1.0 / distances ** 2
    weight = 0.3 * np.sqrt(len(rows))
    rows = np.vstack([rows, weight * np.array([[-0.5, 1.0, -0.5]])])
    wanted = np.r_[wanted, 0.0]
    return np.linalg.lstsq(rows, wanted, rcond=None)[0]


def ellipsoid_at(inverse_squares, directions):
    """The fitted ellipsoid's distance from the origin along each direction."""
    return 1.0 / np.sqrt(np.maximum((directions ** 2) @ inverse_squares, 1e-6))


def harmonic(values, known, neighbours):
    """`values` spread smoothly (harmonic over the corners' graph) from the `known` corners to the rest; a corner
    with no known corner reachable keeps 0 (a weak pull to 0 holds the system)."""
    unknown = np.flatnonzero(~known)
    inner = neighbours[unknown][:, unknown]
    degree = np.asarray(neighbours[unknown].sum(axis=1)).ravel()
    system = diags(degree + 1e-6) - inner
    right = neighbours[unknown][:, np.flatnonzero(known)] @ values[known]
    result = values.copy()
    result[unknown] = spsolve(system.tocsc(), right)
    return result


def smoothed(distance, held, neighbours, ceiling):
    """The distances averaged with their neighbours SMOOTH times, the `held` corners kept, never past `ceiling`."""
    degree = np.maximum(np.asarray(neighbours.sum(axis=1)).ravel(), 1.0)
    for _ in range(SMOOTH):
        average = (neighbours @ distance) / degree
        distance = np.where(held, distance, np.minimum(distance + SMOOTH_SHARE * (average - distance), ceiling))
    return distance


def scalp_patch(points, faces, hair, frame):
    """The scalp: {points, triangles, depth: each point's distance into the hole from the seam (m), hole: whether
    each point is over the hole (not the seam's tuck), open_neck: whether the hair hung over a neck the model never
    had (directions under level that meet nothing, more than OPEN_NECK of them)}. `hair` labels the model's
    triangles."""
    start = origin(frame)
    near = np.linalg.norm(points[faces].mean(axis=1) - start, axis=1) < HEAD_M
    sphere = trimesh.creation.icosphere(subdivisions=SUBDIVISIONS)
    directions = np.asarray(sphere.vertices)
    skin_at = first_hit(points, faces[near & ~hair], start, directions)
    hair_at = first_hit(points, faces[near & hair], start, directions)
    neighbours = sphere_neighbours(sphere)
    nothing = ~np.isfinite(hair_at) & ~np.isfinite(skin_at)
    hole = (hair_at < skin_at) | (nothing & (directions[:, 1] >= NECK_LOWEST))
    seam = grown_ring(hole, neighbours, RING) & ~hole & np.isfinite(skin_at)
    fit = ellipsoid_fit(directions[seam], skin_at[seam])
    skull = ellipsoid_at(fit, directions)
    off = np.abs(skin_at - skull) / skull
    fitted = seam & (off < EAR_OUT)
    skin_height = start[1] + directions[:, 1] * np.where(np.isfinite(skin_at), skin_at, 0.0)
    held = fitted | (seam & (skin_height < frame["eyes_middle"][1] - EAR_LOWEST_M) & (off < JAW_OUT))
    fit = ellipsoid_fit(directions[fitted], skin_at[fitted])
    skull = ellipsoid_at(fit, directions)
    difference = np.where(held, skin_at - TUCK_M - skull, 0.0)
    shaped = skull + harmonic(difference, held, neighbours)
    ceiling = np.where(np.isfinite(hair_at), hair_at - CLEAR_M, np.inf)
    distance = smoothed(np.minimum(shaped, ceiling), held, neighbours, ceiling)
    used = hole | held
    kept_faces = np.asarray(sphere.faces)[used[np.asarray(sphere.faces)].all(axis=1)]
    corners = np.unique(kept_faces)
    renumber = np.full(len(directions), -1)
    renumber[corners] = np.arange(len(corners))
    placed = start + directions[corners] * distance[corners, None]
    seam_points = start + directions[held] * distance[held, None]
    depth = cKDTree(seam_points).query(placed)[0] * hole[corners]
    open_neck = int((nothing & (directions[:, 1] < 0.0)).sum()) > OPEN_NECK
    rooted = (hair_at < skin_at) | (nothing & (directions[:, 1] >= NECK_LOWEST) & (directions[:, 2] < BEHIND))
    return {"points": placed, "triangles": renumber[kept_faces], "depth": depth, "hole": hole[corners],
            "rooted": rooted[corners], "open_neck": open_neck, "directions": directions[corners],
            "distance": distance[corners]}


def laid(points, faces, removed, patch, frame):
    """The model's points with its skin round the `removed` hair laid onto the scalp (see the docstring)."""
    start = origin(frame)
    edge = points[np.unique(faces[removed])]
    kept = np.unique(faces[~removed])
    near = cKDTree(edge).query(points[kept], distance_upper_bound=LAY_M, workers=-1)[0]
    moving = kept[near < LAY_M]
    away = points[moving] - start
    distance = np.linalg.norm(away, axis=1)
    ways = away / np.maximum(distance, 1e-9)[:, None]
    apart, nearest = cKDTree(patch["directions"]).query(ways, k=3, workers=-1)
    weights = 1.0 / np.maximum(apart, 1e-6)
    scalp_at = (patch["distance"][nearest] * weights).sum(axis=1) / weights.sum(axis=1) + LIFT_M
    share = 1.0 - near[near < LAY_M] / LAY_M
    share = share * share * (3.0 - 2.0 * share)
    usable = (apart[:, 0] < np.radians(LAY_DEGREES)) & (np.abs(distance - scalp_at) < LAY_MOST_M)
    moved = points.copy()
    moved[moving] = start + ways * (distance + np.where(usable, share, 0.0) * (scalp_at - distance))[:, None]
    return moved


def nape_of(patch, frame):
    """How far back (z) the scalp's foot lies behind the neck: the median of its hole's points behind the head
    (direction z under -NAPE["behind"]) within NAPE["half_width_m"] of the middle, in their lowest NAPE["band_m"]."""
    places = patch["points"][patch["hole"] & (patch["directions"][:, 2] < -NAPE["behind"])
                             & (np.abs(patch["points"][:, 0] - frame["middle_x"]) < NAPE["half_width_m"])]
    return float(np.median(places[places[:, 1] < places[:, 1].min() + NAPE["band_m"], 2]))


def neck_closed(points, faces, hair, colours_skin_like, frame, patch):
    """The neck closed where the hair hung over it: (points, triangles). `colours_skin_like` marks the model's skin
    triangles. An upright elliptic tube fitted to the neck's skin (its width, its front), its depth NECK_DEPTH of its
    width or, where the scalp's foot lies further back, deep enough that its back meets it (TUCK_M inside; `nape_of`),
    read all round from its axis (`neck_reach`): where the model's skin or the scalp is met within NECK_REACH of the
    tube it runs TUCK_M under it, and the difference spreads over the rest (harmonic, as the scalp's; none within
    NAPE_COS of straight back where nothing is met), never past the hair less CLEAR_M. Kept: the back half, every
    place nothing is met (the jaw's corner, behind the ear) and RING places round them under the skin, so the skin's
    edge meets it where the hair was taken off the jaw, and all round from JAW_KEPT_M under the eyes down (never past
    anything met, less TUCK_M), so whichever side of the neck the swap gives the head, the tube lies under its edge."""
    middles = points[faces].mean(axis=1)
    eyes = frame["eyes_middle"]
    band = (~hair & colours_skin_like & (middles[:, 1] < eyes[1] - NECK_BAND_M[0])
            & (middles[:, 1] > eyes[1] - NECK_BAND_M[1]) & (np.abs(middles[:, 0] - frame["middle_x"]) < 0.08))
    neck = middles[band]
    spread = np.percentile(neck[:, 0], NECK_SPREAD[1]) - np.percentile(neck[:, 0], NECK_SPREAD[0])
    half_width = NECK_TUCK * 0.5 * float(spread)
    front = float(np.percentile(neck[:, 2], 90))
    half_depth = max(NECK_DEPTH * half_width, (front - nape_of(patch, frame) - TUCK_M) / 2.0)
    middle = np.array([frame["middle_x"], front - half_depth])
    low, high = eyes[1] - NECK_BAND_M[1] - NECK_BELOW_M, origin(frame)[1]
    angle, height = np.meshgrid(np.linspace(0.0, 2.0 * np.pi, NECK_AROUND, endpoint=False),
                                np.linspace(low, high, NECK_UP), indexing="ij")
    ellipse = np.stack([half_width * np.sin(angle), half_depth * np.cos(angle)], axis=-1).reshape(-1, 2)
    tube = np.linalg.norm(ellipse, axis=1)
    ways = np.stack([ellipse[:, 0] / tube, np.zeros(len(tube)), ellipse[:, 1] / tube], axis=1)
    axis = np.stack([np.full(len(tube), middle[0]), height.ravel(), np.full(len(tube), middle[1])], axis=1)
    radius, kept = neck_reach(points, faces, hair, patch, axis, ways, tube, angle.ravel(),
                              height.ravel() < eyes[1] - JAW_KEPT_M)
    placed = axis + ways * radius[:, None]
    corner = np.arange(NECK_AROUND * NECK_UP).reshape(NECK_AROUND, NECK_UP)
    quads = np.stack([corner, np.roll(corner, -1, axis=0)], axis=-1)
    quads = np.stack([quads[:, :-1, 0], quads[:, :-1, 1], quads[:, 1:, 1], quads[:, 1:, 0]], axis=-1).reshape(-1, 4)
    quads = quads[kept[quads].all(axis=1)]
    used = np.unique(quads)
    renumber = np.full(len(placed), -1)
    renumber[used] = np.arange(len(used))
    quads = renumber[quads]
    return placed[used], np.vstack([quads[:, [0, 1, 2]], quads[:, [0, 2, 3]]])


def neck_grid():
    """The neck tube's places' neighbours (NECK_AROUND round, wrapping, by NECK_UP high) as a sparse matrix."""
    corner = np.arange(NECK_AROUND * NECK_UP).reshape(NECK_AROUND, NECK_UP)
    pairs = np.vstack([np.stack([corner.ravel(), np.roll(corner, -1, axis=0).ravel()], axis=1),
                       np.stack([corner[:, :-1].ravel(), corner[:, 1:].ravel()], axis=1)])
    count = corner.size
    ones = np.ones(len(pairs) * 2)
    return coo_matrix((ones, (np.r_[pairs[:, 0], pairs[:, 1]], np.r_[pairs[:, 1], pairs[:, 0]])),
                      shape=(count, count)).tocsr()


def met_along(points, faces, starts, ways):
    """Each ray's distance from its start to the first of the triangles it meets (inf when none)."""
    met = np.full(len(starts), np.inf)
    if len(faces):
        where, ray, _ = trimesh.Trimesh(points, faces, process=False).ray.intersects_location(starts, ways,
                                                                                                 multiple_hits=True)
        np.minimum.at(met, ray, np.linalg.norm(where - starts[ray], axis=1))
    return met


def neck_reach(points, faces, hair, patch, axis, ways, tube, angle, under_jaw):
    """Each neck place's distance from its axis point along its way (level, out from the axis) and whether it is kept
    (see `neck_closed`); `tube` is the ellipse's distance there, `angle` its angle from the front, `under_jaw` whether
    it lies JAW_KEPT_M or more under the eyes."""
    met = np.minimum(met_along(points, faces[~hair], axis, ways),
                     met_along(patch["points"], patch["triangles"], axis, ways))
    known = met < NECK_REACH * tube
    covered = np.isfinite(met)
    nape = ~known & (np.cos(angle) < -NAPE_COS)
    neighbours = neck_grid()
    difference = np.where(known, met - TUCK_M - tube, 0.0)
    radius = np.minimum(np.minimum(tube + harmonic(difference, known | nape, neighbours), met - TUCK_M),
                        met_along(points, faces[hair], axis, ways) - CLEAR_M)
    kept = (np.cos(angle) <= 0.0) | ~covered | grown_ring(~covered, neighbours, RING) | under_jaw
    return np.maximum(radius, 0.0), kept
