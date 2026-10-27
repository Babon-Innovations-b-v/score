"""Runs in the physics trial's own Python (score/stages/physics/inside/newton_env.sh: Newton 1.7.0, on this PC's card
or a rented one; never the score venv's): a granular pile made by Newton's implicit MPM, drawn for the effects layer
as a surface built from every one of its grains.

    <env>/bin/python newton_pile.py <pile.json> <out.npz>

The pile's cuttings are the bore's (`bore` radius, `volume` cubic metres loosened: the scene's own, read off its
locked concept by the effects stage's one model call, score/stages/effects/asked.py), brought up the auger and let out
over `pour` seconds, `slices` a second, just over the resting pile's top above the collar and falling fast enough
to clear the slice before it (the rest wait inactive, where the solver does not see them). They fall and spread under
`gravity` (metres a second squared, the body's) as a Drucker-Prager granular material of `angle` (its friction angle,
degrees) and `density` (kg a cubic metre) on a ground of the same friction, for `seconds`, on a grid of `voxel`
metres (its particles jittered, seeded by `seed`), sampled `samples` times a second (a whole share of `slices`). At
each sample every grain let out is drawn into one closed surface by Newton's own particle surface (a density field
of the grains on a grid as fine as their spacing, marched into triangles, newton.geometry.extract_particle_surface,
with the reconstruction its implicit MPM example draws its water by), never a share of them.

Writes, y up, metres, the collar at the origin: `vertices` (every sample's, one after another) and `vertex_starts`
(samples + 1), `indices` (three a triangle, each sample's counted from its own first vertex) and `index_starts`
(samples + 1), and `grains` (how many grains the pile holds); a sample with nothing let out has no triangles.
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
# The surface (Newton's implicit MPM water example's reconstruction, examples/mpm/example_mpm_water_dam_break.py): each
# grain's kernel reaches this many spacings, scaled by KERNEL_SCALE, stretched along its neighbours (anisotropic), the
# field blurred FIELD_SMOOTH passes of FIELD_RADIUS cells and cut at THRESHOLD, the mesh smoothed MESH_SMOOTH passes.
KERNEL_SPACINGS = 3.0
KERNEL_SCALE = 0.6
THRESHOLD = 0.25
FIELD_SMOOTH = 1
FIELD_RADIUS = 2
MESH_SMOOTH = 1


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


def surface(state, model, spacing):
    """One closed surface over every grain let out (y up, metres): its vertices and its triangles' corners, each on a
    grid as fine as the grains' spacing."""
    mesh = newton.geometry.extract_particle_surface(
        state.particle_q, model.particle_radius, spacing, kernel_radius=KERNEL_SPACINGS * spacing,
        kernel_scale=KERNEL_SCALE, threshold=THRESHOLD, field_smooth_iterations=FIELD_SMOOTH,
        field_smooth_radius=FIELD_RADIUS, mesh_smooth_iterations=MESH_SMOOTH, anisotropic=True,
        compute_normals=False, particle_flags=model.particle_flags)
    vertices, indices, _ = mesh.to_arrays()
    if vertices is None:
        return np.zeros((0, 3), np.float32), np.zeros(0, np.int32)
    up = vertices.numpy()[:, [0, 2, 1]] * np.array([1.0, 1.0, -1.0])  # z up to y up: a turn, so faces keep their way
    return up.astype(np.float32), indices.numpy().astype(np.int32)


def simulated(pile):
    """The pile's surface at every sample (its vertices and triangles' corners, y up) and how many grains it holds."""
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
    taken = [surface(state, model, spacing)]
    for tick in range(int(round(float(pile["seconds"]) * rate))):
        if tick < slices:
            let_out(model, solver, state, spots, out, slice(bounds[tick], bounds[tick + 1]), pile, spacing)
        for _ in range(substeps):
            solver.step(state, spare, None, None, step)
            solver.project_outside(spare, spare, step)
            state, spare = spare, state
        if (tick + 1) % every == 0:
            taken.append(surface(state, model, spacing))
    return taken, len(spots)


def packed(taken):
    """The samples' surfaces one after another: vertices, their starts, triangles' corners, their starts."""
    vertex_starts = np.cumsum([0] + [len(vertices) for vertices, _ in taken])
    index_starts = np.cumsum([0] + [len(indices) for _, indices in taken])
    return (np.concatenate([vertices for vertices, _ in taken]), vertex_starts,
            np.concatenate([indices for _, indices in taken]), index_starts)


def main(pile_path, out):
    pile = json.loads(pathlib.Path(pile_path).read_text())
    taken, grains = simulated(pile)
    vertices, vertex_starts, indices, index_starts = packed(taken)
    np.savez_compressed(out, vertices=vertices, vertex_starts=vertex_starts, indices=indices,
                        index_starts=index_starts, grains=grains)
    print(f"newton {newton.__version__}: the pile's {grains} grains drawn as one surface, {len(taken)} samples, "
          f"{len(indices[index_starts[-2]:]) // 3} triangles at the last")


if __name__ == "__main__":
    main(*sys.argv[1:3])
