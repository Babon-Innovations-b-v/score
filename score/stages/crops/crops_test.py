"""The crops stage's free parts on the greenhouse's own data: the concept's tiles and measures on a known grid of
plants, and the measured gate breaking when a kind is missing.

    .venv/bin/python score/stages/crops/crops_test.py
"""
import json
import math
import pathlib
import tempfile

import score.stages.crops.concept as concept
import score.stages.crops.crop_data as crop_data
import score.stages.crops.layer as layer
import score.stages.crops.look as look

RECORD = crop_data.record("greenhouse")
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
    instances = dict(SQUARE_PLOT)
    for number, kind in enumerate(RECORD["kinds"]):
        instances.update(grid(kind, RECORD["kinds"][kind]["nouns"][0], (100 + 350 * number, 100), 3, 30))
        if RECORD["kinds"][kind].get("canopy"):  # a canopy is found as merged masses among the small boxes
            instances[f"{kind}:{RECORD['kinds'][kind]['nouns'][0]}"].append(
                {"box": [100 + 350 * number, 600, 400 + 350 * number, 800], "score": 0.9})
    with tempfile.TemporaryDirectory() as folder:
        output = pathlib.Path(folder)
        crops = output / "crops.json"
        crops.write_text(json.dumps(RECORD))
        found = concept.measures(RECORD, instances, [2000, 2000])
        (output / "concept.json").write_text(json.dumps(found))
        assert concept.judge_measured(output, {"crops": crops}, None).answer == "pass"
        assert found["kinds"]["greens"]["count"] == 1 and found["kinds"]["greens"]["spacing"] == concept.CANOPY_SPACING
        assert abs(found["kinds"]["greens"]["share"] - 300 * 200 / 2000 ** 2) < 1e-3, found["kinds"]["greens"]
        missing = dict(found, kinds=dict(found["kinds"], potato=dict(found["kinds"]["potato"], count=0)))
        (output / "concept.json").write_text(json.dumps(missing))
        assert concept.judge_measured(output, {"crops": crops}, None).answer == "unknown"
        (output / "concept.json").write_text(json.dumps(dict(found, plot=None)))
        assert concept.judge_measured(output, {"crops": crops}, None).answer == "unknown"


def laid_on_greenhouse(folder, spacing_widths):
    """The greenhouse's beds shared and laid at `spacing_widths` plant widths for every kind, plants 0.2 m wide; the
    gates' inputs and output folder."""
    scene = crop_data.REPO / "data/scene/greenhouse.json"
    beds = layer.beds_of(json.loads(scene.read_text()), RECORD["beds"])
    shared = layer.shared_out(beds, {kind: 1.0 for kind in RECORD["kinds"]})
    widths = {kind: 0.2 for kind in RECORD["kinds"]}
    spots = layer.laid_spots(beds, shared, {kind: spacing_widths * 0.2 for kind in RECORD["kinds"]}, 7)
    (folder / "spots.json").write_text(json.dumps({"beds": shared, "spots": spots, "widths": widths}))
    concept_folder = folder / "concept"
    concept_folder.mkdir(exist_ok=True)
    (concept_folder / "concept.json").write_text(json.dumps({"kinds": {kind: {"spacing": 1.5}
                                                                       for kind in RECORD["kinds"]}}))
    crops = folder / "crops.json"
    crops.write_text(json.dumps(RECORD))
    return {"crops": crops, "scene": scene, "crops-concept": concept_folder}, beds, shared, spots


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


def test_look_finds_the_floor_again():
    """A point of the beds' top drawn by a look camera (the effects look's projection) is taken back onto it."""
    import score.stages.effects.look as effects_look
    beds = layer.beds_of(json.loads((crop_data.REPO / "data/scene/greenhouse.json").read_text()), RECORD["beds"])
    for view in look.views_of(beds):
        for point in ((-5.7, 0.06, 4.7), (-3.3, 0.06, 2.3), (-4.5, 0.06, 3.5)):
            pixel = effects_look.projected(view, point, look.SIZE)
            back = look.on_floor(view, pixel, look.SIZE, 0.06)
            assert math.dist(back, (point[0], point[2])) < 1e-6, (view["name"], point, back)
            assert 0 <= pixel[0] < look.SIZE[0] and 0 <= pixel[1] < look.SIZE[1], (view["name"], point, pixel)


def test_look_counts_a_plant_the_kind_of_its_bed():
    """A plant found by any kind's noun, twice, is one plant of the kind laid on the bed its foot stands on."""
    import score.stages.effects.look as effects_look
    beds = {bed["name"]: bed for bed in layer.beds_of(json.loads((crop_data.REPO / "data/scene/greenhouse.json")
                                                                 .read_text()), RECORD["beds"])}
    view = look.views_of(list(beds.values()))[0]
    foot_x, foot_y = effects_look.projected(view, (-5.7, 0.06, 4.7), look.SIZE)
    box = [foot_x - 20, foot_y - 60, foot_x + 20, foot_y]
    instances = {f"{view['name']}/greens:leafy bush": [{"box": box, "score": 0.8}],
                 f"{view['name']}/herb:rosemary": [{"box": [value + 1 for value in box], "score": 0.7}]}
    shared = {kind: [] for kind in RECORD["kinds"]}
    shared["herb"] = ["bed_0_0"]
    spots_record = {"spots": [], "widths": {kind: 0.2 for kind in RECORD["kinds"]}}
    seen = look.seen_on_beds(RECORD, view, instances, beds, shared, spots_record)
    assert seen["herb"]["seen"] == 1 and seen["greens"]["seen"] == 0, seen


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
    print("crops_test: ok")
