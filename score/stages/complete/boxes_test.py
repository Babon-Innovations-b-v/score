"""The completion gate's evidence on a ship place, both ways (2026-10-15: complete@quarters and complete@walkway
answered unknown on their boxes).

complete-boxes measures every boxed row no other box row measures (a code row, a row taken from another place's take),
view by view, and leaves the rows motion-models-boxes measures to it; it applies to the ship's places only. Who is in a
place is its design's (tools/usd/contents_test.py checks the people check).

Run: .venv/bin/python score/stages/complete/boxes_test.py
"""
import json
import pathlib
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
from score import stages  # noqa: E402
import score.stages.complete.boxes as boxes  # noqa: E402
import score.stages.motion.models.boxes as model_boxes  # noqa: E402


def inventory(place):
    return json.loads((REPO / "data/inventory" / f"{place}.json").read_text())


def test_the_rows_no_other_box_row_measures():
    """Both ways: the cockpit's boxed code rows (its door frame, its deck plates) are measured here, its ground_box
    rows (the pilot seat, flagged ground_box) and its unseen door leaf (box null since 436aefa3) are not; the row
    applies to a ship place and not to an old one."""
    rows = {row["id"] for row in boxes.other_rows(inventory("cockpit"))}
    assert {"ring_floor_plate", "hatch_door_frame"} <= rows and not {"pilot_seat", "door_leaf"} & rows, rows
    row = next(row for row in stages.STAGES if row.name == "complete-boxes")
    assert stages.ship_place("cockpit") and not stages.ship_place("hub")
    with designed(set()):
        assert row.applies("cockpit") and not row.applies("hub")
        assert boxes.files("cockpit")["view v1"] == "{seeds}/scene/cockpit/views/cockpit.png"


def designed(places):
    """prop_data.designed answering for `places` alone while held (the machine's own designs left out)."""
    import contextlib
    import score.stages.props.prop_data as prop_data

    @contextlib.contextmanager
    def held():
        kept = prop_data.designed
        prop_data.designed = lambda place: place in places
        try:
            yield
        finally:
            prop_data.designed = kept
    return held()


def test_a_designed_place_has_no_rows_and_reads_no_old_view():
    """A designed place (its locked concept read into its hand-in, every row boxed there) has no complete-boxes row
    and its files name none of its old inventory's views (the cockpit's, lost with the work folder, 2026-10-21)."""
    row = next(row for row in stages.STAGES if row.name == "complete-boxes")
    with designed({"cockpit"}):
        assert not row.applies("cockpit") and not boxes.has_rows("cockpit")
        assert not [name for name in boxes.files("cockpit") if name.startswith("view ")], boxes.files("cockpit")
        assert row.applies("quarters") or not boxes.other_rows(inventory("quarters"))


def test_the_other_rows_are_measured_as_motion_models_boxes_measures():
    """The cockpit's other rows, on two views (its door rows on v3, its deck rows on v1), go to motion-models-boxes' make
    in one listing, each flagged as a row it measures; the listing is not left in the output."""
    calls = []

    def make(inputs, out, seed, params):
        listed = json.loads(pathlib.Path(inputs["inventory"]).read_text())["rows"]
        calls.append({row["id"]: row["ground_box"] for row in listed})
    kept = model_boxes.make_boxes
    model_boxes.make_boxes = make
    try:
        with tempfile.TemporaryDirectory() as temporary:
            boxes.make_boxes({"inventory": REPO / "data/inventory/cockpit.json"}, pathlib.Path(temporary), 0, {})
            assert not list(pathlib.Path(temporary).iterdir()), "the flagged rows are the make's input, not its output"
    finally:
        model_boxes.make_boxes = kept
    assert len(calls) == 1 and set(calls[0]) == {row["id"] for row in boxes.other_rows(inventory("cockpit"))}
    assert all(calls[0].values()) and "pilot_seat" not in calls[0]


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[3] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
