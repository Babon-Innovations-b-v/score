"""An accepted gap moves only the faults it names down the line, never loosens a gate (gaps.py): a failing gate passes
only when every finding is a named object's (of the entry's kind when it says one; by its row for a JSON finding),
keeping the findings; any other fault still fails it; a named unknown moves and another stays; complete fails every
gap by name with its numbers, the owner's and the ones a row wrote in its output; a gap is an input of complete and of
the row it names alone, and only complete's code version holds gaps.py, so moving a verdict re-makes nothing paid.

The owner's gap decisions of the old concepts were retired with them (2026-10-21), so each test writes the decision it
judges, in the file's own form, into a gaps folder of its own.

Breaks that turn it red (each applied once and seen red, then reverted):
- `moved`: `if not all(any(covers(...)) ...)` read with `any` over the findings  -> the named-faults cases (another
  fault moves too).
- `covers`: `and entry.get("contains", "") in finding` dropped  -> the order case (a colour fault moves).
- `object_of`: the JSON branch dropped  -> the rows and boxes cases.
- `moved`: the unknown branch dropped  -> the unknown test.
- `files`: the `row is not None and ...` narrowing dropped  -> the inputs test (the paint reads the street's gaps).
- `judge_accepted`: `written(inputs)` left out  -> the written-gap test.
"""
import contextlib
import json
import pathlib
import tempfile

import pytest

from score import checks, graph, stages
from score.graph import _code
from score.stages import gaps

ROWS = {row.name: row for row in stages.STAGES}
DECIDED = "owner, 2026-10-14 08:40"


def entry(name, row, check, objects, faults, **more):
    """One accepted gap in the file's form."""
    return {"name": name, "row": row, "check": check, "objects": objects, "reason": "a test's decision",
            "decided": DECIDED, "faults": faults, **more}


@contextlib.contextmanager
def decided(place_gaps):
    """gaps.FOLDER a folder of its own holding {place: [gap]} as the owner's files, for the length of a `with`."""
    held = gaps.FOLDER
    with tempfile.TemporaryDirectory() as folder:
        gaps.FOLDER = pathlib.Path(folder)
        for place, found in place_gaps.items():
            (gaps.FOLDER / f"{place}.json").write_text(json.dumps({"gaps": found}))
        try:
            yield
        finally:
            gaps.FOLDER = held


def recorded(place):
    return {gaps.NAME: str(gaps.FOLDER / f"{place}.json")}


def failed(check, findings):
    return checks.Verdict(check, checks.FAIL, f"{len(findings)} faults", {"faults": len(findings)},
                          {"faults": "lower"}, tuple(findings))


RESTING = entry("fragments: resting in the regolith", "assembly", "resting",
                [f"/wreck/Objects/fragment_{number}" for number in (1, 2)],
                [f"/wreck/Objects/fragment_{number}: sunk 0.05 under its contact points" for number in (1, 2)])
SHIP = entry("ship: no made model", "assembly", "placeholders",
             ["/hangar/Structure/ship", "/hangar/Structure/ship_legs"],
             [f"/hangar/Structure/{name}: plain: drawn by the record's {name} builder (a made piece's stand-in)"
              for name in ("ship", "ship_legs")])
ORDER = entry("fluid shelves: order", "surfaces-check", "baked matches its surfaces", ["fluid_shelves_1"],
              ["fluid_shelves_1: plastic_grey baked over galvanized_steel: the close-up's order reversed"],
              contains="order")
ROWS_GAP = entry("far ferry: no stage makes it", "complete", "rows", ["far_ferry"],
                 [json.dumps({"row": "far_ferry", "why": "no object of this row"})])
BOXES_GAP = entry("wall screen: its box", "complete", "boxes", ["wall_screen"],
                  [json.dumps({"row": "wall_screen", "result": "fail", "why": "judge: no screen in the box"})])
GAME = entry("launch: layout taken from the source game", "complete", "game", ["data/scene/launch.json"],
             ["data/scene/launch.json: 12 entries take their numbers from the game (source), 4 positions placed"])
CASES = {  # gap, another fault of the same gate no gap names
    "plain objects": (RESTING, "/wreck/Objects/fragment_3: floats 0.04: nothing under it"),
    "placeholders": (SHIP, "/hangar/Structure/crate: plain: drawn by the record's box builder (a made piece's "
                           "stand-in)"),
    "of its kind only": (ORDER, "fluid_shelves_1: crane_yellow_paint baked [70.1, 5.0, 60.2] against [74.0, 4.1, "
                                "70.3] (dE 36.4)"),
    "rows by row": (ROWS_GAP, json.dumps({"row": "far_tower", "why": "no object of this row"})),
    "boxes by row": (BOXES_GAP, json.dumps({"row": "bunk", "result": "fail", "why": "judge: x"})),
    "a record by its path": (GAME, "scene-record output x/record/launch.json: 1 entries take their numbers from the "
                                   "game (source), 1 positions placed from it"),
}


@pytest.mark.parametrize("case", sorted(CASES))
def test_only_the_named_faults_move_and_any_other_still_stops_the_line(case):
    gap, other = CASES[case]
    named = failed(gap["check"], gap["faults"])
    kept = gaps.moved(named, [gap])
    assert kept.answer == checks.PASS and kept.findings == named.findings, kept
    assert kept.measures["moved"] == len(gap["faults"]) and gap["name"] in kept.reason
    both = failed(gap["check"], [*gap["faults"], other])
    assert gaps.moved(both, [gap]) == both


def test_the_decision_file_is_read_by_row_and_check_and_a_pass_or_unknown_is_left_alone():
    with decided({"wreck": [RESTING, ORDER]}):
        found = gaps.entries(recorded("wreck"), "assembly", "resting")
    assert found == [RESTING]
    unknown = checks.Verdict("resting", checks.UNKNOWN, "no drop run")
    assert gaps.moved(unknown, found) == unknown


def test_a_named_unknown_moves_and_another_unknown_stays():
    """The overseer, 2026-10-15: the likeness no props file answers moves; another unknown stays."""
    found = [entry("launch: no likeness output", "complete", "likeness", [], [], unknown="no accepted likeness@street")]
    assert gaps.moved(checks.Verdict("likeness", checks.UNKNOWN, "no accepted likeness@street"), found).answer \
        == checks.PASS
    other = checks.Verdict("likeness", checks.UNKNOWN, "2 generated rows and no accepted likeness@launch")
    assert gaps.moved(other, found) == other


def test_a_gap_is_an_input_of_complete_and_of_the_row_it_names_alone():
    """The overseer, 2026-10-15: a street's gaps (complete's alone) made the paid paint at three places run again."""
    likeness = entry("launch: no likeness output", "complete", "likeness", [], [], unknown="x")
    with decided({"street": [likeness], "lab": [entry("chairs", "assembly", "placeholders", ["chair_1"], [])]}):
        for row in ("assembly", "surfaces-check", "surfaces-paint"):
            assert gaps.NAME not in ROWS[row].files("street"), row
        assert gaps.NAME in ROWS["complete"].files("street")
        assert gaps.NAME in ROWS["assembly"].files("lab") and gaps.NAME not in ROWS["surfaces-paint"].files("lab")
        assert not gaps.files("nowhere") and not gaps.files("nowhere", "assembly")


def test_complete_fails_each_accepted_gap_by_name_with_its_numbers():
    crane = entry("crane: a foot off the floor", "complete", "resting", ["/campgrounds/Objects/crane_1"],
                  ["/campgrounds/Objects/crane_1: foot 2 3.2 cm off the floor"])
    with decided({"campgrounds": [crane]}):
        found = gaps.judge_accepted(None, recorded("campgrounds"), None)
    assert found.answer == checks.FAIL and "crane: a foot off the floor" in found.reason
    assert found.findings == ("crane: a foot off the floor: /campgrounds/Objects/crane_1: foot 2 3.2 cm off the floor",)
    assert gaps.judge_accepted(None, {}, None).answer == checks.PASS


def test_complete_lists_a_gap_a_row_it_reads_wrote_in_its_output(tmp_path):
    """The neighbours' far city (lost with the old disk, #10): its own gaps.json, listed by complete by name."""
    lost = {"name": "far_city: shown by the plan, not stood", "row": "neighbours", "check": "neighbours",
            "objects": ["/flat/Places/far_city"], "reason": "its seed went with the old disk",
            "decided": "lost input, 2026-10-19 (the old disk)", "faults": []}
    (tmp_path / gaps.WRITTEN).write_text(json.dumps({"gaps": [lost]}))
    found = gaps.judge_accepted(None, {"neighbours": tmp_path}, None)
    assert found.answer == checks.FAIL and "far_city: shown by the plan, not stood" in found.reason, found


def test_the_table_wires_the_gates_and_only_complete_hashes_the_gaps():
    assert graph.GAPPED == "accepted gaps" and graph.GAPPED in [check.name for check in ROWS["complete"].checks]
    for row, gate in (("assembly", "placeholders"), ("assembly", "resting"), ("surfaces-check", "stands level"),
                      ("surfaces-check", "baked matches its surfaces"),
                      ("surfaces-paint", "colour against the close-up"), ("complete", "people"),
                      ("complete", "likeness"), ("complete", "motion"), ("complete", "rows"), ("complete", "game"),
                      ("complete", "boxes")):
        check = next(check for check in ROWS[row].checks if check.name == gate)
        assert hasattr(check.judge, "__wrapped__"), (row, gate)
    hashing = {name for name in ("assembly", "surfaces-check", "surfaces-paint", "complete")
               if _code.REPO / "score/stages/gaps.py" in _code.source_files(graph.code_functions(ROWS[name]))}
    assert hashing == {"complete"}, hashing  # moving a verdict re-makes nothing, the paid paint above all
