"""Runs inside Blender: a scene package's palette recipes baked as the preview draws them (scene_package.bake_jobs),
each part's recipe (tools/props/library/recipes.py: edge wear, dirt, relief, at the place's wear and dirt and the
variant's seed) given off channel by channel into its own maps, so the engine gets the recipe's exact colour,
roughness and metal, not a lit picture, and the normal map is baked from the shaded recipe (its relief and bump), as
tools/props/library/inside/bake.py bakes the props. A part is baked in its object's own frame (z up, metres, its
other parts beside it), on the texture coordinates scene_package unwrapped for it; a laid ground's recipe is baked once
on a flat GROUND_TILE square and blended seamless (seamless), the package box-projecting it over the ground.

    blender -b --python bake_looks.py -- <jobs.json>        (scene_package.blender_baked, through the card queue)
"""
import json
import pathlib
import sys
import time

import bpy
import numpy as np

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tools/props/library/inside"))
import runtime  # noqa: E402

runtime.ready()
import recipes  # noqa: E402
import scene_setup  # noqa: E402

SAMPLES = 16  # the props' bake samples (make_chunky.BAKE_SAMPLES): the wear's bevel and the dirt's occlusion
MARGIN = 4  # pixels a bake bleeds past each chart (scene_package.PADDING)
CHANNELS = (("base_color", True), ("roughness", False), ("metallic", False))


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


def bake(item, channels, size):
    """The recipe's channels baked onto the object's texture coordinates: {channel: pixels}."""
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
        bpy.data.images.remove(target)
    return found


def written(found, size, tiled, folder, pictures):
    """A bake's pictures as glTF reads them: base colour, metal-roughness (roughness in green, metal in blue) and
    the normal map, a tile's made seamless first."""
    if tiled:
        found = {channel: seamless(values) for channel, values in found.items()}
        found["normal"] = unit_normals(found["normal"])
    both = np.ones_like(found["roughness"])
    both[..., 1], both[..., 2] = found["roughness"][..., 0], found["metallic"][..., 0]
    saved(found["base_color"], size, True, folder / pictures["base_color"])
    saved(both, size, False, folder / pictures["metal_roughness"])
    saved(found["normal"], size, False, folder / pictures["normal"])


def baked_file(out, gltf, jobs):
    """Every job of one object's .gltf baked: the object imported whole (its parts beside the one baked)."""
    scene_setup.empty_scene(64, SAMPLES)
    bpy.context.scene.render.bake.margin_type = "EXTEND"
    if not all(job["tile"] for job in jobs):  # a ground's tile is baked on its own square, never on the ground
        bpy.ops.import_scene.gltf(filepath=str(out / gltf))
    for job in jobs:
        began = time.time()
        spec = job["spec"]
        channels = recipes.channels(spec, spec["wear"], spec["dirt"], spec["seed"])
        item = tile_square(job["tile"]) if job["tile"] else bpy.data.objects[job["mesh"]]
        found = bake(item, channels, job["size"])
        written(found, job["size"], bool(job["tile"]), out / "objects", job["pictures"])
        print(f"BAKED {gltf} {job['mesh']} {spec.get('library')} {job['size'][0]}x{job['size'][1]} "
              f"{time.time() - began:.1f} s", flush=True)


def main():
    listing = json.loads(pathlib.Path(sys.argv[sys.argv.index("--") + 1]).read_text())
    out = pathlib.Path(listing["out"])
    by_file = {}
    for job in listing["jobs"]:
        by_file.setdefault(job["gltf"], []).append(job)
    for gltf, jobs in by_file.items():
        baked_file(out, gltf, jobs)
    print(f"BAKE DONE {len(listing['jobs'])} maps", flush=True)


main()
