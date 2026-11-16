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
- **A palette variant is drawn as its recipe.** A look laid from the place's palette (`surface ... palette/<variant>`,
  its spec in `score:recipe:spec`) is replaced by its ProcFunc recipe (tools/props/library/recipes.py, as the
  surfaces bake and the swatches draw it): its edge wear through to the bare layer, dirt in its cavities and its
  relief, at the place's wear and dirt, so shells, floors and repainted parts wear the same finishes the props were
  baked from. A preview look stays for every other reader. The views take AgX's medium high contrast look, as a
  camera's grade, rather than the films' flat base.

    blender -b --python blender_views.py -- <stage.usda> <views.json> <out folder>   (usd_views.py's arguments)
"""
import json
import pathlib
import sys

import bpy

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "tools/blender/inside"))
import usd_views  # noqa: E402

RECIPES_AT = pathlib.Path(__file__).resolve().parents[3] / "tools/props/library/inside"

GLASS_IOR = 1.5  # a thin glass look's reflection share at each angle (window glass)
SEE_THROUGH = ("Alpha", "Transmission Weight")  # the Principled inputs a look's opacity comes in on
GROUND = "Ground"  # the name usd_views.stage_ground takes as the stage's own ground
# AgX's look on the preview's views: a camera's contrast (AgX's base look is the films' flat grade, washing a pale
# interior out to one beige).
CONTRAST = "AgX - Medium High Contrast"


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


DICING_PIXELS = 3.0  # an adaptive subdivision's micro-face size on screen, pixels, in a DICING_WIDTH-wide picture
DICING_WIDTH = 1100  # a wider picture cuts its faces as coarse on the ground (its 8 GB held a low view at 1100, not 1500)
DISPLACEMENT_LEVELS = 5  # the deepest a displaced ground's faces are cut
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
        cut.adaptive_pixel_size = DICING_PIXELS * max(1.0, bpy.context.scene.render.resolution_x / DICING_WIDTH)
        cut.render_levels = DISPLACEMENT_LEVELS
        bpy.context.scene.cycles.offscreen_dicing_scale = OFFSCREEN_DICING
    print("blender_views: displaced", sorted(changed))
    return changed


def recipe_specs(stage_path):
    """{look name: its palette spec} of every look the stage marks with `score:recipe:spec`."""
    from pxr import Usd
    stage = Usd.Stage.Open(str(stage_path))
    found = {}
    for prim in stage.Traverse():
        marked = prim.GetAttribute("score:recipe:spec")
        if marked and marked.Get():
            found[prim.GetName()] = json.loads(marked.Get())
    return found


def upright(item):
    """The object's turn and scale moved into its own mesh, so its own coordinates are the scene's (z up, metres)
    from its origin, as a recipe reads them: a y-up USD's mesh keeps y up under the importer's turn, so a recipe's
    floor grid (face_plane: the world's normal against the object's coordinates) would read a floor's height across
    it and stripe it."""
    import mathutils
    location, rotation, scale = item.matrix_world.decompose()
    held = [(child, child.matrix_world.copy()) for child in item.children]
    if item.data.users > 1:
        item.data = item.data.copy()
    item.data.transform(mathutils.Matrix.LocRotScale(None, rotation, scale))
    item.matrix_world = mathutils.Matrix.Translation(location)
    for child, where in held:  # a child stays where it stood
        child.matrix_world = where


def recipe_looks(objects, specs):
    """Every look the stage marks as a palette variant replaced, in every slot it fills, by its recipe drawn
    (the module's rule), each object wearing one set upright first; the looks it changed."""
    if not specs:
        return []
    sys.path.insert(0, str(RECIPES_AT))
    import runtime
    runtime.ready()
    import recipes
    drawn, changed = {}, []
    for item in objects:
        if item.type != "MESH":
            continue
        if any(slot.material and slot.material.name.split(".")[0] in specs for slot in item.material_slots):
            upright(item)
        for slot in item.material_slots:
            name = slot.material.name.split(".")[0] if slot.material else None
            if name not in specs:
                continue
            if name not in drawn:
                spec = specs[name]
                material = recipes.shaded(recipes.channels(spec, spec["wear"], spec["dirt"], spec["seed"])).item()
                material.displacement_method = "BUMP"
                material.name = f"{name}-recipe"
                drawn[name] = material
                changed.append(name)
            slot.material = drawn[name]
    print("blender_views: recipes", sorted(changed))
    return changed


def with_laid_ground(importer):
    def imported(stage):
        return joined_ground(importer(stage))
    return imported


def with_thin_glass(haze):
    def drawn(objects):
        thin_glass(objects)
        every = list(bpy.data.objects)  # the laid ground too, which usd_views keeps out of `objects`
        tiled_maps(every)
        recipe_looks(every, recipe_specs(sys.argv[sys.argv.index("--") + 1]))
        bpy.context.scene.view_settings.look = CONTRAST
        ground = bpy.data.objects.get(GROUND)
        if ground is not None and ground.type == "MESH":
            displaced(ground)
        return haze(objects)
    return drawn


usd_views.import_stage = with_laid_ground(usd_views.import_stage)
usd_views.haze_volumes = with_thin_glass(usd_views.haze_volumes)  # the looks' pass, never in a plain view
usd_views.main()
