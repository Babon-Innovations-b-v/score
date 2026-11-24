"""A garment is sized to the body that wears it and stays where its pattern seats it: measure.py reads GarmentCode's
measurements off a body's own surface (girths at their levels, the arm's length and angle, the shoulders' width, the
neck's base) and carries the rest from GarmentCode's mean body by the girth each follows or by the height; seated.py
fails a garment sewn off centre, a shoulder seam sliding off its shoulder, a neckline dropping, or the body standing
out through the cloth that covers it, and passes one that sways with the body. Each row is a toy body of tubes
measured, and a toy tee (torso, shoulders, a collar band, sleeve panels between the side and shoulder seams) worn on
a toy torso one way.

Breaks that turn it red (each applied once, seen red, reverted), in measure.py: a girth taken off another band than its
own (the bust's off the waist's levels, the hips' with the hands in the cut), a girth not the tape's (the cut's points
summed rather than its hull's perimeter), the wrist read off the upper arm, the arm's angle taken against the vertical,
a length left in metres, an unread measurement carried by the height where it follows a girth, or a read one overwritten
by the mean body's. In seated.py: the side seam taken for the shoulder seam (the lower chain), the neckline's fall read
off its points at the clip's first frame rather than their places on the moving skin, the body's outward normal not
turning the cloth's (a covered point under inward-wound cloth read as out), or a seam's place on the shoulder judged by
its distance off the skin alone (a seam slid down the arm's side in the turn, lying on the skin, read as seated)."""
import math

import numpy as np
import pytest

from tools.characters.garments import measure, seated

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


def revolved(profile, sides, turn):
    """A surface of revolution round y of (radius, height) rings, `sides` points a ring starting `turn` radians
    round, its triangles wound outward."""
    angles = turn + np.linspace(0.0, 2.0 * math.pi, sides, endpoint=False)
    points = np.concatenate([np.stack([radius * np.cos(angles), np.full(sides, height), radius * np.sin(angles)],
                                      axis=1) for radius, height in profile])
    faces = []
    for ring in range(len(profile) - 1):
        for side in range(sides):
            here, there = ring * sides + side, ring * sides + (side + 1) % sides
            faces += [[here, here + sides, there], [there, here + sides, there + sides]]
    return points, np.asarray(faces)


TORSO, NECK, CLOTH = 0.15, 0.06, 0.005  # m: the toy torso's and neck's radii, the cloth's distance off them
TOP, ARMHOLE = 0.5, 0.40  # m: the shoulders' height, the sleeve panels' lowest


def toy_torso():
    """A torso tube up to its shoulders, its shoulders closing in to a neck tube: 64 points a ring."""
    profile = ([(TORSO, height) for height in np.arange(0.0, TOP, 0.01)]
               + [(radius, TOP) for radius in np.arange(TORSO, NECK, -0.01)]
               + [(NECK, height) for height in np.arange(TOP, 0.62, 0.01)])
    return revolved(profile, 64, math.pi / 64.0)


def toy_tee():
    """A tee CLOTH off the toy torso, as pattern.py records a garment: its torso over the shoulders in four panels
    (left at +x, front at +z), a sleeve panel each side from ARMHOLE up, a collar band up the neck whose top ring
    is the neckline. (record, points, welded faces)."""
    top = TOP + CLOTH
    profile = ([(TORSO + CLOTH, height) for height in np.arange(0.105, top, 0.02)] + [(TORSO + CLOTH, top)]
               + [(radius, top) for radius in np.arange(TORSO + CLOTH - 0.02, NECK + CLOTH, -0.02)]
               + [(NECK + CLOTH, top)] + [(NECK + CLOTH, height) for height in (0.525, 0.545, 0.565)])
    points, faces = revolved(profile, 32, 0.0)
    faces = faces[:, ::-1]  # wound inward, as a GarmentCode panel may be
    middle = points[faces].mean(axis=1)
    names = ["right_btorso", "right_ftorso", "left_btorso", "left_ftorso", "right_sleeve", "left_sleeve", "collar"]
    panel = 2 * (middle[:, 0] > 0) + (middle[:, 2] > 0)
    sleeve = (middle[:, 1] > ARMHOLE) & (middle[:, 1] < top) & (np.abs(middle[:, 2]) < 0.05)
    panel[sleeve] = 4 + (middle[sleeve, 0] > 0)
    panel[middle[:, 1] > top + 0.001] = 6
    copies, box, panel_of, copied = [], [], [], np.zeros_like(faces)
    for number in range(len(names)):
        mine = np.flatnonzero(panel == number)
        used = np.unique(faces[mine])
        local = {int(point): len(box) + index for index, point in enumerate(used)}
        copied[mine] = np.vectorize(local.get)(faces[mine])
        box.extend(used)
        panel_of.extend([number] * len(used))
    neckline = np.flatnonzero(np.isclose(points[:, 1], 0.565))
    record = {"points": points * 100.0, "box": np.asarray(box), "panel": np.asarray(panel_of),
              "panel_names": np.asarray(names), "faces": copied,
              "label/right_collar": neckline[points[neckline, 0] <= 0.0],
              "label/left_collar": neckline[points[neckline, 0] > 0.0]}
    return record, points, faces


FRAMES = 6


def worn(wear, body, cloth, record, scale):
    """The toy tee's sewn points and the torso and tee over FRAMES frames as `wear` wears them: both swaying and
    walking forward and down a stair together, and from the middle frame on what the wear breaks."""
    sewn = cloth.copy()
    shoulders = np.isclose(cloth[:, 1], (TOP + CLOTH) * scale) & np.isclose(cloth[:, 2], 0.0, atol=1e-9)
    seams = {"left": np.flatnonzero(shoulders & (cloth[:, 0] > 0.0))}
    if wear == "sewn off centre":
        sewn[seams["left"], 0] += 0.04  # the seams' middle 2 cm to the left
    moves = [np.array([0.02 * math.sin(frame), -0.08 * frame / FRAMES, 0.03 * frame]) for frame in range(FRAMES)]
    bodies, cloths = np.array([body + move for move in moves]), np.array([sewn + move for move in moves])
    later = slice(FRAMES // 2, None)
    if wear == "slid off the left shoulder":
        cloths[later, seams["left"], 0] += 0.04
    if wear == "slid down the left arm in the turn":
        # from frame 0 on the torso's side under the shoulder, a centimetre apart down it
        down = np.array([[TORSO + CLOTH, TOP - 0.03 - 0.01 * rank, 0.0] for rank in range(len(seams["left"]))])
        cloths[:, seams["left"]] = (down[None] + np.array(moves)[:, None]) * scale
    if wear == "a seam moved under its limit":
        cloths[later, seams["left"], 0] += 0.015
    if wear == "neckline dropped":
        for height, drop in ((0.565, 0.03), (0.545, 0.015)):
            ring = np.flatnonzero(np.isclose(cloth[:, 1], height))
            cloths[later, ring, 1] -= drop
    if wear == "body out through the cloth":
        belly = np.flatnonzero((body[:, 1] > 0.2) & (body[:, 1] < 0.3) & (body[:, 2] > 0.1))
        bodies[later][:, belly] += np.stack([body[belly, 0], np.zeros(len(belly)), body[belly, 2]], axis=1) * (
            0.009 / TORSO)
    return sewn, cloths, bodies


@pytest.mark.parametrize("scale, wear, failed", [
    (1.0, "seated", []),
    (1.15, "seated", []),
    (1.0, "a seam moved under its limit", []),
    (1.0, "sewn off centre", ["off centre"]),
    (1.0, "slid off the left shoulder", ["left shoulder seam"]),
    (1.15, "slid down the left arm in the turn", ["body through cloth", "left shoulder seam"]),
    (1.0, "neckline dropped", ["neckline drop"]),
    (1.0, "body out through the cloth", ["body through cloth"]),
])
def test_a_garment_is_sized_to_and_stays_on_the_body_that_wears_it(scale, wear, failed):
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
    torso, torso_faces = toy_torso()
    record, cloth, cloth_faces = toy_tee()
    sewn, cloths, bodies = worn(wear, torso * scale, cloth * scale, record, scale)
    seating = seated.measured({"record": record, "sewn": sewn, "worn": cloths, "faces": cloth_faces},
                              {"bind": torso * scale, "faces": torso_faces, "frames": bodies})
    assert seating["body points covered"] > 1000, seating
    lines = seated.faults(seating)
    assert sorted(kind for kind in ["off centre", "left shoulder seam", "right shoulder seam", "neckline drop",
                                    "body through cloth"] if any(kind in line for line in lines)) == failed, lines
