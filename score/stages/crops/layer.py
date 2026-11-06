"""crops-layer@<place>: the crops on the place's beds, one point instancer a kind, as a layer the assembly takes.

    make     each kind's baked model (the place's own surface line bakes it like any made model: surfaces-bake
             and its paint's labelled parts) written as an asset the exporter's way (tools/usd/export.write_asset)
             under assets/; the beds (the plan items its bed rows make, crop_data.beds_in) shared out among the
             kinds standing on each bed row by their patches' shares of the concept's plot (crops-concept), whole
             beds each, in the plan's order; on each bed a kind's plants at the concept's spacing (in plant widths, times the made
             model's width: the concept draws its plants larger than the plan's metres hold them, so its look is
             kept, not a density in plants a square metre), on a grid of the bed's cells, each moved within its
             cell, turned and sized by the node's seed; each plant fits its bed, kept in its proportions (owner,
             2026-11-04, a greenhouse's 2.3 m planter tray on beds of 0.47 x 0.67 m: "Scale each plant to its bed"):
             sized down where its reach (its footprint's farthest corner from its foot, so at any turn) passes the
             bed's half side, the bed's spacing in metres sized with it, then each plant kept and moved within its
             own cell, so none overhangs its bed or passes through a neighbour; layers/crops.usda holds /<place>/Crops/<kind>, a
             PointInstancer whose prototype references the kind's asset and carries the kind's inventory row
             (`score:row`, which the completion gate counts as laid) and says what made it (`score:kind` KIND, which
             the made-only check reads). spots.json keeps every plant (kind, bed,
             spot, turn, size) and each kind's model width, footprint at size 1 and spacing in metres. A kind whose model the bake did
             not make and a batch gap its inputs carry names (the prop route left the take out: pixal, the finish
             route, the bake; score/stages/batch_gaps.py) is left out, its beds bare, and named in this output's
             batch-gaps.json with the gaps carried on, so `on beds` and `spacing` move its faults to it
             (stages.BATCH_GATES); a model missing with no gap naming it still raises.
    gates    on beds    every plant stands on its bed, its centre at least EDGE inside the bed's edge and its
                        footprint, turned and sized as laid, within the bed and clear of every other plant's; and
                        every bed carries plants
             spacing    each kind's spacing in plant widths as laid (each plant's width times its size: to its
                        nearest neighbour on its own bed, a plant alone on its bed its bed's side) within
                        LAID_WITHIN of the concept's

Experimental (PRD #6): the crops are laid as the locked concept grows them (its kinds' patches and spacing).
"""
import json
import math
import pathlib
import random
import statistics

from score import checks
from score.stages import batch_gaps
import score.stages.crops.crop_data as crop_data
from score.stages.props import prop_data

LAYER = "layers/crops.usda"
# A plant's centre this far inside its bed's edge, metres; each moved at most this share of its cell from the cell's
# middle; turned anywhere round; sized within SIZE_SPREAD either way; footprints this far over (metres) a fault.
EDGE = 0.03
JITTER = 0.25
SIZE_SPREAD = 0.12
LAID_WITHIN = 0.25
TOUCH = 1e-6
# spots are kept to 0.1 mm: a plant keeps this much more room, so the rounding never takes it past its cell
ROUNDING = 1e-4
KIND = "crop"


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


def shared_by_bed(record, beds, shares):
    """{kind: [bed names]}: each bed row's beds shared out among the kinds standing on it (shared_out)."""
    found = {}
    for bed_row in record["beds"]:
        own = {kind: shares[kind] for kind, entry in record["kinds"].items() if entry["bed"] == bed_row}
        found.update(shared_out([bed for bed in beds if bed["row"] == bed_row], own))
    return found


def bed_count(bed, spacing):
    """How many plants `spacing` metres apart a bed holds on a square grid, at least one."""
    return max(1, round(float(bed["size"][0]) * float(bed["size"][2]) / spacing ** 2))


def reach_of(footprint):
    """How far a plant reaches across the floor from its foot at size 1, at any turn: its footprint's farthest
    corner; `footprint` [low x, high x, low z, high z] round its foot."""
    low_x, high_x, low_z, high_z = footprint
    return max(math.hypot(corner_x, corner_z) for corner_x in (low_x, high_x) for corner_z in (low_z, high_z))


def bed_scale(bed, reach):
    """The size a plant of `reach` is laid at on a bed: 1, or less where its reach passes the bed's half side."""
    return min(1.0, min(float(bed["size"][0]), float(bed["size"][2])) / 2.0 / reach)


def moved(half, room, generator):
    """A plant's offset from its cell's middle: at most JITTER of the cell, never past the `room` it has."""
    return generator.uniform(-1.0, 1.0) * max(0.0, min(JITTER * 2.0 * half, room))


def bed_spots(bed, count, reach, scale, generator):
    """`count` plants on one bed, on a grid of its cells, each sized round `scale` (never past what its cell holds
    at any turn) and moved within its cell as far as its reach leaves room; [(x, z, size)]."""
    width, depth = float(bed["size"][0]), float(bed["size"][2])
    # never more columns than plants: a lone plant on a long bed takes the whole bed, not the first of two cells
    columns = min(count, math.ceil(math.sqrt(count * width / depth)))
    rows = math.ceil(count / columns)
    half_x, half_z = width / columns / 2.0, depth / rows / 2.0
    low_x = float(bed["centre"][0]) - width / 2.0
    low_z = float(bed["centre"][2]) - depth / 2.0
    cells = [(column, row) for row in range(rows) for column in range(columns)][:count]
    found = []
    for column, row in cells:
        size = min(scale * (1.0 + generator.uniform(-SIZE_SPREAD, SIZE_SPREAD)),
                   (min(half_x, half_z) - ROUNDING) / reach)
        kept = max(reach * size, EDGE) + ROUNDING
        found.append((low_x + (2 * column + 1) * half_x + moved(half_x, half_x - kept, generator),
                      low_z + (2 * row + 1) * half_z + moved(half_z, half_z - kept, generator), size))
    return found


def layer_files(place):
    """crops-layer's files: crop_data.layer_files and the place's hand-in (its kinds' takes, takes_of)."""
    return {**crop_data.layer_files(place), "props": prop_data.keyed(place)}


def takes_of(inputs):
    """{row: its take} of the hand-in's objects (layer_files' "props")."""
    return {row: entry["take"] for row, entry in prop_data.record_at(inputs["props"])["objects"].items()}


def model_of(entry):
    """The name a kind's model is baked and laid by: its inventory row's, numbered as the assembly numbers models."""
    return f"{entry['row']}_1"


def laid_spots(beds, shared, spacings, footprints, seed):
    """Every plant: {kind, bed, at (x, top of the bed, z), turn (degrees), size (a factor)}, each kind's `spacings`
    metres apart on its beds at size 1, both sized to each bed its `footprints` (at size 1) would pass (bed_scale)."""
    generator = random.Random(seed)
    named = {bed["name"]: bed for bed in beds}
    spots = []
    for kind, bed_names in shared.items():
        reach = reach_of(footprints[kind])
        for name in bed_names:
            bed = named[name]
            top = float(bed["centre"][1]) + float(bed["size"][1]) / 2.0
            scale = bed_scale(bed, reach)
            for spot_x, spot_z, size in bed_spots(bed, bed_count(bed, spacings[kind] * scale), reach, scale,
                                                  generator):
                spots.append({"kind": kind, "bed": name, "at": [round(spot_x, 4), round(top, 4), round(spot_z, 4)],
                              "turn": round(generator.uniform(0.0, 360.0), 2),
                              "size": round(size, 6)})
    return spots


def left_out(record, bake, carried, takes):
    """{kind: [the carried batch gaps naming it]} of the kinds whose model the bake made none of and a batch gap names
    (by its row, its model or its take, `takes`: {row: take}, takes_of; the finish route's gaps name the
    take alone): the prop route left the take out inside the batch."""
    baked = json.loads((pathlib.Path(bake) / "baked.json").read_text())
    found = {}
    for kind, entry in record["kinds"].items():
        names = {entry["row"], model_of(entry), takes.get(entry["row"])}
        named = [gap["name"] for gap in carried if names & set(gap["objects"])]
        if model_of(entry) not in baked and named:
            found[kind] = named
    return found


def bare_gaps(record, left, shared):
    """The batch gap of each kind left out: its beds bare, named by the kind, its model and its beds."""
    return [batch_gaps.gap(f"{kind}: no model, its beds left bare", "crops-layer", "on beds",
                           (kind, model_of(record["kinds"][kind]), *shared[kind]),
                           [f"{kind}: {model_of(record['kinds'][kind])} was not baked ({'; '.join(names)})"],
                           "the prop route left its take out inside the batch, so no plant of it stands")
            for kind, names in sorted(left.items())]


def write_assets(record, bake, paint, out):
    """Each kind's baked model as an asset under out/assets (export.write_asset, as the assembly takes a bake);
    {kind: {model, lowest (its lowest y), width (its widest across the floor), footprint ([low x, high x, low z,
    high z] round its foot)}}."""
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
                       "width": max(float(high[0] - low[0]), float(high[2] - low[2])),
                       "footprint": [float(low[0]), float(high[0]), float(low[2]), float(high[2])]}
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
    with crop_data.tools("usd"):
        import whole_layer
    whole_layer.stamped(stage.GetRootLayer(), place).Save()


def make_layer(inputs, out, seed, params):
    """The crops layer, its kinds' assets and spots.json (the beds each kind took, every plant, each kind's model
    width and spacing in metres)."""
    record = crop_data.read(inputs)
    measured = json.loads((pathlib.Path(inputs["crops-concept"]) / "concept.json").read_text())["kinds"]
    carried = batch_gaps.of(inputs)
    left = left_out(record, inputs["surfaces-bake"], carried, takes_of(inputs))
    laid = dict(record, kinds={kind: entry for kind, entry in record["kinds"].items() if kind not in left})
    with crop_data.tools("usd"):
        assets = write_assets(laid, pathlib.Path(inputs["surfaces-bake"]), pathlib.Path(inputs["surfaces-paint"]),
                              out)
    beds = crop_data.beds_in(inputs, record)
    shared = shared_by_bed(record, beds, {kind: measured[kind]["share"] for kind in record["kinds"]})
    spacings = {kind: measured[kind]["spacing"] * assets[kind]["width"] for kind in laid["kinds"]}
    footprints = {kind: entry["footprint"] for kind, entry in assets.items()}
    spots = laid_spots(beds, {kind: shared[kind] for kind in laid["kinds"]}, spacings, footprints, seed)
    (out / "layers").mkdir(exist_ok=True)
    write_layer(record["place"], laid, assets, spots, out / LAYER)
    batch_gaps.write(out, [*carried, *bare_gaps(record, left, shared)])
    (out / "spots.json").write_text(json.dumps({"beds": shared, "spots": spots, "spacings": spacings,
                                                "widths": {kind: entry["width"] for kind, entry in assets.items()},
                                                "footprints": footprints}, indent=1))


def layer_faults(folder):
    present = (folder / LAYER).exists() and (folder / "spots.json").exists()
    return [] if present else [f"no {LAYER} or spots.json"]


def corners_of(spot, footprint):
    """A laid plant's footprint across the floor: its four corners [(x, z)], turned about the up axis (the layer's
    quaternion: x' = x cos + z sin, z' = z cos - x sin) and sized, at its spot."""
    turn = math.radians(spot["turn"])
    size = float(spot["size"])
    low_x, high_x, low_z, high_z = footprint
    return [(spot["at"][0] + size * (corner_x * math.cos(turn) + corner_z * math.sin(turn)),
             spot["at"][2] + size * (corner_z * math.cos(turn) - corner_x * math.sin(turn)))
            for corner_x, corner_z in ((low_x, low_z), (high_x, low_z), (high_x, high_z), (low_x, high_z))]


def overhang(corners, bed):
    """How far, metres, a footprint's farthest corner passes its bed's edge (0 or less: within it)."""
    return max(max(abs(corner_x - bed["centre"][0]) - bed["size"][0] / 2.0,
                   abs(corner_z - bed["centre"][2]) - bed["size"][2] / 2.0) for corner_x, corner_z in corners)


def pass_through(first, second):
    """Whether two footprints (convex, corners in order) overlap by more than TOUCH on every axis of their sides."""
    for shape in (first, second):
        for (start_x, start_z), (end_x, end_z) in zip(shape, shape[1:] + shape[:1]):
            axis = (start_z - end_z, end_x - start_x)
            length = math.hypot(*axis)
            if length == 0:
                continue
            ones = [(corner_x * axis[0] + corner_z * axis[1]) / length for corner_x, corner_z in first]
            others = [(corner_x * axis[0] + corner_z * axis[1]) / length for corner_x, corner_z in second]
            if min(max(ones), max(others)) - max(min(ones), min(others)) <= TOUCH:
                return False
    return True


def crossings(spots, footprints):
    """[(plant, plant)] of every two laid plants whose footprints pass through each other."""
    shapes = [corners_of(spot, footprints[spot["kind"]]) for spot in spots]
    lows = [min(corner[0] for corner in shape) for shape in shapes]
    highs = [max(corner[0] for corner in shape) for shape in shapes]
    order = sorted(range(len(spots)), key=lambda number: lows[number])
    found = []
    for place, number in enumerate(order):
        for other in order[place + 1:]:
            if lows[other] > highs[number]:
                break
            if pass_through(shapes[number], shapes[other]):
                found.append((min(number, other), max(number, other)))
    return found


def judge_on_beds(output, inputs, evidence):
    """Every plant stands on its bed, EDGE inside its edge, its footprint within the bed and through no other plant's;
    and every bed carries plants."""
    beds = {bed["name"]: bed for bed in crop_data.beds_in(inputs, crop_data.read(inputs))}
    laid_record = json.loads((output / "spots.json").read_text())
    spots, footprints = laid_record["spots"], laid_record["footprints"]
    failing = []
    for number, spot in enumerate(spots):
        bed = beds.get(spot["bed"])
        if bed is None:
            failing.append(f"plant {number} ({spot['kind']}): on {spot['bed']}, which is no bed of the plan")
            continue
        off_x = abs(spot["at"][0] - bed["centre"][0]) - (bed["size"][0] / 2.0 - EDGE)
        off_z = abs(spot["at"][2] - bed["centre"][2]) - (bed["size"][2] / 2.0 - EDGE)
        if max(off_x, off_z) > 0:
            failing.append(f"plant {number} ({spot['kind']}): {max(off_x, off_z) + EDGE:.3f} m off {spot['bed']}'s "
                           "edge")
        over = overhang(corners_of(spot, footprints[spot["kind"]]), bed)
        if over > TOUCH:
            failing.append(f"plant {number} ({spot['kind']}): overhangs {spot['bed']} by {over:.3f} m")
    failing += [f"plants {number} ({spots[number]['kind']}) and {other} ({spots[other]['kind']}): pass through each "
                "other" for number, other in crossings(spots, footprints)]
    bare = sorted(set(beds) - {spot["bed"] for spot in spots})
    failing += [f"{name}: no plants" for name in bare]
    return checks.Verdict("on beds", checks.FAIL if failing else checks.PASS,
                          f"{len(failing)} faults over {len(spots)} plants on {len(beds)} beds" if failing
                          else f"{len(spots)} plants on {len(beds)} beds", {"faults": len(failing)},
                          {"faults": "lower"}, tuple(failing[:40]))


def laid_spacing(spot, own, width, bed):
    """One laid plant's spacing in its laid widths (`width`, its kind's model width, times its size): the distance to
    the nearest plant of its kind on its own bed, the spacing the layer laid it at (how far apart the beds stand is
    the plan's); a plant alone on its bed, the side of the cell it was laid in, its bed's (the square root of its
    area)."""
    laid_width = width * float(spot["size"])
    others = [other for other in own if other is not spot and other["bed"] == spot["bed"]]
    if not others:  # alone; on no bed of the plan (`on beds` fails it), no cell to read
        return None if bed is None else math.sqrt(float(bed["size"][0]) * float(bed["size"][2])) / laid_width
    point = (spot["at"][0], spot["at"][2])
    return min(math.dist(point, (other["at"][0], other["at"][2])) for other in others) / laid_width


def laid_spacings(spots, widths, beds):
    """{kind: the median over its plants of each one's laid_spacing}, `beds` {name: bed}; a kind of under two plants
    has none."""
    found = {}
    for kind in sorted({spot["kind"] for spot in spots}):
        own = [spot for spot in spots if spot["kind"] == kind]
        if len(own) < 2:
            continue
        each = [laid_spacing(spot, own, widths[kind], beds.get(spot["bed"])) for spot in own]
        read = [value for value in each if value is not None]
        if read:
            found[kind] = statistics.median(read)
    return found


def judge_spacing(output, inputs, evidence):
    """Each kind's spacing in plant widths as laid within LAID_WITHIN of the concept's."""
    record = crop_data.read(inputs)
    measured = json.loads((pathlib.Path(inputs["crops-concept"]) / "concept.json").read_text())["kinds"]
    laid_record = json.loads((output / "spots.json").read_text())
    beds = {bed["name"]: bed for bed in crop_data.beds_in(inputs, record)}
    laid = laid_spacings(laid_record["spots"], laid_record["widths"], beds)
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
