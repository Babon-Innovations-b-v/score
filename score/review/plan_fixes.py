"""The free fixes of his edit's plan or a redrawing's (plans.edit_inside), made where it is shown, never stored over
his edit: what it lays past its own outline brought inside it (`kept_inside`), each doorway its door row's width
(`doors_sized`) and as big as the door standing in it (`doorways_fit`), and nothing laid in a wall, the stairs or its
own row's (`kept_apart`). The plan writing these fixes once also served went with the per-picture chain (#128); these
stayed out of it for two days and the kept plans of every edited place moved with them (the hangar's two person spots
past its 32 x 64 m and the walkway's ceiling light and wall pipes past its 1.5 x 12 m, so plan@hangar and @walkway
failed `held` on 2026-11-22, #156)."""
import math
import re

import numpy

from score.review import holders, plan_checks, standing
from score.stages.earth_seed import design_shell


NUDGE_ROUNDS = 4  # passes over the overlaps, each moving the smaller thing of a pair


MARGIN = 0.05  # metres left between two things nudged apart


RUN_SHARE = 3  # a thing on a wall this many times longer than it is deep is a run (a pipe), cut at a corner


FLIGHT_REACH = 3.0  # metres a stair or ramp is moved out of a thing made larger than drawn at most


FACINGS = ("N", "E", "S", "W")


def item_name(plan, row):
    """The next free plan item name of `row` ("ROCKET ENGINE 2")."""
    stem, taken = row.replace("_", " ").upper(), {item[0] for item in plan["items"]}
    return next(f"{stem} {number}" for number in range(1, 10_000) if f"{stem} {number}" not in taken)


def dropped_item(plan, item):
    """Take `item` off the plan, with its rows and shape."""
    plan["items"].remove(item)
    plan.get("rows", {}).pop(item[0], None)
    plan.get("shapes", {}).pop(item[0], None)


def added_item(plan, row, spot, size, like=None):
    """Put one thing of `row` on the plan, its middle at `spot`, `size` [wide, deep] metres, its shape like `like`'s
    (count 1); its name."""
    name = item_name(plan, row)
    plan["items"].append([name, round(spot[0] - size[0] / 2, 3), round(spot[1] - size[1] / 2, 3), round(size[0], 3),
                          round(size[1], 3), None, "item"])
    plan.setdefault("rows", {})[name] = [row]
    plan.setdefault("shapes", {})[name] = {key: value for key, value in (like or {"shape": "rect"}).items()
                                           if key != "count"}
    return name


# A row's words that say its things pile on one another (holders.PILE_WORDS, held equal by the test).
PILE_WORDS = {"pile", "piles", "piled", "stack", "stacks", "stacked", "heap", "heaps", "heaped"}


def piles(row):
    """Whether a row's things pile on one another: a PILE_WORDS word in its id, name, noun, where or size words."""
    return bool(PILE_WORDS & set(re.findall(r"[a-z]+", " ".join(
        str(row.get(key) or "") for key in ("id", "name", "noun", "where", "size_words")).replace("_", " ").lower())))


def overlapping(box, other):
    """Whether two boxes [x, y, w, d] share any floor."""
    return box[0] < other[0] + other[2] and other[0] < box[0] + box[2] and box[1] < other[1] + other[3] \
        and other[1] < box[1] + box[3]


def walls_and_stairs(plan):
    """[x, y, w, d] of each straight wall the plan draws along an axis and of each stair or ramp's footprint: what no
    run is laid through and nothing is nudged into (settle@airlock, checkout 67: a run of sandbags through its east
    wall, another into its entrance ramp's stairs)."""
    found = []
    for wall in plan.get("walls") or []:
        if "arc" in wall or not wall.get("from") or not wall.get("to"):
            continue
        (x1, y1), (x2, y2) = wall["from"], wall["to"]
        if abs(x2 - x1) > 1e-3 and abs(y2 - y1) > 1e-3:
            continue
        corners = numpy.asarray(plan_checks.wall_polygon(wall), float)
        found.append([*corners.min(axis=0).tolist(), *numpy.ptp(corners, axis=0).tolist()])
    for stair in plan.get("stairs") or []:
        corners = numpy.asarray(stair.get("points") or [], float).reshape(-1, 2)
        if len(corners) >= 3:
            found.append([*corners.min(axis=0).tolist(), *numpy.ptp(corners, axis=0).tolist()])
    return found


def standing_low(plan, inventory, mover):
    """[x, y, w, d] of every thing whose shape stands it low on the floor though no floor holds it (a suit hung on the
    back wall stands on the floor in front of it: plan_checks.blocking reads only floor anchors, so the airlock's
    sandbags were nudged into its empty suit, checkout 67), but `mover` and what stands on it; a thing with no base
    written (a ceiling lamp the fixes placed) and the place's own shell (a wall, floor or ceiling row,
    holders.holder_kind: the engine room's wall panels, laid as the whole room's box) are left out."""
    anchored, left_out = plan_checks.anchors(inventory), plan_checks.people(inventory) | plan_checks.afar(inventory)
    left_out |= {row["id"] for row in inventory.get("rows", []) if holders.holder_kind(row) is not None}
    mover_row = (plan.get("rows", {}).get(mover[0]) or [None])[0]
    return [item[1:5] for item, row, shape in plan_checks.placed_items(plan)
            if item[0] != mover[0] and row not in left_out and anchored.get(row) != f"on:{mover_row}"
            and "base" in (shape or {}) and float(shape["base"] or 0.0) < plan_checks.LOW
            and float(shape.get("tall") or 1.0) > plan_checks.FLAT]


def trimmed(box, blocker, along):
    """`box` [x, y, w, d] cut along its long axis (`along`: 0 for x, 1 for y) to the longer part on either side of
    `blocker`, MARGIN off it; None when no part is left."""
    start, end = box[along], box[along] + box[2 + along]
    low, high = blocker[along] - MARGIN, blocker[along] + blocker[2 + along] + MARGIN
    first, second = (start, min(end, low)), (max(start, high), end)
    keep = max(first, second, key=lambda part: part[1] - part[0])
    if keep[1] - keep[0] <= 0:
        return None
    cut = list(box)
    cut[along], cut[2 + along] = keep[0], keep[1] - keep[0]
    return cut


def shifted(box, blocker, along):
    """`box` moved across its long axis the shortest way out of `blocker`, MARGIN off it."""
    across = 1 - along
    steps = [blocker[across] + blocker[2 + across] + MARGIN - box[across],
             blocker[across] - MARGIN - box[across] - box[2 + across]]
    moved = list(box)
    moved[across] += min(steps, key=abs)
    return moved


def runs_kept_clear(plan, inventory):
    """Each run on the floor (a counted box of several floor things, plan_checks.blocking, laid along its long side)
    kept out of the walls and stairs: one a wall or stair crosses cut to its longer part on one side, its count cut
    with its length, the pieces it lays said in the plan's `dropped` (`count_said`: no later pass lays the cut ones
    again as missing); one a wall or stair only runs along moved off it across; the fixes said. A run held by a wall
    (pipes along it) is left on it."""
    blockers, fixes, cut = walls_and_stairs(plan), [], {}
    for item, row, shape in plan_checks.blocking(plan, inventory):
        count = int((shape or {}).get("count") or 1)
        if count < 2:
            continue
        box, along = list(item[1:5]), 0 if item[3] >= item[4] else 1
        for _ in range(NUDGE_ROUNDS):
            blocker = next((other for other in blockers if overlapping(box, other)), None)
            if blocker is None:
                break
            across = 1 - along
            crosses = blocker[across] <= box[across] and \
                blocker[across] + blocker[2 + across] >= box[across] + box[2 + across]
            box = trimmed(box, blocker, along) if crosses else shifted(box, blocker, along)
            if box is None:
                break
        if box is None or box == list(item[1:5]):
            continue
        kept = max(1, round(count * box[2 + along] / item[3 + along]))
        item[1:5] = [round(value, 3) for value in box]
        shape["count"] = kept
        cut[row] = cut.get(row, 0) + count - kept
        fixes.append(f"{plan_checks.said_name(item[0])}: kept out of the walls and stairs, {kept} of {count} things")
    for row, fewer in cut.items():
        if fewer:
            count_said(plan, row, f"{fewer} fewer of it laid, its runs cut clear of the walls and stairs")
    return fixes


def run_doubles_dropped(plan, inventory):
    """Each single thing on the floor (plan_checks.blocking) standing in a run of its own row (a counted box of
    several) at the run's base, more than plan_checks.OVERLAP of it, taken off: the run lays its own pieces there, so
    it is one of them laid twice; each row's in the plan's `dropped` with the count it lays (`count_said`); the fixes
    said, one a row. settle@airlock, 2026-11-09: runs_kept_clear cut sandbags 1 to 3 from 10, 6 and 5 to 8, 5 and 3
    clear of the walls and stairs, said nowhere, so the next pass's placed_missing laid the five back as sandbags 5 to
    9 where the cut took them off, in sandbags 1 and past the west wall."""
    floor = plan_checks.blocking(plan, inventory)
    runs = [(item, row, shape) for item, row, shape in floor if int((shape or {}).get("count") or 1) > 1]
    doubles = {}
    for item, row, shape in floor:
        if int((shape or {}).get("count") or 1) > 1:
            continue
        base = float((shape or {}).get("base") or 0.0)
        if any(run_row == row and abs(float((run_shape or {}).get("base") or 0.0) - base) < 1e-3
               and shared(item[1:5], run[1:5]) > plan_checks.OVERLAP * item[3] * item[4]
               for run, run_row, run_shape in runs):
            doubles.setdefault(row, []).append(item)
    fixes = []
    for row, items in doubles.items():
        for item in items:
            dropped_item(plan, item)
        why = count_said(plan, row, f"{len(items)} laid again in its own row's run, which lays its pieces there")
        fixes.append(f"{plan_checks.said_name(row)}: {', '.join(plan_checks.said_name(item[0]) for item in items)} "
                     f"taken off, {why}")
    return fixes


def shared(box, other):
    """The floor (square metres) two boxes [x, y, w, d] share."""
    wide = min(box[0] + box[2], other[0] + other[2]) - max(box[0], other[0])
    deep = min(box[1] + box[3], other[1] + other[3]) - max(box[1], other[1])
    return max(wide, 0.0) * max(deep, 0.0)


def floored(plan, inventory):
    """The inventory with each row standing on a row that is a floor (holders.holder_kind: the engine room's floor
    grating) read as on the floor: its railings, engines and core stand on the floor as flat's stove does. A floor,
    wall or ceiling row itself is left on its holder."""
    rows = inventory.get("rows", [])
    floors = {row["id"] for row in rows if holders.holder_kind(row) == "floor"}
    return {**inventory, "rows": [dict(row, anchor="floor") if plan_checks.anchor_of(row) in floors
                                  and holders.holder_kind(row) is None else row for row in rows]}


def piled_on_own(plan, inventory):
    """[(item, the base it stands at on the floor)] of each thing standing on the floor (`floored`) of a row that does
    not pile (piles) laid over one of
    its own row's things whose footprint it crosses: a pile made before plan_fixes.piled asked the row's words
    (2026-11-06), flat's second stove 0.9 m up on its first, the engine room's railings 5 to 8 at 1 to 4 m (env1
    checkout 68: settle@flat, "stove_1 and stove_2 came to rest inside each other")."""
    rows, found = {row["id"]: row for row in inventory.get("rows", [])}, []
    on_floor, laid = plan_checks.anchors(floored(plan, inventory)), plan_checks.placed_items(plan)
    for item, row, shape in laid:
        base = float((shape or {}).get("base") or 0.0)
        if row not in rows or piles(rows[row]) or base <= 0.0 or on_floor[row] not in plan_checks.FLOOR_ANCHORS:
            continue
        under = [float((other_shape or {}).get("base") or 0.0) for other, other_row, other_shape in laid
                 if other is not item and other_row == row and overlapping(item[1:5], other[1:5])
                 and float((other_shape or {}).get("base") or 0.0) < base]
        if under and min(under) < plan_checks.LOW:  # its own row's stand on the floor: not strings overhead
            found.append((item, min(under)))
    return found


def ramp_footprint(item, row, plan):
    """The footprint polygon of a ramp row's `item` where the holders lay it (holders.up_to_level: its long side run
    straight up to a raised level's nearest edge, however far that is from its item), else None."""
    relation = holders.up_to_level(item, row, plan) if row else None
    if relation is None:
        return None
    size = row["size"] if isinstance(row.get("size"), list) and len(row["size"]) == 3 else item[3:5]
    length, wide = max(float(size[0]), float(size[1])), min(float(size[0]), float(size[1]))
    way = numpy.asarray(relation["way"], float)
    across, spot = numpy.array([-way[1], way[0]]), numpy.asarray(relation["spot"], float)
    return [(spot + way * ends * length / 2 + across * side * wide / 2).tolist()
            for ends, side in ((-1, -1), (1, -1), (1, 1), (-1, 1))]


def laid_polygon(item, row, shape, plan, inventory):
    """The footprint polygon of a floor thing where the scene record lays it: a ramp's where the holders run it up
    (`ramp_footprint`), any other's as drawn."""
    found = next((entry for entry in inventory.get("rows", []) if entry["id"] == row), None)
    return ramp_footprint(item, found, plan) or plan_checks.polygon_of(item, shape)


def taken_floor(plan, inventory, item, grid):
    """The grid cells `item` may not stand on: under another floor thing (on the floor, or on a floor the place lays:
    `floored`) where it is laid (`laid_polygon`), a wall, a stair or a thing standing low by a wall
    (`standing_low`)."""
    on_floor = floored(plan, inventory)
    taken = numpy.zeros(grid.shape, dtype=bool)
    for other, row, shape in plan_checks.blocking(plan, on_floor):
        if other is not item:
            taken |= grid.covered(laid_polygon(other, row, shape, plan, on_floor))
    for box in walls_and_stairs(plan) + standing_low(plan, on_floor, item):
        taken |= standing.under(grid, [box[0] + box[2] / 2, box[1] + box[3] / 2], box[2:4])
    return taken


def freed(plan, inventory, item, grid, outline):
    """`item` moved to the nearest floor inside the outline (`outline`'s cells) where it stands in nothing
    (`taken_floor`), MARGIN clear (standing.nearest_free, its footprint for a person's); how far, 0.0 where it stands in
    nothing already, None (and left where it is) when there is no such floor."""
    middle = [item[1] + item[3] / 2, item[2] + item[4] / 2]
    taken = taken_floor(plan, inventory, item, grid)
    if not (taken & standing.under(grid, middle, item[3:5])).any():
        return 0.0
    size = [side + 2 * (MARGIN + grid.size) for side in item[3:5]]  # MARGIN clear, whatever cell it lands in
    free = standing.nearest_free(middle, size, taken, grid, outline, [])
    if free is None:
        return None
    item[1], item[2] = round(free[0] - item[3] / 2, 3), round(free[1] - item[4] / 2, 3)
    return math.dist(middle, free)


def unpiled(plan, inventory):
    """Each thing piled on its own row's though its row does not pile (`piled_on_own`) stood at its own row's base and
    moved clear of what it then stands in (`freed`); one with no free floor is more of its row than the place holds,
    taken off the plan (`surplus_dropped`: the engine room's railings 5 to 8, 3.5 x 2 m each, piled 1 to 4 m on one
    spot, have none, 2026-11-09); the fixes said."""
    fixes, grid, surplus = [], plan_checks.Grid(plan), []
    outline = grid.covered(plan_checks.outline_of(plan))
    for item, base in piled_on_own(plan, inventory):
        shape = plan["shapes"][item[0]]
        shape["base"] = round(base, 3)
        moved = freed(plan, inventory, item, grid, outline)
        if moved is None:
            surplus.append(item)
            continue
        fixes.append(f"{plan_checks.said_name(item[0])}: stood on the floor, not piled on its own row's"
                     + (f", moved {moved:.1f} m out of what it stood in" if moved else ""))
    return fixes + surplus_dropped(plan, inventory, surplus)


def surplus_dropped(plan, inventory, surplus, room="the place's free floor", size=None, why=None):
    """The things of `surplus` (items no free floor of the place holds, or what `room` names) taken off the plan, each
    row's in the plan's `dropped` with its reason (`why`, else that it is more than `room` holds, `size` the words of
    one as made, else its drawn box) and the number it lays, so its count is no gap, no fix places them again
    (plan_checks.count_gaps) and the scene record lays no more (scene_record/writer.counted); what the plan places on
    or in them taken off too (`resting_dropped`); the fixes said, one a row."""
    fixes, by_row = [], {}
    resting = [thing for item in surplus for thing in resting_on(plan, inventory, item) if thing not in surplus]
    for item in surplus:
        by_row.setdefault((plan.get("rows", {}).get(item[0]) or [None])[0], []).append(item)
    for row, items in by_row.items():
        for item in items:
            dropped_item(plan, item)
        said = size or f"{items[0][3]:g} x {items[0][4]:g} m"
        words = count_said(plan, row, why or f"{len(items)} more of it than {room} holds ({said} each)")
        fixes.append(f"{plan_checks.said_name(row)}: {', '.join(plan_checks.said_name(item[0]) for item in items)} "
                     f"taken off, {words}")
    return fixes + resting_dropped(plan, inventory, resting)


def resting_on(plan, inventory, item):
    """[thing] of the plan's things it places on or in `item`: of a row its reading stands on `item`'s row (`on:<row>`),
    their middle within `item`'s footprint (greenhouse's plants 2 on its planter bed 2)."""
    held_on, holder = {row["id"]: plan_checks.anchor_of(row) for row in inventory.get("rows", [])}, \
        (plan.get("rows", {}).get(item[0]) or [None])[0]
    footprint = plan_checks.polygon_of(item, plan.get("shapes", {}).get(item[0]))
    return [thing for thing, row, _ in plan_checks.placed_items(plan) if thing is not item
            and holder is not None and held_on.get(row) == holder
            and plan_checks.inside(numpy.array([[thing[1] + thing[3] / 2, thing[2] + thing[4] / 2]]), footprint).all()]


def resting_dropped(plan, inventory, resting):
    """The things of `resting` (on or in a thing taken off) taken off too (surplus_dropped, said in `dropped`: its
    holder was dropped), but a row's last, left as laid: the plan cannot stand one thing of a row on the floor while
    its row's reading stands it on its holder (holders.held ties it to the nearest one left). Without it greenhouse's
    plants 2 stood 0.5 m up where its planter bed 2 went off its flights' feet (2026-11-09)."""
    surplus = []
    for thing in resting:
        row = (plan.get("rows", {}).get(thing[0]) or [None])[0]
        if thing in plan["items"] and laid_of(plan, row) - sum(
                1 for other in surplus if plan["rows"][other[0]][0] == row) > 1:
            surplus.append(thing)
    return surplus_dropped(plan, inventory, surplus, why="its holder was dropped") if surplus else []


def laid_of(plan, row):
    """How many pieces of `row` the plan lays: each item tied to it its shape's `count` (as plan_checks.count_gaps
    counts them)."""
    return sum(int((plan.get("shapes", {}).get(item[0]) or {}).get("count") or 1) for item in plan.get("items", [])
               if item[6] == "item" and row in (plan.get("rows", {}).get(item[0]) or []))


def count_said(plan, row, why):
    """`why` a fix lays fewer of `row` than before, said in the plan's `dropped` with the pieces it lays now
    (`laid_of`), so its count is no gap, no fix places the rest again (plan_checks.count_gaps) and the scene record
    lays no more (scene_record/writer.counted); the words said."""
    laid = laid_of(plan, row)
    said = f"{why}: {laid} laid"
    plan.setdefault("dropped", []).append({"item": row, "why": said, "laid": laid})
    return said


def wall_runs_parted(plan, inventory):
    """Each run (RUN_SHARE) held on a wall (holders.wall_held) whose end runs into another of its row at the same
    height, reaching past that end (a piece on the next wall at the corner), cut back off it along its long side,
    MARGIN off (`trimmed`), its count cut with its length as runs_kept_clear cuts (and said, `count_said`), while it
    keeps at least half its length; the fixes said. The holders part one wall's pieces, never two walls' at their
    corner: the engine room's pipe 1 along its north wall ran into its corner pipes 2 and 3 (env1 checkout 68:
    settle@engineroom, pipe_1 and pipe_2 inside each other by 0.072 m)."""
    rows = {row["id"]: row for row in inventory.get("rows", [])}
    held = [(item, row, shape) for item, row, shape in plan_checks.placed_items(plan)
            if row in rows and shape is not None and holders.wall_held(rows[row], rows)]
    fixes = []
    for item, row, shape in sorted(held, key=lambda found: -max(found[0][3], found[0][4])):
        box, along = list(item[1:5]), 0 if item[3] >= item[4] else 1
        if box[2 + along] < RUN_SHARE * box[3 - along]:
            continue  # no run: a door, a seat, a corner piece
        low = float(shape.get("base") or 0.0)
        for other, other_row, other_shape in held:
            start, end = other[1 + along], other[1 + along] + other[3 + along]
            other_low = float(other_shape.get("base") or 0.0)
            if other is item or other_row != row or not overlapping(box, other[1:5]) \
                    or not (start <= box[along] or end >= box[along] + box[2 + along]) \
                    or not (other_low < low + float(shape.get("tall") or 0.0)
                            and low < other_low + float(other_shape.get("tall") or 0.0)):
                continue
            box = trimmed(box, other[1:5], along)
            if box is None:
                break
        if box is None or box == list(item[1:5]) or box[2 + along] < item[3 + along] / 2:
            continue
        count = int(shape.get("count") or 1)
        kept = max(1, round(count * box[2 + along] / item[3 + along]))
        item[1:5] = [round(value, 3) for value in box]
        if count > 1:
            shape["count"] = kept
        if kept < count:
            count_said(plan, row, f"{count - kept} fewer of it laid, {plan_checks.said_name(item[0])} cut clear of the "
                                  "piece at its corner")
        fixes.append(f"{plan_checks.said_name(item[0])}: cut to {item[3 + along]:.2f} m along its wall, clear of the "
                     "piece at its corner")
    return fixes


def made_outline(item, row, margin=0.0):
    """The footprint box (a polygon) of a plan `item` as its model is made: its row's read wide and deep (turned for a
    thing facing east or west), never less than the item's own, about the item's middle, `margin` more each way. The
    bake lays a take within its row's read size, never the plan's (prepare/groups.row_size, the surfaces'
    bake_job.laid_size), anywhere in that box whatever the plan's shape: campgrounds' habitat dome 2, drawn a 6.37 m
    circle, is made 10 by 9.9 m, its body reaching 5.03 m from its middle and a guy stake 5.16 m."""
    wide, deep = (row["size"][1], row["size"][0]) if item[5] in ("E", "W") else row["size"][:2]
    wide, deep = max(float(wide), item[3]) + 2 * margin, max(float(deep), item[4]) + 2 * margin
    middle = [item[1] + item[3] / 2, item[2] + item[4] / 2]
    return plan_checks.polygon_of([item[0], middle[0] - wide / 2, middle[1] - deep / 2, wide, deep, *item[5:]], None)


def made_things(plan, inventory):
    """[(item, made_outline MARGIN clear, made_outline)] of each thing on the floor or ground made larger than the
    plan draws it (a read size, one of its own: no run of pieces), its made box inside the plan's outline (a thing
    made past it stands past the plan's edge, its item only its face: the square's 30 m buildings)."""
    rows, outline, found = {row["id"]: row for row in inventory.get("rows", [])}, plan_checks.outline_of(plan), []
    for item, row, shape in plan_checks.blocking(plan, inventory):
        size = (rows.get(row) or {}).get("size")
        if not (isinstance(size, list) and len(size) >= 2) or int((shape or {}).get("count") or 1) > 1:
            continue
        made = made_outline(item, rows[row])
        if (numpy.ptp(numpy.asarray(made, float), axis=0) > numpy.asarray(item[3:5]) + MARGIN).any() and \
                plan_checks.inside(numpy.asarray(made, float), outline).all():
            found.append((item, made_outline(item, rows[row], MARGIN), made))
    return found


def flight_clear(stair, points, plan, things, others):
    """Whether `stair` laid at footprint `points` stands inside the plan's outline and out of its walls (stair_gaps'
    test), of every made thing of `things` (made_things) and of the other flights' footprints `others`."""
    samples, _ = plan_checks.flight_samples(*plan_checks.flight({**stair, "points": points})[:5])
    samples = numpy.vstack([samples, numpy.asarray(points, float)])
    return not plan_checks.past_walls(samples, plan_checks.outline_of(plan), plan.get("walls") or []) and not any(
        plan_checks.inside(samples, polygon).any() for polygon in [*(clear for _, clear, _ in things), *others])


def flights_cleared(plan, inventory):
    """Each stair or ramp the plan lays clear of a thing as drawn but inside it as made (made_things: campgrounds'
    ramp 2, laid 0.62 m off habitat dome 2's drawn 6.37 m circle, 1.2 m inside the dome as made 10 m across; settle@campgrounds,
    2026-11-09: the dome laid inside the ramp) moved straight away from that thing's middle, INSIDE_STEP at a
    time and FLIGHT_REACH at most, to the first spot clear of it and every made thing by MARGIN, inside the outline,
    out of the walls and the other flights (`flight_clear`); left where it is with no such spot. A flight inside the
    thing as drawn too is its own (the lander's ramp up into it); the fixes said."""
    things, fixes = made_things(plan, inventory), []
    stairs = [stair for stair in plan.get("stairs") or [] if len(stair.get("points") or []) >= 3]
    for number, stair in enumerate(stairs, 1):
        corners = numpy.asarray(stair["points"], float)
        middle = corners.mean(axis=0)
        into = next(((item, made) for item, _, made in things
                     if plan_checks.inside(corners, made).any() or plan_checks.inside(
                         numpy.asarray(made, float), corners).any()), None)
        if into is None or plan_checks.inside(corners, plan_checks.polygon_of(
                into[0], plan.get("shapes", {}).get(into[0][0]))).any():
            continue
        item = into[0]
        away = middle - [item[1] + item[3] / 2, item[2] + item[4] / 2]
        away = away / max(float(numpy.linalg.norm(away)), 1e-9)
        others = [other["points"] for other in stairs if other is not stair]
        step = next((step for step in numpy.arange(INSIDE_STEP, FLIGHT_REACH + INSIDE_STEP / 2, INSIDE_STEP)
                     if flight_clear(stair, (corners + away * step).tolist(), plan, things, others)), None)
        if step is None:
            continue
        stair["points"] = [[round(float(value), 3) for value in point] for point in corners + away * step]
        fixes.append(f"{stair.get('kind', 'stair')} {number}: moved {step:.2f} m out of "
                     f"{plan_checks.said_name(item[0])} as it is made "
                     f"({numpy.ptp(numpy.asarray(into[1], float), axis=0).max():.1f} m across, drawn "
                     f"{max(item[3], item[4]):.2f} m)")
    return fixes


SIDES = {(0, 1): "north", (0, -1): "south", (1, 0): "west", (-1, 0): "east"}  # a wall by the way into the plan off it


def wall_ways(plan):
    """[(wall, run, out, length)] of each straight plan wall along an axis (holders.walls_of): its line's unit step,
    the unit step off it into the plan (toward the plan's middle) and its length."""
    centre = numpy.array([float(plan["w"]) / 2, float(plan["d"]) / 2])
    found = []
    for wall in holders.walls_of(plan):
        start, end = numpy.asarray(wall["from"], float), numpy.asarray(wall["to"], float)
        length = float(numpy.linalg.norm(end - start))
        run = (end - start) / max(length, 1e-9)
        if length > 1e-6 and float(numpy.max(numpy.abs(run))) > 0.999:
            found.append((wall, run, numpy.array([-run[1], run[0]]) * holders.off_line(centre, wall)[1], length))
    return found


def in_plan_box(box, plan):
    """`box` [x, y, w, d] clipped to the plan's w x d box and moved the least way into it (as items_inside lays it)."""
    wide, deep = min(box[2], float(plan["w"])), min(box[3], float(plan["d"]))
    return [min(max(box[0], 0.0), float(plan["w"]) - wide), min(max(box[1], 0.0), float(plan["d"]) - deep), wide, deep]


def held_wall(item, row, plan, inventory, ways):
    """The number in `ways` (wall_ways) of the wall the holders lay `item` of `row` against (holders.on_wall: the nearest
    long enough for it), its box taken inside the plan's box first (in_plan_box: a writing's fixes bring it in after
    these); None on no axis wall."""
    laid = [*item[:1], *in_plan_box([float(value) for value in item[1:5]], plan), *item[5:]]
    found = holders.on_wall(laid, row, plan, inventory)
    key = found and holders.wall_key(found["wall"])
    return next((number for number, way in enumerate(ways) if holders.wall_key(way[0]) == key), None)


def built_by_id(plan, inventory):
    """{row id: row} of the reading's rows at the size each is made at (holders.built_rows: what the holders lay)."""
    return {row["id"]: row for row in holders.built_rows(inventory.get("rows", []), plan, inventory)}


def wall_runs(plan, inventory):
    """{row id: [[item, wall number, start, end, low, high]]} of each run (RUN_SHARE) of one thing of a row held on a
    wall (holders.wall_held; one of the shell, one that piles, spans the room or fills an opening left out), in the
    plan's order: on the axis wall (wall_ways) the holders lay it against along its long side (held_wall, the row at
    its built size), start to end its metres along that wall's line, low to high its height band."""
    ways, found = wall_ways(plan), {}
    rows = built_by_id(plan, inventory) if ways else {}
    for item, row, shape in plan_checks.placed_items(plan):
        if row not in rows or shape is None or int(shape.get("count") or 1) > 1 or piles(rows[row]) \
                or not holders.wall_held(rows[row], rows) or holders.holder_kind(rows[row]) is not None \
                or holders.spans(rows[row]) or design_shell.fills_opening(rows[row]):
            continue
        along = 0 if item[3] >= item[4] else 1
        if item[3 + along] < RUN_SHARE * item[4 - along]:
            continue  # no run: a lamp, a clock
        number = held_wall(item, rows[row], plan, inventory, ways)
        if number is None or abs(ways[number][1][along]) < 0.5:
            continue  # held across its long side: its box says nothing of its span there
        box = in_plan_box([float(value) for value in item[1:5]], plan)
        start = numpy.asarray(ways[number][0]["from"], float)
        ends = sorted(min(max(float((numpy.array(point) - start) @ ways[number][1]), 0.0), ways[number][3])
                      for point in ([box[0], box[1]], [box[0] + box[2], box[1] + box[3]]))
        low = float(shape.get("base") or 0.0)
        found.setdefault(row, []).append([item, number, *ends, low, low + float(shape.get("tall") or 0.0)])
    return found


def in_each_other(run, other):
    """Whether two runs of wall_runs lie in each other: on one wall, their metres along it and heights crossing."""
    return run[1] == other[1] and run[2] < other[3] and other[2] < run[3] and run[4] < other[5] and other[4] < run[5]


def laid_along(plan, way, deep, start, end):
    """[x, y, w, d] of a run `deep` metres deep laid against axis wall `way` (wall_ways) from `start` to `end` metres
    along its line, on the plan's side; None where that lies past the plan's outline."""
    wall, run, out, _ = way
    origin = numpy.asarray(wall["from"], float)
    corners = numpy.array([origin + run * start, origin + run * end, origin + run * end + out * deep,
                           origin + run * start + out * deep])
    low, high = corners.min(axis=0), corners.max(axis=0)
    tested = numpy.array([[low[0], low[1]], [high[0], low[1]], [high[0], high[1]], [low[0], high[1]]]) + \
        numpy.array([[1, 1], [-1, 1], [-1, -1], [1, -1]]) * INSIDE_SLACK
    if not plan_checks.inside(tested, plan_checks.outline_of(plan)).all():
        return None
    return [round(float(value), 3) for value in (*low, *(high - low))]


def side_of(way):
    """The compass word of an axis wall (wall_ways), by the way into the plan off it (y runs south)."""
    return SIDES[tuple(int(round(float(value))) for value in way[2])]


def onto_free_wall(plan, inventory, run, row, ways, used):
    """`run` (wall_runs) of `row` laid along the axis wall nearest its middle that no run of its row lies on (`used`,
    wall numbers) and the holders would lay it against there (held_wall: one long enough for it), at the wall's middle;
    its new wall number, None (left as laid) with none."""
    item = run[0]
    box = in_plan_box([float(value) for value in item[1:5]], plan)
    middle = numpy.array([box[0] + box[2] / 2, box[1] + box[3] / 2])
    long, deep = max(item[3], item[4]), min(item[3], item[4])
    for number in sorted((number for number in range(len(ways)) if number not in used),
                         key=lambda number: holders.off_line(middle, ways[number][0])[0]):
        length = ways[number][3]
        span = min(long, length)
        laid = laid_along(plan, ways[number], deep, (length - span) / 2, (length + span) / 2)
        if laid is not None and held_wall([item[0], *laid, *item[5:]], row, plan, inventory, ways) == number:
            item[1:5] = laid
            run[1:4] = [number, (length - span) / 2, (length + span) / 2]
            return number
    return None


def wall_runs_spread(plan, inventory):
    """Each run on a wall (wall_runs) lying in one of its row's laid before it on that wall (in_each_other) laid along
    a wall none of its row's runs lie on (onto_free_wall); one with no such wall left as laid, a gap (stack_gaps); the
    fixes said. 2026-11-09, settle@garage in env1 checkout 68: split_runs laid its seven pipes at the reading's one
    10 m size, each along x at its concept box's projection, three of them past its north edge, and items_inside
    clamped those three into one corner at [0, 0]; the holders stood them over one another on that wall. A run still
    in one laid before it, with no such wall left, is more of its row than the place's walls hold: taken off
    (surplus_dropped), its row's `dropped` saying why, so the scene record lays only the runs that fit (garage's
    seven 10 m pipes, read from SAM 3 boxes of two long runs and of three short stubs boxed in pieces, 2026-11-09:
    pipes 5, 6 and 7 off, four laid on its four walls)."""
    ways, fixes = wall_ways(plan), []
    rows = built_by_id(plan, inventory) if ways else {}
    for row, runs in wall_runs(plan, inventory).items():
        kept, surplus = [], []
        for run in runs:
            if any(in_each_other(run, other) for other in kept):
                if onto_free_wall(plan, inventory, run, rows[row], ways, {other[1] for other in runs}) is None:
                    surplus.append(run[0])
                    continue
                fixes.append(f"{plan_checks.said_name(run[0][0])}: laid along the {side_of(ways[run[1]])} wall, out "
                             "of its row's others on its own")
            kept.append(run)
        fixes += surplus_dropped(plan, inventory, surplus, "the place's wall room")
    return fixes


STAIR_ROWS = {"stair", "stairs", "staircase", "staircases"}  # a row's words naming the flights the shell builds


def eaves_raised(plan):
    """Each roof whose eave stands less than a doorway's head (design_shell.DOOR_HEAD) over a raised level under it
    (plan_checks.LOW or more over the floor: an upper floor, a gallery) raised to
    a storey over that level (the walls' written height, else the height words' ceiling, else design_shell.STOREY),
    its rise kept; the shell raises its walls to the eave (design_shell.wall_height); the fixes said. 2026-11-09,
    settle@greenhouse in env1 checkout 68: its upper floor at 3 m stood over its dome's 2.8 m eave, the dome's
    underside 3.5 to 4.7 m over the ring, and nine things on it (its 2.5 m tanks) stood in the roof."""
    storey = max([float(wall.get("tall") or 0.0) for wall in plan.get("walls") or []], default=0.0) or \
        design_shell.measured_ceiling(plan) or design_shell.STOREY
    fixes = []
    for number, roof in enumerate(plan.get("roofs") or [], 1):
        if len(roof.get("points") or []) < 3 or roof.get("eave") is None:
            continue
        under = [level for level in plan.get("levels") or [] if len(level.get("points") or []) >= 3
                 and float(level.get("height") or 0.0) >= plan_checks.LOW  # a storey up, not the floor or a step
                 and plan_checks.inside(numpy.asarray(level["points"], float), roof["points"]).any()]
        level = max(under, key=lambda level: float(level.get("height") or 0.0), default=None)
        eave = float(roof["eave"])
        if level is None or eave >= float(level.get("height") or 0.0) + design_shell.DOOR_HEAD:
            continue
        raised = round(float(level.get("height") or 0.0) + storey, 3)
        roof["eave"] = raised
        if roof.get("top") is not None:
            roof["top"] = round(float(roof["top"]) + raised - eave, 3)
        height = float(level.get("height") or 0.0)
        fixes.append(f"{roof.get('kind', 'flat')} roof {number}: its eave raised from {eave:g} m to {raised:g} m, a "
                     f"storey ({storey:g} m) over its {level.get('name', 'level')} at {height:g} m")
    return fixes


def stair_rows_dropped(plan, inventory):
    """Each row whose noun names stairs (STAIR_ROWS; a ramp or steps is a thing of its own) and that holds nothing (no
    row stands on it) taken off the plan where the plan draws flights the shell builds (its `stairs`, a ramp's too):
    off every item that ties it and any item of its own, said in the plan's `dropped`; the fixes said. 2026-11-09,
    settle@greenhouse in env1 checkout 68: its reading's stairs row, tied to the walls item, laid two stairs objects on
    the shell's three flights."""
    flights = [stair for stair in plan.get("stairs") or [] if len(stair.get("points") or []) >= 3]
    if not flights:
        return []
    fixes = []
    for row in inventory.get("rows", []):
        if not set(re.findall(r"[a-z]+", str(row.get("noun") or "").lower())) & STAIR_ROWS or \
                any(other.get("anchor") == f"on:{row['id']}" for other in inventory.get("rows", [])):
            continue  # no stairs, or one its railings or people stand on
        tied = [name for name, rows in (plan.get("rows") or {}).items() if row["id"] in (rows or [])]
        if not tied:
            continue
        for name in tied:
            plan["rows"][name] = [found for found in plan["rows"][name] if found != row["id"]]
            if not plan["rows"][name]:
                item = next((item for item in plan["items"] if item[0] == name), None)
                if item is not None:
                    dropped_item(plan, item)
        why = f"the shell builds the plan's {len(flights)} flights"
        plan.setdefault("dropped", []).append({"item": row["id"], "why": why})
        fixes.append(f"{plan_checks.said_name(row['id'])}: taken off, {why}")
    return fixes


def level_cells(plan, grid, item):
    """The grid cells of the level `item`'s middle stands on (the highest holding it; its base the level's height),
    else the plan's outline's."""
    middle = numpy.array([[item[1] + item[3] / 2, item[2] + item[4] / 2]])
    base = float(((plan.get("shapes") or {}).get(item[0]) or {}).get("base") or 0.0)
    holding = [level for level in plan.get("levels") or [] if len(level.get("points") or []) >= 3
               and abs(float(level.get("height") or 0.0) - base) < plan_checks.LOW
               and plan_checks.inside(middle, level["points"]).all()]
    return grid.covered(holding[0]["points"] if holding else plan_checks.outline_of(plan))


def crossing(first, second):
    """Whether two polygons (N x 2 arrays) cross: a corner of either inside the other."""
    return bool(plan_checks.inside(first, second).any() or plan_checks.inside(second, first).any())


def on_flights(plan, inventory):
    """[(item, its made outline)] of each thing on the floor (or on a floor the place lays: `floored`) clear of every
    stair or ramp as drawn but in one's footprint as made (made_outline: its read size about its middle), its made box
    inside the plan's outline (one made past it stands past the plan's edge, made_things)."""
    flights = [numpy.asarray(stair["points"], float) for stair in plan.get("stairs") or []
               if len(stair.get("points") or []) >= 3]
    on_floor, outline, found = floored(plan, inventory), plan_checks.outline_of(plan), []
    rows = {row["id"]: row for row in on_floor.get("rows", [])}
    for item, row, shape in plan_checks.blocking(plan, on_floor) if flights else []:
        size = (rows.get(row) or {}).get("size")
        if not (isinstance(size, list) and len(size) >= 2) or int((shape or {}).get("count") or 1) > 1:
            continue
        inset = [item[0], item[1] + MARGIN, item[2] + MARGIN, max(item[3] - 2 * MARGIN, MARGIN),
                 max(item[4] - 2 * MARGIN, MARGIN), *item[5:]]  # drawn touching a flight is clear of it
        made, drawn = (numpy.asarray(polygon, float) for polygon in (made_outline(item, rows[row]),
                                                                   plan_checks.polygon_of(inset, shape)))
        if plan_checks.inside(made, outline).all() and any(crossing(made, points) for points in flights) and \
                not any(crossing(drawn, points) for points in flights):
            found.append((item, made))
    return found


def off_flights(plan, inventory):
    """Each thing in a stair or ramp as made though clear of it as drawn (on_flights) moved to the nearest floor of its
    own level (level_cells) where it stands as made, MARGIN clear, in no flight, wall, floor thing or thing standing
    low (taken_floor). One with none whose row lays others is more of its row than the place's floor holds as made:
    taken off (surplus_dropped), its row's `dropped` saying why, so the scene record lays only what fits; a row's last
    is left as laid, a gap (flight_gaps). The fixes said. 2026-11-09, settle@greenhouse in env1 checkout 68: planter
    beds 8, 10 and 11 stood on the feet of its flights. Its reading's one planter row is its four central beds, its
    rim's troughs and its crates, read 2.5 m square and made at the bake's fit within that (its take 1 by 0.24 by 1, so
    2.1 m square), drawn 0.47 to 2.05 m: no floor of the lower floor holds beds 2, 7, 8, 10 and 11 so, and they go."""
    grid, fixes, surplus = plan_checks.Grid(plan), [], {}
    rows = {row["id"]: row for row in inventory.get("rows", [])}
    for item, made in on_flights(plan, inventory):
        middle = [item[1] + item[3] / 2, item[2] + item[4] / 2]
        level = level_cells(plan, grid, item)
        span = numpy.ptp(made, axis=0) + 2 * (MARGIN + grid.size)
        free = standing.nearest_free(middle, span.tolist(), taken_floor(plan, inventory, item, grid) | ~level, grid,
                                     level, [])
        if free is None:
            row = (plan.get("rows", {}).get(item[0]) or [None])[0]
            if laid_of(plan, row) - len(surplus.get(row, [])) > 1:
                surplus.setdefault(row, []).append(item)
            continue
        item[1], item[2] = round(free[0] - item[3] / 2, 3), round(free[1] - item[4] / 2, 3)
        fixes.append(f"{plan_checks.said_name(item[0])}: moved {math.dist(middle, free):.2f} m off the stairs, clear "
                     f"of them as made ({numpy.ptp(made, axis=0).max():.1f} m across, drawn "
                     f"{max(item[3], item[4]):.2f} m)")
    for row, items in surplus.items():
        size = rows[row]["size"]  # on_flights finds only things of a row with a read size
        fixes += surplus_dropped(plan, inventory, items, "its level's floor clear of the stairs",
                                 f"up to {size[0]:g} x {size[1]:g} m as made")
    return fixes


def ramps_walled(plan, inventory):
    """Each ramp the holders lay up to a raised level through a wall (its footprint where they lay it,
    `ramp_footprint`, inset MARGIN, past the plan's outline, which the shell walls, or in one of its walls:
    plan_checks.past_walls) taken off (`surplus_dropped`, said in `dropped`): no spot of it climbs to that level. A
    place with no walls is left. settle@airlock, env1 checkout 71: its ramp, drawn at the front, laid 1.5 m off up to
    its locker floor's east edge, through that edge's wall and the porch's, 1 m past the outline."""
    if not plan.get("walls"):
        return []
    rows, outline, walled = {row["id"]: row for row in inventory.get("rows", [])}, plan_checks.outline_of(plan), []
    for item, row, _ in plan_checks.blocking(plan, inventory):
        footprint = ramp_footprint(item, rows.get(row), plan)
        if footprint is None:
            continue
        corners = numpy.asarray(footprint, float)
        side, end = corners[1] - corners[0], corners[3] - corners[0]
        inset = [MARGIN / max(float(numpy.linalg.norm(way)), 1e-9) for way in (side, end)]
        samples = numpy.array([corners[0] + side * along + end * across
                               for along in numpy.linspace(inset[0], 1 - inset[0], 9)
                               for across in numpy.linspace(inset[1], 1 - inset[1], 9)])
        if plan_checks.past_walls(samples, outline, plan["walls"]):
            walled.append(item)
    return surplus_dropped(plan, inventory, walled, why=f"{len(walled)} laid up to a raised level through a wall") \
        if walled else []


RUN_REACH = 1.0  # metres a run is moved at most to lay its pieces end to end as made, clear of what stands round it


def made_sizes(plan, inventory):
    """{row id: [wide, deep, tall]} of each reading row at the size it is made at (prepare's groups.made_size, the
    hand-in's: one repeating piece of a run its reading measured whole), as the holders size a wall thing
    (holders.built_rows)."""
    from score.stages.complete.prepare import groups
    rows, picture = inventory.get("rows", []), inventory.get("picture")
    laid, found = groups.plan_sizes_of(plan, rows), {}
    for row in rows:
        box = row.get("box") or (plan_checks.gemini_box(row["region"], picture) if row.get("region") and picture
                                 else None)
        found[row["id"]] = groups.made_size(row, rows, plan, laid, box)
    return found


def run_room(plan, inventory, item, grid, outline):
    """(the cells a run `item` may stand on: its level's (level_cells); where its middle is drawn off the outline, off
    it, on a level holding its middle or anywhere off it; the cells taken round it: taken_floor's and the cells off
    that room)."""
    room, inside = level_cells(plan, grid, item), grid.covered(outline)
    if not plan_checks.inside(numpy.array([[item[1] + item[3] / 2, item[2] + item[4] / 2]]), outline).all():
        room = (numpy.ones_like(room) if (room == inside).all() else room) & ~inside
    return room, taken_floor(plan, inventory, item, grid) | ~room


def runs_laid_out(plan, inventory):
    """Each run on the floor (a counted box of several floor things, plan_checks.blocking, of a row with a read size)
    laid as the scene record lays it: its pieces as made (the row's read size, its long side along the run's,
    scene_record/writer.spots_of) end to end along its box, clear of every wall, stair, floor thing where it is laid
    and thing standing low by a wall (taken_floor), on its own level (`run_room`). One whose box does not hold its
    pieces so is laid, within RUN_REACH of its middle, as long as the most of its pieces a free spot there holds
    (standing.nearest_free, MARGIN clear), its count cut to them and said in the plan's `dropped` (`count_said`);
    one with no spot even for one taken off (`surplus_dropped`) where its row lays others, else left; the fixes said.
    settle@airlock, env1 checkout 71: its sandbags 0.6 x 0.4 m as made, 6 on a 0.4 x 1.23 m box, 5 on 1.39 m and 3 on
    0.64 m, were parted out of their boxes by the assembly into one another, its locker's suit and its entrance
    flight."""
    grid, outline = plan_checks.Grid(plan), plan_checks.outline_of(plan)
    sizes, fixes, cut, surplus = made_sizes(plan, inventory), [], {}, []
    for item, row, shape in plan_checks.blocking(plan, inventory):
        count, size = int((shape or {}).get("count") or 1), sizes.get(row)
        if count < 2 or not (isinstance(size, list) and len(size) >= 2 and all(
                isinstance(side, (int, float)) and side > 0 for side in size[:2])):
            continue
        along = 0 if item[3] >= item[4] else 1
        long_side, short_side = max(float(size[0]), float(size[1])), min(float(size[0]), float(size[1]))
        middle = [item[1] + item[3] / 2, item[2] + item[4] / 2]
        room, taken = run_room(plan, inventory, item, grid, outline)
        if item[3 + along] >= count * long_side - MARGIN and item[4 - along] >= short_side - MARGIN and not (
                taken & standing.under(grid, middle, item[3:5])).any():
            continue
        placed = None
        for kept in range(count, 0, -1):
            box = [0.0, 0.0]
            box[along], box[1 - along] = kept * long_side, short_side
            free = standing.nearest_free(middle, [side + 2 * (MARGIN + grid.size) for side in box], taken, grid,
                                         room, [])
            if free is not None and math.dist(free, middle) <= RUN_REACH:
                placed = kept, box, free
                break
        if placed is None:
            if laid_of(plan, row) - sum(int(plan["shapes"][other[0]].get("count") or 1) for other in surplus
                                         if plan["rows"][other[0]][0] == row) > count:
                surplus.append(item)
            continue
        kept, box, free = placed
        item[1:5] = [round(free[0] - box[0] / 2, 3), round(free[1] - box[1] / 2, 3), round(box[0], 3),
                     round(box[1], 3)]
        shape["count"] = kept
        cut[row] = cut.get(row, 0) + count - kept
        fixes.append(f"{plan_checks.said_name(item[0])}: laid {kept} of {count} end to end as made "
                     f"({long_side:g} x {short_side:g} m each), moved {math.dist(free, middle):.2f} m clear")
    for row, fewer in cut.items():
        if fewer:
            count_said(plan, row, f"{fewer} fewer of it laid, its runs as long as their free floor holds as made")
    return fixes + (surplus_dropped(plan, inventory, surplus, "its runs' free floor") if surplus else [])


def hung_runs(plan, inventory):
    """[(item, row id, shape, long, short)] of each counted item of a row hung from the roof (holders.under_roof), its
    pieces runs (RUN_SHARE times as long as across: a cable, never a lamp), whose pieces as made (made_sizes: `long`
    along the run, `short` across) are longer end to end than its box: the scene record lays them evenly along its
    box's long line (writer.spots_of), in one another."""
    rows, sizes, found = {row["id"]: row for row in inventory.get("rows", [])}, made_sizes(plan, inventory), []
    for item, row, shape in plan_checks.placed_items(plan):
        count, size = int((shape or {}).get("count") or 1), sizes.get(row)
        if count < 2 or row not in rows or not holders.under_roof(rows[row]) or not (
                isinstance(size, list) and len(size) >= 2 and all(
                    isinstance(side, (int, float)) and side > 0 for side in size[:2])):
            continue
        long, short = max(float(size[0]), float(size[1])), min(float(size[0]), float(size[1]))
        if long >= RUN_SHARE * short and max(item[3], item[4]) < count * long - MARGIN:
            found.append((item, row, shape, long, short))
    return found


def under_wall(way, short, start, end):
    """[x, y, w, d] of a run `short` deep hung along axis wall `way` (wall_ways) from `start` to `end` metres along its
    line, off the wall's room face."""
    wall, run, out, _ = way
    face = numpy.asarray(wall["from"], float) + out * float(wall.get("thick") or 0.0) / 2
    corners = numpy.array([face + run * start, face + run * end, face + run * end + out * short,
                           face + run * start + out * short])
    low, high = corners.min(axis=0), corners.max(axis=0)
    return [round(float(value), 3) for value in (*low, *(high - low))]


def hung_runs_laid_out(plan, inventory):
    """Each run hung from the roof whose pieces as made do not fit its box end to end (hung_runs) laid along the
    room's walls under the roof instead, nearest its middle first: on each axis wall (wall_ways) as many as its face
    holds end to end, clear of every other hung thing, the first wall's on its own item, each further wall's an item
    of its row; what no wall holds is laid no more, said in `dropped` (count_said); the fixes said. settle@storage,
    2026-11-10: its six 2 m cable bundles "round the ceiling edges" on one 2.68 m box, laid 0.45 m apart in one another
    (0.09 to 0.107 m deep)."""
    ways, fixes = wall_ways(plan), []
    outline = plan_checks.outline_of(plan)
    rows = {row["id"]: row for row in inventory.get("rows", [])}
    for item, row, shape, long, short in hung_runs(plan, inventory) if ways else []:
        count, left = int(shape["count"]), int(shape["count"])
        middle = numpy.array([item[1] + item[3] / 2, item[2] + item[4] / 2])
        hung = [other[1:5] for other, other_row, _ in plan_checks.placed_items(plan)
                if other is not item and other_row in rows and holders.under_roof(rows[other_row])]
        laid = []
        for way in sorted(ways, key=lambda way: holders.off_line(middle, way[0])[0]):
            inset = float(way[0].get("thick") or 0.0) / 2 + MARGIN
            pieces = min(left, int((way[3] - 2 * inset + MARGIN) // long))
            if pieces < 1:
                continue
            span = pieces * long
            box = under_wall(way, short, (way[3] - span) / 2, (way[3] + span) / 2)
            corners = numpy.array([[box[0], box[1]], [box[0] + box[2], box[1]], [box[0] + box[2], box[1] + box[3]],
                                   [box[0], box[1] + box[3]]])
            if any(overlapping(box, other) for other in hung + [found for found, _ in laid]) or not plan_checks.inside(
                    corners + numpy.array([[1, 1], [-1, 1], [-1, -1], [1, -1]]) * INSIDE_SLACK, outline).all():
                continue
            laid.append((box, pieces))
            left -= pieces
            if not left:
                break
        if not laid:
            continue
        (first, pieces), *more = laid
        item[1:5] = first
        shape["count"] = pieces
        names = [item[0]]
        for box, pieces in more:
            name = added_item(plan, row, [box[0] + box[2] / 2, box[1] + box[3] / 2], box[2:], like=shape)
            plan["shapes"][name]["count"] = pieces
            names.append(name)
        fixes.append(f"{plan_checks.said_name(item[0])}: its {count} pieces ({long:g} m each as made) hung end to end "
                     f"along {len(laid)} wall{'s' if len(laid) > 1 else ''} under the roof, as "
                     f"{', '.join(plan_checks.said_name(name) for name in names)}")
        if left:
            count_said(plan, row, f"{left} fewer of it laid, no wall under the roof holding more as made")
    return fixes


TOP_CLEAR = 0.01  # metres between things side by side on a top and from its ends (assembly fitting.BOARD_CLEAR)


def made_footprint(item, size):
    """[x, y] metres of a plan item's footprint at its made `size` [wide, deep, tall]: its long side along the way the
    scene record lays it (writer.item_way: its facing's, turned onto a slender box's long side)."""
    from score.stages.scene_record import writer
    way = writer.item_way(item, {"size": list(size)})
    long, short = max(float(size[0]), float(size[1])), min(float(size[0]), float(size[1]))
    return [long, short] if abs(float(way[0])) >= abs(float(way[1])) else [short, long]


def sized(size):
    """Whether a made size has a positive wide and deep."""
    return isinstance(size, list) and len(size) >= 2 and all(
        isinstance(side, (int, float)) and side > 0 for side in size[:2])


def tops_cut(plan, inventory):
    """The things of one row the holders stand on a holder's top (holders.relations, `top`; a row that piles left out)
    cut to those that stand side by side in one row along its long side at their made size (made_sizes, made_footprint),
    TOP_CLEAR apart and from its ends, as the assembly spreads them there (fitting.spread_on_tops), each of the holder
    item's pieces one top: the nearest its holder's middle kept, never fewer than one; the rest taken off
    (`surplus_dropped`, said in `dropped`), so the scene record lays only what fits. hub, 2026-11-11: 16 monitor
    screens on a 1.75 m console top and 19 on a 2.73 m bank were laid in one another (held: 22 of them); the plan
    fixes cut runs on the floor, the walls and under the roof so (runs_laid_out, wall_runs_spread,
    hung_runs_laid_out), its tops not."""
    sizes, items = made_sizes(plan, inventory), {item[0]: item for item in plan.get("items", [])}
    rows, shapes = {row["id"]: row for row in inventory.get("rows", [])}, plan.get("shapes", {})
    on = {}
    for entry in holders.relations(plan, inventory)["relations"]:
        if entry.get("how") == "top" and entry.get("holder") in items and entry["item"] in items \
                and entry["row"] in rows and not piles(rows[entry["row"]]) and sized(sizes.get(entry["row"])):
            on.setdefault((entry["row"], entry["holder"]), []).append(items[entry["item"]])
    fixes, surplus = [], {}
    for (row, holder), things in on.items():
        held_size = sizes.get((plan.get("rows", {}).get(holder) or [None])[0])
        if not sized(held_size):
            continue
        top = made_footprint(items[holder], held_size)
        axis = 0 if top[0] >= top[1] else 1
        long = top[axis] * int((shapes.get(holder) or {}).get("count") or 1)
        middle = numpy.array([items[holder][1] + items[holder][3] / 2, items[holder][2] + items[holder][4] / 2])
        used, kept, cut = TOP_CLEAR, 0, []
        for thing in sorted(things, key=lambda thing: float(numpy.linalg.norm(
                numpy.array([thing[1] + thing[3] / 2, thing[2] + thing[4] / 2]) - middle))):
            needs = int((shapes.get(thing[0]) or {}).get("count") or 1) * (
                made_footprint(thing, sizes[row])[axis] + TOP_CLEAR)
            if used + needs <= long + 1e-9 or not kept:
                used, kept = used + needs, kept + 1
            else:
                cut.append(thing)
        if cut:
            surplus.setdefault(row, []).extend(cut)
            fixes.append(f"{plan_checks.said_name(holder)}: its top, {top[axis]:g} m long as made, holds {kept} of the "
                         f"{len(things)} {plan_checks.said_name(row)} the holders stand on it side by side as made")
    return fixes + [said for row, cut in surplus.items() for said in surplus_dropped(
        plan, inventory, cut, why=f"{len(cut)} more of it than its holders' tops hold side by side as made")]


def kept_apart(plan, inventory):
    """The fixes that keep what settle drops out of each other and out of the shell (env1 checkouts 67 and 68), in
    order: a roof's eave raised a storey over a level standing under it (`eaves_raised`), a stairs row taken off where
    the shell builds the flights (`stair_rows_dropped`), runs kept out of the walls and stairs (`runs_kept_clear`), a
    single thing laid again in its own row's run taken off (`run_doubles_dropped`), a ramp the holders lay up through
    a wall taken off (`ramps_walled`), runs laid as long as their pieces as made, clear of what stands round them
    (`runs_laid_out`), runs hung from the roof longer as made than their box hung along the walls under it
    (`hung_runs_laid_out`), things piled on their own row's
    though it does not pile stood on the floor or taken off (`unpiled`), runs of one row in each other on a wall laid
    along walls free of them or taken off (`wall_runs_spread`), runs on a wall parted (`wall_runs_parted`), stairs and
    ramps moved out of what is made larger than drawn (`flights_cleared`), things made larger than drawn moved off the
    stairs or taken off (`off_flights`), things on a holder's top cut to what stands side by side on it as made
    (`tops_cut`); the fixes said. A writing fixed before them gets them in the pass (plans_pass.unsettled), an edit
    or a redrawing when shown (plans.edit_inside)."""
    return eaves_raised(plan) + stair_rows_dropped(plan, inventory) + runs_kept_clear(plan, inventory) \
        + run_doubles_dropped(plan, inventory) + ramps_walled(plan, inventory) + runs_laid_out(plan, inventory) \
        + hung_runs_laid_out(plan, inventory) + unpiled(plan, inventory) + wall_runs_spread(plan, inventory) \
        + wall_runs_parted(plan, inventory) + flights_cleared(plan, inventory) + off_flights(plan, inventory) \
        + tops_cut(plan, inventory)


# A door row's doorway stands within this of its bearing, degrees; the kinds of opening a person walks through.
BEARING_REACH = 30.0


DOORWAY_KINDS = ("door", "gate", "opening")


SIDE_WAYS = {"N": (0.0, -1.0), "S": (0.0, 1.0), "E": (1.0, 0.0), "W": (-1.0, 0.0)}


def toward(plan, point):
    """The plan side (N, E, S or W) a plan point lies toward from the plan's middle, its box's half sides as one."""
    half = numpy.array([float(plan["w"]) / 2, float(plan["d"]) / 2])
    way = (numpy.asarray(point, float) - half) / numpy.maximum(half, 1e-9)
    return max(SIDE_WAYS, key=lambda side: float(numpy.asarray(SIDE_WAYS[side]) @ way))


def bearing(plan, point):
    way = numpy.asarray(point, float) - [float(plan["w"]) / 2, float(plan["d"]) / 2]
    return math.degrees(math.atan2(float(way[0]), float(-way[1]))) % 360.0


def off_bearing(plan, point, degrees):
    return abs((bearing(plan, point) - float(degrees) + 180.0) % 360.0 - 180.0)


def door_of(plan, door):
    """(how it is placed, metres, words, sill, along, lead) of a plan door row: [side, along, metres, words, sill],
    [bearing, metres, words] or [word, metres, words] (a tube's `near`), its lead under its side and along (`E:9`: a
    wall with doors to two places, the walkway's to the galley and the quarters), else its key and sill (`W@9`), else
    its key."""
    sided = door[0] in SIDE_WAYS
    metres, words = (door[2], door[3] if len(door) > 3 else "") if sided else (door[1], door[2])
    sill = float(door[4]) if sided and len(door) > 4 and door[4] is not None else None
    key = door[0] if isinstance(door[0], str) else f"{float(door[0]):g}"
    leads = plan.get("leads") or {}
    lead = (leads.get(f"{key}:{float(door[1]):g}") if sided else None) or (
        leads.get(f"{key}@{sill:g}") if sill is not None else None) or leads.get(key) or {}
    return door[0], float(metres), str(words), sill, door[1] if sided else None, lead.get("to")


def doorway_for(plan, place, metres, sill, lead, left, along=None):
    """The doorway of `left` [(index, opening)] a door row is: on its side at its sill, the nearest its `along` (a wall
    with two doors: the walkway's to the galley and the quarters), at its bearing, else leading where it leads;
    None."""
    if place in SIDE_WAYS:
        fits = sorted([pair for pair in left if toward(plan, pair[1]["at"]) == place and
                       (sill is None or abs(float(pair[1].get("sill") or 0.0) - sill) <= 0.05)],
                      key=lambda pair: 0.0 if along is None else abs(
                          float(pair[1]["at"][0 if place in ("N", "S") else 1]) - float(along)))
    elif isinstance(place, (int, float)):
        fits = sorted([pair for pair in left if off_bearing(plan, pair[1]["at"], place) <= BEARING_REACH],
                      key=lambda pair: off_bearing(plan, pair[1]["at"], place))
    else:
        fits = [pair for pair in left if lead is not None and pair[1].get("to") == lead]
    return fits[0] if fits else None


DOOR_WORDS = {"door", "hatch", "gate"}  # a row whose id names one of these is a door its doorway holds


DOOR_REACH = 1.5  # metres past its own size a door item's doorway may stand from its middle


def doorways_fit(plan, inventory):
    """Each doorway as big as the door standing in it (#128 D5: the airlock's 1.04 m doorways for its 1.2 x 2.1 m
    door): for each plan item of a door row (its id's last word in DOOR_WORDS, with metres), the nearest doorway within its own
    size and DOOR_REACH of its middle made at least the row's wide, its head at least the row's tall over its sill;
    the fixes said. Never narrowed: a door smaller than its doorway is the fitting's to grow."""
    sizes = {row["id"]: row["size"] for row in inventory.get("rows", []) if isinstance(row.get("size"), list)
             and len(row["size"]) >= 3 and str(row["id"]).lower().split("_")[-1] in DOOR_WORDS
             and all(isinstance(part, (int, float)) and part > 0 for part in row["size"][:3])}
    openings = [opening for opening in plan.get("openings") or [] if opening.get("kind") in DOORWAY_KINDS
                and isinstance(opening.get("at"), list)]
    fixes = []
    for name, x, y, wide, deep, *_ in plan.get("items", []):
        row = next((row for row in plan.get("rows", {}).get(name) or [] if row in sizes), None)
        if row is None or not openings or name == plan_checks.WALLS_ITEM:
            continue
        middle = numpy.array([x + wide / 2, y + deep / 2])
        near = min(openings, key=lambda opening: float(numpy.linalg.norm(numpy.asarray(opening["at"]) - middle)))
        if float(numpy.linalg.norm(numpy.asarray(near["at"]) - middle)) > max(wide, deep) + DOOR_REACH:
            continue
        door_wide, door_tall = float(sizes[row][0]), float(sizes[row][2])
        sill = float(near.get("sill") or 0.0)
        head = float(near["head"]) if near.get("head") is not None else None
        if float(near["wide"]) < door_wide - 1e-6 or (head is not None and head - sill < door_tall - 1e-6):
            fixes.append(f"{name.lower()}: its doorway at {near['at']} {float(near['wide']):g} m wide"
                         + (f", {head - sill:g} m tall" if head is not None else "")
                         + f" made as big as its door, {door_wide:g} x {door_tall:g} m")
            near["wide"] = max(float(near["wide"]), door_wide)
            if head is not None:
                near["head"] = round(max(head, sill + door_tall), 3)
    return fixes + (door_rows_widened(plan) if fixes else [])


def door_rows_widened(plan):
    """Each plan door row whose doorway (doorway_for, as doors_kept matches them) is wider than its metres given
    the doorway's width, so the row and its doorway agree (scene_record's `openings` gate holds them equal); the
    fixes said."""
    left = [(number, opening) for number, opening in enumerate(plan.get("openings") or [])
            if opening.get("kind") in DOORWAY_KINDS]
    fixes = []
    for door in plan.get("doors") or []:
        if not (isinstance(door, list) and len(door) >= 3):
            continue
        place, metres, words, sill, along, lead = door_of(plan, door)
        found = doorway_for(plan, place, metres, sill, lead, left, along)
        if found is None:
            continue
        left.remove(found)
        if float(found[1]["wide"]) > metres + 1e-6:
            door[2 if place in SIDE_WAYS else 1] = float(found[1]["wide"])
            fixes.append(f"{words or place}: its door row {metres:g} m wide made its doorway's {found[1]['wide']:g} m")
    return fixes


def doors_sized(plan):
    """Each doorway of an edit that a door row of it is (doorway_for, as doors_kept matches them) made its row's
    metres wide, where it stands and where it leads kept as the edit draws them: none moved, cut or dropped, which only
    a writing's doors_kept does (2026-11-06: habitat's edit of 2026-10-25 kept its writing's 0.237 m hatches for its
    own 2.2 m rows, the base's redrawn greenhouse a 1.305 m one, so scene-record@habitat and @greenhouse failed
    `openings`); the fixes said."""
    doors = [door_of(plan, door) for door in plan.get("doors") or [] if isinstance(door, list) and len(door) >= 3]
    left = [(number, opening) for number, opening in enumerate(plan.get("openings") or [])
            if opening.get("kind") in DOORWAY_KINDS]
    fixes = []
    for place, metres, words, sill, along, lead in doors:
        found = doorway_for(plan, place, metres, sill, lead, left, along)
        if found is None:
            continue
        left.remove(found)
        if abs(float(found[1]["wide"]) - metres) > 1e-6:
            fixes.append(f"{words}: its doorway at {found[1]['at']} {float(found[1]['wide']):g} m wide made its door "
                         f"row's {metres:g} m")
            found[1]["wide"] = metres
    return fixes


INSIDE_STEP = 0.025  # metres between the offsets tried when a thing is moved inside its outline


INSIDE_SLACK = 0.001  # metres a moved thing's corners are tested inside the outline by (an edge point is not inside)


def offsets(reach):
    """The offsets [dx, dy] of INSIDE_STEP within `reach` metres, nearest first."""
    steps = numpy.arange(-math.ceil(reach / INSIDE_STEP), math.ceil(reach / INSIDE_STEP) + 1) * INSIDE_STEP
    found = numpy.stack(numpy.meshgrid(steps, steps), axis=-1).reshape(-1, 2)
    found = found[numpy.hypot(found[:, 0], found[:, 1]) <= reach + 1e-9]
    return found[numpy.argsort(numpy.hypot(found[:, 0], found[:, 1]), kind="stable")]


def moved_inside(box, outer, outline, reach):
    """`box` [x, y, w, d] moved the least distance that lays it wholly inside `outline`, its size counted: clamped into
    the plan's box `outer` [0, 0, w, d] first (the least move there), then the nearest offset of INSIDE_STEP from it
    that lies inside the outline too (a round or cut-cornered one); None when no move within `reach` metres does."""
    wide, deep = box[2:]
    x = min(max(box[0], outer[0]), outer[0] + outer[2] - wide)
    y = min(max(box[1], outer[1]), outer[1] + outer[3] - deep)
    corners = numpy.array([[x + INSIDE_SLACK, y + INSIDE_SLACK], [x + wide - INSIDE_SLACK, y + INSIDE_SLACK],
                           [x + wide - INSIDE_SLACK, y + deep - INSIDE_SLACK], [x + INSIDE_SLACK, y + deep - INSIDE_SLACK]])
    for chunk in numpy.array_split(offsets(reach), max(1, int(reach / INSIDE_STEP) // 20)):
        laid = (corners[None, :, :] + chunk[:, None, :]).reshape(-1, 2)
        fits = plan_checks.inside(laid, outline).reshape(len(chunk), 4).all(axis=1)
        if fits.any():
            step = chunk[numpy.argmax(fits)]
            return [round(x + float(step[0]), 3), round(y + float(step[1]), 3), wide, deep]
    return None


def frame_inside(plan):
    """The fixes said of a frame whose anchor or toward lies outside the plan's own box, the frame dropped (the plan
    then stands unturned, its middle on the place's floor: scene_record/plan.frame_of): it was set in another plan's
    metres. The Square's writing of 2026-10-21 took the retired 120 x 110 m creator plan (data/plans/square.json, gone
    in eb01c402) as its skeleton, and plan_writing.measured gave it the drawing's 28.989 m box but kept that plan's
    frame, its anchor at [60, 3] and its toward at [60, 47.05]; today's skeleton (plans.base_plan) has none."""
    from score.stages.scene_record.plan import EDGE
    frame = plan.get("frame") or {}
    off = [key for key in ("anchor", "toward") if (frame.get(key) or {}).get("plan") is not None
           and not (-EDGE <= float(frame[key]["plan"][0]) <= plan["w"] + EDGE
                    and -EDGE <= float(frame[key]["plan"][1]) <= plan["d"] + EDGE)]
    if not off:
        return []
    plan.pop("frame")
    return [f"its frame's {' and '.join(f'{key} {frame[key]['plan']}' for key in off)} lay outside its "
            f"{plan['w']:g} x {plan['d']:g} m plan, set in another plan's metres: dropped, the plan stands unturned"]


def items_inside(plan):
    """The fixes said of each item the plan row's gate finds past the plan's own box (scene_record/plan.item_inside; a
    passage drawn past it stands outside by design), moved the least distance that lays it wholly inside its outline,
    its size counted: a run longer than the box's side clipped to it first (the garage's 10 m pipes drawn 5 m past its
    west wall, the hub's monitors past its east wall, 2026-11-04). One no move lays inside is left, the gate names it."""
    from score.stages.scene_record.plan import PASSAGE_WORDS, item_inside
    outer = [0.0, 0.0, float(plan["w"]), float(plan["d"])]
    outline = plan_checks.outline_of(plan)
    fixes = []
    for item in plan.get("items") or []:
        if set(re.findall(r"[a-z]+", str(item[0]).lower())) & PASSAGE_WORDS or item_inside(item, outer):
            continue
        box = [float(value) for value in item[1:5]]
        clipped = [min(box[2], outer[2]), min(box[3], outer[3])]
        moved = moved_inside([*box[:2], *clipped], outer, outline, math.hypot(outer[2], outer[3]))
        if moved is None:
            continue
        said = (f"clipped from {box[2]:g} x {box[3]:g} m to {clipped[0]:g} x {clipped[1]:g} m and "
                if clipped != box[2:] else "")
        item[1:5] = moved
        fixes.append(f"{plan_checks.said_name(item[0])}: {said}moved {math.dist(box[:2], moved[:2]):.2f} m inside "
                     f"the plan's outline")
    return fixes


def people_inside(plan, inventory):
    """The fixes said of each person spot the plan row's gate finds past the plan's own box, moved to the nearest floor
    inside its outline where its footprint lies wholly inside and stands in nothing (standing.nearest_free): the
    galley's third spot at x 5.72 in its 4.64 m, the garage's eighth at y 14.29 in its 12.66 m (2026-11-04). A spot
    of a row beyond or afar stands out there on purpose; one with no such floor is left, the gate names it."""
    from score.review import standing
    from score.stages.scene_record.plan import EDGE
    spots = plan.get("people") or []
    rows = {row["id"]: row for row in inventory.get("rows", [])}
    left_out = plan_checks.beyond(plan, inventory) | plan_checks.afar(inventory)
    grid = plan_checks.Grid(plan)
    inside = grid.covered(plan_checks.outline_of(plan))
    sizes, fixes = standing.footprints(plan, inventory), []
    for number, (spot, size) in enumerate(zip(spots, sizes)):
        row = spot[3] if len(spot) >= 4 and isinstance(spot[3], str) and spot[3] in rows else None
        if row in left_out or (-EDGE <= float(spot[0]) <= plan["w"] + EDGE and -EDGE <= float(spot[1]) <= plan["d"] + EDGE):
            continue
        walls_things = standing.blocked(plan, inventory, grid, plan_checks.anchor_of(rows[row]) if row else None)
        others = [(other, other_size) for other, other_size in zip(spots, sizes) if other is not spot]
        free = standing.nearest_free(spot, size, walls_things | ~inside, grid, inside, others)
        if free is None:
            continue
        spots[number] = [*free, *spot[2:]]
        fixes.append(f"{plan_checks.said_name(row or 'a standing spot')}: its spot {spot[:2]} moved "
                     f"{math.dist(spot[:2], free):.2f} m inside the plan's outline")
    return fixes


def kept_inside(plan, inventory):
    """The fixes said of what the plan lays past its own outline brought inside it (the plan row's gate `held`): a frame
    in another plan's metres dropped (`frame_inside`), each item moved in (`items_inside`), then each person spot
    (`people_inside`, clear of the items as moved)."""
    return frame_inside(plan) + items_inside(plan) + people_inside(plan, inventory)


def tied(plan, answered):
    """The corrected items kept: well formed, each tied to its row (a new one by its name's row) and shape."""
    rows, shapes = dict(plan.get("rows", {})), dict(plan.get("shapes", {}))
    ids = {row for found in rows.values() for row in found}
    items = []
    for item in answered if isinstance(answered, list) else []:
        if not (isinstance(item, list) and len(item) >= 7 and isinstance(item[0], str)
                and all(isinstance(value, (int, float)) for value in item[1:5]) and item[3] > 0 and item[4] > 0):
            continue
        row = rows.get(item[0]) or ([item[0].rsplit(" ", 1)[0].lower().replace(" ", "_")]
                                    if item[0].rsplit(" ", 1)[0].lower().replace(" ", "_") in ids else None)
        if row is None:
            continue
        rows[item[0]] = row
        items.append([item[0], *[round(float(value), 3) for value in item[1:5]],
                      item[5] if item[5] in FACINGS else None, item[6]])
    return items, rows, shapes
