"""Each plan item of a row that stands on, against or in something names what holds it, derived free from the scene
inventory's anchors, the concept's boxes and the plan (issue #72): base's garage door against its module's front, a
monitor on its console's top, a door in the plan's opening and the next one, with no opening left, on its wall, a
wall lamp the plan writer left on the walls item on a named wall's room side; and the file is kept beside the plan
with the plan's sha. Plans and inventories are small ones made here.

Each test names the break that turns it red (`Break: <file>: `old` -> `new``); each was applied once and seen red.

Run: PROPS_HOME=$(mktemp -d) .venv/bin/python -m pytest score/review/holders/test_each_plan_item_names_what_holds_it.py
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))

from score.review import holders, plan_checks  # noqa: E402

PICTURE = [1000, 600]


def plan_of(items, rows, **more):
    """A plan of items [name, x, y, wide, deep, facing, kind] tied to their rows, 20 x 12 m."""
    return {"w": 20.0, "d": 12.0, "items": items, "rows": rows, "shapes": {}, **more}


def by_row(found):
    return {entry["row"]: entry for entry in found["relations"]}


def test_base_s_garage_door_stands_against_its_module_s_front():
    """Base (2026-10-29): the plan lays the garage door to its module's west, but the concept shows its box within the
    module's across, its foot near the module's: against the module's side toward the viewer, S (the viewer looks
    north with no other rows to turn it by).
    Break: score/review/holders/__init__.py: `return snapped(right) if across > under[2] else snapped(toward)` ->
        `return snapped(right) if across > under[2] else snapped(-toward)`"""
    rows = [{"id": "module", "noun": "building", "anchor": "ground", "box": [500, 100, 900, 560]},
            {"id": "garage_door", "noun": "door", "anchor": "on:module", "size": [6.0, 0.5, 8.0],
             "box": [560, 300, 760, 540]}]
    plan = plan_of([["MODULE 1", 8.0, 1.0, 11.9, 17.2, None, "item"],
                    ["GARAGE DOOR 1", 4.1, 13.9, 4.4, 4.4, None, "item"]],
                   {"MODULE 1": ["module"], "GARAGE DOOR 1": ["garage_door"]})
    door = by_row(holders.relations(plan, {"rows": rows, "picture": PICTURE}))["garage_door"]
    assert (door["how"], door["holder"], door["face"]) == ("face", "MODULE 1", "S"), door


def test_a_monitor_stands_on_its_console_s_top():
    """The concept shows the monitor's foot over the console's by more than a quarter of the console's box, its top
    above the console's top quarter: on the console's top, its nearest item named.
    Break: score/review/holders/__init__.py: `return under[3] - seen[3] > TOP_SHARE * tall and seen[1] < under[1] +
        TOP_SHARE * tall` -> `return False`"""
    rows = [{"id": "console", "noun": "console", "anchor": "floor", "box": [300, 300, 700, 500]},
            {"id": "monitor", "noun": "monitor", "anchor": "on:console", "box": [400, 220, 480, 330]}]
    plan = plan_of([["CONSOLE 1", 2.0, 2.0, 3.0, 0.8, "S", "item"], ["CONSOLE 2", 12.0, 2.0, 3.0, 0.8, "S", "item"],
                    ["MONITOR 1", 6.0, 2.0, 0.5, 0.2, None, "item"]],
                   {"CONSOLE 1": ["console"], "CONSOLE 2": ["console"], "MONITOR 1": ["monitor"]})
    monitor = by_row(holders.relations(plan, {"rows": rows, "picture": PICTURE}))["monitor"]
    assert (monitor["how"], monitor["holder"]) == ("top", "CONSOLE 1"), monitor


def test_a_door_goes_in_the_plan_s_opening_and_the_next_on_its_wall():
    """Two door rows the plan writer left on the walls item, one door opening on the north wall: the first goes in
    it, the second, with no opening left, against the longest wall (no projection with no rows laid alike).
    Break: score/review/holders/__init__.py: `found = in_opening(item, row, plan, inventory, taken) if
        design_shell.fills_opening(row) else None` -> `found = None`"""
    rows = [{"id": "door", "noun": "door", "anchor": "wall", "size": [1.2, 0.1, 2.1]},
            {"id": "back_door", "noun": "door", "anchor": "wall", "size": [1.0, 0.1, 2.1]}]
    walls = [{"from": [0.0, 0.0], "to": [20.0, 0.0], "thick": 0.2}, {"from": [20.0, 0.0], "to": [20.0, 12.0], "thick": 0.2}]
    plan = plan_of([[plan_checks.WALLS_ITEM, 0.0, 0.0, 20.0, 12.0, None, "item"]],
                   {plan_checks.WALLS_ITEM: ["door", "back_door"]}, walls=walls,
                   openings=[{"kind": "door", "at": [5.0, 0.0], "wide": 1.4, "sill": 0.0, "head": 2.2}])
    found = by_row(holders.relations(plan, {"rows": rows, "picture": PICTURE}))
    assert found["door"]["how"] == "in" and found["door"]["opening"]["at"] == [5.0, 0.0], found["door"]
    assert found["back_door"]["how"] == "wall" and found["back_door"]["wall"]["to"] == [20.0, 0.0], found["back_door"]


def test_a_wall_lamp_stands_on_its_wall_s_room_side():
    """A lamp on the left wall (a structure row, part wall) the plan writer left on the walls item stands against the
    longest wall's middle, on the side of its line toward the plan's middle: walking it from (0, 0) to (0, 12) (y
    south), the room to +x is its line's side -1.
    Break: score/review/holders/__init__.py: `side = off_line(numpy.array([float(plan["w"]) / 2, float(plan["d"]) /
        2]), wall)[1]` -> `side = 1`"""
    rows = [{"id": "left_wall", "noun": "wall", "part": "wall", "anchor": "floor"},
            {"id": "wall_lamp", "noun": "lamp", "anchor": "on:left_wall", "size": [0.3, 0.2, 0.3]}]
    plan = plan_of([[plan_checks.WALLS_ITEM, 0.0, 0.0, 20.0, 12.0, None, "item"]],
                   {plan_checks.WALLS_ITEM: ["left_wall", "wall_lamp"]}, structure=["left_wall"],
                   walls=[{"from": [0.0, 0.0], "to": [0.0, 12.0], "thick": 0.2},
                          {"from": [0.0, 0.0], "to": [4.0, 0.0], "thick": 0.2}])
    lamp = by_row(holders.relations(plan, {"rows": rows, "picture": PICTURE}))["wall_lamp"]
    assert lamp["how"] == "wall" and lamp["wall"]["to"] == [0.0, 12.0] and lamp["side"] == -1, lamp
    assert lamp["spot"] == [0.0, 6.0], lamp


def test_the_relations_are_kept_beside_the_plan_with_its_sha(tmp_path, monkeypatch):
    """keep writes each place's relations under the relations folder, naming the kept plan's sha, and writes nothing
    again while plan and inventory stand.
    Break: score/review/holders/__init__.py: `if not path.is_file() or path.read_text() != found:` -> `if True:`"""
    for name in ("KEPT_PLANS", "KEPT_INVENTORY", "KEPT"):
        monkeypatch.setattr(holders, name, tmp_path / name)
        (tmp_path / name).mkdir()
    text = json.dumps(plan_of([], {}))
    (tmp_path / "KEPT_PLANS/hut.json").write_text(text)
    (tmp_path / "KEPT_INVENTORY/hut.json").write_text(json.dumps({"rows": []}))
    assert holders.keep(["hut", "nowhere"]) == ["hut"] and holders.keep(["hut"]) == []
    assert json.loads((tmp_path / "KEPT/hut.json").read_text())["plan"] == holders.plan_sha(text)
