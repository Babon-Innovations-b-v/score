"""A decal's plate (#159 round 13; the owner on the locker, 2026-11-24: "its mainly just the lock and the holes"): under
a vent pattern or a printed mark the made shape is flat and closed. TRELLIS.2 draws a locker door's vent holes as
bumps up to 4 mm proud with bars cut right through the door sheet (#191), and the pattern drawn over them showed the
bumps shading under its holes and the bars black through them. The parts row (route_parts.take_decals) holds each
placement to its part's plate here, from the take's own mesh: a grid of rays cast straight at the placement's face
over its box grown by its own size each way (`sampled`) gives each cell's height off the plate, the plate a plane
fitted to the cells of its part that lie on it (`fitted`); a row or column of the grid that is nearly all off the plate
(another part, a step, a groove, no model) is a seam or a part's edge (`seams`). A pattern takes the take's own up
(`upright`: the close-up is drawn upright, and the up its probes give on TRELLIS.2's bumps runs anywhere, the
locker's vents up to 59 degrees off their doors), and
one whose box crosses a seam is moved clear of it, to the side holding the more of it, and refused when that is more
than half its box (`clear_of`): tc6's locker's lower vents of its upper doors were cast across the seam to the doors
below, the fitted camera's error. A text or picture mark is never moved: across a seam, or where its plate is not flat
round it (a fluted cylinder, a curved grip), it is left as it is (`open`, why).

The placement's `closed` ({box, most, plate_point}): the plate's region the bake and the look close
(tools/props/library/inside/bake.py: closed_points and pressed_under, closing_card and cards_over): its `box`, [left, bottom,
right, top] in metres across and up its face from its `at` (its own box, and the bumps and holes that reach out of it,
at most CLOSE_GROW of its size, never over a seam), in which every point standing up to `most` (BUMP_MOST) proud is
pressed onto the plate, and one flat card laid over it on the plate in the finish of the plate at `plate_point`. Its
`at` lies on the plate and its `normal` is the plate's. Its `also`: a box, across and up from the same `at`, round each
hole TRELLIS.2 cut through the plate outside every closed region (holes_closed), closed as its `box` is.

    held(placement, mesh, same, pattern)   the placement on its plate, closed; (None, why) when a pattern cannot be
                                           placed clear of a seam
    holes_closed(placements, mesh, sames, shown=None)  the placements with the holes through their plates outside
                                           every closed region closed too (`also`)
    closed_round(placement, mesh, same, most, reach)  a hardware cut's region closed on its plate (#212), or None
"""
import numpy as np
from scipy import ndimage

GRID = 40  # cells across a box's shorter side
GRID_MOST = 240  # and at most this many across its longer
FRONT = 0.02  # the rays start this far in front of the placement's point
# A cell within TOLERANCE of the plate, and within TOLERANCE_SHARE of its box's longer side, lies on it (the locker's
# door: 0.3 mm off flat over 0.24 m; a 2.4 cm label on the drill's 3 cm round body lies 1.5 mm off its tangent plane
# 9.5 mm each side of it, 0.5 mm 5.5 mm each side, under PLATE_SHARE of its grid either way).
TOLERANCE = 0.0015
TOLERANCE_SHARE = 0.02
# The plate is flat when at least this share of its part's cells lie on the plane fitted to them: the locker's upper
# door's vent box cast across the seam holds 0.45 of them on the door, the rest on the door below, its bumps and holes.
PLATE_SHARE = 0.35
PLATE_FEWEST = 20
BIN = 0.0005  # the plate's height is its part's cells' most common, in bins this wide
SEAM_SHARE = 0.85  # a row or column of cells this much off the plate is a seam or an edge (a vent row: 0.56 at most)
SEAM_TURN = 10  # degrees a seam is looked for turned off the box's own across and up
SEAM_CLEAR = 0.005  # a moved pattern's box keeps this far from the seam it was moved off (over a grid cell)
BUMP_MOST = 0.006  # a cell proud of the plate by more than this is a fitting (a lock, a handle), never pressed flat
CLOSE_GROW = 0.3  # the closed region reaches at most this share of the box's size past it each way
# and LIP grid cells past what it closes: a bar's end cut between two cells drew a dark sliver at the card's edge.
LIP = 2
# A hole TRELLIS.2 cut through a closed mark's plate outside its region (holes_closed, r13: a black dot above each of
# the locker's vents, 1 to 2 cm across, seeing the cabinet's inside 0.24 m behind its door): a patch of the plate's
# grid HOLE_STEP apart (coarser where the plate holds over HOLE_CELLS) whose rays meet nothing or meet the model more
# than HOLE_DEEP behind the plate (the door sheet is 7 mm), at most HOLE_MOST across, ringed LIP cells wide by its
# part within BUMP_MOST of the plate, is closed by a box of its own round it. So is one of any size the close-up shows
# as its plate (`shown`): every ray of it HOLE_THROUGH behind the plate or meeting nothing (right through the sheet,
# never a pocket: a recessed handle's back lies 2 to 4 cm in), HOLE_RING of the cells round it that are no hole its
# part at most BUMP_MOST proud (the hole's own wall, sunk into the sheet, counted with the plate), and the close-up's
# lightness across it within HOLE_SHOWN L* of the plate's round it (HOLE_SEEN cells out), that plate at least
# HOLE_LIGHT: r15f's locker's band 1 remesh kept bars up to 14 cm long through its light doors, which its close-up shows
# plain, onto the cabinet's back 0.48 m behind, its rims 6 to 8 mm down; on a dark plate (r15f's tool cart, L* 15 to
# 30) the close-up cannot tell a hole from the plate, and the hole is left as made.
HOLE_STEP = 0.002
HOLE_CELLS = 250000
HOLE_DEEP = 0.01
HOLE_MOST = 0.025
HOLE_THROUGH = 0.05
HOLE_RING = 0.95
HOLE_SHOWN = 10.0
HOLE_LIGHT = 50.0
HOLE_SEEN = (LIP + 1, 3 * LIP)
PLATE_SAME = 0.999  # two closed marks' normals this alike (cosine), and their plates within BUMP_MOST, share one


def axes(placement):
    """(right, up, normal) unit vectors of a placement's face: its `up` made square to its `normal`, right = up x
    normal (route_parts.ink_extent's)."""
    normal = np.asarray(placement["normal"], dtype=float)
    normal = normal / np.linalg.norm(normal)
    up = np.asarray(placement["up"], dtype=float)
    up = up - (up @ normal) * normal
    up = up / np.linalg.norm(up)
    return np.cross(up, normal), up, normal


def sampled(placement, mesh, same):
    """(across, up, height, mine, facing): the grid over the placement's box grown by its own size each way (cast)."""
    wide, tall = placement["size"]
    step = max(min(wide, tall) / GRID, max(wide, tall) / GRID_MOST)
    return cast(placement, mesh, same, *np.meshgrid(np.arange(-wide, wide + step / 2, step),
                                                    np.arange(-tall, tall + step / 2, step)))


def cast(placement, mesh, same, across, upward):
    """(across, up, height, mine, facing) of the grid `across`, `upward` on the placement's face: each cell's height
    off its point along its normal where a ray from FRONT in front first meets the mesh (NaN where it meets nothing: an
    edge, or a hole right through), whether that face is of its part (`same`, a face's) and its facing (across, up and
    out)."""
    right, up, normal = axes(placement)
    at = np.asarray(placement["at"], dtype=float)
    origins = at + across.reshape(-1, 1) * right + upward.reshape(-1, 1) * up + FRONT * normal
    faces, rays, points = mesh.ray.intersects_id(origins, np.tile(-normal, (len(origins), 1)), multiple_hits=False,
                                                 return_locations=True)
    height, mine = np.full(len(origins), np.nan), np.zeros(len(origins), dtype=bool)
    facing = np.tile([0.0, 0.0, 1.0], (len(origins), 1))
    height[rays] = (points - at) @ normal
    mine[rays] = same[faces]
    facing[rays] = mesh.face_normals[faces] @ np.c_[right, up, normal]
    return (across, upward, height.reshape(across.shape), mine.reshape(across.shape),
            facing.reshape(*across.shape, 3))


def fitted(across, upward, height, mine, facing, tolerance):
    """(slope across, slope up, offset) of the plane its part's cells (`mine`) lie on, or None when under PLATE_SHARE
    of them (or PLATE_FEWEST) lie within `tolerance` of it. Its tilt first the median of their faces' facings (`facing`,
    across, up and out a cell; a placement's own may tilt 7 degrees on TRELLIS.2's bumps), its offset their heights'
    most common (BIN wide), then fitted to those within `tolerance` of that: a median or a fit to them all hinges
    between a door and the door below it a step behind (tc6's locker)."""
    known = mine & ~np.isnan(height)
    if known.sum() < PLATE_FEWEST:
        return None
    middle = np.median(facing[known], axis=0)
    slopes = -middle[:2] / middle[2]
    flat = height - slopes[0] * across - slopes[1] * upward
    bins = np.floor(flat[known] / BIN).astype(int)
    offset = (np.bincount(bins - bins.min()).argmax() + bins.min() + 0.5) * BIN
    near = known & (np.abs(flat - offset) <= tolerance)
    if near.sum() < max(PLATE_FEWEST, PLATE_SHARE * known.sum()):
        return None
    return np.linalg.lstsq(np.c_[across[near], upward[near], np.ones(near.sum())], height[near], rcond=None)[0]


def tolerance_of(size):
    """How far off its plate a cell of a box of `size` may lie on it: TOLERANCE, at most TOLERANCE_SHARE of its longer
    side."""
    return min(TOLERANCE, TOLERANCE_SHARE * max(size))


def off_plate(height, mine, tolerance):
    """Which cells are off the plate: of another part, of none, or further than `tolerance` off it (`height` off the
    fitted plane)."""
    return ~mine | np.isnan(height) | (np.abs(height) > tolerance)


def seams(across, upward, off, step):
    """[(way, place, cells)] of the grid's seams and edges: lines along which at least SEAM_SHARE of the cells lie off
    the plate (`off`), `way` the unit line square to them across and up, `place` theirs along it from the middle,
    `cells` the grid's cells on them. Each of the two ways (a line running across, one running up) is looked for
    turned up to SEAM_TURN, the turn with the most such lines (then the most off, then the least turned): the
    close-up's up is cast through a fitted camera, and tc6's locker's door seam ran 3 degrees across its vent's box;
    past a part's edge every line is off at any turn, and only the edge's own turn lines up the most."""
    found = []
    for square in (np.pi / 2, 0.0):
        best = None
        for turn in np.radians(sorted(np.arange(-SEAM_TURN, SEAM_TURN + 0.5, 1.0), key=abs)):
            way = np.array([np.cos(square + turn), np.sin(square + turn)])
            bins = np.round((across * way[0] + upward * way[1]) / step).astype(int)
            counts = np.bincount((bins - bins.min()).ravel())
            shares = np.bincount((bins - bins.min()).ravel(), weights=off.ravel()) / np.maximum(counts, 1)
            shares[counts < counts.max() / 2] = 0.0
            score = (int((shares >= SEAM_SHARE).sum()), shares.max())
            if best is None or score > best[0]:
                best = (score, way, bins, shares)
        _, way, bins, shares = best
        for line in np.flatnonzero(shares >= SEAM_SHARE):
            found.append((way, float((line + bins.min()) * step), bins == line + bins.min()))
    return found


def clear_of(places, half):
    """How far a box `half` wide each side of its middle (along one way) moves to clear the seams at `places` (along
    it, from its middle) inside it: past the nearest end to the side holding the more of it, SEAM_CLEAR beyond; 0.0
    with none inside; None when that is more than its half."""
    places = np.asarray(places, dtype=float)
    inside = places[np.abs(places) < half]
    if not len(inside):
        return 0.0
    up, down = inside.max() + SEAM_CLEAR + half, inside.min() - SEAM_CLEAR - half
    move = up if abs(up) <= abs(down) else down
    return None if abs(move) > half else float(move)


def half_along(way, size):
    """Half a box of `size` (wide, tall) along a unit `way` across and up."""
    return abs(way[0]) * size[0] / 2 + abs(way[1]) * size[1] / 2


def moved_clear(lines, size):
    """[across, up] metres a box of `size` moves to clear the seams `lines` (seams') it crosses, a way at a time; None
    when it cannot (clear_of)."""
    move = np.zeros(2)
    for square in (0, 1):  # a line running across, then one running up
        mine = [(way, place) for way, place, _ in lines if abs(way[1 - square]) >= abs(way[square])]
        if not mine:
            continue
        step = clear_of([place for _, place in mine], half_along(mine[0][0], size))
        if step is None:
            return None
        move = move + step * mine[0][0]
    return [round(float(value), 5) for value in move]


def closed_region(across, upward, height, mine, lines, size, most=BUMP_MOST, reach=None):
    """[left, bottom, right, top] of the region to close: the box, grown over the cells off the plate (sunk or
    through, or of its part and proud by at most `most`; never another part's standing proud, a fitting) joined
    to it and LIP cells past them, at most CLOSE_GROW of its size past it each way (or to `reach` of its middle), ending
    a grid cell short of a seam (`lines`, seams')."""
    wide, tall = size
    tolerance, step = tolerance_of(size), across[0, 1] - across[0, 0]
    proud = height > np.where(mine, most, tolerance)
    on_seams = np.zeros(across.shape, dtype=bool)
    for _, _, cells in lines:
        on_seams |= cells
    closable = off_plate(height, mine, tolerance) & ~on_seams & ~proud
    boxed = (np.abs(across) <= wide / 2) & (np.abs(upward) <= tall / 2)
    labels, _ = ndimage.label(closable)
    joined = np.isin(labels, np.setdiff1d(np.unique(labels[boxed & closable]), [0])) | boxed
    reach = np.array(size) / 2 * (1 + 2 * CLOSE_GROW) if reach is None else np.array([reach, reach])
    low = np.maximum([across[joined].min() - LIP * step, upward[joined].min() - LIP * step], -reach)
    high = np.minimum([across[joined].max() + LIP * step, upward[joined].max() + LIP * step], reach)
    for way, place, _ in lines:
        side = 1 if abs(way[1]) >= abs(way[0]) else 0  # the region's side a line limits: up for one running across
        other = 1 - side
        sign = np.sign(place) * np.sign(way[side])
        ends = (place - np.sign(place) * step - way[other] * np.array([low[other], high[other]])) / way[side]
        if sign > 0:
            high[side] = min(high[side], ends.min())
        elif sign < 0:
            low[side] = max(low[side], ends.max())
    return [round(float(value), 5) for value in (*low, *high)]


def on_plate(placement, plane):
    """The placement's `at` set on the fitted plane and its `normal` the plane's, its `up` kept square to it."""
    right, up, normal = axes(placement)
    slope_across, slope_up, offset = plane
    at = np.asarray(placement["at"], dtype=float) + offset * normal
    facing = normal - slope_across * right - slope_up * up
    facing = facing / np.linalg.norm(facing)
    upward = up - (up @ facing) * facing
    rounded = lambda vector: [round(float(value), 5) for value in vector]  # noqa: E731
    return dict(placement, at=rounded(at), normal=rounded(facing), up=rounded(upward / np.linalg.norm(upward)))


def plate_point(placement, across, upward, off, plane):
    """A point of the plate (a cell on it, of its part) nearest the placement's middle outside its box, on the fitted
    `plane`: whose finish the closing card takes; None when there is none."""
    right, up, normal = axes(placement)
    wide, tall = placement["size"]
    outside = ~off & ((np.abs(across) > wide / 2) | (np.abs(upward) > tall / 2))
    if not outside.any():
        return None
    nearest = np.argmin(np.where(outside, np.hypot(across, upward), np.inf))
    lying = plane[0] * across.flat[nearest] + plane[1] * upward.flat[nearest] + plane[2]
    point = (np.asarray(placement["at"], dtype=float) + across.flat[nearest] * right + upward.flat[nearest] * up
             + lying * normal)
    return [round(float(value), 5) for value in point]


def measured(placement, mesh, same):
    """(across, up, height off the plate, its part's, its seams, the plate) of a placement's grid (sampled, fitted,
    seams), or None when its plate is not flat round it."""
    tolerance = tolerance_of(placement["size"])
    across, upward, height, mine, facing = sampled(placement, mesh, same)
    plane = fitted(across, upward, height, mine, facing, tolerance)
    if plane is None:
        return None
    height = height - (plane[0] * across + plane[1] * upward + plane[2])
    off = off_plate(height, mine, tolerance)
    return across, upward, height, mine, seams(across, upward, off, across[0, 1] - across[0, 0]), plane


def upright(placement):
    """A pattern's placement with its up the take's own (+y) laid on its face, unless that face lies flat (its +y laid
    on it under half long): the close-up is drawn upright, and the up its probes and ink give on TRELLIS.2's bumps runs
    anywhere (r13holes: the locker's top left vent 59 degrees off its door's up, its bottom right 49)."""
    _, _, normal = axes(placement)
    upward = np.array([0.0, 1.0, 0.0]) - normal[1] * normal
    if np.linalg.norm(upward) < 0.5:
        return placement
    return dict(placement, up=[round(float(value), 5) for value in upward / np.linalg.norm(upward)])


def held(placement, mesh, same, pattern):
    """(placement, None) the placement on its part's plate with its region to close (`closed`, `plate_point`), a
    pattern's up the take's own (upright), or left `open` with why; a pattern moved clear of a seam its box crosses
    (`from`'s `moved`, metres across and up), or (None, why) when it cannot be."""
    turned = upright(placement) if pattern else placement
    found = measured(turned, mesh, same)
    if found is None:
        return dict(placement, open="its plate is not flat round it"), None
    move = moved_clear(found[4], turned["size"])
    if move is None or any(move):
        if not pattern:
            return dict(placement, open="its box crosses a seam or an edge"), None
        right, up, _ = axes(turned) if move else (None, None, None)
        turned = move and dict(turned, at=[round(float(value), 5) for value in
                                           np.asarray(turned["at"], dtype=float) + move[0] * right + move[1] * up],
                               **{"from": dict(turned.get("from", {}), moved=move)})
        found = turned and measured(turned, mesh, same)
        if not found or any(moved_clear(found[4], turned["size"]) or [1]):
            return None, "its box crosses a seam or an edge of its part and cannot be moved clear of it"
    across, upward, height, mine, lines, plane = found
    point = plate_point(turned, across, upward, off_plate(height, mine, tolerance_of(turned["size"])), plane)
    if point is None:
        return dict(placement, open="no plate of its part round it"), None
    return dict(on_plate(turned, plane), closed={
        "box": closed_region(across, upward, height, mine, lines, turned["size"]), "most": BUMP_MOST,
        "plate_point": point}), None


def plate_extent(placement, mesh, same):
    """(low, high) [across, up] of the faces of the placement's part (`same`) on its plate (their middles within
    BUMP_MOST of it, turned its way), from its `at` on its face; None where none is."""
    right, up, normal = axes(placement)
    offset = mesh.triangles_center - np.asarray(placement["at"], dtype=float)
    on = same & (np.abs(offset @ normal) <= BUMP_MOST) & (mesh.face_normals @ normal > np.cos(np.radians(SEAM_TURN)))
    if not on.any():
        return None
    laid = offset[on] @ np.c_[right, up]
    return laid.min(0), laid.max(0)


def plate_holes(placement, mesh, same, shown=None):
    """[[left, bottom, right, top]] across and up from the placement's `at` of each hole through its part's plate (the
    module's HOLE_ rule; one the close-up shows as plate only with `shown`, the close-up's L* at points of the model's
    frame, NaN off it), each grown LIP cells: its plate cast over the whole of its part's extent on it."""
    extent = plate_extent(placement, mesh, same)
    if extent is None:
        return []
    low, high = extent
    step = max(HOLE_STEP, float(np.sqrt(np.prod(high - low + HOLE_STEP) / HOLE_CELLS)))
    across, upward, height, mine, _ = cast(placement, mesh, same, *np.meshgrid(
        np.arange(low[0], high[0] + step / 2, step), np.arange(low[1], high[1] + step / 2, step)))
    through = np.isnan(height) | (height < -HOLE_DEEP)
    plate = mine & (np.abs(height) <= BUMP_MOST)
    seen = None if shown is None else seen_lightness(placement, across, upward, shown)
    labels, _ = ndimage.label(through)
    found = []
    for number, cells in enumerate(ndimage.find_objects(labels), start=1):
        hole = labels[cells] == number
        rows, columns = cells
        if (rows.start < LIP or columns.start < LIP or rows.stop > across.shape[0] - LIP
                or columns.stop > across.shape[1] - LIP):
            continue
        cut = labels == number
        small = max(np.ptp(across[cells][hole]), np.ptp(upward[cells][hole])) + step <= HOLE_MOST
        if not (small and plate[ndimage.binary_dilation(cut, iterations=LIP) & ~cut].all()) and not (
                seen is not None and shown_plate(cut, through, height, mine, seen)):
            continue
        found.append([round(float(value), 5) for value in (
            across[cells][hole].min() - LIP * step, upward[cells][hole].min() - LIP * step,
            across[cells][hole].max() + LIP * step, upward[cells][hole].max() + LIP * step)])
    return found


def seen_lightness(placement, across, upward, shown):
    """The close-up's L* (`shown`) at each cell of the grid `across`, `upward` on the placement's face."""
    right, up, _ = axes(placement)
    points = (np.asarray(placement["at"], dtype=float) + across.reshape(-1, 1) * right
              + upward.reshape(-1, 1) * up)
    return np.asarray(shown(points), dtype=float).reshape(across.shape)


def shown_plate(cut, through, height, mine, seen):
    """Whether the hole `cut` (cells of the plate's grid) is one the close-up shows as its plate (the module's HOLE_
    rule): right through, ringed by its plate, and seen as light as the plate round it."""
    if not (np.isnan(height[cut]) | (height[cut] < -HOLE_THROUGH)).all():
        return False
    ring = ndimage.binary_dilation(cut, iterations=LIP) & ~through
    if not ring.any() or (mine & (height <= BUMP_MOST))[ring].mean() < HOLE_RING:
        return False
    round_it = (ndimage.binary_dilation(cut, iterations=HOLE_SEEN[1])
                & ~ndimage.binary_dilation(cut, iterations=HOLE_SEEN[0]) & ~through)
    inside, plate = seen[cut], seen[round_it]
    if np.isnan(inside).all() or np.isnan(plate).all():
        return False
    return bool(np.nanmedian(plate) >= HOLE_LIGHT and np.nanmedian(inside) >= np.nanmedian(plate) - HOLE_SHOWN)


def in_frame(box, source, target):
    """A box across and up from `source`'s `at` laid across and up from `target`'s (on the same plate)."""
    right, up, _ = axes(source)
    middle = (np.asarray(source["at"], dtype=float) + (box[0] + box[2]) / 2 * right + (box[1] + box[3]) / 2 * up
              - np.asarray(target["at"], dtype=float))
    their_right, their_up, _ = axes(target)
    across, upward = float(middle @ their_right), float(middle @ their_up)
    half_wide, half_tall = (box[2] - box[0]) / 2, (box[3] - box[1]) / 2
    return [round(value, 5) for value in (across - half_wide, upward - half_tall, across + half_wide,
                                          upward + half_tall)]


def shared_plate(first, second):
    """Whether two closed placements lie on one plate: their normals PLATE_SAME alike, each `at` within BUMP_MOST of
    the other's plate (the locker's doors stand a few mm apart: a plate cast twice closed its holes twice)."""
    _, _, normal = axes(first)
    return bool(axes(second)[2] @ normal >= PLATE_SAME
                and abs((np.asarray(second["at"], dtype=float) - np.asarray(first["at"], dtype=float)) @ normal)
                <= BUMP_MOST)


def holes_closed(placements, mesh, sames, shown=None):
    """The placements with each hole TRELLIS.2 cut through a closed one's plate outside every region closed on it
    (plate_holes) closed too: its box in the `also` of the closed placement on that plate (its part's faces the same,
    `sames` a placement's) nearest it, unless it lies wholly in a region closed already (inside_closed); one the
    close-up shows as its plate only with `shown` (plate_holes). r13's locker drew a black dot through each door above
    its vents, 1 to 2 cm outside their closed boxes; a plate is cast once for all its marks."""
    found = [dict(placement, closed=dict(placement["closed"])) if placement.get("closed") else placement
             for placement in placements]
    done = []
    for number, placement in enumerate(found):
        if not placement.get("closed") or any(
                shared_plate(found[other], placement) and np.array_equal(sames[other], sames[number])
                for other in done):
            continue
        done.append(number)
        group = [other for other, each in enumerate(found) if each.get("closed") and shared_plate(placement, each)
                 and np.array_equal(sames[other], sames[number])]
        for hole in plate_holes(placement, mesh, sames[number], shown):
            laid = {other: in_frame(hole, placement, found[other]) for other in group}
            if any(inside_closed(laid[other], found[other]["closed"]) for other in group):
                continue
            nearest = min(group, key=lambda other: np.hypot(laid[other][0] + laid[other][2],
                                                            laid[other][1] + laid[other][3]))
            found[nearest]["closed"] = dict(found[nearest]["closed"],
                                            also=[*found[nearest]["closed"].get("also", []), laid[nearest]])
    return found


def inside_closed(box, closed):
    """Whether a box lies wholly in a closed region's own `box` or in one of its `also`: a hole whose middle alone lay
    in one was left open past it (r15f's locker: the bars through its doors 3 to 4 cm past its vents' boxes)."""
    return any(left <= box[0] and box[2] <= right and bottom <= box[1] and box[3] <= top
               for left, bottom, right, top in [closed["box"], *closed.get("also", [])])


def closed_round(placement, mesh, same, most, reach):
    """A hardware piece's cut (#212, hardware_pieces: its `at` on its face, `normal`, `up` and `size` the blob's square
    core) closed as a mark's plate is: {at, normal, up} set on the plate (on_plate), its `box` (closed_region: every
    cell of its part standing up to `most` closable, to the cut's `reach` of its middle, ending short of a seam), the
    blob's square core pressed past it too where it stands over BUMP_MOST (`pressed`, its `least`: TRELLIS.2 laid
    r13's locker's locks over their doors' edge grooves; stopped at the groove the blob stood beside each lock as a
    lump, a card over the groove hid the door's edge, and the neighbouring door 3.4 mm proud of this one, pressed too,
    drew a white crumpled strip), `most` and `plate_point`; None where its plate is not flat round it or holds no
    point outside its box. Closed to its point, r13's lock blobs stretched their faces from the cut's rim into white
    cracks and starbursts."""
    found = measured(placement, mesh, same)
    if found is None:
        return None
    across, upward, height, mine, lines, plane = found
    point = plate_point(placement, across, upward, off_plate(height, mine, tolerance_of(placement["size"])), plane)
    if point is None:
        return None
    laid = on_plate(placement, plane)
    wide, tall = placement["size"]
    return {"at": laid["at"], "normal": laid["normal"], "up": laid["up"], "most": round(float(most), 5),
            "box": closed_region(across, upward, height, mine, lines, placement["size"], most, reach),
            "pressed": [{"box": [round(float(value), 5) for value in (-wide / 2, -tall / 2, wide / 2, tall / 2)],
                         "least": BUMP_MOST}],
            "plate_point": point}
