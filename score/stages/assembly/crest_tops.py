"""A thing laid on its holder's top where the top is curved, with no flat spot that holds it, laid on the spot of the
top where it rests by the resting check's measure (fitting.fitted, after built_tops.let_down): let down until no point
of it is in the top, CONTACTS of its low points touching, its weight `balance` inside them, every one of its feet down and
what it touches leaning less than the triage's LEAN_MOST by LEAN_SPARE, measured with the triage's own functions on
the thing as the make lays it (its feet levelled by even_feet, which runs after the fitting).

assembly@old_station, 2026-11-12: its sandbags on the left and right modules (horizontal cylinders 3.5 m across) and on
the central hub (a domed roof, flat 2 m across at its middle) were laid at their holder's box corners, where the plan
drew them off their holders, and let_down found no spot whose inner half stands flat within 3 cm (a 1.2 m pile across
a cylinder's crest touches along its middle): they floated 0.06 to 1.03 m over the curve. Each now lies on the nearest
spot of its holder's top where it rests.

    rest(low, every, weight, field, shift)   how far a thing is lifted to stand on its holder's top moved by `shift`
                                             (its low points and weight read on a height field), or None where it
                                             cannot rest there: the quick sieve
    stands(mesh, exact, move)                whether the thing moved by `move` rests on the surface by the triage's own
                                             measure (low points, feet, lean)
    laid_on(stage, place, entries)           each thing on its holders' top (`entries`, built_tops.held_on's) that
                                             does not rest where let_down left it laid on the nearest spot where it
                                             rests, clear of every other thing laid (but its holders and what it
                                             carries); the fits [{name, how, ..., a top one's "top at"}]
"""
import pathlib
import sys

import numpy as np

from score.stages.assembly import fitting

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tools/usd"))

# The height field of a holder's top is read this many metres apart, and the spots a thing is tried at as many.
PITCH = 0.025
STEP = 0.025
# The resting triage's support rule: at least this many points touch (SceneEval's four).
CONTACTS = 4
# How far, degrees, what a thing touches leans less than the triage's LEAN_MOST where it is laid.
LEAN_SPARE = 0.5
# How far, metres, a thing is laid clear over its holder's surface where it is nearest: no part of it in the top.
CLEAR = 0.005
# How many points of a thing's surface beside its vertices keep it out of the top, and how many spots the sieve
# passes are asked again of the surface by the triage's measure at most.
EVERY = 4000
ASKED = 200
# How many spots the sieve's first pass (may_rest) reads at once: small enough that its arrays stay in the cache.
SIEVED_AT_ONCE = 1000
# How far, metres, the sieve's first pass (may_rest) lets a spot through short of BALANCE: its sums' rounding.
SLACK = 1e-9


def rest(low, every, weight, field, shift):
    """How far the thing (its `low` points, triage.low_points', and `every` point of it) is lifted to stand on the
    holder's top (`field`: spots [n, 2] -> heights) once moved by `shift` [x, z], CLEAR over it where nearest, when
    there CONTACTS low points or more touch (within TOLERANCE), its `weight` [x, z] stands `balance` inside them and the
    surface under them slopes less than LEAN_MOST; else None."""
    import triage
    from score.stages.assembly import footing
    spots = low[:, [0, 2]] + shift
    tops = field(spots)
    if not np.isfinite(tops).any():
        return None
    lift = float(np.nanmax(np.concatenate([tops - low[:, 1], field(every[:, [0, 2]] + shift) - every[:, 1]]))) + CLEAR
    gaps = np.where(np.isfinite(tops), low[:, 1] + lift - tops, np.inf)
    touching = gaps <= triage.TOLERANCE
    if touching.sum() < CONTACTS:
        return None
    if footing.inside_by(np.asarray(weight, float) + shift, spots[touching]) < balance(every):
        return None
    return lift if slope(spots[touching], tops[touching]) < triage.LEAN_MOST else None


def may_rest(low, weight, field, shifts):
    """Whether the thing (its `low` points, its `weight` [x, z]) may rest on the holder's top (`field`) moved by each
    of `shifts` [n, 2]: lifted by its low points alone, CONTACTS of them touch and its weight stands `balance` (of its
    low points: never more than rest's, of every point) inside the box around them. rest lifts it by every point of it,
    never less, and more lift touches fewer; the hull of what
    then touches lies within that box. So a shift false here is one rest finds None at (SLACK takes the sums' last
    digits): base's hangar_roof_opening_1 was asked of rest at 1.5 million spots on the hangar's roof, 3 hours."""
    import triage
    tops = field((low[None, :, [0, 2]] + shifts[:, None, :]).reshape(-1, 2)).reshape(len(shifts), len(low))
    found = np.isfinite(tops)
    lift = np.max(np.where(found, tops - low[:, 1], -np.inf), axis=1) + CLEAR
    touching = found & (low[:, 1] + lift[:, None] - tops <= triage.TOLERANCE)
    enough = touching.sum(axis=1) >= CONTACTS
    weights, inside = np.asarray(weight, float) + shifts, balance(low)
    for axis, column in ((0, 0), (1, 2)):
        least = np.min(np.where(touching, low[:, column], np.inf), axis=1) + shifts[:, axis]
        most = np.max(np.where(touching, low[:, column], -np.inf), axis=1) + shifts[:, axis]
        enough &= (weights[:, axis] - least >= inside - SLACK) & (most - weights[:, axis] >= inside - SLACK)
    return enough


def balance(points):
    """How far, metres, a thing's weight stands inside what it touches to rest there (rest, may_rest, stands): the
    triage's BALANCE, or a quarter of the narrower side of its box across (its points [n, 3]) where that is less. No
    point of a 6 cm mouse is 5 cm inside it: quarters' mouse, a 5 cm wrench and a plant pot were never found a spot of
    their desk where they rest, and were left leaning 3.5 to 3.7 degrees (settle@quarters, 2026-11-13)."""
    import triage
    return min(triage.BALANCE, float(np.ptp(np.asarray(points, float)[:, [0, 2]], axis=0).min()) / 4)


def stands(mesh, exact, move, turn=np.eye(4)):
    """Whether the thing (`mesh`) moved by `move` [x, lift, z] rests on the holders' surface (`exact`: spots [n, 2] ->
    heights) by the triage's own measure: CONTACTS of its low points within TOLERANCE, its weight `balance` inside them,
    every foot down (triage.feet_gaps) and what it touches leaning LEAN_SPARE less than LEAN_MOST (triage.lean) from
    its up (`turn`'s, 4 x 4: upright where none is given; flush_tops lays one turned)."""
    import resting
    import triage
    from score.stages.assembly import footing
    moved = mesh.copy()
    moved.apply_translation(move)

    def gaps_of(points):
        tops = exact(points[:, [0, 2]])
        return np.where(np.isfinite(tops), points[:, 1] - tops, np.inf)  # under a top it is in, as the check reads it
    low = np.asarray(triage.low_points(moved), float)
    gaps = gaps_of(low)
    touching = gaps <= triage.TOLERANCE
    if touching.sum() < CONTACTS or footing.inside_by(resting.weight_at(moved), low[touching][:, [0, 2]]) < \
            balance(moved.vertices):
        return False
    if any(gap > triage.TOLERANCE for _, gap in triage.feet_gaps(moved, gaps_of)):
        return False
    return triage.lean(turn, low[touching], gaps[touching]) <= triage.LEAN_MOST - LEAN_SPARE


def slope(spots, heights):
    """Degrees the plane through the points (spots [n, 2], their heights) slopes; 0 where they span no plane."""
    if len(spots) < 3 or np.linalg.matrix_rank(spots - spots.mean(axis=0), tol=0.01) < 2:
        return 0.0
    across, along, _ = np.linalg.lstsq(np.c_[spots, np.ones(len(spots))], heights, rcond=None)[0]
    return float(np.degrees(np.arctan(np.hypot(across, along))))


def laid_on(stage, place, entries):
    """Each thing on its holders' curved top laid where it rests (module docstring), a holder before what it holds,
    carrying what is laid on its own top; the fits."""
    by_name = {entry["name"]: entry for entry in entries}
    carried = {}
    for entry in entries:
        for holder in entry["on"].get("holder") or []:
            carried.setdefault(holder, []).append(entry["name"])
    fits = []
    for name in ordered(by_name):
        fit = one(stage, place, by_name[name], fitting.with_stacked(stage, place, carried, list(by_name)))
        if fit is not None:
            fits.append(fit)
    return fits


def ordered(by_name):
    """The names, each holder among them before what it holds."""
    found = []

    def visit(name, seen=()):
        if name in found or name in seen:
            return
        for holder in by_name[name]["on"].get("holder") or []:
            if holder in by_name:
                visit(holder, (*seen, name))
        found.append(name)
    for name in by_name:
        visit(name)
    return found


def one(stage, place, entry, carried):
    """One thing laid on the spot of its holders' top where it rests, when it does not rest where it is; its fit, or
    None when it rests there, stands within its holder at its foot, or no spot holds it."""
    import resting
    import triage
    import trimesh
    scope = entry["on"].get("holder scope", "Objects")
    holders = [f"/{place}/{scope}/{holder}" for holder in entry["on"].get("holder") or []
               if stage.GetPrimAtPath(f"/{place}/{scope}/{holder}")]
    found = [mesh for mesh in (fitting.surface_mesh(stage, path) for path in holders) if mesh is not None]
    path = f"/{place}/Objects/{entry['name']}"
    own = as_levelled(stage.GetPrimAtPath(path), fitting.surface_mesh(stage, path))
    if not found or own is None or own.area <= 0:
        return None
    boxes = [fitting.world_box(stage, path) for path in holders]
    box = (np.min([low for low, _ in boxes], axis=0), np.max([high for _, high in boxes], axis=0))
    low, high = fitting.world_box(stage, path)
    within = entry["on"]["how"] == "within"
    if within and float(low[1]) <= float(box[0][1]) + fitting.BOARD_BED:
        return None  # at its holder's foot: on the floor it stands in, as let_down leaves it
    surface = trimesh.util.concatenate(found)
    field, exact = height_field(surface, box), exact_field(surface, box)
    low_points = np.asarray(triage.low_points(own), float)
    every = np.vstack([own.vertices, own.sample(EVERY, seed=0)])
    here = rest(low_points, every, resting.weight_at(own), exact, np.zeros(2))
    if here is not None and abs(here - CLEAR) <= fitting.MOVE_LEAST and stands(own, exact, np.array([0.0, here, 0.0])):
        return None
    left_out = {entry["name"], *(entry["on"].get("holder") or []), *carried.get(entry["name"], [])}
    things = stage.GetPrimAtPath(f"/{place}/Objects")
    others = [fitting.world_box(stage, str(prim.GetPath())) for prim in (things.GetChildren() if things else [])
              if prim.GetName() not in left_out]
    top = float(box[1][1]) if within else None  # the held gate measures a thing within its holder off its box top
    laid = spot((own, low_points, every), (field, exact), (low, high), box, others, top)
    if laid is None:
        return None
    foot = fitting.foot_middle(low, high)
    target = foot + laid
    fitting.moved_by(stage.GetPrimAtPath(path), foot, 1.0, target)
    fitting.carry(stage, place, carried, entry["name"], laid)
    moved = float(np.linalg.norm(laid))
    holder_words = ", ".join(entry["on"].get("holder"))
    fit = fitting.laid_fit(stage, path, entry, entry["on"]["how"], entry["on"].get("holder"), moved, 1.0,
                           f"laid {moved:.2f} m onto {holder_words}'s curved top, where it rests")
    return fit if within else {**fit, "top at": round(float(target[1]), 4)}


def height_field(mesh, box):
    """A reader of the holders' top: spots [n, 2] -> the height of the first surface a ray straight down meets
    there (nan where none, or off the holders' box), read PITCH apart over the holders' `box`, each spot's nearest."""
    low, high = (np.asarray(end, float) for end in box)
    xs = np.arange(low[0], high[0] + PITCH / 2, PITCH)
    zs = np.arange(low[2], high[2] + PITCH / 2, PITCH)
    grid = np.array([(x, z) for x in xs for z in zs], float)
    origins = np.c_[grid[:, 0], np.full(len(grid), high[1] + 1.0), grid[:, 1]]
    tops = np.full(len(grid), np.nan)
    hits, rays, _ = mesh.ray.intersects_location(origins, np.tile([0.0, -1.0, 0.0], (len(origins), 1)),
                                                 multiple_hits=False)
    tops[rays] = hits[:, 1]
    field = tops.reshape(len(xs), len(zs))

    def read(spots):
        spots = np.asarray(spots, float)
        across = np.rint((spots[:, 0] - low[0]) / PITCH).astype(int)
        along = np.rint((spots[:, 1] - low[2]) / PITCH).astype(int)
        inside = (across >= 0) & (across < len(xs)) & (along >= 0) & (along < len(zs))
        found = np.full(len(spots), np.nan)
        found[inside] = field[across[inside], along[inside]]
        return found
    return read


def as_levelled(prim, mesh):
    """The thing's mesh as the make lays it after the fitting: a floor thing's feet brought down (even_feet, which
    levels its own asset after the fitting): a pile on two feet, one 4 cm up, rests on both once laid."""
    from score.stages.assembly import even_feet
    if mesh is None or not even_feet.floor_thing(prim):
        return mesh
    levelled = mesh.copy()
    levelled.vertices = even_feet.level_feet(np.asarray(mesh.vertices), np.asarray(mesh.faces))[0]
    return levelled


def exact_field(mesh, box):
    """A reader of the holders' top: spots [n, 2] -> the height of the first surface a ray straight down from over
    the holders' `box` meets there, nan where none."""
    over = float(np.asarray(box[1], float)[1]) + 1.0

    def read(spots):
        spots = np.asarray(spots, float)
        origins = np.c_[spots[:, 0], np.full(len(spots), over), spots[:, 1]]
        found = np.full(len(spots), np.nan)
        hits, rays, _ = mesh.ray.intersects_location(origins, np.tile([0.0, -1.0, 0.0], (len(origins), 1)),
                                                     multiple_hits=False)
        found[rays] = hits[:, 1]
        return found
    return read


def spot(thing, fields, box_of, box, others, top=None):
    """The move [x, lift, z] of a thing (`thing`: its mesh, low points and every point; `box_of` its box low, high) to
    the nearest spot (STEP apart, its footprint kept within the holders' `box`) where it rests on the top (rest on the
    height field, its lift then read off the surface itself and stands asked, ASKED spots at most: `fields`) clear of
    the `others` boxes, its foot within HELD_MOST of `top` when given; None with none."""
    import resting
    field, exact = fields
    mesh, low_points, every = thing
    weight = resting.weight_at(mesh)
    low, high = (np.asarray(end, float) for end in box_of)
    hold_low, hold_high = (np.asarray(end, float) for end in box)
    half = (high - low) / 2
    foot = fitting.foot_middle(low, high)
    xs = np.unique([fitting.kept_within(x, hold_low[0], hold_high[0], half[0])
                    for x in np.arange(hold_low[0], hold_high[0] + STEP / 2, STEP)])
    zs = np.unique([fitting.kept_within(z, hold_low[2], hold_high[2], half[2])
                    for z in np.arange(hold_low[2], hold_high[2] + STEP / 2, STEP)])
    grid = np.stack(np.meshgrid(xs, zs, indexing="ij"), axis=-1).reshape(-1, 2)
    tries = grid[np.argsort(np.hypot(grid[:, 0] - foot[0], grid[:, 1] - foot[2]), kind="stable")]
    shifts = tries - foot[[0, 2]]
    sieved = np.concatenate([part[may_rest(low_points, weight, field, part)] for part in np.array_split(
        shifts, max(1, -(-len(shifts) // SIEVED_AT_ONCE)))])
    asked = 0
    for shift in sieved:
        if rest(low_points, every, weight, field, shift) is None:
            continue
        lift = rest(low_points, every, weight, exact, shift)
        if lift is None or (top is not None and abs(float(low[1]) + lift - top) > fitting.HELD_MOST):
            continue
        move = np.array([shift[0], lift, shift[1]])
        if fitting.meets_any(low + move, high + move, others):
            continue
        if asked >= ASKED:
            return None
        asked += 1
        if stands(mesh, exact, move):
            return move
    return None
