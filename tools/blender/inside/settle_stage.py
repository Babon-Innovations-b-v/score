"""Runs inside Blender (`session.py batch`): let a place's loose objects come to rest on its ground, as real objects do.

    python3 tools/blender/session.py batch tools/blender/inside/settle_stage.py -- <stage.usda> <job.json> <out.json>

job.json: {"loose": [object name, ...], "lift": {object name: metres}, "ignore": [object name, ...], "start": {object
name: 4 x 4}, "under": {object name: [object name, ...]}} (ignore: glowing parts, left out of the statics; start: the
motion, stage frame, row by row, that stands an object upright before its drop, tools/usd/settle.py's upright_start;
under: the loose objects it is stacked on, which it meets as it meets a static: a crate on a crate). Beside the stage,
PARTS_FILE (when the settle stage wrote one, tools/usd/convex_parts.py): {object name: [[corner, ...], ...]}, a
hollow object's convex parts in its drawn mesh's own frame. The stage is brought in whole; its ground
(`Ground`, or a plane at y = 0 in a room, which has none) and every object not named loose are static (passive rigid bodies, their own triangles as their collision), but the sky (NOT_SOLID) and what lies past every
loose object's reach (NEAR).
Each loose object is lifted by its `lift` (just clear of the ground, from tools/usd/settle.py), given its convex hull
as collision and its weight at the middle of its surface (the resting check's weight), and dropped. A hollow object
(a crate, a tray, a bin, a shelf: one with parts) collides by its convex parts instead, so what is stacked in it
meets its floor, not its hull's top: each part a light body of its own (PART_MASS) glued to the object by a fixed
joint, the parts that lie against each other kept from meeting by a joint that holds nothing (glued_parts). Blender 5.0.1's own
compound body was tried first and walks: an open crate of five box children with its weight at its middle slid 21 cm
and turned 0.3 rad in 10 s on a triangle ground while one hull stood still (2026-10-26). Loose objects
collide with the ground and the static objects, not with each other: a convex hull spans a hollow, so one hull section
lying on a panel rested on its hull while the drawn hull stood 4 cm clear (2026-10-08), and Bullet's own triangle
collision for moving bodies dropped pieces through the ground. Two loose objects that come to rest inside each other
are reported (`overlaps`). A loose object that starts inside a static one (a layout fault) would be thrown out of it,
so it collides with the ground alone and is reported. The simulation runs SECONDS under gravity with damping, so nothing bounces off or keeps rolling, and each
object's last pose is taken.

out.json: {"objects": {object name: {"motion": 4 x 4, "moving": metres a second at the end, "inside": [static objects
it starts in]}}, "overlaps": [[name, name], ...]}, the motion is how the object moved from as laid to at rest, in the stage's own frame (y up), row by row
(column vectors): its settled matrix is motion @ its laid matrix.
"""
import json
import pathlib
import sys

import bpy
from mathutils import Matrix, Vector

FPS = 30
SECONDS = 30
GRAVITY = 9.81  # the pose an object rests in does not depend on g; the Moon's 1.62 only takes longer to get there
FRICTION = 0.9
DAMPING_LINEAR = 0.6
DAMPING_ANGULAR = 0.95
# Bullet's collision groups: each loose object has one of its own (1 up), which the ground and the static objects are
# also in, so it meets them and no other loose object; group 0 holds the ground alone, for a loose object laid inside a
# static one.
GROUPS = 20
MARGIN = 0.004
# A hollow object's convex part weighs this (the object 1): light, so its weight stays at the middle of its surface.
PART_MASS = 0.01
# How far apart two of an object's parts may lie and still be kept from meeting (metres): both margins and a centimetre.
TOUCH = 2 * MARGIN + 0.01
# Beside the stage: its hollow objects' convex parts (tools/usd/convex_parts.py's FILE).
PARTS_FILE = "convex-parts.json"
# What a stage draws that nothing stands on or against: its sky (the haze round the place, the stars, the moon's and
# the halo's squares), whose meshes would otherwise be static and enclose every object (2026-10-10: every object of
# usd-r3 started "inside" the haze and was dropped on the bare ground alone).
NOT_SOLID = {"Sky", "Outside"}
# The ground: the stage's Ground, else a made ground's fine patch (/<place>/Outside/near: the terrain stage's layer
# turns the old Ground off; before 2026-10-12 the drop fell onto a plane at y = 0 there), else a plane at y = 0.
GROUND_NAMES = ("Ground", "near")
# How far a loose object is raised for the test of whether it starts inside a static (metres): what it only touches,
# the deck under it, is not "inside" (the resting triage's nudge is the same 5 mm).
NUDGE = 0.005
# How far past a loose object's bounds a static is kept in the simulation (metres): a drop of a few centimetres that
# may tip a piece over its own height never reaches further; statics past every loose object's reach are left out.
NEAR = 3.0
# A room's stage has no Ground: the floor is y = 0 (resting.py's flat place), a plane this many metres across.
FLAT_SIDE = 400.0
SUBSTEPS = 20
ITERATIONS = 40
# The stage's y-up frame onto Blender's z-up and back, as Blender's importer turns a y-up stage.
Y_UP_TO_Z_UP = Matrix(((1, 0, 0, 0), (0, 0, -1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))


def arguments():
    given = sys.argv[sys.argv.index("--") + 1:]
    if len(given) != 3:
        raise SystemExit(__doc__)
    return pathlib.Path(given[0]), json.loads(pathlib.Path(given[1]).read_text()), pathlib.Path(given[2])


def import_stage(stage):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    result = bpy.ops.wm.usd_import(filepath=str(stage), import_guide=False, import_proxy=False,
                                   import_textures_mode="IMPORT_NONE", property_import_mode="ALL",
                                   import_lights=False, create_world_material=False)
    if "FINISHED" not in result:
        raise RuntimeError(f"Blender did not import {stage}: {result}")


def drawn_mesh(holder):
    """An object's drawn mesh: the mesh among its children (a laid object is an Xform holding `geo`)."""
    found = [child for child in holder.children if child.type == "MESH"]
    if len(found) != 1:
        raise RuntimeError(f"{holder.name}: {len(found)} drawn meshes, expected one")
    return found[0]


def unparented(item):
    """The object on its own at the same place: a rigid body must have no parent."""
    placed = item.matrix_world.copy()
    item.parent = None
    item.matrix_world = placed
    return item


def stage_motion(blender):
    """A motion in Blender's world (z up) as the same motion in the stage's own frame (y up), row by row."""
    found = Y_UP_TO_Z_UP.inverted() @ blender @ Y_UP_TO_Z_UP
    return [list(row) for row in found]


def tree(item, shift=Vector()):
    """The object's triangles in world space (moved by `shift`, metres), for overlap tests."""
    from mathutils.bvhtree import BVHTree
    placed = Matrix.Translation(shift) @ item.matrix_world
    return BVHTree.FromPolygons([placed @ vertex.co for vertex in item.data.vertices],
                                [polygon.vertices[:] for polygon in item.data.polygons])


def heights(item):
    """The lowest and highest world height of the object's vertices."""
    found = [(item.matrix_world @ vertex.co).z for vertex in item.data.vertices]
    return min(found), max(found)


def inside_statics(item, statics, lows, middles):
    """The static objects this one starts inside: an overlap that survives raising it by NUDGE (so the deck or plate
    it stands on, which it touches, does not count) and moving it NUDGE away from the static's middle (so a pad or a
    wall it only stands against does not count), with a static that reaches below its middle (so a thing standing on
    it does not count either), as the resting triage's overlap survives its nudge."""
    raised = tree(item, Vector((0.0, 0.0, NUDGE)))
    low, high = heights(item)
    middle = (low + high) / 2
    mine = box_middle(item)
    return [name for name, other in statics.items()
            if lows[name] < middle and raised.overlap(other) and tree(item, away(mine, middles[name])).overlap(other)]


def box_middle(item):
    """The middle of the object's world bounds."""
    corners = [item.matrix_world @ Vector(corner) for corner in item.bound_box]
    return sum(corners, Vector()) / len(corners)


def away(mine, other):
    """A NUDGE step from the other's middle toward this one's (up when they share a middle), as the triage's nudge."""
    way = mine - other
    return way.normalized() * NUDGE if way.length > 1e-9 else Vector((0.0, 0.0, NUDGE))


def world_box(item, margin=0.0):
    """The object's world bounds (low and high corners, Blender's z up), grown by `margin` metres each way."""
    corners = [item.matrix_world @ Vector(corner) for corner in item.bound_box]
    return (Vector([min(corner[axis] for corner in corners) - margin for axis in range(3)]),
            Vector([max(corner[axis] for corner in corners) + margin for axis in range(3)]))


def boxes_meet(one, other):
    """Whether two world bounds overlap."""
    return all(one[0][axis] <= other[1][axis] and other[0][axis] <= one[1][axis] for axis in range(3))


def left_out(holder, ignore):
    """Whether a holder, or a holder it lies under (a fixture's own parts), is one the job leaves out of the statics."""
    while holder is not None:
        if holder.name.split(".")[0] in ignore:
            return True
        holder = holder.parent
    return False


def weight_at_middle(item):
    """The object's origin moved to the middle of its surface (Blender takes the origin as the centre of mass)."""
    bpy.ops.object.select_all(action="DESELECT")
    item.select_set(True)
    bpy.context.view_layer.objects.active = item
    bpy.ops.object.origin_set(type="ORIGIN_CENTER_OF_MASS", center="MEDIAN")


def rigid(item, kind, shape, groups):
    bpy.context.view_layer.objects.active = item
    bpy.ops.rigidbody.object_add(type=kind)
    body = item.rigid_body
    body.collision_shape = shape
    body.friction = FRICTION
    body.restitution = 0.0
    body.use_margin = True
    body.collision_margin = MARGIN
    body.collision_collections = [index in groups for index in range(GROUPS)]
    if kind == "ACTIVE":
        body.linear_damping = DAMPING_LINEAR
        body.angular_damping = DAMPING_ANGULAR
        body.mass = 1.0


def hollow_parts(stage):
    """{object name: its convex parts} from PARTS_FILE beside the stage; none when there is no such file."""
    found = stage.parent / PARTS_FILE
    return json.loads(found.read_text()) if found.exists() else {}


def convex_pieces(name, laid, parts, scene):
    """The object's convex parts (the job's `parts`: corners in its drawn mesh's own frame, laid at `laid`) as meshes of
    their own in the world where it is laid, never drawn, each with its origin at its own middle: Blender takes the
    origin as the centre of mass, and parts weighed at the world's origin threw a crate laid 36 m from it 276 m
    (2026-10-26). None for an object the job gives no parts."""
    pieces = []
    for number, corners in enumerate(parts):
        placed = [laid @ Vector(corner) for corner in corners]
        centre = sum(placed, Vector()) / len(placed)
        mesh = bpy.data.meshes.new(f"{name}_part_{number}")
        mesh.from_pydata([corner - centre for corner in placed], [], [])
        piece = bpy.data.objects.new(mesh.name, mesh)
        scene.collection.objects.link(piece)
        piece.matrix_world = Matrix.Translation(centre)  # its origin, its centre of mass, at the part itself
        piece.hide_render = True
        pieces.append(piece)
    return pieces


def joint(first, second, kind):
    """A rigid body joint of `kind` between two bodies, which keeps them from meeting each other."""
    holder = bpy.data.objects.new(f"joint_{first.name}_{second.name}", None)
    bpy.context.scene.collection.objects.link(holder)
    holder.matrix_world = Matrix.Translation(first.matrix_world.translation)  # the pivot at the body, not the origin
    bpy.context.view_layer.objects.active = holder
    bpy.ops.rigidbody.constraint_add(type=kind)
    holder.rigid_body_constraint.object1 = first
    holder.rigid_body_constraint.object2 = second
    holder.rigid_body_constraint.disable_collisions = True


def part_box(piece):
    """A part's world bounds grown by TOUCH (from its corners: a mesh made here has no bounds until it is drawn)."""
    corners = [piece.matrix_world @ vertex.co for vertex in piece.data.vertices]
    return (Vector([min(corner[axis] for corner in corners) - TOUCH for axis in range(3)]),
            Vector([max(corner[axis] for corner in corners) + TOUCH for axis in range(3)]))


def glued_parts(item, pieces):
    """Each part glued to the object (a fixed joint) and kept from meeting each part it lies against (a joint that
    holds nothing): the parts overlap where they meet, and parts that met would throw the object apart. Glued, the
    parts never move against each other, so two parts whose bounds lie apart never meet and get no joint: a joint
    between every pair grew with the square of the parts, and four 59-part bowls (about 7,100 joints) ran past 25
    minutes (2026-10-26)."""
    boxes = [part_box(piece) for piece in pieces]
    for number, piece in enumerate(pieces):
        joint(item, piece, "FIXED")
        for other in range(number + 1, len(pieces)):
            if boxes_meet(boxes[number], boxes[other]):
                joint(piece, pieces[other], "GENERIC")


def own_group(number):
    """A loose object's own collision group (1 to GROUPS - 1, shared again past that many)."""
    return 1 + number % (GROUPS - 1)


def overlaps(moving):
    """Pairs of loose objects that came to rest inside each other."""
    trees = {name: tree(item) for name, item in moving.items()}
    names = sorted(trees)
    return [[first, second] for index, first in enumerate(names) for second in names[index + 1:]
            if trees[first].overlap(trees[second])]


def world(scene):
    if scene.rigidbody_world is None:
        bpy.ops.rigidbody.world_add()
    simulation = scene.rigidbody_world
    simulation.substeps_per_frame = SUBSTEPS
    simulation.solver_iterations = ITERATIONS
    simulation.point_cache.frame_start = 1
    simulation.point_cache.frame_end = FPS * SECONDS
    scene.gravity = (0.0, 0.0, -GRAVITY)
    scene.render.fps = FPS


def flat_ground(scene):
    """A room's ground where the stage has none: a wide plane at the stage's y = 0, as the resting check reads it."""
    mesh = bpy.data.meshes.new("Ground")
    half = FLAT_SIDE / 2
    mesh.from_pydata([(-half, -half, 0), (half, -half, 0), (half, half, 0), (-half, half, 0)], [], [(0, 1, 2, 3)])
    plane = bpy.data.objects.new("Ground", mesh)
    scene.collection.objects.link(plane)
    return plane


def main():
    stage, job, out = arguments()
    parts = hollow_parts(stage)
    import_stage(stage)
    scene = bpy.context.scene
    world(scene)
    loose = set(job["loose"])
    holders = {item.name: item for item in bpy.data.objects if item.type == "EMPTY"}
    meshes = {item.name.split(".")[0]: item for item in bpy.data.objects if item.type == "MESH"}
    ground = next((meshes[name] for name in GROUND_NAMES if name in meshes), None) or flat_ground(scene)
    rigid(unparented(ground), "PASSIVE", "MESH", range(GROUPS))
    statics, lows, middles, moving, inside = {}, {}, {}, {}, {}
    ignore = set(job.get("ignore", []))
    reach = [world_box(drawn_mesh(holders[name]), NEAR) for name in loose if name in holders]
    for name, holder in holders.items():
        meshes = [child for child in holder.children if child.type == "MESH"]
        if not meshes or name.split(".")[0] in NOT_SOLID or left_out(holder, ignore):
            continue
        if name in loose:
            moving[name] = unparented(drawn_mesh(holder))
            continue
        for item in meshes:  # a static holder may draw several meshes (a character's body and clothes)
            if not any(boxes_meet(world_box(item), box) for box in reach):
                continue  # out of every loose object's reach: nothing it can meet (the square's crowd of 10,000)
            item = unparented(item)
            static = name if len(meshes) == 1 else f"{name}/{item.name}"
            statics[static], lows[static], middles[static] = tree(item), heights(item)[0], box_middle(item)
            rigid(item, "PASSIVE", "MESH", range(GROUPS))
            item.rigid_body.collision_collections = [False] + [True] * (GROUPS - 1)
    begins = {name: Matrix(job.get("start", {}).get(name, Matrix.Identity(4))) for name in moving}
    lifts = {name: Matrix.Translation(Vector((0.0, 0.0, float(job["lift"].get(name, 0.0)))))
             @ Y_UP_TO_Z_UP @ begins[name] @ Y_UP_TO_Z_UP.inverted() for name in moving}
    groups = {name: own_group(number) for number, name in enumerate(moving)}
    for name, item in moving.items():
        inside[name] = inside_statics(item, statics, lows, middles)
        pieces = convex_pieces(name, item.matrix_world, parts.get(name, []), scene)
        weight_at_middle(item)
        item.matrix_world = lifts[name] @ item.matrix_world
        stacked = [groups[other] for other in job.get("under", {}).get(name, []) if other in groups]
        meets = [0] if inside[name] else [groups[name], *stacked]
        rigid(item, "ACTIVE", "CONVEX_HULL", [] if pieces else meets)
        for piece in pieces:
            piece.matrix_world = lifts[name] @ piece.matrix_world
            rigid(piece, "ACTIVE", "CONVEX_HULL", meets)
            piece.rigid_body.mass = PART_MASS
        glued_parts(item, pieces)
    starts = {name: item.matrix_world.copy() for name, item in moving.items()}
    last = {}
    for frame in range(1, FPS * SECONDS + 1):
        scene.frame_set(frame)
        if frame == FPS * SECONDS - 1:
            last = {name: item.matrix_world.translation.copy() for name, item in moving.items()}
    found = {}
    for name, item in moving.items():
        motion = item.matrix_world @ starts[name].inverted() @ lifts[name]
        found[name] = {"motion": stage_motion(motion), "inside": inside[name],
                       "moving": (item.matrix_world.translation - last[name]).length * FPS}
    out.write_text(json.dumps({"objects": found, "overlaps": overlaps(moving)}, indent=1))
    print("settle_stage: wrote", out)


main()
