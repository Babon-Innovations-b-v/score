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
from score.stages.assembly import record, sounds  # noqa: E402
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
    row, a motion's sound at its prim from its start, each file under its world name; a hum on a row the stage lacks
    is named."""
    from pxr import Usd, UsdMedia
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        root = a_toy(folder / "out")
        (folder / "motion").mkdir()
        (folder / f"motion/{TOY}.json").write_text(json.dumps({"motions": [{"prim": f"/{TOY}/Objects/door_1",
                                                                             "start": 2.0}]}))
        uses = [{"sound": "tone", "role": "room", "on": None, "from": "places.json"},
                {"sound": "hum", "role": "object", "on": "fan", "from": "row fan"},
                {"sound": "hum", "role": "motion", "on": f"/{TOY}/Objects/door_1", "at": 0.5, "loops_until": None,
                 "from": "door"},
                {"sound": "hum", "role": "object", "on": "pump", "from": "row pump"}]
        made = a_sound_output(folder / "sound", uses)
        unplaced = sounds.take(made, root, {"motions": folder / "motion", "sounds": folder / "none.json"})
        assert unplaced == ["hum (object): no prim of the row or name pump on the stage"], unplaced
        stage = Usd.Stage.Open(str(root))
        tone = UsdMedia.SpatialAudio(stage.GetPrimAtPath(f"/{TOY}/Sound/Room/tone"))
        assert tone.GetFilePathAttr().Get().path == "../assets/sound/tone.ogg"
        assert (root.parent / "assets/sound/tone.ogg").read_bytes() == b"tone"
        assert stage.GetPrimAtPath(f"/{TOY}/Objects/fan_1/Sound")
        door = UsdMedia.SpatialAudio(stage.GetPrimAtPath(f"/{TOY}/Objects/door_1/Sound_0_2000"))  # its round starts at 2 s
        assert door.GetStartTimeAttr().Get().GetValue() == 2.5 * stage.GetTimeCodesPerSecond()
        assert stage.GetRootLayer().subLayerPaths[2] == "./layers/sound.usda"


def test_a_place_waits_on_every_layer_it_needs():
    """The layers gate: unknown while a layer the place needs (data/checks/contents.json) has no accepted output
    taken, never the seed's in its place; pass once all are; nothing needed of a part of another place; fail on a
    sound placed nowhere; unknown for a place the contents do not list."""
    with tempfile.TemporaryDirectory() as temporary:
        output = pathlib.Path(temporary)
        (output / f"{TOY}.usda").write_text("#usda 1.0\n")
        expected = output / "contents.json"

        def judged(needs, layers, unplaced=()):
            expected.write_text(json.dumps({"places": {TOY: needs} if needs is not None else {}}))
            (output / "origin.json").write_text(json.dumps({"layers": dict.fromkeys(layers, "x"), "record": "r",
                                                            "unplaced sounds": list(unplaced)}))
            return assembly.judge_layers(output, {"expected contents": expected}, None)

        needs = {"effects": ["steam"], "motion": [], "crops": {"planted_share": 0.9}}
        waiting = judged(needs, ["sound", "effects-layer"])
        assert waiting.answer == checks.UNKNOWN and waiting.findings == (f"light@{TOY}", f"crops-layer@{TOY}"), waiting
        assert judged(needs, ["sound", "light", "effects-layer", "crops-layer"]).answer == checks.PASS
        assert judged({"part_of": "host", "effects": ["x"]}, []).answer == checks.PASS
        assert judged(needs, ["sound", "light", "effects-layer", "crops-layer"], ["hum"]).answer == checks.FAIL
        assert judged(None, ["sound"]).answer == checks.UNKNOWN


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


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
