"""Check the settle stage (score/stages/settling) without a drop: its layer lays each written object where its matrix
says over the seed (the assembly takes it the same way), and its drop gate fails a broken drop while one kept as laid
or stood upright for the paint is named; only what lies on the very object resting worse is kept with it; a flush pose
resting worse falls back to the drop's rest; one fallen into the hollow piece it lay on is laid where it lands,
anything else past the limits kept as laid; a cloud drop asks the physics trial's card alone, runs in its Python, and
is never bought twice.

Breaks that turn each check red (each applied once and seen red, reverted, 2026-10-27), in settling/__init__.py:
- the_layer_lays_each_object_at_its_rest: write_layer's `Gf.Matrix4d(local.T.tolist())` made
  `Gf.Matrix4d(local.tolist())` (the matrix written untransposed).
- the_drop_gate_fails_a_broken_drop_and_names_what_was_kept: judge_rested's `if "still moving" in entry["said"]`
  made `if False`.
- only_what_lies_on_the_object_resting_worse_is_kept_with_it: kept_where_worse's `resting_on(name) & worse` made
  `True` (every case of the row kept).
- a_flush_pose_resting_worse_falls_back_to_the_drops_rest: fallen_back's `back = {...}` made `back = set()`.
- one_fallen_into_a_hollow_piece_is_laid_where_it_lands: laid_where_it_lands without its `supports[0] not in hollow`
  test (a one-hull support's faller laid where it lands).
- a_box_fallen_into_its_crate_on_the_stage_is_laid_there: landed_in_hollows' `rest = np.asarray(...["motion"]) @
  pose["before"]` made `rest = pose["before"]` (the drop's motion not applied).
- the_laid_stage_keeps_each_object_where_it_was_laid: laid_stage's copy dropped (`Usd.Stage.Open(str(root))`: the
  poses read back through the settle layer laid over it).
- a_row_the_reading_gave_no_anchor_reads_as_none: with_anchors' `row.get("anchor") or ""` made `row.get("anchor")`
  (held_on_loose meets None).
- a_pair_crossing_as_laid_is_kept_not_broken: laid_inside_each_other returning `poses` unchanged (2026-10-30).
- a_pair_crossing_only_after_the_drop_still_breaks: crossing's `motions.get(name, np.eye(4))` made `np.eye(4)` (the
  pair judged as laid, not as the layer lays it).
- a_lamp_held_on_a_ceiling_or_wall_row_is_not_snapped_down (held.py): held_objects without its `row not in mounted`
  test.
- a_cloud_drop_runs_on_the_trials_card_in_its_python_once (tools/usd/drop.py): simulate's `machine.run(..., env=ENV)`
  without `env=ENV` (the drop sent to the card's Blender).

Run: .venv/bin/python score/stages/settling/test_the_settle_layer_lays_and_its_gate_fails_a_broken_drop.py
"""
import json
import pathlib
import sys
import tempfile

import numpy as np

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tools/usd"))
sys.path.insert(0, str(REPO / "tools/cloud"))
from pxr import Usd, UsdGeom  # noqa: E402
from score import checks, review  # noqa: E402
from score.stages import assembly, settling as settle  # noqa: E402
import test_floating_sunk_and_tipping_objects_are_told_apart as resting_test  # noqa: E402

PLACE = resting_test.PLACE


def a_cloud_drop_runs_on_the_trials_card_in_its_python_once():
    """A cloud drop asks the trial's card class alone and runs the drop script in the trial's Python; the same drop
    again is read back from the cache, no machine asked."""
    import blender_cloud
    import drop
    asked = []

    class Machine:
        def __init__(self, classes, who):
            asked.append({"classes": tuple(classes)})

        def __enter__(self):
            return self

        def __exit__(self, *errors):
            return False

        def run(self, script, arguments, inputs, outputs, minutes=10, env=None):
            asked[-1].update(script=pathlib.Path(script), env=env and pathlib.Path(env))
            pathlib.Path(arguments[2]).write_text(json.dumps({"objects": {}, "overlaps": []}))

    real = blender_cloud.Machine
    blender_cloud.Machine = Machine
    try:
        with tempfile.TemporaryDirectory() as temporary:
            folder = pathlib.Path(temporary)
            (folder / "stage").mkdir()
            stage = folder / "stage" / "place.usda"
            stage.write_text("#usda 1.0\n")
            for _ in range(2):
                drop.simulate(stage, {"crate_1": 0.02}, folder / "drop", cloud=True, cache=folder / "cache")
    finally:
        blender_cloud.Machine = real
    wanted = [{"classes": ("gpu-24gb",), "script": drop.INSIDE, "env": drop.ENV}]
    return [] if asked == wanted else [f"the drops asked {asked}, not {wanted} once"]


def laid(stage, name):
    return np.asarray(UsdGeom.Xformable(stage.GetPrimAtPath(f"/{PLACE}/Objects/{name}"))
                      .ComputeLocalToWorldTransform(Usd.TimeCode.Default())).T


def the_layer_lays_each_object_at_its_rest():
    """A crate moved 10 cm and turned 5 degrees by the layer stands there in the assembly's stage; the other keeps
    the seed's pose."""
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        resting_test.made_models(folder)
        path = resting_test.laid_place(folder, [("crate", "box", (0, 0, 0)), ("crate", "box", (3, 0, 0))],
                                       [("crate", "floor")])
        stage = Usd.Stage.Open(str(path))
        before = laid(stage, "crate_1")
        turn = np.eye(4)
        angle = np.radians(5.0)
        turn[:3, :3] = [[np.cos(angle), 0, np.sin(angle)], [0, 1, 0], [-np.sin(angle), 0, np.cos(angle)]]
        turn[:3, 3] = [0.1, 0.0, 0.0]
        settle.write_layer(stage, PLACE, {"crate_1": turn @ before}, folder / "made" / settle.LAYER)
        assembly.take_layer(folder / "made", path, settle.LAYER, None)
        again = Usd.Stage.Open(str(path))
        problems = []
        if not np.allclose(laid(again, "crate_1"), turn @ before, atol=1e-9):
            problems.append(f"crate_1 stands at {laid(again, 'crate_1')}, not its rest")
        if not np.allclose(laid(again, "crate_2"), laid(stage, "crate_2")):
            problems.append("crate_2 moved though the layer does not name it")
        return problems


def the_drop_gate_fails_a_broken_drop_and_names_what_was_kept():
    """One kept as laid (a 40 degree turn) and one stood upright for the paint pass, named; one still moving at the
    drop's end fails."""
    with tempfile.TemporaryDirectory() as temporary:
        output = pathlib.Path(temporary)
        objects = {"crate_1": {"rested": True, "said": "turns 1 degrees and drifts 1 cm to rest"},
                   "tank_1": {"rested": False, "said": "turns 7 degrees and drifts 2 cm to rest onto feet ending up to "
                                                       "12.7 cm apart in its own frame (level the model's feet); stood "
                                                       "upright on its lowest foot"},
                   "rack_1": {"rested": False, "said": "would not rest as laid: turns 40 degrees and drifts 90 cm"}}
        (output / settle.RECORD).write_text(json.dumps({"place": PLACE, "overlaps": [], "objects": objects}))
        passed = settle.judge_rested(output, {}, None)
        objects["box_1"] = {"rested": False, "said": "still moving 0.40 m/s at the end; left as laid"}
        (output / settle.RECORD).write_text(json.dumps({"place": PLACE, "overlaps": [], "objects": objects}))
        failed = settle.judge_rested(output, {}, None)
        problems = []
        if passed.answer != checks.PASS or passed.measures["kept"] != 1 or not any(
                line.startswith("tank_1") for line in passed.findings):
            problems.append(f"kept as laid counted, the one for the paint named only: {passed}")
        if failed.answer != checks.FAIL or failed.measures["broken"] != 1:
            problems.append(f"still moving: {failed}")
        objects["rack_2"] = dict(objects["rack_1"])  # one more kept as laid is still worse on accept
        objects.pop("box_1")
        (output / settle.RECORD).write_text(json.dumps({"place": PLACE, "overlaps": [], "objects": objects}))
        card = lambda verdict: {"rested": {"answer": verdict.answer, "measures": verdict.measures,
                                           "better": verdict.better}}
        more = settle.judge_rested(output, {}, None)
        if not review.regressions(card(more), card(passed)):
            problems.append("one more kept as laid was not worse than the accepted output")
        return problems


def only_what_lies_on_the_object_resting_worse_is_kept_with_it():
    """Both ways: a case on the pallet that rests worse is kept as laid with it; a case of the same row on another
    pallet of the same row is not (the campgrounds' open cases, 2026-10-15)."""
    eye = np.eye(4)
    moved = np.eye(4)
    moved[1, 3] = 0.01
    poses = {name: {"before": eye, "after": moved, "rested": True, "said": "moved"}
             for name in ("pallet_1", "pallet_2", "case_1", "case_2")}
    inventory = {"rows": [{"id": "pallet", "anchor": "floor"}, {"id": "case", "anchor": "on:pallet"}]}
    under = {"case_1": {"pallet_1"}, "case_2": {"pallet_2"}}
    found = settle.kept_where_worse(poses, {"pallet_1"}, inventory, lambda name: under.get(name, set()))
    kept = sorted(name for name, pose in found.items() if not pose["rested"])
    return [] if kept == ["case_1", "pallet_1"] else [f"kept {kept}, not the worse pallet and its own case"]



def a_flush_pose_resting_worse_falls_back_to_the_drops_rest():
    """Both ways (the wreck's probe lander, 2026-10-15): one stood flush on its slope that rests worse goes back to
    where the drop left it, not to as laid; one flush that rests no worse keeps its flush pose; one resting worse with
    no flush pose is left for kept_where_worse."""
    eye, flush, dropped = np.eye(4), np.eye(4), np.eye(4)
    flush[1, 3], dropped[0, 3] = 0.01, 0.02
    fallback = {"before": eye, "after": dropped, "rested": True, "said": "turns 1 degrees and drifts 2 cm to rest"}
    poses = {"lander_1": {"before": eye, "after": flush, "rested": True, "said": "stood flush", "fallback": fallback},
             "lamp_1": {"before": eye, "after": flush, "rested": True, "said": "stood flush", "fallback": fallback},
             "crate_1": {"before": eye, "after": dropped, "rested": True, "said": "turns 1 degrees"}}
    found, back = settle.fallen_back(poses, {"lander_1", "crate_1"})
    problems = []
    if back != {"lander_1"} or found["lander_1"]["after"] is not dropped or not found["lander_1"]["rested"]:
        problems.append(f"the lander did not fall back to the drop's rest: {back}, {found['lander_1']}")
    if found["lamp_1"] is not poses["lamp_1"] or found["crate_1"] is not poses["crate_1"]:
        problems.append("a flush pose resting no worse, or a worse one with no flush, was changed")
    return problems

def one_fallen_into_a_hollow_piece_is_laid_where_it_lands():
    """Both ways (owner, 2026-10-26: a box laid on an open crate falls 55 cm onto its floor): one past the limits whose
    one support was dropped as convex parts and rests, its middle at rest inside that crate's box, is laid at the
    drop's rest; with its support one hull, or its middle outside the box, or the crate itself kept as laid, it keeps
    the limits."""
    eye, rest = np.eye(4), np.eye(4)
    rest[1, 3] = -0.55
    said = "would not rest as laid: turns 0 degrees and drifts 55 cm to rest"
    pose = {"before": eye, "after": eye, "rested": False, "said": said}
    crate = {"before": eye, "after": eye, "rested": True, "said": "turns 0 degrees and drifts 0 cm to rest"}
    corners = np.array([[x, y, z] for x in (-0.5, 0.5) for y in (0.0, 0.6) for z in (-0.4, 0.4)])
    inside, outside = np.array([0.0, 0.17, 0.0]), np.array([0.0, 0.17, 0.9])
    landed = settle.laid_where_it_lands(pose, rest, inside, ["crate_1"], {"crate_1": []}, crate, corners)
    problems = []
    if not landed["rested"] or landed["after"] is not rest or "laid where it lands" not in landed["said"]:
        problems.append(f"the box in the crate was not laid where it landed: {landed}")
    for why, kept in (
            ("one hull", settle.laid_where_it_lands(pose, rest, inside, ["crate_1"], {}, crate, corners)),
            ("outside", settle.laid_where_it_lands(pose, rest, outside, ["crate_1"], {"crate_1": []}, crate,
                                                   corners)),
            ("crate kept", settle.laid_where_it_lands(pose, rest, inside, ["crate_1"], {"crate_1": []},
                                                      {**crate, "rested": False}, corners)),
            ("tipped", settle.laid_where_it_lands({**pose, "said": "still moving 0.40 m/s at the end; left as laid"},
                                                  rest, inside, ["crate_1"], {"crate_1": []}, crate, corners))):
        if kept["rested"]:
            problems.append(f"{why}: laid where it landed, not kept by the limits: {kept}")
    return problems


def a_box_fallen_into_its_crate_on_the_stage_is_laid_there():
    """The same read off a stage: a box laid on a 1 m crate that the drop puts 0.8 m lower, inside the crate, is laid
    there; one the drop throws 2 m aside keeps its laid pose."""
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        resting_test.made_models(folder)
        path = resting_test.laid_place(folder, [("crate", "box", (0, 0, 0)), ("box", "box", (0, 1.0, 0))],
                                       [("crate", "floor"), ("box", "on:crate")])
        stage = Usd.Stage.Open(str(path))
        problems = []
        for shift, landed in (((0.0, -0.8, 0.0), True), ((2.0, -0.8, 0.0), False)):
            motion = np.eye(4)
            motion[:3, 3] = shift
            poses = {"crate_1": {"before": laid(stage, "crate_1"), "after": laid(stage, "crate_1"), "rested": True,
                                 "said": "turns 0 degrees and drifts 0 cm to rest"},
                     "box_1": {"before": laid(stage, "box_1"), "after": laid(stage, "box_1"), "rested": False,
                               "said": "would not rest as laid: turns 0 degrees and drifts 80 cm to rest"}}
            simulated = {"objects": {"crate_1": {"motion": np.eye(4).tolist()}, "box_1": {"motion": motion.tolist()}}}
            found = settle.landed_in_hollows(stage, PLACE, poses, simulated, {"box_1": ["crate_1"]},
                                             {"crate_1": []})["box_1"]
            if found["rested"] is not landed or (landed and not np.allclose(found["after"],
                                                                            motion @ laid(stage, "box_1"))):
                problems.append(f"moved by {shift}: laid where it lands {found['rested']}, wanted {landed}")
        return problems



def the_laid_stage_keeps_each_object_where_it_was_laid():
    """The grounded seed as laid holds every object its root lays (an earth seed's are its scene record's, none its
    seed folder's: settle@engineroom read a held one there, 2026-10-28), at its laid pose after a settle layer moved it
    in the root."""
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        resting_test.made_models(folder)
        path = resting_test.laid_place(folder, [("crate", "box", (0, 0, 0))], [("crate", "floor")])
        before = laid(Usd.Stage.Open(str(path)), "crate_1")
        seed = settle.laid_stage(path)
        moved = before.copy()
        moved[:3, 3] += [0.1, 0.0, 0.0]
        settle.laid_over(path, seed, PLACE, {"crate_1": {"before": before, "after": moved}}, folder / "held.usda")
        if not np.allclose(laid(Usd.Stage.Open(str(path)), "crate_1"), moved):
            return ["the settle layer did not move crate_1 in the root"]
        if not np.allclose(laid(seed, "crate_1"), before):
            return [f"crate_1 as laid reads {laid(seed, 'crate_1')}, not its laid pose"]
        return []


def a_row_the_reading_gave_no_anchor_reads_as_none():
    """A row whose reading wrote `"anchor": null` (settle@habitat, 2026-10-30) reads as no anchor, so the drop's
    held-on-loose step still finds the tray on its dropped shelf; a written anchor is kept."""
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        resting_test.made_models(folder)
        path = resting_test.laid_place(folder, [("shelf", "box", (0, 0, 0)), ("tray", "box", (0, 1, 0)),
                                                ("lamp", "box", (3, 1, 0))],
                                       [("shelf", "floor"), ("tray", "on:shelf"), ("lamp", "wall")])
        inventory = json.loads((folder / "inventory.json").read_text())
        for row in inventory["rows"]:
            if row["id"] == "lamp":
                row["anchor"] = None
        inventory = settle.with_anchors(inventory)
        stage = Usd.Stage.Open(str(path))
        import settle as method  # tools/usd/settle.py, the drop job's method
        held = method.held_on_loose(stage, PLACE, inventory, method.loose_objects(stage, PLACE, inventory))
        return [] if held == ["tray_1"] else [f"the drop leaves out {held}, not the tray alone"]


def two_boxes(folder, apart):
    """A place of two 1 m crates `apart` metres across, and its meshes as laid (snap.read_place)."""
    import snap
    resting_test.made_models(folder)
    path = resting_test.laid_place(folder, [("crate", "box", (0, 0, 0)), ("crate", "box", (apart, 0, 0))],
                                   [("crate", "floor")])
    return path, snap.read_place(path)


def a_pair_crossing_as_laid_is_kept_not_broken():
    """Two crates the plan laid 50 cm into each other (airlock's sandbags, 2026-10-30), which the drop also leaves
    crossing: both are kept as laid, said laid inside the other, and the layer's poses cross nothing new."""
    with tempfile.TemporaryDirectory() as temporary:
        path, meshes = two_boxes(pathlib.Path(temporary), 0.5)
        stage = Usd.Stage.Open(str(path))
        pairs = [["crate_1", "crate_2"]]
        moved = laid(stage, "crate_1").copy()
        moved[0, 3] += 0.02
        poses = {"crate_1": {"before": laid(stage, "crate_1"), "after": moved, "rested": True, "said": "drifts 2 cm"},
                 "crate_2": {"before": laid(stage, "crate_2"), "after": laid(stage, "crate_2"), "rested": True,
                             "said": "drifts 0 cm"}}
        as_laid = settle.crossing(meshes, pairs, {})
        kept = settle.laid_inside_each_other(poses, as_laid)
        left = settle.crossing(meshes, [pair for pair in pairs if pair not in as_laid], settle.motions(kept))
        problems = []
        if as_laid != pairs or left:
            problems.append(f"crossing as laid {as_laid}, left to break {left}")
        for name, other in (("crate_1", "crate_2"), ("crate_2", "crate_1")):
            pose = kept[name]
            if pose["rested"] or pose["after"] is not pose["before"] or not pose["said"].startswith(
                    f"laid inside {other}"):
                problems.append(f"{name} not kept as laid inside {other}: {pose['rested']}, {pose['said']}")
        return problems


def a_pair_crossing_only_after_the_drop_still_breaks():
    """Two crates laid 3 m apart that the layer lays 50 cm into each other: not crossing as laid, crossing as the
    layer lays them, and the gate fails it."""
    with tempfile.TemporaryDirectory() as temporary:
        path, meshes = two_boxes(pathlib.Path(temporary), 3.0)
        pairs = [["crate_1", "crate_2"]]
        motion = np.eye(4)
        motion[0, 3] = -2.5
        problems = []
        if settle.crossing(meshes, pairs, {}):
            problems.append("two crates 3 m apart cross as laid")
        found = settle.crossing(meshes, pairs, {"crate_2": motion})
        if found != pairs:
            problems.append(f"the crates the layer lays into each other cross {found}")
        output = pathlib.Path(temporary)
        objects = {name: {"rested": True, "said": "drifts"} for name in ("crate_1", "crate_2")}
        (output / settle.RECORD).write_text(json.dumps({"place": PLACE, "overlaps": found, "objects": objects}))
        verdict = settle.judge_rested(output, {}, None)
        if verdict.answer != checks.FAIL or verdict.measures["broken"] != 1:
            problems.append(f"the gate let the crossing pass: {verdict}")
        return problems


def a_lamp_held_on_a_ceiling_or_wall_row_is_not_snapped_down():
    """A lamp on the roof row and a sign on a wall row are mounted, not held from under (airlock's ceiling lamps, 280
    cm over the floor, 2026-10-30): never snapped; a cup on its desk still is."""
    from score.stages.settling import held
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        resting_test.made_models(folder)
        path = resting_test.laid_place(
            folder, [("roof", "box", (0, 3, 0)), ("left_wall", "box", (3, 1, 0)), ("desk", "box", (6, 0, 0)),
                     ("lamp", "box", (0, 2, 0)), ("sign", "box", (3, 1, 1.5)), ("cup", "box", (6, 1, 0))],
            [("roof", "ceiling"), ("left_wall", "floor"), ("desk", "floor"), ("lamp", "on:roof"),
             ("sign", "on:left_wall"), ("cup", "on:desk")])
        inventory = json.loads((folder / "inventory.json").read_text())
        found = held.held_objects(Usd.Stage.Open(str(path)), PLACE, inventory, folder / "kit.json")
        return [] if found == ["cup_1"] else [f"held to snap down: {found}, not the cup alone"]


CHECKS = (a_pair_crossing_as_laid_is_kept_not_broken, a_pair_crossing_only_after_the_drop_still_breaks,
          a_lamp_held_on_a_ceiling_or_wall_row_is_not_snapped_down, a_row_the_reading_gave_no_anchor_reads_as_none, the_laid_stage_keeps_each_object_where_it_was_laid,a_cloud_drop_runs_on_the_trials_card_in_its_python_once, the_layer_lays_each_object_at_its_rest,
          the_drop_gate_fails_a_broken_drop_and_names_what_was_kept,
          only_what_lies_on_the_object_resting_worse_is_kept_with_it,
          a_flush_pose_resting_worse_falls_back_to_the_drops_rest,
          one_fallen_into_a_hollow_piece_is_laid_where_it_lands, a_box_fallen_into_its_crate_on_the_stage_is_laid_there)


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[3] / "conftest.py"))["refuse_outside_sandbox"]()
    failures = [f"{check.__name__}: {problem}" for check in CHECKS for problem in check()]
    for failure in failures:
        print(failure)
    print("ok" if not failures else f"{len(failures)} failed")
    sys.exit(1 if failures else 0)
