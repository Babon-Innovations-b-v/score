"""Check the cut-out size limit (cutsize.py) on boxes either side of it.

Plain python, run by the gate with the system python: python3 tools/props/scene/cutsize_test.py
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from cutsize import MIN_CUT_SIDE, route, size_of  # noqa: E402


def test_a_box_is_measured_by_its_short_side_and_area():
    assert size_of([10, 20, 110, 320]) == {"width": 100, "height": 300, "short_side": 100, "area": 30000}


def test_a_box_at_the_limit_is_redrawn_from_its_cut_out():
    assert route([0, 0, MIN_CUT_SIDE, 2 * MIN_CUT_SIDE], can_close_up=True) == "redraw"
    assert route([0, 0, MIN_CUT_SIDE, MIN_CUT_SIDE], can_close_up=False) == "redraw"


def test_a_box_one_pixel_short_never_feeds_the_redraw():
    tall_but_thin = [0, 0, MIN_CUT_SIDE - 1, 760]
    assert route(tall_but_thin, can_close_up=True) == "close-up"
    assert route(tall_but_thin, can_close_up=False) == "dropped"


def test_the_round_one_habitat_boxes_split_where_the_models_did():
    bench, counter_cabinet = [274, 371, 508, 616], [926, 443, 1170, 731]
    desk, desk_lamp = [812, 401, 984, 559], [901, 326, 933, 419]
    assert [route(box, False) for box in (bench, counter_cabinet)] == ["redraw", "redraw"]
    assert [route(box, False) for box in (desk, desk_lamp)] == ["dropped", "dropped"]


def main():
    tests = [value for name, value in globals().items() if name.startswith("test_")]
    for test in tests:
        test()
    print(f"{len(tests)} checks passed")


if __name__ == "__main__":
    main()
