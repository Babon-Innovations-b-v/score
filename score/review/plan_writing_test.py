"""Plan writing (score/review/plan_writing.py) and its free checks (plan_checks.py) on stand-in data, with stand-ins
for Gemini and the top-down drawing (no call is made, nothing is spent): the answer, in units of the drawing, measured
by the rows' metres into a plan of the stage table's schema with its architecture and shapes, each check's failure a
named gap, his edit checked again; under the standing allowance it runs on its own, with the flag off only inside his
yes."""
import io
import json
import subprocess

import pytest
from PIL import Image

from score.adapters import compute
from score.review import plan_checks, plan_drawing, plan_writing, plans, web
from score.review.plans_test import data, picked, store  # noqa: F401 (the fixtures)

ANSWER = {
    "outline": [[0, 0], [4, 0], [4, 3], [0, 3]],
    "walls": [{"from": [0, 0], "to": [4, 0], "thick": 0.2, "tall": 2.5}, {"from": [4, 0], "to": [4, 3], "thick": 0.2},
              {"from": [4, 3], "to": [0, 3], "thick": 0.2}, {"from": [0, 3], "to": [0, 0], "thick": 0.2},
              {"from": "nowhere"}],
    "openings": [{"kind": "door", "at": [2.0, 3.0], "wide": 0.9, "angle": 0, "swing": "left", "head": 2.1,
                  "to": "yard"}],
    "levels": [{"name": "floor", "height": 0, "points": [[0, 0], [4, 0], [4, 3], [0, 3]]}],
    "roofs": [{"kind": "pitched", "points": [[0, 0], [4, 0], [4, 3], [0, 3]], "eave": 2.5, "top": 3.4}],
    "terrain": {},
    "structure": ["lamp_nowhere"],
    "items": [{"row": "bench", "x": 2.0, "y": 0.6, "wide": 2.0, "deep": 0.6, "shape": "rect", "facing": "S",
               "tall": 0.9, "base": 0},
              {"row": "crate", "x": 2.2, "y": 0.7, "wide": 0.5, "deep": 0.5, "shape": "circle", "tall": 0.5},
              {"row": "lamp", "x": 0.2, "y": 1.5, "wide": 0.3, "deep": 0.2, "tall": 0.3, "base": 2.0},
              {"row": "ghost", "x": 1, "y": 1, "wide": 1, "deep": 1}],
    "people": [[1.0, 2.0]],
    "section": {"y": 1.5},
}


def response(answer):
    return {"candidates": [{"content": {"parts": [{"text": json.dumps(answer)}]}}], "usageMetadata": {}}


UNITS = 100  # drawing units a metre in the stand-in answer: the rows' metres measure it back


@pytest.fixture
def gemini(monkeypatch):
    asked, drawn = [], []
    monkeypatch.setattr(plan_writing, "call_euros", lambda found: 0.04)
    monkeypatch.setattr(compute, "books_refusal", lambda: None)

    def drawing(wording, pictures, frame):
        drawn.append(wording)
        buffer = io.BytesIO()
        Image.new("RGB", (500, 400), (255, 255, 255)).save(buffer, "PNG")
        return buffer.getvalue(), 0.12, 1.0
    monkeypatch.setattr(plan_drawing, "called", drawing)

    def ask(body):
        asked.append(body)
        return response(plan_writing.metred(ANSWER, (UNITS, UNITS), (0, 0))), 1.0
    ask.drawn = drawn
    return asked, ask


def cleared(cleared_for):
    def clear(store, places, euros, node):
        cleared_for.append((node, places, euros))
        return compute.reading_clearance(store, places, euros, node=node)
    return clear


def test_the_answer_is_a_plan_of_the_stage_tables_schema_and_each_failed_check_a_named_gap(store, gemini):
    asked, ask = gemini
    picked(store, "shed")
    assert plans.current(store, "shed")["how"] == "derived"
    clears = []
    price = plan_writing.price(store)
    record, = plan_writing.write(store, ["shed"], "the allowance", clear=cleared(clears), ask=ask)
    assert clears == [(compute.PLAN_WRITING, ["shed"], price)] and record["euros"] == 0.04
    assert record["drawing_euros"] == 0.12 and record["measured"] == {"metres a unit": [0.01, 0.01],
                                                                      "by": "its rows' metres"}
    assert "a bench, 2 a crate" in ask.drawn[0] and len(asked[0]["contents"][0]["parts"]) == 3
    assert plan_writing.spent(store, ["shed"]) == 0.16 and plan_writing.price(store) == 0.16
    told = asked[0]["contents"][0]["parts"][0]["text"]
    assert '"leads to": "yard"' in told
    plan = plans.current(store, "shed")["plan"]
    assert plans.current(store, "shed")["how"] == "written"
    items = {item[0]: item for item in plan["items"]}
    assert items["BENCH 1"] == ["BENCH 1", 1.0, 0.3, 2.0, 0.6, "S", "item"]
    assert plan["rows"]["BENCH 1"] == ["bench", "vice"]  # the vice rides on it, placed by no item of its own
    assert plan["shapes"]["CRATE 1"]["shape"] == "circle" and plan["shapes"]["LAMP 1"]["base"] == 2.0
    assert plan["doors"] == [["S", 2.0, 0.9, "DOOR to the yard"]] and plan["leads"]["S"]["to"] == "yard"
    assert len(plan["walls"]) == 4 and plan["roofs"][0]["top"] == 3.4 and plan["section"] == {"y": 1.5}
    words = [gap["words"] for gap in plan["gaps"]]
    assert {"item": "ghost", "why": "no such row"} in plan["dropped"] and {"item": "walls", "why": "1 off the schema"} \
        in plan["dropped"]  # kept apart: no gap of his
    assert words == ["crate: 2 in the concept, 1 on the plan", "bench 1 and crate 1 stand in each other (north)"]
    assert not [word for word in words if "reached" in word or "outside" in word]
    assert plan_writing.write(store, ["shed"], "the allowance", clear=cleared(clears), ask=ask) == []  # written once
    plan["items"] = [[*item[:2], 0.3, *item[3:]] if item[0] == "CRATE 1" else item for item in plan["items"]]
    plan["items"].append(["CRATE 2", 3.2, 2.0, 0.5, 0.5, None, "item"])
    plan["rows"]["CRATE 2"] = ["crate"]
    plans.edited(store, "shed", plan, "joey")
    words = [gap["words"] for gap in plans.current(store, "shed")["plan"]["gaps"]]
    assert "bench 1 and crate 1 stand in each other (north)" in words and "crate: 2 in the concept, 1 on the plan" not in words  # his second crate counts
    plan["items"] = [[*item[:2], 2.0, *item[3:]] if item[0] == "CRATE 1" else item for item in plan["items"]]
    plan["items"] = [item for item in plan["items"] if item[0] != "CRATE 2"]
    plans.edited(store, "shed", plan, "joey")
    words = [gap["words"] for gap in plans.current(store, "shed")["plan"]["gaps"]]
    assert "bench 1 and crate 1 stand in each other (north)" not in words  # his move, checked again


def test_a_door_walled_in_or_an_inside_place_overlapping_another_is_a_gap():
    plan = {"w": 6.0, "d": 4.0, "doors": [["S", 3.0, 1.0, "DOOR"]], "people": [[1.0, 1.0]],
            "items": [["WALL OF CRATES 1", 0.0, 2.0, 6.0, 0.6, None, "item"]], "rows": {"WALL OF CRATES 1": ["crate"]},
            "holds": [{"place": "a", "x": 0, "y": 0, "w": 3, "d": 2}, {"place": "b", "x": 2, "y": 0, "w": 3, "d": 2},
                      {"place": "c", "x": 5, "y": 3, "w": 3, "d": 3}]}
    inventory = {"rows": [{"id": "crate", "anchor": "floor", "count": 1}]}
    words = [gap["words"] for gap in plan_checks.checked(plan, inventory)]
    assert any(word.startswith("the standing spot (north-west)") and "reached" in word for word in words) or \
        any(word.startswith("the door on the south wall") and "reached" in word for word in words)
    assert "a and b overlap" in words and "c sticks out of the place" in words
    plan["shapes"] = {"WALL OF CRATES 1": {"shape": "rect", "tall": 0.05}}  # a cable on the floor: walked over
    assert not [word for word in plan_checks.checked(plan, inventory) if "reached" in word]
    plan["shapes"] = {}
    plan["items"][0][3] = 4.0  # a way round the crates: every door and spot reached
    assert not [word for word in plan_checks.checked(plan, inventory) if "reached" in word]


def test_a_footprint_answered_as_box_2d_is_measured_from_its_box():
    answer = {"outline": [[0, 0], [1000, 0], [1000, 1000], [0, 1000]],
              "items": [{"row": "bench", "box_2d": [100, 200, 160, 400]}],
              "places": [{"place": "nook", "box_2d": [500, 500, 700, 800]}]}
    inventory = {"rows": [{"id": "bench", "size": [2.0, 0.6, 0.9]}]}
    found, skeleton, how = plan_writing.measured(answer, {"w": 1.0, "d": 1.0}, inventory, held=False)
    assert how == {"metres a unit": [0.01, 0.01], "by": "its rows' metres"} and (skeleton["w"], skeleton["d"]) == (10, 10)
    assert {key: found["items"][0][key] for key in ("x", "y", "wide", "deep")} == {"x": 3.0, "y": 1.3, "wide": 2.0,
                                                                                    "deep": 0.6}
    assert {key: found["places"][0][key] for key in ("x", "y", "w", "d")} == {"x": 5.0, "y": 5.0, "w": 3.0, "d": 2.0}


def test_an_arrangement_not_the_concepts_and_a_tube_joining_nothing_are_gaps():
    # the concept: a hub in the middle, a dome left of it, a hangar behind it, a tube from the hub to the dome
    inventory = {"picture": [1000, 1000], "rows": [
        {"id": "hub", "count": 1, "boxes": [[400, 400, 600, 600]]},
        {"id": "dome", "count": 1, "boxes": [[100, 420, 250, 580]]},
        {"id": "hangar", "count": 1, "boxes": [[350, 50, 650, 200]]},
        {"id": "tube", "count": 1, "boxes": [[250, 480, 400, 520]]}]}
    rows = {"HUB 1": ["hub"], "DOME 1": ["dome"], "HANGAR 1": ["hangar"], "TUBE 1": ["tube"]}
    laid = [["HUB 1", 20.0, 20.0, 10.0, 10.0, None, "item"], ["DOME 1", 2.0, 21.0, 8.0, 8.0, None, "item"],
            ["HANGAR 1", 15.0, 0.0, 20.0, 10.0, None, "item"], ["TUBE 1", 10.0, 24.0, 10.0, 2.0, None, "item"]]
    plan = {"w": 40.0, "d": 40.0, "doors": [], "people": [[30.0, 35.0]], "items": laid, "rows": rows}
    gaps = [gap for gap in plan_checks.checked(plan, inventory) if gap["kind"] in ("arrangement", "joined")]
    assert gaps == []  # as the concept, seen from the south
    packed = [["HUB 1", 20.0, 20.0, 10.0, 10.0, None, "item"], ["DOME 1", 31.0, 21.0, 8.0, 8.0, None, "item"],
              ["HANGAR 1", 15.0, 0.0, 20.0, 10.0, None, "item"], ["TUBE 1", 2.0, 34.0, 10.0, 2.0, None, "item"]]
    words = [gap["words"] for gap in plan_checks.checked({**plan, "items": packed}, inventory)
             if gap["kind"] in ("arrangement", "joined")]
    assert "dome is left of hub in the concept, right of it on the plan" in words
    assert "hub is joined by a tube in the concept, by none on the plan" in words


def test_a_row_off_to_the_side_or_facing_the_wrong_way_is_a_gap_and_a_run_of_crates_counts_whole():
    # the concept: a pad in the middle, a desk on the left, a rack on the right, all at about one depth
    inventory = {"picture": [1000, 1000], "rows": [
        {"id": "pad", "count": 1, "boxes": [[400, 600, 600, 700]]},
        {"id": "desk", "count": 1, "boxes": [[50, 600, 150, 700]]},
        {"id": "rack", "count": 1, "boxes": [[850, 600, 950, 700]]},
        {"id": "crate", "count": 6, "boxes": [[0, 0, 10, 10]]}]}
    rows = {"PAD 1": ["pad"], "DESK 1": ["desk"], "RACK 1": ["rack"], "CRATE 1": ["crate"]}
    laid = [["PAD 1", 14.0, 10.0, 4.0, 4.0, None, "item"], ["DESK 1", 1.0, 10.0, 2.0, 1.0, "S", "item"],
            ["RACK 1", 28.0, 10.0, 2.0, 1.0, None, "item"], ["CRATE 1", 1.0, 1.0, 4.0, 1.0, None, "item"]]
    plan = {"w": 32.0, "d": 20.0, "doors": [], "people": [[16.0, 18.0]], "items": laid, "rows": rows,
            "shapes": {"CRATE 1": {"count": 6}, "DESK 1": {"seen": ["toward"]}}}
    assert [gap["words"] for gap in plan_checks.checked(plan, inventory)] == []  # a run of 6 crates is all 6
    off = [["PAD 1", 22.0, 10.0, 4.0, 4.0, None, "item"], ["DESK 1", 1.0, 10.0, 2.0, 1.0, "N", "item"], *laid[2:]]
    words = [gap["words"] for gap in plan_checks.checked({**plan, "items": off}, inventory)]
    assert "pad stands in the middle of the concept (50% across), on the right of the plan (81% across)" in words
    assert "desk 1 faces toward in the concept, away on the plan" in words


def test_a_thing_the_creator_planned_is_laid_from_his_plan_where_and_the_way_it_is_drawn(monkeypatch):
    from score.review import creator_plans
    ship = {"what": "the ship's floor plan", "places": ["bridge", "hold"], "length": 10.0, "wide": 4.0, "base": 1.0,
            "tall": 3.0, "outline": [[0, 0], [2, 4], [2, 10], [-2, 10], [-2, 4]],
            "rooms": {"bridge": [[-1, 2], [1, 2], [1, 5], [-1, 5]], "hold": [[-2, 5], [2, 5], [2, 10], [-2, 10]]}}
    monkeypatch.setattr(creator_plans, "PLANS", (lambda: ship,))
    holds = [{"place": "bridge", "row": "ship", "x": 0, "y": 0, "w": 1, "d": 1},
             {"place": "hold", "row": "ship", "x": 1, "y": 0, "w": 1, "d": 1}]
    plan = {"items": [["SHIP 1", 18.0, 9.0, 4.0, 2.0, "E", "item"]], "rows": {"SHIP 1": ["ship"]}, "shapes": {},
            "holds": holds}
    laid, gaps = plan_writing.creator_laid(plan)
    assert laid == {"bridge", "hold"} and gaps == []
    assert plan["items"][0] == ["SHIP 1", 15.0, 8.0, 10.0, 4.0, "E", "item"]  # its own 10 x 4 m, nose east, same middle
    assert {hold["place"]: [hold["x"], hold["y"], hold["w"], hold["d"]] for hold in plan["holds"]} == {
        "bridge": [20.0, 9.0, 3.0, 2.0], "hold": [15.0, 8.0, 5.0, 4.0]}
    assert plan["shapes"]["SHIP 1"]["points"][0] == [1.0, 0.5] and plan["shapes"]["SHIP 1"]["base"] == 1.0
    plan["items"][0][5] = None
    assert plan_writing.creator_laid(plan)[1][0]["words"] == "the way ship 1's nose points was not read: laid nose E"


def test_people_things_seen_far_off_and_rows_beyond_the_place_are_no_gaps():
    plan = {"w": 6.0, "d": 4.0, "doors": [], "people": [],
            "items": [["CRATE 1", 1.0, 1.0, 1.0, 1.0, None, "item"], ["DINER 1", 1.2, 1.2, 0.5, 0.5, None, "item"],
                      ["DISTANT FLAG 1", 9.0, 1.0, 1.0, 1.0, None, "item"]],
            "rows": {"CRATE 1": ["crate"], "DINER 1": ["diner"], "DISTANT FLAG 1": ["distant_flag"]}}
    inventory = {"rows": [{"id": "crate", "count": 1}, {"id": "diner", "noun": "person", "count": 1},
                          {"id": "distant_flag", "count": 1}, {"id": "stage", "count": 1}]}
    assert [gap["words"] for gap in plan_checks.checked(plan, inventory)] == ["stage: 1 in the concept, 0 on the plan"]
    assert plan_checks.checked({**plan, "beyond": ["stage"]}, inventory) == []


def test_with_the_flag_off_a_writing_runs_only_inside_his_yes(store, gemini, monkeypatch):
    _, ask = gemini
    picked(store, "shed")
    monkeypatch.setattr(plan_writing, "AUTOMATIC", False)
    with pytest.raises(compute.Refused):
        plan_writing.write(store, ["shed"], "joey", ask=ask)

    def run(argv, env, **named):
        monkeypatch.setenv("SCORE_SPEND_TICKET", env["SCORE_SPEND_TICKET"])
        record, = plan_writing.write(store, [argv[-3]], argv[-1], ask=ask)
        return subprocess.CompletedProcess(argv, 0, plan_writing.said(record) + "\n", "")

    with pytest.raises(web.review.Refused, match="not today's price"):
        web.plan_write(store, "shed", 0.09, "joey", run=run)
    price = plan_writing.price(store)  # the writing and its top-down drawing
    assert web.plan_write(store, "shed", price, "joey", run=run)["place"] == "shed"
    yes, = [store.read(key) for key in store.objects.keys("spend-yes/") if "plan-write-shed" in key]
    assert yes["euros"] == price and yes["by"] == "joey"
    assert plans.current(store, "shed")["how"] == "written"


def test_with_the_flag_on_his_click_asks_no_yes_and_a_reading_writes_its_plan(store, gemini, monkeypatch):
    from score.review import reading
    _, ask = gemini
    picked(store, "shed")
    ran = []

    def run(argv, env, **named):
        ran.append(env)
        return subprocess.CompletedProcess(argv, 0, "", "")

    assert web.plan_write(store, "shed", 0.0, "joey", run=run) == {"place": "shed", "written": "already"}
    assert "SCORE_SPEND_TICKET" not in ran[0] or ran[0]["SCORE_SPEND_TICKET"] == ""
    monkeypatch.setattr(plan_writing, "asked", ask)
    assert reading.planned(store, ["shed"], "the allowance") == 0
    assert plans.current(store, "shed")["how"] == "written"
    monkeypatch.setattr(plan_writing, "AUTOMATIC", False)
    assert reading.planned(store, ["yard"], "the allowance") == 0 and plan_writing.writings(store, "yard") == []


def test_a_read_place_with_no_plan_is_owed_unless_refused_and_an_older_methods_call_sets_no_price(store, gemini):
    picked(store, "shed")
    assert plan_writing.owed(store, ["shed", "yard"]) == ["shed"]
    record = {"place": "shed", "concept": plans.pick_of(store, "shed"), "method": plan_writing.METHOD,
              "reading": plan_writing.reading_at(store, "shed"), "at": "2026-10-21T00:00:00+00:00", "euros": 0.2,
              "refused": "no plan"}
    plan_writing.kept(store, record)
    assert plan_writing.to_write(store, ["shed"]) == ["shed"] and plan_writing.owed(store, ["shed"]) == []
    price = plan_writing.price(store)
    plan_writing.kept(store, {**record, "method": 1, "at": "2026-10-21T00:00:01+00:00", "euros": 0.9})
    assert plan_writing.price(store) == price  # an older method's dearer call is no price of today's
    started = []
    assert plan_writing.started(store, ["shed"], start=lambda argv, **named: started.append(argv)).endswith(".log")
    assert started[0][-2:] == ["score.review.plan_writing", "shed"]


def test_a_scene_added_in_the_app_takes_its_doors_from_its_holders_openings_into_it():
    """A place with no doors of its own (plans.base_plan's bare plan) standing in a holder's box gets a door for each
    holder opening in its walls: one into it leads back to the holder, one in a shared outer wall where that opening
    leads; the plan stage reads the door's height off its words. A place with doors of its own keeps them."""
    from score.stages.scene_record.plan import doors_of
    skeleton = {**plans.base_plan("no_such_place"), "w": 3.0, "d": 2.0}
    openings = [{"kind": "door", "at": [11.5, 7.0], "wide": 0.9, "sill": 0.0, "head": 2.1, "to": "airlock"},
                {"kind": "gate", "at": [13.05, 5.6], "wide": 1.2, "sill": 0.0, "head": 2.4, "to": "outside"},
                {"kind": "door", "at": [0.0, 1.0], "wide": 0.9, "sill": 0.0, "head": 2.1, "to": "sealed"}]
    found = plan_writing.held_doors(skeleton, "airlock", "hangar", [10.0, 5.0, 3.0, 2.0], openings)
    assert found["doors"] == [["S", 1.5, 0.9, "door 0.9 x 2.1 m"], ["E", 0.6, 1.2, "gate 1.2 x 2.4 m"]], found
    assert {key: lead["to"] for key, lead in found["leads"].items()} == {"S": "hangar", "E": "outside"}
    made = doors_of(found, {"rows": []})
    assert [(door["side"], door["leads"], door["tall"], door["cut"]) for door in made] == [
        ("south", "hangar", 2.1, True), ("east", "outside", 2.4, True)], made
    own = {**skeleton, "doors": [["N", 1.0, 0.9, "DOOR"]], "leads": {"N": {"to": "sealed", "why": "filed"}}}
    assert plan_writing.held_doors(own, "airlock", "hangar", [10.0, 5.0, 3.0, 2.0], openings) is own
