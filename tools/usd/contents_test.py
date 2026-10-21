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
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
import contents  # noqa: E402

PLACE = "testplace"
NONE = {name: None for name in contents.OUTPUTS}
# Row-kind rules written here (data/checks/row-kinds.json's shape), so the checks do not follow the house's table.
RULES = {"kettle": {"nouns": ["kettle"], "does": ["emits"]}, "door": {"nouns": ["door"], "does": ["moves"]},
         "plant": {"nouns": ["plants", "planter"], "does": ["grows"]},
         "person": {"nouns": ["person", "crowd"], "does": ["acts"]}}
NOBODY = {"concept": "c0ffee00", "spots": [], "middle": [0.0, 0.0, 0.0], "rows": {}}


def world_data(folder, place=PLACE, people=NOBODY, design=(), scene=None):
    """A world's data folder holding only what the contents checks read of the place (its people's mapping, `people`,
    None for none), the place's design (its scene inventory's rows, `design`) and the bodies folder; all made the
    module's (contents.DATA, contents.DESIGN, contents.BODIES). Its plan and setting give the place a room's bed in a
    base on the Moon (score/stages/sound/beds.py over the environment's library briefs and reference bodies)."""
    data = folder / "data"
    for kind in ("people", "scene", "sound", "checks", "physics", "places"):
        (data / kind).mkdir(parents=True, exist_ok=True)
    for name in ("sound/sounds.json", "physics/bodies.json"):
        (data / name).write_text((REPO / "data" / name).read_text())
    plans = folder / "design" / "plans"  # the design's kept plan (the old data/plans were retired, 2026-10-21)
    plans.mkdir(parents=True, exist_ok=True)
    (plans / f"{place}.json").write_text(json.dumps({"inside": True}))
    (data / "physics/setting.json").write_text(json.dumps({"bodies": [{"body": "moon", "reference": "moon"}],
                                                            "plots": [], "sites": [{"place": place, "on": "moon"}]}))
    (data / "places/within.json").write_text(json.dumps({}))
    (data / "people/rows.json").write_text(json.dumps({"places": {place: people} if people else {}, "new": {}}))
    (data / "checks/row-kinds.json").write_text(json.dumps({"kinds": RULES}))
    (folder / "design" / "inventory").mkdir(parents=True, exist_ok=True)
    (folder / "design" / "inventory" / f"{place}.json").write_text(json.dumps({"place": place, "rows": list(design)}))
    contents.DESIGN = folder / "design" / "inventory"  # as the module's: <home>/design/inventory
    (data / "scene" / f"{place}.json").write_text(json.dumps(scene or {"place": place, "lights": [], "places": []}))
    (folder / "bodies").mkdir(exist_ok=True)
    contents.DATA, contents.BODIES = data, folder / "bodies"
    return data


def held_layers(stage_file, place=PLACE, room_tones=("habitat", "base_hum")):
    """The light and sound layers held by the stage's root, the sound layer with the place's bed."""
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


def people_mapped(rows, place=PLACE):
    """The place's design's people rows (`rows`, each mapped to its looks) written where the people check reads them
    (contents.DATA's people/rows.json), each a person row of its design too (contents.DESIGN)."""
    entry = {**NOBODY, "spots": [[0.0, 0.0, 0.0]], "rows": rows}
    (contents.DATA / "people/rows.json").write_text(json.dumps({"places": {place: entry}, "new": {}}))
    kept = contents.DESIGN / f"{place}.json"
    design = json.loads(kept.read_text())
    shown = {found["id"] for found in design["rows"]}
    design["rows"] += [row(row_id, "person") for row_id in rows if row_id not in shown]
    kept.write_text(json.dumps(design))


BRAM = {"bram": {"name": "bram", "noun": "person", "count": 1, "where": "by the door", "looks": ["bram-work"]}}


def row(row_id, noun, anchor="floor"):
    return {"id": row_id, "name": noun, "noun": noun, "kind": "generate", "count": 1, "anchor": anchor}


def people_both_ways():
    """The cast is the design's people row mapped to its look (data/people/rows.json): bram must stand there. A design
    that shows nobody wants nobody, mapped or not; one that shows somebody nobody mapped is unknown, as is no design."""
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        world_data(folder, design=[row("bram", "person")])
        people_mapped(BRAM)
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
        world_data(folder, people=None)
        stranger = judged("people", path)
        stage.RemovePrim(f"/{PLACE}/Characters/bram")
        stage.GetRootLayer().Save()
        world_data(folder)
        nobody = judged("people", path)
        world_data(folder, people=None)
        unmapped_nobody = judged("people", path)
        world_data(folder, design=[row("bram", "person")])
        mapped_none = judged("people", path)
        world_data(folder, people=None, design=[row("bram", "person")])
        unmapped = judged("people", path)
        (contents.DESIGN / f"{PLACE}.json").unlink()
        undesigned = judged("people", path)
        return problems_of([("a cast person not on the stage", missing, contents.FAIL),
                            ("a body of SOMA's mesh in drapes", draped, contents.FAIL),
                            ("a made body", made, contents.PASS),
                            ("a characters layer with a look not made", unmade, contents.FAIL),
                            ("a design with nobody, somebody on the stage", stranger, contents.FAIL),
                            ("a design with nobody, nobody on the stage", nobody, contents.PASS),
                            ("a design with nobody, no people mapped", unmapped_nobody, contents.PASS),
                            ("a design with a person, its mapping of nobody", mapped_none, contents.UNKNOWN),
                            ("a design with a person, no people mapped", unmapped, contents.UNKNOWN),
                            ("no design", undesigned, contents.UNKNOWN)])


def effects_and_motion_both_ways():
    """The design's emitting row met only by an effect standing on its object; its moving row only by the accepted
    motion output's moves moving on the stage, or written down as still with why."""
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        world_data(folder, design=[row("kettle", "kettle"), row("door", "door")])
        path = bare_stage(folder)
        motion = folder / "motion"
        motion.mkdir()
        made = {**NONE, "motion": motion}

        def moves(record):
            (motion / "moves.json").write_text(json.dumps(record))
            return judged("motion", path, outputs=made)
        cases = [("an effect needed with none standing", judged("effects", path), contents.FAIL),
                 ("a motion needed with no motion output", judged("motion", path), contents.UNKNOWN),
                 ("a still entry with no reason", moves({"moves": [], "still": {f"/{PLACE}/door_1": " "}}),
                  contents.FAIL),
                 ("a need written down as still, with why", moves({"moves": [], "still": {f"/{PLACE}/door_1": "parked"}}),
                  contents.PASS)]
        stage = Usd.Stage.Open(str(path))
        door = UsdGeom.Xform.Define(stage, f"/{PLACE}/door_1")
        stage.GetRootLayer().Save()
        cases.append(("a move standing still on the stage",
                      moves({"moves": [{"name": "door_1", "prim": f"/{PLACE}/door_1"}]}), contents.FAIL))
        translate = door.AddTranslateOp()
        translate.Set(Gf.Vec3d(0, 0, 0), 0)
        translate.Set(Gf.Vec3d(1, 0, 0), 24)
        UsdGeom.Xform.Define(stage, f"/{PLACE}/Effects/kettle_steam")
        stage.GetRootLayer().Save()
        cases += [("the effect standing", judged("effects", path), contents.PASS),
                  ("the motion moving", judged("motion", path, outputs=made), contents.PASS),
                  ("a place with no design", judged("effects", path, place="elsewhere"), contents.UNKNOWN),
                  ("a place with no design", judged("motion", path, place="elsewhere"), contents.UNKNOWN)]
        stage.RemovePrim(f"/{PLACE}/Effects/kettle_steam")
        steam = stage.DefinePrim(f"/{PLACE}/Objects/kettle_1/jet")
        steam.CreateAttribute(contents.EFFECT_KIND, Sdf.ValueTypeNames.String).Set("steam_jet")
        stage.GetRootLayer().Save()
        cases.append(("an emitter laid on the row's object", judged("effects", path), contents.PASS))
        return problems_of(cases)


def crops_both_ways():
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        world_data(folder, design=[row("planter", "planter"), row("greens", "plants", anchor="on:planter")])
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
        both = judged("crops", path)
        plants.CreatePositionsAttr([])
        stage.GetRootLayer().Save()
        world_data(folder, design=[row("fern", "plants")])  # a plant on the floor, no bed: no crops here
        return problems_of([("one of two beds planted", half, contents.FAIL),
                            ("both beds planted", both, contents.PASS),
                            ("a design with no crops", judged("crops", path), contents.PASS),
                            ("a place with no design", judged("crops", path, place="elsewhere"), contents.UNKNOWN)])


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
        # a model an old kit built in code went with the old kits (data/kit, 2026-10-21): every generated model is
        # held to the bake's paint
        chair.CreateAttribute("score:motion_model", Sdf.ValueTypeNames.String).Set("chair-s1")
        stage.GetRootLayer().Save()
        cases.append(("a model the motion models layer lays from its take's bake", judged(
            "painted", path, inventory, {**NONE, "surfaces-check": check}), contents.PASS))
        chair.RemoveProperty("score:motion_model")
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
                  # #19: a row's own kind routes nothing; a `code` row is the loop's
                  ("a code row's model", judged("painted", path, {"rows": [{"id": "chair",
                                                                                           "kind": "code"}]}),
                   contents.UNKNOWN)]
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
                  ("the sound layer and its bed", judged("sound", path), contents.PASS),
                  ("the shown place standing", judged("neighbours", path), contents.PASS),
                  ("no record citing the game", judged("game", path), contents.PASS)]
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
        palette = [["skin_light", "wool_grey", "leather_black"]]  # surfaces of the people line's library
        # the old library's surfaces are retired (2026-10-21) and the people line's are not made yet: the crowd's
        # colours are stood in, as this check judges where people stand, not what they wear
        rows_module = contents.stages_module("people_rows")
        rows_module.palette_colours = lambda palettes: [[(0.5, 0.5, 0.5)] * len(one) for one in palettes]
        people = {**NOBODY, "spots": [[0.0, 0.0, 0.0]], "rows": {
            "guard": {"name": "guard", "looks": ["guard-uniform"], "share": 0.05},
            "bram": {"name": "bram", "looks": ["bram-work"], "share": 0.3},
            "crowd": {"name": "crowd", "noun": "crowd", "crowd": "kit_m_avg-coat-grey", "palettes": palette}}}
        view = {"name": "gate", "eye": [0.0, 1.6, 0.0], "aim": [0.0, 1.6, 10.0], "fov": 60}
        world_data(folder, people=people, scene={"place": PLACE, "lights": [], "places": [], "views": [view]},
                   design=[row("guard", "person"), row("bram", "person"), row("crowd", "crowd")])
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


def the_bed_from_the_design_both_ways():
    """The sound check asks for the bed the place's design gives, so a stage with another room's tone fails, and a
    place its design leaves undecided (no site holds it) is unknown."""
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        data = world_data(folder)
        path = bare_stage(folder)
        held_layers(path, room_tones=("habitat",))
        cases = [("the bed's hum missing", judged("sound", path), contents.FAIL)]
        sound = Usd.Stage.Open(str(folder / "layers/sound.usda"))
        sound.OverridePrim(f"/{PLACE}/Sound/Room/base_hum")
        sound.GetRootLayer().Save()
        cases += [("the whole bed", judged("sound", path), contents.PASS)]
        (data / "physics/setting.json").write_text(json.dumps({"bodies": [], "plots": [], "sites": []}))
        cases += [("no site holding the place", judged("sound", path), contents.UNKNOWN)]
        return problems_of(cases)


TESTS = (people_both_ways, effects_and_motion_both_ways, crops_both_ways, likeness_and_paint_both_ways,
         light_sound_neighbours_and_game_both_ways, the_assembled_record_and_a_waiting_entry_both_ways,
         a_far_look_near_a_view_both_ways, the_bed_from_the_design_both_ways)

if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[2] / "conftest.py"))["refuse_outside_sandbox"]()
    data, design, bodies = contents.DATA, contents.DESIGN, contents.BODIES
    failed = []
    for test in TESTS:
        found = test()
        contents.DATA, contents.DESIGN, contents.BODIES = data, design, bodies
        print(("FAIL " if found else "ok   ") + test.__name__ + "".join(f"\n  {problem}" for problem in found))
        failed += found
    sys.exit(1 if failed else 0)
