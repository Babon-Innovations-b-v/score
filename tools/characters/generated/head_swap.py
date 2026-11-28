"""A generated person's detailed head put on its whole body: the head-and-shoulders model (made from a head close-up)
fitted onto the whole clothed body's soft head, both cut at one level line just under the chin and the jaw (a face and
scalp cut: at the back it runs under the hair), the head's cut edge laid onto the body's, and the head's paint blended
into the body's across a narrow band above the cut. Everything of the body below the cut (its neck, collar, scarf)
stays as the body model made it; the head model gives only the face, scalp, ears and hair.

Inside Blender (CPU):
    blender -b --python head_swap.py -- <body.glb> <head.glb> <least depth> <out.glb> <out transform.json> [<hood> [open]]

The cut's depth under the body's crown (body heights) is read off the swapped result (`chin_under_crown`:
CUT_UNDER_CHIN under the lower of the placed head model's chin and the body's, where the jaw's shade and the hair hide
it), never less than <least depth> (0 for none; a beard's underside can lie under the chin read), and a cut that would
take the chin is refused (`chin_whole`). Cut low on
the neck or inside the collar (0.15 to 0.18, whole person rounds 1 to 7, 2026-11-27), every fix fought the collar, the
old hair lying on it and the seam at once: dark gaps in the collar and a dark line across the neck. <hood>: when the
body's own hood or high collar rises round the neck above the cut, the depth under the crown (body heights) from which
down the body keeps everything round the neck but the neck itself and the throat: its hood stays, the head model's is
dropped. `open` after it: the hood is open in front (a hoodie's, under the chin), so the front is the head's down to the
cut.

The transform JSON holds the head-to-body similarity (scale, rotation, translation) in the glTF frame of the two files,
so anything made on the head model (hair strands, eyes) follows onto the body with the same matrix; the cut's level,
the band and the fit's residual sit beside it. Only the head's vertices within the band above the cut are moved (to
close the seam); everything above the band is the head model under the transform alone.

The fitting, falloff and rasterising pieces are plain numpy (importable without Blender); `main` runs in Blender.
"""
import json
import math
import pathlib
import sys

import numpy as np

ICP_ROUNDS = 40
ICP_KEPT = 0.7  # the share of pairs (the closest) each round fits; the rest are where the two faces truly differ
FIT_POINTS = 8000  # points each side of the fit (a random draw, fixed seed)
START_SCALES = np.arange(0.16, 0.38, 0.02)  # the head model's scales onto the body scanned (its bust ~0.9 high)
SCAN_ROUNDS = 25  # rigid rounds at each scanned scale
# Sizes in the body's heights (the whole body is one person standing, crown to sole).
HEAD_SPAN = 0.13  # crown to chin: the fit's part of both models
TARGET_SPAN = 0.16  # the body's head and neck, for the swap's axis
SNAP_REACH = 0.012  # a head cut-edge point is laid onto the body's cut edge only within this distance (2 cm)
BAND = 0.012  # the shape's band above the cut (2 cm): the head's cut edge laid on the body's eases out across it (the
# cut just under the jaw: wider, the chin and the lips would move with the seam)
# The seam (`seam_shifts`), in body heights: each side's cut edge read as its outer wall's paths (edges facing out from
# the axis: the shells are two walls 3 to 4 mm apart, ragged), a body path's pieces joined across SEAM_BODY_LINK, a
# head path's across SEAM_HEAD_LINK; a head path is laid along its nearest body path in order, its parameter there by
# arc length between anchors (its points within SEAM_ANCHOR, kept in order, and its two ends): laid point by point
# onto the nearest edge, the throat's ragged two-walled edge folded 4.7% of the band's edges (whole person round 6,
# 2026-11-27)
SEAM_ANCHOR = 0.003
SEAM_BODY_LINK = 0.01
SEAM_HEAD_LINK = 0.004
SEAM_BODY_LEAST = 0.005  # body paths shorter than this (strays) are not laid on
SEAM_HEAD_LEAST = 0.003  # head paths shorter than this are not laid
WELD = 1e-6  # vertices this close are one (glTF splits them at UV seams)
SEAM_ROUNDS = 3000  # relaxation rounds of the band's harmonic shift (warm starts take a third)
FOLD_DEGREES = 150.0  # two faces bent past this are folded over each other
SEAM_RELEASES = 120  # rounds of easing the laid points nearest the band's new folds
RELEASED_PER_FOLD = 2  # laid points eased per new fold each round
EASED_SHARE = 0.5  # an eased point keeps this share of its shift
EASED_LEAST = 0.0005  # a shift eased under this (body heights, under 1 mm) lets the point go: it follows the band
PAINT_BAND = 0.015  # the paint's band above the cut (2.5 cm): the head's paint blends from the body's across it (wider,
# the body's soft paint would reach the chin)
NORMAL_AGREE = 0.3  # two surfaces face the same way when their normals' dot is over this (a neck and a collar's
# inside do not)
NORMAL_REACH = 0.004  # within this of the cut (7 mm) the two sides' shading normals are averaged: no shading line
KEEP_RADIUS = 0.12  # the swap holds only within this of the head's axis (20 cm: never the shoulders' outer parts)
HOOD_SLAB = 0.012  # with a hood kept: the neck's parting from the hood read on this slab above the cut (2 cm)
HOOD_ANGLES = 18  # and per this many directions round the axis (20 degrees each)
NECK_RANGE = (0.025, 0.09)  # the parting looked for between these radii from the axis (4 to 15 cm)
FRONT_HALF_ANGLE = 40.0  # with a hood kept: the front (chin, throat) within this many degrees of -y stays the head's
# down to the cut even where no ring parts it from the collar (its faces need not turn outward: the chin's underside)
NECK_FALLBACK = 0.048  # the neck's reach (8 cm) where a hood lies against it with no empty ring between; with a hood
# kept, nothing of the head's under the hood's depth lies farther out, front included: the stairwell woman's open
# puffer collar stood 9 to 13 cm out within 40 to 80 degrees of the front, the head model's copy of it was kept there
# and drawn over the body's as torn shards and black holes (whole person round 5, 2026-11-27)
HOOD_GAP = 0.003  # an empty ring at least this wide (5 mm) parts them; narrower, nothing is round the neck there
TEXEL_SLACK = 0.02  # barycentric slack so a triangle's edge texels are painted too (no unblended rim)
# The chin over the cut (`chin_over_cut`), in body heights: read on slices 4 mm high of the face's middle column (2.7 cm
# wide), up to 13 cm over the cut; the chin is the lowest slice standing 2.5 cm forward of the throat (the woman of
# 2026-11-27: throat 0.015, chin 0.051, 3 cm over the cut)
CHIN_SLICE = 0.0025
CHIN_COLUMN = 0.008
CHIN_REACH = 0.08
CHIN_STEP = 0.015
# The cut's level is read off the swapped result (`chin_under_crown`): scanned down the face's middle column from the
# nose (the column's most forward slice within NOSE_DEPTHS under the crown), the chin's bottom is the first slice
# standing CHIN_BACK behind the nose's front (the throat: the chin stands 1.3 to 1.9 cm behind it, the lips less, the
# throat 3.2 to 4.8 cm; the stairwell and older women's head models and bodies), its front the most forward slice
# within CHIN_WINDOW above it (1.2 cm), read on the head model as placed and on the body, and the cut lies CUT_UNDER_CHIN under the lower of the two. A
# depth typed per person (0.145, read off the head model's own profile) lay on the stairwell woman's chin bottom with no
# margin, and her hood (0.125) dropped the chin above it: her lower lip and chin torn off in every view (2026-11-27).
NOSE_DEPTHS = (0.05, 0.11)
# The middle column is the face's own, through the nose's tip (its most forward point within NOSE_DEPTHS and NOSE_REACH
# of the axis), never the body's axis: the stairwell woman's face stands 0.02 (3.4 cm) to her left of her body's head
# axis, so the axis' column ran down her chin's side, read its front at 0.064 (the chin's own 0.072 to 0.076) and the
# hood's CHIN_HELD reach dropped the chin's front from its bottom to the hood (701 faces): a torn hole under her lower
# lip in every view, though `chin_whole`, reading the same side column, passed (whole person round 9, 2026-11-28).
NOSE_REACH = 0.04
CHIN_DEPTHS = 0.25  # the column is scanned no deeper than this under the crown
CHIN_BACK = 0.025
CHIN_WINDOW = 0.0075
CUT_UNDER_CHIN = 0.005  # 8 mm
# The skirt hung from the head's open edge at the cut (`skirt`, drawn by blender_person): from the edge's points under
# SKIRT_EDGE over the cut, SKIRT_DEPTH down and SKIRT_IN in (body heights; 1.3 cm and 5 mm), under the body's neck
SKIRT_EDGE = 0.004
SKIRT_DEPTH = 0.008
SKIRT_IN = 0.003
CHIN_HELD = 0.006  # with a hood: the front's faces from the chin's bottom up stay the head's this far past the reach
# of the face's middle column from the axis between the chin's bottom and the hood's depth (`face_reach`)


def similarity(source, target, scale=None):
    """The least-squares similarity (scale, rotation 3x3, translation) taking `source` points onto `target` (Umeyama);
    with `scale` given, the best turn and shift at that scale."""
    source_middle, target_middle = source.mean(0), target.mean(0)
    source_centred, target_centred = source - source_middle, target - target_middle
    covariance = target_centred.T @ source_centred / len(source)
    left, singular, right = np.linalg.svd(covariance)
    sign = np.eye(3)
    sign[2, 2] = np.sign(np.linalg.det(left @ right)) or 1.0
    rotation = left @ sign @ right
    if scale is None:
        scale = float(np.trace(np.diag(singular) @ sign) / source_centred.var(0).sum())
    translation = target_middle - scale * rotation @ source_middle
    return scale, rotation, translation


def moved(points, scale, rotation, translation):
    """`points` under the similarity."""
    return scale * points @ rotation.T + translation


def trimmed_icp(source, target, start, nearest, held_of=None, rounds=ICP_ROUNDS, kept=ICP_KEPT, free_scale=True):
    """The similarity taking `source` points onto `target` points from `start` (scale, rotation, translation),
    matched both ways each round (each source point to its nearest target point and each target point to its nearest
    source point, so a free scale neither shrinks nor swells), each way fitting only its `kept` closest pairs; the
    start's scale held unless `free_scale`.
    `nearest(points)` gives a function answering queries' nearest indices among `points`; `held_of(placed)` picks the
    source points taking part where the fit has put them (all when None). Returns (scale, rotation, translation, rms of
    the kept pairs)."""
    scale, rotation, translation = start
    to_target = nearest(target)
    rms = math.inf
    for _ in range(rounds):
        placed = moved(source, scale, rotation, translation)
        held = np.ones(len(source), bool) if held_of is None else held_of(placed)
        taking, placed = source[held], placed[held]
        forward = to_target(placed)
        forward_gaps = np.linalg.norm(target[forward] - placed, axis=1)
        forward_kept = forward_gaps <= np.quantile(forward_gaps, kept)
        backward = nearest(placed)(target)
        backward_gaps = np.linalg.norm(placed[backward] - target, axis=1)
        backward_kept = backward_gaps <= np.quantile(backward_gaps, kept)
        scale, rotation, translation = similarity(
            np.vstack([taking[forward_kept], taking[backward[backward_kept]]]),
            np.vstack([target[forward[forward_kept]], target[backward_kept]]), None if free_scale else scale)
        rms = float(np.sqrt((np.concatenate([forward_gaps[forward_kept], backward_gaps[backward_kept]]) ** 2).mean()))
    return scale, rotation, translation, rms


def lowest(scales, misses):
    """The scale of least miss: the vertex of the parabola through the lowest miss and its neighbours (the lowest
    scale itself at either end of the scan)."""
    best = int(np.argmin(misses))
    if best in (0, len(scales) - 1):
        return float(scales[best])
    curve = np.polyfit(scales[best - 1:best + 2], misses[best - 1:best + 2], 2)
    return float(-curve[1] / (2 * curve[0])) if curve[0] > 0 else float(scales[best])


def chin_over_cut(heights, forward, across):
    """The chin's height over the cut (body heights): of the face's middle column (within CHIN_COLUMN either side), the
    lowest CHIN_SLICE whose front stands CHIN_STEP forward of the throat's (the column's lowest slice over the cut).
    `heights` over the cut and `forward`, `across` in body heights per point (forward toward the face). Refused when
    no slice stands out (no face over the cut)."""
    heights, forward = np.asarray(heights, float), np.asarray(forward, float)
    column = (np.abs(np.asarray(across, float)) < CHIN_COLUMN) & (heights >= 0.0) & (heights < CHIN_REACH)
    slices = np.floor(heights[column] / CHIN_SLICE).astype(int)
    if not len(slices):
        raise ValueError("no head points over the cut in the face's middle column")
    fronts = np.full(slices.max() + 1, -np.inf)
    np.maximum.at(fronts, slices, forward[column])
    throat = fronts[slices.min()]
    standing = np.flatnonzero(fronts > throat + CHIN_STEP)
    if not len(standing):
        raise ValueError("no chin stands forward of the throat over the cut")
    return float(standing[0] * CHIN_SLICE)


def face_column(depths, forward, across):
    """Which points lie on the face's middle column: within CHIN_COLUMN either side of the nose's tip (the most forward
    point within NOSE_DEPTHS under the crown and NOSE_REACH of the axis), down to CHIN_DEPTHS. Refused when no point
    lies where the nose is looked for."""
    depths, forward, across = (np.asarray(values, float) for values in (depths, forward, across))
    nose = (depths >= NOSE_DEPTHS[0]) & (depths < NOSE_DEPTHS[1]) & (np.abs(across) < NOSE_REACH)
    if not nose.any():
        raise ValueError("no nose on the face's middle column")
    middle = across[nose][np.argmax(forward[nose])]
    return (np.abs(across - middle) < CHIN_COLUMN) & (depths >= 0.0) & (depths < CHIN_DEPTHS)


def chin_under_crown(depths, forward, across):
    """The chin's bottom (depth under the crown, body heights) and its front (forward of the axis) on the face's middle
    column (`face_column`): from the nose down, the first CHIN_SLICE standing CHIN_BACK behind the
    nose's front; the chin's bottom is that slice's top, its front the most forward slice CHIN_WINDOW above it. `depths` under the crown, `forward` (toward the face) and
    `across` in body heights per point. Refused when no slice there drops back (no chin on the column)."""
    depths, forward = np.asarray(depths, float), np.asarray(forward, float)
    column = face_column(depths, forward, across)
    slices = np.floor(depths[column] / CHIN_SLICE).astype(int)
    fronts = np.full(slices.max() + 1, -np.inf)
    np.maximum.at(fronts, slices, forward[column])
    upper = np.arange(int(NOSE_DEPTHS[0] / CHIN_SLICE), min(int(NOSE_DEPTHS[1] / CHIN_SLICE), len(fronts)))
    if not len(upper) or not np.isfinite(fronts[upper]).any():
        raise ValueError("no nose on the face's middle column")
    nose = int(upper[np.argmax(fronts[upper])])
    window = int(round(CHIN_WINDOW / CHIN_SLICE))
    for number in range(nose + 1, len(fronts)):
        if np.isfinite(fronts[number]) and fronts[number] < fronts[nose] - CHIN_BACK:
            return float(number * CHIN_SLICE), float(fronts[max(nose, number - window):number].max())
    raise ValueError("no chin drops back to the throat on the face's middle column")


def chin_of(points, axis, crown, height):
    """`chin_under_crown` on points in Blender's frame (z up, the face toward -y): (depth, front) in body heights."""
    return chin_under_crown((crown - points[:, 2]) / height, -(points[:, 1] - axis[1]) / height,
                            (points[:, 0] - axis[0]) / height)


def face_reach(points, axis, crown, height, depths):
    """The farthest the face's middle column (`face_column`) reaches from the axis between `depths` (under the crown,
    body heights, the shallower first), in the points' units; points in Blender's frame (z up, the face toward -y)."""
    depth = (crown - points[:, 2]) / height
    across = points[:, :2] - np.asarray(axis)
    column = face_column(depth, -across[:, 1] / height, across[:, 0] / height)
    column &= (depth >= depths[0]) & (depth <= depths[1])
    if not column.any():
        raise ValueError("no face on the middle column between the chin and the hood")
    return float(np.hypot(across[column, 0], across[column, 1]).max())


def chin_whole(points, axis, crown, height, chin, level):
    """Refuses (SystemExit) a cut that takes the chin: the head as cut (`points`) must still show the chin found
    before the cut (`chin`, its depth and front) within a CHIN_WINDOW, its front no more than CHIN_HELD back, and the
    cut (`level`) must lie at least half CUT_UNDER_CHIN under it."""
    try:
        found = chin_of(points, axis, crown, height)
    except ValueError as missing:
        raise SystemExit(f"the cut took the chin: {missing}") from missing
    depth = (crown - level) / height
    if abs(found[0] - chin[0]) > CHIN_WINDOW or chin[1] - found[1] > CHIN_HELD or depth < chin[0] + CUT_UNDER_CHIN / 2:
        raise SystemExit(f"the cut takes the chin: its bottom {chin[0]:.4f} under the crown and front {chin[1]:.4f}, "
                         f"after the cut {found[0]:.4f} and {found[1]:.4f}, the cut at {depth:.4f}")
    return found


def eased(height, band):
    """The seam's weight at `height` above the cut: 1 at the cut, easing (smoothstep) to 0 at `band`, 0 above."""
    share = np.clip(1.0 - np.asarray(height, float) / band, 0.0, 1.0)
    return share * share * (3.0 - 2.0 * share)


def welded(points):
    """Each vertex's representative (the first vertex at its place, within WELD): glTF splits a mesh's vertices at
    its UV seams, so the faces' own indices never meet across them."""
    _, first, inverse = np.unique(np.round(np.asarray(points) / WELD).astype(np.int64), axis=0, return_index=True,
                                  return_inverse=True)
    return first[inverse.ravel()]


def skirt(points, triangles, low, down, depth, inward):
    """A skirt hung from the open edges of `triangles` whose two points are `low` (per point): each such edge's points
    copied `depth` along `down` (a unit vector) and `inward` towards the edges' middle across it, and the edge joined
    to its copy by two triangles turned as the face the edge borders; (the copies' points, each copy's point, the new
    triangles indexed after `points`). The swap's head and body meet at the cut as two open edges, laid only in part
    where the body's edge hooks back (the stairwell woman's: 43%): still_rig's fan across them hid the slit, and with
    the fan taken off the neck showed a dark line where one saw between the edges to the collar's inside (whole
    person round 11, 2026-11-28)."""
    points = np.asarray(points, float)
    same = welded(points)
    corners = same[np.asarray(triangles)]
    directed = np.vstack([corners[:, [0, 1]], corners[:, [1, 2]], corners[:, [2, 0]]])
    width = len(points)
    keys = directed[:, 0].astype(np.int64) * width + directed[:, 1]
    backs = directed[:, 1].astype(np.int64) * width + directed[:, 0]
    open_edges = np.unique(directed[~np.isin(keys, backs) & np.asarray(low)[directed].all(axis=1)], axis=0)
    if not len(open_edges):
        return np.zeros((0, 3)), np.zeros(0, np.int64), np.zeros((0, 3), np.int64)
    hung, copy_of = np.unique(open_edges, return_inverse=True)
    copy_of = copy_of.reshape(-1, 2) + width
    down = np.asarray(down, float)
    middle = points[hung].mean(axis=0)
    towards = middle - points[hung]
    towards -= np.outer(towards @ down, down)
    towards /= np.maximum(np.linalg.norm(towards, axis=1), 1e-12)[:, None]
    copies = points[hung] + depth * down + inward * towards
    first, second = open_edges[:, 0], open_edges[:, 1]
    faces = np.vstack([np.c_[second, first, copy_of[:, 0]], np.c_[second, copy_of[:, 0], copy_of[:, 1]]])
    return copies, hung, faces


def edges_counted(triangles):
    """The triangles' edges (sorted index pairs, each once) and how many faces share each."""
    pairs = np.sort(np.vstack([triangles[:, [0, 1]], triangles[:, [1, 2]], triangles[:, [2, 0]]]), axis=1)
    return np.unique(pairs, axis=0, return_counts=True)


def chains(pairs):
    """The edge graph `pairs` (k, 2) as ordered vertex paths: each runs between vertices not of two edges (ends and
    branchings); a cycle is opened at one of its vertices."""
    neighbours = {}
    for start, end in np.asarray(pairs, int):
        neighbours.setdefault(start, []).append(end)
        neighbours.setdefault(end, []).append(start)
    walked = set()

    def walk(start, following):
        path = [start, following]
        walked.add(frozenset((start, following)))
        while len(neighbours[path[-1]]) == 2:
            onward = [vertex for vertex in neighbours[path[-1]] if frozenset((path[-1], vertex)) not in walked]
            if not onward:
                break
            walked.add(frozenset((path[-1], onward[0])))
            path.append(onward[0])
        return path
    paths = []
    for only_ends in (True, False):
        for vertex, around in neighbours.items():
            if only_ends and len(around) == 2:
                continue
            paths += [walk(vertex, other) for other in around if frozenset((vertex, other)) not in walked]
    return paths


def along(points):
    """The arc length from a polyline's first point to each of its points."""
    return np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))])


def linked(lines, reach):
    """Polylines (n, >=3 columns, the first three the place) joined end to end, either way round, while two ends lie
    within `reach`, the nearest pair first."""
    lines = [np.asarray(line) for line in lines]
    while True:
        best = None
        for first_number, first in enumerate(lines):
            for second_number, second in enumerate(lines):
                if first_number == second_number:
                    continue
                for first_turned, first_end in ((False, first[-1]), (True, first[0])):
                    for second_turned, second_start in ((False, second[0]), (True, second[-1])):
                        gap = float(np.linalg.norm(first_end[:3] - second_start[:3]))
                        if gap < reach and (best is None or gap < best[0]):
                            best = (gap, first_number, second_number, first_turned, second_turned)
        if best is None:
            return lines
        _, first_number, second_number, first_turned, second_turned = best
        first = lines[first_number][::-1] if first_turned else lines[first_number]
        second = lines[second_number][::-1] if second_turned else lines[second_number]
        lines = [line for number, line in enumerate(lines) if number not in (first_number, second_number)]
        lines.append(np.vstack([first, second]))


def isotonic(values, weights):
    """The non-decreasing sequence nearest `values` in weighted least squares (pooling adjacent violators)."""
    blocks = []
    for value, weight in zip(values, weights):
        blocks.append([value * weight, weight, 1])
        while len(blocks) > 1 and blocks[-2][0] / blocks[-2][1] > blocks[-1][0] / blocks[-1][1]:
            total, mass, count = blocks.pop()
            blocks[-1][0] += total
            blocks[-1][1] += mass
            blocks[-1][2] += count
    return np.concatenate([np.full(count, total / mass) for total, mass, count in blocks])


def on_polyline(queries, line, lengths):
    """Each query's closest point on the polyline `line` (its arc lengths `lengths`): (arc parameter, distance)."""
    starts, steps = line[:-1], np.diff(line, axis=0)
    squared = np.maximum((steps * steps).sum(1), 1e-20)
    share = np.clip(((queries[:, None] - starts[None]) * steps[None]).sum(2) / squared[None], 0.0, 1.0)
    gaps = np.linalg.norm(starts[None] + share[..., None] * steps[None] - queries[:, None], axis=2)
    best = gaps.argmin(1)
    rows = np.arange(len(queries))
    return lengths[best] + share[rows, best] * np.sqrt(squared[best]), gaps[rows, best]


def at_parameter(line, lengths, parameter):
    """The polyline's points at arc parameters `parameter`."""
    step = np.clip(np.searchsorted(lengths, parameter, side="right") - 1, 0, len(line) - 2)
    share = (parameter - lengths[step]) / np.maximum(lengths[step + 1] - lengths[step], 1e-20)
    return line[step] + share[:, None] * (line[step + 1] - line[step])


def opened_at(loop, lengths, parameter):
    """A closed polyline `loop` (its first point its last) opened again at arc parameter `parameter`: it starts and
    ends there."""
    point = at_parameter(loop, lengths, np.array([parameter]))
    after = lengths > parameter
    return np.vstack([point, loop[after][:-1], loop[~after][1:], point]) if after.any() else loop


def unwrapped(parameter, head_lengths, length):
    """Parameters on a closed body loop of `length`, opened at the head path's first point (parameter 0), each moved by
    a whole loop to lie nearest where the head path's arc length says it runs, one way round or the other: (the
    parameters, the way: 1 or -1)."""
    best = None
    for way in (1.0, -1.0):
        expected = head_lengths if way > 0 else length - head_lengths
        turns = np.round((expected - parameter) / length)
        moved = parameter + turns * length
        miss = float(np.abs(moved - expected).sum())
        if best is None or miss < best[0]:
            best = (miss, moved, way)
    return best[1], best[2]


def laid_path(head_line, body_line, anchor, reach, closing=0.0):
    """The head path's points laid along the body path keeping their order: each one's parameter on the body path by
    arc length between anchors (its points within `anchor` of the body path, held in order by an isotonic fit, and
    its two ends). A point is laid when its target falls inside the body path's ends and within `reach`. A body path
    whose ends lie within `closing` is a closed loop (a cut just under the jaw meets the neck as one loop each side),
    closed and opened again where the head path starts, and
    its parameters taken round the loop, never folded back at its ends (opened anywhere else, the isotonic fit pooled
    half the head's loop onto one end: an older woman's edge 3.5% laid). Returns (targets, laid)."""
    closed = len(body_line) > 3 and float(np.linalg.norm(body_line[0] - body_line[-1])) < closing
    if closed:
        body_line = np.vstack([body_line, body_line[:1]])
    lengths = along(body_line)
    head_lengths = along(head_line)
    if closed:
        body_line = opened_at(body_line, lengths, on_polyline(head_line[:1], body_line, lengths)[0][0])
        lengths = along(body_line)
    parameter, gaps = on_polyline(head_line, body_line, lengths)
    weights = 1.0 / (gaps + 1e-4)
    if closed:
        parameter, way = unwrapped(parameter, head_lengths, lengths[-1])
    else:
        way = 1.0 if np.polyfit(head_lengths, parameter, 1, w=weights)[0] >= 0 else -1.0
    anchors = gaps < anchor
    anchors[[0, -1]] = True
    held = np.flatnonzero(anchors)
    parameter = np.interp(head_lengths, head_lengths[held], way * isotonic(way * parameter[held], weights[held]))
    if closed:
        parameter = np.clip(parameter, 0.0, lengths[-1])
        inside = np.ones(len(parameter), bool)
    else:
        inside = (parameter > 1e-9) & (parameter < lengths[-1] - 1e-9)
    targets = at_parameter(body_line, lengths, parameter)
    return targets, inside & (np.linalg.norm(targets - head_line, axis=1) < reach)


def harmonic(count, pairs, fixed, values, rounds, start=None):
    """Shifts (count, 3) over the edge graph `pairs`: `fixed` vertices hold `values`, every other vertex with an edge
    takes its neighbours' mean, relaxed `rounds` times (Jacobi) from `start` (zero when None)."""
    shifts = np.zeros((count, 3)) if start is None else start.copy()
    shifts[fixed] = values[fixed]
    degree = np.bincount(pairs.ravel(), minlength=count).astype(float)
    free = ~fixed & (degree > 0)
    for _ in range(rounds):
        total = np.stack([np.bincount(pairs[:, 0], shifts[pairs[:, 1], axis], count)
                          + np.bincount(pairs[:, 1], shifts[pairs[:, 0], axis], count) for axis in range(3)], 1)
        shifts[free] = total[free] / degree[free, None]
    return shifts


def face_pairs(triangles):
    """The pairs of faces sharing an edge that only they share (m, 2)."""
    count = len(triangles)
    pairs = np.sort(np.vstack([triangles[:, [0, 1]], triangles[:, [1, 2]], triangles[:, [2, 0]]]), axis=1)
    faces = np.tile(np.arange(count), 3)
    order = np.lexsort((pairs[:, 1], pairs[:, 0]))
    pairs, faces = pairs[order], faces[order]
    same = (pairs[1:] == pairs[:-1]).all(1)
    starts = np.flatnonzero(same)
    alone = np.ones(len(starts), bool)
    alone &= ~np.isin(starts + 1, starts)  # not a third face on the edge
    alone &= ~np.isin(starts - 1, starts)
    return np.stack([faces[starts[alone]], faces[starts[alone] + 1]], 1)


def bends(points, triangles, pairs):
    """The bend (degrees) between each face pair's normals."""
    corners = points[triangles]
    normals = np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0])
    normals /= np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-30)
    return np.degrees(np.arccos(np.clip((normals[pairs[:, 0]] * normals[pairs[:, 1]]).sum(1), -1.0, 1.0)))


def outer_paths(pairs, points, normals, axis, least, link):
    """The outer wall's paths among the edges `pairs` (those whose ends' normals face out from the vertical axis at
    `axis`), joined across `link`, the ones at least `least` long; each an index array."""
    middles = points[pairs].mean(1)
    facing = ((middles[:, :2] - np.asarray(axis)) * normals[pairs].sum(1)[:, :2]).sum(1) > 0
    lines = [np.column_stack([points[path], np.array(path, float)]) for path in chains(pairs[facing])]
    return [line[:, 3].astype(int) for line in linked(lines, link) if along(line[:, :3])[-1] >= least]


def seam_laid(points, normals, edge_pairs, body_lines, axis, height, reach):
    """The head's outer cut-edge points laid along the body's outer cut-edge paths (`laid_path`, each head path on its
    nearest body path): (indices, shifts)."""
    indices, shifts = [], []
    for path in outer_paths(edge_pairs, points, normals, axis, SEAM_HEAD_LEAST * height, SEAM_HEAD_LINK * height):
        line = points[path]
        misses = [np.median(on_polyline(line, body, along(body))[1]) for body in body_lines]
        targets, laid = laid_path(line, body_lines[int(np.argmin(misses))], SEAM_ANCHOR * height, reach,
                                  SEAM_BODY_LINK * height)
        indices.append(path[laid])
        shifts.append((targets - line)[laid])
    if not indices:
        return np.zeros(0, int), np.zeros((0, 3))
    indices, shifts = np.concatenate(indices), np.concatenate(shifts)
    _, once = np.unique(indices, return_index=True)  # a vertex two paths share is laid by the first
    return indices[once], shifts[once]


def body_paths(starts, ends, normals, axis, height):
    """The body's outer cut-edge paths (point arrays) from its cut segments and their normals."""
    ends_together = np.vstack([starts, ends])
    owner = welded(ends_together)
    pairs = np.stack([owner[:len(starts)], owner[len(starts):]], 1)
    vertex_normals = np.zeros_like(ends_together)
    np.add.at(vertex_normals, pairs[:, 0], normals)
    np.add.at(vertex_normals, pairs[:, 1], normals)
    paths = outer_paths(pairs, ends_together, vertex_normals, axis, SEAM_BODY_LEAST * height,
                        SEAM_BODY_LINK * height)
    return [ends_together[path] for path in paths]


def seam_shifts(points, triangles, normals, level, band, axis, body_segments, height, reach):
    """The head's points with its cut edge (at z = `level`) laid onto the body's: its outer wall's paths laid in order
    along the body's (`seam_laid`), every other point within `band` above the cut moved by the harmonic shift those
    laid points and the band's still top give it (its inner wall, ragged bits and side walls follow their
    neighbours, never a target of their own); the laid points nearest a fold the move makes (two faces bent past
    FOLD_DEGREES that were not before) keep half their shift (let go under EASED_LEAST) and the band is solved again. `body_segments`: the body's cut
    (starts, ends, normals). Returns (points, laid share of the head's cut-edge vertices, new folds left)."""
    owner = welded(points)
    welded_triangles = owner[triangles]
    edge_pairs, counts = edges_counted(welded_triangles)
    on_cut = (np.abs(points[edge_pairs, 2] - level) < 1e-5 * height).all(1)
    cut_pairs = edge_pairs[(counts == 1) & on_cut]
    summed = np.zeros_like(points)
    np.add.at(summed, owner, normals)
    body_lines = body_paths(*body_segments, axis, height)
    if not len(cut_pairs) or not body_lines:
        return points.copy(), 0.0, 0
    laid, laid_shifts = seam_laid(points, summed, cut_pairs, body_lines, axis, height, reach)
    kept = np.unique(owner)
    in_band = kept[points[kept, 2] < level + band]
    local = -np.ones(len(points), int)
    local[in_band] = np.arange(len(in_band))
    graph = local[edge_pairs]
    reaching_top = (graph >= 0).sum(1) == 1
    graph = graph[(graph >= 0).all(1)]
    fixed = np.zeros(len(in_band), bool)
    fixed[local[edge_pairs[reaching_top]].max(1)] = True  # the band's top row holds still
    values = np.zeros((len(in_band), 3))
    values[local[laid]] = laid_shifts
    held = local[laid]
    fixed[held] = True
    pairs = face_pairs(welded_triangles)
    centres = (points[welded_triangles[pairs[:, 0]]].mean(1) + points[welded_triangles[pairs[:, 1]]].mean(1)) / 2.0
    watched = (centres[:, 2] > level - 1e-5 * height) & (centres[:, 2] < level + band)
    pairs, centres = pairs[watched], centres[watched]
    folded_before = bends(points, welded_triangles, pairs) > FOLD_DEGREES
    shifts, rounds, new = None, SEAM_ROUNDS, np.zeros(0, bool)
    for _ in range(SEAM_RELEASES + 1):
        shifts = harmonic(len(in_band), graph, fixed, values, rounds, shifts)
        moved = points.copy()
        moved[in_band] += shifts
        moved = moved[owner]
        new = (bends(moved, welded_triangles, pairs) > FOLD_DEGREES) & ~folded_before
        still = held[fixed[held]]
        if not new.any() or not len(still):
            break
        distances = np.linalg.norm(points[in_band[still]][:, None] - centres[new][None], axis=2)
        easing = np.unique(still[np.argsort(distances, axis=0)[:RELEASED_PER_FOLD].ravel()])
        values[easing] *= EASED_SHARE
        fixed[easing[np.linalg.norm(values[easing], axis=1) < EASED_LEAST * height]] = False
        rounds = SEAM_ROUNDS // 3
    cut_vertices = np.unique(cut_pairs)
    return moved, float(np.isin(cut_vertices, in_band[held[fixed[held]]]).mean()), int(new.sum())


def texels_of(triangle_uv, size, slack=TEXEL_SLACK):
    """The texel centres inside one UV triangle on a `size` x `size` texture: (columns, rows, barycentrics (n, 3))."""
    corners = np.asarray(triangle_uv, float) * size - 0.5
    low = np.floor(corners.min(0)).astype(int)
    high = np.ceil(corners.max(0)).astype(int)
    low, high = np.clip(low, 0, size - 1), np.clip(high, 0, size - 1)
    columns, rows = np.meshgrid(np.arange(low[0], high[0] + 1), np.arange(low[1], high[1] + 1))
    columns, rows = columns.ravel(), rows.ravel()
    edge_one, edge_two = corners[1] - corners[0], corners[2] - corners[0]
    area = edge_one[0] * edge_two[1] - edge_one[1] * edge_two[0]
    if abs(area) < 1e-12:
        return columns[:0], rows[:0], np.zeros((0, 3))
    offset_x, offset_y = columns - corners[0, 0], rows - corners[0, 1]
    second = (offset_x * edge_two[1] - offset_y * edge_two[0]) / area
    third = (edge_one[0] * offset_y - edge_one[1] * offset_x) / area
    weights = np.stack([1.0 - second - third, second, third], axis=1)
    inside = (weights >= -slack).all(1)
    return columns[inside], rows[inside], weights[inside]


def barycentric(points, corners):
    """Each point's barycentric weights (n, 3) in its triangle `corners` (n, 3, 3), the point projected onto it."""
    edge_one, edge_two = corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0]
    offset = points - corners[:, 0]
    dot_11 = (edge_one * edge_one).sum(1)
    dot_12 = (edge_one * edge_two).sum(1)
    dot_22 = (edge_two * edge_two).sum(1)
    dot_o1 = (offset * edge_one).sum(1)
    dot_o2 = (offset * edge_two).sum(1)
    denominator = np.where(np.abs(dot_11 * dot_22 - dot_12 ** 2) < 1e-20, 1e-20, dot_11 * dot_22 - dot_12 ** 2)
    second = (dot_22 * dot_o1 - dot_12 * dot_o2) / denominator
    third = (dot_11 * dot_o2 - dot_12 * dot_o1) / denominator
    return np.clip(np.stack([1.0 - second - third, second, third], axis=1), 0.0, 1.0)


def bilinear(image, uv):
    """`image` (h, w, c) read at the UVs (n, 2) (Blender's: v up, row 0 at the bottom), bilinear, wrapping clamped."""
    height, width = image.shape[:2]
    x = np.clip(uv[:, 0] * width - 0.5, 0, width - 1.001)
    y = np.clip(uv[:, 1] * height - 0.5, 0, height - 1.001)
    left, bottom = x.astype(int), y.astype(int)
    across, up = (x - left)[:, None], (y - bottom)[:, None]
    return (image[bottom, left] * (1 - across) * (1 - up) + image[bottom, left + 1] * across * (1 - up)
            + image[bottom + 1, left] * (1 - across) * up + image[bottom + 1, left + 1] * across * up)


def gltf_matrix(blender_matrix):
    """A 4x4 transform between Blender's frame (z up) written in the glTF frame (y up) of the files it moves."""
    to_blender = np.array([[1, 0, 0, 0], [0, 0, -1, 0], [0, 1, 0, 0], [0, 0, 0, 1]], float)
    return np.linalg.inv(to_blender) @ blender_matrix @ to_blender


# ---- Blender from here on -------------------------------------------------------------------------------------------


def imported(path, name):
    """The glb's one mesh as a new object called `name`, its transform applied (world coordinates in its data)."""
    import bpy
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    new = [item for item in bpy.data.objects if item not in before]
    meshes = [item for item in new if item.type == "MESH"]
    if len(meshes) != 1:
        raise SystemExit(f"{path}: expected one mesh, found {len(meshes)}")
    mesh = meshes[0]
    mesh.data.transform(mesh.matrix_world)
    mesh.parent = None
    mesh.matrix_world.identity()
    for item in new:
        if item is not mesh:
            bpy.data.objects.remove(item)
    mesh.name = name
    return mesh


def vertices_of(mesh):
    """The mesh's vertex positions (n, 3)."""
    positions = np.zeros(len(mesh.data.vertices) * 3)
    mesh.data.vertices.foreach_get("co", positions)
    return positions.reshape(-1, 3)


def normals_of(mesh):
    """The mesh's vertex normals (n, 3)."""
    normals = np.zeros(len(mesh.data.vertices) * 3)
    mesh.data.vertices.foreach_get("normal", normals)
    return normals.reshape(-1, 3)


def nearest_on(points):
    """A function answering each query point's nearest index among `points` (a KD tree)."""
    from mathutils import kdtree
    tree = kdtree.KDTree(len(points))
    for number, point in enumerate(points):
        tree.insert(point, number)
    tree.balance()

    def answer(queries):
        return np.array([tree.find(query)[1] for query in queries], int)
    return answer


def fitted(body, head):
    """The head's similarity onto the body's head: the head model's head (what the fit puts above the body's chin)
    matched both ways onto the body's head, hair and all. A free scale slides slowly along a long valley, so the scale
    is scanned instead: at each, the best turn and shift (stood crown on crown, centred, then a rigid two-way ICP) and
    its miss; the least miss's scale (a parabola through its neighbours) fitted once more. Returns (scale, rotation,
    translation, rms, crown, middle x, body height)."""
    rng = np.random.default_rng(0)
    body_points, head_points = vertices_of(body), vertices_of(head)
    height = float(np.ptp(body_points[:, 2]))
    crown = float(body_points[:, 2].max())
    chin = crown - HEAD_SPAN * height
    target = body_points[body_points[:, 2] > chin]
    target = target[rng.choice(len(target), min(FIT_POINTS, len(target)), replace=False)]
    source = head_points[rng.choice(len(head_points), min(5 * FIT_POINTS, len(head_points)), replace=False)]
    head_crown = float(head_points[:, 2].max())
    middle = np.median(target, axis=0)

    def held_of(placed):
        held = np.zeros(len(placed), bool)
        above = np.where(placed[:, 2] > chin)[0]
        held[rng.permutation(above)[:FIT_POINTS]] = True
        return held

    def fit_at(scale, rounds):
        upper = source[source[:, 2] > head_crown - HEAD_SPAN * height / scale]
        shift = np.array([middle[0] - scale * np.median(upper[:, 0]), middle[1] - scale * np.median(upper[:, 1]),
                          crown - scale * head_crown])
        return trimmed_icp(source, target, (scale, np.eye(3), shift), nearest_on, held_of, rounds, free_scale=False)

    misses = np.array([fit_at(scale, SCAN_ROUNDS)[3] for scale in START_SCALES])
    print("FIT scan " + " ".join(f"{scale:.2f}:{miss:.5f}" for scale, miss in zip(START_SCALES, misses)), flush=True)
    best = fit_at(lowest(START_SCALES, misses), ICP_ROUNDS)
    print(f"FIT scale {best[0]:.4f}, rms {best[3]:.5f}", flush=True)
    return (*best, crown, float(middle[0]), height)


def split_at(mesh, level):
    """The mesh's faces cut along the level plane z = `level` (no faces removed yet)."""
    import bmesh
    from mathutils import Vector
    built = bmesh.new()
    built.from_mesh(mesh.data)
    bmesh.ops.bisect_plane(built, geom=built.verts[:] + built.edges[:] + built.faces[:], dist=1e-7,
                           plane_co=Vector((0, 0, level)), plane_no=Vector((0, 0, 1)))
    return built


def dropped(built, mesh, keep):
    """The faces `keep` (centre, normal -> bool) refuses deleted, loose vertices too, the cut's split faces made
    triangles again; written back to `mesh`."""
    import bmesh
    gone = [face for face in built.faces if not keep(face.calc_center_median(), face.normal)]
    bmesh.ops.delete(built, geom=gone, context="FACES")
    loose = [vertex for vertex in built.verts if not vertex.link_faces]
    bmesh.ops.delete(built, geom=loose, context="VERTS")
    bmesh.ops.triangulate(built, faces=[face for face in built.faces if len(face.verts) > 3])
    built.to_mesh(mesh.data)
    built.free()
    mesh.data.update()


def cut_segments(mesh, level):
    """The body's open edges along the cut, as (start points, end points, unit normals: their ends' mean)."""
    import bmesh
    built = bmesh.new()
    built.from_mesh(mesh.data)
    built.normal_update()
    pairs = [(tuple(edge.verts[0].co), tuple(edge.verts[1].co), tuple(edge.verts[0].normal + edge.verts[1].normal))
             for edge in built.edges
             if edge.is_boundary and all(abs(vertex.co.z - level) < 1e-5 for vertex in edge.verts)]
    built.free()
    pairs = np.array(pairs, float).reshape(-1, 3, 3)
    normals = pairs[:, 2] / np.maximum(np.linalg.norm(pairs[:, 2], axis=1, keepdims=True), 1e-9)
    return pairs[:, 0], pairs[:, 1], normals


def seam_closed(head, body, level, reach, band, axis):
    """The head's cut edge laid onto the body's (`seam_shifts`) and written back to the head. Returns the share of
    the head's cut edge laid."""
    import bmesh
    built = bmesh.new()
    built.from_mesh(head.data)
    bmesh.ops.triangulate(built, faces=[face for face in built.faces if len(face.verts) > 3])
    triangles = np.array([[vertex.index for vertex in face.verts] for face in built.faces], int)
    built.free()
    height = band / BAND
    points, laid, folds = seam_shifts(vertices_of(head), triangles, normals_of(head), level, band, axis,
                                      cut_segments(body, level), height, reach)
    print(f"SEAM laid {laid:.3f} of the head's cut edge, {folds} new folds in the band", flush=True)
    head.data.vertices.foreach_set("co", points.ravel())
    head.data.update()
    return laid


def image_array(image):
    """The image's pixels (h, w, 4) floats as stored (row 0 at the bottom)."""
    pixels = np.zeros(image.size[0] * image.size[1] * 4, np.float32)
    image.pixels.foreach_get(pixels)
    return pixels.reshape(image.size[1], image.size[0], 4)


def textures_of(mesh):
    """{role: image} of the mesh's one material: its base colour and metal-roughness images."""
    found = {}
    for node in mesh.data.materials[0].node_tree.nodes:
        if node.type != "TEX_IMAGE":
            continue
        linked = [link.to_socket.name for link in node.outputs["Color"].links]
        found["base" if "Base Color" in linked else "metal_rough"] = node.image
    return found


class Surface:
    """The uncut body's surface: the closest point's UV for any query point (a BVH over its triangles)."""

    def __init__(self, mesh):
        from mathutils.bvhtree import BVHTree
        self.points = vertices_of(mesh)
        corners = np.zeros(len(mesh.data.loops), int)
        mesh.data.loops.foreach_get("vertex_index", corners)
        self.triangles = corners.reshape(-1, 3)
        uv = np.zeros(len(mesh.data.loops) * 2)
        mesh.data.uv_layers.active.data.foreach_get("uv", uv)
        self.uv = uv.reshape(-1, 3, 2)
        self.tree = BVHTree.FromPolygons(self.points.tolist(), self.triangles.tolist(), all_triangles=True)

    def uv_at(self, queries, normals, reach):
        """The UV (n, 2) of the body's surface at each query: where the line along the query's normal first meets a
        body face facing its way (within `reach` either side), else its closest surface point."""
        from mathutils import Vector
        located, faces = np.zeros_like(queries), np.zeros(len(queries), int)
        for number, (query, normal) in enumerate(zip(queries, normals)):
            hits = []
            for way in (1.0, -1.0):
                start = Vector(query - way * normal * 1e-5)
                location, face_normal, face, distance = self.tree.ray_cast(start, Vector(way * normal), reach)
                if location is not None and face_normal.dot(Vector(normal)) > NORMAL_AGREE:
                    hits.append((distance, location, face))
            if hits:
                _, location, face = min(hits, key=lambda hit: hit[0])
            else:
                location, _, face, _ = self.tree.find_nearest(query)
            located[number], faces[number] = location, face
        weights = barycentric(located, self.points[self.triangles[faces]])
        return (self.uv[faces] * weights[..., None]).sum(1)


def paint_blended(head, body_surface, body_images, level, band, reach, out_folder, name):
    """The head's texels on the band above the cut blended toward the body's paint at the same place (all body at the
    cut, all head at the band's top), base colour and metal-roughness alike, saved as new images; the body's paint read
    along each texel's normal within `reach`. Returns texels painted."""
    import bpy
    points, normals = vertices_of(head), normals_of(head)
    corners = np.zeros(len(head.data.loops), int)
    head.data.loops.foreach_get("vertex_index", corners)
    triangles = corners.reshape(-1, 3)
    uv = np.zeros(len(head.data.loops) * 2)
    head.data.uv_layers.active.data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 3, 2)
    images = textures_of(head)
    size = images["base"].size[0]
    in_band = np.where((points[triangles, 2] < level + band).any(1))[0]
    columns, rows, places, facing = [], [], [], []
    for triangle in in_band:
        column, row, weights = texels_of(uv[triangle], size)
        columns.append(column)
        rows.append(row)
        places.append(weights @ points[triangles[triangle]])
        facing.append(weights @ normals[triangles[triangle]])
    columns, rows, places = np.concatenate(columns), np.concatenate(rows), np.concatenate(places)
    facing = np.concatenate(facing)
    facing /= np.maximum(np.linalg.norm(facing, axis=1, keepdims=True), 1e-9)
    weight = eased(places[:, 2] - level, band)[:, None]
    body_uv = body_surface.uv_at(places, facing, reach)
    for role, image in images.items():
        pixels = image_array(image)
        theirs = bilinear(body_images[role], body_uv)
        pixels[rows, columns, :3] = pixels[rows, columns, :3] * (1 - weight) + theirs[:, :3] * weight
        blended = bpy.data.images.new(f"{name}_head_{role}", size, size, alpha=True)
        blended.colorspace_settings.name = image.colorspace_settings.name
        blended.pixels.foreach_set(pixels.ravel())
        blended.filepath_raw = str(pathlib.Path(out_folder) / f"{name}_head_{role}.png")
        blended.file_format = "PNG"
        blended.save()
        for material in head.data.materials:
            for node in material.node_tree.nodes:
                if node.type == "TEX_IMAGE" and node.image == image:
                    node.image = blended
    return len(rows)


def shaded_across(mesh, level, reach):
    """The joined mesh's shading normals near the cut made one smooth field across it: each vertex within `reach` of
    the cut takes the mean normal of every vertex (either side) within `reach` of it facing its way, eased back to its own over the
    reach, so the two sides' differing normals draw no line."""
    points, normals = vertices_of(mesh), normals_of(mesh)
    seam_distance = np.abs(points[:, 2] - level)
    near = np.where(seam_distance < reach)[0]
    from mathutils import kdtree
    tree = kdtree.KDTree(len(near))
    for number, index in enumerate(near):
        tree.insert(points[index], number)
    tree.balance()
    shaded = normals.copy()
    for index in near:
        found = [number for _, number, _ in tree.find_range(points[index], reach)
                 if normals[near[number]] @ normals[index] > NORMAL_AGREE]
        mean = normals[near[found]].mean(0)
        share = 1.0 - seam_distance[index] / reach
        blended = normals[index] * (1 - share) + mean / max(np.linalg.norm(mean), 1e-9) * share
        shaded[index] = blended / max(np.linalg.norm(blended), 1e-9)
    mesh.data.normals_split_custom_set_from_vertices(shaded.tolist())
    mesh.data.update()


def transform_record(fit, level, band, laid, texels):
    """The head-to-body transform (Blender and glTF frames) and the cut, as the JSON record."""
    scale, rotation, translation, rms = fit
    matrix = np.eye(4)
    matrix[:3, :3] = scale * rotation
    matrix[:3, 3] = translation
    return {
        "head_to_body_gltf": gltf_matrix(matrix).round(8).tolist(),
        "head_to_body_blender": matrix.round(8).tolist(),
        "scale": round(float(scale), 6),
        "note": ("apply head_to_body_gltf (4x4, column vectors) to points in the head glb's frame to place them in "
                 "the body glb's frame; the head's vertices within the band above the cut were also eased to close "
                 "the seam, everything higher follows the matrix alone"),
        "cut_level_gltf_y": round(level, 6),
        "band": round(band, 6),
        "head_fit_rms": round(float(rms), 6),
        "head_edge_laid_share": round(laid, 4),
        "texels_blended": int(texels),
    }


def neck_gaps(points, axis, level, height):
    """Where a hood or high collar parts from the neck, per direction round the axis (HOOD_ANGLES bins), read on the
    slab just above the cut (HOOD_SLAB high, where both are plain): the middle of the widest empty ring between
    NECK_RANGE's radii (over HOOD_GAP wide); where the hood lies against the neck with no such ring but reaches out
    past two thirds of the range, NECK_FALLBACK; else infinity (nothing round the neck that way). (HOOD_ANGLES,) radii."""
    slab = points[(points[:, 2] > level) & (points[:, 2] < level + HOOD_SLAB * height)]
    across = slab[:, :2] - np.asarray(axis)
    radius = np.hypot(across[:, 0], across[:, 1])
    which = direction_bin(across)
    gaps = np.full(HOOD_ANGLES, np.inf)
    for bin_number in range(HOOD_ANGLES):
        ring = np.sort(radius[which == bin_number])
        ring = ring[(ring > NECK_RANGE[0] * height) & (ring < NECK_RANGE[1] * height)]
        if len(ring) < 2:
            continue
        widths = np.diff(ring)
        widest = int(np.argmax(widths))
        if widths[widest] > HOOD_GAP * height:
            gaps[bin_number] = (ring[widest] + ring[widest + 1]) / 2.0
        elif ring[-1] > NECK_RANGE[1] * height * 0.65:
            gaps[bin_number] = NECK_FALLBACK * height
    return gaps


def direction_bin(across):
    """Each (x, y) offset's direction bin round the axis (0 at the back, the front, -y, in the middle)."""
    angle = np.degrees(np.arctan2(across[..., 0], -across[..., 1]))
    return np.clip(((angle + 180.0) / 360.0 * HOOD_ANGLES).astype(int), 0, HOOD_ANGLES - 1)


def kept_region(level, crown, height, axis, hood, body_points, open_front=False, chin=None):
    """The test (face centre, normal -> bool) of what the head model gives above the cut: within KEEP_RADIUS of the
    head's axis; with `hood` (a depth under the crown, body heights), under that depth only what lies inside the empty
    ring parting the neck from the body's hood or high collar (`neck_gaps`) and within the neck's reach
    (NECK_FALLBACK), so that hood stays the body's. Given a face's normal (the head's faces), only faces turned outward
    count (a neck is, a hood's inside is not), the front (chin and throat, within FRONT_HALF_ANGLE of -y) excepted;
    the body loses all inside the ring. A hood `open_front` (a hoodie's, open under the chin) lies only round the
    sides and back: in the front the head keeps all down to the cut (the hoodie man's chin and beard stand 0.085 out
    under his hood's 0.11, past NECK_FALLBACK: given to the body, his body model's own longer beard stood under the
    head's face as a dark lump, 2026-11-27). The front stays FRONT_HALF_ANGLE wide: opened to 55 to 90 degrees, the
    hood's own front folds beside the jaw were cut and torn (Workbench close-ups, 2026-11-27).
    `chin` (its bottom's z, the face's reach from the axis over it, `face_reach`): the front from the chin's bottom up
    within CHIN_HELD past that reach stays the head's whatever the hood (the chin is face, never neck)."""
    top = crown - hood * height if hood is not None else None
    gaps = neck_gaps(body_points, axis, level, height) if hood is not None else None

    def kept(centre, normal=None):
        across = np.array([centre.x - axis[0], centre.y - axis[1]])
        radius = math.hypot(*across)
        if centre.z < level or radius > KEEP_RADIUS * height:
            return False
        if top is None or centre.z > top:
            return True
        front = abs(math.degrees(math.atan2(across[0], -across[1]))) < FRONT_HALF_ANGLE
        if open_front and front:
            return True
        if chin is not None and front and centre.z >= chin[0] and radius <= chin[1] + CHIN_HELD * height:
            return True
        if radius > min(gaps[direction_bin(across)], NECK_FALLBACK * height):
            return False
        return front or normal is None or normal.x * across[0] + normal.y * across[1] > 0
    return kept


def main():
    import bpy
    from mathutils import Matrix
    arguments = sys.argv[sys.argv.index("--") + 1:]
    body_path, head_path, least_depth, out_glb, out_json = arguments[:5]
    hood = float(arguments[5]) if len(arguments) > 5 else None
    open_front = len(arguments) > 6 and arguments[6] == "open"
    name = pathlib.Path(out_glb).stem
    bpy.ops.wm.read_factory_settings(use_empty=True)
    body = imported(body_path, "body")
    head = imported(head_path, "head")
    *fit, crown, middle_x, height = fitted(body, head)
    matrix = np.eye(4)
    matrix[:3, :3] = fit[0] * fit[1]
    matrix[:3, 3] = fit[2]
    head.data.transform(Matrix(matrix.tolist()))
    head.data.update()
    band = BAND * height
    points = vertices_of(body)
    head_part = points[points[:, 2] > crown - TARGET_SPAN * height]
    axis = (middle_x, float(np.median(head_part[:, 1])))
    chin = chin_of(vertices_of(head), axis, crown, height)
    body_chin = chin_of(points, axis, crown, height)
    cut_depth = max(float(least_depth), max(chin[0], body_chin[0]) + CUT_UNDER_CHIN)
    level = float(crown - cut_depth * height)
    print(f"CHIN head {chin[0]:.4f} (front {chin[1]:.4f}), body {body_chin[0]:.4f} under the crown; cut at "
          f"{cut_depth:.4f}", flush=True)
    held = None if hood is None else (crown - chin[0] * height,
                                      face_reach(vertices_of(head), axis, crown, height, (min(hood, chin[0]), chin[0])))
    kept = kept_region(level, crown, height, axis, hood, points, open_front, held)
    body_surface = Surface(body)
    body_images = {role: image_array(image) for role, image in textures_of(body).items()}
    dropped(split_at(body, level), body, lambda centre, normal: not kept(centre))
    dropped(split_at(head, level), head, kept)
    chin_whole(vertices_of(head), axis, crown, height, chin, level)
    laid = seam_closed(head, body, level, SNAP_REACH * height, band, axis)
    texels = paint_blended(head, body_surface, body_images, level, PAINT_BAND * height, SNAP_REACH * height,
                           pathlib.Path(out_glb).parent, name)
    print(f"SEAM level {level:.4f}, band {band:.4f}, head edge laid {laid:.3f}, texels blended {texels}", flush=True)
    bpy.ops.object.select_all(action="DESELECT")
    body.select_set(True)
    head.select_set(True)
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.join()
    body.name = name
    shaded_across(body, level, NORMAL_REACH * height)
    bpy.ops.export_scene.gltf(filepath=str(out_glb), export_format="GLB", use_selection=True, export_yup=True)
    record = transform_record(fit, level, band, laid, texels)
    record.update({"body": str(body_path), "head": str(head_path), "cut_depth_under_crown": round(cut_depth, 5),
                   "chin_under_crown": {"head": round(chin[0], 5), "body": round(body_chin[0], 5)},
                   "hood_depth_under_crown": hood, "body_height_units": round(height, 6)})
    pathlib.Path(out_json).write_text(json.dumps(record, indent=1))
    print("HEAD SWAP DONE", out_glb, flush=True)


if __name__ == "__main__":
    main()
