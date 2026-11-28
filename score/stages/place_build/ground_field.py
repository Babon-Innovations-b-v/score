"""The ground field (`kit` piece `ground_field`, laid as algorithm/ground_field; 2099 #161, the owner on the pad:
"this smoke and terrain is shit", its palms left out for "there is no ground under them"): a place's shaped outside
ground as one closed heightfield solid in library surfaces. Its relief is the coast's (launch_kit.coast_heights: a
seeded shoreline, the sea bed sinking under the water, a shore band rising to its berm, hills rising inland with
ridges and gullies, every site [x, z, radius, height] levelled and eased into the land around it). Its cells are
`cell` metres, finer inside each `fine` box [x0, z0, x1, z1, cell] (the ground near the place, under what stands on
it). Every top face takes the part of the first of its `bands` whose limits it meets (`below` / `above` a height,
`steeper` / `gentler` than a slope in degrees; the last band takes the rest), each limit moved by one seeded patch
relief (`blend`: up to `height` metres and `slope` degrees either way), so two library surfaces meet in patches and
tongues, never along a contour line. The sides and bottom close the solid in the first band's part. Each part then
wears its library surface from `kit`'s looks."""
import numpy as np

from score.stages.place_build.cockpit_kit import piece, written
from score.stages.place_build.launch_kit import COAST_WAVES, coast_heights, seeded_waves

BAND_LIMITS = ("below", "above", "steeper", "gentler")  # a band's limits: heights in metres, slopes in degrees
PATCH = 120.0  # metres: the longest wave of the patch relief that moves the bands' limits (blend)
BOTTOM = 2.0  # metres the flat bottom lies under the field's lowest point


def axis(low, high, cell, fine):
    """The grid's lines from `low` to `high`, `cell` apart, and `step` apart inside each (start, end, step) of `fine`."""
    lines = [np.linspace(low, high, int(round((high - low) / cell)) + 1)]
    for start, end, step in fine:
        start, end = max(low, start), min(high, end)
        if end > start:
            lines.append(np.linspace(start, end, int(round((end - start) / step)) + 1))
    return np.unique(np.round(np.concatenate(lines), 4))


def checked_bands(bands):
    """The bands as given, refused (ValueError) when one has no part, a limit not in BAND_LIMITS, or the last has a
    limit (it must take every face the others leave)."""
    if not bands:
        raise ValueError("a ground field needs its bands (part and limits)")
    for band in bands:
        if not band.get("part"):
            raise ValueError(f"a band with no part: {band}")
        unknown = set(band) - {"part", *BAND_LIMITS}
        if unknown:
            raise ValueError(f"band {band['part']}: no limit {', '.join(sorted(unknown))} (limits are {', '.join(BAND_LIMITS)})")
    if set(bands[-1]) & set(BAND_LIMITS):
        raise ValueError(f"the last band ({bands[-1]['part']}) takes every face left: it has no limits")
    return bands


def banded(heights, slopes, patches, bands, blend):
    """Each face's band number: the first band whose limits its height (metres) and slope (degrees) meet, each limit
    moved by its patch value (-1..1) times `blend`'s height or slope."""
    lifted = patches * float(blend.get("height", 0.0))
    tilted = patches * float(blend.get("slope", 0.0))
    found = np.full(len(heights), -1)
    for number, band in enumerate(bands):
        meets = found < 0
        if "below" in band:
            meets &= heights < band["below"] + lifted
        if "above" in band:
            meets &= heights >= band["above"] + lifted
        if "steeper" in band:
            meets &= slopes >= band["steeper"] + tilted
        if "gentler" in band:
            meets &= slopes < band["gentler"] + tilted
        found[meets] = number
    return found


def closing(count_x, count_z, below, points):
    """The side walls round a grid of count_x by count_z top points (the bottom's points `below` after them), wound
    to face out from the grid's middle."""
    rim = (list(range(count_z)) + [column * count_z + count_z - 1 for column in range(1, count_x)]
           + [(count_x - 1) * count_z + row for row in range(count_z - 2, -1, -1)]
           + [column * count_z for column in range(count_x - 2, 0, -1)])
    sides = []
    for here, there in zip(rim, rim[1:] + rim[:1]):
        sides += [[here, there, there + below], [here, there + below, here + below]]
    sides = np.asarray(sides)
    corners = points[sides]
    normal = np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0])
    middle = points[:below].mean(axis=0)
    inward = np.einsum("ij,ij->i", normal[:, [0, 2]], (corners.mean(axis=1) - middle)[:, [0, 2]]) < 0
    sides[inward] = sides[inward][:, ::-1]
    return sides


def ground_field(wide=4000.0, deep=1500.0, sea=800.0, rise=60.0, shore=40.0, berm=2.5, depth=8.0, cell=20.0,
                 fine=(), sites=(), seed=0, bands=(), blend=None):
    """The ground field (the docstring's): its pieces, one a band's part (smooth), the first band's closing the solid."""
    bands = checked_bands([dict(band) for band in bands])
    blend = dict(blend or {})
    across = axis(-wide / 2, wide / 2, cell, [(box[0], box[2], box[4]) for box in fine])
    along = axis(-deep, sea, cell, [(box[1], box[3], box[4]) for box in fine])
    grid_x, grid_z = np.meshgrid(across, along, indexing="ij")
    heights, _ = coast_heights(grid_x, grid_z, wide, deep, sea, rise, shore, berm, depth,
                               [tuple(float(value) for value in site) for site in sites], seed)
    count_x, count_z = grid_x.shape
    top = np.column_stack([grid_x.ravel(), heights.ravel(), grid_z.ravel()])
    points = np.vstack([top, top * [1.0, 0.0, 1.0] + [0.0, float(heights.min()) - BOTTOM, 0.0]])
    below = len(top)
    cells = np.arange(count_x * count_z).reshape(count_x, count_z)[:-1, :-1].ravel()
    corners = np.column_stack([cells, cells + 1, cells + count_z + 1, cells + count_z])
    upward = np.vstack([corners[:, [0, 1, 2]], corners[:, [0, 2, 3]]])  # +z then +x under a corner: faces up
    faces = points[upward]
    normal = np.cross(faces[:, 1] - faces[:, 0], faces[:, 2] - faces[:, 0])
    slopes = np.degrees(np.arccos(np.clip(normal[:, 1] / np.linalg.norm(normal, axis=1), -1.0, 1.0)))
    middles = faces.mean(axis=1)
    patches = np.tanh(2.0 * seeded_waves(np.random.default_rng(seed + 17), COAST_WAVES, PATCH, 1.0)(
        middles[:, 0], middles[:, 2]))
    found = banded(middles[:, 1], slopes, patches, bands, blend)
    pieces = [piece(bands[0]["part"], points, np.vstack([upward[found == 0], upward[:, ::-1] + below,
                                                          closing(count_x, count_z, below, points)]), True)]
    for number, band in enumerate(bands[1:], start=1):
        if (found == number).any():
            pieces.append(piece(band["part"], points, upward[found == number], True))
    return pieces


KINDS = {"ground_field": ground_field}


def write(path, kind, sizes):
    """The piece of `kind` (KINDS) with its `sizes` written at `path` (cockpit_kit.written); its parts."""
    if kind not in KINDS:
        raise ValueError(f"no ground field piece {kind!r} (pieces are {', '.join(sorted(KINDS))})")
    return written(path, KINDS[kind](**sizes))
