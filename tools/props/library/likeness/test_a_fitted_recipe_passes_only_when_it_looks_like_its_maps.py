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
- the tread plate row is the relief row's maps: its period along each axis is 16 texels, 0.016 m, its bump 0.004;
  beside a flat recipe the refinement would double it, but a quarter of its 0.016 pitch is 0.004;
- the rusty chrome's rust is 19 of 64 columns, a worn share of 0.2969: its bloom threshold 0.5 + 0.1 x 0.533 (the
  normal's 70.3rd percentile) = 0.5533, so its wear is (0.75 - 0.5533) / 0.3 = 0.6555;
- the smudged plastic's stripes are L 46.03 and 53.98: mean 50.0, dark shade 3.97 under it, spread 3.97, so its
  contrast wants 3.97 / (0.3 x 3.97) = 3.33: contrast 1 and a second shade 3.33 x 3.97 under the mean, L 36.8; its
  ORM green stripes spread 0.0196, a roughness spread of 0.0196 / 0.3 = 0.0654; beside a flat recipe (L 50.03, so
  the colours shift by -0.03) the refinement doubles the shades' gap at contrast 1: L 49.97 - 2 x 13.24 = 23.5;
- the disagreeing views' close detail 0.65 over the overview's 1.40 is 0.464, outside 0.8..1.25, so the cloth's
  0.012 thread is refined by that, within the refinement's step of 2 either way: 0.012 / 2 = 0.006;
- the constant colour row has no albedo map: its colour is its surface.json's constant diffuseColor, linear 0.1845;
- the glow rows are an emissive white: its constant emissiveColor (5, 5, 5) is carried as the map side's glow, unless
  an emission map feeds the glow (USD draws a connected input, never its constant): then the map, and no constant;
- the see-through rows' backdrop is squares of sRGB 0 and 255 (L 0 and 100): a pane showing the same squares shows
  all of it (1), a flat grey none (0); squares of sRGB 119 and 255 (L 49.97 and 100) half (0.5003): beside a flat
  recipe pane the recipe shows 0.4997 less, past the check's 0.08, and its opacity 0.8 is made that much clearer,
  0.3003; the clear plastic's glass passes all its light (weight 1, presence 1): opacity 0, its colour and roughness
  its transmission's (0.8, 0.02), not its constants';
- the opacity map is half 255 and half 64 (0.25), cut at 0.5: half its texels kept, so it stops 0.5 (blended, it
  would stop (1 + 0.251) / 2 = 0.6255);
- the ribs row's height is 2 sin(2 pi (x + 1/2) / 16) along x alone: its period 16 texels, 0.016 m at 0.064 m a
  tile, its slopes all across (anisotropy 1: ribs), half its texels over its middle (stud_share 0.5); the studs row
  is the same sine times its sine up the picture: a period of 16 both ways, a grid (periodic share 1 over 0.25), no
  way its slopes run (studs), half its texels raised, so a round stud sqrt(4 x 0.5 / pi) = 0.7979 of its pitch; at
  0.05 texels high its slopes' rms is about 0.05 x 2 pi / 16 / 2 = 0.01, under 0.02: no relief, a rubber;
- the strand board's flakes are the relief row's 0.012 m features (within 4 times its 0.02 default); the knit's
  stitch its 0.016 m period; the hammered plastic's features, 12 texels of a 0.32 m tile, 0.06 m, drawn at its
  dents' largest size 4 x 0.01 = 0.04;
- the printed check is lines of sRGB 60 (linear 0.0452, L 25.4, over 10 L off its ground's 50) 2 texels wide every
  16: a period of 0.016 m, an area of 1 - (14 / 16)^2 = 0.2344, so lines 0.016 x (1 - sqrt(1 - 0.2344)) = 0.002 wide;
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
- fit.family_of: the generic metal rule dropped (both plain "metal" rows polished_metal by their name), or
  generic_metal's relief test dropped (the ribbed one, polished by its roughness 0.098).
- fit.FAMILY_WORDS: gold ahead of fabric again (the oxford gold row polished_metal), without stone's words (the
  marble row plastic by its measures), or "floor_tile" after "marble" (the floor row rock).
- fit.spec_of: PERIODIC's period dropped (the tread plate's pitch the half-width feature, 0.012), or
  measure.refined's RELIEF_ASPECT cap dropped (its bump doubles to 0.008).
- fit.spec_of: the WORN_FAMILIES wear dropped (the rusty chrome drawn clean, no wear set).
- fit.spec_of: the darker second dropped (the smudged plastic's second L 46), or its roughness spread dropped
  (None: plastic's defaults without the setting), or measure.refined's second move dropped (its second L 36.8, the
  colours' shift alone).
- fit.relief_side: READ_SIDE always (the 2 m tile's chequer averaged away, its roughness widened to 0.464).
- measure.views_apart: None always (the disagreeing views' thread stays 0.012).
- measure.passes: `measured["delta_e"] <= DELTA_E_BOUND` -> `True` (the shifted colour passes).
Breaks of the see-through view and the new families (each applied once, seen red, reverted, 2026-11-23):
- measure.through_measures: the recipe's pane read as the maps' (the opaque glass row passes), or measure.breach's
  see-through share 0 (the same), or measure.refined's opacity step dropped (its opacity stays 0.8).
- fit.family_of: the see-through rule dropped (the clear plastic is plastic), fit.described's transmission colour
  and roughness dropped (its constants'), or see_through_of's transmission 0 (it stops all light: plastic).
- fit.opacity_of: the threshold ignored (the opacity map row stops 0.6255).
- fit.FAMILY_WORDS without "lined", "osb" or "blanket" (the ribs row rubber, the strand board grained wood, the
  knit cloth, "hammer" the hammered row plastic); fit.family_of's MOULDED rule dropped (the studs row rubber), or
  its relief test (the near flat rubber a mat).
- fit.studs: ribs always 0 (the ribs row studs), or a stud's share its area (the studs row 0.5); fit.period_of
  averaged evenly (the ribs row's pitch 0.04); fit.spec_of's check_print dropped (the printed cloth's check 0).
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


def rusty(columns):
    """A grey albedo (sRGB 150) with its first `columns` of SIDE columns rust (sRGB 90, 50, 30)."""
    picture = solid((150,) * 3)
    picture[:, :columns] = (90, 50, 30)
    return picture


def both_views(detail):
    """One view's measures with only its detail ratio off (its colour and highlight as the maps')."""
    return {"delta_e": 0.0, "lightness": 0.0, "highlight": 0.0, "detail": detail, "map_lab": [50.0, 0.0, 0.0],
            "recipe_lab": [50.0, 0.0, 0.0]}


def under(normal):
    """A normal map whose blue is turned under its surface (z negative), its red and green as they were."""
    turned = normal.copy()
    turned[..., 2] = 255 - turned[..., 2]
    return turned


def raised(amplitude, period, both):
    """A GL normal map of the height amplitude * sin(2 pi (x + 1/2) / period), times the same up the picture when
    `both` (studs; else ribs running up it), sampled half a texel off the sine's zeros so no texel stands level
    with its middle."""
    across, row = np.meshgrid(np.arange(SIDE) + 0.5, np.arange(SIDE) + 0.5)
    wave = 2 * np.pi / period
    up = SIDE - row
    rise = np.sin(wave * up) if both else np.ones_like(up)
    slope_across = amplitude * wave * np.cos(wave * across) * rise
    slope_up = amplitude * wave * np.sin(wave * across) * np.cos(wave * up) if both else np.zeros_like(up)
    normal = np.stack([-slope_across, -slope_up, np.ones_like(up)], -1)
    normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
    return np.round((normal + 1.0) * 127.5).astype(np.uint8)


def printed_grid(ground, ink, pitch, line):
    """A grey `ground` with `ink` lines `line` texels wide every `pitch` texels both ways: a printed check."""
    picture = solid((ground,) * 3)
    lined = np.arange(SIDE) % pitch < line
    picture[lined, :] = ink
    picture[:, lined] = ink
    return picture


def checker(light, dark=0, square=8):
    """Squares `square` texels across alternating sRGB `light` and `dark`: the see-through view's backdrop or a pane
    showing it."""
    across, row = np.meshgrid(np.arange(SIDE), np.arange(SIDE))
    lit = ((across // square + row // square) % 2 == 0)[..., None]
    return np.where(lit, np.uint8(light), np.uint8(dark)).repeat(3, axis=-1).astype(np.uint8)


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
     (stripes(109, 129), solid((119,) * 3), {"earlier": {"roughness": 0.5, "highlight": -2.0}}),
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
    ("a large tile's relief is read texel by texel, its slopes not averaged away", "t_plastic_glossy_gray_a01",
     {"t_plastic_glossy_gray_a01_tile_alb.png": solid((119,) * 3),
      "t_plastic_glossy_gray_a01_tile_orm.png": solid((255, 102, 0)),
      "t_plastic_glossy_gray_a01_tile_nor.png": texel_tilts(0.2)}, {"tile_metres": 2.0},
     (solid((119,) * 3), solid((119,) * 3)), {"recipe": "plastic", "roughness": 0.4}),
    ("a flat ORM's chrome has no scratches", "T_Metal_Chrome_A",
     {"T_Metal_Chrome_A_Albedo_1.png": solid((119,) * 3), "T_Metal_Chrome_A_ORM_1.png": solid((255, 0, 255))},
     {"tile_metres": 1.0}, (solid((119,) * 3), solid((119,) * 3)), {"recipe": "polished_metal", "scratches": 0.0}),
    ("a scratched chrome's scratches by its roughness spread, raised by its missing detail", "T_Metal_Chrome_A",
     {"T_Metal_Chrome_A_Albedo_1.png": solid((119,) * 3), "T_Metal_Chrome_A_ORM_1.png": stripes(70, 80)},
     {"tile_metres": 1.0}, (stripes(109, 129), solid((119,) * 3)),
     {"recipe": "polished_metal", "scratches": 0.2614, "refined_scratches": 0.5228}),
    ("a metal its name says no finish of, with relief: bare", "m_opaque_metal_yellow_clean_a01",
     {"albedo.png": solid((119,) * 3), "orm.png": solid((255, 25, 255)), "normal.png": bumps(2.0, 16)},
     {"maps": {"albedo": "albedo.png", "orm": "orm.png", "normal": "normal.png"}, "tile_metres": 0.064},
     (solid((119,) * 3), solid((119,) * 3)), {"recipe": "bare_metal", "family_from": "measures"}),
    ("a metal its name says no finish of, flat and rough: bare", "m_opaque_metal_plain_a01",
     {"albedo.png": solid((119,) * 3), "orm.png": solid((255, 153, 255)), "normal.png": solid(FLAT_NORMAL)},
     {"maps": {"albedo": "albedo.png", "orm": "orm.png", "normal": "normal.png"}, "tile_metres": 1.0},
     (solid((119,) * 3), solid((119,) * 3)), {"recipe": "bare_metal", "family_from": "measures"}),
    ("a cloth named gold is a cloth", "fabric_oxford_gold_t01", {"albedo.png": solid((119,) * 3)},
     {"maps": {"albedo": "albedo.png"}, "tile_metres": 1.0}, (solid((119,) * 3), solid((119,) * 3)),
     {"recipe": "cloth", "family_from": "name"}),
    ("a marble is a stone", "stone_marble_veined_glossy_a03", {"albedo.png": solid((119,) * 3)},
     {"maps": {"albedo": "albedo.png"}, "tile_metres": 1.0}, (solid((119,) * 3), solid((119,) * 3)),
     {"recipe": "rock", "family_from": "name"}),
    ("a marble floor's tiles", "simready_opaque_stone_marble_floor_tile_a", {"albedo.png": solid((119,) * 3)},
     {"maps": {"albedo": "albedo.png"}, "tile_metres": 1.0}, (solid((119,) * 3), solid((119,) * 3)),
     {"recipe": "tiles", "family_from": "name"}),
    ("a tread plate's pitch is its relief's period, its bump grown no higher than a quarter of it",
     "m_opaque_metal_treadplate_rough_a01",
     {"albedo.png": solid((119,) * 3), "orm.png": solid((255, 102, 255)), "normal.png": bumps(2.0, 16)},
     {"maps": {"albedo": "albedo.png", "orm": "orm.png", "normal": "normal.png"}, "tile_metres": 0.064},
     (stripes(109, 129), solid((119,) * 3)),
     {"recipe": "chequer_plate", "relief": (0.016, 0.004, 0.064), "refined_bump": 0.004}),
    ("views that disagree on detail: a finer pattern", "fabric_cotton_black_q01",
     {"albedo.png": solid((119,) * 3), "normal.png": bumps(2.0, 16)},
     {"maps": {"albedo": "albedo.png", "normal": "normal.png"}, "tile_metres": 0.064},
     (solid((119,) * 3), solid((119,) * 3), {"views": {"overview": both_views(1.40), "close": both_views(0.65)}}),
     {"recipe": "cloth", "relief": (0.012, 0.004, 0.064), "refined_size": 0.006}),
    ("a rusty chrome's rust is its wear", "m_opaque_metal_chrome_rusty_a01",
     {"albedo.png": rusty(19), "orm.png": solid((255, 102, 255))},
     {"maps": {"albedo": "albedo.png", "orm": "orm.png"}, "tile_metres": 1.0},
     (solid((119,) * 3), solid((119,) * 3)), {"recipe": "rusted_metal", "wear": 0.6555}),
    ("a smudged plastic: mottled past contrast 1 by a darker second, its roughness spread", "plastic_black_dirty_c01",
     {"albedo.png": stripes(109, 129), "orm.png": stripes(70, 80)},
     {"maps": {"albedo": "albedo.png", "orm": "orm.png"}, "tile_metres": 1.0}, (stripes(109, 129), solid((119,) * 3)),
     {"recipe": "plastic", "contrast": 1.0, "second_lightness": 36.8, "roughness_spread": 0.0654,
      "refined_second_lightness": 23.5}),
    ("a clear plastic's glass: see-through, its look its transmission's colour and roughness",
     "m_trans_plastic_clear_a01", {},
     {"maps": {}, "tile_metres": 1.0, "constants": {"diffuseColor": [0.1845] * 3, "roughness": 0.4, "opacity": 1.0},
      "transmission": {"weight": 1.0, "presence": 1.0, "colour": [0.8] * 3, "roughness": 0.02}},
     (solid((119,) * 3), solid((119,) * 3), {"through": (checker(255), checker(255), checker(255))}),
     {"recipe": "glass", "family_from": "measures", "colour": 0.8, "roughness": 0.02, "opacity": 0.0,
      "see_through": 0.0, "pass": True}),
    ("a glass's recipe more opaque than its maps' pane fails, and is made as much clearer", "m_trans_glass_black_a01",
     {}, {"maps": {}, "tile_metres": 1.0, "constants": {"diffuseColor": [0.1845] * 3, "roughness": 0.27,
                                                        "opacity": 0.8}},
     (solid((119,) * 3), solid((119,) * 3), {"through": (checker(255), checker(255, 119), solid((119,) * 3))}),
     {"recipe": "glass", "opacity": 0.8, "see_through": -0.4997, "pass": False, "refined_opacity": 0.3003}),
    ("an opacity map cut at its threshold: what it stops", "m_opaque_plastic_leaf_a01",
     {"albedo.png": solid((119,) * 3),
      "opacity.png": np.concatenate([solid((255,) * 3)[:, :32], solid((64,) * 3)[:, 32:]], 1)},
     {"maps": {"albedo": "albedo.png", "opacity": "opacity.png"}, "tile_metres": 1.0,
      "opacity": {"constant": 1.0, "threshold": 0.5}}, (solid((119,) * 3), solid((119,) * 3)),
     {"recipe": "glass", "family_from": "measures", "opacity": 0.5}),
    ("a lined rubber is a ribbed mat, its pitch the ribs' period", "m_opaque_rubber_lined_black_a01",
     {"albedo.png": solid((119,) * 3), "normal.png": raised(2.0, 16, False)},
     {"maps": {"albedo": "albedo.png", "normal": "normal.png"}, "tile_metres": 0.064},
     (solid((119,) * 3), solid((119,) * 3)),
     {"recipe": "mat", "family_from": "name", "size": 0.016, "ribs": 1.0, "stud_share": 0.5}),
    ("a rubber whose relief is a grid of studs is a mat", "m_opaque_rubber_black_a01",
     {"albedo.png": solid((119,) * 3), "normal.png": raised(2.0, 16, True)},
     {"maps": {"albedo": "albedo.png", "normal": "normal.png"}, "tile_metres": 0.064},
     (solid((119,) * 3), solid((119,) * 3)),
     {"recipe": "mat", "family_from": "measures", "size": 0.016, "ribs": 0.0, "stud_share": 0.7979}),
    ("a near flat rubber's faint repeat is no mat", "m_opaque_rubber_glossy_black_a01",
     {"albedo.png": solid((119,) * 3), "normal.png": raised(0.05, 16, True)},
     {"maps": {"albedo": "albedo.png", "normal": "normal.png"}, "tile_metres": 0.064},
     (solid((119,) * 3), solid((119,) * 3)), {"recipe": "rubber", "family_from": "name"}),
    ("an oriented strand board's flakes", "m_opaque_wood_osb_cleans_a01",
     {"albedo.png": solid((119,) * 3), "normal.png": bumps(2.0, 16)},
     {"maps": {"albedo": "albedo.png", "normal": "normal.png"}, "tile_metres": 0.064},
     (solid((119,) * 3), solid((119,) * 3)), {"recipe": "strand_board", "family_from": "name", "size": 0.012}),
    ("a blanket's knit, its stitch its relief's period", "opaque_fabric_blanket_blue_a",
     {"albedo.png": solid((119,) * 3), "normal.png": bumps(2.0, 16)},
     {"maps": {"albedo": "albedo.png", "normal": "normal.png"}, "tile_metres": 0.064},
     (solid((119,) * 3), solid((119,) * 3)), {"recipe": "knit", "family_from": "name", "size": 0.016}),
    ("a hammered plastic's dents, at their largest size", "m_opaque_plastic_hammered_black_a01",
     {"albedo.png": solid((119,) * 3), "normal.png": bumps(2.0, 16)},
     {"maps": {"albedo": "albedo.png", "normal": "normal.png"}, "tile_metres": 0.32},
     (solid((119,) * 3), solid((119,) * 3)), {"recipe": "hammered", "family_from": "name", "size": 0.04}),
    ("a cloth's printed check: lines at the print's period, as wide as its area, in its colour",
     "m_opaque_fabric_body_b01", {"albedo.png": printed_grid(119, 60, 16, 2)},
     {"maps": {"albedo": "albedo.png"}, "tile_metres": 0.064}, (solid((119,) * 3), solid((119,) * 3)),
     {"recipe": "cloth", "check": 1.0, "check_pitch": 0.016, "check_line": 0.002, "print_colour": 0.0452}),
    ("a plain cloth has no check", "fabric_cotton_black_q01", {"albedo.png": solid((119,) * 3)},
     {"maps": {"albedo": "albedo.png"}, "tile_metres": 0.064}, (solid((119,) * 3), solid((119,) * 3)),
     {"recipe": "cloth", "check": 0.0}),
]


@pytest.mark.parametrize("name, material, maps, surface, pictures, expected", ROWS, ids=[row[0] for row in ROWS])
def test_a_fitted_recipe_passes_only_when_it_looks_like_its_maps(tmp_path, name, material, maps, surface, pictures,
                                                                  expected):
    found = written(tmp_path, maps, surface)
    made = fit.fitted(material, found["maps"], found["tile_metres"], normal_convention=found["normal_convention"],
                      albedo_colour=found["albedo_colour"], constants=found["constants"],
                      emission_colour=found["emission_colour"], see_through=found["see_through"])
    spec = made["recipe"]
    relief = (round(spec[fit.SIZE_SETTING[spec["recipe"]]], 4), round(spec["bump"], 3), round(made["tile_metres"], 4)) \
        if spec.get("bump") else None
    Image.fromarray(opaque(pictures[0])).save(tmp_path / "map.png")
    Image.fromarray(opaque(pictures[1])).save(tmp_path / "recipe.png")
    views = {"view": measure.view_measures(tmp_path / "map.png", tmp_path / "recipe.png")}
    extra = pictures[2] if len(pictures) > 2 else {}
    if "through" in extra:
        for side, pixels in zip(("backdrop", "map-through", "recipe-through"), extra["through"]):
            Image.fromarray(opaque(pixels)).save(tmp_path / f"{side}.png")
        views["through"] = measure.through_measures(tmp_path / "map-through.png", tmp_path / "recipe-through.png",
                                                    tmp_path / "backdrop.png")
    verdict = measure.likeness(views, "algorithm/surface_recipes@1")
    earlier = extra.get("earlier")
    answer = {"recipe": spec["recipe"], "family_from": made["family_from"], "colour": round(np.mean(spec["colour"]), 4),
              "roughness": round(spec["roughness"], 3), "metal": round(spec["metal"], 3) if "metal" in spec else None,
              "relief": relief, "pass": verdict["pass"], "glow": (found["emission_colour"], "emission" in found["maps"]),
              "opacity": spec.get("opacity"), "refined_roughness": measure.refined(spec, views, earlier)["roughness"],
              "ranking": measure.ranking(views), "glow_strength": spec.get("glow"),
              "scratches": spec.get("scratches"), "wear": spec.get("wear"), "contrast": spec.get("contrast"),
              "roughness_spread": spec.get("roughness_spread"),
              "second_lightness": round(float(colour.lab(np.asarray(spec["second"]))[0]), 1),
              "refined_second_lightness": round(float(colour.lab(np.asarray(
                  measure.refined(spec, views)["second"]))[0]), 1), "refined_bump": measure.refined(spec, views).get("bump"), "refined_scratches": measure.refined(spec, views).get("scratches"),
              "refined_size": measure.refined(spec, extra.get("views", views)).get(
                  fit.SIZE_SETTING.get(spec["recipe"], "")),
              "heights": tuple(spec.get(setting) for setting in fit.RELIEF_SETTINGS),
              "refined_lab": lightness_hue(measure.refined(spec, views)["colour"]),
              "see_through": views.get("through", {}).get("see_through"),
              "refined_opacity": measure.refined(spec, views, earlier).get("opacity"),
              "size": round(spec[fit.SIZE_SETTING[spec["recipe"]]], 4) if spec["recipe"] in fit.SIZE_SETTING else None,
              "ribs": spec.get("ribs"), "stud_share": spec.get("stud_share"), "check": spec.get("check"),
              "check_pitch": spec.get("check_pitch"), "check_line": spec.get("check_line"),
              "print_colour": round(float(np.mean(spec["print_colour"])), 4) if "print_colour" in spec else None}
    assert {key: answer[key] for key in expected} == expected, name
