"""Runs in Blender (on a rented card, blender_cloud.py): the review frames of one made animal, from its exported file.

    blender -b --python tools/characters/animals/blender_review.py -- <animal.glb> <review folder> <raised> [<clip> ...]

The file is read back as the game would get it (so a fault in the export shows), then drawn on a plain floor with a
grid, which shows a foot that slides: <review>/turntable/NN.png (TURNTABLE views round it in its rest pose) and
<review>/<clip>/NN.png (one loop of each clip, every STEP-th frame, from a three-quarter view `raised` degrees above level: high for a
fish, whose swim bends it side to side, lower for a walk). Cycles on the
card, or on the processor's cores on a processor machine (blender_cloud.py sets FARM_CYCLES_GPU or FARM_CYCLES_CPU).
"""
import math
import os
import pathlib
import sys

import bpy
from mathutils import Vector

TURNTABLE = 12
STEP = 2
SIZE = (640, 480)
SAMPLES = 48


def renderer(scene):
    """Cycles, denoised, on the machine's card (OptiX, else CUDA) when it has one, else on its processor."""
    scene.render.engine = "CYCLES"
    scene.cycles.samples = SAMPLES
    scene.cycles.use_denoising = True
    scene.cycles.device = "CPU"
    if os.environ.get("FARM_CYCLES_GPU"):
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
    scene.render.resolution_x, scene.render.resolution_y = SIZE
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    # The plain tone curve, so the review shows the model's own colours (Blender's default curve washes them out).
    scene.view_settings.view_transform = "Standard"


def load(path):
    """An empty scene holding the file; its armature and its meshes."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = 30
    bpy.ops.import_scene.gltf(filepath=str(path))
    things = list(bpy.context.scene.objects)
    armature = next(thing for thing in things if thing.type == "ARMATURE")
    # The importer adds a mesh of its own to draw bones with; only the meshes the armature moves are the animal.
    return armature, [thing for thing in things if thing.type == "MESH" and thing.find_armature() == armature]


def bounds(meshes):
    """The meshes' lowest and highest corners in world space, at the current frame."""
    corners = [mesh.matrix_world @ Vector(corner) for mesh in meshes for corner in mesh.bound_box]
    low = Vector([min(corner[axis] for corner in corners) for axis in range(3)])
    high = Vector([max(corner[axis] for corner in corners) for axis in range(3)])
    return low, high


def floor_and_light(low, high):
    """A grey floor with a grid of 10 cm squares (scaled to the animal) just under it, a sun and a soft sky."""
    size = max(high - low)
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=40, y_subdivisions=40, size=size * 4,
                                    location=(0.0, 0.0, low.z - size * 0.002))
    grid = bpy.context.object
    wire = grid.modifiers.new("lines", "WIREFRAME")
    wire.thickness = size * 0.004
    lines = bpy.data.materials.new("lines")
    lines.diffuse_color = (0.2, 0.2, 0.2, 1.0)
    grid.data.materials.append(lines)
    bpy.ops.mesh.primitive_plane_add(size=size * 4, location=(0.0, 0.0, low.z - size * 0.003))
    sun = bpy.data.lights.new("sun", "SUN")
    sun.energy = 2.0
    holder = bpy.data.objects.new("sun", sun)
    holder.rotation_euler = (math.radians(40), 0.0, math.radians(30))
    bpy.context.scene.collection.objects.link(holder)
    world = bpy.data.worlds.new("sky")
    world.use_nodes = True
    background = next(node for node in world.node_tree.nodes if node.type == "BACKGROUND")
    background.inputs[0].default_value = (0.75, 0.78, 0.82, 1.0)
    background.inputs[1].default_value = 0.5
    bpy.context.scene.world = world


def camera(centre):
    """A camera that looks at `centre` from `reach` away, and an empty it tracks."""
    target = bpy.data.objects.new("target", None)
    target.location = centre
    bpy.context.scene.collection.objects.link(target)
    data = bpy.data.cameras.new("camera")
    data.lens = 60
    holder = bpy.data.objects.new("camera", data)
    bpy.context.scene.collection.objects.link(holder)
    track = holder.constraints.new("TRACK_TO")
    track.target = target
    bpy.context.scene.camera = holder
    return holder


def place_camera(holder, centre, reach, around, raised):
    """Put the camera `around` radians round the animal (0 is its left side), `raised` radians above level."""
    holder.location = centre + reach * Vector((math.cos(around) * math.cos(raised),
                                               math.sin(around) * math.cos(raised), math.sin(raised)))


def clip_actions():
    """Each imported clip's action by the clip's name."""
    return {action.name.split("_Armature")[0].split(".")[0]: action for action in bpy.data.actions}


def play(armature, action):
    """Put a clip on the armature (None for the rest pose)."""
    data = armature.animation_data_create()
    data.action = action
    if action is not None and getattr(action, "slots", None) and hasattr(data, "action_slot"):
        data.action_slot = action.slots[0]


def render(path):
    bpy.context.scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def main():
    arguments = sys.argv[sys.argv.index("--") + 1:]
    model, review, raised, clips = (pathlib.Path(arguments[0]), pathlib.Path(arguments[1]), float(arguments[2]),
                                    arguments[3:])
    armature, meshes = load(model)
    play(armature, None)
    bpy.context.scene.frame_set(0)
    low, high = bounds(meshes)
    centre = (low + high) / 2
    reach = max(high - low) * 3.2
    floor_and_light(low, high)
    holder = camera(centre)
    renderer(bpy.context.scene)
    for view in range(TURNTABLE):
        place_camera(holder, centre, reach, 2 * math.pi * view / TURNTABLE, math.radians(12))
        render(review / "turntable" / f"{view:02d}.png")
    actions = clip_actions()
    place_camera(holder, centre, reach, math.radians(35), math.radians(raised))
    for clip in clips:
        play(armature, actions[clip])
        start, end = (int(frame) for frame in actions[clip].frame_range)
        for frame in range(start, end, STEP):
            bpy.context.scene.frame_set(frame)
            render(review / clip / f"{frame:03d}.png")


if __name__ == "__main__":
    main()
