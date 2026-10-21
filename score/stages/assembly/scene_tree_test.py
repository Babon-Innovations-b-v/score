"""The scene tree stands each child scene its plan lays out in the scene's own assembly, referenced from the child's
own tree at its hold, so opening the parent opens the whole tree; its gate fails a child laid out and not stood, one
of another size than its hold, and one standing where the plan lays out nothing. Toy scenes: a yard holding a shed
(its own frame shifted) and a turned hut, the shed holding a nook. Every expected point is worked out by hand from the
plans below, not by the module's own arithmetic.

Run: .venv/bin/python score/stages/assembly/scene_tree_test.py
"""
import json
import os
import pathlib
import shutil
import sys
import tempfile

# Scratch on disk under $PROPS_HOME/tmp, never /tmp (a RAM-backed tmpfs on the PC).
tempfile.tempdir = str(pathlib.Path(os.environ.get("PROPS_HOME", pathlib.Path.home() / ".farm-factory-props")) / "tmp")
pathlib.Path(tempfile.tempdir).mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))

from score import checks  # noqa: E402
from score.stages.assembly import scene_tree  # noqa: E402

# The yard: 20 x 12 m, no frame, so its north-west corner is at (-10, 0, -6). It holds the shed at (2, 3) and the hut
# at (10, 5), plan metres x east, y south.
YARD = {"w": 20.0, "d": 12.0, "holds": [{"place": "shed", "row": None, "x": 2.0, "y": 3.0, "w": 4.0, "d": 3.0},
                                       {"place": "hut", "row": None, "x": 10.0, "y": 5.0, "w": 4.0, "d": 3.0}]}
# The shed: 4 x 3 m, its north-west corner at (5, 0, -2) of its own frame; it holds the nook at (1, 1).
SHED = {"w": 4.0, "d": 3.0, "frame": {"anchor": {"plan": [0.0, 0.0], "place": [5.0, 0.0, -2.0]}},
        "holds": [{"place": "nook", "row": None, "x": 1.0, "y": 1.0, "w": 2.0, "d": 1.0}]}
# The hut: 4 x 3 m, turned: its plan's east runs along its frame's +z, its south along -x, its corner at the origin.
HUT = {"w": 4.0, "d": 3.0, "frame": {"anchor": {"plan": [0.0, 0.0], "place": [0.0, 0.0, 0.0]},
                                     "toward": {"plan": [1.0, 0.0], "place": [0.0, 0.0, 1.0]}}}
# The nook: 2 x 1 m, no frame: its north-west corner at (-1, 0, -0.5).
NOOK = {"w": 2.0, "d": 1.0}


def a_scene(root, scene, crate):
    """A scene's stage as the assembly leaves it: a root over layers/base.usda, one crate at `crate`."""
    from pxr import Gf, Usd, UsdGeom
    folder = root / scene
    (folder / "layers").mkdir(parents=True)
    base = Usd.Stage.CreateNew(str(folder / "layers/base.usda"))
    UsdGeom.Xform.Define(base, f"/{scene}")
    UsdGeom.Xform.Define(base, f"/{scene}/Objects/crate_1").AddTranslateOp().Set(Gf.Vec3d(*crate))
    base.GetRootLayer().Save()
    stage = Usd.Stage.CreateNew(str(folder / f"{scene}.usda"))
    stage.GetRootLayer().subLayerPaths.append("./layers/base.usda")
    stage.SetDefaultPrim(stage.GetPrimAtPath(f"/{scene}"))
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    stage.GetRootLayer().Save()
    return folder


def a_plan(root, scene, plan):
    path = root / "plans" / f"{scene}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(plan))
    return path


def tree_of(root, scene, assembly, plan, children):
    """scene_tree.make's output for the scene: its assembly, its plan, and each child's (tree, plan)."""
    out = root / "trees" / scene
    out.mkdir(parents=True)
    inputs = {"assembly": assembly, "plan": a_plan(root, scene, plan) if plan else None}
    for child, (tree, child_plan) in children.items():
        inputs[f"scene-tree@{child}"] = tree
        inputs[f"plan {child}"] = a_plan(root, child, child_plan)
    inputs = {name: path for name, path in inputs.items() if path is not None}
    scene_tree.make(inputs, out, 0, {})
    return out, inputs


def crate_at(stage, path):
    from pxr import UsdGeom
    return [round(value, 4) for value in
            UsdGeom.XformCache().GetLocalToWorldTransform(stage.GetPrimAtPath(path)).ExtractTranslation()]


def the_yard(root, hut_plan=HUT, children=("shed", "hut")):
    """The yard's tree over the shed's tree (holding the nook's) and the hut's."""
    nook, _ = tree_of(root, "nook", a_scene(root / "made", "nook", (0.0, 0.0, 0.0)), NOOK, {})
    shed, _ = tree_of(root, "shed", a_scene(root / "made", "shed", (6.0, 0.0, -1.0)), SHED, {"nook": (nook, NOOK)})
    hut, _ = tree_of(root, "hut", a_scene(root / "made", "hut", (-1.0, 0.0, 2.0)), HUT, {})
    trees = {"shed": (shed, SHED), "hut": (hut, hut_plan)}
    return tree_of(root, "yard", a_scene(root / "made", "yard", (0.0, 0.0, 0.0)), YARD,
                   {child: trees[child] for child in children})


def test_opening_the_yard_opens_the_whole_tree_each_child_at_its_hold():
    """The shed's crate at (6, 0, -1) of its frame is plan (1, 1) on the shed, (3, 4) on the yard: (-7, 0, -2). The
    nook's crate at its middle, (0, 0, 0), is plan (1, 0.5) on the nook, (2, 1.5) on the shed, (4, 4.5) on the yard:
    (-6, 0, -1.5). The hut's crate at (-1, 0, 2) is plan (2, 1) on the turned hut, (12, 6) on the yard: (2, 0, 0)."""
    from pxr import Usd
    root = pathlib.Path(tempfile.mkdtemp())
    try:
        yard, inputs = the_yard(root)
        stage = Usd.Stage.Open(str(yard / "yard.usda"))
        assert crate_at(stage, "/yard/Scenes/shed/Objects/crate_1") == [-7.0, 0.0, -2.0]
        assert crate_at(stage, "/yard/Scenes/shed/Scenes/nook/Objects/crate_1") == [-6.0, 0.0, -1.5]
        assert crate_at(stage, "/yard/Scenes/hut/Objects/crate_1") == [2.0, 0.0, 0.0]
        assert crate_at(stage, "/yard/Objects/crate_1") == [0.0, 0.0, 0.0]
        # each child its own layer stack, copied whole: the shed's tree keeps its own root, layers and nook
        assert (yard / "scenes/shed/shed.usda").is_file() and (yard / "scenes/shed/scenes/nook/nook.usda").is_file()
        verdict = scene_tree.judge_children(yard, inputs, None)
        assert verdict.answer == checks.PASS, verdict.findings
        assert verdict.measures["children"] == 2
        nook = scene_tree.judge_children(root / "trees/nook", {"plan": root / "plans/nook.json"}, None)
        assert nook.answer == checks.PASS and nook.reason == "its plan lays out no child scene"
    finally:
        shutil.rmtree(root)


def test_a_child_laid_out_and_not_stood_fails_by_name():
    """The yard's plan lays out the hut; a run with no hut read (in design: no scene of the batch) stands the shed
    alone and fails on the hut."""
    root = pathlib.Path(tempfile.mkdtemp())
    try:
        yard, inputs = the_yard(root, children=("shed",))
        verdict = scene_tree.judge_children(yard, inputs, None)
        assert verdict.answer == checks.FAIL
        assert verdict.findings == ("/yard/Scenes/hut: laid out on yard's plan, not in the stage (no scene of the "
                                    "batch: its design is not done)",)
    finally:
        shutil.rmtree(root)


def test_a_child_whose_plan_is_not_its_holds_size_fails():
    """A hut planned 5 m wide in a 4 m hold: its middle on the hold's, so its corners land half a metre out."""
    root = pathlib.Path(tempfile.mkdtemp())
    try:
        yard, inputs = the_yard(root, hut_plan={**HUT, "w": 5.0})
        verdict = scene_tree.judge_children(yard, inputs, None)
        assert verdict.answer == checks.FAIL
        assert "/yard/Scenes/hut: its plan is 5.0 x 3.0 m, its hold 4.0 x 3.0 m" in verdict.findings
    finally:
        shutil.rmtree(root)


def test_a_child_standing_where_the_plan_lays_out_nothing_fails():
    """The yard's plan edited to hold the shed only, its tree still standing the hut."""
    root = pathlib.Path(tempfile.mkdtemp())
    try:
        yard, inputs = the_yard(root)
        inputs["plan"].write_text(json.dumps({**YARD, "holds": YARD["holds"][:1]}))
        verdict = scene_tree.judge_children(yard, inputs, None)
        assert verdict.findings == ("/yard/Scenes/hut: read as a child scene, laid out nowhere on yard's plan",)
    finally:
        shutil.rmtree(root)


def test_a_scene_with_no_plan_read_is_unknown_not_passed():
    """The yard's tree made with no plan of its own read (a parent scene whose plan is not kept yet): it stands no
    child, and what it should hold cannot be told, so the gate answers unknown, never pass."""
    root = pathlib.Path(tempfile.mkdtemp())
    try:
        yard, inputs = tree_of(root, "yard", a_scene(root / "made", "yard", (0.0, 0.0, 0.0)), None, {})
        verdict = scene_tree.judge_children(yard, inputs, None)
        assert verdict.answer == checks.UNKNOWN
        assert verdict.reason == "no plan of yard read: which child scenes it holds cannot be told"
    finally:
        shutil.rmtree(root)


def test_the_plans_read_and_a_scene_holding_itself_refused():
    """The plan read is the kept one where there is one, else the data's; each child's plan is declared; a plan laying
    out a scene above it is refused."""
    root = pathlib.Path(tempfile.mkdtemp())
    kept, repo = scene_tree.KEPT, scene_tree.REPO
    try:
        scene_tree.KEPT, scene_tree.REPO = root / "kept", root / "repo"
        for folder, scene, plan in (("kept", "yard", YARD), ("repo/data/plans", "shed", SHED),
                                    ("kept", "hut", HUT), ("repo/data/plans", "nook", NOOK)):
            (root / folder).mkdir(parents=True, exist_ok=True)
            (root / folder / f"{scene}.json").write_text(json.dumps(plan))
        assert scene_tree.files("yard") == {"plan": "{home}/design/plans/yard.json",
                                            "plan hut": "{home}/design/plans/hut.json",
                                            "plan shed": "{data}/plans/shed.json"}
        assert scene_tree.files("nook") == {"plan": "{data}/plans/nook.json"}
        assert scene_tree.held("shed") == ["nook"]
        (root / "repo/data/plans/nook.json").write_text(json.dumps({**NOOK, "holds": [{"place": "yard"}]}))
        try:
            scene_tree.held("yard")
        except ValueError as refused:
            assert "cannot hold itself" in str(refused)
        else:
            raise AssertionError("a plan laying out a scene above it was read")
    finally:
        scene_tree.KEPT, scene_tree.REPO = kept, repo
        shutil.rmtree(root)


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[3] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
