"""Accepted gaps (gaps.py): a moving gate passes only when every fault is a named object's, keeping the faults; any other
fault still fails it; complete fails each gap by name with its numbers; a place without a gaps file reads none.

The owner's gap decisions of the old concepts were retired with them (2026-10-21), so each test writes the decision it
judges, in the file's own form, into a gaps folder of its own.

Run: .venv/bin/python -m pytest score/stages/gaps_test.py
"""
import contextlib
import json
import pathlib
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from score import checks, stages  # noqa: E402
from score.stages import gaps  # noqa: E402

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
    """The place's gaps file as its rows read it."""
    return {gaps.NAME: str(gaps.FOLDER / f"{place}.json")}


def failed(check, findings):
    return checks.Verdict(check, checks.FAIL, f"{len(findings)} faults", {"faults": len(findings)},
                          {"faults": "lower"}, tuple(findings))


RESTING = entry("fragments: resting in the regolith", "assembly", "resting",
                [f"/wreck/Objects/fragment_{number}" for number in (1, 2)],
                [f"/wreck/Objects/fragment_{number}: sunk 0.05 under its contact points" for number in (1, 2)])
LIKENESS = entry("launch: no likeness output", "complete", "likeness", [], [],
                 unknown="no accepted likeness@street")
ORDER = entry("fluid shelves: order", "surfaces-check", "baked matches its surfaces", ["fluid_shelves_1"],
              ["fluid_shelves_1: plastic_grey baked over galvanized_steel: the close-up's order reversed"],
              contains="order")
ROWS_GAP = entry("far ferry: no stage makes it", "complete", "rows", ["far_ferry"],
                 [json.dumps({"row": "far_ferry", "why": "no object of this row"})])
BOXES_GAP = entry("wall screen: its box", "complete", "boxes", ["wall_screen"],
                  [json.dumps({"row": "wall_screen", "result": "fail", "why": "judge: no screen in the box"})])
CRANE = entry("crane: a foot off the floor", "complete", "resting", ["/campgrounds/Objects/crane_1"],
              ["/campgrounds/Objects/crane_1: foot 2 3.2 cm off the floor"])


def test_only_the_named_objects_faults_move_and_any_other_still_stops_the_line():
    with decided({"wreck": [RESTING]}):
        found = gaps.entries(recorded("wreck"), "assembly", "resting")
    named = failed("resting", found[0]["faults"])
    kept = gaps.moved(named, found)
    assert kept.answer == checks.PASS and kept.findings == named.findings and kept.measures["moved"] == 2
    other = failed("resting", [*found[0]["faults"], "/wreck/Objects/fragment_3: floats 0.04: nothing under it"])
    assert gaps.moved(other, found) == other
    unknown = checks.Verdict("resting", checks.UNKNOWN, "no drop run")
    assert gaps.moved(unknown, found) == unknown


def test_a_named_unknown_moves_and_another_unknown_or_fault_stays():
    """The overseer, 2026-10-15: the likeness no props file answers moves; another unknown stays."""
    found = [LIKENESS]
    assert gaps.moved(checks.Verdict("likeness", checks.UNKNOWN, "no accepted likeness@street"), found).answer \
        == checks.PASS
    other = checks.Verdict("likeness", checks.UNKNOWN, "2 generated rows and no accepted likeness@launch")
    assert gaps.moved(other, found) == other


def test_a_gap_is_an_input_of_complete_and_of_the_row_it_names_alone():
    """The overseer, 2026-10-15: a street's gaps (complete's alone) made the paid paint at three places run again.
    A gap is an input of complete and of the row it names alone; a place with no file reads none."""
    with decided({"street": [LIKENESS], "lab": [entry("chairs", "assembly", "placeholders", ["chair_1"], [])]}):
        for row in ("assembly", "surfaces-check", "surfaces-paint"):
            assert gaps.NAME not in ROWS[row].files("street"), row
        assert gaps.NAME in ROWS["complete"].files("street")
        assert gaps.NAME in ROWS["assembly"].files("lab") and gaps.NAME not in ROWS["surfaces-paint"].files("lab")
        assert not gaps.files("nowhere") and not gaps.files("nowhere", "assembly")


# The hangar's gap for its code-built stand-in ship as it stood until 2026-10-18 (two of its twelve meshes), when the
# ship was built in code from the plan v7 as a kit piece and the gap went.
SHIP_GAP = {"name": "ship: no made model", "row": "assembly", "check": "placeholders",
            "decided": "owner, 2026-10-14 08:40",
            "objects": ["/hangar/Structure/ship", "/hangar/Structure/ship_legs"],
            "faults": [f"/hangar/Structure/{name}: plain: drawn by the record's {builder} builder without saying which "
                       "plain thing it is (a made piece's stand-in)"
                       for name, builder in (("ship", "ship_hull"), ("ship_legs", "ship_legs"))]}


def test_a_placeholders_gap_moves_its_named_meshes_and_no_other():
    entry = [SHIP_GAP]
    assert gaps.moved(failed("placeholders", entry[0]["faults"]), entry).answer == checks.PASS
    stand_in = "/hangar/Structure/crate: plain: drawn by the record's box builder (a made piece's stand-in)"
    assert gaps.moved(failed("placeholders", [*entry[0]["faults"], stand_in]), entry).answer == checks.FAIL


def test_an_entry_of_one_kind_moves_only_that_kind_of_fault_of_its_objects():
    """An order fault moves from the bake check; a colour fault of the same model still fails it."""
    found = [ORDER]
    assert gaps.moved(failed("baked matches its surfaces", ORDER["faults"]), found).answer == checks.PASS
    colour = "fluid_shelves_1: crane_yellow_paint baked [70.1, 5.0, 60.2] against [74.0, 4.1, 70.3] (dE 36.4)"
    assert gaps.moved(failed("baked matches its surfaces", [*ORDER["faults"], colour]), found).answer == checks.FAIL


def test_a_row_no_stage_makes_moves_from_complete_s_rows_check_by_its_row():
    """The rows check's findings are JSON ({"row", "why"}): its gap names the rows, and another row still fails."""
    found = [ROWS_GAP]
    named = failed("rows", ROWS_GAP["faults"])
    assert gaps.moved(named, found).answer == checks.PASS
    other = failed("rows", [*named.findings, json.dumps({"row": "far_tower", "why": "no object of this row"})])
    assert gaps.moved(other, found) == other


def test_a_layout_from_the_game_moves_from_complete_s_game_check_by_its_record():
    """The game check's findings name their record: the named record's move, another record citing the game (the
    scene-record output) still fails."""
    record = "data/scene/launch.json"
    found = [entry("launch: layout taken from the source game", "complete", "game", [record],
                   [f"{record}: 12 entries take their numbers from the game (source), 4 positions placed from it"])]
    named = failed("game", found[0]["faults"])
    assert gaps.moved(named, found).answer == checks.PASS
    other = failed("game", [*named.findings, "scene-record output x/record/launch.json: 1 entries take their numbers "
                                             "from the game (source), 1 positions placed from it"])
    assert gaps.moved(other, found) == other


def test_a_box_moves_from_complete_s_boxes_check_by_its_row_and_another_box_still_fails():
    """The boxes check's findings are JSON ({"row", "result", "why"}): its gap names the rows, and another still fails."""
    found = [BOXES_GAP]
    named = failed("boxes", BOXES_GAP["faults"])
    assert gaps.moved(named, found).answer == checks.PASS
    other = failed("boxes", [*named.findings, json.dumps({"row": "bunk", "result": "fail", "why": "judge: x"})])
    assert gaps.moved(other, found) == other


def test_complete_fails_each_accepted_gap_by_name_with_its_numbers():
    with decided({"campgrounds": [CRANE]}):
        found = gaps.judge_accepted(None, recorded("campgrounds"), None)
    assert found.answer == checks.FAIL and "crane: a foot off the floor" in found.reason
    assert any("3.2 cm off the floor" in finding for finding in found.findings)
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
    from score.graph import GAPPED
    assert GAPPED == "accepted gaps" and GAPPED in [check.name for check in ROWS["complete"].checks]
    for row, gate in (("assembly", "placeholders"), ("assembly", "resting"), ("surfaces-check", "stands level"),
                      ("surfaces-check", "baked matches its surfaces"),
                      ("surfaces-paint", "colour against the close-up"), ("complete", "people"), ("complete", "likeness"),
                      ("complete", "motion"), ("complete", "rows"), ("complete", "game"), ("complete", "boxes")):
        check = next(check for check in ROWS[row].checks if check.name == gate)
        assert hasattr(check.judge, "__wrapped__"), (row, gate)
    assert hasattr(ROWS["surfaces-paint"].files, "carries") and hasattr(ROWS["surfaces-paint"].files, "wide")
    from score import graph
    from score.graph import _code
    hashing = {name for name in ("assembly", "surfaces-check", "surfaces-paint", "complete")
               if _code.REPO / "score/stages/gaps.py" in _code.source_files(graph.code_functions(ROWS[name]))}
    assert hashing == {"complete"}, hashing  # moving a verdict re-makes nothing, the paid paint above all
