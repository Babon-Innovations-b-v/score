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


# A written plan (plan_writing's schema): the shed's outline, walls, a door in its north wall to the yard beside it,
# its floor, a flat roof, a stair, a bench and a ceiling lamp; one person spot inside, one outside its walls. Its
# holder (the site) holds it and the yard.
WRITTEN = {**SHED, "outline": [[0.0, 0.0], [8.0, 0.0], [8.0, 6.0], [0.0, 6.0]],
           "walls": [{"from": [0.0, 0.0], "to": [8.0, 0.0], "thick": 0.2, "tall": 3.0},
                     {"from": [8.0, 0.0], "to": [8.0, 6.0], "thick": 0.2, "tall": 3.0},
                     {"from": [8.0, 6.0], "to": [0.0, 6.0], "thick": 0.2, "tall": 3.0},
                     {"from": [0.0, 6.0], "to": [0.0, 0.0], "thick": 0.2, "tall": 3.0}],
           "openings": [{"kind": "door", "at": [4.0, 0.0], "wide": 1.2, "angle": 0.0, "swing": "slide", "sill": 0.0,
                         "head": 2.1, "to": "yard"}],
           "levels": [{"name": "floor", "height": 0.0, "points": [[0.0, 0.0], [8.0, 0.0], [8.0, 6.0], [0.0, 6.0]]}],
           "roofs": [{"kind": "flat", "points": [[0.0, 0.0], [8.0, 0.0], [8.0, 6.0], [0.0, 6.0]], "eave": 3.0,
                      "top": 3.0}],
           "stairs": [{"kind": "stair", "points": [[6.0, 4.0], [7.0, 4.0], [7.0, 6.0], [6.0, 6.0]], "from": 0.0,
                       "to": 1.0, "angle": 90.0, "steps": 5}],
           "items": [*SHED["items"], ["LAMP", 3.5, 2.5, 1.0, 1.0, None, "item"]],
           "rows": {**SHED["rows"], "LAMP": ["ceiling_lamp"]},
           "shapes": {"LAMP": {"shape": "rect", "tall": 0.2, "base": 2.7}},
           "people": [[4.0, 3.0, None, None], [20.0, 3.0, None, None]], "terrain": {}}
LAMP_ROW = {"id": "ceiling_lamp", "name": "ceiling lamp", "noun": "lamp", "anchor": "ceiling", "size": [1.0, 1.0, 0.2],
            "count": 1}
SITE = {"title": "SITE", "w": 40.0, "d": 20.0, "leads": {},
        "holds": [{"place": "shed", "row": "shed", "x": 2.0, "y": 2.0, "w": 8.0, "d": 6.0},
                  {"place": "yard", "row": "yard", "x": 12.0, "y": 2.0, "w": 20.0, "d": 12.0}]}
# The base's site at its scene time (data/physics/setting.json): the Sun stands over its horizon then.
SKY = {"site": {"on": "moon", "latitude": 55.0, "longitude": 0.0, "height_m": 0.0}, "time": "2099-10-01T14:00:00Z"}


def written(folder, design):
    """scene-record@shed written into `folder` from its design `design`: (the record's output, the writer's inputs)."""
    from score.review import setting
    from score.stages.scene_record import writer
    folder = pathlib.Path(folder)
    out, inputs = made(folder, design)
    (folder / "plans/site.json").write_text(json.dumps(SITE))
    (folder / "inventory.json").write_text(json.dumps({**INVENTORY, "rows": [*INVENTORY["rows"], LAMP_ROW]}))
    (folder / "sky.json").write_text(json.dumps({**SKY, "place": "shed", "top": "site", "setting": setting.now()}))
    inputs = {**inputs, "plan": out, "sky": folder / "sky.json", "row kinds": REPO / "data/checks/row-kinds.json",
              "lamp library": REPO / "data/library/lamps.json", "places": REPO / "data/definitions/place.json"}
    record = folder / "record"
    record.mkdir()
    writer.make(inputs, record, 0, {})
    assert writer.record_faults(record) == []
    return record, inputs


def test_the_record_is_written_from_the_design():
    """The shed's record holds its shell with the north door cut, its stair, a light over its lamp, its sky from the
    physics, the yard its door leads to where the site holds it, and only the view standing inside its walls; its
    gates pass, and a door filled, a lamp moved off its item and a door to no place each fail by name."""
    from score.review import overhead
    from score.stages.scene_record import gates, writer
    with tempfile.TemporaryDirectory() as folder:
        output, inputs = written(folder, WRITTEN)
        place, record = writer.record_in(output)
        names = {entry["name"] for entry in record["structure"]}
        assert place == "shed" and record["inside"] and {"wall_1", "deck_1", "roof_1", "stair_1"} <= names, names
        assert len([name for name in names if name.startswith("wall_1")]) == 4, names  # cut round the door
        [lamp] = record["lights"]
        assert lamp["at"] == [0.0, 2.71, 0.0] and "ceiling_lamp" in lamp["from"], lamp  # 5% up the fitting
        seen = overhead.seen(json.loads((pathlib.Path(folder) / "sky.json").read_text())["setting"], SKY["site"],
                             SKY["time"])
        sun = next(light for light in seen["lights"] if light["name"] == "Sun")
        [up] = record["environment"]["sky"]["lights"]
        assert up["name"] == "Sun" and up["altitude"] == sun["altitude"] > 0, (up, sun)
        [yard] = record["places"]
        assert yard["name"] == "yard" and yard["at"] == [16.0, 0.0, 3.0] and yard["rotation"] == [0, 0, 0, 1], yard
        assert [view["name"] for view in record["views"]] == ["from-door-1", "spot-1"], record["views"]
        assert [view["name"] for view in record["views_left_out"]] == ["spot-2"], record["views_left_out"]
        assert record["ceiling"] == 3.0, record
        for check in gates.CHECKS:
            verdict = check.judge(output, inputs, {})
            assert verdict.answer == checks.PASS, (verdict.check, verdict.reason, verdict.findings)
        path = output / "record/shed.json"
        filled = {**record, "structure": record["structure"] + [
            {"name": "plug", "builder": "slab", "points": [[-0.8, -3.5], [0.8, -3.5], [0.8, -3.0], [-0.8, -3.0]],
             "low": 0.0, "high": 3.0}]}
        path.write_text(json.dumps(filled))
        verdict = gates.judge_plan_matched(output, inputs, {})
        assert verdict.answer == checks.FAIL and "filled by ['plug']" in " ".join(verdict.findings), verdict.findings
        path.write_text(json.dumps({**record, "lights": [{**lamp, "at": [3.0, 2.7, 0.0]}]}))
        verdict = gates.judge_plan_matched(output, inputs, {})
        assert verdict.answer == checks.FAIL and "'LAMP' stands off" in " ".join(verdict.findings), verdict.findings
    nowhere = json.loads(json.dumps(WRITTEN))
    nowhere["openings"][0]["to"] = "moon_city"
    with tempfile.TemporaryDirectory() as folder:
        output, inputs = written(folder, nowhere)
        verdict = gates.judge_openings(output, inputs, {})
        assert verdict.answer == checks.FAIL and "'moon_city'" in " ".join(verdict.findings), verdict.findings


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(REPO / "conftest.py"))["refuse_outside_sandbox"]()
    test_a_plan_maps_and_faults_fail()
    test_a_written_plan_with_no_corner_takes_its_outline()
    test_the_record_is_written_from_the_design()
    print("scene_record_test: ok")
