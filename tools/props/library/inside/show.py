"""Runs inside Blender (on a rented machine, cloud/library_bake.py): pictures of made pieces side by side, for a page.

The job: {"out", "size", "samples", "rows": [{"name", "models": [.glb paths]}], optional "frame_depth", "distance" and "gap"
(the framed depth and how far the camera stands, as camera_on takes it: small pieces up close)}. Each row's models stand side by
side in one frame, lit as the swatches are, seen three-quarter from the front; writes <out>/<name>.png. Used to lay
one piece made for two places (the same library, each place's own tokens) or two routes' pieces next to each other.
"""
import json
import pathlib
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import runtime  # noqa: E402

runtime.ready()
import scene_setup  # noqa: E402

GAP = 0.25


def stood(path, offset):
    """A model imported and stood on the floor at `offset` along x; its width and height."""
    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    found = [item for item in bpy.context.scene.objects if item not in before and item.type == "MESH"]
    low = Vector((min(min((item.matrix_world @ Vector(corner)).x for corner in item.bound_box) for item in found),
                  min(min((item.matrix_world @ Vector(corner)).y for corner in item.bound_box) for item in found),
                  min(min((item.matrix_world @ Vector(corner)).z for corner in item.bound_box) for item in found)))
    high = Vector((max(max((item.matrix_world @ Vector(corner)).x for corner in item.bound_box) for item in found),
                   max(max((item.matrix_world @ Vector(corner)).y for corner in item.bound_box) for item in found),
                   max(max((item.matrix_world @ Vector(corner)).z for corner in item.bound_box) for item in found)))
    for item in found:
        if item.parent is None:
            item.location += Vector((offset - low.x, -(low.y + high.y) / 2, -low.z))
    return high.x - low.x, high.z - low.z


def main():
    job = json.loads(pathlib.Path(sys.argv[sys.argv.index("--") + 1]).read_text())
    out = pathlib.Path(job["out"])
    out.mkdir(parents=True, exist_ok=True)
    for row in job["rows"]:
        scene_setup.empty_scene(job["size"], job["samples"])
        bpy.context.scene.render.resolution_x = int(job["size"] * 1.6)
        offset, tallest = 0.0, 0.0
        # Seen from in front (Blender +y), the first model stands on the right: they are laid right to left.
        for path in reversed(row["models"]):
            wide, tall = stood(path, offset)
            offset += wide + job.get("gap", GAP)
            tallest = max(tallest, tall)
        bpy.ops.mesh.primitive_cube_add(size=1.0)
        frame = bpy.context.object
        frame.dimensions = (offset, job.get("frame_depth", 0.3), tallest)
        frame.location = (offset / 2, 0.0, tallest / 2)
        bpy.context.view_layer.update()
        scene_setup.camera_on(frame, (0.3, 1.0, 0.3), job.get("distance", 3.2), lens=50)
        bpy.data.objects.remove(frame, do_unlink=True)
        scene_setup.studio_light()
        bpy.context.scene.render.filepath = str(out / f"{row['name']}.png")
        bpy.ops.render.render(write_still=True)
        print("SHOWN", row["name"], flush=True)


main()
