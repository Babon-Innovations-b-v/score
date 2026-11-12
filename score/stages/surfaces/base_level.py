"""The bake's paint with a take's base counted level within 3 cm through its standing height, as its feet are.

place_line.levelled_feet counts a foot down within a hundredth of the take's size, at most FOOT_TOLERANCE_METRES (the
resting check's 3 cm) through its standing height, but hands its base steps (flattened_base, sloped_base,
resting_base) the hundredth with no cap. On a large take a hundredth is far past 3 cm: base's large hangar (0.84 m)
and spacecraft (0.25 m) kept base corners 34 to 60 cm up, which make_chunky's own levelling brought down less the
4 and 8 cm its level corner sank, and surfaces-check's "stands level" (bake_check.STANCE_GAP, 3 cm) failed both
(env1, 2026-11-12). Here each base step's tolerance is capped as the feet's is; a take whose hundredth is under 3 cm,
or whose base has no corner or plane past 3 cm, levels exactly as before.

Run, never imported, by inside/paint_fit.py (the bake's card job, ../bake_fitted.py): its `paint-take` is place_line's
with levelled_feet held as this module's, so place_line.py and paint_take.py, in the code of every row reaching
route_bake.py, do not move.
"""
import contextlib
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.append(str(HERE))

import place_line  # noqa: E402
import prop_env  # noqa: E402

BASE_STEPS = ("flattened_base", "sloped_base", "resting_base")
PAINTS_LEVEL = place_line.levelled_feet


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


def levelled_feet(vertices, faces, tall=None):
    """place_line.levelled_feet with each base step's tolerance at most FOOT_TOLERANCE_METRES through the standing
    height `tall` (metres), as its feet's is; as there when `tall` is unknown. The report as there."""
    import feet
    height, _ = feet.model_scale(vertices)
    cap = place_line.FOOT_TOLERANCE_METRES / tall * height if tall else None
    with capped_base(cap):
        return PAINTS_LEVEL(vertices, faces, tall)


@contextlib.contextmanager
def held():
    """place_line.levelled_feet as this module's while held."""
    place_line.levelled_feet = levelled_feet
    try:
        yield
    finally:
        place_line.levelled_feet = PAINTS_LEVEL


def paint_take_step(inputs, out):
    """place_line's paint-take step, the take's base levelled by this module."""
    with held():
        place_line.paint_take_step(inputs, out)


if __name__ == "__main__":
    prop_env.main({"paint-take": paint_take_step})
