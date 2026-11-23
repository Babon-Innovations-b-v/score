"""Inside Blender (bench.py's look step, through the card queue, #182): a made model's finish drawn as the bake paints
it, the model whole (its own vertex normals kept) under one material, each slot's library recipe mixed in by its
texel mask on the model's own UVs (recipes.masked), seen from the close-up's view direction, framed on its own box
under the library renders' studio light on a light grey world. Drawn at wear 0 and dirt 0: the bench names none.

    blender -b -P look.py -- <look.json (finish.look_job's)>
"""
import json
import math
import pathlib
import sys

import bpy
from mathutils import Matrix, Vector

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "library" / "inside"))
import runtime  # noqa: E402

runtime.ready()
import recipes  # noqa: E402
import scene_setup  # noqa: E402

WORLD_GREY = 0.8


def look_material(masks):
    """One material: each slot's recipe (at wear 0, dirt 0 and its spec's seed) mixed over the ones before it by its
    texel mask, read on the model's active UVs."""
    entries = [(mask["mask"], recipes.channels(mask["spec"], 0.0, 0.0, mask["spec"]["seed"])) for mask in masks]
    material = recipes.masked(entries, recipes.shaded, uv_map="").item()
    material.displacement_method = "BUMP"
    return material


def framed(scene, meshes, job):
    """A camera on the close-up's view direction (job eye and aim), framing the meshes' box at its fov."""
    corners = [item.matrix_world @ Vector(corner) for item in meshes for corner in item.bound_box]
    low = Vector([min(corner[axis] for corner in corners) for axis in range(3)])
    high = Vector([max(corner[axis] for corner in corners) for axis in range(3)])
    centre, radius = (low + high) / 2, (high - low).length / 2
    back = (Vector(job["eye"]) - Vector(job["aim"])).normalized()
    distance = radius / math.sin(math.radians(job["fov"]) / 2) * 1.05
    data = bpy.data.cameras.new("look")
    data.sensor_fit, data.angle = "VERTICAL", math.radians(job["fov"])
    data.clip_start, data.clip_end = 0.001 * radius, 100 * radius
    camera = bpy.data.objects.new("look", data)
    scene.collection.objects.link(camera)
    up = Vector((0, 0, 1))
    right = up.cross(back).normalized()
    camera.matrix_world = Matrix.Translation(centre + back * distance) @ Matrix(
        (right, back.cross(right), back)).transposed().to_4x4()
    scene.camera = camera
    return [list(low), list(high)]


def main():
    job = json.loads(pathlib.Path(sys.argv[sys.argv.index("--") + 1]).read_text())
    scene = scene_setup.empty_scene(job["side"], job["samples"])
    bpy.ops.import_scene.gltf(filepath=job["glb"])
    meshes = [item for item in scene.objects if item.type == "MESH"]
    material = look_material(job["masks"])
    for item in meshes:
        item.data.materials.clear()
        item.data.materials.append(material)
    box = framed(scene, meshes, job)
    scene_setup.studio_light()
    scene.world.node_tree.nodes["Background"].inputs[0].default_value = (WORLD_GREY, WORLD_GREY, WORLD_GREY, 1)
    scene.render.filepath = job["out"]
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    bpy.ops.render.render(write_still=True)
    print("LOOK", json.dumps({"out": job["out"], "box": box, "slots": [mask["slot"] for mask in job["masks"]]}),
          flush=True)


main()
