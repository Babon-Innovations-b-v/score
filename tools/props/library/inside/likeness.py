"""Runs inside Blender: the look-alike check's pictures (#155, tools/props/library/likeness/check.py). Each pair is a
surface's map material and its fitted recipe, rendered on the swatch's test piece (scene_setup.test_piece) under the
swatch's light, from each of its cameras, at wear and dirt 0 (a surface's maps are as made).

    blender -b --python tools/props/library/inside/likeness.py -- <job.json>

The job: {"out", "size", "samples", "seed", "pairs": [{"name", "maps": {role: path}, "tile_metres",
"normal_convention": "opengl" | "directx", "albedo_colour": linear RGB | null, "emission_colour": linear RGB | null,
"roughness", "metal", "recipe": spec, "map": bool}]}; a pair with "map" false has its map pictures from an earlier round and renders only its recipe. The
map material is the maps as a principled surface: the albedo as sRGB colour (with no albedo map, the surface's constant
linear `albedo_colour`), roughness and metal from an ORM map's
green and blue (or their own maps, or a packed albedo's alpha, `roughness_alpha`; with neither, the pair's `roughness` and `metal`, the fit's reading of the surface's
constants or USD's defaults, never Blender's own), its glow the emission map (sRGB, given off at strength 1, as USD draws it) or the
constant linear `emission_colour` (its size the strength: (5, 5, 5) is white at 5), the normal map in tangent space (a DirectX map's green turned over), all on texture coordinates cube-projected at the
maps' tile size, so a repeat covers `tile_metres` as the recipe's metres do. Writes <out>/<name>/map-<view>.png and
recipe-<view>.png, and prints "LIKENESS <name>" per pair.

A pair with "through" true (its maps or its recipe let light through) is also drawn as a pane held square before a
checker backdrop that gives off its own light (so no light or shine moves its squares), each side's pane in its own
see-through: the map side's "see_through" ({"alpha", "threshold", "transmission"}, fit.see_through_of: its alpha the
opacity map's where its maps hold one, cut at its threshold, else the constant; its glass's transmission as the
surface's own, tinted by its colour), the recipe's its spec's `opacity` as the alpha the place's look writes. Writes
<out>/<name>/map-through.png and recipe-through.png, and <out>/backdrop.png, the bare backdrop, once a job.
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
OPAQUE = {"alpha": 1.0, "threshold": 0.0, "transmission": 0.0}  # a map side that says nothing of letting light through
# The see-through view, far from the swatch so no other camera sees it: a PANE metres square at THROUGH_AT, the
# backdrop BACKDROP_GAP behind it (near, so a frosted pane blurs its squares as frosted glass near a wall does),
# checker squares SQUARE metres across, seen square on from THROUGH_DISTANCE through a long lens that the pane fills.
THROUGH_AT = (6.0, 0.0, 0.5)
PANE, BACKDROP, BACKDROP_GAP, SQUARE = 0.4, 1.0, 0.05, 0.03
THROUGH_DISTANCE, THROUGH_LENS = 1.0, 150


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


def math_node(tree, operation, first, second=None):
    """A math node `operation` of its inputs (a socket or a number each)."""
    node = tree.nodes.new("ShaderNodeMath")
    node.operation = operation
    for slot, value in ((0, first), (1, second)):
        if value is None:
            continue
        if isinstance(value, (int, float)):
            node.inputs[slot].default_value = float(value)
        else:
            tree.links.new(value, node.inputs[slot])
    return node.outputs["Value"]


def normal_colour(tree, maps, convention):
    """The normal map's colour as Blender's (OpenGL's) tangent space reads it: a DirectX map's green turned over, its
    blue made again from its red and green (z = sqrt(1 - x^2 - y^2), as fit.rebuilt reads it: a map whose blue is not
    its z rendered black, pointing into the surface)."""
    colour = image_node(tree, maps["normal"], True).outputs["Color"]
    split, joined = tree.nodes.new("ShaderNodeSeparateColor"), tree.nodes.new("ShaderNodeCombineColor")
    tree.links.new(colour, split.inputs["Color"])
    green = split.outputs["Green"]
    if convention == "directx":
        green = math_node(tree, "SUBTRACT", 1.0, green)
    squares = [math_node(tree, "POWER", math_node(tree, "SUBTRACT", math_node(tree, "MULTIPLY", channel, 2.0), 1.0),
                         2.0) for channel in (split.outputs["Red"], green)]
    left = math_node(tree, "MAXIMUM", math_node(tree, "SUBTRACT", math_node(tree, "SUBTRACT", 1.0, squares[0]),
                                                squares[1]), 0.0)
    blue = math_node(tree, "MULTIPLY_ADD", math_node(tree, "SQRT", left), 0.5)
    blue.node.inputs[2].default_value = 0.5
    for channel, socket in (("Red", split.outputs["Red"]), ("Green", green), ("Blue", blue)):
        tree.links.new(socket, joined.inputs[channel])
    return joined.outputs["Color"]


def glow(tree, surface, maps, emission_colour):
    """The surface's light given off: the emission map's colour at strength 1, else the constant `emission_colour`
    (linear) as its hue at the strength of its strongest channel, else none."""
    if "emission" in maps:
        tree.links.new(image_node(tree, maps["emission"], False).outputs["Color"], surface.inputs["Emission Color"])
        surface.inputs["Emission Strength"].default_value = 1.0
        return
    strongest = max(emission_colour or [0.0])
    if strongest <= 0:
        surface.inputs["Emission Strength"].default_value = 0.0
        return
    surface.inputs["Emission Color"].default_value = (*[value / strongest for value in emission_colour], 1.0)
    surface.inputs["Emission Strength"].default_value = strongest


def map_material(name, maps, convention="opengl", albedo_colour=None, emission_colour=None, roughness=0.5, metal=0.0):
    """The maps as a principled surface material, its base colour the albedo map's, else the constant
    `albedo_colour` (linear), its roughness and metal their maps', else the constant `roughness` and `metal`, its glow
    the emission map's, else the constant `emission_colour` (glow)."""
    material = bpy.data.materials.new(f"map-{name}")
    material.use_nodes = True
    tree = material.node_tree
    surface = next(node for node in tree.nodes if node.type == "BSDF_PRINCIPLED")
    if "albedo" in maps:
        tree.links.new(image_node(tree, maps["albedo"], False).outputs["Color"], surface.inputs["Base Color"])
    else:
        surface.inputs["Base Color"].default_value = (*albedo_colour, 1.0)
    if "orm" in maps:
        split = tree.nodes.new("ShaderNodeSeparateColor")
        tree.links.new(image_node(tree, maps["orm"], True).outputs["Color"], split.inputs["Color"])
        tree.links.new(split.outputs["Green"], surface.inputs["Roughness"])
        tree.links.new(split.outputs["Blue"], surface.inputs["Metallic"])
    else:
        for role, socket, constant in (("roughness", "Roughness", roughness), ("metal", "Metallic", metal)):
            if role in maps:
                tree.links.new(image_node(tree, maps[role], True).outputs["Color"], surface.inputs[socket])
            elif role == "roughness" and "roughness_alpha" in maps:
                packed = image_node(tree, maps["roughness_alpha"], False)  # the albedo's own picture: its alpha
                tree.links.new(packed.outputs["Alpha"], surface.inputs[socket])
            else:
                surface.inputs[socket].default_value = constant
    if "normal" in maps:
        bent = tree.nodes.new("ShaderNodeNormalMap")
        bent.uv_map = UV_MAP
        tree.links.new(normal_colour(tree, maps, convention), bent.inputs["Color"])
        tree.links.new(bent.outputs["Normal"], surface.inputs["Normal"])
    glow(tree, surface, maps, emission_colour)
    return material


def seen_through(material, maps, see_through):
    """The map material made to let light through as its surface says (fit.see_through_of): its alpha the opacity
    map's where its maps hold one (cut at its threshold), else the constant, its glass's share passed by the
    principled surface's transmission; the material."""
    tree = material.node_tree
    surface = next(node for node in tree.nodes if node.type == "BSDF_PRINCIPLED")
    if "opacity" in maps:
        alpha = image_node(tree, maps["opacity"], True).outputs["Color"]
        if see_through["threshold"]:
            alpha = math_node(tree, "GREATER_THAN", alpha, see_through["threshold"])
        tree.links.new(alpha, surface.inputs["Alpha"])
    else:
        surface.inputs["Alpha"].default_value = see_through["alpha"]
    surface.inputs["Transmission Weight"].default_value = see_through["transmission"]
    return material


def recipe_seen_through(spec, seed):
    """The recipe's material at its spec's opacity, as the alpha of the look the place writes for it."""
    material = recipe_material(spec, seed)
    surface = next(node for node in material.node_tree.nodes if node.type == "BSDF_PRINCIPLED")
    surface.inputs["Alpha"].default_value = float(spec.get("opacity", 1.0))
    return material


def through_stand():
    """The see-through view's pane, its backdrop (an emission checker) and its camera: (pane, backdrop, camera)."""
    middle = THROUGH_AT
    bpy.ops.mesh.primitive_plane_add(size=PANE, location=middle, rotation=(1.5707963, 0.0, 0.0))
    pane = bpy.context.object
    bpy.ops.mesh.primitive_plane_add(size=BACKDROP, location=(middle[0], middle[1] + BACKDROP_GAP, middle[2]),
                                     rotation=(1.5707963, 0.0, 0.0))
    backdrop = bpy.context.object
    lit = bpy.data.materials.new("backdrop")
    lit.use_nodes = True
    tree = lit.node_tree
    tree.nodes.clear()
    squares = tree.nodes.new("ShaderNodeTexChecker")
    squares.inputs["Scale"].default_value = BACKDROP / SQUARE / 2.0  # a checker's unit holds two squares a side
    squares.inputs["Color1"].default_value = (1.0, 1.0, 1.0, 1.0)
    squares.inputs["Color2"].default_value = (0.0, 0.0, 0.0, 1.0)
    coordinates = tree.nodes.new("ShaderNodeTexCoord")
    tree.links.new(coordinates.outputs["UV"], squares.inputs["Vector"])
    given = tree.nodes.new("ShaderNodeEmission")
    tree.links.new(squares.outputs["Color"], given.inputs["Color"])
    output = tree.nodes.new("ShaderNodeOutputMaterial")
    tree.links.new(given.outputs["Emission"], output.inputs["Surface"])
    backdrop.data.materials.append(lit)
    camera = scene_setup.camera_aimed((middle[0], middle[1] - THROUGH_DISTANCE, middle[2]), middle, THROUGH_LENS)
    return pane, backdrop, camera


def shown_alone(shown, hidden):
    """Each object of `shown` drawn and each of `hidden` left out of the render."""
    for item in shown:
        item.hide_render = False
    for item in hidden:
        item.hide_render = True


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
        # One picture can feed two nodes (a packed albedo's colour and its alpha): each removed once.
        pictures = {node.image.name: node.image for node in material.node_tree.nodes
                    if node.type == "TEX_IMAGE" and node.image}
        bpy.data.materials.remove(material)
        for loaded in pictures.values():
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
    pane, backdrop, through = through_stand()
    stand = (pane, backdrop)
    if any(pair.get("through") for pair in job["pairs"]):
        shown_alone([backdrop], [piece, pane])
        bpy.context.scene.camera = through
        bpy.context.scene.render.filepath = str(out / "backdrop.png")
        bpy.ops.render.render(write_still=True)
    for pair in job["pairs"]:
        folder = out / pair["name"]
        folder.mkdir(parents=True, exist_ok=True)
        projected(piece, pair["tile_metres"])
        shown = {"recipe": recipe_material(pair["recipe"], job["seed"])}
        if pair["map"]:
            shown["map"] = map_material(pair["name"], pair["maps"], pair.get("normal_convention", "opengl"),
                                        pair.get("albedo_colour"), pair.get("emission_colour"), pair["roughness"],
                                        pair["metal"])
        shown_alone([piece], stand)
        for view, camera in cameras.items():
            bpy.context.scene.camera = camera
            for side, material in shown.items():
                rendered(piece, material, folder / f"{side}-{view}.png")
        freed(shown.values())
        if pair.get("through"):
            through_pictures(pair, pane, stand, through, folder, job["seed"])
        print("LIKENESS", pair["name"], flush=True)


def through_pictures(pair, pane, stand, camera, folder, seed):
    """A see-through pair's panes before the backdrop: <folder>/<side>-through.png (the map side's only on its first
    round)."""
    projected(pane, pair["tile_metres"])
    shown = {"recipe": recipe_seen_through(pair["recipe"], seed)}
    if pair["map"]:
        shown["map"] = seen_through(map_material(pair["name"], pair["maps"], pair.get("normal_convention", "opengl"),
                                                 pair.get("albedo_colour"), pair.get("emission_colour"),
                                                 pair["roughness"], pair["metal"]),
                                    pair["maps"], pair["see_through"] or OPAQUE)
    shown_alone(stand, [])
    bpy.context.scene.camera = camera
    for side, material in shown.items():
        rendered(pane, material, folder / f"{side}-through.png")
    freed(shown.values())


main()
