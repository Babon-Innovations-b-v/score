"""Level 2's frames' kinematics on the card (plan step 4): every sampled frame of a body one MuJoCo Warp world, its
kinematics and centre-of-mass frames (`mujoco_warp.kinematics`, `com_pos`), then one launch giving every place and
turn site's Jacobian on every frame (MuJoCo Warp's own `jac_dof`, a thread a world, site and dof); the constants laid
on the card's model's `body_pos` and `site_pos` as `Fitting.apply` lays them. `frames` hands `_level2.frame_rows`
per frame what `_level2.Kinematics` gives on the host, in float32, held to it in the test."""
import mujoco_warp as mjw
import numpy as np
import warp as wp
from mujoco_warp._src.support import jac_dof


@wp.kernel(enable_backward=False)
def _site_jacobians(body_parentid: wp.array[int], body_rootid: wp.array[int], dof_bodyid: wp.array[int],
                    body_isdofancestor: wp.array2d[int], subtree_com: wp.array2d[wp.vec3],
                    cdof: wp.array2d[wp.spatial_vector], site_xpos: wp.array2d[wp.vec3], site_bodyid: wp.array[int],
                    sites: wp.array[int], places: wp.array4d[float], spins: wp.array4d[float]):
    world, index, dof = wp.tid()
    site = sites[index]
    place, spin = jac_dof(body_parentid, body_rootid, dof_bodyid, body_isdofancestor, subtree_com, cdof,
                          site_xpos[world, site], site_bodyid[site], dof, world)
    for axis in range(3):
        places[world, index, axis, dof] = place[axis]
        spins[world, index, axis, dof] = spin[axis]


class Frame:
    """One frame's kinematics as `_level2.Kinematics` holds them (numpy)."""

    def __init__(self, site_turns, body_turns, places, spins):
        self.site_turns, self.body_turns, self.places, self.spins = site_turns, body_turns, places, spins


class CardKinematics:
    """A body's fitting model on the card, `count` worlds (its sampled frames)."""

    def __init__(self, fitting, count):
        self.fitting, self.count = fitting, count
        self.model = mjw.put_model(fitting.model)
        self.data = mjw.make_data(fitting.model, nworld=count)
        self.sites = list(fitting.place_sites) + list(fitting.frame_sites)
        self.site_ids = wp.array(np.array(self.sites, dtype=np.int32), dtype=int)
        shape = (count, len(self.sites), 3, fitting.model.nv)
        self.places, self.spins = wp.zeros(shape, dtype=float), wp.zeros(shape, dtype=float)

    def frames(self, qpos):
        """Each frame's kinematics at `qpos` (frames x nq) on the constants the fitting model holds now."""
        model, data, host = self.model, self.data, self.fitting.model
        model.body_pos.assign(host.body_pos[None].astype(np.float32))
        model.site_pos.assign(host.site_pos[None].astype(np.float32))
        data.qpos.assign(np.asarray(qpos, dtype=np.float32))
        mjw.kinematics(model, data)
        mjw.com_pos(model, data)
        wp.launch(_site_jacobians, dim=(self.count, len(self.sites), host.nv),
                  inputs=[model.body_parentid, model.body_rootid, model.dof_bodyid, model.body_isdofancestor,
                          data.subtree_com, data.cdof, data.site_xpos, model.site_bodyid, self.site_ids],
                  outputs=[self.places, self.spins])
        places, spins = self.places.numpy().astype(float), self.spins.numpy().astype(float)
        marks = len(self.fitting.place_sites)
        site_turns = data.site_xmat.numpy().astype(float)[:, self.fitting.frame_sites]
        body_turns = data.xmat.numpy().astype(float)
        return [Frame(site_turns[frame], body_turns[frame], places[frame, :marks], spins[frame, marks:])
                for frame in range(self.count)]
