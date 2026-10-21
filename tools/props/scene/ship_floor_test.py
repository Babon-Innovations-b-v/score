"""Check the ship's floor plan inside its 46 m hull (ship_floor.py over data/definitions/ship_floor.json): it fits the
hull with no fault, every room keeps a person's size, the eight ship places each have one space, the ship's lock
stands behind the side ring, and the checks catch a room that overlaps, sits under the keel or has a door to nowhere.
Plain Python: runs with the system python; says it skipped until the hull's reader lands (fix-ship-hull).
Run: python3 tools/props/scene/ship_floor_test.py
"""
import copy
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
try:
    import ship_floor  # noqa: E402
except ModuleNotFoundError as missing:
    if missing.name != "ship_outline":
        raise
    print("skipped: the hull's reader (inside/ship_outline.py) lands with the 46 m hull, branch fix-ship-hull")
    sys.exit(0)

SHIP = ship_floor.ship_outline.read_plan(ship_floor.SHIP)
FLOOR = ship_floor.read_floor()


def room(floor, name):
    return next(space for space in ship_floor.spaces(floor) if space["name"] == name)


def test_the_plan_fits_the_hull():
    assert ship_floor.faults(SHIP, FLOOR) == [], ship_floor.faults(SHIP, FLOOR)


def test_the_hull_is_read_at_46_m_before_and_after_the_hull_branch():
    """main's plan v7 says length 31; the hull branch says drawn_length 31, length 46: the same hull either way."""
    branch = {**SHIP, "drawn_length": 31.0, "length": 46.0}
    assert ship_floor.hull_plan(SHIP, FLOOR) == ship_floor.hull_plan(branch, FLOOR)
    assert abs(ship_floor.hull_plan(SHIP, FLOOR)[-1]["y"] - 46.0) < 0.1


def test_every_room_keeps_a_persons_size():
    assert FLOOR["door"]["wide"] == 0.9 and FLOOR["door"]["tall"] == 2.0
    for size in ship_floor.rooms_measured(SHIP, FLOOR):
        assert min(size["clear"]) >= 2.2 and max(size["clear"]) < 4.0, size
        assert size["narrowest"] >= 1.5, size


def test_each_ship_place_has_one_space():
    places = sorted(space["place"] for space in ship_floor.spaces(FLOOR))
    assert places == sorted(["cockpit", "quarters", "galley", "engineroom", "storage", "shiplock",
                             "walkway"])


def test_the_lock_stands_behind_the_side_ring():
    lock, ring = room(FLOOR, "ship's lock"), ship_floor.ring_y(SHIP, FLOOR)
    assert lock["side"] == ship_floor.side_ring(SHIP)["side"] and lock["y"][0] < ring < lock["y"][1]
    assert [door["leads"] for door in lock["doors"] if door["wall"] == "hull"] == ["outside, or a docked craft"]


def test_an_overlapping_room_is_a_fault():
    floor = copy.deepcopy(FLOOR)
    room(floor, "storage")["y"] = [18.0, 27.2]
    assert "cockpit and nav and storage overlap" in ship_floor.faults(SHIP, floor)


def test_a_floor_under_the_keel_is_a_fault():
    floor = copy.deepcopy(FLOOR)
    room(floor, "engine and power room")["floors"] = [[31.5, 2.4]]
    assert any("over its floor's structure" in fault for fault in ship_floor.faults(SHIP, floor))


def test_a_door_to_nowhere_is_a_fault():
    floor = copy.deepcopy(FLOOR)
    room(floor, "galley")["doors"][0]["leads"] = "bridge"
    found = ship_floor.faults(SHIP, floor)
    assert "galley: a door leads to bridge, no space of the plan" in found and "galley: no door to the walkway" in found


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
