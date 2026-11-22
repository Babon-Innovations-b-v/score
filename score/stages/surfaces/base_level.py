"""The bake's paint with a take's base counted level within 3 cm through its standing height, as its feet are.

place_line.levelled_feet counts a foot down within a hundredth of the take's size, at most FOOT_TOLERANCE_METRES (the
resting check's 3 cm) through its standing height, but hands its base steps (flattened_base, sloped_base,
resting_base) the hundredth with no cap. On a large take a hundredth is far past 3 cm: base's large hangar (0.84 m)
and spacecraft (0.25 m) kept base corners 34 to 60 cm up, which make_chunky's own levelling brought down less the
4 and 8 cm its level corner sank, and surfaces-check's "stands level" (bake_check.STANCE_GAP, 3 cm) failed both
(env1, 2026-11-12). Here each base step's tolerance is capped as the feet's is; a take whose hundredth is under 3 cm,
or whose base has no corner or plane past 3 cm, levels exactly as before.

A take its feet step stands on ON_FEET feet or more is on its feet, and its base steps leave it as its feet stand: they
are for a base that is one piece (a rack on a middle part, a hut's sloping floor, a cabinet's plinth rim), and on a
take on its feet the quadrant with no foot under it is an overhang. old_station's rover stood on its wheels and its
docking leg (five feet) and flattened_base brought its front quadrant, the tube's underside 11.7% of its size up beside
the leg, down to the floor: a sheet hanging off its front to the ground (score #156, 2026-11-22).

A take whose feet but its lowest, FLOOR_FEET or more, lie in one plane within the feet's tolerance stands on that plane:
four or more feet agreeing on a plane are the model's own floor (three always share one), so it is turned, at most
FLOOR_TURN degrees, until that plane is level, and its lone lower foot is cut at it (on_floor), never the others
stretched down to the lone one. The rover's four wheels lie within 0.17% of its size of one plane 7.5 degrees off
level, its docking leg 9.6% below it; the feet step stretched the wheels 3.5 to 7.6% of its size down to the leg,
teardrops (score #156, 2026-11-22). Its faces are kept within its finished model's box turned as it was (boxed).

Run, never imported, by inside/paint_fit.py (the bake's card job, ../bake_fitted.py): its `paint-take` is place_line's
with levelled_feet held as this module's, so place_line.py and paint_take.py, in the code of every row reaching
route_bake.py, do not move.
"""
import contextlib
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.append(str(HERE))

import place_line  # noqa: E402
import prop_env  # noqa: E402

BASE_STEPS = ("flattened_base", "sloped_base", "resting_base")
# The feet a take stands on with its base left as they stand (a stool's three).
ON_FEET = 3
PAINTS_LEVEL = place_line.levelled_feet
# The feet besides the lowest that make a floor when they share one plane (three always do), and the most a take is
# turned onto it: past it a plane of feet is no floor the take was meant to stand on (tumble.DEGREES, the bake's own
# limit for a take off square).
FLOOR_FEET, FLOOR_TURN = 4, 10.0
# The faces within this many degrees of +y face up (up_tilt).
UP_FACES = 25.0
# Each turn onto a floor the paint made of the take being painted: {"turn": 4x4 matrix, "degrees", "cut"} (on_floor).
TURNS = []


def capped(step, cap):
    """A base step (its tolerance and most its last two arguments) with its tolerance at most `cap`."""
    return lambda points, *rest: step(points, *rest[:-2], min(rest[-2], cap), rest[-1])


def capped_plane(step, cap):
    """sloped_base as it is, and only where it left the base as it was, again with its tolerance at most `cap`: its
    tolerance is also how near the plane its cells must lie, so capped alone it finds no plane on a base it brought
    down before (base's square module, 1.8% of its size over a plane its cells lie within a hundredth of)."""
    def sloped(points, *rest):
        found, record = step(points, *rest)
        return (found, record) if record["rise"] is not None else capped(step, cap)(points, *rest)
    return sloped


def left(step):
    """A base step (its tolerance its next to last argument) that moves nothing: no gap passes its tolerance."""
    return lambda points, *rest: step(points, *rest[:-2], float("inf"), rest[-1])


@contextlib.contextmanager
def base_left():
    """place_line's base steps leaving every base as it stands while held (left)."""
    kept = {name: getattr(place_line, name) for name in BASE_STEPS}
    for name, step in kept.items():
        setattr(place_line, name, left(step))
    try:
        yield
    finally:
        for name, step in kept.items():
            setattr(place_line, name, step)


@contextlib.contextmanager
def capped_base(cap):
    """place_line's base steps with their tolerance (model units) at most `cap` while held (capped, capped_plane);
    as they are for None."""
    kept = {name: getattr(place_line, name) for name in BASE_STEPS}
    if cap is not None:
        for name, step in kept.items():
            setattr(place_line, name, (capped_plane if name == "sloped_base" else capped)(step, cap))
    try:
        yield
    finally:
        for name, step in kept.items():
            setattr(place_line, name, step)


def floor_plane(lows, tolerance):
    """The plane y = a + b x + c z through the points `lows` (each foot's lowest), as (a, b, c), when every one lies
    within `tolerance` of it; else None."""
    across = np.c_[np.ones(len(lows)), lows[:, 0], lows[:, 2]]
    plane = np.linalg.lstsq(across, lows[:, 1], rcond=None)[0]
    return plane if np.abs(across @ plane - lows[:, 1]).max() <= tolerance else None


def floor_turn(plane, pivot):
    """The 4x4 turn about `pivot` that lays the plane (a, b, c) level."""
    import trimesh
    normal = np.array([-plane[1], 1.0, -plane[2]])
    turn = trimesh.geometry.align_vectors(normal / np.linalg.norm(normal), [0.0, 1.0, 0.0])
    return trimesh.transformations.translation_matrix(pivot) @ turn @ trimesh.transformations.translation_matrix(-pivot)


def up_tilt(points, faces):
    """How far off level, in degrees, the faces of a mesh facing up (within UP_FACES degrees of +y) face on the whole:
    their area-weighted mean normal's angle from +y; 0 for none."""
    corners = points[np.asarray(faces)]
    normals = np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0])  # each twice its face's area
    lengths = np.linalg.norm(normals, axis=1)
    up = normals[(lengths > 0) & (normals[:, 1] > np.cos(np.radians(UP_FACES)) * lengths)].sum(axis=0)
    return float(np.degrees(np.arctan2(np.hypot(up[0], up[2]), up[1]))) if up[1] > 0 else 0.0


def on_floor(vertices, faces, band, link, tolerance, most):
    """feet.level's arguments; the take turned onto its floor and its lone foot cut at it (vertices, its record as
    feet.level's, the turn in TURNS) when its feet but the lowest, FLOOR_FEET or more, lie within `tolerance` of one
    plane at most FLOOR_TURN degrees off level, its lowest foot more than `tolerance` and at most `most` under that
    plane, nothing else under it, and the faces facing up no further off level turned than as made (up_tilt: its own
    up is the reference; hangar's control desk front, its feet on a plane 7.1 degrees off, would have had its top
    tipped from 3.2 to 9.5 degrees); else None. The lone foot is cut at the plane: every point within `link` across of
    the foot and under the plane is laid on it."""
    import feet
    from scipy.spatial import cKDTree
    points = np.array(vertices, dtype=np.float64)
    surface = feet.surface_points(points, faces)
    found = feet.feet(surface, band, link)
    if len(found) < FLOOR_FEET + 1:
        return None
    lows = np.array([surface[members][np.argmin(surface[members, 1])] for members, _ in found])
    plane = floor_plane(lows[1:], tolerance)
    if plane is None or np.degrees(np.arctan(np.hypot(plane[1], plane[2]))) > FLOOR_TURN:
        return None
    pivot = lows[1:].mean(axis=0)
    turn = floor_turn(plane, pivot)
    turned = points @ turn[:3, :3].T + turn[:3, 3]
    lone = surface[found[0][0]] @ turn[:3, :3].T + turn[:3, 3]
    level = pivot[1]
    near, _ = cKDTree(lone[:, [0, 2]]).query(turned[:, [0, 2]], k=1, distance_upper_bound=link)
    under = turned[:, 1] < level
    cut = level - lone[:, 1].min()
    if cut > most or cut <= tolerance or (turned[~np.isfinite(near) & under, 1] < level - tolerance).any():
        return None
    if up_tilt(turned, faces) > up_tilt(points, faces):
        return None
    turned[np.isfinite(near) & under, 1] = level
    degrees = float(np.degrees(np.arctan(np.hypot(plane[1], plane[2]))))
    TURNS.append({"turn": turn, "degrees": round(degrees, 2), "cut": float(cut)})
    gaps = [round(height - found[0][1], 6) for _, height in found]
    return turned, {"feet": len(found), "gaps": gaps, "levelled": [], "refused": []}


@contextlib.contextmanager
def floored():
    """feet.level turning a take onto its floor where on_floor finds one while held; as it is elsewhere."""
    import feet
    level = feet.level
    feet.level = lambda *arguments: on_floor(*arguments) or level(*arguments)
    try:
        yield
    finally:
        feet.level = level


def boxed(write_parts):
    """labels.write_parts with the finished model's box, when the take was turned onto its floor (TURNS), widened to
    hold that box turned as the take was: its faces cut to the box unturned, a turned take's lost its corners'."""
    def written(mesh, labels, order, part_of, face_region, final_bounds, out):
        if TURNS:
            corners = np.array([[x, y, z] for x in final_bounds[:, 0] for y in final_bounds[:, 1]
                                for z in final_bounds[:, 2]])
            turn = np.linalg.multi_dot([np.eye(4), np.eye(4), *(made["turn"] for made in reversed(TURNS))])
            turned = corners @ turn[:3, :3].T + turn[:3, 3]
            final_bounds = np.array([np.minimum(final_bounds[0], turned.min(axis=0)),
                                     np.maximum(final_bounds[1], turned.max(axis=0))])
        return write_parts(mesh, labels, order, part_of, face_region, final_bounds, out)
    return written


def turned_report(report, size):
    """The paint's report with each turn onto its floor (TURNS: its degrees, the lone foot's cut as a share of `size`),
    when there was one."""
    if not TURNS:
        return report
    return dict(report, turned=[made["degrees"] for made in TURNS], cut=[round(made["cut"] / size, 4) for made in TURNS])


def levelled_feet(vertices, faces, tall=None):
    """place_line.levelled_feet with each base step's tolerance at most FOOT_TOLERANCE_METRES through the standing
    height `tall` (metres), as its feet's is; as there when `tall` is unknown. A take on ON_FEET feet or more has its
    feet levelled and its base left as they stand (base_left), its report saying so in `base_left`. The report as
    there. A take on its floor is turned onto it, its lone foot cut (on_floor), its report saying so in `turned` (each turn's
    degrees) and `cut` (each cut, a share of its size)."""
    import feet
    height, diagonal = feet.model_scale(vertices)
    size = max(height, diagonal)
    cap = place_line.FOOT_TOLERANCE_METRES / tall * height if tall else None
    TURNS.clear()
    with capped_base(cap), floored():
        points, report = PAINTS_LEVEL(vertices, faces, tall)
    if report["feet"] < ON_FEET:
        return points, turned_report(report, size)
    TURNS.clear()
    with base_left(), floored():
        points, report = PAINTS_LEVEL(vertices, faces, tall)
    return points, turned_report(dict(report, base_left=f"on {report['feet']} feet: an overhang is no base"), size)


@contextlib.contextmanager
def held():
    """place_line.levelled_feet as this module's, and labels.write_parts boxed, while held."""
    import labels
    write_parts = labels.write_parts
    place_line.levelled_feet = levelled_feet
    labels.write_parts = boxed(write_parts)
    try:
        yield
    finally:
        place_line.levelled_feet = PAINTS_LEVEL
        labels.write_parts = write_parts


def paint_take_step(inputs, out):
    """place_line's paint-take step, the take's base levelled by this module."""
    with held():
        place_line.paint_take_step(inputs, out)


if __name__ == "__main__":
    prop_env.main({"paint-take": paint_take_step})
