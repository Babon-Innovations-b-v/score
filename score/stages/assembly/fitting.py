"""A design's object laid by its relation at its built size (issue #72; bible `architecture/layers`, assembly: the plan
states the relations, the assembly lays by them): its scene record entry's `on` (scene_record/writer.related, from
score/review/holders) says what holds it, and once its baked model and its holder's stand on the stage it is moved, and
shrunk where it does not fit (never grown past its own model), so it sits

    top     on its holder's top, within its footprint (a monitor on its console, a lamp on its desk)
    within  inside its holder's box (plants in their greenhouse, a door in its frame)
    face    with its back on its holder's side `out` points from, within that side's span and height (a garage door on
            its module's front): on the holder's frontmost surface across its own span and height (front_face), and a
            door the bake cut a recess for in that recess, shrunk to fit it beside its room (on_face), out of the room
            each swinging leaf turns through and of its passage (swing_box, passage_box) like a wall's
    wall    with its back on a wall's face (`span`, `out` into the room), within the face's length, out of the room
            each swinging leaf turns through and of its doorway's passage (swing_box, passage_box, on_wall)
    in      in its opening: its middle on the opening's middle at its sill, as wide and tall as the opening at most,
            its middle on the face of its built wall it swings to (its own -z way), else on the wall's room face
            where that wall stands behind the plan's line (opening_spot: hangar's and garage's shell walls stand
            0.15 m behind it), so its swing keeps touching its jamb and clear of it

Boxes are the place's axis-aligned ones (Y up), so a face is the box side nearest `out`; the plan's sizes are
estimates, the built ones are laid (the module's 12 m, not the plan's 17.2). Kept apart from record.py: the light and
settle stages hash it.

    fit(low, high, on, holders, surface, recesses, left, opens, clear)   (scale, the new middle of its foot, words,
                                  its face or None) of one object, or None when it sits
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


def on_face(low, high, on, box, surface=None, recesses=(), clear=()):
    """(scale, foot middle, (the plane its back is on, whether it hangs in a recess)) of an object against its holder
    box's side `out` points from: its back on the holder's frontmost surface across its span and height (front_face;
    else the box's side), its recess's room beside it kept within the face's span too, the door shifted inward along
    the face by what that needs (base's garage door at its module's corner). A door the bake cut a recess for (recess_of) is shrunk to fit
    the recess less its room (base's 8.30 m built door covered 2.2 m of solid wall past its 6.6 m recess) and hangs in
    it as a door in its opening does (opening_spot): its hinge edge, on its room's side, at the recess's jamb, its
    middle on the face the recess opens in, from the recess's foot; swung on the line through its edge's middle
    (motion's hinge) it turns about the jamb's corner and keeps touching it (#36, motion@base: hung 0.6 m off the
    jamb, its back on the face, the shrunk door touched nothing once it swung). Only one whose relation names a recess
    (its `room`, score/review/holders) hangs in one; any other keeps out of the room in `clear` (swing_box,
    passage_box) as a wall's does (face_stretch: street's drying racks hung in its doors' recesses, under their swing,
    so neither door swung, #36 2026-10-30)."""
    size, (hold_low, hold_high) = high - low, box
    room, foot = hold_high - hold_low, foot_middle(low, high)
    axis, side, sign = face_axes(on)
    below, above = beside(on, side)
    scale = min(1.0, room[side] / size[side], room[1] / size[1])
    target, cut = foot.copy(), recess_of(recesses, axis, sign, foot, box) if "room" in on else None
    if cut is not None:
        scale = min(scale, (cut[1][side] - cut[0][side] - below - above) / size[side],
                    (cut[1][1] - cut[0][1]) / size[1])
        half_wide = size[side] * scale / 2
        target[side] = cut[0][side] + half_wide if below > above else cut[1][side] - half_wide if above > below \
            else (cut[0][side] + cut[1][side]) / 2
        target[1] = float(cut[0][1])
    else:
        target[1] = float(np.clip(foot[1], hold_low[1], hold_high[1] - size[1] * scale))
        begin, end = face_stretch(foot, size, on, box, (target[1], target[1] + size[1] * scale), clear)
        if end - begin < hold_high[side] - above - hold_low[side] - below - 1e-9:  # a stretch short of the whole face
            scale = min(scale, (end - begin) / size[side])
        target[side] = kept_within(foot[side], begin, end, size[side] * scale / 2)
    half = size * scale / 2
    span = (target[side] - half[side] - below - FACE_REACH, target[side] + half[side] + above + FACE_REACH)
    face = front_face(surface, axis, sign, side, span, (target[1], target[1] + size[1] * scale))
    face = (hold_high[axis] if sign > 0 else hold_low[axis]) if face is None else face
    target[axis] = face if cut is not None else face + sign * half[axis]
    return scale, target, (float(target[axis] - sign * half[axis]), cut is not None)


def face_stretch(foot, size, on, box, band, clear=()):
    """(from, to) along the face of a holder box `out` points from, less its recess's room beside the object, that an
    object of `size` at `foot` stands in out of the swing and passage boxes `clear` within its depth of the face and
    its height `band` (stretches, stretch_for): the whole face where none does."""
    (hold_low, hold_high), (axis, side, sign) = box, face_axes(on)
    below, above = beside(on, side)
    start, run, out = np.zeros(2), np.zeros(2), np.zeros(2)
    start[side // 2], start[axis // 2] = hold_low[side] + below, hold_high[axis] if sign > 0 else hold_low[axis]
    run[side // 2], out[axis // 2] = 1.0, sign
    length = float(hold_high[side] - above - start[side // 2])
    begin, end = stretch_for(stretches(start, run, out, length, size[axis], band, clear),
                             float(foot[side] - start[side // 2]), size[side])
    return start[side // 2] + begin, start[side // 2] + end


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


def stretches(start, run, out, length, deep, band, clear):
    """[(from, to)] metres along a wall's face from its start that none of the swing boxes `clear` (swing_box) takes
    within `deep` of the face and the height `band` (low, high); the whole face where none does."""
    taken = []
    for low, high in clear:
        corners = np.array([[x, z] for x in (low[0], high[0]) for z in (low[2], high[2])], float) - start
        off = corners @ out
        if off.max() > 0.0 and off.min() < deep and low[1] < band[1] and high[1] > band[0]:
            taken.append((float((corners @ run).min()), float((corners @ run).max())))
    found, at = [], 0.0
    for begin, end in sorted(taken):
        if begin > at:
            found.append((at, min(begin, length)))
        at = max(at, end)
    return [*found, *([(at, length)] if at < length else [])] or [(0.0, length)]


def stretch_for(free, along, reach):
    """The free stretch (from, to) an object of `reach` along its wall at `along` stands in: the nearest that holds it
    whole, else the longest."""
    whole = [part for part in free if part[1] - part[0] >= reach]
    if not whole:
        return max(free, key=lambda part: part[1] - part[0])
    return min(whole, key=lambda part: abs(kept_within(along, part[0], part[1], reach / 2) - along))


def on_wall(low, high, on, clear=()):
    """(scale, foot middle) of an object with its back on a wall's face, within its length, out of the room a leaf in
    an opening turns through (`clear`, swing_box): in the nearest stretch of the face that holds it, shrunk to the
    longest where none does (#36, garage 2026-10-30: 10 m pipes laid along its walls across both doorways stood in
    the doors' swing, so neither door swung)."""
    size, foot = high - low, foot_middle(low, high)
    start, end = (np.array([point[0], point[1]], float) for point in on["span"])
    length = float(np.linalg.norm(end - start))
    run, out = (end - start) / max(length, 1e-9), np.asarray(on["out"], float)
    reach, along = across(run, size), float((foot[[0, 2]] - start) @ run)
    begin, end = stretch_for(stretches(start, run, out, length, across(out, size), (low[1], high[1]), clear), along,
                             reach)
    scale = min(1.0, (end - begin) / max(reach, 1e-9))
    along = kept_within(along, begin, end, reach * scale / 2)
    spot = start + run * along + out * across(out, size) * scale / 2
    return scale, np.array([spot[0], foot[1], spot[1]])


# A built wall an opening's door is sunk into stands within this of the opening's middle, metres: hangar's and
# garage's shell walls, built 0.15 m behind the plan's line their openings are on (#36, 2026-10-29).
WALL_REACH = 0.5


def wall_face(on, walls, axis, opens=None):
    """The face (along `axis`, across the opening) of the built wall nearest an opening's middle a door hangs on: of a
    wall box (low, high) whose length and height reach the opening within WALL_REACH of its middle and no thicker
    than two WALL_REACH (tube's roof and deck boxes span the whole tube), its side `opens`
    points (+1 or -1 along `axis`: the side the door swings to), else (None) the room face of one standing behind
    the middle, never through it; None when none stands so or the opening runs along neither axis (a round wall's:
    its boxes say nothing of its face)."""
    middle, run = np.asarray(on["middle"], float), 2 - axis
    if max(abs(float(way)) for way in on["along"]) < 0.99:
        return None
    reach = [(low, high) for low, high in walls if low[run] <= middle[run] <= high[run]
             and low[1] <= middle[1] + float(on["tall"]) and high[1] >= middle[1]]
    if opens is None:
        faces = [float(low[axis] if low[axis] > middle[axis] else high[axis]) for low, high in reach
                 if not low[axis] <= middle[axis] <= high[axis]]
        faces = [face for face in faces if abs(face - middle[axis]) <= WALL_REACH]
    else:
        faces = [float(high[axis] if opens > 0 else low[axis]) for low, high in reach
                 if low[axis] - WALL_REACH <= middle[axis] <= high[axis] + WALL_REACH
                 and high[axis] - low[axis] <= 2 * WALL_REACH]  # a wall, never a deck or roof across the room
    return min(faces, key=lambda face: abs(face - middle[axis]), default=None)


def slanted(on):
    """Whether an opening runs along neither axis (its built walls' boxes say nothing of their faces)."""
    return max(abs(float(way)) for way in on["along"]) < 0.99


def slanted_face(on, points, opens):
    """The foot middle of a door in an opening along neither axis on the face of its built wall it swings to: the
    farthest the way `opens` points (across the opening) of the built walls' mesh points (`points`, world [n, 3])
    within WALL_REACH of its span, two WALL_REACH of its middle and WALL_REACH of its sill and head (its jambs'
    corners); None where none stands so. Cockpit's rear doors stood on the plan's line of their slanted wall, 0.37 m
    in front of the built wall's room face, and swung their kind's way into its jamb (#36, 2026-10-30)."""
    middle = np.asarray(on["middle"], float)
    run = np.asarray(on["along"], float) / max(float(np.linalg.norm(on["along"])), 1e-9)
    way = np.asarray(opens, float) - run * float(np.asarray(opens, float) @ run)
    way = way / max(float(np.linalg.norm(way)), 1e-9)
    flat = points[:, [0, 2]] - middle[[0, 2]]
    along_off, across_off = flat @ run, flat @ way
    near = (np.abs(along_off) <= float(on["wide"]) / 2 + WALL_REACH) & (np.abs(across_off) <= 2 * WALL_REACH) \
        & (points[:, 1] >= middle[1] - WALL_REACH) & (points[:, 1] <= middle[1] + float(on["tall"]) + WALL_REACH)
    if not near.any():
        return None
    spot = middle.copy()
    spot[[0, 2]] += way * float(across_off[near].max())
    return spot


def opening_spot(on, walls=(), wide=None, left=None, opens=None, points=None):
    """The foot middle of an object in its opening: the opening's middle, moved across it onto the face of its built
    wall it swings to (`opens`, its own -z way on the floor [x, z]: the door kind's swing turns its left edge that
    way; else the room face, wall_face), so a door stands half in the opening between its jambs, half out, its foot
    on the sill's edge and its hinge at the jamb's corner on that face: swung on the line through its edge's middle
    (motion's hinge) its way it keeps touching the jamb and never reaches into it (garage's doors, laid 0.04 m in
    front of their walls, left them as they swung; hung on the room face, they swung out, their kind's way, into
    their own jambs 0.05 to 0.08 m: #36, 2026-10-30). One narrower than its opening (`wide` across it) stands against
    the jamb its own left edge faces (`left`, its own -x way on the floor [x, z]), where a door hangs (the door
    kind's hinge, data/checks/row-kinds.json: its own left edge): garage's 2.01 m round door, centred in its 2.41 m
    opening, swung on a hinge 0.2 m off its jamb and touched nothing. In a slanted wall a door swinging `opens` stands
    on the face its walls' mesh `points` give (slanted_face)."""
    spot = np.asarray(on["middle"], float).copy()
    axis = 0 if abs(on["along"][1]) >= abs(on["along"][0]) else 2
    side = float(opens[axis // 2]) if opens is not None else 0.0
    face = wall_face(on, walls, axis, float(np.sign(side)) if abs(side) >= 0.9 else None)
    if face is not None:
        spot[axis] = face
    elif slanted(on) and opens is not None and points is not None and len(points):
        spot = next((found for found in [slanted_face(on, points, opens)] if found is not None), spot)
    run = np.asarray(on["along"], float) / max(float(np.linalg.norm(on["along"])), 1e-9)
    lined = float(np.asarray(left, float) @ run) if left is not None else 0.0
    if wide is not None and abs(lined) >= 0.9 and float(on["wide"]) - wide > HELD_MOST:
        spot[[0, 2]] += run * np.sign(lined) * (float(on["wide"]) - wide) / 2
    return spot


def in_opening(low, high, on, walls=(), left=None, opens=None, points=None):
    """(scale, foot middle) of an object in its opening, no wider or taller than it, on the face of its built wall it
    swings to and against the jamb its own left edge faces (opening_spot)."""
    size = high - low
    scale = min(1.0, float(on["wide"]) / max(across(on["along"], size), 1e-9), float(on["tall"]) / size[1])
    return scale, opening_spot(on, walls, across(on["along"], size * scale), left, opens, points)


def fit(low, high, on, holders=(), surface=None, recesses=(), left=None, opens=None, clear=()):
    """(scale, the new middle of its foot, words, its face (on_face's) or None) of an object laid by its relation `on`
    (module docstring), from its box (low, high) and its holders' boxes (an opening's: the built walls), a face's holder's
    `surface` points (an opening's: its built walls' mesh points, slanted_face) and the `recesses` the bake cut in it
    (on_face), an opening's object's own left way (`left`,
    and the way it swings to (`opens`, opening_spot), the swing and passage boxes a wall's or face's object keeps out
    of (`clear`, on_wall, face_stretch); None when it already sits (or
    holds to nothing laid)."""
    low, high = np.asarray(low, float), np.asarray(high, float)
    how, face = on["how"], None
    boxes = [tuple(np.asarray(end, float) for end in found) for found in holders]
    if how in ("top", "within", "face"):
        if not boxes:
            return None
        box = nearest(boxes, low, high)
        if how == "face":
            scale, target, face = on_face(low, high, on, box, surface, recesses, clear)
        else:
            scale, target = on_holder(low, high, how, on, box)
    elif how == "wall":
        scale, target = on_wall(low, high, on, clear)
    else:
        scale, target = in_opening(low, high, on, boxes, left, opens, surface)
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
    """Metres a box stands off its opening: its foot's middle off where it fills it (opening_spot: on either face of
    its built wall, or its room face, centred or, narrower than it, against either jamb: the box says nothing of its
    own frame; in a slanted wall anywhere across it within two WALL_REACH: its boxes say nothing of its faces,
    slanted_face), or wider or taller than it."""
    size, foot = high - low, foot_middle(low, high)
    wide, across_it = across(on["along"], size), (abs(float(on["along"][1])), abs(float(on["along"][0])))
    spots = [opening_spot(on, walls, wide, way, opens) for way in (None, on["along"], np.negative(on["along"]))
             for opens in (None, across_it, np.negative(across_it))]
    run = np.asarray(on["along"], float) / max(float(np.linalg.norm(on["along"])), 1e-9)
    normal = np.array([run[1], 0.0, -run[0]]) if slanted(on) else np.zeros(3)

    def apart(spot):
        off = foot - spot
        return float(np.linalg.norm(off - normal * np.clip(off @ normal, -2 * WALL_REACH, 2 * WALL_REACH)))
    return max(min(apart(spot) for spot in spots),
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
    faced = {fit["name"]: fit for fit in laid.get("fitted", []) if fit.get("face") is not None}
    walls = [(wall["low"], wall["high"]) for wall in laid.get("walls", [])]
    faults = []
    for entry in record.get("objects") or []:
        if entry["name"] not in boxes:
            continue
        on = entry.get("on")
        if on:
            fitted_on = faced.get(entry["name"])
            if fitted_on:  # laid on that face; one hung in its recess keeps no room beside it on the face
                on = dict(on, **{"face at": fitted_on["face"]}, **({"room": 0.0} if fitted_on.get("hung") else {}))
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
    """[(name, (low, high))] of the place's built structure on the stage (its Structure prims, and an inside place's
    Shell, design_shell.py: quarters' door hung in the middle of its shell wall and swung its
    kind's way into its jamb, #36 2026-10-30): what an opening's door is sunk into (opening_spot)."""
    roots = [stage.GetPrimAtPath(f"/{place}/{scope}") for scope in ("Structure", "Shell")]
    return [(child.GetName(), world_box(stage, child.GetPath())) for root in roots if root
            for child in root.GetChildren()]


def wall_points(stage, place):
    """World mesh points [n, 3] of the place's built walls (walls), a slanted wall's faces (slanted_face): never a
    deck or slab under two WALL_REACH tall (camp's dome door, in an opening by no built wall, was hung on its deck's
    corner)."""
    return np.concatenate([np.zeros((0, 3))] + [surface_points(stage, f"/{place}/{scope}/{name}")
                                                for scope in ("Structure", "Shell")
                                                for name, (low, high) in walls_in(stage, place, scope)
                                                if high[1] - low[1] >= 2 * WALL_REACH])


def walls_in(stage, place, scope):
    """[(name, (low, high))] of the children of one of the place's built scopes."""
    root = stage.GetPrimAtPath(f"/{place}/{scope}")
    return [(child.GetName(), world_box(stage, child.GetPath())) for child in root.GetChildren()] if root else []


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


def own_way(stage, path, axis):
    """A prim's own -x (`axis` 0: where a door's hinge edge is) or -z (2: the way a door swings to) way on the floor
    [x, z] as it stands (opening_spot)."""
    from pxr import Usd, UsdGeom
    matrix = np.asarray(UsdGeom.Xformable(stage.GetPrimAtPath(path)).ComputeLocalToWorldTransform(
        Usd.TimeCode.Default()))
    way = -matrix[axis, [0, 2]]
    return way / max(float(np.linalg.norm(way)), 1e-9)


def swing_box(stage, path):
    """The world box (low, high) a leaf in its opening turns through: from its middle its own width out along its own
    -z way (the side the door kind's swing turns its left-edge hinge to, data/checks/row-kinds.json), over its own
    span and height: room nothing laid along a wall may stand in (on_wall)."""
    low, high = world_box(stage, path)
    way = own_way(stage, path, 2)
    axis = 0 if abs(way[0]) >= abs(way[1]) else 2
    middle, wide = (low[axis] + high[axis]) / 2, float(high[2 - axis] - low[2 - axis])
    low, high = low.copy(), high.copy()
    low[axis], high[axis] = (middle, middle + wide) if way[axis // 2] > 0 else (middle - wide, middle)
    return low, high


# A doorway's passage, metres: a person's height (score/review/concepts.PERSON) and a step deep on either side of its
# wall, room nothing laid along a wall or face may stand in (#36, garage 2026-10-30: pipes laid along its walls
# inside ran across both doorways, which swung clear out of the room, so nobody could walk through).
PASSAGE_TALL = 1.8
STEP = 0.75


def passage_box(low, high, on, walls=()):
    """The world box (low, high) of the passage through a leaf laid (low, high) by its relation `on`: an opening's
    width (the leaf's own on a face), a person's height from its foot, and a step deep either side of its built wall's
    faces (wall_face) and of the leaf."""
    low, high = np.array(low, float), np.array(high, float)
    faces = []
    if on["how"] == "in":
        axis = 0 if abs(on["along"][1]) >= abs(on["along"][0]) else 2
        middle, half = float(on["middle"][2 - axis]), float(on["wide"]) / 2
        low[2 - axis], high[2 - axis] = min(low[2 - axis], middle - half), max(high[2 - axis], middle + half)
        faces = [face for way in (-1.0, 1.0) if (face := wall_face(on, walls, axis, way)) is not None]
    else:
        axis = face_axes(on)[0]
    low[axis], high[axis] = min([low[axis], *faces]) - STEP, max([high[axis], *faces]) + STEP
    high[1] = low[1] + PASSAGE_TALL
    return low, high


def moved_by(prim, foot, scale, target):
    """The prim's transform op set so its world box's foot middle `foot` moves to `target`, shrunk by `scale` about it."""
    from pxr import Gf, Usd, UsdGeom
    parent = UsdGeom.Xformable(prim.GetParent()).ComputeLocalToWorldTransform(Usd.TimeCode.Default()) \
        if prim.GetParent().IsA(UsdGeom.Xformable) else Gf.Matrix4d(1.0)
    change = Gf.Matrix4d().SetTranslate(Gf.Vec3d(*(-foot))) * Gf.Matrix4d().SetScale(float(scale)) \
        * Gf.Matrix4d().SetTranslate(Gf.Vec3d(*target))
    op = UsdGeom.Xformable(prim).GetOrderedXformOps()[0]
    op.Set(op.Get() * parent * change * parent.GetInverse())


def swings(row):
    """Whether a row's objects swing as a leaf in their opening: a word of its id is a noun of a row kind whose motion
    is a swing (data/checks/row-kinds.json: a door, hatch or gate; never a window, which stands in its opening)."""
    from score.stages import row_kinds
    nouns = {noun for kind in row_kinds.table().values() if (kind.get("motion") or {}).get("move") == "swing"
             for noun in kind["nouns"]}
    return bool(set(row_kinds.words(row).split()) & nouns)


def fitted(stage, place, entries, laid, cuts=None):
    """Each laid entry with an `on` (its name in `laid`) fitted on the stage, a holder before what it holds: a face
    one against its nearest holder's surface and in the recess the bake cut there (`cuts`, {model: baked.json's cuts}),
    an opening's against the built walls, each swinging one in an opening or on a face (swings) on the face it swings
    to and before any on a wall or face, which keeps out of its swing and its passage; the fits [{name, how, holder, moved, scale, low, high, words, face}]
    (its box as laid after), the stage left unsaved."""
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
        if how == "in" and name in leaves and slanted(entry["on"]):
            surface = wall_points(stage, place)
        clear = [box for leaf in sorted(done & leaves) for box in rooms(leaf)] \
            if how in ("wall", "face") and name not in leaves else ()
        found = fit(low, high, entry["on"], built if how == "in" else [box for _, box in held], surface, recesses,
                    own_way(stage, path, 0), own_way(stage, path, 2) if name in leaves else None, clear)
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
                     **({"face": round(face[0], 4), **({"hung": True} if face[1] else {})} if face is not None
                        else {})})

    def rooms(leaf):
        """The swing box and the passage box of a leaf as laid."""
        path = f"/{place}/Objects/{leaf}"
        return swing_box(stage, path), passage_box(*world_box(stage, path), by_name[leaf]["on"], built)

    leaves = {name for name, entry in by_name.items() if entry["on"]["how"] in ("in", "face") and swings(entry["row"])}
    for name in sorted(by_name, key=lambda name: name not in leaves):  # the leaves first: a wall's things keep clear of them
        one(name)
    return fits
