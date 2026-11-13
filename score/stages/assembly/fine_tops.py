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

    FINE                          metres apart the spots are read
    meets(low, high, other)       whether a box reaches into another thing's box or turned outline
    laid(stage, place, entries)   each thing on its holders' top (`entries`, built_tops.held_on's) that does not rest
                                  where it is laid on the nearest spot where it rests; the fits [{..., "top at"}]
"""
import numpy as np

from score.stages.assembly import crest_tops, fitting

# How far apart, metres, the spots of a holder's top a thing is tried at are read, each way.
FINE = 0.005


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
        fit = one(stage, place, by_name[name], carried)
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
    surface = trimesh.util.concatenate(found)
    field, exact = crest_tops.height_field(surface, box), crest_tops.exact_field(surface, box)
    if crest_tops.stands(own, exact, np.zeros(3)):
        return None
    left_out = {entry["name"], *(entry["on"].get("holder") or []), *carried.get(entry["name"], [])}
    things = stage.GetPrimAtPath(f"/{place}/Objects")
    others = [outline_of(stage, str(prim.GetPath())) for prim in (things.GetChildren() if things else [])
              if prim.GetName() not in left_out and prim.IsActive()]
    low_points = np.asarray(triage.low_points(own), float)
    every = np.vstack([own.vertices, own.sample(crest_tops.EVERY, seed=0)])
    low, high = fitting.world_box(stage, path)
    move = spot((own, low_points, every, resting.weight_at(own)), (field, exact), (low, high), box, others)
    if move is None:
        return None
    foot = fitting.foot_middle(low, high)
    fitting.moved_by(stage.GetPrimAtPath(path), foot, 1.0, foot + move)
    fitting.carry(stage, place, carried, entry["name"], move)
    moved = float(np.linalg.norm(move))
    fit = fitting.laid_fit(stage, path, entry, "top", entry["on"].get("holder"), moved, 1.0,
                           f"laid {moved:.2f} m onto {', '.join(entry['on'].get('holder'))}'s top, on the spot "
                           f"of it where it rests")
    return {**fit, "top at": round(float(foot[1] + move[1]), 4)}


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
    """Whether a box (low, high) reaches into another thing (outline_of's) by more than fitting.BOARD_CLEAR every way:
    by its box, and on the floor by its turned outline where it has one (the depth along each side's normal of either
    shape, the least of them, as two convex shapes overlap)."""
    other_low, other_high, outline = other
    if float(fitting.depths(low, high, (other_low, other_high)).min()) <= fitting.BOARD_CLEAR:
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
