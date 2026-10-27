"""The physics stage (score/stages/physics): its trial comes from the design and each of its gates fails its break.

From a design (design.py) on a small place made here (tools/usd's physics test's toy room): the loose rows' laid
objects are dropped back onto their own spots, one with a shelf over it left out, the table (no loose row) never; the
trial's layers write with each drop landing where it stood; the gravity is the body's under the scene's top site (the
Moon's 1.62 m/s², Mars's 3.71: the textbook values); the `designed` gate fails a body no inventory row has; a trial
with no hinge passes only when it says why. The trial runs on the held card in its own Python (Newton's, built by
inside/newton_env.sh) and the renders in Blender, its outputs whole. On a run written here (no engine): a run where the drops land, the door
opens within its limits and the energy only falls passes every gate; each gate fails its own fault (a drop that ends
under its target, a door past its limit, a rise while nothing drives, a body still moving, inside a static or under
its own floor); the energy's rises are per undriven stretch; the trial's copy keeps the shown places, less the
contract.

Breaks that turn each check red (each applied once and seen red, reverted, 2026-10-27):
- the_loose_rows_drop_where_they_stand: design.falls' `return drop, not physics.faults(...)` made `return drop, True`
  (a blocked fall dropped).
- the_gravity_is_the_body_s_under_the_top_site: design.ground's `holder = within[holder]` made `holder = place` (no
  climb up the holders).
- a_body_no_row_has_fails_designed: judge_designed's `strangers = row_kinds.strangers(...)` made `strangers = []`.
- a_trial_with_no_hinge_passes_only_when_it_says_why: judge_hinge's `checks.PASS if said else checks.UNKNOWN` made
  `checks.PASS`.
- a_good_run_passes: measured's `if frozenset((name, path.removesuffix("/geo"))) not in joined` dropped (a leaf
  against its own frame counted inside a static).
- a_drop_under_its_target_fails_reacted: judge_reacted's `if not LANDED[0] <= drop["over top at end"] <= LANDED[1]`
  made `if False`.
- a_door_past_its_limit_fails_hinge: judge_hinge's `or hinge["most"] > hinge["upper"] + LIMIT_SLACK` dropped.
- an_undriven_rise_fails_energy: judge_energy's `if rise > max(ENERGY_SLACK[0] * abs(start), ENERGY_SLACK[1])` made
  `if rise > 1e9`.
- a_body_moving_inside_or_under_its_floor_fails_at_rest: measured's `"floor": min(body["lowest"][0], ...)` made
  `"floor": 0.0` (made ground is not at 0: the stool at -1.5 m read as under its floor).
- the_rises_are_per_undriven_stretch: energy_rises without its `begun = None` on a driven frame.
- the_trial_runs_in_its_own_python_on_the_held_card: make_trial's `TRIAL_MINUTES, env=REPO / TRIAL_ENV)` made
  `TRIAL_MINUTES)` (the trial sent to the card's Blender).
- the_trial_stands_the_shown_places_from_the_neighbours_output: trial_folder's copytree without
  `ignore=shutil.ignore_patterns("contract.json")`.

Run: .venv/bin/python score/stages/physics/test_the_trial_comes_from_the_design_and_each_gate_fails_its_break.py
"""
import json
import pathlib
import shutil
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tools/usd"))
from pxr import Gf, Usd, UsdGeom  # noqa: E402

import test_the_physics_layers_hold_mass_drop_and_hinge as toy  # noqa: E402
from score import checks  # noqa: E402
from score.stages import physics  # noqa: E402
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


def the_loose_rows_drop_where_they_stand():
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


def the_gravity_is_the_body_s_under_the_top_site():
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


def a_body_no_row_has_fails_designed():
    with tempfile.TemporaryDirectory() as folder:
        folder = pathlib.Path(folder)
        inventory = folder / "inventory.json"
        inventory.write_text(json.dumps({"rows": [{"id": "crate", "noun": "crate"}]}))
        record = {"drops": [{"object": "crate_1"}, {"object": "stool_1"}], "hinges": [], "moved": []}
        (folder / "record.json").write_text(json.dumps(record))
        found = physics.judge_designed(folder, {"design": inventory}, None)
        assert found.answer == checks.FAIL and found.findings == ("stool_1 is no object of the scene's inventory",)
        (folder / "record.json").write_text(json.dumps(dict(record, drops=record["drops"][:1])))
        assert physics.judge_designed(folder, {"design": inventory}, None).answer == checks.PASS


def a_trial_with_no_hinge_passes_only_when_it_says_why():
    with tempfile.TemporaryDirectory() as folder:
        folder = pathlib.Path(folder)
        (folder / "measures.json").write_text(json.dumps({"hinges": {}}))
        (folder / "record.json").write_text(json.dumps({"hinges": []}))
        assert physics.judge_hinge(folder, {}, None).answer == checks.UNKNOWN
        (folder / "record.json").write_text(json.dumps({"hinges": [], "no_hinges": design.NO_HINGES}))
        assert physics.judge_hinge(folder, {}, None).answer == checks.PASS



FRAMES = 6
RECORD = {"drops": [{"object": "crate", "onto": "table"}], "moved": ["stool"]}
LAID = {"tops": {"crate": 0.76}}


def motion(dx):
    return [[1, 0, 0, dx], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]


def body(lowest, speed, moved=0.0):
    return {"mass": 10.0, "lowest": lowest, "speed": speed, "motions": [motion(0.0)] * (FRAMES - 1) + [motion(moved)]}


def a_run(**changes):
    """A run of six frames: the crate falls onto the table, the stool is pushed 0.5 m, the leaf opens 90 degrees."""
    run = {"frames": FRAMES, "rate": 24.0, "gravity": 1.62, "statics": 3,
           "bodies": {"crate": body([1.2, 1.1, 0.9, 0.77, 0.765, 0.765], [0, 1, 1, 0.5, 0.01, 0.0]),
                      "stool": body([0.0] * FRAMES, [0, 0.5, 0.5, 0.3, 0.0, 0.0], moved=0.5),
                      "leaf": body([0.01] * FRAMES, [0, 1, 1, 1, 0.02, 0.0])},
           "energy": [100.0, 99.0, 120.0, 140.0, 139.0, 138.5], "driven": [False, False, True, True, False, False],
           "hinges": {"leaf": {"frame": "/p/Objects/frame", "lower": 0.0, "upper": 100.0,
                               "angles": [0.0, 0.0, 30.0, 60.0, 90.0, 90.0]}},
           "joined": [["/p/Objects/frame", "leaf"]],
           "inside at start": {}, "inside at end": {"leaf": ["/p/Objects/frame/geo"]}}
    for path, value in changes.items():
        holder = run
        *parents, last = path.split(".")
        for name in parents:
            holder = holder[name]
        holder[last] = value
    return run


def answers(run):
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        middles = {"crate": [0, 1, 0], "stool": [0, 0.2, 0], "leaf": [0, 1.3, 0]}
        (folder / "measures.json").write_text(json.dumps(physics.measured(run, RECORD, LAID, middles)))
        return {check.name: check.judge(folder, {}, None).answer for check in physics.TRIAL_CHECKS}


def a_good_run_passes():
    found = answers(a_run())
    assert all(answer == checks.PASS for answer in found.values()), found


def a_drop_under_its_target_fails_reacted():
    assert answers(a_run(**{"bodies.crate.lowest": [1.2, 1.0, 0.5, 0.3, 0.3, 0.3]}))["reacted"] == checks.FAIL


def a_door_past_its_limit_fails_hinge():
    assert answers(a_run(**{"hinges.leaf.angles": [0.0, 0.0, 30.0, 60.0, 104.0, 99.0]}))["hinge"] == checks.FAIL


def an_undriven_rise_fails_energy():
    assert answers(a_run(energy=[100.0, 99.0, 120.0, 140.0, 139.0, 145.0]))["energy"] == checks.FAIL


def a_body_moving_inside_or_under_its_floor_fails_at_rest():
    assert answers(a_run(**{"bodies.leaf.speed": [0, 1, 1, 1, 0.5, 0.4]}))["at rest"] == checks.FAIL
    inside = {"leaf": ["/p/Objects/frame/geo"], "crate": ["/p/Objects/table/geo"]}
    assert answers(a_run(**{"inside at end": inside}))["at rest"] == checks.FAIL
    # the floor is each body's own (a drop's target top, else where it stood), not y = 0: made ground is not at 0
    assert answers(a_run(**{"bodies.stool.lowest": [2.0, 1.9, 2.0, 2.0, 2.0, 2.0]}))["at rest"] == checks.FAIL
    assert answers(a_run(**{"bodies.stool.lowest": [-1.5] * FRAMES}))["at rest"] == checks.PASS


def the_rises_are_per_undriven_stretch():
    assert physics.energy_rises([10.0, 10.5, 30.0, 20.0, 21.0], [False, False, True, False, False]) == \
        {0: (0.5, 10.0), 3: (1.0, 20.0)}


def the_trial_stands_the_shown_places_from_the_neighbours_output():
    """The layer reads the place's neighbours output where it has one (no seed, no data/scene record), and the
    trial's copy keeps the shown places under places/ beside the stage, less the contract."""
    from score import stages
    assert stages.PHYSICS_LAYER.after["neighbours"] == ("openusd-stage", 1)
    assert stages.PHYSICS_TRIAL.files == physics.TRIAL_FILES
    assert not any("seeds" in path or "data/scene" in path for path in physics.TRIAL_FILES.values())
    root = pathlib.Path(tempfile.mkdtemp())
    try:
        layer = root / "layer"
        (layer / "places/square").mkdir(parents=True)
        (layer / "flat.usda").write_text("#usda 1.0\n")
        (layer / "places/square/square.usda").write_text("#usda 1.0\n")
        (layer / "contract.json").write_text("{}")
        folder = physics.trial_folder(root / "out", "flat", layer)
        assert (folder / "flat/places/square/square.usda").is_file()
        assert not (folder / "flat/contract.json").exists()
    finally:
        shutil.rmtree(root)


class Held:
    """A stand-in for the held card: each job recorded (its script and the Python it runs in), the trial's run and
    the renders' frames written as the card would."""
    jobs = []

    def __init__(self, classes, who):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass

    def run(self, script, arguments, inputs, outputs, minutes=10, env=None):
        Held.jobs.append((str(pathlib.Path(script).relative_to(REPO)), env and str(pathlib.Path(env).relative_to(REPO))))
        if pathlib.Path(script).name == "physics_trial.py":
            names = toy.physics.bodies_of(toy.RECORD)
            still = {"mass": 1.0, "lowest": [0.5] * 3, "speed": [0.0] * 3, "motions": [motion(0.0)] * 3}
            pathlib.Path(arguments[1]).write_text(json.dumps({
                "rate": 24.0, "frames": 3, "gravity": 1.62, "statics": 1, "bodies": {name: still for name in names},
                "energy": [1.0] * 3, "driven": [False] * 3, "hinges": {}, "joined": [], "inside at start": {},
                "inside at end": {}}))
            return
        from PIL import Image
        pathlib.Path(arguments[2]).mkdir(parents=True)
        for view in json.loads(pathlib.Path(arguments[1]).read_text())["views"]:
            Image.new("RGB", (4, 4)).save(pathlib.Path(arguments[2]) / f"{view['name']}-look.png")


def the_trial_runs_in_its_own_python_on_the_held_card():
    import types
    root = pathlib.Path(tempfile.mkdtemp())
    kept = physics.engines.machine_runner
    try:
        layer = toy.toy_place(root / "layer")
        record = dict(toy.RECORD, views=[{"name": "front"}], moments=[0.0], size=[4, 4])
        (layer / "record.json").write_text(json.dumps(record))
        (layer / "physics.json").write_text(json.dumps(toy.physics.write(layer, record, toy.MATERIALS)))
        physics.engines.machine_runner = lambda: types.SimpleNamespace(Machine=Held)
        (root / "out").mkdir()
        physics.make_trial({"physics-layer": layer}, root / "out", 0, {})
        assert Held.jobs == [(physics.TRIAL_SCRIPT, physics.TRIAL_ENV), (physics.RENDER_SCRIPT, None)], Held.jobs
        assert physics.trial_faults(root / "out") == [], physics.trial_faults(root / "out")
        assert physics.TRIAL_FILES["trial env"].endswith(physics.TRIAL_ENV)
    finally:
        physics.engines.machine_runner = kept
        shutil.rmtree(root)


CHECKS = (the_loose_rows_drop_where_they_stand, the_gravity_is_the_body_s_under_the_top_site,
          a_body_no_row_has_fails_designed, a_trial_with_no_hinge_passes_only_when_it_says_why, a_good_run_passes,
          a_drop_under_its_target_fails_reacted, a_door_past_its_limit_fails_hinge, an_undriven_rise_fails_energy,
          a_body_moving_inside_or_under_its_floor_fails_at_rest, the_rises_are_per_undriven_stretch,
          the_trial_stands_the_shown_places_from_the_neighbours_output,
          the_trial_runs_in_its_own_python_on_the_held_card)


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(REPO / "conftest.py"))["refuse_outside_sandbox"]()
    for check in CHECKS:
        check()
        print("ok", check.__name__)
