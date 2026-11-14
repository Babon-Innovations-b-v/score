"""The cast stands every person and crowd copy on something solid, clear of every solid and of each other, or leaves
them out by name; a look with no usable dressed body fails the characters layer by name, never a stand-in
(cast/__init__.py, measure.py, spread.py, layer.py); a person whose place's sim body ran plays its simulated motion,
its feet on its sim body's, and one without keeps its clip, named (driven.py).

Measured on a toy place made here (a 10 m floor and a 1 m crate), small crowds and plans written here, and the
characters layer driven.make makes with one toy dressed body (skel_usd's conversion of its glb stood in by it) and one
toy sim body. The hub's round-three seed and the motion work's built body the
old tests needed went with the old disk (2026-10-19): those tests only ever skipped, so their rules are held here on
geometry of the test's own.

Breaks that turn it red (each applied once and seen red, then reverted); the stood casts are the cast rows the test
stands and judges, the laid hub the hub's rows among them, every cast then laid in the hub's characters layer:
- `spread.grounded`: `or next(clashes)` dropped  -> the stood casts (the member stays in the crate).
- `spread.grounded`: `or not next(level)` dropped  -> the stood casts (the member stays over the edge).
- `feet.grounded`: `or next(low)` dropped  -> the stood casts (the member by the low block stays over it).
- `feet.feet_into`: `- {on}` dropped  -> the stood casts (the slope's own ground in its feet's way).
- `feet.feet_kept`: `spread.grounded = grounded` dropped  -> the stood casts (the member stays over the block).
- `feet.grounded`: `or next(steep)` dropped  -> the stood casts (the person on the 31 degree slope stands).
- `feet.tilt_under`: `np.hypot(rise[:, 0], rise[:, 1])` read as `rise[:, 0]` (the fall along x only)  -> the stood
  casts (the slope rising along z reads level).
- `walks.walk_clear`: `abs(spot[1] - at[1]) <= measure.FOOT_STEP and` dropped, or read off its leg's start
  (`feet[0][1]`, starts kept at any level)  -> the stood casts (the walker on the 1 m kerb walks the floor beside
  it).
- `walks.walk_clear`: `and not kept.overlaps(spot)` dropped  -> the stood casts (the walker walks through the
  worker).
- `walks.stand_every`: the walker's `walk_clear` dropped  -> the stood casts (it walks off the floor's end).
- `walks.walks_kept`: `spread.stand_every = stand_every` dropped  -> the stood casts (the walker stays facing
  -z).
- `feet.facing_seats`: `turn=` left as it came  -> the stood casts (the sitter faces its chair's back).
- `feet.facing_seats`: `math.atan2(away[0], away[1])` read as `math.atan2(away[1], away[0])`  -> the stood casts.
- `feet.seats_faced`: `cast.on_support, cast.dealt = supported, dealt` made `pass`  -> the stood casts (the
  sitter dealt at its design's turn, facing its chair's back).
- `feet.seats_faced`'s dealt: `dict(single, turn=...)` left as `single`  -> the stood casts (the same).
- `feet.seat_depth`: `hits[:, 1] >= top - SEAT_BAND` read as `np.abs(hits[:, 1] - top) <= SEAT_BAND`  -> the stood
  casts (the bed's pillow ends it: its sitter left at its middle, as quarters' person_bed was).
- `feet.edge_seated`: its `<= DEEP` return made `return person` always  -> the stood casts (the bed's sitter left at
  its middle); `if not into` made `if into` (the walled edge taken)  -> the same; seats_faced's `people.append(turned)`
  made `people.append(person)`  -> the same (the record's spot left at the bed's middle).
- `measure.level_under`: `np.abs(row) <= FOOT_STEP` read as `<= 1.0`  -> the stood casts.
- `measure.level_under`: `- plane @ np.linalg.pinv(plane)` dropped (the gaps judged off the feet, not off a plane)
  -> the stood casts (the person on the slope is left out).
- `measure.run_into`: `sorted(names) if hit else []` read as `[]`  -> the stood casts.
- `spread.NUDGES`: the rings past 1.2 m out to NUDGE_FAR dropped  -> the stood casts (the member among the beds
  left out).
- `cast.seated_clear`: `if not into` read as `if True`  -> the stood casts (the bench's sitter stays under the
  laptop).
- `measure.seat_spots`: the `- BODY_RADIUS` dropped (spots to the seat's very ends)  -> the stood casts (85 spots
  across the bench, not 13 along it).
- `cast.overlaps`: `< measure.KNEE` read as `< 100`  -> the stood casts (bodies on two levels overlap).
- `cast.off_ground`: `> STAND_SLACK` read as `> 1.0`  -> the stood casts (a body 0.10 m off judged standing).
- `cast.short_of`: the packed `not crowd["copies"]` branch dropped  -> the stood casts (the packed
  crowd none of whose spots fit).
- `driven.bodiless`: `.startswith(NO_BODY)` read as `False` (a person with no body passes)  -> the laid hub.
- `cast.made_row`: `row if row in inputs else None` read as `row`  -> the laid hub (a look with no dress row made).
- `cast.short_of`: its left-out line, or its refused lines, dropped  -> the stood casts (the camp's still and walkway
  left out, or its `off` refused, unnamed).
- `spread.on_ground`:`not grounds or` read as `True or`  -> the stood casts (spots between the two grounds).
- `spread.far_enough`: `< FAR_SHARE` read as `<= 1.0`  -> the stood casts (the copy before the door kept).
- `cast.plan_views`: the `unaimed` refusal dropped  -> the stood casts (the spot aimed off its items).
- `cast.on_levels`: `at[1] + min(heights)` read as `at[1]`  -> the stood casts.
- `cast.off_flight`: the spot's height left out (`at - foot` over x and z only)  -> the stood casts (the man, on his
  3 m landing, goes onto the flight under him, nearer across the floor).
- `cast.stairs_of`: `"down" if "down" in words` read as `"up"`  -> the stood casts.
- `cast.on_stairs`: `(lowest, highest) if ... == "up"` read as `(highest, lowest)`  -> the stood casts.
- `cast.off_the_plan`: `not any(...)` read as `False`  -> the stood casts (the spot off the plan stood).
- `cast.on_made_ground`: `ground > at[1]` read as `False`  -> the stood casts (the one under the rise found
  nothing under it).
- `layer.make`: `if row is None or row not in inputs:` read as `if row is None:`  -> the laid hub (it reaches for
  a body that is not there instead of naming the gap).
- `driven.size_over_sim`: `/ float(body["size"]["of the rig"])` dropped  -> the laid hub (the 1.1 body's sim
  hips raised 10% again: feet off).
- `driven.write_driven`: Hips' simulated translation not written  -> the laid hub (the clip's path kept).
- `driven.lay_sim_body`: the Turned transform not set  -> the laid hub (the sim body mirrored off the skin).
- `driven.judge_on_its_sim_body`: `> FEET_WITHIN` read as `> 1.0`  -> the laid hub (the skeleton turned back to its
  clip's hips).
- tools/characters/cast_check.py `repeated_people`: `len(names) > 1` read as `> 9`  -> the stood casts.
- tools/characters/cast.py `kit_mix`: `if not builds or name in builds` dropped, or `(kit or {}).get("plain") or`
  dropped  -> the stood casts (a kit group wears a build or outfit off its kit).
- tools/characters/cast.py `look_of`: the head and hair parts left out  -> the stood casts (two kit draws of
  one build in other hair the same person).
- `measure.KNEE` changed off cast_check's  -> the stood casts (the copied body sizes disagree).
- `measure.seat_top`: `SEAT_LOW <=` dropped (the crate's floor face a seat)  -> the stood casts (the second
  seated person seated on the crate).
- `cast.on_support`: `taken.add(name)` dropped  -> the stood casts (two people on one stool).
- `cast.on_support`: a seated person's `at=at` dropped  -> the stood casts (seated on the floor at its spot).
- `cast.on_support`: `max(tops) > person["at"][1]` read as `True`  -> the stood casts (one over it lowered).
- `measure.run_into`: `- {seat}` dropped  -> the stood casts (the seated body runs into its own stool's back).
- `cast.off_ground`: the no-seat branch dropped  -> the stood casts (a seated one with no seat stands).
- `people_rows.doing_of`: `"seated" if seat_of(row) else` dropped  -> the stood casts (a stool's sitter sits on
  the ground); `people_rows.cast_record`: `"anchor"` dropped  -> the stood casts (nobody supported).
- `cast.unseated`: `doing="standing"` dropped  -> the stood casts (one with no seat stays seated, off members).
- `cast.judge_standing`: the unseated findings dropped  -> the stood casts (stood for want of a seat unnamed).
- `cast.on_stairs`: `runs[flight["name"]] != (0, ...)` dropped from the flight's order  -> the stood casts (the man
  under the deck).
- `cast.on_stairs`: `runs[flight["name"]] or` dropped (the whole flight walked, its clear run unread)  -> the stood
  casts (the woman on the tread under the slab).
- `stages.GAP_GATES`: `"characters-layer": ("bodies",)` dropped, or `driven.judge_bodies`'s finding not starting
  "<name>: "  -> the laid hub (a gap naming every one with no body no longer moves the fail).
- `cast.planned`: `"spots": spots` dropped (the plan's spots not handed to the cast record)  -> the stood casts
  (the climber at the plan's middle, off its spot (0, 0, -3)).
"""
import contextlib
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


def off_box(spot, box):
    """How far a spot stands sideways from a footprint (its lowest x and z, then its highest), metres."""
    low_x, low_z, high_x, high_z = box
    dx = max(low_x - spot[0], 0.0, spot[0] - high_x)
    dz = max(low_z - spot[2], 0.0, spot[2] - high_z)
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
# Where a body's spot is measured: (world, its spots, the ground under each, the solids each runs into, whether the
# ground under its footprint is level). `bare` is a base with no solid (every body stands on nothing, for the standing
# gate to name, never failing the make); `made` the same base measured with its made ground; `edge` edge_place's. A
# ground of None is not read (the body inside the crate), nor a column of None.
MEASURED = [
    ("toy", [[0.5, 0.0, 0.5], [3.0, 0.0, 3.0]], [None, FLOOR], [["Objects/crate"], []], None),
    ("bare", [[0.0, 0.0, 0.0], [1.0, 0.0, 1.0]], [NOTHING, NOTHING], [[], []], None),
    ("made", [[-2.0, 2.0, 10.0]], [{"gap": 0.0, "on": "Ground/rise", "water": False}], [[]], None),
    ("edge", [[-2.0, 0.0, 0.0]], None, [[]], [True]),  # by the vacuum's low block: level, its body clear
    # a foot over the deck's edge from above and from below it, the deck's middle, the steep slope's even ground
    ("edge", [[0.1, 0.058, 0.0], [-0.1, 0.0, 0.0], [2.0, 0.058, 0.0], [0.0, 1.8, 9.0]], None, None,
     [False, False, True, True]),
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


def block(low, high):
    """The triangles of a box from corner `low` to corner `high`."""
    return trimesh.creation.box(bounds=[low, high]).triangles


def edge_place(folder):
    """edges.usda of place `camp`: the toy floor, a 5.8 cm deck over x 0 to 5, a 31 degree slope over z 6 to 10, a
    0.2 m kerb over x -4 to -3, z 2 to 3, a gentle 1.7 degree slope over z -6 to -10 and a vacuum cleaner's 4 cm low
    part 0.18 to 0.22 m off BY_VACUUM."""
    stage = Usd.Stage.CreateNew(str(folder / "edges.usda"))
    UsdGeom.Xform.Define(stage, "/camp")
    mesh(stage, "/camp/Ground/floor", [(-5, 0, -5), (5, 0, -5), (5, 0, 5), (-5, 0, 5)], [(0, 1, 2, 3)])
    mesh(stage, "/camp/Shell/deck", [(0, 0.058, -5), (5, 0.058, -5), (5, 0.058, 5), (0, 0.058, 5)], [(0, 1, 2, 3)])
    mesh(stage, "/camp/Ground/slope", [(-5, 0, 6), (5, 0, 6), (5, 2.4, 10), (-5, 2.4, 10)], [(0, 1, 2, 3)])
    mesh(stage, "/camp/Shell/kerb", [(-4, 0.2, 2), (-3, 0.2, 2), (-3, 0.2, 3), (-4, 0.2, 3)], [(0, 1, 2, 3)])
    mesh(stage, "/camp/Ground/gentle", [(-5, 0, -6), (5, 0, -6), (5, 0.12, -10), (-5, 0.12, -10)], [(0, 1, 2, 3)])
    mesh(stage, "/camp/Objects/vacuum", [(x, y, z) for x in (-1.82, -1.78) for y in (0.0, 0.04) for z in (-0.02, 0.02)],
         [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)])
    stage.Save()
    return measure.solids(folder / "edges.usda", "camp")


BY_VACUUM = [-2.0, 0.0, 0.0]  # the vacuum's block 0.18 to 0.22 m off its middle, under no ray and under its knee
STEEP, GENTLE = [0.0, 1.44, 8.4], [0.0, 0.06, -8.0]  # on the 31 degree slope, on the gentle one
# What ground a person's footprint finds round each spot: (spot, the solid it stands on, the solids its feet's room
# runs into, the slope under it in degrees or None for not read, where feet.grounded stands it or "kept" for the spot).
FOOTING = [
    (BY_VACUUM, "Ground/floor", ["Objects/vacuum"], None, None),  # the low block under its toe: in its feet's way
    ([-3.0, 0.0, 0.0], "Ground/floor", [], None, None),
    ([0.0, 1.8, 9.0], "Ground/slope", [], None, None),  # its own slope is not in the way
    (STEEP, "Ground/slope", [], 31.0, None),  # even, but too steep to stand on (feet.TILT_MOST)
    (GENTLE, "Ground/gentle", [], 1.7, "kept"),
]
# Walker rows, each stood alone on the edge world: (id, its spot, its spot after or None for not read, its turn after).
WALKS = [
    ("facing -z it leaves the floor at once", [-4.0, 0.0, -3.0], [-4.0, 0.0, -3.0], -150.0),
    ("up the gentle slope's fall line its feet would leave their start's level", [-4.0, 0.03, -7.0], None, -90.0),
    ("no walk on its kerb: never the floor's", [-3.5, 0.2, 2.5], [-3.5, 0.2, 2.5], 0.0),
]
CHAIRS = {"Objects/chair_back_z": np.concatenate([block((-0.25, 0.0, -0.25), (0.25, 0.45, 0.25)),
                                                  block((-0.25, 0.45, 0.2), (0.25, 1.0, 0.25))]),
          "Objects/chair_back_x": np.concatenate([block((-0.25, 0.0, -0.25), (0.25, 0.45, 0.25)),
                                                  block((0.2, 0.45, -0.25), (0.25, 1.0, 0.25))]),
          "Objects/stool": block((-0.2, 0.0, -0.2), (0.2, 0.45, 0.2))}
# A bed 1.04 m wide and 1.9 m long, a pillow on it ahead, on a floor; walled, a wall along its -x edge.
BED = {"Objects/bed": np.concatenate([block((-0.51, 0.0, -0.95), (0.53, 0.45, 0.95)),
                                      block((-0.4, 0.45, -0.5), (0.4, 0.65, -0.3))]),
       "Floor/floor": block((-3, -0.1, -3), (3, 0.0, 3))}
WALLED = dict(BED, **{"Shell/wall": block((-1.2, 0.0, -1.0), (-0.9, 2.0, 1.0))})
# How a sitter at the origin, turned 180 or its own turn, is faced and seated on its seat: (id, the solids, its seat,
# its turn, the turn feet.facing_seats gives or None for not read, where and at what turn feet.edge_seated seats it,
# None for the turn not read).
SEATED = [
    ("a chair backed along +z: faces away from its back", CHAIRS, "Objects/chair_back_z", 180.0, 0.0,
     [0.0, 0.0, 0.0], None),
    ("a chair backed along +x", CHAIRS, "Objects/chair_back_x", 180.0, 90.0, None, None),
    ("a stool: keeps its turn", CHAIRS, "Objects/stool", 33.0, 33.0, None, None),
    ("a bed: 0.2 m in from a long edge, facing out over it", BED, "Objects/bed", 0.0, None, [-0.3, 0.0, 0.0], 90.0),
    ("a walled bed: the edge whose feet's room is clear", WALLED, "Objects/bed", 0.0, None, [0.325, 0.0, 0.0], -90.0),
]


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
# A cast as its plan views it and its place stands it, judged as `measured` and `counted` judge it: (id, plan.json or
# None for no plan row, the crowd's row or None for a cast with none, the record's people, the spots they were stood on
# by name, the views (name, eye x, eye z) or the name the plan's refusal holds, the candidates the place fits (None:
# never stood), what the cast makes of its crowd (its candidates, asked, spots, copies) or None for no crowd, the
# standing bodies that overlap, the cast check's faults, and its short findings, or None with the part its one finding
# holds), then, laid, (its looks named missing, those of them with no body). Each row has no member left out and none
# refused; the camp stood in the test is the row that has.
CASTS = [
    ("no crowd", UNAIMED, None, [], {}, "SEFA'S BUNK", None, None, [], [], [], None, (0, 0)),
    ("unread", UNAIMED, KIT_CROWD, [], {}, "SEFA'S BUNK", None, (0, None, None, 0), [], [], None,
     "not read from the plan yet", (3, 2)),
    ("no ground", UNAIMED, dict(KIT_CROWD, count=3, grounds=[]), [], {}, "SEFA'S BUNK", None, (0, None, None, 0), [],
     [], ["the crowd's row makes no item on the plan, so it has no ground (kit_m_avg/coat-grey)"], None, (3, 2)),
    ("aimed off its items", UNAIMED, STRIPS, [], {}, "SEFA'S BUNK", None, None, None, None, None, None, (0, 0)),
    ("packed on two grounds, some fit", ROOM, STRIPS, [], {}, ROOM_VIEWS, 20, (30, 20, 30, 20), [], [], [], None,
     (3, 3)),
    ("packed outdoors, none fit", dict(ROOM, inside=False), STRIPS, [], {}, ROOM_VIEWS[1:], 0, (56, 0, 56, 0), [], [],
     ["none of the crowd's 56 spots on its ground fit (crowd/made)"], None, (3, 2)),
    ("counted down a door's view, short", ROOM, dict(CROWD, spread=[-1.0, -25.0, 2.0, 50.0], count=40), [], {},
     ROOM_VIEWS, 30, (318, 40, None, 30), [], [], ["30 of the crowd's 40 fit"], None, (3, 3)),
    ("counted on an open square, no plan row", None, dict(CROWD, spread=[0.0, 0.0, 6.0, 6.0], count=3), [], {}, [], 3,
     (143, 3, None, 3), [], [], [], None, (3, 3)),
    ("near on one level", None, None, [standing("a", [0.0, 0.0, 0.0]), standing("b", [0.3, 0.0, 0.0]),
                                       standing("c", [3.0, 0.0, 0.0]), standing("d", [3.1, 3.0, 0.0])],  # d on a
     {}, [], None, None, [["a", "b"]], [], [], None, (4, 4)),                                           # landing
    ("dealt a spot on a walk", None, None, [WALKER, standing("worker", [2.0, 0.0, 0.0])], {}, [], None, None, [],
     ["walker walks 0.60 m from worker after 1.05 s (people keep 0.65 m apart)"], [], None, (2, 2)),
    ("stood off the walk", None, None, [WALKER, standing("worker", [2.0, 0.0, 0.0])], {"worker": [2.0, 0.0, 5.0]}, [],
     None, None, [], [], [], None, (2, 2)),
    ("each its own variant", None, None, VARIANTS, {}, [], None, None, [], [], [], None, (2, 2)),
    ("one variant twice", None, None, [dict(person, variant=0) for person in VARIANTS], {}, [], None, None, [],
     ["worker_1 and worker_2 are the same person (worker)"], [], None, (2, 2)),
    ("a kit group, one build and face, each its own hair", None, None,
     [drawn("k0", 0, [0.0, 0.0, 0.0]), drawn("k2", 2, [2.0, 0.0, 0.0])], {}, [], None, None, [], [], [], None, (2, 2)),
    ("a kit group, one face twice", None, None, [drawn("k0", 0, [0.0, 0.0, 0.0]), drawn("k140", 140, [2.0, 0.0, 0.0])],
     {}, [], None, None, [], ["k0 and k140 are the same person (kit_m_avg, hair_side_f1, head_f1)"], [], None, (2, 2)),
]


def on_its_line(view, at):
    """(how far sideways of a view's line, how far down it) a copy stands, metres over the floor."""
    eye, aim = np.asarray(view["eye"], float)[[0, 2]], np.asarray(view["aim"], float)[[0, 2]]
    forward = (aim - eye) / np.linalg.norm(aim - eye)
    towards = np.asarray(at, float)[[0, 2]] - eye
    return abs(towards[0] * forward[1] - towards[1] * forward[0]), float(towards @ forward)


def holds(found, want):
    """Whether `found` holds every field of `want` (a dict field: its own fields, recursively)."""
    return all(holds(found.get(key) or {}, value) if isinstance(value, dict) else found.get(key) == value
               for key, value in want.items())


CAST_FIELDS = ("id", "plan", "crowd", "people", "stood", "views", "fit", "made", "overlapping", "faults", "findings",
               "part", "named")
# What a cast row leaves unsaid. A row stood on a world (`world`, the test's worlds by name) has its `members` stood
# there as cast.make stands them (spread.stand_every, inside `keep`'s standing when one is named) with the crowd
# candidates `candidates`, then holds: each stood member clear of every solid on the ground under it, the `copies`
# that fit (None: not read), `placed` (by name, the fields its stood single holds), `clear` (by name: its footprint,
# lowest x and z then highest, the stood spot at least `least` and at most `most` off it, on `level` unless None) and
# `route` (by name: the footprint and level its whole walk keeps, two body widths off everyone standing); `left_out`
# (stood) and `refused` are what short_of names. Every cast, as its cast.json holds it, is then laid in the hub's
# characters layer (driven.make, the toy body for bram's look, bram's sim body): its people laid by name (`laid`), its
# looks named missing and those of them with no body (`named`), its looks' entries (`looks`: by name, the fields each
# holds) and its people driven by their sim body (`driven`: by name, the joints their clip keeps and their hips' x at
# the sim's last frame); every other laid person, and its crowd, keeps its clip.
CAST = {"plan": None, "crowd": None, "people": [], "stood": {}, "views": [], "fit": None, "made": None,
        "overlapping": [], "faults": [], "findings": [], "part": None, "world": None, "keep": None, "members": (),
        "candidates": [], "copies": None, "placed": {}, "clear": {}, "route": {}, "refused": {}, "laid": [],
        "looks": {}, "driven": {}}
KEEPERS = {None: contextlib.nullcontext, "feet": feet.feet_kept, "walks": walks.walks_kept}
WALKER_ALONE = {"name": "walker", "character": "bram", "doing": "walking", "turn": 0.0, "pace": 1.333, "path": None,
                "facing_to": [0.0, 0.0, 9.0]}
NEAR = (0.5, 0.5, 0.5, 0.5)  # worker_1's spot, the beds' middle
# Members stood on the toy, beds and edge worlds, judged as every cast of CASTS (the camp's rows are made in the test).
STOOD = [
    {"id": "a member in the crate, one 15 m off the floor", "world": "toy", "members": ("worker_1", "worker_2"),
     "people": [standing("worker_1", [0.5, 0.0, 0.5]), standing("worker_2", [20.0, 0.0, 20.0])],
     "candidates": [{"at": [0.5, 0.0, 0.5]}, {"at": [3.0, 0.0, 3.0]}], "copies": [[3.0, 0.0, 3.0]],
     # the body's 16-sided cylinder is BODY_RADIUS to its corners, BODY_RADIUS cos(pi/16) to its flat sides
     "clear": {"worker_1": ((0.0, 0.0, 1.0, 1.0), 0.245, np.inf, 0.0)},
     "findings": ["1 group members left out (worker_2)"], "named": (1, 1)},
    # the layout filled past 1.2 m round its spot (greenhouse's planter beds edge to edge round its middle astronaut,
    # 2026-11-12): it stands on the nearest clear floor out to NUDGE_FAR; none there, it is left out
    {"id": "a member among beds out to 1.7 m", "world": "beds", "members": ("worker_1",),
     "people": [standing("worker_1", [0.5, 0.0, 0.5])],
     "clear": {"worker_1": (NEAR, np.nextafter(1.2, 2.0), spread.NUDGE_FAR, None)}, "named": (1, 1)},  # > 1.2 m off
    {"id": "a member among beds out to 3 m", "world": "wide", "members": ("worker_1",),
     "people": [standing("worker_1", [0.5, 0.0, 0.5])], "findings": ["1 group members left out (worker_1)"],
     "named": (0, 0)},
    # by the deck's edge BODY_RADIUS clear of it, on the level its feet are on; in its middle it stays
    {"id": "members by the deck's edge and in its middle", "world": "edge", "members": ("edge", "middle"),
     "people": [standing("edge", [0.1, 0.0, 0.0]), standing("middle", [2.0, 0.0, 1.0])],
     "clear": {"edge": ((0.0, -np.inf, 0.0, np.inf), measure.BODY_RADIUS, np.inf, None)},
     "placed": {"middle": {"at": [2.0, 0.058, 1.0]}}, "named": (2, 2)},
    {"id": "a member with the vacuum's low block under its toe", "world": "edge", "keep": "feet", "members": ("toe",),
     "people": [standing("toe", BY_VACUUM)],
     "clear": {"toe": ((-1.8, 0.0, -1.8, 0.0), measure.BODY_RADIUS, np.inf, 0.0)}, "named": (1, 1)},
    # turned off the worker's spot, its walk on the floor, off the deck's edge and the floor's end
    {"id": "a walker beside a worker", "world": "edge", "keep": "walks", "members": ("walker",),
     "people": [dict(WALKER_ALONE, at=[-4.0, 0.0, -3.0]), standing("worker", [-2.3, 0.0, 0.0])],
     "route": {"walker": ((-np.inf, measure.BODY_RADIUS - 5, -measure.BODY_RADIUS, 5 - measure.BODY_RADIUS), 0.0)},
     "named": (2, 2)},
] + [{"id": f"a walker alone: {why}", "world": "edge", "keep": "walks", "members": ("walker",),
      "people": [dict(WALKER_ALONE, at=start)],
      "placed": {"walker": dict({"turn": turn}, **({"at": after} if after else {}))}, "named": (1, 1)}
     for why, start, after, turn in WALKS]


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
    (measures/bram.json) and keyed on its guide prim (layers/sim_bodies.usda, at 30 frames a second)."""
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
    stage.SetTimeCodesPerSecond(30)  # the sim-body row's own rate (sim_body._layer), the characters layer's too
    for name in segments:
        op = UsdGeom.Xform.Define(stage, f"/hub/Characters/bram/SimBody/{name}").AddTransformOp()
        for frame, entry in enumerate(frames):
            op.Set(Gf.Matrix4d(entry["worlds"][name].T.tolist()), frame)
    stage.GetRootLayer().Save()
    return Sdf


TOY_PERSON = {"name": "bram", "character": "bram", "look": "bram/work", "at": [1.0, 0.0, 2.0], "turn": 90.0,
              "doing": "standing", "start": 0.2}
HUB = [dict(TOY_PERSON, facing_to=[2.0, 0.0, 2.0]),
       dict(TOY_PERSON, name="nev", character="nev", at=[4.0, 0.0, 2.0], facing_to=[5.0, 0.0, 2.0]),
       dict(TOY_PERSON, name="sev", character="sev", look="sev/work", at=[-3.0, 0.0, 2.0], facing_to=[-2.0, 0.0, 2.0])]
HUB_CROWD = dict(CROWD, count=2, palettes=[0, 1], palette_shares=[0.5, 0.5])
NO_BODY_OF = "no accepted body of its look (people-dress-{})"
KEPT_CLIP = {"by": "its clip", "why": "its sim body was not run (sim_bodies.json's `left out` says why)"}
# The hub's people stood on the toy floor with its crowd, stood or with no ground, and laid: bram's and nev's dress row
# given, sev's look none, so sev and each crowd variant named missing; bram driven by his sim body, nev with none on his
# clip. `named` holds the crowd too: with no variant's body (stood) or no copy stood, the counted gate's (never).
LAID = [{"id": f"the hub, its crowd {name}", "world": "toy", "members": ("bram", "nev", "sev"), "people": HUB,
         "crowd": crowd, "made": made, "findings": findings, "laid": ["bram", "nev"], "named": (4, bodiless),
         "placed": {person["name"]: {"at": person["at"]} for person in HUB},
         "looks": {"sev": {"look": "sev/work", "missing": NO_BODY_OF.format("sev-work")},
                   "crowd": {"missing": missing, "motion": {"by": "its clip",
                                                            "why": "a crowd has no sim bodies (retiring, #56)"}},
                   "crowd-v0": {"missing": NO_BODY_OF.format("crowd-made")},
                   "crowd-v1": {"missing": NO_BODY_OF.format("crowd-made-v1")},
                   "bram": {"motion": {"by": "its sim body"}}, "nev": {"motion": KEPT_CLIP}},
         "driven": {"bram": (["HeadEnd", "Root"], 0.27)}} for name, crowd, made, findings, missing, bodiless in (
    ("stood", dict(HUB_CROWD, spread=[1.5, -4.5, 3.0, 3.0]), (39, 2, None, 2), [],
     "no variant of its look has an accepted body", 4),
    ("never stood", dict(HUB_CROWD, grounds=[]), (0, None, None, 0),
     ["the crowd's row makes no item on the plan, so it has no ground (crowd/made)"],
     "no copy of the crowd stood on its ground (the cast's counted gate: why)", 3))]


def test_people_stand_on_the_ground_clear_of_every_solid_and_each_other_or_are_named(tmp_path, monkeypatch):
    """Every spot is measured on its place's solids (its made ground too; a base with none stands nobody, and runs
    into nothing), and each body's feet judged within the slack, never in water, a seated one on its seat. The ground
    under a footprint is level when it lies within a foot's step of one plane: a deck's edge under one foot is not
    (camp's astronaut_1 and astronaut_2_1, round 33, 2026-10-30, sank into a 5.8 cm deck), an even slope is, but one
    too steep to stand on (wreck's 31 degree made ground, 2026-11-13) is not stood, a gentle one is; a low block under
    a toe and its knee, between level_under's rays, is in its feet's way (airlock's vacuum cleaner, 2026-11-13), its
    own slope never. Each person stands at its row's plan spot facing the plan's middle. A seated person (its design
    anchors it on a seat) sits on the nearest seat of its anchor's row not taken, its feet on the seat's floor under
    its middle, measured from its seat's top and clear of all but its own seat, facing away from its seat's back
    (cockpit's pilot, 2026-11-14; one on a stool keeps its turn), and on a bed 0.2 m in from the long edge whose feet's
    room is clear, facing out over it (quarters' person_bed, 2026-11-14); one whose row lays no seat it sits on is
    named; a standing one is raised onto the top of its anchor under it, and one under a rise of the made ground onto
    it (wreck's astronaut_3, round 33, 2026-10-30: its plan spot at 0 lay under a 3.9 m rise, the knee's ray down
    found nothing and it was left out); one over a hollow stays. One on a raised level stands at its height (the
    stairwell's walkway people on its 3 m landing, Batch 1, 2026-10-25); one outside every level stays down. One its
    row's words stand on stairs (up, down, or none) goes onto the flight nearest its spot over its height that it walks
    clear (the stairwell's man, on its 3 m landing, onto the flight up from it, not the one nearer across the floor
    under him; the woman, on the floor, onto the one from 0 to 1.5 m, its foot its low end though the plan draws it
    from 1.5 m, 2026-11-04), on its first tread the way it walks, facing its last; nobody else moves. One outside the
    plan's outline and off every level is refused by name. A member in a solid, by a deck's edge or by a low block is
    nudged to the nearest clear level floor (out to NUDGE_FAR), or left out; a walker is turned and moved till its whole
    leg stands clear (camp's walker walked its clip into the kitchen counter), off the floor's end, the deck's edge and
    the worker, and on its own level (a kerb's). Every cast is judged through the make's one chain where it was
    stood: a row as written, members stood on their world, the camp in each of its stair worlds as every other. A
    crowd's candidates are its lattice's spots on its grounds only (none between two), no two nearer than two body
    widths, kept off its plan's views: one right before a view is dropped, one far down it or behind it kept. The views
    are its plan's (the plan row's output), never a hand-written record's: a room's one inside its door and one from its
    standing spot, an outdoor plan's from its standing spot only, no plan row none; a spot aimed off its plan's items is
    refused by name, never a bare StopIteration, and stops only a crowd with ground: a cast with no crowd, or a crowd
    with no ground, never reads them. SAM 3 counted: it asks that many; one mass it could not part: every candidate of
    its ground, then the copies that fit (a candidate on a stall is no copy short; none fitting is); no ground: nothing;
    a design's crowd with no ground, or not read from its plan yet, is named short, as are members left out and people
    refused. Standing bodies nearer than two widths on one level overlap (by their feet: one on a landing over another
    does not), by the body sizes measure.py copies from cast_check (so tools/characters stays off the import path, the
    overlay's rule) and cast_check judges walks by. A person dealt a spot on another's walk is judged where they were
    stood (cast_check, 9cc854cf); each person of a look its own variant (owner, 2026-10-25: "Each one looks
    different"), the same variant twice the same person; a group drawn from its kit wears only its kit's builds and
    plain outfit, two draws of one face and hair the same person.

    Every cast, as its cast.json holds it, is then laid in its dressed bodies or named. A look is made only by its own
    usable dress row: the plain row, `-in-<surface>` for its row's fabric, `-v<n>` for a person's own variant, none
    other. The characters layer lays only the people whose dress row is given: each other person and each crowd variant
    named with the row it lacks, never worn by another, the crowd named for its variants or for no copy stood; its
    bodies gate fails each with no body (a crowd never stood is the counted gate's, not a body's) as a finding (the
    owner's GAP rule), and complete's people check (tools/usd/contents.py) fails each by name. Bram's sim body walked
    his hips 0.3 m and swung his left leg: his skeleton plays it (his feet within FEET_WITHIN of the sim body's, which
    stands beside him in his skeleton's frame, both from his clip's start), the joints with no segment and the frames
    after the sim's keep the clip's; nev has no sim body and keeps his clip, named, the crowd its own. The same layer
    with bram's skeleton turned back to its clip's hips while his sim body walked off fails `on its sim body` by name;
    a layer driving nobody passes it."""
    from pxr import UsdSkel
    from score.stages import people_rows
    sys.path.insert(0, str(REPO / "tools/usd"))
    import contents
    seats = seat_place(tmp_path)
    found = toy_place(tmp_path)
    edges = edge_place(tmp_path)
    inputs = made_place(tmp_path / "made")
    bare = measure.solids(tmp_path / "made/base.usda", "camp")
    made = measure.solids(tmp_path / "made/base.usda", "camp", cast.made_ground(inputs, "camp"))
    assert set(found) == {"Ground/floor", "Objects/crate"} and bare == {}
    assert cast.made_ground(inputs, "camp") == tmp_path / "made/world/places/camp.usdc"
    assert cast.made_ground({}, "camp") is None
    # beds edge to edge round the crate's middle, 3.4 m across, then 6 m (no clear floor out to NUDGE_FAR)
    worlds = {"toy": found, "bare": bare, "made": made, "edge": edges, **{
        world: dict(found, **{"Objects/beds": trimesh.creation.box(extents=[across, 0.5, across], transform=trimesh
                                                                    .transformations.translation_matrix(
                                                                        [0.5, 0.25, 0.5])).triangles})
        for world, across in (("beds", 3.4), ("wide", 6.0))}}
    cast_rules, cast_check = measure.characters()
    assert (measure.BODY_RADIUS, measure.KNEE, measure.HEAD) == (cast_check.BODY_RADIUS, cast_check.KNEE,
                                                                 cast_check.HEAD)
    mixes = [cast_rules.kit_mix(seed, KIT_GROUP) for seed in range(KIT_SEEDS)]
    assert {mix["character"] for mix in mixes} == {"kit_m_avg", "kit_w_slim"}
    assert {mix["worn"]["plain"][0] for mix in mixes} == {"plain_uniform_olive"}
    for name, character, surface, variant, usable, look, made_by in MADE:
        found_look = cast.look_of(character)
        assert (found_look, cast.made_row(found_look, surface, variant, dict.fromkeys(usable, "a"))) == (
            look, made_by), name
    for look, surface, variant, row in DRESS_ROWS:
        assert layer.body_row(look, surface, variant) == row, look
        assert row is None or layer.dressed_of(row) == (look.replace("/", "-"), surface, variant), row
    for world, spots, under, into, level in MEASURED:
        if under is not None:
            grounds = measure.ground_under(spots, worlds[world])
            assert [ground if want else want for ground, want in zip(grounds, under)] == under, (world, grounds)
        if into is not None:
            assert measure.run_into(spots, worlds[world]) == into, world
        if level is not None:
            assert measure.level_under(spots, worlds[world]) == level, (world, spots)
    spots, ons, into, tilts, kept = zip(*FOOTING)
    assert feet.feet_into(spots, ons, edges) == list(into)
    sloped = [(spot, tilt, held) for spot, tilt, held in zip(spots, tilts, kept) if tilt is not None]
    assert np.round(feet.tilt_under([spot for spot, _, _ in sloped], edges), 1).tolist() == [
        tilt for _, tilt, _ in sloped]
    with feet.feet_kept():
        assert spread.grounded([spot for spot, _, _ in sloped], edges) == [
            spot if held else None for spot, _, held in sloped]
    for body, finding, whole in OFF_GROUND:
        judged = cast.off_ground(body)
        assert (judged == finding) if whole else (finding in judged), (body, judged)
    assert measure.seat_top(seats["Objects/stool_1_1"]) == ([3.2, 0.0, 3.2], 0.45)
    assert measure.seat_top(seats["Objects/crate_1"]) is None  # its top 1 m up: no seat
    doings = people_rows.doing_of(SITTER), people_rows.doing_of(dict(SITTER, anchor="on:floor"))
    assert doings == ("seated", "sitting"), doings
    assert "spots" not in DESIGN["places"]["camp"] and cast.planned(DESIGN, "wreck", PLAN) == DESIGN
    height = writer.ground_under(inputs, "camp")
    camps, records = [], {}
    for name, over, man_on, woman_on in STAIR_WORLDS:
        solids = dict(seats, **{solid: trimesh.creation.box(extents=size, transform=trimesh.transformations
                                                             .translation_matrix(middle)).triangles
                                for solid, size, middle in over})
        records[name], refused = stood_cast(solids, height)
        assert cast.climbers_of(records[name]) == {"man", "woman"}, name
        worlds[name] = dict(solids, **made)
        # the camp as cast.make stands it, its members stood apart on its solids and made ground and judged with every
        # cast of CASTS: the two with no ground under them left out, the one off the plan refused, by name, its
        # climbers on their flights (each 1.5 m up 2 m in 3 treads)
        camps.append({"id": f"the camp, its stairs {name}", "world": name, "people": records[name]["people"],
                      "members": cast.members_of(records[name]) - cast.climbers_of(records[name]), "refused": refused,
                      "findings": ["2 group members left out (still, walkway)", f"off refused: {refused['off']}"],
                      "placed": {climber: {"at": at, "facing_to": last, "stairs": {
                          "way": way, "flight": flight, "to": last, "rise": 0.5, "run": 0.6667}}
                          for climber, way, (flight, at, last) in (("man", "up", man_on),
                                                                   ("woman", "down", woman_on))},
                      "named": (8, 8)})
    record = records["clear"]
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
    sitter = {"name": "sitter", "doing": "seated", "at": [0.0, 0.0, 0.0], "seat": 0.45}
    for name, solids, seat, turn, faced, edged, edge_turn in SEATED:
        sat = dict(sitter, seat_on=seat, turn=turn)
        if faced is not None:
            assert feet.facing_seats(sat, solids)["turn"] == pytest.approx(faced), name
        if edged is not None:
            moved_to = feet.edge_seated(sat, solids)
            assert moved_to["at"] == edged and (edge_turn is None or moved_to["turn"] == pytest.approx(edge_turn)), (
                name, moved_to)
    with feet.seats_faced():
        chaired = cast.on_support({"people": [dict(sitter, anchor="on:chair_back_z")]},
                                  {"Objects/chair_back_z_1": CHAIRS["Objects/chair_back_z"]})
        with monkeypatch.context() as patched:
            patched.setattr(measure, "characters", lambda: (types.SimpleNamespace(characters_of=lambda record: [
                {"name": "sitter", "turn": 180.0}, {"name": "other", "turn": 33.0}]), None))
            singles = cast.dealt(chaired, {})
        bedded = cast.on_support({"people": [dict(sitter, anchor="on:bed")]},
                                 {"Objects/bed_1": BED["Objects/bed"], "Shell/wall": WALLED["Shell/wall"]})
    assert chaired["people"][0]["seat_on"] == "Objects/chair_back_z_1"
    assert [single["turn"] for single in singles] == [pytest.approx(0.0), 33.0]  # dealt at the turn it faces
    assert bedded["people"][0]["at"] == pytest.approx([0.31, 0.0, 0.0], abs=0.01)  # the record's spot the edge's
    assert (cast.on_support, cast.dealt) == (feet.SUPPORTED, feet.DEALT)  # cast's own back once the make ends
    eye = json.loads(PLACES.read_text())["shared"]["scale"]["eye_height"]
    rig = toy_rig()
    np.savez(tmp_path / "rig.npz", **rig)
    toy_sim(tmp_path / "sim", rig)
    monkeypatch.setattr(layer, "asset_for", lambda row, body, out: out / layer.ASSETS / "toy.usdc")
    (tmp_path / "rows.json").write_text(json.dumps({"places": {"hub": {"concept": "a" * 64, "rows": {
        "crowd": {"crowd": "crowd-made", "count": 2}}}}, "new": {}}))
    gap = {"name": "people with no body", "row": "characters-layer", "check": "bodies", "decided": "a test"}
    assert "bodies" in stages.GAP_GATES["characters-layer"]
    for row in [dict(zip(CAST_FIELDS, row)) for row in CASTS] + STOOD + camps + LAID:
        case = dict(CAST, **row)
        name, crowd, views = case["id"], case["crowd"], case["views"]
        folder = tmp_path / name
        (folder / "cast").mkdir(parents=True)
        inputs = {"places": PLACES}
        if case["plan"] is not None:
            (folder / "plan.json").write_text(json.dumps(case["plan"]))
            inputs["plan"] = folder
        people = [person if "seed" not in person else dict(
            person, character=mixes[person["seed"]]["character"], worn=mixes[person["seed"]]["worn"]["plain"])
            for person in case["people"]]
        record = {"people": people, **({"crowd": crowd} if crowd else {})}
        singles = [dict(person, at=case["stood"].get(person["name"], person["at"])) for person in people]
        if isinstance(views, str):
            with pytest.raises(ValueError, match=views):
                cast.plan_views(inputs)
        else:
            assert [(view["name"], view["eye"]) for view in cast.plan_views(inputs)] == [
                (view, [x, eye, z]) for view, x, z in views], name
        if isinstance(views, str) and crowd and crowd.get("spread"):
            with pytest.raises(ValueError, match=views):
                cast.crowd_of(record, singles, inputs)
            continue  # a refused cast writes no cast.json, so nothing is laid
        crowded = cast.crowd_of(record, singles, inputs)
        spots = [copy["at"] for copy in crowded["copies"]] if crowded else []
        left_out = []
        if case["world"] is not None:
            # stood as cast.make stands them: the crowd's candidates, else the row's own
            world, members = worlds[case["world"]], set(case["members"])
            offered, asked = ((crowded["copies"], crowded["asked"] or 0) if crowded else
                              (case["candidates"], len(case["candidates"])))
            with KEEPERS[case["keep"]]():
                singles, copies = spread.stand_every(singles, members, offered, asked, world)
            left_out = sorted(members - {single["name"] for single in singles})
            crowded = cast.stood_crowd(crowded, copies) if crowded else None
            assert case["copies"] is None or [copy["at"] for copy in copies] == case["copies"], (name, copies)
            stood = [single["at"] for single in singles if single["name"] in members]
            assert not stood or (measure.run_into(stood, world), [ground["gap"] for ground in measure.ground_under(
                stood, world)]) == ([[] for _ in stood], [0.0] * len(stood)), (name, stood)
        by_name = {single["name"]: single for single in singles}
        for person, want in case["placed"].items():
            assert holds(by_name[person], want), (name, by_name[person])
        for person, (box, least, most, level) in case["clear"].items():
            at = by_name[person]["at"]
            assert least <= off_box(at, box) <= most and level in (None, at[1]), (name, person, at)
        for person, ((low_x, low_z, high_x, high_z), level) in case["route"].items():
            others = [single["at"] for single in singles if single["name"] != person and not single.get("path")]
            for spot in walks.route(by_name[person]):
                assert spot[1] == level and low_x <= spot[0] <= high_x and low_z <= spot[2] <= high_z, (name, spot)
                assert all(np.hypot(spot[0] - at[0], spot[2] - at[2]) >= 2 * measure.BODY_RADIUS for at in others), (
                    name, spot)
        if crowded is not None:
            # its candidates on its grounds only, each holding some (a crowd with none stands anywhere on its spread)
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
            if case["fit"] is not None:
                crowded = cast.stood_crowd(crowded, crowded["copies"][:case["fit"]])
            assert (len(spots), crowded["asked"], crowded.get("spots"), len(crowded["copies"])) == case["made"], (
                name, crowded)
        else:
            assert case["made"] is None, name
        assert (cast.overlaps(singles, crowded), cast.checked_cast(record, singles)) == (
            case["overlapping"], case["faults"]), name
        # the cast as cast.make writes it, read back by the counted gate's short_of and laid from
        (folder / "cast/cast.json").write_text(json.dumps({"place": "hub", "characters": singles, "left_out": left_out,
                                                            "refused": case["refused"], "crowd": crowded}))
        short = cast.short_of(json.loads((folder / "cast/cast.json").read_text()))
        assert (short == case["findings"]) if case["part"] is None else (
            case["part"] in short[0] and len(short) == 1), (name, short)
        laid_inputs = {"cast": folder / "cast", "design": tmp_path / "rows.json", "people-dress-bram-work": folder,
                       driven.SIM_ROW: tmp_path / "sim", driven.CLIPS_ROW: tmp_path}
        out = folder / "out"
        toy_asset(out / layer.ASSETS, rig)  # the dressed body skel_usd would convert from its row's glb
        driven.make(laid_inputs, out, 0, {})
        assert layer.layer_faults(out) == [], name
        stage = Usd.Stage.Open(str(out / layer.LAYER))
        laid = [prim.GetName() for prim in stage.GetPrimAtPath("/hub/Characters").GetChildren()]
        looks = json.loads((out / layer.RECORD).read_text())["looks"]
        assert laid == case["laid"] and all(holds(looks[person], want) for person, want in case["looks"].items()), (
            name, laid, looks)
        missing = {person: look for person, look in looks.items() if "missing" in look}
        bodiless = [person for person, look in missing.items() if driven.bodiless(look)]
        assert set(missing) | set(laid) == set(looks) and not set(missing) & set(laid), (name, looks)
        assert (len(missing), len(bodiless)) == case["named"], (name, missing)
        verdict = layer.judge_laid(out, laid_inputs, None)
        assert verdict.answer == checks.PASS and verdict.measures["missing"] == len(missing), (name, verdict)
        assert verdict.findings == tuple(f"{person} ({look['look']}): {look['missing']}"
                                         for person, look in missing.items()), (name, verdict)
        bodies = driven.judge_bodies(out, laid_inputs, None)
        assert bodies.answer == (checks.FAIL if bodiless else checks.PASS), (name, bodies)
        assert bodies.measures["no body"] == len(bodiless) and bodies.findings == tuple(
            f"{person}: {looks[person]['look']}, {looks[person]['missing']}" for person in bodiless), (name, bodies)
        # a recorded gap of the place naming every one with no body moves the fail to complete; one naming only the
        # first of two or more keeps it; complete's people check fails each by name
        assert gaps.moved(bodies, [dict(gap, objects=bodiless)]).answer == checks.PASS, (name, bodiless)
        assert gaps.moved(bodies, [dict(gap, objects=bodiless[:1])]).answer == (
            checks.FAIL if len(bodiless) > 1 else checks.PASS), name
        faults = contents.layer_faults(out)
        assert all(any(fault.startswith(f"{person} ({looks[person]['look']})") for fault in faults)
                   for person in bodiless if person in by_name), (name, faults)
        # each driven by its sim body (its own size: its feet on the sim body's), every other laid one on its clip
        kept = [person for person in laid if person not in case["driven"]] + ([crowded["name"]] if crowded else [])
        for person, (clip_keeps, hips_x) in case["driven"].items():
            motion = looks[person]["motion"]
            assert motion["by"] == "its sim body" and sorted(motion["clip keeps"]) == clip_keeps, (name, motion)
            assert driven.feet_off(out / layer.LAYER, "hub", person, motion) == pytest.approx(0.0, abs=0.002), name
            played = UsdSkel.Animation(stage.GetPrimAtPath(f"/hub/Characters/{person}/SimDriven"))
            assert played.GetTranslationsAttr().Get(TOY_FRAMES - 1 - motion["start"])[1][0] == pytest.approx(
                hips_x, abs=1e-4), name
            assert played.GetTranslationsAttr().Get(TOY_FRAMES + 1 - motion["start"])[1][0] == pytest.approx(0.0)
        for person in laid:
            assert (stage.GetPrimAtPath(f"/hub/Characters/{person}").GetCustomDataByKey("score:motion").startswith(
                "its clip")) == (person not in case["driven"]), (name, person)
        verdict = driven.judge_on_its_sim_body(out, {}, None)
        assert verdict.answer == checks.PASS and verdict.measures["driven"] == len(case["driven"]), (name, verdict)
        assert verdict.findings == tuple(f"{person} keeps its clip: {looks[person]['motion']['why']}"
                                         for person in kept), (name, verdict)
        # each driven skeleton turned back to its clip's hips while its sim body walked off fails by name
        for person in case["driven"]:
            stage.GetPrimAtPath(f"/hub/Characters/{person}/Turned/Skeleton").GetRelationship(
                "skel:animationSource").SetTargets([f"/hub/Characters/{person}/Animations/standing"])
        stage.GetRootLayer().Save()
        verdict = driven.judge_on_its_sim_body(out, {}, None)
        assert verdict.answer == (checks.FAIL if case["driven"] else checks.PASS), (name, verdict)
        assert not case["driven"] or (verdict.measures["worst foot m"] > 0.3 and verdict.findings[0].startswith(
            f"{next(iter(case['driven']))}: a foot")), (name, verdict)
    assert (spread.grounded, spread.stand_every) == (feet.PLAIN, walks.PLAIN)  # spread's own back once a make ends
