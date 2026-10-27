"""Runs in Newton's own Python (score/stages/physics/inside/newton_env.sh, pinned): every loose garment part of one
scene's people as cloth on Newton's VBD solver, against each person's sim body segments moving as they moved in its
sim-body run (people-cloth, owner 2026-10-27).

    <env>/bin/python score/stages/people_cloth/inside/cloth.py <job.json> <out.npz>

job.json (written by score/stages/people_cloth): {"rate", "gravity", "substeps", "iterations", "device", "motion"
(an .npz: per person `<person>/segments` frames x segments x 4 x 4, each segment's world frame; per garment part
`<person>/<part>/skinned` frames x points x 3, its points riding the skin), "people": [{"name", "segments": [{"name",
"points" (its piece of the body surface in the segment's frame), "faces"}], "parts": [{"name", "rest" (points x 3, the
part as built, at the bind), "faces", "free" (one bool a point: loose, simulated), "material": {"density" kg/m2,
"mu" N/m, "lambda" N/m, "bending" N (Newton's edge stiffness), "radius" m}}]}]}.

Each person is a Newton world of its own (every sim-body run stands in the person's own frame, so two would overlap
and meet). Each segment is a kinematic body carrying its piece of the body surface as a mesh collider, its pose set
every substep to where the substep ends between the run's frames (positions blended, turns slerped), with the matching
velocity, so the cloth meets it moving. Each part is one cloth mesh at rest at its built shape; a point not loose has
no mass and is set every substep to where the skin carries it at the substep's end (it rides the body as the baked
garment does), a loose one is simulated. No self contact.
No damping of the cloth's own: Newton's default (10 N s/m against cotton's 5 N/m shear) held loose points 5 cm behind
a walking body within 8 frames, 2026-10-27; the implicit step's own loss is the only one, as no source gives cotton's.

out.npz: per part `<person>/<part>` frames x points x 3 (world, metres, the frame's end), plus `engine` (text).
"""
import json
import pathlib
import sys

import newton
import numpy as np
import warp as wp
from scipy.spatial.transform import Rotation, Slerp


def arguments():
    given = sys.argv[1:]
    if len(given) != 2:
        raise SystemExit(__doc__)
    return pathlib.Path(given[0]), pathlib.Path(given[1])


def pose_of(world):
    """A 4 x 4 as Newton's transform values (x, y, z, qx, qy, qz, qw)."""
    return np.concatenate([world[:3, 3], Rotation.from_matrix(world[:3, :3]).as_quat()])


def blended(worlds, frame, share):
    """Each segment's pose `share` of the way from `frame` to the next (segments x 7) and its velocity over the step
    (segments x 6: Newton's body_qd, linear then angular, world)."""
    one, other = worlds[frame], worlds[min(frame + 1, len(worlds) - 1)]
    poses = np.empty((len(one), 7))
    for index, (start, end) in enumerate(zip(one, other)):
        turns = Slerp([0.0, 1.0], Rotation.from_matrix([start[:3, :3], end[:3, :3]]))
        poses[index, :3] = start[:3, 3] * (1.0 - share) + end[:3, 3] * share
        poses[index, 3:] = turns(share).as_quat()
    return poses


def velocities(worlds, frame, rate):
    """Each segment's velocity from `frame` to the next (segments x 6), held over the frame's substeps."""
    one, other = worlds[frame], worlds[min(frame + 1, len(worlds) - 1)]
    found = np.zeros((len(one), 6))
    found[:, :3] = (other[:, :3, 3] - one[:, :3, 3]) * rate
    for index, (start, end) in enumerate(zip(one, other)):
        found[index, 3:] = Rotation.from_matrix(end[:3, :3] @ start[:3, :3].T).as_rotvec() * rate
    return found


class Scene:
    """Every person's segments and loose parts in one Newton model, VBD over it."""

    def __init__(self, job, motion):
        builder = newton.ModelBuilder(up_axis=newton.Axis.Y, gravity=(0.0, -job["gravity"], 0.0))
        self.people, self.motion, self.rate = [], motion, job["rate"]
        for person in job["people"]:
            # A world each: every person's run stands in its own frame (sim-body's), so two would overlap and meet.
            builder.begin_world(label=person["name"])
            worlds = motion[f"{person['name']}/segments"]
            bodies = []
            for index, segment in enumerate(person["segments"]):
                body = builder.add_body(xform=wp.transform(*np.split(pose_of(worlds[0, index]), [3])),
                                        is_kinematic=True, label=f"{person['name']}/{segment['name']}")
                mesh = newton.Mesh(np.asarray(segment["points"], dtype=np.float32),
                                   np.asarray(segment["faces"], dtype=np.int32).ravel())
                builder.add_shape_mesh(body, mesh=mesh)
                bodies.append(body)
            parts = []
            for part in person["parts"]:
                first = builder.particle_count
                material = part["material"]
                builder.add_cloth_mesh(pos=wp.vec3(0.0, 0.0, 0.0), rot=wp.quat_identity(), scale=1.0,
                                       vel=wp.vec3(0.0, 0.0, 0.0),
                                       vertices=[wp.vec3(*point) for point in part["rest"]],
                                       indices=np.asarray(part["faces"], dtype=np.int32).ravel().tolist(),
                                       density=material["density"], tri_ke=material["mu"], tri_ka=material["lambda"],
                                       tri_kd=0.0, edge_ke=material["bending"], edge_kd=0.0,
                                       particle_radius=material["radius"],
                                       label=f"{person['name']}/{part['name']}")
                free = np.asarray(part["free"], dtype=bool)
                for offset in np.flatnonzero(~free):
                    builder.particle_mass[first + offset] = 0.0
                parts.append({"name": part["name"], "first": first, "count": len(free), "free": free,
                              "skinned": motion[f"{person['name']}/{part['name']}/skinned"]})
            builder.end_world()
            self.people.append({"name": person["name"], "bodies": bodies, "worlds": worlds, "parts": parts})
        builder.color()
        self.model = builder.finalize(device=job["device"])
        self.pipeline = newton.CollisionPipeline(self.model)
        self.contacts = self.pipeline.contacts()
        self.solver = newton.solvers.SolverVBD(self.model, iterations=job["iterations"],
                                               integrate_with_external_rigid_solver=True,
                                               deterministic=wp.DeterministicMode.RUN_TO_RUN)
        self.now, self.next = self.model.state(), self.model.state()
        self.control = self.model.control()
        self.substeps = job["substeps"]
        self.started()

    def started(self):
        """Every part's points where the skin carries them at the first frame, still."""
        points = self.now.particle_q.numpy()
        for person in self.people:
            for part in person["parts"]:
                points[part["first"]:part["first"] + part["count"]] = part["skinned"][0]
        for state in (self.now, self.next):
            state.particle_q.assign(points)
            state.particle_qd.zero_()

    def driven(self, frame, share):
        """The segments' poses and velocities and the riding points `share` of the way from `frame` to the next,
        written into the state the step reads."""
        body_q, body_qd = self.now.body_q.numpy(), self.now.body_qd.numpy()
        points, speeds = self.now.particle_q.numpy(), self.now.particle_qd.numpy()
        for person in self.people:
            worlds = person["worlds"]
            body_q[person["bodies"]] = blended(worlds, frame, share)
            body_qd[person["bodies"]] = velocities(worlds, frame, self.rate)
            after = min(frame + 1, len(worlds) - 1)
            for part in person["parts"]:
                riding = ~part["free"]
                at = part["skinned"][frame] * (1.0 - share) + part["skinned"][after] * share
                rows = part["first"] + np.flatnonzero(riding)
                points[rows] = at[riding]
                speeds[rows] = (part["skinned"][after] - part["skinned"][frame])[riding] * self.rate
        self.now.body_q.assign(body_q)
        self.now.body_qd.assign(body_qd)
        self.now.particle_q.assign(points)
        self.now.particle_qd.assign(speeds)

    def frame(self, frame):
        """Step from `frame` to the next: SUBSTEPS steps, the body and riding points moved before each."""
        step = 1.0 / (self.rate * self.substeps)
        for number in range(self.substeps):
            self.driven(frame, (number + 1) / self.substeps)  # where the step ends: a riding point is not moved by it
            self.now.clear_forces()
            self.pipeline.collide(self.now, self.contacts)
            self.solver.step(self.now, self.next, self.control, self.contacts, step)
            self.now, self.next = self.next, self.now

    def points(self):
        """Every part's points now ({person/part: points x 3})."""
        points = self.now.particle_q.numpy()
        return {f"{person['name']}/{part['name']}": points[part["first"]:part["first"] + part["count"]].copy()
                for person in self.people for part in person["parts"]}


def run(job_path, out_path):
    job = json.loads(job_path.read_text())
    motion = dict(np.load(job["motion"]))
    scene = Scene(job, motion)
    frames = max(len(person["worlds"]) for person in scene.people)
    found = {key: [value] for key, value in scene.points().items()}
    for frame in range(frames - 1):
        scene.frame(frame)
        for key, value in scene.points().items():
            found[key].append(value)
    engine = (f"newton {newton.__version__} SolverVBD ({job['iterations']} iterations, {job['substeps']} substeps a "
              f"frame, run-to-run deterministic) on {job['device']}")
    np.savez_compressed(out_path, engine=np.array(engine), **{key: np.asarray(value) for key, value in found.items()})


if __name__ == "__main__":
    run(*arguments())
