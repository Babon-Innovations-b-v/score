"""Check the gates (room.py, greybox.py, placement.py, model.py) on cases whose answers are obvious.

The gates need numpy and trimesh, which only the prop environment has. Run by the gate with the system python, this
hands itself to the prop environment when the box has one, and says it skipped when it does not.
Run: python3 tools/props/gates/gates_test.py
"""
import json
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
import names  # noqa: E402
import greybox  # noqa: E402
import model  # noqa: E402
import placement  # noqa: E402
import room  # noqa: E402
import shell  # noqa: E402
import surface  # noqa: E402
from room import hub_kit  # noqa: E402
import room_kit  # noqa: E402


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
    layout = {"room": "hub", "pieces": [on_wall(300, 0.0, 2.25, size), on_wall(300, 0.8, 2.25, size),
                         on_wall(300, 0.0, 1.75, (1.2, 1.2, 0.1), "hub_porthole_panel")]}
    assert [found[0] for found in placement.clashes(layout)] == [0]


def bay_piece(kind, wall, across, bottom, size, out=0.0):
    """A piece of the garage (a rounded bay, its numbers from its inventory) against one of its walls."""
    return room_kit.on_side("garage", kind, room_kit.side_named(shell.rounded_numbers({"room": "garage"}), wall), across,
                            bottom, size, out=out)


def test_a_bay_s_wall_gear_is_judged_against_its_own_walls_not_the_hub_s():
    """The garage is a 14 by 12 m rounded room: a box flush on its east wall passes, one stood 0.4 m off it or turned
    on it fails, and its lining's panels lapping past their run do not reach past their wall."""
    kinds = {"garage_junction_box": {"group": "hangs"}, "garage_wall_lower_plain": {"group": "hangs"}}
    flush = bay_piece("junction_box", "east", 1.0, 1.2, (0.3, 0.4, 0.15), out=0.06)
    off = bay_piece("junction_box", "east", -1.0, 1.2, (0.3, 0.4, 0.15), out=0.46)
    turned = bay_piece("junction_box", "east", 2.0, 1.2, (0.3, 0.4, 0.15), out=0.06)
    turned["x"], turned["z"] = turned["z"], [-value for value in turned["x"]]
    panel = bay_piece("wall_lower_plain", "south", 4.0 - 0.6, 0.0, (1.2 + room_kit.LAP, 1.16, 0.06))  # its run ends 4 m out
    layout = {"room": "garage", "kinds": kinds, "pieces": [flush, off, turned, panel]}
    assert [found[0] for found in surface.faults(layout)] == [1, 2]


def test_a_roof_lamp_standing_up_to_a_flat_roof_plate_passes_and_one_hung_short_of_it_fails():
    """room_kit lays a roof row standing, its head at the roof: the hangar's flat roof is lined at 13 m."""
    plate = {"kind": "hangar_roof_face_panel", "at": [0.0, 12.975, -1.0], "x": [-1.0, 0.0, 0.0], "y": [0.0, 0.0, 1.0],
             "z": [0.0, 1.0, 0.0], "size": [2.0, 2.0, 0.05]}
    lamp = {"kind": "hangar_ceiling_lamp", "at": [0.0, 12.55, 0.0], "x": [1.0, 0.0, 0.0], "y": [0.0, 1.0, 0.0],
            "z": [0.0, 0.0, 1.0], "size": [0.5, 0.4, 0.5]}
    short = dict(lamp, at=[0.5, 12.2, 0.5])
    outside = dict(lamp, at=[3.0, 12.55, 0.0])  # under the roof door's opening, where no plate is
    layout = {"room": "hangar", "kinds": {}, "pieces": [plate, lamp, short, outside]}
    assert [found[0] for found in surface.faults(layout)] == [2, 3]


def test_a_bay_plate_laid_with_its_height_and_depth_swapped_is_too_thick_for_the_floor():
    """A machine bay's plate 3.2 by 4.6 m and 5 cm thick, set into the garage's floor, and the same row with its
    depth and height swapped (laid 4.6 m thick, its face 5 cm long)."""
    inventory_row = {"id": "machine_bay_plate", "made": "kit piece", "lies": "floor", "size": [3.2, 0.05, 4.6],
                     "at": [{"x": 0.0, "z": -0.9, "facing": 0}]}
    swapped = dict(inventory_row, size=[3.2, 4.6, 0.05])
    right = room_kit.flat_rows("garage", {"rows": [inventory_row]}, {"machine_bay_plate": inventory_row})
    wrong = room_kit.flat_rows("garage", {"rows": [swapped]}, {"machine_bay_plate": swapped})
    layout = {"room": "garage", "kinds": {}, "pieces": right + wrong}
    assert [found[0] for found in surface.faults(layout)] == [1]


def test_a_box_in_a_bay_s_doorway_clashes_and_the_lining_lapping_to_its_edge_does_not():
    """The garage's east hatch (2.2 m wide) and its south big door (5 m wide, 4 m high)."""
    box = bay_piece("parts_trolley", "east", 0.3, 0.0, (0.6, 0.9, 0.5), out=0.1)
    beside = bay_piece("parts_trolley", "east", 2.0, 0.0, (0.6, 0.9, 0.5), out=0.1)
    lapping = bay_piece("wall_lower_plain", "east", 1.1 + 0.6, 0.0, (1.2 + room_kit.LAP, 1.16, 0.06))
    post_in_door = bay_piece("wall_corner_post", "south", 1.0, 0.0, (0.2, 4.2, 0.2), out=0.06)
    post_beside = bay_piece("wall_corner_post", "south", 2.6, 0.0, (0.2, 4.2, 0.2), out=0.06)
    layout = {"room": "garage", "pieces": [box, beside, lapping, post_in_door, post_beside]}
    assert placement.clashes(layout) == [(0, "garage_parts_trolley", "doorway east"),
                                         (3, "garage_wall_corner_post", "big door south")]


def test_a_place_with_no_known_shell_or_a_kit_in_its_own_frame_is_not_judged():
    for layout in ({"room": "street", "pieces": []},
                   {"room": "garage", "pieces": [{"kind": "gdoor_wall_upper_plain"}]}):
        try:
            shell.walls(layout)
        except SystemExit:
            continue
        raise AssertionError(f"{layout['room']} was judged")


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


def raised(laid, up):
    return dict(laid, at=[laid["at"][0], laid["at"][1] + up, laid["at"][2]])


def test_an_upper_floor_s_door_is_judged_on_its_own_floor_and_not_on_the_walls_below_it():
    """The same 6 m room twice, the second 3 m up: its door wall to wall below, its partition stopping short above."""
    walls = [{"kind": "mars_wall_lower_plain", "at": at, "x": x, "y": [0.0, 1.0, 0.0], "z": z, "size": [6.0, 2.6, 0.08]}
             for at, x, z in (([3.0, 0.0, 0.0], [0.0, 0.0, 1.0], [-1.0, 0.0, 0.0]),
                              ([-3.0, 0.0, 0.0], [0.0, 0.0, -1.0], [1.0, 0.0, 0.0]),
                              ([0.0, 0.0, 3.0], [-1.0, 0.0, 0.0], [0.0, 0.0, -1.0]),
                              ([0.0, 0.0, -3.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]))]
    ground = walls + [partition(0.0, 1.2, "mars_hatch_frame"), partition(-1.8, 2.4), partition(1.8, 2.4)]
    upper = [raised(laid, 3.0) for laid in walls + [partition(0.0, 1.2, "mars_hatch_frame"), partition(-1.8, 2.4),
                                                    partition(1.5, 1.2)]]
    found = doors.check({"pieces": ground + upper})
    assert [at[1] for _, at, _ in found] == [3.0]


def test_a_door_whose_sides_both_stand_in_walls_is_unknown_and_fails():
    door = partition(0.0, 1.2, "mars_hatch_frame")
    block = {"kind": "mars_wall_block", "at": [0.0, 0.0, 0.0], "x": [1.0, 0.0, 0.0], "y": [0.0, 1.0, 0.0],
             "z": [0.0, 0.0, 1.0], "size": [4.0, 2.6, 6.0]}
    found = doors.check({"pieces": [door, block]})
    assert len(found) == 1 and found[0][2].startswith("unknown")


def test_every_kit_layout_s_doors_part_their_two_sides():
    """The gate runs the door check on every installed kit layout (data/kit), not only by hand."""
    for path in sorted((HERE.parents[2] / "data/kit").glob("*.json")):
        assert doors.check(json.loads(path.read_text())) == [], path.name


def test_a_model_under_another_kind_s_name_and_a_name_on_two_routes_fail_before_install():
    """The camp's rod lamp baked as pendant_lamp_1; the stairwell's code junction box beside the lab's generated one."""
    camp = {"pieces": [{"kind": "camp_rod_lamp", "model": "pendant_lamp_1"}], "models": {"pendant_lamp_1": {"route": "code"}}}
    assert len(names.check(camp, "camp", others={}, texts={}, fittings={"pendant_lamp"})) == 1
    assert names.check(camp, "camp", others={}, texts={}, fittings=set()) == []  # a name nothing else uses
    stairwell = {"pieces": [{"kind": "stairwell_junction_box", "model": "junction_box_1"}],
                 "models": {"junction_box_1": {"route": "code"}}}
    lab = {"pieces": [{"kind": "lab_junction_box", "model": "junction_box_1"}], "models": {"junction_box_1": {"route": "model"}}}
    assert len(names.check(stairwell, "stairwell", others={"lab": lab}, texts={}, fittings=set())) == 1
    hub = {"pieces": [{"kind": "hub_pipe_straight", "model": "pipe_straight_1"}], "models": {"pipe_straight_1": {"route": "code"}}}
    lab_pipes = {"pieces": [{"kind": "lab_pipe_straight", "model": "pipe_straight_1"}],
                 "models": {"pipe_straight_1": {"route": "code"}}}
    assert names.check(hub, "hub", others={"lab": lab_pipes}, texts={}, fittings=set()) == []
    twice = 'def lamp(size, laid):\n    pass\n\n\ndef lamp(size, laid):\n    pass\n\n\nBUILDERS = {"lamp": lamp}\n'
    assert len(names.check(hub, "hub", others={}, texts={"pieces": twice}, fittings=set())) == 1


def main():
    tests = [value for name, value in globals().items() if name.startswith("test_")]
    for test in tests:
        test()
    print(f"{len(tests)} checks passed")


if __name__ == "__main__":
    main()
