"""Check the effects stage without Blender: the baked particles follow their record (how many, how long each lives,
where they can reach, thin at birth and death, a burst's dead ones gone), repeat exactly over their loop and from
their seed; Godot's spread and flatness; the effects layer composes between the edit layer and the base, loops its
clip over the stage's time, puts a variant's entries in its variant and makes a replaced prim inactive; a travelling
emitter moves downwind; every real record's entry names the game file it came from and lays out on its place.

Run: .venv/bin/python tools/usd/effects_test.py   (make tests runs it with the framework's environment)
"""
import json
import math
import pathlib
import re
import sys
import tempfile

import numpy as np
from pxr import Sdf, Usd, UsdGeom

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import effects  # noqa: E402
import export  # noqa: E402
import scene as scene_record  # noqa: E402


def box_emitter(**changes):
    """A small drift made here: 300 grains a 2 s life, let out of a 1 m box along x at 1.5 m/s."""
    emitter = {"name": "test_drift", "kind": "dust_drift", "look": "speck", "emitter": {"shape": "box",
               "extents": [0.5, 0.5, 0.5]}, "count": 300, "lifetime": 2.0, "direction": [1.0, 0.0, 0.0],
               "spread": 0.0, "speed": [1.5, 1.5], "size": 0.03, "colour": "#e16e48", "opacity": 0.7,
               "opacity_over_life": [[0.0, 0.0], [0.2, 1.0], [0.7, 1.0], [1.0, 0.0]], "seed": 5,
               "origin": np.zeros(3), "basis": np.eye(3), "from": "made in effects_test.py"}
    emitter.update(changes)
    return emitter


def test_bake_follows_the_record():
    points, widths, opacity = effects.bake(box_emitter())
    assert points.shape == (int(2.0 * effects.SAMPLES) + 1, 300, 3), points.shape
    assert widths.shape == opacity.shape == points.shape[:2]
    # Out of the box along x at 1.5 m/s for at most 2 s, nothing pulling it: never beyond 3 m past the box.
    assert points[..., 0].min() >= -0.5 - 1e-4 and points[..., 0].max() <= 0.5 + 3.0 + 1e-3
    assert np.abs(points[..., 1:]).max() <= 0.5 + 1e-4
    assert np.allclose(widths, 0.03)
    assert 0.0 <= opacity.min() and opacity.max() <= 0.7 + 1e-6
    # The grain let out at the first moment is just born there: thin.
    assert opacity[0, 0] == 0.0
    assert np.array_equal(points[0], points[-1]) and np.array_equal(opacity[0], opacity[-1]), "the loop does not close"


def test_bake_is_seeded():
    first, second = effects.bake(box_emitter()), effects.bake(box_emitter())
    assert all(np.array_equal(one, other) for one, other in zip(first, second))
    other_seed = effects.bake(box_emitter(seed=6))
    assert not np.array_equal(first[0], other_seed[0])


def test_lives_are_drawn_apart_and_still_loop():
    points, _, _ = effects.bake(box_emitter(lives=2))
    assert len(points) == int(4.0 * effects.SAMPLES) + 1
    assert np.array_equal(points[0], points[-1])
    half = int(2.0 * effects.SAMPLES)
    assert not np.allclose(points[0], points[half]), "the second life repeats the first's draws"


def test_a_burst_is_gone_between_breaths():
    burst = box_emitter(count=100, lifetime=1.0, explosiveness=1.0, one_shot={"every": 3.0, "at": 0.5})
    _, widths, opacity = effects.bake(burst)
    before, during, after = (int(seconds * effects.SAMPLES) for seconds in (0.25, 0.9, 2.5))
    assert widths[before].max() == 0.0 and opacity[before].max() == 0.0
    assert (opacity[during] > 0).all()
    assert widths[after].max() == 0.0


def test_spread_and_flatness_as_godot():
    draws = np.random.default_rng(1).random((500, 2))
    straight = effects.spread_directions([1.0, 0.0, 0.0], 0.0, 0.0, draws[:, 0], draws[:, 1])
    assert np.allclose(straight, [1.0, 0.0, 0.0])
    flat = effects.spread_directions([1.0, 0.0, 0.0], 180.0, 1.0, draws[:, 0], draws[:, 1])
    assert np.allclose(flat[:, 1], 0.0) and flat[:, 0].min() < -0.9, "a flat full spread goes every way round"
    cone = effects.spread_directions([0.0, 1.0, 0.0], 6.0, 0.0, draws[:, 0], draws[:, 1])
    assert np.degrees(np.arccos(np.clip(cone[:, 1], -1, 1))).max() <= 6.0 * math.sqrt(2) + 1e-6


def test_gravity_pulls_down():
    points, _, _ = effects.bake(box_emitter(gravity=[0.0, -1.62, 0.0], direction=[0.0, 1.0, 0.0], speed=[1.0, 1.0]))
    # Thrown up at 1 m/s under 1.62: up 0.31 m at most, and down past where it left by the end of its 2 s.
    assert points[..., 1].max() <= 0.5 + 1.0 ** 2 / (2 * 1.62) + 0.01
    assert points[..., 1].min() < -0.5


def stage_folder(place, folder):
    """A place's stage made here: an empty base and edit layer and its root."""
    out = pathlib.Path(folder)
    (out / "layers").mkdir(parents=True)
    base = Sdf.Layer.CreateNew(str(out / "layers/base.usda"))
    stage = Usd.Stage.Open(base)
    UsdGeom.Xform.Define(stage, f"/{place}")
    UsdGeom.Points.Define(stage, f"/{place}/Sky/Dust")
    base.Save()
    export.ensure_edit(out)
    export.write_root(place, out)
    return out


def test_layer_composes_and_loops():
    record = {"place": "spot", "replaces": [{"prim": "Sky/Dust", "why": "test"}], "variants": {"weather": "calm"},
              "effects": [dict(box_emitter(name="calm_drift"), placement={"eye": "door", "offset": [0, 0, -1]},
                               variant=["weather", "calm"]),
                          dict(box_emitter(name="storm_drift", count=50), placement={"eye": "door", "offset": [0, 0, -1]},
                               variant=["weather", "storm"]),
                          dict(box_emitter(name="smoke", look="puff", near_fade=[1.0, 6.0]),
                               placement={"eye": "door", "offset": [0.1, -0.1, -0.2]})]}
    scene = {"views": [{"name": "door", "eye": [1.0, 1.6, 2.0], "aim": [1.0, 1.6, -5.0]}]}
    with tempfile.TemporaryDirectory() as folder:
        out = stage_folder("spot", folder)
        held = effects.write_layer("spot", record, out, None, scene)
        assert held == {"calm_drift": 300, "storm_drift": 50, "smoke": 300}
        root = Sdf.Layer.FindOrOpen(str(out / "spot.usda"))
        assert list(root.subLayerPaths) == ["./layers/edit.usda", "./layers/effects.usda", "./layers/base.usda"]
        stage = Usd.Stage.Open(str(out / "spot.usda"))
        assert not stage.GetPrimAtPath("/spot/Sky/Dust").IsActive()
        grains = UsdGeom.Points(stage.GetPrimAtPath("/spot/Effects/calm_drift/calm_drift_points"))
        assert grains, "the calm variant is not the one chosen"
        assert not stage.GetPrimAtPath("/spot/Effects/storm_drift")
        loop = effects.loop_of(box_emitter()) * effects.RATE
        for time in (0.0, 6.0, 17.0):
            here, later = (np.asarray(grains.GetPointsAttr().Get(moment)) for moment in (time, time + 3 * loop))
            assert np.allclose(here, later), f"the clip does not loop at {time}"
        assert len(grains.GetPointsAttr().Get(5.0)) == 300
        smoke = stage.GetPrimAtPath("/spot/Effects/smoke")
        where = UsdGeom.Xformable(smoke).ComputeLocalToWorldTransform(0.0).ExtractTranslation()
        assert np.allclose(where, [1.1, 1.5, 1.8], atol=1e-6), where  # 0.2 ahead of an eye looking down -z
        assert smoke.GetAttribute("score:effect:look").Get() == "puff"
        assert smoke.GetAttribute("score:effect:count").Get() == 300
        assert smoke.GetAttribute("score:effect:from").Get() == "made in effects_test.py"
        assert (out / effects.ASSETS / "smoke.usdc").exists()
        stage.GetPrimAtPath("/spot/Effects").GetVariantSets().GetVariantSet("weather").SetVariantSelection("storm")
        assert stage.GetPrimAtPath("/spot/Effects/storm_drift/storm_drift_points")


def test_a_devil_wanders_downwind():
    entry = dict(box_emitter(name="devil"), placement={"ground": [10.0, 0.0, 0.0]},
                 travel={"downwind": 1.4, "seconds": 80.0, "age": 20.0}, spin=3.0)
    emitter = effects.ground_emitter(entry, None, {"minute": 0, "turn_a_day": 0.9})
    seconds, last, _ = emitter["path"][-1]
    assert seconds == 60.0
    assert np.allclose(last, [10.0 + 1.4 * 60.0, 0.0, 0.0]), last  # on flat ground the wind's way is x
    with tempfile.TemporaryDirectory() as folder:
        stage = Usd.Stage.CreateNew(str(pathlib.Path(folder) / "devil.usda"))
        xform = UsdGeom.Xform.Define(stage, "/devil")
        effects.stood(xform, emitter)
        moved = xform.ComputeLocalToWorldTransform(30.0 * effects.RATE).ExtractTranslation()
        assert np.allclose(moved, [10.0 + 1.4 * 30.0, 0.0, 0.0], atol=1e-6)


def test_every_record_names_its_game_source_and_lays_out():
    places = {path.stem for path in (HERE.parents[1] / "data/scene").glob("*.json")}
    for path in sorted(effects.RECORDS.glob("*.json")):
        found = json.loads(path.read_text())
        assert found["place"] == path.stem and path.stem in places, f"{path.name} is not one of the world's places"
        for entry in found["effects"]:
            assert re.search(r"(game|sim)/\S+\.(gd|gdshader|tscn):\d", entry.get("from", "")), \
                f"{path.name} {entry['name']} names no game file and lines"
        laid = effects.emitters_of(found, effects.place_ground(path.stem), scene_record.record(path.stem))
        assert len({emitter["name"] for emitter in laid}) == len(laid), f"{path.name}: two emitters share a name"
        for emitter in laid:
            assert np.allclose(emitter["basis"].T @ emitter["basis"], np.eye(3), atol=1e-6)
            assert np.all(np.isfinite(emitter["origin"]))


def main():
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print("ok", test.__name__)


if __name__ == "__main__":
    main()
