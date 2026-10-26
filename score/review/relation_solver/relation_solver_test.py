"""The relation solver's parting of crowded plans (score/review/relation_solver): a pile parted to no overlap inside
the outline, the same answer every run, the walls kept clear, and a plan with nothing in each other given back."""
import itertools

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


def test_twelve_sandbags_on_one_spot_are_parted_inside_the_place_the_same_way_every_run():
    plan, inventory = piled(12)
    assert len(plan_checks.overlap_gaps(plan, inventory, plan_checks.Grid(plan))) == 66  # 12 * 11 / 2
    parted, fixes = relation_solver.parted(plan, inventory)
    assert plan_checks.overlap_gaps(parted, inventory, plan_checks.Grid(parted)) == []
    assert boxes_overlapping(parted["items"]) == 0 and len(fixes) >= 11  # at most one may stay on its spot
    assert all(0.0 <= item[1] and item[1] + item[3] <= 3.0 and 0.0 <= item[2] and item[2] + item[4] <= 3.0
               for item in parted["items"])
    assert relation_solver.parted(plan, inventory) == (parted, fixes)  # seeded: the same answer again
    assert plan["items"][0][1:3] == [1.2, 1.3]  # the plan given is never changed


def test_things_parted_beside_a_wall_never_stand_in_it():
    wall = {"from": [1.9, 0.0], "to": [1.9, 3.0], "thick": 0.2}  # its box x 1.8 to 2.0, beside the pile's 1.2 to 1.8
    plan, inventory = piled(4, walls=[wall])
    parted, fixes = relation_solver.parted(plan, inventory)
    assert fixes and boxes_overlapping(parted["items"]) == 0
    assert all(item[1] + item[3] <= 1.8 + 0.001 or item[1] >= 2.0 - 0.001 for item in parted["items"])


def test_a_plan_with_nothing_in_each_other_is_given_back_as_it_is():
    plan, inventory = piled(1)
    assert relation_solver.parted(plan, inventory) == (plan, [])
