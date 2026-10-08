"""Check the vehicle bays' kit layouts (bay_kit.py): every piece of the garage, the hangar and their big doors' leaves
stands in a square, right-handed frame with a size, nothing reaches out of the room, the big door's opening is left
open, the hangar's crane bridge is two girders lying on its rails with the trolley standing on them, and every kind
laid is a row of the room's inventory.

The checks need numpy, which only the prop environment has. Run by the gate with the system python, this hands itself to
the prop environment when the box has one, and says it skipped when it does not.
Run: python3 tools/props/scene/bay_kit_test.py
"""
import json
import os
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
PROPS_PYTHON = pathlib.Path(os.environ.get("PROPS_PYTHON", pathlib.Path.home() / ".farm-factory-props/env/bin/python"))

try:
    import numpy as np
except ImportError:
    if PROPS_PYTHON.exists() and os.environ.get("BAY_KIT_TEST_HANDED") != "1":
        os.environ["BAY_KIT_TEST_HANDED"] = "1"
        os.execv(str(PROPS_PYTHON), [str(PROPS_PYTHON), __file__])
    print("skipped: no prop environment on this box")
    sys.exit(0)

sys.path.insert(0, str(HERE))
import bay_kit  # noqa: E402
import room_kit  # noqa: E402

ROOMS = ("garage", "hangar")
INVENTORIES = {room: json.loads((bay_kit.REPO / f"data/inventory/{room}.json").read_text()) for room in ROOMS}
LAID = {room: bay_kit.laid_out(room, inventory) for room, inventory in INVENTORIES.items()}
LEAVES = {room: bay_kit.leaf(inventory) for room, inventory in INVENTORIES.items()}


def test_every_piece_stands_in_a_square_right_handed_frame():
    for room in ROOMS:
        for laid in LAID[room] + LEAVES[room]:
            axes = np.array([laid["x"], laid["y"], laid["z"]])
            assert np.allclose(axes @ axes.T, np.eye(3), atol=1e-3), (room, laid["kind"])
            assert np.linalg.det(axes) > 0.99, (room, laid["kind"], "a mirrored frame draws its faces inside out")
            assert all(side > 0 for side in laid["size"]), (room, laid["kind"])


def test_nothing_stands_outside_the_walls():
    for room in ROOMS:
        layout = INVENTORIES[room]["room"]["layout"]
        half = np.asarray(layout["inside"]) / 2 + room_kit.SHELL_WALL / 2 + 0.01
        for laid in LAID[room]:
            corners = room_kit.box_corners(laid)
            assert np.all(np.abs(corners[:, 0]) <= half[0]) and np.all(np.abs(corners[:, 2]) <= half[1]), \
                (room, laid["kind"], laid["at"])


def test_the_garage_s_big_door_opening_is_left_open():
    """No wall panel stands in the big door's opening: its leaves are the game's moving node."""
    layout = INVENTORIES["garage"]["room"]["layout"]
    big = layout["big_door"]
    south = layout["inside"][1] / 2
    for laid in LAID["garage"]:
        if "_wall_" not in laid["kind"] or abs(laid["at"][2] - south) > 0.3:
            continue
        corners = room_kit.box_corners(laid)
        across = (corners[:, 0].min(), corners[:, 0].max())
        low = corners[:, 1].min()
        inside = across[1] > -big["wide"] / 2 + 0.02 and across[0] < big["wide"] / 2 - 0.02
        assert not (inside and low < big["high"] - 0.02), (laid["kind"], laid["at"])


def test_the_hangar_s_trolley_stands_on_its_bridge_on_the_rails():
    rails = INVENTORIES["hangar"]["room"]["layout"]["rails"]
    beams = [laid for laid in LAID["hangar"] if laid["kind"] == "hangar_lattice_ring_rib" and laid["at"][1] > 5]
    long_ways = [laid for laid in beams if abs(laid["x"][2]) > 0.9]
    girders = [laid for laid in beams if abs(laid["x"][0]) > 0.9]
    rail_top = max(laid["at"][1] + laid["size"][1] for laid in long_ways)
    assert len(long_ways) == 2 and len(girders) == 2, (len(long_ways), len(girders))
    assert sorted(laid["at"][2] for laid in girders) == [rails["parked"] - rails["gauge"] / 2,
                                                         rails["parked"] + rails["gauge"] / 2]
    assert all(abs(laid["at"][1] - rail_top) < 1e-3 for laid in girders), "the girders lie on the rails' tops"
    trolley = next(laid for laid in LAID["hangar"] if laid["kind"] == "hangar_crane_trolley")
    girder_top = girders[0]["at"][1] + girders[0]["size"][1]
    assert trolley["at"][1] < girder_top < trolley["at"][1] + trolley["size"][1], "the trolley stands on the girders"
    assert abs(trolley["x"][2]) > 0.9, "its drum across the girders, so its wheels run along them"


def test_every_kind_laid_is_a_row_of_the_inventory():
    for room in ROOMS:
        rows = {f"{room}_{row['id']}" for row in INVENTORIES[room]["rows"]}
        laid = {laid["kind"] for laid in LAID[room]}
        assert laid <= rows, (room, sorted(laid - rows))


if __name__ == "__main__":
    for name, test in sorted(globals().items()):
        if name.startswith("test_") and callable(test):
            test()
            print("ok", name)
