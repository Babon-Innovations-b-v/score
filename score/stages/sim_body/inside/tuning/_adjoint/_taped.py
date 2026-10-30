"""One frame's level 3 gradient on the card, exact by Warp's tape through Newton's eval_fk (#70, card plan step 6b):
the cost 0.5 sum w^2 |target - site(q, offset)|^2 over sites on links, plus level 3's link-frame turn rows
0.5 sum w^2 |log(turn(q) offset target^-1)|^2 (the card's own `_turn_error`), its gradient over the pose q (the inner
unknowns) with the site offsets as the outer ones, in the shape `Body` takes (`gradient(inner, outer)`,
`residuals(inner, outer)`). Float32 on the card, returned as float64."""
import importlib.util
import pathlib

import numpy as np
import warp as wp
import newton


def _card_objective():
    """fit/_card/_objective.py by its path: the package's own imports need more than Newton's Python holds."""
    path = pathlib.Path(__file__).resolve().parents[2] / "fit/_card/_objective.py"
    spec = importlib.util.spec_from_file_location("_card_objective", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_turn_error = _card_objective()._turn_error


@wp.kernel
def _site_cost(body_q: wp.array[wp.transform], links: wp.array[wp.int32], offsets: wp.array[wp.vec3],
               targets: wp.array[wp.vec3], weights: wp.array[wp.float32], residuals: wp.array[wp.vec3],
               cost: wp.array[wp.float32]):
    site = wp.tid()
    residual = weights[site] * (targets[site] - wp.transform_point(body_q[links[site]], offsets[site]))
    residuals[site] = residual
    wp.atomic_add(cost, 0, 0.5 * wp.dot(residual, residual))


@wp.kernel
def _turn_cost(body_q: wp.array[wp.transform], links: wp.array[wp.int32], offsets: wp.array[wp.quat],
               targets: wp.array[wp.vec4], weights: wp.array[wp.float32], residuals: wp.array[wp.vec3],
               cost: wp.array[wp.float32]):
    row = wp.tid()
    residual = weights[row] * _turn_error(body_q[links[row]], targets[row], offsets[row])
    residuals[row] = residual
    wp.atomic_add(cost, 0, 0.5 * wp.dot(residual, residual))


class _TurnRows:
    """Link-frame turn rows: `links`, `weights`, `targets` (rows, 4) x y z w, `offsets` (rows, 4) x y z w in the
    link's frame; fixed, not outer unknowns."""

    def __init__(self, device, links, weights, targets, offsets):
        self.links = wp.array(np.asarray(links, dtype=np.int32), dtype=wp.int32, device=device)
        self.weights = wp.array(np.asarray(weights, dtype=np.float32), dtype=wp.float32, device=device)
        self.targets = wp.array(np.asarray(targets, dtype=np.float32), dtype=wp.vec4, device=device)
        self.offsets = wp.array(np.asarray(offsets, dtype=np.float32), dtype=wp.quat, device=device)
        self.residual_rows = wp.zeros(len(links), dtype=wp.vec3, device=device, requires_grad=True)

    def launch(self, body_q, cost):
        """Each turn row's weighted log residual, added into `cost`."""
        wp.launch(_turn_cost, dim=self.links.shape[0],
                  inputs=[body_q, self.links, self.offsets, self.targets, self.weights],
                  outputs=[self.residual_rows, cost], device=self.links.device)


COUPLING_TERMS = 5


@wp.kernel
def _free_coordinates(pose: wp.array[wp.float32], free_coord: wp.array[wp.int32], joint_q: wp.array[wp.float32]):
    index = wp.tid()
    joint_q[free_coord[index]] = pose[index]


@wp.kernel
def _followers(pose: wp.array[wp.float32], follower_coord: wp.array[wp.int32], leader_free: wp.array[wp.int32],
               follower_rest: wp.array[wp.float32], leader_rest: wp.array[wp.float32],
               poly: wp.array2d[wp.float32], joint_q: wp.array[wp.float32]):
    coupling = wp.tid()
    lead = float(0.0)
    if leader_free[coupling] >= 0:
        lead = pose[leader_free[coupling]] - leader_rest[coupling]
    value = float(0.0)
    power = float(1.0)
    for term in range(COUPLING_TERMS):
        value += poly[coupling, term] * power
        power *= lead
    joint_q[follower_coord[coupling]] = follower_rest[coupling] + value


class _Couplings:
    """MyoFullBody's joint couplings as the projection holds them (`fit/_card/_project.py`): the pose is the free
    coordinates (`free_coord` into joint_q); each follower is its rest plus polyval of its leader's move (`leader_free`
    into the pose, -1 a lock); every other coordinate stays at `base`. Written into joint_q on the tape, each entry
    once, so the pose gradient carries the followers' share through their leaders."""

    def __init__(self, device, free_coord, follower_coord, leader_free, follower_rest, leader_rest, poly, base):
        def ints(values):
            return wp.array(np.asarray(values, dtype=np.int32), dtype=wp.int32, device=device)

        def floats(values):
            return wp.array(np.asarray(values, dtype=np.float32), dtype=wp.float32, device=device)

        self.free_coord, self.follower_coord, self.leader_free = ints(free_coord), ints(follower_coord), ints(leader_free)
        self.follower_rest, self.leader_rest = floats(follower_rest), floats(leader_rest)
        self.poly = wp.array(np.asarray(poly, dtype=np.float32).reshape(-1, COUPLING_TERMS), dtype=wp.float32,
                             device=device)
        self.base = np.asarray(base, dtype=np.float32)
        self.pose = wp.zeros(len(free_coord), dtype=wp.float32, device=device, requires_grad=True)

    def write(self, inner, joint_q):
        """joint_q from the free pose `inner`: base, then the free coordinates, then the followers."""
        joint_q.assign(self.base)
        self.pose.assign(np.asarray(inner, dtype=np.float32))
        wp.launch(_free_coordinates, dim=self.free_coord.shape[0], inputs=[self.pose, self.free_coord],
                  outputs=[joint_q], device=joint_q.device)
        wp.launch(_followers, dim=self.follower_coord.shape[0],
                  inputs=[self.pose, self.follower_coord, self.leader_free, self.follower_rest, self.leader_rest,
                          self.poly], outputs=[joint_q], device=joint_q.device)


class TapedSites:
    """Sites on `model`'s links (`links` index, `weights`, world `targets` (sites, 3)), and optional `turns`
    (links, weights, targets, offsets: `_TurnRows`) and `couplings` (`_Couplings`' arguments after the device, the pose
    then the free coordinates); `model` built with requires_grad, its joint_q the pose when no couplings are given."""

    def __init__(self, model, links, weights, targets, turns=None, couplings=None):
        self.model = model
        self.state = model.state(requires_grad=True)
        device = model.device
        self.links = wp.array(np.asarray(links, dtype=np.int32), dtype=wp.int32, device=device)
        self.weights = wp.array(np.asarray(weights, dtype=np.float32), dtype=wp.float32, device=device)
        self.targets = wp.array(np.asarray(targets, dtype=np.float32), dtype=wp.vec3, device=device)
        self.offsets = wp.zeros(len(links), dtype=wp.vec3, device=device, requires_grad=True)
        self.residual_rows = wp.zeros(len(links), dtype=wp.vec3, device=device, requires_grad=True)
        self.cost = wp.zeros(1, dtype=wp.float32, device=device, requires_grad=True)
        self.turns = _TurnRows(device, *turns) if turns is not None else None
        self.couplings = _Couplings(device, *couplings) if couplings is not None else None

    def _evaluate(self, inner, outer):
        """Forward kinematics at pose `inner`, then the sites' residuals and cost with offsets `outer` (flat)."""
        if self.couplings is None:
            self.model.joint_q.assign(np.asarray(inner, dtype=np.float32))
        else:
            self.couplings.write(inner, self.model.joint_q)
        self.offsets.assign(np.asarray(outer, dtype=np.float32).reshape(-1, 3))
        self.cost.zero_()
        newton.eval_fk(self.model, self.model.joint_q, self.model.joint_qd, self.state)
        wp.launch(_site_cost, dim=self.links.shape[0],
                  inputs=[self.state.body_q, self.links, self.offsets, self.targets, self.weights],
                  outputs=[self.residual_rows, self.cost], device=self.model.device)
        if self.turns is not None:
            self.turns.launch(self.state.body_q, self.cost)

    def gradient(self, inner, outer):
        """d cost / d pose at (`inner`, `outer`), by the tape's backward pass."""
        tape = wp.Tape()
        with tape:
            self._evaluate(inner, outer)
        tape.backward(self.cost)
        pose = self.model.joint_q if self.couplings is None else self.couplings.pose
        found = pose.grad.numpy().astype(np.float64)
        tape.zero()
        return found

    def residuals(self, inner, outer):
        """The sites' weighted residuals, then the turn rows', flat (rows x 3)."""
        self._evaluate(inner, outer)
        rows = [self.residual_rows.numpy()]
        if self.turns is not None:
            rows.append(self.turns.residual_rows.numpy())
        return np.concatenate(rows).astype(np.float64).ravel()
