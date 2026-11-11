"""A thing laid on its holder's top, or within it off its shelves, let down onto the holder's built surface under its
footprint (fitting.fitted, after the tops are spread): on_holder stands a top one on the top of its holder's box,
which is the top of the holder's highest part, not the surface under the thing, and lays a within one at its plan
height. Lab's monitors, lamps and keyboards on a desk whose top stops short of its box, quarters' desk things, flat's
pillow, kettle and dishes, workshop's boxes on their shelving units (settle@<place>, 2026-11-11) floated 0.04 to 0.5 m
over the surface under them, sank into it, or leaned on an edge past the settle's 30 cm snap.

    rest(mesh, low, high)        the height a thing's foot stands at on the built surface under its footprint
    spot(mesh, low, high, box, others)   (foot middle, how far it slid) of the nearest spot it stands on
    held_on(entry)               whether a record entry stands on its holder's built surface (top, or within it)
    let_down(stage, place, entries)      each such thing laid on the surface under it; the fits [{name, how, ...}]
    stacked_spot(stage, place, low, high, others)   a spot on top of one of the things laid on its holders
    stacked_down(stage, place, stacked)  each thing stacked on the runs over its holder laid on their surface
"""
import numpy as np

from score.stages.assembly import fitting

# The pitch, metres, of the spots across its holder's top a thing that stands on no surface where it is laid is tried
# at, nearest first: the resting check's TOLERANCE plus 2 cm.
TOP_PITCH = 0.05
# How far, metres, a thing standing on no surface where it is laid is slid across its holder's top at most: half a
# desk. One further from any surface it stands on is left for the held and resting gates to name.
SLIDE_MOST = 0.6


def rest(mesh, low, high, reach=fitting.BOARD_BED, points=None):
    """The height a thing's foot (its box low, high) stands at on its holder's built surface (`mesh`) under its
    footprint: of the surfaces the rays straight down meet under its foot or over it by `reach` at most (BOARD_BED on
    a top, where no surface of the holder stands over it; its own height within its holder, where it may lie across a
    board), never a board's underside, the nearest to its foot that the inner half of the footprint stands on
    (fitting.supported) and that nothing of the holder crosses from there to its top (fitting.clear_of, and
    fitting.crosses of its surface `points`: a side the rays straight down miss); None where none does."""
    hits = fitting.board_hits(mesh, low, high)
    if not len(hits[0]):
        return None
    tall, foot = float(high[1] - low[1]), float(low[1])
    for height in sorted(set(np.round(np.concatenate(hits), 4).tolist()), key=lambda height: abs(height - foot)):
        if height > foot + reach or np.any((hits[0] > height + 1e-4) & (hits[0] <= height + fitting.BOARD_BED)):
            continue  # out of its reach, or a board's underside: its top is the rest
        lift = height - foot
        if not fitting.supported(hits, height):
            continue
        if reach <= fitting.BOARD_BED and np.any(np.concatenate(hits) > height + fitting.BOARD_BED):
            continue  # on a top nothing of its holder is over it: never a shelf under the top (quarters' mug)
        if fitting.clear_of(hits, height, tall) and (
                points is None or not fitting.crosses(points, low + [0.0, lift, 0.0], high + [0.0, lift, 0.0])):
            return height
    return None


def spot(mesh, low, high, box, others=(), reach=fitting.BOARD_BED):
    """(foot middle, metres slid) of a thing (its box low, high) on its holder's built surface (`mesh`) within the
    holder's `box` (low, high): where it is laid, let down onto the surface under it (rest), else at the nearest spot
    TOP_PITCH apart across the box within SLIDE_MOST that it stands on, meeting none of `others` (the boxes laid on
    the holder beside it), a surface `reach` over its foot at most (rest); None where none is found."""
    low, high = np.asarray(low, float), np.asarray(high, float)
    hold_low, hold_high = (np.asarray(end, float) for end in box)
    foot, half = fitting.foot_middle(low, high), (high - low) / 2
    points = np.vstack([np.asarray(mesh.vertices, float), mesh.sample(fitting.BOARD_SAMPLES, seed=0)])
    tries = [(0.0, 0.0)]
    steps = int(SLIDE_MOST / TOP_PITCH)
    tries += sorted(((x * TOP_PITCH, z * TOP_PITCH) for x in range(-steps, steps + 1)
                     for z in range(-steps, steps + 1) if (x, z) != (0, 0)
                     and np.hypot(x, z) * TOP_PITCH <= SLIDE_MOST), key=lambda move: np.hypot(*move))
    seen = set()
    for along, across in tries:
        middle = np.array([fitting.kept_within(foot[0] + along, hold_low[0], hold_high[0], half[0]), foot[1],
                           fitting.kept_within(foot[2] + across, hold_low[2], hold_high[2], half[2])])
        key = (round(float(middle[0]), 4), round(float(middle[2]), 4))
        if key in seen:
            continue
        seen.add(key)
        shift = middle - foot
        moved_low, moved_high = low + shift, high + shift
        height = rest(mesh, moved_low, moved_high, reach, points)
        if height is None:
            continue
        middle[1] = height
        lift = height - float(low[1])
        if fitting.meets_any(moved_low + [0, lift, 0], moved_high + [0, lift, 0], others):
            continue
        return middle, float(np.hypot(shift[0], shift[2]))
    return None


def stacked_spot(stage, place, low, high, others):
    """((foot middle, metres slid), its name) of a thing (its box low, high) stood on the built top of the nearest of
    `others` (the things laid on its holders before it, which move no more) it stands on clear of the rest (spot, its foot raised to that one's box
    top), (None, None) with none: workshop's seventh storage box, its two shelving units' tops full, straddled their
    meeting and tipped (2026-11-11)."""
    here = fitting.foot_middle(np.asarray(low, float), np.asarray(high, float))
    boxes = {other: fitting.world_box(stage, f"/{place}/Objects/{other}") for other in others}
    for other in sorted(boxes, key=lambda other: float(np.linalg.norm(
            (fitting.foot_middle(*boxes[other]) - here)[[0, 2]]))):
        mesh = fitting.surface_mesh(stage, f"/{place}/Objects/{other}")
        if mesh is None:
            continue
        lift = np.array([0.0, float(boxes[other][1][1]) - float(low[1]), 0.0])
        found = spot(mesh, np.asarray(low, float) + lift, np.asarray(high, float) + lift, boxes[other],
                     [box for name, box in boxes.items() if name != other])
        if found is not None:
            return found, other
    return None, None


def held_on(entry):
    """Whether a scene record entry stands on its holder's built surface: laid on its top, or within it where it is
    neither on its shelves (fitting.on_boards lays those), hung in it (fitting.hangs_in), part of it (`fills`) nor
    under it, its holder an object."""
    on = entry.get("on") or {}
    if on.get("holder scope", "Objects") != "Objects" or not on.get("holder"):
        return False
    return on.get("how") == "top" or (on.get("how") == "within" and not fitting.on_shelves_of(on) and not
                                      fitting.hangs_in(entry) and not entry.get("fills") and not on.get("under"))


def let_down(stage, place, entries):
    """Each thing laid on its holders' top or within them (`entries`, held_on's), a holder before what it holds, moved
    onto the holders' built surface under it (spot, on their surfaces as one mesh within their boxes as one), carrying
    what is laid on its own top (fitting.carry), clear of the others laid on them; a top one with no spot left on them
    on top of one of those (stacked_spot); one already standing there, one within its holder at its foot, or one with
    no spot found, left. The fits [{name, how, ..., a top one's "top at":
    the height its foot stands at, which the held gate measures it off}]."""
    import trimesh
    by_name = {entry["name"]: entry for entry in entries}
    carried = {}
    for entry in entries:
        for holder in entry["on"].get("holder") or []:
            carried.setdefault(holder, []).append(entry["name"])
    fits, done = [], set()

    def one(name, seen=()):
        if name in done or name in seen:
            return
        entry = by_name[name]
        for holder in entry["on"].get("holder") or []:
            if holder in by_name:
                one(holder, (*seen, name))
        done.add(name)
        scope = entry["on"].get("holder scope", "Objects")
        holders = [f"/{place}/{scope}/{holder}" for holder in entry["on"].get("holder") or []
                   if stage.GetPrimAtPath(f"/{place}/{scope}/{holder}")]
        found = [mesh for mesh in (fitting.surface_mesh(stage, path) for path in holders) if mesh is not None]
        if not found:
            return
        boxes = [fitting.world_box(stage, path) for path in holders]
        box = (np.min([low for low, _ in boxes], axis=0), np.max([high for _, high in boxes], axis=0))
        path = f"/{place}/Objects/{name}"
        low, high = fitting.world_box(stage, path)
        others = [fitting.world_box(stage, f"/{place}/Objects/{other}") for holder in entry["on"].get("holder") or []
                  for other in carried.get(holder, []) if other != name]
        within = entry["on"]["how"] == "within"
        if within and float(low[1]) <= float(box[0][1]) + fitting.BOARD_BED:
            return  # at its holder's foot: on the floor it stands in, as on_boards leaves it
        laid = spot(trimesh.util.concatenate(found), low, high, box, others,
                    float(high[1] - low[1]) if within else fitting.BOARD_BED)
        on_other = None
        if laid is None and not within:  # no spot left on the holders: on top of one laid on them, as on_boards stacks
            laid, on_other = stacked_spot(stage, place, low, high, [other for holder in entry["on"].get("holder") or []
                                                                    for other in carried.get(holder, [])
                                                                    if other != name and other in done])
        if laid is None:
            return
        target, slid = laid
        foot = fitting.foot_middle(low, high)
        moved = float(np.linalg.norm(target - foot))
        if moved < fitting.MOVE_LEAST:
            return
        fitting.moved_by(stage.GetPrimAtPath(path), foot, 1.0, target)
        fitting.carry(stage, place, carried, name, target - foot)
        words = f"laid {abs(foot[1] - target[1]):.2f} m {'down' if target[1] < foot[1] else 'up'} onto " \
                f"{on_other or ', '.join(entry['on'].get('holder'))}'s built surface" + (
                    f", no spot left on {', '.join(entry['on'].get('holder'))}" if on_other else " under it")
        fit = fitting.laid_fit(stage, path, entry, entry["on"]["how"], entry["on"].get("holder"), moved, 1.0,
                               words + (f", slid {slid:.2f} m to stand on it" if slid else ""))
        fits.append({**fit, "top at": round(float(target[1]), 4)} if not within else fit)

    for name in by_name:
        one(name)
    return fits


def stacked_down(stage, place, stacked):
    """Each thing moved up onto the runs packed over its holder (`stacked`, fitting.stacked_on_runs' fits: their
    `holder` those runs) let straight down onto their built surface under it where it stands over it (rest): the lift
    is to the runs' box top, and hangar's valve stood 0.06 m over its pipe's surface (2026-11-11); one over no surface
    of them is left. The fits [{name, how "stacked", ..., "top at"}]."""
    import trimesh
    fits = []
    for fit in stacked:
        found = [mesh for mesh in (fitting.surface_mesh(stage, f"/{place}/Objects/{run}") for run in fit["holder"])
                 if mesh is not None]
        path = f"/{place}/Objects/{fit['name']}"
        low, high = fitting.world_box(stage, path)
        height = rest(trimesh.util.concatenate(found), low, high) if found else None
        if height is None or float(low[1]) - height < fitting.MOVE_LEAST:
            continue
        foot = fitting.foot_middle(low, high)
        target = np.array([foot[0], height, foot[2]])
        fitting.moved_by(stage.GetPrimAtPath(path), foot, 1.0, target)
        entry = {"name": fit["name"], "row": fit["row"]}
        down = fitting.laid_fit(stage, path, entry, "stacked", fit["holder"], float(foot[1] - height), 1.0,
                                f"{fit['words']}, then {foot[1] - height:.2f} m down onto their built surface")
        fits.append({**down, "top at": round(float(height), 4)})
    return fits
