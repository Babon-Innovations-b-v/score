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

import numpy

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))

from score.review import holders, plan_checks, plan_fixes  # noqa: E402

PICTURE = [1000, 600]


def plan_of(items, rows, **more):
    """A plan of items [name, x, y, wide, deep, facing, kind] tied to their rows, 20 x 12 m."""
    return {"w": 20.0, "d": 12.0, "items": items, "rows": rows, "shapes": {}, **more}


def by_row(found):
    return {entry["row"]: entry for entry in found["relations"]}


def by_item_of(found):
    return {entry["item"]: entry for entry in found["relations"]}


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
    Break: score/review/holders/__init__.py: `recess = recess_of(item, row, (middle(holder_item), item_way(holder_item,
        nearest[0]), holder_base),` -> `recess = None and recess_of(item, row, (middle(holder_item),
        item_way(holder_item, nearest[0]), holder_base),`"""
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
        TOP_SHARE * tall` -> `return False`
    Break: score/review/holders/__init__.py: held's `if said in ("under", "shelf"):` -> `if False:`, or placement's
        `(?<!left )(?<!right )` dropped (a monitor on the left of its console laid on its side)"""
    rows = [{"id": "console", "noun": "console", "anchor": "floor", "box": [300, 300, 700, 500]},
            {"id": "monitor", "noun": "monitor", "anchor": "on:console", "box": [400, 220, 480, 330]}]
    plan = plan_of([["CONSOLE 1", 2.0, 2.0, 3.0, 0.8, "S", "item"], ["CONSOLE 2", 12.0, 2.0, 3.0, 0.8, "S", "item"],
                    ["MONITOR 1", 6.0, 2.0, 0.5, 0.2, None, "item"]],
                   {"CONSOLE 1": ["console"], "CONSOLE 2": ["console"], "MONITOR 1": ["monitor"]})
    monitor = by_row(holders.relations(plan, {"rows": rows, "picture": PICTURE}))["monitor"]
    assert (monitor["how"], monitor["holder"]) == ("top", "CONSOLE 1"), monitor
    # its reading's placement word past `on`: under it at its foot, on its shelves within, on its side against it;
    # "left side of the console" says where on it, never its side (quarters' cables, poster, 2026-11-04)
    for where, wanted in (("under console", ("within", True)), ("on shelves", ("within", None)),
                          ("console side", ("face", None)), ("left side of console", ("top", None))):
        said = by_row(holders.relations(plan, {"rows": [rows[0], {**rows[1], "where": where}], "picture": PICTURE}))
        assert (said["monitor"]["how"], said["monitor"].get("under")) == wanted, (where, said["monitor"])


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


def test_a_spacesuit_within_its_locker_hangs_and_a_tray_on_a_shelf_does_not():
    """Round 32's docking airlock: its 1.8 m spacesuits at 0.1 m within their 2 m lockers hang (the assembly hangs
    them on the locker's back and judges them by touching). Within a holder, a thing hangs when its foot is over the
    holder's and under its top, it is at least half the holder's height and its top is in the holder's top quarter;
    a tray on a rack's shelf, a sticky note high in a locker, a 1.3 m thing low in a 2.5 m frame, a keyboard on its
    desk's top do not (none of them over all 26 env1 plans either).
    Break: score/review/holders/__init__.py: `and tall >= high / 2 and` -> `and` (the sticky note hangs)
    Break: score/review/holders/__init__.py: `and base + tall >= under + high * (1 - TOP_SHARE)` -> `` (the low
        thing in its frame hangs)"""
    shapes = {"LOCKER 1": {"base": 0.0, "tall": 2.0}, "SUIT 1": {"base": 0.1, "tall": 1.8},
              "RACK 1": {"base": 0.1, "tall": 2.2}, "TRAY 1": {"base": 1.0, "tall": 0.1},
              "NOTE 1": {"base": 1.5, "tall": 0.001}, "FRAME 1": {"base": 0.0, "tall": 2.5},
              "CHASSIS 1": {"base": 0.2, "tall": 1.3}, "DESK 1": {"base": 0.0, "tall": 0.8},
              "KEYBOARD 1": {"base": 0.8, "tall": 0.05}}
    plan = plan_of([], {}, shapes=shapes)
    found = {thing: holders.hangs([thing], [holder], plan) for thing, holder in (
        ("SUIT 1", "LOCKER 1"), ("TRAY 1", "RACK 1"), ("NOTE 1", "LOCKER 1"), ("CHASSIS 1", "FRAME 1"),
        ("KEYBOARD 1", "DESK 1"))}
    assert found == {"SUIT 1": True, "TRAY 1": False, "NOTE 1": False, "CHASSIS 1": False, "KEYBOARD 1": False}, found


def test_a_spot_in_another_holder_like_its_anchor_s_is_held_by_that_one():
    """Round 32's docking airlock: both spacesuits name the left locker, but the plan lays the second in the right
    locker's box, where it hung against the left locker's face 3 m away. The object its plan spot falls in holds it,
    where its anchor's does not and one like it (same anchor, a word shared) does; a spot in neither keeps its anchor.
    Break: score/review/holders/__init__.py: `if not any(inside(item, items[name]) for _, name in pairs):` ->
        `if False:`"""
    rows = [{"id": "locker_left", "noun": "locker", "anchor": "floor", "size": [0.8, 0.6, 2.0]},
            {"id": "locker_right", "noun": "locker", "anchor": "floor", "size": [0.8, 0.6, 2.0]},
            {"id": "suit", "noun": "spacesuit", "anchor": "on:locker_left", "size": [0.6, 0.4, 1.8]}]
    plan = plan_of([["LOCKER LEFT 1", 2.0, 2.0, 0.8, 0.6, "S", "item"],
                    ["LOCKER RIGHT 1", 10.0, 2.0, 0.8, 0.6, "S", "item"],
                    ["SUIT 1", 2.1, 2.1, 0.6, 0.4, "S", "item"], ["SUIT 2", 10.1, 2.1, 0.6, 0.4, "S", "item"],
                    ["SUIT 3", 6.0, 6.0, 0.6, 0.4, "S", "item"]],
                   {"LOCKER LEFT 1": ["locker_left"], "LOCKER RIGHT 1": ["locker_right"], "SUIT 1": ["suit"],
                    "SUIT 2": ["suit"], "SUIT 3": ["suit"]})
    found = {entry["item"]: (entry["how"], entry["holder"]) for entry in holders.relations(
        plan, {"rows": rows, "picture": PICTURE})["relations"] if entry["row"] == "suit"}
    assert found["SUIT 1"] == ("within", "LOCKER LEFT 1") and found["SUIT 2"] == ("within", "LOCKER RIGHT 1"), found
    assert found["SUIT 3"][1] == "LOCKER LEFT 1", found


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
    2026-11-06 (street's 3 m roller shutter cut on the 4.61 m wall its restaurant door already stood in): in a 4.6 x 6
    m room a 3 m shutter with no plan opening left, nearest the front wall the 1.5 m door's plan opening is on, is cut
    on the nearest wall with room beside its openings, the 6 m east wall, and no wall is crowded; a 0.5 m window
    nearest an empty 0.6 m stub is still cut on the stub, at its middle (camp's dome facets).
    Break: score/review/holders/__init__.py: `if wall_key(wall) in on_walls and not has_room(wall, on_walls,
        float(size[0])):` -> `if False:`
    Break: score/review/holders/__init__.py: `if wall_key(wall) in on_walls and not has_room(` -> `if not has_room(`
    Break: score/review/holders/__init__.py: `cut_in(spot, row, item, plan, [*standing, *({"row": row["id"], **piece}
        for piece in found if piece)])` -> `cut_in(spot, row, item, plan)`
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
    rows = [{"id": "door", "noun": "door", "anchor": "wall", "size": [1.0, 0.1, 2.1]},
            {"id": "shutter", "noun": "shutter", "anchor": "wall", "size": [3.0, 0.1, 3.0]}]
    small = [{"from": [0.0, 0.0], "to": [4.6, 0.0], "thick": 0.1}, {"from": [4.6, 0.0], "to": [4.6, 6.0], "thick": 0.1},
             {"from": [4.6, 6.0], "to": [0.0, 6.0], "thick": 0.1}, {"from": [0.0, 6.0], "to": [0.0, 0.0], "thick": 0.1}]
    plan = plan_of([["DOOR 1", 1.8, 0.0, 1.0, 0.1, None, "item"], ["SHUTTER 1", 2.5, 0.3, 3.0, 0.1, None, "item"]],
                   {"DOOR 1": ["door"], "SHUTTER 1": ["shutter"]}, walls=small,
                   openings=[{"kind": "door", "at": [2.3, 0.0], "wide": 1.5, "sill": 0.0, "head": 2.2}])
    found = holders.relations(plan, {"rows": rows, "picture": PICTURE})
    assert by_row(found)["door"]["opening"]["at"] == [2.3, 0.0], by_row(found)["door"]
    assert (by_row(found)["shutter"]["wall"]["from"], by_row(found)["shutter"]["wall"]["to"]) == (
        [4.6, 0.0], [4.6, 6.0]) and "crowded" not in found, found
    rows = [{"id": "window", "noun": "window", "anchor": "wall", "size": [0.5, 0.1, 0.5]}]
    plan = plan_of([["WINDOW 1", 5.0, 0.3, 0.5, 0.1, None, "item"]], {"WINDOW 1": ["window"]},
                   walls=[{"from": [5.0, 0.0], "to": [5.6, 0.0], "thick": 0.1},
                          {"from": [0.0, 3.0], "to": [12.0, 3.0], "thick": 0.1}])
    window = by_row(holders.relations(plan, {"rows": rows, "picture": PICTURE}))["window"]
    assert (window["wall"]["from"], window["opening"]["at"]) == ([5.0, 0.0], [5.3, 0.0]), window


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
        None` -> `return lefts`
    2026-11-07 (settle@storage): three pipes the plan draws on a 0.3 m pillar's N, S and E sides, the concept showing
    them on its S side, too short for the three: each turned to the side the plan draws it on, none crowded (storage's
    pillar pipes laid in one another on one side).
    Break: score/review/holders/__init__.py: `if not [turned for _, entries in crowded for turned in
        [turned_toward(entries, items)] if turned]:` -> `if True:`"""
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
    rows = [{"id": "pillar", "noun": "pillar", "anchor": "floor", "size": [0.3, 0.3, 3.0], "box": [500, 100, 600, 560]},
            {"id": "pillar_pipe", "noun": "pipe", "anchor": "on:pillar", "size": [0.13, 0.1, 3.0],
             "box": [530, 100, 570, 560]}]
    plan = plan_of([["PILLAR 1", 8.0, 5.0, 0.3, 0.3, None, "item"],
                    ["PILLAR PIPE 1", 8.1, 4.9, 0.1, 0.1, None, "item"],
                    ["PILLAR PIPE 2", 8.1, 5.3, 0.1, 0.1, None, "item"],
                    ["PILLAR PIPE 3", 8.3, 5.1, 0.1, 0.1, None, "item"]],
                   {"PILLAR 1": ["pillar"], **{f"PILLAR PIPE {number}": ["pillar_pipe"] for number in (1, 2, 3)}})
    found = holders.relations(plan, {"rows": rows, "picture": PICTURE})
    faces = [by_item_of(found)[f"PILLAR PIPE {number}"]["face"] for number in (1, 2, 3)]
    assert faces == ["N", "S", "E"] and "crowded" not in found, (faces, found.get("crowded"))


def test_things_drawn_past_their_holder_s_built_end_are_spread_inside_it():
    """Hub (#36, assembly@hub held): three 0.5 m monitors drawn against a 9 m console item stood past its 4.5 m built
    model's end, apart as drawn; the assembly kept each inside the face's ends and they overlapped there by 0.5 m. Kept
    inside the ends as the assembly keeps them they meet, so they are spread along it in their plan order, 0.2 m
    apart and 0.2 m inside its end.
    Break: score/review/holders/__init__.py: `kept = [kept_on_face(piece, half) for piece in pieces]` ->
        `kept = [piece["along"] for piece in pieces]`"""
    rows = [{"id": "console", "noun": "console", "anchor": "floor", "size": [4.5, 0.8, 1.0]},
            {"id": "monitor", "noun": "monitor", "anchor": "on:console", "size": [0.5, 0.1, 0.4]}]
    items = [["CONSOLE 1", 0.0, 4.0, 9.0, 1.0, "N", "item"]]
    items += [[f"MONITOR {number}", along, 5.0, 0.5, 0.1, None, "item"]
              for number, along in ((1, 6.5), (2, 7.5), (3, 8.4))]
    plan = plan_of(items, {"CONSOLE 1": ["console"], **{item[0]: ["monitor"] for item in items[1:]}})
    plan["shapes"] = {item[0]: {"base": 1.0} for item in items[1:]}
    found = holders.relations(plan, {"rows": rows, "picture": PICTURE})
    faces = [entry for entry in found["relations"] if entry["row"] == "monitor"]
    assert [(entry["how"], entry["face"]) for entry in faces] == [("face", "S")] * 3, faces
    assert [entry["spots"] for entry in faces] == [[[4.9, 5.05]], [[5.6, 5.05]], [[6.3, 5.05]]], faces
    assert "crowded" not in found, found


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
        2]), wall)[1]` -> `side = 1`
    2026-11-04: workshop's wall things were held on 0.16 m chords of 24 an arc, run backwards past 0 degrees round a
    wall the shell does not build, and the assembly shrank a 1 m panel to 0.2 m. A panel by a round wall drawn from
    315 to 45 degrees (radius 5 about (10, 6)) is held on the piece the shell builds there: from 0 to 15 degrees, 1.31 m.
    Break: score/review/holders/__init__.py walls_of: `for first, second in design_shell.written_lines(wall)]` ->
        `for first, second in zip(*[[[10 + 5 * numpy.cos(turn), 6 + 5 * numpy.sin(turn)] for turn in
        numpy.radians(numpy.linspace(315, 45, 25))][index:] for index in (0, 1)])]` (the old 24 pieces)
    #94: a board the reading puts on the floor 'leaning against the left wall' is held against that wall at no mount
    height, its foot on the floor, resting leaning; a small sign 'attached to the left wall' keeps its eye mount and
    rests attached; a plank 'leaning against the crate' on the crate stands against its side, never on its top.
    Break: score/review/holders/__init__.py: `if leaning_on_floor(row, plan):` -> `if False:`
    Break: score/review/holders/__init__.py: `mount = None if rests(row) == LEANING else mount_height(item, row,
        plan)` -> `mount = mount_height(item, row, plan)`
    Break: score/review/holders/__init__.py: `said = "side" if rests(row) == LEANING else placement(row,
        holder_row)` -> `said = placement(row, holder_row)`
    Break: score/review/holders/__init__.py: `found.append({"item": name, "row": row_id, **got, **rests_entry(row)})`
        -> `found.append({"item": name, "row": row_id, **got})` (the second, the held rows')"""
    turn = numpy.radians(7.5)
    middle = [10.0 + 4.6 * numpy.cos(turn), 6.0 + 4.6 * numpy.sin(turn)]
    round_plan = plan_of([["PANEL 1", middle[0] - 0.1, middle[1] - 0.1, 0.2, 0.2, None, "item"]], {"PANEL 1": ["panel"]},
                         walls=[{"arc": {"centre": [10.0, 6.0], "radius": 5.0, "start": 315.0, "end": 45.0},
                                 "thick": 0.2}])
    panel = by_row(holders.relations(round_plan, {"rows": [{"id": "panel", "noun": "panel", "anchor": "wall",
                                                             "size": [1.0, 0.1, 1.0]}], "picture": PICTURE}))["panel"]
    assert panel["how"] == "wall" and numpy.allclose(panel["wall"]["from"], [15.0, 6.0], atol=1e-3) and numpy.allclose(
        panel["wall"]["to"], [10.0 + 5 * numpy.cos(numpy.radians(15)), 6.0 + 5 * numpy.sin(numpy.radians(15))],
        atol=1e-3), panel
    rows = [{"id": "left_wall", "noun": "wall", "part": "wall", "anchor": "floor"},
            {"id": "wall_lamp", "noun": "lamp", "anchor": "on:left_wall", "size": [0.3, 0.2, 0.3]}]
    plan = plan_of([[plan_checks.WALLS_ITEM, 0.0, 0.0, 20.0, 12.0, None, "item"]],
                   {plan_checks.WALLS_ITEM: ["left_wall", "wall_lamp"]}, structure=["left_wall"],
                   walls=[{"from": [0.0, 0.0], "to": [0.0, 12.0], "thick": 0.2},
                          {"from": [0.0, 0.0], "to": [4.0, 0.0], "thick": 0.2}])
    lamp = by_row(holders.relations(plan, {"rows": rows, "picture": PICTURE}))["wall_lamp"]
    assert lamp["how"] == "wall" and lamp["wall"]["to"] == [0.0, 12.0] and lamp["side"] == -1, lamp
    assert lamp["spot"] == [0.0, 6.0], lamp
    rows += [{"id": "board", "noun": "board", "anchor": "floor", "where": "left, leaning against the left wall",
              "size": [0.4, 0.05, 0.6]},
             {"id": "sign", "noun": "sign", "anchor": "on:left_wall", "where": "left wall, attached to the left wall",
              "size": [0.4, 0.05, 0.3]},
             {"id": "crate", "noun": "crate", "anchor": "floor", "size": [1.0, 1.0, 1.0], "box": [400, 300, 600, 500]},
             {"id": "plank", "noun": "plank", "anchor": "on:crate", "where": "centre, leaning against the crate",
              "size": [0.3, 0.05, 0.8], "box": [450, 200, 550, 300]}]
    plan = plan_of([[plan_checks.WALLS_ITEM, 0.0, 0.0, 20.0, 12.0, None, "item"],
                    ["BOARD 1", 1.0, 5.0, 0.4, 0.1, None, "item"], ["CRATE 1", 9.5, 5.5, 1.0, 1.0, None, "item"],
                    ["PLANK 1", 9.8, 5.7, 0.3, 0.1, None, "item"]],
                   {plan_checks.WALLS_ITEM: ["left_wall", "wall_lamp", "sign"], "BOARD 1": ["board"],
                    "CRATE 1": ["crate"], "PLANK 1": ["plank"]}, structure=["left_wall"], walls=plan["walls"])
    found = by_row(holders.relations(plan, {"rows": rows, "picture": PICTURE}))
    board, sign, plank = found["board"], found["sign"], found["plank"]
    assert (board["how"], board["rests"], board["wall"]["to"]) == ("wall", "leaning", [0.0, 12.0]), board
    assert "height" not in board, board
    assert (sign["how"], sign["rests"], sign["height"]) == ("wall", "attached", 1.35), sign
    assert (plank["how"], plank["holder"], plank["rests"]) == ("face", "CRATE 1", "leaning"), plank
    assert "rests" not in found["wall_lamp"], found["wall_lamp"]


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


ROOM_WALLS = [{"from": [0.0, 0.0], "to": [20.0, 0.0], "thick": 0.2},
              {"from": [0.0, 12.0], "to": [20.0, 12.0], "thick": 0.2},
              {"from": [0.0, 0.0], "to": [0.0, 12.0], "thick": 0.2},
              {"from": [20.0, 0.0], "to": [20.0, 12.0], "thick": 0.2}]


def test_two_wall_panels_each_drawn_as_the_whole_room_stand_on_walls_of_their_own():
    """Engineroom (#36): the plan draws its two wall panels each as the whole room, on a hull that names no side; each
    stands at the middle of the nearest wall the other does not hold (N, then S: both 6 m from the middle), never both
    at the room's middle.
    Break: score/review/holders/__init__.py: `free = [wall for wall in walls if wall_key(wall) not in taken] or walls`
        -> `free = walls`"""
    rows = [{"id": "hull", "noun": "hull", "part": "wall", "anchor": "floor"},
            {"id": "wall_panel", "noun": "panel", "anchor": "on:hull", "size": [20.0, 12.0, 3.5]}]
    plan = plan_of([["PANEL 1", 0.5, 0.5, 19.0, 11.0, None, "item"], ["PANEL 2", 0.5, 0.5, 19.0, 11.0, None, "item"]],
                   {"PANEL 1": ["wall_panel"], "PANEL 2": ["wall_panel"]}, walls=ROOM_WALLS)
    found = {entry["item"]: entry for entry in holders.relations(plan, {"rows": rows, "picture": PICTURE})["relations"]}
    assert found["PANEL 1"]["wall"]["to"] == [20.0, 0.0] and found["PANEL 1"]["spot"] == [10.0, 0.0], found
    assert found["PANEL 2"]["wall"]["to"] == [20.0, 12.0] and found["PANEL 2"]["spot"] == [10.0, 12.0], found
    assert found["PANEL 1"]["side"] == 1 and found["PANEL 2"]["side"] == -1, found  # each on its room side


def test_lights_on_the_wall_their_anchor_names_spread_along_it():
    """Quarters (#36): its string lights and wall light, left on the walls item and anchored on its left wall, stand on
    the wall furthest to the viewer's left (x 0: the viewer looks north), not the longest; both at its spot, they are
    spread evenly along it, a third and two thirds of the way.
    Break: score/review/holders/__init__.py: `wall = named_wall(holder, plan, turn) if holder is not None else None`
        -> `wall = None`
    Break: score/review/holders/__init__.py: `if all(after - before >= WALL_APART for` -> `if all(after - before >= 0
        for`
    And the 2026-11-04 audit's wall, roof and seat faults: six tools on one item each stand at a spot of their own, at
    least their length and PIECE_GAP apart (they all stood at one), centred 1.5 m up (a small wall thing the plan gives
    no height); a 6 m pipe nearest a 2 m jamb stub stands on the 20 m wall instead (it was shrunk onto the stub); a
    crane 'top, spanning left to right' read on a wall hangs from the roof; a lamp 'high on the right wall' stands at
    a quarter under the room's top; a chair 'at the desk' stands before the desk's built side, SEAT_GAP clear, facing
    it (it stood at its plan box, 3 times the desk's size); three railings of a stair share its two sides, never one
    spot.
    2026-11-06 (laid-as-designed@garage): three 8 m ducts on three items at one spot on the 20 m wall stand one over
    another round their mount height, their tall and PIECE_GAP apart (garage's 10 m pipes 3 to 5 stood at one spot);
    two 1 m clocks at one spot are packed along their wall instead, at one height. Two railings on the floor drawn on
    one box (engineroom's railings 3 and 4) are parted: the second beside the first, PIECE_GAP clear, the shortest way
    with floor room (crates stand in front of and behind it); two on one box filling the room keep their spot.
    2026-11-06 (laid-as-designed@hangar, @street): a row of 3 pipes on 2 wall items lays its third at its first item,
    as the scene record does (writer.pieces_of), so that item's relation gives each of its 2 pieces its own spot
    (hangar's 8 pipes on 7 items: its first laid 2 at its one spot); a door row on the walls item and on an item of its
    own has no walls-item relation, which the record never lays, so its item takes the plan's door opening at it
    (street's restaurant doors and shutters: openings on the walls item crowded their wall, its own kept at one
    spot). Only a row whose words say it piles piles (PILE_WORDS, plan_fixes' own).
    2026-11-06 (laid-as-designed's floor part): railings "around engines", four drawn on one box and piled 0 to 3 m
    by the plan's fixes, stand round the two engines' sides on the floor, each its own spot (around_holders); a lantern
    string "above plaza" 6 m up hangs between the two towers that reach it (hung_between), and with no towers stays
    on the floor; a screen the plan stands at its deck's 3.3 m just behind it stands on the floor, one on the deck
    keeps the deck's height, and a crowd under it holds nothing up (stood_under).
    Break: score/review/holders/__init__.py: `writer.counted(row, plan).get("count")` -> `row.get("count")` (the
        dropped railings laid again on those left)
    Break: score/review/holders/__init__.py: `return counts[names.index(name)]` -> `return counts[0] if
        len(names) == 1 else int((shapes.get(name) or {}).get("count") or 1)`
    Break: score/review/holders/__init__.py: `if row is None or name not in tied.get(row_id, []):` -> `if row is None:`
    Break: score/review/holders/__init__.py: `names.remove(plan_checks.WALLS_ITEM)` -> `pass`
    Break: score/review/holders/__init__.py: `PILE_WORDS = {"pile", ` -> `PILE_WORDS = {`
    Break: score/review/holders/__init__.py: `parted_on_wall(found, rows, plan)` -> `pass`
    Break: score/review/holders/__init__.py: `parted_on_floor(found, items, plan, inventory)` -> `pass`
    Break: score/review/holders/__init__.py: `    around_holders(found, items, rows, plan, tied)` -> `    pass`
    Break: score/review/holders/__init__.py: `    hung_between(found, items, rows, plan)` -> `    pass`
    Break: score/review/holders/__init__.py: `    stood_under(found, items, rows, plan)` -> `    pass`
    Break: score/review/holders/__init__.py: `if (row_id != row["id"] or piles(row)) and row_id not in people` ->
        `if (row_id != row["id"] or piles(row))`
    Break: score/review/holders/__init__.py: `"height": round(base, 3)})` -> `})`
    Break: score/review/holders/__init__.py: `for rest in others):` -> `for rest in []):`
    Break: score/review/holders/__init__.py: `if run_needed(row, len(entries)) <= length:` -> `if True:`
    Break: score/review/holders/__init__.py: `entry["spot"] = [round(float(value), 3) for value in start + run *
        along]` -> `pass`
    Break: score/review/holders/__init__.py: `entry["pieces"] = wall_pieces(entry, items[entry["item"]], row, count,
        walls_of(plan))` -> `pass`
    Break: score/review/holders/__init__.py: `fitting = ([wall for wall in walls if wall_length(wall) >= need] if
        pieces == 1 else [])` -> `fitting = (walls if pieces == 1 else [])`
    2026-11-06 (hangar's second 32 m pipe of LARGE PIPES 1 laid as a diagonal chord across its corner, galley's
    cabinets and hub's panels round theirs): three 3.5 m cabinets on one item by the front wall of a 4.6 x 6 m room
    each lie flat along one wall, a piece not fitting before a corner starting past it; two 3.9 m pipes by an L of two
    4 m walls, which holds them only bent or in each other's corner room, go on the 10 m wall further off instead.
    Break: score/review/holders/__init__.py: `for along in flat_alongs(packed(alongs, length, long), runs, long,
        clear):` -> `for along in packed(alongs, length, long):`
    Break: score/review/holders/__init__.py: `if turn > ROUND_BEND:` -> `if False:`
    Break: score/review/holders/__init__.py: `spot = max(spot, low + clear + half)` -> `pass`
    Break: score/review/holders/__init__.py: `wall for wall in walls if holds_flat(chain_of(wall, walls, bend), row,
        pieces)]` -> `wall for wall in walls if chain_length(chain_of(wall, walls, bend)) >= need]`
    Break: score/review/holders/__init__.py: `spanning = kind == "wall" and spans(row)` -> `spanning = False`
    Break: score/review/holders/__init__.py: `return round(EYE_MOUNT - tall / 2, 3)` -> `return None`
    Break: score/review/holders/__init__.py: `seats_beside(found, items, rows, plan, tied)` -> `pass`
    Break: score/review/holders/__init__.py: `rails_along(found, plan)` -> `pass`
    2026-11-06 (hangar's eight 32 m pipes at 10 m in one another, four on its 64 m left wall): three 8 m ducts on
    three items 4 m apart along the 20 m front wall, 2 m up: the second slides along it clear of the first, the third,
    with no room left along it, stands its tall and PIECE_GAP over its height, under the wall's top (the ducts stood
    at one spot above clear the 6 m pipe at 1.4 m on their wall, the middle one two steps up); a wall thing on the
    floor is never stood up.
    Break: score/review/holders/__init__.py: `apart_on_walls(found, rows, plan)` -> `pass`
    Break: score/review/holders/__init__.py: `if (spot := slid_clear(context, row, plan, height, laid)) is not None:`
        -> `if False:`
    Break: score/review/holders/__init__.py: `if height <= 0.0:` -> `if False:`
    2026-11-07 (laid-as-designed@cockpit, @habitat, @workshop, @stairwell): a wall thing is parted at the size it is
    made at (prepare's groups.made_size: a run read round the room's walls one piece of it; a rug keeps its reading's);
    four 3 m pipes 'upper walls' on a 3.5 by 2 m room's south wall, which holds two (its band 2.2 to 2.6 m), put the
    other two on the north wall's run of two 1.75 m walls, each on a 3 m stretch of it (habitat's 18 pipes, three on
    its nearest 3.9 m wall); a tunnel keeps its stretch of wall, a monitor drawn on it before it slid off (workshop's
    monitors packed into its glass tunnel's chord); a 12 m tall conduit the plan stands 12 m up an 11.8 m wall stands
    on the floor (the stairwell's at 12 and 24 m); a 3 m board after two lamps on the only two walls it fits, with no
    room left on either, is laid first and the lamps part round it (the stairwell's 12 m tall conduits after its lamps).
    Break: score/review/holders/__init__.py: `made = groups.made_size(row, rows, plan, laid, box) if wall_held(row,
        by_id) else None` -> `made = None`
    Break: score/review/holders/__init__.py: `elif (moved := walled_clear(context, row, plan, height, boxes)) is not
        None:` -> `elif False:`
    Break: score/review/holders/__init__.py: `for chord in run_chords(plan, long)]` -> `for chord in []]`
    Break: score/review/holders/__init__.py: `for entry in sorted(order, key=lambda entry: not
        passage(rows[entry["row"]])):` -> `for entry in order:`
    Break: score/review/holders/__init__.py: `top = max(wall_top(wall, plan) - tall, 0.0)` -> `top = wall_top(wall,
        plan) - tall`
    Break: score/review/holders/__init__.py: `first += stuck` -> `return`
    2026-11-07 (settle@storage): two 3 m pipes drawn by one 3.2 m wall 2.6 m up, a ceiling light hung by it: the second
    stands under the first, never up into the light (storage's second wall pipe stood up into its ceiling light).
    Break: score/review/holders/__init__.py: `laid = [(box, math.inf) for box in hung_boxes(found, rows, plan)]` ->
        `laid = []`
    2026-11-07 (laid-as-designed@habitat: pipe_12 and pipe_17 stand at one spot): a 3 m pipe with no room on its own
    wall, moved to a 3 m inner wall where one of its row already stands at the spot it would take, on the wall's other
    face, takes another spot or height (habitat's pipes 12 and 17 stood back to back in one inner wall stretch's middle).
    Break: score/review/holders/__init__.py: `row_id == context["row"] and math.dist(spot, context["spot"]) <
        ONE_SPOT` -> `False and math.dist(spot, context["spot"]) < ONE_SPOT`"""
    rows = [{"id": "left_wall", "noun": "wall", "part": "wall", "anchor": "floor"},
            {"id": "string_lights", "noun": "lights", "anchor": "on:left_wall", "size": [3.0, 0.05, 0.05]},
            {"id": "wall_light", "noun": "light", "anchor": "on:left_wall", "size": [1.0, 0.1, 0.1]}]
    plan = plan_of([[plan_checks.WALLS_ITEM, 0.0, 0.0, 20.0, 12.0, None, "item"]],
                   {plan_checks.WALLS_ITEM: ["left_wall", "string_lights", "wall_light"]}, structure=["left_wall"],
                   walls=ROOM_WALLS)
    found = by_row(holders.relations(plan, {"rows": rows, "picture": PICTURE}))
    assert [found[row]["wall"]["to"] for row in ("string_lights", "wall_light")] == [[0.0, 12.0], [0.0, 12.0]], found
    assert sorted(found[row]["spot"] for row in ("string_lights", "wall_light")) == [[0.0, 4.0], [0.0, 8.0]], found
    rows = [{"id": "tools", "noun": "tool", "anchor": "wall", "where": "left wall", "size": [0.5, 0.05, 0.3], "count": 6},
            {"id": "pipe", "noun": "pipe", "anchor": "wall", "where": "back", "size": [6.0, 0.2, 0.2]},
            {"id": "crane", "noun": "crane", "anchor": "wall", "where": "top, spanning left to right",
             "size": [18.0, 2.0, 1.0]},
            {"id": "lamp", "noun": "lamp", "anchor": "wall", "where": "high on the right wall", "size": [0.8, 0.2, 0.3]},
            {"id": "desk", "noun": "desk", "anchor": "floor", "size": [2.0, 0.8, 0.8]},
            {"id": "chair", "noun": "chair", "anchor": "floor", "where": "at the desk", "size": [0.6, 0.6, 1.0]},
            {"id": "staircase", "noun": "staircase", "anchor": "floor"},
            {"id": "railing", "noun": "railing", "anchor": "on:staircase", "size": [3.0, 0.1, 1.0]},
            {"id": "duct", "noun": "duct", "anchor": "wall", "size": [8.0, 0.2, 0.2]},
            {"id": "clock", "noun": "clock", "anchor": "wall", "size": [1.0, 0.1, 0.3]}]
    items = [["TOOLS 1", 0.2, 5.0, 0.5, 2.0, None, "item"], ["PIPE 1", 10.3, 0.5, 0.5, 1.0, None, "item"],
             ["CRANE 1", 1.0, 1.0, 18.0, 2.0, None, "item"], ["LAMP 1", 19.5, 6.0, 0.5, 0.5, None, "item"],
             ["DESK 1", 8.0, 5.0, 6.0, 3.0, "S", "item"], ["CHAIR 1", 10.5, 9.0, 1.0, 1.0, None, "item"],
             *[[f"RAIL {number}", 2.0, 8.0, 1.0, 3.0, None, "item"] for number in (1, 2, 3)],
             *[[f"DUCT {number}", 6.0, 0.3, 8.0, 0.2, None, "item"] for number in (1, 2, 3)],
             *[[f"CLOCK {number}", 14.5, 11.5, 1.0, 0.2, None, "item"] for number in (1, 2)]]
    plan = plan_of(items, {item[0]: [item[0].split()[0].lower().replace("rail", "railing")] for item in items},
                   walls=[*ROOM_WALLS, {"from": [10.0, 0.0], "to": [10.0, 2.0], "thick": 0.2}],
                   stairs=[{"points": [[2.0, 8.0], [3.0, 8.0], [3.0, 11.0], [2.0, 11.0]], "angle": 90.0}])
    plan["shapes"] = {"TOOLS 1": {"count": 6}}
    found = holders.relations(plan, {"rows": rows, "picture": PICTURE})["relations"]
    by_item = {entry["item"]: entry for entry in found}
    tools = by_item["TOOLS 1"]["pieces"]
    alongs = sorted(piece["spot"][1] for piece in tools)
    assert len(tools) == 6 and all(piece["wall"]["from"][0] == piece["wall"]["to"][0] == 0.0 for piece in tools), tools
    assert all(after - before >= 0.5 + holders.PIECE_GAP - 1e-3 for before, after in zip(alongs, alongs[1:])), alongs
    assert {piece["height"] for piece in tools} == {1.35}, tools
    assert (by_item["PIPE 1"]["wall"]["from"], by_item["PIPE 1"]["wall"]["to"]) == ([0.0, 0.0], [20.0, 0.0]), by_item
    assert (by_item["CRANE 1"]["how"], by_item["CRANE 1"].get("to roof")) == ("ceiling", True), by_item["CRANE 1"]
    assert by_item["LAMP 1"]["height"] == 2.25, by_item["LAMP 1"]
    [seat] = by_item["CHAIR 1"]["pieces"]
    assert (by_item["CHAIR 1"]["beside"], seat["spot"], seat["way"]) == ("DESK 1", [11.0, 7.3], [1.0, 0.0]), seat
    rails = [by_item[f"RAIL {number}"]["pieces"][0]["spot"] for number in (1, 2, 3)]
    assert len({tuple(spot) for spot in rails}) == 3, rails
    ducts = [by_item[f"DUCT {number}"] for number in (1, 2, 3)]
    assert sorted(duct["height"] for duct in ducts) == [1.15, 1.65, 1.9], ducts  # 1.4 m is the 6 m pipe's there
    assert {(tuple(duct["spot"]), tuple(duct["wall"]["to"])) for duct in ducts} == {((10.0, 0.4), (20.0, 0.0))}, ducts
    clocks = [by_item[f"CLOCK {number}"] for number in (1, 2)]
    assert sorted(clock["spot"] for clock in clocks) == [[14.475, 12.0], [15.525, 12.0]], clocks
    assert {clock["height"] for clock in clocks} == {1.35}, clocks
    rows = [{"id": "floor_grating", "noun": "grating", "part": "floor", "anchor": "floor"},
            {"id": "railing", "noun": "railing", "anchor": "on:floor_grating", "size": [3.0, 2.0, 1.0], "count": 2},
            {"id": "crate", "noun": "crate", "anchor": "floor", "size": [1.0, 1.0, 1.0]}]
    items = [["RAILING 1", 4.0, 4.0, 3.0, 2.0, None, "item"], ["RAILING 2", 4.0, 4.0, 3.0, 2.0, None, "item"],
             ["CRATE 1", 5.0, 6.5, 1.0, 1.0, None, "item"], ["CRATE 2", 5.0, 1.0, 1.0, 1.0, None, "item"]]
    plan = plan_of(items, {"RAILING 1": ["railing"], "RAILING 2": ["railing"], "CRATE 1": ["crate"],
                           "CRATE 2": ["crate"]}, structure=["floor_grating"])
    railings = by_item_of(holders.relations(plan, {"rows": rows, "picture": PICTURE}))
    assert "spot" not in railings["RAILING 1"] and railings["RAILING 2"]["spot"] == [8.55, 5.0], railings
    plan = plan_of([["RAILING 1", 0.0, 0.0, 20.0, 12.0, None, "item"], ["RAILING 2", 0.0, 0.0, 20.0, 12.0, None,
                                                                         "item"]],
                   {"RAILING 1": ["railing"], "RAILING 2": ["railing"]}, structure=["floor_grating"])
    railings = by_item_of(holders.relations(plan, {"rows": rows[:2], "picture": PICTURE}))
    assert "spot" not in railings["RAILING 2"], railings  # no floor room beside it: kept as drawn
    rows = [{"id": "pipes", "noun": "pipes", "anchor": "wall", "where": "left wall", "size": [4.0, 0.2, 0.2],
             "count": 3}]
    plan = plan_of([["PIPES 1", 0.2, 1.0, 0.4, 4.0, None, "item"], ["PIPES 2", 0.2, 7.0, 0.4, 4.0, None, "item"]],
                   {"PIPES 2": ["pipes"], "PIPES 1": ["pipes"]}, walls=ROOM_WALLS)
    pipes = by_item_of(holders.relations(plan, {"rows": rows, "picture": PICTURE}))
    first = pipes["PIPES 1"]["pieces"]
    assert len(first) == 2 and abs(first[0]["spot"][1] - first[1]["spot"][1]) >= 4.0, first
    assert "pieces" not in pipes["PIPES 2"], pipes

    def flat(piece, walls):  # its face lies along one wall, inside its ends
        ends = [numpy.asarray(piece["wall"][key], float) for key in ("from", "to")]
        return any(all(holders.off_line(end, wall)[0] < 1e-3 and numpy.linalg.norm(holders.on_line(end, wall) - end)
                       < 1e-3 for end in ends) for wall in walls)
    small = [{"from": [0.0, 0.0], "to": [4.6, 0.0], "thick": 0.1}, {"from": [4.6, 0.0], "to": [4.6, 6.0], "thick": 0.1},
             {"from": [4.6, 6.0], "to": [0.0, 6.0], "thick": 0.1}, {"from": [0.0, 6.0], "to": [0.0, 0.0], "thick": 0.1}]
    rows = [{"id": "cabinets", "noun": "cabinets", "anchor": "wall", "size": [3.5, 0.4, 0.6], "count": 3}]
    plan = plan_of([["CABINETS 1", 1.0, 0.5, 3.5, 0.4, None, "item"]], {"CABINETS 1": ["cabinets"]}, walls=small)
    cabinets = by_item_of(holders.relations(plan, {"rows": rows, "picture": PICTURE}))["CABINETS 1"]["pieces"]
    assert len(cabinets) == 3 and all(flat(piece, small) for piece in cabinets), cabinets
    assert len({(tuple(piece["wall"]["from"]), tuple(piece["wall"]["to"])) for piece in cabinets}) == 3, cabinets
    bent = [{"from": [0.0, 4.0], "to": [0.0, 0.0], "thick": 0.1}, {"from": [0.0, 0.0], "to": [4.0, 0.0], "thick": 0.1},
            {"from": [0.0, 11.0], "to": [10.0, 11.0], "thick": 0.1}]
    rows = [{"id": "pipes", "noun": "pipes", "anchor": "wall", "size": [3.9, 0.2, 0.2], "count": 2}]
    plan = plan_of([["PIPES 1", 0.5, 0.5, 3.9, 0.2, None, "item"]], {"PIPES 1": ["pipes"]}, walls=bent)
    pipes = by_item_of(holders.relations(plan, {"rows": rows, "picture": PICTURE}))["PIPES 1"]
    assert pipes["wall"]["to"] == [10.0, 11.0] and all(flat(piece, bent[2:]) for piece in pipes["pieces"]), pipes
    rows = [{"id": "duct", "noun": "duct", "anchor": "wall", "size": [8.0, 0.2, 0.2]}]
    plan = plan_of([[f"DUCT {number}", 1.0 + 4.0 * number, 0.2, 8.0, 0.2, None, "item"] for number in (0, 1, 2)],
                   {f"DUCT {number}": ["duct"] for number in (0, 1, 2)}, walls=ROOM_WALLS,
                   shapes={f"DUCT {number}": {"base": 2.0} for number in (0, 1, 2)})
    ducts = by_item_of(holders.relations(plan, {"rows": rows, "picture": PICTURE}))
    assert [(ducts[f"DUCT {number}"]["spot"], ducts[f"DUCT {number}"].get("height")) for number in (0, 1, 2)] == [
        ([5.0, 0.3], None), ([13.05, 0.0], None), ([13.0, 0.3], 2.25)], ducts
    assert holders.wall_band(rows[0], 0.0, 0.2, ROOM_WALLS[0], plan) == (0.0, 0.0)

    def clear(found, rows, plan):  # no two wall things' built boxes meet by more than WALL_TOUCH
        by_id, boxes = {row["id"]: row for row in rows}, []
        for entry in found["relations"]:
            for piece in entry.get("pieces") or [entry]:
                if piece.get("how") == "wall":
                    boxes.append(holders.relation_box({**entry, **piece}, by_id[entry["row"]], plan))
        return all(holders.boxes_meet(box, other) <= holders.WALL_TOUCH for number, box in enumerate(boxes)
                   for other in boxes[number + 1:])
    rows = [{"id": "hull", "noun": "hull", "part": "wall", "anchor": "floor"},
            {"id": "red_pipes", "noun": "pipes", "anchor": "on:hull", "size": [20.0, 12.0, 0.2], "count": 4},
            {"id": "rug", "noun": "rug", "anchor": "floor", "size": [20.0, 12.0, 0.2]}]
    plan = plan_of([[f"RED PIPES {number}", 0.0, 0.0, 20.0, 12.0, None, "item"] for number in (1, 2)],
                   {f"RED PIPES {number}": ["red_pipes"] for number in (1, 2)}, walls=ROOM_WALLS)
    built = {row["id"]: row["size"] for row in holders.built_rows(rows, plan, {"rows": rows, "picture": PICTURE})
             if "size" in row}
    assert built == {"red_pipes": [16.0, 0.2, 0.2], "rug": [20.0, 12.0, 0.2]}, built  # the run's made piece, on a wall
    box = [{"from": [0.0, 0.0], "to": [3.5, 0.0], "thick": 0.1, "tall": 2.8},
           {"from": [3.5, 0.0], "to": [3.5, 2.0], "thick": 0.1, "tall": 2.8},
           {"from": [3.5, 2.0], "to": [1.75, 2.0], "thick": 0.1, "tall": 2.8},
           {"from": [1.75, 2.0], "to": [0.0, 2.0], "thick": 0.1, "tall": 2.8},
           {"from": [0.0, 2.0], "to": [0.0, 0.0], "thick": 0.1, "tall": 2.8}]
    rows = [{"id": "pipe", "noun": "pipe", "anchor": "wall", "where": "upper walls", "size": [3.0, 0.2, 0.2]}]
    plan = plan_of([[f"PIPE {number}", 0.15 + 0.1 * number, 0.1, 3.0, 0.2, None, "item"] for number in (1, 2, 3, 4)],
                   {f"PIPE {number}": ["pipe"] for number in (1, 2, 3, 4)}, walls=box, w=3.5, d=2.0,
                   outline=[[0.0, 0.0], [3.5, 0.0], [3.5, 2.0], [0.0, 2.0]],
                   shapes={f"PIPE {number}": {"base": 2.6} for number in (1, 2, 3, 4)})
    found = holders.relations(plan, {"rows": rows, "picture": PICTURE})
    pipes = by_item_of(found)
    assert [pipes[f"PIPE {number}"].get("height") for number in (1, 2, 3, 4)] == [None, 2.35, None, 2.35], pipes
    for number in (3, 4):  # the south wall full at both heights its band holds: on the north run of two walls
        pipe = pipes[f"PIPE {number}"]
        assert pipe["wall"]["from"][1] == pipe["wall"]["to"][1] == pipe["spot"][1] == 2.0 and pipe["side"] == 1, pipe
        assert abs(holders.wall_length(pipe["wall"]) - 3.0) < 1e-3 and "nearest wall with room" in pipe["why"], pipe
    assert clear(found, rows, plan), found
    rows = [{"id": "glass_tunnel", "noun": "tunnel", "anchor": "wall", "size": [5.0, 3.0, 3.0]},
            {"id": "monitor", "noun": "monitor", "anchor": "wall", "size": [0.4, 0.1, 0.3]}]
    plan = plan_of([["MONITOR 1", 9.8, 0.1, 0.4, 0.1, None, "item"],
                    ["GLASS TUNNEL 1", 7.5, 0.0, 5.0, 0.5, None, "item"]],
                   {"MONITOR 1": ["monitor"], "GLASS TUNNEL 1": ["glass_tunnel"]}, walls=ROOM_WALLS)
    found = holders.relations(plan, {"rows": rows, "picture": PICTURE})
    laid = by_item_of(found)
    assert laid["GLASS TUNNEL 1"]["spot"] == [10.0, 0.25] and "slid" in laid["MONITOR 1"]["why"], laid  # its own wall
    assert clear(found, rows, plan), found
    rows = [{"id": "conduit", "noun": "conduit", "anchor": "wall", "size": [3.0, 0.1, 12.0]}]
    tall = [{**wall, "tall": 11.8} for wall in ROOM_WALLS]
    plan = plan_of([["CONDUIT 1", 8.0, 0.1, 3.0, 0.1, None, "item"]], {"CONDUIT 1": ["conduit"]}, walls=tall,
                   shapes={"CONDUIT 1": {"base": 12.0}})
    assert by_item_of(holders.relations(plan, {"rows": rows, "picture": PICTURE}))["CONDUIT 1"]["height"] == 0.0
    rows = [{"id": "wall_lamp", "noun": "lamp", "anchor": "wall", "size": [0.2, 0.1, 0.3]},
            {"id": "notice_board", "noun": "board", "anchor": "wall", "size": [3.0, 0.1, 2.9]}]
    narrow = [{"from": [0.0, 0.0], "to": [3.2, 0.0], "thick": 0.1, "tall": 3.0},
              {"from": [3.2, 0.0], "to": [3.2, 1.0], "thick": 0.1, "tall": 3.0},
              {"from": [3.2, 1.0], "to": [0.0, 1.0], "thick": 0.1, "tall": 3.0},
              {"from": [0.0, 1.0], "to": [0.0, 0.0], "thick": 0.1, "tall": 3.0}]
    plan = plan_of([["LAMP 1", 1.5, 0.0, 0.2, 0.1, None, "item"], ["LAMP 2", 1.5, 0.9, 0.2, 0.1, None, "item"],
                    ["BOARD 1", 0.1, 0.0, 3.0, 0.1, None, "item"]],
                   {"LAMP 1": ["wall_lamp"], "LAMP 2": ["wall_lamp"], "BOARD 1": ["notice_board"]}, walls=narrow,
                   w=3.2, d=1.0, outline=[[0.0, 0.0], [3.2, 0.0], [3.2, 1.0], [0.0, 1.0]])
    found = holders.relations(plan, {"rows": rows, "picture": PICTURE})
    laid = by_item_of(found)
    assert laid["BOARD 1"]["spot"] == [1.6, 0.05] and laid["LAMP 1"]["wall"]["to"] == [0.0, 1.0], laid
    assert clear(found, rows, plan), found  # the board, stuck behind the lamps, laid first: the lamps part round it
    rows = [{"id": "pipe_thick", "noun": "pipe", "anchor": "wall", "size": [3.0, 0.15, 0.15]},
            {"id": "ceiling_light", "noun": "light", "anchor": "ceiling", "size": [0.8, 0.3, 0.1]}]
    plan = plan_of([["PIPE THICK 1", 0.25, 0.1, 3.0, 0.15, None, "item"],
                    ["PIPE THICK 2", 0.1, 0.2, 3.0, 0.15, None, "item"],
                    ["CEILING LIGHT 1", 2.0, 0.1, 0.8, 0.3, "S", "item"]],
                   {"PIPE THICK 1": ["pipe_thick"], "PIPE THICK 2": ["pipe_thick"],
                    "CEILING LIGHT 1": ["ceiling_light"]}, walls=narrow, w=3.2, d=1.0,
                   outline=[[0.0, 0.0], [3.2, 0.0], [3.2, 1.0], [0.0, 1.0]],
                   shapes={f"PIPE THICK {number}": {"base": 2.6} for number in (1, 2)})
    found = holders.relations(plan, {"rows": rows, "picture": PICTURE})
    laid, by_id = by_item_of(found), {row["id"]: row for row in rows}
    hung = holders.hung_boxes(found["relations"], by_id, plan)
    assert len(hung) == 1 and abs(hung[0][6] - 2.99) < 1e-6, hung  # under the walls' 3 m: no roof drawn
    assert laid["PIPE THICK 2"]["height"] == 2.4, laid["PIPE THICK 2"]  # 2.8 m would meet the light hung at 2.89 m
    assert all(holders.boxes_meet(holders.relation_box(laid[item], by_id["pipe_thick"], plan), hung[0])
               <= holders.WALL_TOUCH for item in ("PIPE THICK 1", "PIPE THICK 2")), laid
    rows = [{"id": "front_wall", "noun": "wall", "part": "wall", "anchor": "floor"},
            {"id": "shop_door", "noun": "door", "anchor": "on:front_wall", "size": [1.0, 0.1, 2.1]}]
    plan = plan_of([[plan_checks.WALLS_ITEM, 0.0, 0.0, 20.0, 12.0, None, "item"],
                    ["SHOP DOOR 1", 14.5, 0.0, 1.0, 0.2, None, "item"]],
                   {plan_checks.WALLS_ITEM: ["front_wall", "shop_door"], "SHOP DOOR 1": ["shop_door"]},
                   structure=["front_wall"], walls=ROOM_WALLS,
                   openings=[{"kind": "door", "at": [3.0, 0.0], "wide": 1.0, "sill": 0.0, "head": 2.1},
                             {"kind": "door", "at": [15.0, 0.0], "wide": 1.0, "sill": 0.0, "head": 2.1}])
    found = holders.relations(plan, {"rows": rows, "picture": PICTURE})["relations"]
    assert [(entry["item"], entry["opening"]["at"]) for entry in found if entry["row"] == "shop_door"] == [
        ("SHOP DOOR 1", [15.0, 0.0])], found
    assert holders.piles({"id": "sandbags", "size_words": "knee high pile"}) and not holders.piles(
        {"id": "railing", "where": "around engines", "size_words": "waist high"})
    assert holders.PILE_WORDS == plan_fixes.PILE_WORDS
    rows = [{"id": "grating", "noun": "grating", "part": "floor", "anchor": "floor"},
            {"id": "engine", "noun": "engine", "anchor": "on:grating", "size": [3.0, 1.5, 1.5]},
            {"id": "railing", "noun": "railing", "anchor": "on:grating", "where": "around engines",
             "size": [3.5, 0.4, 1.0]}]
    railings = {f"RAILING {number}": ["railing"] for number in range(1, 5)}
    plan = plan_of([["ENGINE 1", 3.0, 4.0, 3.0, 1.5, "N", "item"], ["ENGINE 2", 13.0, 4.0, 3.0, 1.5, "N", "item"],
                    *[[name, 6.0, 6.0, 3.5, 0.4, None, "item"] for name in railings]],
                   {"ENGINE 1": ["engine"], "ENGINE 2": ["engine"], **railings})
    plan["shapes"] = {f"RAILING {number}": {"base": float(number - 1), "tall": 1.0} for number in range(1, 5)}
    found = by_item_of(holders.relations(plan, {"rows": rows, "picture": PICTURE}))
    laid = [found[name] for name in railings]
    assert len({tuple(entry["spot"]) for entry in laid}) == 4 and {entry["height"] for entry in laid} == {0.0}, laid
    for entry in laid:  # each beside one engine's side, 0.2 m (its depth's half) and PIECE_GAP off it
        engine = numpy.array([4.5, 4.75]) if entry["spot"][0] < 10 else numpy.array([14.5, 4.75])
        off = numpy.abs(numpy.subtract(entry["spot"], engine))
        assert round(float(off.max()), 3) in (1.5 + 0.25, 0.75 + 0.25) and "round engine" in entry["why"], entry
    rows = [{"id": "plaza", "noun": "plaza", "part": "ground", "anchor": "ground"},
            {"id": "tower", "noun": "tower", "anchor": "on:plaza", "size": [2.0, 2.0, 18.0]},
            {"id": "crowd", "noun": "crowd", "anchor": "on:plaza", "size": [0.5, 0.3, 1.8]},
            {"id": "lantern_string", "noun": "lanterns", "anchor": "on:plaza", "where": "above plaza",
             "size": [16.0, 0.5, 0.5]},
            {"id": "stage_screen", "noun": "screen", "anchor": "on:plaza", "where": "stage back",
             "size": [8.0, 0.5, 6.0]}]
    items = [["TOWER 1", 0.0, 4.0, 2.0, 2.0, None, "item"], ["TOWER 2", 18.0, 4.0, 2.0, 2.0, None, "item"],
             ["CROWD 1", 0.0, 0.0, 20.0, 12.0, None, "item"], ["LANTERN STRING 1", 2.0, 5.0, 16.0, 0.5, None, "item"],
             ["STAGE SCREEN 1", 6.0, 8.0, 8.0, 0.5, None, "item"],
             ["STAGE SCREEN 2", 6.0, 10.0, 8.0, 0.5, None, "item"]]
    tied = {"TOWER 1": ["tower"], "TOWER 2": ["tower"], "CROWD 1": ["crowd"], "LANTERN STRING 1": ["lantern_string"],
            "STAGE SCREEN 1": ["stage_screen"], "STAGE SCREEN 2": ["stage_screen"]}
    square = plan_of(items, tied, levels=[{"height": 3.3, "points": [[5.0, 9.0], [15.0, 9.0], [15.0, 12.0],
                                                                      [5.0, 12.0]]}])
    square["shapes"] = {"LANTERN STRING 1": {"base": 6.0, "tall": 0.5}, "STAGE SCREEN 1": {"base": 3.3, "tall": 6.0},
                        "STAGE SCREEN 2": {"base": 3.3, "tall": 6.0}, "TOWER 1": {"tall": 18.0},
                        "TOWER 2": {"tall": 18.0}, "CROWD 1": {"tall": 1.8}}
    found = by_item_of(holders.relations(square, {"rows": rows, "picture": PICTURE}))
    assert (found["LANTERN STRING 1"]["how"], found["LANTERN STRING 1"]["holders"]) == (
        "hung", ["TOWER 1", "TOWER 2"]), found["LANTERN STRING 1"]
    assert found["STAGE SCREEN 1"]["height"] == 0.0 and "height" not in found["STAGE SCREEN 2"], found
    square["items"] = items[2:]
    found = by_item_of(holders.relations(square, {"rows": rows, "picture": PICTURE}))
    assert found["LANTERN STRING 1"]["how"] == "floor", found["LANTERN STRING 1"]
    own, inner = ({"from": [5.0, 4.0], "to": [6.0, 4.0], "thick": 0.1, "tall": 2.8},
                  {"from": [5.0, 5.0], "to": [8.0, 5.0], "thick": 0.1, "tall": 2.8})
    pipe = {"id": "pipe", "noun": "pipe", "anchor": "wall", "size": [3.0, 0.2, 0.2]}
    context = {"item": "PIPE 2", "row": "pipe", "how": "wall", "wall": own, "side": 1, "spot": [5.5, 4.0]}
    walled = plan_of([], {}, walls=[own, inner])
    moved, height = holders.walled_clear(context, pipe, walled, 1.0, [])
    assert (moved["spot"], height) == ([5.5, 5.0], 1.0), moved
    moved, height = holders.walled_clear(context, pipe, walled, 1.0, [], [("pipe", [5.5, 5.0], 1.0)])
    assert moved["spot"] != [5.5, 5.0] or abs(height - 1.0) >= holders.ONE_SPOT, (moved, height)
    # settle@engineroom, 2026-11-09: its plan took railings 5 to 8 off (no free floor), saying it lays 4 of the 8 its
    # concept counts; the relations lay one at each item left, as the scene record does, never two
    railed = {"items": [[f"RAIL {number}", 2.0 * number, 1.0, 1.0, 1.0, None, "item"] for number in (1, 2, 3, 4)],
              "rows": {f"RAIL {number}": ["railing"] for number in (1, 2, 3, 4)}}
    railing, tied = {"id": "railing", "count": 8}, {"railing": [f"RAIL {number}" for number in (1, 2, 3, 4)]}
    assert holders.pieces_at("RAIL 1", railing, railed, tied) == 2
    railed["dropped"] = [{"item": "railing", "why": "4 more of it than the place's free floor holds", "laid": 4}]
    assert [holders.pieces_at(f"RAIL {number}", railing, railed, tied) for number in (1, 2, 3, 4)] == [1, 1, 1, 1]


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


def test_an_opening_on_no_wall_the_shell_builds_is_named_loose():
    """The plan check that every opening sits on a wall the shell builds (its outline's or an inner wall's): in a
    20 x 12 m room an opening on its north wall and one on an inner wall across it at y 6 are on walls; one in the
    room's middle of nothing is named loose (the lab's doors, in walls the shell did not build, hung on nothing,
    motion@lab round 35; camp's airlock door still stands in its dome's gap).
    Break: score/review/holders/__init__.py: `if not design_shell.on_a_wall(plan, opening)]` -> `if False]`"""
    walls = [{"from": [0.0, 6.0], "to": [20.0, 6.0], "thick": 0.2}]
    openings = [{"kind": "door", "at": at, "wide": 1.0, "sill": 0.0, "head": 2.0} for at in ([5.0, 0.0], [10.0, 6.0],
                                                                                              [10.0, 3.0])]
    found = holders.relations(plan_of([], {}, walls=walls, openings=openings), {"rows": []})
    loose = [{"opening": 3, "at": [10.0, 3.0], "why": "it sits on no wall the shell builds"}]
    assert found.get("loose") == loose, found


def test_an_open_place_s_doorway_is_no_loose_opening():
    """The street (2026-10-31): its plan draws no walls (an open ground has none) and its stairwell door stands in
    its facade row, a doorway into the building: no wall opening of its own, so it is not named loose.
    Break: score/review/holders/__init__.py: `if "wall" not in shell_parts.parts(plan):` -> `if False:`"""
    opening = {"kind": "door", "at": [1.4, 19.4], "wide": 1.0, "sill": 0.14, "head": 2.2, "to": "stairwell"}
    street = plan_of([], {}, shell="kit", inside=False, walls=[], openings=[opening])
    assert "loose" not in holders.relations(street, {"rows": []}), "an open place's doorway"
