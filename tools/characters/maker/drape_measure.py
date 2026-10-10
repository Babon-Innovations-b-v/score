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
  (fit.y(1.005) to fit.y(1.062)) and how much of that band's height the torso cloth covers.
- self_crossings: how many cloth edges pass through a cloth triangle they share no corner with (cloth through cloth).
- silhouette (with --reference, another simulator's drape of the same pattern on the same body; the look's
  joints.json places the cuts): what the eye reads as a bloated chest, a sleeve ballooning off the arm or no waist,
  which the numbers above miss (2026-10-10). The cloth and the body are cut at places fixed by the joints and the
  body: chest, underbust, waist (the body's narrowest girth between the hips and the chest), belly (between the
  Spine1 and Spine2 joints, a few centimetres lower), low belly (halfway from there to the hips) and hip level; upper arm, elbow, forearm and cuff square to the
  arm's bone; thigh, knee and shin square to the leg's. Per cut, both sides pooled: the cloth's and the body's width (across: the front view's
  silhouette), depth (front to back: the side view's) and girth (a tape measure's, round the convex outline), and
  the stand-off (the cloth's outline radius minus the body's in 72 directions round the bone or the spine), median
  and 90th percentile, cm. Each region is pass, fail (the width or a stand-off larger than the reference's by more
  than TOLERANCE_CM, chosen from the Warp drapes' own spread, or the reference has cloth round the cut and the drape
  has not: a sleeve ridden up short of the cuff) or unknown (neither drape read there, or the body's cut not read).
  `gate` is the verdict over GATE_REGIONS, the torso and the arms, where the owner saw the bloat.
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
            "belt_cloth_cm": round(100.0 * max(0.0, top - max(bottom, low)), 2)}


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
# the low-belly cut in drapes-fix round 4 (267 torso halves): the torso's width came to 1.50 (1.51 before).
TOLERANCE_CM = {"torso": {"cloth_width": 1.5, "standoff_median": 0.5, "standoff_p90": 0.7},
                "arm": {"cloth_width": 0.8, "standoff_median": 0.4, "standoff_p90": 0.5},
                "leg": {"cloth_width": 1.0, "standoff_median": 0.5, "standoff_p90": 0.7}}


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


def body_outline(points, faces, side, point, normal, limb):
    """The body's cut (flat points) round the cut's point: the smallest closed chain round it; a leg's only on its own
    side (the thighs may touch)."""
    segments, keys = plane_section(points, faces, point, normal)
    flat = to_plane(segments.reshape(-1, 3), point, normal).reshape(-1, 2, 2)
    round_it = [chain for chain in loops(keys) if goes_round(flat[chain], np.zeros(2))]
    if not round_it:
        return None
    chain = min(round_it, key=len)
    outline = flat[chain].reshape(-1, 2)
    if limb == "leg":
        outline = outline[segments[chain].reshape(-1, 3)[:, 0] * side > 0]
    return outline


def cloth_outline(points, faces, face_kind, side, point, normal, limb):
    """The cloth's cut (flat points) through the region's panels: the torso cuts everything but the sleeves; a limb
    cut its side's sleeves or trouser leg within reach of the bone."""
    keep = face_kind != 1 if limb == "torso" else face_kind == {"arm": 1, "leg": 2}[limb]
    segments, _ = plane_section(points, faces[keep], point, normal)
    ends = segments.reshape(-1, 3)
    outline = to_plane(ends, point, normal)
    if limb != "torso":
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


def judge(mine, reference, region):
    """One region's verdict against the reference drape's: 'fail' when the cloth's width or its stand-off (median or
    90th percentile) is larger than the reference's by more than TOLERANCE_CM, or when the reference was read there
    and the drape was not (no cloth round the cut: a sleeve ridden up short of it); 'unknown' when the reference was
    not read; else 'pass'; with what failed."""
    if reference is None:
        return {"verdict": "unknown", "over": []}
    if mine is None:
        return {"verdict": "fail", "over": ["unread"]}
    over = [number for number, tolerance in TOLERANCE_CM[limb_of(region)].items()
            if mine[number] > reference[number] + tolerance]
    return {"verdict": "fail" if over else "pass", "over": over}


def gate(verdicts):
    """The drape's verdict over GATE_REGIONS from its per-region verdicts: 'fail' when any fails, 'unknown' when none
    fails and any is unknown, else 'pass'."""
    found = [verdicts[region]["verdict"] for region in GATE_REGIONS]
    return "fail" if "fail" in found else "unknown" if "unknown" in found else "pass"


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
    """Every region's numbers for the drape and the reference drape and the drape's verdict against it."""
    joints = {name: np.asarray(value, dtype=float) * 100.0
              for name, value in json.loads(pathlib.Path(joints_json).read_text()).items()}
    body = sewing.read_obj(body_obj)
    mine = silhouette(read_cloth_cm(folder), body, joints)
    theirs = silhouette(read_cloth_cm(reference), body, joints)
    return {region: {"drape": mine[region], "reference": theirs[region], **judge(mine[region], theirs[region], region)}
            for region in REGIONS}


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
        result["silhouette"] = silhouette_against(options.drape, options.reference, options.body,
                                                  options.look / "joints.json")
        result["silhouette_gate"] = gate(result["silhouette"])
    text = json.dumps(result, indent=1)
    if options.json:
        options.json.write_text(text)
    print(text)


if __name__ == "__main__":
    main()
