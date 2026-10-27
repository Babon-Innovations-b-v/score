"""tools/usd/whole_layer.py: a stamped place layer alone carries metres, Y up and its default prim, its root a def
Xform, and the stage it is a sublayer of composes as before.

Breaks that turn each test red (each applied once and seen red, 2026-10-27):
- test_a_stamped_layer_is_a_whole_asset_alone: whole_layer.py's `layer.defaultPrim = place` made `pass`.
- test_the_stage_it_sits_in_composes_as_before: whole_layer.py's `spec.typeName = spec.typeName or ROOT_TYPE` made
  `spec.typeName = "Scope"`.

Run: .venv/bin/python -m pytest -q tools/usd/test_a_place_layer_is_a_whole_asset_alone.py
"""
import pathlib
import sys

from pxr import Sdf, Usd, UsdGeom

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import whole_layer  # noqa: E402


def override_layer(path):
    """A layer as the motion and effects writers make it: an `over` of the place holding a scope of its own."""
    layer = Sdf.Layer.CreateNew(str(path))
    stage = Usd.Stage.Open(layer)
    UsdGeom.Scope.Define(stage, "/place/Effects")
    layer.GetPrimAtPath("/place").specifier = Sdf.SpecifierOver
    return layer


def test_a_stamped_layer_is_a_whole_asset_alone(tmp_path):
    layer = whole_layer.stamped(override_layer(tmp_path / "effects.usda"), "place")
    layer.Save()
    alone = Usd.Stage.Open(str(tmp_path / "effects.usda"))
    assert UsdGeom.GetStageUpAxis(alone) == UsdGeom.Tokens.y and UsdGeom.GetStageMetersPerUnit(alone) == 1.0
    assert alone.GetDefaultPrim().GetPath() == Sdf.Path("/place") and alone.GetDefaultPrim().IsDefined()
    assert alone.GetDefaultPrim().GetTypeName() == "Xform"


def test_the_stage_it_sits_in_composes_as_before(tmp_path):
    base = Sdf.Layer.CreateNew(str(tmp_path / "base.usda"))
    stage = Usd.Stage.Open(base)
    UsdGeom.Xform.Define(stage, "/place")  # every base's root, tools/usd/export.py
    UsdGeom.Xform.Define(stage, "/place/Objects")
    base.Save()
    override_layer(tmp_path / "effects.usda").Save()
    root = Sdf.Layer.CreateNew(str(tmp_path / "place.usda"))
    root.subLayerPaths[:] = ["./effects.usda", "./base.usda"]
    root.defaultPrim = "place"
    root.Save()
    before = Usd.Stage.Open(str(tmp_path / "place.usda"))
    shape = [(str(prim.GetPath()), prim.GetTypeName(), prim.IsDefined()) for prim in before.Traverse()]
    whole_layer.stamped(Sdf.Layer.FindOrOpen(str(tmp_path / "effects.usda")), "place").Save()
    after = Usd.Stage.Open(str(tmp_path / "place.usda"))
    after.Reload()
    assert [(str(prim.GetPath()), prim.GetTypeName(), prim.IsDefined()) for prim in after.Traverse()] == shape
