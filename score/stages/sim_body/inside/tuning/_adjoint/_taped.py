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


class TapedSites:
    """Sites on `model`'s links (`links` index, `weights`, world `targets` (sites, 3)), and optional `turns`
    (links, weights, targets, offsets: `_TurnRows`); `model` built with requires_grad, its joint_q the pose."""

    def __init__(self, model, links, weights, targets, turns=None):
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

    def _evaluate(self, inner, outer):
        """Forward kinematics at pose `inner`, then the sites' residuals and cost with offsets `outer` (flat)."""
        self.model.joint_q.assign(np.asarray(inner, dtype=np.float32))
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
        found = self.model.joint_q.grad.numpy().astype(np.float64)
        tape.zero()
        return found

    def residuals(self, inner, outer):
        """The sites' weighted residuals, then the turn rows', flat (rows x 3)."""
        self._evaluate(inner, outer)
        rows = [self.residual_rows.numpy()]
        if self.turns is not None:
            rows.append(self.turns.residual_rows.numpy())
        return np.concatenate(rows).astype(np.float64).ravel()
