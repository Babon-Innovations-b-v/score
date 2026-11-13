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
  concept's fill wherever the concept shows unseen light, and writes no glow nobody asked for;
- the rows read the design only (the owner's rule of 2026-10-21: a wording check of the declared files guards it), and
  past faults stay fixed: the strengths saved over the read-only input (2026-10-12, light@camp), a shown place's
  pictures moved away (2026-10-18), score/stages put on sys.path (Buy of 2026-10-24), Blender's magenta, read on the
  surface colour, never a lamp's (2026-10-30).

Breaks that turn these red (each applied once, seen red, reverted, 2026-10-26; "the measures' table" is the rows of
measures read on pictures and passes made here in test_light_measured_against_design, with its verdict rows, the
checks' answers on measures files; "the layer's rows" are the lamp placement rows on seeds made here in it and the
layer's checks after them: strengths, colours, the eye, the fill):
- sky.py: the light's direction negated in `write_light` (the sky test, test_light_measured_against_design: the house
  sun; this and the other sky test breaks proved again 2026-11-13).
- sky.through_dust: the forward peak left out of the beam (depth not delta-scaled), or `dust` not passed on in
  `write`, or the share written on the airless Moon's sun too (the sky test: Mars' and the Moon base's suns,
  2026-11-10).
- measure.where: `x = size[0] / 2 + ...` off by its focal; its look-along-its-up refusal dropped (the measures'
  table: the where rows, proved 2026-11-13; round 33's spot-1 at shiplock looked straight down, up (0, 1, 0), and
  every measure was NaN, 2026-10-30).
- measure.veil: the lower rows read as the upper (the measures' table: the veil rows; proved
  2026-11-13).
- mix.sweep: return 1.0 always (the sweep test).
- mix.lamp_faults: never "blown" (the sweep test).
- layer.strengths: write the strength unscaled (the layer's rows).
- layer.placed_lamps: `free = {path: (lamps_along.laid_at(stage, path, spot), shaped) ...}` -> `free = {path: (spot,
  shaped) ...}` (the layer's rows: a lamp the assembly carried out of a wall with its floor light put back 5 cm inside
  it; light@walkway's spot-2 at 0.079 against its concept's 0.237, 2026-11-12).
- layer.place_middle: the stage's bound for an inside place too (the layer's rows: the ceiling lamp in its fixture, 2026-10-30).
- layer.lamps_through_fixtures: a lamp with no holder of at most FIXTURE_MOST skipped, the old rule (the layer's rows: the
  lamp closed in a post's head, 2026-10-31: kept, every way out stopped).
- light.unlit_why: an inside place lit by a sun alone counted lit (the measures' table: the unlit rows).
- night.is_night: always true; night.scale_of: inside and outside swapped; night.skyglow_of: `within_km` ignored;
  night.roofed: `>= ROOFED_LEAST` -> `> 0`; night.write_layer: `layer.Save()` dropped;
  night.colour: `dark` ignored; night.body_lux: the radius over the distance not squared (the sky
  test: the night, 2026-11-10).
- light.fill_wanted: ignore `unseen` (the layer's rows: the fill); no fill beside a sun, the old rule (the layer's rows: the fill, 2026-10-30).
- light.body_faults: drop the "not lit from its sun" fault (the measures' table: the disc rows; proved
  2026-11-13).
- light.judge_exposure: pass with no concept (the measures' table: the verdict rows).
- light.extremes: `sky` ignored (the Moon look fails), or `luminance[sky]` for `luminance[~sky]` (the dark and blown
  looks pass) (the measures' table: the verdict rows, 2026-10-30).
- light_passes.sky_mask: `== 0` -> `!= 0` (the measures' table: the sky mask row, 2026-10-30; proved
  2026-11-13).
- light.sky_measures: the look's sky read by measure.sky_pixels, not its passes' mask (the look's sky test,
  2026-10-30).
- passes.judge_magenta: the share read times 0 (the measures' table: the magenta rows, 2026-10-30; proved
  2026-11-13).
- mix.sweep: `most` ignored; mix.own_share: the lamp's light left unscaled (`scales.get(group, 1.0) *` dropped) (the
  sweep test, 2026-11-04).
- mix.own_share: the share read on the pixels' mixed light (`mixed(passes, scales).sum()`), the light no group holds
  scaled, or left out (the sweep test, 2026-11-10: tube's denoiser noise read as half its light).
- light.strengths: a lamp-lit place's lamps swept only to the top of mix.SCALES, or a daylit place's to the top of
  mix.LAMP_SCALES (the sun-swept test, 2026-11-10: hangar's lamps stopped at x32).
- light.strengths: `first` always {} (a lamp-lit place's suns not at the floor), or the suns' sweep without
  `mix.SUN_MOST`; light.judge_source: the lamp share rule or the sun rule dropped (the sun-swept test, 2026-11-04).
- measure.surface_cast: brightness left in (`* 128.0 / ...` dropped); light.judge_colour: `gap <= CAST_MOST` ->
  `True` (the measures' table: the cast and verdict rows, 2026-11-04).
- measure.backdrop: every near pixel taken, not only those joined to the border, or the border's share rule dropped;
  light.concept_cast: the backdrop not left out (the measures' table: the cast rows, 2026-11-10).
- light.row_skies: the rows' boxes read as [top, left, bottom, right] (the look's sky test, 2026-11-04).
- light.row_skies: the boxes read whole, not on measure.commonest_near (the look's sky test, 2026-11-10).
- light.open_sky: the doorways not left out (`return mask` first), or light.through_doorways' `reach > 0` dropped
  (the look's sky test, 2026-11-10: hub's door openings read as its sky).
- light_passes.missing_share: the glossy colour pass left out (the measures' table: the missing picture row,
  2026-10-30; proved 2026-11-13).
- passes.neighbours: keep a planless shown place (the measures' table: the places shown rows).
- mix.tone_curve: the one-knot curve of a black view dropped (the measures' table: the black view rows, 2026-10-29).
- light.drawn_count: the sky's prims counted (the measures' table: the drawn row, 2026-10-29).
- passes.source: `grounded.take_bakes(...)` dropped, or `record.take_ground(...)` dropped (the laid test, 2026-10-29).
- passes.device_for: `need > card_gb * 2**30` -> `False` (the measures' table: the card rows, 2026-10-29; proved
  2026-11-13).
- layer.write_fill: the fill's height from anywhere but the record's ceiling, e.g. the stage's bound (the layer's rows: the fill,
  2026-10-30).
- light.strengths: `mix.pinned(scale) or` dropped; light.outside_shell: always False; light.one_spot: every lamp its
  own (the sun-swept test, 2026-10-30).
- mix.fill_sweep: return 1.0 always, the greatest factor for the least, or the place left unjudged; light.strengths:
  the fill's sweep not applied (the shadow test, 2026-10-30).
- mix.fill_sweep: from the top of SCALES down, or `exposed` left out; light.exposed_within: never more black (the
  floor test, 2026-10-30).
- light.strengths: the suns' step down not applied; mix.sun_down: the suns' own scale returned always, the brightness
  rules left out, or from the floor of SCALES up; light.exposed_within: `kinds` ignored (the sunlit wall test,
  2026-10-31).
- light.look_at: the look's 8-bit levels scaled for the float colour through the table; mix.displayed: the nearest
  knot (`order=0`); mix.gain: the ratio unsmoothed; passes.passes_faults: no view transform left unsaid (the float look
  test, 2026-10-30).
- mix.tint: return ones (a lamp's light carries no colour into the mix), or the rest of the light left out;
  light.look_at: `colours` ignored; mix.lamp_light: the paint's own hue always, or the black body for every colour;
  mix.white_fit: the distance read in (x, y) for (u, v); mix.balance: the held class swept too, `most` ignored, or kept
  with any gain; mix.capped: `caps` ignored (the float look test, 2026-11-10); light.shipped_colours: the record
  colour's luminance left out, light.colours_written: the colour written unscaled, light.group_colours: `emitters`
  ignored (the layer's rows, 2026-11-10).
- light.strengths: a night light swept as a sun (`path not in night_lights` dropped; the sun-swept test, 2026-11-10);
  mix.adaptation_degree: L_A the lux itself, mix.adaptation: the gains inverted, mix.adapting_white: the light no
  group holds counted, mix.tint: the REST entry ignored, light.shipped_colours: a night light's layer luminance left
  out, light.environment_adapted: the background left as it was (the layer's rows, 2026-11-10).
- light.strengths: the fill not swept again after a blown lamp is turned down (the shadow view test, 2026-11-10).
- light.room_eye: None always, or for a room its concept shows in daylight an eye too (the layer's rows, 2026-11-10).
- light.balanced_cast: `room` ignored (the joint scale past the caps); scene_record.writer: SIGNAL_LIGHTS left out of
  the emitter words (the float look test, 2026-11-10).
- night.air_glow: the rods' share read on the sky's own luminance (`seen_dark(at_zenith)`), not the adapted eye's
  (night.eye_dark); mix.surround_factor: SURROUND always (the sky test's night and the layer's rows,
  2026-11-10: the square's sky too blue).
- light.look_at: the sky's factor left to the smoothing (the float look test, 2026-11-10: the square's sky lit by its
  lamps' gain); light.seen_inside: the concept's sky as painted (the look's sky test, 2026-11-10: the stairwell);
  light.airless_sky: the concept's sky as painted on an airless body (the look's sky test, 2026-11-10: hangar);
  light.on_card: the look as it is (the measures' table: the verdict rows, 2026-11-10: the street's black police car);
  light_passes.surface_of: the glossy colour left out (the measures' table: the surface reflectance row; proved
  2026-11-13).
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
from score.checks import grain
from score.review import overhead, setting
from score.stages import light
from score.stages.assembly import lamps_along
from score.stages.light import haze, layer, measure, mix, needs, night, passes, sky
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
SQUARE = next(site for site in ENVIRONMENT_1["sites"] if site["place"] == "square")
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


NOON, MIDNIGHT = "2024-03-20T12:00:00Z", "2024-03-20T00:00:00Z"
EARTH_FACE = {"body": "earth", "surface": "earth_face", "family": "paint", "recipe": "painted_plaster",
              "token": "ocean-blue", "hex": "#1f4f8f", "colour": [0.0137, 0.0782, 0.2747], "roughness": 0.7,
              "metal": 0.0}


def sky_stage(place, seen, **given):
    """A stage of `place` with the physics' sky written on it from `seen`; the stage and what was written."""
    stage = stage_of(place)
    stage.SetDefaultPrim(stage.GetPrimAtPath(f"/{place}"))
    return stage, sky.write(stage, place, seen, **given)


def seed_with_old_sky(folder):
    """A seed stage whose record drew the old sky: a sun light, a star field and a world laid as structure; and a
    wall of the place."""
    (folder / "layers").mkdir(parents=True)
    base = Usd.Stage.CreateNew(str(folder / "layers/base.usda"))
    base.SetDefaultPrim(UsdGeom.Xform.Define(base, "/house").GetPrim())
    UsdLux.DistantLight.Define(base, "/house/Lights/sun_1")
    stars = UsdGeom.Mesh.Define(base, "/house/Sky/Stars").GetPrim()
    stars.CreateAttribute("score:kind", text_type()).Set("stars")
    world = UsdGeom.Mesh.Define(base, "/house/Structure/earth").GetPrim()
    world.CreateAttribute("score:plain", text_type()).Set("sky")
    UsdGeom.Mesh.Define(base, "/house/Structure/wall")
    base.Save()
    root = Usd.Stage.CreateNew(str(folder / "house.usda"))
    root.GetRootLayer().subLayerPaths.append("./layers/base.usda")
    root.Save()


def test_light_measured_against_design(tmp_path, monkeypatch):
    """The sky a place is lit by is what overhead.py says at its site and time, written by sky.write (a stage) and
    layer.write (the light layer over a seed), and held to it by the gate. The worlds: the house at its spring
    equinox noon and midnight, the Moon base at environment 1's scene time with its Earth's face and the library,
    Mars' campgrounds in its dust, the square by night, and a seed whose record drew the old sky. Then the measures
    (measure.py) and the views' passes (passes.py, inside/light_passes.py) are read on pictures and passes made here:
    a bank of floodlight panes, a body's disc, a sky, haze, a point in a view, a missing picture's surface colours, the
    object index pass, a magenta look and two passes jobs past and within their card. Last the layer (layer.py) on
    seeds made here: where each lamp lands (a row each), then on the first row's layer its strengths, colours and eye,
    a read-only input kept, the concept's fill in the open and inside, and a shown place's pictures kept."""
    seen = {"noon": overhead.seen(HOUSE, HOUSE["sites"][0], NOON),
            "midnight": overhead.seen(HOUSE, HOUSE["sites"][0], MIDNIGHT),
            "base": overhead.seen(ENVIRONMENT_1, BASE, WHEN),
            "square": overhead.seen(ENVIRONMENT_1, SQUARE, WHEN)}  # 22:00 at the square: the Sun 52.7 under
    (tmp_path / "body-face-earth").mkdir()
    (tmp_path / "body-face-earth/face.json").write_text(json.dumps(EARTH_FACE))
    faces = sky.faces_of({"body-face-earth": str(tmp_path / "body-face-earth"), "sky": str(tmp_path / "none.json")})
    assert faces == {"earth": EARTH_FACE}
    library = json.loads((sky.REPO / "data/library/materials.json").read_text())
    noon, _ = sky_stage("house", seen["noon"])
    midnight, dark = sky_stage("house", seen["midnight"])
    base, _ = sky_stage("base", seen["base"], faces=faces, library=library)
    square, _ = sky_stage("square", seen["square"])
    table = json.loads((REPO / "data/physics/night.json").read_text())
    kept = {"setting": ENVIRONMENT_1, "site": SQUARE, "time": WHEN}
    by_night = night.write(square, "square", seen["square"], kept, table, False)

    # the house's sun at equinox noon shines from due south 90 - 52 = 38 degrees up (x east, y up, z south), at
    # midnight as far under; under the horizon it lights nothing and scatters no day dome from under the ground
    rise = math.radians(90.0 - 52.0)
    toward = [0.0, -math.sin(rise), -math.cos(rise)]
    assert seen["noon"]["lights"][0]["altitude"] == pytest.approx(38.0, abs=0.5)
    assert seen["midnight"]["lights"][0]["altitude"] == pytest.approx(-38.0, abs=0.5)
    sun = noon.GetPrimAtPath("/house/Lights/sky_sun")
    assert np.allclose(shines(sun), toward, atol=1e-3) and UsdLux.DistantLight(sun).GetColorTemperatureAttr().Get() \
        == 5800
    assert np.allclose(sky.sun_entries(seen["noon"])[0]["toward"], toward, atol=1e-3)  # the day dome's sun
    assert sky.sun_entries({**seen["noon"], "lights": []}) == [] and sky.sun_entries(seen["midnight"]) == []
    assert dark["lights"] == [] and not midnight.GetPrimAtPath("/house/Lights/sky_sun")
    dome = UsdLux.DomeLight(noon.GetPrimAtPath("/house/Sky/Backdrops/sky"))
    assert dome.GetIntensityAttr().Get() == pytest.approx(10000 / math.pi / 683.0, rel=1e-6)
    assert not noon.GetPrimAtPath("/house/Sky/Bodies").GetChildren()  # a house's sky holds no worlds

    # every sky written passes its gate (the square's with its night written over it), and the physics' own sky is
    # never taken for the old one
    for name, stage in (("noon", noon), ("midnight", midnight), ("base", base), ("square", square)):
        assert sky.faults(seen[name], sky.held(stage, stage.GetDefaultPrim().GetName())) == [], name
    for stage in (noon, midnight, base):
        assert sky.retired(stage, stage.GetDefaultPrim().GetName()) == []

    # on the Moon base the Earth (6371 km at 356500 to 406700 km) is 1.79 to 2.05 degrees across, the Sun (695700 km
    # at 0.983 to 1.017 AU) 31.5 to 32.6 arc minutes; the airless Moon's sun shines at its top-of-air white
    earth, disc = base.GetPrimAtPath("/base/Sky/Bodies/earth"), base.GetPrimAtPath("/base/Sky/Discs/sun")
    assert 1800 * math.sin(math.radians(1.79 / 2)) < half_height(earth) < 1800 * math.sin(math.radians(2.05 / 2))
    assert 1800 * math.sin(math.radians(31.4 / 120)) < half_height(disc) < 1800 * math.sin(math.radians(32.7 / 120))
    assert not UsdLux.DistantLight(base.GetPrimAtPath("/base/Lights/sky_sun")).GetColorAttr().HasAuthoredValue()
    # a body is painted with the face its row made; one whose row has not run is named waiting, never grey
    material = UsdShade.MaterialBindingAPI(earth).ComputeBoundMaterial()[0]
    assert material.GetPath() == "/base/Looks/earth_face" and not earth.HasAttribute("score:surface:missing")
    assert material.GetPrim().GetAttribute("score:from").Get() == "body-face-earth"
    shader = UsdShade.Shader(base.GetPrimAtPath("/base/Looks/earth_face/surface"))
    assert tuple(shader.GetInput("diffuseColor").Get()) == pytest.approx(EARTH_FACE["colour"], abs=1e-6)
    assert earth.GetAttribute("score:face").Get() == "body-face-earth" and light.face_drawn(earth)
    mars = base.GetPrimAtPath("/base/Sky/Bodies/mars")
    assert not light.face_drawn(mars) and mars.GetAttribute("score:surface").Get() == "mars_face"
    assert "body-face-mars" in mars.GetAttribute("score:surface:missing").Get()
    # the Sun's disc is the library's glowing recipe in its 5772 K black body colour (white, a little warm), no
    # placeholder
    material = UsdShade.MaterialBindingAPI(disc).ComputeBoundMaterial()[0]
    assert material.GetPath() == "/base/Looks/sun_disc" and not disc.HasAttribute("score:surface:missing")
    assert material.GetPrim().GetAttribute("score:recipe").Get() == "glowing"
    glow = UsdShade.Shader(base.GetPrimAtPath("/base/Looks/sun_disc/surface")).GetInput("emissiveColor").Get()
    assert glow[0] == pytest.approx(1.0, abs=0.01) and glow[2] < glow[0]
    sys.path.insert(0, str(sky.REPO / "tools/usd"))
    import placeholders
    base.GetRootLayer().Export(str(tmp_path / "base.usda"))
    assert [fault for fault in placeholders.check(tmp_path / "base.usda") if "/Discs/" in fault["prim"]] == []

    # on Mars at campgrounds' scene time (9.8 degrees up) the beam comes through 0.6 of dust: red
    # e^(-(1 - 0.975 * 0.67^2) * 0.6 / sin 9.8) = 0.137, blue (albedo 0.86) 0.114
    campgrounds = next(site for site in ENVIRONMENT_1["sites"] if site["place"] == "campgrounds")
    on_mars = overhead.seen(ENVIRONMENT_1, campgrounds, "2099-10-01T16:00:00Z")
    dust = json.loads((REPO / "data/physics/dust.json").read_text())["bodies"]["mars"]
    dusty, _ = sky_stage("campgrounds", on_mars, dust=dust)
    beam = UsdLux.DistantLight(dusty.GetPrimAtPath("/campgrounds/Lights/sky_sun"))
    assert np.allclose(beam.GetColorAttr().Get(), [0.1372, 0.1278, 0.1143], atol=2e-3)
    assert beam.GetIntensityAttr().Get() == pytest.approx(on_mars["lights"][0]["lux"] / 683.0 / 4.0, rel=1e-4)

    # the gate names a world moved, a light turned, a backdrop missing, a sun shining up through the ground, a world
    # left out and a world the physics has not
    UsdGeom.Xformable(earth).AddTranslateOp().Set((300.0, 0.0, 0.0))
    UsdGeom.Xformable(base.GetPrimAtPath("/base/Lights/sky_sun")).AddRotateXOp().Set(5.0)
    base.GetPrimAtPath("/base/Sky/Backdrops/stars").SetActive(False)
    found = sky.faults(seen["base"], sky.held(base, "base"))
    for start in ("Earth: at azimuth", "the light Sun: shines from", "the backdrop Stars"):
        assert any(fault.startswith(start) for fault in found), (start, found)
    assert not any("Mars" in fault for fault in found), found
    sky.write_light(midnight, "house", seen["midnight"]["lights"][0])
    assert "the light sun: in the sky, but not overhead" in sky.faults(seen["midnight"], sky.held(midnight, "house"))
    lacking, _ = sky_stage("base", {**seen["base"], "bodies": [body for body in seen["base"]["bodies"]
                                                             if body["body"] != "mars"]})
    sky.write_body(lacking, "base", {"body": "phobos", "azimuth": 10.0, "altitude": 20.0, "across": 0.1, "lit": 1.0})
    found = sky.faults(seen["base"], sky.held(lacking, "base"))
    assert any(fault.startswith("Mars: overhead") for fault in found), found
    assert "the body phobos: in the sky, but not overhead" in found, found

    # the night's light (night.py), worked out by hand: the full Moon outside the air at its mean distance gives
    # 128 000 x 0.12 x (1737.4 / 384 400)^2 = 0.314 lux; a 15.0 mag/arcsec^2 sky 10.8e4 x 10^-6 = 0.108 cd/m^2; an
    # eye at a lit square (10 lux) sees the night pi x 683 / 10 = 214.6 times its physical light, inside (100 lux)
    # 21.5. The rods' share is the adapted eye's, never the sky's own (2026-11-10: the square's sky seen with 64% rods
    # read 2.4 to 2.8 blue to red against its concept's 2.06): at the square's 10 lux, 10 / pi / 5 = 0.64 cd/m^2, a
    # smooth step at (0.6 + 0.20) / 2.6 = 0.31 of its way, 0.224; in a 100 lux room, 6.4 cd/m^2, none
    moon = {"body": "moon", "across": math.degrees(2 * math.asin(1737.4 / 384400.0)), "lit": 1.0}
    for said, measured, expected in (
            ("the full Moon's lux", night.body_lux(kept, {"lux": 128000.0}, moon, table["reflecting"]["moon"]),
             pytest.approx(0.314, abs=0.001)),
            ("a 15 mag/arcsec^2 sky", night.ZERO_MAG * 10 ** (-0.4 * 15.0), pytest.approx(0.108)),
            ("the eye's scale outside", night.scale_of(table, False), pytest.approx(214.6, abs=0.1)),
            ("the eye's scale inside", night.scale_of(table, True), pytest.approx(21.46, abs=0.01)),
            ("rods at 0.001 cd/m^2", night.seen_dark(0.001), 1.0),
            ("rods at 10 cd/m^2", night.seen_dark(10.0), 0.0),
            ("the adapted eye's rods outside", night.eye_dark(table, False), pytest.approx(0.224, abs=0.001)),
            ("the adapted eye's rods inside", night.eye_dark(table, True), 0.0),
            ("the square's skyglow", night.skyglow_of(table, SQUARE)["name"], "Hong Kong, urban"),
            ("135 km up the coast: not the city's sky", night.skyglow_of(table, {**SQUARE, "latitude": 23.5}), None),
            ("the square at 22:00", night.is_night(seen["square"]), True),
            ("the square at 04:00", night.is_night(overhead.seen(ENVIRONMENT_1, SQUARE, "2099-10-01T04:00:00Z")),
             False)):
        assert measured == expected, said
    city = night.colour(night.black_body(4000.0))
    assert city[2] < city[0] < night.colour(night.black_body(4000.0), 1.0)[2]  # the rods see the warm light blue
    # the square by night: its Moon 38 up at its 96% phase through 1.6 airmasses, its sky's glow and air blue
    lux = square.GetPrimAtPath("/square/Lights/night_moon").GetAttribute("score:sky:lux").Get() / by_night["scale"]
    assert 0.05 < lux < 0.314
    ambient = UsdLux.DomeLight(square.GetPrimAtPath("/square/Environment")).GetColorAttr().Get()
    assert ambient[2] > ambient[0] > 0.0 and by_night["zenith_cd"]["skyglow"] == pytest.approx(0.108)
    assert night.write(stage_of("square"), "square", overhead.seen(ENVIRONMENT_1, SQUARE, "2099-10-01T04:00:00Z"),
                       kept, table, False) is None  # by day: nothing
    assert night.write(stage_of("stairwell"), "stairwell", seen["square"], kept, table, True)["outside_scale"] == \
        pytest.approx(214.6, abs=0.1)
    for name, (high_x, high_z), under in (("roof_1", (10.0, 10.0), True), ("roof_2", (2.0, 3.0), False)):
        roofs = stage_of("street")  # a room's ceiling over its 10 x 10 m floor; a 2 x 3 m awning over a street
        roof = UsdGeom.Mesh.Define(roofs, f"/street/Structure/{name}")
        roof.CreatePointsAttr([(0.0, 3.5, 0.0), (high_x, 3.5, 0.0), (high_x, 3.7, high_z), (0.0, 3.7, high_z)])
        roof.GetPrim().CreateAttribute("score:plain", text_type()).Set("shell")
        assert night.roofed(roofs, "street", [[0.0, 0.0], [10.0, 10.0]]) is under, name
    root = Usd.Stage.CreateNew(str(tmp_path / "square.usda"))  # written into a light layer file over the stage
    root.SetDefaultPrim(UsdGeom.Xform.Define(root, "/square").GetPrim())
    root.Save()
    Sdf.Layer.CreateNew(str(tmp_path / "light.usda")).Save()
    written = night.write_layer(tmp_path / "light.usda", tmp_path / "square.usda", "square", kept, table, None)
    assert written["scale"] == pytest.approx(214.6, abs=0.1)
    assert Usd.Stage.Open(str(tmp_path / "light.usda")).GetPrimAtPath("/square/Lights/night_moon")
    assert written["dark"] == pytest.approx(0.224, abs=0.001) and written["outside_scale"] == written["scale"]

    # the light layer writes the physics' sky over a seed's old one, the old turned off and the place's wall left
    # on, and its gate holds it to overhead at the kept sky's time: passed at noon, failed 3 hours on, unknown with
    # no kept sky
    seed, out = tmp_path / "seed", tmp_path / "out"
    seed_with_old_sky(seed)
    kept_sky = {"place": "house", "top": "house", "time": NOON, "setting": HOUSE,
                "site": {"on": "meadow", "x": 0.0, "y": 0.0, "height_m": 0.0}}
    layered = layer.write("house", {"lights": []}, seed, out, kept_sky)
    layer.lamps_file(layered, out)
    assert sorted(layered["sky"]["retired"]) == ["/house/Lights/sun_1", "/house/Sky/Stars", "/house/Structure/earth"]
    composed = Usd.Stage.Open(str(seed / "house.usda"))
    composed.GetRootLayer().subLayerPaths.insert(0, str(out / layer.LAYER))
    assert not composed.GetPrimAtPath("/house/Lights/sun_1").IsActive()
    assert composed.GetPrimAtPath("/house/Lights/sky_sun").IsActive()
    assert composed.GetPrimAtPath("/house/Structure/wall").IsActive()
    for time, answer, said in ((NOON, checks.PASS, ""), (None, checks.UNKNOWN, ""),
                               ("2024-03-20T15:00:00Z", checks.FAIL, "the light Sun: shines from")):
        inputs = {}
        if time:
            (tmp_path / "sky.json").write_text(json.dumps({**kept_sky, "time": time}))
            inputs["sky"] = str(tmp_path / "sky.json")
        verdict = light.judge_sky_bodies(out, inputs, {})
        assert verdict.answer == answer and said in verdict.reason, (time, verdict)

    # the measures and the views' passes, read on pictures and passes made here, each against the answer worked out
    # by hand: one row a measure, its expected value exact, approximate or a strict range (Between)
    grid, glow = measure.head(grid_bank(), 240, 240, 40), measure.head(glowing_bank(), 240, 240, 40)
    rows, columns = np.mgrid[0:SIZE, 0:SIZE]
    lit = np.zeros((SIZE, SIZE, 3))  # a body's disc lit on its right half over a black sky
    round_disc = np.hypot(columns - 100, rows - 100) < 40
    lit[round_disc & (columns >= 100)] = [150, 150, 160]
    lit[round_disc & (columns < 100)] = [12, 12, 14]
    usable = np.ones((SIZE, SIZE), dtype=bool)
    right = measure.body(lit, 100, 100, 40, (1.0, 0.0), usable)
    left = measure.body(lit, 100, 100, 40, (-1.0, 0.0), usable)
    lost = measure.body(np.zeros((SIZE, SIZE, 3)), 100, 100, 40, (1.0, 0.0), usable)
    flat_sky = np.zeros((SIZE, SIZE, 3))  # a flat dusky sky over lit ground; the found sky blue to red 0.6 rising
    flat_sky[:] = [70, 42, 16]
    flat_sky[120:] = [120, 60, 30]
    found_sky = flat_sky.copy()
    found_sky[:90] = np.linspace(170, 195, 90)[:, None, None] * np.array([1.0, 0.78, 0.6])
    concept_rgb = [188.1, 145.2, 112.1]
    flat = measure.sky_of(flat_sky, measure.sky_pixels(flat_sky))
    found = measure.sky_of(found_sky, measure.sky_pixels(found_sky))
    black = np.zeros((SIZE, SIZE, 3))
    near_black = np.full((SIZE, SIZE, 3), [1.33, 1.4, 1.3])
    before = np.full((100, 100, 3), 40.0)
    glowing = before.copy()
    glowing[:50] += 100.0  # a lamp's glow up in the sky leaves the place below as it was
    hazed = glowing.copy()
    hazed[60:] += 30.0  # haze laid over the place's lower part
    ahead = {"eye": [0, 0, 0], "aim": [0, 0, -10], "up": [0, 1, 0], "fov": 90}
    # the surface colours a missing picture gave in Blender 5.0.1 on a tiny stage (2026-10-30): a plain finish's
    # diffuse colour, a metal's glossy colour, a half metal's both; a grey lit magenta keeps its grey surface colour.
    # Each pixel's surface reflectance is the diffuse and glossy colours' luminance together (light.on_card): the
    # grey 0.765 + 0.044 = 0.809, the metal's magenta 0.2126 + 0.0722 = 0.285
    inside = inside_functions("magenta_colour", "missing_share", "surface_of", "sky_mask")
    inside["LUMINANCE"] = (0.2126, 0.7152, 0.0722)  # a tuple, which inside_functions leaves out
    plain, metal, half, grey = (0.956, 0.0, 0.956), (1.0, 0.0, 1.0), (0.48, 0.0, 0.48), (0.765, 0.765, 0.765)
    diffuse = np.array([[plain, (0.0, 0.0, 0.0), half, grey]])
    glossy = np.array([[(0.044,) * 3, metal, (0.52, 0.02, 0.52), (0.044,) * 3]])
    channels = {f"ViewLayer.{kind}.{axis}": values[..., index] for kind, values in
                (("Diffuse Color", diffuse), ("Glossy Color", glossy)) for index, axis in enumerate("RGB")}
    surface = inside["surface_of"](channels)
    # greenhouse's grow light (#ff55ff) lit 62.7% of a look in the old hue band (2026-10-30): the look is not read;
    # the share Blender's own missing picture covers is, and passes rendered before the share are unknown
    (tmp_path / "passes/tiny-0").mkdir(parents=True)
    Image.fromarray(np.full((10, 10, 3), (255, 85, 255), np.uint8)).save(tmp_path / "passes/tiny-0/shot0-look.png")
    magenta = {}
    for said, missing in (("none", {"missing": np.float32(0.0)}), ("1%", {"missing": np.float32(0.01)}),
                          ("unsaid", {})):
        np.savez(tmp_path / "passes/tiny-0/shot0-passes.npz", combined=np.ones((5, 5)), **missing)
        magenta[said] = passes.judge_magenta(tmp_path, {}, {})
    script = (pathlib.Path(passes.__file__).parent / "inside/light_passes.py").read_text()
    # base's light passes (2026-10-29, #36) needed about 29 GB, past this PC's 16 GB card: a job blender_cloud.py
    # predicts past the card it renders on gets the processor in its views file, one that fits keeps the card, and
    # light_passes.py switches Cycles to the processor for it alone, after usd_views.renderer set its samples and
    # denoising
    specs = []
    for number in range(2):
        spec = tmp_path / f"{number}.views.json"
        spec.write_text(json.dumps({"size": [960, 540], "views": [], "lamps": []}))
        specs.append({"script": passes.SCRIPT, "args": ["root", str(spec), "out"], "inputs": [str(spec)]})
    said = json.dumps({"card": 16, "needs": [29.3e9, 2.3e9]})
    monkeypatch.setattr(passes.subprocess, "run", lambda command, **_: subprocess.CompletedProcess(command, 0, said))
    passes.with_devices(specs, tmp_path)
    switch = 'if views.get("device") == "CPU" and scene.render.engine == "CYCLES":'
    # the colour (2026-11-04, the light audit: the lab lit green by its screens, quarters' warm room cool): a cast is
    # read on the mid-tones with brightness taken out, so a grey room twice as bright reads the same, a green one not.
    # A cutaway concept's flat backdrop is no surface of the place (2026-11-10: quarters' warm room on a grey 73% of
    # its picture read neutral): a warm room on grey reads warm, the grey left out; a room filling its picture, its
    # border painted in many colours, keeps every pixel, a warm patch inside the room that touches no border too
    grey_room, green_room = np.full((40, 40, 3), 60.0), np.full((40, 40, 3), [60.0, 75.0, 50.0])
    cutaway = np.full((60, 80, 3), 98.0)
    cutaway[15:45, 20:60] = [150.0, 110.0, 80.0]
    cutaway[25:35, 30:50] = 98.0  # the room's own grey floor, joined to no border
    backdrop_left = light.not_place(cutaway, outdoor=False)
    Image.fromarray(cutaway.astype(np.uint8)).save(tmp_path / "cutaway.png")
    Image.fromarray(np.full((20, 20, 3), 128, np.uint8)).save(tmp_path / "hall.png")
    monkeypatch.setattr(light, "concept_pictures", lambda place: [tmp_path / f"{place}.png"])
    warm = light.concept_cast("cutaway", outdoor=False)
    painted = np.random.default_rng(3).uniform(40.0, 200.0, (60, 80, 3))
    # every view's light all zero gave the tone curve no knots and the sweep crashed in np.interp (2026-10-29,
    # light@base), where the brightness gate should fail it by name
    unlit = {"combined": np.zeros((20, 30)), "lamp_0": np.zeros((20, 30))}
    unlit_views = {"v": (unlit, mix.tone_curve(unlit["combined"], np.full((20, 30), 0.0003)))}
    # every object of the record waited on its model and no ground was laid, so the stage drew nothing and rendered
    # black under its sun (2026-10-29, light-passes@base); the light layer's `drawn` gate counts what it lights
    tiny = Usd.Stage.CreateNew(str(tmp_path / "tiny.usda"))
    UsdGeom.Xform.Define(tiny, "/tiny")
    UsdGeom.Sphere.Define(tiny, "/tiny/Sky/Bodies/earth")
    tiny.Save()
    drawn = [light.drawn_count(tmp_path / "tiny.usda", "tiny")]
    UsdGeom.Cube.Define(tiny, "/tiny/Objects/hub")
    tiny.Save()
    drawn.append(light.drawn_count(tmp_path / "tiny.usda", "tiny"))
    # the rows read the design only (owner's rule of 2026-10-21, a wording check of the declared files): no row
    # declares a record in data/scene, read here on the real design before the one made below stands in for it
    hand_kept = [(place, path) for place in ("launch", "square", "hub")
                 for files in (light.layer_files, light.light_files, passes.passes_files)
                 for path in files(place).values() if path.startswith("{data}/scene")]
    applies = (light.applies("far_city"), light.applies(None))
    design = design_world(tmp_path / "design")
    with monkeypatch.context() as patched:
        patched.setattr(passes, "KEPT", design)
        patched.setattr(needs, "KEPT_PLANS", design / "plans")
        # what a place needs lit: an outdoor place the design stands on no ground lacks its seat and its sky until
        # its kept sky has a site and a scene time; a room under a roof needs neither, whatever an old hand-kept
        # record beside it says; a place with no plan adds nothing
        old = tmp_path / "needs"
        (old / "scene").mkdir(parents=True)
        (old / "skies").mkdir()
        (old / "scene/room.json").write_text(json.dumps({"environment": {"inside": False}, "views": []}))
        (old / "scene/oldonly.json").write_text(json.dumps({"environment": {"inside": False}, "views": []}))
        needed = {"yard": needs_of("yard", old, design)}
        (old / "skies/yard.json").write_text(json.dumps({"place": "yard", "top": "yard",
                                                         "time": "2024-06-01T12:00:00Z",
                                                         "site": {"on": "rock", "x": 0, "y": 0, "height_m": 0},
                                                         "setting": setting.checked(YARD)}))
        needed.update({place: needs_of(place, old, design) for place in ("yard kept", "nowhere")})
        needed.update({place: needs.gaps(place, old, old / "skies") for place in ("room", "oldonly")})  # the light's
        # the record is the scene-record output's (a shown place's read beside, with its seed and its design kit)
        record_inputs = {}
        for node, place in (("scene-record", "launch"), ("scene-record@square", "square")):
            (tmp_path / "rows" / node / "record").mkdir(parents=True)
            (tmp_path / "rows" / node / "record" / f"{place}.json").write_text(json.dumps({"place": place,
                                                                                         "lights": []}))
            record_inputs[node] = str(tmp_path / "rows" / node)
            kit = tmp_path / "rows" / f"{place}-kit.json"  # the design's kit, as earth-seed writes it
            kit.write_text(json.dumps({"room": place, "pieces": []}))
            record_inputs["kit" if place == "launch" else f"kit {place}"] = str(kit)
        record_inputs["neighbour square"] = str(tmp_path / "rows")  # its seed, as passes_files declares it
        heads = light.lamp_heads("launch", record_inputs)
        # the floodlights: the glowing rows the plan aims that the kit lays, each kind `<room>_<row>`
        laid = {place: {"room": place, "pieces": [{"kind": f"{place}_{row}", "part": "glow"}
                                                  for row in ("mast_lamp", "desk")]} for place in ("yard", "hall",
                                                                                                   "shed")}
        shafted = {place: haze.shafted_kinds(place, kit) for place, kit in laid.items()}
        # the places shown: the accepted record's with a kept plan, none before it stands accepted
        flat_record = {"place": "flat", "places": [{"stage": "wreck"}, {"stage": "far_city"}, {"stage": "flat"}]}
        shown = []
        for held in ({"scene-record@flat": flat_record}, {}):
            patched.setattr(Store, "default", classmethod(lambda cls, held=held: Accepted(held)))
            shown.append(passes.neighbours("flat"))
        floodlit = (haze.shafted_rows("yard"), shafted, haze.shafted_kinds("yard", {"room": "yard", "pieces": []}))
    # fault (Buy of 2026-10-24): glowing put score/stages on sys.path, so the assembly's `import sound` took the
    # sound stage package for tools/usd/sound.py and failed on audio_prim
    stages = str(pathlib.Path(haze.__file__).resolve().parents[1])
    lamp, sun = {"path": "/p/Lights/lamp_1"}, {"path": "/p/Lights/sky_sun", "sun": True}
    fill = {"path": "/p/Lights/concept_fill", "sun": True, "fill": True}
    for said, measured, expected in (
            ("a bank of lit panes: its halo", grid["halo"], Between(high=0.02)),
            ("a bank of lit panes: its fill", grid["fill"], Between(high=0.1)),
            ("a bank glowing into the air: its halo", glow["halo"], Between(low=0.08)),
            ("a bank glowing into the air: its fill", glow["fill"], Between(low=0.28)),
            ("a disc lit on its right: its share shown", right["shown"], Between(low=0.45)),
            ("a disc lit on its right: lighter toward its sun", right["sunward"] - right["away"], Between(low=50)),
            ("a disc lost in the sky: its share shown", lost["shown"], 0.0),
            ("a disc on no usable pixel", measure.body(lit, 100, 100, 40, (1.0, 0.0), ~usable), None),
            ("a disc lit from its sun", light.body_faults([body_entry(right)]), []),
            ("a disc lit from the other side", any("not lit from its sun" in fault for fault in
                                                   light.body_faults([body_entry(left)])), True),
            ("its sun along the view: not judged", light.body_faults([body_entry(left, sun_seen=False)]), []),
            ("nearly full: no dark side to judge", light.body_faults([body_entry(left, lit_share=0.98)]), []),
            ("a disc lost in every view", any("shown in none" in fault for fault in
                                              light.body_faults([body_entry(lost)])), True),
            ("a disc shown in one of the views framing it",
             light.body_faults([body_entry(lost), body_entry(right)]), []),
            ("the flat sky's gap to its concept", measure.colour_gap(flat["mean_rgb"], concept_rgb), Between(low=80)),
            ("the found sky's gap to its concept", measure.colour_gap(found["mean_rgb"], concept_rgb),
             Between(high=20)),
            ("the found sky's rise to the horizon", found["rise_to_horizon"], Between(low=0)),
            ("the found sky's blue to red", found["blue_to_red"], Between(0.59, 0.61)),
            ("a black sky's blue to red: no hue, never red", measure.sky_of(black, measure.sky_pixels(black))[
                "blue_to_red"], 1.0),
            ("a near black sky's blue to red", measure.sky_of(near_black, measure.sky_pixels(near_black))[
                "blue_to_red"], Between(0.95, 1.05)),
            ("glow in the sky: no veil", measure.veil(before, glowing), 0.0),
            ("haze over the lower part: its veil", measure.veil(before, hazed),
             Between(30.0 / 255.0 - 1e-3, 30.0 / 255.0 + 1e-3)),
            ("a point straight ahead: x, y, depth, focal",
             tuple(round(value, 6) for value in measure.where(ahead, (200, 100), [0, 0, -5])), (100, 50, 5.0, 100.0)),
            ("a point behind the eye", measure.where(ahead, (200, 100), [0, 0, 5])[0], None),
            ("a missing picture's share on plain, metal and half metal finishes, never a grey lit magenta",
             inside["missing_share"](channels), 0.75),
            ("the surface reflectance's kind", surface.dtype, np.float16),
            ("the metal's and the grey's surface reflectance", surface[0, [1, 3]].tolist(),
             pytest.approx([0.285, 0.809], abs=0.002)),
            ("the sky mask: where the object index pass met no object",
             inside["sky_mask"]({"ViewLayer.Object Index.X": np.array([[0.0, 1.0], [1.0, 0.0]])}).tolist(),
             [[True, False], [False, True]]),
            ("a magenta lamp's look with no missing picture", magenta["none"].answer, checks.PASS),
            ("1% of Blender's missing picture", magenta["1%"].answer, checks.FAIL),
            ("1% of Blender's missing picture: its share", magenta["1%"].measures["magenta share"], 0.01),
            ("passes rendered before the share", magenta["unsaid"].answer, checks.UNKNOWN),
            ("the glossy colour pass rendered", "use_pass_diffuse_color = scene.view_layers[0].use_pass_glossy_color"
             " = True" in script, True),
            ("29.3 GB on a 16 GB card", passes.device_for(29.3e9, 16), "CPU"),
            ("2.3 GB on a 16 GB card", passes.device_for(2.3e9, 16), "GPU"),
            ("20 GB on a rented L4's 24 GB", passes.device_for(20e9, 24), "GPU"),
            ("the jobs' views files", [json.loads(pathlib.Path(job["args"][1]).read_text())["device"]
                                       for job in specs], ["CPU", "GPU"]),
            ("the processor switched after the samples and denoising were set", switch in script and
             script.index("usd_views.renderer(scene") < script.index(switch), True),
            ("a view half black: its black and blown", light.extremes(np.concatenate([np.zeros((10, 20)),
                                                                                      np.full((10, 20), 0.5)])),
             {"black": 0.5, "blown": 0.0}),
            ("a grey room's cast, and twice as bright",
             (measure.surface_cast(grey_room), measure.surface_cast(grey_room * 2)), ([128.0] * 3, [128.0] * 3)),
            ("a black picture's cast: says nothing of a colour", measure.surface_cast(np.zeros((40, 40, 3))), None),
            ("a cutaway's backdrop: its corner left out, its room and the room's grey floor kept",
             (bool(backdrop_left[0, 0]), bool(backdrop_left[30, 40]), bool(backdrop_left[20, 25])),
             (True, False, False)),
            ("a warm room on a grey backdrop: red over blue", warm[0] - warm[2], Between(low=20)),
            ("a picture painted to its border: no backdrop",
             (measure.backdrop(painted), light.not_place(painted, outdoor=False)), (None, None)),
            ("a black view's brightness", mix.place_brightness(unlit_views, {}), pytest.approx(0.0003)),
            ("a black view swept toward 0.3: still not within",
             mix.within(unlit_views, {"lamp_0": mix.sweep(unlit_views, ["lamp_0"], 0.3)}, 0.3), False),
            ("prims drawn by a stage of its sky alone, then with a hub", drawn, [0, 1]),
            ("no light at all, outside and inside: named",
             (bool(light.unlit_why([], inside=False)), bool(light.unlit_why([], inside=True))), (True, True)),
            ("an inside place lit by a sun alone: named", bool(light.unlit_why([sun], inside=True)), True),
            ("an outdoor place lit by its sun", light.unlit_why([sun], inside=False), None),
            ("an inside place lit by its lamp", light.unlit_why([lamp], inside=True), None),
            ("an outdoor place lit by its lamp and sun", light.unlit_why([lamp, sun], inside=False), None),
            ("an inside place lit by its sun and the concept's fill", light.unlit_why([sun, fill], inside=True), None),
            ("a place whose lights were not read", "not read" in light.unlit_why([], False, read=False), True),
            ("an outdoor yard on no ground and with no kept sky", needed["yard"], ["ground:seat:yard",
                                                                                   "sky:site:yard"]),
            ("the yard with its kept sky", needed["yard kept"], []),
            ("a room under its roof, an old record saying outside: no light need", needed["room"], []),
            ("an old hand-kept record with no plan: no light need", needed["oldonly"], []),
            ("a place with no plan", needed["nowhere"], []),
            ("a place with no kept plan, and none: no row", applies, (False, False)),
            ("a row declaring a record in data/scene", hand_kept, []),
            ("the record rows' place, its shown places and a shown place's record",
             (passes.place_of(record_inputs), passes.shown_in(record_inputs),
              passes.record_of("square", record_inputs)["place"]), ("launch", ["square"], "square")),
            ("a kit laying no shafted lamp: no floodlight head", heads, []),
            ("the shafted rows: the glowing row its plan aims", floodlit[0], {"mast_lamp"}),
            ("the shafted kinds a yard, a hall aiming none and a shed aiming no glowing row lay", floodlit[1],
             {"yard": {"yard_mast_lamp"}, "hall": set(), "shed": set()}),
            ("a kit laying none of the yard's shafted rows", floodlit[2], set()),
            ("score/stages put on sys.path", stages in [str(pathlib.Path(entry).resolve()) for entry in sys.path
                                                        if entry], False),
            ("the places an accepted record shows, then none accepted", shown, [["wreck"], []])):
        assert expected == measured, (said, measured)
    with pytest.raises(ValueError, match="'spot-1' looks along its own up"):
        measure.where({"name": "spot-1", "eye": [0, 4, 0], "aim": [0, 1, 0], "up": [0, 1, 0], "fov": 90},
                      (200, 100), [0, 0, 0])

    # the verdicts on the measures: one row a judged measures file and its answer. The exposure's are read on hall's
    # one view, its look and passes made here. Garage's 9.4% black was the Moon's black sky through its doors, its
    # concept a cutaway with no sky (2026-10-30): the sky is left to the sky check. A finish darker than the grey card
    # is judged on its light, read on the card (2026-11-10: the street's police car's black paint, 5.8 to 10.9% of its
    # close views under 4 levels): a view half black paint (4% reflectance, Munsell N2.5's) at 3 levels beside a grey
    # wall, under a tone curve known by hand (look = linear ^ (1 / 2.2)), reads 3 x (0.18 / 0.04) ^ (1 / 2.2) = 5.9
    # levels on the card; the same paint in no light (0 levels) still black, and a grey finish (0.5) at 3 levels black
    # on its own
    hall = tmp_path / "exposure"
    (hall / "looks/hall").mkdir(parents=True)
    (hall / "passes/hall-0").mkdir(parents=True)
    top, half_view, open_floor = (np.zeros((20, 20), bool) for _ in range(3))
    top[:8] = True
    half_view[:, :10] = True
    looked = {name: exposure_of(hall, look, sky_mask, None) for name, look, sky_mask in (
        ("dark", np.full((20, 20), 2), open_floor), ("blown", np.full((20, 20), 255), open_floor),
        ("moon", np.where(top, 0, 128), top))}
    low, high = -16.0, 4.0
    axis = 2.0 ** np.linspace(low, high, 65)
    knots = np.stack(np.meshgrid(axis, axis, axis, indexing="ij"), axis=-1)
    np.savez(hall / "passes/hall-0/view-transform.npz", table=np.minimum(knots, 1.0) ** (1 / 2.2), low=low, high=high)
    looked.update({name: exposure_of(hall, np.where(half_view, level, 128), open_floor,
                                     None if finish is None else np.where(half_view, finish, 0.5))
                   for name, level, finish in (("paint lit", 3, 0.04), ("paint unlit", 0, 0.04), ("grey", 3, 0.5),
                                               ("no surface pass", 3, None))})
    judged = tmp_path / "judged"
    judged.mkdir()
    for said, judge, measures, answer in (
            ("as black as its concept", light.judge_exposure,
             {"exposure": {"concept": {"black": 0.45, "blown": 0.0}, "views": {"wide": {"black": 0.5, "blown": 0.01}}}},
             checks.PASS),
            ("far blacker than its concept", light.judge_exposure,
             {"exposure": {"concept": {"black": 0.01, "blown": 0.0}, "views": {"wide": {"black": 0.2, "blown": 0.0}}}},
             checks.FAIL),
            ("more blown than its concept", light.judge_exposure,
             {"exposure": {"concept": {"black": 0.0, "blown": 0.0}, "views": {"wide": {"black": 0.0, "blown": 0.05}}}},
             checks.FAIL),
            ("no concept", light.judge_exposure,
             {"exposure": {"concept": None, "views": {"wide": {"black": 0.0, "blown": 0.0}}}}, checks.UNKNOWN),
            ("a dark look", light.judge_exposure, {"exposure": looked["dark"]}, checks.FAIL),
            ("a blown look", light.judge_exposure, {"exposure": looked["blown"]}, checks.FAIL),
            ("the Moon's black sky over a grey place", light.judge_exposure, {"exposure": looked["moon"]}, checks.PASS),
            ("black paint lit, read on the card", light.judge_exposure, {"exposure": looked["paint lit"]}, checks.PASS),
            ("black paint unlit", light.judge_exposure, {"exposure": looked["paint unlit"]}, checks.FAIL),
            ("a grey finish at 3 levels", light.judge_exposure, {"exposure": looked["grey"]}, checks.FAIL),
            ("3 levels with no surface pass", light.judge_exposure, {"exposure": looked["no surface pass"]},
             checks.FAIL),
            ("a grey room twice as bright as its grey concept", light.judge_colour,
             {"colour": {"concept": [128.0] * 3, "views": {"v": measure.surface_cast(grey_room * 2)}}}, checks.PASS),
            ("a green room against a grey concept", light.judge_colour,
             {"colour": {"concept": [128.0] * 3, "views": {"v": measure.surface_cast(green_room)}}}, checks.FAIL),
            ("a view with no cast", light.judge_colour, {"colour": {"concept": [128.0] * 3, "views": {"v": None}}},
             checks.UNKNOWN)):
        (judged / "measures.json").write_text(json.dumps(measures))
        assert judge(judged, {}, {}).answer == answer, (said, measures)

    # the layer (layer.py) on seeds made here, one lamp /tiny/Lights/light_1 each: where each lamp lands is a row,
    # its seed's lamp spot, the meshes round it, how far the assembly carried it with its floor light, the record,
    # and what the layer did with it
    bulb = {"type": "omni", "at": [1.0, 2.0, 0.0], "energy": 1.0, "colour": "#ffcc00", "row": "bulb"}
    record = {"lights": [bulb, {"type": "spot", "at": [20.0, 2.0, 0.0], "aim": [20.0, 0.0, 0.0], "angle": 30.0,
                                "energy": 1.0, "colour": "#ffffff", "row": "panel"}]}
    post = ("/tiny/Objects/street_lamp", (((-0.05, 0.0, -0.05), (0.05, 3.3, 0.05)),
                                          ((-0.25, 3.3, -0.25), (0.25, 4.0, 0.25))))
    pavement = ("/tiny/Objects/pavement", (((2.0, 0.0, -1.0), (8.0, 0.1, 1.0)),))
    laid = {}
    for said, spot, meshes, carried, given, done, rule, enclosing, landed in (
            # a record lamp 1 m from the seed's moves it, one far from any is added
            ("a record lamp near the seed lamp", (0.0, 2.0, 0.0), (), None, record, ["moved 1.00 m", "added"], None,
             None, lambda at: at == [1.0, 2.0, 0.0]),
            # a lamp the assembly carried 8 cm with its floor light out of a wall (assembly/lamps_along) keeps its
            # carried spot: the record's lamp at its laid spot is that one, never moved back into the wall
            # (light@walkway, 2026-11-12)
            ("a lamp carried out of its wall", (0.0, 2.0, 0.0), (), 0.08, {"lights": [dict(bulb, at=[0.0, 2.0, 0.0])]},
             ["kept"], None, None, lambda at: at == [0.08, 2.0, 0.0]),
            # walkway, round 33 (2026-10-30): its ceiling ducts reached 6.1 m over a 2.6 m ceiling, the stage bound's
            # middle stood over the ceiling, and its enclosed ceiling lamps moved up into it and read unlit
            ("a ceiling lamp in its fixture under a duct", (0.0, 2.4, 0.0),
             (("/tiny/Objects/fixture", (((-0.1, 2.3, -0.1), (0.1, 2.5, 0.1)),)),
              ("/tiny/Objects/duct", (((-6.0, 2.4, 3.0), (6.0, 9.0, 4.0)),))), None,
             {"lights": [], "inside": True, "floor": [[-1.0, -1.0], [1.0, 1.0]], "ceiling": 2.6}, [],
             "moved out of its fixture", None, lambda at: at[1] < 2.3),
            # square and street, round 34 (2026-10-31): the bake laid each street lamp as one 4 m mesh, post and head,
            # its head closed round the lamp at the library's mount height; no part was small enough to be its
            # fixture, the lamp was kept, every way out stopped, and it lit nothing
            ("a lamp closed in a post's head", (0.0, 3.8, 0.0), (post, pavement), None, {"lights": []}, [],
             "moved out of its model's head", post[0], lambda at: at[0] > 0.25 and 3.3 <= at[1] <= 4.0),
            ("a lamp under a post's head", (0.2, 3.1, 0.2), (post, pavement), None, {"lights": []}, [], None, None,
             lambda at: at == [0.2, 3.1, 0.2])):
        seed = placed_seed(tmp_path / "placed" / said, spot, meshes, carried)
        found = layer.write("tiny", given, seed, tmp_path / "laid" / said)
        laid[said] = found
        lamp = next(lamp for lamp in found["lamps"] if lamp["path"] == "/tiny/Lights/light_1")
        assert [entry["done"] for entry in found["placed"]] == done, (said, found["placed"])
        assert found.get("fixtures", {}).get("/tiny/Lights/light_1", {}).get("rule") == rule, (said, found)
        assert landed(lamp["spot"]) and not lamp["shaped"], (said, lamp)
        if enclosing:  # out of what closed it in
            opened = Usd.Stage.Open(str(seed / "layers/base.usda"))
            assert layer.blocked_share(np.array(lamp["spot"]), [layer.world_mesh(opened, enclosing)]) < \
                layer.ENCLOSED, said

    # the strengths are written into a copy and the read-only input stays (2026-10-12, light@camp: they were saved
    # over the input layer, a read-only checkout); the record's views, at the check size, travel with the layer
    found, out = laid["a record lamp near the seed lamp"], tmp_path / "laid/a record lamp near the seed lamp"
    (out / passes.VIEWS).write_text(json.dumps(passes.record_views(
        {"views": [{"name": "door", "eye": [0, 1.6, 2], "aim": [0, 1.2, 0], "fov": 70}]})))
    before = (out / layer.LAYER).read_bytes()
    for path in out.rglob("*"):
        os.chmod(path, stat.S_IREAD | (stat.S_IEXEC if path.is_dir() else 0))
    try:
        light.layer_copied(out, tmp_path / "copied")
        layer.strengths(tmp_path / "copied" / layer.LAYER, "tiny", {"/tiny/Lights/light_1": (10.0, 2.0)})
        assert (out / layer.LAYER).read_bytes() == before
        size, copied = passes.views_of(tmp_path / "copied")
        assert size == passes.CHECK_SIZE and copied[0]["up"] == [0.0, 1.0, 0.0] and copied[0]["frame"] == 0
    finally:
        for path in out.rglob("*"):
            os.chmod(path, stat.S_IRWXU)
    layer.strengths(out / layer.LAYER, "tiny", {"/tiny/Lights/light_1": (10.0, 0.5)})
    held = Usd.Stage.Open(str(out / layer.LAYER))
    assert held.GetPrimAtPath("/tiny/Lights/light_1").GetAttribute("inputs:intensity").Get() == 5.0
    # the bulb painted #ffcc00 ships its black body's light at the luminance it was rendered with, its brightest
    # channel at most 1 and its intensity raised for the rest; as a faint emitter it keeps its paint
    job = tmp_path / "passes/passes/tiny-0"
    job.mkdir(parents=True)
    (job / "passes.json").write_text(json.dumps({"groups": {"lamp_0": "/tiny/Lights/light_1"}}))
    colours = light.group_colours(tmp_path / "passes", found, record, out / layer.LAYER)
    assert np.allclose(colours["lamp_0"][1], mix.lamp_light(layer.scene.colour("#ffcc00")))
    assert np.allclose(*light.group_colours(tmp_path / "passes", found, record, out / layer.LAYER, {"bulb"})["lamp_0"])
    painted = light.shipped_colours(colours, {"lamp_0": "/tiny/Lights/light_1"}, found, record, out / layer.LAYER)
    boosts = light.colours_written(out / layer.LAYER, painted)
    written = np.array(Sdf.Layer.FindOrOpen(str(out / layer.LAYER)).GetPrimAtPath("/tiny/Lights/light_1")
                       .attributes["inputs:color"].default)
    assert written.max() <= 1.0 + 1e-6 and boosts["/tiny/Lights/light_1"] >= 1.0
    assert math.isclose(float(mix.LUMA @ written) * boosts["/tiny/Lights/light_1"],
                        float(mix.LUMA @ np.array(layer.scene.colour("#ffcc00"))), rel_tol=1e-4)
    # 2026-11-10: flat, under its warm lamps, rendered as a daylight camera sees a tungsten room (cast [162, 128, 93])
    # where its concept's surfaces read about neutral; the eye at a lit place by night adapts to the light it stands
    # in. CIECAM02's D by hand: 100 lx, L_A = 100 / pi / 5 = 6.366 cd/m^2, 1 - e^(-48.366 / 92) / 3.6 = 0.8357.
    assert math.isclose(mix.adaptation_degree(100.0), 0.8357, abs_tol=1e-4)
    # CIE 159's surrounds: dark (SR 0) F 0.8, dim 0.9 at SR 0.1, average 1.0 from 0.2; an eye in the square at 10 lux
    # under its 0.1116 cd/m^2 night sky, SR 0.1116 / (10 / pi) = 0.035, F 0.835, D 0.835 x 0.8252 = 0.689
    assert [mix.surround_factor(ratio) for ratio in (0.0, 0.1, 0.2, 0.5)] == pytest.approx([0.8, 0.9, 1.0, 1.0])
    assert mix.adaptation_degree(10.0, mix.surround_factor(0.1116 / (10.0 / math.pi))) == pytest.approx(0.689,
                                                                                                         abs=0.001)
    tungsten = mix.black_body(2856.0)
    whole, none = mix.adaptation(tungsten, 1.0), mix.adaptation(tungsten, 0.0)
    assert np.allclose(none, np.eye(3)) and np.allclose(whole @ tungsten / float(mix.LUMA @ (whole @ tungsten)),
                                                        np.ones(3), atol=1e-6)
    adapted = mix.unit_light(mix.adaptation(tungsten, 0.8357) @ tungsten)
    # nearer white, a trace of its warmth kept
    assert 1.0 < adapted[0] / adapted[2] < tungsten[0] / tungsten[2], adapted
    views = {"v": ({"combined": np.full((2, 2), 9.0), "lamp_0": np.full((2, 2), 2.0), "lamp_1": np.ones((2, 2))},
                   None)}
    assert np.allclose(mix.adapting_white(views, {"lamp_0": 0.5}, {"lamp_0": (np.ones(3), tungsten),
                                                                  "lamp_1": (np.ones(3), np.ones(3))}),
                       mix.unit_light(tungsten + np.ones(3)))  # its lamps at their scales, the light no group holds out
    # the light no group holds (a shown place's lamps) takes the eye's change of each channel (mix.REST), luminance out
    change = mix.tint({"combined": np.ones((8, 8))}, {}, {mix.REST: (np.ones(3), np.array([2.0, 1.0, 0.5]))},
                      np.ones((8, 8)))
    assert np.allclose(change, mix.unit_light([2.0, 1.0, 0.5]), atol=1e-6), change[0, 0]
    # a night light (no record lamp) ships its adapted colour at the luminance its layer colour was rendered in, and
    # the night air's dome and background are taken through the same adaptation
    stage = Usd.Stage.Open(str(out / layer.LAYER))
    night_moon = UsdLux.DistantLight.Define(stage, "/tiny/Lights/night_moon")
    night_moon.CreateColorAttr(Gf.Vec3f(0.5, 0.5, 0.5))
    dome = UsdLux.DomeLight.Define(stage, "/tiny/Environment")
    dome.CreateColorAttr(Gf.Vec3f(0.2, 0.2, 0.2))
    dome.GetPrim().CreateAttribute("score:background", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(0.1, 0.1, 0.1))
    stage.Save()
    sent = mix.unit_light([0.8, 1.0, 1.3])
    painted = light.shipped_colours({"lamp_1": (np.ones(3), sent)}, {"lamp_1": "/tiny/Lights/night_moon"}, found,
                                    record, out / layer.LAYER)
    assert np.allclose(painted["/tiny/Lights/night_moon"], sent * 0.5), painted
    light.environment_adapted(out / layer.LAYER, "tiny", whole)
    held = Sdf.Layer.FindOrOpen(str(out / layer.LAYER)).GetPrimAtPath("/tiny/Environment")
    assert np.allclose(np.array(held.attributes["inputs:color"].default), whole @ np.full(3, 0.2), atol=1e-6)
    assert np.allclose(np.array(held.attributes["score:background"].default), whole @ np.full(3, 0.1), atol=1e-6)
    # the eye adapts to the light it stands in whatever the hour outside (2026-11-10: greenhouse, a dome lit by its
    # lamps under the Sun, read [175, 105, 101] against its concept's [146, 115, 123], its 2700 K panels seen as a
    # daylight camera sees them): a lamp-lit room (inside, its concept showing no daylight) by day has the eye in its
    # 100 lux (EN 12464-1), pi x 683 / 100 = 21.46 on the views' scale, its room round it; a room its concept shows
    # in daylight, or an outdoor place, has none
    eyes = tmp_path / "night.json"
    eyes.write_text(json.dumps({"adapted_lux": {"outside": 10.0, "inside": 100.0}}))
    unlit = {"scene": {"daylight": False, "unseen": False, "unseen_colour": ""}}
    eye = light.room_eye({"night": str(eyes)}, unlit, {"inside": True})
    assert eye == {"scale": pytest.approx(math.pi * 683.0 / 100.0, rel=1e-3)}, eye
    assert light.room_eye({"night": str(eyes)}, {"scene": dict(unlit["scene"], daylight=True)}, {"inside": True}) \
        is None
    assert light.room_eye({"night": str(eyes)}, unlit, {"inside": False}) is None

    # a concept showing light from no source in view takes its fill, in the open beside a sun over the horizon too
    # (2026-10-30, light@base: its sun, its only light, swept to 1/32 left its shaded walls 53% black where the
    # concept's shade is filled), never where the concept shows none or is not read; the fill is a soft overhead
    # distant light in the open, a sphere light under the ceiling over the middle inside. The seed: a room 6 m across
    # round the middle, a moon km off, an environment dome, a wall's picture
    shown = {"rows": {}, "scene": {"daylight": True, "unseen": True, "unseen_colour": "#ffddbb"}}
    assert light.fill_wanted(shown) and not light.fill_wanted(None)
    assert not light.fill_wanted({**shown, "scene": {**shown["scene"], "unseen": False}})
    seed = tmp_path / "room"
    tiny_seed(seed)
    (seed / "assets/textures").mkdir(parents=True)
    Image.new("RGB", (4, 4), (90, 90, 90)).save(seed / "assets/textures/wall.png")
    base = Usd.Stage.Open(str(seed / "layers/base.usda"))
    UsdGeom.Cube.Define(base, "/tiny/Room").CreateSizeAttr(6.0)
    UsdGeom.Sphere.Define(base, "/tiny/Sky/Moon").AddTranslateOp().Set(Gf.Vec3d(0.0, -5000.0, 0.0))
    UsdLux.DomeLight.Define(base, "/tiny/Environment")
    shader = UsdShade.Shader.Define(base, "/tiny/Looks/wall/picture")
    shader.CreateInput("file", Sdf.ValueTypeNames.Asset).Set("../assets/textures/wall.png")
    base.Save()
    for inside, kind in ((False, UsdLux.DistantLight), (True, UsdLux.SphereLight)):
        out = tmp_path / f"room-inside-{inside}"
        layer.write("tiny", {"lights": [], "environment": {"inside": False}}, seed, out)
        # the scene record, written from the design alone, holds no glow (the old sky record's night glow was the
        # game's, retired 2026-10-21)
        opened = Usd.Stage.Open(str(out / layer.LAYER))  # held while its prim is read
        held = opened.GetPrimAtPath("/tiny/Environment")
        assert not held or not held.HasAttribute("score:glow_threshold")
        found = layer.write_fill(out, seed, "tiny", "#ffddbb", inside, {"floor": [[-3.0, -3.0], [5.0, 3.0]],
                                                                           "ceiling": 3.0},
                                 REPO / "data/library/lamps.json")
        opened = Usd.Stage.Open(str(out / layer.LAYER))
        held = opened.GetPrimAtPath(found["path"])
        assert held.IsA(kind) and found["fill"] and found["sun"], (inside, found)
        assert (found["spot"] is None) != inside and (not inside or found["spot"] == [1.0, 2.7, 0.0]), found
        assert not inside or held.GetAttribute("score:game:range").Get() == 4.0, found  # half the floor's width

    # a shown place keeps its pictures (2026-10-18, light-passes of ten places: a shown place's light layer was written
    # into its seed's copy in the lit tree, and the writer moved that copy's own pictures into assets/light, so its
    # materials drew magenta)
    tree = tmp_path / "tree"
    tree.mkdir()
    shutil.copytree(seed, tree / "tiny", copy_function=os.link)  # hard links, as cp -al (subprocess.run is held above)
    passes.neighbour_layer("tiny", {"lights": []}, seed, tree)
    assert (tree / "tiny/assets/textures/wall.png").exists() and (tree / "tiny" / layer.LAYER).exists()
    assert passes.unresolved(tree / "tiny/tiny.usda") == []
    assert not (tree.parent / "light-of-tiny").exists()
    shutil.rmtree(tree / "tiny/assets/textures")
    assert len(passes.unresolved(tree / "tiny/tiny.usda")) == 1


def exposure_of(folder, look, sky_mask, surface):
    """hall's exposure measures from its one view: its look (levels), its sky mask and its surface reflectance pass,
    when given, saved as rendered."""
    Image.fromarray(np.repeat(look[..., None], 3, axis=2).astype(np.uint8)).save(folder / "looks/hall/v-look.png")
    np.savez(folder / "passes/hall-0/v-passes.npz", combined=np.ones((10, 10)), sky=sky_mask,
             **({} if surface is None else {"surface": surface}))
    return light.exposure_measures("hall", folder, folder)


YARD = {"plots": [{"name": "Rock", "gravity": 9.81}], "sites": [{"place": "yard", "on": "rock", "x": 0, "y": 0}],
        "lights": [{"name": "Sun", "kelvin": 5800, "lux": 100000, "latitude": 52.0, "tilt_deg": 23.44,
                    "day_hours": 24, "year_days": 365.2422, "equinox": "2024-03-20T12:00:00Z"}]}


def design_world(design):
    """The design's kept plans and scene inventories, as score/review/plans.py keeps them: an open yard aiming its
    mast lamp, a room under its roof, a hall aiming nothing, a shed aiming its desk (no glowing kind's row), and the
    wreck, whose plan says where its doors lead; each inventory a mast lamp and a desk. The folder."""
    plans = {"yard": {"shell": "outdoor", "w": 10.0, "d": 10.0, "aims": {"mast_lamp": {"at": "pad"}}},
             "room": {"shell": "kit", "inside": True}, "hall": {"aims": {}},
             "shed": {"aims": {"desk": {"at": "pad"}}}, "wreck": {"leads": {}}}
    for kind in ("plans", "inventory"):
        (design / kind).mkdir(parents=True)
    for place, plan in plans.items():
        (design / f"plans/{place}.json").write_text(json.dumps(plan))
    for place in ("yard", "hall", "shed"):
        (design / f"inventory/{place}.json").write_text(json.dumps({"rows": [
            {"id": "mast_lamp", "name": "mast lamp"}, {"id": "desk", "name": "desk"}]}))
    return design


def needs_of(place, data, design):
    """The light's and the ground's gap ids for `place` (`<place> kept` reads `place`), `data` holding the old
    hand-kept records and the kept skies."""
    place = place.split()[0]
    skies = data / "skies"
    return sorted(gap["id"] for gap in needs.gaps(place, data, skies) +
                  ground_needs.gaps(place, data, design / "plans", skies))


class Accepted:
    """A store holding `held` ({node: record}) as accepted outputs."""

    def __init__(self, held):
        self.held = held

    def accepted(self, node):
        return "output" if node in self.held else None

    def read_file(self, output, name):
        return self.held["scene-record@flat"] if name == "record/flat.json" else None


# --- the measures on pictures made here ----------------------------------------------------------------------------

class Between:
    """A row's expected measure: strictly over `low` and under `high`."""

    def __init__(self, low=-math.inf, high=math.inf):
        self.low, self.high = low, high

    def __eq__(self, value):
        return self.low < value < self.high

    def __repr__(self):
        return f"between {self.low} and {self.high}"


def body_entry(after, sun_seen=True, lit_share=0.5):
    """A body's measure in one view, as light.body_faults reads it."""
    return {"body": "a", "view": "v", "lit": lit_share, "sun_seen": sun_seen, "after": after}


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


def test_a_look_s_sky_is_read_where_the_render_met_no_surface_and_judged_on_the_hue_its_concept_shows(tmp_path,
                                                                                                       monkeypatch):
    """A look's sky is read where the render met no surface, never its top rows' commonest colour, and judged
    against its concept's sky.
    2026-11-02: base's concept drew the Moon's airless sky dark navy ([11.4, 16.5, 27.6], 18.5 levels off black,
    blue to red 2.42); the physics' black sky passed the colour gap (16.7) and failed blue to red (1.0) every round.
    A concept sky within SKY_GAP_MOST of black leaves blue to red unjudged; a lit one still holds it: a sky of
    [95, 90, 95] under a concept of [80, 90, 110] (93 levels off black) passes the gap at 10 levels and fails on blue
    to red 1.0 against 1.375.
    Break: score/stages/light/__init__.py: `hued = dark or abs(ratio - concept["blue_to_red"]) <= BLUE_TO_RED_WITHIN`
        -> `hued = abs(ratio - concept["blue_to_red"]) <= BLUE_TO_RED_WITHIN`"""
    # old_station's lit ground filled its views' top rows and read as its sky, 99.7 levels off its black one
    # (2026-10-30); passes saved before the mask leave the sky unjudged, named
    concept = tmp_path / "concept.png"
    Image.fromarray(np.where(np.arange(100)[:, None, None] < 50, 0, 128).repeat(100, 1).repeat(3, 2)
                    .astype(np.uint8)).save(concept)
    monkeypatch.setattr(light, "concept_pictures", lambda place: [concept])
    (tmp_path / "looks/yard").mkdir(parents=True)
    (tmp_path / "passes/yard-0").mkdir(parents=True)
    sky = np.zeros((100, 100), bool)
    sky[:20] = True
    look = np.where(sky, 0, 200)
    Image.fromarray(np.repeat(look[..., None], 3, axis=2).astype(np.uint8)).save(tmp_path / "looks/yard/v-look.png")
    for held, answer in (({"sky": sky}, checks.PASS), ({}, checks.UNKNOWN)):
        np.savez(tmp_path / "passes/yard-0/v-passes.npz", combined=np.ones((50, 50)), **held)
        (tmp_path / "measures.json").write_text(json.dumps({"sky": light.sky_measures("yard", tmp_path, tmp_path)}))
        verdict = light.judge_sky(tmp_path, {}, {})
        assert verdict.answer == answer, verdict.reason
    assert "no sky mask" in verdict.reason
    # an inside place whose views see sky (2026-11-04: camp's glass domes showed black space, and only outdoor places
    # were judged): read against its sky rows' boxes on its concept, the black top half here, so the look's black
    # sky passes and a lit one fails; with no sky row its concept shows none to judge against
    np.savez(tmp_path / "passes/yard-0/v-passes.npz", combined=np.ones((50, 50)), sky=sky)
    inventory = tmp_path / "inventory.json"
    monkeypatch.setattr(light, "designed", lambda place: True)
    assert light.sees_sky("yard", tmp_path, tmp_path)
    for rows, answer in (([{"id": "stars", "anchor": "sky", "boxes": [[0, 0, 100, 40]]}], checks.PASS),
                         ([{"id": "stars", "anchor": "sky", "boxes": []}], checks.PASS)):
        inventory.write_text(json.dumps({"rows": rows}))
        concept_sky = light.row_skies("yard", inventory)
        measured = light.sky_measures("yard", tmp_path, tmp_path, concept_sky) if concept_sky else \
            {"concept": None, "views": [], "inside": "its concept shows no sky"}
        (tmp_path / "measures.json").write_text(json.dumps({"sky": measured}))
        assert light.judge_sky(tmp_path, {}, {}).answer == answer
    inventory.write_text(json.dumps({"rows": [{"id": "stars", "anchor": "sky", "boxes": [[0, 60, 100, 100]]}]}))
    measured = light.sky_measures("yard", tmp_path, tmp_path, light.row_skies("yard", inventory))
    (tmp_path / "measures.json").write_text(json.dumps({"sky": measured}))
    assert light.judge_sky(tmp_path, {}, {}).answer == checks.FAIL  # its concept's sky lit grey, the look's black
    # a sky row's box holding the place's lit roof under its black sky (2026-11-10: greenhouse's starry band read
    # 58.6 levels grey) is read on the sky's own flat colour, so the look's black sky passes
    inventory.write_text(json.dumps({"rows": [{"id": "stars", "anchor": "sky", "boxes": [[0, 0, 100, 60]]}]}))
    measured = light.sky_measures("yard", tmp_path, tmp_path, light.row_skies("yard", inventory))
    (tmp_path / "measures.json").write_text(json.dumps({"sky": measured}))
    assert light.judge_sky(tmp_path, {}, {}).answer == checks.PASS, measured["concept"]
    # a sky's blue to red is judged only where the concept's sky shows a hue
    def judged(concept_rgb, sky_rgb):
        concept = {"mean_rgb": concept_rgb, "blue_to_red": round(concept_rgb[2] / concept_rgb[0], 4),
                   "rise_to_horizon": 0.0, "pictures": 1}
        after = {"mean_rgb": sky_rgb, "rise_to_horizon": 0.0, "blue_to_red": round(sky_rgb[2] / sky_rgb[0], 4),
                 "gap_to_concept": measure.colour_gap(sky_rgb, concept_rgb)}
        (tmp_path / "measures.json").write_text(json.dumps({"sky": {"concept": concept, "views": [
            {"view": "spot-1", "after": after, "masked": True}]}}))
        return light.judge_sky(tmp_path, {}, {})

    # an inside place's cutaway concept is seen from outside it, its views by the room's eye (2026-11-10: the
    # stairwell's sky through its windows, [3.5, 7.3, 15.1], against its concept's navy [29.8, 33.3, 54.7]): the
    # room's eye at 100 lux takes 21.457 / 214.571 = 0.1 of the light the eye over the square does; the concept's
    # sRGB 29.8, 33.3, 54.7 is linear 0.0128, 0.0152, 0.0373, a tenth of it 4.2, 5.0, 12.2 levels
    painted = {"mean_rgb": [29.8, 33.3, 54.7], "blue_to_red": 1.8356, "rise_to_horizon": 0.0, "pictures": 1}
    inside = light.seen_inside(painted, {"scale": 21.457, "outside_scale": 214.571})
    assert inside["mean_rgb"] == pytest.approx([4.2, 5.0, 12.2], abs=0.15) and inside["painted"] == [29.8, 33.3, 54.7]
    assert judged(inside["mean_rgb"], [3.5, 7.3, 15.1]).answer == checks.PASS
    assert judged(painted["mean_rgb"], [3.5, 7.3, 15.1]).answer == checks.FAIL  # the outside eye's sky: 30.4 levels
    for dark in (None, {"scale": 214.571, "outside_scale": 214.571}, {"scale": 21.457}):  # by day, outside, older
        assert light.seen_inside(painted, dark) == painted
    # on an airless body no air scatters light, so the sky is black whatever the concept paints (2026-11-10: hangar's
    # roof opening on the Moon, [1.1, 1.1, 1.2] against its concept's navy [35.5, 41.9, 69.2], 46.9 levels): judged
    # against black, a black sky passes and a grey one fails; on the Earth (the night table's air) or a dusty body
    # (the record's sky_dome) the concept's sky stands
    navy = {"mean_rgb": [35.5, 41.9, 69.2], "blue_to_red": 1.9516, "rise_to_horizon": 0.0, "pictures": 1}
    table = {"air": {"earth": {"rayleigh_depth": 0.0088}}}
    moon = {"site": {"on": "moon"}, "setting": {"bodies": [{"body": "moon", "reference": "moon"}]}}
    earth = {"site": {"on": "earth"}, "setting": {"bodies": [{"body": "earth", "reference": "earth"}]}}
    airless = light.airless_sky(navy, {}, moon, table)
    assert airless["mean_rgb"] == [0.0, 0.0, 0.0] and airless["painted"] == navy["mean_rgb"]
    for sky_rgb, answer in (([1.1, 1.1, 1.2], checks.PASS), ([30.0, 30.0, 30.0], checks.FAIL)):
        after = {"mean_rgb": sky_rgb, "rise_to_horizon": 0.0, "blue_to_red": round(sky_rgb[2] / sky_rgb[0], 4),
                 "gap_to_concept": measure.colour_gap(sky_rgb, airless["mean_rgb"])}
        (tmp_path / "measures.json").write_text(json.dumps({"sky": {"concept": airless, "views": [
            {"view": "spot-1", "after": after, "masked": True}]}}))
        assert light.judge_sky(tmp_path, {}, {}).answer == answer
    assert judged(navy["mean_rgb"], [1.1, 1.1, 1.2]).answer == checks.FAIL
    assert light.airless_sky(navy, {}, earth, table) == navy
    assert light.airless_sky(navy, {"environment": {"sky_dome": {"depth": 0.6}}}, moon, table) == navy
    assert light.airless_sky(None, {}, moon, table) is None and light.airless_sky(navy, {}, None, table) == navy
    dark = judged([11.4, 16.5, 27.6], [2.5, 2.6, 2.6])
    assert dark.answer == checks.PASS and "not judged" in dark.reason, dark.reason
    lit = judged([80.0, 90.0, 110.0], [95.0, 90.0, 95.0])
    assert lit.answer == checks.FAIL and "gap to the concept 10.0 levels" in lit.reason and "within 0.15" in \
        lit.reason, lit.reason
    # what a view sees through one of the place's doorways is the place the door leads to, never its sky (2026-11-10:
    # hub's door openings, met by no surface down its tubes, read as its sky, 4-9 levels and red against its navy
    # concept): a level view 5 m from a door 4 m wide and 3 m high sees it over columns 26 to 74 and rows 33 to 69 of
    # 100 (focal 50 / tan 40 = 59.6 px); the door's opening is no sky, the sky over the door still is
    door = [{"middle": [0.0, 0.0, -5.0], "inward": [0.0, 0.0, 1.0], "wide": 4.0, "sill": 0.0, "head": 3.0}]
    (tmp_path / "passes/yard-0.views.json").write_text(json.dumps({"size": [100, 100], "views": [
        {"name": "v", "eye": [0.0, 1.6, 0.0], "aim": [0.0, 1.6, -10.0], "up": [0.0, 1.0, 0.0], "fov": 80}]}))
    opening = np.zeros((100, 100), bool)
    opening[36:66, 30:70] = True
    np.savez(tmp_path / "passes/yard-0/v-passes.npz", combined=np.ones((50, 50)), sky=opening)
    assert light.sees_sky("yard", tmp_path, tmp_path) and not light.sees_sky("yard", tmp_path, tmp_path, door)
    behind = [{**door[0], "middle": [0.0, 0.0, 5.0], "inward": [0.0, 0.0, -1.0]}]  # a door behind the eye hides none
    assert light.sees_sky("yard", tmp_path, tmp_path, behind)
    np.savez(tmp_path / "passes/yard-0/v-passes.npz", combined=np.ones((50, 50)), sky=sky | opening)
    assert (light.open_sky(tmp_path, "yard", "v", door) == sky).all()


def inside_functions(*names):
    """Functions and constants of inside/light_passes.py (a Blender script, run only inside Blender) to call here."""
    import ast
    source = (pathlib.Path(passes.__file__).parent / "inside/light_passes.py").read_text()
    kept = [node for node in ast.parse(source).body if isinstance(node, ast.Assign) and node.targets[0].id.isupper()
            and isinstance(node.value, ast.Constant) or getattr(node, "name", None) in names]
    found = {}
    exec(compile(ast.Module(kept, []), "light_passes.py", "exec"), found)
    return found


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
    assert mix.sweep(views, ["lamp_0"], target, most=mix.SUN_MOST) == 1.0  # a sun held at its physical strength
    share = float(2.0 * lamp.sum() / (views_passes["combined"] + lamp).sum())  # the lamp at twice its strength
    assert abs(mix.own_share(views, {"lamp_0": 2.0}, ["lamp_0"]) - share) < 1e-9, share
    assert mix.own_share(views, {}, ["lamp_2"]) is None
    # 2026-11-10, tube: the combined light is denoised, the groups are not; their pixels' difference is noise that no
    # scale turns, which at a sun turned down 32 times read as half the light. On the sums it cancels; the light no
    # group holds (here `rest`) stays at its rendered strength.
    sun = np.full((40, 60), 2.0)
    noise = np.where(np.indices((40, 60)).sum(axis=0) % 2 == 0, 3.0, -3.0)
    noisy = {"combined": rest + lamp + sun, "lamp_0": lamp + noise, "lamp_1": sun - noise}
    floor = {"lamp_0": 1.0, "lamp_1": 1.0 / 32.0}
    truth = float(lamp.sum() / (lamp.sum() + sun.sum() / 32.0 + rest.sum()))
    found = mix.own_share({"v": (noisy, None)}, floor, ["lamp_0"])
    assert abs(found - truth) < 1e-9, (found, truth)
    assert mix.lamp_faults(mix.lamp_measures(views, {}, ["lamp_1"]), ["v"]) == "unlit"
    assert mix.lamp_faults(mix.lamp_measures(views, {}, ["lamp_1"]), []) == "unseen"
    bright = {"combined": rest + 50.0 * lamp, "lamp_0": 50.0 * lamp}
    glaring = {"v": (bright, mix.tone_curve(bright["combined"], np.minimum(bright["combined"], 1.0)))}
    assert mix.lamp_faults(mix.lamp_measures(glaring, {}, ["lamp_0"]), ["v"]) == "blown"
    scale, measures = mix.turned_down(glaring, {}, ["lamp_0"])
    assert scale < 1.0 and mix.lamp_faults(measures, ["v"]) is None, (scale, measures)


def test_the_sun_is_swept_when_the_lamps_stop_at_their_floor_and_lamps_at_one_spot_or_outside_are_judged_so(
        tmp_path, monkeypatch):
    """Faults of 2026-10-30 (#36): airlock's lamps stopped at the sweep's floor while the sun (and fill) carried it
    x1.44 over its concept, never swept since x1.44 is within; engineroom's two wall-panel lamps on one spot each gave
    half the light where they were it, so neither could read blown out; airlock's roof beacon over its dome read
    unlit from inside."""
    ramp = np.tile(np.linspace(0.0, 4.0, 40)[:, None], (1, 60))
    glare = np.where(np.arange(60) < 1, 2000.0 * ramp, 0.0)  # a small glare: the place within x1.5 at the floor
    held = {"lamp_0": glare, "lamp_1": glare, "lamp_2": np.zeros((40, 60)),
            "lamp_3": np.tile(np.linspace(0.05, 0.55, 60), (40, 1))}
    held["combined"] = sum(held.values())
    job = tmp_path / "passes/passes/p-0"
    job.mkdir(parents=True)
    (job / "passes.json").write_text(json.dumps({"groups": {"lamp_0": "/p/Lights/light_1", "lamp_1": "/p/Lights/light_2",
                                                            "lamp_2": "/p/Lights/beacon", "lamp_3": "/p/Lights/sky_sun"}}))
    np.savez(job / "v-passes.npz", **{name: values.astype(np.float16) for name, values in held.items()})
    look = np.repeat(np.repeat(np.round(toned_look(held["combined"]) * 255) / 255, 2, axis=0), 2, axis=1)
    Image.fromarray((np.repeat(look[..., None], 3, axis=2) * 255).astype(np.uint8)).save(job / "v-look.png")
    (tmp_path / "layer").mkdir()
    (tmp_path / "layer" / passes.VIEWS).write_text(json.dumps({"size": [120, 80], "views": [
        {"name": "v", "eye": [0.0, 1.6, 5.0], "aim": [0.0, 1.6, 0.0], "up": [0.0, 1.0, 0.0], "fov": 70.0}]}))
    lamps = [{"path": "/p/Lights/light_1", "spot": [1.0, 2.0, 0.0], "shaft": False},
             {"path": "/p/Lights/light_2", "spot": [1.0, 2.0, 0.0], "shaft": False},
             {"path": "/p/Lights/beacon", "spot": [0.0, 3.2, 0.0], "shaft": False},
             {"path": "/p/Lights/sky_sun", "spot": None, "shaft": False, "sun": True}]
    record = {"inside": True, "floor": [[-3.0, -3.0], [3.0, 3.0]], "ceiling": 3.0}
    monkeypatch.setattr(light, "concept_brightness", lambda place: float(toned_look(np.full((40, 60), 0.2)).mean()))
    monkeypatch.setattr(light, "concept_extremes", lambda place: None)
    assert mix.pinned(float(mix.SCALES[0])) and mix.pinned(float(mix.SCALES[-1])) and not mix.pinned(1.0)
    scales, found = light.strengths("p", tmp_path / "passes", lamps, tmp_path / "layer", record)
    assert found["swept_scale"] == mix.SCALES[0] and found["sun_scale"] < 1.0, found
    one, other = found["lamps"]["/p/Lights/light_1"], found["lamps"]["/p/Lights/light_2"]
    assert other["one_with"] == "/p/Lights/light_1" and scales["lamp_0"] == scales["lamp_1"] < found["swept_scale"]
    assert one["fault"] == other["fault"] == "blown"  # still glaring after its halvings: one lamp, read blown
    assert found["lamps"]["/p/Lights/beacon"]["fault"] == "unseen", found["lamps"]
    assert light.outside_shell([0.0, 3.2, 0.0], record) and not light.outside_shell([0.0, 3.2, 0.0], {"inside": False})
    assert not light.outside_shell([2.9, -0.05, -2.9], record)  # sunk in its deck: still judged
    assert found["source"]["sun_most"] <= mix.SUN_MOST and found["source"]["lamp_lit"] is None, found["source"]
    # 2026-11-04, the light audit: hangar's sun swept to x19 in a night hangar, its lamps 8% of its light. A lamp-lit
    # concept (inside, no daylight) has its suns at the floor while its lamps are swept, never past SUN_MOST after
    held_at = []
    swept = mix.sweep
    monkeypatch.setattr(mix, "sweep", lambda views, groups, target, held=None, most=None, **kept: held_at.append(
        (list(groups), dict(held or {}), most)) or swept(views, groups, target, held, most, **kept))
    _, night = light.strengths("p", tmp_path / "passes", lamps, tmp_path / "layer", record,
                               {"scene": {"daylight": False}})
    assert held_at[0][1] == {"lamp_3": float(mix.SCALES[0])} and all(
        most == mix.SUN_MOST for groups, _, most in held_at if "lamp_3" in groups), held_at
    # 2026-11-10: hangar's lamps (a lamp-lit place's) stopped at x32 with 14% of its light; they reach the top of
    # LAMP_SCALES, a daylit place's lamps only the top of SCALES, where its sun takes over.
    assert held_at[0][2] == float(mix.LAMP_SCALES[-1]) > float(mix.SCALES[-1]), held_at
    held_at.clear()
    light.strengths("p", tmp_path / "passes", lamps, tmp_path / "layer", record, {"scene": {"daylight": True}})
    assert held_at[0][2] == float(mix.SCALES[-1]), held_at
    assert night["source"]["lamp_lit"] is True and night["source"]["sun_most"] <= mix.SUN_MOST, night["source"]
    # 2026-11-10: a lamp-lit night place swept its Moon to the floor as a sun; a night light stands at x1, never swept
    held_at.clear()
    moonlit, _ = light.strengths("p", tmp_path / "passes", lamps, tmp_path / "layer", record,
                                 {"scene": {"daylight": False}}, night_lights=["/p/Lights/sky_sun"])
    assert moonlit["lamp_3"] == 1.0 and not any("lamp_3" in groups for groups, _, _ in held_at), (moonlit, held_at)
    for source, answer, said in (({"lamp_lit": True, "lamp_share": 0.05, "sun_most": 0.5}, checks.FAIL, "5.0%"),
                                 ({"lamp_lit": False, "lamp_share": 0.05, "sun_most": 0.5}, checks.PASS, "daylight"),
                                 ({"lamp_lit": True, "lamp_share": 0.6, "sun_most": 0.5}, checks.PASS, "lamp-lit"),
                                 ({"lamp_lit": False, "lamp_share": 0.6, "sun_most": 19.0}, checks.FAIL, "x19"),
                                 ({"lamp_lit": None, "lamp_share": 0.6, "sun_most": 1.0}, checks.UNKNOWN, "not read")):
        (tmp_path / "measures.json").write_text(json.dumps({"brightness": {"source": source}}))
        verdict = light.judge_source(tmp_path, {}, {})
        assert verdict.answer == answer and said in verdict.reason, (source, verdict.reason)


def test_a_view_in_the_suns_shadow_is_lit_by_the_fill_alone_raised_the_least_that_brings_it(tmp_path, monkeypatch):
    """Fault of 2026-10-30 (#36): at hangar the sun carried 84-94% of every view and was swept with the fill, so
    spot-2, the floor in the parked ship's shadow, stayed at 0.120 against the concept's 0.304 (outside x2.5) with the
    place at x1.00. After the lamps and the suns the fill alone is swept: the least raise that brings every view within
    VIEW_WITHIN with the place kept within BRIGHT_WITHIN; and again once a blown lamp is turned down (2026-11-10)."""
    ramp = np.tile(np.linspace(0.2, 1.8, 30), (20, 1))  # a light that varies, so each view's tone curve has a slope
    held_views = {"lit": {"lamp_0": 1e-4 * ramp, "lamp_1": 0.2 * ramp, "lamp_2": 0.02 * ramp},
                  "shade": {"lamp_0": 1e-4 * ramp, "lamp_1": 0.01 * ramp, "lamp_2": 0.02 * ramp}}
    job = tmp_path / "passes/passes/p-0"
    job.mkdir(parents=True)
    (job / "passes.json").write_text(json.dumps({"groups": {"lamp_0": "/p/Lights/light_1", "lamp_1": "/p/Lights/sky_sun",
                                                            "lamp_2": "/p/Lights/concept_fill"}}))
    for view, held in held_views.items():
        held["combined"] = sum(held.values())
        np.savez(job / f"{view}-passes.npz", **{name: values.astype(np.float16) for name, values in held.items()})
        look = np.repeat(np.repeat(np.round(toned_look(held["combined"]) * 255) / 255, 2, axis=0), 2, axis=1)
        Image.fromarray((np.repeat(look[..., None], 3, axis=2) * 255).astype(np.uint8)).save(job / f"{view}-look.png")
    (tmp_path / "layer").mkdir()
    (tmp_path / "layer" / passes.VIEWS).write_text(json.dumps({"size": [60, 40], "views": [
        {"name": view, "eye": [0.0, 1.6, 5.0], "aim": [0.0, 1.6, 0.0], "up": [0.0, 1.0, 0.0], "fov": 70.0}
        for view in held_views]}))
    lamps = [{"path": "/p/Lights/light_1", "spot": [0.0, 2.0, 0.0], "shaft": False},
             {"path": "/p/Lights/sky_sun", "spot": None, "shaft": False, "sun": True},
             {"path": "/p/Lights/concept_fill", "spot": [0.0, 2.5, 0.0], "shaft": False, "sun": True, "fill": True}]
    target = float(toned_look(np.full((20, 30), 0.2)).mean())
    monkeypatch.setattr(light, "concept_brightness", lambda place: target)
    monkeypatch.setattr(light, "concept_extremes", lambda place: None)
    scales, found = light.strengths("p", tmp_path / "passes", lamps, tmp_path / "layer", {"inside": False})
    views = {view: (held, curve) for view, (held, curve, _) in light.view_passes(tmp_path / "passes", "p").items()}
    lower = float(mix.SCALES[list(mix.SCALES).index(found["fill_scale"]) - 1])
    assert found["fill_scale"] > found["sun_scale"] and scales["lamp_2"] == found["fill_scale"], found
    assert mix.views_within(views, scales, target) and mix.within(views, scales, target), found["after"]
    assert not mix.views_within(views, dict(scales, lamp_2=lower), target)  # the least raise
    assert not mix.views_within(views, dict(scales, lamp_2=found["sun_scale"]), target)  # the suns' sweep alone: off
    assert mix.fill_sweep(views, "lamp_2", target, scales) == scales["lamp_2"]  # swept again: the same
    crowded = {}  # the shade lit only where the fill would carry the middle view, and the place, past x1.5
    for name, sun, fill in (("lit", 0.3, 0.0), ("middle", 0.12, 0.06), ("shade", 0.0, 0.02)):
        held = {"lamp_1": sun * ramp, "lamp_2": fill * ramp, "combined": (sun + fill) * ramp}
        crowded[name] = (held, mix.tone_curve(held["combined"], toned_look(held["combined"])))
    assert mix.within(crowded, {}, 0.12) and not mix.views_within(crowded, {}, 0.12)
    assert mix.views_within(crowded, {"lamp_2": 4.0}, 0.12) and mix.fill_sweep(crowded, "lamp_2", 0.12, {}) == 1.0
    # a blown lamp turned down after the fill's sweep takes its light from the floor it lit: the fill is swept again
    # on the lamps as they then stand (2026-11-10: hangar's light_1 halved for its glare left spot-2 at 0.120 against
    # its concept's 0.304, its fill still at the floor its sweep had set)
    left = (np.arange(30) < 10)[None, :]
    glaring = {"glare": {"lamp_0": np.where(left, 60.0, 0.0) * np.ones((20, 1)), "lamp_1": 0.2 * ramp},
               "lit": {"lamp_0": 0.1 * ramp, "lamp_1": 0.2 * ramp}, "pool": {"lamp_0": 0.06 * ramp, "lamp_1": 0.0 * ramp}}
    for view, held in glaring.items():
        held["lamp_2"] = 0.01 * ramp
        held["combined"] = sum(held.values())
        np.savez(job / f"{view}-passes.npz", **{name: values.astype(np.float16) for name, values in held.items()})
        look = np.repeat(np.repeat(np.round(toned_look(held["combined"]) * 255) / 255, 2, axis=0), 2, axis=1)
        Image.fromarray((np.repeat(look[..., None], 3, axis=2) * 255).astype(np.uint8)).save(job / f"{view}-look.png")
    for view in held_views:
        if view not in glaring:
            (job / f"{view}-passes.npz").unlink()
            (job / f"{view}-look.png").unlink()
    target = float(toned_look(np.full((20, 30), 0.3)).mean())
    monkeypatch.setattr(light, "concept_brightness", lambda place: target)
    scales, found = light.strengths("p", tmp_path / "passes", lamps, tmp_path / "layer", {"inside": True},
                                    {"scene": {"daylight": False}})
    views = {view: (held, curve) for view, (held, curve, _) in light.view_passes(tmp_path / "passes", "p").items()}
    floor = float(mix.SCALES[0])
    assert scales["lamp_0"] < found["swept_scale"] and found["lamps"]["/p/Lights/light_1"]["fault"] is None, found
    assert mix.views_within(views, dict(scales, lamp_0=found["swept_scale"], lamp_2=floor), target)  # before it
    assert not mix.views_within(views, dict(scales, lamp_2=floor), target)  # turned down, the pool too dark
    assert scales["lamp_2"] > floor and found["fill_scale"] == scales["lamp_2"] \
        and found["lamps"]["/p/Lights/concept_fill"]["scale"] == scales["lamp_2"], found
    assert mix.views_within(views, scales, target) and mix.within(views, scales, target), found["after"]


def test_a_fill_the_views_do_not_need_stays_at_the_floor_and_rises_only_as_far_as_their_black_needs(tmp_path):
    """Fault of 2026-10-30 (#36, light@base): the sun, its only light, swept to 1/32 for the bright views, left the
    shaded walls 53% black with every view within x2.5. The fill, wherever the concept shows unseen light, is raised
    from the floor of SCALES only as far as the views need, the exposure gate's rule in that need measured on the looks
    as the light row makes them (light.exposed_within, look_at); a fill no view needs adds no light: it stays at the
    floor."""
    low, high = -24.0, 4.0
    axis = 2.0 ** np.linspace(low, high, 57)
    knots = np.stack(np.meshgrid(axis, axis, axis, indexing="ij"), axis=-1)
    transform = {"table": (knots / (knots + 0.05)) ** 0.6, "low": low, "high": high}  # a tone curve known by hand
    job = tmp_path / "p-0"
    job.mkdir()
    np.savez(job / passes.VIEW_TRANSFORM, **transform)
    ramp = np.tile(np.linspace(0.2, 1.8, 60), (40, 1))
    shadow = (np.arange(60) < 24)[None, :]  # the left 40% of the shade view: the sun's shadow
    views, looks = {}, {}
    for name, sun in (("lit", 0.2 * ramp), ("shade", np.where(shadow, 0.0, 0.2 * ramp))):
        fill = 1e-4 * ramp
        colour = np.repeat((sun + fill)[..., None], 3, axis=2)  # a grey place: its colour is its light
        look = job / f"{name}-look.png"
        Image.fromarray(np.round(mix.displayed(transform, colour) * 255).astype(np.uint8)).save(look)
        held = {"lamp_1": light.halved(sun), "lamp_2": light.halved(fill), "combined": light.halved(sun + fill),
                "colour": colour, "sky": np.zeros(sun.shape, dtype=bool)}  # colour and sky at full size, as saved
        views[name] = (held, mix.tone_curve(held["combined"], light.luminance_of(look)))
        looks[name] = (held, look)
    target, concept, floor = mix.place_brightness(views, {}), {"black": 0.0, "blown": 0.0}, float(mix.SCALES[0])
    assert mix.views_within(views, {"lamp_2": floor}, target)  # within x2.5 with no fill: brightness needs none
    assert not light.exposed_within(looks, concept, {"lamp_2": floor})  # but the shadow is black
    assert mix.fill_sweep(views, "lamp_2", target, {"lamp_2": 1.0}) == floor  # no other need: kept at the floor
    raised = mix.fill_sweep(views, "lamp_2", target, {"lamp_2": 1.0},
                            lambda tried: light.exposed_within(looks, concept, tried))
    lower = float(mix.SCALES[list(mix.SCALES).index(raised) - 1])
    assert raised > floor and light.exposed_within(looks, concept, {"lamp_2": raised})
    assert not light.exposed_within(looks, concept, {"lamp_2": lower})  # the least raise
    assert light.exposed_within(looks, None, {"lamp_2": floor})  # no concept picture: no exposure need


def test_a_sun_blowing_out_the_wall_it_lights_is_stepped_down_only_as_far_as_the_views_need_and_the_fill_after(
        tmp_path, monkeypatch):
    """Fault of 2026-10-31 (#36, round 33): camp's sunlit shell read 2.2-4.3% blown in seven views against its concept's
    0.0% (campgrounds' spot-4 2.4%), the sun 99.7% of the light there and never turned down: a sun is no lamp, and the
    sweep judged blown only lamps. A sun blowing a view past its concept is stepped down SCALES only as far as that
    needs, the place and every view kept within (mix.sun_down), the fill swept after it."""
    low, high = -24.0, 4.0
    axis = 2.0 ** np.linspace(low, high, 57)
    knots = np.stack(np.meshgrid(axis, axis, axis, indexing="ij"), axis=-1)
    transform = {"table": (knots / (knots + 0.05)) ** 0.6, "low": low, "high": high}  # 252 of 255 at 2.3
    job = tmp_path / "passes/passes/p-0"
    job.mkdir(parents=True)
    np.savez(job / passes.VIEW_TRANSFORM, **transform)
    (job / "passes.json").write_text(json.dumps({"groups": {"lamp_0": "/p/Lights/sky_sun",
                                                            "lamp_1": "/p/Lights/concept_fill"}}))
    wall = (np.arange(60) >= 54)[None, :]  # the right tenth: a pale wall in the sun
    sun = np.where(wall, 3.0, 0.2) * np.ones((40, 60))
    fill = np.full((40, 60), 1e-3)
    colour = np.repeat(np.repeat(np.repeat((sun + fill)[..., None], 3, axis=2), 2, axis=0), 2, axis=1)
    Image.fromarray(np.round(mix.displayed(transform, colour) * 255).astype(np.uint8)).save(job / "v-look.png")
    np.savez(job / "v-passes.npz", lamp_0=sun, lamp_1=fill, combined=sun + fill, colour=colour,
             sky=np.zeros(colour.shape[:2], dtype=bool))
    (tmp_path / "layer").mkdir()
    (tmp_path / "layer" / passes.VIEWS).write_text(json.dumps({"size": [120, 80], "views": [
        {"name": "v", "eye": [0.0, 1.6, 5.0], "aim": [0.0, 1.6, 0.0], "up": [0.0, 1.0, 0.0], "fov": 70.0}]}))
    lamps = [{"path": "/p/Lights/sky_sun", "spot": None, "shaft": False, "sun": True},
             {"path": "/p/Lights/concept_fill", "spot": [0.0, 2.5, 0.0], "shaft": False, "sun": True, "fill": True}]
    rendered = light.view_passes(tmp_path / "passes", "p")
    views = {view: (held, curve) for view, (held, curve, _) in rendered.items()}
    looks = {view: (held, look) for view, (held, _, look) in rendered.items()}
    target, concept = mix.place_brightness(views, {}), {"black": 0.0, "blown": 0.0}
    assert not light.exposed_within(looks, concept, {}, ("blown",))  # the wall is white in the render
    monkeypatch.setattr(light, "concept_brightness", lambda place: target)
    monkeypatch.setattr(light, "concept_extremes", lambda place: concept)
    scales, found = light.strengths("p", tmp_path / "passes", lamps, tmp_path / "layer", {"inside": False})
    upper = float(mix.SCALES[list(mix.SCALES).index(scales["lamp_0"]) + 1])
    assert scales["lamp_0"] == found["sun_scale"] < 1.0, found
    assert light.exposed_within(looks, concept, scales)  # the gate's rule holds at the swept strengths
    assert not light.exposed_within(looks, concept, dict(scales, lamp_0=upper), ("blown",))  # the least step down
    assert mix.views_within(views, scales, target) and mix.within(views, scales, target)
    assert scales["lamp_1"] == mix.fill_sweep(views, "lamp_1", target, scales,
                                              lambda tried: light.exposed_within(looks, concept, tried))
    assert mix.sun_down(views, ["lamp_0"], target * 4.0, {"lamp_0": 1.0},
                        lambda tried: light.exposed_within(looks, concept, tried, ("blown",))) == 1.0  # too dark: kept
    monkeypatch.setattr(light, "concept_extremes", lambda place: None)
    assert light.strengths("p", tmp_path / "passes", lamps, tmp_path / "layer", {"inside": False})[0]["lamp_0"] == 1.0


def test_a_dark_view_swept_32_times_up_is_its_float_light_through_the_view_transform_not_its_8_bit_look_scaled(
        tmp_path):
    """Fault (2026-10-30, #36): the mixed look was the render's 8-bit look times the sweep's ratio, so a dark render
    swept 32 times up made every level step of Blender's dither a speck (engineroom 72-114 specks per mille, greenhouse
    45-134). The look is the render's float colour times its mixed light, put through the view transform's table once,
    at the end: at scale 1 within a level of the render's own look, at 32 times near the light rendered so, clean."""
    low, high = -16.0, 4.0
    axis = 2.0 ** np.linspace(low, high, 65)
    knots = np.stack(np.meshgrid(axis, axis, axis, indexing="ij"), axis=-1)
    transform = {"table": (knots / (knots + 0.05)) ** 0.6, "low": low, "high": high}  # a tone curve known by hand
    job = tmp_path / "passes/p-0"
    job.mkdir(parents=True)
    assert passes.passes_faults(tmp_path) == ["no passes rendered", "no look rendered", "no view transform"]
    np.savez(job / passes.VIEW_TRANSFORM, **transform)
    colour = 2.0 ** np.linspace(-14.0, -9.0, 160)[None, :, None] * np.ones((120, 1, 1)) * np.array([1.0, 0.8, 0.6])
    shown = mix.displayed(transform, colour)
    assert np.abs(shown - (colour / (colour + 0.05)) ** 0.6).max() < 0.001  # between knots, trilinear in log light
    rng = np.random.default_rng(3)
    look = job / "v-look.png"  # Blender's look: 8 bits, dithered
    dithered = np.round(shown * 255 + rng.uniform(-1.0, 1.0, shown.shape))
    Image.fromarray(dithered.clip(0, 255).astype(np.uint8)).save(look)
    combined = light.halved(colour @ np.array([0.2126, 0.7152, 0.0722]))
    held = {"combined": combined, "lamp_0": combined * (1.0 + rng.normal(0.0, 0.05, combined.shape)), "colour": colour}
    assert np.abs(np.asarray(light.look_at(held, look, {}), float) - np.asarray(Image.open(look), float)).max() <= 1
    light.look_at(held, look, {"lamp_0": 32.0}).save(tmp_path / "up.png")
    up = np.asarray(Image.open(tmp_path / "up.png"), float)
    assert np.abs(up - mix.displayed(transform, 32.0 * colour) * 255).max() < 6  # as if rendered 32 times as bright
    assert grain.specks(tmp_path / "up.png") < grain.GRAINY_PER_MILLE
    # a lamp's light carries its colour into the mixed look (2026-11-10: greenhouse's lamps swept 25 times up and its
    # sun 32 times down kept its sunlit render's colour): two lamps, a warm and a cool, each half the light; the warm
    # one off, the look is the cool one's colour; in the colours rendered at scale 1 the look is the render's
    warm, cool = mix.unit_light([1.0, 0.6, 0.3]), mix.unit_light([0.5, 0.7, 1.0])
    both = {"lamp_0": (warm, warm), "lamp_1": (cool, cool)}
    halves = {"combined": combined, "lamp_0": combined / 2, "lamp_1": combined / 2, "colour": colour}
    assert np.abs(np.asarray(light.look_at(halves, look, {}, both), float) -
                  np.asarray(light.look_at(halves, look, {}), float)).max() <= 1
    # the sky (where the render met no surface) is light no group holds: a lamp swept 32 times up beside it never
    # brightens it through the smoothing (2026-11-10: the square's sky x1.24 to x1.58 by its lamps turned up)
    open_sky = np.zeros(colour.shape[:2], bool)
    open_sky[:, 80:] = True
    lamp = np.ones_like(combined)
    lamp[:, 40:] = 0.0  # the lamp lights the left half only; the sky stands right of it
    sided = {"combined": combined, "lamp_0": combined * lamp, "colour": colour, "sky": open_sky}
    swept = np.asarray(light.look_at(sided, look, {"lamp_0": 32.0}), float)
    rendered = np.asarray(light.look_at(sided, look, {}), float)
    assert np.abs(swept - rendered)[:, 80:].max() <= 1 and np.abs(swept - rendered)[:, :70].max() > 20
    unmasked = np.asarray(light.look_at({**sided, "sky": np.zeros_like(open_sky)}, look, {"lamp_0": 32.0}), float)
    assert np.abs(unmasked - rendered)[:, 80:84].max() > 1  # without the mask the smoothing reaches it
    change = mix.tint(halves, {"lamp_0": 0.0}, both, light.luminance_of(look)[:combined.shape[0], :combined.shape[1]])
    assert np.allclose(change, cool / ((warm + cool) / 2) / float(mix.LUMA @ (cool / ((warm + cool) / 2))), atol=1e-3)
    # a white lamp painted in its glow's saturated tint throws its black body's light: #ffcc88 is about 3570 K, close
    # to the locus, and its light has more blue than its paint; a magenta grow light keeps its hue; D65 is near white
    painted = np.array(layer.scene.colour("#ffcc88"))
    kelvin, duv = mix.white_fit(painted)
    assert 3400 < kelvin < 3700 and duv < 0.01
    assert mix.lamp_light(layer.scene.colour("#ffcc00"))[2] > mix.unit_light(layer.scene.colour("#ffcc00"))[2] + 0.1
    assert np.allclose(mix.lamp_light(layer.scene.colour("#ff55ff")), mix.unit_light(layer.scene.colour("#ff55ff")))
    assert np.allclose(mix.black_body(6504.0) / mix.black_body(6504.0).max(), 1.0, atol=0.07)
    # the lamps' balance by colour (2026-11-10, greenhouse's warm panels outshining the magenta grow light its concept
    # shows brightest): the class giving the most light held, another swept to the cast's least gap, kept only where
    # it brings the cast BALANCE_GAIN nearer
    chosen, before, after = mix.balance(["panels", "grow"], "panels", lambda found: abs(np.log2(found["grow"]) - 3.0))
    assert chosen == {"panels": 1.0, "grow": 8.0} and before == 3.0 and after == 0.0
    assert mix.balance(["panels", "grow"], "panels", lambda found: 0.5 * abs(np.log2(found["grow"]) - 1.0))[0] == \
        {"panels": 1.0, "grow": 1.0}
    # a screen swept with the lamps never passes its own share (camp, 2026-11-10: its screens at x32 lit it cool)
    assert mix.capped(["panels", "screen"], 8.0, {"panels": 0.5}, {"screen": 1.0}) == {"panels": 4.0, "screen": 1.0}
    # a screen (a faint emitter) or a sun is never raised past its `most`
    assert mix.balance(["panels", "screen"], "panels", lambda found: abs(np.log2(found["screen"]) - 3.0),
                       {"screen": 1.0})[0] == {"panels": 1.0, "screen": 1.0}
    # the balance's estimate brings its lights back to the swept brightness no further than their caps let the looks
    # (2026-11-10: greenhouse's estimate read 1.2 levels on its screens brought back past their cap, its looks 32.5):
    # a cool lamp in a grey room beside light no group holds: brought back x4 it reads bluer, at `room` 1 as it stands
    grey = np.full((32, 32, 3), 0.02)
    lamp = np.full((32, 32), 0.05)
    view = (grey, transform, None, {"lamp_0": lamp}, np.full((32, 32, 1), 0.1),
            np.full((32, 32, 1), 0.1) + lamp[..., None] * cool)
    lamps = {"lamp_0": (cool, cool)}
    plain = light.balanced_cast([view], lamps, {"lamp_0": 1.0})
    assert plain is not None and light.balanced_cast([view], lamps, {"lamp_0": 1.0}, keep=204.8, room=1.0) == plain
    assert light.balanced_cast([view], lamps, {"lamp_0": 1.0}, keep=204.8)[2] > plain[2] + 3.0
    # a warning light or beacon is a signal, a faint emitter, never a room's lamp (garage's amber bulbs, 2026-11-10)
    from score.stages.scene_record import writer
    library = pathlib.Path(__file__).resolve().parents[3] / "data/library/lamps.json"
    assert writer.glow_share({"id": "warning_light", "noun": "light"}, {"glowing": "bulb"}, library)[1] == "emitter"
    assert writer.glow_share({"id": "ceiling_lamp", "noun": "lamp"}, {"glowing": "bulb"}, library)[1] == "source"


def test_the_stage_lit_lays_the_bakes_models_and_the_made_ground(tmp_path, monkeypatch):
    """Fault (2026-10-29, light-passes@base and @airlock): the lit stage was the seed with its record, every design
    object waiting on the surface line's bake and no made ground, so base drew nothing and airlock a bare shell. The
    stage is laid by the assembly's own code: the bake's model at its waiting entry, the made ground over the base.
    Fault (2026-11-04, the eyes review of env1): the made ground was laid with its finish named missing, never bound to
    the surface its scene library gives its row as the assembly binds it, so the campgrounds', base's, square's and
    street's ground rendered a white sheet. It is finished by the assembly's own code (ground_finish), and the layer's
    `surfaced` gate (bare.faults) names a ground or shell mesh with no library surface and an outdoor place's empty
    sky before the paid render.
    Break: passes.source: `ground_finish.finish_ground(...)` dropped (the ground stays named missing).
    Break: bare.faults: `why = bare_why(prim)` -> `why = None` (an unfinished ground or bare wall passes).
    Break: bare.faults: `if outdoor and not sky` -> `if False` (an outdoor place with an empty sky passes).
    Break: passes.shown_in: the `neighbour <name>` test dropped (a ground scene read beside is rendered as shown)."""
    import score.stages.assembly.baked as baked
    from score.stages.light import bare
    from score.stages.terrain import outside
    tiny_seed(tmp_path / "seed")
    seed = Usd.Stage.Open(str(tmp_path / "seed/layers/base.usda"))
    shader = UsdShade.Shader.Define(seed, "/tiny/Library/lunar_regolith/surface")
    shader.CreateIdAttr("UsdPreviewSurface")
    UsdShade.Material.Define(seed, "/tiny/Library/lunar_regolith").CreateSurfaceOutput().ConnectToSource(
        shader.ConnectableAPI(), "surface")
    seed.GetRootLayer().Save()
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
    points, triangles = np.array([[0, 0, 0], [1, 0, 0], [0, 0, 1]], float), np.array([[0, 2, 1]])
    outside.write(ground, "tiny", {"near": (points, triangles)}, "regolith", ["regolith", "the test's"])
    ground.Save()
    (tmp_path / "inventory.json").write_text(json.dumps({"rows": [{"id": "regolith", "noun": "ground",
                                                                   "terrain": True}]}))
    (tmp_path / "library").mkdir()
    (tmp_path / "library/materials.json").write_text(json.dumps({"kinds": {"ground": ["lunar_regolith"]}}))

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
    bare_root = passes.source("tiny", inputs, tmp_path / "bare") / "tiny.usda"
    named = bare.faults(bare_root, "tiny")
    assert any("/tiny/Outside/near (ground): its finish is named missing" in fault for fault in named), named
    assert any("empty sky" in fault for fault in named), named
    inputs.update({"surface-library": str(tmp_path / "library"), "inventory tiny": str(tmp_path / "inventory.json")})
    root = passes.source("tiny", inputs, tmp_path / "lit") / "tiny.usda"
    stage = Usd.Stage.Open(str(root))
    assert stage.GetPrimAtPath("/tiny/Objects/hub_1").IsValid() and stage.GetPrimAtPath("/tiny/Terrain/ground")
    assert light.drawn_count(root, "tiny") == 3
    near = stage.GetPrimAtPath("/tiny/Outside/near")
    assert UsdShade.MaterialBindingAPI(near).ComputeBoundMaterial()[0].GetPath() == "/tiny/Library/lunar_regolith"
    assert bare.faults(root, "tiny") == ["/tiny: an outdoor place with an empty sky (no sky element nor dome light)"]
    wall = UsdGeom.Mesh.Define(stage, "/tiny/Shell/wall").GetPrim()
    wall.CreateAttribute("score:kind", Sdf.ValueTypeNames.String).Set("structure")
    UsdLux.DomeLight.Define(stage, "/tiny/Sky/Backdrops/stars")
    stage.Save()
    assert bare.faults(root, "tiny") == ["/tiny/Shell/wall (structure): it is bound to no material"]
    UsdGeom.Imageable(wall).MakeInvisible()
    stage.Save()
    assert bare.faults(root, "tiny") == []
    assert passes.shown_in({"scene-record@base": "x", "scene-record@square": "y", "neighbour square": "z"}) == \
        ["square"]


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


def placed_seed(seed, spot, meshes, carried):
    """A tiny seed (tiny_seed) with its lamp at `spot`, each of `meshes` ((path, boxes), every (low, high) box of
    one closed mesh) laid in it, and, when `carried` is given, its lamp carried that far along x with a floor light
    the assembly moved out of a wall (lamps_along.moved_with)."""
    tiny_seed(seed)
    base = Usd.Stage.Open(str(seed / "layers/base.usda"))
    UsdGeom.Xformable(base.GetPrimAtPath("/tiny/Lights/light_1")).GetOrderedXformOps()[0].Set(Gf.Vec3d(*spot))
    for path, boxes in meshes:
        corners, faces = [], []
        for low, high in boxes:
            start = len(corners)
            corners += [(x, y, z) for x in (low[0], high[0]) for y in (low[1], high[1]) for z in (low[2], high[2])]
            faces += [start + index for index in (0, 1, 3, 2, 4, 6, 7, 5, 0, 4, 5, 1, 2, 3, 7, 6, 0, 2, 6, 4, 1, 5,
                                                  7, 3)]
        mesh = UsdGeom.Mesh.Define(base, path)
        mesh.CreatePointsAttr([Gf.Vec3f(*corner) for corner in corners])
        mesh.CreateFaceVertexCountsAttr([4] * (6 * len(boxes)))
        mesh.CreateFaceVertexIndicesAttr(faces)
    if carried is not None:
        lamps_along.moved_with(base, "tiny", np.array([-0.1, 1.9, -0.1]), np.array([0.1, 2.1, 0.1]), np.zeros(3),
                               1.0, np.array([carried, 0.0, 0.0]))
    base.Save()
    return seed
