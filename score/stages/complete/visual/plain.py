"""Plain regions of a picture: the parts drawn in one flat colour with no detail in them, as an untextured plane or
floor reads in a render.

The picture is cut into CELL-pixel cells. A cell is plain when its fine detail (the mean step between the picture and
itself blurred by BLUR pixels) is under DETAIL_MOST and it is lighter than DARKEST (a black sky is not a surface).
Plain cells side by side whose mean colours differ by less than COLOUR_STEP join one region.

    regions = plain.regions(image)     # [{"cells": bool grid, "share", "colour", "across", "down"}], largest first
"""
import numpy as np
from scipy import ndimage

CELL = 10  # pixels at frames.SIZE: a 32 by 18 grid
BLUR = 1.5
DETAIL_MOST = 0.006  # mean step, 0 to 1, under which a cell holds no texture
DARKEST = 0.08  # mean lightness under which a cell is sky or shadow, not judged
COLOUR_STEP = 0.05  # the largest mean colour step between two cells of one region


def cell_means(values, cell=CELL):
    """The mean of each cell of a (tall, wide, ...) array whose sides are whole cells."""
    tall, wide = values.shape[0] // cell, values.shape[1] // cell
    cut = values[:tall * cell, :wide * cell]
    return cut.reshape(tall, cell, wide, cell, *values.shape[2:]).mean(axis=(1, 3))


def cell_detail(image):
    """Each cell's fine detail: the mean step between the picture's lightness and itself blurred."""
    lightness = np.asarray(image.convert("L"), dtype=float) / 255
    return cell_means(np.abs(lightness - ndimage.gaussian_filter(lightness, BLUR)))


def cell_colours(image):
    """Each cell's mean colour, 0 to 1."""
    return cell_means(np.asarray(image.convert("RGB"), dtype=float) / 255)


def plain_cells(detail, colours):
    """The cells with no detail that are not dark."""
    return (detail < DETAIL_MOST) & (colours.mean(axis=2) > DARKEST)


def grown(start, plain, colours, taken):
    """The cells of one region grown from a start cell over plain neighbours of near colour."""
    region = np.zeros(plain.shape, dtype=bool)
    waiting = [start]
    region[start] = taken[start] = True
    while waiting:
        row, column = waiting.pop()
        for step_row, step_column in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            near = (row + step_row, column + step_column)
            if not (0 <= near[0] < plain.shape[0] and 0 <= near[1] < plain.shape[1]):
                continue
            if taken[near] or not plain[near]:
                continue
            if np.abs(colours[near] - colours[row, column]).max() >= COLOUR_STEP:
                continue
            region[near] = taken[near] = True
            waiting.append(near)
    return region


def described(region, colours):
    """A region's share of the picture, its mean colour and how far across and down it reaches (0 to 1)."""
    columns, rows = np.flatnonzero(region.any(axis=0)), np.flatnonzero(region.any(axis=1))
    return {"cells": region, "share": float(region.mean()),
            "colour": [round(float(value), 3) for value in colours[region].mean(axis=0)],
            "across": float((columns.max() - columns.min() + 1) / region.shape[1]),
            "down": float((rows.max() - rows.min() + 1) / region.shape[0]),
            "top": int(rows.min()), "bottom": int(rows.max())}


def regions(image):
    """Every plain region of a picture, largest first."""
    colours = cell_colours(image)
    plain = plain_cells(cell_detail(image), colours)
    taken = np.zeros(plain.shape, dtype=bool)
    found = []
    for start in zip(*np.nonzero(plain)):
        if not taken[start]:
            found.append(described(grown(start, plain, colours, taken), colours))
    return sorted(found, key=lambda region: -region["share"])
