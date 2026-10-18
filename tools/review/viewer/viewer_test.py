"""Check the viewer: a stage made here (a five-sided face with a part of its own, a textured surface, a lamp, the sky)
exports to a meshopt-compressed binary with every triangle, its surfaces named and its texture at web size, and a
sidecar with the lamp, the sky and the boxes; picked viewpoints are saved, checked and read back; the server lists the
place, serves its viewer and copy, and saves a viewpoint sent to it. Runs gltfpack through npx; no Blender, no cloud.

Run: .venv/bin/python tools/review/viewer/viewer_test.py   (make tests runs it with the framework's environment)
"""
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
from PIL import Image
from pxr import Gf, Sdf, Usd, UsdGeom, UsdLux, UsdShade

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import export  # noqa: E402
import serve  # noqa: E402
import viewpoints  # noqa: E402

PLACE = "viewer_test_place"  # no scene record of this name: no cameras


def surface(stage, path, picture=None, colour=(0.5, 0.2, 0.1)):
    """A UsdPreviewSurface: its colour, roughness and metalness from `picture` (rgb, g, b) when given."""
    material = UsdShade.Material.Define(stage, path)
    shader = UsdShade.Shader.Define(stage, f"{path}/surface")
    shader.CreateIdAttr("UsdPreviewSurface")
    if picture:
        texture = UsdShade.Shader.Define(stage, f"{path}/picture")
        texture.CreateIdAttr("UsdUVTexture")
        texture.CreateInput("file", Sdf.ValueTypeNames.Asset).Set(str(picture))
        for name, channel, kind in (("diffuseColor", "rgb", "Color3f"), ("roughness", "g", "Float"),
                                    ("metallic", "b", "Float")):
            output = texture.CreateOutput(channel, getattr(Sdf.ValueTypeNames, "Float3" if channel == "rgb" else kind))
            shader.CreateInput(name, getattr(Sdf.ValueTypeNames, kind)).ConnectToSource(output)
    else:
        shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*colour))
    material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
    return material


def test_stage(folder):
    """A place: one mesh (a square and a pentagon, the pentagon a `trim` part), moved 2 m up, a lamp and a sky."""
    picture = folder / "paint.png"
    Image.new("RGB", (2048, 1024), (200, 120, 40)).save(picture)
    stage = Usd.Stage.CreateNew(str(folder / f"{PLACE}.usda"))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    root = UsdGeom.Xform.Define(stage, f"/{PLACE}")
    stage.SetDefaultPrim(root.GetPrim())
    thing = UsdGeom.Xform.Define(stage, f"/{PLACE}/Objects/crate_1")
    thing.AddTranslateOp().Set(Gf.Vec3d(0, 2, 0))
    mesh = UsdGeom.Mesh.Define(stage, f"/{PLACE}/Objects/crate_1/geo")
    mesh.CreatePointsAttr([(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0), (3, 0, 0), (4, 0, 0), (4.5, 1, 0), (3.5, 2, 0),
                           (2.5, 1, 0)])
    mesh.CreateFaceVertexCountsAttr([4, 5])
    mesh.CreateFaceVertexIndicesAttr([0, 1, 2, 3, 4, 5, 6, 7, 8])
    mesh.CreateNormalsAttr([(0, 0, 1)] * 9)
    mesh.SetNormalsInterpolation(UsdGeom.Tokens.vertex)
    UsdGeom.PrimvarsAPI(mesh).CreatePrimvar("st", Sdf.ValueTypeNames.TexCoord2fArray, UsdGeom.Tokens.vertex).Set(
        [(0, 0), (1, 0), (1, 1), (0, 1), (0, 0), (1, 0), (1, 1), (0.5, 1), (0, 1)])
    UsdShade.MaterialBindingAPI.Apply(mesh.GetPrim()).Bind(surface(stage, f"/{PLACE}/Objects/crate_1/Looks/baked",
                                                                      picture))
    trim = UsdGeom.Subset.CreateGeomSubset(mesh, "trim", UsdGeom.Tokens.face, [1], "materialBind")
    UsdShade.MaterialBindingAPI.Apply(trim.GetPrim()).Bind(surface(stage, f"/{PLACE}/Objects/crate_1/Looks/trim"))
    hidden = UsdGeom.Mesh.Define(stage, f"/{PLACE}/Objects/crate_1/collision")
    hidden.CreatePointsAttr([(0, 0, 0), (1, 0, 0), (0, 1, 0)])
    hidden.CreateFaceVertexCountsAttr([3])
    hidden.CreateFaceVertexIndicesAttr([0, 1, 2])
    hidden.CreatePurposeAttr(UsdGeom.Tokens.guide)
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
    return folder / f"{PLACE}.usda"


def glb_document(path):
    """The JSON chunk of a glTF binary."""
    data = path.read_bytes()
    length, kind = struct.unpack_from("<I4s", data, 12)
    assert kind == b"JSON"
    return json.loads(data[20:20 + length])


def check_fan():
    triangles, faces = export.fan([3, 5, 4])
    assert triangles.tolist() == [[0, 1, 2], [3, 4, 5], [3, 5, 6], [3, 6, 7], [8, 9, 10], [8, 10, 11]]
    assert faces.tolist() == [0, 1, 1, 1, 2, 2]


def check_export(stage, out):
    sidecar = json.loads(export.export(PLACE, stage, out).read_text())
    document = glb_document(out / PLACE / f"{PLACE}.glb")
    assert sidecar["triangles"] == 2 + 3, "every triangle of the square and the pentagon, nothing of the guide"
    assert "EXT_meshopt_compression" in document["extensionsRequired"]
    assert sorted(material["name"] for material in document["materials"]) == ["baked", "trim"]
    baked = next(material for material in document["materials"] if material["name"] == "baked")
    assert "baseColorTexture" in baked["pbrMetallicRoughness"]
    assert "metallicRoughnessTexture" in baked["pbrMetallicRoughness"], "one picture: colour, roughness (g), metal (b)"
    assert len(document["images"]) == 1 and document["images"][0]["mimeType"] == "image/jpeg"
    assert [box["name"] for box in sidecar["objects"]] == ["Objects/crate_1"]
    assert sidecar["objects"][0]["low"] == [0.0, 2.0, 0.0] and sidecar["objects"][0]["high"] == [4.5, 4.0, 0.0]
    [lamp] = sidecar["lights"]
    assert lamp["type"] == "point" and lamp["at"] == [1.0, 3.0, 1.0] and lamp["colour"] == [1.0, 0.5, 0.25]
    assert math.isclose(lamp["intensity"], 20.0 * export.CANDELA_PER_INTENSITY)
    assert np.allclose(sidecar["sky"]["ambient"], np.array([0.2, 0.2, 0.4]) * 0.5 * math.pi)
    assert np.allclose(sidecar["sky"]["background"], [0.01, 0.02, 0.03]) and math.isclose(sidecar["sky"]["exposure"],
                                                                                           0.85, rel_tol=1e-6)
    assert sidecar["cameras"] == [] and sidecar["left_out"] == {}


def check_web_picture(folder):
    wide, see_through = folder / "wide.png", folder / "cut.png"
    Image.new("RGB", (4096, 2048), (10, 20, 30)).save(wide)
    picture = Image.new("RGBA", (64, 64), (10, 20, 30, 255))
    picture.putpixel((0, 0), (0, 0, 0, 0))
    picture.save(see_through)
    assert export.web_picture(str(wide), folder / "a") == "a.jpg"
    assert Image.open(folder / "a.jpg").size == (export.TEXTURE_SIZE, export.TEXTURE_SIZE // 2)
    assert export.web_picture(str(see_through), folder / "b") == "b.png", "a see-through picture keeps its alpha"


def check_viewpoints(root):
    view = {"eye": [1, 1.6, 2], "aim": [0, 1.2, -3], "fov": 80}
    assert viewpoints.read(PLACE, root) == []
    first = viewpoints.append(PLACE, dict(view, name="  by  the door "), root)
    second = viewpoints.append(PLACE, dict(view, name="by the door"), root)
    third = viewpoints.append(PLACE, view, root)
    assert [first["name"], second["name"], third["name"]] == ["by the door", "pick-1", "pick-2"]
    assert [each["name"] for each in viewpoints.read(PLACE, root)] == ["by the door", "pick-1", "pick-2"]
    for bad in ({"eye": [1, 2], "aim": [0, 0, 0]}, {"eye": [1, 2, float("nan")], "aim": [0, 0, 0]},
                {"eye": [0, 0, 0], "aim": [0, 0, 0]}, {"eye": [1, 2, 3], "aim": [0, 0, 0], "fov": 0}):
        try:
            viewpoints.append(PLACE, bad, root)
        except viewpoints.BadViewpoint:
            continue
        raise AssertionError(f"saved a bad viewpoint {bad}")
    try:
        viewpoints.read("../escape", root)
        raise AssertionError("read outside the picks folder")
    except viewpoints.BadViewpoint:
        pass


def fetch(url, body=None):
    """The status and body of a GET, or of a POST of `body` as JSON."""
    request = urllib.request.Request(url, data=None if body is None else json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request) as answer:
            return answer.status, answer.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()


def check_server(web, picks):
    server = ThreadingHTTPServer(("127.0.0.1", 0), serve.handler(web, picks))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        status, page = fetch(f"{base}/")
        assert status == 200 and f'href="/view/{PLACE}"'.encode() in page
        status, page = fetch(f"{base}/view/{PLACE}")
        assert status == 200 and b"three.module.min.js" in page
        status, glb = fetch(f"{base}/web/{PLACE}/{PLACE}.glb")
        assert status == 200 and glb[:4] == b"glTF"
        assert fetch(f"{base}/web/{PLACE}/gltfpack.log")[0] == 404, "only the copy and its sidecar are served"
        assert fetch(f"{base}/view/nowhere")[0] == 404
        status, saved = fetch(f"{base}/picks/{PLACE}", {"name": "wide", "eye": [0, 1.6, 5], "aim": [0, 1, 0],
                                                        "fov": 75})
        assert status == 200 and json.loads(saved)["name"] == "wide"
        assert fetch(f"{base}/picks/{PLACE}", {"eye": "here"})[0] == 400
        status, listed = fetch(f"{base}/picks/{PLACE}")
        assert [each["name"] for each in json.loads(listed)["viewpoints"]] == ["wide"]
        assert json.loads((picks / PLACE / "viewpoints.json").read_text())["viewpoints"][0]["eye"] == [0, 1.6, 5]
    finally:
        server.shutdown()


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[3] / "conftest.py"))["refuse_outside_sandbox"]()
    check_fan()
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        check_web_picture(folder)
        check_export(test_stage(folder), folder / "web")
        check_viewpoints(folder / "picks")
        check_server(folder / "web", folder / "served-picks")
    print("viewer_test: ok")
