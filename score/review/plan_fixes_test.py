"""The automatic fixes of a written plan (plan_fixes.py) on stand-in plans: free fixes first, a Correct only for what
is left and kept only when it leaves fewer gaps, and what is left saying why."""
from score.review import plan_checks, plan_fixes

ROWS = [  # three rows boxed once on a 1000 px concept, laid so the projection is x = 10 across, y = 10 foot
    {"id": "desk", "count": 1, "size": [1.0, 1.0, 1.0], "boxes": [[150, 400, 250, 500]]},
    {"id": "rack", "count": 1, "size": [1.0, 1.0, 1.0], "boxes": [[750, 400, 850, 500]]},
    {"id": "pad", "count": 1, "size": [1.0, 1.0, 1.0], "boxes": [[450, 800, 550, 900]]},
    {"id": "barrel", "count": 2, "size": [1.0, 1.0, 1.0], "boxes": [[150, 600, 250, 700], [750, 600, 850, 700]]},
    {"id": "worker", "noun": "person", "count": 1, "boxes": [[480, 200, 520, 300]]},
    {"id": "crate", "count": 1, "size": [0.6, 0.6, 0.6]}]


def stand_in():
    items = [["DESK 1", 1.5, 4.5, 1.0, 1.0, "N", "item"], ["RACK 1", 7.5, 4.5, 1.0, 1.0, None, "item"],
             ["PAD 1", 4.5, 8.5, 1.0, 1.0, None, "item"], ["BARREL 1", 7.5, 6.5, 1.0, 1.0, None, "item"],
             ["WORKER 1", 4.8, 2.8, 0.4, 0.4, None, "item"], ["CRATE 1", 1.8, 4.8, 0.6, 0.6, None, "item"]]
    return {"w": 10.0, "d": 10.0, "doors": [], "people": [[9.5, 9.5]], "items": items,
            "rows": {item[0]: [item[0].split(" ")[0].lower()] for item in items},
            "shapes": {"DESK 1": {"shape": "rect", "seen": ["toward"]}}}


def test_the_free_fixes_stand_people_place_the_missing_turn_and_part_and_leave_the_rest_saying_why():
    inventory = {"picture": [1000, 1000], "rows": ROWS}
    plan = stand_in()
    before = [gap["kind"] for gap in plan_checks.checked(plan, inventory)]
    assert {"placed", "people", "overlap", "arrangement"} <= set(before)
    plan, fixes = plan_fixes.fixed(plan, inventory)
    assert plan["people"][0] == [5.0, 3.0, 0.0, "worker"] and plan["people"][1] == [9.5, 9.5]
    assert "WORKER 1" not in {item[0] for item in plan["items"]}  # a person is no furniture
    barrels = sorted((item[1], item[2]) for item in plan["items"] if item[0].startswith("BARREL"))
    assert barrels == [(1.5, 6.5), (7.5, 6.5)]  # the missing one where its box projects
    assert {item[0]: item for item in plan["items"]}["DESK 1"][5] == "S"  # it faces the viewer in the concept
    assert plan_checks.checked(plan, inventory) == [] and len(fixes) == 4


def test_a_box_of_things_drawn_apart_is_split_round_its_spread():
    inventory = {"rows": [{"id": "tree", "count": 4, "size": [1.0, 1.0, 5.0]}]}
    plan = {"w": 12.0, "d": 12.0, "doors": [], "people": [], "items": [["TREE 1", 1.0, 1.0, 10.0, 10.0, None, "item"]],
            "rows": {"TREE 1": ["tree"]}, "shapes": {"TREE 1": {"shape": "circle", "count": 4}}}
    assert plan_checks.run_gaps(plan, inventory)
    fixes = plan_fixes.split_runs(plan, inventory, None)
    assert fixes == ["tree 1: split into its 4 things"] and len(plan["items"]) == 4
    assert all(item[3] == 1.0 and plan["shapes"][item[0]] == {"shape": "circle"} for item in plan["items"])
    assert not plan_checks.run_gaps(plan, inventory)


def test_a_correction_is_kept_only_when_it_leaves_fewer_gaps_and_what_is_left_says_why(monkeypatch):
    inventory = {"picture": [1000, 1000], "rows": [row for row in ROWS if row["id"] != "barrel"] + [
        {"id": "stool", "count": 1, "size": [0.5, 0.5, 0.5]}]}  # no box: no free fix places it
    answers = []

    def correcting(store, place, plan, left, ask):
        answers.append([gap["words"] for gap in left])
        laid = plan["items"] + [["STOOL 1", 3.0, 3.0, 0.5, 0.5, None, "item"]] if len(answers) == 1 else plan["items"]
        return {**plan, "items": laid, "rows": {**plan["rows"], "STOOL 1": ["stool"]}}, {"euros": 0.07}
    monkeypatch.setattr(plan_fixes, "corrected", correcting)
    plan, calls = plan_fixes.settled(None, "shed", stand_in(), inventory, ask=None)
    assert answers == [["stool: 1 in the concept, 0 on the plan"]] and calls == [{"euros": 0.07}]
    assert plan["gaps"] == [] and "the prompt model corrected 1 gaps" in plan["fixes"]
    monkeypatch.setattr(plan_fixes, "corrected", lambda *args: (args[2], {"euros": 0.07}))  # changes nothing
    plan, calls = plan_fixes.settled(None, "shed", stand_in(), inventory, ask=None)
    assert len(calls) == 1 and [gap["words"] for gap in plan["gaps"]] == [
        f"stool: 1 in the concept, 0 on the plan: {plan_fixes.WHY['placed']}"]


def test_a_row_at_the_concept_s_foot_marked_beyond_is_placed_where_its_box_projects():
    """2026-10-26: the airlock's sandbags at its picture's foot were marked beyond and had no plan item, and its rows
    of several things and its rows on the floor plates fitted no projection: now they fit it, and the row is placed."""
    cube = [1.0, 1.0, 1.0]
    rows = [{"id": "plates", "anchor": "ground", "count": 1, "boxes": [[0, 500, 1000, 1000]]},
            {"id": "barrel", "count": 2, "size": cube, "boxes": [[150, 400, 250, 500], [750, 400, 850, 500]]},
            {"id": "pallet", "anchor": "on:plates", "count": 1, "size": cube, "boxes": [[450, 700, 550, 800]]},
            {"id": "desk", "count": 1, "size": cube, "boxes": [[750, 200, 850, 300]]},
            {"id": "sandbags", "anchor": "ground", "count": 1, "size": cube, "boxes": [[450, 900, 550, 1000]]}]
    items = [["BARREL 1", 1.5, 4.5, 1.0, 1.0, None, "item"], ["BARREL 2", 7.5, 4.5, 1.0, 1.0, None, "item"],
             ["PALLET 1", 4.5, 7.5, 1.0, 1.0, None, "item"], ["DESK 1", 7.5, 2.5, 1.0, 1.0, None, "item"]]
    plan = {"w": 10.0, "d": 10.0, "doors": [], "people": [], "items": items, "structure": ["plates"],
            "beyond": ["sandbags"], "rows": {item[0]: [item[0].split(" ")[0].lower()] for item in items}}
    inventory = {"picture": [1000, 1000], "rows": rows}
    assert [gap["row"] for gap in plan_checks.checked(plan, inventory, ["plates"]) if gap["kind"] == "placed"] == [
        "sandbags"]  # the check lists it, its plan's beyond notwithstanding
    plan, fixes = plan_fixes.fixed(plan, inventory)
    assert plan["beyond"] == [] and fixes[0].startswith("sandbags: at the concept's foot")
    sandbags = [item for item in plan["items"] if item[0] == "SANDBAGS 1"]
    assert sandbags and (sandbags[0][1], sandbags[0][2]) == (4.5, 9.5)  # its box's foot projects to y = 10
