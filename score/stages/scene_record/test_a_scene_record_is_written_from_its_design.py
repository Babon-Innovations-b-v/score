"""A scene record is written from its design alone, on a plan of its own (a small shed beside a yard on a site): its
plan maps, and an item with no rows, a door that says nowhere it leads and a sealed door the layout leaves open each
fail `mapped`; a written plan with no corner takes its outline; the record holds the shell cut round its door, its
stair, a light over its lamp, the sky from the physics (on Mars its dusty day sky, inside too), the places its doors lead to and its backdrop rows are shown
from, every object at its plan item waiting on its model, a row the plan lays only against its edge past it, a far
row far off, each object carrying what holds it (its opening, its wall, its holder), an arched rib as a band, a light where a tower or a glowing row stands, and each part the scene
library's surface; its gates fail a filled door, a moved lamp and a door to no place. Every spot is worked out by hand from the plans below.

Each test names the break that turns it red (`Break: <file>: `old` -> `new``); each was applied once and seen red.

Run: PROPS_HOME=$(mktemp -d) .venv/bin/python -m pytest
    score/stages/scene_record/test_a_scene_record_is_written_from_its_design.py
"""
import hashlib
import json
import math
import pathlib
import re
import sys
import tempfile
import numpy as np
import pytest

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from score import checks  # noqa: E402
from score.stages.scene_record import far, gates, plan, writer  # noqa: E402

SHED = {"title": "SHED", "w": 8.0, "d": 6.0, "corner": 1.0, "height": "walls 3 m, dome rising 1 m",
        "doors": [["N", 4.0, 1.2, "HATCH N, 1.2 x 2.1 m"], ["S", 4.0, 2.0, "BIG DOOR, 2 x 3 m"]],
        "items": [["BENCH", 1.0, 1.0, 2.0, 0.6, None, "item"], ["DRIVE LANE", 3.0, 3.0, 2.0, 2.0, None, "zone"]],
        "people": [[4.0, 3.0]],
        "leads": {"N": {"to": "yard", "why": "a hatch onto the yard"}, "S": {"to": "outside", "why": "the big door"}},
        "rows": {"BENCH": ["bench"], "DRIVE LANE": []},
        "elements": [{"element": "a bench", "rows": ["bench"]}]}
INVENTORY = {"scene": "shed", "rows": [{"id": "bench", "name": "a bench", "anchor": "floor", "size": [2.0, 0.6, 0.9],
                                        "count": 1}],
             "room": {"layout": {"open": ["north", "south"]}}}


# The yard: 20 x 12 m, its gate on its south wall leading to the shed.
YARD = {"title": "YARD", "w": 20.0, "d": 12.0, "leads": {},
        "openings": [{"kind": "gate", "at": [10.0, 12.0], "wide": 1.2, "angle": 0.0, "sill": 0.0, "to": "shed"}]}


def made(folder, record, yard=YARD):
    """plan@shed made into `folder` from `record`, as the table hands it (its kit the plan itself: plan_as_kit)."""
    folder = pathlib.Path(folder)
    plans = folder / "plans"
    plans.mkdir()
    (plans / "yard.json").write_text(json.dumps(yard))
    (plans / "shed.json").write_text(json.dumps(record))
    (folder / "inventory.json").write_text(json.dumps(INVENTORY))
    inputs = {"plan": plans / "shed.json", "kit": plans / "shed.json", "plans": plans,
              "inventory": folder / "inventory.json"}
    out = folder / "plan"
    out.mkdir()
    plan.make(inputs, out, 0, {})
    assert plan.plan_faults(out) == []
    return out, inputs


NO_CORNER = {key: value for key, value in SHED.items() if key != "corner"}


def held_world(folder, drawn):
    """The base's plan output and its inputs, its plans `drawn` (name: plan) written into `folder`."""
    folder = pathlib.Path(folder)
    plans, out = folder / "plans", folder / "out"
    plans.mkdir(), out.mkdir()
    (out / "plan.json").write_text(json.dumps({"place": "base"}))
    (folder / "inventory.json").write_text(json.dumps({"rows": []}))
    for name, own in drawn.items():
        (plans / f"{name}.json").write_text(json.dumps(own))
    return out, {"plans": plans, "inventory": folder / "inventory.json"}


# The base (#72): the tube's plan, 2 x 4 m, its north end to the hub, its south end to the greenhouse; held turned 90
# degrees (north to east) and stretched to 6 m, its hub end leading to the lab (east, x 16) and its greenhouse end to
# the hub (west, x 10), both at y 5.
TUBE = {"w": 2.0, "d": 4.0, "shape": "tube", "openings": [{"kind": "opening", "at": [1.0, 0.0], "to": "hub"},
                                                          {"kind": "opening", "at": [1.0, 4.0], "to": "greenhouse"}]}
HUB = {"w": 10.0, "d": 10.0, "openings": [{"kind": "door", "at": [10.0, 5.0], "to": "tube#1"}]}
LAB = {"w": 4.0, "d": 4.0, "openings": [{"kind": "door", "at": [0.0, 2.0], "to": "tube#1"}]}
TUBE_1 = {"place": "tube", "instance": "tube#1", "turn": 90, "leads": {"hub": "lab", "greenhouse": "hub"},
          "x": 10.0, "y": 4.0, "w": 6.0, "d": 2.0}
BASE = {"w": 20.0, "d": 10.0, "holds": [{"place": "hub", "x": 0.0, "y": 0.0, "w": 10.0, "d": 10.0}, TUBE_1,
                                        {"place": "lab", "x": 16.0, "y": 3.0, "w": 4.0, "d": 4.0}]}
# The base turned: the tube turned 315 degrees (its run south-east) from the hub's corner door (10, 10) 4 m to the
# lab's door at its corner, its box 4.24 m square round its middle (11.41, 11.41); the hub's two doors to `tube` each
# named by its spot; the lab's door on its floor 1 m over its lower one.
TURNED_HUB = {"w": 10.0, "d": 10.0, "openings": [{"kind": "door", "at": [10.0, 10.0], "to": "tube"},
                                                 {"kind": "door", "at": [0.0, 5.0], "to": "tube"}]}
TURNED_LAB = {"w": 4.0, "d": 4.0, "levels": [{"height": 0.0}, {"height": 1.0}],
              "openings": [{"kind": "door", "at": [0.0, 0.0], "sill": 1.0, "to": "tube"}]}
SIDE = 6.0 / math.sqrt(2.0)
TURNED_TUBE = {"place": "tube", "instance": "tube#1", "turn": 315, "leads": {"greenhouse": "lab"},
               "x": 10.0 + 2.0 ** 0.5 - SIDE / 2, "y": 10.0 + 2.0 ** 0.5 - SIDE / 2, "w": SIDE, "d": SIDE}
CORNER = 10.0 + 4.0 / math.sqrt(2.0)
TURNED_BASE = {"w": 20.0, "d": 20.0, "holds": [
    {"place": "hub", "x": 0.0, "y": 0.0, "w": 10.0, "d": 10.0, "leads": {"tube@10,10": "tube#1", "tube@0,5": "outside"}},
    TURNED_TUBE, {"place": "lab", "x": CORNER, "y": CORNER, "w": 4.0, "d": 4.0, "leads": {"tube": "tube#1"}}]}
# Two holds overlapping 0.97 m, and a place held once that more doors lead to than lead back (the base's one tube).
OVERLAPPING = [{"place": "hub", "x": 0.0, "y": 0.0, "w": 10.0, "d": 10.0},
               {"place": "tube", "x": 9.0, "y": 2.0, "w": 4.0, "d": 4.0}]
TO_TUBE = {"kind": "door", "at": [0.0, 0.0], "to": "tube"}
HELD_ONCE = {"hub": (OVERLAPPING[0], {"openings": [TO_TUBE, TO_TUBE]}),
             "tube": (OVERLAPPING[1], {"openings": [{**TO_TUBE, "to": "hub"}]})}
# Two doors on one wall, each led by its own lead (the walkway's galley and quarters doors, 2026-11-05).
TWO_DOORS = {**SHED, "doors": [["E", 1.5, 0.9, "DOOR to the galley 0.9 x 2.0 m"], ["E", 4.5, 0.9, "DOOR to the yard"]],
             "leads": {"E": {"to": "sealed", "why": "shut"}, "E:4.5": {"to": "yard", "why": "the yard's door"}},
             "openings": [{"kind": "door", "at": [8.0, 4.5], "wide": 0.9, "sill": 0.0, "to": "yard"},
                          {"kind": "door", "at": [8.0, 1.5], "wide": 0.9, "sill": 0.0, "to": "sealed"}]}


# A written plan (plan_writing's schema): the shed's outline, walls, a door in its north wall to the yard beside it,
# its floor, a flat roof, a stair, a bench and a ceiling lamp; one person spot inside, one outside its walls. Its
# holder (the site) holds it and the yard.
WRITTEN = {**SHED, "outline": [[0.0, 0.0], [8.0, 0.0], [8.0, 6.0], [0.0, 6.0]],
           "walls": [{"from": [0.0, 0.0], "to": [8.0, 0.0], "thick": 0.2, "tall": 3.0},
                     {"from": [8.0, 0.0], "to": [8.0, 6.0], "thick": 0.2, "tall": 3.0},
                     {"from": [8.0, 6.0], "to": [0.0, 6.0], "thick": 0.2, "tall": 3.0},
                     {"from": [0.0, 6.0], "to": [0.0, 0.0], "thick": 0.2, "tall": 3.0}],
           "openings": [{"kind": "door", "at": [4.0, 0.0], "wide": 1.2, "angle": 0.0, "swing": "slide", "sill": 0.0,
                         "head": 2.1, "to": "yard"},
                        {"kind": "door", "at": [4.0, 6.0], "wide": 2.0, "angle": 180.0, "swing": "slide", "sill": 0.0,
                         "head": 3.0, "to": "outside"}],
           "levels": [{"name": "floor", "height": 0.0, "points": [[0.0, 0.0], [8.0, 0.0], [8.0, 6.0], [0.0, 6.0]]}],
           "roofs": [{"kind": "flat", "points": [[0.0, 0.0], [8.0, 0.0], [8.0, 6.0], [0.0, 6.0]], "eave": 3.0,
                      "top": 3.0}],
           "stairs": [{"kind": "stair", "points": [[6.0, 4.0], [7.0, 4.0], [7.0, 6.0], [6.0, 6.0]], "from": 0.0,
                       "to": 1.0, "angle": 90.0, "steps": 5}],
           "items": [*SHED["items"], ["LAMP", 3.5, 2.5, 1.0, 1.0, None, "item"]],
           "rows": {**SHED["rows"], "LAMP": ["ceiling_lamp"]},
           "shapes": {"LAMP": {"shape": "rect", "tall": 0.2, "base": 2.7}},
           "people": [[4.0, 3.0, None, None], [20.0, 3.0, None, None]], "terrain": {}}
LAMP_ROW = {"id": "ceiling_lamp", "name": "ceiling lamp", "noun": "lamp", "anchor": "ceiling", "size": [1.0, 1.0, 0.2],
            "count": 1}
# The site holds the yard at its north-west corner and the shed south of it, the shed's north door on the yard's gate
# at (10, 12); its items for both rows are their holds.
SITE = {"title": "SITE", "w": 40.0, "d": 20.0, "leads": {},
        "holds": [{"place": "shed", "row": "shed", "x": 6.0, "y": 12.0, "w": 8.0, "d": 6.0},
                  {"place": "yard", "row": "yard", "x": 0.0, "y": 0.0, "w": 20.0, "d": 12.0}],
        "items": [["SHED", 6.0, 12.0, 8.0, 6.0, None, "item"], ["YARD", 0.0, 0.0, 20.0, 12.0, None, "zone"]],
        "rows": {"SHED": ["shed"], "YARD": ["yard"]}}
# The batch's hand-in (prepare's handin.py): the bench a model of its own take, the lamp sharing the bench's take, the
# shed's floor the plan's own shell.
HANDIN = {"rows": [{"id": "bench", "route": "prop", "size": [2.0, 0.6, 0.9], "count": 1},
                   {"id": "ceiling_lamp", "route": "prop", "size": [1.0, 1.0, 0.2], "count": 1},
                   {"id": "shed_floor", "route": "plan", "part": "floor"}],
          "objects": {"bench": {"rows": ["bench", "ceiling_lamp"]}}}
# The base's site at its scene time (data/physics/setting.json): the Sun stands over its horizon then.
SKY = {"site": {"on": "moon", "latitude": 55.0, "longitude": 0.0, "height_m": 0.0}, "time": "2099-10-01T14:00:00Z"}
# The shed furnished whole: a rail run the plan draws once as a polygon counting three, 0.5 m up, and two arched
# ribs (design_shell.arched: a tube's ribs, a band of the shell) across it, each 8 x 0.2 m, at plan y 1 and 4.
RIB = {"id": "structural_ribs", "name": "arched structural ribs", "noun": "ribs", "part": "structure",
       "route": "plan", "size": [3.2, 0.2, 3.2], "count": 2}
FURNISHED = {**WRITTEN, "items": [*WRITTEN["items"], ["RAIL", 1.0, 4.0, 3.0, 1.0, None, "item"],
                                  ["RIBS 1", 0.0, 1.0, 8.0, 0.2, None, "item"],
                                  ["RIBS 2", 0.0, 4.0, 8.0, 0.2, None, "item"]],
             "rows": {**WRITTEN["rows"], "RAIL": ["rail"], "RIBS 1": ["structural_ribs"],
                      "RIBS 2": ["structural_ribs"]},
             "shapes": {**WRITTEN["shapes"], "RAIL": {"shape": "polygon", "points": [[0, 0], [1, 0], [1, 1], [0, 1]],
                                                      "count": 3, "base": 0.5}}}
FURNISHED_HANDIN = {"rows": [*HANDIN["rows"], {"id": "rail", "route": "prop", "size": [1.0, 0.1, 1.0]}, RIB],
                    "objects": {**HANDIN["objects"], "rail": {"rows": ["rail"]}}}


def written(folder, design, yard=YARD, site=SITE, handin=HANDIN):
    """scene-record@shed written into `folder` from its design `design` and the batch's hand-in `handin`: (the
    record's output, the writer's inputs)."""
    from score.review import setting
    from score.stages.scene_record import writer
    folder = pathlib.Path(folder)
    out, inputs = made(folder, design, yard)
    (folder / "plans/site.json").write_text(json.dumps(site))
    (folder / "inventory.json").write_text(json.dumps({**INVENTORY, "rows": [*INVENTORY["rows"], LAMP_ROW]}))
    (folder / "sky.json").write_text(json.dumps({**SKY, "place": "shed", "top": "site", "setting": setting.now()}))
    (folder / "hand-in.json").write_text(json.dumps(handin))
    inputs = {**inputs, "plan": out, "sky": folder / "sky.json", "hand-in": folder / "hand-in.json",
              "row kinds": REPO / "data/checks/row-kinds.json",
              "lamp library": REPO / "data/library/lamps.json", "places": REPO / "data/definitions/place.json",
              "dust": REPO / "data/physics/dust.json"}
    record = folder / "record"
    record.mkdir()
    writer.make(inputs, record, 0, {})
    assert writer.record_faults(record) == []
    return record, inputs


NOWHERE = {**WRITTEN, "openings": [{**WRITTEN["openings"][0], "to": "moon_city"}, WRITTEN["openings"][1]]}
# the drawing's width, not its door row's 1.2 m (habitat's 0.237 m hatches)
NARROW = {**WRITTEN, "openings": [{**WRITTEN["openings"][0], "wide": 0.3}, WRITTEN["openings"][1]]}
# a row the plan also leaves on its walls item, once its fixes placed it on an item of its own (camp's door, 2026-11-06)
WALLED = {**WRITTEN, "items": [*WRITTEN["items"], [writer.WALLS_ITEM, 0.0, 0.0, 8.0, 6.0, None, "item"]],
          "rows": {**WRITTEN["rows"], writer.WALLS_ITEM: ["bench", "ceiling_lamp"]}}
OFF_SITE = {**SITE, "holds": [SITE["holds"][0], {**SITE["holds"][1], "x": 2.0}]}  # the yard held 2 m off its gate
RAISED_YARD = {**YARD, "openings": [{**YARD["openings"][0], "sill": 3.0}]}  # the yard's gate 3 m up: the shed 3 m up
# Every world the verdicts are judged on, by name: a plan made of a record, a base's held plans, or a record written
# from its design (its yard, its site and its hand-in).
WORLDS = {"shed": ("plan", SHED), "no rows": ("plan", {**SHED, "rows": {"DRIVE LANE": []}}),
          "door S nowhere": ("plan", {**SHED, "leads": {"N": SHED["leads"]["N"]}}),
          "sealed open": ("plan", {**SHED, "leads": {**SHED["leads"], "N": {"to": "sealed", "why": "test"}}}),
          "outline": ("plan", {**NO_CORNER, "outline": [[0.0, 0.0], [8.0, 0.0], [8.0, 6.0], [0.0, 6.0]]}),
          "no corner": ("plan", NO_CORNER),
          "base": ("held", {"tube": TUBE, "hub": HUB, "lab": LAB, "base": BASE}),
          "base turned": ("held", {"tube": TUBE, "hub": TURNED_HUB, "lab": TURNED_LAB, "base": TURNED_BASE}),
          "furnished": ("record", FURNISHED, YARD, SITE, FURNISHED_HANDIN),
          "nowhere": ("record", NOWHERE, YARD, SITE, HANDIN), "narrow": ("record", NARROW, YARD, SITE, HANDIN),
          "walled": ("record", WALLED, YARD, SITE, HANDIN), "held off": ("record", WRITTEN, YARD, OFF_SITE, HANDIN),
          "raised": ("record", WRITTEN, RAISED_YARD, SITE, HANDIN)}
BUILDERS = {"plan": made, "held": held_world, "record": written}


class Among:
    """Findings that hold each of `found` among them."""

    def __init__(self, *found):
        self.found = found


def mapped(output, inputs):
    return plan.judge_mapped(output, inputs, None)


def held(output, inputs):
    return plan.judge_held(output, inputs, None)


def site_held(output, inputs):
    """The site's `held` gate, judged beside a written record."""
    holder = output.parent / "site-plan"
    holder.mkdir(exist_ok=True)
    (holder / "plan.json").write_text(json.dumps({"place": "site"}))
    return plan.judge_held(holder, inputs, None)


def opened(output, inputs):
    return gates.judge_openings(output, inputs, {})


def matched(output, inputs):
    return gates.judge_plan_matched(output, inputs, {})


def counted(row_id, count):
    """An inventory edit: row `row_id` counts `count`."""
    return lambda read: {**read, "rows": [{**row, "count": count} if row["id"] == row_id else row
                                          for row in read["rows"]]}


def moved_place(record):
    """A record edit: its one place stood 5 m along the floor from where it stands."""
    return {**record, "places": [{**record["places"][0], "at": [5.0, *record["places"][0]["at"][1:]]}]}


PLUG = {"name": "plug", "builder": "slab", "points": [[-0.8, -3.1], [0.8, -3.1], [0.8, -2.9], [-0.8, -2.9]],
        "low": 0.0, "high": 3.0}
BENCH_HELD = {"holds": [{"place": "bench", "row": "bench", "instance": "bench#1"}]}
NO_REASON = ("row bench: 2 in the scene inventory, 1 laid, and the plan says no reason",)
# Each verdict: its name, the world it is judged on (None: none), the edits made to that world's files first (`record`,
# `plans/<name>` or an input: a JSON in, a JSON out; each file put back after), its gate, and its answer (None: refused
# by name) with what its findings say: exactly a tuple, each of an Among, or a text (or texts) somewhere in them.
VERDICTS = [
    ("the shed maps, its doors leading to the yard and outside", "shed", {}, mapped, checks.PASS, None),
    ("an item with no rows", "no rows", {}, mapped, checks.FAIL, "BENCH"),
    ("a door that says nowhere it leads", "door S nowhere", {}, mapped, checks.FAIL, "door S"),
    ("a sealed door the layout leaves open", "sealed open", {}, mapped, checks.FAIL, "leaves it open"),
    ("a written plan with no corner takes its outline", "outline", {}, mapped, checks.PASS, None),
    ("a plan with no corner and no outline", "no corner", {}, mapped, None, "no corner and no outline"),
    ("the shed holds its spots and items", "shed", {}, held, checks.PASS, None),
    ("a person spot and an item drawn outside the shed, never a duct on its wall's line", "shed",
     {"plans/shed": lambda drawn: {**drawn, "people": [[4.0, 3.0], [9.5, 3.0]],
                                   "items": [*drawn["items"], ["PIPE", -5.0, 3.0, 10.0, 0.1, None, "item"],
                                             ["DUCT", -0.1, 4.0, 0.2, 1.0, None, "item"]]}},
     held, checks.FAIL, ("shed's person spot 2 [9.5, 3.0] lies outside its 8.0 x 6.0 m plan",
                         "shed's item 'PIPE' [-5.0, 3.0, 10.0, 0.1] lies outside its 8.0 x 6.0 m plan")),
    ("two holds' outlines overlapping", None, {}, lambda output, inputs: plan.overlap_faults({"holds": OVERLAPPING}),
     checks.FAIL, ("the outlines of hub and tube overlap, 0.97 m thick",)),
    ("a place held once that more doors lead to than lead back", None, {},
     lambda output, inputs: plan.once_faults(HELD_ONCE), checks.FAIL,
     ("tube is held once, but 2 doors of its siblings lead to it and 1 of its own lead back",)),
    ("two doors on one wall, each by its own lead", None, {}, lambda output, inputs: gates.door_faults(TWO_DOORS),
     checks.PASS, ()),
    ("the base holds its tube turned and stretched", "base", {}, held, checks.PASS, None),
    ("a door naming the tube, not its instance, and a hold another size than its plan laid in it", "base",
     {"plans/hub": lambda hub: {**hub, "openings": [*hub["openings"], {"kind": "door", "at": [5.0, 10.0],
                                                                       "to": "tube"}]},
      "plans/base": lambda base: {**base, "holds": [base["holds"][0], {**TUBE_1, "d": 3.0}, base["holds"][2]]}},
     held, checks.FAIL, ("tube#1's hold is 6 x 3 m, its plan laid in it 6 x 2 m (turned 90)",
                         "hub's door to tube at [5.0, 10.0] names no instance of it (tube#1)",
                         *[f"{one}'s door to {other} at {at} opens 0.5 m from {other}'s nearest door back ({back}) where "
                           "the holder holds both" for one, other, at, back in (
                               ("hub", "tube#1", [10.0, 5.0], [1.0, 4.0]), ("lab", "tube#1", [0.0, 2.0], [1.0, 0.0]),
                               ("tube#1", "hub", [1.0, 4.0], [10.0, 5.0]), ("tube#1", "lab", [1.0, 0.0], [0.0, 2.0]))])),
    ("a hold turned 360 degrees", "base",
     {"plans/base": lambda base: {**base, "holds": [base["holds"][0], {**TUBE_1, "turn": 360}, base["holds"][2]]}},
     held, None, "turns 360 degrees"),
    ("the base holds its tube turned 315 degrees between the hub's corner door and the lab's", "base turned", {}, held,
     checks.PASS, None),
    *[(f"the furnished shed passes {check.name}", "furnished", {},
       lambda output, inputs, check=check: check.judge(output, inputs, {}), checks.PASS, None)
      for check in gates.CHECKS],
    ("a door filled", "furnished", {"record": lambda record: {**record, "structure": [*record["structure"], PLUG]}},
     matched, checks.FAIL, "filled by ['plug']"),
    ("the lamp moved off its item", "furnished",
     {"record": lambda record: {**record, "lights": [{**record["lights"][0], "at": [3.0, 2.7, 0.0]}]}}, matched,
     checks.FAIL, "'LAMP' stands off"),
    ("a glowing row with no lamp", "furnished", {"record": lambda record: {**record, "lights": []}}, matched,
     checks.FAIL, Among("glowing row ceiling_lamp has 0 lamps, its reading counts 1")),
    ("a glowing row one lamp short for no recorded reason", "furnished", {"inventory": counted("ceiling_lamp", 2)},
     matched, checks.FAIL, ("glowing row ceiling_lamp has 1 lamps, its reading counts 2",
                            "row ceiling_lamp: 2 in the scene inventory, 1 laid, and the plan says no reason")),
    ("a glowing row the plan dropped one of (camp's monitors, 2026-11-11)", "furnished",
     {"inventory": counted("ceiling_lamp", 2),
      "plans/shed": lambda drawn: {**drawn, "dropped": [{"item": "ceiling_lamp", "why": "cut: 1 laid", "laid": 1}]}},
     matched, checks.PASS, ()),
    ("a shell row the shell cannot build", "furnished",
     {"hand-in": lambda handin: {**handin, "rows": [*handin["rows"], {"id": "landing_pad", "part": "floor",
                                                                      "route": "plan"}]}},
     matched, checks.FAIL, ("shell row landing_pad (floor) is built by no piece of the shell",)),
    ("a door to no place", "nowhere", {}, opened, checks.FAIL,
     ("opening 1 leads to 'moon_city', no place of the design nor a row of its inventory",
      "opening 1 leads to 'moon_city', its door row 'HATCH N, 1.2 x 2.1 m' to 'yard'")),
    ("a doorway narrower than its door row", "narrow", {}, opened, checks.FAIL,
     ("opening 1 is 0.3 m wide for door row 'HATCH N, 1.2 x 2.1 m' of 1.2 m",)),
    ("a row laid fewer times than its inventory counts, the plan giving no reason", "narrow",
     {"inventory": counted("bench", 2)}, matched, checks.FAIL, NO_REASON),
    ("a child scene's instance no doorway leads to is no reason", "narrow",
     {"inventory": counted("bench", 2), "plans/shed": lambda drawn: {**drawn, **BENCH_HELD}}, matched, checks.FAIL,
     NO_REASON),
    ("laid as often as the doorways lead to its instances", "narrow",
     {"inventory": counted("bench", 2),
      "plans/shed": lambda drawn: {**drawn, "holds": [*BENCH_HELD["holds"], {"place": "yard", "row": "yard",
                                                                            "leads": {"bench": "bench#1"}}]}},
     matched, checks.PASS, None),
    ("a row on its walls item and its own item laid once", "walled", {}, matched, checks.PASS, None),
    *[verdict for world in ("held off", "raised") for verdict in (
        (f"{world}: the shed's door meets the yard's gate", world, {}, opened, checks.PASS, None),
        (f"{world}: the yard stood 5 m off its gate", world, {"record": moved_place}, opened, checks.FAIL,
         "opens 5.00 m along the floor"))],
    ("the site's yard held 2 m off its gate", "held off", {}, site_held, checks.FAIL,
     ["yard's hold is 20.0 x 12.0 m, its yard item 20.0 x 12.0 m, their middles 2.0 m apart",
      "shed's door to yard at [4.0, 0.0] opens 2.0 m from yard's nearest door back"]),
    ("the site holds the shed 3 m over the yard", "raised", {}, site_held, checks.PASS, None),
]


def built(worlds, root, name):
    """World `name` of WORLDS, made under `root` once and kept in `worlds`: (its output, its inputs)."""
    if name not in worlds:
        kind, *args = WORLDS[name]
        folder = root / name
        folder.mkdir()
        try:
            worlds[name] = BUILDERS[kind](folder, *args)
        except ValueError as refused:
            worlds[name] = refused
    if isinstance(worlds[name], ValueError):
        raise worlds[name]
    return worlds[name]


def file_of(key, output, inputs):
    """The file an edit's `key` names in a world: its record, a plan of its own (`plans/<name>`) or an input."""
    if key == "record":
        return output / "record/shed.json"
    if key.startswith("plans/"):
        return pathlib.Path(inputs["plans"]) / f"{key[len('plans/'):]}.json"
    return pathlib.Path(inputs[key])


def judged(worlds, root, world, edits, judge):
    """(answer, findings) of `judge` on `world` with `edits` made to its files, each put back after; a refusal answers
    None with its words."""
    try:
        output, inputs = built(worlds, root, world) if world else (None, None)
        kept = {}
        try:
            for key, edit in edits.items():
                path = file_of(key, output, inputs)
                kept[path] = path.read_text()
                path.write_text(json.dumps(edit(json.loads(kept[path]))))
            found = judge(output, inputs)
        finally:
            for path, text in kept.items():
                path.write_text(text)
    except ValueError as refused:
        return None, (str(refused),)
    if hasattr(found, "answer"):
        return found.answer, tuple(found.findings)
    return (checks.FAIL if found else checks.PASS), tuple(found)


def says(said, findings):
    """Whether `findings` say `said`: exactly a tuple, each of an Among, or a text (or texts) somewhere in them."""
    if said is None:
        return True
    if isinstance(said, tuple):
        return findings == said
    if isinstance(said, Among):
        return all(found in findings for found in said.found)
    return all(text in " | ".join(findings) for text in ([said] if isinstance(said, str) else said))


def test_the_record_is_written_from_the_design(tmp_path):
    """The shed's plan maps, its doors leading to the yard and outside; an item with no rows, a door that says nowhere
    it leads and a sealed door the layout leaves open each fail `mapped` by name; a written plan (plan_writing's: an
    outline, no corner) makes its plan with square corners, its outline drawing every corner, and a plan with neither
    is refused by name (each verdict a row of VERDICTS).
    Break: score/stages/scene_record/plan.py: `return [f"{name} says nowhere it leads, or not why"]` -> `return []`
    Break: score/stages/scene_record/plan.py:
        `found.append(f"{name} is sealed but the room layout leaves it open (no leaf shuts it)")` -> `pass`
    Break: score/stages/scene_record/plan.py: `    if plan.get("outline"):` -> `    if False:`
    Break: score/stages/scene_record/plan.py: `raise ValueError(f"{plan['title']}: the plan gives no corner and no
        outline")`
        -> `return 0.0`
    Its `held` gate passes it, and fails a person spot or an item drawn outside its box (the hangar's workers 3.8 m
    past its wall, the garage's pipes 5 m out: the audit of 2026-11-04), never a pipe drawn on its wall's line; two
    overlapping holds and a place held once that more doors lead to than lead back (the base's one tube) fail too.
    Break: score/stages/scene_record/plan.py: `if not within([float(spot[0]), float(spot[1]), 0.0, 0.0], outer):` ->
        `if False:`
    Break: score/stages/scene_record/plan.py: `return within([x + reach, y + reach,` -> `return True or within([x + reach, y + reach,`
    Break: score/stages/scene_record/plan.py: `if depth > EDGE:` -> `if False:`
    Break: score/stages/scene_record/plan.py: `if leading > back:` -> `if False:`
    A place held several times stands once a hold, each instance by itself (#72, the base's tubes): a tube held
    turned and stretched meets the hub's door and the lab's at its two ends, its own leads renamed by its hold; a
    door naming the tube and not its instance, a hold another size than its plan laid in it, and a turn of 360 degrees
    fail by name. A hold turns any angle the concept needs (the base's tubes off the hub's diagonal facets): a tube
    turned 315 degrees from the hub's corner door to the lab's, its box over the hub's box and the lab's but its
    outline over neither (overlaps judged on outlines), the hub's two doors to `tube` each named by its spot; the lab,
    every door of it on a floor 1 m over its lower one, sunk 1 m so its door meets the tube's.
    Break: score/stages/scene_record/plan.py: `laid = [laid_outline(hold, (held.get(name_of(hold)) or (None, None))[1]) for hold in holds]` ->
        `laid = [laid_outline(hold) for hold in holds]`
    Break: score/stages/scene_record/plan.py: `return round(math.cos(turn), 12), round(math.sin(turn), 12)` ->
        `return round(math.cos(turn)), round(math.sin(turn))`
    Break: score/stages/scene_record/plan.py: `return f"{opening.get('to')}@{float(opening['at'][0]):g},{float(opening['at'][1]):g}"` ->
        `return None`
    Break: score/stages/scene_record/plan.py: `sunk = {name: -sunk_by(plan) for name, (_, plan) in held.items()}` ->
        `sunk = {name: 0.0 for name in held}`
    Break: score/stages/scene_record/plan.py: `return middle + np.array([cos * across - sin * along, sin * across + cos * along])` ->
        `return middle + np.array([across, along])`
    Break: score/stages/scene_record/plan.py: `found[name_of(hold)] = (hold, as_held(hold, read(path)))` ->
        `found[name_of(hold)] = (hold, read(path))`
    Break: score/stages/scene_record/plan.py: `if opening.get("kind") in DOORWAYS and to in instances and to not in held:` -> `if False:`
    Break: score/stages/scene_record/plan.py: `if abs(wide - hold["w"]) > EDGE or abs(deep - hold["d"]) > EDGE:` -> `if False:`
    Break: score/stages/scene_record/writer.py: `own = np.asarray(met[0]["door"]["at"], float) + unturned(hold, there - met[0]["spot"])` ->
        `own = np.asarray(met[0]["door"]["at"], float)`
    Two doors on one wall lead each by its own lead, `<side>:<along>` over its side's (the walkway's galley and
    quarters doors, 2026-11-05), and the openings gate finds each its doorway nearest along.
    Break: score/stages/scene_record/plan.py: `return leads.get(f"{side}:{float(at):g}") or leads.get(` ->
        `return leads.get(`
    Break: score/stages/scene_record/gates.py: `key=lambda pair: abs(float(pair[1]["at"][0 if where in ("N", "S") else 1]) - float(along)))` ->
        `key=lambda pair: 0.0)`
    A record's doorways lead where its own hold leads them, and its neighbours' doors lead back to its hold's name
    (2026-11-06: the base's tube, the airlock).
    Break: score/stages/scene_record/writer.py held_design: `return (place_plan.as_held(own, design), place_plan.name_of(own)) if own else (design, place)` ->
        `return design, place`
    The shed's record holds its shell with the north door cut, its stair, a light over its lamp, its sky from the
    physics, the yard its door leads to where the site holds it, and only the view standing inside its walls; its
    gates pass, and a door filled, a lamp moved off its item and a door to no place each fail by name. The lamp item
    (3.5, 2.5) 1 m square on the 8 x 6 m shed is at the shed's middle, its base 2.7 m, the light 5% up its 0.2 m.
    The yard stands with its gate on the shed's door, (0, 0, -9) from the shed's middle (the base's airlock opened
    21.8 m from the hub's door, the flat stood 9 m under its stairwell door: the audit of 2026-11-04): held 2 m off
    its gate it still stands there and the site's `held` gate fails on the hold and the door; its gate 3 m up stands
    the shed 3 m over it, the yard 3 m down; the yard moved 5 m off fails `openings`.
    Break: score/stages/scene_record/writer.py: `there = there + met[0]["spot"] - met[0]["there"]` -> `pass`
    Break: score/stages/scene_record/writer.py: `round(floor - other_floor + other_level - level, 4)` ->
        `round(floor - other_floor, 4)`
    Break: score/stages/scene_record/gates.py:
        `if along > writer.place_plan.DOORS_MET or up > writer.place_plan.LEVEL_MET:` -> `if False:`
    Break: score/stages/scene_record/plan.py: `elif pair["gap"] > DOORS_MET:` -> `elif False:`
    Break: score/stages/scene_record/plan.py: `if not sized or middle > HOLD_MIDDLE:` -> `if False:`
    Break: score/stages/scene_record/gates.py:
        `found.append(f"opening {number} ({opening.get('kind')}) at {opening['at']} is filled by {filled}")` -> `pass`
    Break: score/stages/scene_record/gates.py: `found.append(f"the light of plan item {name!r} stands off its
        footprint")`
        -> `pass`
    Break: score/stages/scene_record/gates.py: `if row_id in tied and made.get(row_id, 0) < int(row.get("count") or
        1)]` -> `if False]` (a glowing row with fewer lamps than its reading counts passes)
    Break: score/stages/scene_record/gates.py: count_faults' `glowing = {row_id: writer.counted(row, design) ...}`
        dropped (a monitor the plan's `dropped` cut off its desk is counted missing: camp and lab, 2026-11-11)
    Break: score/stages/scene_record/gates.py:
        `found.append(f"opening {number} leads to {to!r}, no place of the design nor a row of its inventory")`
        -> `pass`
    Break: score/stages/scene_record/gates.py: unbuilt_rows' `if row_id not in named]` -> `if False]` (a shell row
        the shell cannot build dropped without a word: the hangar's landing pad, 2026-11-04)
    Break: score/stages/scene_record/writer.py stair: the `if high < low:` swap dropped (a flight drawn from 1 m down
        to 0 m stands its foot at its high end, which the builder lays as a flat block, its treads underneath)
    And (2026-11-04 audit) a doorway is its door row's: one drawn 0.3 m wide for the 1.2 m hatch row, or leading
    elsewhere than its lead, fails `openings` by name; a row laid another number of times than its scene inventory
    counts, the plan giving no reason, fails `plan-matched`; laid as often as the plan's doorways lead to its child
    scene's instances (base's seven tubes, 2026-11-06) it passes. A row the plan also leaves on its walls item, once its
    fixes placed it on an item of its own, is laid once, at its own item (camp's airlock door, 2026-11-06).
    Break: score/stages/scene_record/writer.py item_rows: `if name != WALLS_ITEM or row not in placed]` -> `]`
    Break: score/stages/scene_record/gates.py: `and row["id"] not in said and counted.get(row["id"], 0) !=
        led.get(row["id"])]` -> `and row["id"] not in said]` (the instances the doorways lead to are no reason)
    Break: score/stages/scene_record/gates.py: led_instances' `if hold.get("instance") in led:` -> `if
        hold.get("instance"):` (an instance no doorway leads to counts as a reason)
    Break: score/stages/scene_record/gates.py: `if abs(wide - metres) > DOOR_SHARE * metres or wide < PASSABLE:` ->
        `if False:`
    Break: score/stages/scene_record/gates.py: `if lead is not None and opening.get("to") != lead:` -> `if False:`
    Break: score/stages/scene_record/gates.py: `stair_faults(record, design) + lamp_faults(record, design) + \\
        count_faults(record, design, inputs) + row_count_faults(record, design, inputs)` -> `... + \\
        count_faults(record, design, inputs)`
    2026-11-02, round 44: the day sky's dust left with the old records (eb01c402) and every outdoor Mars place's
    sky was black, campgrounds' 192.8 levels off its concept's. An open place on Mars carries Mars's dusty air
    (data/physics/dust.json: depth 0.6, albedo 0.975, 0.93, 0.86, forward 0.67, diffuse 0.25, its source said) with
    the gain measured against the camp's old concept, and mars_sky draws it butterscotch, its red over its blue; an
    enclosed place on Mars carries it too (2026-11-04: camp's glass domes showed black space in a Mars afternoon), an
    open one on the Moon (no dust) none; the file is a declared input.
    Break: score/stages/scene_record/writer.py: `return found if dome is None else {**found, "sky_dome": dome}` ->
        `return found`
    Break: score/stages/scene_record/writer.py: `if not found:` -> `if inside(design) or not found:` (camp's domes)
    Fault (2026-10-25): the record laid no object of a designed place, so the assembly placed none of its models.
    Each prop row's plan item gets its object `<row>_<n>` over its middle at its shape's base, waiting on its take's
    model (`<first row>_1`); a run the plan draws once as a polygon counting three lays three pieces along it, each
    its long side along the path; a row with no size waits named; the plan's own floor is named on its deck.
    Break: score/stages/scene_record/writer.py: `            base = float(shape.get("base") or 0.0)` ->
        `            base = 0.0`
    Break: score/stages/scene_record/writer.py: `return [along(path, (number + 0.5) / pieces) for number in
        range(pieces)]`
        -> `return [along(path, 0.5) for number in range(pieces)]`
    2026-11-04: the lab's 10 pipes on 6 plan items laid 6. A row counting 5 on two items lays 3 and 2.
    Break: score/stages/scene_record/writer.py pieces_of: `for turn in range(max(short, 0)):` -> `for turn in
        range(0):` (two pipes laid for five)
    Break: score/stages/scene_record/writer.py design_objects: `pieces_of(counted(row, design), laid)` ->
        `pieces_of(row, laid)` (the five laid again where the plan dropped three)
    Batch 1's retry: the tube's ribs, their box the whole picture, framed no close-up. The shell lays an arched
    structure row (design_shell.arched) as an `arch` at each plan item tied to it, at the row's size, named its row,
    painted as a wall; a block of no band, or a row of no structure, is not arched.
    Break: score/stages/scene_record/writer.py: `way = np.array([1.0, 0.0]) if wide >= deep else np.array([0.0, 1.0])`
        -> `way = np.array([0.0, 1.0])`
    Each shell part and stair takes the variant the scene's surface library gives its kind (a stair the floor's
    when the library names no stair), and a part it gives none, or every part while no library is made, carries no
    surface and says why; the scene builder names that on the mesh and binds nothing.
    Break: score/stages/scene_record/writer.py: `    return dict(entry, surface=surface)` -> `    return dict(entry,
        surface="deck_plate")`
    Break: score/stages/earth_seed/design_shell.py: `return f"{place}: the scene's surface library is not made (run
        surface-library first): its {kind} has none"`
        -> `return f"{place}: no surface"`
    Break: score/stages/earth_seed/design_shell.py: `return next((name for name in found if set(name.split("_")) &
        set(words)), found[0])` -> `return found[0]` (docking_airlock's floor painted with its ochre edging)
    The stairwell's palm seen through its window is the square's (prepare's groups.shown_from: `shown`): the record
    stands the holder at its own plan's middle, a place it holds beside where it holds it, each once.
    Break: score/stages/scene_record/writer.py: `if name in stood_already or name == place:` -> `if name == place:`
    The lit shed: a 1 by 1 by 10 m floodlight tower (a stem by its metres) read as a tower (the reading's noun) gets
    one library lamp near its top over its middle, a light switch none (score/stages/row_kinds.py held_by).
    Break: score/stages/scene_record/writer.py: `high = base + tall * share` -> `high = base + share`
    An engine room's core (a machine: its row kind does not glow) its concept shows glowing blue at half the
    brightest light gets the library's lamp over its plan item in that blue at half the lamp's strength; the engine
    its concept shows dark and the starry sky (the physics') get none (reading.concept_light, kept as
    {home}/design/light/<place>.json).
    Break: score/stages/scene_record/writer.py:
        `"energy": round(energy * light["strength"] * part * (float(glow["brightness"]) if glow else 1.0), 4),`
        -> `"energy": round(energy * light["strength"] * part, 4),`
    Break: score/stages/scene_record/writer.py:
        `for row in inventory["rows"] if row["id"] in shown and row.get("anchor") != "sky"}`
        -> `for row in inventory["rows"] if row["id"] in shown}`
    Break: score/stages/scene_record/concept_light.py: `PROPS_HOME / "design" / "light"` -> `PROPS_HOME / "light"`
        (the row reads its concept light where plans.keep keeps none)
    Break: score/stages/scene_record/writer.py pieces_of: `counts[turn % len(counts)] += 1` -> `pass` (four counted
        screens on two items lay two lamps)
    Break: score/stages/scene_record/writer.py glow_share: `return (float(emitter["share"]), "emitter") if said &` ->
        `return (1.0, "source") if said &` (a screen throws a lamp's light)
    Break: score/stages/scene_record/writer.py: `set(emitter["words"]) | CONTROL_FACES | SIGNAL_LIGHTS` ->
        `set(emitter["words"]) | SIGNAL_LIGHTS` (a door's keypad throws a lamp's light: shiplock, 2026-11-10)
    Engineroom (#36): a glowing wall panel the plan draws as the whole room (7 x 5 m of the 8 x 6 m shed), held on
    the west wall at its middle (plan 0, 3), has its lamp on that wall's face (x 0.1) 0.1 m out into the room, at
    plan (0.2, 3), as high as the wall mount says on the shed's 3 m walls (1.5 m), never over the room's middle; the
    plan-matched gate takes it there, off its item's box, and fails it moved off its wall; one on the east wall read
    as three has three lamps spread along the face, at the middles of its thirds (plan y 1, 3 and 5).
    Break: score/stages/scene_record/writer.py: `walled = relation is not None and relation.get("how") == "wall" and
        room` -> `walled = False`
    Break: score/stages/scene_record/gates.py: `if light.get("against"):` -> `if False:`
    Break: score/stages/scene_record/writer.py: `if pieces == 1 else length * (piece + 0.5) / pieces` -> `if True
        else 0.0` (three panels' lamps on one spot)"""
    from pxr import Usd
    from score.review import overhead
    from score.stages.earth_seed import design_shell
    sys.path.insert(0, str(REPO / "tools/usd"))
    import scene
    worlds = {}
    for name, world, edits, judge, answer, said in VERDICTS:
        found, findings = judged(worlds, tmp_path, world, edits, judge)
        assert found == answer and says(said, findings), (name, found, findings)
    # the plans made draw their doors' leads and the outline's walls
    for world, drawn in (("shed", {"leads": ["yard", "outside"]}), ("outline", {"walls": (0.0, 8.0, 6.0)})):
        mapped_plan = json.loads((built(worlds, tmp_path, world)[0] / "plan.json").read_text())
        seen = {"leads": [door["leads"] for door in mapped_plan["doors"]],
                "walls": (mapped_plan["walls"]["corner"], mapped_plan["walls"]["wide"], mapped_plan["walls"]["deep"])}
        assert {key: seen[key] for key in drawn} == drawn, (world, seen)
    assert [door["leads"] for door in plan.doors_of(TWO_DOORS, INVENTORY)] == ["sealed", "yard"]
    # the base: the tube's hub end on the lab's door, its record standing the instance its place's stage, its middle
    # 3 m east of the hub's door, stretched
    plans = built(worlds, tmp_path, "base")[1]["plans"]
    assert plan.on_holder(TUBE_1, TUBE, [1.0, 0.0]).tolist() == [16.0, 5.0]
    stood = gates.writer.sibling("hub", HUB, BASE, "tube#1", plans)
    assert (stood["name"], stood["stage"], stood["instance"], stood["at"], stood["scale"]) == (
        "tube_1", "tube", "tube#1", [8.0, 0.0, 0.0], [1.0, 1.0, 1.5]), stood
    # the base turned: the tube's greenhouse end on the lab's corner, its box over both (its outline over neither),
    # the lab sunk 1 m; each record leads its doorways where its own hold leads them, its neighbours' doors leading
    # back to that hold's name: the tube stands the hub and the lab, the lab and the hub each tube#1, every door met
    # (2026-11-06: the base's tube met no door of the greenhouse or the hub back, which lead to its instance, and the
    # airlock stood the hub, which its hold leads past it to tube#3)
    given = built(worlds, tmp_path, "base turned")[1]
    assert np.allclose(plan.on_holder(TURNED_TUBE, TUBE, [1.0, 4.0]), [CORNER, CORNER])
    assert len(plan.overlap_faults(TURNED_BASE)) == 2  # by their boxes the tube overlaps both
    assert plan.levels_of(plan.held_plans(TURNED_BASE, given["plans"])) == {"hub": 0.0, "tube#1": 0.0, "lab": -1.0}
    for name, own, neighbours in (("tube", TUBE, {"hub", "lab"}), ("lab", TURNED_LAB, {"tube#1"}),
                                  ("hub", TURNED_HUB, {"tube#1"})):
        record = {"place": name, "places": gates.writer.places_of(name, {"doors": []}, own, given["plans"])}
        assert {entry.get("instance", entry["name"]) for entry in record["places"]} == neighbours, record["places"]
        assert gates.pair_faults(record, own, given) == gates.lead_faults(record, own, given) == [], name
    output, inputs = built(worlds, tmp_path, "furnished")
    folder = output.parent
    place, record = writer.record_in(output)
    names = {entry["name"] for entry in record["structure"]}
    assert place == "shed" and record["inside"] and {"wall_1", "deck_1", "roof_1", "stair_1"} <= names, names
    assert len([name for name in names if name.startswith("wall_1")]) == 4, names  # cut round the door
    [lamp] = record["lights"]
    assert lamp["at"] == [0.0, 2.71, 0.0] and "ceiling_lamp" in lamp["from"], lamp  # 5% up the fitting
    seen = overhead.seen(json.loads((folder / "sky.json").read_text())["setting"], SKY["site"], SKY["time"])
    sun = next(light for light in seen["lights"] if light["name"] == "Sun")
    [up] = record["environment"]["sky"]["lights"]
    assert up["name"] == "Sun" and up["altitude"] == sun["altitude"] > 0, (up, sun)
    [yard] = record["places"]
    assert yard["name"] == "yard" and yard["at"] == [0.0, 0.0, -9.0] and yard["rotation"] == [0, 0, 0, 1], yard
    assert [view["name"] for view in record["views"]] == ["from-door-1", "from-door-2", "spot-1"], record["views"]
    assert [view["name"] for view in record["views_left_out"]] == ["spot-2"], record["views_left_out"]
    assert record["ceiling"] == 3.0, record
    stair = next(entry for entry in record["structure"] if entry["name"] == "stair_1")
    down = writer.stair(1, {**WRITTEN["stairs"][0], "from": 1.0, "to": 0.0}, WRITTEN)
    assert down["foot"][1] < down["top"][1] and (down["foot"], down["top"]) == (
        [stair["top"][0], stair["foot"][1], stair["top"][2]], [stair["foot"][0], stair["top"][1], stair["foot"][2]]
    ), (down, stair)  # a flight drawn from its high end stands its foot at its low end: its treads face up
    # every prop row's plan item has its object over its middle at its shape's base, waiting on its take's model:
    # the bench item (1, 1) 2 x 0.6 m at (-2, -1.7) on the shed centred on its 8 x 6 m, the lamp sharing the
    # bench's take at its 2.7 m base, the rail run three pieces along its polygon 0.5 m up, each its long side
    # along the path; the plan's own floor is named on its deck; the arched ribs are no object
    found = {entry["name"]: entry for entry in record["objects"]}
    assert sorted(found) == ["bench_1", "ceiling_lamp_1", "rail_1", "rail_2", "rail_3"], sorted(found)
    bench = found["bench_1"]
    assert bench["at"] == [-2.0, 0.0, -1.7] and bench["bake"] == "bench_1" and bench["row"] == "bench", bench
    assert bench["rotation"] == [0.0, 0.0, 0.0, 1.0] and "surface line's bake" in bench["waiting"], bench
    assert found["ceiling_lamp_1"]["bake"] == "bench_1" and found["ceiling_lamp_1"]["at"] == [0.0, 2.7, 0.0]
    rails = [found[f"rail_{number}"] for number in (1, 2, 3)]
    assert all(rail["at"][1] == 0.5 for rail in rails) and len({tuple(rail["at"]) for rail in rails}) == 3, rails
    assert rails[0]["at"] == [-1.6667, 0.5, 1.0] and rails[0]["rotation"] == [0.0, 0.0, 0.0, 1.0], rails[0]
    deck = next(entry for entry in record["structure"] if entry["name"].startswith("deck"))
    assert deck["row"] == "shed_floor", deck
    # each arched rib is the shell's band at its plan item, at its row's size, named its row: the first rib's
    # item (0, 1) lies east-west across the shed, its 3.2 m span centred at plan x 4, its feet at -1.6 and 1.6,
    # z -1.9; a block of no band, or a row of no structure, is not arched
    assert design_shell.arched(RIB) and not design_shell.arched({**RIB, "size": [3.2, 2.0, 3.2]})
    assert not design_shell.arched({**RIB, "part": "object"})
    ribs = [entry for entry in record["structure"] if entry["builder"] == "arch"]
    assert [entry["name"] for entry in ribs] == ["structural_ribs_1", "structural_ribs_2"], ribs
    assert all(entry["row"] == "structural_ribs" and entry["plain"] == "shell" for entry in ribs), ribs
    assert ribs[0]["feet"] == [[-1.6, -1.9], [1.6, -1.9]] and ribs[0]["low"] == 0.0, ribs[0]
    # no surface library row read: every part of the shell carries no surface and says why, none painted
    # another way; with the scene's library made each takes its kind's, a stair the floor's, a roof the
    # library names none for carries none and says why
    assert all(entry["surface"] is None and "not made" in entry["surface_missing"]
               for entry in record["structure"]), record["structure"]
    made_library = folder / "library"
    made_library.mkdir()
    (made_library / "materials.json").write_text(json.dumps({"kinds": {"wall": ["painted_panel"],
                                                                      "floor": ["deck_plate"]}}))
    plan_record = json.loads((pathlib.Path(inputs["plan"]) / "plan.json").read_text())
    surfaces = {entry["name"]: entry for entry in writer.record_of(
        plan_record, FURNISHED, {**inputs, writer.LIBRARY_ROW: made_library})["structure"]}
    assert {surfaces["wall_1"]["surface"], surfaces["deck_1"]["surface"], surfaces["stair_1"]["surface"]} == \
        {"painted_panel", "deck_plate"} and surfaces["stair_1"]["surface"] == "deck_plate", surfaces
    roof = surfaces["roof_1"]
    assert roof["surface"] is None and "names no surface for the kinds a roof takes" in roof["surface_missing"]
    edged = {"kinds": {"floor": ["hazard_frame_paint", "deck_floor_plate", "floor_vent_grate"],
                       "wall": ["hull_panel", "hull_recess"]}}
    assert [design_shell.surface_for(kind, edged) for kind in ("deck", "wall", "roof")] == [
        "deck_floor_plate", "hull_panel", None]  # the floor's own, never its edging; a wall's first; a roof none
    # the scene builder lays the ribs as their band, named their row, and names the roof's missing surface on its
    # mesh, binding nothing
    stage = Usd.Stage.CreateInMemory()
    scene.write_structure(stage, "shed", [roof, *ribs])
    meshed = scene.built_meshes(ribs[0])[0]["points"]
    assert np.allclose(meshed.min(0), [-1.6, 0.0, -2.0]) and np.allclose(meshed.max(0), [1.6, 3.2, -1.8]), meshed
    assert stage.GetPrimAtPath("/shed/Structure/structural_ribs_1").GetAttribute("score:row").Get() == \
        "structural_ribs"
    mesh = stage.GetPrimAtPath("/shed/Structure/roof_1")
    assert "roof takes" in mesh.GetAttribute("score:surface:missing").Get(), mesh
    assert not mesh.HasRelationship("material:binding"), mesh
    # the places a backdrop row of the hand-in is shown from stand once each: the yard already stood by its
    # door, the site (the palm's holder) at its own plan's middle
    shown = {"rows": [{"id": "palm_tree", "route": "skyline", "shown": {"place": "site", "row": "palm_tree"}},
                      {"id": "far_shed", "route": "skyline", "shown": {"place": "yard", "row": "shed"}}]}
    stood = writer.places_of("shed", plan_record, FURNISHED, inputs["plans"], shown)
    assert [entry["name"] for entry in stood] == ["yard", "site"], stood
    assert stood[1]["at"] == [10.0, 0.0, -5.0] and "palm_tree" in stood[1]["from"], stood[1]
    # a row with no size waits named; a row counting 5 on two items lays 3 and 2, and 2 where the plan dropped three
    unsized = {**FURNISHED_HANDIN, "rows": [{**row, "size": None} if row["id"] == "rail" else row
                                            for row in FURNISHED_HANDIN["rows"]]}
    [rail] = [entry for entry in writer.design_objects(FURNISHED, unsized) if entry["name"] == "rail_1"]
    assert "row rail has no size" in rail["waiting"], rail
    pipes = {**FURNISHED, "items": [*FURNISHED["items"], ["PIPE 1", 5.0, 1.0, 1.0, 0.2, None, "item"],
                                    ["PIPE 2", 5.0, 3.0, 1.0, 0.2, None, "item"]],
             "rows": {**FURNISHED["rows"], "PIPE 1": ["pipe"], "PIPE 2": ["pipe"]}}
    piped = {"rows": [*FURNISHED_HANDIN["rows"], {"id": "pipe", "route": "prop", "size": [1.0, 0.1, 0.1], "count": 5}],
             "objects": {**FURNISHED_HANDIN["objects"], "pipe": {"rows": ["pipe"]}}}
    dropped = {**pipes, "dropped": [{"item": "pipe", "why": "3 more of it than the place's free floor holds",
                                     "laid": 2}]}  # settle@engineroom, 2026-11-09
    for laid_plan, wanted in ((pipes, ["plan item 'PIPE 1'"] * 3 + ["plan item 'PIPE 2'"] * 2),
                              (dropped, ["plan item 'PIPE 1'", "plan item 'PIPE 2'"])):
        laid = writer.design_objects(laid_plan, piped)
        assert [entry["from"].split(",")[0] for entry in laid if entry["row"] == "pipe"] == wanted, laid
    # a row the plan also leaves on its walls item is laid once, at its own item
    place, record = writer.record_in(built(worlds, tmp_path, "walled")[0])
    laid = [entry["name"] for entry in record["objects"] if entry["row"] in ("bench", "ceiling_lamp")]
    assert laid == ["bench_1", "ceiling_lamp_1"] and len(record["lights"]) == 1, (laid, record["lights"])
    # the yard stands on the shed's door back, at its height, whatever the hold
    for world, at in (("held off", [0.0, 0.0, -9.0]), ("raised", [0.0, -3.0, -9.0])):
        [stood] = writer.record_in(built(worlds, tmp_path, world)[0])[1]["places"]
        assert stood["at"] == at, (world, stood)
    assert site_held(*built(worlds, tmp_path, "raised")).measures["held places"] == 2
    # a place on mars inside or out has its dusty day sky and one on the moon none
    sys.path.insert(0, str(REPO / "tools" / "usd"))
    import mars_sky
    from score.review import setting
    dust = json.loads((REPO / "data/physics/dust.json").read_text())
    on_mars = {"site": {"on": "mars", "latitude": 30.0, "longitude": 130.0, "height_m": 0.0},
               "time": "2099-10-01T16:00:00Z", "setting": setting.now()}
    yard = {"title": "YARD", "outline": [[0, 0], [10, 0], [10, 10], [0, 10]], "terrain": {"spots": [[5, 5]]}}
    dome = writer.environment(yard, on_mars, dust)["sky_dome"]
    assert {key: dome[key] for key in ("depth", "albedo", "forward", "diffuse", "gain")} == {
        "depth": 0.6, "albedo": [0.975, 0.93, 0.86], "forward": 0.67, "diffuse": 0.25,
        "gain": list(writer.SKY_GAIN)}, dome
    assert "Wolff et al. 2009" in dome["from"] and "cited" not in dome, dome
    picture = mars_sky.picture(dome, [0.0, -0.5, -0.866], 64)
    red, _, blue = picture[: picture.shape[0] // 2].reshape(-1, 3).mean(axis=0)
    assert red > blue > 0, (red, blue)
    assert writer.environment(WRITTEN, on_mars, dust)["sky_dome"] == dome  # seen through its glass and openings
    assert "sky_dome" not in writer.environment(yard, {**on_mars, "site": {**on_mars["site"], "on": "moon"}}, dust)
    assert writer.files("yard")["dust"] == "{data}/physics/dust.json"
    # the lit shed: its row kinds alone light the tower only; its concept's light lights the core in its blue at half
    # strength, four monitors on two items as faint emitters, and the two whole-room panels on their walls
    from score.review import plans
    from score.stages.scene_record import concept_light
    assert concept_light.KEPT_LIGHT == plans.KEPT_LIGHT
    lit = {**WRITTEN, "items": [["TOWER", 6.0, 1.0, 1.0, 1.0, None, "item"],
                                ["SWITCH", 0.5, 3.0, 0.1, 0.1, None, "item"],
                                ["CORE", 3.0, 2.0, 1.0, 1.0, None, "item"],
                                ["ENGINE", 1.0, 1.0, 2.0, 1.0, None, "item"],
                                ["SKY", 0.0, 0.0, 1.0, 1.0, None, "item"],
                                ["SCREENS", 1.0, 4.0, 3.0, 0.5, None, "item"],
                                ["SCREENS 2", 5.0, 4.0, 2.0, 0.5, None, "item"],
                                ["PANEL", 0.5, 0.5, 7.0, 5.0, None, "item"],
                                ["WEST PANEL", 0.5, 0.5, 7.0, 5.0, None, "item"]],
           "rows": {"TOWER": ["floodlight_tower"], "SWITCH": ["light_switch"], "CORE": ["core"], "ENGINE": ["engine"],
                    "SKY": ["sky"], "SCREENS": ["screens"], "SCREENS 2": ["screens"], "PANEL": ["wall_panel"],
                    "WEST PANEL": ["west_panel"]},
           "shapes": {"TOWER": {"shape": "rect", "tall": 10.0, "base": 0.0},
                      "CORE": {"shape": "rect", "tall": 3.0, "base": 0.0}}}
    lit_rows = [{"id": "floodlight_tower", "name": "floodlight tower", "noun": "tower", "anchor": "on:yard",
                 "size": [1.0, 1.0, 10.0]},
                {"id": "light_switch", "name": "light switch", "noun": "switch", "anchor": "wall"},
                {"id": "core", "name": "energy core", "noun": "core", "anchor": "floor", "size": [1.0, 1.0, 3.0]},
                {"id": "engine", "name": "engine", "noun": "engine", "anchor": "floor", "size": [2.0, 1.0, 1.0]},
                {"id": "sky", "name": "starfield", "noun": "sky", "anchor": "sky"},
                {"id": "screens", "name": "wall monitors", "noun": "monitor", "anchor": "floor", "count": 4},
                {"id": "wall_panel", "name": "wall panel", "noun": "panel", "anchor": "wall", "size": [8.0, 6.0, 3.0],
                 "count": 3},
                {"id": "west_panel", "name": "wall panel", "noun": "panel", "anchor": "wall", "size": [8.0, 6.0, 3.0]}]
    panel_glow = {"glows": True, "glowing": "its lamps", "colour": "#ffeedd", "brightness": 1.0}
    concept = {"rows": {"core": {"glows": True, "glowing": "its column", "colour": "#44aaff", "brightness": 0.5},
                        "screens": {"glows": True, "glowing": "screens", "colour": "#44aaff", "brightness": 0.5},
                        "engine": {"glows": False, "glowing": "", "colour": "", "brightness": 0},
                        "sky": {"glows": True, "glowing": "stars", "colour": "#ffffff", "brightness": 0.4},
                        "wall_panel": panel_glow, "west_panel": panel_glow},
               "scene": {"daylight": False, "unseen": False, "unseen_colour": ""}}
    walls = {"relations": [{"item": "PANEL", "row": "wall_panel", "how": "wall", "side": 1, "spot": [8.0, 3.0],
                            "wall": {"from": [8.0, 0.0], "to": [8.0, 6.0], "thick": 0.2}, "why": "its free wall"},
                           {"item": "WEST PANEL", "row": "west_panel", "how": "wall", "side": 1, "spot": [0.0, 3.0],
                            "wall": {"from": [0.0, 6.0], "to": [0.0, 0.0], "thick": 0.2}, "why": "its free wall"}]}
    with tempfile.TemporaryDirectory() as folder:
        folder = pathlib.Path(folder)
        (folder / "inventory.json").write_text(json.dumps({"scene": "shed", "rows": lit_rows}))
        (folder / "light.json").write_text(json.dumps(concept))
        given = {"inventory": folder / "inventory.json", "row kinds": REPO / "data/checks/row-kinds.json",
                 "lamp library": REPO / "data/library/lamps.json"}
        [tower] = writer.lights(lit, given, walls)  # the switch, the core and the panels by their row kinds: none
        found = writer.lights(lit, {**given, "concept light": folder / "light.json"}, walls)
        [full] = writer.item_lamps(lit["items"][2], {**lit_rows[2], "row_kind": "machine"}, lit_rows, lit,
                                   writer.library_lamps(), given["lamp library"])
        [bulb] = writer.item_lamps(lit["items"][5], {**lit_rows[5], "id": "bulbs", "name": "bulbs", "noun": "bulb"},
                                   lit_rows, lit, writer.library_lamps(), given["lamp library"],
                                   {**concept["rows"]["screens"], "glowing": "bulbs"})
    assert tower["at"][1] == 9.5 and "floodlight_tower" in tower["from"] and tower["range"] == 14.25, tower
    by_row = {}
    for light in found:
        by_row.setdefault(light["row"], []).append(light)
    assert sorted(by_row) == ["core", "floodlight_tower", "screens", "wall_panel", "west_panel"], sorted(by_row)
    assert by_row["floodlight_tower"] == [tower], by_row["floodlight_tower"]
    [core] = by_row["core"]
    assert core["colour"] == "#44aaff" and "its column" in core["from"] and "core" in core["from"], core
    assert core["energy"] == round(full["energy"] / 2, 4) and core["at"] == full["at"], (core, full)
    # four counted screens on two items (3 m from x 1, 2 m from x 5): two lamps along each, at 1.75, 3.25, 5.5 and
    # 6.5 m (x -2.25, -0.75, 1.5, 2.5 on the shed's 8 m), each a faint emitter at 0.1 of the lamp (lamps.json
    # `glowing`), never one lamp an item as a room light
    screens = by_row["screens"]
    assert [screen["at"][0] for screen in screens] == [-2.25, -0.75, 1.5, 2.5], screens
    assert all("faint emitter" in screen["from"] and abs(screen["energy"] - bulb["energy"] * 0.1) <= 1e-4
               for screen in screens), (screens, bulb)
    # the west panel's one lamp at plan (0.2, 3) 1.5 m up; the east panel's three at plan (7.8, 1, 3 and 5)
    (spot,), floor = writer.in_frame(lit, [[0.2, 3.0]], 1.5)
    [west] = by_row["west_panel"]
    assert west["at"] == [spot[0], floor, spot[1]], west
    spots, floor = writer.in_frame(lit, [[7.8, 1.0], [7.8, 3.0], [7.8, 5.0]], 1.5)
    assert [found_at["at"] for found_at in by_row["wall_panel"]] == [[spot[0], floor, spot[1]] for spot in spots], \
        by_row["wall_panel"]
    assert gates.lamp_faults({"lights": found}, lit) == [], gates.lamp_faults({"lights": found}, lit)
    moved = [{**light, "at": [light["at"][0] + 1.0, *light["at"][1:]]} if light is west else light for light in found]
    assert gates.lamp_faults({"lights": moved}, lit) == ["the light of plan item 'WEST PANEL' stands off its wall"]
    # a door whose concept shows its keypad glowing is a faint emitter, its light a lamp still
    door = {"id": "sliding_door", "name": "sliding door", "noun": "door"}
    assert writer.glow_share(door, {"glowing": "keypad"}, given["lamp library"]) == (0.1, "emitter")
    assert writer.glow_share(door, {"glowing": "light panel"}, given["lamp library"]) == (1.0, "source")


class Turned:
    """An object's turn: `writer.yaw_turn` laying its row's long side along plan `way` (a facing letter or a
    vector); `signed` False takes a quaternion and its negative as one turn, and `not_` asks that it is not that turn."""

    def __init__(self, way, signed=True, not_=False):
        self.way, self.signed, self.not_ = way, signed, not_

    def holds(self, rotation, design, size):
        way = writer.FACING_WAY[self.way] if isinstance(self.way, str) else self.way
        wanted = writer.yaw_turn(design, way, size)
        same = rotation == wanted if self.signed else bool(np.isclose(abs(np.dot(rotation, wanted)), 1.0))
        return same != self.not_


class Starts:
    """A said reason that begins with `text`."""

    def __init__(self, text):
        self.text = text

    def holds(self, said, design, size):
        return isinstance(said, str) and said.startswith(self.text)


class Near:
    """A point within `within` (one tolerance an axis) of `point`."""

    def __init__(self, point, within):
        self.point, self.within = point, within

    def holds(self, at, design, size):
        return isinstance(at, list) and bool(np.all(np.abs(np.subtract(at, self.point)) <= self.within))


class Says:
    """A said text that holds `text`."""

    def __init__(self, text):
        self.text = text

    def holds(self, said, design, size):
        return isinstance(said, str) and self.text in said


ABSENT = object()


# Each case: a plan, its hand-in rows, its relations (None: none kept) and the shell's own rows by part (None: none),
# the objects and shell pieces it lays with what each must hold (`field`, `field.sub` or `field.<index>`): a value
# equal, a Turned turn, a Starts reason, ABSENT, or a tuple of these all; and each row named with exactly the pieces
# that name it, no more (none: the row names no piece).
#  - past its edge (2026-10-26, floor_fit.past_edge): on a 20 by 20 m plan (centred: plan (x, y) is place (x - 10,
#    y - 10)) the 30 x 30 m building's strip at the right edge, (18, 0) 2 x 10 m (a corner: it runs along the right
#    edge), stands at plan (35, 5), its body 20 to 50 m east, facing west; the 40 x 20 m one's strip at the foot,
#    (5, 18) 10 x 2 m, at plan (10, 30), 20 to 40 m south, facing north; a kiosk on the ground off the edge stays
#    centred on its item.
#  - a run along its long side (#36, 2026-10-31: the walkway's 12 m ceiling ducts turned by their facing across the
#    hall): a duct long on the ground at an item long the other way to its facing lies along the item (its facing's
#    way turned a quarter, writer.item_way); a chair, not long, keeps its facing on its box a little deeper than wide.
#  - a facade (street, 2026-10-29): on a 6 x 30 m plan (place (x, z) is plan (x - 3, y - 15)) its 3 m deep facade the
#    plan writer left on the walls item stands past the W edge, its middle 1.5 m out, at place (-4.5, 0), its long
#    side along the edge; the AC unit on it names the facade's object alone of the walls item's (its holder row), not
#    the crate also left there, which stands marked unplaced; a door with no relation is marked as filling an
#    opening; a row its relations name nothing holding is marked unheld.
#  - doors at their spots (street, #36: three restaurant doors on one 1.74 m item laid evenly 0.58 m apart, their
#    recesses in one another): where the relation gives each piece its `spots` (score/review/holders face_spots),
#    each door stands at its own, place z -1.4, 0, 1.4, x -0.95 (plan 2.05).
#  - a ramp (settle@airlock, 2026-10-30: its end in its porch deck): with its relation (holders up_to_level), on a 20
#    by 20 m plan it stands at the relation's spot, plan (8.9, 12), place (-1.1, 2), its long side turned up the way
#    east, and its `on` gives the assembly the level's edge at place x -0.1, the way up +x and the level's 0.2 m top.
# The shed (WRITTEN) for its shell's own rows: a flight down from its floor through a hatch in its deck (DOWN), its
# roof cut round an opening (HOLED), and a doorway item on its north door, a crate and bags on a 0.2 m porch deck,
# a box and bags under a 2.5 m loft, bags off every deck on the ground (DECKED: the bags' plan base -0.2 m).
DOWN = {**WRITTEN, "stairs": [*WRITTEN["stairs"], {"kind": "stair", "points": [[1.0, 4.0], [2.0, 4.0], [2.0, 5.0],
                                                                             [1.0, 5.0]],
                                                   "from": 0.0, "to": -1.0, "angle": 90.0, "steps": 5}]}
HOLED = {**DOWN, "roofs": [{**WRITTEN["roofs"][0], "openings": [{"points": [[5, 1], [7, 1], [7, 2], [5, 2]]}]}]}
OPENING_ROWS = {"opening": ["corridor_opening", "floor_hatch", "roof_opening"]}
POSTS = {"id": "posts", "route": "plan", "part": "structure", "name": "posts", "size": [0.2, 0.2, 2.0], "count": 2}
DECKED = {**WRITTEN, "items": [*WRITTEN["items"], ["DOORWAY 1", 3.4, 0.0, 1.2, 0.2, None, "item"],
                               ["CRATE 1", 6.0, 4.0, 1.0, 1.0, None, "item"],
                               ["BOX 1", 1.0, 4.0, 1.0, 1.0, None, "item"],
                               ["BAGS 1", 6.0, 4.0, 1.0, 1.0, None, "item"],
                               ["BAGS 2", 1.0, 4.0, 1.0, 1.0, None, "item"],
                               ["BAGS 3", 9.0, 4.0, 1.0, 1.0, None, "item"]],
          "shapes": {**WRITTEN["shapes"], **{f"BAGS {number}": {"shape": "rect", "tall": 0.2, "base": -0.2}
                                             for number in (1, 2, 3)}},
          "rows": {**WRITTEN["rows"], "DOORWAY 1": ["doorway"], "CRATE 1": ["crate"], "BOX 1": ["box"],
                   "BAGS 1": ["bag_deck"], "BAGS 2": ["bag_floor"], "BAGS 3": ["bag_ground"]},
          "levels": [*WRITTEN["levels"],
                     {"name": "porch deck", "height": 0.2, "points": [[5.0, 3.0], [8.0, 3.0], [8.0, 6.0], [5.0, 6.0]]},
                     {"name": "loft", "height": 2.5, "points": [[0.0, 3.0], [4.0, 3.0], [4.0, 6.0], [0.0, 6.0]]}]}
# A far row (2026-10-26: the square's city skyline had no maker; no scene of the environment stands there, so it is
# ordinary objects, prepare's groups.far_made) on a 20 x 20 m plan whose crate, drum and bench boxes fix its
# projection (up the picture is away): the city's 50 m read tall over its 50 px box at the view's focal length
# (FAR_FOCAL, 595.9 m) is its distance, straight up the picture, its middle at plan (10, 10 - FAR_FOCAL), place
# (0, -FAR_FOCAL); its two pieces 100 m apart on its 200 m, square to that bearing. The lake, terrain, is no far row.
FAR_PLAN = {"w": 20.0, "d": 20.0, "items": [["CRATE 1", 4.5, 14.5, 1, 1, None, "item"],
                                            ["DRUM 1", 14.5, 14.5, 1, 1, None, "item"],
                                            ["BENCH 1", 9.5, 4.5, 1, 1, None, "item"]],
            "rows": {"CRATE 1": ["crate"], "DRUM 1": ["drum"], "BENCH 1": ["bench"]}}
FAR_ROWS = [*[{"id": name, "anchor": "floor", "noun": name, "count": 1, "size": [1, 1, 1], "boxes": [box]}
              for name, box in (("crate", [240, 700, 260, 750]), ("drum", [740, 700, 760, 750]),
                                ("bench", [490, 200, 510, 250]))],
            {"id": "city", "anchor": "ground", "part": "backdrop", "route": "prop", "size": [100.0, 100.0, 50.0],
             "box": [450, 100, 550, 150], "far": {"pieces": 2, "length": 200.0}},
            {"id": "lake", "anchor": "ground", "part": "backdrop", "route": "prop", "terrain": True,
             "size": [50.0, 50.0, 1.0]}]
FAR_FOCAL = 500 / math.tan(math.radians(far.VIEW_FOV / 2))
FACADE_PLAN = {"w": 6.0, "d": 30.0}


# What holds each object, from the place's relations (issue #72), on a 20 by 20 m plan (place (x, z) is plan
# (x - 10, y - 10)): the door the plan writer left on the walls item in its opening at plan (5, 0); the garage door
# against its module's S face, resting leaning; the wall lamp against the west wall 2 m up; a lamp hung from the
# roof; a chair before the module; a spacesuit hanging within it, an oven under it; a stage screen its floor
# relation stands at 0 over its 3.3 m plan base. Its row kinds for the gates: the hung lamp anchored to the ceiling,
# the chair a seat at the module.
RELATED = {"w": 20.0, "d": 20.0, "items": [["ON THE WALLS AND CEILING", 0.0, 0.0, 20.0, 20.0, None, "item"],
                                           ["MODULE 1", 8.0, 2.0, 6.0, 6.0, None, "item"],
                                           ["GARAGE DOOR 1", 4.0, 9.0, 3.0, 3.0, None, "item"],
                                           ["SUIT 1", 9.0, 3.0, 0.5, 0.5, None, "item"],
                                           ["OVEN 1", 12.0, 3.0, 0.5, 0.5, None, "item"],
                                           ["HUNG 1", 2.0, 2.0, 1.0, 1.0, None, "item"],
                                           ["CHAIR 1", 10.0, 12.0, 2.0, 2.0, None, "item"],
                                           ["STAGE 1", 15.0, 6.0, 1.0, 1.0, None, "item"]],
           "rows": {"ON THE WALLS AND CEILING": ["door", "lamp"], "MODULE 1": ["module"],
                    "GARAGE DOOR 1": ["garage_door"], "SUIT 1": ["suit"], "OVEN 1": ["oven"], "HUNG 1": ["hung"],
                    "CHAIR 1": ["chair"], "STAGE 1": ["stage"]},
           "shapes": {"STAGE 1": {"shape": "rect", "base": 3.3}}}
RELATED_ROWS = [{"id": name, "anchor": "floor", "route": "prop", "size": size}
                for name, size in (("door", [1.2, 0.1, 2.1]), ("lamp", [0.3, 0.2, 0.3]), ("module", [6.0, 6.0, 6.0]),
                                   ("garage_door", [3.0, 0.2, 3.0]), ("suit", [0.5, 0.4, 1.8]),
                                   ("oven", [0.5, 0.5, 0.5]), ("hung", [0.4, 0.4, 0.5]), ("chair", [0.6, 0.6, 1.0]),
                                   ("stage", [1.0, 1.0, 1.0]), ("crate", [1.0, 1.0, 1.0]))]
RELATIONS = {"relations": [
    *[{"item": f"CRATE {number}", "row": "crate", "how": "floor", "why": "on the place's floor"} for number in (1, 2)],
    {"item": "ON THE WALLS AND CEILING", "row": "door", "how": "in", "why": "in the plan's door opening 1",
     "opening": {"at": [5.0, 0.0], "wide": 1.4, "sill": 0.0, "head": 2.2},
     "wall": {"from": [0.0, 0.0], "to": [20.0, 0.0], "thick": 0.2}},
    {"item": "ON THE WALLS AND CEILING", "row": "lamp", "how": "wall", "why": "against the wall nearest",
     "wall": {"from": [0.0, 20.0], "to": [0.0, 0.0], "thick": 0.2}, "side": 1, "spot": [0.0, 10.0], "height": 2.0},
    {"item": "HUNG 1", "row": "hung", "how": "ceiling", "to roof": True, "why": "on the place's ceiling"},
    {"item": "CHAIR 1", "row": "chair", "how": "floor", "beside": "MODULE 1", "holder row": "module",
     "pieces": [{"how": "floor", "spot": [11.0, 8.4], "way": [1.0, 0.0], "why": "before module's S side"}],
     "why": "before module"},
    {"item": "GARAGE DOOR 1", "row": "garage_door", "how": "face", "holder": "MODULE 1", "holder row": "module",
     "face": "S", "why": "against module's side", "recess": {"room": 0.55, "room_way": [-1.0, 0.0]},
     "rests": "leaning"},
    {"item": "SUIT 1", "row": "suit", "how": "within", "holder": "MODULE 1", "why": "within module", "hangs": True},
    {"item": "OVEN 1", "row": "oven", "how": "within", "holder": "MODULE 1", "why": "under module", "under": True},
    {"item": "STAGE 1", "row": "stage", "how": "floor", "height": 0.0, "why": "on what is under it"}]}
RELATED_KINDS = {"hung": {"id": "hung", "anchor": "ceiling"},
                 "chair": {"id": "chair", "noun": "chair", "where": "at the module"}}
TURNED_LAMP = writer.yaw_turn(RELATED, (0.0, -1.0), None)
OVER = "stands 1.00 m over the floor with nothing under it, its row on the floor"
SQUARE = [[0.0, 0.0], [20.0, 0.0], [20.0, 20.0], [0.0, 20.0]]
RING = [[0.0, 2.757], [2.757, 0.0], [6.829, 0.0], [9.823, 2.994], [9.823, 6.592], [7.906, 9.101], [4.308, 9.823],
        [2.757, 9.101], [1.325, 7.669], [0.0, 5.989]]  # habitat's walls round its room, 2026-11-07


def crate(number, x, y, height):
    """A crate laid at plan (x, y) of RELATED, `height` over its floor, as plan item 'CRATE <number>'."""
    return {"name": f"crate_{number}", "row": "crate", "kind": "object", "at": [x - 10.0, height, y - 10.0],
            "rotation": writer.yaw_turn(RELATED, (1.0, 0.0), [1.0, 1.0, 1.0]),
            "from": f"plan item 'CRATE {number}', inventory row crate: piece {number} of the row"}


def walled(walls):
    """RELATED walled by `walls`, each [from, to] 0.2 m thick."""
    return {**RELATED, "walls": [{"from": start, "to": end, "thick": 0.2} for start, end in walls]}


def wall_span(first, second):
    """A wall thing's `on.span` running from plan `first` to `second` of RELATED, in the place's frame."""
    return [[first[0] - 10.0, first[1] - 10.0], [second[0] - 10.0, second[1] - 10.0]]


# Each row: what the laid objects' gates (judge_laid_as_designed's) are asked of, and the faults they find in order.
# An edit may stand the objects on another `plan` or under other `relations`, add row `kinds`, `set` an object's
# fields (`field` or `field.sub`), `move` it by a place offset, `copy` it under a new name moved by one, or `add`
# objects.
LAID_FAULTS = [
    ("as laid", {}, []),
    ("the wall lamp turned to its wall", {"set": {"lamp_1": {"rotation": TURNED_LAMP}}},
     ["lamp_1 faces its wall, its back to the room"]),
    ("two lamps at one spot", {"copy": [["lamp_1", "lamp_2", [0.0, 0.0, 0.0]]]},
     ["lamp_1 and lamp_2 of row lamp stand at one spot",
      "lamp_1 and lamp_2 on the walls stand 0.20 m inside each other at their built sizes"]),
    ("the hung lamp 1 m lower", {"move": {"hung_1": [0.0, -1.0, 0.0]}},
     ["hung_1's top stands 1.99 m up, its roof's underside 3.00 m over it"]),
    ("a second lamp 0.1 m along the west wall", {"copy": [["lamp_1", "lamp_9", [0.0, 0.0, 0.1]]]},
     ["lamp_1 and lamp_9 on the walls stand 0.20 m inside each other at their built sizes"]),
    ("a second lamp touching the first", {"copy": [["lamp_1", "lamp_9", [0.0, 0.0, 0.32]]]}, []),
    ("a second lamp 0.1 m along stood over the first", {"copy": [["lamp_1", "lamp_9", [0.0, 0.35, 0.1]]]}, []),
    ("the chair 1.2 m off its module", {"set": {"chair_1": {"at": [1.0, 0.0, -0.5]}}},
     ["chair_1 stands 1.20 m from MODULE 1, its words 'at the module'"]),
    ("crates on the floor and on the module's top", {"add": [crate(1, 15.0, 15.0, 0.0), crate(2, 11.0, 5.0, 6.0)]},
     []),
    ("a crate 1 m up over nothing", {"add": [crate(1, 15.0, 15.0, 1.0)]}, [f"crate_1 {OVER}"]),
    ("a crate 1 m up on a crate of its own row", {"add": [crate(1, 15.0, 15.0, 0.0), crate(2, 15.0, 15.0, 1.0)]},
     [f"crate_2 {OVER}"]),
    ("a crate on a crate of a row that piles", {"add": [crate(1, 15.0, 15.0, 0.0), crate(2, 15.0, 15.0, 1.0)],
                                                "kinds": {"crate": {"id": "crate", "size_words": "a stack of crates"}}},
     []),
    ("crates on a 1 m deck and half way up a flight",
     {"plan": {**RELATED, "levels": [{"height": 1.0, "points": [[14.0, 14.0], [18.0, 14.0], [18.0, 18.0],
                                                                [14.0, 18.0]]}],
               "stairs": [{"points": [[14.0, 1.0], [18.0, 1.0], [18.0, 3.0], [14.0, 3.0]], "from": 0.0, "to": 2.0}]},
      "add": [crate(1, 16.0, 16.0, 1.0), crate(2, 16.0, 2.0, 1.0)]}, []),
    *[(f"a wall lamp laid {how}", {"plan": walled([[[0.0, 0.0], [20.0, 0.0]], [[0.0, 0.0], [0.0, 20.0]],
                                                   [[10.0, 20.0], [15.0, 20.0]], [[15.0, 20.0], [19.698, 21.71]]]),
                                   "set": {"lamp_1": {"on.span": span}}}, faults)
      for how, span, faults in (
          ("flat along a wall", wall_span((0.1, 2.0), (0.1, 6.0)), []),
          ("as a chord over walls 20 degrees apart", wall_span((12.0, 19.9), (18.0, 21.0)), []),
          ("round a corner", wall_span((0.1, 4.0), (4.0, 0.1)),
           ["lamp_1 is laid round a corner of its walls, its ends on two of their straight runs"]))],
    ("a wall lamp laid as a chord over the facets round a closed room",
     {"plan": walled(zip(RING, RING[1:] + RING[:1])), "set": {"lamp_1": {"on.span": wall_span((3.285, 9.056),
                                                                                              (1.043, 7.062))}}},
     []),
    *[(f"a crate hung {how} between the module and a crate", {
        "relations": {"relations": [
            {"item": "CRATE 3", "row": "crate", "how": "hung", "holders": ["MODULE 1", "CRATE 4"],
             "why": "hung between them"},
            {"item": "CRATE 4", "row": "crate", "how": "floor", "why": "on the place's floor"}]},
        "add": [crate(3, 15.0, 15.0, height), crate(4, 16.0, 2.0, 0.0)]}, faults)
      for how, height, faults in (
          ("0.5 m up", 0.5, []),
          ("3 m up", 3.0, ["crate_3 hangs 3.00 m over the floor between MODULE 1 and CRATE 4, 1 of them standing that "
                           "high"]))],
]


PLACED = [
    ("past its edge",
     {"w": 20.0, "d": 20.0, "items": [["RIGHT 1", 18.0, 0.0, 2.0, 10.0, "W", "item"],
                                      ["FRONT 1", 5.0, 18.0, 10.0, 2.0, "N", "item"],
                                      ["KIOSK 1", 9.0, 9.0, 2.0, 2.0, "N", "item"]],
      "rows": {"RIGHT 1": ["right"], "FRONT 1": ["front"], "KIOSK 1": ["kiosk"]}},
     [{"id": name, "anchor": "ground", "route": "shell", "size": size}
      for name, size in (("right", [30.0, 30.0, 20.0]), ("front", [40.0, 20.0, 15.0]), ("kiosk", [2, 2, 3]))],
     None, None,
     {"right_1": {"at": [25.0, 0.0, -5.0], "rotation": Turned("W")},
      "front_1": {"at": [0.0, 0.0, 20.0], "rotation": Turned("N")},
      "kiosk_1": {"at": [0.0, 0.0, 0.0]}},
     {"right": ["right_1"], "front": ["front_1"], "kiosk": ["kiosk_1"]}, None, None),
    ("a run along its long side",
     {"w": 2.0, "d": 12.0, "items": [["DUCT 1", 0.5, 0.0, 0.14, 12.0, "S", "item"],
                                     ["CHAIR 1", 1.2, 5.0, 0.5, 0.6, "S", "item"]],
      "rows": {"DUCT 1": ["duct"], "CHAIR 1": ["chair"]}},
     [{"id": "duct", "route": "prop", "size": [0.5, 12.0, 0.3]},
      {"id": "chair", "route": "prop", "size": [0.5, 0.55, 0.9]}],
     None, None,
     {"duct_1": {"rotation": (Turned((0.0, -1.0), signed=False), Turned("S", signed=False, not_=True))},
      "chair_1": {"rotation": Turned("S", signed=False)}},
     {"duct": ["duct_1"], "chair": ["chair_1"]}, None, None),
    ("a facade past its edge",
     {**FACADE_PLAN, "items": [["ON THE WALLS AND CEILING", 0.0, 0.0, 6.0, 30.0, None, "item"],
                               ["AC 1", 0.5, 10.0, 0.8, 0.4, None, "item"], ["DOOR 1", 5.0, 5.0, 1.0, 0.1, None, "item"],
                               ["LAMP 1", 2.0, 2.0, 0.3, 0.3, None, "item"]],
      "rows": {"ON THE WALLS AND CEILING": ["facade", "crate"], "AC 1": ["ac"], "DOOR 1": ["door"],
               "LAMP 1": ["lamp"]}},
     [{"id": name, "anchor": "floor", "route": "prop", "size": size, "noun": noun}
      for name, size, noun in (("facade", [3.0, 36.0, 24.0], "facade"), ("crate", [1.0, 1.0, 1.0], "crate"),
                               ("ac", [0.8, 0.4, 0.6], "air conditioner"), ("door", [1.0, 0.1, 2.1], "door"),
                               ("lamp", [0.3, 0.3, 0.3], "lamp"))],
     {"relations": [
         {"item": "ON THE WALLS AND CEILING", "row": "facade", "how": "edge", "edge": "W", "spot": [0.0, 15.0],
          "why": "past the plan's W edge"},
         {"item": "AC 1", "row": "ac", "how": "face", "holder": "ON THE WALLS AND CEILING", "holder row": "facade",
          "face": "E", "why": "against facade's face toward the place"}],
      "unheld": [{"item": "LAMP 1", "row": "lamp", "why": "its holder stage is neither laid nor a wall"}]},
     None,
     {"facade_1": {"at": [-4.5, 0.0, 0.0], "unplaced": ABSENT, "rotation": Turned((0.0, 1.0))},
      "ac_1": {"on.holder": ["facade_1"], "on.out": [1.0, 0.0]},
      "crate_1": {"unplaced": Starts("the plan writer left it")},
      "door_1": {"fills": True},
      "lamp_1": {"unheld": Starts("its holder stage")}},
     {"facade": ["facade_1"], "ac": ["ac_1"], "crate": ["crate_1"], "door": ["door_1"], "lamp": ["lamp_1"]}, None,
     None),
    ("doors at their spots",
     {**FACADE_PLAN, "items": [["ON THE WALLS AND CEILING", 0.0, 0.0, 6.0, 30.0, None, "item"],
                               ["DOOR 1", 1.8, 14.13, 0.5, 1.74, "E", "item"]],
      "rows": {"ON THE WALLS AND CEILING": ["facade"], "DOOR 1": ["door"]}},
     [{"id": "facade", "anchor": "floor", "route": "prop", "size": [3.0, 36.0, 24.0], "noun": "facade"},
      {"id": "door", "anchor": "on:facade", "route": "prop", "size": [1.0, 0.1, 2.1], "noun": "door", "count": 3}],
     {"relations": [
         {"item": "ON THE WALLS AND CEILING", "row": "facade", "how": "edge", "edge": "W", "spot": [0.0, 15.0],
          "why": "past the plan's W edge"},
         {"item": "DOOR 1", "row": "door", "how": "face", "holder": "ON THE WALLS AND CEILING", "holder row": "facade",
          "face": "E", "why": "against facade's face toward the place",
          "spots": [[2.05, 13.6], [2.05, 15.0], [2.05, 16.4]]}]},
     None,
     {"door_1": {"at": [-0.95, 0.0, -1.4]}, "door_2": {"at": [-0.95, 0.0, 0.0]}, "door_3": {"at": [-0.95, 0.0, 1.4]}},
     {"door": ["door_1", "door_2", "door_3"]}, None, None),
    ("a ramp up to its level's edge",
     {"w": 20.0, "d": 20.0, "items": [["RAMP 1", 8.0, 9.0, 1.2, 2.0, None, "item"]], "rows": {"RAMP 1": ["ramp"]}},
     [{"id": "ramp", "anchor": "ground", "route": "shell", "size": [1.2, 2.0, 0.2], "noun": "ramp"}],
     {"relations": [{"item": "RAMP 1", "row": "ramp", "how": "ramp", "spot": [8.9, 12.0], "way": [1.0, 0.0],
                     "edge": [[9.9, 14.0], [9.9, 8.0]], "height": 0.2, "why": "up to the porch deck"}]},
     None,
     {"ramp_1": {"at": [-1.1, 0.0, 2.0], "rotation": Turned((1.0, 0.0)),
                 "on": {"how": "ramp", "edge": [[-0.1, 4.0], [-0.1, -2.0]], "up": [1.0, 0.0], "top": 0.2,
                        "why": "up to the porch deck"}}},
     {"ramp": ["ramp_1"]}, None, None),
    ("opening rows with no item named at a cut their words fit, and the shell's pillars", DOWN, [POSTS], None,
     OPENING_ROWS,
     {"posts_1": {"row": "posts", "plain": "shell", "surface": None, "surface_missing": Starts("shed: ")},
      "posts_2": {"row": "posts", "plain": "shell", "surface": None, "surface_missing": Starts("shed: ")}},
     {"corridor_opening": ["wall_1_3"], "floor_hatch": ["stair_2"], "roof_opening": [],
      "posts": ["posts_1", "posts_2"]}, None, None),
    ("a roof's opening named on its cut", HOLED, [], None, OPENING_ROWS, {}, {"roof_opening": ["roof_1"]}, None, None),
    ("a roof's opening named on its cut before its panels row", HOLED, [], None, {**OPENING_ROWS, "roof": ["roof_panels"]},
     {}, {"roof_opening": ["roof_1"]}, None, None),
    ("a shell the earth seed lays lays no pillars", {**WRITTEN, "shell": "kit", "inside": True}, [POSTS], None, None,
     {}, {"posts": []}, None, None),
    ("an opening row on the lintel over its item's cut, things on a low deck on it", DECKED,
     [{"id": name, "route": "prop", "size": [1.0, 1.0, 0.5]}
      for name in ("crate", "box", "bag_deck", "bag_floor", "bag_ground")], None,
     {"wall": ["wall_panels"], "opening": ["doorway", "hatch"]},
     {"wall_1": {"row": "wall_panels"}, "wall_1_3": {"row": "doorway"}, "crate_1": {"at": [2.5, 0.2, 1.5]},
      "box_1": {"at": [-2.5, 0.0, 1.5]}, "bag_deck_1": {"at.1": 0.2}, "bag_floor_1": {"at.1": 0.0},
      "bag_ground_1": {"at.1": -0.2}},
     {"doorway": ["wall_1_3"], "hatch": []}, None, None),
    ("a far row stands far off where its concept box is seen, a run of its pieces", FAR_PLAN, FAR_ROWS, None, None,
     {"city_1": {"at": Near([50.0, 0.0, -FAR_FOCAL], [0.0005, 0.0, 0.1]), "bake": "city_1", "from": Says("far off")},
      "city_2": {"at": Near([-50.0, 0.0, -FAR_FOCAL], [0.0005, 0.0, 0.1]), "bake": "city_1",
                 "from": Says("far off")}},
     {"crate": ["crate_1"], "drum": ["drum_1"], "bench": ["bench_1"], "city": ["city_1", "city_2"], "lake": []},
     {"inventory": {"picture": [1000, 1000], "rows": FAR_ROWS[:4]}, "objects": {"city": {"rows": ["city"]}},
      "unplaced": []}, None),
    ("a far row with no projection to stand it by is named, never laid at its plan item",
     {**FAR_PLAN, "items": [*FAR_PLAN["items"], ["CITY 1", 9.5, 1.0, 2, 2, None, "item"]],
      "rows": {**FAR_PLAN["rows"], "CITY 1": ["city"]}}, FAR_ROWS, None, None, {},
     {"crate": ["crate_1"], "drum": ["drum_1"], "bench": ["bench_1"], "city": []},
     {"inventory": {"picture": [1000, 1000], "rows": [FAR_ROWS[3]]}, "objects": {}, "unplaced": ["city"]}, None),
    ("each object carries what holds it from the place's relations, and its laid-as-designed gates judge it",
     RELATED, RELATED_ROWS, RELATIONS, None,
     {"door_1": {"at": [-5.0, 0.0, -10.0], "on.how": "in", "on.middle": [-5.0, 0.0, -10.0], "on.wide": 1.4,
                 "on.tall": 2.2, "rotation": Turned((1.0, 0.0)), "rests": ABSENT},
      "garage_door_1": {"on.holder": ["module_1"], "on.out": [0.0, 1.0], "rests": "leaning", "on.below": ABSENT,
                        "on.room": 0.55, "on.room_way": [-1.0, 0.0]},
      "lamp_1": {"on.span": [[-9.9, 10.0], [-9.9, -10.0]], "on.out": [1.0, 0.0], "rotation": Turned((0.0, 1.0)),
                 "at.1": 2.0},
      "hung_1": {"at.1": round(3.0 - 0.5 - writer.ROOF_CLEAR, 4)},
      "chair_1": {"at": [1.0, 0.0, -1.6], "beside.holder": ["module_1"]},
      "suit_1": {"on.hangs": True, "on.holder": ["module_1"], "on.under": ABSENT},
      "oven_1": {"on.under": True},
      "stage_1": {"at.1": 0.0}},
     {"door": ["door_1"], "lamp": ["lamp_1"], "garage_door": ["garage_door_1"], "crate": []}, None,
     {"kinds": RELATED_KINDS, "faults": LAID_FAULTS}),
    ("relations derived from another plan than the kept one are left out", RELATED, RELATED_ROWS,
     {**RELATIONS, "plan": "another plan's sha"}, None,
     {"door_1": {"on": ABSENT}, "lamp_1": {"on": ABSENT}}, {}, None,
     {"left out": "the relations were derived from another plan than the kept one (score/review/holders keep)"}),
    *[(f"a wall thing's face ends at the faces of the walls meeting its ends: {how}",
       {"w": 20.0, "d": 20.0, "items": [["ON THE WALLS AND CEILING", 0.0, 0.0, 20.0, 20.0, None, "item"]],
        "rows": {"ON THE WALLS AND CEILING": ["lamp"]},
        "walls": [{"from": start, "to": end, "thick": 0.2} for start, end in walls]},
       [RELATED_ROWS[1]],
       {"relations": [{"item": "ON THE WALLS AND CEILING", "row": "lamp", "how": "wall", "why": "against its wall",
                       "wall": {"from": [20.0, 0.0], "to": [20.0, 20.0], "thick": 0.2}, "side": 1,
                       "spot": [20.0, 10.0], "height": 2.0}]}, None,
       {"lamp_1": {"on.span": span, "on.out": [-1.0, 0.0]}}, {"lamp": ["lamp_1"]}, None, None)
      for how, walls, span in (
          ("a 20 m square of 0.2 m walls", zip(SQUARE, SQUARE[1:] + SQUARE[:1]), [[9.9, -9.9], [9.9, 9.9]]),
          ("a facet meeting it straight on trims nothing", [[[20.0, 0.0], [20.0, 20.0]], [[20.0, 20.0], [20.0, 30.0]]],
           [[9.9, -10.0], [9.9, 10.0]]))],
    ("two lanterns against a thin string hang under it along it",
     {**RELATED, "items": [["STRING 1", 4.0, 4.0, 8.0, 0.1, None, "item"],
                           ["LANTERN 1", 6.0, 14.0, 0.4, 0.4, None, "item"],
                           ["LANTERN 2", 7.0, 14.0, 0.4, 0.4, None, "item"]],
      "rows": {"STRING 1": ["string"], "LANTERN 1": ["lantern"], "LANTERN 2": ["lantern"]}, "shapes": {}},
     [{"id": "string", "anchor": "floor", "route": "prop", "size": [8.0, 0.01, 0.01]},
      {"id": "lantern", "anchor": "floor", "route": "prop", "size": [0.4, 0.4, 0.4]}],
     {"relations": [{"item": f"LANTERN {number}", "row": "lantern", "how": "face", "holder": "STRING 1",
                     "holder row": "string", "face": "S", "why": "against string's side"} for number in (1, 2)]},
     None,
     {"lantern_1": {"on.below": True, "on.along": 0.25, "on.holder": ["string_1"]},
      "lantern_2": {"on.below": True, "on.along": 0.75, "on.holder": ["string_1"]}},
     {"lantern": ["lantern_1", "lantern_2"]}, None, None),
    ("a string hung between two poles names each, one between a pole and nothing laid is held by nothing",
     {**RELATED, "items": [["POLE 1", 2.0, 2.0, 0.5, 0.5, None, "item"], ["POLE 2", 16.0, 2.0, 0.5, 0.5, None, "item"],
                           ["STRING 1", 2.5, 2.0, 13.5, 0.5, None, "item"],
                           ["STRING 2", 2.5, 4.0, 13.5, 0.5, None, "item"]],
      "rows": {"POLE 1": ["pole"], "POLE 2": ["pole"], "STRING 1": ["string"], "STRING 2": ["string"]}, "shapes": {}},
     [{"id": "pole", "anchor": "floor", "route": "prop", "size": [0.5, 0.5, 8.0]},
      {"id": "string", "anchor": "floor", "route": "prop", "size": [13.5, 0.5, 0.5]}],
     {"relations": [{"item": "STRING 1", "row": "string", "how": "hung", "holders": ["POLE 1", "POLE 2"],
                     "holder rows": ["pole", "pole"], "why": "hung between POLE 1 and POLE 2"},
                    {"item": "STRING 2", "row": "string", "how": "hung", "holders": ["POLE 1", "MAST 1"],
                     "holder rows": ["pole", "mast"], "why": "hung between POLE 1 and MAST 1"}]},
     None,
     {"string_1": {"on": {"how": "between", "holder items": ["POLE 1", "POLE 2"], "holder rows": ["pole", "pole"],
                          "why": "hung between POLE 1 and POLE 2", "holder": ["pole_1", "pole_2"]}},
      "string_2": {"on": ABSENT, "unheld": Says("MAST 1")}},
     {"pole": ["pole_1", "pole_2"], "string": ["string_1", "string_2"]}, None, None),
]


@pytest.mark.parametrize("design, rows, relations, shell_rows, expected, laid_rows, far_off, judged",
                         [case[1:] for case in PLACED], ids=[case[0] for case in PLACED])
def test_each_piece_stands_and_is_named_where_its_plan_and_relations_lay_it(tmp_path, design, rows, relations,
                                                                            shell_rows, expected, laid_rows, far_off,
                                                                            judged):
    """Each object and shell piece of a design stands, turns, is named and is marked as its plan item, its kept
    relations and the shell's own rows lay it (the cases in PLACED, worked out by hand): past the plan's edge facing
    in, along its item's long side, at its relation's spot, edge or ramp, naming its holder, or marked unplaced,
    filling or unheld.
    A far row (FAR_PLAN, FAR_ROWS) is laid along the bearing its concept box is seen at, at the distance its read tall
    rises to its box's height in the framework's view, its pieces square to that bearing, waiting on its take's bake;
    one with no projection to stand it by is named unplaced, never placed by guess nor at the plan item its plan laid
    it at too; every row the record lays far off is one `far.far_object` judges far, never a terrain row.
    Break: score/stages/scene_record/far.py: `distance = max(float(size[2]) * focal(picture) / (box[3] - box[1]),`
        -> `distance = max(0.0,`
    Break: score/stages/scene_record/writer.py:
        `spot = np.asarray(placed["at"]) + way * length * ((number - 0.5) / pieces - 0.5)`
        -> `spot = np.asarray(placed["at"])`
    Break: score/stages/scene_record/far.py far_object: `return not row.get("terrain") and` -> `return`
    Break: score/stages/scene_record/writer.py: `spot, way = past_edge_spot(item, design, spot, size)` -> `pass`
    Break: score/stages/scene_record/writer.py: `return np.array([-way[1], way[0]])` -> `return way`
    Break: score/stages/scene_record/writer.py: `return np.asarray(relation["spot"], float) + out * depth / 2,
        np.array([out[1], -out[0]]), base, None` -> `return spot, way, base, None`
    Break: score/stages/scene_record/writer.py: `if rows.get(name) == on.get("holder row", rows.get(name))]` -> `]`
    Break: score/stages/scene_record/writer.py: `if item[0] == WALLS_ITEM and not placed:` -> `if False:`
    Break: score/stages/scene_record/writer.py: `spot = np.asarray(relation["spots"][min(piece,
        len(relation["spots"]) - 1)], float)` -> `pass`
    Break: score/stages/scene_record/writer.py: `return (np.asarray(relation["spot"], float),
        np.asarray(relation["way"], float), base,` -> `return (spot, way, base,`
    2026-10-30: the shell named each opening row on the first free wall piece (the workshop's doorway on wall_2,
    hangar's floor hatch on wall 1's lintel), and laid airlock's sandbags at 0 inside its 0.2 m porch deck. An opening
    row is named on the lintel over the cut its plan item makes (the shed's door at plan (4, 0) cuts wall 1 into its
    foot wall_1, the foot under the door wall_1_2, the lintel wall_1_3 and the rest wall_1_4), and one with no item is
    named on no piece; a crate at the floor on a 0.2 m deck stands on it at 0.2 m, a box at the floor under a 2.5 m
    loft stays at 0 (things may stand under it).
    Break: score/stages/scene_record/writer.py: `return name if over[-1] == 0 else f"{name}_{over[-1] + 1}"` ->
        `return name if over[0] == 0 else f"{name}_{over[0] + 1}"`
    Break: score/stages/scene_record/writer.py: `if base else deck_height(design, spot)` -> `if base else base`
    Break: score/stages/scene_record/writer.py: `0.0 < float(level.get("height") or 0.0) <= design_shell.SLAB +
        DECK_BELOW and` -> `0.0 < float(level.get("height") or 0.0) and`
    A piece whose plan base lies below the floor-lying level at its spot stands on that level (settle@airlock,
    checkout 67: its sandbags' -0.2 m ground base buried them in the 0 m floor deck): -0.2 m bags on the 0.2 m deck
    stand at 0.2, under the loft on the floor at 0, off every deck on the ground at -0.2.
    Break: score/stages/scene_record/writer.py: `height = floor_lift(design, spot, base) if base else` ->
        `height = base if base else`
    Break: score/stages/scene_record/writer.py floor_lift: `return max([base] + [` -> `return max([0.0] + [`
    An opening row with no plan item of its own (2026-11-05) is named by its words on a free piece at an opening the
    shell cuts: the lab's corridor openings on the lintel over the plan's own door (wall_1_3), the hangar's floor
    hatch on the flight going down through its deck's hatch (stair_2), its roof opening on a roof cut round its
    openings, and on nothing while its roof has none; the shell's own pillars stand in the place's frame, named
    their row, painted (here named missing: no library), and none where the earth seed lays the shell.
    Break: score/stages/scene_record/writer.py: `if words & FLOOR_WORDS:` -> `if False:`
    Break: score/stages/scene_record/writer.py: `name_open_cuts(design, shelled + flights, (rows or {}).get("opening",
        []))` -> `pass`
    Break: score/stages/scene_record/writer.py: `if not inside(design) or design_shell.laid_for(design):` ->
        `if not inside(design):`
    A roof with both its panels row and an opening names the opening on its cut (hangar's roof_opening, 2026-11-06).
    Break: score/stages/scene_record/writer.py shell: `name_open_cuts(design, found, (rows or {}).get("opening", []))`
        -> `pass`
    Each object carries what holds it, read through the place's kept relations (the RELATED cases), and the
    laid-as-designed gates judge the laid objects and each edit of them in LAID_FAULTS.
    Issue #72: the record carries each object's relation (score/review/holders) for the assembly to lay it by. On a
    20 by 20 m plan (place (x, z) is plan (x - 10, y - 10)): the door the plan writer left on the walls item stands in
    its opening at plan (5, 0), place (-5, -10), turned along its wall, `in` with its 1.4 m width and 2.2 m height;
    the garage door against its module's S face names the module's object and points out +z; the wall lamp against
    the west wall's room face, the face 0.1 m in at x -9.9, pointing out +x. Relations derived from another plan
    than the kept one are left out, with why, and the place laid as drawn.
    Break: score/stages/earth_seed/design_shell.py relations_read: `if relations.get("plan") != hashlib.sha256(...)
        .hexdigest():` -> `if False:`
    Break: score/stages/scene_record/writer.py: `spot, way, height, on = related(design, relation, spot, way,
        height, size, piece)` -> `pass`
    Break: score/stages/scene_record/writer.py: `on["holder"] = names` -> `pass`
    Break: score/stages/scene_record/writer.py: `found["room"] = float(recess["room"])` -> `pass`
    Break: score/stages/scene_record/writer.py: `**({"hangs": True} if relation.get("hangs") else {}),` -> `` (the
        docking airlock's spacesuit, hanging in its locker, laid as standing in it)
    Break: score/stages/scene_record/writer.py: `**({"under": True} if relation.get("under") else {})}` -> `}` (galley's
        oven and quarters' cables, said under their holder, laid up in it and failing their placement)
    And the 2026-11-04 audit's laid-as-designed gate: the wall lamp's front faces out of its wall into the room (it
    was laid with its back to the room), at its relation's 2 m height; a lamp hung from the roof has its top 0.01 m
    under the place's 3 m ceiling; a chair before the module stands at its piece's spot, naming the module; the
    gate passes on them and fails, by name, on the lamp turned to its wall, two lamps at one spot, the hung lamp
    1 m lower and the chair 1.2 m off its holder.
    Break: score/stages/scene_record/writer.py: `along = np.subtract(wall["to"], wall["from"]) * -float(relation["side"])`
        -> `along = np.subtract(wall["to"], wall["from"])`
    Break: score/stages/scene_record/writer.py: `base = roof_under(design, spot) - float(size[2]) - ROOF_CLEAR` -> `pass`
    Break: score/stages/scene_record/gates.py: `found.append(f"{entry['name']} faces its wall, its back to the room")`
        -> `pass`
    A wall's face ends at the faces of the walls meeting its ends, never at their middle lines (storage's 7.7 m pipes
    on its 7.52 m east line went 0.084 m into its north and south walls, 2026-11-10): the east wall of a 20 m square
    of 0.2 m walls holds its things from z -9.9 to 9.9, and a facet meeting it straight on trims nothing.
    Break: score/stages/scene_record/writer.py: `first, last = holders.corner_trims(design, start, end)` ->
        `first, last = 0.0, 0.0`
    Break: score/stages/scene_record/gates.py: `found.append(f"{one['name']} and {other['name']} of row {row} stand
        at one spot")` -> `pass`
    Break: score/stages/scene_record/gates.py: `if abs(height + size[2] - under) > TOLERANCE:` -> `if False:`
    Break: score/stages/scene_record/gates.py: `if not -TOLERANCE <= gap <= SEAT_REACH:` -> `if False:`
    2026-11-06 (the engine room's railings piled 1 to 4 m over one another, passing every gate): a crate its relation
    stands on the floor passes on the floor, on the module's 6 m top, on a 1 m deck under it and half way up a flight
    rising 0 to 2 m, and fails 1 m up over nothing, and 1 m up on a crate of its own row, unless its row piles.
    Break: score/stages/scene_record/gates.py: `and not ground_under(spots, height, design)}` -> `and False}`
    Break: score/stages/scene_record/gates.py: `(other["row"] != checked[name][0]["row"] or` -> `(True or`
    Break: score/stages/scene_record/gates.py: `holders.piles(rows.get(other["row"]) or {})))}` -> `False))}`
    Break: score/stages/scene_record/gates.py: `and any(design_shell.inside(spot, level["points"]) for spot in
        spots)] + [` -> `and False] + [`
    Break: score/stages/scene_record/gates.py: `min(max(height, float(stair["from"])), float(stair["to"]))` ->
        `float(stair["from"])`
    2026-11-06 (hangar's second 32 m pipe laid as a chord across its left and front walls' corner, passing every
    gate): a wall thing whose face runs from one wall round their corner onto the other fails; one flat along a wall
    passes, and so does a chord over two walls meeting 20 degrees apart (a round wall's facets).
    Break: score/stages/scene_record/gates.py: `if at[0] != at[1]:` -> `if False:`
    Break: score/review/holders/__init__.py: `if turn > ROUND_BEND:` -> `if False:` (the chord over facets fails)
    2026-11-07 (laid-as-designed@habitat): a chord over its facets round a closed room passes too, its far end placed
    where its face runs on from its near one, never on the chain's other pass round the room.
    Break: score/stages/scene_record/gates.py: `holders.chain_along(chain, ends[1], near=first)` ->
        `holders.chain_along(chain, ends[1])`
    2026-11-06 (the square's lantern strings 6 m over its plaza): a thing hung between holders (holders' `hung`)
    passes while both of them stand as high as it hangs, and fails hung over the top of one; a floor relation's
    `height` (holders.stood_under: the square's stage screen stood at its deck's 3.3 m behind it) is where the
    record stands its object, over its plan base.
    Break: score/stages/scene_record/gates.py: `if len(held) < 2:` -> `if False:`
    Break: score/stages/scene_record/gates.py: `hung_faults(objects, design, sizes, relations, standing)` -> `[]`
    Break: score/stages/scene_record/writer.py: `base = float(relation.get("height", base))` -> `pass`
    2026-11-06 (hangar's 32 m pipes at 10 m in one another on its left and front walls, passing every gate): a second
    lamp on the west wall 0.1 m along from the first fails, inside it; one just its length and 0.02 m along, touching,
    passes, and so does one 0.1 m along stood its tall and a gap over it.
    Break: score/stages/scene_record/gates.py: `for depth in [holders.boxes_meet(box, other)] if depth >
        holders.WALL_TOUCH]` -> `for depth in [holders.boxes_meet(box, other)] if False]`
    Break: score/review/holders/__init__.py: `return min(ground, min(first[6], second[6]) - max(first[5], second[5]))`
        -> `return ground` (the lamp stood over the first fails)
    #94: the garage door its relation says rests leaning carries `rests` leaning for the settle to lean it by; the
    door, resting as the others lay it, carries none.
    Break: score/stages/scene_record/writer.py: `**({"rests": relation["rests"]} if relation and relation.get("rests")
        else {})` -> `**{}`
    settle@street (2026-11-11): its 0.4 m red paper lanterns, against the side of their 1 cm lantern string, were
    shrunk to 16% and 2% to fit its height. Two lanterns against an 8 m string 1 cm thick are marked `below` (hung
    under it at their own size), a quarter and three quarters of the way along it; the garage door against its 6 m
    module is not.
    Break: score/stages/scene_record/writer.py: `on["along"] = round((number + 0.5) / len(hung), 4)` -> `pass`
    Break: score/stages/scene_record/writer.py: `return thick <= THIN_SHARE * min(float(side) for side in size)` ->
        `return False` (the lantern laid against the string's side), or `-> return True` (the garage door hung under
        its module)
    assembly@square (2026-11-12): its lantern strings, hung 6 m over the plaza between its buildings, carried no `on`
    and were judged on the plaza. A string the relations hang between two poles carries `between` them, naming each
    pole's object; one hung between a pole and an item that lays no object is held by nothing and says so.
    Break: score/stages/scene_record/writer.py: related's `if how == "hung" and len(relation.get("holders") or []) ==
        2:` -> `if False:` (the string with no `on`), or holder_names' `on["holder"] = [of_item[0] for of_item in
        names]` -> `pass` (no holders named), or its `if all(names):` -> `if any(names):` (held by one pole)"""
    from score.review import holders
    from score.stages.scene_record import gates
    assert writer.design_shell.KEPT_RELATIONS == holders.KEPT  # the row reads its relations where holders keep them
    (tmp_path / "plans").mkdir()
    kept = tmp_path / "plans/shed.json"
    kept.write_text(json.dumps(design))
    given = {"plans": tmp_path / "plans"}
    if relations is not None:  # derived from the kept plan as it stands, unless the case names another plan
        (tmp_path / "relations.json").write_text(json.dumps(
            {"plan": hashlib.sha256(kept.read_text().encode()).hexdigest(), **relations}))
        given["relations"] = tmp_path / "relations.json"
    relations, left_out = writer.relations_input(given, "shed")
    assert left_out == (judged or {}).get("left out"), left_out
    handin = {"rows": rows, "objects": (far_off or {}).get("objects", {})}
    found = [*writer.design_objects(design, handin, relations),
             *writer.structure({"place": "shed"}, design, None, shell_rows),
             *writer.row_entries(design, "shed", None, handin)]
    assert [row["id"] for row in rows if far.far_object(row, set())] == [row["id"] for row in rows if row.get("far")]
    if far_off:
        (tmp_path / "inventory.json").write_text(json.dumps(far_off["inventory"]))
        laid_far, unplaced = writer.far_objects(design, handin, tmp_path / "inventory.json")
        assert [entry["row"] for entry in unplaced] == far_off["unplaced"], unplaced
        found += laid_far
    laid = {entry["name"]: entry for entry in found}
    assert len(laid) == len(found), [entry["name"] for entry in found]
    sizes = {row["id"]: row["size"] for row in rows}
    for name, wanted in expected.items():
        entry = laid[name]
        for path, wants in wanted.items():
            value = entry
            for key in path.split("."):
                value = value[int(key)] if isinstance(value, list) else \
                    value.get(key, ABSENT) if isinstance(value, dict) else ABSENT
            for want in wants if isinstance(wants, tuple) else (wants,):
                if isinstance(want, (Turned, Starts, Near, Says)):
                    held = want.holds(value, design, sizes.get(entry.get("row")))
                else:
                    held = value is want if want is ABSENT or isinstance(want, bool) else value == want
                assert held, (name, path, value, want)
    for row, names in laid_rows.items():
        assert sorted(name for name, entry in laid.items() if entry.get("row") == row) == names, (row, laid)
    objects = [entry for entry in found if entry.get("kind") == "object"]
    for name, edit, wanted in (judged or {}).get("faults", []):
        plan_drawn, held = edit.get("plan", design), edit.get("relations", relations)
        kinds = {**{row["id"]: row for row in rows}, **judged.get("kinds", {}), **edit.get("kinds", {})}
        by_name = {entry["name"]: entry for entry in objects}
        edited = [*objects, *[{**by_name[source], "name": copy} for source, copy, _ in edit.get("copy", [])],
                  *edit.get("add", [])]
        moves = {**edit.get("move", {}), **{copy: by for _, copy, by in edit.get("copy", [])}}
        edited = [json.loads(json.dumps(entry)) for entry in edited]
        for entry in edited:
            if entry["name"] in moves:
                entry["at"] = [at + by for at, by in zip(entry["at"], moves[entry["name"]])]
            for path, value in edit.get("set", {}).get(entry["name"], {}).items():
                *outer, last = path.split(".")
                target = entry
                for key in outer:
                    target = target[key]
                target[last] = value
        faults = gates.spot_faults(edited) + gates.held_wall_faults(edited, plan_drawn, sizes, kinds) + \
            gates.bent_faults(edited, plan_drawn) + gates.wall_overlap_faults(edited, plan_drawn, sizes) + \
            gates.roof_faults(edited, plan_drawn, sizes, held, kinds) + \
            gates.seat_faults(edited, sizes, kinds, plan_drawn) + \
            gates.floor_faults(edited, plan_drawn, sizes, held, kinds)
        assert faults == wanted, (name, faults)


class EyeIn:
    """An eye whose (x, z) lies (`inside` True) or does not lie in the box |x| < `half`, `low` < z < `high`."""

    def __init__(self, half, low, high, inside=True):
        self.half, self.low, self.high, self.inside = half, low, high, inside

    def holds(self, eye):
        return (abs(eye[0]) < self.half and self.low < eye[2] < self.high) == self.inside


class Within:
    """An eye whose (x, z) lies less than `metres` from `point`."""

    def __init__(self, point, metres):
        self.point, self.metres = point, metres

    def holds(self, eye):
        return math.hypot(eye[0] - self.point[0], eye[2] - self.point[1]) < self.metres


class Matches:
    """A said text the pattern finds."""

    def __init__(self, pattern):
        self.pattern = pattern

    def holds(self, said):
        return isinstance(said, str) and re.search(self.pattern, said) is not None


# The places the views are worked on, each 10 m square round the origin unless said (frame: its middle at the origin).
GROUND_YARD = {"floor": [[-5.0, -5.0], [5.0, 5.0]], "floor_height": 0.0, "items": [], "doorways": [],
               "standing": [{"at": [4.0, 2.0], "level": 0.0, "looks_at": None},
                            {"at": [4.0, 2.0], "level": 1.0, "looks_at": None}]}
HATCHED = {"floor": [[0.0, 0.0], [8.0, 6.0]], "floor_height": 0.0, "items": [{"name": "HATCH", "box": [3.0, 2.0, 5.0, 4.0]}],
           "doorways": [], "standing": [{"at": [4.0, 3.0], "level": 3.0, "looks_at": "HATCH"},
                                        {"at": [1.0, 1.0], "level": 0.0, "looks_at": None}]}
CRATED = {"w": 10.0, "d": 10.0, "items": [["CRATE 1", 4.0, 1.5, 2.0, 2.0, None, "item"]], "rows": {"CRATE 1": ["crate"]},
          "people": [[5.0, 3.6], [8.0, 8.0]]}
CRATES = {"rows": [{"id": "crate", "anchor": "floor", "size": [2.0, 2.0, 1.0], "count": 1}]}
CRATE_RECORD = {"floor": [[-5.0, -5.0], [5.0, 5.0]], "floor_height": 0.0, "items": [],
                "doorways": [{"name": "door-1", "middle": [0.0, 0.0, -4.5], "inward": [0.0, 0.0, 1.0], "wide": 1.0,
                              "to": "yard"}],
                "standing": [{"at": [0.0, -1.4], "level": 0.0, "looks_at": None},
                             {"at": [3.0, 3.0], "level": 0.0, "looks_at": None}]}
WARDROBES = {"rows": [{"id": "wardrobe", "anchor": "floor", "size": [0.6, 2.0, 2.0], "count": 1},
                      {"id": "bench", "anchor": "floor", "size": [1.0, 0.4, 0.45], "count": 1}]}
WARDROBED = {"w": 10.0, "d": 10.0, "items": [["WARDROBE 1", 3.9, 4.0, 0.6, 2.0, None, "item"],
                                             ["BENCH 1", 1.2, 1.9, 0.6, 0.4, None, "item"]],
             "rows": {"WARDROBE 1": ["wardrobe"], "BENCH 1": ["bench"]},
             "shapes": {"WARDROBE 1": {"tall": 2.0}, "BENCH 1": {"tall": 0.45}},
             "walls": [{"from": [0.0, 0.0], "to": [10.0, 0.0]}]}
BOXED = {"w": 10.0, "d": 10.0, "items": [["WARDROBE 1", 4.3, 4.3, 1.4, 0.3, None, "item"],
                                         ["WARDROBE 2", 4.3, 4.3, 0.3, 1.4, None, "item"],
                                         ["WARDROBE 3", 5.4, 4.3, 0.3, 1.4, None, "item"],
                                         ["WARDROBE 4", 4.3, 5.4, 1.4, 0.3, None, "item"]],
         "rows": {f"WARDROBE {number}": ["wardrobe"] for number in range(1, 5)},
         "shapes": {f"WARDROBE {number}": {"tall": 2.0} for number in range(1, 5)}}
# Each case: the plan row's record, the design and inventory its clear and sight are worked from (None: neither),
# where its made ground is looked for (the terrain row read or not, the place) and whether one is made there, whether
# the eyes are cleared of things (`clear`) and looks of walls and things (`sight`), and the views kept and left out in
# order with what each must hold (`look` is the aim less the eye on the floor, `heights` the eye's and the aim's): a
# value equal, an EyeIn or Within eye, Matches said text, ABSENT, or a tuple of these all.
VIEWED = [
    ("an open place's eye a person's height over its made ground", GROUND_YARD, None, None, (True, "yard"), True, (),
     {"spot-1": {"eye": [4.0, 3.6, 2.0]}, "spot-2": {"eye": [4.0, 2.6, 2.0]}}, {}),
    ("a place the terrain made no ground for stands on its levels", GROUND_YARD, None, None, (True, "shed"), False, (),
     {"spot-1": {"eye": [4.0, 1.6, 2.0]}, "spot-2": {"eye": [4.0, 2.6, 2.0]}}, {}),
    ("no terrain row read stands on its levels", GROUND_YARD, None, None, (False, "yard"), False, (),
     {"spot-1": {"eye": [4.0, 1.6, 2.0]}, "spot-2": {"eye": [4.0, 2.6, 2.0]}}, {}),
    ("looking straight down, up along the floor's long axis", HATCHED, None, None, (False, "shed"), False, (),
     {"spot-1": {"up": [1.0, 0.0, 0.0]}, "spot-2": {"up": ABSENT}}, {}),
    ("looking straight down on a deep floor", {**HATCHED, "floor": [[0.0, 0.0], [6.0, 8.0]],
                                               "standing": HATCHED["standing"][:1]},
     None, None, (False, "shed"), False, (), {"spot-1": {"up": [0.0, 0.0, 1.0]}}, {}),
    ("an eye in a thing moves out with its look kept", CRATE_RECORD, CRATED, CRATES, (False, "shed"), False, ("clear",),
     {"from-door-1": {"eye": (EyeIn(1.2, -3.7, -1.3, inside=False), Within([0.0, -3.5], 1.5)), "look": [0.0, 8.0],
                      "heights": [1.6, 1.0]},
      "spot-1": {"eye": EyeIn(0.05, -1.3, math.inf), "look": [0.0, 1.4], "heights": [1.6, 1.0]},
      "spot-2": {"eye": [3.0, 1.6, 3.0], "aim": [0.0, 1.0, 0.0]}}, {}),
    ("eyes not cleared stand at their spots", CRATE_RECORD, CRATED, CRATES, (False, "shed"), False, (),
     {"from-door-1": {}, "spot-1": {"eye": [0.0, 1.6, -1.4]}, "spot-2": {"eye": [3.0, 1.6, 3.0]}}, {}),
    ("a look into a thing close by turns, a low bench and a spot off the plan block none",
     {**CRATE_RECORD, "doorways": [], "standing": [{"at": [-1.25, 0.0], "level": 0.0, "looks_at": None},
                                                   {"at": [-4.0, -3.2], "level": 0.0, "looks_at": None},
                                                   {"at": [0.0, -20.0], "level": 0.0, "looks_at": None}]},
     WARDROBED, WARDROBES, (False, "shed"), False, ("sight",),
     {"spot-1": {"eye": [-1.25, 1.6, 0.0], "from": Matches(r", turned [+-]\d+ degrees off a wall or thing 0\.1\d m ahead$")},
      "spot-2": {"aim": [0.0, 1.0, 0.0], "from": "plan standing spot 2, looking to the middle"},
      "spot-3": {"aim": [0.0, 1.0, 0.0], "from": "plan standing spot 3, looking to the middle"}}, {}),
    ("a spot boxed in on every side is left out", {**CRATE_RECORD, "floor": [[-5.0, -5.0], [5.0, 4.0]], "doorways": [],
                                                    "standing": [{"at": [0.0, 0.0], "level": 0.0, "looks_at": None}]},
     BOXED, WARDROBES, (False, "shed"), False, ("sight",), {}, {"spot-1": {"why": Matches("every way it turns")}}),
]


@pytest.mark.parametrize("record, design, inventory, terrain, made_ground, uses, kept, left",
                         [case[1:] for case in VIEWED], ids=[case[0] for case in VIEWED])
def test_each_view_eye_stands_and_looks_where_a_person_would(tmp_path, record, design, inventory, terrain,
                                                             made_ground, uses, kept, left):
    """Each view of a place (the cases in VIEWED, worked out by hand) stands its eye a person's height over what its
    spot stands on and looks where a person would see the room: a standing spot at the floor of an open place stands
    on the terrain row's made ground under it (a ground rising 0.5 m a metre east puts the eye at (4, 2) 2 + 1.6 m
    up), a spot on a 1 m deck stays on its deck, and a place the terrain made no ground for stands on its level
    (wreck's spot-3 and spot-6 eyes stood 2.6 and 4.3 m under its ground, their views black, 2026-10-30).
    Break: score/stages/scene_record/writer.py: `return spot["level"] if under is None else under` ->
        `return spot["level"]`
    Wreck's spot-5, 2026-10-30: a doorway's eye 1 m in lands in a 2 m crate, and a person spot stands against it: each
    eye moves to the nearest floor where a 0.5 m person stands in nothing, its aim moved by the same offset; a spot
    clear of the crate stays where it is, and its own person spot never counts against it.
    Break: score/stages/scene_record/writer.py: `if not standing.stands_in(spot, size, walls_things, grid, others):`
        -> `if True:`; and `eye, aim = eye + [offset[0], 0.0, offset[1]], aim + offset` -> `eye = eye + [offset[0],
        0.0, offset[1]]`
    Flat's spot-2, 2026-10-31: its eye 0.45 m off its wardrobe, aimed at the middle, saw only the wardrobe. A spot
    0.15 m west of a 2 m tall wardrobe looking east at the middle turns to the nearest way clear for a metre (+-15
    degrees will not do: the wardrobe is 2 m deep), its eye kept, and every look kept is clear; a spot boxed in by
    wardrobes on every side is left out with why; a low bench in its look does not block it, nor does anything for
    an eye off the plan (galley's and hangar's spots past their plans, 2026-10-31).
    Break: score/stages/scene_record/writer.py: `if hit is None:` -> `if True:`; and `if (cell >= 0).all() and (cell
        < grid.shape).all() and point[1] - base < tops[tuple(cell)]:` -> `if point[1] - base < tops[grid.cell_of(spot)]:`
    Round 33's spot-1 at shiplock looked straight down at the item under it with the world's up (0, 1, 0), so its
    picture had no sideways and every light measure was NaN (2026-10-30): a look straight down takes the floor's long
    axis as its up, a level look none.
    Break: score/stages/scene_record/writer.py: `return [upright(view, plan["floor"]) for view in found]` ->
        `return found`"""
    from pxr import Usd, UsdGeom
    ground = Usd.Stage.CreateNew(str(tmp_path / "moon/places/yard.usdc"))
    UsdGeom.Xform.Define(ground, "/yard")
    slope = UsdGeom.Mesh.Define(ground, "/yard/Outside/near")
    slope.CreatePointsAttr([(-10, -5, -10), (10, 5, -10), (10, 5, 10), (-10, -5, 10)])
    slope.CreateFaceVertexCountsAttr([4])
    slope.CreateFaceVertexIndicesAttr([0, 1, 2, 3])
    ground.Save()
    read, place = terrain
    under = writer.ground_under({"terrain": str(tmp_path)} if read else {}, place)
    assert (under is not None) == made_ground, (terrain, under)
    clear = writer.clear_of(design, inventory) if "clear" in uses else None
    sight = writer.sight_of(design, inventory) if "sight" in uses else None
    found_kept, found_left = writer.views_inside(writer.views(record, 1.6, under, clear, sight), design, False)
    assert [view["name"] for view in found_kept] == list(kept), found_kept
    assert [view["name"] for view in found_left] == list(left), found_left
    for view in found_kept if sight else []:
        assert sight(np.array(view["eye"]), np.array(view["aim"]), 0.0) is None, view
    for found, expected in ((found_kept, kept), (found_left, left)):
        for view in found:
            fields = {**view, "heights": [view["eye"][1], view["aim"][1]] if "aim" in view else ABSENT,
                      "look": [round(view["aim"][0] - view["eye"][0], 3), round(view["aim"][2] - view["eye"][2], 3)]
                      if "aim" in view else ABSENT}
            for field, wants in expected[view["name"]].items():
                for want in wants if isinstance(wants, tuple) else (wants,):
                    value = fields.get(field, ABSENT)
                    held = want.holds(value) if isinstance(want, (EyeIn, Within, Matches)) else \
                        value is want if want is ABSENT else value == want
                    assert held, (view["name"], field, value, want)
