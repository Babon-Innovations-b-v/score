"""A thing laid against its holder's side whose row the resting check judges standing, let straight down onto what is
under it (on the made ground's place, after on_ground.stood). The check judges a face thing by touching its holder
only when every object of its row is laid on a face (mounted.on_faces); a row whose other objects stand within their
holder is judged standing, and a face one of it the fitting laid up its holder's side (face_spots.met, clear of the
ones laid on the face before it) floats.

assembly@wreck, 2026-11-12: its five solar panels, one row on its lunar lander (two within it, three on its north
side): solar_panels_5, laid 0.41 m up the side to keep clear of solar_panels_4, floated 0.41 m over the ground.

A row the check judges mounted on a wall or ceiling row by its inventory (mounted.mounted, as resting_rows gives it) is
judged by touching, never standing, so its face things stay where the fitting laid them: tube's wall lamps, a row on
its structural ribs (structure_mounted; four within a rib, seven on a rib's side), were let down 1.3 to 2.2 m from 2 m
up their ribs, lamps 5 to 7 into the deck, which the resting gate named "still inside after the nudge"
(assembly@tube, 2026-11-12).

    downs(stage, place, record, rows)   {name: metres down} of each such thing over nothing within TOLERANCE, let
                                        down by the least gap of its foot's points to the first surface under them
                                        (the made ground, or any other thing)
    let_down(folder, place, rows)       each such thing of the place at `folder` moved down, with what it holds; the
                                        fits [{name, how "let down", ...}], laid.json written again
"""
import json
import pathlib

import numpy as np

from score.stages.assembly import BASE_LAYER, RECORD, fitting, made_waiting, on_ground, parting

# The supports the resting check judges a thing standing on what is under it by (triage.support_type's floor and held;
# None: the row's support is read by the triage's own rules, standing unless the record or inventory say otherwise).
STANDING = (None, "floor", "held")


def faced_standing(record, rows=None):
    """The names of the record's things laid on their holder's side (`face`) whose row is judged standing: given no
    support but standing ones by the resting check's reading of the inventory `rows` (assembly.resting_rows: not every
    object of it on a face, mounted.on_faces, nor mounted on a wall or ceiling row, mounted.mounted, nor hung or
    resting as laid); by the record alone (on_faces) without `rows`."""
    from score.stages.assembly import resting_rows
    from score.stages.assembly.mounted import on_faces
    hanging = on_faces(record)
    given = {row["id"]: row.get("support") for row in resting_rows({"rows": rows or []}, record)["rows"]}
    return [entry["name"] for entry in record.get("objects") or []
            if (entry.get("on") or {}).get("how") == "face" and entry["row"] not in hanging
            and given.get(entry["row"]) in STANDING]


def gap_under(points, ground, others):
    """The least gap (metres) from `points` [n, 3] straight down to the first surface under them: the made ground
    (`ground`: (n, 2) x, z -> heights, nan off it) or `others` (one mesh of the other things, or None); inf with
    none."""
    gaps = points[:, 1] - ground(points[:, [0, 2]])
    gaps = np.where(np.isfinite(gaps), gaps, np.inf)
    if others is not None and len(others.faces):
        found, rays, _ = others.ray.intersects_location(points, np.tile([0.0, -1.0, 0.0], (len(points), 1)),
                                                        multiple_hits=False)
        if len(rays):
            under = points[rays, 1] - found[:, 1]
            gaps[rays] = np.minimum(gaps[rays], np.where(under >= -fitting.BOARD_CLEAR, under, np.inf))
    return float(gaps.min())


def downs(stage, place, record, rows=None):
    """{name: metres} each faced thing of a standing row (faced_standing, by the inventory `rows`) is let down by: the
    least gap of its foot's points (within TOLERANCE of its lowest: its back may touch its holder's side higher up,
    solar_panels_5 at one point) to the first surface under them, where that is over TOLERANCE (gap_under)."""
    import resting
    import trimesh
    ground = resting.ground_height(stage, place)
    things = stage.GetPrimAtPath(f"/{place}/Objects")
    names = [prim.GetName() for prim in (things.GetChildren() if things else [])]
    found = {}
    for name in faced_standing(record, rows):
        prim = stage.GetPrimAtPath(f"/{place}/Objects/{name}")
        if not prim:
            continue
        points = on_ground.world_points(prim)
        points = points[points[:, 1] <= points[:, 1].min() + on_ground.TOLERANCE]  # its foot, as the check reads it
        meshes = [mesh for mesh in (fitting.surface_mesh(stage, f"/{place}/Objects/{other}")
                                    for other in names if other != name) if mesh is not None]
        gap = gap_under(points, ground, trimesh.util.concatenate(meshes) if meshes else None)
        if on_ground.TOLERANCE < gap < np.inf:
            found[name] = gap
    return found


def let_down(folder, place, rows=None):
    """Each faced thing of a standing row (by the inventory `rows`) of the place at `folder` moved down onto what is
    under it (downs), what it holds moved with it; the base layer saved and laid.json's boxes and fits written again.
    The fits, [] and nothing written when none moves."""
    from pxr import Gf, Sdf, Usd
    folder = pathlib.Path(folder)
    laid_path, record_path = folder / made_waiting.LAID, folder / RECORD
    if not laid_path.exists() or not record_path.exists():
        return []
    laid, record = json.loads(laid_path.read_text()), json.loads(record_path.read_text())
    stage = Usd.Stage.Open(str(folder / f"{place}.usda"))
    layer = Sdf.Layer.FindOrOpen(str(folder / BASE_LAYER))
    stage.SetEditTarget(Usd.EditTarget(layer))
    entries = {entry["name"]: entry for entry in record.get("objects") or []}
    holding = fitting.holders_of(record)
    fits = []
    for name, drop in sorted(downs(stage, place, record, rows).items()):
        held = [other for other in parting.carried(name, holding)
                if other in entries and stage.GetPrimAtPath(f"/{place}/Objects/{other}")]
        for one in (name, *held):
            path = f"/{place}/Objects/{one}"
            fitting.changed_by(stage.GetPrimAtPath(path), Gf.Matrix4d(on_ground.moved([0.0, -drop, 0.0]).tolist()))
            fits.append(fitting.laid_fit(stage, path, entries[one], "let down", None, drop, 1.0,
                                         f"let down {drop:.2f} m onto what is under it"
                                         + ("" if one == name else f" with {name}, which holds it")))
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
