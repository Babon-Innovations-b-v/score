"""Fold depth_pano.tscn's six distance pictures of a spot into the 360° depth panorama Marble takes.

    ~/.farm-factory-props/env/bin/python tools/props/scene/pano.py <folder> [spot ...]

For each spot (every one in <folder>/spots.json when none is named) writes <spot>-depth.npy (metres,
2:1 equirectangular, nothing hit = inf) and <spot>-depth.png, the 8-bit picture
pano:depth_to_rgb decodes with z_min and z_max (World Labs' web-chisel-depth-png example):
1 - (ln r - ln z_min) / (ln z_max - ln z_min), near white, nothing hit black.

The panorama's middle column looks north along the seat (-along), east is to its right, and its
top row is straight up, in Marble's own frame: x right, y down, z ahead.
"""
import argparse
import json
import math
import pathlib
import sys

import numpy as np
from PIL import Image

# The panorama is this many times as wide as one face of the cube.
WIDE_FACES = 4
# Where the encoded picture's scale starts and stops, in metres: the room's own near and far.
Z_MIN_M = 0.1


def decoded(picture, near_m, far_m):
    """A depth face's distances in metres from its two 8-bit channels (depth_pano.gdshader);
    a pixel that hit nothing (the far end of the scale) is inf."""
    pixels = np.asarray(Image.open(picture).convert("RGB")).astype(np.float64)
    share = (np.round(pixels[..., 0]) + pixels[..., 1] / 255.0) / 255.0
    distance = np.exp(math.log(near_m) + share * (math.log(far_m) - math.log(near_m)))
    distance[share >= 0.999] = np.inf
    return distance


def directions(width):
    """The direction of every pixel of a 2:1 panorama, in the seat's frame (x east, y up, z south)."""
    height = width // 2
    across = (np.arange(width) + 0.5) / width
    down = (np.arange(height) + 0.5) / height
    longitude = (across - 0.5) * 2 * math.pi
    latitude = (0.5 - down) * math.pi
    longitude, latitude = np.meshgrid(longitude, latitude)
    return np.stack([np.cos(latitude) * np.sin(longitude), np.sin(latitude),
                     -np.cos(latitude) * np.cos(longitude)], axis=-1)


def folded(faces, ways, width):
    """The panorama of distances from six faces, each seen by a 90-degree camera turned `ways[way]`
    (its right, up and back columns): each pixel read from the face it falls in."""
    rays = directions(width)
    pano = np.full(rays.shape[:2], np.nan)
    for way, distance in faces.items():
        right, up, back = (np.array(column) for column in ways[way])
        ahead = -(rays @ back)
        safe = np.where(ahead > 1e-6, ahead, 1.0)
        x, y = (rays @ right) / safe, (rays @ up) / safe
        inside = (ahead > 1e-6) & (np.abs(x) <= 1) & (np.abs(y) <= 1) & np.isnan(pano)
        size = distance.shape[0]
        column = np.clip(((x + 1) / 2 * size).astype(int), 0, size - 1)
        row = np.clip(((1 - y) / 2 * size).astype(int), 0, size - 1)
        pano[inside] = distance[row[inside], column[inside]]
    return pano


def encoded(pano, z_max):
    """The 8-bit picture pano:depth_to_rgb decodes with z_min = Z_MIN_M and z_max: near white."""
    finite = np.isfinite(pano)
    share = np.zeros_like(pano)
    share[finite] = (np.log(np.clip(pano[finite], Z_MIN_M, z_max)) - math.log(Z_MIN_M)) / (math.log(z_max) - math.log(Z_MIN_M))
    picture = np.where(finite, 1.0 - share, 0.0)
    return Image.fromarray(np.round(picture * 255).astype(np.uint8), "L")


def fold_spot(folder, spot, facts):
    """One spot's panorama, saved as .npy and as Marble's PNG; its z_max."""
    faces = {way: decoded(folder / f"{spot}-{way}.png", facts["near_m"], facts["far_m"]) for way in facts["ways"]}
    pano = folded(faces, facts["ways"], facts["face_px"] * WIDE_FACES)
    np.save(folder / f"{spot}-depth.npy", pano)
    finite = pano[np.isfinite(pano)]
    z_max = float(np.ceil(finite.max())) if finite.size else facts["far_m"]
    encoded(pano, z_max).save(folder / f"{spot}-depth.png")
    return z_max


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("folder", type=pathlib.Path)
    parser.add_argument("spots", nargs="*")
    options = parser.parse_args()
    facts = json.loads((options.folder / "spots.json").read_text())
    scales = {}
    for spot in options.spots or facts["spots"]:
        scales[spot] = {"z_min": Z_MIN_M, "z_max": fold_spot(options.folder, spot, facts)}
        print(spot, scales[spot], flush=True)
    known = options.folder / "scales.json"
    kept = json.loads(known.read_text()) if known.exists() else {}
    known.write_text(json.dumps({**kept, **scales}, indent=1))


if __name__ == "__main__":
    sys.exit(main())
