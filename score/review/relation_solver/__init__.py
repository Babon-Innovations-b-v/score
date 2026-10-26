"""The plan fixes' fallback for crowded plans (`parted`): the floor things the free fixes left standing in each other
(plan_checks.overlap_gaps after plan_fixes.nudged: a pile of sandbags) parted by IsaacLab-Arena's relation solver,
ported to numpy (`_solver.py`, Apache-2.0, its LICENSE beside it), free on the CPU and seeded. Each thing's plan spot
is a soft target, the walls and every other floor thing are box obstacles, and the outline's box holds them; a thing
of the place's own shell (its `structure`) never moves. The solved plan is kept only when today's checks find fewer
overlaps and no more gaps of any other kind, and what still overlaps stays a gap. Called from plans_pass only, so it
is in no stage's code key.

    plan, fixes = relation_solver.parted(plan, inventory)   # fixes [] and the plan as given when nothing was parted
"""
import collections
import copy
import math

import numpy

from score.review import plan_checks, plan_fixes
from score.review.relation_solver import _solver

SOFT = 1.0  # the pull back to a thing's plan spot a metre off: weaker than the outline's (100) and an overlap's
PIECE = 0.5  # metres: a wall is boxed in pieces this long at most, so a slanted or curved one stays thin
NEIGHBOURS = (0.0, 1.0)  # metres round the things in each other whose floor things move too, tried in turn
SEED = 0


def wall_boxes(wall):
    """A wall {from, to, thick} or {arc, thick} as boxes [low x, low y, high x, high y] of its pieces."""
    thick = float(wall.get("thick") or 0.2)
    if "arc" in wall:
        arc = wall["arc"]
        turns = numpy.radians(numpy.linspace(float(arc["start"]), float(arc["end"]), plan_checks.ROUND + 1))
        line = [numpy.array([arc["centre"][0] + float(arc["radius"]) * math.cos(turn),
                             arc["centre"][1] + float(arc["radius"]) * math.sin(turn)]) for turn in turns]
    else:
        start, end = numpy.asarray(wall["from"], dtype=float), numpy.asarray(wall["to"], dtype=float)
        pieces = max(1, math.ceil(float(numpy.linalg.norm(end - start)) / PIECE))
        line = [start + (end - start) * share for share in numpy.linspace(0.0, 1.0, pieces + 1)]
    boxes = []
    for first, second in zip(line, line[1:]):
        corners = numpy.array(plan_checks.wall_polygon({"from": first.tolist(), "to": second.tolist(),
                                                        "thick": thick}))
        boxes.append([*corners.min(axis=0), *corners.max(axis=0)])
    return boxes


def item_box(item):
    """A plan item's box [low x, low y, high x, high y]."""
    return [item[1], item[2], item[1] + item[3], item[2] + item[4]]


def boxes_meet(box, other, margin=0.0):
    """Whether two boxes come within `margin` of each other (share floor at 0)."""
    return box[0] < other[2] + margin and other[0] < box[2] + margin and box[1] < other[3] + margin \
        and other[1] < box[3] + margin


def movers(plan, inventory, reach):
    """The names of the floor things in each other by today's check (the place's own shell left out), and of the
    floor things within `reach` metres of one."""
    shell = set(plan.get("structure", []))
    gaps = [gap for gap in plan_checks.overlap_gaps(plan, inventory, plan_checks.Grid(plan))
            if not {gap["row"], *plan.get("rows", {}).get(gap["with"], [])} & shell]
    named = {name for gap in gaps for name in (gap["item"], gap["with"])}
    boxes = {item[0]: item_box(item) for item, row, _ in plan_checks.blocking(plan, inventory) if row not in shell}
    return {name for name, box in boxes.items()
            if name in named or any(boxes_meet(box, boxes[other], reach) for other in named if other in boxes)}


def problem_of(plan, inventory, moving):
    """The solver's problem for the floor things `moving` ([(item, row)]): their sizes, their plan spots as soft
    targets, the outline's box, and as obstacles the walls (but one a thing already stands in) and the other floor
    things, a thing standing on another never kept from it."""
    anchored = plan_checks.anchors(inventory)
    names = {item[0] for item, _ in moving}
    still = [(item, row) for item, row, _ in plan_checks.blocking(plan, inventory) if item[0] not in names]
    walls = [box for wall in plan.get("walls", []) for box in wall_boxes(wall)]
    outline = numpy.asarray(plan_checks.outline_of(plan), dtype=float)
    avoids = [[0.0 if plan_checks.attached(row, other_row, anchored) else 1.0 for _, other_row in still]
              + [0.0 if boxes_meet(item_box(item), wall) else 1.0 for wall in walls] for item, row in moving]
    apart = [[0.0 if plan_checks.attached(row, other_row, anchored) else 1.0 for _, other_row in moving]
             for _, row in moving]
    return _solver.Problem([item[3:5] for item, _ in moving], [item[1:3] for item, _ in moving], SOFT,
                           [*outline.min(axis=0), *outline.max(axis=0)],
                           [item_box(item) for item, _ in still] + walls,
                           numpy.asarray(avoids).reshape(len(moving), len(still) + len(walls)), apart,
                           plan_fixes.MARGIN)


def moved(plan, inventory, names):
    """(a copy of the plan with the floor things `names` where the solver puts them, the fixes said)."""
    plan = copy.deepcopy(plan)
    moving = [(item, row) for item, row, _ in plan_checks.blocking(plan, inventory) if item[0] in names]
    if not moving:
        return plan, []
    spots, _ = _solver.solved(problem_of(plan, inventory, moving), seed=SEED)
    fixes = []
    for (item, _), spot in zip(moving, spots):
        step = math.dist(item[1:3], spot)
        if step >= 0.01:
            item[1], item[2] = round(float(spot[0]), 3), round(float(spot[1]), 3)
            fixes.append(f"{plan_checks.said_name(item[0])}: moved {step:.2f} m out of the things it stood in "
                         f"(the relation solver)")
    return plan, fixes


def counted(plan, inventory):
    """{gap kind: how many} by today's checks (plan_checks.checked, the place's own shell left out)."""
    return collections.Counter(gap["kind"] for gap in plan_checks.checked(plan, inventory, plan.get("structure", [])))


def parted(plan, inventory):
    """(the plan with its floor things in each other parted, the fixes said): the solver on those things, then also
    on the floor things round them (NEIGHBOURS), the first answer kept that leaves fewer overlaps and no more gaps of
    any other kind by today's checks; (the plan as given, []) when none does or nothing overlaps."""
    before = counted(plan, inventory)
    if not before["overlap"]:
        return plan, []
    for reach in NEIGHBOURS:
        answer, fixes = moved(plan, inventory, movers(plan, inventory, reach))
        after = counted(answer, inventory)
        if fixes and after["overlap"] < before["overlap"] and all(
                after[kind] <= before[kind] for kind in after if kind != "overlap"):
            return answer, fixes
    return plan, []
