"""Mars's daytime sky as the framework draws it round a place: the light the dusty air scatters toward the eye from
every way, worked out for a flat layer of dust over the ground lit by the place's own sun, and baked once into a
longitude-latitude picture on a ball round the place (scene.write_sky_dome) that any USD reader shows.

Until 2026-10-11 the sky over Mars was the game's thin air shell (a fog 70 m deep) in front of black space: one flat
brown wall with no sun in it (the paper-vs-world-1 audit, item 17). The air above that shell is this picture.

The model is the textbook single scattering of a plane-parallel layer (optical depth `depth`, each colour channel's
single-scattering albedo `albedo`, Henyey-Greenstein phase with forward throw `forward`) seen from its floor, with
its many-times-scattered light as an even glow over it (`diffuse`): the sky paler and brighter toward the horizon,
where the eye looks through more dust, and brightest round the sun, where the dust throws most light forward; Mars's
dust takes more blue than red, so the sky is butterscotch and the sun's glow is paler. The numbers are the record's
(data/scene/<place>.json, environment `sky_dome`), each with its source; the picture's overall brightness and
colour balance are the record's `gain`, measured against the place's concept on the rendered views.

    picture(entry, toward, width) -> float32 (height, width, 3), linear
    write(path, entry, toward, width=1024) -> (path, strength): an 8-bit sRGB PNG of the picture over strength
"""
import pathlib

import numpy as np
from PIL import Image

# The lowest the eye's way is taken to look: under it (the ground's side) the horizon's light is kept.
LOWEST = 0.02


def ways(width):
    """The unit way out from the ball's middle at each texel's centre, as builders.sphere lays its uvs (u its
    longitude, v from the south pole up): the same layout as earth.ways."""
    height = width // 2
    u = (np.arange(width) + 0.5) / width
    v = 1.0 - (np.arange(height) + 0.5) / height
    azimuth = 2.0 * np.pi * u[None, :]
    polar = np.pi * (1.0 - v[:, None])
    return np.stack(np.broadcast_arrays(np.sin(polar) * np.sin(azimuth), np.cos(polar) + 0.0 * azimuth,
                                        -np.sin(polar) * np.cos(azimuth)), axis=-1)


def phase(cosine, forward):
    """Henyey-Greenstein's phase function, per steradian."""
    return (1.0 - forward ** 2) / (4.0 * np.pi * (1.0 + forward ** 2 - 2.0 * forward * cosine) ** 1.5)


def single(up_eye, up_sun, depth):
    """How much of the sun's light one scattering in the layer sends down a way `up_eye` (the sine of its height)
    when the sun stands at `up_sun`, before albedo and phase: mu_s / (mu_s - mu_v) (e^(-depth/mu_s) - e^(-depth/mu_v)),
    its limit where the two are equal."""
    apart = up_sun - up_eye
    close = np.abs(apart) < 1e-4
    safe = np.where(close, 1.0, apart)
    general = up_sun / safe * (np.exp(-depth / up_sun) - np.exp(-depth / up_eye))
    limit = depth / up_eye * np.exp(-depth / up_eye)
    return np.where(close, limit, general)


def picture(entry, toward, width):
    """The sky's light from every way (linear, the record's gain on it) for the sun shining along `toward`."""
    sun = -np.asarray(toward, dtype=np.float64)
    sun /= np.linalg.norm(sun)
    way = ways(width)
    up_eye = np.maximum(way[..., 1], LOWEST)
    up_sun = max(float(sun[1]), LOWEST)
    cosine = way @ sun
    depth = float(entry["depth"])
    albedo = np.asarray(entry["albedo"], dtype=np.float64)
    scattered = phase(cosine, float(entry["forward"]))[..., None] * single(up_eye, up_sun, depth)[..., None] * albedo
    diffuse = float(entry["diffuse"]) * albedo ** 2 * (1.0 - np.exp(-depth / up_eye))[..., None] * up_sun
    return ((scattered + diffuse) * np.asarray(entry["gain"], dtype=np.float64)).astype(np.float32)


def linear_to_srgb(value):
    return np.where(value <= 0.0031308, value * 12.92, 1.055 * np.power(np.clip(value, 0.0, None), 1 / 2.4) - 0.055)


def write(path, entry, toward, width=1024):
    """The picture as an 8-bit sRGB PNG over its 98th percentile (the glow within a few degrees of the sun, under its
    disc, clips white, so the rest of the sky keeps the PNG's steps fine), which is returned with the path: a renderer
    gives the picture off at that strength (score:sky_strength) to get the linear light back."""
    light = picture(entry, toward, width)
    strength = float(np.percentile(light, 98.0))
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray((np.clip(linear_to_srgb(light / strength), 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)).save(path)
    return path, strength
