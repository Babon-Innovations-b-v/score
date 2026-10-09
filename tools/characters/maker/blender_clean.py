"""Clean a dense generated mesh in Blender, run headless: fewer triangles, flat areas made flat (unless NO_DISSOLVE is
set, as for hair). Moved here from the prop chain's Hi3DGen tools.

    blender --background --python blender_clean.py -- <in.glb> <out.glb> <triangles>

The common cleanup for generated meshes (image-to-3dlab does the same): collapse the mesh down to
a game's budget, then dissolve faces that lie nearly flat into one another, so a wall is a few big
flat faces rather than thousands of wobbling ones.
"""
import os
import sys

import bpy

source, target, budget = sys.argv[sys.argv.index("--") + 1:][:3]
budget = int(budget)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=source)
meshes = [thing for thing in bpy.context.scene.objects if thing.type == "MESH"]
bpy.context.view_layer.objects.active = meshes[0]
for thing in meshes:
    thing.select_set(True)
if len(meshes) > 1:
    bpy.ops.object.join()
body = bpy.context.view_layer.objects.active

# merge the seams the generator leaves, so faces meet as one surface
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.mesh.remove_doubles(threshold=0.0005)
bpy.ops.object.mode_set(mode="OBJECT")

faces = len(body.data.polygons)
collapse = body.modifiers.new("collapse", "DECIMATE")
collapse.decimate_type = "COLLAPSE"
collapse.ratio = min(1.0, (budget * 1.6) / max(faces, 1))
bpy.ops.object.modifier_apply(modifier="collapse")

if not os.environ.get("NO_DISSOLVE"):
    flat = body.modifiers.new("flat", "DECIMATE")
    flat.decimate_type = "DISSOLVE"
    flat.angle_limit = 0.07  # about 4 degrees: only nearly flat neighbours merge
    bpy.ops.object.modifier_apply(modifier="flat")

turn = body.modifiers.new("triangles", "TRIANGULATE")
bpy.ops.object.modifier_apply(modifier="triangles")

bpy.ops.export_scene.gltf(filepath=target, export_format="GLB", use_selection=False, export_apply=True)
print(f"cleaned: {faces} faces in, {len(body.data.polygons)} triangles out -> {target}")
