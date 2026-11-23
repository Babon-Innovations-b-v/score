"""Invariant: the physics ready check tells the placing agent, by object, every planted fault that keeps a place from
being walked in and pushed (a crate floating 40 cm over the ground; two crates 10 cm inside each other; a door standing
free of any wall; a door's far side walled off by a crate so no way 0.9 m wide reaches it, unless that door's leaf is joined to a
neighbour there (place.json `joins`), whose side the area's joins check walks; a tunnel whose far end
joins nothing; a tunnel too low to walk in; a box half off a desk that tips, and moves when let go in MuJoCo; an object
with no triangles; a door 40 cm narrower than its opening and one lying 20 cm over its wall; a person standing 30 cm
over the ground; a walker (time-sampled) 30 cm over it, told by its planted foot alone; a round hatch in a square doorway; a person with no head and no right hand; a person whose sleeve tears from its chest to its hand),
while what rests right passes (the walls, a walker stepping with its left foot 10 cm up, the door filling its opening, the desk, a monitor laid `on` the desk, a
panel mounted `on` a wall, a block over an adopted bench's gap held by the convex hull its MuJoCo physics
collides by, a crate on the ground, a rock sunk 30 cm into it, a round hatch in the doorway its tunnel's end wall cut to its own
outline (`tube --cap_door`), a person laid at rest on the ground though its SkelRoot's box
reaches 40 cm under its feet); and `on` lays an object in contact with its support;
and a walker's route goes round a crate in its way on that same floor and through every spot it is sent through, every point of it standing there, and is refused
where no floor is (the walkers' ground, `solids`, holds the wall and the shut door, a solid in its doorway). A field of 300 rocks bedded in
a second ground passes, while a rock 30 cm over it floats and a crate laid into a rock penetrates it, and a rock's
support is cast against only the faces under it (camp's 660 rocks on a terrain ran the check out of 14 GB); a sky dome
laid as an object (`score:kind` light) is no solid: never told, never stood on. Far scenery (two rocks laid into each
other and a ground disc, over 200 m past every walker's reach) is scenery, never told, while the same two rocks 12 m
past the reached objects still penetrate. A closed room (walls, roof, its door shut in its doorway) sees nothing
outside from its walkers' floor (nor does one whose door's own frame stands 0.6 m out of its wall, its looks starting
from the floor with that door shut, nor a closed hall 48 m long, its looks reaching its far wall), and a look past a
face lying along it (which trimesh's embree drops) still meets the wall behind, while the same room with its front
wall left out (a cut-away built into the
building) is told open to the outside, and the room built without its roof, its floor under nothing so its looks judge
nothing, is told no roof (passed in an outside place, a walled yard); in an outside place (place.json `kind`) that open-fronted room is a covered
stretch of the outside (an arcade) and passes, while a shop's room, one structure with a glassless window gap, is told
open. The check's memory stays bounded: a surface's points are read a chunk at a
time (the very points trimesh's sample_surface draws), so a floor of 6.6 million points holds under 64 MB; a post
300 m off, stretching the walkers' grid past the memory budget, is refused by name before the grid is read; and the
settle runs as many models side by side as fit the budget, refusing when not even its largest fits. A room seated
in its area beside a neighbour holding its back wall (the doorway its door fills) and an alcove behind it is told,
alone, its door in no wall and open; seated among that neighbour (check's `neighbours`) it is told just what the
room built whole is (nothing; the alcove on the neighbour's floor left to the neighbour's own check), the
neighbour's post 150 m off, past the room's sight, never lent into it, and the same room cut open in front still open; its looks are cast a batch at a time (CAST_AT_ONCE), each batch meeting what
all of them at once meet, and a large cast's ray structure is freed when it is done.

Breaks that turn this red (each applied once and seen red, then reverted):
- ready.support_faults: `gaps[nearest] > TOLERANCE` made `> 1.0` -> the floating crate passes
- ready.support_faults: `bedded` taken as False -> the rock sunk 30 cm reads as standing on nothing
- ready.crossing_depths: `count % 2` made `count % 2 == 0` -> the overlapping crates pass
- ready.door_faults: the `open_sides` list left empty -> the free-standing door passes
- ready.room_for_walkway: ERODED made 0 -> the blocked door's far side reads reached
- ready.walkway_targets: a joined leaf's far side kept -> the door joined to a neighbour past its blocked side is
  still sent there (the pad's walkway hatch, whose far side is the capsule's, 2099 #161); its join's `from` unread ->
  a doorway joined as laid (no leaf of it) drops the door's side too
- ready.connector_faults: JOIN made 10 -> the tunnel's free end reads joined
- ready.walkers_floor: `clear` taken as all True -> the low tunnel reads walkable
- ready.placed_on: the gap left unsubtracted -> the monitor floats over the desk
- ready.check: the no-collision list left empty -> the decal passes
- settle_mujoco.settled: the steps left out -> the tipping box reads stable
- ready.held_by: the desk whose box holds the pad left out of the pad's statics -> the pad falls through it, unstable
- ready.fit_faults: `gap > FIT` made `gap > 1.0` -> the small door passes; `past > FIT` the same -> the big one passes
- ready.fit_faults: the outline's holes left unfilled -> the lattice gate filling its opening reads as not fitting
- ready.person_faults: `abs(gap) > CONTACT` made `> 1.0` -> the floating person passes (and the floating walker)
- ready.walks: taken as always False -> the walker with its left foot stepping 10 cm up reads floating
- people.shape_faults: `missing` left empty -> the headless person passes; TORN made 1.0 -> the torn sleeve passes
- dome_shell.inside_outline: the count's `% 2` dropped -> the round hatch's doorway is not cut and it does not fit
- place_build.lowest_of: the posed skin left unread (the box's floor taken) -> the person at rest floats 40 cm
- ready.near_ground: `kept` taken as every face -> the far terrain is held whole
- ready.straightened: `in_sight` taken as always True -> the route runs straight through crate_ok
- ready.route: the legs straightened as one path -> the walk skips the spot it is sent through
- ready.solids: the doors left out (doors_standing unread) -> the shut door is no solid
- ready.nearest_to_surface: `+ longest` dropped -> a ring off a coarse box's face reads its corner's distance, not its own
- ready.nearest_to_surface: every pair of a chunk's points and the faces near them weighed at once (trimesh's
  closest_point, as before) -> the dense ball's search holds more pairs than `pairs` (the capsule's package past 12 GB)
- ready.ray_box: the box left open on every axis -> a rock's support query reaches every rock's faces
- ready.role_of: `light` read as a prop -> the sky dome is stood on in `solids` (and its box spans the walkers' grid)
- ready.support_faults on the field: `gaps[nearest] > TOLERANCE` made `> 1.0` -> the floating rock passes
- ready.out_of_reach: `far` left empty -> the far shore reads no collision geometry and the far rocks penetrate
- ready.open_faults: ROOFED made 0.0 -> the roofless room's looks judge nothing and it passes
- ready.open_faults: INSIDE_SHARE made 1.01 -> no point of the cut room reads inside and it passes
- ready.open_faults: SEES made 1.0 -> the closed room's far looks read open and it is told
- ready.sight: SEES alone (the place's diagonal left out) -> the closed hall 48 m long reads open along its length
- ready.rooms: the level looks stopped by props (unmoved left out) -> the cluttered shop reads no room, so passes
- ready.through_joins: no look passes a joined doorway -> the cut room whose open front is joined reads open
- ready.walled: every covered point kept -> the porch outside the closed room's door reads open
- ready.crouched_through: never called -> the hatch marked crouch joins nothing, its sides two pieces
- ready.frame_of: its own y taken for up -> the hatch modelled lying down reads 2.5 cm tall
- ready.levels_under: one ray at the middle -> the stick whose middle stands past the desk reads no level
- ready.library_name: the whole address read -> the airlock's console reads as a door by its place's name
- ready.mounted: the floor under a mount read from the ground, shells and connectors alone -> the plaque on the wall
  over the dais stands 1.0 m over the ground, not over the dais
- ready.look_floor: walkers_floor(laid) with every door open -> the hooded door's frame holds look points that see
  out past it, and the closed room is told
- ready.cast: the rays embree gave up on left uncast -> the look past a face lying along it meets nothing, and the
  wall behind is never met
- ready.open_faults: `rooms` left out of an outside place -> the open-fronted arcade (the cut room under the sky) is told
- ready.rooms: the cover's own object not asked (only doors close) -> the shop's room is no room and its open window
  passes
- ready.seated_among: the neighbour's seat taken alone (this place's own seat not undone) -> the hall's wall stands
  turned off the room, so the seated room's door is in no wall and it reads open
- ready.own_spots: every point kept -> the alcove on the hall's floor, walled and roofed by the hall, reads open from
  the seated room
- ready.seated_among: every neighbour object left out -> the seated room's door is in no wall and it reads open
- ready.Place.hits: CAST_AT_ONCE unread (every look cast at once) -> the closed room's 50 looks reach `cast` in one
  batch past the 7 at once (the square's looks, cast all at once against the plaza, held past 12 GB)
- ready.cast: its `gc.collect()` left out -> the ball's cast leaves its Trimesh (and its ray structure) alive until
  the collector runs (the square's looks held every batch's, past 12 GB)
- ready.box_meets: taken as always True -> the hall's post 150 m off, past the room's sight, is lent (the flat
  among the square's 848 objects ran its check past 12 GB)
- ready.out_of_reach: the reached box taken without GROUND_REACH round it -> the field's rocks and the near rocks read
  scenery and pass
- reach.surface_chunks: `lengths.bit_generator.advance(count)` left out -> the chunked points are not sample_surface's
- reach.surface_chunks: `chunk` taken as 10 ** 12 (the whole surface at once) -> the floor holds 419 MB
- ready.walkers_grid: its `within_memory` left uncalled -> the post's grid is read, not refused
- ready.settle_workers: `room` left out of the count -> three models run where two fit
- ready.settle_mass: its `engine_chosen(prim, "MuJoCo")` left out -> the adopted prop authoring its mass in its
  MuJoCo physics variant alone settles as a hull of DENSITY (NaN), not its 1.5496 kg times its scale cubed (#155)
- ready.settle_colliders: mujoco_chosen left out (the default variant read) -> the adopted bench collides by its
  triangles, so the block over its gap has nothing under it in its statics (#155)
- ready.collider_of: the `convexHull` approximation unread (every collider its triangles) -> the same
- ready.statics_near: the adopted objects' colliders unread (their drawn triangles taken) -> the same
- ready.solid_of: its walk without Usd.TraverseInstanceProxies() -> the adopted desk whose top stands under an
  instanceable prim (a SimReady model's) reads no solid, and `on` refuses "no support" (#155)
"""
import gc
import json
import pathlib
import tracemalloc

import numpy as np
import trimesh
from PIL import Image
from pxr import Gf, Sdf, Usd, UsdGeom, UsdPhysics, UsdSkel, Vt

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


def hutch(stage, place):
    """A desk with a raised back: a top 1.0 x 0.05 x 0.6 at 0.75 m on two side panels, a back panel to 1.15 m, its
    corner at (0.2, 4.4); its box holds what lies on its top."""
    prim = box(stage, place, "hutch", (1.0, 0.05, 0.6), (0.2, 0.70, 4.4))
    for name, size, middle in (("left", (0.05, 0.70, 0.6), (-0.475, -0.375, 0.0)),
                               ("right", (0.05, 0.70, 0.6), (0.475, -0.375, 0.0)),
                               ("back", (1.0, 0.45, 0.05), (0.0, 0.2, 0.275))):
        panel = UsdGeom.Cube.Define(stage, f"{prim.GetPath()}/{name}")
        panel.CreateSizeAttr(1.0)
        panel.AddTranslateOp().Set(Gf.Vec3d(*middle))
        panel.AddScaleOp().Set(Gf.Vec3f(*size))


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


def lattice_gate(stage, place, name, x, z_low, z_high, high):
    """A folding gate across x at `x` from z_low to z_high and `high` tall, one object: its frame 6 cm wide and four
    bars 3 cm wide between, the gaps between them 17 cm (a stairwell's security gate)."""
    holder = UsdGeom.Xform.Define(stage, f"/{place}/Objects/{name}")
    holder.GetPrim().CreateAttribute("score:kind", Sdf.ValueTypeNames.String).Set("model")
    bars = [(z_low, z_low + 0.06, 0.0, high), (z_high - 0.06, z_high, 0.0, high), (z_low, z_high, 0.0, 0.06),
            (z_low, z_high, high - 0.06, high)]
    bars += [(middle - 0.015, middle + 0.015, 0.06, high - 0.06)
             for middle in np.linspace(z_low + 0.06, z_high - 0.06, 6)[1:-1]]
    for number, (bar_low, bar_high, y_low, y_high) in enumerate(bars):
        bar = UsdGeom.Cube.Define(stage, f"{holder.GetPath()}/bar{number}")
        bar.CreateSizeAttr(1.0)
        bar.AddTranslateOp().Set(Gf.Vec3d(x, (y_low + y_high) / 2, (bar_low + bar_high) / 2))
        bar.AddScaleOp().Set(Gf.Vec3f(0.05, y_high - y_low, bar_high - bar_low))


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


def person(stage, place, name, spot, without=(), torn=False, stepping=False):
    """A person 1.7 m tall of boxes bound to a skeleton (head, hands, legs, feet), standing at `spot`, held still;
    `without` its parts left off, `torn` a sleeve from its chest to its left hand pulled 12 cm out (more than double, under
    route_stretch.MOST_METRES), `stepping` its left foot lifted 10 cm and its spot time-sampled a step on (a walker). Its
    SkelRoot's
    box reaches 40 cm under its feet, as a real body's box holds every clip at once."""
    import trimesh
    root = UsdSkel.Root.Define(stage, f"/{place}/Objects/{name}")
    root.GetPrim().CreateAttribute("score:kind", Sdf.ValueTypeNames.String).Set("character")
    root.CreateExtentAttr([Gf.Vec3f(-0.5, -0.4, -0.5), Gf.Vec3f(0.5, 1.8, 0.5)])
    place_build.posed(root.GetPrim(), spot, (0, 0, 0), (1, 1, 1))
    if stepping:
        move = UsdGeom.Xformable(root.GetPrim()).GetOrderedXformOps()[0]
        move.Set(Gf.Vec3d(*spot), 0.0)
        move.Set(Gf.Vec3d(spot[0], spot[1], spot[2] + 0.7), 24.0)
    skeleton = UsdSkel.Skeleton.Define(stage, f"{root.GetPath()}/Skeleton")
    order = list(JOINTS)
    skeleton.CreateJointsAttr(order)
    skeleton.CreateBindTransformsAttr([Gf.Matrix4d(1).SetTranslate(Gf.Vec3d(*JOINTS[joint])) for joint in order])
    local = {joint: np.subtract(JOINTS[joint], JOINTS[joint.rsplit("/", 1)[0]] if "/" in joint else 0).astype(float)
             for joint in order}
    skeleton.CreateRestTransformsAttr([Gf.Matrix4d(1).SetTranslate(Gf.Vec3d(*map(float, local[joint]))) for joint in order])
    held = UsdSkel.Animation.Define(stage, f"{root.GetPath()}/Held")
    held.CreateJointsAttr(order)
    moved = {joint: local[joint] + ([0.12, 0, 0] if torn and joint.endswith("LeftHand") else 0)
             + ([0, 0.1, 0] if stepping and joint.endswith("LeftFoot") else 0) for joint in order}
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


def rock(stage, place, name, middle, radius):
    """A rock: an icosphere of `radius` round `middle`, one mesh under its object."""
    shape = trimesh.creation.icosphere(subdivisions=1, radius=radius)
    holder = UsdGeom.Xform.Define(stage, f"/{place}/Objects/{name}")
    holder.AddTranslateOp().Set(Gf.Vec3d(*map(float, middle)))
    holder.GetPrim().CreateAttribute("score:kind", Sdf.ValueTypeNames.String).Set("model")
    mesh = UsdGeom.Mesh.Define(stage, f"{holder.GetPath()}/geo")
    mesh.CreatePointsAttr(Vt.Vec3fArray.FromNumpy(np.asarray(shape.vertices, np.float32)))
    mesh.CreateFaceVertexCountsAttr([3] * len(shape.faces))
    mesh.CreateFaceVertexIndicesAttr(Vt.IntArray.FromNumpy(np.asarray(shape.faces, np.int32).reshape(-1)))


def rock_field(folder):
    """A second ground at x 20 holding 300 rocks bedded a third of their size into it, a rock 30 cm over it, a crate
    laid 10 cm into a rock (rock_big), and a sky dome (a sphere 300 m round the place, `score:kind` light)."""
    place_build.ground(folder, "field", 6.0, (20.0, -0.02, 0.0))
    stage, place = place_build.opened(folder)
    floor = ready.levels_under(ready.Place(stage, place), "ground", (6.5, 0.0))[-1]  # the field is the same disc
    for number in range(300):  # 20 x 15 spots 0.35 m apart, none touching the next
        radius = 0.06 + 0.03 * (number % 4)
        x, z = 16.6 + 0.35 * (number % 20), -2.45 + 0.35 * (number // 20)
        rock(stage, place, f"rock{number}", (x, floor + radius / 3, z), radius)
    rock(stage, place, "rock_float", (20.0, floor + 0.3 + 0.2, 4.5), 0.2)
    rock(stage, place, "rock_big", (17.0, floor + 0.1, 4.6), 0.3)
    box(stage, place, "crate_in_rock", (0.4, 0.4, 0.4), (17.2, floor, 4.4))
    sky = UsdGeom.Xform.Define(stage, f"/{place}/Objects/sky")
    sky.GetPrim().CreateAttribute("score:kind", Sdf.ValueTypeNames.String).Set("light")
    dome = trimesh.creation.icosphere(subdivisions=2, radius=300.0)
    mesh = UsdGeom.Mesh.Define(stage, f"{sky.GetPath()}/Dome")
    mesh.CreatePointsAttr(Vt.Vec3fArray.FromNumpy(np.asarray(dome.vertices, np.float32)))
    mesh.CreateFaceVertexCountsAttr([3] * len(dome.faces))
    mesh.CreateFaceVertexIndicesAttr(Vt.IntArray.FromNumpy(np.asarray(dome.faces, np.int32).reshape(-1)))
    for side, x in (("near", 18.0), ("far", 240.0)):  # 12 m and 234 m past the reached objects (wall2 at x 5.5)
        rock(stage, place, f"rock_{side}_a", (x, 3.0, -8.0), 1.0)
        rock(stage, place, f"rock_{side}_b", (x + 0.5, 3.0, -8.0), 1.0)
    stage.GetRootLayer().Save()
    place_build.ground(folder, "far_shore", 10.0, (320.0, -0.02, 0.0))


def room(folder, cut, hood=0.0, length=4.0, roof=True, porch=0.0):
    """A room 4 m wide and `length` deep inside, 2.5 m high, on a ground disc: four walls 0.2 m thick, a roof slab
    (unless not `roof`), a doorway 1.0 x 2.1 m in its back wall filled by its shut door; `cut` leaves its front wall out
    (the concept's section, built); `hood` metres of the door's own frame (two cheeks and a head) standing out of the
    wall; `porch` metres of roof standing out past the back wall over the ground (a porch outside the door)."""
    folder.mkdir()
    concept = folder / "concept.png"
    Image.new("RGB", (8, 8)).save(concept)
    place_build.start(folder / "place", "room", concept)
    folder = folder / "place"
    place_build.ground(folder, "ground", 6.0, (0.0, -0.02, 0.0))
    stage, place = place_build.opened(folder)
    box(stage, place, "wall_left", (0.2, 2.5, length + 0.4), (-2.2, 0.0, -2.2))
    box(stage, place, "wall_right", (0.2, 2.5, length + 0.4), (2.0, 0.0, -2.2))
    back = box(stage, place, "wall_back", (1.5, 2.5, 0.2), (-2.0, 0.0, -2.2))
    for name, size, middle in (("right", (1.5, 2.5, 0.2), (2.5, 0.0, 0.0)), ("lintel", (1.0, 0.4, 0.2), (1.25, 1.05, 0.0))):
        block = UsdGeom.Cube.Define(stage, f"{back.GetPath()}/{name}")
        block.CreateSizeAttr(1.0)
        block.AddTranslateOp().Set(Gf.Vec3d(*middle))
        block.AddScaleOp().Set(Gf.Vec3f(*size))
    door = box(stage, place, "door", (0.98, 2.09, 0.05), (-0.49, 0.0, -2.125))
    for name, size, middle in (("cheek_left", (0.1, 2.2, hood), (-0.55, 0.0, -hood / 2 - 0.075)),
                               ("cheek_right", (0.1, 2.2, hood), (0.55, 0.0, -hood / 2 - 0.075)),
                               ("head", (1.2, 0.1, hood), (0.0, 1.1, -hood / 2 - 0.075))) if hood else ():
        block = UsdGeom.Cube.Define(stage, f"{door.GetPath()}/{name}")
        block.CreateSizeAttr(1.0)
        block.AddTranslateOp().Set(Gf.Vec3d(*middle))
        block.AddScaleOp().Set(Gf.Vec3f(*size))
    if not cut:
        box(stage, place, "wall_front", (4.4, 2.5, 0.2), (-2.2, 0.0, length - 2.0))
    if roof:
        box(stage, place, "roof", (4.4, 0.2, length + 0.4 + porch), (-2.2, 2.5, -2.2 - porch))
    stage.GetRootLayer().Save()
    return folder


def joined_room(folder):
    """The cut room (its front wall left out) with that open front a joined doorway (place.json `joins`): the place
    joined there closes it."""
    folder = room(folder, True)
    record = place_build.record_of(folder)
    record["joins"] = {"front": {"middle": [0.0, 0.0, 2.1], "inward": [0.0, 0.0, -1.0], "wide": 4.4, "sill": 0.0,
                                 "head": 2.5, "to": "street"}}
    place_build.write_record(folder, record)
    return folder


def shop(folder, crates=False):
    """A shop's room 4 x 4 m inside as one structure (walls, roof) on a ground disc, a window 1.2 m wide from 0.3 to
    2.0 m left open in its front wall, a glassless gap; in an outside place it is a room of a structure. `crates`:
    nine crates 2 m high standing through the room (its furniture, props)."""
    folder.mkdir()
    concept = folder / "concept.png"
    Image.new("RGB", (8, 8)).save(concept)
    place_build.start(folder / "place", "shop", concept)
    folder = folder / "place"
    place_build.ground(folder, "ground", 6.0, (0.0, -0.02, 0.0))
    stage, place = place_build.opened(folder)
    holder = UsdGeom.Xform.Define(stage, f"/{place}/Objects/shop").GetPrim()
    holder.CreateAttribute("score:role", Sdf.ValueTypeNames.String).Set("structure")
    for name, size, low in (("left", (0.2, 2.5, 4.4), (-2.2, 0.0, -2.2)), ("right", (0.2, 2.5, 4.4), (2.0, 0.0, -2.2)),
                            ("back", (4.4, 2.5, 0.2), (-2.2, 0.0, -2.2)), ("roof", (4.4, 0.2, 4.4), (-2.2, 2.5, -2.2)),
                            ("front_left", (2.2, 2.5, 0.2), (-2.2, 0.0, 2.0)), ("front_right", (1.0, 2.5, 0.2), (1.2, 0.0, 2.0)),
                            ("sill", (1.2, 0.3, 0.2), (0.0, 0.0, 2.0)), ("lintel", (1.2, 0.5, 0.2), (0.0, 2.0, 2.0))):
        block = UsdGeom.Cube.Define(stage, f"{holder.GetPath()}/{name}")
        block.CreateSizeAttr(1.0)
        block.AddTranslateOp().Set(Gf.Vec3d(*(np.asarray(low) + np.asarray(size) / 2)))
        block.AddScaleOp().Set(Gf.Vec3f(*size))
    stage.GetRootLayer().Save()
    if crates:
        stage, place = place_build.opened(folder)
        for number, (x, z) in enumerate((x, z) for x in (-1.6, -0.4, 0.8) for z in (-1.6, -0.4, 0.8)):
            box(stage, place, f"crate{number}", (0.5, 2.0, 0.5), (x, 0.0, z))
        stage.GetRootLayer().Save()
    return folder


def seated_rooms(folder, cut):
    """The room (its front wall left out when `cut`) without its back wall, and a neighbour place, `hall`, holding
    that wall with the doorway the room's door fills and, behind it, an alcove (a slab 0.1 m high, two side walls and a
    roof) standing on the room's ground, and a post 150 m off; both seated in one area, turned a quarter and shifted alike. (room, hall)."""
    folder.mkdir()
    own = room(folder / "room", cut)
    place_build.remove(own, "wall_back")
    hall = room(folder / "hall", False)
    for name in ("wall_left", "wall_right", "wall_front", "roof", "door", "ground"):
        place_build.remove(hall, name)
    stage, place = place_build.opened(hall)
    for name, size, low in (("alcove_floor", (2.4, 0.1, 2.0), (-1.2, 0.0, -4.7)),  # past the door's FIT_DEPTH
                            ("alcove_left", (0.2, 2.5, 2.5), (-1.4, 0.0, -4.7)),
                            ("alcove_right", (0.2, 2.5, 2.5), (1.2, 0.0, -4.7)),
                            ("alcove_roof", (2.8, 0.2, 2.5), (-1.4, 2.5, -4.7)),
                            ("far_post", (0.5, 3.0, 0.5), (150.0, 0.0, 0.0))):  # past the room's sight
        box(stage, place, name, size, low).CreateAttribute("score:role", Sdf.ValueTypeNames.String).Set("structure")
    stage.GetRootLayer().Save()
    seat = np.identity(4)
    seat[:3, :3], seat[:3, 3] = [[0.0, 0.0, 1.0], [0.0, 1.0, 0.0], [-1.0, 0.0, 0.0]], [3.0, 0.0, 1.0]
    for folder in (own, hall):
        record = place_build.record_of(folder)
        record["seat"] = {"area": "block", "matrix": seat.T.reshape(-1).tolist(), "from": "the test's"}
        place_build.write_record(folder, record)
    return own, hall


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
                                              (-1.6, -0.4, 2.1, 2.5), (0.4, 1.6, 2.1, 2.5), (3.5, 4.0, 0, 2.5),
                                              (2.5, 3.5, 2.1, 2.5)])
    lattice_gate(stage, place, "door_lattice", 5.5, 2.5, 3.5, 2.1)  # fills its 1.0 x 2.1 m opening, bars and gaps
    box(stage, place, "door_small", (0.05, 2.1, 0.8), (5.475, 0.0, -1.4))
    box(stage, place, "door_big", (0.05, 2.4, 1.6), (5.375, 0.0, 0.2))
    box(stage, place, "blocker", (2.4, 1.0, 1.1), (-1.2, 0.0, -1.4))
    box(stage, place, "hatch_free", (1.0, 2.0, 0.05), (2.5, 0.0, 3.0))
    box(stage, place, "bulkhead", (3.0, 2.8, 0.2), (-4.5, 0.0, 2.3))
    box(stage, place, "crate_ok", (0.5, 0.5, 0.5), (4.0, 0.0, 1.0))
    box(stage, place, "rock_sunk", (0.6, 0.6, 0.6), (-2.0, -0.32, 5.6))  # bedded 30 cm in the ground
    box(stage, place, "crate_float", (0.5, 0.5, 0.5), (-1.0, 0.4, -4.5))
    box(stage, place, "crate_a", (0.5, 0.5, 0.5), (1.5, 0.0, -3.5))
    box(stage, place, "crate_b", (0.5, 0.5, 0.5), (1.9, 0.0, -3.5))
    desk(stage, place)
    box(stage, place, "monitor", (0.5, 0.35, 0.1), (-2.65, 1.5, -2.8))
    box(stage, place, "tipper", (0.4, 0.4, 0.4), (-3.3, 0.75, -2.9))
    box(stage, place, "panel", (0.6, 0.4, 0.05), (2.0, 0.5, 1.0))
    hutch(stage, place)
    box(stage, place, "pad", (0.3, 0.03, 0.2), (0.55, 0.75, 4.55))  # on the hutch's top, inside its box
    floor = ready.levels_under(ready.Place(stage, place), "ground", (-5.5, 0.0))[-1]
    person(stage, place, "person_ok", (-5.5, floor, 0.0))
    place_build.rested(stage, f"/{place}/Objects/person_ok", (-5.5, floor, 0.0), (0, 0, 0), (1, 1, 1))
    person(stage, place, "person_float", (-5.5, floor + 0.3, 1.5))
    person(stage, place, "person_broken", (-5.5, floor, -1.5), without=("Head", "RightHand"))
    person(stage, place, "person_torn", (-5.5, floor, -3.0), torn=True)
    person(stage, place, "walker", (-5.5, floor, 3.0), stepping=True)
    person(stage, place, "walker_float", (-5.5, floor + 0.3, 4.3), stepping=True)
    hatch(stage, place, "hatch_round", (-6.5, 0.0, -6.0), 1.0, 1.0)
    hatch(stage, place, "hatch_squared", (-6.5, 0.0, 6.0), 1.0, 1.0)
    decal = UsdGeom.Xform.Define(stage, f"/{place}/Objects/decal").GetPrim()
    decal.CreateAttribute("score:kind", Sdf.ValueTypeNames.String).Set("model")
    stage.GetRootLayer().Save()
    place_build.tube(folder, "lock_round", 1.0, 1.0, (-6.5, 0.0, -6.0), (0.0, 90.0, 0.0), cap_door="hatch_round")
    place_build.tube(folder, "lock_squared", 1.0, 1.0, (-6.5, 0.0, 6.0), (0.0, 90.0, 0.0), cap=[1.0, 1.0])
    rock_field(folder)
    return folder


def hatched(folder):
    """A wall 14 m wide (past the ground's edge) with a hatch 1.1 m across in it (its sill 0.26 m up, its top 1.35 m), its leaf a door, on a
    ground disc: the walkers' floor either side joined through it (one piece) or not; (piece one side, the other)."""
    folder.mkdir()
    concept = folder / "concept.png"
    Image.new("RGB", (8, 8)).save(concept)
    place_build.start(folder / "place", "hull", concept)
    folder = folder / "place"
    place_build.ground(folder, "ground", 6.0, (0.0, -0.02, 0.0))
    stage, place = place_build.opened(folder)
    for name, size, low in (("hull_left", (6.45, 2.5, 0.2), (-7.0, 0.0, -0.1)), ("hull_right", (6.45, 2.5, 0.2),
                            (0.55, 0.0, -0.1)), ("hull_sill", (1.1, 0.26, 0.2), (-0.55, 0.0, -0.1)),
                            ("hull_head", (1.1, 1.15, 0.2), (-0.55, 1.35, -0.1))):
        box(stage, place, name, size, low).CreateAttribute("score:role", Sdf.ValueTypeNames.String).Set("structure")
    box(stage, place, "hatch", (1.1, 1.09, 0.05), (-0.55, 0.26, -0.025))
    stage.GetRootLayer().Save()
    return folder


def joined_through(folder):
    """Whether the walkers' floor 1 m either side of the hatch is one piece, every door open (the walkway check's)."""
    stage, place = place_build.opened(folder)
    grid, cells, heights, standing, pieces = ready.walkers_floor(ready.Place(stage, place))
    sides = [ready.spans_near(grid, cells, heights, standing, np.array([0.0, 0.0, way])) for way in (-1.0, 1.0)]
    return all(len(side) for side in sides) and pieces[sides[0][0]] == pieces[sides[1][0]]


def adopted_settle_mass():
    """An adopted prop (#155) settles with the mass its asset authors in its MuJoCo physics variant, times its laid
    scale cubed, the stage's own choice of variant put back after."""
    stage = Usd.Stage.CreateInMemory()
    prop = UsdGeom.Xform.Define(stage, "/p/Objects/prop_1")
    prop.AddScaleOp().Set(Gf.Vec3f(2.0, 2.0, 2.0))
    UsdGeom.Mesh.Define(stage, "/p/Objects/prop_1/geo")
    variants = prop.GetPrim().GetVariantSets().AddVariantSet("MuJoCo")
    for name in ("Disabled", "Enabled"):
        variants.AddVariant(name)
    variants.SetVariantSelection("Enabled")
    with variants.GetVariantEditContext():
        UsdPhysics.MassAPI.Apply(stage.OverridePrim("/p/Objects/prop_1/geo")).CreateMassAttr(1.5496)
    variants.SetVariantSelection("Disabled")
    laid = type("Laid", (), {"prims": {"prop_1": prop.GetPrim()}})()
    assert np.isclose(ready.settle_mass(laid, "prop_1"), 1.5496 * 8)
    assert laid.prims["prop_1"].GetVariantSets().GetVariantSelection("MuJoCo") == "Disabled"


def adopted_settle_colliders():
    """An adopted bench (#155), two blocks 0.3 m apart in one collision mesh, collides by its triangles in its default
    physics variant and by their convex hull in its MuJoCo one: a block laid over its gap is held in the settle by the
    hull's top under it, while the bench drawn, its variant put back, still shows the gap."""
    stage = Usd.Stage.CreateInMemory()
    blocks = trimesh.util.concatenate([trimesh.creation.box([0.5, 0.5, 0.5]).apply_translation([x, 0.25, 0.0])
                                       for x in (-0.4, 0.4)])
    bench = UsdGeom.Xform.Define(stage, "/p/Objects/bench").GetPrim()
    bench.CreateAttribute("score:library", Sdf.ValueTypeNames.String).Set("model/simready_bench_a01@1")
    mesh = UsdGeom.Mesh.Define(stage, "/p/Objects/bench/geo")
    mesh.CreatePointsAttr(Vt.Vec3fArray.FromNumpy(np.asarray(blocks.vertices, dtype=np.float32)))
    mesh.CreateFaceVertexCountsAttr([3] * len(blocks.faces))
    mesh.CreateFaceVertexIndicesAttr(Vt.IntArray.FromNumpy(np.asarray(blocks.faces, dtype=np.int32).reshape(-1)))
    UsdPhysics.CollisionAPI.Apply(mesh.GetPrim())
    UsdPhysics.MassAPI.Apply(mesh.GetPrim()).CreateMassAttr(30.0)
    UsdPhysics.MeshCollisionAPI.Apply(mesh.GetPrim())
    variants = bench.GetVariantSets().AddVariantSet("MuJoCo")
    for name, approximation in (("Enabled", UsdPhysics.Tokens.convexHull), ("Disabled", UsdPhysics.Tokens.none)):
        variants.AddVariant(name)
        variants.SetVariantSelection(name)
        with variants.GetVariantEditContext():
            UsdPhysics.MeshCollisionAPI(stage.OverridePrim("/p/Objects/bench/geo")).CreateApproximationAttr(
                approximation)
    box(stage, "p", "block", (0.1, 0.1, 0.1), (-0.05, 0.5, -0.05))
    laid = ready.Place(stage, "p")
    colliders = ready.settle_colliders(laid)
    statics = ready.statics_near(laid, "block", colliders)
    under = trimesh.Trimesh(statics.reshape(-1, 3), np.arange(len(statics) * 3).reshape(-1, 3), process=False)
    held = under.ray.intersects_any([[0.0, 0.55, 0.0]], [[0.0, -1.0, 0.0]])
    drawn = laid.meshes["bench"].ray.intersects_any([[0.0, 0.55, 0.0]], [[0.0, -1.0, 0.0]])
    assert list(colliders) == ["bench"] and held[0] and not drawn[0], (list(colliders), held, drawn)
    assert laid.prims["bench"].GetVariantSets().GetVariantSelection("MuJoCo") == "Disabled"


def instanced_solid():
    """An adopted desk (#155) whose top, a cube 1.2 x 0.05 x 0.6, stands under an instanceable prim (as a SimReady
    model lays its shapes from its instances' payload) reads as that solid."""
    stage = Usd.Stage.CreateInMemory()
    cube = UsdGeom.Cube.Define(stage, "/Prototypes/top/geo")
    cube.CreateSizeAttr(1.0)
    cube.AddScaleOp().Set(Gf.Vec3f(1.2, 0.05, 0.6))
    UsdGeom.Xform.Define(stage, "/p/Objects/desk").AddTranslateOp().Set(Gf.Vec3d(0.0, 0.75, 0.0))
    shared = UsdGeom.Xform.Define(stage, "/p/Objects/desk/Geometry/top").GetPrim()
    shared.GetReferences().AddInternalReference("/Prototypes/top")
    shared.SetInstanceable(True)
    solid = ready.solid_of(stage.GetPrimAtPath("/p/Objects/desk"))
    assert solid is not None and np.allclose(solid.bounds, [[-0.6, 0.725, -0.3], [0.6, 0.775, 0.3]]), \
        None if solid is None else solid.bounds


def test_every_planted_physics_fault_is_told_by_name(tmp_path, monkeypatch):
    hull = hatched(tmp_path / "hatched")
    place_build.door(hull, "hatch")
    assert not joined_through(hull)  # a standing walker's head meets the hatch's top
    place_build.door(hull, "hatch", crouch=True)
    assert joined_through(hull)  # crouched through, over its sill
    seen, roofless = "open to the outside", "no roof"
    for name, made, kind, told in (("closed", lambda folder: room(folder, False), "inside", None),
                                   ("cut", lambda folder: room(folder, True), "inside", seen),
                                   ("arcade", lambda folder: room(folder, True), "outside", None),
                                   ("shop", shop, "outside", seen),
                                   ("cluttered", lambda folder: shop(folder, crates=True), "outside", seen),
                                   ("porch", lambda folder: room(folder, False, porch=2.0), "inside", None),
                                   ("joined", joined_room, "inside", None),
                                   ("hooded", lambda folder: room(folder, False, hood=0.6), "inside", None),
                                   ("hall", lambda folder: room(folder, False, length=48.0), "inside", None),
                                   ("hall_cut", lambda folder: room(folder, True, length=48.0), "inside", seen),
                                   ("roofless", lambda folder: room(folder, False, roof=False), "inside", roofless),
                                   ("yard", lambda folder: room(folder, False, roof=False), "outside", None)):
        folder = made(tmp_path / name)
        place_build.kind(folder, kind)
        stage, place = place_build.opened(folder)
        shell = ready.Place(stage, place)
        record = place_build.record_of(folder)
        gaps, seeing = ready.open_faults(shell, record["kind"] == "outside", record.get("joins"))
        assert (seeing > 0) == bool(told) and all(fault["fault"] == told for fault in gaps), (name, gaps)
    for cut in (False, True):
        own, hall = seated_rooms(tmp_path / f"seated_{cut}", cut)
        alone, among = ready.check(own, settle=False), ready.check(own, settle=False, neighbours={"hall": hall})
        whole = ready.check(room(tmp_path / f"whole_{cut}", cut), settle=False)
        assert "door not in an opening" in alone["counts"] and alone["open"], alone
        assert among["counts"] == whole["counts"] and bool(among["open"]) == cut, (cut, among, whole)
        lent = ready.seated_among(own, {"hall": hall})[2]
        assert "hall__wall_back" in lent and "hall__far_post" not in lent, lent
    closed = ready.Place(*place_build.opened(tmp_path / "closed" / "place"))  # 50 looks cast 7 at a time
    origins = np.tile([0.3, 1.2, 0.4], (50, 1)) + np.linspace(0.0, 1.0, 50)[:, None] * [0.5, 0.0, 0.5]
    ways = np.array([[np.cos(turn), 0.3, np.sin(turn)] for turn in np.linspace(0.0, 6.0, 50)])
    whole_hits, whole_met = closed.hits(origins, ways), ready.met(closed, origins, ways, 40.0)
    widest, casting = [], ready.cast
    monkeypatch.setattr(ready, "CAST_AT_ONCE", 7)
    monkeypatch.setattr(ready, "cast", lambda triangles, origins, *rest, **given: (
        widest.append(len(origins)), casting(triangles, origins, *rest, **given))[1])
    batched_hits, batched_met = closed.hits(origins, ways), ready.met(closed, origins, ways, 40.0)
    monkeypatch.undo()
    assert max(widest) <= 7 and np.array_equal(batched_met, whole_met) and whole_met.all(), (widest, batched_met)
    assert all(np.allclose(np.sort(one, axis=0), np.sort(two, axis=0)) for one, two in zip(whole_hits, batched_hits)), \
        (whole_hits[1], batched_hits[1])
    ball = trimesh.creation.icosphere(subdivisions=4)  # 5,120 faces: a large cast's ray structure freed at once
    monkeypatch.setattr(ready, "COLLECTED", 5_000)
    gc.collect()
    gc.disable()
    try:
        ready.cast(ball.triangles, np.zeros((4, 3)), np.eye(3)[[0, 1, 2, 0]])
        left = [kept for kept in gc.get_objects() if isinstance(kept, trimesh.Trimesh) and kept is not ball
                and len(kept.faces) == 5_120]
    finally:
        gc.enable()
        monkeypatch.undo()
    assert not left, left
    tilt = 4e-6  # a face lying along the look (embree meets it, its plane and the look meet nowhere), a wall past it
    lying = np.array([[[0.0, 0.5 - tilt, -1.0], [2.0, 0.5 + tilt, -1.0], [1.0, 0.5, 1.0]]])
    walled = np.concatenate([lying, trimesh.creation.box((0.2, 3.0, 4.0)).apply_translation((3.0, 1.5, 0.0)).triangles])
    looks = np.array([[0.0, 0.5, 0.0], [0.0, 0.5, 0.0]]), np.array([[1.0, 0.0, 0.0], [-1.0, 0.0, 0.0]])
    first, every = ready.cast(walled, *looks, multiple_hits=False), ready.cast(walled, *looks)
    assert first[1].tolist() == [0] and np.allclose(first[0], [[2.9, 0.5, 0.0]]) and sorted(every[1].tolist()) == [0, 0], \
        (first, every)
    folder = planted(tmp_path)
    coarse = trimesh.creation.box(extents=(2.0, 2.0, 2.0))  # a face's middle half a metre off, a corner 0.6 off its own
    corner = np.array([1.0, 1.0, 1.0]) + 0.6 / np.sqrt(3.0)
    assert abs(ready.nearest_to_surface(coarse, np.array([[0.0, 1.5, 0.0], corner])) - 0.5) < 1e-6
    dense, weighed = trimesh.creation.icosphere(subdivisions=5), []  # 20,480 faces, every point 0.5 m off it
    off = trimesh.creation.icosphere(subdivisions=2).vertices * 1.5
    held_pairs = trimesh.triangles.closest_point
    for module, name in ((trimesh.triangles, "closest_point"), (trimesh.proximity, "_corresponding")):
        monkeypatch.setattr(module, name,
                            lambda triangles, points: weighed.append(len(points)) or held_pairs(triangles, points))
    assert abs(ready.nearest_to_surface(dense, off, pairs=2000) - 0.5) < 2e-3 and 0 < max(weighed) <= 2000, weighed
    for module, name in ((trimesh.triangles, "closest_point"), (trimesh.proximity, "_corresponding")):
        monkeypatch.setattr(module, name, held_pairs)
    ground = ready.solids(folder)
    assert "wall" in ground and "door" in ground and "sky" not in ground and ground["wall"].shape[1:] == (3, 3), \
        sorted(ground)
    laid = ready.Place(*place_build.opened(folder))
    foot = ready.lowest_points(laid.meshes["rock0"]) + [0.0, ready.RAY_START, 0.0]
    reached, _ = laid.triangles_in(*ready.ray_box(foot, np.tile([0.0, -1.0, 0.0], (len(foot), 1))))
    every = sum(len(laid.meshes[name].faces) for name in laid.names)
    assert len(reached) < every / 20, (len(reached), every)
    monitor = ready.on(folder, "monitor", "desk")
    panel = ready.on(folder, "panel", "wall:wall", height=1.2)
    stage, place = place_build.opened(folder)  # a deck of blocks (a structure) 0.4 m high before the wall
    box(stage, place, "dais", (1.0, 0.4, 0.6), (-3.0, 0.0, 0.15)).CreateAttribute(
        "score:role", Sdf.ValueTypeNames.String).Set("structure")
    box(stage, place, "plaque", (0.3, 0.2, 0.05), (-2.65, 0.6, 0.5))
    stage.GetRootLayer().Save()
    plaque = ready.on(folder, "plaque", "wall:wall", height=1.0)
    stage, place = place_build.opened(folder)  # a stick whose middle stands past the desk's edge, a quarter over it
    box(stage, place, "stick", (0.4, 0.2, 0.1), (-1.95, 1.5, -2.8))
    console = box(stage, place, "console", (0.3, 0.3, 0.3), (6.0, 0.0, 6.0))
    console.GetAttribute("score:library").Set("model/pilot_console_1.airlock@1")  # an airlock's console, no door
    stage.GetRootLayer().Save()
    stick = ready.on(folder, "stick", "desk")
    assert abs(stick["at"][1] - (0.75 + 0.1)) < 0.02, stick
    assert ready.role_of(place_build.opened(folder)[0].GetPrimAtPath(f"/{place}/Objects/console")) == "prop"
    stage, place = place_build.opened(folder)  # a hatch modelled lying down, stood up by its turn
    lying = box(stage, place, "hatch_lying", (1.0, 0.05, 2.0), (8.0, 0.0, 8.0))
    UsdGeom.Xformable(lying).GetOrderedXformOps()[1].Set(Gf.Vec3f(-90.0, 0.0, 0.0))
    stage.GetRootLayer().Save()
    stage, place = place_build.opened(folder)
    _, axes, half = ready.frame_of(ready.Place(stage, place), "hatch_lying")
    assert abs(half[1] - 1.0) < 1e-3 and axes[1][1] > 0.99, (axes, half)  # 2 m tall, standing
    assert abs(plaque["at"][1] - (0.4 + 1.0 + 0.1)) < 0.03, plaque  # over the deck, not the ground under it
    assert abs(monitor["at"][1] - (0.75 + 0.175)) < 0.01, monitor  # its bottom on the desk's top
    assert abs(panel["at"][2] - (0.1 + 0.025)) < 0.01 and abs(panel["at"][1] - 1.4) < 0.03, panel
    walk, metres = ready.route(folder, [(4.25, 0.0, 0.7), (4.25, 0.0, 2.6)])
    walk = np.asarray(walk)
    along = np.linspace(0.0, 1.0, 20)[:, None]
    sampled = np.concatenate([start + (end - start) * along for start, end in zip(walk[:-1], walk[1:])])
    clear_of_crate = (sampled[:, 0] < 4.0 - 0.3) | (sampled[:, 0] > 4.5 + 0.3) | (sampled[:, 2] < 1.0 - 0.3) \
        | (sampled[:, 2] > 1.5 + 0.3)
    assert clear_of_crate.all() and metres > 1.9, (walk.tolist(), metres)
    by_way, _ = ready.route(folder, [(4.25, 0.0, 0.7), (3.0, 0.0, 2.2), (4.25, 0.0, 2.6)])
    assert min(np.hypot(x - 3.0, z - 2.2) for x, _, z in by_way) < 0.35, by_way  # the spot it is sent through
    try:
        ready.route(folder, [(4.25, 0.0, 0.7), (4.25, 2.0, 2.6)])
        raise AssertionError("a spot with no floor under it was routed to")
    except place_build.Refused:
        pass
    terrain = trimesh.creation.box([3000.0, 1.0, 3000.0])
    terrain = trimesh.Trimesh(*trimesh.remesh.subdivide_to_size(terrain.vertices, terrain.faces, 50.0), process=False)
    near = ready.near_ground(terrain, np.array([-5.0, 0.0, -5.0]), np.array([5.0, 2.0, 5.0]))
    assert len(near.faces) < len(terrain.faces) / 100 and np.abs(near.bounds[:, [0, 2]]).max() < 5 + 20 + 50
    summary = ready.check(folder)
    found = json.loads(pathlib.Path(summary["file"]).read_text())["objects"]
    told = {name: {fault["fault"] for fault in faults} for name, faults in found.items()}
    print(json.dumps(summary))
    for name in ("wall", "desk", "monitor", "panel", "crate_ok", "rock_sunk", "bulkhead", "person_ok", "walker",
                 "ground", "field", "sky", "rock_far_a", "rock_far_b", "far_shore",
                 *(f"rock{number}" for number in range(300))):
        assert name not in told, (name, found.get(name))
    assert "floating" in told["rock_float"] and "penetration" in told["crate_in_rock"], \
        (found.get("rock_float"), found.get("crate_in_rock"))
    assert "penetration" in told["rock_near_a"] and "penetration" in told["rock_near_b"], found.get("rock_near_a")
    assert {name for name, role in laid.roles.items() if role == "scenery"} == {"rock_far_a", "rock_far_b", "far_shore"}
    assert told["door"] == {"walkway"}, found["door"]
    stage, place = place_build.opened(folder)
    laid = ready.Place(stage, place)
    for joined, kept in (({"door": {"inward": [0.0, 0.0, 1.0], "from": "the door leaf door"}}, 1),  # its far side the
                         ({"door": {"inward": [0.0, 0.0, 1.0], "from": "the doorway door as laid"}}, 2),  # neighbour's
                         (None, 2)):
        sides = {name: spot for name, spot in ready.walkway_targets(laid, joined)[0].items() if name.startswith("door (")}
        assert len(sides) == kept and (kept == 2 or all(spot[2] > 0.0 for spot in sides.values())), (joined, sides)
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
    assert "door does not fit" not in told.get("door_lattice", ()), found.get("door_lattice")
    assert any(fault.get("over", 0) > 0.15 for fault in found["door_big"] if fault["fault"] == "door does not fit"), \
        found["door_big"]
    assert {fault.get("foot") for fault in found["person_float"] if fault["fault"] == "person floating"} \
        == {"left", "right"}, found["person_float"]
    assert {fault.get("foot") for fault in found["walker_float"] if fault["fault"] == "person floating"} \
        == {"right"}, found["walker_float"]  # its planted foot, the left one stepping 10 cm up
    assert any(set(fault.get("missing", ())) == {"head", "right hand"} for fault in found["person_broken"]), \
        found["person_broken"]
    assert any(fault.get("torn", 0) > 0.5 for fault in found["person_torn"]), found["person_torn"]
    assert "door does not fit" not in told.get("hatch_round", ()), found["hatch_round"]
    assert "door does not fit" in told["hatch_squared"], found.get("hatch_squared")
    reach = ready.reach  # the check's memory stays bounded: a surface read a chunk at a time, its points the same
    small = trimesh.creation.icosphere(2)
    count = int(np.ceil(small.area * reach.SAMPLES_PER_M2))
    chunked = np.vstack([points for points, _ in reach.surface_chunks(small, chunk=999)])[:count]
    assert np.array_equal(chunked, trimesh.sample.sample_surface(small, count, seed=0)[0])
    monkeypatch.setattr(reach, "CHUNK", 200_000)
    plate = trimesh.Trimesh([[-40.0, 0.0, -40.0], [40.0, 0.0, -40.0], [40.0, 0.0, 40.0], [-40.0, 0.0, 40.0]],
                            [[0, 2, 1], [0, 3, 2]])  # 6,400 m², 6.6 million points: 160 MB held whole
    grid = reach.Grid((-2.0, -2.0, 2.0, 2.0))
    tracemalloc.start()
    spans = reach.spans(*reach.floor_points(grid, [plate], lambda middles: np.full(len(middles), np.nan)))
    clear = reach.clear_overhead(grid, [plate], *spans)
    held = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    assert held < 64 * 2 ** 20 and len(spans[0]) == grid.shape[0] * grid.shape[1] and clear.all(), \
        (held, len(spans[0]), grid.shape)
    far = ready.Place(*place_build.opened(folder))  # a post 300 m off stretches the walkers' grid past the budget
    far.meshes["far_post"] = trimesh.creation.box([0.3, 2.0, 0.3]).apply_translation([300.0, 1.0, 300.0])
    far.roles["far_post"], far.names = "structure", [*far.names, "far_post"]
    monkeypatch.setattr(ready, "MEMORY", ready.in_use() + 2 ** 29)
    try:
        ready.walkers_floor(far)
        raise AssertionError("a walkers' grid past the memory budget was read")
    except place_build.Refused as why:
        assert "walkers' grid" in str(why) and "far_post" in str(why), str(why)
    largest = 1000 * ready.PLATE_BYTES + ready.settle_arena()  # the settle runs as many models as fit, or refuses
    monkeypatch.setattr(ready, "MEMORY", ready.in_use() + int(2.5 * largest))
    assert ready.settle_workers({"big": 1000, "small": 10, "tiny": 5}, 0) == 2
    monkeypatch.setattr(ready, "MEMORY", ready.in_use() + largest // 2)
    try:
        ready.settle_workers({"big": 1000, "small": 10}, 0)
        raise AssertionError("a settle model past the memory budget was run")
    except place_build.Refused as why:
        assert "big" in str(why), str(why)
    adopted_settle_mass()
    adopted_settle_colliders()
    instanced_solid()
    if summary["settle"].startswith("not run"):
        print("skipped: the MuJoCo settle (" + summary["settle"] + ")")
        return
    assert "unstable" in told["tipper"] and "unstable" not in told.get("crate_ok", ()) \
        and "unstable" not in told.get("pad", ()), (found["tipper"], found.get("pad"))
