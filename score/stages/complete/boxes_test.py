"""The completion gate's evidence on a ship place, both ways (2026-10-15: complete@quarters and complete@walkway answered
unknown on their boxes and their people).

complete-boxes measures every boxed row no other box row measures (a code row, a row taken from another place's take),
view by view, and leaves the rows machines-boxes measures to it; it applies to the ship's places only. A ship place's
cast record names nobody, so the people check passes on it, where a place with no record stays unknown.

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


def test_one_make_a_view():
    """machines-boxes' make gives every job its first row's picture, so each view is made on its own: the cockpit's
    door rows (v3) apart from its deck rows (v1), each flagged as a row that make measures, and the views' decisions
    gathered into the output."""
    calls = []

    def make(inputs, out, seed, params):
        rows = json.loads(pathlib.Path(inputs["inventory"]).read_text())["rows"]
        calls.append({row["id"]: (row["view"], row["ground_box"]) for row in rows})
        for name in ("grounding.json", "decided.json"):
            (out / name).write_text(json.dumps({f"cockpit.{row['id']}": {"passes": True} for row in rows}))
    kept = machine_boxes.make_boxes
    machine_boxes.make_boxes = make
    try:
        with tempfile.TemporaryDirectory() as temporary:
            out = pathlib.Path(temporary)
            boxes.make_boxes({"inventory": REPO / "data/inventory/cockpit.json"}, out, 0, {})
            decided = json.loads((out / "decided.json").read_text())
            assert not list(out.glob("*/.rows.json")), "the flagged rows are the make's input, not its output"
    finally:
        machine_boxes.make_boxes = kept
    assert [sorted({view for view, _ in call.values()}) for call in calls] == [["v1"], ["v3"]], calls
    assert all(flagged for call in calls for _, flagged in call.values())
    assert set(decided) == {f"cockpit.{row['id']}" for row in boxes.other_rows(inventory("cockpit"))}


def an_empty_stage(place):
    from pxr import Usd, UsdGeom
    stage = Usd.Stage.CreateInMemory()
    UsdGeom.Xform.Define(stage, f"/{place}")
    return stage


def test_a_ship_place_names_its_people():
    """Both ways: every ship place's cast record names nobody, with its reason, and the people check passes on it; a
    place with no record answers unknown."""
    for place in SHIP:
        cast = contents.record("characters", place)
        assert cast is not None and cast["people"] == [] and cast["note"], place
        answer, faults, _ = contents.judge_people(an_empty_stage(place), place, inventory(place), {})
        assert answer == contents.PASS and not faults, (place, answer, faults)
    answer, _, why = contents.judge_people(an_empty_stage("nowhere"), "nowhere", {"rows": []}, {})
    assert answer == contents.UNKNOWN and "no cast" in why


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
