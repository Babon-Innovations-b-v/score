"""The recipe fitted to a surface's maps from their statistics alone, no rendering (#155): which recipe family draws
it, and that recipe's settings, as the start the look-alike check (check.py) renders and refines.

    roles(names)                     {role: map file}: albedo, normal, orm, roughness, metal
    described(surface, names)        a surface.json's maps {role: file}, tile size, normal convention and constant
                                     colour
    statistics(maps, tile_metres)    the maps' measures (a constant colour in place of an albedo map)
    family_of(name, measured)        the recipe family that draws the material
    spec_of(family, measured)        the recipe's spec (recipes.channels' form), colours linear
    fitted(name, maps, tile_metres)  {"recipe": spec, "statistics", "family_from": "name" | "measures",
                                      "tile_metres", "tile_metres_from"}

The measures: the albedo's mean colour in CIE Lab, the mean of its darkest fifth (a pattern's second shade) and the
spread of its lightness; the roughness and metal means (an ORM map's green and blue, or their own maps); the normal
map's relief, its slopes integrated to a height field and high-passed, as its height spread and the size of its
features in metres (from the map's width and `tile_metres`, the
metres one repeat of the maps covers). A DirectX normal map (its green pointing down the picture) has its green
turned over first. A tile size the surface does not know (None) is fitted as a free setting: the size at which the
relief's features are its family's default pattern size, else TILE_METRES, said as assumed. Colours come from the maps, as a surface of an adopted set holds them; a
recipe's palette colours are a scene's, which this fit does not touch. Standard library and numpy (Pillow to read).
"""
import json
import pathlib
import re

import numpy as np

import colour

HERE = pathlib.Path(__file__).resolve().parent
METHOD = HERE.parents[3] / "data/library/materials.json"
# A map's role by the last word of its file name (a trailing number dropped): t_<material>_tile_alb.png,
# T_<Material>_Albedo_1.png, colour.jpg.
ROLE_WORDS = {"albedo": ("alb", "albedo", "basecolor", "basecolour", "color", "colour", "diffuse", "diff"),
              "normal": ("nor", "normal", "normalgl", "nrm"),
              "orm": ("orm",),
              "roughness": ("rou", "rough", "roughness"),
              "metal": ("met", "metal", "metallic", "metalness"),
              "emission": ("emission", "emissive", "emit")}
# The recipe family a material's name says, first match wins (so fibreglass before glass and plastic, painted metal
# before metal, stainless before polished): words of a finish, never of a maker.
FAMILY_WORDS = (("fiberglass", "fiberglass"), ("fibreglass", "fiberglass"), ("emissive", "glowing"),
                ("mirror", "polished_metal"), ("glass", "glass"), ("lens", "glass"), ("treadplate", "chequer_plate"),
                ("diamondplate", "chequer_plate"), ("galvan", "galvanized"),
                ("rust", "rusted_metal"), ("anodiz", "anodized"), ("painted", "painted_metal"),
                ("enamel", "painted_metal"), ("perforat", "perforated_metal"), ("cast", "cast_metal"),
                ("brushed", "bare_metal"), ("stainless", "bare_metal"), ("aluminium", "bare_metal"),
                ("aluminum", "bare_metal"), ("steel", "bare_metal"), ("chrome", "polished_metal"),
                ("polished", "polished_metal"), ("gold", "polished_metal"), ("bronze", "polished_metal"),
                ("copper", "polished_metal"), ("metal", "polished_metal"), ("carbon", "composite"),
                ("rubber", "rubber"), ("ruberoid", "rubber"),
                ("leather", "leather"), ("ceramic", "ceramic"), ("porcelain", "ceramic"), ("plywood", "grained_wood"),
                ("wood", "grained_wood"), ("oak", "grained_wood"), ("cardboard", "cardboard"),
                ("corrugated", "cardboard"), ("box", "cardboard"), ("concrete", "concrete"), ("cement", "concrete"),
                ("fabric", "cloth"), ("tweed", "cloth"), ("cloth", "cloth"), ("rope", "cloth"),
                ("plastic", "plastic"), ("polyurethane", "plastic"), ("nylon", "plastic"), ("foam", "plastic"))
# With no family word: metal over this mean is metal, polished under ROUGH_POLISHED roughness; else plastic.
METAL_MEAN = 0.5
ROUGH_POLISHED = 0.25
# The pattern size setting each family takes the normal map's feature size into (none: the family has no size).
SIZE_SETTING = {"plastic": "grain_size", "leather": "grain_size", "concrete": "pore_size", "cardboard": "fibre_size",
                "fiberglass": "fibre_size", "ceramic": "bump_size", "grained_wood": "ring_pitch",
                "bare_metal": "bump_size", "anodized": "bump_size", "cast_metal": "bump_size", "rubber": "bump_size",
                "painted_metal": "bump_size", "wood": "bump_size", "cloth": "thread", "composite": "weave",
                "chequer_plate": "pitch", "perforated_metal": "pitch", "galvanized": "cell_size"}
# A pattern size the fit sets stays within this factor of its family's default either way: a tile's slow swell
# read as its feature (concrete's 30 cm) is not its pores.
SIZE_RANGE = 4.0
# The darkest share of the albedo whose mean is a pattern's second shade.
DARK_SHARE = 0.2
# Maps are read averaged down to this many texels across: the swatch's pictures show nothing finer.
READ_SIDE = 512
# The high-pass's reach, a share of the map's width: relief wider than it is a tile's slow swell, not its relief.
HIGH_PASS_SHARE = 1.0 / 8.0
# A recipe's bump from the relief's height spread: its relief (noise - 0.5) * bump or a pattern * bump spreads about
# a quarter of the bump; the check refines it.
BUMP_PER_HEIGHT = 4.0
# A pattern's size setting (a noise's 1 / scale, a grid's pitch) from its autocorrelation's half width: a quarter
# wave of a periodic pattern, about a quarter of a noise's feature.
FEATURE_PER_HALF_WIDTH = 4.0
# A normal's z kept off zero so a grazing texel does not read as an infinite slope.
FLAT_FLOOR = 0.05
# Where the autocorrelation falls to half: a feature's half width.
HALF = 0.5
# The tile size said as assumed when the surface names none and the maps cannot fit one (no relief or no pattern size).
TILE_METRES = 1.0
NORMAL_CONVENTIONS = ("opengl", "directx")
# A finish's roughness when neither a map nor its surface.json's constants say it: USD's UsdPreviewSurface default,
# which the map side draws too (inside/likeness.py), so both sides start from one roughness.
UNSAID_ROUGHNESS = 0.5
# A surface.json's constants the fit reads beside its colours: {constant name: the measure it stands in for}.
CONSTANT_MEASURES = {"roughness": "roughness", "metallic": "metal", "opacity": "opacity"}
ROLE_ALIASES = {"metallic": "metal"}  # a surface.json's role names (the USD input's) as this fit's
# A surface.json's packed roles, one file holding two: {role: (the colour role, the role its alpha holds)}.
PACKED_ROLES = {"albedo_roughness": ("albedo", "roughness_alpha")}
# A pattern's contrast from the lightness spread: a mix toward the second shade by contrast * pattern (pattern's
# spread about 0.3) spreads lightness by contrast * 0.3 * the shades' lightness apart.
PATTERN_SPREAD = 0.3


def role_of(name):
    """A map file's role from its name's last word, or None."""
    words = [word for word in re.split(r"[_\-. ]+", pathlib.Path(name).stem.lower()) if word]
    while words and words[-1].isdigit():
        words.pop()
    last = words[-1] if words else ""
    return next((role for role, said in ROLE_WORDS.items() if last in said), None)


def roles(names):
    """{role: file name} for the map files among `names`; the first file of a role wins."""
    found = {}
    for name in names:
        role = role_of(name)
        if role and role not in found:
            found[role] = name
    return found


def described(surface, names):
    """A surface.json's (`surface`, {} for none) maps {role: file name} (its `maps` dict as written, else the entry's
    texture files `names` by their roles), its tile metres ("surface.json"; None when it says it does not know, so
    `fitted` fits it, from None; TILE_METRES "assumed" when it says nothing), its normal convention ("opengl" unless it says
    "directx"), with no albedo map its constant colour (its `constants` diffuseColor, linear as USD holds it; else
    None) and, with no emission map, its constant glow (its `constants` emissiveColor, linear, its intensity in its
    size as USD holds it: (5, 5, 5) is white given off five times over; else None), and its constant roughness,
    metal and opacity (CONSTANT_MEASURES, {measure: value}, only those it writes; a map of the same measure stands
    over its constant in `statistics`):
    {"maps", "tile_metres", "tile_metres_from", "normal_convention", "albedo_colour", "emission_colour",
    "constants"}."""
    maps = surface.get("maps") or {}
    if not isinstance(maps, dict):
        raise ValueError(f"surface.json maps is {type(maps).__name__}, not {{role: file}}")
    convention = surface.get("normal_convention") or "opengl"
    if convention not in NORMAL_CONVENTIONS:
        raise ValueError(f"surface.json normal_convention {convention!r}, not one of {NORMAL_CONVENTIONS}")
    if "tile_metres" not in surface:
        tile = (TILE_METRES, "assumed")
    else:
        tile = (surface["tile_metres"], "surface.json" if surface["tile_metres"] is not None else None)
    found = {ROLE_ALIASES.get(role, role): name for role, name in maps.items()} or roles(names)
    for packed, (colour_role, alpha_role) in PACKED_ROLES.items():
        if packed in found:
            name = found.pop(packed)
            found.setdefault(colour_role, name)
            found.setdefault(alpha_role, name)
    constants = surface.get("constants") or {}
    constant = None if "albedo" in found else constants.get("diffuseColor")
    glow = None if "emission" in found else constants.get("emissiveColor")
    return {"maps": found, "tile_metres": tile[0], "tile_metres_from": tile[1], "normal_convention": convention,
            "albedo_colour": None if constant is None else [float(value) for value in constant],
            "emission_colour": None if glow is None else [float(value) for value in glow],
            "constants": {measure: float(constants[name]) for name, measure in CONSTANT_MEASURES.items()
                          if constants.get(name) is not None}}


def pixels(path):
    """A picture's RGB as 0..1 floats."""
    from PIL import Image
    with Image.open(path) as opened:
        return np.asarray(opened.convert("RGB"), dtype=float) / 255.0


def shrunk(values, side):
    """A picture averaged down in whole blocks to at most `side` texels across (a tile's statistics, read fast)."""
    step = max(1, -(-values.shape[1] // side))
    rows, columns = values.shape[0] // step * step, values.shape[1] // step * step
    cut = values[:rows, :columns]
    return cut.reshape(rows // step, step, columns // step, step, *values.shape[2:]).mean(axis=(1, 3))


def frequencies(shape):
    """The FFT's frequencies (cycles a texel) down and across, as two broadcastable arrays."""
    return np.fft.fftfreq(shape[0])[:, None], np.fft.fftfreq(shape[1])[None, :]


def height_of(normal):
    """The height field (texels) a tangent-space normal map's slopes integrate to, wrapped round as a tile repeats
    (Frankot and Chellappa's projection, 1988), its mean zero."""
    tilt = np.maximum(normal[..., 2], FLAT_FLOOR)
    down, across = frequencies(normal.shape[:2])
    slope_across = np.fft.fft2(-normal[..., 0] / tilt)
    slope_down = np.fft.fft2(normal[..., 1] / tilt)
    squared = (2 * np.pi) ** 2 * (across ** 2 + down ** 2)
    squared[0, 0] = 1.0
    spectrum = (-1j * 2 * np.pi * across * slope_across - 1j * 2 * np.pi * down * slope_down) / squared
    spectrum[0, 0] = 0.0
    return np.real(np.fft.ifft2(spectrum))


def high_passed(field, reach_share):
    """The field less its features wider than `reach_share` of its width (a gaussian low pass taken out)."""
    down, across = frequencies(field.shape)
    width = reach_share * field.shape[1]
    low = np.exp(-2 * (np.pi * width) ** 2 * (across ** 2 + down ** 2))
    return np.real(np.fft.ifft2(np.fft.fft2(field) * (1.0 - low)))


def half_width(field):
    """The lag in texels at which the field's wrapped autocorrelation, averaged across and down, falls to HALF."""
    spectrum = np.abs(np.fft.fft2(field - field.mean())) ** 2
    correlation = np.real(np.fft.ifft2(spectrum))
    if correlation[0, 0] <= 0:
        return float(min(field.shape))
    correlation = correlation / correlation[0, 0]
    lags = []
    for line in (correlation[0, : field.shape[1] // 2], correlation[: field.shape[0] // 2, 0]):
        below = np.nonzero(line < HALF)[0]
        lags.append(float(below[0]) if below.size else float(line.size))
    return float(np.mean(lags))


def albedo_statistics(path):
    """The albedo's mean Lab, the mean Lab of its darkest DARK_SHARE and its lightness spread."""
    values = colour.lab(colour.linear(shrunk(pixels(path), READ_SIDE))).reshape(-1, 3)
    order = np.argsort(values[:, 0])
    dark = values[order[: max(1, int(len(order) * DARK_SHARE))]]
    return {"lab": values.mean(axis=0).tolist(), "dark_lab": dark.mean(axis=0).tolist(),
            "lightness_spread": float(values[:, 0].std())}


def constant_statistics(linear_colour):
    """A constant colour's albedo_statistics: its Lab as the mean and the dark shade, no spread."""
    lab = colour.lab(np.asarray(linear_colour, dtype=float)).tolist()
    return {"lab": lab, "dark_lab": lab, "lightness_spread": 0.0}


def relief_statistics(path, tile_metres, normal_convention="opengl"):
    """The normal map's relief: its height field's high-passed spread (rms, metres) and its features' size in metres
    (FEATURE_PER_HALF_WIDTH half widths of its autocorrelation); a DirectX map's green turned over to OpenGL's."""
    normal = shrunk(pixels(path), READ_SIDE) * 2.0 - 1.0
    if normal_convention == "directx":
        normal[..., 1] = -normal[..., 1]
    metres_a_texel = tile_metres / normal.shape[1]
    relief = high_passed(height_of(normal), HIGH_PASS_SHARE)
    return {"height": float(relief.std() * metres_a_texel),
            "feature_metres": float(half_width(relief) * FEATURE_PER_HALF_WIDTH * metres_a_texel)}


def channel_mean(path, channel):
    """A data map's mean in one channel (0 red, 1 green, 2 blue), its values as stored, never colour managed."""
    return float(shrunk(pixels(path), READ_SIDE)[..., channel].mean())


def alpha_mean(path):
    """A picture's alpha mean, as stored (a packed map's second measure, its roughness)."""
    from PIL import Image
    with Image.open(path) as opened:
        return float(shrunk(np.asarray(opened.convert("RGBA"), dtype=float)[..., 3] / 255.0, READ_SIDE).mean())


def statistics(maps, tile_metres, normal_convention="opengl", albedo_colour=None, constants=None,
               emission_colour=None):
    """The maps' measures from {role: path}: the albedo map, else the constant `albedo_colour` (linear); normal, orm
    or roughness (or a packed albedo's alpha, `roughness_alpha`) and metal when given, else their surface.json `constants` ({measure: value}, described), else a
    roughness of UNSAID_ROUGHNESS and a metal of 0, as the map side draws them; the constant opacity (None when
    unsaid); its glow, the strength it gives off light at (an emission map's 1, else the constant `emission_colour`'s
    strongest channel, else 0) and that constant's hue (its channels over the strongest)."""
    constants = constants or {}
    measured = albedo_statistics(maps["albedo"]) if "albedo" in maps else constant_statistics(albedo_colour)
    measured["tile_metres"] = float(tile_metres)
    measured.update(relief_statistics(maps["normal"], tile_metres, normal_convention) if "normal" in maps else
                    {"height": 0.0, "feature_metres": None})
    if "orm" in maps:
        measured["roughness"], measured["metal"] = channel_mean(maps["orm"], 1), channel_mean(maps["orm"], 2)
    else:
        if "roughness" in maps:
            measured["roughness"] = channel_mean(maps["roughness"], 0)
        elif "roughness_alpha" in maps:
            measured["roughness"] = alpha_mean(maps["roughness_alpha"])
        else:
            measured["roughness"] = constants.get("roughness", UNSAID_ROUGHNESS)
        measured["metal"] = channel_mean(maps["metal"], 0) if "metal" in maps else constants.get("metal", 0.0)
    measured["opacity"] = constants.get("opacity")
    strongest = max(emission_colour or [0.0])
    measured["glow"] = 1.0 if "emission" in maps else float(max(strongest, 0.0))
    measured["glow_hue"] = ([float(value) / strongest for value in emission_colour]
                            if "emission" not in maps and strongest > 0 else None)
    return measured


# Families drawn with no metal, whose name word a measured metal overrules (a metal-coated glass is a metal).
UNMETALLED = ("glass",)


def metal_by_roughness(measured):
    """A metal's family by its roughness: polished under ROUGH_POLISHED, else bare."""
    return "polished_metal" if measured["roughness"] < ROUGH_POLISHED else "bare_metal"


def family_of(name, measured):
    """The recipe family a material's name says (FAMILY_WORDS; a family drawn with no metal, UNMETALLED, yields to a
    metal over METAL_MEAN, which the map side draws as metal), else by its metal and roughness means: (family,
    "name" | "measures"). A surface that gives off light is glowing whatever its name (a glass lamp lens fitted as
    glass drew no light beside its map side's glow)."""
    lowered = name.lower()
    said = next((family for word, family in FAMILY_WORDS if word in lowered), None)
    if measured.get("glow", 0.0) > 0 and said != "glowing":
        return "glowing", "measures"
    for word, family in FAMILY_WORDS:
        if word in lowered:
            if family in UNMETALLED and measured["metal"] > METAL_MEAN:
                return metal_by_roughness(measured), "measures"
            return family, "name"
    if measured["metal"] > METAL_MEAN:
        return metal_by_roughness(measured), "measures"
    return "plastic", "measures"


def linear_colour(values):
    """A Lab colour as the recipe's linear RGB list."""
    return [round(float(value), 5) for value in colour.linear_of_lab(np.asarray(values))]


def spec_of(family, measured, method=METHOD):
    """The family's recipe spec from the measures: its default settings (the method's), the albedo's colours (colour,
    and second, bare and dirt_colour as the dark shade), roughness and metal from their maps, the pattern size from
    the relief's features (within SIZE_RANGE of the family's default), the bump from its height spread (scaled with a
    clamped pattern size, so the recipe's relief keeps the maps' slope: a tile's 30 cm swell drawn at 8 mm grain at its
    full height is a field of steep bumps that scatters the highlight away) and the contrast from the lightness
    spread; a constant opacity where the family has one (glass)."""
    defaults = json.loads(pathlib.Path(method).read_text())["recipes"][family]
    spec = {"recipe": family, **defaults, "colour": linear_colour(measured["lab"])}
    dark = linear_colour(measured["dark_lab"])
    spec.update(second=dark, bare=dark, dirt_colour=dark)
    spec["roughness"] = round(measured["roughness"], 4)
    if "metal" in defaults:
        spec["metal"] = round(measured["metal"], 4)
    if "opacity" in defaults and measured.get("opacity") is not None:
        spec["opacity"] = round(measured["opacity"], 4)
    if "glow" in defaults and measured.get("glow"):
        spec["glow"] = round(measured["glow"], 4)
        if measured.get("glow_hue"):
            spec["colour"] = [round(value, 5) for value in measured["glow_hue"]]
    size_setting = SIZE_SETTING.get(family)
    feature = measured["feature_metres"]
    drawn = feature
    if size_setting and feature:
        default = defaults[size_setting]
        drawn = float(np.clip(feature, default / SIZE_RANGE, default * SIZE_RANGE))
        spec[size_setting] = round(drawn, 5)
    if "bump" in defaults and feature:
        spec["bump"] = round(measured["height"] * BUMP_PER_HEIGHT * drawn / feature, 6)
    apart = abs(measured["lab"][0] - measured["dark_lab"][0])
    if "contrast" in defaults and apart > 1.0:
        spec["contrast"] = round(min(1.0, measured["lightness_spread"] / (PATTERN_SPREAD * apart)), 4)
    return spec


def fitted_tile(family, measured, method=METHOD):
    """The tile metres at which the relief's features (`measured` at a 1 m tile) are the family's default pattern
    size; None when the maps show no relief or the family has no pattern size."""
    size_setting, feature = SIZE_SETTING.get(family), measured["feature_metres"]
    if not size_setting or not feature:
        return None
    return json.loads(pathlib.Path(method).read_text())["recipes"][family][size_setting] / feature


def fitted(name, maps, tile_metres, method=METHOD, normal_convention="opengl", albedo_colour=None, constants=None,
           emission_colour=None):
    """A material's fitted recipe from its maps ({role: path}, with no albedo map its constant `albedo_colour`, with no
    map of a measure its surface.json `constants`), its
    tile size (None: fitted, `fitted_tile`, else TILE_METRES assumed) and its normal map's convention: {"recipe", "statistics", "family_from", "tile_metres",
    "tile_metres_from" (None when given)}."""
    tile_from = None
    if tile_metres is None:
        at_one = statistics(maps, 1.0, normal_convention, albedo_colour, constants, emission_colour)
        tile_metres = fitted_tile(family_of(name, at_one)[0], at_one, method)
        tile_metres, tile_from = (tile_metres, "fitted") if tile_metres else (TILE_METRES, "assumed")
    measured = statistics(maps, tile_metres, normal_convention, albedo_colour, constants, emission_colour)
    family, said_by = family_of(name, measured)
    return {"recipe": spec_of(family, measured, method), "statistics": measured, "family_from": said_by,
            "tile_metres": tile_metres, "tile_metres_from": tile_from}
