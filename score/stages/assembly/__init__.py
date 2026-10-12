"""The assembly stage (P5), as step 0 wires it: a place's round-three OpenUSD stage brought in as an unverified seed,
then judged by the assembly gates that exist today. No spend: nothing is made, rendered or settled.

    make     copies the seed's stage (<place>.usda, layers/, assets/, inputs.json) into the output with origin.json
             saying where it came from; old check results and manifests beside it are agent verdicts and stay out.
             A place on a made ground (the terrain stage's places/<place>.usdc) takes it as layers/ground.usdc,
             sublayered over the seed's base, so the made ground stands in for the old one (experimental, PRD #6).
             A place the effects stage made a layer for (experimental) takes it in place of the seed's own:
             layers/effects.usda and its baked clips, held by the root between the edit layer and the base
    gates    placeholders  tools/usd/placeholders.py: nothing visible stands in for a made piece (the hangar's
                           code-built ship fails, 12 meshes)
             resting       tools/usd/triage.py on a drop run made on this very output (settle.py --dry-run's
                           settled.json, stored as the check's evidence); with none it answers unknown and blocks,
                           and the runner's drive gathers it (gather_drop_run: one drop run on a rented processor
                           machine, cleared at DROP_EUROS) when nothing else blocks the output

The stage that builds a place from its accepted layout replaces the seed maker in step 3; the gates stay. Both judges
read only the world files the stage declares (FILES): the resting judge reads the rules, the place's kit and the
inventory the seed's inputs.json names, found in the declared inventory folder (the whole folder is therefore an
input, so any inventory change makes these nodes run again); a seed naming no inventory there answers unknown.
"""
import json
import pathlib
import shutil
import sys

from score import checks

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tools/usd"))
import placeholders  # noqa: E402
import triage  # noqa: E402

FILES = {"seed": "{seeds}/usd-r3/{place}", "kit": "{data}/kit/{place}.json",
         "fittings": "{data}/library/fittings.json", "resting rules": "{data}/checks/resting.json",
         "inventories": "{data}/inventory"}
SEED_PARTS = ("layers", "assets", "inputs.json")
GROUND_LAYER = "layers/ground.usdc"
EFFECTS_LAYER = "layers/effects.usda"
EFFECTS_CLIPS = "assets/effects"
BASE_LAYER = "./layers/base.usda"
INVENTORY_PREFIX = "data/inventory/"
# One drop run's estimate: a quarter to three quarters of an hour on a rented processor machine (the ledger's settle
# runs of 2026-10-10 cost EUR 0 to 0.85).
DROP_EUROS = 1.0
SEED_NOTE = ("An old output brought in from world 1's round-three stages, never made by this stage; only its gates "
             "on this page judge it.")


def make_from_seed(inputs, out, seed, params):
    """Copy a seed stage's own files into the output, with its origin."""
    folder = inputs["seed"]
    root = folder / f"{folder.name}.usda"
    shutil.copy2(root, out / root.name)
    for part in SEED_PARTS:
        source = folder / part
        if source.is_dir():
            shutil.copytree(source, out / part)
        elif source.exists():
            shutil.copy2(source, out / part)
    (out / "origin.json").write_text(json.dumps({"seed": True, "from": str(folder), "note": SEED_NOTE}, indent=1))
    if "effects-layer" in inputs:
        take_effects(inputs["effects-layer"], out / root.name)
    take_ground(inputs["terrain"], folder.name, out / root.name)


def take_effects(made, root):
    """The effects stage's layer and its baked clips in place of the seed's, held by the root just over the base."""
    from pxr import Sdf
    shutil.rmtree(root.parent / EFFECTS_CLIPS, ignore_errors=True)
    shutil.copytree(pathlib.Path(made) / EFFECTS_CLIPS, root.parent / EFFECTS_CLIPS)
    shutil.copy2(pathlib.Path(made) / EFFECTS_LAYER, root.parent / EFFECTS_LAYER)
    layer = Sdf.Layer.FindOrOpen(str(root))
    layers = list(layer.subLayerPaths)
    if f"./{EFFECTS_LAYER}" not in layers:
        layers.insert(layers.index(BASE_LAYER), f"./{EFFECTS_LAYER}")
        layer.subLayerPaths = layers
        layer.Save()


def take_ground(grounds, place, root):
    """The place's made ground, when the terrain stage made one for it, sublayered just over the seed's base."""
    made = sorted(pathlib.Path(grounds).glob(f"*/places/{place}.usdc"))
    if not made:
        return
    from pxr import Sdf
    shutil.copy2(made[0], root.parent / GROUND_LAYER)
    layer = Sdf.Layer.FindOrOpen(str(root))
    layers = list(layer.subLayerPaths)
    layers.insert(layers.index(BASE_LAYER), f"./{GROUND_LAYER}")
    layer.subLayerPaths = layers
    layer.Save()


def stage_file(output):
    """The output's root OpenUSD file."""
    found = list(output.glob("*.usda"))
    if len(found) != 1:
        raise FileNotFoundError(f"{output} holds {len(found)} root stages, not one")
    return found[0]


def judge_placeholders(output, inputs, evidence):
    """Fail on every visible mesh that stands in for a made piece."""
    faults = placeholders.check(stage_file(output), kits=inputs["kit"].parent)
    findings = tuple(f"{fault['prim']}: {fault['rule']}: {fault['why']}" for fault in faults)
    reason = f"{len(faults)} meshes stand in for made pieces" if faults else "nothing stands in for a made piece"
    return checks.Verdict("placeholders", checks.FAIL if faults else checks.PASS, reason, {"faults": len(faults)},
                          {"faults": "lower"}, findings)


def declared_inventory(output, inventories):
    """The inventory the seed was laid from (its inputs.json), in the world's declared inventory folder; None when it
    names none there."""
    record = output / "inputs.json"
    named = json.loads(record.read_text()).get("inventory", "") if record.exists() else ""
    if not named.startswith(INVENTORY_PREFIX):
        return None
    return pathlib.Path(inventories) / named.removeprefix(INVENTORY_PREFIX)


def judge_resting(output, inputs, evidence):
    """Fail on every real resting fault the drop run and the triage leave, judged on the world files the stage
    declares (rules, kit, inventory) and never on the repository's own."""
    inventory = declared_inventory(output, inputs["inventories"])
    if inventory is None or not inventory.exists():
        return checks.Verdict("resting", checks.UNKNOWN, "the seed names no inventory in the world's inventory "
                              f"folder ({inventory or 'none named'}), so what holds each object up is not known")
    found = triage.triage(stage_file(output), json.loads(pathlib.Path(evidence).read_text()),
                          rules_file=inputs["resting rules"], kit_file=inputs["kit"], inventory_file=inventory)
    real = [fault for fault in found["faults"] if fault["real"]]
    findings = tuple(f"{fault['object']}: {fault['kind']} {fault['measure']}: {fault['why']}" for fault in real)
    reason = (f"{found['real_objects']} objects with real resting faults, {found['false_objects']} false alarms "
              "after the drop run")
    return checks.Verdict("resting", checks.FAIL if real else checks.PASS, reason,
                          {"real faults": len(real), "objects": found["real_objects"]},
                          {"real faults": "lower", "objects": "lower"}, findings)


def gather_drop_run(output, inputs, folder):
    """The drop run on this very output, as settle.py --dry-run --cloud makes it but on the inventory the seed names
    in the declared folder: every loose object dropped in headless Blender on a rented processor machine; its
    settled.json in `folder`."""
    import settle
    from pxr import Usd
    inventory_path = declared_inventory(output, inputs["inventories"])
    if inventory_path is None or not inventory_path.exists():
        raise FileNotFoundError(f"{output.name}: the seed names no inventory in the world's inventory folder "
                                f"({inventory_path or 'none named'}), so nothing can be dropped")
    stage_path = stage_file(output)
    stage = Usd.Stage.Open(str(stage_path))
    place = stage.GetDefaultPrim().GetName()
    inventory = json.loads(inventory_path.read_text())
    loose = settle.loose_objects(stage, place, inventory)
    ignore = (settle.part_objects(stage, place, inventory) + settle.held_on_loose(stage, place, inventory, loose)
              + settle.fixtures_on_loose(stage, place, loose))
    settle.simulate(stage_path, loose, folder, cloud=True, ignore=ignore)
    return folder / "settled.json"


CHECKS = (checks.Check("placeholders", judge_placeholders),
          checks.Check("resting", judge_resting, evidence="a drop run (settle.py --dry-run)"))
GATHERERS = {"resting": (gather_drop_run, DROP_EUROS)}
