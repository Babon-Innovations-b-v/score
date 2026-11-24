"""Runs in Blender (5.x, Cycles): the dressed person's point cache (outfit.usda, ../cache.py) imported and rendered,
a still and a short turn, each framed on the body where it stands that frame.

    blender -b -P tools/characters/garments/inside/render.py -- <outfit.usda> <out folder> <still frame> <turn frame>
        <turn views> [<walk every>]

Writes <out>/still.png (three quarters front, the still frame), <out>/turn/<n>.png (the camera round the body at the
turn frame, `turn views` views) and, with `walk every`, <out>/walk/<frame>.png (every so many clip frames, the camera
beside the walk). Lit by a sky-blue world and one sun, no backdrop of its own: a grey floor plane under the feet.
"""
import math
import pathlib
import sys

import bpy
from mathutils import Vector

DISTANCE = 3.2  # m from the body's middle
HEIGHT = 1.05  # m, the camera's height over the floor
LENS = 55.0  # mm
SAMPLES = 96


def arguments():
    given = sys.argv[sys.argv.index("--") + 1:]
    if len(given) not in (5, 6):
        raise SystemExit(__doc__)
    return (pathlib.Path(given[0]), pathlib.Path(given[1]), int(given[2]), int(given[3]), int(given[4]),
            int(given[5]) if len(given) == 6 else 0)


def scene_set():
    """An empty scene, Cycles on the card, a world and a sun."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    preferences = bpy.context.preferences.addons["cycles"].preferences
    preferences.compute_device_type = "CUDA"
    preferences.get_devices()
    for device in preferences.devices:
        device.use = device.type == "CUDA"
    scene.cycles.device = "GPU"
    scene.cycles.samples = SAMPLES
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = 900, 1200
    scene.view_settings.view_transform = "AgX"
    world = bpy.data.worlds.new("world")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.55, 0.62, 0.72, 1.0)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.6
    scene.world = world
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sun.data.energy = 3.5
    sun.data.angle = math.radians(8.0)
    sun.rotation_euler = (math.radians(50.0), 0.0, math.radians(35.0))
    scene.collection.objects.link(sun)
    return scene


def floor(scene):
    bpy.ops.mesh.primitive_plane_add(size=40.0, location=(0.0, 0.0, 0.0))
    plane = bpy.context.active_object
    material = bpy.data.materials.new("floor")
    material.use_nodes = True
    material.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.32, 0.32, 0.32, 1.0)
    plane.data.materials.append(material)


def body_middle(scene, frame):
    """The body's bounding middle at `frame` (Blender's z up: the importer turns y up into z up)."""
    scene.frame_set(frame)
    body = bpy.data.objects["Body"].evaluated_get(bpy.context.evaluated_depsgraph_get())
    corners = [body.matrix_world @ Vector(corner) for corner in body.bound_box]
    return sum(corners, Vector()) / 8.0


def camera(scene):
    cam = bpy.data.objects.new("camera", bpy.data.cameras.new("camera"))
    cam.data.lens = LENS
    scene.collection.objects.link(cam)
    scene.camera = cam
    return cam


def shot(scene, cam, frame, angle, path):
    """One render at `frame`, the camera `angle` degrees round the body from its front (+y after import)."""
    middle = body_middle(scene, frame)
    turn = math.radians(angle)
    cam.location = Vector((middle.x + DISTANCE * math.sin(turn), middle.y - DISTANCE * math.cos(turn), HEIGHT))
    aim = Vector((middle.x, middle.y, HEIGHT * 0.92)) - cam.location
    cam.rotation_euler = aim.to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def main():
    usd, out, still, turn_frame, views, walk_every = arguments()
    scene = scene_set()
    bpy.ops.wm.usd_import(filepath=str(usd), import_materials=True, set_frame_range=True)
    floor(scene)
    cam = camera(scene)
    shot(scene, cam, still, 30.0, out / "still.png")
    for view in range(views):
        shot(scene, cam, turn_frame, 360.0 * view / views, out / "turn" / f"{view:03d}.png")
    if walk_every:
        for frame in range(scene.frame_start, scene.frame_end + 1, walk_every):
            shot(scene, cam, frame, 70.0, out / "walk" / f"{frame:03d}.png")


main()
