"""A design's object laid by its relation at its built size (issue #72; bible `architecture/layers`, assembly: the plan
states the relations, the assembly lays by them): its scene record entry's `on` (scene_record/writer.related, from
score/review/holders) says what holds it, and once its baked model and its holder's stand on the stage it is moved, and
shrunk where it does not fit (never grown past its own model), so it sits

    top     on its holder's top, within its footprint (a monitor on its console, a lamp on its desk)
    within  inside its holder's box (plants in their greenhouse, a door in its frame)
    face    with its back on its holder's side `out` points from, within that side's span and height (a garage door on
            its module's front): on the holder's frontmost surface across its own span and height (front_face), and a
            door the bake cut a recess for in that recess, shrunk to fit it beside its room (on_face)
    wall    with its back on a wall's face (`span`, `out` into the room), within the face's length
    in      in its opening: its middle on the opening's middle at its sill, as wide and tall as the opening at most,
            its middle on the built wall's room face where that wall stands behind the plan's line (opening_spot:
            hangar's and garage's shell walls stand 0.15 m behind it)

Boxes are the place's axis-aligned ones (Y up), so a face is the box side nearest `out`; the plan's sizes are
estimates, the built ones are laid (the module's 12 m, not the plan's 17.2). Kept apart from record.py: the light and
settle stages hash it.

    fit(low, high, on, holders, surface, recesses)   (scale, the new middle of its foot, words, its face or None) of
                                  one object, or None when it sits
    fitted(stage, place, entries, laid, cuts)   each laid entry's fit applied on the stage; the fits [{name, ...}]
    off(low, high, on, holders)   metres an object as laid stands off where its relation puts it
    held_faults(record, laid)     [(object, what is wrong, metres or None)]: the assembly's `held` gate
    short_doors(record, laid)     [(object, what is wrong, metres)]: doors short of their openings, named, not failed
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


def beside(on, side):
    """(metres kept free below, above) an object along its holder's face axis `side` (0 x, 2 z): its recess's `room`
    on the side its `room_way` points (both sides where it points none), so its whole recess fits within the face."""
    room, way = float(on.get("room") or 0.0), on.get("room_way") or [0.0, 0.0]
    sign = float(np.sign(way[side // 2])) if room else 0.0
    return (room if sign <= 0 else 0.0, room if sign >= 0 else 0.0) if room else (0.0, 0.0)


def face_axes(on):
    """(the axis `out` runs along, the face's axis along the floor, +1 or -1 the way `out` points) of a face
    relation."""
    out = on.get("out", (0.0, 1.0))
    axis = 0 if abs(out[0]) >= abs(out[1]) else 2
    return axis, 2 - axis, 1.0 if out[axis // 2] > 0 else -1.0


# A face object's back rests on its holder's frontmost surface across its own span widened by its recess's room and
# this, metres, each way, so the face a recess opens in counts and not the recess's back (#36: base's module reaches
# 0.39 m further out than its face only in a lip above its garage door).
FACE_REACH = 0.1


def front_face(points, axis, sign, side, span, band):
    """The frontmost (`sign` along `axis`) of a holder's surface `points` (world, [n, 3]) within `span` along `side`
    and `band` in height, or None with none there."""
    if points is None or not len(points):
        return None
    there = points[(points[:, side] >= span[0]) & (points[:, side] <= span[1]) & (points[:, 1] >= band[0])
                   & (points[:, 1] <= band[1])]
    return float((there[:, axis] * sign).max() * sign) if len(there) else None


def recess_of(recesses, axis, sign, foot, box):
    """The recess box (low, high) the bake cut in the holder's face `out` points from (on that side of the holder's
    middle) nearest the object's foot, or None with none there."""
    middle = (box[0] + box[1]) / 2
    found = [(low, high) for low, high in recesses if ((low + high) / 2 - middle)[axis] * sign > 0]
    return min(found, key=lambda cut: float(np.linalg.norm(((cut[0] + cut[1]) / 2 - foot)[[0, 2]])), default=None)


def on_face(low, high, on, box, surface=None, recesses=()):
    """(scale, foot middle, its face) of an object against its holder box's side `out` points from: its back on the
    holder's frontmost surface across its span and height (front_face; else the box's side), its recess's room beside
    it kept within the face's span too, the door shifted inward along the face by what that needs (base's garage door
    at its module's corner); in the recess the bake cut for it (recess_of), shrunk to fit the recess less its room,
    laid beside that room from the recess's foot, so the recess and the door are one size (#36: base's 8.30 m built
    door covered 2.2 m of solid wall past its 6.6 m recess, and its swing swept past the recess's back)."""
    size, (hold_low, hold_high) = high - low, box
    room, foot = hold_high - hold_low, foot_middle(low, high)
    axis, side, sign = face_axes(on)
    below, above = beside(on, side)
    scale = min(1.0, room[side] / size[side], room[1] / size[1])
    target, cut = foot.copy(), recess_of(recesses, axis, sign, foot, box)
    if cut is not None:
        scale = min(scale, (cut[1][side] - cut[0][side] - below - above) / size[side],
                    (cut[1][1] - cut[0][1]) / size[1])
        target[side], target[1] = (cut[0][side] + below + cut[1][side] - above) / 2, float(cut[0][1])
    else:
        target[side] = kept_within(foot[side], hold_low[side] + below, hold_high[side] - above,
                                   size[side] * scale / 2)
        target[1] = float(np.clip(foot[1], hold_low[1], hold_high[1] - size[1] * scale))
    half = size * scale / 2
    span = (target[side] - half[side] - below - FACE_REACH, target[side] + half[side] + above + FACE_REACH)
    face = front_face(surface, axis, sign, side, span, (target[1], target[1] + size[1] * scale))
    face = (hold_high[axis] if sign > 0 else hold_low[axis]) if face is None else face
    target[axis] = face + sign * half[axis]
    return scale, target, face


def on_holder(low, high, how, on, box):
    """(scale, foot middle) of an object top or within a holder box (`on` its relation)."""
    size, (hold_low, hold_high) = high - low, box
    room = hold_high - hold_low
    foot = foot_middle(low, high)
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


# A built wall an opening's door is sunk into stands within this of the opening's middle, metres: hangar's and
# garage's shell walls, built 0.15 m behind the plan's line their openings are on (#36, 2026-10-29).
WALL_REACH = 0.5


def wall_face(on, walls, axis):
    """The room face (along `axis`, across the opening) of the built wall nearest an opening's middle: of a wall box
    (low, high) whose length and height reach the opening and which stands behind its middle, never through it, within
    WALL_REACH; None when none stands so (a wall built on the plan's line holds its opening's middle) or the opening
    runs along neither axis (a round wall's: its boxes say nothing of its face)."""
    middle, run = np.asarray(on["middle"], float), 2 - axis
    if max(abs(float(way)) for way in on["along"]) < 0.99:
        return None
    faces = [float(low[axis] if low[axis] > middle[axis] else high[axis]) for low, high in walls
             if low[run] <= middle[run] <= high[run] and not low[axis] <= middle[axis] <= high[axis]
             and low[1] <= middle[1] + float(on["tall"]) and high[1] >= middle[1]]
    return min((face for face in faces if abs(face - middle[axis]) <= WALL_REACH),
               key=lambda face: abs(face - middle[axis]), default=None)


def opening_spot(on, walls=()):
    """The foot middle of an object in its opening: the opening's middle, moved across it onto the built wall's room
    face (wall_face), so a door stands half in the opening between its jambs, half out, its foot on the sill's edge
    and its hinge at the jamb's corner: swung on the line through its edge's middle (motion's hinge) it keeps on its
    sill and never reaches into its jamb (garage's doors, laid 0.04 m in front of their walls, left them as they
    swung, #36; sunk into the wall, they swung into its jamb)."""
    spot = np.asarray(on["middle"], float).copy()
    axis = 0 if abs(on["along"][1]) >= abs(on["along"][0]) else 2
    face = wall_face(on, walls, axis)
    if face is not None:
        spot[axis] = face
    return spot


def in_opening(low, high, on, walls=()):
    """(scale, foot middle) of an object in its opening, no wider or taller than it, on its built wall's room face
    (opening_spot)."""
    size = high - low
    scale = min(1.0, float(on["wide"]) / max(across(on["along"], size), 1e-9), float(on["tall"]) / size[1])
    return scale, opening_spot(on, walls)


def fit(low, high, on, holders=(), surface=None, recesses=()):
    """(scale, the new middle of its foot, words, its face or None) of an object laid by its relation `on` (module
    docstring), from its box (low, high) and its holders' boxes (an opening's: the built walls), a face's holder's
    `surface` points and the `recesses` the bake cut in it (on_face); None when it already sits (or holds to nothing
    laid)."""
    low, high = np.asarray(low, float), np.asarray(high, float)
    how, face = on["how"], None
    boxes = [tuple(np.asarray(end, float) for end in found) for found in holders]
    if how in ("top", "within", "face"):
        if not boxes:
            return None
        box = nearest(boxes, low, high)
        if how == "face":
            scale, target, face = on_face(low, high, on, box, surface, recesses)
        else:
            scale, target = on_holder(low, high, how, on, box)
    elif how == "wall":
        scale, target = on_wall(low, high, on)
    else:
        scale, target = in_opening(low, high, on, boxes)
    moved = float(np.linalg.norm(target - foot_middle(low, high)))
    if moved < MOVE_LEAST and 1.0 - scale < SHRINK_LEAST:
        return None
    words = f"laid {how} ({on.get('why', '')}): moved {moved:.2f} m" + (
        f", shrunk to {scale:.0%} to fit" if 1.0 - scale >= SHRINK_LEAST else "")
    return scale, target, words, face


# An object stands where its relation puts it within this, metres (the gate's tolerance: a fitted one is within mm).
HELD_MOST = 0.05


def overhang(low, high, hold_low, hold_high, axes):
    """How far a box reaches past another along `axes`, metres (0 inside it)."""
    return max([0.0, *[max(hold_low[axis] - low[axis], high[axis] - hold_high[axis]) for axis in axes]])


def off_holder(low, high, how, on, box):
    """Metres a box stands off its holder box: top (its foot off the top, its footprint past it), within (past it any
    way), face (its back off the face it was laid on, `face at`, else the side `out` points from, it and its recess's
    room past that side's span, or above its top)."""
    hold_low, hold_high = box
    if how == "top":
        return max(abs(low[1] - hold_high[1]), overhang(low, high, hold_low, hold_high, (0, 2)))
    if how == "within":
        return overhang(low, high, hold_low, hold_high, (0, 1, 2))
    axis, side, sign = face_axes(on)
    below, above = beside(on, side)
    face = on.get("face at")
    face = (hold_high[axis] if sign > 0 else hold_low[axis]) if face is None else float(face)
    back = abs(low[axis] - face) if sign > 0 else abs(high[axis] - face)
    spared_low, spared_high = hold_low.copy(), hold_high.copy()
    spared_low[side], spared_high[side] = hold_low[side] + below, hold_high[side] - above
    return max(back, overhang(low, high, spared_low, spared_high, (side,)), max(0.0, high[1] - hold_high[1]))


def too_narrow(low, high, on, box):
    """Metres a face is too narrow for an object and its recess's room beside it (0 where they fit)."""
    _, side, _ = face_axes(on)
    below, above = beside(on, side)
    return max(0.0, (high[side] - low[side]) + below + above - (box[1][side] - box[0][side]))


def off_wall(low, high, on):
    """Metres a box stands off a wall's face: its back off the face's line, or past the face's ends."""
    size, middle = high - low, (low + high) / 2
    start, end = (np.array(point, float) for point in on["span"])
    length = float(np.linalg.norm(end - start))
    run, out = (end - start) / max(length, 1e-9), np.asarray(on["out"], float)
    back = abs(float((middle[[0, 2]] - start) @ out) - across(out, size) / 2)
    along, reach = float((middle[[0, 2]] - start) @ run), across(run, size) / 2
    return max(back, max(0.0, reach - along), max(0.0, along + reach - length))


def off_opening(low, high, on, walls=()):
    """Metres a box stands off its opening: its foot's middle off where it fills it (opening_spot: on its built wall's
    room face), or wider or taller than it."""
    size, foot = high - low, foot_middle(low, high)
    return max(float(np.linalg.norm(foot - opening_spot(on, walls))),
               across(on["along"], size) - float(on["wide"]), size[1] - float(on["tall"]))


def short_of(low, high, on):
    """Metres an object in its opening falls short of the opening's height (0 where it fills it): hangar's doorway, a
    7.79 m wall panel shrunk evenly to fit its 2.25 m wide, 2.66 m tall opening, stood 0.72 m tall (2026-10-29)."""
    return max(0.0, float(on["tall"]) - float(high[1] - low[1])) if on["how"] == "in" else 0.0


def off(low, high, on, holders=()):
    """Metres an object's box (low, high) stands off where its relation `on` puts it (an opening's: by the built
    walls, `holders`); None when its holder lays no box to measure against."""
    low, high = np.asarray(low, float), np.asarray(high, float)
    if on["how"] == "wall":
        return off_wall(low, high, on)
    boxes = [tuple(np.asarray(end, float) for end in found) for found in holders]
    if on["how"] == "in":
        return off_opening(low, high, on, boxes)
    if not boxes:
        return None
    return off_holder(low, high, on["how"], on, nearest(boxes, low, high))


def held_faults(record, laid):
    """[(object, what is wrong, metres or None)] of the record's design objects as the assembly laid them (`laid`,
    made_waiting.LAID): off where their relation puts them (more than HELD_MOST; a face one off the face it was laid
    on, an opening's by the built walls), a door whose holder's face is too narrow for it and its recess (the
    shortfall), a door or window in no opening and on no holder, held by nothing (`unheld`), or left at the room's
    middle (`unplaced`)."""
    boxes = {entry["name"]: (entry["low"], entry["high"]) for entry in [*laid.get("objects", []),
                                                                         *laid.get("holders", [])]}
    faced = {fit["name"]: fit["face"] for fit in laid.get("fitted", []) if fit.get("face") is not None}
    walls = [(wall["low"], wall["high"]) for wall in laid.get("walls", [])]
    faults = []
    for entry in record.get("objects") or []:
        if entry["name"] not in boxes:
            continue
        on = entry.get("on")
        if on:
            on = dict(on, **{"face at": faced[entry["name"]]}) if entry["name"] in faced else on
            low, high = (np.asarray(end, float) for end in boxes[entry["name"]])
            held = [boxes[name] for name in on.get("holder") or [] if name in boxes] if on["how"] != "in" else walls
            narrow = too_narrow(low, high, on, nearest([tuple(np.asarray(end, float) for end in box) for box in held],
                                                       low, high)) \
                if on["how"] == "face" and on.get("room") and held else 0.0
            if narrow > HELD_MOST:
                faults.append((entry["name"], f"its holder's face is {narrow:.2f} m too narrow for it and its recess",
                               round(narrow, 3)))
            distance = off(*boxes[entry["name"]], on, held)
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


def short_doors(record, laid):
    """[(object, what is wrong, metres)] of the record's objects laid in an opening falling short of its height by
    more than HELD_MOST (short_of): the held gate names them, never failing on them, since only a take made again (a
    paid one) mends them (airlock, garage, hangar, habitat, #36, 2026-10-30)."""
    boxes = {entry["name"]: (entry["low"], entry["high"]) for entry in laid.get("objects", [])}
    found = []
    for entry in record.get("objects") or []:
        on = entry.get("on")
        if on and entry["name"] in boxes:
            short = short_of(*(np.asarray(end, float) for end in boxes[entry["name"]]), on)
            if short > HELD_MOST:
                found.append((entry["name"], f"too small for its opening: {short:.2f} m short of its "
                                             f"{float(on['tall']):.2f} m height", round(short, 3)))
    return found


def walls(stage, place):
    """[(name, (low, high))] of the place's built structure on the stage (its Structure prims): what an opening's door
    is sunk into (opening_spot)."""
    root = stage.GetPrimAtPath(f"/{place}/Structure")
    return [(child.GetName(), world_box(stage, child.GetPath())) for child in (root.GetChildren() if root else [])]


def world_box(stage, path):
    from pxr import Usd, UsdGeom
    box = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render]) \
        .ComputeWorldBound(stage.GetPrimAtPath(path)).ComputeAlignedRange()
    return np.array(box.GetMin()), np.array(box.GetMax())


def meshes(stage, path):
    """[(points in their own frame [n, 3], local-to-world matrix)] of each drawn mesh under a prim (never its guide
    collision hull)."""
    from pxr import Usd, UsdGeom
    return [(np.asarray(UsdGeom.Mesh(prim).GetPointsAttr().Get() or [], float).reshape(-1, 3),
             np.asarray(UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(Usd.TimeCode.Default())))
            for prim in Usd.PrimRange(stage.GetPrimAtPath(path)) if prim.IsA(UsdGeom.Mesh)
            and UsdGeom.Imageable(prim).ComputePurpose() != UsdGeom.Tokens.guide]


def surface_points(stage, path):
    """World points [n, 3] of every mesh under a prim (a face holder's surface, front_face)."""
    return np.concatenate([np.zeros((0, 3))] + [points @ matrix[:3, :3] + matrix[3, :3]
                                                for points, matrix in meshes(stage, path)])


def recess_boxes(stage, path, cuts):
    """World boxes (low, high) of the recesses the bake cut in a holder model (baked.json's `cuts`, in its meshes' own
    frame, score/stages/surfaces/route_bake.recess_box)."""
    found = meshes(stage, path)
    if not found:
        return []
    matrix, boxes = found[0][1], []
    for cut in cuts or []:
        if "recess" in cut:
            low, high = cut["recess"]
            corners = np.array([[x, y, z] for x in (low[0], high[0]) for y in (low[1], high[1])
                                for z in (low[2], high[2])], float) @ matrix[:3, :3] + matrix[3, :3]
            boxes.append((corners.min(axis=0), corners.max(axis=0)))
    return boxes


def moved_by(prim, foot, scale, target):
    """The prim's transform op set so its world box's foot middle `foot` moves to `target`, shrunk by `scale` about it."""
    from pxr import Gf, Usd, UsdGeom
    parent = UsdGeom.Xformable(prim.GetParent()).ComputeLocalToWorldTransform(Usd.TimeCode.Default()) \
        if prim.GetParent().IsA(UsdGeom.Xformable) else Gf.Matrix4d(1.0)
    change = Gf.Matrix4d().SetTranslate(Gf.Vec3d(*(-foot))) * Gf.Matrix4d().SetScale(float(scale)) \
        * Gf.Matrix4d().SetTranslate(Gf.Vec3d(*target))
    op = UsdGeom.Xformable(prim).GetOrderedXformOps()[0]
    op.Set(op.Get() * parent * change * parent.GetInverse())


def fitted(stage, place, entries, laid, cuts=None):
    """Each laid entry with an `on` (its name in `laid`) fitted on the stage, a holder before what it holds: a face
    one against its nearest holder's surface and in the recess the bake cut there (`cuts`, {model: baked.json's cuts}),
    an opening's against the built walls; the fits [{name, how, holder, moved, scale, low, high, words, face}] (its box
    as laid after), the stage left unsaved."""
    by_name = {entry["name"]: entry for entry in entries if entry.get("on") and entry["name"] in laid}
    bakes = {entry["name"]: entry.get("bake") for entry in entries}
    done, fits = set(), []
    built = [box for _, box in walls(stage, place)]

    def one(name, seen=()):
        if name in done or name in seen:
            return
        entry = by_name[name]
        for holder in entry["on"].get("holder") or []:
            if holder in by_name:
                one(holder, (*seen, name))
        done.add(name)
        path, scope, how = f"/{place}/Objects/{name}", entry["on"].get("holder scope", "Objects"), entry["on"]["how"]
        held = [(holder, world_box(stage, f"/{place}/{scope}/{holder}")) for holder in entry["on"].get("holder") or []
                if stage.GetPrimAtPath(f"/{place}/{scope}/{holder}")]
        low, high = world_box(stage, path)
        surface, recesses = None, ()
        if how == "face" and held:
            box = nearest([box for _, box in held], low, high)
            holder = next(holder for holder, found in held if found is box)
            surface = surface_points(stage, f"/{place}/{scope}/{holder}")
            recesses = recess_boxes(stage, f"/{place}/{scope}/{holder}", (cuts or {}).get(bakes.get(holder)))
        found = fit(low, high, entry["on"], built if how == "in" else [box for _, box in held], surface, recesses)
        if found is None:
            return
        scale, target, words, face = found
        moved_by(stage.GetPrimAtPath(path), foot_middle(low, high), scale, target)
        from pxr import Sdf
        stage.GetPrimAtPath(path).CreateAttribute("score:fitted", Sdf.ValueTypeNames.String).Set(words)
        after = world_box(stage, path)
        fits.append({"name": name, "row": entry["row"], "how": how,
                     "holder": entry["on"].get("holder"), "moved": round(float(np.linalg.norm(
                         target - foot_middle(low, high))), 3), "scale": round(float(scale), 4),
                     "low": [round(float(value), 4) for value in after[0]],
                     "high": [round(float(value), 4) for value in after[1]], "words": words,
                     **({"face": round(face, 4)} if face is not None else {})})

    for name in by_name:
        one(name)
    return fits
