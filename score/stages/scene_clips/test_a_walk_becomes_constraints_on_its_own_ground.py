"""The scene-made clips (score/stages/scene_clips): a walker's route through the scene, walked at its pace and checked
on the cast's geometry, becomes Kimodo constraints whose feet stand on the scene's own ground, and each gate fails
its break.

On a toy place made here (a floor at y = 0 from x = -1 to 2, three steps of 0.15 m up at x = 2, 2.3 and 2.6, a
landing at 0.45 m to x = 12, a wall at x = 10): a walker at the origin turned -90 degrees (cast.py's front is -z, so
it faces +X) walks a straight leg of the walking sentence's 5 s at 1.333 m/s; its route's ground climbs 0, 0.15,
0.30, 0.45 where the steps are (worked by hand from the boxes); each footfall's ground is the higher of the step under
its heel and its toe, read off the boxes by hand; in Kimodo's canonical frame the route starts at the origin heading
+Z; the feet are asked at their stances' middles every 17.25 frames from frame 24 (rounded, halves to even), right
first, and SOMA77's rest pose puts each sole (hips less 1.0052 m) on its ground; the footfalls' ground is not flat,
so Kimodo's post-processing is off. A walker whose cast path runs into the wall is cut 0.25 m (its body's radius) before it; one cut under two
seconds is left out. The machine's spec carries each clip's constraints, sentence, duration and post-processing.
Gates on written outputs (no Kimodo run): a clip on its route with its soles on their ground passes; hips 0.2 m off
fail `path held`; soles 0.1 m off fail `feet held`; a clip missing from the rig fails `made`. A machine whose set-up
failed (characters.py exits 0, its run folder's setup.log naming the step) stops the make with the row, the place,
the step and the log's last line, before any copy.

Breaks that turn each test red (each applied once and seen red, reverted, 2026-10-27):
- a_straight_leg_walks_the_way_the_walker_faces: legs_of's `at[0] - math.sin(turn) * length` made
  `at[0] + math.sin(turn) * length` (the walker walks backwards).
- the_route_climbs_the_steps: checked's `feet -= under["gap"]` dropped (every frame read from the start's feet).
- each_foot_stands_on_the_ground_under_it: footfalls' `max(ground_at(...))` made `min(ground_at(...))`.
- the_constraints_start_at_the_canonical_origin_heading_plus_z: canonical's `offset[:, 0] * sin + offset[:, 2] * cos`
  made `-offset[:, 0] * sin + offset[:, 2] * cos`.
- the_soles_are_asked_on_their_ground: constraints_of's `fall["ground"] + HIP_OVER_SOLE` made `fall["ground"]`.
- a_walk_into_the_wall_is_cut_before_it: checked's `if clash:` made `if False:`.
- the_duration_gives_kimodo_its_frames: seconds_of's `(frames + 0.5) / RATE` made `frames / RATE`.
- the_spec_carries_each_clips_constraints: make_folder's `"postprocess": plan["postprocess"]` made
  `"postprocess": True`.
- a_good_clip_passes_and_each_gate_fails_its_break: judge_path's `off > PATH_HELD` made `off > 1.0`; judge_feet's
  `off > FOOT_HELD` made `off > 1.0`; judge_made's `f"clip_{plan['clip']}" in held` made `True`.
- a_failed_set_up_is_named: make's `if not (work / "out" / "rig.npz").exists():` made `if False:` (a bare
  FileNotFoundError); failure_of's pattern `^setup step ` made `^setup ` (2026-10-31).

Run: .venv/bin/python -m pytest score/stages/scene_clips/test_a_walk_becomes_constraints_on_its_own_ground.py
"""
import contextlib
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


def tris(box):
    return box.triangles.copy()


def box(low, high):
    return trimesh.creation.box(bounds=[low, high])


@pytest.fixture(scope="module")
def found():
    """The toy place's solids as the cast's measure reads them: {name: triangles}."""
    solids = {"Structure/floor": tris(box([-1.0, -0.2, -2.0], [2.0, 0.0, 2.0]))}
    edges = [x for x, _ in STEPS] + [12.0]
    for number, ((x, top), end) in enumerate(zip(STEPS, edges[1:])):
        solids[f"Structure/step_{number}"] = tris(box([x, -0.2, -2.0], [end, top, 2.0]))
    solids["Structure/wall"] = tris(box([10.0, 0.0, -2.0], [10.3, 3.0, 2.0]))
    return solids


def step_top(x):
    """The toy's ground at x, from its boxes (worked apart from the code)."""
    return max([0.0] + [top for start, top in STEPS if x >= start])


WALKER = {"name": "walker_1", "doing": "walking", "at": [0.0, 0.0, 0.0], "turn": -90.0, "pace": 1.333}


@pytest.fixture(scope="module")
def plan(found):
    made, why = scene_clips.plan_of(WALKER, found)
    assert why is None
    return made


def test_the_pace_agrees_with_cast():
    sys.path.insert(0, str(REPO / "tools/characters"))
    import cast
    assert scene_clips.WALK_PACE == cast.WALK_PACE


def test_a_straight_leg_walks_the_way_the_walker_faces(plan):
    route = np.asarray(plan["route"])
    assert plan["frames"] == 151  # the 6.665 m leg is 5 s at 1.333 m/s: frames 0 to 150
    assert route[-1][0] == pytest.approx(6.665, abs=1e-3)
    assert np.abs(route[:, 2]).max() < 1e-9
    assert plan["placement"]["turn"] == pytest.approx(90.0)


def test_the_route_climbs_the_steps(plan):
    route = np.asarray(plan["route"])
    for x, ground in zip(route[:, 0], route[:, 1]):
        if min(abs(x - start) for start, _ in STEPS) > 0.02:
            assert ground == pytest.approx(step_top(x), abs=1e-6)
    assert route[-1][1] == pytest.approx(0.45)


def test_each_foot_stands_on_the_ground_under_it(plan):
    falls = plan["footfalls"]
    assert [fall["frame"] for fall in falls] == [24, 41, 58, 76, 93, 110, 128]  # 24 + 17.25 k, halves to even
    assert [fall["side"] for fall in falls] == ["right", "left"] * 3 + ["right"]
    for fall in falls:
        heel, toe = fall["hips"][0] - 0.0169, fall["hips"][0] + 0.1806
        assert fall["ground"] == pytest.approx(max(step_top(heel), step_top(toe)), abs=1e-6)
    assert plan["relief"] == pytest.approx(0.45) and plan["postprocess"] is False


def test_the_constraints_start_at_the_canonical_origin_heading_plus_z(plan):
    root2d = plan["constraints"][0]
    assert root2d["type"] == "root2d" and root2d["frame_indices"] == list(range(151))
    path = np.asarray(root2d["smooth_root_2d"])
    assert path[0] == pytest.approx([0.0, 0.0])
    assert path[-1] == pytest.approx([0.0, 6.665], abs=1e-3)  # the +X walk is +Z in Kimodo's frame
    assert np.asarray(root2d["global_root_heading"]) == pytest.approx(np.tile([1.0, 0.0], (151, 1)))


def test_the_soles_are_asked_on_their_ground(plan):
    for constraint in plan["constraints"][1:]:
        side = constraint["type"].removesuffix("-foot")
        falls = [fall for fall in plan["footfalls"] if fall["side"] == side]
        assert constraint["frame_indices"] == [fall["frame"] for fall in falls]
        hips = np.asarray(constraint["root_positions"])
        assert hips[:, 1] - 1.0052 == pytest.approx([fall["ground"] for fall in falls])  # the start's ground is 0
        assert hips[:, 2] == pytest.approx([fall["hips"][0] for fall in falls], abs=1e-4)
        poses = np.asarray(constraint["local_joints_rot"])
        assert poses.shape == (len(falls), 77, 3) and not poses.any()  # rest pose, no turn: the walk heads +Z


def test_a_walk_into_the_wall_is_cut_before_it(found):
    walker = dict(WALKER, name="walker_2", path=[[0.0, 0.0, 0.0], [12.0, 0.45, 0.0]])
    made, why = scene_clips.plan_of(walker, found)
    assert "runs into Structure/wall" in made["cut"]
    assert np.asarray(made["route"])[-1][0] == pytest.approx(10.0 - 0.25, abs=1.333 / 30)
    short = dict(WALKER, name="walker_3", at=[8.5, 0.45, 0.0])
    made, why = scene_clips.plan_of(short, found)
    assert made is None and "under two seconds" in why


def test_the_duration_gives_kimodo_its_frames():
    for frames in range(60, 301):
        assert int(float(scene_clips.seconds_of(frames)) * scene_clips.RATE) == frames


def test_the_spec_carries_each_clips_constraints(plan, tmp_path):
    flat = dict(plan, clip="scene_flat", postprocess=True)
    folder = scene_clips.make_folder(tmp_path / "make", [plan, flat], "toy")
    spec = json.loads((folder / "in/spec.json").read_text())
    assert spec["program"] == "scene_clips.py" and spec["clips"] == ["scene_walker_1", "scene_flat"]
    sys.path.insert(0, str(REPO / "tools/characters/people"))
    import clips
    clip = spec["scene clips"]["scene_walker_1"]
    assert clip["sentence"] == clips.SENTENCES["walking"][0] and clip["seconds"] == "5.0500"
    assert clip["postprocess"] is False and spec["scene clips"]["scene_flat"]["postprocess"] is True
    assert json.loads((folder / clip["constraints"]).read_text()) == plan["constraints"]


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


def verdicts(out):
    return {check.name: check.judge(out, {}, {}).answer for check in scene_clips.CHECKS}


def test_a_good_clip_passes_and_each_gate_fails_its_break(plan, tmp_path):
    assert set(verdicts(written(tmp_path, plan)).values()) == {"pass"}
    assert verdicts(written(tmp_path, plan, hips_off=0.2))["path held"] == "fail"
    assert verdicts(written(tmp_path, plan, sole_off=0.1))["feet held"] == "fail"
    assert verdicts(written(tmp_path, plan, in_rig=False))["made"] == "fail"


SETUP_LOG = """downloading uv 0.13.6 x86_64-unknown-linux-gnu
setup step sam3dbody failed:
No python3-pip. Installing all missing dependencies now ...
scripts/setup.sh: line 61: sudo: command not found
"""


def test_a_failed_set_up_is_named(plan, tmp_path, monkeypatch):
    run = tmp_path / "cloud" / "characters-1-2"

    def failed_machine(work, who):
        (run / "machine-1").mkdir(parents=True)
        (run / "machine-1" / "setup.log").write_text(SETUP_LOG)
        return run

    monkeypatch.setattr(scene_clips.layer_base, "built", lambda inputs: contextlib.nullcontext(tmp_path))
    monkeypatch.setattr(scene_clips.measure, "solids", lambda *args: {})
    monkeypatch.setattr("score.stages.cast.made_ground", lambda *args: None)
    monkeypatch.setattr(scene_clips, "plan_of", lambda single, found: (plan, None))
    monkeypatch.setattr(scene_clips, "on_machine", failed_machine)
    (tmp_path / "cast").mkdir()
    (tmp_path / "cast" / "cast.json").write_text(json.dumps({"place": "camp", "characters": [WALKER]}))
    with pytest.raises(RuntimeError) as failure:
        scene_clips.make({"cast": str(tmp_path / "cast")}, tmp_path, 0, {})
    assert str(failure.value).startswith("scene-clips@camp: no rig.npz came back: the set-up step sam3dbody failed "
                                         "(scripts/setup.sh: line 61: sudo: command not found; ")
