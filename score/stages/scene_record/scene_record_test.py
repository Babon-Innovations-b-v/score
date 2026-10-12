"""The scene-record stage on its proof place, the garage: its plan maps (an item with no rows, a door that says
nowhere it leads and a sealed door the layout leaves open each fail `mapped`); its written record passes all four
gates on the accepted made ground; a `from` naming a game script fails `game-free`, a shell a metre wide of the plan fails
`plan-matched`, the north tube taken away fails `openings` (its door's place does not stand in it), and the room fill
taken away fails `seed-matched` (the seed's light is left out with no reason). Skipped, and says so, on a machine
without the round-three seeds or an accepted terrain output.

Run: .venv/bin/python score/stages/scene_record/scene_record_test.py
"""
import copy
import json
import pathlib
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from score import checks  # noqa: E402
from score.stages import scene_record  # noqa: E402
from score.stages.scene_record import gates, plan, writer  # noqa: E402
from score.store import PROPS_HOME, Store  # noqa: E402

PLACE = "garage"
SEEDS = PROPS_HOME / "work"


def inputs_of(files):
    return {name: pathlib.Path(pattern.format(place=PLACE, data=str(REPO / "data"), seeds=str(SEEDS), repo=str(REPO)))
            for name, pattern in files.items()}


def made_plan(folder, change=None):
    """plan@garage made into `folder`, from the garage's plan changed by `change` when given."""
    inputs = inputs_of(plan.files(PLACE))
    if change is not None:
        changed = json.loads(inputs["plan"].read_text())
        change(changed)
        inputs["plan"] = pathlib.Path(folder) / "plan-in.json"
        inputs["plan"].write_text(json.dumps(changed))
    out = pathlib.Path(folder) / "plan"
    out.mkdir()
    plan.make(inputs, out, 0, {})
    assert plan.plan_faults(out) == []
    return out, inputs


def terrain():
    store = Store.default()
    accepted = store.accepted("terrain")
    return store.checkout(accepted) if accepted else None


def written(folder, ground):
    plan_out, _ = made_plan(folder)
    inputs = {**inputs_of(writer.files(PLACE)), "plan": plan_out, "terrain": ground}
    out = pathlib.Path(folder) / "record"
    out.mkdir()
    writer.make(inputs, out, 0, {})
    assert writer.record_faults(out) == []
    return out, inputs


def answer(check, out, inputs):
    found = check.judge(out, inputs, None)
    return found.answer, found


def rewritten(out, change):
    path = next(pathlib.Path(out).glob("record/*.json"))
    record = json.loads(path.read_text())
    change(record)
    path.write_text(json.dumps(record))


def test_the_garage_plan_maps_and_faults_fail():
    assert scene_record.written(PLACE)
    with tempfile.TemporaryDirectory() as folder:
        out, inputs = made_plan(folder)
        found = plan.judge_mapped(out, inputs, None)
        assert found.answer == checks.PASS, (found.reason, found.findings)
        made = json.loads((out / "plan.json").read_text())
        assert [door["leads"] for door in made["doors"]] == ["tube", "sealed", "sealed", "outside"]
    for change, said in ((lambda record: record["rows"].pop("CHARGE POST"), "CHARGE POST"),
                         (lambda record: record["leads"].pop("W"), "door W"),
                         (lambda record: record["leads"].update(N={"to": "sealed", "why": "test"}), "leaves it open")):
        with tempfile.TemporaryDirectory() as folder:
            out, inputs = made_plan(folder, change)
            found = plan.judge_mapped(out, inputs, None)
            assert found.answer == checks.FAIL and said in " ".join(found.findings), (said, found.findings)


def test_the_garage_record_passes_and_each_fault_fails():
    ground = terrain()
    if not (SEEDS / "usd-r3" / PLACE).exists() or ground is None:
        print("skipped: no round-three seeds or no accepted terrain output on this machine")
        return
    with tempfile.TemporaryDirectory() as folder:
        out, inputs = written(folder, ground)
        for check in gates.CHECKS:
            result, found = answer(check, out, inputs)
            assert result == checks.PASS, (check.name, found.reason, found.findings)
        base = json.loads(next(out.glob("record/*.json")).read_text())
        faults = (
            ("game-free", lambda record: record["structure"][0].update({"from": "module_shell.gd:530"})),
            ("plan-matched", lambda record: record["structure"][0].update({"wide": record["structure"][0]["wide"] + 1})),
            ("openings", lambda record: record.update(places=[item for item in record["places"]
                                                              if item["name"] != "north_tube"])),
            ("seed-matched", lambda record: record.update(lights=[])))
        for name, change in faults:
            rewritten(out, lambda record: record.update(copy.deepcopy(base)))
            rewritten(out, change)
            check = next(check for check in gates.CHECKS if check.name == name)
            result, found = answer(check, out, inputs)
            assert result == checks.FAIL, (name, found.reason)


if __name__ == "__main__":
    test_the_garage_plan_maps_and_faults_fail()
    test_the_garage_record_passes_and_each_fault_fails()
    print("scene_record_test: ok")
