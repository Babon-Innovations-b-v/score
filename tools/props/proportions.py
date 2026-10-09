"""Check a finished model against its inventory row's size before it goes into the game, and say how to fit it.

    ~/.farm-factory-props/env/bin/python tools/props/proportions.py <model.glb> <wide> <deep> <tall> [--flat]

A Pixal3D model is made from one picture, so it guesses the depth it cannot see (the owner, 2026-10-05: "the lockers
got really long"). Two checks, on the model as finished (upright, +Y up, its longest ground side along Z by
glb_file.squared):

- **Upright**: an item whose row is taller than it is wide and deep must have its tallest side up, and one wider than
  tall (a board) must not stand on end; one standing wrong is re-finished (pixal.py --long stands it on its longest
  side), which needs no model.
- **Proportions**: the model's sides are matched to the row's (tall to Y; the footprint's longer side to the row's
  longer of wide and deep). The per-axis scales that would fit it are compared: a spread over SPREAD (20%) means the
  model's own shape is wrong, and it is remade, never stretched into shape. Within it, the fit is the per-axis scale.
  `--flat` is for something that hangs on a wall (a board): only wide and tall are checked, its depth is its own.

The pictures it was made from say what shape it should have, so `--front <cut-out>` and `--side <side view>` add a
third check: the model's own width to height and depth to height against the pictures' (each picture's object box,
the front from its alpha, the side from its studio backdrop, its width taken above the floor shadow). A model that
matches its pictures but not its row means the row's size is the one to look at; one that matches neither is remade.

Prints one JSON line: {"upright", "spread", "flag", "scale": [x, y, z], "sides": ...}. Plain numpy, scipy and trimesh.
"""
import argparse
import json

import numpy as np

SPREAD = 0.20


def extents(path):
    """The finished model's box sides along X, Y (up) and Z, in its own units."""
    import trimesh
    return np.asarray(trimesh.load(path, force="mesh").extents, dtype=np.float64)


def check(sides, size, flat=False):
    """The checks for a model with box sides `sides` (x, y up, z) against a row's (wide, deep, tall)."""
    sides = np.asarray(sides, dtype=np.float64)
    wide, deep, tall = (float(value) for value in size)
    tall_row = tall >= max(wide, deep)
    upright = tall_row == (sides[1] >= max(sides[0], sides[2]) * 0.999)
    longer_on_x = sides[0] >= sides[2]
    ground = (max(wide, deep), min(wide, deep))
    target = np.zeros(3)
    target[1] = tall
    target[0], target[2] = (ground[0], ground[1]) if longer_on_x else (ground[1], ground[0])
    scale = target / np.maximum(sides, 1e-9)
    measured = scale
    if flat:
        thin = 0 if sides[0] < sides[2] else 2
        scale[thin] = float(np.mean(np.delete(scale, thin)))
        target[thin] = sides[thin] * scale[thin]
        measured = np.delete(scale, thin)
    spread = float(measured.max() / measured.min() - 1.0)
    return {"upright": bool(upright), "spread": round(spread, 3), "flag": (not upright) or spread > SPREAD,
            "scale": [round(float(value), 4) for value in scale], "sides": [round(float(value), 4) for value in sides],
            "target": [round(float(value), 4) for value in target]}


def picture_box(path, backdrop=22.0, band=(0.05, 0.75)):
    """Width and height of the object in a picture: its alpha's box when it has one, else backdrop_mask's."""
    from PIL import Image
    picture = Image.open(path)
    if picture.mode == "RGBA" and np.asarray(picture)[..., 3].min() < 128:
        mask = np.asarray(picture)[..., 3] > 128
        rows, columns = np.nonzero(mask)
        return float(columns.max() - columns.min() + 1), float(rows.max() - rows.min() + 1)
    mask = backdrop_mask(np.asarray(picture.convert("RGB"), dtype=np.float32), backdrop)
    rows = np.nonzero(mask.any(axis=1))[0]
    height = rows.max() - rows.min() + 1
    above_shadow = mask[rows.min() + int(band[0] * height):rows.min() + int(band[1] * height)]
    columns = np.nonzero(above_shadow.any(axis=0))[0]
    return float(columns.max() - columns.min() + 1), float(height)


def backdrop_mask(pixels, backdrop):
    """The biggest blob that differs from a studio backdrop. The backdrop is lit unevenly, so each row's is the line
    between that row's left and right edges; the floor shadow beside the object is left to picture_box's band, which
    measures the width only above it."""
    from scipy import ndimage
    width = pixels.shape[1]
    left = np.median(pixels[:, :24], axis=1)
    right = np.median(pixels[:, -24:], axis=1)
    across = np.linspace(0.0, 1.0, width)[None, :, None]
    plain = left[:, None, :] * (1.0 - across) + right[:, None, :] * across
    mask = ndimage.binary_opening(np.linalg.norm(pixels - plain, axis=-1) > backdrop, iterations=3)
    labels, count = ndimage.label(mask)
    sizes = ndimage.sum(mask, labels, range(1, count + 1))
    return labels == int(np.argmax(sizes)) + 1


def against_pictures(sides, front=None, side=None):
    """The model's width:height and depth:height against its front and side pictures', as their ratio (1 = same)."""
    sides = np.asarray(sides, dtype=np.float64)
    wide, deep = (max(sides[0], sides[2]), min(sides[0], sides[2]))
    found = {}
    if front:
        width, height = picture_box(front)
        found["front_ratio"] = round(float((wide / sides[1]) / (width / height)), 3)
    if side:
        width, height = picture_box(side)
        found["side_ratio"] = round(float((deep / sides[1]) / (width / height)), 3)
    found["matches_pictures"] = all(abs(value - 1.0) <= SPREAD for value in found.values())
    return found


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("model")
    parser.add_argument("wide", type=float)
    parser.add_argument("deep", type=float)
    parser.add_argument("tall", type=float)
    parser.add_argument("--flat", action="store_true", help="hangs on a wall: its depth is its own")
    parser.add_argument("--front", help="the cut-out front picture it was made from")
    parser.add_argument("--side", help="a side view of the same object")
    options = parser.parse_args()
    sides = extents(options.model)
    found = check(sides, (options.wide, options.deep, options.tall), options.flat)
    if options.front or options.side:
        found.update(against_pictures(sides, options.front, options.side))
    print(json.dumps(found))


if __name__ == "__main__":
    main()
