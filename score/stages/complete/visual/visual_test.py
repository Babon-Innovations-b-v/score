"""The visual check: its known-bad fixture fails and its clean place passes, the surfaces it reads off a stage are
the ones the stage holds, and a run writes findings, marked pictures and a contact sheet.

The fixture (data/checks/visual/<place>/) is real evidence measured from the store on 2026-10-18 (measure.py), two
pictures a place: old_station's film, where a neighbour's flat untextured ground cuts across the view, the wreck's,
whose floor has no texture, the airlock's, where the walkway tube's panels stand inside the room, and the
workshop's, which is clean.

Run: .venv/bin/python score/stages/complete/visual/visual_test.py
"""
import json
import pathlib
import shutil
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))
from pxr import Gf, Sdf, Usd, UsdGeom, UsdShade  # noqa: E402

from score.stages.complete.visual import __main__ as run  # noqa: E402
from score.stages.complete.visual import judge, room, seen  # noqa: E402

FIXTURE = REPO / "data/checks/visual"
EXPECTED = {"old_station": "fail", "wreck": "fail", "airlock": "fail", "workshop": "pass"}


def fixture_answers():
    """Each fixture place's answer against the one it must give, and the faults it must name."""
    problems = []
    found = {}
    for place, wanted in EXPECTED.items():
        evidence = judge.read(FIXTURE / place)
        found[place] = judge.findings(evidence, FIXTURE / place)
        answer = judge.verdict(evidence, found[place])
        if answer != wanted:
            problems.append(f"{place}: {answer}, not {wanted} ({[item['sentence'] for item in found[place]]})")
    named = {(item["rule"], item["prim"]) for item in found["old_station"]}
    if (judge.BLOCKING, "/old_station/Places/habitat_tube/Outside/near") not in named:
        problems.append(f"old_station: the neighbour's ground across the view is not named as a blocking plane: {named}")
    if not any(item["rule"] == judge.UNTEXTURED and "Outside/near" in item["prim"] for item in found["wreck"]):
        problems.append(f"wreck: its untextured ground is not named: {[item['prim'] for item in found['wreck']]}")
    if not any(item["rule"] == judge.INSIDE and "/Places/lab_tube/" in item["prim"] for item in found["airlock"]):
        problems.append(f"airlock: the tube inside the room is not named: {[item['prim'] for item in found['airlock']]}")
    return problems


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


def a_run_writes_its_pictures():
    """A judge-only run over a copy of the fixture: findings.json per place, a marked picture per finding, the
    contact sheet and the summary."""
    with tempfile.TemporaryDirectory() as temporary:
        out = pathlib.Path(temporary)
        for place in EXPECTED:
            shutil.copytree(FIXTURE / place, out / place)
        run.main(["--judge-only", "--out", str(out), *[part for place in EXPECTED for part in ("--place", place)]])
        problems = []
        for place, wanted in EXPECTED.items():
            written = json.loads((out / place / run.FINDINGS).read_text())
            if written["answer"] != wanted:
                problems.append(f"{place}: findings.json says {written['answer']}, not {wanted}")
            problems += [f"{place}: no picture {item['picture']}" for item in written["findings"]
                         if not (out / place / item["picture"]).is_file()]
        if not (out / "contact_sheet.png").is_file() or not (out / "summary.json").is_file():
            problems.append("no contact sheet or summary")
        return problems


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(REPO / "conftest.py"))["refuse_outside_sandbox"]()
    failures = (fixture_answers() + kinds_read_off_a_stage() + neighbours_read_inside_a_room()
                + a_run_writes_its_pictures())
    for failure in failures:
        print(failure)
    print("ok" if not failures else f"{len(failures)} failed")
    sys.exit(1 if failures else 0)
