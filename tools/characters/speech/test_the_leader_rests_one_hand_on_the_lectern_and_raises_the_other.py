"""Invariant: the leader's speaking pose (speech.py), solved on a body facing +z, aims each upper arm its angles
forward and out (away from the body's middle) of straight down and bends each forearm its elbow toward the front:
the left forearm about level, forward onto the lectern, the right raised in front of the chest; the clip's other
joints are left as they are.

Breaks that turn it red:
- speech.arm_set: the out turn's sign the same on both sides -> the left arm crosses in front of the body
- speech.arm_set: the elbow bent the other way (-elbow) -> a forearm points back
- speech.pose: the right arm set with LEFT's angles -> the right hand is not raised
"""
import pathlib
import sys

import numpy as np
import pytest
from pxr import Gf, Usd, UsdGeom, UsdSkel, Vt

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import speech  # noqa: E402

HOLD = speech.hold_module()
JOINTS = {"Root": (0, 0, 0), "Root/Hips": (0, 1, 0), "Root/Hips/Head": (0, 0.6, 0),
          "Root/Hips/LeftArm": (0.2, 0.4, 0), "Root/Hips/RightArm": (-0.2, 0.4, 0),
          "Root/Hips/LeftArm/LeftForeArm": (0, -0.28, 0), "Root/Hips/LeftArm/LeftForeArm/LeftHand": (0, -0.26, 0),
          "Root/Hips/RightArm/RightForeArm": (0, -0.28, 0),
          "Root/Hips/RightArm/RightForeArm/RightHand": (0, -0.26, 0)}


def body(path):
    """A skeleton as tools/characters lays one out, facing +z (its right on -x), its joints at JOINTS (locals) and a
    `standing` clip holding them."""
    stage = Usd.Stage.CreateNew(str(path))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    UsdSkel.Root.Define(stage, "/Character")
    UsdGeom.Xform.Define(stage, "/Character/Turned")
    skeleton = UsdSkel.Skeleton.Define(stage, HOLD.SKELETON)
    names = list(JOINTS)
    skeleton.CreateJointsAttr(names)
    skeleton.CreateRestTransformsAttr([Gf.Matrix4d().SetTranslate(Gf.Vec3d(*JOINTS[name])) for name in names])
    clip = UsdSkel.Animation.Define(stage, f"/Character/Animations/{HOLD.CLIP}")
    clip.CreateJointsAttr(names)
    clip.CreateTranslationsAttr(Vt.Vec3fArray([Gf.Vec3f(*JOINTS[name]) for name in names]))
    clip.CreateRotationsAttr(Vt.QuatfArray([Gf.Quatf(1)] * len(names)))
    clip.CreateScalesAttr(Vt.Vec3hArray([Gf.Vec3h(1)] * len(names)))
    stage.GetRootLayer().Save()
    return path


@pytest.mark.parametrize("side, angles, outward", [("Left", speech.LEFT, 1.0), ("Right", speech.RIGHT, -1.0)])
def test_the_leader_rests_one_hand_on_the_lectern_and_raises_the_other(tmp_path, side, angles, outward):
    record = speech.pose(body(tmp_path / "body.usda"))
    paths, locals_ = HOLD.clip_locals(Usd.Stage.Open(str(tmp_path / "body.usda")))
    assert sorted(record["joints"]) == sorted(HOLD.named(paths, f"{each}{joint}") for each in ("Left", "Right")
                                              for joint in ("Arm", "ForeArm"))
    for joint, about in record["joints"].items():
        locals_[joint][:3, :3] = np.asarray(Gf.Matrix3d(Gf.Rotation(Gf.Quatd(*about["rotation"]))))
    world = {name.rsplit("/", 1)[-1]: matrix[3, :3] for name, matrix in HOLD.skel_space(paths, locals_).items()}
    upper = HOLD.unit(world[f"{side}ForeArm"] - world[f"{side}Arm"])
    lower = HOLD.unit(world[f"{side}Hand"] - world[f"{side}ForeArm"])
    forward, out = np.radians(angles[0]), np.radians(angles[1])
    assert np.allclose(upper, [outward * np.sin(out) * np.cos(forward), -np.cos(out) * np.cos(forward),
                               np.sin(forward)], atol=1e-6)
    assert np.isclose(np.degrees(np.arccos(upper @ lower)), angles[2], atol=0.1) and lower[2] > 0.6
    raised = world[f"{side}Hand"][1] - world[f"{side}Arm"][1]  # metres from the shoulder up to the wrist
    assert (-0.3 < raised < -0.15) if side == "Left" else (-0.1 < raised < 0.05), raised
