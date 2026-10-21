"""Check the placeholder check on a stage made here: a box that says it is a plain plate passes and one that says
nothing fails, a lathe called a ship fails, a room's own walls pass, a kit piece built in code passes when the sorter
sends its kind to code (its pipeline failure named) and fails when the sorter sends it to the prop pipeline, a mesh with no material or in the
default grey fails, a clear haze shell passes, a proxy fails, and a guide mesh and another place's stage are not
judged. The hangar's case (the owner's demo of 2026-10-11: the check passed the code-built ship he saw as a
placeholder): the ship_hull and ship_legs its record drew until 2026-10-18 fail and a made model in their place passes,
and today's hangar stage (HANGAR_STAGE, when this machine has it) fails while it still holds them (since 2026-10-18 the
record lays no ship: the kit's code-built ship stands on the pads, judged by the sorter rule).

Run: .venv/bin/python tools/usd/placeholders_test.py   (make tests runs it with the framework's environment)
"""
import json
import pathlib
import sys
import tempfile

from pxr import Gf, Sdf, Usd, UsdGeom, UsdShade

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import export  # noqa: E402
import placeholders  # noqa: E402
import scene  # noqa: E402

PLACE = "hub"
REPO = HERE.parents[1]
# The world 1 demo's hangar stage (r4 was filmed from it), outside the repo: checked when this machine has it.
HANGAR_STAGE = pathlib.Path.home() / ".farm-factory-props/work/usd-r3/hangar/hangar.usda"
HANGAR_SHIP = ("ship", "ship_legs")
# The game's upright ship as the hangar's scene record drew it until 2026-10-18, its two code builders.
OLD_HANGAR_SHIP = [{'name': 'ship',
                     'builder': 'ship_hull',
                     'centre': [0.0, 0.5, 8.9],
                     'surface': 'hull_white_gloss',
                     'nose_surface': 'painted_panel',
                     'band_surface': 'hazard_paint',
                     'stripe_surface': 'dark_panel',
                     'seam_surface': 'bare_steel',
                     'steel_surface': 'bare_steel',
                     'glass_surface': 'glass'},
                    {'name': 'ship_legs',
                     'builder': 'ship_legs',
                     'centre': [0.0, 0.5, 8.9],
                     'surface': 'bare_steel',
                     'foot_surface': 'painted_panel'}]
RECORD = {"structure": [
    {"name": "walls", "builder": "room_walls", "wide": 4.0, "deep": 5.0, "corner": 0.6, "high": 2.8,
     "surface": "roof_steel_paint", "doors": []},
    {"name": "slab", "builder": "box", "centre": [0.0, 0.05, 0.0], "size": [2.0, 0.1, 2.0],
     "surface": "roof_steel_paint", "plain": "plate"},
    {"name": "door_leaf", "builder": "box", "centre": [0.0, 1.0, 2.5], "size": [1.0, 2.0, 0.1],
     "surface": "painted_panel"},
    {"name": "ship_body", "builder": "lathe", "profile": [[0.0, 1.6, 5.0, 1.6]], "centre": [3.0, 0.0, 3.0],
     "surface": "hull_white_gloss", "plain": "ship"},
]}
KIT = {"models": {"wall_lower_plain_1": {"route": "code"}, "pipe_straight_1": {"route": "code"},
                  "rover_1": {"route": "code"}, "locker_1": {"route": "model"}}}


def square(stage, path):
    """A one-metre square mesh at path."""
    mesh = UsdGeom.Mesh.Define(stage, path)
    mesh.CreatePointsAttr([Gf.Vec3f(0, 0, 0), Gf.Vec3f(1, 0, 0), Gf.Vec3f(1, 0, 1), Gf.Vec3f(0, 0, 1)])
    mesh.CreateFaceVertexCountsAttr([4])
    mesh.CreateFaceVertexIndicesAttr([0, 1, 2, 3])
    return mesh


def surface(stage, path, **inputs):
    """A UsdPreviewSurface material with only the given inputs set."""
    material = UsdShade.Material.Define(stage, path)
    shader = UsdShade.Shader.Define(stage, f"{path}/surface")
    shader.CreateIdAttr("UsdPreviewSurface")
    for name, (kind, value) in inputs.items():
        shader.CreateInput(name, kind).Set(value)
    material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
    return material


def painted(stage, path, material):
    """A square painted with a material."""
    mesh = square(stage, path)
    UsdShade.MaterialBindingAPI.Apply(mesh.GetPrim()).Bind(material)
    return mesh


def library_surface(stage, path):
    """A library surface as export.library_materials writes one (a coloured UsdPreviewSurface), stood in at `path`:
    the old library's surfaces are retired (2026-10-21) and the remake makes each scene's fresh."""
    material = surface(stage, path, diffuseColor=(Sdf.ValueTypeNames.Color3f, Gf.Vec3f(0.8, 0.8, 0.78)),
                       roughness=(Sdf.ValueTypeNames.Float, 0.5))
    for key, value in (("recipe", "painted_metal"), ("token", "test_white"), ("family", "painted")):
        material.GetPrim().CreateAttribute(f"score:{key}", Sdf.ValueTypeNames.String).Set(value)
    return material


def library_surfaces(stage, place, record):
    """The library surfaces a scene record names (every `...surface` value), stood in under /<place>/Library."""
    def named(value, key=""):
        if isinstance(value, dict):
            return {name for inner, item in value.items() for name in named(item, inner)}
        if isinstance(value, list):
            return {name for item in value for name in named(item, key)}
        return {value} if key.endswith("surface") and isinstance(value, str) else set()
    for name in named(record):
        library_surface(stage, f"/{place}/Library/{name}")


def kit_piece(stage, model, kind):
    """A kit piece: its xform with its model and kind, and its drawn mesh in a library colour."""
    piece = UsdGeom.Xform.Define(stage, f"/{PLACE}/Objects/{model}")
    piece.GetPrim().CreateAttribute("score:model", Sdf.ValueTypeNames.String).Set(model)
    piece.GetPrim().CreateAttribute("score:kind", Sdf.ValueTypeNames.String).Set(kind)
    painted(stage, f"/{PLACE}/Objects/{model}/geo", library_surface(stage, f"/{PLACE}/Library/painted_panel"))


def test_stage(folder):
    """The test place's stage, every case on it; its path."""
    path = folder / "hub.usda"
    stage = Usd.Stage.CreateNew(str(path))
    stage.SetDefaultPrim(UsdGeom.Xform.Define(stage, f"/{PLACE}").GetPrim())
    export.library_materials(stage, PLACE, f"/{PLACE}")
    library_surfaces(stage, PLACE, RECORD)
    scene.write(stage, PLACE, RECORD, folder)
    for model, kind in (("wall_lower_plain_1", "hub_wall_lower_plain"), ("pipe_straight_1", "hub_pipe_straight"),
                        ("rover_1", "hub_rover"), ("locker_1", "hub_locker")):
        kit_piece(stage, model, kind)
    square(stage, f"/{PLACE}/Fixtures/bare")
    painted(stage, f"/{PLACE}/Fixtures/grey", surface(stage, f"/{PLACE}/Looks/grey"))
    clear = surface(stage, f"/{PLACE}/Looks/clear", opacity=(Sdf.ValueTypeNames.Float, 0.0))
    painted(stage, f"/{PLACE}/Sky/Haze", clear)
    coloured = surface(stage, f"/{PLACE}/Looks/red", diffuseColor=(Sdf.ValueTypeNames.Color3f, Gf.Vec3f(1, 0, 0)))
    proxy = painted(stage, f"/{PLACE}/Fixtures/stand_in", coloured)
    proxy.CreatePurposeAttr(UsdGeom.Tokens.proxy)
    square(stage, f"/{PLACE}/Fixtures/collision").CreatePurposeAttr(UsdGeom.Tokens.guide)
    square(stage, f"/{PLACE}/Places/other/bare")
    stage.GetRootLayer().Save()
    return path


def every_rule_catches_its_case():
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        record = folder / "pipeline_failures.json"  # the old record is retired (2026-10-21): this test names its own
        record.write_text(json.dumps({"kinds": {"hub_pipe_straight": {"failure": "a test's", "evidence": "", "on": ""}}}))
        placeholders.sorter.failures.__defaults__ = (record,)
        (folder / "kits").mkdir()
        (folder / "kits" / f"{PLACE}.json").write_text(json.dumps(KIT))
        found = {(fault["prim"].rsplit("/", 1)[-1], fault["rule"])
                 for fault in placeholders.check(test_stage(folder), kits=folder / "kits")}
    # A plain wall plate built in code fails too since #19: only a kind the pipeline-failure record names (the hub's
    # straight pipe) may be code-built.
    expected = {("door_leaf", "plain"), ("ship_body", "plain"), ("rover_1", "sorter"), ("wall_lower_plain_1", "sorter"),
                ("bare", "material"), ("grey", "material"), ("stand_in", "proxy")}
    problems = [f"{name} was not caught by the {rule} rule" for name, rule in sorted(expected - found)]
    problems += [f"{name} was caught by the {rule} rule, wrongly" for name, rule in sorted(found - expected)]
    return problems


def hangar_stage(folder, ship_made):
    """A stage with the hangar record's old ship: drawn by its code builders, or (ship_made) left out of the record with
    a made model standing in its place as a kit piece; its path."""
    entries = OLD_HANGAR_SHIP
    path = folder / "hangar.usda"
    stage = Usd.Stage.CreateNew(str(path))
    stage.SetDefaultPrim(UsdGeom.Xform.Define(stage, "/hangar").GetPrim())
    export.library_materials(stage, "hangar", "/hangar")
    library_surfaces(stage, "hangar", entries)
    scene.write(stage, "hangar", {"structure": [] if ship_made else entries}, folder)
    if ship_made:
        piece = UsdGeom.Xform.Define(stage, "/hangar/Objects/ship_1")
        piece.GetPrim().CreateAttribute("score:model", Sdf.ValueTypeNames.String).Set("ship_1")
        piece.GetPrim().CreateAttribute("score:kind", Sdf.ValueTypeNames.String).Set("hangar_ship")
        painted(stage, "/hangar/Objects/ship_1/geo", library_surface(stage, "/hangar/Library/hull_white_gloss"))
    stage.GetRootLayer().Save()
    return path


def hangar_ship_fails_until_made():
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        (folder / "kits").mkdir()
        (folder / "kits" / "hangar.json").write_text(json.dumps({"models": {"ship_1": {"route": "model"}}}))
        (folder / "built").mkdir()
        (folder / "made").mkdir()
        built = placeholders.check(hangar_stage(folder / "built", ship_made=False), kits=folder / "kits")
        made = placeholders.check(hangar_stage(folder / "made", ship_made=True), kits=folder / "kits")
    caught = {fault["prim"].rsplit("/", 1)[-1].rstrip("_0123456789") for fault in built if fault["rule"] == "plain"}
    problems = [f"the code-built {name} was not caught" for name in HANGAR_SHIP if name not in caught]
    problems += [f"{fault['prim']} was caught by the {fault['rule']} rule with a made ship" for fault in made]
    return problems


def todays_hangar_fails():
    if not HANGAR_STAGE.exists():
        print(f"todays_hangar_fails: skipped, no {HANGAR_STAGE} on this machine")
        return []
    stage = Usd.Stage.Open(str(HANGAR_STAGE))
    held = [name for name in HANGAR_SHIP if stage.GetPrimAtPath(f"/hangar/Structure/{name}").IsValid()]
    caught = {fault["prim"] for fault in placeholders.check(HANGAR_STAGE) if fault["rule"] == "plain"}
    return [f"/hangar/Structure/{name} on today's hangar stage was not caught" for name in held
            if f"/hangar/Structure/{name}" not in caught]


CHECKS = (every_rule_catches_its_case, hangar_ship_fails_until_made, todays_hangar_fails)


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[2] / "conftest.py"))["refuse_outside_sandbox"]()
    failures = [f"{check.__name__}: {problem}" for check in CHECKS for problem in check()]
    for failure in failures:
        print(failure)
    print("ok" if not failures else f"{len(failures)} failed")
    sys.exit(1 if failures else 0)
