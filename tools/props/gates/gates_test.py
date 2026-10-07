"""Check the gates (room.py, greybox.py, placement.py, model.py) on cases whose answers are obvious.

The gates need numpy and trimesh, which only the prop environment has. Run by the gate with the system python, this
hands itself to the prop environment when the box has one, and says it skipped when it does not.
Run: python3 tools/props/gates/gates_test.py
"""
import os
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
PROPS_PYTHON = pathlib.Path(os.environ.get("PROPS_PYTHON", pathlib.Path.home() / ".farm-factory-props/env/bin/python"))

try:
    import numpy as np
    import trimesh
except ImportError:
    if PROPS_PYTHON.exists() and os.environ.get("GATES_TEST_HANDED") != "1":
        os.environ["GATES_TEST_HANDED"] = "1"
        os.execv(str(PROPS_PYTHON), [str(PROPS_PYTHON), __file__])
    print("skipped: no prop environment on this box")
    sys.exit(0)

sys.path.insert(0, str(HERE))
import doors  # noqa: E402
import greybox  # noqa: E402
import model  # noqa: E402
import placement  # noqa: E402
import room  # noqa: E402
from room import hub_kit  # noqa: E402


def on_wall(bearing, across, bottom, size, kind="hub_conduit_box"):
    laid = hub_kit.on_wall("x", bearing, across, bottom, size)
    laid["kind"] = kind
    return laid


def test_the_outer_skin_holds_the_room_and_not_what_is_past_its_walls():
    skin = room.outer_skin()
    assert skin.is_watertight
    inside = skin.contains(np.array([[0.0, 1.0, 0.0], [4.6, 1.5, 0.0], [0.0, 4.6, 0.0]]))
    outside = skin.contains(np.array([[5.2, 1.5, 0.0], [0.0, 6.0, 0.0]]))
    assert inside.all() and not outside.any()


def test_a_model_is_fitted_into_a_unit_box_on_its_foot():
    fitted = room.unit_fit(trimesh.creation.box(extents=(2.0, 4.0, 1.0)), np.eye(3))
    assert np.allclose(fitted.bounds, [[-0.5, 0.0, -0.5], [0.5, 1.0, 0.5]])


def test_a_ray_out_through_the_porthole_is_an_opening_and_one_beside_it_is_not():
    normal, along = hub_kit.bearing_vectors(hub_kit.PORTHOLE[0])
    origins = np.array([normal * 3.0 + np.array([0.0, hub_kit.PORTHOLE[1], 0.0]),
                        normal * 3.0 + along * 0.8 + np.array([0.0, hub_kit.PORTHOLE[1], 0.0])])
    through = greybox.through_opening(origins, np.array([normal, normal]), greybox.openings())
    assert through.tolist() == [True, False]


def test_a_box_in_front_of_the_porthole_clashes_and_one_beside_it_does_not():
    size = (0.2, 0.2, 0.1)
    layout = {"pieces": [on_wall(300, 0.0, 2.25, size), on_wall(300, 0.8, 2.25, size),
                         on_wall(300, 0.0, 1.75, (1.2, 1.2, 0.1), "hub_porthole_panel")]}
    assert [found[0] for found in placement.clashes(layout)] == [0]


def test_a_model_in_its_laid_proportions_passes_and_a_cube_laid_as_a_panel_fails():
    panel = model.check("hub_wall_upper_plain", trimesh.creation.box(extents=(1.2, 2.0, 0.06)), (1.2, 2.0, 0.06))
    cube = model.check("hub_wall_upper_plain", trimesh.creation.box(extents=(1.0, 1.0, 1.0)), (1.2, 2.0, 0.06))
    assert panel["pass"] and panel["watertight"] and abs(panel["thinnest"] - 0.06) < 0.005
    assert cube["spread"] > 0.2 and not cube["pass"]


def partition(across, wide, kind="mars_partition"):
    """A panel 2.6 m tall standing across the floor along x at z = 0, its middle at `across`."""
    return {"kind": kind, "at": [across, 0.0, 0.0], "x": [1.0, 0.0, 0.0], "y": [0.0, 1.0, 0.0], "z": [0.0, 0.0, 1.0],
            "size": [wide, 2.6, 0.08]}


def test_a_door_in_a_partition_that_stops_short_has_a_way_round_and_one_wall_to_wall_has_none():
    """A room 6 m wide (walls at x = +-3, closed at z = +-3) parted at z = 0 by a door and partition panels."""
    walls = [{"kind": "mars_wall_lower_plain", "at": at, "x": x, "y": [0.0, 1.0, 0.0], "z": z, "size": [6.0, 2.6, 0.08]}
             for at, x, z in (([3.0, 0.0, 0.0], [0.0, 0.0, 1.0], [-1.0, 0.0, 0.0]),
                              ([-3.0, 0.0, 0.0], [0.0, 0.0, -1.0], [1.0, 0.0, 0.0]),
                              ([0.0, 0.0, 3.0], [-1.0, 0.0, 0.0], [0.0, 0.0, -1.0]),
                              ([0.0, 0.0, -3.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]))]
    door = partition(0.0, 1.2, "mars_hatch_frame")
    whole = walls + [door, partition(-1.8, 2.4), partition(1.8, 2.4)]
    short = walls + [door, partition(-1.8, 2.4), partition(1.5, 1.2)]  # a 0.9 m gap at its right end
    assert doors.check({"pieces": whole}) == []
    assert len(doors.check({"pieces": short})) == 1
    screen = walls + [partition(-1.8, 2.4)]  # a screen with no door is not judged
    assert doors.check({"pieces": screen}) == []


def main():
    tests = [value for name, value in globals().items() if name.startswith("test_")]
    for test in tests:
        test()
    print(f"{len(tests)} checks passed")


if __name__ == "__main__":
    main()
