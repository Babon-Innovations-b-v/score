"""The effects stage's make and gates on the proof place's own record and seed (the launch), and the look's measures:
the record passes all four gates; a flame light too weak fails `light`, a ground cloud too slow fails `footage`, and
a trail baked off another climb than the rocket's fails `attached`; the airlock's pump-down passes, measured in
metres, and fails `footage` when its fog lingers and `light` is unknown when it no longer says why it gives none; the
camp's drift stays out of its domes and fails `outside` baked without them; a point ahead of a camera lands where the picture shows it; `shown` and `lit` read their measures.

Run: .venv/bin/python score/stages/effects/effects_test.py   (needs the launch's round-three seed in the work folder)
"""
import json
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))

from score import checks  # noqa: E402
from score.stages import effects  # noqa: E402
from score.stages.effects import look  # noqa: E402
from score.store import PROPS_HOME  # noqa: E402

REPO = pathlib.Path(__file__).resolve().parents[3]


def launch_inputs(folder, record=None, motion=None, place="launch"):
    """The launch's (or another place's) inputs, with the record or motion record swapped for a changed copy in
    `folder` when given."""
    inputs = {name: pathlib.Path(pattern.format(place=place, data=str(REPO / "data"), seeds=str(PROPS_HOME / "work")))
              for name, pattern in effects.files(place).items()}
    for name, changed in (("record", record), ("motion", motion)):
        if changed is not None:
            inputs[name] = pathlib.Path(folder) / f"{name}.json"
            inputs[name].write_text(json.dumps(changed))
    return inputs


def answers(inputs, folder):
    out = pathlib.Path(folder) / "out"
    out.mkdir()
    effects.make(inputs, out, 0, {})
    assert effects.layer_faults(out) == []
    return {check.name: check.judge(out, inputs, None) for check in effects.CHECKS}


def launch_record():
    return json.loads((REPO / "data/effects/launch.json").read_text())


def emitter(record, name):
    return next(entry for entry in record["effects"] if entry["name"] == name)


def test_the_launch_passes_its_gates():
    with tempfile.TemporaryDirectory() as folder:
        found = answers(launch_inputs(folder), folder)
    assert all(verdict.answer == checks.PASS for verdict in found.values()), {
        name: (verdict.reason, verdict.findings) for name, verdict in found.items()}
    assert found["attached"].measures["carried"] > 1000, "the rocket never moved the flame"


def test_a_weak_light_and_a_slow_cloud_fail():
    record = launch_record()
    record["lights"][0]["intensity"] = [[seconds, value / 10] for seconds, value in record["lights"][0]["intensity"]]
    for name in ("ground_cloud", "cloud_billows"):
        emitter(record, name)["speed"] = [value / 4 for value in emitter(record, name)["speed"]]
    with tempfile.TemporaryDirectory() as folder:
        found = answers(launch_inputs(folder, record=record), folder)
    assert found["light"].answer == checks.FAIL, found["light"].reason
    assert found["footage"].answer == checks.FAIL, found["footage"].reason


def test_the_airlock_passes_in_metres_and_a_lingering_fog_fails():
    record = json.loads((REPO / "data/effects/airlock.json").read_text())
    with tempfile.TemporaryDirectory() as folder:
        found = answers(launch_inputs(folder, place="airlock"), folder)
    assert all(verdict.answer == checks.PASS for verdict in found.values()), {
        name: (verdict.reason, verdict.findings) for name, verdict in found.items()}
    emitter(record, "pump_fog")["lifetime"] = 8.0
    del record["no_light"]
    with tempfile.TemporaryDirectory() as folder:
        found = answers(launch_inputs(folder, record=record, place="airlock"), folder)
    assert found["footage"].answer == checks.FAIL and found["footage"].measures["fog gone 5 s into the pump-down"] > 0.05
    assert found["light"].answer == checks.UNKNOWN, found["light"].reason


def test_a_trail_baked_off_another_climb_fails():
    motion = json.loads((REPO / "data/motion/launch.json").read_text())
    with tempfile.TemporaryDirectory() as folder:
        inputs = launch_inputs(folder)
        out = pathlib.Path(folder) / "out"
        out.mkdir()
        faster = json.loads(json.dumps(motion))
        faster["motions"][0]["climb"]["push"] = 40.0
        effects.make(dict(inputs, motion=launch_inputs(folder, motion=faster)["motion"]), out, 0, {})
        verdict = effects.judge_attached(out, inputs, None)
    assert verdict.answer == checks.FAIL and verdict.measures["miss"] > 10, verdict.reason


def test_the_camp_drift_stays_out_of_its_domes_and_a_leak_fails():
    record = json.loads((REPO / "data/effects/camp.json").read_text())
    with tempfile.TemporaryDirectory() as folder:
        inputs = launch_inputs(folder, place="camp")
        out = pathlib.Path(folder) / "out"
        out.mkdir()
        effects.make(inputs, out, 0, {})
        assert effects.judge_outside(out, inputs, None).answer == checks.PASS
        leaking = pathlib.Path(folder) / "leaking"
        leaking.mkdir()
        effects.make(launch_inputs(folder, record=dict(record, interiors=[]), place="camp"), leaking, 0, {})
        verdict = effects.judge_outside(leaking, inputs, None)
    assert verdict.answer == checks.FAIL and verdict.measures["most inside"] > 0, verdict.reason


def test_a_point_ahead_lands_mid_picture_and_one_to_the_right_right_of_it():
    view = {"eye": [0.0, 10.0, 0.0], "aim": [-100.0, 10.0, 0.0], "fov": 90.0}
    size = (200, 100)
    assert look.projected(view, [-50.0, 10.0, 0.0], size) == (100.0, 50.0)
    right = look.projected(view, [-50.0, 10.0, -10.0], size)  # looking down -x, -z is to the right
    assert right[0] > 100.0 and abs(right[1] - 50.0) < 1e-9
    assert look.projected(view, [50.0, 10.0, 0.0], size) is None


def test_shown_and_lit_read_their_measures():
    with tempfile.TemporaryDirectory() as folder:
        out = pathlib.Path(folder)
        inputs = launch_inputs(folder)
        views = {"a-t003.0": {"seconds": 3.0, "changed": 0.05, "pad before": 0.02, "pad after": 0.2},
                 "a-t016.0": {"seconds": 16.0, "changed": 0.001, "pad before": 0.02, "pad after": 0.02}}
        (out / "measures.json").write_text(json.dumps({"lift": 4.0, "views": views}))
        assert look.judge_shown(out, inputs, None).answer == checks.FAIL
        assert look.judge_lit(out, inputs, None).answer == checks.PASS
        views["a-t003.0"]["pad after"] = 0.025
        (out / "measures.json").write_text(json.dumps({"lift": 4.0, "views": views}))
        assert look.judge_lit(out, inputs, None).answer == checks.FAIL


def test_the_launch_s_effect_times_follow_its_motion_record_s_lift_off():
    """Fault (2026-10-15): the record's seconds were set for the game's lift-off at 4 s, so with the motion record's 6 s
    the plume began 2 s early and the pad fire stopped at lift-off. Its seconds are now moments of the climb: moved
    with the lift, a number stays as it is, and a moment with no climb to read it from is refused."""
    record = json.loads((REPO / "data/effects/launch.json").read_text())
    motions = json.loads((REPO / "data/motion/launch.json").read_text())
    climb = motions["motions"][0]
    lift_off = climb["start"] + climb["climb"]["lift"]
    timed = {entry["name"]: entry for entry in effects.effect_layer.timed(record, motions)["effects"]}
    assert timed["plume"]["once"][0] == lift_off and timed["pad_fire"]["once"][1] == lift_off + 3.4
    assert timed["flame"]["starts"] == climb["start"]
    later = json.loads(json.dumps(motions))
    later["motions"][0]["climb"]["lift"] += 2.0
    moved = {entry["name"]: entry for entry in effects.effect_layer.timed(record, later)["effects"]}
    assert moved["plume"]["once"][0] == lift_off + 2.0 and moved["flame"]["starts"] == climb["start"]
    plain = {"effects": [{"name": "fog", "once": [1.0, 5.0]}]}
    assert effects.effect_layer.timed(plain, None)["effects"][0]["once"] == [1.0, 5.0]
    try:
        effects.effect_layer.timed(record, {"motions": []})
    except ValueError as error:
        assert "needs one climb" in str(error)
    else:
        raise AssertionError("a moment of a climb the motion record does not hold was read")


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
