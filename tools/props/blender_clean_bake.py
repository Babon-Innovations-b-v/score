"""Bake a generated model's paint and surface onto its slimmed copy, in one clean pass (Blender).

    blender --background --python tools/props/blender_clean_bake.py -- \
        SOURCE.glb TARGET.glb OUT.glb SIZE ANGLE SAMPLES

SOURCE is the generator's dense model, TARGET the slimmed model with its own UVs, in the same
coordinates. Three things the lab's own bake does that made our models messy, and what this does
instead (measured on the crate, ice mine and rover, 2026-10-01):

- It bakes with the slimmed model shaded smooth over every corner, so rays near a fold fan across
  it and paint one part with the next (gold triangles on the crate's white panels). Here the target
  is shaded flat across folds sharper than ANGLE degrees first, so each ray leaves its panel
  straight out, and the model keeps those hard edges in the game.
- It samples the source picture nearest-texel with one ray a texel, which stair-steps. Here the
  source is read smoothly and SAMPLES jittered rays average each texel.
- It also bakes a detail normal map, whose fine noise the game's ink pass draws as black specks.
  Here there is none: base colour and metal-roughness only.
"""
import math
import sys

import bpy

source_path, target_path, out_path, size, angle, samples = sys.argv[sys.argv.index("--") + 1:][:6]
size, angle, samples = int(size), float(angle), int(samples)
# How far the bake looks either side of the slimmed surface for the dense one, as a share of the
# model's size: the lab's own value.
REACH = 0.02


def imported(path, **options):
    """The meshes a glTF file brings in."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path, **options)
    return [thing for thing in bpy.data.objects if thing not in before and thing.type == "MESH"]


def image_feeding(material, sockets):
    """The picture behind one of a material's Principled inputs, through any colour-split node."""
    bsdf = next((node for node in material.node_tree.nodes if node.type == "BSDF_PRINCIPLED"), None)
    if bsdf is None:
        return None
    for socket in sockets:
        for link in bsdf.inputs[socket].links:
            node = link.from_node
            while node.type != "TEX_IMAGE" and node.inputs and node.inputs[0].links:
                node = node.inputs[0].links[0].from_node
            if node.type == "TEX_IMAGE":
                return node.image
    return None


def shine_as_light(material, image):
    """Turn `material` into a plain glow of `image`, read smoothly, which is what a bake copies."""
    nodes, links = material.node_tree.nodes, material.node_tree.links
    for node in list(nodes):
        if node.type != "OUTPUT_MATERIAL":
            nodes.remove(node)
    output = next(node for node in nodes if node.type == "OUTPUT_MATERIAL")
    texture = nodes.new("ShaderNodeTexImage")
    texture.image = image
    texture.interpolation = "Linear"
    glow = nodes.new("ShaderNodeEmission")
    links.new(texture.outputs["Color"], glow.inputs["Color"])
    links.new(glow.outputs["Emission"], output.inputs["Surface"])


def shade_by_folds(target):
    """Smooth within panels, flat across folds sharper than ANGLE."""
    bpy.ops.object.select_all(action="DESELECT")
    target.select_set(True)
    bpy.context.view_layer.objects.active = target
    if target.data.has_custom_normals:
        bpy.ops.mesh.customdata_custom_splitnormals_clear()
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(angle), keep_sharp_edges=False)


def baked(sources, target, name, colour_space):
    """A new picture on the target's UVs holding what the sources glow with."""
    image = bpy.data.images.new(name, width=size, height=size, alpha=False)
    image.colorspace_settings.name = colour_space
    material = target.data.materials[0]
    node = material.node_tree.nodes.new("ShaderNodeTexImage")
    node.image = image
    for other in material.node_tree.nodes:
        other.select = False
    node.select = True
    material.node_tree.nodes.active = node
    bpy.ops.object.select_all(action="DESELECT")
    for thing in sources:
        thing.select_set(True)
    target.select_set(True)
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.bake(type="EMIT")
    material.node_tree.nodes.remove(node)
    image.pack()
    return image


def set_up_the_bake(target):
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = samples
    bake = scene.render.bake
    bake.use_selected_to_active = True
    bake.margin = 16
    bake.use_clear = True
    bake.cage_extrusion = max(target.dimensions) * REACH
    bake.max_ray_distance = bake.cage_extrusion * 2.0


def finished_material(colour, metal):
    """One Principled material wired to the baked base colour and metal-roughness."""
    material = bpy.data.materials.new("FINISHED")
    material.use_nodes = True
    nodes, links = material.node_tree.nodes, material.node_tree.links
    bsdf = next(node for node in nodes if node.type == "BSDF_PRINCIPLED")
    colour_node = nodes.new("ShaderNodeTexImage")
    colour_node.image = colour
    links.new(colour_node.outputs["Color"], bsdf.inputs["Base Color"])
    if metal is not None:
        metal_node = nodes.new("ShaderNodeTexImage")
        metal_node.image = metal
        split = nodes.new("ShaderNodeSeparateColor")
        links.new(metal_node.outputs["Color"], split.inputs["Color"])
        links.new(split.outputs["Green"], bsdf.inputs["Roughness"])
        links.new(split.outputs["Blue"], bsdf.inputs["Metallic"])
    return material


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sources = imported(source_path)
    target = imported(target_path, merge_vertices=True)[0]
    shade_by_folds(target)
    target.data.materials.clear()
    work = bpy.data.materials.new("BAKING")
    work.use_nodes = True
    target.data.materials.append(work)
    set_up_the_bake(target)

    slots = [slot for thing in sources for slot in thing.material_slots]
    colours = {slot.material.name: image_feeding(slot.material, ("Base Color",)) for slot in slots}
    metals = {slot.material.name: image_feeding(slot.material, ("Roughness", "Metallic")) for slot in slots}
    for slot in slots:
        shine_as_light(slot.material, colours[slot.material.name])
    colour = baked(sources, target, "colour", "sRGB")
    metal = None
    if any(metals.values()):
        for slot in slots:
            shine_as_light(slot.material, metals[slot.material.name])
        metal = baked(sources, target, "metal_roughness", "Non-Color")

    target.data.materials.clear()
    target.data.materials.append(finished_material(colour, metal))
    for thing in sources:
        bpy.data.objects.remove(thing, do_unlink=True)
    bpy.ops.object.select_all(action="DESELECT")
    target.select_set(True)
    bpy.ops.export_scene.gltf(filepath=out_path, export_format="GLB", use_selection=True)
    print("CLEAN_BAKE:: done", out_path, flush=True)


main()
