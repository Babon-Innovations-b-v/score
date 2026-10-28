"""A thing moves as its scene's design says, and the motion check holds every move to its record. Made from the design
on a small stage made here (no record written for the scene): the door swings a right angle on the hinge at its own
left edge and shuts again, the fan turns a whole number of times a round, the rover stands parked with its rule's
reason, and every gate passes; with nobody in the scene the door stands shut; a moving row with no object fails
`designed`; a door whose swing strikes is swung the other way, else stands with its strike; a hatch lying flat
stands. The check (check.py, #23), on a cart driven round a closed path, a door swung on its hinge and a hatch slid
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


def toy_inputs(folder, rows=ROWS, extra=()):
    folder = pathlib.Path(folder)
    (folder / "inventory.json").write_text(json.dumps({"rows": rows}))
    seed = a_seed(folder, {"floor": ((-6.0, -0.1, -6.0), (6.0, 0.0, 6.0))}, [*DESIGNED, *extra])
    return {"design": folder / "inventory.json", "row kinds": REPO / "data/checks/row-kinds.json",
            "kinds": REPO / "data/checks/motion.json", "seed": seed}


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
    """The hatch kind's cited range is 15 to 53 degrees a second: the door swings at its middle, 34. The ceiling fan's
    is 400 to 1080: the middle 740 is 41.1 turns in the 20 s round, so 41 turns, 738 a second. Shut, the leaf's middle
    stands at its own spot (3, 1, 1); its hinge is its left edge, (2.55, 1, 1); a quarter turn about the upright there
    (rotateY +90: x to -z) carries the middle 0.45 m from +x of the hinge to -z of it: (2.55, 1, 0.55).
    Break: score/stages/motion/from_design.py: `turns = max(1, round(middle_speed(motion_kind, "angular") * ROUND /
        360.0))` -> `turns = middle_speed(motion_kind, "angular") * ROUND / 360.0`"""
    inputs = toy_inputs(tmp_path)
    out, record = made(inputs, tmp_path)
    found = {check.name: check.judge(out, inputs, None) for check in motion.CHECKS}
    door = f"/{PLACE}/Objects/door_1"
    shut, opened = middle_at(out, inputs, door, 0.0), middle_at(out, inputs, door, 8.0)
    assert all(verdict.answer == checks.PASS for verdict in found.values()), {
        name: (verdict.reason, verdict.findings) for name, verdict in found.items() if verdict.answer != checks.PASS}
    moves = {entry["name"]: entry for entry in record["moves"]}
    assert sorted(moves) == ["door_1", "fan_1"] and list(record["still"]) == [f"/{PLACE}/Objects/rover_1"]
    assert moves["door_1"]["swing"]["speed"] == 34.0 and moves["door_1"]["swing"]["angle"] == 90.0
    assert moves["fan_1"]["spin"]["speed"] == 738.0
    assert np.allclose(shut, (3.0, 1.0, 1.0), atol=1e-6), shut
    assert np.allclose(opened, (2.55, 1.0, 0.55), atol=1e-4), opened


def test_with_nobody_in_the_scene_the_door_stands_shut(tmp_path):
    """No astronaut row: nobody passes through the door, so it stands shut with its rule's reason; the fan still turns.
    Break: score/stages/motion/from_design.py: `elif not served(rule, inventory, kinds):` -> `elif False:`"""
    _, record = made(toy_inputs(tmp_path, [row for row in ROWS if row["id"] != "astronaut"]), tmp_path)
    assert sorted(entry["name"] for entry in record["moves"]) == ["fan_1"]
    assert record["still"][f"/{PLACE}/Objects/door_1"].startswith("nobody passes through it")


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


def test_a_door_that_strikes_its_rule_s_way_is_fitted_to_swing_the_other_way(tmp_path):
    """The post in its rule's way: swung -90 instead, said fitted, clear passes; a quarter turn the other way (rotateY
    -90: x to +z) carries the middle 0.45 m from +x of the hinge to +z of it: (2.55, 1, 1.45).
    Break: score/stages/motion/__init__.py: `kept.append(turned_to(first[prim], left[prim].pop(0)))` -> `still[prim] =
        "struck"`"""
    inputs = toy_inputs(tmp_path, extra=(POST,))
    out, record = made(inputs, tmp_path)
    clear = judge("clear", out, inputs)
    opened = middle_at(out, inputs, f"/{PLACE}/Objects/door_1", 8.0)
    door = next(entry for entry in record["moves"] if entry["name"] == "door_1")
    assert door["swing"]["angle"] == -90.0 and "fitted by the clear gate" in door["from"], door
    assert clear.answer == checks.PASS, (clear.reason, clear.findings)
    assert np.allclose(opened, (2.55, 1.0, 1.45), atol=1e-4), opened


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


def test_a_hatch_lying_flat_stands(tmp_path):
    """A floor hatch 0.6 m across and 0.1 m tall would turn about a level line: it stands, said so.
    Break: score/stages/motion/from_design.py: `elif rule["move"] == "swing" and not upright(stage, path):` -> `elif
        False:`"""
    flat = ("hatch_1", (-1.0, 0.0, -1.0), (-0.3, 0.0, -0.3), (0.3, 0.1, 0.3))
    _, record = made(toy_inputs(tmp_path, ROWS + [{"id": "hatch", "name": "floor hatch", "noun": "hatch"}],
                                extra=(flat,)), tmp_path)
    assert sorted(entry["name"] for entry in record["moves"]) == ["door_1", "fan_1"]
    assert record["still"][f"/{PLACE}/Objects/hatch_1"] == from_design.LYING


def test_covered_asks_for_the_design_s_moving_rows_only(tmp_path):
    """A rocket named as an old record's moving kind, on no moving row, is not asked for (3 moving kinds: door, fan,
    rover); the design's door taken out of the record (neither moved nor standing with a reason) fails by name.
    Break: score/stages/motion/__init__.py: `if path not in moved and path not in still and path.rsplit("/", 1)[-1] not
        in still]` -> `if False]`"""
    rocket = ("rocket_1", (-4.0, 0.0, 0.0), (-0.5, 0.0, -0.5), (0.5, 3.0, 0.5))
    inputs = toy_inputs(tmp_path, ROWS + [{"id": "rocket", "name": "rocket", "noun": "rocket"}], extra=(rocket,))
    out, record = made(inputs, tmp_path)
    kept = judge("covered", out, inputs)
    (out / motion.RECORD).write_text(json.dumps(dict(record, moves=[entry for entry in record["moves"]
                                                                    if entry["name"] != "door_1"])))
    dropped = judge("covered", out, inputs)
    assert kept.answer == checks.PASS and kept.measures["moving kinds"] == 3, (kept.reason, kept.findings)
    assert dropped.answer == checks.FAIL and dropped.findings == (f"/{PLACE}/Objects/door_1 (door)",), dropped.findings


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
