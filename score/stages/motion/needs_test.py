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


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[3] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
