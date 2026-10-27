"""The sim body stage (score/stages/sim_body): a body is built from its rig's own segments, weighed by #64's rule, driven
by its clip's chained frames, and each gate fails its break.

On a toy rig made here (a closed 0.2 x 1 x 0.2 m column, its top four corners weighted to Hips at 0.5 m, its bottom
four to Shin at 0 m): the volume splits half and half at the joints' boundary, with each half's centre and inertia
those of a 0.2 x 0.5 x 0.2 m block (worked by hand); the shin hangs from the hips at the bind offset; the root and
each end site go to the segment that carries them. The mass is the stated weight, else the height squared times
the BMI of the stated sex (NCD-RisC 2016: a 1.80 m woman 80.35 kg), else the mean of both, marked estimated. A clip's
frames chain down the tree (a root turned 90 degrees about up carries a child 1 m along x to -1 m along z). A drive's
gain is the mass its joint carries. On runs written here (no engine): a good run passes every gate, a body 5 cm into
its ground fails `on floor`, a landed foot 5 cm off its ground fails `lands` and so does a body no foot of which
lands, a ground that pushes 10% under the weight fails `carries`, joints 10 degrees off the clip fail `follows`. The
make on the toy, over a toy seed whose ground is one raised square, its engine run stood in by a written one, hands each
body the ground's triangles in its own frame (its spot and turn), leaves out by name a body no solid is near, writes the
layer with each segment's mass and spherical joint under the character's prim, names the clip the rig lacks and the
crowd, and weighs each body by the scene's gravity. Newton itself is not run here (its first run compiles for minutes);
the real run's numbers are on #65.

Breaks that turn each check red (each applied once and seen red, reverted, 2026-10-27):
- the_volume_splits_by_skin_weight: body_of's `.argmax(axis=1)` made `.argmin(axis=1)` (a voxel owned by its weakest
  weight).
- the_root_and_end_sites_go_to_their_carrier: segments_of's carrier `joint = parents[joint]` made `joint = -1` (every
  end site carried by the top segment).
- the_mass_is_stated_else_height_times_bmi: mass_of's `tall ** 2` made `tall`.
- a_body_is_built_at_its_persons_own_size: person_rig's `local[:, hips, :3, 3] *= size` dropped; its
  `local[:, joint, :3, 3] = built["offsets"][joint]` dropped (the clip's own offsets kept).
- the_clip_chains_down_the_tree: clip_frames' `world[:, parents[joint]] @ local[:, joint]` made
  `local[:, joint] @ world[:, parents[joint]]`.
- a_joint_drives_the_mass_it_carries: gains' `carried[segments[index]["parent"]] += carried[index]` dropped.
- a_good_run_passes_and_each_gate_fails_its_break: judge_on_floor's `> SUNK_MOST` made `> 1.0`; judge_lands'
  `> LANDED` made `> 1.0`; landings' `push >= CONTACT * weight` made `push >= 0` (an unloaded foot read as landed);
  judge_carries' `abs(... - 1.0) > CARRIED` made `> 1.0`; judge_follows' `> FOLLOWED` made `> 90`.
- the_make_stands_each_body_on_its_own_ground_under_its_character: write_layer's
  `mass.CreateMassAttr(segment["mass"])` dropped; ground_of's `np.linalg.inv(frame)` made `frame` (the ground taken
  out of the body's frame the wrong way); own_frame's `turn + TURNED` made `turn` (the ground mirrored off the
  skin); make's `if not len(ground)` check dropped (a body with no ground run).

Run: .venv/bin/python -m pytest score/stages/sim_body/test_a_body_built_from_its_segments_carries_its_weight_and_follows_its_clip.py
"""
import json

import numpy as np
import pytest
import trimesh
from pxr import Gf, Usd, UsdGeom, UsdPhysics

from score import checks
from score.stages import sim_body


def toy_rig():
    """A closed column 0.2 x 1 x 0.2 m standing on y = 0: Root at 0, Hips at 0.5 m, Shin at 0 m (Hips' child),
    HeadEnd over Hips, LeftToeEnd under Shin; its top corners weighted to Hips, its bottom ones to Shin."""
    column = trimesh.creation.box(extents=(0.2, 1.0, 0.2))
    column.apply_translation((0.0, 0.5, 0.0))
    names = np.array(["Root", "Hips", "Shin", "HeadEnd", "LeftToeEnd"])
    parents = np.array([-1, 0, 1, 1, 2])
    bind = np.repeat(np.eye(4)[None], 5, axis=0)
    bind[1, 1, 3], bind[3, 1, 3] = 0.5, 1.0
    weights = np.zeros((len(column.vertices), 5))
    weights[column.vertices[:, 1] > 0.5, 1] = 1.0
    weights[column.vertices[:, 1] <= 0.5, 2] = 1.0
    still = np.repeat(np.linalg.inv(bind[parents.clip(0)]) @ bind, 1, axis=0)
    still[0] = bind[0]
    return {"names": names, "parents": parents, "bind": bind, "points": np.asarray(column.vertices),
            "faces": np.asarray(column.faces), "weights": weights, "clip_standing": np.repeat(still[None], 10, axis=0)}


def test_the_volume_splits_by_skin_weight():
    segments, kept = sim_body.body_of(toy_rig())
    hips, shin = segments
    assert [hips["name"], shin["name"]] == ["Hips", "Shin"] and kept == [1, 2]
    assert hips["mass"] == pytest.approx(0.5, abs=0.02) and shin["mass"] == pytest.approx(0.5, abs=0.02)
    assert hips["com"] == pytest.approx([0.0, 0.25, 0.0], abs=0.01)
    assert shin["com"] == pytest.approx([0.0, 0.25, 0.0], abs=0.01)
    block = 0.5 / 12 * (0.5 ** 2 + 0.2 ** 2)  # a 0.5 kg block 0.2 x 0.5 x 0.2 m about its x axis
    assert np.asarray(hips["inertia"])[0, 0] == pytest.approx(block, rel=0.06)
    assert hips["box"][1] == pytest.approx([0.1, 0.25, 0.1], abs=sim_body.VOXEL)  # one voxel


def test_the_root_and_end_sites_go_to_their_carrier():
    rig = toy_rig()
    kept, carriers = sim_body.segments_of(rig)
    assert kept == [1, 2] and carriers == [1, 1, 2, 1, 2]
    hips, shin = sim_body.body_of(rig)[0]
    assert (hips["parent"], shin["parent"]) == (-1, 0)
    assert np.asarray(shin["local"])[1, 3] == pytest.approx(-0.5)


def test_the_mass_is_stated_else_height_times_bmi():
    assert sim_body.mass_of({"weight": 64.0}, 1.75) == {"kg": 64.0, "source": "stated weight"}
    woman = sim_body.mass_of({"height": 1.8, "sex": "female"}, 1.75)
    assert woman["kg"] == pytest.approx(80.35) and woman["source"] == "estimated" and woman["height from"] == "stated"
    unknown = sim_body.mass_of({}, 2.0)
    assert unknown["kg"] == pytest.approx(4 * 24.65) and unknown["sex"] == "not stated"
    assert unknown["height from"] == "the SOMA body's own standing height"


def test_a_body_is_built_at_its_persons_own_size():
    """A built body 1.1 times the rig (its bind, offsets and surface): the person's rig takes its bind and surface,
    every clip's offsets its own and the travel 1.1 times the clip's; its segments stand 1.1 times as far apart."""
    rig = toy_rig()
    rig["clip_standing"][:, 1, 1, 3] = 0.5  # the clip's Hips travel: its height over the Root
    big = np.array(rig["bind"])
    big[:, :3, 3] *= 1.1
    offsets = np.array([np.linalg.inv(big[parent])[:3, :3] @ (big[joint][:3, 3] - big[parent][:3, 3])
                        for joint, parent in enumerate(np.clip(rig["parents"], 0, None))])
    built = {"bind": big, "offsets": offsets, "source_points": rig["points"] * 1.1}
    person, size = sim_body.person_rig(rig, built)
    assert size == pytest.approx(1.1) and sim_body.person_rig(rig, None)[1] == 1.0
    world = sim_body.clip_frames(person, "standing", [1, 2])
    assert world[0, 0, 1, 3] == pytest.approx(0.55)  # the Hips travel 1.1 times the clip's
    assert world[0, 1, 1, 3] == pytest.approx(0.0)  # the Shin at its built offset under it
    assert sim_body.standing_height(person) == pytest.approx(1.1)


def test_the_clip_chains_down_the_tree():
    rig = toy_rig()
    turned = np.eye(4)
    turned[:3, :3] = [[0, 0, 1], [0, 1, 0], [-1, 0, 0]]  # 90 degrees about y
    along = np.eye(4)
    along[0, 3] = 1.0
    rig["clip_turn"] = np.array([[turned, np.eye(4), along, np.eye(4), np.eye(4)]])
    world = sim_body.clip_frames(rig, "turn", [1, 2])
    assert world[0, 1, :3, 3] == pytest.approx([0.0, 0.0, -1.0])


def test_a_joint_drives_the_mass_it_carries():
    segments = [{"mass": 10.0, "parent": -1}, {"mass": 4.0, "parent": 0}, {"mass": 1.0, "parent": 1}]
    assert sim_body.gains(segments) == [[sim_body.DRIVE[0] * mass, sim_body.DRIVE[1] * mass] for mass in (15, 5, 1)]


def frames(count, lowest=0.001, push=1.0, off=0.0, weight=100.0, foot=0.003, foot_push=0.5):
    """A written run of `count` frames: two joints, the ground pushing `push` of `weight`, `foot_push` of it through
    one foot `foot` m over it, the sim `off` degrees about x from the clip on each joint."""
    return [{"angles": [[off, 0.0, 0.0], [off, 0.0, 0.0]], "targets": [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0]],
             "torques": [[1.0, 2.0, 3.0], [0.0, 0.0, 0.0]], "ground": [0.0, push * weight, 0.0], "lowest": lowest,
             "feet": {"LeftFoot": [foot, foot_push * weight], "RightFoot": [0.3, 0.01 * weight]},
             "helper": [3.0, 0.0, 4.0, 0.0, 0.0, 0.0], "poses": []} for _ in range(count)]


def judged(tmp_path, run):
    measures = sim_body.measured(run, 10.0, 10.0)
    (tmp_path / sim_body.RECORD).write_text(json.dumps({"bodies": {"one": {"measures": measures}}}))
    return {check.name: check.judge(tmp_path, {}, {}).answer for check in sim_body.CHECKS}, measures


def test_a_good_run_passes_and_each_gate_fails_its_break(tmp_path):
    good, measures = judged(tmp_path, frames(40))
    assert good == {"on floor": checks.PASS, "lands": checks.PASS, "carries": checks.PASS, "follows": checks.PASS}
    assert (measures["largest torque Nm"], measures["largest helper N"], measures["mean helper N"]) == (3.0, 5.0, 5.0)
    assert measures["landings"] == 40 - int(sim_body.SETTLE * sim_body.RATE)  # the unloaded right foot is no landing
    assert judged(tmp_path, frames(40, lowest=-0.05))[0]["on floor"] == checks.FAIL
    assert judged(tmp_path, frames(40, foot=0.05))[0]["lands"] == checks.FAIL
    assert judged(tmp_path, frames(40, foot_push=0.0))[0]["lands"] == checks.FAIL
    assert judged(tmp_path, frames(40, push=0.9))[0]["carries"] == checks.FAIL
    off, measures = judged(tmp_path, frames(40, off=10.0))
    assert off["follows"] == checks.FAIL and measures["mean off clip deg"] == pytest.approx(10.0)


def toy_seed(folder):
    """A seed whose base layer holds one solid: a 4 x 5 m square at 0.1 m from (-1, -, 0) to (3, -, 5)."""
    (folder / "layers").mkdir(parents=True)
    stage = Usd.Stage.CreateNew(str(folder / "layers/base.usda"))
    UsdGeom.Xform.Define(stage, "/toy")
    square = UsdGeom.Mesh.Define(stage, "/toy/Ground/Ground")
    square.CreatePointsAttr([Gf.Vec3f(x, 0.1, z) for x, z in ((-1, 0), (3, 0), (3, 5), (-1, 5))])
    square.CreateFaceVertexCountsAttr([4])
    square.CreateFaceVertexIndicesAttr([0, 1, 2, 3])
    stage.Save()


def test_the_make_stands_each_body_on_its_own_ground_under_its_character(tmp_path, monkeypatch):
    rig = toy_rig()
    (tmp_path / "clips").mkdir()
    np.savez(tmp_path / "clips/rig.npz", **rig)
    toy_seed(tmp_path / "seed")
    (tmp_path / "cast").mkdir()
    cast = {"place": "toy", "crowd": {"name": "crowd"}, "characters": [
        {"name": "ann", "doing": "standing", "at": [1.0, 0.0, 2.0], "turn": 30.0, "weight": 50.0},
        {"name": "bob", "doing": "flying", "at": [0.0, 0.0, 0.0]},
        {"name": "cid", "doing": "standing", "at": [50.0, 0.0, 50.0]}]}
    (tmp_path / "cast/cast.json").write_text(json.dumps(cast))

    def written(job, out):
        people = json.loads(job.read_text())["people"]
        assert [person["name"] for person in people] == ["ann"]
        person = people[0]
        ground = np.load(person["targets"])["ground"]
        assert ground[:, :, 1] == pytest.approx(0.1)
        # the square's corner (3, 5) is (2, 3) from ann's spot: turned back her 30 degrees and the dressed body's
        # Turned 180 about up, (-0.232, -3.598) (without the Turned: (0.232, 3.598), the ground mirrored)
        assert np.abs(ground.reshape(-1, 3)[:, [0, 2]] - [1.5 - 2 * np.cos(np.pi / 6), -1 - 3 * np.cos(np.pi / 6)]).sum(
            axis=1).min() == pytest.approx(0.0, abs=1e-5)
        frame = frames(1, weight=50.0 * 1.62)[0]
        frame["poses"] = [[0.0, 0.5, 0.0, 0.0, 0.0, 0.0, 1.0], [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0]]
        return {"engine": "written", "people": {"ann": {"frames": [frame] * 20}}}

    monkeypatch.setattr(sim_body, "ran", written)
    monkeypatch.setattr(sim_body, "gravity_of", lambda place, inputs: ("moon", 1.62))
    out = tmp_path / "out"
    out.mkdir()
    sim_body.make({"cast": str(tmp_path / "cast"), sim_body.CLIPS_ROW: str(tmp_path / "clips"),
                   "seed": str(tmp_path / "seed")}, out, 0, {})
    record = json.loads((out / sim_body.RECORD).read_text())
    assert record["bodies"]["ann"]["measures"]["weight N"] == pytest.approx(81.0)
    assert record["bodies"]["ann"]["ground"] == {"solids": ["Ground/Ground"], "triangles": 2}
    assert [line.split(":")[0] for line in record["left out"]] == ["bob", "cid", "crowd"]
    stage = Usd.Stage.Open(str(out / sim_body.LAYER))
    shin = stage.GetPrimAtPath("/toy/Characters/ann/SimBody/Shin")
    assert UsdPhysics.MassAPI(shin).GetMassAttr().Get() == pytest.approx(25.0, abs=1.0)
    assert stage.GetPrimAtPath("/toy/Characters/ann/SimBody/Shin/joint").IsA(UsdPhysics.SphericalJoint)
    assert sim_body.output_faults(out) == []
