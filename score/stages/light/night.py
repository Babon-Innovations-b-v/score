"""A night sky's light over a place on a body with air (data/physics/night.json), once its star stands past astronomical
twilight: the light of the bodies that throw their star's light back (the Moon), the air that light scatters, and the
light a city sends up into its air, each from its measured physics, never from a concept's colours (2026-11-10: the
night places square, street, stairwell and flat rendered under a black sky with only their warm lamps; their concepts
show a navy sky and a blue night light).

    reflected   each reflecting body over the horizon (its `reflecting` entry) a distant light from its direction:
                its star's lux at its distance times its geometric albedo, its size and its phase law (Krisciunas
                and Schaefer 1991), dimmed and reddened by the air along its way; its colour its own light's (kelvin)
                through the air
    air glow    the sky's luminance from every way over the horizon: the moonlit air (Krisciunas and Schaefer's model,
                its Rayleigh part blued by lambda^-4.05, its haze part by Angstrom's lambda^-1.3), the city's light
                scattered by the same air (a `skyglow` site's measured zenith brightness, the city light's kelvin
                weighted by each part's optical depth), and the setting's own backdrops (starlight)

Light is in the views' units, W/m^2 at LUMENS_PER_WATT (sky.py's), times `scale`: the views are set so an 18% grey
under VIEW_LUX reads 0.18 of linear light; an eye at a lit place at night stands in `adapted_lux` (outside, or inside
under a roof: roofed), so the night is drawn as that eye sees it, VIEW_LUX / adapted_lux times its physical light. The
lamps' strengths are the sweep's (light/mix.py), so this is the same picture as the camera's exposure raised for the
night with the lamps swept back.

Colours are worked out from spectra: a black body at the light's kelvin times the air's weighting, through the CIE 1931
observer (Wyman, Sloan and Shirley 2013's fit, JCGT 2(2)) into linear Rec. 709, its luminance one.

    is_night(seen) -> bool
    skyglow_of(table, site) -> its skyglow entry or None
    reflected(seen, kept, table, scale, dark) -> [{name, of, azimuth, altitude, across, lux, colour}]
    air_glow(seen, kept, table, scale) -> {"ambient": [r, g, b], "background": [r, g, b]}   linear radiance
    roofed(stage, place, floor) -> bool                     a roof over most of the floor: the eye stands inside
    write(stage, place, seen, kept, table, inside) -> what was written, or None by day or with no air
    write_layer(layer_path, root, place, kept, table, floor) -> the same, written into a light layer file
"""
import math

import numpy as np

from score.stages.light import sky

# The views' light: an 18% grey under this many lux reads 0.18 (pi W/m^2 of light at LUMENS_PER_WATT lux a watt).
VIEW_LUX = math.pi * sky.LUMENS_PER_WATT
# Astronomical twilight ends with the star 18 degrees under the horizon: past it the sky is the night's alone.
TWILIGHT_END = -18.0
# cd/m^2 of a sky at 0 mag/arcsec^2 (Garstang 1986; 10.8e4 x 10^(-0.4 m)), and nanolamberts to cd/m^2.
ZERO_MAG = 10.8e4
NANOLAMBERT = 1e-5 / math.pi
# Krisciunas and Schaefer (1991): the Moon's light at its mean distance (their I*, 10^(-0.4 (3.84 + ...))) and the
# scattering function's Rayleigh and haze terms, f(rho) = 10^5.36 (1.06 + cos^2 rho) + 10^(6.15 - rho / 40).
MOON_MAGNITUDE = 3.84
RAYLEIGH_SCALE, RAYLEIGH_EVEN = 10 ** 5.36, 1.06
HAZE_SCALE, HAZE_FALL = 10 ** 6.15, 40.0
# The magnitudes' step and the eye's middle wavelength (micrometres) the extinction is read at.
MAGNITUDE = 2.5 / math.log(10.0)
GREEN = 0.55
WAVELENGTHS = np.arange(380.0, 781.0, 5.0)  # nm
# CIE XYZ to linear Rec. 709 (sRGB's primaries, D65).
XYZ_TO_RGB = np.array([[3.2406, -1.5372, -0.4986], [-0.9689, 1.8758, 0.0415], [0.0557, -0.2040, 1.0570]])
LUMINANCE = np.array([0.2126, 0.7152, 0.0722])
# The rods' share of seeing (seen_dark) runs from all of it under 10^MESOPIC_BOTTOM cd/m^2 to none over 10^MESOPIC_TOP,
# and the colour the rods see in, chromaticity (0.25, 0.25) as XYZ over Y (Jensen et al. 2001).
MESOPIC_BOTTOM, MESOPIC_TOP = -2.0, 0.6
BLUE_SHIFT = (1.0, 1.0, 2.0)
# A place stands under a roof (the eye adapted to a room's light) when its roofs cover at least this share of its floor.
ROOFED_LEAST = 0.5
# The sky's ways the glow is summed over: zenith angles and azimuths, degrees.
ZENITHS = np.arange(0.5, 90.0, 1.0)
AZIMUTHS = np.arange(0.0, 360.0, 2.0)
FROM = "the night's physics over the site (score/stages/light/night.py, data/physics/night.json)"


def lobe(wavelength, middle, low, high):
    spread = np.where(wavelength < middle, low, high)
    return np.exp(-0.5 * ((wavelength - middle) / spread) ** 2)


def observer(wavelength):
    """The CIE 1931 colour matching functions (x, y, z) at `wavelength` nm: Wyman, Sloan and Shirley's multi-lobe
    fit."""
    x = 1.056 * lobe(wavelength, 599.8, 37.9, 31.0) + 0.362 * lobe(wavelength, 442.0, 16.0, 26.7) - \
        0.065 * lobe(wavelength, 501.1, 20.4, 26.2)
    y = 0.821 * lobe(wavelength, 568.8, 46.9, 40.5) + 0.286 * lobe(wavelength, 530.9, 16.3, 31.1)
    z = 1.217 * lobe(wavelength, 437.0, 11.8, 36.0) + 0.681 * lobe(wavelength, 459.0, 26.0, 13.8)
    return np.stack([x, y, z])


def black_body(kelvin):
    """Planck's spectral radiance at WAVELENGTHS, its scale left out."""
    metres = WAVELENGTHS * 1e-9
    return 1.0 / (metres ** 5 * np.expm1(1.4388e-2 / (metres * float(kelvin))))


def luminous(spectrum):
    """A spectrum's luminance on the observer's y, its scale left as is."""
    return float(observer(WAVELENGTHS)[1] @ spectrum)


def colour(spectrum, dark=0.0):
    """A spectrum as linear Rec. 709 with luminance 1 (negative channels at 0), as an eye whose rods take `dark` of
    its seeing takes it (seen_dark): its tristimulus blended toward the rods' blue (BLUE_SHIFT) by that share, weighted
    by the light's scotopic over photopic luminance (Larson, Rushmeier and Piatko 1997's approximation,
    V = Y (1.33 (1 + (Y + Z) / X) - 1.68)), the blend of Jensen et al. 2001, 'A Physically-Based Night Sky Model'."""
    tristimulus = observer(WAVELENGTHS) @ spectrum
    tristimulus = tristimulus / tristimulus[1]
    rods = 1.33 * (1.0 + (tristimulus[1] + tristimulus[2]) / tristimulus[0]) - 1.68
    shifted = (1.0 - dark) * tristimulus + dark * rods * np.asarray(BLUE_SHIFT)
    rgb = np.maximum(XYZ_TO_RGB @ shifted, 0.0)
    return rgb / float(LUMINANCE @ rgb)


def seen_dark(luminance):
    """The share of seeing the rods take at a luminance (cd/m^2): all of it under 10^-2, none over 10^0.6, a smooth
    step between in log luminance (Jensen et al. 2001 after Ferwerda et al. 1996)."""
    across = (MESOPIC_TOP - math.log10(max(luminance, 1e-9))) / (MESOPIC_TOP - MESOPIC_BOTTOM)
    across = min(1.0, max(0.0, across))
    return across * across * (3.0 - 2.0 * across)


def depths(air, haze):
    """The air's optical depth at WAVELENGTHS: (Rayleigh's, the haze's)."""
    micrometres = WAVELENGTHS / 1000.0
    return (air["rayleigh_depth"] * micrometres ** -air["rayleigh_power"],
            haze * (micrometres / GREEN) ** -air["angstrom"])


def extinction(air, haze):
    """The air's extinction at GREEN in magnitudes per airmass (Krisciunas and Schaefer's k)."""
    return MAGNITUDE * (air["rayleigh_depth"] * GREEN ** -air["rayleigh_power"] + haze)


def airmass(zenith):
    """Krisciunas and Schaefer's airmass at a zenith angle (degrees): (1 - 0.96 sin^2 Z)^-1/2."""
    return (1.0 - 0.96 * np.sin(np.radians(zenith)) ** 2) ** -0.5


def is_night(seen):
    """Whether every star's light stands past astronomical twilight (TWILIGHT_END): the sky is the night's alone."""
    return bool(seen) and all(light["altitude"] <= TWILIGHT_END for light in seen["lights"])


def site_body(kept):
    on = kept["site"].get("on")
    return next((body for body in kept["setting"].get("bodies") or [] if body.get("body") == on), None)


def air_of(kept, table):
    body = site_body(kept)
    return (table.get("air") or {}).get((body.get("reference") or body.get("body"))) if body else None


def apart_km(first, second):
    """Great-circle kilometres between two (latitude, longitude) on the Earth's mean radius."""
    one, two = np.radians(first), np.radians(second)
    turn = np.sin((two[0] - one[0]) / 2) ** 2 + np.cos(one[0]) * np.cos(two[0]) * np.sin((two[1] - one[1]) / 2) ** 2
    return 2.0 * 6371.0 * math.asin(min(1.0, math.sqrt(float(turn))))


def skyglow_of(table, site):
    """The measured skyglow whose city the site stands in (within its `within_km`), else None."""
    if "latitude" not in site:
        return None
    for entry in table.get("skyglow") or []:
        apart = apart_km((site["latitude"], site["longitude"]), (entry["latitude"], entry["longitude"]))
        if entry.get("on") == site.get("on") and apart <= entry["within_km"]:
            return entry
    return None


def star_of(seen):
    """The brightest star's light (its lux where the site stands), under the horizon or not."""
    return seen["lights"][0] if seen["lights"] else None


def phase_angle(lit):
    """A body's phase angle (degrees) from its lit share: lit = (1 + cos alpha) / 2."""
    return math.degrees(math.acos(max(-1.0, min(1.0, 2.0 * float(lit) - 1.0))))


def distance_km(kept, body):
    """A body's distance from its true size: its radius over the sine of half its angle across."""
    radius = next(entry["radius_km"] for entry in kept["setting"]["bodies"] if entry.get("body") == body["body"])
    return radius / math.sin(math.radians(body["across"]) / 2.0)


def phase_law(entry, alpha):
    return 10.0 ** (-0.4 * (entry["phase_linear"] * abs(alpha) + entry["phase_quartic"] * alpha ** 4))


def body_lux(kept, star, body, entry):
    """The light a reflecting body gives at the site outside the air: its star's lux times its geometric albedo, the
    share of the sky its disc fills seen from its star's side (radius over distance, squared) and its phase law."""
    radius = next(item["radius_km"] for item in kept["setting"]["bodies"] if item.get("body") == body["body"])
    share = (radius / distance_km(kept, body)) ** 2
    return star["lux"] * entry["albedo"] * share * phase_law(entry, phase_angle(body["lit"]))


def reflected(seen, kept, table, scale, dark=0.0):
    """Each reflecting body over the horizon as a light: its lux through the air along its way (its spectrum dimmed
    by exp(-tau X) at each wavelength) times `scale`, and its colour so reddened, as an eye seeing `dark` with its
    rods takes it (colour)."""
    air, star = air_of(kept, table), star_of(seen)
    glow = skyglow_of(table, kept["site"])
    haze = glow["haze_depth"] if glow else 0.0
    found = []
    for body in seen["bodies"]:
        entry = (table.get("reflecting") or {}).get(body["body"])
        if entry is None or star is None or body["altitude"] <= 0.0:
            continue
        spectrum = black_body(entry["kelvin"])
        through = spectrum * np.exp(-sum(depths(air, haze)) * airmass(90.0 - body["altitude"]))
        lux = body_lux(kept, star, body, entry) * luminous(through) / luminous(spectrum)
        found.append({"name": body["name"], "of": body["body"], "azimuth": body["azimuth"],
                      "altitude": body["altitude"], "across": body["across"], "lux": lux * scale,
                      "colour": colour(through, dark).tolist()})
    return found


def ways():
    """(zenith, azimuth) degrees of every sky cell and its solid angle."""
    zenith, azimuth = np.meshgrid(ZENITHS, AZIMUTHS, indexing="ij")
    solid = np.sin(np.radians(zenith)) * math.radians(1.0) * math.radians(2.0)
    return zenith, azimuth, solid


def moonlit_air(seen, kept, table, haze):
    """The air a reflecting body lights, per sky cell: (Rayleigh's luminance, the haze's), cd/m^2, from Krisciunas and
    Schaefer's model with the body's light at its distance and phase."""
    air = air_of(kept, table)
    zenith, azimuth, _ = ways()
    rayleigh, hazy = np.zeros_like(zenith), np.zeros_like(zenith)
    fading = extinction(air, haze)
    for body in seen["bodies"]:
        entry = (table.get("reflecting") or {}).get(body["body"])
        if entry is None or body["altitude"] <= 0.0:
            continue
        alpha = phase_angle(body["lit"])
        light = 10.0 ** (-0.4 * MOON_MAGNITUDE) * phase_law(entry, alpha) * \
            (entry["mean_distance_km"] / distance_km(kept, body)) ** 2
        cosine = np.clip(np.cos(np.radians(zenith)) * math.sin(math.radians(body["altitude"])) +
                         np.sin(np.radians(zenith)) * math.cos(math.radians(body["altitude"])) *
                         np.cos(np.radians(azimuth - body["azimuth"])), -1.0, 1.0)
        rho = np.degrees(np.arccos(cosine))
        common = light * 10.0 ** (-0.4 * fading * airmass(90.0 - body["altitude"])) * \
            (1.0 - 10.0 ** (-0.4 * fading * airmass(zenith))) * NANOLAMBERT
        rayleigh += RAYLEIGH_SCALE * (RAYLEIGH_EVEN + cosine ** 2) * common
        hazy += HAZE_SCALE * 10.0 ** (-rho / HAZE_FALL) * common
    return rayleigh, hazy


def air_glow(seen, kept, table, scale):
    """The sky's light from every way over the horizon in the views' units (radiance, linear Rec. 709) times `scale`:
    `ambient` its cosine-weighted mean (what lights a level surface, over pi), `background` its mean over the sky's
    ways (what the eye sees of it), with the luminance (cd/m^2) of each part at the zenith."""
    air = air_of(kept, table)
    glow = skyglow_of(table, kept["site"])
    haze = glow["haze_depth"] if glow else 0.0
    rayleigh_depth, haze_depth = depths(air, haze)
    zenith, _, solid = ways()
    moon = next(((table.get("reflecting") or {})[body["body"]] for body in seen["bodies"]
                 if body["body"] in (table.get("reflecting") or {})), None)
    moonlight = black_body(moon["kelvin"]) if moon else black_body(5772.0)
    lit_rayleigh, lit_haze = moonlit_air(seen, kept, table, haze)
    parts = [(lit_rayleigh, moonlight * rayleigh_depth), (lit_haze, moonlight * haze_depth)]
    if glow:
        city = black_body(glow["kelvin"])
        parts.append((np.full_like(zenith, ZERO_MAG * 10.0 ** (-0.4 * glow["zenith_mag"])),
                      city * (rayleigh_depth + haze_depth)))
    for backdrop in seen.get("backdrops") or []:
        if backdrop.get("shape") == "dome":
            parts.append((np.full_like(zenith, backdrop["lux"] / math.pi),
                          black_body(backdrop.get("kelvin") or 5772.0)))
    at_zenith = float(sum(value[0].mean() for value, _ in parts))
    dark = seen_dark(at_zenith)
    parts = [(value, colour(spectrum, dark)) for value, spectrum in parts]
    cosine = np.cos(np.radians(zenith))
    ambient = sum(np.sum(value * solid * cosine) / math.pi * tint for value, tint in parts)
    background = sum(np.sum(value * solid) / np.sum(solid) * tint for value, tint in parts)
    to_views = scale / sky.LUMENS_PER_WATT
    return {"ambient": (ambient * to_views).tolist(), "background": (background * to_views).tolist(),
            "dark": round(dark, 4),
            "zenith_cd": {"all": round(at_zenith, 6),
                          "moonlit air": round(float(lit_rayleigh[0].mean() + lit_haze[0].mean()), 6),
                          "skyglow": round(float(parts[2][0][0, 0]), 6) if glow else 0.0}}


def roofed(stage, place, floor):
    """Whether a roof stands over the place: the shell's roofs (design_shell's `roof_<n>`, score:plain "shell") cover
    at least ROOFED_LEAST of its record's floor box (`floor`, [[x, z] low, [x, z] high]) seen from above. A street
    under its shop awnings stands under the open sky; a room under its ceiling does not (2026-11-10: street's record
    is `inside` by its walls, its views full of sky)."""
    from pxr import Usd, UsdGeom
    if not floor:
        return False
    (low_x, low_z), (high_x, high_z) = floor
    area = max((high_x - low_x) * (high_z - low_z), 1e-9)
    cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ["default", "render"])
    root = stage.GetPrimAtPath(f"/{place}")
    covered = 0.0
    for prim in (Usd.PrimRange(root) if root else []):
        plain = prim.GetAttribute("score:plain").Get() if prim.HasAttribute("score:plain") else None
        if plain != "shell" or not prim.GetName().startswith("roof") or not prim.IsA(UsdGeom.Mesh):
            continue
        box = cache.ComputeWorldBound(prim).ComputeAlignedRange()
        wide = max(0.0, min(box.GetMax()[0], high_x) - max(box.GetMin()[0], low_x))
        deep = max(0.0, min(box.GetMax()[2], high_z) - max(box.GetMin()[2], low_z))
        covered += wide * deep
    return covered / area >= ROOFED_LEAST


def scale_of(table, inside):
    """The night's light on the views' scale: VIEW_LUX over the light an eye adapted to the lit place stands in."""
    return VIEW_LUX / table["adapted_lux"]["inside" if inside else "outside"]


def write_light(stage, place, light):
    """A reflecting body's light as a distant light from its way, its colour given (a renderer reads the colour, not a
    colour temperature), /<place>/Lights/night_<body>, tagged "night light" (the sky bodies gate holds the stars'
    lights; this one is the body's)."""
    from pxr import Gf, UsdGeom, UsdLux
    path = f"/{place}/Lights/night_{light['of']}"
    UsdGeom.Scope.Define(stage, f"/{place}/Lights")
    distant = UsdLux.DistantLight.Define(stage, path)
    distant.CreateIntensityAttr(light["lux"] / sky.LUMENS_PER_WATT / sky.scene.DISTANT_STRENGTH_PER_INTENSITY)
    distant.CreateColorAttr(Gf.Vec3f(*light["colour"]))
    distant.CreateAngleAttr(float(light["across"]))
    distant.AddOrientOp().Set(Gf.Quatf(sky.scene.aim_turn([0.0, 0.0, 0.0],
                                                          -sky.way(light["azimuth"], light["altitude"]))))
    sky.tagged(distant.GetPrim(), {"kind": "night light", "sky:of": light["of"], "sky:lux": float(light["lux"]),
                                   "from": FROM})
    return path


def write(stage, place, seen, kept, table, inside):
    """The night's light over the place where its star stands past astronomical twilight on a body whose air the table
    has: each reflecting body's light, and the air's glow as the scene's environment (its ambient light and the sky
    its views see; a stage that has its own environment keeps it). What was written, or None."""
    if not table or not seen or not kept or not is_night(seen) or air_of(kept, table) is None:
        return None
    scale = scale_of(table, inside)
    glow = air_glow(seen, kept, table, scale)
    lights = [write_light(stage, place, light) for light in reflected(seen, kept, table, scale, glow["dark"])]
    found = {"lights": lights, "scale": round(scale, 3), "zenith_cd": glow["zenith_cd"], "dark": glow["dark"],
             "environment": {"ambient": [round(value, 6) for value in glow["ambient"]],
                             "background": [round(value, 6) for value in glow["background"]]}}
    held = stage.GetPrimAtPath(f"/{place}/Environment")
    if not held:
        sky.scene.write_environment(stage, place, {
            "ambient": {"colour": glow["ambient"], "energy": 1.0}, "background": glow["background"],
            "exposure": 1.0, "ground_plane": True, "inside": inside, "from": FROM})
        return found
    lit(held, glow)  # the record's environment (its ambient black, its background black): the night's air over it
    return found


def lit(prim, glow):
    """An environment the stage holds given the night air's ambient light and background (its exposure, glow and the
    rest kept)."""
    from pxr import Gf, Sdf, UsdLux
    dome = UsdLux.DomeLight(prim)
    dome.CreateColorAttr().Set(Gf.Vec3f(*glow["ambient"]))
    dome.CreateIntensityAttr().Set(1.0)
    prim.CreateAttribute("score:background", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*glow["background"]))
    prim.CreateAttribute("score:night", Sdf.ValueTypeNames.String).Set(FROM)


def write_layer(layer_path, root, place, kept, table, floor):
    """The night's light (write) into the light layer at `layer_path` over the place's stage at `root`, a roof over it
    or not (roofed, on its record's `floor`); what was written, or None (the layer left as it was)."""
    from pxr import Sdf, Usd
    layer = Sdf.Layer.FindOrOpen(str(layer_path))
    composed = Sdf.Layer.CreateAnonymous(".usda")
    composed.subLayerPaths.append(layer.identifier)
    composed.subLayerPaths.append(str(root))
    stage = Usd.Stage.Open(composed)
    stage.SetEditTarget(Usd.EditTarget(layer))
    found = write(stage, place, sky.seen_of(kept), kept, table, roofed(stage, place, floor))
    if found:
        layer.Save()
    return found

