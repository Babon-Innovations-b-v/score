"""Runs in Newton's own Python (score/stages/physics/inside/newton_env.sh, pinned): one flag's cloth on Newton's VBD
solver, pinned along its pole and blown by the wind the stage gives it (the motion row's flag cloth,
score/stages/motion/cloth.py).

    <env>/bin/python score/stages/motion/inside/flag_cloth.py <job.json> <out.npz>

job.json (written by score/stages/motion/cloth.py): {"rate" (frames a second), "frames", "substeps", "iterations",
"device", "gravity" ([x, y, z] m/s/s in the cloth's own frame), "points" (nodes x 3, the cloth at rest, metres),
"faces" (triangles x 3), "pinned" (one bool a node: held where it rests, on the pole), "material": {"density" kg/m2,
"mu" N/m, "lambda" N/m, "bending" N (Newton's edge stiffness), "radius" m}, "air": {"density" kg/m3, "normal_drag"
(the plate's normal force coefficient)}, "wind" (frames x 3, the wind in m/s at each frame, held linear between
frames)}.

The wind pushes each triangle along its normal by the pressure of the wind's speed across it, relative to the
triangle's own velocity: 0.5 rho C A (n . v) |n . v| (the flat plate's normal pressure), a third of it on each corner,
set as the particles' outside force before every substep. No self contact, nothing else to meet: a flag in the open.
No damping of the cloth's own (the people cloth's finding, score/stages/people_cloth/CLAUDE.md): the air's push
against the cloth's own speed is the damping.

out.npz: `points` frames x nodes x 3 (the cloth's own frame, metres, each frame's end), `engine` (text).
"""
import json
import pathlib
import sys

import newton
import numpy as np
import warp as wp


def arguments():
    given = sys.argv[1:]
    if len(given) != 2:
        raise SystemExit(__doc__)
    return pathlib.Path(given[0]), pathlib.Path(given[1])


def aero_forces(points, speeds, faces, wind, air):
    """The flat-plate normal pressure of the wind on each triangle, a third on each corner (nodes x 3, newtons)."""
    corners = points[faces]
    doubled = np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0])
    area = 0.5 * np.linalg.norm(doubled, axis=1)
    normal = doubled / np.maximum(2.0 * area, 1e-12)[:, None]
    across = np.einsum("ij,ij->i", normal, wind[None, :] - speeds[faces].mean(axis=1))
    push = (0.5 * air["density"] * air["normal_drag"] * area * across * np.abs(across))[:, None] * normal
    found = np.zeros_like(points)
    for corner in range(3):
        np.add.at(found, faces[:, corner], push / 3.0)
    return found


class Flag:
    """One cloth mesh in one Newton model, VBD over it."""

    def __init__(self, job):
        builder = newton.ModelBuilder(up_axis=newton.Axis.Y, gravity=(0.0, 0.0, 0.0))
        material = job["material"]
        self.faces = np.asarray(job["faces"], dtype=np.int32)
        builder.add_cloth_mesh(pos=wp.vec3(0.0, 0.0, 0.0), rot=wp.quat_identity(), scale=1.0,
                               vel=wp.vec3(0.0, 0.0, 0.0), vertices=[wp.vec3(*point) for point in job["points"]],
                               indices=self.faces.ravel().tolist(), density=material["density"],
                               tri_ke=material["mu"], tri_ka=material["lambda"], tri_kd=0.0,
                               edge_ke=material["bending"], edge_kd=0.0, particle_radius=material["radius"],
                               label="flag")
        self.pinned = np.asarray(job["pinned"], dtype=bool)
        for index in np.flatnonzero(self.pinned):
            builder.particle_mass[index] = 0.0
        self.masses = np.asarray(builder.particle_mass, dtype=np.float64)
        builder.color()
        self.model = builder.finalize(device=job["device"])
        self.solver = newton.solvers.SolverVBD(self.model, iterations=job["iterations"],
                                               deterministic=wp.DeterministicMode.RUN_TO_RUN)
        self.now, self.next = self.model.state(), self.model.state()
        self.control = self.model.control()
        self.gravity = np.asarray(job["gravity"], dtype=np.float64)
        self.air, self.rate, self.substeps = job["air"], job["rate"], job["substeps"]

    def pushed(self, wind):
        """The outside force on every free node: the wind's pressure and its own weight (the model's gravity is
        off, so the cloth's frame may stand any way up)."""
        points, speeds = self.now.particle_q.numpy(), self.now.particle_qd.numpy()
        found = aero_forces(points.astype(np.float64), speeds.astype(np.float64), self.faces, wind, self.air)
        found += self.masses[:, None] * self.gravity[None, :]
        found[self.pinned] = 0.0
        return found.astype(np.float32)

    def frame(self, wind, after):
        """Step one frame: `substeps` steps, the wind held linear from this frame's to the next's."""
        step = 1.0 / (self.rate * self.substeps)
        for number in range(self.substeps):
            share = number / self.substeps
            self.now.clear_forces()
            self.now.particle_f.assign(self.pushed(wind * (1.0 - share) + after * share))
            self.solver.step(self.now, self.next, self.control, None, step)
            self.now, self.next = self.next, self.now

    def points(self):
        return self.now.particle_q.numpy().copy()


def run(job_path, out_path):
    job = json.loads(job_path.read_text())
    flag = Flag(job)
    wind = np.asarray(job["wind"], dtype=np.float64)
    found = [flag.points()]
    for frame in range(job["frames"] - 1):
        flag.frame(wind[frame], wind[min(frame + 1, len(wind) - 1)])
        found.append(flag.points())
    engine = (f"newton {newton.__version__} SolverVBD ({job['iterations']} iterations, {job['substeps']} substeps a "
              f"frame, run-to-run deterministic) on {job['device']}")
    np.savez_compressed(out_path, engine=np.array(engine), points=np.asarray(found))


if __name__ == "__main__":
    run(*arguments())
