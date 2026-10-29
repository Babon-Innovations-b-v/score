"""The light stage's invariant: a place is lit from its design and the environment concept's physics, and measured
against its concept, never against hand-kept numbers. Pinned through the stage's interface on pictures, passes and
stages made here, each answer worked out by hand:

- the sky (sky.py) is what overhead.py says at the site and time: a house's sun at its spring equinox noon shines from
  due south 90 - 52 = 38 degrees up; on the Moon base the Earth is 1.79 to 2.05 degrees across, the Sun 31.5 to 32.6
  arc minutes; a sun under the horizon lights nothing; the gate names a world moved, a light turned, a backdrop or a
  world missing; the old sky is turned off; a body is drawn from the face its row made, a sun's disc from the
  library's glowing recipe, never grey;
- the measures (measure.py) read halo, fill, discs lit from their sun, sky colour, veil and a point's pixel;
- the sweep (mix.py) finds the scale that brings a look to a target (a lamp at twice its strength), turns a blown lamp
  down and names an unlit one;
- the layer (layer.py) moves a seed lamp to a record lamp near it, adds one far from any, writes strengths, adds the
  concept's fill only where no sky light reaches, and writes no glow nobody asked for;
- the rows read the design only (the owner's rule of 2026-10-21: a wording check of the declared files guards it), and
  past faults stay fixed: the strengths saved over the read-only input (2026-10-12, light@camp), a shown place's
  pictures moved away (2026-10-18), score/stages put on sys.path (Buy of 2026-10-24), Blender's magenta.

Breaks that turn these red (each applied once, seen red, reverted, 2026-10-26):
- sky.py: the light's direction negated in `write_light` (the house sun test).
- measure.where: `x = size[0] / 2 + ...` off by its focal (the where test).
- measure.veil: the lower rows read as the upper (the veil test).
- mix.sweep: return 1.0 always (the sweep test).
- mix.lamp_faults: never "blown" (the sweep test).
- layer.strengths: write the strength unscaled (the layer test).
- light.unlit_why: an inside place lit by a sun alone counted lit (the unlit test).
- light.fill_wanted: ignore `unseen` (the fill test).
- light.body_faults: drop the "not lit from its sun" fault (the discs test).
- light.judge_exposure: pass with no concept (the exposure test).
- passes.judge_magenta: the magenta share always 0 (the magenta test).
- passes.neighbours: keep a planless shown place (the neighbours test).
- mix.tone_curve: the one-knot curve of a black view dropped (the black view test, 2026-10-29).
- light.drawn_count: the sky's prims counted (the drawn test, 2026-10-29).
- passes.source: `grounded.take_bakes(...)` dropped, or `record.take_ground(...)` dropped (the laid test, 2026-10-29).
"""
import json
import math
import os
import pathlib
import shutil
import stat
import subprocess
import sys

import numpy as np
import pytest
from PIL import Image
from pxr import Gf, Sdf, Usd, UsdGeom, UsdLux, UsdShade

from score import checks
from score.review import overhead, setting
from score.stages import light
from score.stages.light import haze, layer, measure, mix, needs, passes, sky
from score.stages.terrain import needs as ground_needs
from score.store import Store

REPO = pathlib.Path(__file__).resolve().parents[3]
SIZE = 200
WIDE = 480

HOUSE = setting.checked({
    "plots": [{"name": "Meadow", "gravity": 9.81}],
    "lights": [{"name": "Sun", "kelvin": 5800, "lux": 100000, "latitude": 52.0, "tilt_deg": 23.44, "day_hours": 24,
                "year_days": 365.2422, "equinox": "2024-03-20T12:00:00Z"}],
    "backdrops": [{"name": "Sky", "shape": "dome", "lux": 10000, "kelvin": 9000}],
    "sites": [{"place": "house", "on": "meadow", "x": 0, "y": 0}]})
ENVIRONMENT_1 = setting.now()
BASE = next(site for site in ENVIRONMENT_1["sites"] if site["place"] == "base")
WHEN = "2099-10-01T14:00:00Z"  # environment 1's scene time: the Sun 33 degrees over the base


# --- the sky from the physics ---------------------------------------------------------------------------------------

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


def text_type():
    return Sdf.ValueTypeNames.String


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
    # the day dome is scattered from the brightest light, the way it shines
    assert np.allclose(sky.sun_entries(seen)[0]["toward"], [0.0, -math.sin(rise), -math.cos(rise)], atol=1e-3)
    assert sky.sun_entries({**seen, "lights": []}) == []


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
    assert earth.GetAttribute("score:face").Get() == "body-face-earth" and light.face_drawn(earth)
    assert not light.face_drawn(stage.GetPrimAtPath("/base/Sky/Bodies/mars"))  # its row has not run


def test_the_gate_names_a_world_moved_a_light_turned_a_backdrop_missing_and_a_world_left_out():
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


def test_the_sun_s_disc_is_the_library_s_glowing_recipe_in_its_black_body_colour_and_no_placeholder(tmp_path):
    sys.path.insert(0, str(sky.REPO / "tools/usd"))
    import placeholders
    library = json.loads((sky.REPO / "data/library/materials.json").read_text())
    stage = stage_of("base")
    stage.SetDefaultPrim(stage.GetPrimAtPath("/base"))
    sky.write(stage, "base", overhead.seen(ENVIRONMENT_1, BASE, WHEN), library=library)
    disc = stage.GetPrimAtPath("/base/Sky/Discs/sun")
    material = UsdShade.MaterialBindingAPI(disc).ComputeBoundMaterial()[0]
    assert material.GetPath() == "/base/Looks/sun_disc" and not disc.HasAttribute("score:surface:missing")
    assert material.GetPrim().GetAttribute("score:recipe").Get() == "glowing"
    glow = UsdShade.Shader(stage.GetPrimAtPath("/base/Looks/sun_disc/surface")).GetInput("emissiveColor").Get()
    assert glow[0] == pytest.approx(1.0, abs=0.01) and glow[2] < glow[0]  # 5772 K: white, a little warm
    stage.GetRootLayer().Export(str(tmp_path / "base.usda"))
    assert [fault for fault in placeholders.check(tmp_path / "base.usda") if "/Discs/" in fault["prim"]] == []


# --- the measures on pictures made here ----------------------------------------------------------------------------

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


def test_a_floodlight_bank_of_lit_panes_has_no_halo_and_one_glowing_into_the_air_has():
    grid, glow = measure.head(grid_bank(), 240, 240, 40), measure.head(glowing_bank(), 240, 240, 40)
    assert grid["halo"] < 0.02 and grid["fill"] < 0.1, grid
    assert glow["halo"] > 0.08 and glow["fill"] > 0.28, glow


def test_a_disc_lit_from_its_sun_passes_and_one_lit_from_the_other_side_or_lost_fails():
    """A body's disc lit on its right half over a black sky shows and is lighter toward the sun on the right; the
    gate's rules fail the same disc judged with its sun on the left, and a disc lost in the sky."""
    rows, columns = np.mgrid[0:SIZE, 0:SIZE]
    lit = np.zeros((SIZE, SIZE, 3))
    disc = np.hypot(columns - 100, rows - 100) < 40
    lit[disc & (columns >= 100)] = [150, 150, 160]
    lit[disc & (columns < 100)] = [12, 12, 14]
    usable = np.ones((SIZE, SIZE), dtype=bool)
    right = measure.body(lit, 100, 100, 40, (1.0, 0.0), usable)
    assert right["shown"] > 0.45 and right["sunward"] > right["away"] + 50, right
    left = measure.body(lit, 100, 100, 40, (-1.0, 0.0), usable)
    lost = measure.body(np.zeros((SIZE, SIZE, 3)), 100, 100, 40, (1.0, 0.0), usable)
    assert lost["shown"] == 0.0 and measure.body(lit, 100, 100, 40, (1.0, 0.0), ~usable) is None

    def entry(after, sun_seen=True, lit_share=0.5):
        return {"body": "a", "view": "v", "lit": lit_share, "sun_seen": sun_seen, "after": after}
    assert light.body_faults([entry(right)]) == []
    assert any("not lit from its sun" in fault for fault in light.body_faults([entry(left)]))
    assert light.body_faults([entry(left, sun_seen=False)]) == []  # its sun along the view: not judged
    assert light.body_faults([entry(left, lit_share=0.98)]) == []  # nearly full: no dark side to judge
    assert any("shown in none" in fault for fault in light.body_faults([entry(lost)]))
    assert light.body_faults([entry(lost), entry(right)]) == []  # shown in one of the views framing it


def test_a_sky_s_colour_blue_to_red_and_rise_are_read_on_the_pixels_the_flat_sky_held():
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
    black = np.zeros((SIZE, SIZE, 3))
    near_black = np.full((SIZE, SIZE, 3), [1.33, 1.4, 1.3])
    assert measure.sky_of(black, measure.sky_pixels(black))["blue_to_red"] == 1.0  # no hue, never "red"
    assert abs(measure.sky_of(near_black, measure.sky_pixels(near_black))["blue_to_red"] - 1.0) < 0.05


def test_haze_over_the_lower_part_reads_as_a_veil_and_glow_in_the_sky_does_not():
    before = np.full((100, 100, 3), 40.0)
    after = before.copy()
    after[:50] += 100.0  # a lamp's glow up in the sky leaves the place below as it was
    assert measure.veil(before, after) == 0.0
    after[60:] += 30.0  # haze laid over the place's lower part
    assert abs(measure.veil(before, after) - 30.0 / 255.0) < 1e-3


def test_a_point_straight_ahead_falls_in_the_pictures_middle_and_one_behind_nowhere():
    view = {"eye": [0, 0, 0], "aim": [0, 0, -10], "up": [0, 1, 0], "fov": 90}
    x, y, depth, focal = measure.where(view, (200, 100), [0, 0, -5])
    assert (round(x), round(y), round(depth, 6), round(focal, 6)) == (100, 50, 5.0, 100.0)
    assert measure.where(view, (200, 100), [0, 0, 5])[0] is None


def test_a_view_far_blacker_or_more_blown_than_its_concept_fails_and_with_no_concept_is_unknown(tmp_path):
    half_black = np.concatenate([np.zeros((10, 20)), np.full((10, 20), 0.5)])
    assert light.extremes(half_black) == {"black": 0.5, "blown": 0.0}
    for concept, views, answer in (({"black": 0.45, "blown": 0.0}, {"wide": {"black": 0.5, "blown": 0.01}}, checks.PASS),
                                   ({"black": 0.01, "blown": 0.0}, {"wide": {"black": 0.2, "blown": 0.0}}, checks.FAIL),
                                   ({"black": 0.0, "blown": 0.0}, {"wide": {"black": 0.0, "blown": 0.05}}, checks.FAIL),
                                   (None, {"wide": {"black": 0.0, "blown": 0.0}}, checks.UNKNOWN)):
        (tmp_path / "measures.json").write_text(json.dumps({"exposure": {"concept": concept, "views": views}}))
        assert light.judge_exposure(tmp_path, {}, {}).answer == answer, (concept, views)


def test_a_look_with_one_percent_of_blenders_missing_texture_magenta_fails(tmp_path):
    (tmp_path / "passes/tiny-0").mkdir(parents=True)
    clean = np.full((100, 100, 3), (120, 110, 100), np.uint8)
    Image.fromarray(clean).save(tmp_path / "passes/tiny-0/shot0-000-look.png")
    assert passes.judge_magenta(tmp_path, {}, {}).answer == checks.PASS
    clean[:10, :10] = (193, 79, 136)  # the tube's hub through its hatch, 2026-10-16
    Image.fromarray(clean).save(tmp_path / "passes/tiny-0/shot0-000-look.png")
    verdict = passes.judge_magenta(tmp_path, {}, {})
    assert verdict.answer == checks.FAIL and verdict.measures["magenta share"] == 0.01, verdict


# --- the sweep on passes made here ----------------------------------------------------------------------------------

def toned_look(light_in):
    """A look made from light by a known tone curve (light over one plus light)."""
    return light_in / (1.0 + light_in)


def test_the_sweep_finds_the_lamps_scale_turns_a_blown_lamp_down_and_names_an_unlit_one():
    rest = np.tile(np.linspace(0.01, 0.1, 60), (40, 1))
    lamp = np.tile(np.linspace(0.0, 4.0, 40)[:, None], (1, 60))
    lamp[:, 30:] = 0.0
    views_passes = {"combined": rest + lamp, "lamp_0": lamp, "lamp_1": np.zeros((40, 60))}
    views = {"v": (views_passes, mix.tone_curve(views_passes["combined"], toned_look(views_passes["combined"])))}
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


def test_a_black_view_is_measured_black_not_a_crash():
    """Fault (2026-10-29, light@base): every view's light all zero gave the tone curve no knots and the sweep crashed in
    np.interp, where the brightness gate should fail it by name."""
    black = {"combined": np.zeros((20, 30)), "lamp_0": np.zeros((20, 30))}
    views = {"v": (black, mix.tone_curve(black["combined"], np.full((20, 30), 0.0003)))}
    assert mix.place_brightness(views, {}) == pytest.approx(0.0003)
    assert not mix.within(views, {"lamp_0": mix.sweep(views, ["lamp_0"], 0.3)}, 0.3)


def test_a_stage_drawing_nothing_but_its_sky_is_named_before_the_paid_render(tmp_path):
    """Fault (2026-10-29, light-passes@base): every object of the record waited on its model and no ground was laid,
    so the stage drew nothing and rendered black under its sun; the light layer's `drawn` gate counts what it lights."""
    stage = Usd.Stage.CreateNew(str(tmp_path / "tiny.usda"))
    UsdGeom.Xform.Define(stage, "/tiny")
    UsdGeom.Sphere.Define(stage, "/tiny/Sky/Bodies/earth")
    stage.Save()
    assert light.drawn_count(tmp_path / "tiny.usda", "tiny") == 0
    UsdGeom.Cube.Define(stage, "/tiny/Objects/hub")
    stage.Save()
    assert light.drawn_count(tmp_path / "tiny.usda", "tiny") == 1


def test_the_stage_lit_lays_the_bakes_models_and_the_made_ground(tmp_path, monkeypatch):
    """Fault (2026-10-29, light-passes@base and @airlock): the lit stage was the seed with its record, every design
    object waiting on the surface line's bake and no made ground, so base drew nothing and airlock a bare shell. The
    stage is laid by the assembly's own code: the bake's model at its waiting entry, the made ground over the base."""
    import score.stages.assembly.baked as baked
    tiny_seed(tmp_path / "seed")
    (tmp_path / "record/record").mkdir(parents=True)
    hub = {"name": "hub_1", "row": "hub", "bake": "hub_1", "kind": "object", "at": [0.0, 0.0, 0.0],
           "rotation": [0.0, 0.0, 0.0, 1.0], "waiting": "its model comes from the bake"}
    (tmp_path / "record/record/tiny.json").write_text(json.dumps({"place": "tiny", "objects": [hub]}))
    (tmp_path / "kit.json").write_text(json.dumps({"pieces": []}))
    (tmp_path / "surfaces.json").write_text("{}")
    (tmp_path / "bake/made").mkdir(parents=True)
    (tmp_path / "bake/baked.json").write_text(json.dumps({"hub_1": {}}))
    (tmp_path / "bake/made/hub_1.gltf").write_text("{}")  # what the laid model's hash is stamped from
    (tmp_path / "terrain/grounds/places").mkdir(parents=True)
    ground = Usd.Stage.CreateNew(str(tmp_path / "terrain/grounds/places/tiny.usdc"))
    UsdGeom.Cube.Define(ground, "/tiny/Terrain/ground")
    ground.Save()

    def made(bake, paint, out, models=None):  # the bake's asset as take_bake writes it, without its paint
        asset = Usd.Stage.CreateNew(str(out / "assets/hub_1.usdc"))
        asset.SetDefaultPrim(UsdGeom.Xform.Define(asset, "/hub_1").GetPrim())
        UsdGeom.Cube.Define(asset, "/hub_1/geo")
        asset.Save()
    monkeypatch.setattr(baked, "take_bake", made)
    inputs = {"seed": str(tmp_path / "seed"), "scene-record": str(tmp_path / "record"),
              "kit": str(tmp_path / "kit.json"), "surfaces": str(tmp_path / "surfaces.json"),
              "surfaces-bake": str(tmp_path / "bake"), "surfaces-paint": str(tmp_path / "bake"),
              "terrain": str(tmp_path / "terrain")}
    root = passes.source("tiny", inputs, tmp_path / "lit") / "tiny.usda"
    stage = Usd.Stage.Open(str(root))
    assert stage.GetPrimAtPath("/tiny/Objects/hub_1").IsValid() and stage.GetPrimAtPath("/tiny/Terrain/ground")
    assert light.drawn_count(root, "tiny") == 2


# --- the layer on a stage made here ---------------------------------------------------------------------------------

def tiny_seed(seed):
    """A seed stage with one lamp, /tiny/Lights/light_1 at (0, 2, 0), intensity 10."""
    (seed / "layers").mkdir(parents=True)
    base = Usd.Stage.CreateNew(str(seed / "layers/base.usda"))
    base.SetDefaultPrim(UsdGeom.Xform.Define(base, "/tiny").GetPrim())
    UsdGeom.Scope.Define(base, "/tiny/Lights")
    lamp = UsdLux.SphereLight.Define(base, "/tiny/Lights/light_1")
    lamp.CreateIntensityAttr(10.0)
    lamp.AddTranslateOp().Set(Gf.Vec3d(0.0, 2.0, 0.0))
    base.Save()
    root = Usd.Stage.CreateNew(str(seed / "tiny.usda"))
    root.GetRootLayer().subLayerPaths.append("./layers/base.usda")
    root.Save()


def test_a_record_lamp_near_a_seed_lamp_moves_it_one_far_is_added_and_the_strengths_land(tmp_path):
    seed, out = tmp_path / "seed", tmp_path / "out"
    tiny_seed(seed)
    record = {"lights": [{"type": "omni", "at": [1.0, 2.0, 0.0], "energy": 1.0, "colour": "#ffffff"},
                         {"type": "spot", "at": [20.0, 2.0, 0.0], "aim": [20.0, 0.0, 0.0], "angle": 30.0,
                          "energy": 1.0, "colour": "#ffffff"}]}
    found = layer.write("tiny", record, seed, out)
    assert [entry["done"] for entry in found["placed"]] == ["moved 1.00 m", "added"], found["placed"]
    moved = next(lamp for lamp in found["lamps"] if lamp["path"] == "/tiny/Lights/light_1")
    assert moved["spot"] == [1.0, 2.0, 0.0] and not moved["shaped"], moved
    layer.strengths(out / layer.LAYER, "tiny", {"/tiny/Lights/light_1": (10.0, 0.5)})
    held = Usd.Stage.Open(str(out / layer.LAYER))
    assert held.GetPrimAtPath("/tiny/Lights/light_1").GetAttribute("inputs:intensity").Get() == 5.0


def test_no_camera_glow_is_written_from_a_record_that_holds_none(tmp_path):
    """The scene record, written from the design alone, holds no glow (the old sky record's night glow was the game's,
    retired 2026-10-21)."""
    seed = tmp_path / "seed"
    tiny_seed(seed)
    base = Usd.Stage.Open(str(seed / "layers/base.usda"))
    UsdLux.DomeLight.Define(base, "/tiny/Environment")
    base.Save()
    layer.write("tiny", {"lights": [], "environment": {"inside": False}}, seed, tmp_path / "dark")
    dark = Usd.Stage.Open(str(tmp_path / "dark" / layer.LAYER))  # held while its prim is read
    held = dark.GetPrimAtPath("/tiny/Environment")
    assert not held or not held.HasAttribute("score:glow_threshold")


def test_a_place_lit_by_nothing_in_its_design_is_named_before_the_paid_render():
    """No light at all, or an inside place lit only by the sky's lights outside its shell."""
    lamp, sun = {"path": "/p/Lights/lamp_1"}, {"path": "/p/Lights/sky_sun", "sun": True}
    assert light.unlit_why([], inside=False) and light.unlit_why([], inside=True)
    assert light.unlit_why([sun], inside=True) and light.unlit_why([sun], inside=False) is None
    assert light.unlit_why([lamp], inside=True) is None and light.unlit_why([lamp, sun], inside=False) is None
    fill = {"path": "/p/Lights/concept_fill", "sun": True, "fill": True}
    assert light.unlit_why([sun, fill], inside=True) is None and "not read" in light.unlit_why([], False, read=False)


@pytest.mark.parametrize("inside, kind", ((False, UsdLux.DistantLight), (True, UsdLux.SphereLight)))
def test_the_concepts_fill_comes_only_where_no_sky_light_reaches(tmp_path, inside, kind):
    """A concept showing light from no source in view takes its fill where no sky light reaches the place (none over
    the horizon, or inside its shell), never where the concept shows none or a sun lights it in the open; the fill is
    a soft overhead distant light in the open, a sphere light under the ceiling over the middle inside."""
    seen = {"rows": {}, "scene": {"daylight": True, "unseen": True, "unseen_colour": "#ffddbb"}}
    sun = {"path": "/p/Lights/sky_sun", "sun": True}
    assert light.fill_wanted(seen, [], inside=False) and light.fill_wanted(seen, [sun], inside=True)
    assert not light.fill_wanted(seen, [sun], inside=False) and not light.fill_wanted(None, [], inside=True)
    assert not light.fill_wanted({**seen, "scene": {**seen["scene"], "unseen": False}}, [], inside=True)
    seed, out = tmp_path / "seed", tmp_path / "out"
    tiny_seed(seed)
    base = Usd.Stage.Open(str(seed / "layers/base.usda"))
    UsdGeom.Cube.Define(base, "/tiny/Room").CreateSizeAttr(6.0)  # a room 6 m across round the middle
    base.Save()
    layer.write("tiny", {"lights": []}, seed, out)
    found = layer.write_fill(out, seed, "tiny", "#ffddbb", inside, 3.0, REPO / "data/library/lamps.json")
    opened = Usd.Stage.Open(str(out / layer.LAYER))  # held while its prim is read
    held = opened.GetPrimAtPath(found["path"])
    assert held.IsA(kind) and found["fill"] and found["sun"], found
    assert (found["spot"] is None) != inside and (not inside or found["spot"][1] < 3.0), found


def test_the_strengths_are_written_into_a_copy_and_the_read_only_input_stays(tmp_path):
    """Fault (2026-10-12, light@camp): the strengths were saved over the input layer, a read-only checkout."""
    seed, made, out = tmp_path / "seed", tmp_path / "made", tmp_path / "out"
    tiny_seed(seed)
    layer.write("tiny", {"lights": []}, seed, made)
    views = {"views": [{"name": "door", "eye": [0, 1.6, 2], "aim": [0, 1.2, 0], "fov": 70}]}
    (made / passes.VIEWS).write_text(json.dumps(passes.record_views(views)))
    before = (made / layer.LAYER).read_bytes()
    for path in made.rglob("*"):
        os.chmod(path, stat.S_IREAD | (stat.S_IEXEC if path.is_dir() else 0))
    try:
        light.layer_copied(made, out)
        layer.strengths(out / layer.LAYER, "tiny", {"/tiny/Lights/light_1": (10.0, 2.0)})
        assert (made / layer.LAYER).read_bytes() == before
        size, copied = passes.views_of(out)  # the record's views, at the check size, travel with the layer
        assert size == passes.CHECK_SIZE and copied[0]["up"] == [0.0, 1.0, 0.0] and copied[0]["frame"] == 0
    finally:
        for path in made.rglob("*"):
            os.chmod(path, stat.S_IRWXU)


def test_a_shown_place_keeps_its_pictures(tmp_path):
    """Fault (2026-10-18, light-passes of ten places): a shown place's light layer was written into its seed's copy in
    the lit tree, and the writer moved that copy's own pictures into assets/light, so its materials drew magenta."""
    seed, tree = tmp_path / "seed", tmp_path / "tree"
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


# --- the rows read the design only ----------------------------------------------------------------------------------

def test_what_an_outdoor_place_needs_lit_comes_from_its_plan_and_kept_sky(tmp_path, monkeypatch):
    """An outdoor place the design stands on no ground lacks its seat and its sky until its kept sky has a site and a
    scene time; a room under a roof needs neither, whatever an old hand-kept record beside it says; a place with no
    plan adds nothing."""
    data = tmp_path
    for folder in ("scene", "plans", "definitions", "skies"):
        (data / folder).mkdir(parents=True)
    skies = data / "skies"
    (data / "plans/yard.json").write_text(json.dumps({"shell": "outdoor", "w": 10.0, "d": 10.0}))
    (data / "plans/room.json").write_text(json.dumps({"shell": "kit", "inside": True}))
    (data / "scene/room.json").write_text(json.dumps({"environment": {"inside": False}, "views": []}))
    (data / "scene/oldonly.json").write_text(json.dumps({"environment": {"inside": False}, "views": []}))
    monkeypatch.setattr(needs, "KEPT_PLANS", data / "plans")

    def ids(place):
        return sorted(gap["id"] for gap in needs.gaps(place, data, skies) +
                      ground_needs.gaps(place, data, data / "plans", skies))
    assert ids("yard") == ["ground:seat:yard", "sky:site:yard"], ids("yard")
    house = {"plots": [{"name": "Rock", "gravity": 9.81}], "sites": [{"place": "yard", "on": "rock", "x": 0, "y": 0}],
             "lights": [{"name": "Sun", "kelvin": 5800, "lux": 100000, "latitude": 52.0, "tilt_deg": 23.44,
                         "day_hours": 24, "year_days": 365.2422, "equinox": "2024-03-20T12:00:00Z"}]}
    (skies / "yard.json").write_text(json.dumps({"place": "yard", "top": "yard", "time": "2024-06-01T12:00:00Z",
                                                 "site": {"on": "rock", "x": 0, "y": 0, "height_m": 0},
                                                 "setting": setting.checked(house)}))
    assert ids("yard") == [], ids("yard")
    assert needs.gaps("room", data, skies) == []
    assert needs.gaps("oldonly", data, skies) == [] and ids("nowhere") == []


def test_the_rows_read_the_scene_record_output_never_a_hand_kept_record(tmp_path):
    """Owner's rule of 2026-10-21 (wording check of the declared files): no row declares a record in data/scene; the
    record is the scene-record output's (a shown place's read beside), and a place with no kept plan has no row."""
    assert not light.applies("far_city") and not light.applies(None)
    for place in ("launch", "square", "hub"):
        for files in (light.layer_files, light.light_files, passes.passes_files):
            assert not [path for path in files(place).values() if path.startswith("{data}/scene")], (place, files)
    inputs = {}
    for node, place in (("scene-record", "launch"), ("scene-record@square", "square")):
        (tmp_path / node / "record").mkdir(parents=True)
        (tmp_path / node / "record" / f"{place}.json").write_text(json.dumps({"place": place, "lights": []}))
        inputs[node] = str(tmp_path / node)
        kit = tmp_path / f"{place}-kit.json"  # the design's kit, as earth-seed writes it
        kit.write_text(json.dumps({"room": place, "pieces": []}))
        inputs["kit" if place == "launch" else f"kit {place}"] = str(kit)
    assert passes.place_of(inputs) == "launch" and passes.shown_in(inputs) == ["square"]
    assert passes.record_of("square", inputs)["place"] == "square"
    assert light.lamp_heads("launch", inputs) == []  # no kit lays a shafted lamp: no floodlight head


def test_the_floodlights_are_the_glowing_rows_the_plan_aims_that_the_kit_lays(tmp_path, monkeypatch):
    rows = [{"id": "mast_lamp", "name": "mast lamp"}, {"id": "desk", "name": "desk"}]
    aims = {"yard": {"mast_lamp": {"at": "pad"}}, "hall": {}, "shed": {"desk": {"at": "pad"}}}
    for kind in ("design/plans", "design/inventory"):
        (tmp_path / kind).mkdir(parents=True)
    for place, aimed in aims.items():
        (tmp_path / f"design/plans/{place}.json").write_text(json.dumps({"aims": aimed}))
        (tmp_path / f"design/inventory/{place}.json").write_text(json.dumps({"rows": rows}))
    monkeypatch.setattr(passes, "KEPT", tmp_path / "design")
    laid = {place: {"room": place, "pieces": [{"kind": f"{place}_{row['id']}", "part": "glow"} for row in rows]}
            for place in aims}
    assert haze.shafted_rows("yard") == {"mast_lamp"}
    # fault (Buy of 2026-10-24): glowing put score/stages on sys.path, so the assembly's `import sound` took the
    # sound stage package for tools/usd/sound.py and failed on audio_prim
    stages = str(pathlib.Path(haze.__file__).resolve().parents[1])
    assert stages not in [str(pathlib.Path(entry).resolve()) for entry in sys.path if entry], sys.path
    assert haze.shafted_kinds("yard", laid["yard"]) == {"yard_mast_lamp"}
    assert not haze.shafted_kinds("hall", laid["hall"]) and not haze.shafted_kinds("shed", laid["shed"])
    assert not haze.shafted_kinds("yard", {"room": "yard", "pieces": []})


def test_the_places_shown_are_the_accepted_records_with_a_kept_plan(tmp_path, monkeypatch):
    """Never an old hand-kept record's: none before the record stands accepted, a planless one left out."""
    record = {"place": "flat", "places": [{"stage": "wreck"}, {"stage": "far_city"}, {"stage": "flat"}]}

    class Accepted:
        def __init__(self, held):
            self.held = held

        def accepted(self, node):
            return "output" if node in self.held else None

        def read_file(self, output, name):
            return self.held["scene-record@flat"] if name == "record/flat.json" else None

    monkeypatch.setattr(passes, "KEPT", tmp_path)
    (tmp_path / "plans").mkdir()
    (tmp_path / "plans/wreck.json").write_text(json.dumps({"leads": {}}))
    monkeypatch.setattr(Store, "default", classmethod(lambda cls: Accepted({"scene-record@flat": record})))
    assert passes.neighbours("flat") == ["wreck"]
    monkeypatch.setattr(Store, "default", classmethod(lambda cls: Accepted({})))
    assert passes.neighbours("flat") == []
