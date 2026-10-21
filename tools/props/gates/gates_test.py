"""Check the gates (room.py's model fit, model.py) on cases whose answers are obvious. The kit rooms' own gates
(greybox, placement, surface, shell, round_room, tube, density, doors, names) went with the old kits (2026-10-21).

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
import model  # noqa: E402
import room  # noqa: E402


def test_a_model_is_fitted_into_a_unit_box_on_its_foot():
    fitted = room.unit_fit(trimesh.creation.box(extents=(2.0, 4.0, 1.0)), np.eye(3))
    assert np.allclose(fitted.bounds, [[-0.5, 0.0, -0.5], [0.5, 1.0, 0.5]])


def test_a_model_in_its_laid_proportions_passes_and_a_cube_laid_as_a_panel_fails():
    panel = model.check("hub_wall_upper_plain", trimesh.creation.box(extents=(1.2, 2.0, 0.06)), (1.2, 2.0, 0.06))
    cube = model.check("hub_wall_upper_plain", trimesh.creation.box(extents=(1.0, 1.0, 1.0)), (1.2, 2.0, 0.06))
    assert panel["pass"] and panel["watertight"] and abs(panel["thinnest"] - 0.06) < 0.005
    assert cube["spread"] > 0.2 and not cube["pass"]


def main():
    tests = [value for name, value in globals().items() if name.startswith("test_")]
    for test in tests:
        test()
    print(f"{len(tests)} checks passed")


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[3] / "conftest.py"))["refuse_outside_sandbox"]()
    main()
