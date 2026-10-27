"""Runs in the physics trial's own Python (score/stages/physics/inside/newton_env.sh: Newton 1.7.0, on this PC's card
or a rented one; never the score venv's): a granular pile made by Newton's implicit MPM, its particles sampled for the
effects layer.

    <env>/bin/python newton_pile.py <pile.json> <out.npz>

The pile's cuttings are the bore's (`bore` radius, `volume` cubic metres loosened), brought up the auger and let out
over `pour` seconds, `slices` a second, just over the resting pile's top above the collar and falling fast enough
to clear the slice before it (the rest wait inactive, where the solver does not see them). They fall and spread under
`gravity` (metres a second squared, the body's) as a Drucker-Prager granular material of `angle` (its friction angle,
degrees) and `density` (kg a cubic metre) on a ground of the same friction, for `seconds`, on a grid of `voxel`
metres, sampled `samples` times a second (a whole share of `slices`). Of its particles `count` are drawn (seeded by `seed`), each as wide as the
share of the pile it stands for.

Writes `points` (samples x count x 3, metres, y up, the collar at the origin) and `widths` (samples x count, metres;
0 for one not let out yet, written at the collar).
"""
import json
import math
import pathlib
import sys

import numpy as np
import warp as wp

import newton
from newton.solvers import SolverImplicitMPM

# Particles a grid cell along each axis, and the longest step the solver takes, seconds.
PER_CELL = 2
STEP_MOST = 1.0 / 96.0
# A particle slower than this rests on the pile (metres a second), and a slice is let out this far over its top.
RESTING = 0.1
DROP = 0.1


def cone_friction(angle):
    """Newton's Drucker-Prager friction for a friction angle (degrees): its yield cone (deviatoric stress norm under
    friction times sqrt(3/2) times the pressure, rheology_solver_kernels.YieldParamVec) through Mohr-Coulomb's in
    triaxial compression, M = 6 sin / (3 - sin) = 1.5 friction."""
    sine = math.sin(math.radians(angle))
    return 4.0 * sine / (3.0 - sine)


def column(pile):
    """The bore's cuttings as a standing column of particle spots on the collar (z up), jittered within their cells,
    lowest first, and the spacing between them."""
    voxel, radius = float(pile["voxel"]), float(pile["bore"])
    tall = float(pile["volume"]) / (math.pi * radius * radius)
    spacing = voxel / PER_CELL
    across = np.arange(-radius + spacing / 2, radius, spacing)
    grid_x, grid_y, grid_z = np.meshgrid(across, across, np.arange(spacing / 2, tall, spacing), indexing="ij")
    spots = np.stack([grid_x.ravel(), grid_y.ravel(), grid_z.ravel()], axis=1)
    spots = spots[np.hypot(spots[:, 0], spots[:, 1]) <= radius]
    spots += np.random.default_rng(int(pile["seed"])).uniform(-0.25, 0.25, spots.shape) * spacing
    return spots[np.argsort(spots[:, 2], kind="stable")], spacing


def top_over_collar(spots, speeds, out, bore):
    """How high the let-out particles resting on the pile stand over the collar (within the bore's radius of its
    axis), metres."""
    resting = out & (np.linalg.norm(speeds, axis=1) < RESTING)
    near = spots[resting & (np.hypot(spots[:, 0], spots[:, 1]) <= bore)]
    return float(near[:, 2].max()) if len(near) else 0.0


def built(pile, spots, spacing):
    """The model (every particle inactive, on a ground of the material's friction) and its MPM solver."""
    builder = newton.ModelBuilder()
    SolverImplicitMPM.register_custom_attributes(builder)
    for spot in spots:
        builder.add_particle(wp.vec3(*spot), wp.vec3(0.0), spacing ** 3 * float(pile["density"]), spacing / 2,
                             flags=0)
    builder.add_ground_plane(cfg=newton.ModelBuilder.ShapeConfig(mu=math.tan(math.radians(float(pile["angle"])))))
    model = builder.finalize()
    model.set_gravity((0.0, 0.0, -float(pile["gravity"])))
    model.mpm.friction.fill_(cone_friction(float(pile["angle"])))
    config = SolverImplicitMPM.Config()
    config.voxel_size = float(pile["voxel"])
    return model, SolverImplicitMPM(model, config=config)


def let_out(model, solver, state, spots, out, which, pile, spacing):  # noqa: PLR0913
    """One slice of the column made active just over the resting pile's top above the collar, falling as fast as
    clears its own thickness before the next."""
    now, speeds = state.particle_q.numpy(), state.particle_qd.numpy()
    thick = spots[which, 2].max() - spots[which, 2].min() + spacing
    lift = top_over_collar(now, speeds, out, float(pile["bore"])) + DROP - spots[which, 2].min()
    now[which] = spots[which] + np.array([0.0, 0.0, lift])
    speeds[which] = np.array([0.0, 0.0, -thick * float(pile["slices"])])
    state.particle_q.assign(now)
    state.particle_qd.assign(speeds)
    out[which] = True
    flags = model.particle_flags.numpy()
    flags[out] = int(newton.ParticleFlags.ACTIVE)
    model.particle_flags.assign(flags)
    solver.notify_model_changed(newton.ModelFlags.MODEL_PROPERTIES)


def simulated(pile):
    """The pile's particles at every sample (samples x count x 3, z up), whether each is let out by then (samples x
    count) and their radius."""
    spots, spacing = column(pile)
    model, solver = built(pile, spots, spacing)
    state, spare = model.state(), model.state()
    rate = float(pile["slices"])
    substeps = math.ceil(1.0 / rate / STEP_MOST)
    step = 1.0 / rate / substeps
    every = int(round(rate / float(pile["samples"])))
    slices = int(round(float(pile["pour"]) * rate))
    bounds = np.linspace(0, len(spots), slices + 1).astype(int)
    out = np.zeros(len(spots), dtype=bool)
    taken, shown = [state.particle_q.numpy().copy()], [out.copy()]
    for tick in range(int(round(float(pile["seconds"]) * rate))):
        if tick < slices:
            let_out(model, solver, state, spots, out, slice(bounds[tick], bounds[tick + 1]), pile, spacing)
        for _ in range(substeps):
            solver.step(state, spare, None, None, step)
            solver.project_outside(spare, spare, step)
            state, spare = spare, state
        if (tick + 1) % every == 0:
            taken.append(state.particle_q.numpy().copy())
            shown.append(out.copy())
    return np.stack(taken), np.stack(shown), spacing / 2


def drawn(pile, points, shown, radius):
    """The `count` drawn particles in the effects layer's frame (y up): spots and widths, each as wide as the share
    of the pile's particles it stands for, 0 before it is let out (at the collar)."""
    which = np.sort(np.random.default_rng(int(pile["seed"])).choice(points.shape[1], int(pile["count"]),
                                                                     replace=False))
    width = 2 * radius * (points.shape[1] / len(which)) ** (1 / 3)
    points, shown = points[:, which], shown[:, which]
    up = np.where(shown[..., None], points, 0.0)[..., [0, 2, 1]] * np.array([1.0, 1.0, -1.0])  # z up to y up
    return up.astype(np.float32), np.where(shown, width, 0.0).astype(np.float32)


def main(pile_path, out):
    pile = json.loads(pathlib.Path(pile_path).read_text())
    points, shown, radius = simulated(pile)
    spots, widths = drawn(pile, points, shown, radius)
    np.savez_compressed(out, points=spots, widths=widths)
    print(f"newton {newton.__version__}: {spots.shape[1]} of the pile's {points.shape[1]} particles drawn, "
          f"{spots.shape[0]} samples")


if __name__ == "__main__":
    main(*sys.argv[1:3])
