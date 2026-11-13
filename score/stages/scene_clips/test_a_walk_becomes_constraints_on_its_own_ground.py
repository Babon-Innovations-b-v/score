"""The scene-made clips (score/stages/scene_clips): a walker's route through the scene, walked at its pace and checked
on the cast's geometry, becomes Kimodo constraints whose feet stand on the scene's own ground, and each gate fails
its break.

Three toy worlds made here, each with its ground worked by hand from its boxes. The steps: a floor at y = 0 from
x = -1 to 2, three steps of 0.15 m up at x = 2, 2.3 and 2.6, a landing at 0.45 m to x = 12, a wall at x = 10. The
flight: a floor under x < 0, six 0.3 m treads 0.15 m apart from x = 0, a landing at 0.9 m from x = 1.8. The kerb: a
street at y = 0 and a 0.2 m kerb to x = 0.3. The walkers are rows of one table, each planned through `plan_of` and
held to the same rules:
- a walker at the origin turned -90 degrees (cast.py's front is -z, so it faces +X) walks a straight leg of the
  walking sentence's 5 s at 1.333 m/s; its route's ground climbs 0, 0.15, 0.30, 0.45 where the steps are; each
  footfall's ground is the higher of the step under its heel and its toe; the feet are asked at their stances' middles
  every 17.25 frames from frame 24 (rounded, halves to even), right first; the footfalls' ground is not flat, so
  Kimodo's post-processing is off.
- a climber (cast.on_stairs' `stairs`) walks its own flight from its first tread's middle to its last's, one tread a
  stance (its pace the run every 17.25 frames), each foot asked on the next tread up, with the stairs' own sentence;
  a descender walks it down, and the lowest ground it walks is Kimodo's floor (its `lift`), so no sole is asked under
  it, and the machine lowers the clip back onto its start's ground.
- a walk off the kerb before its first stance stands every stance on the street, its start's floor not.
- a walker whose cast path runs into the wall is cut 0.25 m (its body's radius) before it; one cut under two seconds
  is left out.
For every planned walker, in Kimodo's canonical frame the route starts at the origin heading +Z, and SOMA77's rest
pose puts each sole (hips less 1.0052 m) on its ground less its start's ground plus its lift, never under Kimodo's
floor. The machine's spec carries each clip's constraints, sentence, duration, post-processing and lift.
Gates on written outputs (no Kimodo run): a clip on its route with its soles on their ground passes; hips 0.2 m off
fail `path held`; soles 0.1 m off fail `feet held`; a clip missing from the rig fails `made`. A machine whose set-up
failed (characters.py exits 0, its run folder's setup.log naming the step) stops the make with the row, the place,
the step and the log's last line, before any copy.

Breaks that turn the test red (each applied once and seen red, reverted; first 2026-10-27, again on the fold into one
test 2026-11-13), by the behaviour each one breaks:
- a straight leg walks the way the walker faces: legs_of's `at[0] - math.sin(turn) * length` made
  `at[0] + math.sin(turn) * length` (the walker walks backwards).
- the route climbs the steps: checked's `feet -= under["gap"]` dropped (every frame read from the start's feet);
  pace_of's climber `float(single["stairs"]["run"]) * RATE / STEP_FRAMES` made the cast's pace (2026-11-04: its
  feet land three treads apart, and its 1.5 m flight walks under two seconds).
- each foot stands on the ground under it: footfalls' `max(ground_at(...))` made `min(ground_at(...))`; plan_of's
  `[grounds[0]] +` dropped from the relief's heights (a walk off a kerb post-processed onto the kerb's floor,
  2026-11-10).
- the soles are asked on their ground above Kimodo's floor (2026-11-11): constraints_of's `+ [0.0, lift, 0.0]`
  dropped (the descender's soles asked down to -0.6 m, under Kimodo's floor: the stairwell's woman, 0.36 m off); the
  machine's `lowered` `arrays[key][..., 1] -= lift` made `+= lift`; make_folder's `"lift": plan["lift"]` made
  `"lift": 0.0`; constraints_of's `fall["ground"] + HIP_OVER_SOLE` made `fall["ground"]`.
- the constraints start at the canonical origin heading +Z: canonical's `offset[:, 0] * sin + offset[:, 2] * cos`
  made `-offset[:, 0] * sin + offset[:, 2] * cos`.
- a walk into the wall is cut before it: checked's `if clash:` made `if False:`.
- the duration gives Kimodo its frames: seconds_of's `(frames + 0.5) / RATE` made `frames / RATE`.
- the spec carries each clip's constraints: make_folder's `"postprocess": plan["postprocess"]` made
  `"postprocess": True`.
- a good clip passes and each gate fails its break: judge_path's `off > PATH_HELD` made `off > 1.0`; judge_feet's
  `off > FOOT_HELD` made `off > 1.0`; judge_made's `f"clip_{plan['clip']}" in held` made `True`.
- a failed set-up is named: make's `if not (work / "out" / "rig.npz").exists():` made `if False:` (a bare
  FileNotFoundError); failure_of's pattern `^setup step ` made `^setup ` (2026-10-31).

Run: .venv/bin/python -m pytest score/stages/scene_clips/test_a_walk_becomes_constraints_on_its_own_ground.py
"""
import contextlib
import importlib
import json
import math
import pathlib
import sys

import numpy as np
import pytest
import trimesh

from score.stages import scene_clips

REPO = pathlib.Path(__file__).resolve().parents[3]
STEPS = ((2.0, 0.15), (2.3, 0.30), (2.6, 0.45))  # (x where it begins, its top)
HEEL, TOE = 0.0169, 0.1806  # the sole behind and ahead of the hips, along the walk (SOMA77's rest pose)


def tris(low, high):
    return trimesh.creation.box(bounds=[low, high]).triangles.copy()


def steps_world():
    """The steps' solids as the cast's measure reads them: {name: triangles}."""
    solids = {"Structure/floor": tris([-1.0, -0.2, -2.0], [2.0, 0.0, 2.0])}
    edges = [x for x, _ in STEPS] + [12.0]
    for number, ((x, top), end) in enumerate(zip(STEPS, edges[1:])):
        solids[f"Structure/step_{number}"] = tris([x, -0.2, -2.0], [end, top, 2.0])
    solids["Structure/wall"] = tris([10.0, 0.0, -2.0], [10.3, 3.0, 2.0])
    return solids


def flight_world():
    """A floor, a flight of six 0.3 m treads 0.15 m apart, a landing at 0.9 m."""
    solids = {"Structure/floor": tris([-2.0, -0.2, -2.0], [0.0, 0.0, 2.0]),
              "Structure/landing": tris([1.8, -0.2, -2.0], [4.0, 0.9, 2.0])}
    for step in range(6):
        solids[f"Structure/step_{step}"] = tris([0.3 * step, -0.2, -2.0], [0.3 * (step + 1), 0.15 * (step + 1), 2.0])
    return solids


def kerb_world():
    return {"Structure/street": tris([-1.0, -0.2, -2.0], [8.0, 0.0, 2.0]),
            "Structure/kerb": tris([-1.0, -0.2, -2.0], [0.3, 0.2, 2.0])}


def steps_ground(x):
    """The steps' ground at x, from its boxes (worked apart from the code)."""
    return max([0.0] + [top for start, top in STEPS if x >= start])


def kerb_ground(x):
    return 0.2 if x < 0.3 else 0.0


WORLDS = {"steps": (steps_world(), steps_ground, [start for start, _ in STEPS]),
          "flight": (flight_world(), None, []), "kerb": (kerb_world(), kerb_ground, [0.3])}
WALKER = {"name": "walker_1", "doing": "walking", "at": [0.0, 0.0, 0.0], "turn": -90.0, "pace": 1.333}

# (id, world, walker, what its plan must be); "ground" on a flat walk is read off the world's ground by hand under each
# footfall's heel and toe, "grounds" on a stair walk is the tread each foot is asked on.
WALKERS = [
    ("walker on the steps", "steps", WALKER,
     {"frames": 151, "end": (6.665, 1e-3), "turn": 90.0, "lift": 0.0, "relief": 0.45, "postprocess": False,
      "falls": [24, 41, 58, 76, 93, 110, 128], "sides": ["right", "left"] * 3 + ["right"], "top": 0.45}),
    ("climber", "flight",
     {"name": "man", "doing": "walking", "at": [0.15, 0.15, 0.0], "turn": -90.0, "pace": 1.333,
      "stairs": {"way": "up", "flight": "stair_1", "to": [1.65, 0.9, 0.0], "rise": 0.15, "run": 0.3}},
     {"pace": 0.3 * 30 / 17.25, "end": (1.65, 0.01), "top": 0.9, "falls": [24, 41, 58, 76],
      "grounds": [0.45, 0.6, 0.75, 0.9], "sentence": scene_clips.STAIRS["up"], "postprocess": False, "lift": 0.0}),
    ("descender", "flight",
     {"name": "woman", "doing": "walking", "at": [1.65, 0.9, 0.0], "turn": 90.0,
      "stairs": {"way": "down", "flight": "stair_1", "to": [0.15, 0.15, 0.0], "rise": 0.15, "run": 0.3}},
     {"lift": 0.75, "grounds": [0.75, 0.6, 0.45, 0.3]}),
    ("walk off a kerb", "kerb", {"name": "man", "doing": "walking", "at": [0.0, 0.2, 0.0], "turn": -90.0,
                                 "pace": 1.333},
     {"relief": 0.2, "postprocess": False, "grounds": [0.0] * 7}),
    ("walk into the wall", "steps", dict(WALKER, name="walker_2", path=[[0.0, 0.0, 0.0], [12.0, 0.45, 0.0]]),
     {"cut": "runs into Structure/wall", "end": (10.0 - 0.25, 1.333 / 30)}),
    ("cut under two seconds", "steps", dict(WALKER, name="walker_3", at=[8.5, 0.45, 0.0]),
     {"left out": "under two seconds"}),
]

# (id, how the written output is off, the gate that fails; None: every gate passes)
GATES = [("good clip", {}, None), ("hips 0.2 m off", {"hips_off": 0.2}, "path held"),
         ("soles 0.1 m off", {"sole_off": 0.1}, "feet held"), ("clip missing from the rig", {"in_rig": False}, "made")]

SETUP_LOG = """downloading uv 0.13.6 x86_64-unknown-linux-gnu
setup step sam3dbody failed:
No python3-pip. Installing all missing dependencies now ...
scripts/setup.sh: line 61: sudo: command not found
"""


def planned():
    """Every walker of the table planned on its world: {id: (plan or None, why)}."""
    return {name: scene_clips.plan_of(single, WORLDS[world][0]) for name, world, single, _ in WALKERS}


def held_to_its_ground(name, world, single, plan, expect):
    """The planned walk against its world's hand-worked ground and the row's expected outcome."""
    _, ground, edges = WORLDS[world]
    route, falls = np.asarray(plan["route"]), plan["footfalls"]
    facing = -math.sin(math.radians(single["turn"]))  # +1 walks +X, -1 walks -X
    start = np.asarray(single["at"])
    assert route[0] == pytest.approx(start, abs=1e-9), name
    assert np.abs(route[:, 2]).max() < 1e-9, name
    if "end" in expect:
        assert route[-1][0] == pytest.approx(expect["end"][0], abs=expect["end"][1]), name
    if "top" in expect:
        assert route[-1][1] == pytest.approx(expect["top"]), name
    for key in ("frames", "lift", "relief", "pace"):
        if key in expect:
            assert plan[key] == pytest.approx(expect[key]), (name, key, plan[key])
    for key in ("postprocess", "sentence"):
        if key in expect:
            assert plan[key] == expect[key], (name, key, plan[key])
    if "turn" in expect:
        assert plan["placement"]["turn"] == pytest.approx(expect["turn"]), name
    if "falls" in expect:
        assert [fall["frame"] for fall in falls] == expect["falls"], name  # 24 + 17.25 k, halves to even
    if "sides" in expect:
        assert [fall["side"] for fall in falls] == expect["sides"], name
    if ground is not None:
        for x, height in zip(route[:, 0], route[:, 1]):
            if min([abs(x - edge) for edge in edges] or [1.0]) > 0.02:
                assert height == pytest.approx(ground(x), abs=1e-6), (name, x)
        for fall in falls:
            heel, toe = fall["hips"][0] - facing * HEEL, fall["hips"][0] + facing * TOE
            assert fall["ground"] == pytest.approx(max(ground(heel), ground(toe)), abs=1e-6), (name, fall)
    if "grounds" in expect:
        assert [fall["ground"] for fall in falls] == pytest.approx(expect["grounds"]), name


def asked_on_its_ground(name, single, plan):
    """Kimodo's constraints: the canonical root from the origin heading +Z, each sole on its ground."""
    root2d = plan["constraints"][0]
    reach = abs(plan["route"][-1][0] - single["at"][0])
    assert root2d["type"] == "root2d" and root2d["frame_indices"] == list(range(plan["frames"])), name
    path = np.asarray(root2d["smooth_root_2d"])
    assert path[0] == pytest.approx([0.0, 0.0]), name
    assert path[-1] == pytest.approx([0.0, reach], abs=1e-3), name  # the walk is +Z in Kimodo's frame
    assert np.asarray(root2d["global_root_heading"]) == pytest.approx(np.tile([1.0, 0.0], (plan["frames"], 1))), name
    start_ground = plan["route"][0][1]
    for constraint in plan["constraints"][1:]:
        side = constraint["type"].removesuffix("-foot")
        falls = [fall for fall in plan["footfalls"] if fall["side"] == side]
        assert constraint["frame_indices"] == [fall["frame"] for fall in falls], name
        hips = np.asarray(constraint["root_positions"])
        soles = hips[:, 1] - 1.0052
        assert soles == pytest.approx([fall["ground"] - start_ground + plan["lift"] for fall in falls]), name
        assert soles.min() >= 0.0, name  # never under Kimodo's floor
        assert hips[:, 2] == pytest.approx([abs(fall["hips"][0] - single["at"][0]) for fall in falls], abs=1e-4), name
        poses = np.asarray(constraint["local_joints_rot"])
        assert poses.shape == (len(falls), 77, 3) and not poses.any(), name  # rest pose: the walk heads +Z


def written(tmp_path, plan, hips_off=0.0, sole_off=0.0, in_rig=True):
    """A scene-clips output as the make writes it, its motion on its route with its soles on their ground."""
    out = tmp_path / f"out-{hips_off}-{sole_off}-{in_rig}"
    (out / "motions").mkdir(parents=True)
    route = scene_clips.canonical(plan["route"], plan["placement"]["origin"], math.radians(plan["placement"]["turn"]))
    roots = route + [hips_off, 1.0, 0.0]
    joints = np.zeros((len(route), 77, 3))
    for fall in plan["footfalls"]:
        joints[fall["frame"], scene_clips.TOE_END[fall["side"]], 1] = fall["ground"] + sole_off
    np.savez(out / "motions" / f"{plan['clip']}.npz", root_positions=roots, posed_joints=joints)
    (out / "motions" / f"{plan['clip']}.record.json").write_text("{}")
    np.savez(out / "rig.npz", **({f"clip_{plan['clip']}": np.zeros(1)} if in_rig else {"names": np.zeros(1)}))
    (out / scene_clips.RECORD).write_text(json.dumps({"place": "toy", "clips": [plan], "left out": []}))
    return out


def test_a_walk_becomes_constraints_on_its_own_ground(tmp_path, monkeypatch):
    sys.path.insert(0, str(REPO / "tools/characters"))
    import cast
    assert scene_clips.WALK_PACE == cast.WALK_PACE
    for frames in range(60, 301):
        assert int(float(scene_clips.seconds_of(frames)) * scene_clips.RATE) == frames, frames

    plans = planned()
    for name, world, single, expect in WALKERS:
        plan, why = plans[name]
        if "left out" in expect:
            assert plan is None and expect["left out"] in why, (name, why)
            continue
        assert why is None, (name, why)
        if "cut" in expect:
            assert expect["cut"] in plan["cut"], (name, plan["cut"])
        held_to_its_ground(name, world, single, plan, expect)
        asked_on_its_ground(name, single, plan)

    # the machine's spec carries each clip as planned; the descender's lift comes back off Kimodo's clip on the machine
    walker, down = plans["walker on the steps"][0], plans["descender"][0]
    flat = dict(walker, clip="scene_flat", postprocess=True)
    folder = scene_clips.make_folder(tmp_path / "make", [walker, flat, down], "toy")
    spec = json.loads((folder / "in/spec.json").read_text())
    assert spec["program"] == "scene_clips.py" and spec["clips"] == ["scene_walker_1", "scene_flat", "scene_woman"]
    sys.path.insert(0, str(REPO / "tools/characters/people"))
    import clips as people_clips
    clips = spec["scene clips"]
    assert clips["scene_walker_1"]["sentence"] == people_clips.SENTENCES["walking"][0]
    assert clips["scene_walker_1"]["seconds"] == "5.0500"
    assert clips["scene_walker_1"]["postprocess"] is False and clips["scene_flat"]["postprocess"] is True
    assert json.loads((folder / clips["scene_walker_1"]["constraints"]).read_text()) == walker["constraints"]
    sys.path.insert(0, str(REPO / "tools/characters/clips"))
    machine = importlib.import_module("scene_clips")
    motion = tmp_path / "woman.npz"  # Kimodo's first stance as asked: its sole 0.6 over its floor
    np.savez(motion, root_positions=np.array([[0.0, 1.6052, 0.0]]), smooth_root_pos=np.array([[0.0, 1.6052, 0.0]]),
             posed_joints=np.full((1, 77, 3), 0.6), foot_contacts=np.ones((1, 6), dtype=bool))
    machine.lowered(motion, clips["scene_woman"]["lift"])
    with np.load(motion) as held:
        assert held["root_positions"][0, 1] == pytest.approx(0.8552) and held["foot_contacts"].all()
        assert held["smooth_root_pos"][0, 1] == pytest.approx(0.8552)
        first = dict(down, footfalls=[dict(down["footfalls"][0], frame=0)])  # asked 0.15 under her start's ground
        assert scene_clips.feet_off(first, {"posed_joints": held["posed_joints"]}) == pytest.approx(0.0, abs=1e-6)

    for name, off, failing in GATES:
        out = written(tmp_path, walker, **off)
        verdicts = {check.name: check.judge(out, {}, {}).answer for check in scene_clips.CHECKS}
        assert verdicts == {gate: "fail" if gate == failing else "pass" for gate in verdicts}, (name, verdicts)

    # a machine whose set-up failed stops the make, naming the step and the log's last line
    run = tmp_path / "cloud" / "characters-1-2"

    def failed_machine(work, who):
        (run / "machine-1").mkdir(parents=True)
        (run / "machine-1" / "setup.log").write_text(SETUP_LOG)
        return run

    monkeypatch.setattr(scene_clips.layer_base, "built", lambda inputs: contextlib.nullcontext(tmp_path))
    monkeypatch.setattr(scene_clips.measure, "solids", lambda *args: WORLDS["steps"][0])
    monkeypatch.setattr("score.stages.cast.made_ground", lambda *args: None)
    monkeypatch.setattr(scene_clips, "on_machine", failed_machine)
    (tmp_path / "cast").mkdir()
    (tmp_path / "cast" / "cast.json").write_text(json.dumps({"place": "camp", "characters": [WALKER]}))
    with pytest.raises(RuntimeError) as failure:
        scene_clips.make({"cast": str(tmp_path / "cast")}, tmp_path / "made", 0, {})
    assert str(failure.value).startswith("scene-clips@camp: no rig.npz came back: the set-up step sam3dbody failed "
                                         "(scripts/setup.sh: line 61: sudo: command not found; ")
