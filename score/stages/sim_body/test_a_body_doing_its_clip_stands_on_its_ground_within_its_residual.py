"""The sim body stage (score/stages/sim_body): a person's rig is read at its own build and weighed by #64's rule, its
clip's frames chain down the tree, the model is fetched only as pinned, and each gate fails its break.

On a toy rig made here (a closed 0.2 x 1 x 0.2 m column: Root at 0, Hips at 0.5 m, LeftFoot at 0 m, the end sites): the
root and each end site go to the segment that carries them. The mass is the stated weight, else the height squared times
the BMI of the stated sex (NCD-RisC 2016: a 1.80 m woman 80.35 kg), else the mean of both, marked estimated. A built
body 1.1 times the rig plays its clips 1.1 times as far. A clip whose offsets are shorter than its rig's bind (as
people-clips-made's are: posed on SOMA's zero-identity body, 7 cm shorter than the template its bind is, #70) is played
on the bind's own bones and lifted so its standing frame's feet are where the bind's are, every clip by the same lift,
as the people build plays it (`tools.characters.played`, prop_build.py's arithmetic): its feet stand on its ground; a
clip floating its still foot 7 mm mid-clip stands it on its ground on every frame, a jump keeps its flight. A clip's frames chain
down the tree (a root turned 90 degrees about up carries a child 1 m along x to -1 m along z). The model's wheel is
unpacked only when its sha256 is the pinned one. On runs written here (no engine): a good run passes every gate, a body
5 cm into its ground fails `on floor`, a landed foot 5 cm off its ground fails `lands` and so does a body no foot of
which lands, unless it sits and its ground carries it (a seated body its ground never carries fails), a ground that pushes 10% under the weight fails `carries`, a segment 10 degrees off the clip fails
`follows` and so does RRA's move of a segment 6 degrees or the pelvis 2.5 cm off the fitted path in one frame, a
residual force over 2% of the weight or a moment over 1% of it times the centre's height fails `residual`, a body
shaking a degree each frame round its clip's swing fails `smooth` and one moving as its clip does passes. The make on
the toy, over a toy seed whose ground is one raised square, its engine run stood in by a written one, hands each body
the ground's triangles in its own frame (its spot and turn, then the dressed body's Turned), leaves out by name a body
no solid is near, names the clip the rig lacks and the crowd, weighs each body by the scene's gravity, and writes the
layer: each SOMA segment an Xform at its pose every frame holding the bone it rides, another bone under Bones, and the
muscles as lines coloured by activation; the record names the model's attribution (MyoSuite, MoBL-ARMS); each body is
calibrated on the static table (no clip of the rig handed to the run), with the person's mesh for the sizing; and SOMA's
joints leave the stage unchanged: every frame's `poses` in the measures are the clip's own segment frames bit for bit,
though the written run moved them 0.6 m (#70: SOMA is the truth). A cast of a crowd and no singles is a valid input: no run, no
body, the record's `no bodies` naming why, every gate passing; a cast whose one single's clip the rig lacks still fails
the output's contract, and so does an empty cast (no singles and no crowd), by name (#70, square, 2026-10-30). Newton and MuJoCo are not run here (the model's run
takes minutes); the real run's numbers are on #65.

Breaks that turn each check red (each applied once and seen red, reverted, 2026-10-27):
- a_body_doing_its_clip_stands_on_its_ground_within_its_residual (2026-11-13: the four breaks below folded into it,
  each seen red on it), its root and end sites going to their carrier: segments_of's carrier `joint = parents[joint]`
  made `joint = -1`.
- the_mass_is_stated_else_height_times_bmi: mass_of's `tall ** 2` made `tall`.
- its body built at its person's own size: person_rig's `size` handed to played as 1.0 (2026-10-29; before, its
  `local[:, hips, :3, 3] *= size` dropped; green since the lift is figured at the size, on main before the fold
  too); route_clip's scale handed to played as `size` (the climber's route 1.1 m long, 2026-11-04); its `ground +
  (... - ground) * size` made `... * size` (its feet under the steps).
- its clip on its bind's bones with its feet on its ground, 2026-10-29 (#70's float): person_rig's no-build case
  made `return rig, 1.0` (the clip's own offsets, 5 cm short, played raw: the standing foot 2 cm over its ground); its
  lift handed to played as 0.0 (the foot 3 cm under its ground; 2026-10-29, the lift now `played.floor_lift`).
- its clip on its bind's bones with its feet on its ground, 2026-11-05 (#70, the pickup's float): person_rig's
  `stood(found, ...)` dropped (the floating foot 7 mm over its ground); stood's `heights < STANCE_HIGH` dropped (the
  jump's flight pulled 10 cm down onto its ground); stood's `heights <= others[:, None]` dropped (the sitting column's
  foot pulled 2 cm down, its other skin pushed under its floor).
- its clip on its bind's bones with its feet on its ground, 2026-11-06 (#70, Kimodo's own contacts): person_rig's
  `played.contacted(found[key], ...)` handed the unstood `played.clip_local(...)` (the correction given the floating
  foot); contacts_of's `"foot_contacts" in saved.files` check dropped (a motion without contacts refused); make's
  `contacts` not handed to person_rig (no clip corrected).
- its clip on its bind's bones with its feet on its ground, 2026-11-06 (#70, the toes Kimodo's toe pin sank):
  person_rig's `toes_lifted(found, ...)` dropped (the corrected clip's toes never lifted); toes_lifted's
  `moved[low] = played.toward_flat(...)` dropped (the tipped foot's toes 1 cm under); its share made 0 (the same).
- its clip chained down the tree: played.chained's `world[:, parents[joint]] @ local[:, joint]` made
  `local[:, joint] @ world[:, parents[joint]]` (2026-10-29: clip_frames chains through it).
- the_model_is_unpacked_only_as_pinned: fetched's sha256 check dropped.
- a_good_run_passes_and_each_gate_fails_its_break: judge_on_floor's `> SUNK_MOST` made `> 1.0`; judge_lands'
  `> LANDED` made `> 1.0`; landings' `push >= CONTACT * weight` made `push >= 0`; judge_carries'
  `abs(... - 1.0) > CARRIED` made `> 1.0`; judge_follows' `> FOLLOWED` made `> 90`; judge_residual's force check
  dropped; its moment check dropped; RESIDUAL_FORCE 0.02 made 0.05 (2026-10-28); judge_follows' per-frame turn
  check dropped; its pelvis check dropped (2026-10-28); landing_fault's seated `return None if ... else` made
  `return None` (a seated body its ground never carried passes), and `body.get("clip") in SEATED` made `False` (a
  seated body its seat carries fails "no foot landed"; 2026-11-04); judge_smooth's `> ...["clip jerk deg"]` made
  `> 1e9` (a body shaking 1 degree every other frame round its clip's swing passes), and measured's clip jerk of
  `frame["targets"]` made `frame["angles"]` (the body judged against itself)
  (2026-11-05).
- the_make_stands_each_body_on_its_own_ground_under_its_character, 2026-10-28: make's `adjusted=entry["adjusted"]`
  dropped (the RRA adjustment not recorded); make's job `"adjust"` dropped (the run gets no cap).
- the_make_stands_each_body_on_its_own_ground_under_its_character: ground_of's `np.linalg.inv(frame)` made `frame`;
  own_frame's `turn + TURNED` made `turn`; make's `if not len(ground)` check dropped; write_layer's
  `points @ carried[:3, :3].T + carried[:3, 3]` made `points` (a ridden bone drawn in its body's frame, not its
  segment's); its colour's `shade` made 0; the record's `"attribution": ATTRIBUTION` made `""`.
- the_make_stands_each_body_on_its_own_ground_under_its_character, 2026-10-28 (#70): make's `frame["poses"] =
  [soma_pose(world) ...]` made `pass` (the run's moved poses kept); soma_pose's `world[:3, 3]` rounded to 2 places;
  make's targets `points=rig["points"]` made `rig["bind"]` (the mesh not handed to the sizing).
- the_make_stands_each_body_on_its_own_ground_under_its_character, 2026-10-28 (#70's solver): make's
  `"calibrated on": CALIBRATED_ON` made `"the rig's standing clip"`.
- the_make_stands_each_body_on_its_own_ground_under_its_character, 2026-11-04: left_out_why's climber check dropped
  (the climber walks the flat clip through its steps).
- the_make_stands_each_body_on_its_own_ground_under_its_character, 2026-11-02: on_card's targets' folders dropped
  from its inputs (the machine has no targets).
- the_make_stands_each_body_on_its_own_ground_under_its_character, 2026-11-06 (every sim body run on a card): ran's
  `os.environ.get(LOCAL) == "1"` made `True` (the run on this PC); on_card's `kind=KIND` dropped (rented as a Blender
  job); batched's `PER_MACHINE` made 1 (a card a clip); ran_elsewhere's people merge kept the first card's alone;
  card_minutes' high `clips * CLIP_HIGH_MINUTES` made `clips * CLIP_MINUTES` (the high reserved at the likely).
- a_cast_of_no_singles_passes_with_its_reason_and_a_missing_clip_fails, 2026-10-30 (#70): output_faults'
  `"no bodies" not in` check dropped (the crowd-only cast failed again); no_singles' `cast["characters"]` made `True`.
- a_cast_of_no_singles_passes_with_its_reason_and_a_missing_clip_fails, 2026-10-30 (#70): no_singles'
  `or not cast.get("crowd")` dropped (the empty cast passed with the crowd's reason).

Run: .venv/bin/python -m pytest score/stages/sim_body/test_a_body_doing_its_clip_stands_on_its_ground_within_its_residual.py
"""
import hashlib
import json
import types
import zipfile

import numpy as np
import pytest
import trimesh
from pxr import Gf, Usd, UsdGeom

from score import checks
from score.stages import sim_body


def toy_rig():
    """A closed column 0.2 x 1 x 0.2 m standing on y = 0: Root at 0, Hips at 0.5 m, LeftFoot at 0 m (Hips' child),
    HeadEnd over Hips, LeftToeEnd under LeftFoot; its top corners weighted to Hips, its bottom ones to LeftFoot."""
    column = trimesh.creation.box(extents=(0.2, 1.0, 0.2))
    column.apply_translation((0.0, 0.5, 0.0))
    names = np.array(["Root", "Hips", "LeftFoot", "HeadEnd", "LeftToeEnd"])
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


def toe_rig():
    """A foot on y = 0: Root, Hips 0.5 m up, LeftFoot 0.08 m up, LeftToeBase 0.12 m ahead of it 0.02 m up, LeftToeEnd;
    its skin a heel block (LeftFoot's) and a toe block ahead of the toe base (LeftToeBase's), both down to y = 0; its
    clip `tipped`, two frames: the foot pitched 30 degrees onto its toes with the toe base on its bind's height, then
    the bind's pose."""
    names = np.array(["Root", "Hips", "LeftFoot", "LeftToeBase", "LeftToeEnd"])
    parents = np.array([-1, 0, 1, 2, 3])
    bind = np.tile(np.eye(4), (5, 1, 1))
    bind[1:, :3, 3] = [[0.0, 0.5, 0.0], [0.0, 0.08, 0.0], [0.0, 0.02, 0.12], [0.0, 0.006, 0.17]]
    heel = trimesh.creation.box(extents=(0.08, 0.06, 0.14), transform=trimesh.transformations.translation_matrix(
        (0.0, 0.03, 0.03))).vertices
    toes = trimesh.creation.box(extents=(0.08, 0.02, 0.06), transform=trimesh.transformations.translation_matrix(
        (0.0, 0.01, 0.15))).vertices
    weights = np.zeros((len(heel) + len(toes), 5))
    weights[:len(heel), 2], weights[len(heel):, 3] = 1.0, 1.0
    still = np.linalg.inv(bind[parents.clip(0)]) @ bind
    still[0] = bind[0]
    clip = np.repeat(still[None], 2, axis=0)
    angle = np.radians(30.0)
    clip[0, 2, :3, :3] = [[1.0, 0.0, 0.0], [0.0, np.cos(angle), -np.sin(angle)], [0.0, np.sin(angle), np.cos(angle)]]
    clip[0, 2, 1, 3] = 0.02 - 0.5 - (clip[0, 2, :3, :3] @ [0.0, -0.06, 0.12])[1]  # the toe base on its bind's height
    return {"names": names, "parents": parents, "bind": bind, "points": np.r_[heel, toes], "weights": weights,
            "clip_tipped": clip}


def test_the_mass_is_stated_else_height_times_bmi():
    assert sim_body.mass_of({"weight": 64.0}, 1.75) == {"kg": 64.0, "source": "stated weight"}
    woman = sim_body.mass_of({"height": 1.8, "sex": "female"}, 1.75)
    assert woman["kg"] == pytest.approx(80.35) and woman["source"] == "estimated" and woman["height from"] == "stated"
    unknown = sim_body.mass_of({}, 2.0)
    assert unknown["kg"] == pytest.approx(4 * 24.65) and unknown["sex"] == "not stated"
    assert unknown["height from"] == "the SOMA body's own standing height"


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


def judged(tmp_path, run, turn=3.0, pelvis=1.5, clip="walking"):
    """The gates on a written run of `clip` whose RRA moved a segment `turn` degrees and the pelvis `pelvis` cm at
    most."""
    adjusted = {"largest turn deg": turn, "pelvis cm": [0.5, pelvis]}
    measures = sim_body.measured({"frames": run, "kg": 10.0, "com height": 1.0, "adjusted": adjusted}, 10.0)
    (tmp_path / sim_body.RECORD).write_text(json.dumps({"bodies": {"one": {"clip": clip, "measures": measures}}}))
    return {check.name: check.judge(tmp_path, {}, {}).answer for check in sim_body.CHECKS}, measures


def test_a_good_run_passes_and_each_gate_fails_its_break(tmp_path):
    good, measures = judged(tmp_path, frames(40))
    assert good == {"on floor": checks.PASS, "lands": checks.PASS, "carries": checks.PASS, "follows": checks.PASS,
                    "residual": checks.PASS, "smooth": checks.PASS}
    assert (measures["largest torque Nm"], measures["largest residual N"], measures["largest muscle force N"]) == (
        3.0, 1.0, 300.0)
    assert measures["frames within residual limits"] == 1.0
    assert measures["landings"] == 40  # the unloaded right foot is no landing
    assert judged(tmp_path, frames(40, lowest=-0.05))[0]["on floor"] == checks.FAIL
    assert judged(tmp_path, frames(40, foot=0.05))[0]["lands"] == checks.FAIL
    assert judged(tmp_path, frames(40, foot_push=0.0))[0]["lands"] == checks.FAIL
    assert judged(tmp_path, frames(40, foot_push=0.0), clip="sitting")[0]["lands"] == checks.PASS  # its seat carries
    assert judged(tmp_path, frames(40, push=0.0, foot_push=0.0), clip="sitting")[0]["lands"] == checks.FAIL
    assert judged(tmp_path, frames(40, push=0.9))[0]["carries"] == checks.FAIL
    off, measures = judged(tmp_path, frames(40, off=10.0))
    assert off["follows"] == checks.FAIL and measures["mean off clip deg"] == pytest.approx(10.0)
    assert judged(tmp_path, frames(40), turn=6.0)[0]["follows"] == checks.FAIL  # one frame's chest 6 degrees off
    assert judged(tmp_path, frames(40), pelvis=2.5)[0]["follows"] == checks.FAIL  # one frame's pelvis 2.5 cm off
    over, measures = judged(tmp_path, frames(40, residual=(0.0, 2.5, 0.0)))  # over 2% of 100 N
    assert over["residual"] == checks.FAIL and measures["frames within residual limits"] == 0.0
    assert judged(tmp_path, frames(40, moment=(1.1, 0.0, 0.0)))[0]["residual"] == checks.FAIL  # over 1 N m
    swing = [[[30 * np.sin(frame / 6), 0.0, 0.0]] * 2 for frame in range(40)]  # the clip's smooth swing about x
    shaken = frames(40)
    for frame, (turns, wanted) in enumerate(zip(shaken, swing)):  # the body follows it 1 degree off every other frame
        turns.update(targets=wanted, angles=[[wanted[0][0] + (-1) ** frame, 0.0, 0.0]] * 2)
    rough, measures = judged(tmp_path, shaken)
    assert rough["smooth"] == checks.FAIL and measures["jerk deg"] > measures["clip jerk deg"] > 0
    for turns in shaken:  # the body moving as its clip does: no rougher
        turns["angles"] = turns["targets"]
    assert judged(tmp_path, shaken)[0]["smooth"] == checks.PASS


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
    """A written engine run for the job's one person: Hips and LeftFoot each riding a bone 0.1 m up its segment's own
    frame, one muscle of two points, twenty frames, each with poses moved 0.6 m up (as the run wrote them before #70:
    the stage must not keep them)."""
    person = job["people"][0]
    written = []
    for _ in range(20):
        frame = frames(1, weight=person["kg"] * 1.62)[0]
        frame.update(poses=[[0.0, 0.6, 0.0, 0.0, 0.0, 0.0, 1.0], [0.0, 0.6, 0.0, 0.0, 0.0, 0.0, 1.0]],
                     activations=[1.0], forces=[100.0])
        written.append(frame)
    entry = {"rides": {"Hips": "pelvis", "LeftFoot": "tibia_l"}, "model": {"kg": person["kg"]},
             "muscles": ["soleus_l"], "bones": ["pelvis", "tibia_l", "talus_l"], "kg": person["kg"], "com height": 0.5,
             "frames": written,
             "adjusted": {"pelvis cm": [0.5, 1.2], "largest turn deg": 3.0, "mass %": -1.0}}
    bones = np.zeros((20, 3, 7))
    bones[:, :, 6] = 1.0
    bones[:, 0, 1], bones[:, 1, 1] = 0.6, 0.1  # each ridden bone 0.1 m up its segment
    riders = np.zeros((20, 2, 7))
    riders[:, :, 6] = 1.0
    riders[:, 0, 1] = 0.5  # the Hips segment 0.5 m up, the LeftFoot at the origin
    arrays = {"ann/bones": bones, "ann/segments": riders,
              "ann/paths": np.tile([[0.0, 0.4, 0.0], [0.0, 0.1, 0.0]], (20, 1)).astype(np.float32),
              "ann/counts": np.full((20, 1), 2, dtype=np.int32)}
    for bone in entry["bones"]:
        arrays[f"ann/mesh/{bone}/points"] = np.array([[0, 0, 0], [0.1, 0, 0], [0, 0.1, 0]], dtype=np.float32)
        arrays[f"ann/mesh/{bone}/faces"] = np.array([[0, 1, 2]], dtype=np.int32)
    return {"engine": "written", "people": {"ann": entry}}, arrays


def test_the_make_stands_each_body_on_its_own_ground_under_its_character(tmp_path, monkeypatch):
    rig = toy_rig()
    rig["clip_standing"] = np.concatenate([rig["clip_standing"]] * 2)  # twenty frames, as the written run's
    rig["clip_standing"][:, 1, 1, 3] = np.linspace(0.5, 0.6, 20)  # its Hips rising: a clip that moves
    bent = np.eye(4)
    bent[1:3, 1:3] = [[np.cos(0.2), -np.sin(0.2)], [np.sin(0.2), np.cos(0.2)]]
    rig["clip_standing"][:, 2] = rig["clip_standing"][:, 2] @ bent  # its standing shin bent off the bind
    (tmp_path / "clips").mkdir()
    np.savez(tmp_path / "clips/rig.npz", **rig)
    (tmp_path / "clips/motions").mkdir()  # Kimodo's own foot contacts beside the rig, as people-clips-made keeps them
    np.savez(tmp_path / "clips/motions/standing.npz", foot_contacts=np.ones((20, 6), dtype=bool))
    corrected = []
    monkeypatch.setattr(sim_body._body.played, "contacted",
                        lambda local, names, parents, bind, given: corrected.append(len(given)) or local)
    toy_seed(tmp_path / "seed")
    (tmp_path / "cast").mkdir()
    cast = {"place": "toy", "crowd": {"name": "crowd"}, "characters": [
        {"name": "ann", "doing": "standing", "at": [1.0, 0.0, 2.0], "turn": 30.0, "weight": 50.0},
        {"name": "bob", "doing": "flying", "at": [0.0, 0.0, 0.0]},
        {"name": "cid", "doing": "standing", "at": [50.0, 0.0, 50.0]},
        {"name": "dee", "doing": "standing", "at": [1.0, 0.0, 2.0],
         "stairs": {"way": "up", "flight": "stair_1", "to": [1.0, 1.0, 3.0], "rise": 0.2, "run": 0.2}}]}
    (tmp_path / "cast/cast.json").write_text(json.dumps(cast))

    def written(job, out):
        job = json.loads(job.read_text())
        assert [person["name"] for person in job["people"]] == ["ann"]
        person = job["people"][0]
        assert person["segments"] == ["Hips", "LeftFoot"] and person["kg"] == 50.0 and job["model"] == "fetched"
        assert job["adjust"]["follows deg"] == sim_body.FOLLOWED and job["residual"]["force"] == 0.02
        assert "standing" not in person  # the calibration is the static table (#70), no clip of the rig
        ground = np.load(person["targets"])["ground"]
        assert np.load(person["targets"])["points"] == pytest.approx(rig["points"])  # the mesh the sizing reads
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
    assert corrected == [20]  # the one build's standing clip given Kimodo's correction on its contacts
    ann = record["bodies"]["ann"]
    assert ann["measures"]["weight N"] == pytest.approx(81.0) and ann["segments"] == {"Hips": "pelvis",
                                                                                      "LeftFoot": "tibia_l"}
    assert ann["ground"] == {"solids": ["Ground/Ground"], "triangles": 2}
    assert ann["calibrated on"] == sim_body.CALIBRATED_ON
    assert [line.split(":")[0] for line in record["left out"]] == ["bob", "cid", "dee", "crowd"]
    assert "no scene-made clip up its stairs (stair_1)" in record["left out"][2]  # a climber never walks flat
    assert record["bodies"]["ann"]["adjusted"] == {"pelvis cm": [0.5, 1.2], "largest turn deg": 3.0, "mass %": -1.0}
    assert "Holzbaur" in record["model"]["attribution"] and "Apache-2.0" in record["model"]["attribution"]
    monkeypatch.undo()  # the real ran again
    held = []  # the run goes to rented cards of kind sim-body, its clips batched, its files at their paths

    class Machine:
        def __init__(self, classes, who, minutes, kind):
            held.append((classes, minutes, kind))

        def __enter__(self):
            return self

        def run(self, script, arguments, inputs, outputs, minutes, env):
            names = [person["name"] for person in json.loads(arguments[0].read_text())["people"]]
            held.append((script, arguments, inputs, outputs, env, names))
            json.dump({"engine": "rented", "rate": 30, "people": {name: {"of": name} for name in names}},
                      outputs[0].open("w"))
            np.savez(outputs[1], **{f"{name}_bones": np.ones(1) for name in names})

        def __exit__(self, *_):
            pass
    monkeypatch.setattr(sim_body.subprocess, "run", lambda *_, **__: pytest.fail("ran on this PC"))
    monkeypatch.setattr("score.adapters.engines.machine_runner",
                        lambda: types.SimpleNamespace(Machine=Machine, SETUP_MINUTES=8))
    monkeypatch.setattr(sim_body, "PER_MACHINE", 2)  # three clips: two on one card, one on another
    job = tmp_path / "job.json"
    job.write_text(json.dumps({"model": "/models/88b0", "rate": 30, "people": [
        {"name": name, "targets": str(tmp_path / f"clips/{name}.npz")} for name in ("ann", "bob", "cid")]}))
    found, arrays = sim_body.ran(job, tmp_path / "run.json")
    assert found == {"engine": "rented", "rate": 30, "people": {"ann": {"of": "ann"}, "bob": {"of": "bob"},
                                                                "cid": {"of": "cid"}}}
    assert sorted(arrays) == ["ann_bones", "bob_bones", "cid_bones"]
    cards = sorted((entry for entry in held if len(entry) == 6), key=lambda entry: entry[5])
    assert [entry[5] for entry in cards] == [["ann", "bob"], ["cid"]]
    assert sorted(entry for entry in held if len(entry) == 3) == [
        (list(sim_body.CLASSES), sim_body.card_minutes(1)[1], "sim-body"),
        (list(sim_body.CLASSES), sim_body.card_minutes(2)[1], "sim-body")]
    first = tmp_path / "job-0.json"
    assert cards[0][:5] == (sim_body.REPO / sim_body.INSIDE, [first, tmp_path / "run-0.json"],
                            [first, tmp_path / "clips", "/models/88b0"],
                            [tmp_path / "run-0.json", tmp_path / "run-0.npz"], sim_body.REPO / sim_body.ENV_SCRIPT)
    assert sorted(path.name for path in tmp_path.glob("*-[0-9].*")) == []  # the parts gone, one run left
    # priced from measured minutes: the row's estimate is seven clips' high on one card, no clip is free, and the
    # forecast reads its cast's singles
    monkeypatch.undo()
    from score.adapters import engines
    engines.machine_runner()  # tools/cloud on the path: the kind's classes are capacity's, an L4 first, parked clean
    import capacity
    import park
    assert capacity.order_for(sim_body.KIND)[0] == sim_body.CLASSES[0] == "gpu-24gb"
    assert set(sim_body.CLASSES) <= set(capacity.classes_for(sim_body.KIND)) and sim_body.KIND in park.CLEANUPS
    assert park.CLEANUPS[sim_body.KIND]({"paths": {"/home/x/job.json", "/root/lib/envs"}}) == "rm -rf /home/x/job.json"
    assert sim_body.priced(7)["euros"] == sim_body.EUROS and sim_body.priced(7)["cards"] == 1
    assert sim_body.priced(0)["euros"] == 0.0
    assert sim_body.priced(sim_body.PER_MACHINE + 1)["cards"] == 2
    assert sim_body.forecast({"cast": str(tmp_path / "cast")}) == sim_body.priced(4)
    stage = Usd.Stage.Open(str(out / sim_body.LAYER))
    root = "/toy/Characters/ann/SimBody"
    cache = UsdGeom.XformCache(5)
    bone = stage.GetPrimAtPath(f"{root}/LeftFoot/bone_tibia_l")
    first = UsdGeom.Mesh(bone).GetPointsAttr().Get()[0]
    assert cache.GetLocalToWorldTransform(bone).Transform(Gf.Vec3d(first))[1] == pytest.approx(0.1)  # 0.1 m up it
    assert stage.GetPrimAtPath(f"{root}/Bones/bone_talus_l/bone_talus_l").IsA(UsdGeom.Mesh)
    muscles = UsdGeom.BasisCurves(stage.GetPrimAtPath(f"{root}/Muscles"))
    assert list(muscles.GetCurveVertexCountsAttr().Get(5)) == [2]
    assert tuple(UsdGeom.PrimvarsAPI(muscles).GetPrimvar("displayColor").Get(5)[0]) == pytest.approx(
        sim_body.ACTIVE, abs=1e-6)
    # SOMA's joints leave the stage unchanged: every frame's poses are the clip's own segment frames as the stage
    # plays it (person_rig: its standing feet stood on its floor), bit for bit
    from scipy.spatial.transform import Rotation
    clip = sim_body.clip_frames(sim_body.person_rig(rig, None)[0], "standing", [1, 2])
    measures = json.loads((out / "measures/ann.json").read_text())
    for frame, worlds in zip(measures, clip):
        for pose, world in zip(frame["poses"], worlds):
            assert pose[:3] == list(world[:3, 3]) and Rotation.from_quat(pose[3:]).as_matrix() == pytest.approx(
                world[:3, :3], abs=1e-12)
    assert len(measures) == len(clip) == 20
    assert sim_body.output_faults(out) == []


def made_on(tmp_path, monkeypatch, cast):
    """The make on the toy rig and seed for a cast, no engine run allowed; its output folder."""
    tmp_path.mkdir()
    np.savez(tmp_path / "rig.npz", **toy_rig())
    toy_seed(tmp_path / "seed")
    (tmp_path / "cast").mkdir()
    (tmp_path / "cast/cast.json").write_text(json.dumps({"place": "toy", **cast}))
    monkeypatch.setattr(sim_body, "ran", lambda job, out: pytest.fail("no body to run"))
    monkeypatch.setattr(sim_body, "gravity_of", lambda place, inputs: ("moon", 1.62))
    out = tmp_path / "out"
    out.mkdir()
    sim_body.make({"cast": str(tmp_path / "cast"), sim_body.CLIPS_ROW: str(tmp_path),
                   "seed": str(tmp_path / "seed")}, out, 0, {})
    return out


def test_a_cast_of_no_singles_passes_with_its_reason_and_a_missing_clip_fails(tmp_path, monkeypatch):
    out = made_on(tmp_path / "crowd", monkeypatch, {"crowd": {"name": "crowd"}, "characters": []})
    record = json.loads((out / sim_body.RECORD).read_text())
    assert record["bodies"] == {} and record["no bodies"] == sim_body.NO_SINGLES
    assert sim_body.output_faults(out) == []
    assert all(check.judge(out, {}, {}).answer == checks.PASS for check in sim_body.CHECKS)
    lacking = {"characters": [{"name": "bob", "doing": "flying", "at": [0, 0, 0]}]}
    out = made_on(tmp_path / "lacking", monkeypatch, lacking)
    assert "no bodies" not in json.loads((out / sim_body.RECORD).read_text())
    assert sim_body.output_faults(out) == ["no sim body: the cast names no character whose clip the rig holds"]
    out = made_on(tmp_path / "empty", monkeypatch, {"characters": []})
    assert "no bodies" not in json.loads((out / sim_body.RECORD).read_text())
    assert sim_body.output_faults(out) == [sim_body.EMPTY_CAST] == ["empty cast: no single characters and no crowd"]


def near(want, tol=None):
    """(low, high) bounds within `tol` of `want`; with no `tol`, pytest.approx's own (a millionth of it)."""
    want = np.asarray(want, dtype=float)
    tol = 1e-6 * np.abs(want) + 1e-12 if tol is None else tol
    return want - tol, want + tol


def clip_worlds(tmp_path):
    """The rigs the clips are played on, by name: `stored` the toy rig as saved, a clip `turn` of its root turned 90
    degrees about up carrying LeftFoot 1 m along x; `built` the toy (its standing Hips 0.5 m over the Root) on a body
    1.1 times its bind, offsets and surface, with a climber's scene-made clip `scene_man` up 0.3 m over 1 m of route
    (its ground 1 m up in the scene); `shorter` the toy's clips posed on a body 5 cm shorter in the leg (the foot 0.45
    m under the Hips at 0.47 m) played with no build: standing, walking 1 m along x, floating its still foot up to 7 mm
    over a second, jumping 10 cm on frames 4 and 5, sitting (upside down, its other skin under its foot 2 cm up), the
    floating one's Kimodo motion carrying its foot contacts (the jumping one's none); `toe stored` the toe rig's
    tipped foot as saved and `toes lifted` it with its toes lifted."""
    rig = toy_rig()
    rig["clip_standing"][:, 1, 1, 3] = 0.5  # the clip's Hips travel: its height over the Root
    big = np.array(rig["bind"])
    big[:, :3, 3] *= 1.1
    offsets = np.array([np.linalg.inv(big[parent])[:3, :3] @ (big[joint][:3, 3] - big[parent][:3, 3])
                        for joint, parent in enumerate(np.clip(rig["parents"], 0, None))])
    built = {"bind": big, "offsets": offsets, "source_points": rig["points"] * 1.1}
    person, size = sim_body.person_rig(rig, built)
    climb = np.array(rig["clip_standing"])
    ground = np.linspace(0.0, 0.3, len(climb))
    climb[:, 1, 0, 3], climb[:, 1, 1, 3] = np.linspace(0.0, 1.0, len(climb)), ground + 0.5
    plan = {"clip": "scene_man", "placement": {"origin": [4.0, 1.0, 2.0], "turn": 90.0},
            "route": [[4.0 + along, 1.0 + up, 2.0] for along, up in zip(np.linspace(0.0, 1.0, len(climb)), ground)]}
    person["clip_scene_man"] = sim_body.route_clip(rig, built, {**rig, "clip_scene_man": climb}, plan)
    stored = toy_rig()
    turned, along = np.eye(4), np.eye(4)
    turned[:3, :3] = [[0, 0, 1], [0, 1, 0], [-1, 0, 0]]  # 90 degrees about y
    along[0, 3] = 1.0
    stored["clip_turn"] = np.array([[turned, np.eye(4), along, np.eye(4), np.eye(4)]])
    short = toy_rig()
    short["clip_standing"][:, 1, 1, 3] = 0.47
    short["clip_standing"][:, 2, 1, 3] = -0.45
    short["clip_walking"] = np.array(short["clip_standing"])
    short["clip_walking"][:, 1, 0, 3] = np.linspace(0.0, 1.0, 10)
    short["clip_floating"] = np.repeat(short["clip_standing"][:1], 30, axis=0)  # a second, as the pickup's float
    short["clip_floating"][:, 1, 1, 3] += 0.007 * np.sin(np.linspace(0.0, np.pi, 30)) ** 2
    short["clip_jumping"] = np.array(short["clip_standing"])
    short["clip_jumping"][4:6, 1, 1, 3] += 0.1
    short["clip_sitting"] = np.array(short["clip_standing"])
    short["clip_sitting"][:, 1, :3, :3] = np.diag([1.0, -1.0, -1.0])
    short["clip_sitting"][:, 1, 1, 3] = -0.48 - 0.03  # less the 3 cm lift the standing clip gives every clip
    (tmp_path / "motions").mkdir()
    np.savez(tmp_path / "motions" / "floating.npz", foot_contacts=np.ones((30, 6), dtype=bool))
    np.savez(tmp_path / "motions" / "jumping.npz", root_positions=np.zeros((10, 3)))
    contacts = sim_body.contacts_of(tmp_path, short)
    shorter, unbuilt = sim_body.person_rig(short, None, contacts)
    toe = toe_rig()
    return {"stored": stored, "built": person, "shorter": shorter, "toe stored": toe,
            "toes lifted": {**toe, "clip_tipped": sim_body._body.toes_lifted(toe, toe["clip_tipped"])}}, {
        "built": size, "shorter": unbuilt, "contacts": contacts, "short": short}


ROUTE = np.linspace(0.0, 0.3, 10)  # the climber's route's ground
# (world, clip, what: a joint's segment frame or the left foot's lowest skin, axis, (low, high) on every frame)
PLAYED = [
    ("built", "standing", "Hips", 1, near(0.55)),  # the Hips travel 1.1 times the clip's
    ("built", "standing", "LeftFoot", 1, near(0.0)),  # the LeftFoot at its built offset under it
    ("built", "standing", "LeftToeEnd", 1, near(0.0)),  # an end site goes with the segment that carries it
    ("built", "scene_man", "Hips", 0, near(np.linspace(0.0, 1.0, 10))),  # along its route, never 1.1 m
    ("built", "scene_man", "Hips", 1, near(ROUTE + 0.55)),  # up its steps, its hips its own height over them
    ("built", "scene_man", "LeftFoot", 1, near(ROUTE)),  # its foot on the route's ground
    ("stored", "turn", "LeftFoot", slice(None), near([[0.0, 0.0, -1.0]])),  # chained down the tree
    ("shorter", "standing", "LeftFoot", 1, near(0.0, 1e-9)),  # its foot on the bind's ground, not 2 cm under
    ("shorter", "walking", "Hips", 1, near([0.5] * 10)),  # lifted by the same 3 cm, not floating 2 cm
    ("shorter", "walking", "LeftFoot", 1, near([0.0] * 10, 1e-9)),
    ("shorter", "walking", "Hips", 0, near(np.linspace(0.0, 1.0, 10))),  # its travel along the ground as it was
    ("shorter", "floating", "LeftFoot", 1, near([0.0] * 30, 0.999e-3)),  # stood on every frame, not 7 mm up
    ("shorter", "floating", "Hips", 0, near([0.5] * 30)),  # Kimodo's correction (its stand-in: 0.5 m along x) kept
    ("shorter", "jumping", "LeftFoot", 1, near([0.0] * 4 + [0.1] * 2 + [0.0] * 4, 1e-6)),  # its flight kept
    ("shorter", "jumping", "Hips", 0, near([0.0] * 10)),  # no correction: Kimodo gave it no contacts
    ("shorter", "sitting", "LeftFoot", 1, near([0.02] * 10, 1e-6)),  # carried by its other skin, foot left up
    ("shorter", "sitting", "Hips", 1, near([-0.48] * 10)),
    ("toe stored", "tipped", "sole", None, ([-np.inf, -1e-9], [np.nextafter(-0.01, -1.0), 1e-9])),  # toes under
    ("toes lifted", "tipped", "sole", None, ([-sim_body._body.TOE_FLOOR, -1e-9], [np.nextafter(0.003, 0.0), 1e-9])),  # bent onto it
]


def test_a_body_doing_its_clip_stands_on_its_ground_within_its_residual(tmp_path, monkeypatch):
    """Every clip played on its rig: each row's segment (an end site read through the segment carrying it) or foot
    skin within its bounds on every frame; the build's size, and Kimodo's correction run on the floating clip alone,
    handed it stood, its toes then lifted, the toe base never moved."""
    handed, lifted = [], []

    def contacted(local, names, parents, bind, given):
        """Kimodo's correction's stand-in (MotionCorrection is not run here: its numbers are on #70): the clip it is
        handed with its Root moved 0.5 m along x."""
        handed.append((local, len(given)))
        moved = np.array(local)
        moved[:, 0, 0, 3] += 0.5
        return moved
    monkeypatch.setattr(sim_body._body.played, "contacted", contacted)
    toes_lifted = sim_body._body.toes_lifted
    monkeypatch.setattr(sim_body._body, "toes_lifted",
                        lambda rig, local: lifted.append(local) or toes_lifted(rig, local))
    worlds, made = clip_worlds(tmp_path)
    assert sim_body.segments_of(toy_rig()) == ([1, 2], [1, 1, 2, 1, 2])
    assert made["built"] == pytest.approx(1.1) and sim_body.standing_height(worlds["built"]) == pytest.approx(1.1)
    assert made["shorter"] == 1.0 and np.asarray(worlds["shorter"]["bind"]) == pytest.approx(made["short"]["bind"])
    assert list(made["contacts"]) == ["floating"] and made["contacts"]["floating"].shape == (30, 6)
    assert [count for _, count in handed] == [30] and len(lifted) == 2  # the floating clip's, then the tipped foot's
    assert lifted[0] == pytest.approx(worlds["shorter"]["clip_floating"])  # the corrected clip's toes lifted after
    assert np.abs(sim_body.clip_frames({**worlds["shorter"], "clip_floating": handed[0][0]}, "floating",
                                       [1, 2])[:, 1, 1, 3]).max() < 0.001  # handed the stood clip
    toe, stored = worlds["toes lifted"], worlds["toe stored"]
    assert toe["clip_tipped"][1] == pytest.approx(stored["clip_tipped"][1])  # a foot on its floor left as it is
    assert sim_body._body.played.chained(toe["clip_tipped"], toe["parents"])[:, 3, :3, 3] == pytest.approx(
        sim_body._body.played.chained(stored["clip_tipped"], stored["parents"])[:, 3, :3, 3])  # the toe base kept
    for world, clip, what, axis, (low, high) in PLAYED:
        rig = worlds[world]
        if what == "sole":
            got = sim_body._body.foot_lowest(rig, rig[f"clip_{clip}"], sim_body._body.FEET[0])
        else:
            kept, carriers = sim_body.segments_of(rig)
            segment = kept.index(carriers[[str(name) for name in rig["names"]].index(what)])
            got = sim_body.clip_frames(rig, clip, kept)[:, segment, :3, 3][:, axis]
        assert np.all((low <= got) & (got <= high)), f"{world} {clip} {what}: {got} not within {low}..{high}"
