"""Drape a GarmentCode garment on its body with Newton (newton-physics/newton, Apache-2.0, on NVIDIA Warp, Apache-2.0):
the commercial-OK simulator that replaces GarmentCode's own Warp fork (non-commercial) and Blender's rougher cloth.
Runs in the newton environment (tools/props/cloud/characters_setup.sh), on a card or, slowly, on a processor.

    python newton_drape.py <job.json>

job.json (written by `drape_garment.py`):
    {"sewing": "<name>_sewing.npz", "box_mesh": "<name>_boxmesh.obj", "labels": "<name>_vertex_labels.yaml",
     "measurements": "ours.yaml" (GarmentCode's, centimetres), "body": "ours.obj" (metres, y up),
     "joints": "joints.json" or null, "cloth": {...} the design's cloth.json, "out": "<folder>", "name": "<name>"}

The set-up follows GarmentCode's own simulation (pygarment/meshgen/garment.py, MIT), written anew for Newton; nothing
of the Warp fork is used. The cloth is GarmentCode's box mesh, welded: the panels already stand round the body with
each seam's points shared, halfway across the gap. Each triangle's rest shape and each edge's rest length come from
its own flat panel (the sewing record, `sewing.py`), so the stretched seams pull themselves shut and the panels take
their true shape round the body: that is the sewing. Bending rests flat. Gravity is off for the first frames, as
GarmentCode's run held it off, then `gravity` (it may be lighter) while the seams close and the held points are held,
then `settle_gravity` (the earth's, 9.81 m/s^2) from the attachment's release to the end; the waist points are
held at the body's waist level and the collars at the neck's
width for the attachment frames, as GarmentCode's Warp run held them (`sewing.attachments`); every point's speed is
damped and clamped; the body is a triangle mesh the cloth slides on with friction; the cloth collides with itself.
The run ends when the cloth is still (GarmentCode's test: fewer than a share of its points moving more than a
threshold in a frame) or at the design's last frame.

Solver: Newton's SolverVBD (vertex block descent: StVK membrane, dihedral bending, body and self contact).
Settings: the design's cloth.json "newton" section (`SETTINGS` names each with its default).

Writes <out>/<name>_sim.obj (centimetres, the box mesh's point order, as GarmentCode's save_frame wrote it) and
<out>/newton_cloth.json: the simulator (name, version, licence), the settings, the frames run, seconds, whether it
came to rest, how many points ended inside the body and how far from it, and the sleeves' cover of the upper arms.
"""
import json
import math
import pathlib
import sys
import time

import numpy as np
import warp as wp
import yaml

import newton

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import sewing  # noqa: E402

CENTIMETRES = 0.01
SIMULATOR = {"name": "Newton SolverVBD", "licence": "Apache-2.0 (Newton and NVIDIA Warp)",
             "source": "https://github.com/newton-physics/newton"}
# The design's "newton" settings and their defaults (the work suit's, tuned on Nev against GarmentCode's Warp drape,
# 2026-10-09): metres, kilograms, seconds.
SETTINGS = {
    "density": 0.3,              # cloth mass per square metre of flat panel
    "gravity": 2.0,              # while the seams close and the held points are held (after the zero-gravity frames)
    "settle_gravity": 9.81,      # from the attachment's release to the end: the final settle is always under this
    "tri_ke": 500.0,             # membrane stiffness (StVK, N/m); 3000 pulled a work suit off the shoulders
    "tri_ka": 500.0,             # membrane area stiffness
    "tri_kd": 1.0e-4,            # membrane damping
    "edge_ke": 2.0,              # bending stiffness; much lower leaves many small crumples
    "edge_kd": 1.0e-5,           # bending damping
    "body_ke": 1.0e3,            # body contact stiffness
    "body_kd": 1.0e-3,           # body contact damping
    "body_mu": 0.5,              # body friction (GarmentCode's body_friction)
    "body_margin": 0.0025,       # how far off the body the cloth is kept (GarmentCode's body_collision_thickness)
    "particle_radius": 0.002,    # the cloth's half thickness for body contact
    "self_contact": True,
    "self_margin": 0.003,        # cloth-to-cloth distance
    "self_gap": 0.002,           # extra detection distance
    "fps": 60,                   # GarmentCode's sim_fps
    "substeps": 10,              # GarmentCode's sim_substeps
    "iterations": 10,            # VBD iterations a substep
    "zero_gravity_frames": 10,   # GarmentCode's zero_gravity_steps
    "attachment_frames": 400,    # GarmentCode's attachment_frames
    "hold_to_end": False,        # keep holding the waist and collars through the settle (a belted suit's waist)
    "attachment_rate": 0.05,     # share of the way to a held point's target taken each substep
    "below_waist": 0.0,          # the waist held this share of the height under GarmentCode's waist level
    "damping": 2.0,              # every point's speed loses this share a second (GarmentCode's global damping)
    "max_speed": 0.25,           # metres a second (GarmentCode's global_max_velocity, 25 cm/s)
    "min_frames": 450,           # never stop before this frame (the cloth answers the settle's gravity first)
    "max_frames": 1200,          # stop here if the cloth is still moving
    "still_cm": 0.03,            # GarmentCode's static_threshold: a point moving less per frame is still
    "still_share": 0.015,        # GarmentCode's non_static_percent (1.5 %): this share may still move
}


def job():
    given = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    if len(given) != 1:
        raise SystemExit(__doc__)
    return json.loads(pathlib.Path(given[0]).read_text())


def settings_of(cloth):
    """The design's Newton settings over the defaults."""
    given = cloth.get("newton", {})
    unknown = set(given) - set(SETTINGS)
    if unknown:
        raise SystemExit(f"unknown newton settings in cloth.json: {sorted(unknown)}")
    return {**SETTINGS, **given}


def add_cloth(builder, record, start, settings):
    """The welded cloth: a particle per box mesh point at `start` (metres), each triangle with its flat panel's rest
    shape, each edge bending with its flat panel's rest length and a flat rest angle; the number of edges whose
    bending was left out (`sewing.bending_edges`)."""
    count = len(start)
    laid = np.asarray(record["points"], dtype=float) * CENTIMETRES
    welded = sewing.welded_faces(record)
    masses = sewing.point_masses({**record, "points": laid}, count, settings["density"])
    builder.add_particles([tuple(point) for point in start], [(0.0, 0.0, 0.0)] * count, masses.tolist(),
                          radius=[settings["particle_radius"]] * count)
    # A triangle's rest shape is read from where its corners are when it is added: each panel's corners are put
    # where the flat panel has them while its triangles are added, then every point goes back to the start.
    for number in np.unique(record["panel"]):
        mine = np.where(record["panel"] == number)[0]
        for copy in mine:
            builder.particle_q[int(record["box_index"][copy])] = wp.vec3(*laid[copy])
        panel_faces = welded[record["panel"][record["faces"][:, 0]] == number]
        builder.add_triangles(panel_faces[:, 0], panel_faces[:, 1], panel_faces[:, 2],
                              tri_ke=[settings["tri_ke"]] * len(panel_faces),
                              tri_ka=[settings["tri_ka"]] * len(panel_faces),
                              tri_kd=[settings["tri_kd"]] * len(panel_faces),
                              tri_drag=[0.0] * len(panel_faces), tri_lift=[0.0] * len(panel_faces))
    for index, point in enumerate(start):
        builder.particle_q[index] = wp.vec3(*point)
    edges, owners, odd = sewing.bending_edges(welded)
    first = len(builder.edge_indices)
    builder.add_edges(edges[:, 0].tolist(), edges[:, 1].tolist(), edges[:, 2].tolist(), edges[:, 3].tolist(),
                      rest=[0.0] * len(edges), edge_ke=[settings["edge_ke"]] * len(edges),
                      edge_kd=[settings["edge_kd"]] * len(edges))
    lengths = sewing.rest_edge_lengths({**record, "points": laid}, edges, owners)
    builder.edge_rest_length[first:first + len(edges)] = lengths.tolist()
    return odd


def add_body(builder, path, settings):
    """The body as a fixed triangle mesh the cloth collides with."""
    points, faces = sewing.read_obj(path)
    shape = newton.ModelBuilder.ShapeConfig(ke=settings["body_ke"], kd=settings["body_kd"], mu=settings["body_mu"],
                                           margin=settings["body_margin"])
    builder.add_shape_mesh(body=-1, mesh=newton.Mesh(points, faces.reshape(-1)), cfg=shape)
    return points, faces


@wp.kernel
def hold_points(points: wp.array[wp.int32], axes: wp.array[wp.int32], targets: wp.array[wp.float32], rate: float,
                positions: wp.array[wp.vec3]):
    """Move each held point a share of the way to its target along its axis (GarmentCode's attachment: the waist
    level along y, a collar's x)."""
    index = wp.tid()
    point = points[index]
    position = positions[point]
    position[axes[index]] = position[axes[index]] + rate * (targets[index] - position[axes[index]])
    positions[point] = position


@wp.kernel
def damp_and_clamp(velocities: wp.array[wp.vec3], keep: float, most: float):
    """Every point's speed damped by a share and clamped to the most allowed (GarmentCode's global damping)."""
    index = wp.tid()
    velocity = velocities[index] * keep
    speed = wp.length(velocity)
    if speed > most:
        velocity = velocity * (most / speed)
    velocities[index] = velocity


@wp.kernel
def outside_distance(mesh: wp.uint64, positions: wp.array[wp.vec3], reach: float, signed: wp.array[wp.float32]):
    """Each point's signed distance to the body (negative inside), or `reach` when farther."""
    index = wp.tid()
    query = wp.mesh_query_point(mesh, positions[index], reach)
    if query.result:
        nearest = wp.mesh_eval_position(mesh, query.face, query.u, query.v)
        signed[index] = query.sign * wp.length(positions[index] - nearest)
    else:
        signed[index] = reach


def held_arrays(task, record, settings):
    """GarmentCode's held points as arrays for `hold_points`, in metres, the waist lowered by `below_waist`."""
    labels = yaml.safe_load(pathlib.Path(task["labels"]).read_text()) or {}
    body = yaml.safe_load(pathlib.Path(task["measurements"]).read_text())["body"]
    points, axes, targets = [], [], []
    for indices, axis, value in sewing.attachments(labels, body):
        if axis == 1:
            value -= settings["below_waist"] * body["height"]
        points.extend(indices.tolist())
        axes.extend([axis] * len(indices))
        targets.extend([value * CENTIMETRES] * len(indices))
    return (wp.array(points, dtype=wp.int32), wp.array(axes, dtype=wp.int32), wp.array(targets, dtype=wp.float32),
            len(points))


class Drape:
    """The model, solver and states of one drape."""

    def __init__(self, task, record, settings):
        self.settings = settings
        builder = newton.ModelBuilder(up_axis=newton.Axis.Y, gravity=0.0)
        box_points, _ = sewing.read_obj(task["box_mesh"])
        self.start = box_points * CENTIMETRES
        self.odd_edges = add_cloth(builder, record, self.start, settings)
        self.body_points, self.body_faces = add_body(builder, task["body"], settings)
        builder.color(include_bending=True)
        self.model = builder.finalize()
        self.model.soft_contact_ke = settings["body_ke"]
        self.model.soft_contact_kd = settings["body_kd"]
        self.model.soft_contact_mu = settings["body_mu"]
        self.pipeline = newton.CollisionPipeline(self.model, soft_contact_gap=settings["self_gap"] + 0.005)
        self.solver = newton.solvers.SolverVBD(
            self.model, iterations=settings["iterations"], particle_enable_self_contact=settings["self_contact"],
            particle_self_contact_margin=settings["self_margin"], particle_self_contact_gap=settings["self_gap"],
            collision_pipeline=self.pipeline)
        self.states = [self.model.state(), self.model.state()]
        self.control = self.model.control()
        self.held = held_arrays(task, record, settings)
        self.step_seconds = 1.0 / settings["fps"] / settings["substeps"]
        self.keep = math.exp(-settings["damping"] * self.step_seconds)
        self.graphs = {}
        if settings["substeps"] % 2:
            raise SystemExit("newton settings: substeps must be even (the states swap each substep)")

    def gravity(self, value):
        self.model.set_gravity((0.0, -value, 0.0))

    def frame(self, holding):
        """One frame of substeps; on a card, a CUDA graph of it captured once for holding and once for not (the
        substeps are even, so the states end where they began; gravity is changed in place)."""
        if not wp.get_device().is_cuda:
            self.substeps(holding)
            return
        if holding not in self.graphs:
            with wp.ScopedCapture() as capture:
                self.substeps(holding)
            self.graphs[holding] = capture.graph
        wp.capture_launch(self.graphs[holding])

    def substeps(self, holding):
        for _ in range(self.settings["substeps"]):
            self.states[0].clear_forces()
            self.solver.step(self.states[0], self.states[1], self.control, None, self.step_seconds)
            self.states = [self.states[1], self.states[0]]
            if holding and self.held[3]:
                wp.launch(hold_points, dim=self.held[3], inputs=[*self.held[:3], self.settings["attachment_rate"],
                                                                 self.states[0].particle_q])
            wp.launch(damp_and_clamp, dim=self.model.particle_count,
                      inputs=[self.states[0].particle_qd, self.keep, self.settings["max_speed"]])

    def points(self):
        return self.states[0].particle_q.numpy().astype(float)


def run(drape, settings):
    """Frames until the cloth is still after the attachment is let go (and after `min_frames`), or `max_frames`;
    the frames run, whether it came to rest, the seconds taken, and the moving share at each hundredth frame."""
    began, last, trace = time.time(), drape.points(), []
    drape.gravity(0.0)
    still = False
    for frame in range(settings["max_frames"]):
        if frame == settings["zero_gravity_frames"]:
            drape.gravity(settings["gravity"])
        if frame == settings["attachment_frames"]:
            drape.gravity(settings["settle_gravity"])
        drape.frame(settings["hold_to_end"] or frame < settings["attachment_frames"])
        now = drape.points()
        if not np.isfinite(now).all():
            raise RuntimeError(f"the cloth blew up at frame {frame}")
        moving = float((np.abs(now - last).sum(axis=1) > settings["still_cm"] * CENTIMETRES).mean())
        last = now
        if frame % 100 == 0:
            trace.append({"frame": frame, "moving": round(moving, 4), "seconds": round(time.time() - began, 1)})
            print(f"frame {frame}: {moving:.1%} of the cloth moving, {time.time() - began:.0f} s", flush=True)
        if frame >= max(settings["attachment_frames"], settings["min_frames"]) and moving < settings["still_share"]:
            still = True
            break
    return frame + 1, still, time.time() - began, trace


def body_distances(drape, points):
    """Each cloth point's signed distance to the body in metres (negative inside), up to 10 cm."""
    mesh = wp.Mesh(points=wp.array(drape.body_points, dtype=wp.vec3),
                   indices=wp.array(drape.body_faces.reshape(-1), dtype=wp.int32), support_winding_number=True)
    signed = wp.zeros(len(points), dtype=wp.float32)
    wp.launch(outside_distance, dim=len(points), inputs=[mesh.id, wp.array(points, dtype=wp.vec3), 0.1, signed])
    return signed.numpy()


def sleeve_cover(task, record, points):
    """Each arm's bare shares of the upper arm (`sewing.uncovered`), as cloth_drape.py checks them; {} without
    joints."""
    if not task.get("joints"):
        return {}
    joints = json.loads(pathlib.Path(task["joints"]).read_text())
    names = [str(name) for name in record["panel_names"]]
    welded = sewing.welded_faces(record)
    span = task["cloth"].get("blender", {}).get("sleeve_span", [0.3, 0.75])
    bare = {}
    for side, (shoulder, elbow) in (("left_arm", ("LeftArm", "LeftForeArm")), ("right_arm", ("RightArm",
                                                                                            "RightForeArm"))):
        on = np.zeros(len(points), dtype=bool)
        for number, name in enumerate(names):
            if sewing.arm_of(name) == side:
                on[record["box_index"][record["panel"] == number]] = True
        bare[side] = sewing.uncovered(points, welded, on, joints[shoulder], joints[elbow], span)
    return bare


def write_result(task, points, report):
    out = pathlib.Path(task["out"])
    out.mkdir(parents=True, exist_ok=True)
    box_text = pathlib.Path(task["box_mesh"]).read_text()
    (out / f"{task['name']}_sim.obj").write_text(sewing.sim_obj(box_text, points / CENTIMETRES))
    (out / "newton_cloth.json").write_text(json.dumps(report, indent=1))
    print(json.dumps({key: value for key, value in report.items() if key != "cloth"}, indent=1))


def main():
    task = job()
    record = dict(np.load(task["sewing"]))
    settings = settings_of(task["cloth"])
    wp.init()
    drape = Drape(task, record, settings)
    frames, still, seconds, trace = run(drape, settings)
    points = drape.points()
    signed = body_distances(drape, points)
    report = {"simulator": {**SIMULATOR, "version": newton.__version__, "warp": wp.__version__,
                            "device": str(wp.get_device())},
              "settings": settings, "cloth": task["cloth"], "points": len(points),
              "frames": frames, "came_to_rest": still, "seconds": round(seconds, 1), "trace": trace,
              "held_points": drape.held[3], "edges_without_bending": drape.odd_edges,
              "points_inside_body": int((signed < 0).sum()),
              "deepest_inside_cm": round(float(-min(signed.min(), 0.0)) / CENTIMETRES, 2),
              "bare_arm": sleeve_cover(task, record, points)}
    if not still:
        print("WARNING: the cloth was still moving at the last frame; look at it before using it", flush=True)
    write_result(task, points, report)


if __name__ == "__main__":
    main()
