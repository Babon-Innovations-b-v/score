"""Level 1's Jacobian by implicit differentiation at the inner optimum (#70, card plan step 6b): the inner unknowns
z = (every frame's pose q_k, then the body's constants c) sit where level 2 and 3's gradient g(z, theta) is zero, so
dz/dtheta = -H^-1 dg/dtheta and a residual row's derivative is dR/dtheta = R_theta - R_z H^-1 dg/dtheta. H is the FULL
Hessian, central differences of the gradient (the study measured Gauss-Newton alone 22.4 % off), read in the
block-arrow shape frames give it: one coordinate of EVERY frame stepped together (frames meet only through c), then
each constant alone (`arrow_hessian`); it is solved by the Schur step over the constants (`schur_solve`). An inner fit
whose gradient is not zero gives a wrong derivative, so `implicit_jacobian` refuses it (`Unconverged`), never uses it.
Callables, not a model: the card code supplies g (Newton eval_fk on a wp.Tape) and the residuals; numpy only here."""
import numpy as np


class Unconverged(ValueError):
    """The inner fit stopped where its gradient is not zero: its implicit derivative would be wrong."""


def gradient_norm(gradient, inner, outer):
    """The largest absolute entry of the inner gradient at (`inner`, `outer`)."""
    return float(np.max(np.abs(gradient(inner, outer))))


def arrow_hessian(gradient, inner, outer, frames, pose_size, step):
    """The Hessian's blocks at `inner`: per frame (frames, pose_size, pose_size), the frame-constant couplings
    (frames, pose_size, constants) and the constants' corner, by central differences of `gradient`."""
    poses = frames * pose_size
    constants = len(inner) - poses
    blocks = np.zeros((frames, pose_size, pose_size))
    couplings = np.zeros((frames, pose_size, constants))
    corner = np.zeros((constants, constants))
    for coordinate in range(pose_size):
        change = _central(gradient, inner, outer, np.arange(frames) * pose_size + coordinate, step)
        blocks[:, :, coordinate] = change[:poses].reshape(frames, pose_size)
    for constant in range(constants):
        change = _central(gradient, inner, outer, [poses + constant], step)
        couplings[:, :, constant] = change[:poses].reshape(frames, pose_size)
        corner[:, constant] = change[poses:]
    return blocks, couplings, 0.5 * (corner + corner.T)


def _central(gradient, inner, outer, indices, step):
    """The gradient's central difference over `step` with the inner coordinates `indices` moved together."""
    up, down = np.array(inner, dtype=float), np.array(inner, dtype=float)
    up[indices] += step
    down[indices] -= step
    return (gradient(up, outer) - gradient(down, outer)) / (2 * step)


def mixed(gradient, inner, outer, step):
    """dg/dtheta (inner size, outer size) by central differences of `gradient` over each outer unknown."""
    columns = []
    for unknown in range(len(outer)):
        up, down = np.array(outer, dtype=float), np.array(outer, dtype=float)
        up[unknown] += step
        down[unknown] -= step
        columns.append((gradient(inner, up) - gradient(inner, down)) / (2 * step))
    return np.stack(columns, axis=1)


def schur_solve(blocks, couplings, corner, right):
    """H^-1 `right` for the block-arrow H (`arrow_hessian`'s blocks), `right` of shape (inner size, columns)."""
    frames, pose_size, _ = blocks.shape
    poses = frames * pose_size
    by_frame = right[:poses].reshape(frames, pose_size, -1)
    solved_right = np.linalg.solve(blocks, by_frame)
    solved_couplings = np.linalg.solve(blocks, couplings)
    reduced = corner - np.einsum("kpc,kpd->cd", couplings, solved_couplings)
    reduced_right = right[poses:] - np.einsum("kpc,kpn->cn", couplings, solved_right)
    constants = np.linalg.solve(reduced, reduced_right)
    poses_solved = solved_right - np.einsum("kpc,cn->kpn", solved_couplings, constants)
    return np.concatenate([poses_solved.reshape(poses, -1), constants])


def by_columns(function, point, step):
    """`function`'s Jacobian at `point` by central differences (rows of `function`, columns of `point`)."""
    columns = []
    for unknown in range(len(point)):
        up, down = np.array(point, dtype=float), np.array(point, dtype=float)
        up[unknown] += step
        down[unknown] -= step
        columns.append((function(up) - function(down)) / (2 * step))
    return np.stack(columns, axis=1)


def implicit_jacobian(residuals, gradient, inner, outer, frames, pose_size, steps, tolerance):
    """dR/dtheta at the inner optimum `inner` for the outer unknowns `outer`: R_theta - R_z H^-1 dg/dtheta, `steps`
    (inner step, outer step) the central differences' steps; `Unconverged` when the gradient there exceeds
    `tolerance`."""
    norm = gradient_norm(gradient, inner, outer)
    if norm > tolerance:
        raise Unconverged(f"inner gradient {norm:.3g} over tolerance {tolerance:.3g}")
    inner_step, outer_step = steps
    hessian = arrow_hessian(gradient, inner, outer, frames, pose_size, inner_step)
    moved = schur_solve(*hessian, mixed(gradient, inner, outer, outer_step))
    by_inner = by_columns(lambda point: residuals(point, outer), inner, inner_step)
    by_outer = by_columns(lambda point: residuals(inner, point), outer, outer_step)
    return by_outer - by_inner @ moved
