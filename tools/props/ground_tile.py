"""A drawn picture of ground made into a tile that repeats without a seam, for Earth's ground (#55).

The picture model draws the ground straight down but not as a repeating tile, so each edge is
blended into the opposite one. The contrast can be pulled down too, because a strong pattern
repeated across a square reads as a chessboard from the balcony (the overseer's note, 2026-09-30).

    ~/.farm-factory-props/env/bin/python tools/props/ground_tile.py <picture.png> <tile.png> [--contrast 0.6]

writes a 1024 px square tile.
"""
import argparse

import numpy as np
from PIL import Image

SIDE = 1024
# How many pixels of the picture's own size each edge is blended over.
BLEND = 48


def seamless(picture):
    """The picture with each edge blended into the opposite one, BLEND pixels smaller each way."""
    pixels = np.asarray(picture.convert("RGB")).astype(np.float32)
    ramp_shape = {0: (-1, 1, 1), 1: (1, -1, 1)}
    for axis in (0, 1):
        ramp = np.linspace(0.0, 1.0, BLEND).reshape(ramp_shape[axis])
        head = np.take(pixels, range(BLEND), axis=axis)
        tail = np.take(pixels, range(pixels.shape[axis] - BLEND, pixels.shape[axis]), axis=axis)
        pixels = np.take(pixels, range(pixels.shape[axis] - BLEND), axis=axis)
        blended = head * ramp + tail * (1.0 - ramp)
        pixels = np.concatenate([blended, np.take(pixels, range(BLEND, pixels.shape[axis]), axis=axis)], axis=axis)
    return pixels


def softened(pixels, contrast):
    """The pixels pulled towards their own mean colour, contrast 1 leaving them as they were."""
    mean = pixels.mean(axis=(0, 1))
    return mean + (pixels - mean) * contrast


def ground_tile(picture, contrast=1.0):
    """A SIDE square tile from a drawn picture of ground."""
    pixels = softened(seamless(picture), contrast)
    return Image.fromarray(pixels.clip(0, 255).astype(np.uint8)).resize((SIDE, SIDE), Image.LANCZOS)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("picture")
    parser.add_argument("tile")
    parser.add_argument("--contrast", type=float, default=1.0, help="1 keeps the picture's own, lower softens it")
    arguments = parser.parse_args()
    ground_tile(Image.open(arguments.picture), arguments.contrast).save(arguments.tile)
    print(arguments.tile)


if __name__ == "__main__":
    main()
