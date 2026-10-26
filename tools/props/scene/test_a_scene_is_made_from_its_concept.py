"""The scene's invariant: a scene is made from its locked concept and nothing typed. Its inventory's rows stand on
boxes measured on the concept (never typed, never the whole picture, spread over it), an unmeasured box blocks the
close-ups; each close-up camera stands inside the world and frames its item; a cut-out too small never feeds the
redraw; one real-world object is made once; a scene's style is its design's alone; a lamp's light comes from the
library by its mount, never a typed number; no paid Marble call runs outside a cleared run; the ship's floor plan fits
its hull with rooms a person fits.

Every answer below is worked out by hand from a small fixture (a box room 8 m wide, boxes on a 2752 x 1536 concept,
a lamp at 3 m) or read from the owner's rules, never computed by the code under test.

Breaks that turn these red (each applied once, seen red, reverted, 2026-10-26):
- box_check `spread_problems`: `if False:` for the one-quarter check ->
  test_boxes_spread_over_their_picture_pass_and_typed_ones_crowded_in_a_corner_fail.
- box_check `box_problems`: `if False:` for the whole-picture check ->
  test_a_box_outside_its_picture_or_over_the_whole_of_it_fails.
- box_check `judge_rows`: drop `if not is_whole(...)` -> test_the_judge_sees_the_whole_picture_and_the_crop_once_a_seed.
- box_check `verdict`: `len(failing) < len(replies)` ->
  test_the_judges_majority_decides_and_a_third_seed_breaks_only_a_tie.
- box_check `noun`: split on `[(;]` only (no colon or comma) -> test_sam_3_is_asked_for_the_short_name.
- box_check `grounding`: drop the `fills` condition ->
  test_sam_3_s_masks_ground_a_box_before_the_judge_and_tighten_a_loose_one.
- box_check `from_proposals`: `return True` -> test_the_gate_passes_only_a_measured_box_checked_on_that_box.
- box_check `row_verdict`: an unmeasured box `return PASS` ->
  test_an_unmeasured_box_blocks_and_a_row_laid_from_the_plan_is_not_boxed.
- partition `mapping_problems`: `if False:` for the reasonless drop ->
  test_a_row_s_box_is_its_proposals_own_and_every_proposal_is_accounted_for.
- inventory `row_problems`: `if False:` for the unknown view ->
  test_an_inventory_row_says_where_it_is_seen_and_what_it_is.
- inventory `approved_inventory`: `if False:` for the approval ->
  test_the_cloud_refuses_a_missing_or_unapproved_inventory.
- duplicates `pair_problem`: `if False:` for two takes -> test_one_real_world_object_is_made_once_unless_a_row_says_why.
- cutsize `route`: `> MIN_CUT_SIDE` -> test_a_cut_out_under_the_limit_never_feeds_the_redraw.
- closeups `camera_for`: frame at 0.6 in place of FILL -> test_the_front_camera_frames_its_item_upright_from_its_front.
- closeups `camera_for`: `distance = blocked` (no clearance) ->
  test_every_camera_stands_inside_the_room_or_is_moved_or_dropped.
- closeups `label_of`: keep the words after the comma ->
  test_each_camera_carries_the_items_it_sees_with_their_boxes_and_words.
- closeups `resolve`: the lowest score wins -> test_a_pixel_has_one_owner_and_a_cut_out_keeps_only_its_pixels.
- place `read_look`: `if False:` for the kept look ->
  test_a_scene_s_style_is_its_environment_s_line_and_its_locked_concept_s_look.
- place `read_look`: `if False:` for the empty answer ->
  test_a_scene_with_no_locked_concept_or_an_empty_look_is_refused.
- data/definitions/place.json: the shared rule "Modules, ships and moving parts are built in code." ->
  test_every_place_keeps_only_its_name_and_style_and_no_shared_rule_sends_a_ship_to_code.
- lamps `light_at`: no least reach -> test_a_lamp_s_light_is_the_library_s_for_its_mount_never_a_typed_number.
- lamps `on_stem`: `return False` -> test_a_lamp_is_mounted_as_what_holds_it_and_at_its_head_only_by_its_metres.
- marble `generate`, and apart `paint`: `pass` for `compute.require_cleared` ->
  test_no_world_or_painting_is_bought_outside_a_cleared_run.
- data/definitions/ship_floor.json: a door 0.8 m wide ->
  test_the_ship_s_floor_plan_fits_its_46_m_hull_with_rooms_a_person_fits.
- ship_floor `overlap_faults`: `if False:` -> test_an_overlap_a_floor_under_the_keel_and_a_door_to_nowhere_are_faults.

    PROPS_HOME=$(mktemp -d) .venv/bin/python -m pytest tools/props/scene/test_a_scene_is_made_from_its_concept.py
"""
import copy
import json
import math
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


def test_boxes_spread_over_their_picture_pass_and_typed_ones_crowded_in_a_corner_fail():
    assert box_check.measured_problems(an_inventory(spread_over_the_picture()), {"v1": SIZE}) == []
    problems = box_check.measured_problems(an_inventory(crowded()), {"v1": SIZE})
    assert any("one quarter" in problem for problem in problems), problems
    assert any("span only" in problem for problem in problems), problems
    assert box_check.measured_problems(an_inventory(crowded(box_from=["v1.1"])), {"v1": SIZE}) == []  # measured
    small = [a_row(f"r{index}", [200 + 400 * index, 700, 240 + 400 * index, 740]) for index in range(6)]
    problems = box_check.measured_problems(an_inventory(small), {"v1": SIZE})
    assert any("cover" in problem and "its rows suggest" in problem for problem in problems), problems
    few = box_check.measured_problems(an_inventory(small[:4]), {"v1": SIZE})
    assert not any("its rows suggest" in problem for problem in few), few  # a few far things may be small


def test_a_box_outside_its_picture_or_over_the_whole_of_it_fails():
    rows = spread_over_the_picture() + [a_row("over", [2600, 1400, 2900, 1600])]
    problems = box_check.measured_problems(an_inventory(rows), {"v1": SIZE})
    assert any("row over" in problem and "not inside" in problem for problem in problems), problems
    whole = [0, 0, SIZE[0], SIZE[1]]
    rows = spread_over_the_picture() + [a_row("wall_lower", whole, group="kit: wall", repeats="across the room"),
                                        a_row("desk", whole, group="kit: furniture"), a_row("rack", whole)]
    problems = box_check.measured_problems(an_inventory(rows), {"v1": SIZE})
    assert {problem.split(":")[0] for problem in problems if "whole picture" in problem} == \
        {"row wall_lower", "row desk", "row rack"}, problems
    rows = spread_over_the_picture() + [a_row("hidden", None, unseen="behind the camera")]
    assert box_check.measured_problems(an_inventory(rows), {"v1": SIZE}) == []
    assert box_check.measured_problems(an_inventory(rows), {"v1": None}) == ["view v1: its picture is missing"]


def test_the_judge_sees_the_whole_picture_and_the_crop_once_a_seed(tmp_path):
    picture = tmp_path / "concept.png"
    Image.new("RGB", SIZE, (90, 90, 90)).save(picture)
    rows = spread_over_the_picture()[:2] + [a_row("wall", [0, 0, SIZE[0], SIZE[1]], group="kit: wall")]
    jobs = box_check.judge_jobs("camp", an_inventory(rows, str(picture)), {"v1": SIZE}, tmp_path / "judge",
                                box_check.SEEDS)
    assert len(jobs) == 2 * len(box_check.SEEDS)  # the kit wall's whole picture is not asked about
    assert {job["seed"] for job in jobs} == set(box_check.SEEDS)
    whole, cut = (pathlib.Path(path) for path in jobs[0]["images"])
    assert Image.open(whole).width == box_check.OVERVIEW_WIDE
    assert max(Image.open(cut).size) >= box_check.SHORTEST_CROP
    assert "the r0" in jobs[0]["text"]


def test_the_judges_majority_decides_and_a_third_seed_breaks_only_a_tie(tmp_path):
    shown = 'thinking... {"shows": true, "main": true, "what": "a locker"}'
    beside = '{"shows": true, "main": false, "what": "the wall beside a locker"}'
    assert box_check.verdict([shown, shown, beside])["passes"]
    failed = box_check.verdict([shown, beside, "no answer at all"])
    assert not failed["passes"] and failed["passed"] == 1 and failed["what"] == "the wall beside a locker"
    wall = '{"shows": false, "main": false, "what": "a wall"}'
    first, second, third = box_check.SEEDS
    jobs = [{"name": f"{key}~{seed}", "seed": seed, "text": "", "images": []} for key in ("agreed", "split", "unasked")
            for seed in (first, second)]
    for name, text in ((f"agreed~{first}", wall), (f"agreed~{second}", wall), (f"split~{first}", shown),
                       (f"split~{second}", wall)):
        (tmp_path / f"{name}.txt").write_text(text)
    assert [job["name"] for job in box_check.deciding_jobs(jobs, tmp_path)] == [f"split~{third}"]
    found = box_check.verdicts(jobs, tmp_path)
    assert set(found) == {"agreed"} and not found["agreed"]["passes"] and found["agreed"]["of"] == 2
    (tmp_path / f"split~{third}.txt").write_text(shown)
    assert box_check.verdicts(jobs, tmp_path)["split"] == {"passes": True, "passed": 2, "of": 3, "what": "a wall"}


def test_sam_3_is_asked_for_the_short_name():
    assert box_check.noun("stainless galley counter: worktop with hob and sink") == "stainless galley counter"
    assert box_check.noun("a strip lamp in a steel housing with a frosted lens, over a door") == "strip lamp"
    assert box_check.noun("lamp on a rod from the ceiling: housing and lens") == "lamp"
    assert box_check.nouns("plain lower wall panel, bolted") == ["plain lower wall panel", "panel"]
    assert box_check.nouns("hammer") == ["hammer"]


def test_sam_3_s_masks_ground_a_box_before_the_judge_and_tighten_a_loose_one():
    inside = {"box": [10, 10, 50, 50], "score": 0.9, "inside": 0.9, "fills": 0.6}
    tiny = {"box": [10, 10, 14, 14], "score": 0.9, "inside": 1.0, "fills": 0.01}
    elsewhere = {"box": [900, 10, 990, 80], "score": 0.8, "inside": 0.0, "fills": 0.0}
    room = {"box": [0, 0, 2700, 1500], "score": 0.9, "inside": 0.02, "fills": 0.9}
    assert box_check.grounding([elsewhere, inside], SIZE) == {"grounding": "grounded"}
    assert box_check.grounding([elsewhere, tiny], SIZE) == {"grounding": "loose", "found_at": [10, 10, 14, 14]}
    assert box_check.grounding([elsewhere], SIZE) == {"grounding": "off", "found_at": [900, 10, 990, 80]}
    assert box_check.grounding([room], SIZE) == {"grounding": "not found"}  # the whole room says nothing
    assert box_check.grounding([], SIZE) == {"grounding": "not found"}
    rows = spread_over_the_picture()[:2] + [a_row("wall", [0, 0, SIZE[0], SIZE[1]], group="kit: wall")]
    assert box_check.mask_jobs("camp", an_inventory(rows, "/concepts/K01.png"), {"v1": SIZE}) == [
        {"picture": "/concepts/K01.png", "rows": [{"key": "camp.r0", "nouns": ["r0"], "box": rows[0]["box"]},
                                                  {"key": "camp.r1", "nouns": ["r1"], "box": rows[1]["box"]},
                                                  {"key": "camp.wall", "nouns": ["wall"], "box": rows[2]["box"]}]}]
    grounded = {"camp.galley": {"grounding": "grounded"}, "camp.crate": {"grounding": "off", "found_at": [1, 2, 3, 4]},
                "camp.net": {"grounding": "not found"}, "camp.bin": {"grounding": "not found"}}
    judged = {"camp.galley.1-2-3-4": {"passes": False, "what": "a wall"},
              "camp.crate.1-2-3-4": {"passes": True, "what": ""},
              "camp.net.1-2-3-4": {"passes": False, "what": "a wall"}}
    results = box_check.decided(grounded, judged)
    assert [results[key]["passes"] for key in ("camp.galley", "camp.crate", "camp.net", "camp.bin")] == \
        [True, True, False, None]  # SAM 3 finding the words elsewhere leaves the box to the judge
    found = an_inventory([a_row("keyboard", [100, 100, 900, 600]), a_row("wall", [0, 0, 900, 600], group="kit: wall")])
    loose = {"camp.keyboard": {"grounding": "loose", "found_at": [400, 300, 520, 340]},
             "camp.wall": {"grounding": "loose", "found_at": [0, 0, 10, 10]}}
    assert box_check.tighten("camp", found, loose) == ["keyboard", "wall"]  # a repeating row boxes one example
    assert found["rows"][0]["box"] == [400, 300, 520, 340] and found["rows"][1]["box"] == [0, 0, 10, 10]


@pytest.fixture
def partitioned(tmp_path, monkeypatch):
    """A place with one picture, its proposals and its recorded results in a partition folder; call it with
    {row: (box, box_from)} for its inventory."""
    picture = tmp_path / "concept.png"
    Image.new("RGB", SIZE, (90, 90, 90)).save(picture)
    monkeypatch.setattr(box_check, "PARTITION", tmp_path / "partition")
    (tmp_path / "partition" / "camp").mkdir(parents=True)
    proposals = [{"id": "v1.1", "view": "v1", "box": [113, 207, 391, 618], "area": 90000},
                 {"id": "v1.2", "view": "v1", "box": [1503, 811, 1702, 1033], "area": 30000}]
    (tmp_path / "partition" / "camp" / "proposals.json").write_text(json.dumps(proposals))
    (tmp_path / "partition" / "camp" / "boxes.json").write_text(json.dumps({
        "galley": {"passes": True, "by": "SAM 3: grounded", "box": [113, 207, 391, 618]},
        "crate": {"passes": True, "by": "SAM 3: grounded", "box": [1503, 811, 1702, 1033]}}))

    def made(boxes):
        rows = [a_row(name, box, **({"box_from": source} if source else {})) for name, (box, source) in boxes.items()]
        return an_inventory(rows, str(picture))
    return made


def test_the_gate_passes_only_a_measured_box_checked_on_that_box(partitioned):
    found = partitioned({"galley": ([113, 207, 391, 618], ["v1.1"]), "crate": ([1503, 811, 1702, 1033], ["v1.2"])})
    assert box_check.gate("camp", found)["result"] == "pass"
    found["rows"][1]["box"] = [1503, 811, 1702, 1040]  # moved by hand since: no longer its proposal's box
    assert box_check.gate("camp", found)["rows"]["crate"]["result"] == "fail"
    found = partitioned({
        "galley": ([600, 200, 900, 640], None),               # round numbers, typed (the camp's, 2026-10-09)
        "crate": ([0, 0, SIZE[0], SIZE[1]], None),           # the whole picture
        "table": ([113, 207, 391, 618], ["v1.2"]),           # names a proposal it is not the box of
        "bunk": ([1200, 300, 1300, 400], ["v1.1"])})          # outside the object it names
    rows = box_check.gate("camp", found)["rows"]
    assert all(rows[name]["result"] == "fail" for name in ("galley", "crate", "table", "bunk")), rows
    assert "typed" in rows["galley"]["why"] and "whole picture" in rows["crate"]["why"]


def test_an_unmeasured_box_blocks_and_a_row_laid_from_the_plan_is_not_boxed(partitioned):
    found = partitioned({"galley": ([113, 207, 391, 618], ["v1.1"]), "crate": ([1503, 811, 1701, 1033], None)})
    verdict = box_check.gate("camp", found)
    assert verdict["rows"]["crate"]["result"] == "unknown" and verdict["result"] == "unknown", verdict
    found = partitioned({"galley": ([113, 207, 391, 618], ["v1.1"]), "ground": ([0, 0, SIZE[0], SIZE[1]], None)})
    found["rows"][1]["route"] = "ground"
    verdict = box_check.gate("camp", found, box_check.UNBOXED)
    assert verdict["result"] == "pass" and verdict["unboxed"] == ["ground"], verdict
    assert box_check.gate("camp", found)["rows"]["ground"]["result"] == "fail"  # the close-ups crop by the box
    found["rows"][1]["route"] = "prop"
    assert box_check.gate("camp", found, box_check.UNBOXED)["rows"]["ground"]["result"] == "fail"


def a_partition_place():
    return {"rows": [{"id": "desk", "view": "v1", "box": None, "unseen": "x"},
                     {"id": "lamp", "view": "v1", "box": None, "unseen": "x"},
                     {"id": "wall", "view": "v1", "box": None, "unseen": "x", "repeats": "across the room"}]}


PROPOSALS = [{"id": "v1.1", "view": "v1", "box": [100, 100, 500, 400], "area": 90000, "share": 0.02},
             {"id": "v1.2", "view": "v1", "box": [120, 120, 200, 200], "area": 5000, "share": 0.001},
             {"id": "v1.3", "view": "v1", "box": [800, 50, 900, 150], "area": 8000, "share": 0.002},
             {"id": "v1.4", "view": "v1", "box": [1500, 900, 1900, 1300], "area": 120000, "share": 0.03}]


def test_a_row_s_box_is_its_proposals_own_and_every_proposal_is_accounted_for():
    """Tiles cover the picture; a mapping leaving a big proposal or a row out, or dropping one with no reason, is
    refused; applied boxes are the proposals' own; a pointer only picks proposals and is never kept as a box."""
    boxes = [box for _, _, box in partition.tile_boxes(SIZE)]
    assert min(box[0] for box in boxes) == 0 and max(box[2] for box in boxes) == SIZE[0]
    assert min(box[1] for box in boxes) == 0 and max(box[3] for box in boxes) == SIZE[1]
    unboxed = a_partition_place()
    for row in unboxed["rows"]:
        row.pop("unseen")
    problems = partition.mapping_problems(unboxed, PROPOSALS, {"v1.1": {"row": "desk"}, "v1.3": {"drop": ""}})
    assert any("v1.4 is neither" in line for line in problems), problems   # a big proposal left out
    assert not any("v1.2" in line for line in problems), problems           # a part of v1.1 needs no entry
    assert any("dropped without a reason" in line for line in problems), problems
    assert any("row lamp has no proposal" in line for line in problems), problems
    mapped = a_partition_place()
    new = partition.apply(mapped, PROPOSALS, {"v1.1": {"row": "desk"}, "v1.3": {"rows": ["lamp", "wall"]},
                                              "v1.4": {"new": "a crate"}})
    rows = {row["id"]: row for row in mapped["rows"]}
    assert rows["desk"]["box"] == [100, 100, 500, 400] and rows["desk"]["box_from"] == ["v1.1"]
    assert "unseen" not in rows["lamp"] and rows["wall"]["box"] == [800, 50, 900, 150]
    assert new[0]["words"] == "a crate" and new[0]["box"] == [1500, 900, 1900, 1300]
    mapping, matched = partition.snap(a_partition_place(), PROPOSALS,
                                      {"desk": [90, 90, 520, 420], "lamp": [790, 40, 910, 160]})
    assert matched["desk"]["proposals"] == ["v1.1", "v1.2"] and matched["lamp"]["proposals"] == ["v1.3"]
    assert mapping["v1.1"] == {"rows": ["desk"]}
    pointed = a_partition_place()
    partition.apply(pointed, PROPOSALS, mapping)
    assert {row["id"]: row["box"] for row in pointed["rows"]}["desk"] == [100, 100, 500, 400]


# ---- the inventory's shape -----------------------------------------------------------------------------------------

def a_scene_row(**changes):
    row = {"id": "r1", "view": "v1", "box": [10, 20, 300, 400], "name": "white louvred locker",
           "kind": "generate", "anchor": "wall", "size": [0.6, 0.5, 1.9], "count": 2,
           "thing": "prop:habitat_locker"}
    row.update(changes)
    return row


def a_scene(*rows, **changes):
    found = {"scene": "habitat", "place": "habitat",
             "plan": {"world": "w1", "seed": 7, "views": [{"id": "v1", "picture": "WORK/v1.png"}]},
             "approved": "2026-10-05, plan: w1", "migrated": "",
             "room": {"shell": "abc", "light": "place", "backdrop": "", "wall_fill": []},
             "rows": list(rows) or [a_scene_row()]}
    found.update(changes)
    return found


def test_an_inventory_row_says_where_it_is_seen_and_what_it_is():
    assert inventory.problems(a_scene(), "habitat") == []
    wrong = inventory.problems(a_scene(a_scene_row(view="v9")), "habitat")
    assert any("no box, no row" in line for line in wrong), wrong
    assert inventory.problems(a_scene(a_scene_row(box=None, unseen="behind the camera")), "habitat") == []
    wrong = inventory.problems(a_scene(a_scene_row(box=None)), "habitat")
    assert any("no 'unseen'" in line for line in wrong), wrong
    wrong = inventory.problems(a_scene(a_scene_row(kind="shared", anchor="somewhere", size=[1, 0, 1], count=0)),
                               "habitat")
    assert len(wrong) == 4, wrong  # its kind, anchor, size and count each named
    host = a_scene_row(id="r1", anchor="floor")
    assert inventory.problems(a_scene(host, a_scene_row(id="r2", anchor="on:r1")), "habitat") == []
    assert inventory.problems(a_scene(host, a_scene_row(id="r2", anchor="on:r7")), "habitat")
    assert inventory.problems(a_scene(a_scene_row(kind="mechanic", thing="node:Workstation")), "habitat")
    assert inventory.problems(a_scene(a_scene_row(kind="mechanic", thing="node:Workstation", prop="desk")),
                              "habitat") == []
    wrong = inventory.problems(a_scene(approved="", migrated="2026-10-06"), "habitat")
    assert any("approval" in line for line in wrong), wrong
    for scene, found in inventory.every_inventory().items():  # every committed inventory is sound
        if not found.get("no_place"):  # a line no place owns (the people's looks, #41): no scene's inventory
            assert inventory.problems(found, scene) == [], scene


def test_the_cloud_refuses_a_missing_or_unapproved_inventory(tmp_path):
    path = tmp_path / "habitat.json"
    with pytest.raises(SystemExit, match="no inventory"):
        inventory.approved_inventory(path)
    path.write_text(json.dumps(a_scene(approved="")))
    with pytest.raises(SystemExit, match="not approved"):
        inventory.approved_inventory(path)
    path.write_text(json.dumps(a_scene()))
    assert inventory.approved_inventory(path)["scene"] == "habitat"


# ---- one object made once ------------------------------------------------------------------------------------------

def a_made_row(name, kind="generate", **changes):
    return {"id": name, "kind": kind, "name": f"the {name}", **changes}


def two_places(first, second):
    return {"hub": {"rows": [first]}, "lab": {"rows": [second]}}


def test_one_real_world_object_is_made_once_unless_a_row_says_why():
    """The owner, 2026-10-09: no duplicates; reuse first."""
    found = duplicates.problems(two_places(a_made_row("desklamp"), a_made_row("desklamp")),
                                {"hub": {"desklamp_1": "desklamp-r6"}, "lab": {"desklamp_1": "desklamp-lab1"}})
    assert len(found) == 1 and "made twice" in found[0], found
    assert duplicates.problems(two_places(a_made_row("desklamp"), a_made_row("desklamp")),
                               {"hub": {"desklamp_1": "desklamp-r6"}, "lab": {"desklamp_1": "desklamp-r6"}}) == []
    found = duplicates.problems(two_places(a_made_row("kettle"), a_made_row("kettle")),
                                {"hub": {"kettle": "kettle-r1"}, "lab": {}})
    assert len(found) == 1 and "not made yet" in found[0], found
    found = duplicates.problems(two_places(a_made_row("far_palm"), a_made_row("palm")),
                                {"hub": {"far_palm": "palm-a"}, "lab": {"palm": "palm-b"}})
    assert len(found) == 1, found  # far scenery names the same object
    second = a_made_row("power_unit", own_model="a battery cabinet, not the small ground power unit")
    assert duplicates.problems(two_places(a_made_row("power_unit"), second),
                               {"hub": {"power_unit": "power_unit-g1"}, "lab": {"power_unit": "power_unit-r3"}}) == []
    models = {"hub": {"kettle": "kettle-r1"}, "lab": {"kettle": "kettle-r2"}}
    assert any("made from kettle-r2" in line for line in duplicates.problems(
        two_places(a_made_row("kettle"), a_made_row("kettle", reuse="hub:kettle")), models))
    assert any("no inventory row" in line for line in duplicates.problems(
        two_places(a_made_row("kettle"), a_made_row("kettle", reuse="hub:pot")), models))
    assert duplicates.problems(two_places(a_made_row("conduit_box", "code"), a_made_row("conduit_box", "code")),
                               {}) == []
    assert duplicates.problems(two_places(a_made_row("kettle"), a_made_row("kettle")),
                               {"hub": {"kettle": "kettle-r1"}}) == []  # a scene whose takes are not stored


# ---- the cut-out limit ---------------------------------------------------------------------------------------------

def test_a_cut_out_under_the_limit_never_feeds_the_redraw():
    """The owner, 2026-10-02: "the low-res ones look shit". A box is measured by its short side."""
    assert size_of([10, 20, 110, 320]) == {"width": 100, "height": 300, "short_side": 100, "area": 30000}
    assert route([0, 0, MIN_CUT_SIDE, 2 * MIN_CUT_SIDE], can_close_up=True) == "redraw"
    assert route([0, 0, MIN_CUT_SIDE, MIN_CUT_SIDE], can_close_up=False) == "redraw"
    tall_but_thin = [0, 0, MIN_CUT_SIDE - 1, 760]
    assert route(tall_but_thin, can_close_up=True) == "close-up"
    assert route(tall_but_thin, can_close_up=False) == "dropped"
    bench, counter_cabinet = [274, 371, 508, 616], [926, 443, 1170, 731]  # round one's habitat: these made models
    desk, desk_lamp = [812, 401, 984, 559], [901, 326, 933, 419]  # and these did not
    assert [route(box, False) for box in (bench, counter_cabinet, desk, desk_lamp)] == \
        ["redraw", "redraw", "dropped", "dropped"]


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


def test_the_front_camera_frames_its_item_upright_from_its_front():
    """In front of the rack (z under 3.7, level with it), its target in the middle of the picture, its front's height
    filling FILL of the frame, up in the world up in the picture."""
    item = wall_item()
    camera = closeups.camera_for(item, box_room(), DOWN, closeups.SHOTS[0])
    eye = np.array(camera["eye"])
    assert eye[2] < 3.7 and abs(eye[0]) < 1e-9 and abs(eye[1] - 0.55) < 1e-9
    pixel, depth = framed(camera, [camera["target"]])
    assert np.allclose(pixel[0], [camera["size"] / 2] * 2) and depth[0] > 0
    centre, (wide, deep, tall) = np.array(item["centre"]), item["size"]
    pixel, _ = framed(camera, [centre + [sx * wide / 2, sy * tall / 2, -deep / 2] for sx in (-1, 1) for sy in (-1, 1)])
    assert abs((pixel[:, 1].max() - pixel[:, 1].min()) / camera["size"] - closeups.FILL) < 0.02
    target = np.array(camera["target"])
    pixel, _ = framed(camera, [target + [0, -0.5, 0], target + [0, 0.5, 0]])
    assert pixel[0, 1] < pixel[1, 1]


def test_every_camera_stands_inside_the_room_or_is_moved_or_dropped():
    """The four shots stand inside the room (the sides either side of the front, the above one above the item); a
    wall behind pulls a camera in and widens its lens; a low wall in the way raises it; no room to stand drops it."""
    room = box_room()
    cameras = [closeups.camera_for(wall_item(), room, DOWN, shot) for shot in closeups.SHOTS]
    assert all(camera is not None and closeups.inside_room(room, np.array(camera["eye"]), DOWN) for camera in cameras)
    assert cameras[1]["eye"][0] * cameras[2]["eye"][0] < 0 and cameras[3]["eye"][1] < 0.55
    camera = closeups.camera_for(wall_item(centre=[0.0, 0.55, 1.1]), box_room(half=1.4), DOWN, closeups.SHOTS[0])
    assert camera is not None and camera["note"]
    assert camera["eye"][2] > -1.4 + closeups.CLEARANCE_M - 1e-6 and camera["fov"] > closeups.FOV_DEGREES
    assert closeups.camera_for(wall_item(centre=[0.0, 0.55, 0.2]), box_room(half=0.5), DOWN,
                               closeups.SHOTS[0]) is None
    walled = np.concatenate([room, solid([-4.0, 0.3, 2.8], [4.0, 1.5, 3.0])])
    assert closeups.camera_for(wall_item(), walled, DOWN, closeups.SHOTS[0]) is None
    camera = closeups.camera_or_raised(wall_item(), walled, DOWN, closeups.SHOTS[0])
    assert camera is not None and "raised" in camera["note"] and camera["eye"][1] < 0.55


def test_each_camera_carries_the_items_it_sees_with_their_boxes_and_words():
    room = box_room()
    items = [wall_item(name="equipment rack, 0.6 m"),
             wall_item(id="locker", name="tall locker", centre=[0.9, 0.55, 3.7]),
             wall_item(id="far", centre=[0.0, 0.55, -3.7], facing=[0, 0, 1])]
    front = next(camera for camera in closeups.plan(room, items, DOWN)
                 if camera["item"] == "rack" and camera["shot"] == "front")
    assert "rack" in front["prompts"] and "locker" in front["prompts"] and "far" not in front["prompts"]
    left, top, right, bottom = front["boxes"]["rack"]
    assert left < front["size"] / 2 < right and top < front["size"] / 2 < bottom
    assert abs((bottom - top) / front["size"] - closeups.FILL) < 0.05
    assert front["labels"] == {"rack": "equipment rack", "locker": "tall locker"}


def test_a_pixel_has_one_owner_and_a_cut_out_keeps_only_its_pixels():
    first = np.zeros((4, 4), bool)
    first[:, :3] = True
    second = np.zeros((4, 4), bool)
    second[:, 1:] = True
    owners = closeups.resolve([first, second], [0.6, 0.9])
    assert (owners[:, 0] == 0).all() and (owners[:, 1:] == 1).all()
    owners = closeups.resolve([first, second], [0.9, 0.6])
    assert (owners[:, :3] == 0).all() and (owners[:, 3] == 1).all()
    assert (closeups.resolve([np.zeros((2, 2), bool)], [0.9]) == -1).all()
    image = np.full((50, 50, 3), 200, np.uint8)
    mask = np.zeros((50, 50), bool)
    mask[10:30, 20:40] = True
    rgba = closeups.cut(image, mask, margin=0.1)  # 20 x 20 and a 10% margin a side
    assert rgba.shape == (24, 24, 4) and rgba[..., 3].sum() == 20 * 20 * 255
    assert closeups.cut(image, np.zeros((50, 50), bool)) is None
    assert closeups.extents([2.0, 0.5, 1.0], 0.0, 0.0) == (2.0, 1.0, 0.25)
    assert math.isclose(closeups.extents([2.0, 0.5, 1.0], 90.0, 0.0)[0], 0.5, abs_tol=1e-9)


# ---- a scene's style, from its design ------------------------------------------------------------------------------

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


def test_a_scene_s_style_is_its_environment_s_line_and_its_locked_concept_s_look(tmp_path):
    """The owner, 2026-10-21: no per-place prose decides a picture. A scene added in the app is worded from the
    environment concept's style line, then its locked concept's look, read once by one call on that very picture,
    kept, and read again only for a new lock."""
    asked = []

    def asker(question, picture):
        asked.append((question, picture.getpixel((0, 0))))
        return "  matte  sand-blasted steel, warm amber light "
    store, looks = a_design(tmp_path, "garden_shed", "a" * 64, (200, 10, 10)), tmp_path / "looks"
    assert "garden_shed" not in place.places()
    assert place.unread(["garden_shed"], store, looks) == ["garden_shed"]
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
    a_design(tmp_path, "garden_shed", "b" * 64, (10, 10, 200))  # a new lock: its look is read again
    place.style_text("garden_shed", store, asker, looks)
    assert asked[-1][1] == (10, 10, 200) and len(asked) == 2


def test_a_scene_with_no_locked_concept_or_an_empty_look_is_refused(tmp_path):
    store, looks = a_design(tmp_path, "galley", "c" * 64, (0, 0, 0)), tmp_path / "looks"
    with pytest.raises(SystemExit, match="no locked concept"):
        place.style_text("lab", store, lambda *_: "x", looks)
    with pytest.raises(SystemExit, match="no locked concept"):
        place.unread(["lab"], store, looks)
    with pytest.raises(SystemExit, match="came back empty"):
        place.style_text("galley", store, lambda *_: " ", looks)
    assert place.unread(["galley"], store, looks) == ["galley"]  # nothing kept for an empty answer


def test_every_place_keeps_only_its_name_and_style_and_no_shared_rule_sends_a_ship_to_code():
    """Every place keeps its name and style (its palette, materials, wear, light, pictures and plan were the old
    concepts' and were retired, 2026-10-21). A wording check guarding the owner's rule of 2026-10-07 (code builds only
    plain plates, pipes and trims): the shared rule "Modules, ships and moving parts are built in code" was what the
    hangar's code-built ship cited (design of 2026-10-11, section 9)."""
    for name, entry in place.places().items():
        if name == place.SHARED:
            assert entry["scale"]["eye_height"] == 1.6
            assert not [rule for rule in entry["rules"] if "ship" in rule.lower() and "code" in rule.lower()]
            continue
        assert "name" in entry and "style" in entry, name
        retired = {"plan", "palette", "materials", "wear", "light", "pictures"} & set(entry)
        assert not retired, f"{name} keeps retired fields {sorted(retired)}"


# ---- a lamp's light ------------------------------------------------------------------------------------------------

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
           {"id": "loop_b", "noun": "frame", "anchor": "on:loop_a"}]
WORDS = {"ceiling": ["ceiling", "roof"], "wall": ["wall", "walls"]}


def laid(*heights):
    return [{"kind": "x_lamp", "at": [0.0, height, 0.0]} for height in heights]


def test_a_lamp_s_light_is_the_library_s_for_its_mount_never_a_typed_number():
    """Owner, 2026-10-21: no per-scene list decides what a scene gets. A ceiling lamp whose pieces hang at 3.0, 3.0
    and 3.2 m hangs at their middle, 3.0 m: reach 2.0 x 3.0 = 6.0 m, strength 0.05 x 6.0 = 0.3; a wall lamp at 0.5 m
    keeps the least reach 1.5 m (strength 0.04 x 1.5 = 0.06); a lens part is not where it hangs; a locker with a typed
    light is no lamp; a light on the roof is a ceiling lamp (2.5 m: reach 5.0, strength 0.25)."""
    row = {"id": "pendant", "noun": "lamp", "anchor": "ceiling", "made": "kit piece"}
    assert lamps.light_of(row, laid(3.0, 3.0, 3.2), library=LAMP_LIBRARY) == \
        {"strength": 0.3, "reach": 6.0, "high": 0.05, "shadows": True}
    assert lamps.light_of({"id": "sconce", "noun": "light", "anchor": "wall"}, laid(0.5), library=LAMP_LIBRARY) == \
        {"strength": 0.06, "reach": 1.5, "high": 0.5, "shadows": False}
    pieces = laid(3.0) + [{"kind": "x_lamp", "at": [0.0, 0.0, 0.0], "part": "glow"}]
    assert lamps.light_of({"id": "lamp", "noun": "lamp", "anchor": "ceiling"}, pieces,
                          library=LAMP_LIBRARY)["reach"] == 6.0
    locker = {"id": "locker", "noun": "locker", "anchor": "floor", "light": {"strength": 9.0, "reach": 9.0}}
    assert lamps.light_of(locker, laid(0.0), library=LAMP_LIBRARY) is None
    assert lamps.light_of({"id": "roof_light", "noun": "light", "anchor": "on:roof_dome"}, laid(2.5), READING,
                          library=LAMP_LIBRARY, words=WORDS) == \
        {"strength": 0.25, "reach": 5.0, "high": 0.05, "shadows": True}


def test_a_lamp_is_mounted_as_what_holds_it_and_at_its_head_only_by_its_metres():
    """`on:<row>`: the held row's noun, else its own anchor, else what it is on in turn; a desk lamp stands. A street
    lamp 5 m tall on 0.4 m, or a light on a 6 m mast, is at its head; a squat tower and a table lamp stand."""
    def mount(on):
        return lamps.mount_of({"id": "lamp", "noun": "lamp", "anchor": on}, READING, WORDS)
    assert [mount(on) for on in ("on:roof_dome", "on:left_wall", "on:ceiling_beam", "on:ribs", "on:desk",
                                 "on:loop_a", "on:nothing", "floor")] == \
        ["ceiling", "wall", "ceiling", "wall", "stands", "stands", "stands", "stands"]
    rows = READING + [{"id": "mast", "noun": "mast", "anchor": "ground", "size": [0.3, 0.3, 6.0]}]
    assert lamps.mount_of({"id": "street_lamp", "name": "street lamp", "noun": "lamp", "anchor": "ground",
                           "size": [0.4, 0.4, 5.0]}, rows, WORDS) == "head"
    assert lamps.mount_of({"id": "light", "noun": "light", "anchor": "on:mast", "size": [0.5, 0.3, 0.4]}, rows,
                          WORDS) == "head"
    assert lamps.mount_of({"id": "floodlight_tower", "name": "floodlight tower", "noun": "tower", "anchor": "ground",
                           "size": [3.0, 3.0, 4.0]}, rows, WORDS) == "stands"
    assert lamps.mount_of({"id": "table_lamp", "name": "table lamp", "noun": "lamp"}, rows, WORDS) == "stands"
    assert "head" not in lamps.mount_words() and lamps.mounts()["head"]["high"] > 0.9
    assert {"ceiling", "roof"} <= set(lamps.mount_words()["ceiling"]) and "wall" in lamps.mount_words()["wall"]
    for name in ("ceiling", "wall", "stands"):
        assert set(lamps.mounts()[name]) == set(LAMP_LIBRARY[name]), name


# ---- Marble's paid calls -------------------------------------------------------------------------------------------

def test_no_world_or_painting_is_bought_outside_a_cleared_run(tmp_path, monkeypatch):
    """Fault (design of 2026-10-11, section 6): generate (1,500 to 3,000 credits) and paint (80) called the World API
    for any caller, outside the runner's gate and the owner's yes."""
    sent = []
    monkeypatch.setattr(marble, "call", lambda *arguments: sent.append(arguments))
    monkeypatch.delenv(marble.compute.TICKET, raising=False)
    for paid_call in (lambda: marble.generate("lab", tmp_path, marble.MODEL, None),
                      lambda: marble.paint("lab", tmp_path, tmp_path / "depth.png", 5.0, "words", 7)):
        with pytest.raises(marble.compute.Refused, match="nothing rents outside a cleared run"):
            paid_call()
    assert sent == [], "the World API was called outside a cleared run"


# ---- the ship's floor plan -----------------------------------------------------------------------------------------

FLOOR = ship_floor.read_floor()


def room(floor, name):
    return next(space for space in ship_floor.spaces(floor) if space["name"] == name)


def test_the_ship_s_floor_plan_fits_its_46_m_hull_with_rooms_a_person_fits():
    """No fault; stations front to back to 46 m, a section of five corners widest at the waist; 0.9 x 2.0 m doors,
    rooms 2.2 to 4 m clear; the seven ship places one space each; the lock behind the side ring, its hull door out."""
    assert ship_floor.faults(FLOOR) == []
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
    lock, ring = room(FLOOR, "ship's lock"), FLOOR["hull"]["side_ring"]
    assert lock["side"] == ring["side"] and lock["y"][0] < ring["y"] < lock["y"][1]
    assert [door["leads"] for door in lock["doors"] if door["wall"] == "hull"] == ["outside, or a docked craft"]


def test_an_overlap_a_floor_under_the_keel_and_a_door_to_nowhere_are_faults():
    floor = copy.deepcopy(FLOOR)
    room(floor, "storage")["y"] = [18.0, 27.2]
    assert "cockpit and nav and storage overlap" in ship_floor.faults(floor)
    floor = copy.deepcopy(FLOOR)
    room(floor, "engine and power room")["floors"] = [[31.5, 2.4]]
    assert any("over its floor's structure" in fault for fault in ship_floor.faults(floor))
    floor = copy.deepcopy(FLOOR)
    room(floor, "galley")["doors"][0]["leads"] = "bridge"
    found = ship_floor.faults(floor)
    assert "galley: a door leads to bridge, no space of the plan" in found and "galley: no door to the walkway" in found
