"""The sim body stage (score/stages/sim_body): a person's rig is read at its own build and weighed by #64's rule, its
clip's frames chain down the tree, the model is fetched only as pinned, and each gate fails its break.

On a toy rig made here (a closed 0.2 x 1 x 0.2 m column: Root at 0, Hips at 0.5 m, LeftFoot at 0 m, the end sites): the
root and each end site go to the segment that carries them. The mass is the stated weight, else the height squared times
the BMI of the stated sex (NCD-RisC 2016: a 1.80 m woman 80.35 kg), else the mean of both at the SOMA body's own
height, marked estimated (the make's ann, eve and fay). A built
body 1.1 times the rig plays its clips 1.1 times as far. A clip whose offsets are shorter than its rig's bind (as
people-clips-made's are: posed on SOMA's zero-identity body, 7 cm shorter than the template its bind is, #70) is played
on the bind's own bones and lifted so its standing frame's feet are where the bind's are, every clip by the same lift,
as the people build plays it (`tools.characters.played`, prop_build.py's arithmetic): its feet stand on its ground; a
clip floating its still foot 7 mm mid-clip stands it on its ground on every frame, a jump keeps its flight. A clip's frames chain
down the tree (a root turned 90 degrees about up carries a child 1 m along x to -1 m along z). The model's wheel is
unpacked only when its sha256 is the pinned one (a make whose model is pinned at another stops). On runs written here
(no engine): a good run passes every gate, a body
5 cm into its ground fails `on floor`, a landed foot 5 cm off its ground fails `lands` and so does a body no foot of
which lands, unless it sits and its ground carries it (a seated body its ground never carries fails), a ground that pushes 10% under the weight fails `carries`, a segment 10 degrees off the clip fails
`follows` and so does RRA's move of a segment 6 degrees or the pelvis 2.5 cm off the fitted path in one frame, a
residual force over 2% of the weight or a moment over 1% of it times the centre's height fails `residual`, a body
shaking a degree each frame round its clip's swing fails `smooth` and one moving as its clip does passes. The make on
the toy, over a toy seed whose ground is one raised square, its run the real one on rented cards of kind sim-body (the
machine path stood in, writing a written run; two clips a card), hands each body
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

Breaks that turn the one test red (each applied once and seen red, reverted, 2026-10-27; 2026-11-13 the file folded
into its one test, every break below seen red on it again):
- its root and end sites going to their carrier: segments_of's carrier `joint = parents[joint]`
  made `joint = -1`.
- its mass: mass_of's `tall ** 2` made `tall`.
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
- its model unpacked only as pinned: fetched's sha256 check dropped.
- its gates on the written runs: judge_on_floor's `> SUNK_MOST` made `> 1.0`; judge_lands'
  `> LANDED` made `> 1.0`; landings' `push >= CONTACT * weight` made `push >= 0`; judge_carries'
  `abs(... - 1.0) > CARRIED` made `> 1.0`; judge_follows' `> FOLLOWED` made `> 90`; judge_residual's force check
  dropped; its moment check dropped; RESIDUAL_FORCE 0.02 made 0.05 (2026-10-28); judge_follows' per-frame turn
  check dropped; its pelvis check dropped (2026-10-28); landing_fault's seated `return None if ... else` made
  `return None` (a seated body its ground never carried passes), and `body.get("clip") in SEATED` made `False` (a
  seated body its seat carries fails "no foot landed"; 2026-11-04); judge_smooth's `> ...["clip jerk deg"]` made
  `> 1e9` (a body shaking 1 degree every other frame round its clip's swing passes), and measured's clip jerk of
  `frame["targets"]` made `frame["angles"]` (the body judged against itself)
  (2026-11-05).
- its make on the place's cast, 2026-10-28: make's `adjusted=entry["adjusted"]`
  dropped (the RRA adjustment not recorded); make's job `"adjust"` dropped (the run gets no cap).
- its make on the place's cast: ground_of's `np.linalg.inv(frame)` made `frame`;
  own_frame's `turn + TURNED` made `turn`; make's `if not len(ground)` check dropped; write_layer's
  `points @ carried[:3, :3].T + carried[:3, 3]` made `points` (a ridden bone drawn in its body's frame, not its
  segment's); its colour's `shade` made 0; the record's `"attribution": ATTRIBUTION` made `""`.
- its make on the place's cast, 2026-10-28 (#70): make's `frame["poses"] =
  [soma_pose(world) ...]` made `pass` (the run's moved poses kept); soma_pose's `world[:3, 3]` rounded to 2 places;
  make's targets `points=rig["points"]` made `rig["bind"]` (the mesh not handed to the sizing).
- its make on the place's cast, 2026-10-28 (#70's solver): make's
  `"calibrated on": CALIBRATED_ON` made `"the rig's standing clip"`.
- its make on the place's cast, 2026-11-04: left_out_why's climber check dropped
  (the climber walks the flat clip through its steps).
- its make on the place's cast, 2026-11-02: on_card's targets' folders dropped
  from its inputs (the machine has no targets).
- its make on the place's cast, 2026-11-06 (every sim body run on a card): ran's
  `os.environ.get(LOCAL) == "1"` made `True` (the run on this PC); on_card's `kind=KIND` dropped (rented as a Blender
  job); batched's `PER_MACHINE` made 1 (a card a clip; the constant made 1: the price's cards); ran_elsewhere's
  people merge kept the first card's alone;
  card_minutes' high `clips * CLIP_HIGH_MINUTES` made `clips * CLIP_MINUTES` (the high reserved at the likely).
- its casts' make, 2026-10-30 (#70): output_faults'
  `"no bodies" not in` check dropped (the crowd-only cast failed again); no_singles' `cast["characters"]` made `True`.
- its casts' make, 2026-10-30 (#70): no_singles'
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


def frames(count, lowest=0.001, push=1.0, off=0.0, weight=100.0, foot=0.003, foot_push=0.5, residual=(0.6, 0.0, 0.8),
           moment=(0.0, 0.0, 0.0), shake=None):
    """A written run of `count` frames: two segments, the ground pushing `push` of `weight`, `foot_push` of it through
    one foot `foot` m over it, the body `off` degrees about x from the clip on each segment, a residual; with `shake`,
    the clip swinging smoothly about x and the body following it `shake` degrees off every other frame."""
    run = [{"angles": [[off, 0.0, 0.0], [off, 0.0, 0.0]], "targets": [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0]],
            "torques": [1.0, -3.0], "ground": [0.0, push * weight, 0.0], "lowest": lowest,
            "feet": {"LeftFoot": [foot, foot_push * weight], "RightFoot": [0.3, 0.01 * weight]},
            "residual": [*residual, *moment], "reserve": 0.5, "activations": [0.1, 0.4], "forces": [20.0, 300.0],
            "poses": []} for _ in range(count)]
    if shake is not None:
        for number, frame in enumerate(run):
            wanted = [[30 * np.sin(number / 6), 0.0, 0.0]] * 2
            frame.update(targets=wanted, angles=[[wanted[0][0] + shake * (-1) ** number, 0.0, 0.0]] * 2)
    return run


def judged(folder, run, turn=3.0, pelvis=1.5, clip="walking"):
    """The gates on a written run of `clip` whose RRA moved a segment `turn` degrees and the pelvis `pelvis` cm at
    most: their answers and the run's measures."""
    adjusted = {"largest turn deg": turn, "pelvis cm": [0.5, pelvis]}
    measures = sim_body.measured({"frames": run, "kg": 10.0, "com height": 1.0, "adjusted": adjusted}, 10.0)
    (folder / sim_body.RECORD).write_text(json.dumps({"bodies": {"one": {"clip": clip, "measures": measures}}}))
    return {check.name: check.judge(folder, {}, {}).answer for check in sim_body.CHECKS}, measures


PASSED = dict.fromkeys(("on floor", "lands", "carries", "follows", "residual", "smooth"), checks.PASS)
# (the run, frames(40, ...)'s arguments, judged's arguments, the gates' answers, its measures, its turns rougher than
# its clip's); the weight 100 N, so the residual's limits 2 N and 1 N m
GATED = [
    ("good", {}, {}, PASSED, {"largest torque Nm": 3.0, "largest residual N": 1.0, "largest muscle force N": 300.0,
                              "frames within residual limits": 1.0, "landings": 40}, False),  # the right foot unloaded
    ("5 cm into its ground", {"lowest": -0.05}, {}, {"on floor": checks.FAIL}, {}, False),
    ("its landed foot 5 cm off", {"foot": 0.05}, {}, {"lands": checks.FAIL}, {}, False),
    ("no foot lands", {"foot_push": 0.0}, {}, {"lands": checks.FAIL}, {}, False),
    ("sitting, its seat carries", {"foot_push": 0.0}, {"clip": "sitting"}, {"lands": checks.PASS}, {}, False),
    ("sitting, nothing carries", {"push": 0.0, "foot_push": 0.0}, {"clip": "sitting"}, {"lands": checks.FAIL}, {},
     False),
    ("its ground 10% under", {"push": 0.9}, {}, {"carries": checks.FAIL}, {}, False),
    ("10 degrees off its clip", {"off": 10.0}, {}, {"follows": checks.FAIL}, {"mean off clip deg": pytest.approx(10.0)},
     False),
    ("RRA turned a segment 6 degrees", {}, {"turn": 6.0}, {"follows": checks.FAIL}, {}, False),
    ("RRA moved the pelvis 2.5 cm", {}, {"pelvis": 2.5}, {"follows": checks.FAIL}, {}, False),
    ("a residual force of 2.5 N", {"residual": (0.0, 2.5, 0.0)}, {}, {"residual": checks.FAIL},
     {"frames within residual limits": 0.0}, False),
    ("a residual moment of 1.1 N m", {"moment": (1.1, 0.0, 0.0)}, {}, {"residual": checks.FAIL}, {}, False),
    ("shaking a degree round its clip's swing", {"shake": 1.0}, {}, {"smooth": checks.FAIL}, {}, True),
    ("moving as its clip does", {"shake": 0.0}, {}, {"smooth": checks.PASS}, {}, False),
]


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


def make_inputs(folder):
    """The make's inputs under `folder`: the toy rig whose standing clip runs twenty frames, its Hips rising and its
    shin bent off the bind, Kimodo's own foot contacts beside it (as people-clips-made keeps them), the toy seed; and
    the model's wheel. Returns (inputs without the cast, the rig, the wheel)."""
    rig = toy_rig()
    rig["clip_standing"] = np.concatenate([rig["clip_standing"]] * 2)
    rig["clip_standing"][:, 1, 1, 3] = np.linspace(0.5, 0.6, 20)
    bent = np.eye(4)
    bent[1:3, 1:3] = [[np.cos(0.2), -np.sin(0.2)], [np.sin(0.2), np.cos(0.2)]]
    rig["clip_standing"][:, 2] = rig["clip_standing"][:, 2] @ bent
    (folder / "clips/motions").mkdir(parents=True)
    np.savez(folder / "clips/rig.npz", **rig)
    np.savez(folder / "clips/motions/standing.npz", foot_contacts=np.ones((20, 6), dtype=bool))
    toy_seed(folder / "seed")
    wheel = folder / "wheel" / "model.whl"
    wheel.parent.mkdir()
    with zipfile.ZipFile(wheel, "w") as packed:
        packed.writestr("musclemimic_models/model/body/myofullbody.xml", "<mujoco/>")
    return {sim_body.CLIPS_ROW: str(folder / "clips"), "seed": str(folder / "seed")}, rig, wheel


def written_run(job):
    """A written engine run for each of the job's people: Hips and LeftFoot each riding a bone 0.1 m up its segment's
    own frame, one muscle of two points, twenty frames, each with poses moved 0.6 m up (as the run wrote them before
    #70: the stage must not keep them)."""
    people, arrays = {}, {}
    for person in job["people"]:
        name = person["name"]
        written = []
        for _ in range(20):
            frame = frames(1, weight=person["kg"] * 1.62)[0]
            frame.update(poses=[[0.0, 0.6, 0.0, 0.0, 0.0, 0.0, 1.0], [0.0, 0.6, 0.0, 0.0, 0.0, 0.0, 1.0]],
                         activations=[1.0], forces=[100.0])
            written.append(frame)
        people[name] = {"rides": {"Hips": "pelvis", "LeftFoot": "tibia_l"}, "model": {"kg": person["kg"]},
                        "muscles": ["soleus_l"], "bones": ["pelvis", "tibia_l", "talus_l"], "kg": person["kg"],
                        "com height": 0.5, "frames": written,
                        "adjusted": {"pelvis cm": [0.5, 1.2], "largest turn deg": 3.0, "mass %": -1.0}}
        bones = np.zeros((20, 3, 7))
        bones[:, :, 6] = 1.0
        bones[:, 0, 1], bones[:, 1, 1] = 0.6, 0.1  # each ridden bone 0.1 m up its segment
        riders = np.zeros((20, 2, 7))
        riders[:, :, 6] = 1.0
        riders[:, 0, 1] = 0.5  # the Hips segment 0.5 m up, the LeftFoot at the origin
        arrays.update({f"{name}/bones": bones, f"{name}/segments": riders,
                       f"{name}/paths": np.tile([[0.0, 0.4, 0.0], [0.0, 0.1, 0.0]], (20, 1)).astype(np.float32),
                       f"{name}/counts": np.full((20, 1), 2, dtype=np.int32)})
        for bone in people[name]["bones"]:
            arrays[f"{name}/mesh/{bone}/points"] = np.array([[0, 0, 0], [0.1, 0, 0], [0, 0.1, 0]], dtype=np.float32)
            arrays[f"{name}/mesh/{bone}/faces"] = np.array([[0, 1, 2]], dtype=np.int32)
    return {"engine": "rented", "rate": 30, "people": people}, arrays


def rented(seen):
    """blender_cloud's machine path stood in: each card hired is kept in seen["hired"] (its classes, minutes, kind),
    each job run on one in seen["ran"] (script, arguments, inputs, outputs, env, the job, its people's targets read),
    its run written by written_run."""
    class Machine:
        def __init__(self, classes, who, minutes, kind):
            seen["hired"].append((classes, minutes, kind))

        def __enter__(self):
            return self

        def run(self, script, arguments, inputs, outputs, minutes, env):
            job = json.loads(arguments[0].read_text())
            seen["ran"].append((script, arguments, inputs, outputs, env, job,
                                {person["name"]: dict(np.load(person["targets"])) for person in job["people"]}))
            found, arrays = written_run(job)
            outputs[0].write_text(json.dumps(found))
            np.savez(outputs[1], **arrays)

        def __exit__(self, *_):
            pass
    return types.SimpleNamespace(Machine=Machine, SETUP_MINUTES=8)


SINGLES = [{"name": "ann", "doing": "standing", "at": [1.0, 0.0, 2.0], "turn": 30.0, "weight": 50.0},
           {"name": "bob", "doing": "flying", "at": [0.0, 0.0, 0.0]},  # a clip the rig lacks
           {"name": "cid", "doing": "standing", "at": [50.0, 0.0, 50.0]},  # no solid near
           {"name": "dee", "doing": "standing", "at": [1.0, 0.0, 2.0],  # a climber with no scene-made clip
            "stairs": {"way": "up", "flight": "stair_1", "to": [1.0, 1.0, 3.0], "rise": 0.2, "run": 0.2}},
           {"name": "eve", "doing": "standing", "at": [0.0, 0.0, 1.0], "height": 1.8, "sex": "female"},
           {"name": "fay", "doing": "standing", "at": [2.0, 0.0, 4.0]}]
CROWD = {"name": "crowd"}
LACKING = "no sim body: the cast names no character whose clip the rig holds"
# (the cast, its crowd and singles, its model pinned at the wheel's own sha256, the error the make raises, its bodies,
# the names it leaves out, its record's `no bodies`, its output's faults, the people on each rented card, the gates'
# answers where judged: the place's written runs carry a fixed 1 N residual, over fay's 2%)
CASTS = [
    ("the place's", {"crowd": CROWD, "characters": SINGLES}, True, "", ["ann", "eve", "fay"],
     ["bob", "cid", "dee", "crowd"], None, [], [["ann", "eve"], ["fay"]], None),
    ("the place's, its model not as pinned", {"crowd": CROWD, "characters": SINGLES}, False, "sha256", [], [], None,
     [], [], None),
    ("a crowd and no singles", {"crowd": CROWD, "characters": []}, True, "", [], ["crowd"], sim_body.NO_SINGLES, [],
     [], PASSED),
    ("a single whose clip the rig lacks", {"characters": SINGLES[1:2]}, True, "", [], ["bob"], None, [LACKING], [],
     None),
    ("empty", {"characters": []}, True, "", [], [], None, ["empty cast: no single characters and no crowd"], [], None),
]


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
    """Every clip played on its rig, each row's segment or foot skin within its bounds on every frame; every written
    run judged by the gates as its row says; the make run on each cast through the real run's rented cards: who gets a
    body and who is left out by name, each body weighed, stood on its own ground, calibrated, its run on its card, its
    layer written and its SOMA poses kept bit for bit; the price of the clips."""
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
    (tmp_path / "played").mkdir()
    worlds, made = clip_worlds(tmp_path / "played")
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

    (tmp_path / "judged").mkdir()
    for name, run, judging, answers, wanted, rougher in GATED:
        got, measures = judged(tmp_path / "judged", frames(40, **run), **judging)
        assert {gate: got[gate] for gate in answers} == answers, name
        assert {key: measures[key] for key in wanted} == wanted, name
        assert (measures["jerk deg"] > measures["clip jerk deg"] > 0) == rougher, name

    inputs, rig, wheel = make_inputs(tmp_path / "inputs")
    sha = hashlib.sha256(wheel.read_bytes()).hexdigest()
    monkeypatch.setattr(sim_body, "HOME", tmp_path / "home")
    monkeypatch.setattr(sim_body, "gravity_of", lambda place, inputs: ("moon", 1.62))
    monkeypatch.setattr(sim_body, "PER_MACHINE", 2)  # three clips: two on one card, one on another
    monkeypatch.delenv(sim_body.LOCAL, raising=False)
    monkeypatch.setattr(sim_body.subprocess, "run", lambda *_, **__: pytest.fail("ran on this PC"))
    outs = {}
    for name, cast, pinned, error, bodies, left, reason, faults, cards, gates in CASTS:
        folder = tmp_path / "made" / name
        (folder / "cast").mkdir(parents=True)
        (folder / "cast/cast.json").write_text(json.dumps({"place": "toy", **cast}))
        monkeypatch.setattr(sim_body, "MODEL", (wheel.as_uri(), sha if pinned else "0" * 64))
        seen = {"hired": [], "ran": []}
        monkeypatch.setattr("score.adapters.engines.machine_runner", lambda seen=seen: rented(seen))
        (folder / "out").mkdir()
        try:
            sim_body.make({**inputs, "cast": str(folder / "cast")}, folder / "out", 0, {})
            raised = ""
        except ValueError as fault:
            raised = str(fault)
        assert bool(raised) == bool(error) and error in raised, f"{name}: raised {raised!r}"
        if raised:
            continue
        record = json.loads((folder / "out" / sim_body.RECORD).read_text())
        assert sorted(record["bodies"]) == bodies, name
        assert [line.split(":")[0] for line in record["left out"]] == left, name
        assert record.get("no bodies") == reason and sim_body.output_faults(folder / "out") == faults, name
        assert sorted(sorted(person["name"] for person in job["people"]) for *_, job, _ in seen["ran"]) == cards, name
        if gates:
            assert {check.name: check.judge(folder / "out", {}, {}).answer for check in sim_body.CHECKS} == gates, name
        outs[name] = folder / "out", record, seen
    out, record, seen = outs["the place's"]

    # the run: on rented cards of kind sim-body, its clips batched, its files at their paths, its parts gone
    # each make with a body has its one build's standing clip given Kimodo's correction (the place's cast's, then its
    # unpinned model's before the model stops it); a cast with no body plays none
    assert [count for _, count in handed] == [30, 20, 20]
    assert sorted(seen["hired"]) == [(list(sim_body.CLASSES), sim_body.card_minutes(1)[1], "sim-body"),
                                     (list(sim_body.CLASSES), sim_body.card_minutes(2)[1], "sim-body")]
    ran = sorted(seen["ran"], key=lambda card: card[5]["people"][0]["name"])
    model = sim_body.HOME / "models" / sha[:16]
    for number, (script, arguments, given, outputs, env, job, targets) in enumerate(ran):
        part = out / f"job-{number}.json"
        assert (script, arguments, given, outputs, env) == (
            sim_body.REPO / sim_body.INSIDE, [part, out / f"run-{number}.json"], [part, out / "clips", str(model)],
            [out / f"run-{number}.json", out / f"run-{number}.npz"], sim_body.REPO / sim_body.ENV_SCRIPT)
        assert job["model"] == str(model) and job["adjust"]["follows deg"] == sim_body.FOLLOWED
        assert job["residual"]["force"] == 0.02
        for person in job["people"]:
            assert person["segments"] == ["Hips", "LeftFoot"] and "standing" not in person  # the static table (#70)
            assert targets[person["name"]]["points"] == pytest.approx(rig["points"])  # the mesh the sizing reads
            assert targets[person["name"]]["ground"][:, :, 1] == pytest.approx(0.1)
    assert (model / "musclemimic_models/model/body/myofullbody.xml").read_text() == "<mujoco/>"
    assert sorted(path.name for path in out.glob("*-[0-9].*")) == []
    # the square's corner (3, 5) is (2, 3) from ann's spot: turned back her 30 degrees and the dressed body's Turned
    # 180 about up, (-0.232, -3.598) (without the Turned: (0.232, 3.598), the ground mirrored)
    ground = ran[0][6]["ann"]["ground"]
    assert np.abs(ground.reshape(-1, 3)[:, [0, 2]] - [1.5 - 2 * np.cos(np.pi / 6), -1 - 3 * np.cos(np.pi / 6)]).sum(
        axis=1).min() == pytest.approx(0.0, abs=1e-5)

    # the record: each body weighed (stated, else its height squared times its sex's BMI, else the mean of both at
    # the SOMA body's height) under the scene's gravity, on its ground, calibrated, adjusted; the model attributed
    assert record["engine"] == "rented" and ran[0][5]["people"][0]["kg"] == 50.0
    assert {name: body["mass"] for name, body in record["bodies"].items()} == {
        "ann": {"kg": 50.0, "source": "stated weight"},
        "eve": {"kg": pytest.approx(80.35), "source": "estimated", "height": 1.8, "height from": "stated",
                "sex": "female", "bmi": 24.8},
        "fay": {"kg": pytest.approx(24.65), "source": "estimated", "height": 1.0,
                "height from": "the SOMA body's own standing height", "sex": "not stated", "bmi": 24.65}}
    for name, body in record["bodies"].items():
        assert body["measures"]["weight N"] == round(body["mass"]["kg"] * 1.62, 2), name
        assert body["segments"] == {"Hips": "pelvis", "LeftFoot": "tibia_l"}, name
        assert body["ground"] == {"solids": ["Ground/Ground"], "triangles": 2}, name
        assert body["calibrated on"] == sim_body.CALIBRATED_ON, name
        assert body["adjusted"] == {"pelvis cm": [0.5, 1.2], "largest turn deg": 3.0, "mass %": -1.0}, name
    assert record["bodies"]["ann"]["measures"]["weight N"] == pytest.approx(81.0)
    assert "no scene-made clip up its stairs (stair_1)" in record["left out"][2]  # a climber never walks flat
    assert "Holzbaur" in record["model"]["attribution"] and "Apache-2.0" in record["model"]["attribution"]

    # the layer: each segment an Xform holding the bone it rides, another bone under Bones, the muscles coloured by
    # activation; SOMA's joints leave the stage unchanged: every frame's poses the clip's own segment frames as the
    # stage plays it (person_rig, Kimodo's correction given), bit for bit
    from scipy.spatial.transform import Rotation
    stage = Usd.Stage.Open(str(out / sim_body.LAYER))
    cache = UsdGeom.XformCache(5)
    contacts = sim_body.contacts_of(inputs[sim_body.CLIPS_ROW], rig)
    clip = sim_body.clip_frames(sim_body.person_rig(rig, None, contacts)[0], "standing", [1, 2])
    for name in record["bodies"]:
        root = f"/toy/Characters/{name}/SimBody"
        bone = stage.GetPrimAtPath(f"{root}/LeftFoot/bone_tibia_l")
        first = UsdGeom.Mesh(bone).GetPointsAttr().Get()[0]
        assert cache.GetLocalToWorldTransform(bone).Transform(Gf.Vec3d(first))[1] == pytest.approx(0.1), name
        assert stage.GetPrimAtPath(f"{root}/Bones/bone_talus_l/bone_talus_l").IsA(UsdGeom.Mesh), name
        muscles = UsdGeom.BasisCurves(stage.GetPrimAtPath(f"{root}/Muscles"))
        assert list(muscles.GetCurveVertexCountsAttr().Get(5)) == [2], name
        assert tuple(UsdGeom.PrimvarsAPI(muscles).GetPrimvar("displayColor").Get(5)[0]) == pytest.approx(
            sim_body.ACTIVE, abs=1e-6), name
        measures = json.loads((out / f"measures/{name}.json").read_text())
        assert len(measures) == len(clip) == 20, name
        for frame, segments in zip(measures, clip):
            for pose, world in zip(frame["poses"], segments):
                assert pose[:3] == list(world[:3, 3]) and Rotation.from_quat(pose[3:]).as_matrix() == pytest.approx(
                    world[:3, :3], abs=1e-12), name

    # priced from measured minutes: seven clips' high on one card, no clip free, the forecast its cast's singles; the
    # kind's classes capacity's, an L4 first, parked clean
    monkeypatch.undo()
    from score.adapters import engines
    engines.machine_runner()  # tools/cloud on the path
    import capacity
    import park
    assert capacity.order_for(sim_body.KIND)[0] == sim_body.CLASSES[0] == "gpu-24gb"
    assert set(sim_body.CLASSES) <= set(capacity.classes_for(sim_body.KIND)) and sim_body.KIND in park.CLEANUPS
    assert park.CLEANUPS[sim_body.KIND]({"paths": {"/home/x/job.json", "/root/lib/envs"}}) == "rm -rf /home/x/job.json"
    assert sim_body.priced(7)["euros"] == sim_body.EUROS and sim_body.priced(7)["cards"] == 1
    assert sim_body.priced(0)["euros"] == 0.0
    assert sim_body.priced(sim_body.PER_MACHINE + 1)["cards"] == 2
    assert sim_body.forecast({"cast": str(tmp_path / "made/the place's/cast")}) == sim_body.priced(len(SINGLES))
