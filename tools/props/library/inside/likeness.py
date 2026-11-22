"""Runs inside Blender: the look-alike check's pictures (#155, tools/props/library/likeness/check.py). Each pair is a
surface's map material and its fitted recipe, rendered on the swatch's test piece (scene_setup.test_piece) under the
swatch's light, from each of its cameras, at wear and dirt 0 (a surface's maps are as made).

    blender -b --python tools/props/library/inside/likeness.py -- <job.json>

The job: {"out", "size", "samples", "seed", "pairs": [{"name", "maps": {role: path}, "tile_metres",
"normal_convention": "opengl" | "directx", "recipe": spec, "map": bool}]}; a pair with "map" false has its map pictures from an earlier round and renders only its recipe. The
map material is the maps as a principled surface: the albedo as sRGB colour, roughness and metal from an ORM map's
green and blue (or their own maps), the normal map in tangent space (a DirectX map's green turned over), all on texture coordinates cube-projected at the
maps' tile size, so a repeat covers `tile_metres` as the recipe's metres do. Writes <out>/<name>/map-<view>.png and
recipe-<view>.png, and prints "LIKENESS <name>" per pair.
"""
import json
import pathlib
import sys

import bpy

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import runtime  # noqa: E402

runtime.ready()
import recipes  # noqa: E402
import scene_setup  # noqa: E402

UV_MAP = "likeness"


def projected(piece, tile_metres):
    """The piece's texture coordinates cube-projected so one unit of them is `tile_metres` of the piece."""
    if UV_MAP not in piece.data.uv_layers:
        piece.data.uv_layers.new(name=UV_MAP)
    piece.data.uv_layers.active = piece.data.uv_layers[UV_MAP]
    bpy.context.view_layer.objects.active = piece
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.cube_project(cube_size=tile_metres, correct_aspect=False, clip_to_bounds=False,
                            scale_to_bounds=False)
    bpy.ops.object.mode_set(mode="OBJECT")


def image_node(tree, path, data):
    """An image texture of `path` on the projected coordinates, as colour (sRGB) or as data (non-colour)."""
    node = tree.nodes.new("ShaderNodeTexImage")
    node.image = bpy.data.images.load(path, check_existing=True)
    node.image.colorspace_settings.name = "Non-Color" if data else "sRGB"
    coordinates = tree.nodes.new("ShaderNodeUVMap")
    coordinates.uv_map = UV_MAP
    tree.links.new(coordinates.outputs["UV"], node.inputs["Vector"])
    return node


def normal_colour(tree, maps, convention):
    """The normal map's colour as Blender's (OpenGL's) tangent space reads it: a DirectX map's green turned over."""
    colour = image_node(tree, maps["normal"], True).outputs["Color"]
    if convention != "directx":
        return colour
    split, joined = tree.nodes.new("ShaderNodeSeparateColor"), tree.nodes.new("ShaderNodeCombineColor")
    turned = tree.nodes.new("ShaderNodeMath")
    turned.operation = "SUBTRACT"
    turned.inputs[0].default_value = 1.0
    tree.links.new(colour, split.inputs["Color"])
    tree.links.new(split.outputs["Green"], turned.inputs[1])
    for channel, socket in (("Red", split.outputs["Red"]), ("Green", turned.outputs["Value"]),
                            ("Blue", split.outputs["Blue"])):
        tree.links.new(socket, joined.inputs[channel])
    return joined.outputs["Color"]


def map_material(name, maps, convention="opengl"):
    """The maps as a principled surface material."""
    material = bpy.data.materials.new(f"map-{name}")
    material.use_nodes = True
    tree = material.node_tree
    surface = next(node for node in tree.nodes if node.type == "BSDF_PRINCIPLED")
    tree.links.new(image_node(tree, maps["albedo"], False).outputs["Color"], surface.inputs["Base Color"])
    if "orm" in maps:
        split = tree.nodes.new("ShaderNodeSeparateColor")
        tree.links.new(image_node(tree, maps["orm"], True).outputs["Color"], split.inputs["Color"])
        tree.links.new(split.outputs["Green"], surface.inputs["Roughness"])
        tree.links.new(split.outputs["Blue"], surface.inputs["Metallic"])
    else:
        for role, socket in (("roughness", "Roughness"), ("metal", "Metallic")):
            if role in maps:
                tree.links.new(image_node(tree, maps[role], True).outputs["Color"], surface.inputs[socket])
        if "metal" not in maps:
            surface.inputs["Metallic"].default_value = 0.0
    if "normal" in maps:
        bent = tree.nodes.new("ShaderNodeNormalMap")
        bent.uv_map = UV_MAP
        tree.links.new(normal_colour(tree, maps, convention), bent.inputs["Color"])
        tree.links.new(bent.outputs["Normal"], surface.inputs["Normal"])
    return material


def recipe_material(spec, seed):
    """The fitted recipe as the library draws it, new and clean."""
    material = recipes.shaded(recipes.channels(spec, 0.0, 0.0, seed)).item()
    material.displacement_method = "BUMP"
    return material


def rendered(piece, material, path):
    """One picture of the piece in `material` from the scene's camera."""
    piece.data.materials.clear()
    piece.data.materials.append(material)
    bpy.context.scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def freed(materials):
    """A pair's materials and the pictures they loaded removed, so a long batch does not hold every set's maps."""
    for material in materials:
        pictures = [node.image for node in material.node_tree.nodes if node.type == "TEX_IMAGE" and node.image]
        bpy.data.materials.remove(material)
        for loaded in pictures:
            if not loaded.users:
                bpy.data.images.remove(loaded)


def main():
    job = json.loads(pathlib.Path(sys.argv[sys.argv.index("--") + 1]).read_text())
    out = pathlib.Path(job["out"])
    scene_setup.empty_scene(job["size"], job["samples"])
    piece = scene_setup.test_piece()
    cameras = {"overview": scene_setup.camera_on(piece, (0.55, -0.75, 0.62), 2.6),
               "close": scene_setup.camera_aimed((0.12, -0.12, 0.33), (0.12, 0.08, 0.03), 50)}
    scene_setup.studio_light()
    for pair in job["pairs"]:
        folder = out / pair["name"]
        folder.mkdir(parents=True, exist_ok=True)
        projected(piece, pair["tile_metres"])
        shown = {"recipe": recipe_material(pair["recipe"], job["seed"])}
        if pair["map"]:
            shown["map"] = map_material(pair["name"], pair["maps"], pair.get("normal_convention", "opengl"))
        for view, camera in cameras.items():
            bpy.context.scene.camera = camera
            for side, material in shown.items():
                rendered(piece, material, folder / f"{side}-{view}.png")
        freed(shown.values())
        print("LIKENESS", pair["name"], flush=True)


main()
