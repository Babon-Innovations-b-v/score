"""Check the ship rooms' kit layouts (ship_kit.py) on a bridge-shaped room: every piece stands in a square,
right-handed frame inside the room, the floor and the ceiling cover the outline without gaps, the walls run round it
with the doorway left clear, the glazed walls hold their windows, every row the inventory places is laid, and the
shell's plain plates take the names the route builds in code.

Needs numpy, which only the prop environment has: run by the gate with the system python, this hands itself to the
prop environment when the box has one, and says it skipped when it does not.
Run: python3 tools/props/scene/ship_kit_test.py
"""
import os
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
PROPS_PYTHON = pathlib.Path(os.environ.get("PROPS_PYTHON", pathlib.Path.home() / ".farm-factory-props/env/bin/python"))

try:
    import numpy as np
except ImportError:
    if PROPS_PYTHON.exists() and os.environ.get("SHIP_KIT_TEST_HANDED") != "1":
        os.environ["SHIP_KIT_TEST_HANDED"] = "1"
        os.execv(str(PROPS_PYTHON), [str(PROPS_PYTHON), __file__])
    print("skipped: no prop environment on this box")
    sys.exit(0)

sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "library"))
import ship_kit  # noqa: E402
import sorter  # noqa: E402

ROOM = "bridge"
PLAN = {"title": "BRIDGE", "w": 4.6, "d": 4.6, "height": "ceiling 2.5 m",
        "kit": {"nose_cut": 0.9, "sill": 1.1, "head": 2.1, "pillar": 0.1},
        "doors": [["N", 2.3, 1.2, "AFT DOOR 1.2 x 2.2 m"]]}


def row(row_id, size, at, **more):
    return {"id": row_id, "size": size, "made": "kit piece", "at": at, **more}


INVENTORY = {"rows": [
    row("ring_floor_plate", [1.2, 0.04, 1.2], []), row("roof_face_panel", [1.2, 0.04, 1.2], []),
    row("pilot_seat", [0.7, 0.8, 1.25], [{"x": -0.95, "y": 0.0, "z": 1.0, "facing": 180},
                                         {"x": 0.95, "y": 0.0, "z": 1.0, "facing": 180}], solid=True),
    row("main_console", [2.8, 0.65, 1.05], [{"x": 0.0, "y": 0.0, "z": 1.975, "facing": 0}], solid=True),
    row("floor_grate", [1.2, 0.04, 0.6], [{"x": 0.0, "y": 0.0, "z": 0.2, "facing": 0}], lies="floor"),
]}
CEILING = 2.5
OUTLINE = [np.array(point) for point in ((-2.3, -2.3), (2.3, -2.3), (2.3, 1.4), (1.4, 2.3), (-1.4, 2.3), (-2.3, 1.4))]


def laid():
    return ship_kit.layout(ROOM, PLAN, INVENTORY)


def corners(piece):
    """A laid piece's eight box corners: from its origin at the middle of its foot, x by its wide, y up its tall, z
    by its deep; a tapered plate's head as wide as its taper."""
    origin, x_axis, y_axis, z_axis = (np.array(piece[key]) for key in ("at", "x", "y", "z"))
    wide, tall, deep = piece["size"]
    found = []
    for up in (0.0, tall):
        half = wide / 2 * (piece.get("taper", 1.0) if up else 1.0)
        for across in (-half, half):
            for back in (-deep / 2, deep / 2):
                found.append(origin + x_axis * across + y_axis * up + z_axis * back)
    return found


def inside(point, margin):
    """Whether a point (x, z) lies inside the outline, or within `margin` outside it."""
    for index, start in enumerate(OUTLINE):
        end = OUTLINE[(index + 1) % len(OUTLINE)]
        along = (end - start) / np.linalg.norm(end - start)
        outward = np.array([along[1], -along[0]])
        if (point - start) @ outward > margin:
            return False
    return True


def area(points):
    return 0.5 * abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(points, points[1:] + points[:1])))


def test_every_piece_stands_in_a_square_right_handed_frame():
    for piece in laid()["pieces"]:
        axes = [np.array(piece[axis]) for axis in "xyz"]
        assert all(abs(np.linalg.norm(axis) - 1.0) < 1e-4 for axis in axes), piece["kind"]
        assert abs(np.dot(np.cross(axes[0], axes[1]), axes[2]) - 1.0) < 1e-4, piece["kind"]
        assert all(side > 0 for side in piece["size"]), piece["kind"]


def test_nothing_reaches_out_of_the_room():
    for piece in laid()["pieces"]:
        for corner in corners(piece):
            assert inside(corner[[0, 2]], 0.1), (piece["kind"], piece["at"])
            assert -0.1 <= corner[1] <= CEILING + 0.1, (piece["kind"], piece["at"])


def test_the_floor_and_the_ceiling_cover_the_outline():
    for kind in ("ring_floor_plate", "roof_face_panel"):
        plates = [piece for piece in laid()["pieces"] if piece["kind"] == f"{ROOM}_{kind}"]
        covered = sum(piece["size"][0] * piece["size"][1] * (1 + piece["taper"]) / 2 for piece in plates)
        assert abs(covered - area(OUTLINE)) < 1e-3, (kind, covered, area(OUTLINE))


def test_the_walls_run_round_the_room_with_the_doorway_clear():
    pieces = laid()["pieces"]
    lower = [piece for piece in pieces if piece["kind"] == f"{ROOM}_wall_lower_plain"]
    run = sum(piece["size"][0] - ship_kit.LAP for piece in lower)
    perimeter = sum(np.linalg.norm(OUTLINE[(index + 1) % 6] - point) for index, point in enumerate(OUTLINE))
    assert abs(run - (perimeter - 1.2)) < 1e-3, (run, perimeter)
    for piece in lower:
        x, _, z = piece["at"]
        assert not (abs(x) < 0.6 - 1e-3 and z < -2.0), piece["at"]  # nothing low in the aft doorway


def test_the_glazed_walls_hold_their_windows():
    panes = [piece for piece in laid()["pieces"] if piece["kind"] == f"{ROOM}_window_pane"]
    assert len(panes) == 4  # two in the front, one in each cut corner
    for pane in panes:
        assert pane["at"][2] > 1.3 and abs(pane["at"][1] - 1.15) < 1e-6, pane["at"]


def test_every_row_the_inventory_places_is_laid():
    counts = laid()["counts"]
    assert counts[f"{ROOM}_pilot_seat"] == 2 and counts[f"{ROOM}_main_console"] == 1, counts


def test_the_grate_lies_set_into_the_deck():
    """The grate lies flat with its face flush with the deck's, and the deck plates under it are cut to the grate itself
    (ship_kit.SET_IN_GAP: no seam round it, the ship stands on no ground)."""
    pieces = laid()["pieces"]
    grate = next(piece for piece in pieces if piece["kind"] == f"{ROOM}_floor_grate")
    assert grate.get("set_in") and grate["z"] == [0.0, -1.0, 0.0], grate
    cut = [piece for piece in pieces if piece["kind"] == f"{ROOM}_ring_floor_plate" and piece.get("openings")]
    area = sum((high_x - low_x) * (high_y - low_y) for piece in cut for low_x, low_y, high_x, high_y in piece["openings"])
    gap = ship_kit.SET_IN_GAP
    assert abs(area - (1.2 + 2 * gap) * (0.6 + 2 * gap)) < 1e-3, area


def test_the_shell_s_plain_plates_are_built_in_code():
    routes = {kind: entry["route"] for kind, entry in sorter.sorted_kinds(laid()).items()}
    for own in ("wall_lower_plain", "wall_upper_plain", "ring_floor_plate", "roof_face_panel"):
        assert routes[f"{ROOM}_{own}"] == "code", own
    assert routes[f"{ROOM}_pilot_seat"] == "model"


TAPERED = {"title": "COCKPIT", "w": 6.53, "d": 3.0, "height": "ceiling 2.43 m at the back",
           "kit": {"front_wide": 5.69, "glazed": "roof", "ceiling_front": 1.82, "windows_from": 0.6},
           "doors": [["N", 3.265, 0.9, "AFT DOOR 0.9 x 2.0 m"]]}
TAPERED_INVENTORY = {"rows": [row("ring_floor_plate", [1.2, 0.04, 1.2], []), row("roof_face_panel", [1.2, 0.04, 1.2], [])]}


def tapered_pieces(kind):
    return [piece for piece in ship_kit.layout("cockpit", TAPERED, TAPERED_INVENTORY)["pieces"]
            if piece["kind"] == f"cockpit_{kind}"]


def test_a_tapered_room_s_floor_covers_its_outline():
    covered = sum(piece["size"][0] * piece["size"][1] * (1 + piece["taper"]) / 2
                  for piece in tapered_pieces("ring_floor_plate"))
    assert abs(covered - (6.53 + 5.69) / 2 * 3.0) < 1e-3, covered


def test_a_room_widening_to_its_front_covers_its_outline():
    """The engine room widens toward its front (6.02 m at the back, 7.43 m at the front): its first side strips start
    at a point and are laid from their front, and the floor still covers the outline."""
    widening = {**TAPERED, "w": 6.02, "d": 4.1, "kit": {"front_wide": 7.43, "glazed": "none", "ceiling_front": 3.2}}
    pieces = [piece for piece in ship_kit.layout("engineroom", widening, TAPERED_INVENTORY)["pieces"]
              if piece["kind"] == "engineroom_ring_floor_plate"]
    covered = sum(piece["size"][0] * piece["size"][1] * (1 + piece["taper"]) / 2 for piece in pieces)
    assert abs(covered - (6.02 + 7.43) / 2 * 4.1) < 1e-3, covered


def test_a_tapered_room_s_roof_slopes_under_its_ceiling_with_its_windows():
    """The roof, its windows and ribs lie on the sloping ceiling (2.43 m at the back to 1.82 m at the front), inside the
    walls; four lights, two either side of a rib in each of the two glazed rows, and a cross rib between the rows."""
    assert len(tapered_pieces("window_pane")) == 4 and len(tapered_pieces("frame_rib")) == 3
    for kind in ("roof_face_panel", "window_pane", "frame_rib"):
        for piece in tapered_pieces(kind):
            for corner in corners(piece):
                ceiling = ship_kit.ceiling_at(TAPERED, corner[2])
                assert abs(corner[1] - ceiling) < 0.25, (kind, corner, ceiling)
                assert abs(corner[0]) <= ship_kit.half_at(TAPERED, corner[2]) + 0.1, (kind, corner)
                assert abs(corner[2]) <= 1.5 + 0.1, (kind, corner)


def test_a_tapered_room_s_upper_wall_plates_reach_the_ceiling():
    for piece in tapered_pieces("wall_upper_plain"):
        x, y, z = piece["at"]
        assert abs(y + piece["size"][1] - ship_kit.ceiling_at(TAPERED, z)) < 0.05, piece["at"]


CORRIDOR = {"title": "A CORRIDOR", "w": 1.2, "d": 6.0, "height": "ceiling 2.4 m", "kit": {"nose_cut": 0.0},
            "doors": [["W", 3.0, 0.9, "DOOR 0.9 x 2.0 m"], ["S", 0.6, 0.9, "DOOR 0.9 x 2.0 m"]]}


def test_a_room_s_ruled_plain_rows_are_laid_from_its_plan():
    rows = {"rows": [
        row("edge_light_strip", [5.6, 0.06, 0.05], [], count=2, anchor="wall"),
        row("ceiling_light_panel", [1.4, 0.2, 0.05], [], count=3, anchor="ceiling"),
        row("frame_rib", [1.2, 0.12, 2.4], [], count=3, anchor="wall"),
        row("floor_grate", [0.6, 0.04, 1.2], [], count=4, anchor="floor")]}
    spots = {found["id"]: found["at"] for found in ship_kit.with_ruled_spots(CORRIDOR, rows)["rows"]}
    assert len(spots["edge_light_strip"]) == 2 and {spot["facing"] for spot in spots["edge_light_strip"]} == {90, 270}
    panels = spots["ceiling_light_panel"]
    assert len(panels) == 3 and all(spot["size"][0] <= 1.0 for spot in panels)  # never wider than the corridor
    assert all(abs(spot["z"]) < 3.0 for spot in panels + spots["floor_grate"])
    ribs = spots["frame_rib"]
    middle = [spot for spot in ribs if abs(spot["z"]) < 0.5]  # the rib at the west door: no bar in its doorway
    assert not any(spot["x"] < -0.3 for spot in middle), middle
    assert len(ribs) == 3 + 3 + 2  # a ceiling bar each, an east bar each, a west bar where no door is
    for spot in ribs:
        if spot["x"]:  # a side bar stands up its wall to the ceiling, half in the wall's lining and half out
            assert spot["size"][1] > 2.0 and spot["size"][2] == ship_kit.RIB_BAR, spot
            assert abs(abs(spot["x"]) - (CORRIDOR["w"] / 2 - ship_kit.WALL_DEEP)) < 1e-9, spot


def test_a_glazed_roof_s_frame_ribs_are_its_own_not_ruled():
    """The cockpit's frame ribs are the ones between its roof's lights: no corridor bars across it or down its walls."""
    ribbed = {"rows": TAPERED_INVENTORY["rows"] + [row("frame_rib", [0.15, 0.2, 1.4], [], count=3, anchor="ceiling")]}
    pieces = [piece for piece in ship_kit.layout("cockpit", TAPERED, ribbed)["pieces"]
              if piece["kind"] == "cockpit_frame_rib"]
    assert len(pieces) == len(tapered_pieces("frame_rib")) == 3


def test_a_raised_deck_and_its_step_face_are_laid():
    plan = dict(CORRIDOR, kit={"nose_cut": 0.0, "step": {"up": 0.4, "at": 1.0}})
    raised = ship_kit.raised_deck("corridor", plan, "ring_floor_plate", 0.04)
    assert raised and all(abs(piece["at"][1] - 0.38) < 0.01 for piece in raised)  # its top at the step's height
    assert min(piece["at"][2] for piece in raised) <= -2.9  # from the back wall
    faces = ship_kit.ruled_spots(plan, {"id": "pit_wall_panel", "size": [1.2, 0.06, 0.4], "count": 2})
    assert len(faces) == 2 and all(spot["z"] == 1.0 and spot["size"][2] == 0.4 for spot in faces)
    assert abs(sum(spot["size"][0] for spot in faces) - 1.2) < 1e-9  # across the whole room


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[3] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
