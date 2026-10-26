"""A scene's effects are made from its design, ride their objects at their measured spots, and pass every gate;
a row that emits with no object on the stage fails `designed` (effects/__init__.py, from_design.py). The stage is a
small kitchen made here; no record is written for the scene.

Breaks that turn it red (each applied once and seen red, then reverted):
- `from_design.spot_on`: `middle + at * half` read as `middle`  -> the first test (the kettle's spout at its box's
  middle, not its front).
- `from_design.record`: the `missing.append(...)` line left out  -> the second test (`designed` passes).
- `from_design.checks_of`: `emitters=[name]` read as `emitters=[]`  -> the first test (`footage` is no longer measured
  on each emitter, so it does not pass).
"""
import json
import pathlib

from score import checks
from score.stages import effects

REPO = pathlib.Path(__file__).resolve().parents[3]
PLACE = "toy"
# The toy kitchen's objects: (name, low corner, high corner of the model's own box, where it stands).
OBJECTS = (("stove_1", (-0.4, 0.0, -0.3), (0.4, 0.9, 0.3), (2.0, 0.0, 1.0)),
           ("kettle_1", (-0.1, 0.0, -0.08), (0.1, 0.25, 0.08), (-1.0, 0.9, 0.0)),
           ("chair_1", (-0.25, 0.0, -0.25), (0.25, 0.9, 0.25), (0.0, 0.0, 2.0)))
INVENTORY = {"rows": [{"id": "stove", "name": "stove", "noun": "stove"},
                      {"id": "kettle", "name": "kettle", "noun": "kettle"},
                      {"id": "chair", "name": "chair", "noun": "chair"},
                      {"id": "wall", "name": "back wall", "noun": "wall"}]}


def box_mesh(stage, path, low, high):
    """A closed box mesh between two corners."""
    from pxr import UsdGeom
    corners = [(x, y, z) for x in (low[0], high[0]) for y in (low[1], high[1]) for z in (low[2], high[2])]
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    mesh = UsdGeom.Mesh.Define(stage, path)
    mesh.CreatePointsAttr(corners)
    mesh.CreateFaceVertexCountsAttr([4] * len(faces))
    mesh.CreateFaceVertexIndicesAttr([index for face in faces for index in face])


def toy_seed(folder, objects=OBJECTS):
    """A stage folder <folder>/toy/toy.usda: the place's objects, each a box under Objects."""
    from pxr import Gf, Usd, UsdGeom
    seed = pathlib.Path(folder) / PLACE
    seed.mkdir(parents=True)
    stage = Usd.Stage.CreateNew(str(seed / f"{PLACE}.usda"))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    stage.SetDefaultPrim(UsdGeom.Xform.Define(stage, f"/{PLACE}").GetPrim())
    UsdGeom.Scope.Define(stage, f"/{PLACE}/Objects")
    for name, low, high, at in objects:
        holder = UsdGeom.Xform.Define(stage, f"/{PLACE}/Objects/{name}")
        holder.AddTranslateOp().Set(Gf.Vec3d(*at))
        box_mesh(stage, f"/{PLACE}/Objects/{name}/body", low, high)
    stage.GetRootLayer().Save()
    return seed


def toy_inputs(folder, inventory=INVENTORY, objects=OBJECTS):
    folder = pathlib.Path(folder)
    (folder / "inventory.json").write_text(json.dumps(inventory))
    return {"design": folder / "inventory.json", "row kinds": REPO / "data/checks/row-kinds.json",
            "effect kinds": REPO / "data/checks/effects.json", "seed": toy_seed(folder / "seeds", objects)}


def answers(inputs, folder):
    out = pathlib.Path(folder) / "out"
    out.mkdir()
    effects.make(inputs, out, 0, {})
    assert effects.layer_faults(out) == []
    return out, {check.name: check.judge(out, inputs, None) for check in effects.CHECKS}


def test_the_stove_and_the_kettle_carry_their_steam_at_their_spots_and_pass(tmp_path):
    from pxr import Usd, UsdGeom
    out, found = answers(toy_inputs(tmp_path), tmp_path)
    record = json.loads((out / "record.json").read_text())
    stage = Usd.Stage.Open(str(tmp_path / "seeds" / PLACE / f"{PLACE}.usda"))
    stage.GetRootLayer().subLayerPaths.append(str(out / "layers/effects.usda"))
    where = {name: UsdGeom.Xformable(stage.GetPrimAtPath(f"/{PLACE}/Objects/{name.split('_')[0]}_1/{name}"))
             .ComputeLocalToWorldTransform(Usd.TimeCode.Default()).ExtractTranslation()
             for name in ("stove_1_steam_rise", "kettle_1_steam_jet")}
    assert all(verdict.answer == checks.PASS for verdict in found.values()), {
        name: (verdict.reason, verdict.findings) for name, verdict in found.items()}
    assert {entry["name"]: entry["row"] for entry in record["effects"]} == {"stove_1_steam_rise": "stove",
                                                                            "kettle_1_steam_jet": "kettle"}
    # the stove's steam on the middle of its top: (2.0, 0.0 + 0.9, 1.0); the kettle's spout at the front of its box,
    # six tenths of the way up from its middle: (-1.0, 0.9 + 0.125 + 0.6 * 0.125, 0.0 + 0.08)
    assert max(abs(a - b) for a, b in zip(where["stove_1_steam_rise"], (2.0, 0.9, 1.0))) < 1e-6, where
    assert max(abs(a - b) for a, b in zip(where["kettle_1_steam_jet"], (-1.0, 1.1, 0.08))) < 1e-6, where
    # every footage check is measured on its own emitter
    assert {check["anchor"] for check in record["footage"]["checks"]} == set(where), record["footage"]["checks"]


def test_a_row_that_emits_with_no_object_on_the_stage_fails_designed(tmp_path):
    rows = INVENTORY["rows"] + [{"id": "humidifier", "name": "humidifier", "noun": "humidifier"}]
    _, found = answers(toy_inputs(tmp_path, inventory={"rows": rows}), tmp_path)
    assert found["designed"].answer == checks.FAIL, found["designed"].reason
    assert found["designed"].findings == ("humidifier emits humidifier_mist, and no object of it stands on the stage",)

