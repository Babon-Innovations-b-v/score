"""fit/_card: on 12 rows (frames) of a small chain (20 hinge dofs, two frozen, two followers on one leader and one
without a leader, bounds with some rows sitting on them), seeded alike, one step at a time: the card's damped
reduced step equals the CPU prototype's (card/proto/lm.py: mink's damping 1e-3 |r|^2 + 1e-9, frozen out, followers
through their coupling's slope, one active-set pass holding dofs at a bound that push out) to 1e-5 rad, and the
card's projection equals the prototype's (ranges, couplings by polyval, frozen) with every follower on polyval of its
leader to 1e-6 rad and every coordinate inside its range. Rows whose dofs are held must exist (else the hold is not
tested). Runs in Newton's own Python on a CUDA card; with no Newton env or no card it prints `skipped`.

Breaks (each applied once, seen red, reverted):
- (2026-10-29) _step's `LM_DAMPING * squared + DAMPING` made `DAMPING`: mink's damping is lost, the step differs.
- (2026-10-29) _reduced_jacobian's `* slopes[row, coupling]` dropped: followers ride their leader at slope 1.
- (2026-10-29) damped_step's second `_solved(..., keep, ...)` made `first`: a dof at its bound is not held.
- (2026-10-29) _projected's `power *= lead` made `power *= 1.0`: a coupling is no longer polyval of its leader.

Run: .venv/bin/python score/stages/sim_body/inside/fit/_card/test_the_card_step_and_projection_equal_the_cpu_prototype.py
"""
import os
import pathlib
import subprocess
import sys

INSIDE = pathlib.Path(__file__).resolve().parents[2]
IN_ENV = "SIM_BODY_INSIDE_TEST"
ROWS, RESIDUALS, DOFS = 12, 30, 20
FROZEN = (3, 7)
COUPLINGS = ((5, 2, (0.01, 0.6, -0.2, 0.05, 0.01)), (9, 2, (0.0, -0.4, 0.1, 0.0, 0.02)),
             (11, -1, (0.05, 0.0, 0.0, 0.0, 0.0)))  # follower, leader (-1: none), polyval coefficients
BOUND = 0.25  # float32-exact; dofs 0, 1, 4 and 6 range over +-BOUND
BOUNDED = (0, 1, 4, 6)


def fixture():
    """The rows' Jacobians, residuals, poses (some on their bounds), rest pose and seeds, float32-exact."""
    import numpy as np
    generator = np.random.default_rng(7)
    jacobian = generator.normal(size=(ROWS, RESIDUALS, DOFS)).astype(np.float32).astype(float)
    residuals = generator.normal(scale=1.0, size=(ROWS, RESIDUALS)).astype(np.float32).astype(float)
    qpos = generator.uniform(-0.2, 0.2, size=(ROWS, DOFS))
    qpos[::2, BOUNDED] = BOUND
    qpos[1::2, BOUNDED] = -BOUND
    rest = generator.uniform(-0.05, 0.05, size=DOFS).astype(np.float32).astype(float)
    seeds = generator.uniform(-0.2, 0.2, size=(ROWS, DOFS)).astype(np.float32).astype(float)
    lower = np.full(DOFS, -1e30)
    upper = np.full(DOFS, 1e30)
    lower[list(BOUNDED)], upper[list(BOUNDED)] = -BOUND, BOUND
    return jacobian, residuals, qpos.astype(np.float32).astype(float), rest, seeds, lower, upper


def prototype_step(jacobian, residuals, qpos, rest, lower, upper):
    """card/proto/lm.py's step in float64 (hinge-only: coordinate = dof), with its held count."""
    import numpy as np
    jac = jacobian.copy()
    for follower, leader, poly in COUPLINGS:
        if leader >= 0:
            lead = qpos[:, leader] - rest[leader]
            slope = sum(power * poly[power] * lead ** (power - 1) for power in range(1, 5))
            jac[:, :, leader] += jac[:, :, follower] * slope[:, None]
    free = [dof for dof in range(DOFS) if dof not in FROZEN and dof not in {c[0] for c in COUPLINGS}]
    sub = jac[:, :, free]
    grad = np.einsum("frd,fr->fd", sub, residuals)
    hess = np.einsum("frd,fre->fde", sub, sub)
    hess[:, range(len(free)), range(len(free))] += (1e-3 * (residuals ** 2).sum(1) + 1e-9)[:, None]
    step = -np.linalg.solve(hess, grad[..., None])[..., 0]
    at = qpos[:, free]
    held = ((at <= lower[free] + 1e-9) & (step < 0)) | ((at >= upper[free] - 1e-9) & (step > 0))
    keep = ~held
    hess_kept = hess * (keep[:, :, None] & keep[:, None, :]) + np.eye(len(free))[None] * held[:, :, None]
    step = -np.linalg.solve(hess_kept, (grad * keep)[..., None])[..., 0] * keep
    full = np.zeros((ROWS, DOFS))
    full[:, free] = step
    return full, np.linalg.norm(step, axis=1), int(held.any(1).sum()), free


def prototype_projected(qpos, rest, seeds, lower, upper):
    """card/proto/gpu.py's `projected`: ranges, couplings by polyval, frozen from the seeds."""
    import numpy as np
    found = np.clip(qpos, lower, upper)
    for follower, leader, poly in COUPLINGS:
        lead = found[:, leader] - rest[leader] if leader >= 0 else 0.0
        found[:, follower] = rest[follower] + sum(poly[power] * lead ** power for power in range(5))
    found[:, list(FROZEN)] = seeds[:, list(FROZEN)]
    return found


def the_step_equals_the_prototype():
    import numpy as np
    import warp as wp
    from fit._card import Reduction, damped_step
    jacobian, residuals, qpos, rest, _, lower, upper = fixture()
    wanted, wanted_norms, held_rows, free = prototype_step(jacobian, residuals, qpos, rest, lower, upper)
    coupled = COUPLINGS
    reduction = Reduction(free, free, lower[free], upper[free], [c[0] for c in coupled], [c[1] for c in coupled],
                          [c[1] for c in coupled], [rest[c[1]] if c[1] >= 0 else 0.0 for c in coupled],
                          np.array([c[2] for c in coupled]), "cuda:0")
    card = lambda values: wp.array(values.astype(np.float32), dtype=wp.float32, device="cuda:0")
    active = wp.array(np.ones(ROWS, np.int32), dtype=wp.int32, device="cuda:0")
    full, norms = damped_step(reduction, card(jacobian), card(residuals), card(qpos), active)
    problems = []
    if held_rows == 0:
        problems.append("no row holds a dof at its bound: the fixture does not test the hold")
    miss = np.abs(full.numpy() - wanted).max()
    if miss > 1e-5:
        problems.append(f"step differs from the prototype's by {miss:.2e} rad (most 1e-5)")
    if np.abs(norms.numpy() - wanted_norms).max() > 1e-5:
        problems.append("step lengths differ from the prototype's")
    return problems


def the_projection_equals_the_prototype():
    import numpy as np
    import warp as wp
    from fit._card import Projection, project
    _, _, qpos, rest, seeds, lower, upper = fixture()
    stepped = qpos + np.random.default_rng(8).normal(scale=0.3, size=qpos.shape)
    stepped = stepped.astype(np.float32).astype(float)
    wanted = prototype_projected(stepped, rest, seeds, lower, upper)
    projection = Projection(lower, upper, [c[0] for c in COUPLINGS], [c[1] for c in COUPLINGS],
                            [rest[c[0]] for c in COUPLINGS], [rest[c[1]] if c[1] >= 0 else 0.0 for c in COUPLINGS],
                            np.array([c[2] for c in COUPLINGS]), list(FROZEN), "cuda:0")
    card = wp.array(stepped.astype(np.float32), dtype=wp.float32, device="cuda:0")
    project(projection, card, wp.array(seeds.astype(np.float32), dtype=wp.float32, device="cuda:0"))
    found = card.numpy().astype(float)
    problems = []
    if np.abs(found - wanted).max() > 1e-6:
        problems.append(f"projection differs from the prototype's by {np.abs(found - wanted).max():.2e} rad")
    for follower, leader, poly in COUPLINGS:
        lead = found[:, leader] - rest[leader] if leader >= 0 else 0.0
        miss = np.abs(found[:, follower] - rest[follower] - sum(poly[p] * lead ** p for p in range(5))).max()
        if miss > 1e-6:
            problems.append(f"follower {follower} off polyval of its leader by {miss:.2e} rad")
    leaders = [dof for dof in BOUNDED if dof not in {c[0] for c in COUPLINGS}]
    if (found[:, leaders] < lower[leaders]).any() or (found[:, leaders] > upper[leaders]).any():
        problems.append("a coordinate left its range")
    if not np.array_equal(found[:, list(FROZEN)], seeds[:, list(FROZEN)].astype(np.float32)):
        problems.append("a frozen coordinate moved off its seed")
    return problems


CHECKS = (the_step_equals_the_prototype, the_projection_equals_the_prototype)


def in_newton():
    """The checks, in Newton's own Python, on the card."""
    import warp as wp
    if not wp.is_cuda_available():
        print("skipped: no CUDA card")
        return 0
    sys.path.insert(0, str(INSIDE))
    failures = [f"{check.__name__}: {problem}" for check in CHECKS for problem in check()]
    for failure in failures:
        print(failure)
    print("ok" if not failures else f"{len(failures)} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    if os.environ.get(IN_ENV):
        sys.exit(in_newton())
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[6] / "conftest.py"))["refuse_outside_sandbox"]()
    env = pathlib.Path(os.environ["PROPS_HOME"]) / "envs/newton_env"
    if not list(env.glob(".built-*")):
        print(f"skipped: no Newton env built at {env} (score/stages/physics/inside/newton_env.sh)")
        sys.exit(0)
    sys.exit(subprocess.run([str(env / "bin/python"), "-B", __file__], env={**os.environ, IN_ENV: "1"}).returncode)
