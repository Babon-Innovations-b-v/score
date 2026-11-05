"""Runs inside Blender: a layer peel's three passes (`../peel.py` writes the job and joins the passes).

    blender -b --python body_peel.py -- <job.json>

Every person three ways on the job's camera path: `dressed` (its dressed body's glTF posed by the job's joint moves,
its rest fitted to the clip rig's bind), `mesh` (its bare SOMA surface at the job's points, solid with its edges
drawn), `sim` (the sim body layer's own geometry under the person's SimBody, imported with its time samples and shown
at the record's frame, each touching body's push an arrow from its centre of pressure), over the job's ground. Every array comes from the job, already in
the place and Z up; nothing is worked out here but the fit and the drawing.
A place peel's job (`"kind": "place"`, peel.place_job) draws a place three ways on its one standing camera:
`finished` (its stage imported as it is, its lights and finishes its own), `bare` (the same models, every finish
replaced by one plain clay) and `physics` (the job's collision shapes, its moving bodies apart, the drawn models
hidden, the stage's lights kept).
Out: <out>/<pass>/<frame>.png, the frames the job's `frames` names (dealt), numbered in the whole shot.
"""
import json
import math
import sys

import bpy
import numpy as np
from mathutils import Matrix, Vector

FLOOR = (0.32, 0.33, 0.35)
CLAY = (0.72, 0.70, 0.67)
EDGES = (0.05, 0.05, 0.06)
SIM = (0.95, 0.42, 0.12)  # the sim body geometry with no colours of its own
STATIC = (0.36, 0.52, 0.70)  # a place's still colliders (its moving bodies are SIM)
# The push arrows (owner, 2026-11-04: "visible but not obnoxious or ugly"): a slim shaft and a small head at a fixed
# width on screen whatever the camera's distance, a little see-through and lit a little from within so they read in
# shadow, in the job's colour (the film's --film-push token).
SHAFT_PIXELS = 1.6  # the shaft's radius on screen
HEAD_PIXELS = 4.5  # the head's radius on screen
HEAD_LONG_PIXELS = 13.0  # the head's length on screen, never more than half the arrow
ARROW_ALPHA = 0.72
ARROW_GLOW = 0.6
LIFT = 0.002  # metres: the arrow's foot off its ground beyond its own radius, so it never pokes through
# The crowd's cheap body every dressed file carries beside the person's own (tools/characters/cast.py): never one
# person's.
FAR = "far"


def material(name, colour, glow=0.0, alpha=1.0):
    made = bpy.data.materials.new(name)
    made.use_nodes = True
    shader = made.node_tree.nodes["Principled BSDF"]
    shader.inputs["Base Color"].default_value = (*colour, 1.0)
    shader.inputs["Roughness"].default_value = 0.6
    shader.inputs["Alpha"].default_value = alpha
    if glow:
        shader.inputs["Emission Color"].default_value = (*colour, 1.0)
        shader.inputs["Emission Strength"].default_value = glow
    return made


def collection(name):
    made = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(made)
    return made


def linked(obj, into):
    for holder in list(obj.users_collection):
        holder.objects.unlink(obj)
    into.objects.link(obj)
    return obj


def renderer(job):
    """Cycles on this machine's card, the job's size and samples, denoised."""
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    preferences = bpy.context.preferences.addons["cycles"].preferences
    for kind in ("OPTIX", "CUDA"):
        try:
            preferences.compute_device_type = kind
        except TypeError:
            continue
        preferences.get_devices()
        if any(device.type == kind for device in preferences.devices):
            for device in preferences.devices:
                device.use = device.type == kind
            scene.cycles.device = "GPU"
            break
    scene.cycles.samples = job["samples"]
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = job["size"]
    scene.render.resolution_percentage = 100
    scene.render.fps = round(job["record_rate"])
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = "AgX"


def surroundings(job):
    """The ground (the job's triangles of the scene, else a flat floor at 0), a sun, the sky's fill and the camera."""
    if job["ground"]:
        triangles = np.load(job["ground"])
        ground = bpy.data.meshes.new("ground")
        ground.from_pydata(triangles.reshape(-1, 3).tolist(), [], np.arange(len(triangles) * 3).reshape(-1, 3).tolist())
        bpy.context.scene.collection.objects.link(bpy.data.objects.new("ground", ground))
    else:
        bpy.ops.mesh.primitive_plane_add(size=200.0)
        ground = bpy.context.object.data
    ground.materials.append(material("floor", FLOOR))
    world = bpy.data.worlds.new("world")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.05, 0.06, 0.08, 1.0)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.0
    bpy.context.scene.world = world
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sun.data.energy = 3.0
    sun.rotation_euler = (0.7, 0.2, 0.9)
    bpy.context.scene.collection.objects.link(sun)
    camera = bpy.data.objects.new("camera", bpy.data.cameras.new("camera"))
    camera.data.lens = job["camera"]["lens"]
    bpy.context.scene.collection.objects.link(camera)
    bpy.context.scene.camera = camera
    return camera


def aimed(camera, spot):
    """The camera at the job's spot for one frame ({eye, aim})."""
    camera.location = Vector(spot["eye"])
    camera.rotation_euler = (Vector(spot["aim"]) - camera.location).to_track_quat("-Z", "Y").to_euler()


def dressed(person, into):
    """The person's dressed body (its armature and the meshes it skins; not the crowd's far body), its armature's
    rest fitted to the clip rig's bind frames (a turn about up and a shift) and the whole placed: (the armature, the
    fit A taking the rig's frame into the armature's)."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=person["glb"])
    made = [obj for obj in bpy.data.objects if obj not in before]
    armature = next(obj for obj in made if obj.type == "ARMATURE")
    kept = [armature, *(obj for obj in made if obj.parent == armature and obj.type == "MESH"
                        and obj.name.split(".")[0] != FAR)]
    for obj in made:
        if obj not in kept:
            bpy.data.objects.remove(obj)
    if armature.animation_data:
        armature.animation_data.action = None  # posed from the sim body's clip, never its own
    fit = rest_fit(armature, person["joints"], np.load(person["arrays"])["bind_heads"])
    holder = bpy.data.objects.new(f"{person['name']}_placed", None)
    into.objects.link(holder)
    holder.matrix_world = Matrix(person["placed"]) @ fit.inverted() @ armature.matrix_world.inverted()
    for obj in kept:
        linked(obj, into)
    armature.parent = holder
    return armature, fit


def rest_fit(armature, joints, heads):
    """The turn about up and the shift that best lay the clip rig's bind joints (`heads`, Z up) on the armature's rest
    heads of the same names (least squares)."""
    pairs = [(heads[index], armature.data.bones[name].head_local) for index, name in enumerate(joints)
             if name in armature.data.bones]
    rig = np.array([pair[0] for pair in pairs])
    rest = np.array([list(pair[1]) for pair in pairs])
    rig_middle, rest_middle = rig.mean(axis=0), rest.mean(axis=0)
    one, other = rig[:, :2] - rig_middle[:2], rest[:, :2] - rest_middle[:2]
    angle = np.arctan2((one[:, 0] * other[:, 1] - one[:, 1] * other[:, 0]).sum(), (one * other).sum())
    fit = Matrix.Rotation(float(angle), 4, "Z")
    fit.translation = Vector(rest_middle.tolist()) - fit.to_3x3() @ Vector(rig_middle.tolist())
    return fit


def posed(armature, fit, joints, moves):
    """Every bone of the dressed body at its rig joint's move (`moves`: joints x 4 x 4, the rig's frame), parent
    first: its rest carried by the move, set as the bone's basis against its parent."""
    index = {name: number for number, name in enumerate(joints)}
    inverse = fit.inverted()
    wanted = {}

    def pose(bone):
        rest = bone.matrix_local
        move = fit @ Matrix(moves[index[bone.name]].tolist()) @ inverse if bone.name in index else Matrix()
        wanted[bone.name] = move @ rest
        if bone.parent:
            parent = bone.parent
            above = parent.matrix_local.inverted() @ rest
            basis = above.inverted() @ wanted[parent.name].inverted() @ wanted[bone.name]
        else:
            basis = rest.inverted() @ wanted[bone.name]
        armature.pose.bones[bone.name].matrix_basis = basis
        for child in bone.children:
            pose(child)

    for bone in armature.data.bones:
        if bone.parent is None:
            pose(bone)


def bare(person, arrays, into):
    """The bare SOMA surface: one mesh shown twice, solid clay and its edges; the mesh (its points set each frame)."""
    mesh = bpy.data.meshes.new(f"{person['name']}_mesh")
    mesh.from_pydata(arrays["points"][0].tolist(), [], arrays["faces"].tolist())
    mesh.materials.append(material("clay", CLAY))
    solid = linked(bpy.data.objects.new(f"{person['name']}_solid", mesh), into)
    solid.data.polygons.foreach_set("use_smooth", [True] * len(mesh.polygons))
    edges = linked(bpy.data.objects.new(f"{person['name']}_edges", mesh), into)
    wire = edges.modifiers.new("edges", "WIREFRAME")
    wire.thickness, wire.use_replace, wire.material_offset = 0.0025, True, 1
    edges.data.materials.append(material("edges", EDGES))
    return mesh


def sim(person, arrays, into, look):
    """The person's sim body as its layer holds it (whatever geometry sits under its SimBody prim, guides included,
    each transform keyed at its time samples), placed, and a push arrow a touching body: [(arrow shaft, arrow head)
    a body]."""
    before = set(bpy.data.objects)
    bpy.ops.wm.usd_import(filepath=person["sim_layer"], prim_path_mask=person["sim_root"], import_guide=True,
                          import_render=True, import_proxy=False, set_frame_range=False, create_collection=False,
                          read_mesh_colors=True, import_materials=True)
    made = [obj for obj in bpy.data.objects if obj not in before]
    if not any(obj.type in ("MESH", "CURVES", "CURVE") for obj in made):
        raise RuntimeError(f"{person['sim_layer']}: no geometry under {person['sim_root']}")
    holder = bpy.data.objects.new(f"{person['name']}_sim", None)
    into.objects.link(holder)
    holder.matrix_world = Matrix(person["placed"])
    for obj in made:
        linked(obj, into)
        if obj.parent is None:
            obj.parent = holder
        if obj.type in ("MESH", "CURVES", "CURVE") and not obj.data.materials:
            obj.data.materials.append(look["coloured"] if "displayColor" in getattr(obj.data, "attributes", {})
                                      else look["sim"])
    arrows = []
    for _ in range(arrays["arrow_start"].shape[1]):
        bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=1.0, depth=1.0)  # scaled each frame (arrow_at)
        shaft = linked(bpy.context.object, into)
        bpy.ops.mesh.primitive_cone_add(vertices=24, radius1=1.0, depth=1.0)
        head = linked(bpy.context.object, into)
        for part in (shaft, head):
            part.data.materials.append(look["arrow"])
            part.data.polygons.foreach_set("use_smooth", [True] * len(part.data.polygons))
            part.visible_shadow = False  # an overlay: it casts nothing on the body or its ground
        arrows.append((shaft, head))
    return arrows


def coloured():
    """A material showing a geometry's own colours (its `displayColor`, a muscle's activation say)."""
    made = material("coloured", (1.0, 1.0, 1.0))
    nodes = made.node_tree.nodes
    colour = nodes.new("ShaderNodeAttribute")
    colour.attribute_name = "displayColor"
    made.node_tree.links.new(colour.outputs["Color"], nodes["Principled BSDF"].inputs["Base Color"])
    return made


def pixel_metres(camera, at):
    """How many metres one pixel spans at `at` on the camera's picture (its depth along the camera's aim)."""
    scene = bpy.context.scene
    aim = camera.rotation_euler.to_matrix() @ Vector((0.0, 0.0, -1.0))  # as `aimed` set it this frame
    depth = max((Vector(at.tolist()) - camera.location).dot(aim), 0.1)
    return depth * camera.data.sensor_width / (camera.data.lens * scene.render.resolution_x)


def arrow_at(parts, start, vector, camera, fade):
    """The arrow from `start` along `vector`, its tip at the push's length, its widths SHAFT_PIXELS and HEAD_PIXELS on
    the camera's picture, its foot lifted its own radius and LIFT off the ground; hidden where the job has none (the
    ground does not push that body) or before it fades in."""
    shaft, head = parts
    shown = fade > 0 and not np.isnan(start).any() and np.linalg.norm(vector) > 1e-4
    for part in parts:
        part.hide_render = not shown
    if not shown:
        return
    direction = Vector(vector.tolist())
    pixel = pixel_metres(camera, start + vector / 2)
    radius = SHAFT_PIXELS * pixel
    foot = Vector(start.tolist()) + direction.normalized() * (radius + LIFT)
    length = max(direction.length - radius - LIFT, 1e-4)
    head_long = min(HEAD_LONG_PIXELS * pixel, length / 2)
    turn = direction.to_track_quat("Z", "Y").to_euler()
    along = direction.normalized()
    shaft.location = foot + along * (length - head_long) / 2
    shaft.rotation_euler, shaft.scale = turn, (radius, radius, length - head_long)
    head.location = foot + along * (length - head_long / 2)
    head.rotation_euler, head.scale = turn, (HEAD_PIXELS * pixel, HEAD_PIXELS * pixel, head_long)


def faded(made, fade):
    """The arrows' material at `fade` of its look (0 to 1): its see-through and its glow both."""
    shader = made.node_tree.nodes["Principled BSDF"]
    shader.inputs["Alpha"].default_value = ARROW_ALPHA * fade
    shader.inputs["Emission Strength"].default_value = ARROW_GLOW * fade


def dealt(job):
    """(film frame, its source time code) of the frames this job draws: its `frames` [first, end) of the shot where
    the shot was dealt over several cards (peel.sliced), else every one."""
    first, end = job.get("frames", [0, len(job["source"])])
    return [(frame, job["source"][frame]) for frame in range(first, end)]


def draw(job):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    renderer(job)
    camera = surroundings(job)
    groups = {name: collection(name) for name in job["passes"]}
    # The sim body lets the push arrows under it show through.
    look = {"sim": material("sim", SIM, alpha=0.55),
            "arrow": material("arrow", tuple(job["arrows"]["colour"]), glow=ARROW_GLOW, alpha=ARROW_ALPHA),
            "coloured": coloured()}
    people = []
    for person in job["people"]:
        arrays = dict(np.load(person["arrays"]))
        armature, fit = dressed(person, groups["dressed"])
        mesh = bare(person, arrays, groups["mesh"])
        arrows = sim(person, arrays, groups["sim"], look)
        people.append((person, arrays, armature, fit, mesh, arrows))
    scene = bpy.context.scene
    for frame, source in dealt(job):
        aimed(camera, job["camera"]["path"][frame])
        scene.frame_set(source)  # the sim body layer's time code: the record's frame, at its rate (renderer)
        fade = job["arrows"]["fade"][frame]
        faded(look["arrow"], fade)
        for person, arrays, armature, fit, mesh, arrows in people:
            posed(armature, fit, person["joints"], arrays["moves"][frame])
            mesh.vertices.foreach_set("co", arrays["points"][frame].astype(np.float32).ravel())
            mesh.update()
            for parts, start, vector in zip(arrows, arrays["arrow_start"][frame], arrays["arrow_vector"][frame]):
                arrow_at(parts, start, vector, camera, fade)
        for name in job["passes"]:
            for other, group in groups.items():
                group.hide_render = other != name
            scene.render.filepath = f"{job['out']}/{name}/{frame:04d}.png"
            bpy.ops.render.render(write_still=True)


def shapes(job, into):
    """The place's collision shapes (the job's physics.npz: static and moving triangles, Z up), solid, their edges
    drawn: [the objects]."""
    arrays = dict(np.load(job["physics"]))
    made = []
    for kind, colour in (("static", STATIC), ("moving", SIM)):
        triangles = arrays[kind]
        if not len(triangles):
            continue
        mesh = bpy.data.meshes.new(f"physics_{kind}")
        mesh.from_pydata(triangles.reshape(-1, 3).tolist(), [], np.arange(len(triangles) * 3).reshape(-1, 3).tolist())
        mesh.materials.append(material(f"physics_{kind}", colour))
        made.append(linked(bpy.data.objects.new(f"physics_{kind}", mesh), into))
        edges = linked(bpy.data.objects.new(f"physics_{kind}_edges", mesh), into)
        wire = edges.modifiers.new("edges", "WIREFRAME")
        wire.thickness, wire.use_replace, wire.material_offset = 0.004, True, 1
        mesh.materials.append(material("edges", EDGES))
        made.append(edges)
    return made


def place_stage(job, into):
    """The place's finished stage imported as it is (no guides: its hulls are the physics pass's), its lights and
    world its own: [its drawn objects]."""
    before = set(bpy.data.objects)
    result = bpy.ops.wm.usd_import(filepath=job["stage"], import_guide=False, import_proxy=False, import_lights=True,
                                   create_world_material=True, set_frame_range=False)
    if "FINISHED" not in result:
        raise RuntimeError(f"Blender did not import {job['stage']}: {result}")
    made = [obj for obj in bpy.data.objects if obj not in before]
    for obj in made:
        linked(obj, into)
    return [obj for obj in made if obj.type != "LIGHT"]


def draw_place(job):
    """A place peel's three passes on its standing camera, at each film frame's stage time code."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    renderer(job)
    scene = bpy.context.scene
    drawn = place_stage(job, collection("finished"))
    bodies = shapes(job, collection("physics"))
    if scene.world is None:
        scene.world = bpy.data.worlds.new("world")
    camera = bpy.data.objects.new("camera", bpy.data.cameras.new("camera"))
    camera.data.sensor_fit = "HORIZONTAL"
    camera.data.angle = math.radians(job["camera"]["fov"])
    scene.collection.objects.link(camera)
    scene.camera = camera
    clay = material("clay", CLAY)
    for frame, source in dealt(job):
        aimed(camera, job["camera"]["path"][frame])
        scene.frame_set(source)
        for name in job["passes"]:
            for obj in drawn:
                obj.hide_render = name == "physics"
            for obj in bodies:
                obj.hide_render = name != "physics"
            bpy.context.view_layer.material_override = clay if name == "bare" else None
            scene.render.filepath = f"{job['out']}/{name}/{frame:04d}.png"
            bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    given = json.loads(open(sys.argv[sys.argv.index("--") + 1]).read())
    if given.get("kind") == "place":
        draw_place(given)
    else:
        draw(given)
