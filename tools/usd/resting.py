"""Check that every object of a place's OpenUSD stage rests on what it should rest on: nothing floating over the
ground or over the object it stands on, nothing sunk into the ground deeper than it was laid.

    .venv/bin/python tools/usd/resting.py <stage.usda> [--out <resting.json>] [--settle]

The stage is read as composed (the creator's edit layer included), in its own frame (metres, y up). The ground is the
stage's `/<place>/Ground` mesh, or y = 0 on a flat place. For every object (children included) the drawn mesh is
taken in the stage's frame and each of its points is looked at straight down:

    gap     how far the object's lowest point clears what is under it: the ground, or another object's surface
            a ray down from that point meets. An object with a gap over TOLERANCE floats.
    weight  where the object's weight falls (the middle of its surface, by area). An object whose weight stands
            outside what it touches (its points within TOLERANCE of the ground, of a support under it, or of another
            object beside it) tips: one end hangs in the air. The check says how far down it would settle before its weight stands over what it touches.
    depth   how far the object's deepest point lies under the ground under it. The game lays some pieces into the
            ground on purpose (a wreck's hull dug in): a negative lift (`score:lift`) is how deep a piece was laid,
            and only depth past that and TOLERANCE is sunk.

Exceptions are data: an object whose inventory row hangs (its `anchor` is wall, ceiling or roof) is not checked, and a
child (`anchor` on:<row>) is checked for floating only, against what is under it. Prints one line per object that
fails; exits 1 when any does.

--settle is the ground snap: it lowers every object that tips by as far as it settles, in the place's layout itself
(the spot's `y` in data/inventory/<place>.json and the piece's `at` in data/kit/<place>.json), so the next export
lays it resting. Export the stage again and check it after.
"""
import argparse
import json
import pathlib
import sys

import numpy as np
import trimesh
from pxr import Usd, UsdGeom
from scipy.interpolate import LinearNDInterpolator
from scipy.spatial import ConvexHull, QhullError, cKDTree

REPO = pathlib.Path(__file__).resolve().parents[2]
# How far off the ground or its support an object may be, either way, and still rest there, in metres.
TOLERANCE = 0.03
HUNG = {"wall", "ceiling", "roof"}
# How many of an object's lowest points are looked down from for another object under them, and how far above each
# point the ray starts, so a point bedded a little into its support still finds the support's top.
FOOTPRINT = 600
RAY_START = 0.1
# How far an object's weight may fall outside what it touches and still stand, and how far down it is let settle.
BALANCE = 0.05
SETTLE_MOST = 1.5
# How densely another object's surface is sampled to find where this one touches it, and the most samples taken.
CONTACT_SPACING = 0.02
CONTACT_SAMPLES = 300_000


def in_stage(prim):
    """A mesh prim's points in the stage's frame, and its triangles."""
    mesh = UsdGeom.Mesh(prim)
    points = np.asarray(mesh.GetPointsAttr().Get(), dtype=np.float64)
    matrix = np.asarray(UsdGeom.Xformable(mesh).ComputeLocalToWorldTransform(Usd.TimeCode.Default()))
    triangles = np.asarray(mesh.GetFaceVertexIndicesAttr().Get()).reshape(-1, 3)
    return points @ matrix[:3, :3] + matrix[3, :3], triangles


def ground_height(stage, place):
    """The ground's height under any (x, z): read off the stage's ground mesh, or 0 on a flat place."""
    prim = stage.GetPrimAtPath(f"/{place}/Ground")
    if not prim.IsValid():
        return lambda flat: np.zeros(len(flat))
    points, _ = in_stage(prim)
    return LinearNDInterpolator(points[:, [0, 2]], points[:, 1])


def objects_of(stage, place):
    """Every laid object of the stage (children included): {path: prim}."""
    root = stage.GetPrimAtPath(f"/{place}/Objects")
    return {str(prim.GetPath()): prim for prim in Usd.PrimRange(root)
            if prim.HasAttribute("score:kind") and prim.GetChild("geo").IsValid()}


def support_gaps(points, others):
    """How far each of the lowest of these points stands over another object's surface straight under it (inf where
    none is under it): (those points, their gaps)."""
    lowest = points[np.argsort(points[:, 1])[:FOOTPRINT]]
    gaps = np.full(len(lowest), np.inf)
    if others is None:
        return lowest, gaps
    origins = lowest + [0.0, RAY_START, 0.0]
    hits, rays, _ = others.ray.intersects_location(origins, np.tile([0.0, -1.0, 0.0], (len(origins), 1)))
    np.minimum.at(gaps, rays, origins[rays, 1] - hits[:, 1] - RAY_START)
    return lowest, gaps


def outside_by(point, footprint):
    """How far a point (x, z) lies outside the convex hull of the footprint's points (x, z); 0 inside, inf with no
    footprint."""
    if len(footprint) == 0:
        return np.inf
    try:
        corners = footprint[ConvexHull(footprint).vertices]
    except QhullError:  # fewer than three points, or all on one line: the nearest of them
        return float(np.min(np.linalg.norm(footprint - point, axis=1)))
    ends = np.roll(corners, -1, axis=0)
    edges = ends - corners
    across = edges[:, 0] * (point[1] - corners[:, 1]) - edges[:, 1] * (point[0] - corners[:, 0])
    if np.all(across >= 0) or np.all(across <= 0):
        return 0.0
    share = np.clip(np.einsum("ij,ij->i", point - corners, edges) / np.einsum("ij,ij->i", edges, edges), 0.0, 1.0)
    return float(np.min(np.linalg.norm(corners + edges * share[:, None] - point, axis=1)))


def weight_at(mesh):
    """Where an object's weight falls, (x, z): the middle of its surface, each face by its area (a made model is a
    shell, not a solid)."""
    return (mesh.triangles_center * mesh.area_faces[:, None]).sum(axis=0)[[0, 2]] / mesh.area


def settling(weight, flat, clearance):
    """How far an object must go down for its weight to stand over what it touches (points within TOLERANCE of the
    ground or a support): 0 when it already does, None when even SETTLE_MOST lower it does not."""
    for down in np.arange(0.0, SETTLE_MOST + 1e-9, 0.01):
        if outside_by(weight, flat[clearance <= down + TOLERANCE]) <= BALANCE:
            return round(float(down), 2)
    return None


def touching(points, others):
    """Which of these points touch another object (within TOLERANCE of its surface, from any side: a walkway tube
    held between two modules touches them at its ends)."""
    if others is None:
        return np.zeros(len(points), dtype=bool)
    count = int(min(CONTACT_SAMPLES, max(1000, others.area / CONTACT_SPACING ** 2)))
    samples, _ = trimesh.sample.sample_surface(others, count, seed=0)
    distances, _ = cKDTree(samples).query(points, distance_upper_bound=TOLERANCE)
    return distances <= TOLERANCE


def neighbours(meshes, name, low, high):
    """The other objects' meshes whose box reaches under this one's footprint, joined; None when there are none."""
    near = [mesh for other, mesh in meshes.items() if other != name and not other.startswith(name + "/")
            and np.all(mesh.bounds[0][[0, 2]] <= high[[0, 2]]) and np.all(mesh.bounds[1][[0, 2]] >= low[[0, 2]])
            and mesh.bounds[0][1] <= high[1]]
    return trimesh.util.concatenate(near) if near else None


def judged(name, prim, mesh, ground, others):
    """One object's verdict: its gap over what is under it, its depth under the ground, whether its weight stands
    over what it touches (and how far down it would settle), and what is wrong."""
    points = np.asarray(mesh.vertices)
    anchor = prim.GetAttribute("score:anchor").Get() or ""
    lift = float(prim.GetAttribute("score:lift").Get() or 0.0) if prim.HasAttribute("score:lift") else 0.0
    found = {"object": name, "row": prim.GetAttribute("score:row").Get(), "anchor": anchor}
    if anchor in HUNG:
        return dict(found, result="hung, not checked")
    clearance = points[:, 1] - ground(points[:, [0, 2]])
    known = np.isfinite(clearance)
    on_ground = float(clearance[known].min()) if known.any() else np.inf
    lowest, gaps = support_gaps(points, others)
    beside = points[touching(points, others)]
    flat = np.vstack([points[known][:, [0, 2]], lowest[:, [0, 2]], beside[:, [0, 2]]])
    under = np.concatenate([np.maximum(clearance[known], 0.0), gaps, np.zeros(len(beside))])
    gap = float(under.min()) if len(under) else np.inf
    depth = max(0.0, -on_ground)
    allowed = max(0.0, -lift)
    weight = weight_at(mesh)
    down = settling(weight, flat, under)
    faults = []
    if gap > TOLERANCE:
        faults.append(f"floats {gap * 100:.1f} cm over what is under it")
    elif down != 0.0:
        faults.append(f"tips: its weight is {outside_by(weight, flat[under <= TOLERANCE]) * 100:.0f} cm outside what "
                      f"it stands on; " + (f"it settles {down * 100:.0f} cm lower" if down is not None
                                           else f"it does not settle within {SETTLE_MOST * 100:.0f} cm"))
    if not anchor.startswith("on:") and depth > allowed + TOLERANCE:
        faults.append(f"sunk {depth * 100:.1f} cm into the ground (laid {allowed * 100:.0f} cm in)")
    return dict(found, gap=round(gap, 4) if np.isfinite(gap) else None, depth=round(depth, 4),
                laid_in=round(allowed, 4), settles=down, result="; ".join(faults) or "rests", passed=not faults)


def settled_layout(verdicts, inventory_path, kit_path):
    """The ground snap: every laid object (`<row>_<n>`, the n-th spot of its row) that tips, lowered in the layout by
    as far as it settles; the objects lowered, with how far."""
    inventory = json.loads(inventory_path.read_text())
    kit = json.loads(kit_path.read_text())
    spots = {row["id"]: row["at"] for row in inventory["rows"]}
    pieces = {}
    for piece in kit["pieces"]:
        pieces.setdefault(piece["row"], []).append(piece)
    lowered = {}
    for found in verdicts:
        if "/" in found["object"] or not found.get("settles") or not found["result"].startswith("tips"):
            continue
        row, number = found["object"].rsplit("_", 1)
        spot, piece = spots[row][int(number) - 1], pieces[row][int(number) - 1]
        spot["y"] = round(float(spot.get("y", 0.0)) - found["settles"], 2)
        piece["at"][1] = spot["y"]
        lowered[found["object"]] = found["settles"]
    inventory_path.write_text(json.dumps(inventory, indent=1, ensure_ascii=False) + "\n")
    kit_path.write_text(json.dumps(kit, indent="\t", ensure_ascii=False) + "\n")
    return lowered


def check(stage_path):
    """Every object of the stage judged: a list of verdicts, in the stage's order."""
    stage = Usd.Stage.Open(str(stage_path))
    place = stage.GetDefaultPrim().GetName()
    ground = ground_height(stage, place)
    prims = objects_of(stage, place)
    meshes = {}
    for name, prim in prims.items():
        points, triangles = in_stage(prim.GetChild("geo"))
        meshes[name] = trimesh.Trimesh(points, triangles, process=False)
    verdicts = []
    for name, prim in prims.items():
        mesh = meshes[name]
        others = neighbours(meshes, name, *mesh.bounds)
        verdicts.append(judged(name.removeprefix(f"/{place}/Objects/"), prim, mesh, ground, others))
    return verdicts


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("stage", type=pathlib.Path)
    parser.add_argument("--out", type=pathlib.Path)
    parser.add_argument("--settle", action="store_true", help="lower every object that tips in the place's layout")
    arguments = parser.parse_args()
    verdicts = check(arguments.stage)
    if arguments.settle:
        stage = Usd.Stage.Open(str(arguments.stage))
        place = stage.GetDefaultPrim().GetName()
        lowered = settled_layout(verdicts, REPO / f"data/inventory/{place}.json", REPO / f"data/kit/{place}.json")
        print("settled in the layout: " + (", ".join(f"{name} {down * 100:.0f} cm" for name, down in lowered.items())
                                           or "nothing"))
    if arguments.out:
        arguments.out.write_text(json.dumps(verdicts, indent=1) + "\n")
    failed = [verdict for verdict in verdicts if verdict.get("passed") is False]
    for verdict in failed:
        print(f"{verdict['object']}: {verdict['result']}")
    print(f"{len(verdicts)} objects, {len(failed)} not resting")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
