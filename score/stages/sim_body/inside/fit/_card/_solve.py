"""Level 3's loop on the card (plan step 1): mink's steps for every row at once until each row stops.

Per step: Newton's analytic Jacobian (IKOptimizerLM's own buffers, its own solve never launched), the residuals in
float64 from float64 link frames (`_forward`), the damped reduced step (`_step`), Newton's integrate, the exact
projection (`_project`). A row stops by a rule fixed against mink on the proto clip (mink's own 1e-8 on the step
never fires with a float32 Jacobian): its reduced step under STEP_DONE, or its float64 cost moved less than COST_DONE
of itself over two steps (1e-7 left the shoulder's flat elevation plane 0.012 deg off mink, 1e-9 0.0025 on the proto
clip but 0.047 on mean_squat's chain, where a row still creeps down elv_angle_r's valley; 1e-10 reaches mink there, 0.0048 deg, and 1e-11 runs the
proto clip's frame 41 0.0104 mm past mink's stop along the root's flat height), or it
cycles at its float32 pose's floor: its cost back within CYCLE_RETURN of the change between, two steps apart, by a
step under CYCLE_STEP (1e-4: mean_squat's row 148 cycles at mink's angle by 3e-5 rad steps, its float32
Jacobian's floor in that valley; a toy row seeded 0.5 mm off: the float64 step equals the card's, its model gain 3.7e-12 while
the float32 pose's rounding moves the cost 9e-9 either way, so it went A, B, A for good). A monotone fall never
returns, so the cycle rule cannot stop one early. It also stops, as mink's frames do (`../_frames.solved`), when a step
moved its float64 residuals (the weighted errors) by under MOVED_DONE: a drift no objective sees, elv_angle and its
follower cancelling at zero shoulder elevation (#70's arms_raise). A stopped row's step is zero from then on. A row still going at MOST_STEPS
raises NotConverged, as mink's frames do (`../_frames.py`)."""
import warp as wp

from ._forward import Forward, frames
from ._objective import wide_residuals
from ._project import project
from ._step import damped_step

MOST_STEPS = 300
CHUNK_ROWS = 8000  # the plan's: about 2.9 GB on the card a chunk of MyoFullBody rows, under the 8 GB cap beside env1
STEP_DONE = 1e-6
COST_DONE = 1e-10
MOVED_DONE = 1e-8  # mink's own, `_frames.STEP_DONE` on the change of the weighted errors
CYCLE_STEP = 1e-4  # a row back at its cost of two steps before, by steps this short, is at its float32 pose's floor
CYCLE_RETURN = 1e-2  # ... back within this share of the cost change between the two
ROOT_TURN = 3  # the free root's quaternion starts at coordinate 3 in both layouts


class NotConverged(RuntimeError):
    """A row whose fit did not stop in MOST_STEPS."""


@wp.kernel(enable_backward=False)
def _to_mujoco(joint_q: wp.array2d[wp.float32], qpos: wp.array2d[wp.float32]):
    """Newton's coordinates (root turn x, y, z, w) in MuJoCo's (w, x, y, z)."""
    row, coord = wp.tid()
    source = coord
    if coord == ROOT_TURN:
        source = ROOT_TURN + 3
    elif coord > ROOT_TURN and coord < ROOT_TURN + 4:
        source = coord - 1
    qpos[row, coord] = joint_q[row, source]


@wp.kernel(enable_backward=False)
def _to_newton(qpos: wp.array2d[wp.float32], joint_q: wp.array2d[wp.float32]):
    """MuJoCo's coordinates in Newton's."""
    row, coord = wp.tid()
    source = coord
    if coord == ROOT_TURN + 3:
        source = ROOT_TURN
    elif coord >= ROOT_TURN and coord < ROOT_TURN + 3:
        source = coord + 1
    joint_q[row, coord] = qpos[row, source]


@wp.kernel(enable_backward=False)
def _stopped(residuals: wp.array2d[wp.float64], before: wp.array2d[wp.float64], norms: wp.array[wp.float32],
             history: wp.array2d[wp.float64], step: int, active: wp.array[wp.int32], steps: wp.array[wp.int32]):
    """The stop rule for one step: history holds each row's cost at the last three poses, before its residuals at
    the last pose."""
    row = wp.tid()
    if active[row] == 0:
        return
    cost = wp.float64(0.0)
    moved = wp.float64(0.0)
    for residual in range(residuals.shape[1]):
        cost += residuals[row, residual] * residuals[row, residual]
        change = residuals[row, residual] - before[row, residual]
        moved += change * change
        before[row, residual] = residuals[row, residual]
    history[row, 2] = history[row, 1]
    history[row, 1] = history[row, 0]
    history[row, 0] = cost
    steps[row] = step + 1
    settled = step >= 2 and wp.abs(history[row, 2] - cost) <= wp.float64(COST_DONE) * cost
    returned = wp.abs(history[row, 2] - cost) <= wp.float64(CYCLE_RETURN) * wp.abs(history[row, 1] - cost)
    cycling = step >= 2 and norms[row] < CYCLE_STEP and returned
    unseen = step >= 1 and wp.sqrt(moved) < wp.float64(MOVED_DONE)
    if norms[row] < STEP_DONE or settled or cycling or unseen:
        active[row] = 0


@wp.kernel(enable_backward=False)
def _narrowed(wide: wp.array2d[wp.float64], narrow: wp.array2d[wp.float32]):
    row, residual = wp.tid()
    narrow[row, residual] = wp.float32(wide[row, residual])


def _wide_residuals(optimizer, forward, joint_q, body_q, wide):
    """Every objective's residuals in float64 from joint_q's float64 link frames."""
    frames(forward, joint_q, body_q)
    for objective, start in zip(optimizer.objectives, optimizer.residual_offsets, strict=True):
        wide_residuals(objective, body_q, start, optimizer.problem_idx, wide)


def solved(optimizer, reduction, projection, joint_q, seeds, most_steps=MOST_STEPS):
    """Every row's pose fitted from joint_q [rows, coords] (Newton's layout): (qpos [rows, coords] in MuJoCo's
    layout, steps [rows]). optimizer is the batch's IKOptimizerLM (Newton's IKSolver(...)._impl), seeds [rows,
    coords] MuJoCo's layout (the frozen coordinates' values)."""
    device = joint_q.device
    rows, coords = joint_q.shape
    current = wp.clone(joint_q)
    following = wp.empty_like(current)
    velocity = wp.zeros((rows, optimizer.model.joint_dof_count), dtype=wp.float32, device=device)
    qpos = wp.empty_like(current)
    history = wp.zeros((rows, 3), dtype=wp.float64, device=device)
    forward = Forward(optimizer.model)
    body_q = wp.empty((rows, forward.bodies), dtype=wp.transformd, device=device)
    wide = wp.zeros((rows, optimizer.n_residuals), dtype=wp.float64, device=device)
    before = wp.zeros_like(wide)
    narrow = wp.empty((rows, optimizer.n_residuals), dtype=wp.float32, device=device)
    active = wp.ones(rows, dtype=wp.int32, device=device)
    steps = wp.zeros(rows, dtype=wp.int32, device=device)
    for step in range(most_steps):
        context = optimizer._ctx_solver(current)
        optimizer._residuals_analytic(context)
        jacobian = optimizer._jacobian_at(context)
        _wide_residuals(optimizer, forward, current, body_q, wide)
        wp.launch(_narrowed, dim=wide.shape, inputs=[wide], outputs=[narrow], device=device)
        wp.launch(_to_mujoco, dim=(rows, coords), inputs=[current], outputs=[qpos], device=device)
        full, norms = damped_step(reduction, jacobian, narrow, qpos, active)
        optimizer._integrate_dq(current, dq_in=full, joint_q_out=following, joint_qd_out=velocity)
        wp.launch(_to_mujoco, dim=(rows, coords), inputs=[following], outputs=[qpos], device=device)
        project(projection, qpos, seeds)
        wp.launch(_to_newton, dim=(rows, coords), inputs=[qpos], outputs=[current], device=device)
        wp.launch(_stopped, dim=rows, inputs=[wide, before, norms, history, step, active, steps], device=device)
        if step % 10 == 9 and not active.numpy().any():
            break
    if active.numpy().any():
        raise NotConverged(f"{int(active.numpy().sum())} rows did not stop in {most_steps} steps")
    wp.launch(_to_mujoco, dim=(rows, coords), inputs=[current], outputs=[qpos], device=device)
    return qpos, steps


def solved_in_chunks(optimizer_for, reduction, projection, joint_q, seeds, chunk_rows=CHUNK_ROWS):
    """`solved` over joint_q's rows CHUNK_ROWS at a time: (qpos [rows, coords] in MuJoCo's layout, steps [rows]) as
    host arrays. optimizer_for(start, stop) gives the IKOptimizerLM for rows start:stop (one IKSolver a chunk: its
    buffers are per row); joint_q and seeds are host arrays [rows, coords]."""
    import numpy as np
    found, steps = [], []
    for start in range(0, joint_q.shape[0], chunk_rows):
        stop = min(start + chunk_rows, joint_q.shape[0])
        optimizer = optimizer_for(start, stop)
        device = optimizer.model.device
        chunk = lambda values: wp.array(np.ascontiguousarray(values[start:stop], dtype=np.float32), dtype=wp.float32,
                                        device=device)
        qpos, made = solved(optimizer, reduction, projection, chunk(joint_q), chunk(seeds))
        found.append(qpos.numpy())
        steps.append(made.numpy())
    return np.concatenate(found), np.concatenate(steps)
