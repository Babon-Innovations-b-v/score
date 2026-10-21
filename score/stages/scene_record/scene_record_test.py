"""The scene-record stage's plan row on a plan of its own (a small domed shed beside a yard): its plan maps, and an item
with no rows, a door that says nowhere it leads and a sealed door the layout leaves open each fail `mapped`; a written
plan with no corner takes its outline, and one with neither is refused by name.

The tests on the old concepts' places (the garage's, stairwell's and wreck's records over their round-three seeds,
the hub's, tube's, greenhouse's and hangar's shells, the flat's and camp's kits) went with those places' filed plans,
kits and records, retired on 2026-10-21.

Run: .venv/bin/python score/stages/scene_record/scene_record_test.py
"""
import json
import pathlib
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from score import checks  # noqa: E402
from score.stages.scene_record import plan  # noqa: E402

SHED = {"title": "SHED", "w": 8.0, "d": 6.0, "corner": 1.0, "height": "walls 3 m, dome rising 1 m",
        "doors": [["N", 4.0, 1.2, "HATCH N, 1.2 x 2.1 m"], ["S", 4.0, 2.0, "BIG DOOR, 2 x 3 m"]],
        "items": [["BENCH", 1.0, 1.0, 2.0, 0.6, None, "item"], ["DRIVE LANE", 3.0, 3.0, 2.0, 2.0, None, "zone"]],
        "people": [[4.0, 3.0]],
        "leads": {"N": {"to": "yard", "why": "a hatch onto the yard"}, "S": {"to": "outside", "why": "the big door"}},
        "rows": {"BENCH": ["bench"], "DRIVE LANE": []},
        "elements": [{"element": "a bench", "rows": ["bench"]}]}
INVENTORY = {"scene": "shed", "rows": [{"id": "bench", "name": "a bench", "anchor": "floor", "size": [2.0, 0.6, 0.9],
                                        "count": 1}],
             "room": {"layout": {"open": ["north", "south"]}}}


def made(folder, record):
    """plan@shed made into `folder` from `record`, as the table hands it (its kit the plan itself: plan_as_kit)."""
    folder = pathlib.Path(folder)
    plans = folder / "plans"
    plans.mkdir()
    (plans / "yard.json").write_text(json.dumps({"title": "YARD", "w": 20.0, "d": 12.0, "leads": {}}))
    (plans / "shed.json").write_text(json.dumps(record))
    (folder / "inventory.json").write_text(json.dumps(INVENTORY))
    inputs = {"plan": plans / "shed.json", "kit": plans / "shed.json", "plans": plans,
              "inventory": folder / "inventory.json"}
    out = folder / "plan"
    out.mkdir()
    plan.make(inputs, out, 0, {})
    assert plan.plan_faults(out) == []
    return out, inputs


def test_a_plan_maps_and_faults_fail():
    with tempfile.TemporaryDirectory() as folder:
        out, inputs = made(folder, SHED)
        found = plan.judge_mapped(out, inputs, None)
        assert found.answer == checks.PASS, (found.reason, found.findings)
        assert [door["leads"] for door in json.loads((out / "plan.json").read_text())["doors"]] == ["yard", "outside"]
    for change, said in ((lambda record: record["rows"].pop("BENCH"), "BENCH"),
                         (lambda record: record["leads"].pop("S"), "door S"),
                         (lambda record: record["leads"].update(N={"to": "sealed", "why": "test"}), "leaves it open")):
        record = json.loads(json.dumps(SHED))
        change(record)
        with tempfile.TemporaryDirectory() as folder:
            out, inputs = made(folder, record)
            found = plan.judge_mapped(out, inputs, None)
            assert found.answer == checks.FAIL and said in " ".join(found.findings), (said, found.findings)


def test_a_written_plan_with_no_corner_takes_its_outline():
    """A written plan (plan_writing's: an outline, no corner) makes its plan with square corners, its outline drawing
    every corner; a plan with neither is refused by name."""
    record = {key: value for key, value in SHED.items() if key != "corner"}
    with tempfile.TemporaryDirectory() as folder:
        out, _ = made(folder, {**record, "outline": [[0.0, 0.0], [8.0, 0.0], [8.0, 6.0], [0.0, 6.0]]})
        walls = json.loads((out / "plan.json").read_text())["walls"]
        assert walls["corner"] == 0.0 and (walls["wide"], walls["deep"]) == (8.0, 6.0), walls
    with tempfile.TemporaryDirectory() as folder:
        try:
            made(folder, record)
        except ValueError as refused:
            assert "no corner and no outline" in str(refused), refused
        else:
            raise AssertionError("a plan with no corner and no outline was made")


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(REPO / "conftest.py"))["refuse_outside_sandbox"]()
    test_a_plan_maps_and_faults_fail()
    test_a_written_plan_with_no_corner_takes_its_outline()
    print("scene_record_test: ok")
