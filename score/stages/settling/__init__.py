"""The settle stage (experimental, PRD #6, until the owner reviews it): where a place's objects come to rest on its made
ground, laid as an OpenUSD settle layer that the assembly stage puts into the place's stage over the seed's base.

    make     the seed (world 1's round-three stage) on the terrain stage's made ground (assembly.take_ground), every
             loose object dropped once in headless Blender on a rented processor machine (tools/usd/settle.py's drop
             job: an object an old settle left tipped onto uneven feet stood upright first, one stacked on another
             meeting it), and each one's rest (settle.rest_poses: a small correction written, a large one left as laid,
             a tip onto uneven feet stood upright for the paint to level); then each fixed one the triage finds
             floating as laid let down onto what is under it (held.fixed_let_down); then each held object stood
             upright and snapped down onto its holder as it rests (held.held_rests); and each object that then rests
             worse than as laid kept as laid with what it holds (kept_where_worse); all laid as layers/settle.usda
             (an over of each moved object's transform), with settle.json (each object's rest and what it did) and the drop's own
             record (drop/settle-job.json, drop/settled.json). A drop is bought only when something loose is to be
             stood up or unstacked or the triage finds a fault on it (free, first); a drop already paid for (the same
             job, drop script and stage) is read back from DROPS, not bought again.
    gates    rested    the drop did not break: nothing still moving at its end, no two at rest inside each other; one
                       kept as laid (it would turn or drift past the settle's limits: its layout's or its model's fault)
                       or stood upright on uneven feet for the paint is named, not failed
             resting   the settle layer makes nothing rest worse: no object the resting triage finds a real fault on
                       on the seed with its made ground and the layer that it found none on without it (the feet
                       and lean of one stood upright for the paint aside); what is left is named, for the assembly's
                       own drop and triage to judge on the baked models

Only the places in stages.SETTLED have the row; the assembly of any other place lays the seed's poses. The seed's
models, not the surface stage's bakes, are dropped, so the row does not wait on the paint: a baked model keeps its
shape but for the feet the paint levels, which the upright stand leaves room for.
"""
import json
import os
import pathlib
import shutil
import sys
import tempfile

from score import checks, contracts
from score.store import PROPS_HOME

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tools/usd"))
import settle  # noqa: E402
import triage  # noqa: E402
from score.stages.settling import held as snapped  # noqa: E402

LAYER = "layers/settle.usda"
RECORD = "settle.json"
DROP = "drop"
# One drop run's estimate: as the assembly's (a quarter to three quarters of an hour on a rented processor machine).
EUROS = 1.0
# Drops already paid for, by their job, drop script and stage (settle.drop_key): the same drop is never bought twice.
DROPS = PROPS_HOME / "store/cache/drops"
# Where the gates put a seed together to judge it (on disk, beside the store's cache).
SCRATCH = PROPS_HOME / "store/cache"
SEED_PARTS = ("layers", "inputs.json")
# A rest the paint finishes: the faults the triage raises of an object stood upright on uneven feet.
FOR_THE_PAINT = ("foot off", "leans", "tips")


def files(place):
    """What the stage reads: the place's seed stage, kit (its seat and its pieces' spots), scene record (when it has
    one: what the kit relay reads), inventory (what holds each object up), the resting rules and the drop script its
    machine runs."""
    import stage_inputs
    found = {"seed": "{seeds}/usd-r3/{place}", "kit": "{data}/kit/{place}.json",
             "inventory": "{data}/inventory/" + stage_inputs.inventory_path(place).name,
             "resting rules": "{data}/checks/resting.json",
             "drop script": "{repo}/tools/blender/inside/settle_stage.py"}  # run by path on the machine
    if (REPO / "data/scene" / f"{place}.json").exists():
        found["scene"] = "{data}/scene/{place}.json"
    return found


def read_json(path):
    return json.loads(pathlib.Path(path).read_text())


def place_of(inputs):
    return pathlib.Path(inputs["seed"]).name


# --- the stage dropped -------------------------------------------------------------------------------------------

def grounded_seed(inputs, folder):
    """The seed's stage in `folder` on the place's made ground, each kit piece at its kit spot (the assembly's
    take_ground and relay_kit, so the settle starts from what the assembly lays): its root and layers copied, its
    assets linked (read, never written). The root's path."""
    import score.stages.assembly.record as record  # this form: the code version hashes record.py alone
    seed = pathlib.Path(inputs["seed"])
    folder.mkdir(parents=True, exist_ok=True)
    root = folder / f"{seed.name}.usda"
    shutil.copy2(seed / root.name, root)
    for part in SEED_PARTS:
        source = seed / part
        if source.is_dir():
            shutil.copytree(source, folder / part)
        elif source.exists():
            shutil.copy2(source, folder / part)
    shutil.copytree(seed / "assets", folder / "assets", copy_function=linked)
    record.take_ground(inputs["terrain"], seed.name, root)
    record.relay_kit({key: inputs[key] for key in ("kit", "scene") if key in inputs}, folder, seed.name)
    return root


def linked(source, target):
    """A file linked where it can be (one disk), else copied."""
    try:
        os.link(source, target)
    except OSError:
        shutil.copy2(source, target)


def make(inputs, out, seed, params):
    """Drop the place's loose objects on its made ground and lay where each comes to rest. The grounded seed is put
    together in the output's own folder and taken out again once the drop is read."""
    from pxr import Usd
    place = place_of(inputs)
    inventory = read_json(inputs["inventory"])
    scratch = out / "scratch"
    try:
        root = grounded_seed(inputs, scratch)
        seed = Usd.Stage.Open(str(pathlib.Path(inputs["seed"]) / root.name))  # the seed's poses, which nothing moves
        stage = Usd.Stage.Open(str(root))
        loose, ignore, starts, under = settle.drop_job(stage, place, inventory, upright=True, kit_path=inputs["kit"])
        found = judged(root, inputs)
        laid = faulty(found, place)
        if starts or under or laid & set(loose):
            simulated = settle.simulate(root, loose, out / DROP, cloud=True, ignore=ignore, start=starts, under=under,
                                        cache=DROPS)
        else:  # nothing loose to stand up, unstack or put right: no drop is bought, each rests as laid
            simulated = still(loose, out / DROP)
        poses = settle.rest_poses(stage, place, inventory, simulated, starts)
        laid_over(root, seed, place, poses, scratch / "dropped.usda")
        poses = merged(poses, fixed_phase(root, found, place), seed, place)  # before the held: they lie on these
        poses = merged(poses, held_phase(root, scratch / "fixed.usda", inputs, inventory, poses, seed), seed, place)
        laid_over(root, seed, place, poses, scratch / "held.usda")
        poses = kept_where_worse(poses, faulty(judged(root, inputs), place) - laid, inventory)
        write_layer(seed, place, moved(poses), out / LAYER)
        del stage, seed
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    (out / RECORD).write_text(json.dumps({
        "place": place, "overlaps": simulated["overlaps"],
        "objects": {name: {"rested": pose["rested"], "said": pose["said"], "matrix": pose["after"].tolist()}
                    for name, pose in sorted(poses.items())}}, indent=1))


def judged(root, inputs):
    """The resting triage of the stage at `root` on the declared rules, kit and inventory."""
    return triage.triage(root, None, rules_file=inputs["resting rules"], kit_file=inputs["kit"],
                         inventory_file=inputs["inventory"])


def faulty(found, place):
    """The top-level objects a triage finds a real fault on, by name (the free check before a drop is bought, and
    after one what it made worse)."""
    names = {fault["object"].removeprefix(f"/{place}/Objects/") for fault in found["faults"] if fault["real"]}
    return {name.split("/")[0] for name in names}


def kept_where_worse(poses, worse, inventory):
    """Each object that rests worse than as laid (`worse`: names with a real fault now and none before: a model with
    a sloping base the drop tips over the triage's lean, a mouse snapped onto a desk's edge), and what is held on it,
    kept as laid: the layer never makes an object rest worse."""
    held_on = {row["id"]: row.get("anchor", "").removeprefix("on:") for row in inventory["rows"]}
    rows = {name.rsplit("_", 1)[0] for name in worse}
    kept = {name for name in poses if name in worse or held_on.get(name.rsplit("_", 1)[0]) in rows}
    return {name: (dict(pose, after=pose["before"], rested=False,
                        said=f"kept as laid: {pose['said']} made it rest worse") if name in kept else pose)
            for name, pose in poses.items()}


def still(loose, folder):
    """A drop's record in which every loose object rests as laid (no drop was needed), written as a drop's is."""
    import numpy as np
    folder.mkdir(parents=True, exist_ok=True)
    found = {"objects": {name: {"motion": np.eye(4).tolist(), "moving": 0.0, "inside": []} for name in sorted(loose)},
             "overlaps": [], "dropped": False}
    (folder / "settled.json").write_text(json.dumps(found, indent=1))
    return found


def moved(poses):
    """{name: its rest} of each pose that moves its object."""
    import numpy as np
    return {name: pose["after"] for name, pose in poses.items() if not np.allclose(pose["after"], pose["before"])}


def merged(poses, found, seed, place):
    """A later step's poses over the earlier ones, each from the seed's laid matrix; one the later step left as laid
    keeps where the earlier put it."""
    for name, pose in found.items():
        earlier = poses.get(name, {}).get("after")
        kept = pose["after"] is pose["before"] and earlier is not None
        poses[name] = {**pose, "before": settle.laid_matrix(seed, place, name),
                       "after": earlier if kept else pose["after"]}
    return poses


def laid_over(root, seed, place, poses, path):
    """The poses so far written as a layer at `path`, put over everything else the scratch root holds."""
    from pxr import Sdf
    write_layer(seed, place, moved(poses), path)
    layer = Sdf.Layer.FindOrOpen(str(root))
    layer.subLayerPaths = [str(path), *layer.subLayerPaths]
    layer.Save()


def held_phase(root, path, inputs, inventory, poses, seed):
    """Each held object at rest on its holders as they rest (held.held_rests), and its own glowing parts carried
    with it: {name: pose}."""
    from pxr import Usd
    place = place_of(inputs)
    laid_over(root, seed, place, poses, path)
    held = snapped.held_rests(root, place, inventory, inputs["kit"])
    rested = Usd.Stage.Open(str(root))
    entries = {name: {"before": pose["before"], "after": pose["after"],
                      "middle": settle.object_middle(rested, place, name)}
               for name, pose in held.items() if pose["rested"]}
    held.update({name: {**found, "rested": True, "said": "carried with what it lies on"}
                 for name, found in settle.carried_with(rested, place, inventory, entries).items()})
    return held


def fixed_phase(root, found, place):
    """Each fixed object the triage (`found`, with everything else at rest) finds floating, let down onto what is
    under it (held.fixed_let_down): {name: pose}."""
    floating = sorted({fault["object"].removeprefix(f"/{place}/Objects/") for fault in found["faults"]
                       if fault["real"] and fault["kind"] == "floats" and fault["support"] == "fixed"})
    return snapped.fixed_let_down(root, place, [name for name in floating if "/" not in name])


def write_layer(stage, place, matrices, path):
    """An over of each object's transform ({name: its matrix in the stage's frame}, written in its parent's frame)
    as an OpenUSD layer."""
    import numpy as np
    from pxr import Gf, Sdf, Usd, UsdGeom
    path.parent.mkdir(parents=True, exist_ok=True)
    layer = Sdf.Layer.CreateNew(str(path))
    for name, matrix in sorted(matrices.items()):
        prim = stage.GetPrimAtPath(f"/{place}/Objects/{name}")
        parent = UsdGeom.Xformable(prim.GetParent()).ComputeLocalToWorldTransform(Usd.TimeCode.Default())
        parent = np.asarray(parent).T
        local = np.linalg.inv(parent) @ np.asarray(matrix)
        spec = Sdf.CreatePrimInLayer(layer, prim.GetPath())
        spec.specifier = Sdf.SpecifierOver
        transform = Sdf.AttributeSpec(spec, "xformOp:transform", Sdf.ValueTypeNames.Matrix4d)
        transform.default = Gf.Matrix4d(local.T.tolist())
        order = Sdf.AttributeSpec(spec, "xformOpOrder", Sdf.ValueTypeNames.TokenArray,
                                  variability=Sdf.VariabilityUniform)
        order.default = ["xformOp:transform"]
    layer.Save()


def layer_faults(folder):
    """The settle layer and its record are there."""
    folder = pathlib.Path(folder)
    return [f"no {part}" for part in (LAYER, RECORD, f"{DROP}/settled.json") if not (folder / part).exists()]


# --- the gates ---------------------------------------------------------------------------------------------------

def judge_rested(output, inputs, evidence):
    """Fail when the drop broke: an object still moving at its end, or two at rest inside each other (a rest of at
    least one written). One that would not rest as laid keeps its pose (its fault stays where it was, for its layout
    or its model) and one stood upright on uneven feet waits on the paint: both are named, neither fails the row."""
    record = read_json(pathlib.Path(output) / RECORD)
    faults = [f"{name}: {entry['said']}" for name, entry in sorted(record["objects"].items())
              if "still moving" in entry["said"]]
    faults += [f"{first} and {second} came to rest inside each other" for first, second in record["overlaps"]
               if any(record["objects"].get(name, {}).get("rested") for name in (first, second))]  # not both kept
    kept = [f"{name}: {entry['said']}" for name, entry in sorted(record["objects"].items())
            if not entry["rested"] and "still moving" not in entry["said"]]
    reason = (f"{len(faults)} drops broke" if faults else f"all {len(record['objects'])} rests found") + \
        (f"; {len(kept)} kept as laid or stood upright for the paint" if kept else "")
    return checks.Verdict("rested", checks.FAIL if faults else checks.PASS, reason,
                          {"broken": len(faults), "kept": len(kept)}, {"broken": "lower", "kept": "lower"},
                          tuple(faults) + tuple(kept))


def for_the_paint(entry):
    """Whether an object's rest is a stand upright on uneven feet (settle.rest_poses), for the paint to finish."""
    return not entry["rested"] and entry["said"].endswith("stood upright on its lowest foot")


def judge_resting(output, inputs, evidence):
    """Fail when the settle layer makes any object rest worse: an object the resting triage finds a real fault on, on
    the seed with its made ground and the settle layer, that it found none on without the layer (the feet and lean of
    an object stood upright for the paint aside). What is left is named; the assembly's own drop and triage judge it
    on the baked models."""
    record = read_json(pathlib.Path(output) / RECORD)
    for_paint = {name for name, entry in record["objects"].items() if for_the_paint(entry)}
    found = {}
    for state, layered in (("before", False), ("after", True)):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as scratch:  # on disk: a seed copy is too big for /tmp
            found[state] = triage.triage(rested_root(output, inputs, pathlib.Path(scratch), layered),
                                         rules_file=inputs["resting rules"], kit_file=inputs["kit"],
                                         inventory_file=inputs["inventory"])
    real = {state: [fault for fault in found[state]["faults"] if fault["real"]
                    and not (fault["object"].rsplit("/", 1)[-1] in for_paint and fault["kind"] in FOR_THE_PAINT)]
            for state in found}
    was = {fault["object"] for fault in real["before"]}  # an object at fault as laid is no worse for another kind
    worse = [fault for fault in real["after"] if fault["object"] not in was]
    objects = {state: len({fault["object"] for fault in real[state]}) for state in real}
    findings = tuple(f"{'worse' if fault in worse else 'left'}: {fault['object']}: {fault['kind']} {fault['measure']}: "
                     f"{fault['why']}" for fault in sorted(real["after"], key=lambda fault: fault not in worse))
    reason = (f"{objects['after']} of {found['after']['objects']} objects with real resting faults rested, "
              f"{objects['before']} as laid" + (f"; {len(worse)} faults new with the settle layer" if worse else ""))
    return checks.Verdict("resting", checks.FAIL if worse else checks.PASS, reason,
                          {"objects with faults": objects["after"], "as laid": objects["before"], "worse": len(worse)},
                          {"objects with faults": "lower", "worse": "lower"}, findings)


def rested_root(output, inputs, folder, layered=True):
    """The seed on its made ground, its kit pieces at their kit spots (grounded_seed), in `folder`, with the settle
    layer over it unless not `layered`: the stage the assembly lays, but for the bakes and the other layers."""
    from pxr import Sdf
    root = grounded_seed(inputs, folder)
    if layered:
        layer = Sdf.Layer.FindOrOpen(str(root))
        layer.subLayerPaths = [str(pathlib.Path(output) / LAYER), *layer.subLayerPaths]
        layer.Save()
    return root


SETTLE_LAYER = contracts.Contract("settle-layer", 1, layer_faults, {"length": "metre", "up axis": "Y"})
CHECKS = (checks.Check("rested", judge_rested), checks.Check("resting", judge_resting))
