"""Where a person can stand on a plan: a person's footprint (their people row's size) overlaps no wall, no floor thing
and no other person, with no slack, and when it does the nearest floor inside the outline where it overlaps none.
The pass's person spots (plans_pass.spaced_people) and the scene record's views (scene_record/writer.py: an eye stands
where a person would) are held to it alike (#36, 2026-10-30: the airlock's three spots within 7 cm, wreck's views).
Its own module so the scene record's key reads it without the pass's."""
import math

import numpy
import scipy.ndimage

from score.review import plan_checks

PERSON = 0.5  # metres: a person's footprint each way when no people row gives one (the cast's body, two BODY_RADIUS)


def footprints(plan, inventory):
    """Each person spot's footprint [wide, deep] in metres: its people row's size, else the largest people row's,
    else PERSON square."""
    sizes = {row["id"]: [float(side) for side in row["size"][:2]]
             for row in plan_checks.person_rows(inventory) if isinstance(row.get("size"), list)}
    other = max(sizes.values(), key=lambda size: size[0] * size[1], default=[PERSON, PERSON])
    return [sizes.get(spot[3], other) if len(spot) >= 4 and isinstance(spot[3], str) else other
            for spot in plan.get("people", [])]


def blocked(plan, inventory, grid, sits_on):
    """The grid cells a person cannot stand in: under a wall (its doorways open) or a floor thing, the things of
    `sits_on`'s row left out (a person sits on its bench)."""
    found = numpy.zeros(grid.shape, dtype=bool)
    for item, row, shape in plan_checks.blocking(plan, inventory):
        if row != sits_on:
            found |= grid.covered(plan_checks.polygon_of(item, shape))
    for wall in plan.get("walls", []):
        found |= grid.covered(plan_checks.wall_polygon(wall))
    for opening in plan.get("openings", []):
        if opening.get("kind") in ("door", "opening", "gate"):
            found &= ~grid.covered(plan_checks.opening_polygon(opening))
    return found


def under(grid, spot, size):
    """The grid cells whose centres a person's footprint `size` [wide, deep] at `spot` covers (no slack)."""
    return ((numpy.abs(grid.centres[:, 0] - spot[0]) < size[0] / 2)
            & (numpy.abs(grid.centres[:, 1] - spot[1]) < size[1] / 2)).reshape(grid.shape)


def in_each_other(spot, size, other, other_size):
    """Whether two people's footprints overlap."""
    return abs(spot[0] - other[0]) < (size[0] + other_size[0]) / 2 and abs(spot[1] - other[1]) < (
        size[1] + other_size[1]) / 2


def stands_in(spot, size, walls_things, grid, others):
    """Whether a person at `spot` stands in a wall or a floor thing (`walls_things`, `blocked`'s cells) or in one of
    `others` ([(spot, footprint)])."""
    return bool((walls_things & under(grid, spot, size)).any()) or any(
        in_each_other(spot, size, other, other_size) for other, other_size in others)


def nearest_free(spot, size, walls_things, grid, outline, others):
    """The nearest grid cell centre [x, y] inside the outline (`outline`'s cells) where a person at it stands in
    nothing (`stands_in`), or None when there is none."""
    reach = [max(0, math.ceil(side / 2 / grid.size) - 1) * 2 + 1 for side in (size[1], size[0])]
    fits = outline & ~scipy.ndimage.maximum_filter(walls_things.astype(numpy.uint8), size=reach, mode="constant",
                                                   cval=1).astype(bool)
    for other, other_size in others:
        fits &= ~((numpy.abs(grid.centres[:, 0] - other[0]) < (size[0] + other_size[0]) / 2)
                  & (numpy.abs(grid.centres[:, 1] - other[1]) < (size[1] + other_size[1]) / 2)).reshape(grid.shape)
    if not fits.any():
        return None
    cells = numpy.flatnonzero(fits.ravel())
    nearest = grid.centres[cells[numpy.argmin(numpy.hypot(grid.centres[cells, 0] - spot[0],
                                                          grid.centres[cells, 1] - spot[1]))]]
    return [round(float(nearest[0]), 3), round(float(nearest[1]), 3)]
