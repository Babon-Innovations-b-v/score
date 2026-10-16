"""Check the completion gate's contents checks (contents.py) both ways, on a place made here with its own world data:
each passes on a place that holds what it should and fails (or is unknown, which blocks) on one that does not.

Run: .venv/bin/python tools/usd/contents_test.py   (make tests runs it with the framework's environment)
"""
import json
import os
import pathlib
import sys
import tempfile

# Scratch on disk under $PROPS_HOME/tmp, never /tmp (a RAM-backed tmpfs on the PC).
tempfile.tempdir = str(pathlib.Path(os.environ.get("PROPS_HOME", pathlib.Path.home() / ".farm-factory-props")) / "tmp")
pathlib.Path(tempfile.tempdir).mkdir(parents=True, exist_ok=True)

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
    (data / "people").mkdir(exist_ok=True)
    (data / "people/bodies.json").write_text(json.dumps({"full": ["bram-work"]}))
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
        (data / "movers").mkdir()
        (data / "movers" / f"{PLACE}.json").write_text(json.dumps({"movers": [], "still": {"door": " "}}))
        cases.append(("a still entry with no reason", judged("motion", path), contents.FAIL))
        (data / "movers" / f"{PLACE}.json").write_text(json.dumps({"movers": [], "still": {"door": "parked"}}))
        cases.append(("a need written down as still, with why", judged("motion", path), contents.PASS))
        (data / "motion" / f"{PLACE}.json").write_text(json.dumps({"motions": [{"name": "door",
                                                                                 "prim": f"/{PLACE}/game_door"}]}))
        (data / "movers" / f"{PLACE}.json").write_text(json.dumps({"movers": [], "renamed": {
            f"/{PLACE}/game_door": f"/{PLACE}/door_leaf_1"}}))
        stage = Usd.Stage.Open(str(path))
        leaf = UsdGeom.Xform.Define(stage, f"/{PLACE}/door_leaf_1").AddTranslateOp()
        leaf.Set(Gf.Vec3d(0, 0, 0), 0)
        leaf.Set(Gf.Vec3d(1, 0, 0), 24)
        stage.GetRootLayer().Save()
        cases.append(("a game motion's prim moving under the name the movers record renames it to",
                      judged("motion", path), contents.PASS))
        (data / "movers" / f"{PLACE}.json").write_text(json.dumps({"movers": []}))
        cases.append(("the same motion without the rename", judged("motion", path), contents.FAIL))
        stage.RemovePrim(f"/{PLACE}/door_leaf_1")
        stage.GetRootLayer().Save()
        (data / "movers" / f"{PLACE}.json").unlink()
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
        stage.RemovePrim(f"/{PLACE}/Effects/kettle_steam")
        UsdGeom.Xform.Define(stage, f"/{PLACE}/Effects/kettle_steam_0_1")
        stage.GetRootLayer().Save()
        cases.append(("the effect standing as its cells", judged("effects", path), contents.PASS))
        stage.RemovePrim(f"/{PLACE}/Effects/kettle_steam_0_1")
        UsdGeom.Xform.Define(stage, f"/{PLACE}/Effects/kettle_steam_big")
        stage.GetRootLayer().Save()
        cases.append(("only another entry's name beginning with it", judged("effects", path), contents.FAIL))
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
        kit = folder / "data/kit" / f"{PLACE}.json"
        kit.parent.mkdir()
        kit.write_text(json.dumps({"models": {"chair-b": {"route": "code"}}}))
        cases.append(("a generated row's model the kit builds in code", judged("painted", path, inventory,
                                                                             {**NONE, "surfaces-check": check}),
                      contents.PASS))
        chair.GetAttribute("score:model").Set("models/testplace_kit/chair-b.gltf")
        stage.GetRootLayer().Save()
        cases.append(("the kit's code-built model laid as its file", judged("painted", path, inventory,
                                                                          {**NONE, "surfaces-check": check}),
                      contents.PASS))
        kit.unlink()
        cases.append(("that file with no code route in the kit", judged("painted", path, inventory,
                                                                       {**NONE, "surfaces-check": check}),
                      contents.FAIL))
        chair.GetAttribute("score:model").Set("chair-b")
        chair.CreateAttribute("score:machine", Sdf.ValueTypeNames.String).Set("chair-s1")
        stage.GetRootLayer().Save()
        cases.append(("a machine the machines layer lays from its take's bake", judged(
            "painted", path, inventory, {**NONE, "surfaces-check": check}), contents.PASS))
        chair.RemoveProperty("score:machine")
        stage.GetRootLayer().Save()
        chair.CreateAttribute("score:from", Sdf.ValueTypeNames.String).Set(
            f"plan item{contents.LAID_FROM_BAKE}chair")
        stage.GetRootLayer().Save()
        cases.append(("a waiting entry laid from the bake", judged("painted", path, inventory,
                                                                 {**NONE, "surfaces-check": check}), contents.PASS))
        chair.RemoveProperty("score:from")
        stage.GetRootLayer().Save()
        origin = path.parent / contents.ASSEMBLY_ORIGIN
        origin.write_text(json.dumps({"made pieces": {"chair": "chair-b"}}))
        cases.append(("a ship place's made piece laid from the bake", judged("painted", path, inventory,
                                                                           {**NONE, "surfaces-check": check}),
                      contents.PASS))
        owner = folder / "owner"
        owner.mkdir()
        (owner / "likeness.json").write_text(json.dumps({"objects": {"chair": {}}}))
        cases.append(("a made piece held by its painting place's likeness", judged(
            "likeness", path, inventory, {**NONE, "likeness": likeness, "likeness@owner": owner}), contents.PASS))
        origin.unlink()
        cases.append(("a painting place's likeness for a row not laid from its bake", judged(
            "likeness", path, inventory, {**NONE, "likeness": likeness, "likeness@owner": owner}), contents.FAIL))
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


def the_assembled_record_and_a_waiting_entry_both_ways():
    """Light and neighbours judge the record beside the stage (the assembly's scene.json) over data/scene's; game
    judges every scene record (beside, data/scene's, the stored scene-record output's), a `source` as a `from`, and
    counts the positions taken; an entry the assembly laid nothing for, waiting on its model, fails `waiting` by
    name."""
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        lamp = {"type": "omni", "from": "the game 2099's lamp.gd"}
        data = world_data(folder, scene={"place": PLACE, "lights": [lamp], "places": []})
        path = bare_stage(folder)
        cases = [("data/scene's record, none beside", judged("neighbours", path), contents.PASS),
                 ("data/scene's record citing the game, none beside", judged("game", path), contents.FAIL),
                 ("nothing waiting", judged("waiting", path), contents.PASS)]
        (path.parent / contents.ASSEMBLED_SCENE).write_text(json.dumps(
            {"lights": [], "places": [{"name": "next_door", "stage": "other"}]}))
        stage = Usd.Stage.Open(str(path))
        stage.GetPrimAtPath(f"/{PLACE}").CreateAttribute(contents.WAITING, Sdf.ValueTypeNames.StringArray).Set(
            ["objects cairn: its model comes through the next batch"])
        stage.GetRootLayer().Save()
        cases += [("the assembled record's shown place missing", judged("neighbours", path), contents.FAIL),
                  ("the assembled record free of the game, data/scene's citing it", judged("game", path),
                   contents.FAIL),
                  ("the cairn waiting on its model", judged("waiting", path), contents.FAIL)]
        (data / "scene" / f"{PLACE}.json").write_text(json.dumps({"place": PLACE, "lights": [], "places": []}))
        cases.append(("every scene record free of the game", judged("game", path), contents.PASS))
        made = folder / "scene-record-output"
        (made / "record").mkdir(parents=True)
        (made / "record" / f"{PLACE}.json").write_text(json.dumps({"objects": [
            {"name": "rocket", "at": [-270, 0, -60], "source": "earth_site.gd:260 ROCKET_AT"},
            {"name": "pad", "at": [0, 0, 0], "from": "the plan's pad"}]}))
        stored = {**NONE, "scene-record": made}
        verdict, faults, _ = contents.JUDGES["game"](Usd.Stage.Open(str(path)), PLACE, {"rows": []}, stored)
        cases.append(("the stored scene-record output placing the rocket from the game", verdict, contents.FAIL))
        if not (len(faults) == 1 and "1 entries take their numbers from the game (source), 1 positions" in faults[0]):
            cases.append(("the stored output's fault counts", faults, "one source, one position"))
        return problems_of(cases)


def a_far_look_near_a_view_both_ways():
    """A far-only look (not made in full: the guard; the crowd's far body) filling over a tenth of a view's frame
    height fails people by name, view and share; the full-body crew member as near passes; the far ones stood back
    pass."""
    from pxr import Vt
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        cast = {"place": PLACE, "people": [{"name": "guard", "character": "guard"}, {"name": "bram", "character": "bram",
                                                                                   "look": "bram_work"}],
                "crowd": {"name": "crowd", "character": "kit_m_avg", "count": 2}}
        view = {"name": "gate", "eye": [0.0, 1.6, 0.0], "aim": [0.0, 1.6, 10.0], "fov": 60}
        world_data(folder, cast=cast, scene={"place": PLACE, "lights": [], "places": [], "views": [view]})
        path = bare_stage(folder)
        stage = Usd.Stage.Open(str(path))
        for name, depth in (("guard", 3.0), ("bram", 3.0)):
            person = UsdGeom.Xform.Define(stage, f"/{PLACE}/Characters/{name}")
            person.AddTranslateOp().Set(Gf.Vec3d(0.0, 0.0, depth))
            person.GetPrim().SetCustomDataByKey("score:character", name)
            (folder / f"bodies/{name}.json").write_text(json.dumps({"route": "prop"}))
        crowd = UsdGeom.PointInstancer.Define(stage, f"/{PLACE}/Characters/crowd")
        crowd.CreatePositionsAttr(Vt.Vec3fArray([Gf.Vec3f(0.0, 0.0, 4.0), Gf.Vec3f(0.0, 0.0, 80.0)]))
        crowd.GetPrim().SetCustomDataByKey("score:character", "kit_m_avg")
        (folder / "bodies/kit_m_avg.json").write_text(json.dumps({"route": "prop"}))
        stage.GetRootLayer().Save()
        near = contents.JUDGES["people"](Usd.Stage.Open(str(path)), PLACE, {"rows": []}, NONE)
        UsdGeom.Xformable(stage.GetPrimAtPath(f"/{PLACE}/Characters/guard")).GetOrderedXformOps()[0].Set(
            Gf.Vec3d(0.0, 0.0, 40.0))
        crowd.GetPositionsAttr().Set(Vt.Vec3fArray([Gf.Vec3f(0.0, 0.0, 40.0), Gf.Vec3f(0.0, 0.0, 80.0)]))
        stage.GetRootLayer().Save()
        named = [fault for fault in near[1] if "far-only" in fault]
        problems = [] if len(named) == 2 and named[0].startswith("guard: ") and "view gate" in named[0] and \
            named[1].startswith("crowd: ") and "1 of 2" in named[1] else [f"the near far-only faults: {near[1]}"]
        return problems + problems_of([("a far guard and crowd near the view", near[0], contents.FAIL),
                                       ("both stood back", judged("people", path), contents.PASS)])


TESTS = (people_both_ways, a_part_is_judged_on_its_host, effects_and_motion_both_ways, crops_both_ways, likeness_and_paint_both_ways,
         light_sound_neighbours_and_game_both_ways, the_assembled_record_and_a_waiting_entry_both_ways,
         a_far_look_near_a_view_both_ways)

if __name__ == "__main__":
    data, bodies = contents.DATA, contents.BODIES
    failed = []
    for test in TESTS:
        found = test()
        contents.DATA, contents.BODIES = data, bodies
        print(("FAIL " if found else "ok   ") + test.__name__ + "".join(f"\n  {problem}" for problem in found))
        failed += found
    sys.exit(1 if failed else 0)
