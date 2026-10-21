"""The physics trial made from a design (design.py) on a small place made here (tools/usd/physics_test.py's toy room):
its loose rows' laid objects are dropped back onto their own spots, one with a shelf over it left out, the table (no
loose row) never; the trial's layers write with each drop landing where it stood; the gravity is the body's under the
scene's top site (the Moon's 1.62 m/s², Mars's 3.71: the textbook values); and the `designed` gate fails a body no
inventory row has.

Run: .venv/bin/python score/stages/physics/design_test.py
"""
import json
import pathlib
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tools/usd"))
from pxr import Gf, Usd, UsdGeom  # noqa: E402

import physics_test as toy  # noqa: E402
from score import checks  # noqa: E402
from score.stages import physics as stage_physics  # noqa: E402
from score.stages import row_kinds  # noqa: E402
from score.stages.physics import design  # noqa: E402

INVENTORY = {"rows": [{"id": "crate", "noun": "crate"}, {"id": "stool", "noun": "stool"},
                      {"id": "table", "noun": "table"}, {"id": "floor_plate", "noun": "floor plate"}]}
SETTING = json.loads((REPO / "data/physics/setting.json").read_text())


def toy_with_shelf(folder):
    """The toy room with a shelf 0.2 m over crate_2's top: crate_2's fall is not clear."""
    toy.toy_place(folder)
    stage = Usd.Stage.Open(str(pathlib.Path(folder) / "layers/base.usda"))
    box = [((2.3, 0.5, 1.8), (2.7, 0.55, 2.2))]
    holder = UsdGeom.Xform.Define(stage, f"/{toy.PLACE}/Objects/shelf_1")
    holder.MakeMatrixXform().Set(Gf.Matrix4d().SetTranslate(Gf.Vec3d(2.5, 0.525, 2.0)))
    toy.mesh(stage, f"/{toy.PLACE}/Objects/shelf_1/geo", box, (2.5, 0.525, 2.0))
    stage.Save()
    return toy.composed(folder)


def test_the_loose_rows_drop_where_they_stand():
    with tempfile.TemporaryDirectory() as folder:
        record = design.trial(toy.PLACE, toy_with_shelf(folder), INVENTORY, row_kinds.table(), ("moon", 1.62))
        assert [drop["object"] for drop in record["drops"]] == ["crate_1", "stool_1"], record["drops"]
        assert record["left out"] == ["crate_2: something stands in its fall"], record["left out"]
        written = toy.physics.write(folder, record, toy.MATERIALS)
        assert not written["faults"], written["faults"]
        # each lands back on its own lowest point: the crate's on the floor at 0, the stool's at 0.01
        assert {name: round(top, 6) for name, top in written["tops"].items()} == {"crate_1": 0.0, "stool_1": 0.01}
        written_stage = toy.composed(folder)
        lifted = toy.physics.world_box(toy.physics.object_prim(written_stage, "crate_1"))
        assert abs(lifted[0][1] - 0.5) < 1e-6 and abs(lifted[0][0] - 1.85) < 1e-6, lifted
        scene = written_stage.GetPrimAtPath(f"/{toy.PLACE}/Physics/Scene")
        assert abs(scene.GetAttribute("physics:gravityMagnitude").Get() - 1.62) < 1e-6


def test_the_gravity_is_the_body_s_under_the_top_site():
    body, gravity = design.ground("habitat", {"habitat": "base"}, SETTING)
    assert body == "moon" and abs(gravity - 1.62) < 0.01, (body, gravity)
    body, gravity = design.ground("camp", {"camp": "campgrounds"}, SETTING)
    assert body == "mars" and abs(gravity - 3.71) < 0.02, (body, gravity)
    try:
        design.ground("nowhere", {}, SETTING)
    except ValueError:
        pass
    else:
        raise AssertionError("a scene under no site was given a body")


def test_a_body_no_row_has_fails_designed():
    with tempfile.TemporaryDirectory() as folder:
        folder = pathlib.Path(folder)
        inventory = folder / "inventory.json"
        inventory.write_text(json.dumps({"rows": [{"id": "crate", "noun": "crate"}]}))
        record = {"drops": [{"object": "crate_1"}, {"object": "stool_1"}], "hinges": [], "moved": []}
        (folder / "record.json").write_text(json.dumps(record))
        found = stage_physics.judge_designed(folder, {"design": inventory}, None)
        assert found.answer == checks.FAIL and found.findings == ("stool_1 is no object of the scene's inventory",)
        (folder / "record.json").write_text(json.dumps(dict(record, drops=record["drops"][:1])))
        assert stage_physics.judge_designed(folder, {"design": inventory}, None).answer == checks.PASS


def test_a_trial_with_no_hinge_passes_only_when_it_says_why():
    with tempfile.TemporaryDirectory() as folder:
        folder = pathlib.Path(folder)
        (folder / "measures.json").write_text(json.dumps({"hinges": {}}))
        (folder / "record.json").write_text(json.dumps({"hinges": []}))
        assert stage_physics.judge_hinge(folder, {}, None).answer == checks.UNKNOWN
        (folder / "record.json").write_text(json.dumps({"hinges": [], "no_hinges": design.NO_HINGES}))
        assert stage_physics.judge_hinge(folder, {}, None).answer == checks.PASS


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(REPO / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
