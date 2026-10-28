"""The physics of one person's movement, frame by frame, on the MuJoCo model Newton builds (nothing stepped):
`Physics.needed` the generalised forces the movement needs (inverse dynamics, armature and passive forces in),
`Physics.stops` the joints at an end of their range, and `Physics.shared` the static optimisation, one bounded least
squares that gives the forces to the ground's pushes (`contact.pushes`), the joints' stops and the muscles' activations
(least squared activation first, the pelvis' six balance rows BALANCE times dearer than a joint's); what they cannot
give is the pelvis' residual and each joint's reserve, measured and never applied."""
import mujoco
import numpy as np

from contact import pushes
from ground import normals
from model import Couplings
from solvers import least

CONTACT_COST = 1e-3  # the solve's weight of a newton of contact force (or N m of a joint's stop) against an activation
# The solve's weight of the pelvis' residual (a newton or N m) against a joint's reserve (N m): the ground must balance
# the whole body first, so a movement it cannot carry shows as residual, and one the muscles cannot make as reserves.
BALANCE = 100.0
AT_STOP = 1e-4  # radians or metres: a joint this near an end of its range stands against it


class Physics:
    """One person's MuJoCo model as Newton built it, and the frame by frame share of its movement's forces."""

    def __init__(self, model, ground, colliders):
        self.model, self.data = model, mujoco.MjData(model)
        self.couplings = Couplings(model)
        self.ground, self.up = ground, normals(ground)
        self.colliders = colliders
        self.muscles = np.flatnonzero(model.actuator_dyntype == mujoco.mjtDyn.mjDYN_MUSCLE)

    def needed(self, qpos, qvel, qacc):
        """The state set, and the generalised forces the movement needs beyond the passive ones (nv)."""
        model, data = self.model, self.data
        data.qpos[:], data.qvel[:], data.qacc[:] = qpos, qvel, qacc
        mujoco.mj_fwdPosition(model, data)
        mujoco.mj_fwdVelocity(model, data)
        found = np.zeros(model.nv)
        mujoco.mj_rne(model, data, 1, found)
        return found + model.dof_armature * qacc - data.qfrc_passive

    def contacts(self):
        """The points the ground pushes now (`contact.pushes` on this person's colliders and ground)."""
        return pushes(self.model, self.data, self.ground, self.up, self.colliders)

    def stops(self):
        """Each leading hinge or slide at an end of its range now, as a one-sided generalised force pushing it back
        in (nv x stops): MuJoCo's joint limit, the passive structures that hold a straight knee, say."""
        model, data = self.model, self.data
        found = []
        for dof in self.couplings.leads:
            joint = model.dof_jntid[dof]
            if not model.jnt_limited[joint] or model.jnt_type[joint] not in (mujoco.mjtJoint.mjJNT_HINGE,
                                                                              mujoco.mjtJoint.mjJNT_SLIDE):
                continue
            at, (low, high) = data.qpos[model.jnt_qposadr[joint]], model.jnt_range[joint]
            for sign, end in ((1.0, at <= low + AT_STOP), (-1.0, at >= high - AT_STOP)):
                if end:
                    column = np.zeros(model.nv)
                    column[dof] = sign
                    found.append(column)
        return np.array(found).T if found else np.zeros((model.nv, 0))

    def shared(self, needed):
        """The needed forces shared out: each contact's push (N, MuJoCo's frame, by body), each muscle's activation
        and force (N, tension), the residual on the pelvis (force N and moment N m, MuJoCo's frame) and each leading
        joint's reserve and net moment (N m)."""
        model, data = self.model, self.data
        mapped = self.couplings.map(data.qpos)
        moments = np.zeros((model.nu, model.nv))
        mujoco.mju_sparse2dense(moments, data.actuator_moment, data.moment_rownnz, data.moment_rowadr,
                                data.moment_colind)
        gains, biases = [], []
        for actuator in self.muscles:
            gains.append(mujoco.mju_muscleGain(data.actuator_length[actuator], data.actuator_velocity[actuator],
                                               model.actuator_lengthrange[actuator], model.actuator_acc0[actuator],
                                               model.actuator_gainprm[actuator, :9]))
            biases.append(mujoco.mju_muscleBias(data.actuator_length[actuator], model.actuator_lengthrange[actuator],
                                                model.actuator_acc0[actuator], model.actuator_biasprm[actuator, :9]))
        gains, biases = np.array(gains), np.array(biases)
        arms = moments[self.muscles].T  # nv x muscles
        contacts = self.contacts()
        columns = []
        for _, along, edges in contacts:
            columns += [along.T @ edge for edge in edges]
        pushes = np.array(columns).T if columns else np.zeros((model.nv, 0))
        stops = self.stops()
        wanted = mapped.T @ (needed - arms @ biases)
        system = mapped.T @ np.concatenate([pushes, stops, arms * gains], axis=1)
        count, held = pushes.shape[1], stops.shape[1]
        costs = np.concatenate([np.full(count + held, CONTACT_COST), np.ones(len(self.muscles))])
        rows = np.ones(len(wanted))
        rows[:6] = BALANCE  # the pelvis' six rows: the whole body's balance, kept before any joint's
        solved = least(system * rows[:, None], wanted * rows, costs, np.concatenate([np.full(count + held, np.inf),
                                                                                    np.ones(len(self.muscles))]))
        pushed, activations = solved[:count], solved[count + held:]
        left = wanted - system @ solved
        forces = np.zeros((model.nbody, 3))
        edges = [(body, edge) for body, _, mine in contacts for edge in mine]
        for (body, edge), weight in zip(edges, pushed):
            forces[body] += weight * edge
        root = data.xmat[model.jnt_bodyid[0]].reshape(3, 3)
        net = mapped.T @ (needed - pushes @ pushed)
        return {"pushes": forces, "activations": activations, "forces": -(gains * activations + biases),
                "residual": np.concatenate([left[:3], root @ left[3:6]]), "reserves": left[6:], "moments": net[6:]}
