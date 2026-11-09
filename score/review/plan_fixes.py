"""The automatic fixes of a written plan (owner, 2026-10-21: "if u can detect these ... then why dont u just fix them,
gaps should only show things that cant be fixed auto"), run after every plan writing (plan_writing.written_one) and
before it is shown; his own edits are never touched, and no inside place's room moves (a locked scene's room stays
where its draw was drawn: plans.locked_rooms_kept).

First the free fixes (`fixed`), each a check of plan_checks with one answer: a row marked beyond that stands at the
concept's foot brought in (plan_checks.beyond: the airlock's sandbags); every people row stood as person spots
(plan["people"], [x, y, None, row], first: the cast stands on them), where its SAM boxes project onto the plan; a
counted box of things drawn apart split into its things along the drawing's spread; a row placed fewer times than the
concept counts given its missing things where their boxes project; a thing facing another way than the concept shows
turned to the concept's way; two floor things standing in each other nudged apart the shortest way out, inside the
walls. The projection (`projector`) is fitted on the rows boxed on the concept as many times as they are laid on the
plan (`anchors`, on the floor or on the shell's floor rows), their boxes' middle across and foot to their middle on
the plan.

Then what is still open goes to the prompt model as the notes of one automatic Correct (`corrected`, as the plan
page's, under the plan-writing allowance, its cost kept with the writing), the free fixes run again on its answer, and
it is kept only when fewer gaps are left; at most CORRECTIONS times. What is left is a gap, saying why (`why_left`).

    python -m score.review.plan_fixes <place> ...   # fix the written plans shown now, each a new writing kept
"""
import argparse
import copy
import io
import json
import math
import re
import sys

import numpy

from score.review import concepts, holders, plan_checks, plans, standing
from score.stages.earth_seed import design_shell

CORRECTIONS = 2  # automatic Correct calls at most, each kept only when it leaves fewer gaps
NUDGE_ROUNDS = 4  # passes over the overlaps, each moving the smaller thing of a pair
MARGIN = 0.05  # metres left between two things nudged apart
RUN_SHARE = 3  # a thing on a wall this many times longer than it is deep is a run (a pipe), cut at a corner
FLIGHT_REACH = 3.0  # metres a stair or ramp is moved out of a thing made larger than drawn at most
SPREAD_LEAST = 0.5  # metres the rows a projection is fitted on must lay their things' middles apart at least
FACINGS = ("N", "E", "S", "W")
# The corrected plan's schema, the keys `corrected` reads: its items, each [name, x, y, w, d, facing, kind] (a name or
# word, else a number), and its standing spots [x, y]; the API holds the answer to it (ai.google.dev structured output).
CORRECTED = {"type": "OBJECT", "required": ["items", "people"], "propertyOrdering": ["items", "people"],
             "properties": {"items": {"type": "ARRAY", "items": {"type": "ARRAY", "items": {
                 "anyOf": [{"type": "STRING"}, {"type": "NUMBER"}], "nullable": True}}},
                 "people": {"type": "ARRAY", "items": {"type": "ARRAY", "items": {"type": "NUMBER"}}}}}
WHY = {  # what a gap left after the fixes says: why no fix of it took
    "placed": "no box of it on the concept projects onto the plan, and the correction did not place it",
    "people": "no box of them on the concept projects onto the plan",
    "overlap": "no free floor inside the walls to move either to, and the correction did not part them",
    "outside": "the correction did not bring it inside",
    "arrangement": "the correction did not lay it the concept's way",
    "reach": "the correction did not clear a way to it",
    "tiling": "inside places are never moved by the fixes",
    "joined": "the correction did not join it",
    "stacked": "no wall the holders would lay it against is free of its row's runs",
    "flight": "no floor of its level holds it as made clear of the stairs",
}


# --- the projection from the concept onto the plan ---------------------------------------------------------------

def projector(plan, inventory):
    """A function from a SAM box (pixels of the concept) to its spot [x, y] on the plan, inside its outline box
    (`projection`); None with fewer than three rows to fit it on, or when their spots on the plan all lie within
    SPREAD_LEAST of their middle: such a fit sends every box to that one spot (the engine room's grating, doors and
    windows, each laid round the room's middle, so all three at it: its four missing railings were laid on one spot
    and piled 1 to 4 m, 2026-11-06)."""
    matrix = plan_checks.projection(plan, inventory)
    spots = numpy.array([spot for _, spot in plan_checks.projection_anchors(plan, inventory)], dtype=float)
    if matrix is None or float(numpy.linalg.norm(spots - spots.mean(axis=0), axis=1).max()) < SPREAD_LEAST:
        return None
    wide, high = inventory["picture"]

    def project(box):
        spot = numpy.array([(box[0] + box[2]) / 2 / wide, box[3] / high, 1.0]) @ matrix
        return [round(min(max(float(spot[0]), 0.0), plan["w"]), 3), round(min(max(float(spot[1]), 0.0), plan["d"]), 3)]
    return project


# --- the free fixes ------------------------------------------------------------------------------------------------

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


def stood_people(plan, inventory, project):
    """Every people row but a crowd stood as person spots where its boxes project (its items taken off: a person is
    no furniture), first among the plan's standing spots; the fixes said."""
    rows = plan_checks.person_rows(inventory)
    if not rows:
        return []
    ids = {row["id"] for row in rows}
    found = [spot for spot in plan.get("people", []) if not (len(spot) >= 4 and spot[3] in ids)]
    stood, fixes = [], []
    for row in rows:
        laid = [item for item, row_id, _ in plan_checks.placed_items(plan) if row_id == row["id"]]
        spots = ([project(box) for box in plan_checks.boxes_of(row)] if project else []) or [
            [round(item[1] + item[3] / 2, 3), round(item[2] + item[4] / 2, 3)] for item in laid]
        for item in laid:
            dropped_item(plan, item)
        stood += [[*spot, 0.0, row["id"]] for spot in spots]  # on the plan's own floor
        if spots:
            fixes.append(f"{plan_checks.said_name(row['id'])}: stood as {len(spots)} person spot"
                         f"{'s' if len(spots) > 1 else ''} where the concept shows them")
    plan["people"] = stood + found
    return fixes


def spread_spots(box, count, size):
    """`count` middles of things of `size` spread over a run's `box` [x, y, w, d]: round its edge when the box is
    much larger than a thing both ways (trees round a plaza), else along its longer side."""
    x, y, wide, deep = box
    if wide > 3 * size[0] and deep > 3 * size[1]:
        edge = 2 * (wide + deep - size[0] - size[1])
        spots = []
        for number in range(count):
            way = edge * number / count
            left, top, right, bottom = x + size[0] / 2, y + size[1] / 2, x + wide - size[0] / 2, y + deep - size[1] / 2
            for start, end in (((left, top), (right, top)), ((right, top), (right, bottom)),
                               ((right, bottom), (left, bottom)), ((left, bottom), (left, top))):
                length = math.dist(start, end)
                if way <= length or (start, end) == ((left, bottom), (left, top)):
                    share = way / length if length else 0.0
                    spots.append([start[0] + (end[0] - start[0]) * share, start[1] + (end[1] - start[1]) * share])
                    break
                way -= length
        return spots
    along = wide >= deep
    step = (wide if along else deep) / count
    return [[x + step * (number + 0.5), y + deep / 2] if along else [x + wide / 2, y + step * (number + 0.5)]
            for number in range(count)]


def split_runs(plan, inventory, project):
    """Each counted box of things drawn apart (plan_checks.run_gaps) split into its things: where its row's boxes
    project when they are as many, else spread over the box; the fixes said."""
    by_id, fixes = {row["id"]: row for row in inventory.get("rows", [])}, []
    for gap in plan_checks.run_gaps(plan, inventory):
        item = next((item for item in plan["items"] if item[0] == gap["item"]), None)
        if item is None:
            continue
        shape = plan.get("shapes", {}).get(item[0]) or {}
        count, row = int(shape.get("count") or 1), by_id[gap["row"]]
        size = [min(float(row["size"][0]), item[3]), min(float(row["size"][1]), item[4])]
        boxes = plan_checks.boxes_of(row)
        spots = ([project(box) for box in boxes] if project and len(boxes) == count else
                 spread_spots(item[1:5], count, size))
        dropped_item(plan, item)
        for spot in spots:
            added_item(plan, row["id"], spot, size, shape)
        fixes.append(f"{plan_checks.said_name(gap['item'])}: split into its {count} things")
    return fixes


# A row's words that say its things pile on one another (holders.PILE_WORDS, held equal by the test).
PILE_WORDS = {"pile", "piles", "piled", "stack", "stacks", "stacked", "heap", "heaps", "heaped"}


def piles(row):
    """Whether a row's things pile on one another: a PILE_WORDS word in its id, name, noun, where or size words."""
    return bool(PILE_WORDS & set(re.findall(r"[a-z]+", " ".join(
        str(row.get(key) or "") for key in ("id", "name", "noun", "where", "size_words")).replace("_", " ").lower())))


def piled(plan, row, box, tall):
    """The base a new thing of `row` with footprint `box` [x, y, w, d] stands at: for a row whose things pile (piles:
    airlock's sandbags, "knee high pile", crossed by 5 to 25 cm, 2026-10-30) on the highest thing of its row whose
    footprint it crosses, else 0, on the floor, the overlap left to nudged (2026-11-06: the engine room's railings 5
    to 8 piled 1 to 4 m over one another). `tall` is the row's, for a thing whose shape gives none."""
    return max([float((shape or {}).get("base") or 0.0) + float((shape or {}).get("tall") or tall)
                for item, row_id, shape in plan_checks.placed_items(plan)
                if row_id == row["id"] and overlapping(box, item[1:5])], default=0.0) if piles(row) else 0.0


def placed_missing(plan, inventory, project):
    """Each row on the floor placed fewer times than the concept counts given its missing things where its boxes
    project, those nearest a thing already laid taken as that one's; a thing of a row that piles whose footprint
    crosses one of its row's piled on it (piled), never standing in it; the fixes said."""
    if project is None:
        return []
    fixes, short = [], {gap["row"] for gap in plan_checks.count_gaps(plan, inventory, set(plan.get("structure", [])))}
    for row in inventory.get("rows", []):
        if row["id"] not in short or not isinstance(row.get("size"), list):
            continue
        laid = [(item, shape) for item, row_id, shape in plan_checks.placed_items(plan) if row_id == row["id"]]
        placed = sum(int((shape or {}).get("count") or 1) for _, shape in laid)
        spots = [project(box) for box in plan_checks.boxes_of(row)]
        for item, shape in laid:  # each laid thing takes the spots nearest it, as many as it counts
            middle = [item[1] + item[3] / 2, item[2] + item[4] / 2]
            for _ in range(int((shape or {}).get("count") or 1)):
                if spots:
                    spots.remove(min(spots, key=lambda spot: math.dist(spot, middle)))
        missing = max(0, int(row.get("count", 1) or 1) - placed)
        like = laid[0][1] if laid else None
        size = [float(row["size"][0]), float(row["size"][1])]
        added = []
        for spot in spots[:missing]:
            base = piled(plan, row, [spot[0] - size[0] / 2, spot[1] - size[1] / 2, *size],
                         float(row["size"][2]) if len(row["size"]) > 2 else 0.0)
            added.append(added_item(plan, row["id"], spot, size, like))
            if base:
                plan["shapes"][added[-1]]["base"] = round(base, 3)
        if added:
            fixes.append(f"{plan_checks.said_name(row['id'])}: {len(added)} more placed where the concept shows them")
    return fixes


def faced(plan, inventory):
    """Each thing facing another way than the concept shows turned the concept's way; the fixes said."""
    _, _, turn = plan_checks.viewed(plan, inventory)
    fixes = []
    for item, _, shape in plan_checks.placed_items(plan):
        seen = (shape or {}).get("seen")
        if item[5] in FACINGS and seen and plan_checks.facing_word(item[5], turn) not in seen:
            facing = next((facing for word in seen for facing in FACINGS
                           if plan_checks.facing_word(facing, turn) == word), None)
            if facing:
                item[5] = facing
                fixes.append(f"{plan_checks.said_name(item[0])}: turned to face {'-'.join(seen)} as in the concept")
    return fixes


def overlapping(box, other):
    """Whether two boxes [x, y, w, d] share any floor."""
    return box[0] < other[0] + other[2] and other[0] < box[0] + box[2] and box[1] < other[1] + other[3] \
        and other[1] < box[1] + box[3]


def way_out(mover, still, plan, others):
    """The shortest step [dx, dy] that takes `mover`'s box out of `still`'s, inside the outline and into no box of
    `others`; None when there is none."""
    box, other = mover[1:5], still[1:5]
    steps = [[other[0] + other[2] - box[0] + MARGIN, 0.0], [other[0] - box[0] - box[2] - MARGIN, 0.0],
             [0.0, other[1] + other[3] - box[1] + MARGIN], [0.0, other[1] - box[1] - box[3] - MARGIN]]
    outline = plan_checks.outline_of(plan)
    for step in sorted(steps, key=lambda step: abs(step[0]) + abs(step[1])):
        moved = [box[0] + step[0], box[1] + step[1], box[2], box[3]]
        corners = numpy.array([[moved[0], moved[1]], [moved[0] + moved[2], moved[1]],
                               [moved[0] + moved[2], moved[1] + moved[3]], [moved[0], moved[1] + moved[3]]])
        if plan_checks.inside(corners, outline).all() and not any(overlapping(moved, rest) for rest in others):
            return step
    return None


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


def taken_floor(plan, inventory, item, grid):
    """The grid cells `item` may not stand on: under another floor thing (on the floor, or on a floor the place lays:
    `floored`), a wall, a stair or a thing standing low by a wall (`standing_low`)."""
    on_floor = floored(plan, inventory)
    taken = numpy.zeros(grid.shape, dtype=bool)
    for other, _, shape in plan_checks.blocking(plan, on_floor):
        if other is not item:
            taken |= grid.covered(plan_checks.polygon_of(other, shape))
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


def stack_gaps(plan, inventory):
    """A gap for each two runs of one row lying in each other on one wall (wall_runs, in_each_other)."""
    gaps = []
    for row, runs in wall_runs(plan, inventory).items():
        for number, run in enumerate(runs):
            for other in runs[number + 1:]:
                if in_each_other(run, other):
                    box = run[0][1:5]
                    gaps.append({"kind": "stacked", "item": run[0][0], "row": row, "with": other[0][0],
                                 "at": [round(box[0] + box[2] / 2, 2), round(box[1] + box[3] / 2, 2)],
                                 "words": f"{plan_checks.said_name(run[0][0])} and {plan_checks.said_name(other[0][0])} "
                                          "run along one stretch of one wall at one height"})
    return gaps


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


def flight_gaps(plan, inventory):
    """A gap for each thing left in a stair or ramp as made (on_flights)."""
    return [{"kind": "flight", "item": item[0], "row": (plan.get("rows", {}).get(item[0]) or [None])[0],
             "at": plan_checks.middle_of(made.tolist()),
             "words": f"{plan_checks.said_name(item[0])} stands on the stairs as made "
                      f"({numpy.ptp(made, axis=0).max():.1f} m across, drawn {max(item[3], item[4]):.2f} m)"}
            for item, made in on_flights(plan, inventory)]


def kept_apart(plan, inventory):
    """The fixes that keep what settle drops out of each other and out of the shell (env1 checkouts 67 and 68), in
    order: a roof's eave raised a storey over a level standing under it (`eaves_raised`), a stairs row taken off where
    the shell builds the flights (`stair_rows_dropped`), runs kept out of the walls and stairs (`runs_kept_clear`), a
    single thing laid again in its own row's run taken off (`run_doubles_dropped`), things piled on their own row's
    though it does not pile stood on the floor or taken off (`unpiled`), runs of one row in each other on a wall laid
    along walls free of them or taken off (`wall_runs_spread`), runs on a wall parted (`wall_runs_parted`), stairs and
    ramps moved out of what is made larger than drawn (`flights_cleared`), things made larger than drawn moved off the
    stairs or taken off (`off_flights`); the fixes said. A writing fixed before them gets them in the pass (plans_pass.unsettled), an edit
    or a redrawing when shown (plans.edit_inside)."""
    return eaves_raised(plan) + stair_rows_dropped(plan, inventory) + runs_kept_clear(plan, inventory) \
        + run_doubles_dropped(plan, inventory) + unpiled(plan, inventory) + wall_runs_spread(plan, inventory) \
        + wall_runs_parted(plan, inventory) + flights_cleared(plan, inventory) + off_flights(plan, inventory)


def nudged(plan, inventory):
    """Two floor things standing in each other (plan_checks.overlap_gaps) parted: the smaller moved the shortest way
    out, inside the walls and into nothing else (no floor thing, no thing standing low by a wall, no wall, no stair);
    the fixes said."""
    fixes, clear = [], walls_and_stairs(plan)
    for _ in range(NUDGE_ROUNDS):
        found = plan_checks.overlap_gaps(plan, inventory, plan_checks.Grid(plan))
        moved_any = False
        for gap in found:
            items = {item[0]: item for item in plan["items"]}
            pair = [items.get(gap["item"]), items.get(gap["with"])]
            if None in pair:
                continue
            mover, still = sorted(pair, key=lambda item: item[3] * item[4])
            floor = {item[0] for item, *_ in plan_checks.blocking(plan, inventory)}
            others = [item[1:5] for item in plan["items"] if item[0] in floor and item[0] not in (mover[0], still[0])]
            others += [box for box in standing_low(plan, inventory, mover) if box != still[1:5]] + clear
            step = way_out(mover, still, plan, others)
            if step:
                mover[1], mover[2] = round(mover[1] + step[0], 3), round(mover[2] + step[1], 3)
                moved_any = True
                fixes.append(f"{plan_checks.said_name(mover[0])}: moved {math.hypot(*step):.1f} m out of "
                             f"{plan_checks.said_name(still[0])}")
        if not moved_any:
            break
    return fixes


def brought_in(plan, inventory):
    """The rows the plan marks beyond that stand at the picture's foot (plan_checks.beyond) taken off its `beyond`,
    so the free fixes place them where their boxes project; the fixes said."""
    kept = plan_checks.beyond(plan, inventory)
    moved = [row for row in plan.get("beyond", []) if row not in kept]
    plan["beyond"] = [row for row in plan.get("beyond", []) if row in kept]
    return [f"{plan_checks.said_name(row)}: at the concept's foot, so on this place's ground, not beyond it"
            for row in moved]


# A door row's doorway stands within this of its bearing, degrees; the kinds of opening a person walks through.
BEARING_REACH = 30.0
DOORWAY_KINDS = ("door", "gate", "opening")
SIDE_ANGLES = {"N": 0.0, "E": 90.0, "S": 180.0, "W": 270.0}
SIDE_WAYS = {"N": (0.0, -1.0), "S": (0.0, 1.0), "E": (1.0, 0.0), "W": (-1.0, 0.0)}
DOOR_SIZE = re.compile(r"\d+(?:\.\d+)? ?x ?(\d+(?:\.\d+)?) ?m")  # a door row's words "(0.9 x 2.0 m)": its height
DOOR_HEAD = 2.1  # metres of a cut doorway's head its words give none (design_shell.DOOR_HEAD)


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


def on_outline(plan, point):
    """The point of the plan's outline nearest a plan point."""
    outline = numpy.asarray(plan_checks.outline_of(plan), float)
    best = None
    for start, end in zip(outline, numpy.roll(outline, -1, axis=0)):
        run = end - start
        near = start + run * float(numpy.clip((point - start) @ run / max(float(run @ run), 1e-9), 0.0, 1.0))
        if best is None or float(numpy.linalg.norm(near - point)) < float(numpy.linalg.norm(best - point)):
            best = near
    return best


def side_spot(plan, side, along, metres):
    """Where a door row [side, along, metres] stands: `along` its side (from its west or north end, kept its half
    width inside it), on the plan's outline."""
    length = float(plan["w"] if side in ("N", "S") else plan["d"])
    along = min(max(float(along), metres / 2), max(length - metres / 2, metres / 2))
    point = {"N": [along, 0.0], "S": [along, float(plan["d"])], "W": [0.0, along], "E": [float(plan["w"]), along]}[side]
    return [round(float(value), 3) for value in on_outline(plan, numpy.asarray(point, float))]


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


def doors_kept(plan, inventory):
    """Every doorway of the plan the design's door rows say (2026-11-04 audit: the drawing's openings, Gemini's answer
    scaled, came out 0.2 to 5 m wide against 1 to 2.2 m door rows, on other walls, more or fewer): each door row's
    doorway (on its side and sill, at its bearing, else where it leads) its metres wide and leading where its lead
    does, the drawing kept only for where along its wall it stands; a side door row with none there moves the
    doorway left over that leads where it does, else any left over, to its side at its along, else one is cut there;
    the doorways no door row is dropped, where the plan has door rows; the fixes said."""
    doors = [door_of(plan, door) for door in plan.get("doors") or [] if isinstance(door, list) and len(door) >= 3]
    if not doors:
        return []
    openings, fixes = plan.setdefault("openings", []), []
    left = [(number, opening) for number, opening in enumerate(openings) if opening.get("kind") in DOORWAY_KINDS]
    unmet = []
    for place, metres, words, sill, along, lead in doors:
        found = doorway_for(plan, place, metres, sill, lead, left, along)
        if found is None:
            unmet.append((place, metres, words, sill, along, lead))
            continue
        left.remove(found)
        opening = found[1]
        if abs(float(opening["wide"]) - metres) > 1e-6 or (lead is not None and opening.get("to") != lead):
            fixes.append(f"{words}: its doorway {float(opening['wide']):g} m wide to {opening.get('to')!r} made "
                         f"its door row's {metres:g} m to {lead!r}")
            opening.update(wide=metres, **({"to": lead} if lead is not None else {}))
    for place, metres, words, sill, along, lead in unmet:
        if place not in SIDE_WAYS:
            fixes.append(f"{words}: no doorway at its {place} and none moved there (only a side door row is)")
            continue
        spare = next((pair for pair in left if lead is not None and pair[1].get("to") == lead), None) or (
            left[0] if left else None)
        head = DOOR_SIZE.search(words)
        opening = spare[1] if spare else {"kind": "door", "swing": "none",
                                          "head": round((sill or 0.0) + (float(head.group(1)) if head else
                                                                         DOOR_HEAD), 3)}
        if spare:
            left.remove(spare)
        else:
            openings.append(opening)
        opening.update(at=side_spot(plan, place, along, metres), wide=metres, angle=SIDE_ANGLES[place],
                       sill=opening.get("sill", sill or 0.0) if sill is None else sill,
                       **({"to": lead} if lead is not None else {"to": opening.get("to")}))
        fixes.append(f"{words}: its doorway {'moved' if spare else 'cut'} to its {place} side at {along}")
    for number, opening in sorted(left, reverse=True):
        openings.pop(number)
        fixes.append(f"the doorway at {opening['at']} to {opening.get('to')!r}: no door row of the plan, dropped")
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


# --- what lies past its own outline (the plan row's gate `held`, scene_record/plan.inside_faults) ---------------------

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


def fixed(plan, inventory):
    """(the plan with every free fix made, the fixes said): rows at the concept's foot brought in from beyond, people
    stood, runs split, missing things placed, facings turned, runs kept out of walls and stairs, things piled on their
    own row's though it does not pile stood on the floor or taken off, one row's runs in each other on a wall laid along
    free walls, runs on a wall parted, stairs and ramps moved out of what is made larger than drawn, overlaps parted, in
    that order (each later one on the earlier's plan), then what lies past its own outline brought inside it."""
    plan = copy.deepcopy(plan)
    fixes = brought_in(plan, inventory)
    project = projector(plan, inventory)
    fixes += stood_people(plan, inventory, project) + split_runs(plan, inventory, project)
    fixes += placed_missing(plan, inventory, project) + faced(plan, inventory) + kept_apart(plan, inventory)
    fixes += nudged(plan, inventory)
    fixes += doors_kept(plan, inventory) + kept_inside(plan, inventory)
    return plan, fixes


# --- what is left: the automatic Correct --------------------------------------------------------------------------

def open_gaps(plan, inventory):
    """The plan's gaps by today's free checks, runs left in each other on a wall (stack_gaps) and things left on the
    stairs as made (flight_gaps), its inside places not laid out kept as written."""
    return [gap for gap in plan.get("gaps", []) if gap["kind"] == "place"] + plan_checks.checked(
        plan, inventory, plan.get("structure", [])) + stack_gaps(plan, inventory) + flight_gaps(plan, inventory)


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


def corrected(store, place, plan, left, ask):
    """One automatic Correct of `plan` by the gaps `left` as its notes (the plan page's question, plans.plan_question),
    the drawn plan and the locked concept sent; (the corrected plan, its call {model, asked, answered, euros}). Its
    size, rooms and doors stay; Refused when it answers no plan."""
    from PIL import Image

    from score.review import plan_writing, reading
    note = ("Fix these problems the free checks found, each where it is, and change nothing else: "
            + "; ".join(gap["words"] for gap in left))
    question = plans.plan_question(plan, [], [], note)
    pro, _, _ = concepts.tools()
    concept = Image.open(io.BytesIO(store.objects.read_bytes(f"blobs/{plans.pick_of(store, place)}")))
    body = {"contents": [{"role": "user", "parts": [{"text": question}] + [
        pro.part(picture, concepts.LONGEST_SENT) for picture in (plans.drawn(plan), concept)]}],
        "generationConfig": {"temperature": 0, "responseMimeType": "application/json", "responseSchema": CORRECTED}}
    response, _ = ask(body)
    answered = reading.answer_text(response)
    call = {"model": plan_writing.MODEL, "asked": note, "answered": answered,
            "euros": plan_writing.call_euros(response)}
    found = plans.answered_plan(answered)
    items, rows, shapes = tied(plan, found.get("items"))
    if not items:
        raise plans.Refused("the correction answered no items")
    zones = [item for item in plan["items"] if item[6] == "zone"]
    people = [spot for spot in found.get("people") or [] if isinstance(spot, list) and len(spot) >= 2
              and all(isinstance(value, (int, float)) for value in spot[:2])]
    return {**plan, "items": [item for item in items if item[6] != "zone"] + zones, "rows": rows,
            "shapes": shapes, "people": people or plan.get("people", [])}, call


def why_left(gaps):
    """Each gap left after the fixes, saying why no fix of it took."""
    return [{**gap, "words": f"{gap['words']}: {WHY[gap['kind']]}"} if gap["kind"] in WHY and ": " + WHY[gap["kind"]]
            not in gap["words"] else gap for gap in gaps]


def settled(store, place, plan, inventory, ask):
    """(the plan with the free fixes made and up to CORRECTIONS automatic Corrects kept, each only when it left fewer
    gaps, its gaps what is left, each saying why, and `fixes` what was fixed; the Correct calls made)."""
    plan, fixes = fixed(plan, inventory)
    calls = []
    for _ in range(CORRECTIONS):
        left = open_gaps(plan, inventory)
        if not [gap for gap in left if gap["kind"] != "place"]:
            break
        try:
            answer, call = corrected(store, place, plan, left, ask)
        except (plans.Refused, concepts.Refused, ValueError) as refused:
            calls.append({"refused": str(refused)[:200]})
            break
        calls.append(call)
        answer, more = fixed(answer, inventory)
        if len(open_gaps(answer, inventory)) >= len(left):
            break
        plan, fixes = answer, fixes + [f"the prompt model corrected {len(left)} gaps"] + more
    plan["fixes"] = fixes
    plan["gaps"] = why_left(open_gaps(plan, inventory))
    return plan, calls


# --- the plans written before the fixes --------------------------------------------------------------------------

def fix_written(store, places, by, ask=None):
    """Fix the written plan shown of each of `places` (its newest writing in force, unless fixed already), each kept
    as a new writing of the same lock, reading and method with its fixes and the cost of its Correct calls; the
    records."""
    from score.review import plan_writing
    found = []
    for place in places:
        writing = plan_writing.written_of(store, place)
        if not writing or "fixes" in writing["plan"]:
            continue
        plan, calls = settled(store, place, writing["plan"], plans.inventory_of(store, place),
                              ask or plan_writing.asked)
        euros = round(sum(call.get("euros", 0.0) for call in calls), 6)
        found.append(plan_writing.kept(store, {
            **{key: writing[key] for key in ("place", "concept", "reading", "method", "drawing", "measured")
               if key in writing}, "by": by, "at": concepts.now(), "euros": euros, "drawing_euros": 0.0,
            "fixed_from": writing["at"], "calls": calls, "plan": plan}))
    return found


def main(argv):
    """Fix the places named under the plan-writing allowance; one line a place."""
    from score.adapters import compute
    from score.review import plan_writing
    from score.store import Store
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("places", nargs="+")
    parser.add_argument("--by", default="the owner's standing allowance")
    options = parser.parse_args(argv)
    store = Store.default()
    euros = round(0.2 * CORRECTIONS * len(options.places), 2)
    with plan_writing.cleared(store, options.places, euros):
        compute.require_cleared("a plan writing", store)
        for record in fix_written(store, options.places, options.by):
            print(json.dumps({"place": record["place"], "fixes": len(record["plan"]["fixes"]),
                              "gaps left": len(record["plan"]["gaps"]), "euros": record["euros"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
