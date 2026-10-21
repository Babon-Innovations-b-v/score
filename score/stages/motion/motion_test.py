"""The motion stage made from a scene's design on a small stage made here (no record written for the scene): its door
swings a right angle on the hinge at its own left edge and shuts again, its fan turns a whole number of times a
round, its rover stands parked with its rule's reason, and every gate passes; with nobody in the scene the door
stands shut with its reason; a row that moves with no object on the stage fails `designed`. A door whose swing strikes
something is fitted by the gate: swung the other way where that keeps clear, else standing with its strike as the
reason; a hatch lying flat stands, since a swing turns about an upright line.

Run: .venv/bin/python score/stages/motion/motion_test.py
"""
import json
import pathlib
import sys
import tempfile

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
        {"id": "astronaut", "name": "astronaut", "noun": "astronaut"}, {"id": "wall", "name": "wall", "noun": "wall"}, {"id": "ceiling", "name": "ceiling", "noun": "ceiling"}]


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


def toy_place(folder, extra=()):
    """The scene's stage folder: a floor, a wall the door's hinge edge stands in, a ceiling the fan hangs in, a door,
    a fan, a rover and an astronaut, and `extra` things (name, at, low, high)."""
    seed = pathlib.Path(folder) / "seeds" / PLACE
    (seed / "layers").mkdir(parents=True)
    stage = Usd.Stage.CreateNew(str(seed / "layers/base.usda"))
    stage.SetDefaultPrim(UsdGeom.Xform.Define(stage, f"/{PLACE}").GetPrim())
    box(stage, f"/{PLACE}/Structure/floor", (-6.0, -0.1, -6.0), (6.0, 0.0, 6.0))
    thing(stage, "wall_1", (2.2, 0.0, 1.0), (-0.5, 0.0, -0.1), (0.5, 2.5, 0.1))
    thing(stage, "ceiling_1", (-3.0, 2.8, -3.0), (-1.0, 0.0, -1.0), (1.0, 0.2, 1.0))
    thing(stage, "door_1", (3.0, 0.0, 1.0), (-0.45, 0.0, -0.05), (0.45, 2.0, 0.05))
    thing(stage, "fan_1", (-3.0, 2.6, -3.0), (-0.6, 0.0, -0.6), (0.6, 0.25, 0.6))
    thing(stage, "rover_1", (-3.0, 0.0, 3.0), (-1.0, 0.0, -0.7), (1.0, 1.0, 0.7))
    thing(stage, "astronaut_1", (0.0, 0.0, -4.0), (-0.25, 0.0, -0.15), (0.25, 1.8, 0.15))
    for name, at, low, high in extra:
        thing(stage, name, at, low, high)
    stage.GetRootLayer().Save()
    top = Sdf.Layer.CreateNew(str(seed / f"{PLACE}.usda"))
    top.subLayerPaths.append("./layers/base.usda")
    top.defaultPrim = PLACE
    top.timeCodesPerSecond = 24.0
    top.Save()
    return seed


def toy_inputs(folder, rows=ROWS, extra=()):
    folder = pathlib.Path(folder)
    (folder / "inventory.json").write_text(json.dumps({"rows": rows}))
    return {"design": folder / "inventory.json", "row kinds": REPO / "data/checks/row-kinds.json",
            "kinds": REPO / "data/checks/motion.json", "seed": toy_place(folder, extra)}


def made(inputs, folder):
    out = pathlib.Path(folder) / "out"
    out.mkdir()
    motion.make(inputs, out, 0, {})
    assert motion.layer_faults(out) == []
    return out, json.loads((out / motion.RECORD).read_text())


def middle_at(output, inputs, prim, seconds):
    """The world middle of a prim's bounds at a second, with the motion layer over the scene's stage."""
    root = Sdf.Layer.CreateAnonymous(".usda")
    root.subLayerPaths = [str(pathlib.Path(output) / "layers/motion.usda"),
                          str(pathlib.Path(inputs["seed"]) / f"{PLACE}.usda")]
    stage = Usd.Stage.Open(root)
    bound = UsdGeom.BBoxCache(seconds * 24.0, ["default"]).ComputeWorldBound(stage.GetPrimAtPath(prim))
    return np.asarray(bound.ComputeAlignedRange().GetMidpoint())


def test_the_door_swings_the_fan_turns_the_rover_stands_and_every_gate_passes():
    with tempfile.TemporaryDirectory() as folder:
        inputs = toy_inputs(folder)
        out, record = made(inputs, folder)
        found = {check.name: check.judge(out, inputs, None) for check in motion.CHECKS}
        door = f"/{PLACE}/Objects/door_1"
        shut, opened = middle_at(out, inputs, door, 0.0), middle_at(out, inputs, door, 8.0)
    assert all(verdict.answer == checks.PASS for verdict in found.values()), {
        name: (verdict.reason, verdict.findings) for name, verdict in found.items() if verdict.answer != checks.PASS}
    moves = {entry["name"]: entry for entry in record["moves"]}
    assert sorted(moves) == ["door_1", "fan_1"] and list(record["still"]) == [f"/{PLACE}/Objects/rover_1"]
    # the hatch kind's cited range is 15 to 53 degrees a second: its middle, 34
    assert moves["door_1"]["swing"]["speed"] == 34.0 and moves["door_1"]["swing"]["angle"] == 90.0
    # the ceiling fan's cited range is 400 to 1080: the middle 740 is 41.1 turns in 20 s, so 41 turns, 738 a second
    assert moves["fan_1"]["spin"]["speed"] == 738.0
    # shut, the leaf's middle stands at its own spot (3, 1, 1); its hinge is its left edge, (2.55, 1, 1); a quarter turn
    # about the upright there (rotateY +90: x to -z) carries the middle 0.45 m from +x of the hinge to -z of it
    assert np.allclose(shut, (3.0, 1.0, 1.0), atol=1e-6), shut
    assert np.allclose(opened, (2.55, 1.0, 0.55), atol=1e-4), opened


def test_with_nobody_in_the_scene_the_door_stands_shut():
    rows = [row for row in ROWS if row["id"] != "astronaut"]
    with tempfile.TemporaryDirectory() as folder:
        _, record = made(toy_inputs(folder, rows), folder)
    assert sorted(entry["name"] for entry in record["moves"]) == ["fan_1"]
    assert record["still"][f"/{PLACE}/Objects/door_1"].startswith("nobody passes through it")


def test_a_row_that_moves_with_no_object_fails_designed():
    rows = ROWS + [{"id": "crane", "name": "crane", "noun": "crane"}]
    with tempfile.TemporaryDirectory() as folder:
        inputs = toy_inputs(folder, rows)
        out, _ = made(inputs, folder)
        verdict = next(check for check in motion.CHECKS if check.name == "designed").judge(out, inputs, None)
    assert verdict.answer == checks.FAIL
    assert verdict.findings == ("crane moves (swing), and no object of it stands on the stage",), verdict.findings


# A post standing in the quarter the door sweeps opening its rule's way (rotateY +90: from +x of its hinge (2.55, 1)
# toward -z): its corner (2.8, 0.6) lies 0.47 m from the hinge, inside the leaf's 0.9 m; and its mirror over the
# door's line (z = 1), in the quarter it sweeps the other way.
POST = ("wall_2", (3.0, 0.0, 0.4), (-0.2, 0.0, -0.2), (0.2, 1.0, 0.2))
MIRROR = ("wall_3", (3.0, 0.0, 1.6), (-0.2, 0.0, -0.2), (0.2, 1.0, 0.2))


def test_a_door_that_strikes_its_rule_s_way_is_fitted_to_swing_the_other_way():
    with tempfile.TemporaryDirectory() as folder:
        inputs = toy_inputs(folder, extra=(POST,))
        out, record = made(inputs, folder)
        clear = next(check for check in motion.CHECKS if check.name == "clear").judge(out, inputs, None)
        opened = middle_at(out, inputs, f"/{PLACE}/Objects/door_1", 8.0)
    door = next(entry for entry in record["moves"] if entry["name"] == "door_1")
    assert door["swing"]["angle"] == -90.0 and "fitted by the clear gate" in door["from"], door
    assert clear.answer == checks.PASS, (clear.reason, clear.findings)
    # a quarter turn the other way (rotateY -90: x to +z) carries the middle 0.45 m from +x of the hinge to +z of it
    assert np.allclose(opened, (2.55, 1.0, 1.45), atol=1e-4), opened


def test_a_door_that_strikes_every_way_stands_with_its_strike():
    with tempfile.TemporaryDirectory() as folder:
        inputs = toy_inputs(folder, extra=(POST, MIRROR))
        out, record = made(inputs, folder)
        clear = next(check for check in motion.CHECKS if check.name == "clear").judge(out, inputs, None)
    assert sorted(entry["name"] for entry in record["moves"]) == ["fan_1"]
    reason = record["still"][f"/{PLACE}/Objects/door_1"]
    # at 60 degrees, the least tried, the leaf still sweeps the post's corner (48 degrees round, 0.67 m out) either way
    assert reason.startswith("it strikes at every way it was tried") and "wall_" in reason, reason
    assert clear.answer == checks.PASS, (clear.reason, clear.findings)


def test_a_hatch_lying_flat_stands():
    rows = ROWS + [{"id": "hatch", "name": "floor hatch", "noun": "hatch"}]
    flat = ("hatch_1", (-1.0, 0.0, -1.0), (-0.3, 0.0, -0.3), (0.3, 0.1, 0.3))
    with tempfile.TemporaryDirectory() as folder:
        _, record = made(toy_inputs(folder, rows, extra=(flat,)), folder)
    assert sorted(entry["name"] for entry in record["moves"]) == ["door_1", "fan_1"]
    assert record["still"][f"/{PLACE}/Objects/hatch_1"] == from_design.LYING


def test_covered_asks_for_the_design_s_moving_rows_only():
    # a rocket named as an old record's moving kind (data/checks/motion.json's prims), on no moving row, is not asked
    # for; the design's door taken out of the record (neither moved nor standing with a reason) is
    rocket = ("rocket_1", (-4.0, 0.0, 0.0), (-0.5, 0.0, -0.5), (0.5, 3.0, 0.5))
    rows = ROWS + [{"id": "rocket", "name": "rocket", "noun": "rocket"}]
    with tempfile.TemporaryDirectory() as folder:
        inputs = toy_inputs(folder, rows, extra=(rocket,))
        out, record = made(inputs, folder)
        covered = next(check for check in motion.CHECKS if check.name == "covered")
        kept = covered.judge(out, inputs, None)
        (out / motion.RECORD).write_text(json.dumps(dict(record, moves=[entry for entry in record["moves"]
                                                                        if entry["name"] != "door_1"])))
        dropped = covered.judge(out, inputs, None)
    assert kept.answer == checks.PASS and kept.measures["moving kinds"] == 3, (kept.reason, kept.findings)
    assert dropped.answer == checks.FAIL and dropped.findings == (f"/{PLACE}/Objects/door_1 (door)",), dropped.findings


def test_a_swing_is_tried_its_rule_s_way_and_the_other_down_to_sixty_degrees():
    assert motion.swing_angles(90.0) == [90.0, -90.0, 80.0, -80.0, 70.0, -70.0, 60.0, -60.0]


def test_a_speed_is_the_middle_of_its_kind_s_cited_range():
    assert from_design.middle_speed({"angular": [15.0, 53.0]}, "angular") == 34.0
    assert abs(from_design.middle_speed({"linear": [0.08, 0.4]}, "linear") - 0.24) < 1e-12


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[3] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
