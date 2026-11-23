"""The 2099 prologue's leader speaking at the square's lectern (2099 #161), solved in code on a people body as a
score_lib pose: both arms' joint rotations over the body's `standing` clip at its start.

    .venv/bin/python tools/characters/speech/speech.py <character.usdc> <out folder>

Writes <out>/pose.json: `joints` {joint path: {"rotation": [w, x, y, z]}}, the local rotations of LeftArm,
LeftForeArm, RightArm and RightForeArm that replace the clip's (CLIP, SECOND), and `angles`, the ones it was solved at;
place_build's `hold` lays it on a laid character (no `hold` frame: nothing is held).

The pose: the left forearm rests forward on the lectern's top (the upper arm LEFT[0] forward and LEFT[1] out of
straight down, the elbow bent LEFT[2] toward the front), the right hand is raised in front of the chest, open, as a
speaker's beat (RIGHT, the same three). Every angle is the builder's own: no source read gives a speaker's arms. The
arm geometry (aiming a bone, the body's frame) is the smoker's hold's (tools/props/smoke_beat/hold/hold.py), loaded
by its file.
"""
import importlib.util
import json
import pathlib
import sys

import numpy as np
from pxr import Usd

HOLD = pathlib.Path(__file__).resolve().parents[2] / "props/smoke_beat/hold/hold.py"
LEFT = (25.0, 12.0, 70.0)  # degrees: forward, out, elbow (the forearm 5 degrees over level, onto the lectern's top)
RIGHT = (35.0, 25.0, 100.0)  # degrees: the hand raised to the chest, the forearm 45 degrees over level


def hold_module():
    """The smoker's hold (its arm geometry), loaded by its file."""
    spec = importlib.util.spec_from_file_location("hold", HOLD)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def arm_set(hold, paths, locals_, side, angles):
    """`locals_` with the `side` ("Left" or "Right") arm's upper arm `angles`[0] forward and [1] out of straight
    down and its forearm bent [2] from it toward the front."""
    forward_angle, out_angle, elbow = angles
    up, forward, right = hold.frame_of(paths, hold.skel_space(paths, locals_))
    out_turn = -out_angle if side == "Right" else out_angle  # out, away from the body's middle, on either side
    upper = hold.unit(-up @ hold.turned(forward_angle, right) @ hold.turned(out_turn, forward))
    lower = hold.unit(upper @ hold.turned(elbow, hold.unit(np.cross(upper, forward))))
    arm, forearm, hand = (hold.named(paths, f"{side}{joint}") for joint in ("Arm", "ForeArm", "Hand"))
    posed = hold.aimed(paths, locals_, arm, forearm, upper)
    return hold.aimed(paths, posed, forearm, hand, lower)


def pose(asset_path):
    """The pose record of the body at `asset_path`."""
    hold = hold_module()
    paths, locals_ = hold.clip_locals(Usd.Stage.Open(str(asset_path)))
    posed = arm_set(hold, paths, arm_set(hold, paths, locals_, "Left", LEFT), "Right", RIGHT)
    joints = [hold.named(paths, f"{side}{joint}") for side in ("Left", "Right") for joint in ("Arm", "ForeArm")]
    return {"clip": hold.CLIP, "second": hold.SECOND,
            "joints": {path: {"rotation": hold.quaternion(posed[path])} for path in joints},
            "angles": {"left": dict(zip(("forward", "out", "elbow"), LEFT)),
                       "right": dict(zip(("forward", "out", "elbow"), RIGHT))}}


def main():
    asset, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    record = pose(asset)
    (out / "pose.json").write_text(json.dumps(record, indent=1))
    print(f"pose.json: {len(record['joints'])} joints -> {out}")


if __name__ == "__main__":
    main()
