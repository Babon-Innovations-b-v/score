"""A surface's maps fit the recipe they show (its family by its name's finish word, else by its metal and roughness;
its colour, roughness, metal, pattern size and bump from the maps), and the look-alike check passes a recipe's
pictures only when they look like the maps' (its colour, and its detail where the maps show detail).

Each row is 64-texel maps written under the file names an adopted set or an image set gives them, the material's
name, its surface.json (its tile size; an adopted set's maps by role, its normal convention), and a pair of 64-pixel pictures standing in for the two renders (inside/likeness.py, which needs
Blender and the card: it is proven by a run on this PC's card, see the overlay). Every answer is worked out by hand:
- sRGB 119 is L* 50.0 (linear 0.1845), so the fitted colour is 0.1845 in each channel; an ORM green of 102 is
  roughness 0.4, a blue of 255 metal 1.0 (of 230 metal 0.902, green 25 roughness 0.098: a metal under 0.25 rough is
  polished);
- the relief row's height is 2 sin(2 pi x / 16) sin(2 pi y / 16) texels at 1 mm a texel: its spread is half its
  amplitude, 1 texel, 0.001 m, so the bump is 4 x 0.001 = 0.004; its autocorrelation, cos(2 pi lag / 16), first falls
  under half at lag 3 (cos 67.5 deg = 0.38; lag 2 gives 0.71), so its features are 3 x 4 texels = 0.012 m;
- the adopted relief row is the same relief as a DirectX map (its green turned over) whose surface.json knows no tile
  size: its features are 12 / 64 = 0.1875 of a tile, so the tile is fitted to 0.01 / 0.1875 = 0.0533 m, where they
  are concrete's default pore size 0.01, and its bump 4 x 0.0533 / 64 = 0.0033;
- the plastic relief row is the relief row's maps under a plastic's name: its 0.012 m features are over plastic's
  largest grain (4 x 0.002 = 0.008 m), so the grain is 0.008 and the bump keeps the relief's slope, 0.004 x 0.008 /
  0.012 = 0.0027 (at its full 0.004 a field of steep bumps that scatters the highlight away);
- the fine slopes row's 2 x 2 blocks of +-0.2 average to a normal of length 0.9798, hiding a variance of 0.0206
  (Toksvig), so its roughness 0.4 widens to (0.4^4 + 0.0206)^(1/4) = 0.464;
- the scratched chrome's ORM green stripes of 70 and 80 (0.2745 and 0.3137) spread 0.0196, so its scratches are
  0.0196 / 0.075 = 0.2614; its flat recipe beside striped maps has no detail, so the refinement doubles them;
- the constant colour row has no albedo map: its colour is its surface.json's constant diffuseColor, linear 0.1845;
- the glow rows are an emissive white: its constant emissiveColor (5, 5, 5) is carried as the map side's glow, unless
  an emission map feeds the glow (USD draws a connected input, never its constant): then the map, and no constant;
- sRGB (150, 104, 112) is Lab (48.95, 19.66, 2.96), 19.9 from sRGB 119's (50.0, 0, 0): over the check's 10, while its
  lightness stays within 1.1 (the lightness and highlight bounds hold); stripes of sRGB 109 and 129 (L* 46.0 and
  54.0) two pixels wide beside a flat sRGB 119 differ under 0.1 in cell colour and 4 in lightness, but the flat one
  has no detail: a detail ratio of 0, under 0.8.

Breaks (each applied once, seen red, reverted, 2026-11-22):
- fit.family_of: `if word in lowered:` -> `if False:` (every named row reads its family by its measures: the plastic,
  chrome and concrete rows red).
- fit.height_of: `normal[..., 1] / tilt` -> `-normal[..., 1] / tilt` (the relief row's slopes no longer integrate:
  its height spread falls by half).
- fit.role_of: no trailing number dropped (`T_..._Albedo_1.png` reads no role: the second row has no albedo).
- fit.described: `maps.items()` read as the dict's keys (the adopted row's maps are files named `albedo`, never
  written), or relief_statistics' DirectX `normal[..., 1] = -normal[..., 1]` dropped (the adopted row's slopes no
  longer integrate: its bump halves), or fitted's `fitted_tile` made None (the adopted row's tile assumed 1 m).
- fit.spec_of: the bump's `* drawn / feature` dropped (the plastic relief row's bump is the full 0.004).
- fit.described: `albedo_colour` always None (the constant colour row has no albedo: KeyError).
- fit.described: `emission_colour` always None (the constant glow row loses its five-times white), or the constant
  read even beside an emission map (the emission map row glows twice); fit.ROLE_WORDS without "emission" (the
  emission map row's emission.png reads no role).
- fit.described: `constants` always {} (the glass constants row keeps glass's 0.05 roughness and 0.2 opacity, the
  metal constants row metal 0), or statistics' UNSAID_ROUGHNESS read as the family's default (the cotton row 0.85).
- measure.roughness_step: the secant dropped (the dim highlight row steps 0.04 smoother, 0.36, not 0.6), or
  measure.breach's detail share dropped (that row ranks (0, 0.0), a pass).
- measure.shifted: the colour clipped channel by channel (colour.linear_of_lab alone): the orange row's raised
  colour turns yellow, lightness 96.9 at hue 104, not 99.1 at 92 (its shift, sRGB (255, 200, 120) less (200, 100, 30)
  in Lab, on (0.8, 0.3, 0.05) is L 99.1 at hue 91.6, in gamut only near grey).
- fit.FAMILY_WORDS without "mirror" (the mirror row is glass), or family_of's UNMETALLED rule dropped (the metal
  glass row is glass).
- fit.family_of: the glow rule dropped (the lamp glass row is glass, the warm plastic plastic), or spec_of's glow
  hue dropped (the warm plastic's colour its diffuse 0.8).
- fit.described: PACKED_ROLES' split dropped (the packed row has no albedo: KeyError), or statistics' alpha read
  dropped (its roughness USD's 0.5).
- fit.rebuilt: the map's own blue kept (the turned-under row's slopes over FLAT_FLOOR: its relief far too high).
- fit.spec_of: toksvig_roughness dropped (the fine slopes row's roughness stays 0.4).
- fit.spec_of: the no-normal-map flattening dropped (the cotton row keeps cloth's 0.0002 bump, the boxes row
  cardboard's 0.0003 flutes).
- fit.spec_of: the scratches fit dropped (the flat chrome keeps polished_metal's 0.3), or measure.refined's scratches
  left out (the scratched chrome's stay 0.2614).
- measure.passes: `measured["delta_e"] <= DELTA_E_BOUND` -> `True` (the shifted colour passes).
- measure.view_measures: `detail = 1.0` always (the flat recipe beside striped maps passes).
"""
import pathlib
import sys

import numpy as np
import pytest
from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import colour  # noqa: E402
import fit  # noqa: E402
import measure  # noqa: E402

SIDE = 64
FLAT_NORMAL = (128, 128, 255)


def solid(rgb):
    """A SIDE-square picture of one colour."""
    return np.tile(np.array(rgb, dtype=np.uint8), (SIDE, SIDE, 1))


def bumps(amplitude, period):
    """A GL normal map of the height amplitude * sin(2 pi x / period) * sin(2 pi y / period) texels (y up the
    picture, as a GL map's green)."""
    across, row = np.meshgrid(np.arange(SIDE), np.arange(SIDE))
    wave = 2 * np.pi / period
    up = SIDE - 1 - row
    slope_across = amplitude * wave * np.cos(wave * across) * np.sin(wave * up)
    slope_up = amplitude * wave * np.sin(wave * across) * np.cos(wave * up)
    normal = np.stack([-slope_across, -slope_up, np.ones_like(slope_up)], -1)
    normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
    return np.round((normal + 1.0) * 127.5).astype(np.uint8)


def stripes(dark, light):
    """Upright stripes two pixels wide, alternating two greys."""
    picture = solid((dark,) * 3)
    picture[:, (np.arange(SIDE) // 2) % 2 == 1] = light
    return picture


def written(folder, pictures, surface):
    """Each {file name: RGB array} written as a picture in `folder`; the surface.json's reading (fit.described), its
    maps {role: path}."""
    for name, pixels in pictures.items():
        Image.fromarray(pixels).save(folder / name)
    found = fit.described(surface, list(pictures))
    return {**found, "maps": {role: str(folder / name) for role, name in found["maps"].items()}}


def directx(normal):
    """A GL normal map as DirectX keeps it: its green turned over."""
    turned = normal.copy()
    turned[..., 1] = 255 - turned[..., 1]
    return turned


def seen(recipe, family_from, colour, roughness, metal, relief, passed, glow):
    """A row's whole answer: the fit's family and where it came from, its mean colour, roughness, metal and relief,
    whether the pictures pass, and the glow it carries (its constant emissiveColor, an emission map)."""
    return {"recipe": recipe, "family_from": family_from, "colour": colour, "roughness": roughness, "metal": metal,
            "relief": relief, "pass": passed, "glow": glow}


def lightness_hue(linear):
    """A linear colour's CIE lightness and hue angle (degrees), rounded."""
    lab = colour.lab(np.asarray(linear, dtype=float))
    return round(float(lab[0]), 1), float(round(np.degrees(np.arctan2(lab[2], lab[1]))))


def texel_tilts(slope):
    """A 1024-texel normal map tilted +-`slope` in x texel by texel, a chequer: read at fit.READ_SIDE (512) each 2 x 2
    block averages to (0, 0, sqrt(1 - slope^2))."""
    across, row = np.meshgrid(np.arange(1024), np.arange(1024))
    sign = np.where((across + row) % 2 == 0, 1.0, -1.0)
    normal = np.stack([sign * slope, np.zeros_like(sign), np.full_like(sign, np.sqrt(1 - slope ** 2))], -1)
    return np.round((normal + 1.0) * 127.5).astype(np.uint8)


def under(normal):
    """A normal map whose blue is turned under its surface (z negative), its red and green as they were."""
    turned = normal.copy()
    turned[..., 2] = 255 - turned[..., 2]
    return turned


def opaque(pixels):
    """An RGB picture as a fully covered RGBA render."""
    return np.concatenate([pixels, np.full((SIDE, SIDE, 1), 255, dtype=np.uint8)], -1)


ROWS = [
    ("plastic, the same look", "t_plastic_glossy_gray_a01",
     {"t_plastic_glossy_gray_a01_tile_alb.png": solid((119,) * 3),
      "t_plastic_glossy_gray_a01_tile_orm.png": solid((255, 102, 0)),
      "t_plastic_glossy_gray_a01_tile_nor.png": solid(FLAT_NORMAL)}, {"tile_metres": 1.0},
     (solid((119,) * 3), solid((119,) * 3)),
     seen("plastic", "name", 0.1845, 0.4, None, None, True, (None, False))),
    ("chrome by its name, older file names", "T_Metal_Chrome_A",
     {"T_Metal_Chrome_A_Albedo_1.png": solid((119,) * 3), "T_Metal_Chrome_A_ORM_1.png": solid((255, 102, 255)),
      "T_Metal_Chrome_A_Normal_1.png": solid(FLAT_NORMAL)}, {"tile_metres": 1.0},
     (solid((119,) * 3), solid((119,) * 3)),
     seen("polished_metal", "name", 0.1845, 0.4, 1.0, None, True, (None, False))),
    ("metal by its measures, a colour shifted", "t_unnamed_a01",
     {"t_unnamed_a01_tile_alb.png": solid((119,) * 3), "t_unnamed_a01_tile_orm.png": solid((255, 25, 230))}, {"tile_metres": 1.0},
     (solid((119,) * 3), solid((150, 104, 112))),
     seen("polished_metal", "measures", 0.1845, 0.098, 0.902, None, False, (None, False))),
    ("concrete relief, a flat recipe beside detail", "t_concrete_bare_a01",
     {"colour.jpg": solid((119,) * 3), "roughness.png": solid((102,) * 3), "normal.png": bumps(2.0, 16)},
     {"tile_metres": 0.064}, (stripes(109, 129), solid((119,) * 3)),
     seen("concrete", "name", 0.1845, 0.4, None, (0.012, 0.004, 0.064), False, (None, False))),
    ("an adopted set's relief, maps by role, DirectX, tile fitted", "t_concrete_bare_a01",
     {"albedo.png": solid((119,) * 3), "roughness.png": solid((102,) * 3), "normal.png": directx(bumps(2.0, 16))},
     {"maps": {"albedo": "albedo.png", "roughness": "roughness.png", "normal": "normal.png"}, "tile_metres": None,
      "normal_convention": "directx"}, (stripes(109, 129), solid((119,) * 3)),
     seen("concrete", "name", 0.1845, 0.4, None, (0.01, 0.003, 0.0533), False, (None, False))),
    ("plastic relief over its largest grain, the bump at its slope", "t_plastic_rough_black_a01",
     {"t_plastic_rough_black_a01_tile_alb.png": solid((119,) * 3),
      "t_plastic_rough_black_a01_tile_orm.png": solid((255, 102, 0)),
      "t_plastic_rough_black_a01_tile_nor.png": bumps(2.0, 16)}, {"tile_metres": 0.064},
     (solid((119,) * 3), solid((119,) * 3)),
     seen("plastic", "name", 0.1845, 0.4, None, (0.008, 0.003, 0.064), True, (None, False))),
    ("a constant colour, no albedo map", "m_opaque_metal_chrome_a01",
     {"normal.png": solid(FLAT_NORMAL), "orm.png": solid((255, 102, 255))},
     {"maps": {"normal": "normal.png", "orm": "orm.png"}, "tile_metres": 1.0,
      "constants": {"diffuseColor": [0.1845, 0.1845, 0.1845]}}, (solid((119,) * 3), solid((119,) * 3)),
     seen("polished_metal", "name", 0.1845, 0.4, 1.0, None, True, (None, False))),
    ("a constant glow, its intensity in its size", "m_opaque_plastic_emissive_white_a01",
     {"normal.png": solid(FLAT_NORMAL), "orm.png": solid((255, 102, 0))},
     {"maps": {"normal": "normal.png", "orm": "orm.png"}, "tile_metres": 1.0,
      "constants": {"diffuseColor": [1.0, 1.0, 1.0], "emissiveColor": [5.0, 5.0, 5.0]}},
     (solid((255,) * 3), solid((255,) * 3)),
     seen("glowing", "name", 1.0, 0.4, None, None, True, ([5.0, 5.0, 5.0], False))),
    ("an emission map by its file name, over a constant glow", "m_opaque_plastic_emissive_white_a01",
     {"emission.png": solid((255,) * 3), "normal.png": solid(FLAT_NORMAL), "orm.png": solid((255, 102, 0))},
     {"tile_metres": 1.0, "constants": {"diffuseColor": [1.0, 1.0, 1.0], "emissiveColor": [5.0, 5.0, 5.0]}},
     (solid((255,) * 3), solid((255,) * 3)),
     {**seen("glowing", "name", 1.0, 0.4, None, None, True, (None, True)), "glow_strength": 1.0}),
    ("a glass's constants, no maps", "m_trans_glass_black_a01", {},
     {"maps": {}, "tile_metres": 1.0,
      "constants": {"diffuseColor": [0.1845] * 3, "roughness": 0.27, "metallic": 0.0, "opacity": 0.054}},
     (solid((119,) * 3), solid((119,) * 3)), {"recipe": "glass", "roughness": 0.27, "opacity": 0.054}),
    ("a metal's constants, no maps", "m_opaque_metal_chrome_a01", {},
     {"maps": {}, "tile_metres": 1.0, "constants": {"diffuseColor": [0.1845] * 3, "roughness": 0.0, "metallic": 1.0}},
     (solid((119,) * 3), solid((119,) * 3)), {"recipe": "polished_metal", "roughness": 0.0, "metal": 1.0}),
    ("no roughness said anywhere: USD's default, as the map side draws", "m_opaque_fabric_cotton_black_a01",
     {"albedo.png": solid((119,) * 3)}, {"maps": {"albedo": "albedo.png"}, "tile_metres": 1.0},
     (solid((119,) * 3), solid((119,) * 3)), {"recipe": "cloth", "roughness": 0.5, "heights": (0.0, None)}),
    ("no normal map: no flutes", "paper_unique_brown_boxes_a", {},
     {"maps": {}, "tile_metres": None, "constants": {"diffuseColor": [0.1845] * 3}},
     (solid((119,) * 3), solid((119,) * 3)), {"recipe": "cardboard", "heights": (None, 0.0)}),
    ("a dim highlight that lowering made dimmer: rougher, ranked by its one breach", "t_plastic_glossy_gray_a01",
     {"t_plastic_glossy_gray_a01_tile_alb.png": solid((119,) * 3),
      "t_plastic_glossy_gray_a01_tile_orm.png": solid((255, 102, 0))}, {"tile_metres": 1.0},
     (stripes(109, 129), solid((119,) * 3), {"roughness": 0.5, "highlight": -2.0}),
     {"recipe": "plastic", "roughness": 0.4, "pass": False, "refined_roughness": 0.6, "ranking": (1, 1.0)}),
    ("an orange raised past the gamut keeps its hue", "m_opaque_metal_anodized_orange_a01", {},
     {"maps": {}, "tile_metres": 1.0, "constants": {"diffuseColor": [0.8, 0.3, 0.05]}},
     (solid((255, 200, 120)), solid((200, 100, 30))), {"recipe": "anodized", "refined_lab": (99.1, 92.0)}),
    ("a mirror is a metal, though its name says glass", "m_opaque_glass_mirror_a01", {"metal.png": solid((255,) * 3)},
     {"maps": {"metal": "metal.png"}, "tile_metres": 1.0,
      "constants": {"diffuseColor": [0.1845] * 3, "roughness": 0.0}},
     (solid((119,) * 3), solid((119,) * 3)), {"recipe": "polished_metal", "family_from": "name", "metal": 1.0}),
    ("a glass whose constant metal is 1 is a metal", "m_trans_glass_black_a01", {},
     {"maps": {}, "tile_metres": 1.0, "constants": {"diffuseColor": [0.1845] * 3, "roughness": 0.27, "metallic": 1.0}},
     (solid((119,) * 3), solid((119,) * 3)), {"recipe": "bare_metal", "family_from": "measures", "metal": 1.0}),
    ("a glass lamp that glows is glowing, at its strength", "m_trans_glass_light_a01", {},
     {"maps": {}, "tile_metres": 1.0, "constants": {"diffuseColor": [1.0] * 3, "emissiveColor": [3.7] * 3}},
     (solid((255,) * 3), solid((255,) * 3)),
     {"recipe": "glowing", "family_from": "measures", "colour": 1.0, "glow_strength": 3.7}),
    ("a plastic's warm glow: its hue at its strongest channel's strength", "m_opaque_plastic_white_a01", {},
     {"maps": {}, "tile_metres": 1.0, "constants": {"diffuseColor": [0.8] * 3, "emissiveColor": [3.0, 2.66, 1.65]}},
     (solid((255,) * 3), solid((255,) * 3)),
     {"recipe": "glowing", "family_from": "measures", "colour": 0.8122, "glow_strength": 3.0}),
    ("a packed albedo, its roughness in its alpha", "m_trans_glass_colored_a01",
     {"albedo_roughness.png": solid((119, 119, 119, 51))},
     {"maps": {"albedo_roughness": "albedo_roughness.png"}, "tile_metres": 1.0, "constants": {"metallic": 1.0}},
     (solid((119,) * 3), solid((119,) * 3)),
     {"recipe": "polished_metal", "colour": 0.1845, "roughness": 0.2, "metal": 1.0}),
    ("a normal map whose blue points into the surface reads by its slopes", "t_concrete_bare_a01",
     {"colour.jpg": solid((119,) * 3), "roughness.png": solid((102,) * 3), "normal.png": under(bumps(2.0, 16))},
     {"tile_metres": 0.064}, (solid((119,) * 3), solid((119,) * 3)),
     {"recipe": "concrete", "relief": (0.012, 0.004, 0.064)}),
    ("slopes finer than the read widen the roughness", "t_plastic_glossy_gray_a01",
     {"t_plastic_glossy_gray_a01_tile_alb.png": solid((119,) * 3),
      "t_plastic_glossy_gray_a01_tile_orm.png": solid((255, 102, 0)),
      "t_plastic_glossy_gray_a01_tile_nor.png": texel_tilts(0.2)}, {"tile_metres": 1.0},
     (solid((119,) * 3), solid((119,) * 3)), {"recipe": "plastic", "roughness": 0.464}),
    ("a flat ORM's chrome has no scratches", "T_Metal_Chrome_A",
     {"T_Metal_Chrome_A_Albedo_1.png": solid((119,) * 3), "T_Metal_Chrome_A_ORM_1.png": solid((255, 0, 255))},
     {"tile_metres": 1.0}, (solid((119,) * 3), solid((119,) * 3)), {"recipe": "polished_metal", "scratches": 0.0}),
    ("a scratched chrome's scratches by its roughness spread, raised by its missing detail", "T_Metal_Chrome_A",
     {"T_Metal_Chrome_A_Albedo_1.png": solid((119,) * 3), "T_Metal_Chrome_A_ORM_1.png": stripes(70, 80)},
     {"tile_metres": 1.0}, (stripes(109, 129), solid((119,) * 3)),
     {"recipe": "polished_metal", "scratches": 0.2614, "refined_scratches": 0.5228}),
]


@pytest.mark.parametrize("name, material, maps, surface, pictures, expected", ROWS, ids=[row[0] for row in ROWS])
def test_a_fitted_recipe_passes_only_when_it_looks_like_its_maps(tmp_path, name, material, maps, surface, pictures,
                                                                  expected):
    found = written(tmp_path, maps, surface)
    made = fit.fitted(material, found["maps"], found["tile_metres"], normal_convention=found["normal_convention"],
                      albedo_colour=found["albedo_colour"], constants=found["constants"],
                      emission_colour=found["emission_colour"])
    spec = made["recipe"]
    relief = (round(spec[fit.SIZE_SETTING[spec["recipe"]]], 4), round(spec["bump"], 3), round(made["tile_metres"], 4)) \
        if spec.get("bump") else None
    Image.fromarray(opaque(pictures[0])).save(tmp_path / "map.png")
    Image.fromarray(opaque(pictures[1])).save(tmp_path / "recipe.png")
    views = {"view": measure.view_measures(tmp_path / "map.png", tmp_path / "recipe.png")}
    verdict = measure.likeness(views, "algorithm/surface_recipes@1")
    earlier = pictures[2] if len(pictures) > 2 else None
    answer = {"recipe": spec["recipe"], "family_from": made["family_from"], "colour": round(np.mean(spec["colour"]), 4),
              "roughness": round(spec["roughness"], 3), "metal": round(spec["metal"], 3) if "metal" in spec else None,
              "relief": relief, "pass": verdict["pass"], "glow": (found["emission_colour"], "emission" in found["maps"]),
              "opacity": spec.get("opacity"), "refined_roughness": measure.refined(spec, views, earlier)["roughness"],
              "ranking": measure.ranking(views), "glow_strength": spec.get("glow"),
              "scratches": spec.get("scratches"), "refined_scratches": measure.refined(spec, views).get("scratches"),
              "heights": tuple(spec.get(setting) for setting in fit.RELIEF_SETTINGS), "refined_lab": lightness_hue(measure.refined(spec, views)["colour"])}
    assert {key: answer[key] for key in expected} == expected, name
