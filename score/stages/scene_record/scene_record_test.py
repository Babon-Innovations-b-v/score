"""The scene-record stage on its proof places, the garage (a domed room) and the stairwell (a kit shell): the
garage's plan maps (an item with no rows, a door that says nowhere it leads and a sealed door the layout leaves open
each fail `mapped`); its written record passes all four gates on the accepted made ground; a `from` naming a game
script fails `game-free`, a shell a metre wide of the plan fails `plan-matched`, the north tube taken away fails
`openings` (its door's place does not stand in it), and the room fill taken away fails `seed-matched` (the seed's light
is left out with no reason). The stairwell's record passes all four too; its block a metre off the plan's fails
`plan-matched`, the flat taken away fails `openings` (the front door's place), and its landing lights taken away fail
`seed-matched`; a plan door moved off the kit's doorway fails `plan-matched`. The wreck (an outdoor place) passes all
five (its viewers standing on the made ground); its break lamp's light taken away fails `plan-matched` and the Earth
taken away fails `seed-matched`. Skipped, and says so, on a machine
without the round-three seeds or an accepted terrain output. The hub's facets, the walkway tube and the greenhouse's
glass dome and plot and the hangar's flat roof each match their plan, and a shell number moved a metre fails
`plan-matched`.

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


def inputs_of(files, place=PLACE):
    return {name: pathlib.Path(pattern.format(place=place, data=str(REPO / "data"), seeds=str(SEEDS), repo=str(REPO)))
            for name, pattern in files.items()}


def made_plan(folder, change=None, place=PLACE):
    """plan@<place> made into `folder`, from the place's plan changed by `change` when given."""
    inputs = inputs_of(plan.files(place), place)
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


def written(folder, ground, place=PLACE, change=None):
    plan_out, _ = made_plan(folder, change, place)
    inputs = {**inputs_of(writer.files(place), place), "plan": plan_out, "terrain": ground}
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


def moved_door(record):
    record["doors"][0][1] += 0.5


def test_a_kit_shell_record_passes_and_each_fault_fails():
    ground = terrain()
    if not (SEEDS / "usd-r3" / "stairwell").exists() or ground is None:
        print("skipped: no round-three seeds or no accepted terrain output on this machine")
        return
    with tempfile.TemporaryDirectory() as folder:
        out, inputs = written(folder, ground, "stairwell")
        for check in gates.CHECKS:
            result, found = answer(check, out, inputs)
            assert result == checks.PASS, (check.name, found.reason, found.findings)
        base = json.loads(next(out.glob("record/*.json")).read_text())
        faults = (
            ("plan-matched", lambda record: record["structure"][0].update(
                {"centre": [record["structure"][0]["centre"][0] + 1.0, *record["structure"][0]["centre"][1:]]})),
            ("openings", lambda record: record.update(places=[item for item in record["places"]
                                                              if item["name"] != "flat"])),
            ("seed-matched", lambda record: record.update(lights=[light for light in record["lights"]
                                                                  if light["type"] == "sun"])))
        for name, change in faults:
            rewritten(out, lambda record: record.update(copy.deepcopy(base)))
            rewritten(out, change)
            check = next(check for check in gates.CHECKS if check.name == name)
            result, found = answer(check, out, inputs)
            assert result == checks.FAIL, (name, found.reason)
    with tempfile.TemporaryDirectory() as folder:
        out, inputs = written(folder, ground, "stairwell", moved_door)
        result, found = answer(next(check for check in gates.CHECKS if check.name == "plan-matched"), out, inputs)
        assert result == checks.FAIL and "doorway" in found.reason, found.reason


def test_an_outdoor_record_passes_and_each_fault_fails():
    ground = terrain()
    if not (SEEDS / "usd-r3" / "wreck").exists() or ground is None:
        print("skipped: no round-three seeds or no accepted terrain output on this machine")
        return
    with tempfile.TemporaryDirectory() as folder:
        out, inputs = written(folder, ground, "wreck")
        mapped = plan.judge_mapped(inputs["plan"], inputs_of(plan.files("wreck"), "wreck"), None)
        assert mapped.answer == checks.PASS, (mapped.reason, mapped.findings)
        for check in gates.CHECKS:
            result, found = answer(check, out, inputs)
            assert result == checks.PASS, (check.name, found.reason, found.findings)
        base = json.loads(next(out.glob("record/*.json")).read_text())
        faults = (
            ("plan-matched", lambda record: record.update(lights=[light for light in record["lights"]
                                                                  if light["type"] != "omni"])),
            ("seed-matched", lambda record: record.update(structure=[])))
        for name, change in faults:
            rewritten(out, lambda record: record.update(copy.deepcopy(base)))
            rewritten(out, change)
            check = next(check for check in gates.CHECKS if check.name == name)
            result, found = answer(check, out, inputs)
            assert result == checks.FAIL, (name, found.reason)


def shell_faults_of(made, structure):
    """The plan-matched gate's shell faults for a shell written from `made` (the plan record)."""
    record = {"structure": structure, "floor": made["floor"]}
    shape = made["walls"].get("shape")
    roof = gates.roof_faults(record, made["walls"]) if shape == "flat" else []
    return gates.facet_faults(record, made) if shape == "faceted" else gates.tube_faults(record, made) \
        if shape == "tube" else gates.shell_faults(record, made["walls"]) + gates.door_faults(record, made) + roof


def test_every_shell_kind_matches_its_plan_and_a_moved_number_fails():
    """The faceted hub, the walkway tube, the glass-domed greenhouse (with its plot) and the flat-roofed hangar: each
    plan maps, its shell matches it, and a shell number moved a metre (the hangar's west roof slab a metre over its
    door opening) fails plan-matched."""
    for place, name, key in (("hub", "shell_walls", "apothem"), ("tube", "hull_crown", "radius"),
                             ("greenhouse", "dome_glass", "rise"), ("hangar", "roof_slab_west", "centre")):
        with tempfile.TemporaryDirectory() as folder:
            out, inputs = made_plan(folder, place=place)
            found = plan.judge_mapped(out, inputs, None)
            assert found.answer == checks.PASS, (place, found.reason)
            made = json.loads((out / "plan.json").read_text())
            structure = writer.shell(made) + writer.plots(made)
            assert shell_faults_of(made, structure) == [], (place, shell_faults_of(made, structure))
            moved = copy.deepcopy(structure)
            item = next(item for item in moved if item["name"] == name)
            if isinstance(item[key], list):
                item[key][0] += 1.0
            else:
                item[key] += 1.0
            assert shell_faults_of(made, moved), (place, name, key)


def test_a_moved_leaf_runs_clear_only_its_open_way():
    """The flat's balcony leaf slid open south runs clear; slid north it runs into the TV and its cabinet."""
    kit = json.loads((REPO / "data/kit/flat.json").read_text())
    assert gates.sweep_faults({"moved": [{"node": "BalconyDoor", "by": [0.0, 0.0, 1.4]}]}, kit) == []
    found = gates.sweep_faults({"moved": [{"node": "BalconyDoor", "by": [0.0, 0.0, -1.4]}]}, kit)
    assert any("crt_tv" in line for line in found), found


def test_an_object_carries_its_kit_models_children_and_a_dropped_child_fails():
    """The camp's stores rack carries the eight cases its kit model stands on it; a rack without them leaves the
    seed's cases unmatched with no reason (seed-matched fails them by name), and a removed row's children stay off."""
    kit = json.loads((REPO / "data/kit/camp.json").read_text())
    rows = {row["id"] for row in json.loads((REPO / "data/inventory/camp.json").read_text())["rows"]}
    rack = {"name": "StoresRack", "model": "models/camp_kit/stores_rack_1.gltf", "at": [-1.028, 0.0, -3.429]}
    children = writer.kit_children(rack, kit, rows, set(), "camp")
    assert [child["model"] for child in children] == ["models/camp_kit/case_1.gltf"] * 8, children
    assert {child["row"] for child in children} == {"case"}
    desk = writer.kit_children({"model": "models/camp_kit/comms_desk_1.gltf"}, kit, rows, set(), "camp")
    assert sum(child["model"].endswith("monitor_1_glow.gltf") for child in desk) == 2, desk
    assert writer.kit_children(rack, kit, rows, {"case"}, "camp") == []
    seed = next(entry for entry in json.loads((REPO / "data/scene/camp.json").read_text())["objects"]
                if entry["name"] == "StoresRack")
    assert gates.children_left("objects/StoresRack", seed, {**rack, "children": children}) == []
    assert len(gates.children_left("objects/StoresRack", seed, rack)) == 8


if __name__ == "__main__":
    test_an_object_carries_its_kit_models_children_and_a_dropped_child_fails()
    test_a_moved_leaf_runs_clear_only_its_open_way()
    test_every_shell_kind_matches_its_plan_and_a_moved_number_fails()
    test_the_garage_plan_maps_and_faults_fail()
    test_the_garage_record_passes_and_each_fault_fails()
    test_a_kit_shell_record_passes_and_each_fault_fails()
    test_an_outdoor_record_passes_and_each_fault_fails()
    print("scene_record_test: ok")
