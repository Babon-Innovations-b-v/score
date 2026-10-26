"""Check the review page on two runs made here: a stage that was rerun shows before and after, a check that caught
something says what it caught, a stage that wrote nothing reads as not recorded, and the scene's cameras all stand
outside the place looking at it. No Blender: the renders' record is written by the test and the page built with
--no-render. The page is the module's one output, so its cases read the built page for what it must show, each worked
out apart from the page code (a run's numbers, the files the test drew); "Not recorded" is a wording check guarding
the overlay's rule that a stage that wrote nothing reads as not recorded, never as a stand-in. Each case is a check
returning its problems; the test_ wrappers at the end fail on any.

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


def a_rerun_shows_before_and_after():
    with tempfile.TemporaryDirectory() as folder:
        text = built(pathlib.Path(folder))
    closeups = text.split('id="closeups"')[1].split("</section>")[0]
    models = text.split('id="models"')[1].split("</section>")[0]
    problems = []
    if "before" not in closeups or "after" not in closeups:
        problems.append("a close-up that changed between runs is not shown before and after")
    if "hull_panel--parts--before.png" not in models or "hull_panel--parts--now.png" not in models:
        problems.append("a labelled take drawn in both runs is not shown before and after")
    return problems


def a_check_says_what_it_caught():
    with tempfile.TemporaryDirectory() as folder:
        text = built(pathlib.Path(folder))
    checks = text.split('id="checks"')[1]
    problems = []
    if "split did not register (clear 4%), painted whole" not in checks:
        problems.append("the earlier run's parts that did not register are not named as caught")
    gate = checks.split("Parts labelling")[0]
    if gate.count("thinnest wall under 3 mm") != 1:
        problems.append("the thin wall only the earlier run's model gate caught is not named exactly once")
    return problems


def a_stage_that_wrote_nothing_is_not_recorded():
    with tempfile.TemporaryDirectory() as folder:
        text = built(pathlib.Path(folder))
    problems = []
    for anchor in ("concept", "scene"):
        if "Not recorded" not in text.split(f'id="{anchor}"')[1].split("</section>")[0]:
            problems.append(f"the {anchor} section does not say it was not recorded")
    if records.run(None) is not None:
        problems.append("a run that was not given reads as a run")
    return problems


def the_cameras_stand_outside_looking_in():
    low, high = np.array([-9.0, 0.0, -12.0]), np.array([9.0, 7.0, 10.0])
    middle = (low + high) / 2
    problems = []
    views = renders.fixed_views(low, high) + renders.walk_views(low, high)
    for view in views:
        eye, aim = np.array(view["eye"]), np.array(view["aim"])
        if low[0] <= eye[0] <= high[0] and low[2] <= eye[2] <= high[2]:
            problems.append(f"{view['name']} stands inside the place")
        if np.linalg.norm((aim - middle)[[0, 2]]) > 1e-6:
            problems.append(f"{view['name']} does not look at the place's middle")
    if sum(1 for view in views if view.get("look_only")) != renders.WALK_FRAMES:
        problems.append("the walk's frames are not all look-only")
    return problems


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


def a_room_is_seen_from_inside():
    """A room's scene record puts its cameras inside its floor (never outside a closed room), its walk at standing
    height inside it, and its cutaway over it with the roof left out."""
    record, problems = ROOM, []
    low, high = np.array(record["floor"][0]), np.array(record["floor"][1])
    for view in renders.record_views(record):
        eye = np.array(view["eye"])[[0, 2]]
        if not (np.all(eye >= low - 0.5) and np.all(eye <= high + 0.5)):
            problems.append(f"{view['name']} stands outside the room")
    cut = renders.cutaway(record)
    if cut["hide_layers"] != [ROOF_LAYER] or cut["eye"][1] <= record["ceiling"]:
        problems.append("the cutaway is not over the room with its roof left out")
    if not cut_covers(cut["hide_over"], record["structure"][0]):
        problems.append("the cutaway does not leave the roof slab out")
    if cut_covers(cut["hide_over"], record["structure"][1]):
        problems.append("the cutaway leaves out the desk under the ceiling")
    walk = renders.record_walk(record)
    if not walk or any(frame["eye"][1] != STANDING for frame in walk):
        problems.append("the walk is not at standing height")
    for frame in walk:
        eye = np.array(frame["eye"])[[0, 2]]
        if not (np.all(eye >= low) and np.all(eye <= high)):
            problems.append(f"the walk's {frame['name']} leaves the room")
    return problems


def every_view_a_place_is_inked():
    """Every one of a place's own cameras is also drawn with the game's ink lines, as the game draws them over every
    frame, and the page lays each inked view beside its look (and none it was not given)."""
    problems = []
    if not all(view.get("ink") for view in renders.record_views(ROOM)):
        problems.append("not every view is inked")
    with tempfile.TemporaryDirectory() as folder:
        out = pathlib.Path(folder)
        (out / "scene/now").mkdir(parents=True)
        for name in ("a-look.png", "a-ink.png", "b-look.png", "b-ink.png", "c-look.png"):
            (out / "scene/now" / name).write_bytes(b"")
        body = page.scene_section({"views": ["a", "b", "c"], "report": {"layers": [], "objects": 0, "triangles": 0,
                                                                        "materials": []}, "extent": [[0], [1]]}, out)
        if "scene/now/a-ink.png" not in body or "scene/now/b-ink.png" not in body or "c-ink.png" in body:
            problems.append("the page does not lay each inked view beside its look")
    return problems


def an_overlap_reads_in_the_resting_table():
    """An object caught only for lying inside another (a hung one: no gap, no depth) reads as its overlap, its gap
    and depth cells empty; an object that passed has no row."""
    rows = page.resting_rows("now", [{"object": "lamp_1", "passed": False, "result": "hung, not checked; overlaps "
                                      "cable_1 by 4 cm"},
                                     {"object": "crate_1", "passed": True, "gap": 0.001, "depth": 0.0, "result": "ok"}])
    if len(rows) != 1 or "overlaps cable_1 by 4 cm" not in rows[0] or "crate_1" in rows[0]:
        return ["only the hung object's overlap should read in the resting table"]
    if rows[0].count('<td class="num"></td>') != 2:
        return ["a hung object's gap and depth are not left empty"]
    return []


def the_plans_an_inventory_names_are_shown():
    """Each dimensioned plan an inventory names is shown with its picture and lists; a place with none says so."""
    problems = []
    with tempfile.TemporaryDirectory() as folder:
        out = pathlib.Path(folder)
        (out / "dome").mkdir()
        (out / "dome/plan.json").write_text(json.dumps({"pieces": [["GALLEY COUNTER", [1.35, 1.2], "door", "game"]],
                                                        "notes": ["The door dome."]}))
        Image.new("RGB", (8, 8)).save(out / "dome/plan.png")
        pictures = page.Pictures(out / "page")
        found = [records.dimensioned_plan(out / "dome/plan.json"), records.dimensioned_plan(out / "gone/plan.json")]
        body = page.plan_section(None, {}, pictures, found)
        for wanted in ("GALLEY COUNTER", "1.35 × 1.2", "The door dome.", "img/dimensioned-1", "not on disk"):
            if wanted not in body:
                problems.append(f"the plan section does not show {wanted!r}")
        if "has no dimensioned plan" not in page.plan_section(None, {}, pictures, []):
            problems.append("a place with no plan does not say so plainly")
    return problems


def a_before_stage_stands_beside_the_game():
    """A view the before stage drew too shows before, scene and game in one tile; one it did not shows scene and game."""
    with tempfile.TemporaryDirectory() as folder:
        out = pathlib.Path(folder)
        for label in ("before", "now"):
            (out / "scene" / label).mkdir(parents=True)
        Image.new("RGB", (8, 8), (90, 90, 90)).save(out / "scene/now/a-look.png")
        Image.new("RGB", (8, 8), (90, 90, 90)).save(out / "scene/now/b-look.png")
        Image.new("RGB", (8, 8), (40, 40, 40)).save(out / "scene/before/a-look.png")
        Image.new("RGB", (8, 8), (90, 90, 90)).save(out / "game.png")
        tiles, judged, _ = page.game_beside({"games": {"a": "game.png", "b": "game.png"}}, out, out,
                                            page.Pictures(out))
    problems = []
    if judged != 2 or "scene/before/a-look.png" not in tiles[0] or 'class="two three"' not in tiles[0]:
        problems.append("the before stage's view is not laid before the scene and the game's shot")
    if "scene/before" in tiles[1] or "three" in tiles[1]:
        problems.append("a view the before stage did not draw shows a before")
    return problems


def only_the_places_drawn_are_sent():
    """A stage is sent with the places it shows, never with the ones those show, which it turns off."""
    record = {"places": [{"stage": "tube"}, {"stage": "airlock"}, {"stage": "tube"}]}
    if renders.places_shown(record) != ["tube", "airlock"]:
        return [f"the places sent are {renders.places_shown(record)}, not the tube and the airlock alone"]
    return []


def the_owner_and_the_coordinator_are_told_apart():
    """What the owner rejected and what the coordinator took out with it read as two sentences, each under its name."""
    record = {"owner_rejected": [{"what": "the pad", "names": ["pad"], "date": "2026-10-04", "why": "playtest"}],
              "coordinator_removed": [{"what": "the rocket on it", "names": ["rocket"], "date": "2026-10-10",
                                       "why": "it stood on the pad"}]}
    said = page.rejected_sentence(record)
    owner, _, coordinator = said.partition("Left out by the coordinator: ")
    if "Left out by the owner: the pad" not in owner or "rocket" in owner or not coordinator.startswith("the rocket"):
        return [f"the left-out sentences read {said!r}"]
    return []


def test_a_rerun_shows_before_and_after():
    assert a_rerun_shows_before_and_after() == []


def test_a_check_says_what_it_caught():
    assert a_check_says_what_it_caught() == []


def test_a_stage_that_wrote_nothing_is_not_recorded():
    assert a_stage_that_wrote_nothing_is_not_recorded() == []


def test_the_cameras_stand_outside_looking_in():
    assert the_cameras_stand_outside_looking_in() == []


def test_a_room_is_seen_from_inside():
    assert a_room_is_seen_from_inside() == []


def test_every_view_a_place_is_inked():
    assert every_view_a_place_is_inked() == []


def test_an_overlap_reads_in_the_resting_table():
    assert an_overlap_reads_in_the_resting_table() == []


def test_the_plans_an_inventory_names_are_shown():
    assert the_plans_an_inventory_names_are_shown() == []


def test_a_before_stage_stands_beside_the_game():
    assert a_before_stage_stands_beside_the_game() == []


def test_only_the_places_drawn_are_sent():
    assert only_the_places_drawn_are_sent() == []


def test_the_owner_and_the_coordinator_are_told_apart():
    assert the_owner_and_the_coordinator_are_told_apart() == []


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(HERE.parents[1] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
