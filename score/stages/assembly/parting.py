"""A thing on the floor that a wall's thing was laid into, parted from it after the fitting (wired.make's `parted`,
and grounded.grounded_seed's, so the settle drops what the assembly lays: settle@airlock failed on that very
pair while only the assembly parted it, 2026-11-10).

fitting.fitted parts the things nothing holds first and lays each wall's and face's things after, so a wall thing laid
along its wall can land on a floor thing parted before it, and fitting.parted keeps its parting only when the place's
whole crossing count drops (airlock, 2026-11-10: control_pedestals_2 0.16 m inside wall_pipes_1, packed along its wall
after the pedestals stood). Here each such floor thing (no `on`, holding nothing, no climbing row, filling nothing) is
moved to its nearest free spot at its built size (fitting.free_spot: clear of every other laid object and holder it
shares height with and of the wall pieces, in its own room, never through a wall), on the base layer, and its box in
laid.json and its fit (`how` "parted") written again; one with no free spot is left as laid, for the held gate to name.
The wall thing stays where its relation put it.
"""
import json

import numpy as np

from score.stages.assembly import BASE_LAYER, RECORD, fitting, made_waiting

LEANING = ("wall", "face")


def loose(entry, holding):
    """Whether an entry is a thing on the floor this may move: nothing holds it, it holds nothing, it climbs into no
    level and fills no holder."""
    return not entry.get("on") and not fitting.climbs(entry) and not entry.get("fills") and not any(
        entry["name"] in held for held in holding.values())


def crossed(record, boxes):
    """{floor thing: the wall or face thing laid into it} of the record's entries as laid (`boxes`), the floor thing
    one `loose` may move, the two sharing height and reaching into each other more than fitting.HELD_MOST every way."""
    holding = fitting.holders_of(record)
    entries = [entry for entry in record.get("objects") or [] if entry["name"] in boxes]
    leaning = [entry["name"] for entry in entries if (entry.get("on") or {}).get("how") in LEANING]
    found = {}
    for entry in entries:
        if not loose(entry, holding):
            continue
        box = boxes[entry["name"]]
        into = [name for name in leaning if fitting.tall_together(box, boxes[name])
                and fitting.depths(*box, boxes[name]).min() > fitting.HELD_MOST]
        if into:
            found[entry["name"]] = into[0]
    return found


def room_of(stage, place):
    """(the box of the place's walls [low x, low z, high x, high z], its wall pieces [(low, high)], its slanted walls),
    as fitting.parted reads them."""
    built = fitting.walls(stage, place)
    room = [box for name, box in built if name.split("_")[0] == "wall"]
    pieces = [box for name, box in fitting.statics(built) if name.split("_")[0] == "wall"]
    inside = ([min(box[0][0] for box in room), min(box[0][2] for box in room), max(box[1][0] for box in room),
               max(box[1][2] for box in room)] if room else fitting.OPEN)
    return inside, pieces, fitting.slants(stage, place)


def parted(out, place):
    """Each floor thing a wall's thing was laid into moved to its nearest free spot on the base layer, laid.json
    written again; the fits [{name, how "parted", ...}]."""
    from pxr import Sdf, Usd
    laid_path, record_path = out / made_waiting.LAID, out / RECORD
    if not laid_path.exists() or not record_path.exists():
        return []
    laid, record = json.loads(laid_path.read_text()), json.loads(record_path.read_text())
    boxes = {entry["name"]: tuple(np.asarray(end, float) for end in (entry["low"], entry["high"]))
             for entry in laid.get("objects", [])}
    movers = crossed(record, boxes)
    if not movers:
        return []
    layer = Sdf.Layer.FindOrOpen(str(out / BASE_LAYER))
    stage = Usd.Stage.Open(layer)
    inside, pieces, slanted = room_of(stage, place)
    holders = [tuple(np.asarray(end, float) for end in (entry["low"], entry["high"]))
               for entry in laid.get("holders", [])]
    entries = {entry["name"]: entry for entry in record.get("objects") or []}
    fits = []
    for name in sorted(movers, key=lambda name: -float(np.prod((boxes[name][1] - boxes[name][0])[[0, 2]]))):
        path = f"/{place}/Objects/{name}"
        box = fitting.world_box(stage, path)
        others = [*holders, *(found for other, found in boxes.items() if other != name)]
        move = fitting.free_spot(box, others, pieces, fitting.bound_of(box, inside), slanted)
        if move is None:
            continue
        foot = fitting.foot_middle(*box)
        fitting.moved_by(stage.GetPrimAtPath(path), foot, 1.0, foot + move)
        fits.append(fitting.laid_fit(stage, path, entries[name], "parted", None, np.linalg.norm(move), 1.0,
                                     f"parted {float(np.linalg.norm(move)):.2f} m on the floor at its built size: "
                                     f"{movers[name]} was laid against its wall into it"))
        boxes[name] = fitting.world_box(stage, path)
    layer.Save()
    moved = {fit["name"]: fit for fit in fits}
    laid["objects"] = [{**entry, "low": moved[entry["name"]]["low"], "high": moved[entry["name"]]["high"]}
                       if entry["name"] in moved else entry for entry in laid["objects"]]
    laid["fitted"] = [*laid.get("fitted", []), *fits]
    laid_path.write_text(json.dumps(laid, indent=1))
    return fits
