"""The assembly stage (P5): a place's single, final assembly. Its round-three OpenUSD stage comes in as an unverified
seed, and every layer stage's accepted output the node reads takes the place of the seed's part, so each place is
assembled once its layers have landed. No spend: nothing is rendered or settled here.

    make     copies the seed's stage (<place>.usda, layers/, assets/, inputs.json) into the output; old check results
             and manifests beside it are agent verdicts and stay out. Then, each from its accepted output:
             record   the scene-record row's record (experimental) written over the base's old record prims
                      (RECORD_ROOTS) with tools/usd/scene.py's writer; a place without the row keeps the seed's
                      record, said unverified. The record built from is written beside the stage (scene.json), the
                      one the neighbours stage reads
             layers   each layer stage of LAYERS the table holds (effects, motion, light, machines, crops; all
                      experimental) as a sublayer of its own with its assets, in place of the seed's of that name,
                      the root's sublayers in ORDER and its time range as long as the longest layer's
             bakes    a place's baked models (surfaces-bake) in place of the seed's assets, each laid object stamped
                      with the baked file's hash and the seed's as the model it repainted (stamp_baked_hash)
             ground   the terrain stage's places/<place>.usdc as layers/ground.usdc, just over the base
             sound    the sound row's output (experimental) written as layers/sound.usda (sounds.py), in place of the
                      seed's
             origin.json says the seed it came from, the record, every layer output taken and any sound placed
             nowhere.
    gates    layers        unknown while a layer the place needs (data/checks/contents.json's needs, sound and light
                           for every place it lists) has no accepted output taken: never the seed's in its place;
                           fail on a sound placed nowhere
             placeholders  tools/usd/placeholders.py: nothing visible stands in for a made piece (the hangar's
                           code-built ship fails, 12 meshes)
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
from score.stages.assembly import sounds

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tools/usd"))
import placeholders  # noqa: E402
import triage  # noqa: E402

FILES = {"seed": "{seeds}/usd-r3/{place}", "kit": "{data}/kit/{place}.json",
         "fittings": "{data}/library/fittings.json", "resting rules": "{data}/checks/resting.json",
         "inventories": "{data}/inventory", "library": "{data}/library", "sounds": "{data}/sound/surfaces.json",
         "places": "{data}/definitions/place.json", "tokens": "{repo}/design/tokens/tokens.json",
         "surfaces": "{data}/surfaces/{place}.json", "expected contents": "{data}/checks/contents.json",
         "motions": "{data}/motion", "grounds": "{data}/ground"}


def files(place):
    """FILES, and the place's seed scene record where it has one (the door leaves' kits have none)."""
    seed_record = {"scene": "{data}/scene/{place}.json"} if (REPO / f"data/scene/{place}.json").exists() else {}
    return {**FILES, **seed_record}


SEED_PARTS = ("layers", "assets", "inputs.json")
GROUND_LAYER = "layers/ground.usdc"
# The layer stages the assembly takes, each a sublayer of the root of its own: {stage: ((schema, version) read, its
# layer file, its assets folder or None)}. A stage joins the assembly's reads the day it joins the stage table
# (score/stages.layered): the motion, light and crops rows land after this table.
LAYERS = {"effects-layer": (("effects-layer", 1), "layers/effects.usda", "assets/effects"),
          "motion": (("motion-layer", 1), "layers/motion.usda", None),
          "light": (("light", 1), "layers/light.usda", "assets/light"),
          "machines-layer": (("machines-layer", 1), "layers/machines.usda", "assets"),
          "crops-layer": (("crops-layer", 1), "layers/crops.usda", "assets")}
# Every stage the assembly reads for the place's own layers (the bakes and the ground are read in the table).
READS = {"scene-record": ("scene-record", 1), "sound": ("sound-layer", 1),
         **{name: wanted for name, (wanted, _, _) in LAYERS.items()}}
# What each need of data/checks/contents.json asks of the place's layers, and the layers every place it lists (not a
# part of another) needs whatever its needs: contents.py's light and sound checks judge every such place.
NEEDS = {"effects": "effects-layer", "motion": "motion", "crops": "crops-layer"}
EVERY_PLACE = ("sound", "light")
# The root's sublayers, strongest first, by file name.
ORDER = ("edit", "characters", "sound", "light", "motion", "effects", "crops", "machines", "ground", "base")
# The base's prims tools/usd/scene.py writes from the scene record, removed before the accepted record is written.
RECORD_ROOTS = ("Structure", "Terrain", "Water", "Fixtures", "Rocks", "Places", "Sky", "Lights", "Environment",
                "Shafts")
RECORD = "scene.json"
BASE_LAYER = "./layers/base.usda"
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
        take_bake(pathlib.Path(inputs["surfaces-bake"]), pathlib.Path(inputs["surfaces-paint"]), out)
    for claimed in claimed_bakes(inputs, out):
        take_bake(*claimed)
    take_ground(inputs["terrain"], folder.name, out / root.name)
    unplaced = sounds.take(pathlib.Path(inputs["sound"]), out / root.name, inputs) if "sound" in inputs else []
    taken = {name: pathlib.Path(inputs[name]).name for name in READS if name in inputs}
    (out / "origin.json").write_text(json.dumps({"seed": True, "from": str(folder), "note": SEED_NOTE,
                                                 "record": record, "layers": taken, "unplaced sounds": unplaced},
                                                indent=1))


def take_record(inputs, out, place):
    """The place's scene record, written beside the stage (RECORD): its accepted scene-record output's, written over
    the seed base's record prims (RECORD_ROOTS removed, tools/usd/scene.py's writer run again on the base with the
    place's kit and ground record, as export.py runs it); for a place with none, the seed's own record, unverified. Where it came from,
    for origin.json."""
    if "scene-record" not in inputs and "scene" not in inputs:
        return "none: the place has no scene record"
    if "scene-record" not in inputs:
        shutil.copy2(inputs["scene"], out / RECORD)
        return f"the seed's record ({pathlib.Path(inputs['scene']).name}), unverified: no scene-record row"
    import ground as grounds
    import scene
    from pxr import Sdf, Usd
    made = pathlib.Path(inputs["scene-record"]) / "record" / f"{place}.json"
    shutil.copy2(made, out / RECORD)
    record = json.loads(made.read_text())
    kit = json.loads(pathlib.Path(inputs["kit"]).read_text())
    base = Sdf.Layer.FindOrOpen(str(out / BASE_LAYER))
    edit = Sdf.BatchNamespaceEdit()
    for name in RECORD_ROOTS:
        if base.GetPrimAtPath(f"/{place}/{name}"):
            edit.Add(f"/{place}/{name}", Sdf.Path.emptyPath)
    if not base.Apply(edit):
        raise RuntimeError(f"{place}: the seed's record prims could not be removed from its base")
    ground = grounds.place_ground(place, kit.get("on_seat", [0.0, 0.0]))  # as export.py's main: None for a room
    scene.write(Usd.Stage.Open(base), place, record, out, kit=kit, pieces=laid_pieces(kit, record), ground=ground)
    base.Save()
    return f"scene-record@{place}"


def claiming_places(place):
    """The places whose surface line paints models this place lays (its surface data's `elsewhere`), read beside."""
    path = REPO / "data/surfaces" / f"{place}.json"
    elsewhere = json.loads(path.read_text()).get("elsewhere", {}) if path.exists() else {}
    return sorted({claim["place"] for claim in elsewhere.values()})


def claimed_bakes(inputs, out):
    """(bake, paint, out, models) of each place whose bake holds models this place lays (its surface data's
    `elsewhere`, read beside: surfaces-bake@<place>), each model under the name both places give it."""
    found = []
    elsewhere = json.loads(pathlib.Path(inputs["surfaces"]).read_text()).get("elsewhere", {})
    for name, path in inputs.items():
        if name.startswith("surfaces-bake@"):
            other = name.split("@", 1)[1]
            models = [model for model, claim in elsewhere.items() if claim["place"] == other]
            found.append((pathlib.Path(path), pathlib.Path(inputs[f"surfaces-paint@{other}"]), out, models))
    return found


def take_bake(bake, paint, out, models=None):
    """The surface stage's baked models in place of the seed's: each model a place's bake made (or only `models` of
    it), written as the exporter writes an asset (tools/usd/export.write_asset: drawn mesh, collision, a subset per
    library surface from the paint's labelled parts) over the seed's assets/<model>.usdc and its maps."""
    import export
    import library
    variants = library.variants(library.theme_library())
    sounds = json.loads(export.SOUNDS.read_text())
    baked = json.loads((bake / "baked.json").read_text())
    missing = [model for model in models or () if model not in baked]
    if missing:
        raise FileNotFoundError(f"{bake}: its bake made none of {missing}, which this place lays by its claim")
    for model in models if models is not None else baked:
        entry = baked[model]
        (out / "assets" / f"{model}.usdc").unlink(missing_ok=True)
        export.write_asset(model, bake / "made", {model: paint / "labelled" / entry["parts"]}, None, entry["base"],
                           entry["size"], out, variants, sounds)
        stamp_baked_hash(out / BASE_LAYER, model, bake / "made" / f"{model}.gltf")


def stamp_baked_hash(base, model, gltf):
    """Every object of the base layer that lays `model` carries the baked file's hash (score:model_sha256,
    stage_inputs.model_hash, which the completion gate reads) in place of the seed's, and the seed's as the model the
    bake repainted (score:repaint_of, which the pick lock reads: a pick chooses the model, never its old paint)."""
    from pxr import Sdf
    import stage_inputs  # not complete.py: an edit to the gate re-makes no assembly
    layer = Sdf.Layer.FindOrOpen(str(base))
    sha256 = stage_inputs.model_hash(gltf)
    paths = []
    layer.Traverse(Sdf.Path.absoluteRootPath, paths.append)
    for path in paths:
        spec = layer.GetPrimAtPath(path) if path.IsPrimPath() else None
        if spec is None or "score:model" not in spec.attributes or spec.attributes["score:model"].default != model:
            continue
        before = {name: spec.attributes[name].default for name in ("score:model_sha256", "score:repaint_of")
                  if name in spec.attributes}
        for name, value in (("score:repaint_of", before.get("score:repaint_of") or before.get("score:model_sha256")),
                            ("score:model_sha256", sha256)):
            if value is None:
                continue
            attribute = spec.attributes[name] if name in spec.attributes else \
                Sdf.AttributeSpec(spec, name, Sdf.ValueTypeNames.String)
            attribute.default = value
    layer.Save()


def laid_pieces(kit, record):
    """A kit's pieces as the record's writer reads them for its lamps (scene.kit_lights): a walkway tube's on every
    bay of its way, each with its spot (export.tube_spots, as export.kit_room_pieces lays them); another's as laid."""
    if "bay" not in kit or not record.get("tube_length"):
        return kit["pieces"]
    import export
    return [dict(laid, spot=spot.tolist()) for laid in kit["pieces"]
            for spot in export.tube_spots(laid, record["tube_length"], float(kit["bay"]))]


def take_layer(made, root, layer, assets):
    """A layer stage's layer in place of the seed's (or beside it), with its assets: a folder of its own replaced
    whole, the shared assets/ merged. The root holds it in its place (hold) and plays as long as it does."""
    from pxr import Sdf
    if assets:
        if assets != "assets":
            shutil.rmtree(root.parent / assets, ignore_errors=True)
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


def hold(root, layer):
    """The root holding `layer` among its sublayers, all in ORDER (strongest first, by file name); one ORDER does
    not name goes just over the base."""
    from pxr import Sdf
    found = Sdf.Layer.FindOrOpen(str(root))
    layers = [path for path in found.subLayerPaths if path != layer] + [layer]

    def rank(path):
        stem = pathlib.PurePosixPath(path).stem
        return ORDER.index(stem) if stem in ORDER else ORDER.index("base") - 0.5

    found.subLayerPaths = sorted(layers, key=rank)
    found.Save()


def take_ground(grounds, place, root):
    """The place's made ground, when the terrain stage made one for it, sublayered just over the seed's base."""
    made = sorted(pathlib.Path(grounds).glob(f"*/places/{place}.usdc"))
    if not made:
        return
    shutil.copy2(made[0], root.parent / GROUND_LAYER)
    hold(root, f"./{GROUND_LAYER}")


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


def needed_layers(place, expected):
    """The layer stages a place needs (data/checks/contents.json's needs, and EVERY_PLACE): none for a part of another
    place (judged on its host), None for a place it does not list."""
    needs = expected["places"].get(place)
    if needs is None:
        return None
    if "part_of" in needs:
        return []
    return [*EVERY_PLACE, *(stage for need, stage in NEEDS.items() if needs.get(need))]


def judge_layers(output, inputs, evidence):
    """Unknown while a layer the place needs has no accepted output the assembly took (never a seed's in its place);
    fail on a sound of the sound layer that plays at nothing on the stage."""
    origin = json.loads((output / "origin.json").read_text())
    place = stage_file(output).stem
    needed = needed_layers(place, json.loads(pathlib.Path(inputs["expected contents"]).read_text()))
    taken = sorted(origin["layers"])
    measures = {"taken": len(taken), "unplaced sounds": len(origin["unplaced sounds"])}
    if origin["unplaced sounds"]:
        return checks.Verdict("layers", checks.FAIL, f"{len(origin['unplaced sounds'])} sounds play at nothing on "
                              "the stage", measures, {"unplaced sounds": "lower"}, tuple(origin["unplaced sounds"]))
    if needed is None:
        return checks.Verdict("layers", checks.UNKNOWN, f"{place} is not listed in data/checks/contents.json, so "
                              "the layers it needs are not known", measures)
    waiting = [f"{name}@{place}" for name in needed if name not in origin["layers"]]
    if waiting:
        return checks.Verdict("layers", checks.UNKNOWN, f"waits on {', '.join(waiting)} (no accepted output taken); "
                              f"took {', '.join(taken) or 'none'}", measures, findings=tuple(waiting))
    return checks.Verdict("layers", checks.PASS, f"every layer it needs taken ({', '.join(needed) or 'none'}); took "
                          f"{', '.join(taken) or 'none'}; record: {origin['record']}", measures)


CHECKS = (checks.Check("layers", judge_layers), checks.Check("placeholders", judge_placeholders),
          checks.Check("resting", judge_resting, evidence="a drop run (settle.py --dry-run)"))
GATHERERS = {"resting": (gather_drop_run, DROP_EUROS)}
