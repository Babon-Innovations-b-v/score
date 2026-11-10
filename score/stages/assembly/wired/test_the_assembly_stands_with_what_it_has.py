"""The assembly as the table runs it stands with what it has: a floor thing a wall's thing was laid into is parted to
its nearest free spot (one holding another, or only touching, is left); a stage the make left in a reference cycle holds
no asset layer once it is made (so the screens take can write its stack over the asset); and a voice on a person the
characters layer did not lay is a named gap for complete, never an unplaced sound failing the layers gate, while a
voice on a person who was laid, and any other sound, still fails it. Toy folders made here; no store, no machine.

Breaks (each applied once, seen red, reverted):
Break: score/stages/assembly/wired/parting.py: `if not loose(entry, holding):` -> `if False:` (the console holding its
    screen is moved too)
Break: score/stages/assembly/wired/parting.py: `fitting.moved_by(stage.GetPrimAtPath(path), foot, 1.0, foot + move)`
    -> `pass` (laid.json says parted, the stage still holds it in the pipe)
Break: score/stages/assembly/wired/__init__.py: `gc.collect()` -> `pass` (the cycle's stage keeps the asset loaded)
Break: score/stages/assembly/wired/__init__.py: `if use.get("voice") and use["on"] not in laid` -> `if use["on"] not in
    laid` (the pump's hum is taken out too)
Break: score/stages/assembly/wired/__init__.py: `if "missing" not in look` -> `if True` (the astronaut named missing
    counts as laid: base's voice stays unplaced)
Break: score/stages/__init__.py: `screens.assembled(wired.make)` -> `screens.assembled(assembly.make_from_seed)`
"""
import gc
import json
import pathlib
import sys

import numpy as np

REPO = pathlib.Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))

from score import checks, stages  # noqa: E402
from score.stages import assembly, gaps  # noqa: E402
from score.stages.assembly import fitting, made_waiting, sounds, wired  # noqa: E402
from score.stages.assembly.wired import parting  # noqa: E402

VOICE = {"sound": "crew_talk", "role": "object", "on": "person_1", "voice": True, "from": "voices"}
HUM = {"sound": "pump_hum", "role": "object", "on": "pump_1", "from": "objects"}
RADIO = {"sound": "helmet_radio_talk", "role": "object", "on": "astronaut_left", "voice": True, "from": "voices"}
# A 6 m room's walls; a pipe laid against its west wall; a pedestal on the floor 0.2 m inside the pipe; a console the
# pipe also reaches into, which holds a screen; a crate only touching the pipe.
WALLS = {"wall_1": ((-3.0, 0.0, -3.0), (-2.9, 3.0, 3.0)), "wall_2": ((2.9, 0.0, -3.0), (3.0, 3.0, 3.0)),
         "wall_3": ((-3.0, 0.0, -3.0), (3.0, 3.0, -2.9)), "wall_4": ((-3.0, 0.0, 2.9), (3.0, 3.0, 3.0))}
THINGS = {"pipe_1": ((-2.9, 0.0, -1.0), (-2.2, 2.5, 0.3)), "pedestal_1": ((-2.4, 0.0, 0.0), (-2.0, 0.7, 0.4)),
          "console_1": ((-2.4, 0.0, -1.2), (-2.0, 0.7, -0.6)), "screen_1": ((-2.3, 0.7, -1.1), (-2.1, 1.0, -0.7)),
          "crate_1": ((-2.2, 0.0, 1.0), (-1.8, 0.5, 1.4))}
ON = {"pipe_1": {"how": "wall", "holder": None, "span": [[-2.9, -3.0], [-2.9, 3.0]], "out": [1.0, 0.0]},
      "screen_1": {"how": "top", "holder": ["console_1"]}}


def a_box(stage, path, low, high):
    """A cube prim filling the box (low, high), placed by one transform op as the assembly's objects are."""
    from pxr import Gf, UsdGeom
    cube = UsdGeom.Cube.Define(stage, path)
    cube.CreateSizeAttr(1.0)
    low, high = np.asarray(low, float), np.asarray(high, float)
    cube.AddTransformOp().Set(Gf.Matrix4d().SetScale(Gf.Vec3d(*(high - low)))
                              * Gf.Matrix4d().SetTranslate(Gf.Vec3d(*((low + high) / 2))))


def a_laid_room(folder):
    """An assembly output holding the room on its base layer, its scene record and its laid.json."""
    from pxr import Usd, UsdGeom
    (folder / "layers").mkdir(parents=True)
    stage = Usd.Stage.CreateNew(str(folder / assembly.BASE_LAYER))
    UsdGeom.Xform.Define(stage, "/toy")
    for name, (low, high) in WALLS.items():
        a_box(stage, f"/toy/Structure/{name}", low, high)
    for name, (low, high) in THINGS.items():
        a_box(stage, f"/toy/Objects/{name}", low, high)
    stage.GetRootLayer().Save()
    record = {"objects": [{"name": name, "row": name.rsplit("_", 1)[0], **({"on": ON[name]} if name in ON else {})}
                          for name in THINGS]}
    (folder / assembly.RECORD).write_text(json.dumps(record))
    (folder / made_waiting.LAID).write_text(json.dumps({"objects": [
        {"name": name, "row": name.rsplit("_", 1)[0], "low": list(low), "high": list(high)}
        for name, (low, high) in THINGS.items()], "holders": [], "fitted": []}))
    return folder


def a_cycle_holding(asset):
    """A stage referencing `asset`, held only by a closure that calls itself (fitting.fitted's `one`)."""
    from pxr import Usd
    stage = Usd.Stage.CreateInMemory()
    stage.DefinePrim("/thing").GetReferences().AddReference(str(asset))

    def one(depth=0):
        return stage if depth else one(depth + 1)
    return one


def an_assembly(folder, uses, looks):
    """An assembly output whose sounds `uses` all played at nothing, and its inputs: the sound output and a characters
    layer of `looks`."""
    (folder / "out").mkdir(parents=True)
    (folder / f"out/{folder.name}.usda").write_text("#usda 1.0\n")
    (folder / "sound").mkdir()
    (folder / "characters").mkdir()
    (folder / "sound/sound.json").write_text(json.dumps({"sounds": {}, "uses": uses}))
    (folder / "characters/characters.json").write_text(json.dumps({"place": "lab", "looks": looks}))
    (folder / "out/origin.json").write_text(json.dumps({"layers": {}, "record": "scene-record@lab",
                                                         "unplaced sounds": [wired.unplaced_words(use)
                                                                             for use in uses]}))
    return folder / "out", {"sound": folder / "sound", "characters-layer": folder / "characters"}


def test_the_assembly_stands_with_what_it_has(tmp_path):
    from pxr import Sdf, Usd
    assert stages.ASSEMBLY.make.__wrapped__ is wired.make

    room = a_laid_room(tmp_path / "room")
    fits = parting.parted(room, "toy")
    assert [(fit["name"], fit["how"], fit["moved"]) for fit in fits] == [("pedestal_1", "parted", 0.2)], fits
    stage = Usd.Stage.Open(str(room / assembly.BASE_LAYER))
    low, high = fitting.world_box(stage, "/toy/Objects/pedestal_1")
    assert np.allclose(low, (-2.2, 0.0, 0.0)) and np.allclose(high, (-1.8, 0.7, 0.4)), (low, high)
    laid = json.loads((room / made_waiting.LAID).read_text())
    assert [entry["low"] for entry in laid["objects"] if entry["name"] == "pedestal_1"] == [[-2.2, 0.0, 0.0]]
    for name in ("console_1", "crate_1", "pipe_1"):
        assert np.allclose(fitting.world_box(stage, f"/toy/Objects/{name}")[0], THINGS[name][0]), name
    assert parting.parted(room, "toy") == []
    del stage

    asset = tmp_path / "assets/monitor.usda"
    asset.parent.mkdir()
    made = Sdf.Layer.CreateNew(str(asset))
    made.defaultPrim = "thing"
    Sdf.CreatePrimInLayer(made, "/thing")
    made.Save()
    del made
    gc.disable()
    try:
        held = a_cycle_holding(asset)
        del held
        assert Sdf.Layer.Find(str(asset)) is not None
        wired.release()
    finally:
        gc.enable()
    assert Sdf.Layer.Find(str(asset)) is None
    asset.rename(asset.with_name("monitor_baked.usda"))
    Sdf.Layer.CreateNew(str(asset)).Save()

    stage = Usd.Stage.CreateInMemory()
    stage.DefinePrim("/lab")
    assert sounds.object_sounds(stage, "lab", [VOICE], {}, tmp_path) == [wired.unplaced_words(VOICE)]

    out, inputs = an_assembly(tmp_path / "lab", [VOICE], {})
    wired.silence(inputs, out)
    origin = json.loads((out / "origin.json").read_text())
    assert origin["unplaced sounds"] == [] and origin[wired.SILENT] == [wired.unplaced_words(VOICE)]
    verdict = assembly.judge_layers(out, inputs, None)
    assert verdict.answer == checks.UNKNOWN, verdict
    accepted = gaps.judge_accepted(tmp_path, {"assembly": out}, None)
    assert accepted.answer == checks.FAIL and accepted.findings == (
        f"crew_talk: person_1's voice, person_1 not laid: {wired.unplaced_words(VOICE)}",), accepted
    assert "its cast lays no one of that name" in accepted.reason

    missing = {"astronaut_left": {"look": "astronaut_suit/made", "missing": "no accepted body of its look"}}
    out, inputs = an_assembly(tmp_path / "base", [RADIO, HUM], missing)
    wired.silence(inputs, out)
    origin = json.loads((out / "origin.json").read_text())
    assert origin["unplaced sounds"] == [wired.unplaced_words(HUM)], origin
    assert "no accepted body of its look" in json.loads((out / gaps.WRITTEN).read_text())["gaps"][0]["reason"]
    assert assembly.judge_layers(out, inputs, None).answer == checks.FAIL

    laid = {"astronaut_left": {"look": "astronaut_suit/made"}}
    out, inputs = an_assembly(tmp_path / "laid", [RADIO], laid)
    wired.silence(inputs, out)
    origin = json.loads((out / "origin.json").read_text())
    assert origin["unplaced sounds"] == [wired.unplaced_words(RADIO)] and wired.SILENT not in origin
    assert not (out / gaps.WRITTEN).exists()
    assert assembly.judge_layers(out, inputs, None).answer == checks.FAIL
