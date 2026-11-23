"""The render beside the concept, for the agent (a vision model reading both) to choose the next correction, and a
few plain measures of how far apart they are. Nothing here judges: the agent decides.

    compare(folder) -> {"picture": <folder>/compare.png, "layout_iou", "objects": [...], "colour": {...}}

compare.png: the concept, the render, and the concept dimmed with the render's silhouette in red over it and each
concept object's outline in green (where red sits outside green, the render has something the concept has not; green
with no red, an object the render lacks).
- layout_iou: the render's silhouette (usd_views' mask) against the union of the concept's object masks
  (objects.json, SAM 3's); null when the concept was not split.
- objects: each concept object's word, box and `covered` (the share of its mask the render's silhouette covers),
  least covered first.
- colour: the mean CIE76 difference of the two pictures over a GRID of cells, and each cell's, row by row.
- lightness: the mean CIE L* (0 black .. 100 white) of the concept and of the render over the render's silhouette,
  so a place lit or exposed far brighter than its concept (the 2099 judge, 2026-11-23: the engineroom's gunmetal
  palette read near white under its lamps) shows as a number, apart from its palette's colours.
"""
import json
import pathlib

import numpy as np

from score.stages import place_build

GRID = (4, 4)  # columns, rows of the colour cells
PANEL = 512  # each panel's pixels across in compare.png
DIM = 0.45  # the concept's brightness under the overlay


def picture(path, size):
    """An RGB picture at `size` (an RGBA one over black)."""
    from PIL import Image
    opened = Image.open(path)
    if opened.mode == "RGBA":
        flat = Image.new("RGB", opened.size, (0, 0, 0))
        flat.paste(opened, mask=opened.getchannel("A"))
        opened = flat
    return opened.convert("RGB").resize(size, Image.BILINEAR)


def rgb(shown):
    """A picture's pixels as 0..1 floats."""
    return np.asarray(shown, dtype=float) / 255.0


def lab(shown):
    """A picture's pixels in CIE Lab, through Pillow's colour management (sRGB to Lab, L 0..100)."""
    from PIL import ImageCms
    turned = ImageCms.applyTransform(shown, ImageCms.buildTransform(
        ImageCms.createProfile("sRGB"), ImageCms.createProfile("LAB"), "RGB", "LAB"))
    values = np.asarray(turned)
    signed = values.view(np.int8).astype(float)  # a and b come as signed bytes
    return np.stack([values[..., 0] * 100.0 / 255.0, signed[..., 1], signed[..., 2]], -1)


def mask(path, size):
    """A mask picture as booleans at `size`: its alpha where it has one, else its brightness."""
    from PIL import Image
    opened = Image.open(path)
    channel = opened.getchannel("A") if opened.mode in ("RGBA", "LA") else opened.convert("L")
    return np.asarray(channel.resize(size, Image.NEAREST)) > 127


def concept_objects(folder):
    """objects.json's objects that have a mask, or [] when the concept was not split."""
    found = pathlib.Path(folder) / "objects.json"
    if not found.exists():
        return []
    return [item for item in json.loads(found.read_text()) if item.get("mask") and pathlib.Path(item["mask"]).exists()]


def iou(first, second):
    union = (first | second).sum()
    return round(float((first & second).sum() / union), 3) if union else None


def coverage(objects, masks, silhouette):
    """Each object's word, box and covered share, least covered first."""
    rows = [{"word": item["word"], "box": item["box"],
             "covered": round(float((shape & silhouette).sum() / max(shape.sum(), 1)), 3)}
            for item, shape in zip(objects, masks)]
    return sorted(rows, key=lambda row: row["covered"])


def colour_cells(concept, render, grid=GRID):
    """The mean CIE76 difference over the picture and in each grid cell (rows of columns)."""
    difference = np.linalg.norm(lab(concept) - lab(render), axis=-1)
    tall, wide = difference.shape
    cells = [[round(float(difference[row * tall // grid[1]:(row + 1) * tall // grid[1],
                                     column * wide // grid[0]:(column + 1) * wide // grid[0]].mean()), 1)
              for column in range(grid[0])] for row in range(grid[1])]
    return {"mean": round(float(difference.mean()), 1), "cells": cells}


def lightness(concept, render, silhouette):
    """The mean L* of the concept and of the render over the silhouette (the whole picture when it is empty)."""
    where = silhouette if silhouette.any() else np.ones_like(silhouette)
    return {"concept": round(float(lab(concept)[..., 0][where].mean()), 1),
            "render": round(float(lab(render)[..., 0][where].mean()), 1)}


def overlay(concept, silhouette, masks):
    """The concept dimmed, the render's silhouette tinted red over it, each object's outline green."""
    shown = concept * DIM
    shown[silhouette] = shown[silhouette] * 0.5 + np.array([0.5, 0.0, 0.0])
    for shape in masks:
        edge = shape & ~(np.roll(shape, 1, 0) & np.roll(shape, -1, 0) & np.roll(shape, 1, 1) & np.roll(shape, -1, 1))
        shown[edge] = [0.1, 1.0, 0.2]
    return shown


def side_by_side(panels, path):
    from PIL import Image
    joined = np.concatenate(panels, axis=1)
    Image.fromarray((np.clip(joined, 0, 1) * 255).astype(np.uint8)).save(path)


def compare(folder):
    """The side-by-side picture and the measures of the last render against the concept."""
    folder = pathlib.Path(folder)
    for needed in ("render.png", "render-mask.png"):
        if not (folder / needed).exists():
            raise place_build.Refused(f"{folder / needed} is missing: render first")
    wide, tall = place_build.record_of(folder)["size"]
    size = (PANEL, max(1, round(PANEL * tall / wide)))
    concept, render = picture(folder / "concept.png", size), picture(folder / "render.png", size)
    silhouette = mask(folder / "render-mask.png", size)
    objects = concept_objects(folder)
    masks = [mask(item["mask"], size) for item in objects]
    union = np.logical_or.reduce(masks) if masks else None
    side_by_side([rgb(concept), rgb(render), overlay(rgb(concept), silhouette, masks)], folder / "compare.png")
    return {"picture": str(folder / "compare.png"), "layout_iou": iou(union, silhouette) if masks else None,
            "objects": coverage(objects, masks, silhouette), "colour": colour_cells(concept, render),
            "lightness": lightness(concept, render, silhouette)}
