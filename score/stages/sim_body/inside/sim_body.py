"""Runs in Newton's own Python (score/stages/physics/inside/newton_env.sh: Newton with its MuJoCo solver, pinned): every
character's sim body of one scene, side by side, each on its own copy of the scene's ground and meeting nothing else
(#65).

    <env>/bin/python score/stages/sim_body/inside/sim_body.py <job.json> <out.json>

job.json (written by score/stages/sim_body): {"rate", "gravity", "people": [{"name", "segments": [{"name", "parent"
(index, -1 for the root), "local" (4 x 4, the joint's frame in its parent's at SOMA's bind pose), "mass", "com",
"inertia" (3 x 3, the segment's frame), "box" ([centre, half sizes], the segment's frame)}], "targets" (an .npz whose
`world` is frames x segments x 4 x 4: each segment's frame in the clip, from the clip's own rotations, and `ground`
n x 3 x 3: the scene's triangles it may touch, in its own frame), "gains" ([stiffness, damping] per segment, N m/rad
and N m s/rad)}]}.

Each body is its segments as rigid links, a free root and a ball joint at every other SOMA joint frame. Newton's eval_ik
turns the clip's segment frames into joint angles (exact for ball joints), which drive MuJoCo position actuators on the
ball joints, their damping the joints' own (SolverMuJoCo, Euler, on MuJoCo's CPU backend: it repeats bit for bit, and
MuJoCo Warp's deterministic mode breaks a body over 60 dofs, #60). The CPU backend runs MuJoCo's own collision (mj_step;
Newton's contact pipeline is the GPU path's only), and MuJoCo meets a mesh as its convex hull: a walker on a slope's
mesh stood on the hull's chord 18 cm over the drawn ground (2026-10-27). So each body's ground is a MuJoCo heightfield
sampled every CELL from its triangles, in its own collision group, so each body meets its own copy and no other body
(each person set apart in the world: apart_of); every shape's contact gap is 0 (Newton's default 0.1 m becomes MuJoCo's
geom gap, which with no margin let a box fall through a heightfield and held a foot 20 cm over it, 2026-10-27). A spot's
ground is where a body can stand there: the lowest surface over its triangles with HEADROOM free over it (a lintel over
a door leaves the floor; a step's closed box and a table are stood on, as blocks). The ground push is MuJoCo's solved
contact forces (mj_contactForce). The root has no actuator: its height is free, so the body's weight rests on its ground
through contact; a helper force and torque (OpenSim's residuals) hold its horizontal path and its turn to the clip's,
recorded every frame. Heights over the ground are measured on the drawn triangles, not the heightfield, so the
sampling's own error shows in them.

out.json: {"engine", "rate", "people": {name: {"frames": [{"angles": [[x, y, z] degrees, rotation vector, per ball
joint], "targets": [...the clip's...], "torques": [[x, y, z] N m per ball joint], "ground": [x, y, z] N (the ground's
push on the body, the frame's substeps' mean), "lowest": m (the lowest collider corner's height over the ground, null
off it), "feet": {segment: [its lowest corner's height over the ground (null off it), the ground's upward push on it
N]} (FEET), "helper": [force xyz N, torque xyz N m], "poses": [[x, y, z, qx, qy, qz, qw] per segment]}]}}}
"""
import json
import pathlib
import sys

import mujoco
import newton
import numpy as np
import warp as wp
from scipy.spatial.transform import Rotation

SUBSTEPS = 16
DEVICE = "cpu"  # the CPU backend steps one world held on the CPU
# The root helper per kilogram of body: horizontal stiffness (N/m) and damping (N s/m), turn stiffness (N m/rad) and
# damping (N m s/rad). Stiff enough to hold the clip's path, soft against the contacts that carry the weight.
HELPER = (40.0, 12.0, 40.0, 6.0)
# The gap left under the lowest collider at the start (metres): the body is let down onto its ground, never into it.
START_GAP = 0.002
# Free height over a surface for a body to stand on it (metres): under less (a table top, a shelf) it is a block.
HEADROOM = 1.0
# The heightfield's sample spacing (metres): a riser is a slope one cell deep.
CELL = 0.02
FEET = ("Foot", "ToeBase")
APART = 10.0  # metres between two people's grounds in the one world


def arguments():
    given = sys.argv[1:]
    if len(given) != 2:
        raise SystemExit(__doc__)
    return pathlib.Path(given[0]), pathlib.Path(given[1])


def transform(matrix):
    """A 4 x 4 as Newton's transform (position, quaternion xyzw)."""
    matrix = np.asarray(matrix, dtype=float)
    return wp.transform(wp.vec3(*matrix[:3, 3]), wp.quat(*Rotation.from_matrix(matrix[:3, :3]).as_quat()))


def matrix(pose):
    """A Newton pose (position, quaternion xyzw) as a 4 x 4."""
    found = np.eye(4)
    found[:3, :3], found[:3, 3] = Rotation.from_quat(pose[3:]).as_matrix(), pose[:3]
    return found


def corners(box):
    """The eight corners of a box [centre, half sizes] in its segment's frame."""
    centre, half = np.asarray(box[0]), np.asarray(box[1])
    signs = np.array([[x, y, z] for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)], dtype=float)
    return centre + signs * half


def crossings(points, ground):
    """Where the triangles cross the upright line through each point (x, z): (point index, height) pairs."""
    corner, edge1, edge2 = ground[:, 0], ground[:, 1] - ground[:, 0], ground[:, 2] - ground[:, 0]
    det = edge1[:, 0] * edge2[:, 2] - edge1[:, 2] * edge2[:, 0]
    flat = np.abs(det) > 1e-12  # an upright triangle crosses no upright line
    corner, edge1, edge2, det = corner[flat], edge1[flat], edge2[flat], det[flat]
    low, high = ground[flat][:, :, [0, 2]].min(axis=1), ground[flat][:, :, [0, 2]].max(axis=1)
    order = np.argsort(points[:, 0])
    firsts = np.searchsorted(points[order, 0], low[:, 0], side="left")
    lasts = np.searchsorted(points[order, 0], high[:, 0], side="right")
    found_points, found_heights = [], []
    for index in range(len(corner)):
        mine = order[firsts[index]:lasts[index]]
        mine = mine[(points[mine, 2] >= low[index, 1]) & (points[mine, 2] <= high[index, 1])]
        dx, dz = points[mine, 0] - corner[index, 0], points[mine, 2] - corner[index, 2]
        one = (dx * edge2[index, 2] - dz * edge2[index, 0]) / det[index]
        two = (edge1[index, 0] * dz - edge1[index, 2] * dx) / det[index]
        inside = (one >= 0) & (two >= 0) & (one + two <= 1)
        found_points.append(mine[inside])
        found_heights.append(corner[index, 1] + one[inside] * edge1[index, 1] + two[inside] * edge2[index, 1])
    return np.concatenate(found_points), np.concatenate(found_heights)


def standing(points, ground):
    """Each point's ground height: the lowest crossing with HEADROOM free over it (nan where none is)."""
    which, heights = crossings(points, ground)
    order = np.lexsort((heights, which))
    which, heights = which[order], heights[order]
    above = np.append(heights[1:], np.inf)
    above[np.append(which[1:] != which[:-1], True)] = np.inf  # the top crossing of each point has nothing over it
    free = above - heights >= HEADROOM
    found = np.full(len(points), np.nan)
    which, heights = which[free], heights[free]
    first = np.unique(which, return_index=True)[1]  # the lowest standing crossing of each point
    found[which[first]] = heights[first]
    return found


def heights_over(points, ground):
    """Each point's height over its ground; nan where it has none."""
    return points[:, 1] - standing(points, ground)


def heightfield(ground):
    """The ground as a Newton heightfield and its transform in the body's frame (Y up): its standing heights sampled
    every CELL over the triangles' span; a spot with none is a hole, set a metre under the lowest."""
    low, high = ground[:, :, [0, 2]].reshape(-1, 2).min(axis=0), ground[:, :, [0, 2]].reshape(-1, 2).max(axis=0)
    columns, rows = (np.floor((high - low) / CELL + 1e-9).astype(int) + 1)
    xs, zs = low[0] + np.arange(columns) * CELL, low[1] + np.arange(rows) * CELL
    # MuJoCo's rows run along the field's own y from -half to +half; turned to Y up, its y is the body's -z.
    grid_x, grid_z = np.meshgrid(xs, zs[::-1])
    heights = standing(np.stack([grid_x.ravel(), np.zeros(grid_x.size), grid_z.ravel()], axis=1), ground)
    heights = np.where(np.isnan(heights), np.nanmin(heights) - 1.0, heights).reshape(rows, columns)
    half = (xs[-1] - xs[0]) / 2, (zs[-1] - zs[0]) / 2
    field = newton.Heightfield(data=heights.astype(np.float32), nrow=rows, ncol=columns, hx=half[0], hy=half[1])
    turn = wp.quat(*Rotation.from_euler("x", -90, degrees=True).as_quat())
    return field, wp.transform(wp.vec3(xs[0] + half[0], 0.0, zs[0] + half[1]), turn)


def lowest(segments, worlds, ground):
    """The lowest collider corner's height over the ground, the segments posed at `worlds` (segments x 4 x 4); None
    when no corner is over any of it."""
    heights = heights_over(np.concatenate([corners(segment["box"]) @ world[:3, :3].T + world[:3, 3]
                                           for segment, world in zip(segments, worlds)]), ground)
    return None if np.isnan(heights).all() else float(np.nanmin(heights))


def rounded(value):
    return None if value is None else round(value, 5)


def add_person(builder, person, start, ground, group):
    """One person's sim body: its segments posed at `start`, its joints, gains and colliders, and its ground (a
    heightfield), which they meet and nothing else (their own collision group, every pair of the body filtered, set
    apart: one world holds every body, the CPU backend runs one world)."""
    links, joints, shapes = [], [], []
    shape = newton.ModelBuilder.ShapeConfig(collision_group=group, mu=0.9, gap=0.0)
    for index, segment in enumerate(person["segments"]):
        link = builder.add_link(xform=transform(start[index]), com=wp.vec3(*segment["com"]),
                                inertia=wp.mat33(*np.ravel(segment["inertia"])), mass=segment["mass"],
                                label=f"{person['name']}/{segment['name']}", lock_inertia=True)
        centre, half = segment["box"]
        shapes.append(builder.add_shape_box(link, xform=wp.transform(wp.vec3(*centre), wp.quat_identity()), hx=half[0],
                              hy=half[1], hz=half[2], cfg=shape))
        if segment["parent"] < 0:
            joints.append(builder.add_joint_free(link, label=f"{person['name']}/{segment['name']}"))
        else:
            stiffness, damping = person["gains"][index]
            # The drive's damping is the joint's own: MuJoCo's Euler integrates joint damping implicitly, an
            # actuator's velocity gain explicitly (that blew a 76 kg body up within 10 ms at 2 ms steps).
            joints.append(builder.add_joint_ball(
                links[segment["parent"]], link, parent_xform=transform(segment["local"]),
                child_xform=wp.transform_identity(), armature=0.01, damping=damping,
                label=f"{person['name']}/{segment['name']}", actuator_mode=newton.JointTargetMode.POSITION))
            first = builder.joint_qd_start[joints[-1]]
            for dof in range(first, first + 3):
                builder.joint_target_ke[dof] = stiffness
                builder.joint_target_kd[dof] = 0.0
        links.append(link)
    builder.add_articulation(joints, label=person["name"])
    field, placed = heightfield(ground)
    builder.add_shape_heightfield(xform=placed, heightfield=field, label=f"{person['name']}/ground",
                                  cfg=shape)
    for index, one in enumerate(shapes):
        for other in shapes[index + 1:]:
            builder.add_shape_collision_filter_pair(one, other)
    return links, joints


def apart_of(number, grounds):
    """Where person `number` is set in the one world, along x (its own frame moved by it): each person's ground is
    a static shape on MuJoCo's world body, which Newton's collision groups cannot keep from the other bodies (MuJoCo's
    excludes are by body pair), so the people stand APART beyond each other's grounds' reach."""
    reach = max(float(np.abs(ground[:, :, [0, 2]]).max()) for ground in grounds) * 2 + APART
    return np.array([number * reach, 0.0, 0.0])


class Scene:
    """Every person's body in Newton: the model, its states, the solver."""

    def __init__(self, job, targets, grounds):
        builder = newton.ModelBuilder(up_axis=newton.Axis.Y, gravity=(0.0, -job["gravity"], 0.0))
        newton.solvers.SolverMuJoCo.register_custom_attributes(builder)
        self.people = []
        for number, (person, worlds, ground) in enumerate(zip(job["people"], targets, grounds)):
            apart = apart_of(number, grounds)
            worlds, ground = np.array(worlds), ground + apart
            worlds[:, :, :3, 3] += apart
            links, joints = add_person(builder, person, worlds[0], ground, number + 1)
            feet = [index for index, segment in enumerate(person["segments"]) if segment["name"].endswith(FEET)]
            self.people.append({"links": links, "joints": joints, "person": person, "worlds": worlds,
                                "ground": ground, "feet": feet, "apart": apart})
        # MuJoCo's own CPU backend, not MuJoCo Warp: newton 1.7.0 with mujoco-warp 3.15.0 in deterministic mode turns
        # every body over 60 dofs to NaN within 15 ms (#60; this body has 72), and the CPU backend repeats bit for bit.
        self.model = builder.finalize(device=DEVICE)
        self.solver = newton.solvers.SolverMuJoCo(self.model, use_mujoco_cpu=True, use_mujoco_contacts=False,
                                                  integrator="euler")
        self.observables = self.solver.observables(kinds={self.solver.ObservableKind.QFRC_ACTUATOR})
        self.now, self.next = self.model.state(), self.model.state()
        self.to_newton = self.solver.mjc_body_to_newton.numpy()[0]
        self.control = self.model.control()
        self.q_start = self.model.joint_q_start.numpy()
        self.qd_start = self.model.joint_qd_start.numpy()
        newton.eval_fk(self.model, self.model.joint_q, self.model.joint_qd, self.now)

    def angles_of(self, worlds_now):
        """The joint coordinates whose bodies stand at `worlds_now` (one array of segments x 4 x 4 per person):
        Newton's eval_ik, the analytic per-joint split (exact for ball joints)."""
        poses = np.zeros((self.model.body_count, 7), dtype=np.float32)
        for entry, worlds in zip(self.people, worlds_now):
            for link, world in zip(entry["links"], worlds):
                poses[link, :3] = world[:3, 3]
                poses[link, 3:] = Rotation.from_matrix(world[:3, :3]).as_quat()
        scratch = self.model.state()
        scratch.body_q.assign(poses)
        joint_q = wp.zeros_like(self.model.joint_q)
        joint_qd = wp.zeros_like(self.model.joint_qd)
        newton.eval_ik(self.model, scratch, joint_q, joint_qd)
        return joint_q.numpy()

    def posed(self, joint_q):
        """The state at `joint_q`, still; each person's segments' world frames (segments x 4 x 4)."""
        self.now.joint_q.assign(joint_q)
        self.now.joint_qd.zero_()
        newton.eval_fk(self.model, self.now.joint_q, self.now.joint_qd, self.now)
        body_q = self.now.body_q.numpy()
        return [np.array([matrix(body_q[link]) for link in entry["links"]]) for entry in self.people]

    def started(self):
        """Every body at its clip's first frame, let down so its lowest collider stands START_GAP over its ground
        (measured on the body itself: SOMA's bind bones are not the clip's lengths) over its ground, still."""
        joint_q = self.angles_of([entry["worlds"][0] for entry in self.people])
        for entry, worlds in zip(self.people, self.posed(joint_q)):
            over = lowest(entry["person"]["segments"], worlds, entry["ground"])
            if over is None:
                raise SystemExit(f"{entry['person']['name']}: no ground under its first frame's body")
            joint_q[self.q_start[entry["joints"][0]] + 1] += START_GAP - over
        self.posed(joint_q)
        self.control.joint_target_q.assign(joint_q)

    def helpers(self, frame):
        """Each person's root helper now: a force holding its horizontal path and a torque holding its turn to the
        clip's at `frame` ({person index: (force, torque)}), written into the root's body force."""
        body_q, body_qd = self.now.body_q.numpy(), self.now.body_qd.numpy()
        forces = np.zeros((self.model.body_count, 6), dtype=np.float32)
        found = {}
        for number, entry in enumerate(self.people):
            root, target = entry["links"][0], entry["worlds"][frame % len(entry["worlds"])][0]
            mass = sum(segment["mass"] for segment in entry["person"]["segments"])
            pushed, pushed_damping, turned, turned_damping = (gain * mass for gain in HELPER)
            force = pushed * (target[:3, 3] - body_q[root, :3]) - pushed_damping * body_qd[root, :3]
            force[1] = 0.0
            error = Rotation.from_matrix(target[:3, :3]) * Rotation.from_quat(body_q[root, 3:]).inv()
            torque = turned * error.as_rotvec() - turned_damping * body_qd[root, 3:]
            forces[root] = [*force, *torque]
            found[number] = (force, torque)
        self.now.body_f.assign(forces)
        return found

    def pushes(self):
        """Each segment's push from its ground now (N, world, by Newton body): the contact forces MuJoCo solved this
        step (mj_contactForce, the force on geom2 along the contact frame), the ground's on each segment."""
        model, data = self.solver.mj_model, self.solver.mj_data
        found, wrench = np.zeros((self.model.body_count, 3)), np.zeros(6)
        for index in range(data.ncon):
            contact = data.contact[index]
            mujoco.mj_contactForce(model, data, index, wrench)
            force = contact.frame.reshape(3, 3).T @ wrench[:3]
            one, other = model.geom_bodyid[contact.geom1], model.geom_bodyid[contact.geom2]
            body, sign = (other, 1.0) if one == 0 else (one, -1.0)
            found[int(self.to_newton[body])] += sign * force
        return found

    def frame(self, frame, rate):
        """Step to `frame`: the clip's angles there as targets, SUBSTEPS steps; each person's ground push (the
        substeps' mean, N, by segment) and root helper (the substeps' mean)."""
        targets = self.angles_of([entry["worlds"][frame % len(entry["worlds"])] for entry in self.people])
        self.control.joint_target_q.assign(targets)
        step = 1.0 / (rate * SUBSTEPS)
        ground = np.zeros((self.model.body_count, 3))
        helper = np.zeros((len(self.people), 6))
        for _ in range(SUBSTEPS):
            self.now.clear_forces()
            for number, (force, torque) in self.helpers(frame).items():
                helper[number] += np.concatenate([force, torque]) / SUBSTEPS
            self.solver.step(self.now, self.next, self.control, None, step, observables=self.observables)
            self.now, self.next = self.next, self.now
            ground += self.pushes() / SUBSTEPS
        return targets, ground, helper

    def measured(self, targets, ground, helper):
        """Each person's measures now: its ball joints' angles and the clip's (rotation vectors, degrees), their
        torques (N m), the ground push, the lowest collider corner and each foot's over the ground with its push, the
        root helper and every segment's pose."""
        joint_q = self.now.joint_q.numpy()
        torques = self.observables.qfrc_actuator.numpy()
        body_q = self.now.body_q.numpy()
        found = []
        for number, entry in enumerate(self.people):
            balls = entry["joints"][1:]
            angles = [Rotation.from_quat(joint_q[self.q_start[joint]:self.q_start[joint] + 4]).as_rotvec(degrees=True)
                      for joint in balls]
            wanted = [Rotation.from_quat(targets[self.q_start[joint]:self.q_start[joint] + 4]).as_rotvec(degrees=True)
                      for joint in balls]
            worlds = [matrix(body_q[link]) for link in entry["links"]]
            poses = [np.concatenate([body_q[link][:3] - entry["apart"], body_q[link][3:]]) for link in entry["links"]]
            found.append({"angles": np.round(angles, 3).tolist(), "targets": np.round(wanted, 3).tolist(),
                          "torques": np.round([torques[self.qd_start[joint]:self.qd_start[joint] + 3]
                                               for joint in balls], 3).tolist(),
                          "ground": np.round(ground[entry["links"]].sum(axis=0), 3).tolist(),
                          "lowest": rounded(lowest(entry["person"]["segments"], worlds, entry["ground"])),
                          "feet": {entry["person"]["segments"][foot]["name"]: [
                              rounded(lowest([entry["person"]["segments"][foot]], [worlds[foot]], entry["ground"])),
                              round(float(ground[entry["links"][foot], 1]), 3)] for foot in entry["feet"]},
                          "helper": np.round(helper[number], 3).tolist(),
                          "poses": np.round(poses, 5).tolist()})
        return found


def run(job_path, out_path):
    job = json.loads(job_path.read_text())
    targets = [np.load(person["targets"])["world"] for person in job["people"]]
    scene = Scene(job, targets, [np.load(person["targets"])["ground"] for person in job["people"]])
    scene.started()
    frames = max(len(worlds) for worlds in targets)
    people = {person["name"]: {"frames": []} for person in job["people"]}
    first = scene.measured(scene.angles_of([entry["worlds"][0] for entry in scene.people]),
                           np.zeros((scene.model.body_count, 3)), np.zeros((len(people), 6)))
    for person, measures in zip(job["people"], first):
        people[person["name"]]["frames"].append(measures)
    for frame in range(1, frames):
        measures = scene.measured(*scene.frame(frame, job["rate"]))
        for person, entry in zip(job["people"], measures):
            if frame < len(targets[job["people"].index(person)]):
                people[person["name"]]["frames"].append(entry)
    out_path.write_text(json.dumps({"engine": f"newton {newton.__version__} SolverMuJoCo, "
                                              "MuJoCo's CPU backend", "rate": job["rate"],
                                    "people": people}))


if __name__ == "__main__":
    run(*arguments())
