"""The person's constants by scipy's `least_squares` with bounds, solved together with the angles of the frames given
as one sparse problem (the recipe of 2026-10-28: alternating mink's angles and the constants converged linearly, a
length error half absorbed by the angles each round, where the joint problem reached machine precision in 17
evaluations on 30 frames): the unknowns are each bone group's size factor, each placed joint centre's move in its
parent, each marker's move on its body, and each frame's leading coordinates (the root's place and its turn as a
rotation vector off mink's, each leading hinge and slide; a follower set from its leader by the model's coupling, the
held fingers as they stand); the rows are every frame's turn errors and marker place errors, weighed as mink weighs
them (`_frames.weights`, OpenSim's), a prior row per marker move of the same weight (a marker's move and its
body's place trade one for one; its landmark's place on the SOMA mesh is its start) and a row per bone group holding
its stretch to SOMA's length (LENGTH_WEIGHT). The leading joints' ranges are
the box bounds; the followers' own are not held (`Fitting.limited_model`)."""
import mujoco
import numpy as np
from scipy.optimize import least_squares
from scipy.sparse import lil_matrix
from scipy.spatial.transform import Rotation

from fit._frames import weights

SIZE_MOST = 0.1  # a group's size factor within 1 -+ this of the sizing's (SOMA's joint distances)
JOINT_MOST = 0.04  # metres a joint centre may move in its parent (the hips stand 33 mm a side narrower than SOMA's)
MARK_MOST = 0.03  # metres a marker may move on its body (the landmarks' soft tissue: -8 to 44 mm)
# A bone group's stretch at the standing pose held to SOMA's length (SOMA is the truth, its size too): a millimetre
# off costs as 10 cm of marker error. Without it the markers shortened the legs by 2 to 3 cm a segment (their landmark
# joint centres stand 4 to 24 mm off SOMA's joints); at 10 they still took 15 to 18 mm off the thighs and shins
# (2026-10-28, both test walkers).
LENGTH_WEIGHT = 100.0
INSIDE = 1e-9  # a start this far inside its bounds (least_squares wants a start within them)


class Problem:
    """The joint problem on a `Fitting` over the frames of `path` (frames x nq, mink's, the charts' centres) with
    their targets `turns` (frames x groups x 3 x 3) and `points` (frames x markers x 3)."""

    def __init__(self, fitting, path, turns, points):
        self.fitting, self.path, self.turns, self.points = fitting, np.asarray(path), turns, points
        model = fitting.model
        frozen = set(fitting.frozen)
        self.root = model.jnt_qposadr[0] if model.jnt_type[0] == mujoco.mjtJoint.mjJNT_FREE else None
        self.leading = [joint for joint in fitting.leaders if model.jnt_type[joint] != mujoco.mjtJoint.mjJNT_FREE
                        and model.jnt_dofadr[joint] not in frozen]
        self.width = (6 if self.root is not None else 0) + len(self.leading)
        self.costs = weights(fitting)
        self.data, self.standing = mujoco.MjData(model), mujoco.MjData(model)

    def _qpos(self, frame, values):
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

    def start(self, constants):
        """The unknowns' start: the constants, then each frame's coordinates at mink's angles."""
        model, found = self.fitting.model, [np.asarray(constants, dtype=float)]
        for qpos in self.path:
            root = [qpos[self.root:self.root + 3], np.zeros(3)] if self.root is not None else []
            found.append(np.concatenate([*root, qpos[model.jnt_qposadr[self.leading]]]))
        return np.concatenate(found)

    def bounds(self):
        """The constants' bounds, then each frame's: the leading joints' ranges (unbounded where unlimited)."""
        fitting, model = self.fitting, self.fitting.model
        sizes, joints, marks = len(fitting.sizes), 3 * len(fitting.joints), 3 * len(fitting.marks)
        most = np.concatenate([np.full(sizes, SIZE_MOST), np.full(joints, JOINT_MOST), np.full(marks, MARK_MOST)])
        middle = np.concatenate([np.ones(sizes), np.zeros(joints + marks)])
        limited = model.jnt_limited[self.leading].astype(bool)
        low = np.where(limited, model.jnt_range[self.leading, 0], -np.inf)
        high = np.where(limited, model.jnt_range[self.leading, 1], np.inf)
        free = np.full(6 if self.root is not None else 0, np.inf)
        frames = len(self.path)
        return (np.concatenate([middle - most, np.tile(np.concatenate([-free, low]), frames)]),
                np.concatenate([middle + most, np.tile(np.concatenate([free, high]), frames)]))

    def residuals(self, unknowns):
        """Every frame's weighed turn errors (the geodesic angle's rotation vector, mink's) and marker errors, then the
        markers' moves, then the stretches' lengths off SOMA's."""
        fitting, data, model = self.fitting, self.data, self.fitting.model
        constants = unknowns[:fitting.width()]
        fitting.apply(constants)
        turn_cost, place_costs = self.costs
        mark_cost = place_costs[0] if len(place_costs) else 0.0
        found = []
        for frame in range(len(self.path)):
            values = unknowns[fitting.width() + frame * self.width:fitting.width() + (frame + 1) * self.width]
            data.qpos[:] = self._qpos(frame, values)
            mujoco.mj_kinematics(model, data)
            seen = data.site_xmat[fitting.frame_sites].reshape(-1, 3, 3)
            off = Rotation.from_matrix(np.transpose(seen, (0, 2, 1)) @ self.turns[frame]).as_rotvec()
            found += [turn_cost * off.ravel(),
                      (place_costs[:, None] * (data.site_xpos[fitting.place_sites] - self.points[frame])).ravel()]
        found.append(mark_cost * fitting.unpack(constants)[2].ravel())
        lengths, soma = fitting.lengths(constants, self.standing)
        found.append(LENGTH_WEIGHT * mark_cost * (lengths - soma))
        return np.concatenate(found)

    def sparsity(self):
        """Which unknowns each row reads: a frame's turn rows its own coordinates; its place rows those and every size
        and joint constant, a marker's its own move too; a prior row its own move; a length row every size and joint
        constant."""
        fitting = self.fitting
        sizes_joints, marks, groups = len(fitting.sizes) + 3 * len(fitting.joints), len(fitting.marks), len(
            fitting.frame_sites)
        per = 3 * (groups + len(fitting.place_sites))
        frames = len(self.path)
        stretches = len(fitting.stretches)
        found = lil_matrix((frames * per + 3 * marks + stretches, fitting.width() + frames * self.width), dtype=int)
        for frame in range(frames):
            rows = slice(frame * per, (frame + 1) * per)
            found[rows, fitting.width() + frame * self.width:fitting.width() + (frame + 1) * self.width] = 1
            marked = slice(frame * per + 3 * groups, (frame + 1) * per)
            found[marked, :sizes_joints] = 1
            for mark in range(marks):
                for axis in range(3):
                    found[frame * per + 3 * groups + 3 * mark + axis, sizes_joints + 3 * mark + axis] = 1
        for mark in range(marks):
            for axis in range(3):
                found[frames * per + 3 * mark + axis, sizes_joints + 3 * mark + axis] = 1
        found[frames * per + 3 * marks:, :sizes_joints] = 1
        return found


def constants(fitting, path, turns, points, start):
    """The constants (vector, as `Fitting.unpack` reads it) and the frames' angles (frames x nq) that best meet the
    frames' targets together, from `start` and mink's `path`; the model is left with the constants laid on, and the
    solve's evaluation count."""
    problem = Problem(fitting, path, turns, points)
    low, high = problem.bounds()
    begin = problem.start(start)
    begin = np.clip(begin, np.where(np.isfinite(low), low + INSIDE, low), np.where(np.isfinite(high), high - INSIDE,
                                                                                    high))
    found = least_squares(problem.residuals, begin, bounds=(low, high), jac_sparsity=problem.sparsity(),
                          x_scale="jac", method="trf", tr_solver="lsmr")
    width = fitting.width()
    fitting.apply(found.x[:width])
    angles = np.array([problem._qpos(frame, found.x[width + frame * problem.width:width + (frame + 1) * problem.width])
                       for frame in range(len(path))])
    return found.x[:width], angles, int(found.nfev)
