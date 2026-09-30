"""Where a place measured on the take C crewman's body lands on this person's body (#112).

The crew's parts were first placed on one body, take C's, and many of their numbers are places on
it: the collar's lowest front, the pocket, the yokes, the chest box, the brows. A person of another
build keeps every one of those decisions, moved onto their own body by their own skeleton:

- a height is moved piecewise between the joints up the body (floor, ankle, knee, hip, the spine,
  the neck, the eyes, the top of the head), so the pocket stays the same share of the way from the
  belt to the collar;
- a width on the torso is scaled by the shoulders above the chest and by the hips below the
  hips, blended between;
- a place on the head is moved with the eyes: its offset from the eyes' middle scaled by how far
  apart the eyes are (across and deep) and by the eyes-to-crown height (up).

The person's joints come from `joints.json` in the look (every joint of the body model at the bind
pose, the eyes too, which the shipped skeleton drops); take C's are the table below. With no
`joints.json`, every place is take C's own, so the crew build is unchanged.
"""
import json

import numpy as np
from paths import LOOK

# Take C's joints at the bind pose, metres (look/identity.npz, 2026-09-29).
TAKE_C = {
    "LeftFoot": (0.157, 0.072, -0.101), "LeftShin": (0.130, 0.484, -0.003),
    "LeftLeg": (0.100, 0.915, -0.027), "Hips": (0.0, 0.998, -0.049),
    "Spine1": (0.0, 1.049, -0.050), "Spine2": (0.0, 1.121, -0.051), "Chest": (0.0, 1.194, -0.058),
    "Neck1": (0.0, 1.457, -0.059), "Neck2": (0.0, 1.532, -0.035), "Head": (0.0, 1.596, -0.016),
    "LeftEye": (0.031, 1.649, 0.060), "HeadEnd": (0.0, 1.757, -0.035),
    "LeftArm": (0.161, 1.401, -0.063), "LeftForeArm": (0.342, 1.176, -0.051),
    "LeftHand": (0.530, 1.020, 0.064),
}
UP_THE_BODY = ("LeftFoot", "LeftShin", "LeftLeg", "Hips", "Spine1", "Spine2", "Chest", "Neck1",
               "Neck2", "Head", "LeftEye", "HeadEnd")


def _joints():
    path = LOOK / "joints.json"
    if not path.exists():
        return {name: np.array(place) for name, place in TAKE_C.items()}
    read = json.loads(path.read_text())
    return {name: np.array(read[name]) for name in TAKE_C}


THEIRS = _joints()
OURS = {name: np.array(place) for name, place in TAKE_C.items()}


def y(height):
    """A height on take C's body, on this body."""
    ours = np.array([0.0] + [OURS[name][1] for name in UP_THE_BODY])
    theirs = np.array([0.0] + [THEIRS[name][1] for name in UP_THE_BODY])
    height = np.asarray(height, dtype=float)
    inside = np.interp(height, ours, theirs)
    above = theirs[-1] + (height - ours[-1]) * (theirs[-1] - theirs[-2]) / (ours[-1] - ours[-2])
    return np.where(height > ours[-1], above, inside)


def width_share(height):
    """How much wider this torso is than take C's at a height on take C's body."""
    shoulders = THEIRS["LeftArm"][0] / OURS["LeftArm"][0]
    hips = THEIRS["LeftLeg"][0] / OURS["LeftLeg"][0]
    blend = np.clip((np.asarray(height, float) - OURS["Hips"][1])
                    / (OURS["Chest"][1] - OURS["Hips"][1]), 0.0, 1.0)
    return hips + (shoulders - hips) * blend


def x(across, height):
    """A place across the torso on take C's body, at a height on take C's body, on this body."""
    return np.asarray(across, float) * width_share(height)


def xy(across, height):
    return float(x(across, height)), float(y(height))


def arm_share():
    """How much longer this upper arm is than take C's."""
    return (np.linalg.norm(THEIRS["LeftForeArm"] - THEIRS["LeftArm"])
            / np.linalg.norm(OURS["LeftForeArm"] - OURS["LeftArm"]))


def leg_share():
    """How much longer this leg (hip to ankle) is than take C's."""
    return (THEIRS["LeftLeg"][1] - THEIRS["LeftFoot"][1]) / (OURS["LeftLeg"][1] - OURS["LeftFoot"][1])


def _eyes_middle(joints):
    return np.array([0.0, joints["LeftEye"][1], joints["LeftEye"][2]])


def head_scale():
    across = THEIRS["LeftEye"][0] / OURS["LeftEye"][0]
    up = (THEIRS["HeadEnd"][1] - THEIRS["LeftEye"][1]) / (OURS["HeadEnd"][1] - OURS["LeftEye"][1])
    return np.array([across, up, across])


def head(point):
    """A place on take C's head, on this head."""
    point = np.asarray(point, dtype=float)
    return _eyes_middle(THEIRS) + (point - _eyes_middle(OURS)) * head_scale()


def head_xy(points):
    """Front-view (x, y) places on take C's head, on this head."""
    points = np.asarray(points, dtype=float)
    full = np.column_stack([points[:, 0], points[:, 1], np.full(len(points), OURS["LeftEye"][2])])
    return head(full)[:, :2]


def neck_z(depth):
    """A depth near take C's neck, on this neck (moved with the upper neck joint)."""
    return depth + THEIRS["Neck2"][2] - OURS["Neck2"][2]


def eye(side):
    """This body's eye joint, (x, y, z); side +1 is the left."""
    left = THEIRS["LeftEye"]
    return np.array([left[0] * side, left[1], left[2]])
