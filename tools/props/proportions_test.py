"""Check the model proportion check (proportions.py) on boxes whose answers are obvious.

The checks need numpy, which only the prop environment has. Run by the gate with the system python, this hands
itself to the prop environment when the box has one, and says it skipped when it does not.
Run: python3 tools/props/proportions_test.py
"""
import os
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
PROPS_PYTHON = pathlib.Path(os.environ.get("PROPS_PYTHON", pathlib.Path.home() / ".farm-factory-props/env/bin/python"))

try:
    import numpy as np  # noqa: F401
except ImportError:
    if PROPS_PYTHON.exists() and os.environ.get("PROPORTIONS_TEST_HANDED") != "1":
        os.environ["PROPORTIONS_TEST_HANDED"] = "1"
        os.execv(str(PROPS_PYTHON), [str(PROPS_PYTHON), __file__])
    print("skipped: no prop environment on this box")
    sys.exit(0)

sys.path.insert(0, str(HERE))
import proportions  # noqa: E402


def test_a_model_in_the_rows_shape_passes_and_fits_by_one_scale():
    found = proportions.check([0.3, 1.0, 0.6], (0.6, 0.3, 1.0))
    assert found["upright"] and not found["flag"] and found["spread"] < 1e-9
    assert found["scale"] == [1.0, 1.0, 1.0]


def test_the_footprints_longer_side_is_matched_to_the_rows_longer_side_whichever_axis_it_lies_on():
    assert not proportions.check([0.6, 1.0, 0.3], (0.6, 0.3, 1.0))["flag"]
    assert not proportions.check([0.3, 1.0, 0.6], (0.3, 0.6, 1.0))["flag"]


def test_a_tall_item_lying_down_is_flagged_not_upright():
    found = proportions.check([0.5, 0.76, 1.0], (1.2, 0.55, 2.0))
    assert not found["upright"] and found["flag"]


def test_a_model_too_deep_for_its_row_is_flagged_and_its_scales_show_why():
    found = proportions.check([0.26, 0.99, 0.78], (0.6, 0.6, 1.9))
    assert found["upright"] and found["flag"] and found["spread"] > proportions.SPREAD


def test_a_small_difference_is_fitted_per_axis_without_a_flag():
    found = proportions.check([0.55, 1.0, 0.33], (0.6, 0.3, 1.0))
    assert not found["flag"]
    assert abs(found["sides"][0] * found["scale"][0] - 0.6) < 1e-3 and abs(found["sides"][2] * found["scale"][2] - 0.3) < 1e-3


def test_a_board_on_a_wall_keeps_its_own_depth():
    found = proportions.check([0.07, 0.62, 0.9], (1.2, 0.08, 0.8), flat=True)
    assert not found["flag"]
    assert abs(found["scale"][0] - (found["scale"][1] + found["scale"][2]) / 2) < 1e-6


def test_a_wide_board_standing_on_end_is_flagged_not_upright():
    assert not proportions.check([0.07, 0.9, 0.62], (1.2, 0.08, 0.8), flat=True)["upright"]


def test_a_model_is_held_against_its_pictures_shape(tmp=pathlib.Path("/tmp")):
    from PIL import Image
    import numpy as np
    front = np.zeros((100, 100, 4), np.uint8)
    front[10:90, 30:70, 3] = 255
    Image.fromarray(front, "RGBA").save(tmp / "proportions_front.png")
    side = np.full((100, 100, 3), 200, np.uint8)
    side[10:90, 40:60] = 40
    Image.fromarray(side).save(tmp / "proportions_side.png")
    found = proportions.against_pictures([0.4, 0.8, 0.2], tmp / "proportions_front.png", tmp / "proportions_side.png")
    assert found["matches_pictures"] and abs(found["front_ratio"] - 1.0) < 0.05 and abs(found["side_ratio"] - 1.0) < 0.05
    assert not proportions.against_pictures([0.4, 0.8, 0.6], None, tmp / "proportions_side.png")["matches_pictures"]


def test_a_side_view_on_an_unevenly_lit_backdrop_is_measured_above_its_floor_shadow(tmp=pathlib.Path("/tmp")):
    from PIL import Image
    import numpy as np
    side = np.tile(np.linspace(170, 230, 200, dtype=np.float32)[None, :, None], (200, 1, 3))
    side[20:180, 80:120] = 60
    side[150:180, 120:190] = 120
    Image.fromarray(side.astype(np.uint8)).save(tmp / "proportions_shadow.png")
    width, height = proportions.picture_box(tmp / "proportions_shadow.png")
    assert abs(width - 40) <= 2 and abs(height - 160) <= 2


def main():
    tests = [value for name, value in globals().items() if name.startswith("test_")]
    for test in tests:
        test()
    print(f"{len(tests)} checks passed")


if __name__ == "__main__":
    main()
