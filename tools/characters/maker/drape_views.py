"""Runs inside Blender (headless, through tools/props/cloud/blender_cloud.py): pictures of drapes on their body from
the front and the side, every drape with the same cameras, so two simulators' drapes of one garment can be laid side by
side and compared.

    blender -b --python tools/characters/maker/drape_views.py -- <views.json>

views.json: {"body": "<ours.obj, metres, y up>", "drapes": {"<label>": "<*_sim.obj, centimetres>", ...},
             "out": "<folder>", "size": 900}
Writes <out>/<label>_front.png and <out>/<label>_side.png: Workbench, the cloth a flat grey-blue with its own shading
and outline so folds read, the body skin-coloured, an orthographic camera fitted to the body.
"""
import json
import math
import pathlib
import sys

import bpy
from mathutils import Matrix

CENTIMETRES = 0.01
# The pattern's frame (y up) onto Blender's (z up).
Y_UP_TO_Z_UP = Matrix(((1, 0, 0, 0), (0, 0, -1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))
CLOTH_COLOUR = (0.42, 0.52, 0.66, 1.0)
BODY_COLOUR = (0.86, 0.68, 0.56, 1.0)


def job():
    given = sys.argv[sys.argv.index("--") + 1:]
    if len(given) != 1:
        raise SystemExit(__doc__)
    return json.loads(pathlib.Path(given[0]).read_text())


def read_obj(path, scale):
    points, faces = [], []
    for line in pathlib.Path(path).read_text().splitlines():
        if line.startswith("v "):
            points.append(tuple(float(value) * scale for value in line.split()[1:4]))
        elif line.startswith("f "):
            corners = [int(token.split("/")[0]) - 1 for token in line.split()[1:]]
            faces.extend((corners[0], corners[index], corners[index + 1]) for index in range(1, len(corners) - 1))
    return points, faces


def placed(name, path, scale, colour):
    points, faces = read_obj(path, scale)
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(points, [], faces)
    mesh.shade_smooth()
    holder = bpy.data.objects.new(name, mesh)
    holder.matrix_world = Y_UP_TO_Z_UP
    holder.color = colour
    bpy.context.scene.collection.objects.link(holder)
    return holder


def set_up_scene(size):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = scene.render.resolution_y = size
    shading = scene.display.shading
    shading.light = "STUDIO"
    shading.color_type = "OBJECT"
    shading.show_cavity = True
    shading.cavity_type = "BOTH"
    shading.show_object_outline = True
    scene.render.film_transparent = False
    world = bpy.data.worlds.new("plain")
    world.color = (1.0, 1.0, 1.0)
    scene.world = world
    shading.background_type = "WORLD"
    return scene


def camera(scene, body, side):
    """An orthographic camera on the body's middle, from the front (+y in Blender, the pattern's +z) or its left."""
    corners = [body.matrix_world @ point.co for point in body.data.vertices]
    low = [min(corner[axis] for corner in corners) for axis in range(3)]
    high = [max(corner[axis] for corner in corners) for axis in range(3)]
    middle = [(low[axis] + high[axis]) / 2 for axis in range(3)]
    data = bpy.data.cameras.new("view")
    data.type = "ORTHO"
    data.ortho_scale = (high[2] - low[2]) * 1.08
    holder = bpy.data.objects.new("view", data)
    scene.collection.objects.link(holder)
    if side:
        holder.location = (middle[0] + 5.0, middle[1], middle[2])
        holder.rotation_euler = (math.pi / 2, 0, math.pi / 2)
    else:
        holder.location = (middle[0], middle[1] - 5.0, middle[2])
        holder.rotation_euler = (math.pi / 2, 0, 0)
    scene.camera = holder
    return holder


def render(scene, path):
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def main():
    task = job()
    out = pathlib.Path(task["out"])
    out.mkdir(parents=True, exist_ok=True)
    for label, drape in task["drapes"].items():
        scene = set_up_scene(task.get("size", 900))
        body = placed("body", task["body"], 1.0, BODY_COLOUR)
        placed("cloth", drape, CENTIMETRES, CLOTH_COLOUR)
        for side in (False, True):
            camera(scene, body, side)
            render(scene, out / f"{label}_{'side' if side else 'front'}.png")


if __name__ == "__main__":
    main()
