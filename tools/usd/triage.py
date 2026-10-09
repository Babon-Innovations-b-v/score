"""The resting triage: every resting fault of a place's OpenUSD stage judged by what holds the object up, real faults
kept apart from false alarms, and the real ones grouped by cause with one close-up each.

    .venv/bin/python tools/usd/triage.py <stage.usda> [--settled <settle/settled.json>] [--out <triage.json>]
                                         [--closeups <folder> [--cloud]]

The resting check (resting.py) asks one question of every object: does it stand on what is under it. On a big place
most of what it flags is not wrong (the hangar: 865 of 1,686 objects): a wall panel of a kit stands where the kit's
frame lays it, a cable is meant to bed into its skirting, a crate stands on a deck the scene record built. The triage
asks each object the question its support asks:

    support   from the inventory row as data, never guessed: `support` when the row says it; `part` for a kit piece's
              glowing part or screen (judged with its host); `fixed` (a building, a mast) when `"fixed": true`; `kit`
              (fixed in the kit's frame) when its row's group is one of the kit's shell groups or its kit kind's group
              is `hangs` or `floors`; `hanging` when its name says it hangs; `held` when it stands on another row
              (`on:<row>`); `wall` and `ceiling` from its anchor; `floor` otherwise (data/checks/resting.json).
    floor, held  supported by the ground, the deck or the object under it: at least four points of its footing within
              TOLERANCE of a surface straight under them, and its weight inside what they span (SceneEval's support
              rule); else it floats or tips. Sunk below its contact points past TOLERANCE, unless its class may bed in.
    wall, ceiling, hanging  supported by touching anything (SceneEval: one contact): one that touches nothing hangs free.
    kit, fixed  stand as laid; a fixed one is still judged for floating (unless joined to another piece) and sinking, a
              kit piece only for lying inside a loose one.
    overlap   two objects, at least one loose, whose surfaces meet (FCL's collision set, collide.py) and one lies inside
              the other deeper than TOLERANCE (or than its bedding class allows); counted only if they still meet after
              the loose one is nudged NUDGE away from the other (SceneEval's false-positive guard).
    drop      when a settle run's result is given (settle.py --dry-run writes settle/settled.json): a loose object that
              moves more than settle.SAGE_MOVE or turns more than settle.SAGE_TURN when dropped does not rest as laid
              (SAGE's stability rule) and is a real fault whatever else it passes.

Every fault the plain resting check would raise is kept, marked real or false with why, so the counts can be compared.
Real faults are grouped by cause (model, kind of fault, size band), the largest group first, each with the worst case's
measure in millimetres and, with --closeups, one close-up picture aimed at it (the object and what it meets, nothing
else drawn, from a camera the tool sets: annotate.py). The guards are copied from SceneEval (Tam et al., arXiv
2503.14756, github.com/3dlg-hcvc/SceneEval, MIT: metrics/support.py and metrics/collision.py) and the drop rule from
SAGE (NVlabs, arXiv 2602.10116, github.com/NVlabs/sage, Apache-2.0); the code is ours.
"""
import argparse
import json
import math
import pathlib
import sys

import numpy as np
import trimesh
from pxr import Usd, UsdGeom

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
import collide  # noqa: E402
import resting  # noqa: E402

RULES = REPO / "data/checks/resting.json"
TOLERANCE = resting.TOLERANCE
BALANCE = resting.BALANCE
# SceneEval's support rule: a thing standing on the ground or on an object needs this many contact points.
CONTACTS_NEEDED = 4
# SceneEval's collision guard: an overlap counts only if it survives moving the object this far away (metres).
NUDGE = 0.005
# How many of an object's points near its bottom look down for a support, and how many surface samples join its
# vertices.
LOW_POINTS = 600
OWN_SAMPLES = 4000
# How far over an object's lowest point its footing is looked for (metres): a base tilted by the ground's slope or a
# settle still touches with all its feet.
LOW_BAND = 0.1
RAY_START = resting.RAY_START
# The size bands a group of faults is cut by (metres): under 1 cm, 1 to 5, 5 to 20, 20 to 100, over a metre.
BANDS = (0.01, 0.05, 0.2, 1.0)
# Only a piece standing loose on the floor is dropped (settle.py's loose pieces); SAGE's rule judges no other.
DROPPED = ("floor",)
LOOSE = ("floor", "held", "wall", "ceiling", "hanging")  # "part": a kit piece's glowing part, judged with its host
STATIC_GROUPS = ("Structure", "Fixtures")


# --- reading the stage ------------------------------------------------------------------------------------------

def rules():
    """The triage's data (data/checks/resting.json)."""
    return json.loads(RULES.read_text())


def words_of(row):
    """A row's id and name as a set of lower-case words."""
    text = f"{row.get('id', '')} {row.get('name', '')}".lower().replace("_", " ")
    return set("".join(letter if letter.isalnum() else " " for letter in text).split())


def support_type(row, prim, data, kit_groups):
    """What holds an object up, from its inventory row and its kit kind's group (and the stage's score:fixed when the
    row is not found)."""
    if row.get("support"):
        return row["support"]
    row_id = prim.GetAttribute("score:row").Get() if prim.HasAttribute("score:row") else ""
    if any(row_id.endswith(suffix) for suffix in data["parts"]):
        return "part"
    if row.get("fixed") or (prim.HasAttribute("score:fixed") and prim.GetAttribute("score:fixed").Get()):
        return "fixed"
    kind = prim.GetAttribute("score:kind").Get() if prim.HasAttribute("score:kind") else None
    if row.get("group") in data["fixed_in_kit"] or kit_groups.get(kind) in data["fixed_in_kit_kinds"]:
        return "kit"
    anchor = row.get("anchor") or (prim.GetAttribute("score:anchor").Get() if prim.HasAttribute("score:anchor") else "")
    if words_of(row) & set(data["hanging"]):
        return "hanging"
    if anchor.startswith("on:"):
        return "held"
    if anchor == "wall":
        return "wall"
    if anchor in ("ceiling", "roof"):
        return "ceiling"
    return "floor"


def bedding(row, data):
    """How deep a row's class may bed into what it lies on, and the class; (0, None) for most."""
    found = [(entry["depth"], entry["class"]) for entry in data["may_bed"] if words_of(row) & set(entry["words"])]
    return max(found) if found else (0.0, None)


def static_meshes(stage, place):
    """The meshes the scene record built that things stand on or against: {path: trimesh in the stage's frame}."""
    found = {}
    for group in STATIC_GROUPS:
        root = stage.GetPrimAtPath(f"/{place}/{group}")
        if not root.IsValid():
            continue
        for prim in Usd.PrimRange(root):
            if prim.IsA(UsdGeom.Mesh) and UsdGeom.Imageable(prim).ComputeVisibility() != UsdGeom.Tokens.invisible:
                points, triangles = resting.in_stage(prim)
                if len(triangles):
                    found[str(prim.GetPath())] = trimesh.Trimesh(points, triangles, process=False)
    return found


def object_entry(name, prim, rows, data, kit_groups):
    """One laid object: its mesh in the stage's frame, its local mesh and matrix, its row and how it is held up."""
    geo = prim.GetChild("geo")
    mesh = UsdGeom.Mesh(geo)
    local = np.asarray(mesh.GetPointsAttr().Get(), dtype=np.float64)
    triangles = np.asarray(mesh.GetFaceVertexIndicesAttr().Get()).reshape(-1, 3)
    matrix = np.asarray(UsdGeom.Xformable(geo).ComputeLocalToWorldTransform(Usd.TimeCode.Default())).T
    row = rows.get(prim.GetAttribute("score:row").Get(), {})
    model = prim.GetAttribute("score:model").Get() if prim.HasAttribute("score:model") else None
    world = trimesh.Trimesh(local @ matrix[:3, :3].T + matrix[:3, 3], triangles, process=False)
    return {"name": name, "prim": prim, "row": row, "row_id": prim.GetAttribute("score:row").Get(), "model": model,
            "local": local, "triangles": triangles, "matrix": matrix, "mesh": world,
            "support": support_type(row, prim, data, kit_groups), "bed": bedding(row, data)}


def object_sizes(stage_path):
    """Each laid object's largest side in metres, by prim path, from the stage's own bounds."""
    stage = Usd.Stage.Open(str(stage_path))
    cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render])
    place = stage.GetDefaultPrim().GetName()
    return {path: float(max(cache.ComputeWorldBound(prim).ComputeAlignedRange().GetSize()))
            for path, prim in resting.objects_of(stage, place).items()}


def kit_groups(place):
    """{kit kind: its group} of the place's kit (data/kit/<place>.json), empty when it has none."""
    path = REPO / "data/kit" / f"{place}.json"
    kinds = json.loads(path.read_text()).get("kinds", {}) if path.exists() else {}
    return {kind: entry.get("group") for kind, entry in kinds.items()}


def inventory_rows(place, stage_path):
    """The place's inventory rows by id: the one the stage was exported from (complete.py), else none."""
    import complete
    path = complete.recorded_inventory(place, stage_path)
    return {row["id"]: row for row in json.loads(path.read_text())["rows"]} if path.exists() else {}


# --- the ray mesh: every surface, each face knowing whose it is --------------------------------------------------

class Surfaces:
    """Every object's and static mesh's triangles in one mesh for rays, each face knowing which it belongs to."""

    def __init__(self, meshes):
        self.names = list(meshes)
        joined = [meshes[name] for name in self.names]
        self.owner = np.concatenate([np.full(len(mesh.faces), index) for index, mesh in enumerate(joined)])
        self.mesh = trimesh.util.concatenate(joined)
        self.rays = trimesh.ray.ray_triangle.RayMeshIntersector(self.mesh)
        self.cache = None

    def hits_below(self, points):
        """Every surface straight under each point (rays down from RAY_START over it): (ray, owner, gap) arrays."""
        origins = points + [0.0, RAY_START, 0.0]
        hits, rays, faces = self.rays.intersects_location(origins, np.tile([0.0, -1.0, 0.0], (len(origins), 1)),
                                                          multiple_hits=True)
        return rays, self.owner[faces], origins[rays, 1] - hits[:, 1] - RAY_START

    def gaps_below(self, points, left_out):
        """How far each point stands over the first surface straight under it that is not one of the left-out owners
        (inf where nothing is under it)."""
        if self.cache is None or self.cache[0] is not points:
            self.cache = (points, self.hits_below(points))
        rays, owners, gaps_found = self.cache[1]
        keep = ~np.isin(owners, list(left_out))
        gaps = np.full(len(points), np.inf)
        np.minimum.at(gaps, rays[keep], gaps_found[keep])
        return gaps


# --- judging one object -----------------------------------------------------------------------------------------

def low_points(mesh):
    """An object's points near its bottom (within LOW_BAND of its lowest), of its vertices and a sample of its
    surface, at most LOW_POINTS of them spread over that band: its whole footing, not only its lowest corner."""
    points = np.vstack([np.asarray(mesh.vertices), mesh.sample(OWN_SAMPLES, seed=0)]) if mesh.area > 0 else \
        np.asarray(mesh.vertices)
    low = points[points[:, 1] <= points[:, 1].min() + LOW_BAND]
    if len(low) > LOW_POINTS:
        low = low[np.random.default_rng(0).choice(len(low), LOW_POINTS, replace=False)]
    return low


def standing(entry, ground, surfaces, left_out, statics):
    """How a floor or held object stands: its gap (with and without the scene record's decks and fixtures), how many
    points touch, how far its weight falls outside them, how deep it lies under the ground."""
    points = low_points(entry["mesh"])
    clearance = points[:, 1] - ground(points[:, [0, 2]])
    known = np.isfinite(clearance)
    on_ground = np.where(known, np.maximum(np.where(known, clearance, 0.0), 0.0), np.inf)
    gaps = surfaces.gaps_below(points, left_out)
    plain = surfaces.gaps_below(points, left_out | statics)
    best = np.minimum(on_ground, gaps)
    touching = best <= TOLERANCE
    return {"gap": float(best.min()), "plain_gap": float(np.minimum(on_ground, plain).min()),
            "contacts": int(touching.sum()),
            "outside": resting.outside_by(resting.weight_at(entry["mesh"]), points[touching][:, [0, 2]]),
            "depth": max(0.0, -float(np.nanmin(clearance[known]))) if known.any() else 0.0,
            "lowest": points[np.argmin(points[:, 1])]}


def fault(entry, kind, measure, real, why, point, partner=None):
    """One fault of one object."""
    return {"object": entry["name"], "row": entry["row_id"], "model": entry["model"], "support": entry["support"],
            "kind": kind, "measure": round(float(measure), 4) if np.isfinite(measure) else None, "partner": partner,
            "point": [round(float(value), 3) for value in point], "real": real, "why": why}


def kit_faults(entry, found):
    """A kit piece stands where the kit's frame lays it: what the plain check would say of it, as false alarms."""
    if found["plain_gap"] > TOLERANCE:
        return [fault(entry, "floats", found["plain_gap"], False, "a kit piece stands where the kit's frame lays it",
                      found["lowest"])]
    if found["depth"] > TOLERANCE:
        return [fault(entry, "sunk", found["depth"], False, "a kit piece stands where the kit's frame lays it",
                      found["lowest"])]
    return []


def held_up_faults(entry, found):
    """A floor, held or fixed object: floating (false when the scene record's deck holds it), too few contacts or its
    weight outside them (not for a fixed one)."""
    support = entry["support"]
    if found["gap"] > TOLERANCE:
        return [fault(entry, "floats", found["gap"], True, "nothing under it within the tolerance", found["lowest"])]
    faults = []
    if found["plain_gap"] > TOLERANCE:
        faults.append(fault(entry, "floats", found["plain_gap"], False,
                            "stands on a deck or fixture the scene record built", found["lowest"]))
    if support == "fixed":
        return faults
    if found["contacts"] < CONTACTS_NEEDED:
        faults.append(fault(entry, "tips", found["contacts"], True,
                            f"touches what is under it at {found['contacts']} points (needs {CONTACTS_NEEDED})",
                            found["lowest"]))
    elif found["outside"] > BALANCE:
        faults.append(fault(entry, "tips", found["outside"], True, "its weight falls outside what it touches",
                            entry["mesh"].bounds.mean(axis=0)))
    return faults


def sunk_faults(entry, found):
    """A floor or fixed object deeper under the ground than its contact points, unless its class may bed in."""
    if found["depth"] <= TOLERANCE:
        return []
    allowed, kind = entry["bed"]
    if found["depth"] <= TOLERANCE + allowed:
        return [fault(entry, "sunk", found["depth"], False, f"a {kind} may bed in {allowed * 100:.0f} cm",
                      found["lowest"])]
    return [fault(entry, "sunk", found["depth"], True, "below its own contact points", found["lowest"])]


def standing_faults(entry, ground, surfaces, left_out, statics):
    """The floating, tipping and sinking faults of one object, each real or false by its support. A piece on a wall
    or ceiling, or hanging, is judged by touching something instead (Scene.touches), as the plain check never judged
    it standing."""
    support = entry["support"]
    if support in ("wall", "ceiling", "hanging"):
        return []
    found = standing(entry, ground, surfaces, left_out, statics)
    if support == "part":
        return [dict(item, why="a glowing part is judged with its host") for item in kit_faults(entry, found)]
    if support == "kit":
        return kit_faults(entry, found)
    faults = held_up_faults(entry, found)
    if support in ("floor", "fixed"):
        faults += sunk_faults(entry, found)
    return faults


def joined_up(item, scene):
    """A fixed piece that floats over the ground but is joined to another piece (a walkway tube held between two
    modules at its ends) is held by that join: a false alarm."""
    if item["support"] == "fixed" and item["kind"] == "floats" and item["real"] and scene.touches(item["object"],
                                                                                               TOLERANCE):
        return dict(item, real=False, why="a fixed piece held by what it is joined to")
    return item


# --- overlaps ---------------------------------------------------------------------------------------------------

def nudge_way(entry, other_mesh):
    """The way from the other object's middle to this one's, as a unit vector (up when they share a middle)."""
    way = entry["mesh"].bounds.mean(axis=0) - other_mesh.bounds.mean(axis=0)
    length = np.linalg.norm(way)
    return way / length if length > 1e-9 else np.array([0.0, 1.0, 0.0])


def overlap_faults(entries, statics, scene):
    """Every pair, at least one loose, whose surfaces meet with one inside the other past TOLERANCE: each a fault
    on the loose one(s), real only if it survives the nudge and its bedding allowance. Kit pieces joined to each other
    or to the scene record's shell are kept as false alarms (the plain check raised them)."""
    faults = []
    for first, second in sorted(scene.collision_set()):
        one, other = entries.get(first), entries.get(second)
        if one is not None and other is not None and (second.startswith(first + "/") or first.startswith(second + "/")):
            continue
        loose = [entry for entry in (one, other) if entry is not None and entry["support"] in LOOSE]
        joined = [entry for entry in (one, other) if entry is not None and entry["support"] == "kit"]
        if not loose and not joined:
            continue
        first_mesh = one["mesh"] if one is not None else statics[first]
        second_mesh = other["mesh"] if other is not None else statics[second]
        depth = max(resting.overlap_depth(first_mesh, second_mesh), resting.overlap_depth(second_mesh, first_mesh))
        if depth <= TOLERANCE:
            continue
        if not loose:  # kit pieces joined in the kit's frame (a skirting into a door frame): the plain check's alarm
            faults += [fault(entry, "overlaps", depth, False, "kit pieces joined in the kit's frame",
                             entry["mesh"].bounds.mean(axis=0), second if entry is one else first) for entry in joined]
            continue
        for entry in loose:
            partner = second if entry is one else first
            partner_mesh = second_mesh if entry is one else first_mesh
            allowed, kind = entry["bed"]
            if depth <= TOLERANCE + allowed:
                real, why = False, f"a {kind} may bed in {allowed * 100:.0f} cm"
            elif not scene.intersection_test(entry["name"], partner, nudge_way(entry, partner_mesh) * NUDGE):
                real, why = False, f"clears after a {NUDGE * 1000:.0f} mm nudge (a touch, not an overlap)"
            else:
                real, why = True, "still inside after the nudge"
            point = trimesh.bounds.corners(np.array([np.maximum(first_mesh.bounds[0], second_mesh.bounds[0]),
                                                     np.minimum(first_mesh.bounds[1], second_mesh.bounds[1])]))
            faults.append(fault(entry, "overlaps", depth, real, why, point.mean(axis=0), partner))
    return faults


# --- the drop -----------------------------------------------------------------------------------------------------

def drop_faults(entries, settled):
    """SAGE's rule on a settle run's result: every loose object that moves or turns too far when dropped."""
    import settle
    faults = []
    for name, found in sorted(settled.get("objects", {}).items()):
        path = next((path for path in entries if path.endswith(f"/Objects/{name}")), None)
        if path is None or found.get("moving", 0.0) > settle.STILL:
            continue
        entry = entries[path]
        if entry["support"] not in DROPPED:  # a drop run made before its row's support was known: not loose
            continue
        before = entry["matrix"]
        turned, moved = settle.correction({"before": before, "after": np.asarray(found["motion"]) @ before,
                                           "middle": entry["local"].mean(axis=0).tolist()})
        if settle.unstable(turned, moved):
            faults.append(fault(entry, "unstable", moved, True,
                                f"moves {moved:.2f} m and turns {turned:.0f} degrees when dropped (SAGE: over "
                                f"{settle.SAGE_MOVE} m or {settle.SAGE_TURN:.0f} degrees)",
                                entry["mesh"].bounds.mean(axis=0)))
    return faults


# --- the triage ---------------------------------------------------------------------------------------------------

def band(measure):
    """The size band a measure falls in, as words."""
    if measure is None:
        return "no measure"
    edges = (0.0, *BANDS, math.inf)
    for low, high in zip(edges, edges[1:]):
        if measure < high:
            return f"{low * 100:g} to {high * 100:g} cm" if high != math.inf else f"over {low * 100:g} cm"
    return "no measure"


def groups(faults):
    """Real faults grouped by cause (model, kind, size band), the largest group first, each with its worst case."""
    found = {}
    for item in faults:
        if not item["real"]:
            continue
        measure = item["measure"] if item["kind"] != "tips" or item["why"].startswith("its weight") else None
        key = (item["model"] or item["row"] or "", item["kind"], band(measure))
        found.setdefault(key, []).append(item)
    ordered = sorted(found.items(), key=lambda pair: (-len(pair[1]), pair[0]))
    return [{"model": model, "kind": kind, "band": size, "count": len(items),
             "worst": max(items, key=lambda item: item["measure"] or 0.0),
             "objects": [item["object"] for item in items]} for (model, kind, size), items in ordered]


def triage(stage_path, settled=None):
    """The triage of one stage: every fault, real or false, and the real ones grouped by cause."""
    stage = Usd.Stage.Open(str(stage_path))
    place = stage.GetDefaultPrim().GetName()
    data = rules()
    rows = inventory_rows(place, stage_path)
    groups_of = kit_groups(place)
    entries = {path: object_entry(path, prim, rows, data, groups_of)
               for path, prim in resting.objects_of(stage, place).items()}
    statics = static_meshes(stage, place)
    ground = resting.ground_height(stage, place)
    surfaces = Surfaces({**{path: entry["mesh"] for path, entry in entries.items()}, **statics})
    index = {name: number for number, name in enumerate(surfaces.names)}
    scene = collide.Scene()
    for path, entry in entries.items():
        scene.add(path, entry["model"] or path, entry["local"], entry["triangles"], entry["matrix"])
    for path, mesh in statics.items():
        scene.add(path, path, np.asarray(mesh.vertices), np.asarray(mesh.faces), np.eye(4))
    static_ids = {index[name] for name in statics}
    faults = []
    for path, entry in entries.items():
        left_out = {number for name, number in index.items() if name == path or name.startswith(path + "/")}
        found = [joined_up(item, scene) for item in standing_faults(entry, ground, surfaces, left_out, static_ids)]
        if entry["support"] in ("wall", "ceiling", "hanging") and not scene.touches(path, TOLERANCE):
            found.append(fault(entry, "hangs free", 0.0, True, f"a {entry['support']} piece touching nothing",
                               entry["mesh"].bounds.mean(axis=0)))
        faults += found
    faults += overlap_faults(entries, statics, scene)
    if settled is not None:
        faults += drop_faults(entries, settled)
    real = {item["object"] for item in faults if item["real"]}
    flagged = {item["object"] for item in faults}
    return {"place": place, "stage": str(stage_path), "objects": len(entries), "flagged": len(flagged),
            "real_objects": len(real), "false_objects": len(flagged - real), "faults": faults, "groups": groups(faults)}


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("stage", type=pathlib.Path)
    parser.add_argument("--settled", type=pathlib.Path, help="a settle run's settled.json (settle.py --dry-run)")
    parser.add_argument("--out", type=pathlib.Path)
    parser.add_argument("--closeups", type=pathlib.Path, help="render one close-up a group into this folder")
    parser.add_argument("--cloud", action="store_true", help="render the close-ups on a rented machine")
    options = parser.parse_args()
    found = triage(options.stage, json.loads(options.settled.read_text()) if options.settled else None)
    if options.closeups:
        import annotate
        annotate.fault_closeups(options.stage, found["groups"], options.closeups, options.cloud)
    if options.out:
        options.out.write_text(json.dumps(found, indent=1) + "\n")
    for group in found["groups"]:
        worst = group["worst"]
        print(f"{group['count']:4} {group['kind']:10} {group['band']:14} {group['model']}: worst {worst['object']} "
              f"({(worst['measure'] or 0) * 1000:.0f} mm; {worst['why']})")
    print(f"{found['objects']} objects, {found['flagged']} flagged: {found['real_objects']} real, "
          f"{found['false_objects']} false alarms")
    sys.exit(1 if found["real_objects"] else 0)


if __name__ == "__main__":
    main()
