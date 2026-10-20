"""crops-layer@<place>: the crops on the place's beds, one point instancer a kind, as a layer the assembly takes.

    make     each kind's baked model (the place's own surface line bakes it like any made model: surfaces-bake
             and its paint's labelled parts) written as an asset the exporter's way (tools/usd/export.write_asset)
             under assets/; the beds (the scene record's boxes named with the crop data's `beds` prefix) shared out
             among the kinds by their patches' shares of the concept's plot (crops-concept), whole beds each, in the
             record's order; on each bed a kind's plants at the concept's spacing (in plant widths, times the made
             model's width: the concept draws its plants larger than the plan's metres hold them, so its look is
             kept, not a density in plants a square metre), on a grid of the bed's cells, each moved within its
             cell, turned and sized by the node's seed; layers/crops.usda holds /<place>/Crops/<kind>, a
             PointInstancer whose prototype references the kind's asset and carries the kind's inventory row
             (`score:row`, which the completion gate counts as laid) and says what made it (`score:kind` KIND, which
             the made-only check reads). spots.json keeps every plant (kind, bed,
             spot, turn, size) and each kind's model width and spacing in metres.
    gates    on beds    every plant stands on its bed, its centre at least EDGE inside the bed's edge, and every
                        bed carries plants
             spacing    each kind's spacing in plant widths as laid within LAID_WITHIN of the concept's

Experimental (PRD #6): the crop state (the concept's mid-season beds, not the game's bare start) is the owner's
open decision; the crop data says so.
"""
import json
import math
import pathlib
import random
import statistics

from score import checks
import score.stages.crops.crop_data as crop_data

LAYER = "layers/crops.usda"
# A plant's centre this far inside its bed's edge, metres; each moved at most this share of its cell from the cell's
# middle; turned anywhere round; sized within SIZE_SPREAD either way.
EDGE = 0.03
JITTER = 0.25
SIZE_SPREAD = 0.12
LAID_WITHIN = 0.25
KIND = "crop"


def beds_of(scene, prefix):
    """The scene record's beds: [{name, centre, size}], in the record's order."""
    return [{"name": item["name"], "centre": item["centre"], "size": item["size"]}
            for item in scene["structure"] if item["name"].startswith(prefix)]


def shared_out(beds, shares):
    """{kind: [bed names]}: whole beds to each kind by its share (largest remainder, at least one each), in order."""
    total = sum(shares.values())
    wanted = {kind: len(beds) * share / total for kind, share in shares.items()}
    counts = {kind: max(1, int(value)) for kind, value in wanted.items()}
    by_remainder = sorted(wanted, key=lambda kind: -(wanted[kind] - int(wanted[kind])))
    while sum(counts.values()) < len(beds):
        counts[by_remainder.pop(0)] += 1
    while sum(counts.values()) > len(beds):
        counts[max(counts, key=lambda kind: counts[kind])] -= 1
    found, start = {}, 0
    for kind in shares:
        found[kind] = [bed["name"] for bed in beds[start:start + counts[kind]]]
        start += counts[kind]
    return found


def bed_count(bed, spacing):
    """How many plants `spacing` metres apart a bed holds on a square grid, at least one."""
    return max(1, round(float(bed["size"][0]) * float(bed["size"][2]) / spacing ** 2))


def bed_spots(bed, count, generator):
    """`count` plants on one bed, on a grid of its cells, each moved within its cell; [(x, z)]."""
    width, depth = float(bed["size"][0]), float(bed["size"][2])
    columns = math.ceil(math.sqrt(count * width / depth))
    rows = math.ceil(count / columns)
    cell_x, cell_z = width / columns, depth / rows
    low_x = float(bed["centre"][0]) - width / 2.0
    low_z = float(bed["centre"][2]) - depth / 2.0
    cells = [(column, row) for row in range(rows) for column in range(columns)][:count]
    return [(low_x + (column + 0.5 + generator.uniform(-JITTER, JITTER)) * cell_x,
             low_z + (row + 0.5 + generator.uniform(-JITTER, JITTER)) * cell_z) for column, row in cells]


def model_of(entry):
    """The name a kind's model is baked and laid by: its inventory row's, numbered as the assembly numbers models."""
    return f"{entry['row']}_1"


def laid_spots(beds, shared, spacings, seed):
    """Every plant: {kind, bed, at (x, top of the bed, z), turn (degrees), size (a factor)}, each kind's `spacings`
    metres apart on its beds."""
    generator = random.Random(seed)
    named = {bed["name"]: bed for bed in beds}
    spots = []
    for kind, bed_names in shared.items():
        for name in bed_names:
            bed = named[name]
            top = float(bed["centre"][1]) + float(bed["size"][1]) / 2.0
            for spot_x, spot_z in bed_spots(bed, bed_count(bed, spacings[kind]), generator):
                spots.append({"kind": kind, "bed": name, "at": [round(spot_x, 4), round(top, 4), round(spot_z, 4)],
                              "turn": round(generator.uniform(0.0, 360.0), 2),
                              "size": round(1.0 + generator.uniform(-SIZE_SPREAD, SIZE_SPREAD), 4)})
    return spots


def write_assets(record, bake, paint, out):
    """Each kind's baked model as an asset under out/assets (export.write_asset, as the assembly takes a bake);
    {kind: {model, lowest (its lowest y), width (its widest across the floor)}}."""
    import export
    import library
    from pxr import Usd, UsdGeom
    variants = library.variants(library.theme_library())
    sounds = json.loads(export.SOUNDS.read_text())
    baked = json.loads((bake / "baked.json").read_text())
    found = {}
    for kind, entry in record["kinds"].items():
        model = model_of(entry)
        if model not in baked:
            raise FileNotFoundError(f"{kind}: the place's bake made no {model}")
        made = baked[model]
        export.write_asset(model, bake / "made", {model: paint / "labelled" / made["parts"]}, None, made["base"],
                           made["size"], out, variants, sounds)
        stage = Usd.Stage.Open(str(out / "assets" / f"{model}.usdc"))
        bounds = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ["default", "render"]).ComputeWorldBound(
            stage.GetDefaultPrim()).ComputeAlignedRange()
        low, high = bounds.GetMin(), bounds.GetMax()
        found[kind] = {"model": model, "lowest": float(low[1]),
                       "width": max(float(high[0] - low[0]), float(high[2] - low[2]))}
    return found


def write_layer(place, record, assets, spots, path):
    """layers/crops.usda: /<place>/Crops/<kind>, a point instancer a kind over its asset, each plant standing on its
    bed (the model's lowest point on the bed's top, sized and turned about the up axis)."""
    from pxr import Gf, Sdf, Usd, UsdGeom, Vt
    stage = Usd.Stage.CreateNew(str(path))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    stage.OverridePrim(f"/{place}")
    UsdGeom.Scope.Define(stage, f"/{place}/Crops")
    for kind, entry in record["kinds"].items():
        model, lowest = assets[kind]["model"], assets[kind]["lowest"]
        instancer = UsdGeom.PointInstancer.Define(stage, f"/{place}/Crops/{kind}")
        prototype = UsdGeom.Xform.Define(stage, f"/{place}/Crops/{kind}/Prototypes/{model}")
        prototype.GetPrim().CreateAttribute("score:row", Sdf.ValueTypeNames.String).Set(entry["row"])
        # what made it, as the made-only check reads it; a kind, not score:model, so the place's painted check (its
        # seed-repaint rule) does not take a crop's bake for a seed's paint
        prototype.GetPrim().CreateAttribute("score:kind", Sdf.ValueTypeNames.String).Set(KIND)
        prototype.GetPrim().GetReferences().AddReference(f"../assets/{model}.usdc")
        instancer.GetPrototypesRel().AddTarget(prototype.GetPath())
        own = [spot for spot in spots if spot["kind"] == kind]
        halves = [math.radians(spot["turn"]) / 2.0 for spot in own]
        instancer.CreateProtoIndicesAttr(Vt.IntArray([0] * len(own)))
        instancer.CreatePositionsAttr(Vt.Vec3fArray([Gf.Vec3f(spot["at"][0], spot["at"][1] - lowest * spot["size"],
                                                              spot["at"][2]) for spot in own]))
        instancer.CreateOrientationsAttr(Vt.QuathArray([Gf.Quath(math.cos(half), Gf.Vec3h(0.0, math.sin(half), 0.0))
                                                        for half in halves]))
        instancer.CreateScalesAttr(Vt.Vec3fArray([Gf.Vec3f(spot["size"]) for spot in own]))
    stage.GetRootLayer().Save()


def make_layer(inputs, out, seed, params):
    """The crops layer, its kinds' assets and spots.json (the beds each kind took, every plant, each kind's model
    width and spacing in metres)."""
    record = json.loads(pathlib.Path(inputs["crops"]).read_text())
    scene = json.loads(pathlib.Path(inputs["scene"]).read_text())
    measured = json.loads((pathlib.Path(inputs["crops-concept"]) / "concept.json").read_text())["kinds"]
    with crop_data.tools("usd"):
        assets = write_assets(record, pathlib.Path(inputs["surfaces-bake"]), pathlib.Path(inputs["surfaces-paint"]),
                              out)
    beds = beds_of(scene, record["beds"])
    shared = shared_out(beds, {kind: measured[kind]["share"] for kind in record["kinds"]})
    spacings = {kind: measured[kind]["spacing"] * assets[kind]["width"] for kind in record["kinds"]}
    spots = laid_spots(beds, shared, spacings, seed)
    (out / "layers").mkdir(exist_ok=True)
    write_layer(record["place"], record, assets, spots, out / LAYER)
    (out / "spots.json").write_text(json.dumps({"beds": shared, "spots": spots, "spacings": spacings,
                                                "widths": {kind: entry["width"] for kind, entry in assets.items()}},
                                               indent=1))


def layer_faults(folder):
    present = (folder / LAYER).exists() and (folder / "spots.json").exists()
    return [] if present else [f"no {LAYER} or spots.json"]


def judge_on_beds(output, inputs, evidence):
    """Every plant stands on its bed, EDGE inside its edge, and every bed carries plants."""
    record = json.loads(pathlib.Path(inputs["crops"]).read_text())
    beds = {bed["name"]: bed for bed in beds_of(json.loads(pathlib.Path(inputs["scene"]).read_text()),
                                                record["beds"])}
    spots = json.loads((output / "spots.json").read_text())["spots"]
    failing = []
    for number, spot in enumerate(spots):
        bed = beds.get(spot["bed"])
        if bed is None:
            failing.append(f"plant {number} ({spot['kind']}): on {spot['bed']}, which is no bed of the scene")
            continue
        off_x = abs(spot["at"][0] - bed["centre"][0]) - (bed["size"][0] / 2.0 - EDGE)
        off_z = abs(spot["at"][2] - bed["centre"][2]) - (bed["size"][2] / 2.0 - EDGE)
        if max(off_x, off_z) > 0:
            failing.append(f"plant {number} ({spot['kind']}): {max(off_x, off_z) + EDGE:.3f} m off {spot['bed']}'s "
                           "edge")
    bare = sorted(set(beds) - {spot["bed"] for spot in spots})
    failing += [f"{name}: no plants" for name in bare]
    return checks.Verdict("on beds", checks.FAIL if failing else checks.PASS,
                          f"{len(failing)} faults over {len(spots)} plants on {len(beds)} beds" if failing
                          else f"{len(spots)} plants on {len(beds)} beds", {"faults": len(failing)},
                          {"faults": "lower"}, tuple(failing[:40]))


def laid_spacings(spots, widths):
    """{kind: the median distance from a plant to its nearest neighbour of its kind over the kind's model width}."""
    found = {}
    for kind in sorted({spot["kind"] for spot in spots}):
        points = [(spot["at"][0], spot["at"][2]) for spot in spots if spot["kind"] == kind]
        if len(points) < 2:
            continue
        nearest = [min(math.dist(point, other) for number, other in enumerate(points) if number != index)
                   for index, point in enumerate(points)]
        found[kind] = statistics.median(nearest) / widths[kind]
    return found


def judge_spacing(output, inputs, evidence):
    """Each kind's spacing in plant widths as laid within LAID_WITHIN of the concept's."""
    record = json.loads(pathlib.Path(inputs["crops"]).read_text())
    measured = json.loads((pathlib.Path(inputs["crops-concept"]) / "concept.json").read_text())["kinds"]
    laid_record = json.loads((output / "spots.json").read_text())
    laid = laid_spacings(laid_record["spots"], laid_record["widths"])
    failing = []
    for kind in record["kinds"]:
        wanted, got = measured[kind]["spacing"], laid.get(kind)
        if got is None:
            failing.append(f"{kind}: under two plants laid, no spacing")
        elif abs(got - wanted) > LAID_WITHIN * wanted:
            failing.append(f"{kind}: {got:.2f} plant widths apart as laid, the concept's {wanted:.2f}")
    return checks.Verdict("spacing", checks.FAIL if failing else checks.PASS,
                          f"{len(failing)} of {len(record['kinds'])} kinds off the concept's spacing" if failing
                          else f"{len(record['kinds'])} kinds within {LAID_WITHIN:.0%} of the concept's spacing",
                          {f"{kind} spacing": round(value, 3) for kind, value in laid.items()}, findings=tuple(failing))


CHECKS = (checks.Check("on beds", judge_on_beds), checks.Check("spacing", judge_spacing))
