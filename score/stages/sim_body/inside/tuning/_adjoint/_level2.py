"""Level 2's Body off `fit/_constants.Problem` (#70, case (a): the constants outer to level 3, their derivative from
level 2's own stationarity). The Problem's unknowns are the constants first, then each sampled frame's leading
coordinates; a `Body` reads poses first, then constants, so the unknowns and the gradient are permuted between the two.
The gradient is J^T r of the Problem's rows (`jacobian`, the card's exact `_card._level2.jacobian` in use), the
untold entries and the bound-held ones pinned by `_bodies.Pinned`. Numpy only: the Problem and its Jacobian are given."""
import numpy as np

from . import Body
from ._bodies import Pinned

HELD = 1e-5  # an unknown this far from a finite bound is held there by the solve's active set


def to_problem(inner, held):
    """Body order (poses, then the `held` constants) to the Problem's (constants, then poses)."""
    inner = np.asarray(inner, dtype=float)
    return np.concatenate([inner[inner.size - held:], inner[:inner.size - held]])


def to_body(unknowns, held):
    """The Problem's order (the `held` constants, then poses) to Body order (poses, then constants)."""
    unknowns = np.asarray(unknowns, dtype=float)
    return np.concatenate([unknowns[held:], unknowns[:held]])


def pinned_mask(problem, unknowns, kept):
    """Body-order mask of the entries level 2 does not move: not in `kept` (the told unknowns' indices, Problem
    order, as `fit/_constants.told` gives them) or within HELD of a finite bound."""
    low, high = problem.bounds()
    unknowns = np.asarray(unknowns, dtype=float)
    pinned = np.ones(unknowns.size, dtype=bool)
    pinned[np.asarray(kept, dtype=int)] = False
    pinned |= (np.isfinite(low) & (unknowns - low < HELD)) | (np.isfinite(high) & (high - unknowns < HELD))
    return to_body(pinned, len(problem.slots))


def level2_body(problem_at, jacobian, solved, kept, outer):
    """Level 2 as a `Body` at its optimum `solved` (Problem order): `problem_at(outer)` the Problem at level 1's
    point, `jacobian(problem, unknowns)` its rows' Jacobian, `kept` the told unknowns (Problem order)."""
    problem = problem_at(outer)
    held = len(problem.slots)
    inner = to_body(solved, held)
    pinned = Pinned(inner, pinned_mask(problem, solved, kept))
    last = {np.asarray(outer, dtype=float).tobytes(): problem}

    def problem_of(at):
        """The Problem at level 1's point `at`, rebuilt only when `at` moved since the last call (H's columns step the
        inner unknowns at one outer point; a real `problem_at` re-reads the body, 0.3 s a call)."""
        key = np.asarray(at, dtype=float).tobytes()
        if key not in last:
            last.clear()
            last[key] = problem_at(at)
        return last[key]

    def gradient(point, at):
        """J^T r at the Body-order point, the pinned entries' springs in place of theirs."""
        moved = problem_of(at)
        unknowns = to_problem(pinned.whole(point), held)
        found = jacobian(moved, unknowns).T @ moved.residuals(unknowns)
        return pinned.gradient(point, to_body(np.asarray(found).ravel(), held))

    frames = len(problem.path)
    return Body("level 2", None, gradient, inner, frames, problem.width)
