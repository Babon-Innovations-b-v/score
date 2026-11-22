"""Runs inside Blender: the plain scene the library's renders and bakes start from (Cycles on the processor)."""
import math
import os

import bpy
from mathutils import Vector


def use_card(scene):
    """Cycles on the machine's graphics cards (OptiX, else CUDA): set FARM_CYCLES_GPU=1, which only the rented
    machines do; this PC never bakes (the coordinator, 2026-10-06, after a local bake took every core and WSL
    crashed)."""
    preferences = bpy.context.preferences.addons["cycles"].preferences
    for kind in ("OPTIX", "CUDA"):
        try:
            preferences.compute_device_type = kind
        except TypeError:
            continue
        preferences.get_devices()
        cards = [device for device in preferences.devices if device.type == kind]
        if cards:
            for device in preferences.devices:
                device.use = device.type == kind
            scene.cycles.device = "GPU"
            return kind
    raise RuntimeError("FARM_CYCLES_GPU is set but no OptiX or CUDA card was found")


def empty_scene(size, samples):
    """A factory-empty scene drawing with Cycles at `size` pixels square, denoised, transparent behind: on the card where
    FARM_CYCLES_GPU is set (the rented machines), else on the processor."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    if os.environ.get("FARM_CYCLES_GPU"):
        use_card(scene)
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True  # a picture that ships is clean (score/checks/grain.py); a bake ignores it
    scene.render.resolution_x = scene.render.resolution_y = size
    scene.render.film_transparent = True
    scene.view_settings.view_transform = "Standard"
    world = bpy.data.worlds.new("world")
    scene.world = world
    world.use_nodes = True
    background = next(node for node in world.node_tree.nodes if node.type == "BACKGROUND")
    background.inputs[0].default_value = (0.32, 0.34, 0.37, 1.0)
    background.inputs[1].default_value = 0.5
    return scene


def studio_light():
    """A key sun from the upper left and a weaker one from behind, as a work lamp and a bounce."""
    for name, energy, rotation in (("key", 3.0, (50, 0, 35)), ("rim", 1.0, (60, 0, 200))):
        light = bpy.data.objects.new(name, bpy.data.lights.new(name, "SUN"))
        light.data.energy = energy
        light.rotation_euler = tuple(math.radians(value) for value in rotation)
        bpy.context.scene.collection.objects.link(light)


def camera_on(target, direction, distance, lens=50):
    """A camera looking at `target`'s middle from `direction`, `distance` times its size away."""
    corners = [target.matrix_world @ Vector(corner) for corner in target.bound_box]
    middle = sum(corners, Vector()) / 8
    size = max((corner - middle).length for corner in corners)
    camera = bpy.data.objects.new("camera", bpy.data.cameras.new("camera"))
    camera.data.lens = lens
    camera.location = middle + Vector(direction).normalized() * size * distance
    camera.rotation_euler = (middle - camera.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.collection.objects.link(camera)
    bpy.context.scene.camera = camera
    return camera


def camera_aimed(location, target, lens):
    """A camera at `location` looking at `target`, not made the scene's camera."""
    camera = bpy.data.objects.new("aimed", bpy.data.cameras.new("aimed"))
    camera.data.lens = lens
    camera.location = location
    camera.rotation_euler = (Vector(target) - Vector(location)).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.collection.objects.link(camera)
    return camera


def test_piece():
    """The swatch's test piece (swatch.py, likeness.py), its parts joined, smooth where curved, true edges kept."""
    parts = []
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, 0.015))
    plate = bpy.context.object
    plate.scale = (0.4, 0.4, 0.03)
    parts.append(plate)
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(-0.06, 0.05, 0.045))
    boss = bpy.context.object
    boss.scale = (0.16, 0.12, 0.03)
    parts.append(boss)
    for across in (-0.15, 0.15):
        bpy.ops.mesh.primitive_cylinder_add(radius=0.014, depth=0.012, vertices=12, location=(across, 0.15, 0.036))
        parts.append(bpy.context.object)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.035, depth=0.42, vertices=32, location=(0.0, -0.11, 0.065),
                                        rotation=(0.0, math.pi / 2, 0.0))
    parts.append(bpy.context.object)
    for part in parts:
        bpy.ops.object.select_all(action="DESELECT")
        part.select_set(True)
        bpy.context.view_layer.objects.active = part
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
        bevel = part.modifiers.new("bevel", "BEVEL")
        bevel.width = 0.003
        bevel.segments = 2
        bevel.limit_method = "ANGLE"
        bpy.ops.object.modifier_apply(modifier=bevel.name)
    bpy.ops.object.select_all(action="DESELECT")
    for part in parts:
        part.select_set(True)
    bpy.context.view_layer.objects.active = plate
    bpy.ops.object.join()
    bpy.ops.object.shade_auto_smooth(angle=math.radians(35))
    return plate
