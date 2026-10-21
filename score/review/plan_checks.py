"""The free checks on a written plan (CONTEXT.md "plan"; score/review/plan_writing.py), each failure a named gap of the
plan, never guessed past: every inventory row placed once (as many items as it counts), every item inside the
outline, no two items on the floor overlapping (a row on another row, and a row on a wall or the ceiling, excepted),
every door and standing spot reachable on foot from the others, and the inside places tiling the outline without
overlap. Measured on a grid of the plan (`Grid`): an item's footprint is its shape (`footprint`), the walls block,
their openings do not."""
import collections
import math

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
KINDS = ("placed", "outside", "overlap", "reach", "tiling")  # the gaps' kinds these checks write


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


def placed_items(plan):
    """[(item, its row id or None, its shape)] of the plan's items that are things (no zone, no walls item)."""
    from score.review.plans import WALLS_ITEM
    return [(item, (plan.get("rows", {}).get(item[0]) or [None])[0], plan.get("shapes", {}).get(item[0]))
            for item in plan.get("items", []) if item[6] == "item" and item[0] != WALLS_ITEM]


def count_gaps(plan, inventory, structure):
    """A gap for each row standing on the floor or the ground placed another number of times than it counts."""
    placed = collections.Counter(row for _, row, _ in placed_items(plan))
    gaps = []
    for row in inventory.get("rows", []):
        if row["id"] in structure or (row.get("anchor") or "floor") not in FLOOR_ANCHORS:
            continue
        count = int(row.get("count", 1) or 1)
        if placed[row["id"]] != count:
            gaps.append({"kind": "placed", "item": row["id"], "row": row["id"],
                         "words": f"{said_name(row['id'])}: {count} in the concept, {placed[row['id']]} on the plan"})
    return gaps


def outside(polygon, grid, outline):
    """Whether more than OUTSIDE of `polygon`'s cells lie outside the outline."""
    covered = grid.covered(polygon)
    return (covered & ~outline).sum() > OUTSIDE * covered.sum()


def outside_gaps(plan, grid, outline):
    """A gap for each item more than OUTSIDE of whose footprint lies outside the outline."""
    gaps = []
    for item, row, shape in placed_items(plan):
        polygon = polygon_of(item, shape)
        if outside(polygon, grid, outline):
            gaps.append({"kind": "outside", "item": item[0], "row": row, "at": middle_of(polygon),
                         "words": f"{said_name(item[0])} sticks out of the place ({where(middle_of(polygon), plan)})"})
    return gaps


def blocking(plan, inventory):
    """[(item, row, shape)] of the items that stand on the floor: anchored on the floor or the ground, base below
    LOW, and taller than FLAT (a cable, a mat or a track lies under what stands on it and is walked over)."""
    anchored = anchors(inventory)
    return [(item, row, shape) for item, row, shape in placed_items(plan)
            if anchored.get(row, "floor") in FLOOR_ANCHORS and float((shape or {}).get("base") or 0.0) < LOW
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


def checked(plan, inventory, structure=()):
    """Every free check's gaps on `plan` against its scene inventory (`structure`: the rows that are the place's own
    shell, walls, floor, roof or ground, drawn as the plan's walls and levels, never items)."""
    grid = Grid(plan)
    outline = grid.covered(outline_of(plan))
    return (count_gaps(plan, inventory, set(structure)) + outside_gaps(plan, grid, outline)
            + overlap_gaps(plan, inventory, grid) + reach_gaps(plan, inventory, grid, outline)
            + hold_gaps(plan, grid, outline))
