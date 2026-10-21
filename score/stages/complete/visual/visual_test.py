"""The visual check: the surfaces it reads off a stage are the ones the stage holds, and a neighbour standing inside
a room is found. (Its fixture of the old concepts' films, data/checks/visual, was retired with them on 2026-10-21; a
fixture is measured again from today's films with measure.gather.)

Run: .venv/bin/python score/stages/complete/visual/visual_test.py
"""
import pathlib
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))
from pxr import Gf, Sdf, Usd, UsdGeom, UsdShade  # noqa: E402

from score.stages.complete.visual import room, seen  # noqa: E402

def quad(stage, path, corners):
    """A one-face mesh with texture coordinates."""
    mesh = UsdGeom.Mesh.Define(stage, path)
    mesh.CreatePointsAttr([Gf.Vec3f(*corner) for corner in corners])
    mesh.CreateFaceVertexCountsAttr([4])
    mesh.CreateFaceVertexIndicesAttr([0, 1, 2, 3])
    UsdGeom.PrimvarsAPI(mesh).CreatePrimvar("st", Sdf.ValueTypeNames.TexCoord2fArray).Set(
        [(0, 0), (1, 0), (1, 1), (0, 1)])
    return mesh


def preview(stage, path, colour=None, texture=None):
    """A UsdPreviewSurface material in a plain colour, or reading a texture file."""
    material = UsdShade.Material.Define(stage, path)
    surface = UsdShade.Shader.Define(stage, f"{path}/surface")
    surface.CreateIdAttr("UsdPreviewSurface")
    material.CreateSurfaceOutput().ConnectToSource(surface.ConnectableAPI(), "surface")
    if colour is not None:
        surface.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(colour)
    if texture is not None:
        image = UsdShade.Shader.Define(stage, f"{path}/image")
        image.CreateIdAttr("UsdUVTexture")
        image.CreateInput("file", Sdf.ValueTypeNames.Asset).Set(texture)
        surface.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).ConnectToSource(
            image.ConnectableAPI(), "rgb")
    return material


def made_stage(folder):
    """A stage of four walls side by side before the camera: textured, a missing texture, a plain floor-like
    `Outside/near`, and one with no material."""
    (folder / "wood.png").write_bytes(b"not read, only resolved")
    stage = Usd.Stage.CreateNew(str(folder / "test.usda"))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    stage.SetDefaultPrim(UsdGeom.Xform.Define(stage, "/test").GetPrim())
    walls = {"/test/Objects/crate_1/geo": preview(stage, "/test/Looks/wood", texture="./wood.png"),
             "/test/Objects/lost_1/geo": preview(stage, "/test/Looks/lost", texture="./lost.png"),
             "/test/Outside/near": preview(stage, "/test/Looks/regolith", colour=(0.3, 0.3, 0.28)),
             "/test/Objects/bare_1/geo": None}
    for number, (path, material) in enumerate(walls.items()):
        left = -4 + number * 2
        mesh = quad(stage, path, [(left, -2, 0), (left + 2, -2, 0), (left + 2, 2, 0), (left, 2, 0)])
        if material is not None:
            UsdShade.MaterialBindingAPI.Apply(mesh.GetPrim()).Bind(material)
    stage.GetRootLayer().Save()
    return stage


def kinds_read_off_a_stage():
    """Each wall's surface kind as the check reads it through a camera, against the kind it was made with."""
    with tempfile.TemporaryDirectory() as temporary:
        stage = made_stage(pathlib.Path(temporary))
        view = {"eye": [0, 0, 6], "aim": [0, 0, 0], "up": [0, 1, 0], "fov": 80.0}
        sight = seen.record(stage, seen.gathered(stage), view, grid=(48, 27))
    met = {path: kind for path, _, kind in sight["surfaces"]}
    wanted = {"/test/Objects/crate_1/geo": seen.TEXTURED, "/test/Objects/lost_1/geo": seen.TEXTURE_MISSING,
              "/test/Outside/near": seen.PLAIN_COLOUR, "/test/Objects/bare_1/geo": seen.NO_MATERIAL}
    return [f"{path}: read as {met.get(path)}, made as {kind}" for path, kind in wanted.items() if met.get(path) != kind]


def room_stage(folder):
    """A 4 m box room of named walls, floor and roof, a neighbour's panel standing 1 m inside it and another's
    meeting its wall from outside."""
    stage = Usd.Stage.CreateNew(str(folder / "room.usda"))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    faces = {"floor_1": [(-2, 0, -2), (2, 0, -2), (2, 0, 2), (-2, 0, 2)],
             "roof_1": [(-2, 3, -2), (2, 3, -2), (2, 3, 2), (-2, 3, 2)],
             "wall_1": [(-2, 0, -2), (2, 0, -2), (2, 3, -2), (-2, 3, -2)],
             "wall_2": [(-2, 0, 2), (2, 0, 2), (2, 3, 2), (-2, 3, 2)]}
    for name, corners in faces.items():
        quad(stage, f"/room/Objects/{name}/geo", corners)
    quad(stage, "/room/Places/tube/Objects/panel_1/geo", [(-1, 0.5, 1), (1, 0.5, 1), (1, 2.5, 1), (-1, 2.5, 1)])
    quad(stage, "/room/Places/hall/Objects/panel_1/geo", [(-1, 0.5, 2), (1, 0.5, 2), (1, 2.5, 3), (-1, 2.5, 3)])
    return stage


def neighbours_read_inside_a_room():
    """The panel inside the room is found, the one meeting the wall is not."""
    with tempfile.TemporaryDirectory() as temporary:
        found = [item["prim"] for item in room.intrusions(room_stage(pathlib.Path(temporary)), "room")]
    wanted = ["/room/Places/tube/Objects/panel_1/geo"]
    return [] if found == wanted else [f"a room's neighbours inside read {found}, not {wanted}"]


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[4] / "conftest.py"))["refuse_outside_sandbox"]()
    failures = kinds_read_off_a_stage() + neighbours_read_inside_a_room()
    for failure in failures:
        print(failure)
    print("ok" if not failures else f"{len(failures)} failed")
    sys.exit(1 if failures else 0)
