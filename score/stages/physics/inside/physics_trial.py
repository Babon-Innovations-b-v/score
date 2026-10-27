"""Runs in the trial's own Python (newton_env.sh: Newton with its MuJoCo solver; on a rented card or this PC): run a
place's physics trial from the stage's own UsdPhysics (experimental, F11; the layers are tools/usd/physics.py's).

    <env>/bin/python score/stages/physics/inside/physics_trial.py <stage.usda> <out.json>

Newton reads the composed stage as written (`add_usd`: Y up, metres, the scene's pull, each rigid body's MassAPI mass,
its convex hull guide and its physics material, the revolute joints with their limits and DriveAPI, the fixed joints,
every other colliding mesh as static triangles) and steps it with MuJoCo's solver on Newton's own contacts
(`SolverMuJoCo(use_mujoco_contacts=False)`: MuJoCo's own treat a hollow static as convex). What the importer leaves to
its caller is read with pxr here and driven every substep: each kinematic hand where its time samples move it, and
each drive's torque cap at its frame (a time-sampled maxForce; nothing outside its window).

Measured every frame: each body's motion from its start (4 x 4, column vectors, the stage's frame), its lowest point,
its speed, its kinetic energy (moving and turning, the body's own inertia) and its height's energy, each revolute
joint's angle (degrees, as UsdPhysics measures it), and whether anything drives the trial (a hand moves, a motor is
on). At the start and the end: the statics each body lies inside (its drawn triangles crossing theirs after raising
it NUDGE).

out.json: {"rate", "frames", "gravity", "bodies": {name: {"path", "mass", "friction", "restitution", "motions": [...],
"lowest": [...], "speed": [...]}}, "energy": [...], "driven": [...], "hinges": {leaf: {"frame", "lower",
"upper", "angles": [...]}}, "joined": [[name, name], ...], "inside at start": {name: [...]}, "inside at end": {...},
"statics": n, "engine": "..."}
"""
import json
import math
import pathlib
import sys

import fcl
import newton
import numpy as np
import warp as wp
from pxr import Gf, Usd, UsdGeom, UsdPhysics, UsdShade

SUBSTEPS = 20
# Raised this far (metres), a body that only touches what it stands on is not inside it (the resting triage's nudge).
NUDGE = 0.005
NOT_SOLID = ("Sky",)


def arguments():
    given = sys.argv[1:]
    if len(given) != 2:
        raise SystemExit(__doc__)
    return pathlib.Path(given[0]), pathlib.Path(given[1])


def colliding(prim):
    return prim.HasAPI(UsdPhysics.CollisionAPI) and UsdPhysics.CollisionAPI(prim).GetCollisionEnabledAttr().Get() \
        is not False


def material_of(mesh):
    """The physics material bound to a mesh: its dynamic friction and restitution."""
    bound = UsdShade.MaterialBindingAPI(mesh).ComputeBoundMaterial("physics")[0]
    if not bound:
        raise RuntimeError(f"{mesh.GetPath()}: no physics material bound")
    api = UsdPhysics.MaterialAPI(bound.GetPrim())
    return api.GetDynamicFrictionAttr().Get(), api.GetRestitutionAttr().Get()


def hulls_of(prim):
    """The body's colliding convex hulls; a moving body here collides by them only."""
    found = [child for child in prim.GetChildren() if colliding(child)
             and UsdPhysics.MeshCollisionAPI(child).GetApproximationAttr().Get() == "convexHull"]
    if not found or any(colliding(child) for child in prim.GetChildren() if child not in found):
        raise RuntimeError(f"{prim.GetPath()}: a moving body here collides by its convex hull only")
    return found


def triangles(mesh):
    """A mesh's points in the world (the stage's start) and its faces as triangles (fans)."""
    geometry = UsdGeom.Mesh(mesh)
    matrix = np.asarray(UsdGeom.Xformable(mesh).ComputeLocalToWorldTransform(Usd.TimeCode.Default()))
    points = np.asarray(geometry.GetPointsAttr().Get(), dtype=float)
    points = points @ matrix[:3, :3] + matrix[3, :3]
    indices, faces, at = list(geometry.GetFaceVertexIndicesAttr().Get()), [], 0
    for count in geometry.GetFaceVertexCountsAttr().Get():
        faces += [(indices[at], indices[at + corner], indices[at + corner + 1]) for corner in range(1, count - 1)]
        at += count
    return points, np.asarray(faces, dtype=np.int64)


def drive_of(joint, frames):
    """A revolute joint's angular drive: its torque cap at each frame (a time-sampled maxForce)."""
    if not joint.HasAPI(UsdPhysics.DriveAPI, "angular"):
        return None
    force = UsdPhysics.DriveAPI(joint, "angular").GetMaxForceAttr()
    return [float(force.Get(code)) for code in range(frames)]


def read_physics(stage):
    """What the composed stage says about its physics that the trial measures or drives, by prim path."""
    rate = stage.GetTimeCodesPerSecond()
    scene = next(prim for prim in stage.Traverse() if prim.IsA(UsdPhysics.Scene))
    pull = UsdPhysics.Scene(scene).GetGravityMagnitudeAttr().Get()
    frames = int(round(scene.GetAttribute("score:physics:seconds").Get() * rate)) + 1
    bodies, hands, joints = {}, {}, []
    for prim in stage.Traverse():
        if prim.HasAPI(UsdPhysics.RigidBodyAPI):
            if UsdPhysics.RigidBodyAPI(prim).GetKinematicEnabledAttr().Get():
                hand = UsdGeom.Xformable(prim)
                hands[str(prim.GetPath())] = [hand.ComputeLocalToWorldTransform(code) for code in range(frames)]
                continue
            hulls_of(prim)
            drawn = next(child for child in prim.GetChildren() if child.IsA(UsdGeom.Mesh) and child.GetName() == "geo")
            friction, restitution = material_of(drawn)
            bodies[str(prim.GetPath())] = {"name": prim.GetName(), "mass": UsdPhysics.MassAPI(prim).GetMassAttr().Get(),
                                           "friction": friction, "restitution": restitution,
                                           "drawn": triangles(drawn)}
        elif prim.IsA(UsdPhysics.RevoluteJoint) or prim.IsA(UsdPhysics.FixedJoint):
            revolute = prim.IsA(UsdPhysics.RevoluteJoint)
            joint = UsdPhysics.RevoluteJoint(prim) if revolute else UsdPhysics.FixedJoint(prim)
            joints.append({"path": str(prim.GetPath()), "revolute": revolute,
                           "bodies": [str(rel.GetTargets()[0]) for rel in (joint.GetBody0Rel(), joint.GetBody1Rel())],
                           "limits": [joint.GetLowerLimitAttr().Get(), joint.GetUpperLimitAttr().Get()] if revolute
                           else None,
                           "drive": drive_of(prim, frames) if revolute else None})
    owned = tuple(path + "/" for path in bodies)
    statics = {str(prim.GetPath()): triangles(prim) for prim in stage.Traverse()
               if prim.IsA(UsdGeom.Mesh) and colliding(prim) and UsdGeom.Imageable(prim).ComputePurpose() != "guide"
               and not str(prim.GetPath()).startswith(owned)
               and not any(part in NOT_SOLID for part in prim.GetPath().pathString.split("/"))}
    return {"rate": rate, "pull": pull, "frames": frames, "bodies": bodies, "hands": hands, "joints": joints,
            "statics": statics}


def matrix_of(pose):
    """A Newton transform (p, q xyzw) as a 4 x 4 matrix acting on column vectors."""
    x, y, z, w = pose[3:]
    rotation = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                         [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                         [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
    found = np.eye(4)
    found[:3, :3], found[:3, 3] = rotation, pose[:3]
    return found


def pose_of(matrix):
    """A pxr world matrix (row vectors, maybe scaled) as a Newton transform (p, q xyzw)."""
    turned = Gf.Matrix4d(matrix).RemoveScaleShear().ExtractRotationQuat()
    return [*matrix.ExtractTranslation(), *turned.GetImaginary(), turned.GetReal()]


def bvh(points, faces):
    model = fcl.BVHModel()
    model.beginModel(len(points), len(faces))
    model.addSubModel(points, faces)
    model.endModel()
    return model


def boxes_meet(one, other):
    return bool(np.all(one.min(axis=0) <= other.max(axis=0)) and np.all(other.min(axis=0) <= one.max(axis=0)))


def inside(physics, placed):
    """{body: [statics it lies inside]}: its drawn triangles, where `placed` puts them and raised NUDGE, crossing a
    static's."""
    found = {}
    for path, body in physics["bodies"].items():
        points = placed[path] + np.array([0.0, NUDGE, 0.0])
        mine = fcl.CollisionObject(bvh(points, body["drawn"][1]))
        found[body["name"]] = [
            other for other, (others, faces) in physics["statics"].items() if boxes_meet(points, others) and
            fcl.collide(mine, fcl.CollisionObject(bvh(others, faces)), fcl.CollisionRequest(), fcl.CollisionResult())]
    return found


class Trial:
    """The stage in Newton: its model, two states, the solver on Newton's contacts, and what the caller drives."""

    def __init__(self, stage_path, physics):
        builder = newton.ModelBuilder(up_axis=newton.Axis.Y)
        built = builder.add_usd(str(stage_path))
        self.body_index = {path: built["path_body_map"][path] for path in physics["bodies"]}
        self.hand_index = {path: built["path_body_map"][path] for path in physics["hands"]}
        joint_index = built["path_joint_map"]
        self.drives = [(builder.joint_qd_start[joint_index[joint["path"]]], joint["drive"])
                       for joint in physics["joints"] if joint["drive"]]
        self.angles = {joint["path"]: builder.joint_q_start[joint_index[joint["path"]]]
                       for joint in physics["joints"] if joint["revolute"]}
        self.hand_joints = {path: next(joint for joint, child in enumerate(builder.joint_child) if child == index)
                            for path, index in self.hand_index.items()}
        self.model = builder.finalize(device=wp.get_preferred_device())
        self.hand_starts = {path: (int(self.model.joint_q_start.numpy()[joint]),
                                   int(self.model.joint_qd_start.numpy()[joint]))
                            for path, joint in self.hand_joints.items()}
        self.solver = newton.solvers.SolverMuJoCo(self.model, use_mujoco_contacts=False, integrator="euler")
        self.now, self.next = self.model.state(), self.model.state()
        self.control = self.model.control()
        self.pipeline = newton.CollisionPipeline(self.model, deterministic=True)
        self.contacts = self.pipeline.contacts()
        newton.eval_fk(self.model, self.model.joint_q, self.model.joint_qd, self.now)
        self.caps = None

    def cap(self, code):
        """Each drive's torque cap at frame `code` (told to the solver only when it changes)."""
        caps = [torques[code] for _, torques in self.drives]
        if caps == self.caps:
            return
        limits = self.model.joint_effort_limit.numpy()
        for (dof, _), torque in zip(self.drives, caps):
            limits[dof] = torque
        self.model.joint_effort_limit.assign(limits)
        self.solver.notify_model_changed(newton.ModelFlags.JOINT_DOF_PROPERTIES)
        self.caps = caps

    def hold_hands(self, hands, code, share, rate):
        """Each kinematic hand between its frames' poses, `share` of the way into frame `code`, moving at their
        difference."""
        if not hands:
            return
        joint_q, joint_qd = self.now.joint_q.numpy(), self.now.joint_qd.numpy()
        for path, poses in hands.items():
            before, after = np.asarray(poses[code - 1][:3]), np.asarray(poses[code][:3])
            q_at, qd_at = self.hand_starts[path]
            joint_q[q_at:q_at + 7] = [*(before + (after - before) * share), *poses[code][3:]]
            joint_qd[qd_at:qd_at + 6] = [*((after - before) * rate), 0.0, 0.0, 0.0]
        self.now.joint_q.assign(joint_q)
        self.now.joint_qd.assign(joint_qd)
        newton.eval_fk(self.model, self.now.joint_q, self.now.joint_qd, self.now,
                       body_flag_filter=newton.BodyFlags.KINEMATIC)

    def frame(self, hands, code, rate):
        """Step from frame code - 1 to frame code."""
        self.cap(code)
        step = 1.0 / (rate * SUBSTEPS)
        for sub in range(SUBSTEPS):
            self.hold_hands(hands, code, (sub + 1) / SUBSTEPS, rate)
            self.now.clear_forces()
            self.pipeline.collide(self.now, self.contacts)
            self.solver.step(self.now, self.next, self.control, self.contacts, step)
            self.now, self.next = self.next, self.now

    def poses(self):
        """{body path: 4 x 4 world pose} now."""
        found = self.now.body_q.numpy()
        return {path: matrix_of(found[index]) for path, index in self.body_index.items()}


def turn_of(rotation):
    """The angular change of a rotation matrix (radians times its axis)."""
    angle = math.acos(max(-1.0, min(1.0, (np.trace(rotation) - 1) / 2)))
    if angle < 1e-9:
        return np.zeros(3)
    axis = np.array([rotation[2, 1] - rotation[1, 2], rotation[0, 2] - rotation[2, 0], rotation[1, 0] - rotation[0, 1]])
    return axis / (2 * math.sin(angle)) * angle


def run(stage_path, out):
    """Step the trial frame by frame and measure it."""
    stage = Usd.Stage.Open(str(stage_path))
    physics = read_physics(stage)
    trial = Trial(stage_path, physics)
    rate, pull, frames = physics["rate"], physics["pull"], physics["frames"]
    hands = {path: [pose_of(matrix) for matrix in at] for path, at in physics["hands"].items()}
    masses, coms = trial.model.body_mass.numpy(), trial.model.body_com.numpy()
    inertias = trial.model.body_inertia.numpy()
    starts = trial.poses()
    locals_ = {path: (body["drawn"][0] - starts[path][:3, 3]) @ starts[path][:3, :3] for path, body in
               physics["bodies"].items()}
    found = {body["name"]: {key: body[key] for key in ("mass", "friction", "restitution")} | {
        "path": path, "motions": [], "lowest": [], "speed": []} for path, body in physics["bodies"].items()}
    angles = {path: [] for path in trial.angles}
    energies, driven, before = [], [], dict(starts)
    for code in range(frames):
        if code:
            trial.frame(hands, code, rate)
        now, total = trial.poses(), 0.0
        for path, pose in now.items():
            index, entry = trial.body_index[path], found[physics["bodies"][path]["name"]]
            middle, earlier = pose[:3, :3] @ coms[index] + pose[:3, 3], before[path][:3, :3] @ coms[index] + \
                before[path][:3, 3]
            speed = float(np.linalg.norm(middle - earlier)) * rate
            spin = pose[:3, :3].T @ turn_of(pose[:3, :3] @ before[path][:3, :3].T) * rate
            total += 0.5 * masses[index] * speed ** 2 + 0.5 * float(spin @ inertias[index] @ spin) \
                + masses[index] * pull * middle[1]
            entry["motions"].append((pose @ np.linalg.inv(starts[path])).tolist())
            entry["lowest"].append(round(float((locals_[path] @ pose[:3, :3].T + pose[:3, 3])[:, 1].min()), 5))
            entry["speed"].append(round(speed, 5))
            before[path] = pose
        joint_q = trial.now.joint_q.numpy()
        for path, at in trial.angles.items():
            angles[path].append(round(math.degrees(float(joint_q[at])), 4))
        energies.append(round(total, 5))
        driven.append(any(code > 0 and poses[code][:3] != poses[code - 1][:3] for poses in hands.values())
                      or any(torques[code] > 0 for _, torques in trial.drives))
    ended = trial.poses()
    names = {path: body["name"] for path, body in physics["bodies"].items()}
    result = {"rate": rate, "frames": frames, "gravity": pull, "statics": len(physics["statics"]), "bodies": found,
              "energy": energies, "driven": driven,
              "hinges": {names[joint["bodies"][1]]: {"frame": joint["bodies"][0], "lower": joint["limits"][0],
                                                     "upper": joint["limits"][1], "angles": angles[joint["path"]]}
                         for joint in physics["joints"] if joint["revolute"]},
              "joined": [[names.get(path, path) for path in joint["bodies"]] for joint in physics["joints"]],
              "inside at start": inside(physics, {path: body["drawn"][0] for path, body in physics["bodies"].items()}),
              "inside at end": inside(physics, {path: locals_[path] @ ended[path][:3, :3].T + ended[path][:3, 3]
                                                for path in physics["bodies"]}),
              "engine": f"newton {newton.__version__} SolverMuJoCo on Newton's contacts, {wp.get_preferred_device()}"}
    out.write_text(json.dumps(result))
    print("physics_trial: wrote", out)


if __name__ == "__main__":
    run(*arguments())
