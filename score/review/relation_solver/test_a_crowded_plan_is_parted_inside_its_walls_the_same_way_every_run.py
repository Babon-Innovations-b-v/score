"""The relation solver's parting of crowded plans (score/review/relation_solver): a pile parted to no overlap inside
the outline, the same answer every run, the plan given never changed, and the walls kept clear. The overlaps are
counted apart from the checks' grid (`boxes_overlapping`) and the 66 pairs of twelve on one spot by hand.

The old third test (a plan with nothing in each other given back as it is) went on 2026-10-27: no single break turns
it red, since `parted`'s early return and its last `return plan, []` each give the plan back without the other.

One test asks it of two worlds as rows: twelve sandbags piled on one spot in an open place, and four piled beside a
wall. Each row is parted, then judged by the same checks: no overlap by the checks' grid or by hand, every bag but
one moved, all inside the outline, out of the wall's span, the same answer again, and the plan given unchanged.

Breaks (each applied once, seen red, reverted), in __init__.py:
- `moved`'s `plan = copy.deepcopy(plan)` taken out (the plan given is moved in place): both rows red on the
  plan-unchanged check.
- `walls = [box for wall in plan.get("walls", []) for box in wall_boxes(wall)]` made `walls = []`: the
  beside-a-wall row red on its wall-span check.
"""
import itertools

import pytest

from score.review import plan_checks, relation_solver

BAG = [0.6, 0.35]


def piled(count, wide=3.0, walls=()):
    """A `wide` metres square place with `count` sandbags all on one spot (the airlock's pile, 2026-10-26)."""
    items = [[f"SANDBAGS {number}", 1.2, 1.3, *BAG, None, "item"] for number in range(1, count + 1)]
    plan = {"w": wide, "d": wide, "doors": [], "people": [], "items": items, "walls": list(walls),
            "rows": {item[0]: ["sandbags"] for item in items}}
    inventory = {"rows": [{"id": "sandbags", "anchor": "ground", "count": count, "size": [*BAG, 0.15]}]}
    return plan, inventory


def boxes_overlapping(items):
    """The pairs of item boxes sharing floor, counted apart from the checks' grid."""
    return sum(1 for first, second in itertools.combinations(items, 2)
               if first[1] < second[1] + second[3] and second[1] < first[1] + first[3]
               and first[2] < second[2] + second[4] and second[2] < first[2] + first[4])


WALL = {"from": [1.9, 0.0], "to": [1.9, 3.0], "thick": 0.2}  # its box x 1.8 to 2.0, beside the pile's 1.2 to 1.8


@pytest.mark.parametrize("count, walls, wall_span", [
    (12, (), None),
    (4, (WALL,), (1.8, 2.0)),
], ids=["twelve_on_one_spot_in_the_open", "four_beside_a_wall"])
def test_a_crowded_plan_is_parted_inside_its_walls_the_same_way_every_run(count, walls, wall_span):
    plan, inventory = piled(count, walls=walls)
    assert len(plan_checks.overlap_gaps(plan, inventory, plan_checks.Grid(plan))) == count * (count - 1) // 2
    parted, fixes = relation_solver.parted(plan, inventory)
    assert plan_checks.overlap_gaps(parted, inventory, plan_checks.Grid(parted)) == []
    assert boxes_overlapping(parted["items"]) == 0 and len(fixes) >= count - 1  # at most one may stay on its spot
    assert all(0.0 <= item[1] and item[1] + item[3] <= 3.0 and 0.0 <= item[2] and item[2] + item[4] <= 3.0
               for item in parted["items"])
    if wall_span:
        assert all(item[1] + item[3] <= wall_span[0] + 0.001 or item[1] >= wall_span[1] - 0.001
                   for item in parted["items"])
    assert relation_solver.parted(plan, inventory) == (parted, fixes)  # seeded: the same answer again
    assert plan["items"][0][1:3] == [1.2, 1.3]  # the plan given is never changed
