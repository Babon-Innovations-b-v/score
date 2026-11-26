"""A garment is sized to the body that wears it and stays where its pattern seats it: measure.py reads GarmentCode's
measurements off a body's own surface (girths at their levels, the arm's length and angle, the shoulders' width, the
neck's base) and carries the rest from GarmentCode's mean body by the girth each follows or by the height; seated.py
fails a garment sewn off centre, a shoulder seam sliding off its shoulder, a neckline dropping, the body standing out
through the cloth that covers it, cloth torn (part of it left behind as the body walks on, or hanging off the rest
from when it was sewn), or a garment under it out
through it (the toy torso worn as a garment under the tee), and passes one that sways with the body;
shaped.py gives a body another build (wider and taller as its
shape model and height say) and turns its arms out of a wider torso, the least it needs, refusing one past its most;
bands.py cuts a band out of a garment's cloth along its edges, a set height over its hem; details.py lays a garment's
construction marks on its cloth (a seam's mark on one panel's side and its other side's on the other, an edge's along
each open edge, a plain seam left bare, a patch at its anchor), each a hair's breadth outside the cloth's drawn face; inside/laying.py lays a box mesh's points that stand inside the
body out of it (in a thigh, and between two thighs that cross each other) and leaves one with no way out inside, for
the drape to refuse, moves trouser legs laid as GarmentCode lays them (wide of the legs) across over the legs, short of
the crotch's middle, and leaves a sleeve cap's sheet laid through a torso panel out of self contact against it;
inside/laying.py lifts the skin under sewn cloth to stand clear outside it (where an outer layer is sewn alone), two
thighs that face each other only to the middle between them, and leaves the bare skin; inside/laying.py rests a seam's triangle laid 15 times its panel as laid when sewing starts
and at its flat panel (as Newton's builder rests a triangle) when it ends, so float32 reads its area as the seam
closes, and a laid sliver at its flat panel throughout. Each row is a toy body of
tubes measured, and a toy tee (torso, shoulders, a collar band, sleeve panels between the side and shoulder seams)
worn on a toy torso one way, or the toy body reshaped or its arms cleared.

Breaks that turn it red (each applied once, seen red, reverted), in measure.py: a girth taken off another band than its
own (the bust's off the waist's levels, the hips' with the hands in the cut), a girth not the tape's (the cut's points
summed rather than its hull's perimeter), the wrist read off the upper arm, the arm's angle taken against the vertical,
the knee's girth read off the thigh's band or the calf's off the knee's, a length left in metres, the front's length over the bust left unread (carried by the height), an unread measurement
carried by the height where it follows a girth, or a read one overwritten by the mean body's. In seated.py: the side
seam taken for the shoulder seam (the lower chain), the neckline's fall read off its points at the clip's first frame
rather than their places on the moving skin, the body's outward normal not turning the cloth's (a covered point under
inward-wound cloth read as out), or a seam's place on the shoulder judged by its distance off the skin alone (a seam
slid down the arm's side in the turn, lying on the skin, read as seated); a garment under another judged by its winding
point by point or not at all (a garment wound inward read as through), against its sewn shape rather than its frames, or
never failed; torn edges never failed, or judged against the sewn cloth rather than the cut. In shaped.py: the arms turned in rather than out, an arm point read sunk
outside the torso, the
armpit's fold counted or every arm point left out, a shape's standard deviations not scaling its direction, the height
not set, or the joints left unscaled with the skin. In bands.py: the triangles taken whole by their middles (not cut on
the band's edges), or a cut's point made once per panel rather than once per seam point (the cloth opened along its
seams). In details.py: a seam taken for an open edge (two panels sharing box points not matched), a plain seam marked,
a strip laid outside its panel (its inward normal not turned), the lift not past the thickness on outward-wound cloth,
or a patch's side taken towards the body's middle, a dart (a panel sewn to itself) taken for an open edge, a "middle" patch's level read at the panel's top, a neck's rib stopped at its ends, or a neckline's edge at its unlabelled centre corner taken for a hem. In inside/laying.py: no point inside put out (each moved straight off
its nearest skin), no way out along the axes for a point the first step leaves inside, that step's points not looked
at again, or a point the layer's reach moves into a fold of the skin kept there; a seam's triangle rested at its flat
panel from the start (its float32 area ratio lost as the seam is crushed), a rest's corner 2 put the other way along
its first edge or its shape transposed (not Newton's), the share not reaching the flat panel, or a laid sliver kept as
its start; trouser legs not moved over the legs, moved the other way, or moved in past the crotch's gap; a crossing's points not left out against the triangle it passes through, its edge not against that
triangle's edges, or an edge sharing a corner with a triangle taken for one through it (cloth that crosses nothing
leaving its own neighbours out of self contact); a waistband's top worn where the skin is nearest it (off its level
on a body that narrows above the hips), its side seams' tops not held (the ring open at the seams), each point worn
where its own level way in meets the skin, spaced by count rather than by its cut, or run the other way round her (left
and right swapped), or a side seam closed by the point under its top; the skin an outer layer is sewn alone on not
past the cloth under it by its clear, moved in rather than out, or moved where no cloth lies, or lifted in full where two
thighs face (each through the other's, its room ahead not halved: seen red 2026-11-26). In inside/pattern.py: a waistband laid where
GarmentCode lays it rather than at the level it is cut for, moved up rather than down, its flat copies left behind its
points, or a garment with no worn top moved. In fabrics.py: a strip mark's pattern not a whole number of times in its
repeat (the rib's 1.6 mm ribs in 12 mm), or the denim's wear mottled across its tile."""
import json
import math
import pathlib

import numpy as np
import pytest

from tools.characters.garments import bands, details, fabrics, measure, seated, shaped
from tools.characters.garments.inside import laying

NAMES = ["Hips", "Spine2", "Chest", "Neck1", "LeftShoulder", "RightShoulder", "LeftArm", "RightArm", "LeftForeArm",
         "LeftHand", "RightForeArm", "RightHand", "LeftLeg", "LeftShin", "RightLeg", "RightShin", "LeftFoot",
         "RightFoot"]
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
    """A body of tubes, `scale` times the base size: a torso with a bust, a waist and hips, two legs (a thigh, a
    narrower knee, a calf and an ankle), two arms ARM down with a narrower wrist. Its measurements as built (cm and
    degrees)."""
    levels = np.linspace(0.80, 1.50, 57)
    profile = np.interp(levels, [0.80, 0.90, 0.97, 1.05, 1.25, 1.50], [0.13, 0.15, 0.12, 0.11, 0.14, 0.10])
    pieces = [tube([[0.0, level, 0.0] for level in levels], profile, [0, 1, 0],
                   lambda ring: "Hips" if levels[ring] < 1.0 else "Spine2" if levels[ring] < 1.15 else "Chest")]
    for side in (1.0, -1.0):
        prefix = "Left" if side > 0 else "Right"
        legs = np.linspace(0.0, 0.85, 35)
        legs_r = np.interp(legs, [0.0, 0.10, 0.32, 0.45, 0.60, 0.85], [0.03, 0.03, 0.05, 0.045, 0.06, 0.06])
        pieces.append(tube([[side * 0.07, level, 0.0] for level in legs], legs_r, [0, 1, 0],
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
              "LeftShin": (0.07, 0.45), "RightShin": (-0.07, 0.45), "LeftFoot": (0.07, 0.08),
              "RightFoot": (-0.07, 0.08)}
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
             "shoulder_w": 40.0, "arm_pose_angle": math.degrees(ARM), "waist_line": 45.0,
             # the front's profile from the waist (1.05 m, r 11 cm) over the bust (1.25, 14) to the neck (1.50, 10)
             "waist_over_bust_line": math.hypot(20.0, 3.0) + math.hypot(25.0, 4.0),
             "knee_circ": 2 * math.pi * 4.5, "knee_h": 45.0, "calf_circ": 2 * math.pi * 5.0, "calf_h": 32.0}
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
              "panel_names": np.asarray(names), "faces": copied, "flat": points[np.asarray(box)] * 100.0,
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
    if wear == "torn into a flap":
        # from the middle frame the left side's lower half left behind where it was, the rest walking on
        flap = np.flatnonzero((cloth[:, 0] > 0.0) & (cloth[:, 1] < (TOP - 0.15) * scale))
        cloths[later, flap] = sewn[flap] + moves[FRAMES // 2]
    if wear == "torn as it was sewn":
        # the left side's lower half sewn 10 cm low, hanging off the rest from the start and worn on with it
        flap = np.flatnonzero((cloth[:, 0] > 0.0) & (cloth[:, 1] < (TOP - 0.15) * scale))
        sewn[flap, 1] -= 0.1
        cloths = np.array([sewn + move for move in moves])
    if wear == "body out through the cloth":
        belly = np.flatnonzero((body[:, 1] > 0.2) & (body[:, 1] < 0.3) & (body[:, 2] > 0.1))
        bodies[later][:, belly] += np.stack([body[belly, 0], np.zeros(len(belly)), body[belly, 2]], axis=1) * (
            0.009 / TORSO)
    return sewn, cloths, bodies


PARENTS = [-1, 0, 1, 2, 2, 2, 4, 5, 6, 8, 7, 10, 0, 12, 0, 14, 13, 15]  # NAMES' parents


def widened(points, weights, share):
    """The toy body with its torso (Hips, Spine2, Chest) `share` times as wide and deep."""
    torso = np.isin(np.asarray(weights).argmax(axis=1), [NAMES.index(name) for name in ("Hips", "Spine2", "Chest")])
    found = np.array(points, dtype=float)
    found[torso] *= [share, 1.0, share]
    return found


def toy_clip(bind, inward):
    """Three frames of the toy body with both upper arms turned `inward` degrees further down than at the bind."""
    from scipy.spatial.transform import Rotation
    local = np.array([bind[joint] if parent < 0 else np.linalg.inv(bind[parent]) @ bind[joint]
                      for joint, parent in enumerate(PARENTS)])
    clip = np.repeat(local[None], 3, axis=0)
    for name, side in (("LeftArm", 1.0), ("RightArm", -1.0)):
        clip[:, NAMES.index(name), :3, :3] = Rotation.from_rotvec([0.0, 0.0, -side * math.radians(inward)]).as_matrix()
    return clip


def arms_turned_out(scale, wear):
    """shaped.arms_cleared on the toy body for a `wear` of ARMS: (torso widening, arms turned in) -> the degrees
    the arms are turned out, or None when they cannot be cleared."""
    points, faces, weights, bind, _ = toy_body(scale)
    share, inward = ARMS[wear]
    try:
        return shaped.arms_cleared(bind, widened(points, weights, share), faces, weights, NAMES, np.array(PARENTS),
                                   toy_clip(bind, inward))[3]
    except ValueError:
        return None


# Rows of shaped.py (a body given another build): the torso's widening and the arms' turn in on the clip.
ARMS = {"arms clear of a mean torso": (1.0, 25.0), "arms sunk in a wide torso": (1.6, 25.0),
        "arms sunk past the most turn": (2.0, 25.0)}


def toy_built(scale):
    """shaped.built on the toy body as its own shape model, one direction widening the torso a twentieth, given two
    standard deviations of it and a height of 1.8 m: (its torso girth over the toy's, its height in m)."""
    points, faces, weights, bind, _ = toy_body(scale)
    shapes = {"mean": points, "faces": faces, "directions": (widened(points, weights, 1.1) - points)[None] / 2.0}
    build = {"bind": bind, "source_points": points, "points": points, "weights": weights}
    found = shaped.built(build, weights, PARENTS, {"shape": {"0": 2.0}, "height_m": 1.8}, shapes)
    assert "points" not in found and "weights" not in found
    measured = measure.measured(found["source_points"], faces, weights, NAMES, found["bind"])
    girth = measured["waist"] / measure.measured(points, faces, weights, NAMES, bind)["waist"]
    return girth * float(scale) / (1.8 / (points[:, 1].max() - points[:, 1].min())), measured["height"] / 100.0


def taped(scale, width):
    """The toy tee's torso cut along a band `width` tall 3 cm over its hem (bands.cut): how far the band's triangles
    and the rest stray from their sides of its edges (m, 0 when the cut is clean), refused when the band's area is
    not its girth times its width or the cut opened the cloth."""
    record, cloth, _ = toy_tee()
    sewn = cloth * scale
    banded = bands.cut(record, sewn, {"width_m": width, "torso_m": [0.03], "sleeve_m": []})
    points = bands.frames_with(sewn[None], banded["made"], banded["weights"])[0]
    corners = points[banded["faces"]]
    above = corners[:, :, 1] - sewn[:, 1].min()
    within = np.minimum(above - 0.03, 0.03 + width - above)  # a corner's depth inside the band, negative out of it
    torso = above.max(axis=1) < TOP * scale - sewn[:, 1].min()  # the triangles under the shoulders' turn
    stray = max(0.0, -within[banded["banded"]].min(), within[~banded["banded"] & torso].max())
    areas = 0.5 * np.linalg.norm(np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0]), axis=1)
    girth = 2.0 * math.pi * (TORSO + CLOTH) * scale
    assert areas[banded["banded"]].sum() == pytest.approx(girth * width, rel=0.02)
    welded = np.asarray(record["box"])[record["faces"]]
    assert len(seated.open_edge_points(banded["faces"])) == len(seated.open_edge_points(welded))
    return stray


def toy_sheet():
    """Two 20 x 30 cm flat panels side by side on the plane z = 0.1 m (front, +z out), sharing their middle edge
    (x = 0) at the body's middle, as pattern.py records them: the right panel at -x, the left at +x."""
    grid = np.arange(0.0, 21.0, 2.0), np.arange(0.0, 31.0, 2.0)
    copies, flat, box, panel_of, faces, places = [], [], [], [], [], {}
    for number, sign in ((0, -1.0), (1, 1.0)):
        start = len(copies)
        for row, height in enumerate(grid[1]):
            for column, across in enumerate(grid[0]):
                key = (round(sign * across, 3), height)
                places.setdefault(key, len(places))
                copies.append([sign * across, height, 10.0])
                flat.append([sign * across, height])
                box.append(places[key])
                panel_of.append(number)
        width = len(grid[0])
        for row in range(len(grid[1]) - 1):
            for column in range(width - 1):
                corner = start + row * width + column
                quad = [corner, corner + 1, corner + width + 1, corner + width]
                if sign < 0:
                    quad = quad[::-1]
                faces += [[quad[0], quad[1], quad[2]], [quad[0], quad[2], quad[3]]]
    points = np.zeros((len(places), 3))
    for (across, height), index in places.items():
        points[index] = [across / 100.0, height / 100.0, 0.1]
    record = {"copies": np.asarray(copies), "flat": np.asarray(flat), "box": np.asarray(box),
              "panel": np.asarray(panel_of), "panel_names": np.asarray(["right", "left"]), "faces": np.asarray(faces)}
    return record, points


def necklines():
    """The toy sheet with the top edge's points from 2 to 18 cm out labelled a collar's, its corners not (as GarmentCode
    labels a tee's front neckline, its centre front corner left out): how many of each panel's open edges details.py
    takes for the neck."""
    record, _ = toy_sheet()
    box, flat = np.asarray(record["box"]), np.asarray(record["flat"])
    top = np.unique(box[(flat[:, 1] == 30.0) & (np.abs(flat[:, 0]) >= 2.0) & (np.abs(flat[:, 0]) <= 18.0)])
    record = {**record, "label/right_collar": top[top < 0], "label/left_collar": top}
    return [len(groups.get("neck", [])) for _, groups in sorted(details.classified(
        record, details.panel_edges(record)).items())]


def marked(library, plain):
    """The toy sheet's marks (a 6 mm seam mark, a 10 mm edge mark, a 4 x 2 cm patch 5 cm towards the left panel's
    side and 5 cm down from its top inner corner): each mark's triangle count, the farthest any point lies off the
    sheet less the lift, and the patch's middle (cm)."""
    record, points = toy_sheet()
    sizes = {"seam": [0.012, 0.006], "edge": [0.012, 0.010], "patch": [0.04, 0.02]}
    for name, size in sizes.items():
        own = pathlib.Path(library) / "surface" / name / "1"
        own.mkdir(parents=True, exist_ok=True)
        (own / "surface.json").write_text(json.dumps({"size_m": size}))
    surface = {name: {"name": name, "address": f"surface/{name}@1"} for name in sizes}
    garment = {"details": {"seam": surface["seam"], "edge": surface["edge"],
                           "plain seams": [["right", "left"]] if plain else [],
                           "patches": [{"mark": surface["patch"], "panel": "left", "anchor": "top-centre",
                                        "across_cm": 5.0, "down_cm": 5.0}]}}
    body = points - [0.0, 0.0, 0.1]
    made = details.laid(record, garment, library, points[None], body, 0.003)
    laid, triangles, _, finish, surfaces = made
    names = [known["name"] for known in surfaces]
    counts = {name: int((finish == index).sum()) for index, name in enumerate(names)}
    sheet = record["faces"][0]
    normal = np.cross(*(points[record["box"][sheet[1:]]] - points[record["box"][sheet[0]]]))
    lift = details.CLEAR_M + (0.003 if normal[2] > 0 else 0.0)
    off = float(np.abs(laid[0][:, 2] - 0.1 - lift).max())
    past = float(max(np.abs(laid[0][:, 0]).max() - 0.2, -laid[0][:, 1].min(), laid[0][:, 1].max() - 0.3)) * 100.0
    patch = laid[0][triangles[finish == names.index("patch")].ravel()]
    return counts, off, past, (patch[:, :2].min(axis=0) + patch[:, :2].max(axis=0)) / 2.0 * 100.0


def darted(library):
    """The toy sheet as one panel sewn to itself down its middle (a dart: GarmentCode shapes Pants' waist with them),
    a 6 mm seam mark and a 10 mm edge mark given and no dart mark: each mark's triangle count."""
    record, points = toy_sheet()
    record = {**record, "panel": np.ones_like(record["panel"])}
    for name, size in {"seam": [0.012, 0.006], "edge": [0.012, 0.010]}.items():
        own = pathlib.Path(library) / "surface" / name / "1"
        own.mkdir(parents=True, exist_ok=True)
        (own / "surface.json").write_text(json.dumps({"size_m": size}))
    garment = {"details": {name: {"name": name, "address": f"surface/{name}@1"} for name in ("seam", "edge")}}
    _, _, _, finish, surfaces = details.laid(record, garment, library, points[None], points - [0.0, 0.0, 0.1], 0.003)
    return {known["name"]: int((finish == index).sum()) for index, known in enumerate(surfaces)}


def neck_ends():
    """The toy sheet's left panel's top edge (0 to 20 cm) as a neckline's rib strip, 1.9 cm wide: its flat points'
    least and most x (cm)."""
    record, _ = toy_sheet()
    flat, panel_of = np.asarray(record["flat"]), np.asarray(record["panel"])
    copies = np.flatnonzero((panel_of == 1) & (flat[:, 1] == 30.0))
    copies = copies[np.argsort(flat[copies, 0])]
    points = details.strip(record, 1, copies, [0.012, 0.019], 0.012, details.NECK_OVERRUN_CM)[0]
    return [float(points[:, 0].min()), float(points[:, 0].max())]


def middle_patch():
    """The middle (cm) of a 4 x 2 cm patch laid on the toy sheet's left panel (20 cm wide) at its width's middle 10 cm
    under its top, 2 cm towards its side."""
    record, points = toy_sheet()
    spec = {"panel": "left", "anchor": "middle", "across_cm": 2.0, "down_cm": 10.0}
    _, flat_points, _, _ = details.patch(record, ["right", "left"], spec, [0.04, 0.02])
    return (flat_points.min(axis=0) + flat_points.max(axis=0)) / 2.0


def toy_thighs(apart=0.1):
    """Two closed thighs, 6 cm round and `apart` (m) between their axes, at 10 cm overlapping 2 cm between them (as a
    SOMA body's touching thighs cross each other): (points, faces)."""
    points, faces = [], []
    for side in (1.0, -1.0):
        levels = np.linspace(0.0, 0.8, 17)
        ring_points, ring_faces, _ = tube([[side * apart / 2.0, level, 0.0] for level in levels], [0.06] * len(levels),
                                          [0, 1, 0], lambda ring: "Hips")
        ends = [len(ring_points), len(ring_points) + 1]
        ring_points = np.concatenate([ring_points, [[side * 0.05, 0.0, 0.0], [side * 0.05, 0.8, 0.0]]])
        last = (len(levels) - 1) * SIDES
        caps = [[ends[0], (side_ + 1) % SIDES, side_] for side_ in range(SIDES)]
        caps += [[ends[1], last + side_, last + (side_ + 1) % SIDES] for side_ in range(SIDES)]
        faces.append(np.concatenate([ring_faces, caps]) + sum(len(each) for each in points))
        points.append(ring_points)
    return np.concatenate(points), np.concatenate(faces)


def pants_laid(clear):
    """Toy pants points as GarmentCode's box mesh may lay them on another body (one 3 cm deep in a thigh, as her tee's
    sleeve fronts in her arms; one in the overlap between the thighs, as her jeans' front crotch curve above her crotch,
    the skin nearest it the other thigh's; one outside) laid 6 mm out with `clear`: how many stay inside the body."""
    skin, faces = toy_thighs()

    def inside(points):
        return np.abs(laying.winding(points, skin, faces)) > laying.INSIDE
    points = np.array([[0.08, 0.5, 0.0], [0.0, 0.5, 0.0], [0.0, 0.5, 0.2]])
    assert inside(points).tolist() == [True, True, False]
    laid = laying.laid_out(points, skin, 0.006, clear, inside)
    nearest = skin[np.linalg.norm(skin - points[2], axis=1).argmin()]
    assert np.linalg.norm(laid[2] - nearest) == pytest.approx(np.linalg.norm(points[2] - nearest) + 0.006)
    return int(inside(laid).sum())


def skin_worn_under(clear):
    """A toy thigh's skin (`toy_thighs`' left one) worn by cloth sewn 1 cm off it from 20 to 40 cm up
    (`laying.worn_skin`, `clear` past it): each skin point's distance off its axis well inside the cloth's span and
    well outside it, and the most a point moved."""
    points, faces = toy_thighs()
    keep = np.flatnonzero(points[:, 0] > 0.0)
    skin, faces = points[keep], np.searchsorted(keep, faces[np.isin(faces, keep).all(axis=1)])
    ring = skin[(skin[:, 1] >= 0.2) & (skin[:, 1] <= 0.4)]
    cloth = ring + np.concatenate([(ring[:, [0, 2]] - [0.05, 0.0]) / 0.06 * 0.01, np.zeros((len(ring), 1))],
                                  axis=1)[:, [0, 2, 1]]
    worn = laying.worn_skin(skin, faces, cloth, clear)
    off = np.linalg.norm(worn[:, [0, 2]] - [0.05, 0.0], axis=1)
    side = np.linalg.norm(skin[:, [0, 2]] - [0.05, 0.0], axis=1) > 0.059
    covered = side & (skin[:, 1] > 0.25) & (skin[:, 1] < 0.35)
    bare = side & ((skin[:, 1] < 0.15) | (skin[:, 1] > 0.45))
    return off[covered], off[bare], float(np.linalg.norm(worn - skin, axis=1).max())


def skins_worn_facing(gap):
    """Two toy thighs `gap` (m) apart, each worn by cloth sewn 1 cm off it from 20 to 40 cm up with 5 mm clear past it
    (`laying.worn_skin`): how far the left thigh's lifted skin stands past the middle between them (towards the right
    thigh) and the lift on its outer side."""
    points, faces = toy_thighs(0.12 + gap)
    middles = np.where(points[:, 0] > 0.0, 0.06 + gap / 2.0, -0.06 - gap / 2.0)
    band = (points[:, 1] >= 0.2) & (points[:, 1] <= 0.4)
    ring = points[band]
    out = np.stack([ring[:, 0] - middles[band], np.zeros(len(ring)), ring[:, 2]], axis=1)
    cloth = ring + out / np.maximum(np.linalg.norm(out, axis=1, keepdims=True), 1e-9) * 0.01
    worn = laying.worn_skin(points, faces, cloth, 0.005)
    left = (points[:, 0] > 0.0) & (points[:, 1] > 0.25) & (points[:, 1] < 0.35)
    outer = left & (points[:, 0] > middles + 0.059)
    return float(-worn[left, 0].min()), float(np.median(worn[outer, 0] - points[outer, 0]))


def legs_laid(moved):
    """Toy trousers laid as GarmentCode lays them (each leg's front and back panels flat, 24 cm wide, from 6 cm off the
    crotch's middle outwards, a crotch point both legs hold) beside two toy legs 8 cm either side of the middle, 8 cm
    across, and `laying.over_legs` applied or not: (the share of each leg's width at its lowest level inside its laid
    cloth's, the least, the nearest a leg's point comes to the crotch's middle, the crotch point's move; m)."""
    columns, levels = np.linspace(0.06, 0.30, 13), np.arange(0.05, 0.76, 0.05)
    points, panel, names = [[0.0, 0.8, 0.0], [0.0, 0.8, 0.0]], [0, 2], ["pant_f_l", "pant_b_l", "pant_f_r", "pant_b_r"]
    for number, name in enumerate(names):
        side, depth = (1.0 if name.endswith("_l") else -1.0), (0.15 if "_f_" in name else -0.15)
        for level in levels:
            points.extend([side * column, level, depth] for column in columns)
            panel.extend([number] * len(columns))
    points = np.asarray(points)
    box = np.arange(len(points))
    box[1] = 0  # the crotch point held by the left and right front panels both
    record = {"panel_names": np.asarray(names), "box": box, "panel": np.asarray(panel)}
    turn = np.linspace(0.0, 2.0 * math.pi, 24, endpoint=False)
    skin = np.array([[side * 0.08 + 0.04 * math.cos(angle), level, 0.04 * math.sin(angle)]
                     for side in (1.0, -1.0) for level in np.arange(0.0, 0.8, 0.01) for angle in turn])
    legs, crotch = laying.leg_points(record)
    laid = points[np.unique(box)]
    index = {int(point): number for number, point in enumerate(np.unique(box))}
    legs = {side: np.array([index[int(point)] for point in mine]) for side, mine in legs.items()}
    crotch = np.array([index[int(point)] for point in crotch])
    after = laying.over_legs(laid, legs, crotch, skin) if moved else laid
    shares, nearest = [], []
    for side, mine in legs.items():
        low = mine[after[mine, 1] == after[mine, 1].min()]
        leg = skin[(np.abs(skin[:, 1] - 0.05) < 0.005) & (side * skin[:, 0] > 0.0), 0]
        inside = np.clip(leg, after[low, 0].min(), after[low, 0].max())
        shares.append(float(np.ptp(inside) / np.ptp(leg)))
        nearest.append(float(np.min(side * after[mine, 0])))
    return min(shares), min(nearest), float(np.linalg.norm(after[crotch] - laid[crotch]))


def builder_rest(corners):
    """Newton's builder's rest of triangles from their corners (add_triangles: the corners seen in the triangle's own
    frame, the first axis along corner 0 to 1): D's inverse per triangle."""
    first, second = corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0]
    along = first / np.linalg.norm(first, axis=1, keepdims=True)
    normal = np.cross(first, second)
    up = np.cross(normal / np.linalg.norm(normal, axis=1, keepdims=True), along)
    frame = np.stack([along, up], axis=2)
    return np.linalg.inv(np.matmul(frame.transpose(0, 2, 1), np.stack([first, second], axis=2)))


def area_ratio_error(corners, rest):
    """How far Newton's float32 J_s squared (the area ratio's square, (f0.f0)(f1.f1) - (f0.f1)^2 of the deformation
    gradient's columns) is off its float64 value for triangles at `corners` resting at `rest`, relative to it."""
    found = []
    for kind in (np.float32, np.float64):
        edges = np.stack([corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0]], axis=2).astype(kind)
        gradient = np.matmul(edges, rest.astype(kind))
        one, two = gradient[:, :, 0], gradient[:, :, 1]
        found.append(np.sum(one * one, axis=1) * np.sum(two * two, axis=1) - np.sum(one * two, axis=1) ** 2)
    return np.abs(found[0].astype(float) - found[1]) / found[1]


def seam_rested(wear):
    """A toy seam's triangle (a 1.3 cm panel triangle laid with its corner 1 20 cm across the body, as a back panel's
    triangle at a box mesh's shoulder) or a laid sliver, rested through its sewing (`laying.rest_lengths`): (the laid
    cloth's stretch at the start, its rest at the end against Newton's flat rest, float32's error on its area ratio
    with its corner 2 crushed to 0.4 mm along the long edge and 0.03 mm off it (woman_stair_modern's tee triangle 4609
    as it blew up) resting at the start and resting flat, the rest's area half way)."""
    flat = np.array([[[0.0, 0.0, 0.0], [0.013, 0.0, 0.0], [0.006, 0.011, 0.0]]])
    far = np.array([0.02, 0.2, 0.05])
    laid = np.array([[[0.0, 0.0, 0.0], far, [0.006, 0.011, 0.0]] if "seam" in wear
                     else [[0.0, 0.0, 0.0], [0.4, 0.0, 0.0], [0.2, 0.0001, 0.0]]])
    lengths = laying.edge_lengths(laid[0], [[0, 1, 2]]), laying.edge_lengths(flat[0], [[0, 1, 2]])
    start, _ = laying.rest_shapes(laying.rest_lengths(*lengths, 0.0))
    end, _ = laying.rest_shapes(laying.rest_lengths(*lengths, 1.0))
    _, half = laying.rest_shapes(laying.rest_lengths(*lengths, 0.5))
    gradient = np.matmul(np.stack([laid[:, 1] - laid[:, 0], laid[:, 2] - laid[:, 0]], axis=2), start)
    along = far / np.linalg.norm(far)
    off = np.cross(along, [1.0, 0.0, 0.0])
    crushed = laid.copy()
    crushed[0, 2] = 0.0004 * along + 0.00003 * off / np.linalg.norm(off)
    return (float(np.linalg.norm(gradient)), float(np.abs(end - builder_rest(flat)).max()),
            float(area_ratio_error(crushed, start)[0]), float(area_ratio_error(crushed, builder_rest(flat))[0]),
            float(half[0]))


def grid(columns, rows, corner, across, up):
    """A sheet of triangles: (columns + 1) x (rows + 1) points from `corner` along `across` and `up` (m a step)."""
    points = np.array([np.asarray(corner) + column * np.asarray(across) + row * np.asarray(up)
                       for row in range(rows + 1) for column in range(columns + 1)], dtype=float)
    faces = []
    for row in range(rows):
        for column in range(columns):
            here = row * (columns + 1) + column
            faces += [[here, here + 1, here + columns + 1], [here + 1, here + columns + 2, here + columns + 1]]
    return points, np.asarray(faces)


def sleeve_crossed(wear):
    """A toy torso panel (a 10 x 10 sheet of 1 cm triangles, bent as a back is round, so neighbouring triangles are not
    in one plane) and a sleeve cap's strip (3 mm wide, its edges 1 cm long) standing across it, poked through the
    middle of one of its triangles or a centimetre clear of it, as one cloth: its crossing filters
    (`laying.crossing_filters`, every edge a contact edge), the strip's edge through the torso, the torso triangles it
    may pass through and that edge's number."""
    torso, torso_faces = grid(10, 10, [0.0, 0.0, 0.0], [0.01, 0.0, 0.0], [0.0, 0.01, 0.0])
    torso[:, 2] = 2.0 * (torso[:, 0] - 0.05) ** 2
    sleeve, sleeve_faces = grid(1, 2, [0.0505, 0.052, -0.0105 if "through" in wear else 0.01],
                                [0.003, 0.0, 0.0], [0.0, 0.0, 0.01])
    points, triangles = np.concatenate([torso, sleeve]), np.concatenate([torso_faces, sleeve_faces + len(torso)])
    edges = laying.edges_of(triangles)
    points_to, edges_to = laying.crossing_filters(points, triangles, edges)
    # the strip's edge at x 5.05 cm from its second row (z -0.05 cm) to its third (z 0.95 cm) passes through the torso
    # between 5 and 6 cm, where no torso edge meets the strip
    lower, upper = len(torso) + 2, len(torso) + 4
    under = [number for number, face in enumerate(torso_faces)
             if (torso[face][:, :2] >= 0.0499).all() and (torso[face][:, :2] <= 0.0601).all()]
    crossing = int(np.flatnonzero((edges == sorted((lower, upper))).all(axis=1))[0])
    return points_to, edges_to, (lower, upper), under, crossing


def toy_band():
    """A toy waistband's box mesh as pattern.py records it: a front panel (+z) and a back panel, each 9 columns by 2
    rows, sewn at the side seams by their end columns' shared points, laid as GarmentCode's box mesh lays them (flat
    panels 8 cm off the toy body at 0.3 m high, the seams' points at the sides) and cut 6 cm a column at the front, 9
    at the back; `lower_interface` labels each panel's top edge without its seam corners, as GarmentCode does.
    (record, laid points in m)."""
    across = np.linspace(-0.2, 0.2, 9)
    laid = []
    for height in (0.3, 0.28):
        laid += [[-0.26, height, 0.0]] + [[x, height, 0.31] for x in across[1:-1]] + [[0.26, height, 0.0]]
    for height in (0.3, 0.28):
        laid += [[x, height, -0.31] for x in across[1:-1]]
    box, panel, copies, faces = [], [], [], []
    for number, step in enumerate((6.0, 9.0)):
        start = len(box)
        for row in range(2):
            for column in range(9):
                seam = column in (0, 8)
                box.append(row * 9 + column if number == 0 or seam else 18 + row * 7 + column - 1)
                panel.append(number)
                copies.append([column * step, -row * 2.0, 0.0])
        for column in range(8):
            here, below = start + column, start + 9 + column
            faces += [[here, below, here + 1], [here + 1, below, below + 1]]
    box = np.asarray(box)
    top = box[[number * 18 + column for number in range(2) for column in range(1, 8)]]
    record = {"box": box, "panel": np.asarray(panel), "faces": np.asarray(faces), "copies": np.asarray(copies),
              "label/lower_interface": top}
    return record, np.asarray(laid)


WIDER = 1.3  # the toy waist's x over its z


def waistband_worn():
    """The toy band's top ring (`toy_band`) worn by `laying.top_ring` and `laying.worn_places` on a body whose waist is
    WIDER across than deep and whose hips widen 4 cm in each 10 cm down: how many points the ring holds, each place's
    height off its point's level and its distance off the skin at that level (m, the most of each), the most and
    least of the worn edges' lengths over their cut lengths, and how many places stand on the other side (left or right,
    front or back) from their points as laid."""
    profile = [(0.15 + 0.4 * (0.5 - height), height) for height in np.arange(0.0, 0.81, 0.01)]
    profile = [(max(radius, 0.12), height) for radius, height in profile]
    skin, faces = revolved(profile, 96, 0.0)
    skin[:, 0] *= WIDER
    record, laid = toy_band()
    order, cut = laying.top_ring(record, ["lower_interface"], 0.01)
    ring = laid[order]
    triangles, weights = laying.worn_places(ring, cut, skin, faces)
    worn = np.sum(skin[faces[triangles]] * weights[:, :, None], axis=1)
    radius = 0.15 + 0.4 * (0.5 - 0.3)
    stretch = np.linalg.norm(np.roll(worn, -1, axis=0) - worn, axis=1) / cut
    sided = np.abs(ring[:, [0, 2]]) > 1e-9
    return (len(order), float(np.abs(worn[:, 1] - ring[:, 1]).max()),
            float(np.abs(np.hypot(worn[:, 0] / WIDER, worn[:, 2]) - radius).max()),
            float(stretch.max()), float(stretch.min()),
            int(np.sum(sided & (np.sign(worn[:, [0, 2]]) != np.sign(ring[:, [0, 2]])))))


def band_lowered(top):
    """The toy waistband's box mesh (cm) laid by pattern.py at the level `top` its top is cut for: (its worn top's
    levels, each point's and each copy's move, cm), and a tee's record (no worn top) and the band with no cut level
    left as laid (True)."""
    from tools.characters.garments.inside import pattern
    record, laid = toy_band()
    record = {**record, "points": laid * 100.0, "copies": np.asarray(record["copies"], dtype=float) + [0.0, 30.0, 0.0]}
    lowered = pattern.lowered_to_cut(record, top)
    ring = lowered["points"][record["label/lower_interface"], 1]
    moves = np.concatenate([lowered[key] - record[key] for key in ("points", "copies")])
    tee = {key: value for key, value in record.items() if key != "label/lower_interface"}
    kept = all(np.array_equal(pattern.lowered_to_cut(given, cut)[key], given[key])
               for given, cut in ((tee, top), (record, None)) for key in ("points", "copies"))
    return ring, moves, kept


def fabric_repeats():
    """How cleanly the drawn fabrics repeat: the strip marks' rows whose step across the repeat (last column to first)
    is bigger than any step inside them, and the denim tile's colour blurred over a centimetre, its spread over its
    mean (a blotch larger than the threads repeating every tile)."""
    from scipy.ndimage import uniform_filter
    broken = 0
    for title, drawn, _, _, form in fabrics.MARKS.values():
        if form != "strip":
            continue
        rgba = drawn().maps()[0].astype(float)
        inside = np.abs(np.diff(rgba, axis=1)).max(axis=(1, 2))
        broken += int(np.sum(np.abs(rgba[:, 0] - rgba[:, -1]).max(axis=1) > inside + 1e-9))
    size = fabrics.TILE_PX // 2  # four pixels a thread: the threads still drawn, the tile drawn in a quarter the time
    colour = fabrics.denim_maps(size=size)[0].mean(axis=-1)
    blurred = uniform_filter(colour, size=int(round(0.01 / fabrics.TILE_M * size)), mode="wrap")
    return broken, float(blurred.std() / colour.mean())


@pytest.mark.parametrize("scale, wear, failed", [
    (1.0, "seated", []),
    (1.15, "seated", []),
    (1.0, "a seam moved under its limit", []),
    (1.0, "sewn off centre", ["off centre"]),
    (1.0, "slid off the left shoulder", ["left shoulder seam"]),
    (1.15, "slid down the left arm in the turn", ["body through cloth", "left shoulder seam", "torn",
                                                  "under through over"]),
    (1.0, "neckline dropped", ["neckline drop"]),
    (1.0, "torn into a flap", ["body through cloth", "torn", "under through over"]),
    (1.0, "torn as it was sewn", ["torn"]),
    (1.0, "body out through the cloth", ["body through cloth", "under through over"]),
    (1.0, "arms clear of a mean torso", 0.0),
    (1.0, "arms sunk in a wide torso", 14.0),
    (1.0, "arms sunk past the most turn", None),
    (1.0, "built a tenth wider and 1.8 m tall", (1.1, 1.8)),
    (1.0, "a band round the torso", 0.05),
    (1.15, "a band round the torso", 0.05),
    (1.0, "marks on a seam, its edges and a pocket", False),
    (1.0, "marks with the seam plain", True),
    (1.0, "a patch at its panel's middle, at its level", [12.0, 20.0]),
    (1.0, "a neck's rib run on past its ends", [-0.8, 20.8]),
    (1.0, "a dart's sides left unmarked", {"edge": 2 * 2 * (20 * 2 + 30) * 2}),
    (1.0, "a neckline's marks run to its centre seam", [10, 10]),
    (1.0, "pants laid round thighs that touch", 0),
    (1.0, "pants laid with too short a way out", 1),
    (1.0, "trouser legs laid over the legs", True),
    (1.0, "trouser legs laid as GarmentCode lays them", False),
    (1.0, "a seam's triangle laid across the body", "rests as laid"),
    (1.0, "a sliver laid", "rests flat"),
    (1.0, "a sleeve cap laid through its torso", True),
    (1.0, "a sleeve cap laid clear of its torso", False),
    (1.0, "a waistband's top worn at its level", 0.0),
    (1.0, "a skin worn under the cloth sewn on it", 0.005),
    (1.0, "skins worn where two thighs face", 0.02),
    (1.0, "a waistband laid at the level it is cut for", 25.0),
    (1.0, "fabrics drawn to repeat cleanly", 0.05),
])
def test_a_garment_is_sized_to_and_stays_on_the_body_that_wears_it(scale, wear, failed, tmp_path):
    points, faces, weights, bind, built = toy_body(scale)
    found = {**measure.measured(points, faces, weights, NAMES, bind),
             **measure.below_knee(points, faces, weights, NAMES, bind)}
    for key, value in built.items():
        # a girth is a SIDES-gon's perimeter (0.07% under its circle's); a level is read to the scan's step
        tolerance = 0.01 * value if key in ("bust", "waist", "hips", "leg_circ", "wrist", "knee_circ",
                                            "calf_circ") else 1.5
        assert found[key] == pytest.approx(value, abs=tolerance), key
    mean = {"height": 166.0, "bust": 97.0, "underbust": 81.0, "back_width": 46.0, "hip_inclination": 12.7,
            "armscye_depth": 12.6, "arm_length": 51.6, "waist": 80.0, "hips": 104.0}
    sized = measure.sized(mean, found)
    assert sized["underbust"] == pytest.approx(81.0 * found["bust"] / 97.0, rel=1e-3)
    assert sized["armscye_depth"] == pytest.approx(12.6 * found["height"] / 166.0, rel=1e-3)
    assert sized["hip_inclination"] == 12.7
    assert sized["arm_length"] == pytest.approx(found["arm_length"], rel=1e-3)
    if wear in ARMS:
        assert arms_turned_out(scale, wear) == failed
        return
    if wear.startswith("built"):
        assert toy_built(scale) == pytest.approx(failed, abs=0.01)
        return
    if wear.startswith("a band"):
        assert taped(scale, failed) == pytest.approx(0.0, abs=1e-9)
        return
    if wear.startswith("trouser legs"):
        share, nearest, crotch = legs_laid(failed)
        # moved over the legs, each leg's width lies inside its laid cloth's at the hem, no leg point nearer the
        # crotch's middle than the gap, the crotch seam where it was laid; as GarmentCode lays them, a quarter out
        assert (share == pytest.approx(1.0)) == failed, share
        assert nearest >= laying.CROTCH_GAP_M - 1e-9 and crotch == 0.0, (nearest, crotch)
        return
    if wear.startswith("a skin worn"):
        # the skin under the cloth stands its clear outside it (the 48-gon's sides 0.1% inside its circle), out along
        # its own normal; the bare skin is where it was
        covered, bare, most = skin_worn_under(failed)
        assert covered == pytest.approx(0.07 + failed, abs=0.0005), covered
        assert bare == pytest.approx(0.06, abs=1e-9) and most < 0.01 + failed + 0.0005, (bare, most)
        return
    if wear.startswith("skins worn"):
        # each thigh's skin facing the other lifted half the gap, the two meeting in the middle, not through each other;
        # its outer side lifted the cloth's centimetre and the clear
        past, outer = skins_worn_facing(failed)
        assert past <= 1e-3 and outer == pytest.approx(0.015, abs=0.0005), (past, outer)
        return
    if wear.startswith("pants"):
        # the drape refuses a garment with a point left inside the body, never sews it
        assert pants_laid(0.001 if "too short" in wear else 0.0045) == failed
        return
    if wear.startswith(("a seam's", "a sliver")):
        stretch, off_newton, area_error, flat_error, half_area = seam_rested(wear)
        # at the start the laid cloth is at its rest (a deformation gradient a rotation: its norm the square root of
        # two), where at its flat panel it stood 18 times stretched; at the end the rest is Newton's own flat one
        if failed == "rests as laid":
            assert stretch == pytest.approx(math.sqrt(2.0), abs=1e-6)
            # resting flat, float32 loses the crushed triangle's area ratio whole (the blow-up); resting as laid not
            assert flat_error > 0.5 and area_error < 0.01, (flat_error, area_error)
        else:
            assert stretch > 20.0, stretch
        assert off_newton == pytest.approx(0.0, abs=1e-6) and half_area > 0.0
        return
    if wear.startswith("fabrics"):
        # every strip mark runs on across its repeat; the denim's shade varies under 5% over a centimetre (its 3 cm
        # wear clouds, 10%, read as an acid wash tiled every 10 cm, #225 round 9)
        broken, blotches = fabric_repeats()
        assert broken == 0 and blotches < failed, (broken, blotches)
        return
    if wear.startswith("a waistband laid"):
        # the top ring at its cut level (laid at 30 cm), every point and every flat copy moved down alike by the 5 cm
        ring, moves, kept = band_lowered(failed)
        assert ring == pytest.approx(failed, abs=1e-9) and kept, (ring, kept)
        assert moves == pytest.approx(np.tile([0.0, failed - 30.0, 0.0], (len(moves), 1)), abs=1e-9), moves
        return
    if wear.startswith("a waistband"):
        # the ring closed by both side seams' tops (14 labelled, 16 held), worn on the skin at its own level (the
        # 96-sided ring's chords at most 0.2 mm in), each edge stretched alike round her (but for its chords' 2% across
        # the waist's turns), every point on its own side
        held, level, off, most, least, swapped = waistband_worn()
        assert held == 16 and level == pytest.approx(failed, abs=1e-9) and off < 0.0005, (held, level, off)
        assert most / least < 1.02 and swapped == 0, (most, least, swapped)
        return
    if wear.startswith("a sleeve cap"):
        points_to, edges_to, (lower, upper), under, crossing = sleeve_crossed(wear)
        if failed:
            # the crossing edge's points are left out against the torso triangle it passes through, and the edge
            # against that triangle's edges both ways
            assert all(under[0] in points_to.get(point, set()) or under[1] in points_to.get(point, set())
                       for point in (lower, upper)), points_to
            assert crossing in edges_to and all(crossing in edges_to[other] for other in edges_to[crossing])
        else:
            # cloth that crosses nothing (its own triangles sharing corners never counted) leaves nothing out
            assert points_to == {} and edges_to == {}, (points_to, edges_to)
        return
    if wear.startswith("a neck's rib"):
        # the rib runs on past the neckline's ends so two halves meeting at an angle leave no wedge between them
        assert neck_ends() == pytest.approx(failed, abs=1e-6)
        return
    if wear.startswith("a patch at"):
        # a knee's fading wherever the leg narrows: the middle of the panel's width at the patch's level
        assert middle_patch() == pytest.approx(failed, abs=1e-6)
        return
    if wear.startswith("a dart"):
        # the sheet's outer edge marked all round (140 cm, a strip every 0.5 cm), its middle (a dart, a panel sewn
        # to itself) neither a seam nor a hem
        assert darted(tmp_path) == failed
        return
    if wear.startswith("a neckline"):
        # each panel's ten top edges are the neck's, those at its unlabelled corners too, and no side edge
        assert necklines() == failed
        return
    if wear.startswith("marks"):
        counts, off, past, middle = marked(tmp_path, failed)
        # the seam's 30 cm, a strip a side every 0.5 cm: 60 quads a side; each panel's three open edges 70 cm
        assert counts.get("seam", 0) == (0 if failed else 2 * 60 * 2), counts
        assert counts["edge"] == 2 * 2 * (20 * 2 + 30) * 2 and counts["patch"] == 4 * 2 * 2, counts
        assert off == pytest.approx(0.0, abs=1e-6) and past < 1e-6, (off, past)
        assert middle == pytest.approx([5.0, 25.0], abs=1e-6)
        return
    torso, torso_faces = toy_torso()
    record, cloth, cloth_faces = toy_tee()
    sewn, cloths, bodies = worn(wear, torso * scale, cloth * scale, record, scale)
    seating = seated.measured({"record": record, "sewn": sewn, "worn": cloths, "faces": cloth_faces},
                              {"bind": torso * scale, "faces": torso_faces, "frames": bodies})
    assert seating["body points covered"] > 1000, seating
    lines = seated.faults(seating)
    # the torso worn as a garment under the tee, its triangles wound inward (as a GarmentCode panel may be), turned
    # out by the body inside it
    under = {"sewn": torso * scale, "worn": bodies, "faces": torso_faces[:, ::-1]}
    lines += seated.layer_faults("under", "over", seated.layered(
        under, {"sewn": sewn, "worn": cloths, "faces": cloth_faces}, torso * scale * [0.9, 0.95, 0.9]))
    assert sorted(kind for kind in ["off centre", "left shoulder seam", "right shoulder seam", "neckline drop",
                                    "body through cloth", "under through over", "torn"]
                  if any(kind in line for line in lines)) == failed, lines
