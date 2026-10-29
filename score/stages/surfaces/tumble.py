"""Whether a take stands square in its model frame (#36, 2026-10-29: 154 of env1's 406 baked models stood tumbled, base's
square module rolled 32 degrees, camp's bunk bed 44), and the turn that stands it square. Free, numpy and trimesh, in
the prop environment: the bake stands a take square before it is laid (route_bake.stood_square) and surfaces-check's
`stands square` fails one that still is not (bake_check.judge_square). Its own module, so the two rows that read it
hash only this.

    measure(points)                (degrees off, looseness): its oriented box's axes against the frame's
    keeps_pose(row, lying, debris) why a row keeps the pose it was made in, or None
    square_turn(points, size)      the turn standing a tumbled take square, its box's proportions the row's

A take is tumbled when its oriented box (of its convex hull) is turned more than DEGREES off the frame (the axis
nearest up off up, or its long plan axis off the frame's, mod 90, for one not round in plan) and its frame-aligned
box is more than LOOSE times its own: a round or irregular thing whose box turns freely is never called tumbled.
A row whose design lays it lying or leaning keeps its pose: stance.json's lying classes (torn wreckage, a thing on
its side), its `leans`, and the resting rules' ground debris (rocks, boulders, rubble, a pile: a natural shape with
no up, which rests as it was made).
"""
import itertools
import math
import re

import numpy as np

DEGREES = 10.0
LOOSE = 1.25
ROUND_PLAN = 0.92  # a plan this near square (its oriented box's two plan sides) is round: its yaw is not read


def oriented(points):
    """(axes as columns, extents) of the oriented box of the points' convex hull."""
    import trimesh
    hull = trimesh.PointCloud(np.asarray(points, float)).convex_hull
    box = hull.bounding_box_oriented
    return box.primitive.transform[:3, :3], np.asarray(box.primitive.extents, float), hull


def measure(points):
    """(degrees its oriented box stands off the frame, its frame-aligned box's volume over its oriented box's)."""
    axes, extents, hull = oriented(points)
    up = int(np.argmax(np.abs(axes[1, :])))
    tilt = math.degrees(math.acos(min(1.0, abs(float(axes[1, up])))))
    plan = [axis for axis in range(3) if axis != up]
    yaw = 0.0
    if min(extents[plan]) / max(extents[plan]) <= ROUND_PLAN:
        way = axes[[0, 2], plan[int(np.argmax(extents[plan]))]]
        yaw = math.degrees(math.atan2(way[1], way[0])) % 90
        yaw = min(yaw, 90 - yaw)
    loose = float(np.prod(hull.extents)) / max(float(np.prod(extents)), 1e-12)
    return round(max(tilt, yaw), 2), round(loose, 3)


def tumbled(points):
    degrees, loose = measure(points)
    return degrees > DEGREES and loose > LOOSE


def words_of(row):
    return set(re.findall(r"[a-z]+", f"{row.get('id', '')} {row.get('name', '')}".replace("_", " ").lower()))


def keeps_pose(row, lying, debris):
    """Why the row keeps the pose it was made in (its design lays it lying or leaning, or it is ground debris with no
    up), or None. `lying`: stance.json's lying classes' words (phrases too); `debris`: the resting rules' ground debris
    words."""
    text = f"{row.get('id', '')} {row.get('name', '')}".replace("_", " ").lower()
    if row.get("leans"):
        return "its design lays it leaning"
    said = next((word for word in lying if (" " in word and word in text) or word in words_of(row)), None)
    if said:
        return f"its design lays it lying ({said})"
    natural = sorted(words_of(row) & set(debris))
    if natural:
        return f"ground debris with no up ({', '.join(natural)}): it rests as it was made"
    return None


def square_turn(points, size):
    """The turn (rows, the frame's) that stands points square: of every way to set their oriented box's axes on the
    frame's (each axis on each, the up one pointing up), the one whose box best keeps the row's `size` proportions
    (x wide, y tall, z deep: |log| misfits, as bake_job.measured_turn weighs a footprint), the least turn on a tie."""
    axes, extents, _ = oriented(points)
    wide, tall, deep = (max(float(side), 1e-6) for side in size)
    best = None
    for order in itertools.permutations(range(3)):
        rows = []
        for frame_axis, box_axis in enumerate(order):
            way = axes[:, box_axis]
            rows.append(way if way[frame_axis] >= 0 else -way)  # each box axis the way its frame axis points
        turn = np.array(rows)
        if np.linalg.det(turn) < 0:
            turn[2] = -turn[2]
        ex, ey, ez = (extents[box_axis] for box_axis in order)
        misfit = abs(math.log(ex / ey) - math.log(wide / tall)) + abs(math.log(ez / ey) - math.log(deep / tall))
        angle = math.degrees(math.acos(max(-1.0, min(1.0, (float(np.trace(turn)) - 1) / 2))))
        score = (round(misfit, 6), angle)
        if best is None or score < best[0]:
            best = (score, turn)
    return best[1]
