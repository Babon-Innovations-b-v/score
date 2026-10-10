"""How well a drape hangs, in numbers that can be set beside another simulator's drape of the same pattern on the same
body: the trouser hem's height, how crumpled the cloth is, how far the legs balloon off the body, how the space suit
sits at the waist and how much cloth the people tools' belt finds.

    ~/.farm-factory-props/env/bin/python tools/characters/maker/drape_measure.py <drape folder> <body obj, cm> \
        <look folder> [--reference <drape folder>] [--json out.json]

The drape folder holds <kind>_<n>_sim.obj (centimetres) and its _sim_segmentation.txt, as GarmentCode's and the
maker's drapes both do; the look folder is the person's (its joints.json places the belt band through
tools/characters/people/fit.py, as space_suit.py places it). Numpy and scipy only, seconds on any machine.

- hem_cm: the lowest trouser point of each leg above the floor (the body's lowest point), the mean of the two legs.
- crumple_deg: the mean bend between neighbouring cloth triangles, in degrees, over the whole garment (the same
  pattern at the same spacing bends the same where it hangs smoothly; crumples raise it).
- balloon_cm: the mean distance from the trouser cloth to the body between the ankle and the knee.
- waist_crumple_deg: crumple_deg in the band from the hips to the lowest ribs (where a gathered waist shows).
- torso_low_m, belt_band_m, belt_cloth_cm: the torso panels' lowest point, the belt band space_suit.py cuts
  (fit.y(1.005) to fit.y(1.062)) and how much of that band's height the torso cloth covers; null when the torso
  cloth does not reach the band (no belt band to read: the work suit, whose torso ends at its waistband above it).
- self_crossings: how many cloth edges pass through a cloth triangle they share no corner with (cloth through cloth).
- silhouette (with --reference, another simulator's drape of the same pattern on the same body; the look's
  joints.json places the cuts): what the eye reads as a bloated chest, a sleeve ballooning off the arm or no waist,
  which the numbers above miss (2026-10-10). The cloth and the body are cut at places fixed by the joints and the
  body: chest, underbust, waist (the body's narrowest girth between the hips and the chest), belly (between the
  Spine1 and Spine2 joints, a few centimetres lower), low belly (halfway from there to the hips) and hip level; upper
  arm, elbow, forearm and cuff square to the arm's bone; thigh, knee and shin square to the leg's. Per cut, both
  sides pooled: the cloth's and the body's width (across: the front view's silhouette), depth (front to back: the
  side view's) and girth (a tape measure's, round the convex outline), and the stand-off (the cloth's outline radius
  minus the body's in 72 directions round the bone or the spine), median and 90th percentile, cm. Each region is
  pass, fail (the width or a stand-off larger than the reference's by more than TOLERANCE_CM, chosen from the Warp
  drapes' own spread, or the reference has cloth round the cut and the drape has not: a sleeve ridden up short of the
  cuff) or unknown (neither drape read there, or the body's cut not read).
- dense: the same numbers and verdict at every dense cut (`dense_cuts`): the torso every centimetre from the hips to
  the shoulders, the shoulder (the cloth with its sleeves' caps) every centimetre from the armpit to the shoulders,
  each arm every 5 % of its bones and at the elbow; a cut neither drape's cloth goes round is 'absent'. `bands` sums
  them per band: the cuts failed or unknown and the largest margin over the tolerance.
- silhouette_gate: the verdict over GATE_REGIONS (the torso and the arms, where the owner saw the bloat) and every
  dense cut: fail when any fails, unknown when none fails and any is unknown, else pass.
- belt: the belt band against the reference's (`judge_belt`): unknown when the reference has no belt band to read.
- verdict: the worst of silhouette_gate and belt; only pass lets a drape through (unknown blocks as fail does).
"""
import argparse
import importlib
import json
import os
import pathlib
import sys

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import ConvexHull, QhullError, cKDTree

import sewing

PEOPLE = pathlib.Path(__file__).resolve().parents[1] / "people"
# The belt band space_suit.py cuts from the torso, in take C's heights (moved onto the person by fit.y).
BELT_BAND = (1.005, 1.062)
# The waist band where gathers are counted, in take C's heights: from the hips to the lowest ribs.
WAIST_BAND = (0.95, 1.12)


def read_obj(path):
    """Points (metres) and triangles of an obj written in centimetres."""
    points, faces = sewing.read_obj(path)
    return points / 100.0, faces


def drape_files(folder):
    """The cloth obj and its segmentation in a drape folder."""
    folder = pathlib.Path(folder)
    cloth = next(folder.glob("*_sim.obj"))
    return cloth, cloth.with_name(cloth.name.replace("_sim.obj", "_sim_segmentation.txt"))


def panel_labels(segmentation):
    """Each point's panel name; a point on a seam keeps the first stitch it names."""
    return np.array([line.split(",")[0] for line in pathlib.Path(segmentation).read_text().split("\n") if line.strip()])


def face_normals(points, faces):
    """Each triangle's unit normal."""
    normals = np.cross(points[faces[:, 1]] - points[faces[:, 0]], points[faces[:, 2]] - points[faces[:, 0]])
    return normals / np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-12)


def edge_bends(points, faces):
    """For every edge two triangles share: the bend between them in degrees, and the edge's middle height."""
    edges = np.sort(faces[:, [[0, 1], [1, 2], [2, 0]]].reshape(-1, 2), axis=1)
    owner = np.repeat(np.arange(len(faces)), 3)
    order = np.lexsort((edges[:, 1], edges[:, 0]))
    edges, owner = edges[order], owner[order]
    shared = np.all(edges[1:] == edges[:-1], axis=1)
    first, second = owner[:-1][shared], owner[1:][shared]
    normals = face_normals(points, faces)
    cosine = np.clip(np.sum(normals[first] * normals[second], axis=1), -1.0, 1.0)
    middle = points[edges[:-1][shared]].mean(axis=1)
    return np.degrees(np.arccos(cosine)), middle[:, 1]


def leg_mask(labels):
    """The trouser points (legs and cuffs)."""
    return np.char.startswith(labels, "pant")


def hem_height(points, labels, floor):
    """The mean over both legs of each leg's lowest trouser point above the floor, in metres."""
    lows = []
    for side in ("l", "r"):
        leg = np.array([label.startswith("pant") and (label.endswith(f"_{side}") or f"_{side}_" in label)
                        for label in labels])
        if leg.any():
            lows.append(points[leg, 1].min() - floor)
    return float(np.mean(lows)) if lows else None


def balloon(points, labels, body_tree, low, high):
    """The mean distance from the trouser points between two heights to the nearest body point, in metres."""
    keep = leg_mask(labels) & (points[:, 1] > low) & (points[:, 1] < high)
    if not keep.any():
        return None
    return float(body_tree.query(points[keep])[0].mean())


def fit_module(look):
    """tools/characters/people/fit.py reading this look's joints."""
    os.environ["MOTION_LOOK"] = str(pathlib.Path(look).resolve())
    sys.path.insert(0, str(PEOPLE))
    for name in ("paths", "fit"):
        sys.modules.pop(name, None)
    return importlib.import_module("fit")


def belt_numbers(points, labels, fit):
    """The torso's lowest point, the belt band and the band height the torso cloth covers, in metres."""
    torso = np.char.find(labels, "torso") >= 0
    if not torso.any():
        return {}
    low = float(points[torso, 1].min())
    bottom, top = float(fit.y(BELT_BAND[0])), float(fit.y(BELT_BAND[1]))
    return {"torso_low_m": round(low, 4), "belt_band_m": [round(bottom, 4), round(top, 4)],
            "belt_cloth_cm": belt_cover(low, bottom, top)}


def belt_cover(low, bottom, top):
    """How much of the belt band's height (cm) cloth reaching down to `low` covers; None when it does not reach the
    band: there is no belt band to read (the work suit's torso ends above it, at its waistband), which a 0.0 hid
    (drapes-fix round-5 recheck: every work suit, Warp's and Newton's, read 0.0, so the number tested nothing)."""
    if low >= top:
        return None
    return round(100.0 * (top - max(bottom, low)), 2)


def measure(folder, body_obj, look):
    """Every number of the module's header for one drape."""
    cloth, segmentation = drape_files(folder)
    points, faces = read_obj(cloth)
    labels = panel_labels(segmentation)
    body_points, _ = read_obj(body_obj)
    floor = float(body_points[:, 1].min())
    fit = fit_module(look)
    joints = json.loads((pathlib.Path(look) / "joints.json").read_text())
    knee = np.mean([joints["LeftShin"][1], joints["RightShin"][1]])
    ankle = np.mean([joints["LeftFoot"][1], joints["RightFoot"][1]])
    bends, heights = edge_bends(points, faces)
    waist = (heights > fit.y(WAIST_BAND[0])) & (heights < fit.y(WAIST_BAND[1]))
    result = {"drape": str(cloth), "points": int(len(points)),
              "crumple_deg": round(float(bends.mean()), 3),
              "waist_crumple_deg": round(float(bends[waist].mean()), 3) if waist.any() else None}
    hem = hem_height(points, labels, floor)
    if hem is not None:
        result["hem_cm"] = round(100.0 * hem, 2)
        leg_balloon = balloon(points, labels, cKDTree(body_points), ankle + 0.05, knee)
        result["balloon_cm"] = round(100.0 * leg_balloon, 2) if leg_balloon is not None else None
    result.update(belt_numbers(points, labels, fit))
    result["self_crossings"] = self_crossings(points, faces)
    return result


# --- silhouette: the cloth's outline round the body at fixed cuts, against a reference drape ---

ANGLES = np.radians(np.arange(0.0, 360.0, 5.0))
UP = np.array([0.0, 1.0, 0.0])
TORSO_REGIONS = ("chest", "underbust", "waist", "belly", "low_belly", "hip")
ARM_REGIONS = ("upper_arm", "elbow", "forearm", "cuff")
LEG_REGIONS = ("thigh", "knee", "shin")
REGIONS = TORSO_REGIONS + ARM_REGIONS + LEG_REGIONS
# The regions a drape must pass (`gate`): the whole torso and the whole sleeve, where the owner saw the bloat (a
# bloated chest and underbust, no waist, sleeves ballooning off the arm; 2026-10-10). The low belly and the hip are
# gated too since drapes-fix round 4: without them the 15 cm between the belly cut and the hips, where the space
# suit's waist seam and belt sit, went unjudged, and a puffy lower belly would have passed (round-3 recheck). The legs
# are read and judged but not gated: the Newton trousers hang at full gravity where Warp's hung at a hundredth of it.
GATE_REGIONS = ("chest", "underbust", "waist", "belly", "low_belly", "hip", "upper_arm", "elbow", "forearm", "cuff")
# The gate also reads the dense cuts (`dense_cuts`): the named cuts are 6 to 9 cm apart, and a drape tuned until they
# passed still bulged between them (drapes-fix round-5 recheck: a belly pouch 0.7 cm over the tolerance between the
# low-belly and hip cuts, an underbust 2 cm too wide 2 mm from the underbust cut, nothing cut from the armpit to the
# shoulder). The torso and the shoulder every TORSO_STEP_CM, each arm bone every ARM_STEP of its length.
TORSO_STEP_CM = 1.0
ARM_STEP = 0.05
# The upper arm is cut from UPPER_ARM_FROM of the bone down (nearer the shoulder a cut square to the bone cuts the
# torso, and the shoulder band reads there; on the player's body it still does at 30 %, one 53 cm loop round torso
# and arm, so `dense_cuts` drops any arm cut whose body chain takes in the spine), the forearm from FOREARM_FROM past the elbow (nearer, the cut meets the
# upper sleeve; the elbow cut reads there); both to ARM_TO (the hand starts past it).
UPPER_ARM_FROM, FOREARM_FROM, ARM_TO = 0.3, 0.1, 0.95
# The natural waist is looked for between the hip joints and the Chest joint, every WAIST_STEP_CM.
WAIST_STEP_CM = 0.5
# Cloth cut further than this from a limb's bone (cm) belongs to another part of the garment.
LIMB_REACH_CM = {"arm": 22.0, "leg": 30.0}
# The share of directions round the bone a cut must cover (go round) to be read at all.
COVER = 0.9
# The tolerance over the reference (cm) for each number the verdict judges, from the Warp drapes' own spread
# (2026-10-10): on 48 approved Warp drapes on 14 bodies, the 90th percentile, rounded up to a millimetre, of the
# difference between a drape's left and right at the same cut (a near-mirrored pattern on a near-mirrored body: what
# the simulator leaves to chance; Warp itself repeats a drape exactly). Limbs: the left limb's cut against the
# right's; the torso: its right half against its left (width as each half's stand-off sideways). Measured again with
# the low-belly cut in drapes-fix round 4 (267 torso halves): the torso's width came to 1.50 (1.51 before). On the
# dense cuts of the same 48 drapes (2026-10-10: 2,079 torso halves, 1,303 arm pairs without the arm cuts that take in
# the spine) the spread is no larger (torso 1.30, 0.38, 0.54; arm 0.67, 0.29, 0.43), so the torso's and the arm's tolerances stay the named cuts'. The shoulder
# is measured on its own dense cuts (392 halves: 0.61, 0.24, 0.62), as the sleeve's cap is in its cloth.
TOLERANCE_CM = {"torso": {"cloth_width": 1.5, "standoff_median": 0.5, "standoff_p90": 0.7},
                "shoulder": {"cloth_width": 0.7, "standoff_median": 0.3, "standoff_p90": 0.7},
                "arm": {"cloth_width": 0.8, "standoff_median": 0.4, "standoff_p90": 0.5},
                "leg": {"cloth_width": 1.0, "standoff_median": 0.5, "standoff_p90": 0.7}}
# How much less of the belt band (cm) the drape's torso cloth may cover than the reference's, from the same 48 Warp
# drapes: the 90th percentile, rounded up to a millimetre, of the difference between the band height the left torso
# panels cover and the right's, on the 24 that read a band (2026-10-10: 0.31).
BELT_TOLERANCE_CM = 0.4


def limb_of(region):
    """'torso', 'arm' or 'leg'."""
    return "torso" if region in TORSO_REGIONS else "arm" if region in ARM_REGIONS else "leg"


def point_kinds(labels):
    """Each point's part: 0 torso and the rest, 1 sleeve, 2 trousers."""
    sleeve = (np.char.find(labels, "sleeve") >= 0) | np.char.startswith(labels, "sl_")
    return np.where(sleeve, 1, np.where(np.char.startswith(labels, "pant"), 2, 0))


def panel_of_each_point(segmentation, points):
    """Each point's panel: the first name on its line that is not a stitch, else the nearest such point's."""
    lines = [line for line in pathlib.Path(segmentation).read_text().split("\n") if line.strip()]
    labels = np.array([next((name for name in line.split(",") if not name.startswith("stitch")), "")
                       for line in lines])
    blank = labels == ""
    if blank.any() and (~blank).any():
        labels[blank] = labels[~blank][cKDTree(points[~blank]).query(points[blank])[1]]
    return labels


def unit(vector):
    return vector / np.linalg.norm(vector)


def spine_point(joints, height):
    """The spine's point at a height (Hips to Neck1, straight between joints)."""
    chain = np.array([joints[name] for name in ("Hips", "Spine1", "Spine2", "Chest", "Neck1")])
    return np.array([np.interp(height, chain[:, 1], chain[:, 0]), height, np.interp(height, chain[:, 1], chain[:, 2])])


def natural_waist(body, joints):
    """The height of the body's narrowest girth (round the spine) between the hip joints and the Chest joint: where a
    tape measures the waist; the Spine joints sit several centimetres under it (5 to 9 cm on Nev, Ama and the
    player)."""
    hip = (joints["LeftLeg"][1] + joints["RightLeg"][1]) / 2
    heights = np.arange(hip, joints["Chest"][1], WAIST_STEP_CM)
    girths = []
    for height in heights:
        found = outline_numbers(body_outline(*body, 0, spine_point(joints, height), np.array([0.0, 1.0, 0.0]),
                                             "torso"))
        girths.append(found["girth"] if found else np.inf)
    if not np.isfinite(girths).any():
        raise ValueError("the body's torso is not cut round the spine anywhere between the hips and the chest")
    return float(heights[int(np.argmin(girths))])


def torso_heights(joints, body):
    """The torso cuts' heights: chest (0.4 of the way from the Chest joint up to the shoulders), underbust (the Chest
    joint), waist (`natural_waist`), belly (between Spine1 and Spine2), low belly (halfway from the belly cut to the
    hips) and hip (the hip joints)."""
    shoulder = (joints["LeftArm"][1] + joints["RightArm"][1]) / 2
    belly = (joints["Spine1"][1] + joints["Spine2"][1]) / 2
    hip = (joints["LeftLeg"][1] + joints["RightLeg"][1]) / 2
    return {"chest": joints["Chest"][1] + 0.4 * (shoulder - joints["Chest"][1]), "underbust": joints["Chest"][1],
            "waist": natural_waist(body, joints), "belly": belly, "low_belly": (belly + hip) / 2, "hip": hip}


def limb_plane(region, start, middle, end):
    """A limb cut's (point, normal) from the limb's three joints: square to the bone, at the elbow or knee square to
    the two bones' bisector."""
    upper, lower = unit(middle - start), unit(end - middle)
    places = {"upper_arm": (start + 0.5 * (middle - start), upper), "thigh": (start + 0.35 * (middle - start), upper),
              "elbow": (middle, unit(upper + lower)), "knee": (middle, unit(upper + lower)),
              "forearm": (middle + 0.45 * (end - middle), lower), "cuff": (middle + 0.9 * (end - middle), lower),
              "shin": (middle + 0.5 * (end - middle), lower)}
    return places[region]


def cuts(joints, body):
    """Every cut: (region, side, point, normal); side is +1 or -1 for limbs (the sign of the limb's x), 0 for the
    torso; `body` (points cm, faces) places the waist."""
    found = [(region, 0, spine_point(joints, height), np.array([0.0, 1.0, 0.0]))
             for region, height in torso_heights(joints, body).items()]
    for prefix in ("Left", "Right"):
        for regions, names in ((ARM_REGIONS, ("Arm", "ForeArm", "Hand")), (LEG_REGIONS, ("Leg", "Shin", "Foot"))):
            chain = [np.asarray(joints[prefix + name], dtype=float) for name in names]
            side = 1 if chain[0][0] > 0 else -1
            found.extend((region, side, *limb_plane(region, *chain)) for region in regions)
    return found


def pair_height(joints, name):
    """The mean height of a Left and Right joint pair ('Arm': the shoulders, 'Leg': the hips)."""
    return (joints["Left" + name][1] + joints["Right" + name][1]) / 2


def armpit_height(body, joints):
    """The lowest height, every TORSO_STEP_CM from the Chest joint up to the shoulder joints, where the body's cut
    round the spine reaches out past both upper arms' bones at that height: where the arms join the torso (past the
    shoulder joints alone came 1 to 2 cm low on Nev, Ama and the player, under the arms' join)."""
    for height in np.arange(np.ceil(joints["Chest"][1]), pair_height(joints, "Arm"), TORSO_STEP_CM):
        point = spine_point(joints, height)
        outline = body_outline(*body, 0, point, UP, "torso")
        if outline is None:
            continue
        bones = [upper_arm_at(joints, prefix, height)[0] - point[0] for prefix in ("Left", "Right")]
        if outline[:, 0].min() < min(bones) and outline[:, 0].max() > max(bones):
            return float(height)
    raise ValueError("the body's cut round the spine never takes in the upper arms under the shoulders: no armpit")


def upper_arm_at(joints, prefix, height):
    """The point of one upper arm's bone (the Arm joint to the ForeArm joint, straight) at a height."""
    start, end = (np.asarray(joints[prefix + name], dtype=float) for name in ("Arm", "ForeArm"))
    return start + (height - start[1]) / (end[1] - start[1]) * (end - start)


def torso_band_cuts(joints):
    """The torso's cuts every TORSO_STEP_CM from the hip joints to the shoulder joints, as (name, 'torso', side,
    point, normal)."""
    heights = np.arange(np.ceil(pair_height(joints, "Leg")), pair_height(joints, "Arm"), TORSO_STEP_CM)
    return [(f"torso_{height:.0f}", "torso", 0, spine_point(joints, height), UP) for height in heights]


def shoulder_band_cuts(joints, body):
    """The shoulder's cuts every TORSO_STEP_CM from the armpit (`armpit_height`) to the shoulder joints, as (name,
    'shoulder', side, point, normal)."""
    heights = np.arange(armpit_height(body, joints), pair_height(joints, "Arm"), TORSO_STEP_CM)
    return [(f"shoulder_{height:.0f}", "shoulder", 0, spine_point(joints, height), UP) for height in heights]


def arm_band_cuts(joints):
    """Each arm's cuts square to the bone every ARM_STEP of the upper arm and the forearm, and at the elbow, as
    (name, 'arm', side, point, normal); the two arms' cuts share names."""
    upper = np.arange(UPPER_ARM_FROM, ARM_TO + 1e-9, ARM_STEP)
    lower = np.arange(FOREARM_FROM, ARM_TO + 1e-9, ARM_STEP)
    found = []
    for prefix in ("Left", "Right"):
        start, middle, end = (np.asarray(joints[prefix + name], dtype=float) for name in ("Arm", "ForeArm", "Hand"))
        side = 1 if start[0] > 0 else -1
        found += [(f"upper_arm_{round(100 * share)}", "arm", side, start + share * (middle - start),
                   unit(middle - start)) for share in upper]
        found.append(("elbow", "arm", side, *limb_plane("elbow", start, middle, end)))
        found += [(f"forearm_{round(100 * share)}", "arm", side, middle + share * (end - middle), unit(end - middle))
                  for share in lower]
    return found


def dense_cuts(joints, body):
    """Every cut the gate reads besides the named ones: the torso's, the shoulder's and the arms' bands, without an
    arm cut whose body chain takes in the spine (`takes_in_spine`)."""
    arms = [cut for cut in arm_band_cuts(joints) if not takes_in_spine(*body[:2], joints, *cut[2:])]
    return torso_band_cuts(joints) + shoulder_band_cuts(joints, body) + arms


def plane_basis(normal):
    """The cut's (across, front) unit vectors: front is the world's +z laid into the plane."""
    front = unit(np.array([0.0, 0.0, 1.0]) - normal * normal[2])
    return unit(np.cross(normal, front)), front


def plane_section(points, faces, point, normal):
    """The plane's cut through the triangles: segments (n, 2, 3) and, for each end, the mesh edge it lies on (an id
    shared by the neighbouring triangle's segment)."""
    height = (points - point) @ normal
    above = height[faces] > 0
    faces = faces[above.any(axis=1) & ~above.all(axis=1)]
    above = height[faces] > 0
    ends, keys = [], []
    for first, second in ((0, 1), (1, 2), (2, 0)):
        one, two = faces[:, first], faces[:, second]
        share = height[one] / np.where(height[one] == height[two], 1.0, height[one] - height[two])
        ends.append(points[one] + share[:, None] * (points[two] - points[one]))
        keys.append(np.minimum(one, two) * len(points) + np.maximum(one, two))
    crossing = np.stack([above[:, 0] != above[:, 1], above[:, 1] != above[:, 2], above[:, 2] != above[:, 0]], axis=1)
    ends, keys = np.stack(ends, axis=1)[crossing].reshape(-1, 2, 3), np.stack(keys, axis=1)[crossing].reshape(-1, 2)
    return ends, keys


def loops(keys):
    """The segments' connected chains, as an index array per chain."""
    if not len(keys):
        return []
    _, nodes = np.unique(keys, return_inverse=True)
    nodes = nodes.reshape(-1, 2)
    graph = coo_matrix((np.ones(len(nodes)), (nodes[:, 0], nodes[:, 1])), shape=(nodes.max() + 1,) * 2)
    _, chain = connected_components(graph, directed=False)
    segment_chain = chain[nodes[:, 0]]
    return [np.flatnonzero(segment_chain == number) for number in np.unique(segment_chain)]


def to_plane(points, point, normal):
    """Points as (across, front) in the cut, from its point."""
    across, front = plane_basis(normal)
    offset = points - point
    return np.c_[offset @ across, offset @ front]


def goes_round(segments, centre):
    """Whether flat segments (n, 2, 2) close round a point (crossings of a ray along +across, odd = round)."""
    start, end = segments[:, 0] - centre, segments[:, 1] - centre
    straddle = (start[:, 1] > 0) != (end[:, 1] > 0)
    share = start[straddle, 1] / (start[straddle, 1] - end[straddle, 1])
    crossing = start[straddle, 0] + share * (end[straddle, 0] - start[straddle, 0])
    return int((crossing > 0).sum()) % 2 == 1


def body_chain(points, faces, point, normal):
    """The body's cut round the cut's point, the smallest closed chain round it, as (segments (n, 2, 3), the same
    flat (n, 2, 2)); None when no chain goes round it."""
    segments, keys = plane_section(points, faces, point, normal)
    flat = to_plane(segments.reshape(-1, 3), point, normal).reshape(-1, 2, 2)
    round_it = [chain for chain in loops(keys) if goes_round(flat[chain], np.zeros(2))]
    if not round_it:
        return None
    chain = min(round_it, key=len)
    return segments[chain], flat[chain]


def body_outline(points, faces, side, point, normal, limb):
    """The body's cut (flat points) round the cut's point (`body_chain`); a leg's only on its own side (the thighs may
    touch)."""
    found = body_chain(points, faces, point, normal)
    if found is None:
        return None
    segments, flat = found
    outline = flat.reshape(-1, 2)
    if limb == "leg":
        outline = outline[segments.reshape(-1, 3)[:, 0] * side > 0]
    return outline


def takes_in_spine(points, faces, joints, side, point, normal):
    """Whether the body's chain round an arm cut reaches the spine (`spine_point` at the cut's height): the cut runs
    through the torso and the arm as one loop, so it reads the torso, not the arm."""
    found = body_chain(points, faces, point, normal)
    if found is None:
        return False
    ends = found[0].reshape(-1, 3)
    return bool(((ends[:, 0] - spine_point(joints, point[1])[0]) * side).min() <= 0)


def cloth_outline(points, faces, face_kind, side, point, normal, limb):
    """The cloth's cut (flat points) through the region's panels: the torso cuts everything but the sleeves, the
    shoulder everything but the trousers (the sleeve's cap with the torso); a limb cut its side's sleeves or trouser
    leg within reach of the bone."""
    keep = {"torso": face_kind != 1, "shoulder": face_kind != 2, "arm": face_kind == 1, "leg": face_kind == 2}[limb]
    segments, _ = plane_section(points, faces[keep], point, normal)
    ends = segments.reshape(-1, 3)
    outline = to_plane(ends, point, normal)
    if limb in LIMB_REACH_CM:
        outline = outline[(ends[:, 0] * side > 0) & (np.linalg.norm(outline, axis=1) < LIMB_REACH_CM[limb])]
    return outline


def radii(polygon):
    """A convex outline's distance from the cut's point in each of ANGLES (nan where the point is outside it)."""
    directions = np.c_[np.cos(ANGLES), np.sin(ANGLES)]
    start, edge = polygon, np.roll(polygon, -1, axis=0) - polygon
    across = directions[:, :1] * edge[None, :, 1] - directions[:, 1:] * edge[None, :, 0]
    safe = np.where(np.abs(across) > 1e-12, across, np.nan)
    along_ray = (start[None, :, 0] * edge[None, :, 1] - start[None, :, 1] * edge[None, :, 0]) / safe
    along_edge = (start[None, :, 0] * directions[:, 1:] - start[None, :, 1] * directions[:, :1]) / safe
    hit = (along_edge >= -1e-9) & (along_edge <= 1 + 1e-9) & (along_ray > 0)
    found = np.where(hit, along_ray, -np.inf).max(axis=1)
    return np.where(np.isfinite(found), found, np.nan)


def outline_numbers(outline):
    """Width (across), depth (front to back), girth (a tape measure's: the convex outline's length) and the radii of
    a cut; None when fewer than four points were cut or the outline does not go round the cut's point."""
    if outline is None or len(outline) < 4:
        return None
    try:
        polygon = outline[ConvexHull(outline).vertices]
    except QhullError:
        return None
    rays = radii(polygon)
    if np.isfinite(rays).mean() < COVER:
        return None
    return {"width": float(np.ptp(polygon[:, 0])), "depth": float(np.ptp(polygon[:, 1])),
            "girth": float(np.linalg.norm(np.roll(polygon, -1, axis=0) - polygon, axis=1).sum()), "radii": rays}


def cloth_parts(points, faces, labels):
    """Each triangle's part (point_kinds' numbers, the most of its corners')."""
    kinds = point_kinds(labels)[faces]
    return np.array([np.bincount(row, minlength=3).argmax() for row in kinds])


def side_cuts(cloth, body, joints):
    """region -> [(cloth numbers, body numbers) per side]; cloth and body are (points cm, faces[, face parts])."""
    found = {region: [] for region in REGIONS}
    for region, side, point, normal in cuts(joints, body):
        limb = limb_of(region)
        drape = outline_numbers(cloth_outline(*cloth, side, point, normal, limb))
        found[region].append((drape, outline_numbers(body_outline(*body, side, point, normal, limb))))
    return found


def pooled(pairs):
    """Width, depth, girth (mean of the sides read) of cloth and body and the stand-off (cloth radius minus body
    radius in every direction of every side) median and 90th percentile, cm; None where no side was read."""
    read = [(drape, body) for drape, body in pairs if drape is not None and body is not None]
    if not read:
        return None
    gaps = np.concatenate([drape["radii"] - body["radii"] for drape, body in read])
    gaps = gaps[np.isfinite(gaps)]
    row = {f"{who}_{key}": round(float(np.mean([pair[index][key] for pair in read])), 2)
           for index, who in enumerate(("cloth", "body")) for key in ("width", "depth", "girth")}
    row.update({"standoff_median": round(float(np.median(gaps)), 2),
                "standoff_p90": round(float(np.percentile(gaps, 90)), 2), "sides": len(read)})
    return row


def silhouette(cloth, body, joints):
    """region -> pooled numbers (or None) for one drape on its body; joints in centimetres."""
    return {region: pooled(pairs) for region, pairs in side_cuts(cloth, body, joints).items()}


def dense_silhouette(cloth, body, joints):
    """cut name -> (band, pooled numbers or None, whether cloth went round the cut on any side) for every one of
    `dense_cuts`, the two arms' cuts pooled."""
    pairs, bands = {}, {}
    for name, band, side, point, normal in dense_cuts(joints, body):
        drape = outline_numbers(cloth_outline(*cloth, side, point, normal, band))
        pairs.setdefault(name, []).append((drape, outline_numbers(body_outline(*body, side, point, normal, band))))
        bands[name] = band
    return {name: (bands[name], pooled(found), any(drape is not None for drape, _ in found))
            for name, found in pairs.items()}


def judge_dense(mine, reference, band):
    """A dense cut's verdict from both drapes' `dense_silhouette` rows: 'absent' when neither drape's cloth goes round
    it (a cut past both sleeves' ends: nothing to judge, and nothing that differs), else `judge`'s."""
    if not mine[2] and not reference[2]:
        return {"verdict": "absent", "over": [], "margin_cm": None}
    return judge(mine[1], reference[1], band)


def judge(mine, reference, group):
    """One cut's verdict against the reference drape's, with the tolerances of its group (TOLERANCE_CM's 'torso',
    'shoulder', 'arm' or 'leg'): 'fail' when the cloth's width or its stand-off (median or 90th percentile) is larger
    than the reference's by more than the tolerance, or when the reference was read there and the drape was not (no
    cloth round the cut: a sleeve ridden up short of it); 'unknown' when the reference was not read; else 'pass'; with
    what failed and the margin (cm, the most any number is over its tolerance; below 0 is room left)."""
    if reference is None:
        return {"verdict": "unknown", "over": [], "margin_cm": None}
    if mine is None:
        return {"verdict": "fail", "over": ["unread"], "margin_cm": None}
    margins = {number: mine[number] - reference[number] - tolerance
               for number, tolerance in TOLERANCE_CM[group].items()}
    over = [number for number, margin in margins.items() if margin > 0]
    return {"verdict": "fail" if over else "pass", "over": over, "margin_cm": round(max(margins.values()), 2)}


def worst(found):
    """'fail' when any of the verdicts fails, 'unknown' when none fails and any is unknown, else 'pass' (a dense
    cut 'absent' from both drapes passes)."""
    found = list(found)
    return "fail" if "fail" in found else "unknown" if "unknown" in found else "pass"


def gate(verdicts, dense_verdicts):
    """The drape's silhouette verdict (`worst`) over GATE_REGIONS' named cuts and every dense cut."""
    return worst([verdicts[region]["verdict"] for region in GATE_REGIONS] +
                 [row["verdict"] for row in dense_verdicts.values()])


def band_summary(dense_verdicts):
    """band -> how many dense cuts were judged, the cuts failed and unknown, and the cut with the largest margin."""
    summary = {}
    for name, row in dense_verdicts.items():
        band = summary.setdefault(row["band"], {"cuts": 0, "fail": [], "unknown": [], "worst_cut": None,
                                                "worst_margin_cm": None})
        band["cuts"] += 1
        if row["verdict"] in ("fail", "unknown"):
            band[row["verdict"]].append(name)
        if row["margin_cm"] is not None and (band["worst_margin_cm"] is None or
                                             row["margin_cm"] > band["worst_margin_cm"]):
            band["worst_cut"], band["worst_margin_cm"] = name, row["margin_cm"]
    return summary


def judge_belt(mine, reference):
    """The belt band's verdict against the reference drape's (`belt_cover`, cm): 'unknown' when the reference has
    no belt band to read; 'fail' when the reference reads one and the drape does not (its torso ridden up out of the
    band) or covers it less than the reference by more than BELT_TOLERANCE_CM; else 'pass'."""
    if reference is None:
        return "unknown"
    if mine is None or mine < reference - BELT_TOLERANCE_CM:
        return "fail"
    return "pass"


def crossing_pairs(points, faces, edges, edge_index, face_index):
    """Of candidate (edge, triangle) pairs sharing no corner, the edges that pass through their triangle
    (Moller-Trumbore with the segment's own length)."""
    apart = ~(faces[face_index] == edges[edge_index, :1]).any(axis=1) & \
        ~(faces[face_index] == edges[edge_index, 1:]).any(axis=1)
    edge_index, face_index = edge_index[apart], face_index[apart]
    start, direction = points[edges[edge_index, 0]], points[edges[edge_index, 1]] - points[edges[edge_index, 0]]
    first, second, third = (points[faces[face_index, corner]] for corner in range(3))
    side_one, side_two = second - first, third - first
    across = np.cross(direction, side_two)
    determinant = np.einsum("ij,ij->i", side_one, across)
    usable = np.abs(determinant) > 1e-12
    inverse = np.where(usable, 1.0 / np.where(usable, determinant, 1.0), 0.0)
    offset = start - first
    along_one = np.einsum("ij,ij->i", offset, across) * inverse
    turned = np.cross(offset, side_one)
    along_two = np.einsum("ij,ij->i", direction, turned) * inverse
    along_edge = np.einsum("ij,ij->i", side_two, turned) * inverse
    hit = usable & (along_one >= 0) & (along_two >= 0) & (along_one + along_two <= 1) & (along_edge >= 0) & \
        (along_edge <= 1)
    return edge_index[hit]


def self_crossings(points, faces, chunk=4096):
    """How many cloth edges pass through a cloth triangle they share no corner with: cloth gone through cloth, which
    GarmentCode's Warp drapes keep at 0. A triangle can only be crossed by an edge whose middle lies within the
    triangle's radius plus half the edge's length of its centre; candidates are found that way, a chunk of edges at a
    time."""
    edges = np.unique(np.sort(faces[:, [[0, 1], [1, 2], [2, 0]]].reshape(-1, 2), axis=1), axis=0)
    corners = points[faces]
    centres = corners.mean(axis=1)
    radii = np.linalg.norm(corners - centres[:, None], axis=2).max(axis=1)
    middles = 0.5 * (points[edges[:, 0]] + points[edges[:, 1]])
    halves = 0.5 * np.linalg.norm(points[edges[:, 0]] - points[edges[:, 1]], axis=1)
    crossed = []
    for size in np.unique(np.ceil(np.log2(np.maximum(radii, 1e-9)))):
        group = np.flatnonzero(np.ceil(np.log2(np.maximum(radii, 1e-9))) == size)
        group_tree = cKDTree(centres[group])
        for begin in range(0, len(edges), chunk):
            rows = np.arange(begin, min(begin + chunk, len(edges)))
            near = group_tree.query_ball_point(middles[rows], halves[rows] + 2.0 ** size)
            counts = [len(found) for found in near]
            if not sum(counts):
                continue
            edge_index = np.repeat(rows, counts)
            face_index = group[np.concatenate([np.asarray(found, dtype=np.int64) for found in near])]
            crossed.append(crossing_pairs(points, faces, edges, edge_index, face_index))
    return int(len(np.unique(np.concatenate(crossed)))) if crossed else 0


def read_cloth_cm(folder):
    """A drape folder's cloth (centimetres, triangles, each triangle's part)."""
    cloth, segmentation = drape_files(folder)
    points, faces = sewing.read_obj(cloth)
    return points, faces, cloth_parts(points, faces, panel_of_each_point(segmentation, points))


def silhouette_against(folder, reference, body_obj, joints_json):
    """The drape's silhouette against the reference drape's: every named region's numbers and verdict
    ('silhouette'), every dense cut's ('dense'), each band's summary ('bands') and the gate's verdict
    ('silhouette_gate')."""
    joints = {name: np.asarray(value, dtype=float) * 100.0
              for name, value in json.loads(pathlib.Path(joints_json).read_text()).items()}
    body = sewing.read_obj(body_obj)
    cloth, theirs = read_cloth_cm(folder), read_cloth_cm(reference)
    mine_named, theirs_named = silhouette(cloth, body, joints), silhouette(theirs, body, joints)
    named = {region: {"drape": mine_named[region], "reference": theirs_named[region],
                      **judge(mine_named[region], theirs_named[region], limb_of(region))} for region in REGIONS}
    mine_dense, theirs_dense = dense_silhouette(cloth, body, joints), dense_silhouette(theirs, body, joints)
    dense = {name: {"band": row[0], "drape": row[1], "reference": theirs_dense[name][1],
                    **judge_dense(row, theirs_dense[name], row[0])} for name, row in mine_dense.items()}
    return {"silhouette": named, "dense": dense, "bands": band_summary(dense), "silhouette_gate": gate(named, dense)}


def belt_of(folder, look):
    """`belt_cover` of a drape folder's torso cloth on the look's belt band (None: no band to read)."""
    cloth, segmentation = drape_files(folder)
    points, _ = read_obj(cloth)
    return belt_numbers(points, panel_labels(segmentation), fit_module(look)).get("belt_cloth_cm")


def against(folder, reference, body_obj, look, belt_cloth_cm):
    """Everything judged against the reference drape: the silhouette (`silhouette_against`), the belt band
    (`judge_belt`) and the drape's verdict (`worst` of the two): only 'pass' lets a drape through."""
    found = silhouette_against(folder, reference, body_obj, pathlib.Path(look) / "joints.json")
    reference_belt = belt_of(reference, look)
    found.update(reference_belt_cloth_cm=reference_belt, belt=judge_belt(belt_cloth_cm, reference_belt))
    found["verdict"] = worst([found["silhouette_gate"], found["belt"]])
    return found


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("drape", type=pathlib.Path)
    parser.add_argument("body", type=pathlib.Path)
    parser.add_argument("look", type=pathlib.Path)
    parser.add_argument("--reference", type=pathlib.Path, help="a drape folder of the same pattern on the same body")
    parser.add_argument("--json", type=pathlib.Path)
    options = parser.parse_args()
    result = measure(options.drape, options.body, options.look)
    if options.reference:
        result.update(against(options.drape, options.reference, options.body, options.look,
                              result.get("belt_cloth_cm")))
    text = json.dumps(result, indent=1)
    if options.json:
        options.json.write_text(text)
    print(text)


if __name__ == "__main__":
    main()
