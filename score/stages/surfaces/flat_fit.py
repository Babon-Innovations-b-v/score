"""The bake's fit of a flat row: its model's face laid to the row's face, its depth held apart.

bake_job.fit_within (#10: the plan wins on space, the model on shape) scales a take as one to the largest that fits
its row. On a flat row (the model gate's shape class "flat", tools/props/gates/model.py: its thinnest side under
FLAT_SHARE of its longest, its middle side at least SLENDER_SHARE of it) the side that binds is the thin one whenever
the model is deeper than the row, so the face shrank to the model's depth: of 115 flat rows in this PC's accepted
bakes 58 were laid under 60% of their face, quarters' picture frame 0.039 by 0.046 by 0.02 m for its 0.15 by 0.2 by
0.02 m row (6%), its wall 1.5 mm and "thin and in proportion" failed (#10, 2026-11-12). Here a flat row's model is
scaled as one so its face (the row's two large sides) fits within the row's face, and then only where its depth at
that scale is past `depth_bound` of the row's depth is its depth alone squashed to that bound: a door stays near its
read thickness, and a lumpy window, laid by its face alone, is not 1.1 m deep. A row that is not flat is laid exactly
as bake_job lays it.

Run, never imported by the bake's other code, by inside/paint_fit.py (the bake's card job, ../bake_fitted.py): its
`bake-job` and `square-again` are route_bake.py's with bake_job.fitted_size held as this module's, so bake_job.py and
route_bake.py, in the code of every row reaching route_bake.py, do not move.
"""
import contextlib
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
LIBRARY_TOOLS = HERE.parents[2] / "tools/props/library"  # bake_job's `import library`, as palette_library adds it
for folder in (HERE, LIBRARY_TOOLS):
    if str(folder) not in sys.path:
        sys.path.append(str(folder))

import numpy as np  # noqa: E402

import bake_job  # noqa: E402
import prop_env  # noqa: E402
import route_bake  # noqa: E402

# A flat row's model depth, at the scale its face fits, is at most DEPTH_TIMES the row's read depth and never held
# under DEPTH_LEAST (a row read 1 cm deep keeps a frame's or a panel's own relief up to 5 cm).
DEPTH_TIMES = 3.0
DEPTH_LEAST = 0.05
FITS = bake_job.fitted_size


def flat(size):
    """Whether a row's size lies flat by the model gate's shape class (bake_job.model_gate: FLAT_SHARE,
    SLENDER_SHARE)."""
    gate = bake_job.model_gate()
    smallest, middle, largest = sorted(float(side) for side in size)
    return largest > 0 and smallest / largest < gate.FLAT_SHARE and middle / largest >= gate.SLENDER_SHARE


def depth_bound(depth):
    """The deepest a flat row read `depth` deep lays its model (DEPTH_TIMES of it, at least DEPTH_LEAST)."""
    return max(DEPTH_TIMES * float(depth), DEPTH_LEAST)


def face_fit(found, size):
    """`found` (a model's sides) on a flat row's `size`: scaled as one to the largest whose two face sides (all but the
    row's thinnest) fit within the row's, then its depth (the row's thinnest side's) alone at most depth_bound."""
    found = np.maximum(np.asarray(found, float), 1e-9)
    size = np.asarray(size, float)
    thin = int(np.argmin(size))
    face = [side for side in range(3) if side != thin]
    laid = found * float(np.min(size[face] / found[face]))
    laid[thin] = min(laid[thin], depth_bound(size[thin]))
    return [round(float(side), 3) for side in laid]


def fitted_size(labelled, size, base):
    """bake_job.fitted_size, a flat row's by face_fit."""
    if not flat(size):
        return FITS(labelled, size, base)
    return face_fit(np.ptp(bake_job.take_points(labelled) @ np.array(base, float).reshape(3, 3).T, axis=0), size)


@contextlib.contextmanager
def held():
    """bake_job.fitted_size as this module's while held (laid_size and refitted both lay by it)."""
    bake_job.fitted_size = fitted_size
    try:
        yield
    finally:
        bake_job.fitted_size = FITS


def bake_job_step(inputs, out):
    """route_bake's bake-job step, a flat row laid by its face."""
    with held():
        route_bake.bake_job_step(inputs, out)


def square_again_step(inputs, out):
    """route_bake's square-again step, a flat row laid again by its face."""
    with held():
        route_bake.square_again_step(inputs, out)


if __name__ == "__main__":
    prop_env.main({"bake-job": bake_job_step, "square-again": square_again_step})
