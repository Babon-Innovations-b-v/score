"""A design's object laid by its relation at its built size (issue #72; bible `architecture/layers`, assembly: the plan
states the relations, the assembly lays by them): its scene record entry's `on` (scene_record/writer.related, from
score/review/holders) says what holds it, and once its baked model and its holder's stand on the stage it is moved, and
shrunk where it does not fit (never grown past its own model), so it sits

    top     on its holder's top, within its footprint (a monitor on its console, a lamp on its desk), then let down
            onto the built surface under it, as is one within it off its shelves (built_tops.let_down)
    within  inside its holder's box (plants in their greenhouse, a door in its frame); one that hangs in it (its
            relation's `hangs`: a spacesuit in its locker) moved back onto the holder's built inside back face,
            touching it (on_back); one on its holder's shelves (on_shelves_of) that crosses its holder's built
            surface standing where it is laid (a box on a shelf unit at the plan's base, through its board) or meets
            one laid in it before, laid on the nearest of the holder's built boards under it it fits on clear of both,
            else on its top (on_boards); of several holders the nearest with such a spot, tried in order of distance,
            then on top of one laid there before (stacked_spots) the same way, and with none on any of them left as laid
            and named crowded (shelved)
    face    with its back on its holder's side `out` points from, within that side's span and height (a garage door on
            its module's front): on the holder's frontmost surface across its own span and height (front_face), and a
            door the bake cut a recess for in that recess, shrunk to fit it beside its room (on_face), out of the room
            each swinging leaf turns through and of its passage (swing_box, passage_box) like a wall's; one the
            record hangs `below` a holder much thinner than it (a lantern on its string) hung under the holder's
            built surface at its built size, its top on it (hung_under)
    wall    with its back on a wall's face (`span`, `out` into the room), within the face's length, out of the room
            each swinging leaf turns through and of its doorway's passage (swing_box, passage_box, on_wall), on the
            front of the built ribs and pillars standing out of the face across it (stood_off); on a slanted wall on
            its built face behind its span, or the nearest along its `out` either way (face_near), its long side
            along it (along_its_wall)
    in      in its opening: its middle on the opening's middle at its sill, as wide and tall as the opening at most,
            its middle on the face of its built wall it swings to (its own -z way), else on the wall's room face
            where that wall stands behind the plan's line (opening_spot: hangar's and garage's shell walls stand
            0.15 m behind it), so its swing keeps touching its jamb and clear of it
    ramp    up its way onto its level's built deck: its foot on the ground it stands on, pitched by the slope from
            there to the deck's top over its length, its high end's foot on the deck's near side (ramp_rest)

and things nothing holds (no `on`) laid at their built size inside each other, a fixture or a wall are parted on the
floor at that size, each in its own room and on its deck (on_deck), by the plan fixes' relation solver and then the
nearest free spot (parted; a thin rug under a table is no overlap, a thin turned thing is judged by its outline,
thin_outline; one with no free spot is named, crowded_faults), and one still inside a deck or
wall (statics) is moved the least way out of it
(moved_out: airlock's sandbags in its porch deck, its porch post in its wall), and one whose built surface passes up
through a roof's built surface (by the roof's mesh, never its box: a dome's box holds the room under it) is moved down
under it (moved_down, through_roofs), and one hung from the roof (`under roof`) built shorter than its reading moved up
to the roof's built underside over it (hung_up), and one whose parts under the roof still touch none of it (its tallest
part up in the roof's opening) moved up until they do (hung_by_parts); a wall thing standing outside its place's walls (a passage) moved out
past the walls and decks it reaches into (moved_past); and the things on the tops of the same holders that meet
there spread evenly along the run their tops make, in rows across it where one line does not hold them
(spread_on_tops). Boxes are the place's axis-aligned ones (Y up),
so a face is the box side nearest `out`; the plan's sizes are estimates, the built ones are laid (the module's 12 m,
not the plan's 17.2). Kept apart from record.py: the light and settle stages hash it.

    fit(low, high, on, holders, surface, recesses, left, opens, clear)   (scale, the new middle of its foot, words,
                                  its face or None) of one object, or None when it sits
    fitted(stage, place, entries, laid, cuts)   each laid entry's fit applied on the stage; the fits [{name, ...}]
    off(low, high, on, holders)   metres an object as laid stands off where its relation puts it
    held_faults(record, laid)     [(object, what is wrong, metres or None)]: the assembly's `held` gate, one left
                                  inside a deck or wall, or up through a roof (laid's `roofs`), its relation does not
                                  lay it in (an opening's door, a passage against its wall: passes) too, and two
                                  things inside each other, held or not, but for one holding the other
    through_roofs(stage, place, names)   [{name, roof, metres}] of the objects passing up through a roof's surface
    short_doors(record, laid)     [(object, what is wrong, metres)]: doors short of their openings, named, not failed
"""
import itertools
import math

import numpy as np

from score.stages.assembly import board_spots, floor_clear, passages, wall_clear

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
        band, whole = (target[1], target[1] + size[1] * scale), hold_high[side] - above - hold_low[side] - below
        begin, end = face_stretch(foot, size, on, box, band, clear)
        if end - begin < whole - 1e-9:  # a stretch short of the whole face
            scale = min(scale, (end - begin) / size[side])
        target[side] = kept_within(foot[side], begin, end, size[side] * scale / 2)
        face = front_face(surface, axis, sign, side, (target[side] - size[side] * scale / 2 - below - FACE_REACH,
                                                      target[side] + size[side] * scale / 2 + above + FACE_REACH), band)
        if face is not None and clear:  # the things laid before it measured off the surface it stands on, not the
            begin, end = face_stretch(foot, size, on, box, band, clear, face)  # box's side (wreck's solar panels on
            scale = min(scale, (end - begin) / size[side]) if end - begin < whole - 1e-9 else scale  # its lander's
            target[side] = kept_within(foot[side], begin, end, size[side] * scale / 2)  # frame, 2026-11-11)
        if surface is not None:  # where its back meets nothing of its holder: slid to where it does (lab's valve)
            from score.stages.assembly import face_spots
            target = face_spots.met(surface, on, box, size * scale, target, clear)
    half = size * scale / 2
    span = (target[side] - half[side] - below - FACE_REACH, target[side] + half[side] + above + FACE_REACH)
    face = front_face(surface, axis, sign, side, span, (target[1], target[1] + size[1] * scale))
    face = (hold_high[axis] if sign > 0 else hold_low[axis]) if face is None else face
    target[axis] = face if cut is not None else face + sign * half[axis]
    return scale, target, (float(target[axis] - sign * half[axis]), cut is not None)


def face_stretch(foot, size, on, box, band, clear=(), face=None):
    """(from, to) along the face of a holder box `out` points from (at `face`, its built surface's plane, where given:
    else the box's side), less its recess's room beside the object, that an object of `size` at `foot` stands in out
    of the swing and passage boxes `clear` within its depth of the face and its height `band` (stretches,
    stretch_for): the whole face where none does."""
    (hold_low, hold_high), (axis, side, sign) = box, face_axes(on)
    below, above = beside(on, side)
    start, run, out = np.zeros(2), np.zeros(2), np.zeros(2)
    start[side // 2], start[axis // 2] = hold_low[side] + below, hold_high[axis] if sign > 0 else hold_low[axis]
    if face is not None:
        start[axis // 2] = float(face)
    run[side // 2], out[axis // 2] = 1.0, sign
    length = float(hold_high[side] - above - start[side // 2])
    begin, end = stretch_for(stretches(start, run, out, length, size[axis], band, clear),
                             float(foot[side] - start[side // 2]), size[side])
    return start[side // 2] + begin, start[side // 2] + end


def hung_under(low, high, box, surface=None, share=None):
    """(1.0, foot middle) of a thing the scene record hangs under a holder much thinner than it (its relation's
    `below`, scene_record/writer.thin_holder: a lantern on its 1 cm string), at its built size: its middle under the
    point of the holder's built surface (`surface`) nearest where it would hang, its top on that point, which touching
    then meets. Where it would hang: its own height under the holder box's foot, at `share` (its relation's `along`)
    of the way along the holder's long run across the floor (hung_run), else at its own place across; with no
    surface, under the box's foot there, kept within the box across. Laid against the string's side, settle@street's
    red paper lanterns were shrunk to 16% and 2% of their size to fit its 1 cm height (2026-11-11)."""
    import trimesh
    size, foot, (hold_low, hold_high) = high - low, foot_middle(low, high), box
    points = np.asarray(surface.vertices, float) if surface is not None and len(surface.faces) else \
        np.array([[x, 0.0, z] for x in (hold_low[0], hold_high[0]) for z in (hold_low[2], hold_high[2])])
    target = foot.copy()
    target[[0, 2]] = foot[[0, 2]] if share is None else hung_run(points, float(share))
    target[[0, 2]] = np.clip(target[[0, 2]], hold_low[[0, 2]], hold_high[[0, 2]])
    top = float(hold_low[1])
    if surface is not None and len(surface.faces):
        hanging = np.array([[target[0], hold_low[1] - size[1], target[2]]])
        met, _, _ = trimesh.proximity.closest_point(surface, hanging)
        target[[0, 2]], top = met[0][[0, 2]], float(met[0][1])
    target[1] = top - size[1]
    return 1.0, target


def hung_run(points, share):
    """The floor point (x, z) `share` of the way along the long run across the floor of a holder's built `points`
    ([n, 3]): their main line across the floor (its way's largest part positive), from their least reach along it to
    their most."""
    across = points[:, [0, 2]]
    middle = across.mean(axis=0)
    way = np.linalg.svd(across - middle, full_matrices=False)[2][0]
    way = way if way[int(np.argmax(np.abs(way)))] > 0 else -way
    reach = (across - middle) @ way
    return middle + way * (reach.min() + (reach.max() - reach.min()) * share)


def hung_off(low, high, box):
    """Metres a thing hung under its thin holder (hung_under) stands off it: its top under the holder box's foot or
    over its top, its middle past the box across."""
    (hold_low, hold_high), middle = box, (np.asarray(low, float) + np.asarray(high, float)) / 2
    return max(float(hold_low[1] - high[1]), float(high[1] - hold_high[1]),
               overhang(middle, middle, hold_low, hold_high, (0, 2)), 0.0)


def on_holder(low, high, how, on, box):
    """(scale, foot middle) of an object top or within a holder box (`on` its relation)."""
    size, (hold_low, hold_high) = high - low, box
    room = hold_high - hold_low
    foot = foot_middle(low, high)
    scale = min(1.0, room[0] / size[0], room[2] / size[2], *([room[1] / size[1]] if how == "within" else []))
    half = size * scale / 2
    target = np.array([kept_within(foot[0], hold_low[0], hold_high[0], half[0]), 0.0,
                       kept_within(foot[2], hold_low[2], hold_high[2], half[2])])
    target[1] = hold_high[1] if how == "top" else hold_low[1] if on.get("under") else \
        float(np.clip(foot[1], hold_low[1], hold_high[1] - size[1] * scale))
    return scale, target


# A thing laid on its holder's boards (on_boards) finds them by rays straight down this many a side over its
# footprint, and the boxes they stand among keep BOARD_CLEAR clear, metres.
BOARD_RAYS = 5
BOARD_CLEAR = 0.01
# A surface of its holder this far over a thing's foot is the board it stands on, bedded in it (an uneven board's top),
# never one it goes through: the resting check's own TOLERANCE, metres.
BOARD_BED = 0.03


# The words a within relation's `why` starts with where the holders put it on its holder's shelves (score/review/holders
# held: its reading's placement word), the one the scene record carries of it.
SHELVES = "on the shelves of "


def on_shelves_of(on):
    """Whether a within relation lays its thing on its holder's shelves (SHELVES), not in it as the plan draws (a sink
    in its counter) or at its foot."""
    return str(on.get("why") or "").startswith(SHELVES)


def board_hits(mesh, low, high):
    """The heights at which rays straight down meet a holder's built surface (`mesh`, surface_mesh's) over a
    footprint (low, high): [the middle ray's, then BOARD_RAYS a side across the footprint's], each an array."""
    import trimesh
    across = [np.linspace(low[axis], high[axis], BOARD_RAYS) for axis in (0, 2)]
    spots = [((low[0] + high[0]) / 2, (low[2] + high[2]) / 2), *((x, z) for x in across[0] for z in across[1])]
    origins = np.array([[x, float(mesh.bounds[1][1]) + 1.0, z] for x, z in spots], float)
    found, rays, _ = trimesh.ray.ray_triangle.RayMeshIntersector(mesh).intersects_location(
        origins, np.tile([0.0, -1.0, 0.0], (len(origins), 1)), multiple_hits=True)
    return [np.asarray(found, float).reshape(-1, 3)[np.asarray(rays) == index, 1] for index in range(len(spots))]


def clear_of(hits, foot, tall):
    """Whether a thing `tall` with its foot at `foot` stands clear of every surface the rays met (`hits`,
    board_hits'): none over BOARD_BED above its foot and under its top."""
    every = np.concatenate(hits)
    return not np.any((every > foot + BOARD_BED) & (every < foot + tall))


# How many points of a holder's surface on_boards samples to find a part of it inside a thing (a side panel the rays
# straight down never meet), besides its corners.
BOARD_SAMPLES = 20000


def crosses(points, low, high):
    """Whether any of a holder's surface `points` [n, 3] lies inside a box (low, high) by more than BOARD_CLEAR (over
    its foot: BOARD_BED): the board under its foot, bedded in it, and one over its top, touching, never do."""
    inner_low = np.asarray(low, float) + [BOARD_CLEAR, BOARD_BED, BOARD_CLEAR]
    inner_high = np.asarray(high, float) - BOARD_CLEAR
    return bool(np.any(np.all((points > inner_low) & (points < inner_high), axis=1)))


def meets_any(low, high, boxes):
    """Whether a box (low, high) reaches into any of `boxes` [(low, high)] by more than BOARD_CLEAR every way."""
    return any(float(depths(low, high, box).min()) > BOARD_CLEAR for box in boxes)


def supported(hits, foot):
    """Whether a thing's foot at `foot` stands on a board over the inner half of its footprint: the middle ray's and
    each inner ray's of board_hits' grid (all but its outer ring) meet a surface within BOARD_BED of it. Galley's jars
    (settle@galley, 2026-11-11): one snapped onto a 5 cm strut that slopes 31 degrees, one over its unit's top edge,
    10 degrees, each met by the middle ray alone."""
    inner = [1 + across * BOARD_RAYS + along for across in range(1, BOARD_RAYS - 1)
             for along in range(1, BOARD_RAYS - 1)]
    return all(np.any(np.abs(hits[index] - foot) <= BOARD_BED) for index in (0, *inner))


def slid_spots(target, box, size, half):
    """{rounded spot: foot middle} of the spots on_boards tries for a thing of `size` (`half` of it) laid at `target`
    within its holder's `box`: from it a step its size and BOARD_CLEAR at a time each way along x and z, each
    combination, kept within the box. Along the holder's longer side alone left galley's jars beside its corner
    shelves' boards, a jar at 1.5 m over none and three on its top (2026-11-11)."""
    hold_low, hold_high = box
    ways = []
    for axis in (0, 2):
        step = float(size[axis]) + BOARD_CLEAR
        ways.append([(axis, way * count * step) for count in
                     range(int((hold_high[axis] - hold_low[axis]) / max(step, 1e-9)) + 1) for way in (1, -1)])
    spots = {}
    for moves in itertools.product(*ways):
        spot = np.array(target, float)
        for axis, move in moves:
            spot[axis] = kept_within(spot[axis] + move, hold_low[axis], hold_high[axis], half[axis])
        spots.setdefault((round(float(spot[0]), 4), round(float(spot[2]), 4)), spot)
    return spots


def on_boards(low, high, scale, target, box, mesh, taken=(), stack=False):
    """The foot middle of a thing laid within its holder (on_holder's `target`, its box (low, high) shrunk by
    `scale`) on the holder's built boards (`mesh`, its surface): where it stands at `target` on a board under the
    inner half of its footprint (supported) crossing no surface of the holder (crosses: a side the rays straight down
    miss too) and meeting none of the boxes laid in it before (`taken`), `target`; else the nearest spot
    to it on such a board (a surface the middle ray meets) with no surface of the holder inside it and none of `taken`,
    slid along and across the holder where its own spot is taken (slid_spots), then at every board_spots.BOARD_PITCH
    along its longer side where that slide finds none; else on the holder's top there (the highest surface under it,
    supported). 2026-11-08: engineroom's 40 cm boxes laid at the plan's 0.5 m base in shelf units with 39 cm
    between boards, through the second board, and two at one spot, which the settle's snap does not lift; galley's
    seven jars at one spot in their corner shelves, over no board. `target` too where its middle meets no board and it
    stands at its holder's foot; one over no board above it is laid on a board like the rest (galley's jar left at
    1.5 m over none, 2026-11-11); else, `stack`ing,
    on top of one laid there before (stacked_spots); None where none of those has a clear spot left (crowded: garage's 12
    boxes piled at two spots of one of its three shelf units, 2026-11-10)."""
    size = (np.asarray(high, float) - np.asarray(low, float)) * scale
    half, tall = size / 2, float(size[1])
    hold_low, hold_high = box

    def footprint(spot):
        return np.array([spot[0] - half[0], spot[1], spot[2] - half[2]]), \
            np.array([spot[0] + half[0], spot[1] + tall, spot[2] + half[2]])

    points = np.vstack([np.asarray(mesh.vertices, float), mesh.sample(BOARD_SAMPLES, seed=0)])

    def clear(hits, spot):
        return clear_of(hits, float(spot[1]), tall) and not crosses(points, *footprint(spot)) \
            and not meets_any(*footprint(spot), taken)

    hits = board_hits(mesh, *footprint(target))
    standing = bool(np.any(np.abs(hits[0] - float(target[1])) <= BOARD_CLEAR))  # on a board as laid
    if (not len(hits[0]) and float(target[1]) <= hold_low[1] + BOARD_BED) or \
            (standing and clear(hits, target) and supported(hits, float(target[1]))):
        return target
    axis = 0 if hold_high[0] - hold_low[0] >= hold_high[2] - hold_low[2] else 2

    def rests_and_tops(tried):
        """([foot middle] on a board clear, [foot middle] on the top clear) over the `tried` spots."""
        rests, tops = [], []
        for spot in tried:
            hits = board_hits(mesh, *footprint(spot))
            if not len(hits[0]):
                continue
            for foot in sorted(set(np.round(hits[0], 4).tolist())):
                if np.any((hits[0] > foot + 1e-4) & (hits[0] <= foot + BOARD_BED)):
                    continue  # a board's underside or a step in its top: its top is the rest
                placed = np.array([spot[0], foot, spot[2]])
                if clear(hits, placed) and supported(hits, foot):
                    rests.append(placed)
            top = np.array([spot[0], float(np.concatenate(hits).max()), spot[2]])
            if not meets_any(*footprint(top), taken) and not crosses(points, *footprint(top)) \
                    and supported(hits, float(top[1])):
                tops.append(top)
        return rests, tops
    rests, tops = rests_and_tops(slid_spots(target, box, size, half).values())
    inside = float(hold_high[1]) - BOARD_BED  # a rest under this is on a board within the holder, not on its top
    if not any(float(spot[1]) < inside for spot in rests):  # a board stretch the slide stepped over (board_spots)
        rests += [spot for spot in rests_and_tops(board_spots.along(target, axis, hold_low, hold_high, half))[0]
                  if float(spot[1]) < inside]
    found = rests or tops or (stacked_spots(footprint, points, taken, box) if stack else [])
    if not found:
        return None
    return min(found, key=lambda spot: float(np.linalg.norm(spot - target)))


def stacked_spots(footprint, points, taken, box):
    """[foot middle] of each spot on top of a thing laid on a holder's board or top (`taken`, their boxes; the
    holder's `box`), never on one stacked itself, where a thing of `footprint` (spot -> its box) stands meeting none of
    them and crossing no surface (`points`) of the holder: the last place a thing on a holder's boards is laid, where
    every board and top is taken (garage's 14 storage boxes, 7 board and top spots on its three shelf units,
    2026-11-11)."""
    hold_low, hold_high = (np.asarray(end, float) for end in box)
    found = []
    for low, high in taken:
        middle = (np.asarray(low, float) + np.asarray(high, float)) / 2
        if not (np.all(middle[[0, 2]] >= hold_low[[0, 2]]) and np.all(middle[[0, 2]] <= hold_high[[0, 2]])) \
                or float(low[1]) > hold_high[1] + BOARD_BED:
            continue
        spot = np.array([middle[0], float(high[1]), middle[2]])
        if not meets_any(*footprint(spot), taken) and not crosses(points, *footprint(spot)):
            found.append(spot)
    return found


def stretches(start, run, out, length, deep, band, clear):
    """[(from, to)] metres along a wall's face from its start that none of the swing boxes `clear` (swing_box) takes
    within `deep` of the face and the height `band` (low, high) (free_stretches); the whole face where none does."""
    return free_stretches(start, run, out, length, deep, band, clear) or [(0.0, length)]


def free_stretches(start, run, out, length, deep, band, clear):
    """[(from, to)] metres along a wall's face from its start that none of the boxes `clear` takes within `deep` of
    the face and the height `band` (low, high); none where they take it all. A box is (low, high), or the corners
    [n, 3] of one turned (oriented_corners: a thing laid along a slanted wall)."""
    taken = []
    for box in clear:
        points = np.asarray(box, float)
        if len(points) == 2:
            points = np.array([[x, y, z] for x in points[:, 0] for y in points[:, 1] for z in points[:, 2]])
        corners = points[:, [0, 2]] - start
        off = corners @ out
        if off.max() > 0.0 and off.min() < deep and points[:, 1].min() < band[1] and points[:, 1].max() > band[0]:
            taken.append((float((corners @ run).min()), float((corners @ run).max())))
    found, at = [], 0.0
    for begin, end in sorted(taken):
        if begin > at:
            found.append((at, min(begin, length)))
        at = max(at, end)
    return [*found, *([(at, length)] if at < length else [])]


def stretch_for(free, along, reach):
    """The free stretch (from, to) an object of `reach` along its wall at `along` stands in: the nearest that holds it
    whole, else the longest."""
    whole = [part for part in free if part[1] - part[0] >= reach]
    if not whole:
        return max(free, key=lambda part: part[1] - part[0])
    return min(whole, key=lambda part: abs(kept_within(along, part[0], part[1], reach / 2) - along))


# A wall thing that meets one laid before it on its wall where no stretch at its height holds it is stood this far
# under it (as the holders' PIECE_GAP stands one over another), metres.
MOUNT_GAP = 0.05


def on_wall(low, high, on, clear=(), mounted=(), corners=None, built=()):
    """(scale, foot middle) of an object with its back on a wall's face, within its length, out of the room a leaf in
    an opening turns through and of the wall and face things laid before it (`clear`, swing_box; `mounted`, their
    boxes): in the nearest stretch of the face that holds it, shrunk to the longest where none does (#36, garage
    2026-10-30: 10 m pipes laid along its walls across both doorways stood in the doors' swing, so neither door swung).
    Where only a thing laid before it leaves no stretch at its height whole, it is stood the nearest height lower,
    MOUNT_GAP under one of them and never under the floor, where one does (mounted_height: habitat's pipes stood 0.25 m
    apart at 0.45 m tall, its kitchen cabinets and hangar's 32 m pipes across each other at its corners, 2026-11-10).
    Its reach along the wall and its depth out of it are its own box's (`corners`, oriented_corners), turned with it,
    where given: a pipe laid along a slanted wall is as deep as its box across, not as its world box (habitat's 3 m
    pipes on its 45 degree walls were laid 1.5 m off them, into each other at the corners, 2026-11-10). On a wall
    running along x or z it stands on the front of the built pieces standing out of the face across its reach
    (`built`, their boxes; stood_off)."""
    size, foot = high - low, foot_middle(low, high)
    on = stood_face(low, high, on, corners, built)
    start, run, out, length = wall_line(on)
    reach, deep = wall_reach(low, high, run, out, corners)
    along = float((foot[[0, 2]] - start) @ run)
    height = mounted_height(start, run, out, length, size, low[1], reach, deep, clear, mounted)
    begin, end = stretch_for(stretches(start, run, out, length, deep, (height, height + size[1]),
                                       [*clear, *mounted]), along, reach)
    scale = min(1.0, (end - begin) / max(reach, 1e-9))
    along = kept_within(along, begin, end, reach * scale / 2)
    spot = start + run * along + out * deep * scale / 2
    return scale, np.array([spot[0], height, spot[1]])


# A wall's face is probed for openings this far in front of its line, and met within this far behind it, metres.
HOLE_FRONT = 0.3
HOLE_DEEP = 1.0


def wall_holes(mesh, on, band):
    """The boxes (corners [8, 3]) of the openings cut through a wall relation's face (`on`, its span and out) within
    a height `band` (low, high): each run of the face where rays every RAY_STEP along it at the band's low, middle and
    high, cast from HOLE_FRONT in front of its line straight at it, meet no built wall (`mesh`, built_walls) within
    HOLE_DEEP, a RAY_STEP past its outermost open rays either way (its edge lies between rays: shiplock's screen
    laid against its hole's measured edge hung 0.02 m over it), as deep as HOLE_FRONT before the line to HOLE_DEEP
    behind it; none with no mesh. A wall thing keeps out
    of them as it keeps out of a door's swing (on_wall's `clear`): walkway's and shiplock's screens hung in holes
    cut through their walls (2026-11-11)."""
    if mesh is None or not len(mesh.faces):
        return []
    start, run, out, length = wall_line(on)
    alongs = np.arange(RAY_STEP / 2, length, RAY_STEP)
    if not len(alongs):
        return []
    heights = np.linspace(band[0], band[1], 3)
    floor = start[None, :] + run[None, :] * alongs[:, None] + out[None, :] * HOLE_FRONT
    origins = np.array([[x, height, z] for x, z in floor for height in heights])
    way = np.array([-out[0], 0.0, -out[1]])
    hits, met, _ = mesh.ray.intersects_location(origins, np.tile(way, (len(origins), 1)), multiple_hits=False)
    near = np.zeros(len(origins), bool)
    near[met[np.linalg.norm(hits - origins[met], axis=1) <= HOLE_FRONT + HOLE_DEEP]] = True
    open_at = ~near.reshape(len(alongs), len(heights)).any(axis=1)
    found, begin = [], None
    for number, opened in enumerate([*open_at, False]):
        if opened and begin is None:
            begin = number
        elif not opened and begin is not None:
            ends = (alongs[begin] - RAY_STEP, alongs[number - 1] + RAY_STEP)  # its edge within a step either way
            found.append(np.array([[*(start + run * along + out * off)[[0]], height, *(start + run * along + out * off)[[1]]]
                                   for along in ends for height in band for off in (-HOLE_DEEP, HOLE_FRONT)]))
            begin = None
    return found


# The rays walls_ahead casts start this far in front of the face and stand this far inside the height band, metres:
# off the face's own triangles and off a deck's top or a roof's underside lying in the band's plane.
AHEAD_OFF = 0.01


def walls_ahead(mesh, on, band, deep):
    """The boxes (corners [8, 3]) of the runs of a wall relation's face (`on`, laid on its built face) where a built
    wall (`mesh`, built_walls) stands in front of it within `deep`, within a height `band` (low, high): each run where
    rays every RAY_STEP along it at the band's low, middle and high, cast from the face straight out, meet a built
    surface within `deep`, or lie past where a built surface crosses the face itself (a ray along it from its middle
    meets one), a RAY_STEP past its outermost met rays either way, `deep` out from the face; none with no mesh. A
    wall thing keeps out of them as it keeps out of a hole cut through its wall (wall_holes): settle@street's drying
    rack 3 was laid on its slanted wall_7 in the sharp corner where wall_8 folds back in front of it, 0.05 m inside
    wall_8 (2026-11-11)."""
    if mesh is None or not len(mesh.faces):
        return []
    start, run, out, length = wall_line(on)
    alongs = np.arange(RAY_STEP / 2, length, RAY_STEP)
    if not len(alongs):
        return []
    heights = np.linspace(band[0] + AHEAD_OFF, band[1] - AHEAD_OFF, 3)
    floor = start[None, :] + run[None, :] * alongs[:, None] + out[None, :] * AHEAD_OFF
    origins = np.array([[x, height, z] for x, z in floor for height in heights])
    way = np.array([out[0], 0.0, out[1]])
    hits, met, _ = mesh.ray.intersects_location(origins, np.tile(way, (len(origins), 1)), multiple_hits=False)
    near = np.zeros(len(origins), bool)
    near[met[np.linalg.norm(hits - origins[met], axis=1) <= deep]] = True
    taken = near.reshape(len(alongs), len(heights)).any(axis=1)
    middle = start + run * length / 2 + out * AHEAD_OFF  # and past where a wall crosses the face itself, outside
    for sign in (1.0, -1.0):
        line = np.array([[middle[0], height, middle[1]] for height in heights])
        hits, met, _ = mesh.ray.intersects_location(line, np.tile([run[0] * sign, 0.0, run[1] * sign], (3, 1)),
                                                    multiple_hits=False)
        if len(met):
            past = length / 2 + sign * float(np.linalg.norm(hits - line[met], axis=1).min())
            taken |= alongs >= past if sign > 0 else alongs <= past
    found, begin = [], None
    for number, blocked in enumerate([*taken, False]):
        if blocked and begin is None:
            begin = number
        elif not blocked and begin is not None:
            ends = (alongs[begin] - RAY_STEP, alongs[number - 1] + RAY_STEP)
            corners = [start + run * along + out * off for along in ends for off in (0.0, deep)]
            found.append(np.array([[corner[0], height, corner[1]] for corner in corners for height in band]))
            begin = None
    return found


def wall_line(on):
    """(start, run, out, length) of a wall relation's face: its span's start [x, z], the unit way along it, the way
    `out` into the room, and its length in metres."""
    start, end = (np.array([point[0], point[1]], float) for point in on["span"])
    length = float(np.linalg.norm(end - start))
    return start, (end - start) / max(length, 1e-9), np.asarray(on["out"], float), length


def wall_reach(low, high, run, out, corners=None):
    """(reach along `run`, depth along `out`) metres of a wall thing: its own turned box's (`corners`,
    oriented_corners) where given, else its world box's (low, high)."""
    if corners is None:
        size = np.asarray(high, float) - np.asarray(low, float)
        return across(run, size), across(out, size)
    floor = np.asarray(corners, float)[:, [0, 2]]
    return float(np.ptp(floor @ run)), float(np.ptp(floor @ out))


def stood_face(low, high, on, corners=None, built=()):
    """A wall relation `on` with its span moved out of its face onto the front of the built pieces standing out of it
    across a wall thing's reach (its box (low, high), its turned `corners`; stood_off), the face the thing is laid
    on (on_wall) and the held gate measures it off; as it is on a slanted wall or with no such piece."""
    if slanted_wall(on):
        return on
    start, run, out, length = wall_line(on)
    reach, deep = wall_reach(low, high, run, out, corners)
    along = float((foot_middle(np.asarray(low, float), np.asarray(high, float))[[0, 2]] - start) @ run)
    stood = stood_off(start, run, out, length, (along - reach / 2, along + reach / 2), deep, (low[1], high[1]), built)
    if stood <= 0.0:
        return on
    return {**on, "span": [[float(value) for value in np.asarray(point, float) + out * stood] for point in on["span"]]}


# The furthest a built piece stands out of a wall's face for a wall thing to stand on its front (stood_off), metres:
# hangar's ribs stand 1.5 m out; a deck or a wall across the room, further, is no piece of the wall.
STAND_OFF_MOST = 2.0


def stood_off(start, run, out, length, reach, deep, band, built):
    """How far out of a wall's face (start, run, out, `length` metres long) a wall thing `deep` across the stretch
    `reach` (from, to) metres along it and the height `band` (low, high) stands: the front of the furthest built piece
    (`built`, its boxes) standing out of the face into it, its middle within the face's length, at most STAND_OFF_MOST
    out and no thicker across than WALL_THICKEST (a slanted wall's or a deck's box holds the room), there; 0 where none
    does. Hangar's 32 m pipes ran through the ribs and pillars standing 1.5 and 0.5 m out of its long walls, 0.33 m
    deep in each (2026-11-11). The walls meeting the face at its ends are no ribs: walkway's 12 m pipe along its whole
    1.37 m wide corridor was stood on the end walls' 1.5 m front, against the wall across (2026-11-11)."""
    found = [0.0]
    for low, high in built:
        if min(high[0] - low[0], high[2] - low[2]) > WALL_THICKEST:
            continue
        corners = np.array([[x, z] for x in (low[0], high[0]) for z in (low[2], high[2])], float) - start
        off, along = corners @ out, corners @ run
        if off.min() < deep and 0.0 < off.max() <= STAND_OFF_MOST and along.min() < reach[1] \
                and along.max() > reach[0] and 0.0 < float(along.min() + along.max()) / 2 < length \
                and low[1] < band[1] and high[1] > band[0]:
            found.append(float(off.max()))
    return max(found)


def mounted_height(start, run, out, length, size, height, reach, deep, clear, mounted):
    """The height a wall thing of `size` laid at `height` stands at on its wall's face (start, run, out, length): its
    own where its longest free stretch there (stretches) among `clear` and `mounted` is as long as among `clear` alone
    (its whole `reach` at most: one longer than its wall is shrunk to the wall all the same); else the nearest lower
    one MOUNT_GAP under one of `mounted`, its foot never under the floor, where it is; else its own. `deep` its depth
    out of the wall."""

    def longest(at, boxes):
        return max((part[1] - part[0] for part in free_stretches(start, run, out, length, deep, (at, at + size[1]),
                                                                  boxes)), default=0.0)

    wanted = min(reach, longest(height, clear)) - 1e-9
    if longest(height, [*clear, *mounted]) >= wanted:
        return height
    lower = sorted({float(np.asarray(other, float)[:, 1].min()) - size[1] - MOUNT_GAP for other in mounted} - {height},
                   reverse=True)
    return next((at for at in lower if 0.0 <= at < height and longest(at, [*clear, *mounted]) >= wanted), height)


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


def hole_wall(on, pieces, mesh):
    """(the relation of an opening along neither axis laid along the straight built wall it was cut in, the degrees
    about +y that turn its `along` that way): of the wall pieces (`pieces`, boxes running along x or z: straight) whose
    run holds the opening's middle and height, within two WALL_REACH of it across, the nearest, where a ray across it
    at the opening's middle height meets no surface (`mesh`, built_walls) inside the wall (a hole is cut through it
    there); its middle on the wall's line, its `along` that run's way; (on, 0) where none is, or where a built wall
    stands at the opening's own ends (own_jambs: it is cut in its own slanted wall). settle@street's
    restaurant door 2: its plan's opening on a slanted plan wall, cut by the kit's shell through the straight wall_2
    0.67 m beside it, was laid slanted across that hole, 0.15 m inside wall_2 (2026-11-11)."""
    if not slanted(on) or mesh is None:
        return on, 0.0
    middle, run = np.asarray(on["middle"], float), np.asarray(on["along"], float)
    height = middle[1] + float(on["tall"]) / 2
    if own_jambs(on, mesh, height):
        return on, 0.0
    found = []
    for low, high in pieces:
        axis = 0 if high[0] - low[0] >= high[2] - low[2] else 2  # the way the wall runs
        cross = 2 - axis
        centre = (low[cross] + high[cross]) / 2
        if not (low[axis] <= middle[axis] <= high[axis] and low[1] <= height <= high[1]) \
                or abs(middle[cross] - centre) > 2 * WALL_REACH:
            continue
        spot, way = middle.copy(), np.zeros(3)
        spot[cross], way[cross] = centre, 1.0
        origin = spot + np.array([0.0, height - spot[1], 0.0]) - way * (high[cross] - low[cross] + WALL_REACH)
        hits, _, _ = mesh.ray.intersects_location(origin[None], way[None])
        inside = [hit for hit in np.asarray(hits, float).reshape(-1, 3)
                  if low[cross] - 1e-6 <= hit[cross] <= high[cross] + 1e-6]
        if not inside:
            found.append((abs(middle[cross] - centre), spot, axis))
    if not found:
        return on, 0.0
    _, spot, axis = min(found, key=lambda one: one[0])
    along = np.zeros(2)
    along[axis // 2] = 1.0 if run[axis // 2] >= 0.0 else -1.0
    unit = run / max(float(np.linalg.norm(run)), 1e-9)
    degrees = math.degrees(math.atan2(unit[1] * along[0] - unit[0] * along[1], float(unit @ along)))
    return {**on, "middle": [float(value) for value in spot], "along": [float(value) for value in along]}, degrees


def own_jambs(on, mesh, height):
    """Whether a built wall (`mesh`) stands on an opening's own line just past either of its ends (2 RAY_STEP), at
    `height`, within WALL_REACH across it: the opening is cut in its own wall (shutter 1 in street's slanted wall_9,
    never moved to wall_8 standing 0.54 m off its middle)."""
    run = np.asarray(on["along"], float) / max(float(np.linalg.norm(on["along"])), 1e-9)
    way = np.array([-run[1], 0.0, run[0]])
    middle = np.asarray(on["middle"], float)
    ends = [middle + np.array([run[0], 0.0, run[1]]) * sign * (float(on["wide"]) / 2 + 2 * RAY_STEP)
            for sign in (1.0, -1.0)]
    origins = np.array([[end[0], height, end[2]] for end in ends]) - way * WALL_REACH
    hits, rays, _ = mesh.ray.intersects_location(origins, np.tile(way, (2, 1)), multiple_hits=False)
    met = np.linalg.norm(np.asarray(hits, float).reshape(-1, 3) - origins[np.asarray(rays, int)], axis=1)
    return bool((met <= 2 * WALL_REACH).any())


# An opening thing's clear run is measured on this many lines across its depth, and its floor under this many points
# a side of its foot (opening_clear).
CLEAR_LINES = 7


def opening_clear(points, on, mesh):
    """(its foot's height, from, to metres along its relation's `along` from its middle) an opening thing (its world
    mesh `points`) has clear of `mesh` (the built walls and the opening things laid before it): the highest surface
    under its foot, and along lines across its depth (CLEAR_LINES) at its foot stood on that, middle and head, the
    nearest surface either way from its middle. settle@street's roller shutters, 0.35 m deep in a 0.1 m wall:
    shutter 1 reached 0.05 m into wall_8 where the street's facade folds back past its opening's end, shutter 2, cut
    into that fold's back wall, into wall_9 before it and 0.1 m into the pavement its sill was cut under
    (2026-11-11)."""
    run = np.asarray(on["along"], float) / max(float(np.linalg.norm(on["along"])), 1e-9)
    normal = np.array([-run[1], run[0]])
    flat = points[:, [0, 2]]
    alongs, acrosses = flat @ run, flat @ normal
    middle = float(alongs.min() + alongs.max()) / 2
    low, high = float(points[:, 1].min()), float(points[:, 1].max())
    inset = min(AHEAD_OFF, (float(np.ptp(acrosses)) / 4))
    lines = np.linspace(acrosses.min() + inset, acrosses.max() - inset, CLEAR_LINES)
    feet = [run * along + normal * across for along in np.linspace(alongs.min(), alongs.max(), CLEAR_LINES)
            for across in lines]
    downs = np.array([[x, (low + high) / 2, z] for x, z in feet])
    hits, rays, _ = mesh.ray.intersects_location(downs, np.tile((0.0, -1.0, 0.0), (len(downs), 1)),
                                                 multiple_hits=False)
    floor = max([float(hit[1]) for hit in np.asarray(hits, float).reshape(-1, 3)], default=low)
    heights = np.linspace(max(low, floor) + AHEAD_OFF, high - AHEAD_OFF, 3)  # at the foot as it is stood up
    origins = np.array([[*(run * middle + normal * across)[[0]], height, *(run * middle + normal * across)[[1]]]
                        for across in lines for height in heights])
    reach = []
    for sign in (1.0, -1.0):
        way = np.array([run[0], 0.0, run[1]]) * sign
        hits, rays, _ = mesh.ray.intersects_location(origins, np.tile(way, (len(origins), 1)), multiple_hits=False)
        met = np.linalg.norm(np.asarray(hits, float).reshape(-1, 3) - origins[np.asarray(rays, int)], axis=1)
        reach.append(float(met.min()) if len(met) else np.inf)
    return floor, -reach[1], reach[0]


def held_clear(stage, path, on, mesh):
    """An opening thing laid in its opening (`on`) held on the stage to what it has clear of `mesh` (opening_clear):
    its foot stood up onto the floor under it, its head kept, and its width held to its clear run, across its width
    alone in an opening along x or z, whole in a slanted one (in_opening's way), moved to that run's middle; the words
    said ("" where it stands clear)."""
    own = surface_mesh(stage, path)
    if own is None or mesh is None:
        return ""
    points = np.asarray(own.vertices, float)
    floor, start, end = opening_clear(points, on, mesh)
    run = np.asarray(on["along"], float) / max(float(np.linalg.norm(on["along"])), 1e-9)
    half = float(np.ptp(points[:, [0, 2]] @ run)) / 2
    bottom, top = float(points[:, 1].min()), float(points[:, 1].max())
    lift = floor - bottom if MOVE_LEAST < floor - bottom < top - bottom else 0.0
    narrow = start > -half + MOVE_LEAST or end < half - MOVE_LEAST
    if (not lift and not narrow) or end - start <= MOVE_LEAST:  # one with no clear run left as laid, for the gate
        return ""
    start, end = (max(start, -half), min(end, half)) if narrow else (-half, half)
    share = (end - start) / (2 * half)
    scale = np.full(3, share) if slanted(on) else np.ones(3)
    if not slanted(on):
        scale[0 if abs(run[0]) >= abs(run[1]) else 2] = share
    scale[1] = min(scale[1], (top - bottom - lift) / (top - bottom))
    foot = foot_middle(*world_box(stage, path))
    target = foot + np.array([run[0], 0.0, run[1]]) * (start + end) / 2 + np.array([0.0, lift, 0.0])
    moved_by(stage.GetPrimAtPath(path), foot, scale, target)
    return "; " + ", ".join(([f"stood up {lift:.2f} m onto the floor under it"] if lift else [])
                            + ([f"held to its clear {end - start:.2f} m"] if narrow else []))


def touching(stage, path, surface):
    """A thing laid on its holder's side moved the least that puts its nearest point on the holder's surface
    (`surface`, its world triangles), where that is more than MOVE_LEAST and FACE_REACH at most; the words said (""
    where it touches, or is too far to be moved so). settle@street's red paper lantern 11, on the 1 cm end of its
    sagging lantern string, stood 0.045 m under the string's end, touching nothing (2026-11-11)."""
    import trimesh
    own = surface_mesh(stage, path)
    if own is None:
        return ""
    met, gaps, _ = trimesh.proximity.closest_point(surface, np.asarray(own.vertices, float))
    nearest = int(np.argmin(gaps))
    if not MOVE_LEAST < float(gaps[nearest]) <= FACE_REACH:
        return ""
    foot = foot_middle(*world_box(stage, path))
    moved_by(stage.GetPrimAtPath(path), foot, 1.0, foot + met[nearest] - np.asarray(own.vertices, float)[nearest])
    return f"; moved {float(gaps[nearest]):.2f} m onto its holder's surface"


def off_faces(stage, path, faces):
    """A thing laid within a holder on a wall (`faces`, the wall relations its holders are laid on: fitted's
    faced_on) moved out along each face's `out` until no point of it beside the face stands behind it; the words said
    ("" where none does). A holder turned along a slanted wall holds the things within it in its world box, which
    reaches behind the wall: settle@street's hanging clothes 3 and 4, within drying rack 2 on wall_7, stood 0.05 m in
    it (2026-11-11)."""
    own = surface_mesh(stage, path)
    if own is None or not faces:
        return ""
    points = np.asarray(own.vertices, float)[:, [0, 2]]
    shift = np.zeros(2)
    for on in faces:
        start, run, out, length = wall_line(on)
        along = (points - start) @ run
        beside = points[(along >= 0.0) & (along <= length)]  # behind the face itself, never past its ends
        if not len(beside):
            continue
        behind = float(((beside + shift - start) @ out).min())
        if behind < -MOVE_LEAST:
            shift = shift - out * behind
    if not shift.any():
        return ""
    foot = foot_middle(*world_box(stage, path))
    moved_by(stage.GetPrimAtPath(path), foot, 1.0, foot + np.array([shift[0], 0.0, shift[1]]))
    return f"; moved {float(np.linalg.norm(shift)):.2f} m out of the wall its holder is laid on"


# What fit says of a thing laid on its holder's boards when no clear spot is left on them (on_boards' None).
CROWDED = "crowded"
# A wall thing shrunk below this to fit its stretch is shrunk to nothing: CROWDED, left as laid (fit).
SCALE_LEAST = 1e-6


def fit(low, high, on, holders=(), surface=None, recesses=(), left=None, opens=None, clear=(), mounted=(),
        corners=None, built=(), stack=False):
    """(scale, the new middle of its foot, words, its face (on_face's) or None) of an object laid by its relation `on`
    (module docstring), from its box (low, high) and its holders' boxes (an opening's: the built walls), a face's holder's
    `surface` mesh (surface_mesh; an opening's: its built walls' mesh points, one array a wall, slanted_face; a within
    one's: its holder's, on_boards) and the `recesses` the bake cut in it
    (on_face), an opening's object's own left way (`left`,
    and the way it swings to (`opens`, opening_spot), the swing and passage boxes a wall's or face's object keeps out
    of (`clear`, on_wall, face_stretch; a within one's: the boxes laid in its holder before it), and a wall's or face's
    the boxes of the wall and face things laid before it (`mounted`, on_wall, on_face), and a wall one's own turned
    box (`corners`, oriented_corners, on_wall) and the built pieces' boxes it stands in front of (`built`, on_wall);
    a within one's whether it may stand on one laid before it (`stack`, on_boards); None when it already
    sits (or
    holds to nothing laid); CROWDED when it is laid on its holder's boards and none has a clear spot left, or on a
    wall with no stretch of it left."""
    low, high = np.asarray(low, float), np.asarray(high, float)
    how, face = on["how"], None
    boxes = [tuple(np.asarray(end, float) for end in found) for found in holders]
    if how in ("top", "within", "face"):
        if not boxes:
            return None
        box = nearest(boxes, low, high)
        if how == "face" and on.get("below"):  # under a holder much thinner than it, at its built size
            scale, target = hung_under(low, high, box, surface, on.get("along"))
        elif how == "face":
            scale, target, face = on_face(low, high, on, box, surface, recesses, [*clear, *mounted])
        else:
            scale, target = on_holder(low, high, how, on, box)
            if how == "within" and surface is not None:
                target = on_boards(low, high, scale, target, box, surface, clear, stack)
                if target is None:
                    return CROWDED
    elif how == "wall":
        scale, target = on_wall(low, high, on, clear, mounted, corners, built)
        if scale < SCALE_LEAST:  # no stretch of its wall left: shrunk to nothing, it would vanish (habitat's third
            return CROWDED       # kitchen cabinet, 2026-11-11: its turned box then had no frame, oriented_corners)
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
    way, but over its top when it stands on it: on_boards; one on its shelves may reach over its top from its top
    board, whose room over it the fitting found clear: storage's bags on their units' open top boards, 2026-11-11), face (its back off the face it was laid on, `face at`,
    else the side `out` points from, it and its recess's room past that side's span, or above its top; one hung
    `below` a thin holder as hung_off measures it)."""
    hold_low, hold_high = box
    if how == "top":  # off its built top where it was let down onto it (built_tops), else its box's top
        return max(abs(low[1] - float(on.get("top at", hold_high[1]))),
                   overhang(low, high, hold_low, hold_high, (0, 2)))
    if how == "within":
        above = 0.0 if on_shelves_of(on) else \
            min(max(0.0, high[1] - hold_high[1]), abs(low[1] - hold_high[1]))  # on its top it stands over it
        return max(overhang(low, high, hold_low, hold_high, (0, 2)), max(0.0, hold_low[1] - low[1]), above,
                   abs(low[1] - hold_low[1]) if on.get("under") else 0.0)
    if on.get("below"):  # hung under its thin holder (hung_under)
        return hung_off(low, high, box)
    axis, side, sign = face_axes(on)
    below, above = beside(on, side)
    face = on.get("face at")
    face = (hold_high[axis] if sign > 0 else hold_low[axis]) if face is None else float(face)
    back = abs(low[axis] - face) if sign > 0 else abs(high[axis] - face)
    spared_low, spared_high = hold_low.copy(), hold_high.copy()
    spared_low[side], spared_high[side] = hold_low[side] + below, hold_high[side] - above
    return max(back, overhang(low, high, spared_low, spared_high, (side,)), max(0.0, high[1] - hold_high[1]))


def stacked_off(low, high, on, holders, others):
    """Metres a thing laid within its holders (`holders`, their boxes) stands off the top of one laid there before
    (`others`, the boxes of the things the same holders hold) it is stacked on (on_boards' `stack`): its foot off that
    one's top, its footprint past the holder it stands over; inf where it stands on none. Garage's boxes 8 to 13,
    stacked on the boxes on its shelf units' tops, were named 0.33 m off their shelves (2026-11-11)."""
    low, high = np.asarray(low, float), np.asarray(high, float)
    under = [np.asarray(box[1], float) for box in others
             if abs(float(box[1][1]) - float(low[1])) <= HELD_MOST and min(high[0], box[1][0]) - max(low[0], box[0][0])
             > HELD_MOST and min(high[2], box[1][2]) - max(low[2], box[0][2]) > HELD_MOST]
    if not under or not holders:
        return np.inf
    hold_low, hold_high = (np.asarray(end, float) for end in nearest(
        [tuple(np.asarray(end, float) for end in box) for box in holders], low, high))
    return max(min(abs(float(top[1]) - float(low[1])) for top in under),
               overhang(low, high, hold_low, hold_high, (0, 2)))


def too_narrow(low, high, on, box):
    """Metres a face is too narrow for an object and its recess's room beside it (0 where they fit)."""
    _, side, _ = face_axes(on)
    below, above = beside(on, side)
    return max(0.0, (high[side] - low[side]) + below + above - (box[1][side] - box[0][side]))


def off_wall(low, high, on, corners=None):
    """Metres a box stands off a wall's face: its back off the face's line, or past the face's ends; by its turned
    box's floor `corners` [[x, z]] where given (laid_face: hub's pipes turned onto its slanted walls stood 0.10 m off
    them by their world boxes, flush by their own, 2026-11-11)."""
    if corners is not None:
        start, run, out, length = wall_line(on)
        floor = np.asarray(corners, float) - start
        alongs = floor @ run
        return max(abs(float((floor @ out).min())), max(0.0, -float(alongs.min())),
                   max(0.0, float(alongs.max()) - length))
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
# The thickest piece laid on the floor (a landing pad, floor grates) a thing nothing holds is moved up out of, metres.
FLOOR_PIECE = 0.3
# The furthest a thing nothing holds is moved out of the structure it starts inside, metres.
OUT_MOST = 1.0
# The rows that climb into the level they reach (a stair at the plan's stair, a ladder): never moved out of its deck.
CLIMBING = ("stair", "stairs", "staircase", "steps", "ladder")
# The rows that join their place through the wall they are laid against (review/holders PASSAGE_WORDS).
PASSING = ("tunnel", "tunnels", "tube", "tubes", "corridor", "corridors")


def statics(built):
    """[(name, (low, high))] of the built structure [(name, (low, high))] that is a deck, a level or a wall running
    along x or z (WALL_THICKEST), or a piece laid on the floor no thicker than FLOOR_PIECE (floor_piece: hangar's
    0.1 m landing pad, a step ladder laid inside it, 2026-11-10)."""
    return [(name, box) for name, box in built if (name.split("_")[0] in STATICS and (
        name.split("_")[0] != "wall" or min(box[1][0] - box[0][0], box[1][2] - box[0][2]) <= WALL_THICKEST))
        or floor_piece(name, box)]


def floor_piece(name, box):
    """Whether a built piece (name, (low, high)) is one laid on the floor (design_shell.floor_pieces: a landing pad,
    floor grates): starting at the floor (within HELD_MOST of 0) and no thicker than FLOOR_PIECE, never a roof's."""
    return name.split("_")[0] != ROOF and float(box[0][1]) <= HELD_MOST and float(box[1][1] - box[0][1]) <= FLOOR_PIECE


def climbs(entry):
    """Whether an entry's row climbs into the level it reaches (CLIMBING: a stair, a ladder): its whole name one, or
    a part of one named first by it (stair_railing); never a thing only named for one (hangar's step_ladder, a
    free-standing object read as a ladder and left inside the 0.1 m landing pad it was laid in, 2026-11-10)."""
    words = str(entry.get("row") or "").split("_")
    return "_".join(words) in CLIMBING or words[0] in CLIMBING


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


def inside_of(low, high, built, corners=None, shapes=None):
    """[(name, metres)] of the statics of the built structure a box reaches into by more than HELD_MOST every way: by
    its turned box (`corners`, oriented_corners: reach_into) where given, against each static's own (`shapes`,
    {name: corners}, wall_corners) where it has one (lab's pipes along its slanted walls, their world boxes in the
    walls' world boxes at the corners, 2026-11-11)."""
    shapes = shapes or {}
    found = [(name, float(depths(low, high, box).min()) if corners is None else
              reach_into(corners, shapes.get(name, box_corners(box)))) for name, box in statics(built)]
    return [(name, round(depth, 3)) for name, depth in found if depth > HELD_MOST]


def wall_corners(stage, path):
    """The 8 corners [8, 3] of a built piece's own box: the least-area rectangle round its drawn points on the floor
    (a slanted wall's turned slab, never its world box, which holds the room beside it), its height theirs; its world
    box's where it draws fewer than three points."""
    points = surface_points(stage, path)
    if len(points) < 3:
        return box_corners(world_box(stage, path))
    floor = points[:, [0, 2]]
    from scipy.spatial import ConvexHull, QhullError
    try:
        floor = floor[ConvexHull(floor, qhull_options="QJ").vertices]
    except (QhullError, ValueError):
        return box_corners(world_box(stage, path))
    best = None
    for start, end in zip(floor, np.roll(floor, -1, axis=0)):
        run = (end - start) / max(float(np.linalg.norm(end - start)), 1e-12)
        across = np.array([-run[1], run[0]])
        along, out = floor @ run, floor @ across
        area = float(np.ptp(along) * np.ptp(out))
        if best is None or area < best[0]:
            best = (area, run, across, (along.min(), along.max()), (out.min(), out.max()))
    _, run, across, alongs, outs = best
    low, high = float(points[:, 1].min()), float(points[:, 1].max())
    return np.array([[*(run * along + across * out)[[0]], height, *(run * along + across * out)[[1]]]
                     for along in alongs for height in (low, high) for out in outs])


def box_corners(box):
    """The 8 corners [8, 3] of an axis-aligned box (low, high), in oriented_corners' order."""
    low, high = (np.asarray(end, float) for end in box)
    return np.array([[x, y, z] for x in (low[0], high[0]) for y in (low[1], high[1]) for z in (low[2], high[2])])


def box_axes(corners):
    """The three unit edge ways of a turned box's corners (oriented_corners' order: x, then y, then z of its own
    frame); a flat edge's left out."""
    found = []
    for edge in (corners[4] - corners[0], corners[2] - corners[0], corners[1] - corners[0]):
        length = float(np.linalg.norm(edge))
        if length > 1e-9:
            found.append(edge / length)
    return found


def reach_into(corners, other):
    """Metres a turned box (its 8 `corners`) reaches into another (its 8): the least overlap of their shadows on the
    world's axes, each box's own edge ways and the level ways across both of their upright faces (separating axes;
    at most 0 when they are apart). Of two boxes square to the world it is depths' least."""
    first, second = np.asarray(corners, float), np.asarray(other, float)
    ways = [np.eye(3)[axis] for axis in range(3)] + box_axes(first) + box_axes(second)
    for one in box_axes(first):
        for two in box_axes(second):
            across = np.cross(one, two)
            if float(np.linalg.norm(across)) > 1e-6:
                ways.append(across / float(np.linalg.norm(across)))
    least = np.inf
    for way in ways:
        mine, theirs = first @ way, second @ way
        least = min(least, float(min(mine.max(), theirs.max()) - max(mine.min(), theirs.min())))
    return least


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
    the built walls, `holders`; a wall's by its turned box's floor `corners`, where the fit gave them); None when its
    holder lays no box to measure against."""
    low, high = np.asarray(low, float), np.asarray(high, float)
    if on["how"] == "wall":
        return off_wall(low, high, on, on.get("corners"))
    boxes = [tuple(np.asarray(end, float) for end in found) for found in holders]
    if on["how"] == "in":
        return off_opening(low, high, on, boxes)
    if on["how"] == "ramp":
        return off_ramp(low, high, on, boxes)
    if not boxes:
        return None
    if on["how"] == "top" and len(boxes) > 1 and top_run(boxes) is not None:  # one run of tops (spread_on_tops):
        return off_holder(low, high, "top", on, (np.min([box[0] for box in boxes], axis=0),  # workshop's box over
                                                 np.max([box[1] for box in boxes], axis=0)))  # two units' meeting
    return off_holder(low, high, on["how"], on, nearest(boxes, low, high))


def held_faults(record, laid):
    """[(object, what is wrong, metres or None)] of the record's design objects as the assembly laid them (`laid`,
    made_waiting.LAID): off where their relation puts them (more than HELD_MOST; a face one off the face it was laid
    on, an opening's by the built walls), a door whose holder's face is too narrow for it and its recess (the
    shortfall), a door or window in no opening and on no holder, held by nothing (`unheld`), left at the room's
    middle (`unplaced`), or two things left inside each other, held or not (crowded_faults). One stacked on the run
    packed over its holder (stacked_on_runs: its fit's how "stacked") is judged on that run."""
    boxes = {entry["name"]: (entry["low"], entry["high"]) for entry in [*laid.get("objects", []),
                                                                         *laid.get("holders", [])]}
    shapes = {entry["name"]: np.asarray(entry["corners"], float) for entry in laid.get("objects", [])
              if len(entry.get("corners") or ()) == 8}
    built_shapes = {wall["name"]: np.asarray(wall["corners"], float) for wall in laid.get("walls", [])
                    if len(wall.get("corners") or ()) == 8}
    faced = {fit["name"]: fit for fit in laid.get("fitted", []) if fit.get("face") is not None}
    walled = {fit["name"]: fit for fit in laid.get("fitted", []) if fit.get("span") is not None}
    holed = {fit["name"]: fit["opening"] for fit in laid.get("fitted", []) if fit.get("opening") is not None}
    stacked = {fit["name"]: fit["holder"] for fit in laid.get("fitted", []) if fit["how"] == "stacked"}
    topped = {fit["name"]: fit.get("top at") for fit in laid.get("fitted", [])}  # its last fit's: stacked after
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
            if topped.get(entry["name"]) is not None:  # let down onto its holder's built top (built_tops)
                on = dict(on, **{"top at": topped[entry["name"]]})
            if on["how"] == "wall" and entry["name"] in walled:  # on the face it was laid on, by its own box
                on = dict(on, **{key: walled[entry["name"]][key] for key in ("span", "out", "corners")})
            if on["how"] == "in" and entry["name"] in holed:  # in the straight wall its hole was cut in (hole_wall)
                on = dict(on, **holed[entry["name"]])
            low, high = (np.asarray(end, float) for end in boxes[entry["name"]])
            held = walls if on["how"] in ("in", "ramp") else [boxes[name] for name in stacked.get(
                entry["name"], on.get("holder") or []) if name in boxes]
            narrow = too_narrow(low, high, on, nearest([tuple(np.asarray(end, float) for end in box) for box in held],
                                                       low, high)) \
                if on["how"] == "face" and on.get("room") and held else 0.0
            if narrow > HELD_MOST:
                faults.append((entry["name"], f"its holder's face is {narrow:.2f} m too narrow for it and its recess",
                               round(narrow, 3)))
            distance = off(*boxes[entry["name"]], on, held)
            if distance is not None and distance > HELD_MOST and on["how"] == "within":
                distance = min(distance, stacked_off(low, high, on, held, [
                    boxes[other["name"]] for other in record.get("objects") or [] if other["name"] != entry["name"]
                    and other["name"] in boxes and set((other.get("on") or {}).get("holder") or [])
                    & set(on.get("holder") or [])]))
            if distance is None:
                faults.append((entry["name"], f"its holder {', '.join(on.get('holder') or [])} is not laid", None))
            elif distance > HELD_MOST:
                faults.append((entry["name"], f"{distance:.2f} m off where it is laid {on['how']} ({on.get('why', '')})",
                               round(distance, 3)))
        if not held_in(on) and not climbs(entry) and not fills_holder(entry):
            low, high = (np.asarray(end, float) for end in boxes[entry["name"]])
            faults += [(entry["name"], f"laid {depth:.2f} m inside {static}, nothing holding it there", depth)
                       for static, depth in inside_of(low, high, named_walls, shapes.get(entry["name"]), built_shapes)
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
    return faults + crowded_faults(record, boxes, shapes)


def fills_holder(entry):
    """Whether an object fills the holder it is laid on (`fills`: a door's window), which stands in its opening, so
    it is in the wall as its holder is (docking_airlock's door window 0.10 m in the wall its door hangs in,
    2026-11-11); crowded_faults leaves it out as well."""
    return bool(entry.get("fills")) and bool(entry.get("on")) and entry["on"]["how"] in ("face", "within", "top")


def crowded_faults(record, boxes, shapes=None):
    """[(object, what is wrong, metres)] of each pair of the record's objects laid inside each other by more than
    HELD_MOST every way (boxes {name: (low, high)} as laid), held or not: two things on the floor parting could not fit
    at their built size (parted: habitat's bunk beds laid across its slanted inner wall, 2026-11-04), two held at one
    spot (galley's seven jars on its corner shelves, quarters' lockers in each other, 2026-11-03), named, never shrunk
    or forced; by their turned boxes (`shapes`, {name: corners}) where both have them. A pair one of which holds the
    other (its relation's `holder`, down a chain: a book on a shelf on a desk) is the relation's to judge, and so is one laid into the structure (held_in), a climbing row or one filling
    its holder (`fills`: a door's window)."""
    entries = [entry for entry in record.get("objects") or [] if entry["name"] in boxes
               and not held_in(entry.get("on")) and not climbs(entry) and not entry.get("fills")]
    holding = holders_of(record)
    names = sorted(entry["name"] for entry in entries)
    shapes = shapes or {}

    def reach(first, second):  # by their turned boxes where both have them (the greenhouse's railings up its stairs)
        if first in shapes and second in shapes:
            return reach_into(shapes[first], shapes[second])
        return float(depths(*boxes[first], [np.asarray(end, float) for end in boxes[second]]).min())
    found = [(first, second, reach(first, second))
             for number, first in enumerate(names) for second in names[number + 1:]
             if second not in holding.get(first, ()) and first not in holding.get(second, ())]
    return [(first, f"laid {depth:.2f} m inside {second} at its built size" +
             ("" if holding.get(first) or holding.get(second) else ", nothing holding either there"),
             round(depth, 3)) for first, second, depth in found if depth > HELD_MOST]


def placement_faults(record, rows):
    """[(object, what is wrong, None)] of the record's objects whose relation is not the one their reading's placement
    word asks (score/review/holders.placement, inventory `rows` {id: row}): one said under its holder or on its
    shelves held other than within it (under: at its foot), one said on its holder's side laid on its top
    (quarters' cables under its desk on the desk top, its poster on the locker's side flat on its top, 2026-11-04)."""
    from score.review import holders  # not at import: holders is in the scene record's key, never this one's
    found = []
    for entry in record.get("objects") or []:
        on, row = entry.get("on") or {}, rows.get(entry.get("row"))
        holder = rows.get(on.get("holder row"))
        if not (row and holder):
            continue
        said = holders.placement(row, holder)
        wrong = (said == "under" and not (on["how"] == "within" and on.get("under"))) or \
            (said == "shelf" and on["how"] != "within") or (said == "side" and on["how"] == "top")
        if wrong:
            found.append((entry["name"], f"laid {on['how']} {holder['id']}, though its reading says "
                                         f"{row.get('where')!r} ({said})", None))
    return found


def holders_of(record):
    """{object: every object holding it, down its chain of relations (its `on`'s `holder`, theirs, ...)} of the
    record's objects."""
    direct = {entry["name"]: set((entry.get("on") or {}).get("holder") or []) for entry in record.get("objects") or []}
    found = {}
    for name in direct:
        seen, more = set(), set(direct[name])
        while more:
            seen |= more
            more = {holder for one in more for holder in direct.get(one, ())} - seen
        found[name] = seen
    return found


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


# A turn onto a built wall's face smaller than this, degrees, is none (on_built_face).
TURN_LEAST = 0.05
# How far in from each end of a wall thing's span, a share of its length, the rays that find its built face are cast
# (on_built_face): a ray from the very end grazes past its wall's corner onto the wall behind.
FACE_INSET = 0.1


def slanted_wall(on):
    """Whether a wall relation's face runs along neither axis (its `out`), by any angle (workshop's tools 7.5 degrees
    off x on a wall built 16 degrees off it)."""
    return min(abs(float(way)) for way in on["out"]) > 1e-6


def built_walls(stage, place):
    """The place's built walls (walls: its Structure and Shell pieces) as one mesh; None with none."""
    import trimesh
    found = [mesh for scope in ("Structure", "Shell") for name, _ in walls_in(stage, place, scope)
             if (mesh := surface_mesh(stage, f"/{place}/{scope}/{name}")) is not None]
    return trimesh.util.concatenate(found) if found else None


def on_built_face(on, height, mesh):
    """(the wall relation laid on the room face of the built wall behind its span, the degrees about +y that turn its
    `out` to that face's): two points of its span FACE_INSET in from its ends each moved back along its `out` onto the
    first surface of `mesh` (built_walls) a ray from WALL_REACH out in front of the point at `height` meets going back,
    within 2 WALL_REACH, its ends laid square onto the line through the two, and its `out` that line's normal on the
    room's side; (as it is, 0) where either ray meets none. Workshop's slanted walls were built 3 cm off and 6.5
    degrees turned from the faces their things' spans give, so a thing laid flush on its span stood up to 4.6 cm in its
    wall at one end (2026-11-10). A ray from a span's very end grazes past its wall's corner onto the next wall behind
    it: habitat's kitchen cabinets and control panel on its wall_9 were turned 3 degrees into it, 9 cm deep
    (2026-11-11). Where either ray meets none, the built face nearest the span along its `out` either way within
    FACE_FAR is taken (face_near)."""
    if mesh is None:
        return on, 0.0
    import trimesh
    ends = [np.asarray(point, float) for point in on["span"]]
    out = np.asarray(on["out"], float)
    first, last = face_run(ends, out, height, mesh)
    inner = [ends[0] + (ends[1] - ends[0]) * (first + (last - first) * share)
             for share in (FACE_INSET, 1.0 - FACE_INSET)]
    origins = np.array([[point[0] + out[0] * WALL_REACH, height, point[1] + out[1] * WALL_REACH] for point in inner])
    back = np.array([-out[0], 0.0, -out[1]])
    hits, rays, _ = trimesh.ray.ray_triangle.RayMeshIntersector(mesh).intersects_location(
        origins, np.tile(back, (2, 1)))
    hits, rays = np.asarray(hits, float).reshape(-1, 3), np.asarray(rays)
    faces = []
    for ray in (0, 1):
        reach = (hits[rays == ray] - origins[ray]) @ back
        reach = reach[(reach > 0.0) & (reach <= 2 * WALL_REACH)]
        if not len(reach):
            return face_near(on, height, mesh)
        faces.append(origins[ray][[0, 2]] + back[[0, 2]] * float(reach.min()))
    run = faces[1] - faces[0]
    if float(np.linalg.norm(run)) < 1e-6:
        return on, 0.0
    normal = np.array([-run[1], run[0]]) / float(np.linalg.norm(run))
    normal = normal if normal @ out >= 0.0 else -normal
    degrees = math.degrees(math.atan2(out[1] * normal[0] - out[0] * normal[1], out @ normal))
    laid = [end - normal * float((end - faces[0]) @ normal) for end in ends]
    return {**on, "span": [[float(value) for value in end] for end in laid],
            "out": [float(value) for value in normal]}, degrees


def face_run(ends, out, height, mesh):
    """(from, to) shares of a wall relation's span (`ends` [x, z], its `out`) clear of a built surface (`mesh`)
    crossing in front of it inside its inner run (past FACE_INSET of its length from its middle either way): a ray
    from its middle WALL_REACH out along it each way at `height` (where on_built_face's rays start) meets the first
    such, and the run ends WALL_REACH before it, so no face ray starts behind it; (0, 1) where none does. Street's
    wall_7 runs on behind wall_8 folding back across its end: the face's far ray met wall_8 and laid its air
    conditioners 1 and 4 turned off wall_7, touching nothing (settle@street, 2026-11-11)."""
    run = ends[1] - ends[0]
    length = float(np.linalg.norm(run))
    if length < 1e-6:
        return 0.0, 1.0
    way = run / length
    middle = (ends[0] + ends[1]) / 2 + out * WALL_REACH
    origin = np.array([[middle[0], height, middle[1]]] * 2)
    ways = np.array([[way[0], 0.0, way[1]], [-way[0], 0.0, -way[1]]])
    hits, rays, _ = mesh.ray.intersects_location(origin, ways, multiple_hits=False)
    shares = [0.0, 1.0]
    for hit, ray in zip(np.asarray(hits, float).reshape(-1, 3), np.asarray(rays, int)):
        reach = float(np.linalg.norm(hit - origin[ray]))
        if reach < (0.5 - FACE_INSET) * length:
            kept = max(reach - WALL_REACH, 0.0)
            shares[1 - ray] = 0.5 + (kept if ray == 0 else -kept) / length
    return shares[0], shares[1]


# How far along a wall relation's `out` either way from its span's middle its built face is looked for where it does
# not stand behind its span (face_near), metres: under the 3 m a wall across the room stands at in the module test.
FACE_FAR = 1.5
# The farthest a built face found so is followed along either way from where it was met (face_near), metres.
FACE_RUN_MOST = 10.0


def face_near(on, height, mesh):
    """(the wall relation laid on the standing built face (`mesh`, built_walls) a ray from its span's middle at
    `height` meets first along its `out` either way within FACE_FAR, its `out` that face's normal toward the span, its
    span the run of that face round the point met (face_span), the degrees about +y that turn its `out` to the face's);
    (on, 0) where none is. Greenhouse's plan walls are an arc round its middle, 0.65 m thick, its shell built on its
    outline's octagon 0.3 to 1.2 m behind the arc's inner face: its eight wall lamps were laid on the arc's chords,
    touching nothing, and its two pipes, their plan spots in the arc's outer half, on its outer face, out of the
    room and through its walls (settle@greenhouse, 2026-11-11)."""
    start, run, out, length = wall_line(on)
    middle = start + run * length / 2
    origins = np.array([[middle[0], height, middle[1]]] * 2)
    ways = np.array([[-out[0], 0.0, -out[1]], [out[0], 0.0, out[1]]])
    hits, rays, triangles = mesh.ray.intersects_location(origins, ways, multiple_hits=False)
    found = []
    for hit, ray, triangle in zip(np.asarray(hits, float).reshape(-1, 3), np.asarray(rays, int),
                                  np.asarray(triangles, int)):
        normal = np.asarray(mesh.face_normals[triangle], float)
        flat = normal[[0, 2]]
        reach = float(np.linalg.norm(hit - origins[ray]))
        if reach <= FACE_FAR and float(np.linalg.norm(flat)) >= STANDING_LEAST:  # a standing face, not a deck's
            found.append((reach, hit, flat / float(np.linalg.norm(flat)) * (1.0 if flat @ ways[ray][[0, 2]] < 0.0
                                                                            else -1.0)))
    if not found:
        return on, 0.0
    _, hit, normal = min(found, key=lambda one: one[0])
    begin, end = face_span(hit, normal, mesh)
    degrees = math.degrees(math.atan2(out[1] * normal[0] - out[0] * normal[1], float(out @ normal)))
    return {**on, "span": [[float(value) for value in point] for point in (begin, end)],
            "out": [float(value) for value in normal]}, degrees


# A face whose normal's floor part is shorter than this stands at no wall (a deck's top, a roof's slope).
STANDING_LEAST = 0.9


def face_span(hit, normal, mesh):
    """(from, to) [x, z] of the run of a built face (`mesh`) round a point on it (`hit` [x, y, z], its unit floor
    `normal` toward the room): every RAY_STEP along it either way out to FACE_RUN_MOST, a ray from WALL_REACH in front
    of it at the point's height cast back meets the face's plane within MOVE_LEAST, from the point met on to the last
    such either way (a crossing wall, a turn of the wall or a hole ends it)."""
    tangent = np.array([-normal[1], normal[0]])
    steps = np.arange(RAY_STEP, FACE_RUN_MOST + RAY_STEP / 2, RAY_STEP)
    ends = []
    for sign in (1.0, -1.0):  # from its (out z, -out x) end
        floor = hit[[0, 2]] + tangent[None, :] * (sign * steps)[:, None] + normal * WALL_REACH
        origins = np.array([[x, hit[1], z] for x, z in floor])
        hits, rays, _ = mesh.ray.intersects_location(origins, np.tile([-normal[0], 0.0, -normal[1]],
                                                                      (len(origins), 1)), multiple_hits=False)
        met = np.full(len(origins), np.inf)
        met[np.asarray(rays, int)] = np.linalg.norm(np.asarray(hits, float).reshape(-1, 3)
                                                    - origins[np.asarray(rays, int)], axis=1)
        on_face = np.abs(met - WALL_REACH) <= MOVE_LEAST
        last = int(np.argmin(on_face)) if not on_face.all() else len(steps)  # the steps on it before the first off
        ends.append(hit[[0, 2]] + tangent * sign * (steps[last - 1] if last else 0.0))
    return ends[0], ends[1]


def along_its_wall(stage, path, on):
    """Whether a wall thing whose own box (oriented_corners) reaches across its wall (`on`'s `out`) more than
    STRAIGHT_LEAST times as far as along it was turned a quarter about +y on the stage, its long side along the face.
    Greenhouse's 3 m pipes, their rows 3 m tall, were built lying and laid sticking 3 m out of their wall, through the
    walls behind it (settle@greenhouse, 2026-11-11)."""
    low, high = world_box(stage, path)
    reach, deep = wall_reach(low, high, *wall_line(on)[1:3], oriented_corners(stage, path))
    if deep <= STRAIGHT_LEAST * max(reach, 1e-9):
        return False
    pivot = foot_middle(low, high)
    pitched_by(stage.GetPrimAtPath(path), pivot, (0.0, 1.0, 0.0), 90.0, pivot)
    return True


def oriented_corners(stage, path):
    """The 8 corners [8, 3] in the stage's frame of a prim's own bounding box, turned with it (a pipe laid along a
    slanted wall: its world box would hold the triangle it spans): every drawn point under it (a mesh's points, any
    other shape's extent corners) in its own frame, boxed, and the box's corners back in the stage's."""
    from pxr import Usd, UsdGeom
    time = Usd.TimeCode.Default()
    own = np.asarray(UsdGeom.Xformable(stage.GetPrimAtPath(path)).ComputeLocalToWorldTransform(time))
    points = []
    for prim in Usd.PrimRange(stage.GetPrimAtPath(path)):
        if not prim.IsA(UsdGeom.Boundable) or UsdGeom.Imageable(prim).ComputePurpose() == UsdGeom.Tokens.guide:
            continue
        found = UsdGeom.Mesh(prim).GetPointsAttr().Get() if prim.IsA(UsdGeom.Mesh) else \
            UsdGeom.Boundable.ComputeExtentFromPlugins(UsdGeom.Boundable(prim), time)
        if not found:
            continue
        local = np.asarray(found, float).reshape(-1, 3)
        if not prim.IsA(UsdGeom.Mesh):  # an extent's two corners: all eight
            local = np.array([[x, y, z] for x in local[:, 0] for y in local[:, 1] for z in local[:, 2]])
        matrix = np.asarray(UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(time))
        points.append(local @ matrix[:3, :3] + matrix[3, :3])
    if not points or abs(float(np.linalg.det(own[:3, :3]))) < 1e-12:  # a frame shrunk flat has no own box
        low, high = world_box(stage, path)
        return np.array([[x, y, z] for x in (low[0], high[0]) for y in (low[1], high[1]) for z in (low[2], high[2])])
    inverse = np.linalg.inv(own)
    mine = np.concatenate(points) @ inverse[:3, :3] + inverse[3, :3]
    low, high = mine.min(axis=0), mine.max(axis=0)
    box = np.array([[x, y, z] for x in (low[0], high[0]) for y in (low[1], high[1]) for z in (low[2], high[2])])
    return box @ own[:3, :3] + own[3, :3]


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
    (its box as laid after), the stage left unsaved. A thing hung from the roof built taller than its reading is first
    hung down under it (moved_down), so it is parted at the height it hangs at. The things nothing holds are parted
    first (parted, one hung from the roof with no room left under it left out) and what is
    still in a deck or wall pulled out of it (moved_out), so what they hold is fitted where they stand."""
    by_name = {entry["name"]: entry for entry in entries if entry.get("on") and entry["name"] in laid}
    bakes = {entry["name"]: entry.get("bake") for entry in entries}
    loose = [entry for entry in entries if entry["name"] in laid and not entry.get("on") and not climbs(entry)]
    fits = moved_down(stage, place, [entry for entry in loose if entry.get("under roof")])
    done, fits = set(), fits + parted(stage, place, loose, set(by_name))
    loose = [entry for entry in loose if stage.GetPrimAtPath(f"/{place}/Objects/{entry['name']}").IsActive()]
    fits += moved_out(stage, place, loose)
    fits += floor_clear.off_edges(stage, place, loose) + floor_clear.apart(stage, place, loose)
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
        if how == "in":  # laid along the straight built wall its hole was cut in (hole_wall)
            walled_in, degrees = hole_wall(entry["on"], [box for wall, box in statics(walls(stage, place))
                                                         if wall.split("_")[0] == "wall" and straight(box)], faces())
            if walled_in is not entry["on"]:
                if abs(degrees) > TURN_LEAST:
                    pivot = foot_middle(low, high)
                    pitched_by(stage.GetPrimAtPath(path), pivot, (0.0, 1.0, 0.0), degrees, pivot)
                    low, high = world_box(stage, path)
                entry = {**entry, "on": walled_in}
                laid_in[name] = walled_in
        if how == "in" and name in leaves and slanted(entry["on"]):
            surface = wall_points(stage, place)
        on_shelves = how == "within" and held and on_shelves_of(entry["on"]) and not hangs_in(entry)
        along = False  # turned to lie along its wall (along_its_wall)
        if on_shelves:
            holder, found = shelved(low, high, entry["on"], held,
                                    lambda holder: surface_mesh(stage, f"/{place}/{scope}/{holder}"), taken)
        else:
            turned = how == "wall" and not passes(entry)  # a passage meets its place through its wall, as laid
            on_face = False  # laid on its slanted wall's built face (on_built_face found it)
            if turned and slanted_wall(entry["on"]):  # laid on its built wall's face, turned to it
                built_on, degrees = on_built_face(entry["on"], (low[1] + high[1]) / 2, faced())
                on_face = built_on is not entry["on"]
                if abs(degrees) > TURN_LEAST:
                    pivot = foot_middle(low, high)
                    pitched_by(stage.GetPrimAtPath(path), pivot, (0.0, 1.0, 0.0), degrees, pivot)
                    low, high = world_box(stage, path)
                entry = {**entry, "on": built_on}
            if turned and along_its_wall(stage, path, entry["on"]):
                along = True
                low, high = world_box(stage, path)
            walled = how in ("wall", "face") and name not in leaves
            clear = [*(box for leaf in sorted(done & leaves) for box in rooms(leaf)), *climbing] if walled else ()
            if turned:  # and out of the openings cut through its wall (wall_holes)
                clear = [*clear, *wall_holes(faces(), entry["on"], (float(low[1]), float(high[1])))]
            if on_face:  # and out of the built walls standing in front of its face (walls_ahead)
                deep = wall_reach(low, high, *wall_line(entry["on"])[1:3], oriented_corners(stage, path))[1]
                clear = [*clear, *walls_ahead(faces(), entry["on"], (float(low[1]), float(high[1])), deep)]
            others = [box for other, box in mounted.items() if other not in (entry["on"].get("holder") or [])] \
                if walled else ()
            corners = oriented_corners(stage, path) if turned else None
            found = fit(low, high, entry["on"], built if how == "in" else [box for _, box in held], surface,
                        recesses, own_way(stage, path, 0), own_way(stage, path, 2) if name in leaves else None, clear,
                        others, corners, () if passes(entry) else built)
            if turned:  # the face it is laid on, which the held gate measures it off (held_faults)
                faced_on[name] = stood_face(low, high, entry["on"], corners, built)
        if held and hangs_in(entry):
            found = on_back(stage, found, low, high, path, held, f"/{place}/{scope}/", built)
        if found is CROWDED:
            fits.append(laid_fit(stage, path, entry, how, entry["on"].get("holder"), 0.0, 1.0,
                                 f"crowded: no clear stretch left on its wall; left as laid" if how == "wall" else
                                 f"crowded: no clear spot left on the boards of {', '.join(name for name, _ in held)}"
                                 f"; left as laid"))
            return
        if found is None:
            if on_shelves:
                taken.setdefault(holder, []).append((low, high))
            if how in ("wall", "face"):
                mounted[name] = oriented_corners(stage, path)
            return
        scale, target, words, face = found
        moved_by(stage.GetPrimAtPath(path), foot_middle(low, high), scale, target)
        if along:
            words += "; turned a quarter to lie along its wall: built long across it"
        if how == "in":  # held to what it has clear of the built walls and the opening things laid before it
            words += held_clear(stage, path, entry["on"], opened_around())
            opened.append(path)
        if how == "face" and surface is not None:  # its back met on its holder's surface
            words += touching(stage, path, surface)
        if how == "within" and not on_shelves:  # in front of the wall its holder is laid on
            words += off_faces(stage, path, [faced_on[holder] for holder, _ in held if holder in faced_on])
        from pxr import Sdf
        stage.GetPrimAtPath(path).CreateAttribute("score:fitted", Sdf.ValueTypeNames.String).Set(words)
        after = world_box(stage, path)
        if on_shelves:
            taken.setdefault(holder, []).append(after)
        if how in ("wall", "face"):
            mounted[name] = oriented_corners(stage, path)
        fits.append({"name": name, "row": entry["row"], "how": how,
                     "holder": entry["on"].get("holder"), "moved": round(float(np.linalg.norm(
                         target - foot_middle(low, high))), 3), "scale": round(float(np.min(scale)), 4),
                     "low": [round(float(value), 4) for value in after[0]],
                     "high": [round(float(value), 4) for value in after[1]], "words": words,
                     **({"face": round(face[0], 4), **({"hung": True} if face[1] else {})} if face is not None
                        else {}), **(laid_face(faced_on[name], oriented_corners(stage, path)) if name in faced_on
                                     else {}),
                     **({"opening": {key: laid_in[name][key] for key in ("middle", "along")}} if name in laid_in
                        else {})})

    def rooms(leaf):
        """The swing box and the passage box of a leaf as laid."""
        path = f"/{place}/Objects/{leaf}"
        return swing_box(stage, path), passage_box(*world_box(stage, path), by_name[leaf]["on"], built)

    def opened_around():
        """The place's built walls and the opening things laid so far (`opened`) as one mesh; None with none."""
        import trimesh
        found = [mesh for mesh in [faces(), *(surface_mesh(stage, other) for other in opened)] if mesh is not None]
        return trimesh.util.concatenate(found) if found else None

    def faces():
        """The place's built walls as one mesh (built_walls), made once."""
        if "mesh" not in built_mesh:
            built_mesh["mesh"] = built_walls(stage, place)
        return built_mesh["mesh"]

    def faced():
        """The place's built walls without its roofs as one mesh (wall_clear.face_walls), made once."""
        if "faced" not in built_mesh:
            built_mesh["faced"] = wall_clear.face_walls(stage, place)
        return built_mesh["faced"]

    built_mesh = {}
    climbing = wall_clear.climbing(stage, place, entries)  # the climbing rows' things, which no wall thing stands in
    leaves = {name for name, entry in by_name.items() if entry["on"]["how"] in ("in", "face") and swings(entry["row"])}
    taken = {}  # {holder: the boxes laid within it so far}, on_boards
    faced_on = {}  # {wall thing: the relation it is laid by: on its built face (on_built_face), stood (stood_face)}
    laid_in = {}  # {opening thing: its relation laid along the straight wall its hole was cut in (hole_wall)}
    opened = []  # the paths of the opening things laid so far, which each laid after keeps clear of (held_clear)
    mounted = {}  # {wall or face thing: its box as laid}, which each laid after it on a wall or face keeps clear of
    for name in sorted(by_name, key=lambda name: name not in leaves):  # the leaves first: a wall's things keep clear of them
        one(name)
    walled = [entry for entry in by_name.values() if entry["on"]["how"] == "wall"]
    topped = [entry for entry in by_name.values() if entry["on"]["how"] == "top"]
    fits += spread_on_tops(stage, place, topped)
    from score.stages.assembly import built_tops  # onto the built surface under them
    fits += built_tops.let_down(stage, place, [entry for entry in by_name.values() if built_tops.held_on(entry)])
    fits += moved_past(stage, place, walled)
    moved_in(stage, place, walled, fits)
    fits += passages.drawn_in(stage, place, walled)
    wall_clear.under_roofs(stage, place, walled, fits)
    stacked = stacked_on_runs(stage, place, topped, walled)
    fits += stacked + built_tops.stacked_down(stage, place, stacked)  # onto the runs' built surface
    return fits + moved_down(stage, place, loose) + \
        hung_up(stage, place, loose) + hung_by_parts(stage, place, loose)


def laid_face(on, corners):
    """The fit's words for the held gate of a wall thing laid: the face's `span` and `out` it is laid on, and its
    turned box's floor corners as laid (`corners`, oriented_corners: a pipe turned along a slanted wall is as deep as
    its own box, never its world box)."""
    return {"span": [[round(float(value), 4) for value in point] for point in on["span"]],
            "out": [round(float(value), 6) for value in on["out"]],
            "corners": [[round(float(point[0]), 4), round(float(point[2]), 4)] for point in np.asarray(corners, float)]}


def shelved(low, high, on, held, surface_of, taken):
    """(holder, fit) of a thing laid on its holders' boards (on_shelves_of) from its box (low, high): each of `held`
    [(name, box)] tried nearest first on the floor plan, on its built surface (`surface_of(name)`, surface_mesh's),
    clear of the boxes laid in it before (`taken`, {name: [(low, high)]}), the first that is not CROWDED, then each
    again stacking on one laid before (on_boards' `stack`); (None, CROWDED) when none has a clear spot left. Garage's
    14 boxes on three shelf units all went to the nearest, 12 piled at two spots of it (2026-11-10); its three units
    hold 7 on their boards and tops, the rest stacked on those (2026-11-11)."""
    here = (np.asarray(low, float) + np.asarray(high, float)) / 2

    def distance(item):
        return float(np.linalg.norm(((np.asarray(item[1][0], float) + np.asarray(item[1][1], float)) / 2
                                     - here)[[0, 2]]))

    for stack in (False, True):
        for holder, box in sorted(held, key=distance):
            found = fit(low, high, on, [box], surface_of(holder), clear=taken.get(holder, []), stack=stack)
            if found is not CROWDED:
                return holder, found
    return None, CROWDED


def laid_fit(stage, path, entry, how, holder, moved, scale, words):
    """The fit {name, how, ...} of an entry moved on the stage: its words set on the prim, its box as laid after."""
    from pxr import Sdf
    stage.GetPrimAtPath(path).CreateAttribute("score:fitted", Sdf.ValueTypeNames.String).Set(words)
    after = world_box(stage, path)
    return {"name": entry["name"], "row": entry["row"], "how": how, "holder": holder, "moved": round(float(moved), 3),
            "scale": round(float(np.min(scale)), 4), "low": [round(float(value), 4) for value in after[0]],
            "high": [round(float(value), 4) for value in after[1]], "words": words}


# The pull back to a parted thing's laid spot a metre off, as the plan fixes' solver pulls a plan spot
# (relation_solver.SOFT): weaker than staying inside the place's structure (the solver's ON_SLOPE) and an overlap's.
PULL = 1.0


def tall_together(box, other):
    """Whether two boxes (low, high) reach into each other's height by more than HELD_MOST: a rug a few cm thick and
    the table on it never do."""
    return min(box[1][1], other[1][1]) - max(box[0][1], other[0][1]) > HELD_MOST


def crossing(boxes, statics_built, slanted=()):
    """How many of the boxes {name: (low, high)} stand inside each other or inside a static, by more than HELD_MOST
    every way (inside_of's rule), or inside a slanted wall (in_slants)."""
    names = sorted(boxes)
    return sum(depths(*boxes[first], boxes[second]).min() > HELD_MOST
               for number, first in enumerate(names) for second in names[number + 1:]) \
        + sum(len(inside_of(*box, statics_built)) for box in boxes.values()) \
        + sum(in_slants(box, slanted) for box in boxes.values())


def through(start, end, others):
    """Which of the boxes `others` (low (M, 3), high (M, 3)) the floor path from `start` to `end` ([x, y, z]; x and z
    read) passes through, (M,) booleans: a thing whose middle went that way through a wall went into the next room."""
    low, high = others[0][:, [0, 2]], others[1][:, [0, 2]]
    first, way = np.asarray(start, float)[[0, 2]], (np.asarray(end, float) - start)[[0, 2]]
    still = np.abs(way) < 1e-12
    with np.errstate(divide="ignore", invalid="ignore"):
        near, far = (low - first) / np.where(still, 1.0, way), (high - first) / np.where(still, 1.0, way)
    enter = np.where(still, np.where((low < first) & (first < high), -np.inf, np.inf), np.minimum(near, far))
    leave = np.where(still, np.where((low < first) & (first < high), np.inf, -np.inf), np.maximum(near, far))
    return np.maximum(enter.max(axis=1), 0.0) < np.minimum(leave.min(axis=1), 1.0)


def stacked(boxes):
    """Boxes [(low, high)] as (low (M, 3), high (M, 3)), the form through and free_spot read."""
    return (np.array([box[0] for box in boxes], float).reshape(-1, 3),
            np.array([box[1] for box in boxes], float).reshape(-1, 3))


def flush_moves(box, others, inside, axis, side, slants=()):
    """The moves along one floor axis (0: x, 2: z; `side` that axis's in `inside`: 0 or 1) that set a box (low,
    high) flush against a side of one of `others` (low (M, 3), high (M, 3)) or of `inside` [low x, low z, high x,
    high z], or against a slanted wall's outline (`slants`, slant_flush), and no move: the only moves a least move
    clear of boxes needs."""
    bounds = [bound for bound in (inside[side] - box[0][axis], inside[side + 2] - box[1][axis]) if np.isfinite(bound)]
    return np.unique(np.concatenate([[0.0], others[1][:, axis] - box[0][axis], others[0][:, axis] - box[1][axis],
                                     bounds, *(slant_flush(box, outline, side) for outline, _ in slants)]))


# --- slanted walls: a wall whose box holds the room beside it (WALL_THICKEST), read by its outline on the floor ----

def slants(stage, place):
    """[(outline [k, 2] (x, z), box (low, high))] of each built wall statics leaves out for its slant: the convex
    outline of its mesh on the floor, where that outline is no thicker than WALL_THICKEST (a straight slanted wall;
    a round one's would hold the room), its box for its height; and of each built flight (flight: a stair or ramp the
    scene record builds as steps, its outline a straight flight's at any width and turn). 2026-11-08: engineroom's
    corner walls, which the parting knew only by the box of the walls, took core_1 5.48 m into wall_12 and railings 7
    and 8 through walls 2 and 10, out of the room."""
    from scipy.spatial import ConvexHull, QhullError
    found = []
    for scope in ("Structure", "Shell"):
        for name, box in walls_in(stage, place, scope):
            if not flight(name) and (name.split("_")[0] != "wall"
                                     or min(box[1][0] - box[0][0], box[1][2] - box[0][2]) <= WALL_THICKEST):
                continue
            points = surface_points(stage, f"/{place}/{scope}/{name}")[:, [0, 2]]
            try:
                outline = points[ConvexHull(points).vertices]
            except (QhullError, ValueError):
                continue
            if flight(name) or min(np.ptp(outline @ way) for way in outline_ways(outline)) <= WALL_THICKEST:
                found.append((outline, box))
    return found


# The built flights' names' first words (scene_record/writer.stair: the plan's stair or ramp kind, `<kind>_<n>`).
FLIGHTS = ("stair", "ramp")


def flight(name):
    """Whether a built structure piece is a flight of steps (FLIGHTS), which statics leaves out (its box holds the
    floor beside a turned flight) and slants judges by its outline: settle@campgrounds, 2026-11-11, found its lander
    and a dome laid 0.65 and 0.76 m into ramp_1 and ramp_2, built as steps, which nothing parted them from."""
    return name.split("_")[0] in FLIGHTS


def outline_ways(outline):
    """The unit normals [k, 2] of a convex outline's edges [k, 2] (x, z)."""
    edges = np.roll(outline, -1, axis=0) - outline
    ways = np.stack([-edges[:, 1], edges[:, 0]], axis=1)
    return ways / np.maximum(np.linalg.norm(ways, axis=1, keepdims=True), 1e-12)


def slant_depth(middles, half, outline):
    """How far each floor rectangle (its middle (N, 2) (x, z), its `half` sides [x, z]) reaches into a convex outline
    (N,): the least overlap over the outline's edge normals and the two floor axes (0 or less: apart)."""
    ways = np.vstack([[[1.0, 0.0], [0.0, 1.0]], outline_ways(outline)])
    reach = np.abs(ways) @ np.asarray(half, float)
    along = np.asarray(middles, float).reshape(-1, 2) @ ways.T
    ends = outline @ ways.T
    return (np.minimum(along + reach, ends.max(axis=0)) - np.maximum(along - reach, ends.min(axis=0))).min(axis=1)


def slant_flush(box, outline, side):
    """The moves along one floor axis (`side` 0: x, 1: z) that set a box (low, high) flush against a convex outline
    on one of its separating ways (slant_depth's)."""
    middle, half = foot_middle(*box)[[0, 2]], (box[1] - box[0])[[0, 2]] / 2
    ways = np.vstack([[[1.0, 0.0], [0.0, 1.0]], outline_ways(outline)])
    ways = ways[np.abs(ways[:, side]) > 1e-6]
    reach, along, ends = np.abs(ways) @ half, ways @ middle, outline @ ways.T
    return np.concatenate([(ends.max(axis=0) - (along - reach)) / ways[:, side],
                           (ends.min(axis=0) - (along + reach)) / ways[:, side]])


def slant_crossed(start, ends, outline):
    """Which floor paths from `start` to each of `ends` (N, 3) pass through a convex outline (N,) booleans (the
    outline's edge normals and each path's own normal separate the ones that do not)."""
    first, last = np.asarray(start, float)[[0, 2]], np.asarray(ends, float).reshape(-1, 3)[:, [0, 2]]
    ways = outline_ways(outline)
    path = last - first
    own = np.stack([-path[:, 1], path[:, 0]], axis=1)
    apart = ((np.minimum(first @ ways.T, last @ ways.T) >= (outline @ ways.T).max(axis=0))
             | (np.maximum(first @ ways.T, last @ ways.T) <= (outline @ ways.T).min(axis=0))).any(axis=1)
    side = outline @ own.T
    lined = (own * first).sum(axis=1)
    return ~apart & ~((side.min(axis=0) >= lined) | (side.max(axis=0) <= lined))


def in_slants(box, slanted):
    """Whether a box (low, high) reaches into one of the slanted walls `slanted` (slants') it shares height with by
    more than HELD_MOST."""
    middle, half = foot_middle(*box)[[0, 2]], (box[1] - box[0])[[0, 2]] / 2
    return any(tall_together(box, wall) and float(slant_depth(middle, half, outline)[0]) > HELD_MOST
               for outline, wall in slanted)


# How many moves free_spot judges at once (memory: each against every other box).
FREE_CHUNK = 2048


def free_spot(box, others, pieces, inside, slanted=(), floors=()):
    """The least move [x, y, z] on the floor that takes a box (low, high) clear of every box of `others` and of the
    wall `pieces` (each [(low, high)], those it shares height with: tall_together) and of the slanted walls
    (`slanted`, slants': by their outlines) and keeps it in `inside` [low x, low z, high x, high z], its middle
    passing through no wall piece or slanted wall it did not start in (it stays in its room), and its footprint over
    the deck it stands on where it starts on one (`floors`, deck_triangles: on_deck); None where no move
    does. Only flush moves are judged (flush_moves), so the move found is exact. The solver's overlap
    gives a box laid across a wall no way out (it holds the wall's piece inside its own on both axes, so the
    overlap's gradient is 0): habitat's bunk beds, 2.1 m long, laid across its slanted inner wall."""
    deck = deck_at(box, floors)
    near = stacked([other for other in [*others, *pieces] if tall_together(box, other)])
    walls_near = stacked([piece for piece in pieces if tall_together(box, piece)])
    middle, size = foot_middle(*box), box[1] - box[0]
    started = through(middle, middle, walls_near)
    sloped = [(outline, wall) for outline, wall in slanted if tall_together(box, wall)]
    along, across = np.meshgrid(flush_moves(box, near, inside, 0, 0, sloped),
                                flush_moves(box, near, inside, 2, 1, sloped))
    moves = np.stack([along.ravel(), np.zeros(along.size), across.ravel()], axis=1)
    moves = moves[np.lexsort((moves[:, 2], moves[:, 0], np.hypot(moves[:, 0], moves[:, 2])))]
    spots = box[0][[0, 2]] + moves[:, [0, 2]]
    moves = moves[(spots >= np.asarray(inside[:2]) - 1e-6).all(axis=1)
                  & (spots + size[[0, 2]] <= np.asarray(inside[2:]) + 1e-6).all(axis=1)]
    for first in range(0, len(moves), FREE_CHUNK):
        chunk = moves[first:first + FREE_CHUNK]
        reach = (np.minimum(box[1] + chunk[:, None], near[1][None]) - np.maximum(box[0] + chunk[:, None],
                                                                                 near[0][None])).min(axis=2)
        clear = ~(reach > HELD_MOST).any(axis=1)
        for outline, _ in sloped:
            begun = slant_depth(middle[[0, 2]], np.zeros(2), outline)[0] >= 0.0  # a point's depth: 0 in it
            clear &= slant_depth(middle[[0, 2]] + chunk[:, [0, 2]], size[[0, 2]] / 2, outline) <= HELD_MOST
            if not begun:
                clear &= ~slant_crossed(middle, middle + chunk, outline)
        if deck is not None:
            clear &= on_deck(box[0] + chunk, size, deck)
        for move in chunk[clear]:
            if not (through(middle, middle + move, walls_near) & ~started).any():
                return move
    return None


def deck_at(box, floors):
    """The deck triangles of `floors` ([n, 3, 3], deck_triangles) lying at a box's (low, high) foot, within HELD_MOST
    of its height, where its foot's middle stands over one of them; None where it stands on none (on the ground)."""
    if not len(floors):
        return None
    level = floors[(np.abs(floors[:, :, 1] - float(box[0][1])) <= HELD_MOST).all(axis=1)]
    if not len(level) or not np.isfinite(roof_under(foot_middle(*box)[None, :], level))[0]:
        return None
    return level


def on_deck(lows, size, deck):
    """(N,) whether each footprint (its box's low corner `lows` [N, 3], its `size`) stands over the `deck`
    triangles (deck_at) at its middle and its four corners. Greenhouse's upper floor is cut 0.3 to 1.2 m short of
    its walls: its desks, a chair and a tank parted clear of each other went past its edge, tipping and floating
    3 m over the floor below (settle@greenhouse, 2026-11-11)."""
    lows = np.asarray(lows, float).reshape(-1, 3)
    offsets = np.array([[0.5, 0.0, 0.5], [0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0], [1.0, 0.0, 1.0]]) \
        * np.asarray(size, float)
    points = (lows[:, None, :] + offsets[None, :, :]).reshape(-1, 3)
    return np.isfinite(roof_under(points, deck)).reshape(len(lows), len(offsets)).all(axis=1)


def parted_spots(boxes, movers, fixed, inside):
    """{name: its box (low, high)} of the movers {name: the box it starts from} parted on the floor by the relation
    solver, at their built size: each pulled softly back to where it starts, kept in `inside` [low x, low z, high x,
    high z], clear of each other and of the `fixed` boxes [(low, high)] and the things not moving ({name: box} of
    `boxes` not in `movers`) it shares height with (tall_together)."""
    from score.review.relation_solver._solver import Problem, solved
    obstacles = [*fixed, *(box for name, box in boxes.items() if name not in movers)]
    order = sorted(movers)
    boxes = {**boxes, **movers}
    problem = Problem([(boxes[name][1] - boxes[name][0])[[0, 2]] for name in order],
                      [boxes[name][0][[0, 2]] for name in order], PULL, inside,
                      [[low[0], low[2], high[0], high[2]] for low, high in obstacles],
                      [[1.0 if tall_together(boxes[name], other) else 0.0 for other in obstacles] for name in order],
                      [[1.0 if tall_together(boxes[name], boxes[other]) else 0.0 for other in order]
                       for name in order], 0.0)
    spots, _ = solved(problem)
    return {name: (np.array([spot[0], boxes[name][0][1], spot[1]]),
                   np.array([spot[0], boxes[name][0][1], spot[1]]) + boxes[name][1] - boxes[name][0])
            for name, spot in zip(order, spots)}


def crowded(boxes, fixed, slanted=()):
    """The names of the boxes {name: (low, high)} standing inside another of them or inside one of `fixed` [(low,
    high)] by more than HELD_MOST every way, sharing height (tall_together: a rug under a table never does), or
    inside a slanted wall (in_slants)."""
    return {name for name, box in boxes.items()
            if any(tall_together(box, other) and depths(*box, other).min() > HELD_MOST for other in fixed)
            or any(tall_together(box, found) and depths(*box, found).min() > HELD_MOST
                   for other_name, found in boxes.items() if other_name != name) or in_slants(box, slanted)}


def moved_box(box, shift):
    """A box (low, high) moved by `shift` [x, y, z], or as it was when there is no shift (None)."""
    return box if shift is None else (box[0] + shift, box[1] + shift)


OPEN = [-np.inf, -np.inf, np.inf, np.inf]


def bound_of(box, inside):
    """The floor box [low x, low z, high x, high z] a thing (low, high) is kept in: `inside` (the box of the place's
    walls) when its middle stands in it, else none (OPEN: airlock's porch post, outside its walls)."""
    middle = foot_middle(*box)[[0, 2]]
    return inside if (np.asarray(inside[:2]) <= middle).all() and (middle <= np.asarray(inside[2:])).all() else OPEN


def bound_of_all(boxes, inside):
    """The one floor box the solver keeps the boxes [(low, high)] in: `inside` grown to hold each one standing
    outside it as laid (bound_of)."""
    outside = [box for box in boxes if bound_of(box, inside) is OPEN]
    return [min([inside[0], *(box[0][0] for box in outside)]), min([inside[1], *(box[0][2] for box in outside)]),
            max([inside[2], *(box[1][0] for box in outside)]), max([inside[3], *(box[1][2] for box in outside)])]


def parted_boxes(boxes, still, pieces, inside, slanted=(), hung=(), floors=()):
    """({name: box (low, high)}, {name left out}) of the boxes {name: (low, high)} of the things nothing holds, the
    crowded ones parted
    at their built size, kept in `inside` [low x, low z, high x, high z], clear of the `still` boxes (fixtures and held
    things) and the wall `pieces` [(low, high)]: each laid across a still box or a wall moved to the free spot
    nearest it among those alone (free_spot: the solver's overlap gives one laid across a wall no way out), those
    then inside each other parted by the relation solver (parted_spots); then each one still inside another, a still
    box or a wall piece, or
    whose middle the solver took through a wall into the next room, the biggest first, at the free spot nearest its
    laid one among everything (free_spot); one with none left as laid (the held gate names it). One hung from the
    roof (`hung`, their names) with none has the spot it would have clear of the hung ones after it by name, which
    are parted again around it, and is left out where it has none even so: of two things a roof holds where room is
    left for one, the plan's later one is left out (hangar's two 30 x 13 m cranes and its one 20.2 m bay between its
    ribs, 2026-11-11), never left in the other. The slanted walls (`slanted`, slants') are judged by their outlines
    throughout: the solver knows only boxes, so one it leaves in or takes through a slanted wall goes to its free
    spot too, as does one it takes off the deck it stood on (`floors`, deck_triangles: on_deck)."""
    fixed = [*still, *pieces]
    movers = crowded(boxes, fixed, slanted)
    if not movers:
        return boxes, set()
    after = {**boxes, **{name: moved_box(boxes[name], free_spot(boxes[name], still, pieces,
                                                                 bound_of(boxes[name], inside), slanted, floors))
                         for name in movers if crowded({name: boxes[name]}, fixed, slanted)}}
    crowd = crowded(after, []) & movers
    if crowd:
        after.update(parted_spots(after, {name: after[name] for name in crowd}, fixed,
                                  bound_of_all([boxes[name] for name in crowd], inside)))
    walls_all = stacked(pieces)
    crossed = {name for name in movers if (through(foot_middle(*boxes[name]), foot_middle(*after[name]), walls_all)
                                           & ~through(foot_middle(*boxes[name]), foot_middle(*boxes[name]),
                                                      walls_all)).any()
               or any(slant_crossed(foot_middle(*boxes[name]), foot_middle(*after[name]), outline)[0]
                      and not slant_crossed(foot_middle(*boxes[name]), foot_middle(*boxes[name]), outline)[0]
                      for outline, _ in slanted)} | {
        name for name in movers if (deck := deck_at(boxes[name], floors)) is not None
        and not on_deck(after[name][0], boxes[name][1] - boxes[name][0], deck)[0]}
    tried, left = set(), set()
    while pending := sorted((crowded(after, fixed, slanted) & movers | crossed) - tried - left,
                            key=lambda name: (-float(np.prod((boxes[name][1] - boxes[name][0])[[0, 2]])), name)):
        name = pending[0]
        tried.add(name)
        others = [*still, *(box for other, box in after.items() if other != name)]
        if not (name in crossed or crowded({name: after[name]}, [*others, *pieces], slanted)):
            continue
        shift = free_spot(boxes[name], others, pieces, bound_of(boxes[name], inside), slanted, floors)
        if shift is None and name in hung:
            later = {other for other in set(hung) & movers if other > name and other in after}
            shift = free_spot(boxes[name], [*still, *(box for other, box in after.items()
                                                      if other != name and other not in later)],
                              pieces, bound_of(boxes[name], inside), slanted, floors)
            if shift is None:
                left.add(name)
                del after[name]
                continue
            tried -= later
        after[name] = moved_box(boxes[name], shift)
    return after, left


def parted(stage, place, entries, holding=()):
    """The entries nothing holds (a thing on the floor) laid at their built size inside another, a fixture or a wall
    (more than HELD_MOST every way: a rug under a table never is) parted on the floor at their built size
    (parted_boxes: the nearest free spot in its own room for one in a fixture or wall, then the plan fixes' relation
    solver, score/review/relation_solver/_solver, for those inside each other, each pulled softly back to where it
    starts, then the nearest free spot again for one the solver left crossing; each kept inside the box of the place's
    walls where its middle stands in it (bound_of), clear of every fixture, still thing and wall piece it shares
    height with, and of each slanted wall by its outline on the floor (slants), never through one), never shrunk; the
    fixtures, the structure and the things nothing crowds never move, and the held
    things (`holding`, their names) are left out: fitted after, onto where their holders stand. Kept only when fewer
    stand inside each other or a static after (#72, settle@flat: its bed in its bedside table and wardrobe, laid
    bigger than the plan's estimates). One hung from the roof (the scene record's `under roof`) with no free spot is
    left out (parted_boxes): its prim made inactive, so nothing lays, drops or judges it, and its fit says why (how
    "left out"), a gap of its own; the fits [{name, how "parted" or "left out", ...}]. A thin thing turned off the
    floor's axes (thin_outline: a railing's world box holds the room beside it) is never parted and kept clear of by
    its outline, as a slanted wall is; each parted one stays on the deck it stands on (on_deck)."""
    paths = {entry["name"]: f"/{place}/Objects/{entry['name']}" for entry in entries}
    outlines = {name: outline for name, path in paths.items() if (outline := thin_outline(stage, path)) is not None}
    boxes = {name: world_box(stage, path) for name, path in paths.items() if name not in outlines}
    held = {f"{scope}/{name}": box for scope in ("Objects", "Fixtures") for name, box in walls_in(stage, place, scope)
            if scope == "Fixtures" or (name not in boxes and name not in outlines and name not in holding)}
    built = walls(stage, place)
    thin = statics(built)
    pieces = [box for name, box in thin if name.split("_")[0] == "wall"]
    room = [box for name, box in built if name.split("_")[0] == "wall"]
    inside = ([min(box[0][0] for box in room), min(box[0][2] for box in room), max(box[1][0] for box in room),
               max(box[1][2] for box in room)] if room else [-np.inf, -np.inf, np.inf, np.inf])
    slanted = [*slants(stage, place), *((outline, world_box(stage, paths[name])) for name, outline in outlines.items())]
    after, left = parted_boxes(boxes, list(held.values()), pieces, inside, slanted,
                               {entry["name"] for entry in entries if entry.get("under roof")},
                               deck_triangles(stage, place))
    if crossing({**held, **after}, thin, slanted) >= crossing({**held, **boxes}, thin, slanted):
        return []
    fits = []
    for entry in entries:
        if entry["name"] in outlines:
            continue
        if entry["name"] in left:
            fits.append(left_out(stage, paths[entry["name"]], entry, boxes[entry["name"]]))
            continue
        shift = after[entry["name"]][0] - boxes[entry["name"]][0]
        if float(np.linalg.norm(shift)) < MOVE_LEAST:
            continue
        foot = foot_middle(*boxes[entry["name"]])
        moved_by(stage.GetPrimAtPath(paths[entry["name"]]), foot, 1.0, foot + shift)
        fits.append(laid_fit(stage, paths[entry["name"]], entry, "parted", None, np.linalg.norm(shift), 1.0,
                             f"parted {float(np.linalg.norm(shift)):.2f} m on the floor at its built size: laid "
                             f"inside another thing, nothing holding it there"))
    return fits


# A thin thing whose world box holds more than this many times its own turned box's floor is turned off the floor's axes
# (thin_outline); a thing thicker across than THIN_MOST metres is no thin one (a turned bench is parted by its box).
TURNED_MOST = 2.0
THIN_MOST = 0.3


def thin_outline(stage, path):
    """The floor outline [4, 2] (x, z) of a thing's own turned box (oriented_corners), at least 2 MOVE_LEAST thick,
    where that box is straight (STRAIGHT_LEAST times as long as thick), THIN_MOST thick at most, and its world box
    holds more than TURNED_MOST times its floor; None otherwise. Greenhouse's five railings, 9.4 m chords round its upper floor's middle, have
    world boxes 3.7 m deep: its desks, chairs and tanks standing clear of them in those boxes were parted out of them,
    past its upper floor's edge (settle@greenhouse, 2026-11-11)."""
    corners = oriented_corners(stage, path)[:, [0, 2]]
    origin, along, across = corners[0], corners[4] - corners[0], corners[1] - corners[0]
    long, thick = float(np.linalg.norm(along)), float(np.linalg.norm(across))
    if long < thick:
        along, across, long, thick = across, along, thick, long
    if long < 1e-9 or long < STRAIGHT_LEAST * thick or thick > THIN_MOST:
        return None
    if float(np.prod(np.ptp(corners, axis=0))) <= TURNED_MOST * long * max(thick, 2 * MOVE_LEAST):
        return None
    side = np.array([-along[1], along[0]]) / long
    middle = origin + across / 2
    half = side * max(thick, 2 * MOVE_LEAST) / 2
    return np.array([middle - half, middle + along - half, middle + along + half, middle + half])


def left_out(stage, path, entry, box):
    """The fit {name, how "left out", ...} of a thing hung from the roof that has no free spot under it (parted_boxes):
    its prim made inactive, its box (low, high) as it was laid."""
    from pxr import Sdf
    words = ("left out: hung from the roof with no free spot under it at its built size, the room there taken by the "
             "things hung before it")
    prim = stage.GetPrimAtPath(path)
    prim.CreateAttribute("score:fitted", Sdf.ValueTypeNames.String).Set(words)
    prim.SetActive(False)
    return {"name": entry["name"], "row": entry["row"], "how": "left out", "holder": None, "moved": 0.0, "scale": 1.0,
            "low": [round(float(value), 4) for value in box[0]], "high": [round(float(value), 4) for value in box[1]],
            "words": words}


def moved_out(stage, place, entries):
    """Each entry laid with nothing holding it (no `on`: a thing on the floor) that starts inside a deck or level of
    the built structure (statics: airlock's sandbags in its porch deck, laid at the plan's estimate) moved the least
    way out of each in turn (out_of), on the stage, where that is OUT_MOST at most; the fits [{name, how, ...}]. A
    climbing row (climbs: a stair into its level) is left to its stair. One in a wall is parted's, which keeps it in
    its room (the least way out of a wall can be through it: habitat's bunk bed, 2026-11-04), and leaves one that fits
    nowhere there as laid for the held gate to name (hangar's 46 m ship in its 32 m room). One reaching into a wall
    piece by HELD_MOST at most across it, too little for parted to take it (crowded), is moved back out of it the way
    it came in, along the floor (shallow_out): settle@street's police car stood 0.044 m into wall_12 (2026-11-11)."""
    pieces = statics(walls(stage, place))
    built, fits = [(name, box) for name, box in pieces if name.split("_")[0] != "wall"], []
    thin = [(name, box) for name, box in pieces if name.split("_")[0] == "wall" and straight(box)]
    for entry in entries:
        path = f"/{place}/Objects/{entry['name']}"
        low, high = world_box(stage, path)
        shift, left = np.zeros(3), []
        for static, box in built:
            if depths(low + shift, high + shift, box).min() > HELD_MOST:
                shift += out_of(low + shift, high + shift, box)
                left.append(static)
        for static, box in thin:
            move = shallow_out(low + shift, high + shift, box)
            if move is not None:
                shift += move
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


# A wall piece whose box is this many times as long as it is thick runs along x or z, its box its own shape (a
# slanted wall's box holds the room beside it).
STRAIGHT_LEAST = 4.0


def straight(box):
    """Whether a wall piece's box (low, high) is its own shape: STRAIGHT_LEAST times as long as thick on the floor."""
    size = sorted(float(value) for value in (np.asarray(box[1], float) - np.asarray(box[0], float))[[0, 2]])
    return size[1] >= STRAIGHT_LEAST * max(size[0], 1e-9)


def shallow_out(low, high, box):
    """The move [x, 0, z] that takes a box (low, high) reaching into a wall piece's box by more than MOVE_LEAST and
    at most HELD_MOST along the floor out of it the shorter way on that axis; None where it reaches in less, or more
    (one in the wall is parted's)."""
    reach = depths(low, high, box)
    if reach.min() <= MOVE_LEAST:
        return None
    ahead = np.asarray(box[1], float) - np.asarray(low, float)
    back = np.asarray(high, float) - np.asarray(box[0], float)
    moves = np.where(ahead <= back, ahead, -back)
    axis = 0 if abs(moves[0]) <= abs(moves[2]) else 2
    if abs(moves[axis]) > HELD_MOST:
        return None
    move = np.zeros(3)
    move[axis] = moves[axis]
    return move


def top_run(holds):
    """(axis, from, to, top) of the one run along x (0) or z (2) the tops of holder boxes [(low, high)] make, each
    meeting the next within BOARD_CLEAR at one height (BOARD_BED): two shelf units side by side; None where they make
    no one run."""
    lows, highs = np.array([box[0] for box in holds], float), np.array([box[1] for box in holds], float)
    if float(np.ptp(highs[:, 1])) > BOARD_BED:
        return None
    axis = 0 if highs[:, 0].max() - lows[:, 0].min() >= highs[:, 2].max() - lows[:, 2].min() else 2
    order = np.argsort(lows[:, axis])
    if any(lows[after, axis] > highs[before, axis] + BOARD_CLEAR for before, after in zip(order, order[1:])):
        return None
    return axis, float(lows[:, axis].min()), float(highs[:, axis].max()), float(highs[:, 1].max())


def spread_on_tops(stage, place, entries):
    """The things laid on the tops of the same holders (`entries`, their `on` how "top", of any row), where two of them
    meet by more than BOARD_CLEAR, spread evenly over the run their holders' tops make (top_run): in one line along
    it, each its built length and as many even gaps apart, where they all fit so, else in rows across the top
    (packed_rows: hub's 16 monitors on a 1.75 x 0.81 m console laid at one spot, lab's desk carrying its monitors,
    lamps and microscope one in the next, 2026-11-11), in their order along it. Each was kept within its nearest
    holder's top alone, so the pieces past one unit's end were pushed into the one before (settle@workshop's storage
    boxes 6 and 7 on their two shelf units, 2026-11-10). Things that fit neither way are left for the held gate to
    name; the fits [{name, how, ...}]."""
    groups, carried = {}, {}
    for entry in entries:
        groups.setdefault(tuple(entry["on"].get("holder") or []), []).append(entry)
        for holder in entry["on"].get("holder") or []:
            carried.setdefault(holder, []).append(entry["name"])
    fits = []
    for holders, pieces in groups.items():
        scope = pieces[0]["on"].get("holder scope", "Objects")
        holds = [world_box(stage, f"/{place}/{scope}/{name}") for name in holders
                 if stage.GetPrimAtPath(f"/{place}/{scope}/{name}")]
        boxes = {entry["name"]: world_box(stage, f"/{place}/Objects/{entry['name']}") for entry in pieces}
        run = top_run(holds) if holds and len(pieces) > 1 else None
        if run is None or not any(float(depths(*boxes[one], boxes[other]).min()) > BOARD_CLEAR
                                  for one in boxes for other in boxes if one < other):
            continue
        axis, start, end, top = run
        side = 2 - axis
        across_from = max(float(low[side]) for low, _ in holds)
        across_to = min(float(high[side]) for _, high in holds)
        order = sorted(pieces, key=lambda entry: float(sum(boxes[entry["name"]])[axis]))
        longs = [float(boxes[entry["name"]][1][axis] - boxes[entry["name"]][0][axis]) for entry in order]
        deeps = [float(boxes[entry["name"]][1][side] - boxes[entry["name"]][0][side]) for entry in order]
        rows = packed_rows(longs, deeps, end - start, across_to - across_from)
        if rows is None:
            continue
        spots = row_spots(rows, longs, deeps, (start, end), (across_from, across_to))
        for entry, (along, across_at) in zip(order, spots):
            name, (low, high) = entry["name"], boxes[entry["name"]]
            target = foot_middle(low, high)
            target[axis], target[1] = along, top
            if len(rows) > 1:
                target[side] = across_at
            moved = float(np.linalg.norm(target - foot_middle(low, high)))
            if moved < MOVE_LEAST:
                continue
            path = f"/{place}/Objects/{name}"
            moved_by(stage.GetPrimAtPath(path), foot_middle(low, high), 1.0, target)
            carry(stage, place, carried, name, target - foot_middle(low, high))
            fits.append(laid_fit(stage, path, entry, "spread", list(holders), moved, 1.0,
                                 f"spread {moved:.2f} m over its holders' tops: the things on them met there"))
    return fits


def carry(stage, place, carried, name, shift, seen=()):
    """The things laid on the top of a thing moved by `shift` (`carried`, {holder: [names]}), and theirs, moved with
    it: quarters' papers on a book were left where the book stood before its desk's things were spread (2026-11-11)."""
    for other in carried.get(name, []):
        if other in seen:
            continue
        path = f"/{place}/Objects/{other}"
        foot = foot_middle(*world_box(stage, path))
        moved_by(stage.GetPrimAtPath(path), foot, 1.0, foot + shift)
        carry(stage, place, carried, other, shift, (*seen, name))


def packed_rows(longs, deeps, length, depth):
    """[[piece, ...]] of things `longs` long and `deeps` deep (in their order) laid in rows across a top `length` long
    and `depth` deep, BOARD_CLEAR from each other and its edges: all in one row where they fit so, else each row
    filled in turn as far as it holds; None where a thing is longer than the top or the rows are deeper than it."""
    rows, row, used = [], [], BOARD_CLEAR
    for number, long in enumerate(longs):
        if row and used + long + BOARD_CLEAR > length:
            rows.append(row)
            row, used = [], BOARD_CLEAR
        if used + long + BOARD_CLEAR > length:
            return None
        row.append(number)
        used += long + BOARD_CLEAR
    rows.append(row)
    if len(rows) > 1 and sum(max(deeps[number] for number in row) for row in rows) + \
            BOARD_CLEAR * (len(rows) + 1) > depth:
        return None
    return rows


def row_spots(rows, longs, deeps, run, across):
    """[(along, across)] the middle of each piece of `rows` (packed_rows) on a top running `run` (from, to) along and
    `across` (from, to) deep: each row's pieces their lengths and as many even gaps apart along it, the rows their
    depths and as many even gaps apart across it, in order."""
    spots = {}
    sizes = [max(deeps[number] for number in row) for row in rows]
    gap_across = (across[1] - across[0] - sum(sizes)) / (len(rows) + 1)
    at_across = across[0]
    for row, size in zip(rows, sizes):
        gap = (run[1] - run[0] - sum(longs[number] for number in row)) / (len(row) + 1)
        at, middle = run[0], at_across + gap_across + size / 2
        for number in row:
            spots[number] = (at + gap + longs[number] / 2, middle)
            at += gap + longs[number]
        at_across += gap_across + size
    return [spots[number] for number in range(len(longs))]


def room_box(built):
    """[low x, low z, high x, high z] of the place's built walls [(name, (low, high))] (each named wall...), OPEN
    where it has none (an open place)."""
    room = [box for name, box in built if name.split("_")[0] == "wall"]
    return ([min(box[0][0] for box in room), min(box[0][2] for box in room), max(box[1][0] for box in room),
             max(box[1][2] for box in room)] if room else OPEN)


def past_walls(low, high, out, built):
    """The move [x, y, z] along a wall thing's `out` ([x, z]) that takes its box (low, high) clear of every static of
    the built structure (`built`: [(name, (low, high))]) it reaches into by more than HELD_MOST every way, past each
    one's far side in turn; and their names."""
    way = np.array([float(out[0]), 0.0, float(out[1])])
    shift, left = np.zeros(3), []
    for _ in built:  # a move past one can reach into another farther out: until none is left
        into = [(name, box) for name, box in built if depths(low + shift, high + shift, box).min() > HELD_MOST]
        if not into:
            break
        for name, box in into:  # clear of it on any one axis the way runs along: the least move that does
            ends = np.where(way > 0, np.asarray(box[1], float) - (low + shift),
                            np.asarray(box[0], float) - (high + shift))
            shift += way * min(max(0.0, float(ends[axis] / way[axis])) for axis in (0, 2) if abs(way[axis]) > 1e-9)
            left.append(name)
    return shift, list(dict.fromkeys(left))


def stacked_on_runs(stage, place, entries, walled):
    """Each thing on its holder's top (`entries`, their `on` how "top") laid inside a wall thing (`walled`, their `on`
    how "wall") its holder's top runs under (a pipe run packed PIECE_GAP over the one it stands on) moved straight up
    onto that one's top, then onto the next's, where that is OUT_MOST at most all told: hangar's valve on its pipe,
    the next pipe up its wall 5 cm over it, laid 0.25 m inside that one (2026-11-11); one further up is left for the
    held gate to name; the fits [{name, how "stacked", ...}]."""
    runs = [entry["name"] for entry in walled]
    fits = []
    for entry in entries:
        path, holders = f"/{place}/Objects/{entry['name']}", set(entry["on"].get("holder") or [])
        low, high = world_box(stage, path)
        lift, over = 0.0, []
        while found := [(name, box) for name in runs if name not in holders and name not in over
                        and depths(low + [0.0, lift, 0.0], high + [0.0, lift, 0.0],
                                   box := world_box(stage, f"/{place}/Objects/{name}")).min() > HELD_MOST]:
            lift = max(float(box[1][1]) for _, box in found) - float(low[1])
            over += [name for name, _ in found]
        if not over or lift > OUT_MOST:
            continue
        foot = foot_middle(low, high)
        moved_by(stage.GetPrimAtPath(path), foot, 1.0, foot + [0.0, lift, 0.0])
        fits.append(laid_fit(stage, path, entry, "stacked", over, lift, 1.0,
                             f"moved {lift:.2f} m up onto {', '.join(over)}: laid on its holder's top inside the run "
                             "packed over it"))
    return fits


def moved_past(stage, place, entries):
    """Each wall thing (`entries`, their `on` how "wall") standing outside its place's room (in_room: a passage's middle
    over none of its decks, a passage meeting its module from outside; any other's outside its walls' box: the
    greenhouse's pipe in its corner past its upper floor was pushed out through its wall, 2026-11-11) that reaches into a built wall or deck moved straight out along
    its `out` past it, where that is OUT_MOST or its own depth that way at most: its relation's face is a chord
    inside a round room's facets, so its body stood through the facets and its hatch alcove's walls (settle@workshop's
    front glass tunnel, 3 m deep, 0.08 to 0.15 m inside four walls, 1.48 m in from the alcove's end, 2026-11-10).
    One in the room is left as fitted; the fits [{name, how, ...}]."""
    built = statics(walls(stage, place))
    room, decks, fits = room_box(built), deck_triangles(stage, place), []
    for entry in entries:
        path = f"/{place}/Objects/{entry['name']}"
        low, high = world_box(stage, path)
        middle = foot_middle(low, high)
        if in_room(middle, room, decks if passes(entry) else ()):  # a passage by the floor; any other by the walls
            continue
        shift, left = past_walls(low, high, entry["on"]["out"], built)
        moved = float(np.linalg.norm(shift))
        if not left or moved > max(OUT_MOST, across(entry["on"]["out"], high - low)):
            continue
        moved_by(stage.GetPrimAtPath(path), middle, 1.0, middle + shift)
        fits.append({**laid_fit(stage, path, entry, "past", left, moved, 1.0,
                                f"moved {moved:.2f} m out past {', '.join(left)}: laid outside its place, into them"),
                     **laid_face({**entry["on"], "span": [np.asarray(point, float) + shift[[0, 2]]
                                                          for point in entry["on"]["span"]]},
                                 oriented_corners(stage, path))})  # the face it now stands on, for the held gate
    return fits


# A wall thing passing up through a vault's roof is stepped this far at a time into the room, up to IN_MOST, metres.
IN_STEP = 0.05
IN_MOST = 2.0


def moved_in(stage, place, entries, fits):
    """Each wall thing (`entries`, their `on` how "wall") whose built surface passes up through a roof's (through_roofs)
    moved into the room along its `out` by the least of IN_STEP steps that takes it clear (IN_MOST at most, its middle
    kept over the room's decks, in_room, and into no static it was not in), its fit's face (`span`), turned box and
    box moved with it, so the held gate measures it off the face it now stands on (`fits`, changed in place): a
    vault's sides curve in over its plan's straight walls (tube's screens, panels and pipe bundles laid on its walls'
    lines stood 0.5 to 2 m up through its vault, 2026-11-11). One no step clears is left for the held gate to name."""
    built = roofs(stage, place)
    if not built:
        return
    under, room, decks = statics(walls(stage, place)), room_box(statics(walls(stage, place))), deck_triangles(stage, place)
    by_fit = {fit["name"]: fit for fit in fits}
    for entry in entries:
        name, path = entry["name"], f"/{place}/Objects/{entry['name']}"
        if not through_roofs(stage, place, [name], built):
            continue
        out = np.array([float(entry["on"]["out"][0]), 0.0, float(entry["on"]["out"][1])])
        points, (low, high) = surface_points(stage, path), world_box(stage, path)
        before = {found for found, _ in inside_of(low, high, under)}
        step = next((count * IN_STEP for count in range(1, int(round(IN_MOST / IN_STEP)) + 1)
                     if in_room(foot_middle(low, high) + out * count * IN_STEP, room, decks)
                     and all(through_roof(points + out * count * IN_STEP, triangles) <= HELD_MOST
                             for _, triangles in built)
                     and not {found for found, _ in inside_of(low + out * count * IN_STEP, high + out * count * IN_STEP,
                                                              under)} - before), None)
        if step is None:
            continue
        middle = foot_middle(low, high)
        moved_by(stage.GetPrimAtPath(path), middle, 1.0, middle + out * step)
        words = f"moved {step:.2f} m into the room from its wall: its wall's line stands outside the roof there"
        from pxr import Sdf
        stage.GetPrimAtPath(path).CreateAttribute("score:fitted", Sdf.ValueTypeNames.String).Set(words)
        after = world_box(stage, path)
        fit = by_fit.get(name)
        if fit is None:
            fit = {"name": name, "row": entry["row"], "how": "wall", "holder": None, "moved": 0.0, "scale": 1.0}
            fits.append(fit)
        shift = (out * step)[[0, 2]]
        fit.update({"moved": round(float(fit["moved"]) + step, 3), "words": f"{fit.get('words', '')}; {words}",
                    "low": [round(float(value), 4) for value in after[0]],
                    "high": [round(float(value), 4) for value in after[1]],
                    **{key: [[round(float(value), 4) for value in np.asarray(point, float) + shift]
                             for point in fit[key]] for key in ("span", "corners") if key in fit}})
        if "span" not in fit:
            fit.update(laid_face({**entry["on"], "span": [np.asarray(point, float) + shift
                                                          for point in entry["on"]["span"]]},
                                 oriented_corners(stage, path)))


def deck_triangles(stage, place):
    """[n, 3, 3] world triangles of the place's built decks (its Structure and Shell prims named deck...), the floor
    its room stands on; empty with none (an open place)."""
    from pxr import Usd, UsdGeom
    found = [mesh_triangles(prim) for scope in ("Structure", "Shell")
             for name, _ in walls_in(stage, place, scope) if name.split("_")[0] == "deck"
             for prim in Usd.PrimRange(stage.GetPrimAtPath(f"/{place}/{scope}/{name}")) if prim.IsA(UsdGeom.Mesh)]
    found = [triangles for triangles in found if len(triangles)]
    return np.concatenate(found) if found else np.zeros((0, 3, 3))


def in_room(point, room, decks):
    """Whether a point [x, y, z] stands in its place's room: over its built decks' faces (`decks`, deck_triangles)
    where it has any, else within its walls' box (`room`, room_box). By the box alone, workshop's round room held its
    glass tunnels outside it, so they were left across its door 2 and door 3 (2026-11-11)."""
    if len(decks):
        return bool(np.isfinite(roof_under(np.asarray(point, float)[None, :], decks))[0])
    return room[0] <= point[0] <= room[2] and room[1] <= point[2] <= room[3]


def roofs(stage, place):
    """[(name, triangles [n, 3, 3] in the world)] of the place's built roofs (its Structure prims named ROOF..., and an
    inside place's Shell's, design_shell.py: airlock's dome, which hung_up never saw, its roof light left 0.13 m under
    it touching nothing, 2026-11-10): each drawn mesh's faces, fanned into triangles."""
    from pxr import Usd, UsdGeom
    scopes = [stage.GetPrimAtPath(f"/{place}/{scope}") for scope in ("Structure", "Shell")]
    found = []
    for child in [child for root in scopes if root for child in root.GetChildren()]:
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


# A thing hung from the roof stands this far under its built underside, metres (the scene record's ROOF_CLEAR).
ROOF_CLEAR = 0.01


def under_roof_gap(points, built):
    """Metres the lowest built roof face over a surface's points stands over its highest point there (the least gap
    over any of them), None where no roof face stands over any."""
    gaps = [roof_under(points, triangles) - points[:, 1] for _, triangles in built]
    gaps = [gap[np.isfinite(gap)] for gap in gaps]
    found = [float(gap.min()) for gap in gaps if len(gap)]
    return min(found) if found else None


def box_topped(points):
    """A thing's surface points [n, 3] each raised to its top: its box's top over its footprint, which a thing hung
    from the roof keeps under the roof (hangar's crane, its top in the roof's open middle, 0.34 m higher than its parts
    under the roof's edge strips, stood up through them, 2026-11-11)."""
    return np.c_[points[:, 0], np.full(len(points), points[:, 1].max() if len(points) else 0.0), points[:, 2]]


def hung_up(stage, place, entries):
    """Each entry hung from the roof (the scene record's `under roof`: laid with its top at the roof's underside by its
    reading's tall) whose built top (box_topped: its box's, over its footprint) stands more than ROOF_CLEAR under the
    built roof over it moved straight up to it,
    where that is OUT_MOST at most: its model is made at its own tall, so the record's hang leaves a shorter one
    touching nothing (settle@airlock, 2026-11-10: its roof light read 0.4 m tall, built 0.27, 0.13 m under its dome);
    the fits [{name, how, ...}]."""
    built, fits = roofs(stage, place), []
    for entry in entries if built else []:
        if not entry.get("under roof"):
            continue
        path = f"/{place}/Objects/{entry['name']}"
        gap = under_roof_gap(box_topped(surface_points(stage, path)), built)
        if gap is None or not ROOF_CLEAR + MOVE_LEAST < gap <= OUT_MOST + ROOF_CLEAR:
            continue
        lift = gap - ROOF_CLEAR
        low, high = world_box(stage, path)
        moved_by(stage.GetPrimAtPath(path), foot_middle(low, high), 1.0, foot_middle(low, high) + [0.0, lift, 0.0])
        words = f"moved {lift:.2f} m up to the roof it hangs from: built shorter than its reading"
        from pxr import Sdf
        stage.GetPrimAtPath(path).CreateAttribute("score:fitted", Sdf.ValueTypeNames.String).Set(words)
        after = world_box(stage, path)
        fits.append({"name": entry["name"], "row": entry["row"], "how": "up", "holder": [name for name, _ in built],
                     "moved": round(lift, 3), "scale": 1.0, "low": [round(float(value), 4) for value in after[0]],
                     "high": [round(float(value), 4) for value in after[1]], "words": words})
    return fits


def hung_by_parts(stage, place, entries):
    """Each entry hung from the roof (`under roof`) whose built surface touches no roof over it after hung_up (its box's
    top hung under the roof where its tallest part stands in the roof's opening: hangar's crane, hung by its box, its
    trolley up in the open middle and its ends 0.63 m and more under the edge strips its runs ride, touching nothing,
    motion@hangar 2026-11-11) moved straight up until a part under a roof stands ROOF_CLEAR under it, its taller parts
    standing up in the opening, and moved out from under a roof edge a part overhangs by HELD_MOST at most (part_hang),
    where that is OUT_MOST at most and takes it into no deck or level it was not in; the fits [{name, how "hung", ...}]."""
    built, fits, under = roofs(stage, place), [], statics(walls(stage, place))
    sinks = [(name, box) for name, box in under if name.split("_")[0] != "wall"]
    for entry in entries if built else []:
        path = f"/{place}/Objects/{entry['name']}"
        if not entry.get("under roof") or not stage.GetPrimAtPath(path).IsActive():
            continue
        hang = part_hang(surface_points(stage, path), built)
        if hang is None:
            continue
        low, high = world_box(stage, path)
        move = np.array([hang[1][0], hang[0], hang[1][1]])
        if {name for name, _ in inside_of(low + move, high + move, sinks)} - {name for name, _ in inside_of(low, high,
                                                                                                         sinks)}:
            continue
        moved_by(stage.GetPrimAtPath(path), foot_middle(low, high), 1.0, foot_middle(low, high) + move)
        words = (f"moved {hang[0]:.2f} m up to the roof over its parts, its taller ones standing in the roof's opening"
                 + (f", {float(np.linalg.norm(hang[1])):.3f} m out from under a roof edge" if np.any(hang[1]) else ""))
        from pxr import Sdf
        stage.GetPrimAtPath(path).CreateAttribute("score:fitted", Sdf.ValueTypeNames.String).Set(words)
        after = world_box(stage, path)
        fits.append({"name": entry["name"], "row": entry["row"], "how": "hung", "holder": [name for name, _ in built],
                     "moved": round(float(np.linalg.norm(move)), 3), "scale": 1.0,
                     "low": [round(float(value), 4) for value in after[0]],
                     "high": [round(float(value), 4) for value in after[1]], "words": words})
    return fits


def part_hang(points, built):
    """(lift, [x, z] shift) that hangs a surface's points [n, 3] from the roofs `built` by its parts: straight up until
    one under a roof stands ROOF_CLEAR under it, none through any, the highest such hang first (its parts under the
    roof it stands highest under); a part that would go up through another roof's edge it overhangs is taken out from
    under it by the least shift along x or z, HELD_MOST at most. None where a part already stands ROOF_CLEAR (and
    MOVE_LEAST) under a roof, where no roof is over it, or where no hang of OUT_MOST at most is left."""
    heights = np.array([roof_under(points, triangles) for _, triangles in built]).reshape(len(built), len(points))
    gaps = heights - points[:, 1]
    if not np.isfinite(gaps).any() or np.nanmin(gaps) <= ROOF_CLEAR + MOVE_LEAST:
        return None
    lifts = sorted({float(np.nanmin(gap)) - ROOF_CLEAR for gap in gaps if np.isfinite(gap).any()}, reverse=True)
    for lift in [lift for lift in lifts if lift <= OUT_MOST]:
        through = np.isfinite(gaps) & (gaps < lift + ROOF_CLEAR - 1e-6)
        shift = out_from_under(points, through, built)
        if shift is None or float(np.linalg.norm(shift)) > HELD_MOST:
            continue
        moved = points + [shift[0], 0.0, shift[1]]
        after = np.array([roof_under(moved, triangles) for _, triangles in built]).reshape(gaps.shape) - moved[:, 1]
        if not (np.isfinite(after) & (after < lift + ROOF_CLEAR - 1e-6)).any():
            return lift, shift
    return None


def out_from_under(points, through, built):
    """The least [x, z] shift along one axis taking each point [n, 3] off every roof (`built`) it would go up through
    (`through` [roofs, n]), MOVE_LEAST past the roof's box; [0, 0] where none would."""
    if not through.any():
        return np.zeros(2)
    needs = []
    for axis, sign in ((0, 1.0), (0, -1.0), (2, 1.0), (2, -1.0)):
        need = 0.0
        for (_, triangles), over in zip(built, through):
            if over.any():
                corners = triangles.reshape(-1, 3)
                edge = corners[:, axis].max() if sign > 0 else corners[:, axis].min()
                need = max(need, float(np.max(sign * (edge - points[over, axis]))) + MOVE_LEAST)
        needs.append((need, axis, sign))
    need, axis, sign = min(needs)
    return np.array([sign * need, 0.0]) if axis == 0 else np.array([0.0, sign * need])


def moved_down(stage, place, entries):
    """Each entry laid with nothing holding it (no `on`) whose built surface passes up through a roof's (through_roofs:
    by its mesh, never its box) moved straight down under it, where that is OUT_MOST at most and sinks it into no deck,
    level or wall it was not in (greenhouse's cabinet and tanks on its upper floor under its low roof would have gone
    0.8 to 0.96 m into that floor); one further through or with no room under it is left as laid, for the held gate
    to name. One hung from the roof (`under roof`) whose box's top (box_topped) reaches over the roof's underside over
    it is hung ROOF_CLEAR under it however far that is, as its relation lays it, and only kept out of a deck or level:
    parted takes it out of a wall across the floor (hangar's 6.5 m tall cranes laid by their 2 m reading, 4.5 m up
    through its roof's edges, 2026-11-11); the fits [{name, how, ...}]."""
    built, fits, under = roofs(stage, place), [], statics(walls(stage, place))
    for entry in entries if built else []:
        path, hung = f"/{place}/Objects/{entry['name']}", bool(entry.get("under roof"))
        if hung:
            top = box_topped(surface_points(stage, path))
            through = [{"roof": roof, "metres": round(-float(np.nanmin(gaps)), 3)} for roof, triangles in built
                       if len(gaps := roof_under(top, triangles) - top[:, 1]) and np.isfinite(gaps).any()
                       and np.nanmin(gaps) < ROOF_CLEAR - MOVE_LEAST]
            drop = max([found["metres"] for found in through], default=0.0) + ROOF_CLEAR
        else:
            through = through_roofs(stage, place, [entry["name"]], built)
            drop = max([found["metres"] for found in through], default=0.0)
        low, high = world_box(stage, path)
        lowered = (low - [0.0, drop, 0.0], high - [0.0, drop, 0.0])
        sinks = [(name, box) for name, box in under if not (hung and name.split("_")[0] == "wall")]
        if not through or (drop > OUT_MOST and not hung) or {name for name, _ in inside_of(*lowered, sinks)} - {
                name for name, _ in inside_of(low, high, sinks)}:
            continue
        moved_by(stage.GetPrimAtPath(path), foot_middle(low, high), 1.0, foot_middle(low, high) - [0.0, drop, 0.0])
        left = [found["roof"] for found in through]
        words = (f"moved {drop:.2f} m down under {', '.join(left)}: hung from it, built taller than its reading" if hung
                 else f"moved {drop:.2f} m down out of {', '.join(left)}: laid up through it, nothing holding it there")
        from pxr import Sdf
        stage.GetPrimAtPath(path).CreateAttribute("score:fitted", Sdf.ValueTypeNames.String).Set(words)
        after = world_box(stage, path)
        fits.append({"name": entry["name"], "row": entry["row"], "how": "down", "holder": left, "moved": round(drop, 3),
                     "scale": 1.0, "low": [round(float(value), 4) for value in after[0]],
                     "high": [round(float(value), 4) for value in after[1]], "words": words})
    return fits
