"""Run inside Blender: thin a mesh to about a number of triangles, keeping its open edges.

    blender -b -P blender_thin.py -- <in.npz> <out.npz> <triangles> [symmetric]

Blender's collapse thinning, with every point on an open edge (a neckline, a cuff, a hem) pinned
so the ends of the silhouette do not shrink. `symmetric` keeps the left and the right alike.
Reads and writes `points` and `faces`.
"""
import sys

import bmesh
import bpy
import numpy as np

ARGUMENTS = sys.argv[sys.argv.index("--") + 1:]
SOURCE, TARGET, COUNT = ARGUMENTS[0], ARGUMENTS[1], int(ARGUMENTS[2])
SYMMETRIC = "symmetric" in ARGUMENTS[3:]


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


def pin_the_open_edges(thing):
    """A vertex group holding every point not on an open edge: the thinning may move only those."""
    work = bmesh.new()
    work.from_mesh(thing.data)
    boundary = {vert.index for edge in work.edges if edge.is_boundary for vert in edge.verts}
    work.free()
    group = thing.vertex_groups.new(name="free")
    group.add([index for index in range(len(thing.data.vertices)) if index not in boundary],
              1.0, "REPLACE")
    return len(boundary)


def thin(thing, ratio):
    modifier = thing.modifiers.new("thin", "DECIMATE")
    modifier.decimate_type = "COLLAPSE"
    modifier.ratio = ratio
    modifier.use_collapse_triangulate = True
    modifier.vertex_group = "free"
    modifier.vertex_group_factor = 1.0
    if SYMMETRIC:
        modifier.use_symmetry = True
        modifier.symmetry_axis = "X"
    bpy.ops.object.modifier_apply(modifier="thin")


def triangles_of(thing):
    work = bmesh.new()
    work.from_mesh(thing.data)
    bmesh.ops.triangulate(work, faces=work.faces[:])
    work.verts.ensure_lookup_table()
    points = np.array([vert.co[:] for vert in work.verts])
    faces = np.array([[vert.index for vert in face.verts] for face in work.faces])
    return points, faces


def main():
    data = np.load(SOURCE, allow_pickle=True)
    thing = mesh_object(data["points"], data["faces"].astype(int))
    pinned = pin_the_open_edges(thing)
    thin(thing, min(1.0, COUNT / len(data["faces"])))
    points, faces = triangles_of(thing)
    np.savez(TARGET, points=points, faces=faces)
    print("THINNED", len(data["faces"]), "->", len(faces), "triangles;", pinned, "open-edge points pinned")


main()
