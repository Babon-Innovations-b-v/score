"""Level 2 made well posed (#70): the constants' data curvature, the Schur complement of the data Jacobian on the told
constants' columns with every frame's coordinates eliminated (each frame's rows read only its own coordinates), has
directions the data barely tells (a scapula's y, a lumbar level's z: the CPU ended 0.7 mm apart from nudged starts at
equal cost, 2026-10-30), along which a cold and a warm solve stop at different points. One rule lifts each of its
eigenvalues under `floor` times the largest up to that floor, by a pull to the start constants along its eigenvector
only; the well told directions keep their prior rows alone."""
import numpy as np
from scipy.sparse import csc_matrix


def curvature(problem, matrix, keep):
    """The told constants' data curvature (told constants x told constants) from `matrix`, the problem's Jacobian, and
    `keep`, the told unknowns' columns: the constants' Gram matrix less each frame's coordinates' share."""
    held, frames, per = len(problem.slots), len(problem.path), _per(problem)
    data = csc_matrix(matrix)[:frames * per].tocsr()
    constants = keep[keep < held]
    found = np.zeros((len(constants), len(constants)))
    for frame in range(frames):
        block = data[frame * per:(frame + 1) * per]
        own = np.arange(held + frame * problem.width, held + (frame + 1) * problem.width)
        own = own[np.isin(own, keep)]
        moved, angles = block[:, constants].toarray(), block[:, own].toarray()
        found += moved.T @ moved - moved.T @ angles @ np.linalg.lstsq(angles, moved, rcond=None)[0]
    return found, constants


def lift(problem, matrix, keep, floor):
    """The pull rows (lifted x held) that raise the told constants' data curvature to `floor` of its largest along
    every direction under it, each row its eigenvector scaled by the square root of the missing curvature."""
    found, constants = curvature(problem, matrix, keep)
    values, vectors = np.linalg.eigh((found + found.T) / 2)
    missing = floor * values[-1] - values
    low = missing > 0
    rows = np.zeros((int(low.sum()), len(problem.slots)))
    rows[:, constants] = (vectors[:, low] * np.sqrt(missing[low])).T
    return rows


def _per(problem):
    """A frame's row count: three turn rows per bone group, three place rows per marker."""
    return 3 * (len(problem.fitting.frame_sites) + len(problem.fitting.place_sites))
