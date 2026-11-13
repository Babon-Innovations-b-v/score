"""Check the viewer: a stage made here (one crate of a triangle, a five-sided `trim` part with a see-through picture
and a square, under a picture twice web size; a guide mesh; a floor in a library tile; a lamp; the sky) exports to a
meshopt-compressed binary with every drawn triangle, its surfaces named, its pictures at web size (the see-through one
keeping its alpha) and the tile's repeat on every tile picture, and a sidecar with the lamp, the sky and the boxes;
the server over that copy lists the place, serves its viewer and copy and nothing else of it, and saves, checks and
reads back the viewpoints sent to it. Runs gltfpack through npx; no Blender, no cloud.

Breaks (each applied once, seen red, reverted), in tools/review/viewer/ (export.py unless named):
- polygons as fans: fan starts each triangle one corner late (`first + step`).
- the export whole: drawn takes every mesh, the guide purpose too (`shown = True`).
- a web-size picture: web_picture never keeps a see-through picture's alpha (`see_through = False`).
- a tile's repeat: repeat_scale finds no scale (`return None`).
- picks saved and checked: viewpoints.checked keeps a name already taken.
- the server: serve.py's handler serves any file under a place's copy, its gltfpack.log too.

Run: PROPS_HOME=$(mktemp -d) .venv/bin/python tools/review/viewer/test_the_web_copy_is_the_stage_whole_and_the_picks_are_kept.py
"""
import io
import json
import math
import pathlib
import struct
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import numpy as np
import pytest
from PIL import Image
from pxr import Gf, Sdf, Usd, UsdGeom, UsdLux, UsdShade

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import export  # noqa: E402
import serve  # noqa: E402
import shaders  # noqa: E402  (tools/usd, on the path export.py sets)
import viewpoints  # noqa: E402

PLACE = "viewer_test_place"  # no scene record of this name: no cameras
TILE_METRES = 2.0  # the deck tile repeats every 2 m: a 0.5 scale on the floor's metre uvs
# gltfpack stores texture coordinates in 12 bits of a normalized uint16 and folds the material's own repeat into the
# KHR_texture_transform that undoes it: the scale it writes is the uvs' span times the repeat times 65535 / 4095.
UV_BITS_SCALE = 65535 / 4095
LOOK = {"eye": [1, 1.6, 2], "aim": [0, 1.2, -3], "fov": 80}
# (what is sent to POST /picks/<place>, the status answered, the name it is saved under)
PICKS_SENT = [
    (dict(LOOK, name="  by  the door "), 200, "by the door"),
    (dict(LOOK, name="by the door"), 200, "pick-1"),
    (LOOK, 200, "pick-2"),
    ({"name": "wide", "eye": [0, 1.6, 5], "aim": [0, 1, 0], "fov": 75}, 200, "wide"),
    ({"eye": "here"}, 400, None),
    ({"eye": [1, 2], "aim": [0, 0, 0]}, 400, None),
    ({"eye": [1, 2, float("nan")], "aim": [0, 0, 0]}, 400, None),
    ({"eye": [0, 0, 0], "aim": [0, 0, 0]}, 400, None),
    ({"eye": [1, 2, 3], "aim": [0, 0, 0], "fov": 0}, 400, None),
]
# (a GET path, the status answered, bytes the answer holds)
SERVED = [
    ("/", 200, f'href="/view/{PLACE}"'.encode()),
    (f"/view/{PLACE}", 200, b"three.module.min.js"),
    (f"/web/{PLACE}/{PLACE}.glb", 200, b"glTF"),
    (f"/web/{PLACE}/gltfpack.log", 404, b"nothing at"),
    ("/view/nowhere", 404, b"nothing at"),
]


def surface(stage, path, picture):
    """A UsdPreviewSurface with its colour, roughness and metalness from `picture` (rgb, g, b)."""
    material = UsdShade.Material.Define(stage, path)
    shader = UsdShade.Shader.Define(stage, f"{path}/surface")
    shader.CreateIdAttr("UsdPreviewSurface")
    texture = UsdShade.Shader.Define(stage, f"{path}/picture")
    texture.CreateIdAttr("UsdUVTexture")
    texture.CreateInput("file", Sdf.ValueTypeNames.Asset).Set(str(picture))
    for name, channel, kind in (("diffuseColor", "rgb", "Color3f"), ("roughness", "g", "Float"),
                                ("metallic", "b", "Float")):
        output = texture.CreateOutput(channel, getattr(Sdf.ValueTypeNames, "Float3" if channel == "rgb" else kind))
        shader.CreateInput(name, getattr(Sdf.ValueTypeNames, kind)).ConnectToSource(output)
    material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
    return material


def pictures(folder):
    """The crate's picture (twice web size), the trim's see-through one and the deck's library tile: their paths."""
    wide, see_through, tiles = folder / "paint.png", folder / "cut.png", folder / "tiles"
    Image.new("RGB", (2 * export.TEXTURE_SIZE, export.TEXTURE_SIZE), (200, 120, 40)).save(wide)
    cut = Image.new("RGBA", (64, 64), (10, 20, 30, 255))
    cut.putpixel((0, 0), (0, 0, 0, 0))
    cut.save(see_through)
    tiles.mkdir()
    for role in shaders.TILE_ROLES:
        Image.new("RGB", (8, 8), (90, 90, 90)).save(tiles / f"deck_{role}.png")
    (tiles / "tiles.json").write_text(json.dumps({"deck": {"metres": TILE_METRES, "side": 8}}))
    return wide, see_through, tiles


def mesh(stage, path, points, counts, uvs):
    """A mesh of `points` with faces of `counts` corners in order, facing +z, its uvs per point."""
    made = UsdGeom.Mesh.Define(stage, path)
    made.CreatePointsAttr(points)
    made.CreateFaceVertexCountsAttr(counts)
    made.CreateFaceVertexIndicesAttr(list(range(len(points))))
    made.CreateNormalsAttr([(0, 0, 1)] * len(points))
    made.SetNormalsInterpolation(UsdGeom.Tokens.vertex)
    UsdGeom.PrimvarsAPI(made).CreatePrimvar("st", Sdf.ValueTypeNames.TexCoord2fArray, UsdGeom.Tokens.vertex).Set(uvs)
    return made


def a_stage(folder):
    """A place: a crate moved 2 m up (a triangle, a pentagon that is its `trim` part, a square; a guide mesh beside),
    a 2 m floor in the deck tile, a lamp and a sky: the stage's path."""
    wide, see_through, tiles = pictures(folder)
    path = folder / "stage" / PLACE / f"{PLACE}.usda"
    path.parent.mkdir(parents=True)
    stage = Usd.Stage.CreateNew(str(path))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    root = UsdGeom.Xform.Define(stage, f"/{PLACE}")
    stage.SetDefaultPrim(root.GetPrim())
    UsdGeom.Xform.Define(stage, f"/{PLACE}/Objects/crate_1").AddTranslateOp().Set(Gf.Vec3d(0, 2, 0))
    crate = mesh(stage, f"/{PLACE}/Objects/crate_1/geo",
                 [(0, 0, 0), (1, 0, 0), (0, 1, 0), (3, 0, 0), (4, 0, 0), (4.5, 1, 0), (3.5, 2, 0), (2.5, 1, 0),
                  (5, 0, 0), (6, 0, 0), (6, 1, 0), (5, 1, 0)], [3, 5, 4],
                 [(0, 0), (1, 0), (0, 1), (0, 0), (1, 0), (1, 1), (0.5, 1), (0, 1), (0, 0), (1, 0), (1, 1), (0, 1)])
    UsdShade.MaterialBindingAPI.Apply(crate.GetPrim()).Bind(surface(stage, f"/{PLACE}/Objects/crate_1/Looks/baked",
                                                                       wide))
    trim = UsdGeom.Subset.CreateGeomSubset(crate, "trim", UsdGeom.Tokens.face, [1], "materialBind")
    UsdShade.MaterialBindingAPI.Apply(trim.GetPrim()).Bind(surface(stage, f"/{PLACE}/Objects/crate_1/Looks/trim",
                                                                      see_through))
    mesh(stage, f"/{PLACE}/Objects/crate_1/collision", [(0, 0, 0), (1, 0, 0), (0, 1, 0)], [3],
         [(0, 0), (1, 0), (0, 1)]).CreatePurposeAttr(UsdGeom.Tokens.guide)
    floor = mesh(stage, f"/{PLACE}/Objects/floor_1/geo", [(0, 0, 0), (2, 0, 0), (2, 2, 0), (0, 2, 0)], [4],
                 [(0, 0), (2, 0), (2, 2), (0, 2)])
    UsdShade.MaterialBindingAPI.Apply(floor.GetPrim()).Bind(shaders.tile_look(stage, PLACE, "deck", folder / "stage",
                                                                              tiles))
    lamp = UsdLux.SphereLight.Define(stage, f"/{PLACE}/Lights/light_1")
    lamp.CreateIntensityAttr(20.0)
    lamp.CreateColorAttr(Gf.Vec3f(1.0, 0.5, 0.25))
    lamp.AddTranslateOp().Set(Gf.Vec3d(1, 3, 1))
    dome = UsdLux.DomeLight.Define(stage, f"/{PLACE}/Environment")
    dome.CreateIntensityAttr(0.5)
    dome.CreateColorAttr(Gf.Vec3f(0.2, 0.2, 0.4))
    dome.GetPrim().CreateAttribute("score:background", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(0.01, 0.02, 0.03))
    dome.GetPrim().CreateAttribute("score:exposure", Sdf.ValueTypeNames.Float).Set(0.85)
    stage.Save()
    return path


def glb(path):
    """A glTF binary's JSON document and its binary chunk."""
    data = path.read_bytes()
    length, kind = struct.unpack_from("<I4s", data, 12)
    assert kind == b"JSON"
    return json.loads(data[20:20 + length]), data[20 + length + 8:]


def picture_of(document, binary, reference):
    """The mime type and the opened picture a material's texture reference points at in the binary."""
    image = document["images"][document["textures"][reference["index"]]["source"]]
    view = document["bufferViews"][image["bufferView"]]
    start = view.get("byteOffset", 0)
    return image["mimeType"], Image.open(io.BytesIO(binary[start:start + view["byteLength"]]))


def fetch(url, body=None):
    """The status and body of a GET, or of a POST of `body` as JSON."""
    request = urllib.request.Request(url, data=None if body is None else json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request) as answer:
            return answer.status, answer.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()


def test_the_web_copy_is_the_stage_whole_and_the_picks_are_kept():
    folder = pathlib.Path(tempfile.mkdtemp())
    stage, web, picks = a_stage(folder), folder / "web", folder / "picks"
    export.export(PLACE, stage, web)
    sidecar = json.loads((web / PLACE / f"{PLACE}.json").read_text())
    document, binary = glb(web / PLACE / f"{PLACE}.glb")

    opened = Usd.Stage.Open(str(stage))
    triangles, faces = export.fan(
        UsdGeom.Mesh(opened.GetPrimAtPath(f"/{PLACE}/Objects/crate_1/geo")).GetFaceVertexCountsAttr().Get())
    assert triangles.tolist() == [[0, 1, 2], [3, 4, 5], [3, 5, 6], [3, 6, 7], [8, 9, 10], [8, 10, 11]]
    assert faces.tolist() == [0, 1, 1, 1, 2, 2]
    assert sidecar["triangles"] == 1 + 3 + 2 + 2, "every triangle of the crate and the floor, nothing of the guide"
    assert "EXT_meshopt_compression" in document["extensionsRequired"]

    materials = {material["name"]: material for material in document["materials"]}
    assert sorted(materials) == ["baked", "deck", "trim"]
    baked, trim = materials["baked"]["pbrMetallicRoughness"], materials["trim"]["pbrMetallicRoughness"]
    assert baked["metallicRoughnessTexture"]["index"] == baked["baseColorTexture"]["index"], \
        "one picture: colour, roughness (g), metal (b)"
    kind, picture = picture_of(document, binary, baked["baseColorTexture"])
    assert (kind, picture.size) == ("image/jpeg", (export.TEXTURE_SIZE, export.TEXTURE_SIZE // 2)), "web size"
    kind, picture = picture_of(document, binary, trim["baseColorTexture"])
    assert (kind, picture.mode) == ("image/png", "RGBA"), "a see-through picture keeps its alpha"
    assert picture.getpixel((0, 0))[3] == 0
    deck = materials["deck"]
    for reference in (deck["pbrMetallicRoughness"]["baseColorTexture"],
                      deck["pbrMetallicRoughness"]["metallicRoughnessTexture"], deck["normalTexture"]):
        assert reference["extensions"][export.TRANSFORM]["scale"] == pytest.approx(
            [2.0 / TILE_METRES * UV_BITS_SCALE] * 2, rel=1e-5), f"the tile's repeat on every picture: {reference}"
    assert len(document["images"]) == 2 + len(shaders.TILE_ROLES)

    assert sidecar["objects"] == [{"name": "Objects/crate_1", "low": [0.0, 2.0, 0.0], "high": [6.0, 4.0, 0.0]},
                                  {"name": "Objects/floor_1", "low": [0.0, 0.0, 0.0], "high": [2.0, 2.0, 0.0]}]
    [lamp] = sidecar["lights"]
    assert lamp["type"] == "point" and lamp["at"] == [1.0, 3.0, 1.0] and lamp["colour"] == [1.0, 0.5, 0.25]
    assert math.isclose(lamp["intensity"], 20.0 * export.CANDELA_PER_INTENSITY)
    assert np.allclose(sidecar["sky"]["ambient"], np.array([0.2, 0.2, 0.4]) * 0.5 * math.pi)
    assert np.allclose(sidecar["sky"]["background"], [0.01, 0.02, 0.03]) and math.isclose(sidecar["sky"]["exposure"],
                                                                                           0.85, rel_tol=1e-6)
    assert sidecar["cameras"] == [] and sidecar["left_out"] == {}

    server = ThreadingHTTPServer(("127.0.0.1", 0), serve.handler(web, picks))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        for path, status, held in SERVED:
            answered, body = fetch(f"{base}{path}")
            assert (answered, held in body) == (status, True), f"GET {path}: {answered} {body[:200]!r}"
        assert json.loads(fetch(f"{base}/picks/{PLACE}")[1])["viewpoints"] == [], "no pick before one is sent"
        for sent, status, name in PICKS_SENT:
            answered, body = fetch(f"{base}/picks/{PLACE}", sent)
            assert (answered, json.loads(body).get("name")) == (status, name), f"POST {sent}: {answered} {body!r}"
        listed = json.loads(fetch(f"{base}/picks/{PLACE}")[1])["viewpoints"]
    finally:
        server.shutdown()
    saved = [name for _, status, name in PICKS_SENT if status == 200]
    assert [each["name"] for each in listed] == saved
    assert [each["name"] for each in viewpoints.read(PLACE, picks)] == saved, "read back from the picks folder"
    assert json.loads((picks / PLACE / "viewpoints.json").read_text())["viewpoints"][-1]["eye"] == [0, 1.6, 5]
    with pytest.raises(viewpoints.BadViewpoint):
        viewpoints.read("../escape", picks)


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(HERE.parents[2] / "conftest.py"))["refuse_outside_sandbox"]()
    test_the_web_copy_is_the_stage_whole_and_the_picks_are_kept()
    print("ok test_the_web_copy_is_the_stage_whole_and_the_picks_are_kept")
