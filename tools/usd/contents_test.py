"""Check the completion gate's contents checks (contents.py) both ways, on a place made here with its own world data:
each passes on a place that holds what it should and fails (or is unknown, which blocks) on one that does not.

Run: .venv/bin/python tools/usd/contents_test.py   (make tests runs it with the framework's environment)
"""
import json
import pathlib
import sys
import tempfile

from pxr import Gf, Sdf, Usd, UsdGeom, UsdLux

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import contents  # noqa: E402

PLACE = "testplace"
NONE = {name: None for name in contents.OUTPUTS}


def world_data(folder, place=PLACE, cast=None, needs=None, scene=None, sound=None):
    """A world's data folder holding only what the contents checks read of the place, and the bodies folder; both
    made the module's (contents.DATA, contents.BODIES)."""
    data = folder / "data"
    for kind in ("characters", "scene", "sound", "checks", "effects", "motion"):
        (data / kind).mkdir(parents=True, exist_ok=True)
    (data / "characters" / f"{place}.json").write_text(json.dumps(cast or {"place": place, "people": [],
                                                                             "note": "nobody works here"}))
    (data / "checks/contents.json").write_text(json.dumps({"places": {place: needs or {"effects": [], "motion": []}}}))
    (data / "scene" / f"{place}.json").write_text(json.dumps(scene or {"place": place, "lights": [], "places": []}))
    (data / "sound/places.json").write_text(json.dumps({"places": {place: sound or {"loops": ["hum"],
                                                                                     "from": "the creator's brief"}}}))
    (folder / "bodies").mkdir(exist_ok=True)
    contents.DATA, contents.BODIES = data, folder / "bodies"
    return data


def held_layers(stage_file, place=PLACE, room_tones=("hum",)):
    """The light and sound layers held by the stage's root, the sound layer with the place's room tones."""
    folder = pathlib.Path(stage_file).parent
    (folder / "layers").mkdir(exist_ok=True)
    Sdf.Layer.CreateNew(str(folder / "layers/light.usda")).Save()
    sound = Usd.Stage.CreateNew(str(folder / "layers/sound.usda"))
    for name in room_tones:
        sound.OverridePrim(f"/{place}/Sound/Room/{name}")
    sound.GetRootLayer().Save()
    root = Sdf.Layer.FindOrOpen(str(stage_file))
    root.subLayerPaths.insert(0, contents.SOUND_LAYER)
    root.subLayerPaths.insert(0, contents.LIGHT_LAYER)
    root.Save()


def bare_stage(folder, place=PLACE):
    """A stage of the place with nothing in it; its file."""
    path = folder / f"{place}.usda"
    stage = Usd.Stage.CreateNew(str(path))
    stage.SetDefaultPrim(UsdGeom.Xform.Define(stage, f"/{place}").GetPrim())
    stage.GetRootLayer().Save()
    return path


def judged(name, path, inventory=None, outputs=None, place=PLACE):
    return contents.JUDGES[name](Usd.Stage.Open(str(path)), place, inventory or {"rows": []}, outputs or NONE)[0]


def problems_of(cases):
    """Each case (what, got, wanted) that read otherwise."""
    return [f"{what}: {got}, not {wanted}" for what, got, wanted in cases if got != wanted]


def people_both_ways():
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        cast = {"place": PLACE, "people": [{"name": "bram", "character": "bram", "doing": "idle", "at": [0, 0, 0],
                                            "facing_to": [0, 0, 1], "why": "a test"}]}
        world_data(folder, cast=cast)
        path = bare_stage(folder)
        missing = judged("people", path)
        stage = Usd.Stage.Open(str(path))
        stage.DefinePrim(f"/{PLACE}/Characters/bram").SetCustomDataByKey("score:character", "bram")
        stage.GetRootLayer().Save()
        (folder / "bodies/bram.json").write_text(json.dumps({"drapes": {"work_drape": {"name": "Newton SolverVBD"}}}))
        draped = judged("people", path)
        (folder / "bodies/bram.json").write_text(json.dumps({"route": "prop"}))
        made = judged("people", path)
        layer = folder / "layer"
        layer.mkdir()
        (layer / "characters.json").write_text(json.dumps({"looks": {"bram": {"look": "bram_work",
                                                                              "missing": "no built model"}},
                                                           "licence": []}))
        unmade = judged("people", path, outputs={**NONE, "characters-layer": layer})
        (folder / "data/characters" / f"{PLACE}.json").unlink()
        return problems_of([("a cast person not on the stage", missing, contents.FAIL),
                            ("a body of SOMA's mesh in drapes", draped, contents.FAIL),
                            ("a made body", made, contents.PASS),
                            ("a characters layer with a look not made", unmade, contents.FAIL),
                            ("no cast", judged("people", path), contents.UNKNOWN)])


def effects_and_motion_both_ways():
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        data = world_data(folder, needs={"effects": ["steam"], "motion": ["door"]})
        path = bare_stage(folder)
        cases = [("an effect needed with no record", judged("effects", path), contents.FAIL),
                 ("a motion needed with no record", judged("motion", path), contents.FAIL)]
        (data / "effects" / f"{PLACE}.json").write_text(json.dumps({"effects": [{"name": "kettle_steam"}]}))
        (data / "motion" / f"{PLACE}.json").write_text(json.dumps({"motions": [{"name": "door",
                                                                                 "prim": f"/{PLACE}/door"}]}))
        stage = Usd.Stage.Open(str(path))
        door = UsdGeom.Xform.Define(stage, f"/{PLACE}/door")
        stage.GetRootLayer().Save()
        cases += [("a recorded effect not on the stage", judged("effects", path), contents.FAIL),
                  ("a recorded motion standing still", judged("motion", path), contents.FAIL)]
        UsdGeom.Xform.Define(stage, f"/{PLACE}/Effects/kettle_steam")
        translate = door.AddTranslateOp()
        translate.Set(Gf.Vec3d(0, 0, 0), 0)
        translate.Set(Gf.Vec3d(1, 0, 0), 24)
        stage.GetRootLayer().Save()
        cases += [("the effect standing", judged("effects", path), contents.PASS),
                  ("the motion moving", judged("motion", path), contents.PASS),
                  ("a place the expectations do not list", judged("effects", path, place="elsewhere"),
                   contents.UNKNOWN)]
        return problems_of(cases)


def crops_both_ways():
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        world_data(folder, needs={"crops": {"planted_share": 1.0}})
        path = bare_stage(folder)
        stage = Usd.Stage.Open(str(path))
        for number, x in enumerate((0.0, 3.0)):
            tile = UsdGeom.Mesh.Define(stage, f"/{PLACE}/bed_{number}")
            tile.CreatePointsAttr([(x - 0.5, 0, -0.5), (x + 0.5, 0, -0.5), (x + 0.5, 0, 0.5), (x - 0.5, 0, 0.5)])
            tile.CreateFaceVertexCountsAttr([4])
            tile.CreateFaceVertexIndicesAttr([0, 1, 2, 3])
            tile.GetPrim().CreateAttribute("score:plain", Sdf.ValueTypeNames.String).Set("soil")
        plants = UsdGeom.PointInstancer.Define(stage, f"/{PLACE}/Crops/lettuce")
        plants.CreatePositionsAttr([(0.1, 0, 0.1)])
        stage.GetRootLayer().Save()
        half = judged("crops", path)
        plants.CreatePositionsAttr([(0.1, 0, 0.1), (2.9, 0, -0.2)])
        stage.GetRootLayer().Save()
        return problems_of([("one of two beds planted", half, contents.FAIL),
                            ("both beds planted", judged("crops", path), contents.PASS)])


def likeness_and_paint_both_ways():
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        world_data(folder)
        path = bare_stage(folder)
        stage = Usd.Stage.Open(str(path))
        chair = stage.DefinePrim(f"/{PLACE}/Objects/chair_1")
        chair.CreateAttribute("score:row", Sdf.ValueTypeNames.String).Set("chair")
        chair.CreateAttribute("score:model", Sdf.ValueTypeNames.String).Set("chair-b")
        stage.GetRootLayer().Save()
        inventory = {"rows": [{"id": "chair", "kind": "generate"}]}
        likeness, check = folder / "likeness", folder / "check"
        likeness.mkdir()
        check.mkdir()
        (likeness / "likeness.json").write_text(json.dumps({"objects": {"lamp": {}}}))
        cases = [("a generated model with no likeness output", judged("likeness", path, inventory), contents.UNKNOWN),
                 ("a likeness output without the row", judged("likeness", path, inventory,
                                                              {**NONE, "likeness": likeness}), contents.FAIL),
                 ("an unrepainted generated model", judged("painted", path, inventory,
                                                           {**NONE, "surfaces-check": check}), contents.FAIL)]
        (likeness / "likeness.json").write_text(json.dumps({"objects": {"chair": {}}}))
        chair.CreateAttribute("score:repaint_of", Sdf.ValueTypeNames.String).Set("seed hash")
        stage.GetRootLayer().Save()
        cases += [("the row held to its close-up", judged("likeness", path, inventory,
                                                          {**NONE, "likeness": likeness}), contents.PASS),
                  ("repainted with no surfaces-check", judged("painted", path, inventory), contents.UNKNOWN),
                  ("repainted and checked", judged("painted", path, inventory, {**NONE, "surfaces-check": check}),
                   contents.PASS),
                  ("a code row's model", judged("painted", path, {"rows": [{"id": "chair", "kind": "code"}]}),
                   contents.PASS)]
        return problems_of(cases)


def light_sound_neighbours_and_game_both_ways():
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        scene = {"place": PLACE, "lights": [{"type": "omni", "from": "the game 2099's module_shell.gd:203"}],
                 "places": [{"name": "next_door", "stage": "other"}]}
        data = world_data(folder, scene=scene)
        path = bare_stage(folder)
        stage = Usd.Stage.Open(str(path))
        stage.DefinePrim(f"/{PLACE}/Places/next_door").GetReferences().AddReference("./other/other.usda")
        stage.GetRootLayer().Save()
        cases = [("no light layer", judged("light", path), contents.FAIL),
                 ("no sound layer", judged("sound", path), contents.FAIL),
                 ("a shown place resolving to nothing", judged("neighbours", path), contents.FAIL),
                 ("a lamp from the game", judged("game", path), contents.FAIL)]
        held_layers(path)
        UsdLux.SphereLight.Define(stage, f"/{PLACE}/Lights/lamp_0")
        stage.GetRootLayer().Save()
        (folder / "other").mkdir()
        other = bare_stage(folder / "other", "other")
        shown = Usd.Stage.Open(str(other))
        shown.DefinePrim("/other/thing")
        shown.GetRootLayer().Save()
        scene["lights"][0]["from"] = "the light stage's sweep against concept K04"
        (data / "scene" / f"{PLACE}.json").write_text(json.dumps(scene))
        cases += [("the light layer and the lamp", judged("light", path), contents.PASS),
                  ("the sound layer and its room tone", judged("sound", path), contents.PASS),
                  ("the shown place standing", judged("neighbours", path), contents.PASS),
                  ("no record citing the game", judged("game", path), contents.PASS)]
        return problems_of(cases)


def a_part_is_judged_on_its_host():
    """A door's leaves (gdoor, hdoor) have no cast, lamps, room tones or shown places of their own: listed as a part,
    those pass as judged on the host's stage; unlisted, they stay unknown."""
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        data = world_data(folder, needs={"part_of": "host", "effects": [], "motion": []})
        for kind in ("characters", "scene"):
            (data / kind / f"{PLACE}.json").unlink()
        (data / "sound/places.json").write_text(json.dumps({"places": {}}))
        path = bare_stage(folder)
        cases = [(f"{name} of a part", judged(name, path), contents.PASS)
                 for name in ("people", "light", "sound", "neighbours", "effects", "motion")]
        (data / "checks/contents.json").write_text(json.dumps({"places": {PLACE: {"effects": [], "motion": []}}}))
        cases += [(f"{name} of a place with no records", judged(name, path), contents.UNKNOWN)
                  for name in ("people", "light", "sound", "neighbours")]
        return problems_of(cases)


TESTS = (people_both_ways, a_part_is_judged_on_its_host, effects_and_motion_both_ways, crops_both_ways, likeness_and_paint_both_ways,
         light_sound_neighbours_and_game_both_ways)

if __name__ == "__main__":
    data, bodies = contents.DATA, contents.BODIES
    failed = []
    for test in TESTS:
        found = test()
        contents.DATA, contents.BODIES = data, bodies
        print(("FAIL " if found else "ok   ") + test.__name__ + "".join(f"\n  {problem}" for problem in found))
        failed += found
    sys.exit(1 if failed else 0)
