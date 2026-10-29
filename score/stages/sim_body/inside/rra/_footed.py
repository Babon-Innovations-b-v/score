"""The feet kept where they stood by the legs (`Footing`): a move of the pelvis or trunk leaves the feet, and so the
ground's contacts, as they were. mink per frame, set up as the fit's (`fit.solved`, its solver, step and steps): each
foot body's place and turn a `FrameTask`, the pelvis' height held to its own by FOOTED_HEIGHT (a `FrameTask` on the
root's body, its height alone: mink's `PostureTask` leaves a free joint out), every leading dof but the legs' and the
root's height frozen (`DofFreezingTask`), the couplings held exactly (`EqualityConstraintTask` as a constraint) and the
leading joints in their ranges (`ConfigurationLimit`); a frame that does not converge fails the run
(`fit.NotConverged`), never kept silently. Before #70's one-solver rule (2026-10-29) this was a handwritten damped least
squares, 40 fixed steps, ranges by clipping."""
import mink
import mujoco
import numpy as np
from scipy.spatial.transform import Rotation

import fit

FOOTED_HEIGHT = 0.1  # the weight of a metre of the pelvis' height against one of a foot's place (or a radian of turn)
ROOT_HEIGHT = 2  # the free root's vertical dof (MuJoCo's frame is Z up)


class Footing:
    """mink's tasks, limits and constraints holding `feet` (body ids) on a model and its `couplings`; `footed` gives a
    path with its feet put back."""

    def __init__(self, model, couplings, feet):
        self.model, self.feet = model, list(feet)
        ancestors = set()
        for body in self.feet:
            while body > 0:
                ancestors.add(body)
                body = model.body_parentid[body]
        legs = {ROOT_HEIGHT} | {int(dof) for dof in couplings.leads[6:] if model.dof_bodyid[dof] in ancestors}
        self.tasks = [mink.FrameTask(model.body(body).name, "body", position_cost=1.0, orientation_cost=1.0,
                                     lm_damping=fit.LM_DAMPING) for body in self.feet]
        self.root = int(model.jnt_bodyid[0])
        self.height = mink.FrameTask(model.body(self.root).name, "body", position_cost=[0.0, 0.0, FOOTED_HEIGHT],
                                     orientation_cost=0.0, lm_damping=fit.LM_DAMPING)
        followers = [joint for joint, _, _ in couplings.followers]
        self.limits = [mink.ConfigurationLimit(fit.followers_free(model, followers), gain=1.0)]
        self.constraints = [mink.EqualityConstraintTask(model, cost=1.0, gain=1.0)] if model.neq else []
        self.constraints.append(mink.DofFreezingTask(model, dof_indices=[int(dof) for dof in couplings.leads
                                                                         if int(dof) not in legs]))
        self.configuration = mink.Configuration(model)
        self.data = mujoco.MjData(model)

    def footed(self, path, before):
        """`path` with each foot body put back where it stands in `before`, place and turn, frame by frame, by the
        legs' joints; the pelvis' height held to its own in `path` by FOOTED_HEIGHT: a pelvis raised past what a
        straight leg reaches comes down, or its feet would leave the ground (1 cm up lifted them 9 mm, 600 N of
        residual, 2026-10-28)."""
        found = []
        for qpos, still in zip(path, before):
            self.data.qpos[:] = still
            mujoco.mj_kinematics(self.model, self.data)
            for task, body in zip(self.tasks, self.feet):
                task.set_target(mink.SE3.from_rotation_and_translation(
                    mink.SO3.from_matrix(self.data.xmat[body].reshape(3, 3)), self.data.xpos[body].copy()))
            self.configuration.update(qpos)
            self.height.set_target(self.configuration.get_transform_frame_to_world(self.model.body(self.root).name,
                                                                                   "body"))
            found.append(fit.solved(self.configuration, self.tasks + [self.height], self.limits, self.constraints))
        return np.array(found)

    def off(self, path, before):
        """How far each frame's feet are from where they stand in `before`: the largest place (m) and turn (rad) over
        the feet, frames x 2."""
        found = []
        for qpos, still in zip(path, before):
            here = self._poses(qpos)
            there = self._poses(still)
            found.append([max(np.linalg.norm(a[0] - b[0]) for a, b in zip(here, there)),
                          max(Rotation.from_matrix(a[1].T @ b[1]).magnitude() for a, b in zip(here, there))])
        return np.array(found)

    def _poses(self, qpos):
        """Each foot body's world place and turn at `qpos`."""
        self.data.qpos[:] = qpos
        mujoco.mj_kinematics(self.model, self.data)
        return [(self.data.xpos[body].copy(), self.data.xmat[body].reshape(3, 3).copy()) for body in self.feet]

