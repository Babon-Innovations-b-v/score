"""The scene's invariant: a scene is made from its locked concept and nothing typed. Its inventory's rows stand on
boxes measured on the concept (never typed, never the whole picture, spread over it), an unmeasured box blocks the
close-ups; each close-up camera stands inside the world and frames its item; a cut-out too small never feeds the
redraw; one real-world object is made once; a scene's style is its design's alone; a lamp's light comes from the
library by its mount, never a typed number; no paid Marble call runs outside a cleared run; the ship's floor plan fits
its hull with rooms a person fits.

Every answer below is worked out by hand from a small fixture (a box room 8 m wide, boxes on a 2752 x 1536 concept,
a lamp at 3 m) or read from the owner's rules, never computed by the code under test.

Breaks that turn these red (each applied once, seen red, reverted, 2026-10-26; the inventory, duplicate, cut-out and
lamp breaks again 2026-11-14 on the merged test, the close-up, style, Marble and floor plan breaks later that day):
- box_check `spread_problems`: `if False:` for the one-quarter check -> test_a_scene_is_made_from_its_concept.
- box_check `box_problems`: `if False:` for the whole-picture check -> test_a_scene_is_made_from_its_concept.
- box_check `judge_rows`: drop `if not is_whole(...)` -> test_a_scene_is_made_from_its_concept.
- box_check `verdict`: `len(failing) < len(replies)` -> test_a_scene_is_made_from_its_concept.
- box_check `noun`: split on `[(;]` only (no colon or comma) -> test_a_scene_is_made_from_its_concept.
- box_check `grounding`: drop the `fills` condition -> test_a_scene_is_made_from_its_concept.
- box_check `from_proposals`: `return True` -> test_a_scene_is_made_from_its_concept.
- box_check `row_verdict`: an unmeasured box `return PASS` -> test_a_scene_is_made_from_its_concept.
- partition `mapping_problems`: `if False:` for the reasonless drop -> test_a_scene_is_made_from_its_concept.
- inventory `row_problems`: `if False:` for the unknown view -> test_a_scene_is_made_from_its_concept.
- inventory `approved_inventory`: `if False:` for the approval -> test_a_scene_is_made_from_its_concept.
- duplicates `pair_problem`: `if False:` for two takes -> test_a_scene_is_made_from_its_concept.
- cutsize `route`: `> MIN_CUT_SIDE` -> test_a_scene_is_made_from_its_concept.
- closeups `camera_for`: frame at 0.6 in place of FILL -> test_a_scene_is_made_from_its_concept.
- closeups `camera_for`: `distance = blocked` (no clearance) -> test_a_scene_is_made_from_its_concept.
- closeups `label_of`: keep the words after the comma -> test_a_scene_is_made_from_its_concept.
- closeups `resolve`: the lowest score wins -> test_a_scene_is_made_from_its_concept.
- place `read_look`: `if False:` for the kept look -> test_a_scene_is_made_from_its_concept.
- place `read_look`: `if False:` for the empty answer -> test_a_scene_is_made_from_its_concept.
- data/definitions/place.json: the shared rule "Modules, ships and moving parts are built in code." ->
  test_a_scene_is_made_from_its_concept.
- lamps `light_at`: no least reach -> test_a_scene_is_made_from_its_concept.
- lamps `on_stem`: `return False` -> test_a_scene_is_made_from_its_concept.
- marble `generate`, and apart `paint`: `pass` for `compute.require_cleared` -> test_a_scene_is_made_from_its_concept.
- data/definitions/ship_floor.json: a door 0.8 m wide -> test_a_scene_is_made_from_its_concept.
- ship_floor `overlap_faults`: `if False:` -> test_a_scene_is_made_from_its_concept.

    PROPS_HOME=$(mktemp -d) .venv/bin/python -m pytest tools/props/scene/test_a_scene_is_made_from_its_concept.py
"""
import copy
import json
import pathlib
import sys

import numpy as np
import pytest
from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import box_check  # noqa: E402
import closeups  # noqa: E402
import duplicates  # noqa: E402
import inventory  # noqa: E402
import lamps  # noqa: E402
import marble  # noqa: E402
import partition  # noqa: E402
import place  # noqa: E402
import ship_floor  # noqa: E402
from cutsize import MIN_CUT_SIDE, route, size_of  # noqa: E402

SIZE = (2752, 1536)


# ---- the boxes a scene's rows stand on -----------------------------------------------------------------------------

def a_row(name, box, **changes):
    row = {"id": name, "view": "v1", "box": box, "name": f"the {name}", "kind": "generate", "anchor": "floor",
           "size": [1.0, 0.5, 1.2], "count": 1, "thing": f"prop:{name}"}
    row.update(changes)
    return row


def an_inventory(rows, picture="WORK/v1.png"):
    return {"plan": {"views": [{"id": "v1", "picture": picture}]}, "rows": rows}


def spread_over_the_picture():
    """Twelve boxes drawn over the whole picture, as a partition drawn on the concept leaves them."""
    return [a_row(f"r{index}", [100 + 200 * index, 200 + 90 * (index % 4), 380 + 200 * index, 620 + 200 * (index % 4)])
            for index in range(12)]


def crowded(**changes):
    """The camp's door dome as it was: 24 round-number boxes reaching only x 1600, y 900 of the concept."""
    return [a_row(f"r{index}", [100 + 100 * (index % 6), 100 + 100 * (index // 6), 600 + 150 * (index % 6),
                                400 + 100 * (index // 6)], **changes) for index in range(24)]


# ---- the world: one concept, its proposals, the inventory mapped on them ------------------------------------------

WIDE, TALL = SIZE
# SAM 2.1's proposals on the concept: a galley, a drawer lying inside it (a part), a crate, and a big unnamed thing.
GALLEY, DRAWER = [113, 207, 391, 618], [120, 220, 200, 300]
CRATE, BIG = [1503, 811, 1702, 1033], [1800, 900, 2200, 1300]
PROPOSALS = [{"id": "v1.1", "view": "v1", "box": GALLEY, "area": 90000, "share": 0.02},
             {"id": "v1.2", "view": "v1", "box": DRAWER, "area": 5000, "share": 0.001},
             {"id": "v1.3", "view": "v1", "box": CRATE, "area": 30000, "share": 0.002},
             {"id": "v1.4", "view": "v1", "box": BIG, "area": 120000, "share": 0.03}]

# measured_problems on typed and measured boxes: (case, rows, picture size, fragments one problem holds together,
# fragments no problem holds, how many problems or None, or the exact list of problems).
WHOLE = [0, 0, WIDE, TALL]
SMALL = [a_row(f"r{index}", [200 + 400 * index, 700, 240 + 400 * index, 740]) for index in range(6)]
MEASURED = [
    ("spread over the picture", spread_over_the_picture(), SIZE, [], [], 0),
    ("typed and crowded in a corner", crowded(), SIZE, [("one quarter",), ("span only",)], [], None),
    ("crowded but measured", crowded(box_from=["v1.1"]), SIZE, [], [], 0),
    ("six small boxes", SMALL, SIZE, [("cover", "its rows suggest")], [], None),
    ("a few far things may be small", SMALL[:4], SIZE, [], ["its rows suggest"], None),
    ("a box over the edge", spread_over_the_picture() + [a_row("over", [2600, 1400, 2900, 1600])], SIZE,
     [("row over", "not inside")], [], None),
    ("whole-picture boxes, kit rows too", spread_over_the_picture() + [
        a_row("wall_lower", WHOLE, group="kit: wall", repeats="across the room"),
        a_row("desk", WHOLE, group="kit: furniture"), a_row("rack", WHOLE)], SIZE,
     [("row wall_lower", "whole picture"), ("row desk", "whole picture"), ("row rack", "whole picture")], [], 3),
    ("an unseen row", spread_over_the_picture() + [a_row("hidden", None, unseen="behind the camera")], SIZE, [], [], 0),
    ("its picture missing", spread_over_the_picture() + [a_row("hidden", None, unseen="behind the camera")], None,
     [], [], ["view v1: its picture is missing"]),
]

# The words SAM 3 is asked for a row's name: its short name, then its last word when that is shorter.
NOUNS = [("stainless galley counter: worktop with hob and sink", ["stainless galley counter", "counter"]),
         ("a strip lamp in a steel housing with a frosted lens, over a door", ["strip lamp", "lamp"]),
         ("lamp on a rod from the ceiling: housing and lens", ["lamp"]),
         ("plain lower wall panel, bolted", ["plain lower wall panel", "panel"]),
         ("hammer", ["hammer"])]

# The judge's replies for one box and its verdict.
SHOWN = 'thinking... {"shows": true, "main": true, "what": "a locker"}'
BESIDE = '{"shows": true, "main": false, "what": "the wall beside a locker"}'
ON_A_WALL = '{"shows": false, "main": false, "what": "a wall"}'
VERDICTS = [([SHOWN, SHOWN, BESIDE], {"passes": True, "passed": 2, "of": 3, "what": "the wall beside a locker"}),
            ([SHOWN, BESIDE, "no answer at all"], {"passes": False, "passed": 1, "of": 3,
                                                   "what": "the wall beside a locker"})]

# SAM 3's instances of each row's words, and what they say of its box. The whole room says nothing.
INSIDE = {"box": [10, 10, 50, 50], "score": 0.9, "inside": 0.9, "fills": 0.6}
TINY = {"box": [10, 10, 14, 14], "score": 0.9, "inside": 1.0, "fills": 0.01}
ELSEWHERE = {"box": [900, 10, 990, 80], "score": 0.8, "inside": 0.0, "fills": 0.0}
ROOM = {"box": [0, 0, 2700, 1500], "score": 0.9, "inside": 0.02, "fills": 0.9}
KEYS = {"box": [400, 300, 520, 340], "score": 0.9, "inside": 1.0, "fills": 0.02}
GROUNDING = {"camp.galley": ([ELSEWHERE, INSIDE], {"grounding": "grounded"}),
             "camp.crate": ([ELSEWHERE], {"grounding": "off", "found_at": ELSEWHERE["box"]}),
             "camp.net": ([ROOM], {"grounding": "not found"}),
             "camp.bin": ([], {"grounding": "not found"}),
             "camp.keyboard": ([ELSEWHERE, TINY], {"grounding": "loose", "found_at": TINY["box"]}),
             "camp.wall": ([ROOM, KEYS], {"grounding": "loose", "found_at": KEYS["box"]})}

# Rows added to the mapped world one at a time and the gate's word on each: (row, box, box_from, route, the routes
# passed unboxed, the row's result, words of its why, the scene's result).
GATE = [
    ("moved", [1503, 811, 1702, 1040], ["v1.3"], None, (), "fail", "not the box round", "fail"),  # moved by hand
    ("typed", [600, 200, 900, 640], None, None, (), "fail", "typed", "fail"),  # round numbers (the camp's, 2026-10-09)
    ("whole", WHOLE, None, None, (), "fail", "whole picture", "fail"),
    ("table", GALLEY, ["v1.3"], None, (), "fail", "not the box round", "fail"),  # names a proposal not its own
    ("bunk", [1200, 300, 1300, 400], ["v1.1"], None, (), "fail", "not the box round", "fail"),  # outside its thing
    ("unmeasured", [1503, 811, 1701, 1033], None, None, (), "unknown", "not measured", "unknown"),
    ("ground", WHOLE, None, "ground", box_check.UNBOXED, "pass", "not boxed", "pass"),  # laid from the plan
    ("ground", WHOLE, None, "ground", (), "fail", "whole picture", "fail"),  # the close-ups crop by the box
    ("ground", WHOLE, None, "prop", box_check.UNBOXED, "fail", "whole picture", "fail"),
]

# Rows added to the mapped inventory, or changes to the inventory itself, and its shape problems: (case, row or None,
# the inventory's changes, fragments one problem holds together, how many problems or None).
SEEN = [10, 20, 300, 400]
SHAPE = [
    ("a row on a view the plan lacks", a_row("hood", SEEN, view="v9"), {}, [("row hood", "no box, no row")], None),
    ("no box and no reason", a_row("hood", None), {}, [("row hood", "no 'unseen'")], None),
    ("a wrong kind, anchor, size and count",
     a_row("hood", SEEN, kind="shared", anchor="somewhere", size=[1, 0, 1], count=0), {}, [], 4),
    ("on a row of the scene", a_row("hood", SEEN, anchor="on:galley"), {}, [], 0),
    ("on no row of the scene", a_row("hood", SEEN, anchor="on:r7"), {}, [("row hood", "anchor 'on:r7'")], 1),
    ("a mechanic naming no prop", a_row("hood", SEEN, kind="mechanic", thing="node:Workstation"), {},
     [("row hood", "mechanic row")], 1),
    ("a mechanic naming its prop", a_row("hood", SEEN, kind="mechanic", thing="node:Workstation", prop="desk"), {},
     [], 0),
    ("migrated without approval", None, {"approved": "", "migrated": "2026-10-06"}, [("approval",)], None),
]


def a_made_row(name, kind="generate", **changes):
    return {"id": name, "kind": kind, "name": f"the {name}", **changes}


# Two places' made rows naming one object, the takes each is made from, and the duplicate problems: (case, hub's row,
# lab's row, takes, fragments one problem holds together, how many problems or None). The owner, 2026-10-09: no
# duplicates; reuse first.
KETTLES = {"hub": {"kettle": "kettle-r1"}, "lab": {"kettle": "kettle-r2"}}
DUPLICATES = [
    ("made twice", a_made_row("desklamp"), a_made_row("desklamp"),
     {"hub": {"desklamp_1": "desklamp-r6"}, "lab": {"desklamp_1": "desklamp-lab1"}}, [("made twice",)], 1),
    ("one take in both", a_made_row("desklamp"), a_made_row("desklamp"),
     {"hub": {"desklamp_1": "desklamp-r6"}, "lab": {"desklamp_1": "desklamp-r6"}}, [], 0),
    ("about to be made again", a_made_row("kettle"), a_made_row("kettle"), {"hub": {"kettle": "kettle-r1"}, "lab": {}},
     [("not made yet",)], 1),
    ("far scenery names the same object", a_made_row("far_palm"), a_made_row("palm"),
     {"hub": {"far_palm": "palm-a"}, "lab": {"palm": "palm-b"}}, [], 1),
    ("its own model, said why", a_made_row("power_unit"),
     a_made_row("power_unit", own_model="a battery cabinet, not the small ground power unit"),
     {"hub": {"power_unit": "power_unit-g1"}, "lab": {"power_unit": "power_unit-r3"}}, [], 0),
    ("a reuse made from another take", a_made_row("kettle"), a_made_row("kettle", reuse="hub:kettle"), KETTLES,
     [("made from kettle-r2",)], None),
    ("a reuse of no row", a_made_row("kettle"), a_made_row("kettle", reuse="hub:pot"), KETTLES,
     [("no inventory row",)], None),
    ("built in code", a_made_row("conduit_box", "code"), a_made_row("conduit_box", "code"), {}, [], 0),
    ("a scene whose takes are not stored", a_made_row("kettle"), a_made_row("kettle"),
     {"hub": {"kettle": "kettle-r1"}}, [], 0),
]

# Which way a cut-out is drawn, by its short side (the owner, 2026-10-02: "the low-res ones look shit"): (box, whether
# a close-up can be made, route). Round one's habitat: the bench and counter cabinet made models, the desk and desk
# lamp did not.
ROUTES = [([0, 0, MIN_CUT_SIDE, 2 * MIN_CUT_SIDE], True, "redraw"),
          ([0, 0, MIN_CUT_SIDE, MIN_CUT_SIDE], False, "redraw"),
          ([0, 0, MIN_CUT_SIDE - 1, 760], True, "close-up"), ([0, 0, MIN_CUT_SIDE - 1, 760], False, "dropped"),
          ([274, 371, 508, 616], False, "redraw"), ([926, 443, 1170, 731], False, "redraw"),
          ([812, 401, 984, 559], False, "dropped"), ([901, 326, 933, 419], False, "dropped")]

LAMP_LIBRARY = {"ceiling": {"high": 0.05, "reach_per_height": 2.0, "least_reach": 1.5, "strength_per_reach": 0.05,
                            "shadows": True},
                "wall": {"high": 0.5, "reach_per_height": 1.5, "least_reach": 1.5, "strength_per_reach": 0.04,
                         "shadows": False},
                "stands": {"high": 0.5, "reach_per_height": 1.5, "least_reach": 1.5, "strength_per_reach": 0.03,
                           "shadows": False}}
# A reading's rows as the creator's kept scene inventories carry them: each anchored on the row it rests on.
READING = [{"id": "floor_plates", "noun": "floor plates", "anchor": "ground"},
           {"id": "left_wall", "noun": "wall", "anchor": "on:floor_plates"},
           {"id": "roof_dome", "noun": "roof", "anchor": "on:left_wall"},
           {"id": "ceiling_beam", "name": "ceiling beam", "noun": "beam", "anchor": "roof"},
           {"id": "ribs", "noun": "ribs", "anchor": "on:left_wall"},
           {"id": "desk", "noun": "desk", "anchor": "floor"},
           {"id": "loop_a", "noun": "frame", "anchor": "on:loop_b"},
           {"id": "loop_b", "noun": "frame", "anchor": "on:loop_a"},
           {"id": "mast", "noun": "mast", "anchor": "ground", "size": [0.3, 0.3, 6.0]}]
WORDS = {"ceiling": ["ceiling", "roof"], "wall": ["wall", "walls"]}


def a_lamp(anchor, name="lamp", noun="lamp", size=None):
    return {"id": name, "name": name.replace("_", " "), "noun": noun, "anchor": anchor,
            **({"size": size} if size else {})}


# How a lamp is mounted: `on:<row>` is the held row's noun, else its own anchor, else what it is on in turn; a desk
# lamp stands. A street lamp 5 m tall on 0.4 m, or a light on a 6 m mast, is at its head; a squat tower and a table
# lamp stand (by their metres only).
MOUNTS = [(a_lamp("on:roof_dome"), "ceiling"), (a_lamp("on:left_wall"), "wall"), (a_lamp("on:ceiling_beam"), "ceiling"),
          (a_lamp("on:ribs"), "wall"), (a_lamp("on:desk"), "stands"), (a_lamp("on:loop_a"), "stands"),
          (a_lamp("on:nothing"), "stands"), (a_lamp("floor"), "stands"),
          (a_lamp("ground", "street_lamp", size=[0.4, 0.4, 5.0]), "head"),
          (a_lamp("on:mast", "light", "light", [0.5, 0.3, 0.4]), "head"),
          (a_lamp("ground", "floodlight_tower", "tower", [3.0, 3.0, 4.0]), "stands"),
          (a_lamp(None, "table_lamp"), "stands")]


def laid(*heights):
    return [{"kind": "x_lamp", "at": [0.0, height, 0.0]} for height in heights]


# A lamp's light is the library's for its mount, never a typed number (owner, 2026-10-21): (row, its laid pieces,
# light). A ceiling lamp whose pieces hang at 3.0, 3.0 and 3.2 m hangs at their middle, 3.0 m: reach 2.0 x 3.0 = 6.0 m,
# strength 0.05 x 6.0 = 0.3; a lens part is not where it hangs; a wall lamp at 0.5 m keeps the least reach 1.5 m
# (strength 0.04 x 1.5 = 0.06); a locker with a typed light is no lamp; a light on the roof is a ceiling lamp (2.5 m:
# reach 5.0, strength 0.25).
CEILING_AT_3 = {"strength": 0.3, "reach": 6.0, "high": 0.05, "shadows": True}
LIGHTS = [(a_lamp("ceiling", "pendant") | {"made": "kit piece"}, laid(3.0, 3.0, 3.2), CEILING_AT_3),
          (a_lamp("ceiling"), laid(3.0) + [{"kind": "x_lamp", "at": [0.0, 0.0, 0.0], "part": "glow"}], CEILING_AT_3),
          (a_lamp("wall", "sconce", "light"), laid(0.5), {"strength": 0.06, "reach": 1.5, "high": 0.5,
                                                         "shadows": False}),
          (a_lamp("floor", "locker", "locker") | {"light": {"strength": 9.0, "reach": 9.0}}, laid(0.0), None),
          (a_lamp("on:roof_dome", "roof_light", "light"), laid(2.5), {"strength": 0.25, "reach": 5.0, "high": 0.05,
                                                                      "shadows": True})]


def problems_hold(problems, has, lacks, count):
    """Whether `problems` holds each group of `has` in one line, no line holds any of `lacks`, and there are `count`
    of them when `count` is a number, or they are exactly `count` when it is a list."""
    exact = problems == count if isinstance(count, list) else len(problems) == count
    return (all(any(all(part in line for part in group) for line in problems) for group in has)
            and not any(part in line for part in lacks for line in problems)
            and (count is None or exact))

# ---- the close-up cameras ------------------------------------------------------------------------------------------

DOWN = [0, 1, 0]


def solid(low, high):
    """The twelve triangles of a box from corner `low` to corner `high`."""
    corners = np.array([[x, y, z] for x in (low[0], high[0]) for y in (low[1], high[1]) for z in (low[2], high[2])],
                       dtype=float)
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    return np.array([[corners[a], corners[b], corners[c]] for a, b, c, d in faces
                     for a, b, c in ((a, b, c), (a, c, d))])


def box_room(half=4.0):
    """A closed room in Marble's frame (y down): x and z from -half to half, ceiling at y -1.5, floor at y 1.5."""
    return solid([-half, -1.5, -half], [half, 1.5, half])


def wall_item(**changes):
    """A rack against the north wall (z = +4), facing south into the room."""
    return {"id": "rack", "centre": [0.0, 0.55, 3.7], "size": [0.6, 0.6, 1.9], "facing": [0, 0, -1], **changes}


def framed(camera, points):
    """The pixels `points` land on in `camera`'s picture."""
    view = closeups.view_matrix(camera["eye"], camera["target"], DOWN)
    return closeups.project(points, view, closeups.lens(camera["fov"], camera["size"]))


# The 8 m room's items: the rack, a locker beside it and a rack on the far wall facing back.
ITEMS = [wall_item(name="equipment rack, 0.6 m"), wall_item(id="locker", name="tall locker", centre=[0.9, 0.55, 3.7]),
         wall_item(id="far", centre=[0.0, 0.55, -3.7], facing=[0, 0, 1])]
# A rack's front shot in tighter rooms: (case, item, room, words its note holds or None when it is dropped, the
# lowest z its eye may stand at, whether its lens is wider than FOV_DEGREES, whether its eye is above the rack's
# middle; None where the case says nothing of it). A wall 1.4 m behind leaves 0.25 m clearance; a 0.5 m room has
# nowhere to stand; a wall 1.2 m tall at z 2.8 to 3.0 blocks the level shot, which is raised over it.
STANDS = [("a wall behind", wall_item(centre=[0.0, 0.55, 1.1]), box_room(half=1.4), "pulled in",
           -1.4 + closeups.CLEARANCE_M - 1e-6, True, None),
          ("no room to stand", wall_item(centre=[0.0, 0.55, 0.2]), box_room(half=0.5), None, None, None, None),
          ("a low wall in the way", wall_item(), np.concatenate([box_room(), solid([-4.0, 0.3, 2.8], [4.0, 1.5, 3.0])]),
           "raised", None, None, True)]


def columns(*spans, shape=(4, 4)):
    """A mask true over the column `spans` of every row."""
    mask = np.zeros(shape, bool)
    for span in spans:
        mask[:, span] = True
    return mask


# Two masks over a 4 x 4 picture (columns 0-2 and 1-3), their scores, and each pixel's owner: the higher score wins
# the shared columns, -1 where no mask lies.
OWNERS = [([columns(slice(0, 3)), columns(slice(1, 4))], [0.6, 0.9], [[0, 1, 1, 1]] * 4),
          ([columns(slice(0, 3)), columns(slice(1, 4))], [0.9, 0.6], [[0, 0, 0, 1]] * 4),
          ([columns(shape=(2, 2))], [0.9], [[-1, -1]] * 2)]
CUT_MASK = np.zeros((50, 50), bool)
CUT_MASK[10:30, 20:40] = True
# A cut-out of a 50 x 50 picture: (mask, margin, its shape and how much of it is opaque, or None). 20 x 20 with a 10%
# margin a side is 24 x 24, its 400 pixels opaque; an empty mask cuts nothing.
CUTS = [(CUT_MASK, 0.1, ((24, 24, 4), 20 * 20 * 255)), (np.zeros((50, 50), bool), 0.06, None)]
# How a 2 x 0.5 x 1 m item looks: (turn, tilt, wide, tall, reach, tolerance). Turned 90 degrees it shows its 0.5 m
# side and reaches half its 2 m width.
EXTENTS = [(0.0, 0.0, (2.0, 1.0, 0.25), 0.0), (90.0, 0.0, (0.5, 1.0, 1.0), 1e-9)]

# A scene's style asked for without what it needs: (case, scene, the look's answer or None for asking what is
# unread, the refusal). The garden shed's look coming back empty keeps nothing.
REFUSED = [("no locked concept, its style", "lab", "x", "no locked concept"),
           ("no locked concept, what is unread", "lab", None, "no locked concept"),
           ("an empty look", "garden_shed", " ", "came back empty")]


def a_design(folder, scene, sha, colour):
    """A store in `folder` holding one locked concept of `scene`: its picture (a plain `colour` PNG) and its lock."""
    _, _, Store = place.design()
    store = Store.in_folder(folder)
    objects = pathlib.Path(folder) / "objects"
    (objects / "blobs").mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (64, 36), colour).save(objects / "blobs" / sha, "PNG")
    picks = objects / "concepts" / scene / "picks"
    picks.mkdir(parents=True, exist_ok=True)
    (picks / f"{len(list(picks.iterdir())):04d}.json").write_text(json.dumps(
        {"place": scene, "sha": sha, "by": "owner", "at": "2026-10-21T10:00:00+00:00", "environment": None}))
    return store


# ---- the ship's floor plan -----------------------------------------------------------------------------------------

FLOOR = ship_floor.read_floor()
# One change to the plan and its faults: (case, space, the field's path, its new value, faults it holds whole, words
# some fault holds). Storage moved onto the cockpit; the engine room's floor under the keel; the galley's only door
# led to a bridge the plan lacks.
REPLANNED = [("as drawn", None, (), None, [], []),
             ("an overlap", "storage", ("y",), [18.0, 27.2], ["cockpit and nav and storage overlap"], []),
             ("a floor under the keel", "engine and power room", ("floors",), [[31.5, 2.4]], [],
              ["over its floor's structure"]),
             ("a door to nowhere", "galley", ("doors", 0, "leads"), "bridge",
              ["galley: a door leads to bridge, no space of the plan", "galley: no door to the walkway"], [])]


def space_named(floor, name):
    return next(space for space in ship_floor.spaces(floor) if space["name"] == name)


def test_a_scene_is_made_from_its_concept(tmp_path, monkeypatch):
    """A scene's rows stand on boxes measured on its concept. Tiles cover the concept; every SAM 2.1 proposal is mapped
    to a row, dropped with a reason or named new (a part of a mapped one needs nothing), and a pointer only picks
    proposals: a row's box is its proposals' own. The gate passes only a measured box checked on that very box,
    blocks an unmeasured one and fails a typed, whole-picture or moved one; boxes typed into one corner fail; the judge
    sees the whole picture and the crop of every box but a kit row's whole picture, once a seed, its majority decides
    and a third seed breaks only a tie; SAM 3 is asked for a row's short name, a box it grounds passes, a loose one is
    tightened to the thing inside it, and words found elsewhere leave the box to the judge. The inventory those rows
    make says where each row is seen and what it is, and the cloud builds only from it sound and approved; one
    real-world object across places is made once unless a row says why; a cut-out under the limit never feeds the
    redraw; a lamp in it is mounted as what holds it, and its light is the library's for that mount. Each item's
    close-up cameras stand inside the world framing it upright from its turn, carrying the items they see with their
    boxes and words; a wall behind pulls a camera in, a low wall raises it, no room drops it; a pixel has one owner
    and a cut-out keeps only its pixels. A scene's style is its environment's line and its locked concept's look,
    read once a lock and refused without a lock or a look; every place keeps only its name and style. No Marble world
    or painting is bought outside a cleared run. The ship's floor plan fits its 46 m hull with rooms a person fits,
    and an overlap, a floor under the keel and a door to nowhere are its faults."""
    picture = tmp_path / "concept.png"
    Image.new("RGB", SIZE, (90, 90, 90)).save(picture)
    monkeypatch.setattr(box_check, "PARTITION", tmp_path / "partition")
    folder = tmp_path / "partition" / "camp"
    folder.mkdir(parents=True)
    (folder / "proposals.json").write_text(json.dumps(PROPOSALS))

    def the_place():
        return {"scene": "camp", "place": "camp", "approved": "2026-10-05, plan: w1", "migrated": "",
                "room": {"shell": "abc", "light": "place", "backdrop": "", "wall_fill": []},
                **an_inventory([a_row("galley", None, unseen="x"), a_row("crate", None, unseen="x"),
                                a_row("wall", None, unseen="x", group="kit: wall", repeats="across the room")],
                               str(picture))}

    tiles = [box for _, _, box in partition.tile_boxes(SIZE)]
    assert (min(box[0] for box in tiles), min(box[1] for box in tiles), max(box[2] for box in tiles),
            max(box[3] for box in tiles)) == (0, 0, WIDE, TALL)

    unboxed = the_place()
    for row in unboxed["rows"]:
        row.pop("unseen")
    problems = partition.mapping_problems(unboxed, PROPOSALS, {"v1.1": {"row": "galley"}, "v1.3": {"drop": ""},
                                                               "v1.4": {"row": "wall"}})
    assert problems == ["proposal v1.3 is dropped without a reason", "row crate has no proposal and no 'unseen' reason"]
    problems = partition.mapping_problems(unboxed, PROPOSALS, {"v1.1": {"row": "galley"},
                                                               "v1.3": {"rows": ["crate", "wall"]}})
    assert problems == ["proposal v1.4 is neither mapped to a row nor dropped with a reason"]  # v1.2 is v1.1's part

    found = the_place()
    mapping, matched = partition.snap(found, PROPOSALS,
                                      {"galley": [100, 200, 400, 630], "crate": [1490, 800, 1710, 1040]})
    assert matched["galley"]["proposals"] == ["v1.1", "v1.2"] and matched["crate"]["proposals"] == ["v1.3"]
    assert mapping == {"v1.1": {"rows": ["galley"]}, "v1.2": {"rows": ["galley"]}, "v1.3": {"rows": ["crate"]}}
    mapping["v1.3"]["rows"].append("wall")
    mapping["v1.4"] = {"new": "a crate"}
    new = partition.apply(found, PROPOSALS, mapping)
    assert [(row["id"], row["box"], row["box_from"], "unseen" in row) for row in found["rows"]] == [
        ("galley", GALLEY, ["v1.1", "v1.2"], False),  # the proposals' own box, never the pointer
        ("crate", CRATE, ["v1.3"], False), ("wall", CRATE, ["v1.3"], False)]
    assert [(element["words"], element["box"]) for element in new] == [("a crate", BIG)]

    (folder / "boxes.json").write_text(json.dumps({name: {"passes": True, "by": "SAM 3: grounded", "box": box}
                                                   for name, box in (("galley", GALLEY), ("crate", CRATE),
                                                                     ("wall", CRATE))}))
    verdict = box_check.gate("camp", found)
    assert verdict["result"] == "pass" and {row["result"] for row in verdict["rows"].values()} == {"pass"}, verdict
    for name, box, source, routed, routes, result, why, scene in GATE:
        added = copy.deepcopy(found)
        added["rows"].append(a_row(name, box, **({"box_from": source} if source else {}),
                                   **({"route": routed} if routed else {})))
        verdict = box_check.gate("camp", added, routes)
        case = f"{name} routed {routed} under {routes}"
        assert verdict["rows"][name]["result"] == result and why in verdict["rows"][name]["why"], (case, verdict)
        passed_unboxed = [name] if routed in routes else []
        assert verdict["result"] == scene and verdict["unboxed"] == passed_unboxed, (case, verdict)

    for case, rows, size, has, lacks, count in MEASURED:
        problems = box_check.measured_problems(an_inventory(rows), {"v1": size})
        assert problems_hold(problems, has, lacks, count), (case, problems)

    for words, expected in NOUNS:
        assert box_check.nouns(words) == expected and box_check.noun(words) == expected[0], words

    judged = copy.deepcopy(found)
    judged["rows"] += [a_row("net", [700, 400, 900, 700]), a_row("keyboard", [1000, 300, 1400, 600]),
                       a_row("wall_kit", WHOLE, group="kit: wall")]
    jobs = box_check.judge_jobs("camp", judged, {"v1": SIZE}, tmp_path / "judge", box_check.SEEDS)
    first, second, third = box_check.SEEDS
    keys = [f"camp.{name}.{'-'.join(map(str, box))}" for name, box in (
        ("galley", GALLEY), ("crate", CRATE), ("wall", CRATE), ("net", [700, 400, 900, 700]),
        ("keyboard", [1000, 300, 1400, 600]))]  # the kit wall's whole picture is not asked about
    assert [job["name"] for job in jobs] == [f"{key}~{seed}" for key in keys for seed in box_check.SEEDS]
    whole, cut = (pathlib.Path(path) for path in jobs[0]["images"])
    assert Image.open(whole).width == box_check.OVERVIEW_WIDE
    assert max(Image.open(cut).size) >= box_check.SHORTEST_CROP
    assert "the galley" in jobs[0]["text"]
    assert box_check.mask_jobs("camp", judged, {"v1": SIZE}) == [
        {"picture": str(picture), "rows": [{"key": f"camp.{row['id']}", "nouns": [row["id"]], "box": row["box"]}
                                           for row in judged["rows"]]}]

    for replies, expected in VERDICTS:
        assert box_check.verdict(replies) == expected, replies
    answers = tmp_path / "answers"
    answers.mkdir()
    galley, crate, _, net, _ = keys  # the wall and the keyboard are not answered yet
    for name, text in ((f"{galley}~{first}", ON_A_WALL), (f"{galley}~{second}", ON_A_WALL),
                       (f"{net}~{first}", ON_A_WALL), (f"{net}~{second}", ON_A_WALL),
                       (f"{crate}~{first}", SHOWN), (f"{crate}~{second}", ON_A_WALL)):
        (answers / f"{name}.txt").write_text(text)
    assert [job["name"] for job in box_check.deciding_jobs(jobs, answers)] == [f"{crate}~{third}"]
    agreed = {"passes": False, "passed": 0, "of": 2, "what": "a wall"}
    assert box_check.verdicts(jobs, answers) == {galley: agreed, net: agreed}  # the split crate waits on its third
    (answers / f"{crate}~{third}.txt").write_text(SHOWN)
    verdicts = box_check.verdicts(jobs, answers)
    assert verdicts[crate] == {"passes": True, "passed": 2, "of": 3, "what": "a wall"}

    grounded = {}
    for key, (instances, expected) in GROUNDING.items():
        grounded[key] = box_check.grounding(instances, SIZE)
        assert grounded[key] == expected, key
    results = box_check.decided(grounded, verdicts)
    assert {key: results[key]["passes"] for key in GROUNDING} == {
        "camp.galley": True,  # SAM 3 grounds it over the judge
        "camp.crate": True,  # SAM 3 finding the words elsewhere leaves the box to the judge
        "camp.net": False, "camp.bin": None, "camp.keyboard": None, "camp.wall": None}
    assert box_check.tighten("camp", judged, grounded) == ["wall", "keyboard"]  # a repeating row boxes one example
    boxes = {row["id"]: row["box"] for row in judged["rows"]}
    assert boxes["wall"] == KEYS["box"] and boxes["keyboard"] == TINY["box"] and boxes["galley"] == GALLEY

    assert inventory.problems(the_place(), "camp") == [] and inventory.problems(found, "camp") == []
    for case, row, changes, has, count in SHAPE:
        changed = copy.deepcopy(found) | changes
        changed["rows"] += [row] if row else []
        problems = inventory.problems(changed, "camp")
        assert problems_hold(problems, has, [], count), (case, problems)
    for scene, kept in inventory.every_inventory().items():  # every committed inventory is sound
        if not kept.get("no_place"):  # a line no place owns (the people's looks, #41): no scene's inventory
            assert inventory.problems(kept, scene) == [], scene
    path = tmp_path / "inventory" / "camp.json"
    with pytest.raises(SystemExit, match="no inventory"):
        inventory.approved_inventory(path)
    path.parent.mkdir()
    path.write_text(json.dumps(found | {"approved": ""}))
    with pytest.raises(SystemExit, match="not approved"):
        inventory.approved_inventory(path)
    path.write_text(json.dumps(found))
    assert inventory.approved_inventory(path) == found  # the cloud builds from it once approved

    for case, first, second, takes, has, count in DUPLICATES:
        problems = duplicates.problems({"hub": {"rows": [first]}, "lab": {"rows": [second]}}, takes)
        assert problems_hold(problems, has, [], count), (case, problems)

    assert size_of([10, 20, 110, 320]) == {"width": 100, "height": 300, "short_side": 100, "area": 30000}
    for box, can_close_up, expected in ROUTES:
        assert route(box, can_close_up) == expected, (box, can_close_up)

    for lamp, expected in MOUNTS:
        assert lamps.mount_of(lamp, READING, WORDS) == expected, lamp
    for lamp, pieces, expected in LIGHTS:
        assert lamps.light_of(lamp, pieces, READING, library=LAMP_LIBRARY, words=WORDS) == expected, lamp
    assert "head" not in lamps.mount_words() and lamps.mounts()["head"]["high"] > 0.9
    assert {"ceiling", "roof"} <= set(lamps.mount_words()["ceiling"]) and "wall" in lamps.mount_words()["wall"]
    assert {name: set(lamps.mounts()[name]) for name in LAMP_LIBRARY} == {
        name: set(lamp) for name, lamp in LAMP_LIBRARY.items()}  # the fixture's lamps carry the library's fields

    room = box_room()
    planned = closeups.plan(room, ITEMS, DOWN)
    racks = {camera["shot"]: camera for camera in planned if camera["item"] == "rack"}
    assert list(racks) == [shot[0] for shot in closeups.SHOTS], planned  # each shot stands inside the room
    assert not any("raised" in camera["note"] for camera in racks.values()), racks  # at its own tilt, none raised
    assert all(closeups.inside_room(room, np.array(camera["eye"]), DOWN) for camera in planned)
    assert racks["left"]["eye"][0] * racks["right"]["eye"][0] < 0 and racks["above"]["eye"][1] < 0.55
    front = racks["front"]  # in front of the rack, level with it, its target mid-picture, its height FILL, upright
    eye = np.array(front["eye"])
    assert eye[2] < 3.7 and abs(eye[0]) < 1e-9 and abs(eye[1] - 0.55) < 1e-9
    pixel, depth = framed(front, [front["target"]])
    assert np.allclose(pixel[0], [front["size"] / 2] * 2) and depth[0] > 0
    centre, (wide, deep, tall) = np.array(ITEMS[0]["centre"]), ITEMS[0]["size"]
    pixel, _ = framed(front, [centre + [sx * wide / 2, sy * tall / 2, -deep / 2] for sx in (-1, 1) for sy in (-1, 1)])
    assert abs((pixel[:, 1].max() - pixel[:, 1].min()) / front["size"] - closeups.FILL) < 0.02
    target = np.array(front["target"])
    pixel, _ = framed(front, [target + [0, -0.5, 0], target + [0, 0.5, 0]])
    assert pixel[0, 1] < pixel[1, 1]
    assert "rack" in front["prompts"] and "locker" in front["prompts"] and "far" not in front["prompts"]
    left, top, right, bottom = front["boxes"]["rack"]
    assert left < front["size"] / 2 < right and top < front["size"] / 2 < bottom
    assert abs((bottom - top) / front["size"] - closeups.FILL) < 0.05
    assert front["labels"] == {"rack": "equipment rack", "locker": "tall locker"}
    for case, item, walls, note, lowest, wider, above in STANDS:
        camera = closeups.camera_or_raised(item, walls, DOWN, closeups.SHOTS[0])
        if note is None:
            assert camera is None, (case, camera)
            continue
        assert camera is not None and note in camera["note"], (case, camera)
        assert note == "raised" or "raised" not in camera["note"], (case, camera)  # found at its own tilt
        assert closeups.inside_room(walls, np.array(camera["eye"]), DOWN), case
        assert lowest is None or camera["eye"][2] > lowest, (case, camera)
        assert wider is None or camera["fov"] > closeups.FOV_DEGREES, (case, camera)
        assert above is None or camera["eye"][1] < 0.55, (case, camera)
    for masks, scores, owners in OWNERS:
        assert (closeups.resolve(masks, scores) == np.array(owners)).all(), scores
    image = np.full((50, 50, 3), 200, np.uint8)
    for mask, margin, expected in CUTS:
        rgba = closeups.cut(image, mask, margin=margin)
        assert (None if rgba is None else (rgba.shape, rgba[..., 3].sum())) == expected, margin
    for turn, tilt, expected, tolerance in EXTENTS:
        assert np.allclose(closeups.extents([2.0, 0.5, 1.0], turn, tilt), expected, rtol=0, atol=tolerance), turn

    asked = []

    def asker(question, picture):
        asked.append((question, picture.getpixel((0, 0))))
        return "  matte  sand-blasted steel, warm amber light "
    store, looks = a_design(tmp_path / "design", "garden_shed", "a" * 64, (200, 10, 10)), tmp_path / "looks"
    assert "garden_shed" not in place.places()
    for case, scene, answer, refusal in REFUSED:
        with pytest.raises(SystemExit, match=refusal):
            if answer is None:
                place.unread([scene], store, looks)
            else:
                place.style_text(scene, store, lambda *_, said=answer: said, looks)
    assert place.unread(["garden_shed"], store, looks) == ["garden_shed"]  # nothing kept for the empty look
    assert place.kept_style("garden_shed", store, looks) is None  # a dry run's words: nothing asked
    environment = place.environment_style(store)
    assert environment and environment == place.design()[1].style_now()  # no EC version kept: today's
    style = place.style_text("garden_shed", store, asker, looks)
    assert style == f"{environment.rstrip('.')}. matte sand-blasted steel, warm amber light"
    assert asked == [(place.LOOK_QUESTION, (200, 10, 10))]
    assert place.style_text("garden_shed", store, asker, looks) == style and len(asked) == 1  # kept, asked once
    assert place.kept_style("garden_shed", store, looks) == style and place.unread(["garden_shed"], store, looks) == []
    kept = json.loads((looks / "garden_shed" / f"{'a' * 64}.json").read_text())
    assert kept["concept"] == "a" * 64 and kept["model"] == place.LOOK_MODEL
    a_design(tmp_path / "design", "garden_shed", "b" * 64, (10, 10, 200))  # a new lock: its look is read again
    place.style_text("garden_shed", store, asker, looks)
    assert asked[-1][1] == (10, 10, 200) and len(asked) == 2
    for name, entry in place.places().items():  # every place keeps only its name and style
        if name == place.SHARED:  # and no shared rule sends a ship to code (owner, 2026-10-07)
            assert entry["scale"]["eye_height"] == 1.6
            assert not [rule for rule in entry["rules"] if "ship" in rule.lower() and "code" in rule.lower()]
            continue
        assert "name" in entry and "style" in entry, name
        retired = {"plan", "palette", "materials", "wear", "light", "pictures"} & set(entry)
        assert not retired, f"{name} keeps retired fields {sorted(retired)}"

    sent = []
    monkeypatch.setattr(marble, "call", lambda *arguments: sent.append(arguments))
    monkeypatch.delenv(marble.compute.TICKET, raising=False)
    world = tmp_path / "world"
    for paid_call in (lambda: marble.generate("lab", world, marble.MODEL, None),
                      lambda: marble.paint("lab", world, world / "depth.png", 5.0, "words", 7)):
        with pytest.raises(marble.compute.Refused, match="nothing rents outside a cleared run"):
            paid_call()
    assert sent == [], "the World API was called outside a cleared run"

    for case, name, path, value, lines, words in REPLANNED:
        floor = copy.deepcopy(FLOOR)
        if name:
            held = space_named(floor, name)
            for step in path[:-1]:
                held = held[step]
            held[path[-1]] = value
        faults = ship_floor.faults(floor)
        assert (faults == []) == (name is None), (case, faults)
        assert all(line in faults for line in lines), (case, faults)
        assert all(any(word in fault for fault in faults) for word in words), (case, faults)
    hull = ship_floor.hull_of(FLOOR)
    assert [row["y"] for row in hull] == sorted(row["y"] for row in hull)
    assert abs(hull[-1]["y"] - 46.0) < 0.1 and FLOOR["length"] == 46.0
    corners = ship_floor.section(FLOOR, hull[len(hull) // 2])
    assert len(corners) == 5 and max(corners)[0] == corners[2][0] == hull[len(hull) // 2]["half"]
    assert FLOOR["door"]["wide"] == 0.9 and FLOOR["door"]["tall"] == 2.0
    for size in ship_floor.rooms_measured(FLOOR):
        assert min(size["clear"]) >= 2.2 and max(size["clear"]) < 4.0 and size["narrowest"] >= 1.5, size
    assert sorted(space["place"] for space in ship_floor.spaces(FLOOR)) == \
        sorted(["cockpit", "quarters", "galley", "engineroom", "storage", "shiplock", "walkway"])
    lock, ring = space_named(FLOOR, "ship's lock"), FLOOR["hull"]["side_ring"]
    assert lock["side"] == ring["side"] and lock["y"][0] < ring["y"] < lock["y"][1]
    assert [door["leads"] for door in lock["doors"] if door["wall"] == "hull"] == ["outside, or a docked craft"]
