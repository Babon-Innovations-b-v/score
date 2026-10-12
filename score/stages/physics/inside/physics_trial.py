"""Runs inside Blender (`blender -b`, a cloud machine): run a place's physics trial on Blender's Bullet from the
stage's own UsdPhysics (experimental, F11; the layers are tools/usd/physics.py's).

    blender -b --python score/stages/physics/inside/physics_trial.py -- <stage.usda> <out.json>

The stage's geometry comes in through Blender's USD reader; its physics is read with pxr off the composed stage,
since Blender's reader takes no UsdPhysics: the scene's pull and seconds, each rigid body (its mass, its physics
material's dynamic friction and restitution, its convex hull when the hull collides), each kinematic hand and where
its time samples move it, each revolute joint (a Bullet hinge about the joint's axis within its limits) and fixed
joint, and every other mesh whose collision is on, as static triangles. Bullet multiplies two bodies' frictions and
restitutions, so each takes the square root of its material's: two of one material meet at the material's own.

Measured every frame: each body's motion from its start (4 x 4, column vectors, the stage's frame), its lowest point,
its speed, its kinetic energy (moving and turning, the turn's inertia a solid box of its bounds) and its height's
energy, each hinge's angle about its axis, and whether anything drives the trial (a hand moves, a motor is on). At
the end: each body's speed and the statics it lies inside (an overlap that survives raising it NUDGE), and the same at
the start.

out.json: {"rate", "frames", "gravity", "bodies": {name: {"mass", "friction", "restitution", "motions": [...],
"lowest": [...], "speed": [...]}}, "energy": [...], "driven": [...], "hinges": {leaf: {"frame", "lower",
"upper", "angles": [...]}}, "joined": [[name, name], ...], "inside at start": {name: [...]}, "inside at end": {...},
"statics": n}
"""
import json
import math
import pathlib
import sys

import bpy
import numpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

SUBSTEPS = 20
ITERATIONS = 40
MARGIN = 0.004
LINEAR_DAMPING = 0.04
ANGULAR_DAMPING = 0.1
# Raised this far (metres), a body that only touches what it stands on is not inside it (the resting triage's nudge).
NUDGE = 0.005
# How far past a body's reach a static still takes part (metres).
NEAR = 1.0
NOT_SOLID = ("Sky",)
# The stage's y-up frame onto Blender's z-up and back, as Blender's importer turns a y-up stage.
Y_UP_TO_Z_UP = Matrix(((1, 0, 0, 0), (0, 0, -1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))
# A joint's axis (its frame's X, Y or Z) onto the Z a Bullet hinge turns about.
AXIS_TO_Z = {"X": Matrix.Rotation(math.pi / 2, 4, "Y"), "Y": Matrix.Rotation(-math.pi / 2, 4, "X"),
             "Z": Matrix.Identity(4)}


def arguments():
    given = sys.argv[sys.argv.index("--") + 1:]
    if len(given) != 2:
        raise SystemExit(__doc__)
    return pathlib.Path(given[0]), pathlib.Path(given[1])


def import_stage(stage):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    result = bpy.ops.wm.usd_import(filepath=str(stage), import_guide=False, import_proxy=False,
                                   import_textures_mode="IMPORT_NONE", property_import_mode="ALL",
                                   import_lights=False, create_world_material=False, merge_parent_xform=False)
    if "FINISHED" not in result:
        raise RuntimeError(f"Blender did not import {stage}: {result}")
    bpy.context.view_layer.update()  # the importer's turn onto z up reaches the children's world matrices here


def to_blender(matrix):
    """A pxr matrix (row vectors, the stage's frame) as a Blender world matrix (column vectors, z up)."""
    return Y_UP_TO_Z_UP @ Matrix([list(row) for row in matrix]).transposed()


def to_stage(matrix):
    """A Blender motion (z up) as the same motion in the stage's frame (y up), row by row."""
    return [list(row) for row in Y_UP_TO_Z_UP.inverted() @ matrix @ Y_UP_TO_Z_UP]


def colliding(prim):
    from pxr import UsdPhysics
    return prim.HasAPI(UsdPhysics.CollisionAPI) and UsdPhysics.CollisionAPI(prim).GetCollisionEnabledAttr().Get() \
        is not False


def material_of(mesh):
    """The physics material bound to a drawn mesh: its dynamic friction and restitution."""
    from pxr import UsdPhysics, UsdShade
    bound = UsdShade.MaterialBindingAPI(mesh).ComputeBoundMaterial("physics")[0]
    if not bound:
        raise RuntimeError(f"{mesh.GetPath()}: no physics material bound")
    api = UsdPhysics.MaterialAPI(bound.GetPrim())
    return api.GetDynamicFrictionAttr().Get(), api.GetRestitutionAttr().Get()


def hull_collides(prim):
    """Whether the body collides by a convex hull (an enabled collision guide with that approximation)."""
    from pxr import UsdPhysics
    return any(colliding(child) and UsdPhysics.MeshCollisionAPI(child).GetApproximationAttr().Get() == "convexHull"
               for child in prim.GetChildren())


def joint_world(joint, index):
    """A joint's frame in the world as pxr gives it (row vectors): its body's world times its local frame."""
    from pxr import Gf, UsdGeom
    body = joint.GetPrim().GetStage().GetPrimAtPath(getattr(joint, f"GetBody{index}Rel")().GetTargets()[0])
    local = Gf.Matrix4d().SetRotate(Gf.Quatd(getattr(joint, f"GetLocalRot{index}Attr")().Get()))
    local.SetTranslateOnly(Gf.Vec3d(getattr(joint, f"GetLocalPos{index}Attr")().Get()))
    return local * UsdGeom.Xformable(body).ComputeLocalToWorldTransform(0)


def drive_of(joint, frames):
    """A revolute joint's angular drive: its target speed (degrees a second) and its torque cap at each frame."""
    from pxr import UsdPhysics
    if not joint.HasAPI(UsdPhysics.DriveAPI, "angular"):
        return None
    drive = UsdPhysics.DriveAPI(joint, "angular")
    return {"speed": drive.GetTargetVelocityAttr().Get(),
            "torque": [drive.GetMaxForceAttr().Get(code) for code in range(frames)]}


def read_physics(stage_path):
    """What the composed stage says about its physics, by prim path."""
    from pxr import Usd, UsdGeom, UsdPhysics
    stage = Usd.Stage.Open(str(stage_path))
    rate = stage.GetTimeCodesPerSecond()
    scene = next(prim for prim in stage.Traverse() if prim.IsA(UsdPhysics.Scene))
    pull = UsdPhysics.Scene(scene).GetGravityMagnitudeAttr().Get()
    seconds = scene.GetAttribute("score:physics:seconds").Get()
    frames = int(round(seconds * rate)) + 1
    bodies, hands, joints = {}, {}, []
    for prim in stage.Traverse():
        if prim.HasAPI(UsdPhysics.RigidBodyAPI):
            body = UsdPhysics.RigidBodyAPI(prim)
            if body.GetKinematicEnabledAttr().Get():
                cube = UsdGeom.Xformable(prim)
                hands[prim.GetName()] = {
                    "path": str(prim.GetPath()),
                    "at": [[list(row) for row in cube.ComputeLocalToWorldTransform(code)] for code in range(frames)]}
                continue
            if not hull_collides(prim):
                raise RuntimeError(f"{prim.GetPath()}: a moving body here collides by its convex hull only")
            friction, restitution = material_of(next(child for child in prim.GetChildren()
                                                     if child.IsA(UsdGeom.Mesh) and child.GetName() == "geo"))
            placed = UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(0)
            bodies[prim.GetName()] = {"path": str(prim.GetPath()), "mass": UsdPhysics.MassAPI(prim).GetMassAttr().Get(),
                                      "friction": friction, "restitution": restitution,
                                      "world": [list(row) for row in placed]}
        elif prim.IsA(UsdPhysics.RevoluteJoint) or prim.IsA(UsdPhysics.FixedJoint):
            revolute = prim.IsA(UsdPhysics.RevoluteJoint)
            joint = UsdPhysics.RevoluteJoint(prim) if revolute else UsdPhysics.FixedJoint(prim)
            joints.append({"name": prim.GetName(), "revolute": revolute,
                           "bodies": [str(rel.GetTargets()[0]) for rel in (joint.GetBody0Rel(), joint.GetBody1Rel())],
                           "world": [list(row) for row in joint_world(joint, 0)],
                           "axis": joint.GetAxisAttr().Get() if revolute else None,
                           "limits": [joint.GetLowerLimitAttr().Get(), joint.GetUpperLimitAttr().Get()] if revolute
                           else None,
                           "drive": drive_of(prim, frames) if revolute else None})
    statics = {str(prim.GetPath()): material_of(prim) for prim in stage.Traverse()
               if prim.IsA(UsdGeom.Mesh) and colliding(prim) and UsdGeom.Imageable(prim).ComputePurpose() != "guide"
               and not any(part in NOT_SOLID for part in prim.GetPath().pathString.split("/"))}
    return {"rate": rate, "pull": pull, "frames": frames, "bodies": bodies, "hands": hands, "joints": joints,
            "statics": statics}


def chain(item):
    """An imported object's names from its root down, Blender's .001 suffixes taken off: its prim path's tail."""
    names = []
    while item is not None:
        names.append(item.name.split(".")[0])
        item = item.parent
    return "/" + "/".join(reversed(names))


def by_prim(paths, items):
    """{prim path: Blender object} for the paths, each matched by the object's name chain ending the path."""
    found = {}
    for item in items:
        tail = chain(item)
        for path in paths:
            if path.endswith(tail):
                found[path] = item
    return found


def holder_of(path):
    """The object a drawn mesh belongs to: the prim holding its `geo` (a joint names the object)."""
    return path.rsplit("/", 1)[0] if path.endswith("/geo") else path


def turned_up(holders, physics, body_paths):
    """Blender's reader turns a y-up stage onto z up in some versions and not in others (5.0.1 left a stage with no
    root object as it was): turn every root object here when a body does not stand where its stage puts it."""
    path, holder = next(iter(holders.items()))
    wanted = to_blender(physics["bodies"][body_paths[path]]["world"]).translation
    if (holder.matrix_world.translation - wanted).length < 1e-3:
        return
    for item in [item for item in bpy.data.objects if item.parent is None]:
        item.matrix_world = Y_UP_TO_Z_UP @ item.matrix_world
    bpy.context.view_layer.update()
    if (holder.matrix_world.translation - wanted).length > 1e-3:
        raise RuntimeError(f"{path} stands at {tuple(holder.matrix_world.translation)}, its stage puts it at "
                           f"{tuple(wanted)}")


def unparented(item):
    placed = item.matrix_world.copy()
    item.parent = None
    item.matrix_world = placed
    return item


def weight_at_middle(item):
    """The object's origin moved to the middle of its surface (Blender takes the origin as the centre of mass)."""
    bpy.ops.object.select_all(action="DESELECT")
    item.select_set(True)
    bpy.context.view_layer.objects.active = item
    bpy.ops.object.origin_set(type="ORIGIN_CENTER_OF_MASS", center="MEDIAN")


def rigid(item, kind, shape, friction, restitution):
    bpy.context.view_layer.objects.active = item
    bpy.ops.rigidbody.object_add(type=kind)
    body = item.rigid_body
    body.collision_shape = shape
    body.friction = math.sqrt(friction)
    body.restitution = math.sqrt(restitution)
    body.use_margin = True
    body.collision_margin = MARGIN
    return body


def world_box(item, margin=0.0):
    corners = [item.matrix_world @ Vector(corner) for corner in item.bound_box]
    return (Vector([min(corner[axis] for corner in corners) - margin for axis in range(3)]),
            Vector([max(corner[axis] for corner in corners) + margin for axis in range(3)]))


def boxes_meet(one, other):
    return all(one[0][axis] <= other[1][axis] and other[0][axis] <= one[1][axis] for axis in range(3))


def tree(item, shift=Vector()):
    placed = Matrix.Translation(shift) @ item.matrix_world
    return BVHTree.FromPolygons([placed @ vertex.co for vertex in item.data.vertices],
                                [polygon.vertices[:] for polygon in item.data.polygons])


def inside(moving, statics):
    """{body: [statics it lies inside]}: an overlap that survives raising the body NUDGE."""
    trees = {path: tree(item) for path, item in statics.items()}
    return {name: [path for path, other in trees.items() if tree(item, Vector((0, 0, NUDGE))).overlap(other)]
            for name, item in moving.items()}


def make_hand(name, hand):
    """A kinematic box of the hand's size, keyed at each frame where the stage's time samples move it."""
    turned = [to_blender(matrix) for matrix in hand["at"]]
    half = Vector(turned[0].to_scale()) / 2
    corners = [(x * half.x, y * half.y, z * half.z) for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(corners, [], [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)])
    item = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(item)
    for frame, matrix in enumerate(turned, start=1):
        item.location = matrix.translation
        item.keyframe_insert("location", frame=frame)
    item.location = turned[0].translation
    body = rigid(item, "PASSIVE", "BOX", 1.0, 0.0)
    body.kinematic = True
    return item


def joint_empty(joint, objects):
    """The joint as a Bullet constraint on an empty at its frame (a hinge turning about the joint's axis)."""
    empty = bpy.data.objects.new(joint["name"], None)
    bpy.context.scene.collection.objects.link(empty)
    turn = AXIS_TO_Z[joint["axis"]] if joint["revolute"] else Matrix.Identity(4)
    empty.matrix_world = to_blender(joint["world"]) @ turn
    bpy.context.view_layer.objects.active = empty
    bpy.ops.rigidbody.constraint_add(type="HINGE" if joint["revolute"] else "FIXED")
    constraint = empty.rigid_body_constraint
    # Bullet's hinge turns its first object against its second: the joint's body1 against its body0, as UsdPhysics
    # measures a revolute joint's angle (checked on the toy place: the other order opened the leaf the wrong way).
    constraint.object1, constraint.object2 = (objects[path] for path in reversed(joint["bodies"]))
    constraint.disable_collisions = True
    if joint["revolute"]:
        constraint.use_limit_ang_z = True
        constraint.limit_ang_z_lower, constraint.limit_ang_z_upper = (math.radians(limit) for limit in joint["limits"])
    if joint.get("drive"):
        motor(joint, empty, constraint)
    return empty


def motor(joint, hinge, held):
    """The hinge's drive as a Bullet motor on the same pair, turning about the hinge's axis (a motor turns about its
    own x), switched on at the frames its torque cap is above nothing."""
    empty = bpy.data.objects.new(f"{joint['name']}_drive", None)
    bpy.context.scene.collection.objects.link(empty)
    empty.matrix_world = hinge.matrix_world @ Matrix.Rotation(-math.pi / 2, 4, "Y")
    bpy.context.view_layer.objects.active = empty
    bpy.ops.rigidbody.constraint_add(type="MOTOR")
    constraint = empty.rigid_body_constraint
    constraint.object1, constraint.object2 = held.object1, held.object2
    constraint.disable_collisions = True
    constraint.use_motor_ang = True
    constraint.motor_ang_target_velocity = math.radians(joint["drive"]["speed"])
    for frame, torque in enumerate(joint["drive"]["torque"], start=1):
        constraint.motor_ang_max_impulse = max(torque, 0.0)
        constraint.enabled = torque > 0
        constraint.keyframe_insert("motor_ang_max_impulse", frame=frame)
        constraint.keyframe_insert("enabled", frame=frame)


def vertices(item):
    found = numpy.empty(len(item.data.vertices) * 3)
    item.data.vertices.foreach_get("co", found)
    return found.reshape(-1, 3)


def turn_angle(matrix):
    """The angle (degrees) a rotation turns about Blender's z, the stage's y."""
    return math.degrees(math.atan2(matrix[1][0], matrix[0][0]))


def box_inertia(mass, local):
    """A solid box's principal inertia over the body's own bounds."""
    size = local.max(axis=0) - local.min(axis=0)
    return mass / 12 * numpy.array([size[1] ** 2 + size[2] ** 2, size[0] ** 2 + size[2] ** 2,
                                    size[0] ** 2 + size[1] ** 2])


def energy(body, item, local, inertia, before, rate, pull):
    """The body's kinetic energy (moving and turning) and its height's, between the frame before and this one."""
    now = item.matrix_world.copy()
    speed = (now.translation - before.translation).length * rate
    turned = (now.to_3x3() @ before.to_3x3().transposed()).to_quaternion()
    spin = turned.axis * turned.angle * rate
    own = numpy.array(now.to_3x3().transposed() @ spin)
    moving = 0.5 * body["mass"] * speed ** 2 + 0.5 * float(inertia @ own ** 2)
    return speed, moving + body["mass"] * pull * now.translation.z


def set_world(scene, rate, frames, pull):
    if scene.rigidbody_world is None:
        bpy.ops.rigidbody.world_add()
    simulation = scene.rigidbody_world
    simulation.substeps_per_frame = SUBSTEPS
    simulation.solver_iterations = ITERATIONS
    simulation.point_cache.frame_start = 1
    simulation.point_cache.frame_end = frames
    scene.frame_start, scene.frame_end = 1, frames
    scene.gravity = (0.0, 0.0, -pull)
    scene.render.fps = int(round(rate))


def reach(moving, hands):
    """Where anything moving can go: each body's bounds grown by its own size and NEAR, each hand's path."""
    boxes = []
    for item in moving.values():
        low, high = world_box(item)
        boxes.append(world_box(item, max(high - low) + NEAR))
    for hand in hands.values():
        for matrix in (hand["at"][0], hand["at"][-1]):
            spot = to_blender(matrix).translation
            boxes.append((spot - Vector((NEAR,) * 3), spot + Vector((NEAR,) * 3)))
    return boxes


def main():
    stage_path, out = arguments()
    physics = read_physics(stage_path)
    import_stage(stage_path)
    scene = bpy.context.scene
    set_world(scene, physics["rate"], physics["frames"], physics["pull"])
    meshes = [item for item in bpy.data.objects if item.type == "MESH"]
    body_paths = {body["path"]: name for name, body in physics["bodies"].items()}
    holders = by_prim(list(body_paths), [item for item in bpy.data.objects if item.type == "EMPTY"])
    if len(holders) != len(body_paths):
        raise RuntimeError(f"bodies not found among the imported objects: {sorted(set(body_paths) - set(holders))}")
    turned_up(holders, physics, body_paths)
    moving = {}
    for path, holder in holders.items():
        drawn = [child for child in holder.children if child.type == "MESH"]
        if len(drawn) != 1:
            raise RuntimeError(f"{path}: {len(drawn)} drawn meshes, expected one")
        moving[body_paths[path]] = unparented(drawn[0])
    joined_paths = {path for joint in physics["joints"] for path in joint["bodies"]}
    reachable = reach(moving, physics["hands"])
    statics = {}
    for path, item in by_prim(physics["statics"], [item for item in meshes if item not in moving.values()]).items():
        if holder_of(path) in joined_paths or any(boxes_meet(world_box(item), box) for box in reachable):
            statics[path] = unparented(item)
            rigid(item, "PASSIVE", "MESH", *physics["statics"][path])
    objects = {holder_of(path): item for path, item in statics.items()}
    for name, item in moving.items():
        body = physics["bodies"][name]
        weight_at_middle(item)
        rigid(item, "ACTIVE", "CONVEX_HULL", body["friction"], body["restitution"])
        item.rigid_body.mass = body["mass"]
        item.rigid_body.linear_damping = LINEAR_DAMPING
        item.rigid_body.angular_damping = ANGULAR_DAMPING
        objects[body["path"]] = item
    missing = sorted(joined_paths - set(objects))
    if missing:
        raise RuntimeError(f"joint bodies with no collider here: {missing}")
    for joint in physics["joints"]:
        joint_empty(joint, objects)
    for name, hand in physics["hands"].items():
        make_hand(name, hand)
    started = inside(moving, statics)
    run(scene, physics, moving, statics, started, out)


def run(scene, physics, moving, statics, started, out):
    """Step the simulation frame by frame and measure it."""
    rate, pull, frames = physics["rate"], physics["pull"], physics["frames"]
    locals_ = {name: vertices(item) for name, item in moving.items()}
    inertias = {name: box_inertia(physics["bodies"][name]["mass"], locals_[name]) for name in moving}
    hinges = {joint["bodies"][1]: joint for joint in physics["joints"] if joint["revolute"]}
    found = {name: {**physics["bodies"][name], "motions": [], "lowest": [], "speed": []} for name in moving}
    angles = {path: [] for path in hinges}
    energies, driven, starts, before = [], [], {}, {}
    hand_spots = {name: [tuple(hand["at"][code][3][:3]) for code in range(frames)]
                  for name, hand in physics["hands"].items()}
    torques = [joint["drive"]["torque"] for joint in physics["joints"] if joint.get("drive")]
    names = {body["path"]: name for name, body in physics["bodies"].items()}
    for frame in range(1, frames + 1):
        scene.frame_set(frame)
        total = 0.0
        for name, item in moving.items():
            now = item.matrix_world.copy()
            starts.setdefault(name, now)
            before.setdefault(name, now)
            placed = numpy.asarray(now)
            lowest = float((locals_[name] @ placed[:3, :3].T + placed[:3, 3])[:, 2].min())
            speed, held = energy(found[name], item, locals_[name], inertias[name], before[name], rate, pull)
            total += held
            entry = found[name]
            entry["motions"].append(to_stage(now @ starts[name].inverted()))
            entry["lowest"].append(round(lowest, 5))
            entry["speed"].append(round(speed, 5))
            before[name] = now
        for path in hinges:
            name = names[path]
            turned = moving[name].matrix_world.to_3x3() @ starts[name].to_3x3().transposed()
            angles[path].append(round(turn_angle(turned), 4))
        energies.append(round(total, 5))
        code = frame - 1
        driven.append(any(code > 0 and spots[code] != spots[code - 1] for spots in hand_spots.values())
                      or any(torque[code] > 0 for torque in torques))
    ended = inside(moving, statics)
    result = {"rate": rate, "frames": frames, "gravity": pull, "statics": len(statics), "bodies": found,
              "energy": energies, "driven": driven,
              "hinges": {names[path]: {"frame": joint["bodies"][0], "lower": joint["limits"][0],
                                       "upper": joint["limits"][1], "angles": angles[path]}
                         for path, joint in hinges.items()},
              "joined": [[names.get(path, path) for path in joint["bodies"]] for joint in physics["joints"]],
              "inside at start": started, "inside at end": ended}
    out.write_text(json.dumps(result))
    print("physics_trial: wrote", out)


main()
