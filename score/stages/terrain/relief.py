"""The fine relief a ground's diorama picture gives its heights: the picture is drawn straight down over the plan, its
relative depth read by Depth Anything V2 Small (larger is nearer, so higher), and only its fine part kept (the depth
less its own smoothing over the plan's `fine` metres), turned to run with the plan's large shape, at the plan's
`amplitude` RMS metres, softened on held flats and paths to the plan's `quiet` share. The picture's colours are never
kept: surfaces come from the library (zones.py).

Each candidate picture is first registered on the plan, measured: a picture model may draw the square smaller than
its frame or off its middle, so the zoom and shift under which its depth's large part best follows the plan's large
shape is found (`registration`). The candidate that then follows best is taken (the largest correlation, by its
size), never judged by eye; its sign turns the relief (a depth that runs against the plan's shape reads bright as
low, as the game's skins did).
"""
import numpy as np
from scipy import ndimage

# The smoothing, in multiples of `fine`, over which the depth's large part is compared with the plan's shape, and the
# side in pixels it is compared at.
COMPARE = 4.0
COARSE = 192
# The registrations tried: the picture's square drawn this share of the frame across (a picture model may leave a
# margin round it), shifted by these shares of the side.
REGISTER_SCALES = tuple(round(0.7 + 0.02 * step, 2) for step in range(16))
REGISTER_SHIFTS = (-0.04, -0.02, 0.0, 0.02, 0.04)
# The plan's outer band left out of the comparison, a share of its side each way: a picture's margin, smoothed, bleeds
# into its square's edge.
INNER_EDGE = 0.1


def detrended(field):
    """A field less its best-fitting plane."""
    rows, columns = np.indices(field.shape)
    design = np.stack([rows.ravel(), columns.ravel(), np.ones(field.size)], axis=1)
    solution, *_ = np.linalg.lstsq(design, field.ravel(), rcond=None)
    return field - (design @ solution).reshape(field.shape)


def compared_at(depth, large, side, fine, size=COARSE):
    """The depth's large part and the plan's shape at `size` pixels a side, smoothed over COMPARE x fine metres."""
    sigma = COMPARE * fine / (side / size)
    first = ndimage.gaussian_filter(ndimage.zoom(depth, size / depth.shape[0], order=1), sigma)
    second = ndimage.gaussian_filter(ndimage.zoom(large, size / large.shape[0], order=1), sigma)
    return first, second


def warped(field, scale, shift_x, shift_z, size):
    """A square field seen through a centred zoom of `scale` (the picture's square drawn `scale` of the frame across,
    a margin round it) and a shift (shares of the side), at `size` pixels: what of the field lies on the plan."""
    middle = (field.shape[0] - 1) / 2
    plan_at = (np.arange(size) / (size - 1) - 0.5) * (field.shape[0] - 1)
    rows = middle + (plan_at[:, None] * scale + shift_z * field.shape[0]) * np.ones((1, size))
    columns = middle + (plan_at[None, :] * scale + shift_x * field.shape[0]) * np.ones((size, 1))
    return ndimage.map_coordinates(field, [rows, columns], order=1, mode="nearest")


def registration(depth, large, side, fine):
    """Where the picture lies on the plan, measured: the centred zoom and shift (REGISTER_SCALES, REGISTER_SHIFTS)
    under which the depth's large part best follows the plan's shape inside its outer band (the largest correlation
    by its size, less their planes), and that correlation."""
    first, second = compared_at(depth, large, side, fine)
    edge = int(COARSE * INNER_EDGE)
    inner = (slice(edge, COARSE - edge), slice(edge, COARSE - edge))
    target = detrended(second[inner]).ravel()
    best = (1.0, 0.0, 0.0, 0.0)
    for scale in REGISTER_SCALES:
        for shift_x in REGISTER_SHIFTS:
            for shift_z in REGISTER_SHIFTS:
                seen = detrended(warped(first, scale, shift_x, shift_z, COARSE)[inner]).ravel()
                found = float(np.corrcoef(seen, target)[0, 1])
                if abs(found) > abs(best[3]):
                    best = (scale, shift_x, shift_z, found)
    return {"scale": best[0], "shift_x": best[1], "shift_z": best[2], "correlation": round(best[3], 4)}


def chosen(depths, large, side, fine):
    """The candidate whose registered depth follows the plan best: (its index, every candidate's registration)."""
    found = [registration(depth, large, side, fine) for depth in depths]
    return int(np.argmax([abs(each["correlation"]) for each in found])), found


def on_plan(depth, placed):
    """A depth map brought onto the plan by its registration, at its own size."""
    return warped(depth, placed["scale"], placed["shift_x"], placed["shift_z"], depth.shape[0])


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
