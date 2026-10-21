"""The terrain stage's gates, measured on the made grounds:

    scale      every named landform as big as its plan says (a crater's depth and rim diameter, a hill range's
               crest), the waterfront at its level, and no height clipped by the record's sixteen bits
    slope      the held flats under every seat level (their steepest slope) and the paths walkable

and the measures ground-fit@<place> (fit.py) takes on a place's own stage standing on its made ground: the ground
under its objects (`measure_under`) and its openings (`measure_openings`). The `measure_*` functions take any place
stage.
"""
import json
import pathlib

import numpy as np
from pxr import Usd, UsdGeom

from score import checks
from score.stages.terrain import measures, outside, record, sight

# An object stood on the old ground when its lowest point was within this of the old ground under its middle.
STANDING_BAND = 0.3
# A flat world's object has the made ground within this of its feet; a ball's object no rougher footprint than
# before by more than this (metres).
FEET = 0.05
ROUGHER = 0.10
# A spot lies under water when the ground there is this far under the water's level (the waterfront's ground lies a
# few centimetres under it, behind the quay).
WATER_DEPTH = 0.5
# A doorway opens onto a floor when one lies within this below its sill, this far out from the doorway each side.
DOOR_DROP = 0.6
DOOR_OUT = 0.6
# A probe stands inside when a floor lies within this below it.
PROBE_FLOOR = 2.0
PROBE_HEIGHT = 1.6
PROBE_GRID = 5


# --- the places -------------------------------------------------------------------------------------------------

def footprint(scene, kit):
    """The place's own box (across, along): its scene record's floor, else its kit's pieces."""
    if scene.get("floor"):
        return np.asarray(scene["floor"][0], dtype=float), np.asarray(scene["floor"][1], dtype=float)
    spots = np.array([[piece["at"][0], piece["at"][2]] for piece in kit["pieces"]]) if kit else np.zeros((1, 2))
    return spots.min(axis=0), spots.max(axis=0)


def place_files(inputs, place):
    """A place's scene record and kit (or None)."""
    def read(folder):
        path = pathlib.Path(inputs[folder]) / f"{place}.json" if folder in inputs else None
        return json.loads(path.read_text()) if path and path.exists() else None
    return read("scenes") or {}, read("kits")


def leaves(stage, place, kit):
    """The prims of the place's moving door leaves: its kit's `_leaf` pieces' objects."""
    found = []
    stems = {piece["model"].rsplit("_", 1)[0] for piece in (kit or {}).get("pieces", [])
             if piece["kind"].endswith("_leaf") and piece.get("model")}
    objects = stage.GetPrimAtPath(f"/{place}/Objects")
    if objects.IsValid():
        found += [str(child.GetPath()) for child in objects.GetChildren() if child.GetName().rsplit("_", 1)[0] in stems]
    return found


# --- doors and views --------------------------------------------------------------------------------------------

def kit_doors(kit):
    """Every doorway in the kit's walls (an opening from the floor at least 1.9 m tall): its middle on the sill and
    the wall's normal."""
    found = []
    for piece in (kit or {}).get("pieces", []):
        for low_u, low_v, high_u, high_v in piece.get("openings") or []:
            if low_v > 0.05 or high_v - low_v < 1.9 or "wall" not in piece["kind"]:
                continue
            across, up, normal = (np.asarray(piece[axis], dtype=float) for axis in ("x", "y", "z"))
            middle = np.asarray(piece["at"], dtype=float) + across * (low_u + high_u) / 2 + up * low_v
            found.append({"door": f"{piece.get('model', piece['kind'])} at {np.round(middle, 2).tolist()}",
                          "middle": middle, "normal": normal})
    return found


def shell_doors(scene):
    """Every doorway in the scene record's room walls: its middle on the deck and the wall's normal."""
    found = []
    sides = {"north": (0, -1), "south": (0, 1), "east": (1, 0), "west": (-1, 0)}
    for entry in scene.get("structure", []):
        if entry.get("builder") != "room_walls":
            continue
        for door in entry.get("doors", []):
            across, along = sides[door["side"]]
            middle = np.array([across * entry["wide"] / 2, 0.0, along * entry["deep"] / 2])
            found.append({"door": f"{entry['name']} {door['side']} door ({door['wide']} x {door['tall']} m)",
                          "middle": middle, "normal": np.array([across, 0.0, along], dtype=float)})
    return found


def caster(mesh):
    """A ray caster over a trimesh (Embree when it is there)."""
    import trimesh
    return trimesh.ray.ray_pyembree.RayMeshIntersector(mesh) if trimesh.ray.has_embree else mesh.ray


def drops(rays, origins, down):
    """How far below each origin the first surface lies straight down (inf where none)."""
    directions = np.repeat(np.asarray(down, dtype=float)[None, :], len(origins), axis=0)
    hits, ray_index, _ = rays.intersects_location(origins, directions, multiple_hits=False)
    found = np.full(len(origins), np.inf)
    for hit, index in zip(hits, ray_index):
        found[index] = min(found[index], float(np.linalg.norm(hit - origins[index])))
    return found


def door_floors(rays, doors, up):
    """Each doorway's floor on both sides: how far under its sill the first surface lies DOOR_OUT out, and whether
    both are within DOOR_DROP."""
    up = np.asarray(up, dtype=float)
    found = []
    for door in doors:
        origins = np.array([door["middle"] + side * door["normal"] * DOOR_OUT + up * 1.0 for side in (1.0, -1.0)])
        below = drops(rays, origins, -up) - 1.0
        found.append({"door": door["door"], "drops": [round(float(value), 2) if np.isfinite(value) else None
                                                      for value in below],
                      "open_onto_nothing": bool(np.any(below > DOOR_DROP))})
    return found


def probes(rays, scene, kit, up):
    """Where a viewer stands: the scene record's view eyes and a grid over the place's own box at eye height, each
    kept only over a floor within PROBE_FLOOR."""
    low, high = footprint(scene, kit)
    grid = [[across, PROBE_HEIGHT, along] for across in np.linspace(low[0] + 0.4, high[0] - 0.4, PROBE_GRID)
            for along in np.linspace(low[1] + 0.4, high[1] - 0.4, PROBE_GRID)]
    spots = np.array([view["eye"] for view in scene.get("views", [])] + grid, dtype=float)
    floor = drops(rays, spots, -np.asarray(up, dtype=float))
    return spots[floor <= PROBE_FLOOR]


def measure_openings(stage, place, records, ball=None, up=(0.0, 1.0, 0.0)):
    """A place stage's openings: every doorway's floors and the void rays from inside, the doors open; `records` its
    (scene record, kit or None); `ball` the world's middle and radius in the place's frame on
    a small world (its horizon dips)."""
    scene, kit = records
    seen = sight.gathered(stage, leaves(stage, place, kit))
    rays = caster(seen)
    doors = door_floors(rays, kit_doors(kit) + shell_doors(scene), up)
    viewed = sight.voids(seen, probes(rays, scene, kit, up), up, ball=ball)
    return {"doors": doors, "doors_onto_nothing": sum(door["open_onto_nothing"] for door in doors),
            "void_rays": viewed["void"], "rays": viewed["rays"], "void_share": round(viewed["share"], 6),
            "probes": len(viewed["probes"]), "worst_probe": viewed["worst"]}


# --- objects on the ground --------------------------------------------------------------------------------------

def object_boxes(stage, place):
    """Each laid object's box in the place's frame: {name: (low, high)}."""
    cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render])
    objects = stage.GetPrimAtPath(f"/{place}/Objects")
    found = {}
    for child in objects.GetChildren() if objects.IsValid() else []:
        box = cache.ComputeWorldBound(child).ComputeAlignedRange()
        if not box.IsEmpty():
            found[child.GetName()] = (np.asarray(box.GetMin()), np.asarray(box.GetMax()))
    return found


def heights_under(laid, spots):
    """The ground's height in the place's frame under each (across, along)."""
    spots = np.atleast_2d(spots)
    flat = laid.origin + spots[:, [0]] * laid.frame[0] + spots[:, [1]] * laid.frame[2]
    directions = flat / np.linalg.norm(flat, axis=1, keepdims=True)
    height, _ = laid.height(directions)
    return laid.in_place_frame(directions * (laid.radius + height)[:, None])[:, 1]


def footprint_spots(low, high):
    """Nine spots over an object's footprint (its corners, edges' middles and middle)."""
    return np.array([[across, along] for across in np.linspace(low[0], high[0], 3)
                     for along in np.linspace(low[2], high[2], 3)])


def measure_under(boxes, old_ground, laid, water_level=None):
    """Every object that stood on the old ground, judged on the made one against how it stood on the old one:
    {"standing": count, "faults": [...]}. A fault: water under it now; on a flat world (where an object keeps its
    height) the ground further from its feet than before by more than FEET; on a ball (where the export stands each
    piece on the ground under it) the ground under its footprint rougher than before by more than ROUGHER.
    `old_ground(spots)` gives the old ground's height under spots, `laid` the made Ground."""
    flat_world = laid.radius > 1e5
    faults, standing = [], 0
    for name, (low, high) in boxes.items():
        spots = footprint_spots(low, high)
        middle = spots[4:5]
        if abs(low[1] - old_ground(middle)[0]) > STANDING_BAND:
            continue
        standing += 1
        made = heights_under(laid, spots)
        before = old_ground(spots)
        if water_level is not None and np.any(made < water_level - WATER_DEPTH):
            faults.append(f"{name}: over water, the ground {float(made.min()):.2f} m under its footprint")
        elif flat_world and abs(low[1] - made[4]) > abs(low[1] - before[4]) + FEET:
            faults.append(f"{name}: its feet at {low[1]:.2f} m, the ground under it at {made[4]:.2f} m "
                          f"(before {before[4]:.2f} m)")
        elif not flat_world and np.ptp(made) > np.ptp(before) + ROUGHER:
            faults.append(f"{name}: the ground under it varies {np.ptp(made):.2f} m, before {np.ptp(before):.2f} m")
    return {"standing": standing, "faults": faults}


# --- the gates ----------------------------------------------------------------------------------------------------

def grounds_of(output):
    """Every made ground in the output: {name: record}."""
    return {folder.name: record.read(folder) for folder in sorted(pathlib.Path(output).iterdir())
            if (folder / "ground.json").exists()}


def plans_of(inputs):
    """Every ground's plan: {name: plan}."""
    return {path.stem: json.loads(path.read_text()) for path in sorted((pathlib.Path(inputs["grounds"]) / "plan")
                                                                         .glob("*.json"))}


def judge_scale(output, inputs, evidence):
    """Fail on a named landform off its planned size, a waterfront off its level, or a height clipped."""
    plans = plans_of(inputs)
    findings = [f"{name}: {fault}" for name, made in grounds_of(output).items()
                for fault in measures.scale(made, plans[name])["faults"]]
    reason = f"{len(findings)} landforms or levels off their plan" if findings else \
        "every named landform within its planned size, every level held"
    return checks.Verdict("scale", checks.FAIL if findings else checks.PASS, reason,
                          {"faults": len(findings)}, {"faults": "lower"}, tuple(findings))


def judge_slope(output, inputs, evidence):
    """Fail on a held flat, a path or a level seat steeper than its limit (measures.py)."""
    plans = plans_of(inputs)
    findings, steepest = [], {}
    for name, made in grounds_of(output).items():
        found = measures.slope(made, plans[name], inputs)
        steepest[f"{name} flats max"] = found["flats_max"]
        findings += [f"{name}: {fault}" for fault in found["faults"]]
    reason = "; ".join(findings) if findings else "every flat and seat level, every path walkable"
    return checks.Verdict("slope", checks.FAIL if findings else checks.PASS, reason,
                          {"faults": len(findings), **steepest}, {"faults": "lower"}, tuple(findings))


def old_ground(grounds, plan_record, place, on_seat):
    """The old ground's height under spots of the place: the copied ground record's (in the `grounds` folder) on a
    ball, the old disc's level on the Earth."""
    copied = plan_record["copied"]
    if "disc" in copied:
        level = copied["disc"]["levels"][place]
        return lambda spots: np.full(len(np.atleast_2d(spots)), level)
    folder = pathlib.Path(grounds)
    old = {**json.loads((folder / copied["record"]).read_text()), "folder": str(folder)}
    if place not in old["places"]:
        return lambda spots: np.full(len(np.atleast_2d(spots)), -np.inf)  # it stood on no ground before
    laid = outside.placed_ground(old, old["places"][place], on_seat)
    return lambda spots: heights_under(laid, spots)


def ball_of(laid):
    """The world's middle and radius in a place's frame, for a small world; None for the Earth."""
    if laid.radius > outside.HORIZON:
        return None
    return laid.in_place_frame(np.zeros(3))[0], laid.radius - outside.BALL_BELOW


CHECKS = (checks.Check("scale", judge_scale), checks.Check("slope", judge_slope))
