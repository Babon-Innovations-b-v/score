"""The relief of a plan's terrain spots (design.spline, as this module's `spline` puts in its place), kept within their
heights (2026-11-12, wreck): a thin-plate spline through three spots is the flat plane through them, and wreck's
three, a shallow dip of about 1 m ((11.04, 12.54, -0.5), (8.14, 13.29, -1), (19.07, 13.29, -1)), gave a plane 33.7
degrees steep, kept at full height out to the farthest spot: ridges of 6.5 m and pits of 5 m round the place, and the
things laid on it faulted.

    shape = bounded.shaped(spots)   # [[x, y, height]] -> a function of [[x, y]] giving heights within the spots'

A dip (three spots, none above the floor) is no plane: each point takes the spots' heights weighed by the inverse
square of its distance to each (Shepard's), which never leaves their range and passes through every spot. Any other
spline is clipped to the spots' lowest and highest height, so it never rises or sinks past what the plan gives.

Apart from design.py so that only the rows that shape a relief take it into their keys: terrain and ground-fit (ROWS)
declare it as a file of theirs (FILES, added in the framework's table, score/stages/__init__.py, which imports it and
so installs it in every process that runs a row). design.py is read by the assembly (ground_finish) and prepare too,
and an edit there moved 62 paid rows (settle, sim body, peels, body faces, light passes, ...) that never shape a
relief. Importing this module puts `spline` in design.spline's place (`install`), once a process.
"""
import numpy as np

from score.stages.terrain import design

# The rows that shape a relief from a plan's spots, and the file each declares so its key takes this module in.
ROWS = ("terrain", "ground-fit")
FILES = {"bounded relief": "{repo}/score/stages/terrain/bounded.py"}


def is_dip(spots):
    """Whether three distinct spots [[x, y, height]] mean a dip: none stands above the floor (height 0)."""
    return len(spots) == 3 and bool((spots[:, 2] <= 0.0).all())


def weighed(spots):
    """The spots' heights at points [[x, y]], each spot weighed by the inverse square of its distance (its own height
    at a spot)."""
    def shape(points):
        apart = np.atleast_2d(points)[:, None, :] - spots[None, :, :2]
        weights = 1.0 / np.maximum((apart ** 2).sum(axis=2), 1e-12)
        return (weights * spots[:, 2]).sum(axis=1) / weights.sum(axis=1)
    return shape


def clipped(spots):
    """The thin-plate spline through the spots, clipped to their lowest and highest height."""
    from scipy.interpolate import RBFInterpolator
    spline = RBFInterpolator(spots[:, :2], spots[:, 2], kernel="thin_plate_spline", smoothing=1e-3)
    low, high = float(spots[:, 2].min()), float(spots[:, 2].max())
    return lambda points: np.clip(spline(np.atleast_2d(points)), low, high)


def shaped(spots):
    """The shape of distinct spots [[x, y, height]] of differing heights: weighed for a dip, else clipped."""
    return weighed(spots) if is_dip(spots) else clipped(spots)


def spline(source):
    """The relief of a source's spots in its plan metres (design.spline's, its shape `shaped`): a function of [[x, y]]
    giving heights, or None when its spots give no relief (fewer than three, or all one height: then each spot's
    height is the whole relief)."""
    spots = np.asarray(source["spots"], dtype=float)
    spots = spots[np.unique(spots[:, :2], axis=0, return_index=True)[1]]
    if len(spots) < 3 or np.ptp(spots[:, 2]) < 1e-3:
        return None
    shape = shaped(spots)
    middle = np.asarray(source["middle"])
    reach = float(np.hypot(*(spots[:, :2] - middle).T).max()) or 1.0

    def relief(points):
        points = np.atleast_2d(points)
        far = np.hypot(*(points - middle).T)
        fade = (design.FADE_PAST * reach - far) / ((design.FADE_PAST - 1.0) * reach)
        return shape(points) * np.clip(fade, 0.0, 1.0)
    return relief


def install():
    """Put `spline` in design.spline's place, so design.reliefs shapes every source with it."""
    design.spline = spline


install()
