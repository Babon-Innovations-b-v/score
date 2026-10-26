"""The terrain stage's gates, measured on the grounds it drew:

    spots      the ground drawn (each source place's fine patch) passes within SPOT_WITHIN of every terrain spot of the
               plans standing on it
    curve      at the far edge of every place's coarse ground the ground has fallen by the body's true curve (its
               radius's sagitta) within CURVE_WITHIN of it, or stays level on a plot

and the measures ground-fit@<place> (fit.py) takes on a place's own stage standing on its made ground: rays down
(`drops`), what stands on it (`object_boxes`) and its openings (`measure_openings`, from its scene record's doorways
and views). The `measure_*` functions take any place stage.
"""
import json
import math
import pathlib

import numpy as np
from pxr import Usd, UsdGeom

from score import checks
import score.stages.terrain.design as design  # by module: terrain's make (its __init__) stays out of the key
import score.stages.terrain.sight as sight

# A spot's ground within this of its planned height (metres): the fine patch's step bends the spline no more.
SPOT_WITHIN = 0.05
# The far edge's fall within this share of the body's sagitta there, or this many metres, whichever is more.
CURVE_SHARE = 0.01
CURVE_WITHIN = 0.05
# A doorway opens onto a floor when one lies within this below its sill, this far out from the doorway each side.
DOOR_DROP = 0.6
DOOR_OUT = 0.6
# A probe stands inside when a floor lies within this below it.
PROBE_FLOOR = 2.0
PROBE_HEIGHT = 1.6
PROBE_GRID = 5
HIGH = 1000.0  # a ray down starts this far over a spot


# --- rays ---------------------------------------------------------------------------------------------------------

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


def heights(rays, spots):
    """The surface's height straight under each spot [[x, z]] (nan where none)."""
    spots = np.atleast_2d(spots)
    origins = np.column_stack([spots[:, 0], np.full(len(spots), HIGH), spots[:, 1]])
    return HIGH - drops(rays, origins, [0.0, -1.0, 0.0])


# --- the place's doorways and views ----------------------------------------------------------------------------------

def footprint(record):
    """The place's own box (across, along): its scene record's floor."""
    return np.asarray(record["floor"][0], dtype=float), np.asarray(record["floor"][1], dtype=float)


def record_doors(record):
    """Every doorway of the scene record (its plan's doorways): its middle on its sill and its way out."""
    return [{"door": door["name"], "middle": np.asarray(door["middle"], dtype=float),
             "normal": -np.asarray(door["inward"], dtype=float)} for door in record.get("doorways", [])]


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


def probes(rays, record, up):
    """Where a viewer stands: the scene record's view eyes and a grid over the place's own box at eye height, each
    kept only over a floor within PROBE_FLOOR."""
    low, high = footprint(record)
    grid = [[across, PROBE_HEIGHT, along] for across in np.linspace(low[0] + 0.4, high[0] - 0.4, PROBE_GRID)
            for along in np.linspace(low[1] + 0.4, high[1] - 0.4, PROBE_GRID)]
    spots = np.array([view["eye"] for view in record.get("views", [])] + grid, dtype=float)
    floor = drops(rays, spots, -np.asarray(up, dtype=float))
    return spots[floor <= PROBE_FLOOR]


def measure_openings(stage, place, record, ball=None, up=(0.0, 1.0, 0.0)):
    """A place stage's openings: every doorway's floors and the void rays from inside, from its scene record's
    doorways and views; `ball` the world's middle and radius in the place's frame on a body (its horizon dips)."""
    seen = sight.gathered(stage)
    rays = caster(seen)
    doors = door_floors(rays, record_doors(record), up)
    viewed = sight.voids(seen, probes(rays, record, up), up, ball=ball)
    return {"doors": doors, "doors_onto_nothing": sum(door["open_onto_nothing"] for door in doors),
            "void_rays": viewed["void"], "rays": viewed["rays"], "void_share": round(viewed["share"], 6),
            "probes": len(viewed["probes"]), "worst_probe": viewed["worst"]}


# --- objects on the ground ---------------------------------------------------------------------------------------------

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


def footprint_spots(low, high):
    """Nine spots over an object's footprint (its corners, edges' middles and middle)."""
    return np.array([[across, along] for across in np.linspace(low[0], high[0], 3)
                     for along in np.linspace(low[2], high[2], 3)])


# --- the gates ----------------------------------------------------------------------------------------------------

def mesh_caster(points, triangles):
    import trimesh
    return caster(trimesh.Trimesh(points, triangles, process=False))


def spot_faults(ground, laid):
    """Each source's spots against the ground drawn in its own place's fine patch: (measured, faults)."""
    measured, faults = [], []
    for source in ground["sources"]:
        place, entry = source["place"], ground["places"][source["place"]]
        rays = mesh_caster(*laid[place]["near"])
        for x, y, height in source["spots"]:
            spot = spot_in_frame(ground, place, x, y)
            found = float(heights(rays, [spot])[0])
            off = abs(found - (entry["floor"] + height))
            measured.append({"place": place, "spot": [x, y, height], "ground": round(found - entry["floor"], 3)})
            if not math.isfinite(found) or off > SPOT_WITHIN:
                faults.append(f"{place}: the ground at its spot ({x:g}, {y:g}) stands {found - entry['floor']:.2f} m, "
                              f"its plan says {height:g} m")
    return measured, faults


def spot_in_frame(ground, place, x, y):
    """A plan point of a place as [x, z] of its frame."""
    entry = ground["places"][place]
    origin, axes = np.asarray(entry["origin"], dtype=float), np.asarray(entry["axes"], dtype=float)
    top = ground["tops"][entry["top"]]
    hold = next((source["offset"] for source in ground["sources"] if source["place"] == place), [0.0, 0.0])
    world = design.tangent(top, [[x + hold[0], y + hold[1]]])[0]
    return ((world - origin) @ axes)[[0, 2]]


def curve_faults(ground, laid):
    """Each place's coarse ground at its far edge against the body's true fall there, from its top scene's site
    (where its floor touches the sphere): (measured, faults)."""
    measured, faults = [], []
    for place, found in laid.items():
        points, triangles = found["far"]
        entry = ground["places"][place]
        site = np.asarray(ground["tops"][entry["top"]]["middle"], dtype=float)
        middle = ((site - np.asarray(entry["origin"])) @ np.asarray(entry["axes"]))[[0, 2]]
        corner = int(np.argmax(np.hypot(points[:, 0] - middle[0], points[:, 2] - middle[1])))
        fall = entry["floor"] - float(points[corner, 1])
        distance = float(np.hypot(*(points[corner, [0, 2]] - middle)))
        wanted = ground["radius"] - math.sqrt(ground["radius"] ** 2 - distance ** 2) if ground["kind"] == "body" else 0.0
        measured.append({"place": place, "distance": round(distance, 1), "fall": round(fall, 3),
                         "true fall": round(wanted, 3)})
        if abs(fall - wanted) > max(CURVE_WITHIN, CURVE_SHARE * wanted):
            faults.append(f"{place}: the ground {distance:.0f} m out has fallen {fall:.2f} m, the body's curve "
                          f"{wanted:.2f} m")
    return measured, faults


def measured(ground, laid):
    """The ground's measures: {"spots": {measured, faults}, "curve": {measured, faults}}."""
    spots, spot_faults_found = spot_faults(ground, laid)
    curve, curve_faults_found = curve_faults(ground, laid)
    return {"spots": {"measured": spots, "faults": spot_faults_found},
            "curve": {"measured": curve, "faults": curve_faults_found}}


def grounds_of(output):
    """Every made ground's measures in the output: {name: measures}."""
    return {folder.name: json.loads((folder / "measures.json").read_text())
            for folder in sorted(pathlib.Path(output).iterdir()) if (folder / "ground.json").exists()}


def judge(name, sentence):
    """A gate on one measure of every ground: fail on any fault, else pass with `sentence`."""
    def judged(output, inputs, evidence):
        found = {ground: measures[name] for ground, measures in grounds_of(output).items()}
        faults = [fault for measures in found.values() for fault in measures["faults"]]
        count = sum(len(measures["measured"]) for measures in found.values())
        return checks.Verdict(name, checks.FAIL if faults else checks.PASS,
                              "; ".join(faults[:3]) if faults else sentence.format(count=count),
                              {"faults": len(faults), "measured": count}, {"faults": "lower"}, tuple(faults))
    judged.__name__ = f"judge_{name}"
    return judged


CHECKS = (checks.Check("spots", judge("spots", "the ground passes through all {count} terrain spots of the plans")),
          checks.Check("curve", judge("curve", "every place's ground falls with its body's true curve ({count} "
                                               "places)")))
