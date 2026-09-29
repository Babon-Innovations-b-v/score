"""Run inside Blender: texture coordinates for one part, by Blender's smart projection.

    blender -b -P blender_unwrap.py -- <in.npz> <out.npz> [angle in degrees] [margin]

Reads `points` and `faces`; writes `corner_uv` (a pair for each corner of each face, v running
up the picture) for the same faces in the same order, so the caller splits the points along the
texture seams itself.
"""
import math
import sys

import bpy
import numpy as np

ARGUMENTS = sys.argv[sys.argv.index("--") + 1:]
SOURCE, OUT = ARGUMENTS[0], ARGUMENTS[1]
ANGLE = float(ARGUMENTS[2]) if len(ARGUMENTS) > 2 else 66.0
MARGIN = float(ARGUMENTS[3]) if len(ARGUMENTS) > 3 else 0.006


def mesh_object(points, faces):
    """The mesh as the one selected, active object in an empty scene."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    mesh = bpy.data.meshes.new("part")
    mesh.from_pydata(points.tolist(), [], faces.tolist())
    mesh.update()
    thing = bpy.data.objects.new("part", mesh)
    bpy.context.scene.collection.objects.link(thing)
    bpy.context.view_layer.objects.active = thing
    thing.select_set(True)
    return thing


def unwrap():
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(ANGLE), island_margin=MARGIN,
                             area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode="OBJECT")


def corner_uv(mesh, faces):
    """Each face's three texture coordinates, checked to be the faces that went in."""
    layer = mesh.uv_layers.active.data
    corner = np.zeros((len(mesh.loops), 2))
    layer.foreach_get("uv", corner.ravel())
    order = np.zeros(len(mesh.polygons) * 3, dtype=np.int64)
    for index, polygon in enumerate(mesh.polygons):
        if polygon.loop_total != 3:
            raise SystemExit("not a triangle")
        order[index * 3:index * 3 + 3] = range(polygon.loop_start, polygon.loop_start + 3)
    check = np.array([mesh.loops[loop].vertex_index for loop in order]).reshape(-1, 3)
    if not (check == faces).all():
        raise SystemExit("face order changed")
    return corner[order].reshape(-1, 3, 2)


def main():
    data = np.load(SOURCE)
    faces = data["faces"].astype(np.int64)
    thing = mesh_object(data["points"], faces)
    unwrap()
    np.savez(OUT, corner_uv=corner_uv(thing.data, faces))
    print("UNWRAPPED", SOURCE, len(faces))


main()
