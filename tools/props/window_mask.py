"""A window mask for a generated building: white where a pane is, black elsewhere.

The light session lights a building's windows at night from this mask (#113), because a generated
building is one mesh with one baked colour texture and its windows are only pixels in it. Keying the
glow off the colour itself would also light blue cladding and reflected sky, so each building gets
its own mask instead, in the colour texture's own UVs.

A pane is a small patch clearly darker than the wall round it. The seams between the texture's
pieces are dark too, but long and thin, so any patch longer than a pane is dropped.

    ~/.farm-factory-props/env/bin/python tools/props/window_mask.py <building.glb> [...]

writes <building>_windows.png beside each model, 512 px square.
"""
import io
import pathlib
import sys

import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

import glb_file

SIDE = 512
# How far round a pixel the wall it is compared with reaches, and how much darker a pane must be,
# both at the texture's own size, where a pane is a few pixels across.
WALL_REACH = 5
DARKER_BY = 0.07
# A patch longer than this many pixels of the small mask is a seam between texture pieces.
LONGEST_PANE = 8
# How much of a small pixel has to be pane for the small pixel to count as one.
PANE_SHARE = 40


def colour_texture(path):
    """The model's base colour texture, in grey."""
    document, views = glb_file.read(path)
    material = document["materials"][0]
    texture = document["textures"][material["pbrMetallicRoughness"]["baseColorTexture"]["index"]]
    image = document["images"][texture["source"]]
    return Image.open(io.BytesIO(views[image["bufferView"]])).convert("L")


def darker_than_the_wall(grey):
    """Every pixel clearly darker than the wall round it, stray single pixels left out."""
    wall = np.asarray(grey.filter(ImageFilter.BoxBlur(WALL_REACH)), dtype=np.float32) / 255.0
    value = np.asarray(grey, dtype=np.float32) / 255.0
    dark = Image.fromarray(((value < wall - DARKER_BY) * 255).astype(np.uint8))
    return dark.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.MaxFilter(3))


def shrunk(dark):
    """The dark pixels at SIDE, a small pixel counting as dark when enough of what it covers was."""
    small = dark.filter(ImageFilter.MaxFilter(3)).resize((SIDE, SIDE), Image.BOX)
    return np.asarray(small) > PANE_SHARE


def without_seams(white):
    """The mask with every patch too long to be a pane taken out."""
    white = white.copy()
    patches, _count = ndimage.label(white)
    for number, box in enumerate(ndimage.find_objects(patches), start=1):
        if max(box[0].stop - box[0].start, box[1].stop - box[1].start) > LONGEST_PANE:
            white[box][patches[box] == number] = False
    return white


def window_mask(grey):
    """The mask for a colour texture in grey, as a black and white picture SIDE square."""
    white = without_seams(shrunk(darker_than_the_wall(grey)))
    return Image.fromarray((white * 255).astype(np.uint8))


def main():
    for model in map(pathlib.Path, sys.argv[1:]):
        out = model.with_name(model.stem + "_windows.png")
        mask = window_mask(colour_texture(model))
        mask.save(out)
        print(out, f"{np.asarray(mask).mean() / 255:.1%} window")


if __name__ == "__main__":
    main()
