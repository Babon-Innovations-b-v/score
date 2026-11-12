"""A thing the scene record hangs between two holders (its `on` how "between": score/review/holders' `hung`, a lantern
string over the square's plaza between two buildings) laid from one holder's built surface to the other's, or left
waiting while either is not laid (fitting.fitted calls laid; assembly.resting_rows judges its rows hanging, by
touching; fitting.off measures it by off).

    rows(record)                   {row id: "hanging"} of the rows whose every object hangs between holders
    laid(stage, place, entries)    each such thing spanned between its holders, or left waiting; the fits
    off(low, high, boxes)          metres a thing so laid stands off the nearer side of either holder's box

The square's eight lantern strings, which its plan hangs 6 m over the plaza between its left and right buildings (two
between its back floodlight tower and the right building), had no `on`: the inventory's on:plaza made them held, and
they floated 1.7 to 4.35 m over it (2026-11-12). Its three buildings wait on a bake retake, so the strings wait with
them: a string with nothing to hang from is never laid as if it hung.
"""
import math

import numpy as np

BETWEEN = "between"
# Two holders' surfaces nearer than this, metres, along the floor leave no run to hang a thing over: left as laid.
RUN_LEAST = 0.1


def between(entry):
    """Whether a scene record entry hangs between two holders (its `on` how BETWEEN)."""
    return (entry.get("on") or {}).get("how") == BETWEEN


def rows(record):
    """{row id: "hanging"} of the scene `record`'s rows whose every object hangs between its holders: the resting
    triage judges each by touching them (a hanging one touching nothing fails, hanging free), never as standing on the
    place's floor its inventory anchors it to."""
    found = {}
    for entry in record.get("objects") or []:
        found.setdefault(entry["row"], []).append(between(entry))
    return {row_id: "hanging" for row_id, hung in found.items() if all(hung)}


def laid(stage, place, entries):
    """Each laid entry hung between holders (`entries`, the record's objects; its prim active) laid from one holder's
    built surface to the other's (spanned), or, where either holder is not laid (its model waiting on the bake), left
    out waiting for it (waiting); the fits [{name, how, ...}]."""
    fits = []
    for entry in entries:
        path = f"/{place}/Objects/{entry['name']}"
        prim = stage.GetPrimAtPath(path)
        if not between(entry) or not prim or not prim.IsActive():
            continue
        holders = list(entry["on"].get("holder") or [])
        missing = [name for name in holders if not (stage.GetPrimAtPath(f"/{place}/Objects/{name}") and
                                                    stage.GetPrimAtPath(f"/{place}/Objects/{name}").IsActive())]
        found = waiting(stage, path, entry, missing) if missing or len(holders) != 2 else \
            spanned(stage, place, path, entry, holders)
        if found is not None:
            fits.append(found)
    return fits


def waiting(stage, path, entry, missing):
    """The fit {name, how "waiting", ...} of a thing hung between holders not all laid (`missing`, their names): its
    prim made inactive, its box as it was laid. It is laid between them once their models are (the square's lantern
    strings while its buildings wait on a bake retake): left standing where the plan drew it, it would hang on
    nothing."""
    from pxr import Sdf
    from score.stages.assembly import fitting
    box = fitting.world_box(stage, path)
    words = (f"waiting: hung between {' and '.join(entry['on'].get('holder') or [])}, "
             f"{' and '.join(missing) or 'one'} not laid yet (its model waiting on the bake)")
    prim = stage.GetPrimAtPath(path)
    prim.CreateAttribute("score:fitted", Sdf.ValueTypeNames.String).Set(words)
    prim.SetActive(False)
    return {"name": entry["name"], "row": entry["row"], "how": "waiting", "holder": entry["on"].get("holder"),
            "moved": 0.0, "scale": 1.0, "low": [round(float(value), 4) for value in box[0]],
            "high": [round(float(value), 4) for value in box[1]], "words": words}


def long_way(corners):
    """The unit floor way [x, z] of a turned box's (corners [8, 3], fitting.oriented_corners) long side, and its
    length along it."""
    floor = np.asarray(corners, float)[:, [0, 2]]
    way = np.linalg.svd(floor - floor.mean(axis=0), full_matrices=False)[2][0]
    reach = floor @ way
    return way, float(reach.max() - reach.min())


def anchors(stage, place, holders, middle):
    """[floor point (x, z)] of each holder's built surface (fitting.surface_mesh, else its box) nearest a thing's
    middle [x, y, z]: where it hangs from it."""
    import trimesh
    from score.stages.assembly import fitting
    found = []
    for name in holders:
        surface = fitting.surface_mesh(stage, f"/{place}/Objects/{name}")
        if surface is None or not len(surface.faces):
            surface = trimesh.creation.box(bounds=fitting.world_box(stage, f"/{place}/Objects/{name}"))
        point, _, _ = trimesh.proximity.closest_point(surface, np.asarray([middle], float))
        found.append(np.asarray(point[0], float)[[0, 2]])
    return found


def spanned(stage, place, path, entry, holders):
    """The fit {name, how "between", ...} of a thing laid between its two holders (`holders`): its long side turned
    along the floor run from the point of one's built surface nearest its middle to the other's (anchors), its middle
    at the run's middle and at its own height, shrunk to the run where it is built longer, so its ends meet both
    surfaces; built shorter than the run (never grown past its own model) it is laid at its size from the holder
    nearer its middle, short of the other, which off measures and the held gate names. None where the two surfaces
    stand within RUN_LEAST of each other along the floor."""
    from score.stages.assembly import fitting
    low, high = fitting.world_box(stage, path)
    middle = (low + high) / 2
    first, second = anchors(stage, place, holders, middle)
    run = float(np.linalg.norm(second - first))
    if run < RUN_LEAST:
        return None
    way, _ = long_way(fitting.oriented_corners(stage, path))
    toward = (second - first) / run
    degrees = math.degrees(math.atan2(way[1], way[0]) - math.atan2(toward[1], toward[0]))
    degrees = (degrees + 90.0) % 180.0 - 90.0  # a long side has no front: the least turn either way
    prim, pivot = stage.GetPrimAtPath(path), fitting.foot_middle(low, high)
    fitting.pitched_by(prim, pivot, (0.0, 1.0, 0.0), degrees, pivot)
    low, high = fitting.world_box(stage, path)
    _, length = long_way(fitting.oriented_corners(stage, path))
    scale = min(1.0, run / max(length, 1e-9))
    if scale < 1.0:
        at = (first + second) / 2
        words = f"hung between {holders[0]} and {holders[1]}: turned {degrees:.1f} degrees along the {run:.2f} m " \
                f"run between them, shrunk to {scale:.0%} to fit it"
    else:
        near = 0 if np.linalg.norm(first - middle[[0, 2]]) <= np.linalg.norm(second - middle[[0, 2]]) else 1
        start, sign = (first, 1.0) if near == 0 else (second, -1.0)
        at = start + sign * toward * length / 2
        words = f"hung from {holders[near]} toward {holders[1 - near]}: turned {degrees:.1f} degrees along the " \
                f"{run:.2f} m run between them, built {length:.2f} m long, {run - length:.2f} m short of " \
                f"{holders[1 - near]}"
    foot = fitting.foot_middle(low, high)
    fitting.moved_by(prim, foot, scale, np.array([at[0], foot[1], at[1]]))
    return fitting.laid_fit(stage, path, entry, BETWEEN, holders, float(np.linalg.norm(at - middle[[0, 2]])), scale,
                            words)


def off(low, high, boxes):
    """Metres a thing hung between holders (their boxes [(low, high)]) stands off the nearer side of the farther of
    them: 0 where it reaches into or onto both."""
    low, high = np.asarray(low, float), np.asarray(high, float)
    return max((float(np.linalg.norm(np.maximum(0.0, np.maximum(np.asarray(box[0], float) - high,
                                                                low - np.asarray(box[1], float)))))
                for box in boxes), default=0.0)
