"""tools/usd/effects.py without Blender: the baked particles follow their record (how many, how long each lives,
where they can reach, thin at birth and death, a burst's dead ones gone), repeat exactly over their loop and from
their seed; Godot's spread and flatness; the effects layer composes between the edit layer and the base, loops its
clip over the stage's time, puts a variant's entries in its variant and makes a replaced prim inactive; a travelling
emitter moves downwind; on a place's ball the wind lies along the ground at every spot.

Breaks that turn each test red (each applied once and seen red, 2026-10-27), all in effects.py:
- test_bake_follows_the_record: flight's `points = points + velocity * STEP` made `+ 2 * velocity * STEP`.
- test_bake_is_seeded: bake's `np.random.default_rng([seed, life])` made `np.random.default_rng()`.
- test_lives_are_drawn_apart_and_still_loop: bake's `np.random.default_rng([seed, life])` made `([seed, 0])`.
- test_a_burst_is_gone_between_breaths: bake's `else since < lifetime` made `else since < 10 * lifetime`.
- test_spread_and_flatness_as_godot: spread_directions' `* (1.0 - flatness)` dropped from `angle_two`.
- test_gravity_pulls_down: flight's `force = np.broadcast_to(gravity, points.shape).copy()` made
  `force = np.zeros(points.shape)`.
- test_layer_composes_and_loops: looped_times' `for turn in range(int(math.ceil(HORIZON / loop))):` made
  `for turn in range(1):`.
- test_an_event_lets_out_once_where_its_prim_climbs: bake_once's `points[..., 1] += climbed(...)` made `pass`.
- test_a_rider_moves_with_its_prim_and_lights_when_it_starts: clip_times' `if emitter.get("starts") is None:` made
  `if True:`.
- test_a_rider_keeps_its_own_size_on_a_scaled_prim: unscaled's `undo.Set(Gf.Vec3f(*(1.0 / scale)))` made
  `undo.Set(Gf.Vec3f(1.0, 1.0, 1.0))`.
- test_a_devil_wanders_downwind: ground_emitter's `* float(travel["downwind"])` dropped from `flat`.
- test_the_wind_lies_along_the_ground: place_wind's `wind_along(out, ...)` made `wind_along([0.0, 1.0, 0.0], ...)`.

Run: .venv/bin/python tools/usd/test_baked_particles_follow_their_record.py
"""
import math
import pathlib
import sys
import tempfile

import numpy as np
from pxr import Gf, Sdf, Usd, UsdGeom

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import effects  # noqa: E402
import export  # noqa: E402


def box_emitter(**changes):
    """A small drift made here: 300 grains a 2 s life, let out of a 1 m box along x at 1.5 m/s."""
    emitter = {"name": "test_drift", "kind": "dust_drift", "look": "speck", "emitter": {"shape": "box",
               "extents": [0.5, 0.5, 0.5]}, "count": 300, "lifetime": 2.0, "direction": [1.0, 0.0, 0.0],
               "spread": 0.0, "speed": [1.5, 1.5], "size": 0.03, "colour": "#e16e48", "opacity": 0.7,
               "opacity_over_life": [[0.0, 0.0], [0.2, 1.0], [0.7, 1.0], [1.0, 0.0]], "seed": 5,
               "origin": np.zeros(3), "basis": np.eye(3), "from": "made in test_baked_particles_follow_their_record.py"}
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
        assert smoke.GetAttribute("score:effect:from").Get() == "made in test_baked_particles_follow_their_record.py"
        assert (out / effects.ASSETS / "smoke.usdc").exists()
        stage.GetPrimAtPath("/spot/Effects").GetVariantSets().GetVariantSet("weather").SetVariantSelection("storm")
        assert stage.GetPrimAtPath("/spot/Effects/storm_drift/storm_drift_points")


def test_an_event_lets_out_once_where_its_prim_climbs():
    climb = {"lift": 1.0, "push": 12.0, "pull": 2.0, "start": 2.0}
    trail = box_emitter(once=[3.0, 5.0], samples=6, lifetime=1.0, speed=[0.0, 0.0], climb=climb)
    points, widths, _ = effects.bake(trail)
    assert len(points) == int(round(3.0 * 6)) + 1  # from its first second to its last particle's death
    assert widths[0].max() == 0.0 and widths[-1].max() == 0.0, "alive before its first birth or after its last death"
    # Each particle stays where it was let out (no speed): the prim's climb at its birth, within the box.
    born = 3.0 + (np.arange(300) + 0.5) / 300 * 2.0
    lift = 0.5 * 10.0 * (born - 3.0) ** 2
    alive = widths > 0
    assert np.abs(points[..., 1] - lift[None, :])[alive].max() <= 0.5 + 1e-4


def test_a_rider_moves_with_its_prim_and_lights_when_it_starts():
    record = {"place": "pad", "effects": [dict(box_emitter(name="flame", count=50, lifetime=0.5), starts=1.0,
                                               placement={"on": "Fixtures/rocket", "offset": [0.0, -1.0, 0.0]})],
              "lights": [{"name": "glow", "on": "Fixtures/rocket", "colour": "#ffb877", "shadows": False,
                          "intensity": [[0.0, 0.0], [1.0, 0.0], [1.5, 1000.0]], "from": "made in test_baked_particles_follow_their_record.py"}]}
    with tempfile.TemporaryDirectory() as folder:
        out = stage_folder("pad", folder)
        base = Usd.Stage.Open(str(out / "layers/base.usda"))
        rocket = UsdGeom.Xform.Define(base, "/pad/Fixtures/rocket")
        rocket.AddTranslateOp().Set(Gf.Vec3d(5.0, 0.0, 0.0), 0.0)
        rocket.GetOrderedXformOps()[0].Set(Gf.Vec3d(5.0, 100.0, 0.0), 240.0)
        base.GetRootLayer().Save()
        effects.write_layer("pad", record, out)
        stage = Usd.Stage.Open(str(out / "pad.usda"))
        flame = stage.GetPrimAtPath("/pad/Fixtures/rocket/flame")
        for code, height in ((0.0, -1.0), (240.0, 99.0)):
            where = UsdGeom.Xformable(flame).ComputeLocalToWorldTransform(code).ExtractTranslation()
            assert np.allclose(where, [5.0, height, 0.0]), where
        grains = UsdGeom.Points(stage.GetPrimAtPath("/pad/Fixtures/rocket/flame/flame_points"))
        assert max(grains.GetWidthsAttr().Get(12.0)) == 0.0, "the flame burns before it starts"
        assert max(grains.GetWidthsAttr().Get(36.0)) > 0.0, "the flame does not burn after it starts"
        glow = stage.GetPrimAtPath("/pad/Fixtures/rocket/glow")
        assert glow.GetAttribute("inputs:intensity").Get(12.0) == 0.0
        assert glow.GetAttribute("inputs:intensity").Get(36.0) == 1000.0
        assert glow.GetAttribute("score:game:shadows").Get() is False
        assert stage.GetPrimAtPath("/pad/Fixtures").GetSpecifier() == Sdf.SpecifierDef  # the base's, kept


def test_a_rider_keeps_its_own_size_on_a_scaled_prim():
    """An effect riding a prim scaled 4 x 2 x 4 stands at its offset scaled as a spot on the prim, and its particles
    keep the metres the effect gives them."""
    record = {"place": "pad", "effects": [dict(box_emitter(name="flame", count=50, lifetime=0.5),
                                               placement={"on": "Fixtures/tank", "offset": [0.0, 1.0, 0.0]})]}
    with tempfile.TemporaryDirectory() as folder:
        out = stage_folder("pad", folder)
        base = Usd.Stage.Open(str(out / "layers/base.usda"))
        tank = UsdGeom.Xform.Define(base, "/pad/Fixtures/tank")
        tank.AddTranslateOp().Set(Gf.Vec3d(5.0, 0.0, 0.0))
        tank.AddRotateYOp().Set(90.0)
        tank.AddScaleOp().Set(Gf.Vec3f(4.0, 2.0, 4.0))
        base.GetRootLayer().Save()
        effects.write_layer("pad", record, out)
        stage = Usd.Stage.Open(str(out / "pad.usda"))
        placed = UsdGeom.Xformable(stage.GetPrimAtPath("/pad/Fixtures/tank/flame")).ComputeLocalToWorldTransform(0.0)
        assert np.allclose(placed.ExtractTranslation(), [5.0, 2.0, 0.0]), placed
        assert np.allclose(np.linalg.norm(np.asarray(placed)[:3, :3], axis=1), 1.0), placed


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


def ball_ground(folder):
    """A flat planned ground on a 220 m ball, its seat leaning out of the world's y (so its up is no axis)."""
    from PIL import Image
    code = np.full((65, 65), round(20.0 / 40.0 * 65535), dtype=np.int64)
    Image.fromarray(np.stack([code >> 8, code & 255, np.zeros_like(code)], axis=-1).astype(np.uint8)).save(
        folder / "heights.png")
    Image.new("RGB", (64, 64), (128, 128, 128)).save(folder / "skin.jpg")
    record = {"heights": "heights.png", "skin": "skin.jpg", "side": 260.0, "low": 20.0, "span": 40.0,
              "radius": 220.0, "plan_out": [0.3, 0.9, 0.2], "folder": str(folder)}
    return effects.grounds.Ground(record, {"out": [0.3, 0.9, 0.2], "heading": 0.0}, [0.0, 0.0])


def test_the_wind_lies_along_the_ground():
    """On a place's ball the ground's up turns from spot to spot (28 m on a 220 m ball is 7 degrees): the wind is a
    unit way across the ground's up at every spot."""
    with tempfile.TemporaryDirectory() as folder:
        ground = ball_ground(pathlib.Path(folder))
    wind = {"minute": 8630, "turn_a_day": 0.9}  # a wind as an effects record gives it
    ups = []
    for across, along in [(0.0, 0.0), (0.0, 14.0), (14.0, 0.0), (-28.0, 28.0), (28.0, -28.0)]:
        _, up = effects.on_ground(ground, across, along, 0.0)
        way = effects.place_wind(ground, across, along, wind)
        assert math.isclose(float(np.linalg.norm(way)), 1.0, abs_tol=1e-9)
        assert abs(float(np.dot(way, up))) < 1e-6, (across, along, float(np.dot(way, up)))
        ups.append(up)
    assert not np.allclose(ups[3], ups[4], atol=1e-2), "the ground's up does not turn over the ball"


def main():
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print("ok", test.__name__)


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[2] / "conftest.py"))["refuse_outside_sandbox"]()
    main()
