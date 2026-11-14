"""A roof piece laid on its holder's top is part of that holder's roof: fixed to it where it meets it, never a loose
thing that must rest on its own weight. A row is one when the design names it a roof or an opening (its inventory
`part`, ROOF_PARTS) and the scene record lays every object of it on its holder's top (on_tops.laid_on_tops). It is
judged fixed (the triage's `fixed` support: as laid, floating only when it touches nothing, and sinking), and it is
let straight down onto the holder's surface it spans, by the least gap between the two, never slid across the top
for a spot where its own weight would hold it.

assembly@base, 2026-11-12: its glass pyramid roof on the central hub (an 8.5 m pyramid over the hub's domed
top) and its hangar roof opening on the large hangar (a slab with a fin hanging 2.7 m under it into the
hangar's open middle) were judged standing (`held`): laid at the hub's and the hangar's box top, they floated 0.26
and 2.98 m over the surface under them, and no spot of either top held their weight.

A thing the scene record says is attached on its holder's top (its `rests`, holders: a fitting on a run, a part
the plan draws over its holder's footprint) is let down so too: it is fixed to its holder already (mounted.
resting_as_laid), and no spot of a top need hold its weight. assembly@workshop, 2026-11-14: its lamp, the robotic arm's
head, was left at the arm's box top and floated 0.24 m over the arm under it.

    roofs(rows, record)          {row id: "fixed"} of the inventory `rows` that are roof pieces on their holder's top
    attached(record)             {row ids} of the scene record's rows whose every object is attached on its
                                 holder's top
    gap(own, holders)            the least gap, metres, straight down from a thing's surface to its holders' surface
                                 (and up from theirs to its), inf where none is under it
    downs(stage, place, record, rows, boxes)   {name: metres} each roof piece or attached thing more than TOLERANCE
                                        over its holders (an attached thing's: also what is laid under it) is let down
    laid_under(name, boxes)      the things laid under a thing's footprint, below its bottom
    let_down(folder, place, rows)       each such piece of the place at `folder` moved down with what it holds; the
                                        fits [{name, how "roofed", ..., "top at"}], laid.json written again
"""
import json
import pathlib

import numpy as np

from score.stages.assembly import BASE_LAYER, RECORD, fitting, made_waiting, on_ground, on_tops, parting

# The inventory parts (reading.PARTS) of a piece of its holder's roof: the roof itself, an opening in it.
ROOF_PARTS = ("roof", "opening")
# How far, metres, a roof piece is left over its holder where they are nearest: crest_tops' clear.
CLEAR = 0.005
# How many points of each surface, beside its vertices, its gap is read at.
SAMPLES = 40000


def roofs(rows, record):
    """{row id: "fixed"} of the inventory `rows` ([row]) whose part is a roof piece (ROOF_PARTS) and every object of
    which the scene `record` lays on its holder's top."""
    topped = on_tops.laid_on_tops(record or {})
    return {row["id"]: "fixed" for row in rows or [] if row.get("part") in ROOF_PARTS and row["id"] in topped}


def attached(record):
    """The row ids of the scene `record` whose every object it lays on its holder's top and says is attached to it
    (its `rests`, holders.ATTACHED)."""
    rows = {}
    for entry in (record or {}).get("objects") or []:
        rows.setdefault(entry["row"], []).append((entry.get("on") or {}).get("how") == "top"
                                                 and entry.get("rests") == "attached")
    return {row_id for row_id, fixed in rows.items() if all(fixed)}


def gap(own, holders):
    """The least gap (metres) between the mesh `own` and the mesh `holders` under it, straight down from its surface
    points and straight up from theirs within its footprint; inf where nothing of either meets the other."""
    down = np.array([0.0, -1.0, 0.0])
    points = np.vstack([own.vertices, own.sample(SAMPLES, seed=0)])
    found, rays, _ = holders.ray.intersects_location(points, np.tile(down, (len(points), 1)), multiple_hits=False)
    gaps = [points[rays, 1] - found[:, 1]]
    low, high = own.bounds
    under = np.vstack([holders.vertices, holders.sample(SAMPLES, seed=1)])
    under = under[np.all((under[:, [0, 2]] >= low[[0, 2]]) & (under[:, [0, 2]] <= high[[0, 2]]), axis=1)]
    if len(under):
        found, rays, _ = own.ray.intersects_location(under, np.tile(-down, (len(under), 1)), multiple_hits=False)
        gaps.append(found[:, 1] - under[rays, 1])
    gaps = np.concatenate(gaps)
    return float(gaps.min()) if len(gaps) else float("inf")


def downs(stage, place, record, rows, boxes=None):
    """{name: metres} each roof piece (roofs) and each thing attached on its holder's top (attached) is let down by:
    its gap to its holders less CLEAR, where that gap is over TOLERANCE. An attached thing's holders are its record's
    and every thing laid under its footprint (`boxes`, laid.json's {name: {low, high}}): one the laying already stood
    on another (hangar's valves packed onto the pipe over theirs) is not let down through it."""
    import trimesh
    roofed, fixed = roofs(rows, record), attached(record)
    found = {}
    for entry in record.get("objects") or []:
        if entry["row"] not in {**roofed, **dict.fromkeys(fixed)} or \
                not stage.GetPrimAtPath(f"/{place}/Objects/{entry['name']}"):
            continue
        own = fitting.surface_mesh(stage, f"/{place}/Objects/{entry['name']}")
        under = laid_under(entry["name"], boxes or {}) if entry["row"] in fixed and entry["row"] not in roofed else []
        meshes = [mesh for mesh in (fitting.surface_mesh(stage, f"/{place}/Objects/{holder}")
                                    for holder in dict.fromkeys([*(entry["on"].get("holder") or []), *under])
                                    if stage.GetPrimAtPath(f"/{place}/Objects/{holder}")) if mesh is not None]
        if own is None or not meshes:
            continue
        between = gap(own, trimesh.util.concatenate(meshes))
        if on_ground.TOLERANCE < between < np.inf:
            found[entry["name"]] = between - CLEAR
    return found


def laid_under(name, boxes):
    """The names of the things laid (`boxes`, {name: {low, high}}) whose box meets the footprint of `name`'s and
    starts below its bottom."""
    own = boxes.get(name)
    if own is None:
        return []
    low, high = own["low"], own["high"]
    return [other for other, box in boxes.items() if other != name and box["low"][1] < low[1]
            and box["low"][0] <= high[0] and box["high"][0] >= low[0] and box["low"][2] <= high[2]
            and box["high"][2] >= low[2]]


def let_down(folder, place, rows=None):
    """Each roof piece and attached thing of the place at `folder` (by the inventory `rows` and its record) moved down
    onto its holders (downs), what it holds moved with it; the base layer saved and laid.json's boxes and fits written
    again, the piece's fit its "top at" (the held gate measures it there). The fits, [] and nothing written when none
    moves."""
    from pxr import Gf, Sdf, Usd
    folder = pathlib.Path(folder)
    laid_path, record_path = folder / made_waiting.LAID, folder / RECORD
    if not rows or not laid_path.exists() or not record_path.exists():
        return []
    laid, record = json.loads(laid_path.read_text()), json.loads(record_path.read_text())
    stage = Usd.Stage.Open(str(folder / f"{place}.usda"))
    layer = Sdf.Layer.FindOrOpen(str(folder / BASE_LAYER))
    stage.SetEditTarget(Usd.EditTarget(layer))
    entries = {entry["name"]: entry for entry in record.get("objects") or []}
    holding = fitting.holders_of(record)
    fits, roofed = [], roofs(rows, record)
    boxes = {entry["name"]: entry for entry in laid.get("objects") or [] if "low" in entry and "high" in entry}
    for name, drop in sorted(downs(stage, place, record, rows, boxes).items()):
        onto = "whose roof it is" if entries[name]["row"] in roofed else "it is attached to"
        held = [other for other in parting.carried(name, holding)
                if other in entries and stage.GetPrimAtPath(f"/{place}/Objects/{other}")]
        for one in (name, *held):
            path = f"/{place}/Objects/{one}"
            fitting.changed_by(stage.GetPrimAtPath(path), Gf.Matrix4d(on_ground.moved([0.0, -drop, 0.0]).tolist()))
            fit = fitting.laid_fit(stage, path, entries[one], "roofed", None, drop, 1.0,
                                   f"let down {drop:.2f} m onto the holder {onto}"
                                   + ("" if one == name else f" with {name}, which holds it"))
            fits.append({**fit, "top at": fit["low"][1]} if one == name else fit)
    if not fits:
        return []
    layer.Save()
    moved = {fit["name"]: fit for fit in fits}
    laid["objects"] = [{**entry, "low": moved[entry["name"]]["low"], "high": moved[entry["name"]]["high"],
                        **({"corners": [[round(float(value), 4) for value in point] for point in
                                        fitting.oriented_corners(stage, f"/{place}/Objects/{entry['name']}")]}
                           if "corners" in entry else {})}
                       if entry["name"] in moved else entry for entry in laid.get("objects", [])]
    laid["fitted"] = [*laid.get("fitted", []), *fits]
    laid_path.write_text(json.dumps(laid, indent=1))
    return fits
