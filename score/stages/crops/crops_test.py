"""The crops stage's free parts on a design of its own: the crop kinds and beds read off a scene inventory and plan,
the concept's tiles and measures on a known grid of plants, the gates, and the look's camera round trip.

    .venv/bin/python score/stages/crops/crops_test.py
"""
import json
import math
import pathlib
import sys
import tempfile

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
RECORD = crop_data.record_of(INVENTORY, KINDS)
BEDS = crop_data.beds_of(PLAN, INVENTORY, RECORD)


def design_inputs(folder):
    """The design's files as a crop row reads them: its inventory, plan and the row-kind rules."""
    (folder / "inventory.json").write_text(json.dumps(INVENTORY))
    (folder / "plan.json").write_text(json.dumps(PLAN))
    return {"inventory": folder / "inventory.json", "plan": folder / "plan.json", "row kinds": row_kinds.TABLE}


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
    return size[0] / 2 * (1 + float(way @ right) / depth / half_wide), size[1] / 2 - float(way @ up) / depth / half_wide * size[0] / 2


def test_crop_kinds_and_beds_come_from_the_design():
    """The rows that grow on the planter are the kinds, each asked by its name (a noun two kinds share is left out),
    the planter is the plot; the beds are the plan items the planter makes, in the place's frame on the lower floor;
    a design with no row growing on a bed has no crops."""
    assert list(RECORD["kinds"]) == ["lettuce", "potato", "herb", "greens"], RECORD["kinds"]
    assert RECORD["kinds"]["lettuce"] == {"row": "lettuce", "nouns": ["lettuce"], "bed": "planter_bed"}
    assert RECORD["kinds"]["greens"]["nouns"] == ["leafy bush", "plants"], RECORD["kinds"]["greens"]
    assert RECORD["beds"] == ["planter_bed"] and RECORD["concept"]["plot"]["nouns"] == ["raised planter bed", "planter"]
    assert RECORD["place"] == "greenhouse" and RECORD["concept"]["view"] == crop_data.DESIGN_VIEW
    assert len(BEDS) == 25 and {bed["row"] for bed in BEDS} == {"planter_bed"}, BEDS
    first = BEDS[0]
    assert first["name"] == "PLANTER BED 0_0" and first["size"] == [0.6, 0.06, 0.6], first
    assert first["centre"] == [-5.4, 0.43, 1.6], first
    bare = dict(INVENTORY, rows=[row for row in INVENTORY["rows"] if row["id"] in ("planter_bed", "door")])
    assert crop_data.record_of(bare, KINDS)["kinds"] == {}


SQUARE_PLOT = {"plot:raised garden bed": [{"box": [0, 0, 2000, 2000], "score": 0.9, "inside": 1.0, "fills": 1.0}]}


def grid(kind, noun, origin, count, spacing, width=8):
    """count x count plants of one kind, `spacing` pixels apart and `width` wide, as SAM 3 would give them."""
    half = width / 2
    return {f"{kind}:{noun}": [{"box": [origin[0] + column * spacing - half, origin[1] + row * spacing - half,
                                        origin[0] + column * spacing + half, origin[1] + row * spacing + half],
                                "score": 0.9, "inside": 1.0, "fills": 0.0}
                               for row in range(count) for column in range(count)]}


def test_tiles_cover_the_picture_and_map_back():
    size = [2752, 1536]
    tiles = concept.tile_boxes(size)
    assert len(tiles) == concept.TILES[0] * concept.TILES[1]
    assert min(box[0] for box in tiles) == 0 and max(box[2] for box in tiles) == size[0]
    assert min(box[1] for box in tiles) == 0 and max(box[3] for box in tiles) == size[1]
    jobs = concept.jobs_of(RECORD, "K09.png", size, [(f"tile-{number}.png", box) for number, box in enumerate(tiles)])
    assert all(row["key"].startswith("plot:") for row in jobs[0]["rows"]) and len(jobs) == len(tiles) + 1
    assert any(row["key"] == "1/lettuce:lettuce" for row in jobs[2]["rows"])
    # a plant at (10, 20)-(30, 40) on the second tile's upscaled picture
    found = concept.on_picture({"1/lettuce:lettuce": [{"box": [10, 20, 30, 40], "score": 0.9}]}, tiles)
    left, top = tiles[1][:2]
    assert found["lettuce:lettuce"][0]["box"] == [left + 10 / concept.UPSCALE, top + 20 / concept.UPSCALE,
                                                  left + 30 / concept.UPSCALE, top + 40 / concept.UPSCALE]


def test_spacing_and_share_of_a_grid():
    """On a square plot seen square (no slant): 6 x 6 plants 100 px apart and 50 px wide are two widths apart; a
    plant found twice (two nouns, or two tiles) is kept once; a stray far off is left out."""
    instances = dict(SQUARE_PLOT)
    instances.update(grid("lettuce", "lettuce", (550, 550), 6, 100, 50))
    instances.update(grid("potato", "potato", (1300, 1300), 3, 40, 20))
    instances["herb:rosemary"] = [{"box": [1900, 100, 1910, 110], "score": 0.9}]
    doubled = grid("lettuce", "lettuce", (552, 552), 6, 100, 50)["lettuce:lettuce"]
    instances["lettuce:lettuce"] = instances["lettuce:lettuce"] + doubled
    found = concept.measures(RECORD, instances, [2000, 2000])["kinds"]
    assert found["lettuce"]["count"] == 36 and found["potato"]["count"] == 9, found
    assert abs(found["lettuce"]["spacing"] - 2.0) < 0.01 and abs(found["potato"]["spacing"] - 2.0) < 0.01, found
    assert abs(found["lettuce"]["share"] - 0.09) < 0.001, found["lettuce"]
    assert found["herb"]["count"] == 0 and found["herb"]["strays"] == 1, found["herb"]


def test_measured_gate():
    """Every kind found in a patch passes; a kind found in none, or no plot, is unknown; a merged mass (a box over
    MERGED widths) is left out of its kind."""
    instances = dict(SQUARE_PLOT)
    for number, kind in enumerate(RECORD["kinds"]):
        instances.update(grid(kind, RECORD["kinds"][kind]["nouns"][0], (100 + 350 * number, 100), 3, 30))
    instances["greens:leafy bush"].append({"box": [1150, 600, 1450, 800], "score": 0.9})
    with tempfile.TemporaryDirectory() as folder:
        output = pathlib.Path(folder)
        inputs = design_inputs(output)
        found = concept.measures(RECORD, instances, [2000, 2000])
        (output / "concept.json").write_text(json.dumps(found))
        assert concept.judge_measured(output, inputs, None).answer == "pass"
        assert found["kinds"]["greens"]["count"] == 9, found["kinds"]["greens"]
        missing = dict(found, kinds=dict(found["kinds"], potato=dict(found["kinds"]["potato"], count=0)))
        (output / "concept.json").write_text(json.dumps(missing))
        assert concept.judge_measured(output, inputs, None).answer == "unknown"
        (output / "concept.json").write_text(json.dumps(dict(found, plot=None)))
        assert concept.judge_measured(output, inputs, None).answer == "unknown"


def laid_on_greenhouse(folder, spacing_widths):
    """The design's beds shared and laid at `spacing_widths` plant widths for every kind, plants 0.2 m wide; the
    gates' inputs and output folder."""
    beds = crop_data.beds_in(design_inputs(folder), RECORD)
    shared = layer.shared_by_bed(RECORD, beds, {kind: 1.0 for kind in RECORD["kinds"]})
    widths = {kind: 0.2 for kind in RECORD["kinds"]}
    spots = layer.laid_spots(beds, shared, {kind: spacing_widths * 0.2 for kind in RECORD["kinds"]}, 7)
    (folder / "spots.json").write_text(json.dumps({"beds": shared, "spots": spots, "widths": widths}))
    concept_folder = folder / "concept"
    concept_folder.mkdir(exist_ok=True)
    (concept_folder / "concept.json").write_text(json.dumps({"kinds": {kind: {"spacing": 1.5}
                                                                       for kind in RECORD["kinds"]}}))
    return {**design_inputs(folder), "crops-concept": concept_folder}, beds, shared, spots


def test_layer_gates():
    """Laid at the concept's 1.5 widths every bed carries plants and both gates pass; laid at 3 widths spacing fails;
    a plant moved off its bed fails `on beds`."""
    with tempfile.TemporaryDirectory() as folder:
        folder = pathlib.Path(folder)
        inputs, beds, shared, spots = laid_on_greenhouse(folder, 1.5)
        assert sum(len(names) for names in shared.values()) == len(beds) == 25, shared
        assert layer.judge_on_beds(folder, inputs, None).answer == "pass"
        verdict = layer.judge_spacing(folder, inputs, None)
        assert verdict.answer == "pass", verdict
        laid_on_greenhouse(folder, 3.0)
        assert layer.judge_spacing(folder, inputs, None).answer == "fail"
        record = json.loads((folder / "spots.json").read_text())
        record["spots"][0]["at"][0] += 1.0
        (folder / "spots.json").write_text(json.dumps(record))
        assert layer.judge_on_beds(folder, inputs, None).answer == "fail"


def test_layer_says_what_made_its_crops():
    """Each kind's prototype says what made it (score:kind), so the made-only check passes the laid crop meshes;
    without the mark it fails them, as it did on complete@greenhouse of 2026-10-17."""
    from pxr import Sdf, Usd, UsdGeom
    with tempfile.TemporaryDirectory() as folder:
        folder = pathlib.Path(folder)
        (folder / "assets").mkdir()
        (folder / "layers").mkdir()
        assets = {}
        for kind, entry in RECORD["kinds"].items():
            model = layer.model_of(entry)
            asset = Usd.Stage.CreateNew(str(folder / "assets" / f"{model}.usdc"))
            asset.SetDefaultPrim(UsdGeom.Xform.Define(asset, f"/{model}").GetPrim())
            UsdGeom.Mesh.Define(asset, f"/{model}/geo")
            asset.GetRootLayer().Save()
            assets[kind] = {"model": model, "lowest": 0.0}
        spot = {"at": [0.0, 0.0, 0.0], "turn": 0.0, "size": 1.0}
        layer.write_layer("greenhouse", RECORD, assets, [dict(spot, kind=kind) for kind in RECORD["kinds"]],
                          folder / layer.LAYER)
        stage = Usd.Stage.CreateInMemory()
        stage.GetRootLayer().subLayerPaths.append(str(folder / layer.LAYER))
        stage.SetDefaultPrim(UsdGeom.Xform.Define(stage, "/greenhouse").GetPrim())
        with crop_data.tools("usd"):
            import made_only
        assert made_only.unmade_meshes(stage) == [], made_only.unmade_meshes(stage)
        stage.SetEditTarget(Usd.EditTarget(Sdf.Layer.Find(str(folder / layer.LAYER))))
        for kind in RECORD["kinds"]:
            prototype = stage.GetPrimAtPath(f"/greenhouse/Crops/{kind}/Prototypes/{assets[kind]['model']}")
            assert prototype.GetChild("geo").IsValid(), kind
            prototype.RemoveProperty("score:kind")
        assert len(made_only.unmade_meshes(stage)) == len(RECORD["kinds"])


def test_look_finds_the_floor_again():
    """A point of the beds' top drawn by a look camera is taken back onto it."""
    for view in look.views_of(BEDS):
        for point in ((-5.4, 0.46, 1.6), (-3.0, 0.46, -0.8), (-4.2, 0.46, 0.4)):
            pixel = projected(view, point, look.SIZE)
            back = look.on_floor(view, pixel, look.SIZE, 0.46)
            assert math.dist(back, (point[0], point[2])) < 1e-6, (view["name"], point, back)
            assert 0 <= pixel[0] < look.SIZE[0] and 0 <= pixel[1] < look.SIZE[1], (view["name"], point, pixel)


def test_look_counts_a_plant_the_kind_of_its_bed():
    """A plant found by any kind's noun, twice, is one plant of the kind laid on the bed its foot stands on."""
    beds = {bed["name"]: bed for bed in BEDS}
    view = look.views_of(BEDS)[0]
    foot_x, foot_y = projected(view, (-5.4, 0.46, 1.6), look.SIZE)
    box = [foot_x - 20, foot_y - 60, foot_x + 20, foot_y]
    instances = {f"{view['name']}/greens:leafy bush": [{"box": box, "score": 0.8}],
                 f"{view['name']}/herb:rosemary": [{"box": [value + 1 for value in box], "score": 0.7}]}
    shared = {kind: [] for kind in RECORD["kinds"]}
    shared["herb"] = ["PLANTER BED 0_0"]
    spots_record = {"spots": [], "widths": {kind: 0.2 for kind in RECORD["kinds"]}}
    seen = look.seen_on_beds(RECORD, view, instances, beds, shared, spots_record)
    assert seen["herb"]["seen"] == 1 and seen["greens"]["seen"] == 0, seen


def boxed_inputs(folder, gemini=()):
    """The design's files with every crop row boxed by the reading: SAM 3's box, Gemini's region for `gemini`."""
    inputs = design_inputs(folder)
    rows = [dict(row, box=[10, 10, 40, 40], **({"boxed_by": "gemini"} if row["id"] in gemini else {}))
            for row in INVENTORY["rows"]]
    (folder / "inventory.json").write_text(json.dumps(dict(INVENTORY, rows=rows)))
    return {**inputs, "concept": folder / "concept.png"}


def test_crop_boxes_the_reading_placed_pass_and_rent_nothing():
    """2026-10-22 benchmark: crops-boxes read the retired page-A inventory, found nothing to mask and still rented a
    card. Off the design, a crop row SAM 3 boxed in the reading passes as it stands, with no mask job and no rent."""
    folder = pathlib.Path(tempfile.mkdtemp(prefix="crops-boxes-"))
    inputs = boxed_inputs(folder)
    assert boxes.to_mask(inputs) == []
    out = folder / "out"
    out.mkdir()
    boxes.make_boxes(inputs, out, 1, {})  # a rent here would need a cleared run and fail
    assert not (out / "mask-jobs.json").exists()
    verdict = boxes.judge_boxed(out, inputs, None)
    assert verdict.answer == checks.PASS, verdict


def test_only_a_crop_row_the_reading_framed_by_gemini_is_masked():
    """A crop row whose reading box is Gemini's region is SAM 3's job again, on the locked concept; until decided the
    gate is unknown, never a pass."""
    folder = pathlib.Path(tempfile.mkdtemp(prefix="crops-boxes-"))
    inputs = boxed_inputs(folder, gemini=("potato",))
    [job] = boxes.to_mask(inputs)
    assert job["picture"] == str(folder / "concept.png") and [row["key"] for row in job["rows"]] == ["potato"]
    assert job["rows"][0]["keep"] == boxes.KEEP and job["rows"][0]["nouns"] == ["potato"]
    out = folder / "out"
    out.mkdir()
    (out / "decided.json").write_text(json.dumps({"decided": {row: boxes.IN_READING for row in RECORD["kinds"]
                                                              if row != "potato"}}))
    verdict = boxes.judge_boxed(out, inputs, None)
    assert verdict.answer == checks.UNKNOWN and verdict.findings[0].startswith("potato"), verdict


def test_look_rents_one_card_class():
    """A batch job runs on its one priced class; no stock is a gap, never a larger card (#21)."""
    assert "," not in look.CARDS, look.CARDS

if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[3] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
    print("crops_test: ok")
