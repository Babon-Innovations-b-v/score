"""The machines stage's layout and gates on the garage's own seed, with a stand-in rover (four wheels and a body, at the
rover's size): laid on the lift it rests; lifted it floats; pushed into a post it lies in it; the outline and parts
gates fail by name. Needs the garage's seed ($PROPS_HOME/work/usd-r3/garage)."""
import json
import pathlib
import shutil
import sys

import numpy as np
import trimesh

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
import score.stages.machines as machines  # noqa: E402
from score import checks  # noqa: E402
from score.store import PROPS_HOME  # noqa: E402

SEED = PROPS_HOME / "work/usd-r3/garage"
ENTRY = {"take": "kit5-rover-3", "kind": "garage_rover", "on": "rover_lift_1", "turn": "across"}


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
    layer = Sdf.Layer.CreateNew(str(folder / machines.LAYER))
    machines.lay(layer, "garage", "rover_1", ENTRY, matrix, "test")
    layer.Save()
    (folder / "placed.json").write_text(json.dumps({"machines": {"rover_1": {"take": ENTRY["take"],
                                                                             "outline": outline}}}))
    return folder


def test_layout_and_gates(work):
    stage = machines.seed_stage(SEED)
    matrix, yaw, drop = machines.pose(np.asarray(stand_in().vertices), ENTRY, stage, "garage")
    assert yaw == 0.0 and abs(drop - machines.DROP_FROM) < 0.02, (yaw, drop)  # across the posts, onto the floor
    inputs = {"seed": SEED}
    laid = machines.judge_resting(output_with(work / "laid", matrix), inputs, None)
    assert laid.answer == checks.PASS, laid
    lifted = matrix.copy()
    lifted[3, 1] += 0.2
    floats = machines.judge_resting(output_with(work / "lifted", lifted), inputs, None)
    assert floats.answer == checks.FAIL and "floats" in floats.findings[0], floats
    pushed = matrix.copy()
    pushed[3, 0] += 1.2
    inside = machines.judge_resting(output_with(work / "pushed", pushed), inputs, None)
    assert inside.answer == checks.FAIL and "rover_lift_1" in " ".join(inside.findings), inside
    unlike = machines.judge_outline(output_with(work / "unlike", matrix, outline=0.3), inputs, None)
    assert unlike.answer == checks.FAIL and "rover_1" in unlike.findings[0], unlike
    parts = work / "parts"
    parts.mkdir()
    (parts / "parts.json").write_text(json.dumps({"takes": {"kit5-rover-3": {
        "parts": [{"words": "white mudguards"}], "finishes": [{"finish": "white mudguards"},
                                                              {"finish": "black tyres"}]}}}))
    missing = machines.judge_parts(work / "laid", {"surfaces-parts": parts}, None)
    assert missing.answer == checks.FAIL and "black tyres" in missing.findings[0], missing


def test_assembly_takes_it(work):
    """The assembly holds the machines layer just over the base and carries the machine's asset."""
    from pxr import Sdf
    from score.stages import assembly
    (work / "place/layers").mkdir(parents=True)
    Sdf.Layer.CreateNew(str(work / "place/layers/base.usda")).Save()
    root = Sdf.Layer.CreateNew(str(work / "place/garage.usda"))
    root.subLayerPaths = ["./layers/edit.usda", assembly.BASE_LAYER]
    root.Save()
    assembly.take_layer(work / "laid", work / "place/garage.usda", *assembly.LAYERS["machines-layer"][1:])
    layers = list(Sdf.Layer.FindOrOpen(str(work / "place/garage.usda")).subLayerPaths)
    assert layers == ["./layers/edit.usda", "./layers/machines.usda", assembly.BASE_LAYER], layers
    assert (work / "place/assets/rover_1.usdc").exists() and (work / "place" / machines.LAYER).exists()


def test_boxes_grounds_the_machine_rows(work):
    """machines-boxes asks SAM 3 for the hangar's ship only, and its gate fails a box SAM 3 found elsewhere (the cloud
    call and the partition's record stood in for)."""
    import score.stages.machines.boxes as boxes
    box_check, box_masks_cloud = boxes.box_tools()
    recorded = []
    asked = []

    def fake_mask(jobs, out, *rest):
        found = json.loads(pathlib.Path(jobs).read_text())
        asked.extend(row["key"] for job in found for row in job["rows"])
        pathlib.Path(out).write_text(json.dumps({row["key"]: [{"box": [0, 0, 50, 50], "inside": 0.0, "fills": 0.0,
                                                                  "score": 0.9}]
                                                 for job in found for row in job["rows"]}))
    kept = box_masks_cloud.mask, box_check.record_results
    box_masks_cloud.mask, box_check.record_results = fake_mask, lambda results, measured: recorded.append(results)
    try:
        out = work / "boxes"
        out.mkdir()
        inputs = {"inventory": boxes.REPO / "data/inventory/hangar.json",
                  "view v1": PROPS_HOME / "work/scene/hangar/views/K01.png"}
        boxes.make_boxes(inputs, out, 0, {})
    finally:
        box_masks_cloud.mask, box_check.record_results = kept
    assert asked == ["hangar.ship"], asked
    verdict = boxes.judge_grounded(out, inputs, None)
    assert verdict.answer == checks.FAIL and "off" in verdict.findings[0], verdict
    assert recorded and recorded[0]["hangar.ship"]["passes"] is None  # an ungrounded box is not recorded as passing


def main():
    work = PROPS_HOME / "store-tests/machines"
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    try:
        test_layout_and_gates(work)
        test_assembly_takes_it(work)
        test_boxes_grounds_the_machine_rows(work)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    print("machines_test: ok")


if __name__ == "__main__":
    main()
