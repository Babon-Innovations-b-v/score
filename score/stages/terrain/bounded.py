"""The relief of a plan's terrain spots (design.spline, as this module's `spline` puts in its place), kept within their
heights (2026-11-12, wreck): a thin-plate spline through three spots is the flat plane through them, and wreck's
three, a shallow dip of about 1 m ((11.04, 12.54, -0.5), (8.14, 13.29, -1), (19.07, 13.29, -1)), gave a plane 33.7
degrees steep, kept at full height out to the farthest spot: ridges of 6.5 m and pits of 5 m round the place, and the
things laid on it faulted.

    shape = bounded.dented(spots)   # [[x, y, height <= 0]] -> a function of [[x, y]]: each spot a dent, else 0
    shape = bounded.shaped(spots)   # [[x, y, height]] -> a function of [[x, y]] giving heights within the spots'

Spots none above the floor are dents (`dented`), each local to its spot (2026-11-12, wreck): its plan's notes lay
"the forward section resting in a 2.5 m dent 30 cm deep where it struck, the two pressure spheres in shallow dents".
One dip weighed over all three spots (Shepard's, the first fix) still ran the ground 0.4 to 0.8 m across the place and
faded past the farthest spot inside it: its rocket halves, lander, tank, cylindrical part and gold foil stood on the
slope. Each spot is now a round dent its height deep, flat to DENT_FLOOR from it and reaching DENT_REACH, and the
ground is the floor outside the dents. Any other spline is clipped to the spots' lowest and highest height, so it
never rises or sinks past what the plan gives.

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


# How far, metres, a dent reaches from its spot (wreck's plan notes give its rocket's dent as 2.5 m across), and how
# far its floor, flat at the spot's height: wreck's spherical tank, 1.5 m round, leaned 6.4 to 7.9 degrees on the
# faces of a bowl, and 3.1 on a 1.5 m floor, as the place's near grid (0.5 m apart) draws them: every triangle of
# that grid within 0.3 m of the spot has its corners on a 2 m floor.
DENT_REACH = 1.25
DENT_FLOOR = 1.0


def is_dented(spots):
    """Whether spots [[x, y, height]] mean dents: none stands above the floor (height 0)."""
    return bool((spots[:, 2] <= 0.0).all())


def dented(spots):
    """The ground of dent spots at points [[x, y]]: each spot the middle of a round dent its height deep, flat to
    DENT_FLOOR from it and rising straight to the floor (0) at DENT_REACH; the deeper dent where two meet, the floor
    elsewhere."""
    def shape(points):
        points = np.atleast_2d(np.asarray(points, dtype=float))
        apart = np.hypot(points[:, None, 0] - spots[None, :, 0], points[:, None, 1] - spots[None, :, 1])
        rise = np.clip((apart - DENT_FLOOR) / (DENT_REACH - DENT_FLOOR), 0.0, 1.0)
        return (spots[None, :, 2] * (1.0 - rise)).min(axis=1)
    return shape


def clipped(spots):
    """The thin-plate spline through the spots, clipped to their lowest and highest height."""
    from scipy.interpolate import RBFInterpolator
    spline = RBFInterpolator(spots[:, :2], spots[:, 2], kernel="thin_plate_spline", smoothing=1e-3)
    low, high = float(spots[:, 2].min()), float(spots[:, 2].max())
    return lambda points: np.clip(spline(np.atleast_2d(points)), low, high)


def shaped(spots):
    """The shape of distinct spots [[x, y, height]] of differing heights, none of them dents: clipped."""
    return clipped(spots)


def spline(source):
    """The relief of a source's spots in its plan metres (design.spline's, its shape `shaped`): a function of [[x, y]]
    giving heights, or None when its spots give no relief (fewer than three, or all one height: then each spot's
    height is the whole relief)."""
    spots = np.asarray(source["spots"], dtype=float)
    spots = spots[np.unique(spots[:, :2], axis=0, return_index=True)[1]]
    if is_dented(spots):
        return dented(spots)
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
