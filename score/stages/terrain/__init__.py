"""The terrain stage (the paper's Methods, "Terrain"): every ground of the environment from its dimensioned plan, one
environment node for all of them (Earth's harbour, the Moon round the base, Mars round the camp). Free, and made from
the repository alone: the plans, the library, the design tokens and the seated places' records, never the work folder.

Terrain is a model layer (CONTEXT.md "layer adapter", the owner, 2026-10-20): its shape is to come from the place's
rough model and its detail areas (outcrops, craters, cliffs, the ground round a building) from close-ups made into
models through the prop pipeline, joined into one continuous ground (#27). Until that adapter lands this row is the
code fallback, and every ground's measures.json says so (`made_by`, MADE_BY): the plan's large shape in code.

    make     for each plan in data/ground/plan/: the plan's large shape in code (plan.py, landforms.py: flats, paths,
             craters of every kind, ridges, buttes, dunes, canyons, hills, a coastline); the plan's levelled yards and
             dents; every zone one library surface (record.py); the rocks by the plan's rule (rocks.py); the ground
             record, and for every place on it the layer that draws the ground in the place's frame (outside.py)
    gates    scale      named landforms at their planned size, levels held, nothing clipped
             slope      flats, paths and level seats under their limits
             The ground under each place's objects, its continuity and its openings are judged on the place's
             assembly, which stands on this ground (ground-fit@<place>, fit.py).

The output (contract `grounds` v1) holds a folder per ground: ground.json (the record tools/usd/ground.py reads),
heights.png, zones.png, skin.png, rocks.json, plan.png (for reading), measures.json, and places/<place>.usdc, the
layer a place's stage takes over its old ground (the ground only: the places it shows are its own stage's and the
neighbours row's).
"""
import json
import pathlib

from pxr import Sdf, Usd, UsdGeom

from score import contracts
from score.stages.terrain import gates, measures, outside, plan, record, rocks

FILES = {"grounds": "{data}/ground", "library": ("{data}/library/materials.json", record.ground_surfaces),
         "tokens": "{data}/../design/tokens/tokens.json", "scenes": "{data}/scene", "kits": "{data}/kit"}
DRAWING_SIDE = 1024
CHECKS = gates.CHECKS
# What made every ground until the terrain adapter on the prop pipeline lands (#27): the code fallback, named.
MADE_BY = {"made_by": "code fallback: the plan's large shape (plan.py, landforms.py)",
           "why": "the terrain adapter (the rough model's ground and the detail areas' close-ups through the prop "
                  "pipeline, joined into one ground) is not built yet (#27)"}


def place_layers(folder, made, record_plan, inputs):
    """For every place on the ground, the layer that draws the made ground in its frame over its old ground:
    {place: the neighbours written (none: a place's shown places are its own stage's)}."""
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
        written[place] = outside.write(stage, place, made, zoned, laid, {**scene, "places": []},
                                       lambda name: f"../../{name}/{name}.usda")
        layer.Save()
    return written


def make_ground(ground, record_plan, shaped, inputs, out):
    """One ground's record, pictures, measures and place layers into out/<ground>."""
    folder = out / ground
    record.write(folder, record_plan, shaped, shaped.heights, rocks.laid(shaped, record_plan), inputs)
    made = record.read(folder)
    place_layers(folder, made, record_plan, inputs)
    found = {**MADE_BY, "scale": measures.scale(made, record_plan, shaped),
             "slope": measures.slope(made, record_plan, inputs), "compared": measures.compared(made, record_plan, inputs)}
    (folder / "measures.json").write_text(json.dumps(found, indent=1))


def make(inputs, out, seed, params):
    """Make every ground of the environment from its plan."""
    for path in sorted((pathlib.Path(inputs["grounds"]) / "plan").glob("*.json")):
        record_plan = json.loads(path.read_text())
        shaped = plan.shape(record_plan)
        (out / path.stem).mkdir(parents=True, exist_ok=True)
        plan.drawing(shaped, record_plan, DRAWING_SIDE).save(out / path.stem / "plan.png")
        make_ground(path.stem, record_plan, shaped, inputs, out)


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
