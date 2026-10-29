"""The person's constants (#70's level 2) by scipy's `least_squares` with bounds, solved together with the angles of
the frames given as one sparse problem (the recipe of 2026-10-28: alternating mink's angles and the constants
converged linearly, where the joint problem reached machine precision in 17 evaluations on 30 frames). The unknowns
are the constants (each free marker's move on its body and each joint inside a bone group's move in its parent; the
lengths are SOMA's, from the sizing, never solved here) and each frame's leading coordinates (the root's place and its turn as a rotation
vector off mink's, each leading hinge and slide; a follower set from its leader by the model's coupling, the held
fingers as they stand); the held markers' moves stand as given. The rows are every frame's turn errors and marker
place errors, weighed as mink weighs them (`_frames.weights`, OpenSim's), then a prior row per unknown constant: a marker's move to its landmark's link at its marker's own
weight (a move and its body's place trade one for one), within `MARK_MOST`; an inside joint's move to its file's
place at the markers' mean weight, within `MARK_MOST` too (as small as a landmark's correction). Warm from mink's
angles at the start constants (Cotton et al. 2026, the idea only: cold, theirs explained the markers with a wrong pose).
The leading joints' ranges are the box bounds; the followers' own are not held (`Fitting.limited_model`)."""
import mujoco
import numpy as np
from scipy.optimize import least_squares
from scipy.sparse import lil_matrix
from scipy.spatial.transform import Rotation

from fit._frames import weights

MARK_MOST = 0.03  # metres a marker may move on its body off its landmark's link
INSIDE = 1e-9  # a start this far inside its bounds (least_squares wants a start within them)


class Problem:
    """The constants' problem on a `Fitting` over the frames of `path` (frames x nq, mink's, the charts' centres) with
    their targets `turns` (frames x groups x 3 x 3) and `points` (frames x markers x 3); `given` the constants vector
    the held markers' moves are read from, `free` the markers that may move (by index)."""

    def __init__(self, fitting, path, turns, points, given, free=()):
        self.fitting, self.path, self.turns, self.points = fitting, np.asarray(path), turns, points
        self.given = np.asarray(given, dtype=float)
        model = fitting.model
        frozen = set(fitting.frozen)
        self.root = model.jnt_qposadr[0] if model.jnt_type[0] == mujoco.mjtJoint.mjJNT_FREE else None
        self.leading = [joint for joint in fitting.leaders if model.jnt_type[joint] != mujoco.mjtJoint.mjJNT_FREE
                        and model.jnt_dofadr[joint] not in frozen]
        self.width = (6 if self.root is not None else 0) + len(self.leading)
        marked = 3 * len(fitting.marks)
        self.slots = np.array([3 * mark + axis for mark in free for axis in range(3)]
                              + [marked + 3 * joint + axis for joint in range(len(fitting.inside)) for axis in range(3)],
                              dtype=int)
        self.free = list(free)
        self.costs = weights(fitting)
        self.data = mujoco.MjData(model)

    def constants(self, unknowns):
        """The whole constants vector: the given one with the unknowns laid in."""
        found = self.given.copy()
        found[self.slots] = unknowns[:len(self.slots)]
        return found

    def qpos(self, frame, values):
        """A frame's qpos from its leading coordinates."""
        qpos = self.path[frame].copy()
        start = 0
        if self.root is not None:
            at = self.root
            qpos[at:at + 3] = values[:3]
            turn = Rotation.from_quat(self.path[frame][at + 3:at + 7], scalar_first=True) * Rotation.from_rotvec(
                values[3:6])
            qpos[at + 3:at + 7] = turn.as_quat(scalar_first=True)
            start = 6
        qpos[self.fitting.model.jnt_qposadr[self.leading]] = values[start:]
        return self.fitting.coupled(qpos)

    def start(self):
        """The unknowns' start: the constants as given, then each frame's coordinates at the path's."""
        model, found = self.fitting.model, [self.given[self.slots]]
        for qpos in self.path:
            root = [qpos[self.root:self.root + 3], np.zeros(3)] if self.root is not None else []
            found.append(np.concatenate([*root, qpos[model.jnt_qposadr[self.leading]]]))
        return np.concatenate(found)

    def bounds(self):
        """The constants' bounds (within MARK_MOST), then each frame's: the leading joints' ranges (unbounded where unlimited)."""
        model = self.fitting.model
        low, high = np.full(len(self.slots), -MARK_MOST), np.full(len(self.slots), MARK_MOST)
        limited = model.jnt_limited[self.leading].astype(bool)
        joint_low = np.where(limited, model.jnt_range[self.leading, 0], -np.inf)
        joint_high = np.where(limited, model.jnt_range[self.leading, 1], np.inf)
        free = np.full(6 if self.root is not None else 0, np.inf)
        frames = len(self.path)
        return (np.concatenate([low, np.tile(np.concatenate([-free, joint_low]), frames)]),
                np.concatenate([high, np.tile(np.concatenate([free, joint_high]), frames)]))

    def residuals(self, unknowns):
        """Every frame's weighed turn errors (the geodesic angle's rotation vector, mink's) and marker errors, then the
        constants' prior rows."""
        fitting, data, model = self.fitting, self.data, self.fitting.model
        constants = self.constants(unknowns)
        fitting.apply(constants)
        turn_cost, place_costs = self.costs
        held = len(self.slots)
        found = []
        for frame in range(len(self.path)):
            values = unknowns[held + frame * self.width:held + (frame + 1) * self.width]
            data.qpos[:] = self.qpos(frame, values)
            mujoco.mj_kinematics(model, data)
            seen = data.site_xmat[fitting.frame_sites].reshape(-1, 3, 3)
            off = Rotation.from_matrix(np.transpose(seen, (0, 2, 1)) @ self.turns[frame]).as_rotvec()
            found += [turn_cost * off.ravel(),
                      (place_costs[:, None] * (data.site_xpos[fitting.place_sites] - self.points[frame])).ravel()]
        moved = 3 * len(self.free)
        found += [(place_costs[self.free][:, None] * unknowns[:moved].reshape(-1, 3)).ravel(),
                  float(np.mean(place_costs)) * unknowns[moved:held]]
        return np.concatenate(found)

    def sparsity(self):
        """Which unknowns each row reads: a frame's turn rows its own coordinates; its place rows those, a marker's
        its own move and the moves of the inside joints it rides below;
        a prior row its own constant."""
        fitting, held = self.fitting, len(self.slots)
        groups, marks = len(fitting.frame_sites), len(fitting.place_sites)
        per = 3 * (groups + marks)
        frames = len(self.path)
        found = lil_matrix((frames * per + held, held + frames * self.width), dtype=int)
        for frame in range(frames):
            found[frame * per:(frame + 1) * per, held + frame * self.width:held + (frame + 1) * self.width] = 1
            placed = frame * per + 3 * groups
            for index, mark in enumerate(self.free):
                found[placed + 3 * mark:placed + 3 * mark + 3, 3 * index:3 * index + 3] = 1
            for joint, riders in enumerate(fitting.riding):
                column = 3 * (len(self.free) + joint)
                for mark in riders:
                    found[placed + 3 * mark:placed + 3 * mark + 3, column:column + 3] = 1
        for slot in range(held):
            found[frames * per + slot, slot] = 1
        return found


def staged(fitting, path, turns, points, given, free=(), jacobian=None):
    """The constants (the whole vector, as `Fitting.unpack` reads it) and the frames' angles (frames x nq) that best
    meet the frames' targets together, from `given` and mink's path; the model is left with the constants laid on,
    and the solve's evaluation count. `jacobian(problem, unknowns)` (the card's exact one, `_card._level2.jacobian`)
    replaces scipy's 2-point differences in the problem's sparse pattern, the reference, when given."""
    problem = Problem(fitting, path, turns, points, given, free)
    low, high = problem.bounds()
    begin = np.clip(problem.start(), np.where(np.isfinite(low), low + INSIDE, low),
                    np.where(np.isfinite(high), high - INSIDE, high))
    exact = {"jac": lambda unknowns: jacobian(problem, unknowns)} if jacobian is not None else {
        "jac_sparsity": problem.sparsity()}
    found = least_squares(problem.residuals, begin, bounds=(low, high), x_scale="jac", method="trf",
                          tr_solver="lsmr", **exact)
    constants = problem.constants(found.x)
    fitting.apply(constants)
    held = len(problem.slots)
    angles = np.array([problem.qpos(frame, found.x[held + frame * problem.width:held + (frame + 1) * problem.width])
                       for frame in range(len(path))])
    return constants, angles, int(found.nfev)
