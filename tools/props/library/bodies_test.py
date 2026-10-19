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
CORE = [1.4, 2.3, 1.4]
FUEL = [0.9, 1.8, 0.9]
WATER = [1.6, 1.6, 1.6]
LANDER = [8.649, 19.0, 10.597]
ROVER = [1.72, 1.66, 3.03]
CRANE = [1.811, 3.2, 1.065]
# Each built body's laid size, by the first word of its builder.
SIZES = {"console": CONSOLE, "station": MODULE, "power": CORE, "fuel": FUEL, "water": WATER, "lander": LANDER,
         "rover": ROVER, "crane": CRANE}
# Each place's bake entry that names a body: (place, model, builder).
WIRED = (("cockpit", "main_console_1", "console_body"), ("old_station", "first_module", "station_module"),
         ("engineroom", "power_core_1", "power_core"), ("engineroom", "fuel_tank_1", "fuel_tank"),
         ("greenhouse", "water_tank_1", "water_tank"), ("campgrounds", "lander", "lander_body"),
         ("garage", "rover_1", "rover_body"), ("campgrounds", "crane", "crane_body"))
# The plan's kind for each builder (build_only builds the kind's part after its first underscore).
KINDS = {"console_body": "cockpit_console_body", "station_module": "station_station_module",
         "power_core": "engineroom_power_core", "fuel_tank": "engineroom_fuel_tank",
         "water_tank": "greenhouse_water_tank", "lander_body": "campgrounds_lander_body",
         "rover_body": "garage_rover_body", "crane_body": "campgrounds_crane_body"}


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


def test_the_core_the_water_tank_the_lander_and_the_crane_keep_nothing_of_their_takes():
    middles = np.zeros((2, 3))
    assert not bodies.kept("power_core", CORE, middles, ["clear_glass", "led_white"], []).any()
    assert not bodies.kept("water_tank", WATER, middles, ["dark_panel", "bare_steel"], []).any()
    assert not bodies.kept("lander_body", LANDER, middles, ["stainless", "stainless"], []).any()
    assert not bodies.kept("crane_body", CRANE, middles, ["cream_paint", "stainless"], []).any()


def test_the_core_s_lamps_sit_on_its_drums_and_its_pipes_stay_in_its_box():
    for low, high in bodies.CORE_LAMPS:
        assert bodies.CORE_PLINTH[0] < low < high <= bodies.CORE_HOOD[2]
    reach = max(abs(x) for run in bodies.CORE_PIPES for x, _ in run) + bodies.CORE_PIPE[0]
    assert reach < 0.5 and bodies.CORE_CANISTER["at"] + bodies.CORE_CANISTER["radius"] < 0.5


def test_the_fuel_tank_keeps_its_fittings_by_place_only():
    """Each FUEL_DETAILS box keeps the take's faces in it (its gauge, valve and pipe fittings); none elsewhere."""
    boxes = bodies.detail_boxes("fuel_tank", FUEL)
    assert len(boxes) == len(bodies.FUEL_DETAILS)
    inside = [[(low[axis] + high[axis]) / 2 for axis in range(3)] for low, high in boxes]
    found = bodies.kept("fuel_tank", FUEL, inside + [[0.0, -1.0, 0.0]], ["dark_panel"] * (len(boxes) + 1), [])
    assert found.tolist() == [True] * len(boxes) + [False], found


def test_the_lander_s_hull_stands_in_its_laid_box_and_closes_at_its_top():
    profile = np.array(bodies.lander_profile(LANDER))
    assert profile[0].tolist() == [0.0, bodies.LANDER_FOOT * LANDER[1]] and profile[-1].tolist() == [0.0, LANDER[1]]
    assert np.all(np.diff(profile[2:, 0]) < 0) and np.all(np.diff(profile[1:, 1]) >= 0)
    axis = bodies.LANDER_AXIS * LANDER[2]
    assert profile[:, 0].max() < LANDER[0] / 2 and axis + profile[:, 0].max() < LANDER[2] / 2


def test_the_lander_s_stencil_panel_is_flat_under_its_decal():
    """The decal (1.2 x 0.3 m at [0, 7.5], details.json campgrounds_lander) lies wholly on the panel cut flat into
    the hull's front, so the bake's clear_spot finds it flat where it was placed."""
    across, low, high = bodies.LANDER_PANEL
    assert across * LANDER[0] >= 0.6 and low * LANDER[1] <= 7.5 - 0.15 and high * LANDER[1] >= 7.5 + 0.15
    first, last, count = bodies.LANDER_SEAMS
    seams = [(first + (last - first) * step / (count - 1)) * LANDER[1] for step in range(count)]
    assert not any(low * LANDER[1] - 0.05 < seam < high * LANDER[1] + 0.05 for seam in seams), seams


def test_the_rover_keeps_its_seats_and_console_details_by_place_only():
    wide, tall, deep = ROVER
    x0, x1, y0, y1, z0, z1 = bodies.ROVER_DETAILS["seats"]
    on_a_seat = [0.0, (y0 + y1) / 2 * tall, (z0 + z1) / 2 * deep]
    tyre = [bodies.ROVER_TYRE[0] * wide - 0.05, bodies.ROVER_WHEEL[0] * tall, bodies.ROVER_AXLES[1] * deep]
    floor = [0.0, bodies.ROVER_FLOOR[0] * tall, 0.0]
    found = bodies.kept("rover_body", ROVER, [on_a_seat, tyre, floor], ["plastic_grey", "plastic_grey", "screen"], [])
    assert found.tolist() == [True, False, False], found
    assert set(bodies.ROVER_DETAIL_SURFACES) == set(bodies.ROVER_DETAILS)


def test_the_rover_s_detail_boxes_stand_in_its_laid_box():
    for low, high in bodies.detail_boxes("rover_body", ROVER):
        for axis in range(3):
            assert low[axis] < high[axis]
        assert -ROVER[0] / 2 <= low[0] and high[0] <= ROVER[0] / 2 and 0 <= low[1] and high[1] <= ROVER[1] + 1e-9
        assert -ROVER[2] / 2 <= low[2] and high[2] <= ROVER[2] / 2


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
            f"{builder}_1": {"route": "code", "kind": kind, "size": SIZES[builder.split("_")[0]], "laid": {}}
            for builder, kind in KINDS.items()}}))
        out = pathlib.Path(folder) / "built"
        done = subprocess.run([sys.executable, str(REPO / "tools/blender/session.py"), "batch",
                               str(HERE / "inside/build_only.py"), "--", str(REPO), str(plan), str(out)],
                              capture_output=True, text=True)
        assert done.returncode == 0, done.stdout[-2000:] + done.stderr[-2000:]
        built = {path.stem: trimesh.load(path, force="mesh") for path in out.glob("*.glb")}
        assert sorted(built) == sorted(f"{builder}_1" for builder in KINDS), sorted(built)
        for name, mesh in built.items():
            size = SIZES[name.split("_")[0]]
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
