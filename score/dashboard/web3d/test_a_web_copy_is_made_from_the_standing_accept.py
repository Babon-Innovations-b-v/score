"""Invariant: a place's 3D web copy is made from the standing accept of its assembly (a rejected one never), its files
linked from the store and never copied; each prim is listed under the layer that defines it; the cameras are the
scene record's; the preview's pictures are made smaller without touching the full copy's; a haze body is read with
its box, a shown place's haze is not. gltfpack and the films' exporter are not run here: the command runs the real
convert up to write_copies, which is stood in for by one that reads the linked stage it is handed.

Breaks that turn this red (each applied once and seen red, then reverted):
- __main__.web3d: `out or str(settings.SCORE_WEB_COPIES)` -> `out or str(settings.SCORE_PROPS_HOME / "web")`
  -> the copy is written outside the served folder
- convert.standing_accept: drop the reject filter (`if item["at"] > rejected...` -> `if True`) -> the rejected row
- convert.linked_output: `target.symlink_to(...)` -> `shutil.copy(...)` -> the stage handed on is not a link
- facts.layer_of: `defining[-1]` -> `defining[0]` (the strongest sublayer) -> the Shelf is listed under light
- convert.cameras: default fov 75.0 -> 60.0 -> K01's camera
- convert.webp_copy: `opened.thumbnail((side, side)...)` dropped -> the preview's picture is 600 x 300
- facts.hazes: drop `shown_place(prim) or` -> beta's haze is read as the place's own
"""
import json

import pytest

from score.dashboard import __main__ as commands
from score.dashboard.web3d import convert, facts

pytestmark = pytest.mark.django_db

HAZE = ('  def Mesh "Haze" (\n   )\n  {{\n   point3f[] points = [(0, 0, 0), (2, 0, 0), (2, 3, 4), (0, 3, 4)]\n'
        '   int[] faceVertexCounts = [4]\n   int[] faceVertexIndices = [0, 1, 2, 3]\n'
        '   custom string score:kind = "haze"\n   custom color3f score:haze_colour = (0.9, 0.8, 0.7)\n'
        '   custom float score:haze_density = 0.025\n   custom float score:haze_reach = 24\n  }}\n')
# Light only `over`s the Wall the base defines and defines the Lamp itself; a Shelf both define is the weakest's
# (the base's): a stronger layer's own def of it does not move it. The base holds the place's haze and a shown
# place's (beta's) haze.
FILES = {
    "alpha.usda": '#usda 1.0\n(\n defaultPrim = "alpha"\n subLayers = [@./layers/light.usda@, @./layers/base.usda@]\n)\n',
    "layers/base.usda": ('#usda 1.0\ndef Xform "alpha"\n{\n def Xform "Wall"\n {\n }\n def Xform "Shelf"\n {\n }\n'
                         ' def Xform "Sky"\n {\n' + HAZE.format() + ' }\n def Xform "Places"\n {\n'
                         '  def Xform "beta"\n  {\n   def Xform "Sky"\n   {\n' + HAZE.format() + '   }\n  }\n }\n}\n'),
    "layers/light.usda": ('#usda 1.0\nover "alpha"\n{\n def SphereLight "Lamp"\n {\n }\n over "Wall"\n {\n }\n'
                          ' def Xform "Shelf"\n {\n }\n}\n'),
}
VIEWS = {"views": [{"name": "K01", "eye": [0, 1, 2], "aim": [0, 0, 0]},
                   {"name": "K02", "eye": [3, 1, 2], "aim": [0, 0, 0], "fov": 40}]}


def stored(store, output, files):
    """`files` {name: text} kept in the store as `output`'s blobs and listing."""
    blobs = store / "objects/blobs"
    blobs.mkdir(parents=True, exist_ok=True)
    (store / "objects/outputs").mkdir(parents=True, exist_ok=True)
    listing = {}
    for name, text in files.items():
        sha = f"{output}-{name.replace('/', '-')}"
        (blobs / sha).write_text(text)
        listing[name] = sha
    (store / "objects/outputs" / f"{output}.json").write_text(json.dumps(listing))


def decision(store, area, output, at):
    folder = store / "objects" / area / "assembly@alpha"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{output}-{at}.json").write_text(json.dumps({"output": output, "at": at}))


def handed_on(handed):
    """A write_copies that keeps what the converter hands it and what the linked stage reads as."""
    def write_copies(place, stage_folder, out_root, origin, views, elsewhere=()):
        from pxr import Usd
        stage = Usd.Stage.Open(str(stage_folder / f"{place}.usda"))
        handed.update(place=place, out=out_root, origin=origin, views=views, elsewhere=set(elsewhere),
                      linked=(stage_folder / f"{place}.usda").is_symlink(),
                      layers={name: facts.layer_of(stage.GetPrimAtPath(f"/alpha/{name}"))
                              for name in ("Wall", "Lamp", "Shelf")},
                      hazes=facts.hazes(stage, Usd.TimeCode.Default()))
        return {"triangles": 1, "bytes": 1, "light_bytes": 1, "seconds": 0.1, "left_out": {}}
    return write_copies


@pytest.mark.parametrize("rejected, standing", [(False, "new"), (True, "old")],
                         ids=["the newest accept stands", "a rejected newest accept no longer stands"])
def test_a_web_copy_is_made_from_the_standing_accept(rejected, standing, monkeypatch, settings, tmp_path):
    from PIL import Image
    store = tmp_path / "store"
    for output in ("old", "new"):
        stored(store, output, FILES)
    decision(store, "accepts", "old", "2026-10-01T10:00:00")
    decision(store, "accepts", "new", "2026-10-02T10:00:00")
    if rejected:
        decision(store, "rejects", "new", "2026-10-03T10:00:00")
    (tmp_path / "data/scene").mkdir(parents=True)
    (tmp_path / "data/scene/alpha.json").write_text(json.dumps(VIEWS))
    monkeypatch.setattr(convert, "REPO", tmp_path)
    settings.SCORE_PROPS_HOME = tmp_path
    settings.SCORE_WEB_COPIES = tmp_path / "served"
    handed = {}
    monkeypatch.setattr(convert, "write_copies", handed_on(handed))

    commands.main(["web3d", "alpha"])

    assert handed["place"] == "alpha" and handed["out"] == tmp_path / "served"
    assert handed["origin"] == {"from_output": standing,
                                "accepted_at": {"old": "2026-10-01T10:00:00", "new": "2026-10-02T10:00:00"}[standing]}
    assert convert.accepted_assembly(store, "nowhere") is None
    assert handed["linked"], "the accepted stage is linked from the store, never copied"
    assert handed["layers"] == {"Wall": "base", "Lamp": "light", "Shelf": "base"}
    assert handed["views"] == [{"name": "K01", "eye": [0, 1, 2], "aim": [0, 0, 0], "fov": 75.0},
                               {"name": "K02", "eye": [3, 1, 2], "aim": [0, 0, 0], "fov": 40.0}]
    assert convert.cameras("beta") == []
    assert handed["elsewhere"] == set()
    [haze] = handed["hazes"]  # beta's haze is a shown place's, not alpha's own
    assert haze["density"] == pytest.approx(0.025) and haze["reach"] == 24.0
    assert haze["low"] == [0.0, 0.0, 0.0] and haze["high"] == [2.0, 3.0, 4.0]
    assert haze["colour"] == pytest.approx([0.9, 0.8, 0.7])

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
