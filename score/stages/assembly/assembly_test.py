"""The resting gate reads the world files the assembly stage declares, never the repository's own: a changed rules
file, kit or inventory in the world's data changes its verdict, and a seed naming no inventory there is unknown.
No spend: a one-piece place made here, a drop run in which nothing moved.

Run: .venv/bin/python score/stages/assembly/assembly_test.py
"""
import json
import os
import pathlib
import shutil
import sys
import tempfile

# Scratch on disk under $PROPS_HOME/tmp, never /tmp (a RAM-backed tmpfs on the PC).
tempfile.tempdir = str(pathlib.Path(os.environ.get("PROPS_HOME", pathlib.Path.home() / ".farm-factory-props")) / "tmp")
pathlib.Path(tempfile.tempdir).mkdir(parents=True, exist_ok=True)

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tools/usd"))

from score import checks  # noqa: E402
from score.stages import assembly  # noqa: E402
from score.stages.assembly import made_waiting, record, sounds  # noqa: E402
import triage_test  # noqa: E402

STILL = {"objects": {}}


def a_seed(root):
    """A place holding one floor plate sunk 40 cm (a kit piece's false alarm under the repository's rules), as the
    stage's output, its inputs record naming the world's inventory."""
    (root / "made").mkdir()
    stage = triage_test.place_of(root / "made", [("plate", "box", (6, -0.4, 0))],
                                 [triage_test.row("plate", group="kit: floor")])
    output = root / "output"
    shutil.copytree(stage.parent, output)
    record = json.loads((output / "inputs.json").read_text())
    (output / "inputs.json").write_text(json.dumps({**record, "inventory": f"data/inventory/{stage.stem}.json"}))
    return output, stage.stem


def world_data(root, place, fixed_in_kit):
    """The world's data the stage declares: rules, kit and inventory, with the rules' kit groups as given."""
    data = root / "data"
    for part in ("checks", "kit", "inventory"):
        (data / part).mkdir(parents=True)
    rules = json.loads((REPO / "data/checks/resting.json").read_text())
    (data / "checks/resting.json").write_text(json.dumps({**rules, "fixed_in_kit": fixed_in_kit}))
    (data / "kit" / f"{place}.json").write_text(json.dumps({"kinds": {}}))
    (data / "inventory" / f"{place}.json").write_text(json.dumps(
        {"rows": [triage_test.row("plate", group="kit: floor")]}))
    return {"resting rules": data / "checks/resting.json", "kit": data / "kit" / f"{place}.json",
            "inventories": data / "inventory"}


def resting(output, inputs):
    evidence = output.parent / "settled.json"
    evidence.write_text(json.dumps(STILL))
    return assembly.judge_resting(output, inputs, evidence)


def test_the_resting_gate_reads_the_declared_world_files():
    """Fault (review of step 0, 2026-10-11): the judge read the repository's resting.json, kit and inventory, so a
    world whose data was elsewhere was judged on files its key did not cover."""
    root = pathlib.Path(tempfile.mkdtemp())
    try:
        output, place = a_seed(root)
        kit_floor = world_data(root / "kept", place, ["kit: floor"])
        assert resting(output, kit_floor).answer == checks.PASS
        no_kit_groups = world_data(root / "changed", place, [])
        verdict = resting(output, no_kit_groups)
        assert verdict.answer == checks.FAIL and "plate" in " ".join(verdict.findings), verdict
        record = json.loads((output / "inputs.json").read_text())
        (output / "inputs.json").chmod(0o644)
        (output / "inputs.json").write_text(json.dumps({**record, "inventory": "/elsewhere/rows.json"}))
        assert resting(output, kit_floor).answer == checks.UNKNOWN
    finally:
        shutil.rmtree(root)


def test_a_baked_model_s_objects_carry_its_hash_and_keep_the_owner_s_pick():
    """Both ways: after the assembly takes a bake, the object carries the baked file's hash (not the seed's, the
    greenhouse's water tank until 2026-10-12) and its pick still holds through `repaint_of`; the same hash written
    without the seed's beside it breaks the pick."""
    import complete
    import picks
    import resting_test
    from pxr import Sdf, Usd
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        resting_test.made_models(folder)
        seed_hash = complete.model_hash(folder / "models/box.gltf")
        pick = {"model": "box", "sha256": seed_hash, "decided": "owner, 2026-10-09: this take"}
        stage = triage_test.place_of(folder, [("crate", "box", (0, 0, 0))], [triage_test.row("crate", pick=pick)])
        inventory = json.loads((folder / "inventory.json").read_text())
        baked = folder / "models/plank.gltf"  # stands for the bake of the box: another file, another hash
        assembly.stamp_baked_hash(stage.parent / assembly.BASE_LAYER, "box", baked)
        opened = Usd.Stage.Open(str(stage))  # held: a prim of a stage nothing holds expires at once
        prim = opened.GetPrimAtPath(f"/{triage_test.PLACE}/Objects/crate_1")
        assert prim.GetAttribute("score:model_sha256").Get() == complete.model_hash(baked)
        assert prim.GetAttribute("score:repaint_of").Get() == seed_hash
        assert picks.check(stage, inventory) == ([], 1)
        layer = Sdf.Layer.FindOrOpen(str(stage.parent / assembly.BASE_LAYER))
        spec = layer.GetPrimAtPath(f"/{triage_test.PLACE}/Objects/crate_1")
        spec.RemoveProperty(spec.attributes["score:repaint_of"])
        layer.Save()
        found, _ = picks.check(stage, inventory)
        assert len(found) == 1 and "not the owner's pick" in found[0]["why"], found


def a_cube_asset(path, size):
    """An asset holding one cube `size` metres a side, its default prim named after the file."""
    from pxr import Usd, UsdGeom
    stage = Usd.Stage.CreateNew(str(path))
    root = UsdGeom.Xform.Define(stage, f"/{path.stem}")
    UsdGeom.Cube.Define(stage, f"/{path.stem}/cube").GetSizeAttr().Set(size)
    stage.SetDefaultPrim(root.GetPrim())
    stage.GetRootLayer().Save()


def test_a_fixture_laid_from_a_released_file_takes_the_bake_of_its_model():
    """Fault (complete@launch, 2026-10-15): the rocket, a plan object laid from the released
    models/launch_rocket_solid/far_rocket_1.gltf, kept the seed's paint, as the bake's far_rocket_1 was matched only
    by name. It now references the baked asset, named by its model; a bake that moved the frame fails."""
    from pxr import Sdf, Usd, UsdGeom
    with tempfile.TemporaryDirectory() as temporary:
        out = pathlib.Path(temporary)
        (out / "assets").mkdir()
        (out / "layers").mkdir()
        a_cube_asset(out / "assets/fixture_rocket.usdc", 2.0)
        a_cube_asset(out / "assets/rocket.usdc", 2.0)
        base = Usd.Stage.CreateNew(str(out / "layers/base.usda"))
        prim = UsdGeom.Xform.Define(base, "/toy/Fixtures/rocket").GetPrim()
        prim.GetReferences().AddReference("../assets/fixture_rocket.usdc")
        prim.CreateAttribute("score:model", Sdf.ValueTypeNames.String).Set("models/rockets/rocket.gltf")
        base.GetRootLayer().Save()
        assembly.lay_fixtures_baked(out / assembly.BASE_LAYER, "rocket")
        spec = Sdf.Layer.FindOrOpen(str(out / assembly.BASE_LAYER)).GetPrimAtPath("/toy/Fixtures/rocket")
        assert [ref.assetPath for ref in spec.referenceList.prependedItems] == ["../assets/rocket.usdc"]
        assert spec.attributes["score:model"].default == "rocket"
        spec.referenceList.prependedItems = [Sdf.Reference("../assets/fixture_rocket.usdc")]
        spec.attributes["score:model"].default = "models/rockets/rocket.gltf"
        spec.layer.Save()
        a_cube_asset(out / "assets/rocket.usdc", 3.0)
        try:
            assembly.lay_fixtures_baked(out / assembly.BASE_LAYER, "rocket")
        except ValueError as error:
            assert "moved the model's frame" in str(error)
        else:
            raise AssertionError("a bake that moved the frame was laid")


TOY = "toy"


def a_toy(root):
    """A seed stage of a place `toy` as round three left it: a root over edit, characters, sound, effects and base
    layers; the base with a fan of row `fan`, a door, and the old record's wall and lamp."""
    from pxr import Sdf, Usd, UsdGeom
    (root / "layers").mkdir(parents=True)
    base = Usd.Stage.CreateNew(str(root / "layers/base.usda"))
    UsdGeom.Xform.Define(base, f"/{TOY}/Objects/fan_1").GetPrim().CreateAttribute(
        "score:row", Sdf.ValueTypeNames.String).Set("fan")
    UsdGeom.Xform.Define(base, f"/{TOY}/Objects/door_1")
    UsdGeom.Cube.Define(base, f"/{TOY}/Structure/old_wall")
    UsdGeom.Xform.Define(base, f"/{TOY}/Lights/old_lamp")
    base.GetRootLayer().Save()
    for name in ("edit", "characters", "sound", "effects"):
        Sdf.Layer.CreateNew(str(root / f"layers/{name}.usda")).Save()
    stage = Usd.Stage.CreateNew(str(root / f"{TOY}.usda"))
    stage.GetRootLayer().subLayerPaths = [f"./layers/{name}.usda" for name in
                                          ("edit", "characters", "sound", "effects", "base")]
    stage.SetDefaultPrim(stage.GetPrimAtPath(f"/{TOY}"))
    stage.GetRootLayer().Save()
    return root / f"{TOY}.usda"


def test_a_layer_is_held_in_its_place_and_the_root_plays_as_long_as_it():
    """A layer stage's layer (the motion row's, the light row's) goes between the others in their order, replacing
    the seed's of the same name, and the root's time range grows to the layer's."""
    from pxr import Sdf
    with tempfile.TemporaryDirectory() as temporary:
        root = a_toy(pathlib.Path(temporary) / "out")
        made = pathlib.Path(temporary) / "motion"
        (made / "layers").mkdir(parents=True)
        layer = Sdf.Layer.CreateNew(str(made / "layers/motion.usda"))
        layer.timeCodesPerSecond, layer.startTimeCode, layer.endTimeCode = 24.0, 0.0, 480.0
        layer.Save()
        assembly.take_layer(made, root, "layers/motion.usda", None)
        (made / "layers/light.usda").write_text("#usda 1.0\n")
        (made / "assets/light").mkdir(parents=True)
        (made / "assets/light/earth.png").write_bytes(b"png")
        assembly.take_layer(made, root, "layers/light.usda", "assets/light")
        found = Sdf.Layer.FindOrOpen(str(root))
        found.Reload()
        assert list(found.subLayerPaths) == [f"./layers/{name}.usda" for name in
                                             ("edit", "characters", "sound", "light", "motion", "effects", "base")]
        assert found.endTimeCode == 480.0 and (root.parent / "assets/light/earth.png").exists()
        live = pathlib.Path(temporary) / "live"  # the light stage's live lamps: a layer and no assets (2026-10-13)
        (live / "layers").mkdir(parents=True)
        (live / "layers/light.usda").write_text("#usda 1.0\n")
        assembly.take_layer(live, root, "layers/light.usda", "assets/light")
        assert not (root.parent / "assets/light").exists()


def test_the_accepted_record_replaces_the_seed_s_and_a_place_without_one_keeps_its_seed_record():
    """The accepted scene record's prims stand in the base in place of the old record's (the wall and the lamp
    gone, the objects kept), and the record is written beside the stage; a place with no record row keeps the seed's
    and says so."""
    from pxr import Usd
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        root = a_toy(folder / "out")
        (folder / "record/record").mkdir(parents=True)
        record = {"place": TOY, "lights": [{"type": "omni", "at": [0, 2, 0], "energy": 1.0, "range": 4.0}]}
        (folder / f"record/record/{TOY}.json").write_text(json.dumps(record))
        (folder / "kit.json").write_text(json.dumps({"pieces": []}))
        said = assembly.take_record({"scene-record": folder / "record", "kit": folder / "kit.json"}, root.parent, TOY)
        stage = Usd.Stage.Open(str(root))
        assert said == f"scene-record@{TOY}" and json.loads((root.parent / assembly.RECORD).read_text()) == record
        assert not stage.GetPrimAtPath(f"/{TOY}/Structure/old_wall") and not stage.GetPrimAtPath(f"/{TOY}/Lights/old_lamp")
        assert stage.GetPrimAtPath(f"/{TOY}/Lights/light_1") and stage.GetPrimAtPath(f"/{TOY}/Objects/fan_1")
        other = a_toy(folder / "other")
        said = assembly.take_record({"scene": folder / f"record/record/{TOY}.json", "kit": folder / "kit.json"},
                                    other.parent, TOY)
        kept = Usd.Stage.Open(str(other))  # held: a prim of a stage nothing holds expires at once
        assert "unverified" in said and kept.GetPrimAtPath(f"/{TOY}/Structure/old_wall")


def test_the_collision_gate_fails_a_seed_s_bare_wall_and_passes_the_record_written_again():
    """A seed's record wall drawn with no collision (as round three wrote every wall, floor and stair) fails the
    collision gate by name; the accepted record written over it (a wall and a flight of stairs) collides, so it
    passes."""
    from pxr import Sdf, Usd, UsdGeom, UsdShade
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        root = a_toy(folder / "out")
        base = Usd.Stage.Open(str(root.parent / "layers/base.usda"))
        UsdShade.Material.Define(base, f"/{TOY}/Library/concrete")
        bare = UsdGeom.Mesh.Define(base, f"/{TOY}/Structure/seed_floor")
        bare.GetPrim().CreateAttribute("score:kind", Sdf.ValueTypeNames.String).Set("structure")
        base.GetRootLayer().Save()
        before = assembly.judge_collision(root.parent, {}, None)
        assert before.answer == checks.FAIL and before.measures == {"uncolliding": 1, "models without collider": 0}
        assert before.findings[0].startswith(f"/{TOY}/Structure/seed_floor: "), before.findings
        (folder / "record/record").mkdir(parents=True)
        record = {"place": TOY, "structure": [
            {"name": "wall", "builder": "box", "centre": [0, 1.5, -4], "size": [8, 3, 0.2], "surface": "concrete"},
            {"name": "steps", "builder": "stairs", "foot": [2, 0, 0], "top": [2, 1.2, -1.8], "wide": 1.0, "steps": 6,
             "surface": "concrete"}]}
        (folder / f"record/record/{TOY}.json").write_text(json.dumps(record))
        (folder / "kit.json").write_text(json.dumps({"pieces": []}))
        assembly.take_record({"scene-record": folder / "record", "kit": folder / "kit.json"}, root.parent, TOY)
        after = assembly.judge_collision(root.parent, {}, None)
        assert after.answer == checks.PASS and after.measures == {"uncolliding": 0, "models without collider": 0}, \
            after.findings
        stage = Usd.Stage.Open(str(root))  # held: a prim of a stage nothing holds expires at once
        assert all(stage.GetPrimAtPath(f"/{TOY}/Structure/{name}") for name in ("wall", "steps"))

def a_sound_output(folder, uses):
    """A sound stage's output: hum and tone, each one file, played by `uses`."""
    for name in ("hum", "tone"):
        (folder / f"files/sound/{name}.ogg").parent.mkdir(parents=True, exist_ok=True)
        (folder / f"files/sound/{name}.ogg").write_bytes(name.encode())
    sounds = {name: {"files": [f"files/sound/{name}.ogg"], "volume_db": -6.0, "bus": "ambience" if name == "tone"
                     else "machines", "loops": True, "reach": 8.0, "ground_thud": False} for name in ("hum", "tone")}
    (folder / "sound.json").write_text(json.dumps({"place": TOY, "sounds": sounds, "uses": uses}))
    return folder


def test_the_sound_layer_is_the_sound_stage_s_and_a_sound_placed_nowhere_is_said():
    """Fault (2026-10-12): the assembly kept the seed's sound layer, so camp, launch and square failed complete's
    sound check. The layer is written from the accepted output: the room tone under Sound/Room, the hum at the fan's
    row, a motion's sound at its prim at its own second of the stage (the sound record gives one use a round), each
    file under its world name; a hum on a row the stage lacks is named."""
    from pxr import Usd, UsdMedia
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        root = a_toy(folder / "out")
        uses = [{"sound": "tone", "role": "room", "on": None, "from": "places.json"},
                {"sound": "hum", "role": "object", "on": "fan", "from": "row fan"},
                {"sound": "hum", "role": "motion", "on": f"/{TOY}/Objects/door_1", "at": 2.5, "loops_until": None,
                 "from": "door"},
                {"sound": "hum", "role": "object", "on": "pump", "from": "row pump"}]
        made = a_sound_output(folder / "sound", uses)
        unplaced = sounds.take(made, root, {"sounds": folder / "none.json"})
        assert unplaced == ["hum (object): no prim of the row or name pump on the stage"], unplaced
        stage = Usd.Stage.Open(str(root))
        tone = UsdMedia.SpatialAudio(stage.GetPrimAtPath(f"/{TOY}/Sound/Room/tone"))
        assert tone.GetFilePathAttr().Get().path == "../assets/sound/tone.ogg"
        assert (root.parent / "assets/sound/tone.ogg").read_bytes() == b"tone"
        assert stage.GetPrimAtPath(f"/{TOY}/Objects/fan_1/Sound")
        door = UsdMedia.SpatialAudio(stage.GetPrimAtPath(f"/{TOY}/Objects/door_1/Sound_0"))
        assert door.GetStartTimeAttr().Get().GetValue() == 2.5 * stage.GetTimeCodesPerSecond()
        assert stage.GetRootLayer().subLayerPaths[2] == "./layers/sound.usda"


# Row-kind rules written here (data/checks/row-kinds.json's shape), so the test does not follow the house's table.
KINDS = {"person": {"nouns": ["astronaut"], "does": ["acts"]}, "kettle": {"nouns": ["kettle"], "does": ["emits"]},
         "door": {"nouns": ["door"], "does": ["moves"]}, "plant": {"nouns": ["plants", "planter"], "does": ["grows"]},
         "loose": {"nouns": ["crate"], "does": ["loose"]}}
# A design showing a person, a kettle, a door hung on its wall as code, and plants on a raised planter.
DESIGN = {"rows": [{"id": "wall", "noun": "wall", "kind": "code", "anchor": "floor"},
                   {"id": "pilot", "noun": "astronaut", "kind": "generate", "anchor": "floor"},
                   {"id": "kettle", "noun": "kettle", "kind": "generate", "anchor": "floor"},
                   {"id": "door", "noun": "door", "kind": "code", "anchor": "on:wall"},
                   {"id": "bed", "noun": "planter", "kind": "generate", "anchor": "floor"},
                   {"id": "greens", "noun": "plants", "kind": "generate", "anchor": "on:bed"}]}


def test_a_place_needs_the_layers_its_design_shows():
    """The layers a place needs are read off its design alone: the person its characters layer, the kettle its
    effects, the door its motion, the plants on the planter its crops; no loose row, so no settle; light and sound always. A bare room needs light and sound only, and a crate
    on the floor its settle."""
    assert assembly.needed_layers(DESIGN, KINDS) == ["characters-layer", "crops-layer", "effects-layer", "motion",
                                                     "light", "sound"]
    bare = {"rows": [{"id": "wall", "noun": "wall", "kind": "code", "anchor": "floor"}]}
    assert assembly.needed_layers(bare, KINDS) == ["light", "sound"]
    crate = {"id": "crate", "noun": "crate", "kind": "generate", "anchor": "floor"}
    assert assembly.needed_layers({"rows": [*bare["rows"], crate]}, KINDS) == ["settle", "light", "sound"]


def test_a_place_waits_on_every_layer_it_needs():
    """The layers gate: unknown while a layer the place's design needs has no accepted output taken, never the seed's
    in its place; pass once all are; fail on a sound placed nowhere; unknown for a place with no design."""
    with tempfile.TemporaryDirectory() as temporary:
        output = pathlib.Path(temporary)
        (output / f"{TOY}.usda").write_text("#usda 1.0\n")
        (output / "design.json").write_text(json.dumps(DESIGN))
        (output / "row-kinds.json").write_text(json.dumps({"kinds": KINDS}))
        designed = {"design": output / "design.json", "row kinds": output / "row-kinds.json"}

        def judged(layers, unplaced=(), inputs=designed):
            (output / "origin.json").write_text(json.dumps({"layers": dict.fromkeys(layers, "x"), "record": "r",
                                                            "unplaced sounds": list(unplaced)}))
            return assembly.judge_layers(output, inputs, None)

        every = ["characters-layer", "crops-layer", "effects-layer", "motion", "light", "sound"]
        waiting = judged(["sound", "effects-layer", "motion", "light"])
        assert waiting.answer == checks.UNKNOWN and waiting.findings == (f"characters-layer@{TOY}",
                                                                         f"crops-layer@{TOY}"), waiting
        assert judged(every).answer == checks.PASS
        assert judged(every, ["hum"]).answer == checks.FAIL
        assert judged(every, inputs={"row kinds": output / "row-kinds.json"}).answer == checks.UNKNOWN


def test_a_tube_s_lamps_hang_on_every_bay_of_its_way():
    """A walkway tube's record is written with its pieces laid on every bay of the record's way (each with its
    spot, as the exporter lays them, so its lamps hang where the seed's did); a room's pieces stand as laid."""
    kit = {"bay": 2.0, "pieces": [{"kind": "tube_bay", "tube_part": "bay"}]}
    laid = assembly.laid_pieces(kit, {"tube_length": 6.0})
    assert len(laid) == 3 and all("spot" in piece for piece in laid), laid
    assert assembly.laid_pieces({"pieces": kit["pieces"]}, {}) == kit["pieces"]


def test_an_entry_waiting_on_its_model_lays_nothing_and_is_named():
    """Fault (2026-10-12): the campgrounds' record names its cairn, whose model is not released yet, and the
    assembly errored on it. An entry marked `waiting` lays nothing; the root prim names it for the completion gate."""
    from pxr import Usd
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        root = a_toy(folder / "out")
        (folder / "record/record").mkdir(parents=True)
        record = {"place": TOY, "objects": [{"name": "cairn", "model": "models/none/none.glb", "at": [0, 0, 0],
                                             "waiting": "its model comes through the next batch"}]}
        (folder / f"record/record/{TOY}.json").write_text(json.dumps(record))
        (folder / "kit.json").write_text(json.dumps({"pieces": []}))
        assembly.take_record({"scene-record": folder / "record", "kit": folder / "kit.json"}, root.parent, TOY)
        stage = Usd.Stage.Open(str(root))
        assert not stage.GetPrimAtPath(f"/{TOY}/Fixtures/cairn")
        assert list(stage.GetPrimAtPath(f"/{TOY}").GetAttribute(assembly.WAITING).Get()) == [
            "objects cairn: its model comes through the next batch"]


def test_a_waiting_entry_whose_row_the_bake_made_is_laid_with_it_and_no_longer_named():
    """The camp grounds' cairn (2026-10-13): its record entry waits on a released model that never comes; once the
    place's surface line has baked its row, the assembly lays that model where the entry stands (turned, its middle
    over the spot, its foot on it) and the entry leaves the root's waiting list."""
    from pxr import Gf, Usd, UsdGeom
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        root = a_toy(folder / "out")
        (folder / "record/record").mkdir(parents=True)
        record_data = {"place": TOY, "objects": [{"name": "cairn", "model": "models/none/none.glb", "row": "cairn",
                                                  "at": [3.0, 0.5, -2.0], "rotation": [0.0, 0.7071068, 0.0, 0.7071068],
                                                  "waiting": "no released model"}]}
        (folder / f"record/record/{TOY}.json").write_text(json.dumps(record_data))
        (folder / "kit.json").write_text(json.dumps({"pieces": []}))
        assembly.take_record({"scene-record": folder / "record", "kit": folder / "kit.json"}, root.parent, TOY)
        (root.parent / "assets").mkdir(exist_ok=True)
        asset = Usd.Stage.CreateNew(str(root.parent / "assets/cairn.usdc"))
        mesh = UsdGeom.Mesh.Define(asset, "/cairn/drawn")
        mesh.CreatePointsAttr([(-1.0, -1.0, -0.25), (1.0, -1.0, -0.25), (1.0, 1.0, 0.25), (-1.0, 1.0, 0.25)])
        mesh.CreateFaceVertexCountsAttr([4])
        mesh.CreateFaceVertexIndicesAttr([0, 1, 2, 3])
        asset.SetDefaultPrim(asset.GetPrimAtPath("/cairn"))
        asset.Save()
        (folder / "bake").mkdir()
        (folder / "bake/baked.json").write_text(json.dumps({"cairn": {}}))
        assert made_waiting.lay(root.parent, TOY, folder / "bake") == ["cairn"]
        stage = Usd.Stage.Open(str(root))
        prim = stage.GetPrimAtPath(f"/{TOY}/Fixtures/cairn")
        box = UsdGeom.BBoxCache(0, [UsdGeom.Tokens.default_]).ComputeWorldBound(prim).ComputeAlignedRange()
        middle = (box.GetMin() + box.GetMax()) / 2
        assert Gf.IsClose(box.GetMin()[1], 0.5, 1e-5) and Gf.IsClose(middle[0], 3.0, 1e-5), box
        assert Gf.IsClose(middle[2], -2.0, 1e-5) and Gf.IsClose(box.GetSize()[2], 2.0, 1e-4), box  # turned 90 degrees
        assert prim.GetAttribute("score:row").Get() == "cairn"
        assert not stage.GetPrimAtPath(f"/{TOY}").HasAttribute(assembly.WAITING)


def a_baked_triangle(made, name):
    """A one-triangle baked .gltf named `name` in `made`, its buffer beside it."""
    import struct
    made.mkdir(parents=True, exist_ok=True)
    blob = (struct.pack("9f", 0, 0, 0, 1, 0, 0, 0, 1, 0) + struct.pack("9f", 0, 0, 1, 0, 0, 1, 0, 0, 1)
            + struct.pack("6f", 0, 0, 1, 0, 0, 1) + struct.pack("3H", 0, 1, 2))
    (made / f"{name}.bin").write_bytes(blob)
    views = [(0, 36), (36, 36), (72, 24), (96, 6)]
    kinds = [(5126, "VEC3"), (5126, "VEC3"), (5126, "VEC2"), (5123, "SCALAR")]
    document = {"buffers": [{"uri": f"{name}.bin", "byteLength": len(blob)}],
                "bufferViews": [{"buffer": 0, "byteOffset": start, "byteLength": length} for start, length in views],
                "accessors": [{"bufferView": index, "componentType": component, "count": 3, "type": kind}
                              for index, (component, kind) in enumerate(kinds)],
                "nodes": [{"mesh": 0}],
                "meshes": [{"primitives": [{"attributes": {"POSITION": 0, "NORMAL": 1, "TEXCOORD_0": 2},
                                            "indices": 3}]}]}
    (made / f"{name}.gltf").write_text(json.dumps(document))


def test_a_claimed_model_is_laid_under_this_place_s_name_from_the_name_its_place_bakes_it_under():
    """The hangar (2026-10-15): it lays parts_rack_1, which old_station bakes as parts_rack (its take parts_rack-r1);
    the assembly looked for parts_rack_1 in old_station's bake and stopped. The claim's baked name comes from the
    hangar's own bake (elsewhere.json, baked_as), and the model is read from it under the hangar's name."""
    import export
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        (folder / "surfaces.json").write_text(json.dumps(
            {"elsewhere": {"parts_rack_1": {"take": "parts_rack-r1", "place": "old_station"}}}))
        (folder / "bake").mkdir()
        (folder / "bake/elsewhere.json").write_text(json.dumps({"parts_rack_1": {
            "take": "parts_rack-r1", "place": "old_station", "node": "surfaces-bake@old_station",
            "baked_as": "parts_rack"}}))
        (folder / "old").mkdir()
        (folder / "old/baked.json").write_text(json.dumps({"parts_rack": {"parts": "parts_rack-r1"}}))
        inputs = {"surfaces": folder / "surfaces.json", "surfaces-bake": folder / "bake",
                  "surfaces-bake@old_station": folder / "old", "surfaces-paint@old_station": folder / "paint"}
        [(bake, _, _, models)] = assembly.claimed_bakes(inputs, folder / "out")
        assert bake == folder / "old" and models == {"parts_rack_1": "parts_rack"}, models
        a_baked_triangle(folder / "old/made", "parts_rack")
        found = assembly.renamed_model(folder / "old/made", "parts_rack", "parts_rack_1", folder / "out/renamed")
        geometry = export.model_geometry(export.model_file(found, "parts_rack_1"))
        assert len(geometry["positions"]) == 3, geometry
        assert assembly.renamed_model(folder / "old/made", "parts_rack", "parts_rack", folder / "x") == folder / "old/made"


def test_a_claimed_model_its_place_bakes_under_its_own_name_is_laid_from_its_own_bake():
    """assembly@hub (2026-10-15): workshop bakes wrench_1 to wrench_4 from one take (wrench-r6), each its own size,
    and the hub's elsewhere.json names wrench_1 as every wrench's baked_as; wrench_2 stood as wrench_1's bake and
    lay_fixtures_baked stopped on the moved box. A model the claimed place bakes under its own name with the claimed
    take is read under it."""
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        names = ("wrench_1", "wrench_2", "wrench_9")
        elsewhere = {name: {"take": "wrench-r6", "place": "workshop"} for name in names}
        (folder / "surfaces.json").write_text(json.dumps({"elsewhere": elsewhere}))
        (folder / "bake").mkdir()
        (folder / "bake/elsewhere.json").write_text(json.dumps(
            {name: dict(claim, baked_as="wrench_1") for name, claim in elsewhere.items()}))
        (folder / "workshop").mkdir()
        (folder / "workshop/baked.json").write_text(json.dumps(
            {"wrench_1": {"parts": "wrench-r6"}, "wrench_2": {"parts": "wrench-r6"}}))
        inputs = {"surfaces": folder / "surfaces.json", "surfaces-bake": folder / "bake",
                  "surfaces-bake@workshop": folder / "workshop", "surfaces-paint@workshop": folder / "paint"}
        [(_, _, _, models)] = assembly.claimed_bakes(inputs, folder / "out")
        assert models == {"wrench_1": "wrench_1", "wrench_2": "wrench_2", "wrench_9": "wrench_1"}, models


def test_a_kit_piece_moved_since_the_seed_stands_at_its_kit_spot():
    """Fault (2026-10-12): the garage's fourth pressure gauge moved off the big door's leaf track in its kit, yet the
    assembly and the motion stage kept the seed's object where the old kit put it. relay_kit lays every piece at its
    kit spot now; a piece that did not move keeps its transform, and so does a second run."""
    import ground
    from pxr import Usd, UsdGeom
    laid_on = ground.place_ground
    ground.place_ground = lambda place, seat: None  # the toy is exported flat, as export.py --flat lays it
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        stage = triage_test.place_of(folder, [("crate", "box", (0, 0, 0)), ("crate", "box", (3, 0, 0))],
                                     [triage_test.row("crate")])
        kit = json.loads((folder / "kit.json").read_text())
        kit["pieces"][1]["at"] = [5.0, 0.0, 2.0]
        (folder / "kit.json").write_text(json.dumps(kit))
        said = record.relay_kit({"kit": folder / "kit.json"}, stage.parent, triage_test.PLACE)
        assert said == "; kit: 1 pieces laid at their kit spot (crate_2)", said
        opened = Usd.Stage.Open(str(stage))  # held: a prim of a stage nothing holds expires at once
        moved = UsdGeom.Xformable(opened.GetPrimAtPath(f"/{triage_test.PLACE}/Objects/crate_2"))
        assert tuple(moved.ComputeLocalToWorldTransform(0).ExtractTranslation()) == (5.0, 0.0, 2.0)
        assert record.relay_kit({"kit": folder / "kit.json"}, stage.parent, triage_test.PLACE) == ""
    ground.place_ground = laid_on


def test_a_light_the_motion_layer_animates_plays_its_keyframes():
    """A lamp whose strength the motion layer keys and the light layer sets plays the motion's keys on the assembled
    stage (the airlock's cycle light); a lamp the motion leaves alone keeps the light layer's strength. Both layers
    come in read-only, as a store checkout holds them, and neither file changes (assembly@airlock, 2026-10-16: the
    edit of the taken light layer was refused, and the store's files are never edited)."""
    import hashlib
    from pxr import Usd, UsdLux
    with tempfile.TemporaryDirectory() as temporary:
        root = a_toy(pathlib.Path(temporary) / "out")
        sums = {}
        for name, keyed in (("light", False), ("motion", True)):
            made = pathlib.Path(temporary) / name
            (made / "layers").mkdir(parents=True)
            stage = Usd.Stage.CreateNew(str(made / f"layers/{name}.usda"))
            for lamp in ("cycle", "steady"):
                if keyed and lamp == "steady":
                    continue
                strength = UsdLux.SphereLight.Define(stage, f"/{TOY}/Lights/{lamp}").CreateIntensityAttr()
                if keyed:
                    strength.Set(0.0, 0)
                    strength.Set(50.0, 12)
                else:
                    strength.Set(20.0)
            stage.GetRootLayer().Save()
            (made / f"layers/{name}.usda").chmod(0o444)  # as a store checkout holds it
            assembly.take_layer(made, root, f"layers/{name}.usda", None)
            sums[name] = hashlib.sha256((made / f"layers/{name}.usda").read_bytes()).hexdigest()
        before = Usd.Stage.Open(str(root))
        assert before.GetPrimAtPath(f"/{TOY}/Lights/cycle").GetAttribute("inputs:intensity").GetNumTimeSamples() == 0
        assembly.motion_over_light(root)
        stage = Usd.Stage.Open(str(root))
        cycle = stage.GetPrimAtPath(f"/{TOY}/Lights/cycle").GetAttribute("inputs:intensity")
        assert cycle.GetNumTimeSamples() == 2 and cycle.Get(12) == 50.0, cycle.Get(12)
        assert stage.GetPrimAtPath(f"/{TOY}/Lights/steady").GetAttribute("inputs:intensity").Get() == 20.0
        for name, digest in sums.items():
            for folder in (pathlib.Path(temporary) / name, root.parent):
                assert hashlib.sha256((folder / f"layers/{name}.usda").read_bytes()).hexdigest() == digest, (name, folder)
        held = list(stage.GetRootLayer().subLayerPaths)
        assert held.index("./layers/motion_keys.usda") + 1 == held.index("./layers/light.usda"), held


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[3] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
