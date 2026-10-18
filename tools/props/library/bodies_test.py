"""Check the code-built bodies of big objects seen up close (inside/bodies.py, inside/pieces_bodies.py, the bake's
make_chunky.make_bodied): which of a take's faces each body keeps, the places' bake entries that name a body, and
each body built at its laid size in headless Blender (inside/build_only.py, geometry only, no bake) with walls the
model check passes.

Needs Blender (tools/blender/session.py batch) and trimesh for the build; the rest runs on numpy alone. Run with the
system python it hands itself to the prop environment, and says it skipped the build on a box without either.
Run: python3 tools/props/library/bodies_test.py
"""
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
PROPS_PYTHON = pathlib.Path(os.environ.get("PROPS_PYTHON", pathlib.Path.home() / ".farm-factory-props/env/bin/python"))
try:
    import numpy as np
    import trimesh
except ImportError:
    if PROPS_PYTHON.exists() and os.environ.get("BODIES_TEST_HANDED") != "1":
        os.environ["BODIES_TEST_HANDED"] = "1"
        os.execv(str(PROPS_PYTHON), [str(PROPS_PYTHON), __file__])
    print("skipped: no prop environment on this box")
    sys.exit(0)

sys.path.insert(0, str(HERE / "inside"))
import bodies  # noqa: E402

sys.path.insert(0, str(HERE.parent / "gates"))
import model as model_check  # noqa: E402

CONSOLE = [3.6, 1.0, 0.65]
MODULE = [6.5, 4.308, 3.783]
# Each place's bake entry that names a body: (place, model, builder).
WIRED = (("cockpit", "main_console_1", "console_body"), ("old_station", "first_module", "station_module"))


def test_the_console_keeps_its_controls_anywhere_and_its_bays_details_only():
    wide, tall, deep = CONSOLE
    bay_low, bay_high = bodies.console_bays(CONSOLE)["middle_bay"]
    in_bay = [0.0, (bay_low[1] + bay_high[1]) / 2, bay_high[2] - 0.01]
    behind_bay = [0.0, in_bay[1], bay_high[2] + 0.05]
    on_the_back = [0.0, 0.5, deep / 2 - 0.01]
    middles = [in_bay, behind_bay, on_the_back, on_the_back]
    surfaces = ["dark_panel", "dark_panel", "dark_panel", "led_red"]
    found = bodies.kept("console_body", CONSOLE, middles, surfaces, ["led_red"])
    assert found.tolist() == [True, False, False, True], found


def test_the_console_s_crown_keeps_its_light_strip():
    wide, tall, deep = CONSOLE
    x0, x1, y0, y1, front = bodies.CONSOLE_CROWN_BLOCK
    strip = [0.0, (y0 + y1) / 2 * tall, front * deep - 0.01]
    assert bodies.kept("console_body", CONSOLE, [strip], ["dark_panel"], []).tolist() == [True]


def test_the_console_s_outline_stands_in_its_laid_box():
    points = np.array(bodies.console_outline(CONSOLE))
    assert np.isclose(points[:, 0].min(), -CONSOLE[0] / 2) and np.isclose(points[:, 0].max(), CONSOLE[0] / 2)
    assert points[:, 1].min() == 0.0 and np.isclose(points[:, 1].max(), bodies.CONSOLE_TOP * CONSOLE[1])
    for low, high in bodies.console_bays(CONSOLE).values():
        assert -CONSOLE[0] / 2 < low[0] < high[0] < CONSOLE[0] / 2 and 0 < low[1] < high[1] < CONSOLE[1]


def test_the_module_keeps_nothing_of_its_take():
    middles = np.zeros((3, 3))
    assert not bodies.kept("station_module", MODULE, middles, ["mli_gold", "mli_silver", "galvanized_dull"],
                           []).any()


def test_the_module_s_blankets_and_holes_follow_its_grid():
    blankets = bodies.module_foil(MODULE)
    letters = sum(cells.count("S") + cells.count("G") for cells in bodies.MODULE_FOIL)
    step = (bodies.MODULE_HULL[1] - bodies.MODULE_HULL[0]) * MODULE[0] / len(bodies.MODULE_FOIL[0])
    assert round(sum(end - start for _, _, _, start, end in blankets) / step) == letters
    assert {surface for surface, *_ in blankets} == {"mli_silver", "mli_gold"}
    holes = bodies.module_holes(MODULE)
    assert len(holes) == 1 and holes[0][:2] == (30.0, 60.0), holes


def test_every_wired_body_is_built_by_a_body_builder_and_its_turn_is_a_turn():
    """Each place's model named in WIRED is baked from a take BODIES builds over a body (the registry lives in the
    bake's folder, bodies.py, not in the place's data), with a builder pieces_bodies has and a turn that is a turn."""
    builders = re.findall(r'"(\w+)": \w+', (HERE / "inside/pieces_bodies.py").read_text().split("BUILDERS = ", 1)[1])
    for place, model, builder in WIRED:
        bake = json.loads((REPO / f"data/surfaces/{place}.json").read_text())["bake"]
        take = bake.get("models", {}).get(model, model)
        body = bodies.body_of(take)
        assert body is not None and body["builder"] == builder and builder in builders, (place, take, body)
        turn = np.array(bodies.laid_turn(take, np.eye(3).flatten().tolist())).reshape(3, 3)
        assert np.allclose(turn @ turn.T, np.eye(3)) and np.isclose(np.linalg.det(turn), 1.0), (place, turn)
        assert builder in bodies.DETAILS


def test_every_body_builds_with_walls_the_model_check_passes():
    if not (REPO / "tools/blender/session.py").exists():
        print("skipped: no Blender launcher")
        return
    with tempfile.TemporaryDirectory() as folder:
        plan = pathlib.Path(folder) / "plan.json"
        plan.write_text(json.dumps({"models": {
            "console_body_1": {"route": "code", "kind": "cockpit_console_body", "size": CONSOLE, "laid": {}},
            "station_module_1": {"route": "code", "kind": "old_station_station_module", "size": MODULE,
                                 "laid": {}}}}))
        out = pathlib.Path(folder) / "built"
        done = subprocess.run([sys.executable, str(REPO / "tools/blender/session.py"), "batch",
                               str(HERE / "inside/build_only.py"), "--", str(REPO), str(plan), str(out)],
                              capture_output=True, text=True)
        assert done.returncode == 0, done.stdout[-2000:] + done.stderr[-2000:]
        built = {path.stem: trimesh.load(path, force="mesh") for path in out.glob("*.glb")}
        assert sorted(built) == ["console_body_1", "station_module_1"], sorted(built)
        for name, mesh in built.items():
            size = CONSOLE if name.startswith("console") else MODULE
            # Within its laid box and filling most of it: a body drops the take's lumps (the module's foil flaps
            # stood 23 cm over its hull), never grows past them.
            assert np.all(mesh.extents <= np.array(size) + 0.01), (name, mesh.extents)
            assert np.all(mesh.extents >= np.array(size) * 0.85), (name, mesh.extents)
            thinnest = model_check.thinnest(mesh, mesh.extents)
            assert thinnest >= model_check.THINNEST_LIMIT, (name, thinnest)


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(REPO / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
