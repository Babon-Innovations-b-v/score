"""Thin a mesh stored as .npz (points, faces) to about a target triangle count with Blender's
quadric (collapse) decimation, keeping open edges where they are: the hair shell down to a game's budget. Moved here from round three's decimate.py (#100).

    blender -b -P blender_decimate.py -- <in.npz> <out.npz> <target triangles> [symmetric]

`symmetric` asks for left/right (x) symmetry, for the suit. Open edges (neckline, cuffs, hems)
are pinned through a vertex group so the silhouette's ends do not shrink.
"""
import sys

import bpy
import bmesh
import numpy as np

args = sys.argv[sys.argv.index("--") + 1:]
SOURCE, TARGET, COUNT = args[0], args[1], int(args[2])
SYMMETRIC = "symmetric" in args[3:]

bpy.ops.wm.read_factory_settings(use_empty=True)
data = np.load(SOURCE, allow_pickle=True)
mesh = bpy.data.meshes.new("m")
mesh.from_pydata(data["points"].tolist(), [], data["faces"].astype(int).tolist())
mesh.update()
thing = bpy.data.objects.new("m", mesh)
bpy.context.scene.collection.objects.link(thing)
bpy.context.view_layer.objects.active = thing
thing.select_set(True)

# Pin the open edges: a vertex group with the boundary at weight 0 and the rest at 1, used by the
# modifier as a factor (0 = never collapse).
work = bmesh.new()
work.from_mesh(mesh)
boundary = {vert.index for edge in work.edges if edge.is_boundary for vert in edge.verts}
work.free()
group = thing.vertex_groups.new(name="free")
group.add([index for index in range(len(mesh.vertices)) if index not in boundary], 1.0, "REPLACE")

modifier = thing.modifiers.new("thin", "DECIMATE")
modifier.decimate_type = "COLLAPSE"
modifier.ratio = min(1.0, COUNT / len(data["faces"]))
modifier.use_collapse_triangulate = True
modifier.vertex_group = "free"
modifier.vertex_group_factor = 1.0
if SYMMETRIC:
    modifier.use_symmetry = True
    modifier.symmetry_axis = "X"
bpy.ops.object.modifier_apply(modifier="thin")
work = bmesh.new()
work.from_mesh(thing.data)
bmesh.ops.triangulate(work, faces=work.faces[:])
work.verts.ensure_lookup_table()
points = np.array([vert.co[:] for vert in work.verts])
faces = np.array([[vert.index for vert in face.verts] for face in work.faces])
np.savez(TARGET, points=points, faces=faces)
print("DECIMATED", len(data["faces"]), "->", len(faces), "triangles;", len(boundary), "open-edge points pinned")
