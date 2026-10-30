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


class _Constants:
    """Level 2's constants for one body: each free site's move off its landmark (`free_sites`, into the sites) and each
    inside joint's move of its place in its parent (`inside_joints`, into joint_X_p), 3 values each, free sites first.
    Laid onto the offsets and joint_X_p before the tape's forward pass; their gradient read off those arrays' grads.
    A body batched per frame (every frame a copy of it in one model) gives each as rows (frames, count): every copy
    takes the same moves, and their gradients sum."""

    def __init__(self, model, free_sites, inside_joints):
        self.free_sites = np.atleast_2d(np.asarray(free_sites, dtype=int))
        self.inside_joints = np.atleast_2d(np.asarray(inside_joints, dtype=int))
        self.free_count = self.free_sites.shape[1]
        self.size = 3 * (self.free_count + self.inside_joints.shape[1])
        self.base_places = model.joint_X_p.numpy().copy()

    def lay(self, moves, offsets, joint_x_p):
        """`offsets` (sites, 3) with the free sites' moves added, and joint_X_p with the inside joints' moves."""
        moves = np.asarray(moves, dtype=np.float32).reshape(-1, 3)
        moved = offsets.copy()
        moved[self.free_sites] += moves[:self.free_count]
        places = self.base_places.copy()
        places[self.inside_joints, :3] += moves[self.free_count:]
        joint_x_p.assign(places)
        return moved

    def gradient(self, offsets, joint_x_p):
        """d cost / d moves from the tape's grads on the offsets and joint_X_p, flat in the moves' order."""
        sites = offsets.grad.numpy()[self.free_sites].sum(axis=0)
        joints = joint_x_p.grad.numpy()[self.inside_joints, :3].sum(axis=0)
        return np.concatenate([sites, joints]).astype(np.float64).ravel()


class TapedSites:
    """Sites on `model`'s links (`links` index, `weights`, world `targets` (sites, 3)), and optional `turns`
    (links, weights, targets, offsets: `_TurnRows`) and `couplings` (`_Couplings`' arguments after the device, the pose
    then the free coordinates) and `constants` (`_Constants`' arguments after the model: level 2's free sites and inside
joints, the inner unknowns after the pose); `model` built with requires_grad, its joint_q the pose when no couplings
are given. `trusted`: the outer unknowns hold each site's trust (its weight) after the offsets, level 1's landmark
weights, replacing `weights` at every evaluation. `ends` (with `trusted`): the last `ends` sites are the group ends
(their offsets the group-end centres' moves) and the outer unknowns after the offsets are the landmarks' trusts, then
"end weight", then "marker goal": each site weighs sqrt(goal * trust / sum of trusts), an end's trust "end weight"
times the landmarks' mean (`fit.fitting` and `fit/_card/_objective`'s markers' goal). `copies` (a body batched per
frame): the sites are that many copies of one frame's, copy by copy, and `outer` is one copy's (its sites' offsets, then
its trusts), laid on every copy, so each copy's last `ends` sites are its ends and its weights are its own frame's."""

    def __init__(self, model, links, weights, targets, turns=None, couplings=None, constants=None, trusted=False, ends=None,
                 copies=1):
        self.model = model
        self.copies = copies
        self.trusted = trusted
        self.ends = ends
        self.state = model.state(requires_grad=True)
        device = model.device
        self.links = wp.array(np.asarray(links, dtype=np.int32), dtype=wp.int32, device=device)
        self.weights = wp.array(np.asarray(weights, dtype=np.float32), dtype=wp.float32, device=device,
                                requires_grad=True)
        self.targets = wp.array(np.asarray(targets, dtype=np.float32), dtype=wp.vec3, device=device)
        self.offsets = wp.zeros(len(links), dtype=wp.vec3, device=device, requires_grad=True)
        self.residual_rows = wp.zeros(len(links), dtype=wp.vec3, device=device, requires_grad=True)
        self.cost = wp.zeros(1, dtype=wp.float32, device=device, requires_grad=True)
        self.turns = _TurnRows(device, *turns) if turns is not None else None
        self.couplings = _Couplings(device, *couplings) if couplings is not None else None
        self.constants = _Constants(model, *constants) if constants is not None else None

    def _split(self, inner):
        """The pose and level 2's moves from `inner` (the moves empty when no constants are given)."""
        inner = np.asarray(inner, dtype=np.float64)
        size = self.constants.size if self.constants is not None else 0
        return inner[:len(inner) - size], inner[len(inner) - size:]

    def _weighed(self, tail):
        """The sites' weights from the outer unknowns after the offsets: the trusts themselves, or with `ends` the
        markers' goal's weights from the landmarks' trusts, "end weight" and "marker goal"."""
        if self.ends is None:
            return tail
        trusts, end_weight, goal = tail[:-2], tail[-2], tail[-1]
        trusts = np.concatenate([trusts, np.full(self.ends, end_weight * trusts.mean())])
        return np.sqrt(goal * trusts / max(trusts.sum(), 1e-12)).astype(np.float32)

    def _evaluate(self, inner, outer):
        """Forward kinematics at `inner` (the pose, then level 2's moves), then the sites' residuals and cost with
        offsets `outer` (flat)."""
        pose, moves = self._split(inner)
        if self.couplings is None:
            self.model.joint_q.assign(pose.astype(np.float32))
        else:
            self.couplings.write(pose, self.model.joint_q)
        outer = np.asarray(outer, dtype=np.float32)
        sites = self.links.shape[0] // self.copies
        if self.trusted:
            self.weights.assign(np.tile(self._weighed(outer[3 * sites:]), self.copies))
            outer = outer[:3 * sites]
        offsets = np.tile(outer.reshape(-1, 3), (self.copies, 1))
        if self.constants is not None:
            offsets = self.constants.lay(moves, offsets, self.model.joint_X_p)
        self.offsets.assign(offsets)
        self.cost.zero_()
        newton.eval_fk(self.model, self.model.joint_q, self.model.joint_qd, self.state)
        wp.launch(_site_cost, dim=self.links.shape[0],
                  inputs=[self.state.body_q, self.links, self.offsets, self.targets, self.weights],
                  outputs=[self.residual_rows, self.cost], device=self.model.device)
        if self.turns is not None:
            self.turns.launch(self.state.body_q, self.cost)

    def gradient(self, inner, outer):
        """d cost / d inner at (`inner`, `outer`) by the tape's backward pass: the pose's, then level 2's moves'."""
        tape = wp.Tape()
        with tape:
            self._evaluate(inner, outer)
        tape.backward(self.cost)
        pose = self.model.joint_q if self.couplings is None else self.couplings.pose
        found = pose.grad.numpy().astype(np.float64)
        if self.constants is not None:
            found = np.concatenate([found, self.constants.gradient(self.offsets, self.model.joint_X_p)])
        tape.zero()
        return found

    def _weighed_back(self, tail, weight_grad):
        """d cost / d tail from d cost / d each site's weight (one copy's): `_weighed`'s Jacobian transposed."""
        tail = np.asarray(tail, dtype=np.float64)
        if self.ends is None:
            return weight_grad
        trusts, end_weight, goal = tail[:-2], tail[-2], tail[-1]
        count = len(trusts)
        mean = trusts.mean()
        every = np.concatenate([trusts, np.full(self.ends, end_weight * mean)])
        total = every.sum()
        shares = 0.5 * weight_grad * np.sqrt(goal * every / total)
        ends_share = shares[count:].sum()
        total_back = -shares.sum() / total
        found = shares[:count] / trusts + ends_share / (mean * count) + total_back * (1 + self.ends * end_weight / count)
        return np.concatenate([found, [ends_share / end_weight + total_back * self.ends * mean,
                                       shares.sum() / goal]])

    def outer_gradient(self, inner, outer):
        """d cost / d outer at (`inner`, `outer`) by the tape's backward pass: each site offset's grad summed over the
        copies, then (`trusted`) the weights' grads through `_weighed`."""
        tape = wp.Tape()
        with tape:
            self._evaluate(inner, outer)
        tape.backward(self.cost)
        sites = self.links.shape[0] // self.copies
        found = self.offsets.grad.numpy().astype(np.float64).reshape(self.copies, sites * 3).sum(axis=0)
        if self.trusted:
            weight_grad = self.weights.grad.numpy().astype(np.float64).reshape(self.copies, sites).sum(axis=0)
            found = np.concatenate([found, self._weighed_back(np.asarray(outer)[3 * sites:], weight_grad)])
        tape.zero()
        return found

    def residuals(self, inner, outer):
        """The sites' weighted residuals, then the turn rows', flat (rows x 3)."""
        self._evaluate(inner, outer)
        rows = [self.residual_rows.numpy()]
        if self.turns is not None:
            rows.append(self.turns.residual_rows.numpy())
        return np.concatenate(rows).astype(np.float64).ravel()


def turned_offsets(sites, moves, work):
    """`work()` with each turn row's offset in `moves` ({row: body-side rad}) turned: the site holds R_cal^T, so
    R_cal -> R_cal exp([w]x) makes it exp(-[w]x) R_cal^T; the offsets are put back after."""
    from scipy.spatial.transform import Rotation
    kept = sites.turns.offsets
    offsets = kept.numpy().astype(np.float64)
    for row, turn in moves.items():
        offsets[row] = (Rotation.from_rotvec(-np.asarray(turn)) * Rotation.from_quat(offsets[row])).as_quat()
    sites.turns.offsets = wp.array(offsets.astype(np.float32), dtype=wp.quat, device=kept.device)
    try:
        return work()
    finally:
        sites.turns.offsets = kept
