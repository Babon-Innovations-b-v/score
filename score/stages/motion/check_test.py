"""The motion check (check.py, #23) on a small place made here, no seeds: a cart driven round a closed path, a door
swung on its hinge and a hatch slid down pass `follows`, `steps`, `moving area` and `clear`; then one known fault each:
the cart judged against a path its layer does not drive (follows), the door against an angle it does not swing
(follows), one frame of the cart's drive thrown 2 m aside (steps), a crate the layer moves that no record names and
the door's turn taken out of the layer (moving area), and the cart's path laid through the wall (clear).

Run: .venv/bin/python score/stages/motion/check_test.py
"""
import copy
import json
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))

from pxr import Gf, Sdf, Usd, UsdGeom  # noqa: E402

from score import checks  # noqa: E402
from score.stages import motion  # noqa: E402

REPO = pathlib.Path(__file__).resolve().parents[3]
PLACE = "toy"
RECORD = {"place": PLACE, "seconds": 12.0, "moves": [
    {"name": "cart_round", "prim": f"/{PLACE}/Objects/cart_1", "kind": "rover", "on": "rail", "start": 0.0,
     "length": 12.0, "loop": True,
     "path": {"points": [[0, 0], [3, 0], [3, 3], [0, 3]], "relative": True}},
    {"name": "door_swing", "prim": f"/{PLACE}/Objects/door_1", "kind": "hatch", "on": "rail", "start": 0.0,
     "length": 12.0, "loop": True,
     "swing": {"about": "Objects/hinge_1", "angle": 90.0, "speed": 45.0, "starts": "shut",
               "moves": [[1.0, "open"], [6.0, "shut"]]}},
    {"name": "hatch_slide", "prim": f"/{PLACE}/Objects/hatch_1", "kind": "hatch", "on": "rail", "start": 0.0,
     "length": 12.0, "loop": True,
     "slide": {"by": [0.0, -1.0, 0.0], "speed": 0.5, "starts": "shut", "moves": [[1.0, "open"], [6.0, "shut"]]}}]}


def box(stage, path, low, high):
    """A drawn box mesh of triangles from `low` to `high`."""
    (x0, y0, z0), (x1, y1, z1) = low, high
    points = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1),
              (x0, y1, z1)]
    quads = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (3, 7, 6, 2), (0, 4, 7, 3), (1, 2, 6, 5)]
    mesh = UsdGeom.Mesh.Define(stage, path)
    mesh.GetPointsAttr().Set([Gf.Vec3f(*point) for point in points])
    mesh.GetFaceVertexCountsAttr().Set([3] * 12)
    mesh.GetFaceVertexIndicesAttr().Set([index for a, b, c, d in quads for index in (a, b, c, a, c, d)])


def thing(stage, name, at, size):
    """An object Xform at `at` with a box mesh of `size` standing on its origin."""
    xform = UsdGeom.Xform.Define(stage, f"/{PLACE}/Objects/{name}")
    xform.AddTranslateOp().Set(Gf.Vec3d(*at))
    half = (size[0] / 2, 0.0, size[2] / 2)
    box(stage, f"/{PLACE}/Objects/{name}/body", (-half[0], 0.0, -half[2]), (half[0], size[1], half[2]))


def toy_place(folder):
    """The place's stage folder: a root over one base layer with a floor, a wall, a cart, a door on its hinge post,
    a hatch and a crate."""
    seed = pathlib.Path(folder) / "seeds" / PLACE
    (seed / "layers").mkdir(parents=True)
    stage = Usd.Stage.CreateNew(str(seed / "layers/base.usda"))
    root = UsdGeom.Xform.Define(stage, f"/{PLACE}")
    stage.SetDefaultPrim(root.GetPrim())
    box(stage, f"/{PLACE}/Structure/wall", (8.0, 0.0, -2.0), (8.3, 3.0, 6.0))
    thing(stage, "cart_1", (0.0, 0.05, 0.0), (1.0, 0.8, 1.0))
    thing(stage, "door_1", (-4.0, 0.0, -4.0), (1.0, 2.0, 0.1))
    thing(stage, "hinge_1", (-4.55, 0.0, -4.0), (0.1, 2.0, 0.1))
    thing(stage, "hatch_1", (5.0, 0.0, -4.0), (1.0, 0.1, 1.0))
    thing(stage, "crate_1", (-4.0, 0.0, 3.0), (0.6, 0.6, 0.6))
    stage.GetRootLayer().Save()
    top = Sdf.Layer.CreateNew(str(seed / f"{PLACE}.usda"))
    top.subLayerPaths.append("./layers/base.usda")
    top.defaultPrim = PLACE
    top.timeCodesPerSecond = 24.0
    top.Save()
    return seed


def inputs_for(folder, seed, record):
    path = pathlib.Path(folder) / f"rigid-{len(list(pathlib.Path(folder).glob('rigid-*')))}.json"
    path.write_text(json.dumps(record))
    return {"moves": path, "kinds": REPO / "data/checks/motion.json", "seed": seed}


def judged(output, inputs, names):
    return {check.name: check.judge(output, inputs, None) for check in motion.CHECKS if check.name in names}


def layer_attribute(output, prim, name):
    layer = Sdf.Layer.FindOrOpen(str(pathlib.Path(output) / "layers/motion.usda"))
    return layer, layer.GetAttributeAtPath(f"{prim}.{name}")


def test_the_check_passes_a_true_motion_and_fails_each_known_fault():
    with tempfile.TemporaryDirectory() as folder:
        seed = toy_place(folder)
        inputs = inputs_for(folder, seed, RECORD)
        out = pathlib.Path(folder) / "out"
        out.mkdir()
        motion.make(inputs, out, 0, {})
        found = judged(out, inputs, ("follows", "steps", "moving area", "clear"))
        assert all(verdict.answer == checks.PASS for verdict in found.values()), {
            name: (verdict.reason, verdict.findings) for name, verdict in found.items()}

        elsewhere = copy.deepcopy(RECORD)
        elsewhere["moves"][0]["path"]["points"][2] = [4.0, 4.0]
        verdict = judged(out, inputs_for(folder, seed, elsewhere), ("follows",))["follows"]
        assert verdict.answer == checks.FAIL and any("off its path's curve" in line for line in verdict.findings), \
            verdict

        wider = copy.deepcopy(RECORD)
        wider["moves"][1]["swing"]["angle"] = 60.0
        verdict = judged(out, inputs_for(folder, seed, wider), ("follows",))["follows"]
        assert verdict.answer == checks.FAIL and any("swings 90.0 degrees, its record 60.0" in line
                                                     for line in verdict.findings), verdict

        layer, moved = layer_attribute(out, f"/{PLACE}/Objects/cart_1", "xformOp:translate:path")
        code = sorted(layer.ListTimeSamplesForPath(moved.path))[40]
        spot = layer.QueryTimeSample(moved.path, code)
        layer.SetTimeSample(moved.path, code, Gf.Vec3d(spot[0] + 2.0, spot[1], spot[2]))
        layer.Save()
        verdict = judged(out, inputs, ("steps",))["steps"]
        assert verdict.answer == checks.FAIL and any(line.startswith("cart_round: jumps") for line in verdict.findings), \
            verdict
        layer.SetTimeSample(moved.path, code, spot)

        crate = Sdf.CreatePrimInLayer(layer, f"/{PLACE}/Objects/crate_1")
        crate.specifier = Sdf.SpecifierOver
        shift = Sdf.AttributeSpec(crate, "xformOp:translate", Sdf.ValueTypeNames.Double3)
        layer.SetTimeSample(shift.path, 0.0, Gf.Vec3d(-4.0, 0.0, 3.0))
        layer.SetTimeSample(shift.path, 48.0, Gf.Vec3d(-3.0, 0.0, 3.0))
        _, swung = layer_attribute(out, f"/{PLACE}/Objects/door_1", "xformOp:rotateY:swing")
        for sample in layer.ListTimeSamplesForPath(swung.path):
            layer.EraseTimeSample(swung.path, sample)
        layer.Save()
        verdict = judged(out, inputs, ("moving area",))["moving area"]
        assert verdict.answer == checks.FAIL and f"/{PLACE}/Objects/crate_1: moves, yet no record moves it" in \
            verdict.findings and f"/{PLACE}/Objects/door_1: its record moves it, yet it stands still in the stage" in \
            verdict.findings, verdict

    with tempfile.TemporaryDirectory() as folder:
        seed = toy_place(folder)
        through = copy.deepcopy(RECORD)
        through["moves"][0]["path"]["points"] = [[0, 0], [9, 0], [9, 3], [0, 3]]
        inputs = inputs_for(folder, seed, through)
        out = pathlib.Path(folder) / "out"
        out.mkdir()
        motion.make(inputs, out, 0, {})
        verdict = judged(out, inputs, ("clear",))["clear"]
        assert verdict.answer == checks.FAIL and any("Structure/wall" in line for line in verdict.findings), verdict


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[3] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
