"""Named gaps (gaps.py): a moving gate passes only when every fault is a named object's, keeping the faults; any other
fault still fails it; complete fails each gap by name with its numbers; a place without a gaps file reads none.

Run: .venv/bin/python -m pytest score/stages/gaps_test.py
"""
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from score import checks, stages  # noqa: E402
from score.stages import gaps  # noqa: E402

ROWS = {row.name: row for row in stages.STAGES}


def recorded(place):
    """The place's gaps file as its rows read it."""
    return {gaps.NAME: str(gaps.FOLDER / f"{place}.json")}


def failed(check, findings):
    return checks.Verdict(check, checks.FAIL, f"{len(findings)} faults", {"faults": len(findings)},
                          {"faults": "lower"}, tuple(findings))


def test_only_the_named_objects_faults_move_and_any_other_still_stops_the_line():
    entry = gaps.entries(recorded("wreck"), "assembly", "resting")
    named = failed("resting", entry[0]["faults"])
    kept = gaps.moved(named, entry)
    assert kept.answer == checks.PASS and kept.findings == named.findings and kept.measures["moved"] == 7
    other = failed("resting", [*entry[0]["faults"], "/wreck/Objects/fragment_3: floats 0.04: nothing under it"])
    assert gaps.moved(other, entry) == other
    unknown = checks.Verdict("resting", checks.UNKNOWN, "no drop run")
    assert gaps.moved(unknown, entry) == unknown


def test_a_named_unknown_moves_and_another_unknown_or_fault_stays():
    """The overseer, 2026-10-15: the likeness no props file answers, the square's still cloth and its people."""
    entry = gaps.entries(recorded("street"), "complete", "likeness")
    unknown = checks.Verdict("likeness", checks.UNKNOWN, entry[0]["faults"][0].split(": ", 1)[1])
    assert gaps.moved(unknown, entry).answer == checks.PASS
    other = checks.Verdict("likeness", checks.UNKNOWN, "2 generated rows and no accepted likeness@launch")
    assert gaps.moved(other, entry) == other
    for check in ("people", "motion"):
        entry = gaps.entries(recorded("square"), "complete", check)
        assert gaps.moved(failed(check, entry[0]["faults"]), entry).answer == checks.PASS
        assert gaps.moved(failed(check, [*entry[0]["faults"], "clock: no motion of the records moves with it in its "
                                                               "name"]), entry).answer == checks.FAIL


def test_a_gap_is_an_input_of_complete_and_of_the_row_it_names_alone():
    """The overseer, 2026-10-15: the street's gaps (complete's alone) made the paid paint at three places run again.
    A gap is an input of complete and of the row it names alone (the lab's chairs: the assembly's, never the paint's)."""
    for row in ("assembly", "surfaces-check", "surfaces-paint"):
        assert gaps.NAME not in ROWS[row].files("street"), row
    assert gaps.NAME in ROWS["complete"].files("street")
    for row in ("assembly", "surfaces-check", "surfaces-paint"):  # keyed whole since 2026-10-14, as before
        assert gaps.NAME in ROWS[row].files("hangar"), row
    assert gaps.NAME in ROWS["assembly"].files("lab") and gaps.NAME not in ROWS["surfaces-paint"].files("lab")


def test_the_hangars_twelve_ship_meshes_move_from_placeholders():
    entry = gaps.entries(recorded("hangar"), "assembly", "placeholders")
    assert len(entry[0]["objects"]) == 12 and entry[0]["name"] == "ship: no made model"
    assert gaps.moved(failed("placeholders", entry[0]["faults"]), entry).answer == checks.PASS
    stand_in = "/hangar/Structure/crate: plain: drawn by the record's box builder (a made piece's stand-in)"
    assert gaps.moved(failed("placeholders", [*entry[0]["faults"], stand_in]), entry).answer == checks.FAIL


def test_an_entry_of_one_kind_moves_only_that_kind_of_fault_of_its_objects():
    """The garage's order faults move from the bake check; a colour fault of the same model still fails it."""
    entry = gaps.entries(recorded("garage"), "surfaces-check", "baked matches its surfaces")
    assert gaps.moved(failed("baked matches its surfaces", entry[0]["faults"]), entry).answer == checks.PASS
    colour = "fluid_shelves_1: crane_yellow_paint baked [70.1, 5.0, 60.2] against [74.0, 4.1, 70.3] (dE 36.4)"
    assert gaps.moved(failed("baked matches its surfaces", [*entry[0]["faults"], colour]), entry).answer == checks.FAIL


def test_a_row_no_stage_makes_moves_from_complete_s_rows_check_by_its_row():
    """The rows check's findings are JSON ({"row", "why"}): its gap names the rows, and another row still fails."""
    entry = gaps.entries(recorded("launch"), "complete", "rows")
    named = failed("rows", entry[0]["faults"] + entry[1]["faults"])
    assert gaps.moved(named, entry).answer == checks.PASS
    other = failed("rows", [*named.findings, json.dumps({"row": "far_ferry", "why": "no object of this row"})])
    assert gaps.moved(other, entry) == other


def test_a_layout_from_the_game_moves_from_complete_s_game_check_by_its_record():
    """The overseer, 2026-10-15: the 18 places whose records cite the source game ship as named gaps; the game
    check's findings name their record, and another record citing the game (the scene-record output) still fails."""
    entry = gaps.entries(recorded("launch"), "complete", "game")
    assert entry and entry[0]["name"].startswith("launch: layout taken from the source game: 12 citations, 4 positions")
    named = failed("game", entry[0]["faults"])
    assert gaps.moved(named, entry).answer == checks.PASS
    other = failed("game", [*named.findings, "scene-record output x/record/launch.json: 1 entries take their numbers "
                                             "from the game (source), 1 positions placed from it"])
    assert gaps.moved(other, entry) == other


def test_a_box_moves_from_complete_s_boxes_check_by_its_row_and_another_box_still_fails():
    """The boxes check's findings are JSON ({"row", "result", "why"}): its gap names the rows, and another still fails."""
    entry = gaps.entries(recorded("quarters"), "complete", "boxes")
    named = failed("boxes", [fault for gap in entry for fault in gap["faults"]])
    assert gaps.moved(named, entry).answer == checks.PASS
    other = failed("boxes", [*named.findings, json.dumps({"row": "wall_screen", "result": "fail", "why": "judge: x"})])
    assert gaps.moved(other, entry) == other


def test_complete_fails_each_named_gap_by_name_with_its_numbers():
    found = gaps.judge_named(None, recorded("campgrounds"), None)
    assert found.answer == checks.FAIL and "crane: a foot off the floor" in found.reason
    assert any("3.2 cm off the floor" in finding for finding in found.findings)
    assert gaps.judge_named(None, {}, None).answer == checks.PASS


def test_only_places_with_a_gaps_file_read_one_and_the_table_wires_the_three_gates():
    places = sorted(path.stem for path in gaps.FOLDER.glob("*.json"))
    assert places == ["airlock", "camp", "campgrounds", "cockpit", "engineroom", "flat", "galley", "garage", "greenhouse",
                      "habitat", "hangar", "hub", "lab", "launch", "navigation", "old_station", "quarters", "shiplock", "square",
                      "stairwell", "storage", "street", "tube", "walkway", "workshop", "wreck"], places
    assert gaps.NAME in ROWS["assembly"].files("hangar") and gaps.NAME not in ROWS["assembly"].files("gdoor")
    # a gate given gaps after 2026-10-14 reads only a file naming it, the KEYED_WHOLE places too
    assert gaps.NAME in ROWS["complete-boxes"].files("walkway") and gaps.NAME not in ROWS["complete-boxes"].files("hangar")
    assert gaps.files("galley", "complete-boxes") and not gaps.files("hangar", "complete-boxes")
    assert gaps.NAME in ROWS["complete"].files("wreck") and gaps.NAME not in ROWS["complete"].files("gdoor")
    from score.graph import GAPPED
    assert GAPPED == "named gaps" and GAPPED in [check.name for check in ROWS["complete"].checks]
    for row, gate in (("assembly", "placeholders"), ("assembly", "resting"), ("surfaces-check", "stands level"),
                      ("surfaces-check", "baked matches its surfaces"),
                      ("surfaces-paint", "colour against the close-up"), ("complete", "people"), ("complete", "likeness"),
                      ("complete", "motion"), ("complete", "rows"), ("complete", "game"),
                      ("complete", "boxes"), ("complete-boxes", "grounded")):
        check = next(check for check in ROWS[row].checks if check.name == gate)
        assert hasattr(check.judge, "__wrapped__"), (row, gate)
    assert hasattr(ROWS["surfaces-paint"].files, "carries") and hasattr(ROWS["surfaces-paint"].files, "wide")
    from score import graph
    from score.graph import _code
    hashing = {name for name in ("assembly", "surfaces-check", "surfaces-paint", "complete-boxes", "complete")
               if _code.REPO / "score/stages/gaps.py" in _code.source_files(graph.code_functions(ROWS[name]))}
    assert hashing == {"complete"}, hashing  # moving a verdict re-makes nothing, the paid paint above all
    every = [entry for place in places for entry in json.loads((gaps.FOLDER / f"{place}.json").read_text())["gaps"]]
    for entry in every:
        assert entry["faults"] and all(gaps.object_of(fault) in entry["objects"] for fault in entry["faults"])
