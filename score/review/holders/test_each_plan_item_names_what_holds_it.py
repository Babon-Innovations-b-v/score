"""Each plan item of a row that stands on, against or in something names what holds it, derived free from the scene
inventory's anchors, the concept's boxes and the plan (issue #72): base's garage door against its module's front, a
monitor on its console's top, monitors the reading anchors on one bank on the nearest of the consoles the concept
shows them on, a door in the plan's opening and the next one, with no opening left, in an opening cut for it, a
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


def test_a_moving_door_s_recess_holds_its_motion_and_a_static_one_sits_flush():
    """#72 (score, 2026-10-29: a door that opens needs a true opening in its holder model, one that never moves sits
    flush): base's garage door swings (its kind's rule, served: an astronaut passes), so its module gets a recess
    behind it on its S face, the model's +z (laid along E: its +x east), as deep as its 6 m swing sweeps plus
    RECESS_MARGIN, its middle 7.65 m left of the module's, widened on its hinge side (its own left, laid along E:
    the module's -x) by its 0.5 m thickness plus RECESS_MARGIN and the side wall the bake keeps (RECESS_WALL), so it
    lies RECESS_MARGIN clear of that wall at full open (2026-10-29: without the wall it lay flush against it); a
    sliding door's recess is its own 0.5 m thickness deep with its width and thickness of room on the side it slides
    to (+x); a shutter (no motion rule) has none.
    Break: score/review/holders/__init__.py: `room = (deep if rule["move"] == "swing" else wide + deep) + RECESS_MARGIN
        + RECESS_WALL` -> `... + RECESS_MARGIN` (the wall left out)
    Break: score/review/holders/__init__.py: `depth = (wide * abs(math.sin(math.radians(float(rule.get("angle") or
        90.0)))) if rule["move"] == "swing"` -> `depth = (deep if rule["move"] == "swing"`
    Break: score/review/holders/__init__.py: `recess = recess_of(item, row, (middle(holder_item), item_way(holder_item),
        holder_base), nearest[0],` -> `recess = None and recess_of(item, row, (middle(holder_item),
        item_way(holder_item), holder_base), nearest[0],`"""
    rows = [{"id": "module", "noun": "building", "anchor": "ground", "size": [12.0, 12.0, 12.0],
             "box": [500, 100, 900, 560]},
            {"id": "garage_door", "noun": "door", "anchor": "on:module", "size": [6.0, 0.5, 8.0],
             "box": [560, 300, 760, 540]},
            {"id": "shutter", "noun": "shutter", "anchor": "on:module", "size": [2.0, 0.1, 2.0],
             "box": [800, 400, 880, 540]},
            {"id": "astronaut", "noun": "astronaut", "anchor": "floor"}]
    plan = plan_of([["MODULE 1", 8.0, 1.0, 11.9, 17.2, None, "item"],
                    ["GARAGE DOOR 1", 4.1, 13.9, 4.4, 4.4, None, "item"],
                    ["SHUTTER 1", 20.0, 5.0, 0.1, 2.0, None, "item"]],
                   {"MODULE 1": ["module"], "GARAGE DOOR 1": ["garage_door"], "SHUTTER 1": ["shutter"]})
    found = by_row(holders.relations(plan, {"rows": rows, "picture": PICTURE}))
    recess = found["garage_door"]["recess"]
    assert (recess["model"], recess["axis"], recess["side"]) == ("module_1", "z", 1.0), recess
    assert recess["depth"] == 6.0 + holders.RECESS_MARGIN and recess["along"] == -7.65, recess
    room = round(0.5 + holders.RECESS_MARGIN + holders.RECESS_WALL, 3)
    assert (recess["room"], recess["room_side"]) == (room, -1.0), recess
    assert found["shutter"]["how"] == "face" and "recess" not in found["shutter"], found["shutter"]
    kinds = holders.row_kinds.table()
    sliding = {**kinds, "door": {**kinds["door"], "motion": {**kinds["door"]["motion"], "move": "slide"}}}
    recess = by_row(holders.relations(plan, {"rows": rows, "picture": PICTURE}, kinds=sliding))["garage_door"]["recess"]
    assert recess["depth"] == 0.5 + holders.RECESS_MARGIN and recess["room"] == 6.6 and recess["room_side"] == 1.0


def test_three_doors_on_one_face_item_stand_their_width_and_room_apart():
    """Street (#36): its three 1.0 m restaurant doors on one 1.74 m plan item were laid 0.58 m apart, their recesses
    in one another. Each piece of a face relation gets its own spot (`spots`), its width, its recess's room and
    OPENING_ROOM from the next, about the item's middle, and its recess's `pieces` read the same spots.
    Break: score/review/holders/__init__.py: `if length >= pitch * (len(placed) - 1) - 1e-9:` -> `if True:`"""
    rows = [{"id": "module", "noun": "building", "anchor": "ground", "size": [12.0, 12.0, 12.0],
             "box": [500, 100, 900, 560]},
            {"id": "restaurant_door", "noun": "door", "anchor": "on:module", "size": [1.0, 0.1, 2.1], "count": 3,
             "box": [560, 300, 760, 540]},
            {"id": "astronaut", "noun": "astronaut", "anchor": "floor"}]
    plan = plan_of([["MODULE 1", 8.0, 1.0, 11.9, 17.2, None, "item"],
                    ["RESTAURANT DOOR 1", 9.0, 18.4, 1.74, 0.5, None, "item"]],
                   {"MODULE 1": ["module"], "RESTAURANT DOOR 1": ["restaurant_door"]})
    door = by_row(holders.relations(plan, {"rows": rows, "picture": PICTURE}))["restaurant_door"]
    pitch = 1.0 + door["recess"]["room"] + holders.OPENING_ROOM
    xs = [spot[0] for spot in door["spots"]]
    assert len(xs) == 3 and all(abs(right - left - pitch) < 1e-3 for left, right in zip(xs, xs[1:])), door
    assert abs(xs[1] - 9.87) < 1e-3, door  # about the item's middle
    alongs = door["recess"]["pieces"]
    assert all(abs(abs(right - left) - pitch) < 1e-3 for left, right in zip(alongs, alongs[1:])), door["recess"]


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


def test_a_spacesuit_too_tall_for_its_locker_s_top_stands_within_it():
    """Round 32's docking airlock: the 1.8 m spacesuit's box lies in its 2 m locker's top half, so the concept reads
    it as on the locker's top, and the assembly stood it there through the 2.5 m ceiling. On a top it must fit under
    the place's height (its tallest wall or its highest roof): here within the locker, where the plan lays it; under
    a dome rising to 4.2 m (the workshop's robotic arm on its console) it stays on the top.
    Break: score/review/holders/__init__.py: `if on_top(row, holder_row) and fits_over(row, holder_row, room) and` ->
        `if on_top(row, holder_row) and`
    Break: score/review/holders/__init__.py: room_height's `+ [float(roof["top"]) for roof in plan.get("roofs") or []
        if roof.get("top")]` -> `+ []`"""
    rows = [{"id": "locker", "noun": "locker", "anchor": "floor", "size": [0.8, 0.6, 2.0], "box": [681, 565, 813, 1062]},
            {"id": "suit", "noun": "spacesuit", "anchor": "on:locker", "size": [0.6, 0.4, 1.8],
             "box": [687, 565, 812, 789]}]
    picture = [3000, 1200]
    walls = [{"from": [0.0, 0.0], "to": [20.0, 0.0], "thick": 0.2, "tall": 2.5}]
    items = [["LOCKER 1", 2.0, 2.0, 0.8, 0.6, "S", "item"], ["SUIT 1", 2.1, 2.1, 0.6, 0.4, "S", "item"]]
    tied = {"LOCKER 1": ["locker"], "SUIT 1": ["suit"]}
    low = by_row(holders.relations(plan_of(items, tied, walls=walls), {"rows": rows, "picture": picture}))["suit"]
    assert (low["how"], low["holder"]) == ("within", "LOCKER 1"), low
    domed = plan_of(items, tied, walls=walls, roofs=[{"kind": "dome", "eave": 2.5, "top": 4.2}])
    high = by_row(holders.relations(domed, {"rows": rows, "picture": picture}))["suit"]
    assert high["how"] == "top", high


def test_monitors_the_concept_shows_on_two_consoles_stand_on_the_nearest():
    """Hub (2026-10-29): the reading anchors all 38 monitors on its 3 x 0.8 m control bank (one anchor a row), but the
    concept shows them on the bank and on a console beside it. Each monitor stands on the nearest of the rows like
    its named holder (the same anchor, a word of what it is shared: control) that the concept shows its things on;
    the chair a monitor's foot also falls in, a row of another kind, holds none.
    Break: score/review/holders/__init__.py: `and kind_words(other) & kind_words(holder)]` -> `]`
    Break: score/review/holders/__init__.py: `items, shown = plan_items(plan), seen_holders(row, holder, rows, laid)`
        -> `items, shown = plan_items(plan), [holder]`"""
    rows = [{"id": "main_control_bank", "noun": "control bank", "anchor": "floor", "box": [100, 200, 400, 500]},
            {"id": "control_console_right", "noun": "console", "anchor": "floor", "box": [600, 300, 900, 500]},
            {"id": "chair", "noun": "chair", "anchor": "floor", "box": [650, 380, 700, 470]},
            {"id": "monitor_screen", "noun": "monitor", "anchor": "on:main_control_bank",
             "boxes": [[150, 150, 200, 260], [660, 300, 700, 400], [800, 240, 850, 340]]}]
    plan = plan_of([["MAIN CONTROL BANK 1", 1.0, 1.0, 3.0, 0.8, "S", "item"],
                    ["CONTROL CONSOLE RIGHT 1", 14.0, 1.0, 3.0, 0.8, "S", "item"],
                    ["CHAIR 1", 15.0, 2.5, 0.6, 0.6, None, "item"],
                    ["MONITOR SCREEN 1", 2.0, 1.2, 0.5, 0.1, None, "item"],
                    ["MONITOR SCREEN 2", 15.0, 1.2, 0.5, 0.1, None, "item"],
                    ["MONITOR SCREEN 3", 15.2, 2.6, 0.5, 0.1, None, "item"]],
                   {"MAIN CONTROL BANK 1": ["main_control_bank"], "CONTROL CONSOLE RIGHT 1": ["control_console_right"],
                    "CHAIR 1": ["chair"], "MONITOR SCREEN 1": ["monitor_screen"],
                    "MONITOR SCREEN 2": ["monitor_screen"], "MONITOR SCREEN 3": ["monitor_screen"]})
    found = {entry["item"]: entry["holder"] for entry in holders.relations(plan, {"rows": rows, "picture": PICTURE})[
        "relations"] if entry["row"] == "monitor_screen"}
    assert found == {"MONITOR SCREEN 1": "MAIN CONTROL BANK 1", "MONITOR SCREEN 2": "CONTROL CONSOLE RIGHT 1",
                     "MONITOR SCREEN 3": "CONTROL CONSOLE RIGHT 1"}, found


def test_a_door_goes_in_the_plan_s_opening_and_the_next_in_one_cut_for_it():
    """Two door rows the plan writer left on the walls item, one door opening on the north wall: the first goes in
    it; the second, with no opening left (cockpit's four rear doors, 2026-10-29: one opening on its plan), in an
    opening cut for it where its spot meets the nearest wall: with no projection (no rows laid alike) its one piece
    spread along the longest wall, at (10, 0), its own 1.0 m wide and 2.1 m tall from the floor.
    Break: score/review/holders/__init__.py: `found = in_opening(item, row, plan, inventory, taken) if
        design_shell.fills_opening(row) else None` -> `found = None`
    Break: score/review/holders/__init__.py: `found = [in_plan_opening(spot, row, plan, taken) or (cut_in(spot, row,
        item, plan) if spot is not None else None)` -> `found = [in_plan_opening(spot, row, plan, taken)`"""
    rows = [{"id": "door", "noun": "door", "anchor": "wall", "size": [1.2, 0.1, 2.1]},
            {"id": "back_door", "noun": "door", "anchor": "wall", "size": [1.0, 0.1, 2.1]}]
    walls = [{"from": [0.0, 0.0], "to": [20.0, 0.0], "thick": 0.2}, {"from": [20.0, 0.0], "to": [20.0, 12.0], "thick": 0.2}]
    plan = plan_of([[plan_checks.WALLS_ITEM, 0.0, 0.0, 20.0, 12.0, None, "item"]],
                   {plan_checks.WALLS_ITEM: ["door", "back_door"]}, walls=walls,
                   openings=[{"kind": "door", "at": [5.0, 0.0], "wide": 1.4, "sill": 0.0, "head": 2.2}])
    found = by_row(holders.relations(plan, {"rows": rows, "picture": PICTURE}))
    assert found["door"]["how"] == "in" and found["door"]["opening"]["at"] == [5.0, 0.0], found["door"]
    assert found["back_door"]["how"] == "in" and found["back_door"]["opening"] == {
        "at": [10.0, 0.0], "wide": 1.0, "sill": 0.0, "head": 2.1, "cut": True}, found["back_door"]


def test_a_window_takes_a_window_s_opening_and_a_door_a_door_s():
    """#36, camp: the relations gave the dome door's opening to a dome window (the plan draws only door openings), so
    the window stood in the door's swing. With one door opening at (5, 0) and a window laid first, at the north
    wall's east end: the window is cut where its spot meets the wall, kept 0.25 + OPENING_ROOM + the wall's 0.2 m
    inside its end (x 19.35), and the door takes the door opening.
    Break: score/review/holders/__init__.py: `if number not in taken and (opening["kind"] == "window") == (word ==
        "window")]` -> `if number not in taken]`
    Break: score/review/holders/__init__.py: `at = start + run * kept_along(float((on_line(spot, wall) - start) @
        run), length, keep)` -> `at = on_line(spot, wall)`"""
    rows = [{"id": "dome_window", "noun": "window", "anchor": "wall", "size": [0.5, 0.1, 0.5]},
            {"id": "dome_door", "noun": "door", "anchor": "wall", "size": [1.0, 0.1, 2.0]}]
    walls = [{"from": [0.0, 0.0], "to": [20.0, 0.0], "thick": 0.2}, {"from": [20.0, 0.0], "to": [20.0, 12.0], "thick": 0.2}]
    plan = plan_of([["DOME WINDOW 1", 19.6, 0.0, 0.2, 0.1, None, "item"],
                    ["DOME DOOR 1", 4.5, 0.0, 1.0, 0.2, None, "item"]],
                   {"DOME WINDOW 1": ["dome_window"], "DOME DOOR 1": ["dome_door"]}, walls=walls,
                   openings=[{"kind": "door", "at": [5.0, 0.0], "wide": 1.4, "sill": 0.0, "head": 2.2}])
    found = by_row(holders.relations(plan, {"rows": rows, "picture": PICTURE}))
    assert found["dome_window"]["opening"] == {"at": [19.35, 0.0], "wide": 0.5, "sill": 0.9, "head": 1.4,
                                               "cut": True}, found["dome_window"]
    assert found["dome_door"]["opening"]["at"] == [5.0, 0.0] and "cut" not in found["dome_door"]["opening"], found


def test_doors_laid_on_one_item_each_get_their_own_opening():
    """#36, cockpit: the plan lays its four 1.2 m rear doors on one item, so its relation gave them one opening and
    the scene record stacked all four in it. Each piece takes an opening of its own where the scene record lays it
    (along the item, x 8.25 to 9.75 on the north wall), cut at its built width and spread apart along the wall with
    OPENING_ROOM between them: middles 8.25, 9.65, 11.05, 12.45.
    Break: score/review/holders/__init__.py: `return [spot for spot, _ in piece_middles(item, row, plan)]` ->
        `return [middle(item)]`"""
    rows = [{"id": "rear_door", "noun": "door", "anchor": "wall", "size": [1.2, 0.2, 2.1], "count": 4}]
    plan = plan_of([["REAR DOOR 1", 8.0, 0.2, 2.0, 0.4, None, "item"]], {"REAR DOOR 1": ["rear_door"]},
                   walls=[{"from": [0.0, 0.0], "to": [20.0, 0.0], "thick": 0.2}])
    door = by_row(holders.relations(plan, {"rows": rows, "picture": PICTURE}))["rear_door"]
    assert [piece["opening"]["at"] for piece in door["pieces"]] == [[8.25, 0.0], [9.65, 0.0], [11.05, 0.0],
                                                                     [12.45, 0.0]], door
    assert all(piece["opening"]["wide"] == 1.2 and piece["opening"]["cut"] for piece in door["pieces"]), door


def test_openings_are_cut_at_their_built_widths_spread_apart_on_their_wall():
    """#36: stairwell's plan drew its 1 m doors and gate in 0.39 m openings, and the assembly shrank them to 0.39 m;
    habitat's 1 m door and 1.5 m window, drawn 0.42 m apart, would meet cut at their widths. On a 20 m wall a 1 m door
    in a 0.39 m opening at x 19.8 is cut at its own 1 m, a 2 m window in a 0.2 m opening at x 18.7 at its 2 m; meeting,
    they are spread apart in their order along the wall, 0.2 m between them and 0.2 m plus the wall's 0.2 m inside its
    end: the door at 20 - 0.4 - 0.5 = 19.1, the window 0.2 m before it at 17.4. A 4 m wall cannot hold two 2 m doors
    so: both stay as the plan draws them, the wall named crowded.
    Break: score/review/holders/__init__.py: `if wide <= float(opening["wide"]):` -> `if True:`
    Break: score/review/holders/__init__.py: `crowded = spread(found)` -> `crowded = []`
    Break: score/review/holders/__init__.py: `return lefts if lefts and lefts[0] >= room - 1e-9 else None` ->
        `return lefts`"""
    rows = [{"id": "door", "noun": "door", "anchor": "wall", "size": [1.0, 0.1, 2.1]},
            {"id": "window", "noun": "window", "anchor": "wall", "size": [2.0, 0.1, 1.0]}]
    walls = [{"from": [0.0, 0.0], "to": [20.0, 0.0], "thick": 0.2}]
    plan = plan_of([[plan_checks.WALLS_ITEM, 0.0, 0.0, 20.0, 12.0, None, "item"]],
                   {plan_checks.WALLS_ITEM: ["door", "window"]}, walls=walls,
                   openings=[{"kind": "door", "at": [19.8, 0.0], "wide": 0.39, "sill": 0.0, "head": 2.2},
                             {"kind": "window", "at": [18.7, 0.0], "wide": 0.2, "sill": 1.0, "head": 2.0}])
    found = holders.relations(plan, {"rows": rows, "picture": PICTURE})
    assert by_row(found)["door"]["opening"] == {"at": [19.1, 0.0], "wide": 1.0, "sill": 0.0, "head": 2.2,
                                                "cut": True}, by_row(found)["door"]
    assert by_row(found)["window"]["opening"] == {"at": [17.4, 0.0], "wide": 2.0, "sill": 1.0, "head": 2.0,
                                                  "cut": True}, by_row(found)["window"]
    assert "crowded" not in found
    rows = [{"id": "door", "noun": "door", "anchor": "wall", "size": [2.0, 0.1, 2.1]},
            {"id": "back_door", "noun": "door", "anchor": "wall", "size": [2.0, 0.1, 2.1]}]
    plan = plan_of([[plan_checks.WALLS_ITEM, 0.0, 0.0, 4.0, 12.0, None, "item"]],
                   {plan_checks.WALLS_ITEM: ["door", "back_door"]}, walls=[{"from": [0.0, 0.0], "to": [4.0, 0.0],
                                                                           "thick": 0.2}],
                   openings=[{"kind": "door", "at": [1.5, 0.0], "wide": 0.3, "sill": 0.0, "head": 2.2},
                             {"kind": "door", "at": [2.5, 0.0], "wide": 0.3, "sill": 0.0, "head": 2.2}])
    found = holders.relations(plan, {"rows": rows, "picture": PICTURE})
    assert sorted(entry["opening"]["wide"] for entry in found["relations"]) == [0.3, 0.3], found["relations"]
    assert [sorted(entry["rows"]) for entry in found["crowded"]] == [["back_door", "door"]], found.get("crowded")


def test_a_street_facade_stands_past_its_edge_and_its_units_on_its_face():
    """Street (2026-10-29): its building facades, wall rows the plan writer left on the walls item, stood at the
    street's middle, the AC units on them held by nothing (the plan draws no wall). A facade whose concept box stands
    in the view's left half stands past the plan's left edge (the viewer looking north: W), at its middle; a unit on
    it stands against its face toward the street, E.
    Break: score/review/holders/__init__.py: `return {"how": "face", "holder": plan_checks.WALLS_ITEM, "holder row":
        holder["id"],` -> `return {"how": "face", "holder": plan_checks.WALLS_ITEM, "holder row": None,`"""
    rows = [{"id": "left_building_facade", "noun": "building facade", "part": "wall", "anchor": "ground",
             "box": [0, 0, 300, 600]},
            {"id": "air_conditioner_unit", "noun": "air conditioner", "anchor": "on:left_building_facade",
             "box": [100, 200, 160, 240]}]
    plan = plan_of([[plan_checks.WALLS_ITEM, 0.0, 0.0, 6.0, 30.0, None, "item"],
                    ["AIR CONDITIONER UNIT 1", 0.5, 10.0, 0.8, 0.4, None, "item"]],
                   {plan_checks.WALLS_ITEM: ["left_building_facade"], "AIR CONDITIONER UNIT 1": ["air_conditioner_unit"]},
                   structure=["left_building_facade"], w=6.0, d=30.0)
    found = by_row(holders.relations(plan, {"rows": rows, "picture": PICTURE}))
    facade, unit = found["left_building_facade"], found["air_conditioner_unit"]
    assert (facade["how"], facade["edge"], facade["spot"]) == ("edge", "W", [0.0, 15.0]), facade
    assert (unit["how"], unit["holder row"], unit["face"]) == ("face", "left_building_facade", "E"), unit


def test_things_on_one_face_that_meet_at_their_built_widths_are_spread_along_it():
    """Street (#36): its 3 m window, stairwell entrance and roller shutters were laid at their built widths on 1.74 m
    plan items and overlapped on their facade's face. On a 30 m facade a 3 m window drawn at y 10 and a 3 m shutter
    drawn 1.74 m after it meet at their widths: the window keeps its spot, the shutter is spread on past it, 0.2 m
    (OPENING_ROOM) between them, to y 13.2; an air conditioner above both (3.0 m up, both 3.0 m tall at most) meets
    neither and keeps its spot. On a 6 m facade the two cannot stand so: both keep their spots, the face named
    crowded.
    Break: score/review/holders/__init__.py: `crowded = spread(found) + face_spread(found, items, rows, plan, inventory,
        kinds)` -> `crowded = spread(found)`
    Break: score/review/holders/__init__.py: `return first["band"][0] < second["band"][1] - 1e-9 and second["band"][0]
        < first["band"][1] - 1e-9` -> `return True`
    Break: score/review/holders/__init__.py: `return lefts if clear and lefts[0] >= -half + OPENING_ROOM - 1e-9 else
        None` -> `return lefts`"""
    def facade_plan(long):
        rows = [{"id": "left_building_facade", "noun": "building facade", "part": "wall", "anchor": "ground",
                 "size": [3.0, long, 20.0], "box": [0, 0, 300, 600]},
                {"id": "window", "noun": "window", "anchor": "on:left_building_facade", "size": [3.0, 0.1, 2.5]},
                {"id": "shutter", "noun": "shutter", "anchor": "on:left_building_facade", "size": [3.0, 0.1, 3.0]},
                {"id": "air_conditioner_unit", "noun": "air conditioner", "anchor": "on:left_building_facade",
                 "size": [0.8, 0.4, 0.6]}]
        plan = plan_of([[plan_checks.WALLS_ITEM, 0.0, 0.0, 6.0, long, None, "item"],
                        ["WINDOW 1", 0.5, long / 2 - 5.87, 0.5, 1.74, "E", "item"],
                        ["SHUTTER 1", 0.5, long / 2 - 4.13, 0.5, 1.74, "E", "item"],
                        ["AIR CONDITIONER UNIT 1", 0.5, long / 2 - 5.3, 0.4, 0.6, "E", "item"]],
                       {plan_checks.WALLS_ITEM: ["left_building_facade"], "WINDOW 1": ["window"],
                        "SHUTTER 1": ["shutter"], "AIR CONDITIONER UNIT 1": ["air_conditioner_unit"]},
                       structure=["left_building_facade"], w=6.0, d=long)
        plan["shapes"] = {"AIR CONDITIONER UNIT 1": {"base": 3.0}}
        return holders.relations(plan, {"rows": rows, "picture": PICTURE})
    found = facade_plan(30.0)
    spread = by_row(found)
    assert "spots" not in spread["window"] and "spots" not in spread["air_conditioner_unit"], spread
    assert spread["shutter"]["spots"] == [[0.75, 13.2]], spread["shutter"]
    assert "crowded" not in found and all("_holder" not in entry for entry in found["relations"]), found
    found = facade_plan(6.0)
    assert all("spots" not in entry for entry in found["relations"]), found["relations"]
    assert [(entry["face"], entry["rows"]) for entry in found["crowded"]] == [("E", ["air_conditioner_unit", "shutter", "window"])], found


def test_a_stair_the_plan_writer_left_unplaced_stands_at_the_plan_s_stair():
    """Greenhouse (2026-10-29): its two stairs rows, on its lower floor, stood at the room's middle (the walls item);
    the plan draws its stairs. Each stands at the next stair's middle, along its way up (90 degrees: south, the
    plan's y).
    Break: score/review/holders/__init__.py: `if words_of(row) & STAIR_WORDS and stairs:` -> `if False:`"""
    rows = [{"id": "lower_floor", "noun": "floor", "part": "floor", "anchor": "ground"},
            {"id": "stairs", "noun": "stairs", "anchor": "on:lower_floor", "count": 1}]
    plan = plan_of([[plan_checks.WALLS_ITEM, 0.0, 0.0, 20.0, 12.0, None, "item"]],
                   {plan_checks.WALLS_ITEM: ["lower_floor", "stairs"]}, structure=["lower_floor"],
                   stairs=[{"kind": "stair", "points": [[2.0, 2.0], [6.0, 2.0], [6.0, 3.0], [2.0, 3.0]], "angle": 90}])
    stairs = by_row(holders.relations(plan, {"rows": rows, "picture": PICTURE}))["stairs"]
    assert stairs["how"] == "floor" and stairs["spot"] == [4.0, 2.5] and stairs["way"] == [0.0, 1.0], stairs


def test_a_ramp_runs_up_to_the_nearest_raised_level_s_edge():
    """Airlock (settle@airlock, 2026-10-30): its ramp's plan item ended 0.42 m short of its porch deck (0.2 m up), its
    long side along the deck's edge, so the record laid it beside the deck, its end in the deck's slab. A ramp row on
    the ground climbs to the nearest raised level: its 2 m long side run straight up to that level's nearest edge
    (x 9.889, the way up east, into the level), its high end on the edge, its middle 1 m short of it at the item's y;
    a bench beside the same deck, no ramp, gets no relation, and with no raised level the ramp gets none either.
    Break: score/review/holders/__init__.py: `way = way if way @ (inner - start) > 0 else -way` -> `... < 0 ...`
    Break: score/review/holders/__init__.py: `None) or up_to_level(item, row, plan)` -> `None)`"""
    rows = [{"id": "ramp", "noun": "ramp", "anchor": "ground", "size": [1.2, 2.0, 0.2]},
            {"id": "bench", "noun": "bench", "anchor": "ground", "size": [1.2, 0.4, 0.4]}]
    items = [["RAMP 1", 8.267, 10.904, 1.2, 2.0, None, "item"], ["BENCH 1", 8.0, 9.0, 1.2, 0.4, None, "item"]]
    tied = {"RAMP 1": ["ramp"], "BENCH 1": ["bench"]}
    levels = [{"name": "the floor", "height": 0.0, "points": [[0.0, 0.0], [12.0, 0.0], [12.0, 12.0], [0.0, 12.0]]},
              {"name": "the porch deck", "height": 0.2,
               "points": [[9.889, 8.625], [15.298, 8.625], [15.298, 14.74], [9.889, 14.74]]}]
    found = by_row(holders.relations(plan_of(items, tied, levels=levels), {"rows": rows, "picture": PICTURE}))
    assert sorted(found) == ["ramp"], found
    ramp = found["ramp"]
    assert ramp["how"] == "ramp" and ramp["way"] == [1.0, 0.0] and ramp["height"] == 0.2, ramp
    assert ramp["spot"] == [8.889, 11.904] and ramp["edge"] == [[9.889, 14.74], [9.889, 8.625]], ramp
    flat = holders.relations(plan_of(items, tied, levels=levels[:1]), {"rows": rows, "picture": PICTURE})
    assert flat["relations"] == [], flat


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


def test_a_thing_drawn_past_its_wall_stands_in_the_room_and_a_tunnel_outside():
    """Hangar (held@hangar, 2026-10-30): two of its back-wall pipes were drawn 1.6 and 2.3 m past the wall the outline
    closes the room with, so they stood against its outer face, outside the hangar, 0.48 m in the built wall. A thing
    against a wall drawn past the outline stands on the room's side; a tunnel the concept shows meeting the wall from
    outside (garage's glass tunnel) keeps its side. Walking the back wall from (20, 12) to (0, 12), the room (north,
    -y) is its side +1.
    Break: score/review/holders/__init__.py: `or (placed and past_outline(spot, row, plan))` -> ``
    Break: score/review/holders/__init__.py: `and not kind_words(row) & PASSAGE_WORDS and not` -> `and not`"""
    rows = [{"id": "large_pipes", "noun": "pipes", "anchor": "wall", "size": [0.4, 8.0, 0.4]},
            {"id": "glass_tunnel", "noun": "tunnel", "anchor": "wall", "size": [2.5, 4.0, 2.5]}]
    items = [["LARGE PIPES 1", 10.0, 12.0, 1.0, 3.1, None, "item"], ["GLASS TUNNEL 1", 3.0, 12.3, 1.7, 4.2, "S", "item"]]
    plan = plan_of(items, {"LARGE PIPES 1": ["large_pipes"], "GLASS TUNNEL 1": ["glass_tunnel"]},
                   outline=[[0.0, 0.0], [20.0, 0.0], [20.0, 12.0], [0.0, 12.0]],
                   walls=[{"from": [20.0, 12.0], "to": [0.0, 12.0], "thick": 0.6}])
    found = by_row(holders.relations(plan, {"rows": rows, "picture": PICTURE}))
    assert found["large_pipes"]["how"] == "wall" and found["large_pipes"]["side"] == 1, found
    assert found["glass_tunnel"]["how"] == "wall" and found["glass_tunnel"]["side"] == -1, found


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
