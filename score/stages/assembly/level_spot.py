"""A thing nothing holds, laid at the floor of an open place where the made ground under it slopes, slid across to the
nearest spot within SLIDE_MOST where the ground under its box is level by the resting check's measure (before
on_ground.stood stands it there): a round tank in a dent rests at the dent's bottom, never on its side.

assembly@wreck, 2026-11-12: its spherical tank 2, laid 0.26 m off the middle of its 1 m dent (terrain/bounded.py), was
turned 7.9 degrees with the dent's side under its box by on_ground and leaned so: its up axis 7.9 degrees from what it
touched. Slid to where the dent under it is level, it stands upright at the dent's bottom.

    spot(low, high, ground)   the shift [x, z] (metres) of a box (low, high) to the nearest spot, SLIDE_STEP apart
                              within SLIDE_MOST, where the ground under it is level (on_ground.ground_up straight up);
                              None where none is, or where it is level already
    slid(folder, place)       each such thing of the place at `folder` slid there, what it holds with it; the fits
                              [{name, how "slid level", ...}], the base layer saved and laid.json written again
"""
import json
import pathlib

import numpy as np

from score.stages.assembly import BASE_LAYER, RECORD, even_feet, fitting, made_waiting, on_ground, parting

# How far, metres, a thing is slid at most to a level spot (a tank's own radius off its dent's middle, and more), and
# the pitch of the spots tried, nearest first.
SLIDE_MOST = 0.5
SLIDE_STEP = 0.02


def level(low, high, ground):
    """Whether the ground under a box (low, high) is level by the resting check's measure (on_ground.ground_up)."""
    normal = on_ground.ground_up(low, high, ground)
    return normal is not None and bool(np.allclose(normal, [0.0, 1.0, 0.0]))


def spot(low, high, ground):
    """The shift [x, z] of a box (low, high) to the nearest spot where the ground under it is level (module
    docstring); None where it is level already, where the ground under it is not known, or no spot is."""
    if on_ground.ground_up(low, high, ground) is None or level(low, high, ground):
        return None
    steps = int(round(SLIDE_MOST / SLIDE_STEP))
    tries = sorted(((x * SLIDE_STEP, z * SLIDE_STEP) for x in range(-steps, steps + 1)
                    for z in range(-steps, steps + 1) if 0 < np.hypot(x, z) * SLIDE_STEP <= SLIDE_MOST),
                   key=lambda shift: np.hypot(*shift))
    for x, z in tries:
        shift = np.array([x, 0.0, z])
        if level(low + shift, high + shift, ground):
            return np.array([x, z])
    return None


def slid(folder, place):
    """Each thing nothing holds at the floor of an open place, over no built deck, where the ground under it slopes,
    slid to the nearest level spot (spot), with what it holds; the fits, [] and nothing written when none moves."""
    from pxr import Gf, Sdf, Usd
    import resting
    folder = pathlib.Path(folder)
    laid_path, record_path = folder / made_waiting.LAID, folder / RECORD
    if not laid_path.exists() or not record_path.exists():
        return []
    laid, record = json.loads(laid_path.read_text()), json.loads(record_path.read_text())
    stage = Usd.Stage.Open(str(folder / f"{place}.usda"))
    near = stage.GetPrimAtPath(f"/{place}/{on_ground.MADE_GROUND}")
    if record.get("inside") or not (near and near.IsActive()):
        return []
    ground = resting.ground_height(stage, place)
    layer = Sdf.Layer.FindOrOpen(str(folder / BASE_LAYER))
    stage.SetEditTarget(Usd.EditTarget(layer))
    decks = fitting.deck_triangles(stage, place)
    holding = fitting.holders_of(record)
    entries = {entry["name"]: entry for entry in record.get("objects") or []}
    fits = []
    for name, entry in sorted(entries.items()):
        prim = stage.GetPrimAtPath(f"/{place}/Objects/{name}")
        if not (prim and parting.loose(entry) and even_feet.floor_thing(prim) and on_ground.at_floor(entry)):
            continue
        points = on_ground.world_points(prim)
        if not len(points):
            continue
        low, high = points.min(axis=0), points.max(axis=0)
        if on_ground.over_deck([(low[0] + high[0]) / 2, low[1], (low[2] + high[2]) / 2], decks):
            continue
        shift = spot(low, high, ground)
        if shift is None:
            continue
        held = [other for other in parting.carried(name, holding)
                if other in entries and stage.GetPrimAtPath(f"/{place}/Objects/{other}")]
        for one in (name, *held):
            path = f"/{place}/Objects/{one}"
            fitting.changed_by(stage.GetPrimAtPath(path),
                               Gf.Matrix4d(on_ground.moved([shift[0], 0.0, shift[1]]).tolist()))
            fits.append(fitting.laid_fit(stage, path, entries[one], "slid level", None, float(np.hypot(*shift)), 1.0,
                                         f"slid {np.hypot(*shift):.2f} m to where the ground under it is level"
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
