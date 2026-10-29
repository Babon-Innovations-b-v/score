"""The damped Gauss-Newton step mink takes, per row on the card in the reduced dofs (plan step 1).

Reduced dofs: frozen dofs out, each coupled follower's column added onto its leader's through the coupling's
slope (polyval's derivative at the leader), dofs at a bound whose step pushes out held, and released once their descent points back inside.
Damping is mink's: LM_DAMPING times the squared error plus DAMPING on every full dof's diagonal (S^T S reduced). The solve is Warp's tile
Cholesky (Newton's own IKOptimizerLM pattern) at the reduced size, 37 on MyoFullBody (128 dofs, 40 frozen,
51 followers), inside sm_120's shared memory for any size up to 79."""
import functools

import warp as wp

LM_DAMPING = 1e-3
DAMPING = 1e-9
BOUND_SLACK = 1e-9
HOLD_PASSES = 3  # solves after the first, each holding the dofs the last one pushed out and releasing a held one
# whose own descent points back inside its range (the active set's exit: heavy_kimodo's knee held on 0, mink 4e-4 in)
TILE_THREADS = 32


@wp.kernel(enable_backward=False)
def _slopes(qpos: wp.array2d[wp.float32], leader_coord: wp.array[wp.int32], leader_rest: wp.array[wp.float32],
            poly: wp.array2d[wp.float32], slopes: wp.array2d[wp.float32]):
    """Each coupling's d follower / d leader at the row's pose (zero for a coupling without a leader)."""
    row, coupling = wp.tid()
    if leader_coord[coupling] < 0:
        slopes[row, coupling] = 0.0
        return
    lead = qpos[row, leader_coord[coupling]] - leader_rest[coupling]
    slopes[row, coupling] = (poly[coupling, 1] + 2.0 * poly[coupling, 2] * lead
                             + 3.0 * poly[coupling, 3] * lead * lead + 4.0 * poly[coupling, 4] * lead * lead * lead)


@wp.kernel(enable_backward=False)
def _reduced_jacobian(jacobian: wp.array3d[wp.float32], free_dof: wp.array[wp.int32],
                      follower_dof: wp.array[wp.int32], leader_reduced: wp.array[wp.int32],
                      slopes: wp.array2d[wp.float32], reduced: wp.array3d[wp.float32]):
    """J S(q): a free dof's column plus every follower column it leads, times that coupling's slope."""
    row, residual, column = wp.tid()
    value = jacobian[row, residual, free_dof[column]]
    for coupling in range(follower_dof.shape[0]):
        if leader_reduced[coupling] == column:
            value += jacobian[row, residual, follower_dof[coupling]] * slopes[row, coupling]
    reduced[row, residual, column] = value


@wp.kernel(enable_backward=False)
def _normal_equations(reduced: wp.array3d[wp.float32], residuals: wp.array2d[wp.float32],
                      keep: wp.array2d[wp.float32], slopes: wp.array2d[wp.float32],
                      leader_reduced: wp.array[wp.int32], hessian: wp.array3d[wp.float32],
                      gradient: wp.array2d[wp.float32]):
    """Damped J_red^T J_red and -J_red^T r, a held dof's row and column replaced by the identity's. The damping is
    mink's on every dof of the full step, S^T S in the reduced dofs: a leader's own plus its followers' slopes squared
    (elv_angle with its follower at slope -1 damped twice; damped once, heavy_squat's row 148 swung 1 rad a step)."""
    row, first, second = wp.tid()
    squared = float(0.0)
    spread = float(1.0)
    if first == second:
        for coupling in range(leader_reduced.shape[0]):
            if leader_reduced[coupling] == first:
                spread += slopes[row, coupling] * slopes[row, coupling]
    product = float(0.0)
    for residual in range(reduced.shape[1]):
        product += reduced[row, residual, first] * reduced[row, residual, second]
        squared += residuals[row, residual] * residuals[row, residual]
    value = product * keep[row, first] * keep[row, second]
    if first == second:
        value += keep[row, first] * (LM_DAMPING * squared + DAMPING) * spread + (1.0 - keep[row, first])
    hessian[row, first, second] = value
    if second == 0:
        pulled = float(0.0)
        for residual in range(reduced.shape[1]):
            pulled += reduced[row, residual, first] * residuals[row, residual]
        gradient[row, first] = -pulled * keep[row, first]


@functools.cache
def _cholesky_kernel(size: int):
    """Warp's tile Cholesky and its solve, one row a block, at one reduced size."""
    tile_size = wp.constant(size)

    def solve(hessian: wp.array3d[wp.float32], gradient: wp.array2d[wp.float32], step: wp.array2d[wp.float32]):
        row = wp.tid()
        factor = wp.tile_cholesky(wp.tile_load(hessian[row], shape=(tile_size, tile_size)))
        wp.tile_store(step[row], wp.tile_cholesky_solve(factor, wp.tile_load(gradient[row], shape=(tile_size,))))

    solve.__name__ = solve.__qualname__ = f"reduced_cholesky_{size}"
    return wp.kernel(enable_backward=False, module="unique")(solve)


@wp.kernel(enable_backward=False)
def _predicted(reduced: wp.array3d[wp.float32], step: wp.array2d[wp.float32], residuals: wp.array2d[wp.float32],
               predicted: wp.array2d[wp.float32]):
    """The linear model's residuals after the step, r + J_red s."""
    row, residual = wp.tid()
    value = residuals[row, residual]
    for column in range(step.shape[1]):
        value += reduced[row, residual, column] * step[row, column]
    predicted[row, residual] = value


@wp.kernel(enable_backward=False)
def _kept(step: wp.array2d[wp.float32], qpos: wp.array2d[wp.float32], free_coord: wp.array[wp.int32],
          lower: wp.array[wp.float32], upper: wp.array[wp.float32], reduced: wp.array3d[wp.float32],
          predicted: wp.array2d[wp.float32], keep: wp.array2d[wp.float32]):
    """A free dof at its bound whose step pushes out is held (keep 0); a held one whose model gradient there,
    J_red^T (r + J_red s), points its descent back inside is released (keep 1)."""
    row, column = wp.tid()
    at = qpos[row, free_coord[column]]
    on_low = at <= lower[column] + BOUND_SLACK
    on_high = at >= upper[column] - BOUND_SLACK
    if keep[row, column] == 0.0:
        slope = float(0.0)
        for residual in range(reduced.shape[1]):
            slope += reduced[row, residual, column] * predicted[row, residual]
        inside = (on_low and slope < 0.0) or (on_high and slope > 0.0)
        keep[row, column] = wp.where(inside, 1.0, 0.0)
        return
    out_low = on_low and step[row, column] < 0.0
    out_high = on_high and step[row, column] > 0.0
    keep[row, column] = wp.where(out_low or out_high, 0.0, 1.0)


@wp.kernel(enable_backward=False)
def _scattered(step: wp.array2d[wp.float32], free_dof: wp.array[wp.int32], active: wp.array[wp.int32],
               full: wp.array2d[wp.float32]):
    """The reduced step laid on its free dofs of the full step (zero elsewhere and for a stopped row)."""
    row, column = wp.tid()
    full[row, free_dof[column]] = wp.where(active[row] != 0, step[row, column], 0.0)


@wp.kernel(enable_backward=False)
def _norms(step: wp.array2d[wp.float32], norms: wp.array[wp.float32]):
    """Each row's reduced step length, mink's stop measure."""
    row = wp.tid()
    total = float(0.0)
    for column in range(step.shape[1]):
        total += step[row, column] * step[row, column]
    norms[row] = wp.sqrt(total)


class Reduction:
    """The reduced dofs on the card: which dofs are free, their coordinates and bounds, and the couplings."""

    def __init__(self, free_dof, free_coord, lower, upper, follower_dof, leader_dof, leader_coord, leader_rest,
                 poly, device):
        reduced_of = {int(dof): column for column, dof in enumerate(free_dof)}
        self.size = len(free_dof)
        self.free_dof = wp.array(free_dof, dtype=wp.int32, device=device)
        self.free_coord = wp.array(free_coord, dtype=wp.int32, device=device)
        self.lower = wp.array(lower, dtype=wp.float32, device=device)
        self.upper = wp.array(upper, dtype=wp.float32, device=device)
        self.follower_dof = wp.array(follower_dof, dtype=wp.int32, device=device)
        self.leader_reduced = wp.array([reduced_of.get(int(dof), -1) for dof in leader_dof], dtype=wp.int32,
                                       device=device)
        self.leader_coord = wp.array(leader_coord, dtype=wp.int32, device=device)
        self.leader_rest = wp.array(leader_rest, dtype=wp.float32, device=device)
        self.poly = wp.array(poly, dtype=wp.float32, device=device)


def _solved(reduction, reduced, residuals, keep, slopes, device):
    """One damped reduced solve for every row under its keep mask."""
    rows, size = keep.shape
    hessian = wp.empty((rows, size, size), dtype=wp.float32, device=device)
    gradient = wp.empty((rows, size), dtype=wp.float32, device=device)
    step = wp.empty((rows, size), dtype=wp.float32, device=device)
    wp.launch(_normal_equations, dim=(rows, size, size), inputs=[reduced, residuals, keep, slopes, reduction.leader_reduced],
              outputs=[hessian, gradient], device=device)
    wp.launch_tiled(_cholesky_kernel(reduction.size), dim=[rows], inputs=[hessian, gradient], outputs=[step],
                    block_dim=TILE_THREADS, device=device)
    return step


def damped_step(reduction, jacobian, residuals, qpos, active):
    """mink's damped step for every row: (full step [rows, dofs], reduced step length [rows]).

    jacobian [rows, residuals, dofs] and residuals [rows, residuals] at qpos [rows, coords] (MuJoCo's layout);
    active [rows] int32, a stopped row's step zero. Active-set passes: solve, hold the dofs at a bound the step pushes
    out, solve again, HOLD_PASSES times, a held dof whose descent points back inside released (one pass left a toy row
    with two dofs at their bounds pushing a third out and back by projection every step, never stopping)."""
    device = jacobian.device
    rows, count, dofs = jacobian.shape
    slopes = wp.empty((rows, reduction.poly.shape[0]), dtype=wp.float32, device=device)
    wp.launch(_slopes, dim=slopes.shape, inputs=[qpos, reduction.leader_coord, reduction.leader_rest,
                                                 reduction.poly], outputs=[slopes], device=device)
    reduced = wp.empty((rows, count, reduction.size), dtype=wp.float32, device=device)
    wp.launch(_reduced_jacobian, dim=reduced.shape, inputs=[jacobian, reduction.free_dof, reduction.follower_dof,
                                                            reduction.leader_reduced, slopes],
              outputs=[reduced], device=device)
    keep = wp.ones((rows, reduction.size), dtype=wp.float32, device=device)
    step = _solved(reduction, reduced, residuals, keep, slopes, device)
    predicted = wp.empty((rows, count), dtype=wp.float32, device=device)
    for _ in range(HOLD_PASSES):
        wp.launch(_predicted, dim=predicted.shape, inputs=[reduced, step, residuals], outputs=[predicted],
                  device=device)
        wp.launch(_kept, dim=keep.shape, inputs=[step, qpos, reduction.free_coord, reduction.lower, reduction.upper,
                                                 reduced, predicted], outputs=[keep], device=device)
        step = _solved(reduction, reduced, residuals, keep, slopes, device)
    full = wp.zeros((rows, dofs), dtype=wp.float32, device=device)
    wp.launch(_scattered, dim=step.shape, inputs=[step, reduction.free_dof, active], outputs=[full], device=device)
    norms = wp.empty(rows, dtype=wp.float32, device=device)
    wp.launch(_norms, dim=rows, inputs=[step], outputs=[norms], device=device)
    return full, norms
