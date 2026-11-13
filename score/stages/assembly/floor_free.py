"""Things on the floor kept clear of the built walls, and its flat things of the wall things too, by their surfaces as
the drop judges them (fitting.fitted calls cleared last; settle@habitat failed its resting gate on them, 2026-11-13).

    cleared(stage, place, loose, entries)   walls_clear, then flat_clear, then the edges of the flat things moved
    walls_clear(stage, place, loose, entries)   each standing thing reaching into a built wall moved the least way out
    flat_clear(stage, place, loose, entries)    each flat thing reaching into a wall or a wall thing moved, or shrunk,
                                                to its free floor patch

The parting and the clearings after it judge by boxes and let a thing stand up to HELD_MOST (5 cm) into a slanted wall
and the resting check's 3 cm into a straight one; a flat thing, a rug 1.7 cm thick, never reaches any of them by its
box's height, so nothing ever moved one. The drop takes an object whose triangles still cross a static's after a
NUDGE as laid inside it (left as laid, its layout's fault): habitat's rugs 4 and 7 to 10, laid at the plan's spots in
its corner rooms, lay across its partition walls 19 to 22 and under control panel 2 and curtain 5, and bookshelf 2
stood 2 cm into slanted wall_11. Its bunk bed 2, 2.01 m long where the room between slanted wall_15 and wall_18 is
1.91 m, stood 4.4 cm into the one and 3.4 cm into the other, and its hull slid 92 cm out between them in the drop.
Here each thing's floor footprint (its own turned box) is judged against the walls' (and wall things') cuts at its
height, sampled every SAMPLE, and moved the least way along its own axes, by STEP up to MOVE_MOST (a flat thing
FLAT_MOVE_MOST), to stand GAP clear of them, its middle passing through none it did not start in, over the deck it
stands on; a flat thing that has no such spot at its size is shrunk about its middle, by SHRINK_STEP down to
SHRINK_MOST, to the largest that has one. One with none is left as laid, for the gate to name.
"""
import numpy as np

# What reaches into a static less than this is no overlap to the drop (settle_drop.NUDGE), metres.
NUDGE = 0.005
# How far clear of the walls a thing moved is set, metres.
GAP = 0.01
# The step of the moves tried, and of the points a wall's cut is sampled at, metres.
STEP = 0.01
SAMPLE = 0.01
# The furthest a standing thing is moved along each of its own axes, and a flat one, metres.
MOVE_MOST = 0.5
FLAT_MOVE_MOST = 1.0
# The least share of its size a flat thing keeps, and the step it is shrunk by.
SHRINK_MOST = 0.5
SHRINK_STEP = 0.02
# Where a standing thing's footprint is cut through the walls: this far over its foot, and at its middle, metres.
FOOT_CUT = 0.05


def cut(mesh, height):
    """[k, 2, 2] the floor segments (x, z) of a mesh's cut at `height`."""
    import trimesh
    segments = trimesh.intersections.mesh_plane(mesh, [0.0, 1.0, 0.0], [0.0, float(height), 0.0])
    return np.asarray(segments, float).reshape(-1, 2, 3)[:, :, [0, 2]]


def sampled(segments):
    """[n, 2] floor points along the segments [k, 2, 2], SAMPLE apart along each."""
    if not len(segments):
        return np.zeros((0, 2))
    starts, ends = segments[:, 0], segments[:, 1]
    counts = np.maximum(np.ceil(np.linalg.norm(ends - starts, axis=1) / SAMPLE).astype(int), 1)
    shares = np.concatenate([np.linspace(0.0, 1.0, count + 1) for count in counts])
    firsts, lasts = np.repeat(starts, counts + 1, axis=0), np.repeat(ends, counts + 1, axis=0)
    return firsts + (lasts - firsts) * shares[:, None]


def holds(segments, point):
    """Whether a floor point stands inside the closed cut the segments [k, 2, 2] draw (a ray along x crosses it an
    odd number of times)."""
    if not len(segments):
        return False
    starts, ends = segments[:, 0], segments[:, 1]
    spans = (starts[:, 1] > point[1]) != (ends[:, 1] > point[1])
    rise = np.where(spans, ends[:, 1] - starts[:, 1], 1.0)
    at = starts[:, 0] + (point[1] - starts[:, 1]) * (ends[:, 0] - starts[:, 0]) / rise
    return bool(int((spans & (at > point[0])).sum()) % 2)


def obstacles(meshes, heights, middle):
    """(points [n, 2], through [m, 2]) of the meshes' cuts at each of `heights` (sampled): all of them, and those of the
    meshes whose cut does not hold the floor point `middle` (what a thing's middle starts in it may pass out of)."""
    found, through = [np.zeros((0, 2))], [np.zeros((0, 2))]
    for _, mesh in meshes:
        for height in heights:
            segments = cut(mesh, height)
            points = sampled(segments)
            found.append(points)
            if not holds(segments, middle):
                through.append(points)
    return np.concatenate(found), np.concatenate(through)


def footprint(stage, path):
    """(middle [2], axes [2, 2] (its own floor axes as rows), half [2]) of a prim's own turned box on the floor
    (fitting.oriented_corners)."""
    from score.stages.assembly import fitting
    corners = fitting.oriented_corners(stage, path)[:, [0, 2]]
    along, across = corners[4] - corners[0], corners[1] - corners[0]
    sides = np.array([along, across])
    lengths = np.maximum(np.linalg.norm(sides, axis=1), 1e-9)
    return corners[0] + (along + across) / 2, sides / lengths[:, None], lengths / 2


def local(points, middle, axes):
    """[n, 2] floor points in a footprint's own frame (its middle, its axes)."""
    return (np.asarray(points, float).reshape(-1, 2) - middle) @ axes.T


def reaches(points, half):
    """Whether any of the points (own frame) stands inside a footprint `half` by more than NUDGE."""
    return bool(((np.abs(points) < half - NUDGE).all(axis=1)).any())


def free_moves(points, half, steps):
    """[k, 2] the moves (own frame) on a grid STEP apart, `steps` each way, that leave a footprint `half` GAP clear of
    every point (own frame), the least first."""
    size = 2 * steps + 1
    blocked = np.zeros((size + 1, size + 1), int)
    reach = half + GAP
    first = np.clip(np.ceil((points - reach) / STEP - 1e-9).astype(int) + steps, 0, size)
    last = np.clip(np.floor((points + reach) / STEP + 1e-9).astype(int) + steps + 1, 0, size)
    keep = (first < last).all(axis=1)
    first, last = first[keep], last[keep]
    np.add.at(blocked, (first[:, 0], first[:, 1]), 1)
    np.add.at(blocked, (last[:, 0], first[:, 1]), -1)
    np.add.at(blocked, (first[:, 0], last[:, 1]), -1)
    np.add.at(blocked, (last[:, 0], last[:, 1]), 1)
    taken = blocked.cumsum(axis=0).cumsum(axis=1)[:size, :size] > 0
    along, across = np.nonzero(~taken)
    moves = np.stack([along - steps, across - steps], axis=1) * STEP
    return moves[np.lexsort((moves[:, 1], moves[:, 0], np.hypot(moves[:, 0], moves[:, 1])))]


def passes_through(points, move):
    """Whether a footprint's middle, moved by `move` (own frame), passes within GAP of any of the points (own frame)."""
    length = float(np.hypot(*move))
    if length < 1e-9:
        return False
    way = np.asarray(move, float) / length
    along = np.clip(points @ way, 0.0, length)
    return bool((np.linalg.norm(points - along[:, None] * way, axis=1) < GAP).any())


def placed(spot, half, axes, deck):
    """Whether a footprint at `spot` (world floor middle), `half` along its `axes`, stands over the `deck`
    (fitting.deck_at's; None: on the ground) at its middle and its corners."""
    from score.stages.assembly import fitting
    if deck is None:
        return True
    corners = np.array([spot + sign_one * half[0] * axes[0] + sign_two * half[1] * axes[1]
                        for sign_one in (-1, 1) for sign_two in (-1, 1)] + [spot])
    level = float(deck[:, :, 1].mean())
    return bool(np.isfinite(fitting.roof_under(np.column_stack([corners[:, 0], np.full(len(corners), level),
                                                                   corners[:, 1]]), deck)).all())


def spot_for(found, middle, axes, half, deck, scales, most, allowed=lambda move, scale: True):
    """(scale, world floor move [2]) of the largest of `scales` at which a footprint (its middle, axes, half) has a free
    spot (free_moves) clear of the points (`found`: obstacles' (points, through), world) `most` away at most along
    each of its axes, its middle passing through none of the `through` points, over its deck, `allowed` by the caller;
    the least such move. None where none is."""
    reach = half.max() + most + GAP + STEP
    near, crossed = (own[(np.abs(own) <= reach).all(axis=1)] for own in (local(points, middle, axes)
                                                                         for points in found))
    steps = int(round(most / STEP))
    for scale in scales:
        for move in free_moves(near, half * scale, steps):
            world = move @ axes
            if passes_through(crossed, move) or not placed(middle + world, half * scale, axes, deck) \
                    or not allowed(world, scale):
                continue
            return scale, world
    return None


def meshes_near(stage, paths, low, high, most):
    """[(path, its world mesh)] of the `paths` whose world box meets a box (low, high) widened `most` on the floor."""
    from score.stages.assembly import fitting
    found = []
    reach = np.array([most + GAP, 0.0, most + GAP])
    for path in paths:
        other = fitting.world_box(stage, path)
        if (np.minimum(high + reach, other[1]) - np.maximum(low - reach, other[0]) >= 0.0).all():
            mesh = fitting.surface_mesh(stage, path)
            if mesh is not None:
                found.append((path, mesh))
    return found


def wall_paths(stage, place):
    """The paths of the place's built pieces (fitting.walls: its Structure and Shell)."""
    return [f"/{place}/{scope}/{child.GetName()}" for scope in ("Structure", "Shell")
            if (root := stage.GetPrimAtPath(f"/{place}/{scope}")) for child in root.GetChildren()]


def shrunk(low, high, middle, scale, move):
    """The box (low, high) of a flat thing's box shrunk by `scale` about its footprint's `middle` on the floor and moved
    by the floor `move` [2]."""
    at = np.array([middle[0], 0.0, middle[1]])
    shift = np.array([move[0], 0.0, move[1]])
    floor = np.array([scale, 1.0, scale])
    return at + (np.asarray(low, float) - at) * floor + shift, at + (np.asarray(high, float) - at) * floor + shift


def edged(low, high, boxes):
    """{index} of the `boxes` (low, high) standing across the floor edge of a flat thing's box (low, high): partly on
    it by their footprints, never wholly on or off it."""
    found = set()
    for number, (one, other) in enumerate(boxes):
        on = np.minimum(high, other)[[0, 2]] - np.maximum(low, one)[[0, 2]]
        if (on > 0.0).all() and not ((one[[0, 2]] >= low[[0, 2]]).all() and (other[[0, 2]] <= high[[0, 2]]).all()):
            found.add(number)
    return found


def carried_by(entries):
    """{holder: [the things whose relation holds them on or in it]} of the record's entries."""
    found = {}
    for entry in entries:
        if (entry.get("on") or {}).get("holder scope", "Objects") == "Objects":
            for holder in (entry.get("on") or {}).get("holder") or []:
                found.setdefault(holder, []).append(entry["name"])
    return found


def walls_clear(stage, place, loose, entries):
    """Each standing thing on the floor (`loose`, flat ones aside) whose footprint a built wall's cut, at FOOT_CUT
    over its foot and at its middle, reaches into by more than NUDGE moved the least way to stand GAP clear of every
    wall there (spot_for), reaching into no other laid thing it shares height with by more than the resting check's
    touch where it did not, and across no flat thing's edge it was not across where it is too broad to lean there
    (edged) where a spot keeps it so, with what it holds (carried_by); the fits [{name, how "off wall", ...}]."""
    from score.stages.assembly import fitting, floor_clear
    boxes = floor_clear.laid_boxes(stage, place, [entry for entry in entries if entry.get("name")])
    walls, decks, carried, fits = wall_paths(stage, place), fitting.deck_triangles(stage, place), \
        carried_by(entries), []
    flats = [box for name, box in floor_clear.laid_boxes(stage, place, loose).items() if floor_clear.flat(box)]
    for entry in loose:
        name, path = entry["name"], f"/{place}/Objects/{entry['name']}"
        if name not in boxes or floor_clear.flat(boxes[name]) or set(str(entry.get("row") or "").split("_")) & set(
                fitting.PASSING):  # a passage meets its place through its wall
            continue
        low, high = boxes[name]
        middle, axes, half = footprint(stage, path)
        found = obstacles(meshes_near(stage, walls, low, high, MOVE_MOST),
                          (float(low[1]) + FOOT_CUT, (float(low[1]) + float(high[1])) / 2), middle)
        if not reaches(local(found[0], middle, axes), half):
            continue
        held = set(carried.get(name, []))
        others = [box for other, box in boxes.items() if other != name and other not in held
                  and fitting.tall_together(boxes[name], box)
                  and fitting.depths(low, high, box).min() <= floor_clear.TOUCH]

        rugs = [box for box in flats if not floor_clear.leans((low, high), box[1][1] - box[0][1])]
        across = {number for number, box in enumerate(rugs) if edged(*box, [(low, high)])}

        def apart(move, scale, others=others, low=low, high=high):
            shift = np.array([move[0], 0.0, move[1]])
            return all(fitting.depths(low + shift, high + shift, box).min() <= floor_clear.TOUCH for box in others)

        def kept_off(move, scale, rugs=rugs, across=across, low=low, high=high):
            shift = np.array([move[0], 0.0, move[1]])
            return apart(move, scale) and {number for number, box in enumerate(rugs)
                                           if edged(*box, [(low + shift, high + shift)])} <= across

        deck = fitting.deck_at((low, high), decks)
        spot = spot_for(found, middle, axes, half, deck, (1.0,), MOVE_MOST, kept_off) or \
            spot_for(found, middle, axes, half, deck, (1.0,), MOVE_MOST, apart)
        if spot is None:
            continue
        shift = np.array([spot[1][0], 0.0, spot[1][1]])
        foot = fitting.foot_middle(low, high)
        fitting.moved_by(stage.GetPrimAtPath(path), foot, 1.0, foot + shift)
        fitting.carry(stage, place, carried, name, shift)
        boxes[name] = fitting.world_box(stage, path)
        fits.append(fitting.laid_fit(stage, path, entry, "off wall", None, np.linalg.norm(shift), 1.0,
                                     f"moved {float(np.linalg.norm(shift)):.2f} m off a built wall its footprint "
                                     f"reached into"))
    return fits


def flat_clear(stage, place, loose, entries):
    """Each flat thing on the floor (`loose`, floor_clear.flat) whose footprint the cut, at its middle height, of a
    built wall, a fixture or a laid thing a relation holds (a wall thing standing on the floor) reaches into by more
    than NUDGE moved the least way to stand GAP clear of them, or shrunk about its middle to the largest share, down
    to SHRINK_MOST, that has such a spot (spot_for), with no standing thing too broad to lean across its edge
    (floor_clear.leans) across it (edged; the small ones are floor_clear.off_edges'), else none newly across it; the
    fits [{name, how "flat clear", ...}]."""
    from score.stages.assembly import fitting, floor_clear
    held = [f"/{place}/Objects/{entry['name']}" for entry in entries if entry.get("on")
            and stage.GetPrimAtPath(f"/{place}/Objects/{entry['name']}")
            and stage.GetPrimAtPath(f"/{place}/Objects/{entry['name']}").IsActive()]
    fixtures = [f"/{place}/Fixtures/{name}" for name, _ in fitting.walls_in(stage, place, "Fixtures")]
    statics, decks, fits = [*wall_paths(stage, place), *fixtures, *held], fitting.deck_triangles(stage, place), []
    scales = [1.0 - number * SHRINK_STEP for number in range(int(round((1.0 - SHRINK_MOST) / SHRINK_STEP)) + 1)]
    for entry in loose:
        path = f"/{place}/Objects/{entry['name']}"
        prim = stage.GetPrimAtPath(path)
        if not prim or not prim.IsActive() or entry.get("under roof"):
            continue
        low, high = fitting.world_box(stage, path)
        if not floor_clear.flat((low, high)):
            continue
        middle, axes, half = footprint(stage, path)
        found = obstacles(meshes_near(stage, statics, low, high, FLAT_MOVE_MOST),
                          ((float(low[1]) + float(high[1])) / 2,), middle)
        if not reaches(local(found[0], middle, axes), half):
            continue
        standing = [box for name, box in floor_clear.laid_boxes(stage, place, loose).items() if name != entry["name"]
                    and not floor_clear.flat(box) and not floor_clear.leans(box, high[1] - low[1])]
        across = edged(low, high, standing)

        def clear(move, scale, low=low, high=high, standing=standing, middle=middle):
            return not edged(*shrunk(low, high, middle, scale, move), standing)

        def kept(move, scale, low=low, high=high, across=across, standing=standing, middle=middle):
            return edged(*shrunk(low, high, middle, scale, move), standing) <= across

        deck = fitting.deck_at((low, high), decks)
        spot = spot_for(found, middle, axes, half, deck, scales, FLAT_MOVE_MOST, clear) or \
            spot_for(found, middle, axes, half, deck, scales, FLAT_MOVE_MOST, kept)
        if spot is None:
            continue
        scale, move = spot
        foot = fitting.foot_middle(low, high)
        target = foot + np.array([move[0], 0.0, move[1]])
        foot_at = foot.copy()
        foot_at[[0, 2]] = middle  # shrunk about its footprint's middle
        fitting.moved_by(prim, foot_at, [scale, 1.0, scale], foot_at + (target - foot))
        moved = float(np.hypot(*move))
        fits.append(fitting.laid_fit(stage, path, entry, "flat clear", None, moved, [scale, 1.0, scale],
                                     f"moved {moved:.2f} m and shrunk to {scale:.0%} onto its free floor patch: "
                                     f"laid into a wall or a wall thing"))
    return fits


def cleared(stage, place, loose, entries):
    """The standing things on the floor off the walls (walls_clear), then its flat things clear of the walls and wall
    things (flat_clear), then what stands across a flat thing's edge moved again (floor_clear.off_edges) where any
    moved; the fits."""
    from score.stages.assembly import floor_clear
    fits = walls_clear(stage, place, loose, entries) + flat_clear(stage, place, loose, entries)
    return fits + (floor_clear.off_edges(stage, place, loose) if fits else [])
