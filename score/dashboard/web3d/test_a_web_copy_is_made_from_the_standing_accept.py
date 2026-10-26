"""Invariant: a place's 3D web copy is made from the standing accept of its assembly (a rejected one never), its files
linked from the store and never copied; each prim is listed under the layer that defines it; the cameras are the
scene record's; the preview's pictures are made smaller without touching the full copy's; a haze body is read with
its box, a shown place's haze is not. gltfpack and the films' exporter are not run here.

Breaks that turn this red (each applied once and seen red, then reverted):
- __main__.web3d: `out or str(settings.SCORE_WEB_COPIES)` -> `out or str(settings.SCORE_PROPS_HOME / "web")`
  -> test_the_command_runs_the_converter_into_the_served_folder
- convert.standing_accept: drop the reject filter (`if item["at"] > rejected...` -> `if True`) -> test_a_rejected_...
- convert.linked_output: `target.symlink_to(...)` -> `shutil.copy(...)` -> test_the_standing_accept_is_linked_...
- facts.layer_of: `defining[-1]` -> `defining[0]` (the strongest sublayer) -> test_each_prim_is_named_by_the_layer_...
- convert.cameras: default fov 75.0 -> 60.0 -> test_the_cameras_come_from_the_scene_record
- convert.webp_copy: `opened.thumbnail((side, side)...)` dropped -> test_the_preview_pictures_are_made_smaller
- facts.hazes: drop `shown_place(prim) or` -> test_a_haze_body_is_read_with_its_box_...
"""
import json

import pytest

from score.dashboard import __main__ as commands
from score.dashboard.web3d import convert, facts

pytestmark = pytest.mark.django_db


def test_the_command_runs_the_converter_into_the_served_folder(monkeypatch, settings, tmp_path):
    called = {}
    monkeypatch.setattr(convert, "convert", lambda place, store, out: called.update(place=place, store=store,
                                                                                    out=out) or {
        "triangles": 1, "bytes": 1, "light_bytes": 1, "seconds": 0.1, "left_out": {}})
    settings.SCORE_WEB_COPIES = tmp_path / "web"
    commands.main(["web3d", "alpha"])
    assert called == {"place": "alpha", "store": settings.SCORE_PROPS_HOME / "store", "out": tmp_path / "web"}


def test_the_standing_accept_is_linked_not_copied(world, tmp_path):
    accept = convert.accepted_assembly(world.root / "store", "alpha")
    assert accept["output"] == world.outputs["assembly@alpha"]
    assert convert.accepted_assembly(world.root / "store", "nowhere") is None
    folder = convert.linked_output(world.root / "store", accept["output"], tmp_path / "stage")
    linked = folder / "alpha.usda"
    assert linked.is_symlink() and "defaultPrim" in linked.read_text()


def test_a_rejected_accept_no_longer_stands(tmp_path):
    """Two accepts of assembly@alpha, the newer one rejected after it: the older one stands again."""
    accepts = tmp_path / "objects/accepts/assembly@alpha"
    rejects = tmp_path / "objects/rejects/assembly@alpha"
    accepts.mkdir(parents=True)
    rejects.mkdir(parents=True)
    (accepts / "a.json").write_text(json.dumps({"output": "old", "at": "2026-10-01T10:00:00"}))
    (accepts / "b.json").write_text(json.dumps({"output": "new", "at": "2026-10-02T10:00:00"}))
    assert convert.accepted_assembly(tmp_path, "alpha")["output"] == "new"
    (rejects / "r.json").write_text(json.dumps({"output": "new", "at": "2026-10-03T10:00:00"}))
    assert convert.accepted_assembly(tmp_path, "alpha")["output"] == "old"


def test_each_prim_is_named_by_the_layer_that_defines_it(tmp_path):
    """Light only `over`s the Wall the base defines, and defines the Lamp itself; a Shelf both define is the
    weakest's (the base's): a stronger layer's own def of it does not move it."""
    from pxr import Usd
    layers = tmp_path / "layers"
    layers.mkdir()
    (layers / "base.usda").write_text('#usda 1.0\ndef Xform "alpha"\n{\n def Xform "Wall"\n {\n }\n'
                                      ' def Xform "Shelf"\n {\n }\n}\n')
    (layers / "light.usda").write_text('#usda 1.0\nover "alpha"\n{\n def SphereLight "Lamp"\n {\n }\n'
                                       ' over "Wall"\n {\n }\n def Xform "Shelf"\n {\n }\n}\n')
    (tmp_path / "alpha.usda").write_text('#usda 1.0\n(\n defaultPrim = "alpha"\n subLayers = [@./layers/light.usda@, '
                                         '@./layers/base.usda@]\n)\n')
    stage = Usd.Stage.Open(str(tmp_path / "alpha.usda"))
    assert facts.layer_of(stage.GetPrimAtPath("/alpha/Wall")) == "base"
    assert facts.layer_of(stage.GetPrimAtPath("/alpha/Lamp")) == "light"
    assert facts.layer_of(stage.GetPrimAtPath("/alpha/Shelf")) == "base"


def test_the_cameras_come_from_the_scene_record(monkeypatch, tmp_path):
    (tmp_path / "data/scene").mkdir(parents=True)
    (tmp_path / "data/scene/alpha.json").write_text(json.dumps({"views": [
        {"name": "K01", "eye": [0, 1, 2], "aim": [0, 0, 0]}, {"name": "K02", "eye": [3, 1, 2], "aim": [0, 0, 0],
                                                              "fov": 40}]}))
    monkeypatch.setattr(convert, "REPO", tmp_path)
    assert convert.cameras("alpha") == [{"name": "K01", "eye": [0, 1, 2], "aim": [0, 0, 0], "fov": 75.0},
                                        {"name": "K02", "eye": [3, 1, 2], "aim": [0, 0, 0], "fov": 40.0}]
    assert convert.cameras("beta") == []


def test_the_preview_pictures_are_made_smaller(tmp_path):
    from PIL import Image
    source = tmp_path / "gltf"
    source.mkdir()
    (source / "alpha.gltf").write_text('{"images": [{"uri": "wall.jpg"}]}')
    Image.new("RGB", (600, 300)).save(source / "wall.jpg")
    copied = convert.webp_copy(source / "alpha.gltf", tmp_path / "light", 128)
    assert copied == tmp_path / "light/alpha.gltf"
    assert json.loads(copied.read_text())["images"] == [{"uri": "wall.webp"}]
    with Image.open(tmp_path / "light/wall.webp") as smaller:
        assert smaller.size == (128, 64)  # 600 x 300 to 128 a side, its shape kept
    with Image.open(source / "wall.jpg") as kept:
        assert kept.size == (600, 300)


def test_a_haze_body_is_read_with_its_box_and_a_shown_place_haze_is_not(tmp_path):
    from pxr import Gf, Sdf, Usd, UsdGeom
    stage = Usd.Stage.CreateNew(str(tmp_path / "alpha.usda"))
    stage.SetDefaultPrim(UsdGeom.Xform.Define(stage, "/alpha").GetPrim())
    for path in ("/alpha/Sky/Haze", "/alpha/Places/beta/Sky/Haze"):
        haze = UsdGeom.Mesh.Define(stage, path)
        haze.CreatePointsAttr([(0, 0, 0), (2, 0, 0), (2, 3, 4), (0, 3, 4)])
        haze.CreateFaceVertexCountsAttr([4])
        haze.CreateFaceVertexIndicesAttr([0, 1, 2, 3])
        prim = haze.GetPrim()
        prim.CreateAttribute("score:kind", Sdf.ValueTypeNames.String).Set("haze")
        prim.CreateAttribute("score:haze_colour", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(0.9, 0.8, 0.7))
        prim.CreateAttribute("score:haze_density", Sdf.ValueTypeNames.Float).Set(0.025)
        prim.CreateAttribute("score:haze_reach", Sdf.ValueTypeNames.Float).Set(24.0)
    [found] = facts.hazes(stage, Usd.TimeCode.Default())
    assert found["density"] == pytest.approx(0.025) and found["reach"] == 24.0
    assert found["low"] == [0.0, 0.0, 0.0] and found["high"] == [2.0, 3.0, 4.0]
    assert found["colour"] == pytest.approx([0.9, 0.8, 0.7])
