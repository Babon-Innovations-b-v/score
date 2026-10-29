"""The person's constants by scipy's `least_squares` with bounds, one stage at a time, each solved together with the
angles of the frames given as one sparse problem (the recipe of 2026-10-28: alternating mink's angles and the
constants converged linearly, where the joint problem reached machine precision in 17 evaluations on 30 frames).
A stage's unknowns are its constants (`SIZES`: the size factors, the overall one and each size group's; `MARKS`: each
free marker's move on its body) and each frame's leading coordinates (the root's place and its turn as a rotation
vector off mink's, each leading hinge and slide; a follower set from its leader by the model's coupling, the held
fingers as they stand); the other stage's constants stand as given. The rows are every frame's turn errors and marker
place errors, weighed as mink weighs them (`_frames.weights`, OpenSim's), then a prior row per unknown constant: a
size factor pulled gently to 1 (`SIZE_PULL`, within `SIZE_MOST`; Cotton et al. 2026's staged fit pulls its group
scales to 1 the same way, the idea taken, nothing copied), a marker's move to its landmark's link at its marker's own
weight (a move and its body's place trade one for one), within `MARK_MOST`. Staged as Cotton et al. 2026 stage it
(warm from the stage before; cold, theirs explained the markers with a wrong pose): sizes, then the markers' moves.
The leading joints' ranges are the box bounds; the followers' own are not held (`Fitting.limited_model`)."""
import mujoco
import numpy as np
from scipy.optimize import least_squares
from scipy.sparse import lil_matrix
from scipy.spatial.transform import Rotation

from fit._frames import weights

SIZES, MARKS = "sizes", "marks"
SIZE_MOST = 0.1  # a size factor within 1 -+ this (the landmark sizing's lengths are 1)
SIZE_PULL = 0.05  # a size factor's prior row: this times its distance from 1
MARK_MOST = 0.03  # metres a marker may move on its body off its landmark's link
INSIDE = 1e-9  # a start this far inside its bounds (least_squares wants a start within them)


class Problem:
    """One stage's problem on a `Fitting` over the frames of `path` (frames x nq, the stage before's, the charts'
    centres) with their targets `turns` (frames x groups x 3 x 3) and `points` (frames x markers x 3); `stage` SIZES
    or MARKS, `given` the constants vector the other stage's part is read from, `free` the markers that may move (by
    index; MARKS only)."""

    def __init__(self, fitting, path, turns, points, stage, given, free=()):
        self.fitting, self.path, self.turns, self.points = fitting, np.asarray(path), turns, points
        self.stage, self.given = stage, np.asarray(given, dtype=float)
        model = fitting.model
        frozen = set(fitting.frozen)
        self.root = model.jnt_qposadr[0] if model.jnt_type[0] == mujoco.mjtJoint.mjJNT_FREE else None
        self.leading = [joint for joint in fitting.leaders if model.jnt_type[joint] != mujoco.mjtJoint.mjJNT_FREE
                        and model.jnt_dofadr[joint] not in frozen]
        self.width = (6 if self.root is not None else 0) + len(self.leading)
        sizes = len(fitting.sizes)
        self.slots = (np.arange(sizes) if stage == SIZES else
                      np.array([sizes + 3 * mark + axis for mark in free for axis in range(3)], dtype=int))
        self.free = list(free)
        self.costs = weights(fitting)
        self.data = mujoco.MjData(model)

    def constants(self, unknowns):
        """The whole constants vector: the given one with this stage's unknowns laid in."""
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
        """The unknowns' start: this stage's constants as given, then each frame's coordinates at the path's."""
        model, found = self.fitting.model, [self.given[self.slots]]
        for qpos in self.path:
            root = [qpos[self.root:self.root + 3], np.zeros(3)] if self.root is not None else []
            found.append(np.concatenate([*root, qpos[model.jnt_qposadr[self.leading]]]))
        return np.concatenate(found)

    def bounds(self):
        """This stage's constants' bounds, then each frame's: the leading joints' ranges (unbounded where unlimited)."""
        model = self.fitting.model
        if self.stage == SIZES:
            low, high = np.full(len(self.slots), 1.0 - SIZE_MOST), np.full(len(self.slots), 1.0 + SIZE_MOST)
        else:
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
        stage's prior rows."""
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
        if self.stage == SIZES:
            found.append(SIZE_PULL * (unknowns[:held] - 1.0))
        else:
            found.append((place_costs[self.free][:, None] * unknowns[:held].reshape(-1, 3)).ravel())
        return np.concatenate(found)

    def sparsity(self):
        """Which unknowns each row reads: a frame's turn rows its own coordinates; its place rows those and every size
        factor (SIZES), or a marker's its own move (MARKS); a prior row its own constant."""
        fitting, held = self.fitting, len(self.slots)
        groups, marks = len(fitting.frame_sites), len(fitting.place_sites)
        per = 3 * (groups + marks)
        frames = len(self.path)
        found = lil_matrix((frames * per + held, held + frames * self.width), dtype=int)
        for frame in range(frames):
            found[frame * per:(frame + 1) * per, held + frame * self.width:held + (frame + 1) * self.width] = 1
            placed = frame * per + 3 * groups
            if self.stage == SIZES:
                found[placed:(frame + 1) * per, :held] = 1
            for index, mark in enumerate(self.free):
                found[placed + 3 * mark:placed + 3 * mark + 3, 3 * index:3 * index + 3] = 1
        for slot in range(held):
            found[frames * per + slot, slot] = 1
        return found


def staged(fitting, path, turns, points, stage, given, free=()):
    """One stage's constants (the whole vector, as `Fitting.unpack` reads it) and the frames' angles (frames x nq)
    that best meet the frames' targets together, from `given` and the path of the stage before; the model is left
    with the constants laid on, and the solve's evaluation count."""
    problem = Problem(fitting, path, turns, points, stage, given, free)
    low, high = problem.bounds()
    begin = np.clip(problem.start(), np.where(np.isfinite(low), low + INSIDE, low),
                    np.where(np.isfinite(high), high - INSIDE, high))
    found = least_squares(problem.residuals, begin, bounds=(low, high), jac_sparsity=problem.sparsity(),
                          x_scale="jac", method="trf", tr_solver="lsmr")
    constants = problem.constants(found.x)
    fitting.apply(constants)
    held = len(problem.slots)
    angles = np.array([problem.qpos(frame, found.x[held + frame * problem.width:held + (frame + 1) * problem.width])
                       for frame in range(len(path))])
    return constants, angles, int(found.nfev)
