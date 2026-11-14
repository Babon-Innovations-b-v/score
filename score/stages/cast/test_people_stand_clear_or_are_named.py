"""The cast stands every person and crowd copy on something solid, clear of every solid and of each other, or leaves
them out by name; a look with no usable dressed body fails the characters layer by name, never a stand-in
(cast/__init__.py, measure.py, spread.py, layer.py); a person whose place's sim body ran plays its simulated motion,
its feet on its sim body's, and one without keeps its clip, named (driven.py).

Measured on a toy place made here (a 10 m floor and a 1 m crate), small crowds and plans written here, and the
characters layer made with no dressed body at all. The hub's round-three seed and the motion work's built body the
old tests needed went with the old disk (2026-10-19): those tests only ever skipped, so their rules are held here on
geometry of the test's own.

Breaks that turn it red (each applied once and seen red, then reverted):
- `spread.grounded`: `or next(clashes)` dropped  -> the stood test (the member stays in the crate).
- `spread.grounded`: `or not next(level)` dropped  -> the deck edge test (the member stays over the edge).
- `feet.grounded`: `or next(low)` dropped  -> the deck edge test (the member by the low block stays over it).
- `feet.feet_into`: `- {on}` dropped  -> the deck edge test (the slope's own ground in its feet's way).
- `feet.feet_kept`: `spread.grounded = grounded` dropped  -> the deck edge test (the member stays over the block).
- `feet.grounded`: `or next(steep)` dropped  -> the deck edge test (the person on the 31 degree slope stands).
- `feet.tilt_under`: `np.hypot(rise[:, 0], rise[:, 1])` read as `rise[:, 0]` (the fall along x only)  -> the deck
  edge test (the slope rising along z reads level).
- `walks.walk_clear`: `abs(spot[1] - at[1]) <= measure.FOOT_STEP and` dropped, or read off its leg's start
  (`feet[0][1]`, starts kept at any level)  -> the deck edge test (the walker on the 1 m kerb walks the floor beside
  it).
- `walks.walk_clear`: `and not kept.overlaps(spot)` dropped  -> the deck edge test (the walker walks through the
  worker).
- `walks.stand_every`: the walker's `walk_clear` dropped  -> the deck edge test (it walks off the floor's end).
- `walks.walks_kept`: `spread.stand_every = stand_every` dropped  -> the deck edge test (the walker stays facing
  -z).
- `feet.facing_seats`: `turn=` left as it came  -> the deck edge test (the sitter faces its chair's back).
- `feet.facing_seats`: `math.atan2(away[0], away[1])` read as `math.atan2(away[1], away[0])`  -> the deck edge test.
- `feet.seats_faced`: `cast.on_support, cast.dealt = supported, dealt` made `pass`  -> the deck edge test (the
  sitter dealt at its design's turn, facing its chair's back).
- `feet.seats_faced`'s dealt: `dict(single, turn=...)` left as `single`  -> the deck edge test (the same).
- `feet.seat_depth`: `hits[:, 1] >= top - SEAT_BAND` read as `np.abs(hits[:, 1] - top) <= SEAT_BAND`  -> the deck
  edge test (the bed's pillow ends it: its sitter left at its middle, as quarters' person_bed was).
- `feet.edge_seated`: its `<= DEEP` return made `return person` always  -> the deck edge test (the bed's sitter left at
  its middle); `if not into` made `if into` (the walled edge taken)  -> the same; seats_faced's `people.append(turned)`
  made `people.append(person)`  -> the same (the record's spot left at the bed's middle).
- `measure.level_under`: `np.abs(row) <= FOOT_STEP` read as `<= 1.0`  -> the deck edge test.
- `measure.level_under`: `- plane @ np.linalg.pinv(plane)` dropped (the gaps judged off the feet, not off a plane)
  -> the deck edge test (the person on the slope is left out).
- `measure.run_into`: `sorted(names) if hit else []` read as `[]`  -> the stood test.
- `spread.NUDGES`: the rings past 1.2 m out to NUDGE_FAR dropped  -> the stood test (the member among the beds
  left out).
- `cast.seated_clear`: `if not into` read as `if True`  -> the stood test (the bench's sitter stays under the
  laptop).
- `measure.seat_spots`: the `- BODY_RADIUS` dropped (spots to the seat's very ends)  -> the stood test (85 spots
  across the bench, not 13 along it).
- `cast.overlaps`: `< measure.KNEE` read as `< 100`  -> the apart test (bodies on two levels overlap).
- `cast.off_ground`: `> STAND_SLACK` read as `> 1.0`  -> the stood test (a body 0.10 m off judged standing).
- `cast.short_of`: the packed `not crowd["copies"]` branch dropped  -> the crowd test (the packed crowd none of whose spots fit).
- `driven.bodiless`: `.startswith(NO_BODY)` read as `False` (a person with no body passes)  -> the dressed body test.
- `cast.made_row`: `row if row in inputs else None` read as `row`  -> the dressed body test (a look with no dress row made).
- `spread.on_ground`: `not grounds or` read as `True or`  -> the crowd test (spots between the two grounds).
- `spread.far_enough`: `< FAR_SHARE` read as `<= 1.0`  -> the crowd test (the copy before the door kept).
- `cast.plan_views`: the `unaimed` refusal dropped  -> the crowd test (the spot aimed off its items).
- `cast.on_levels`: `at[1] + min(heights)` read as `at[1]`  -> the stood test.
- `cast.off_flight`: the spot's height left out (`at - foot` over x and z only)  -> the stood test (the man, on his
  3 m landing, goes onto the flight under him, nearer across the floor).
- `cast.stairs_of`: `"down" if "down" in words` read as `"up"`  -> the stood test.
- `cast.on_stairs`: `(lowest, highest) if ... == "up"` read as `(highest, lowest)`  -> the stood test.
- `cast.off_the_plan`: `not any(...)` read as `False`  -> the stood test (the spot off the plan stood).
- `cast.on_made_ground`: `ground > at[1]` read as `False`  -> the stood test (the one under the rise found
  nothing under it).
- `layer.make`: `if row is None or row not in inputs:` read as `if row is None:`  -> the dressed body test (it reaches for
  a body that is not there instead of naming the gap).
- `driven.size_over_sim`: `/ float(body["size"]["of the rig"])` dropped  -> the sim body test (the 1.1 body's sim
  hips raised 10% again: feet off).
- `driven.write_driven`: Hips' simulated translation not written  -> the sim body test (the clip's path kept).
- `driven.lay_sim_body`: the Turned transform not set  -> the sim body test (the sim body mirrored off the skin).
- `driven.judge_on_its_sim_body`: `> FEET_WITHIN` read as `> 1.0`  -> the sim body test (the skeleton turned back to its clip's hips).
- tools/characters/cast_check.py `repeated_people`: `len(names) > 1` read as `> 9`  -> the apart test.
- tools/characters/cast.py `kit_mix`: `if not builds or name in builds` dropped, or `(kit or {}).get("plain") or`
  dropped  -> the apart test (a kit group wears a build or outfit off its kit).
- tools/characters/cast.py `look_of`: the head and hair parts left out  -> the apart test (two kit draws of one build
  in other hair the same person).
- `measure.KNEE` changed off cast_check's  -> the apart test (the copied body sizes disagree).
- `measure.seat_top`: `SEAT_LOW <=` dropped (the crate's floor face a seat)  -> the stood test (the second
  seated person seated on the crate).
- `cast.on_support`: `taken.add(name)` dropped  -> the stood test (two people on one stool).
- `cast.on_support`: a seated person's `at=at` dropped  -> the stood test (seated on the floor at its spot).
- `cast.on_support`: `max(tops) > person["at"][1]` read as `True`  -> the stood test (one over it lowered).
- `measure.run_into`: `- {seat}` dropped  -> the stood test (the seated body runs into its own stool's back).
- `cast.off_ground`: the no-seat branch dropped  -> the stood test (a seated one with no seat stands).
- `people_rows.doing_of`: `"seated" if seat_of(row) else` dropped  -> the stood test (a stool's sitter sits on
  the ground); `people_rows.cast_record`: `"anchor"` dropped  -> the stood test (nobody supported).
- `cast.unseated`: `doing="standing"` dropped  -> the stood test (one with no seat stays seated, off members).
- `cast.judge_standing`: the unseated findings dropped  -> the stood test (stood for want of a seat unnamed).
- `cast.on_stairs`: `runs[flight["name"]] != (0, ...)` dropped from the flight's order  -> the stood test (the man
  under the deck).
- `cast.on_stairs`: `runs[flight["name"]] or` dropped (the whole flight walked, its clear run unread)  -> the stood
  test (the woman on the tread under the slab).
- `stages.GAP_GATES`: `"characters-layer": ("bodies",)` dropped, or `driven.judge_bodies`'s finding not starting
  "<name>: "  -> the dressed body test (a gap naming every one with no body no longer moves the fail).
- `cast.planned`: `"spots": spots` dropped (the plan's spots not handed to the cast record)  -> the stood test
  (the climber at the plan's middle, off its spot (0, 0, -3)).
"""
import json
import pathlib
import sys
import types

import numpy as np
import pytest
import trimesh
from pxr import Usd, UsdGeom

from score import checks, stages
from score.stages import cast, gaps
from score.stages.cast import driven, feet, layer, measure, spread, walks
from score.stages.scene_record import writer

REPO = pathlib.Path(__file__).resolve().parents[3]
PLACES = REPO / "data/definitions/place.json"


def mesh(stage, path, corners, faces):
    shape = UsdGeom.Mesh.Define(stage, path)
    shape.CreatePointsAttr(corners)
    shape.CreateFaceVertexCountsAttr([len(face) for face in faces])
    shape.CreateFaceVertexIndicesAttr([index for face in faces for index in face])


def toy_place(folder):
    """base.usda of place `camp`: a 10 m floor from -5 to 5 at height 0 and a 1 m crate from 0 to 1 on it."""
    stage = Usd.Stage.CreateNew(str(folder / "base.usda"))
    UsdGeom.Xform.Define(stage, "/camp")
    mesh(stage, "/camp/Ground/floor", [(-5, 0, -5), (5, 0, -5), (5, 0, 5), (-5, 0, 5)], [(0, 1, 2, 3)])
    corners = [(x, y, z) for x in (0, 1) for y in (0, 1) for z in (0, 1)]
    mesh(stage, "/camp/Objects/crate", corners,
         [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)])
    stage.Save()
    return measure.solids(folder / "base.usda", "camp")


def off_the_crate(spot):
    """How far a spot stands from the crate's footprint, sideways, metres."""
    dx = max(0.0 - spot[0], 0.0, spot[0] - 1.0)
    dz = max(0.0 - spot[2], 0.0, spot[2] - 1.0)
    return (dx * dx + dz * dz) ** 0.5


def seat_place(folder):
    """base.usda of place `camp`: the toy floor, a 1 m crate `crate_1` from 0 to 1 and a 0.4 m stool `stool_1_1` at
    3 to 3.4, its seat 0.45 high, its back a board 0.05 thick up to 0.9 along its far side; a bench `bench_1_1` 0.45
    high, x -3 to -2.4, z 0 to 2, and a laptop `laptop_1` 0.4 m square from 1.2 to 1.25 over its middle (quarters'
    laptop on the bunk over its sitter, 2026-11-12)."""
    stage = Usd.Stage.CreateNew(str(folder / "seats.usda"))
    UsdGeom.Xform.Define(stage, "/camp")
    mesh(stage, "/camp/Ground/floor", [(-5, 0, -5), (5, 0, -5), (5, 0, 5), (-5, 0, 5)], [(0, 1, 2, 3)])
    box = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    mesh(stage, "/camp/Objects/crate_1", [(x, y, z) for x in (0, 1) for y in (0, 1) for z in (0, 1)], box)
    mesh(stage, "/camp/Objects/stool_1_1", [(x, y, z) for x in (3, 3.4) for y in (0, 0.45) for z in (3, 3.4)]
         + [(x, y, z) for x in (3, 3.4) for y in (0.45, 0.9) for z in (3.35, 3.4)],
         box + [tuple(index + 8 for index in face) for face in box])
    mesh(stage, "/camp/Objects/bench_1_1", [(x, y, z) for x in (-3, -2.4) for y in (0, 0.45) for z in (0, 2)], box)
    mesh(stage, "/camp/Objects/laptop_1", [(x, y, z) for x in (-2.9, -2.5) for y in (1.2, 1.25) for z in (0.8, 1.2)],
         box)
    stage.Save()
    return measure.solids(folder / "seats.usda", "camp")


def made_place(folder):
    """Place `camp` with a base.usda of no solid of its own and the terrain row's made ground
    (world/places/camp.usdc): a rise 2 m up over x -5 to 0 and a hollow 1 m down over x 0 to 5, both over z 6 to 14,
    past the seats (wreck's made ground, an earth seed whose plan lays no shell). Returns the terrain row's inputs."""
    folder.mkdir()
    base = Usd.Stage.CreateNew(str(folder / "base.usda"))
    UsdGeom.Xform.Define(base, "/camp")
    base.Save()
    ground = Usd.Stage.CreateNew(str(folder / "world/places/camp.usdc"))
    mesh(ground, "/camp/Ground/rise", [(-5, 2, 6), (0, 2, 6), (0, 2, 14), (-5, 2, 14)], [(0, 1, 2, 3)])
    mesh(ground, "/camp/Ground/hollow", [(0, -1, 6), (5, -1, 6), (5, -1, 14), (0, -1, 14)], [(0, 1, 2, 3)])
    ground.Save()
    return {"terrain": str(folder)}


FLOOR = {"gap": 0.0, "on": "Ground/floor", "water": False}
NOTHING = {"gap": None, "on": None, "water": False}
# Where a body's spot is measured: (world, its spots, the ground under each, the solids each runs into). `bare` is a
# base with no solid (every body stands on nothing, for the standing gate to name, never failing the make); `made` the
# same base measured with its made ground. A ground of None is not read (the body inside the crate).
MEASURED = [
    ("toy", [[0.5, 0.0, 0.5], [3.0, 0.0, 3.0]], [None, FLOOR], [["Objects/crate"], []]),
    ("bare", [[0.0, 0.0, 0.0], [1.0, 0.0, 1.0]], [NOTHING, NOTHING], [[], []]),
    ("made", [[-2.0, 2.0, 10.0]], [{"gap": 0.0, "on": "Ground/rise", "water": False}], [[]]),
]
# What is wrong with where a body's feet are: (the body's measure, the finding, whether the finding is the whole of it).
OFF_GROUND = [
    ({"gap": 0.03, "on": "Ground/floor", "water": False}, None, True),
    ({"gap": 0.1, "on": "Ground/floor", "water": False}, "+0.10 m off", False),
    ({"gap": 0.0, "on": "Ground/floor", "water": True}, "standing in the water", True),
    ({"gap": None, "on": None, "water": False}, "nothing solid", False),
    ({"gap": 0.0, "on": "Ground/floor", "water": False, "seat": None}, "no seat", False),
    ({"gap": 0.0, "on": "Objects/stool_1_1", "water": False, "seat": "Objects/stool_1_1"}, None, True),
]


# The plan the camp's people are dealt from (#76: never a copy in rows.json that drifts from it): 20 m square cornered
# at (-5, -5) in the place's frame, its middle (5, 0, 5), its untagged spot (5, 2) at (0, 0, -3) for the seat rows, a
# 3 m landing over x 10 to 12, z -5 to -3, a flight up from it (3 to 4.5 m) and one down from 1.5 m to the floor drawn
# from its high end (the stairwell's, Batch 1 and 2026-11-04), and each other row's own spot: the man on the landing
# by his flight, the woman and one on no stairs on the floor, one on the landing, one under the made ground's rise
# (-2, 0, 10), one over its hollow (2, 0, 10), and one off the plan (16, 0, -4) (the hangar's workers, 2026-11-04).
PLAN = {"w": 20.0, "d": 20.0, "frame": {"anchor": {"plan": [0.0, 0.0], "place": [-5.0, 0.0, -5.0]}},
        "levels": [{"height": 3.0, "points": [[15.0, 0.0], [17.0, 0.0], [17.0, 2.0], [15.0, 2.0]]}],
        "stairs": [{"kind": "stair", "points": [[17.0, 0.0], [18.0, 0.0], [18.0, 2.0], [17.0, 2.0]], "from": 3.0,
                    "to": 4.5, "angle": 270.0, "steps": 3},
                   {"kind": "stair", "points": [[16.6, 2.0], [17.6, 2.0], [17.6, 4.0], [16.6, 4.0]], "from": 1.5,
                    "to": 0.0, "angle": 90.0, "steps": 3}],
        "people": [[5.0, 2.0, 0], [16.9, 1.95, 0, "man"], [18.0, 3.0, 0, "woman"], [18.0, 3.0, 0, "still"],
                   [16.0, 1.0, 0, "walkway"], [3.0, 15.0, 0, "hill"], [7.0, 15.0, 0, "dip"], [21.0, 1.0, 0, "off"]]}
SITTER = {"name": "astronaut", "where": "sitting at dining table", "anchor": "on:stool_1", "looks": ["astro-made"] * 2}
STANDER = {"name": "person in uniform", "where": "by the console", "looks": ["person-made"]}
DESIGN = {"places": {"camp": {"concept": "a" * 64, "rows": {
    "sitter": SITTER, "unlaid": dict(SITTER, anchor="on:chair", looks=["astro-made"]),
    "climber": dict(SITTER, anchor="on:crate", where="standing", looks=["astro-made"]),
    "man": {"name": "man walking up stairs", "where": "middle flight of stairs", "looks": ["man-made"]},
    "woman": {"name": "woman walking down stairs", "where": "bottom flight of stairs", "looks": ["woman-made"]},
    "still": STANDER, "walkway": STANDER, "hill": STANDER, "dip": STANDER, "off": STANDER}}}}
UP_TOP, DOWN_TOP = [12.5, 4.5, -4.6667], [12.1, 1.5, -2.6667]  # the last tread up the high flight, the low one's top
DOWN_FOOT = [12.1, 0.5, -1.3333]  # the low flight's lowest tread
# The stairs the camp's solids leave clear: (id, the solids over them, the man's flight, spot and last tread, the
# woman's). A deck 1.5 m over the man's flight (the stairwell's 3 m deck over its flight from the 1.5 m landing,
# 2026-11-10): he walks up the nearest flight he walks clear, the low one. A slab over the low flight's top tread too
# (its stacked flights, no flight clear end to end, 2026-11-10): the woman walks its clear treads, the man the nearest
# flight whole, for the clear gate to name.
DECK = ("Shell/deck_2", [1.2, 0.2, 2.0], [12.5, 5.1, -4.0])
SLAB = ("Shell/deck_4", [1.2, 0.2, 0.5], [12.1, 3.1, -2.67])
STAIR_WORLDS = [
    ("clear", [], ("stair_1", [12.5, 3.5, -3.3333], UP_TOP), ("stair_2", DOWN_TOP, DOWN_FOOT)),
    ("under a deck", [DECK], ("stair_2", DOWN_FOOT, DOWN_TOP), ("stair_2", DOWN_TOP, DOWN_FOOT)),
    ("under a deck and a slab", [DECK, SLAB], ("stair_1", [12.5, 3.5, -3.3333], UP_TOP),
     ("stair_2", [12.1, 1.0, -2.0], DOWN_FOOT)),
]


def stood_cast(found, height):
    """The camp's people as cast.make stands them before they are spread apart (its bake left out): dealt their plan
    spots, each its stairs read off its row, raised to its level and onto the made ground (`height`), the ones off the
    plan refused, then each on its stairs and its support among `found`. Returns (record, refused)."""
    from score.stages import people_rows
    record = cast.on_made_ground(cast.on_levels(cast.with_stairs(people_rows.cast_record(
        "camp", cast.planned(DESIGN, "camp", PLAN)), "camp", DESIGN), PLAN), height)
    refused = cast.off_the_plan(record, PLAN)
    record = dict(record, people=[person for person in record["people"] if person["name"] not in refused])
    return cast.on_support(cast.on_stairs(record, PLAN, found), found), refused


def test_a_person_is_stood_on_the_ground_under_it_clear_of_every_solid_or_left_out(tmp_path):
    """Every spot is measured on its place's solids (its made ground too; a base with none stands nobody, and runs
    into nothing), and each body's feet judged within the slack, never in water, a seated one on its seat. Each person
    stands at its row's plan spot facing the plan's middle. A seated person (its design anchors it on a seat) sits on
    the nearest seat of its anchor's row not taken, its feet on the seat's floor under its middle, measured from its
    seat's top and clear of all but its own seat; one whose row lays no seat it sits on is named; a standing one is
    raised onto the top of its anchor under it, and one under a rise of the made ground onto it (wreck's astronaut_3,
    round 33, 2026-10-30: its plan spot at 0 lay under a 3.9 m rise, the knee's ray down found nothing and it was left
    out); one over a hollow stays. One on a raised level stands at its height (the stairwell's walkway people on its
    3 m landing, Batch 1, 2026-10-25); one outside every level stays down. One its row's words stand on stairs (up,
    down, or none) goes onto the flight nearest its spot over its height that it walks clear (the stairwell's man,
    on its 3 m landing, onto the flight up from it, not the one nearer across the floor under him; the woman, on the
    floor, onto the one from 0 to 1.5 m, its foot its low end though the plan draws it from 1.5 m, 2026-11-04), on its
    first tread the way it walks, facing its last; nobody else moves. One outside the plan's outline and off every
    level is refused by name."""
    from score.stages import people_rows
    seats = seat_place(tmp_path)
    found = toy_place(tmp_path)
    inputs = made_place(tmp_path / "made")
    bare = measure.solids(tmp_path / "made/base.usda", "camp")
    made = measure.solids(tmp_path / "made/base.usda", "camp", cast.made_ground(inputs, "camp"))
    assert set(found) == {"Ground/floor", "Objects/crate"} and bare == {}
    assert cast.made_ground(inputs, "camp") == tmp_path / "made/world/places/camp.usdc"
    assert cast.made_ground({}, "camp") is None
    worlds = {"toy": found, "bare": bare, "made": made}
    for world, spots, under, into in MEASURED:
        grounds = measure.ground_under(spots, worlds[world])
        assert [ground if want else want for ground, want in zip(grounds, under)] == under, (world, grounds)
        assert measure.run_into(spots, worlds[world]) == into, world
    for body, finding, whole in OFF_GROUND:
        judged = cast.off_ground(body)
        assert (judged == finding) if whole else (finding in judged), (body, judged)
    assert measure.seat_top(seats["Objects/stool_1_1"]) == ([3.2, 0.0, 3.2], 0.45)
    assert measure.seat_top(seats["Objects/crate_1"]) is None  # its top 1 m up: no seat
    doings = people_rows.doing_of(SITTER), people_rows.doing_of(dict(SITTER, anchor="on:floor"))
    assert doings == ("seated", "sitting"), doings
    assert "spots" not in DESIGN["places"]["camp"] and cast.planned(DESIGN, "wreck", PLAN) == DESIGN
    height = writer.ground_under(inputs, "camp")
    for name, over, man_on, woman_on in STAIR_WORLDS:
        solids = dict(seats, **{solid: trimesh.creation.box(extents=size, transform=trimesh.transformations
                                                             .translation_matrix(middle)).triangles
                                for solid, size, middle in over})
        record, refused = stood_cast(solids, height)
        people = {person["name"]: person for person in record["people"]}
        for person, (flight, at, last), way in ((people["man"], man_on, "up"), (people["woman"], woman_on, "down")):
            walk = person["stairs"]
            assert (walk["way"], walk["flight"], person["at"], walk["to"], person["facing_to"]) == (
                way, flight, at, last, last), (name, person)
            assert (walk["rise"], walk["run"]) == (0.5, 0.6667), (name, walk)  # each flight 1.5 m up 2 m in 3
        assert cast.climbers_of(record) == {"man", "woman"}, name
        assert list(refused) == ["off"], (name, refused)
    assert cast.short_of({"left_out": [], "refused": refused, "crowd": None}) == [f"off refused: {refused['off']}"]
    record, _ = stood_cast(seats, height)
    people = {person["name"]: person for person in record["people"]}
    assert {tuple(person["facing_to"]) for person in record["people"]
            if not person["stairs"]} == {(5.0, 0.0, 5.0)}  # the plan's middle
    assert (people["walkway"]["at"], people["still"]["at"], people["still"]["stairs"]) == (
        [11.0, 3.0, -4.0], [13.0, 0.0, -2.0], None), people
    # under the rise it stands on it; over the hollow it stays, for spread.grounded to lower
    assert (people["hill"]["at"], people["dip"]["at"]) == ([-2.0, 2.0, 10.0], [2.0, 0.0, 10.0]), people
    assert spread.grounded([[-2.0, 0.0, 10.0]], made) == [None]
    assert spread.grounded([people["hill"]["at"], people["dip"]["at"]], made) == [[-2.0, 2.0, 10.0], [2.0, -1.0, 10.0]]
    assert cast.on_made_ground(record, None) == record
    assert (people["sitter_1"]["at"], people["sitter_1"]["seat"], people["sitter_1"]["seat_on"]) == (
        [3.2, 0.0, 3.2], 0.45, "Objects/stool_1_1"), people["sitter_1"]
    assert people["sitter_2"]["seat"] is None and people["unlaid"]["seat"] is None  # the stool taken; no chair laid
    # one with no free seat stands on clear floor by its spot, named why (camp's office chairs never laid, airlock's
    # bench top 0.19 m, 2026-11-10), for the standing gate to name and members_of to nudge clear
    assert (people["unlaid"]["doing"], people["sitter_2"]["doing"]) == ("standing", "standing")
    assert "chair lays no piece" in people["unlaid"]["unseated"] and "taken" in people["sitter_2"]["unseated"]
    low = cast.on_support({"people": [dict(people["climber"], doing="seated", anchor="on:crate")]}, seats)["people"][0]
    assert "none of crate's 1 pieces holds a seat" in low["unseated"], low
    assert {"unlaid", "sitter_2"} <= cast.members_of(record) and "sitter_1" not in cast.members_of(record)
    (tmp_path / "cast.json").write_text(json.dumps({"characters": [people["unlaid"], people["sitter_1"]]}))
    (tmp_path / "measures.json").write_text(json.dumps({"bodies": [
        {"name": "unlaid", "gap": 0.0, "on": "Ground/floor", "water": False}]}))
    standing = cast.judge_standing(tmp_path, {}, {})
    assert standing.answer == checks.PASS and standing.findings == (f"unlaid: {people['unlaid']['unseated']}",)
    assert people["climber"]["at"] == [0.0, 0.0, -3.0]  # off the crate
    over = cast.on_support({"people": [dict(people["climber"], at=[0.5, 0.0, 0.5])]}, seats)["people"][0]
    assert over["at"] == [0.5, 1.0, 0.5]
    high = cast.on_support({"people": [dict(people["climber"], at=[0.5, 2.0, 0.5])]}, seats)["people"][0]
    assert high["at"] == [0.5, 2.0, 0.5]  # never lowered
    # a sitter whose body at its seat's middle runs into a thing over it (quarters' laptop on the bunk over its
    # sitter) sits at the nearest spot along its seat clear of it; one clear at the middle keeps it; one with no clear
    # spot keeps the middle, for the clear gate to name
    top = measure.top_of("seated")
    bench = measure.seat_spots(seats["Objects/bench_1_1"])
    assert bench[0] == ([-2.7, 0.0, 1.0], 0.45) and len(bench) == 13, bench  # the middle, then 0.125 m along it
    assert measure.run_into([[-2.7, 0.45, 1.0]], seats, [top], ["Objects/bench_1_1"]) == [["Objects/laptop_1"]]
    at, height = cast.seated_clear(seats, "Objects/bench_1_1")
    assert height == 0.45 and at[0] == -2.7 and abs(at[2] - 1.0) == 0.5, at  # the nearest clear: 0.2 + 0.25 off
    assert measure.run_into([[at[0], height, at[2]]], seats, [top], ["Objects/bench_1_1"]) == [[]]
    assert cast.seated_clear(seats, "Objects/stool_1_1") == ([3.2, 0.0, 3.2], 0.45)
    plank = trimesh.creation.box(extents=[0.6, 0.05, 2.0], transform=trimesh.transformations.translation_matrix(
        [-2.7, 1.2, 1.0])).triangles
    assert cast.seated_clear(dict(seats, **{"Objects/plank": plank}), "Objects/bench_1_1") == ([-2.7, 0.0, 1.0], 0.45)
    bunk = cast.on_support({"people": [dict(people["sitter_1"], at=[-2.7, 0.0, 1.0], anchor="on:bench_1")]}, seats)
    assert (bunk["people"][0]["at"], bunk["people"][0]["seat_on"]) == (at, "Objects/bench_1_1"), bunk
    spot = cast.seated_spot(people["sitter_1"])
    assert spot == [3.2, 0.45, 3.2] and measure.ground_under([spot], seats)[0]["gap"] == 0.0
    assert measure.run_into([spot], seats, [top], ["Objects/stool_1_1"]) == [[]]
    assert measure.run_into([spot], seats, [top]) == [["Objects/stool_1_1"]]  # its back, its own
    inside = {"name": "worker_1", "at": [0.5, 0.0, 0.5], "doing": "standing"}
    lost = {"name": "worker_2", "at": [20.0, 0.0, 20.0], "doing": "standing"}  # off the floor, 15 m from it
    placed, copies = spread.stand_every([inside, lost], {"worker_1", "worker_2"},
                                        [{"at": [0.5, 0.0, 0.5]}, {"at": [3.0, 0.0, 3.0]}], 2, found)
    assert [person["name"] for person in placed] == ["worker_1"], placed
    spot = placed[0]["at"]
    # the body's 16-sided cylinder is BODY_RADIUS to its corners, BODY_RADIUS cos(pi/16) to its flat sides
    assert spot[1] == 0.0 and off_the_crate(spot) >= 0.245, spot
    assert [copy["at"] for copy in copies] == [[3.0, 0.0, 3.0]]  # the crowd copy on the crate is not stood
    # a member whose spot the layout filled past 1.2 m round (greenhouse's planter beds edge to edge round its middle
    # astronaut, 2026-11-12) stands on the nearest clear floor out to NUDGE_FAR; none there, it is left out
    beds = dict(found, **{"Objects/beds": trimesh.creation.box(
        extents=[3.4, 0.5, 3.4], transform=trimesh.transformations.translation_matrix([0.5, 0.25, 0.5])).triangles})
    placed, _ = spread.stand_every([inside], {"worker_1"}, [], 0, beds)
    off = np.hypot(placed[0]["at"][0] - 0.5, placed[0]["at"][2] - 0.5) if placed else None
    assert placed and 1.2 < off <= spread.NUDGE_FAR and measure.run_into([placed[0]["at"]], beds) == [[]], placed
    wide = dict(found, **{"Objects/beds": trimesh.creation.box(
        extents=[6.0, 0.5, 6.0], transform=trimesh.transformations.translation_matrix([0.5, 0.25, 0.5])).triangles})
    assert spread.stand_every([inside], {"worker_1"}, [], 0, wide)[0] == []


def test_a_person_by_a_decks_edge_is_stood_where_the_ground_under_both_feet_is_level(tmp_path, monkeypatch):
    """Camp's astronaut_1 and astronaut_2_1 (round 33, 2026-10-30) stood within 0.15 m of a 5.8 cm deck's edge, their
    middles on one level and a foot over the other, and sank into it in sim-body. Nudged, each stands BODY_RADIUS
    clear of the edge; one in the deck's middle stays. Airlock's astronaut (2026-11-13) stood with a vacuum cleaner's
    low part under its toe, under its body's knee and between level_under's rays: one by a low block there is nudged
    off it, its feet's room clear of it (feet.feet_into). Wreck's astronauts stood flat-footed on its 31 degree made
    ground and sank 0.14 to 0.18 m (2026-11-13): an even slope is even (level_under) but too steep to stand on
    (feet.TILT_MOST), a gentle one is not. Camp's walker walked its clip into the kitchen counter: a walker is turned
    and moved till its whole leg stands clear (walks.walk_clear), off the floor's end, the deck's edge and the worker, and on its own level (a kerb's)."""
    stage = Usd.Stage.CreateNew(str(tmp_path / "base.usda"))
    UsdGeom.Xform.Define(stage, "/camp")
    mesh(stage, "/camp/Ground/floor", [(-5, 0, -5), (5, 0, -5), (5, 0, 5), (-5, 0, 5)], [(0, 1, 2, 3)])
    mesh(stage, "/camp/Shell/deck", [(0, 0.058, -5), (5, 0.058, -5), (5, 0.058, 5), (0, 0.058, 5)], [(0, 1, 2, 3)])
    mesh(stage, "/camp/Ground/slope", [(-5, 0, 6), (5, 0, 6), (5, 2.4, 10), (-5, 2.4, 10)], [(0, 1, 2, 3)])
    mesh(stage, "/camp/Shell/kerb", [(-4, 0.2, 2), (-3, 0.2, 2), (-3, 0.2, 3), (-4, 0.2, 3)], [(0, 1, 2, 3)])
    mesh(stage, "/camp/Ground/gentle", [(-5, 0, -6), (5, 0, -6), (5, 0.12, -10), (-5, 0.12, -10)], [(0, 1, 2, 3)])
    mesh(stage, "/camp/Objects/vacuum", [(x, y, z) for x in (-1.82, -1.78) for y in (0.0, 0.04) for z in (-0.02, 0.02)],
         [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)])
    stage.Save()
    found = measure.solids(tmp_path / "base.usda", "camp")
    by_vacuum = [-2.0, 0.0, 0.0]  # the block 0.18 to 0.22 m off its middle, under no ray and under its knee
    assert measure.level_under([by_vacuum], found) == [True] and measure.run_into([by_vacuum], found) == [[]]
    assert feet.feet_into([by_vacuum, [-3.0, 0.0, 0.0]], ["Ground/floor"] * 2, found) == [["Objects/vacuum"], []]
    assert feet.feet_into([[0.0, 1.8, 9.0]], ["Ground/slope"], found) == [[]]  # its own slope is not in the way
    with feet.feet_kept():
        stood = spread.nudged([{"name": "toe", "at": by_vacuum}], found, spread.Kept())[0]["at"]
    assert spread.grounded is feet.PLAIN  # spread's own standing back once the make ends
    assert stood[1] == 0.0 and np.hypot(stood[0] + 1.8, stood[2]) >= measure.BODY_RADIUS, stood
    assert measure.level_under([[0.1, 0.058, 0.0], [-0.1, 0.0, 0.0], [2.0, 0.058, 0.0], [0.0, 1.8, 9.0]], found) == [
        False, False, True, True]
    members = [{"name": "edge", "at": [0.1, 0.0, 0.0]}, {"name": "middle", "at": [2.0, 0.0, 1.0]}]
    placed = spread.nudged(members, found, spread.Kept())
    edge, middle = (person["at"] for person in placed)
    assert abs(edge[0]) >= measure.BODY_RADIUS and edge[1] == (0.058 if edge[0] > 0 else 0.0), edge
    assert middle == [2.0, 0.058, 1.0]
    steep, gentle = [0.0, 1.44, 8.4], [0.0, 0.06, -8.0]
    assert np.round(feet.tilt_under([steep, gentle], found), 1).tolist() == [31.0, 1.7]
    with feet.feet_kept():
        assert spread.grounded([steep, gentle], found) == [None, gentle]
    walker = {"name": "walker", "doing": "walking", "at": [-4.0, 0.0, -3.0], "turn": 0.0, "pace": 1.333, "path": None}
    worker = {"name": "worker", "doing": "standing", "at": [-2.3, 0.0, 0.0], "turn": 0.0}
    with walks.walks_kept():
        alone = spread.stand_every([walker], {"walker"}, [], 0, found)[0][0]
        beside = spread.stand_every([walker, worker], {"walker"}, [], 0, found)[0][-1]
        across = spread.stand_every([dict(walker, at=[-4.0, 0.03, -7.0])], {"walker"}, [], 0, found)[0][0]
        kerbed = spread.stand_every([dict(walker, at=[-3.5, 0.2, 2.5])], {"walker"}, [], 0, found)[0][0]
    assert spread.stand_every is walks.PLAIN
    assert (alone["at"], alone["turn"]) == ([-4.0, 0.0, -3.0], -150.0), alone  # facing -z it leaves the floor at once
    assert beside["turn"] != -150.0 and min(np.hypot(spot[0] + 2.3, spot[2]) for spot in walks.route(beside)) >= 0.5
    assert (kerbed["at"], kerbed["turn"]) == ([-3.5, 0.2, 2.5], 0.0), kerbed  # no walk on its kerb: never the floor's
    assert across["turn"] == -90.0, across  # up the gentle slope's fall line its feet would leave their start's level
    assert all(spot[1] == 0.0 and spot[0] <= -measure.BODY_RADIUS and abs(spot[2]) <= 5 - measure.BODY_RADIUS
               for spot in walks.route(beside)), beside

    # cockpit's pilot sat facing his seat's back (2026-11-14): a seated person faces away from its seat's back, one
    # on a stool keeps its turn
    def box(low, high):
        return trimesh.creation.box(bounds=[low, high]).triangles
    chairs = {"Objects/chair_back_z": np.concatenate([box((-0.25, 0.0, -0.25), (0.25, 0.45, 0.25)),
                                                      box((-0.25, 0.45, 0.2), (0.25, 1.0, 0.25))]),
              "Objects/chair_back_x": np.concatenate([box((-0.25, 0.0, -0.25), (0.25, 0.45, 0.25)),
                                                      box((0.2, 0.45, -0.25), (0.25, 1.0, 0.25))]),
              "Objects/stool": box((-0.2, 0.0, -0.2), (0.2, 0.45, 0.2))}
    sitter = {"name": "sitter", "doing": "seated", "at": [0.0, 0.0, 0.0], "seat": 0.45, "turn": 180.0}
    assert feet.facing_seats(dict(sitter, seat_on="Objects/chair_back_z"), chairs)["turn"] == pytest.approx(0.0)
    assert feet.facing_seats(dict(sitter, seat_on="Objects/chair_back_x"), chairs)["turn"] == pytest.approx(90.0)
    assert feet.facing_seats(dict(sitter, seat_on="Objects/stool", turn=33.0), chairs)["turn"] == 33.0
    record = {"people": [{"name": "sitter", "doing": "seated", "at": [0.0, 0.0, 0.0], "anchor": "on:chair_back_z"}]}
    with feet.seats_faced():
        placed = cast.on_support(record, {"Objects/chair_back_z_1": chairs["Objects/chair_back_z"]})
        monkeypatch.setattr(measure, "characters", lambda: (types.SimpleNamespace(characters_of=lambda record: [
            {"name": "sitter", "turn": 180.0}, {"name": "other", "turn": 33.0}]), None))
        singles = cast.dealt(placed, {})
    assert placed["people"][0]["seat_on"] == "Objects/chair_back_z_1"
    assert [single["turn"] for single in singles] == [pytest.approx(0.0), 33.0]  # dealt at the turn it faces
    assert (cast.on_support, cast.dealt) == (feet.SUPPORTED, feet.DEALT)  # cast's own back once the make ends
    # quarters' person_bed sat at its bunk's middle facing along it, its shins under the bunk's foot (2026-11-14): one
    # on a bed 1.04 m wide and 1.9 m long, a pillow on it ahead, sits 0.2 m in from a long edge, facing out over it, the
    # edge whose feet's room is clear (a wall along the other); one on a chair stays where it sat
    bed = {"Objects/bed": np.concatenate([box((-0.51, 0.0, -0.95), (0.53, 0.45, 0.95)),
                                          box((-0.4, 0.45, -0.5), (0.4, 0.65, -0.3))]),
           "Floor/floor": box((-3, -0.1, -3), (3, 0.0, 3))}
    walled = dict(bed, **{"Shell/wall": box((-1.2, 0.0, -1.0), (-0.9, 2.0, 1.0))})
    sat = dict(sitter, seat_on="Objects/bed", turn=0.0)
    assert [feet.edge_seated(sat, bed)[key] for key in ("at", "turn")] == [[-0.3, 0.0, 0.0], pytest.approx(90.0)]
    assert [feet.edge_seated(sat, walled)[key] for key in ("at", "turn")] == [[0.325, 0.0, 0.0], pytest.approx(-90.0)]
    assert feet.edge_seated(dict(sitter, seat_on="Objects/chair_back_z", turn=0.0), chairs)["at"] == [0.0, 0.0, 0.0]
    with feet.seats_faced():
        placed = cast.on_support({"people": [{"name": "sitter", "doing": "seated", "at": [0.0, 0.0, 0.0],
                                              "anchor": "on:bed"}]}, {"Objects/bed_1": bed["Objects/bed"],
                                                                     "Shell/wall": walled["Shell/wall"]})
    assert placed["people"][0]["at"] == pytest.approx([0.31, 0.0, 0.0], abs=0.01)  # the record's spot the edge's


CROWD = {"seed": 3, "count": None, "facing_to": [0.0, 0.0, -10.0], "turn_jitter": 0.1, "height_jitter": 0.0,
         "doing": ["standing"], "shares": [1.0], "phases": 1, "palettes": [0], "palette_shares": [1.0],
         "name": "crowd", "character": "crowd", "look": "crowd_made"}
KIT_CROWD = {"name": "crowd", "character": "kit_m_avg", "look": "kit_m_avg_coat-grey", "doing": ["idle"],
             "count": None}
# Two grounds 2 m wide, 6 m apart, on a 10 m spread.
STRIPS = dict(CROWD, spread=[-5.0, -5.0, 10.0, 10.0], grounds=[[-5.0, -5.0, 2.0, 10.0], [3.0, -5.0, 2.0, 10.0]])
ROOM = {"inside": True, "floor": [[-5.0, -5.0], [5.0, 5.0]], "floor_height": 0.0, "items": [],
        "doorways": [{"name": "door-1", "middle": [0.0, 0.0, 5.0], "inward": [0.0, 0.0, -1.0], "wide": 1.0,
                      "sill": 0.0, "head": 2.1, "to": None}],
        "standing": [{"at": [3.0, 3.0], "level": 0.0, "looks_at": None}]}
ROOM_VIEWS = [("from-door-1", 0.0, 4.0), ("spot-1", 3.0, 3.0)]
# The camp's accepted plan (2026-10-21): a spot looking at its kit's objects, no plan items.
UNAIMED = {"place": "camp", "inside": True, "floor": [[-5.0, -5.0], [5.0, 5.0]], "floor_height": 0.0, "items": [],
           "doors": [], "standing": [{"at": [1.0, 4.0], "level": 0.0, "looks_at": "SEFA'S BUNK"}]}
FAR_DOWN = 10.0  # metres down a view (its fov 80) past which a body fills under FAR_SHARE of its frame
# A crowd as its plan views it and the place stands it: (id, plan.json or None for no plan row, the crowd's row or None
# for a cast with none, the views (name, eye x, eye z) or the name the plan's refusal holds, the candidates the place
# fits (None: never stood), what the cast makes of it (its candidates, asked, spots, copies) or None for no crowd, and
# its short findings, or None with the part its one finding holds).
CROWDS = [
    ("no crowd", UNAIMED, None, "SEFA'S BUNK", None, None, [], None),
    ("unread", UNAIMED, KIT_CROWD, "SEFA'S BUNK", None, (0, None, None, 0), None, "not read from the plan yet"),
    ("no ground", UNAIMED, dict(KIT_CROWD, count=3, grounds=[]), "SEFA'S BUNK", None, (0, None, None, 0),
     ["the crowd's row makes no item on the plan, so it has no ground (kit_m_avg/coat-grey)"], None),
    ("aimed off its items", UNAIMED, STRIPS, "SEFA'S BUNK", None, None, None, None),
    ("packed on two grounds, some fit", ROOM, STRIPS, ROOM_VIEWS, 20, (30, 20, 30, 20), [], None),
    ("packed outdoors, none fit", dict(ROOM, inside=False), STRIPS, ROOM_VIEWS[1:], 0, (56, 0, 56, 0),
     ["none of the crowd's 56 spots on its ground fit (crowd/made)"], None),
    ("counted down a door's view, short", ROOM, dict(CROWD, spread=[-1.0, -25.0, 2.0, 50.0], count=40), ROOM_VIEWS,
     30, (318, 40, None, 30), ["30 of the crowd's 40 fit"], None),
    ("counted on an open square, no plan row", None, dict(CROWD, spread=[0.0, 0.0, 6.0, 6.0], count=3), [], 3,
     (143, 3, None, 3), [], None),
]


def on_its_line(view, at):
    """(how far sideways of a view's line, how far down it) a copy stands, metres over the floor."""
    eye, aim = np.asarray(view["eye"], float)[[0, 2]], np.asarray(view["aim"], float)[[0, 2]]
    forward = (aim - eye) / np.linalg.norm(aim - eye)
    towards = np.asarray(at, float)[[0, 2]] - eye
    return abs(towards[0] * forward[1] - towards[1] * forward[0]), float(towards @ forward)


def test_a_crowd_stands_on_its_grounds_apart_clear_of_its_plans_views_and_is_short_only_when_none_fit(tmp_path):
    """A crowd's candidates are its lattice's spots on its grounds only (none between two), no two nearer than two
    body widths, kept off its plan's views: one right before a view is dropped, one far down it or behind it kept. The
    views are its plan's (the plan row's output), never a hand-written record's: a room's one inside its door and one
    from its standing spot, an outdoor plan's from its standing spot only, no plan row none; a spot aimed off its
    plan's items is refused by name, never a bare StopIteration, and stops only a crowd with ground: a cast with no
    crowd, or a crowd with no ground, never reads them. SAM 3 counted: it asks that many; one mass it could not part:
    every candidate of its ground, then the copies that fit (a candidate on a stall is no copy short; none fitting
    is); no ground: nothing; a design's crowd with no ground, or not read from its plan yet, is named short."""
    eye = json.loads(PLACES.read_text())["shared"]["scale"]["eye_height"]
    for name, plan, crowd, views, fit, made, findings, part in CROWDS:
        inputs = {"places": PLACES}
        if plan is not None:
            (tmp_path / name).mkdir()
            (tmp_path / name / "plan.json").write_text(json.dumps(plan))
            inputs["plan"] = tmp_path / name
        record = {"people": [], **({"crowd": crowd} if crowd else {})}
        if isinstance(views, str):
            with pytest.raises(ValueError, match=views):
                cast.plan_views(inputs)
        else:
            assert [(view["name"], view["eye"]) for view in cast.plan_views(inputs)] == [
                (view, [x, eye, z]) for view, x, z in views], name
        if isinstance(views, str) and crowd and crowd.get("spread"):
            with pytest.raises(ValueError, match=views):
                cast.crowd_of(record, [], inputs)
            continue
        found = cast.crowd_of(record, [], inputs)
        if found is not None:
            spots = [copy["at"] for copy in found["copies"]]
            # on its grounds only, each holding some (a crowd with none stands anywhere on its spread)
            on = [[left <= at[0] <= left + wide and near <= at[2] <= near + long
                   for left, near, wide, long in crowd.get("grounds") or []] for at in spots]
            assert not crowd.get("grounds") or (all(map(any, on)) and all(map(any, zip(*on)))), (name, spots)
            nearest = min([np.hypot(a[0] - b[0], a[2] - b[2]) for number, a in enumerate(spots)
                           for b in spots[number + 1:]], default=np.inf)
            assert nearest >= 2 * measure.BODY_RADIUS, (name, nearest)
            for view in [] if isinstance(views, str) else cast.plan_views(inputs):
                assert all(spread.frame_share(view, at) < spread.FAR_SHARE for at in spots), (name, view["name"])
                down = [on_its_line(view, at)[1] for at in spots if on_its_line(view, at)[0] < 0.3]
                assert all(depth < 0 or depth > FAR_DOWN for depth in down), (name, view["name"], down)
            if fit is not None:
                found = cast.stood_crowd(found, found["copies"][:fit])
            assert (len(spots), found["asked"], found.get("spots"), len(found["copies"])) == made, (name, found)
        else:
            assert made is None, name
        short = cast.short_of({"left_out": [], "crowd": found})
        assert (short == findings) if part is None else (part in short[0] and len(short) == 1), (name, short)


BRAM = {"character": "bram", "look": "bram_work"}
KIT = {"character": "kit_m_avg", "worn": ["plain_coat_grey", "head_f1"]}
IN_BLUE = "people-dress-bram-work-in-jacket_blue"
# A look made by its own usable dress row, and none other: (id, the character, its row's fabric, its variant, the
# dress rows usable, its look, the row it is made by or None for not made).
MADE = [
    ("plain", BRAM, None, 0, ["people-dress-bram-work"], ("bram", "work"), "people-dress-bram-work"),
    ("no row usable", BRAM, None, 0, [], ("bram", "work"), None),
    ("plain for a fabric", BRAM, "jacket_blue", 0, ["people-dress-bram-work"], ("bram", "work"), None),
    ("its fabric", BRAM, "jacket_blue", 0, [IN_BLUE], ("bram", "work"), IN_BLUE),
    ("fabric for a variant", BRAM, "jacket_blue", 2, [IN_BLUE], ("bram", "work"), None),
    ("its variant", BRAM, "jacket_blue", 2, [f"{IN_BLUE}-v2"], ("bram", "work"), f"{IN_BLUE}-v2"),
    ("kit outfit", KIT, None, 0, ["people-dress-kit_m_avg-coat-grey"], ("kit_m_avg", "coat-grey"),
     "people-dress-kit_m_avg-coat-grey"),
    ("no look", {"character": "bram"}, None, 0, ["people-dress-bram-work"], None, None),
]
# A dress row's name and what it is of, both ways: (the cast's look, fabric, variant, the row or None for no look).
DRESS_ROWS = [
    ("bram/work", "jacket_blue", 2, f"{IN_BLUE}-v2"),
    ("bram/work", "jacket_blue", 0, IN_BLUE),
    ("astronaut/made", None, 0, "people-dress-astronaut-made"),
    (None, "jacket_blue", 0, None),
]
CROWD_COPIES = [{"palette": 0}, {"palette": 1}]
# The characters layer's crowd and what it names of it: (id, its stood copies, the crowd's missing, the people with
# no body of their look: bram, nev, both variants and, stood, the crowd itself).
LAID = [
    ("stood", CROWD_COPIES, "no variant of its look has an accepted body", 5),
    ("never stood", [], "no copy of the crowd stood on its ground", 4),
]


def test_a_person_or_crowd_variant_with_no_dressed_body_is_left_out_and_named_never_laid_in_a_stand_in(tmp_path):
    """A look is made only by its own usable dress row: the plain row, `-in-<surface>` for its row's fabric, `-v<n>`
    for a person's own variant, none other. The characters layer with no dress row given lays nobody: each person and
    each crowd variant named with the row it lacks, never worn by another, the crowd named for its variants or for no
    copy stood; its bodies gate fails each with no body (a crowd never stood is the counted gate's, not a body's) as a
    finding (the owner's GAP rule), and complete's people check (tools/usd/contents.py) fails each by name."""
    for name, character, surface, variant, usable, look, made in MADE:
        found = cast.look_of(character)
        assert (found, cast.made_row(found, surface, variant, dict.fromkeys(usable, "a"))) == (look, made), name
    for look, surface, variant, row in DRESS_ROWS:
        assert layer.body_row(look, surface, variant) == row, look
        assert row is None or layer.dressed_of(row) == (look.replace("/", "-"), surface, variant), row
    sys.path.insert(0, str(REPO / "tools/usd"))
    import contents
    bram = {"name": "bram", "character": "bram", "look": "bram/work", "at": [1.0, 0.0, 2.0], "turn": 90.0,
            "doing": "standing", "start": 0.0}
    design = {"places": {"hub": {"concept": "a" * 64, "rows": {"crowd": {"crowd": "crowd-made", "count": 2}}}},
              "new": {}}
    gap = {"name": "people with no body", "row": "characters-layer", "check": "bodies", "decided": "a test"}
    assert "bodies" in stages.GAP_GATES["characters-layer"]
    for name, copies, crowd_missing, bodiless in LAID:
        folder = tmp_path / name
        (folder / "cast").mkdir(parents=True)
        crowd = {"name": "crowd", "character": "crowd", "look": "crowd/made", "copies": copies}
        (folder / "cast/cast.json").write_text(json.dumps({"place": "hub", "crowd": crowd,
                                                           "characters": [bram, dict(bram, name="nev")]}))
        (folder / "rows.json").write_text(json.dumps(design))
        inputs = {"cast": folder / "cast", "design": folder / "rows.json"}
        out = folder / "out"
        out.mkdir()
        layer.make(inputs, out, 0, {})
        assert layer.layer_faults(out) == [], name
        assert not Usd.Stage.Open(str(out / layer.LAYER)).GetPrimAtPath("/hub/Characters").GetChildren(), name
        looks = json.loads((out / layer.RECORD).read_text())["looks"]
        assert crowd_missing in looks["crowd"]["missing"], (name, looks)
        assert [looks[f"crowd-v{variant}"]["missing"] for variant in (0, 1)] == [
            "no accepted body of its look (people-dress-crowd-made)",
            "no accepted body of its look (people-dress-crowd-made-v1)"], (name, looks)
        verdict = layer.judge_laid(out, inputs, None)
        assert verdict.answer == checks.PASS and verdict.measures["missing"] == 5, (name, verdict)
        assert verdict.findings[0] == "bram (bram/work): no accepted body of its look (people-dress-bram-work)"
        bodies = driven.judge_bodies(out, inputs, None)
        assert bodies.answer == checks.FAIL and bodies.measures["no body"] == bodiless, (name, bodies)
        assert bodies.findings[0] == "bram: bram/work, no accepted body of its look (people-dress-bram-work)"
        # a recorded gap of the place naming every one with no body moves the fail to complete; one naming only bram
        # keeps it
        named = [finding.partition(":")[0] for finding in bodies.findings]
        assert gaps.moved(bodies, [dict(gap, objects=named)]).answer == checks.PASS, (name, named)
        assert gaps.moved(bodies, [dict(gap, objects=["bram"])]).answer == checks.FAIL, name
        assert [fault for fault in contents.layer_faults(out) if fault.startswith("nev (bram/work)")], name


def standing(name, at, **more):
    """A person of their own character standing at `at`, facing +z."""
    return {"name": name, "character": name, "doing": "standing", "at": at, "facing_to": [0.0, 0.0, 9.0], **more}


def drawn(name, seed, at):
    """A person of KIT_GROUP standing at `at`, drawn from its kit by `seed` in its plain outfit."""
    return standing(name, at, seed=seed)


WALKER = {"name": "walker", "character": "bram", "doing": "walking", "at": [0.0, 0.0, 0.0],
          "facing_to": [4.0, 0.0, 0.0], "path": [[0.0, 0.0, 0.0], [4.0, 0.0, 0.0]]}
VARIANTS = [standing("worker_1", [0.0, 0.0, 0.0], character="worker", look="worker_made", variant=0),
            standing("worker_2", [3.0, 0.0, 0.0], character="worker", look="worker_made", variant=1)]
# A group held to two builds and one plain outfit (the square's front row), drawn by KIT_SEEDS seeds.
KIT_GROUP = {"builds": ["m_avg", "w_slim"], "plain": ["uniform_olive"]}
KIT_SEEDS = 200
# People as their record holds them and where the cast stood them: (id, the record's people, the spots they were stood
# on by name, the standing bodies that overlap, the cast check's faults).
APART = [
    ("near on one level", [standing("a", [0.0, 0.0, 0.0]), standing("b", [0.3, 0.0, 0.0]),
                           standing("c", [3.0, 0.0, 0.0]), standing("d", [3.1, 3.0, 0.0])],  # d on a landing over c
     {}, [["a", "b"]], []),
    ("dealt a spot on a walk", [WALKER, standing("worker", [2.0, 0.0, 0.0])], {}, [],
     ["walker walks 0.60 m from worker after 1.05 s (people keep 0.65 m apart)"]),
    ("stood off the walk", [WALKER, standing("worker", [2.0, 0.0, 0.0])], {"worker": [2.0, 0.0, 5.0]}, [], []),
    ("each its own variant", VARIANTS, {}, [], []),
    ("one variant twice", [dict(person, variant=0) for person in VARIANTS], {}, [],
     ["worker_1 and worker_2 are the same person (worker)"]),
    ("a kit group, one build and face, each its own hair", [drawn("k0", 0, [0.0, 0.0, 0.0]),
                                                           drawn("k2", 2, [2.0, 0.0, 0.0])], {}, [], []),
    ("a kit group, one face twice", [drawn("k0", 0, [0.0, 0.0, 0.0]), drawn("k140", 140, [2.0, 0.0, 0.0])], {}, [],
     ["k0 and k140 are the same person (kit_m_avg, hair_side_f1, head_f1)"]),
]


def test_people_stand_apart_on_their_level_judged_where_they_were_stood_and_each_their_own_person():
    """Standing bodies nearer than two widths on one level overlap (by their feet: one on a landing over another does
    not), by the body sizes measure.py copies from cast_check (so tools/characters stays off the import path, the
    overlay's rule) and cast_check judges walks by. A person dealt a spot on another's walk is judged where they were
    stood (cast_check, 9cc854cf); each person of a look its own variant (owner, 2026-10-25: "Each one looks
    different"), the same variant twice the same person; a group drawn from its kit wears only its kit's builds and
    plain outfit, two draws of one face and hair the same person."""
    cast_rules, cast_check = measure.characters()
    assert (measure.BODY_RADIUS, measure.KNEE, measure.HEAD) == (cast_check.BODY_RADIUS, cast_check.KNEE,
                                                                 cast_check.HEAD)
    mixes = [cast_rules.kit_mix(seed, KIT_GROUP) for seed in range(KIT_SEEDS)]
    assert {mix["character"] for mix in mixes} == {"kit_m_avg", "kit_w_slim"}
    assert {mix["worn"]["plain"][0] for mix in mixes} == {"plain_uniform_olive"}
    for name, people, stood, overlapping, faults in APART:
        people = [person if "seed" not in person else dict(
            person, character=mixes[person["seed"]]["character"], worn=mixes[person["seed"]]["worn"]["plain"])
            for person in people]
        singles = [dict(person, at=stood.get(person["name"], person["at"])) for person in people]
        stood_on = [{"name": person, "at": at} for person, at in stood.items()]
        assert (cast.overlaps(singles, None), cast.checked_cast({"people": people}, stood_on)) == (
            overlapping, faults), name


# --- a person driven by its sim body (driven.py) -------------------------------------------------------------------

TOY_JOINTS = ("Root", "Root/Hips", "Root/Hips/LeftLeg", "Root/Hips/LeftLeg/LeftFoot", "Root/Hips/RightLeg",
              "Root/Hips/RightLeg/RightFoot", "Root/Hips/HeadEnd")
TOY_PARENTS = np.array([-1, 0, 1, 2, 1, 4, 1])
TOY_PLACES = ((0, 0, 0), (0, 1.0, 0), (0.1, 0.9, 0), (0.1, 0.05, 0), (-0.1, 0.9, 0), (-0.1, 0.05, 0), (0, 1.7, 0))
TOY_SIZE, TOY_LIFT, TOY_FRAMES = 1.1, -0.005, 10


def moved(x=0.0, y=0.0, z=0.0, turn=0.0):
    """A 4 x 4 turned `turn` degrees about z and moved by (x, y, z)."""
    from scipy.spatial.transform import Rotation
    found = np.eye(4)
    found[:3, :3], found[:3, 3] = Rotation.from_euler("z", turn, degrees=True).as_matrix(), (x, y, z)
    return found


def chained(locals_):
    worlds = []
    for joint, local in enumerate(locals_):
        worlds.append(local if TOY_PARENTS[joint] < 0 else worlds[TOY_PARENTS[joint]] @ local)
    return worlds


def toy_rig():
    """The mean rig: TOY_JOINTS at TOY_PLACES, its standing clip TOY_FRAMES frames of the bind pose."""
    bind = np.array([moved(*place) for place in TOY_PLACES])
    rest = [bind[0]] + [np.linalg.inv(bind[TOY_PARENTS[joint]]) @ bind[joint] for joint in range(1, len(bind))]
    return {"names": np.array([path.rpartition("/")[2] for path in TOY_JOINTS]), "parents": TOY_PARENTS,
            "bind": bind, "clip_standing": np.repeat(np.array(rest)[None], TOY_FRAMES, axis=0)}


def toy_asset(folder, rig):
    """A dressed body as skel_usd writes one, TOY_SIZE times the rig, turned about up as the people's bodies are, its
    standing clip two frames longer than the sim's, its Hips lifted TOY_LIFT."""
    from pxr import Gf, Sdf, UsdSkel, Vt
    folder.mkdir(parents=True)
    path = folder / "toy.usdc"
    stage = Usd.Stage.CreateNew(str(path))
    stage.SetTimeCodesPerSecond(30)
    root = UsdSkel.Root.Define(stage, "/Character")
    stage.SetDefaultPrim(root.GetPrim())
    UsdGeom.Xform.Define(stage, "/Character/Turned").AddTransformOp().Set(Gf.Matrix4d().SetRotate(
        Gf.Rotation(Gf.Vec3d(0, 1, 0), 180)))
    UsdGeom.Scope.Define(stage, "/Character/Turned/Body")
    skeleton = UsdSkel.Skeleton.Define(stage, "/Character/Turned/Skeleton")
    skeleton.CreateJointsAttr(Vt.TokenArray(TOY_JOINTS))
    bind = [Gf.Matrix4d(moved(*(np.array(place) * TOY_SIZE)).T.tolist()) for place in TOY_PLACES]
    skeleton.CreateBindTransformsAttr(Vt.Matrix4dArray(bind))
    skeleton.CreateRestTransformsAttr(Vt.Matrix4dArray(bind))
    clip = UsdSkel.Animation.Define(stage, "/Character/Animations/standing")
    clip.CreateJointsAttr(Vt.TokenArray(TOY_JOINTS))
    clip.CreateScalesAttr(Vt.Vec3hArray([Gf.Vec3h(1, 1, 1)] * len(TOY_JOINTS)))
    local = rig["clip_standing"][0]
    places = [local[joint, :3, 3] * (1 if joint else 0) * TOY_SIZE for joint in range(len(TOY_JOINTS))]
    places[1] = places[1] + (0, TOY_LIFT, 0)
    for frame in range(TOY_FRAMES + 2):
        clip.CreateRotationsAttr().Set(Vt.QuatfArray([Gf.Quatf(1, 0, 0, 0)] * len(TOY_JOINTS)), frame)
        clip.CreateTranslationsAttr().Set(Vt.Vec3fArray([Gf.Vec3f(*map(float, place)) for place in places]), frame)
    root.GetPrim().SetCustomDataByKey("score:clip_seconds", {"standing": (TOY_FRAMES + 1) / 30})
    UsdSkel.BindingAPI.Apply(skeleton.GetPrim()).CreateAnimationSourceRel().SetTargets(
        [Sdf.Path("/Character/Animations/standing")])
    stage.GetRootLayer().Save()
    return path


def toy_sim(folder, rig):
    """A sim-body output for bram, built at his own size (TOY_SIZE times the rig, as sim_body.person_rig builds it):
    its hips walked 0.3 m along x and let down 2 cm, its left leg swung 20 degrees, each segment's pose a frame
    (measures/bram.json) and keyed on its guide prim (layers/sim_bodies.usda)."""
    from pxr import Gf, Sdf
    from scipy.spatial.transform import Rotation
    segments = ["Hips", "LeftLeg", "LeftFoot", "RightLeg", "RightFoot"]
    frames = []
    for frame in range(TOY_FRAMES):
        local = [np.array(matrix) for matrix in rig["clip_standing"][frame]]
        for matrix in local:
            matrix[:3, 3] *= TOY_SIZE
        local[1] = moved(0.3 * frame / TOY_FRAMES, -0.02) @ local[1]
        local[2] = local[2] @ moved(turn=20.0)
        worlds = dict(zip([path.rpartition("/")[2] for path in TOY_JOINTS], chained(local)))
        frames.append({"poses": [[*worlds[name][:3, 3], *Rotation.from_matrix(worlds[name][:3, :3]).as_quat()]
                                 for name in segments], "worlds": worlds})
    (folder / "measures").mkdir(parents=True)
    (folder / "measures/bram.json").write_text(json.dumps([{"poses": frame["poses"]} for frame in frames]))
    (folder / "sim_bodies.json").write_text(json.dumps({"bodies": {"bram": {
        "segments": {name: 1.0 for name in segments}, "size": {"of the rig": TOY_SIZE}}}}))
    (folder / "layers").mkdir()
    stage = Usd.Stage.CreateNew(str(folder / "layers/sim_bodies.usda"))
    for name in segments:
        op = UsdGeom.Xform.Define(stage, f"/hub/Characters/bram/SimBody/{name}").AddTransformOp()
        for frame, entry in enumerate(frames):
            op.Set(Gf.Matrix4d(entry["worlds"][name].T.tolist()), frame)
    stage.GetRootLayer().Save()
    return Sdf


def laid_driven(tmp_path, people):
    """The characters layer's people laid and driven as driven.make does, on the toy body, rig and sim body."""
    from pxr import Sdf
    rig = toy_rig()
    out = tmp_path / "out"
    asset = toy_asset(out / layer.ASSETS, rig)
    np.savez(tmp_path / "rig.npz", **rig)
    toy_sim(tmp_path / "sim", rig)
    inputs = {driven.SIM_ROW: tmp_path / "sim", driven.CLIPS_ROW: tmp_path}
    (out / "layers").mkdir()
    stage = Usd.Stage.Open(Sdf.Layer.CreateNew(str(out / layer.LAYER)))
    sim = driven.sim_of(inputs, out)
    looks = {}
    for single in people:
        layer.lay_person(stage, "/hub/Characters", single, asset)
        looks[single["name"]] = {"look": single["look"]}
    driven.drive_people(stage, out / layer.LAYER, "hub", people, looks, sim)
    stage.GetRootLayer().Save()
    (out / layer.RECORD).write_text(json.dumps({"place": "hub", "looks": looks}))
    return out, Usd.Stage.Open(str(out / layer.LAYER))


TOY_PERSON = {"name": "bram", "character": "bram", "look": "bram/work", "at": [1.0, 0.0, 2.0], "turn": 90.0,
              "doing": "standing", "start": 0.2}


def test_a_person_moves_by_its_sim_body_its_feet_on_its_sim_bodys_and_one_without_keeps_its_clip(tmp_path):
    """Bram's sim body walked his hips 0.3 m and swung his left leg: his skeleton plays it (his feet within FEET_WITHIN
    of the sim body's, which stands beside him in his skeleton's frame, both from his clip's start), the joints with
    no segment and the frames after the sim's keep the clip's; nev has no sim body and keeps his clip, named. The same
    layer with bram's skeleton turned back to its clip's hips while his sim body walked off fails `on its sim body`
    by name."""
    out, stage = laid_driven(tmp_path, [TOY_PERSON, dict(TOY_PERSON, name="nev", character="nev")])
    record = json.loads((out / layer.RECORD).read_text())["looks"]
    assert record["bram"]["motion"]["by"] == "its sim body"
    assert sorted(record["bram"]["motion"]["clip keeps"]) == ["HeadEnd", "Root"]
    assert record["nev"]["motion"] == {"by": "its clip", "why": "its sim body was not run (sim_bodies.json's "
                                                                "`left out` says why)"}
    assert stage.GetPrimAtPath("/hub/Characters/nev").GetCustomDataByKey("score:motion").startswith("its clip")
    off = driven.feet_off(out / layer.LAYER, "hub", "bram", record["bram"]["motion"])
    # the sim body is bram's own size (1.1 times the rig): his feet stand on its (3.9 cm off at the rig's size)
    assert off == pytest.approx(0.0, abs=0.002)
    from pxr import UsdSkel
    played = UsdSkel.Animation(stage.GetPrimAtPath("/hub/Characters/bram/SimDriven"))
    start = record["bram"]["motion"]["start"]
    assert played.GetTranslationsAttr().Get(TOY_FRAMES - 1 - start)[1][0] == pytest.approx(0.27, abs=1e-4)
    assert played.GetTranslationsAttr().Get(TOY_FRAMES + 1 - start)[1][0] == pytest.approx(0.0)  # the clip's again
    verdict = driven.judge_on_its_sim_body(out, {}, None)
    assert verdict.answer == checks.PASS and verdict.measures["driven"] == 1, verdict
    assert verdict.findings == ("nev keeps its clip: its sim body was not run (sim_bodies.json's `left out` says why)",)
    stage.GetPrimAtPath("/hub/Characters/bram/Turned/Skeleton").GetRelationship("skel:animationSource").SetTargets(
        ["/hub/Characters/bram/Animations/standing"])
    stage.GetRootLayer().Save()
    verdict = driven.judge_on_its_sim_body(out, {}, None)
    assert verdict.answer == checks.FAIL and verdict.measures["worst foot m"] > 0.3, verdict
    assert verdict.findings[0].startswith("bram: a foot"), verdict
