"""ground: a point stands on the highest drawn triangle under it at most REACH_UP (the cast's KNEE) over it with
HEADROOM free over it, at the height worked out by hand, and every triangle's normal points up (pure numpy: the score
venv runs it).

Breaks (each applied once, seen red, reverted), 2026-10-28 and 2026-10-30:
- standing's `free = (above - heights >= HEADROOM) & ...` made `>= 0`: a point 1.1 m over a floor, over a counter
  top at 1.0 m with a cupboard 0.5 m over it, stands on the counter top, under the cupboard.
- standing's `top = which != np.append(which[1:], -1)` made the first of each point (the lowest, as before
  2026-10-30): a point on a deck 2.958 m over a floor stands on the floor, the deck read as its roof (greenhouse's
  astronauts on Structure/deck_2).
- standing's `& (heights <= points[which, 1] + REACH_UP)` dropped: a point on the floor under the deck stands on the
  deck.
- REACH_UP made 0.4: it no longer agrees with the cast's KNEE.
- normals' `found *= np.sign(found[:, 1:2]) + (found[:, 1:2] == 0)` dropped: a triangle wound the other way points
  down.

Run: .venv/bin/python score/stages/sim_body/inside/ground/test_a_point_stands_on_the_highest_ground_in_reach.py
"""
import pathlib
import sys

import numpy as np

INSIDE = pathlib.Path(__file__).resolve().parents[1]
REPO = pathlib.Path(__file__).resolve().parents[5]
sys.path[:0] = [str(INSIDE), str(REPO)]
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


def a_low_top_is_a_block_not_a_floor():
    """A floor at 0, a counter top at 1.0 m and a cupboard's bottom at 1.5 m over it: the top has 0.5 m free, under
    HEADROOM (1 m), so a point 1.1 m up, the top within its reach, stands on the floor (1.0 m free); a point 3 m up
    stands on the cupboard."""
    under = np.array(square(0.0) + square(1.0, -1.0, 1.0) + square(1.5, -1.0, 1.0))
    on_floor = ground.standing(np.array([[0.5, 1.1, 0.5]]), under)[0][0]
    on_cupboard = ground.standing(np.array([[0.5, 3.0, 0.5]]), under)[0][0]
    return ([] if on_floor == 0.0 else [f"over the counter top under the cupboard: stands at {on_floor}, not 0"]) + (
        [] if on_cupboard == 1.5 else [f"over the cupboard: stands at {on_cupboard}, not 1.5"])


def a_point_on_a_deck_stands_on_the_deck():
    """A floor at 0 and a deck at 2.958 m (greenhouse's Structure/deck_2): a point on the deck stands on it, not on
    the floor 2.958 m under it; a point on the floor under the deck, the deck out of its reach, stands on the floor."""
    decked = np.array(square(0.0) + square(2.958, -1.0, 1.0))
    on_deck = ground.standing(np.array([[0.5, 2.958, 0.5]]), decked)[0][0]
    on_floor = ground.standing(np.array([[0.5, 0.0, 0.5]]), decked)[0][0]
    return ([] if on_deck == 2.958 else [f"on the deck: stands at {on_deck}, not 2.958"]) + (
        [] if on_floor == 0.0 else [f"under the deck: stands at {on_floor}, not 0"])


def reach_up_is_the_casts_knee():
    """REACH_UP is the cast's KNEE, so the cast and the sim body stand a person on the same surface."""
    from score.stages.cast import measure
    return [] if ground.REACH_UP == measure.KNEE else [f"REACH_UP {ground.REACH_UP}, the cast's KNEE {measure.KNEE}"]


def every_normal_points_up():
    """A triangle wound either way has the upward unit normal (0, 1, 0)."""
    both = np.array([[[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]],
                     [[0.0, 0.0, 0.0], [0.0, 0.0, 1.0], [1.0, 0.0, 0.0]]])
    found = ground.normals(both)
    return [] if np.allclose(found, [[0.0, 1.0, 0.0]] * 2) else [f"normals {found.tolist()}"]


CHECKS = (a_point_over_a_slope_stands_at_its_height, a_low_top_is_a_block_not_a_floor,
          a_point_on_a_deck_stands_on_the_deck, reach_up_is_the_casts_knee, every_normal_points_up)


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(REPO / "conftest.py"))["refuse_outside_sandbox"]()
    failures = [f"{check.__name__}: {problem}" for check in CHECKS for problem in check()]
    for failure in failures:
        print(failure)
    print("ok" if not failures else f"{len(failures)} failed")
    sys.exit(1 if failures else 0)
