"""A design's object laid by its relation at its built size (issue #72; bible `architecture/layers`, assembly: the plan
states the relations, the assembly lays by them): its scene record entry's `on` (scene_record/writer.related, from
score/review/holders) says what holds it, and once its baked model and its holder's stand on the stage it is moved, and
shrunk where it does not fit (never grown past its own model), so it sits

    top     on its holder's top, within its footprint (a monitor on its console, a lamp on its desk)
    within  inside its holder's box (plants in their greenhouse, a door in its frame); one that hangs in it (its
            relation's `hangs`: a spacesuit in its locker) moved back onto the holder's built inside back face,
            touching it (on_back)
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
    ramp    up its way onto its level's built deck: its foot on the ground it stands on, pitched by the slope from
            there to the deck's top over its length, its high end's foot on the deck's near side (ramp_rest)

and a thing nothing holds (no `on`) that starts inside a deck or wall (statics) is moved the least way out of it
(moved_out: airlock's sandbags in its porch deck, its porch post in its wall), and one whose built surface passes up
through a roof's built surface (by the roof's mesh, never its box: a dome's box holds the room under it) is moved down
under it (moved_down, through_roofs). Boxes are the place's axis-aligned ones (Y up), so a face is the box side nearest `out`; the plan's sizes are
estimates, the built ones are laid (the module's 12 m, not the plan's 17.2). Kept apart from record.py: the light and
settle stages hash it.

    fit(low, high, on, holders, surface, recesses, left, opens, clear)   (scale, the new middle of its foot, words,
                                  its face or None) of one object, or None when it sits
    fitted(stage, place, entries, laid, cuts)   each laid entry's fit applied on the stage; the fits [{name, ...}]
    off(low, high, on, holders)   metres an object as laid stands off where its relation puts it
    held_faults(record, laid)     [(object, what is wrong, metres or None)]: the assembly's `held` gate, one left
                                  inside a deck or wall, or up through a roof (laid's `roofs`), its relation does not
                                  lay it in (an opening's door, a passage against its wall: passes) too
    through_roofs(stage, place, names)   [{name, roof, metres}] of the objects passing up through a roof's surface
    short_doors(record, laid)     [(object, what is wrong, metres)]: doors short of their openings, named, not failed
"""
import math

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


# Rays front_face casts at a holder's surface stand this far apart across the object's span and height, metres.
RAY_STEP = 0.05


def front_face(mesh, axis, sign, side, span, band):
    """The frontmost (`sign` along `axis`) of a holder's surface (`mesh`, its world triangles) within `span` along
    `side` and `band` in height: where rays every RAY_STEP over them, cast at it from in front, first meet it; None
    with none met. Its triangles, never its corners: a facade's flat front has corners only at its ends, so within a
    drying rack's 0.12 m the corners seen were a window's back, and two racks stood 1.3 and 2.3 m inside it (#36)."""
    if mesh is None or not len(mesh.faces):
        return None
    grid = [np.linspace(low, high, max(2, int(np.ceil((high - low) / RAY_STEP)) + 1)) for low, high in (span, band)]
    alongs, heights = (values.ravel() for values in np.meshgrid(*grid))
    origins = np.zeros((len(alongs), 3))
    origins[:, side], origins[:, 1] = alongs, heights
    origins[:, axis] = mesh.bounds[1][axis] + 1.0 if sign > 0 else mesh.bounds[0][axis] - 1.0
    directions = np.zeros_like(origins)
    directions[:, axis] = -sign
    hits, _, _ = mesh.ray.intersects_location(origins, directions, multiple_hits=False)
    return float((hits[:, axis] * sign).max() * sign) if len(hits) else None


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
    farthest the way `opens` points (across the opening) of its jambs' mesh points within WALL_REACH of its sill and
    head, a jamb a built wall (`points`, one world [n, 3] a wall) that stands within WALL_REACH of the opening's span
    and two WALL_REACH of its middle from its sill up to its head, each within WALL_REACH; None where none stands so.
    Cockpit's rear doors stood on the plan's line of their slanted wall, 0.37 m in front of the built wall's room face,
    and swung their kind's way into its jamb (#36, 2026-10-30). A deck or a wall under the sill is no jamb: camp's dome
    door was hung on its deck's corner; greenhouse's door, in its dome, 0.86 m out on the tops of the walls under it,
    and swung off them (motion@greenhouse, round 34)."""
    middle = np.asarray(on["middle"], float)
    head = middle[1] + float(on["tall"])
    run = np.asarray(on["along"], float) / max(float(np.linalg.norm(on["along"])), 1e-9)
    way = np.asarray(opens, float) - run * float(np.asarray(opens, float) @ run)
    way = way / max(float(np.linalg.norm(way)), 1e-9)
    faces = []
    for wall in points:
        flat = wall[:, [0, 2]] - middle[[0, 2]]
        along_off, across_off = flat @ run, flat @ way
        beside = (np.abs(along_off) <= float(on["wide"]) / 2 + WALL_REACH) & (np.abs(across_off) <= 2 * WALL_REACH)
        if not beside.any() or wall[beside, 1].min() > middle[1] + WALL_REACH \
                or wall[beside, 1].max() < head - WALL_REACH:
            continue
        near = beside & (wall[:, 1] >= middle[1] - WALL_REACH) & (wall[:, 1] <= head + WALL_REACH)
        faces.extend(across_off[near])
    if not faces:
        return None
    spot = middle.copy()
    spot[[0, 2]] += way * float(max(faces))
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
    start, end = jambs(on, walls, spot)
    if wide is not None and abs(lined) >= 0.9 and end - start - wide > HELD_MOST:
        spot[[0, 2]] += run * ((start + end) / 2 + np.sign(lined) * (end - start - wide) / 2)
    else:
        spot[[0, 2]] += run * (start + end) / 2
    return spot


def jambs(on, walls, spot):
    """(from, to) metres along an opening from its middle between the built jambs beside a door laid at `spot`: the
    nearest faces of the built walls (`walls`, boxes) standing beside it either way at the door's across place and
    half its height, within the opening's own width; the opening's own ends where none stands so, or the opening runs
    along neither axis (its boxes say nothing of its jambs). The lab's 1.896 m opening stood between its entry
    passage's walls 0.632 m thick, centred on its ends: 1.264 m clear (motion@lab, round 35)."""
    half = float(on["wide"]) / 2
    if slanted(on):
        return -half, half
    run_axis = 0 if abs(on["along"][0]) >= abs(on["along"][1]) else 2
    sign, middle = float(np.sign(on["along"][run_axis // 2])), np.asarray(on["middle"], float)
    across, height = 2 - run_axis, middle[1] + float(on["tall"]) / 2
    start, end = -half, half
    for low, high in walls:
        if not (low[across] <= spot[across] <= high[across] and low[1] <= height <= high[1]):
            continue
        near, far = sorted(((low[run_axis] - middle[run_axis]) * sign, (high[run_axis] - middle[run_axis]) * sign))
        if far <= 0.0:
            start = max(start, far)
        elif near >= 0.0:
            end = min(end, near)
    return start, end


def in_opening(low, high, on, walls=(), left=None, opens=None, points=None):
    """(scale, foot middle) of an object in its opening, no taller than it, on the face of its built wall it swings to
    and against the jamb its own left edge faces (opening_spot); one wider than the clear width between its built
    jambs (jambs) held to it across its width alone, as a thin build is held to its row's section (scale then a world
    [x, y, z]), never left standing in its jambs (the lab's 1.447 m door in its 1.264 m clear opening)."""
    size = high - low
    scale = min(1.0, float(on["tall"]) / size[1])
    run_axis = 0 if abs(on["along"][0]) >= abs(on["along"][1]) else 2
    spot = opening_spot(on, walls, None, left, opens, points)
    start, end = jambs(on, walls, spot)
    wide = across(on["along"], size * scale)
    if wide > end - start and not slanted(on):
        scale = np.full(3, scale)
        scale[run_axis] *= (end - start) / wide
        wide = end - start
    elif wide > end - start:
        scale *= (end - start) / wide
        wide = end - start
    return scale, opening_spot(on, walls, wide, left, opens, points)


def fit(low, high, on, holders=(), surface=None, recesses=(), left=None, opens=None, clear=()):
    """(scale, the new middle of its foot, words, its face (on_face's) or None) of an object laid by its relation `on`
    (module docstring), from its box (low, high) and its holders' boxes (an opening's: the built walls), a face's holder's
    `surface` mesh (surface_mesh; an opening's: its built walls' mesh points, one array a wall, slanted_face) and the `recesses` the bake cut in it
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
    moved, least = float(np.linalg.norm(target - foot_middle(low, high))), float(np.min(scale))
    if moved < MOVE_LEAST and 1.0 - least < SHRINK_LEAST:
        return None
    words = f"laid {how} ({on.get('why', '')}): moved {moved:.2f} m" + (
        (f", narrowed to {least:.0%} across to fit" if np.ndim(scale) else f", shrunk to {least:.0%} to fit")
        if 1.0 - least >= SHRINK_LEAST else "")
    return scale, target, words, face


# An object stands where its relation puts it within this, metres (the gate's tolerance: a fitted one is within mm).
HELD_MOST = 0.05
# A ramp's deck is looked for this far past its level's edge, metres (the built deck reaches past the plan's line).
RAMP_PROBE = 0.05


def ramp_deck(on, built):
    """The built box (low, high) a ramp climbs to: of the built statics holding a spot RAMP_PROBE past the middle of
    its level's `edge` along its way `up`, the one whose top is nearest the level's `top`; None with none there."""
    up = np.asarray(on["up"], float)
    probe = np.asarray(on["edge"], float).mean(axis=0) + up * RAMP_PROBE
    decks = [box for box in built if box[0][0] <= probe[0] <= box[1][0] and box[0][2] <= probe[1] <= box[1][2]]
    return min(decks, key=lambda box: abs(float(box[1][1]) - float(on["top"]))) if decks else None


def side_along(box, up, side=min):
    """Where a box's side facing back down a level way `up` [x, z] lies along it (`side` max: its side facing up it)."""
    return side(float(np.array([x, z]) @ up) for x in (box[0][0], box[1][0]) for z in (box[0][2], box[1][2]))


def ramp_rest(low, high, on, built):
    """(pivot, axis, degrees, target) of a ramp laid by its relation `on` (module docstring) from its box (low, high),
    its long side laid up the way `up`: pitched about its low end's foot (`pivot`, about the level `axis` across that
    way, then moved to `target`) by the slope from the ground it stands on to its deck's top over its length, so its
    high end's foot rests on that deck's near side at its top; None with no deck built there (ramp_deck)."""
    deck = ramp_deck(on, built)
    if deck is None:
        return None
    up = np.asarray(on["up"], float)
    length = across(up, high - low)
    angle = math.asin(float(np.clip((float(deck[1][1]) - float(low[1])) / max(length, 1e-9), 0.0, 1.0)))
    way = np.array([up[0], 0.0, up[1]])
    pivot = foot_middle(low, high) - way * length / 2
    reach = side_along(deck, up) - length * math.cos(angle) - float(pivot[[0, 2]] @ up)
    return pivot, np.cross(way, [0.0, 1.0, 0.0]), math.degrees(angle), pivot + way * reach


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


# What a laid object never starts inside unless its relation lays it there (a door in its opening): the shell's decks,
# raised levels and walls (scene_record/writer.shell's names), never a roof by its box (a dome's box holds the room
# under it): a roof by its mesh (ROOF, through_roofs).
STATICS = ("deck", "level", "wall")
ROOF = "roof"
# A wall's box is the wall only where it runs along x or z: no thicker than this across, metres (a slanted wall's box
# holds the room beside it: habitat's, hub's and workshop's walls, 2 to 390 m across).
WALL_THICKEST = 1.0
# The furthest a thing nothing holds is moved out of the structure it starts inside, metres.
OUT_MOST = 1.0
# The rows that climb into the level they reach (a stair at the plan's stair, a ladder): never moved out of its deck.
CLIMBING = ("stair", "stairs", "staircase", "steps", "ladder")
# The rows that join their place through the wall they are laid against (review/holders PASSAGE_WORDS).
PASSING = ("tunnel", "tunnels", "tube", "tubes", "corridor", "corridors")


def statics(built):
    """[(name, (low, high))] of the built structure [(name, (low, high))] that is a deck, a level or a wall running
    along x or z (WALL_THICKEST)."""
    return [(name, box) for name, box in built if name.split("_")[0] in STATICS
            and (name.split("_")[0] != "wall" or min(box[1][0] - box[0][0], box[1][2] - box[0][2]) <= WALL_THICKEST)]


def climbs(entry):
    """Whether an entry's row climbs into the level it reaches (CLIMBING: a stair, a ladder)."""
    return bool(set(str(entry.get("row") or "").split("_")) & set(CLIMBING))


def passes(entry):
    """Whether an entry is a passage laid against its wall (PASSING: a tunnel, a tube), which meets its place from
    outside through that wall (garage's glass tunnel, habitat's corridor tube at its tube door, workshop's tunnels):
    in it by its relation, as a door is in its opening."""
    return bool(entry.get("on")) and entry["on"]["how"] == "wall" and bool(
        set(str(entry.get("row") or "").split("_")) & set(PASSING))


def depths(low, high, box):
    """[x, y, z] metres a box (low, high) reaches into another on each axis (one at most 0: they are apart)."""
    return np.minimum(np.asarray(high, float), box[1]) - np.maximum(np.asarray(low, float), box[0])


def held_in(on):
    """Whether an object's relation lays it into the built structure: in its opening, or held by a structure piece
    (a tube's rib)."""
    return bool(on) and (on["how"] == "in" or on.get("holder scope") == "Structure")


def inside_of(low, high, built):
    """[(name, metres)] of the statics of the built structure a box reaches into by more than HELD_MOST every way."""
    return [(name, round(float(depths(low, high, box).min()), 3)) for name, box in statics(built)
            if depths(low, high, box).min() > HELD_MOST]


def out_of(low, high, box):
    """The least move [x, y, z] that takes a box (low, high) clear of a static's box: on each axis the shorter way past
    either of the static's sides (a cable bundle 4.3 m wide across a 0.14 m wall goes 0.33 m, past the wall's near
    side), the least of those; never down (it would sink under the floor)."""
    ahead = np.asarray(box[1], float) - np.asarray(low, float)
    back = np.asarray(high, float) - np.asarray(box[0], float)
    back[1] = np.inf
    moves = np.where(ahead <= back, ahead, -back)
    axis = int(np.argmin(np.abs(moves)))
    move = np.zeros(3)
    move[axis] = moves[axis]
    return move


def off_ramp(low, high, on, built):
    """Metres a ramp's high end stands off its deck's near side along its way up; None with no deck built there."""
    deck = ramp_deck(on, built)
    if deck is None:
        return None
    up = np.asarray(on["up"], float)
    return abs(side_along((low, high), up, max) - side_along(deck, up))


def off(low, high, on, holders=()):
    """Metres an object's box (low, high) stands off where its relation `on` puts it (an opening's and a ramp's: by
    the built walls, `holders`); None when its holder lays no box to measure against."""
    low, high = np.asarray(low, float), np.asarray(high, float)
    if on["how"] == "wall":
        return off_wall(low, high, on)
    boxes = [tuple(np.asarray(end, float) for end in found) for found in holders]
    if on["how"] == "in":
        return off_opening(low, high, on, boxes)
    if on["how"] == "ramp":
        return off_ramp(low, high, on, boxes)
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
    named_walls = [(wall["name"], (np.asarray(wall["low"], float), np.asarray(wall["high"], float)))
                   for wall in laid.get("walls", [])]
    walls = [box for _, box in named_walls]
    roofed = {}
    for found in laid.get("roofs", []):
        roofed.setdefault(found["name"], []).append(found)
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
            held = walls if on["how"] in ("in", "ramp") else [boxes[name] for name in on.get("holder") or []
                                                              if name in boxes]
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
        if not held_in(on) and not climbs(entry):
            low, high = (np.asarray(end, float) for end in boxes[entry["name"]])
            faults += [(entry["name"], f"laid {depth:.2f} m inside {static}, nothing holding it there", depth)
                       for static, depth in inside_of(low, high, named_walls)
                       if not (passes(entry) and static.split("_")[0] == "wall")]
        if not held_in(on) and not climbs(entry):
            faults += [(entry["name"], f"laid {found['metres']:.2f} m up through {found['roof']}, nothing holding it "
                                       "there", found["metres"]) for found in roofed.get(entry["name"], [])]
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
    """World mesh points [n, 3] of each of the place's built walls (walls), one array a wall: a slanted wall's faces,
    each judged a jamb or not by itself (slanted_face)."""
    return [surface_points(stage, f"/{place}/{scope}/{name}") for scope in ("Structure", "Shell")
            for name, _ in walls_in(stage, place, scope)]


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
    """World points [n, 3] of every mesh under a prim (a built wall's, slanted_face)."""
    return np.concatenate([np.zeros((0, 3))] + [points @ matrix[:3, :3] + matrix[3, :3]
                                                for points, matrix in meshes(stage, path)])


def surface_mesh(stage, path):
    """The world triangles of every drawn mesh under a prim, as one mesh (a face holder's surface, front_face), each
    face a fan from its first corner; None with none."""
    import trimesh
    from pxr import Usd, UsdGeom
    points, triangles, count = [], [], 0
    for prim in Usd.PrimRange(stage.GetPrimAtPath(path)):
        if not prim.IsA(UsdGeom.Mesh) or UsdGeom.Imageable(prim).ComputePurpose() == UsdGeom.Tokens.guide:
            continue
        mesh = UsdGeom.Mesh(prim)
        own = np.asarray(mesh.GetPointsAttr().Get() or [], float).reshape(-1, 3)
        matrix = np.asarray(UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(Usd.TimeCode.Default()))
        indices, first = np.asarray(mesh.GetFaceVertexIndicesAttr().Get() or [], np.int64), 0
        for corners in np.asarray(mesh.GetFaceVertexCountsAttr().Get() or [], np.int64):
            face = indices[first:first + corners] + count
            triangles += [(face[0], face[step], face[step + 1]) for step in range(1, corners - 1)]
            first += corners
        points.append(own @ matrix[:3, :3] + matrix[3, :3])
        count += len(own)
    if not triangles:
        return None
    return trimesh.Trimesh(np.concatenate(points), np.asarray(triangles, np.int64), process=False)


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

def changed_by(prim, change):
    """The prim's transform op set so its world transform is followed by `change` (a world matrix)."""
    from pxr import Gf, Usd, UsdGeom
    parent = UsdGeom.Xformable(prim.GetParent()).ComputeLocalToWorldTransform(Usd.TimeCode.Default()) \
        if prim.GetParent().IsA(UsdGeom.Xformable) else Gf.Matrix4d(1.0)
    op = UsdGeom.Xformable(prim).GetOrderedXformOps()[0]
    op.Set(op.Get() * parent * change * parent.GetInverse())


def swings(row):
    """Whether a row's objects swing as a leaf in their opening: a word of its id is a noun of a row kind whose motion
    is a swing (data/checks/row-kinds.json: a door, hatch or gate; never a window, which stands in its opening)."""
    from score.stages import row_kinds
    nouns = {noun for kind in row_kinds.table().values() if (kind.get("motion") or {}).get("move") == "swing"
             for noun in kind["nouns"]}
    return bool(set(row_kinds.words(row).split()) & nouns)


def moved_by(prim, foot, scale, target):
    """The prim's transform op set so its world box's foot middle `foot` moves to `target`, shrunk by `scale` about it
    (a number, or a world [x, y, z]: a door held to its opening's clear width, in_opening)."""
    from pxr import Gf
    changed_by(prim, Gf.Matrix4d().SetTranslate(Gf.Vec3d(*(-foot)))
               * Gf.Matrix4d().SetScale(Gf.Vec3d(*np.broadcast_to(np.asarray(scale, float), 3)))
               * Gf.Matrix4d().SetTranslate(Gf.Vec3d(*target)))


def pitched_by(prim, pivot, axis, degrees, target):
    """The prim's transform op set so it turns `degrees` about the world `axis` through `pivot`, which moves to
    `target`."""
    from pxr import Gf
    changed_by(prim, Gf.Matrix4d().SetTranslate(Gf.Vec3d(*(-pivot)))
               * Gf.Matrix4d().SetRotate(Gf.Rotation(Gf.Vec3d(*axis), float(degrees)))
               * Gf.Matrix4d().SetTranslate(Gf.Vec3d(*target)))


def ramped(stage, path, entry, low, high, built):
    """[its fit] of a ramp laid up to its deck on the stage (ramp_rest), [] with no deck built there or none to do."""
    rest = ramp_rest(low, high, entry["on"], built)
    if rest is None:
        return []
    pivot, axis, degrees, target = rest
    moved = float(np.linalg.norm(target - pivot))
    if moved < MOVE_LEAST and degrees < 0.1:
        return []
    pitched_by(stage.GetPrimAtPath(path), pivot, axis, degrees, target)
    words = f"laid ramp ({entry['on'].get('why', '')}): moved {moved:.2f} m, pitched {degrees:.1f} degrees"
    from pxr import Sdf
    stage.GetPrimAtPath(path).CreateAttribute("score:fitted", Sdf.ValueTypeNames.String).Set(words)
    after = world_box(stage, path)
    return [{"name": entry["name"], "row": entry["row"], "how": "ramp", "holder": None, "moved": round(moved, 3),
             "scale": 1.0, "pitch": round(degrees, 2), "low": [round(float(value), 4) for value in after[0]],
             "high": [round(float(value), 4) for value in after[1]], "words": words}]


def hangs_in(entry):
    """Whether a scene record entry hangs within its holder: laid `within` it with the relation's `hangs`
    (score/review/holders.hangs: the docking airlock's spacesuits in their lockers): the assembly hangs it on the
    holder's back (on_back) and its resting check judges it by touching (assembly.hung_within). One that fills its
    holder (a door's window, `fills`) is part of it, never hung."""
    on = entry.get("on") or {}
    return on.get("how") == "within" and bool(on.get("hangs")) and not entry.get("fills")


# The grid a hung object's back and its holder's inside face are met on, metres (hung_back): each cell across and up.
HANG_CELL = 0.05


def back_way(points, low, high, room_middle):
    """(axis 0 x or 2 z, +1 or -1) of a holder's back from an object inside it: opposite the side its surface
    `points` (world [n, 3]) leave open across the object's span and height beyond the object's middle (its open
    front), else opposite the side toward `room_middle` [x, z]."""
    middle = (low + high) / 2
    band = (points[:, 1] >= low[1]) & (points[:, 1] <= high[1])
    for axis, other in ((0, 2), (2, 0)):
        across = band & (points[:, other] >= low[other]) & (points[:, other] <= high[other])
        for sign in (1.0, -1.0):
            if not np.any(across & (sign * (points[:, axis] - middle[axis]) > 0)):
                return axis, -sign
    toward = np.asarray(room_middle, float) - middle[[0, 2]]
    axis = 0 if abs(toward[0]) >= abs(toward[1]) else 2
    return axis, -float(np.sign(toward[0 if axis == 0 else 1]) or 1.0)


def hung_back(own, holder, low, high, room_middle):
    """How far (metres, along the holder's back way: (axis, sign, shift)) an object inside its holder moves until its
    built surface `own` (world points [n, 3]) first meets the holder's inside back face (`holder`'s points behind its
    middle), cell by cell (HANG_CELL across and up); None when no cell holds both."""
    axis, sign = back_way(holder, low, high, room_middle)
    other = 2 if axis == 0 else 0
    middle = (low[axis] + high[axis]) / 2
    behind = holder[sign * (holder[:, axis] - middle) > 0]
    behind = behind[(behind[:, 1] >= low[1]) & (behind[:, 1] <= high[1])
                    & (behind[:, other] >= low[other]) & (behind[:, other] <= high[other])]
    walls, backs = {}, {}
    for cells, depth, found, pick in ((walls, sign * behind[:, axis], behind, min),
                                      (backs, sign * own[:, axis], own, max)):
        for key, value in zip(map(tuple, np.floor(found[:, [other, 1]] / HANG_CELL).astype(int)), depth):
            cells[key] = pick(cells.get(key, value), value)
    gaps = [walls[key] - backs[key] for key in walls.keys() & backs.keys()]
    return (axis, sign, float(min(gaps))) if gaps else None


def on_back(stage, found, low, high, path, held, scope, built):
    """A fit (fit's, or None where it sat) of an object that hangs within its holder moved along the holder's back way
    until it meets the holder's built inside back face (hung_back, on the nearest of `held` [(name, box)] under the
    prim path `scope`), its height and its place across kept; the room's middle from the `built` structure boxes."""
    foot = foot_middle(low, high)
    scale, target, words, face = found if found is not None else (1.0, foot.copy(), "laid within", None)
    target = np.array(target, float)
    box = nearest([box for _, box in held], low, high)
    holder = next(name for name, found_box in held if found_box is box)
    shown = [corner for pair in built for corner in pair] or list(box)
    room_middle = ((np.min(shown, axis=0) + np.max(shown, axis=0)) / 2)[[0, 2]]
    own = (surface_points(stage, path) - foot) * scale + target
    hung = hung_back(own, surface_points(stage, f"{scope}{holder}"), (low - foot) * scale + target,
                     (high - foot) * scale + target, room_middle)
    if hung is None:
        return found
    axis, sign, shift = hung
    target[axis] += sign * shift
    return scale, target, f"{words}, hung {shift * 100:+.1f} cm onto {holder}'s back", face


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
        if how == "ramp":
            fits.extend(ramped(stage, path, entry, low, high, built))
            return
        surface, recesses = None, ()
        if how == "face" and held:
            box = nearest([box for _, box in held], low, high)
            holder = next(holder for holder, found in held if found is box)
            surface = surface_mesh(stage, f"/{place}/{scope}/{holder}")
            recesses = recess_boxes(stage, f"/{place}/{scope}/{holder}", (cuts or {}).get(bakes.get(holder)))
        if how == "in" and name in leaves and slanted(entry["on"]):
            surface = wall_points(stage, place)
        clear = [box for leaf in sorted(done & leaves) for box in rooms(leaf)] \
            if how in ("wall", "face") and name not in leaves else ()
        found = fit(low, high, entry["on"], built if how == "in" else [box for _, box in held], surface, recesses,
                    own_way(stage, path, 0), own_way(stage, path, 2) if name in leaves else None, clear)
        if held and hangs_in(entry):
            found = on_back(stage, found, low, high, path, held, f"/{place}/{scope}/", built)
        if found is None:
            return
        scale, target, words, face = found
        moved_by(stage.GetPrimAtPath(path), foot_middle(low, high), scale, target)
        from pxr import Sdf
        stage.GetPrimAtPath(path).CreateAttribute("score:fitted", Sdf.ValueTypeNames.String).Set(words)
        after = world_box(stage, path)
        fits.append({"name": name, "row": entry["row"], "how": how,
                     "holder": entry["on"].get("holder"), "moved": round(float(np.linalg.norm(
                         target - foot_middle(low, high))), 3), "scale": round(float(np.min(scale)), 4),
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
    loose = [entry for entry in entries if entry["name"] in laid and not entry.get("on") and not climbs(entry)]
    return fits + moved_out(stage, place, loose) + moved_down(stage, place, loose)


def moved_out(stage, place, entries):
    """Each entry laid with nothing holding it (no `on`: a thing on the floor) that starts inside a static of the
    built structure (statics: airlock's sandbags in its porch deck, its porch post in its wall, laid at the plan's
    estimate) moved the least way out of each in turn (out_of), on the stage, where that is OUT_MOST at most (a
    thing further in crosses the structure: hangar's 46 m ship in its 32 m room, left as laid for the held gate to
    name); the fits [{name, how, ...}]. A climbing row (climbs: a stair into its level) is left to its stair."""
    built, fits = statics(walls(stage, place)), []
    for entry in entries:
        path = f"/{place}/Objects/{entry['name']}"
        low, high = world_box(stage, path)
        shift, left = np.zeros(3), []
        for static, box in built:
            if depths(low + shift, high + shift, box).min() > HELD_MOST:
                shift += out_of(low + shift, high + shift, box)
                left.append(static)
        moved = float(np.linalg.norm(shift))
        if not left or moved > OUT_MOST:
            continue
        moved_by(stage.GetPrimAtPath(path), foot_middle(low, high), 1.0, foot_middle(low, high) + shift)
        words = f"moved {moved:.2f} m out of {', '.join(left)}: laid inside it, nothing holding it there"
        from pxr import Sdf
        stage.GetPrimAtPath(path).CreateAttribute("score:fitted", Sdf.ValueTypeNames.String).Set(words)
        after = world_box(stage, path)
        fits.append({"name": entry["name"], "row": entry["row"], "how": "out", "holder": left,
                     "moved": round(moved, 3), "scale": 1.0, "low": [round(float(value), 4) for value in after[0]],
                     "high": [round(float(value), 4) for value in after[1]], "words": words})
    return fits


def roofs(stage, place):
    """[(name, triangles [n, 3, 3] in the world)] of the place's built roofs (its Structure prims named ROOF...): each
    drawn mesh's faces, fanned into triangles."""
    from pxr import Usd, UsdGeom
    root = stage.GetPrimAtPath(f"/{place}/Structure")
    found = []
    for child in root.GetChildren() if root else []:
        if child.GetName().startswith(ROOF):
            found.append((child.GetName(), np.concatenate([np.zeros((0, 3, 3))] + [
                mesh_triangles(prim) for prim in Usd.PrimRange(child) if prim.IsA(UsdGeom.Mesh)
                and UsdGeom.Imageable(prim).ComputePurpose() != UsdGeom.Tokens.guide])))
    return found


def mesh_triangles(prim):
    """[n, 3, 3] world triangles of a mesh prim's faces, each fanned from its first corner."""
    from pxr import Usd, UsdGeom
    mesh = UsdGeom.Mesh(prim)
    matrix = np.asarray(UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(Usd.TimeCode.Default()))
    points = np.asarray(mesh.GetPointsAttr().Get() or [], float).reshape(-1, 3) @ matrix[:3, :3] + matrix[3, :3]
    indices, start, fans = np.asarray(mesh.GetFaceVertexIndicesAttr().Get() or [], int), 0, []
    for count in mesh.GetFaceVertexCountsAttr().Get() or []:
        fans += [(indices[start], indices[start + corner], indices[start + corner + 1]) for corner in range(1, count - 1)]
        start += count
    return points[np.asarray(fans, int).reshape(-1, 3)]


def roof_under(points, triangles):
    """[n] the height of the lowest of a roof's faces over (or under) each point's place on the floor (x, z), NaN where
    none is; a standing face (a dome's rim, a gable's end) lies over no place."""
    corner, first, second = triangles[:, 0], triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0]
    to = points[:, None, :] - corner[None, :, :]
    both = first[:, 0] * second[:, 2] - first[:, 2] * second[:, 0]
    level = np.abs(both) > 1e-12
    both = np.where(level, both, 1.0)
    along = (to[..., 0] * second[None, :, 2] - to[..., 2] * second[None, :, 0]) / both
    across = (first[None, :, 0] * to[..., 2] - first[None, :, 2] * to[..., 0]) / both
    over = level & (along >= 0) & (across >= 0) & (along + across <= 1)
    height = np.where(over, corner[None, :, 1] + along * first[None, :, 1] + across * second[None, :, 1], np.inf)
    lowest = height.min(axis=1)
    return np.where(np.isfinite(lowest), lowest, np.nan)


def through_roof(points, triangles):
    """Metres a built surface's points reach up over a roof's lowest face over them where some of them stand under
    it: the roof's surface passes through the thing (a thing under a dome reaches none; one wholly on it is not through
    it); 0.0 otherwise. Read at the points' convex hull's corners: a roof's height over the floor is concave (a dome, a
    gable, a flat slab), so the most a point reaches over it is at one of them."""
    if len(points) < 2 or not len(triangles):
        return 0.0
    from scipy.spatial import ConvexHull
    from scipy.spatial import QhullError
    try:
        points = points[ConvexHull(points, qhull_options="QJ").vertices]
    except (QhullError, ValueError):
        pass
    low, high = points.min(axis=0), points.max(axis=0)
    near = triangles[(triangles[:, :, [0, 2]].max(axis=1) >= low[[0, 2]]).all(axis=1)
                     & (triangles[:, :, [0, 2]].min(axis=1) <= high[[0, 2]]).all(axis=1)]
    if not len(near):
        return 0.0
    reach = points[:, 1] - roof_under(points, near)
    reach = reach[np.isfinite(reach)]
    # shortcut: read at hull corners only, so a thing reaching out past a roof's edge is read at its corners under it;
    # read every point should one through a roof go unnamed.
    return round(float(reach.max()), 3) if len(reach) and reach.min() < 0 < reach.max() else 0.0


def through_roofs(stage, place, names, built=None):
    """[{name, roof, metres}] of the laid objects (`names`) whose built surface passes up through a built roof's
    surface (`built`, roofs: the place's) by more than HELD_MOST (through_roof), one for each roof it passes through."""
    built = roofs(stage, place) if built is None else built
    found = []
    for name in names if built else []:
        points = surface_points(stage, f"/{place}/Objects/{name}")
        for roof, triangles in built:
            metres = through_roof(points, triangles)
            if metres > HELD_MOST:
                found.append({"name": name, "roof": roof, "metres": metres})
    return found


def moved_down(stage, place, entries):
    """Each entry laid with nothing holding it (no `on`) whose built surface passes up through a roof's (through_roofs:
    by its mesh, never its box) moved straight down under it, where that is OUT_MOST at most and sinks it into no deck,
    level or wall it was not in (greenhouse's cabinet and tanks on its upper floor under its low roof would have gone
    0.8 to 0.96 m into that floor); one further through or with no room under it is left as laid, for the held gate
    to name; the fits [{name, how, ...}]."""
    built, fits, under = roofs(stage, place), [], statics(walls(stage, place))
    for entry in entries if built else []:
        path = f"/{place}/Objects/{entry['name']}"
        through = through_roofs(stage, place, [entry["name"]], built)
        drop = max([found["metres"] for found in through], default=0.0)
        low, high = world_box(stage, path)
        lowered = (low - [0.0, drop, 0.0], high - [0.0, drop, 0.0])
        if not through or drop > OUT_MOST or {name for name, _ in inside_of(*lowered, under)} - {
                name for name, _ in inside_of(low, high, under)}:
            continue
        moved_by(stage.GetPrimAtPath(path), foot_middle(low, high), 1.0, foot_middle(low, high) - [0.0, drop, 0.0])
        left = [found["roof"] for found in through]
        words = f"moved {drop:.2f} m down out of {', '.join(left)}: laid up through it, nothing holding it there"
        from pxr import Sdf
        stage.GetPrimAtPath(path).CreateAttribute("score:fitted", Sdf.ValueTypeNames.String).Set(words)
        after = world_box(stage, path)
        fits.append({"name": entry["name"], "row": entry["row"], "how": "down", "holder": left, "moved": drop,
                     "scale": 1.0, "low": [round(float(value), 4) for value in after[0]],
                     "high": [round(float(value), 4) for value in after[1]], "words": words})
    return fits
