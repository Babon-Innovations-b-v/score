"""Inside Blender (bench.py's look step, through the card queue, #182): a made model's finish drawn as the bake paints
it, the model whole (its own vertex normals kept) under one material, each slot's library recipe mixed in by its texel
mask on the model's own UVs (recipes.masked) and darkened by the model's own ambient occlusion baked on them
(bake.occlusion, #206: tc6w2's anesthesia machine drawn one flat white where NVIDIA's shades into its seams), seen from
the close-up's view direction and up (a flat row from straight above, +y up), framed on its own box under the close-up's
own studio light (closeup.lit: two large area lamps and a dim grey sky), so it is lit as NVIDIA's input render it is
held to. Under the library renders' two suns and a bright, even grey world a mirror finish reflects only that grey:
tc5r's chrome chucks, nozzle and rods were drawn dull flat grey at roughness 0.13, where the input's chrome shines
(#159). Drawn at wear 0 and dirt 0: the bench names none. Then the mesh alone (`bare.png`, the job's `bare`): the same
model, camera and light in one plain white surface, its own vertex normals kept, which the look's holes check reads
(bench.py look_holes, #159: the printer box's normals turned inward drew black holes through its front).
The mesh is laid in the model's own frame first (`laid`), as its finish placed the decals and the recipes measure in
metres; each text decal's box as drawn is written beside the picture (`marks.json`), which the bench reads back (#185).
A job naming a `usd` in place of a `glb` draws NVIDIA's own model, its own materials, by this camera and light alone
(`truth_drawn`): the look's light held to the close-up it was drawn into (bench.light_step, #206).

    blender -b -P look.py -- <look.json (finish.look_job's)>
"""
import json
import math
import pathlib
import sys

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Matrix, Vector

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "library" / "inside"))
sys.path.insert(0, str(HERE))
import runtime  # noqa: E402

runtime.ready()
import bake  # noqa: E402  (the model's own ambient occlusion, #206)
import closeup  # noqa: E402  (the close-up's light, `lit`)
import recipes  # noqa: E402
import scene_setup  # noqa: E402
from finish import look_axes  # noqa: E402

BARE_WHITE = (0.8, 0.8, 0.8, 1.0)  # the mesh-alone picture's one surface: the principled default's white


def look_material(masks, occlusion=None):
    """One material: each slot's recipe (at wear 0, dirt 0 and its spec's seed) mixed over the ones before it by its
    texel mask, read on the model's active UVs, a glass's alpha drawn as the bake carries it (recipes.shaded's
    `through`, #186), every base colour darkened by the model's own ambient occlusion (`occlusion`, #206)."""
    entries = [(mask["mask"], recipes.channels(mask["spec"], 0.0, 0.0, mask["spec"]["seed"])) for mask in masks]
    material = recipes.masked(entries, lambda found: recipes.shaded(found, through=True), uv_map="",
                              occlusion=occlusion).item()
    material.displacement_method = "BUMP"
    return material


def occluded(meshes, masks):
    """The model's own ambient occlusion on its active UVs, at its texel masks' side (bake.occlusion, as the place's
    bake gives its finish, #206)."""
    side = bpy.data.images.load(str(masks[0]["mask"]), check_existing=True).size[0]
    return bake.occlusion(meshes, "", side, bake.occlusion_reach(meshes))


def laid(meshes):
    """Each mesh's own data moved into the model's frame and its object left at none (#185): final.glb's mesh sits
    under a `fitted` node that turns and scales it, so in its object coordinates the decals (placed in the model's
    frame) printed on its side, smeared, and the recipes' sizes in metres were drawn a third too large."""
    for item in meshes:
        placed = item.matrix_world.copy()
        item.parent = None
        item.data.transform(placed)
        item.data.update()
        item.matrix_world = Matrix.Identity(4)
    bpy.context.view_layer.update()  # each bound_box (framed's) read anew


def mark_boxes(scene, masks):
    """[{"text", "box": [left, top, right, bottom] pixels}] of each text decal of the slots' specs as drawn: its four
    corners (recipes.decal_axes about its `at`, its size) seen through the scene's camera."""
    side = scene.render.resolution_x
    found = []
    for mask in masks:
        for decal in mask["spec"].get("decals") or []:
            if not decal.get("text"):
                continue
            right, up, _ = recipes.decal_axes(decal)
            width, height = decal["size_m"]
            corners = [Vector(decal["at"]) + Vector(right) * (across * width / 2) + Vector(up) * (upward * height / 2)
                       for across in (-1, 1) for upward in (-1, 1)]
            seen = [world_to_camera_view(scene, scene.camera, corner) for corner in corners]
            columns, rows = [point.x * side for point in seen], [(1 - point.y) * side for point in seen]
            found.append({"text": decal["text"], "box": [min(columns), min(rows), max(columns), max(rows)]})
    return found


def framed(scene, meshes, job):
    """A camera on the close-up's view direction and up (finish.look_axes of the job's eye, aim and up), framing the
    meshes' box at its fov."""
    corners = [item.matrix_world @ Vector(corner) for item in meshes for corner in item.bound_box]
    low = Vector([min(corner[axis] for corner in corners) for axis in range(3)])
    high = Vector([max(corner[axis] for corner in corners) for axis in range(3)])
    centre, radius = (low + high) / 2, (high - low).length / 2
    right, up, back = (Vector(axis) for axis in look_axes(job))
    distance = radius / math.sin(math.radians(job["fov"]) / 2) * 1.05
    data = bpy.data.cameras.new("look")
    data.sensor_fit, data.angle = "VERTICAL", math.radians(job["fov"])
    data.clip_start, data.clip_end = 0.001 * radius, 100 * radius
    camera = bpy.data.objects.new("look", data)
    scene.collection.objects.link(camera)
    camera.matrix_world = Matrix.Translation(centre + back * distance) @ Matrix((right, up, back)).transposed().to_4x4()
    scene.camera = camera
    return [list(low), list(high)]


def drawn(scene, path):
    """The scene rendered to `path` as an RGBA PNG."""
    scene.render.filepath = path
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    bpy.ops.render.render(write_still=True)


def bare_material():
    """One plain white surface: the mesh alone, shaded by its own normals."""
    material = bpy.data.materials.new("bare")
    material.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = BARE_WHITE
    return material


def seen(scene, meshes, job):
    """The look's camera framing the meshes (framed) and the close-up's own light on their box (closeup.lit, #200):
    one setting for a made model and for NVIDIA's own (truth_drawn), so the light the bench holds to the close-up is
    the light every look is drawn under (#206). The box."""
    box = framed(scene, meshes, job)
    closeup.lit(scene, *box, {"eye": list(scene.camera.matrix_world.translation)})
    return box


def truth_drawn(scene, job):
    """NVIDIA's own model (the job's `usd`, read as closeup.imported reads it, its own materials) drawn by this look's
    camera and light to the job's `out`: the look's light calibration (bench.light_step, #206), held to the
    close-up NVIDIA's model was drawn into."""
    meshes = closeup.imported(pathlib.Path(job["usd"]))
    box = seen(scene, meshes, job)
    drawn(scene, job["out"])
    print("LOOK", json.dumps({"out": job["out"], "box": box, "truth": job["usd"]}), flush=True)


def main():
    job = json.loads(pathlib.Path(sys.argv[sys.argv.index("--") + 1]).read_text())
    scene = scene_setup.empty_scene(job["side"], job["samples"])
    if job.get("usd"):
        truth_drawn(scene, job)
        return
    bpy.ops.import_scene.gltf(filepath=job["glb"])
    meshes = [item for item in scene.objects if item.type == "MESH"]
    laid(meshes)
    material = look_material(job["masks"], occluded(meshes, job["masks"]))
    for item in meshes:
        item.data.materials.clear()
        item.data.materials.append(material)
    box = seen(scene, meshes, job)
    drawn(scene, job["out"])
    bare = bare_material()
    for item in meshes:
        item.data.materials.clear()
        item.data.materials.append(bare)
    drawn(scene, job["bare"])
    marks = pathlib.Path(job["out"]).with_name("marks.json")
    marks.write_text(json.dumps(mark_boxes(scene, job["masks"]), indent=1))
    print("LOOK", json.dumps({"out": job["out"], "box": box, "slots": [mask["slot"] for mask in job["masks"]]}),
          flush=True)


main()
