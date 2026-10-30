"""Runs in the physics trial's own Python (score/stages/physics/inside/newton_env.sh: Newton with its MuJoCo solver; on
a rented card or this PC): let a place's loose objects come to rest on its ground, as real objects do.

    <env>/bin/python score/stages/settling/inside/settle_drop.py <stage.usda> <job.json> <out.json>

job.json: {"loose": [object name, ...], "lift": {object name: metres}, "ignore": [object name, ...], "start": {object
name: 4 x 4}, "under": {object name: [object name, ...]}} (ignore: glowing parts and what lies on a loose object, left
out of the statics; start: the motion, stage frame, row by row, that stands an object upright before its drop,
tools/usd/settle.py's upright_starts; under: the loose objects it is stacked on, which it meets as it meets a static: a
crate on a crate). Beside the stage, PARTS_FILE (when the settle stage wrote one, tools/usd/convex_parts.py): {object
name: [[corner, ...], ...]}, a hollow object's convex parts in its drawn mesh's own frame.

The stage is read with pxr as composed. Its ground (the mesh `Ground`, else a made ground's fine patch `near`, else a
plane at y = 0 in a room, which has none) and every other drawn mesh within NEAR of a loose object are static
triangles, but the sky (NOT_SOLID) and what the job leaves out. Each loose object is lifted by its `lift`, weighs 1 at
the middle of its surface (the resting check's weight) with its box's inertia, and collides by its convex hull; a hollow
object (a crate, a tray, a bin, a shelf: one with parts) by its convex parts instead, all on the one body, so what is
stacked in it meets its floor, not its hull's top. Loose objects collide with the ground and the statics, not with each
other but what they are stacked on (a convex hull spans a hollow: one hull section lying on a panel rested on its hull
while the drawn hull stood 4 cm clear, 2026-10-08). One that starts inside a static (a layout fault) would be thrown out
of it, so it collides with the ground alone and is reported. Newton steps it with MuJoCo's solver on Newton's own
contacts (sorted), SECONDS under gravity (or until everything has been still QUIET_SECONDS) with each body's
speed damped every frame (DAMPING_LINEAR, DAMPING_ANGULAR), so nothing bounces off or keeps rolling; each object's last
pose is taken. Two loose objects whose
drawn triangles cross at rest are reported (`overlaps`).

out.json: {"objects": {object name: {"motion": 4 x 4, "moving": metres a second at the end, "inside": [static objects
it starts in]}}, "overlaps": [[name, name], ...], "engine": "..."}; the motion is how the object moved from as laid to
at rest, in the stage's own frame (y up), row by row (column vectors): its settled matrix is motion @ its laid matrix.
"""
import json
import math
import pathlib
import sys

import fcl
import newton
import numpy as np
import warp as wp
from pxr import Usd, UsdGeom
from scipy.spatial import ConvexHull

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "physics/inside"))
from physics_trial import boxes_meet, bvh, matrix_of, triangles  # noqa: E402

FPS = 30
SECONDS = 30
# A drop ends early once every body has moved slower than this (metres a second) and turned slower (radians a second)
# for QUIET_SECONDS on end: what is left of SECONDS changes no rest, only the card's minutes.
QUIET = (0.005, 0.02)
QUIET_SECONDS = 2
SUBSTEPS = 20
GRAVITY = 9.81  # the pose an object rests in does not depend on g; the Moon's 1.62 only takes longer to get there
FRICTION = 0.9
# The share of each body's speed (moving, turning) taken off a second: its fall slowed, its roll stopped (Bullet's.)
DAMPING_LINEAR = 0.6
DAMPING_ANGULAR = 0.95
MASS = 1.0
# Each shape's skin (metres): two resting on each other stand two skins apart, so their drawn triangles do not touch
# (with none, a box stacked on a crate read as at rest inside it).
MARGIN = 0.004
# Room for this many contacts a loose shape (each convex part of a body is one; Newton reduces each pair's to a few),
# and the solver's rows a contact (an elliptic cone: 3). Sized by Newton from the ground's triangles, the solver asked
# for 3.4 billion (toy, 2026-10-27); sized by bodies (64 a body), bodies of 50 to 157 parts overflowed it
# (settle@garage, settle@airlock, 2026-10-29). Measured on this PC's card at 16 a shape: the garage's 13 bodies of 809
# shapes peaked at 1,411 contacts, the airlock's 29 sandbag-heavy bodies of 2,733 at 13,474 (4.9 a shape), 13 and 20 s.
# The cone is elliptic: on MuJoCo's default pyramid every box on the toy's 5.7 degree slope spun 7 degrees about its up
# as it landed. The solve is not Warp's deterministic mode: over 32 dofs (6 loose bodies) MuJoCo Warp's sparse
# Jacobian sizes its sorted records past 2^31 (19 billion for 20 bodies, the patched mujoco-warp too), a dense one
# stops at 60 dofs, and its sparse inertia solve is wrong over 60 dofs in a tree (#60). Newton's contacts are sorted.
CONTACTS = 16
ROWS = 3
# Beside the stage: its hollow objects' convex parts (tools/usd/convex_parts.py's FILE).
PARTS_FILE = "convex-parts.json"
# What a stage draws that nothing stands on or against: its sky (the haze round the place, the stars, the moon's and
# the halo's squares) and what lies outside it (the far ground), which would otherwise enclose every object.
NOT_SOLID = {"Sky", "Outside"}
GROUND_NAMES = ("Ground", "near")
# How far a loose object is raised, or moved from a static's middle, for the test of whether it starts inside it
# (metres): what it only touches, the deck under it or a wall beside it, is not "inside" (the resting triage's nudge).
NUDGE = 0.005
# How far past a loose object's bounds a static is kept (metres): statics past every loose object's reach are left out.
NEAR = 3.0


def arguments():
    given = sys.argv[1:]
    if len(given) != 3:
        raise SystemExit(__doc__)
    return pathlib.Path(given[0]), json.loads(pathlib.Path(given[1]).read_text()), pathlib.Path(given[2])


def drawn(stage):
    """{holder path: [its drawn meshes]}: every prim holding meshes (guides and proxies aside), as the scene lays it."""
    found = {}
    for prim in stage.Traverse(Usd.TraverseInstanceProxies()):
        if prim.IsA(UsdGeom.Mesh) and UsdGeom.Imageable(prim).ComputePurpose() in ("default", "render"):
            found.setdefault(str(prim.GetParent().GetPath()), []).append(prim)
    return found


def ground_mesh(stage):
    """The ground's mesh prim (GROUND_NAMES in order), None in a room."""
    meshes = [prim for prim in stage.Traverse() if prim.IsA(UsdGeom.Mesh)]
    return next((prim for name in GROUND_NAMES for prim in meshes if prim.GetName() == name), None)


def left_out(path, ignore):
    """Whether a holder, or a holder it lies under, is sky or one the job leaves out of the statics."""
    names = path.strip("/").split("/")
    return any(name in NOT_SOLID or name in ignore for name in names)


def surface_middle(points, faces):
    """The middle of a mesh's surface (its triangles weighed by their area): where its weight is."""
    corners = points[faces]
    areas = np.linalg.norm(np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0]), axis=1)
    return (corners.mean(axis=1) * areas[:, None]).sum(axis=0) / max(areas.sum(), 1e-12)


def box_inertia(points, mesh):
    """The inertia (stage frame, about the middle) of a body of MASS whose box in its own frame bounds `points`."""
    laid = np.asarray(UsdGeom.Xformable(mesh).ComputeLocalToWorldTransform(Usd.TimeCode.Default())).T[:3, :3]
    turn = laid / np.linalg.norm(laid, axis=0)
    size = np.ptp(points @ turn, axis=0)
    own = np.diag([size[1] ** 2 + size[2] ** 2, size[0] ** 2 + size[2] ** 2, size[0] ** 2 + size[1] ** 2]) * MASS / 12
    return turn @ own @ turn.T


def hull(points):
    """A convex hull of points as a Newton mesh."""
    return newton.Mesh(points, ConvexHull(points).simplices.reshape(-1), compute_inertia=False)


def parts_of(mesh, corners):
    """A hollow object's convex parts (corners in its drawn mesh's own frame) in the stage's frame."""
    matrix = np.asarray(UsdGeom.Xformable(mesh).ComputeLocalToWorldTransform(Usd.TimeCode.Default()))
    return [np.asarray(part, dtype=float) @ matrix[:3, :3] + matrix[3, :3] for part in corners]


def inside_statics(mine, statics):
    """The statics an object (its drawn triangles as laid) starts inside: an overlap that survives raising it NUDGE (the
    deck it stands on does not count) and moving it NUDGE away from the static's middle (a wall it stands against does
    not count), with a static reaching below its middle (a thing standing on it does not count either), as the resting
    triage's overlap survives its nudge."""
    points, faces = mine
    middle = (points[:, 1].min() + points[:, 1].max()) / 2
    found = []
    for name, (others, other_faces) in statics.items():
        if others[:, 1].min() >= middle or not boxes_meet(points, others):
            continue
        way = (points.min(axis=0) + points.max(axis=0)) / 2 - (others.min(axis=0) + others.max(axis=0)) / 2
        away = way / np.linalg.norm(way) * NUDGE if np.linalg.norm(way) > 1e-9 else np.array([0.0, NUDGE, 0.0])
        if all(crossing((points + shift, faces), (others, other_faces)) for shift in ([0.0, NUDGE, 0.0], away)):
            found.append(name)
    return found


def crossing(one, other):
    """Whether two triangle sets cross."""
    return boxes_meet(one[0], other[0]) and fcl.collide(fcl.CollisionObject(bvh(*one)),
                                                        fcl.CollisionObject(bvh(*other)),
                                                        fcl.CollisionRequest(), fcl.CollisionResult()) > 0


def stack_groups(names, under):
    """{name: its collision group}: one of its own, shared with what it is stacked on (and what that is on)."""
    group = {name: name for name in names}

    def root(name):
        while group[name] != name:
            name = group[name]
        return name

    for name, supports in under.items():
        for support in supports:
            if name in group and support in group:
                group[root(name)] = root(support)
    roots = sorted({root(name) for name in names})
    return {name: 1 + roots.index(root(name)) for name in names}


@wp.kernel
def damped(speeds: wp.array(dtype=float), kept: wp.array(dtype=float)):
    """Each speed times its kept share."""
    index = wp.tid()
    speeds[index] = speeds[index] * kept[index]


class Drop:
    """The place in Newton: the statics, the loose bodies, the solver on Newton's contacts."""

    def __init__(self, stage, stage_path, job):
        holders = drawn(stage)
        place = stage.GetDefaultPrim().GetName()
        loose = {name: f"/{place}/Objects/{name}" for name in job["loose"] if f"/{place}/Objects/{name}" in holders}
        ignore = set(job.get("ignore", []))
        self.meshes = {}
        for name, path in loose.items():
            if len(holders[path]) != 1:
                raise RuntimeError(f"{name}: {len(holders[path])} drawn meshes, expected one")
            self.meshes[name] = triangles(holders[path][0])
        reach = [np.array([points.min(axis=0) - NEAR, points.max(axis=0) + NEAR]) for points, _ in self.meshes.values()]
        ground = ground_mesh(stage)
        self.statics = {}
        for path, meshes in holders.items():
            if path in loose.values() or left_out(path, ignore):
                continue
            for mesh in meshes:
                if ground is not None and mesh.GetPath() == ground.GetPath():
                    continue
                points, faces = triangles(mesh)
                if len(faces) and any(boxes_meet(points, box) for box in reach):
                    self.statics[path if len(meshes) == 1 else str(mesh.GetPath())] = (points, faces)
        self.inside = {name: inside_statics(self.meshes[name], self.statics) for name in loose}
        parts = json.loads((stage_path.parent / PARTS_FILE).read_text()) if (stage_path.parent / PARTS_FILE).exists() \
            else {}
        builder = newton.ModelBuilder(up_axis=newton.Axis.Y, gravity=(0.0, -GRAVITY, 0.0))
        statics = {"mu": FRICTION, "restitution": 0.0, "density": 0.0, "margin": MARGIN, "collision_group": -1}
        if ground is None:
            builder.add_ground_plane(cfg=newton.ModelBuilder.ShapeConfig(**statics))
        else:
            points, faces = triangles(ground)
            builder.add_shape_mesh(-1, mesh=newton.Mesh(points, faces.reshape(-1), compute_inertia=False),
                                   cfg=newton.ModelBuilder.ShapeConfig(**statics))
        static_shapes = [builder.add_shape_mesh(-1, mesh=newton.Mesh(points, faces.reshape(-1),
                                                                     compute_inertia=False),
                                                cfg=newton.ModelBuilder.ShapeConfig(**statics))
                         for points, faces in self.statics.values()]
        groups = stack_groups(sorted(loose), {name: supports for name, supports in job.get("under", {}).items()
                                              if not self.inside.get(name)})
        self.bodies, self.middles, shapes = {}, {}, 0
        for number, name in enumerate(sorted(loose)):
            points, faces = self.meshes[name]
            middle = surface_middle(points, faces)
            start = np.eye(4)
            start[:3, 3] = middle
            start = np.asarray(job.get("start", {}).get(name, np.eye(4))) @ start
            start[1, 3] += float(job["lift"].get(name, 0.0))
            turn = wp.quat_from_matrix(wp.mat33(*start[:3, :3].reshape(-1)))
            body = builder.add_body(xform=wp.transform(wp.vec3(*start[:3, 3]), turn), mass=MASS,
                                    inertia=wp.mat33(*box_inertia(points, holders[loose[name]][0]).reshape(-1)),
                                    lock_inertia=True, label=name)
            group = len(loose) + 1 + number if self.inside[name] else groups[name]
            cfg = newton.ModelBuilder.ShapeConfig(mu=FRICTION, restitution=0.0, density=0.0, margin=MARGIN,
                                                  collision_group=group)
            pieces = parts_of(holders[loose[name]][0], parts[name]) if parts.get(name) else [points]
            for piece in pieces:
                shape = builder.add_shape_convex_hull(body, mesh=hull(piece - middle), cfg=cfg)
                for other in static_shapes if self.inside[name] else ():
                    builder.add_shape_collision_filter_pair(shape, other)
            self.bodies[name], self.middles[name] = body, middle
            shapes += len(pieces)
        if not self.bodies:  # nothing loose: MuJoCo refuses a model with no joint (assembly@docking_airlock, 2026-10-30)
            return
        self.model = builder.finalize(device=wp.get_preferred_device())
        self.room = CONTACTS * shapes
        self.solver = newton.solvers.SolverMuJoCo(
            self.model, use_mujoco_contacts=False, integrator="euler", cone="elliptic", nconmax=self.room,
            njmax=self.room * ROWS)
        self.now, self.next = self.model.state(), self.model.state()
        self.control = self.model.control()
        self.pipeline = newton.CollisionPipeline(self.model, deterministic=True, rigid_contact_max=self.room)
        self.contacts = self.pipeline.contacts()
        newton.eval_fk(self.model, self.model.joint_q, self.model.joint_qd, self.now)
        damping = np.array([DAMPING_LINEAR] * 3 + [DAMPING_ANGULAR] * 3)
        self.kept = wp.array(np.tile((1.0 - damping) ** (1.0 / FPS), len(self.bodies)), dtype=float,
                             device=self.model.device)
        self.graph, self.stepped = None, False

    def frame(self):
        """Step one frame; on a card from the second on as one captured graph (kernel launches cost more than the
        kernels; the first frame, uncaptured, makes what the steps allocate)."""
        if self.graph is None and self.model.device.is_cuda and self.stepped:
            with wp.ScopedCapture() as capture:  # records the frame without stepping it
                self.steps()
            self.graph = capture.graph
        if self.graph is not None:
            wp.capture_launch(self.graph)
        else:
            self.steps()
        self.stepped = True
        if int(self.contacts.rigid_contact_count.numpy()[0]) >= self.room:
            raise RuntimeError(f"the drop met {self.room} contacts, all it has room for: raise CONTACTS")

    def steps(self):
        """SUBSTEPS (an even count: the states end where they began), then every body's speed damped a frame's share."""
        step = 1.0 / (FPS * SUBSTEPS)
        for _ in range(SUBSTEPS):
            self.now.clear_forces()
            self.pipeline.collide(self.now, self.contacts)
            self.solver.step(self.now, self.next, self.control, self.contacts, step)
            self.now, self.next = self.next, self.now
        wp.launch(damped, dim=len(self.kept), inputs=[self.now.joint_qd, self.kept], device=self.model.device)

    def poses(self):
        """{name: 4 x 4 world pose of its body} now."""
        found = self.now.body_q.numpy()
        return {name: matrix_of(found[body]) for name, body in self.bodies.items()}


def overlaps(meshes, motions):
    """Pairs of loose objects whose drawn triangles cross at rest."""
    placed = {name: (points @ motions[name][:3, :3].T + motions[name][:3, 3], faces)
              for name, (points, faces) in meshes.items()}
    names = sorted(placed)
    return [[first, second] for index, first in enumerate(names) for second in names[index + 1:]
            if crossing(placed[first], placed[second])]


def stepped(drop):
    """Step the drop SECONDS, or until every body has been QUIET for QUIET_SECONDS: (each body's pose at the end,
    its speed over the last frame, metres a second)."""
    before, quiet = drop.poses(), 0
    for frame in range(FPS * SECONDS):
        drop.frame()
        now = drop.poses()
        speeds = {name: float(np.linalg.norm(now[name][:3, 3] - before[name][:3, 3])) * FPS for name in now}
        turns = {name: math.acos(min(1.0, max(-1.0, (np.trace(now[name][:3, :3] @ before[name][:3, :3].T) - 1) / 2)))
                 * FPS for name in now}
        quiet = quiet + 1 if max(speeds.values()) < QUIET[0] and max(turns.values()) < QUIET[1] else 0
        before = now
        if quiet >= QUIET_SECONDS * FPS:
            print(f"settle_drop: all still for {QUIET_SECONDS} s after {(frame + 1) / FPS:.1f} s")
            break
    return before, speeds


def main():
    stage_path, job, out = arguments()
    stage = Usd.Stage.Open(str(stage_path))
    drop = Drop(stage, stage_path, job)
    found, motions = {}, {}
    if drop.bodies:
        ended, speeds = stepped(drop)
        for name, pose in ended.items():
            laid = np.eye(4)
            laid[:3, 3] = drop.middles[name]
            motions[name] = pose @ np.linalg.inv(laid)
            found[name] = {"motion": motions[name].tolist(), "inside": drop.inside[name], "moving": speeds[name]}
    out.write_text(json.dumps({"objects": found, "overlaps": overlaps(drop.meshes, motions),
                               "engine": f"newton {newton.__version__} SolverMuJoCo on Newton's contacts, "
                                         f"{wp.get_preferred_device()}"}, indent=1))
    print("settle_drop: wrote", out)


if __name__ == "__main__":
    main()
