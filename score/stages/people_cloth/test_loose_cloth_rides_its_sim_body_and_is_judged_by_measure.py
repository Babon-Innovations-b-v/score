"""The people cloth stage (score/stages/people_cloth): a garment's loose points are the ones the shell gate calls loose,
its seam-split points one cloth, the person's skeleton plays the sim body's turns on its own bones, the skin carries a
point by its weights, the body surface is cut one piece a segment in its segment's frame, the cloth values come from
the table by plane stress, and each gate fails its break.

On toys made here: a rig of three points with shell offsets 0.01, 0.06 and 0.2 m (OFFSET_MOST 0.05: the last two
loose); a square of two triangles with one corner given twice (welded to four points, a face that lost a corner
dropped); a two-joint skeleton (Hips at 1 m, Shin 0.5 m under it) whose sim poses are its bind (it stays at its bind)
and then turned 90 degrees at the Hips about up (the shin's foot, 0.5 m under, stays under; a point 0.1 m along x off
the Hips goes to -0.1 m along z); a cotton row (E 30.54 N/m, nu 0.3058: lambda 10.3026 N/m, worked by hand). On runs
written here (no engine): a good run passes every gate, a loose point 1 cm inside the body fails `through`, an edge 20%
past its built and skin length fails `stretch` while one the skin itself draws long does not, nor one at its built
length where the skin draws it short, cloth still sliding
0.05 m/s on a standing body fails `rests`. The make with no dressed body names each person left out and writes an
empty layer. Newton itself is not run here (its kernels compile for a minute); the real run's numbers are on its
commit.

Breaks that turn each check red (each applied once and seen red, reverted, 2026-10-27):
- loose_points_are_the_shell_gates_loose_cloth: loose_of's `> limit` made `>= 0.0`.
- seam_split_points_are_one_cloth: welded's `index[faces]` made `faces`.
- the_skeleton_plays_the_sims_turns_on_its_own_bones: person_worlds' `np.swapaxes(turns[:, segment[parent]], 1, 2) @`
  dropped (a segment's world turn taken as its turn against its parent).
- the_skin_carries_a_point_by_its_weights: skinned's `@ np.linalg.inv(np.asarray(bind, dtype=float))[None]` dropped.
- the_body_is_cut_one_piece_a_segment: pieces' `points[used] @ frame[:3, :3].T + frame[:3, 3]` made `points[used]`.
- the_cloth_values_come_from_the_table: material_of's `/ (1.0 - poisson ** 2)` dropped.
- a_good_run_passes_and_each_gate_fails_its_break: judge_through's `> limit` made `> 1.0`; judge_stretch's
  `> STRETCH_MOST` made `> 1.0`; stretches' `np.maximum(built[None], riding)` made `riding`, and made `built[None]`
  (each seen red on its own); judge_rests' `> REST_MOST` made `> 1.0`.
- the_make_names_each_person_left_out: make's `left_out.append(...)` dropped.

Run: PROPS_HOME=$(mktemp -d) .venv/bin/python -m pytest score/stages/people_cloth/test_loose_cloth_rides_its_sim_body_and_is_judged_by_measure.py
"""
import json

import numpy as np
from pxr import Usd

from score import checks
from score.stages import people_cloth
from score.stages.people_bodies import bodies


def test_loose_points_are_the_shell_gates_loose_cloth():
    rig = {"points": np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [2.0, 0.0, 0.0]]),
           "shell_offsets": np.array([0.01, 0.06, 0.2])}
    found = people_cloth.loose_of(np.array([[0.0, 0.01, 0.0], [1.01, 0.0, 0.0], [2.0, 0.0, 0.02]]), rig,
                                  bodies.OFFSET_MOST)
    assert found.tolist() == [False, True, True]


def test_seam_split_points_are_one_cloth():
    points = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [1.0, 1.0, 0.0], [1.0, 0.0, 0.0]])
    faces = np.array([[0, 1, 2], [4, 3, 2], [1, 4, 2]])
    found, joined, index = people_cloth.welded(points, faces)
    assert len(found) == 4
    assert index[1] == index[4]
    assert len(joined) == 2 and np.allclose(found[joined[1]], points[[4, 3, 2]])


def skeleton():
    """Root at the floor, Hips 1 m over it, Shin 0.5 m under the Hips (kept: Hips, Shin)."""
    bind = np.repeat(np.eye(4)[None], 3, axis=0)
    bind[1, 1, 3], bind[2, 1, 3] = 1.0, 0.5
    return {"names": np.array(["Root", "Hips", "Shin"]), "parents": np.array([-1, 0, 1]), "bind": bind}


def poses_of(worlds):
    from scipy.spatial.transform import Rotation
    return [[[*world[:3, 3], *Rotation.from_matrix(world[:3, :3]).as_quat()] for world in frame] for frame in worlds]


def test_the_skeleton_plays_the_sims_turns_on_its_own_bones():
    rig = skeleton()
    still = people_cloth.person_worlds(rig, [1, 2], poses_of([rig["bind"][[1, 2]]]))
    assert np.allclose(still[0], rig["bind"])
    turned = rig["bind"][[1, 2]].copy()
    quarter = np.array([[0.0, 0.0, 1.0], [0.0, 1.0, 0.0], [-1.0, 0.0, 0.0]])  # 90 degrees about up
    turned[:, :3, :3] = quarter
    turned[0, :3, 3], turned[1, :3, 3] = (0.0, 1.0, 0.0), (0.0, 0.5, 0.0)
    worlds = people_cloth.person_worlds(rig, [1, 2], poses_of([turned]))
    assert np.allclose(worlds[0, 2, :3, 3], (0.0, 0.5, 0.0))
    assert np.allclose(worlds[0, 2, :3, :3], quarter)
    # the shin turned with its parent and no further: its turn against the hips is none
    assert np.allclose(worlds[0, 1, :3, :3].T @ worlds[0, 2, :3, :3], np.eye(3))


def test_the_skin_carries_a_point_by_its_weights():
    rig = skeleton()
    worlds = rig["bind"][None].copy()
    worlds[0, 1, :3, :3] = np.array([[0.0, 0.0, 1.0], [0.0, 1.0, 0.0], [-1.0, 0.0, 0.0]])
    worlds[0, 2] = worlds[0, 1] @ np.linalg.inv(rig["bind"][1]) @ rig["bind"][2]
    point = np.array([[0.1, 1.0, 0.0]])
    found = people_cloth.skinned(point, np.array([[1, 2]]), np.array([[1.0, 0.0]]), worlds, rig["bind"])
    assert np.allclose(found[0, 0], (0.0, 1.0, -0.1))
    half = people_cloth.skinned(point, np.array([[1, 0]]), np.array([[0.5, 0.5]]), worlds, rig["bind"])
    assert np.allclose(half[0, 0], (0.05, 1.0, -0.05))
    assert np.allclose(people_cloth.skinned(point, np.array([[1, 2]]), np.array([[1.0, 0.0]]), rig["bind"][None],
                                            rig["bind"])[0], point)


def test_the_body_is_cut_one_piece_a_segment():
    rig = skeleton()
    points = np.array([[0.0, 1.0, 0.0], [0.1, 1.0, 0.0], [0.0, 1.1, 0.0], [0.0, 0.5, 0.0], [0.1, 0.5, 0.0],
                       [0.0, 0.4, 0.0]])
    faces = np.array([[0, 1, 2], [3, 4, 5]])
    weights = np.zeros((6, 3))
    weights[:3, 1], weights[3:, 2] = 1.0, 1.0
    found = people_cloth.pieces(points, faces, weights, [1, 2], [1, 1, 2], rig["bind"])
    assert len(found) == 2 and len(found[0]["faces"]) == 1 and len(found[1]["faces"]) == 1
    assert np.allclose(sorted(map(tuple, found[0]["points"])), sorted([(0, 0, 0), (0.1, 0, 0), (0, 0.1, 0)]))
    assert np.allclose(sorted(map(tuple, found[1]["points"])), sorted([(0, 0, 0), (0.1, 0, 0), (0, -0.1, 0)]))


def test_the_cloth_values_come_from_the_table():
    row = json.loads((people_cloth.REPO / "data/physics/cloth.json").read_text())["recipes"]["cloth"]
    points = np.array([[0.0, 0.0, 0.0], [0.01, 0.0, 0.0], [0.0, 0.01, 0.0]])
    found = people_cloth.material_of(row, points, np.array([[0, 1, 2]]), 0.003)
    assert found["mu"] == row["shear"] == 4.971
    assert round(found["lambda"], 4) == 10.3026
    mean_edge = (0.01 + 0.01 + 0.01 * 2 ** 0.5) / 3
    assert np.isclose(found["bending"], row["bending"] / mean_edge)
    assert found["radius"] == 0.0015 and found["density"] == 0.224


def written_run(folder, deep=0.0, stretch=0.02, restless=0.001):
    """A people_cloth.json as the make writes it, one standing and one walking person."""
    def part(clip):
        found = {"deepest m": deep, "frames deeper than thickness": int(deep > 0.003), "largest stretch": stretch,
                 "largest drift off skin m": 0.01}
        if clip in people_cloth.STILL:
            found["restless m/s"] = restless
        return {"cloth_5": {"node": "made", "points": 10, "loose": 3, "measures": found}}
    record = {"place": "toy", "engine": "written", "seconds": 0.0, "left out": [],
              "people": {"stander": {"clip": "standing", "parts": part("standing"), "left out": []},
                         "walker": {"clip": "walking", "parts": part("walking"), "left out": []}}}
    (folder / people_cloth.RECORD).write_text(json.dumps(record))
    return folder


def answers(folder):
    return {check.name: check.judge(folder, {}, {}).answer for check in people_cloth.CHECKS}


def test_a_good_run_passes_and_each_gate_fails_its_break(tmp_path):
    for name, made in (("good", {}), ("through", {"deep": 0.01}), ("stretch", {"stretch": 0.2}),
                       ("rests", {"restless": 0.05})):
        folder = tmp_path / name
        folder.mkdir()
        found = answers(written_run(folder, **made))
        failed = {check for check, answer in found.items() if answer == checks.FAIL}
        assert failed == (set() if name == "good" else {name}), name
    rest = np.array([[0.0, 0.0, 0.0], [0.01, 0.0, 0.0], [0.0, 0.01, 0.0]])
    free = np.array([False, True, False])
    faces = np.array([[0, 1, 2]])
    skin_long = np.array([[[0.0, 0.0, 0.0], [0.02, 0.0, 0.0], [0.0, 0.01, 0.0]]])
    assert people_cloth.stretches(skin_long, rest, skin_long, faces, free)[0] < 1e-9
    pulled = np.array([[[0.0, 0.0, 0.0], [0.012, 0.0, 0.0], [0.0, 0.01, 0.0]]])
    assert np.isclose(people_cloth.stretches(pulled, rest, rest[None], faces, free)[0], 0.2)
    skin_short = np.array([[[0.0, 0.0, 0.0], [0.008, 0.0, 0.0], [0.0, 0.01, 0.0]]])
    assert people_cloth.stretches(rest[None], rest, skin_short, faces, free)[0] < 1e-9


def test_the_make_names_each_person_left_out(tmp_path):
    sim, cast, out = tmp_path / "sim", tmp_path / "cast", tmp_path / "out"
    for folder in (sim, cast, out):
        folder.mkdir()
    (sim / "sim_bodies.json").write_text(json.dumps({"rate": 30.0, "gravity": 9.81, "bodies": {
        "nev": {"clip": "standing", "measures": {}}}}))
    (cast / "cast.json").write_text(json.dumps({"place": "toy", "characters": [
        {"name": "nev", "look": "astronaut/made", "doing": "standing"}], "crowd": None}))
    np.savez(tmp_path / "rig.npz", weights=np.zeros((1, 1)))
    inputs = {"sim-body": str(sim), "cast": str(cast), "people-clips-made": str(tmp_path),
              "cloth materials": str(people_cloth.REPO / "data/physics/cloth.json")}
    people_cloth.make(inputs, out, 0, {})
    record = json.loads((out / people_cloth.RECORD).read_text())
    assert record["left out"] == ["nev: no usable dressed and built body of its look (people-dress-astronaut-made, "
                                  "people-body-astronaut-made)"]
    assert people_cloth.output_faults(out) == []
    assert not list(Usd.Stage.Open(str(out / people_cloth.LAYER)).Traverse())
