"""Level 3's loop on the card (plan step 1): mink's steps for every row at once until each row stops.

Per step: Newton's analytic residuals and Jacobian (IKOptimizerLM's own buffers, its own solve never launched), the
damped reduced step (`_step`), Newton's integrate, the exact projection (`_project`). A row stops by a float32 rule
fixed against mink's 1e-8 (which never fires in float32): its reduced step under STEP_DONE, or its cost moved less
than COST_DONE of itself over two steps; a stopped row's step is zero from then on. A row still going at MOST_STEPS
raises NotConverged, as mink's frames do (`../_frames.py`)."""
import warp as wp

from ._project import project
from ._step import damped_step

MOST_STEPS = 300
STEP_DONE = 1e-6
COST_DONE = 1e-7
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
def _stopped(residuals: wp.array2d[wp.float32], norms: wp.array[wp.float32], history: wp.array2d[wp.float32],
             step: int, active: wp.array[wp.int32], steps: wp.array[wp.int32]):
    """The stop rule for one step: history holds each row's cost at the last three poses."""
    row = wp.tid()
    if active[row] == 0:
        return
    cost = float(0.0)
    for residual in range(residuals.shape[1]):
        cost += residuals[row, residual] * residuals[row, residual]
    history[row, 2] = history[row, 1]
    history[row, 1] = history[row, 0]
    history[row, 0] = cost
    steps[row] = step + 1
    settled = step >= 2 and wp.abs(history[row, 2] - cost) <= COST_DONE * cost
    if norms[row] < STEP_DONE or settled:
        active[row] = 0


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
    history = wp.zeros((rows, 3), dtype=wp.float32, device=device)
    active = wp.ones(rows, dtype=wp.int32, device=device)
    steps = wp.zeros(rows, dtype=wp.int32, device=device)
    for step in range(most_steps):
        context = optimizer._ctx_solver(current)
        optimizer._residuals_analytic(context)
        jacobian = optimizer._jacobian_at(context)
        wp.launch(_to_mujoco, dim=(rows, coords), inputs=[current], outputs=[qpos], device=device)
        full, norms = damped_step(reduction, jacobian, context.residuals, qpos, active)
        optimizer._integrate_dq(current, dq_in=full, joint_q_out=following, joint_qd_out=velocity)
        wp.launch(_to_mujoco, dim=(rows, coords), inputs=[following], outputs=[qpos], device=device)
        project(projection, qpos, seeds)
        wp.launch(_to_newton, dim=(rows, coords), inputs=[qpos], outputs=[current], device=device)
        wp.launch(_stopped, dim=rows, inputs=[context.residuals, norms, history, step, active, steps], device=device)
        if step % 10 == 9 and not active.numpy().any():
            break
    if active.numpy().any():
        raise NotConverged(f"{int(active.numpy().sum())} rows did not stop in {most_steps} steps")
    wp.launch(_to_mujoco, dim=(rows, coords), inputs=[current], outputs=[qpos], device=device)
    return qpos, steps
