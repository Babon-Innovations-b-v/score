"""A thing on its holder's top that crest_tops.laid_on and flush_tops.laid left not resting, laid on a spot of the top
where it rests, read FINE apart (crest_tops reads them STEP apart, 2.5 cm), clear of every other thing laid by its
turned outline where it is a thin one turned off the floor's axes (fitting.thin_outline: a railing laid diagonally,
whose world box holds the room beside it), by its box otherwise (tops_levelled.laid, after flush_tops).

settle@greenhouse, 2026-11-13 (its inputs' seed laid with the resting triage as laid): its desk's model (one model, six
desks) has no flat top: a U of sloping bowls 0.35 to 0.54 m up, whose one level stretch is its front rim at 0.54 m,
0.1 to 0.15 m deep. A 0.4 m computer stands on it with its weight triage.BALANCE inside what it touches only with its
front a little past the desk's (its middle within 2 cm of one spot): crest_tops keeps a thing's footprint within its
holder's box, 2.5 cm apart, and its box test took the room beside the place's diagonal railings for railing, so the four
computers were left over the bowls and the settle let them down 10 cm into them, leaning 51 degrees. Each now stands on
that rim as it was laid (no turn), its weight inside what it touches by the check's own measure (crest_tops.stands).

One no spot of its holders' top holds is laid on the top of one of the others laid on them where it rests there, the
nearest first (`stacked`): settle@quarters, 2026-11-13, its desk (a 1.2 m bake of a 2.5 m reading, its front left
0.6 x 0.3 m open, the rest sloping 2 to 3 degrees) holds its 25 things only with some on others, and its mouse, a
wrench, a plant pot on the keyboard and a picture frame on the other pot leaned 3.5 to 22 degrees where they were laid.

    FINE                          metres apart the spots are read
    meets(low, high, other)       whether a box reaches into another thing's box or turned outline
    laid(stage, place, entries)   each thing on its holders' top (`entries`, built_tops.held_on's) that does not rest
                                  where it is laid, or reaches into another laid on them (crowding), on the nearest
                                  spot where it rests clear of the others; the fits [{..., "top at"}]
    crowding(stage, place, entry, carried, box_of)   the other laid on its holders, no taller, it reaches into, or None
    stacked(stage, place, entry, thing, box_of, carried)   (the move, the name) onto the nearest other's top where
                                  it rests
"""
import numpy as np

from score.stages.assembly import crest_tops, fitting

# How far apart, metres, the spots of a holder's top a thing is tried at are read, each way.
FINE = 0.005
# How far, metres, crowding reads boxes as the same: another's top this far over a thing's own is as high (two of one
# model side by side), and a box this far into another is clear of it (spot lays one at the clear edge, which reads a
# hair into it once its move is written in single floats).
SAME = 1e-4


def laid(stage, place, entries):
    """Each thing on its holders' top that does not rest where it is laid on the nearest spot where it rests (module
    docstring), a holder before what it holds, carrying what is on its own top; the fits."""
    by_name = {entry["name"]: entry for entry in entries if entry["on"].get("how") == "top"}
    carried = {}
    for entry in entries:
        for holder in entry["on"].get("holder") or []:
            carried.setdefault(holder, []).append(entry["name"])
    fits = []
    for name in crest_tops.ordered(by_name):
        fit = one(stage, place, by_name[name], fitting.with_stacked(stage, place, carried, list(by_name)))
        if fit is not None:
            fits.append(fit)
    return fits


def one(stage, place, entry, carried):
    """One thing laid on the nearest spot of its holders' top where it rests, when it does not rest where it is; its
    fit, or None when it rests there or no spot holds it."""
    import resting
    import triage
    import trimesh
    holders = [f"/{place}/Objects/{holder}" for holder in entry["on"].get("holder") or []
               if stage.GetPrimAtPath(f"/{place}/Objects/{holder}")]
    found = [mesh for mesh in (fitting.surface_mesh(stage, path) for path in holders) if mesh is not None]
    path = f"/{place}/Objects/{entry['name']}"
    own = crest_tops.as_levelled(stage.GetPrimAtPath(path), fitting.surface_mesh(stage, path))
    if not found or own is None or own.area <= 0:
        return None
    boxes = [fitting.world_box(stage, holder) for holder in holders]
    box = (np.min([low for low, _ in boxes], axis=0), np.max([high for _, high in boxes], axis=0))
    surface = trimesh.util.concatenate(found + beside(stage, place, entry, carried,
                                                      float(fitting.world_box(stage, path)[1][1])))
    field, exact = crest_tops.height_field(surface, box), crest_tops.exact_field(surface, box)
    low_points = np.asarray(triage.low_points(own), float)
    every = np.vstack([own.vertices, own.sample(crest_tops.EVERY, seed=0)])
    low, high = fitting.world_box(stage, path)
    if crest_tops.stands(own, exact, np.zeros(3)) and crowding(stage, place, entry, carried, (low, high)) is None:
        return None
    left_out = {entry["name"], *(entry["on"].get("holder") or []), *carried.get(entry["name"], [])}
    things = stage.GetPrimAtPath(f"/{place}/Objects")
    others = [outline_of(stage, str(prim.GetPath())) for prim in (things.GetChildren() if things else [])
              if prim.GetName() not in left_out and prim.IsActive()]
    thing = (own, low_points, every, resting.weight_at(own))
    move, on_other = spot(thing, (field, exact), (low, high), box, others), None
    if move is None:
        move, on_other = stacked(stage, place, entry, thing, (low, high), carried)
    if move is None or (on_other is not None and float(np.linalg.norm(move)) < fitting.MOVE_LEAST):
        return None  # no spot holds it, or it rests on the other where it lies
    foot = fitting.foot_middle(low, high)
    fitting.moved_by(stage.GetPrimAtPath(path), foot, 1.0, foot + move)
    fitting.carry(stage, place, carried, entry["name"], move)
    moved = float(np.linalg.norm(move))
    holders = ", ".join(entry["on"].get("holder"))
    fit = fitting.laid_fit(stage, path, entry, "top", entry["on"].get("holder"), moved, 1.0,
                           f"laid {moved:.2f} m onto {holders}'s top, on the spot of it where it rests" if on_other
                           is None else f"laid {moved:.2f} m onto {on_other}'s top where it rests, no spot of "
                                        f"{holders}'s top holding it")
    return {**fit, "top at": round(float(foot[1] + move[1]), 4)}


def beside(stage, place, entry, carried, under, but=()):
    """The built surfaces (meshes) of the others laid on a thing's holders (`carried`'s) whose box tops stand under
    `under` (metres: its own top), less what rides on it, and theirs, and `but`: what it stands among and over, which
    the resting check reads under its points as it reads its holders (a taller one beside it, read from above, would
    stand over it). Judged on its
    holders alone, quarters' keyboard and books, their boxes 8 to 9 mm into each other's on its desk (fitting.BOARD_CLEAR
    lets a box 1 cm into another), and a book laid 9.5 mm deep over two 1.3 cm wrenches, rested, and leaned 5 to 16
    degrees on each other (settle@quarters, 2026-11-13)."""
    left_out = {entry["name"], *riding(entry["name"], carried), *but}
    names = [other for holder in entry["on"].get("holder") or [] for other in carried.get(holder, [])
             if other not in left_out and stage.GetPrimAtPath(f"/{place}/Objects/{other}")
             and float(fitting.world_box(stage, f"/{place}/Objects/{other}")[1][1]) < under]
    return [mesh for mesh in (fitting.surface_mesh(stage, f"/{place}/Objects/{other}") for other in dict.fromkeys(names))
            if mesh is not None]


def riding(name, carried):
    """The things riding on a thing (`carried`'s, fitting.with_stacked's), down their chain."""
    riders, todo = set(), [name]
    while todo:
        for rider in carried.get(todo.pop(), []):
            if rider not in riders:
                riders.add(rider)
                todo.append(rider)
    return riders


def crowding(stage, place, entry, carried, box_of):
    """The first other laid on a thing's holders (`carried`'s, less what rides on it) whose top stands no higher than
    its own that its box (`box_of`) reaches into (meets), else None: a thing that rests where it is laid is still laid
    again clear of them. One standing taller over it is the one laid into it, and is laid again itself (`beside` reads
    this one under it). Lab's two 0.4 m monitors (one model, a box turned 45 degrees in its frame), laid at one corner
    of its 0.92 m desk bake, their boxes 20 cm into each other and their models into each other: each rested on the
    desk alone (stands), and the resting check read each one's low points inside the other as its support and its up
    leaning 8.6 and 6.4 degrees (settle@lab, 2026-11-14)."""
    left_out = {entry["name"], *riding(entry["name"], carried)}
    for holder in entry["on"].get("holder") or []:
        for other in carried.get(holder, []):
            path = f"/{place}/Objects/{other}"
            if other in left_out or not stage.GetPrimAtPath(path) or not stage.GetPrimAtPath(path).IsActive():
                continue
            found = outline_of(stage, path)
            low, high = (np.asarray(end, float) for end in box_of)
            if float(found[1][1]) <= float(high[1]) + SAME and meets(low + SAME, high - SAME, found):
                return other
    return None


def stacked(stage, place, entry, thing, box_of, carried):
    """(the move [x, lift, z], its name) of a thing (`thing`: mesh, low points, every point, weight; `box_of` its box)
    onto the top of the nearest of the others laid on its holders (`carried`'s, less what rides on it) where it rests
    there (spot, on that one's surface within its box), clear of the rest; (None, None) with none."""
    name = entry["name"]
    riding = set(carried.get(name, []))
    names = [other for holder in entry["on"].get("holder") or [] for other in carried.get(holder, [])
             if other != name and other not in riding and stage.GetPrimAtPath(f"/{place}/Objects/{other}")]
    here = fitting.foot_middle(*box_of)
    boxes = {other: fitting.world_box(stage, f"/{place}/Objects/{other}") for other in names}
    things = stage.GetPrimAtPath(f"/{place}/Objects")
    for other in sorted(boxes, key=lambda other: float(np.linalg.norm((fitting.foot_middle(*boxes[other]) - here)[
            [0, 2]]))):
        mesh = fitting.surface_mesh(stage, f"/{place}/Objects/{other}")
        if mesh is None or mesh.area <= 0:
            continue
        import trimesh
        left_out = {name, other, *riding, *(entry["on"].get("holder") or [])}
        others = [outline_of(stage, str(prim.GetPath())) for prim in (things.GetChildren() if things else [])
                  if prim.GetName() not in left_out and prim.IsActive()]
        tall = float(box_of[1][1] - box_of[0][1])
        under = trimesh.util.concatenate([mesh, *beside(stage, place, entry, carried, float(boxes[other][1][1]) + tall,
                                                         {other})])
        fields = crest_tops.height_field(under, boxes[other]), crest_tops.exact_field(under, boxes[other])
        move = spot(thing, fields, box_of, boxes[other], others)
        if move is not None:
            return move, other
    return None, None


def spot(thing, fields, box_of, box, others):
    """The move [x, lift, z] of a thing (its mesh, low points, every point and weight; `box_of` its box) to the nearest
    spot FINE apart, its foot's middle over the holders' `box` (its footprint may reach past the box's edge, as a
    thing stands over a desk's front: what holds it is the rest's measure, its weight inside what it touches), where it
    rests on the top (crest_tops.may_rest, rest on the height field and on the surface, then stands, crest_tops.ASKED
    spots at most) and meets none of `others` (outline_of's); None with none."""
    field, exact = fields
    mesh, low_points, every, weight = thing
    low, high = (np.asarray(end, float) for end in box_of)
    hold_low, hold_high = (np.asarray(end, float) for end in box)
    foot = fitting.foot_middle(low, high)
    xs = np.arange(hold_low[0], hold_high[0] + FINE / 2, FINE)
    zs = np.arange(hold_low[2], hold_high[2] + FINE / 2, FINE)
    grid = np.stack(np.meshgrid(xs, zs, indexing="ij"), axis=-1).reshape(-1, 2)
    shifts = grid[np.argsort(np.hypot(grid[:, 0] - foot[0], grid[:, 1] - foot[2]), kind="stable")] - foot[[0, 2]]
    sieved = np.concatenate([part[crest_tops.may_rest(low_points, weight, field, part)] for part in np.array_split(
        shifts, max(1, -(-len(shifts) // crest_tops.SIEVED_AT_ONCE)))])
    asked = 0
    for shift in sieved:
        if crest_tops.rest(low_points, every, weight, field, shift) is None:
            continue
        lift = crest_tops.rest(low_points, every, weight, exact, shift)
        if lift is None:
            continue
        move = np.array([shift[0], lift, shift[1]])
        if any(meets(low + move, high + move, other) for other in others):
            continue
        if asked >= crest_tops.ASKED:
            return None
        asked += 1
        if crest_tops.stands(mesh, exact, move):
            return move
    return None


def outline_of(stage, path):
    """(low, high, outline) of another thing: its world box, and its turned floor outline [4, 2] (x, z) where it is a
    thin thing turned off the floor's axes (fitting.thin_outline), else None."""
    low, high = fitting.world_box(stage, path)
    return low, high, fitting.thin_outline(stage, path)


def meets(low, high, other):
    """Whether a box (low, high) reaches into another thing (outline_of's): by its box (fitting.reaches_into), and on
    the floor by its turned outline where it has one (the depth along each side's normal of either
    shape, the least of them, as two convex shapes overlap)."""
    other_low, other_high, outline = other
    if not fitting.reaches_into(low, high, (other_low, other_high)):
        return False
    if outline is None:
        return True
    square = np.array([[low[0], low[2]], [high[0], low[2]], [high[0], high[2]], [low[0], high[2]]])
    return overlap(square, np.asarray(outline, float)) > fitting.BOARD_CLEAR


def overlap(first, second):
    """How far two convex polygons [n, 2] reach into each other: the least, over every side's normal of either, of
    how far their spans along it overlap (negative apart)."""
    least = np.inf
    for shape in (first, second):
        sides = np.roll(shape, -1, axis=0) - shape
        for side in sides:
            length = float(np.hypot(*side))
            if length < 1e-12:
                continue
            normal = np.array([-side[1], side[0]]) / length
            one, two = first @ normal, second @ normal
            least = min(least, min(one.max(), two.max()) - max(one.min(), two.min()))
    return float(least)
