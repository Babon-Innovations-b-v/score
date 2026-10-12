"""The resting gate reads the world files the assembly stage declares, never the repository's own: a changed rules
file, kit or inventory in the world's data changes its verdict, and a seed naming no inventory there is unknown.
No spend: a one-piece place made here, a drop run in which nothing moved.

Run: .venv/bin/python score/stages/assembly/assembly_test.py
"""
import json
import pathlib
import shutil
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tools/usd"))

from score import checks  # noqa: E402
from score.stages import assembly  # noqa: E402
import triage_test  # noqa: E402

STILL = {"objects": {}}


def a_seed(root):
    """A place holding one floor plate sunk 40 cm (a kit piece's false alarm under the repository's rules), as the
    stage's output, its inputs record naming the world's inventory."""
    (root / "made").mkdir()
    stage = triage_test.place_of(root / "made", [("plate", "box", (6, -0.4, 0))],
                                 [triage_test.row("plate", group="kit: floor")])
    output = root / "output"
    shutil.copytree(stage.parent, output)
    record = json.loads((output / "inputs.json").read_text())
    (output / "inputs.json").write_text(json.dumps({**record, "inventory": f"data/inventory/{stage.stem}.json"}))
    return output, stage.stem


def world_data(root, place, fixed_in_kit):
    """The world's data the stage declares: rules, kit and inventory, with the rules' kit groups as given."""
    data = root / "data"
    for part in ("checks", "kit", "inventory"):
        (data / part).mkdir(parents=True)
    rules = json.loads((REPO / "data/checks/resting.json").read_text())
    (data / "checks/resting.json").write_text(json.dumps({**rules, "fixed_in_kit": fixed_in_kit}))
    (data / "kit" / f"{place}.json").write_text(json.dumps({"kinds": {}}))
    (data / "inventory" / f"{place}.json").write_text(json.dumps(
        {"rows": [triage_test.row("plate", group="kit: floor")]}))
    return {"resting rules": data / "checks/resting.json", "kit": data / "kit" / f"{place}.json",
            "inventories": data / "inventory"}


def resting(output, inputs):
    evidence = output.parent / "settled.json"
    evidence.write_text(json.dumps(STILL))
    return assembly.judge_resting(output, inputs, evidence)


def test_the_resting_gate_reads_the_declared_world_files():
    """Fault (review of step 0, 2026-10-11): the judge read the repository's resting.json, kit and inventory, so a
    world whose data was elsewhere was judged on files its key did not cover."""
    root = pathlib.Path(tempfile.mkdtemp())
    try:
        output, place = a_seed(root)
        kit_floor = world_data(root / "kept", place, ["kit: floor"])
        assert resting(output, kit_floor).answer == checks.PASS
        no_kit_groups = world_data(root / "changed", place, [])
        verdict = resting(output, no_kit_groups)
        assert verdict.answer == checks.FAIL and "plate" in " ".join(verdict.findings), verdict
        record = json.loads((output / "inputs.json").read_text())
        (output / "inputs.json").chmod(0o644)
        (output / "inputs.json").write_text(json.dumps({**record, "inventory": "/elsewhere/rows.json"}))
        assert resting(output, kit_floor).answer == checks.UNKNOWN
    finally:
        shutil.rmtree(root)


def test_a_baked_model_s_objects_carry_its_hash_and_keep_the_owner_s_pick():
    """Both ways: after the assembly takes a bake, the object carries the baked file's hash (not the seed's, the
    greenhouse's water tank until 2026-10-12) and its pick still holds through `repaint_of`; the same hash written
    without the seed's beside it breaks the pick."""
    import complete
    import picks
    import resting_test
    from pxr import Sdf, Usd
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        resting_test.made_models(folder)
        seed_hash = complete.model_hash(folder / "models/box.gltf")
        pick = {"model": "box", "sha256": seed_hash, "decided": "owner, 2026-10-09: this take"}
        stage = triage_test.place_of(folder, [("crate", "box", (0, 0, 0))], [triage_test.row("crate", pick=pick)])
        inventory = json.loads((folder / "inventory.json").read_text())
        baked = folder / "models/plank.gltf"  # stands for the bake of the box: another file, another hash
        assembly.stamp_baked_hash(stage.parent / assembly.BASE_LAYER, "box", baked)
        opened = Usd.Stage.Open(str(stage))  # held: a prim of a stage nothing holds expires at once
        prim = opened.GetPrimAtPath(f"/{triage_test.PLACE}/Objects/crate_1")
        assert prim.GetAttribute("score:model_sha256").Get() == complete.model_hash(baked)
        assert prim.GetAttribute("score:repaint_of").Get() == seed_hash
        assert picks.check(stage, inventory) == ([], 1)
        layer = Sdf.Layer.FindOrOpen(str(stage.parent / assembly.BASE_LAYER))
        spec = layer.GetPrimAtPath(f"/{triage_test.PLACE}/Objects/crate_1")
        spec.RemoveProperty(spec.attributes["score:repaint_of"])
        layer.Save()
        found, _ = picks.check(stage, inventory)
        assert len(found) == 1 and "not the owner's pick" in found[0]["why"], found


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
