"""A design's object laid by its relation at its built size (issue #72; bible `architecture/layers`, assembly: the plan
states the relations, the assembly lays by them): its scene record entry's `on` (scene_record/writer.related, from
score/review/holders) says what holds it, and once its baked model and its holder's stand on the stage it is moved, and
shrunk where it does not fit (never grown past its own model), so it sits

    top     on its holder's top, within its footprint (a monitor on its console, a lamp on its desk)
    within  inside its holder's box (plants in their greenhouse, a door in its frame)
    face    with its back on its holder's side `out` points from, within that side's span and height (a garage door on
            its module's front)
    wall    with its back on a wall's face (`span`, `out` into the room), within the face's length
    in      in its opening: its middle on the opening's middle at its sill, as wide and tall as the opening at most

Boxes are the place's axis-aligned ones (Y up), so a face is the box side nearest `out`; the plan's sizes are
estimates, the built ones are laid (the module's 12 m, not the plan's 17.2). Kept apart from record.py: the light and
settle stages hash it.

    fit(low, high, on, holders)   (scale, the new middle of its foot, words) of one object, or None when it sits
    fitted(stage, place, entries, laid)   each laid entry's fit applied on the stage; the fits [{name, ...}]
    off(low, high, on, holders)   metres an object as laid stands off where its relation puts it
    held_faults(record, laid)     [(object, what is wrong, metres or None)]: the assembly's `held` gate
"""
import numpy as np

# A fit that moves an object less than this, metres, and shrinks it by less than SHRINK_LEAST is no fit: it sits.
MOVE_LEAST = 0.01
SHRINK_LEAST = 0.001


def foot_middle(low, high):
    return np.array([(low[0] + high[0]) / 2, low[1], (low[2] + high[2]) / 2])


def kept_within(value, low, high, half):
    """`value` moved the least that keeps `half` either side of it within [low, high]."""
    return float(np.clip(value, low + half, high - half)) if high - low >= 2 * half else (low + high) / 2


def nearest(holders, low, high):
    """The holder box (low, high) whose middle is nearest the object's, on the floor plan."""
    here = (np.asarray(low) + np.asarray(high)) / 2
    return min(holders, key=lambda box: float(np.linalg.norm(((box[0] + box[1]) / 2 - here)[[0, 2]])))


def across(way, size):
    """An axis-aligned box's reach along a level way [x, z]."""
    return abs(way[0]) * size[0] + abs(way[1]) * size[2]


def on_holder(low, high, how, out, box):
    """(scale, foot middle) of an object top, within or face on a holder box."""
    size, (hold_low, hold_high) = high - low, box
    room = hold_high - hold_low
    foot = foot_middle(low, high)
    if how == "face":
        axis = 0 if abs(out[0]) >= abs(out[1]) else 2
        side = 2 - axis
        scale = min(1.0, room[side] / size[side], room[1] / size[1])
        half = size * scale / 2
        target = foot.copy()
        target[axis] = (hold_high[axis] + half[axis]) if out[axis // 2] > 0 else (hold_low[axis] - half[axis])
        target[side] = kept_within(foot[side], hold_low[side], hold_high[side], half[side])
        target[1] = float(np.clip(foot[1], hold_low[1], hold_high[1] - size[1] * scale))
        return scale, target
    scale = min(1.0, room[0] / size[0], room[2] / size[2], *([room[1] / size[1]] if how == "within" else []))
    half = size * scale / 2
    target = np.array([kept_within(foot[0], hold_low[0], hold_high[0], half[0]), 0.0,
                       kept_within(foot[2], hold_low[2], hold_high[2], half[2])])
    target[1] = hold_high[1] if how == "top" else float(np.clip(foot[1], hold_low[1], hold_high[1] - size[1] * scale))
    return scale, target


def on_wall(low, high, on):
    """(scale, foot middle) of an object with its back on a wall's face, within its length."""
    size, foot = high - low, foot_middle(low, high)
    start, end = (np.array([point[0], point[1]], float) for point in on["span"])
    length = float(np.linalg.norm(end - start))
    run, out = (end - start) / max(length, 1e-9), np.asarray(on["out"], float)
    scale = min(1.0, length / max(across(run, size), 1e-9))
    along = kept_within(float((foot[[0, 2]] - start) @ run), 0.0, length, across(run, size) * scale / 2)
    spot = start + run * along + out * across(out, size) * scale / 2
    return scale, np.array([spot[0], foot[1], spot[1]])


def in_opening(low, high, on):
    """(scale, foot middle) of an object in its opening, no wider or taller than it."""
    size = high - low
    scale = min(1.0, float(on["wide"]) / max(across(on["along"], size), 1e-9), float(on["tall"]) / size[1])
    return scale, np.asarray(on["middle"], float)


def fit(low, high, on, holders=()):
    """(scale, the new middle of its foot, words) of an object laid by its relation `on` (module docstring), from its
    box (low, high) and its holders' boxes; None when it already sits (or holds to nothing laid)."""
    low, high = np.asarray(low, float), np.asarray(high, float)
    how = on["how"]
    if how in ("top", "within", "face"):
        if not holders:
            return None
        box = nearest([tuple(np.asarray(end, float) for end in found) for found in holders], low, high)
        scale, target = on_holder(low, high, how, on.get("out", (0.0, 1.0)), box)
    elif how == "wall":
        scale, target = on_wall(low, high, on)
    else:
        scale, target = in_opening(low, high, on)
    moved = float(np.linalg.norm(target - foot_middle(low, high)))
    if moved < MOVE_LEAST and 1.0 - scale < SHRINK_LEAST:
        return None
    words = f"laid {how} ({on.get('why', '')}): moved {moved:.2f} m" + (
        f", shrunk to {scale:.0%} to fit" if 1.0 - scale >= SHRINK_LEAST else "")
    return scale, target, words


# An object stands where its relation puts it within this, metres (the gate's tolerance: a fitted one is within mm).
HELD_MOST = 0.05


def overhang(low, high, hold_low, hold_high, axes):
    """How far a box reaches past another along `axes`, metres (0 inside it)."""
    return max([0.0, *[max(hold_low[axis] - low[axis], high[axis] - hold_high[axis]) for axis in axes]])


def off_holder(low, high, how, out, box):
    """Metres a box stands off its holder box: top (its foot off the top, its footprint past it), within (past it any
    way), face (its back off the side `out` points from, past that side's span or above its top)."""
    hold_low, hold_high = box
    if how == "top":
        return max(abs(low[1] - hold_high[1]), overhang(low, high, hold_low, hold_high, (0, 2)))
    if how == "within":
        return overhang(low, high, hold_low, hold_high, (0, 1, 2))
    axis = 0 if abs(out[0]) >= abs(out[1]) else 2
    back = abs(low[axis] - hold_high[axis]) if out[axis // 2] > 0 else abs(high[axis] - hold_low[axis])
    return max(back, overhang(low, high, hold_low, hold_high, (2 - axis,)), max(0.0, high[1] - hold_high[1]))


def off_wall(low, high, on):
    """Metres a box stands off a wall's face: its back off the face's line, or past the face's ends."""
    size, middle = high - low, (low + high) / 2
    start, end = (np.array(point, float) for point in on["span"])
    length = float(np.linalg.norm(end - start))
    run, out = (end - start) / max(length, 1e-9), np.asarray(on["out"], float)
    back = abs(float((middle[[0, 2]] - start) @ out) - across(out, size) / 2)
    along, reach = float((middle[[0, 2]] - start) @ run), across(run, size) / 2
    return max(back, max(0.0, reach - along), max(0.0, along + reach - length))


def off_opening(low, high, on):
    """Metres a box stands off its opening: its foot's middle off the opening's, or wider or taller than it."""
    size, foot = high - low, foot_middle(low, high)
    return max(float(np.linalg.norm(foot - np.asarray(on["middle"], float))),
               across(on["along"], size) - float(on["wide"]), size[1] - float(on["tall"]))


def off(low, high, on, holders=()):
    """Metres an object's box (low, high) stands off where its relation `on` puts it; None when its holder lays no
    box to measure against."""
    low, high = np.asarray(low, float), np.asarray(high, float)
    if on["how"] == "wall":
        return off_wall(low, high, on)
    if on["how"] == "in":
        return off_opening(low, high, on)
    boxes = [tuple(np.asarray(end, float) for end in found) for found in holders]
    if not boxes:
        return None
    return off_holder(low, high, on["how"], on.get("out", (0.0, 1.0)), nearest(boxes, low, high))


def held_faults(record, laid):
    """[(object, what is wrong, metres or None)] of the record's design objects as the assembly laid them (`laid`,
    made_waiting.LAID): off where their relation puts them (more than HELD_MOST), a door or window in no opening and
    on no holder, held by nothing (`unheld`), or left at the room's middle (`unplaced`)."""
    boxes = {entry["name"]: (entry["low"], entry["high"]) for entry in [*laid.get("objects", []),
                                                                         *laid.get("holders", [])]}
    faults = []
    for entry in record.get("objects") or []:
        if entry["name"] not in boxes:
            continue
        on = entry.get("on")
        if on:
            distance = off(*boxes[entry["name"]], on, [boxes[name] for name in on.get("holder") or [] if name in boxes])
            if distance is None:
                faults.append((entry["name"], f"its holder {', '.join(on.get('holder') or [])} is not laid", None))
            elif distance > HELD_MOST:
                faults.append((entry["name"], f"{distance:.2f} m off where it is laid {on['how']} ({on.get('why', '')})",
                               round(distance, 3)))
        if entry.get("fills") and not (on and on["how"] in ("in", "face", "within", "top")):
            faults.append((entry["name"], "a door or window in no opening and on no holder", None))
        for mark in ("unheld", "unplaced"):
            if entry.get(mark):
                faults.append((entry["name"], f"{'held by nothing' if mark == 'unheld' else 'at the room middle'}: "
                                              f"{entry[mark]}", None))
    return faults


def world_box(stage, path):
    from pxr import Usd, UsdGeom
    box = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render]) \
        .ComputeWorldBound(stage.GetPrimAtPath(path)).ComputeAlignedRange()
    return np.array(box.GetMin()), np.array(box.GetMax())


def moved_by(prim, foot, scale, target):
    """The prim's transform op set so its world box's foot middle `foot` moves to `target`, shrunk by `scale` about it."""
    from pxr import Gf, Usd, UsdGeom
    parent = UsdGeom.Xformable(prim.GetParent()).ComputeLocalToWorldTransform(Usd.TimeCode.Default()) \
        if prim.GetParent().IsA(UsdGeom.Xformable) else Gf.Matrix4d(1.0)
    change = Gf.Matrix4d().SetTranslate(Gf.Vec3d(*(-foot))) * Gf.Matrix4d().SetScale(float(scale)) \
        * Gf.Matrix4d().SetTranslate(Gf.Vec3d(*target))
    op = UsdGeom.Xformable(prim).GetOrderedXformOps()[0]
    op.Set(op.Get() * parent * change * parent.GetInverse())


def fitted(stage, place, entries, laid):
    """Each laid entry with an `on` (its name in `laid`) fitted on the stage, a holder before what it holds; the fits
    [{name, how, holder, moved, scale, low, high, words}] (its box as laid after), the stage left unsaved."""
    by_name = {entry["name"]: entry for entry in entries if entry.get("on") and entry["name"] in laid}
    done, fits = set(), []

    def one(name, seen=()):
        if name in done or name in seen:
            return
        entry = by_name[name]
        for holder in entry["on"].get("holder") or []:
            if holder in by_name:
                one(holder, (*seen, name))
        done.add(name)
        path, scope = f"/{place}/Objects/{name}", entry["on"].get("holder scope", "Objects")
        holders = [world_box(stage, f"/{place}/{scope}/{holder}") for holder in entry["on"].get("holder") or []
                   if stage.GetPrimAtPath(f"/{place}/{scope}/{holder}")]
        low, high = world_box(stage, path)
        found = fit(low, high, entry["on"], holders)
        if found is None:
            return
        scale, target, words = found
        moved_by(stage.GetPrimAtPath(path), foot_middle(low, high), scale, target)
        from pxr import Sdf
        stage.GetPrimAtPath(path).CreateAttribute("score:fitted", Sdf.ValueTypeNames.String).Set(words)
        after = world_box(stage, path)
        fits.append({"name": name, "row": entry["row"], "how": entry["on"]["how"],
                     "holder": entry["on"].get("holder"), "moved": round(float(np.linalg.norm(
                         target - foot_middle(low, high))), 3), "scale": round(float(scale), 4),
                     "low": [round(float(value), 4) for value in after[0]],
                     "high": [round(float(value), 4) for value in after[1]], "words": words})

    for name in by_name:
        one(name)
    return fits
