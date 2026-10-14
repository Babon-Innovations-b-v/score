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


def test_the_hangars_twelve_ship_meshes_move_from_placeholders():
    entry = gaps.entries(recorded("hangar"), "assembly", "placeholders")
    assert len(entry[0]["objects"]) == 12 and entry[0]["name"] == "ship: no made model"
    assert gaps.moved(failed("placeholders", entry[0]["faults"]), entry).answer == checks.PASS
    stand_in = "/hangar/Structure/crate: plain: drawn by the record's box builder (a made piece's stand-in)"
    assert gaps.moved(failed("placeholders", [*entry[0]["faults"], stand_in]), entry).answer == checks.FAIL


def test_complete_fails_each_named_gap_by_name_with_its_numbers():
    found = gaps.judge_named(None, recorded("campgrounds"), None)
    assert found.answer == checks.FAIL and "crane: a foot off the floor" in found.reason
    assert any("3.2 cm off the floor" in finding for finding in found.findings)
    assert gaps.judge_named(None, {}, None).answer == checks.PASS


def test_only_places_with_a_gaps_file_read_one_and_the_table_wires_the_three_gates():
    places = sorted(path.stem for path in gaps.FOLDER.glob("*.json"))
    assert places == ["campgrounds", "hangar", "wreck"], places
    assert gaps.NAME in ROWS["assembly"].files("hangar") and gaps.NAME not in ROWS["assembly"].files("hub")
    assert gaps.NAME in ROWS["complete"].files("wreck") and gaps.NAME not in ROWS["complete"].files("flat")
    assert "named gaps" in [check.name for check in ROWS["complete"].checks]
    for row, gate in (("assembly", "placeholders"), ("assembly", "resting"), ("surfaces-check", "stands level")):
        check = next(check for check in ROWS[row].checks if check.name == gate)
        assert hasattr(check.judge, "__wrapped__"), (row, gate)
    every = [entry for place in places for entry in json.loads((gaps.FOLDER / f"{place}.json").read_text())["gaps"]]
    for entry in every:
        assert entry["faults"] and all(gaps.object_of(fault) in entry["objects"] for fault in entry["faults"])
