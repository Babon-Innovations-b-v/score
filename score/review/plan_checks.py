"""The free checks on a written plan (CONTEXT.md "plan"; score/review/plan_writing.py), each failure a named gap of the
plan, never guessed past: every inventory row placed once (as many items as it counts), every item inside the
outline, no two items on the floor overlapping (a row on another row, and a row on a wall or the ceiling, excepted),
every door and standing spot reachable on foot from the others, and the inside places tiling the outline without
overlap. Measured on a grid of the plan (`Grid`): an item's footprint is its shape (`footprint`), the walls block,
their openings do not."""
import collections
import math
import re

import numpy

CELLS = 400  # grid cells along the plan's longer side
FINEST = 0.05  # metres: no cell is smaller
OUTSIDE = 0.2  # an item is outside the outline when more than this share of it is
OVERLAP = 0.15  # two items overlap when they share more than this share of the smaller one
STEP_IN = 0.6  # metres a door's seed is moved into the place before it is looked for
NEAREST = 1.0  # metres a blocked seed may look for a free cell
LOW = 0.5  # metres: an item standing higher than this (its base) does not block the floor
FLAT = 0.15  # metres: an item no taller than this lies flat on the floor, under the rest
ROUND = 24  # sides of a circle's polygon
FLOOR_ANCHORS = ("floor", "ground")
WALLS_ITEM = "ON THE WALLS AND CEILING"
PEOPLE = {"person", "people", "crowd", "man", "woman", "child", "figure", "pedestrian", "astronaut", "worker"}
AFAR = {"distant", "far", "background", "faraway"}
CROWD = {"crowd", "crowds", "audience", "spectators"}  # a people row the cast stands as a far crowd, no spots
KINDS = ("placed", "people", "outside", "overlap", "reach", "tiling", "arrangement", "joined")  # the gaps' kinds
# The arrangement against the concept: two rows' order counts where clear in both, the concept's as shares of its
# picture, the plan's as a share of its reach; left and right only for rows at about one depth (perspective).
SAME_DEPTH = 0.12
CLEAR_SEEN = 0.06
CLEAR_LAID = 0.08
TURNS = 5  # degrees between the viewer's ways tried
FRAME_APART = 0.25  # share of the view a row's place across it may differ by between the concept and the plan
CONNECTORS = {"tube", "tubes", "tunnel", "corridor", "walkway", "bridge", "passage", "connector", "link"}
JOIN_SEEN = 0.01  # share of the picture two boxes may stand apart and still meet in the concept
JOIN_LAID = 1.0  # metres a connector may stand from a part and still meet it on the plan
SPREAD = 4.0  # times its things' footprints side by side a run's box may cover before it is things drawn apart
SPREAD_SLACK = 4.0  # square metres more than its things a run's box may always cover (a small run's loose box)
# A box whose foot is within this share of the picture's height of its bottom edge reaches the picture's foot.
FOOT_SHARE = 0.01


def polygon_of(item, shape):
    """The footprint polygon [[x, y], ...] in plan metres of a legacy item [name, x, y, wide, deep, facing, kind] and
    its shape ({shape: rect | circle | polygon, points: [[u, v], ...] in 0..1 of the item's box}, None: rect)."""
    _, x, y, wide, deep, *_ = item
    kind = (shape or {}).get("shape", "rect")
    if kind == "circle":
        return [[x + wide / 2 + wide / 2 * math.cos(turn), y + deep / 2 + deep / 2 * math.sin(turn)]
                for turn in numpy.linspace(0, 2 * math.pi, ROUND, endpoint=False)]
    if kind == "polygon" and len(shape.get("points") or []) >= 3:
        return [[x + u * wide, y + v * deep] for u, v in shape["points"]]
    return [[x, y], [x + wide, y], [x + wide, y + deep], [x, y + deep]]


def outline_of(plan):
    """The plan's outline polygon: its `outline` when it has one, else its w x d box."""
    points = plan.get("outline") or []
    return points if len(points) >= 3 else [[0, 0], [plan["w"], 0], [plan["w"], plan["d"]], [0, plan["d"]]]


def wall_polygon(wall):
    """A straight wall {from, to, thick} as its polygon, or an arc wall {arc {centre, radius, start, end}, thick} as
    a band of ROUND pieces round it."""
    thick = float(wall.get("thick") or 0.2) / 2
    if "arc" in wall:
        arc = wall["arc"]
        turns = numpy.radians(numpy.linspace(float(arc["start"]), float(arc["end"]), ROUND))
        centre, radius = arc["centre"], float(arc["radius"])
        outer = [[centre[0] + (radius + thick) * math.cos(turn), centre[1] + (radius + thick) * math.sin(turn)]
                 for turn in turns]
        inner = [[centre[0] + (radius - thick) * math.cos(turn), centre[1] + (radius - thick) * math.sin(turn)]
                 for turn in turns[::-1]]
        return outer + inner
    (x1, y1), (x2, y2) = wall["from"], wall["to"]
    length = math.hypot(x2 - x1, y2 - y1) or 1.0
    across = [-(y2 - y1) / length * thick, (x2 - x1) / length * thick]
    return [[x1 + across[0], y1 + across[1]], [x2 + across[0], y2 + across[1]],
            [x2 - across[0], y2 - across[1]], [x1 - across[0], y1 - across[1]]]


def opening_polygon(opening):
    """An opening {at, wide, angle} as a box across its wall, wide along it and a metre through it."""
    turn = math.radians(float(opening.get("angle") or 0.0))
    along, across = [math.cos(turn), math.sin(turn)], [-math.sin(turn), math.cos(turn)]
    half, deep = float(opening["wide"]) / 2, 0.5
    x, y = opening["at"]
    return [[x + sign_a * half * along[0] + sign_b * deep * across[0],
             y + sign_a * half * along[1] + sign_b * deep * across[1]]
            for sign_a, sign_b in ((-1, -1), (1, -1), (1, 1), (-1, 1))]


def inside(points, polygon):
    """Which of `points` (N x 2) lie inside `polygon` (even-odd rule)."""
    found = numpy.zeros(len(points), dtype=bool)
    xs, ys = points[:, 0], points[:, 1]
    corners = numpy.asarray(polygon, dtype=float)
    for (x1, y1), (x2, y2) in zip(corners, numpy.roll(corners, -1, axis=0)):
        crosses = (y1 > ys) != (y2 > ys)
        with numpy.errstate(divide="ignore", invalid="ignore"):
            at = (x2 - x1) * (ys - y1) / (y2 - y1) + x1
        found ^= crosses & (xs < at)
    return found


class Grid:
    """The plan's floor as cells of `size` metres: their centres, and the cells a polygon covers (its centre in it, or
    for a polygon smaller than a cell, the cell under its middle)."""

    def __init__(self, plan):
        # over everything the plan lays, so a thing off the outline is counted off it
        corners = numpy.asarray(outline_of(plan) + [corner for item, _, shape in placed_items(plan)
                                                    for corner in polygon_of(item, shape)]
                                + [[hold["x"] + hold["w"] * side, hold["y"] + hold["d"] * side]
                                   for hold in plan.get("holds", []) for side in (0, 1)], dtype=float)
        self.low = numpy.minimum(corners.min(axis=0), 0.0)
        high = numpy.maximum(corners.max(axis=0), [plan["w"], plan["d"]])
        self.size = max(FINEST, float(max(high - self.low)) / CELLS)
        self.shape = (int(math.ceil((high[1] - self.low[1]) / self.size)) + 1,
                      int(math.ceil((high[0] - self.low[0]) / self.size)) + 1)
        rows, columns = numpy.indices(self.shape)
        self.centres = numpy.stack([self.low[0] + (columns.ravel() + 0.5) * self.size,
                                    self.low[1] + (rows.ravel() + 0.5) * self.size], axis=1)

    def covered(self, polygon):
        """A boolean mask (rows x columns) of the cells `polygon` covers."""
        mask = inside(self.centres, polygon).reshape(self.shape)
        if not mask.any():
            middle = numpy.asarray(polygon, dtype=float).mean(axis=0)
            mask[self.cell_of(middle)] = True
        return mask

    def cell_of(self, point):
        row = int(min(max((point[1] - self.low[1]) // self.size, 0), self.shape[0] - 1))
        column = int(min(max((point[0] - self.low[0]) // self.size, 0), self.shape[1] - 1))
        return row, column


SIDE_WORDS = {"N": "north", "S": "south", "E": "east", "W": "west"}


def where(point, plan):
    """Where a point stands in the place, in plain words: its corner, side or middle (thirds of the outline box)."""
    across = ("west", "", "east")[min(2, max(0, int(3 * point[0] / max(plan["w"], 0.01))))]
    down = ("north", "", "south")[min(2, max(0, int(3 * point[1] / max(plan["d"], 0.01))))]
    return f"{down}-{across}" if down and across else down or across or "middle"


def middle_of(polygon):
    corners = numpy.asarray(polygon, dtype=float)
    return [round(float(value), 2) for value in (corners.min(axis=0) + corners.max(axis=0)) / 2]


def said_name(name):
    """A plan item's name as said: lower case ("BENCH 1" the "bench 1")."""
    return str(name).lower().replace("_", " ")


def anchors(inventory):
    """{row id: anchor} of the inventory's rows ('floor' when it names none)."""
    return {row["id"]: row.get("anchor") or "floor" for row in inventory.get("rows", [])}


def last_words(row):
    """The last word of a row's id and of its noun: what it is ("diner_seated" by its noun "person")."""
    return {str(said).replace("_", " ").strip().lower().split(" ")[-1] for said in (row["id"], row.get("noun") or "")}


def people(inventory):
    """The ids of the rows that are people (PEOPLE): they sit and stand on things and move, so they block nothing."""
    return {row["id"] for row in inventory.get("rows", []) if last_words(row) & PEOPLE}


def crowd(row):
    """Whether a people row is a crowd (the cast's far crowd, never single person spots)."""
    return bool(last_words(row) & CROWD or set(row["id"].split("_")) & CROWD)


def person_rows(inventory):
    """The people rows stood as person spots (plan["people"] entries [x, y, facing, row]): every one but a crowd."""
    return [row for row in inventory.get("rows", []) if row["id"] in people(inventory) and not crowd(row)]


def afar(inventory):
    """The ids of the rows seen far off (AFAR in their id: a distant crowd): outside the place on purpose."""
    return {row["id"] for row in inventory.get("rows", []) if set(row["id"].split("_")) & AFAR}


def at_foot(rows, picture):
    """The ids of the rows a SAM 3 box of which reaches the picture's foot (within FOOT_SHARE of its height): they
    stand on the place's own floor or ground before the viewer, so none is beyond it, whatever the plan said
    (2026-10-26: the airlock's sandbags piled at the picture's bottom edges were listed beyond, and nothing made
    them)."""
    if not picture:
        return set()
    foot = picture[1] * (1 - FOOT_SHARE)
    return {row["id"] for row in rows
            if any(box and len(box) == 4 and box[3] >= foot for box in row.get("boxes") or [row.get("box")])}


def beyond(plan, inventory):
    """The ids of the rows the plan marks beyond the place, but for those at the picture's foot (`at_foot`): those
    stand on its own floor or ground and are placed like any other."""
    return set(plan.get("beyond", [])) - at_foot(inventory.get("rows", []), inventory.get("picture"))


def placed_items(plan):
    """[(item, its row id or None, its shape)] of the plan's items that are things (no zone, no walls item)."""
    return [(item, (plan.get("rows", {}).get(item[0]) or [None])[0], plan.get("shapes", {}).get(item[0]))
            for item in plan.get("items", []) if item[6] == "item" and item[0] != WALLS_ITEM]


def count_gaps(plan, inventory, structure):
    """A gap for each row standing on the floor or the ground placed another number of times than it counts (none for
    a row the writer saw beyond the place, through a window or past its edge: the plan's `beyond`); an item of a run
    (a row of shelving, a stack of crates) counts as many as its shape's `count`."""
    placed = collections.Counter()
    for _, row, shape in placed_items(plan):
        placed[row] += int((shape or {}).get("count") or 1)
    gaps, left_out = [], beyond(plan, inventory) | people(inventory)  # people stand on person spots
    for row in inventory.get("rows", []):
        if row["id"] in structure | left_out or (row.get("anchor") or "floor") not in FLOOR_ANCHORS:
            continue
        count = int(row.get("count", 1) or 1)
        if placed[row["id"]] != count:
            gaps.append({"kind": "placed", "item": row["id"], "row": row["id"],
                         "words": f"{said_name(row['id'])}: {count} in the concept, {placed[row['id']]} on the plan"})
    return gaps


def people_gaps(plan, inventory):
    """A gap for each people row (no crowd) stood on fewer person spots than the concept shows (owner, 2026-10-21:
    people are never furniture; the cast stands on these spots)."""
    stood = collections.Counter(spot[3] for spot in plan.get("people", []) if len(spot) >= 4)
    return [{"kind": "people", "item": row["id"], "row": row["id"],
             "words": f"{said_name(row['id'])}: {int(row.get('count', 1) or 1)} in the concept, "
                      f"{stood[row['id']]} person spots on the plan"}
            for row in person_rows(inventory) if row["id"] not in beyond(plan, inventory)
            and stood[row["id"]] < int(row.get("count", 1) or 1)]


def outside(polygon, grid, outline):
    """Whether more than OUTSIDE of `polygon`'s cells lie outside the outline."""
    covered = grid.covered(polygon)
    return (covered & ~outline).sum() > OUTSIDE * covered.sum()


def outside_gaps(plan, inventory, grid, outline):
    """A gap for each item standing on the floor or the ground more than OUTSIDE of whose footprint lies outside the
    outline (a thing on a wall stands on its line; one seen far off stands out there on purpose)."""
    anchored, far, gaps = anchors(inventory), afar(inventory), []
    for item, row, shape in placed_items(plan):
        if anchored.get(row, "floor") not in FLOOR_ANCHORS or row in far:
            continue
        polygon = polygon_of(item, shape)
        if outside(polygon, grid, outline):
            gaps.append({"kind": "outside", "item": item[0], "row": row, "at": middle_of(polygon),
                         "words": f"{said_name(item[0])} sticks out of the place ({where(middle_of(polygon), plan)})"})
    return gaps


def blocking(plan, inventory):
    """[(item, row, shape)] of the items that stand on the floor: anchored on the floor or the ground, base below
    LOW, taller than FLAT (a cable, a mat or a track lies under what stands on it and is walked over), no person and
    nothing seen far off."""
    anchored, left_out = anchors(inventory), people(inventory) | afar(inventory)
    return [(item, row, shape) for item, row, shape in placed_items(plan)
            if anchored.get(row, "floor") in FLOOR_ANCHORS and row not in left_out
            and float((shape or {}).get("base") or 0.0) < LOW
            and float((shape or {}).get("tall") or 1.0) > FLAT]


def attached(first, second, anchored):
    """Whether one of two rows stands on the other (its anchor `on:<the other>`)."""
    return anchored.get(first) == f"on:{second}" or anchored.get(second) == f"on:{first}"


def overlap_gaps(plan, inventory, grid):
    """A gap for each two floor items sharing more than OVERLAP of the smaller one, unless one stands on the other."""
    anchored = anchors(inventory)
    found = [(item, row, grid.covered(polygon_of(item, shape)), middle_of(polygon_of(item, shape)))
             for item, row, shape in blocking(plan, inventory)]
    gaps = []
    for number, (item, row, mask, middle) in enumerate(found):
        for other, other_row, other_mask, _ in found[number + 1:]:
            if attached(row, other_row, anchored):
                continue
            shared = (mask & other_mask).sum()
            if shared > OVERLAP * min(mask.sum(), other_mask.sum()):
                gaps.append({"kind": "overlap", "item": item[0], "row": row, "at": middle, "with": other[0],
                             "words": f"{said_name(item[0])} and {said_name(other[0])} stand in each other "
                                      f"({where(middle, plan)})"})
    return gaps


def free_floor(plan, inventory, grid, outline):
    """The cells one can walk on: inside the outline, under no floor item and no wall, a wall's openings open."""
    free = outline.copy()
    for item, _, shape in blocking(plan, inventory):
        free &= ~grid.covered(polygon_of(item, shape))
    for wall in plan.get("walls", []):
        free &= ~grid.covered(wall_polygon(wall))
    for opening in plan.get("openings", []):
        if opening.get("kind") in ("door", "opening", "gate"):
            free |= grid.covered(opening_polygon(opening)) & outline
    return free


def door_seeds(plan):
    """[(what, point)] of every door a little inside the place, and every standing spot."""
    seeds = []
    for side, at, *_ in plan.get("doors", []):
        if side in SIDE_WORDS:
            point = {"N": (at, STEP_IN), "S": (at, plan["d"] - STEP_IN), "W": (STEP_IN, at),
                     "E": (plan["w"] - STEP_IN, at)}[side]
            to = (plan.get("leads", {}).get(side) or {}).get("to")
            seeds.append((f"the door on the {SIDE_WORDS[side]} wall" + (f" to the {said_name(to)}" if to else ""),
                          point))
    for opening in plan.get("openings", []):
        if opening.get("kind") in ("door", "opening", "gate"):
            to = f" to the {said_name(opening['to'])}" if opening.get("to") else ""
            seeds += [(f"the {opening['kind']}{to} ({where(opening['at'], plan)})", point)
                      for point in stepped_in(opening)]
    return seeds + [(f"the standing spot ({where(spot, plan)})", (spot[0], spot[1])) for spot in plan.get("people", [])]


def stepped_in(opening):
    """The two points STEP_IN either side of an opening, through its wall."""
    turn = math.radians(float(opening.get("angle") or 0.0))
    x, y = opening["at"]
    return [(x - sign * STEP_IN * math.sin(turn), y + sign * STEP_IN * math.cos(turn)) for sign in (1, -1)]


def nearest_free(free, grid, point):
    """The free cell at or nearest `point` within NEAREST, else None."""
    row, column = grid.cell_of(point)
    reach = int(math.ceil(NEAREST / grid.size))
    best = None
    for found_row in range(max(0, row - reach), min(grid.shape[0], row + reach + 1)):
        for found_column in range(max(0, column - reach), min(grid.shape[1], column + reach + 1)):
            far = (found_row - row) ** 2 + (found_column - column) ** 2
            if free[found_row, found_column] and (best is None or far < best[0]):
                best = (far, (found_row, found_column))
    return best and best[1]


def regions(free):
    """Each free cell's connected region's number (4-neighbours), -1 for blocked cells."""
    label = numpy.full(free.shape, -1, dtype=int)
    count = 0
    for start in zip(*numpy.nonzero(free)):
        if label[start] >= 0:
            continue
        label[start], queue = count, collections.deque([start])
        while queue:
            row, column = queue.popleft()
            for step_row, step_column in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                near = (row + step_row, column + step_column)
                if 0 <= near[0] < free.shape[0] and 0 <= near[1] < free.shape[1] and free[near] and label[near] < 0:
                    label[near] = count
                    queue.append(near)
        count += 1
    return label


def reach_gaps(plan, inventory, grid, outline):
    """A gap for each door or standing spot not reachable on foot from the most of the others (an opening counts by
    its better side)."""
    free = free_floor(plan, inventory, grid, outline)
    label = regions(free)
    seeds, points = {}, {}
    for what, point in door_seeds(plan):
        cell = nearest_free(free, grid, point)
        seeds.setdefault(what, []).append(label[cell] if cell else -1)
        points.setdefault(what, [round(float(point[0]), 2), round(float(point[1]), 2)])
    counted = collections.Counter(region for found in seeds.values() for region in set(found) if region >= 0)
    if not counted:
        return [{"kind": "reach", "item": what, "row": None, "at": points[what],
                 "words": f"{what} has no free floor in front of it"} for what in seeds]
    main = counted.most_common(1)[0][0]
    return [{"kind": "reach", "item": what, "row": None, "at": points[what],
             "words": f"{what} cannot be reached on foot"} for what, found in seeds.items() if main not in found]


def hold_gaps(plan, grid, outline):
    """A gap for each inside place lying outside the outline or overlapping another."""
    holds = plan.get("holds", [])
    boxes = [[[hold["x"], hold["y"]], [hold["x"] + hold["w"], hold["y"]], [hold["x"] + hold["w"], hold["y"] + hold["d"]],
              [hold["x"], hold["y"] + hold["d"]]] for hold in holds]
    masks = [grid.covered(box) for box in boxes]
    gaps = [{"kind": "tiling", "item": hold["place"], "row": hold.get("row"), "at": middle_of(box),
             "words": f"{said_name(hold['place'])} sticks out of the place"}
            for hold, box in zip(holds, boxes) if outside(box, grid, outline)]
    for number, (hold, mask) in enumerate(zip(holds, masks)):
        gaps += [{"kind": "tiling", "item": hold["place"], "row": hold.get("row"), "at": middle_of(boxes[number]),
                  "with": other["place"], "words": f"{said_name(hold['place'])} and {said_name(other['place'])} overlap"}
                 for other, other_mask in zip(holds[number + 1:], masks[number + 1:])
                 if (mask & other_mask).sum() > OVERLAP * min(mask.sum(), other_mask.sum())]
    return gaps


# --- the arrangement against the concept --------------------------------------------------------------------------

def laid_boxes(plan):
    """{row id: [[x0, y0, x1, y1], ...]} in plan metres of each row's items and of the inside places it holds."""
    found = collections.defaultdict(list)
    for item, row, shape in placed_items(plan):
        corners = numpy.asarray(polygon_of(item, shape), dtype=float)
        found[row].append([*corners.min(axis=0), *corners.max(axis=0)])
    for hold in plan.get("holds", []):
        if hold.get("row"):
            found[hold["row"]].append([hold["x"], hold["y"], hold["x"] + hold["w"], hold["y"] + hold["d"]])
    return found


def concept_spots(plan, inventory):
    """{row id: (across, middle, foot, box)} of each row standing on the floor or the ground, counted once, placed on
    the plan and boxed by SAM 3 on the concept: its box's middle across and down and its foot (the box's bottom, nearer
    the lower), as shares of the picture, and the box in pixels. People, rows seen far off, the place itself and rows
    beyond it are left out."""
    picture, placed = inventory.get("picture"), set(laid_boxes(plan))
    if not picture:
        return {}
    left_out = people(inventory) | afar(inventory) | beyond(plan, inventory) | (set(plan.get(
        "structure", [])) - placed)
    found = {}
    for row in inventory.get("rows", []):
        boxes = [box for box in row.get("boxes") or ([row["box"]] if row.get("box") else []) if box]
        if (row.get("anchor") or "floor") in FLOOR_ANCHORS and int(row.get("count", 1) or 1) == 1 and len(boxes) == 1 \
                and row["id"] in placed and row["id"] not in left_out and not whole(row, picture):
            box = boxes[0]
            found[row["id"]] = ((box[0] + box[2]) / 2 / picture[0], (box[1] + box[3]) / 2 / picture[1],
                                box[3] / picture[1], box)
    return found


def plan_spots(plan, rows):
    """{row id: [x, y]} the middle of each of `rows`' items and inside places on the plan (their mean when several)."""
    return {row: numpy.mean([[(box[0] + box[2]) / 2, (box[1] + box[3]) / 2] for box in boxes], axis=0)
            for row, boxes in laid_boxes(plan).items() if row in rows}


def relations(seen, laid, turn):
    """[(first, second, axis, said, drawn)] of every pair of rows whose order is clear both in the concept (`seen`) and
    on the plan (`laid`) with the viewer turned `turn` degrees from looking north: across (left of, right of) for pairs
    at about one depth, depth (behind, in front of) where the feet and the middles agree (a big building's foot
    alone reaches far forward); `said` and `drawn` the signs."""
    right = numpy.array([math.cos(math.radians(turn)), math.sin(math.radians(turn))])
    toward = numpy.array([-right[1], right[0]])  # toward the viewer: south when looking north
    reach = max(float(numpy.ptp(numpy.array(list(laid.values())), axis=0).max()), FINEST) if laid else 1.0
    found = []
    rows = sorted(seen)
    for number, first in enumerate(rows):
        for second in rows[number + 1:]:
            (across, middle, foot, _), (other_across, other_middle, other_foot, _) = seen[first], seen[second]
            apart = laid[first] - laid[second]
            if abs(foot - other_foot) <= SAME_DEPTH and abs(across - other_across) > CLEAR_SEEN \
                    and abs(apart @ right) > CLEAR_LAID * reach:
                found.append((first, second, "across", numpy.sign(across - other_across), numpy.sign(apart @ right)))
            if abs(foot - other_foot) > CLEAR_SEEN and abs(middle - other_middle) > CLEAR_SEEN \
                    and numpy.sign(foot - other_foot) == numpy.sign(middle - other_middle) \
                    and abs(apart @ toward) > CLEAR_LAID * reach:
                found.append((first, second, "depth", numpy.sign(foot - other_foot), numpy.sign(apart @ toward)))
    return found


def best_turn(seen, laid):
    """The way the viewer looks (degrees from north, TURNS apart) under which the plan agrees with the concept most."""
    return max(range(0, 360, TURNS), key=lambda turn: sum(said == drawn for *_, said, drawn
                                                          in relations(seen, laid, turn)))


SAID = {("across", 1): "right of", ("across", -1): "left of", ("depth", 1): "in front of", ("depth", -1): "behind"}


def order_gaps(plan, inventory):
    """A gap for each two rows whose order on the plan is not the concept's (left of, right of, behind, in front of),
    the plan seen from the way that agrees with the concept most."""
    seen, laid, turn = viewed(plan, inventory)
    if len(seen) < 2:
        return []
    return [{"kind": "arrangement", "item": first, "row": first, "with": second, "at": [round(float(value), 2) for value
                                                                                      in laid[first]],
             "words": f"{said_name(first)} is {SAID[(axis, int(said))]} {said_name(second)} in the concept, "
                      f"{SAID[(axis, int(drawn))]} it on the plan"}
            for first, second, axis, said, drawn in relations(seen, laid, turn) if said != drawn]


def viewed(plan, inventory):
    """(seen, laid, turn): the rows boxed on the concept and laid on the plan (concept_spots, plan_spots) and the way
    the viewer looks that agrees with the concept most (best_turn; north with fewer than two rows to order)."""
    seen = concept_spots(plan, inventory)
    laid = plan_spots(plan, set(seen))
    seen = {row: spot for row, spot in seen.items() if row in laid}
    return seen, laid, best_turn(seen, laid) if len(seen) >= 2 else 0


def ways(turn):
    """(right, toward) unit steps on the plan of the viewer looking `turn` degrees from north (y runs south)."""
    right = numpy.array([math.cos(math.radians(turn)), math.sin(math.radians(turn))])
    return right, numpy.array([-right[1], right[0]])


def third(share):
    """Where a share across the view stands, in words."""
    return "on the left" if share < 1 / 3 else "on the right" if share > 2 / 3 else "in the middle"


def shares(values):
    """{key: its value's share of the way from the least of `values` to the most}."""
    low, high = min(values.values()), max(values.values())
    return {key: (value - low) / max(high - low, 1e-9) for key, value in values.items()}


def frame_gaps(plan, inventory):
    """A gap for each row standing elsewhere across the view on the plan than in the concept (the middle against a
    side: a pad off to one side): its share of the way across from the leftmost of the rows boxed on both to the
    rightmost, in the concept's picture and on the plan seen from the way that agrees with the concept most, more
    than FRAME_APART apart (both from the same rows, so the painting's crop and perspective cancel out)."""
    seen, laid, turn = viewed(plan, inventory)
    if len(seen) < 3:
        return []
    right, _ = ways(turn)
    concept = shares({row: spot[0] for row, spot in seen.items()})
    drawn = shares({row: float(laid[row] @ right) for row in seen})
    gaps = []
    for row in sorted(seen):
        across, share = concept[row], drawn[row]
        if abs(share - across) > FRAME_APART:
            gaps.append({"kind": "arrangement", "item": row, "row": row, "at": [round(float(value), 2)
                                                                                for value in laid[row]],
                         "words": f"{said_name(row)} stands {third(across)} of the concept ({across:.0%} across), "
                                  f"{third(share)} of the plan ({share:.0%} across)"})
    return gaps


def facing_word(facing, turn):
    """The way a plan facing (N, E, S, W) points as the concept's viewer sees it: toward, away, left or right."""
    step = numpy.array({"N": (0, -1), "E": (1, 0), "S": (0, 1), "W": (-1, 0)}[facing], dtype=float)
    right, toward = ways(turn)
    along, near = float(step @ right), float(step @ toward)
    return ("right" if along > 0 else "left") if abs(along) > abs(near) else ("toward" if near > 0 else "away")


def facing_gaps(plan, inventory):
    """A gap for each item whose facing on the plan is not the way the concept shows it facing (its shape's `seen`,
    the writer's reading of the painting), the plan seen from the way that agrees with the concept most."""
    _, _, turn = viewed(plan, inventory)
    gaps = []
    for item, row, shape in placed_items(plan):
        seen = (shape or {}).get("seen")
        if item[5] in ("N", "E", "S", "W") and seen and facing_word(item[5], turn) not in seen:
            gaps.append({"kind": "arrangement", "item": item[0], "row": row, "at": middle_of(polygon_of(item, shape)),
                         "words": f"{said_name(item[0])} faces {'-'.join(seen)} in the concept, "
                                  f"{facing_word(item[5], turn)} on the plan"})
    return gaps


def run_gaps(plan, inventory):
    """A gap for each item counting several of its row (a run: shelving, a stack of crates) whose box covers far more
    than its things side by side: things drawn apart boxed as one, each to be laid where it stands."""
    sizes = {row["id"]: row["size"] for row in inventory.get("rows", []) if isinstance(row.get("size"), list)}
    gaps = []
    for item, row, shape in placed_items(plan):
        count, size = int((shape or {}).get("count") or 1), sizes.get(row) or [None, None]
        things = count * size[0] * size[1] if size[0] and size[1] else None
        if count > 1 and things and item[3] * item[4] > max(SPREAD * things, things + SPREAD_SLACK):
            gaps.append({"kind": "arrangement", "item": item[0], "row": row, "at": middle_of(polygon_of(item, shape)),
                         "words": f"{said_name(item[0])} boxes {count} things drawn apart as one "
                                  f"({item[3]:.1f} x {item[4]:.1f} m), not one run"})
    return gaps


def connector(row):
    """Whether a row joins parts (a tube, a corridor, a walkway, a bridge)."""
    return bool(last_words(row) & CONNECTORS)


def touching(box, other, margin):
    """Whether two boxes [x0, y0, x1, y1] meet within `margin`."""
    return box[0] - margin <= other[2] and other[0] - margin <= box[2] and box[1] - margin <= other[3] \
        and other[1] - margin <= box[3]


def join_gaps(plan, inventory):
    """A gap for each row a connector (a tube, a corridor) meets in the concept that no connector meets on the plan."""
    picture = inventory.get("picture")
    rows = {row["id"]: row for row in inventory.get("rows", [])}
    joins = [row for row in rows.values() if connector(row)]
    if not picture or not joins:
        return []
    seen = concept_spots(plan, inventory)
    margin = JOIN_SEEN * max(picture)
    joined = {row for row, (*_, box) in seen.items() if not connector(rows[row]) and any(
        touching(box, join_box, margin) for join in joins for join_box in join.get("boxes") or [] if join_box)}
    boxes = laid_boxes(plan)
    laid_joins = [box for join in joins for box in boxes.get(join["id"], [])]
    joiner = said_name(joins[0]["id"])
    return [{"kind": "joined", "item": row, "row": row, "at": middle_of([boxes[row][0][:2], boxes[row][0][2:]]),
             "words": f"{said_name(row)} is joined by a {joiner} in the concept, by none on the plan"}
            for row in sorted(joined) if boxes.get(row)
            and not any(touching(box, join_box, JOIN_LAID) for box in boxes[row] for join_box in laid_joins)]


def checked(plan, inventory, structure=()):
    """Every free check's gaps on `plan` against its scene inventory (`structure`: the rows that are the place's own
    shell, walls, floor, roof or ground, drawn as the plan's walls and levels, never items: an item of one, a backdrop
    the writer placed, is left out of the checks), and the rows that are the place itself (whole) counted so."""
    structure = set(structure) | {row["id"] for row in inventory.get("rows", [])
                                  if whole(row, inventory.get("picture"))}
    plan = {**plan, "items": [item for item in plan.get("items", [])
                              if not set(plan.get("rows", {}).get(item[0]) or []) & structure]}
    grid = Grid(plan)
    outline = grid.covered(outline_of(plan))
    return (count_gaps(plan, inventory, set(structure)) + people_gaps(plan, inventory) + outside_gaps(plan, inventory, grid, outline)
            + overlap_gaps(plan, inventory, grid) + reach_gaps(plan, inventory, grid, outline)
            + hold_gaps(plan, grid, outline) + order_gaps(plan, inventory) + frame_gaps(plan, inventory)
            + facing_gaps(plan, inventory) + run_gaps(plan, inventory) + join_gaps(plan, inventory))


# --- the rows the place itself is, and the projection from the concept onto the plan -------------------------------

def anchor_of(row):
    """A row's anchor: floor, wall, ... or the id of the row it stands on (a reading's `on:<id>`)."""
    anchor = row.get("anchor") or "floor"
    return anchor[3:] if anchor.startswith("on:") else anchor


WHOLE = 0.6  # a row whose surest box spans this share of the picture both ways is the place itself (its ground, sky)


GROUND = {"sea", "ocean", "water", "lake", "pool", "river", "harbour", "plaza", "square", "ground", "terrain", "sky",
          "floor", "road", "street", "pavement", "grass", "sand", "dust", "regolith", "soil", "skyline", "backdrop",
          "horizon", "mountains", "hills"}


def whole(row, picture):
    """Whether a row is the place itself rather than a thing in it: its surest box spans most of the picture, or it
    is the place's ground, water or sky (`GROUND`: the plan's ground and terrain, never a sized object; owner,
    2026-10-21)."""
    box = (row.get("boxes") or [None])[0]
    # what it is, the last word of its id or noun ("harbour_water", not "floor_lamp")
    words = {re.split(r"[_\s]+", str(said).strip().lower())[-1] for said in (row["id"], row.get("noun") or "")}
    return bool(box and picture and (box[2] - box[0]) >= WHOLE * picture[0] and (box[3] - box[1]) >= WHOLE * picture[1]
                or row.get("anchor") == "sky" or (anchor_of(row) in ("floor", "ground") and words & GROUND))


def boxes_of(row):
    """A row's SAM boxes on the concept (its instances')."""
    return [box for box in row.get("boxes") or ([row["box"]] if row.get("box") else []) if box]


def gemini_box(region, size):
    """A 0 to 1000 [ymin, xmin, ymax, xmax] region (score/review/reading.py) as a pixel box [left, top, right,
    bottom] on a picture of `size` [wide, tall]."""
    wide, tall = size
    return [round(region[1] * wide / 1000), round(region[0] * tall / 1000), round(region[3] * wide / 1000),
            round(region[2] * tall / 1000)]


def projection_anchors(plan, inventory):
    """[(across, foot), (x, y)] of each row on the floor (or on a row of the place's shell: its floor plates) boxed on
    the concept as many times as it is laid on the plan (concept_spots' rows, and the rows of several things too): the
    mean of its boxes' middles across and feet as shares of the picture, and the mean of its things' middles on the
    plan."""
    picture, laid, shell = inventory.get("picture"), laid_boxes(plan), set(plan.get("structure", []))
    if not picture:
        return []
    left_out = people(inventory) | afar(inventory) | beyond(plan, inventory)
    found = []
    for row in inventory.get("rows", []):
        boxes, things = boxes_of(row), laid.get(row["id"], [])
        if anchor_of(row) in {*FLOOR_ANCHORS, *shell} and boxes and len(things) == len(boxes) \
                and row["id"] not in left_out and not whole(row, picture):
            found.append((numpy.mean([[(box[0] + box[2]) / 2 / picture[0], box[3] / picture[1]] for box in boxes],
                                     axis=0),
                          numpy.mean([[(box[0] + box[2]) / 2, (box[1] + box[3]) / 2] for box in things], axis=0)))
    return found


def projection(plan, inventory):
    """The fitted map (a 3 x 2 matrix) from [a box's middle across, its foot, 1] as shares of the concept to its spot
    [x, y] on the plan, fitted on the rows boxed and laid alike (`projection_anchors`); None with fewer than three
    such rows."""
    fitted = projection_anchors(plan, inventory)
    if len(fitted) < 3:
        return None
    source = numpy.array([[seen[0], seen[1], 1.0] for seen, _ in fitted])
    target = numpy.array([spot for _, spot in fitted], dtype=float)
    return numpy.linalg.lstsq(source, target, rcond=None)[0]
