"""The motion layer's models step's layout and gates on the garage's own seed, with a stand-in rover (four wheels and a body, at the
rover's size): laid on the lift it rests; lifted it floats; pushed into a post it lies in it; the outline and parts
gates fail by name. Needs the garage's seed ($PROPS_HOME/work/usd-r3/garage)."""
import json
import pathlib
import shutil
import sys

import numpy as np
import trimesh

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[4]))
import score.stages.motion.models as models  # noqa: E402
from score import checks  # noqa: E402
from score.store import PROPS_HOME  # noqa: E402

SEED = PROPS_HOME / "work/usd-r3/garage"
ENTRY = {"row": "rover", "take": "kit5-rover-3", "kind": "garage_rover", "on": "rover_lift_1", "turn": "across"}


def stand_in():
    """A rover 1.72 wide, 1.66 tall, 3.03 long: four wheels of 0.6 m and a body over them, its foot at y 0."""
    wheels = [trimesh.creation.cylinder(radius=0.3, height=0.25, sections=24,
                                        transform=trimesh.transformations.rotation_matrix(np.pi / 2, [0, 0, 1]))
              for _ in range(4)]
    for wheel, (x, z) in zip(wheels, [(-0.735, -1.21), (0.735, -1.21), (-0.735, 1.21), (0.735, 1.21)]):
        wheel.apply_translation([x, 0.3, z])
    body = trimesh.creation.box([1.2, 1.06, 3.03])
    body.apply_translation([0, 1.13, 0])
    return trimesh.util.concatenate([*wheels, body])


def write_asset(mesh, folder):
    """The stand-in as the asset writer lays a model: /rover_1/geo."""
    from pxr import Usd, UsdGeom, Vt
    (folder / "assets").mkdir(parents=True, exist_ok=True)
    stage = Usd.Stage.CreateNew(str(folder / "assets/rover_1.usdc"))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    root = UsdGeom.Xform.Define(stage, "/rover_1")
    stage.SetDefaultPrim(root.GetPrim())
    geo = UsdGeom.Mesh.Define(stage, "/rover_1/geo")
    geo.CreatePointsAttr(Vt.Vec3fArray.FromNumpy(np.asarray(mesh.vertices, dtype=np.float32)))
    geo.CreateFaceVertexCountsAttr([3] * len(mesh.faces))
    geo.CreateFaceVertexIndicesAttr(np.asarray(mesh.faces).ravel().tolist())
    stage.GetRootLayer().Save()


def output_with(folder, matrix, outline=0.8):
    """An output folder: the layer laying the stand-in at `matrix`, its asset and placed.json."""
    from pxr import Sdf
    shutil.rmtree(folder, ignore_errors=True)
    write_asset(stand_in(), folder)
    (folder / "layers").mkdir()
    layer = Sdf.Layer.CreateNew(str(folder / models.LAYER))
    models.lay(layer, "garage", "rover_1", ENTRY, matrix, "test")
    layer.Save()
    (folder / "placed.json").write_text(json.dumps({"models": {"rover_1": {"take": ENTRY["take"],
                                                                             "outline": outline}}}))
    return folder


def test_layout_and_gates(work):
    stage = models.seed_stage(SEED)
    matrix, yaw, drop = models.pose(np.asarray(stand_in().vertices), ENTRY, stage, "garage")
    assert yaw == 0.0 and abs(drop - models.DROP_FROM) < 0.02, (yaw, drop)  # across the posts, onto the floor
    inputs = {"seed": SEED}
    laid = models.judge_resting(output_with(work / "laid", matrix), inputs, None)
    assert laid.answer == checks.PASS, laid
    lifted = matrix.copy()
    lifted[3, 1] += 0.2
    floats = models.judge_resting(output_with(work / "lifted", lifted), inputs, None)
    assert floats.answer == checks.FAIL and "floats" in floats.findings[0], floats
    pushed = matrix.copy()
    pushed[3, 0] += 1.2
    inside = models.judge_resting(output_with(work / "pushed", pushed), inputs, None)
    assert inside.answer == checks.FAIL and "rover_lift_1" in " ".join(inside.findings), inside
    unlike = models.judge_outline(output_with(work / "unlike", matrix, outline=0.3), inputs, None)
    assert unlike.answer == checks.FAIL and "rover_1" in unlike.findings[0], unlike
    parts = work / "parts"
    parts.mkdir()
    (parts / "parts.json").write_text(json.dumps({"takes": {"kit5-rover-3": {
        "parts": [{"words": "white mudguards"}], "finishes": [{"finish": "white mudguards"},
                                                              {"finish": "black tyres"}]}}}))
    missing = models.judge_parts(work / "laid", {"surfaces-parts": parts}, None)
    assert missing.answer == checks.FAIL and "black tyres" in missing.findings[0], missing


def test_a_model_stands_on_its_settled_support(work):
    """assembly@garage (2026-10-15): the settle let the lift down 14 cm off its spot and the rover, laid on the seed's
    lift, lay 8.8 cm inside the settled one. Over a settle layer that moves the lift 1.2 m east the rover is laid 1.2 m
    east too, and the resting gate judges it on the settled lift: the rover laid on the seed's lift lies in it."""
    from pxr import Gf, Sdf, UsdGeom
    settled = work / "settled"
    (settled / "layers").mkdir(parents=True)
    layer = Sdf.Layer.CreateNew(str(settled / models.SETTLE_LAYER))
    seed = models.seed_stage(SEED)  # held: a prim of a stage nothing holds expires at once
    lift = UsdGeom.Xformable(seed.GetPrimAtPath("/garage/Objects/rover_lift_1")).GetLocalTransformation()
    moved = lift * Gf.Matrix4d().SetTranslate(Gf.Vec3d(1.2, 0, 0))
    spec = Sdf.CreatePrimInLayer(layer, "/garage/Objects/rover_lift_1")
    spec.specifier = Sdf.SpecifierOver
    Sdf.AttributeSpec(spec, "xformOp:transform", Sdf.ValueTypeNames.Matrix4d).default = moved
    order = Sdf.AttributeSpec(spec, "xformOpOrder", Sdf.ValueTypeNames.TokenArray, variability=Sdf.VariabilityUniform)
    order.default = ["xformOp:transform"]
    layer.Save()
    points = np.asarray(stand_in().vertices)
    before, _, _ = models.pose(points, ENTRY, models.seed_stage(SEED), "garage")
    after, _, _ = models.pose(points, ENTRY, models.seed_stage(SEED, settled), "garage")
    assert abs(after[3, 0] - before[3, 0] - 1.2) < 0.01, (before[3], after[3])
    inputs = {"seed": SEED, "settle": settled}
    assert models.judge_resting(output_with(work / "settled-laid", after), inputs, None).answer == checks.PASS
    old = models.judge_resting(output_with(work / "seed-laid", before), inputs, None)
    assert old.answer == checks.FAIL and "rover_lift_1" in " ".join(old.findings), old


def test_a_model_lies_along_the_place_s_axis_its_record_names_and_off_its_support_s_middle():
    """The hangar's ship (2026-10-15): its 7.2 m pad is square, so "along" the pad laid the 31 m hull across the 26 m
    hangar. `turn` "x" or "z" lays its long side along the place's axis; `off` sets it off the support's middle."""
    stage = models.seed_stage(SEED)
    points = np.asarray(stand_in().vertices)  # 3.03 m long along z
    along_z, yaw_z, _ = models.pose(points, dict(ENTRY, turn="z"), stage, "garage")
    _, yaw_x, _ = models.pose(points, dict(ENTRY, turn="x"), stage, "garage")
    assert (yaw_z, yaw_x) == (0.0, 90.0), (yaw_z, yaw_x)
    moved, _, _ = models.pose(points, dict(ENTRY, turn="z", off=[0.0, -0.4]), stage, "garage")
    assert abs(moved[3, 2] - along_z[3, 2] + 0.4) < 1e-6 and abs(moved[3, 0] - along_z[3, 0]) < 1e-6, (moved, along_z)


def test_a_mounted_piece_goes_where_its_host_plan_puts_it():
    """A ship 31 m long laid along z with its nose at -z: a piece 2 m back from the tip, 1 m to starboard (+x when
    facing -z) and 0.5 m up sits there; a host with no nose refuses its pieces by name."""
    low, high = (-4.0, 0.2, -15.5), (4.0, 6.2, 15.5)
    point = models.mount_point(low, high, "-z", [1.0, 2.0, 0.5])
    assert np.allclose(point, [1.0, 0.7, -13.5]), point
    assert np.allclose(models.mount_point(low, high, "+x", [1.0, 0.0, 0.0]), [4.0, 0.2, 1.0])  # facing +x, starboard is +z
    hull = trimesh.creation.box(bounds=(low, high))
    hosts = {"ship_1": (np.array(low), np.array(high), np.eye(3), 0.0, hull)}
    piece = {"mounted": {"on": "ship_1", "at": [1.0, 2.0, 0.5]}}
    matrix = models.mounted_pose(np.array([[-0.5, -0.5, -0.5], [0.5, 0.5, 0.5]]), piece, hosts,
                                   {"models": {"ship_1": {"nose": "-z"}}})
    assert np.allclose(matrix[3, :3], [1.0, 0.7, -13.5]), matrix
    # under the hull's floor (0.2 up), moved up onto it; out past its side (x 4.0), moved in onto it
    under = {"mounted": {"on": "ship_1", "at": [1.0, 2.0, -1.0], "onto": "up"}}
    lifted = models.mounted_pose(np.array([[-0.5, -0.5, -0.5], [0.5, 0.5, 0.5]]), under, hosts,
                                   {"models": {"ship_1": {"nose": "-z"}}})
    assert abs(lifted[3, 1] + 0.5 - (0.2 - models.MOUNT_CLEAR)) < 1e-6, lifted  # its top 2 mm under the floor
    outside = {"mounted": {"on": "ship_1", "at": [5.0, 2.0, 1.0], "onto": "in"}}
    pulled = models.mounted_pose(np.array([[-0.5, -0.5, -0.5], [0.5, 0.5, 0.5]]), outside, hosts,
                                   {"models": {"ship_1": {"nose": "-z"}}})
    assert abs(pulled[3, 0] - 0.5 - (4.0 + models.MOUNT_CLEAR)) < 1e-6, pulled  # its inner side 2 mm off the side
    try:
        models.mounted_pose(np.zeros((2, 3)), piece, hosts, {"models": {"ship_1": {}}})
    except ValueError as refused:
        assert "ship_1" in str(refused), refused
    else:
        raise AssertionError("a host with no nose laid its piece")


def test_assembly_takes_it(work):
    """The assembly holds the motion models layer just over the base and carries the model's asset; the model stands
    as its inventory row, where its sound plays (assembly@garage, 2026-10-15: laid as rover_1, rover_idle found
    nothing)."""
    from pxr import Sdf
    from score.stages import assembly
    (work / "place/layers").mkdir(parents=True)
    base = Sdf.Layer.CreateNew(str(work / "place/layers/base.usda"))
    Sdf.CreatePrimInLayer(base, "/garage/Objects")  # the seed's base defines the place and its objects
    for path in ("/garage", "/garage/Objects"):
        base.GetPrimAtPath(path).specifier = Sdf.SpecifierDef
    base.Save()
    root = Sdf.Layer.CreateNew(str(work / "place/garage.usda"))
    root.subLayerPaths = ["./layers/edit.usda", assembly.BASE_LAYER]
    root.Save()
    assembly.take_layer(work / "laid", work / "place/garage.usda", *assembly.LAYERS["motion-models"][1:])
    layers = list(Sdf.Layer.FindOrOpen(str(work / "place/garage.usda")).subLayerPaths)
    assert layers == ["./layers/edit.usda", "./layers/motion-models.usda", assembly.BASE_LAYER], layers
    assert (work / "place/assets/rover_1.usdc").exists() and (work / "place" / models.LAYER).exists()
    from pxr import Usd
    from score.stages.assembly import sounds
    stage = Usd.Stage.Open(str(work / "place/garage.usda"))
    found = sounds.prims_by_name(stage, "garage")
    assert [prim.GetName() for prim in found.get("rover", [])] == ["rover_1"], sorted(found)  # its sound's row


def test_boxes_grounds_the_model_rows(work):
    """motion-models-boxes asks SAM 3 for the hangar's ship and its ground_box row only, and its gate fails a box SAM 3
    found elsewhere (the cloud call, the box judge and the partition's record stood in for)."""
    import score.stages.motion.models.boxes as boxes
    box_check, box_masks_cloud = boxes.box_tools()
    recorded = []
    asked = []

    pictures = {}

    def fake_mask(jobs, out, *rest):
        found = json.loads(pathlib.Path(jobs).read_text())
        asked.extend(row["key"] for job in found for row in job["rows"])
        pictures.update({row["key"]: pathlib.Path(job["picture"]).name for job in found for row in job["rows"]})
        pathlib.Path(out).write_text(json.dumps({row["key"]: [{"box": [0, 0, 50, 50], "inside": 0.0, "fills": 0.0,
                                                                  "score": 0.9}]
                                                 for job in found for row in job["rows"]}))
    kept = box_masks_cloud.mask, box_check.record_results, boxes.judged
    box_masks_cloud.mask, box_check.record_results = fake_mask, lambda results, measured: recorded.append(results)
    boxes.judged = lambda *rest: {}  # the Gemini box judge (a paid ask) stood in for: it gives no verdict
    try:
        out = work / "boxes"
        out.mkdir()
        inputs = {"inventory": boxes.REPO / "data/inventory/hangar.json",
                  **{f"view {view}": PROPS_HOME / f"work/scene/hangar/views/{name}.png"
                     for view, name in (("v1", "K01"), ("v2", "shuttle"), ("v3", "thrusters"))}}
        boxes.make_boxes(inputs, out, 0, {})
    finally:
        box_masks_cloud.mask, box_check.record_results, boxes.judged = kept
    # the model rows (the hull and its three thruster designs) and the ground_box one
    assert sorted(asked) == ["hangar.lattice_ring_rib", "hangar.lift_thruster", "hangar.main_engine",
                             "hangar.nose_thruster", "hangar.ship"], asked
    # each row measured on its own view's picture (2026-10-15: every job got the first row's, the cockpit's console
    # on the seat's picture), both ways: the girder on the hall, the hull on the shuttle, the thrusters on theirs
    assert pictures == {"hangar.lattice_ring_rib": "K01.png", "hangar.ship": "shuttle.png",
                        "hangar.main_engine": "thrusters.png", "hangar.lift_thruster": "thrusters.png",
                        "hangar.nose_thruster": "thrusters.png"}, pictures
    verdict = boxes.judge_grounded(out, inputs, None)
    assert verdict.answer == checks.FAIL and "hangar.ship: unchecked (SAM 3: off)" in verdict.findings, verdict
    assert recorded and recorded[0]["hangar.ship"]["passes"] is None  # an ungrounded box is not recorded as passing


def main():
    work = PROPS_HOME / "store-tests/models"
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    try:
        test_layout_and_gates(work)
        test_a_model_stands_on_its_settled_support(work)
        test_a_model_lies_along_the_place_s_axis_its_record_names_and_off_its_support_s_middle()
        test_a_mounted_piece_goes_where_its_host_plan_puts_it()
        test_assembly_takes_it(work)
        test_boxes_grounds_the_model_rows(work)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    print("models_test: ok")


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[4] / "conftest.py"))["refuse_outside_sandbox"]()
    main()
