"""RRA's linear part: what a state asks of the body (the needed wrench at the pelvis and the lumbar's needed moments),
what the ground's pushes alone leave of it (the residual), each frame's state, the dofs RRA moves, a path moved by
them, and the residual's and lumbar's change with each frame's move, linearised."""
import mujoco
import numpy as np

from bone_groups import TRUNK
from model import limited, rates
from muscles import BALANCE, CONTACT_COST
from solvers import least, stencils

RRA_STEP = 1e-5  # the central differences' step (m, rad)


def about(model, data, generalised, origin):
    """The pelvis' six rows of a generalised force as a world wrench (force, then moment about `origin`, MuJoCo's
    frame): the free joint's force is the world's, its moment the root body's about its own origin."""
    root = model.jnt_bodyid[0]
    force = generalised[:3]
    moment = data.xmat[root].reshape(3, 3) @ generalised[3:6] + np.cross(data.xpos[root] - origin, force)
    return np.concatenate([force, moment])


def balance(physics, qpos, qvel, qacc, origin):
    """The wrench the movement needs at the pelvis (about `origin`), the ground's pushes' wrenches (6 x pushes) and
    what the pushes cannot give of it: the pelvis' rows of `Physics.shared` alone (muscles and joint stops put no net
    force on the whole body), the same weights."""
    model, data = physics.model, physics.data
    needed = about(model, data, physics.needed(qpos, qvel, qacc), origin)
    columns = [about(model, data, along.T @ edge, origin) for _, along, edges in physics.contacts() for edge in edges]
    pushes = np.array(columns).T if columns else np.zeros((6, 0))
    pushed = least(BALANCE * pushes, BALANCE * needed, np.full(pushes.shape[1], CONTACT_COST),
                   np.full(pushes.shape[1], np.inf))
    return needed, needed - pushes @ pushed


def demands(physics, qpos, qvel, qacc, origin, trunk):
    """What a state asks of the body: the needed wrench about `origin` (6) and the needed moments at the `trunk`
    leading dofs (the lumbar's, N m: what its muscles must give, or its reserves)."""
    needed = physics.needed(qpos, qvel, qacc)
    return np.concatenate([about(physics.model, physics.data, needed, origin),
                           (physics.couplings.map(qpos).T @ needed)[trunk]])


def trunk_moments(physics, states, trunk):
    """Each frame's needed moments at the `trunk` leading dofs (frames x trunk)."""
    return np.array([demands(physics, *state, trunk)[6:] for state in states])


def sensitivity(physics, qpos, qvel, qacc, origin, adjusted):
    """d(what the state asks: `demands`, the trunk the adjusted lumbar leaders) / d(each `adjusted` leading dof's
    place, speed and acceleration): three (6 + trunk) x adjusted matrices, by central differences of inverse
    dynamics."""
    model, couplings = physics.model, physics.couplings
    mapped = couplings.map(qpos)
    found = [np.zeros((len(adjusted), len(adjusted))) for _ in range(3)]  # 6 wrench rows and the trunk's
    for column, lead in enumerate(adjusted):
        step = mapped[:, lead] * RRA_STEP
        for sign in (1.0, -1.0):
            placed = qpos.copy()
            mujoco.mj_integratePos(model, placed, sign * step, 1.0)
            for kind, state in enumerate(((couplings.apply(placed), qvel, qacc), (qpos, qvel + sign * step, qacc),
                                          (qpos, qvel, qacc + sign * step))):
                found[kind][:, column] += sign * demands(physics, *state, origin, adjusted[6:]) / (2 * RRA_STEP)
    return found


def adjusted_leads(physics):
    """The leading dofs RRA adjusts here (the owner's: the pelvis and the trunk): the root's six and the lumbar's
    leaders (TRUNK), as columns of the couplings' map."""
    model, leads = physics.model, physics.couplings.leads
    names = [mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, model.dof_jntid[dof]) for dof in leads]
    trunk = [column for column, name in enumerate(names) if column >= 6 and name.endswith(TRUNK)]
    if len(trunk) != len(TRUNK):
        raise ValueError(f"the model's lumbar leaders {TRUNK} not found once each: {len(trunk)} found")
    return [0, 1, 2, 3, 4, 5, *trunk]


def moved(physics, path, adjustment, adjusted):
    """`path` with each frame's adjustment (frames x adjusted, the leading dofs' own units: metres, radians) added."""
    model, couplings = physics.model, physics.couplings
    found = []
    for qpos, change in zip(path, adjustment):
        leads = np.zeros(len(couplings.leads))
        leads[adjusted] = change
        qpos = qpos.copy()
        mujoco.mj_integratePos(model, qpos, couplings.map(qpos) @ leads, 1.0)
        found.append(limited(model, qpos, couplings))
    return np.array(found)


def frame_states(physics, path, rate):
    """Each frame's speeds, accelerations (`rates`) and the pelvis' origin (MuJoCo's frame), the residuals' point."""
    model, data = physics.model, physics.data
    velocities, accelerations = rates(model, path, rate)
    origins = []
    for qpos in path:
        data.qpos[:] = qpos
        mujoco.mj_kinematics(model, data)
        origins.append(data.xpos[model.jnt_bodyid[0]].copy())
    return list(zip(path, velocities, accelerations, origins))


def residuals(physics, states):
    """Each frame's residual after the ground's pushes alone (`balance`; frames x 6)."""
    return np.array([balance(physics, *state)[1] for state in states])


def linearised(physics, states, adjusted, rate, scale):
    """The residuals' and the trunk's moments' change with each frame's move of the `adjusted` dofs ((6 + trunk)
    frames x frames adjusted, over `scale`): each frame's sensitivity to its place, speed and acceleration, the speeds
    and accelerations `rates`' own differences of the places."""
    count, width = len(states), len(adjusted)
    rows = width
    speeds, accelerations = stencils(count, rate)
    system = np.zeros((rows * count, count * width))
    for frame, state in enumerate(states):
        places, speed, acceleration = sensitivity(physics, *state, adjusted)
        for other in range(max(frame - 2, 0), min(frame + 3, count)):
            block = speed * speeds[frame, other] + acceleration * accelerations[frame, other]
            system[rows * frame:rows * (frame + 1), other * width:(other + 1) * width] = block + (
                places if other == frame else 0.0)
    return system / scale[:, None]
