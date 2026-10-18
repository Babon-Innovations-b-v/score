"""The motion stage's make and gates on the proof place's own records and seed (the launch: three ferries and the
game's rocket): the records pass all five gates; a ferry's lane laid over the pad fails `clear`, a round driven too
fast fails `speeds`, a round that no longer fits the layer's seconds fails `loops`, a lane run up onto the land fails
`grounded`, and a ferry left out of the record fails `covered`. A hub hatch swings open on its hinge and back within
its kind's speeds (the hub's own record keeps its hatches shut while nobody passes, so the swing is given here).

Run: .venv/bin/python score/stages/motion/motion_test.py   (needs the launch's and hub's round-three seeds in the work
folder)
"""
import json
import pathlib
import sys
import tempfile

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))

from score import checks  # noqa: E402
from score.stages import motion  # noqa: E402
from score.store import PROPS_HOME  # noqa: E402

REPO = pathlib.Path(__file__).resolve().parents[3]


def place_inputs(place, folder, movers=None):
    """The place's inputs, its movers record swapped for a changed copy in `folder` when given."""
    inputs = {name: pathlib.Path(pattern.format(place=place, data=str(REPO / "data"), seeds=str(PROPS_HOME / "work")))
              for name, pattern in motion.files(place).items()}
    if movers is not None:
        inputs["movers"] = pathlib.Path(folder) / "movers.json"
        inputs["movers"].write_text(json.dumps(movers))
    return inputs


def made(inputs, folder):
    out = pathlib.Path(folder) / "out"
    out.mkdir()
    motion.make(inputs, out, 0, {})
    assert motion.layer_faults(out) == []
    return out


def answers(inputs, folder, only=None):
    out = made(inputs, folder)
    return {check.name: check.judge(out, inputs, None) for check in motion.CHECKS
            if only is None or check.name in only}


def launch_movers():
    return json.loads((REPO / "data/movers/launch.json").read_text())


def mover(record, name):
    return next(entry for entry in record["movers"] if entry["name"] == name)


def test_the_launch_passes_its_gates():
    with tempfile.TemporaryDirectory() as folder:
        found = answers(place_inputs("launch", folder), folder)
    assert all(verdict.answer == checks.PASS for verdict in found.values()), {
        name: (verdict.reason, verdict.findings) for name, verdict in found.items()}
    assert found["covered"].measures["moved"] == 4, found["covered"].measures


def test_a_ferry_read_without_a_time_stands_at_its_rest():
    from pxr import Sdf, Usd, UsdGeom
    with tempfile.TemporaryDirectory() as folder:
        inputs = place_inputs("launch", folder)
        out = made(inputs, folder)
        stage = motion.composed(out, inputs)
        still = motion.composed(out, inputs)
        still.MuteLayer(Sdf.Layer.FindOrOpen(str(out / "layers/motion.usda")).identifier)
        for entry in launch_movers()["movers"]:
            unset, rest = (np.asarray(UsdGeom.Xformable(found.GetPrimAtPath(entry["prim"])).ComputeLocalToWorldTransform(
                Usd.TimeCode.Default())) for found in (stage, still))
            assert np.allclose(unset, rest, atol=1e-6), (entry["name"], unset[3], rest[3])


def test_a_lane_over_the_pad_fails_clear():
    record = launch_movers()
    lane = mover(record, "ferry_2")["path"]
    lane["points"] = [[x, z + 60.0] for x, z in lane["points"]]  # north over the pad's apron
    with tempfile.TemporaryDirectory() as folder:
        found = answers(place_inputs("launch", folder, record), folder, ("clear",))
    assert found["clear"].answer == checks.FAIL, found["clear"].reason
    assert any("far_pad" in line for line in found["clear"].findings), found["clear"].findings


def test_a_round_too_fast_fails_speeds():
    record = launch_movers()
    mover(record, "ferry_1")["length"] = 60.0  # 941 m in 60 s: 15.7 m/s, past the Star Ferry's 5.8
    with tempfile.TemporaryDirectory() as folder:
        found = answers(place_inputs("launch", folder, record), folder, ("speeds",))
    assert found["speeds"].answer == checks.FAIL, found["speeds"].reason
    assert found["speeds"].measures["ferry_1 peak"] > 15.0, found["speeds"].measures


def test_a_round_off_the_layer_s_seconds_fails_loops():
    record = launch_movers()
    with tempfile.TemporaryDirectory() as folder:
        inputs = place_inputs("launch", folder, record)
        out = made(inputs, folder)
        mover(record, "ferry_2")["length"] = 100.0  # the record now says a round the layer does not hold
        inputs["movers"].write_text(json.dumps(record))
        verdict = dict((check.name, check) for check in motion.CHECKS)["loops"].judge(out, inputs, None)
    assert verdict.answer == checks.FAIL, verdict.reason
    assert any("ferry_2" in line for line in verdict.findings), verdict.findings


def test_a_lane_up_on_the_land_fails_grounded():
    record = launch_movers()
    lane = mover(record, "ferry_1")["path"]
    lane["points"] = [[x + 40.0, z] for x, z in lane["points"]]  # past the harbour's edge at x -110
    with tempfile.TemporaryDirectory() as folder:
        found = answers(place_inputs("launch", folder, record), folder, ("grounded",))
    assert found["grounded"].answer == checks.FAIL, found["grounded"].reason
    assert any("ferry_1" in line and "off the water" in line for line in found["grounded"].findings)


def test_a_ferry_left_standing_fails_covered():
    record = launch_movers()
    record["movers"] = [entry for entry in record["movers"] if entry["name"] != "ferry_3"]
    with tempfile.TemporaryDirectory() as folder:
        found = answers(place_inputs("launch", folder, record), folder, ("covered",))
    assert found["covered"].answer == checks.FAIL, found["covered"].reason
    assert found["covered"].findings == ("/launch/Objects/far_ferry_3 (ferry)",), found["covered"].findings


def swinging_hatch():
    """The hub's movers record with its first hatch (leaf, wheel and window) swung 90 degrees into the room at 30
    degrees a second, opening at 4 s and shutting at 15 s of a 60 s round, as the record held it until 2026-10-18."""
    record = json.loads((REPO / "data/movers/hub.json").read_text())
    swing = {"about": "Objects/hatch_hinge_1", "angle": -90.0, "speed": 30.0, "starts": "shut",
             "moves": [[4.0, "open"], [15.0, "shut"]]}
    parts = ("leaf", "wheel", "window")
    record["movers"] = [{"name": f"hatch_door_{part}_1", "prim": f"/hub/Objects/hatch_{part}_1", "kind": "hatch",
                         "on": "rail", "start": 0.0, "length": 60.0, "loop": True, "swing": swing,
                         "from": "motion_test: a hatch opened by someone passing through"} for part in parts]
    record["still"] = {name: why for name, why in record["still"].items()
                       if name not in {f"hatch_{part}_1" for part in parts}}
    return record


def test_a_hub_hatch_swings_open_and_back():
    with tempfile.TemporaryDirectory() as folder:
        inputs = place_inputs("hub", folder, swinging_hatch())
        out = made(inputs, folder)
        stage = motion.composed(out, inputs)
        record = json.loads(inputs["movers"].read_text())
        leaf = next(entry for entry in record["movers"] if entry["name"].startswith("hatch_door_leaf"))
        swing, rate = leaf["swing"], motion.rate_of(stage)
        shape = motion.shaped(stage, leaf["prim"])
        opened = float(leaf["start"]) + float(swing["moves"][0][0]) + abs(float(swing["angle"])) / float(swing["speed"])
        turned = motion.turn_between(shape.placed(float(leaf["start"]) * rate), shape.placed(opened * rate))
        found = {check.name: check.judge(out, inputs, None) for check in motion.CHECKS}
    assert np.isclose(turned, abs(float(swing["angle"])), atol=0.5), turned
    assert all(verdict.answer == checks.PASS for verdict in found.values()), {
        name: (verdict.reason, verdict.findings) for name, verdict in found.items()}


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[3] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
