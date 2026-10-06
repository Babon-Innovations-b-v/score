"""Runs inside Blender: bake one piece's library materials into the maps the game draws (base colour, roughness and
metal, normal) at the texel density its place asks, and write it as a .glb.

    import bake; report = bake.baked(piece, specs, wear, dirt, seed, density, "out.glb")

Each material slot of the piece is named for a library material; `specs` maps that name to its resolved entry
(library.py). The recipe (recipes.py) is built per slot and each channel given off as light is baked, so what the
game gets is the recipe's exact colour, roughness and metal, not a lit picture. The normal map is baked from the
shaded recipe, its relief and chipped edges included. Roughness and metal are packed as glTF wants them (green and
blue of one picture), which HubKit hands to the look's shader (Textured) with the base colour and the normal map.
"""
import math
import time

import bpy
import numpy as np

import recipes

SMALLEST = 128
LARGEST = 2048
# How much of the square a packed UV layout fills, on average, to size the picture for a texel density.
UV_FILL = 0.55


def picture_side(item, density):
    """The square picture side (a power of two) that gives `density` pixels a metre over the piece's surface."""
    area = sum(face.area for face in item.data.polygons)
    wanted = math.sqrt(area / UV_FILL) * density
    return int(min(LARGEST, max(SMALLEST, 2 ** round(math.log2(max(wanted, 1.0))))))


def unwrapped(item, side):
    """The piece's faces laid out flat in one UV square, islands a few pixels apart."""
    bpy.ops.object.select_all(action="DESELECT")
    item.select_set(True)
    bpy.context.view_layer.objects.active = item
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=4.0 / side, area_weight=1.0,
                             scale_to_bounds=False)
    bpy.ops.object.mode_set(mode="OBJECT")


def new_picture(name, side, colour_data):
    picture = bpy.data.images.new(name, side, side, alpha=False, float_buffer=False)
    picture.colorspace_settings.name = "sRGB" if colour_data else "Non-Color"
    return picture


def with_target(material, picture):
    """A material with `picture` as its active image node, the bake's target."""
    node = material.node_tree.nodes.new("ShaderNodeTexImage")
    node.image = picture
    material.node_tree.nodes.active = node
    return material


def bake_channel(item, slot_materials, picture, kind):
    """Put each slot's material for this channel on the piece and bake `kind` (EMIT or NORMAL) into `picture`."""
    for index, material in enumerate(slot_materials):
        item.data.materials[index] = with_target(material, picture)
    bpy.ops.object.bake(type=kind, margin=8, use_clear=True, normal_space="TANGENT")


def channel_materials(found_by_slot, channel):
    """Per slot, its recipe's channel given off as light."""
    return [recipes.emitted(getattr(found, channel)).item() for found in found_by_slot]


def shaded_materials(found_by_slot):
    found = []
    for channels in found_by_slot:
        material = recipes.shaded(channels).item()
        material.displacement_method = "BUMP"
        found.append(material)
    return found


def packed(roughness, metal, side, name):
    """glTF's metal-roughness picture: roughness in green, metal in blue, red left white."""
    rough = np.array(roughness.pixels[:], dtype=np.float32).reshape(side, side, 4)
    shine = np.array(metal.pixels[:], dtype=np.float32).reshape(side, side, 4)
    both = np.ones((side, side, 4), dtype=np.float32)
    both[..., 1] = rough[..., 0]
    both[..., 2] = shine[..., 0]
    picture = new_picture(name, side, False)
    picture.pixels.foreach_set(both.ravel())
    return picture


def game_material(name, base, metal_roughness, normal):
    """The material the .glb carries: base colour, metal-roughness and normal pictures on one principled surface,
    wired the way the glTF exporter reads them."""
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    nodes, links = material.node_tree.nodes, material.node_tree.links
    surface = next(node for node in nodes if node.type == "BSDF_PRINCIPLED")
    colour = nodes.new("ShaderNodeTexImage")
    colour.image = base
    links.new(colour.outputs["Color"], surface.inputs["Base Color"])
    packed_node = nodes.new("ShaderNodeTexImage")
    packed_node.image = metal_roughness
    split = nodes.new("ShaderNodeSeparateColor")
    links.new(packed_node.outputs["Color"], split.inputs["Color"])
    links.new(split.outputs["Green"], surface.inputs["Roughness"])
    links.new(split.outputs["Blue"], surface.inputs["Metallic"])
    bumps = nodes.new("ShaderNodeTexImage")
    bumps.image = normal
    mapped = nodes.new("ShaderNodeNormalMap")
    links.new(bumps.outputs["Color"], mapped.inputs["Color"])
    links.new(mapped.outputs["Normal"], surface.inputs["Normal"])
    return material


def bake_across(high, low, slot_materials, picture, kind, reach):
    """Bake `kind` from the full-detail model `high` (its slots given these materials) onto `low`'s UV picture."""
    for index, material in enumerate(slot_materials):
        high.data.materials[index] = material
    target = bpy.data.materials.get("bake_target") or bpy.data.materials.new("bake_target")
    target.use_nodes = True
    with_target(target, picture)
    low.data.materials.clear()
    low.data.materials.append(target)
    bpy.ops.object.select_all(action="DESELECT")
    high.select_set(True)
    low.select_set(True)
    bpy.context.view_layer.objects.active = low
    bpy.ops.object.bake(type=kind, margin=8, use_clear=True, normal_space="TANGENT", use_selected_to_active=True,
                        cage_extrusion=reach, max_ray_distance=reach * 2)


def baked_from(high, low, specs, wear, dirt, seed, density, reach, path):
    """A generated piece: its library materials worked out on the full-detail model `high` (so wear follows its
    real edges, not the facets of a cut-down copy) and baked onto `low`, which is exported. The report as `baked`."""
    began = time.time()
    side = picture_side(low, density)
    unwrapped(low, side)
    names = [material.name.split(".")[0] for material in high.data.materials]
    found_by_slot = [recipes.channels(specs[name], wear, dirt, seed) for name in names]
    pictures = {}
    for channel, colour_data in (("base_color", True), ("roughness", False), ("metallic", False)):
        pictures[channel] = new_picture(f"{low.name}_{channel}", side, colour_data)
        bake_across(high, low, channel_materials(found_by_slot, channel), pictures[channel], "EMIT", reach)
    pictures["normal"] = new_picture(f"{low.name}_normal", side, False)
    bake_across(high, low, shaded_materials(found_by_slot), pictures["normal"], "NORMAL", reach)
    metal_roughness = packed(pictures["roughness"], pictures["metallic"], side, f"{low.name}_metal_roughness")
    low.data.materials.clear()
    low.data.materials.append(game_material(low.name, pictures["base_color"], metal_roughness, pictures["normal"]))
    exported(low, path)
    return {"side": side, "slots": names, "triangles": sum(len(face.vertices) - 2 for face in low.data.polygons),
            "high_triangles": sum(len(face.vertices) - 2 for face in high.data.polygons),
            "seconds": round(time.time() - began, 1)}


def exported(item, path):
    bpy.ops.object.select_all(action="DESELECT")
    item.select_set(True)
    bpy.context.view_layer.objects.active = item
    bpy.ops.export_scene.gltf(filepath=str(path), export_format="GLB", use_selection=True, export_apply=True,
                              export_yup=True, export_image_format="AUTO", export_materials="EXPORT")


def baked(item, specs, wear, dirt, seed, density, path):
    """Bake a piece's library materials and export it; a report of its size, picture side, slots and seconds."""
    began = time.time()
    side = picture_side(item, density)
    unwrapped(item, side)
    names = [material.name.split(".")[0] for material in item.data.materials]
    found_by_slot = [recipes.channels(specs[name], wear, dirt, seed) for name in names]
    pictures = {}
    for channel, colour_data in (("base_color", True), ("roughness", False), ("metallic", False)):
        pictures[channel] = new_picture(f"{item.name}_{channel}", side, colour_data)
        bake_channel(item, channel_materials(found_by_slot, channel), pictures[channel], "EMIT")
    pictures["normal"] = new_picture(f"{item.name}_normal", side, False)
    bake_channel(item, shaded_materials(found_by_slot), pictures["normal"], "NORMAL")
    metal_roughness = packed(pictures["roughness"], pictures["metallic"], side, f"{item.name}_metal_roughness")
    item.data.materials.clear()
    item.data.materials.append(game_material(item.name, pictures["base_color"], metal_roughness, pictures["normal"]))
    exported(item, path)
    return {"side": side, "slots": names, "triangles": sum(len(face.vertices) - 2 for face in item.data.polygons),
            "seconds": round(time.time() - began, 1)}
