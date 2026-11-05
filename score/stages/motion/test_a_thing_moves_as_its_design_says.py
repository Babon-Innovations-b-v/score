"""A thing moves as its scene's design says, and the motion check holds every move to its record. Made from the design
on a small stage made here (no record written for the scene): the door swings a right angle on the hinge at its own
left edge and shuts again, the fan turns a whole number of times a round, the rover stands parked with its rule's
reason, and every gate passes; with nobody in the scene the door stands shut; two seeds make the same moves, so
the row is unseeded; a moving row with no object fails `designed`, left out by name where a batch gap or the accepted plan's
gap names it; a door whose swing strikes is swung the other
way, else stands with its strike; a hatch lying flat stands; a rocket climbs off the Moon at its push less its
body's pull and stands where its push would not lift it, and a flag on an airless body hangs still. The check (check.py, #23), on a cart driven round a closed path, a door swung on its hinge and a hatch slid
down: each passes, and one known fault each fails by name. Expected spots are worked out by hand below.

Each test names the break that turns it red (`Break: <file>: `old` -> `new``); each was applied once and seen red.

Run: PROPS_HOME=$(mktemp -d) .venv/bin/python -m pytest score/stages/motion/test_a_thing_moves_as_its_design_says.py
"""
import copy
import json
import pathlib
import shutil
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))

import numpy as np  # noqa: E402
from pxr import Gf, Sdf, Usd, UsdGeom  # noqa: E402

from score import checks  # noqa: E402
from score.stages import motion  # noqa: E402
from score.stages.motion import from_design  # noqa: E402

REPO = pathlib.Path(__file__).resolve().parents[3]
PLACE = "toy"
ROWS = [{"id": "door", "name": "door", "noun": "door"}, {"id": "fan", "name": "ceiling fan", "noun": "fan"},
        {"id": "rover", "name": "rover", "noun": "rover"},
        {"id": "astronaut", "name": "astronaut", "noun": "astronaut"}, {"id": "wall", "name": "wall", "noun": "wall"},
        {"id": "ceiling", "name": "ceiling", "noun": "ceiling"}]


def box(stage, path, low, high):
    """A drawn box mesh of triangles from `low` to `high`."""
    (x0, y0, z0), (x1, y1, z1) = low, high
    points = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1),
              (x0, y1, z1)]
    quads = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (3, 7, 6, 2), (0, 4, 7, 3), (1, 2, 6, 5)]
    mesh = UsdGeom.Mesh.Define(stage, path)
    mesh.GetPointsAttr().Set([Gf.Vec3f(*point) for point in points])
    mesh.GetFaceVertexCountsAttr().Set([3] * 12)
    mesh.GetFaceVertexIndicesAttr().Set([index for a, b, c, d in quads for index in (a, b, c, a, c, d)])


def thing(stage, name, at, low, high):
    """An object Xform at `at` with a box mesh from `low` to `high` in its own frame."""
    xform = UsdGeom.Xform.Define(stage, f"/{PLACE}/Objects/{name}")
    xform.AddTranslateOp().Set(Gf.Vec3d(*at))
    box(stage, f"/{PLACE}/Objects/{name}/body", low, high)


def a_seed(folder, structure, things):
    """A scene's stage folder: a root over one base layer holding `structure` ({name: (low, high)}) and `things`
    ((name, at, low, high))."""
    seed = pathlib.Path(folder) / "seeds" / PLACE
    (seed / "layers").mkdir(parents=True)
    stage = Usd.Stage.CreateNew(str(seed / "layers/base.usda"))
    stage.SetDefaultPrim(UsdGeom.Xform.Define(stage, f"/{PLACE}").GetPrim())
    for name, (low, high) in structure.items():
        box(stage, f"/{PLACE}/Structure/{name}", low, high)
    for name, at, low, high in things:
        thing(stage, name, at, low, high)
    stage.GetRootLayer().Save()
    top = Sdf.Layer.CreateNew(str(seed / f"{PLACE}.usda"))
    top.subLayerPaths.append("./layers/base.usda")
    top.defaultPrim = PLACE
    top.timeCodesPerSecond = 24.0
    top.Save()
    return seed


# --- the moves made from the design ---------------------------------------------------------------------------------

# A floor; a wall the door's hinge edge stands in; a ceiling the fan hangs in; a door, a fan, a rover and an astronaut.
DESIGNED = [("wall_1", (2.2, 0.0, 1.0), (-0.5, 0.0, -0.1), (0.5, 2.5, 0.1)),
            ("ceiling_1", (-3.0, 2.8, -3.0), (-1.0, 0.0, -1.0), (1.0, 0.2, 1.0)),
            ("door_1", (3.0, 0.0, 1.0), (-0.45, 0.0, -0.05), (0.45, 2.0, 0.05)),
            ("fan_1", (-3.0, 2.6, -3.0), (-0.6, 0.0, -0.6), (0.6, 0.25, 0.6)),
            ("rover_1", (-3.0, 0.0, 3.0), (-1.0, 0.0, -0.7), (1.0, 1.0, 0.7)),
            ("astronaut_1", (0.0, 0.0, -4.0), (-0.25, 0.0, -0.15), (0.25, 1.8, 0.15))]


# The cast's walker: along x = 3 from z = 5 to z = -3 at 1.333 m a second, through the door's doorway (its box x 2.55
# to 3.45 at z 0.95 to 1.05); within a metre of the box from z 2.05 to -0.05, 2.21 to 3.79 s into its walk.
WALKER = {"name": "astronaut_1", "doing": "walking", "at": [3.0, 0.0, 5.0], "turn": 0.0, "pace": 1.333,
          "path": [[3.0, 0.0, 5.0], [3.0, 0.0, -3.0]]}
SEATED = {"name": "astronaut_1", "doing": "sitting", "at": [0.0, 0.0, -4.0], "turn": 0.0, "path": None}


def a_sky(on, gravity):
    """A scene's sky inputs (score/review/scene_sky.py) whose site stands on one body of the reference table."""
    return {"place": PLACE, "site": {"on": on}, "setting": {"bodies": [{"body": on, "name": on.title(),
                                                                         "reference": on, "gravity": gravity}]}}


def toy_inputs(folder, rows=ROWS, extra=(), cast=(WALKER,), sky=a_sky("earth", 9.82)):
    folder = pathlib.Path(folder)
    (folder / "inventory.json").write_text(json.dumps({"rows": rows}))
    (folder / "sky.json").write_text(json.dumps(sky))
    seed = a_seed(folder, {"floor": ((-6.0, -0.1, -6.0), (6.0, 0.0, 6.0))}, [*DESIGNED, *extra])
    (folder / "cast").mkdir(exist_ok=True)
    (folder / "cast/cast.json").write_text(json.dumps({"characters": list(cast)}))
    return {"design": folder / "inventory.json", "row kinds": REPO / "data/checks/row-kinds.json",
            "kinds": REPO / "data/checks/motion.json", "seed": seed, "cast": folder / "cast",
            "sky": folder / "sky.json", "bodies": REPO / "data/physics/bodies.json"}


def made(inputs, folder):
    out = pathlib.Path(folder) / "out"
    out.mkdir()
    motion.make(inputs, out, 0, {})
    assert motion.layer_faults(out) == []
    return out, json.loads((out / motion.RECORD).read_text())


def judge(name, out, inputs):
    return next(check for check in motion.CHECKS if check.name == name).judge(out, inputs, None)


def middle_at(output, inputs, prim, seconds):
    """The world middle of a prim's bounds at a second, with the motion layer over the scene's stage."""
    root = Sdf.Layer.CreateAnonymous(".usda")
    root.subLayerPaths = [str(pathlib.Path(output) / "layers/motion.usda"),
                          str(pathlib.Path(inputs["seed"]) / f"{PLACE}.usda")]
    stage = Usd.Stage.Open(root)
    bound = UsdGeom.BBoxCache(seconds * 24.0, ["default"]).ComputeWorldBound(stage.GetPrimAtPath(prim))
    return np.asarray(bound.ComputeAlignedRange().GetMidpoint())


def test_the_door_swings_the_fan_turns_the_rover_stands_and_every_gate_passes(tmp_path):
    """The hatch kind's cited range is 15 to 53 degrees a second: the door swings at its middle, 34, so 90 degrees
    take 2.647 s. The cast's walker comes within a metre of it from 2.21 to 3.79 s: it opens from 0 (2.21 - 2.647 is
    before the start), stands open at 3 s, shuts from 3.7 s (its route read every 0.1 s), played once (no loop). The ceiling fan's is 400 to 1080:
    the middle 740 is 41.1 turns in the 20 s round, so 41 turns, 738 a second. Shut, the leaf's middle stands at its
    own spot (3, 1, 1); its hinge is its left edge, (2.55, 1, 1); a quarter turn about the upright there (rotateY +90:
    x to -z) carries the middle 0.45 m from +x of the hinge to -z of it: (2.55, 1, 0.55).
    Break: score/stages/motion/from_design.py: `turns = max(1, round(middle_speed(motion_kind, "angular") * ROUND /
        360.0))` -> `turns = middle_speed(motion_kind, "angular") * ROUND / 360.0`
    Break: score/stages/motion/from_design.py: `opens = max(free, enter - travel)` -> `opens = max(free, enter)`"""
    inputs = toy_inputs(tmp_path)
    out, record = made(inputs, tmp_path)
    found = {check.name: check.judge(out, inputs, None) for check in motion.CHECKS}
    door = f"/{PLACE}/Objects/door_1"
    shut, opened = middle_at(out, inputs, door, 8.0), middle_at(out, inputs, door, 3.0)
    assert all(verdict.answer == checks.PASS for verdict in found.values()), {
        name: (verdict.reason, verdict.findings) for name, verdict in found.items() if verdict.answer != checks.PASS}
    moves = {entry["name"]: entry for entry in record["moves"]}
    assert sorted(moves) == ["door_1", "fan_1"] and list(record["still"]) == [f"/{PLACE}/Objects/rover_1"]
    assert moves["door_1"]["swing"]["speed"] == 34.0 and moves["door_1"]["swing"]["angle"] == 90.0
    assert moves["door_1"]["swing"]["moves"] == [[0.0, "open"], [3.7, "shut"]] and not moves["door_1"]["loop"], \
        moves["door_1"]["swing"]
    assert moves["fan_1"]["spin"]["speed"] == 738.0
    assert np.allclose(shut, (3.0, 1.0, 1.0), atol=1e-6), shut
    assert np.allclose(opened, (2.55, 1.0, 0.55), atol=1e-4), opened


OPEN_DOOR = ("open_door_1", (-4.0, 0.0, 0.0), (-0.45, 0.0, -0.05), (0.45, 2.0, 0.05))
SLIDING_DOOR = ("sliding_door_1", (-4.0, 0.0, 4.0), (-0.6, 0.0, -0.05), (0.6, 2.1, 0.05))
WORDED = [{"id": "open_door", "name": "open apartment door", "noun": "door"},
          {"id": "sliding_door", "name": "sliding door", "noun": "door"}]


def test_with_nobody_walking_through_the_doors_stand_as_their_words_say(tmp_path):
    """Fault (the audit of 2026-11-04, 22 doors in 12 places): every door swung open at 2 s and shut at 10 s each
    20 s round wherever the inventory held any person, with nobody walking through. The astronaut sits, so no walker
    passes: the door stands shut with its rule's reason, the open apartment door stands posed open (its row's words),
    the sliding door stands shut, and `passed` and `rests` pass. The old fixed clock (a swing open at 2 s, shut at 10
    s, every round) written into the record fails `passed`, with no walker near; the sliding door written as a swing
    fails `rests`; no cast at all leaves every door standing.
    Break: score/stages/motion/from_design.py: `elif not served(rule, inventory, kinds) or spans == []:`
        -> `elif not served(rule, inventory, kinds):`
    Break: score/stages/motion/__init__.py: `if not any(enter <= end and leave >= begin for enter, leave in near):`
        -> `if False:`
    Break: score/stages/motion/__init__.py: `if said & set(NOT_ONE_LEAF) and path in swings:` -> `if False:`
    Break: score/stages/motion/from_design.py: `return dict(rule, rests="open") if said & set(base.get("open_words",
        ())) else rule` -> `return rule`"""
    inputs = toy_inputs(tmp_path, ROWS + WORDED, (OPEN_DOOR, SLIDING_DOOR), cast=(SEATED,))
    out, record = made(inputs, tmp_path)
    assert sorted(entry["name"] for entry in record["moves"]) == ["fan_1"]
    assert record["still"][f"/{PLACE}/Objects/door_1"].startswith("nobody passes through it")
    assert record["still"][f"/{PLACE}/Objects/sliding_door_1"].startswith("nobody passes through it")
    assert [entry["name"] for entry in record["posed"]] == ["open_door_1"], record["posed"]
    assert record["still"][f"/{PLACE}/Objects/open_door_1"].startswith("it stands open")
    assert middle_at(out, inputs, f"/{PLACE}/Objects/open_door_1", 5.0)[2] < -0.4  # turned off its wall line
    for name in ("passed", "rests", "moving area", "covered"):
        verdict = judge(name, out, inputs)
        assert verdict.answer == checks.PASS, (name, verdict.reason, verdict.findings)
    clock = {"name": "door_1", "prim": f"/{PLACE}/Objects/door_1", "row": "door", "kind": "hatch", "on": "rail",
             "start": 0.0, "length": 20.0, "loop": True,
             "swing": {"about": {"side": [-1.0, 0.0, 0.0]}, "angle": 90.0, "speed": 34.0, "starts": "shut",
                       "moves": [[2.0, "open"], [10.0, "shut"]]}}
    slid = dict(clock, name="sliding_door_1", prim=f"/{PLACE}/Objects/sliding_door_1", row="sliding_door")
    (out / motion.RECORD).write_text(json.dumps(dict(record, moves=[*record["moves"], clock, slid])))
    verdict = judge("passed", out, inputs)
    assert verdict.answer == checks.FAIL and verdict.findings[0].startswith(
        "door_1: off its rest from 2.0 to 12.6 s, and no walker"), verdict.findings
    verdict = judge("rests", out, inputs)
    assert verdict.answer == checks.FAIL and any("sliding_door_1: its row says sliding, yet it swings" in line
                                                 for line in verdict.findings), verdict.findings
    (tmp_path / "alone").mkdir()
    alone = toy_inputs(tmp_path / "alone", cast=())
    _, record = made(alone, tmp_path / "alone")
    assert sorted(entry["name"] for entry in record["moves"]) == ["fan_1"]


def test_the_make_never_reads_its_seed_so_a_failure_is_noted_never_remade(tmp_path):
    """Two seeds make the same record and layer, so the table marks the row unseeded: a failed output is noted for a
    fix upstream, never remade with a fresh seed (motion@base, 2026-10-29: both attempts the same output).
    Break: score/stages/__init__.py: `"light", "motion")` -> `"light")`"""
    from score import stages
    inputs, outs = toy_inputs(tmp_path), []
    for seed in (0, 1778076555):
        out = tmp_path / f"out-{seed}"
        out.mkdir()
        motion.make(inputs, out, seed, {})
        outs.append([(out / name).read_bytes() for name in (motion.RECORD, "layers/motion.usda")])
    assert outs[0] == outs[1]
    assert not next(row for row in stages.STAGES if row.name == "motion").seeded


def test_a_row_that_moves_with_no_object_fails_designed(tmp_path):
    """A crane row moves and no object of it stands on the stage: `designed` fails naming it.
    Break: score/stages/motion/__init__.py: `faults += list(record.get("missing", []))` -> `pass`"""
    inputs = toy_inputs(tmp_path, ROWS + [{"id": "crane", "name": "crane", "noun": "crane"}])
    out, _ = made(inputs, tmp_path)
    verdict = judge("designed", out, inputs)
    assert verdict.answer == checks.FAIL
    assert verdict.findings == ("crane: moves (swing), and no object of it stands on the stage",), verdict.findings
    assert table_judge("designed", out, inputs).answer == checks.FAIL, "no batch gap names the crane, so its fault stays"


def table_judge(name, out, inputs):
    """A gate as the stage table runs it, batch gaps moved (stages.accepted_gaps, BATCH_GATES)."""
    from score import stages
    row = stages.accepted_gaps(stages.MOTION)
    return next(check for check in row.checks if check.name == name).judge(out, inputs, None)


def test_a_moving_row_whose_take_the_bake_left_out_carries_its_gap(tmp_path):
    """Fault (env1 on this PC, 2026-10-28, motion@garage): the bake's job for the vehicle lift's take failed in the
    batch, a batch gap naming the take only, and `designed` stopped the line on the lift having no object. The crane's
    take is named by a carried bake gap: `designed` still fails it by name, the motion output carries the bake's gap
    and its own naming the row, and the table moves the fault (stages.BATCH_GATES), so the line goes on.
    Break: score/stages/motion/from_design.py: `names = {row["id"], str(row.get("thing", "")).split(":", 1)[-1]}`
    -> `names = {row["id"]}`"""
    crane = {"id": "crane", "name": "crane", "noun": "crane", "thing": "prop:toy_crane_b26f85f9"}
    inputs = toy_inputs(tmp_path, ROWS + [crane])
    (tmp_path / "bake").mkdir()
    (tmp_path / "bake/batch-gaps.json").write_text(json.dumps({"gaps": [{
        "name": "toy_crane_b26f85f9: not baked", "row": "surfaces-bake", "check": "baked",
        "objects": ["toy_crane_b26f85f9"], "faults": ["toy_crane_b26f85f9: its bake job brought nothing back"],
        "reason": "the take's bake job ran once in the batch and failed"}]}))
    inputs["surfaces-bake"] = tmp_path / "bake"
    out, record = made(inputs, tmp_path)
    assert judge("designed", out, inputs).answer == checks.FAIL
    assert record["left_out"] == {"crane": ["toy_crane_b26f85f9: not baked"]}, record["left_out"]
    carried = [entry["name"] for entry in json.loads((out / "batch-gaps.json").read_text())["gaps"]]
    assert carried == ["toy_crane_b26f85f9: not baked", "crane: no object, so it does not move"], carried
    verdict = table_judge("designed", out, inputs)
    assert verdict.answer == checks.PASS and "moved to complete" in verdict.reason, (verdict.reason, verdict.findings)


def test_a_moving_row_the_accepted_plan_places_none_of_is_left_out_by_its_plan_gap(tmp_path):
    """Fault (motion@hangar, 2026-10-29): the floor hatch's row was read with no box, the accepted plan placed none of
    it ("floor hatch: 1 in the concept, 0 on the plan"), and `designed` stopped the line on it having no object. The
    crane's row is named by the plan's `placed` gap: `designed` still fails it by name, the record leaves it out by
    that gap, which names where its source fix waits (#36), and the table moves the fault, so the line goes on; the
    plan's other gaps leave nothing out.
    Break: score/stages/motion/__init__.py: `planned = from_design.plan_gaps(read_json(inputs["plan"])) if "plan" in
    inputs else []` -> `planned = []`"""
    inputs = toy_inputs(tmp_path, ROWS + [{"id": "crane", "name": "crane", "noun": "crane"}])
    inputs["plan"] = tmp_path / "plan.json"
    inputs["plan"].write_text(json.dumps({"gaps": [
        {"kind": "placed", "item": "crane", "row": "crane", "words": "crane: 1 in the concept, 0 on the plan"},
        {"kind": "outside", "item": "FAN 1", "row": "fan", "words": "fan 1 sticks out of the place"}]}))
    out, record = made(inputs, tmp_path)
    assert judge("designed", out, inputs).answer == checks.FAIL
    assert record["left_out"] == {"crane": ['crane: the accepted plan\'s gap "crane: 1 in the concept, 0 on the plan" '
                                            f"(its source fix: {from_design.PLAN_FIX})"]}, record["left_out"]
    assert "issues/36#issuecomment-" in from_design.PLAN_FIX
    carried = [entry["name"] for entry in json.loads((out / "batch-gaps.json").read_text())["gaps"]]
    assert carried == ["crane: no object, so it does not move"], carried
    verdict = table_judge("designed", out, inputs)
    assert verdict.answer == checks.PASS and "moved to complete" in verdict.reason, (verdict.reason, verdict.findings)


def a_baked_door(bake, paint, out, models=None):
    """The bake's door_1 written as the assembly's asset of it (baked.take_bake's place, its repaint left out): a leaf
    0.9 m wide, 2 m tall and 0.1 m thick."""
    stage = Usd.Stage.CreateNew(str(pathlib.Path(out) / "assets/door_1.usdc"))
    stage.SetDefaultPrim(UsdGeom.Xform.Define(stage, "/door_1").GetPrim())
    box(stage, "/door_1/leaf", (-0.45, 0.0, -0.05), (0.45, 2.0, 0.05))
    stage.GetRootLayer().Save()


def test_a_design_s_door_waiting_on_its_bake_stands_on_the_stage_and_swings(tmp_path, monkeypatch):
    """Fault (Batch 1, 2026-10-27, 24 places): the scene record's design objects wait on the surface line's bake, and
    the motion stage read no bake, so every moving row had no object and `designed` failed it. The door's object
    waits in the accepted record; the bake made its model, so it stands on the stage, swings, and `designed` passes.
    Break: score/stages/layer_base.py: `grounded.take_bakes(inputs, folder, seed.name)` -> `pass`"""
    import score.stages.assembly.baked as baked
    monkeypatch.setattr(baked, "take_bake", a_baked_door)
    inputs = toy_inputs(tmp_path, ROWS, extra=())
    shutil.rmtree(inputs["seed"].parent)
    inputs["seed"] = a_seed(tmp_path, {}, [thing for thing in DESIGNED if thing[0] != "door_1"])
    door = {"name": "door_1", "row": "door", "bake": "door_1", "kind": "object", "at": [3.0, 0.0, 1.0],
            "rotation": [0.0, 0.0, 0.0, 1.0], "waiting": "its model door_1 comes from the surface line's bake"}
    (tmp_path / "record/record").mkdir(parents=True)
    (tmp_path / f"record/record/{PLACE}.json").write_text(json.dumps({"place": PLACE, "objects": [door]}))
    (tmp_path / "bake/made").mkdir(parents=True)
    (tmp_path / "bake/baked.json").write_text(json.dumps({"door_1": {}}))
    (tmp_path / "bake/made/door_1.gltf").write_text("{}")
    (tmp_path / "kit.json").write_text(json.dumps({"pieces": []}))
    (tmp_path / "surfaces.json").write_text("{}")
    inputs.update({"scene-record": tmp_path / "record", "kit": tmp_path / "kit.json", "surfaces-bake": tmp_path / "bake",
                   "surfaces-paint": tmp_path, "surfaces": tmp_path / "surfaces.json"})
    out, record = made(inputs, tmp_path)
    verdict = judge("designed", out, inputs)
    assert record["missing"] == [] and verdict.answer == checks.PASS, (record["missing"], verdict.findings)
    assert f"/{PLACE}/Objects/door_1" in [entry["prim"] for entry in record["moves"]], record


# A post standing in the quarter the door sweeps opening its rule's way (rotateY +90: from +x of its hinge (2.55, 1)
# toward -z): its corner (2.8, 0.6) lies 0.47 m from the hinge, inside the leaf's 0.9 m; and its mirror over the
# door's line (z = 1), in the quarter it sweeps the other way.
POST = ("wall_2", (3.0, 0.0, 0.4), (-0.2, 0.0, -0.2), (0.2, 1.0, 0.2))
MIRROR = ("wall_3", (3.0, 0.0, 1.6), (-0.2, 0.0, -0.2), (0.2, 1.0, 0.2))


# A wall behind the sliding door along its whole travel either way, and a post 0.3 m past its +x end; a second walker
# along x = -4 from z = 0 to 6 passes it from 2.2 s to its walk's end at 4.5 s.
BEHIND = ("wall_4", (-3.6, 0.0, 4.15), (-2.4, 0.0, -0.1), (2.4, 2.5, 0.1))
PAST = ("wall_5", (-2.9, 0.0, 3.9), (-0.2, 0.0, -0.1), (0.2, 1.0, 0.1))
SLIDER = {"name": "astronaut_2", "doing": "walking", "at": [-4.0, 0.0, 0.0], "turn": 0.0, "pace": 1.333,
          "path": [[-4.0, 0.0, 0.0], [-4.0, 0.0, 6.0]]}


def test_a_door_that_strikes_its_rule_s_way_is_fitted_to_swing_the_other_way(tmp_path):
    """The post in its rule's way: swung -90 instead, said fitted, clear passes; a quarter turn the other way (rotateY
    -90: x to +z) carries the middle 0.45 m from +x of the hinge to +z of it: (2.55, 1, 1.45). Fault (the audit of
    2026-11-04): a sliding door swung as one hinged leaf. The sliding door slides its own 1.2 m width along its wall
    at its kind's middle 0.29 m a second (4.138 s) for the walker passing it (within a metre from 2.2 to 3.7 s), so it
    opens from 0 and shuts as soon as it is open; its rule's way (+x) strikes the post, so it slides -x, said fitted:
    its middle at x -4.58 at 2 s; every gate passes.
    Break: score/stages/motion/__init__.py: `kept.append(fit(first[prim], left[prim].pop(0)))` -> `still[prim] =
        "struck"`
    Break: score/stages/motion/from_design.py: `variant = next((entry["motion"] for entry in kinds[row["row_kind"]]
        .get("variants", []) if said & set(entry["words"])), {})` -> `variant = {}`"""
    inputs = toy_inputs(tmp_path, ROWS + WORDED[1:], extra=(POST, SLIDING_DOOR, BEHIND, PAST), cast=(WALKER, SLIDER))
    out, record = made(inputs, tmp_path)
    found = {check.name: check.judge(out, inputs, None) for check in motion.CHECKS}
    opened = middle_at(out, inputs, f"/{PLACE}/Objects/door_1", 3.0)
    slid = middle_at(out, inputs, f"/{PLACE}/Objects/sliding_door_1", 2.0)
    moves = {entry["name"]: entry for entry in record["moves"]}
    assert moves["door_1"]["swing"]["angle"] == -90.0 and "fitted by the clear gate" in moves["door_1"]["from"]
    assert moves["sliding_door_1"]["slide"]["by"] == [-1.2, 0.0, 0.0], moves["sliding_door_1"]["slide"]
    assert all(verdict.answer == checks.PASS for verdict in found.values()), {
        name: (verdict.reason, verdict.findings) for name, verdict in found.items() if verdict.answer != checks.PASS}
    assert np.allclose(opened, (2.55, 1.0, 1.45), atol=1e-4), opened
    assert moves["sliding_door_1"]["slide"]["moves"] == [[0.0, "open"], [4.138, "shut"]]
    assert np.allclose(slid, (-4.58, 1.05, 4.0), atol=1e-4), slid


def test_a_door_that_strikes_every_way_stands_with_its_strike(tmp_path):
    """Posts both ways: at 60 degrees, the least tried, the leaf still sweeps a post's corner (48 degrees round, 0.67 m
    out) either way, so it stands with its strike as the reason and clear passes.
    Break: score/stages/motion/__init__.py: `still[prim] = f"it strikes at every way it was tried, so it stands:
        {struck[prim]}"` -> `still[prim] = "struck"`"""
    inputs = toy_inputs(tmp_path, extra=(POST, MIRROR))
    out, record = made(inputs, tmp_path)
    clear = judge("clear", out, inputs)
    assert sorted(entry["name"] for entry in record["moves"]) == ["fan_1"]
    reason = record["still"][f"/{PLACE}/Objects/door_1"]
    assert reason.startswith("it strikes at every way it was tried") and "wall_" in reason, reason
    assert clear.answer == checks.PASS, (clear.reason, clear.findings)


def parted(folder, name, at, row, turn=0.0):
    """A parted build (score/stages/props/moving_parts) on the toy's base layer as the route lays it: an object Xform
    at `at` turned `turn` degrees about up, each node of its model an Xform of its own name at its node's origin
    holding its mesh."""
    from score.stages.props import moving_parts
    scene, _ = moving_parts.build(row, from_design.row_kinds.table())
    stage = Usd.Stage.Open(str(pathlib.Path(folder) / "seeds" / PLACE / "layers/base.usda"))
    xform = UsdGeom.Xform.Define(stage, f"/{PLACE}/Objects/{name}")
    xform.AddTranslateOp().Set(Gf.Vec3d(*at))
    xform.AddRotateYOp().Set(turn)
    for node in scene.graph.nodes_geometry:
        placed, geometry = scene.graph[node]
        mesh = scene.geometry[geometry]
        part = UsdGeom.Xform.Define(stage, f"/{PLACE}/Objects/{name}/{node}")
        part.AddTranslateOp().Set(Gf.Vec3d(*(float(value) for value in placed[:3, 3])))
        drawn = UsdGeom.Mesh.Define(stage, f"/{PLACE}/Objects/{name}/{node}/mesh")
        drawn.GetPointsAttr().Set([Gf.Vec3f(*(float(value) for value in point)) for point in mesh.vertices])
        drawn.GetFaceVertexCountsAttr().Set([3] * len(mesh.faces))
        drawn.GetFaceVertexIndicesAttr().Set([int(index) for index in mesh.faces.flatten()])
    stage.GetRootLayer().Save()


def test_a_hatch_lying_flat_stands_and_a_parted_build_moves_its_parts(tmp_path):
    """A floor hatch 0.6 m across and 0.1 m tall would turn about a level line: it stands, said so. Built with its
    parts apart (#19, score/stages/props/moving_parts), a double door 1.6 m wide turned a quarter about up at (3, 0,
    -2), across the walker's route, swings its two leaves on their own pivots (its outer edges) the opposite ways, so
    both open to its own +x (the world's -z), for the walker passing it from 4.5 s (within a metre of a leaf, read
    every 0.1 s) and shut after it; the door itself never swings as one leaf, and every gate passes over it; an open
    floor hatch so built stands posed open, its lid turned up 90 degrees on its level hinge (its middle 0.2 m up),
    and a shut one on the walker's route (at (3, 0, 3.5)) lifts its lid on that hinge as the walker comes and lowers
    it after, turning about its own x axis only.
    Break: score/stages/motion/from_design.py: `elif rule["move"] == "swing" and not upright(stage, path):` -> `elif
        False:`
    Break: score/stages/motion/from_design.py: `if rule["move"] in ("swing", "split") and hinged(stage, path):` ->
        `if False:` (the double door is unmade, covered fails)
    Break: tools/usd/motion_layer.py: `return own_pivot(stage, move)` -> `return own_side(stage, move, [0.0, 0.0,
        0.0])` (a leaf turns about its middle)
    Break: score/stages/motion/check.py: `tilt = max(tilt_of(turn, axis) for turn in turns)` -> `tilt =
        max(tilt_of(turn) for turn in turns)` (follows fails the lid's level hinge as tipping off the
        upright)
    Break: score/stages/motion/__init__.py: `moved = {path for path in moving_row_prims(stage, place, inputs) if
        under(path, moving)} | moving` -> `moved = moving`
    Break: score/stages/motion/from_design.py: `moves += [[at_least(opens), "open"], [at_least(shuts), "shut"]]` ->
        `moves += [[round(opens, 3), "open"], [round(shuts, 3), "shut"]]` (the walked lid's shut rounds to before its
        opening ends, and its layer is refused)"""
    flat = ("hatch_1", (-1.0, 0.0, -1.0), (-0.3, 0.0, -0.3), (0.3, 0.1, 0.3))
    _, record = made(toy_inputs(tmp_path, ROWS + [{"id": "hatch", "name": "floor hatch", "noun": "hatch"}],
                                extra=(flat,)), tmp_path)
    assert sorted(entry["name"] for entry in record["moves"]) == ["door_1", "fan_1"]
    assert record["still"][f"/{PLACE}/Objects/hatch_1"] == from_design.LYING
    folder = tmp_path / "parted"
    folder.mkdir()
    double = {"id": "double_door", "name": "double door", "noun": "door", "size": [1.6, 0.1, 2.1]}
    lid = {"id": "open_hatch", "name": "open floor hatch", "noun": "hatch", "size": [0.6, 0.6, 0.1]}
    walked = {"id": "floor_hatch", "name": "floor hatch", "noun": "hatch", "size": [0.6, 0.6, 0.1]}
    inputs = toy_inputs(folder, ROWS + [double, lid, walked])
    parted(folder, "double_door_1", (3.0, 0.0, -2.0), double, turn=90.0)
    parted(folder, "open_hatch_1", (-1.0, 0.0, -1.0), lid)
    parted(folder, "floor_hatch_1", (3.0, 0.0, 3.5), walked)
    out, record = made(inputs, folder)
    found = {check.name: check.judge(out, inputs, None) for check in motion.CHECKS}
    moves = {entry["name"]: entry for entry in record["moves"]}
    door = f"/{PLACE}/Objects/double_door_1"
    assert sorted(moves) == ["door_1", "double_door_1.leaf_left", "double_door_1.leaf_right", "fan_1",
                             "floor_hatch_1.lid"], sorted(moves)
    assert (moves["floor_hatch_1.lid"]["swing"]["axis"], moves["floor_hatch_1.lid"]["swing"]["angle"]) == ("x", -90.0)
    left, right = moves["double_door_1.leaf_left"]["swing"], moves["double_door_1.leaf_right"]["swing"]
    assert (left["angle"], right["angle"], left["axis"], left["about"]) == (90.0, -90.0, "y", {"pivot": True})
    assert left["moves"] == [[1.853, "open"], [6.1, "shut"]], left["moves"]  # 4.5 less 90 / 34; the walk ends at 6.1
    shut = middle_at(out, inputs, f"{door}/leaf_left__hinge_y", 0.0)
    opened = middle_at(out, inputs, f"{door}/leaf_left__hinge_y", 5.0)
    other = middle_at(out, inputs, f"{door}/leaf_right__hinge_yn", 5.0)
    assert opened[2] < shut[2] - 0.3 and other[2] < shut[2] - 0.3, (shut, opened, other)  # both open to -z
    assert [entry["name"] for entry in record["posed"]] == ["open_hatch_1.lid"], record["posed"]
    raised = middle_at(out, inputs, f"/{PLACE}/Objects/open_hatch_1/lid__hinge_xn", 5.0)
    lifted = middle_at(out, inputs, f"/{PLACE}/Objects/floor_hatch_1/lid__hinge_xn", 2.0)
    down = middle_at(out, inputs, f"/{PLACE}/Objects/floor_hatch_1/lid__hinge_xn", 15.0)
    assert raised[1] > 0.2 and lifted[1] > 0.2 and down[1] < 0.1, (raised, lifted, down)
    assert all(verdict.answer == checks.PASS for verdict in found.values()), {
        name: (verdict.reason, verdict.findings) for name, verdict in found.items() if verdict.answer != checks.PASS}


def test_covered_asks_for_the_design_s_moving_rows_only(tmp_path):
    """A ship named as an old record's moving kind, on a craft row that stands with its written reason, is not asked
    for (3 moving kinds: door, fan, rover); the design's door taken out of the record (neither moved nor standing with
    a reason) fails by name. Fault (the audit of 2026-11-04): a row no kind moves was invisible to every gate (the
    launching rocket, flags, a body of water, 102 screens). A launching rocket in the sky over Earth climbs straight
    up at the middle of its kind's cited push, (11.13 + 13.84) / 2 = 12.485 m/s/s, less Earth's 9.82: 2.665 m/s/s,
    so 0.5 * 2.665 * 20^2 = 533 m risen in the 20 s round, and `speeds`, `grounded` and the check pass it; its
    exhaust (no effect kind makes it), a wind turbine (a moving word no kind moves) and a screen (a `does` no stage
    reads) each fail `covered` by name, and a design holding only the turbine has the motion row, so the fault is
    judged. A launch written with no pull taken off climbs at the whole 12.485 m/s/s, which with Earth's pull is a
    push of 22.3, over the kind's: `speeds` fails it. On the Moon (3e-13 kPa of air, the reference table's) the flag hangs still with its reason and the
    rocket (12.485 over 1.624) climbs off its pad on the floor, `grounded` reading it once it has risen half a metre; under a body pulling 15 m/s/s it stands, its push not lifting it.
    Break: score/stages/motion/__init__.py: `if path not in moved and path not in still and path.rsplit("/", 1)[-1] not
        in still]` -> `if False]`
    Break: score/stages/motion/from_design.py: `unmade.append(f"{path}: {rule['move']}, which no writer makes:
        {rule['why']}")` -> `still[path] = rule["why"]`
    Break: score/stages/row_kinds.py: `if heard and not done & {"moves", "loose"} and not (kind and
        kinds[kind].get("stands")):` -> `if False:`
    Break: score/stages/design_layers.py: `return found | {"motion"} if row_kinds.uncovered(inventory, kinds) else
        found` -> `return found`
    Break: score/stages/motion/from_design.py: `"climb": {"lift": 0.0, "push": round(push, 4), "pull":
        float(body["gravity"])},` -> `"climb": {"lift": 0.0, "push": round(push, 4), "pull": 0.0},`
    Break: score/stages/motion/__init__.py: `push = 2.0 * risen / (seconds - lift) ** 2 + float(body["gravity"])` ->
        `push = 2.0 * risen / (seconds - lift) ** 2 + float(entry["climb"]["pull"])`
    Break: score/stages/motion/from_design.py: `return [f"{path}: exhaust, {rule['exhaust']}"] if rule.get("exhaust")
        else []` -> `return []`
    Break: score/stages/motion/from_design.py: `elif rule.get("airless") and airless(body):` -> `elif False:`
    Break: score/stages/motion/__init__.py: `for moment in np.arange(np.ceil(climbed_from(entry)), seconds + 1e-9,
        1.0):` ->
        `for moment in np.arange(0.0, seconds + 1e-9, 1.0):`"""
    from score.stages import design_layers
    ship = ("ship_1", (-4.0, 0.0, 0.0), (-0.5, 0.0, -0.5), (0.5, 3.0, 0.5))
    inputs = toy_inputs(tmp_path, ROWS + [{"id": "ship", "name": "ship", "noun": "ship"}], extra=(ship,))
    out, record = made(inputs, tmp_path)
    kept = judge("covered", out, inputs)
    (out / motion.RECORD).write_text(json.dumps(dict(record, moves=[entry for entry in record["moves"]
                                                                    if entry["name"] != "door_1"])))
    dropped = judge("covered", out, inputs)
    assert kept.answer == checks.PASS and kept.measures["moving kinds"] == 3, (kept.reason, kept.findings)
    assert dropped.answer == checks.FAIL and dropped.findings == (f"/{PLACE}/Objects/door_1 (door)",), dropped.findings
    unmade = [{"id": "rocket", "name": "launching rocket", "noun": "rocket"},
              {"id": "turbine", "name": "wind turbine", "noun": "turbine"},
              {"id": "screen", "name": "wall screen", "noun": "screen"}]
    rocket = ("rocket_1", (-4.0, 10.0, -4.0), (-0.5, 0.0, -0.5), (0.5, 3.0, 0.5))  # in the sky, as the reading anchors it
    (tmp_path / "unmade").mkdir()
    inputs = toy_inputs(tmp_path / "unmade", ROWS + unmade, extra=(rocket,))
    out, record = made(inputs, tmp_path / "unmade")
    verdict = judge("covered", out, inputs)
    launch = next(entry for entry in record["moves"] if entry["name"] == "rocket_1")
    risen = middle_at(out, inputs, f"/{PLACE}/Objects/rocket_1", 20.0) - middle_at(out, inputs,
                                                                                  f"/{PLACE}/Objects/rocket_1", 0.0)
    assert launch["climb"] == {"lift": 0.0, "push": 12.485, "pull": 9.82} and not launch["loop"], launch
    assert np.allclose(risen, [0.0, 533.0, 0.0], atol=0.01), risen
    for name in ("speeds", "grounded", "follows", "steps"):
        assert judge(name, out, inputs).answer == checks.PASS, (name, judge(name, out, inputs).findings)
    assert abs(judge("speeds", out, inputs).measures["rocket_1 push"] - 12.485) < 0.01
    assert verdict.answer == checks.FAIL, verdict.reason
    assert [line.split(":", 2)[:2] for line in verdict.findings] == [
        [f"/{PLACE}/Objects/rocket_1", " exhaust, its exhaust's flame and smoke under it, which no effect kind makes "
         "yet (data/checks/effects.json measures no rocket exhaust on footage)"], ["turbine", " \"wind turbine\" names a moving thing (turbine), and its kind (none) gives it no move and no written reason to stand (data/checks/row-kinds.json)"],
        ["screen", " its kind screen shows, and no stage makes that (row-kinds.json `read_by`)"]], verdict.findings
    assert "motion" in design_layers.kinds_of({"rows": [unmade[1]]})
    unpulled = dict(record, moves=[dict(entry, climb=dict(entry["climb"], pull=0.0)) if "climb" in entry else entry
                                   for entry in record["moves"]])
    (tmp_path / "unpulled").mkdir()
    (tmp_path / "unpulled" / motion.RECORD).write_text(json.dumps(unpulled))
    motion.write_motion(dict(inputs, moves=tmp_path / "unpulled" / motion.RECORD), tmp_path / "unpulled",
                        inputs["seed"])
    shutil.copy(out / "moved.json", tmp_path / "unpulled" / "moved.json")
    assert judge("speeds", tmp_path / "unpulled", inputs).answer == checks.FAIL
    flag = [{"id": "flag", "name": "flag", "noun": "flag"}, unmade[0]]
    for name, sky in (("moon", a_sky("moon", 1.624)), ("heavy", a_sky("heavy", 15.0))):
        (tmp_path / name).mkdir()
        pad = ("rocket_1", (-4.0, 0.0, -4.0), (-0.5, 0.0, -0.5), (0.5, 3.0, 0.5))
        flagged = toy_inputs(tmp_path / name, ROWS + flag, extra=(pad, ("flag_1", (4.0, 0.0, -4.0),
                                                                       (-0.5, 0.0, -0.05), (0.5, 1.0, 0.05))), sky=sky)
        lifted, found = made(flagged, tmp_path / name)
        moved = [entry["name"] for entry in found["moves"]]
        if name == "moon":
            assert found["still"].get(f"/{PLACE}/Objects/flag_1", "").startswith(
                "it hangs still: no air stands on its body to wave it (Moon: 3e-13 kPa)"), found["still"]
            assert "rocket_1" in moved and judge("grounded", lifted, flagged).answer == checks.PASS
        else:
            assert "rocket_1" not in moved and "does not lift it off" in found["still"][f"/{PLACE}/Objects/rocket_1"]


def test_a_swing_is_tried_its_rule_s_way_and_the_other_down_to_sixty_degrees():
    """90 either way, then 10 less each time, down to 60 included.
    Break: score/stages/motion/__init__.py: `sizes = np.arange(abs(float(angle)), FIT_LEAST - 1e-9, -FIT_STEP)` ->
        `sizes = np.arange(abs(float(angle)), FIT_LEAST, -FIT_STEP)`"""
    assert motion.swing_angles(90.0) == [90.0, -90.0, 80.0, -80.0, 70.0, -70.0, 60.0, -60.0]


def test_a_speed_is_the_middle_of_its_kind_s_cited_range():
    """15 to 53 degrees a second: 34; 0.08 to 0.4 m a second: 0.24.
    Break: score/stages/motion/from_design.py: `return (float(low) + float(high)) / 2` -> `return float(high)`"""
    assert from_design.middle_speed({"angular": [15.0, 53.0]}, "angular") == 34.0
    assert abs(from_design.middle_speed({"linear": [0.08, 0.4]}, "linear") - 0.24) < 1e-12


# --- the motion check on a written record ---------------------------------------------------------------------------

RECORD = {"place": PLACE, "seconds": 12.0, "moves": [
    {"name": "cart_round", "prim": f"/{PLACE}/Objects/cart_1", "kind": "rover", "on": "rail", "start": 0.0,
     "length": 12.0, "loop": True,
     "path": {"points": [[0, 0], [3, 0], [3, 3], [0, 3]], "relative": True}},
    {"name": "door_swing", "prim": f"/{PLACE}/Objects/door_1", "kind": "hatch", "on": "rail", "start": 0.0,
     "length": 12.0, "loop": True,
     "swing": {"about": "Objects/hinge_1", "angle": 90.0, "speed": 45.0, "starts": "shut",
               "moves": [[1.0, "open"], [6.0, "shut"]]}},
    {"name": "hatch_slide", "prim": f"/{PLACE}/Objects/hatch_1", "kind": "hatch", "on": "rail", "start": 0.0,
     "length": 12.0, "loop": True,
     "slide": {"by": [0.0, -1.0, 0.0], "speed": 0.5, "starts": "shut", "moves": [[1.0, "open"], [6.0, "shut"]]}}]}
# A wall at x = 8 to 8.3; a cart, a door on its hinge post, a hatch and a crate, each standing on its own origin.
CHECKED = [(name, at, (-size[0] / 2, 0.0, -size[2] / 2), (size[0] / 2, size[1], size[2] / 2))
           for name, at, size in (("cart_1", (0.0, 0.05, 0.0), (1.0, 0.8, 1.0)),
                                  ("door_1", (-4.0, 0.0, -4.0), (1.0, 2.0, 0.1)),
                                  ("hinge_1", (-4.55, 0.0, -4.0), (0.1, 2.0, 0.1)),
                                  ("hatch_1", (5.0, 0.0, -4.0), (1.0, 0.1, 1.0)),
                                  ("crate_1", (-4.0, 0.0, 3.0), (0.6, 0.6, 0.6)))]


def checked_place(folder, record=RECORD):
    """The checked place's seed and its motion layer written from `record` (the stage makes its own from the design:
    from_design.py), the record kept as the output's."""
    seed = a_seed(folder, {"wall": ((8.0, 0.0, -2.0), (8.3, 3.0, 6.0))}, CHECKED)
    out = pathlib.Path(folder) / "out"
    out.mkdir()
    (out / motion.RECORD).write_text(json.dumps(record))
    motion.write_motion({"kinds": REPO / "data/checks/motion.json", "seed": seed, "moves": out / motion.RECORD}, out,
                        seed)
    return seed, out


def judged(output, seed, record, name):
    """The named gate judged against `record` as the output's record."""
    (pathlib.Path(output) / motion.RECORD).write_text(json.dumps(record))
    check = next(check for check in motion.CHECKS if check.name == name)
    return check.judge(output, {"kinds": REPO / "data/checks/motion.json", "seed": seed}, None)


def motion_layer(output):
    return Sdf.Layer.FindOrOpen(str(pathlib.Path(output) / "layers/motion.usda"))


def test_the_check_passes_a_true_motion(tmp_path):
    """The cart round its path, the door swung 90 degrees on its hinge and the hatch slid down pass follows, steps,
    moving area and clear.
    Break: score/stages/motion/check.py: `if abs(reached - wanted) > ANGLE_MOST:` -> `if abs(reached - wanted) >= 0:`"""
    seed, out = checked_place(tmp_path)
    found = {name: judged(out, seed, RECORD, name) for name in ("follows", "steps", "moving area", "clear")}
    assert all(verdict.answer == checks.PASS for verdict in found.values()), {
        name: (verdict.reason, verdict.findings) for name, verdict in found.items()}


def test_follows_fails_a_move_off_its_record(tmp_path):
    """The cart judged against a path its layer does not drive (its third corner moved to (4, 4)) is off its curve;
    the door judged against a 60 degree swing it does not make swings 90.
    Break: score/stages/motion/check.py: `faults.append(f"{name}: {off.max():.2f} m off its path's curve at its frame
        {int(off.argmax())}")` -> `pass`
    Break: score/stages/motion/check.py: `if abs(reached - wanted) > ANGLE_MOST:` -> `if False:`"""
    seed, out = checked_place(tmp_path)
    elsewhere = copy.deepcopy(RECORD)
    elsewhere["moves"][0]["path"]["points"][2] = [4.0, 4.0]
    verdict = judged(out, seed, elsewhere, "follows")
    assert verdict.answer == checks.FAIL and any("off its path's curve" in line for line in verdict.findings), verdict
    wider = copy.deepcopy(RECORD)
    wider["moves"][1]["swing"]["angle"] = 60.0
    verdict = judged(out, seed, wider, "follows")
    assert verdict.answer == checks.FAIL and any("swings 90.0 degrees, its record 60.0" in line
                                                 for line in verdict.findings), verdict


def test_steps_fails_a_frame_thrown_aside(tmp_path):
    """One frame of the cart's drive thrown 2 m aside is a jump of the cart.
    Break: score/stages/motion/check.py: `return np.flatnonzero(steps > most)` -> `return np.array([], dtype=int)`"""
    seed, out = checked_place(tmp_path)
    layer = motion_layer(out)
    moved = layer.GetAttributeAtPath(f"/{PLACE}/Objects/cart_1.xformOp:translate:path")
    code = sorted(layer.ListTimeSamplesForPath(moved.path))[40]
    spot = layer.QueryTimeSample(moved.path, code)
    layer.SetTimeSample(moved.path, code, Gf.Vec3d(spot[0] + 2.0, spot[1], spot[2]))
    layer.Save()
    verdict = judged(out, seed, RECORD, "steps")
    assert verdict.answer == checks.FAIL and any(line.startswith("cart_round: jumps") for line in verdict.findings), \
        verdict


def test_moving_area_fails_a_stray_mover_and_a_named_one_standing_still(tmp_path):
    """A crate the layer moves that no record names, and the door's turn taken out of the layer, each fail by name.
    Break: score/stages/motion/check.py: `stray = [path for path in varying_prims(stage, place, scopes) if not
        under_any(path, named)]` -> `stray = []`
    Break: score/stages/motion/check.py: `still = [path for path in named if frame_steps(shapes[path], codes).sum() <=
        STILL_MOST]` -> `still = []`"""
    seed, out = checked_place(tmp_path)
    layer = motion_layer(out)
    crate = Sdf.CreatePrimInLayer(layer, f"/{PLACE}/Objects/crate_1")
    crate.specifier = Sdf.SpecifierOver
    shift = Sdf.AttributeSpec(crate, "xformOp:translate", Sdf.ValueTypeNames.Double3)
    layer.SetTimeSample(shift.path, 0.0, Gf.Vec3d(-4.0, 0.0, 3.0))
    layer.SetTimeSample(shift.path, 48.0, Gf.Vec3d(-3.0, 0.0, 3.0))
    swung = layer.GetAttributeAtPath(f"/{PLACE}/Objects/door_1.xformOp:rotateY:swing")
    for sample in layer.ListTimeSamplesForPath(swung.path):
        layer.EraseTimeSample(swung.path, sample)
    layer.Save()
    verdict = judged(out, seed, RECORD, "moving area")
    assert verdict.answer == checks.FAIL, verdict
    assert f"/{PLACE}/Objects/crate_1: moves, yet no record moves it" in verdict.findings, verdict
    assert f"/{PLACE}/Objects/door_1: its record moves it, yet it stands still in the stage" in verdict.findings


def test_clear_fails_a_path_laid_through_the_wall(tmp_path):
    """The cart's path laid out to x = 9 runs through the wall at x = 8: clear fails naming the wall.
    Break: score/stages/motion/__init__.py: `faults.append((path, f"{path}: reaches {worst:.2f} m into {where[0]} at
        {where[1] / rate:.2f} s"))` -> `pass`"""
    through = copy.deepcopy(RECORD)
    through["moves"][0]["path"]["points"] = [[0, 0], [9, 0], [9, 3], [0, 3]]
    seed, out = checked_place(tmp_path, through)
    verdict = judged(out, seed, through, "clear")
    assert verdict.answer == checks.FAIL and any("Structure/wall" in line for line in verdict.findings), verdict
