"""The terrain stage (the paper's Methods, "Terrain"): every ground of the world made from its dimensioned plan, one
world node for all of them (Earth's harbour, the Moon round the base, Mars round the camp).

    make     for each plan in data/ground/plan/: the plan's large shape in code (plan.py, landforms.py: flats, paths,
             craters of every kind, ridges, buttes, dunes, canyons, hills, a coastline); a diorama picture drawn
             straight down over the plan's shading by Qwen-Image-Edit-2511 (tools/props/cloud/pictures.py, PAID: its
             `candidates`, an 80 GB card each); each picture's depth by Depth Anything V2 Small
             (tools/props/cloud/depth.py, PAID, any card); each registered on the plan and the one whose depth
             follows the plan best gives the fine relief (relief.py); the plan's levelled yards and dents; every zone one library surface
             (record.py); the rocks by the plan's rule (rocks.py); the ground record, and for every place on it the
             layer that draws the ground and its missing neighbours in the place's frame (outside.py)
    gates    scale      named landforms at their planned size, levels held, nothing clipped
             slope      flats, paths and level seats under their limits
             under      ground under every object that stood on the old ground
             openings   no doorway onto nothing and no view running out below the horizon, doors open

The output (contract `grounds` v1) holds a folder per ground: ground.json (the record tools/usd/ground.py reads),
heights.png, zones.png, skin.png, rocks.json, plan.png (for reading) and shading.png (the pictures' input), the
candidates' pictures and the chosen depth on the plan, measures.json,
and places/<place>.usdc, the layer a place's stage takes over its old ground.
"""
import hashlib
import json
import pathlib
import shutil
import sys

import numpy as np
from pxr import Sdf, Usd, UsdGeom

from score import contracts
from score.stages.terrain import gates, measures, outside, plan, record, relief, rocks

REPO = pathlib.Path(__file__).resolve().parents[3]
FILES = {"grounds": "{data}/ground", "library": ("{data}/library/materials.json", record.ground_surfaces),
         "tokens": "{data}/../design/tokens/tokens.json", "scenes": "{data}/scene", "kits": "{data}/kit",
         "motion": "{data}/motion", "seeds": "{seeds}/usd-r3"}
# The run's estimate: about a dozen Qwen-Image-Edit pictures on 80 GB cards and their depth on any card.
EUROS = 6.0
PICTURE_SIDE = 1024
CHECKS = gates.CHECKS


def cloud_runners():
    """The picture and depth runners (tools/props/cloud), loaded only when the stage makes."""
    folder = REPO / "tools/props/cloud"
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))
    import depth
    import pictures
    return pictures, depth


def picture_jobs(shaped_plans, out, seed):
    """The diorama picture jobs, `candidates` a ground, each named by its drawing, wording and seed so a changed plan
    is drawn again: [{name, wording, seed, refs, width, height, ground, candidate}]."""
    jobs = []
    for ground, (record_plan, _) in shaped_plans.items():
        drawing = out / "picture-refs" / f"{ground}-shading.png"  # its own name: every job's refs share one folder
        drawing.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(out / ground / "shading.png", drawing)
        for candidate in range(record_plan["picture"]["candidates"]):
            picked_seed = (seed + 7919 * candidate) % 2 ** 31
            named = hashlib.sha256(drawing.read_bytes() + record_plan["picture"]["wording"].encode()
                                   + str(picked_seed).encode()).hexdigest()[:12]
            jobs.append({"name": f"terrain-{ground}-{named}-c{candidate}", "wording": record_plan["picture"]["wording"],
                         "seed": picked_seed, "refs": [str(drawing)], "width": PICTURE_SIDE,
                         "height": PICTURE_SIDE, "ground": ground, "candidate": candidate})
    return jobs


def drawn(jobs, out):
    """Every picture job drawn on rented cards, each copied into its ground's diorama folder; {ground: [paths]}."""
    pictures, _ = cloud_runners()
    listing = out / "pictures.json"
    listing.write_text(json.dumps(jobs, indent=1))
    pictures.draw_list(listing, model="qwen-edit")
    shutil.rmtree(out / "picture-refs")
    found = {}
    for job in jobs:
        made = pictures.PICTURES / f"{job['name']}.png"
        if made.exists():
            target = out / job["ground"] / "diorama" / f"c{job['candidate']}.png"
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(made, target)
            found.setdefault(job["ground"], []).append(target)
    return found


def depths(found, out):
    """Every picture's depth, read on rented cards: {picture path: depth array}."""
    _, depth = cloud_runners()
    every = [path for paths in found.values() for path in paths]
    work = out / "depth-work"
    renamed = []
    for path in every:
        named = work / "in" / f"{path.parent.parent.name}-{path.stem}.png"
        named.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, named)
        renamed.append(named)
    depth.measure(renamed, work / "out")
    read = {}
    for path, named in zip(every, renamed):
        result = work / "out" / f"{named.stem}.npy"
        if result.exists():
            read[path] = np.load(result).astype(np.float64)
    shutil.rmtree(work)
    return read


def chosen_relief(ground, record_plan, shaped, pictures_of, read, out):
    """The ground's relief from its best-following candidate, and what was measured to choose it."""
    candidates = [path for path in pictures_of if path in read]
    if not candidates:
        raise RuntimeError(f"{ground}: no diorama picture came back with its depth; nothing to read its relief from")
    settings = record_plan["relief"]
    best, placed = relief.chosen([read[path] for path in candidates], shaped.heights, shaped.grid.side,
                                 settings["fine"])
    sign = 1.0 if placed[best]["correlation"] >= 0 else -1.0
    depth = relief.on_plan(read[candidates[best]], placed[best])
    np.save(out / ground / "diorama" / "chosen-depth.npy", depth.astype(np.float16))
    choice = {"picture": f"diorama/{candidates[best].name}", "correlation": placed[best]["correlation"],
              "registrations": {path.name: found for path, found in zip(candidates, placed)}, "sign": sign}
    return relief.relief(shaped, record_plan, depth, sign), choice


def place_layers(folder, made, record_plan, inputs):
    """For every place on the ground, the layer that draws the made ground in its frame over its old ground, and the
    neighbours its scene record names, as a stage folder's layers/ reaches them (../../<stage>/<stage>.usda)."""
    written = {}
    for place, seat in record_plan["seats"].items():
        scene, kit, _ = gates.place_files(inputs, place)
        if not scene:
            continue
        zoned, laid = outside.meshes(made, seat, (kit or {}).get("on_seat", [0.0, 0.0]), gates.footprint(scene, kit))
        path = folder / "places" / f"{place}.usdc"
        path.parent.mkdir(parents=True, exist_ok=True)
        layer = Sdf.Layer.CreateNew(str(path))
        stage = Usd.Stage.Open(layer)
        UsdGeom.SetStageMetersPerUnit(stage, 1.0)
        UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
        stage.DefinePrim(f"/{place}")
        seed_stage = gates.seed_stage(inputs["seeds"], place)
        missing = [entry for entry in scene.get("places", [])
                   if not seed_stage.GetPrimAtPath(f"/{place}/Places/{entry['name']}").IsValid()]
        written[place] = outside.write(stage, place, made, zoned, laid, {**scene, "places": missing},
                                       lambda name: f"../../{name}/{name}.usda")
        layer.Save()
    return written


def make_ground(ground, record_plan, shaped, pictures_of, read, inputs, out):
    """One ground's record, pictures, measures and place layers into out/<ground>."""
    folder = out / ground
    added, choice = chosen_relief(ground, record_plan, shaped, pictures_of, read, out)
    made = record.write(folder, record_plan, shaped, shaped.heights + added, rocks.laid(shaped, record_plan), choice,
                        inputs)
    made = record.read(folder)
    neighbours = place_layers(folder, made, record_plan, inputs)
    found = {"relief": {**choice, "rms_m": round(float(added.std()), 3)}, "neighbours_added": neighbours,
             "scale": measures.scale(made, record_plan, shaped), "slope": measures.slope(made, record_plan, inputs),
             "compared": measures.compared(made, record_plan, inputs)}
    (folder / "measures.json").write_text(json.dumps(found, indent=1))


def make(inputs, out, seed, params):
    """Make every ground of the world from its plan."""
    shaped_plans = {}
    for path in sorted((pathlib.Path(inputs["grounds"]) / "plan").glob("*.json")):
        record_plan = json.loads(path.read_text())
        shaped = plan.shape(record_plan)
        (out / path.stem).mkdir(parents=True, exist_ok=True)
        plan.drawing(shaped, record_plan, PICTURE_SIDE).save(out / path.stem / "plan.png")
        plan.shading(shaped, PICTURE_SIDE).save(out / path.stem / "shading.png")
        shaped_plans[path.stem] = (record_plan, shaped)
    found = drawn(picture_jobs(shaped_plans, out, seed), out)
    read = depths(found, out)
    for ground, (record_plan, shaped) in shaped_plans.items():
        make_ground(ground, record_plan, shaped, found.get(ground, []), read, inputs, out)


def grounds_faults(folder):
    """The output against its contract: at least one ground, each with its record and pictures."""
    folder = pathlib.Path(folder)
    made = [path for path in folder.iterdir() if (path / "ground.json").exists()]
    if not made:
        return ["no ground made"]
    faults = []
    for ground in made:
        for name in ("heights.png", "zones.png", "skin.png", "rocks.json", "measures.json"):
            if not (ground / name).exists():
                faults.append(f"{ground.name} lacks {name}")
    return faults


GROUNDS = contracts.Contract("grounds", 1, grounds_faults, {"length": "metre", "up axis": "Y"})
