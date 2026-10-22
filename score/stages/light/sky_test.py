"""The light layer's sky from the environment concept's physics (score/stages/light/sky.py) on stages made here,
against skies worked out by hand: a house on a plot under a far sun at its spring equinox noon (the sun 90 degrees
less the latitude up, due south), and environment 1's base on the Moon (the Earth about 1.9 degrees across, the Sun
about half a degree); the gate holds the layer to overhead.py and names what moved or is missing; the old sky is
turned off and the physics' sky left on."""
import json
import math

import numpy as np
import pytest
from pxr import Usd, UsdGeom, UsdLux

from score.review import overhead, setting
from score.stages.light import sky

HOUSE = setting.checked({
    "plots": [{"name": "Meadow", "gravity": 9.81}],
    "lights": [{"name": "Sun", "kelvin": 5800, "lux": 100000, "latitude": 52.0, "tilt_deg": 23.44, "day_hours": 24,
                "year_days": 365.2422, "equinox": "2024-03-20T12:00:00Z"}],
    "backdrops": [{"name": "Sky", "shape": "dome", "lux": 10000, "kelvin": 9000}],
    "sites": [{"place": "house", "on": "meadow", "x": 0, "y": 0}]})
ENVIRONMENT_1 = setting.now()
BASE = next(site for site in ENVIRONMENT_1["sites"] if site["place"] == "base")
WHEN = "2099-10-01T14:00:00Z"  # environment 1's scene time: the Sun 33 degrees over the base


def stage_of(place):
    stage = Usd.Stage.CreateInMemory()
    UsdGeom.Xform.Define(stage, f"/{place}")
    return stage


def shines(prim):
    """The way a distant light shines, its -z in the stage."""
    matrix = np.asarray(UsdGeom.XformCache().GetLocalToWorldTransform(prim), dtype=float)
    return np.array([0.0, 0.0, -1.0]) @ matrix[:3, :3]


def half_height(prim):
    points = np.asarray(UsdGeom.Mesh(prim).GetPointsAttr().Get(), dtype=float)
    return (points[:, 1].max() - points[:, 1].min()) / 2.0


def test_a_house_sun_at_its_equinox_noon_shines_from_due_south_38_degrees_up_and_the_sky_dome_lights():
    seen = overhead.seen(HOUSE, HOUSE["sites"][0], "2024-03-20T12:00:00Z")
    stage = stage_of("house")
    sky.write(stage, "house", seen)
    sun = stage.GetPrimAtPath("/house/Lights/sky_sun")
    rise = math.radians(90.0 - 52.0)
    assert np.allclose(shines(sun), [0.0, -math.sin(rise), -math.cos(rise)], atol=1e-3)  # x east, y up, z south
    assert UsdLux.DistantLight(sun).GetColorTemperatureAttr().Get() == 5800
    dome = UsdLux.DomeLight(stage.GetPrimAtPath("/house/Sky/Backdrops/sky"))
    assert dome.GetIntensityAttr().Get() == pytest.approx(10000 / math.pi / 683.0, rel=1e-6)
    assert not stage.GetPrimAtPath("/house/Sky/Bodies").GetChildren()  # a house's sky holds no worlds
    assert sky.faults(seen, sky.held(stage, "house")) == []


def test_the_earth_over_the_moon_base_is_a_ball_about_two_degrees_across_and_the_sun_half_a_degree():
    seen = overhead.seen(ENVIRONMENT_1, BASE, WHEN)
    stage = stage_of("base")
    sky.write(stage, "base", seen)
    earth = stage.GetPrimAtPath("/base/Sky/Bodies/earth")
    # the Earth's 6371 km radius at the Moon's 356500 to 406700 km: 1.79 to 2.05 degrees across
    assert 1800 * math.sin(math.radians(1.79 / 2)) < half_height(earth) < 1800 * math.sin(math.radians(2.05 / 2))
    sun = stage.GetPrimAtPath("/base/Sky/Discs/sun")
    # the Sun's 695700 km radius at 0.983 to 1.017 AU: 31.5 to 32.6 arc minutes
    assert 1800 * math.sin(math.radians(31.4 / 120)) < half_height(sun) < 1800 * math.sin(math.radians(32.7 / 120))
    assert earth.GetAttribute("score:surface").Get() == "earth_face"
    assert "body-face-earth" in earth.GetAttribute("score:surface:missing").Get()  # its face waits: named, never grey
    assert sky.faults(seen, sky.held(stage, "base")) == []


def test_a_body_is_painted_with_the_face_its_row_made(tmp_path):
    from pxr import UsdShade
    face = {"body": "earth", "surface": "earth_face", "family": "paint", "recipe": "painted_plaster",
            "token": "ocean-blue", "hex": "#1f4f8f", "colour": [0.0137, 0.0782, 0.2747], "roughness": 0.7, "metal": 0.0}
    (tmp_path / "body-face-earth").mkdir()
    (tmp_path / "body-face-earth/face.json").write_text(json.dumps(face))
    faces = sky.faces_of({"body-face-earth": str(tmp_path / "body-face-earth"), "sky": str(tmp_path / "none.json")})
    assert faces == {"earth": face}
    stage = stage_of("base")
    sky.write(stage, "base", overhead.seen(ENVIRONMENT_1, BASE, WHEN), faces=faces)
    earth = stage.GetPrimAtPath("/base/Sky/Bodies/earth")
    material = UsdShade.MaterialBindingAPI(earth).ComputeBoundMaterial()[0]
    assert material.GetPath() == "/base/Looks/earth_face" and not earth.HasAttribute("score:surface:missing")
    assert material.GetPrim().GetAttribute("score:from").Get() == "body-face-earth"
    shader = UsdShade.Shader(stage.GetPrimAtPath("/base/Looks/earth_face/surface"))
    assert tuple(shader.GetInput("diffuseColor").Get()) == pytest.approx(face["colour"], abs=1e-6)
    from score.stages import light
    assert earth.GetAttribute("score:face").Get() == "body-face-earth" and light.face_drawn(earth)
    assert not light.face_drawn(stage.GetPrimAtPath("/base/Sky/Bodies/mars"))  # its row has not run


def test_the_gate_names_a_world_moved_a_light_turned_and_a_backdrop_missing():
    seen = overhead.seen(ENVIRONMENT_1, BASE, WHEN)
    stage = stage_of("base")
    sky.write(stage, "base", seen)
    UsdGeom.Xformable(stage.GetPrimAtPath("/base/Sky/Bodies/earth")).AddTranslateOp().Set((300.0, 0.0, 0.0))
    UsdGeom.Xformable(stage.GetPrimAtPath("/base/Lights/sky_sun")).AddRotateXOp().Set(5.0)
    stage.GetPrimAtPath("/base/Sky/Backdrops/stars").SetActive(False)
    found = sky.faults(seen, sky.held(stage, "base"))
    assert any(fault.startswith("Earth: at azimuth") for fault in found), found
    assert any(fault.startswith("the light Sun: shines from") for fault in found), found
    assert any(fault.startswith("the backdrop Stars") for fault in found), found
    assert not any("Mars" in fault for fault in found), found


def test_a_world_overhead_left_out_and_one_not_overhead_are_faults():
    seen = overhead.seen(ENVIRONMENT_1, BASE, WHEN)
    stage = stage_of("base")
    sky.write(stage, "base", {**seen, "bodies": [body for body in seen["bodies"] if body["body"] != "mars"]})
    sky.write_body(stage, "base", {"body": "phobos", "azimuth": 10.0, "altitude": 20.0, "across": 0.1, "lit": 1.0})
    found = sky.faults(seen, sky.held(stage, "base"))
    assert any(fault.startswith("Mars: overhead") for fault in found), found
    assert "the body phobos: in the sky, but not overhead" in found, found


def test_the_old_sky_is_turned_off_and_the_physics_sky_left_on():
    stage = stage_of("wreck")
    UsdLux.DistantLight.Define(stage, "/wreck/Lights/sun_1")
    stars = UsdGeom.Mesh.Define(stage, "/wreck/Sky/Stars").GetPrim()
    stars.CreateAttribute("score:kind", text_type()).Set("stars")
    world = UsdGeom.Mesh.Define(stage, "/wreck/Structure/earth").GetPrim()
    world.CreateAttribute("score:plain", text_type()).Set("sky")
    wall = UsdGeom.Mesh.Define(stage, "/wreck/Structure/wall").GetPrim()
    off = sky.retired(stage, "wreck")
    assert sorted(off) == ["/wreck/Lights/sun_1", "/wreck/Sky/Stars", "/wreck/Structure/earth"], off
    assert wall.IsActive()
    sky.write(stage, "wreck", overhead.seen(ENVIRONMENT_1, BASE, WHEN))
    assert sky.retired(stage, "wreck") == []  # the physics' own sky is never the old one


def test_the_day_dome_is_scattered_from_the_brightest_light_the_way_it_shines():
    seen = overhead.seen(HOUSE, HOUSE["sites"][0], "2024-03-20T12:00:00Z")
    rise = math.radians(38.0)
    assert np.allclose(sky.sun_entries(seen)[0]["toward"], [0.0, -math.sin(rise), -math.cos(rise)], atol=1e-3)
    assert sky.sun_entries({**seen, "lights": []}) == []


def test_a_sun_under_the_horizon_lights_nothing_and_its_light_held_anyway_is_a_fault():
    # the house's equinox midnight: the sun as far under the horizon as it stands over it at noon, 90 - 52 = 38 degrees
    seen = overhead.seen(HOUSE, HOUSE["sites"][0], "2024-03-20T00:00:00Z")
    assert seen["lights"][0]["altitude"] == pytest.approx(-38.0, abs=0.5)
    stage = stage_of("house")
    written = sky.write(stage, "house", seen)
    assert written["lights"] == [] and not stage.GetPrimAtPath("/house/Lights/sky_sun")
    assert sky.sun_entries(seen) == []  # no day dome scattered from under the ground
    assert sky.faults(seen, sky.held(stage, "house")) == []
    sky.write_light(stage, "house", seen["lights"][0])  # a sky that shines it up through the ground anyway
    assert "the light sun: in the sky, but not overhead" in sky.faults(seen, sky.held(stage, "house"))


def text_type():
    from pxr import Sdf
    return Sdf.ValueTypeNames.String


def seed_with_old_sky(folder):
    """A seed stage whose record drew the old sky: a sun light and a star field."""
    (folder / "layers").mkdir(parents=True)
    base = Usd.Stage.CreateNew(str(folder / "layers/base.usda"))
    base.SetDefaultPrim(UsdGeom.Xform.Define(base, "/house").GetPrim())
    UsdLux.DistantLight.Define(base, "/house/Lights/sun_1")
    stars = UsdGeom.Mesh.Define(base, "/house/Sky/Stars").GetPrim()
    stars.CreateAttribute("score:kind", text_type()).Set("stars")
    base.Save()
    root = Usd.Stage.CreateNew(str(folder / "house.usda"))
    root.GetRootLayer().subLayerPaths.append("./layers/base.usda")
    root.Save()


def test_the_light_layer_writes_the_physics_sky_over_the_old_one_and_its_gate_holds_it_to_overhead(tmp_path):
    import json
    from score import checks
    from score.stages import light
    from score.stages.light import layer
    seed, out = tmp_path / "seed", tmp_path / "out"
    seed_with_old_sky(seed)
    kept = {"place": "house", "top": "house", "time": "2024-03-20T12:00:00Z", "setting": HOUSE,
            "site": {"on": "meadow", "x": 0.0, "y": 0.0, "height_m": 0.0}}
    (tmp_path / "sky.json").write_text(json.dumps(kept))
    found = layer.write("house", {"lights": []}, seed, out, kept)
    layer.lamps_file(found, out)
    assert sorted(found["sky"]["retired"]) == ["/house/Lights/sun_1", "/house/Sky/Stars"]
    composed = Usd.Stage.Open(str(seed / "house.usda"))
    composed.GetRootLayer().subLayerPaths.insert(0, str(out / layer.LAYER))
    assert not composed.GetPrimAtPath("/house/Lights/sun_1").IsActive()
    assert composed.GetPrimAtPath("/house/Lights/sky_sun").IsActive()
    verdict = light.judge_sky_bodies(out, {"sky": str(tmp_path / "sky.json")}, {})
    assert verdict.answer == checks.PASS, verdict
    (tmp_path / "later.json").write_text(json.dumps({**kept, "time": "2024-03-20T15:00:00Z"}))  # the sun 3 hours on
    verdict = light.judge_sky_bodies(out, {"sky": str(tmp_path / "later.json")}, {})
    assert verdict.answer == checks.FAIL and "the light Sun: shines from" in verdict.reason, verdict
    assert light.judge_sky_bodies(out, {}, {}).answer == checks.UNKNOWN
