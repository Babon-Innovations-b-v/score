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
- the constant colour row has no albedo map: its colour is its surface.json's constant diffuseColor, linear 0.1845;
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


def opaque(pixels):
    """An RGB picture as a fully covered RGBA render."""
    return np.concatenate([pixels, np.full((SIDE, SIDE, 1), 255, dtype=np.uint8)], -1)


ROWS = [
    ("plastic, the same look", "t_plastic_glossy_gray_a01",
     {"t_plastic_glossy_gray_a01_tile_alb.png": solid((119,) * 3),
      "t_plastic_glossy_gray_a01_tile_orm.png": solid((255, 102, 0)),
      "t_plastic_glossy_gray_a01_tile_nor.png": solid(FLAT_NORMAL)}, {"tile_metres": 1.0},
     (solid((119,) * 3), solid((119,) * 3)),
     ("plastic", "name", 0.1845, 0.4, None, None, True)),
    ("chrome by its name, older file names", "T_Metal_Chrome_A",
     {"T_Metal_Chrome_A_Albedo_1.png": solid((119,) * 3), "T_Metal_Chrome_A_ORM_1.png": solid((255, 102, 255)),
      "T_Metal_Chrome_A_Normal_1.png": solid(FLAT_NORMAL)}, {"tile_metres": 1.0},
     (solid((119,) * 3), solid((119,) * 3)),
     ("polished_metal", "name", 0.1845, 0.4, 1.0, None, True)),
    ("metal by its measures, a colour shifted", "t_unnamed_a01",
     {"t_unnamed_a01_tile_alb.png": solid((119,) * 3), "t_unnamed_a01_tile_orm.png": solid((255, 25, 230))}, {"tile_metres": 1.0},
     (solid((119,) * 3), solid((150, 104, 112))),
     ("polished_metal", "measures", 0.1845, 0.098, 0.902, None, False)),
    ("concrete relief, a flat recipe beside detail", "t_concrete_bare_a01",
     {"colour.jpg": solid((119,) * 3), "roughness.png": solid((102,) * 3), "normal.png": bumps(2.0, 16)},
     {"tile_metres": 0.064}, (stripes(109, 129), solid((119,) * 3)),
     ("concrete", "name", 0.1845, 0.4, None, (0.012, 0.004, 0.064), False)),
    ("an adopted set's relief, maps by role, DirectX, tile fitted", "t_concrete_bare_a01",
     {"albedo.png": solid((119,) * 3), "roughness.png": solid((102,) * 3), "normal.png": directx(bumps(2.0, 16))},
     {"maps": {"albedo": "albedo.png", "roughness": "roughness.png", "normal": "normal.png"}, "tile_metres": None,
      "normal_convention": "directx"}, (stripes(109, 129), solid((119,) * 3)),
     ("concrete", "name", 0.1845, 0.4, None, (0.01, 0.003, 0.0533), False)),
    ("plastic relief over its largest grain, the bump at its slope", "t_plastic_rough_black_a01",
     {"t_plastic_rough_black_a01_tile_alb.png": solid((119,) * 3),
      "t_plastic_rough_black_a01_tile_orm.png": solid((255, 102, 0)),
      "t_plastic_rough_black_a01_tile_nor.png": bumps(2.0, 16)}, {"tile_metres": 0.064},
     (solid((119,) * 3), solid((119,) * 3)),
     ("plastic", "name", 0.1845, 0.4, None, (0.008, 0.003, 0.064), True)),
    ("a constant colour, no albedo map", "m_opaque_metal_chrome_a01",
     {"normal.png": solid(FLAT_NORMAL), "orm.png": solid((255, 102, 255))},
     {"maps": {"normal": "normal.png", "orm": "orm.png"}, "tile_metres": 1.0,
      "constants": {"diffuseColor": [0.1845, 0.1845, 0.1845]}}, (solid((119,) * 3), solid((119,) * 3)),
     ("polished_metal", "name", 0.1845, 0.4, 1.0, None, True)),
]


@pytest.mark.parametrize("name, material, maps, surface, pictures, expected", ROWS, ids=[row[0] for row in ROWS])
def test_a_fitted_recipe_passes_only_when_it_looks_like_its_maps(tmp_path, name, material, maps, surface, pictures,
                                                                  expected):
    found = written(tmp_path, maps, surface)
    made = fit.fitted(material, found["maps"], found["tile_metres"], normal_convention=found["normal_convention"],
                      albedo_colour=found["albedo_colour"])
    spec = made["recipe"]
    relief = (round(spec[fit.SIZE_SETTING[spec["recipe"]]], 4), round(spec["bump"], 3), round(made["tile_metres"], 4)) \
        if spec.get("bump") else None
    Image.fromarray(opaque(pictures[0])).save(tmp_path / "map.png")
    Image.fromarray(opaque(pictures[1])).save(tmp_path / "recipe.png")
    verdict = measure.likeness({"view": measure.view_measures(tmp_path / "map.png", tmp_path / "recipe.png")},
                               "algorithm/surface_recipes@1")
    answer = (spec["recipe"], made["family_from"], round(np.mean(spec["colour"]), 4), round(spec["roughness"], 3),
              round(spec["metal"], 3) if "metal" in spec else None, relief, verdict["pass"])
    assert answer == expected, name
