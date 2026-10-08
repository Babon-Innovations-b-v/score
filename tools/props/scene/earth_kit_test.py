"""Check the prologue's kit layouts (earth_kit.py): every piece stands in a proper frame inside its room, and the stairwell's flights land on its landings. Hands itself to the prop environment for numpy.
Run: python3 tools/props/scene/earth_kit_test.py
"""
import json
import os
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
PROPS_PYTHON = pathlib.Path.home() / ".farm-factory-props/env/bin/python"
try:
    import numpy as np
except ImportError:
    if PROPS_PYTHON.exists() and os.environ.get("EARTH_KIT_TEST_HANDED") != "1":
        raise SystemExit(subprocess.call([str(PROPS_PYTHON), __file__], env=dict(os.environ, EARTH_KIT_TEST_HANDED="1")))
    print("earth_kit_test: skipped, no numpy here")
    raise SystemExit(0)

sys.path.insert(0, str(HERE))
import earth_kit  # noqa: E402


def test_every_piece_has_a_right_handed_unit_frame():
    for room in earth_kit.ROOMS:
        for found in earth_kit.layout(room)["pieces"]:
            axes = [np.array(found[axis]) for axis in "xyz"]
            assert all(abs(np.linalg.norm(axis) - 1.0) < 1e-6 for axis in axes), found["kind"]
            assert abs(np.dot(np.cross(axes[0], axes[1]), axes[2]) - 1.0) < 1e-6, found["kind"]
            assert all(side > 0 for side in found["size"]), found["kind"]


def test_the_flat_s_pieces_stay_in_the_flat_or_on_its_balcony():
    for found in earth_kit.layout("flat")["pieces"]:
        x, y, z = found["at"]
        assert -5.6 <= x <= 3.3 and -6.3 <= z <= -0.7 and -0.3 <= y <= earth_kit.FLAT_HEIGHT + 0.05, found


def test_the_flights_climb_from_the_street_to_the_flat():
    flights = [found for found in earth_kit.layout("stairwell")["pieces"] if found["kind"] == "stairwell_stair_flight"]
    feet = sorted(found["at"][1] - earth_kit.FLOOR_TOP for found in flights)
    assert len(flights) == 6 and np.allclose(feet, [0.0, 1.5, 3.0, 4.5, 6.0, 7.5])
    for found in flights:
        lane = earth_kit.STAIR_LANE_A if found["z"][2] > 0 else earth_kit.STAIR_LANE_B
        assert abs(found["at"][0] - (lane[0] + lane[1]) / 2) < 1e-6


def test_the_doorways_are_cut_where_the_game_has_its_doors():
    flat = earth_kit.layout("flat")["pieces"]
    east = next(found for found in flat if found["kind"] == "flat_plaster_wall" and found["z"][0] == 1.0)
    x0, y0, x1, y1 = east["openings"][0]
    assert np.isclose(x1 - x0, earth_kit.FRONT_DOORWAY[0]) and np.isclose(y1 - y0, earth_kit.FRONT_DOORWAY[1])
    middle = np.array(east["at"]) + np.array(east["x"]) * (x0 + x1) / 2
    assert np.isclose(middle[2], earth_kit.FRONT_DOOR_Z)


def laid_box(laid):
    """A laid piece's box in the place's frame (low, high corners)."""
    axes = np.array([laid["x"], laid["y"], laid["z"]]).T
    corners = np.array([np.asarray(laid["at"]) + axes @ (np.asarray(laid["size"]) * [across, up, deep])
                        for across in (-0.5, 0.5) for up in (0.0, 1.0) for deep in (-0.5, 0.5)])
    return corners.min(axis=0), corners.max(axis=0)


def test_the_open_street_gate_stands_clear_of_the_street_s_pieces():
    """The installed layouts: the open gate on the pavement's top, inside no piece of the street kit (in the game's
    scene check it once stood 9 cm inside a shop's render plate and read as sunk, 2026-10-08)."""
    kits = HERE.parents[2] / "data/kit"
    gate = next(laid for laid in json.loads((kits / "stairwell.json").read_text())["pieces"]
                if laid["kind"] == "stairwell_street_gate")
    low, high = laid_box(gate)
    assert np.isclose(low[1], earth_kit.STREET_PAVED_TOP), low
    for laid in json.loads((kits / "street.json").read_text())["pieces"]:
        other_low, other_high = laid_box(laid)
        inside = np.minimum(high, other_high) - np.maximum(low, other_low)
        assert not np.all(inside > 0.005), (laid["kind"], inside)


def main():
    tests = [value for name, value in globals().items() if name.startswith("test_")]
    for test in tests:
        test()
    print(f"{len(tests)} checks passed")


if __name__ == "__main__":
    main()
