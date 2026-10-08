"""Check the greenhouse's kit layout (greenhouse_kit.py): no deck plate lies under the plot's beds, and every piece
stands inside the room. (Its rises and robot station against the game's own scripts are checked in the game 2099.)

The game's numbers are read from its own scripts, so a change there that the layout missed fails here. The checks need
numpy, which only the prop environment has: run by the gate with the system python, this hands itself to the prop
environment when the box has one, and says it skipped when it does not.
Run: python3 tools/props/scene/greenhouse_kit_test.py
"""
import json
import os
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
PROPS_PYTHON = pathlib.Path(os.environ.get("PROPS_PYTHON", pathlib.Path.home() / ".farm-factory-props/env/bin/python"))

try:
    import numpy as np
except ImportError:
    if PROPS_PYTHON.exists() and os.environ.get("GREENHOUSE_KIT_TEST_HANDED") != "1":
        os.environ["GREENHOUSE_KIT_TEST_HANDED"] = "1"
        os.execv(str(PROPS_PYTHON), [str(PROPS_PYTHON), __file__])
    print("skipped: no prop environment on this box")
    sys.exit(0)

sys.path.insert(0, str(HERE))
import greenhouse_kit as kit  # noqa: E402

INVENTORY = json.loads((REPO / "data/inventory/greenhouse.json").read_text())
PIECES = kit.laid_out(INVENTORY)


def constant(script, name):
    """A number or a Vector3/Vector2 constant of a GDScript, as a float or a tuple."""
    text = (REPO / script).read_text()
    found = re.search(rf"^const {name}\s*(?::\s*\w+)?\s*:=\s*(.+)$", text, re.MULTILINE)
    assert found, f"{name} not in {script}"
    value = found.group(1).strip()
    vector = re.match(r"Vector[23]i?\(([^)]*)\)", value)
    if vector:
        return tuple(float(part) for part in vector.group(1).split(","))
    return float(value)


def own(laid):
    return laid["kind"].split("_", 1)[1]


def middle(laid):
    return np.asarray(laid["at"]) + np.asarray(laid["y"]) * laid["size"][1] / 2


def test_every_piece_stands_in_a_square_right_handed_frame():
    """A mirrored frame draws a piece's faces inside out; a skewed one shears its model (the grow light bars, their
    lenses and the booms were mirrored, the node plates near the dome's top up to 8% off square, 2026-10-08)."""
    for laid in PIECES:
        axes = np.array([laid["x"], laid["y"], laid["z"]])
        assert np.allclose(axes @ axes.T, np.eye(3), atol=1e-3), laid["kind"]
        assert np.linalg.det(axes) > 0.99, laid["kind"]


def test_every_rise_top_has_a_surface_at_its_height():
    tops = [laid for laid in PIECES if own(laid) in ("ring_floor_plate", "ledge_cover")]
    for rise in kit.rises():
        x = (rise["x"][0] + rise["x"][1]) / 2
        z = (rise["z"][0] + rise["z"][1]) / 2
        covering = [laid for laid in tops if abs(laid["at"][1] + laid["size"][2] / 2 - rise["top"]) < 1e-3 and
                    abs(laid["at"][0] - x) <= laid["size"][0] / 2 + 0.7 and
                    laid["at"][2] - 0.01 <= z <= laid["at"][2] + laid["size"][1] + 0.7]
        assert covering, f"nothing on the {rise['part']} at {x:.2f}, {z:.2f}"


def test_no_deck_plate_lies_under_the_beds():
    for laid in PIECES:
        if own(laid) != "ring_floor_plate":
            continue
        x, z = laid["at"][0], laid["at"][2] + laid["size"][1] / 2
        assert not (kit.PLOT[0] < x < kit.PLOT[1] and kit.PLOT[2] < z < kit.PLOT[3]), f"a plate under the beds: {x}, {z}"


def test_every_piece_stands_inside_the_room():
    for laid in PIECES:
        point = middle(laid)
        assert kit.inside_room(point[0], point[2], -0.2), f"{laid['kind']} outside the room at {point}"
        assert -0.3 <= point[1] <= 6.3, f"{laid['kind']} at height {point[1]}"  # a duct box hangs under the deck


def test_the_gantry_hangs_under_the_dome():
    layout = INVENTORY["room"]["layout"]
    for laid in PIECES:
        if own(laid) == "rig_hanger":
            top = laid["at"][1] + laid["size"][1]
            assert abs(top - kit.dome_height(layout, laid["at"][0], laid["at"][2])) < 1e-3


def main():
    tests = [value for name, value in globals().items() if name.startswith("test_")]
    for test in tests:
        test()
    print(f"{len(tests)} greenhouse kit checks pass")


if __name__ == "__main__":
    main()
