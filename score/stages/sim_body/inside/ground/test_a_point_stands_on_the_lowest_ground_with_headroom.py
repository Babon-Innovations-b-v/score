"""ground: a point stands on the lowest drawn triangle under it with HEADROOM free over it, at the height worked out by
hand, and every triangle's normal points up (pure numpy: the score venv runs it).

Breaks (each applied once, seen red, reverted), 2026-10-28:
- standing's `free = above - heights >= HEADROOM` made `>= 0`: a point over a floor with a table top 0.5 m over it
  stands on the floor, under the table.
- normals' `found *= np.sign(found[:, 1:2]) + (found[:, 1:2] == 0)` dropped: a triangle wound the other way points
  down.

Run: .venv/bin/python score/stages/sim_body/inside/ground/test_a_point_stands_on_the_lowest_ground_with_headroom.py
"""
import pathlib
import sys

import numpy as np

INSIDE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(INSIDE))
import ground  # noqa: E402


def square(height, low=-5.0, high=5.0):
    """A flat square at `height` (Y up) as two triangles."""
    return [[[low, height, low], [high, height, high], [high, height, low]],
            [[low, height, low], [low, height, high], [high, height, high]]]


def a_point_over_a_slope_stands_at_its_height():
    """The slope through (0, 0, 0), (2, 1, 0) and (0, 0, 2) is y = x / 2: a point at x 1, z 0.5, 5 m up, stands on
    it at 0.5 m, 4.5 m over it; a point off every triangle has no ground (nan, -1)."""
    slope = np.array([[[0.0, 0.0, 0.0], [2.0, 1.0, 0.0], [0.0, 0.0, 2.0]]])
    points = np.array([[1.0, 5.0, 0.5], [100.0, 0.0, 100.0]])
    heights, triangles = ground.standing(points, slope)
    problems = [] if abs(heights[0] - 0.5) < 1e-12 and triangles[0] == 0 else [
        f"over the slope: {heights[0]} on triangle {triangles[0]}, not 0.5 on 0"]
    problems += [] if np.isnan(heights[1]) and triangles[1] == -1 else [f"off the ground: {heights[1]}, {triangles[1]}"]
    over = ground.heights_over(points[:1], slope)[0]
    return problems + ([] if abs(over - 4.5) < 1e-12 else [f"height over the slope {over}, not 4.5"])


def a_point_under_a_low_top_stands_on_the_top():
    """A floor at 0 with a table top at 0.5 m over it: the floor has 0.5 m free, under HEADROOM (1 m), so a point over
    both stands on the top; with a roof 2.5 m over the floor instead, it stands on the floor."""
    point = np.array([[0.5, 3.0, 0.5]])
    table = np.array(square(0.0) + square(0.5, -1.0, 1.0))
    roofed = np.array(square(0.0) + square(2.5, -1.0, 1.0))
    on_table, on_floor = ground.standing(point, table)[0][0], ground.standing(point, roofed)[0][0]
    return ([] if on_table == 0.5 else [f"under the table top: stands at {on_table}, not 0.5"]) + (
        [] if on_floor == 0.0 else [f"under the roof: stands at {on_floor}, not 0"])


def every_normal_points_up():
    """A triangle wound either way has the upward unit normal (0, 1, 0)."""
    both = np.array([[[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]],
                     [[0.0, 0.0, 0.0], [0.0, 0.0, 1.0], [1.0, 0.0, 0.0]]])
    found = ground.normals(both)
    return [] if np.allclose(found, [[0.0, 1.0, 0.0]] * 2) else [f"normals {found.tolist()}"]


CHECKS = (a_point_over_a_slope_stands_at_its_height, a_point_under_a_low_top_stands_on_the_top,
          every_normal_points_up)


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[5] / "conftest.py"))["refuse_outside_sandbox"]()
    failures = [f"{check.__name__}: {problem}" for check in CHECKS for problem in check()]
    for failure in failures:
        print(failure)
    print("ok" if not failures else f"{len(failures)} failed")
    sys.exit(1 if failures else 0)
