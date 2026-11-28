"""budget.cut's Blender side: a made model's meshes cut to a share of their faces by Blender's Decimate (Collapse: the
quadric edge collapse, which keeps the silhouette, small hardware and holes and carries each corner's texture place
across a UV seam), written as a GLB of their geometry alone (the maker's GLB keeps everything else, budget.with_cut).
The model is read with its vertices merged by position, so a UV seam is an edge inside the mesh and never a border two
sides of which would collapse apart into a crack.

    blender -b --python budget_blender.py -- <in.glb> <out.glb> <faces>
"""
import json
import pathlib
import sys

import bpy

KEPT = 200  # a mesh with no more faces than this is kept whole (a part's lip, a hinge pin)


def arguments():
    given = sys.argv[sys.argv.index("--") + 1:]
    return pathlib.Path(given[0]), pathlib.Path(given[1]), int(given[2])


def cut(faces):
    """Every mesh over KEPT faces given one Decimate at the share that brings the model to about `faces`; the faces
    before."""
    meshes = [item for item in bpy.data.objects if item.type == "MESH"]
    total = sum(len(item.data.polygons) for item in meshes)
    share = faces / max(total, 1)
    for item in meshes:
        if share < 1.0 and len(item.data.polygons) > KEPT:
            decimate = item.modifiers.new("budget", "DECIMATE")
            decimate.ratio = max(share, KEPT / len(item.data.polygons))
            decimate.use_collapse_triangulate = True
    return total


def main():
    source, out, faces = arguments()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    result = bpy.ops.import_scene.gltf(filepath=str(source), merge_vertices=True)
    if "FINISHED" not in result:
        raise RuntimeError(f"Blender did not read {source}: {result}")
    before = cut(faces)
    bpy.ops.export_scene.gltf(filepath=str(out), export_format="GLB", export_apply=True, export_materials="NONE",
                              export_cameras=False, export_lights=False, export_yup=True)
    print("budget_blender: " + json.dumps({"before": before, "asked": faces}))


main()
