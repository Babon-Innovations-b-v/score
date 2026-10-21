"""The assembly stage (P5): a place's single, final assembly. Its round-three OpenUSD stage comes in as an unverified
seed, and every layer stage's accepted output the node reads takes the place of the seed's part, so each place is
assembled once its layers have landed. No spend: nothing is rendered or settled here.

    make     copies the seed's stage (<place>.usda, layers/, assets/, inputs.json) into the output; old check results
             and manifests beside it are agent verdicts and stay out. Then, each from its accepted output:
             record   the scene-record row's record (experimental) written over the base's old record prims
                      (RECORD_ROOTS) with tools/usd/scene.py's writer, its room shell drawn with the place's library
                      tiles (surface-tiles) where it has them; a place without the row keeps the seed's
                      record, said unverified; an entry marked `waiting` lays nothing and is named on the root prim
                      (score:waiting) for complete. The record built from is written beside the stage (scene.json), the
                      one the neighbours stage reads
             layers   each layer stage of LAYERS the table holds (effects, motion, light, motion models, crops, settle,
                      characters, the kit's shell sections; all experimental) as a sublayer of its own with its
                      assets, in place of the seed's of that name,
                      the root's sublayers in ORDER and its time range as long as the longest layer's
             bakes    a place's baked models (surfaces-bake) in place of the seed's assets, each laid object stamped
                      with the baked file's hash and the seed's as the model it repainted (stamp_baked_hash); a
                      record entry waiting on its model whose row the bake made is laid with it (made_waiting.py)
             ground   the terrain stage's places/<place>.usdc as layers/ground.usdc, just over the base
             sound    the sound row's output (experimental) written as layers/sound.usda (sounds.py), in place of the
                      seed's
             origin.json says the seed it came from, the record, every layer output taken and any sound placed
             nowhere.
    gates    layers        unknown while a layer the place's design shows (needed_layers: its locked concept's
                           scene inventory, the `design` file, by design_layers, the stage table's own answer) has no
                           accepted output taken, never the seed's in its place, and for a place with no design;
                           fail on a sound placed nowhere
             placeholders  tools/usd/placeholders.py: nothing visible stands in for a made piece (the hangar's
                           code-built ship fails, 12 meshes)
             collision     tools/usd/colliders.py: every wall, floor, stair and ground (a gprim of kind structure or
                           ground) collides, and every model (a prim naming its score:model) has a collider of its
                           own; free. Static colliders only: mass and interaction are the named gap
             resting       tools/usd/triage.py on a drop run made on this very output (settle.py --dry-run's
                           settled.json, stored as the check's evidence); with none it answers unknown and blocks,
                           and the runner's drive gathers it (gather_drop_run: one drop run on a rented processor
                           machine, cleared at DROP_EUROS) when nothing else blocks the output

The judges read only the world files the stage declares (files): the resting judge reads the rules, the place's kit
and the inventory the seed's inputs.json names, found in the declared inventory folder (the whole folder is therefore
an input, so any inventory change makes these nodes run again); a seed naming no inventory there answers unknown.
"""
import json
import pathlib
import shutil
import sys

from score import checks
from score.stages import design_layers
from score.stages.assembly import made_waiting, sounds
from score.stages.assembly.baked import (  # noqa: F401  (the table and the tests read them here)
    BOX_TOLERANCE, claimed_bakes, claiming_places, lay_fixtures_baked, renamed_model, stamp_baked_hash, take_bake)
from score.stages.assembly.record import (  # noqa: F401  (motion and light call take_record)
    BASE_LAYER, GROUND_LAYER, ORDER, RECORD, RECORD_ROOTS, WAITING, hold, laid_pieces, take_ground, take_record,
    without_waiting)

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tools/usd"))
import colliders  # noqa: E402
import placeholders  # noqa: E402
import triage  # noqa: E402

FILES = {"seed": "{seeds}/usd-r3/{place}", "kit": "{data}/kit/{place}.json",
         "resting rules": "{data}/checks/resting.json",
         "inventories": "{data}/inventory", "library": "{data}/library", "sounds": "{data}/sound/surfaces.json",
         "places": "{data}/definitions/place.json", "tokens": "{repo}/design/tokens/tokens.json",
         "row kinds": "{data}/checks/row-kinds.json",
         "grounds": "{data}/ground"}


def files(place):
    """FILES, the place's surface data (its design's, else data/surfaces': surfaces/surface_data.pattern's rule, read
    here so the surface package stays out of this code version) and its design (its locked concept's scene
    inventory, design_layers.PATTERN) where it has one: the layers gate reads which layers it needs from it."""
    designed = (design_layers.KEPT.parent / "surfaces" / f"{place}.json").is_file()
    surfaces = ("{home}/design/surfaces/" if designed else "{data}/surfaces/") + f"{place}.json"
    design = {"design": design_layers.PATTERN} if (design_layers.KEPT / f"{place}.json").is_file() else {}
    return {**FILES, "surfaces": surfaces, **design}


SEED_PARTS = ("layers", "assets", "inputs.json")
# The layer stages the assembly takes, each a sublayer of the root of its own: {stage: ((schema, version) read, its
# layer file, its assets folder or None)}. A stage joins the assembly's reads the day it joins the stage table
# (score/stages.layered): the motion, light and crops rows land after this table.
LAYERS = {"effects-layer": (("effects-layer", 1), "layers/effects.usda", "assets/effects"),
          "motion": (("motion-layer", 2), "layers/motion.usda", None),
          "light": (("light", 1), "layers/light.usda", "assets/light"),
          "crops-layer": (("crops-layer", 1), "layers/crops.usda", "assets"),
          "settle": (("settle-layer", 1), "layers/settle.usda", None),
          "characters-layer": (("characters-layer", 1), "layers/characters.usda", "assets/characters"),
          "kit-sections": (("kit-sections", 1), "layers/sections.usda", None)}
# Every stage the assembly reads for the place's own layers (the bakes and the ground are read in the table).
READS = {"scene-record": ("scene-record", 1), "sound": ("sound-layer", 1), "surface-tiles": ("surface-tiles", 1),
         **{name: wanted for name, (wanted, _, _) in LAYERS.items()}}
# The layer stage the assembly takes for each layer kind a design shows (design_layers; the physics' settle layer).
NEEDS = {"people": "characters-layer", "crops": "crops-layer", "effects": "effects-layer", "motion": "motion",
         "physics": "settle", "light": "light", "sound": "sound"}
INVENTORY_PREFIX = "data/inventory/"
# One drop run's estimate: a quarter to three quarters of an hour on a rented processor machine (the ledger's settle
# runs of 2026-10-10 cost EUR 0 to 0.85).
DROP_EUROS = 1.0
SEED_NOTE = ("An old output brought in from world 1's round-three stages, never made by this stage; only its gates "
             "on this page judge it.")


def make_from_seed(inputs, out, seed, params):
    """Copy a seed stage's own files into the output, then take every accepted layer the node reads in place of the
    seed's part (the record's prims, each layer stage's sublayer, the bakes, the ground, the sounds), and write what
    it took into origin.json."""
    folder = inputs["seed"]
    root = folder / f"{folder.name}.usda"
    shutil.copy2(root, out / root.name)
    for part in SEED_PARTS:
        source = folder / part
        if source.is_dir():
            shutil.copytree(source, out / part)
        elif source.exists():
            shutil.copy2(source, out / part)
    record = take_record(inputs, out, folder.name)
    for name, (_, layer, assets) in LAYERS.items():
        if name in inputs:
            take_layer(pathlib.Path(inputs[name]), out / root.name, layer, assets)
    if "surfaces-bake" in inputs:
        bake = pathlib.Path(inputs["surfaces-bake"])
        take_bake(bake, pathlib.Path(inputs["surfaces-paint"]), out)
        for row in made_waiting.lay(out, folder.name, bake):
            stamp_baked_hash(out / BASE_LAYER, row, bake / "made" / f"{row}.gltf")
    for claimed in claimed_bakes(inputs, out):
        take_bake(*claimed)
    take_ground(inputs["terrain"], folder.name, out / root.name)
    unplaced = sounds.take(pathlib.Path(inputs["sound"]), out / root.name, inputs) if "sound" in inputs else []
    motion_over_light(out / root.name)  # last: no hold after it sorts its layer under the light's
    taken = {name: pathlib.Path(inputs[name]).name for name in READS if name in inputs}
    (out / "origin.json").write_text(json.dumps({"seed": True, "from": str(folder), "note": SEED_NOTE,
                                                 "record": record, "layers": taken, "unplaced sounds": unplaced},
                                                indent=1))


def take_layer(made, root, layer, assets):
    """A layer stage's layer in place of the seed's (or beside it), with its assets when its output has any (the
    light stage's live lamps have none): a folder of its own replaced whole, the seed's gone with none, the shared
    assets/ merged. The root holds it in its place (hold) and plays as long as it does."""
    from pxr import Sdf
    if assets and assets != "assets":
        shutil.rmtree(root.parent / assets, ignore_errors=True)
    if assets and (made / assets).is_dir():
        shutil.copytree(made / assets, root.parent / assets, dirs_exist_ok=True)
    (root.parent / layer).parent.mkdir(exist_ok=True)
    shutil.copy2(made / layer, root.parent / layer)
    hold(root, f"./{layer}")
    taken = Sdf.Layer.FindOrOpen(str(root.parent / layer))
    if taken.HasEndTimeCode():
        stage_root = Sdf.Layer.FindOrOpen(str(root))
        stage_root.startTimeCode = 0.0
        stage_root.endTimeCode = max(taken.endTimeCode, stage_root.endTimeCode if stage_root.HasEndTimeCode() else 0)
        stage_root.timeCodesPerSecond = taken.timeCodesPerSecond
        stage_root.framesPerSecond = taken.framesPerSecond
        stage_root.Save()


# The layer the assembly writes of the motion's keys a light layer's plain value would hide, held just over the light.
MOTION_KEYS = "layers/motion_keys.usda"


def motion_over_light(root):
    """Every attribute the motion layer keys and the light layer also sets, its keys written again in a layer of the
    assembly's own (MOTION_KEYS) held just over the light layer: the light layer stands over the motion layer
    (record.ORDER), so its plain value hid the motion's keys (the airlock's cycle light, the garage's big door beacon,
    2026-10-16). Both taken layers stay as they came (the store's files are read-only and never edited)."""
    from pxr import Sdf
    out = root.parent
    motion, light = out / LAYERS["motion"][1], out / LAYERS["light"][1]
    if not (motion.exists() and light.exists()):
        return
    animated, lights = Sdf.Layer.FindOrOpen(str(motion)), Sdf.Layer.FindOrOpen(str(light))
    paths = []
    animated.Traverse(Sdf.Path.absoluteRootPath, paths.append)
    hidden = [path for path in paths if path.IsPropertyPath() and animated.GetAttributeAtPath(path)
              and animated.ListTimeSamplesForPath(path) and lights.GetAttributeAtPath(path)]
    if not hidden:
        return
    keys = Sdf.Layer.CreateNew(str(out / MOTION_KEYS))
    for path in hidden:
        spec = Sdf.AttributeSpec(Sdf.CreatePrimInLayer(keys, path.GetPrimPath()), path.name,
                                 animated.GetAttributeAtPath(path).typeName)
        for time in animated.ListTimeSamplesForPath(path):
            keys.SetTimeSample(spec.path, time, animated.QueryTimeSample(path, time))
    keys.Save()
    stage_root = Sdf.Layer.FindOrOpen(str(root))
    held = list(stage_root.subLayerPaths)
    held.insert(held.index(f"./{LAYERS['light'][1]}"), f"./{MOTION_KEYS}")
    stage_root.subLayerPaths = held
    stage_root.Save()


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


def judge_collision(output, inputs, evidence):
    """Fail on every wall, floor, stair or ground with no collision and every model with no collider."""
    from pxr import Usd
    faults = colliders.faults(Usd.Stage.Open(str(stage_file(output))))
    findings = tuple(f"{fault['prim']}: {fault['why']}" for fault in faults)
    solid = sum(fault["what"] != "model" for fault in faults)
    reason = (f"{solid} walls, floors or grounds without collision, {len(faults) - solid} models without a collider"
              if faults else "every wall, floor, stair and ground collides and every model has a collider")
    return checks.Verdict("collision", checks.FAIL if faults else checks.PASS, reason,
                          {"uncolliding": solid, "models without collider": len(faults) - solid},
                          {"uncolliding": "lower", "models without collider": "lower"}, findings)


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
    loose, ignore, _, under = settle.drop_job(stage, place, json.loads(inventory_path.read_text()), upright=False)
    settle.simulate(stage_path, loose, folder, cloud=True, ignore=ignore, under=under)
    return folder / "settled.json"


def needed_layers(inventory, kinds):
    """The layer stages a place's design needs (NEEDS of design_layers.kinds_of its scene inventory, by the row-kind
    rules `kinds`), in NEEDS' order."""
    shown = design_layers.kinds_of(inventory, kinds)
    return [stage for kind, stage in NEEDS.items() if kind in shown]


def judge_layers(output, inputs, evidence):
    """Unknown while a layer the place's design needs has no accepted output the assembly took (never a seed's in
    its place), and for a place with no design; fail on a sound of the sound layer that plays at nothing on the
    stage."""
    origin = json.loads((output / "origin.json").read_text())
    place = stage_file(output).stem
    taken = sorted(origin["layers"])
    measures = {"taken": len(taken), "unplaced sounds": len(origin["unplaced sounds"])}
    if origin["unplaced sounds"]:
        return checks.Verdict("layers", checks.FAIL, f"{len(origin['unplaced sounds'])} sounds play at nothing on "
                              "the stage", measures, {"unplaced sounds": "lower"}, tuple(origin["unplaced sounds"]))
    if "design" not in inputs:
        return checks.Verdict("layers", checks.UNKNOWN, f"{place} has no design (no scene inventory read from a "
                              "locked concept), so the layers it needs are not known", measures)
    needed = needed_layers(json.loads(pathlib.Path(inputs["design"]).read_text()),
                           json.loads(pathlib.Path(inputs["row kinds"]).read_text())["kinds"])
    waiting = [f"{name}@{place}" for name in needed if name not in origin["layers"]]
    if waiting:
        return checks.Verdict("layers", checks.UNKNOWN, f"waits on {', '.join(waiting)} (no accepted output taken); "
                              f"took {', '.join(taken) or 'none'}", measures, findings=tuple(waiting))
    return checks.Verdict("layers", checks.PASS, f"every layer it needs taken ({', '.join(needed) or 'none'}); took "
                          f"{', '.join(taken) or 'none'}; record: {origin['record']}", measures)


CHECKS = (checks.Check("layers", judge_layers), checks.Check("placeholders", judge_placeholders),
          checks.Check("collision", judge_collision),
          checks.Check("resting", judge_resting, evidence="a drop run (settle.py --dry-run)"))
GATHERERS = {"resting": (gather_drop_run, DROP_EUROS)}
