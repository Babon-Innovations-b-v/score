"""Check the hub's kit layout (hub_kit.py): the room's surfaces are one partition of made pieces, every piece's frame is
square, and the layout lays out exactly what the inventory lists.

The checks need numpy, which only the prop environment has. Run by the gate with the system python, this hands itself to
the prop environment when the box has one, and says it skipped when it does not.
Run: python3 tools/props/scene/hub_kit_test.py
"""
import json
import os
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
PROPS_PYTHON = pathlib.Path(os.environ.get("PROPS_PYTHON", pathlib.Path.home() / ".farm-factory-props/env/bin/python"))

try:
    import numpy as np  # noqa: F401
except ImportError:
    if PROPS_PYTHON.exists() and os.environ.get("HUB_KIT_TEST_HANDED") != "1":
        os.environ["HUB_KIT_TEST_HANDED"] = "1"
        os.execv(str(PROPS_PYTHON), [str(PROPS_PYTHON), __file__])
    print("skipped: no prop environment on this box")
    sys.exit(0)

sys.path.insert(0, str(HERE))
import hub_kit  # noqa: E402

INVENTORY = json.loads(hub_kit.INVENTORY.read_text())
PIECES = hub_kit.laid_out(INVENTORY)


def test_the_rooms_surfaces_are_one_partition_of_made_pieces():
    score = hub_kit.partition_score(PIECES)
    assert score["all"]["coverage"] >= 0.99, score["all"]
    assert score["all"]["overlap"] <= 0.02, score["all"]
    for surface in ("walls", "roof"):
        assert score[surface]["coverage"] >= 0.999, (surface, score[surface])


def test_every_piece_stands_in_a_square_frame():
    for found in PIECES:
        axes = np.array([found["x"], found["y"], found["z"]])
        assert np.allclose(axes @ axes.T, np.eye(3), atol=1e-3), found["kind"]
        assert np.linalg.det(axes) > 0, found["kind"]
        assert all(side > 0 for side in found["size"]), found["kind"]


def test_the_layout_lays_out_what_the_inventory_lists():
    laid = {}
    for found in PIECES:
        laid[found["kind"]] = laid.get(found["kind"], 0) + 1
    listed = {f"hub_{row['id']}": row["count"] for row in INVENTORY["rows"] if row.get("made") == "kit piece"}
    assert laid == listed, {kind: (laid.get(kind), listed.get(kind)) for kind in set(laid) | set(listed)
                            if laid.get(kind) != listed.get(kind)}


def test_the_game_layout_stands_every_piece_laid_out_now_each_on_its_made_model():
    written = json.loads(hub_kit.GAME_LAYOUT.read_text())
    whole = [found for found in written["pieces"] if "part" not in found]
    laid = {}
    for found in PIECES:
        laid[found["kind"]] = laid.get(found["kind"], 0) + 1
    assert written["counts"] == laid
    assert len(whole) == len(PIECES)
    assert all(found["model"] in written["models"] for found in written["pieces"])


def test_every_set_in_fitting_lies_flush_in_an_opening_cut_in_its_host():
    assert hub_kit.standing_proud(PIECES) == []
    assert any(found.get("set_in") for found in PIECES)


def test_a_doors_parts_go_with_its_leaf_when_it_stands_open():
    kinds = hub_kit.kit_kinds(INVENTORY)
    found = hub_kit.doors(kinds, INVENTORY)
    leaves = [piece for piece in found if piece["kind"] == "hub_hatch_leaf"]
    wheels = [piece for piece in found if piece["kind"] == "hub_hatch_wheel"]
    for leaf in leaves:
        nearest = min(wheels, key=lambda wheel: np.linalg.norm(np.subtract(wheel["at"], leaf["at"])))
        assert np.allclose(nearest["z"], leaf["z"], atol=1e-6), "a wheel faces the way its leaf does"


def main():
    tests = [value for name, value in globals().items() if name.startswith("test_")]
    for test in tests:
        test()
    print(f"{len(tests)} checks passed")


if __name__ == "__main__":
    main()
