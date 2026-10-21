"""Plan writing (score/review/plan_writing.py) and its free checks (plan_checks.py) on stand-in data, with a stand-in
for Gemini (no call is made, nothing is spent): the answer made into a plan of the stage table's schema with its
architecture and shapes, each check's failure a named gap, his edit checked again; under the standing allowance it
runs on its own, with the flag off only inside his yes."""
import json
import subprocess

import pytest

from score.adapters import compute
from score.review import plan_checks, plan_writing, plans, web
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


@pytest.fixture
def gemini(monkeypatch):
    asked = []
    monkeypatch.setattr(plan_writing, "call_euros", lambda found: 0.04)
    monkeypatch.setattr(compute, "books_refusal", lambda: None)

    def ask(body):
        asked.append(body)
        return response(ANSWER), 1.0
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
    record, = plan_writing.write(store, ["shed"], "the allowance", clear=cleared(clears), ask=ask)
    assert clears == [(compute.PLAN_WRITING, ["shed"], 0.05)] and record["euros"] == 0.04
    told = asked[0]["contents"][0]["parts"][0]["text"]
    assert '"fixed doors"' in told and '"leads to": "yard"' in told and '"metres [wide, deep, tall]"' in told
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
    assert web.plan_write(store, "shed", 0.05, "joey", run=run)["place"] == "shed"
    yes, = [store.read(key) for key in store.objects.keys("spend-yes/") if "plan-write-shed" in key]
    assert yes["euros"] == 0.05 and yes["by"] == "joey"
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
