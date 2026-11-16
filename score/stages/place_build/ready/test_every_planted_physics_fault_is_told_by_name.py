"""Invariant: the physics ready check tells the placing agent, by object, every planted fault that keeps a place from
being walked in and pushed (a crate floating 40 cm over the ground; two crates 10 cm inside each other; a door standing
free of any wall; a door's far side walled off by a crate so no way 0.9 m wide reaches it; a tunnel whose far end
joins nothing; a tunnel too low to walk in; a box half off a desk that tips, and moves when let go in MuJoCo; an object
with no triangles; a door 40 cm narrower than its opening and one lying 20 cm over its wall; a person standing 30 cm
over the ground; a round hatch in a square doorway; a person with no head and no right hand; a person whose sleeve tears from its chest to its hand),
while what rests right passes (the walls, the door filling its opening, the desk, a monitor laid `on` the desk, a
panel mounted `on` a wall, a crate on the ground, a round hatch in the doorway its tunnel's end wall cut to its own
outline (`tube --cap_door`), a person laid at rest on the ground though its SkelRoot's box
reaches 40 cm under its feet); and `on` lays an object in contact with its support;
and a walker's route goes round a crate in its way on that same floor, every point of it standing there, and is refused
where no floor is (the walkers' ground, `solids`, holds the wall and not the open door).

Breaks that turn this red (each applied once and seen red, then reverted):
- ready.support_faults: `gaps[nearest] > TOLERANCE` made `> 1.0` -> the floating crate passes
- ready.crossing_depths: `count % 2` made `count % 2 == 0` -> the overlapping crates pass
- ready.door_faults: the `open_sides` list left empty -> the free-standing door passes
- ready.room_for_walkway: ERODED made 0 -> the blocked door's far side reads reached
- ready.connector_faults: JOIN made 10 -> the tunnel's free end reads joined
- ready.walkers_floor: `clear` taken as all True -> the low tunnel reads walkable
- ready.placed_on: the gap left unsubtracted -> the monitor floats over the desk
- ready.check: the no-collision list left empty -> the decal passes
- settle_mujoco.settled: the steps left out -> the tipping box reads stable
- ready.fit_faults: `gap > FIT` made `gap > 1.0` -> the small door passes; `past > FIT` the same -> the big one passes
- ready.person_faults: `abs(gap) > CONTACT` made `> 1.0` -> the floating person passes
- people.shape_faults: `missing` left empty -> the headless person passes; TORN made 1.0 -> the torn sleeve passes
- dome_shell.inside_outline: the count's `% 2` dropped -> the round hatch's doorway is not cut and it does not fit
- place_build.lowest_of: the posed skin left unread (the box's floor taken) -> the person at rest floats 40 cm
- ready.near_ground: `kept` taken as every face -> the far terrain is held whole
- ready.straightened: `in_sight` taken as always True -> the route runs straight through crate_ok
- ready.nearest_to_surface: `+ longest` dropped -> a ring off a coarse box's face reads its corner's distance, not its own
"""
import json
import pathlib

import numpy as np
import trimesh
from PIL import Image
from pxr import Gf, Sdf, UsdGeom, UsdSkel, Vt

from score.stages import place_build
from score.stages.place_build import ready


def box(stage, place, name, size, low, kind="model"):
    """An object of one cube `size` (x, y, z metres) whose lowest corner is `low`."""
    path = f"/{place}/Objects/{name}"
    holder = UsdGeom.Xform.Define(stage, path)
    holder.AddTranslateOp().Set(Gf.Vec3d(*(np.asarray(low) + np.asarray(size) / 2)))
    holder.AddRotateXYZOp().Set(Gf.Vec3f(0, 0, 0))
    holder.AddScaleOp().Set(Gf.Vec3f(1, 1, 1))
    cube = UsdGeom.Cube.Define(stage, f"{path}/geo")
    cube.CreateSizeAttr(1.0)
    cube.AddScaleOp().Set(Gf.Vec3f(*size))
    prim = holder.GetPrim()
    prim.CreateAttribute("score:kind", Sdf.ValueTypeNames.String).Set(kind)
    prim.CreateAttribute("score:library", Sdf.ValueTypeNames.String).Set(f"model/{name}")
    return prim


def desk(stage, place):
    """A desk: a top 1.2 x 0.05 x 0.6 at 0.75 m on four legs, its corner at (-3, -3)."""
    prim = box(stage, place, "desk", (1.2, 0.05, 0.6), (-3.0, 0.70, -3.0))
    for number, (x, z) in enumerate(((-0.55, -0.25), (0.55, -0.25), (-0.55, 0.25), (0.55, 0.25))):
        leg = UsdGeom.Cube.Define(stage, f"{prim.GetPath()}/leg{number}")
        leg.CreateSizeAttr(1.0)
        leg.AddTranslateOp().Set(Gf.Vec3d(x, -0.375, z))
        leg.AddScaleOp().Set(Gf.Vec3f(0.05, 0.70, 0.05))


def wall(stage, place):
    """A wall 8 m long, 2.5 m high and 0.2 m thick along x at z 0, a doorway 1.2 m wide and 2.1 m high cut in its
    middle: one object of three blocks."""
    prim = box(stage, place, "wall", (3.4, 2.5, 0.2), (-4.0, 0.0, -0.1))
    for name, size, middle in (("right", (3.4, 2.5, 0.2), (4.6, 0.0, 0.0)), ("lintel", (1.2, 0.4, 0.2), (2.3, 1.05, 0.0))):
        block = UsdGeom.Cube.Define(stage, f"{prim.GetPath()}/{name}")
        block.CreateSizeAttr(1.0)
        block.AddTranslateOp().Set(Gf.Vec3d(*middle))
        block.AddScaleOp().Set(Gf.Vec3f(*size))


def wall_along_z(stage, place, name, x, blocks):
    """A wall 0.2 m thick across x at `x`, one object of blocks (z low, z high, y low, y high)."""
    holder = UsdGeom.Xform.Define(stage, f"/{place}/Objects/{name}")
    holder.GetPrim().CreateAttribute("score:kind", Sdf.ValueTypeNames.String).Set("model")
    for number, (z_low, z_high, y_low, y_high) in enumerate(blocks):
        block = UsdGeom.Cube.Define(stage, f"{holder.GetPath()}/block{number}")
        block.CreateSizeAttr(1.0)
        block.AddTranslateOp().Set(Gf.Vec3d(x, (y_low + y_high) / 2, (z_low + z_high) / 2))
        block.AddScaleOp().Set(Gf.Vec3f(0.2, y_high - y_low, z_high - z_low))


JOINTS = {"Root": (0, 0, 0), "Root/Hips": (0, 0.9, 0), "Root/Hips/Spine": (0, 1.3, 0),
          "Root/Hips/Spine/Head": (0, 1.5, 0), "Root/Hips/Spine/LeftHand": (0.3, 1.0, 0),
          "Root/Hips/Spine/RightHand": (-0.3, 1.0, 0), "Root/Hips/LeftLeg": (0.1, 0.9, 0),
          "Root/Hips/LeftLeg/LeftShin": (0.1, 0.5, 0), "Root/Hips/LeftLeg/LeftShin/LeftFoot": (0.1, 0.08, 0),
          "Root/Hips/RightLeg": (-0.1, 0.9, 0), "Root/Hips/RightLeg/RightShin": (-0.1, 0.5, 0),
          "Root/Hips/RightLeg/RightShin/RightFoot": (-0.1, 0.08, 0)}
PARTS = {"Root/Hips/Spine/Head": ((0, 1.6, 0), (0.2, 0.2, 0.2)), "Root/Hips/Spine": ((0, 1.2, 0), (0.35, 0.6, 0.2)),
         "Root/Hips/Spine/LeftHand": ((0.3, 1.0, 0), (0.08, 0.1, 0.08)),
         "Root/Hips/Spine/RightHand": ((-0.3, 1.0, 0), (0.08, 0.1, 0.08)),
         "Root/Hips/LeftLeg": ((0.1, 0.7, 0), (0.12, 0.4, 0.12)), "Root/Hips/RightLeg": ((-0.1, 0.7, 0), (0.12, 0.4, 0.12)),
         "Root/Hips/LeftLeg/LeftShin": ((0.1, 0.29, 0), (0.1, 0.42, 0.1)),
         "Root/Hips/RightLeg/RightShin": ((-0.1, 0.29, 0), (0.1, 0.42, 0.1)),
         "Root/Hips/LeftLeg/LeftShin/LeftFoot": ((0.1, 0.04, 0.05), (0.1, 0.08, 0.25)),
         "Root/Hips/RightLeg/RightShin/RightFoot": ((-0.1, 0.04, 0.05), (0.1, 0.08, 0.25))}


def skinned(stage, path, points, faces, joints):
    """A mesh under a skeleton, each point bound wholly to its joint's number."""
    mesh = UsdGeom.Mesh.Define(stage, path)
    mesh.CreatePointsAttr(Vt.Vec3fArray.FromNumpy(np.asarray(points, np.float32)))
    mesh.CreateFaceVertexCountsAttr([3] * len(faces))
    mesh.CreateFaceVertexIndicesAttr(Vt.IntArray.FromNumpy(np.asarray(faces, np.int32).reshape(-1)))
    binding = UsdSkel.BindingAPI.Apply(mesh.GetPrim())
    binding.CreateJointIndicesPrimvar(False, 1).Set(Vt.IntArray(list(map(int, joints))))
    binding.CreateJointWeightsPrimvar(False, 1).Set(Vt.FloatArray([1.0] * len(joints)))
    binding.CreateGeomBindTransformAttr(Gf.Matrix4d(1))


def person(stage, place, name, spot, without=(), torn=False):
    """A person 1.7 m tall of boxes bound to a skeleton (head, hands, legs, feet), standing at `spot`, held still;
    `without` its parts left off, `torn` a sleeve from its chest to its left hand pulled 12 cm out (more than double, under
    route_stretch.MOST_METRES). Its SkelRoot's
    box reaches 40 cm under its feet, as a real body's box holds every clip at once."""
    import trimesh
    root = UsdSkel.Root.Define(stage, f"/{place}/Objects/{name}")
    root.GetPrim().CreateAttribute("score:kind", Sdf.ValueTypeNames.String).Set("character")
    root.CreateExtentAttr([Gf.Vec3f(-0.5, -0.4, -0.5), Gf.Vec3f(0.5, 1.8, 0.5)])
    place_build.posed(root.GetPrim(), spot, (0, 0, 0), (1, 1, 1))
    skeleton = UsdSkel.Skeleton.Define(stage, f"{root.GetPath()}/Skeleton")
    order = list(JOINTS)
    skeleton.CreateJointsAttr(order)
    skeleton.CreateBindTransformsAttr([Gf.Matrix4d(1).SetTranslate(Gf.Vec3d(*JOINTS[joint])) for joint in order])
    local = {joint: np.subtract(JOINTS[joint], JOINTS[joint.rsplit("/", 1)[0]] if "/" in joint else 0).astype(float)
             for joint in order}
    skeleton.CreateRestTransformsAttr([Gf.Matrix4d(1).SetTranslate(Gf.Vec3d(*map(float, local[joint]))) for joint in order])
    held = UsdSkel.Animation.Define(stage, f"{root.GetPath()}/Held")
    held.CreateJointsAttr(order)
    moved = {joint: local[joint] + ([0.12, 0, 0] if torn and joint.endswith("LeftHand") else 0) for joint in order}
    held.CreateTranslationsAttr([Gf.Vec3f(*map(float, moved[joint])) for joint in order])
    held.CreateRotationsAttr([Gf.Quatf(1)] * len(order))
    held.CreateScalesAttr([Gf.Vec3h(1, 1, 1)] * len(order))
    binding = UsdSkel.BindingAPI.Apply(skeleton.GetPrim())
    binding.CreateAnimationSourceRel().SetTargets([held.GetPath()])
    UsdSkel.BindingAPI.Apply(root.GetPrim()).CreateSkeletonRel().SetTargets([skeleton.GetPath()])
    for number, (joint, (middle, size)) in enumerate(PARTS.items()):
        if any(joint.endswith(part) for part in without):
            continue
        part = trimesh.creation.box(size)
        skinned(stage, f"{root.GetPath()}/part{number}", part.vertices + middle, part.faces,
                [order.index(joint)] * len(part.vertices))
    if torn:
        sleeve = [(0.2, 1.1, 0.1), (0.2, 1.15, 0.1), (0.26, 1.1, 0.1), (0.26, 1.15, 0.1)]
        joints = [order.index("Root/Hips/Spine")] * 2 + [order.index("Root/Hips/Spine/LeftHand")] * 2
        skinned(stage, f"{root.GetPath()}/sleeve", sleeve, [(0, 2, 1), (1, 2, 3)], joints)


def hatch(stage, place, name, tunnel_at, radius, length):
    """A round hatch 1 m across standing on a tunnel's deck in the plane of its end wall (the tunnel along +x)."""
    import trimesh
    from score.stages.place_build import dome_shell
    deck = tunnel_at[1] + dome_shell.FLOOR * radius
    disc = trimesh.creation.cylinder(radius=0.5, height=0.05, sections=48)
    disc.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, (0, 1, 0)))
    disc.apply_translation((tunnel_at[0] + length - dome_shell.CAP_THICK / 2, deck + 0.5, tunnel_at[2]))
    holder = UsdGeom.Xform.Define(stage, f"/{place}/Objects/{name}")
    holder.GetPrim().CreateAttribute("score:kind", Sdf.ValueTypeNames.String).Set("model")
    mesh = UsdGeom.Mesh.Define(stage, f"{holder.GetPath()}/geo")
    mesh.CreatePointsAttr(Vt.Vec3fArray.FromNumpy(np.asarray(disc.vertices, np.float32)))
    mesh.CreateFaceVertexCountsAttr([3] * len(disc.faces))
    mesh.CreateFaceVertexIndicesAttr(Vt.IntArray.FromNumpy(np.asarray(disc.faces, np.int32).reshape(-1)))


def planted(folder):
    """The fixture place: a ground disc, a wall with a 1.2 m opening and its door, and every planted fault."""
    concept = folder / "concept.png"
    Image.new("RGB", (8, 8)).save(concept)
    place_build.start(folder / "place", "fixture", concept)
    folder = folder / "place"
    place_build.ground(folder, "ground", 7.0, (0.0, -0.02, 0.0))
    place_build.tube(folder, "tunnel", 1.4, 3.0, (-3.0, 0.0, 2.5))  # its far end, at z 5.5, joins nothing
    place_build.tube(folder, "crawl", 0.7, 2.0, (3.5, 0.0, -5.0), (0.0, 90.0, 0.0))
    stage, place = place_build.opened(folder)
    wall(stage, place)
    box(stage, place, "door", (1.18, 2.08, 0.05), (-0.59, 0.0, -0.025))  # 1 to 2 cm inside its opening
    wall_along_z(stage, place, "wall2", 5.5, [(-2.5, -1.6, 0, 2.5), (-0.4, 0.4, 0, 2.5), (1.6, 2.5, 0, 2.5),
                                              (-1.6, -0.4, 2.1, 2.5), (0.4, 1.6, 2.1, 2.5)])
    box(stage, place, "door_small", (0.05, 2.1, 0.8), (5.475, 0.0, -1.4))
    box(stage, place, "door_big", (0.05, 2.4, 1.6), (5.375, 0.0, 0.2))
    box(stage, place, "blocker", (2.4, 1.0, 1.1), (-1.2, 0.0, -1.4))
    box(stage, place, "hatch_free", (1.0, 2.0, 0.05), (2.5, 0.0, 3.0))
    box(stage, place, "bulkhead", (3.0, 2.8, 0.2), (-4.5, 0.0, 2.3))
    box(stage, place, "crate_ok", (0.5, 0.5, 0.5), (4.0, 0.0, 1.0))
    box(stage, place, "crate_float", (0.5, 0.5, 0.5), (-1.0, 0.4, -4.5))
    box(stage, place, "crate_a", (0.5, 0.5, 0.5), (1.5, 0.0, -3.5))
    box(stage, place, "crate_b", (0.5, 0.5, 0.5), (1.9, 0.0, -3.5))
    desk(stage, place)
    box(stage, place, "monitor", (0.5, 0.35, 0.1), (-2.65, 1.5, -2.8))
    box(stage, place, "tipper", (0.4, 0.4, 0.4), (-3.3, 0.75, -2.9))
    box(stage, place, "panel", (0.6, 0.4, 0.05), (2.0, 0.5, 1.0))
    floor = ready.levels_under(ready.Place(stage, place), "ground", (-5.5, 0.0))[-1]
    person(stage, place, "person_ok", (-5.5, floor, 0.0))
    place_build.rested(stage, f"/{place}/Objects/person_ok", (-5.5, floor, 0.0), (0, 0, 0), (1, 1, 1))
    person(stage, place, "person_float", (-5.5, floor + 0.3, 1.5))
    person(stage, place, "person_broken", (-5.5, floor, -1.5), without=("Head", "RightHand"))
    person(stage, place, "person_torn", (-5.5, floor, -3.0), torn=True)
    hatch(stage, place, "hatch_round", (-6.5, 0.0, -6.0), 1.0, 1.0)
    hatch(stage, place, "hatch_squared", (-6.5, 0.0, 6.0), 1.0, 1.0)
    decal = UsdGeom.Xform.Define(stage, f"/{place}/Objects/decal").GetPrim()
    decal.CreateAttribute("score:kind", Sdf.ValueTypeNames.String).Set("model")
    stage.GetRootLayer().Save()
    place_build.tube(folder, "lock_round", 1.0, 1.0, (-6.5, 0.0, -6.0), (0.0, 90.0, 0.0), cap_door="hatch_round")
    place_build.tube(folder, "lock_squared", 1.0, 1.0, (-6.5, 0.0, 6.0), (0.0, 90.0, 0.0), cap=[1.0, 1.0])
    return folder


def test_every_planted_physics_fault_is_told_by_name(tmp_path):
    folder = planted(tmp_path)
    coarse = trimesh.creation.box(extents=(2.0, 2.0, 2.0))  # a face's middle half a metre off, a corner 0.6 off its own
    corner = np.array([1.0, 1.0, 1.0]) + 0.6 / np.sqrt(3.0)
    assert abs(ready.nearest_to_surface(coarse, np.array([[0.0, 1.5, 0.0], corner])) - 0.5) < 1e-6
    monitor = ready.on(folder, "monitor", "desk")
    panel = ready.on(folder, "panel", "wall:wall", height=1.2)
    assert abs(monitor["at"][1] - (0.75 + 0.175)) < 0.01, monitor  # its bottom on the desk's top
    assert abs(panel["at"][2] - (0.1 + 0.025)) < 0.01 and abs(panel["at"][1] - 1.4) < 0.03, panel
    walk, metres = ready.route(folder, [(4.25, 0.0, 0.7), (4.25, 0.0, 2.6)])
    walk = np.asarray(walk)
    along = np.linspace(0.0, 1.0, 20)[:, None]
    sampled = np.concatenate([start + (end - start) * along for start, end in zip(walk[:-1], walk[1:])])
    clear_of_crate = (sampled[:, 0] < 4.0 - 0.3) | (sampled[:, 0] > 4.5 + 0.3) | (sampled[:, 2] < 1.0 - 0.3) \
        | (sampled[:, 2] > 1.5 + 0.3)
    assert clear_of_crate.all() and metres > 1.9, (walk.tolist(), metres)
    try:
        ready.route(folder, [(4.25, 0.0, 0.7), (4.25, 2.0, 2.6)])
        raise AssertionError("a spot with no floor under it was routed to")
    except place_build.Refused:
        pass
    terrain = trimesh.creation.box([3000.0, 1.0, 3000.0])
    terrain = trimesh.Trimesh(*trimesh.remesh.subdivide_to_size(terrain.vertices, terrain.faces, 50.0), process=False)
    near = ready.near_ground(terrain, np.array([-5.0, 0.0, -5.0]), np.array([5.0, 2.0, 5.0]))
    assert len(near.faces) < len(terrain.faces) / 100 and np.abs(near.bounds[:, [0, 2]]).max() < 5 + 20 + 50
    ground = ready.solids(folder)
    assert "wall" in ground and "door" not in ground and ground["wall"].shape[1:] == (3, 3), sorted(ground)
    summary = ready.check(folder)
    found = json.loads(pathlib.Path(summary["file"]).read_text())["objects"]
    told = {name: {fault["fault"] for fault in faults} for name, faults in found.items()}
    print(json.dumps(summary))
    for name in ("wall", "desk", "monitor", "panel", "crate_ok", "bulkhead", "person_ok",
                 "ground"):
        assert name not in told, (name, found.get(name))
    assert told["door"] == {"walkway"}, found["door"]
    assert "floating" in told["crate_float"], found["crate_float"]
    assert "penetration" in told["crate_a"] and "penetration" in told["crate_b"], (found.get("crate_a"))
    assert "door not in an opening" in told["hatch_free"], found.get("hatch_free")
    assert any(fault.get("end") == "end" for fault in found["tunnel"]) \
        and not any(fault.get("end") == "start" for fault in found["tunnel"]), found["tunnel"]
    assert any("unwalkable" in fault for fault in found["crawl"]), found["crawl"]
    assert told["decal"] == {"no collision geometry"}, found["decal"]
    assert "tips" in told["tipper"], found["tipper"]
    assert any(fault.get("gap", 0) > 0.15 for fault in found["door_small"] if fault["fault"] == "door does not fit"), \
        found["door_small"]
    assert any(fault.get("over", 0) > 0.15 for fault in found["door_big"] if fault["fault"] == "door does not fit"), \
        found["door_big"]
    assert {fault.get("foot") for fault in found["person_float"] if fault["fault"] == "person floating"} \
        == {"left", "right"}, found["person_float"]
    assert any(set(fault.get("missing", ())) == {"head", "right hand"} for fault in found["person_broken"]), \
        found["person_broken"]
    assert any(fault.get("torn", 0) > 0.5 for fault in found["person_torn"]), found["person_torn"]
    assert "door does not fit" not in told.get("hatch_round", ()), found["hatch_round"]
    assert "door does not fit" in told["hatch_squared"], found.get("hatch_squared")
    if summary["settle"].startswith("not run"):
        print("skipped: the MuJoCo settle (" + summary["settle"] + ")")
        return
    assert "unstable" in told["tipper"] and "unstable" not in told.get("crate_ok", ()), found["tipper"]
