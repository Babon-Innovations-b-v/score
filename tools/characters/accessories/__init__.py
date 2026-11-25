"""What a dressed person of the people line wears beside its sewn clothes (#228, under PRD #223): shoes on its feet and
a belt on its skirt's waistband, each built on the person it is worn by and finished with score_lib surfaces.

Shoes are a library model when the outfit names one (`shoes.model`, its finish `shoes.finish`): `shoe_model.py`
fits it to each foot (scaled to the foot, set on it where it stands flattest, the upper stretched a little where the
foot presses, carried by the foot's skin weights) and checks the foot inside it every clip frame (owner, 2026-11-25:
the made slip-on read as no real shoe; the library's first is an adopted knit runner with laces, eyelets, a heel tab
and a foam sole). The library holds no belt model (its belts are conveyor and engine belts), so a belt, and a shoe
that names no model, is fitted from the body as the garments are sized from it:

- A shoe with no model is made on a last of the body's own foot (`last`: the convex hull of the foot's cross-sections
  along it, so the toes are boxed), out along the last's normals by the upper's thickness and, where it faces down, a
  sole SOLE_M deep, cut at its collar (the ankle joint's height at the heel, THROAT_M lower over the toes' base). Each
  point is carried by the skin weights of the foot points nearest it, so it moves with the foot and bends at the toes as
  the clip plays (the clips rig's joints every frame, `worlds`); where the foot would still come out of it at the bind
  or on the clip, it is pushed out (`cleared`). The person is lifted so the lower sole's lowest over the clip stands on
  the floor, as the clip's bare feet do. In the outfit's USD each shoe's upper and sole are UsdPhysics colliders (a
  convex hull each) for Newton.
- A belt is a band BELT_M wide just under the skirt's waistband top (its `lower_interface` label), round whatever
  is there each frame (the garments' cloth and the body) but the garments the outfit's belt is `covered by` (a coat
  over a belted shirt), CLEAR_M off it, with a buckle at the front; its frame turns with the hips. It is laid after the drape and does not hold the cloth under it (the drape's own belt is #228's
  next slice).

`measured` reads the fit over the clip and `faults` names what is past its limit (a sole through the floor, the
foot out through its shoe, a belt off its waistband); the garments run fails on a fault, after its pictures.
"""
import pathlib

import numpy as np

UPPER_M = 0.004  # the upper's leather off the skin
SOLE_M = 0.012  # the sole under the foot's bottom
SOLE_FROM = 0.2  # a skin normal this far down starts the sole; as far from straight down, it is all sole
THROAT_M = 0.010  # how much lower the collar sits over the toes' base than at the heel
COLLAR_REACH_M = 0.02  # the skin taken over the collar, for the collar's cut to run through
SOLE_LINE_M = 0.03  # the sole's top edge over the shoe's lowest at the bind
SMOOTH_ROUNDS = 4
LAST_STEP_M = 0.006  # the last's cross-sections apart along the foot
RING = 40  # the last's points round a cross-section
BLEND_NEAREST = 4
SAMPLE_SPLITS = 4  # the skin points a shoe point is carried by
TOE_SPRING_M = 0.008
CLEAR_ROUNDS = 6
CLEAR_EVERY = 3
CLEAR_STEP_M = 0.001
COVERED_UNDER_M = 0.005  # the skin this far under the collar is covered by the shoe
BELT_M = 0.03  # the belt's width
BELT_THICK_M = 0.004
CLEAR_M = 0.002  # the belt's inside off what it is worn round
UNDER_TOP_M = 0.003  # the belt's top under the waistband's top
REACH_M = 0.04  # what the belt goes round: within this of the waistband's widest (the hanging hands are not)
BINS = 72  # the belt's points round the waist
BUCKLE = {"wide": 0.045, "tall_over": 0.008, "bar": 0.006, "deep": 0.004}  # m
TEXTURE_METRES = 0.25  # what a library surface's texture covers once (st 0..1) on an accessory
FLOOR_LIMIT_M = 0.002  # a sole this far under the floor is through it
HOVER_LIMIT_M = 0.005  # a sole never nearer the floor than this over the whole clip never stands on it
FOOT_LIMIT_M = 0.0  # a foot point this far out past its shoe's surface is out through it
BELT_LIMIT_M = 0.015  # a belt's top this far from the waistband's top is off it
# A belt's inside this far off the skin under it holds the cloth out, not in: the drape holds the cloth under a belt
# within 15 mm of the skin (garments.BELT_LAYERS: two layers, their gaps and contact margins), with 5 mm of a fold.
HOLD_LIMIT_M = 0.02
COVER_LIMIT_M = 0.0  # cloth worn over a belt this far inside its outside has the belt out through it


def vertex_normals(points, faces):
    """Area-weighted outward normals of a triangle surface's points."""
    corners = points[faces]
    crossed = np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0])
    found = np.zeros_like(points)
    for corner in range(3):
        np.add.at(found, faces[:, corner], crossed)
    return found / np.maximum(np.linalg.norm(found, axis=1, keepdims=True), 1e-12)


def joint_place(body, name):
    names = [str(each) for each in body["names"]]
    return np.asarray(body["joints"])[names.index(name)][:3, 3]


def collar_height(body, side, points):
    """The collar's height over each of `points`: the ankle's at the heel, THROAT_M lower from the toes' base on."""
    ankle, toes = joint_place(body, f"{side}Foot"), joint_place(body, f"{side}ToeBase")
    forward = (toes - ankle) * np.array([1.0, 0.0, 1.0])
    reach = np.linalg.norm(forward)
    along = np.clip((points - ankle) @ (forward / reach) / reach, 0.0, 1.0)
    return ankle[1] - THROAT_M * along


def cut(made, blend, faces, value):
    """The surface cut where `value` (one a point) crosses nought: each crossed edge gets a point at its crossing
    (its place and its blend of body points interpolated), each crossed triangle is split. (made, blend, faces, the
    faces' flags of lying where `value` is under nought)."""
    made, blend, crossing = list(made), list(blend), {}
    value = list(value)

    def at(first, second):
        key = (min(first, second), max(first, second))
        if key not in crossing:
            share = value[key[0]] / (value[key[0]] - value[key[1]])
            made.append(made[key[0]] * (1.0 - share) + made[key[1]] * share)
            blend.append(blend[key[0]] * (1.0 - share) + blend[key[1]] * share)
            value.append(0.0)
            crossing[key] = len(made) - 1
        return crossing[key]

    found, under = [], []
    for face in np.asarray(faces):
        below = [value[corner] < 0.0 for corner in face]
        if all(below) or not any(below):
            found.append(list(face))
            under.append(all(below))
            continue
        alone = next(rank for rank in range(3) if below.count(below[rank]) == 1)
        first, second, third = face[alone], face[(alone + 1) % 3], face[(alone + 2) % 3]
        towards, back = at(first, second), at(third, first)
        found += [[first, towards, back], [towards, second, third], [towards, third, back]]
        under += [below[alone], not below[alone], not below[alone]]
    return np.asarray(made), np.asarray(blend), np.asarray(found), np.asarray(under)


def hull_ring(flat, angles):
    """The convex hull of flat (2-d) points met by rays from its middle at `angles`: (middle, ring points)."""
    from scipy.spatial import ConvexHull
    hull = ConvexHull(flat)
    middle = flat[hull.vertices].mean(axis=0)
    direction = np.stack([np.cos(angles), np.sin(angles)], axis=1)
    normals, offsets = hull.equations[:, :2], hull.equations[:, 2]
    facing = direction @ normals.T
    along = -(middle @ normals.T + offsets)[None] / np.where(facing > 1e-9, facing, np.nan)
    return middle, middle + direction * np.nanmin(along, axis=1)[:, None]


def last(body, side, skin):
    """The last a shoe is made on, round `skin` (the foot's points): the convex hull of the foot's cross-section
    every LAST_STEP_M along the foot (across it and up), RING points round each, rings joined, the heel's and the
    toes' ends closed half a step past them. The hull boxes the toes as a toe box does: made off the foot's own
    surface, the shoe showed each toe and the offset surfaces of neighbouring toes crossed (2026-11-24). (points,
    faces wound outward)."""
    ankle, end = joint_place(body, f"{side}Foot"), joint_place(body, f"{side}ToeEnd")
    forward = (end - ankle) * np.array([1.0, 0.0, 1.0])
    forward /= np.linalg.norm(forward)
    up = np.array([0.0, 1.0, 0.0])
    across = np.cross(up, forward)
    along = skin @ forward
    angles = np.linspace(0.0, 2.0 * np.pi, RING, endpoint=False)
    rings, ends = [], []
    for place in np.arange(along.min() + LAST_STEP_M / 2.0, along.max(), LAST_STEP_M):
        mine = np.abs(along - place) < LAST_STEP_M
        if mine.sum() < 6:  # the foot's very ends: too few points for a cross-section
            continue
        flat = np.stack([skin[mine] @ across, skin[mine] @ up], axis=1)
        middle, ring = hull_ring(flat, angles)
        rings.append(forward * place + ring[:, :1] * across + ring[:, 1:] * up)
        ends.append(forward * place + middle[0] * across + middle[1] * up)
    points = np.concatenate(rings + [[ends[0] - forward * LAST_STEP_M / 2.0, ends[-1] + forward * LAST_STEP_M / 2.0]])
    count, heel, toes = len(rings), len(rings) * RING, len(rings) * RING + 1
    faces = []
    for number in range(count - 1):
        for corner in range(RING):
            here, there = number * RING + corner, number * RING + (corner + 1) % RING
            faces += [[here, there, here + RING], [there, there + RING, here + RING]]
    for corner in range(RING):
        faces += [[heel, (corner + 1) % RING, corner],
                  [toes, (count - 1) * RING + corner, (count - 1) * RING + (corner + 1) % RING]]
    faces = np.asarray(faces)
    corners = points[faces]
    if np.einsum("fi,fi->f", corners[:, 0], np.cross(corners[:, 1], corners[:, 2])).sum() < 0.0:
        faces = faces[:, ::-1]
    return points, faces


def sampled(points, faces):
    """Points over a surface's triangles, SAMPLE_SPLITS + 1 a side of each on a barycentric grid: the body's own points
    lie too far apart for the last's thin cross-sections (half of them held under six, 2026-11-24)."""
    shares = np.array([(first, second, SAMPLE_SPLITS - first - second)
                       for first in range(SAMPLE_SPLITS + 1) for second in range(SAMPLE_SPLITS + 1 - first)],
                      dtype=float) / SAMPLE_SPLITS
    return np.einsum("sc,fci->fsi", shares, points[faces]).reshape(-1, 3)


def skin_blend(made, body_points, skin_points, count):
    """Each of `made`'s share of the body's points: its `count` nearest skin points (`skin_points`, numbers among
    `body_points`), by inverse distance."""
    from scipy.spatial import cKDTree
    distance, nearest = cKDTree(body_points[skin_points]).query(made, k=count)
    shares = 1.0 / np.maximum(distance, 1e-6)
    blend = np.zeros((len(made), len(body_points)))
    np.put_along_axis(blend, np.asarray(skin_points)[nearest], shares / shares.sum(axis=1, keepdims=True), axis=1)
    return blend


def sprung(made, body, side):
    """The toe box's front raised off the floor as a shoe's toe spring: TOE_SPRING_M at the toes' end, growing with
    the square of the way past the toes' base (the boxed toes' front went 3 mm through the floor at push-off)."""
    toes, end = joint_place(body, f"{side}ToeBase"), joint_place(body, f"{side}ToeEnd")
    forward = (end - toes) * np.array([1.0, 0.0, 1.0])
    reach = np.linalg.norm(forward)
    past = np.clip((made - toes) @ (forward / reach) / reach, 0.0, None)
    found = made.copy()
    found[:, 1] += TOE_SPRING_M * past ** 2
    return found


def smoothed(made, faces, rounds):
    """Taubin's smoothing (a shrinking step then a growing one, so the shape keeps its size), the surface's open
    edge kept where it is."""
    count = len(made)
    edges = np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
    pairs, uses = np.unique(np.sort(edges, axis=1), axis=0, return_counts=True)
    open_edge = np.zeros(count, dtype=bool)
    open_edge[pairs[uses == 1].ravel()] = True
    both = np.concatenate([pairs, pairs[:, ::-1]])
    neighbours = np.bincount(both[:, 0], minlength=count)[:, None]
    found = made.copy()
    for _ in range(rounds):
        for step in (0.5, -0.53):
            mean = np.zeros_like(found)
            np.add.at(mean, both[:, 0], found[both[:, 1]])
            moved = found + step * (mean / np.maximum(neighbours, 1) - found)
            found[~open_edge] = moved[~open_edge]
    return found


def shoe(body, side):
    """One shoe made on the body's `side` ("Left" or "Right") foot at the bind: {"points", "faces", "sole" (a face's
    flag), "blend" (each point's share of the body's points: where on the skin it is carried from), "weights",
    "covered" (the body's points the shoe covers), "foot length m"}."""
    points, faces = np.asarray(body["bind"], dtype=float), np.asarray(body["faces"], dtype=np.int64)
    weights = np.asarray(body["weights"], dtype=float)
    ankle, knee = joint_place(body, f"{side}Foot"), joint_place(body, f"{side}Shin")
    near = np.abs(points[:, 0] - ankle[0]) < np.abs(points[:, 0] + ankle[0])  # this side's half of the body
    foot = np.flatnonzero(near & (points[:, 1] < knee[1])
                          & (points[:, 1] < collar_height(body, side, points) + COLLAR_REACH_M))
    inside = np.zeros(len(points), dtype=bool)
    inside[foot] = True
    shape, shoe_faces = last(body, side, sampled(points, faces[inside[faces].all(axis=1)]))
    shape = smoothed(shape, shoe_faces, SMOOTH_ROUNDS)
    normals = vertex_normals(shape, shoe_faces)
    # the sole's share of a point: none on the last's sides and top, all of it under it, so the sole keeps its
    # thickness under the toes as the foot rolls onto them (a foot's bottom band stretched down left the toes' sole
    # 4 mm thin and the shoe 8 mm over the floor at push-off, 2026-11-24)
    sole = np.clip((-normals[:, 1] - SOLE_FROM) / (1.0 - 2.0 * SOLE_FROM), 0.0, 1.0)
    made = sprung(shape + normals * (UPPER_M + SOLE_M * sole)[:, None], body, side)
    blend = skin_blend(shape, points, foot, BLEND_NEAREST)
    made, blend, shoe_faces, inside = cut(made, blend, shoe_faces, shape[:, 1] - collar_height(body, side, shape))
    made, blend, shoe_faces = kept_only(made, blend, shoe_faces[inside])
    lowest = made[:, 1].min()
    made, blend, shoe_faces, sole_faces = cut(made, blend, shoe_faces, made[:, 1] - lowest - SOLE_LINE_M)
    covered = foot[points[foot, 1] < collar_height(body, side, points[foot]) - COVERED_UNDER_M]
    made = cleared(made, shoe_faces, blend @ weights, body, covered, CLEAR_ROUNDS)
    along = points[foot] @ ((joint_place(body, f"{side}ToeEnd") - ankle) * np.array([1.0, 0.0, 1.0]))
    along /= np.linalg.norm((joint_place(body, f"{side}ToeEnd") - ankle) * np.array([1.0, 0.0, 1.0]))
    return {"points": made, "faces": shoe_faces, "sole": sole_faces, "blend": blend, "weights": blend @ weights,
            "covered": covered, "foot length m": float(along.max() - along.min())}


def kept_only(made, blend, faces):
    """Only the points `faces` use, the faces renumbered."""
    used = np.unique(faces)
    local = np.full(len(made), -1)
    local[used] = np.arange(len(used))
    return made[used], blend[used], local[faces]


def carried(points, weights, body, frames=None):
    """Points made at the bind carried by the body's joints every frame of the body's `worlds`, or those of `frames`
    (frames x points x 3)."""
    from score.stages.people_cloth import skinned
    joints = np.tile(np.arange(weights.shape[1]), (len(weights), 1))
    worlds = np.asarray(body["worlds"])
    return skinned(points, joints, weights, worlds if frames is None else worlds[frames], np.asarray(body["joints"]))


def face_uvs(points, faces):
    """Each triangle corner's texture coordinate, the triangle projected along its normal's largest axis."""
    corners = points[faces]
    normal = np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0])
    axis = np.abs(normal).argmax(axis=1)
    keep = np.array([[1, 2], [0, 2], [0, 1]])[axis]
    flat = np.take_along_axis(corners, np.repeat(keep[:, None, :], 3, axis=1), axis=2)
    return flat.reshape(-1, 2) / TEXTURE_METRES


def hips_turns(body, frames):
    """The hips' turn off the bind each of `frames` (indices of `worlds`), 3 x 3."""
    names = [str(each) for each in body["names"]]
    hips = names.index("Hips")
    worlds = np.asarray(body["worlds"])[frames, hips, :3, :3]
    return worlds @ np.linalg.inv(np.asarray(body["joints"])[hips, :3, :3])[None]


def ring_bins(around, centre, axes):
    """The largest distance off the waist's middle of `around` (points x 3) in each of BINS turns round it, empty
    turns filled from their neighbours. `axes`: the frame's x, up and z."""
    offset = around - centre
    side, up, front = axes
    angle = np.arctan2(offset @ front, offset @ side) % (2.0 * np.pi)
    radius = np.hypot(offset @ front, offset @ side)
    bins = (angle / (2.0 * np.pi) * BINS).astype(int) % BINS
    found = np.full(BINS, np.nan)
    for number in np.unique(bins):
        found[number] = radius[bins == number].max()
    known = np.flatnonzero(~np.isnan(found))
    if len(known) == 0:
        raise SystemExit("the belt finds nothing at its waistband")
    found = np.interp(np.arange(BINS), known, found[known], period=BINS)
    return np.maximum(found, np.maximum(np.roll(found, 1), np.roll(found, -1)))


def in_band(ring, points, turn):
    """Which of `points` are in the belt's band: from its top (UNDER_TOP_M under the waistband's top, `ring`) down
    BELT_M, CLEAR_M either side, and no further round than REACH_M past the waistband's widest."""
    side, up, front = turn[:, 0], turn[:, 1], turn[:, 2]
    centre = ring.mean(axis=0)
    top = float(((ring - centre) @ up).max())
    offset = points - centre
    band = offset @ up
    reach = np.hypot(offset @ side, offset @ front)
    widest = float(np.hypot((ring - centre) @ side, (ring - centre) @ front).max())
    return (band > top - UNDER_TOP_M - BELT_M - CLEAR_M) & (band < top + CLEAR_M) & (reach < widest + REACH_M)


def held_in(ring, skin, belt_radius, turn):
    """How far the belt's inside stands off the skin under it at its farthest turn round (m): what the cloth between
    them holds it out by. A belt that holds the cloth in stands off the skin by the cloth's layers alone."""
    side, up, front = turn[:, 0], turn[:, 1], turn[:, 2]
    skin_radius = ring_bins(skin[in_band(ring, skin, turn)], ring.mean(axis=0), (side, up, front))
    return float((belt_radius[:BINS] - CLEAR_M - skin_radius).max())


def under_cover(ring, cover, belt_radius, turn):
    """How far the cloth worn over the belt (`cover`, its points) comes inside the belt's outside at its deepest turn
    round (m, negative when it stays outside): the belt out through the coat over it. Turns with no cover point in
    the band are left out."""
    side, up, front = turn[:, 0], turn[:, 1], turn[:, 2]
    centre = ring.mean(axis=0)
    offset = cover[in_band(ring, cover, turn)] - centre
    if not len(offset):
        return -np.inf
    angle = np.arctan2(offset @ front, offset @ side) % (2.0 * np.pi)
    bins = (angle / (2.0 * np.pi) * BINS).astype(int) % BINS
    radius = np.hypot(offset @ front, offset @ side)
    nearest = np.full(BINS, np.inf)
    np.minimum.at(nearest, bins, radius)
    covered = np.isfinite(nearest)
    return float((belt_radius[:BINS][covered] + BELT_THICK_M - nearest[covered]).max())


def belt_frame(ring, around, turn):
    """The belt on one frame: its points (rows of BINS + 1, the seam point twice for its texture: inside top, inside
    bottom, outside bottom, outside top), the waistband's top height and the frame's axes."""
    side, up, front = turn[:, 0], turn[:, 1], turn[:, 2]
    centre = ring.mean(axis=0)
    top = float(((ring - centre) @ up).max())
    belt_top = top - UNDER_TOP_M
    radius = ring_bins(around[in_band(ring, around, turn)], centre, (side, up, front)) + CLEAR_M
    angles = (np.arange(BINS + 1) + 0.5) * 2.0 * np.pi / BINS
    radius = np.append(radius, radius[0])
    directions = np.cos(angles)[:, None] * side + np.sin(angles)[:, None] * front
    rows = [(0.0, belt_top), (0.0, belt_top - BELT_M), (BELT_THICK_M, belt_top - BELT_M), (BELT_THICK_M, belt_top)]
    points = np.concatenate([centre + directions * (radius + out)[:, None] + up * height for out, height in rows])
    return points, centre + up * top, (side, up, front), radius


def band_faces(count, rows):
    """Quads between consecutive rows (and the last back to the first) of `count` points, as triangles."""
    faces = []
    for row in range(rows):
        nxt = (row + 1) % rows
        for column in range(count - 1):
            here, there = row * count + column, nxt * count + column
            faces += [[here, here + 1, there], [here + 1, there + 1, there]]
    return np.asarray(faces)


def buckle_points(centre, axes, radius, belt_top):
    """A buckle's frame at the belt's front: an outer and an inner rectangle, each front and back (16 points)."""
    side, up, front = axes
    face_at = centre + front * (radius + BELT_THICK_M) + up * (belt_top - BELT_M / 2.0)
    half_w, half_h = BUCKLE["wide"] / 2.0, (BELT_M + BUCKLE["tall_over"]) / 2.0
    found = []
    for depth in (0.0, BUCKLE["deep"]):
        for width, height in ((half_w, half_h), (half_w - BUCKLE["bar"], half_h - BUCKLE["bar"])):
            found += [face_at + front * depth + side * sx * width + up * sy * height
                      for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    return np.asarray(found)


def buckle_faces():
    """The buckle frame's triangles: front and back rings and the outer and inner walls."""
    faces = []
    rings = {"front outer": 0, "front inner": 4, "back outer": 8, "back inner": 12}
    for outer, inner in (("front outer", "front inner"), ("back outer", "back inner"), ("front outer", "back outer"),
                         ("front inner", "back inner")):
        for corner in range(4):
            here, there = rings[outer] + corner, rings[outer] + (corner + 1) % 4
            down, across = rings[inner] + corner, rings[inner] + (corner + 1) % 4
            faces += [[here, there, across], [here, across, down]]
    return np.asarray(faces)


def belt(body, start, garments, ring_points, covering=()):
    """The belt and its buckle over the clip: `garments` the draped garments it is worn round (frames x points x 3
    each), the waistband's top the points `ring_points` of the first of them; `covering` the garments worn over it
    (a coat over a belted shirt), never gone round. Frames x points x 3 each, with their faces, the waistband's top
    each frame, the belt's inside off the skin and the cover's deepest inside the belt (`under_cover`)."""
    worn = [np.asarray(points) for points in garments]
    count = len(worn[0])
    body_frames = np.asarray(body["frames"])[start:start + count]
    turns = hips_turns(body, np.arange(start, start + count))
    over = [np.asarray(points) for points in covering]
    belts, buckles, tops, ups, off_skin, inside_cover = [], [], [], [], [], []
    for frame in range(count):
        ring = worn[0][frame][ring_points]
        around = np.concatenate([points[frame] for points in worn] + [body_frames[frame]])
        points, top, axes, radius = belt_frame(ring, around, turns[frame])
        off_skin.append(held_in(ring, body_frames[frame], radius, turns[frame]))
        if over:
            inside_cover.append(under_cover(ring, np.concatenate([cloth[frame] for cloth in over]), radius,
                                            turns[frame]))
        belts.append(points)
        tops.append(top)
        ups.append(axes[1])
        front = int(round((np.pi / 2.0) / (2.0 * np.pi) * BINS - 0.5))
        buckles.append(buckle_points(ring.mean(axis=0), axes, radius[front],
                                     float((top - ring.mean(axis=0)) @ axes[1]) - UNDER_TOP_M))
    return {"belt": np.asarray(belts), "belt faces": band_faces(BINS + 1, 4), "buckle": np.asarray(buckles),
            "buckle faces": buckle_faces(), "waistband top": np.asarray(tops), "up": np.asarray(ups),
            "off the skin": np.asarray(off_skin), "inside the cover": np.asarray(inside_cover)}


def belt_uvs():
    """Each belt point's texture coordinate (u round the waist, v across), BINS + 1 a row, 4 rows."""
    across = [0.0, BELT_M, BELT_M + BELT_THICK_M, 2.0 * BELT_M + BELT_THICK_M]
    columns = np.arange(BINS + 1) / BINS
    return np.array([[column * 0.8 / TEXTURE_METRES, height / TEXTURE_METRES] for height in across
                     for column in columns])


def capped(faces):
    """The shoe's faces with its collar closed: a fan from a new point (numbered after the shoe's) at the collar's
    middle, for telling inside from out."""
    edges = np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
    keys, uses = np.unique(np.sort(edges, axis=1), axis=0, return_counts=True)
    open_keys = {tuple(key) for key in keys[uses == 1]}
    rim = [edge for edge in edges if tuple(sorted(edge)) in open_keys]
    middle = int(faces.max()) + 1
    return np.concatenate([faces, np.array([[second, first, middle] for first, second in rim], dtype=faces.dtype)])


def winding(points, triangles):
    """The winding number of the closed surface of `triangles` (corners x 3 each) round each of `points`
    (Jacobson's: the triangles' solid angles over 4 pi): one inside, nought outside."""
    found = np.zeros(len(points))
    for start in range(0, len(points), 64):
        corner = triangles[None] - points[start:start + 64, None, None]  # points x triangles x 3 x 3
        length = np.linalg.norm(corner, axis=3)
        first, second, third = corner[..., 0, :], corner[..., 1, :], corner[..., 2, :]
        volume = np.einsum("pti,pti->pt", first, np.cross(second, third))
        under = (length[..., 0] * length[..., 1] * length[..., 2]
                 + np.einsum("pti,pti->pt", first, second) * length[..., 2]
                 + np.einsum("pti,pti->pt", second, third) * length[..., 0]
                 + np.einsum("pti,pti->pt", third, first) * length[..., 1])
        found[start:start + 64] = (2.0 * np.arctan2(volume, under)).sum(axis=1) / (4.0 * np.pi)
    return found


def out_past(skin, shoe_points, shoe_faces):
    """How far each skin point is out of the shoe: nought inside it (its collar closed, `winding` over a half),
    else its distance to the shoe."""
    import trimesh
    closed = np.concatenate([shoe_points, collar_middle(shoe_points, shoe_faces)[None]])
    outside = winding(skin, closed[capped(shoe_faces)]) < 0.5
    found = np.zeros(len(skin))
    if outside.any():
        mesh = trimesh.Trimesh(shoe_points, shoe_faces, process=False)
        found[outside] = trimesh.proximity.closest_point(mesh, skin[outside])[1]
    return found


def cleared(made, faces, weights, body, covered, rounds):
    """The shoe pushed out over the skin it covers wherever that skin is out of it, at the bind and on every
    CLEAR_EVERY-th frame of the clip as the shoe and the foot are carried: the bind's corners of the triangle nearest
    an outside skin point moved out along that triangle's normal by the skin's distance and CLEAR_STEP_M (the big
    toe's top stood 4 mm out through the smoothed toe box at the bind, and the bending toes 1.3 mm out through the
    shoe on the clip, 2026-11-24)."""
    import trimesh
    found = made.copy()
    frames = [0, *range(int(body["clip_start"]), len(body["frames"]), CLEAR_EVERY)]
    for _ in range(rounds):
        push = np.zeros_like(found)
        posed = carried(found, weights, body, frames)
        for number, frame in enumerate(frames):
            skin = np.asarray(body["frames"])[frame][covered]
            past = out_past(skin, posed[number], faces)
            if past.max() <= 0.0:
                continue
            mesh = trimesh.Trimesh(found, faces, process=False)
            _, _, triangles = trimesh.proximity.closest_point(trimesh.Trimesh(posed[number], faces, process=False),
                                                              skin[past > 0.0])
            for distance, triangle in zip(past[past > 0.0], triangles):
                wanted = mesh.face_normals[triangle] * (distance + CLEAR_STEP_M)
                for corner in faces[triangle]:
                    if wanted @ wanted > push[corner] @ push[corner]:
                        push[corner] = wanted
        if not push.any():
            break
        found += push
    return found


def collar_middle(shoe_points, shoe_faces):
    """The middle of the shoe's open edge (its collar)."""
    edges = np.concatenate([shoe_faces[:, [0, 1]], shoe_faces[:, [1, 2]], shoe_faces[:, [2, 0]]])
    keys, uses = np.unique(np.sort(edges, axis=1), axis=0, return_counts=True)
    return shoe_points[np.unique(keys[uses == 1])].mean(axis=0)


def measured(shoes, worn_shoes, body_frames, body_faces, belted, lift):
    """The fit over the clip: each shoe's foot length (and EU size, 1.5 x (foot cm + 1.5)), its sole's lowest over
    the floor after the lift, and how far the foot's skin it covers comes out past the shoe (`out_past`); the belt's
    top off the waistband's top and its girth."""
    found = {}
    for side, made in shoes.items():
        frames = worn_shoes[side]
        lowest = float(frames[..., 1].min()) + lift
        outs = made.get("outs") or [float(out_past(skin[made["covered"]], frame, made["faces"]).max())
                                    for frame, skin in zip(frames, body_frames)]
        found[side.lower()] = {"foot length cm": round(made["foot length m"] * 100.0, 1),
                               "eu size": round(1.5 * (made["foot length m"] * 100.0 + 1.5), 1),
                               "sole lowest over the floor mm": round(lowest * 1000.0, 1),
                               "foot farthest out past the shoe mm": round(max(outs) * 1000.0, 2)}
    if belted is not None:
        top_rows = belted["belt"][:, -(BINS + 1):]
        top_off = np.abs(np.einsum("fi,fi->f", top_rows.mean(axis=1) - belted["waistband top"], belted["up"]))
        inner = belted["belt"][:, :BINS]
        girth = np.linalg.norm(np.diff(np.concatenate([inner, inner[:, :1]], axis=1), axis=1), axis=2).sum(axis=1)
        found["belt"] = {"top farthest off the waistband top mm": round(float(top_off.max()) * 1000.0, 1),
                         "girth cm": [round(float(girth.min()) * 100.0, 1), round(float(girth.max()) * 100.0, 1)],
                         "inside farthest off the skin mm": round(float(belted["off the skin"].max()) * 1000.0, 1)}
        if len(belted["inside the cover"]):
            found["belt"]["out through the cloth over it mm"] = round(
                max(0.0, float(belted["inside the cover"].max())) * 1000.0, 1)
    return found


def faults(found):
    """The measures past their limits, one line each (none when the accessories fit)."""
    lines = []
    for side in ("left", "right"):
        shoe_found = found.get(side)
        if shoe_found is None:
            continue
        if shoe_found["sole lowest over the floor mm"] < -FLOOR_LIMIT_M * 1000.0:
            lines.append(f"{side} shoe below the floor: {shoe_found['sole lowest over the floor mm']} mm (limit "
                         f"-{FLOOR_LIMIT_M * 1000.0:.0f})")
        if shoe_found["sole lowest over the floor mm"] > HOVER_LIMIT_M * 1000.0:
            lines.append(f"{side} shoe never on the floor: its sole {shoe_found['sole lowest over the floor mm']} mm "
                         f"over it at its lowest (limit {HOVER_LIMIT_M * 1000.0:.0f})")
        if shoe_found["foot farthest out past the shoe mm"] > FOOT_LIMIT_M * 1000.0:
            lines.append(f"{side} foot out through its shoe: {shoe_found['foot farthest out past the shoe mm']} mm")
    if "belt" in found and found["belt"]["top farthest off the waistband top mm"] > BELT_LIMIT_M * 1000.0:
        lines.append(f"belt off the waistband: its top {found['belt']['top farthest off the waistband top mm']} mm "
                     f"off the waistband's top (limit {BELT_LIMIT_M * 1000.0:.0f})")
    if "belt" in found and found["belt"]["inside farthest off the skin mm"] > HOLD_LIMIT_M * 1000.0:
        lines.append(f"belt not holding the cloth in: its inside {found['belt']['inside farthest off the skin mm']} "
                     f"mm off the skin (limit {HOLD_LIMIT_M * 1000.0:.0f})")
    if found.get("belt", {}).get("out through the cloth over it mm", 0.0) > COVER_LIMIT_M * 1000.0:
        lines.append(f"belt out through the cloth over it: {found['belt']['out through the cloth over it mm']} mm "
                     f"(limit {COVER_LIMIT_M * 1000.0:.0f})")
    return lines


def worn(chosen, body, drape, records, library=None):
    """The outfit's accessories (its `accessories`: "shoes" and a "belt" "on" a garment) over the drape's clip
    frames: {"shoes": {side: shoe with its "frames"}, "belt": belt() or None, "lift", "found", "faults"}. Shoes that
    name a library `model` are that model fitted on each foot (`shoe_model`, read from the fetched `library`), else
    made on the foot (`shoe`)."""
    start = int(body["clip_start"])
    names = [name for name in drape if name in records]
    count = len(drape[names[0]])
    shoes = {}
    if "shoes" in chosen:
        shoes = shoes_worn(chosen["shoes"], body, start, count, library)
    belted = None
    if "belt" in chosen:
        under, over = chosen["belt"]["on"], chosen["belt"].get("covered by", [])
        ring = np.asarray(records[under]["label/lower_interface"])
        belted = belt(body, start, [drape[under]] + [drape[name] for name in names if name not in [under, *over]],
                      ring, [drape[name] for name in over])
    # lifted so the lower sole's lowest over the clip stands on the floor, as the clip's bare feet do (lifted by the
    # soles' depth under the feet at the bind, they stood 3 to 5 mm over the floor all through the walk, 2026-11-24)
    lift = max([-float(made["frames"][..., 1].min()) for made in shoes.values()], default=0.0)
    found = measured(shoes, {side: made["frames"] for side, made in shoes.items()},
                     np.asarray(body["frames"])[start:start + count], np.asarray(body["faces"]), belted, lift)
    return {"shoes": shoes, "belt": belted, "lift": lift, "found": found,
            "faults": faults(found)}


def shoes_worn(chosen, body, start, count, library):
    """Each side's shoe carried over the clip's `count` frames from `start` ("frames"); a library model's with how far
    the foot is out of it each frame ("outs", `shoe_model.out_of`)."""
    from tools.characters.accessories import shoe_model
    found = {}
    if "model" in chosen:
        kind, rest = chosen["model"]["address"].split("/", 1)
        name, version = rest.split("@")
        model = shoe_model.read(pathlib.Path(library) / kind / name / version / chosen["model"]["file"])
        grid = shoe_model.cavity(model)
    for side in ("Left", "Right"):
        made = shoe_model.fitted(body, side, model, grid) if "model" in chosen else shoe(body, side)
        made["frames"] = carried(made["points"], made["weights"], body)[start:start + count]
        if "model" in chosen:
            made["outs"] = [float(shoe_model.out_of(made, np.asarray(body["frames"])[frame][made["covered"]],
                                                    shoe_model.moves_at(body, frame)).max())
                            for frame in range(start, start + count)]
        found[side] = made
    return found


def collidable(mesh, first):
    """`mesh` a collider for Newton (UsdPhysics: a convex hull round it), its points' default the clip's first frame's
    (`first`): Newton's importer reads the default, and with time samples alone it read no points (2026-11-24)."""
    from pxr import UsdPhysics, Vt
    mesh.GetPointsAttr().Set(Vt.Vec3fArray.FromNumpy(np.asarray(first, dtype=np.float32)))
    UsdPhysics.CollisionAPI.Apply(mesh.GetPrim())
    UsdPhysics.MeshCollisionAPI.Apply(mesh.GetPrim()).CreateApproximationAttr(UsdPhysics.Tokens.convexHull)


def textured(mesh, uvs, interpolation):
    from pxr import Sdf, UsdGeom
    primvar = UsdGeom.PrimvarsAPI(mesh).CreatePrimvar("st", Sdf.ValueTypeNames.TexCoord2fArray, interpolation)
    primvar.Set(np.asarray(uvs, dtype=np.float32).tolist())


def written_into(stage, dressed, chosen, library):
    """/Outfit/Accessories in `stage`: each shoe an upper and a sole (colliders; a library model's one mesh, a
    collider, in its finish), the belt and its buckle, every clip frame, each bound to its library surface; /Outfit
    lifted by the soles."""
    from pxr import Gf, UsdGeom
    from tools.characters.garments import cache
    UsdGeom.Xform.Define(stage, "/Outfit/Accessories")
    if dressed["lift"]:
        UsdGeom.Xformable(stage.GetPrimAtPath("/Outfit")).AddTranslateOp().Set(Gf.Vec3d(0.0, dressed["lift"], 0.0))
    for side, made in dressed["shoes"].items():
        UsdGeom.Xform.Define(stage, f"/Outfit/Accessories/{side.lower()}_shoe")
        if "uv" in made:  # a library model: one mesh, its own UVs, its finish
            mesh = cache.mesh_at(stage, f"/Outfit/Accessories/{side.lower()}_shoe/shoe", made["faces"], made["frames"],
                                 0)
            textured(mesh, made["uv"], UsdGeom.Tokens.vertex)
            collidable(mesh, made["frames"][0])
            cache.bound(stage, mesh, chosen["shoes"]["finish"], library)
            continue
        for part, faces in (("upper", made["faces"][~made["sole"]]), ("sole", made["faces"][made["sole"]])):
            mesh = cache.mesh_at(stage, f"/Outfit/Accessories/{side.lower()}_shoe/{part}", faces, made["frames"], 0)
            textured(mesh, face_uvs(made["points"], faces), UsdGeom.Tokens.faceVarying)
            collidable(mesh, made["frames"][0])
            cache.bound(stage, mesh, chosen["shoes"][part], library)
    if dressed["belt"] is not None:
        belted = dressed["belt"]
        strap = cache.mesh_at(stage, "/Outfit/Accessories/belt", belted["belt faces"], belted["belt"], 0)
        textured(strap, belt_uvs(), UsdGeom.Tokens.vertex)
        cache.bound(stage, strap, chosen["belt"]["strap"], library)
        buckle = cache.mesh_at(stage, "/Outfit/Accessories/buckle", belted["buckle faces"], belted["buckle"], 0)
        textured(buckle, face_uvs(belted["buckle"][0], belted["buckle faces"]), UsdGeom.Tokens.faceVarying)
        cache.bound(stage, buckle, chosen["belt"]["buckle"], library)


def surfaces(chosen):
    """The library surfaces the accessories wear."""
    return [surface for kind in chosen.values() for key, surface in kind.items() if isinstance(surface, dict)]
