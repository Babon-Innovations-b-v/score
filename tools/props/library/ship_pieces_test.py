"""Check the ship rooms' code builders (inside/pieces_ship.py): each of the nine plain kinds builds at the bridge's laid
size in headless Blender (inside/build_only.py, geometry only, no bake, as route.py precheck builds), its glowing lens
left out as the bake splits it off, and passes the model check's thinnest wall; and no ship builder takes a name
another room's builder has.

Needs Blender (tools/blender/session.py batch) and trimesh, which the prop environment has: run with the system python
it hands itself to the prop environment, and says it skipped on a box without either.
Run: python3 tools/props/library/ship_pieces_test.py
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
    import trimesh
except ImportError:
    if PROPS_PYTHON.exists() and os.environ.get("SHIP_PIECES_TEST_HANDED") != "1":
        os.environ["SHIP_PIECES_TEST_HANDED"] = "1"
        os.execv(str(PROPS_PYTHON), [str(PROPS_PYTHON), __file__])
    print("skipped: no prop environment on this box")
    sys.exit(0)

sys.path.insert(0, str(HERE.parent / "gates"))
import model as model_check  # noqa: E402

# The bridge's laid sizes (wide, tall, deep), as tools/props/scene/ship_kit.py lays them.
SIZES = {"window_frame": [1.2728, 1.0, 0.12], "window_pane": [1.0728, 0.9, 0.04], "dash_light_bar": [2.4, 0.04, 0.05],
         "ceiling_light_panel": [0.9, 0.06, 0.45], "edge_light_strip": [2.0, 0.05, 0.06],
         "frame_rib": [0.15, 1.4, 0.2], "floor_grate": [1.2, 0.6, 0.04], "command_platform": [1.6, 0.3, 1.2],
         "platform_step": [0.8, 0.15, 0.3], "thrust_indicator": [0.4, 0.4, 0.4],
         "outer_hatch": [1.3, 1.9, 0.35]}


def test_no_ship_builder_takes_another_room_s_name():
    """pieces.py asserts it as it loads; read here from the sources, so the check runs without Blender."""
    source = (HERE / "inside/pieces.py").read_text()
    names = set(re.findall(r'"([a-z_]+)"', source.split("BUILDERS = {", 1)[1].split(")}", 1)[0]))
    for module in ("pieces_earth.py", "earth_flat.py", "earth_stairwell.py"):
        text = (HERE / "inside" / module).read_text()
        if "BUILDERS = {" in text:
            names |= set(re.findall(r'"([a-z_]+)"', text.split("BUILDERS = {", 1)[1].split(")}", 1)[0]))
    assert not names & set(SIZES), names & set(SIZES)


def test_every_ship_builder_builds_with_walls_the_model_check_passes():
    if not (REPO / "tools/blender/session.py").exists():
        print("skipped: no Blender launcher")
        return
    with tempfile.TemporaryDirectory() as folder:  # never the real home's work/ (2026-10-18 review)
        plan = pathlib.Path(folder) / "plan.json"
        plan.write_text(json.dumps({"models": {f"{own}_1": {"route": "code", "kind": f"bridge_{own}", "size": size,
                                                            "laid": {"taper": 1.0}}
                                               for own, size in SIZES.items()}}))
        out = pathlib.Path(folder) / "built"
        done = subprocess.run([sys.executable, str(REPO / "tools/blender/session.py"), "batch",
                               str(HERE / "inside/build_only.py"), "--", str(REPO), str(plan), str(out)],
                              capture_output=True, text=True)
        assert done.returncode == 0, done.stdout[-2000:] + done.stderr[-2000:]
        built = {path.stem: trimesh.load(path, force="mesh") for path in out.glob("*.glb")}
        assert sorted(built) == sorted(f"{own}_1" for own in SIZES), sorted(built)
        for name, mesh in built.items():
            thinnest = model_check.thinnest(mesh, mesh.extents)
            assert thinnest >= model_check.THINNEST_LIMIT, (name, thinnest)


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[3] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
