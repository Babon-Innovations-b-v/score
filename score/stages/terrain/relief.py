"""The fine relief a ground's diorama picture gives its heights: the picture is drawn straight down over the plan, its
relative depth read by Depth Anything V2 Small (larger is nearer, so higher), and only its fine part kept (the depth
less its own smoothing over the plan's `fine` metres), turned to run with the plan's large shape, at the plan's
`amplitude` RMS metres, softened on held flats and paths to the plan's `quiet` share. The picture's colours are never
kept: surfaces come from the library (zones.py).

Of a ground's candidate pictures the one whose smoothed depth follows the plan's large shape best is taken (the
largest correlation, by its size), measured, never judged by eye; its sign turns the relief (a depth that runs
against the plan's shape reads bright as low, as the game's skins did).
"""
import numpy as np
from scipy import ndimage

# The smoothing, in multiples of `fine`, over which the depth's large part is compared with the plan's shape.
COMPARE = 4.0


def detrended(field):
    """A field less its best-fitting plane."""
    rows, columns = np.indices(field.shape)
    design = np.stack([rows.ravel(), columns.ravel(), np.ones(field.size)], axis=1)
    solution, *_ = np.linalg.lstsq(design, field.ravel(), rcond=None)
    return field - (design @ solution).reshape(field.shape)


def agreement(depth, large, side, fine):
    """The correlation of a depth map's large part with the plan's large shape (both at the depth's size, smoothed
    over COMPARE x fine metres, less their planes)."""
    pixel = side / depth.shape[0]
    shape = ndimage.zoom(large, depth.shape[0] / large.shape[0], order=1)
    first = detrended(ndimage.gaussian_filter(depth, COMPARE * fine / pixel))
    second = detrended(ndimage.gaussian_filter(shape, COMPARE * fine / pixel))
    return float(np.corrcoef(first.ravel(), second.ravel())[0, 1])


def chosen(depths, large, side, fine):
    """The candidate whose depth follows the plan best: (its index, every candidate's correlation)."""
    found = [agreement(depth, large, side, fine) for depth in depths]
    return int(np.argmax(np.abs(found))), found


def fine_part(depth, side, fine, sign, points):
    """A depth map's fine part at the plan's grid, turned by `sign`, at unit RMS."""
    pixel = side / depth.shape[0]
    part = depth - ndimage.gaussian_filter(depth, fine / pixel)
    part = ndimage.zoom(part, points / depth.shape[0], order=1) * sign
    return part / (part.std() + 1e-9)


def relief(shaped, record, depth, sign):
    """The relief laid over the plan's large shape: the fine part at the plan's amplitude (measured as RMS where it
    applies), its share on flats and paths the plan's `quiet`, and only where the plan's `only` landform stands
    higher than its `over` when it names one; clipped at four times the amplitude."""
    settings = record["relief"]
    grid = shaped.grid
    part = fine_part(depth, grid.side, settings["fine"], sign, grid.points)
    where = np.ones_like(part)
    only = settings.get("only")
    if only:
        where = np.clip(shaped.masks[only["landform"]] / only["over"], 0.0, 1.0)
    applied = where > 0.5
    rms = part[applied].std() if applied.any() else 1.0
    part = part / (rms + 1e-9) * settings["amplitude"]
    quiet = np.clip(shaped.held + shaped.on_path, 0.0, 1.0)
    part = part * (1.0 - quiet * (1.0 - settings["quiet"])) * where
    return np.clip(part, -4 * settings["amplitude"], 4 * settings["amplitude"])
