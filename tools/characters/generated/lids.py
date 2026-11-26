"""A generated person's lids reshaped to the photo's, its lashes grown and its painted brows regrown as hair (#223).

After `eyes.py` sets a real eyeball behind each painted eye the face still reads as a doll's: TRELLIS.2's lid rims are
thick rubbery ridges of triangles some 3 mm across, the openings taller and rounder than the photo's (white over and
under the iris: a stare), no lashes, and the brows flat paint.

    python -m tools.characters.generated.lids <model.glb> <eyes folder> <close-up photo> <marks.json> <out> \
        --height <m>

`<eyes folder>` is `eyes.py`'s out (eyes.npz, stats.json), `<marks.json>` the photo's landmarks (`marks.py`).

1. **The openings**: each lid opening as its edge's distance from the eyeball's centre at every angle (DEGREES, seen
   from the front). The model's is where the eye shows in front of the head or the socket lies deep (`model_outline`,
   on the floor `eyes.py` pushed back); the photo's is MediaPipe's lid margins (`photo_outline`) laid on the model by
   the iris (`photo_frame`: the photo's iris centre on the eyeball's, scaled between the eyes' distance apart and the
   irises' size, turned by the line between the eyes), never past the ball's silhouette (CORNER_SHARE: the photo's
   inner corner is the caruncle's, past the ball).
2. **Fine skin** (`lids_refined`): the lids' triangles split in four REFINE times round each eye and once more along
   its margin, their neighbours closed (split in two or three, `refined`) so no crack opens; the UVs split alike, so
   the model's own paint stays.
3. **The lids moved** (`reshaped`): each point round an eye moved out or in from the eyeball's centre so the opening's
   edge lies on the photo's (inside the opening scaled, outside by the change fading over FALL_M); the lid made thin,
   its front LID_M in front of the eye's own surface (ball and cornea) with its margin rounded (ROUND_M), the rim's
   inner wall laid from the margin into the eye (the wet line runs there, `eyes.wet_strip`), the socket's floor moved
   across only and sunk behind the ball, the change in depth fading out over DEPTH_FALL_M (further where it is pulled
   back far, DEPTH_SLOPE) and past the ball's silhouette (HOLD_OUT_M). The eyeball stays as `eyes.py` set it.
4. **Lashes** (`lashes`): rooted just in front of each new margin, upper (UPPER_LASHES, denser outward) and lower
   (LOWER_LASHES, sparse), none by the inner corner (LASH_BARE), grown as the face module's lashes
   (`../face/strands.py`: LASH_LENGTH, LASH_CURL, LASH_CORNER, LASH_RADIUS, `lash_line`): out of the margin, curling
   up off the upper lid and down off the lower, the outer lashes swept outward.
5. **Brows**: the model's painted brow (paint darker than the forehead's in a brow's place, `brow_seen`) painted over
   on its own texture with the skin round it as the front view sees it (`unpainted`); the brows regrown as hair
   (`brows`) on the band between the photo's brow marks laid on the model by the same frame as its eye, as many hairs
   as the photo's darkness there says (BROW_DENSITY where it is BROW_FULL_DARK darker than its skin), each turned as
   the face module's brows (`../face/strands.brow_angle`: up at the head, outward along the body, down at the tail,
   the lower hairs up and the upper down) and lying along the skin (its LIFT, RISE, BROW_LENGTH, BROW_RADIUS).
6. The lashes' and the brows' finish is the library's strand finish (`fibre.fibre_of`) fitted to the colour of the
   photo's lashes and brows (their darkest pixels, HAIR_DARKEST: the hair's own colour, not the skin between).

Writes <out>/lids.npz (in the model's own frame and units: the head mesh mended, its points welded across the UV
seams so it shades smooth (the glb's own normals do that on the model), its UVs per triangle corner; the wet line; the
lashes' and brows' strands), <out>/texture.png (the model's texture, its brows painted over), <out>/fibre.json and
<out>/stats.json; prints one line. Drawn by `blender_lids.py`.
"""
import argparse
import importlib
import json
import pathlib

import numpy as np
from PIL import Image
from scipy import ndimage
from skimage.color import rgb2lab

from tools.characters.generated import beard, eyes, fibre

DEGREES = np.arange(0.0, 360.0, 2.0)  # an opening's edge is read at these angles round the eye's centre
SOCKET_M = 0.0005  # the model's opening: where the eye shows, or the head lies this near the eyeball's centre depth
ZONE_M = 0.026  # round each eye's centre (seen from the front) the lids are refined and may move
REFINE = 2  # times each lid triangle is split in four (some 2.8 mm across to 0.7 mm)
MARGIN_REFINE_M = (-0.002, 0.003)  # and once more within this of the opening's edge (to 0.35 mm)
FALL_M = 0.008  # the opening's change fades out over this far out from its edge
CORNER_SHARE = 0.96  # the new opening reaches at most this share of the ball's radius out (the photo's inner corner,
# the caruncle's, lies 15 to 17 mm from the iris, past a 12 mm ball: there the opening showed the socket's black,
# 2026-11-26)
CORNER_SMOOTH = 2.0  # the held edge smoothed over this many of DEGREES' steps
LID_M = 0.0015  # a lid's front stands this far in front of the eye's surface by its margin (a 1 to 2 mm margin)
ROUND_M = 0.0006  # the margin's front rounded over this
GAP_M = 0.0001  # a lid's skin stays this far in front of the eye
SINK_M = 0.0004  # the rim's inner wall runs into the eye to this far inside it (it meets the eye in the tear film's
# line; ended over the eye, the wall's triangles to the floor behind cut across the ball's curve as black slivers,
# 2026-11-26)
WALL_M = 0.0002  # and leans this far in over the eye, seen from the front, from the margin to its end
WALL_BAND_M = 0.002  # the rim's inner wall is what lies this near inside the old edge (deeper in is the socket's
# floor even when it lies shallow: laid on the margin, it folded the lid over itself in black wedges, 2026-11-26)
DEPTH_HOLD_M = 0.002  # the lid lies on the eye this far out from its margin, then
DEPTH_FALL_M = 0.008  # its depth change fades out by this far, or further where the lid is pulled back far:
DEPTH_SLOPE = 2.5  # over this many times the pull at the edge (the eye's corners, 6 to 8 mm in front of the ball, cut
# the light off the eye's sides in a narrow slot, 2026-11-26), up to
DEPTH_FALL_MAX_M = 0.016
MOVE_M = 0.032  # round each eye's centre points move (past the edge and the longest fall)
HOLD_OUT_M = 0.012  # and fades out over this far past the ball's silhouette (faded inside it, the eye's corners stood
# 6 to 8 mm in front of the ball, a cliff and a dark pit between, 2026-11-26)
BALL_EDGE = 0.95  # off the eye (and past this share of its radius) the lid follows the ball's depth here
LIFT_LIMIT_M = 0.009  # a lid is never moved further than this in depth
UPPER_LASHES = 130
LOWER_LASHES = 45
LASH_ROOT_M = (0.0002, 0.0007)  # lashes root this far out from the margin (two or three rows)
LASH_BARE = {"upper": 0.12, "lower": 0.25}  # no lashes on this share of the lid by the inner corner (the punctum)
LASH_OUTWARD = (1.0, 2.2)  # lashes per length of lid, the inner end to the outer
LASH_OUT_DEGREES = {"upper": 25.0, "lower": 30.0}  # a lash leaves the margin this far off straight forward, outward
LASH_SWEEP_DEGREES = 20.0  # the outer lashes swept outward by up to this
LASH_SPREAD_DEGREES = 6.0
BROW_BAND_GROW = 0.35  # the photo's brow band (between its marks) widened by this share of its height each way
BROW_DENSITY = 1.5e6  # hairs a m2 where the photo's brow is fully dark (some 150 a cm2)
BROW_FULL_DARK = 0.35  # the photo's brow this much darker than its skin is fully dense
BROW_SKIN_RING = 0.6  # the photo's skin read round the band, out to this share of its height further
BROW_SOFT_PX = 3.0  # the photo's darkness smoothed over this (pixels) before it sets the density
BROW_PAINT = {"over_m": (0.006, 0.032), "across_m": 0.024, "dark": 0.12, "grow_m": 0.0012, "skin_quantile": 70}
FILL_SIGMAS = (4.0, 8.0, 16.0, 32.0)  # front view pixels: the painted brow filled from the skin round it, near first
HAIR_DARKEST = {"lashes": 5, "brows": 15}  # percent of the darkest pixels a hair's colour is read on
LASH_BAND_M = 0.0015  # the photo's lashes read this far out over the upper margin
SEED = 223


def face_strands():
    """The face module's `strands` (brows and lashes on ICT's face), on the face module's path."""
    eyes.face_modules()
    return importlib.import_module("strands")


def smooth_step(value):
    """0 below 0, 1 above 1, smooth between."""
    clipped = np.clip(value, 0.0, 1.0)
    return clipped * clipped * (3.0 - 2.0 * clipped)


def polar(points, centre):
    """Points' angle (degrees, 0 to 360) and distance round `centre`, seen from the front."""
    offset = points[:, :2] - centre[:2]
    return np.degrees(np.arctan2(offset[:, 1], offset[:, 0])) % 360.0, np.linalg.norm(offset, axis=1)


def edge_at(edge, degrees):
    """An opening's edge (its values at DEGREES) at any angles, interpolated round the circle."""
    return np.interp(np.asarray(degrees) % 360.0, DEGREES, edge, period=360.0)


def ray_hits(polygon, centre):
    """The distance at each of DEGREES where a ray out from `centre` leaves the closed `polygon` (x, y rows)."""
    start, side = polygon, np.roll(polygon, -1, axis=0) - polygon
    offset = start - centre[:2]
    radii = []
    for degrees in DEGREES:
        way = np.array([np.cos(np.radians(degrees)), np.sin(np.radians(degrees))])
        cross = way[0] * side[:, 1] - way[1] * side[:, 0]
        with np.errstate(divide="ignore", invalid="ignore"):
            out = (offset[:, 0] * side[:, 1] - offset[:, 1] * side[:, 0]) / cross
            share = (offset[:, 0] * way[1] - offset[:, 1] * way[0]) / cross
        hit = (share >= 0.0) & (share <= 1.0) & (out > 0.0)
        if not hit.any():
            raise ValueError(f"a ray at {degrees} degrees leaves no lid outline round {centre[:2]}")
        radii.append(out[hit].max())
    return np.array(radii)


def photo_frame(marks, centres, iris_radius_m):
    """The photo's pixels laid on the model round each eye: a function (pixels, eye index) -> model (x, y). The photo's
    iris centre lands on the eyeball's centre, scaled by the geometric mean of the eyes' distance apart (model over
    photo) and the irises' size (the model's iris over the photo's), turned by the line between the eyes (the photo's
    rows go down, the model's y up)."""
    irises = np.array([eye["iris_centre"] for eye in marks["eyes"]], np.float64) * np.array([1.0, -1.0])
    apart = np.linalg.norm(centres[1, :2] - centres[0, :2]) / np.linalg.norm(irises[1] - irises[0])
    sized = iris_radius_m / np.mean([eye["iris_radius"] for eye in marks["eyes"]])
    scale = float(np.sqrt(apart * sized))
    model_way, photo_way = centres[1, :2] - centres[0, :2], irises[1] - irises[0]
    turn = np.arctan2(model_way[1], model_way[0]) - np.arctan2(photo_way[1], photo_way[0])
    rotation = np.array([[np.cos(turn), -np.sin(turn)], [np.sin(turn), np.cos(turn)]])

    def laid(pixels, index):
        offset = np.asarray(pixels, np.float64) * np.array([1.0, -1.0]) - irises[index]
        return centres[index, :2] + scale * offset @ rotation.T

    laid.scale = scale
    return laid


def photo_outline(marks, laid, centres, radius):
    """Each eye's photo opening (its edge's distance at DEGREES round its eyeball's centre), from its lid marks, held
    within CORNER_SHARE of the ball's `radius` (smoothed round the circle over CORNER_SMOOTH steps)."""
    edges = []
    for index, eye in enumerate(marks["eyes"]):
        ring = np.vstack([eye["upper"], eye["lower"][::-1][1:-1]])
        edge = np.minimum(ray_hits(laid(ring, index), centres[index]), CORNER_SHARE * radius)
        edges.append(ndimage.gaussian_filter1d(edge, CORNER_SMOOTH, mode="wrap"))
    return edges


def view_of(depth, box):
    """A depth raster over `box` as a view `eyes.depth_at` reads."""
    xs = box[0] + (np.arange(depth.shape[1]) + 0.5) * eyes.STEP_M
    ys = box[2] + (np.arange(depth.shape[0]) + 0.5) * eyes.STEP_M
    return {"depth": depth, "xs": xs, "ys": ys}


def eye_box(centre):
    """The front view's box round an eye's centre."""
    return (centre[0] - ZONE_M, centre[0] + ZONE_M, centre[1] - ZONE_M, centre[1] + ZONE_M)


def front_view(points, triangles, box, behind):
    """The surface seen from the front in `box` (its triangles in front of depth `behind`): a view."""
    used = (points[:, 2] > behind)[triangles].all(axis=1)
    depth, _ = eyes.raster(points, triangles[used], np.zeros((len(points), 2)), box, eyes.STEP_M)
    return view_of(depth, box)


def model_outline(head, eye, centre):
    """The model's opening round one eye: (its edge's distance at DEGREES, the head's depth just outside it). The
    opening is where the eye shows in front of the head, or the head lies within SOCKET_M of the eyeball's centre
    depth (the socket's floor beside the ball), joined to the eye's middle."""
    head_depth, eye_depth = head["depth"], eye["depth"]
    shows = np.isfinite(eye_depth) & ~(head_depth > eye_depth)
    deep = np.isfinite(head_depth) & (head_depth < centre[2] + SOCKET_M)
    pieces, _ = ndimage.label(shows | deep)
    middle = pieces[np.searchsorted(head["ys"], centre[1]), np.searchsorted(head["xs"], centre[0])]
    if middle == 0:
        raise ValueError(f"the eye at {centre} does not show from the front")
    opening = pieces == middle
    reach = np.arange(0.0, ZONE_M, eyes.STEP_M / 2.0)
    radii, depths = [], []
    for degrees in DEGREES:
        way = np.array([np.cos(np.radians(degrees)), np.sin(np.radians(degrees))])
        cols = np.clip(np.round((centre[0] + reach * way[0] - head["xs"][0]) / eyes.STEP_M).astype(int), 0,
                       opening.shape[1] - 1)
        rows = np.clip(np.round((centre[1] + reach * way[1] - head["ys"][0]) / eyes.STEP_M).astype(int), 0,
                       opening.shape[0] - 1)
        out = np.flatnonzero(~opening[rows, cols])
        radius = reach[out[0]] if len(out) else reach[-1]
        radii.append(radius)
        outside = centre[:2] + (radius + 2.0 * eyes.STEP_M) * way
        depths.append(float(eyes.depth_at(head, [outside[0]], [outside[1]])[0]))
    return np.array(radii), np.array(depths)


def split_sides(triangles, chosen, count):
    """The sides (sorted point pairs) of the `chosen` triangles, each once, and each triangle side's midpoint index
    (count + the side's row; -1 where it is not split): (sides, midpoints (m x 3))."""
    pairs = np.sort(np.stack([triangles[:, [0, 1]], triangles[:, [1, 2]], triangles[:, [2, 0]]], axis=1), axis=2)
    encoded = pairs[..., 0].astype(np.int64) * count + pairs[..., 1]
    sides = np.unique(encoded[chosen].reshape(-1))
    where = np.minimum(np.searchsorted(sides, encoded), max(len(sides) - 1, 0))
    found = (len(sides) > 0) & (sides[where] == encoded) if len(sides) else np.zeros(encoded.shape, bool)
    return np.column_stack([sides // count, sides % count]), np.where(found, count + where, -1)


def refined(points, carried, triangles, chosen):
    """The mesh with the `chosen` triangles split in four at their sides' midpoints (`carried`, per point values such
    as the UVs, halved alike) and every triangle with split sides closed (one split: two triangles, two: three), so no
    side keeps a point one neighbour has and the other lacks: (points, carried, triangles), each triangle wound as the
    one it came from."""
    sides, middles = split_sides(triangles, chosen, len(points))
    points = np.vstack([points, points[sides].mean(axis=1)])
    carried = np.vstack([carried, carried[sides].mean(axis=1)])
    split = middles >= 0
    made = [triangles[split.sum(axis=1) == 0]]
    for count in (1, 2, 3):
        rows = np.flatnonzero(split.sum(axis=1) == count)
        if not len(rows):
            continue
        if count == 1:
            turn = np.argmax(split[rows], axis=1)  # the split side first
        elif count == 2:
            turn = (np.argmin(split[rows], axis=1) + 1) % 3  # the whole side last
        else:
            turn = np.zeros(len(rows), int)
        order = (turn[:, None] + np.arange(3)[None, :]) % 3
        first, second, third = np.take_along_axis(triangles[rows], order, axis=1).T
        one, two, three = np.take_along_axis(middles[rows], order, axis=1).T
        if count == 1:
            made += [np.column_stack([first, one, third]), np.column_stack([one, second, third])]
        elif count == 2:
            made += [np.column_stack([one, second, two]), np.column_stack([first, one, two]),
                     np.column_stack([first, two, third])]
        else:
            made += [np.column_stack([first, one, three]), np.column_stack([one, second, two]),
                     np.column_stack([three, two, third]), np.column_stack([one, two, three])]
    return points, carried, np.vstack(made)


def near_edge(middles, centre, edge, reach):
    """Whether each point lies round the eye in front of its middle, within `reach` (low, high) of its opening's
    edge."""
    degrees, out = polar(middles, centre)
    beyond = out - edge_at(edge, degrees)
    return (middles[:, 2] > centre[2] - ZONE_M / 2.0) & (beyond > reach[0]) & (beyond < reach[1])


def lids_refined(points, carried, triangles, centres, edges):
    """The lids' triangles refined: REFINE times within ZONE_M of each eye, then once more along each opening's edge
    (within MARGIN_REFINE_M of `edges`, each eye's further out of its old and new edge)."""
    for _ in range(REFINE):
        middles = points[triangles].mean(axis=1)
        chosen = np.zeros(len(triangles), bool)
        for centre in centres:
            chosen |= ((np.linalg.norm(middles[:, :2] - centre[:2], axis=1) < ZONE_M)
                       & (middles[:, 2] > centre[2] - ZONE_M / 2.0))
        points, carried, triangles = refined(points, carried, triangles, chosen)
    middles = points[triangles].mean(axis=1)
    chosen = np.zeros(len(triangles), bool)
    for centre, edge in zip(centres, edges):
        chosen |= near_edge(middles, centre, edge, MARGIN_REFINE_M)
    return refined(points, carried, triangles, chosen)


def front_of_eye(eye, centre, radius, x, y):
    """The eye's surface depth at (x, y) and how far the lid may follow it there (1 inside the ball's silhouette,
    fading to 0 over HOLD_OUT_M past it); off the eye (or past BALL_EDGE of its radius), the ball's depth at
    BALL_EDGE."""
    depth = eyes.depth_at(eye, x, y)
    out = np.hypot(np.asarray(x) - centre[0], np.asarray(y) - centre[1])
    rim = centre[2] + radius * np.sqrt(1.0 - BALL_EDGE ** 2)
    depth = np.where(np.isfinite(depth) & (out < BALL_EDGE * radius), depth, rim)
    hold = smooth_step((radius + HOLD_OUT_M - out) / HOLD_OUT_M)
    return depth, hold


def lid_profile(beyond):
    """A lid's front over the eye's surface, `beyond` its margin (metres out, seen from the front): LID_M, its margin
    rounded over ROUND_M."""
    inward = np.clip(ROUND_M - beyond, 0.0, ROUND_M)
    return LID_M - ROUND_M + np.sqrt(ROUND_M ** 2 - inward ** 2)


def moved_across(out, was, wanted, deep, wall):
    """Each point's new distance from the eye's centre: inside the old opening scaled onto the new, outside moved by
    the change fading over FALL_M; a point of the rim's inner wall (`wall`) laid from the new margin in by up to
    WALL_M as it lies `deep` (0 at the margin, 1 at its end)."""
    beyond = out - was
    reach = np.where(beyond < 0.0, out * wanted / was, out + (wanted - was) * (1.0 - smooth_step(beyond / FALL_M)))
    return np.where(wall, wanted - WALL_M * deep, reach)


def moved_depth(depth, beyond, surface, ball, hold, deep, wall, fall):
    """Each point's new depth: the lid's front (`lid_profile` over the eye's `surface`, its clear film and cornea
    included) where it lies by the margin, fading back to its own by `fall` out and by `hold`, never more than
    LIFT_LIMIT_M from it; the rim's inner wall from the margin's foot (LID_M less ROUND_M over the eye) to SINK_M
    inside the `ball` itself (under the clear film, the wall showed through it as black, 2026-11-26) as it lies
    `deep`."""
    lid = surface + lid_profile(beyond)
    fade = hold * (1.0 - smooth_step((beyond - DEPTH_HOLD_M) / (fall - DEPTH_HOLD_M)))
    front = depth + fade * np.clip(lid - depth, -LIFT_LIMIT_M, LIFT_LIMIT_M)
    foot = surface + LID_M - ROUND_M
    inner = depth + hold * (foot + (ball - SINK_M - foot) * deep - depth)
    return np.where(wall, inner, front)


def depth_falls(centre, radius, was_depth, wanted_edge, eye):
    """How far out from the new edge each angle's depth change fades (at DEGREES): DEPTH_FALL_M, or DEPTH_SLOPE times
    the lid's pull back there (the old margin's depth over the lid's front on the eye at the new edge), up to
    DEPTH_FALL_MAX_M."""
    way = np.column_stack([np.cos(np.radians(DEGREES)), np.sin(np.radians(DEGREES))])
    rim = centre[:2] + wanted_edge[:, None] * way
    surface, _ = front_of_eye(eye, centre, radius, rim[:, 0], rim[:, 1])
    return np.clip(DEPTH_SLOPE * (was_depth - surface - LID_M), DEPTH_FALL_M, DEPTH_FALL_MAX_M)


def reshaped(points, floor, centres, radius, outlines, eye_views):
    """The points round each eye moved so its opening is the photo's and its lids are thin (the module's step 3).
    `floor` marks the painted floor `eyes.py` pushed back; it and the socket deeper than LID_EDGE_M behind the old
    margin move across only (and back behind the eye where they would stand in front of it, never forward: laid on the
    margin with the rim's wall, they spanned the opening as a skin over the eye, 2026-11-26); `outlines` each eye's
    (old edge, the head's depth just outside it, new edge); `eye_views` each eye's surface seen from the front, its
    `ball` the eyeball's own (under the clear film and cornea)."""
    moved = points.copy()
    side = np.where(points[:, 0] < centres[:, 0].mean(), 0, 1)
    for index, (centre, (was_edge, was_depth, wanted_edge), eye) in enumerate(zip(centres, outlines, eye_views)):
        rows = np.flatnonzero((side == index) & (points[:, 2] > centre[2] - ZONE_M / 2.0)
                              & (np.linalg.norm(points[:, :2] - centre[:2], axis=1) < MOVE_M))
        degrees, out = polar(points[rows], centre)
        was, wanted = edge_at(was_edge, degrees), edge_at(wanted_edge, degrees)
        behind = (edge_at(was_depth, degrees) - points[rows, 2]) / eyes.LID_EDGE_M
        own_floor = floor[rows] | ((out < was) & ((behind >= 1.0) | (out < was - WALL_BAND_M)))
        wall = (out < was) & ~own_floor
        deep = np.clip(behind, 0.0, 1.0)
        reach = moved_across(out, was, wanted, deep, wall)
        across = centre[:2] + reach[:, None] * np.column_stack([np.cos(np.radians(degrees)),
                                                                np.sin(np.radians(degrees))])
        surface, hold = front_of_eye(eye, centre, radius, across[:, 0], across[:, 1])
        ball, _ = front_of_eye(eye["ball"], centre, radius, across[:, 0], across[:, 1])
        fall = edge_at(depth_falls(centre, radius, was_depth, wanted_edge, eye), degrees)
        depth = moved_depth(points[rows, 2], reach - wanted, surface, ball, hold, deep, wall, fall)
        on_eye = np.isfinite(eyes.depth_at(eye, across[:, 0], across[:, 1])) & ~own_floor & ~wall
        depth = np.where(on_eye, np.maximum(depth, surface + GAP_M), depth)
        moved[rows, :2] = across
        sunk = np.where(np.isfinite(eyes.depth_at(eye, across[:, 0], across[:, 1])),
                        np.minimum(points[rows, 2], ball - 2.0 * eyes.BURIED_M), points[rows, 2])
        moved[rows, 2] = np.where(own_floor, sunk, depth)
    return moved


def pushed_floor(points, moved_from, moved_to):
    """The model's points with `eyes.py`'s floor push applied (each `moved_from` point to its `moved_to`, matched on
    their place to a tenth of a micrometre) and which points it moved."""
    keys = {tuple(key): row for row, key in enumerate(np.round(moved_from / 1e-7).astype(np.int64))}
    rows = np.array([keys.get(tuple(key), -1) for key in np.round(points / 1e-7).astype(np.int64)])
    floor = rows >= 0
    moved = points.copy()
    moved[floor] = moved_to[rows[floor]]
    return moved, floor


def wet_edges(centres, radius, photo_edges, eye_views):
    """Each new opening as `eyes.wet_strip` reads it: a function of angle -> (edge's distance, its margin's depth),
    the margin standing LID_M less ROUND_M over the eye's surface there."""
    made = []
    for centre, edge, eye in zip(centres, photo_edges, eye_views):
        way = np.column_stack([np.cos(np.radians(DEGREES)), np.sin(np.radians(DEGREES))])
        rim = centre[:2] + edge[:, None] * way
        surface, _ = front_of_eye(eye, centre, radius, rim[:, 0], rim[:, 1])
        depth = surface + LID_M - ROUND_M

        def at(degrees, edge=edge, depth=depth):
            return edge_at(edge, degrees), edge_at(depth, degrees)

        made.append(at)
    return made


def lid_span(inner, outer, upper):
    """A lid's angles from its inner corner to its outer (degrees), unwrapped so the way between them passes over the
    eye (`upper`) or under it."""
    span = (outer - inner) % 360.0
    over = 0.0 < (inner + span / 2.0) % 360.0 < 180.0
    return inner, (inner + span if over == upper else inner + span - 360.0)


def lash_roots(count, bare, rng):
    """`count` shares along a lid (0 its inner corner, 1 its outer), none on its `bare` share by the inner corner,
    denser outward (LASH_OUTWARD)."""
    share = np.linspace(0.0, 1.0, 2001)
    weight = np.where(share < bare, 0.0, np.interp(share, [bare, 1.0], LASH_OUTWARD))
    cumulative = np.cumsum(weight) / weight.sum()
    return np.interp((np.arange(count) + rng.random(count)) / count, cumulative, share)


def lid_lashes(head, centre, edge, span, upper, count, rng):
    """One lid's lashes rooted just outside its `edge` along `span` (inner to outer corner's angles), curling up
    (`upper`) or down: (points (count x LASH_POINTS x 3), radius (count x LASH_POINTS))."""
    face = face_strands()
    side = "upper" if upper else "lower"
    along = lash_roots(count, LASH_BARE[side], rng)
    degrees = span[0] + (span[1] - span[0]) * along
    angle = np.radians(degrees)
    radial = np.column_stack([np.cos(angle), np.sin(angle), np.zeros(count)])
    out = edge_at(edge, degrees) + rng.uniform(*LASH_ROOT_M, count)
    roots = np.column_stack([centre[0] + out * radial[:, 0], centre[1] + out * radial[:, 1], np.full(count, np.nan)])
    for step in range(4):  # a root by the margin may read the opening's edge pixel: read it a pixel further out
        missing = ~np.isfinite(roots[:, 2])
        if not missing.any():
            break
        further = roots[missing, :2] + step * eyes.STEP_M * radial[missing, :2]
        roots[missing, 2] = eyes.depth_at(head, further[:, 0], further[:, 1])
    if not np.isfinite(roots[:, 2]).all():
        raise ValueError(f"lash roots round {centre[:2]} are off the head at "
                         f"{np.round(degrees[~np.isfinite(roots[:, 2])], 1).tolist()} degrees")
    corner = np.clip(np.abs(np.cos(angle)) * 1.15 - 0.15, 0.0, 1.0)
    length = rng.uniform(*face.LASH_LENGTH[side], count) * (1.0 - face.LASH_CORNER * corner ** 2)
    curl = face.LASH_CURL[side] * rng.uniform(0.8, 1.2, count)
    tilt = np.radians(LASH_OUT_DEGREES[side] + rng.normal(0.0, LASH_SPREAD_DEGREES, count))
    forward = np.cos(tilt)[:, None] * np.array([0.0, 0.0, 1.0]) + np.sin(tilt)[:, None] * radial
    outward = np.array([np.sign(np.cos(np.radians(span[1]))), 0.0, 0.0])
    sweep = np.radians(LASH_SWEEP_DEGREES * along ** 2)[:, None]
    forward = np.cos(sweep) * forward + np.sin(sweep) * outward
    forward /= np.linalg.norm(forward, axis=1, keepdims=True)
    rising = np.array([0.0, 1.0 if upper else -1.0, 0.0])
    normal = rising - (forward @ rising)[:, None] * forward
    normal /= np.linalg.norm(normal, axis=1, keepdims=True)
    made = np.array([face.lash_line(*frame) for frame in zip(roots, forward, normal, length, curl)])
    return made, np.tile(np.linspace(*face.LASH_RADIUS, face.LASH_POINTS), (count, 1))


def lashes(heads, centres, photo_edges, marks, laid, rng):
    """Both eyes' upper and lower lashes: (counts, points, radius)."""
    points, radii = [], []
    for index, (head, centre, edge) in enumerate(zip(heads, centres, photo_edges)):
        eye = marks["eyes"][index]
        corners = laid(np.array([eye["upper"][0], eye["upper"][-1]]), index) - centre[:2]
        inner, outer = np.degrees(np.arctan2(corners[:, 1], corners[:, 0])) % 360.0
        for upper, count in ((True, UPPER_LASHES), (False, LOWER_LASHES)):
            made, radius = lid_lashes(head, centre, edge, lid_span(inner, outer, upper), upper, count, rng)
            points.append(made)
            radii.append(radius)
    points, radii = np.concatenate(points), np.concatenate(radii)
    return np.full(len(points), points.shape[1]), points.reshape(-1, 3), radii.reshape(-1)


def resampled(line, along):
    """Points at shares `along` of a polyline's length."""
    steps = np.linalg.norm(np.diff(line, axis=0), axis=1)
    reached = np.concatenate([[0.0], np.cumsum(steps)]) / steps.sum()
    return np.column_stack([np.interp(along, reached, line[:, axis]) for axis in range(line.shape[1])])


def brow_band(brow, along, across):
    """Photo pixels in a brow's band: at shares `along` (its inner end to its tail) and `across` (-1 its lower mark,
    1 its upper)."""
    lower = resampled(np.asarray(brow["lower"], np.float64), along)
    upper = resampled(np.asarray(brow["upper"], np.float64), along)
    return lower + (upper - lower) * ((across + 1.0) / 2.0)[:, None]


def photo_lightness(photo):
    """The photo's luminance smoothed over BROW_SOFT_PX: a sampler (column, row) -> lightness."""
    soft = ndimage.gaussian_filter(eyes.luminance(photo), BROW_SOFT_PX)

    def at(pixels):
        return ndimage.map_coordinates(soft, [pixels[:, 1], pixels[:, 0]], order=1, mode="nearest")

    return at


def brow_darkness(brow, lightness, along, across):
    """How dark the photo's brow is at each band place, over its own skin (the band's edge ring's median), as a share
    of BROW_FULL_DARK (0 skin, 1 fully dense)."""
    rng = np.random.default_rng(SEED)
    ring_along = rng.random(4000)
    ring_across = np.sign(rng.random(4000) - 0.5) * (1.0 + 2.0 * BROW_BAND_GROW
                                                    + rng.random(4000) * 2.0 * BROW_SKIN_RING)
    skin = np.median(lightness(brow_band(brow, ring_along, ring_across)))
    dark = (skin - lightness(brow_band(brow, along, across))) / skin
    return np.clip(dark / BROW_FULL_DARK, 0.0, 1.0)


def surface_normal(head, x, y):
    """The head's front's normal at (x, y) from its depth's slope (y up, +z toward the viewer)."""
    step = eyes.STEP_M
    slope_x = (eyes.depth_at(head, x + step, y) - eyes.depth_at(head, x - step, y)) / (2.0 * step)
    slope_y = (eyes.depth_at(head, x, y + step) - eyes.depth_at(head, x, y - step)) / (2.0 * step)
    normal = np.column_stack([-slope_x, -slope_y, np.ones_like(slope_x)])
    return normal / np.linalg.norm(normal, axis=1, keepdims=True)


def brow_hairs(brow, index, laid, lightness, head, rng):
    """One brow's hairs on the head's front (`head`, a view): (points (n x BROW_POINTS x 3), radius (n x points))."""
    face = face_strands()
    lower = laid(np.asarray(brow["lower"], np.float64), index)
    upper = laid(np.asarray(brow["upper"], np.float64), index)
    middle = (lower + upper) / 2.0
    height = np.linalg.norm(resampled(upper, np.linspace(0, 1, 50)) - resampled(lower, np.linspace(0, 1, 50)), axis=1)
    length = np.linalg.norm(np.diff(middle, axis=0), axis=1).sum()
    area = length * height.mean() * (1.0 + 2.0 * BROW_BAND_GROW)
    candidates = int(area * BROW_DENSITY)
    along = rng.random(candidates)
    across = rng.uniform(-1.0 - 2.0 * BROW_BAND_GROW, 1.0 + 2.0 * BROW_BAND_GROW, candidates)
    keep = rng.random(candidates) < brow_darkness(brow, lightness, along, across)
    along, across = along[keep], across[keep]
    roots = laid(brow_band(brow, along, across), index)
    tangent = resampled(middle, np.clip(along + 0.01, 0, 1)) - resampled(middle, np.clip(along - 0.01, 0, 1))
    normal = surface_normal(head, roots[:, 0], roots[:, 1])
    outward = np.column_stack([tangent, np.zeros(len(tangent))])
    outward -= np.einsum("pd,pd->p", outward, normal)[:, None] * normal
    outward /= np.linalg.norm(outward, axis=1, keepdims=True)
    upward = np.cross(normal, outward)
    upward *= np.sign(upward[:, 1])[:, None]
    angle = face.brow_angle(along, np.clip(across, -1.0, 1.0), rng)
    heading = np.cos(angle)[:, None] * outward + np.sin(angle)[:, None] * upward
    part = np.where(along < 0.3, "head", np.where(along < 0.8, "body", "tail"))
    hair_length = rng.uniform(*np.array([face.BROW_LENGTH[name] for name in part]).T)
    reach = np.linspace(0.0, 1.0, face.BROW_POINTS)[None, :] * hair_length[:, None]
    flat = (np.column_stack([roots, np.zeros(len(roots))])[:, None, :] + reach[..., None] * heading[:, None, :])
    flat = flat.reshape(-1, 3)
    skin = eyes.depth_at(head, flat[:, 0], flat[:, 1])
    lift = face.LIFT * (1.0 - np.exp(-reach.reshape(-1) / face.RISE * 3.0))
    points = np.column_stack([flat[:, :2], skin]) + surface_normal(head, flat[:, 0], flat[:, 1]) * lift[:, None]
    points = points.reshape(len(roots), face.BROW_POINTS, 3)
    whole = np.isfinite(points).all(axis=(1, 2))
    radius = np.tile(np.linspace(*face.BROW_RADIUS, face.BROW_POINTS), (int(whole.sum()), 1))
    return points[whole], radius


def brow_box(brow, index, laid):
    """The front view's box round a brow laid on the model, with room for its hairs."""
    placed = laid(np.vstack([brow["upper"], brow["lower"]]), index)
    low, high = placed.min(axis=0) - 0.012, placed.max(axis=0) + 0.012
    return (low[0], high[0], low[1], high[1])


def brows(points, triangles, centres, marks, laid, photo, rng):
    """Both brows' hairs: (counts, points, radius, each brow's hair count)."""
    lightness = photo_lightness(photo)
    made, radii, counts = [], [], []
    for index, brow in enumerate(marks["brows"]):
        head = front_view(points, triangles, brow_box(brow, index, laid), centres[index, 2] - ZONE_M / 2.0)
        hairs, radius = brow_hairs(brow, index, laid, lightness, head, rng)
        made.append(hairs)
        radii.append(radius)
        counts.append(len(hairs))
    made, radii = np.concatenate(made), np.concatenate(radii)
    return np.full(len(made), made.shape[1]), made.reshape(-1, 3), radii.reshape(-1), counts


def brow_seen(points, triangles, uv, texture, centre):
    """The painted brow over one eye seen from the front (BROW_PAINT's `over_m` over the eye, within its `across_m`):
    (the view's paint, its texels, which pixels show the model, which are the brow). The brow is the paint darker
    than the forehead's (its `skin_quantile` lightness) by `dark`, its largest piece, grown by `grow_m`."""
    box = (centre[0] - BROW_PAINT["across_m"], centre[0] + BROW_PAINT["across_m"],
           centre[1] + BROW_PAINT["over_m"][0], centre[1] + BROW_PAINT["over_m"][1])
    used = (points[:, 2] > centre[2] - ZONE_M / 2.0)[triangles].all(axis=1)
    depth, texel = eyes.raster(points, triangles[used], uv, box, eyes.STEP_M)
    paint = eyes.painted(texture, texel)
    lightness = eyes.luminance(paint)
    seen = np.isfinite(depth)
    skin = np.percentile(lightness[seen], BROW_PAINT["skin_quantile"])
    pieces, count = ndimage.label(seen & (lightness < skin * (1.0 - BROW_PAINT["dark"])))
    if not count:
        return paint, texel, seen, np.zeros(seen.shape, bool)
    largest = pieces == 1 + np.argmax(np.bincount(pieces.ravel())[1:])
    grown = ndimage.binary_dilation(largest, iterations=int(round(BROW_PAINT["grow_m"] / eyes.STEP_M))) & seen
    return paint, texel, seen, grown


def filled(paint, known, holes):
    """The `holes` pixels of a picture filled from its `known` ones round them (each the mean of the known pixels
    within FILL_SIGMAS, the nearest first)."""
    result = paint.copy()
    left = holes.copy()
    weight_of = known.astype(np.float64)
    for sigma in FILL_SIGMAS:
        weight = ndimage.gaussian_filter(weight_of, sigma)
        mean = np.stack([ndimage.gaussian_filter(paint[..., channel] * weight_of, sigma) for channel in range(3)],
                        axis=-1) / np.maximum(weight, 1e-9)[..., None]
        reached = left & (weight > 0.05)
        result[reached] = mean[reached]
        left &= ~reached
    return result


def unpainted(points, triangles, uv, texture, centres):
    """The texture with the painted brows painted over (`brow_seen`): filled from the skin round them where the front
    view sees them (the view is the face's own neighbourhood; the texture's atlas puts other islands next to a brow's
    texels) by the skin there that is not dark (a man's lid painted in shade under his brow filled it orange,
    2026-11-26), each brow texel the mean of the filled pixels that show it: (texture, texels painted over)."""
    height, width = texture.shape[:2]
    total = np.zeros((height, width, 3))
    hits = np.zeros((height, width))
    for centre in centres:
        paint, texel, seen, brow = brow_seen(points, triangles, uv, texture, centre)
        lightness = eyes.luminance(paint)
        skin = np.percentile(lightness[seen], BROW_PAINT["skin_quantile"])
        known = seen & ~brow & (lightness >= skin * (1.0 - BROW_PAINT["dark"]))
        colour = filled(paint, known, brow)
        cols = np.clip(np.round(texel[brow][:, 0] * (width - 1)).astype(int), 0, width - 1)
        rows = np.clip(np.round((1.0 - texel[brow][:, 1]) * (height - 1)).astype(int), 0, height - 1)
        np.add.at(total, (rows, cols), colour[brow])
        np.add.at(hits, (rows, cols), 1.0)
    result = texture.copy()
    painted_over = hits > 0
    result[painted_over] = total[painted_over] / hits[painted_over][:, None]
    return result, int(painted_over.sum())


def hair_colour(pixels, darkest):
    """A hair's colour read off photo pixels: the median of their darkest `darkest` percent: (sRGB, CIELAB)."""
    order = np.argsort(eyes.luminance(pixels))
    chosen = pixels[order[:max(1, int(len(order) * darkest / 100.0))]]
    srgb = np.median(chosen, axis=0)
    return srgb, rgb2lab(srgb[None, None])[0, 0]


def lash_pixels(photo, marks, scale):
    """The photo's pixels over each upper lid's margin, out to LASH_BAND_M (the lashes and the shade between)."""
    band = int(round(LASH_BAND_M / scale))
    pixels = []
    for eye in marks["eyes"]:
        line = resampled(np.asarray(eye["upper"], np.float64), np.linspace(0.0, 1.0, 200))
        for rise in range(band):
            place = np.round(line - np.array([0.0, rise])).astype(int)
            pixels.append(photo[place[:, 1], place[:, 0]])
    return np.vstack(pixels)


def brow_pixels(photo, marks):
    """The photo's pixels in both brows' bands (between their marks)."""
    rng = np.random.default_rng(SEED)
    places = np.vstack([brow_band(brow, rng.random(5000), rng.uniform(-1.0, 1.0, 5000)) for brow in marks["brows"]])
    places = np.round(places).astype(int)
    return photo[places[:, 1], places[:, 0]]


def fibres(photo, marks, scale):
    """The lashes' and the brows' strand finishes fitted to the photo's colours."""
    lash = hair_colour(lash_pixels(photo, marks, scale), HAIR_DARKEST["lashes"])
    brow = hair_colour(brow_pixels(photo, marks), HAIR_DARKEST["brows"])
    return {"lashes": fibre.fibre_of(*lash), "brows": fibre.fibre_of(*brow)}


def eye_pieces(eyes_npz, scale):
    """The eyeballs and the cornea's shell as one piece of points and triangles (metres)."""
    pieces = [{"points": eyes_npz[f"{name}.points"] * scale, "triangles": eyes_npz[f"{name}.triangles"]}
              for name in ("eyes", "cornea")]
    return {"points": np.vstack([piece["points"] for piece in pieces]),
            "triangles": np.vstack([pieces[0]["triangles"], pieces[1]["triangles"] + len(pieces[0]["points"])])}


def made(points, triangles, uv, texture, photo, marks, eyes_npz, eye_stats, scale):
    """The lids, lashes and brows made for one model (metres, the model's frame; `scale` the model's units to
    metres, `eyes_npz` and `eye_stats` what `eyes.py` wrote): {points, triangles, uv, wet, lashes, brows, texture,
    fibres, stats}."""
    rng = np.random.default_rng(SEED)
    centres = np.array(eye_stats["eye_centres_m"])
    radius = eye_stats["eye_diameter_mm"] / 2000.0
    pushed, floor = pushed_floor(points, eyes_npz["moved_from"] * scale, eyes_npz["moved_to"] * scale)
    pieces = eye_pieces(eyes_npz, scale)
    eye_views = [front_view(pieces["points"], pieces["triangles"], eye_box(centre), -np.inf) for centre in centres]
    balls = eyes_npz["eyes.points"] * scale
    for view, centre in zip(eye_views, centres):
        view["ball"] = front_view(balls, eyes_npz["eyes.triangles"], eye_box(centre), -np.inf)
    heads = [front_view(pushed, triangles, eye_box(centre), centre[2] - ZONE_M / 2.0) for centre in centres]
    was = [model_outline(head, eye, centre) for head, eye, centre in zip(heads, eye_views, centres)]
    laid = photo_frame(marks, centres, eyes.IRIS_DIAMETER_M / 2.0 * radius * 2.0 / eyes.EYE_DIAMETER_M)
    wanted = photo_outline(marks, laid, centres, radius)
    carried = np.column_stack([uv, floor])
    fine, carried, fine_triangles = lids_refined(pushed, carried, triangles, centres,
                                                 [np.maximum(old[0], new) for old, new in zip(was, wanted)])
    final = reshaped(fine, carried[:, 2] > 1.0 - 1e-9, centres, radius,
                     [(old[0], old[1], new) for old, new in zip(was, wanted)], eye_views)
    removed = eyes.buried(final, fine_triangles, centres, radius)
    kept = np.delete(fine_triangles, removed, axis=0)
    wet = eyes.wet_strip(final, kept, centres[:, :2], wet_edges(centres, radius, wanted, eye_views))
    after = [front_view(final, kept, eye_box(centre), centre[2] - ZONE_M / 2.0) for centre in centres]
    lash_counts, lash_points, lash_radius = lashes(after, centres, wanted, marks, laid, rng)
    brow_counts, brow_points, brow_radius, per_brow = brows(final, kept, centres, marks, laid, photo, rng)
    texture, painted_over = unpainted(pushed, triangles, uv, texture, centres)
    stats = {"photo_scale_mm_per_px": round(laid.scale * 1000, 4),
             "opening_height_mm": {"model": [round(1000 * (edge_at(old[0], 90) + edge_at(old[0], 270)), 2)
                                             for old in was],
                                   "photo": [round(1000 * (edge_at(new, 90) + edge_at(new, 270)), 2)
                                             for new in wanted]},
             "opening_width_mm": {"model": [round(1000 * (edge_at(old[0], 0) + edge_at(old[0], 180)), 2)
                                            for old in was],
                                  "photo": [round(1000 * (edge_at(new, 0) + edge_at(new, 180)), 2) for new in wanted]},
             "triangles": [int(len(triangles)), int(len(kept))], "removed_triangles": int(len(removed)),
             "wet_triangles": int(len(wet["triangles"])), "lashes": int(len(lash_counts)), "brow_hairs": per_brow,
             "brow_texels_painted_over": painted_over}
    welded, index = beard.welded(final, kept)
    joined = index[kept]
    whole = (joined[:, 0] != joined[:, 1]) & (joined[:, 1] != joined[:, 2]) & (joined[:, 2] != joined[:, 0])
    return {"points": welded, "triangles": joined[whole], "uv": carried[:, :2][kept[whole]], "wet": wet,
            "lashes": (lash_counts, lash_points, lash_radius), "brows": (brow_counts, brow_points, brow_radius),
            "texture": texture, "fibres": fibres(photo, marks, laid.scale), "stats": stats}


def written(result, scale, out):
    """The made lids written in the model's own units (metres over `scale`): <out>/lids.npz, texture.png,
    fibre.json, stats.json."""
    arrays = {"head.points": result["points"] / scale, "head.triangles": result["triangles"],
              "head.uv": result["uv"], "wet.points": result["wet"]["points"] / scale,
              "wet.triangles": result["wet"]["triangles"]}
    for name in ("lashes", "brows"):
        counts, points, radius = result[name]
        arrays.update({f"{name}.counts": counts, f"{name}.points": points / scale, f"{name}.radius": radius / scale})
    np.savez_compressed(out / "lids.npz", **arrays)
    Image.fromarray(np.round(np.clip(result["texture"], 0, 1) * 255).astype(np.uint8)).save(out / "texture.png")
    (out / "fibre.json").write_text(json.dumps(result["fibres"], indent=1))
    (out / "stats.json").write_text(json.dumps(result["stats"], indent=1))
    return out / "lids.npz"


def arguments():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("model", type=pathlib.Path)
    parser.add_argument("eyes", type=pathlib.Path, help="eyes.py's out folder (eyes.npz, stats.json)")
    parser.add_argument("photo", type=pathlib.Path)
    parser.add_argument("marks", type=pathlib.Path, help="marks.py's landmarks of the photo")
    parser.add_argument("out", type=pathlib.Path)
    parser.add_argument("--height", type=float, required=True, help="the model's height in metres as drawn")
    return parser.parse_args()


def main():
    options = arguments()
    points, triangles, uv, texture = eyes.loaded(options.model)
    scale = options.height / float(np.ptp(points[:, 1]))
    photo = np.asarray(Image.open(options.photo).convert("RGB"), np.float64) / 255.0
    eyes_npz = dict(np.load(options.eyes / "eyes.npz"))
    eye_stats = json.loads((options.eyes / "stats.json").read_text())
    marks = json.loads(options.marks.read_text())
    result = made(points * scale, triangles, uv, texture, photo, marks, eyes_npz, eye_stats, scale)
    options.out.mkdir(parents=True, exist_ok=True)
    path = written(result, scale, options.out)
    stats = result["stats"]
    print(f"lids: {path}, openings {stats['opening_height_mm']['model']} -> {stats['opening_height_mm']['photo']} "
          f"mm tall, {stats['lashes']} lashes, brow hairs {stats['brow_hairs']}, {stats['wet_triangles']} wet-line "
          f"triangles")


if __name__ == "__main__":
    main()
