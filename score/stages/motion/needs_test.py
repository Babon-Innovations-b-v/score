"""The motion layer's gaps (needs.py) on data made here: a row of a moving kind with nothing moving it is a gap until
a move or a still reason is written, and a place's motion need is a gap until a motion is named for it.

Run: .venv/bin/python score/stages/motion/needs_test.py
"""
import json
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))

from score.stages.motion import needs  # noqa: E402

PLACE = "toy"


def write(data, name, record):
    path = pathlib.Path(data) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record))


def test_a_moving_row_and_a_need_are_gaps_until_a_record_answers_them():
    with tempfile.TemporaryDirectory() as data:
        write(data, "checks/motion.json", {"kinds": {"hatch": {"prims": ["hatch_door"]}}})
        write(data, f"inventory/{PLACE}.json", {"rows": [{"id": "hatch_door"}, {"id": "crate"}]})
        write(data, "checks/contents.json", {"places": {PLACE: {"motion": ["fan"]}}})
        found = {gap["id"] for gap in needs.gaps(PLACE, data)}
        assert found == {"motion:move:hatch_door", "motion:need:fan"}, found
        write(data, f"motion/rigid/{PLACE}.json", {"moves": [
            {"name": "fan_spin", "prim": f"/{PLACE}/Fixtures/fan_1", "spin": {"speed": 90}}],
            "still": {f"/{PLACE}/Objects/hatch_door_1": "shut while nobody passes"}})
        assert needs.gaps(PLACE, data) == [], needs.gaps(PLACE, data)
        write(data, f"motion/rigid/{PLACE}.json", {"moves": [], "still": {"hatch_door_1": " "}})
        found = {gap["id"]: gap for gap in needs.gaps(PLACE, data)}
        assert set(found) == {"motion:move:hatch_door", "motion:need:fan"}, "a still with no reason answers nothing"
        assert found["motion:move:hatch_door"]["node"] is None and "data/motion/rigid/toy.json" in \
            found["motion:move:hatch_door"]["work"]


def test_a_designed_place_s_records_of_its_old_concept_are_gaps_and_their_rows_do_not_run():
    """The garage's models record names its old take and the greenhouse's crop data its old view K09 (both lost with
    the old disk, 2026-10-19): once each place is designed, the rows reading them do not apply and each record is a
    named gap; concept_people reads each designed place's picked concept."""
    import score.stages.concept_people as concept_people
    import score.stages.crops.crop_data as crop_data
    import score.stages.motion.models as models
    import score.stages.props.prop_data as prop_data
    kept = prop_data.DESIGN
    with tempfile.TemporaryDirectory() as design:
        prop_data.DESIGN = pathlib.Path(design)
        try:
            assert models.applies("garage") and crop_data.applies("greenhouse") and not needs.old_records("garage")
            for place in ("garage", "greenhouse", "flat"):
                (prop_data.DESIGN / f"{place}.json").write_text(json.dumps({"objects": {"rover": {"take": "new"}}}))
            assert not models.applies("garage") and models.old_takes("garage") == ["kit5-rover-3"]
            assert not crop_data.applies("greenhouse")
            assert [gap["item"] for gap in needs.old_records("garage")] == ["models:kit5-rover-3"]
            assert [gap["item"] for gap in needs.old_records("greenhouse")] == ["crops"]
            views = concept_people.designed_views(concept_people.REPO / "data/inventory")
            assert views["prologue_flat"] == {"concept": "{home}/design/concepts/flat.png"}, views
        finally:
            prop_data.DESIGN = kept


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[3] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
