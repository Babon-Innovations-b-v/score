"""Runs inside Blender: a scene package's palette recipes baked as the preview draws them (scene_package.bake_jobs),
each part's recipe (tools/props/library/recipes.py: edge wear, dirt, relief, at the place's wear and dirt and the
variant's seed) given off channel by channel into its own maps, so the engine gets the recipe's exact colour,
roughness and metal, not a lit picture, and the normal map is baked from the shaded recipe (its relief and bump), as
tools/props/library/inside/bake.py bakes the props. A part is baked in its object's own frame (z up, metres, its
other parts beside it), on the texture coordinates scene_package unwrapped for it; a laid ground's recipe is baked once
on a flat GROUND_TILE square and blended seamless (seamless), the package box-projecting it over the ground.
A picture-made model's part (a job's `shade`, scene_package.shade_of, #209) has its base colour darkened by the model's
own ambient occlusion on its map, every other part of the model shading it too (tools/props/library/inside/bake.py
occlusion, as the bench's look and make_chunky's take bake give theirs, #206), and in the seams its decoded mesh holds
where make kept one (bake.seamed, #159 route C): so the place's bake draws it as its bench look does. Where the
finish route ran on the model in its place (the shade's `finish`, scene_package.finish_of, #213), each of its maps is
baked from the model itself (finish_model, bake_finished): its slots' recipes and decals mixed by their texel masks on
its own UVs, at the place's wear and dirt, darkened by its own occlusion, as bake.bake_from bakes a take's masks.

    blender -b --python bake_looks.py -- <jobs.json>        (scene_package.blender_baked, through the card queue)

A run bakes the few maps of one object it is handed (scene_package.BATCH), each map's pictures written under the
listing's `into` as <key>_<picture>.png and then its <key>.done mark, so a run that stops leaves every map it finished
for the next run to keep; what a map made (its materials, a tile's square, its pixels) is freed before the next.
"""
import gc
import json
import pathlib
import sys
import time

import bpy
import numpy as np
from mathutils import Matrix

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tools/props/library/inside"))
import runtime  # noqa: E402

runtime.ready()
import bake as props_bake  # noqa: E402  (the model's own ambient occlusion and its seams, #206, #159)
import procfunc as pf  # noqa: E402
import recipes  # noqa: E402
import scene_setup  # noqa: E402

SAMPLES = 16  # the props' bake samples (make_chunky.BAKE_SAMPLES): the wear's bevel and the dirt's occlusion
MARGIN = 4  # pixels a bake bleeds past each chart (scene_package.PADDING)
CHANNELS = (("base_color", True), ("roughness", False), ("metallic", False))
# How far a part's bake looks for its finish's model (bake_finished): the part is that model's own surface, converted,
# so a share of the model's box diagonal, at least FINISH_LEAST metres.
FINISH_REACH, FINISH_LEAST = 0.01, 0.002


def picture(name, size, colour):
    found = bpy.data.images.new(name, size[0], size[1], alpha=False, float_buffer=False)
    found.colorspace_settings.name = "sRGB" if colour else "Non-Color"
    return found


def targeted(material, target):
    """A material with `target` as its active image node, the bake's target."""
    node = material.node_tree.nodes.new("ShaderNodeTexImage")
    node.image = target
    material.node_tree.nodes.active = node
    return material


def worn(item, material):
    """Every slot of the object given one material."""
    item.data.materials.clear()
    item.data.materials.append(material)
    for face in item.data.polygons:
        face.material_index = 0


def tile_square(side):
    """A flat square of `side` metres from the origin, its texture coordinates its own position over the side, as
    scene_package box-projects a laid ground over GROUND_TILE."""
    mesh = bpy.data.meshes.new("tile")
    mesh.from_pydata([(0, 0, 0), (side, 0, 0), (side, side, 0), (0, side, 0)], [], [(0, 1, 2, 3)])
    layer = mesh.uv_layers.new(name="UVMap")
    for loop in mesh.loops:
        corner = mesh.vertices[loop.vertex_index].co
        layer.data[loop.index].uv = (corner.x / side, corner.y / side)
    item = bpy.data.objects.new("tile", mesh)
    bpy.context.scene.collection.objects.link(item)
    return item


def pixels_of(found):
    size = found.size
    values = np.empty(size[0] * size[1] * 4, dtype=np.float32)
    found.pixels.foreach_get(values)
    return values.reshape(size[1], size[0], 4)


def seamless(values):
    """A tile made to repeat without a seam: the tile and its copies rolled half a side across, down and both,
    each weighed away from its own seams (sin squared from its edges), so every edge meets its far edge."""
    tall, wide = values.shape[:2]
    across = np.sin(np.pi * (np.arange(wide) + 0.5) / wide) ** 2
    down = np.sin(np.pi * (np.arange(tall) + 0.5) / tall) ** 2
    x, y = across[None, :, None], down[:, None, None]
    rolled_x = np.roll(values, wide // 2, axis=1)
    rolled_y = np.roll(values, tall // 2, axis=0)
    rolled_both = np.roll(rolled_x, tall // 2, axis=0)
    return x * y * values + (1 - x) * y * rolled_x + x * (1 - y) * rolled_y + (1 - x) * (1 - y) * rolled_both


def unit_normals(values):
    """A normal map's colours made unit normals again (a blend shortens them)."""
    way = values[..., :3] * 2.0 - 1.0
    way /= np.maximum(np.linalg.norm(way, axis=-1, keepdims=True), 1e-6)
    values[..., :3] = way * 0.5 + 0.5
    return values


def saved(values, size, colour, path):
    """The pixels written as a PNG at `path`."""
    found = picture(path.stem, size, colour)
    found.pixels.foreach_set(np.ascontiguousarray(values, dtype=np.float32).ravel())
    path.parent.mkdir(parents=True, exist_ok=True)
    found.filepath_raw = str(path)
    found.file_format = "PNG"
    found.save()
    bpy.data.images.remove(found)


def resident_gb():
    """This Blender's memory now and at its highest (VmRSS, VmHWM), in GB."""
    status = dict(line.split(":", 1) for line in pathlib.Path("/proc/self/status").read_text().splitlines()
                  if ":" in line)
    return [round(int(status[name].split()[0]) / 1024 / 1024, 2) for name in ("VmRSS", "VmHWM")]


def freed():
    """Every material, mesh, image and node group nothing uses any more removed (a map's own), and Python's too."""
    for material in list(bpy.data.materials):
        if not material.users:
            bpy.data.materials.remove(material)
    bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
    gc.collect()


def decoded_of(shade):
    """The model's decoded mesh the job's `shade` names (its path in the place's made/ folder) imported as one object,
    or None where it names none (a model made before make kept it)."""
    if not shade.get("decoded"):
        return None
    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.gltf(filepath=shade["decoded"])
    found = [item for item in bpy.context.scene.objects if item not in before and item.type == "MESH"]
    if len(found) != 1:
        raise SystemExit(f"{shade['decoded']}: {len(found)} meshes, not the one decoded mesh")
    return found[0]


def occlusion_of(item, model, decoded, size):
    """The model's own ambient occlusion on the part `item`'s map (`size` [width, height]), the model's other parts
    (`model`, every mesh of its file) shading it too, darkened in the seams its `decoded` mesh holds where it has one
    (bake.occlusion, bake.seamed): a Non-Color picture on the part's active UVs."""
    among = [other for other in model if other is not item]
    reach = props_bake.occlusion_reach(model)
    if decoded is None:
        return props_bake.occlusion([item], "", list(size), reach, among=among)
    return props_bake.seamed([item], decoded, "", list(size), reach, among=among)


def occluded(channels, picture):
    """The Channels' base colour darkened by the occlusion `picture` read on the part's active UVs (recipes.occluded,
    as recipes.masked darkens the bench look's)."""
    uv = pf.nodes.shader.uv_map(uv_map="")
    shut = pf.nodes.math.separate_xyz(pf.nodes.texture.image(vector=uv, image=pf.Image(picture),
                                                             extension="EXTEND").color).x
    return recipes.occluded(channels, shut)


def bake(item, channels, size):
    """The recipe's channels baked onto the object's texture coordinates: {channel: pixels}; each channel's material
    and picture removed once read."""
    bpy.ops.object.select_all(action="DESELECT")
    item.select_set(True)
    bpy.context.view_layer.objects.active = item
    found = {}
    for channel, colour in CHANNELS + (("normal", False),):
        target = picture(f"bake_{channel}", size, colour)
        if channel == "normal":
            material = recipes.shaded(channels).item()
            material.displacement_method = "BUMP"
        else:
            material = recipes.emitted(getattr(channels, channel)).item()
        worn(item, targeted(material, target))
        bpy.ops.object.bake(type="NORMAL" if channel == "normal" else "EMIT", margin=MARGIN, use_clear=True,
                            normal_space="TANGENT")
        found[channel] = pixels_of(target)
        item.data.materials.clear()
        bpy.data.materials.remove(material)
        bpy.data.images.remove(target)
    return found


def finish_model(finish, decoded):
    """The finish route's model (its look job's `glb`: finished/route.py, #213) imported, its meshes laid in the model's
    own frame as the bench look lays them (look.py `laid`: the decals and the recipes' metres are placed there) and
    stood at the copy's turn and stretch (`stretch`, scene_package.finish_of) as their objects' place, so they lie on
    the part baked while reading their finish in their own frame: (its meshes, the look job, the model's own ambient
    occlusion on its own UVs at its masks' side, darkened in the seams of its `decoded` mesh where there is one, as the
    bench look's: look.py `occluded`)."""
    look = json.loads(pathlib.Path(finish["look"]).read_text())
    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.gltf(filepath=look["glb"])
    meshes = [item for item in bpy.context.scene.objects if item not in before and item.type == "MESH"]
    stood = Matrix(finish["stretch"]) if finish.get("stretch") else Matrix.Identity(4)
    for item in meshes:
        placed = item.matrix_world.copy()
        item.parent = None
        item.data.transform(placed)
        item.data.update()
        item.matrix_world = stood
    bpy.context.view_layer.update()
    side = bpy.data.images.load(look["masks"][0]["mask"], check_existing=True).size[0]
    reach = props_bake.occlusion_reach(meshes)
    shut = props_bake.occlusion(meshes, "", side, reach) if decoded is None else props_bake.seamed(
        meshes, decoded, "", side, reach)
    shut.use_fake_user = True  # kept through each map's freed()
    return meshes, look, shut


def bake_finished(item, finish, wear, dirt, size):
    """The finish route's masked recipes (each slot's spec, its decals with it, mixed by its texel mask on the model's
    own UVs: recipes.masked, as bake.bake_from mixes a take's) baked from the model (`finish`, finish_model's) onto the
    part `item`'s texture coordinates at the place's `wear` and `dirt`, its base colour darkened by the model's own
    occlusion: {channel: pixels}, each material and picture removed once read."""
    meshes, look, shut = finish
    entries = [(mask["mask"], recipes.channels(mask["spec"], wear, dirt, mask["spec"]["seed"]))
               for mask in look["masks"]]
    low, high = props_bake.box_of(meshes)
    reach = max(FINISH_LEAST, FINISH_REACH * (high - low).length)
    across = {"use_selected_to_active": True, "cage_extrusion": reach, "max_ray_distance": reach * 2}
    bpy.ops.object.select_all(action="DESELECT")
    for mesh in meshes:
        mesh.select_set(True)
    item.select_set(True)
    bpy.context.view_layer.objects.active = item
    found = {}
    for channel, colour in CHANNELS + (("normal", False),):
        target = picture(f"bake_{channel}", size, colour)
        if channel == "normal":
            material = props_bake.bumped(recipes.masked(entries, recipes.shaded, uv_map="").item())
        else:
            material = recipes.masked(entries, lambda channels: recipes.emitted(getattr(channels, channel)),
                                      relief=False, uv_map="", occlusion=shut).item()
        for mesh in meshes:
            worn(mesh, material)
        holder = bpy.data.materials.new("finish_target")
        holder.use_nodes = True
        worn(item, targeted(holder, target))
        bpy.ops.object.bake(type="NORMAL" if channel == "normal" else "EMIT", margin=MARGIN, use_clear=True,
                            normal_space="TANGENT", **across)
        found[channel] = pixels_of(target)
        for mesh in meshes + [item]:
            mesh.data.materials.clear()
        bpy.data.materials.remove(material)
        bpy.data.materials.remove(holder)
        bpy.data.images.remove(target)
    return found


def written(found, size, tiled, into, key):
    """A bake's pictures as glTF reads them (scene_package.PICTURES): base colour, metal-roughness (roughness in green,
    metal in blue) and the normal map, a tile's made seamless first, as <into>/<key>_<picture>.png, then its
    <key>.done mark."""
    if tiled:
        found = {channel: seamless(values) for channel, values in found.items()}
        found["normal"] = unit_normals(found["normal"])
    both = np.ones_like(found["roughness"])
    both[..., 1], both[..., 2] = found["roughness"][..., 0], found["metallic"][..., 0]
    saved(found["base_color"], size, True, into / f"{key}_base_color.png")
    saved(both, size, False, into / f"{key}_metal_roughness.png")
    saved(found["normal"], size, False, into / f"{key}_normal.png")
    (into / f"{key}.done").touch()


def baked_file(out, into, gltf, jobs):
    """Every job handed of one object's .gltf baked: the object imported whole (its parts beside the one baked)."""
    scene_setup.empty_scene(64, SAMPLES)
    bpy.context.scene.render.bake.margin_type = "EXTEND"
    if not all(job["tile"] for job in jobs):  # a ground's tile is baked on its own square, never on the ground
        bpy.ops.import_scene.gltf(filepath=str(out / gltf))
    model = [item for item in bpy.context.scene.objects if item.type == "MESH"]
    shade = next((job["shade"] for job in jobs if job.get("shade")), None)
    decoded = decoded_of(shade) if shade else None
    finish = finish_model(shade["finish"], decoded) if shade and shade.get("finish") else None
    for job in jobs:
        began = time.time()
        spec = job["spec"]
        item = tile_square(job["tile"]) if job["tile"] else bpy.data.objects[job["mesh"]]
        shut = None
        if finish and job.get("shade"):
            found = bake_finished(item, finish, spec["wear"], spec["dirt"], job["size"])
        else:
            channels = recipes.channels(spec, spec["wear"], spec["dirt"], recipes.SEED)
            shut = occlusion_of(item, model, decoded, job["size"]) if job.get("shade") else None
            found = bake(item, channels if shut is None else occluded(channels, shut), job["size"])
        if shut is not None:
            bpy.data.images.remove(shut)
        written(found, job["size"], bool(job["tile"]), into, job["key"])
        del found
        if job["tile"]:
            bpy.data.objects.remove(item)
        freed()
        now, highest = resident_gb()
        print(f"BAKED {gltf} {job['mesh']} {spec.get('library')} {job['size'][0]}x{job['size'][1]} "
              f"{time.time() - began:.1f} s, memory {now} GB (highest {highest} GB)", flush=True)


def main():
    listing = json.loads(pathlib.Path(sys.argv[sys.argv.index("--") + 1]).read_text())
    out, into = pathlib.Path(listing["out"]), pathlib.Path(listing["into"])
    into.mkdir(parents=True, exist_ok=True)
    by_file = {}
    for job in listing["jobs"]:
        by_file.setdefault(job["gltf"], []).append(job)
    for gltf, jobs in by_file.items():
        baked_file(out, into, gltf, jobs)
    print(f"BAKE DONE {len(listing['jobs'])} maps", flush=True)


main()
