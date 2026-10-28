"""The sim body stage (score/stages/sim_body): a person's rig is read at its own build and weighed by #64's rule, its
clip's frames chain down the tree, the model is fetched only as pinned, and each gate fails its break.

On a toy rig made here (a closed 0.2 x 1 x 0.2 m column: Root at 0, Hips at 0.5 m, Shin at 0 m, the end sites): the
root and each end site go to the segment that carries them. The mass is the stated weight, else the height squared
times the BMI of the stated sex (NCD-RisC 2016: a 1.80 m woman 80.35 kg), else the mean of both, marked estimated. A
built body 1.1 times the rig plays its clips 1.1 times as far. A clip's frames chain down the tree (a root turned 90
degrees about up carries a child 1 m along x to -1 m along z). The model's wheel is unpacked only when its sha256 is
the pinned one. On runs written here (no engine): a good run passes every gate, a body 5 cm into its ground fails
`on floor`, a landed foot 5 cm off its ground fails `lands` and so does a body no foot of which lands, a ground that
pushes 10% under the weight fails `carries`, a segment 10 degrees off the clip fails `follows` and so does RRA's move
of a segment 6 degrees or the pelvis 2.5 cm off the fitted path in one frame, a residual force over
2% of the weight or a moment over 1% of it times the centre's height fails `residual`. The make on the toy, over a toy
seed whose ground is one raised square, its engine run stood in by a written one, hands each body the ground's
triangles in its own frame (its spot and turn, then the dressed body's Turned), leaves out by name a body no solid is
near, names the clip the rig lacks and the crowd, weighs each body by the scene's gravity, and writes the layer: each
SOMA segment an Xform at its pose every frame holding the bone it rides, another bone under Bones, and the muscles as
lines coloured by activation; the record names the model's attribution (MyoSuite, MoBL-ARMS); each body is
calibrated on the rig's standing clip, its first frame handed to the run.
Newton and MuJoCo are not run here (the model's run takes minutes); the real run's
numbers are on #65.

Breaks that turn each check red (each applied once and seen red, reverted, 2026-10-27):
- the_root_and_end_sites_go_to_their_carrier: segments_of's carrier `joint = parents[joint]` made `joint = -1`.
- the_mass_is_stated_else_height_times_bmi: mass_of's `tall ** 2` made `tall`.
- a_body_is_built_at_its_persons_own_size: person_rig's `local[:, hips, :3, 3] *= size` dropped.
- the_clip_chains_down_the_tree: clip_frames' `world[:, parents[joint]] @ local[:, joint]` made
  `local[:, joint] @ world[:, parents[joint]]`.
- the_model_is_unpacked_only_as_pinned: fetched's sha256 check dropped.
- a_good_run_passes_and_each_gate_fails_its_break: judge_on_floor's `> SUNK_MOST` made `> 1.0`; judge_lands'
  `> LANDED` made `> 1.0`; landings' `push >= CONTACT * weight` made `push >= 0`; judge_carries'
  `abs(... - 1.0) > CARRIED` made `> 1.0`; judge_follows' `> FOLLOWED` made `> 90`; judge_residual's force check
  dropped; its moment check dropped; RESIDUAL_FORCE 0.02 made 0.05 (2026-10-28); judge_follows' per-frame turn
  check dropped; its pelvis check dropped (2026-10-28).
- the_make_stands_each_body_on_its_own_ground_under_its_character, 2026-10-28: make's `adjusted=entry["adjusted"]`
  dropped (the RRA adjustment not recorded); make's job `"adjust"` dropped (the run gets no cap).
- the_make_stands_each_body_on_its_own_ground_under_its_character: ground_of's `np.linalg.inv(frame)` made `frame`;
  own_frame's `turn + TURNED` made `turn`; make's `if not len(ground)` check dropped; write_layer's
  `points @ carried[:3, :3].T + carried[:3, 3]` made `points` (a ridden bone drawn in its body's frame, not its
  segment's); its colour's `shade` made 0; make's `clip_frames(rig, STANDING, kept)[0]` made `rig["bind"][kept]`
  (calibrated on the bind, not the standing clip); the record's `"attribution": ATTRIBUTION` made `""`.

Run: .venv/bin/python -m pytest score/stages/sim_body/test_a_body_doing_its_clip_stands_on_its_ground_within_its_residual.py
"""
import hashlib
import json
import zipfile

import numpy as np
import pytest
import trimesh
from pxr import Gf, Usd, UsdGeom

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


def test_the_root_and_end_sites_go_to_their_carrier():
    kept, carriers = sim_body.segments_of(toy_rig())
    assert kept == [1, 2] and carriers == [1, 1, 2, 1, 2]


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


def test_the_model_is_unpacked_only_as_pinned(tmp_path, monkeypatch):
    wheel = tmp_path / "made" / "model.whl"
    wheel.parent.mkdir()
    with zipfile.ZipFile(wheel, "w") as packed:
        packed.writestr("musclemimic_models/model/body/myofullbody.xml", "<mujoco/>")
    sha = hashlib.sha256(wheel.read_bytes()).hexdigest()
    monkeypatch.setattr(sim_body, "HOME", tmp_path / "home")
    monkeypatch.setattr(sim_body, "MODEL", (wheel.as_uri(), "0" * 64))
    with pytest.raises(ValueError, match="sha256"):
        sim_body.fetched()
    monkeypatch.setattr(sim_body, "MODEL", (wheel.as_uri(), sha))
    folder = sim_body.fetched()
    assert (folder / "musclemimic_models/model/body/myofullbody.xml").read_text() == "<mujoco/>"


def frames(count, lowest=0.001, push=1.0, off=0.0, weight=100.0, foot=0.003, foot_push=0.5, residual=(0.6, 0.0, 0.8),
           moment=(0.0, 0.0, 0.0)):
    """A written run of `count` frames: two segments, the ground pushing `push` of `weight`, `foot_push` of it through
    one foot `foot` m over it, the body `off` degrees about x from the clip on each segment, a residual."""
    return [{"angles": [[off, 0.0, 0.0], [off, 0.0, 0.0]], "targets": [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0]],
             "torques": [1.0, -3.0], "ground": [0.0, push * weight, 0.0], "lowest": lowest,
             "feet": {"LeftFoot": [foot, foot_push * weight], "RightFoot": [0.3, 0.01 * weight]},
             "residual": [*residual, *moment], "reserve": 0.5, "activations": [0.1, 0.4], "forces": [20.0, 300.0],
             "poses": []} for _ in range(count)]


def judged(tmp_path, run, turn=3.0, pelvis=1.5):
    """The gates on a written run whose RRA moved a segment `turn` degrees and the pelvis `pelvis` cm at most."""
    adjusted = {"largest turn deg": turn, "pelvis cm": [0.5, pelvis]}
    measures = sim_body.measured({"frames": run, "kg": 10.0, "com height": 1.0, "adjusted": adjusted}, 10.0)
    (tmp_path / sim_body.RECORD).write_text(json.dumps({"bodies": {"one": {"measures": measures}}}))
    return {check.name: check.judge(tmp_path, {}, {}).answer for check in sim_body.CHECKS}, measures


def test_a_good_run_passes_and_each_gate_fails_its_break(tmp_path):
    good, measures = judged(tmp_path, frames(40))
    assert good == {"on floor": checks.PASS, "lands": checks.PASS, "carries": checks.PASS, "follows": checks.PASS,
                    "residual": checks.PASS}
    assert (measures["largest torque Nm"], measures["largest residual N"], measures["largest muscle force N"]) == (
        3.0, 1.0, 300.0)
    assert measures["frames within residual limits"] == 1.0
    assert measures["landings"] == 40  # the unloaded right foot is no landing
    assert judged(tmp_path, frames(40, lowest=-0.05))[0]["on floor"] == checks.FAIL
    assert judged(tmp_path, frames(40, foot=0.05))[0]["lands"] == checks.FAIL
    assert judged(tmp_path, frames(40, foot_push=0.0))[0]["lands"] == checks.FAIL
    assert judged(tmp_path, frames(40, push=0.9))[0]["carries"] == checks.FAIL
    off, measures = judged(tmp_path, frames(40, off=10.0))
    assert off["follows"] == checks.FAIL and measures["mean off clip deg"] == pytest.approx(10.0)
    assert judged(tmp_path, frames(40), turn=6.0)[0]["follows"] == checks.FAIL  # one frame's chest 6 degrees off
    assert judged(tmp_path, frames(40), pelvis=2.5)[0]["follows"] == checks.FAIL  # one frame's pelvis 2.5 cm off
    over, measures = judged(tmp_path, frames(40, residual=(0.0, 2.5, 0.0)))  # over 2% of 100 N
    assert over["residual"] == checks.FAIL and measures["frames within residual limits"] == 0.0
    assert judged(tmp_path, frames(40, moment=(1.1, 0.0, 0.0)))[0]["residual"] == checks.FAIL  # over 1 N m


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


def written_run(job):
    """A written engine run for the job's one person: Hips and Shin each riding a bone 0.1 m up its segment's own
    frame, one muscle of two points, twenty frames."""
    person = job["people"][0]
    frame = frames(1, weight=person["kg"] * 1.62)[0]
    frame.update(poses=[[0.0, 0.6, 0.0, 0.0, 0.0, 0.0, 1.0], [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0]],
                 activations=[1.0], forces=[100.0])
    entry = {"rides": {"Hips": "pelvis", "Shin": "tibia_l"}, "model": {"kg": person["kg"]}, "muscles": ["soleus_l"],
             "bones": ["pelvis", "tibia_l", "talus_l"], "kg": person["kg"], "com height": 0.5, "frames": [frame] * 20,
             "adjusted": {"pelvis cm": [0.5, 1.2], "largest turn deg": 3.0, "mass %": -1.0}}
    bones = np.zeros((20, 3, 7))
    bones[:, :, 6] = 1.0
    bones[:, 0, 1], bones[:, 1, 1] = 0.6, 0.1  # each ridden bone 0.1 m up its segment
    riders = np.zeros((20, 2, 7))
    riders[:, :, 6] = 1.0
    riders[:, 0, 1] = 0.5  # the Hips segment 0.5 m up, the Shin at the origin
    arrays = {"ann/bones": bones, "ann/segments": riders,
              "ann/paths": np.tile([[0.0, 0.4, 0.0], [0.0, 0.1, 0.0]], (20, 1)).astype(np.float32),
              "ann/counts": np.full((20, 1), 2, dtype=np.int32)}
    for bone in entry["bones"]:
        arrays[f"ann/mesh/{bone}/points"] = np.array([[0, 0, 0], [0.1, 0, 0], [0, 0.1, 0]], dtype=np.float32)
        arrays[f"ann/mesh/{bone}/faces"] = np.array([[0, 1, 2]], dtype=np.int32)
    return {"engine": "written", "people": {"ann": entry}}, arrays


def test_the_make_stands_each_body_on_its_own_ground_under_its_character(tmp_path, monkeypatch):
    rig = toy_rig()
    bent = np.eye(4)
    bent[1:3, 1:3] = [[np.cos(0.2), -np.sin(0.2)], [np.sin(0.2), np.cos(0.2)]]
    rig["clip_standing"][:, 2] = rig["clip_standing"][:, 2] @ bent  # its standing shin bent off the bind
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
        job = json.loads(job.read_text())
        assert [person["name"] for person in job["people"]] == ["ann"]
        person = job["people"][0]
        assert person["segments"] == ["Hips", "Shin"] and person["kg"] == 50.0 and job["model"] == "fetched"
        assert job["adjust"]["follows deg"] == sim_body.FOLLOWED and job["residual"]["force"] == 0.02
        assert np.asarray(person["standing"]) == pytest.approx(sim_body.clip_frames(rig, "standing", [1, 2])[0])
        ground = np.load(person["targets"])["ground"]
        assert ground[:, :, 1] == pytest.approx(0.1)
        # the square's corner (3, 5) is (2, 3) from ann's spot: turned back her 30 degrees and the dressed body's
        # Turned 180 about up, (-0.232, -3.598) (without the Turned: (0.232, 3.598), the ground mirrored)
        assert np.abs(ground.reshape(-1, 3)[:, [0, 2]] - [1.5 - 2 * np.cos(np.pi / 6), -1 - 3 * np.cos(np.pi / 6)]).sum(
            axis=1).min() == pytest.approx(0.0, abs=1e-5)
        return written_run(job)

    monkeypatch.setattr(sim_body, "ran", written)
    monkeypatch.setattr(sim_body, "fetched", lambda: "fetched")
    monkeypatch.setattr(sim_body, "gravity_of", lambda place, inputs: ("moon", 1.62))
    out = tmp_path / "out"
    out.mkdir()
    sim_body.make({"cast": str(tmp_path / "cast"), sim_body.CLIPS_ROW: str(tmp_path / "clips"),
                   "seed": str(tmp_path / "seed")}, out, 0, {})
    record = json.loads((out / sim_body.RECORD).read_text())
    ann = record["bodies"]["ann"]
    assert ann["measures"]["weight N"] == pytest.approx(81.0) and ann["segments"] == {"Hips": "pelvis",
                                                                                      "Shin": "tibia_l"}
    assert ann["ground"] == {"solids": ["Ground/Ground"], "triangles": 2}
    assert ann["calibrated on"].startswith("the rig's standing clip")
    assert [line.split(":")[0] for line in record["left out"]] == ["bob", "cid", "crowd"]
    assert record["bodies"]["ann"]["adjusted"] == {"pelvis cm": [0.5, 1.2], "largest turn deg": 3.0, "mass %": -1.0}
    assert "Holzbaur" in record["model"]["attribution"] and "Apache-2.0" in record["model"]["attribution"]
    stage = Usd.Stage.Open(str(out / sim_body.LAYER))
    root = "/toy/Characters/ann/SimBody"
    cache = UsdGeom.XformCache(5)
    bone = stage.GetPrimAtPath(f"{root}/Shin/bone_tibia_l")
    first = UsdGeom.Mesh(bone).GetPointsAttr().Get()[0]
    assert cache.GetLocalToWorldTransform(bone).Transform(Gf.Vec3d(first))[1] == pytest.approx(0.1)  # 0.1 m up the Shin
    assert stage.GetPrimAtPath(f"{root}/Bones/bone_talus_l/bone_talus_l").IsA(UsdGeom.Mesh)
    muscles = UsdGeom.BasisCurves(stage.GetPrimAtPath(f"{root}/Muscles"))
    assert list(muscles.GetCurveVertexCountsAttr().Get(5)) == [2]
    assert tuple(UsdGeom.PrimvarsAPI(muscles).GetPrimvar("displayColor").Get(5)[0]) == pytest.approx(
        sim_body.ACTIVE, abs=1e-6)
    assert json.loads((out / "measures/ann.json").read_text())[0]["poses"][0][1] == 0.6  # the clip's, as written
    assert sim_body.output_faults(out) == []
