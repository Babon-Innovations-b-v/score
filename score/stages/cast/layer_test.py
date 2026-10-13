"""The characters layer on the hub's cast with a stand-in accepted body: Bram laid in his look's body at his spot,
playing his clip; a person whose look has no accepted body is left out, never a stand-in, and the layer passes
with the gap named, which complete's people check (tools/usd/contents.py) fails by name. The stand-in body is a built body on this machine (the motion work's bram.glb); skipped, and says so,
without one. Nothing rented.

Run: .venv/bin/python score/stages/cast/layer_test.py
"""
import json
import os
import pathlib
import shutil
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from score import checks  # noqa: E402
import score.stages.cast.layer as layer  # noqa: E402

BODY = pathlib.Path(os.environ.get("MOTION_WORK", pathlib.Path.home() / ".farm-factory-motion/work")) / "bodies/bram.glb"
# Scratch on disk under $PROPS_HOME/tmp, never /tmp (a RAM-backed tmpfs on the PC).
tempfile.tempdir = str(layer.SCRATCH)
layer.SCRATCH.mkdir(parents=True, exist_ok=True)


def a_cast(folder, people):
    """The cast stage's output for the hub: these people, no crowd."""
    (folder / "cast").mkdir(parents=True)
    (folder / "cast/cast.json").write_text(json.dumps({"place": "hub", "characters": people, "crowd": None}))
    (folder / "record.json").write_text(json.dumps({"place": "hub", "people": []}))
    return {"cast": folder / "cast", "cast record": folder / "record.json"}


def test_a_person_stands_in_their_own_accepted_body_and_a_missing_body_is_named():
    if not BODY.exists():
        print(f"skipped: no built body at {BODY}")
        return
    from pxr import Usd, UsdGeom
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        bram = {"name": "bram", "character": "bram", "look": "bram/work", "at": [1.0, 0.0, 2.0], "turn": 90.0,
                "doing": "standing", "start": 0.0}
        nev = {"name": "nev", "character": "nev", "look": "nev/work", "at": [3.0, 0.0, 2.0], "turn": 0.0,
               "doing": "standing", "start": 0.0}
        inputs = a_cast(folder, [bram, nev])
        dressed = folder / "dress"  # stands for people-dress-bram-work's accepted output
        dressed.mkdir()
        shutil.copyfile(BODY, dressed / "body.glb")
        inputs[layer.body_row("bram/work")] = dressed
        out = folder / "out"
        out.mkdir()
        layer.make(inputs, out, 0, {})
        assert layer.layer_faults(out) == []
        stage = Usd.Stage.Open(str(out / layer.LAYER))
        person = stage.GetPrimAtPath("/hub/Characters/bram")
        assert person and person.GetCustomDataByKey("score:look") == "bram/work"
        spot = UsdGeom.Xformable(person).ComputeLocalToWorldTransform(0).ExtractTranslation()
        assert tuple(spot) == (1.0, 0.0, 2.0), spot
        assert (out / layer.ASSETS / "bram-work.usdc").exists()
        assert not stage.GetPrimAtPath("/hub/Characters/nev")
        verdict = layer.judge_laid(out, inputs, None)
        assert verdict.answer == checks.PASS and verdict.measures["missing"] == 1, verdict
        assert "nev (nev/work)" in verdict.findings[0], verdict
        sys.path.insert(0, str(REPO / "tools/usd"))
        import contents
        assert [fault for fault in contents.layer_faults(out) if fault.startswith("nev (nev/work)")], \
            contents.layer_faults(out)
        out_all = folder / "all"
        out_all.mkdir()
        inputs = {**a_cast(folder / "bram only", [bram]), layer.body_row("bram/work"): dressed}
        layer.make(inputs, out_all, 0, {})
        assert layer.judge_laid(out_all, inputs, None).answer == checks.PASS


def test_a_place_reads_only_the_looks_its_cast_names():
    """Each cast place waits on its own looks' bodies, not the slowest look of all: the looks are dealt from its
    record as the cast stage deals them (a named look, the crowd's far body)."""
    record = {"people": [{"name": "bram", "character": "bram", "look": "bram_work", "at": [0, 0, 0],
                          "facing_to": [0, 0, 1], "doing": "standing"}],
              "crowd": {"name": "crowd", "character": "kit_m_avg", "body": "far"}}
    assert layer.dealt_looks(json.dumps(record)) == {"bram-work", "kit_m_avg-far"}
    assert layer.dealt_looks(json.dumps({"people": []})) == frozenset()


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
