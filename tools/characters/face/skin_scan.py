"""Real skin's small detail from a photographed head scan (#226): the colour and relief of skin a few millimetres
across, cut from Infinite-Realities' head scan of Lee Perry-Smith and made into a seamless tile the skin's finish
repeats over the whole body.

Procedural pores and noise blotches (ed6d3057b) never read as skin (owner, 2026-11-25: "skin waxy everywhere:
pores, redness, veins, tone variation"): a noise has none of skin's structure (pores in rows along the lines of
tension, fine capillaries, the speckle of melanin). The scan's own albedo carries all of it, photographed.

Source: "Infinite, 3D Head Scan by Lee Perry-Smith is licensed under a Creative Commons Attribution 3.0 Unported
License. Based on a work at www.triplegangers.com." (ir-ltd.net), its albedo (`lambertian.jpg`, 4096 x 4096) as
Morgan McGuire and Guedis Cardenas converted it, fetched from github.com/keijiro/InfiniteScan at `COMMIT` (its
License.txt: every model and image file CC BY 3.0). Changed: a square of the forehead cut out, its light and its
colour over more than `COLOUR_SIGMA_MM` taken out, made to repeat with no seam (`periodic`).

`tiles(folder)` writes `<folder>/skin_detail_colour.png` (each channel's ratio to its own local mean, 0.5 the mean,
8-bit linear) and `<folder>/skin_detail_height.png` (the brightness's ratio to its mean over `HEIGHT_SIGMA_MM`, dark
pores and creases low, 16-bit, 0.5 the mean), and returns the measures the finish's record carries (`scan`).
The download is cached (`cache_root()`, 9 MB) and checked against `SHA256`.
"""
import hashlib
import os
import pathlib
import urllib.request

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

COMMIT = "150b6c46ebb6a011b93ed2e0fee9b612df78281b"
SOURCE = f"https://github.com/keijiro/InfiniteScan/raw/{COMMIT}/Assets/InfiniteScan/Textures/lambertian.jpg"
SHA256 = "4fc7297835e2081cb914d1a8507fc837687102eed7bd3c6bed25b72960a09e08"
CREDIT = ("Infinite, 3D Head Scan by Lee Perry-Smith (Infinite-Realities, ir-ltd.net), based on a work at "
          "www.triplegangers.com, converted by Morgan McGuire and Guedis Cardenas, from github.com/keijiro/InfiniteScan "
          f"at {COMMIT}, CC BY 3.0; changed: a forehead square cut out, its light and broad tone taken out, made "
          "to repeat")
LICENCE_URL = "https://creativecommons.org/licenses/by/3.0/"
SOURCE_ID = "infinite_head_scan"  # its row in score_lib's config/sources.toml
# The scan's scale on the forehead: its eyes' middles stand 492 pixels apart on the 4096 texture (read off the
# albedo, the closed lids' middles at x 1748 and 2240 on row 1200), a woman's and a man's mean pupil distance 63 mm
# (Dodgson 2004), so 0.128 mm a pixel where the face looks forward.
METRES_PER_PIXEL = 0.063 / 492
# The square cut: the forehead between the brows' tops and the hairline's stubble, clear of the frown's crease
# (columns 1900 to 2220, rows 625 to 945): skin and nothing else, 41 mm across.
SQUARE = (1900, 625, 320)
# Colour over more than this (the scan's light, the broad tone) is the finish's own, not the tile's: wide enough to keep
# the blotches a few millimetres across that make skin read uneven (3 mm left only a speckle; the face read as wax).
COLOUR_SIGMA_MM = 6.0
# relief: pores and fine creases are a tenth to a half of a millimetre across; the scan's albedo taken as height
# over 1 mm drew blobs a millimetre wide, a stucco over the whole skin (photoreal round 1, 2026-11-26)
HEIGHT_SIGMA_MM = 0.45
# The scan is a JPEG: its 8-pixel blocks' edges and its half-size, blocky colour would come up as a grid and blue
# speckle once the broad tone is taken out, so the brightness is smoothed a little under a pore's size and the colour
# (each channel over the brightness) over a JPEG's colour pixel.
JPEG_SIGMA_PIXELS = 0.7
CHROMA_SIGMA_PIXELS = 1.5
LUMINANCE = np.array([0.2126, 0.7152, 0.0722])  # Rec. 709's weights of linear red, green and blue


def cache_root():
    """Where the scan's albedo is kept: SCORE_SKIN_CACHE, else ~/.cache/score/skin-scan."""
    return pathlib.Path(os.environ.get("SCORE_SKIN_CACHE", pathlib.Path.home() / ".cache/score/skin-scan"))


def albedo():
    """The scan's albedo, fetched once at the pinned commit; refused when its bytes are not the pinned ones."""
    path = cache_root() / COMMIT / "lambertian.jpg"
    if not path.is_file():
        path.parent.mkdir(parents=True, exist_ok=True)
        part = path.with_suffix(".part")
        urllib.request.urlretrieve(SOURCE, part)
        part.rename(path)
    found = hashlib.sha256(path.read_bytes()).hexdigest()
    if found != SHA256:
        raise ValueError(f"{path}: sha256 {found}, not the pinned scan's {SHA256}")
    return path


def linear(picture):
    """An sRGB picture's channels as linear values 0 to 1."""
    values = np.asarray(picture, dtype=np.float64) / 255.0
    return np.where(values <= 0.04045, values / 12.92, ((values + 0.055) / 1.055) ** 2.4)


def ratio_to_local_mean(values, sigma_pixels):
    """Each channel's value over its own Gaussian mean `sigma_pixels` wide (the tile's detail, its mean 1)."""
    if values.ndim == 2:
        return values / gaussian_filter(values, sigma_pixels, mode="wrap")
    return np.stack([values[..., channel] / gaussian_filter(values[..., channel], sigma_pixels, mode="wrap")
                     for channel in range(values.shape[-1])], axis=-1)


def periodic(values):
    """The square's periodic part (Moisan 2011, "Periodic plus smooth image decomposition"): the square less the
    smooth image whose Laplacian is the jumps across its opposite edges, so it repeats with no seam and no crossfade
    (a crossfade blurs where it mixes and shows a cross where its weights meet). Each channel on its own."""
    if values.ndim == 3:
        return np.stack([periodic(values[..., channel]) for channel in range(values.shape[-1])], axis=-1)
    rows, columns = values.shape
    jumps = np.zeros_like(values)
    jumps[0, :] += values[-1, :] - values[0, :]
    jumps[-1, :] += values[0, :] - values[-1, :]
    jumps[:, 0] += values[:, -1] - values[:, 0]
    jumps[:, -1] += values[:, 0] - values[:, -1]
    across = 2.0 * np.cos(2.0 * np.pi * np.arange(rows) / rows)[:, None] + \
        2.0 * np.cos(2.0 * np.pi * np.arange(columns) / columns)[None, :] - 4.0
    across[0, 0] = 1.0
    smooth = np.fft.fft2(jumps) / across
    smooth[0, 0] = 0.0
    return values - np.real(np.fft.ifft2(smooth))


def square_of(path):
    """The forehead square of the scan's albedo, linear."""
    left, top, side = SQUARE
    with Image.open(path) as picture:
        return linear(picture.convert("RGB").crop((left, top, left + side, top + side)))


def tiles(folder):
    """The colour and height tiles written under `folder`; the record's `scan` block."""
    folder = pathlib.Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    skin = square_of(albedo())
    skin = gaussian_filter(periodic(skin), (JPEG_SIGMA_PIXELS, JPEG_SIGMA_PIXELS, 0), mode="wrap")
    brightness = skin @ LUMINANCE
    tone = gaussian_filter(skin / brightness[..., None], (CHROMA_SIGMA_PIXELS, CHROMA_SIGMA_PIXELS, 0), mode="wrap")
    colour = ratio_to_local_mean(tone * brightness[..., None], COLOUR_SIGMA_MM / 1000.0 / METRES_PER_PIXEL)
    height = ratio_to_local_mean(brightness, HEIGHT_SIGMA_MM / 1000.0 / METRES_PER_PIXEL)
    spread = float(height.std())
    height_scaled = np.clip(0.5 + (height - 1.0) / (6.0 * spread), 0.0, 1.0)
    Image.fromarray(np.clip(np.round(colour * 0.5 * 255.0), 0, 255).astype(np.uint8)).save(
        folder / "skin_detail_colour.png")
    Image.fromarray(np.round(height_scaled * 65535.0).astype(np.uint16)).save(folder / "skin_detail_height.png")
    return {"colour": "skin_detail_colour.png", "height": "skin_detail_height.png",
            "tile_m": round(SQUARE[2] * METRES_PER_PIXEL, 5),
            "colour_spread": [round(float(value), 4) for value in colour.std(axis=(0, 1))],
            "height_spread_of_three_sigma": 0.5}
