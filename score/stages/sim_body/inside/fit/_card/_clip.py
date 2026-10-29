"""A clip's level 3 on the card (#70, plan step 5's first piece): the card loop (`_solve`) set up from a fitted MuJoCo
model as `../_frames.Frames` sets mink up (the turns' and the markers' sites and costs, the couplings held, the leading
joints in their followers-free ranges, the frozen dofs), every frame one row seeded on its own (`_seeds`). The
prototype's setup (the card build's gate.py) made production; mink in `../_frames.py` stays the reference."""
import mujoco
import numpy as np
import warp as wp
from scipy.spatial.transform import Rotation

from ._objective import PlacePerProblem, TurnPerProblem
from ._project import Projection
from ._seeds import newton_order
from ._solve import solved_in_chunks
from ._step import Reduction

BIG = 1e30  # a bound that never holds
DEVICE = "cuda:0"
LIMITED_TYPES = (int(mujoco.mjtJoint.mjJNT_SLIDE), int(mujoco.mjtJoint.mjJNT_HINGE))


def couplings(mjm):
    """The model's active joint couplings [(follower coord, leader coord or -1, polycoef[5])]."""
    return [(int(mjm.jnt_qposadr[mjm.eq_obj1id[index]]),
             int(mjm.jnt_qposadr[mjm.eq_obj2id[index]]) if mjm.eq_obj2id[index] >= 0 else -1,
             np.array(mjm.eq_data[index, :5], dtype=float))
            for index in range(mjm.neq)
            if int(mjm.eq_type[index]) == int(mujoco.mjtEq.mjEQ_JOINT) and mjm.eq_active0[index]]


def coordinate_bounds(limited):
    """(lower, upper) per coordinate [nq]: a limited slide's or hinge's range, else +-BIG."""
    lower, upper = np.full(limited.nq, -BIG), np.full(limited.nq, BIG)
    for joint in range(limited.njnt):
        if limited.jnt_limited[joint] and int(limited.jnt_type[joint]) in LIMITED_TYPES:
            lower[limited.jnt_qposadr[joint]], upper[limited.jnt_qposadr[joint]] = limited.jnt_range[joint]
    return lower, upper


def dof_coordinates(mjm):
    """Each dof's coordinate [nv]: a free joint's six dofs all its first coordinate, a slide's or hinge's its own."""
    found = np.zeros(mjm.nv, dtype=int)
    for joint in range(mjm.njnt):
        if int(mjm.jnt_type[joint]) == int(mujoco.mjtJoint.mjJNT_FREE):
            found[mjm.jnt_dofadr[joint]:mjm.jnt_dofadr[joint] + 6] = mjm.jnt_qposadr[joint]
        else:
            found[mjm.jnt_dofadr[joint]] = mjm.jnt_qposadr[joint]
    return found


def reduction_of(mjm, limited, frozen):
    """The reduced dofs (`_step.Reduction`): the frozen dofs and the followers out, each follower on its leader."""
    coupled, (lower, upper), coordinate = couplings(mjm), coordinate_bounds(limited), dof_coordinates(mjm)
    dof_of = {int(coordinate[dof]): dof for dof in range(mjm.nv) if dof >= 6 or coordinate[dof] != 0}
    followers = {dof_of[follower] for follower, _, _ in coupled}
    free = [dof for dof in range(mjm.nv) if dof not in set(frozen) and dof not in followers]
    rooted = lambda dof: dof < 6 and int(mjm.jnt_type[0]) == int(mujoco.mjtJoint.mjJNT_FREE)
    return Reduction(free, [int(coordinate[dof]) for dof in free],
                     [-BIG if rooted(dof) else lower[coordinate[dof]] for dof in free],
                     [BIG if rooted(dof) else upper[coordinate[dof]] for dof in free],
                     [dof_of[follower] for follower, _, _ in coupled],
                     [dof_of[leader] if leader >= 0 else -1 for _, leader, _ in coupled],
                     [leader for _, leader, _ in coupled],
                     [mjm.qpos0[leader] if leader >= 0 else 0.0 for _, leader, _ in coupled],
                     np.array([poly for _, _, poly in coupled]).reshape(-1, 5), DEVICE)


def projection_of(mjm, limited, frozen):
    """The exact projection (`_project.Projection`): ranges (the root's coordinates never), followers, frozen."""
    coupled, (lower, upper), coordinate = couplings(mjm), coordinate_bounds(limited), dof_coordinates(mjm)
    lower[:7], upper[:7] = -BIG, BIG
    return Projection(list(lower), list(upper), [follower for follower, _, _ in coupled],
                      [leader for _, leader, _ in coupled], [mjm.qpos0[follower] for follower, _, _ in coupled],
                      [mjm.qpos0[leader] if leader >= 0 else 0.0 for _, leader, _ in coupled],
                      np.array([poly for _, _, poly in coupled]).reshape(-1, 5),
                      [int(coordinate[dof]) for dof in frozen], DEVICE)


def card(values, kind):
    """A float32 card array of `values` as Warp type `kind`."""
    return wp.array(np.ascontiguousarray(values, dtype=np.float32), dtype=kind, device=DEVICE)


class Clip:
    """The card loop's parts for one fitted model: `newton_model` built from the model's own MJCF (its bodies where
    the constants put them), `mjm` the MuJoCo model with the fit's sites, `frame_sites` / `place_sites` its turn and
    marker sites, `turn_cost` / `place_costs` `_frames.weights`', `frozen` dofs, `limited` the followers-free copy."""

    def __init__(self, newton_model, mjm, frame_sites, place_sites, turn_cost, place_costs, frozen, limited):
        if newton_model.joint_coord_count != mjm.nq or newton_model.joint_dof_count != mjm.nv:
            raise ValueError(f"Newton's {newton_model.joint_coord_count} coords / {newton_model.joint_dof_count} dofs"
                             f" against MuJoCo's {mjm.nq} / {mjm.nv}")
        self.model, self.mjm = newton_model, mjm
        self.frame_sites, self.place_sites = list(frame_sites), list(place_sites)
        self.turn_cost, self.place_costs = float(turn_cost), np.asarray(place_costs, dtype=float)
        self.body = {label.split("/")[-1]: index for index, label in enumerate(newton_model.body_label)}
        self.reduction = reduction_of(mjm, limited, frozen)
        self.projection = projection_of(mjm, limited, frozen)

    def link(self, site):
        """The Newton body a MuJoCo site rides."""
        return self.body[self.mjm.body(int(self.mjm.site_bodyid[site])).name]

    def optimizer_for(self, turns, points):
        """optimizer_for(start, stop) for `_solve.solved_in_chunks`: Newton's IKOptimizerLM on rows start:stop."""
        from newton import ik

        def made(start, stop):
            rows = stop - start
            objectives = [TurnPerProblem(self.link(site), card(np.tile(self.mjm.site_quat[site][[1, 2, 3, 0]],
                                                                       (rows, 1)), wp.quat),
                                         card(Rotation.from_matrix(turns[start:stop, group]).as_quat(), wp.vec4),
                                         card(np.full(rows, self.turn_cost), wp.float32))
                          for group, site in enumerate(self.frame_sites)]
            objectives += [PlacePerProblem(self.link(site), card(np.tile(self.mjm.site_pos[site], (rows, 1)), wp.vec3),
                                           card(points[start:stop, mark], wp.vec3),
                                           card(np.full(rows, cost), wp.float32))
                           for mark, (site, cost) in enumerate(zip(self.place_sites, self.place_costs))]
            return ik.IKSolver(self.model, rows, objectives, optimizer="lm",
                               jacobian_mode=ik.IKJacobianType.ANALYTIC)._impl
        return made

    def angles(self, turns, points, seeds):
        """Every frame's angles (frames x nq, MuJoCo's layout) and steps, each frame from its own seed [frames, nq]:
        `turns` frames x groups x 3 x 3, `points` frames x markers x 3."""
        seeds = np.asarray(seeds, dtype=float)
        return solved_in_chunks(self.optimizer_for(np.asarray(turns), np.asarray(points)), self.reduction,
                                self.projection, newton_order(seeds), seeds)
