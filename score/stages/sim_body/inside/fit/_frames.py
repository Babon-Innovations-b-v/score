"""Every frame's joint angles by mink (github.com/kevinzakka/mink, Apache-2.0, pinned 1.3.0 in newton_env.sh), MuJoCo's
inverse kinematics: per frame one quadratic program a step, run to convergence (an offline fit, no real-time rate), the
bone groups' turns (orientation-only `FrameTask`s on the calibration sites, the main term), the landmarks' markers and
the joint centres they give (position-only `FrameTask`s on the marker and centre sites) weighed as OpenSim's IK weighs
its goals (each goal's squared errors over its own count: `weights`), the model's couplings held exactly
(`EqualityConstraintTask` as a constraint, OpenSim's default), the leading joints kept in their ranges
(`ConfigurationLimit`), the joints no target sees frozen (`DofFreezingTask`). Each frame starts from the one before."""
import mink
import mujoco
import numpy as np

SOLVER = "daqp"  # the QP solver every mink example uses; pinned with mink
STEP_DONE = 1e-8  # a step this small (the tangent step's norm) ends a frame's fit
MOST_STEPS = 300  # a frame not converged by then fails the run: never kept silently
LM_DAMPING = 1e-3  # mink's Levenberg-Marquardt term on each task: shapes a step, never moves the optimum
DAMPING = 1e-9


class NotConverged(RuntimeError):
    """A frame whose fit did not converge in MOST_STEPS."""


def solved(configuration, tasks, limits, constraints, refresh=None):
    """mink's steps on `configuration` (from where it stands) until a step is under STEP_DONE: its qpos; `refresh`,
    when given, sets the targets again before each step. Not converged in MOST_STEPS raises NotConverged."""
    for _ in range(MOST_STEPS):
        if refresh is not None:
            refresh()
        velocity = mink.solve_ik(configuration, tasks, 1.0, SOLVER, damping=DAMPING, limits=limits,
                                 constraints=constraints)
        configuration.integrate_inplace(velocity, 1.0)
        if np.linalg.norm(velocity) < STEP_DONE:
            return configuration.q.copy()
    raise NotConverged(f"a frame's fit did not converge in {MOST_STEPS} steps (its last step "
                       f"{np.linalg.norm(velocity)})")


def weights(fitting):
    """Each turn task's cost and each place task's (markers', then the joint centres' they give): OpenSim's IK
    normalises each goal by its own weight sum (Simbody's OrientationSensors and Markers goals, every weight 1, as
    OpenSense's), here two goals, the turns and the markers (the joint-centre markers among them; SOMA's own joints are
    no goal, #70 2026-10-29: they are the measure); a mink cost multiplies the error, so the cost is one over the
    goal's count's square root."""
    places = len(fitting.place_sites)
    return 1.0 / np.sqrt(max(len(fitting.frame_sites), 1)), np.full(places, 1.0 / np.sqrt(max(places, 1)))


class Frames:
    """mink's tasks, limits and constraints on a `Fitting`; `fitted` gives the clip's angles (frames x nq)."""

    def __init__(self, fitting):
        self.fitting = fitting
        model = fitting.model
        turn_cost, place_costs = weights(fitting)
        self.turns = [mink.FrameTask(site, "site", position_cost=0.0, orientation_cost=turn_cost,
                                     lm_damping=LM_DAMPING) for site in fitting.frame_sites]
        self.marks = [mink.FrameTask(site, "site", position_cost=cost, orientation_cost=0.0, lm_damping=LM_DAMPING)
                      for site, cost in zip(fitting.place_sites, place_costs)]
        self.limits = [mink.ConfigurationLimit(fitting.limited_model(), gain=1.0)]
        self.constraints = [mink.EqualityConstraintTask(model, cost=1.0, gain=1.0)] if model.neq else []
        if fitting.frozen:
            self.constraints.append(mink.DofFreezingTask(model, dof_indices=fitting.frozen))
        self.configuration = mink.Configuration(model)

    def _targets(self, turns, points):
        """The frame's targets set: each group site's world turn (MuJoCo's frame); each marker's place, its target
        turn its site's own, so mink's SE(3) error is the plain place error (its V^-1 term vanishes)."""
        for task, turn in zip(self.turns, turns):
            task.set_target(mink.SE3.from_rotation(mink.SO3.from_matrix(turn)))
        self._marked(points)

    def _marked(self, points):
        """Each place task's target: its point, turned as its site turns now."""
        configuration = self.configuration
        for task, point in zip(self.marks, points):
            turn = configuration.get_transform_frame_to_world(task.frame_name, "site").rotation()
            task.set_target(mink.SE3.from_rotation_and_translation(turn, point))

    def frame(self, qpos, turns, points):
        """One frame's angles (qpos) from `qpos`, to convergence."""
        self.configuration.update(qpos)
        self._targets(turns, points)
        return solved(self.configuration, self.turns + self.marks, self.limits, self.constraints,
                      lambda: self._marked(points))

    def start(self, turns, points):
        """The first frame's start: the standing pose, its root turned so the first group's site turns as its target
        and moved so the markers' mean is the targets'."""
        model, data = self.fitting.model, mujoco.MjData(self.fitting.model)
        qpos = self.fitting.standing()
        data.qpos[:] = qpos
        mujoco.mj_kinematics(model, data)
        site = self.fitting.frame_sites[0]
        now = data.site_xmat[site].reshape(3, 3)
        turn = turns[0] @ now.T @ data.xmat[model.jnt_bodyid[0]].reshape(3, 3)
        mujoco.mju_mat2Quat(qpos[3:7], turn.reshape(-1))
        data.qpos[:] = qpos
        mujoco.mj_kinematics(model, data)
        qpos[:3] += np.mean(points, axis=0) - np.mean(data.site_xpos[self.fitting.place_sites], axis=0)
        return qpos

    def fitted(self, turns, points, start=None):
        """Every frame's angles (frames x nq): `turns` frames x groups x 3 x 3 and `points` frames x place sites x 3
        (the markers', then the joint centres'), both MuJoCo's frame; each frame from the one before, the first from
        `start` (else `start()`)."""
        qpos = self.start(turns[0], points[0]) if start is None else start
        found = []
        for frame_turns, frame_points in zip(turns, points):
            qpos = self.frame(qpos, frame_turns, frame_points)
            found.append(qpos)
        return np.array(found)
