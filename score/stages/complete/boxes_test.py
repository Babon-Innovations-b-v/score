"""The completion gate's evidence on a ship place, both ways (2026-10-15: complete@quarters and complete@walkway
answered unknown on their boxes and their people).

complete-boxes measures every boxed row no other box row measures (a code row, a row taken from another place's take),
view by view, and leaves the rows machines-boxes measures to it; it applies to the ship's places only. A ship place's
cast record names who is there (nobody, or the cockpit's two pilots of the brief), so the people check
answers, where a place with no record stays unknown.

Run: .venv/bin/python score/stages/complete/boxes_test.py
"""
import json
import pathlib
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tools/usd"))
from score import stages  # noqa: E402
import score.stages.complete.boxes as boxes  # noqa: E402
import score.stages.machines.boxes as machine_boxes  # noqa: E402
import contents  # noqa: E402

SHIP = ("cockpit", "quarters", "navigation", "galley", "storage", "engineroom", "shiplock", "walkway")


def inventory(place):
    return json.loads((REPO / "data/inventory" / f"{place}.json").read_text())


def test_the_rows_no_other_box_row_measures():
    """Both ways: the cockpit's code rows (its door leaf, its deck plates) are measured here, its machine-boxed rows
    (the pilot seat, flagged ground_box) are not; the row applies to a ship place and not to an old one."""
    rows = {row["id"] for row in boxes.other_rows(inventory("cockpit"))}
    assert {"door_leaf", "ring_floor_plate", "hatch_door_frame"} <= rows and "pilot_seat" not in rows, rows
    row = next(row for row in stages.STAGES if row.name == "complete-boxes")
    if not stages.ship_place("cockpit"):
        raise SystemExit("cockpit has no ship base stage on this machine (usd-ship/cockpit): cannot test the table")
    assert row.applies("cockpit") and not row.applies("hub")


def test_the_other_rows_are_measured_as_machines_boxes_measures():
    """The cockpit's other rows, on two views (its door rows on v3, its deck rows on v1), go to machines-boxes' make
    in one listing, each flagged as a row it measures; the listing is not left in the output."""
    calls = []

    def make(inputs, out, seed, params):
        listed = json.loads(pathlib.Path(inputs["inventory"]).read_text())["rows"]
        calls.append({row["id"]: row["ground_box"] for row in listed})
    kept = machine_boxes.make_boxes
    machine_boxes.make_boxes = make
    try:
        with tempfile.TemporaryDirectory() as temporary:
            boxes.make_boxes({"inventory": REPO / "data/inventory/cockpit.json"}, pathlib.Path(temporary), 0, {})
            assert not list(pathlib.Path(temporary).iterdir()), "the flagged rows are the make's input, not its output"
    finally:
        machine_boxes.make_boxes = kept
    assert len(calls) == 1 and set(calls[0]) == {row["id"] for row in boxes.other_rows(inventory("cockpit"))}
    assert all(calls[0].values()) and "pilot_seat" not in calls[0]


def an_empty_stage(place):
    from pxr import Usd, UsdGeom
    stage = Usd.Stage.CreateInMemory()
    UsdGeom.Xform.Define(stage, f"/{place}")
    return stage


def test_a_ship_place_names_its_people():
    """Both ways: every ship place has a cast record; one naming nobody passes the people check, the cockpit's two
    pilots of the owner's brief (no look made) fail it by name, and a place with no record answers unknown."""
    for place in SHIP:
        cast = contents.record("characters", place)
        answer, faults, _ = contents.judge_people(an_empty_stage(place), place, inventory(place), {})
        if place == "cockpit":
            assert cast.get("count_reason") and answer == contents.FAIL, (answer, faults)
            assert faults == ["pilot_port: in the cast, not on the stage",
                              "pilot_starboard: in the cast, not on the stage"], faults
            continue
        assert cast["people"] == [] and cast["note"] and answer == contents.PASS and not faults, (place, faults)
    answer, _, why = contents.judge_people(an_empty_stage("nowhere"), "nowhere", {"rows": []}, {})
    assert answer == contents.UNKNOWN and "no cast" in why


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
