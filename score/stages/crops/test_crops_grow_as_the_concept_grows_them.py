"""Crops grow as the locked concept grows them: the crop kinds and beds are read off the design alone (its inventory
and plan), the concept's plants are counted and spaced in plant widths on a known grid, laid on every bed at that
spacing, and gated (measured, on beds, spacing, boxed); a kind the prop route left out is a gap with its beds bare,
never a raise. No spend: a design of its own (a greenhouse of 25 beds, four crop kinds), SAM 3's boxes written here.

One world is grown through the stage's own steps: the design read into its kinds and beds; SAM 3's plants on the
concept's tiles mapped back and measured (the concept's own spacing, 1.5 widths, for every kind); laid on the beds at
that spacing; the layer written and the look's cameras, stage and count run on those beds. Each gate's cases are rows
of a table (input -> answer) fed through the gate.

The design and the concept, read:
  The rows that grow on the planter are the kinds, each asked by its name (a noun two kinds share is left out), the
  planter is the plot; the beds are the plan items the planter makes, in the place's frame on the lower floor; a
  design with no row growing on a bed has no crops. The first bed, plan item (0.3, 7.3) 0.6 m square on the 12 m
  plan, is at (-5.4, 1.6) in the place's frame, 0.06 m tall on the 0.4 m lower floor: its middle 0.43 up.
  Break: score/stages/crops/crop_data.py: `shared = any(row_kinds.words(other.get("noun")) == noun for other in crops
      if other is not row)` -> `shared = False`
  Break: score/stages/crops/crop_data.py: `round(floor + tall / 2, 4)` -> `round(tall / 2, 4)`
  The 3 x 2 tiles reach every edge of the picture; a plant found on a tile's picture (drawn UPSCALE larger) maps back
  to the whole picture at the tile's corner plus its box over UPSCALE, and one found on two tiles is kept once.
  Break: score/stages/crops/concept.py: `min(size[0], round(left + wide * (1 + OVERLAP)))` -> `min(size[0], round(left
      + wide))`
  Break: score/stages/crops/concept.py: `dict(instance, box=[left + instance["box"][0] / UPSCALE` -> `dict(instance,
      box=[left + instance["box"][0]`
  On a square plot seen square (no slant) a grid's spacing is its plants' distance over their width; a plant found
  twice (two tiles, or boxed twice) is kept once; a stray far off is left out. The lettuce's 36 plants in a 6 x 6 grid
  75 px apart cover 450 x 450 px of the 2000 px plot: 0.0506 of it.
  Break: score/stages/crops/concept.py: `"strays": len(own) - len(members)` -> `"strays": 0`
  Break: score/stages/crops/concept.py: `if not any(same_plant(instance["box"], other["box"])` -> `if True or not
      any(same_plant(instance["box"], other["box"])`
  Every kind found in a patch passes `measured`; a kind under FOUND_LEAST plants, found in none, or no plot, is
  unknown; a merged mass (a box over MERGED widths) is left out of its kind, not even counted a stray.
  Break: score/stages/crops/concept.py: `found["kinds"][kind]["count"] < FOUND_LEAST or found` -> `found`
  Break: score/stages/crops/concept.py: `return width(instance["box"]) > MERGED * statistics.median(` -> `return False
      and statistics.median(`

The layer:
  Laid at the concept's spacing every bed carries plants and both gates pass; laid at twice it spacing fails; a plant
  moved off its bed fails `on beds`. Greenhouse, 2026-11-04: one 2.3 m planter tray was laid on every bed of 0.47 x
  0.67 m, overhanging it and passing through its neighbours; now each plant is sized to its bed, in its proportions,
  and `on beds` fails a plant whose turned footprint overhangs its bed or passes through another's. Greenhouse,
  2026-11-06: a tray a bed, `spacing` read each lone tray to the next bed's (3.43 widths, the plan's distance, against
  the concept's 1.45), and a lone tray on a wide bed was laid in the first of two cells, at half the size its bed
  holds; now a plant's spacing is to its nearest neighbour on its own bed, a lone plant's its bed's side, and a bed
  never has more columns than plants.
  Break: score/stages/crops/layer.py: `elif abs(got - wanted) > LAID_WITHIN * wanted:` -> `elif False:`
  Break: score/stages/crops/layer.py: `if max(off_x, off_z) > 0:` -> `if False:`
  Break: score/stages/crops/layer.py: `return min(1.0, min(float(bed["size"][0]), float(bed["size"][2])) / 2.0 /
      reach)` -> `return 1.0`
  Break: score/stages/crops/layer.py: `if over > TOUCH:` -> `if False:`
  Break: score/stages/crops/layer.py: `for number, other in crossings(spots, footprints)]` -> `for number, other in
      []]`
  Break: score/stages/crops/layer.py: `laid_width = width * float(spot["size"])` -> `laid_width = width`
  Break: score/stages/crops/layer.py: `if other is not spot and other["bed"] == spot["bed"]]` -> `if other is not
      spot]`
  Break: score/stages/crops/layer.py: `columns = min(count, math.ceil(math.sqrt(count * width / depth)))` -> `columns
      = math.ceil(math.sqrt(count * width / depth))`
  crops-layer, try 4 of 2026-10-25: a kind whose take the prop route made a batch gap has no baked model, and the
  layer raised instead of carrying the gap. Now the kind is left out, its beds bare and named in a gap, and the
  table's `on beds` and `spacing` move its faults to that gap; a model missing with no gap naming it is no gap.
  Break: score/stages/crops/layer.py: `if model_of(entry) not in baked and named:` -> `if model_of(entry) not in
      baked:`
  Break: score/stages/crops/layer.py: `(kind, model_of(record["kinds"][kind]), *shared[kind]),` -> `(kind,
      model_of(record["kinds"][kind])),`
  Greenhouse, 2026-10-28: the finish route's split gap named the plants' take alone, and the layer raised.
  Break: score/stages/crops/layer.py: `names = {entry["row"], model_of(entry), takes.get(entry["row"])}` ->
      `names = {entry["row"], model_of(entry)}`
  Each kind's prototype says what made it (score:kind), so the made-only check passes the laid crop meshes; without
  the mark it fails them, as it did on complete@greenhouse of 2026-10-17.
  Break: score/stages/crops/layer.py: `prototype.GetPrim().CreateAttribute("score:kind",
      Sdf.ValueTypeNames.String).Set(KIND)` -> `pass`

The look:
  A point of the beds' top drawn by a look camera (projected here by the camera's own geometry) is taken back onto it,
  and it falls inside the picture; a look framing a plant laid far past the beds (a wide plant's reach) steps back
  until that plant and every bed corner are in the picture (crops-look@greenhouse, 2026-11-03: at 6.5 m its 2.3 m
  trays ran off the picture, 3 of 11 seen).
  Break: score/stages/crops/look.py: `rise = (size[1] / 2 - pixel[1]) / (size[0] / 2) * half_wide` -> `rise = (size[1]
      / 2 - pixel[1]) / (size[1] / 2) * half_wide`
  Break: score/stages/crops/look.py: `points = [*bed_corners(beds), *framed]` -> `points = bed_corners(beds)`
  crops-look@greenhouse, try 4 of 2026-10-25: its beds are plan items named 'PLANTER BED 1', no prim name, so the
  stage build raised before the card was rented. Each bed's prim is a valid identifier, its name kept. Each bed is a
  mesh of its own corners with no xform op (2026-11-03: Blender stood the scaled cubes up, their depth their height),
  as wide, tall and deep as its plan box, its faces wound outward.
  Break: score/stages/crops/look.py: `prims = [Tf.MakeValidIdentifier(bed["name"]) for bed in beds]` -> `prims =
      [bed["name"] for bed in beds]`
  Break: score/stages/crops/look.py: `float(bed["centre"][1]) + side_y * float(bed["size"][1]) / 2.0` ->
      `float(bed["centre"][1]) + side_y * float(bed["size"][2]) / 2.0`
  Break: score/stages/crops/look.py: `BOX_FACES = (0, 1, 3, 2,` -> `BOX_FACES = (0, 2, 3, 1,`
  A plant found by any kind's noun, twice, is one plant of the kind laid on the bed it stands on (the herb's bed here,
  though one box was found as 'leafy bush'): its box's middle taken back onto the level of its own middle, a 0.5 m
  tall herb's 0.25 m over the bed's top (taken onto the top it lands 0.36 m behind, off its 0.6 m bed).
  Break: score/stages/crops/look.py: `bed_under(spot, shared[kind], beds)) for spot` -> `bed_under(spot, list(beds),
      beds)) for spot`
  Break: score/stages/crops/look.py: `level = top + heights.get(kind, 0.0) * (statistics.median(sizes) if sizes else
      1.0) / 2.0` -> `level = top`
  Greenhouse, 2026-11-06: a tray a bed, `density` would read each lone tray's spacing to the next bed's (about 5
  widths against the concept's 1.45) in one laid width for trays sized 0.15 to 0.5; now a seen plant's spacing is to
  the nearest seen plant on its own bed, a lone one's its bed's side, each in its laid width on its bed.
  Break: score/stages/crops/look.py: `if number != index and other_name == name]` -> `if number != index]`
  Break: score/stages/crops/look.py: `if spot["kind"] == kind and spot["bed"] == name] or sizes` -> `if
      spot["kind"] == kind] or sizes`
  A batch job runs on its one priced class; no stock is a gap, never a larger card (#21).
  Break: score/stages/crops/look.py: `CARDS = "gpu-24gb"` -> `CARDS = "gpu-24gb,gpu-48gb"`

The boxes:
  2026-10-22 benchmark: crops-boxes read the retired page-A inventory, found nothing to mask and still rented a card.
  Off the design, a crop row SAM 3 boxed in the reading passes as it stands, with no mask job and no rent; a crop row
  whose reading box is Gemini's region is SAM 3's job again, on the locked concept, and until decided the gate is
  unknown, never a pass.
  Break: score/stages/crops/boxes.py: `if rows[name].get("box") and rows[name].get("boxed_by") == GEMINI]` -> `if
      rows[name].get("box")]`
  Break: score/stages/crops/boxes.py: `else checks.UNKNOWN if failing else checks.PASS)` -> `else checks.PASS)`

Each break was applied once and seen red.

Run: PROPS_HOME=$(mktemp -d) .venv/bin/python -m pytest score/stages/crops/test_crops_grow_as_the_concept_grows_them.py
"""
import json
import math
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
import score.stages.crops.boxes as boxes  # noqa: E402
import score.stages.crops.concept as concept  # noqa: E402
import score.stages.crops.crop_data as crop_data  # noqa: E402
import score.stages.crops.layer as layer  # noqa: E402
import score.stages.crops.look as look  # noqa: E402
from score import checks  # noqa: E402
from score.stages import row_kinds  # noqa: E402

KINDS = row_kinds.table()


def crop_row(row_id, name, noun="crops"):
    return {"id": row_id, "name": name, "noun": noun, "count": 5, "anchor": "on:planter_bed", "size": [0.5, 0.5, 0.3]}


# A design as the reading keeps it: a planter bed row on the lower floor, four crop rows on it, a door and a lamp.
INVENTORY = {"scene": "greenhouse", "place": "greenhouse", "rows": [
    {"id": "planter_bed", "name": "raised planter bed", "noun": "planter", "count": 25, "anchor": "on:lower_floor",
     "size": [0.6, 0.6, 0.06]},
    crop_row("lettuce", "lettuce"), crop_row("potato", "potato"), crop_row("herb", "rosemary"),
    crop_row("greens", "leafy bush", "plants"),
    {"id": "door", "name": "sliding door", "noun": "door", "count": 1, "anchor": "wall", "size": [1.2, 0.1, 2.2]},
    {"id": "wall_lamp", "name": "wall lamp", "noun": "lamp", "count": 2, "anchor": "wall", "size": [0.3, 0.3, 0.3]}]}
# Its plan: 25 beds, 0.6 m squares in a 5 x 5 grid, on a 12 m room whose lower floor is 0.4 m up; a lamp item.
PLAN = {"w": 12.0, "d": 12.0, "levels": [{"name": "lower floor", "height": 0.4, "points": []}],
        "items": [[f"PLANTER BED {column}_{row}", 0.3 + 0.6 * column, 1.3 - 0.6 * row + 6.0, 0.6, 0.6, None, "item"]
                  for column in range(5) for row in range(5)] + [["WALL LAMP 1", 0.0, 0.0, 0.3, 0.3, None, "item"]],
        "rows": {**{f"PLANTER BED {column}_{row}": ["planter_bed"] for column in range(5) for row in range(5)},
                 "WALL LAMP 1": ["wall_lamp"]}}

PICTURE = [2000, 2000]  # the concept's view, its plot seen square (no slant)
PLOT = {"plot:raised garden bed": [{"box": [0, 0, 2000, 2000], "score": 0.9, "inside": 1.0, "fills": 1.0}]}
SQUARE = [-0.1, 0.1, -0.1, 0.1]  # a plant 0.2 m wide, its foot in its middle
TRAY = [-1.15, 1.15, -0.4, 0.4]  # the greenhouse's planter tray, 2.3 m long, on beds of 0.6 m


def grid(origin, count, spacing, width):
    """count x count plant boxes `spacing` pixels apart and `width` wide, as SAM 3 would give them."""
    half = width / 2
    return [{"box": [origin[0] + column * spacing - half, origin[1] + row * spacing - half,
                     origin[0] + column * spacing + half, origin[1] + row * spacing + half], "score": 0.9}
            for row in range(count) for column in range(count)]


# SAM 3's plants on the concept, every kind 1.5 of its widths apart: lettuce 6 x 6, found twice 2 px apart; potato,
# herb and greens 3 x 3; a herb stray far off; a merged mass of greens.
LETTUCE = grid((550, 550), 6, 75, 50)
SEEN = {"lettuce:lettuce": LETTUCE + [dict(plant, box=[value + 2 for value in plant["box"]]) for plant in LETTUCE],
        "potato:potato": grid((1300, 1300), 3, 30, 20),
        "herb:rosemary": grid((200, 1500), 3, 12, 8) + [{"box": [1900, 100, 1908, 108], "score": 0.9}],
        "greens:leafy bush": grid((1300, 200), 3, 12, 8) + [{"box": [1150, 600, 1450, 800], "score": 0.9}]}


def on_tiles(seen, tiles):
    """SAM 3's answer on the tiles: each plant on every tile its middle lies on, in that tile's upscaled picture."""
    found = {}
    for key, listed in seen.items():
        for instance in listed:
            middle = concept.centre(instance["box"])
            for number, tile in enumerate(tiles):
                if concept.inside(middle, tile):
                    found.setdefault(f"{number}/{key}", []).append(dict(instance, box=[
                        (instance["box"][index] - tile[index % 2]) * concept.UPSCALE for index in range(4)]))
    return found


# The concept's cases: (id, SAM 3's plants on the tiles, `measured`'s answer).
MEASURED = [
    ("every kind in a patch", SEEN, checks.PASS),
    ("a kind in a patch under FOUND_LEAST", dict(SEEN, **{"potato:potato": SEEN["potato:potato"][:2]
                                                          + SEEN["potato:potato"][3:5]}), checks.UNKNOWN),
    ("a kind found in none", {key: value for key, value in SEEN.items() if key != "potato:potato"}, checks.UNKNOWN),
]


def moved_off(spots):
    spots[0]["at"][0] += 1.0


def past_its_edge(spots):
    spots[0]["size"] *= 1.5  # centre still on its bed, the plant past its edge


def on_its_neighbour(spots):
    first, second = [spot for spot in spots if spot["bed"] == spots[0]["bed"]][:2]
    second["at"] = [first["at"][0] + 0.05, first["at"][1], first["at"][2] + 0.02]  # within its bed, on its neighbour


# The layer's cases: (id, footprint, times the concept's spacing laid, a change to the laid spots, the gate, its
# answer, a word its findings hold).
LAID = [
    ("at the concept's spacing", SQUARE, 1.0, None, "on beds", checks.PASS, ""),
    ("at the concept's spacing", SQUARE, 1.0, None, "spacing", checks.PASS, ""),
    ("trays sized to their beds", TRAY, 1.0, None, "on beds", checks.PASS, ""),
    ("at twice the concept's spacing", SQUARE, 2.0, None, "spacing", checks.FAIL, "plant widths apart"),
    ("a plant moved off its bed", SQUARE, 1.0, moved_off, "on beds", checks.FAIL, "edge"),
    ("a tray past its bed's edge", TRAY, 1.0, past_its_edge, "on beds", checks.FAIL, "overhangs"),
    ("a plant on its neighbour", SQUARE, 1.0, on_its_neighbour, "on beds", checks.FAIL, "pass through"),
]

WIDE = {"name": "wide", "row": "planter_bed", "centre": [0.0, 0.43, 0.0], "size": [2.05, 0.06, 1.685]}
SMALL = {"name": "small", "row": "planter_bed", "centre": [2.68, 0.43, 0.0], "size": [0.473, 0.06, 0.674]}
LONG = {"name": "long", "row": "planter_bed", "centre": [0.0, 0.43, 0.0], "size": [0.6, 0.06, 3.0]}
# Trays at the concept's 1.45 on beds of their own shape: (id, beds, the beds its trays stand on, in order, the
# first tray's size above).
BED_SHAPES = [
    ("a long bed holds a row of trays", [LONG], ["long"] * 3, 0.0),
    ("a lone tray fills its whole bed", [WIDE, SMALL], ["wide", "small"], 0.6),
]


def gap_of(name, route, check, objects, findings, note):
    from score.stages import batch_gaps
    return batch_gaps.gap(name, route, check, objects, findings, note)


# Which kinds the prop route left out: (id, the carried batch gaps, the takes, {kind: the gaps naming it}).
LEFT_OUT = [
    ("a missing model no gap names", [], {"potato": "potato_a1"}, {}),
    ("a split gap naming its take alone",
     [gap_of("potato_a1: not one finish a face", "finish-route-split", "one finish a face", ("potato_a1",),
             ["views disagree"], "")], {"potato": "potato_a1"}, {"potato": ["potato_a1: not one finish a face"]}),
    ("a pixal gap naming its kind",
     [gap_of("potato: Pixal3D made no model", "pixal", "takes", ("potato",), ["potato: no model"], "the job ran once")],
     {}, {"potato": ["potato: Pixal3D made no model"]}),
]

# The boxes' cases: (id, the crop rows the reading framed by Gemini's region, the rows masked again, `boxed`).
BOXED = [
    ("every crop row boxed by SAM 3", (), [], checks.PASS),
    ("one crop row framed by Gemini", ("potato",), ["potato"], checks.UNKNOWN),
]


def design_inputs(folder):
    """The design's files as a crop row reads them: its inventory (every row boxed by the reading, Gemini's region
    for `gemini`), plan, the row-kind rules and the concept."""
    folder.mkdir(parents=True, exist_ok=True)
    rows = [dict(row, box=[10, 10, 40, 40]) for row in INVENTORY["rows"]]
    (folder / "inventory.json").write_text(json.dumps(dict(INVENTORY, rows=rows)))
    (folder / "plan.json").write_text(json.dumps(PLAN))
    return {"inventory": folder / "inventory.json", "plan": folder / "plan.json", "row kinds": row_kinds.TABLE,
            "concept": folder / "concept.png"}


def projected(view, point, size):
    """Where a point of the stage falls in a look camera's picture (x, y from the top left, pixels): usd_views.py's
    camera, `fov` across the picture's width, the inverse of look.on_floor."""
    eye, aim = np.asarray(view["eye"], dtype=float), np.asarray(view["aim"], dtype=float)
    ahead = (aim - eye) / np.linalg.norm(aim - eye)
    right = np.cross(ahead, [0.0, 1.0, 0.0])
    right /= np.linalg.norm(right)
    up = np.cross(right, ahead)
    way = np.asarray(point, dtype=float) - eye
    depth = float(way @ ahead)
    half_wide = math.tan(math.radians(view["fov"]) / 2)
    return (size[0] / 2 * (1 + float(way @ right) / depth / half_wide),
            size[1] / 2 - float(way @ up) / depth / half_wide * size[0] / 2)


def in_picture(view, point):
    pixel = projected(view, point, look.SIZE)
    return 0 <= pixel[0] < look.SIZE[0] and 0 <= pixel[1] < look.SIZE[1]


def lay(folder, record, beds, spacing, footprint, kinds):
    """`kinds` laid on the design's beds `spacing` of their widths apart, plants of `footprint`: spots.json."""
    shared = layer.shared_by_bed(record, beds, {kind: 1.0 for kind in record["kinds"]})
    width = max(footprint[1] - footprint[0], footprint[3] - footprint[2])
    spots = layer.laid_spots(beds, {kind: shared[kind] for kind in kinds},
                             {kind: spacing[kind] * width for kind in kinds}, {kind: footprint for kind in kinds}, 7)
    (folder / "spots.json").write_text(json.dumps({"beds": shared, "spots": spots,
                                                   "widths": {kind: width for kind in record["kinds"]},
                                                   "footprints": {kind: footprint for kind in record["kinds"]}}))
    return shared, spots


def changed(folder, change):
    laid_record = json.loads((folder / "spots.json").read_text())
    change(laid_record["spots"])
    (folder / "spots.json").write_text(json.dumps(laid_record))


def test_crops_grow_as_the_concept_grows_them(tmp_path):
    from pxr import Sdf, Usd, UsdGeom

    from score import stages
    from score.stages import batch_gaps
    inputs = design_inputs(tmp_path / "design")

    # The design, read: its kinds, its plot and its beds.
    record = crop_data.read(inputs)
    assert record == crop_data.record_of(INVENTORY, KINDS)
    assert list(record["kinds"]) == ["lettuce", "potato", "herb", "greens"], record["kinds"]
    assert record["kinds"]["lettuce"] == {"row": "lettuce", "nouns": ["lettuce"], "bed": "planter_bed"}
    assert record["kinds"]["greens"]["nouns"] == ["leafy bush", "plants"], record["kinds"]["greens"]
    assert record["beds"] == ["planter_bed"] and record["concept"]["plot"]["nouns"] == ["raised planter bed", "planter"]
    assert record["place"] == "greenhouse" and record["concept"]["view"] == crop_data.DESIGN_VIEW
    beds = crop_data.beds_in(inputs, record)
    assert beds == crop_data.beds_of(PLAN, INVENTORY, record)
    assert len(beds) == 25 and {bed["row"] for bed in beds} == {"planter_bed"}, beds
    assert beds[0]["name"] == "PLANTER BED 0_0" and beds[0]["size"] == [0.6, 0.06, 0.6], beds[0]
    assert beds[0]["centre"] == [-5.4, 0.43, 1.6], beds[0]
    bare = dict(INVENTORY, rows=[row for row in INVENTORY["rows"] if row["id"] in ("planter_bed", "door")])
    assert crop_data.record_of(bare, KINDS)["kinds"] == {}

    # The concept, measured on its tiles.
    tiles = concept.tile_boxes(PICTURE)
    assert len(tiles) == concept.TILES[0] * concept.TILES[1]
    assert min(box[0] for box in tiles) == 0 and max(box[2] for box in tiles) == PICTURE[0]
    assert min(box[1] for box in tiles) == 0 and max(box[3] for box in tiles) == PICTURE[1]
    jobs = concept.jobs_of(record, "K09.png", PICTURE,
                           [(f"tile-{number}.png", box) for number, box in enumerate(tiles)])
    assert all(row["key"].startswith("plot:") for row in jobs[0]["rows"]) and len(jobs) == len(tiles) + 1
    assert any(row["key"] == "1/lettuce:lettuce" for row in jobs[2]["rows"])
    for name, seen, answer in MEASURED:
        folder = tmp_path / "concept" / name
        folder.mkdir(parents=True)
        found = concept.measures(record, concept.on_picture({**PLOT, **on_tiles(seen, tiles)}, tiles), PICTURE)
        (folder / "concept.json").write_text(json.dumps(found))
        verdict = concept.judge_measured(folder, inputs, None)
        assert verdict.answer == answer, (name, verdict)
    no_plot = concept.measures(record, concept.on_picture(on_tiles(SEEN, tiles), tiles), PICTURE)
    (folder / "concept.json").write_text(json.dumps(no_plot))
    assert no_plot["plot"] is None and concept.judge_measured(folder, inputs, None).answer == checks.UNKNOWN
    measured = tmp_path / "concept" / MEASURED[0][0]
    kinds = json.loads((measured / "concept.json").read_text())["kinds"]
    assert {kind: (kinds[kind]["count"], kinds[kind]["strays"]) for kind in kinds} == {
        "lettuce": (36, 0), "potato": (9, 0), "herb": (9, 1), "greens": (9, 0)}, kinds
    assert all(abs(kinds[kind]["spacing"] - 1.5) < 0.01 for kind in kinds), kinds
    assert abs(kinds["lettuce"]["share"] - 450 ** 2 / 2000 ** 2) < 0.001, kinds["lettuce"]
    spacing = {kind: kinds[kind]["spacing"] for kind in kinds}

    # The layer: laid on the design's beds at the concept's spacing, and gated.
    inputs = {**inputs, "crops-concept": measured}
    own = {check.name: check for check in layer.CHECKS}  # the gates as written; `gated` as the stage table runs them
    gated = {check.name: check for row in stages.STAGES if row.name == "crops-layer" for check in row.checks}
    for number, (name, footprint, times, change, gate, answer, word) in enumerate(LAID):
        folder = tmp_path / "laid" / str(number)
        folder.mkdir(parents=True)
        shared, spots = lay(folder, record, beds, {kind: times * spacing[kind] for kind in kinds}, footprint, kinds)
        assert sorted(name for names in shared.values() for name in names) == sorted(bed["name"] for bed in beds)
        named = {bed["name"]: bed for bed in beds}
        assert all(layer.overhang(layer.corners_of(spot, footprint), named[spot["bed"]]) <= 0 for spot in spots), name
        sizes = [spot["size"] for spot in spots]
        assert max(sizes) / min(sizes) <= (1 + layer.SIZE_SPREAD) / (1 - layer.SIZE_SPREAD) + 1e-9, (name, sizes)
        if change:
            changed(folder, change)
        verdict = own[gate].judge(folder, inputs, None)
        assert verdict.answer == answer and (not word or any(word in finding for finding in verdict.findings)), \
            (name, verdict)
    laid_trays = layer.judge_spacing(tmp_path / "laid" / "2", inputs, None).measures
    assert min(laid_trays.values()) > 1.0, laid_trays  # in each tray's laid width: in its 2.3 m model's, 0.26
    shaped_trays = {}
    for name, shaped, standing, least in BED_SHAPES:
        trays = layer.laid_spots(shaped, {"greens": [bed["name"] for bed in shaped]}, {"greens": 1.45 * 2.3},
                                 {"greens": TRAY}, 7)
        named = {bed["name"]: bed for bed in shaped}
        assert [spot["bed"] for spot in trays] == standing, (name, trays)
        assert all(layer.overhang(layer.corners_of(spot, TRAY), named[spot["bed"]]) <= 0 for spot in trays), name
        assert trays[0]["size"] > least, (name, trays)  # a lone tray its whole bed's size
        laid = layer.laid_spacings(trays, {"greens": 2.3}, named)["greens"]
        assert abs(laid - 1.45) <= layer.LAID_WITHIN * 1.45, (name, laid)  # each as far apart as its own bed gives it
        shaped_trays[name] = trays
    lone = shaped_trays[BED_SHAPES[1][0]]

    # A kind the prop route left out: its beds bare and named in a gap.
    bake = tmp_path / "bake"
    bake.mkdir()
    (bake / "baked.json").write_text(json.dumps({layer.model_of(entry): {} for kind, entry in record["kinds"].items()
                                                 if kind != "potato"}))
    (tmp_path / "props.json").write_text(json.dumps({"objects": {"potato": {"route": "prop", "take": "potato_a1"}}}))
    for name, carried, takes, left in LEFT_OUT:
        named_takes = layer.takes_of({"props": tmp_path / "props.json"}) if takes else {}
        assert named_takes == takes, name
        assert layer.left_out(record, bake, carried, named_takes) == left, name
    folder, pixal = tmp_path / "gapped", tmp_path / "pixal"
    folder.mkdir(), pixal.mkdir()
    batch_gaps.write(pixal, LEFT_OUT[2][1])
    left = layer.left_out(record, bake, batch_gaps.read([pixal]), {})
    shared = lay(folder, record, beds, spacing, SQUARE, [kind for kind in kinds if kind not in left])[0]
    gapped = {**inputs, "pixal": pixal}
    for gate in ("on beds", "spacing"):
        assert own[gate].judge(folder, gapped, None).answer == checks.FAIL, gate  # the gate's own answer stands
    batch_gaps.write(folder, [*batch_gaps.read([pixal]), *layer.bare_gaps(record, left, shared)])
    for gate in ("on beds", "spacing"):
        verdict = gated[gate].judge(folder, gapped, None)
        assert verdict.answer == checks.PASS and "moved to complete as accepted gaps" in verdict.reason, verdict
    changed(folder, moved_off)  # a laid kind's own fault is no gap's
    assert gated["on beds"].judge(folder, gapped, None).answer == checks.FAIL

    # The layer written: each kind's prototype says what made it.
    crops = tmp_path / "crops"
    (crops / "assets").mkdir(parents=True)
    assets = {}
    for kind, entry in record["kinds"].items():
        model = layer.model_of(entry)
        asset = Usd.Stage.CreateNew(str(crops / "assets" / f"{model}.usdc"))
        asset.SetDefaultPrim(UsdGeom.Xform.Define(asset, f"/{model}").GetPrim())
        UsdGeom.Mesh.Define(asset, f"/{model}/geo")
        asset.GetRootLayer().Save()
        assets[kind] = {"model": model, "lowest": 0.0}
    (crops / layer.LAYER).parent.mkdir(parents=True, exist_ok=True)
    laid_square = json.loads((tmp_path / "laid" / "0" / "spots.json").read_text())
    layer.write_layer("greenhouse", record, assets, laid_square["spots"], crops / layer.LAYER)
    stage = Usd.Stage.CreateInMemory()
    stage.GetRootLayer().subLayerPaths.append(str(crops / layer.LAYER))
    stage.SetDefaultPrim(UsdGeom.Xform.Define(stage, "/greenhouse").GetPrim())
    with crop_data.tools("usd"):
        import made_only
    assert made_only.unmade_meshes(stage) == [], made_only.unmade_meshes(stage)
    stage.SetEditTarget(Usd.EditTarget(Sdf.Layer.Find(str(crops / layer.LAYER))))
    for kind in record["kinds"]:
        prototype = stage.GetPrimAtPath(f"/greenhouse/Crops/{kind}/Prototypes/{assets[kind]['model']}")
        assert prototype.GetChild("geo").IsValid(), kind
        prototype.RemoveProperty("score:kind")
    assert len(made_only.unmade_meshes(stage)) == len(record["kinds"])

    # The look: its cameras, its stage of the beds and its count, on one priced card class.
    assert "," not in look.CARDS, look.CARDS
    for view in look.views_of(beds):
        for point in ((-5.4, 0.46, 1.6), (-3.0, 0.46, -0.8), (-4.2, 0.46, 0.4)):
            back = look.on_floor(view, projected(view, point, look.SIZE), look.SIZE, 0.46)
            assert math.dist(back, (point[0], point[2])) < 1e-6, (view["name"], point, back)
            assert in_picture(view, point), (view["name"], point)
    framed = look.plant_reach({"spots": [{"kind": "greens", "at": [3.0, 0.46, 6.0], "size": 1.0}],
                               "widths": {"greens": 2.3}}, {"greens": 0.4})
    for view in look.views_of(beds, framed):
        assert math.dist(view["eye"], view["aim"]) > look.AWAY, view
        assert all(in_picture(view, point) for point in [*framed, *look.bed_corners(beds)]), view["name"]
    (tmp_path / "blank" / "assets").mkdir(parents=True)
    (tmp_path / "blank" / layer.LAYER).parent.mkdir(parents=True, exist_ok=True)
    blank = Usd.Stage.CreateNew(str(tmp_path / "blank" / layer.LAYER))
    blank.GetRootLayer().Save()
    stage = Usd.Stage.Open(str(look.beds_stage("greenhouse", beds, tmp_path / "blank", tmp_path / "look")))
    meshes = [prim for prim in stage.Traverse() if prim.GetTypeName() == "Mesh"]
    names = sorted(prim.GetAttribute("score:name").Get() for prim in meshes)
    assert names == sorted(bed["name"] for bed in beds) and " " in names[0], names
    by_name = {bed["name"]: bed for bed in beds}
    for prim in meshes:
        mesh = UsdGeom.Mesh(prim)
        assert not mesh.GetOrderedXformOps(), prim.GetPath()
        points = np.asarray(mesh.GetPointsAttr().Get(), dtype=float)
        bed = by_name[prim.GetAttribute("score:name").Get()]
        assert np.allclose(points.max(axis=0) - points.min(axis=0), bed["size"], atol=1e-5), (bed, points)
        assert np.allclose((points.max(axis=0) + points.min(axis=0)) / 2, bed["centre"], atol=1e-5), (bed, points)
        indices, middle = list(mesh.GetFaceVertexIndicesAttr().Get()), points.mean(axis=0)
        for face in range(len(indices) // 4):
            corner = points[indices[4 * face:4 * face + 4]]
            assert np.cross(corner[1] - corner[0], corner[2] - corner[0]) @ (corner.mean(axis=0) - middle) > 0, \
                (prim.GetPath(), face)
    view = look.views_of(beds)[0]
    middle_x, middle_y = projected(view, (-5.4, 0.46 + 0.25, 1.6), look.SIZE)
    box = [middle_x - 20, middle_y - 60, middle_x + 20, middle_y + 60]
    herb_bed = {kind: [] for kind in record["kinds"]}
    herb_bed["herb"] = ["PLANTER BED 0_0"]
    seen = look.seen_on_beds(record, view, {f"{view['name']}/greens:leafy bush": [{"box": box, "score": 0.8}],
                                            f"{view['name']}/herb:rosemary": [{"box": [value + 1 for value in box],
                                                                               "score": 0.7}]},
                             by_name, herb_bed, {"spots": [], "widths": {kind: 0.2 for kind in record["kinds"]}},
                             {kind: 0.5 for kind in record["kinds"]})
    assert seen["herb"]["seen"] == 1 and seen["greens"]["seen"] == 0, seen
    trays_record = {"spots": lone, "widths": {"greens": 2.3}}
    widths = look.laid_widths("greens", 2.3, ["wide", "small"], lone)
    assert abs(widths["wide"] - 2.3 * lone[0]["size"]) < 1e-9, widths  # each bed's own tray size, not the kind's
    level = 0.46 + 0.4 * (lone[0]["size"] + lone[1]["size"]) / 4.0  # the beds' top plus half the trays' median height
    view = look.views_of([WIDE, SMALL], look.plant_reach(trays_record, {"greens": 0.4}))[0]
    middles = [projected(view, (spot["at"][0], level, spot["at"][2]), look.SIZE) for spot in lone]
    found = {f"{view['name']}/greens:leafy bush": [{"box": [pixel_x - 8, pixel_y - 8, pixel_x + 8, pixel_y + 8],
                                                     "score": 0.9} for pixel_x, pixel_y in middles]}
    greens_beds = {kind: [] for kind in record["kinds"]}
    greens_beds["greens"] = ["wide", "small"]
    seen = look.seen_on_beds(record, view, found, {"wide": WIDE, "small": SMALL}, greens_beds, trays_record,
                             {kind: 0.4 for kind in record["kinds"]})["greens"]
    assert seen["seen"] == 2 and abs(seen["spacing"] - 1.45) <= look.SEEN_WITHIN * 1.45, seen

    # The boxes: a crop row SAM 3 boxed in the reading passes as it stands; one Gemini framed is masked again.
    for name, gemini, masked, answer in BOXED:
        folder = tmp_path / "boxes" / name
        boxed = design_inputs(folder)
        rows = [dict(row, **({"boxed_by": boxes.GEMINI} if row["id"] in gemini else {}))
                for row in json.loads(boxed["inventory"].read_text())["rows"]]
        boxed["inventory"].write_text(json.dumps(dict(INVENTORY, rows=rows)))
        jobs = boxes.to_mask(boxed)
        assert [row["key"] for job in jobs for row in job["rows"]] == masked, (name, jobs)
        assert all(job["picture"] == str(boxed["concept"]) and row["keep"] == boxes.KEEP
                   and row["nouns"] == record["kinds"][row["key"]]["nouns"] for job in jobs for row in job["rows"])
        out = folder / "out"
        out.mkdir()
        if jobs:  # SAM 3's measure is the rented card's: until it decides, the reading's rows alone are decided
            (out / "decided.json").write_text(json.dumps({"decided": {row: boxes.IN_READING for row in record["kinds"]
                                                                      if row not in masked}}))
        else:
            boxes.make_boxes(boxed, out, 1, {})  # a rent here would need a cleared run and fail
        assert not (out / "mask-jobs.json").exists(), name
        verdict = boxes.judge_boxed(out, boxed, None)
        assert verdict.answer == answer and all(finding.startswith(tuple(masked)) for finding in verdict.findings), \
            (name, verdict)
