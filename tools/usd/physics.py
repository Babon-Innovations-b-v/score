"""A place's physics as OpenUSD's own physics schema (UsdPhysics), and a trial that makes its objects react
(experimental, F11: the paper's "responsive"). Any reader of UsdPhysics (PhysX, Newton, Isaac) loads the layers;
the framework's own run is Newton's (score/stages/physics/inside/physics_trial.py), which reads them as written.

    .venv/bin/python tools/usd/physics.py <stage folder> <trial record> <materials>

writes, beside the place's other layers and held by its root just under the edit layer:

    layers/physics.usda   every drawn mesh of the place collides by its own triangles (the export's convex hull
                          guide is switched off for a static object); every object carries its mass (MassAPI: the
                          drawn surface's area times its material's sheet and density, props being hollow shells)
                          and its physics material (static and dynamic friction, restitution, density), bound for
                          the physics purpose; the scene's pull is the record's `gravity`
    layers/trial.usda     the trial: its bodies (RigidBodyAPI; colliding by the export's convex hull, their
                          triangles off), each drop lifted `over` metres above its target at its spot, each hinge a
                          RevoluteJoint about the vertical through its pins' middle (limits `opens`, degrees; the pins
                          are the joint, so they do not collide; the leaf hangs `clear` metres over the floor; a
                          `drive` {speed, torque, start, end} is its motor, a DriveAPI), what a leaf carries held to
                          it by a FixedJoint, and each push a kinematic box (an unseen hand, a guide) moved in a line
                          between its seconds

and, after the run, `write_motion` writes layers/physics_motion.usda: each body's transform at every frame of the run
as time samples, strongest of the root's layers, so any USD reader plays the trial back.

The trial record (score/stages/physics/design.py makes it from the scene's design) names the trial: `body`, `gravity`
(m/s², its body's in the environment concept's physics; a record without it is refused), `material`, `seconds`, `drops` ({object, onto (an object, or "floor":
y = 0; none: back onto where it stands), at [x, z] (none: its own spot), over}), `hinges` ({leaf, frame, pins, carries, opens, clear, drive}),
`pushes` ({name, size, from, to, start, end}) and `moved` (objects only a push moves). Its free check, `faults`,
refuses a trial whose bodies have no drawn mesh or whose drop falls onto anything but its target.
"""
import argparse
import json
import pathlib

import numpy as np
from pxr import Gf, Sdf, Usd, UsdGeom, UsdPhysics, UsdShade

import whole_layer


LAYERS = ("./layers/physics_motion.usda", "./layers/trial.usda", "./layers/physics.usda")
EDIT = "./layers/edit.usda"
NOT_SOLID = ("Sky",)
# A drop's fall is clear when nothing but its target stands inside its column, this much narrower than its footprint
# each way (metres): a neighbour it only grazes is not under it.
COLUMN_INSET = 0.02
# A hinge's motor follows its speed as closely as its torque allows: a velocity drive this stiff (newton metres a
# second a degree).
STIFF_DRIVE = 1e6


def bodies_of(record):
    """The trial's moving objects: what it drops, each hinge's leaf and what it carries, and what a push moves."""
    found = [drop["object"] for drop in record["drops"]]
    for hinge in record["hinges"]:
        found += [hinge["leaf"], *hinge["carries"]]
    return found + list(record.get("moved", []))


def opened(folder):
    """The place's composed stage from its folder (one root .usda)."""
    roots = [path for path in pathlib.Path(folder).glob("*.usda")]
    if len(roots) != 1:
        raise ValueError(f"{folder}: {len(roots)} root stages, expected one")
    return Usd.Stage.Open(str(roots[0])), roots[0]


def place_path(stage):
    return stage.GetDefaultPrim().GetPath()


def object_prim(stage, name):
    """A laid object's prim by its name, anywhere under the place's Objects (a child stands under its parent)."""
    found = [prim for prim in Usd.PrimRange(stage.GetDefaultPrim().GetChild("Objects")) if prim.GetName() == name]
    if len(found) != 1:
        raise ValueError(f"{len(found)} objects named {name}, expected one")
    return found[0]


def world(prim, time=Usd.TimeCode.Default()):
    return UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(time)


def world_box(prim):
    """The prim's world bounds as (low, high) numpy arrays."""
    found = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ["default", "render"]).ComputeWorldBound(prim)
    box = found.ComputeAlignedRange()
    return np.asarray(box.GetMin()), np.asarray(box.GetMax())


def mesh_area(mesh, matrix):
    """A mesh's surface area in world metres (its polygons fanned into triangles)."""
    points = np.asarray(mesh.GetPointsAttr().Get(), dtype=float)
    points = np.c_[points, np.ones(len(points))] @ np.asarray(matrix)
    counts = mesh.GetFaceVertexCountsAttr().Get()
    indices = np.asarray(mesh.GetFaceVertexIndicesAttr().Get())
    area, start = 0.0, 0
    for count in counts:
        face = points[indices[start:start + count], :3]
        start += count
        for corner in range(1, count - 1):
            area += np.linalg.norm(np.cross(face[corner] - face[0], face[corner + 1] - face[0])) / 2
    return area


def own_meshes(prim):
    """The meshes an object draws itself, not those of the objects standing on it (its child objects)."""
    return [UsdGeom.Mesh(child) for child in prim.GetChildren()
            if child.IsA(UsdGeom.Mesh) and UsdGeom.Imageable(child).ComputePurpose() != UsdGeom.Tokens.guide]


def hulls(prim):
    """The export's convex hull guides of an object."""
    return [child for child in prim.GetChildren() if child.IsA(UsdGeom.Mesh) and child.HasAPI(UsdPhysics.CollisionAPI)
            and UsdGeom.Imageable(child).ComputePurpose() == UsdGeom.Tokens.guide]


def laid_objects(stage):
    """Every laid object of the place: a prim under Objects that draws a mesh of its own."""
    return [prim for prim in Usd.PrimRange(stage.GetDefaultPrim().GetChild("Objects")) if own_meshes(prim)]


def write_materials(stage, materials):
    """One physics material prim a material, under /<place>/Physics."""
    for name, spec in materials.items():
        material = UsdShade.Material.Define(stage, place_path(stage).AppendPath(f"Physics/{name}"))
        api = UsdPhysics.MaterialAPI.Apply(material.GetPrim())
        api.CreateStaticFrictionAttr(spec["static"])
        api.CreateDynamicFrictionAttr(spec["dynamic"])
        api.CreateRestitutionAttr(spec["restitution"])
        api.CreateDensityAttr(spec["density"])


def write_scene(stage, record):
    scene = UsdPhysics.Scene.Define(stage, place_path(stage).AppendPath("Physics/Scene"))
    scene.CreateGravityDirectionAttr(Gf.Vec3f(0.0, -1.0, 0.0))
    if "gravity" not in record:
        raise SystemExit(f"physics: no physics for {record.get('body')}: the trial record names no gravity")
    scene.CreateGravityMagnitudeAttr(record["gravity"])
    scene.GetPrim().CreateAttribute("score:physics:seconds", Sdf.ValueTypeNames.Double).Set(record["seconds"])


def collide_by_triangles(stage, material):
    """Every drawn mesh of the place but its sky collides by its own triangles, its physics material bound; how
    many."""
    binding = UsdShade.Material(stage.GetPrimAtPath(place_path(stage).AppendPath(f"Physics/{material}")))
    count = 0
    for prim in stage.Traverse():
        if not prim.IsA(UsdGeom.Mesh) or any(part in NOT_SOLID for part in prim.GetPath().pathString.split("/")):
            continue
        if UsdGeom.Imageable(prim).ComputePurpose() == UsdGeom.Tokens.guide:
            continue
        UsdPhysics.CollisionAPI.Apply(prim)
        UsdPhysics.MeshCollisionAPI.Apply(prim).CreateApproximationAttr(UsdPhysics.Tokens.none)
        UsdShade.MaterialBindingAPI.Apply(prim).Bind(binding, UsdShade.Tokens.weakerThanDescendants, "physics")
        count += 1
    return count


def write_masses(stage, spec):
    """Each laid object's mass, its export hull switched off; {object: kg}."""
    found = {}
    for prim in laid_objects(stage):
        area = sum(mesh_area(mesh, mesh.ComputeLocalToWorldTransform(Usd.TimeCode.Default()))
                   for mesh in own_meshes(prim))
        mass = area * spec["sheet"] * spec["density"]
        UsdPhysics.MassAPI.Apply(prim).CreateMassAttr(mass)
        for hull in hulls(prim):
            UsdPhysics.CollisionAPI(hull).CreateCollisionEnabledAttr(False)
        found[prim.GetName()] = round(mass, 3)
    return found


def top_of(stage, onto):
    """The height a drop lands on: its target's top, or the floor's 0."""
    return 0.0 if onto == "floor" else float(world_box(object_prim(stage, onto))[1][1])


def landing(stage, drop):
    """The height a drop lands on: its target's top, or with no target the height its own lowest point stands at."""
    return top_of(stage, drop["onto"]) if "onto" in drop else float(world_box(object_prim(stage, drop["object"]))[0][1])


def spot_of(stage, drop):
    """[x, z] a drop falls at: its `at`, or its own middle where it stands."""
    if "at" in drop:
        return drop["at"]
    low, high = world_box(object_prim(stage, drop["object"]))
    return [float(low[0] + high[0]) / 2, float(low[2] + high[2]) / 2]


def moved(prim, shift):
    """The object moved by `shift` (metres, the stage's frame) in its own transform."""
    placed = world(prim) * Gf.Matrix4d().SetTranslate(shift)
    UsdGeom.Xformable(prim).MakeMatrixXform().Set(placed * world(prim.GetParent()).GetInverse())


def lifted(stage, drop):
    """The drop's object moved so its lowest point stands `over` its target's top with its middle at `at`."""
    prim = object_prim(stage, drop["object"])
    low, high = world_box(prim)
    middle, at = (low + high) / 2, spot_of(stage, drop)
    moved(prim, Gf.Vec3d(at[0] - middle[0], landing(stage, drop) + drop["over"] - low[1], at[1] - middle[2]))


def make_body(prim):
    """A trial body: a rigid body colliding by the export's hull, its own triangles off, the hull bound to the
    physics material of what it draws."""
    UsdPhysics.RigidBodyAPI.Apply(prim)
    drawn = own_meshes(prim)
    for mesh in drawn:
        UsdPhysics.CollisionAPI(mesh.GetPrim()).CreateCollisionEnabledAttr(False)
    material = UsdShade.MaterialBindingAPI(drawn[0].GetPrim()).ComputeBoundMaterial("physics")[0]
    for hull in hulls(prim):
        UsdPhysics.CollisionAPI(hull).CreateCollisionEnabledAttr(True)
        UsdShade.MaterialBindingAPI.Apply(hull).Bind(material, UsdShade.Tokens.weakerThanDescendants, "physics")


def joint_frames(joint, one, other, point):
    """A joint's frame at a world point, its axes the world's, in each of its two bodies' frames."""
    for index, body in ((0, one), (1, other)):
        inverse = world(body).GetInverse()
        rotation = Gf.Matrix4d(inverse).RemoveScaleShear().ExtractRotationQuat()
        getattr(joint, f"CreateLocalPos{index}Attr")(Gf.Vec3f(inverse.Transform(point)))
        getattr(joint, f"CreateLocalRot{index}Attr")(Gf.Quatf(rotation))
        getattr(joint, f"CreateBody{index}Rel")().SetTargets([body.GetPath()])


def write_drive(joint, drive, rate):
    """The hinge's motor: an angular velocity drive (`speed` degrees a second) whose torque is capped at `torque`
    newton metres between its seconds and is nothing outside them (time samples a frame either side)."""
    api = UsdPhysics.DriveAPI.Apply(joint, UsdPhysics.Tokens.angular)
    api.CreateTypeAttr(UsdPhysics.Tokens.force)
    api.CreateTargetVelocityAttr(drive["speed"])
    api.CreateStiffnessAttr(0.0)
    api.CreateDampingAttr(STIFF_DRIVE)
    force = api.CreateMaxForceAttr()
    start, end = drive["start"] * rate, drive["end"] * rate
    for code, value in ((start - 1, 0.0), (start, drive["torque"]), (end, drive["torque"]), (end + 1, 0.0)):
        force.Set(value, code)


def write_hinge(stage, hinge, rate):
    """The leaf's RevoluteJoint to its frame about the vertical through its pins' middle; its carried objects' fixed
    joints to it; its pins out of the collision."""
    frame, leaf = object_prim(stage, hinge["frame"]), object_prim(stage, hinge["leaf"])
    for name in (hinge["leaf"], *hinge["carries"]):
        moved(object_prim(stage, name), Gf.Vec3d(0.0, hinge["clear"], 0.0))
    pins = [world_box(object_prim(stage, pin)) for pin in hinge["pins"]]
    middle = np.mean([(low + high) / 2 for low, high in pins], axis=0)
    joints = place_path(stage).AppendPath("Physics/Joints")
    joint = UsdPhysics.RevoluteJoint.Define(stage, joints.AppendChild(f"{hinge['leaf']}_hinge"))
    # The hinge roots the leaf's articulation (its frame is static), so what the leaf carries joins it.
    UsdPhysics.ArticulationRootAPI.Apply(joint.GetPrim())
    joint.CreateAxisAttr(UsdPhysics.Tokens.y)
    joint.CreateLowerLimitAttr(hinge["opens"][0])
    joint.CreateUpperLimitAttr(hinge["opens"][1])
    # UsdPhysics' limits are hard; Newton's own default is a soft spring, so its joint attribute says hard (+inf).
    joint.GetPrim().CreateAttribute("newton:limitStiffness", Sdf.ValueTypeNames.Float).Set(float("inf"))
    joint_frames(joint, frame, leaf, Gf.Vec3d(*middle))
    # A joint's bodies do not collide (UsdPhysics' default), said outright for a static frame, which is no body: the
    # leaf is filtered against the frame's colliders.
    pairs = UsdPhysics.FilteredPairsAPI.Apply(leaf).CreateFilteredPairsRel()
    for mesh in own_meshes(frame):
        pairs.AddTarget(mesh.GetPath())
    if "drive" in hinge:
        write_drive(joint.GetPrim(), hinge["drive"], rate)
    for carried in hinge["carries"]:
        held = object_prim(stage, carried)
        fixed = UsdPhysics.FixedJoint.Define(stage, joints.AppendChild(f"{carried}_held"))
        joint_frames(fixed, leaf, held, world(held).ExtractTranslation())
    for pin in hinge["pins"]:
        for mesh in own_meshes(object_prim(stage, pin)):
            UsdPhysics.CollisionAPI(mesh.GetPrim()).CreateCollisionEnabledAttr(False)


def write_push(stage, push, rate):
    """A kinematic box moved in a line from `from` to `to` between its seconds, held before and after."""
    hand = UsdGeom.Cube.Define(stage, place_path(stage).AppendPath(f"Physics/Hands/{push['name']}"))
    hand.CreateSizeAttr(1.0)
    hand.CreatePurposeAttr(UsdGeom.Tokens.guide)
    UsdPhysics.CollisionAPI.Apply(hand.GetPrim())
    UsdPhysics.RigidBodyAPI.Apply(hand.GetPrim()).CreateKinematicEnabledAttr(True)
    moving = hand.AddTranslateOp()
    moving.Set(Gf.Vec3d(*push["from"]), push["start"] * rate)
    moving.Set(Gf.Vec3d(*push["to"]), push["end"] * rate)
    hand.AddScaleOp().Set(Gf.Vec3f(*push["size"]))


def faults(stage, record):
    """What stops the trial before it runs: a body with no drawn mesh, a drop whose column holds anything but its
    target (each object's bounds against the column from its target's top up to where it starts)."""
    found = [f"{name} draws no mesh" for name in bodies_of(record) if not own_meshes(object_prim(stage, name))]
    for drop in record["drops"]:
        low, high = world_box(object_prim(stage, drop["object"]))
        half, at = (high - low) / 2 - COLUMN_INSET, spot_of(stage, drop)
        column_low = np.array([at[0] - half[0], landing(stage, drop) + 0.01, at[1] - half[2]])
        column_high = np.array([at[0] + half[0], column_low[1] + drop["over"] + 2 * half[1], at[1] + half[2]])
        for prim in laid_objects(stage):
            if prim.GetName() in (drop["object"], drop.get("onto")):
                continue
            other_low, other_high = world_box(prim)
            if np.all(other_low < column_high) and np.all(other_high > column_low):
                found.append(f"{drop['object']}: {prim.GetName()} stands in its fall")
    return found


def layer_stage(root, layer, others):
    """The composed stage with `layer` strongest over `others` (layer identifiers) and every write going into it."""
    stand_in = Sdf.Layer.CreateAnonymous(".usda")
    stand_in.subLayerPaths[:] = [layer.identifier, *others]
    stand_in.defaultPrim = Sdf.Layer.FindOrOpen(str(root)).defaultPrim
    stage = Usd.Stage.Open(stand_in)
    stage.SetEditTarget(Usd.EditTarget(layer))
    return stage


def new_layer(folder, name, note):
    path = pathlib.Path(folder) / "layers" / name
    if path.exists():
        path.unlink()
    layer = Sdf.Layer.CreateNew(str(path))
    layer.documentation = note
    return layer


def held(root_path):
    """The root made to hold the physics layers written so far, just under the edit layer."""
    root = Sdf.Layer.FindOrOpen(str(root_path))
    folder = root_path.parent
    kept = [path for path in root.subLayerPaths if path not in LAYERS]
    mine = [path for path in LAYERS if (folder / path).exists()]
    at = kept.index(EDIT) + 1 if EDIT in kept else 0
    root.subLayerPaths[:] = [*kept[:at], *mine, *kept[at:]]
    root.Save()


def layer_ids(root_path, names):
    root = Sdf.Layer.FindOrOpen(str(root_path))
    return [str(root_path.parent / path) for path in root.subLayerPaths if path not in names]


def write(folder, record, materials):
    """The physics and trial layers of the place's stage in `folder`; what was written, or faults that stop it."""
    stage, root_path = opened(folder)
    if stage.GetDefaultPrim().GetName() != record["place"]:
        raise ValueError(f"{folder} holds {stage.GetDefaultPrim().GetName()}, the record is {record['place']}'s")
    stopped = faults(stage, record)
    if stopped:
        return {"faults": stopped}
    rate = stage.GetTimeCodesPerSecond()
    layer = new_layer(folder, "physics.usda", "The place's physics (tools/usd/physics.py): collision, mass, material.")
    working = layer_stage(root_path, layer, layer_ids(root_path, LAYERS))
    write_materials(working, materials["materials"])
    write_scene(working, record)
    meshes = collide_by_triangles(working, record["material"])
    masses = write_masses(working, materials["materials"][record["material"]])
    whole_layer.stamped(layer, record["place"]).Save()
    trial = new_layer(folder, "trial.usda", "The place's physics trial (tools/usd/physics.py).")
    working = layer_stage(root_path, trial, [layer.identifier, *layer_ids(root_path, LAYERS)])
    tops = {drop["object"]: landing(working, drop) for drop in record["drops"]}
    for drop in record["drops"]:
        lifted(working, drop)
    for name in bodies_of(record):
        make_body(object_prim(working, name))
    for hinge in record["hinges"]:
        write_hinge(working, hinge, rate)
    for push in record["pushes"]:
        write_push(working, push, rate)
    whole_layer.stamped(trial, record["place"]).Save()
    held(root_path)
    return {"faults": [], "meshes": meshes, "masses": masses, "bodies": {name: masses[name] for name in
                                                                         bodies_of(record)}, "tops": tops}


def write_motion(folder, motions):
    """layers/physics_motion.usda: each body's transform at every frame as time samples. `motions` is {object: [4 x 4
    motion from its trial start, column vectors, the stage's frame], ...} one a frame from time code 0."""
    stage, root_path = opened(folder)
    layer = new_layer(folder, "physics_motion.usda", "The physics trial's run (tools/usd/physics.py write_motion).")
    working = layer_stage(root_path, layer, layer_ids(root_path, ("./layers/physics_motion.usda",)))
    frames = 0
    for name, steps in motions.items():
        prim = object_prim(working, name)
        start, parent = world(prim), world(prim.GetParent())
        op = UsdGeom.Xformable(prim).MakeMatrixXform()
        for code, motion in enumerate(steps):
            # Gf multiplies row vectors: the motion after the start pose is start * motion transposed.
            op.Set(start * Gf.Matrix4d(np.asarray(motion).T.tolist()) * parent.GetInverse(), code)
        frames = max(frames, len(steps))
    layer.startTimeCode, layer.endTimeCode = 0.0, float(frames - 1)
    whole_layer.stamped(layer, stage.GetDefaultPrim().GetName()).Save()
    held(root_path)
    return frames


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("folder")
    parser.add_argument("record")
    parser.add_argument("materials")
    given = parser.parse_args()
    found = write(given.folder, json.loads(pathlib.Path(given.record).read_text()),
                  json.loads(pathlib.Path(given.materials).read_text()))
    print(json.dumps(found if found["faults"] else {key: found[key] for key in ("meshes", "bodies", "tops")}))
    if found["faults"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
