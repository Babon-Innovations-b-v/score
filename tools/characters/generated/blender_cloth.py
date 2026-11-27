"""Inside Blender (CPU only): a generated person walking with her clothes as cloth (`cloth.py`'s cloth.npz) or skinned
whole (still_rig's body.glb as it is), at her own height, drawn the whole route's photo way (../whole/render.py: the
CC0 park sky as world and ground, the incident meter, 85 mm): standing front; walking at the stride's three points
(left foot ahead, passing, right foot ahead) from the side and three quarters; walking from the back; then the film
(cloth.SECONDS at cloth.FPS from three quarters, numbered frames; the mp4 is made outside).

    blender -b --python blender_cloth.py -- <repo> <body.glb> <cloth.npz> <library> <out> <cloth|skinned>
        <samples> <size> [<film samples> <film size>]

The cloth: the shell's faces of each simulated garment (cloth.SIMULATED) taken off the skinned shell into a mesh of
their own, its points and their normals set every frame to the run's (each Blender point to the nearest garment
point at the bind), never thickened (the shell is the skinned person's own: a solidify's inner layer poked through
its thin noisy walls as dark blotches all over the jacket; round 4, 2026-11-27); the collision body drawn under them,
so a lifted hem shows a body and a T-shirt, never the hollow shell. The armature plays the clip at the run's clip
time, in place (the run's travel taken out).
"""
import math
import pathlib
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.kdtree import KDTree

ARGS = sys.argv[sys.argv.index("--") + 1:]
REPO, GLB, CLOTH, LIBRARY, OUT, MODE, SAMPLES, SIZE = ARGS[:8]
FILM = ARGS[8:] if len(ARGS) > 8 else None
sys.path.insert(0, str(pathlib.Path(REPO) / "tools/characters/whole"))
sys.path.insert(0, str(pathlib.Path(REPO) / "tools/characters/generated"))
import render  # noqa: E402

# The people are developed plainly (sRGB), as blender_eyes.VIEW, not in the whole route's AgX look (2026-11-27: its
# medium high contrast look takes lit skin's chroma down and a shadow's up).
VIEW = ("Standard", "None")
SHELL = "work"  # still_rig.OUTFIT: the rigged shell's node
SETTING = {"sky": "polyhaven_cloudy_vondelpark"}
VIEWS = (("side", 270.0), ("three_quarter", 215.0))
FILM_DEGREES = 235.0
UNDER = {"trunk": ("Hips", "Spine1", "Spine2", "Chest", "Neck1", "LeftShoulder", "RightShoulder", "LeftArm",
                   "RightArm", "LeftForeArm", "RightForeArm"),
         "legs": ("LeftLeg", "RightLeg", "LeftShin", "RightShin")}
# the body under the clothes, seen only through a gap: the T-shirt's white on the trunk and arms, dark denim on the
# legs; its head, hands and feet are never drawn (the shell's own are)
UNDER_COLOURS = {"trunk": (0.78, 0.78, 0.76, 1.0), "legs": (0.06, 0.1, 0.2, 1.0)}


def kinds_of(data):
    """cloth.KINDS as cloth.npz names them (cloth.py needs scipy: not imported here)."""
    return [str(kind) for kind in data["kind_names"]]


def simulated_of(data):
    """The garments cloth.npz moves as cloth."""
    return [str(kind) for kind in data["simulated"]]


def to_blender(points):
    """glTF (y up, facing +z) to Blender (z up, facing -y)."""
    points = np.asarray(points, float)
    return np.stack([points[..., 0], -points[..., 2], points[..., 1]], axis=-1)


def imported():
    """The person imported into an empty scene, its far body hidden; (armature, its shell mesh: still_rig's `work`)."""
    for item in list(bpy.data.objects):
        bpy.data.objects.remove(item)
    bpy.ops.import_scene.gltf(filepath=GLB)
    armature = next(item for item in bpy.data.objects if item.type == "ARMATURE")
    for item in bpy.data.objects:
        if item.type == "MESH" and item.name.startswith("far"):
            item.hide_render = True
    shell = bpy.data.objects[SHELL]
    return armature, shell


def coordinates(mesh):
    found = np.zeros(len(mesh.vertices) * 3)
    mesh.vertices.foreach_get("co", found)
    return found.reshape(-1, 3)


def tree_of(points):
    tree = KDTree(len(points))
    for number, point in enumerate(points):
        tree.insert(Vector(point), number)
    tree.balance()
    return tree


def face_kinds(shell, data):
    """Each polygon of the imported shell's kind: the kind of the nearest shell face middle of cloth.npz."""
    middles = to_blender(data["shell_points"][data["shell_faces"]].mean(1))
    tree = tree_of(middles)
    kinds = data["kinds"]
    return np.array([kinds[tree.find(polygon.center)[1]] for polygon in shell.data.polygons])


def split_off(shell, kinds, kind, number):
    """A copy of the shell holding only `kind`'s polygons (kind number `number`), unskinned (its points are set from the run)."""
    garment = shell.copy()
    garment.data = shell.data.copy()
    garment.name = kind
    bpy.context.scene.collection.objects.link(garment)
    for modifier in list(garment.modifiers):
        garment.modifiers.remove(modifier)
    mesh = bmesh.new()
    mesh.from_mesh(garment.data)
    mesh.faces.ensure_lookup_table()
    bmesh.ops.delete(mesh, geom=[face for face in mesh.faces if kinds[face.index] != number],
                     context="FACES")
    mesh.to_mesh(garment.data)
    mesh.free()
    garment.vertex_groups.clear()
    garment.data.shade_smooth()
    return garment


def kept_only(shell, kinds, dropped):
    """The skinned shell with the `dropped` kinds' polygons removed."""
    mesh = bmesh.new()
    mesh.from_mesh(shell.data)
    mesh.faces.ensure_lookup_table()
    bmesh.ops.delete(mesh, geom=[face for face in mesh.faces if kinds[face.index] in dropped], context="FACES")
    mesh.to_mesh(shell.data)
    mesh.free()


def body_made(armature, shell, data):
    """The collision body under the clothes, skinned by its own weights, coloured by its points' strongest joints
    (UNDER) in the person's own shirt's and trousers' paint (cloth.under_colours; UNDER_COLOURS for a run without)."""
    weights = data["body_weights"]
    kinds = data["joint_names"][weights.argmax(1)]
    region_of = np.array([0 if kind in UNDER["trunk"] else 1 if kind in UNDER["legs"] else 2 for kind in kinds])
    face_region = np.array([np.bincount(region_of[face], minlength=3).argmax() for face in data["body_faces"]])
    drawn = face_region < 2
    mesh = bpy.data.meshes.new("under")
    mesh.from_pydata(to_blender(data["body_points"]).tolist(), [], data["body_faces"][drawn].tolist())
    body = bpy.data.objects.new("under", mesh)
    bpy.context.scene.collection.objects.link(body)
    body.parent = shell.parent
    body.matrix_world = shell.matrix_world.copy()
    for joint, name in enumerate(data["joint_names"]):
        group = body.vertex_groups.new(name=str(name))
        for number in np.flatnonzero(weights[:, joint] > 0.0):
            group.add([int(number)], float(weights[number, joint]), "REPLACE")
    modifier = body.modifiers.new("skin", "ARMATURE")
    modifier.object = armature
    for number, (region, colour) in enumerate(UNDER_COLOURS.items()):
        if "under_colours" in data:  # the person's own shirt and trousers (cloth.under_colours)
            colour = (*[float(value) for value in data["under_colours"][number]], 1.0)
        material = bpy.data.materials.new(f"under_{region}")
        material.use_nodes = True
        material.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = colour
        material.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.8
        mesh.materials.append(material)
    mesh.polygons.foreach_set("material_index", face_region[drawn].astype(np.int32))
    mesh.shade_smooth()
    return body


def garments_made(shell, data):
    """{kind: (object, each Blender point's garment point)}; the skinned shell keeps the other kinds."""
    kinds = face_kinds(shell, data)
    found = {}
    for kind in simulated_of(data):
        garment = split_off(shell, kinds, kind, kinds_of(data).index(kind))
        used = data[f"{kind}_used"]
        tree = tree_of(to_blender(data["shell_points"][used]))
        mapping = np.array([tree.find(Vector(point))[1] for point in coordinates(garment.data)])
        found[kind] = (garment, mapping)
    kept_only(shell, kinds, [kinds_of(data).index(kind) for kind in simulated_of(data)])
    return found


def posed(armature, action, seconds):
    """The armature at `seconds` into its clip."""
    scene = bpy.context.scene
    frame = action.frame_range[0] + seconds * scene.render.fps / scene.render.fps_base
    scene.frame_set(int(math.floor(frame)), subframe=frame - math.floor(frame))


def laid(garments, data, key, index):
    """Each garment's points set to the run's at `key` frame `index` (the run's points are in the glTF frame), each
    shaded by its own smooth normal as the run turns it (the shell's, as the skinned person is: the moved surface's
    own faces drew it lumpy)."""
    for kind, (garment, mapping) in garments.items():
        points = to_blender(data[f"{key}/{kind}"][index])[mapping]
        garment.data.vertices.foreach_set("co", points.ravel())
        garment.data.normals_split_custom_set_from_vertices(to_blender(data[f"{key}/{kind}_normal"][index])[mapping])
        garment.data.update()


def playing(armature, clip):
    action = next(action for action in bpy.data.actions if action.name.split("_")[0] == clip
                  or action.name.startswith(clip))
    armature.animation_data_create()
    armature.animation_data.action = action
    if hasattr(armature.animation_data, "action_slot") and action.slots:
        armature.animation_data.action_slot = action.slots[0]
    return action


def at(armature, action, garments, data, key, index, holder):
    """The person at the run's `key` frame `index`: posed, the cloth laid, hips over the turntable's middle."""
    posed(armature, action, float(data[f"{key}/time"][index]))
    if garments:
        laid(garments, data, key, index)
    holder.location = Vector((0.0, 0.0, 0.0))
    bpy.context.view_layer.update()
    hips = armature.matrix_world @ armature.pose.bones["Hips"].head
    holder.location = Vector((-hips.x, -hips.y, 0.0))
    bpy.context.view_layer.update()


def staged(scale):
    """The person under a holder (sized to her own height) on a turntable; (holder, turntable)."""
    scene = bpy.context.scene
    holder = bpy.data.objects.new("holder", None)
    turntable = bpy.data.objects.new("turntable", None)
    scene.collection.objects.link(holder)
    scene.collection.objects.link(turntable)
    for item in list(scene.objects):
        if item.parent is None and item not in (holder, turntable):
            item.parent = holder
    holder.parent = turntable
    holder.scale = (scale,) * 3
    return holder, turntable


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    data = dict(np.load(CLOTH))
    armature, shell = imported()
    garments = {}
    if MODE == "cloth":
        garments = garments_made(shell, data)
        body_made(armature, shell, data)
    holder, turntable = staged(float(data["scale"]))
    scene = bpy.context.scene
    standing = playing(armature, "standing")
    at(armature, standing, garments, data, "standing/standing", 0, holder)
    items = [item for item in scene.objects if item.type == "MESH" and not item.hide_render]
    low, high = render.bounds(items)
    middle = Vector((0.0, 0.0, (low.z + high.z) / 2))
    high = Vector((0.0, 0.0, high.z))
    print(f"standing height {high.z - low.z:.3f} m", flush=True)
    exposure = render.place(LIBRARY, middle, SETTING)
    render.film(scene, exposure)
    scene.view_settings.view_transform, scene.view_settings.look = VIEW
    scene.cycles.device = "CPU"
    scene.cycles.samples = int(SAMPLES)
    scene.render.resolution_x, scene.render.resolution_y = int(SIZE) * 2 // 3, int(SIZE)
    scene.render.resolution_percentage = 100
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 8
    camera = render.camera_made(scene)
    render.framed(camera, middle, high, render.MARGIN, render.EYE_HEIGHT, render.STOPS["side"])
    out = pathlib.Path(OUT)
    out.mkdir(parents=True, exist_ok=True)
    render.drawn(scene, turntable, 180.0, out, "standing_front")
    walking = playing(armature, "walking")
    for view, degrees in VIEWS:
        for point in ("left_ahead", "passing", "right_ahead"):
            at(armature, walking, garments, data, f"walking/{point}", 0, holder)
            render.drawn(scene, turntable, degrees, out, f"walk_{view}_{point}")
    at(armature, walking, garments, data, "walking/passing", 0, holder)
    render.drawn(scene, turntable, 0.0, out, "walk_back_passing")
    print("SHEET RENDER DONE", flush=True)
    if FILM:
        scene.cycles.samples = int(FILM[0])
        scene.render.resolution_x, scene.render.resolution_y = int(FILM[1]) * 2 // 3, int(FILM[1])
        film = out / "film"
        film.mkdir(exist_ok=True)
        for index in range(len(data["walking/film/time"])):
            at(armature, walking, garments, data, "walking/film", index, holder)
            turntable.rotation_euler = (0.0, 0.0, -math.radians(FILM_DEGREES))
            scene.render.filepath = str(film / f"{index:03d}.png")
            bpy.ops.render.render(write_still=True)
        print("FILM RENDER DONE", flush=True)


main()
