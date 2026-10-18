"""The web3d command: `python -m score.dashboard web3d <place>` reaches the converter with the dashboard's own folders;
the converter finds the standing accept of the place's assembly, links (never copies) its files, names each prim's
defining layer, reads the scene record's cameras and makes the preview's smaller pictures. gltfpack and the films'
exporter are not run here."""
import json

import pytest

from score.dashboard import __main__ as commands
from score.dashboard.web3d import convert

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


def test_each_prim_is_named_by_the_layer_that_defines_it(tmp_path):
    from pxr import Usd
    layers = tmp_path / "layers"
    layers.mkdir()
    (layers / "base.usda").write_text('#usda 1.0\ndef Xform "alpha"\n{\n def Xform "Wall"\n {\n }\n}\n')
    (layers / "light.usda").write_text('#usda 1.0\nover "alpha"\n{\n def SphereLight "Lamp"\n {\n }\n'
                                       ' over "Wall"\n {\n }\n}\n')
    (tmp_path / "alpha.usda").write_text('#usda 1.0\n(\n defaultPrim = "alpha"\n subLayers = [@./layers/light.usda@, '
                                         '@./layers/base.usda@]\n)\n')
    stage = Usd.Stage.Open(str(tmp_path / "alpha.usda"))
    assert convert.layer_of(stage.GetPrimAtPath("/alpha/Wall")) == "base"
    assert convert.layer_of(stage.GetPrimAtPath("/alpha/Lamp")) == "light"


def test_the_cameras_come_from_the_scene_record(monkeypatch, tmp_path):
    (tmp_path / "data/scene").mkdir(parents=True)
    (tmp_path / "data/scene/alpha.json").write_text(json.dumps({"views": [
        {"name": "K01", "eye": [0, 1, 2], "aim": [0, 0, 0]}]}))
    monkeypatch.setattr(convert, "REPO", tmp_path)
    assert convert.cameras("alpha") == [{"name": "K01", "eye": [0, 1, 2], "aim": [0, 0, 0], "fov": 75.0}]
    assert convert.cameras("beta") == []


def test_the_preview_pictures_are_made_smaller(tmp_path):
    from PIL import Image
    source = tmp_path / "gltf"
    source.mkdir()
    (source / "alpha.gltf").write_text("{}")
    Image.new("RGB", (600, 300)).save(source / "wall.jpg")
    copied = convert.smaller_copy(source / "alpha.gltf", tmp_path / "light", 128)
    assert copied == tmp_path / "light/alpha.gltf"
    with Image.open(tmp_path / "light/wall.jpg") as smaller:
        assert max(smaller.size) == 128
    with Image.open(source / "wall.jpg") as kept:
        assert kept.size == (600, 300)
