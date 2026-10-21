"""Check the ship's floor plan inside its 46 m hull (ship_floor.py over data/definitions/ship_floor.json, its rooms and
its own hull): it fits the hull with no fault, every room keeps a person's size, the eight ship places each have one
space, the ship's lock stands behind the side ring, the hull runs the floor plan's length, and the checks catch a room
that overlaps, sits under the keel or has a door to nowhere.
Plain Python: runs with the system python.
Run: python3 tools/props/scene/ship_floor_test.py
"""
import copy
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ship_floor  # noqa: E402

FLOOR = ship_floor.read_floor()


def room(floor, name):
    return next(space for space in ship_floor.spaces(floor) if space["name"] == name)


def test_the_plan_fits_the_hull():
    assert ship_floor.faults(FLOOR) == [], ship_floor.faults(FLOOR)


def test_the_hull_is_the_floor_plan_s_own_at_its_length():
    """The floor plan carries its hull (plan v7's, built at 46 m): stations front to back to its length, a section
    of five corners from the keel up, the waist its widest."""
    hull = ship_floor.hull_of(FLOOR)
    assert [row["y"] for row in hull] == sorted(row["y"] for row in hull)
    assert abs(hull[-1]["y"] - FLOOR["length"]) < 0.1 and FLOOR["length"] == 46.0
    corners = ship_floor.section(FLOOR, hull[len(hull) // 2])
    assert len(corners) == 5 and max(corners)[0] == corners[2][0] == hull[len(hull) // 2]["half"]


def test_every_room_keeps_a_persons_size():
    assert FLOOR["door"]["wide"] == 0.9 and FLOOR["door"]["tall"] == 2.0
    for size in ship_floor.rooms_measured(FLOOR):
        assert min(size["clear"]) >= 2.2 and max(size["clear"]) < 4.0, size
        assert size["narrowest"] >= 1.5, size


def test_each_ship_place_has_one_space():
    places = sorted(space["place"] for space in ship_floor.spaces(FLOOR))
    assert places == sorted(["cockpit", "quarters", "galley", "engineroom", "storage", "shiplock",
                             "walkway"])


def test_the_lock_stands_behind_the_side_ring():
    lock, ring = room(FLOOR, "ship's lock"), FLOOR["hull"]["side_ring"]
    assert lock["side"] == ring["side"] and lock["y"][0] < ring["y"] < lock["y"][1]
    assert [door["leads"] for door in lock["doors"] if door["wall"] == "hull"] == ["outside, or a docked craft"]


def test_an_overlapping_room_is_a_fault():
    floor = copy.deepcopy(FLOOR)
    room(floor, "storage")["y"] = [18.0, 27.2]
    assert "cockpit and nav and storage overlap" in ship_floor.faults(floor)


def test_a_floor_under_the_keel_is_a_fault():
    floor = copy.deepcopy(FLOOR)
    room(floor, "engine and power room")["floors"] = [[31.5, 2.4]]
    assert any("over its floor's structure" in fault for fault in ship_floor.faults(floor))


def test_a_door_to_nowhere_is_a_fault():
    floor = copy.deepcopy(FLOOR)
    room(floor, "galley")["doors"][0]["leads"] = "bridge"
    found = ship_floor.faults(floor)
    assert "galley: a door leads to bridge, no space of the plan" in found and "galley: no door to the walkway" in found


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
