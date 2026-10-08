"""Check the rounded rooms' and the walkway tube's kit layouts (room_kit.py, tube_kit.py): every piece stands in a
square, right-handed frame, the floor and the dome are covered without gaps, nothing reaches out of the room, and every
row the inventory places is laid.

The checks need numpy, which only the prop environment has. Run by the gate with the system python, this hands itself to
the prop environment when the box has one, and says it skipped when it does not.
Run: python3 tools/props/scene/room_kit_test.py
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
    if PROPS_PYTHON.exists() and os.environ.get("ROOM_KIT_TEST_HANDED") != "1":
        os.environ["ROOM_KIT_TEST_HANDED"] = "1"
        os.execv(str(PROPS_PYTHON), [str(PROPS_PYTHON), __file__])
    print("skipped: no prop environment on this box")
    sys.exit(0)

sys.path.insert(0, str(HERE))
import room_kit  # noqa: E402
import tube_kit  # noqa: E402

ROOMS = ("habitat", "airlock", "lab")
INVENTORIES = {room: json.loads((room_kit.REPO / f"data/inventory/{room}.json").read_text()) for room in ROOMS}
LAID = {room: room_kit.laid_out(room, inventory) for room, inventory in INVENTORIES.items()}


def test_every_piece_stands_in_a_square_right_handed_frame():
    for room, pieces in LAID.items():
        for laid in pieces + tube_kit.bay() + tube_kit.end():
            axes = np.array([laid["x"], laid["y"], laid["z"]])
            assert np.allclose(axes @ axes.T, np.eye(3), atol=1e-3), (room, laid["kind"])
            assert np.linalg.det(axes) > 0.99, (room, laid["kind"], "a mirrored frame draws its faces inside out")


def test_the_outline_is_the_shells_own():
    """Four corners of CORNER_STEPS steps between four straight walls, the walls where the floor's size puts them."""
    layout = INVENTORIES["habitat"]["room"]["layout"]
    sides = room_kit.sides(layout)
    assert len(sides) == 4 * (room_kit.CORNER_STEPS + 1)
    north = room_kit.side_named(layout, "north")
    assert np.allclose(north["outward"], (0.0, -1.0)) and abs(north["start"][1] + 5.0) < 1e-6


def test_the_floor_is_covered_once():
    """The deck plates' areas (trapezoids by their taper) add up to the floor inside the outline."""
    for room, pieces in LAID.items():
        layout = INVENTORIES[room]["room"]["layout"]
        plates = [laid for laid in pieces if laid["kind"] == f"{room}_ring_floor_plate" and laid["at"][1] < 0.0]
        area = sum(laid["size"][0] * laid["size"][1] * (1 + laid.get("taper", 1.0)) / 2 for laid in plates)
        points = np.array(room_kit.outline(layout["inside"], layout["corner"]))
        shoelace = 0.5 * abs(np.dot(points[:, 0], np.roll(points[:, 1], 1)) - np.dot(points[:, 1], np.roll(points[:, 0], 1)))
        assert abs(area - shoelace) < 0.01 * shoelace, (room, area, shoelace)


def test_nothing_stands_outside_the_walls():
    for room, pieces in LAID.items():
        layout = INVENTORIES[room]["room"]["layout"]
        half = np.asarray(layout["inside"]) / 2 + room_kit.SHELL_WALL / 2 + 0.01
        for laid in pieces:
            corners = room_kit.box_corners(laid)
            assert np.all(np.abs(corners[:, 0]) <= half[0]) and np.all(np.abs(corners[:, 2]) <= half[1]), \
                (room, laid["kind"], laid["at"])


def test_every_placed_row_is_laid_as_often_as_its_spots():
    """A pipe run may be laid as more lengths than its spots: the layout cuts it at every valve on it."""
    for room, inventory in INVENTORIES.items():
        counts = {}
        for laid in LAID[room]:
            counts[laid["kind"]] = counts.get(laid["kind"], 0) + 1
        for row in inventory["rows"]:
            if row.get("made") == "kit piece" and row.get("at"):
                laid = counts.get(f"{room}_{row['id']}", 0)
                assert laid >= len(row["at"]) if row["id"] in room_kit.PIPE_RUN else laid == len(row["at"]), \
                    (room, row["id"])


def test_a_valve_breaks_its_pipe_run_and_every_run_has_brackets():
    for room, pieces in LAID.items():
        pipes = [laid for laid in pieces if room_kit.own(laid) == "pipe_straight"]
        for valve in (laid for laid in pieces if room_kit.own(laid) == "pipe_valve"):
            for pipe in pipes:
                shift = room_kit.hub_kit.on_run(pipe, valve)
                assert shift is None or abs(shift) >= (pipe["size"][0] + valve["size"][0]) / 2 - 1e-3, \
                    (room, "a pipe runs through the valve at", valve["at"])
        assert not pipes or any(room_kit.own(laid) == "pipe_bracket" for laid in pieces), room


def test_a_set_in_mat_has_its_opening_cut_in_the_plates_under_it():
    plates = [laid for laid in LAID["habitat"] if laid.get("openings")]
    mats = [laid for laid in LAID["habitat"] if laid["kind"] == "habitat_tread_mat"]
    assert mats and plates and all(laid.get("set_in") for laid in mats)


def test_a_ledge_is_topped_to_the_curved_wall_and_faced_along_its_edge():
    """The lab's side ledges (SteppedFloor: LEDGE_DEEP deep, its top the room's): deck plates at the ledge's top cover
    the ledge's ground plan inside the outline, and riser plates stand along its whole room edge."""
    layout = INVENTORIES["lab"]["room"]["layout"]
    half = np.asarray(layout["inside"]) / 2
    for name, top in layout["ledges"].items():
        sign = 1.0 if name == "east" else -1.0
        tops = [laid for laid in LAID["lab"] if laid["kind"] == "lab_ring_floor_plate" and laid["at"][1] > 0.0
                and np.sign(laid["at"][0]) == sign]
        assert tops and all(abs(laid["at"][1] + laid["size"][2] / 2 - top) < 1e-3 for laid in tops), name
        covered = sum(laid["size"][0] * laid["size"][1] for laid in tops)
        reach, straight = layout["corner"], half[1] - layout["corner"]
        # The ledge's plan: its straight run and, at each end, the corner's arc beyond the ledge's inner line.
        offsets = np.linspace(0.0, reach, 2001)
        wide = np.clip(half[0] - reach + np.sqrt(reach ** 2 - offsets ** 2) - (half[0] - room_kit.LEDGE_DEEP), 0.0, None)
        plan = room_kit.LEDGE_DEEP * 2 * straight + 2 * np.trapezoid(wide, offsets)
        assert plan <= covered <= plan * 1.15, (name, covered, plan)
        risers = [laid for laid in LAID["lab"] if laid["kind"] == "lab_pit_wall_panel" and np.sign(laid["at"][0]) == sign]
        assert abs(sum(laid["size"][0] for laid in risers) - 2 * (straight + np.sqrt(reach ** 2 - (reach - room_kit.LEDGE_DEEP) ** 2))) < 1e-3


def test_a_shut_hatch_names_its_door_so_the_game_can_open_it():
    for room in ("habitat", "lab"):
        shut = [laid for laid in LAID[room] if room_kit.own(laid) in ("hatch_leaf", "hatch_wheel", "hatch_window")]
        assert shut and all(laid.get("door") in INVENTORIES[room]["room"]["layout"]["doors"] for laid in shut), room


def test_the_tube_bay_spans_one_hoop_spacing_and_stands_on_its_deck():
    for laid in tube_kit.bay():
        corners = room_kit.box_corners(laid)
        assert corners[:, 2].min() >= -1e-6 and corners[:, 2].max() <= tube_kit.BAY + 1e-6, laid["kind"]
        assert corners[:, 1].min() >= -0.05 and corners[:, 1].max() <= tube_kit.AXIS_HIGH + tube_kit.RADIUS, laid["kind"]


def main():
    tests = [value for name, value in globals().items() if name.startswith("test_")]
    for test in tests:
        test()
    print(f"{len(tests)} checks passed")


if __name__ == "__main__":
    main()
