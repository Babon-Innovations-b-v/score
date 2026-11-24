"""Runs in Newton's own Python (score/stages/physics/inside/newton_env.sh, pinned; Newton and Warp, Apache-2.0): an
outfit of GarmentCode garments sewn, draped and worn over one clip on Newton's SolverVBD, against the person's body as
one moving triangle mesh. Never GarmentCode's own simulator (its Warp fork is non-commercial).

    <env>/bin/python tools/characters/garments/inside/drape.py <job.json> <out.npz>

job.json (written by tools/characters/garments): {"device", "rate" (frames a second), "substeps", "iterations",
"gravity" (m/s2), "body": <npz: `bind` points x 3 (m), `faces`, `frames` frames x points x 3 (the body's skin every
frame of the run: its turn from the bind to the clip's first frame, then the clip), `clip_start`>, "sew_seconds",
"still_seconds", "garments": [{"name", "record": <pattern.py's npz>, "offset": [x, y, z] (m, the record's frame to the
body's), "worn": [labels of the record's points worn on the body], "holds": [{"label", "axis" (0 x, 1 y, 2 z),
"value" (m)}: points drawn to a level while sewing], "material": {"density" kg/m2, "mu" N/m, "lambda" N/m, "bending" N,
"radius" m}}], "contact": {"mu", "ke", "kd", "margin" (m)}, "self": {"margin", "gap" (m)}}.

The run, in the order GarmentCode's own drape goes: each garment's box mesh (its panels laid round the body, each seam's
points shared) is one cloth whose triangles rest at their flat panels' shapes and whose edges bend flat, so the seams
pull shut and the panels take their sewn shape round the body; a garment's held points (its waistband's top,
GarmentCode's `lower_interface`) are carried from where the box lays them to the body's skin under them at the waist
level and then ride the skin as a worn waistband does, every other point is cloth; a garment's drawn points (a
neckline's sides, GarmentCode's `right_collar` and `left_collar`) are drawn to their level while sewing, as
GarmentCode's attachments draw them, and let go after. Gravity is off for the first fifth
of `sew_seconds`, then on; speeds are capped at SEW_SPEED while sewing (GarmentCode's global cap), never after. Then
the body turns from its bind to the clip's first frame (the job's frames up to `clip_start`), stands `still_seconds`,
and plays the clip. Each substep the body mesh's points and velocities are set where the skin is at the substep's end
and the mesh refitted, so the cloth meets the moving body with its own speed (Newton reads mesh velocities for
contact). Cloth and cloth collide (self contact, between garments too). No cloth damping of its own. VBD's run-to-run
deterministic mode is off: on this card it took a substep from 10 ms to 180 ms (2026-11-24).

out.npz: per garment `<name>` clip frames x points x 3 (m, world, each clip frame's end), `<name>/sewn` points x 3 (at
the bind after sewing), `inside/<name>` clip frames x points (each point's signed distance to the body at that frame,
m, negative inside), `seconds/clip` (the clip's wall seconds), `seconds/sew`, `engine` (text).
"""
import json
import pathlib
import sys
import time

import newton
import numpy as np
import warp as wp

SEW_SPEED = 0.25  # m/s, GarmentCode's global_max_velocity while the panels close (sim_config.py)
CENTIMETRES = 0.01
HOLD_SHARE = 0.05  # of the way to its level a drawn point moves each substep while sewing


def arguments():
    given = sys.argv[1:]
    if len(given) != 2:
        raise SystemExit(__doc__)
    return pathlib.Path(given[0]), pathlib.Path(given[1])


def bending_edges(faces):
    """Each inner edge of the welded mesh with its two triangles' far corners, as Newton's (o1, o2, v1, v2), and the
    triangle each side came from."""
    found, sides = {}, []
    for number, face in enumerate(faces):
        for corner in range(3):
            one, other, far = face[corner], face[(corner + 1) % 3], face[(corner + 2) % 3]
            key = (min(one, other), max(one, other))
            if key in found:
                first_far, first_face = found.pop(key)
                sides.append(((first_far, far, key[0], key[1]), (first_face, number)))
            else:
                found[key] = (far, number)
    return sides


@wp.kernel
def capped(velocities: wp.array[wp.vec3], most: float):
    index = wp.tid()
    speed = wp.length(velocities[index])
    if speed > most:
        velocities[index] = velocities[index] * (most / speed)


@wp.kernel
def signed_distance(mesh: wp.uint64, points: wp.array[wp.vec3], reach: float, found: wp.array[wp.float32]):
    """Each point's distance to the body's surface, negative inside (winding number), `reach` when farther."""
    index = wp.tid()
    query = wp.mesh_query_point_sign_winding_number(mesh, points[index], reach)
    if query.result:
        nearest = wp.mesh_eval_position(mesh, query.face, query.u, query.v)
        found[index] = query.sign * wp.length(points[index] - nearest)
    else:
        found[index] = reach


@wp.kernel
def nearest(mesh: wp.uint64, points: wp.array[wp.vec3], reach: float, faces: wp.array[wp.int32],
            uvs: wp.array[wp.vec2]):
    """Each point's nearest place on the mesh: its triangle (-1 past `reach`) and barycentric u, v."""
    index = wp.tid()
    query = wp.mesh_query_point_no_sign(mesh, points[index], reach)
    faces[index] = -1
    if query.result:
        faces[index] = query.face
        uvs[index] = wp.vec2(query.u, query.v)


@wp.kernel
def drawn(particles: wp.array[wp.int32], axis: int, value: float, share: float, positions: wp.array[wp.vec3]):
    """Each point moved `share` of the way to `value` along `axis` (GarmentCode's attachment while sewing)."""
    index = wp.tid()
    particle = particles[index]
    position = positions[particle]
    position[axis] = position[axis] + share * (value - position[axis])
    positions[particle] = position


@wp.kernel
def skin_at(frames: wp.array[wp.vec3], count: int, frame: int, after: int, share: float, rate: float,
            points: wp.array[wp.vec3], velocities: wp.array[wp.vec3]):
    """The body's skin `share` of the way from `frame` to `after` (frames stored one after another, `count` points
    each), and its velocity over the frame."""
    index = wp.tid()
    one, other = frames[frame * count + index], frames[after * count + index]
    points[index] = one * (1.0 - share) + other * share
    velocities[index] = (other - one) * rate


@wp.kernel
def held_on(particles: wp.array[wp.int32], corners: wp.array[wp.vec3i], weights: wp.array[wp.vec3],
            start: wp.array[wp.vec3], radius: float, carry: float, skin: wp.array[wp.vec3], rate: float,
            positions: wp.array[wp.vec3], velocities: wp.array[wp.vec3]):
    """Each held point `carry` of the way from where the box laid it to its place on the skin (out by `radius`), its
    velocity the move over the substep."""
    index = wp.tid()
    triangle, weight = corners[index], weights[index]
    one, two, three = skin[triangle[0]], skin[triangle[1]], skin[triangle[2]]
    normal = wp.normalize(wp.cross(two - one, three - one))
    on = one * weight[0] + two * weight[1] + three * weight[2] + normal * radius
    target = start[index] * (1.0 - carry) + on * carry
    particle = particles[index]
    velocities[particle] = (target - positions[particle]) * rate
    positions[particle] = target


class Garment:
    """One garment's cloth in the builder: its particles, triangles, bending edges and held points."""

    def __init__(self, builder, spec):
        record = dict(np.load(spec["record"]))
        offset = np.asarray(spec["offset"], dtype=float)
        self.name, self.first = spec["name"], builder.particle_count
        self.points = record["points"] * CENTIMETRES + offset
        copies, box, faces = record["copies"] * CENTIMETRES + offset, record["box"], record["faces"]
        welded = box[faces]
        self.faces, self.count = welded, len(self.points)
        material = spec["material"]
        flat = copies[faces]
        areas = 0.5 * np.linalg.norm(np.cross(flat[:, 1] - flat[:, 0], flat[:, 2] - flat[:, 0]), axis=1)
        masses = np.zeros(self.count)
        np.add.at(masses, welded.ravel(), np.repeat(areas / 3.0 * material["density"], 3))
        self.held = np.unique(np.concatenate([record[f"label/{key}"] for key in spec.get("worn", [])]
                                             or [np.zeros(0, int)]))
        self.holds = [(record[f"label/{hold['label']}"] + self.first, hold["axis"], hold["value"])
                      for hold in spec.get("holds", [])]
        masses[self.held] = 0.0
        builder.add_particles([tuple(point) for point in self.points], [(0.0, 0.0, 0.0)] * self.count,
                              masses.tolist(), radius=[material["radius"]] * self.count)
        # A triangle's rest shape is read off its corners where they stand when it is added: each panel's corners are
        # put on its flat panel (laid in 3D) while its triangles go in, then every point goes back to the box mesh.
        for panel in np.unique(record["panel"]):
            mine = np.flatnonzero(record["panel"] == panel)
            for copy in mine:
                builder.particle_q[self.first + int(box[copy])] = wp.vec3(*copies[copy])
            panel_faces = welded[record["panel"][faces[:, 0]] == panel] + self.first
            count = len(panel_faces)
            builder.add_triangles(panel_faces[:, 0], panel_faces[:, 1], panel_faces[:, 2],
                                  tri_ke=[material["mu"]] * count, tri_ka=[material["lambda"]] * count,
                                  tri_kd=[0.0] * count, tri_drag=[0.0] * count, tri_lift=[0.0] * count)
        for index, point in enumerate(self.points):
            builder.particle_q[self.first + index] = wp.vec3(*point)
        sides = bending_edges(welded)
        corners = np.array([corner for corner, _ in sides], dtype=np.int64) + self.first
        builder.add_edges(corners[:, 0].tolist(), corners[:, 1].tolist(), corners[:, 2].tolist(),
                          corners[:, 3].tolist(), rest=[0.0] * len(sides),
                          edge_ke=[material["bending"]] * len(sides), edge_kd=[0.0] * len(sides))
        self.edges = len(sides)


class Outfit:
    """The body and every garment in one Newton model, VBD over it."""

    def __init__(self, job, body):
        builder = newton.ModelBuilder(up_axis=newton.Axis.Y, gravity=(0.0, 0.0, 0.0))
        self.frames, self.bind = body["frames"].astype(np.float32), body["bind"].astype(np.float32)
        self.faces = body["faces"].astype(np.int32)
        contact = job["contact"]
        shape = newton.ModelBuilder.ShapeConfig(mu=contact["mu"], ke=contact["ke"], kd=contact["kd"],
                                               margin=contact["margin"])
        self.body = newton.Mesh(self.bind, self.faces.ravel())
        builder.add_shape_mesh(body=-1, mesh=self.body, cfg=shape)
        self.garments = [Garment(builder, spec) for spec in job["garments"]]
        builder.color(include_bending=True)
        self.model = builder.finalize(device=job["device"])
        self.model.soft_contact_mu, self.model.soft_contact_ke = contact["mu"], contact["ke"]
        self.model.soft_contact_kd = contact["kd"]
        self.mesh = self.body.mesh  # the wp.Mesh the model collides with, its points moved each substep
        self.pipeline = newton.CollisionPipeline(self.model, soft_contact_gap=contact["margin"])
        self.contacts = self.pipeline.contacts()
        self.solver = newton.solvers.SolverVBD(
            self.model, iterations=job["iterations"], particle_enable_self_contact=True,
            particle_self_contact_margin=job["self"]["margin"], particle_self_contact_gap=job["self"]["gap"])
        self.now, self.next = self.model.state(), self.model.state()
        self.control = self.model.control()
        self.rate, self.substeps = job["rate"], job["substeps"]
        self.holds = [(wp.array(points.astype(np.int32), dtype=wp.int32), axis, value)
                      for garment in self.garments for points, axis, value in garment.holds]
        self.frames_card = wp.array(self.frames.reshape(-1, 3), dtype=wp.vec3)
        self.held = [self.worn_on(garment) for garment in self.garments if len(garment.held)]

    def worn_on(self, garment):
        """Where each held point is worn: the body's nearest surface point to it at the bind, out by the cloth's
        radius along that triangle's normal, as arrays on the card: (particles, the triangles' corners, barycentric
        weights, the box mesh's start, the radius)."""
        mesh = wp.Mesh(points=wp.array(self.bind, dtype=wp.vec3), indices=wp.array(self.faces.ravel(), dtype=wp.int32))
        count = len(garment.held)
        faces, uvs = wp.zeros(count, dtype=wp.int32), wp.zeros(count, dtype=wp.vec2)
        wp.launch(nearest, dim=count, inputs=[mesh.id, wp.array(garment.points[garment.held], dtype=wp.vec3), 1.0,
                                              faces, uvs])
        faces, uvs = faces.numpy(), uvs.numpy()
        if (faces < 0).any():
            raise RuntimeError(f"{garment.name}: a held point is over a metre off the body")
        weights = np.stack([1.0 - uvs[:, 0] - uvs[:, 1], uvs[:, 0], uvs[:, 1]], axis=1)
        radius = float(self.model.particle_radius.numpy()[garment.first])
        return (wp.array((garment.first + garment.held).astype(np.int32), dtype=wp.int32),
                wp.array(self.faces[faces].astype(np.int32), dtype=wp.vec3i), wp.array(weights, dtype=wp.vec3),
                wp.array(garment.points[garment.held], dtype=wp.vec3), radius)

    def step(self, frame, share, carry, sewing):
        """One substep ending `share` of the way from `frame` to the next: the body there (its mesh's points and
        velocities, refitted), the held points carried `carry` of the way to the skin, then VBD."""
        after = min(frame + 1, len(self.frames) - 1)
        wp.launch(skin_at, dim=len(self.bind), inputs=[self.frames_card, len(self.bind), frame, after, share,
                                                        self.rate, self.mesh.points, self.mesh.velocities])
        self.mesh.refit()
        for particles, corners, weights, start, radius in self.held:
            wp.launch(held_on, dim=len(particles), inputs=[particles, corners, weights, start, radius, carry,
                                                           self.mesh.points, self.rate * self.substeps,
                                                           self.now.particle_q, self.now.particle_qd])
        self.now.clear_forces()
        self.pipeline.collide(self.now, self.contacts)
        self.solver.step(self.now, self.next, self.control, self.contacts, 1.0 / (self.rate * self.substeps))
        self.now, self.next = self.next, self.now
        if sewing:
            wp.launch(capped, dim=self.model.particle_count, inputs=[self.now.particle_qd, SEW_SPEED])
            for particles, axis, value in self.holds:
                wp.launch(drawn, dim=len(particles), inputs=[particles, axis, value, HOLD_SHARE, self.now.particle_q])

    def frame(self, frame, carry=1.0, sewing=False, moving=True):
        """Every substep from `frame` to the next (not `moving`: the body held at `frame`)."""
        for number in range(self.substeps):
            share = (number + 1) / self.substeps * moving
            self.step(frame, share, carry, sewing)

    def points(self, garment):
        return self.now.particle_q.numpy()[garment.first:garment.first + garment.count].copy()

    def inside(self, frame, points):
        """Each point's signed distance to the body at `frame` (m, negative inside)."""
        mesh = wp.Mesh(points=wp.array(self.frames[frame], dtype=wp.vec3),
                       indices=wp.array(self.faces.ravel(), dtype=wp.int32), support_winding_number=True)
        found = wp.zeros(len(points), dtype=wp.float32)
        wp.launch(signed_distance, dim=len(points), inputs=[mesh.id, wp.array(points, dtype=wp.vec3), 0.1, found])
        return found.numpy()


def sewn(outfit, job):
    """The garments sewn and settled on the body held at its bind: gravity off for the first fifth, the held points
    carried onto the skin over the first half; the wall seconds."""
    began, frames = time.monotonic(), int(job["sew_seconds"] * job["rate"])
    for count in range(frames):
        if count == frames // 5:
            outfit.model.set_gravity((0.0, -job["gravity"], 0.0))
        outfit.frame(0, carry=min(1.0, count / (frames / 2.0)), sewing=True, moving=False)
        if count % 30 == 29:
            if not np.isfinite(outfit.now.particle_q.numpy()).all():
                raise RuntimeError(f"the cloth blew up sewing, frame {count}")
            print(f"sewing: frame {count + 1} of {frames}, {time.monotonic() - began:.0f} s", flush=True)
    return time.monotonic() - began


def worn(outfit, job, clip_start):
    """The turn from the bind to the clip's first frame, `still_seconds` standing, then the clip: each garment's
    points at each clip frame's end, and the clip's wall seconds."""
    for frame in range(clip_start):
        outfit.frame(frame)
    for _ in range(int(job["still_seconds"] * job["rate"])):
        outfit.frame(clip_start, moving=False)
    found = {garment.name: [outfit.points(garment)] for garment in outfit.garments}
    wp.synchronize()
    began = time.monotonic()
    for frame in range(clip_start, len(outfit.frames) - 1):
        outfit.frame(frame)
        for garment in outfit.garments:
            found[garment.name].append(outfit.points(garment))
        if not np.isfinite(outfit.now.particle_q.numpy()).all():
            raise RuntimeError(f"the cloth blew up at clip frame {frame - clip_start}")
    wp.synchronize()
    return {name: np.asarray(value) for name, value in found.items()}, time.monotonic() - began


def run(job_path, out_path):
    job = json.loads(job_path.read_text())
    body = dict(np.load(job["body"]))
    wp.init()
    with wp.ScopedDevice(job["device"]):
        outfit = Outfit(job, body)
        sew_seconds = sewn(outfit, job)
        sewn_points = {garment.name: outfit.points(garment) for garment in outfit.garments}
        clip_start = int(body["clip_start"])
        found, clip_seconds = worn(outfit, job, clip_start)
        out = {"engine": np.array(f"newton {newton.__version__} SolverVBD on warp {wp.__version__} "
                                  f"({job['iterations']} iterations, {job['substeps']} substeps a frame, not "
                                  f"run-to-run deterministic) on {wp.get_device()}"),
               "seconds/sew": np.array(sew_seconds), "seconds/clip": np.array(clip_seconds)}
        for garment in outfit.garments:
            out[garment.name] = found[garment.name]
            out[f"{garment.name}/sewn"] = sewn_points[garment.name]
            out[f"{garment.name}/faces"] = garment.faces
            out[f"inside/{garment.name}"] = np.array([outfit.inside(clip_start + number, points) for number, points
                                                      in enumerate(found[garment.name])])
        np.savez_compressed(out_path, **out)
    print(json.dumps({"sew seconds": round(sew_seconds, 1), "clip seconds": round(clip_seconds, 1),
                      "clip frames": len(found[outfit.garments[0].name])}), flush=True)


if __name__ == "__main__":
    run(*arguments())
