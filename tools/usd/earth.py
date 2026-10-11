"""The Earth's surface as the framework draws it on a ball in a place's sky: the real planet, from NASA's Blue Marble
(Next Generation, July 2004: the land and sea as the satellites saw them, no cloud) with NASA's cloud cover over it,
baked once into a longitude-latitude picture that a sphere's uvs (builders.sphere) take, so any USD reader shows the
same planet. Both are NASA Earth Observatory's Visible Earth pictures, free of copyright (NASA's media guidelines);
they are fetched once into PROPS_HOME/downloads/nasa and checked against their pinned sha256, never kept in the
repository.

Until 2026-10-11 this was the game 2099's ink_earth shader repeated in numpy (flat palette colours and an ink line
round every coast), which read as a cartoon disc in every Moon place's sky (the paper-vs-world-1 audit, item 17).

The day and night step is the light's work in the stage: the ball is a plain diffuse surface lit by the place's own
sun, so its night side is dark where the sun does not reach it.

    picture(width) -> uint8 (height, width, 3) array, sRGB
    write(path, width=4096) -> path
"""
import hashlib
import os
import pathlib
import urllib.request

import numpy as np
from PIL import Image

PROPS_HOME = pathlib.Path(os.environ.get("PROPS_HOME", pathlib.Path.home() / ".farm-factory-props"))
DOWNLOADS = PROPS_HOME / "downloads/nasa"
SOURCES = {
    "surface": ("https://eoimages.gsfc.nasa.gov/images/imagerecords/74000/74092/world.200407.3x5400x2700.jpg",
                "f55226d46d27e05511f2118dc6aa24f5dbf9b6b2cddc87cc6e0e7dd067c00b11"),
    "clouds": ("https://eoimages.gsfc.nasa.gov/images/imagerecords/57000/57747/cloud_combined_2048.jpg",
               "daddaad84d7a33bbbc86cdda3f591099f57cee8607b7bcf3b67eb7e4f7a1c793"),
}
# Which longitude lies at u = 0 of the ball's uvs, in degrees east: chosen so Africa and Europe face the Moon base's
# places (the old station's eye sees the ball's u near 0.43, its Earth 20 degrees across).
LONGITUDE_AT_U0 = -134.0
# How the cloud map's brightness becomes cover: none under CLOUD_FROM, full at CLOUD_FULL; cloud tops a little under
# pure white.
CLOUD_FROM = 0.08
CLOUD_FULL = 0.85
CLOUD_WHITE = 0.93


def source(name):
    """The local copy of one NASA picture, fetched once and checked against its pinned sha256."""
    url, digest = SOURCES[name]
    path = DOWNLOADS / pathlib.PurePosixPath(url).name
    if not path.exists():
        DOWNLOADS.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(url, timeout=300) as answer:
            path.write_bytes(answer.read())
    found = hashlib.sha256(path.read_bytes()).hexdigest()
    if found != digest:
        raise ValueError(f"{path} is not NASA's picture: sha256 {found}, pinned {digest}")
    return path


def srgb_to_linear(value):
    return np.where(value <= 0.04045, value / 12.92, ((value + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(value):
    return np.where(value <= 0.0031308, value * 12.92, 1.055 * np.power(np.clip(value, 0.0, None), 1 / 2.4) - 0.055)


def resampled(name, width, mode):
    """One NASA picture at `width` x `width / 2`, turned so its longitude LONGITUDE_AT_U0 lies at u = 0, as floats
    from 0 to 1."""
    picture = Image.open(source(name)).convert(mode).resize((width, width // 2), Image.LANCZOS)
    values = np.asarray(picture, dtype=np.float64) / 255.0
    shift = int(round((LONGITUDE_AT_U0 + 180.0) / 360.0 * width))
    return np.roll(values, -shift, axis=1)


def picture(width=4096):
    """The Earth's surface as an sRGB picture, longitude across and latitude up (north at the top row), the cloud
    cover laid over the land and sea in linear light."""
    surface = srgb_to_linear(resampled("surface", width, "RGB"))
    cloud = np.clip((resampled("clouds", width, "L") - CLOUD_FROM) / (CLOUD_FULL - CLOUD_FROM), 0.0, 1.0)
    white = srgb_to_linear(np.array(CLOUD_WHITE))
    mixed = surface + (white - surface) * cloud[..., None]
    return (np.clip(linear_to_srgb(mixed), 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)


def write(path, width=4096):
    """The picture saved as PNG at `path` (made once: a picture already there is kept)."""
    path = pathlib.Path(path)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(picture(width)).save(path)
    return path
