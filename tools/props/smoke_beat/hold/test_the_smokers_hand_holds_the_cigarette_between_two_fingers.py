"""Invariant: the smoker's pose (hold.py), solved on a body whose right hand hangs palm in, thumb forward, aims the
upper arm 15 degrees forward and 10 out of straight down and bends the forearm 90 degrees toward the front, and lays the
cigarette across the hand at 0.7 of its length from the wrist, a quarter of its breadth toward the thumb (between the
index and the middle finger), in the middle of its thickness, its lit end out the back of the hand and its filter's
middle at the grip.

Breaks that turn it red:
- hold.arm_pose: the elbow bent the other way (-ELBOW) -> the forearm points back
- hold.hold_frame: the palm read as facing out (`@ right`) -> the hand reads as a left one and is refused
- hold.hold_frame: the gap a quarter breadth toward the little finger -> the grip sits off the thumb's side
"""
import pathlib
import sys

import numpy as np
from pxr import Gf, Usd, UsdGeom, UsdSkel, Vt

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import hold  # noqa: E402

JOINTS = {"Root": (0, 0, 0), "Root/Hips": (0, 1, 0), "Root/Hips/Head": (0, 0.6, 0),
          "Root/Hips/LeftArm": (0.2, 0.4, 0), "Root/Hips/RightArm": (-0.2, 0.4, 0),
          "Root/Hips/RightArm/RightForeArm": (0, -0.28, 0),
          "Root/Hips/RightArm/RightForeArm/RightHand": (0, -0.26, 0)}
WRIST = np.array([-0.2, 0.86, 0.0])
HAND = (0.18, 0.09, 0.03)  # long (down), broad (front to back), thick (side to side)


def body(path):
    """A body as tools/characters lays one out, facing +z: its joints at JOINTS (locals), a `standing` clip holding
    them, and a right hand of HAND hanging from the wrist, skinned whole to RightHand."""
    stage = Usd.Stage.CreateNew(str(path))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    root = UsdSkel.Root.Define(stage, "/Character")
    UsdGeom.Xform.Define(stage, "/Character/Turned")
    skeleton = UsdSkel.Skeleton.Define(stage, hold.SKELETON)
    names = list(JOINTS)
    locals_ = [Gf.Matrix4d().SetTranslate(Gf.Vec3d(*JOINTS[name])) for name in names]
    worlds = {}
    for name, local in zip(names, locals_):
        parent = name.rsplit("/", 1)[0] if "/" in name else None
        worlds[name] = local * worlds[parent] if parent else local
    skeleton.CreateJointsAttr(names)
    skeleton.CreateRestTransformsAttr(locals_)
    skeleton.CreateBindTransformsAttr([worlds[name] for name in names])
    clip = UsdSkel.Animation.Define(stage, f"/Character/Animations/{hold.CLIP}")
    clip.CreateJointsAttr(names)
    clip.CreateTranslationsAttr(Vt.Vec3fArray([Gf.Vec3f(*JOINTS[name]) for name in names]))
    clip.CreateRotationsAttr(Vt.QuatfArray([Gf.Quatf(1)] * len(names)))
    clip.CreateScalesAttr(Vt.Vec3hArray([Gf.Vec3h(1)] * len(names)))
    grid = np.stack(np.meshgrid(np.linspace(-HAND[0], 0, 19), np.linspace(-HAND[1] / 2, HAND[1] / 2, 10),
                                np.linspace(-HAND[2] / 2, HAND[2] / 2, 4), indexing="ij"), -1).reshape(-1, 3)
    points = WRIST + grid[:, [2, 0, 1]]  # thick along x, long down y, broad along z
    UsdGeom.Scope.Define(stage, "/Character/Turned/Body")  # typed: UsdSkel skips a mesh under a typeless prim
    UsdGeom.Xform.Define(stage, "/Character/Turned/Body/work")
    mesh = UsdGeom.Mesh.Define(stage, "/Character/Turned/Body/work/hand")
    mesh.CreatePointsAttr(Vt.Vec3fArray.FromNumpy(points.astype(np.float32)))
    binding = UsdSkel.BindingAPI.Apply(mesh.GetPrim())
    binding.CreateSkeletonRel().SetTargets([skeleton.GetPath()])
    binding.CreateJointIndicesPrimvar(False, 1).Set(Vt.IntArray([names.index(name) for name in names
                                                                 if name.endswith("RightHand")] * len(points)))
    binding.CreateJointWeightsPrimvar(False, 1).Set(Vt.FloatArray([1.0] * len(points)))
    binding.CreateGeomBindTransformAttr(Gf.Matrix4d(1))
    UsdSkel.BindingAPI.Apply(root.GetPrim())
    stage.GetRootLayer().Save()
    return path


def test_the_smokers_hand_holds_the_cigarette_between_two_fingers(tmp_path):
    record = hold.pose(body(tmp_path / "body.usda"))
    asset = Usd.Stage.Open(str(tmp_path / "body.usda"))
    paths, locals_ = hold.clip_locals(asset)
    for joint, about in record["joints"].items():
        locals_[joint][:3, :3] = np.asarray(Gf.Matrix3d(Gf.Rotation(Gf.Quatd(*about["rotation"]))))
    world = {name.rsplit("/", 1)[-1]: matrix[3, :3] for name, matrix in hold.skel_space(paths, locals_).items()}
    upper = hold.unit(world["RightForeArm"] - world["RightArm"])
    lower = hold.unit(world["RightHand"] - world["RightForeArm"])
    forward, out = np.radians(hold.UPPER_FORWARD), np.radians(hold.UPPER_OUT)
    assert np.allclose(upper, [-np.sin(out) * np.cos(forward), -np.cos(out) * np.cos(forward), np.sin(forward)], atol=1e-6)
    assert np.isclose(np.degrees(np.arccos(upper @ lower)), hold.ELBOW, atol=0.1) and lower[2] > 0.9
    grip = (record["hold"]["translate"] + np.array([0.0, 0.0, hold.GRIP_Z]) @ np.asarray(
        Gf.Matrix3d(Gf.Rotation(Gf.Quatd(*record["hold"]["rotation"])))))
    assert np.allclose(grip, [0.0, -hold.GRIP_SHARE * HAND[0], HAND[1] / 4], atol=2e-3), grip  # in the hand's frame
    lit = np.array([0.0, 0.0, 1.0]) @ np.asarray(Gf.Matrix3d(Gf.Rotation(Gf.Quatd(*record["hold"]["rotation"]))))
    assert np.allclose(lit, [-1.0, 0.0, 0.0], atol=1e-6)  # the palm faces the body's middle (+x): the lit end out
