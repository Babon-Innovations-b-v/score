"""Cut level, rectilinear plan views out of a spot's 360° panorama: the painting, or the depth.

    ~/.farm-factory-props/env/bin/python tools/props/scene/planview.py <pano.png|depth.npy> <spot> \
        --out <folder> [--ways north,east,...] [--size 2048x1152] [--hfov 90] [--eye 1.6]

Each view is what a level camera standing at the spot's eye would see turned one way: the four
ways and the four diagonals by default, 2048 x 1152 with a 90-degree horizontal field of view.
Writes <folder>/<spot>-<way>.png (a .npy of metres too when cutting a depth panorama) and merges
each view's camera into <folder>/views.json, so the game can be drawn from the identical camera.

The ways are depth_pano.gd's: a yaw in degrees about up off the seat's frame, as Godot turns a
camera (Basis(UP, yaw)): north 0 (looking -z), east -90, south 180, west 90. The panorama is
pano.py's: its middle column looks north and east is to its right. A Godot camera keeps its
height by default, so views.json also gives the vertical field of view to set as Camera3D.fov.
"""
import argparse
import json
import math
import pathlib
import sys

import numpy as np
from PIL import Image

# Every way a view is cut, as a Godot yaw about up in degrees (depth_pano.gd's WAYS, plus the
# diagonals between them).
WAYS = {
    "north": 0.0, "northeast": -45.0, "east": -90.0, "southeast": -135.0,
    "south": 180.0, "southwest": 135.0, "west": 90.0, "northwest": 45.0,
}
WIDTH, HEIGHT = 2048, 1152
HFOV_DEGREES = 90.0
EYE_M = 1.6


def vertical_fov(hfov_degrees, width, height):
    """The vertical field of view in degrees of a rectilinear view as wide as `hfov_degrees`."""
    return math.degrees(2 * math.atan(math.tan(math.radians(hfov_degrees) / 2) * height / width))


def turn(yaw_degrees):
    """A level camera's right and back axes in the seat's frame (x east, y up, z south)."""
    angle = math.radians(yaw_degrees)
    right = np.array([math.cos(angle), 0.0, -math.sin(angle)])
    back = np.array([math.sin(angle), 0.0, math.cos(angle)])
    return right, back


def rays(yaw_degrees, hfov_degrees, width, height):
    """The direction through every pixel's middle of a level view turned `yaw_degrees`."""
    right, back = turn(yaw_degrees)
    half_wide = math.tan(math.radians(hfov_degrees) / 2)
    half_high = half_wide * height / width
    across = ((np.arange(width) + 0.5) / width * 2 - 1) * half_wide
    rise = (1 - (np.arange(height) + 0.5) / height * 2) * half_high
    across, rise = np.meshgrid(across, rise)
    directions = across[..., None] * right + rise[..., None] * np.array([0.0, 1.0, 0.0]) - back
    return directions / np.linalg.norm(directions, axis=-1, keepdims=True)


def pano_pixels(directions, pano_width, pano_height):
    """Where each direction falls in a 2:1 panorama (pano.py's frame), as float column and row."""
    longitude = np.arctan2(directions[..., 0], -directions[..., 2])
    latitude = np.arcsin(np.clip(directions[..., 1], -1, 1))
    column = (longitude / (2 * math.pi) + 0.5) * pano_width - 0.5
    row = (0.5 - latitude / math.pi) * pano_height - 0.5
    return column, row


def sampled_nearest(pano, column, row):
    """The panorama's nearest pixel at each place, wrapping round the sides."""
    height, width = pano.shape[:2]
    across = np.mod(np.round(column).astype(int), width)
    down = np.clip(np.round(row).astype(int), 0, height - 1)
    return pano[down, across]


def sampled_smooth(pano, column, row):
    """The panorama read between its four nearest pixels at each place, wrapping round the sides."""
    height, width = pano.shape[:2]
    left = np.floor(column).astype(int)
    top = np.floor(row).astype(int)
    share_across = (column - left)[..., None]
    share_down = (row - top)[..., None]
    left_column, right_column = np.mod(left, width), np.mod(left + 1, width)
    top_row, bottom_row = np.clip(top, 0, height - 1), np.clip(top + 1, 0, height - 1)
    upper = pano[top_row, left_column] * (1 - share_across) + pano[top_row, right_column] * share_across
    lower = pano[bottom_row, left_column] * (1 - share_across) + pano[bottom_row, right_column] * share_across
    return upper * (1 - share_down) + lower * share_down


def cut_view(pano, yaw_degrees, hfov_degrees, width, height, smooth=True):
    """One level view of a panorama (H x W x C, or H x W of metres read nearest)."""
    column, row = pano_pixels(rays(yaw_degrees, hfov_degrees, width, height), pano.shape[1], pano.shape[0])
    if not smooth or pano.ndim == 2:
        return sampled_nearest(pano, column, row)
    return sampled_smooth(pano.astype(np.float64), column, row)


def camera(spot, way, eye_m, hfov_degrees, width, height, source):
    """A view's camera as views.json records it."""
    return {"spot": spot, "way": way, "yaw_degrees": WAYS[way], "pitch_degrees": 0.0,
            "eye_m": eye_m, "hfov_degrees": hfov_degrees,
            "vfov_degrees": round(vertical_fov(hfov_degrees, width, height), 4),
            "width": width, "height": height, "source": str(source)}


def loaded(path):
    """A panorama as an array: a painting's RGB, or a depth .npy's metres."""
    if path.suffix == ".npy":
        return np.load(path)
    return np.asarray(Image.open(path).convert("RGB"))


def save_view(view, path):
    """A cut view written as a PNG, and as .npy too when it holds metres."""
    if view.ndim == 2:
        np.save(path.with_suffix(".npy"), view)
        finite = np.isfinite(view)
        scale = view[finite].max() if finite.any() else 1.0
        shade = np.where(finite, 1.0 - np.clip(view / scale, 0, 1), 0.0)
        Image.fromarray(np.round(shade * 255).astype(np.uint8), "L").save(path)
        return
    Image.fromarray(np.clip(np.round(view), 0, 255).astype(np.uint8), "RGB").save(path)


def record(out, cameras):
    """Merges the views' cameras into <out>/views.json, keyed '<spot>-<way>'."""
    known = out / "views.json"
    kept = json.loads(known.read_text()) if known.exists() else {}
    kept.update(cameras)
    known.write_text(json.dumps(kept, indent=1, sort_keys=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("pano", type=pathlib.Path)
    parser.add_argument("spot")
    parser.add_argument("--out", type=pathlib.Path, required=True)
    parser.add_argument("--ways", default=",".join(WAYS))
    parser.add_argument("--size", default=f"{WIDTH}x{HEIGHT}")
    parser.add_argument("--hfov", type=float, default=HFOV_DEGREES)
    parser.add_argument("--eye", type=float, default=EYE_M)
    options = parser.parse_args()
    width, height = (int(side) for side in options.size.split("x"))
    options.out.mkdir(parents=True, exist_ok=True)
    pano = loaded(options.pano)
    cameras = {}
    for way in options.ways.split(","):
        path = options.out / f"{options.spot}-{way}.png"
        save_view(cut_view(pano, WAYS[way], options.hfov, width, height), path)
        cameras[f"{options.spot}-{way}"] = camera(options.spot, way, options.eye, options.hfov,
                                                  width, height, options.pano)
        print(path, flush=True)
    record(options.out, cameras)


if __name__ == "__main__":
    sys.exit(main())
