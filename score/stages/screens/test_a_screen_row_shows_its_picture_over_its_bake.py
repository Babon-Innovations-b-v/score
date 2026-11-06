"""A screen row shows its picture over its bake: of a model's surfaces its display part is a lit one naming a screen
(else its largest lit one; none lit, none and a gap that fails `pictured` by name), laid flat on its front with the
picture upright and unmirrored seen from in front, its subset bound to the picture's material in its own layer, and
the assembly's asset made a stack of that layer over the bake, the other parts as baked; the motion row's `covered`
reads the screens stage as what makes a row that shows.

Every answer is worked out by hand from the fixture: a 2 m by 1 m front quad facing +z at z 0.1 over a box body,
its corners at x -1 and 1, y 0 and 1.

Breaks that turn it red (each applied once, seen red, reverted, 2026-11-06):
- screens.display: `if said or not glowing: return said` -> `return glowing` (the LED pictured beside the screen)
- screens.laid_flat: `found[used, 0] = 1.0 - u if mirrored else u` -> `found[used, 0] = u if mirrored else 1.0 - u`
- screens.take: `stack.subLayerPaths = [f"./{LAYERS}/{model}.usda", f"./{model}_baked.usdc"]` -> the two swapped
  (the bake's binding wins over the picture's)
- screens.judge_pictured: `checks.FAIL if failing else checks.PASS` -> `checks.PASS`
- score/stages/motion/__init__.py coverage: `**read_json(inputs["screens"])["read_by"]` dropped
"""
import json
import pathlib

import numpy as np
from pxr import Usd, UsdGeom, UsdShade, Vt

from score import checks
from score.stages import motion, row_kinds, screens

REPO = pathlib.Path(__file__).resolve().parents[3]
# The front quad (faces 0 and 1, the screen's) and a body face behind it (face 2) and the LED (face 3).
POSITIONS = np.array([[-1, 0, 0.1], [1, 0, 0.1], [1, 1, 0.1], [-1, 1, 0.1],
                      [-1, 0, -0.5], [1, 0, -0.5], [1, 1, -0.5], [0.9, 0.0, 0.11], [1.0, 0.0, 0.11], [1.0, 0.1, 0.11]],
                     float)
TRIANGLES = np.array([[0, 1, 2], [0, 2, 3], [4, 6, 5], [7, 8, 9]])
SURFACES = np.array(["screen_glow__a", "screen_glow__a", "case_paint", "led_glow"])
SPECS = {"screen_glow__a": {"recipe": "glowing", "library": "screen_glow", "colour": [0.1, 0.5, 0.8], "seed": 123456,
                            "token": "screen-blue"},
         "case_paint": {"recipe": "painted_metal", "library": "case_paint", "colour": [0.5, 0.5, 0.5]},
         "led_glow": {"recipe": "glowing", "library": "led_glow", "colour": [1.0, 0.1, 0.1]}}
COLOURS = {"space-black": [0.01, 0.01, 0.02], "screen-blue": [0.1, 0.5, 0.8]}
RECIPES = {"screen": {"roughness": 0.1}}


def baked_asset(folder, model):
    """assets/<model>.usdc as export.write_asset lays it: /<model>/geo, a subset a surface bound to its own material."""
    stage = Usd.Stage.CreateNew(str(folder / "assets" / f"{model}.usdc"))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    stage.SetDefaultPrim(UsdGeom.Xform.Define(stage, f"/{model}").GetPrim())
    mesh = UsdGeom.Mesh.Define(stage, f"/{model}/geo")
    mesh.CreatePointsAttr(Vt.Vec3fArray.FromNumpy(POSITIONS.astype(np.float32)))
    mesh.CreateFaceVertexCountsAttr([3] * len(TRIANGLES))
    mesh.CreateFaceVertexIndicesAttr(Vt.IntArray.FromNumpy(TRIANGLES.reshape(-1).astype(np.int32)))
    for name in sorted(set(SURFACES)):
        faces = Vt.IntArray.FromNumpy(np.flatnonzero(SURFACES == name).astype(np.int32))
        subset = UsdGeom.Subset.CreateGeomSubset(mesh, name, UsdGeom.Tokens.face, faces, UsdShade.Tokens.materialBind)
        material = UsdShade.Material.Define(stage, f"/{model}/Looks/{name}")
        UsdShade.MaterialBindingAPI.Apply(subset.GetPrim()).Bind(material)
    stage.GetRootLayer().Save()


def test_a_screen_row_shows_its_picture_over_its_bake(tmp_path):
    words = screens.rules()["words"]
    areas = np.array([1.0, 1.0, 1.0, 0.005])
    assert screens.display(SURFACES, areas, SPECS, words) == ["screen_glow__a"]  # named: never the LED beside it
    unnamed = {**SPECS, "screen_glow__a": dict(SPECS["screen_glow__a"], library="panel_glow")}
    assert screens.display(SURFACES, areas, unnamed, words) == ["screen_glow__a"]  # none named: the largest lit
    assert screens.display(SURFACES, areas, {name: dict(spec, recipe="painted_metal") for name, spec in SPECS.items()},
                           words) == []
    out = tmp_path / "screens"
    found = (POSITIONS, TRIANGLES, SURFACES, np.zeros(len(TRIANGLES), dtype=int))
    record = screens.pictured("monitor_1", found, SPECS, COLOURS, "space-black", RECIPES, None, words, out)
    assert record["surfaces"] == ["screen_glow__a"] and record["seed"] == 123456 % screens.SEED_FOLD, record
    assert (out / "screens" / "textures" / "monitor_1_base.png").is_file()
    unlit = (POSITIONS, TRIANGLES, np.array(["case_paint"] * 4), found[3])
    assert screens.pictured("dark_1", unlit, SPECS, COLOURS, "space-black", RECIPES, None, words, out) is None
    # the assembly's side: the baked asset kept under its stack, the screen bound to its picture, the case as baked
    assembly = tmp_path / "assembly"
    (assembly / "assets").mkdir(parents=True)
    baked_asset(assembly, "monitor_1")
    (out / screens.RECORD).write_text(json.dumps({"models": {"monitor_1": record}}))
    assert screens.take(out, assembly) == ["monitor_1"]
    stage = Usd.Stage.Open(str(assembly / "assets" / "monitor_1.usdc"))
    bound = {child.GetName(): UsdShade.MaterialBindingAPI(child).ComputeBoundMaterial()[0].GetPath().pathString
             for child in stage.GetPrimAtPath("/monitor_1/geo").GetChildren()}
    assert bound == {"screen_glow__a": "/monitor_1/Looks/screen_glow__a__screen",
                     "case_paint": "/monitor_1/Looks/case_paint", "led_glow": "/monitor_1/Looks/led_glow"}, bound
    laid = np.asarray(UsdGeom.PrimvarsAPI(stage.GetPrimAtPath("/monitor_1/geo")).GetPrimvar("screen_st").Get())
    # x -1..1 across, y 0..1 up, seen from +z (the quad's front): unmirrored, upright, the body's points untouched
    assert np.allclose(laid[:4], [[0, 0], [1, 0], [1, 1], [0, 1]]) and np.allclose(laid[4:7], 0), laid
    assert stage.GetDefaultPrim().GetName() == "monitor_1" and UsdGeom.GetStageUpAxis(stage) == "Y"
    # the gate: a screen take with no display part fails by name
    gap = {"gaps": [{"name": "dark_1: no screen to draw on", "faults": ["dark_1: its take shows, and its bake has "
                                                                         "no lit part"]}]}
    (out / "batch-gaps.json").write_text(json.dumps(gap))
    failed = screens.judge_pictured(out, {}, {})
    assert failed.answer == checks.FAIL and failed.findings == tuple(gap["gaps"][0]["faults"])
    (out / "batch-gaps.json").write_text(json.dumps({"gaps": []}))
    assert screens.judge_pictured(out, {}, {}).answer == checks.PASS and screens.screens_faults(out) == []
    # the motion row's covered: a screen is made by this stage, so no row that shows is uncovered
    inputs = {"row kinds": REPO / "data/checks/row-kinds.json", "screens": REPO / "data/checks/screens.json"}
    design = {"rows": [{"id": "monitor_screen", "name": "monitor screen", "noun": "monitor"}]}
    assert row_kinds.uncovered(design, row_kinds.table(), motion.coverage(inputs)) == []
    assert row_kinds.uncovered(design, row_kinds.table()) != []  # row-kinds.json alone still leaves it unmade
