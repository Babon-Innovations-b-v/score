"""The model the fit solves on (`Fitting`): MuJoCo's own compile of the person's file (it keeps the model's joint
couplings, which mink holds exactly; Newton's model is given the found angles by joint name), with a site on each bone
group's frame body turned by the calibration table (its frame is the SOMA segment's when the group lies as SOMA's
does), a site on each marker's body where the landmark sits, and the person's constants laid on it in place
(`Fitting.apply`): each marker moved on its body and each joint inside a bone group moved in its parent (#70: the vertebrae, shoulder blade, wrist bones and inner foot joints
placed by the landmarks). Only `body_pos` and `site_pos` change: the fit is kinematics, so nothing else is compiled
again."""
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


def end_site(model, parts):
    """A group end's marker site (body name, body-local point): MyoFullBody's centre given as weighted body points
    (`parts`: [(body, sized local point, weight)]) put on the bodies' nearest common holder at the model's rest pose,
    one rule for every end (one body's point stays as it is; the hips' middle lands on the pelvis, where both hip
    centres are fixed; the neck's on the thorax, the neck and head rigid on it)."""
    data = mujoco.MjData(model)
    mujoco.mj_kinematics(model, data)
    bodies = [model.body(name).id for name, _, _ in parts]
    holder = next(body for body in _above(model, bodies[0]) if all(body in _above(model, other) for other in bodies))
    world = sum(weight * (data.xpos[body] + data.xmat[body].reshape(3, 3) @ local)
                for body, (_, local, weight) in zip(bodies, parts))
    return model.body(holder).name, data.xmat[holder].reshape(3, 3).T @ (world - data.xpos[holder])


def _above(model, body):
    """A body and every body above it, nearest first ([body id])."""
    chain = [body]
    while chain[-1]:
        chain.append(int(model.body_parentid[chain[-1]]))
    return chain


class Fitting:
    """The fitting model and what the constants move. `path` the person's file; `frames` [(group, frame body, R_cal)]:
    one orientation site each, in that order; `marks` [(name, body, local point)]: one marker site each (the place
    sites, `place_sites`); `frozen` the bodies whose joints no target sees (held as they stand); `trusts` each
    marker's trust (its weight among the markers; every one 1 when not given); `stretches` each bone group's bodies
    (source names, filed): a body whose parent is another body of its group sits on a joint inside that group
    (`inside`), solved where a marker rides it or a body below it; the found moves are written in the person's file
    (`myo.person_file`). The lengths are SOMA's, from the sizing: nothing here scales a body."""

    def __init__(self, path, frames, marks, frozen=(), trusts=None, stretches=()):
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
        self.inside = self._inside(stretches)
        self.inside_names = [own_name(model.body(body).name) for body in self.inside]  # the file's names
        self.riding = [[mark for mark, site in enumerate(self.place_sites)
                        if self._under_body(model.site_bodyid[site], body)] for body in self.inside]
        self.base = model.body_pos.copy(), model.site_pos.copy()
        self.leaders, self.followers = self._leading()
        self.frozen = [dof for dof in range(model.nv) if self._under(model.dof_bodyid[dof], frozen)]

    def _leading(self):
        """The joints no coupling sets (the free root among them) and the followers."""
        model = self.model
        followers = {int(model.eq_obj1id[equality]) for equality in range(model.neq)
                     if model.eq_type[equality] == mujoco.mjtEq.mjEQ_JOINT}
        return [joint for joint in range(model.njnt) if joint not in followers], sorted(followers)

    def _inside(self, stretches):
        """The bodies on a joint inside a bone group (by id; a split body's outermost wrapper): its parent another
        body of the same group's `stretches`, a marker riding it or a body below it."""
        model, found = self.model, []
        carried = {model.site_bodyid[site] for site in self.place_sites}
        for body in range(1, model.nbody):
            own, parent = own_name(model.body(body).name), own_name(model.body(model.body_parentid[body]).name)
            inner = own != parent and any(own in bodies and parent in bodies for bodies in stretches)
            if inner and any(self._under_body(rider, body) for rider in carried):
                found.append(body)
        return found

    def _under_body(self, body, top):
        """Whether `body` is `top` or below it (by id)."""
        while body > 0:
            if body == top:
                return True
            body = self.model.body_parentid[body]
        return False

    def _under(self, body, tops):
        """Whether a body is one of `tops` or below one."""
        model = self.model
        while body > 0:
            if own_name(model.body(body).name) in tops:
                return True
            body = model.body_parentid[body]
        return False

    def width(self):
        """How many constants: three per marker, three per inside joint."""
        return 3 * len(self.marks) + 3 * len(self.inside)

    def unpack(self, constants):
        """(marker moves markers x 3, inside joints' moves joints x 3) of a constants vector."""
        marked = 3 * len(self.marks)
        return np.reshape(constants[:marked], (-1, 3)), np.reshape(constants[marked:], (-1, 3))

    def neutral(self):
        """The constants that leave the person's file as it is: no marker or joint moved."""
        return np.zeros(self.width())

    def apply(self, constants):
        """The constants laid on the model in place, from its base: an inside joint's place in its parent by its own
        move, a marker site by its own move."""
        marks, joints = self.unpack(constants)
        body_pos, site_pos = self.base
        self.model.body_pos[:] = body_pos
        self.model.body_pos[self.inside] += joints
        self.model.site_pos[:] = site_pos
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
