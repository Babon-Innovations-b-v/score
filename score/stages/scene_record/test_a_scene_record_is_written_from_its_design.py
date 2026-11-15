"""A scene record is written from its design alone, on a plan of its own (a small shed beside a yard on a site): its
plan maps, and an item with no rows, a door that says nowhere it leads and a sealed door the layout leaves open each
fail `mapped`; a written plan with no corner takes its outline; the record holds the shell cut round its door, its
stair, a light over its lamp, the sky from the physics (on Mars its dusty day sky, inside too), the places its doors lead to and its backdrop rows are shown
from, every object at its plan item waiting on its model, a row the plan lays only against its edge past it, a far
row far off, each object carrying what holds it (its opening, its wall, its holder), an arched rib as a band, a light where a tower or a glowing row stands, and each part the scene
library's surface; its gates fail a filled door, a moved lamp and a door to no place. Every spot is worked out by hand from the plans below.

The test names the break that turns it red (`Break: <file>: `old` -> `new``); each was applied once and seen red.

Run: PROPS_HOME=$(mktemp -d) .venv/bin/python -m pytest
    score/stages/scene_record/test_a_scene_record_is_written_from_its_design.py
"""
import hashlib
import json
import math
import pathlib
import re
import sys
import numpy as np
import pytest

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from score import checks  # noqa: E402
from score.review import holders as review_holders, plans as review_plans  # noqa: E402
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

# The places a backdrop row of the furnished shed's hand-in is shown from: the yard (already stood by its door) and
# the site (the palm's holder).
SHOWN = {"rows": [{"id": "palm_tree", "route": "skyline", "shown": {"place": "site", "row": "palm_tree"}},
                  {"id": "far_shed", "route": "skyline", "shown": {"place": "yard", "row": "shed"}}]}
# A row counting 5 on two items of the furnished shed (lays 3 and 2), and the same plan dropping three of them
# (settle@engineroom, 2026-11-09: lays 1 and 1).
PIPES = {**FURNISHED, "items": [*FURNISHED["items"], ["PIPE 1", 5.0, 1.0, 1.0, 0.2, None, "item"],
                                ["PIPE 2", 5.0, 3.0, 1.0, 0.2, None, "item"]],
         "rows": {**FURNISHED["rows"], "PIPE 1": ["pipe"], "PIPE 2": ["pipe"]}}
PIPED = {"rows": [*FURNISHED_HANDIN["rows"], {"id": "pipe", "route": "prop", "size": [1.0, 0.1, 0.1], "count": 5}],
         "objects": {**FURNISHED_HANDIN["objects"], "pipe": {"rows": ["pipe"]}}}
DROPPED = {**PIPES, "dropped": [{"item": "pipe", "why": "3 more of it than the place's free floor holds", "laid": 2}]}
UNSIZED = {**FURNISHED_HANDIN, "rows": [{**row, "size": None} if row["id"] == "rail" else row
                                        for row in FURNISHED_HANDIN["rows"]]}
# A library whose floor kinds hold an edging and a grate beside its plate, its walls a recess beside its panel.
EDGED = {"kinds": {"floor": ["hazard_frame_paint", "deck_floor_plate", "floor_vent_grate"],
                   "wall": ["hull_panel", "hull_recess"]}}
# A yard on Mars at its afternoon, the same site on the Moon.
MARS = {"site": {"on": "mars", "latitude": 30.0, "longitude": 130.0, "height_m": 0.0}, "time": "2099-10-01T16:00:00Z"}
MOON = {**MARS, "site": {**MARS["site"], "on": "moon"}}
MARS_YARD = {"title": "YARD", "outline": [[0, 0], [10, 0], [10, 10], [0, 10]], "terrain": {"spots": [[5, 5]]}}
# The lit shed: a 10 m floodlight tower, a light switch, a core its concept shows glowing blue at half the brightest
# light, an engine it shows dark, the starry sky, four counted monitors on two items (3 m from x 1, 2 m from x 5), a
# glowing wall panel read as three drawn as the whole room against the east wall and one against the west wall.
LIT = {**WRITTEN, "items": [["TOWER", 6.0, 1.0, 1.0, 1.0, None, "item"],
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
LIT_ROWS = [{"id": "floodlight_tower", "name": "floodlight tower", "noun": "tower", "anchor": "on:yard",
             "size": [1.0, 1.0, 10.0]},
            {"id": "light_switch", "name": "light switch", "noun": "switch", "anchor": "wall"},
            {"id": "core", "name": "energy core", "noun": "core", "anchor": "floor", "size": [1.0, 1.0, 3.0]},
            {"id": "engine", "name": "engine", "noun": "engine", "anchor": "floor", "size": [2.0, 1.0, 1.0]},
            {"id": "sky", "name": "starfield", "noun": "sky", "anchor": "sky"},
            {"id": "screens", "name": "wall monitors", "noun": "monitor", "anchor": "floor", "count": 4},
            {"id": "wall_panel", "name": "wall panel", "noun": "panel", "anchor": "wall", "size": [8.0, 6.0, 3.0],
             "count": 3},
            {"id": "west_panel", "name": "wall panel", "noun": "panel", "anchor": "wall", "size": [8.0, 6.0, 3.0]}]
PANEL_GLOW = {"glows": True, "glowing": "its lamps", "colour": "#ffeedd", "brightness": 1.0}
LIT_CONCEPT = {"rows": {"core": {"glows": True, "glowing": "its column", "colour": "#44aaff", "brightness": 0.5},
                        "screens": {"glows": True, "glowing": "screens", "colour": "#44aaff", "brightness": 0.5},
                        "engine": {"glows": False, "glowing": "", "colour": "", "brightness": 0},
                        "sky": {"glows": True, "glowing": "stars", "colour": "#ffffff", "brightness": 0.4},
                        "wall_panel": PANEL_GLOW, "west_panel": PANEL_GLOW},
               "scene": {"daylight": False, "unseen": False, "unseen_colour": ""}}
LIT_WALLS = {"relations": [{"item": "PANEL", "row": "wall_panel", "how": "wall", "side": 1, "spot": [8.0, 3.0],
                            "wall": {"from": [8.0, 0.0], "to": [8.0, 6.0], "thick": 0.2}, "why": "its free wall"},
                           {"item": "WEST PANEL", "row": "west_panel", "how": "wall", "side": 1, "spot": [0.0, 3.0],
                            "wall": {"from": [0.0, 6.0], "to": [0.0, 0.0], "thick": 0.2}, "why": "its free wall"}]}
LAMP_LIBRARY = REPO / "data/library/lamps.json"
SLIDING_DOOR = {"id": "sliding_door", "name": "sliding door", "noun": "door"}


def plan_read(output, inputs):
    """A made plan's own record, as `plan`."""
    return [("plan", json.loads((output / "plan.json").read_text()))]


def record_read(output, inputs):
    """A written record's pieces by name: the record itself (`record`), its objects and shell pieces, and its views
    kept (row `view`) and left out (row `left out`)."""
    record = writer.record_in(output)[1]
    return [("record", record), *[(entry["name"], entry) for entry in [
        *record["objects"], *record["structure"], *viewed(record["views"], True),
        *viewed(record["views_left_out"], False)]]]


def furnished_read(output, inputs):
    """What the furnished shed's record stands by besides its own pieces: the Sun the physics sees at its site and
    time, its stair drawn from its high end, its shell painted from a scene library whose walls and floors have one
    variant each (`painted <piece>`), its ribs and its roof laid on a USD stage by the scene builder, and the places
    its backdrop rows are shown from (`shown <n>`)."""
    from pxr import Usd
    from score.review import overhead
    sys.path.insert(0, str(REPO / "tools/usd"))
    import scene
    folder = output.parent
    record = writer.record_in(output)[1]
    seen = overhead.seen(json.loads((folder / "sky.json").read_text())["setting"], SKY["site"], SKY["time"])
    plan_record = json.loads((pathlib.Path(inputs["plan"]) / "plan.json").read_text())
    library = folder / "library"
    library.mkdir()
    (library / "materials.json").write_text(json.dumps({"kinds": {"wall": ["painted_panel"], "floor": ["deck_plate"]}}))
    painted = writer.record_of(plan_record, FURNISHED, {**inputs, writer.LIBRARY_ROW: library})["structure"]
    ribs = [entry for entry in record["structure"] if entry["builder"] == "arch"]
    stage = Usd.Stage.CreateInMemory()
    scene.write_structure(stage, "shed", [*[entry for entry in painted if entry["name"] == "roof_1"], *ribs])
    meshed = scene.built_meshes(ribs[0])[0]["points"]
    roof = stage.GetPrimAtPath("/shed/Structure/roof_1")
    return [("sun seen", next(light for light in seen["lights"] if light["name"] == "Sun")),
            ("stair drawn down", writer.stair(1, {**WRITTEN["stairs"][0], "from": 1.0, "to": 0.0}, WRITTEN)),
            *[(f"painted {entry['name']}", entry) for entry in painted],
            ("rib mesh", {"low": meshed.min(0).tolist(), "high": meshed.max(0).tolist(),
                          "prim's row": stage.GetPrimAtPath("/shed/Structure/structural_ribs_1").GetAttribute(
                              "score:row").Get()}),
            ("roof mesh", {"missing": roof.GetAttribute("score:surface:missing").Get(),
                           "bound": roof.HasRelationship("material:binding")}),
            *[(f"shown {number}", entry) for number, entry in enumerate(
                writer.places_of("shed", plan_record, FURNISHED, inputs["plans"], SHOWN), 1)]]


def base_read(output, inputs):
    """The base's tube: where its hub end stands on its holder, and the record of the hub standing it."""
    return [("tube's hub end", {"at": plan.on_holder(TUBE_1, TUBE, [1.0, 0.0]).tolist()}),
            ("tube stood", gates.writer.sibling("hub", HUB, BASE, "tube#1", inputs["plans"]))]


def turned_base_read(output, inputs):
    """The base turned: where the tube's greenhouse end stands, its boxes' overlaps, each place's level, and each
    place's record standing its neighbours (`<place>'s record`, its pair and lead faults beside)."""
    found = [("tube's greenhouse end", {"at": plan.on_holder(TURNED_TUBE, TUBE, [1.0, 4.0]).tolist()}),
             ("box overlaps", {"found": plan.overlap_faults(TURNED_BASE)}),
             ("levels", {"by place": plan.levels_of(plan.held_plans(TURNED_BASE, inputs["plans"]))})]
    for name, own in (("tube", TUBE), ("lab", TURNED_LAB), ("hub", TURNED_HUB)):
        record = {"place": name, "places": gates.writer.places_of(name, {"doors": []}, own, inputs["plans"])}
        found.append((f"{name}'s record", {"stands": sorted(entry.get("instance", entry["name"])
                                                            for entry in record["places"]),
                                           "pairs": gates.pair_faults(record, own, inputs),
                                           "leads": gates.lead_faults(record, own, inputs)}))
    return found


def raised_read(output, inputs):
    """The site's `held` measures beside the raised shed."""
    return [("site", site_held(output, inputs).measures)]


def two_doors(folder):
    """The doors of TWO_DOORS, numbered."""
    return [(f"door {number}", door) for number, door in enumerate(plan.doors_of(TWO_DOORS, INVENTORY), 1)]


def counted_runs(folder):
    """The furnished shed's objects with its rail row unsized (`unsized <name>`), and those of PIPES (`five <name>`)
    and DROPPED (`dropped <name>`)."""
    return [*[(f"unsized {entry['name']}", entry) for entry in writer.design_objects(FURNISHED, UNSIZED)],
            *[(f"{how} {entry['name']}", entry) for how, laid_plan in (("five", PIPES), ("dropped", DROPPED))
              for entry in writer.design_objects(laid_plan, PIPED)]]


def arched_and_painted(folder):
    """Whether the rib row, a 2 m deep block of it and an object row of it are arched, and the EDGED library's
    surface for a deck, a wall and a roof."""
    arched = writer.design_shell.arched
    return [("rib", {"arched": arched(RIB)}), ("2 m deep rib", {"arched": arched({**RIB, "size": [3.2, 2.0, 3.2]})}),
            ("rib object", {"arched": arched({**RIB, "part": "object"})}),
            ("edged", {kind: writer.design_shell.surface_for(kind, EDGED) for kind in ("deck", "wall", "roof")})]


def skies(folder):
    """The environment of the yard and of the shed on Mars, and of the yard on the Moon; the Mars dome's picture's
    upper half's red and blue; the yard record's files."""
    sys.path.insert(0, str(REPO / "tools" / "usd"))
    import mars_sky
    from score.review import setting
    dust = json.loads((REPO / "data/physics/dust.json").read_text())
    now = setting.now()
    on_mars = writer.environment(MARS_YARD, {**MARS, "setting": now}, dust)
    picture = mars_sky.picture(on_mars["sky_dome"], [0.0, -0.5, -0.866], 64)
    red, _, blue = picture[: picture.shape[0] // 2].reshape(-1, 3).mean(axis=0)
    return [("yard on mars", on_mars), ("shed on mars", writer.environment(WRITTEN, {**MARS, "setting": now}, dust)),
            ("yard on the moon", writer.environment(MARS_YARD, {**MOON, "setting": now}, dust)),
            ("mars picture", {"red": float(red), "blue": float(blue)}), ("yard's files", writer.files("yard"))]


def lit_shed(folder):
    """The lit shed's lights by its row kinds alone and by its concept's light (`lit <n>`, in the order laid), the
    lamp its core gets glowing at full brightness and a bulb row's on the monitors' item, where the west and east
    walls' spots stand in its frame 1.5 m up, and the glow share of a door whose keypad or light panel glows."""
    (folder / "inventory.json").write_text(json.dumps({"scene": "shed", "rows": LIT_ROWS}))
    (folder / "light.json").write_text(json.dumps(LIT_CONCEPT))
    given = {"inventory": folder / "inventory.json", "row kinds": REPO / "data/checks/row-kinds.json",
             "lamp library": LAMP_LIBRARY}
    found = writer.lights(LIT, {**given, "concept light": folder / "light.json"}, LIT_WALLS)
    spots = [(side, writer.in_frame(LIT, points, 1.5))
             for side, points in (("west", [[0.2, 3.0]]), ("east", [[7.8, 1.0], [7.8, 3.0], [7.8, 5.0]]))]
    shares = [(glowing, writer.glow_share(SLIDING_DOOR, {"glowing": glowing}, LAMP_LIBRARY))
              for glowing in ("keypad", "light panel")]
    return [("by row kinds", {"lights": writer.lights(LIT, given, LIT_WALLS)}), ("concept lights", {"lights": found}),
            *[(f"lit {number}", light) for number, light in enumerate(found, 1)],
            ("full core", {"lamps": writer.item_lamps(LIT["items"][2], {**LIT_ROWS[2], "row_kind": "machine"},
                                                      LIT_ROWS, LIT, writer.library_lamps(), LAMP_LIBRARY)}),
            ("bulbs", {"lamps": writer.item_lamps(LIT["items"][5], {**LIT_ROWS[5], "id": "bulbs", "name": "bulbs",
                                                                    "noun": "bulb"},
                                                  LIT_ROWS, LIT, writer.library_lamps(), LAMP_LIBRARY,
                                                  {**LIT_CONCEPT["rows"]["screens"], "glowing": "bulbs"})}),
            *[(f"{side} wall spot {number}", {"at": [spot[0], floor, spot[1]]})
              for side, (found_spots, floor) in spots for number, spot in enumerate(found_spots, 1)],
            *[(f"{glowing} door", {"share": share, "as": kind}) for glowing, (share, kind) in shares]]


def kept_where(folder):
    """Where the scene record reads its kept relations and its concept light."""
    from score.stages.scene_record import concept_light
    return [("relations", {"kept": writer.design_shell.KEPT_RELATIONS}), ("concept light",
                                                                        {"kept": concept_light.KEPT_LIGHT})]


def concept_lamps(output, inputs, moved=0.0):
    """The lamp faults of the lit shed's concept lights, its west panel's lamp moved `moved` m along x."""
    lights = dict(output)["concept lights"]["lights"]
    return gates.lamp_faults({"lights": [{**light, "at": [light["at"][0] + moved, *light["at"][1:]]}
                                         if light["row"] == "west_panel" else light for light in lights]}, LIT)


def file_of(key, output, inputs):
    """The file an edit's `key` names in a world: its record, a plan of its own (`plans/<name>`) or an input."""
    if key == "record":
        return output / "record/shed.json"
    if key.startswith("plans/"):
        return pathlib.Path(inputs["plans"]) / f"{key[len('plans/'):]}.json"
    return pathlib.Path(inputs[key])


def judged(output, inputs, edits, judge):
    """(answer, findings) of `judge` on a world's `output` and `inputs` with `edits` made to its files, each put back
    after; a refusal (of the world, or of the judge) answers None with its words."""
    if isinstance(output, ValueError):
        return None, (str(output),)
    try:
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


class Turned:
    """An object's turn: `writer.yaw_turn` laying its row's long side along plan `way` (a facing letter or a
    vector); `signed` False takes a quaternion and its negative as one turn, and `not_` asks that it is not that turn."""

    def __init__(self, way, signed=True, not_=False):
        self.way, self.signed, self.not_ = way, signed, not_

    def holds(self, rotation, design, size, laid):
        way = writer.FACING_WAY[self.way] if isinstance(self.way, str) else self.way
        wanted = writer.yaw_turn(design, way, size)
        same = rotation == wanted if self.signed else bool(np.isclose(abs(np.dot(rotation, wanted)), 1.0))
        return same != self.not_


class Starts:
    """A said reason that begins with `text`."""

    def __init__(self, text):
        self.text = text

    def holds(self, said, design, size, laid):
        return isinstance(said, str) and said.startswith(self.text)


class Near:
    """A point within `within` (one tolerance an axis) of `point`."""

    def __init__(self, point, within):
        self.point, self.within = point, within

    def holds(self, at, design, size, laid):
        return isinstance(at, list) and bool(np.all(np.abs(np.subtract(at, self.point)) <= self.within))


class Says:
    """A said text that holds `text`."""

    def __init__(self, text):
        self.text = text

    def holds(self, said, design, size, laid):
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
#  - a band (assembly@base, 2026-11-15: its connecting tubes, each drawn a diagonal band from its hub to a module, laid
#    north to south): a 15 m tube on a band drawn corner to corner of its 8 m box lies along the band, a crate on one
#    keeps its facing's way.
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
#  - a take at its flight (#128, 2026-11-15: the greenhouse's baked stairs and the airlock's baked ramp unused, box
#    flights laid; a box ramp beside the engine room's ramp take): on a 10 by 10 m plan (place (x, z) is plan
#    (x - 5, y - 5)) the stairs row with a take and no item of its own is laid at its two stair flights, stairs_1 at
#    flight 1's middle, plan (1.5, 2), place (-3.5, -3), turned south its way up, and stairs_2 at flight 3's, plan
#    (6.5, 2), turned north (drawn down from 1 m), its foot at 0; the ramp row on its own item RAMP 1 stays there,
#    plan (7, 7.7), naming the ramp flight 2 it stands for; no box flight is laid for those three, while ramp 4, which
#    no row's take is left for, stays a flight of steps; the step ladder, a thing named for none, takes no flight.
FLOWN = {"w": 10.0, "d": 10.0,
         "items": [["RAMP 1", 6.0, 7.2, 2.0, 1.0, None, "item"], ["LADDER 1", 4.0, 4.0, 1.0, 1.0, None, "item"]],
         "rows": {"RAMP 1": ["ramp"], "LADDER 1": ["step_ladder"]},
         "stairs": [{"kind": "stair", "points": [[1.0, 1.0], [2.0, 1.0], [2.0, 3.0], [1.0, 3.0]], "from": 0.0,
                     "to": 1.0, "angle": 90.0, "steps": 5},
                    {"kind": "ramp", "points": [[6.0, 6.0], [8.0, 6.0], [8.0, 7.0], [6.0, 7.0]], "from": 0.0,
                     "to": 0.2, "angle": 0.0, "steps": 0},
                    {"kind": "stair", "points": [[6.0, 1.0], [7.0, 1.0], [7.0, 3.0], [6.0, 3.0]], "from": 1.0,
                     "to": 0.0, "angle": 90.0, "steps": 5},
                    {"kind": "ramp", "points": [[3.0, 8.0], [4.0, 8.0], [4.0, 9.0], [3.0, 9.0]], "from": 0.0,
                     "to": 0.1, "angle": 0.0, "steps": 0}]}
FLOWN_ROWS = [{"id": "stairs", "route": "shell", "size": [1.0, 2.0, 1.0]},
              {"id": "ramp", "route": "shell", "size": [2.0, 1.0, 0.2]},
              {"id": "step_ladder", "route": "prop", "size": [0.5, 0.5, 1.8]}]
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
    ("a long row on a band its item draws across its box lies along the band",
     {"w": 10.0, "d": 10.0, "items": [["TUBE 1", 1.0, 1.0, 8.0, 8.0, None, "item"],
                                      ["CRATE 1", 1.0, 1.0, 8.0, 8.0, None, "item"]],
      "rows": {"TUBE 1": ["tube"], "CRATE 1": ["crate"]},
      "shapes": {name: {"shape": "polygon", "points": [[1.0, 0.7143], [0.7143, 1.0], [0.0, 0.2857], [0.2857, 0.0]]}
                 for name in ("TUBE 1", "CRATE 1")}},
     [{"id": "tube", "route": "prop", "size": [3.0, 15.0, 3.0]},
      {"id": "crate", "route": "prop", "size": [1.0, 1.0, 1.0]}],
     None, None,
     {"tube_1": {"rotation": Turned((math.sqrt(0.5), math.sqrt(0.5)))},
      "crate_1": {"rotation": Turned((1.0, 0.0))}},
     {"tube": ["tube_1"], "crate": ["crate_1"]}, None, None),
    ("a long table facing nowhere lies along its long box, a square stool on one keeps the east way",
     {"w": 4.0, "d": 6.0, "items": [["TABLE 1", 1.0, 2.0, 1.1, 2.4, None, "item"],
                                    ["STOOL 1", 2.5, 2.0, 1.1, 2.4, None, "item"]],
      "rows": {"TABLE 1": ["table"], "STOOL 1": ["stool"]}},
     [{"id": "table", "route": "prop", "size": [2.0, 0.8, 0.8]},
      {"id": "stool", "route": "prop", "size": [0.4, 0.4, 0.5]}],
     None, None,
     {"table_1": {"rotation": Turned((0.0, 1.0))}, "stool_1": {"rotation": Turned((1.0, 0.0))}},
     {"table": ["table_1"], "stool": ["stool_1"]}, None, None),
    ("a passage against its wall runs out through it, a lamp on the wall along it",
     {"w": 10.0, "d": 10.0, "items": [["ON THE WALLS AND CEILING", 0.0, 0.0, 10.0, 10.0, None, "item"]],
      "rows": {"ON THE WALLS AND CEILING": ["tunnel", "lamp"]}},
     [{"id": "tunnel", "noun": "tunnel", "anchor": "wall", "route": "shell", "size": [3.0, 5.0, 3.0]},
      {"id": "lamp", "anchor": "wall", "route": "prop", "size": [0.3, 0.2, 0.3]}],
     {"relations": [{"item": "ON THE WALLS AND CEILING", "row": row, "how": "wall", "why": "against the wall nearest",
                     "wall": {"from": [10.0, 0.0], "to": [10.0, 10.0], "thick": 0.2}, "side": 1, "spot": [10.0, at]}
                    for row, at in (("tunnel", 3.0), ("lamp", 8.0))]}, None,
     {"tunnel_1": {"on.how": "wall", "rotation": Turned((1.0, 0.0))},
      "lamp_1": {"on.how": "wall", "rotation": Turned((0.0, -1.0))}},
     {"tunnel": ["tunnel_1"], "lamp": ["lamp_1"]}, None, None),
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
    ("a take laid at its flight, never a box flight beside it", FLOWN, FLOWN_ROWS, None, None,
     {"stairs_1": {"at": [-3.5, 0.0, -3.0], "rotation": Turned((0.0, 1.0)), "flight": "stair_1",
                   "bake": "stairs_1"},
      "stairs_2": {"at": [1.5, 0.0, -3.0], "rotation": Turned((0.0, -1.0), signed=False), "flight": "stair_3"},
      "ramp_1": {"at": [2.0, 0.0, 2.7], "flight": "ramp_2"}, "step_ladder_1": {"flight": ABSENT},
      "stair_1": ABSENT, "ramp_2": ABSENT, "stair_3": ABSENT, "ramp_4": {"builder": "stairs"}},
     {"stairs": ["stairs_1", "stairs_2"], "ramp": ["ramp_1"], "step_ladder": ["step_ladder_1"]},
     {"inventory": {"picture": [1000, 1000], "rows": []}, "unplaced": [],
      "objects": {row["id"]: {"rows": [row["id"]]} for row in FLOWN_ROWS}}, None),
    ("opening rows with no item named at a cut their words fit, and the shell's pillars", DOWN, [POSTS], None,
     OPENING_ROWS,
     {"posts_1": {"row": "posts", "plain": "shell", "surface": None, "surface_missing": Starts("shed: ")},
      "posts_2": {"row": "posts", "plain": "shell", "surface": None, "surface_missing": Starts("shed: ")}},
     {"corridor_opening": ["wall_1_3"], "floor_hatch": ["stair_2"], "roof_opening": [],
      "posts": ["posts_1", "posts_2"]}, None, None),
    ("a roof's opening named on its cut", HOLED, [], None, OPENING_ROWS, {}, {"roof_opening": ["roof_1"]}, None, None),
    ("a roof's opening named on its cut before its panels row", HOLED, [], None, {**OPENING_ROWS, "roof": ["roof_panels"]},
     {}, {"roof_opening": ["roof_1"]}, None, None),
    ("a shell the earth seed lays gets its pillars here", {**WRITTEN, "shell": "kit", "inside": True}, [POSTS], None, None,
     {}, {"posts": ["posts_1", "posts_2"]}, None, None),
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


class EyeIn:
    """An eye whose (x, z) lies (`inside` True) or does not lie in the box |x| < `half`, `low` < z < `high`."""

    def __init__(self, half, low, high, inside=True):
        self.half, self.low, self.high, self.inside = half, low, high, inside

    def holds(self, eye, design, size, laid):
        return (abs(eye[0]) < self.half and self.low < eye[2] < self.high) == self.inside


class Within:
    """An eye whose (x, z) lies less than `metres` from `point`."""

    def __init__(self, point, metres):
        self.point, self.metres = point, metres

    def holds(self, eye, design, size, laid):
        return math.hypot(eye[0] - self.point[0], eye[2] - self.point[1]) < self.metres


class Matches:
    """A said text the pattern finds."""

    def __init__(self, pattern):
        self.pattern = pattern

    def holds(self, said, design, size, laid):
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
# Each case: a plan, its hand-in rows, its relations (None: none kept) and the shell's own rows by part (None: none),
# the view record its views are worked from (None: none) with where its made ground is looked for (the terrain row read
# or not, the place), whether one is made there and whether the eyes are cleared of things (`clear`) and looks of
# walls and things (`sight`); the objects, shell pieces and views it lays with what each must hold (`field`,
# `field.sub` or `field.<index>`; a view's `look` is its aim less its eye on the floor, its `heights` the eye's and the
# aim's): a value equal, a Turned turn, a Starts, Says or Matches text, a Near, EyeIn or Within point, ABSENT, or a
# tuple of these all; each row named with exactly the pieces that name it in the order laid (a view kept is of row
# `view`, one left out of row `left out`); its far rows and its laid-as-designed gates. The views' places are 10 m
# square round the origin unless said (frame: its middle at the origin).
CASES = [(name, design, rows, relations, shell_rows, None, *laid)
         for name, design, rows, relations, shell_rows, *laid in PLACED] + [
    *[(name, None, [], None, None, (GROUND_YARD, terrain, made, ()), {"spot-1": {"eye": [4.0, high, 2.0]},
                                                                       "spot-2": {"eye": [4.0, 2.6, 2.0]}},
       {"view": ["spot-1", "spot-2"], "left out": []}, None, None)
      for name, terrain, made, high in (
          ("an open place's eye a person's height over its made ground", (True, "yard"), True, 3.6),
          ("a place the terrain made no ground for stands on its levels", (True, "shed"), False, 1.6),
          ("no terrain row read stands on its levels", (False, "yard"), False, 1.6))],
    ("looking straight down, up along the floor's long axis", None, [], None, None,
     (HATCHED, (False, "shed"), False, ()), {"spot-1": {"up": [1.0, 0.0, 0.0]}, "spot-2": {"up": ABSENT}},
     {"view": ["spot-1", "spot-2"], "left out": []}, None, None),
    ("looking straight down on a deep floor", None, [], None, None,
     ({**HATCHED, "floor": [[0.0, 0.0], [6.0, 8.0]], "standing": HATCHED["standing"][:1]}, (False, "shed"), False, ()),
     {"spot-1": {"up": [0.0, 0.0, 1.0]}}, {"view": ["spot-1"], "left out": []}, None, None),
    ("an eye in a thing moves out with its look kept", CRATED, CRATES["rows"], None, None,
     (CRATE_RECORD, (False, "shed"), False, ("clear",)),
     {"from-door-1": {"eye": (EyeIn(1.2, -3.7, -1.3, inside=False), Within([0.0, -3.5], 1.5)), "look": [0.0, 8.0],
                      "heights": [1.6, 1.0]},
      "spot-1": {"eye": EyeIn(0.05, -1.3, math.inf), "look": [0.0, 1.4], "heights": [1.6, 1.0]},
      "spot-2": {"eye": [3.0, 1.6, 3.0], "aim": [0.0, 1.0, 0.0]}},
     {"view": ["from-door-1", "spot-1", "spot-2"], "left out": []}, None, None),
    ("eyes not cleared stand at their spots", CRATED, CRATES["rows"], None, None,
     (CRATE_RECORD, (False, "shed"), False, ()),
     {"spot-1": {"eye": [0.0, 1.6, -1.4]}, "spot-2": {"eye": [3.0, 1.6, 3.0]}},
     {"view": ["from-door-1", "spot-1", "spot-2"], "left out": []}, None, None),
    ("a look into a thing close by turns, a low bench and a spot off the plan block none", WARDROBED,
     WARDROBES["rows"], None, None,
     ({**CRATE_RECORD, "doorways": [], "standing": [{"at": [-1.25, 0.0], "level": 0.0, "looks_at": None},
                                                    {"at": [-4.0, -3.2], "level": 0.0, "looks_at": None},
                                                    {"at": [0.0, -20.0], "level": 0.0, "looks_at": None}]},
      (False, "shed"), False, ("sight",)),
     {"spot-1": {"eye": [-1.25, 1.6, 0.0], "from": Matches(r", turned [+-]\d+ degrees off a wall or thing 0\.1\d m ahead$")},
      "spot-2": {"aim": [0.0, 1.0, 0.0], "from": "plan standing spot 2, looking to the middle"},
      "spot-3": {"aim": [0.0, 1.0, 0.0], "from": "plan standing spot 3, looking to the middle"}},
     {"view": ["spot-1", "spot-2", "spot-3"], "left out": []}, None, None),
    ("a spot boxed in on every side is left out", BOXED, WARDROBES["rows"], None, None,
     ({**CRATE_RECORD, "floor": [[-5.0, -5.0], [5.0, 4.0]], "doorways": [],
       "standing": [{"at": [0.0, 0.0], "level": 0.0, "looks_at": None}]}, (False, "shed"), False, ("sight",)),
     {"spot-1": {"why": Matches("every way it turns")}}, {"view": [], "left out": ["spot-1"]}, None, None),
]


def made_ground(folder):
    """A terrain folder under `folder` whose moon yard's ground rises 0.5 m a metre east."""
    from pxr import Usd, UsdGeom
    ground = Usd.Stage.CreateNew(str(folder / "moon/places/yard.usdc"))
    UsdGeom.Xform.Define(ground, "/yard")
    slope = UsdGeom.Mesh.Define(ground, "/yard/Outside/near")
    slope.CreatePointsAttr([(-10, -5, -10), (10, 5, -10), (10, 5, 10), (-10, -5, 10)])
    slope.CreateFaceVertexCountsAttr([4])
    slope.CreateFaceVertexIndicesAttr([0, 1, 2, 3])
    ground.Save()
    return folder


def viewed(views, kept):
    """`views` as laid entries: each of row `view` if `kept`, else `left out`, with its look and heights."""
    return [{**view, "row": "view" if kept else "left out",
             "heights": [view["eye"][1], view["aim"][1]] if "aim" in view else ABSENT,
             "look": [round(view["aim"][0] - view["eye"][0], 3), round(view["aim"][2] - view["eye"][2], 3)]
             if "aim" in view else ABSENT} for view in views]



class Count:
    """A list of exactly `count` things."""

    def __init__(self, count):
        self.count = count

    def holds(self, found, design, size, laid):
        return isinstance(found, list) and len(found) == self.count


class As:
    """The value at `path` (`field`, `field.sub` or `field.<index>`; none: the whole) of laid entry `name`."""

    def __init__(self, name, path=None):
        self.name, self.path = name, path

    def value(self, laid):
        return laid[self.name] if self.path is None else value_at(laid[self.name], self.path)

    def holds(self, found, design, size, laid):
        return found == self.value(laid)


class Over:
    """A number over `than` (a number or an As)."""

    def __init__(self, than):
        self.than = than

    def holds(self, found, design, size, laid):
        than = self.than.value(laid) if isinstance(self.than, As) else self.than
        return isinstance(found, (int, float)) and found > than


class Share:
    """A number `share` of the value an As finds: rounded to 4 places like it, or within `within` of it."""

    def __init__(self, of, share, within=None):
        self.of, self.share, self.within = of, share, within

    def holds(self, found, design, size, laid):
        whole = self.of.value(laid) * self.share
        return found == round(whole, 4) if self.within is None else abs(found - whole) <= self.within


class Each:
    """A list each of whose things holds every field of `wanted`."""

    def __init__(self, wanted):
        self.wanted = wanted

    def holds(self, found, design, size, laid):
        return isinstance(found, list) and not any(misfits(entry, self.wanted, design, size, laid) for entry in found)


def value_at(entry, path):
    """The value at `path` (`field`, `field.sub` or `field.<index>`; empty: `entry` itself) of `entry`, or ABSENT."""
    value = entry
    for key in path.split(".") if path else []:
        value = (value[int(key)] if int(key) < len(value) else ABSENT) if isinstance(value, list) else \
            value.get(key, ABSENT) if isinstance(value, dict) else ABSENT
    return value


def misfits(entry, wanted, design, size, laid):
    """The (path, value, want) of `wanted` (path: a want, or a tuple of wants) that `entry` does not hold: a want with
    `holds` holds by it, ABSENT and a bool by identity, any other by equality."""
    missed = []
    for path, wants in wanted.items():
        value = value_at(entry, path)
        for want in wants if isinstance(wants, tuple) else (wants,):
            if hasattr(want, "holds"):
                held = want.holds(value, design, size, laid)
            else:
                held = value is want if want is ABSENT or isinstance(want, bool) else value == want
            if not held:
                missed.append((path, value, want))
    return missed


def laid_pieces(folder, design, rows, relations, shell_rows, view, far_off, kinds):
    """The pieces a design lays (its objects, shell pieces, row entries, far rows and the views of `view`: its view
    record, where its made ground is looked for and its uses) on its plan kept in `folder`, under `relations` derived
    from that plan (unless they name another), with what the laying found as entry `laid` (relations left out, rows
    judged far, far rows unplaced, whether ground was made, kept views whose look is blocked); beside them the objects,
    design, relations kept, row sizes and row `kinds` its gates judge by."""
    (folder / "plans").mkdir()
    kept = folder / "plans/shed.json"
    kept.write_text(json.dumps(design))
    given = {"plans": folder / "plans"}
    if relations is not None:  # derived from the kept plan as it stands, unless the case names another plan
        (folder / "relations.json").write_text(json.dumps(
            {"plan": hashlib.sha256(kept.read_text().encode()).hexdigest(), **relations}))
        given["relations"] = folder / "relations.json"
    relations, left_out = writer.relations_input(given, "shed")
    handin = {"rows": rows, "objects": (far_off or {}).get("objects", {})}
    found = [*writer.design_objects(design, handin, relations),
             *writer.structure({"place": "shed"}, design, None, shell_rows, handin),
             *writer.row_entries(design, "shed", None, handin)] if design else []
    unplaced = ground = None
    blocked = []
    if far_off:
        (folder / "inventory.json").write_text(json.dumps(far_off["inventory"]))
        laid_far, unplaced = writer.far_objects(design, handin, folder / "inventory.json")
        found += laid_far
    if view:
        record, (read, place), uses = view
        under = writer.ground_under({"terrain": str(made_ground(folder))} if read else {}, place)
        ground = under is not None
        clear = writer.clear_of(design, {"rows": rows}) if "clear" in uses else None
        sight = writer.sight_of(design, {"rows": rows}) if "sight" in uses else None
        views_kept, views_left = writer.views_inside(writer.views(record, 1.6, under, clear, sight), design, False)
        blocked = [kept_view["name"] for kept_view in views_kept
                   if sight and sight(np.array(kept_view["eye"]), np.array(kept_view["aim"]), 0.0) is not None]
        found += viewed(views_kept, True) + viewed(views_left, False)
    laid = {"name": "laid", "left out": left_out, "far": [row["id"] for row in rows if far.far_object(row, set())],
            "unplaced": None if unplaced is None else [entry["row"] for entry in unplaced], "ground made": ground,
            "blocked looks": blocked}
    return {"found": [*found, laid], "objects": [entry for entry in found if entry.get("kind") == "object"],
            "design": design, "relations": relations, "sizes": {row["id"]: row["size"] for row in rows},
            "kinds": {**{row["id"]: row for row in rows}, **kinds}}, None


def laid_faults(edit):
    """A judge of a design's laid objects (judge_laid_as_designed's gates) after `edit` (LAID_FAULTS)."""
    def judge(laid, inputs):
        plan_drawn, held = edit.get("plan", laid["design"]), edit.get("relations", laid["relations"])
        kinds, sizes = {**laid["kinds"], **edit.get("kinds", {})}, laid["sizes"]
        by_name = {entry["name"]: entry for entry in laid["objects"]}
        edited = [*laid["objects"], *[{**by_name[source], "name": copy} for source, copy, _ in edit.get("copy", [])],
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
        return gates.spot_faults(edited) + gates.held_wall_faults(edited, plan_drawn, sizes, kinds) + \
            gates.bent_faults(edited, plan_drawn) + gates.wall_overlap_faults(edited, plan_drawn, sizes) + \
            gates.roof_faults(edited, plan_drawn, sizes, held, kinds) + \
            gates.seat_faults(edited, sizes, kinds, plan_drawn) + \
            gates.floor_faults(edited, plan_drawn, sizes, held, kinds)
    return judge


def pieces_row(name, design, rows, relations, shell_rows, view, expected, laid_rows, far_off, judged_by):
    """A row of ROWS from a case of CASES: its world the pieces its design lays, what the laying found expected beside
    its pieces, and its laid-as-designed faults as verdicts."""
    judged_by = judged_by or {}
    found = {"left out": judged_by.get("left out"), "far": [row["id"] for row in rows if row.get("far")],
             "unplaced": far_off["unplaced"] if far_off else None, "ground made": view[2] if view else None,
             "blocked looks": []}
    return (name, ("pieces", design, rows, relations, shell_rows, view and (view[0], view[1], view[3]), far_off,
                   judged_by.get("kinds", {})), None, {**expected, "laid": found}, laid_rows,
            [(fault, {}, laid_faults(edit), checks.FAIL if wanted else checks.PASS, tuple(wanted))
             for fault, edit, wanted in judged_by.get("faults", [])])


BUILDERS = {"plan": made, "held": held_world, "record": written, "pieces": laid_pieces,
            "made": lambda folder, make: (make(folder), None)}
READ = {"plan": plan_read, "held": lambda output, inputs: [], "record": record_read,
        "pieces": lambda laid, inputs: [(entry["name"], entry) for entry in laid["found"]],
        "made": lambda output, inputs: output}
# What the lit shed's lights hold (worked out in its row's words below), and which of them name each row.
LIT_EXPECTED = {
    "by row kinds": {"lights": Count(1), "lights.0.at.1": 9.5, "lights.0.from": Says("floodlight_tower"),
                     "lights.0.range": 14.25},
    "concept lights": {"lights": Count(10)}, "full core": {"lamps": Count(1)}, "bulbs": {"lamps": Count(1)},
    "lit 1": {"": As("by row kinds", "lights.0")},
    "lit 2": {"colour": "#44aaff", "from": (Says("its column"), Says("core")),
              "energy": Share(As("full core", "lamps.0.energy"), 0.5), "at": As("full core", "lamps.0.at")},
    **{f"lit {number}": {"at.0": x, "from": Says("faint emitter"),
                         "energy": Share(As("bulbs", "lamps.0.energy"), 0.1, within=1e-4)}
       for number, x in ((3, -2.25), (4, -0.75), (5, 1.5), (6, 2.5))},
    **{f"lit {number}": {"at": As(f"east wall spot {number - 6}", "at")} for number in (7, 8, 9)},
    "lit 10": {"at": As("west wall spot 1", "at")},
    "keypad door": {"share": 0.1, "as": "emitter"}, "light panel door": {"share": 1.0, "as": "source"}}
LIT_ROWS_LAID = {"floodlight_tower": ["lit 1"], "core": ["lit 2"], "screens": ["lit 3", "lit 4", "lit 5", "lit 6"],
                 "wall_panel": ["lit 7", "lit 8", "lit 9"], "west_panel": ["lit 10"]}
FURNISHED_STRUCTURE = {"deck_1": "slab", "wall_1": "slab", "wall_1_2": "slab", "wall_1_3": "slab", "wall_1_4": "slab",
                       "wall_2": "slab", "wall_3": "slab", "wall_3_2": "slab", "wall_3_3": "slab", "wall_4": "slab",
                       "roof_1": "slab", "stair_1": "stairs", "structural_ribs_1": "arch",
                       "structural_ribs_2": "arch",
                       **{f"kit_frames_wall_{wall}_{part}": "slab" for wall, parts in ((1, 3), (3, 2))
                          for part in range(1, parts + 1)}}
# Each world the record is written or judged on, with what its pieces hold and its verdicts: its builder and its
# arguments (None: none), what is read from it besides its own pieces, what its pieces hold, each row named with
# exactly the pieces that name it, and each verdict (its name, the edits made to the world's files first (`record`,
# `plans/<name>` or an input: a JSON in, a JSON out; each file put back after), its gate, and its answer (None:
# refused by name) with what its findings say: exactly a tuple, each of an Among, or a text (or texts) somewhere in
# them).
RECORD_ROWS = [
    ("the shed maps and holds its spots and items, its doors leading to the yard and outside", ("plan", SHED), None,
     {"plan": {"doors.0.leads": "yard", "doors.1.leads": "outside", "doors.2": ABSENT}}, {},
     [("it maps", {}, mapped, checks.PASS, None), ("it holds", {}, held, checks.PASS, None),
      ("a person spot and an item drawn outside the shed, never a duct on its wall's line",
       {"plans/shed": lambda drawn: {**drawn, "people": [[4.0, 3.0], [9.5, 3.0]],
                                     "items": [*drawn["items"], ["PIPE", -5.0, 3.0, 10.0, 0.1, None, "item"],
                                               ["DUCT", -0.1, 4.0, 0.2, 1.0, None, "item"]]}},
       held, checks.FAIL, ("shed's person spot 2 [9.5, 3.0] lies outside its 8.0 x 6.0 m plan",
                           "shed's item 'PIPE' [-5.0, 3.0, 10.0, 0.1] lies outside its 8.0 x 6.0 m plan"))]),
    ("an item with no rows", ("plan", {**SHED, "rows": {"DRIVE LANE": []}}), None, {}, {},
     [("it fails mapped", {}, mapped, checks.FAIL, "BENCH")]),
    ("a door that says nowhere it leads", ("plan", {**SHED, "leads": {"N": SHED["leads"]["N"]}}), None, {}, {},
     [("it fails mapped", {}, mapped, checks.FAIL, "door S")]),
    ("a sealed door the layout leaves open",
     ("plan", {**SHED, "leads": {**SHED["leads"], "N": {"to": "sealed", "why": "test"}}}), None, {}, {},
     [("it fails mapped", {}, mapped, checks.FAIL, "leaves it open")]),
    ("a written plan with no corner takes its outline, its walls square",
     ("plan", {**NO_CORNER, "outline": [[0.0, 0.0], [8.0, 0.0], [8.0, 6.0], [0.0, 6.0]]}), None,
     {"plan": {"walls.corner": 0.0, "walls.wide": 8.0, "walls.deep": 6.0}}, {},
     [("it maps", {}, mapped, checks.PASS, None)]),
    ("a plan with no corner and no outline", ("plan", NO_CORNER), None, {}, {},
     [("it is refused", {}, mapped, None, "no corner and no outline")]),
    ("two holds' outlines overlapping, and a place held once that more doors lead to than lead back", None, None, {},
     {}, [("overlapping", {}, lambda output, inputs: plan.overlap_faults({"holds": OVERLAPPING}), checks.FAIL,
           ("the outlines of hub and tube overlap, 0.97 m thick",)),
          ("held once", {}, lambda output, inputs: plan.once_faults(HELD_ONCE), checks.FAIL,
           ("tube is held once, but 2 doors of its siblings lead to it and 1 of its own lead back",))]),
    ("two doors on one wall, each by its own lead", ("made", two_doors), None,
     {"door 1": {"leads": "sealed"}, "door 2": {"leads": "yard"}, "door 3": ABSENT}, {},
     [("their openings", {}, lambda output, inputs: gates.door_faults(TWO_DOORS), checks.PASS, ())]),
    # the tube's hub end on the lab's door, the hub's record standing the instance its place's stage, its middle 3 m
    # east of the hub's door, stretched
    ("the base holds its tube turned and stretched", ("held", {"tube": TUBE, "hub": HUB, "lab": LAB, "base": BASE}),
     base_read, {"tube's hub end": {"at": [16.0, 5.0]},
                 "tube stood": {"name": "tube_1", "stage": "tube", "instance": "tube#1", "at": [8.0, 0.0, 0.0],
                                "scale": [1.0, 1.0, 1.5]}}, {},
     [("it holds", {}, held, checks.PASS, None),
      ("a door naming the tube, not its instance, and a hold another size than its plan laid in it",
       {"plans/hub": lambda hub: {**hub, "openings": [*hub["openings"], {"kind": "door", "at": [5.0, 10.0],
                                                                         "to": "tube"}]},
        "plans/base": lambda base: {**base, "holds": [base["holds"][0], {**TUBE_1, "d": 3.0}, base["holds"][2]]}},
       held, checks.FAIL, ("tube#1's hold is 6 x 3 m, its plan laid in it 6 x 2 m (turned 90)",
                           "hub's door to tube at [5.0, 10.0] names no instance of it (tube#1)",
                           *[f"{one}'s door to {other} at {at} opens 0.5 m from {other}'s nearest door back ({back}) "
                             "where the holder holds both" for one, other, at, back in (
                                 ("hub", "tube#1", [10.0, 5.0], [1.0, 4.0]), ("lab", "tube#1", [0.0, 2.0], [1.0, 0.0]),
                                 ("tube#1", "hub", [1.0, 4.0], [10.0, 5.0]),
                                 ("tube#1", "lab", [1.0, 0.0], [0.0, 2.0]))])),
      ("a hold turned 360 degrees",
       {"plans/base": lambda base: {**base, "holds": [base["holds"][0], {**TUBE_1, "turn": 360}, base["holds"][2]]}},
       held, None, "turns 360 degrees")]),
    # the tube's greenhouse end on the lab's corner, its box over both (its outline over neither), the lab sunk 1 m;
    # each record leads its doorways where its own hold leads them, its neighbours' doors leading back to that hold's
    # name: the tube stands the hub and the lab, the lab and the hub each tube#1, every door met (2026-11-06: the
    # base's tube met no door of the greenhouse or the hub back, which lead to its instance, and the airlock stood the
    # hub, which its hold leads past it to tube#3)
    ("the base holds its tube turned 315 degrees between the hub's corner door and the lab's",
     ("held", {"tube": TUBE, "hub": TURNED_HUB, "lab": TURNED_LAB, "base": TURNED_BASE}), turned_base_read,
     {"tube's greenhouse end": {"at": Near([CORNER, CORNER], 1e-6)},
      "box overlaps": {"found": ["the outlines of hub and tube#1 overlap, 0.50 m thick",
                                 "the outlines of tube#1 and lab overlap, 0.50 m thick"]},
      "levels": {"by place": {"hub": 0.0, "tube#1": 0.0, "lab": -1.0}},
      "tube's record": {"stands": ["hub", "lab"], "pairs": [], "leads": []},
      "lab's record": {"stands": ["tube#1"], "pairs": [], "leads": []},
      "hub's record": {"stands": ["tube#1"], "pairs": [], "leads": []}}, {},
     [("it holds", {}, held, checks.PASS, None)]),
    # the shed's record: its shell cut round its north door (wall 1 into four), its stair, its ribs as arched bands
    # (the first rib's item (0, 1) lies east-west across the shed, its 3.2 m span centred at plan x 4, its feet at
    # -1.6 and 1.6, z -1.9), the light 5% up its lamp's 0.2 m over its 2.7 m base, the Sun the physics sees, the yard
    # its door leads to where the site holds it, and only the views standing inside its walls; every prop row's plan
    # item has its object over its middle at its shape's base, waiting on its take's model (the bench item (1, 1)
    # 2 x 0.6 m at (-2, -1.7) on the shed centred on its 8 x 6 m, the lamp sharing the bench's take at its 2.7 m base,
    # the rail run three pieces along its polygon 0.5 m up, each its long side along the path); the plan's own floor
    # named on its deck; no surface library read, every piece carries no surface and says why; with the scene's
    # library made each takes its kind's, a stair the floor's, a roof the library names none for none, which the
    # scene builder names on its mesh, binding nothing; a flight drawn from its high end stands its foot at its low
    # end (its treads face up); the places its backdrop rows are shown from stand once each, the site at its own
    # plan's middle
    ("the furnished shed", ("record", FURNISHED, YARD, SITE, FURNISHED_HANDIN), furnished_read,
     {"record": {"place": "shed", "inside": True, "ceiling": 3.0, "lights": Count(1), "lights.0.at": [0.0, 2.71, 0.0],
                 "lights.0.from": Says("ceiling_lamp"), "environment.sky.lights": Count(1),
                 "environment.sky.lights.0.name": "Sun",
                 "environment.sky.lights.0.altitude": (As("sun seen", "altitude"), Over(0)),
                 "places": Count(1), "places.0.name": "yard", "places.0.at": [0.0, 0.0, -9.0],
                 "places.0.rotation": [0, 0, 0, 1], "objects": Count(5),
                 "structure": (Count(len(FURNISHED_STRUCTURE)),
                               Each({"surface": None, "surface_missing": Says("not made")}))},
      **{name: {"builder": builder} for name, builder in FURNISHED_STRUCTURE.items()},
      "deck_1": {"builder": "slab", "row": "shed_floor"},
      "stair_1": {"builder": "stairs", "foot": [2.5, 0.0, 1.0], "top": [2.5, 1.0, 3.0]},
      "stair drawn down": {"foot": [2.5, 0.0, 3.0], "top": [2.5, 1.0, 1.0]},
      "structural_ribs_1": {"builder": "arch", "plain": "shell", "feet": [[-1.6, -1.9], [1.6, -1.9]], "low": 0.0},
      "structural_ribs_2": {"builder": "arch", "plain": "shell"},
      "bench_1": {"at": [-2.0, 0.0, -1.7], "bake": "bench_1", "rotation": [0.0, 0.0, 0.0, 1.0],
                  "waiting": Says("surface line's bake")},
      "ceiling_lamp_1": {"bake": "bench_1", "at": [0.0, 2.7, 0.0]},
      "rail_1": {"at": [-1.6667, 0.5, 1.0], "rotation": [0.0, 0.0, 0.0, 1.0]},
      "rail_2": {"at": [0.0, 0.5, 2.0]}, "rail_3": {"at": [-2.6667, 0.5, 2.0]},
      "painted wall_1": {"surface": "painted_panel"}, "painted deck_1": {"surface": "deck_plate"},
      "painted stair_1": {"surface": "deck_plate"},
      "painted roof_1": {"surface": None, "surface_missing": Says("names no surface for the kinds a roof takes")},
      "rib mesh": {"low": Near([-1.6, 0.0, -2.0], 1e-6), "high": Near([1.6, 3.2, -1.8], 1e-6),
                   "prim's row": "structural_ribs"},
      "roof mesh": {"missing": Says("roof takes"), "bound": False},
      "shown 1": {"name": "yard"}, "shown 2": {"name": "site", "at": [10.0, 0.0, -5.0], "from": Says("palm_tree")},
      "shown 3": ABSENT},
     {"bench": ["bench_1"], "ceiling_lamp": ["ceiling_lamp_1"], "rail": ["rail_1", "rail_2", "rail_3"],
      "structural_ribs": ["structural_ribs_1", "structural_ribs_2", "painted structural_ribs_1",
                          "painted structural_ribs_2"],
      "view": ["from-door-1", "from-door-2", "spot-1"], "left out": ["spot-2"]},
     [*[(f"it passes {check.name}", {}, lambda output, inputs, check=check: check.judge(output, inputs, {}),
         checks.PASS, None) for check in gates.CHECKS],
      ("a door filled", {"record": lambda record: {**record, "structure": [*record["structure"], PLUG]}},
       matched, checks.FAIL, "filled by ['plug']"),
      ("the lamp moved off its item",
       {"record": lambda record: {**record, "lights": [{**record["lights"][0], "at": [3.0, 2.7, 0.0]}]}}, matched,
       checks.FAIL, "'LAMP' stands off"),
      ("a glowing row with no lamp", {"record": lambda record: {**record, "lights": []}}, matched,
       checks.FAIL, Among("glowing row ceiling_lamp has 0 lamps, its reading counts 1")),
      ("a glowing row one lamp short for no recorded reason", {"inventory": counted("ceiling_lamp", 2)},
       matched, checks.FAIL, ("glowing row ceiling_lamp has 1 lamps, its reading counts 2",
                              "row ceiling_lamp: 2 in the scene inventory, 1 laid, and the plan says no reason")),
      ("a glowing row the plan dropped one of (camp's monitors, 2026-11-11)",
       {"inventory": counted("ceiling_lamp", 2),
        "plans/shed": lambda drawn: {**drawn, "dropped": [{"item": "ceiling_lamp", "why": "cut: 1 laid", "laid": 1}]}},
       matched, checks.PASS, ()),
      ("a shell row the shell cannot build",
       {"hand-in": lambda handin: {**handin, "rows": [*handin["rows"], {"id": "landing_pad", "part": "floor",
                                                                        "route": "plan"}]}},
       matched, checks.FAIL, ("shell row landing_pad (floor) is built by no piece of the shell",))]),
    # a row with no size waits named; a row counting 5 on two items lays 3 and 2, and 1 and 1 where the plan dropped
    # three
    ("a run counted over its items, cut where the plan dropped some, and a row with no size",
     ("made", counted_runs), None,
     {"unsized rail_1": {"waiting": Says("row rail has no size")},
      **{f"five pipe_{number}": {"from": Starts(f"plan item 'PIPE {item}',")}
         for number, item in ((1, 1), (2, 1), (3, 1), (4, 2), (5, 2))},
      "dropped pipe_1": {"from": Starts("plan item 'PIPE 1',")},
      "dropped pipe_2": {"from": Starts("plan item 'PIPE 2',")}},
     {"pipe": ["five pipe_1", "five pipe_2", "five pipe_3", "five pipe_4", "five pipe_5", "dropped pipe_1",
               "dropped pipe_2"]}, []),
    # a block of no band, or a row of no structure, is not arched; a library's floor takes its own, never its edging,
    # a wall its first, a roof none
    ("an arched row, and a library's surface by kind", ("made", arched_and_painted), None,
     {"rib": {"arched": True}, "2 m deep rib": {"arched": False}, "rib object": {"arched": False},
      "edged": {"deck": "deck_floor_plate", "wall": "hull_panel", "roof": None}}, {}, []),
    ("a door to no place", ("record", NOWHERE, YARD, SITE, HANDIN), None, {}, {},
     [("its openings", {}, opened, checks.FAIL,
       ("opening 1 leads to 'moon_city', no place of the design nor a row of its inventory",
        "opening 1 leads to 'moon_city', its door row 'HATCH N, 1.2 x 2.1 m' to 'yard'"))]),
    ("a doorway narrower than its door row, its rows counted", ("record", NARROW, YARD, SITE, HANDIN), None, {}, {},
     [("its openings", {}, opened, checks.FAIL,
       ("opening 1 is 0.3 m wide for door row 'HATCH N, 1.2 x 2.1 m' of 1.2 m",)),
      ("a row laid fewer times than its inventory counts, the plan giving no reason",
       {"inventory": counted("bench", 2)}, matched, checks.FAIL, NO_REASON),
      ("a child scene's instance no doorway leads to is no reason",
       {"inventory": counted("bench", 2), "plans/shed": lambda drawn: {**drawn, **BENCH_HELD}}, matched, checks.FAIL,
       NO_REASON),
      ("laid as often as the doorways lead to its instances",
       {"inventory": counted("bench", 2),
        "plans/shed": lambda drawn: {**drawn, "holds": [*BENCH_HELD["holds"], {"place": "yard", "row": "yard",
                                                                              "leads": {"bench": "bench#1"}}]}},
       matched, checks.PASS, None)]),
    ("a row on its walls item and its own item laid once, at its own item", ("record", WALLED, YARD, SITE, HANDIN),
     None, {"record": {"lights": Count(1)}}, {"bench": ["bench_1"], "ceiling_lamp": ["ceiling_lamp_1"]},
     [("it is matched", {}, matched, checks.PASS, None)]),
    # the yard stands on the shed's door back, at its height, whatever the hold: held 2 m off its gate it still stands
    # there and the site's `held` fails on the hold and the door; its gate 3 m up stands the shed 3 m over it
    ("the site's yard held 2 m off its gate", ("record", WRITTEN, YARD, OFF_SITE, HANDIN), None,
     {"record": {"places": Count(1), "places.0.at": [0.0, 0.0, -9.0]}}, {},
     [("the shed's door meets the yard's gate", {}, opened, checks.PASS, None),
      ("the yard stood 5 m off its gate", {"record": moved_place}, opened, checks.FAIL, "opens 5.00 m along the floor"),
      ("the site's held", {}, site_held, checks.FAIL,
       ["yard's hold is 20.0 x 12.0 m, its yard item 20.0 x 12.0 m, their middles 2.0 m apart",
        "shed's door to yard at [4.0, 0.0] opens 2.0 m from yard's nearest door back"])]),
    ("the site holds the shed 3 m over the yard", ("record", WRITTEN, RAISED_YARD, SITE, HANDIN), raised_read,
     {"record": {"places": Count(1), "places.0.at": [0.0, -3.0, -9.0]}, "site": {"held places": 2}}, {},
     [("the shed's door meets the yard's gate", {}, opened, checks.PASS, None),
      ("the yard stood 5 m off its gate", {"record": moved_place}, opened, checks.FAIL, "opens 5.00 m along the floor"),
      ("the site's held", {}, site_held, checks.PASS, None)]),
    # a place on Mars, inside or out, has its dusty day sky (data/physics/dust.json, its source said), drawn
    # butterscotch, its red over its blue; one on the Moon none; the dust file is a declared input
    ("a place on mars has its dusty day sky", ("made", skies), None,
     {"yard on mars": {"sky_dome.depth": 0.6, "sky_dome.albedo": [0.975, 0.93, 0.86], "sky_dome.forward": 0.67,
                       "sky_dome.diffuse": 0.25, "sky_dome.gain": list(writer.SKY_GAIN),
                       "sky_dome.from": Says("Wolff et al. 2009"), "sky_dome.cited": ABSENT},
      "shed on mars": {"sky_dome": As("yard on mars", "sky_dome")}, "yard on the moon": {"sky_dome": ABSENT},
      "mars picture": {"red": Over(As("mars picture", "blue")), "blue": Over(0)},
      "yard's files": {"dust": "{data}/physics/dust.json"}}, {}, []),
    # its row kinds alone light the tower only, one library lamp near its top over its middle; its concept's light
    # lights the core in its blue at half strength, four monitors on two items as faint emitters at 0.1 of the lamp
    # (two lamps along each, at 1.75, 3.25, 5.5 and 6.5 m: x -2.25, -0.75, 1.5, 2.5 on the shed's 8 m), the west panel's
    # one lamp at plan (0.2, 3) 1.5 m up and the east panel's three at plan (7.8, 1, 3 and 5); a door whose concept
    # shows its keypad glowing is a faint emitter, its light panel a lamp still
    ("the lit shed", ("made", lit_shed), None, LIT_EXPECTED, LIT_ROWS_LAID,
     [("its lamps stand on their items and walls", {}, concept_lamps, checks.PASS, ()),
      ("the west panel's lamp moved off its wall", {}, lambda output, inputs: concept_lamps(output, inputs, 1.0),
       checks.FAIL, ("the light of plan item 'WEST PANEL' stands off its wall",))]),
    ("the record reads its relations and concept light where holders and plans keep them", ("made", kept_where), None,
     {"relations": {"kept": review_holders.KEPT}, "concept light": {"kept": review_plans.KEPT_LIGHT}}, {}, []),
]
ROWS = RECORD_ROWS + [pieces_row(*case) for case in CASES]


@pytest.mark.parametrize("world, reading, laid, laid_rows, verdicts", [row[1:] for row in ROWS],
                         ids=[row[0] for row in ROWS])
def test_a_scene_record_is_written_from_its_design(tmp_path, world, reading, laid, laid_rows, verdicts):
    """Each world of ROWS (a plan made of a record, a base's held plans, a record written from its design, the pieces
    a design lays, or what a writer's call returns) is built once through its real entry point, every piece it lays
    holds what its row says, each row names exactly its pieces, and each verdict its gates give on it (after the
    row's edits) answers as said. Worked out by hand on the plans above:
    The shed's plan maps, its doors leading to the yard and outside; an item with no rows, a door that says nowhere
    it leads and a sealed door the layout leaves open each fail `mapped` by name; a written plan (plan_writing's: an
    outline, no corner) makes its plan with square corners, its outline drawing every corner, and a plan with neither
    is refused by name.
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
    Break: score/stages/scene_record/writer.py design_objects: `if on and on["how"] == "wall" and
        plan_checks.connector(row):` -> `if False:` (the tunnel laid along its wall, across its doorway: workshop's
        glass tunnels, 2026-11-15)
    Break: score/stages/scene_record/writer.py item_way: `lambda across, along: min(across, along) <= ELONGATED *
        max(across, along))` -> `lambda across, along: False)` (galley's table laid across its box, 2026-11-15)
    Break: score/stages/scene_record/writer.py spots_of: `item_way(item, row) if band is None else band` ->
        `item_way(item, row)` (the tube laid north to south across its band), or band_way's
        `or min(size[0], size[1]) > BAND_SHARE * max(size[0], size[1])` dropped (the crate turned onto the band)
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
        else 0.0` (three panels' lamps on one spot)
    Each object, shell piece and view of a design stands, turns, is named and is marked as its plan item, its kept
    relations, the shell's own rows and its standing spots lay it (the cases in CASES, worked out by hand): past the
    plan's edge facing in, along its item's long side, at its relation's spot, edge or ramp, naming its holder, or
    marked unplaced, filling or unheld; each view's eye a person's height over what its spot stands on, looking where
    a person would.
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
    their row, painted (here named missing: no library), and so where the earth seed lays the shell, whose base lays
    only its deck, walls and roof (#128); its door frames are the wall kit's (score/stages/wall_kit), `slab` entries.
    Break: score/stages/scene_record/writer.py: `if words & FLOOR_WORDS:` -> `if False:`
    Break: score/stages/scene_record/writer.py: `name_open_cuts(design, shelled + flights, (rows or {}).get("opening",
        []))` -> `pass`
    Break: score/stages/scene_record/writer.py row_entries: `if not inside(design):` ->
        `if not inside(design) or design_shell.laid_for(design):`
    Break: score/stages/scene_record/writer.py record_of: the `kit_entries(...)` term dropped (the shed's frames gone)
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
    #128 (2026-11-15): a row's take is laid at the plan's flights it stands for, and no box flight is laid there.
    Break: score/stages/scene_record/writer.py structure: `if number not in taken]` -> `if True]` (box flights beside)
    Break: score/stages/scene_record/writer.py design_objects: `flights_named(design, handin, found)` -> `pass` (the
        ramp on its own item names no flight)
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
        names]` -> `pass` (no holders named), or its `if all(names):` -> `if any(names):` (held by one pole)
    Each view of a place (the view cases of CASES, worked out by hand) stands its eye a person's height over what its
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
    try:
        output, inputs = BUILDERS[world[0]](tmp_path, *world[1:]) if world else (None, None)
    except ValueError as refused:
        output, inputs = refused, None
    pairs = [] if world is None or isinstance(output, ValueError) else \
        [*READ[world[0]](output, inputs), *(reading(output, inputs) if reading else [])]
    found = dict(pairs)
    assert len(found) == len(pairs), [name for name, _ in pairs]
    design, sizes = (output["design"], output["sizes"]) if world and world[0] == "pieces" else (None, {})
    for name, wanted in laid.items():
        assert (name in found) != (wanted is ABSENT), (name, sorted(found))
        missed = [] if wanted is ABSENT else misfits(found[name], wanted, design,
                                                      sizes.get(found[name].get("row")), found)
        assert not missed, (name, missed)
    for row, names in laid_rows.items():
        assert [name for name, entry in found.items() if entry.get("row") == row] == names, (row, list(found))
    for name, edits, judge, answer, said in verdicts:
        got, findings = judged(output, inputs, edits, judge)
        assert got == answer and says(said, findings), (name, got, findings)
