"""Runs inside Blender on the cluster (`../../cloud/blender_cloud.py`): the settle check as MuJoCo saw it, for the
demo film's physics card (tools/review/opening.py): the chosen loose objects' convex hulls (what MuJoCo collides them
by) resting on the triangles near them (their statics), from the place's settle job
(score/stages/place_build/ready/settle_mujoco.py's job.npz: `hull_<name>`, `statics_<name>`, metres, y up).

    blender -b --python tools/blender/inside/settle_view.py -- <job.json>

The job: {"npz": the settle job, "objects": [name, ...], "out": png, "size": [width, height], "samples", "reach":
metres of statics kept round the objects}. The hulls are the job's own points; their places are where the settle laid
them (the settle moved each by under a few centimetres, its record says how far).
"""
import json
import math
import pathlib
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Vector

HULL_COLOUR = (0.62, 0.30, 0.13, 1.0)
STATIC_COLOUR = (0.36, 0.37, 0.39, 1.0)


def blender_points(points):
    """Points (n, 3), y up, as Blender's z up."""
    return np.stack([points[:, 0], -points[:, 2], points[:, 1]], axis=1)


def material(name, colour, roughness):
    found = bpy.data.materials.new(name)
    found.use_nodes = True
    shader = found.node_tree.nodes["Principled BSDF"]
    shader.inputs["Base Color"].default_value = colour
    shader.inputs["Roughness"].default_value = roughness
    return found


def hull_object(name, points, look):
    """The convex hull of `points` as a mesh object in `look`."""
    mesh = bmesh.new()
    for point in points:
        mesh.verts.new(point)
    bmesh.ops.convex_hull(mesh, input=mesh.verts)
    data = bpy.data.meshes.new(name)
    mesh.to_mesh(data)
    mesh.free()
    found = bpy.data.objects.new(name, data)
    data.materials.append(look)
    bpy.context.scene.collection.objects.link(found)
    return found


def statics_object(triangles, low, high, look):
    """The static triangles whose bounds meet the box `low`..`high` (a floor's long fan triangles too), one mesh."""
    inside = np.all((triangles.min(axis=1) <= high) & (triangles.max(axis=1) >= low), axis=1)
    kept = triangles[inside].reshape(-1, 3)
    data = bpy.data.meshes.new("statics")
    data.from_pydata([tuple(point) for point in kept], [], [(index, index + 1, index + 2)
                                                           for index in range(0, len(kept), 3)])
    data.validate()
    found = bpy.data.objects.new("statics", data)
    data.materials.append(look)
    bpy.context.scene.collection.objects.link(found)
    return found


def scene(size, samples):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    found = bpy.context.scene
    found.render.engine = "CYCLES"
    found.cycles.device = "CPU"
    found.cycles.samples = samples
    found.cycles.use_denoising = True
    found.render.resolution_x, found.render.resolution_y = size
    found.render.film_transparent = True
    found.view_settings.view_transform = "Standard"
    world = bpy.data.worlds.new("world")
    found.world = world
    world.use_nodes = True
    background = next(node for node in world.node_tree.nodes if node.type == "BACKGROUND")
    background.inputs[0].default_value = (0.5, 0.52, 0.56, 1.0)
    background.inputs[1].default_value = 0.35
    return found


def lights(middle, reach):
    sun = bpy.data.lights.new("sun", "SUN")
    sun.energy = 2.2
    sun.angle = math.radians(8)
    holder = bpy.data.objects.new("sun", sun)
    holder.rotation_euler = (math.radians(40), 0.0, math.radians(35))
    bpy.context.scene.collection.objects.link(holder)
    fill = bpy.data.lights.new("fill", "AREA")
    fill.energy = 40.0 * reach * reach
    fill.size = reach * 2
    lamp = bpy.data.objects.new("fill", fill)
    lamp.location = middle + Vector((-reach, -reach, reach * 1.5))
    lamp.rotation_euler = (Vector((0, 0, 0)) - Vector((-1, -1, 1.5))).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.collection.objects.link(lamp)


def camera(middle, span, size):
    """A camera three-quarters above, aimed at `middle`, far enough that `span` metres fill the frame's width."""
    data = bpy.data.cameras.new("camera")
    data.lens = 50
    holder = bpy.data.objects.new("camera", data)
    bpy.context.scene.collection.objects.link(holder)
    direction = Vector((0.75, -1.0, 0.85)).normalized()
    distance = span / (2 * math.tan(data.angle_x / 2)) * 1.15
    holder.location = middle + direction * distance
    holder.rotation_euler = (middle - holder.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = holder


def main():
    job = json.loads(pathlib.Path(sys.argv[sys.argv.index("--") + 1]).read_text())
    found = np.load(job["npz"], allow_pickle=True)
    scene(job["size"], job["samples"])
    hull_look, static_look = material("hull", HULL_COLOUR, 0.55), material("static", STATIC_COLOUR, 0.8)
    hulls = {name: blender_points(found[f"hull_{name}"]) for name in job["objects"]}
    every = np.concatenate(list(hulls.values()))
    low, high = every.min(axis=0) - job["reach"], every.max(axis=0) + job["reach"]
    low[2] = every[:, 2].min() - 0.05  # the floor they stand on, nothing under it (terrain below a deck)
    for name, points in hulls.items():
        hull_object(name, points, hull_look)
    triangles = np.concatenate([blender_points(found[f"statics_{name}"].reshape(-1, 3)).reshape(-1, 3, 3)
                                for name in job["objects"]])
    # Objects side by side share their statics (each other, the floor): each triangle once, or the copies fight.
    triangles = np.unique(np.round(triangles.reshape(-1, 9), 5), axis=0).reshape(-1, 3, 3)
    statics_object(triangles, low, high, static_look)
    middle = Vector(((every.min(axis=0) + every.max(axis=0)) / 2).tolist())
    span = float(np.max(every.max(axis=0)[:2] - every.min(axis=0)[:2])) + job["reach"]
    lights(middle, span)
    camera(middle, span, job["size"])
    bpy.context.scene.render.filepath = job["out"]
    bpy.ops.render.render(write_still=True)


main()
