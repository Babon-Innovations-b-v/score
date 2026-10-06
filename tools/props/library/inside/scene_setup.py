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
    """A factory-empty scene drawing with Cycles at `size` pixels square, transparent behind: on the card where
    FARM_CYCLES_GPU is set (the rented machines), else on the processor."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    if os.environ.get("FARM_CYCLES_GPU"):
        use_card(scene)
    scene.cycles.samples = samples
    scene.cycles.use_denoising = False
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
