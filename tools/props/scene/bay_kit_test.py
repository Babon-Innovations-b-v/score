"""Check the vehicle bays' kit layouts (bay_kit.py): every piece of the garage and the hangar
stands in a square, right-handed frame with a size, nothing reaches out of the room, the big door's opening has no
wall panel in it, each bay's door leaves are two objects of its own across its opening, the hangar's crane bridge is two girders lying on its rails with the trolley standing on them, and every kind
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


def test_every_piece_stands_in_a_square_right_handed_frame():
    for room in ROOMS:
        for laid in LAID[room]:
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
    """No wall panel stands in the big door's opening: its leaves (big_door_leaf) shut it, slid by the motion layer."""
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


def test_each_bay_s_door_leaves_are_two_objects_of_its_own_shutting_its_opening():
    """The garage's and the hangar's door leaves are objects of the room (owner, 2026-10-20: never places of their
    own), two of one row each, side by side across the big door's or the roof's opening."""
    for room, row, opening in (("garage", "big_door_leaf", INVENTORIES["garage"]["room"]["layout"]["big_door"]["wide"]),
                               ("hangar", "roof_leaf", INVENTORIES["hangar"]["room"]["layout"]["opening"][0])):
        leaves = [laid for laid in LAID[room] if laid["kind"] == f"{room}_{row}"]
        assert len(leaves) == 2, (room, len(leaves))
        across = sorted(edge for laid in leaves for edge in (laid["at"][0] - laid["size"][0] / 2,
                                                             laid["at"][0] + laid["size"][0] / 2))
        assert across[0] <= -opening / 2 and across[-1] >= opening / 2, (room, across, "a leaf leaves the opening open")


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


def test_the_installed_garage_header_is_as_tall_as_its_posts_are_wide_and_clear_of_the_opening():
    """The installed kit lays each piece at its made model's own box: the header's model had its three bolts laid up
    a 0.2 m beam, so it came out 0.42 m tall and hung 11 cm into the opening (2026-10-09)."""
    layout = INVENTORIES["garage"]["room"]["layout"]
    big = layout["big_door"]
    post = room_kit.size_of({row["id"]: row for row in INVENTORIES["garage"]["rows"]}, "wall_corner_post")
    installed = json.loads((bay_kit.REPO / "data/kit/garage.json").read_text())
    headers = [laid for laid in installed["pieces"]
               if laid["kind"] == "garage_wall_corner_post" and laid["size"][0] >= big["wide"] - 1e-3]
    assert len(headers) == 1
    corners = room_kit.box_corners(headers[0])
    assert abs(corners[:, 1].max() - corners[:, 1].min() - post[0]) < 0.01
    assert corners[:, 1].min() >= big["high"] - 1e-3


def test_the_hangar_s_ship_stands_under_its_roof_door_with_its_engines_and_thrusters_on_it():
    """The ship built in code from the plan v7 stands wholly under the roof's opening (it lifts straight out), clear
    of the walls, and every engine and thruster laid on it lies within its hull's box (2026-10-18: the hangar sized to
    the ship, not the ship to the hangar)."""
    layout = INVENTORIES["hangar"]["room"]["layout"]
    hull = next(laid for laid in LAID["hangar"] if laid["kind"] == "hangar_ship")
    corners = room_kit.box_corners(hull)
    low, high = corners.min(axis=0), corners.max(axis=0)
    opening = np.asarray(layout["opening"]) / 2
    assert np.all(np.abs(corners[:, [0, 2]]) <= opening), (low, high, "the ship reaches past the roof's opening")
    assert abs(low[1]) < 1e-3, "the ship stands on its feet on the floor"
    assert hull["shows"]["hull"]["length"] == hull["size"][2], "the hull is laid at the plan's built length"
    mounted = [laid for laid in LAID["hangar"]
               if laid["kind"] in ("hangar_main_engine", "hangar_lift_thruster", "hangar_nose_thruster")]
    assert len(mounted) == 10, len(mounted)
    for laid in mounted:
        assert np.all(room_kit.box_corners(laid) >= low - 0.5) and np.all(room_kit.box_corners(laid) <= high + 0.5), \
            (laid["kind"], laid["at"])


def test_the_hangar_s_pads_lie_under_the_ship_s_legs():
    hull = next(laid for laid in LAID["hangar"] if laid["kind"] == "hangar_ship")
    pads = [laid for laid in LAID["hangar"] if laid["kind"] == "hangar_machine_bay_plate"]
    nose = np.asarray(hull["at"]) - np.asarray(hull["z"]) * hull["size"][2] / 2
    for leg in hull["shows"]["hull"]["legs"]:
        foot = nose + np.asarray(hull["z"]) * leg["y"] + np.asarray(hull["x"]) * leg["x"]
        assert any(np.all(np.abs(foot[[0, 2]] - room_kit.box_corners(pad)[:, [0, 2]].mean(axis=0)) < 3.6)
                   for pad in pads), (leg, "a leg with no pad under it")


def test_every_kind_laid_is_a_row_of_the_inventory():
    for room in ROOMS:
        rows = {f"{room}_{row['id']}" for row in INVENTORIES[room]["rows"]}
        laid = {laid["kind"] for laid in LAID[room]}
        assert laid <= rows, (room, sorted(laid - rows))


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[3] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in sorted(globals().items()):
        if name.startswith("test_") and callable(test):
            test()
            print("ok", name)
