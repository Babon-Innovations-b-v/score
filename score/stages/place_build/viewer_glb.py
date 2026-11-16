"""review.viewer's Blender side: the scene (review.kept_stage's: the objects not kept, the sky and lights inactive)
read as Blender's USD reader reads it and written as one GLB with Draco-compressed meshes and JPEG textures, its
meshes decimated to about FACES faces in all, each texture shrunk to at most TEXTURES[0] pixels and halved again until
the file fits the megabytes asked.
Writes <out>.json beside it: {"texture": the pixels the last write kept, "megabytes"}.

    blender -b --python viewer_glb.py -- <viewer.usda> <out.glb> <megabytes>
"""
import json
import pathlib
import sys

import bpy

TEXTURES = (1024, 512, 256, 128)
FACES = 600_000  # the GLB's faces at most, about (Draco: some 10 bytes a face)
SMALL = 2000  # a mesh with no more faces than this is kept whole
QUALITY = 80


def arguments():
    given = sys.argv[sys.argv.index("--") + 1:]
    return pathlib.Path(given[0]), pathlib.Path(given[1]), float(given[2])


def lightened(faces):
    """Every mesh over SMALL faces decimated by one share, so the scene holds about `faces` faces in all (a viewer's
    model never ships: its shapes need only read at a glance). The faces before."""
    meshes = [item for item in bpy.data.objects if item.type == "MESH"]
    total = sum(len(item.data.polygons) for item in meshes)
    share = faces / max(total, 1)
    if share < 1.0:
        for item in meshes:
            if len(item.data.polygons) > SMALL:
                cut = item.modifiers.new("viewer", "DECIMATE")
                cut.ratio = max(share, SMALL / len(item.data.polygons))
    return total


def shrunk(pixels):
    """Every image at most `pixels` on its longer side."""
    for image in bpy.data.images:
        if image.size[0] and max(image.size) > pixels:
            scale = pixels / max(image.size)
            image.scale(max(1, round(image.size[0] * scale)), max(1, round(image.size[1] * scale)))


def written(path):
    """The scene as a GLB: Draco meshes, JPEG textures, no cameras or lights."""
    options = dict(filepath=str(path), export_format="GLB", export_draco_mesh_compression_enable=True,
                   export_draco_mesh_compression_level=6, export_image_format="JPEG", export_apply=True,
                   export_cameras=False, export_lights=False)
    try:
        bpy.ops.export_scene.gltf(**options, export_image_quality=QUALITY)
    except TypeError:
        bpy.ops.export_scene.gltf(**options, export_jpeg_quality=QUALITY)


def main():
    stage, out, megabytes = arguments()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    result = bpy.ops.wm.usd_import(filepath=str(stage), import_guide=False, import_proxy=False, import_lights=False,
                                   create_world_material=False)
    if "FINISHED" not in result:
        raise RuntimeError(f"Blender did not import {stage}: {result}")
    for layer_collection in bpy.context.view_layer.layer_collection.children:  # a point instancer's prototypes
        if layer_collection.collection.name.startswith("prototypes"):
            layer_collection.exclude = True
    print(f"viewer_glb: {lightened(FACES)} faces cut to about {FACES}")
    for pixels in TEXTURES:
        shrunk(pixels)
        written(out)
        size = out.stat().st_size / 1e6
        print(f"viewer_glb: {out} {size:.1f} MB at {pixels} px")
        if size <= megabytes:
            break
    out.with_suffix(".json").write_text(json.dumps({"texture": pixels, "megabytes": round(size, 2)}))


main()
