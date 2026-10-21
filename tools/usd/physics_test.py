"""Check the physics layers on a small place made here, without Blender: each object's mass from its area, its
material and triangles, a drop lifted over its target, a blocked fall refused, the hinge at its pins' middle with its
limits and its motor's window, the hand's path, the layers' order under the edit layer, and a run's motion played
back by time samples.

Run: .venv/bin/python tools/usd/physics_test.py [<folder>]   (a folder keeps the toy place, for a Blender run)
"""
import json
import math
import pathlib
import sys
import tempfile

import numpy as np
from pxr import Gf, Sdf, Usd, UsdGeom, UsdPhysics, UsdShade

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
import physics  # noqa: E402

PLACE = "toy"
MATERIALS = json.loads((REPO / "data/physics/materials.json").read_text())
# Name: (low corner, high corner), the stage's frame; a door frame is its two posts and its lintel.
BOXES = {"floor_plate_1": [((-3, -0.04, -3), (3, 0, 3))], "table_1": [((-1.5, 0, -0.5), (-0.5, 0.76, 0.5))],
         "crate_1": [((1.85, 0, 1.85), (2.15, 0.3, 2.15))], "crate_2": [((2.35, 0, 1.85), (2.65, 0.3, 2.15))],
         "frame_1": [((-1.2, 0, -2.65), (-1.13, 2.75, -2.35)), ((1.13, 0, -2.65), (1.2, 2.75, -2.35)),
                     ((-1.2, 2.67, -2.65), (1.2, 2.75, -2.35))],
         "leaf_1": [((-1.12, 0, -2.56), (1.12, 2.66, -2.44))],
         "pin_1": [((1.13, 0.5, -2.44), (1.25, 0.9, -2.3))], "pin_2": [((1.13, 2.0, -2.44), (1.25, 2.4, -2.3))],
         "wheel_1": [((-0.2, 1.0, -2.44), (0.2, 1.4, -2.38))], "stool_1": [((1.5, 0.01, 0.8), (1.9, 0.48, 1.2))]}
RECORD = {"place": PLACE, "body": "moon", "gravity": 1.62, "material": "steel", "seconds": 4.0,
          "drops": [{"object": "crate_1", "onto": "table_1", "at": [-1.0, 0.0], "over": 0.5},
                    {"object": "crate_2", "onto": "floor", "at": [2.2, 0.5], "over": 0.8}],
          "hinges": [{"leaf": "leaf_1", "frame": "frame_1", "pins": ["pin_1", "pin_2"], "carries": ["wheel_1"],
                      "opens": [0.0, 100.0], "clear": 0.01,
                      "drive": {"speed": 60.0, "torque": 2000.0, "start": 0.5, "end": 2.5}}],
          "pushes": [{"name": "push_stool", "size": [0.15, 0.2, 0.3], "from": [1.2, 0.3, 1.0], "to": [2.2, 0.3, 1.0],
                      "start": 0.5, "end": 1.5}],
          "moved": ["stool_1"]}


def box_points(low, high):
    corners = [(x, y, z) for x in (low[0], high[0]) for y in (low[1], high[1]) for z in (low[2], high[2])]
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    return corners, faces


def mesh(stage, path, boxes, middle):
    points, counts, indices = [], [], []
    for low, high in boxes:
        corners, faces = box_points(np.subtract(low, middle), np.subtract(high, middle))
        indices += [len(points) + corner for face in faces for corner in face]
        counts += [4] * len(faces)
        points += corners
    found = UsdGeom.Mesh.Define(stage, path)
    found.CreatePointsAttr([Gf.Vec3f(*point) for point in points])
    found.CreateFaceVertexCountsAttr(counts)
    found.CreateFaceVertexIndicesAttr(indices)
    return found


def toy_place(folder):
    """A room with a table, two crates, a hinged door in its frame, a stool, laid as the export lays objects."""
    folder = pathlib.Path(folder)
    (folder / "layers").mkdir(parents=True)
    Sdf.Layer.CreateNew(str(folder / "layers/edit.usda")).Save()
    stage = Usd.Stage.CreateNew(str(folder / "layers/base.usda"))
    place = UsdGeom.Xform.Define(stage, f"/{PLACE}")
    stage.SetDefaultPrim(place.GetPrim())
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    for name, boxes in BOXES.items():
        middle = np.mean([np.add(low, high) / 2 for low, high in boxes], axis=0)
        holder = UsdGeom.Xform.Define(stage, f"/{PLACE}/Objects/{name}")
        holder.MakeMatrixXform().Set(Gf.Matrix4d().SetTranslate(Gf.Vec3d(*middle)))
        mesh(stage, f"/{PLACE}/Objects/{name}/geo", boxes, middle)
        hull = mesh(stage, f"/{PLACE}/Objects/{name}/collision", boxes, middle)
        hull.CreatePurposeAttr(UsdGeom.Tokens.guide)
        UsdPhysics.CollisionAPI.Apply(hull.GetPrim())
        UsdPhysics.MeshCollisionAPI.Apply(hull.GetPrim()).CreateApproximationAttr("convexHull")
    stage.Save()
    root = Sdf.Layer.CreateNew(str(folder / f"{PLACE}.usda"))
    root.subLayerPaths[:] = ["./layers/edit.usda", "./layers/base.usda"]
    root.defaultPrim = PLACE
    root.timeCodesPerSecond = 24
    root.pseudoRoot.SetInfo("upAxis", "Y")
    root.pseudoRoot.SetInfo("metersPerUnit", 1.0)
    root.Save()
    return folder


def composed(folder):
    return Usd.Stage.Open(str(pathlib.Path(folder) / f"{PLACE}.usda"))


def written_once(folder):
    found = physics.write(folder, RECORD, MATERIALS)
    assert not found["faults"], found["faults"]
    return found


def masses_follow_the_area(folder):
    found = written_once(folder)
    steel = MATERIALS["materials"]["steel"]
    assert math.isclose(found["masses"]["crate_1"], 6 * 0.3 ** 2 * steel["sheet"] * steel["density"], rel_tol=1e-3)
    stage = composed(folder)
    floor = stage.GetPrimAtPath(f"/{PLACE}/Objects/floor_plate_1/geo")
    assert UsdPhysics.MeshCollisionAPI(floor).GetApproximationAttr().Get() == "none"
    bound = UsdShade.MaterialBindingAPI(floor).ComputeBoundMaterial("physics")[0]
    assert math.isclose(UsdPhysics.MaterialAPI(bound.GetPrim()).GetDynamicFrictionAttr().Get(), steel["dynamic"],
                        rel_tol=1e-6)
    assert not stage.GetPrimAtPath(f"/{PLACE}/Objects/table_1").HasAPI(UsdPhysics.RigidBodyAPI)
    hull = stage.GetPrimAtPath(f"/{PLACE}/Objects/crate_1/collision")
    assert UsdPhysics.CollisionAPI(hull).GetCollisionEnabledAttr().Get() is True
    scene = UsdPhysics.Scene(stage.GetPrimAtPath(f"/{PLACE}/Physics/Scene"))
    assert math.isclose(scene.GetGravityMagnitudeAttr().Get(), 1.62, rel_tol=1e-6)


def a_drop_is_lifted_over_its_target(folder):
    stage = composed(folder)
    low, high = physics.world_box(stage.GetPrimAtPath(f"/{PLACE}/Objects/crate_1"))
    assert math.isclose(low[1], 0.76 + 0.5, abs_tol=1e-5) and math.isclose((low[0] + high[0]) / 2, -1.0, abs_tol=1e-5)


def the_hinge_stands_at_its_pins(folder):
    stage = composed(folder)
    joint = UsdPhysics.RevoluteJoint(stage.GetPrimAtPath(f"/{PLACE}/Physics/Joints/leaf_1_hinge"))
    assert joint.GetAxisAttr().Get() == "Y" and (joint.GetLowerLimitAttr().Get(), joint.GetUpperLimitAttr().Get()) == \
        (0.0, 100.0)
    frame = physics.world(stage.GetPrimAtPath(f"/{PLACE}/Objects/frame_1"))
    at = frame.Transform(Gf.Vec3d(joint.GetLocalPos0Attr().Get()))
    assert np.allclose(at, (1.19, 1.45, -2.37), atol=1e-5), at
    pin = stage.GetPrimAtPath(f"/{PLACE}/Objects/pin_1/geo")
    assert UsdPhysics.CollisionAPI(pin).GetCollisionEnabledAttr().Get() is False
    assert math.isclose(physics.world_box(stage.GetPrimAtPath(f"/{PLACE}/Objects/leaf_1"))[0][1], 0.01, abs_tol=1e-6)
    drive = UsdPhysics.DriveAPI(joint.GetPrim(), "angular")
    assert [drive.GetMaxForceAttr().Get(code) for code in (0, 12, 36, 60, 61)] == [0.0, 2000.0, 2000.0, 2000.0, 0.0]
    hand = UsdGeom.Xformable(stage.GetPrimAtPath(f"/{PLACE}/Physics/Hands/push_stool"))
    assert np.allclose(hand.ComputeLocalToWorldTransform(0).ExtractTranslation(), (1.2, 0.3, 1.0))
    assert np.allclose(hand.ComputeLocalToWorldTransform(24 * 1.0).ExtractTranslation(), (1.7, 0.3, 1.0))
    root = Sdf.Layer.FindOrOpen(str(pathlib.Path(folder) / f"{PLACE}.usda"))
    assert list(root.subLayerPaths) == ["./layers/edit.usda", "./layers/trial.usda", "./layers/physics.usda",
                                        "./layers/base.usda"]


def the_motion_plays_back(folder):
    before = composed(folder)
    lifted = Gf.Vec3d(physics.world(before.GetPrimAtPath(f"/{PLACE}/Objects/crate_1")).ExtractTranslation())
    down = np.eye(4)
    down[1, 3] = -0.5
    assert physics.write_motion(folder, {"crate_1": [np.eye(4).tolist(), down.tolist()]}) == 2
    stage = composed(folder)
    prim = stage.GetPrimAtPath(f"/{PLACE}/Objects/crate_1")
    assert np.allclose(physics.world(prim, 1).ExtractTranslation(), lifted - Gf.Vec3d(0, 0.5, 0))
    assert Sdf.Layer.FindOrOpen(str(pathlib.Path(folder) / f"{PLACE}.usda")).subLayerPaths[1] == \
        "./layers/physics_motion.usda"


def a_blocked_fall_is_refused():
    with tempfile.TemporaryDirectory() as temporary:
        folder = toy_place(pathlib.Path(temporary) / PLACE)
        record = dict(RECORD, drops=[{"object": "crate_1", "onto": "floor", "at": [-1.0, 0.0], "over": 1.0}])
        found = physics.write(folder, record, MATERIALS)
        assert found["faults"] == ["crate_1: table_1 stands in its fall"], found["faults"]


def main():
    kept = sys.argv[1] if len(sys.argv) > 1 else None
    with tempfile.TemporaryDirectory() as temporary:
        folder = toy_place(pathlib.Path(kept or temporary) / PLACE)
        masses_follow_the_area(folder)
        a_drop_is_lifted_over_its_target(folder)
        the_hinge_stands_at_its_pins(folder)
        if not kept:
            the_motion_plays_back(folder)
    a_blocked_fall_is_refused()
    print("physics_test: ok")


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[2] / "conftest.py"))["refuse_outside_sandbox"]()
    main()
