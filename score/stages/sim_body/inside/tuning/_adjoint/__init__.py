"""Level 1's Jacobian by implicit differentiation at the inner optimum (#70, card plan step 6b): the inner unknowns
z = (every frame's pose q_k, then the body's constants c) sit where level 2 and 3's gradient g(z, theta) is zero, so
dz/dtheta = -H^-1 dg/dtheta and a residual row's derivative is dR/dtheta = R_theta - R_z H^-1 dg/dtheta. H is the FULL
Hessian, central differences of the gradient (the study measured Gauss-Newton alone 22.4 % off), read in the
block-arrow shape frames give it: one coordinate of EVERY frame stepped together (frames meet only through c), then
each constant alone (`arrow_hessian`); it is solved by the Schur step over the constants (`schur_solve`). An inner fit
whose gradient is not zero gives a wrong derivative, so `implicit_jacobian` refuses it (`Unconverged`), never uses it.
Callables, not a model: the card code supplies g (Newton eval_fk on a wp.Tape) and the residuals; numpy only here."""
import numpy as np

from .. import SKIN_SCALE


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


def inner_motion(gradient, inner, outer, frames, pose_size, steps, tolerance):
    """dz/dtheta = -H^-1 dg/dtheta at the inner optimum `inner`, as H^-1 dg/dtheta (inner size, outer size), `steps`
    (inner step, outer step) the central differences' steps; `Unconverged` when the gradient there exceeds
    `tolerance`."""
    norm = gradient_norm(gradient, inner, outer)
    if norm > tolerance:
        raise Unconverged(f"inner gradient {norm:.3g} over tolerance {tolerance:.3g}")
    inner_step, outer_step = steps
    hessian = arrow_hessian(gradient, inner, outer, frames, pose_size, inner_step)
    return schur_solve(*hessian, mixed(gradient, inner, outer, outer_step))


def implicit_jacobian(residuals, gradient, inner, outer, frames, pose_size, steps, tolerance):
    """dR/dtheta at the inner optimum `inner` for the outer unknowns `outer`: R_theta - R_z H^-1 dg/dtheta, R_z and
    R_theta by central differences of `residuals` (`inner_motion` for the rest)."""
    moved = inner_motion(gradient, inner, outer, frames, pose_size, steps, tolerance)
    inner_step, outer_step = steps
    by_inner = by_columns(lambda point: residuals(point, outer), inner, inner_step)
    by_outer = by_columns(lambda point: residuals(inner, point), outer, outer_step)
    return by_outer - by_inner @ moved


def rowed_jacobian(rows, gradient, inner, outer, frames, pose_size, steps, tolerance):
    """dR/dtheta as `implicit_jacobian` with R's derivative given, not differenced: `rows` (R_z (rows, inner size),
    R_theta (rows, outer size)) taped at (`inner`, `outer`), so a real body's thousands of inner unknowns cost no
    residual calls."""
    by_inner, by_outer = rows
    return by_outer - by_inner @ inner_motion(gradient, inner, outer, frames, pose_size, steps, tolerance)


class Body:
    """One tuning body's inner problem at its optimum: `residuals(inner, outer)` its rows, `gradient(inner, outer)`
    level 2 and 3's gradient, `inner` the solved poses then constants, `frames` and `pose_size` its shape."""

    def __init__(self, name, residuals, gradient, inner, frames, pose_size):
        self.name, self.residuals, self.gradient = name, residuals, gradient
        self.inner, self.frames, self.pose_size = np.asarray(inner, dtype=float), frames, pose_size


def chained_jacobian(level2, level3, outer, steps, tolerance):
    """dR/dtheta when level 2's constants c are outer to level 3 (case (a), #70): `level2` a Body over its sampled
    frames' poses then c, stationary in its own gradient, gives dc/dtheta; `level3` a Body over the poses only, its
    `residuals` and `gradient` taking the outer point (theta, then c), gives R's derivative over (theta, c) with its
    poses re-solved; chained, R_theta + R_c dc/dtheta + R_q dq/dtheta."""
    joined = np.concatenate([np.asarray(outer, dtype=float), level2.inner[level2.frames * level2.pose_size:]])
    both = implicit_jacobian(level3.residuals, level3.gradient, level3.inner, joined, level3.frames, level3.pose_size,
                             steps, tolerance)
    return both[:, :len(outer)] + both[:, len(outer):] @ constant_motion(level2, outer, steps, tolerance)


def constant_motion(level2, outer, steps, tolerance):
    """dc/dtheta from level 2's own stationarity: its residuals are the constants themselves (rows [0 | I] exactly,
    no residual call), so it is minus the constants' share of H^-1 dg/dtheta."""
    moved = inner_motion(level2.gradient, level2.inner, outer, level2.frames, level2.pose_size, steps, tolerance)
    return -moved[level2.frames * level2.pose_size:]


def chained_rows(level2, level3, rows, outer, steps, tolerance):
    """`chained_jacobian` with level 3's derivative given, not differenced: `rows` (R_q (rows, poses), R_theta (rows,
    outer), R_c (rows, constants)) taped at level 3's optimum, so the real body costs no residual calls."""
    by_poses, by_outer, by_constants = rows
    joined = np.concatenate([np.asarray(outer, dtype=float), level2.inner[level2.frames * level2.pose_size:]])
    both = rowed_jacobian((by_poses, np.hstack([by_outer, by_constants])), level3.gradient, level3.inner, joined,
                          level3.frames, level3.pose_size, steps, tolerance)
    return both[:, :len(outer)] + both[:, len(outer):] @ constant_motion(level2, outer, steps, tolerance)


def transposed_mixed(body, weights, outer, step):
    """`weights`^T dg/dtheta (columns of `weights`, outer size): by `body.products(inner, outer, weights)` when the body
    has it (two taped outer gradients a column, d/dtheta of g . w by symmetry), else `mixed`'s columns once."""
    products = getattr(body, "products", None)
    if products is not None:
        return products(body.inner, outer, weights)
    return weights.T @ mixed(body.gradient, body.inner, outer, step)


def adjoint_solve(body, outer, right, steps, tolerance):
    """H^-T `right` at `body`'s optimum (`Unconverged` over `tolerance`): H's blocks read once, every column of
    `right` solved against them."""
    norm = gradient_norm(body.gradient, body.inner, outer)
    if norm > tolerance:
        raise Unconverged(f"inner gradient {norm:.3g} over tolerance {tolerance:.3g}")
    blocks, couplings, corner = arrow_hessian(body.gradient, body.inner, outer, body.frames, body.pose_size, steps[0])
    return schur_solve(blocks.transpose(0, 2, 1), couplings, corner, right)


def adjoint_rows(level2, level3, rows, outer, steps, tolerance):
    """`chained_rows` in reverse: one solve per row, not per outer unknown. lambda = H3^-T R_q^T gives the rows over
    (theta, c), D = (R_theta | R_c) - lambda^T g3_(q,theta c); mu = H2^-T [0; D_c^T] gives D_theta - mu^T g2_(z,theta),
    so each factor serves every row and every column of theta at once."""
    by_poses, by_outer, by_constants = rows
    joined = np.concatenate([np.asarray(outer, dtype=float), level2.inner[level2.frames * level2.pose_size:]])
    lifted = adjoint_solve(level3, joined, np.asarray(by_poses, dtype=float).T, steps, tolerance)
    both = np.hstack([by_outer, by_constants]) - transposed_mixed(level3, lifted, joined, steps[1])
    right = np.zeros((len(level2.inner), len(both)))
    right[level2.frames * level2.pose_size:] = both[:, len(outer):].T
    lowered = adjoint_solve(level2, outer, right, steps, tolerance)
    return both[:, :len(outer)] - transposed_mixed(level2, lowered, outer, steps[1])


def refused(bodies, outer, tolerance):
    """{name: inner gradient's largest entry} of every body whose inner fit stopped over `tolerance`."""
    norms = {body.name: gradient_norm(body.gradient, body.inner, outer) for body in bodies}
    return {name: norm for name, norm in norms.items() if norm > tolerance}


def stacked_jacobian(bodies, outer, prior, steps, tolerance):
    """Level 1's whole Jacobian (rows x outer unknowns) in `tuning`'s row order, every body's rows then `prior`'s
    (`prior(outer)`, its columns by central differences): each body's block by `implicit_jacobian`. Every body is
    checked before any is used, and `Unconverged` names each one stopped over `tolerance`."""
    stopped = refused(bodies, outer, tolerance)
    if stopped:
        raise Unconverged("inner fits stopped unconverged: "
                          + ", ".join(f"{name} {norm:.3g}" for name, norm in stopped.items()))
    blocks = [implicit_jacobian(body.residuals, body.gradient, body.inner, outer, body.frames, body.pose_size, steps,
                                tolerance) for body in bodies]
    return np.concatenate(blocks + [by_columns(prior, outer, steps[1])])


def rms_row(values, rows, point_frames=None, frames=None):
    """A root mean square's value and derivative row from per-point `values` and their derivative `rows` (points,
    unknowns): d sqrt(mean v^2) = mean(v dv) / rms, a zero row where every value is zero. With `point_frames` and
    `frames`, each row is its point's frame block of a pose of `frames` blocks, and the derivative row the whole pose's."""
    values, rows = np.asarray(values, dtype=float), np.asarray(rows, dtype=float)
    width = rows.shape[1] if frames is None else frames * rows.shape[1]
    root = float(np.sqrt(np.mean(np.square(values))))
    if root == 0.0:
        return 0.0, np.zeros(width)
    if frames is None:
        return root, (values @ rows) / (len(values) * root)
    summed = np.zeros((frames, rows.shape[1]))
    np.add.at(summed, np.asarray(point_frames), values[:, None] * rows)
    return root, summed.ravel() / (len(values) * root)


def distance_rows(differences, rows):
    """Per-frame distances |d| and their derivative rows from per-frame differences (frames, 3) and their derivatives
    (frames, 3, unknowns): d|d| = (d / |d|) . dd."""
    differences = np.asarray(differences, dtype=float)
    lengths = np.linalg.norm(differences, axis=1)
    return lengths, np.einsum("fk,fkn->fn", differences / lengths[:, None], np.asarray(rows))


def case_rows(skins, frames=None):
    """One case's level 1 rows and their derivative rows over the inner unknowns, in `tuning.case_residuals`' order
    and scale, from taped measures: `skins` {region: (depths outside per point m, their rows (points, unknowns))},
    each row the root mean square over its points (`rms_row`), mm for metres as the measures give. With `frames` (a
    pose of that many frame blocks) a skin is (depths, rows (points, block), each point's frame) and every row is laid
    on its own frame's block (`TapedMeasures.measured`). Turns and joints are no rows (the owner's aim of 2026-11-01:
    level 1 tunes the bones inside the skin; turns are its check, joints reported)."""
    return scaled_rows({key: rms_row(1000 * np.asarray(part[0]), 1000 * np.asarray(part[1]),
                                     *((part[2], frames) if frames is not None else ()))
                        for key, part in skins.items()})


def scaled_rows(reduced):
    """`case_rows`' values and rows from each region's (root mean square mm, its row): over SKIN_SCALE and the square
    root of the regions' count, in sorted order (`tuning.case_residuals`' scale), as `TapedMeasures.region_rows`
    gives them too."""
    scale = np.sqrt(1.0 / len(reduced)) / SKIN_SCALE
    return (np.array([scale * reduced[key][0] for key in sorted(reduced)]),
            np.stack([scale * np.asarray(reduced[key][1]) for key in sorted(reduced)]))
