"""Check the review page on one world made here: two runs built into a page (a stage that was rerun shows before and
after, a check that caught something says what it caught, a stage that wrote nothing reads as not recorded), a closed
room's scene record, its inked views, a resting table, the plans an inventory names, a before stage beside the game
and a left-out record. No Blender: the renders' record is written by the test and the page built with --no-render.
The world is built once; the one test then reads what it shows against three tables: the words each part of the page
must show (or must not), the values the renders and page derive, and where each camera set must stand. Each expected
entry is worked out apart from the page code (a run's numbers, the files the test drew); "Not recorded" is a wording
check guarding the overlay's rule that a stage that wrote nothing reads as not recorded, never as a stand-in.

Breaks (each applied once, seen red, reverted), in tools/review/ (page.py unless named):
- a rerun before and after: shot_cell never pairs two runs' shots (`if False:`).
- a check says what it caught: label_rows never names an unregistered split.
- not recorded: missing drops its "Not recorded:" words.
- cameras outside looking in: renders.fixed_views stands each side view 1 m from the middle.
- a room seen from inside: renders.cutaway leaves no layer out (`hide_layers=[]`).
- every view inked: renders.record_views marks no view `ink`.
- an overlap in the resting table: resting_rows keeps the objects that passed too.
- the plans shown: dimensioned_block reads a plan that is gone as found.
- a before stage beside the game: game_beside never lays the before stage's view.
- only the places drawn: renders.places_shown lists a place each time it is named.
- owner and coordinator apart: rejected_sentence reads the owner's list under the coordinator's name.

Run: PROPS_HOME=$(mktemp -d) .venv/bin/python tools/review/test_the_review_page_shows_what_the_stages_wrote.py
"""
import json
import pathlib
import sys
import tempfile
import types

import numpy as np
from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import page  # noqa: E402
import records  # noqa: E402
import renders  # noqa: E402

PLACE = "wreck"  # a place the library and the repo's data know; the runs are the test's own


def a_run(folder, colour, registered):
    """A run folder as the route leaves it: a close-up, one labelled take, the plan and the model gate's record."""
    (folder / "closeups").mkdir(parents=True)
    Image.new("RGB", (16, 16), colour).save(folder / "closeups/hull_panel.png")
    take = folder / "parts/hull_panel-r1"
    take.mkdir(parents=True)
    (take / "hull_white_scorched.ply").write_text("")
    (take / "labels.json").write_text(json.dumps({
        "take": "hull_panel-r1", "way": "parts" if registered else "whole: its split did not register",
        "shares": {"hull_white_scorched": 1.0}, "upright_gap": 0.004,
        "registration": {"registered": registered, "clear": 0.9 if registered else 0.04, "gap_share": 0.02},
        "patchy": {"pass": True, "faults": []}}))
    (folder / "plan-route.json").write_text(json.dumps({"models": {"hull_panel": {
        "kind": "wreck_hull_panel", "route": "model", "size": [1.4, 0.65, 1.37], "budget": "furniture",
        "faces": 19000}}}))
    (folder / "checks.json").write_text(json.dumps({"hull_panel": {
        "class": "chunky", "faces": 19000, "watertight": True, "pieces": 1, "biggest_share": 1.0, "spread": 0.0,
        "thinnest": 0.001 if not registered else 0.006, "pass": registered}}))
    return folder


def built(root):
    before = a_run(root / "before", (200, 0, 0), registered=False)
    now = a_run(root / "now", (0, 0, 200), registered=True)
    out = root / "page"
    out.mkdir()
    shots = {f"hull_panel--parts--{label}": {"triangles": 10, "size": [1, 1, 1]} for label in ("before", "now")}
    (out / "renders.json").write_text(json.dumps({"shots": shots, "scene": None}))
    (out / "models").mkdir()
    for name in shots:
        Image.new("RGB", (8, 8)).save(out / f"models/{name}.png")
    options = types.SimpleNamespace(place=PLACE, run=now, before=before, out=out, concept=None, references=None,
                                    stage=None, before_stage=None, agreement=None, no_render=True)
    return page.build(options).read_text()


def cut_covers(over, entry):
    """Whether a cutaway's `hide_over` leaves a structure box out: wholly over its height, over its floor."""
    low = np.array(entry["centre"]) - np.array(entry["size"]) / 2
    high = np.array(entry["centre"]) + np.array(entry["size"]) / 2
    return bool(low[1] >= over["above"] and high[0] > over["low"][0] and low[0] < over["high"][0]
                and high[2] > over["low"][1] and low[2] < over["high"][1])


# A closed room's scene record as data/scene/<place>.json held them (that folder is retired; the renders still read
# the record's shape): a 6 x 8 m floor, a 3 m ceiling, a roof slab over it, two of the player's spots inside.
ROOM = {"inside": True, "floor": [[-3.0, -4.0], [3.0, 4.0]], "ceiling": 3.0,
        "views": [{"name": "door", "eye": [-2.5, 1.6, 3.5], "aim": [0.0, 1.2, 0.0], "game": "door.png"},
                  {"name": "desk", "eye": [2.0, 1.6, -3.0], "aim": [0.0, 1.2, 0.0]}],
        "structure": [{"builder": "box", "name": "roof", "centre": [0.0, 3.1, 0.0], "size": [6.0, 0.2, 8.0]},
                      {"builder": "box", "name": "desk", "centre": [2.0, 0.4, -3.5], "size": [1.2, 0.8, 0.6]}]}
ROOF_LAYER = 2  # a roof's draw layer (tools/review/CLAUDE.md: "a room with a roof (draw layer 2)")
STANDING = 1.6  # a person's eye height, metres


PLACE_BOX = (np.array([-9.0, 0.0, -12.0]), np.array([9.0, 7.0, 10.0]))  # a place seen from outside
REJECTED = {"owner_rejected": [{"what": "the pad", "names": ["pad"], "date": "2026-10-04", "why": "playtest"}],
            "coordinator_removed": [{"what": "the rocket on it", "names": ["rocket"], "date": "2026-10-10",
                                     "why": "it stood on the pad"}]}
RESTING = [{"object": "lamp_1", "passed": False, "result": "hung, not checked; overlaps cable_1 by 4 cm"},
           {"object": "crate_1", "passed": True, "gap": 0.001, "depth": 0.0, "result": "ok"}]


def section(text, anchor):
    """The page's section of one anchor, up to its end."""
    return text.split(f'id="{anchor}"')[1].split("</section>")[0]


def inked_views(out):
    """The scene section laid over three views of which two were also drawn inked."""
    (out / "scene/now").mkdir(parents=True)
    for name in ("a-look.png", "a-ink.png", "b-look.png", "b-ink.png", "c-look.png"):
        (out / "scene/now" / name).write_bytes(b"")
    return page.scene_section({"views": ["a", "b", "c"], "report": {"layers": [], "objects": 0, "triangles": 0,
                                                                    "materials": []}, "extent": [[0], [1]]}, out)


def plans(out):
    """The plan section for an inventory naming one plan on disk and one gone, and for one naming none."""
    (out / "dome").mkdir(parents=True)
    (out / "dome/plan.json").write_text(json.dumps({"pieces": [["GALLEY COUNTER", [1.35, 1.2], "door", "game"]],
                                                    "notes": ["The door dome."]}))
    Image.new("RGB", (8, 8)).save(out / "dome/plan.png")
    pictures = page.Pictures(out / "page")
    found = [records.dimensioned_plan(out / "dome/plan.json"), records.dimensioned_plan(out / "gone/plan.json")]
    return page.plan_section(None, {}, pictures, found), page.plan_section(None, {}, pictures, [])


def beside_the_game(out):
    """Two views laid beside the game's shot, the before stage having drawn only the first."""
    for label in ("before", "now"):
        (out / "scene" / label).mkdir(parents=True)
    Image.new("RGB", (8, 8), (90, 90, 90)).save(out / "scene/now/a-look.png")
    Image.new("RGB", (8, 8), (90, 90, 90)).save(out / "scene/now/b-look.png")
    Image.new("RGB", (8, 8), (40, 40, 40)).save(out / "scene/before/a-look.png")
    Image.new("RGB", (8, 8), (90, 90, 90)).save(out / "game.png")
    tiles, judged, _ = page.game_beside({"games": {"a": "game.png", "b": "game.png"}}, out, out, page.Pictures(out))
    return tiles, judged


def the_world():
    """Everything the page and its renders make from the test's runs and records, by name."""
    with tempfile.TemporaryDirectory() as folder:
        root = pathlib.Path(folder)
        text = built(root / "runs")
        scene_views = inked_views(root / "inked")
        plan_body, no_plan_body = plans(root / "plans")
        tiles, judged = beside_the_game(root / "beside")
    checks = text.split('id="checks"')[1]
    rows = page.resting_rows("now", RESTING)
    said = page.rejected_sentence(REJECTED)
    cut = renders.cutaway(ROOM)
    outside = renders.fixed_views(*PLACE_BOX) + renders.walk_views(*PLACE_BOX)
    walk = renders.record_walk(ROOM)
    shown = {"close-ups": section(text, "closeups"), "models": section(text, "models"), "checks": checks,
             "model gate": checks.split("Parts labelling")[0], "concept": section(text, "concept"),
             "scene": section(text, "scene"), "scene views": scene_views, "resting table": "".join(rows),
             "plans": plan_body, "no plans": no_plan_body, "tile a": tiles[0], "tile b": tiles[1],
             "left out": said, "left out by the owner": said.partition("Left out by the coordinator: ")[0]}
    values = {"a run not given": records.run(None), "places sent": renders.places_shown(
                  {"places": [{"stage": "tube"}, {"stage": "airlock"}, {"stage": "tube"}]}),
              "resting rows": len(rows), "views judged beside the game": judged,
              "cutaway's hidden layers": cut["hide_layers"], "cutaway over the ceiling": cut["eye"][1] > ROOM["ceiling"],
              "cutaway leaves the roof slab out": cut_covers(cut["hide_over"], ROOM["structure"][0]),
              "cutaway leaves the desk out": cut_covers(cut["hide_over"], ROOM["structure"][1]),
              "look-only walk frames": sum(1 for view in outside if view.get("look_only")),
              "every room view inked": all(view.get("ink") for view in renders.record_views(ROOM)),
              "room walk eye heights": {frame["eye"][1] for frame in walk}}
    cameras = {"outside the place": outside, "the room's views": renders.record_views(ROOM), "the room's walk": walk}
    return shown, values, cameras


# Where on the page, what it shows, how many times (None: at least once, 0: never), and why.
SHOWN = [
    ("close-ups", "before", None, "a close-up that changed between runs is shown before"),
    ("close-ups", "after", None, "and after"),
    ("models", "hull_panel--parts--before.png", None, "a labelled take drawn in both runs is shown before"),
    ("models", "hull_panel--parts--now.png", None, "and after"),
    ("checks", "split did not register (clear 4%), painted whole", None,
     "the earlier run's parts that did not register are named as caught"),
    ("model gate", "thinnest wall under 3 mm", 1, "the thin wall only the earlier run's model gate caught, once"),
    ("concept", "Not recorded", None, "a stage that wrote nothing says it was not recorded"),
    ("scene", "Not recorded", None, "a stage that wrote nothing says it was not recorded"),
    ("scene views", "scene/now/a-ink.png", None, "each inked view is laid beside its look"),
    ("scene views", "scene/now/b-ink.png", None, "each inked view is laid beside its look"),
    ("scene views", "c-ink.png", 0, "a view not drawn inked has no ink picture"),
    ("resting table", "overlaps cable_1 by 4 cm", None, "a hung object reads as its overlap"),
    ("resting table", "crate_1", 0, "an object that passed has no row"),
    ("resting table", '<td class="num"></td>', 2, "a hung object's gap and depth are left empty"),
    ("plans", "GALLEY COUNTER", None, "a plan's pieces are listed"),
    ("plans", "1.35 × 1.2", None, "with their sizes"),
    ("plans", "The door dome.", None, "and its notes"),
    ("plans", "img/dimensioned-1", None, "and its picture"),
    ("plans", "not on disk", None, "a plan that is gone says so"),
    ("no plans", "has no dimensioned plan", None, "a place with no plan says so plainly"),
    ("tile a", "scene/before/a-look.png", None, "the before stage's view is laid before the scene and the game"),
    ("tile a", 'class="two three"', None, "in one tile of three"),
    ("tile b", "scene/before", 0, "a view the before stage did not draw shows no before"),
    ("tile b", "three", 0, "and is a tile of two"),
    ("left out by the owner", "Left out by the owner: the pad", None, "the owner's reject reads under his name"),
    ("left out by the owner", "rocket", 0, "never with the coordinator's"),
    ("left out", "Left out by the coordinator: the rocket", None, "the coordinator's reads under its own"),
]

# What the renders and the page derive, and what it must be.
VALUES = {"a run not given": None, "places sent": ["tube", "airlock"], "resting rows": 1,
          "views judged beside the game": 2, "cutaway's hidden layers": [ROOF_LAYER], "cutaway over the ceiling": True,
          "cutaway leaves the roof slab out": True, "cutaway leaves the desk out": False,
          "look-only walk frames": renders.WALK_FRAMES, "every room view inked": True,
          "room walk eye heights": {STANDING}}

# Where each camera set stands on the ground (x, z): inside or outside a box, with a margin, and whether it looks at
# the box's middle.
ROOM_FLOOR = (np.array(ROOM["floor"][0]), np.array(ROOM["floor"][1]))
PLACE_FLOOR = (PLACE_BOX[0][[0, 2]], PLACE_BOX[1][[0, 2]])
CAMERAS = [("outside the place", PLACE_FLOOR, 0.0, "outside", True),
           ("the room's views", ROOM_FLOOR, 0.5, "inside", False),
           ("the room's walk", ROOM_FLOOR, 0.0, "inside", False)]


def test_the_review_page_shows_what_the_stages_wrote():
    shown, values, cameras = the_world()
    problems = []
    for where, words, times, why in SHOWN:
        found = shown[where].count(words)
        if (found == 0) if times is None else (found != times):
            problems.append(f"{where}: {words!r} found {found} times; wanted {why}")
    for name, wanted in VALUES.items():
        if values[name] != wanted:
            problems.append(f"{name}: {values[name]!r}, wanted {wanted!r}")
    for name, (low, high), margin, stands, looks_at_middle in CAMERAS:
        for view in cameras[name]:
            eye = np.array(view["eye"])[[0, 2]]
            inside = bool(np.all(eye >= low - margin) and np.all(eye <= high + margin))
            if inside != (stands == "inside"):
                problems.append(f"{name}: {view['name']} does not stand {stands}")
            if looks_at_middle and np.linalg.norm(np.array(view["aim"])[[0, 2]] - (low + high) / 2) > 1e-6:
                problems.append(f"{name}: {view['name']} does not look at the middle")
    assert problems == []


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(HERE.parents[1] / "conftest.py"))["refuse_outside_sandbox"]()
    test_the_review_page_shows_what_the_stages_wrote()
    print("ok")
