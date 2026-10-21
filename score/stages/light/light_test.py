"""Check the light stage's measures on pictures made here: a floodlight bank drawn as a grid of lit panes in a dark
frame has no halo and a low fill, the same bank glowing into the air round it has both; a flat-palette disc covers
most of itself with its eight commonest colours and a noisy one does not; a sky's colour, its blue to red and its rise
to the horizon are read on the pixels the flat sky held before; haze over the picture's lower part reads as a veil; a point straight ahead falls in the picture's middle.
The sweep (mix.py) on passes made here: the scale that brings a place to its concept's brightness is found, a lamp
that whites out what it lights is turned down, one on screen that lights nothing is unlit. The layer (layer.py) on a
stage made here: a record lamp near a seed lamp moves it, one far from any is added, and the strengths land on it.

Run: .venv/bin/python score/stages/light/light_test.py   (make tests runs it)
"""
import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
from score.stages.light import layer, measure, mix  # noqa: E402
from score.store import PROPS_HOME  # noqa: E402

REPO = pathlib.Path(__file__).resolve().parents[3]

SIZE = 200
WIDE = 480


def grid_bank():
    picture = np.full((WIDE, WIDE, 3), 20.0)
    picture[210:270, 200:280] = 5.0
    for row in range(2):
        for column in range(3):
            picture[215 + row * 28:237 + row * 28, 205 + column * 25:225 + column * 25] = 250.0
    return picture


def glowing_bank():
    rows, columns = np.mgrid[0:WIDE, 0:WIDE]
    distance = np.hypot(columns - 240, rows - 240)
    picture = np.full((WIDE, WIDE, 3), 20.0) + (230.0 * np.exp(-distance / 45.0))[..., None]
    return np.clip(picture, 0, 255)


def check_heads():
    grid, glow = measure.head(grid_bank(), 240, 240, 40), measure.head(glowing_bank(), 240, 240, 40)
    assert grid["halo"] < 0.02 and grid["fill"] < 0.1, grid
    assert glow["halo"] > 0.08 and glow["fill"] > 0.28, glow


def check_discs():
    rng = np.random.default_rng(1)
    flat = np.zeros((SIZE, SIZE, 3))
    flat[:, :100] = [40, 90, 160]
    flat[:, 100:] = [60, 140, 60]
    noisy = np.clip(flat + rng.normal(0, 30, flat.shape), 0, 255)
    assert measure.disc(flat, 100, 100, 80)["flat_share"] > 0.9
    assert measure.disc(noisy, 100, 100, 80)["flat_share"] < 0.2


def check_sky():
    before = np.zeros((SIZE, SIZE, 3))
    before[:] = [70, 42, 16]
    before[120:] = [120, 60, 30]
    after = before.copy()
    after[:90] = np.linspace(170, 195, 90)[:, None, None] * np.array([1.0, 0.78, 0.6])
    concept = [188.1, 145.2, 112.1]
    flat = measure.sky_of(before, measure.sky_pixels(before))
    found = measure.sky_of(after, measure.sky_pixels(after))
    assert measure.colour_gap(flat["mean_rgb"], concept) > 80 and measure.colour_gap(found["mean_rgb"], concept) < 20
    assert found["rise_to_horizon"] > 0 and abs(found["blue_to_red"] - 0.6) < 0.01, found


def check_veil():
    before = np.full((100, 100, 3), 40.0)
    after = before.copy()
    after[:50] += 100.0  # a lamp's glow up in the sky leaves the place below as it was
    assert measure.veil(before, after) == 0.0
    after[60:] += 30.0  # haze laid over the place's lower part
    assert abs(measure.veil(before, after) - 30.0 / 255.0) < 1e-3


def check_where():
    view = {"eye": [0, 0, 0], "aim": [0, 0, -10], "up": [0, 1, 0], "fov": 90}
    x, y, depth, focal = measure.where(view, (200, 100), [0, 0, -5])
    assert (round(x), round(y), round(depth, 6), round(focal, 6)) == (100, 50, 5.0, 100.0)
    assert measure.where(view, (200, 100), [0, 0, 5])[0] is None


def toned_look(light):
    """A look made from light by a known tone curve (light over one plus light)."""
    return light / (1.0 + light)


def check_sweep():
    rest = np.tile(np.linspace(0.01, 0.1, 60), (40, 1))
    lamp = np.tile(np.linspace(0.0, 4.0, 40)[:, None], (1, 60))
    lamp[:, 30:] = 0.0
    passes = {"combined": rest + lamp, "lamp_0": lamp, "lamp_1": np.zeros((40, 60))}
    views = {"v": (passes, mix.tone_curve(passes["combined"], toned_look(passes["combined"])))}
    target = float(toned_look(rest + 2.0 * lamp).mean())
    assert abs(np.log2(mix.sweep(views, ["lamp_0"], target) / 2.0)) <= 0.25  # the curve past what was rendered
    assert mix.sweep(views, [], target) == 1.0
    assert mix.lamp_faults(mix.lamp_measures(views, {}, "lamp_1"), ["v"]) == "unlit"
    assert mix.lamp_faults(mix.lamp_measures(views, {}, "lamp_1"), []) == "unseen"
    bright = {"combined": rest + 50.0 * lamp, "lamp_0": 50.0 * lamp}
    glaring = {"v": (bright, mix.tone_curve(bright["combined"], np.minimum(bright["combined"], 1.0)))}
    assert mix.lamp_faults(mix.lamp_measures(glaring, {}, "lamp_0"), ["v"]) == "blown"
    scale, measures = mix.turned_down(glaring, {}, "lamp_0")
    assert scale < 1.0 and mix.lamp_faults(measures, ["v"]) is None, (scale, measures)


def tiny_seed(seed):
    """A seed stage with one lamp, /tiny/Lights/light_1 at (0, 2, 0), intensity 10."""
    from pxr import Gf, Usd, UsdGeom, UsdLux
    (seed / "layers").mkdir(parents=True)
    base = Usd.Stage.CreateNew(str(seed / "layers/base.usda"))
    base.SetDefaultPrim(UsdGeom.Xform.Define(base, "/tiny").GetPrim())
    UsdGeom.Scope.Define(base, "/tiny/Lights")
    light = UsdLux.SphereLight.Define(base, "/tiny/Lights/light_1")
    light.CreateIntensityAttr(10.0)
    light.AddTranslateOp().Set(Gf.Vec3d(0.0, 2.0, 0.0))
    base.Save()
    root = Usd.Stage.CreateNew(str(seed / "tiny.usda"))
    root.GetRootLayer().subLayerPaths.append("./layers/base.usda")
    root.Save()


def check_layer():
    import tempfile
    from pxr import Usd
    (PROPS_HOME / "store-tests").mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=PROPS_HOME / "store-tests") as folder:
        seed, out = pathlib.Path(folder) / "seed", pathlib.Path(folder) / "out"
        tiny_seed(seed)
        record = {"lights": [{"type": "omni", "at": [1.0, 2.0, 0.0],
                              "energy": 1.0, "colour": "#ffffff"},
                             {"type": "spot", "at": [20.0, 2.0, 0.0], "aim": [20.0, 0.0, 0.0], "angle": 30.0,
                              "energy": 1.0, "colour": "#ffffff"}]}
        found = layer.write("tiny", record, seed, out)
        assert [entry["done"] for entry in found["placed"]] == ["moved 1.00 m", "added"], found["placed"]
        moved = next(lamp for lamp in found["lamps"] if lamp["path"] == "/tiny/Lights/light_1")
        assert moved["spot"] == [1.0, 2.0, 0.0] and not moved["shaped"], moved
        layer.strengths(out / layer.LAYER, "tiny", {"/tiny/Lights/light_1": (10.0, 0.5)})
        held = Usd.Stage.Open(str(out / layer.LAYER))
        assert held.GetPrimAtPath("/tiny/Lights/light_1").GetAttribute("inputs:intensity").Get() == 5.0


def check_copy_leaves_its_input():
    """Fault (2026-10-12, light@camp): the strengths were saved over the input layer, a read-only checkout. The make
    writes its own copy and the input stays as it was."""
    import os
    import stat
    import tempfile
    from score.stages import light
    (PROPS_HOME / "store-tests").mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=PROPS_HOME / "store-tests") as folder:
        seed, made, out = (pathlib.Path(folder) / name for name in ("seed", "made", "out"))
        tiny_seed(seed)
        layer.write("tiny", {"lights": []}, seed, made)
        views = {"views": [{"name": "door", "eye": [0, 1.6, 2], "aim": [0, 1.2, 0], "fov": 70}]}
        (made / light.passes.VIEWS).write_text(json.dumps(light.passes.record_views(views)))
        before = (made / layer.LAYER).read_bytes()
        for path in made.rglob("*"):
            os.chmod(path, stat.S_IREAD | (stat.S_IEXEC if path.is_dir() else 0))
        light.layer_copied(made, out)
        layer.strengths(out / layer.LAYER, "tiny", {"/tiny/Lights/light_1": (10.0, 2.0)})
        assert (made / layer.LAYER).read_bytes() == before
        size, copied = light.passes.views_of(out)  # the record's views, at the check size, travel with the layer
        assert size == light.passes.CHECK_SIZE and copied[0]["up"] == [0.0, 1.0, 0.0] and copied[0]["frame"] == 0
        for path in made.rglob("*"):
            os.chmod(path, stat.S_IRWXU)


def check_neighbour_keeps_its_pictures():
    """Fault (2026-10-18, light-passes of ten places): a shown place's light layer was written into its seed's copy in
    the lit tree, and the writer moved that copy's own pictures into assets/light, so its materials drew magenta. Its
    layer is written beside the tree now: the copy keeps its pictures and the lit tree names none that is missing."""
    import shutil
    import subprocess
    import tempfile
    from PIL import Image
    from pxr import Sdf, Usd, UsdShade
    from score.stages.light import passes
    (PROPS_HOME / "store-tests").mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=PROPS_HOME / "store-tests") as folder:
        seed, tree = pathlib.Path(folder) / "seed", pathlib.Path(folder) / "tree"
        tiny_seed(seed)
        (seed / "assets/textures").mkdir(parents=True)
        Image.new("RGB", (4, 4), (90, 90, 90)).save(seed / "assets/textures/wall.png")
        base = Usd.Stage.Open(str(seed / "layers/base.usda"))
        shader = UsdShade.Shader.Define(base, "/tiny/Looks/wall/picture")
        shader.CreateInput("file", Sdf.ValueTypeNames.Asset).Set("../assets/textures/wall.png")
        base.Save()
        tree.mkdir()
        subprocess.run(["cp", "-al", str(seed), str(tree / "tiny")], check=True)
        passes.neighbour_layer("tiny", {"lights": []}, seed, tree)
        assert (tree / "tiny/assets/textures/wall.png").exists() and (tree / "tiny" / layer.LAYER).exists()
        assert passes.unresolved(tree / "tiny/tiny.usda") == []
        assert not (tree.parent / "light-of-tiny").exists()
        shutil.rmtree(tree / "tiny/assets/textures")
        assert len(passes.unresolved(tree / "tiny/tiny.usda")) == 1


def check_magenta():
    """A look with 1% of Blender's missing-texture magenta (as the tone curve draws it) fails; a clean one passes."""
    import tempfile
    from PIL import Image
    from score import checks
    from score.stages.light import passes
    with tempfile.TemporaryDirectory() as folder:
        output = pathlib.Path(folder)
        (output / "passes/tiny-0").mkdir(parents=True)
        clean = np.full((100, 100, 3), (120, 110, 100), np.uint8)
        Image.fromarray(clean).save(output / "passes/tiny-0/shot0-000-look.png")
        assert passes.judge_magenta(output, {}, {}).answer == checks.PASS
        clean[:10, :10] = (193, 79, 136)  # the tube's hub through its hatch, 2026-10-16
        Image.fromarray(clean).save(output / "passes/tiny-0/shot0-000-look.png")
        verdict = passes.judge_magenta(output, {}, {})
        assert verdict.answer == checks.FAIL and verdict.measures["magenta share"] == 0.01, verdict


def check_shafts_from_rows():
    """A floodlight's shaft is its inventory row's lamp's (the sky record's lamp row), never a hand-kept lamp of one
    place: the launch's pad floodlights get theirs in the record the scene-record row writes from its plan and kit,
    and no place's light data adds lamps."""
    from score.stages.light import haze
    from score.stages.scene_record import kit_shell
    sky = json.loads((REPO / "data/definitions/sky.json").read_text())["earth"]
    aims = json.loads((REPO / "data/plans/launch.json").read_text())["aims"]
    plan = {"aims": aims, "floor_height": 0.0,
            "items": [{"name": aim["at"], "box": [0, 0, 1, 1]} for aim in aims.values()]}
    kit = json.loads((REPO / "data/kit/launch.json").read_text())
    pads = [light for light in kit_shell.lamps(plan, kit, dict(sky, body="earth"))
            if "far_pad_floodlight" in light["from"]]
    lenses = [laid for laid in kit["pieces"]
              if laid["kind"] == "launch_far_pad_floodlight" and laid.get("part") == "glow"]
    assert len(pads) == len(lenses) > 0 and all(light.get("shaft") for light in pads), pads
    assert not [path for path in (REPO / "data/light").glob("*.json") if "kit_lamps" in json.loads(path.read_text())]
    assert haze.shafted_kinds("launch") == {"launch_far_pad_floodlight"}


def check_needs():
    """An outdoor place no ground seats lacks its seat and its sky; seated, it still lacks its sky until its kept sky
    has a site and a scene time on the environment's physics; a room under a roof needs neither, whatever an old
    hand-kept record beside it says; a place with no plan adds nothing (its route's plan gap stands)."""
    import shutil
    import tempfile
    from score.stages.light import needs
    from score.review import setting
    from score.stages.terrain import needs as ground_needs
    data = pathlib.Path(tempfile.mkdtemp())
    for folder in ("scene", "plans", "ground/plan", "definitions"):
        (data / folder).mkdir(parents=True)
    skies = data / "skies"
    skies.mkdir()
    (data / "plans/yard.json").write_text(json.dumps({"shell": "outdoor"}))
    (data / "plans/room.json").write_text(json.dumps({"shell": "kit", "inside": True}))
    (data / "scene/room.json").write_text(json.dumps({"environment": {"inside": False}, "views": []}))
    (data / "scene/oldonly.json").write_text(json.dumps({"environment": {"inside": False}, "views": []}))

    def ids(place):
        return sorted(gap["id"] for gap in needs.gaps(place, data, skies) + ground_needs.gaps(place, data))
    assert ids("yard") == ["ground:seat:yard", "sky:site:yard"], ids("yard")
    (data / "ground/plan/rock.json").write_text(json.dumps({"ground": "rock", "seats": {"yard": {}}}))
    assert ids("yard") == ["sky:site:yard"], ids("yard")  # no copied ground record places a detail area
    house = {"plots": [{"name": "Rock", "gravity": 9.81}], "sites": [{"place": "yard", "on": "rock", "x": 0, "y": 0}],
             "lights": [{"name": "Sun", "kelvin": 5800, "lux": 100000, "latitude": 52.0, "tilt_deg": 23.44,
                         "day_hours": 24, "year_days": 365.2422, "equinox": "2024-03-20T12:00:00Z"}]}
    (skies / "yard.json").write_text(json.dumps({"place": "yard", "top": "yard", "time": "2024-06-01T12:00:00Z",
                                                 "site": {"on": "rock", "x": 0, "y": 0, "height_m": 0},
                                                 "setting": setting.checked(house)}))
    assert ids("yard") == [], ids("yard")
    assert sorted(gap["id"] for gap in needs.gaps("room", data, skies)) == []
    assert needs.gaps("oldonly", data, skies) == [] and ids("nowhere") == []
    shutil.rmtree(data)


def check_exposure():
    """A view far blacker or more blown out than its concept fails; one as dark as a concept with a black sky passes;
    with no concept the gate cannot tell."""
    import shutil
    import tempfile
    from score import checks
    from score.stages import light
    half_black = np.concatenate([np.zeros((10, 20)), np.full((10, 20), 0.5)])
    assert light.extremes(half_black) == {"black": 0.5, "blown": 0.0}
    output = pathlib.Path(tempfile.mkdtemp())
    for concept, views, answer in (({"black": 0.45, "blown": 0.0}, {"wide": {"black": 0.5, "blown": 0.01}}, checks.PASS),
                                   ({"black": 0.01, "blown": 0.0}, {"wide": {"black": 0.2, "blown": 0.0}}, checks.FAIL),
                                   ({"black": 0.0, "blown": 0.0}, {"wide": {"black": 0.0, "blown": 0.05}}, checks.FAIL),
                                   (None, {"wide": {"black": 0.0, "blown": 0.0}}, checks.UNKNOWN)):
        (output / "measures.json").write_text(json.dumps({"exposure": {"concept": concept, "views": views}}))
        found = light.judge_exposure(output, {}, {})
        assert found.answer == answer, (concept, views, found)
    shutil.rmtree(output)


def check_design_rows():
    """The rows read the design only: they apply to every place whose plan the scene-record row writes (and to no
    place without a plan), light-haze where the kit lays a lamp with a shaft, the record is the scene-record output's
    (a shown place's read beside), the floodlight heads are the shafted kinds' glow parts of the place and of the
    places it shows, and no row declares a hand-kept record in data/scene."""
    import tempfile
    from score.stages import light, scene_record
    from score.stages.light import haze, passes
    plans = sorted(path.stem for path in (REPO / "data/plans").glob("*.json"))
    assert plans and all(light.applies(place) == scene_record.written(place) for place in plans)
    assert not light.applies("far_city") and not light.applies(None)
    assert [place for place in plans if haze.applies(place)] == ["launch", "square"]
    assert haze.shafted_kinds("square") == {"square_far_floodlight_tower"} and haze.shafted_kinds("flat") == set()
    for place in plans:
        for files in (light.layer_files, light.light_files, passes.passes_files):
            assert not [path for path in files(place).values() if path.startswith("{data}/scene")], (place, files)
    with tempfile.TemporaryDirectory() as folder:
        inputs = {}
        for node, place in (("scene-record", "launch"), ("scene-record@square", "square")):
            (pathlib.Path(folder) / node / "record").mkdir(parents=True)
            (pathlib.Path(folder) / node / "record" / f"{place}.json").write_text(
                json.dumps({"place": place, "lights": []}))
            inputs[node] = str(pathlib.Path(folder) / node)
        assert passes.place_of(inputs) == "launch" and passes.shown_in(inputs) == ["square"]
        assert passes.record_of("square", inputs)["place"] == "square"
        heads = len(light.lamp_heads("launch", inputs))
        alone = len(light.lamp_heads("launch", {"scene-record": inputs["scene-record"]}))
        glows = {place: sum(1 for laid in json.loads((REPO / f"data/kit/{place}.json").read_text())["pieces"]
                            if laid["kind"] in haze.shafted_kinds(place) and laid.get("part") == "glow")
                 for place in ("launch", "square")}
        assert alone == glows["launch"] > 0 and heads == glows["launch"] + glows["square"], (alone, heads, glows)


def main():
    check_design_rows()
    check_needs()
    check_exposure()
    check_sweep()
    check_layer()
    check_copy_leaves_its_input()
    check_shafts_from_rows()
    check_neighbour_keeps_its_pictures()
    check_magenta()
    check_heads()
    check_discs()
    check_sky()
    check_veil()
    check_where()
    print("light_test: ok")


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[3] / "conftest.py"))["refuse_outside_sandbox"]()
    main()
