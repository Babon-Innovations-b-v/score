"""Runs inside Blender: the placing agent's preview (render.py), tools/blender/inside/usd_views.py with two changes a
laid place needs, made here so the films' and the physics' renders (which key usd_views.py) stay as they are:

- **A laid ground is the ground.** Every mesh of an object the agent laid with `put --ground` (score:ground on it or
  a parent) is joined into one `Ground`, which usd_views takes as the stage's own ground: no grey plane of its own
  under it (the camp pilot's plane fought the laid regolith), and the ground left out of the objects' mask.
- **See-through looks are thin glass.** A look with opacity under 1 (which Blender 5's reader brings in as the
  Principled BSDF's transmission, 1 - opacity, at IOR 1.5: solid refracting glass, whose skin bends what is behind
  it and darkens the shadow it casts like a block of glass; or as its alpha) is drawn as a thin glass skin: light passes it tinted by its colour as much as it is opaque, and it gives back a Fresnel share of what
  is around it at its roughness, so a dome's glass shows what stands inside and throws only a faint shadow, never a
  dark shell.
- **An image surface tiles at its own size.** A look whose maps come from an image surface entry (its surface.json
  beside them names `tile_metres`, the ground a map covers, as the CC0 PBR sets take in) reads its maps by the
  object's own position (metres in its file, the frame its normals are in, so the box projection picks the right
  face; an object laid at a scale tiles at that scale) over that size, box-projected, so a wall, floor or dome shows
  the finish at its real size whatever its own texture coordinates are (kit pieces' map into a palette).
- **A laid ground's image surface is displaced.** When its surface.json names `displacement_metres` and lists a
  `displacement` map, the ground's look reads that map over the same tile and moves the skin by it (Cycles' adaptive
  subdivision, finer where the eye is close), so the scanned ground's pebbles and ripples stand up in a low view
  instead of being painted flat.

    blender -b --python blender_views.py -- <stage.usda> <views.json> <out folder>   (usd_views.py's arguments)
"""
import json
import pathlib
import sys

import bpy

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "tools/blender/inside"))
import usd_views  # noqa: E402

GLASS_IOR = 1.5  # a thin glass look's reflection share at each angle (window glass)
SEE_THROUGH = ("Alpha", "Transmission Weight")  # the Principled inputs a look's opacity comes in on
GROUND = "Ground"  # the name usd_views.stage_ground takes as the stage's own ground


def laid_grounds(objects):
    """The meshes of every object laid as the place's ground (score:ground true on it or a parent)."""
    found = []
    for item in objects:
        holder = item
        while item.type == "MESH" and holder is not None:
            if usd_views.score_value(holder, "ground"):
                found.append(item)
                break
            holder = holder.parent
    return found


def joined_ground(objects):
    """The laid ground's meshes joined into one object named GROUND (kept where they stand); the objects without the
    ones joined away."""
    grounds = laid_grounds(objects)
    if not grounds:
        return objects
    first = grounds[0]
    if len(grounds) > 1:
        with bpy.context.temp_override(active_object=first, selected_editable_objects=grounds,
                                       selected_objects=grounds):
            bpy.ops.object.join()
    first.name = GROUND
    gone = set(grounds[1:])
    return [item for item in objects if item not in gone]


def thin_glass(objects):
    """Every see-through look drawn as thin glass (the module's rule); the looks it changed."""
    changed = []
    for material in {slot.material for item in objects if item.type == "MESH" for slot in item.material_slots
                     if slot.material and slot.material.use_nodes}:
        tree = material.node_tree
        shader = next((node for node in tree.nodes if node.type == "BSDF_PRINCIPLED"), None)
        if shader is None or any(shader.inputs[name].is_linked for name in SEE_THROUGH):
            continue
        opacity = shader.inputs["Alpha"].default_value * (1.0 - shader.inputs["Transmission Weight"].default_value)
        if opacity >= 1.0:
            continue
        colour = shader.inputs["Base Color"].default_value
        output = next(node for node in tree.nodes if node.type == "OUTPUT_MATERIAL")
        passing = tree.nodes.new("ShaderNodeBsdfTransparent")
        passing.inputs["Color"].default_value = [1.0 - opacity * (1.0 - value) for value in colour[:3]] + [1.0]
        mirror = tree.nodes.new("ShaderNodeBsdfGlossy")
        mirror.inputs["Roughness"].default_value = shader.inputs["Roughness"].default_value
        share = tree.nodes.new("ShaderNodeFresnel")
        share.inputs["IOR"].default_value = GLASS_IOR
        mix = tree.nodes.new("ShaderNodeMixShader")
        tree.links.new(share.outputs["Fac"], mix.inputs["Fac"])
        tree.links.new(passing.outputs["BSDF"], mix.inputs[1])
        tree.links.new(mirror.outputs["BSDF"], mix.inputs[2])
        tree.links.new(mix.outputs["Shader"], output.inputs["Surface"])
        changed.append(material.name)
    print("blender_views: thin glass", sorted(changed))
    return changed


BOX_BLEND = 0.3  # how softly a box-projected map blends across a corner


def tile_metres(node):
    """The ground one copy of an image texture node's map covers, from the image surface's surface.json beside it;
    None for any other map (a model's bake keeps its own texture coordinates)."""
    image = getattr(node, "image", None)
    if image is None or not image.filepath:
        return None
    record = pathlib.Path(bpy.path.abspath(image.filepath)).parent / "surface.json"
    if not record.is_file():
        return None
    return json.loads(record.read_text()).get("tile_metres")


def tiled_maps(objects):
    """Every image surface's maps read by the object's own position over their tile, box-projected (the module's
    rule); the looks it changed."""
    changed = []
    for material in {slot.material for item in objects if item.type == "MESH" for slot in item.material_slots
                     if slot.material and slot.material.use_nodes}:
        tree = material.node_tree
        maps = [(node, tile_metres(node)) for node in tree.nodes if node.type == "TEX_IMAGE"]
        maps = [(node, tile) for node, tile in maps if tile]
        if not maps:
            continue
        where = tree.nodes.new("ShaderNodeTexCoord")
        for node, tile in maps:
            scaled = tree.nodes.new("ShaderNodeVectorMath")
            scaled.operation = "SCALE"
            scaled.inputs["Scale"].default_value = 1.0 / float(tile)
            tree.links.new(where.outputs["Object"], scaled.inputs[0])
            for link in list(node.inputs["Vector"].links):
                tree.links.remove(link)
            tree.links.new(scaled.outputs["Vector"], node.inputs["Vector"])
            node.projection = "BOX"
            node.projection_blend = BOX_BLEND
        changed.append(material.name)
    print("blender_views: tiled maps", sorted(changed))
    return changed


DICING_PIXELS = 2.0  # an adaptive subdivision's micro-face size on screen, pixels
DISPLACEMENT_LEVELS = 6  # the deepest a displaced ground's faces are cut
OFFSCREEN_DICING = 25.0  # how much coarser faces out of the picture are cut (the 2.6 km ground is mostly out of it)


def surface_record(node):
    """The image surface's surface.json beside an image texture node's map, or None."""
    image = getattr(node, "image", None)
    if image is None or not image.filepath:
        return None, None
    folder = pathlib.Path(bpy.path.abspath(image.filepath)).parent
    record = folder / "surface.json"
    return (json.loads(record.read_text()), folder) if record.is_file() else (None, None)


def displaced(ground):
    """The laid ground's image surfaces displaced by their own height maps (the module's rule); the looks changed."""
    changed = []
    for material in {slot.material for slot in ground.material_slots if slot.material and slot.material.use_nodes}:
        tree = material.node_tree
        found = next(((node, *surface_record(node)) for node in tree.nodes if node.type == "TEX_IMAGE"
                      and surface_record(node)[0] and surface_record(node)[0].get("displacement_metres")), None)
        if found is None:
            continue
        colour_node, record, folder = found
        heights = next((name for name in record.get("maps", []) if name.startswith("displacement")), None)
        if heights is None or not (folder / heights).is_file():
            continue
        height_map = tree.nodes.new("ShaderNodeTexImage")
        height_map.image = bpy.data.images.load(str(folder / heights), check_existing=True)
        height_map.image.colorspace_settings.name = "Non-Color"
        height_map.projection, height_map.projection_blend = "BOX", BOX_BLEND
        tree.links.new(colour_node.inputs["Vector"].links[0].from_socket, height_map.inputs["Vector"])
        move = tree.nodes.new("ShaderNodeDisplacement")
        move.inputs["Midlevel"].default_value = 0.5
        move.inputs["Scale"].default_value = float(record["displacement_metres"])
        tree.links.new(height_map.outputs["Color"], move.inputs["Height"])
        output = next(node for node in tree.nodes if node.type == "OUTPUT_MATERIAL")
        tree.links.new(move.outputs["Displacement"], output.inputs["Displacement"])
        material.displacement_method = "BOTH"
        changed.append(material.name)
    if changed:
        cut = ground.modifiers.new("displaced", "SUBSURF")
        cut.subdivision_type = "SIMPLE"
        cut.use_adaptive_subdivision = True
        cut.adaptive_space = "PIXEL"
        cut.adaptive_pixel_size = DICING_PIXELS
        cut.render_levels = DISPLACEMENT_LEVELS
        bpy.context.scene.cycles.offscreen_dicing_scale = OFFSCREEN_DICING
    print("blender_views: displaced", sorted(changed))
    return changed


def with_laid_ground(importer):
    def imported(stage):
        return joined_ground(importer(stage))
    return imported


def with_thin_glass(haze):
    def drawn(objects):
        thin_glass(objects)
        tiled_maps(list(bpy.data.objects))  # the laid ground too, which usd_views keeps out of `objects`
        ground = bpy.data.objects.get(GROUND)
        if ground is not None and ground.type == "MESH":
            displaced(ground)
        return haze(objects)
    return drawn


usd_views.import_stage = with_laid_ground(usd_views.import_stage)
usd_views.haze_volumes = with_thin_glass(usd_views.haze_volumes)  # the looks' pass, never in a plain view
usd_views.main()
