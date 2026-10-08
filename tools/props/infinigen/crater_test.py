"""Check the crater shape and the steering on cases whose right answer is obvious: the bowl's floor and rim heights,
the flank back to the plain, ejecta only outside the rim, a crater on a round world measured along the ground, and
a plan window cropped and its spots moved into the window's own metres.

numpy only, which only the prop environment has: run by the gate with the system python, this hands itself to the
prop environment when the box has one, and says it skipped when it does not.

Run: python3 tools/props/infinigen/crater_test.py
"""
import math
import os
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
PROPS_PYTHON = pathlib.Path(os.environ.get("PROPS_PYTHON", pathlib.Path.home() / ".farm-factory-props/env/bin/python"))

try:
    import numpy as np
except ImportError:
    if PROPS_PYTHON.exists() and os.environ.get("CRATER_TEST_HANDED") != "1":
        os.environ["CRATER_TEST_HANDED"] = "1"
        os.execv(str(PROPS_PYTHON), [str(PROPS_PYTHON), __file__])
    print("skipped: no prop environment on this box")
    sys.exit(0)

sys.path.insert(0, str(HERE))
import crater  # noqa: E402
import steer  # noqa: E402


def test_bowl_floor_rim_and_flank():
    heights = crater.profile([0.0, 35.0 - 1e-9, 35.0 + 17.5, 100.0], 35.0, 14.0, 3.0)
    assert math.isclose(heights[0], 3.0 - 14.0), heights
    assert math.isclose(heights[1], 3.0, abs_tol=1e-3), heights
    assert math.isclose(heights[2], 0.0, abs_tol=1e-9) and heights[3] == 0.0, heights


def test_ejecta_only_outside_the_rim():
    weights = crater.ejecta_weight([10.0, 35.0, 36.0, 35 * 1.8, 200.0], 35.0, 1.8)
    assert weights[0] == 0.0 and weights[1] == 0.0, weights
    assert 0.9 < weights[2] <= 1.0 and weights[3] == 0.0 and weights[4] == 0.0, weights


def test_crater_on_a_round_world_measures_along_the_ground():
    radius = 220.0
    centre = (0.0, 0.0, radius)
    # A point a quarter of the way round sits pi/2 * R away along the ground.
    distance = crater.surface_distance(np.array([[radius, 0.0, 0.0]]), centre, radius)
    assert math.isclose(distance[0], math.pi / 2 * radius, rel_tol=1e-9), distance
    floor = crater.lift(np.array([[0.0, 0.0, radius]]), [{"centre": centre, "diameter": 20.0,
                                                          "depth_below_rim": 4.0, "rim_above_plain": 1.0}],
                        np.zeros(1), spherical_radius=radius)
    assert math.isclose(floor[0], -3.0), floor


def test_lumps_are_smooth_bounded_and_repeatable():
    points = np.stack([np.linspace(0, 20, 4001), np.full(4001, 3.3)], axis=1)
    values = crater.lumps(points, 7)
    assert np.all(np.abs(values) <= 1.0), values.max()
    assert np.max(np.abs(np.diff(values))) < 0.05, "a 5 mm step should never jump"
    assert np.array_equal(values, crater.lumps(points, 7)) and not np.array_equal(values, crater.lumps(points, 8))


def test_window_crop_and_spots():
    plan = np.arange(16, dtype=float).reshape(4, 4)  # row 0 north, 30 m across
    corner = steer.crop(plan, 30.0, 0.0, 0.0, 30.0, size=4)
    assert np.allclose(corner, plan), corner
    spots = steer.spots_inside([{"x": 12.0, "y": 50.0}, {"x": 80.0, "y": 50.0}], 10.0, 40.0, 50.0)
    assert spots == [{"x": 2.0, "y": 10.0}], spots


if __name__ == "__main__":
    for name, check in sorted(globals().items()):
        if name.startswith("test_"):
            check()
            print(f"ok {name}")
