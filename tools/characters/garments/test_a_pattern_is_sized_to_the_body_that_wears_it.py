"""A garment's pattern is sized to the body that wears it: measure.py reads GarmentCode's measurements off a body's own
surface (girths at their levels, the arm's length and angle, the shoulders' width, the neck's base) and carries the
rest from GarmentCode's mean body by the girth each follows or by the height.

Breaks that turn it red: a girth taken off another band than its own (the bust's off the waist's levels, the hips'
with the hands in the cut), a girth not the tape's (the cut's points summed rather than its hull's perimeter), the
wrist read off the upper arm, the arm's angle taken against the vertical, a length left in metres, an unread
measurement carried by the height where it follows a girth, or a read one overwritten by the mean body's.
"""
import math

import numpy as np
import pytest

from tools.characters.garments import measure

NAMES = ["Hips", "Spine2", "Chest", "Neck1", "LeftShoulder", "RightShoulder", "LeftArm", "RightArm", "LeftForeArm",
         "LeftHand", "RightForeArm", "RightHand", "LeftLeg", "LeftShin", "RightLeg", "RightShin"]
SIDES = 48
ARM = math.radians(50.0)  # the arms' angle under the horizontal (not 45: its sine and cosine would agree)


def tube(centres, radii, axis, joint_of):
    """A ring of SIDES points round each centre (normal `axis`), joined ring to ring; each ring's joint."""
    axis = np.asarray(axis, dtype=float) / np.linalg.norm(axis)
    first = np.cross(axis, [0.0, 0.0, 1.0] if abs(axis[2]) < 0.9 else [1.0, 0.0, 0.0])
    first /= np.linalg.norm(first)
    second = np.cross(axis, first)
    angles = np.linspace(0.0, 2.0 * math.pi, SIDES, endpoint=False)
    points = np.concatenate([np.asarray(centre) + radius * (np.cos(angles)[:, None] * first + np.sin(angles)[:, None]
                                                            * second) for centre, radius in zip(centres, radii)])
    faces = []
    for ring in range(len(centres) - 1):
        for side in range(SIDES):
            here, there = ring * SIDES + side, ring * SIDES + (side + 1) % SIDES
            faces += [[here, there, here + SIDES], [there, there + SIDES, here + SIDES]]
    joints = np.repeat([joint_of(ring) for ring in range(len(centres))], SIDES)
    return points, np.asarray(faces), joints


def toy_body(scale):
    """A body of tubes, `scale` times the base size: a torso with a bust, a waist and hips, two legs, two arms ARM
    down with a narrower wrist. Its measurements as built (cm and degrees)."""
    levels = np.linspace(0.80, 1.50, 57)
    profile = np.interp(levels, [0.80, 0.90, 0.97, 1.05, 1.25, 1.50], [0.13, 0.15, 0.12, 0.11, 0.14, 0.10])
    pieces = [tube([[0.0, level, 0.0] for level in levels], profile, [0, 1, 0],
                   lambda ring: "Hips" if levels[ring] < 1.0 else "Spine2" if levels[ring] < 1.15 else "Chest")]
    for side in (1.0, -1.0):
        prefix = "Left" if side > 0 else "Right"
        legs = np.linspace(0.0, 0.85, 35)
        pieces.append(tube([[side * 0.07, level, 0.0] for level in legs], [0.06] * len(legs), [0, 1, 0],
                           lambda ring, p=prefix, l=legs: f"{p}Leg" if l[ring] > 0.45 else f"{p}Shin"))
        direction = np.array([side * math.cos(ARM), -math.sin(ARM), 0.0])
        shares = np.linspace(0.0, 1.0, 41)
        radii = [0.025 if 0.75 <= share <= 0.97 else 0.04 for share in shares]
        pieces.append(tube([np.array([side * 0.2, 1.4, 0.0]) + direction * 0.5 * share for share in shares], radii,
                           direction, lambda ring, p=prefix, s=shares: f"{p}Arm" if s[ring] < 0.5 else f"{p}ForeArm"))
    points, faces, joints, offset = [], [], [], 0
    for piece_points, piece_faces, piece_joints in pieces:
        points.append(piece_points)
        faces.append(piece_faces + offset)
        joints.append(piece_joints)
        offset += len(piece_points)
    joints = np.concatenate(joints)
    weights = np.zeros((len(joints), len(NAMES)))
    weights[np.arange(len(joints)), [NAMES.index(name) for name in joints]] = 1.0
    places = {"Hips": (0, 0.95), "Spine2": (0, 1.10), "Chest": (0, 1.20), "Neck1": (0, 1.45),
              "LeftShoulder": (0.1, 1.42),
              "RightShoulder": (-0.1, 1.42), "LeftLeg": (0.07, 0.85), "RightLeg": (-0.07, 0.85),
              "LeftShin": (0.07, 0.45), "RightShin": (-0.07, 0.45)}
    bind = np.tile(np.eye(4), (len(NAMES), 1, 1))
    for name, (x, y) in places.items():
        bind[NAMES.index(name), :2, 3] = x, y
    for side, prefix in ((1.0, "Left"), (-1.0, "Right")):
        direction = np.array([side * math.cos(ARM), -math.sin(ARM), 0.0])
        for name, share in (("Arm", 0.0), ("ForeArm", 0.5), ("Hand", 1.0)):
            bind[NAMES.index(prefix + name), :3, 3] = np.array([side * 0.2, 1.4, 0.0]) + direction * 0.5 * share
    bind[:, :3, 3] *= scale
    built = {"height": 150.0, "head_l": 0.0, "bust": 2 * math.pi * 14.0, "waist": 2 * math.pi * 11.0,
             "hips": 2 * math.pi * 15.0, "leg_circ": 2 * math.pi * 6.0, "wrist": 2 * math.pi * 2.5, "arm_length": 50.0,
             "shoulder_w": 40.0, "arm_pose_angle": math.degrees(ARM), "waist_line": 45.0}
    built = {key: value * (scale if key != "arm_pose_angle" else 1.0) for key, value in built.items()}
    return np.concatenate(points) * scale, np.concatenate(faces), weights, bind, built


@pytest.mark.parametrize("scale", [1.0, 1.15])
def test_a_pattern_is_sized_to_the_body_that_wears_it(scale):
    points, faces, weights, bind, built = toy_body(scale)
    found = measure.measured(points, faces, weights, NAMES, bind)
    for key, value in built.items():
        # a girth is a SIDES-gon's perimeter (0.07% under its circle's); a level is read to the scan's step
        tolerance = 0.01 * value if key in ("bust", "waist", "hips", "leg_circ", "wrist") else 1.5
        assert found[key] == pytest.approx(value, abs=tolerance), key
    mean = {"height": 166.0, "bust": 97.0, "underbust": 81.0, "back_width": 46.0, "hip_inclination": 12.7,
            "armscye_depth": 12.6, "arm_length": 51.6, "waist": 80.0, "hips": 104.0}
    sized = measure.sized(mean, found)
    assert sized["underbust"] == pytest.approx(81.0 * found["bust"] / 97.0, rel=1e-3)
    assert sized["armscye_depth"] == pytest.approx(12.6 * found["height"] / 166.0, rel=1e-3)
    assert sized["hip_inclination"] == 12.7
    assert sized["arm_length"] == pytest.approx(found["arm_length"], rel=1e-3)
