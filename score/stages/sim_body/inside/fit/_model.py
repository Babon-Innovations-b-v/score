"""The model the fit solves on (`Fitting`): MuJoCo's own compile of the person's file (it keeps the model's joint
couplings, which mink holds exactly; Newton's model is given the found angles by joint name), with a site on each bone
group's frame body turned by the calibration table (its frame is the SOMA segment's when the group lies as SOMA's
does), a site on each marker's body where the landmark sits, and the person's constants laid on it in place
(`Fitting.apply`): each size group's factor (the overall one times its own) and each marker moved on its body. Only `body_pos` and `site_pos` change: the fit is
kinematics, so nothing else is compiled again."""
import copy
import re

import mujoco
import numpy as np
from scipy.spatial.transform import Rotation

WRAPPER = re.compile(r"__j\d+$")  # a split body's wrapper (`myo._fixes.split`): it is its body's


def own_name(name):
    """A body's name before the split: a wrapper's is its body's."""
    return WRAPPER.sub("", name)


def filed(name):
    """A source model's body name as the person's file writes it (`myo._fixes.renamed`: '-' and spaces to '_')."""
    return name.replace("-", "_").replace(" ", "_")


def followers_free(model, followers):
    """A copy of `model` whose `followers` (joint ids: the joints a coupling sets) have no range of their own: a coupled
    follower's range is narrower than its polynomial over its leader's in 35 of MyoFullBody's 51 couplings, so held,
    it would stop its leader short; OpenSim's assembler bounds the clamped coordinates only."""
    found = copy.deepcopy(model)
    found.jnt_limited[list(followers)] = 0
    return found


OVERALL = "overall"  # the size factor every body takes, beside its own group's


class Fitting:
    """The fitting model and what the constants move. `path` the person's file; `frames` [(group, frame body, R_cal)]:
    one orientation site each, in that order; `marks` [(name, body, local point)]: one marker site each (the place
    sites, `place_sites`); `owners` {source body name: size group}; `own_placed` the bodies placed in their parent by
    their own group's size; `frozen` the bodies whose joints no target sees (held as they stand); `trusts` each
    marker's trust (its weight among the markers; every one 1 when not given); `goal` how many of the first marks
    make the goal's sum (all when not given; the group ends after them weigh against the landmarks' sum). The size factors (`sizes`) are OVERALL,
    then each size group's: a body's size is OVERALL's times its group's."""

    def __init__(self, path, frames, marks, owners, own_placed=(), frozen=(), trusts=None, goal=None):
        spec = mujoco.MjSpec.from_file(str(path))
        for group, body, calibration in frames:
            spec.body(body).add_site(name=f"fit:{group}", quat=Rotation.from_matrix(calibration.T).as_quat(
                scalar_first=True))
        for name, body, local in marks:
            spec.body(body).add_site(name=f"mark:{name}", pos=local)
        self.model = spec.compile()
        model = self.model
        self.groups = [group for group, _, _ in frames]
        self.frame_sites = [mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, f"fit:{group}") for group in self.groups]
        self.marks = [name for name, _, _ in marks]
        self.mark_sites = [mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, f"mark:{name}") for name in self.marks]
        self.place_sites = self.mark_sites
        self.trusts = np.ones(len(self.marks)) if trusts is None else np.asarray(trusts, dtype=float)
        self.goal = len(self.marks) if goal is None else goal
        self.sizes = [OVERALL] + sorted(set(owners.values()))
        group_of = self._groups_of(owners)
        placing = [group_of[body] if own_name(model.body(body).name) in own_placed
                   else group_of[model.body_parentid[body]] for body in range(model.nbody)]
        self.placing = np.array([-1 if group is None else self.sizes.index(group) for group in placing])
        self.carrying = np.array([-1 if group_of[model.site_bodyid[site]] is None
                                  else self.sizes.index(group_of[model.site_bodyid[site]])
                                  for site in self.place_sites])
        self.base = model.body_pos.copy(), model.site_pos.copy()
        self.leaders, self.followers = self._leading()
        self.frozen = [dof for dof in range(model.nv) if self._under(model.dof_bodyid[dof], frozen)]

    def _groups_of(self, owners):
        """Each body's size group (None for the world and a body above every group): its own, else its parent's."""
        model, found = self.model, [None]
        for body in range(1, model.nbody):
            found.append(owners.get(own_name(model.body(body).name), found[model.body_parentid[body]]))
        return found

    def _leading(self):
        """The joints no coupling sets (the free root among them) and the followers."""
        model = self.model
        followers = {int(model.eq_obj1id[equality]) for equality in range(model.neq)
                     if model.eq_type[equality] == mujoco.mjtEq.mjEQ_JOINT}
        return [joint for joint in range(model.njnt) if joint not in followers], sorted(followers)

    def _under(self, body, tops):
        """Whether a body is one of `tops` or below one."""
        model = self.model
        while body > 0:
            if own_name(model.body(body).name) in tops:
                return True
            body = model.body_parentid[body]
        return False

    def width(self):
        """How many constants: a size factor per size group (OVERALL first), three per marker."""
        return len(self.sizes) + 3 * len(self.marks)

    def unpack(self, constants):
        """(size factors, marker moves markers x 3) of a constants vector."""
        sizes = len(self.sizes)
        return np.asarray(constants[:sizes]), np.reshape(constants[sizes:], (-1, 3))

    def neutral(self):
        """The constants that leave the person's file as it is: every factor 1, no marker moved."""
        return np.concatenate([np.ones(len(self.sizes)), np.zeros(3 * len(self.marks))])

    def factors(self, sizes):
        """Each size group's whole factor (OVERALL's times its own; OVERALL's alone for itself)."""
        found = sizes[0] * np.asarray(sizes, dtype=float)
        found[0] = sizes[0]
        return found

    def apply(self, constants):
        """The constants laid on the model in place, from its base: a body's place in its parent by its parent's group
        factor (or its own, `own_placed`), a marker site by its body's group factor and by its own move."""
        sizes, marks = self.unpack(constants)
        factors = self.factors(sizes)
        body_pos, site_pos = self.base
        scale = np.where(self.placing >= 0, factors[np.maximum(self.placing, 0)], 1.0)
        self.model.body_pos[:] = body_pos * scale[:, None]
        self.model.site_pos[:] = site_pos
        carried = np.where(self.carrying >= 0, factors[np.maximum(self.carrying, 0)], 1.0)
        self.model.site_pos[self.place_sites] = site_pos[self.place_sites] * carried[:, None]
        self.model.site_pos[self.mark_sites] += marks

    def limited_model(self):
        """A copy of the model whose followers' own ranges are off: a coupled follower's range is narrower than its
        polynomial over its leader's in 35 of MyoFullBody's 51 couplings (the published model's), so held, it would
        stop its leader short (recipe of 2026-10-28: 50 degrees off a reachable pose); OpenSim's assembler bounds
        the clamped coordinates only, as the run did before."""
        return followers_free(self.model, self.followers)

    def coupled(self, qpos):
        """`qpos` with every coupled joint set from its leader by the model's polynomial (a lock to its constant)."""
        model, qpos = self.model, qpos.copy()
        for equality in range(model.neq):
            if model.eq_type[equality] != mujoco.mjtEq.mjEQ_JOINT:
                continue
            follower, leader = model.eq_obj1id[equality], model.eq_obj2id[equality]
            moved = qpos[model.jnt_qposadr[leader]] - model.qpos0[model.jnt_qposadr[leader]] if leader >= 0 else 0.0
            qpos[model.jnt_qposadr[follower]] = model.qpos0[model.jnt_qposadr[follower]] + sum(
                model.eq_data[equality, power] * moved ** power for power in range(5))
        return qpos

    def standing(self):
        """The model's default pose with its couplings applied (MyoSuite's `stand`; qpos)."""
        return self.coupled(self.model.qpos0)
