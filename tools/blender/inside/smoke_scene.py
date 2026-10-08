"""Runs inside Blender: the smoke test's scene, a cube on a floor seen by a camera (smoke.py)."""
import math

import bpy


def clear():
    for item in list(bpy.data.objects):
        bpy.data.objects.remove(item, do_unlink=True)


def add_shapes():
    bpy.ops.mesh.primitive_plane_add(size=8, location=(0, 0, 0))
    bpy.context.active_object.name = "floor"
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0.5))
    cube = bpy.context.active_object
    cube.name = "cube"
    paint = bpy.data.materials.new("cube-red")
    paint.diffuse_color = (0.8, 0.15, 0.1, 1.0)
    paint.use_nodes = True
    paint.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.8, 0.15, 0.1, 1.0)
    cube.data.materials.append(paint)


def add_camera_and_light(scene):
    bpy.ops.object.camera_add(location=(3.2, -3.2, 2.4))
    camera = bpy.context.active_object
    camera.name = "camera"
    look = camera.constraints.new("TRACK_TO")
    look.target = bpy.data.objects["cube"]
    scene.camera = camera
    bpy.ops.object.light_add(type="SUN", rotation=(math.radians(50), 0, math.radians(30)))
    bpy.context.active_object.data.energy = 3.0


def set_render(scene):
    """Cycles on the processor, small and quick: the smoke test proves the route, not the look."""
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 16
    scene.render.resolution_x = 512
    scene.render.resolution_y = 288


def build():
    scene = bpy.context.scene
    clear()
    add_shapes()
    add_camera_and_light(scene)
    set_render(scene)
    print(f"objects: {sorted(item.name for item in scene.objects)}")
