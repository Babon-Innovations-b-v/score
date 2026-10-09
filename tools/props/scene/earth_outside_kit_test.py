"""Check the Earth's outdoor kit layouts (earth_outside_kit.py): they read the game's own numbers as recorded, every piece stands in
a proper frame, the street keeps its way from the door to the car clear and every face it dresses stands where the
blocks' faces are. Hands itself to the prop environment for numpy.
Run: python3 tools/props/scene/earth_outside_kit_test.py
"""
import os
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
PROPS_PYTHON = pathlib.Path.home() / ".farm-factory-props/env/bin/python"
try:
    import numpy as np
except ImportError:
    if PROPS_PYTHON.exists() and os.environ.get("EARTH_OUTSIDE_KIT_TEST_HANDED") != "1":
        raise SystemExit(subprocess.call([str(PROPS_PYTHON), __file__],
                                         env=dict(os.environ, EARTH_OUTSIDE_KIT_TEST_HANDED="1")))
    print("earth_outside_kit_test: skipped, no numpy here")
    raise SystemExit(0)

sys.path.insert(0, str(HERE))
import earth_outside_kit as kit  # noqa: E402

NUMBERS = kit.site()


def test_the_game_s_numbers_are_read_from_its_scripts():
    assert NUMBERS["STREET_GROUND"] == [6.0, -8.0, 8.0, 20.0]
    assert NUMBERS["OWN_BLOCKS_AT"][1] == [1.45, 0.0, 17.1]
    assert len(NUMBERS["SQUARE_TIERS"]) == 3 and len(NUMBERS["SQUARE_TIERS"][0]) == 6
    assert len(NUMBERS["FLOODLIGHT_TOWERS"]) == 4
    assert NUMBERS["PODIUM_AT"][1] == NUMBERS["BIG_STAGE_DECK"]
    assert [NUMBERS[f"BLOCK_{letter}"][2] for letter in "ABCD"] == [-90.0, -90.0, 90.0, 90.0]


def test_every_piece_stands_in_a_right_handed_unit_frame():
    for room in kit.PLACES:
        for laid in kit.layout_of(room)["pieces"]:
            axes = [np.asarray(laid[name]) for name in ("x", "y", "z")]
            assert all(abs(np.linalg.norm(axis) - 1.0) < 1e-3 for axis in axes), laid
            assert np.allclose(np.cross(axes[1], axes[2]), axes[0], atol=1e-3), laid
            assert all(side > 0 for side in laid["size"]), laid


def test_the_way_from_the_street_door_to_the_car_is_clear():
    car = NUMBERS["CAR_AT"]
    door = NUMBERS["STAIRWELL_GROUND"][0] + NUMBERS["STAIRWELL_GROUND"][2] + NUMBERS["WALL"] + kit.PLATE_DEEP
    way = (door + 0.3, NUMBERS["FRONT_DOOR_Z"] - 0.5, car[0] - 1.2, car[2])
    for laid in kit.layout_of("street")["pieces"]:
        own = laid["kind"].split("_", 1)[1]
        if own not in kit.STANDING:
            continue
        x, _, z = laid["at"]
        if own == "street_lamp":  # what stands on the pavement is its pole, at its box's -x end
            x -= laid["x"][0] * (laid["size"][0] / 2 - kit.POLE_IN)
        assert not (way[0] < x < way[2] and way[1] < z < way[3]), laid["kind"]


def test_the_street_s_facade_pieces_stand_on_their_block_s_face():
    faces = kit.street_faces(NUMBERS)
    planes = sorted({round(float(face.middle[0]), 3) for face in faces.values()})
    for laid in kit.layout_of("street")["pieces"]:
        if not laid["kind"].endswith(("render_upper", "render_shop", "render_lower")):
            continue
        back = np.asarray(laid["at"]) + np.asarray(laid["z"]) * laid["size"][2] / 2
        assert min(abs(back[0] - plane) for plane in planes) < 1e-3, laid


def test_the_square_s_lanterns_hang_under_their_strings_and_over_the_crowd():
    pieces = kit.layout_of("square")["pieces"]
    lanterns = [laid for laid in pieces if laid["kind"].endswith("far_lantern")]
    assert lanterns and all(laid["at"][1] > 3.0 for laid in lanterns)


def test_each_crowd_banner_stands_both_poles_on_one_level_of_the_crowd():
    pieces = [laid for laid in kit.layout_of("square")["pieces"] if laid["kind"] == "square_crowd_banner"]
    assert len(pieces) == len(kit.CROWD_BANNERS) == 6
    levels = kit.terraces(NUMBERS)
    spread = NUMBERS["CROWD_SPREAD"]
    for laid in pieces:
        at, along = np.asarray(laid["at"]), np.asarray(laid["x"])
        assert spread[0] <= at[0] <= spread[0] + spread[2] and spread[1] <= at[2] <= spread[1] + spread[3], laid
        for pole in (at - along * laid["size"][0] / 2, at + along * laid["size"][0] / 2):
            under = max([high[1] for low, high in levels if low[0] <= pole[0] <= high[0] and low[2] <= pole[2] <= high[2]],
                        default=kit.ROAD_TOP - 0.02)
            assert abs(under - at[1]) < 1e-6, laid


def test_the_guard_hut_stands_on_the_paving_clear_of_the_stage_and_the_banners_down_their_poles():
    pieces = kit.layout_of("square")["pieces"]
    huts = [laid for laid in pieces if laid["kind"] == "square_guard_hut"]
    assert len(huts) == 1
    x, y, z = huts[0]["at"]
    half = max(kit.GUARD_HUT[0], kit.GUARD_HUT[2]) / 2
    stage = NUMBERS["BIG_STAGE_GROUND"]
    assert y == kit.ROAD_TOP - 0.02
    assert z - half > stage[1] + stage[3] + 1.0  # left of the stage as the balcony sees it, clear of its side
    for laid in pieces:
        if laid["kind"] == "square_far_banner":
            assert abs(laid["at"][2] - z) > half + kit.BANNER[0] / 2 or abs(laid["at"][0] - x) > half + 0.5, laid


def main():
    tests = [value for name, value in globals().items() if name.startswith("test_")]
    for test in tests:
        test()
    print(f"{len(tests)} checks passed")


if __name__ == "__main__":
    main()
