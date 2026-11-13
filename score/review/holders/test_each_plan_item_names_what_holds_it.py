"""Each plan item of a row that stands on, against or in something names what holds it, derived free from the scene
inventory's anchors, the concept's boxes and the plan (issue #72): base's garage door against its module's front, a
monitor on its console's top, monitors the reading anchors on one bank on the nearest of the consoles the concept
shows them on, a door in the plan's opening and the next one, with no opening left, in an opening cut for it, a
wall lamp the plan writer left on the walls item on a named wall's room side; and the file is kept beside the plan
with the plan's sha. Plans and inventories are small ones made here.

One test asks it of every row of CASES: a world (a plan and its rows through holders.relations, keep over a home of
its own, or one of holders' judging functions with its inputs) and what its answer must hold, part by part. The rows'
ids begin with the behaviour they pin, named in brackets below with the breaks that turn its rows red
(`Break: <file>: `old` -> `new``); each was applied once, seen red and reverted.

Run: PROPS_HOME=$(mktemp -d) .venv/bin/python -m pytest score/review/holders/test_each_plan_item_names_what_holds_it.py

[garage-door] Base (2026-10-29): the plan lays the garage door to its module's west, but the concept shows its box within the
    module's across, its foot near the module's: against the module's side toward the viewer, S (the viewer looks
    north with no other rows to turn it by).
    Break: score/review/holders/__init__.py: `return snapped(right) if across > under[2] else snapped(toward)` ->
        `return snapped(right) if across > under[2] else snapped(-toward)`

[recess] #72 (score, 2026-10-29: a door that opens needs a true opening in its holder model, one that never moves sits
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
        item_way(holder_item, nearest[0]), holder_base),`

[three-doors] Street (#36): its three 1.0 m restaurant doors on one 1.74 m plan item were laid 0.58 m apart, their recesses
    in one another. Each piece of a face relation gets its own spot (`spots`), its width, its recess's room and
    OPENING_ROOM from the next, about the item's middle, and its recess's `pieces` read the same spots.
    Break: score/review/holders/__init__.py: `if length >= pitch * (len(placed) - 1) - 1e-9:` -> `if True:`

[on-top] The concept shows the monitor's foot over the console's by more than a quarter of the console's box, its top
    above the console's top quarter: on the console's top, its nearest item named.
    Break: score/review/holders/__init__.py: `return under[3] - seen[3] > TOP_SHARE * tall and seen[1] < under[1] +
        TOP_SHARE * tall` -> `return False`
    Break: score/review/holders/__init__.py: held's `if said in ("under", "shelf"):` -> `if False:`, or placement's
        `(?<!left )(?<!right )` dropped (a monitor on the left of its console laid on its side)
    Galley (settle@galley, 2026-11-11): its stove top and sink, flat, anchored on its 0.9 m counter at 0.9 m but drawn
    half past its front edge with boxes the concept does not show on its top, were laid against its side, the stove
    floating 0.76 m: a flat thing the plan stands at its holder's top is on it; one standing on the floor, and a
    monitor (not flat) there, keep the side.
    Break: score/review/holders/__init__.py: held's `if plan_top and said != "side"` -> `if False and said != "side"`
    Break: score/review/holders/__init__.py: lies_flat's `<= FLAT_SHARE * min(` -> `<= 9.0 * min(` (the monitor on
        the top), or stands_on_top's `<= STAND_REACH` -> `<= 9.0` (the stove on the floor on the top)
    its reading's placement word past `on`: under it at its foot, on its shelves within, on its side against it;
    "left side of the console" says where on it, never its side (quarters' cables, poster, 2026-11-04)
    Flat (settle@flat, 2026-11-11): its second blanket, drawn at 0.7 m on the first blanket on its 0.5 m bed, its
    middle 1 cm past the bed's side, was laid against that side 0.24 m up: one the plan stacks on what stands on its
    holder's top is on that top; with the first blanket drawn elsewhere on the bed it stands on nothing there and
    keeps the side. Break: score/review/holders/__init__.py: stands_on_top's `or stacked.on_stack(item, holder_item,
    plan,     STAND_REACH)` dropped (the stacked blanket on the bed's side), or stacked.py's `meets(other, item)]`
    ->     `True]` (the blanket elsewhere on the bed holds it up)

[too-tall] Round 32's docking airlock: the 1.8 m spacesuit's box lies in its 2 m locker's top half, so the concept reads
    it as on the locker's top, and the assembly stood it there through the 2.5 m ceiling. On a top it must fit under
    the place's height (its tallest wall or its highest roof): here within the locker, where the plan lays it; under
    a dome rising to 4.2 m (the workshop's robotic arm on its console) it stays on the top.
    Break: score/review/holders/__init__.py: `if on_top(row, holder_row) and fits_over(row, holder_row, room) and` ->
        `if on_top(row, holder_row) and`
    Break: score/review/holders/__init__.py: room_height's `+ [float(roof["top"]) for roof in plan.get("roofs") or []
        if roof.get("top")]` -> `+ []`
    A fitting on a run lower than it is tall (hangar's 0.6 m valve laid inside its 0.4 x 32 m pipe) is on the run,
    never within it; a sitter taller than its seat, clothes on a 1.5 x 0.5 m drying rack (no run) and a valve no taller
    than its pipe stay within (the 7 within relations of airlock, camp, quarters and street).
    Hangar (2026-11-11): its valve let down onto the round top of its pipe leaned 12.5 degrees on it; a fitting on a
    run is attached to it (the settle and the resting check take it as laid, mounted.resting_as_laid).
    Break: score/review/holders/__init__.py: on_run's relation's `"rests": ATTACHED,` dropped
    Break: score/review/holders/__init__.py: `if on_run(row, holder_row):` -> `if False:`
    Break: score/review/holders/__init__.py: on_run's `all(longest >= RUN_SHARE * other` -> `all(longest >= other`
        (the drying rack a run)
    Lab (settle@lab, 2026-11-11): its 0.2 m valves laid within their 0.1 x 0.1 x 2.5 m standing pipes floated 1.5 m:
    a fitting wider than a standing run is thick is against its side, the one away from the wall nearest the run
    (they went against the wall side the concept showed, 0.1 m into the wall); one on a lying run, one no wider than
    its standing run and one on a stub no run, keep their relation.
    Break: score/review/holders/__init__.py: held's `if not across_run(row, holder_row):` -> `if True:`, or
        across_run's `tall >= RUN_SHARE * thick and` dropped (the valve on the stub laid against it)
    Break: score/review/holders/__init__.py: held's `if off_wall:` -> `if False:` (the valve on the side the concept
        shows), or side_off_wall's `away * (numpy.abs(away) == numpy.abs(away).max())` -> `-away * (...)` (toward the
        wall)

[hangs] Round 32's docking airlock: its 1.8 m spacesuits at 0.1 m within their 2 m lockers hang (the assembly hangs
    them on the locker's back and judges them by touching). Within a holder, a thing hangs when its foot is over the
    holder's and under its top, it is at least half the holder's height and its top is in the holder's top quarter;
    a tray on a rack's shelf, a sticky note high in a locker, a 1.3 m thing low in a 2.5 m frame, a keyboard on its
    desk's top do not (none of them over all 26 env1 plans either).
    Break: score/review/holders/__init__.py: `and tall >= high / 2 and` -> `and` (the sticky note hangs)
    Break: score/review/holders/__init__.py: `and base + tall >= under + high * (1 - TOP_SHARE)` -> `` (the low
        thing in its frame hangs)

[other-holder] Round 32's docking airlock: both spacesuits name the left locker, but the plan lays the second in the right
    locker's box, where it hung against the left locker's face 3 m away. The object its plan spot falls in holds it,
    where its anchor's does not and one like it (same anchor, a word shared) does; a spot in neither keeps its anchor.
    Break: score/review/holders/__init__.py: `if not any(inside(item, items[name]) for _, name in pairs):` ->
        `if False:`

[nearest-console] Hub (2026-10-29): the reading anchors all 38 monitors on its 3 x 0.8 m control bank (one anchor a row), but the
    concept shows them on the bank and on a console beside it. Each monitor stands on the nearest of the rows like
    its named holder (the same anchor, a word of what it is shared: control) that the concept shows its things on;
    the chair a monitor's foot also falls in, a row of another kind, holds none.
    Break: score/review/holders/__init__.py: `and kind_words(other) & kind_words(holder)]` -> `]`
    Break: score/review/holders/__init__.py: `items, shown = plan_items(plan), seen_holders(row, holder, rows, laid)`
        -> `items, shown = plan_items(plan), [holder]`

[cut-opening] Two door rows the plan writer left on the walls item, one door opening on the north wall: the first goes in
    it; the second, with no opening left (cockpit's four rear doors, 2026-10-29: one opening on its plan), in an
    opening cut for it where its spot meets the nearest wall: with no projection (no rows laid alike) its one piece
    spread along the longest wall, at (10, 0), its own 1.0 m wide and 2.1 m tall from the floor.
    Break: score/review/holders/__init__.py: `found = in_opening(item, row, plan, inventory, taken) if
        design_shell.fills_opening(row) else None` -> `found = None`
    Break: score/review/holders/__init__.py: `found = [in_plan_opening(spot, row, plan, taken) or (cut_in(spot, row,
        item, plan) if spot is not None else None)` -> `found = [in_plan_opening(spot, row, plan, taken)`

[window-opening] #36, camp: the relations gave the dome door's opening to a dome window (the plan draws only door openings), so
    the window stood in the door's swing. With one door opening at (5, 0) and a window laid first, at the north
    wall's east end: the window is cut where its spot meets the wall, kept 0.25 + OPENING_ROOM + the wall's 0.2 m
    inside its end (x 19.35), and the door takes the door opening.
    Break: score/review/holders/__init__.py: `if number not in taken and (opening["kind"] == "window") == (word ==
        "window")]` -> `if number not in taken]`
    Break: score/review/holders/__init__.py: `at = start + run * kept_along(float((on_line(spot, wall) - start) @
        run), length, keep)` -> `at = on_line(spot, wall)`

[own-openings] #36, cockpit: the plan lays its four 1.2 m rear doors on one item, so its relation gave them one opening and
    the scene record stacked all four in it. Each piece takes an opening of its own where the scene record lays it
    (along the item, x 8.25 to 9.75 on the north wall), cut at its built width and spread apart along the wall with
    OPENING_ROOM between them: middles 8.25, 9.65, 11.05, 12.45.
    Break: score/review/holders/__init__.py: `return [spot for spot, _ in piece_middles(item, row, plan)]` ->
        `return [middle(item)]`

[built-widths] #36: stairwell's plan drew its 1 m doors and gate in 0.39 m openings, and the assembly shrank them to 0.39 m;
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
        `return lefts`

[facade] Street (2026-10-29): its building facades, wall rows the plan writer left on the walls item, stood at the
    street's middle, the AC units on them held by nothing (the plan draws no wall). A facade whose concept box stands
    in the view's left half stands past the plan's left edge (the viewer looking north: W), at its middle; a unit on
    it stands against its face toward the street, E.
    Break: score/review/holders/__init__.py: `return {"how": "face", "holder": plan_checks.WALLS_ITEM, "holder row":
        holder["id"],` -> `return {"how": "face", "holder": plan_checks.WALLS_ITEM, "holder row": None,`

[face-spread] Street (#36): its 3 m window, stairwell entrance and roller shutters were laid at their built widths on 1.74 m
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
        [turned_toward(entries, items)] if turned]:` -> `if True:`

[built-end] Hub (#36, assembly@hub held): three 0.5 m monitors drawn against a 9 m console item stood past its 4.5 m built
    model's end, apart as drawn; the assembly kept each inside the face's ends and they overlapped there by 0.5 m. Kept
    inside the ends as the assembly keeps them they meet, so they are spread along it in their plan order, 0.2 m
    apart and 0.2 m inside its end.
    Break: score/review/holders/__init__.py: `kept = [kept_on_face(piece, half) for piece in pieces]` ->
        `kept = [piece["along"] for piece in pieces]`

[stair] Greenhouse (2026-10-29): its two stairs rows, on its lower floor, stood at the room's middle (the walls item);
    the plan draws its stairs. Each stands at the next stair's middle, along its way up (90 degrees: south, the
    plan's y).
    Break: score/review/holders/__init__.py: `if words_of(row) & STAIR_WORDS and stairs:` -> `if False:`

[ramp] Airlock (settle@airlock, 2026-10-30): its ramp's plan item ended 0.42 m short of its porch deck (0.2 m up), its
    long side along the deck's edge, so the record laid it beside the deck, its end in the deck's slab. A ramp row on
    the ground climbs to the nearest raised level: its 2 m long side run straight up to that level's nearest edge
    (x 9.889, the way up east, into the level), its high end on the edge, its middle 1 m short of it at the item's y;
    a bench beside the same deck, no ramp, gets no relation, and with no raised level the ramp gets none either.
    Break: score/review/holders/__init__.py: `way = way if way @ (inner - start) > 0 else -way` -> `... < 0 ...`
    Break: score/review/holders/__init__.py: `None) or up_to_level(item, row, plan)` -> `None)`

[wall-side] A lamp on the left wall (a structure row, part wall) the plan writer left on the walls item stands against the
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
        -> `found.append({"item": name, "row": row_id, **got})` (the second, the held rows')

[past-wall] Hangar (held@hangar, 2026-10-30): two of its back-wall pipes were drawn 1.6 and 2.3 m past the wall the outline
    closes the room with, so they stood against its outer face, outside the hangar, 0.48 m in the built wall. A thing
    against a wall drawn past the outline stands on the room's side; a tunnel the concept shows meeting the wall from
    outside (garage's glass tunnel) keeps its side. Walking the back wall from (20, 12) to (0, 12), the room (north,
    -y) is its side +1.
    Break: score/review/holders/__init__.py: `or (placed and past_outline(spot, row, plan))` -> ``
    Break: score/review/holders/__init__.py: `and not kind_words(row) & PASSAGE_WORDS and not` -> `and not`

[two-panels] Engineroom (#36): the plan draws its two wall panels each as the whole room, on a hull that names no side; each
    stands at the middle of the nearest wall the other does not hold (N, then S: both 6 m from the middle), never both
    at the room's middle.
    Break: score/review/holders/__init__.py: `free = [wall for wall in walls if wall_key(wall) not in taken] or walls`
        -> `free = walls`

[wall-spread] Quarters (#36): its string lights and wall light, left on the walls item and anchored on its left wall, stand on
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
    Break: score/review/holders/__init__.py: stair_sides' `**({"height": float(stair["from"])} if "from" in stair else
        {}),` dropped, or relation's `"rests": ATTACHED,` dropped (the stairwell's railings at their items' heights,
        dropped loose)
    Break: score/review/holders/__init__.py: relations' `or stood_on(item, row, rows, plan, items, laid)` dropped (the
        lamps over the desk and over nothing held by nothing), or stood_on's `if base / 2 < found[0] <= base +
        STAND_REACH` -> `if found[0] <= base + STAND_REACH` (the lamp over the rug on the rug) or -> `if True` (the lamp
        over the shelf on its top, inside it), or its `if named:` -> `if False:` (the TV on the floor), or its `if base
        <= max(STAND_REACH, tall / 2): return None` dropped (the lamp on the floor given a relation)
    Break: score/review/holders/__init__.py: relations' `got = named_top.named_top(got, item, row, rows, plan, items,
        laid, tied)` dropped (airlock's case on its floor plates 'on bench' left on the floor), or
        score/review/holders/named_top.py: `if base <= max(holders.STAND_REACH, tall / 2) or not
        holders.where_words(row) & ON_WORDS:` -> `if not holders.where_words(row) & ON_WORDS:` (the box drawn on the
        floor 'on bench' laid on the bench) or -> `if base <= max(holders.STAND_REACH, tall / 2):` (the engine room's
        railings drawn up 'around engines' laid on an engine's top)
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
        ONE_SPOT` -> `False and math.dist(spot, context["spot"]) < ONE_SPOT`
    2026-11-10 (laid-as-designed@habitat: kitchen cabinets 1 and 2, 4 and 5 0.10 and 0.12 m in each other): a wall
    thing is parted on its wall's face as the scene record lays it, ended at the walls meeting it at a corner
    (corner_trims), not on its wall's line: a 0.8 m cabinet drawn at the end of a 3.2 m line whose corner walls are
    0.4 m thick is kept 0.2 m further in, so the one drawn 0.05 m clear of it on the line slides clear of it.
    Break: score/review/holders/__init__.py: `first, last = corner_trims(plan, start, end)  # its face's ends` ->
        `first, last = 0.0, 0.0  # its face's ends`
    settle@stairwell, 2026-11-10: its railings laid at their plan items' heights, 0.5 to 3 m off their flights'
    feet, and dropped as loose: each stands at its flight's foot, attached to it
    settle@habitat, @hangar, @quarters, 2026-11-10: a floor row's own item its plan stands up on nothing its row
    names (table lamps 0.8 m up 'in living areas, bedrooms', bench tools 1 m up 'on the work bench') had no relation
    and fell in the drop. A lamp 0.8 m up over a 0.78 m desk stands on its top; one over nothing stands on the
    floor; one over a 1.2 m shelf, whose top is over it, on the floor too, and one over a 2 cm rug no holder of it
    but on the floor at the rug's top; one on the floor has no relation; a TV 0.4 m up 'on tv stand' over nothing
    stands on the nearest TV stand's top.
    settle@airlock, 2026-11-11: its open case, anchored on its floor plates but 'on bench', drawn 0.49 m up beside
    the bench's top, was read as on the floor and floated 0.42 m: it stands on the bench's top; a box 'on bench' its
    plan draws on the floor stays there
    settle@engineroom, 2026-11-09: its plan took railings 5 to 8 off (no free floor), saying it lays 4 of the 8 its
    concept counts; the relations lay one at each item left, as the scene record does, never two

[kept] keep writes each place's relations under the relations folder, naming the kept plan's sha, and writes nothing
    again while plan and inventory stand.
    Break: score/review/holders/__init__.py: `if not path.is_file() or path.read_text() != found:` -> `if True:`

[loose] The plan check that every opening sits on a wall the shell builds (its outline's or an inner wall's): in a
    20 x 12 m room an opening on its north wall and one on an inner wall across it at y 6 are on walls; one in the
    room's middle of nothing is named loose (the lab's doors, in walls the shell did not build, hung on nothing,
    motion@lab round 35; camp's airlock door still stands in its dome's gap).
    Break: score/review/holders/__init__.py: `if not design_shell.on_a_wall(plan, opening)]` -> `if False]`

[open-doorway] The street (2026-10-31): its plan draws no walls (an open ground has none) and its stairwell door stands in
    its facade row, a doorway into the building: no wall opening of its own, so it is not named loose.
    Break: score/review/holders/__init__.py: `if "wall" not in shell_parts.parts(plan):` -> `if False:`
"""
import contextlib
import json
import pathlib
import sys
import tempfile
from unittest import mock

import numpy
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))

from score.review import holders, plan_checks, plan_fixes  # noqa: E402

PICTURE = [1000, 600]
ABSENT = type("Absent", (), {"__repr__": lambda self: "ABSENT"})()  # a key the answer does not hold


def plan_of(items, rows, **more):
    """A plan of items [name, x, y, wide, deep, facing, kind] tied to their rows, 20 x 12 m."""
    return {"w": 20.0, "d": 12.0, "items": items, "rows": rows, "shapes": {}, **more}


def relate(plan, rows, picture=PICTURE, kinds=None):
    """The place's relations through holders.relations, indexed by row and by item, with the world they came from."""
    found = holders.relations(plan, {"rows": rows, **({"picture": picture} if picture else {})}, kinds=kinds)
    return {**found, "row": {entry["row"]: entry for entry in found["relations"]},
            "item": {entry["item"]: entry for entry in found["relations"]}, "world": {"plan": plan, "rows": rows}}


def kept(plan, inventory):
    """keep run twice over one place in a home of its own (and a place with no files): what each run wrote, and the
    sha the kept file names."""
    with tempfile.TemporaryDirectory() as home, contextlib.ExitStack() as stack:
        for name in ("KEPT_PLANS", "KEPT_INVENTORY", "KEPT"):
            folder = pathlib.Path(home) / name
            folder.mkdir()
            stack.enter_context(mock.patch.object(holders, name, folder))
        (pathlib.Path(home) / "KEPT_PLANS/hut.json").write_text(json.dumps(plan))
        (pathlib.Path(home) / "KEPT_INVENTORY/hut.json").write_text(json.dumps(inventory))
        first, second = holders.keep(["hut", "nowhere"]), holders.keep(["hut"])
        return {"first": first, "second": second,
                "sha": json.loads((pathlib.Path(home) / "KEPT/hut.json").read_text())["plan"]}


# What a want's path reads past a key: measures of the value reached (each takes the value and the whole answer).
def each(*segments):
    return lambda value, root: [probe(part, segments, root) for part in value]


def among(*keys):
    return lambda value, root: [value.get(key, ABSENT) for key in keys]


def where(key, wanted):
    return lambda value, root: [part for part in value if part.get(key) == wanted]


def by_id(field):
    return lambda value, root: {row["id"]: row[field] for row in value if field in row}


def ordered(value, root):
    return sorted(value)


def steps(value, root):
    return [after - before for before, after in zip(value, value[1:])]


def magnitude(value, root):
    return [abs(part) for part in value]


def count(value, root):
    return len(value)


def keys(value, root):
    return sorted(value)


def unique(value, root):
    return [json.loads(text) for text in sorted({json.dumps(part) for part in value})]


def distinct(value, root):
    return len(unique(value, root))


def length(value, root):
    return holders.wall_length(value)


def lies_flat(walls):
    """1 when a piece's face lies along one of the walls, both its ends on that wall's line inside its ends."""
    def measure(piece, root):
        ends = [numpy.asarray(piece["wall"][key], float) for key in ("from", "to")]
        return any(all(holders.off_line(end, wall)[0] < 1e-3 and numpy.linalg.norm(holders.on_line(end, wall) - end)
                       < 1e-3 for end in ends) for wall in walls)
    return measure


def off_nearest(points):
    """How far a spot stands off the nearest of the points along its furthest axis, to the mm."""
    def measure(spot, root):
        nearest = min(points, key=lambda point: numpy.linalg.norm(numpy.subtract(spot, point)))
        return round(float(numpy.abs(numpy.subtract(spot, nearest)).max()), 3)
    return measure


def world_rows(root):
    return {row["id"]: row for row in root["world"]["rows"]}


def clear(found, root):
    """The most two wall things' built boxes meet by."""
    rows, plan, boxes = world_rows(root), root["world"]["plan"], []
    for entry in found["relations"]:
        for piece in entry.get("pieces") or [entry]:
            if piece.get("how") == "wall":
                boxes.append(holders.relation_box({**entry, **piece}, rows[entry["row"]], plan))
    return max((holders.boxes_meet(box, other) for number, box in enumerate(boxes) for other in boxes[number + 1:]),
               default=0.0)


def hung(found, root):
    return holders.hung_boxes(found["relations"], world_rows(root), root["world"]["plan"])


def meets_hung(item):
    """How far the item's built box meets the first box hung from the roof."""
    def measure(found, root):
        entry = found["item"][item]
        box = holders.relation_box(entry, world_rows(root)[entry["row"]], root["world"]["plan"])
        return holders.boxes_meet(box, hung(found, root)[0])
    return measure


def elsewhere(spot, height):
    """1 when walled_clear's answer takes another spot or a height ONE_SPOT off the one given."""
    return lambda value, root: value[0]["spot"] != spot or abs(value[1] - height) >= holders.ONE_SPOT


def probe(value, path, root):
    """The part of an answer a want's path names: `a/b/0` keys and list places, measures between them; ABSENT when
    its last key is not there (a key missing before it fails the row)."""
    parts = [step for segment in path for step in ([segment] if callable(segment) else segment.split("/"))]
    for number, step in enumerate(parts):
        if callable(step):
            value = step(value, root)
        elif isinstance(value, (list, tuple)) and step.isdigit():
            value = value[int(step)]
        elif number == len(parts) - 1 or step in value:
            value = value.get(step, ABSENT)
        else:
            raise KeyError(f"{step} of {'/'.join(map(str, parts))} not in {sorted(value)}")
    return value


class Near:
    """Within `tol` of the value, at the same shape."""
    def __init__(self, value, tol=1e-3):
        self.value, self.tol = value, tol

    def __eq__(self, got):
        return got is not ABSENT and numpy.shape(got) == numpy.shape(self.value) and bool(numpy.all(
            numpy.abs(numpy.asarray(got, float) - numpy.asarray(self.value, float)) < self.tol))

    def __repr__(self):
        return f"Near({self.value!r}, {self.tol})"


class AtLeast:
    """At least the value (every one of a list)."""
    def __init__(self, value):
        self.value = value

    def __eq__(self, got):
        return got is not ABSENT and all(part >= self.value for part in (got if isinstance(got, list) else [got]))

    def __repr__(self):
        return f"AtLeast({self.value})"


class AtMost:
    """At most the value."""
    def __init__(self, value):
        self.value = value

    def __eq__(self, got):
        return got is not ABSENT and got <= self.value

    def __repr__(self):
        return f"AtMost({self.value})"


class Each:
    """Every one of a list as wanted."""
    def __init__(self, wanted):
        self.wanted = wanted

    def __eq__(self, got):
        return isinstance(got, list) and all(self.wanted == part for part in got)

    def __repr__(self):
        return f"Each({self.wanted!r})"


class OneOf:
    def __init__(self, *values):
        self.values = values

    def __eq__(self, got):
        return got in self.values

    def __repr__(self):
        return f"OneOf{self.values!r}"


class Holds:
    """A text holding these words."""
    def __init__(self, text):
        self.text = text

    def __eq__(self, got):
        return isinstance(got, str) and self.text in got

    def __repr__(self):
        return f"Holds({self.text!r})"


def case(name, judge, *args, want, **kwargs):
    """One row: what is asked (a holders function, or relate/kept over a world) and what its answer must hold."""
    return pytest.param(judge, args, kwargs, want, id=name)


CASES = []

# garage-door, recess: base's module and its doors
MODULE = {"id": "module", "noun": "building", "anchor": "ground", "box": [500, 100, 900, 560]}
GARAGE_DOOR = {"id": "garage_door", "noun": "door", "anchor": "on:module", "size": [6.0, 0.5, 8.0],
               "box": [560, 300, 760, 540]}
BASE_ITEMS = [["MODULE 1", 8.0, 1.0, 11.9, 17.2, None, "item"], ["GARAGE DOOR 1", 4.1, 13.9, 4.4, 4.4, None, "item"]]
CASES.append(case("garage-door", relate, plan_of(BASE_ITEMS, {"MODULE 1": ["module"], "GARAGE DOOR 1": ["garage_door"]}),
                  [MODULE, GARAGE_DOOR],
                  want={"row/garage_door/how": "face", "row/garage_door/holder": "MODULE 1",
                        "row/garage_door/face": "S"}))
SIZED_MODULE = {**MODULE, "size": [12.0, 12.0, 12.0]}
ASTRONAUT = {"id": "astronaut", "noun": "astronaut", "anchor": "floor"}
RECESS_ROWS = [SIZED_MODULE, GARAGE_DOOR,
               {"id": "shutter", "noun": "shutter", "anchor": "on:module", "size": [2.0, 0.1, 2.0],
                "box": [800, 400, 880, 540]}, ASTRONAUT]
RECESS_PLAN = plan_of([*BASE_ITEMS, ["SHUTTER 1", 20.0, 5.0, 0.1, 2.0, None, "item"]],
                      {"MODULE 1": ["module"], "GARAGE DOOR 1": ["garage_door"], "SHUTTER 1": ["shutter"]})
CASES.append(case("recess-swing", relate, RECESS_PLAN, RECESS_ROWS, want={
    "row/garage_door/recess/model": "module_1", "row/garage_door/recess/axis": "z",
    "row/garage_door/recess/side": 1.0, "row/garage_door/recess/depth": 6.0 + holders.RECESS_MARGIN,
    "row/garage_door/recess/along": -7.65,
    "row/garage_door/recess/room": round(0.5 + holders.RECESS_MARGIN + holders.RECESS_WALL, 3),
    "row/garage_door/recess/room_side": -1.0, "row/shutter/how": "face", "row/shutter/recess": ABSENT}))
KINDS = holders.row_kinds.table()
SLIDING = {**KINDS, "door": {**KINDS["door"], "motion": {**KINDS["door"]["motion"], "move": "slide"}}}
CASES.append(case("recess-slide", relate, RECESS_PLAN, RECESS_ROWS, kinds=SLIDING, want={
    "row/garage_door/recess/depth": 0.5 + holders.RECESS_MARGIN, "row/garage_door/recess/room": 6.6,
    "row/garage_door/recess/room_side": 1.0}))

# three-doors: three 1.0 m doors on one 1.74 m face item, each its width, recess room and OPENING_ROOM apart
PITCH = 1.0 + round(0.1 + holders.RECESS_MARGIN + holders.RECESS_WALL, 3) + holders.OPENING_ROOM
CASES.append(case(
    "three-doors", relate,
    plan_of([["MODULE 1", 8.0, 1.0, 11.9, 17.2, None, "item"],
             ["RESTAURANT DOOR 1", 9.0, 18.4, 1.74, 0.5, None, "item"]],
            {"MODULE 1": ["module"], "RESTAURANT DOOR 1": ["restaurant_door"]}),
    [SIZED_MODULE, {"id": "restaurant_door", "noun": "door", "anchor": "on:module", "size": [1.0, 0.1, 2.1],
                    "count": 3, "box": [560, 300, 760, 540]}, ASTRONAUT],
    want={("row/restaurant_door/spots", each("0"), steps): Near([PITCH, PITCH]),
          "row/restaurant_door/spots/1/0": Near(9.87),  # about the item's middle
          ("row/restaurant_door/recess/pieces", steps, magnitude): Near([PITCH, PITCH])}))

# on-top: a monitor on its console's top; its placement words; a flat stove on its counter; a stacked blanket
CONSOLE = {"id": "console", "noun": "console", "anchor": "floor", "box": [300, 300, 700, 500]}
MONITOR = {"id": "monitor", "noun": "monitor", "anchor": "on:console", "box": [400, 220, 480, 330]}
CONSOLES = plan_of([["CONSOLE 1", 2.0, 2.0, 3.0, 0.8, "S", "item"], ["CONSOLE 2", 12.0, 2.0, 3.0, 0.8, "S", "item"],
                    ["MONITOR 1", 6.0, 2.0, 0.5, 0.2, None, "item"]],
                   {"CONSOLE 1": ["console"], "CONSOLE 2": ["console"], "MONITOR 1": ["monitor"]})
CASES.append(case("on-top-monitor", relate, CONSOLES, [CONSOLE, MONITOR],
                  want={"row/monitor/how": "top", "row/monitor/holder": "CONSOLE 1"}))
for said, how, under in (("under console", "within", True), ("on shelves", "within", ABSENT),
                          ("console side", "face", ABSENT), ("left side of console", "top", ABSENT)):
    CASES.append(case(f"on-top-said-{said.replace(' ', '-')}", relate, CONSOLES, [CONSOLE, {**MONITOR, "where": said}],
                      want={"row/monitor/how": how, "row/monitor/under": under}))
COUNTER = {"id": "kitchen_counter", "noun": "counter", "anchor": "floor", "size": [3.5, 0.6, 0.9],
           "box": [1692, 603, 1949, 779]}
for name, size, base, how in (("on-top-flat-stove", [0.6, 0.6, 0.05], 0.9, "top"),
                              ("on-top-stove-on-floor", [0.6, 0.6, 0.05], 0.0, "face"),
                              ("on-top-standing-stove", [0.5, 0.1, 0.4], 0.9, "face")):
    stove = {"id": "stove_top", "noun": "stove", "anchor": "on:kitchen_counter", "where": "right wall, on counter",
             "size": size, "box": [1500, 700, 1680, 779]}
    CASES.append(case(name, relate, plan_of(
        [["KITCHEN COUNTER 1", 3.625, 0.775, 0.6, 3.5, "E", "item"], ["STOVE TOP 1", 4.017, 1.544, 0.566, 0.878, "E", "item"]],
        {"KITCHEN COUNTER 1": ["kitchen_counter"], "STOVE TOP 1": ["stove_top"]},
        shapes={"KITCHEN COUNTER 1": {"shape": "rect", "tall": 0.9, "base": 0.0},
                "STOVE TOP 1": {"shape": "rect", "tall": 0.05, "base": base}}), [COUNTER, stove], picture=[3000, 1200],
        want={"row/stove_top/how": how, "row/stove_top/holder": "KITCHEN COUNTER 1"}))
BED = {"id": "bed", "noun": "bed", "anchor": "floor", "size": [2.0, 1.0, 0.5]}
BLANKET = {"id": "blanket", "noun": "blanket", "anchor": "on:bed", "where": "on bed, right", "size": [0.8, 0.6, 0.2]}
for name, first, how in (("on-top-stacked-blanket", [2.536, 1.203], "top"),
                         ("on-top-blanket-beside-the-stack", [1.0, 1.1], "face")):
    CASES.append(case(name, relate, plan_of(
        [["BED 1", 0.994, 1.084, 1.912, 0.956, "E", "item"], ["BLANKET 1", *first, 0.478, 0.717, "W", "item"],
         ["BLANKET 2", 2.247, 1.753, 0.8, 0.6, None, "item"]],
        {"BED 1": ["bed"], "BLANKET 1": ["blanket"], "BLANKET 2": ["blanket"]},
        shapes={"BED 1": {"shape": "rect", "tall": 0.5, "base": 0.0}, "BLANKET 1": {"shape": "rect", "tall": 0.2, "base": 0.5},
                "BLANKET 2": {"shape": "rect", "tall": 0.2, "base": 0.7}}), [BED, BLANKET],
        want={"item/BLANKET 2/how": how, "item/BLANKET 2/holder": "BED 1"}))

# too-tall: fittings on runs, valves by standing pipes, a spacesuit too tall for its locker's top
PIPE_RUN = {"size": [0.4, 32.0, 0.4]}
for name, thing, holder, wanted in (
        ("too-tall-valve-on-its-pipe-run", {"size": [0.6, 0.2, 0.6]}, PIPE_RUN, True),
        ("too-tall-valve-no-taller-than-its-pipe", {"size": [0.6, 0.2, 0.3]}, PIPE_RUN, False),
        ("too-tall-clothes-on-a-drying-rack", {"size": [0.5, 0.1, 0.8]}, {"size": [1.5, 0.5, 0.1]}, False),
        ("too-tall-sitter-on-its-seat", {"size": [0.6, 0.4, 1.8]}, {"size": [0.4, 0.4, 0.5]}, False),
        ("too-tall-sizeless-on-a-run", {}, PIPE_RUN, False)):
    CASES.append(case(name, holders.on_run, thing, holder, want={(): wanted}))
RUNS = {"PIPE 1": ["PIPE 1", 0.0, 0.0, 32.0, 0.4, "S", "item"], "VALVE 1": ["VALVE 1", 1.0, 0.0, 0.6, 0.2, "S", "item"]}
LARGE_PIPES = {"id": "large_pipes", "noun": "pipe", "anchor": "wall", **PIPE_RUN}
for name, size, how, rests in (("too-tall-valve-attached-on-its-run", [0.6, 0.2, 0.6], "top", "attached"),
                               ("too-tall-valve-within-its-run", [0.6, 0.2, 0.3], "within", ABSENT)):
    CASES.append(case(name, holders.held, RUNS["VALVE 1"],
                      {"id": "pipe_valves", "noun": "valve", "anchor": "on:large_pipes", "size": size},
                      LARGE_PIPES, ["PIPE 1"], RUNS, 0.0, want={"how": how, "holder": "PIPE 1", "rests": rests}))
WALLED = plan_of([], {}, walls=[{"from": [0.0, 0.0], "to": [20.0, 0.0], "thick": 0.2},
                                {"from": [0.0, 0.0], "to": [0.0, 12.0], "thick": 0.2}])
CASES.append(case("too-tall-off-the-north-wall", holders.side_off_wall, ["PIPE 9", 5.0, 0.2, 0.2, 0.2, None, "item"],
                  WALLED, want={(): "S"}))
CASES.append(case("too-tall-off-the-west-wall", holders.side_off_wall, ["PIPE 9", 0.2, 6.0, 0.2, 0.2, None, "item"],
                  WALLED, want={(): "E"}))
STANDING = {"id": "pipe", "noun": "pipe", "anchor": "wall", "size": [0.1, 0.1, 2.5]}
CASES.append(case("too-tall-valve-off-the-wall", holders.held, RUNS["VALVE 1"],
                  {"id": "valve", "noun": "valve", "anchor": "on:pipe", "size": [0.2, 0.1, 0.2]}, STANDING, ["PIPE 1"],
                  RUNS, 0.0, off_wall="S", want={"how": "face", "face": "S"}))
for name, size, holder, how in (
        ("too-tall-valve-beside-a-standing-pipe", [0.2, 0.1, 0.2], STANDING, "face"),
        ("too-tall-valve-no-wider-than-its-pipe", [0.08, 0.08, 0.2], STANDING, "within"),
        ("too-tall-valve-in-a-lying-run", [0.6, 0.2, 0.3], {**STANDING, "size": [0.4, 32.0, 0.4]}, "within"),
        ("too-tall-valve-on-a-stub", [0.2, 0.1, 0.2], {**STANDING, "size": [0.1, 0.1, 0.15]}, "within")):
    CASES.append(case(name, holders.held, RUNS["VALVE 1"],
                      {"id": "valve", "noun": "valve", "anchor": "on:pipe", "size": size}, holder, ["PIPE 1"], RUNS,
                      0.0, want={"how": how, "holder": "PIPE 1"}))
LOCKER_ROWS = [{"id": "locker", "noun": "locker", "anchor": "floor", "size": [0.8, 0.6, 2.0], "box": [681, 565, 813, 1062]},
               {"id": "suit", "noun": "spacesuit", "anchor": "on:locker", "size": [0.6, 0.4, 1.8],
                "box": [687, 565, 812, 789]}]
LOCKER_ITEMS = [["LOCKER 1", 2.0, 2.0, 0.8, 0.6, "S", "item"], ["SUIT 1", 2.1, 2.1, 0.6, 0.4, "S", "item"]]
LOCKER_TIED = {"LOCKER 1": ["locker"], "SUIT 1": ["suit"]}
LOW_WALLS = [{"from": [0.0, 0.0], "to": [20.0, 0.0], "thick": 0.2, "tall": 2.5}]
CASES.append(case("too-tall-suit-under-a-low-ceiling", relate, plan_of(LOCKER_ITEMS, LOCKER_TIED, walls=LOW_WALLS),
                  LOCKER_ROWS, picture=[3000, 1200], want={"row/suit/how": "within", "row/suit/holder": "LOCKER 1"}))
CASES.append(case("too-tall-suit-under-a-dome", relate, plan_of(
    LOCKER_ITEMS, LOCKER_TIED, walls=LOW_WALLS, roofs=[{"kind": "dome", "eave": 2.5, "top": 4.2}]), LOCKER_ROWS,
    picture=[3000, 1200], want={"row/suit/how": "top"}))

# hangs: within a holder, which things hang
HANG_PLAN = plan_of([], {}, shapes={
    "LOCKER 1": {"base": 0.0, "tall": 2.0}, "SUIT 1": {"base": 0.1, "tall": 1.8}, "RACK 1": {"base": 0.1, "tall": 2.2},
    "TRAY 1": {"base": 1.0, "tall": 0.1}, "NOTE 1": {"base": 1.5, "tall": 0.001}, "FRAME 1": {"base": 0.0, "tall": 2.5},
    "CHASSIS 1": {"base": 0.2, "tall": 1.3}, "DESK 1": {"base": 0.0, "tall": 0.8},
    "KEYBOARD 1": {"base": 0.8, "tall": 0.05}})
for thing, holder, wanted in (("SUIT 1", "LOCKER 1", True), ("TRAY 1", "RACK 1", False), ("NOTE 1", "LOCKER 1", False),
                              ("CHASSIS 1", "FRAME 1", False), ("KEYBOARD 1", "DESK 1", False)):
    CASES.append(case(f"hangs-{thing.split()[0].lower()}", holders.hangs, [thing], [holder], HANG_PLAN,
                      want={(): wanted}))

# other-holder: a spot in another locker like its anchor's
CASES.append(case(
    "other-holder", relate,
    plan_of([["LOCKER LEFT 1", 2.0, 2.0, 0.8, 0.6, "S", "item"], ["LOCKER RIGHT 1", 10.0, 2.0, 0.8, 0.6, "S", "item"],
             ["SUIT 1", 2.1, 2.1, 0.6, 0.4, "S", "item"], ["SUIT 2", 10.1, 2.1, 0.6, 0.4, "S", "item"],
             ["SUIT 3", 6.0, 6.0, 0.6, 0.4, "S", "item"]],
            {"LOCKER LEFT 1": ["locker_left"], "LOCKER RIGHT 1": ["locker_right"], "SUIT 1": ["suit"],
             "SUIT 2": ["suit"], "SUIT 3": ["suit"]}),
    [{"id": "locker_left", "noun": "locker", "anchor": "floor", "size": [0.8, 0.6, 2.0]},
     {"id": "locker_right", "noun": "locker", "anchor": "floor", "size": [0.8, 0.6, 2.0]},
     {"id": "suit", "noun": "spacesuit", "anchor": "on:locker_left", "size": [0.6, 0.4, 1.8]}],
    want={"item/SUIT 1/how": "within", "item/SUIT 1/holder": "LOCKER LEFT 1", "item/SUIT 2/how": "within",
          "item/SUIT 2/holder": "LOCKER RIGHT 1", "item/SUIT 3/holder": "LOCKER LEFT 1"}))

# nearest-console: monitors the concept shows on two consoles
CASES.append(case(
    "nearest-console", relate,
    plan_of([["MAIN CONTROL BANK 1", 1.0, 1.0, 3.0, 0.8, "S", "item"],
             ["CONTROL CONSOLE RIGHT 1", 14.0, 1.0, 3.0, 0.8, "S", "item"], ["CHAIR 1", 15.0, 2.5, 0.6, 0.6, None, "item"],
             ["MONITOR SCREEN 1", 2.0, 1.2, 0.5, 0.1, None, "item"], ["MONITOR SCREEN 2", 15.0, 1.2, 0.5, 0.1, None, "item"],
             ["MONITOR SCREEN 3", 15.2, 2.6, 0.5, 0.1, None, "item"]],
            {"MAIN CONTROL BANK 1": ["main_control_bank"], "CONTROL CONSOLE RIGHT 1": ["control_console_right"],
             "CHAIR 1": ["chair"], "MONITOR SCREEN 1": ["monitor_screen"], "MONITOR SCREEN 2": ["monitor_screen"],
             "MONITOR SCREEN 3": ["monitor_screen"]}),
    [{"id": "main_control_bank", "noun": "control bank", "anchor": "floor", "box": [100, 200, 400, 500]},
     {"id": "control_console_right", "noun": "console", "anchor": "floor", "box": [600, 300, 900, 500]},
     {"id": "chair", "noun": "chair", "anchor": "floor", "box": [650, 380, 700, 470]},
     {"id": "monitor_screen", "noun": "monitor", "anchor": "on:main_control_bank",
      "boxes": [[150, 150, 200, 260], [660, 300, 700, 400], [800, 240, 850, 340]]}],
    want={("item", among("MONITOR SCREEN 1", "MONITOR SCREEN 2", "MONITOR SCREEN 3"), each("holder")): [
        "MAIN CONTROL BANK 1", "CONTROL CONSOLE RIGHT 1", "CONTROL CONSOLE RIGHT 1"]}))

# cut-opening, window-opening, own-openings, built-widths: doors and windows in openings
NORTH_EAST = [{"from": [0.0, 0.0], "to": [20.0, 0.0], "thick": 0.2}, {"from": [20.0, 0.0], "to": [20.0, 12.0], "thick": 0.2}]
DOOR_OPENING = {"kind": "door", "at": [5.0, 0.0], "wide": 1.4, "sill": 0.0, "head": 2.2}
CASES.append(case(
    "cut-opening", relate,
    plan_of([[plan_checks.WALLS_ITEM, 0.0, 0.0, 20.0, 12.0, None, "item"]], {plan_checks.WALLS_ITEM: ["door", "back_door"]},
            walls=NORTH_EAST, openings=[DOOR_OPENING]),
    [{"id": "door", "noun": "door", "anchor": "wall", "size": [1.2, 0.1, 2.1]},
     {"id": "back_door", "noun": "door", "anchor": "wall", "size": [1.0, 0.1, 2.1]}],
    want={"row/door/how": "in", "row/door/opening/at": [5.0, 0.0], "row/back_door/how": "in",
          "row/back_door/opening": {"at": [10.0, 0.0], "wide": 1.0, "sill": 0.0, "head": 2.1, "cut": True}}))
CASES.append(case(
    "window-opening", relate,
    plan_of([["DOME WINDOW 1", 19.6, 0.0, 0.2, 0.1, None, "item"], ["DOME DOOR 1", 4.5, 0.0, 1.0, 0.2, None, "item"]],
            {"DOME WINDOW 1": ["dome_window"], "DOME DOOR 1": ["dome_door"]}, walls=NORTH_EAST, openings=[DOOR_OPENING]),
    [{"id": "dome_window", "noun": "window", "anchor": "wall", "size": [0.5, 0.1, 0.5]},
     {"id": "dome_door", "noun": "door", "anchor": "wall", "size": [1.0, 0.1, 2.0]}],
    want={"row/dome_window/opening": {"at": [19.35, 0.0], "wide": 0.5, "sill": 0.9, "head": 1.4, "cut": True},
          "row/dome_door/opening/at": [5.0, 0.0], "row/dome_door/opening/cut": ABSENT}))
CASES.append(case(
    "own-openings", relate,
    plan_of([["REAR DOOR 1", 8.0, 0.2, 2.0, 0.4, None, "item"]], {"REAR DOOR 1": ["rear_door"]},
            walls=[{"from": [0.0, 0.0], "to": [20.0, 0.0], "thick": 0.2}]),
    [{"id": "rear_door", "noun": "door", "anchor": "wall", "size": [1.2, 0.2, 2.1], "count": 4}],
    want={("row/rear_door/pieces", each("opening/at")): [[8.25, 0.0], [9.65, 0.0], [11.05, 0.0], [12.45, 0.0]],
          ("row/rear_door/pieces", each("opening/wide")): [1.2] * 4,
          ("row/rear_door/pieces", each("opening/cut")): [True] * 4}))
CASES.append(case(
    "built-widths-spread", relate,
    plan_of([[plan_checks.WALLS_ITEM, 0.0, 0.0, 20.0, 12.0, None, "item"]], {plan_checks.WALLS_ITEM: ["door", "window"]},
            walls=[{"from": [0.0, 0.0], "to": [20.0, 0.0], "thick": 0.2}],
            openings=[{"kind": "door", "at": [19.8, 0.0], "wide": 0.39, "sill": 0.0, "head": 2.2},
                      {"kind": "window", "at": [18.7, 0.0], "wide": 0.2, "sill": 1.0, "head": 2.0}]),
    [{"id": "door", "noun": "door", "anchor": "wall", "size": [1.0, 0.1, 2.1]},
     {"id": "window", "noun": "window", "anchor": "wall", "size": [2.0, 0.1, 1.0]}],
    want={"row/door/opening": {"at": [19.1, 0.0], "wide": 1.0, "sill": 0.0, "head": 2.2, "cut": True},
          "row/window/opening": {"at": [17.4, 0.0], "wide": 2.0, "sill": 1.0, "head": 2.0, "cut": True},
          "crowded": ABSENT}))
CASES.append(case(
    "built-widths-crowded", relate,
    plan_of([[plan_checks.WALLS_ITEM, 0.0, 0.0, 4.0, 12.0, None, "item"]], {plan_checks.WALLS_ITEM: ["door", "back_door"]},
            walls=[{"from": [0.0, 0.0], "to": [4.0, 0.0], "thick": 0.2}],
            openings=[{"kind": "door", "at": [1.5, 0.0], "wide": 0.3, "sill": 0.0, "head": 2.2},
                      {"kind": "door", "at": [2.5, 0.0], "wide": 0.3, "sill": 0.0, "head": 2.2}]),
    [{"id": "door", "noun": "door", "anchor": "wall", "size": [2.0, 0.1, 2.1]},
     {"id": "back_door", "noun": "door", "anchor": "wall", "size": [2.0, 0.1, 2.1]}],
    want={("relations", each("opening/wide"), ordered): [0.3, 0.3],
          ("crowded", each("rows", ordered)): [["back_door", "door"]]}))
SMALL_ROOM = [{"from": [0.0, 0.0], "to": [4.6, 0.0], "thick": 0.1}, {"from": [4.6, 0.0], "to": [4.6, 6.0], "thick": 0.1},
              {"from": [4.6, 6.0], "to": [0.0, 6.0], "thick": 0.1}, {"from": [0.0, 6.0], "to": [0.0, 0.0], "thick": 0.1}]
CASES.append(case(
    "built-widths-wall-with-room", relate,
    plan_of([["DOOR 1", 1.8, 0.0, 1.0, 0.1, None, "item"], ["SHUTTER 1", 2.5, 0.3, 3.0, 0.1, None, "item"]],
            {"DOOR 1": ["door"], "SHUTTER 1": ["shutter"]}, walls=SMALL_ROOM,
            openings=[{"kind": "door", "at": [2.3, 0.0], "wide": 1.5, "sill": 0.0, "head": 2.2}]),
    [{"id": "door", "noun": "door", "anchor": "wall", "size": [1.0, 0.1, 2.1]},
     {"id": "shutter", "noun": "shutter", "anchor": "wall", "size": [3.0, 0.1, 3.0]}],
    want={"row/door/opening/at": [2.3, 0.0], "row/shutter/wall/from": [4.6, 0.0], "row/shutter/wall/to": [4.6, 6.0],
          "crowded": ABSENT}))
CASES.append(case(
    "built-widths-stub", relate,
    plan_of([["WINDOW 1", 5.0, 0.3, 0.5, 0.1, None, "item"]], {"WINDOW 1": ["window"]},
            walls=[{"from": [5.0, 0.0], "to": [5.6, 0.0], "thick": 0.1}, {"from": [0.0, 3.0], "to": [12.0, 3.0], "thick": 0.1}]),
    [{"id": "window", "noun": "window", "anchor": "wall", "size": [0.5, 0.1, 0.5]}],
    want={"row/window/wall/from": [5.0, 0.0], "row/window/opening/at": [5.3, 0.0]}))

# facade, face-spread: a street facade past the plan's edge and the things on its face
FACADE = {"id": "left_building_facade", "noun": "building facade", "part": "wall", "anchor": "ground",
          "box": [0, 0, 300, 600]}
CASES.append(case(
    "facade", relate,
    plan_of([[plan_checks.WALLS_ITEM, 0.0, 0.0, 6.0, 30.0, None, "item"], ["AIR CONDITIONER UNIT 1", 0.5, 10.0, 0.8, 0.4, None, "item"]],
            {plan_checks.WALLS_ITEM: ["left_building_facade"], "AIR CONDITIONER UNIT 1": ["air_conditioner_unit"]},
            structure=["left_building_facade"], w=6.0, d=30.0),
    [FACADE, {"id": "air_conditioner_unit", "noun": "air conditioner", "anchor": "on:left_building_facade",
              "box": [100, 200, 160, 240]}],
    want={"row/left_building_facade/how": "edge", "row/left_building_facade/edge": "W",
          "row/left_building_facade/spot": [0.0, 15.0], "row/air_conditioner_unit/how": "face",
          "row/air_conditioner_unit/holder row": "left_building_facade", "row/air_conditioner_unit/face": "E"}))


def facade_plan(long):
    """A facade `long` m along with a 3 m window, a 3 m shutter 1.74 m after it and an air conditioner 3 m up."""
    return plan_of([[plan_checks.WALLS_ITEM, 0.0, 0.0, 6.0, long, None, "item"],
                    ["WINDOW 1", 0.5, long / 2 - 5.87, 0.5, 1.74, "E", "item"],
                    ["SHUTTER 1", 0.5, long / 2 - 4.13, 0.5, 1.74, "E", "item"],
                    ["AIR CONDITIONER UNIT 1", 0.5, long / 2 - 5.3, 0.4, 0.6, "E", "item"]],
                   {plan_checks.WALLS_ITEM: ["left_building_facade"], "WINDOW 1": ["window"], "SHUTTER 1": ["shutter"],
                    "AIR CONDITIONER UNIT 1": ["air_conditioner_unit"]},
                   structure=["left_building_facade"], w=6.0, d=long, shapes={"AIR CONDITIONER UNIT 1": {"base": 3.0}})


def facade_rows(long):
    return [{**FACADE, "size": [3.0, long, 20.0]},
            {"id": "window", "noun": "window", "anchor": "on:left_building_facade", "size": [3.0, 0.1, 2.5]},
            {"id": "shutter", "noun": "shutter", "anchor": "on:left_building_facade", "size": [3.0, 0.1, 3.0]},
            {"id": "air_conditioner_unit", "noun": "air conditioner", "anchor": "on:left_building_facade",
             "size": [0.8, 0.4, 0.6]}]


CASES.append(case("face-spread", relate, facade_plan(30.0), facade_rows(30.0), want={
    "row/window/spots": ABSENT, "row/air_conditioner_unit/spots": ABSENT, "row/shutter/spots": [[0.75, 13.2]],
    "crowded": ABSENT, ("relations", each("_holder")): Each(ABSENT)}))
CASES.append(case("face-spread-crowded", relate, facade_plan(6.0), facade_rows(6.0), want={
    ("relations", each("spots")): Each(ABSENT), ("crowded", each("face")): ["E"],
    ("crowded", each("rows")): [["air_conditioner_unit", "shutter", "window"]]}))
CASES.append(case(
    "face-spread-pillar", relate,
    plan_of([["PILLAR 1", 8.0, 5.0, 0.3, 0.3, None, "item"], ["PILLAR PIPE 1", 8.1, 4.9, 0.1, 0.1, None, "item"],
             ["PILLAR PIPE 2", 8.1, 5.3, 0.1, 0.1, None, "item"], ["PILLAR PIPE 3", 8.3, 5.1, 0.1, 0.1, None, "item"]],
            {"PILLAR 1": ["pillar"], **{f"PILLAR PIPE {number}": ["pillar_pipe"] for number in (1, 2, 3)}}),
    [{"id": "pillar", "noun": "pillar", "anchor": "floor", "size": [0.3, 0.3, 3.0], "box": [500, 100, 600, 560]},
     {"id": "pillar_pipe", "noun": "pipe", "anchor": "on:pillar", "size": [0.13, 0.1, 3.0], "box": [530, 100, 570, 560]}],
    want={("item", among("PILLAR PIPE 1", "PILLAR PIPE 2", "PILLAR PIPE 3"), each("face")): ["N", "S", "E"],
          "crowded": ABSENT}))

# built-end: three monitors drawn past their console's built end
END_ITEMS = [["CONSOLE 1", 0.0, 4.0, 9.0, 1.0, "N", "item"],
             *[[f"MONITOR {number}", along, 5.0, 0.5, 0.1, None, "item"] for number, along in ((1, 6.5), (2, 7.5), (3, 8.4))]]
CASES.append(case(
    "built-end", relate,
    plan_of(END_ITEMS, {"CONSOLE 1": ["console"], **{item[0]: ["monitor"] for item in END_ITEMS[1:]}},
            shapes={item[0]: {"base": 1.0} for item in END_ITEMS[1:]}),
    [{"id": "console", "noun": "console", "anchor": "floor", "size": [4.5, 0.8, 1.0]},
     {"id": "monitor", "noun": "monitor", "anchor": "on:console", "size": [0.5, 0.1, 0.4]}],
    want={("item", among("MONITOR 1", "MONITOR 2", "MONITOR 3"), each("how")): ["face"] * 3,
          ("item", among("MONITOR 1", "MONITOR 2", "MONITOR 3"), each("face")): ["S"] * 3,
          ("item", among("MONITOR 1", "MONITOR 2", "MONITOR 3"), each("spots")): [[[4.9, 5.05]], [[5.6, 5.05]], [[6.3, 5.05]]],
          "crowded": ABSENT}))

# stair, ramp
CASES.append(case(
    "stair", relate,
    plan_of([[plan_checks.WALLS_ITEM, 0.0, 0.0, 20.0, 12.0, None, "item"]], {plan_checks.WALLS_ITEM: ["lower_floor", "stairs"]},
            structure=["lower_floor"],
            stairs=[{"kind": "stair", "points": [[2.0, 2.0], [6.0, 2.0], [6.0, 3.0], [2.0, 3.0]], "angle": 90}]),
    [{"id": "lower_floor", "noun": "floor", "part": "floor", "anchor": "ground"},
     {"id": "stairs", "noun": "stairs", "anchor": "on:lower_floor", "count": 1}],
    want={"row/stairs/how": "floor", "row/stairs/spot": [4.0, 2.5], "row/stairs/way": [0.0, 1.0]}))
RAMP_ROWS = [{"id": "ramp", "noun": "ramp", "anchor": "ground", "size": [1.2, 2.0, 0.2]},
             {"id": "bench", "noun": "bench", "anchor": "ground", "size": [1.2, 0.4, 0.4]}]
RAMP_ITEMS = [["RAMP 1", 8.267, 10.904, 1.2, 2.0, None, "item"], ["BENCH 1", 8.0, 9.0, 1.2, 0.4, None, "item"]]
LEVELS = [{"name": "the floor", "height": 0.0, "points": [[0.0, 0.0], [12.0, 0.0], [12.0, 12.0], [0.0, 12.0]]},
          {"name": "the porch deck", "height": 0.2,
           "points": [[9.889, 8.625], [15.298, 8.625], [15.298, 14.74], [9.889, 14.74]]}]
CASES.append(case("ramp", relate, plan_of(RAMP_ITEMS, {"RAMP 1": ["ramp"], "BENCH 1": ["bench"]}, levels=LEVELS),
                  RAMP_ROWS, want={("row", keys): ["ramp"], "row/ramp/how": "ramp", "row/ramp/way": [1.0, 0.0],
                                   "row/ramp/height": 0.2, "row/ramp/spot": [8.889, 11.904],
                                   "row/ramp/edge": [[9.889, 14.74], [9.889, 8.625]]}))
CASES.append(case("ramp-no-raised-level", relate,
                  plan_of(RAMP_ITEMS, {"RAMP 1": ["ramp"], "BENCH 1": ["bench"]}, levels=LEVELS[:1]), RAMP_ROWS,
                  want={"relations": []}))

# wall-side: a panel by a round wall, a wall lamp on its wall's room side, things leaning and attached
PANEL_MIDDLE = [10.0 + 4.6 * numpy.cos(numpy.radians(7.5)), 6.0 + 4.6 * numpy.sin(numpy.radians(7.5))]
CASES.append(case(
    "wall-side-round-wall", relate,
    plan_of([["PANEL 1", PANEL_MIDDLE[0] - 0.1, PANEL_MIDDLE[1] - 0.1, 0.2, 0.2, None, "item"]], {"PANEL 1": ["panel"]},
            walls=[{"arc": {"centre": [10.0, 6.0], "radius": 5.0, "start": 315.0, "end": 45.0}, "thick": 0.2}]),
    [{"id": "panel", "noun": "panel", "anchor": "wall", "size": [1.0, 0.1, 1.0]}],
    want={"row/panel/how": "wall", "row/panel/wall/from": Near([15.0, 6.0]),
          "row/panel/wall/to": Near([10.0 + 5 * numpy.cos(numpy.radians(15)), 6.0 + 5 * numpy.sin(numpy.radians(15))])}))
LEFT_WALL = {"id": "left_wall", "noun": "wall", "part": "wall", "anchor": "floor"}
WALL_LAMP = {"id": "wall_lamp", "noun": "lamp", "anchor": "on:left_wall", "size": [0.3, 0.2, 0.3]}
LEFT_WALLS = [{"from": [0.0, 0.0], "to": [0.0, 12.0], "thick": 0.2}, {"from": [0.0, 0.0], "to": [4.0, 0.0], "thick": 0.2}]
CASES.append(case(
    "wall-side-lamp", relate,
    plan_of([[plan_checks.WALLS_ITEM, 0.0, 0.0, 20.0, 12.0, None, "item"]], {plan_checks.WALLS_ITEM: ["left_wall", "wall_lamp"]},
            structure=["left_wall"], walls=LEFT_WALLS), [LEFT_WALL, WALL_LAMP],
    want={"row/wall_lamp/how": "wall", "row/wall_lamp/wall/to": [0.0, 12.0], "row/wall_lamp/side": -1,
          "row/wall_lamp/spot": [0.0, 6.0]}))
CASES.append(case(
    "wall-side-leaning", relate,
    plan_of([[plan_checks.WALLS_ITEM, 0.0, 0.0, 20.0, 12.0, None, "item"], ["BOARD 1", 1.0, 5.0, 0.4, 0.1, None, "item"],
             ["CRATE 1", 9.5, 5.5, 1.0, 1.0, None, "item"], ["PLANK 1", 9.8, 5.7, 0.3, 0.1, None, "item"]],
            {plan_checks.WALLS_ITEM: ["left_wall", "wall_lamp", "sign"], "BOARD 1": ["board"], "CRATE 1": ["crate"],
             "PLANK 1": ["plank"]}, structure=["left_wall"], walls=LEFT_WALLS),
    [LEFT_WALL, WALL_LAMP,
     {"id": "board", "noun": "board", "anchor": "floor", "where": "left, leaning against the left wall",
      "size": [0.4, 0.05, 0.6]},
     {"id": "sign", "noun": "sign", "anchor": "on:left_wall", "where": "left wall, attached to the left wall",
      "size": [0.4, 0.05, 0.3]},
     {"id": "crate", "noun": "crate", "anchor": "floor", "size": [1.0, 1.0, 1.0], "box": [400, 300, 600, 500]},
     {"id": "plank", "noun": "plank", "anchor": "on:crate", "where": "centre, leaning against the crate",
      "size": [0.3, 0.05, 0.8], "box": [450, 200, 550, 300]}],
    want={"row/board/how": "wall", "row/board/rests": "leaning", "row/board/wall/to": [0.0, 12.0],
          "row/board/height": ABSENT, "row/sign/how": "wall", "row/sign/rests": "attached", "row/sign/height": 1.35,
          "row/plank/how": "face", "row/plank/holder": "CRATE 1", "row/plank/rests": "leaning",
          "row/wall_lamp/rests": ABSENT}))

# past-wall: things drawn past their wall stand in the room, a tunnel outside
CASES.append(case(
    "past-wall", relate,
    plan_of([["LARGE PIPES 1", 10.0, 12.0, 1.0, 3.1, None, "item"], ["GLASS TUNNEL 1", 3.0, 12.3, 1.7, 4.2, "S", "item"]],
            {"LARGE PIPES 1": ["large_pipes"], "GLASS TUNNEL 1": ["glass_tunnel"]},
            outline=[[0.0, 0.0], [20.0, 0.0], [20.0, 12.0], [0.0, 12.0]],
            walls=[{"from": [20.0, 12.0], "to": [0.0, 12.0], "thick": 0.6}]),
    [{"id": "large_pipes", "noun": "pipes", "anchor": "wall", "size": [0.4, 8.0, 0.4]},
     {"id": "glass_tunnel", "noun": "tunnel", "anchor": "wall", "size": [2.5, 4.0, 2.5]}],
    want={"row/large_pipes/how": "wall", "row/large_pipes/side": 1, "row/glass_tunnel/how": "wall",
          "row/glass_tunnel/side": -1}))

ROOM_WALLS = [{"from": [0.0, 0.0], "to": [20.0, 0.0], "thick": 0.2},
              {"from": [0.0, 12.0], "to": [20.0, 12.0], "thick": 0.2},
              {"from": [0.0, 0.0], "to": [0.0, 12.0], "thick": 0.2},
              {"from": [20.0, 0.0], "to": [20.0, 12.0], "thick": 0.2}]

# two-panels: two wall panels each drawn as the whole room
CASES.append(case(
    "two-panels", relate,
    plan_of([["PANEL 1", 0.5, 0.5, 19.0, 11.0, None, "item"], ["PANEL 2", 0.5, 0.5, 19.0, 11.0, None, "item"]],
            {"PANEL 1": ["wall_panel"], "PANEL 2": ["wall_panel"]}, walls=ROOM_WALLS),
    [{"id": "hull", "noun": "hull", "part": "wall", "anchor": "floor"},
     {"id": "wall_panel", "noun": "panel", "anchor": "on:hull", "size": [20.0, 12.0, 3.5]}],
    want={"item/PANEL 1/wall/to": [20.0, 0.0], "item/PANEL 1/spot": [10.0, 0.0], "item/PANEL 1/side": 1,
          "item/PANEL 2/wall/to": [20.0, 12.0], "item/PANEL 2/spot": [10.0, 12.0], "item/PANEL 2/side": -1}))

# wall-spread: things on walls, roofs, seats, stairs and floors spread apart
CASES.append(case(
    "wall-spread-lights", relate,
    plan_of([[plan_checks.WALLS_ITEM, 0.0, 0.0, 20.0, 12.0, None, "item"]],
            {plan_checks.WALLS_ITEM: ["left_wall", "string_lights", "wall_light"]}, structure=["left_wall"],
            walls=ROOM_WALLS),
    [LEFT_WALL, {"id": "string_lights", "noun": "lights", "anchor": "on:left_wall", "size": [3.0, 0.05, 0.05]},
     {"id": "wall_light", "noun": "light", "anchor": "on:left_wall", "size": [1.0, 0.1, 0.1]}],
    want={("row", among("string_lights", "wall_light"), each("wall/to")): [[0.0, 12.0], [0.0, 12.0]],
          ("row", among("string_lights", "wall_light"), each("spot"), ordered): [[0.0, 4.0], [0.0, 8.0]]}))
HALL_ROWS = [{"id": "tools", "noun": "tool", "anchor": "wall", "where": "left wall", "size": [0.5, 0.05, 0.3], "count": 6},
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
HALL_ITEMS = [["TOOLS 1", 0.2, 5.0, 0.5, 2.0, None, "item"], ["PIPE 1", 10.3, 0.5, 0.5, 1.0, None, "item"],
              ["CRANE 1", 1.0, 1.0, 18.0, 2.0, None, "item"], ["LAMP 1", 19.5, 6.0, 0.5, 0.5, None, "item"],
              ["DESK 1", 8.0, 5.0, 6.0, 3.0, "S", "item"], ["CHAIR 1", 10.5, 9.0, 1.0, 1.0, None, "item"],
              *[[f"RAIL {number}", 2.0, 8.0, 1.0, 3.0, None, "item"] for number in (1, 2, 3)],
              *[[f"DUCT {number}", 6.0, 0.3, 8.0, 0.2, None, "item"] for number in (1, 2, 3)],
              *[[f"CLOCK {number}", 14.5, 11.5, 1.0, 0.2, None, "item"] for number in (1, 2)]]
HALL_TIED = {item[0]: [item[0].split()[0].lower().replace("rail", "railing")] for item in HALL_ITEMS}
HALL_WALLS = [*ROOM_WALLS, {"from": [10.0, 0.0], "to": [10.0, 2.0], "thick": 0.2}]
FLIGHT = {"points": [[2.0, 8.0], [3.0, 8.0], [3.0, 11.0], [2.0, 11.0]], "angle": 90.0}
RAILS = among("RAIL 1", "RAIL 2", "RAIL 3")
DUCTS = among("DUCT 1", "DUCT 2", "DUCT 3")
CLOCKS = among("CLOCK 1", "CLOCK 2")
CASES.append(case(
    "wall-spread-hall", relate,
    plan_of(HALL_ITEMS, HALL_TIED, walls=HALL_WALLS, stairs=[FLIGHT], shapes={"TOOLS 1": {"count": 6}}), HALL_ROWS,
    want={("item/TOOLS 1/pieces", count): 6, ("item/TOOLS 1/pieces", each("wall/from/0")): Each(0.0),
          ("item/TOOLS 1/pieces", each("wall/to/0")): Each(0.0),
          ("item/TOOLS 1/pieces", each("spot/1"), ordered, steps): AtLeast(0.5 + holders.PIECE_GAP - 1e-3),
          ("item/TOOLS 1/pieces", each("height"), unique): [1.35],
          "item/PIPE 1/wall/from": [0.0, 0.0], "item/PIPE 1/wall/to": [20.0, 0.0],
          "item/CRANE 1/how": "ceiling", "item/CRANE 1/to roof": True, "item/LAMP 1/height": 2.25,
          "item/CHAIR 1/beside": "DESK 1", ("item/CHAIR 1/pieces", count): 1,
          "item/CHAIR 1/pieces/0/spot": [11.0, 7.3], "item/CHAIR 1/pieces/0/way": [1.0, 0.0],
          ("item", RAILS, each("pieces/0/spot"), distinct): 3,
          ("item", DUCTS, each("height"), ordered): [1.15, 1.65, 1.9],  # 1.4 m is the 6 m pipe's there
          ("item", DUCTS, each("spot"), unique): [[10.0, 0.4]], ("item", DUCTS, each("wall/to"), unique): [[20.0, 0.0]],
          ("item", CLOCKS, each("spot"), ordered): [[14.475, 12.0], [15.525, 12.0]],
          ("item", CLOCKS, each("height"), unique): [1.35]}))
CASES.append(case(
    "wall-spread-flight-railings", relate,
    plan_of(HALL_ITEMS, HALL_TIED, walls=HALL_WALLS, stairs=[{**FLIGHT, "from": 1.5, "to": 3.0}]), HALL_ROWS,
    want={("item", RAILS, each("rests")): Each(holders.ATTACHED), ("item", RAILS, each("pieces/0/height")): Each(1.5)}))
LIT_ITEMS = [["DESK 1", 2.0, 2.0, 1.0, 0.6, None, "item"], ["SHELF 1", 8.0, 2.0, 1.0, 0.4, None, "item"],
             ["RUG 1", 14.0, 8.0, 2.0, 2.0, None, "item"], ["TV STAND 1", 2.0, 9.0, 1.2, 0.4, None, "item"],
             ["TV STAND 2", 17.0, 1.0, 1.2, 0.4, None, "item"], ["TV 1", 4.0, 9.0, 1.0, 0.1, None, "item"],
             ["LAMP 1", 2.3, 2.1, 0.3, 0.3, None, "item"], ["LAMP 2", 5.0, 5.0, 0.3, 0.3, None, "item"],
             ["LAMP 3", 8.3, 2.05, 0.3, 0.3, None, "item"], ["LAMP 4", 12.0, 5.0, 0.3, 0.3, None, "item"],
             ["LAMP 5", 14.5, 8.5, 0.3, 0.3, None, "item"]]
CASES.append(case(
    "wall-spread-stood-on", relate,
    plan_of(LIT_ITEMS, {item[0]: [item[0].rsplit(" ", 1)[0].lower().replace(" ", "_")] for item in LIT_ITEMS},
            shapes={**{f"LAMP {number}": {"base": 0.8, "tall": 0.5} for number in (1, 2, 3, 5)},
                    "LAMP 4": {"base": 0.0, "tall": 0.5}, "TV 1": {"base": 0.4, "tall": 0.6}}),
    [{"id": "desk", "noun": "desk", "anchor": "floor", "size": [1.0, 0.6, 0.78]},
     {"id": "shelf", "noun": "shelf", "anchor": "floor", "size": [1.0, 0.4, 1.2]},
     {"id": "rug", "noun": "rug", "anchor": "floor", "size": [2.0, 2.0, 0.02]},
     {"id": "tv_stand", "noun": "tv stand", "anchor": "floor", "size": [1.2, 0.4, 0.5]},
     {"id": "tv", "noun": "tv", "anchor": "floor", "where": "on tv stand", "size": [1.0, 0.1, 0.6]},
     {"id": "lamp", "noun": "lamp", "anchor": None, "where": "living areas, bedrooms", "size": [0.3, 0.3, 0.5]}],
    want={"item/LAMP 1/how": "top", "item/LAMP 1/holder": "DESK 1", "item/LAMP 1/holder row": "desk",
          ("item", among("LAMP 2", "LAMP 3", "LAMP 5"), each("how")): ["floor"] * 3,
          ("item", among("LAMP 2", "LAMP 3", "LAMP 5"), each("height")): [0.0, 0.0, 0.02],  # the last on the rug's top
          "item/LAMP 4": ABSENT, "item/TV 1/how": "top", "item/TV 1/holder": "TV STAND 1"}))
CASES.append(case(
    "wall-spread-named-top", relate,
    plan_of([["BENCH 1", 2.0, 2.0, 1.0, 0.35, None, "item"], ["CASE 1", 3.1, 2.0, 0.35, 0.35, None, "item"],
             ["BOX 1", 5.0, 5.0, 0.3, 0.3, None, "item"]], {"BENCH 1": ["bench"], "CASE 1": ["case"], "BOX 1": ["box"]},
            structure=["floor_plates"],
            shapes={"CASE 1": {"base": 0.49, "tall": 0.3}, "BOX 1": {"base": 0.0, "tall": 0.3}}),
    [{"id": "floor_plates", "noun": "floor plates", "part": "floor", "anchor": "ground"},
     {"id": "bench", "noun": "bench", "anchor": "on:floor_plates", "size": [0.6, 0.6, 0.49]},
     {"id": "case", "noun": "case", "anchor": "on:floor_plates", "where": "on bench", "size": [0.5, 0.4, 0.3]},
     {"id": "box", "noun": "box", "anchor": "on:floor_plates", "where": "on bench", "size": [0.3, 0.3, 0.3]}],
    want={"item/CASE 1/how": "top", "item/CASE 1/holder": "BENCH 1", "item/CASE 1/holder row": "bench",
          "item/BOX 1/how": "floor"}))
GRATING = {"id": "floor_grating", "noun": "grating", "part": "floor", "anchor": "floor"}
GRATING_RAILING = {"id": "railing", "noun": "railing", "anchor": "on:floor_grating", "size": [3.0, 2.0, 1.0], "count": 2}
CASES.append(case(
    "wall-spread-parted-on-floor", relate,
    plan_of([["RAILING 1", 4.0, 4.0, 3.0, 2.0, None, "item"], ["RAILING 2", 4.0, 4.0, 3.0, 2.0, None, "item"],
             ["CRATE 1", 5.0, 6.5, 1.0, 1.0, None, "item"], ["CRATE 2", 5.0, 1.0, 1.0, 1.0, None, "item"]],
            {"RAILING 1": ["railing"], "RAILING 2": ["railing"], "CRATE 1": ["crate"], "CRATE 2": ["crate"]},
            structure=["floor_grating"]),
    [GRATING, GRATING_RAILING, {"id": "crate", "noun": "crate", "anchor": "floor", "size": [1.0, 1.0, 1.0]}],
    want={"item/RAILING 1/spot": ABSENT, "item/RAILING 2/spot": [8.55, 5.0]}))
CASES.append(case(
    "wall-spread-no-floor-room", relate,
    plan_of([["RAILING 1", 0.0, 0.0, 20.0, 12.0, None, "item"], ["RAILING 2", 0.0, 0.0, 20.0, 12.0, None, "item"]],
            {"RAILING 1": ["railing"], "RAILING 2": ["railing"]}, structure=["floor_grating"]),
    [GRATING, GRATING_RAILING], want={"item/RAILING 2/spot": ABSENT}))  # kept as drawn
CASES.append(case(
    "wall-spread-row-on-two-items", relate,
    plan_of([["PIPES 1", 0.2, 1.0, 0.4, 4.0, None, "item"], ["PIPES 2", 0.2, 7.0, 0.4, 4.0, None, "item"]],
            {"PIPES 2": ["pipes"], "PIPES 1": ["pipes"]}, walls=ROOM_WALLS),
    [{"id": "pipes", "noun": "pipes", "anchor": "wall", "where": "left wall", "size": [4.0, 0.2, 0.2], "count": 3}],
    want={("item/PIPES 1/pieces", count): 2, ("item/PIPES 1/pieces", each("spot/1"), steps, magnitude): AtLeast(4.0),
          "item/PIPES 2/pieces": ABSENT}))
CASES.append(case(
    "wall-spread-round-corners", relate,
    plan_of([["CABINETS 1", 1.0, 0.5, 3.5, 0.4, None, "item"]], {"CABINETS 1": ["cabinets"]}, walls=SMALL_ROOM),
    [{"id": "cabinets", "noun": "cabinets", "anchor": "wall", "size": [3.5, 0.4, 0.6], "count": 3}],
    want={("item/CABINETS 1/pieces", count): 3, ("item/CABINETS 1/pieces", each(lies_flat(SMALL_ROOM))): Each(True),
          ("item/CABINETS 1/pieces", each("wall"), distinct): 3}))
BENT = [{"from": [0.0, 4.0], "to": [0.0, 0.0], "thick": 0.1}, {"from": [0.0, 0.0], "to": [4.0, 0.0], "thick": 0.1},
        {"from": [0.0, 11.0], "to": [10.0, 11.0], "thick": 0.1}]
CASES.append(case(
    "wall-spread-bent-wall", relate,
    plan_of([["PIPES 1", 0.5, 0.5, 3.9, 0.2, None, "item"]], {"PIPES 1": ["pipes"]}, walls=BENT),
    [{"id": "pipes", "noun": "pipes", "anchor": "wall", "size": [3.9, 0.2, 0.2], "count": 2}],
    want={"item/PIPES 1/wall/to": [10.0, 11.0], ("item/PIPES 1/pieces", each(lies_flat(BENT[2:]))): Each(True)}))
DUCT = {"id": "duct", "noun": "duct", "anchor": "wall", "size": [8.0, 0.2, 0.2]}
DUCT_PLAN = plan_of([[f"DUCT {number}", 1.0 + 4.0 * number, 0.2, 8.0, 0.2, None, "item"] for number in (0, 1, 2)],
                    {f"DUCT {number}": ["duct"] for number in (0, 1, 2)}, walls=ROOM_WALLS,
                    shapes={f"DUCT {number}": {"base": 2.0} for number in (0, 1, 2)})
CASES.append(case("wall-spread-ducts-slide-then-stand", relate, DUCT_PLAN, [DUCT], want={
    "item/DUCT 0/spot": [5.0, 0.3], "item/DUCT 0/height": ABSENT, "item/DUCT 1/spot": [13.05, 0.0],
    "item/DUCT 1/height": ABSENT, "item/DUCT 2/spot": [13.0, 0.3], "item/DUCT 2/height": 2.25}))
CASES.append(case("wall-spread-band-on-the-floor", holders.wall_band, DUCT, 0.0, 0.2, ROOM_WALLS[0], DUCT_PLAN,
                  want={(): (0.0, 0.0)}))
RED_PIPES_ROWS = [{"id": "hull", "noun": "hull", "part": "wall", "anchor": "floor"},
                  {"id": "red_pipes", "noun": "pipes", "anchor": "on:hull", "size": [20.0, 12.0, 0.2], "count": 4},
                  {"id": "rug", "noun": "rug", "anchor": "floor", "size": [20.0, 12.0, 0.2]}]
CASES.append(case(
    "wall-spread-made-size", holders.built_rows, RED_PIPES_ROWS,
    plan_of([[f"RED PIPES {number}", 0.0, 0.0, 20.0, 12.0, None, "item"] for number in (1, 2)],
            {f"RED PIPES {number}": ["red_pipes"] for number in (1, 2)}, walls=ROOM_WALLS),
    {"rows": RED_PIPES_ROWS, "picture": PICTURE},
    want={(by_id("size"),): {"red_pipes": [16.0, 0.2, 0.2], "rug": [20.0, 12.0, 0.2]}}))  # the run's piece, on a wall
TALL_BOX = [{"from": [0.0, 0.0], "to": [3.5, 0.0], "thick": 0.1, "tall": 2.8},
            {"from": [3.5, 0.0], "to": [3.5, 2.0], "thick": 0.1, "tall": 2.8},
            {"from": [3.5, 2.0], "to": [1.75, 2.0], "thick": 0.1, "tall": 2.8},
            {"from": [1.75, 2.0], "to": [0.0, 2.0], "thick": 0.1, "tall": 2.8},
            {"from": [0.0, 2.0], "to": [0.0, 0.0], "thick": 0.1, "tall": 2.8}]
UPPER = {f"item/PIPE {number}/{key}": wanted for number in (3, 4) for key, wanted in (
    ("wall/from/1", 2.0), ("wall/to/1", 2.0), ("spot/1", 2.0), ("side", 1), ("why", Holds("nearest wall with room")))}
CASES.append(case(
    "wall-spread-upper-walls", relate,
    plan_of([[f"PIPE {number}", 0.15 + 0.1 * number, 0.1, 3.0, 0.2, None, "item"] for number in (1, 2, 3, 4)],
            {f"PIPE {number}": ["pipe"] for number in (1, 2, 3, 4)}, walls=TALL_BOX, w=3.5, d=2.0,
            outline=[[0.0, 0.0], [3.5, 0.0], [3.5, 2.0], [0.0, 2.0]],
            shapes={f"PIPE {number}": {"base": 2.6} for number in (1, 2, 3, 4)}),
    [{"id": "pipe", "noun": "pipe", "anchor": "wall", "where": "upper walls", "size": [3.0, 0.2, 0.2]}],
    want={("item", among("PIPE 1", "PIPE 2", "PIPE 3", "PIPE 4"), each("height")): [ABSENT, 2.35, ABSENT, 2.35],
          **UPPER, ("item/PIPE 3/wall", length): Near(3.0), ("item/PIPE 4/wall", length): Near(3.0),
          (clear,): AtMost(holders.WALL_TOUCH)}))  # the south wall full: on the north run of two walls
THICK = [{"from": [0.0, 3.2], "to": [0.0, 0.0], "thick": 0.4}, {"from": [0.0, 0.0], "to": [3.0, 0.0], "thick": 0.4},
         {"from": [3.0, 0.0], "to": [3.0, 3.2], "thick": 0.4}, {"from": [3.0, 3.2], "to": [0.0, 3.2], "thick": 0.4}]
CASES.append(case(
    "wall-spread-corner-trims", relate,
    plan_of([["CABINET 1", 0.0, 0.0, 0.4, 0.8, None, "item"], ["CABINET 2", 0.0, 0.85, 0.4, 0.8, None, "item"]],
            {"CABINET 1": ["kitchen_cabinet"], "CABINET 2": ["kitchen_cabinet"]}, walls=THICK, w=3.0, d=3.2,
            outline=[[0.0, 0.0], [3.0, 0.0], [3.0, 3.2], [0.0, 3.2]],
            shapes={f"CABINET {number}": {"base": 1.5} for number in (1, 2)}),
    [{"id": "kitchen_cabinet", "noun": "cabinet", "anchor": "wall", "size": [0.8, 0.4, 0.8]}],
    want={"item/CABINET 2/spot/1": AtLeast(1.0 + 0.4 - holders.WALL_TOUCH),  # its face starts at 0.2 m
          "item/CABINET 2/why": Holds("slid"), (clear,): AtMost(holders.WALL_TOUCH)}))
CASES.append(case(
    "wall-spread-tunnel-first", relate,
    plan_of([["MONITOR 1", 9.8, 0.1, 0.4, 0.1, None, "item"], ["GLASS TUNNEL 1", 7.5, 0.0, 5.0, 0.5, None, "item"]],
            {"MONITOR 1": ["monitor"], "GLASS TUNNEL 1": ["glass_tunnel"]}, walls=ROOM_WALLS),
    [{"id": "glass_tunnel", "noun": "tunnel", "anchor": "wall", "size": [5.0, 3.0, 3.0]},
     {"id": "monitor", "noun": "monitor", "anchor": "wall", "size": [0.4, 0.1, 0.3]}],
    want={"item/GLASS TUNNEL 1/spot": [10.0, 0.25], "item/MONITOR 1/why": Holds("slid"),  # the tunnel its own wall
          (clear,): AtMost(holders.WALL_TOUCH)}))
CASES.append(case(
    "wall-spread-under-the-wall-top", relate,
    plan_of([["CONDUIT 1", 8.0, 0.1, 3.0, 0.1, None, "item"]], {"CONDUIT 1": ["conduit"]},
            walls=[{**wall, "tall": 11.8} for wall in ROOM_WALLS], shapes={"CONDUIT 1": {"base": 12.0}}),
    [{"id": "conduit", "noun": "conduit", "anchor": "wall", "size": [3.0, 0.1, 12.0]}],
    want={"item/CONDUIT 1/height": 0.0}))
NARROW = [{"from": [0.0, 0.0], "to": [3.2, 0.0], "thick": 0.1, "tall": 3.0},
          {"from": [3.2, 0.0], "to": [3.2, 1.0], "thick": 0.1, "tall": 3.0},
          {"from": [3.2, 1.0], "to": [0.0, 1.0], "thick": 0.1, "tall": 3.0},
          {"from": [0.0, 1.0], "to": [0.0, 0.0], "thick": 0.1, "tall": 3.0}]
NARROW_OUTLINE = [[0.0, 0.0], [3.2, 0.0], [3.2, 1.0], [0.0, 1.0]]
CASES.append(case(
    "wall-spread-stuck-laid-first", relate,
    plan_of([["LAMP 1", 1.5, 0.0, 0.2, 0.1, None, "item"], ["LAMP 2", 1.5, 0.9, 0.2, 0.1, None, "item"],
             ["BOARD 1", 0.1, 0.0, 3.0, 0.1, None, "item"]],
            {"LAMP 1": ["wall_lamp"], "LAMP 2": ["wall_lamp"], "BOARD 1": ["notice_board"]}, walls=NARROW, w=3.2, d=1.0,
            outline=NARROW_OUTLINE),
    [{"id": "wall_lamp", "noun": "lamp", "anchor": "wall", "size": [0.2, 0.1, 0.3]},
     {"id": "notice_board", "noun": "board", "anchor": "wall", "size": [3.0, 0.1, 2.9]}],
    want={"item/BOARD 1/spot": [1.6, 0.05], "item/LAMP 1/wall/to": [0.0, 1.0],
          (clear,): AtMost(holders.WALL_TOUCH)}))  # the board laid first: the lamps part round it
CASES.append(case(
    "wall-spread-under-a-hung-light", relate,
    plan_of([["PIPE THICK 1", 0.25, 0.1, 3.0, 0.15, None, "item"], ["PIPE THICK 2", 0.1, 0.2, 3.0, 0.15, None, "item"],
             ["CEILING LIGHT 1", 2.0, 0.1, 0.8, 0.3, "S", "item"]],
            {"PIPE THICK 1": ["pipe_thick"], "PIPE THICK 2": ["pipe_thick"], "CEILING LIGHT 1": ["ceiling_light"]},
            walls=NARROW, w=3.2, d=1.0, outline=NARROW_OUTLINE,
            shapes={f"PIPE THICK {number}": {"base": 2.6} for number in (1, 2)}),
    [{"id": "pipe_thick", "noun": "pipe", "anchor": "wall", "size": [3.0, 0.15, 0.15]},
     {"id": "ceiling_light", "noun": "light", "anchor": "ceiling", "size": [0.8, 0.3, 0.1]}],
    want={(hung, count): 1, (hung, "0/6"): Near(2.99, 1e-6),  # under the walls' 3 m: no roof drawn
          "item/PIPE THICK 2/height": 2.4,  # 2.8 m would meet the light hung at 2.89 m
          (meets_hung("PIPE THICK 1"),): AtMost(holders.WALL_TOUCH),
          (meets_hung("PIPE THICK 2"),): AtMost(holders.WALL_TOUCH)}))
CASES.append(case(
    "wall-spread-door-on-its-own-item", relate,
    plan_of([[plan_checks.WALLS_ITEM, 0.0, 0.0, 20.0, 12.0, None, "item"], ["SHOP DOOR 1", 14.5, 0.0, 1.0, 0.2, None, "item"]],
            {plan_checks.WALLS_ITEM: ["front_wall", "shop_door"], "SHOP DOOR 1": ["shop_door"]},
            structure=["front_wall"], walls=ROOM_WALLS,
            openings=[{"kind": "door", "at": [3.0, 0.0], "wide": 1.0, "sill": 0.0, "head": 2.1},
                      {"kind": "door", "at": [15.0, 0.0], "wide": 1.0, "sill": 0.0, "head": 2.1}]),
    [{"id": "front_wall", "noun": "wall", "part": "wall", "anchor": "floor"},
     {"id": "shop_door", "noun": "door", "anchor": "on:front_wall", "size": [1.0, 0.1, 2.1]}],
    want={("relations", where("row", "shop_door"), each("item")): ["SHOP DOOR 1"],
          ("relations", where("row", "shop_door"), each("opening/at")): [[15.0, 0.0]]}))
CASES.append(case("wall-spread-a-pile-piles", holders.piles, {"id": "sandbags", "size_words": "knee high pile"},
                  want={(): True}))
CASES.append(case("wall-spread-a-railing-does-not-pile", holders.piles,
                  {"id": "railing", "where": "around engines", "size_words": "waist high"}, want={(): False}))
CASES.append(case("wall-spread-pile-words-are-plan-fixes-own", getattr, holders, "PILE_WORDS",
                  want={(): plan_fixes.PILE_WORDS}))
ENGINE_RAILINGS = {f"RAILING {number}": ["railing"] for number in range(1, 5)}
CASES.append(case(
    "wall-spread-around-engines", relate,
    plan_of([["ENGINE 1", 3.0, 4.0, 3.0, 1.5, "N", "item"], ["ENGINE 2", 13.0, 4.0, 3.0, 1.5, "N", "item"],
             *[[name, 6.0, 6.0, 3.5, 0.4, None, "item"] for name in ENGINE_RAILINGS]],
            {"ENGINE 1": ["engine"], "ENGINE 2": ["engine"], **ENGINE_RAILINGS},
            shapes={f"RAILING {number}": {"base": float(number - 1), "tall": 1.0} for number in range(1, 5)}),
    [{"id": "grating", "noun": "grating", "part": "floor", "anchor": "floor"},
     {"id": "engine", "noun": "engine", "anchor": "on:grating", "size": [3.0, 1.5, 1.5]},
     {"id": "railing", "noun": "railing", "anchor": "on:grating", "where": "around engines", "size": [3.5, 0.4, 1.0]}],
    want={("item", among(*ENGINE_RAILINGS), each("spot"), distinct): 4,
          ("item", among(*ENGINE_RAILINGS), each("height"), unique): [0.0],
          # each beside one engine's side, 0.2 m (its depth's half) and PIECE_GAP off it
          ("item", among(*ENGINE_RAILINGS), each("spot", off_nearest([[4.5, 4.75], [14.5, 4.75]]))):
              Each(OneOf(1.5 + 0.25, 0.75 + 0.25)),
          ("item", among(*ENGINE_RAILINGS), each("why")): Each(Holds("round engine"))}))
PLAZA_ROWS = [{"id": "plaza", "noun": "plaza", "part": "ground", "anchor": "ground"},
              {"id": "tower", "noun": "tower", "anchor": "on:plaza", "size": [2.0, 2.0, 18.0]},
              {"id": "crowd", "noun": "crowd", "anchor": "on:plaza", "size": [0.5, 0.3, 1.8]},
              {"id": "lantern_string", "noun": "lanterns", "anchor": "on:plaza", "where": "above plaza",
               "size": [16.0, 0.5, 0.5]},
              {"id": "stage_screen", "noun": "screen", "anchor": "on:plaza", "where": "stage back", "size": [8.0, 0.5, 6.0]}]
PLAZA_ITEMS = [["TOWER 1", 0.0, 4.0, 2.0, 2.0, None, "item"], ["TOWER 2", 18.0, 4.0, 2.0, 2.0, None, "item"],
               ["CROWD 1", 0.0, 0.0, 20.0, 12.0, None, "item"], ["LANTERN STRING 1", 2.0, 5.0, 16.0, 0.5, None, "item"],
               ["STAGE SCREEN 1", 6.0, 8.0, 8.0, 0.5, None, "item"], ["STAGE SCREEN 2", 6.0, 10.0, 8.0, 0.5, None, "item"]]


def plaza(items):
    """The plaza with its deck 3.3 m up and the items given."""
    return plan_of(items, {"TOWER 1": ["tower"], "TOWER 2": ["tower"], "CROWD 1": ["crowd"],
                           "LANTERN STRING 1": ["lantern_string"], "STAGE SCREEN 1": ["stage_screen"],
                           "STAGE SCREEN 2": ["stage_screen"]},
                   levels=[{"height": 3.3, "points": [[5.0, 9.0], [15.0, 9.0], [15.0, 12.0], [5.0, 12.0]]}],
                   shapes={"LANTERN STRING 1": {"base": 6.0, "tall": 0.5}, "STAGE SCREEN 1": {"base": 3.3, "tall": 6.0},
                           "STAGE SCREEN 2": {"base": 3.3, "tall": 6.0}, "TOWER 1": {"tall": 18.0},
                           "TOWER 2": {"tall": 18.0}, "CROWD 1": {"tall": 1.8}})


CASES.append(case("wall-spread-plaza", relate, plaza(PLAZA_ITEMS), PLAZA_ROWS, want={
    "item/LANTERN STRING 1/how": "hung", "item/LANTERN STRING 1/holders": ["TOWER 1", "TOWER 2"],
    "item/STAGE SCREEN 1/height": 0.0, "item/STAGE SCREEN 2/height": ABSENT}))
CASES.append(case("wall-spread-plaza-without-towers", relate, plaza(PLAZA_ITEMS[2:]), PLAZA_ROWS,
                  want={"item/LANTERN STRING 1/how": "floor"}))
OWN_WALL = {"from": [5.0, 4.0], "to": [6.0, 4.0], "thick": 0.1, "tall": 2.8}
INNER_WALL = {"from": [5.0, 5.0], "to": [8.0, 5.0], "thick": 0.1, "tall": 2.8}
PIPE_CONTEXT = ({"item": "PIPE 2", "row": "pipe", "how": "wall", "wall": OWN_WALL, "side": 1, "spot": [5.5, 4.0]},
                {"id": "pipe", "noun": "pipe", "anchor": "wall", "size": [3.0, 0.2, 0.2]},
                plan_of([], {}, walls=[OWN_WALL, INNER_WALL]), 1.0, [])
CASES.append(case("wall-spread-onto-an-inner-wall", holders.walled_clear, *PIPE_CONTEXT,
                  want={"0/spot": [5.5, 5.0], "1": 1.0}))
CASES.append(case("wall-spread-its-row-already-there", holders.walled_clear, *PIPE_CONTEXT, [("pipe", [5.5, 5.0], 1.0)],
                  want={(elsewhere([5.5, 5.0], 1.0),): True}))
RAILED = {"items": [[f"RAIL {number}", 2.0 * number, 1.0, 1.0, 1.0, None, "item"] for number in (1, 2, 3, 4)],
          "rows": {f"RAIL {number}": ["railing"] for number in (1, 2, 3, 4)}}
RAILED_TIED = {"railing": [f"RAIL {number}" for number in (1, 2, 3, 4)]}
CASES.append(case("wall-spread-pieces-at-an-item", holders.pieces_at, "RAIL 1", {"id": "railing", "count": 8}, RAILED,
                  RAILED_TIED, want={(): 2}))
for number in (1, 2, 3, 4):
    CASES.append(case(f"wall-spread-pieces-at-rail-{number}-after-drops", holders.pieces_at, f"RAIL {number}",
                      {"id": "railing", "count": 8},
                      {**RAILED, "dropped": [{"item": "railing", "why": "4 more of it than the place's free floor holds",
                                              "laid": 4}]}, RAILED_TIED, want={(): 1}))

# kept, loose, open-doorway
CASES.append(case("kept", kept, plan_of([], {}), {"rows": []}, want={
    "first": ["hut"], "second": [], "sha": holders.plan_sha(json.dumps(plan_of([], {})))}))
CASES.append(case(
    "loose", relate,
    plan_of([], {}, walls=[{"from": [0.0, 6.0], "to": [20.0, 6.0], "thick": 0.2}],
            openings=[{"kind": "door", "at": at, "wide": 1.0, "sill": 0.0, "head": 2.0}
                      for at in ([5.0, 0.0], [10.0, 6.0], [10.0, 3.0])]), [], picture=None,
    want={"loose": [{"opening": 3, "at": [10.0, 3.0], "why": "it sits on no wall the shell builds"}]}))
CASES.append(case(
    "open-doorway", relate,
    plan_of([], {}, shell="kit", inside=False, walls=[],
            openings=[{"kind": "door", "at": [1.4, 19.4], "wide": 1.0, "sill": 0.14, "head": 2.2, "to": "stairwell"}]),
    [], picture=None, want={"loose": ABSENT}))


@pytest.mark.parametrize("judge, args, kwargs, want", CASES)
def test_each_plan_item_names_what_holds_it(judge, args, kwargs, want):
    """Each row's answer holds what its want names, part by part."""
    answer = judge(*args, **kwargs)
    for path, wanted in want.items():
        got = probe(answer, path if isinstance(path, tuple) else (path,), answer)
        assert wanted == got, (path, got, wanted)
