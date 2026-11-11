"""Things on the floor moved off what the parting lets them stand on or in (fitting.fitted calls each after the parting;
settle@habitat failed its resting gate on them, 2026-11-11).

    off_edges(stage, place, entries)     each small thing across a flat thing's edge moved wholly on or off it
    apart(stage, place, entries)         each thing reaching into another past the resting check's touch moved out

The parting judges by boxes and lets two stand HELD_MOST inside each other, and knows no rug: habitat's sofa, parted
flush to its slanted wall_11, stood 0.047 m into table lamp 2 (0.041 m by their surfaces, past the resting check's
0.03 m), and its potted plant 5 and table lamp 4 stood across the 2 cm edges of rugs 6 and 7, leaning 4.2 and 4.9
degrees once dropped (the check leans 3 at most).
"""
import math

import numpy as np

# A flat thing on the floor (a rug, a mat) stands no taller than this, metres.
FLAT_TALL = 0.05
# A thing across a flat thing's edge leans more than the resting check allows (triage.LEAN_MOST, degrees) when its
# footprint across the edge is short for the flat thing's height; it is moved wholly on or off it.
LEAN_MOST = 3.0
# Two things on the floor reaching into each other by their boxes more than this every way (the resting check's
# TOLERANCE) are moved apart; a touch less is no overlap to it.
TOUCH = 0.03
# The step, metres, of the moves tried off a flat thing's edge.
EDGE_STEP = 0.01
# Footprint points sampled each way across a thing's foot.
FOOT_POINTS = 7


def flat(box):
    """Whether a laid box (low, high) is a flat thing on the floor: no taller than FLAT_TALL."""
    return float(box[1][1] - box[0][1]) <= FLAT_TALL


def outline(points):
    """[n, 2] the floor outline (x, z) of a flat thing's surface points [n, 3], their convex hull in order: a round
    rug's own, never its box's; None where they span no area (a thing drawn as a line)."""
    from scipy.spatial import ConvexHull, QhullError
    floor = np.unique(np.round(np.asarray(points, float)[:, [0, 2]], 6), axis=0)
    try:
        return floor[ConvexHull(floor).vertices]
    except (QhullError, ValueError):
        return None


def inside_outline(points, ring):
    """[n] whether each floor point (x, z) stands in a convex outline (`ring`, counter-clockwise or not)."""
    edges = np.roll(ring, -1, axis=0) - ring
    cross = edges[None, :, 0] * (points[:, None, 1] - ring[None, :, 1]) - \
        edges[None, :, 1] * (points[:, None, 0] - ring[None, :, 0])
    return (cross >= -1e-9).all(axis=1) | (cross <= 1e-9).all(axis=1)


def foot_points(box):
    """[n, 2] floor points (x, z) across a box's (low, high) footprint, FOOT_POINTS each way, its edges in."""
    xs = np.linspace(float(box[0][0]), float(box[1][0]), FOOT_POINTS)
    zs = np.linspace(float(box[0][2]), float(box[1][2]), FOOT_POINTS)
    return np.array([[x, z] for x in xs for z in zs])


def across_edge(points, rings):
    """Whether floor points stand partly in and partly out of any of the outlines `rings`."""
    return any(0 < int(inside_outline(points, ring).sum()) < len(points) for ring in rings)


def edge_move(box, rings, others, pieces, slanted=()):
    """The least level move [x, y, z] along x or z, by EDGE_STEP up to the box's own footprint, that stands a box
    (low, high) wholly on or off each of the outlines `rings`, reaching into none of `others` or the wall `pieces`
    (boxes) it shares height with by more than TOUCH, nor into a slanted wall (`slanted`, fitting.slants') it was not
    in; None where none does."""
    from score.stages.assembly import fitting
    points, size = foot_points(box), box[1] - box[0]
    near = [other for other in [*others, *pieces] if fitting.tall_together(box, other)]
    tries = sorted(((step * EDGE_STEP, axis, sign) for axis in (0, 2) for sign in (1.0, -1.0)
                    for step in range(1, int(math.ceil(float(size[axis]) / EDGE_STEP)) + 1)), key=lambda item: item[0])
    for distance, axis, sign in tries:
        move = np.zeros(3)
        move[axis] = sign * distance
        if across_edge(points + move[[0, 2]], rings):
            continue
        if any(fitting.depths(box[0] + move, box[1] + move, other).min() > TOUCH for other in near):
            continue
        if fitting.in_slants((box[0] + move, box[1] + move), slanted) and not fitting.in_slants(box, slanted):
            continue
        return move
    return None


def leans(box, tall):
    """Whether a thing (its box) across the edge of a flat thing `tall` metres high would lean past LEAN_MOST: that
    height over the thing's shorter footprint side."""
    size = box[1] - box[0]
    return math.degrees(math.atan2(float(tall), max(float(min(size[0], size[2])), 1e-9))) > LEAN_MOST


def laid_boxes(stage, place, entries):
    """{name: box (low, high)} of the entries laid and standing on the stage, none hung from the roof (`under roof`)."""
    from score.stages.assembly import fitting
    found = {}
    for entry in entries:
        if entry.get("under roof"):
            continue
        path = f"/{place}/Objects/{entry['name']}"
        if stage.GetPrimAtPath(path) and stage.GetPrimAtPath(path).IsActive():
            found[entry["name"]] = fitting.world_box(stage, path)
    return found


def wall_pieces(stage, place):
    """The boxes of the place's straight wall pieces (fitting.statics)."""
    from score.stages.assembly import fitting
    return [box for name, box in fitting.statics(fitting.walls(stage, place)) if name.split("_")[0] == "wall"]


def off_edges(stage, place, entries):
    """Each thing on the floor (`entries`, nothing holding them) standing across the edge of a flat one (a rug: one
    no taller than FLAT_TALL, by its outline on the floor) and short enough across it to lean past LEAN_MOST moved the
    least way along x or z that stands it wholly on or off every one, clear of the rest (edge_move), where one does;
    the fits [{name, how "off edge", ...}]."""
    from score.stages.assembly import fitting
    boxes = laid_boxes(stage, place, entries)
    rings = {name: ring for name, box in boxes.items() if flat(box)
             and (ring := outline(fitting.surface_points(stage, f"/{place}/Objects/{name}"))) is not None}
    pieces, slanted, fits = wall_pieces(stage, place), fitting.slants(stage, place), []
    for name, box in sorted(boxes.items()):
        if flat(box) or float(box[0][1]) > FLAT_TALL:
            continue
        crossed = [flat_name for flat_name, ring in rings.items() if across_edge(foot_points(box), [ring])]
        if not any(leans(box, boxes[flat_name][1][1] - boxes[flat_name][0][1]) for flat_name in crossed):
            continue
        move = edge_move(box, list(rings.values()), [other for other_name, other in boxes.items()
                                                      if other_name != name and other_name not in rings], pieces,
                         slanted)
        if move is None:
            continue
        path = f"/{place}/Objects/{name}"
        foot = fitting.foot_middle(*box)
        fitting.moved_by(stage.GetPrimAtPath(path), foot, 1.0, foot + move)
        boxes[name] = fitting.world_box(stage, path)
        entry = next(entry for entry in entries if entry["name"] == name)
        fits.append(fitting.laid_fit(stage, path, entry, "off edge", None, np.linalg.norm(move), 1.0,
                                     f"moved {float(np.linalg.norm(move)):.2f} m off a rug's edge it stood across"))
    return fits


def apart(stage, place, entries):
    """Each pair of things on the floor (`entries`, nothing holding them; flat ones aside) sharing height and reaching
    into each other by their boxes more than TOUCH every way and HELD_MOST at most (the parting's leave): the one with
    the smaller footprint moved the least way along x or z out of the other, reaching into nothing else it shares
    height with by more than TOUCH, where that is HELD_MOST at most; the fits [{name, how "apart", ...}]."""
    from score.stages.assembly import fitting
    boxes = {name: box for name, box in laid_boxes(stage, place, entries).items() if not flat(box)}
    pieces, slanted, fits = wall_pieces(stage, place), fitting.slants(stage, place), []
    names = sorted(boxes)
    for number, first in enumerate(names):
        for second in names[number + 1:]:
            one, other = boxes[first], boxes[second]
            reach = float(fitting.depths(*one, other).min()) if fitting.tall_together(one, other) else 0.0
            if not TOUCH < reach <= fitting.HELD_MOST:
                continue
            area = {name: float(np.prod((box[1] - box[0])[[0, 2]])) for name, box in ((first, one), (second, other))}
            mover, still = (first, second) if area[first] <= area[second] else (second, first)
            move = out_move(boxes[mover], boxes[still], [box for name, box in boxes.items()
                                                         if name not in (mover, still)], pieces, slanted)
            if move is None:
                continue
            path = f"/{place}/Objects/{mover}"
            foot = fitting.foot_middle(*boxes[mover])
            fitting.moved_by(stage.GetPrimAtPath(path), foot, 1.0, foot + move)
            boxes[mover] = fitting.world_box(stage, path)
            entry = next(entry for entry in entries if entry["name"] == mover)
            fits.append(fitting.laid_fit(stage, path, entry, "apart", [still], np.linalg.norm(move), 1.0,
                                         f"moved {float(np.linalg.norm(move)):.2f} m out of {still}, laid "
                                         f"{reach:.2f} m inside it"))
    return fits


def out_move(box, other, rest, pieces, slanted=()):
    """The least move [x, y, z] along x or z that takes a box (low, high) flush out of `other`, HELD_MOST at most,
    reaching into none of `rest` or the wall `pieces` it shares height with by more than TOUCH, nor into a slanted wall
    (`slanted`, fitting.slants') it was not in; None where none does."""
    from score.stages.assembly import fitting
    near = [found for found in [*rest, *pieces] if fitting.tall_together(box, found)]
    tries = []
    for axis in (0, 2):
        tries.append((float(other[1][axis] - box[0][axis]), axis, 1.0))
        tries.append((float(box[1][axis] - other[0][axis]), axis, -1.0))
    for distance, axis, sign in sorted(tries):
        if distance > fitting.HELD_MOST:
            continue
        move = np.zeros(3)
        move[axis] = sign * distance
        if any(fitting.depths(box[0] + move, box[1] + move, found).min() > TOUCH for found in near):
            continue
        if not fitting.in_slants((box[0] + move, box[1] + move), slanted) or fitting.in_slants(box, slanted):
            return move
    return None
