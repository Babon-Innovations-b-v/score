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


def test_the_shell_s_plain_plates_are_built_in_code():
    routes = {kind: entry["route"] for kind, entry in sorter.sorted_kinds(laid()).items()}
    for own in ("wall_lower_plain", "wall_upper_plain", "ring_floor_plate", "roof_face_panel"):
        assert routes[f"{ROOM}_{own}"] == "code", own
    assert routes[f"{ROOM}_pilot_seat"] == "model"


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
