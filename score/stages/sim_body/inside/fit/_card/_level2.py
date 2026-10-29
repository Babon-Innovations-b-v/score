"""Level 2's exact Jacobian (plan step 4): the Jacobian of `fit._constants.Problem.residuals` in its own sparse
pattern (`Problem.sparsity`), analytic, for scipy's `least_squares(jac=...)` in place of its 2-point differences, the
optimiser and its stopping unchanged. Per frame, the unknowns reach the dofs by `dof_map` (the root's place one for one,
its rotation vector off mink's turn through SO(3)'s right Jacobian, MuJoCo's free joint turning in its body's frame; a
leading joint its own dof and each follower's by its polynomial's slope); a place row is its site's place Jacobian
through that, a turn row (the log of R_site^T R_target) its site's turn Jacobian through -J_l^-1(log) R_site^T; a
marker's move reaches its site through its body's turn, an inside joint's move every site it carries through its
parent's turn; a prior row its constant's weight. The frames' kinematics come from MuJoCo in float64 on the host
(`Kinematics`, the reference) or from the card (`_level2_card`, float32)."""
import mujoco
import numpy as np
from scipy.sparse import csr_matrix


def skew(vector):
    """The cross-product matrix of a 3-vector."""
    return np.array([[0.0, -vector[2], vector[1]], [vector[2], 0.0, -vector[0]], [-vector[1], vector[0], 0.0]])


def right_jacobian(rotation):
    """SO(3)'s right Jacobian at a rotation vector: R(v + dv) = R(v) exp(J_r(v) dv)."""
    angle, cross = np.linalg.norm(rotation), skew(rotation)
    if angle < 1e-8:
        return np.eye(3) - 0.5 * cross
    return (np.eye(3) - (1 - np.cos(angle)) / angle ** 2 * cross
            + (angle - np.sin(angle)) / angle ** 3 * cross @ cross)


def left_jacobian_inverse(rotation):
    """SO(3)'s inverse left Jacobian at a rotation vector: log(exp(d) R) = log(R) + J_l^-1 d."""
    angle, cross = np.linalg.norm(rotation), skew(rotation)
    if angle < 1e-8:
        return np.eye(3) - 0.5 * cross
    factor = 1 / angle ** 2 - (1 + np.cos(angle)) / (2 * angle * np.sin(angle))
    return np.eye(3) - 0.5 * cross + factor * cross @ cross


def couplings(model):
    """Each joint coupling as (follower joint, leader joint, polynomial coefficients); a lock (no leader) left out."""
    return [(int(model.eq_obj1id[eq]), int(model.eq_obj2id[eq]), model.eq_data[eq, :5].copy())
            for eq in range(model.neq) if model.eq_type[eq] == mujoco.mjtEq.mjEQ_JOINT and model.eq_obj2id[eq] >= 0]


def dof_map(problem, qpos, rotation):
    """How a frame's leading coordinates move the dofs (nv x width): the root's place one for one, its rotation vector
    by J_r, a leader its own dof, a follower by d polyval / d leader at the frame's `qpos`."""
    model = problem.fitting.model
    found = np.zeros((model.nv, problem.width))
    start = 0
    if problem.root is not None:
        dof = model.jnt_dofadr[0]
        found[dof:dof + 3, :3] = np.eye(3)
        found[dof + 3:dof + 6, 3:6] = right_jacobian(rotation)
        start = 6
    column = {int(joint): start + index for index, joint in enumerate(problem.leading)}
    for joint, at in column.items():
        found[model.jnt_dofadr[joint], at] = 1.0
    for follower, leader, coefficients in couplings(model):
        if leader in column:
            moved = qpos[model.jnt_qposadr[leader]] - model.qpos0[model.jnt_qposadr[leader]]
            slope = sum(power * coefficients[power] * moved ** (power - 1) for power in range(1, 5))
            found[model.jnt_dofadr[follower], column[leader]] += slope
    return found


class Kinematics:
    """One frame's kinematics on the fitting model (MuJoCo, float64): the sites' places and turns, their place and
    turn Jacobians (world frame, dofs), each body's turn."""

    def __init__(self, fitting, qpos):
        model = fitting.model
        data = mujoco.MjData(model)
        data.qpos[:] = qpos
        mujoco.mj_kinematics(model, data)
        mujoco.mj_comPos(model, data)
        self.site_turns = data.site_xmat[fitting.frame_sites].reshape(-1, 3, 3).copy()
        self.body_turns = data.xmat.reshape(-1, 3, 3).copy()
        self.places = np.zeros((len(fitting.place_sites), 3, model.nv))
        self.spins = np.zeros((len(fitting.frame_sites), 3, model.nv))
        for index, site in enumerate(fitting.place_sites):
            mujoco.mj_jacSite(model, data, self.places[index], None, site)
        for index, site in enumerate(fitting.frame_sites):
            mujoco.mj_jacSite(model, data, None, self.spins[index], site)


def frame_rows(problem, frame, kinematics, targets, values):
    """A frame's rows of the Jacobian (3 (groups + markers) x unknowns, dense): its coordinates' columns, the free
    markers' and the inside joints' moves."""
    fitting, model = problem.fitting, problem.fitting.model
    turn_cost, place_costs = problem.costs
    held = len(problem.slots)
    qpos = problem.qpos(frame, values)
    rotation = values[3:6] if problem.root is not None else np.zeros(3)
    mapping = dof_map(problem, qpos, rotation)
    groups, marks = len(fitting.frame_sites), len(fitting.place_sites)
    found = np.zeros((3 * (groups + marks), held + len(problem.path) * problem.width))
    own = slice(held + frame * problem.width, held + (frame + 1) * problem.width)
    for group in range(groups):
        seen = kinematics.site_turns[group]
        off = _log(seen.T @ targets[frame][group])
        found[3 * group:3 * group + 3, own] = -turn_cost * left_jacobian_inverse(off) @ seen.T @ (
            kinematics.spins[group] @ mapping)
    placed = 3 * groups
    for mark in range(marks):
        found[placed + 3 * mark:placed + 3 * mark + 3, own] = place_costs[mark] * kinematics.places[mark] @ mapping
    for index, mark in enumerate(problem.free):
        body = model.site_bodyid[fitting.place_sites[mark]]
        found[placed + 3 * mark:placed + 3 * mark + 3, 3 * index:3 * index + 3] = (
            place_costs[mark] * kinematics.body_turns[body])
    for joint, riders in enumerate(fitting.riding):
        column = 3 * (len(problem.free) + joint)
        parent = model.body_parentid[fitting.inside[joint]]
        for mark in riders:
            found[placed + 3 * mark:placed + 3 * mark + 3, column:column + 3] = (
                place_costs[mark] * kinematics.body_turns[parent])
    return found


def _log(turn):
    """A rotation matrix's rotation vector (scipy's, as the residuals take it)."""
    from scipy.spatial.transform import Rotation
    return Rotation.from_matrix(turn).as_rotvec()


def jacobian(problem, unknowns, card=None):
    """The whole Jacobian of `problem.residuals` at `unknowns` (sparse, rows and columns as the residuals and
    `problem.sparsity`), the constants laid on the model as the residuals lay them; the frames' kinematics MuJoCo's on
    the host, or `card`'s (a `_level2_card.CardKinematics` of the problem's frames) when given."""
    fitting = problem.fitting
    fitting.apply(problem.constants(unknowns))
    held = len(problem.slots)
    values = [unknowns[held + frame * problem.width:held + (frame + 1) * problem.width]
              for frame in range(len(problem.path))]
    poses = [problem.qpos(frame, value) for frame, value in enumerate(values)]
    seen = card.frames(np.array(poses)) if card is not None else [Kinematics(fitting, pose) for pose in poses]
    blocks = [csr_matrix(frame_rows(problem, frame, seen[frame], problem.turns, value))
              for frame, value in enumerate(values)]
    return _stacked(problem, blocks)


def _stacked(problem, blocks):
    """The frames' rows stacked over the constants' prior rows (each its constant's weight on its own column)."""
    from scipy.sparse import vstack
    turn_cost, place_costs = problem.costs
    held = len(problem.slots)
    moved = 3 * len(problem.free)
    weights = np.concatenate([np.repeat(place_costs[problem.free], 3),
                              np.full(held - moved, float(np.mean(place_costs)))])
    priors = csr_matrix((weights, (np.arange(held), np.arange(held))),
                        shape=(held, held + len(problem.path) * problem.width))
    return vstack(blocks + [priors], format="csr")
