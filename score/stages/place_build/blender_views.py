"""Runs inside Blender: the placing agent's preview (render.py), tools/blender/inside/usd_views.py with two changes a
laid place needs, made here so the films' and the physics' renders (which key usd_views.py) stay as they are:

- **A cut is the camera's.** The objects a view's `cut` names (place.json `cut`; the listing's own `cut` for a view
  that names none, as the films' frames) are left out of that view's camera rays alone, so a concept's cut-away is
  drawn at render while the building stays closed, and an outside view sees it closed.
- **A laid ground is the ground.** Every mesh of an object the agent laid with `put --ground` (score:ground on it or
  a parent) is joined into one `Ground`, which usd_views takes as the stage's own ground: no grey plane of its own
  under it (the camp pilot's plane fought the laid regolith), and the ground left out of the objects' mask.
- **See-through looks are thin glass** (a rough one frosted, FROST_FROM). A look with opacity under 1 (which Blender 5's reader brings in as the
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
  baked from; a see-through variant (glass, its opacity under 1) stays thin glass. A preview look stays for every
  other reader. The views take AgX's medium high contrast look, as a
  camera's grade, rather than the films' flat base.
- **A picture is drawn at most HELD_TEXELS a side**, the side the game holds it at (scene_package.HELD_TEXELS), so
  the preview shows what the game shows and a place of adopted 4096 sets fits its Blender's cap (#156, 2026-11-23:
  the capsule's NVIDIA SimReady parts held 8 GB of maps and the render's 8 GB Blender was killed for memory).

    blender -b --python blender_views.py -- <stage.usda> <views.json> <out folder>   (usd_views.py's arguments)
"""
import json
import pathlib
import sys

import bpy

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "tools/blender/inside"))
import usd_views  # noqa: E402

RECIPES_AT = pathlib.Path(__file__).resolve().parents[3] / "tools/props/library/inside"
# The method's recipe defaults (place_build.palette_spec's): a spec laid before its recipe carried a default (a glass
# laid before it carried its opacity) is drawn with it, as a look laid now would be.
METHOD = pathlib.Path(__file__).resolve().parents[3] / "data/library/materials.json"

GLASS_IOR = 1.5  # a thin glass look's reflection share at each angle (window glass)
# A rough see-through look is frosted: its passing light scatters (a translucent share) as far as its roughness
# goes from FROST_FROM to FROST_FULL, so a frosted dome reads milky and a clear one (0.05) passes straight as before.
FROST_FROM, FROST_FULL = 0.15, 0.5
SEE_THROUGH = ("Alpha", "Transmission Weight")  # the Principled inputs a look's opacity comes in on
GROUND = "Ground"  # the name usd_views.stage_ground takes as the stage's own ground
# AgX's look on the preview's views: a camera's contrast (AgX's base look is the films' flat grade, washing a pale
# interior out to one beige).
CONTRAST = "AgX - Medium High Contrast"
HELD_TEXELS = "2048"  # Cycles' texture limit: scene_package.HELD_TEXELS, the side the game holds a picture at


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


def frosted(tree, tint, roughness):
    """The light a thin glass look passes: straight through (transparent) tinted `tint`, scattered (translucent) in the
    share its roughness frosts it (FROST_FROM to FROST_FULL)."""
    straight = tree.nodes.new("ShaderNodeBsdfTransparent")
    straight.inputs["Color"].default_value = tint
    frost = min(1.0, max(0.0, (roughness - FROST_FROM) / (FROST_FULL - FROST_FROM)))
    if frost <= 0.0:
        return straight
    scattered = tree.nodes.new("ShaderNodeBsdfTranslucent")
    scattered.inputs["Color"].default_value = tint
    mix = tree.nodes.new("ShaderNodeMixShader")
    mix.inputs["Fac"].default_value = frost
    tree.links.new(straight.outputs["BSDF"], mix.inputs[1])
    tree.links.new(scattered.outputs["BSDF"], mix.inputs[2])
    return mix


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
        tint = [1.0 - opacity * (1.0 - value) for value in colour[:3]] + [1.0]
        passing = frosted(tree, tint, shader.inputs["Roughness"].default_value)
        mirror = tree.nodes.new("ShaderNodeBsdfGlossy")
        mirror.inputs["Roughness"].default_value = shader.inputs["Roughness"].default_value
        share = tree.nodes.new("ShaderNodeFresnel")
        share.inputs["IOR"].default_value = GLASS_IOR
        mix = tree.nodes.new("ShaderNodeMixShader")
        tree.links.new(share.outputs["Fac"], mix.inputs["Fac"])
        tree.links.new(passing.outputs[0], mix.inputs[1])
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
    """{look name: its palette spec} of every look the stage marks with `score:recipe:spec`, an opacity the spec lacks
    taken from its recipe's method default (METHOD), as a look laid now carries it."""
    from pxr import Usd
    method = json.loads(METHOD.read_text())["recipes"]
    stage = Usd.Stage.Open(str(stage_path))
    found = {}
    for prim in stage.Traverse():
        marked = prim.GetAttribute("score:recipe:spec")
        if marked and marked.Get():
            spec = json.loads(marked.Get())
            if "opacity" not in spec and "opacity" in method.get(spec.get("recipe"), {}):
                spec["opacity"] = method[spec["recipe"]]["opacity"]
            found[prim.GetName()] = spec
    return found


def see_through(objects, specs):
    """Every palette look whose spec is see-through (opacity under 1) given that opacity on its shader, so thin_glass
    draws it: a look laid before its recipe carried its opacity came in opaque (place_build.recipe_marked writes it on
    a look laid now); the looks it changed."""
    changed = []
    for material in {slot.material for item in objects if item.type == "MESH" for slot in item.material_slots
                     if slot.material and slot.material.use_nodes}:
        spec = specs.get(material.name.split(".")[0])
        opacity = float(spec.get("opacity", 1.0)) if spec else 1.0
        shader = next((node for node in material.node_tree.nodes if node.type == "BSDF_PRINCIPLED"), None)
        if opacity >= 1.0 or shader is None or any(shader.inputs[name].is_linked for name in SEE_THROUGH):
            continue
        if shader.inputs["Alpha"].default_value * (1.0 - shader.inputs["Transmission Weight"].default_value) >= 1.0:
            shader.inputs["Alpha"].default_value = opacity
            changed.append(material.name)
    print("blender_views: see-through from their specs", sorted(changed))
    return changed


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
    (the module's rule), each object wearing one set upright first, one material drawn a spec (hundreds of windows
    wearing one frame paint share it: a material each held a street's preview over 8 GB); the looks it changed."""
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
            spec = specs[name]
            if float(spec.get("opacity", 1.0)) < 1.0:  # see-through: thin_glass drew it, the module's rule
                continue
            key = json.dumps(spec, sort_keys=True)  # one material a variant, however many objects wear it
            if key not in drawn:
                material = recipes.shaded(recipes.channels(spec, spec["wear"], spec["dirt"], spec["seed"])).item()
                material.displacement_method = "BUMP"
                material.name = f"{name}-recipe"
                drawn[key] = material
            if name not in changed:
                changed.append(name)
            slot.material = drawn[key]
    print("blender_views: recipes", len(drawn), "drawn for", len(changed), "looks")
    return changed


PRIM_PATH = "usd_prim_path"  # the custom property each imported object keeps its prim's path in


class PrimPaths(bpy.types.USDHook):
    """Each imported object stamped with the path of the prim it was read from: Blender 5's reader merges a
    single-mesh Xform into its mesh and names the object for the mesh ('geo', 'geo.001'), so an object's name does not
    say which laid object it is, its prim's path does (the reader's own prim map)."""
    bl_idname = "score_prim_paths"
    bl_label = "SCORE prim paths"

    @staticmethod
    def on_import(context):
        for path, ids in context.get_prim_map().items():
            for item in ids:
                if isinstance(item, bpy.types.Object):
                    item[PRIM_PATH] = str(path)
        return True


CUT = {}  # each object a view cuts: the Blender objects it is made of (camera_cut)
LISTED_CUT = []  # the listing's own cut: a view naming none is cut so (the films' frames)


def camera_cut(objects):
    """The objects any view's `cut` names (place.json `cut`: the concept's cut-away), with everything under them,
    found for view_cut, which leaves them out of each such view's camera rays alone: the building stays closed, its cut
    wall still shades and bounces light, and that camera sees through it (owner 2026-11-19: a concept's cut is the
    camera's, never the building's). A cut object is found by its prim's path (/<place>/Objects/<name>), never by
    its Blender name."""
    arguments = sys.argv[sys.argv.index("--") + 1:]
    listing = json.loads(pathlib.Path(arguments[1]).read_text())
    LISTED_CUT[:] = listing.get("cut") or []
    names = set(LISTED_CUT) | {name for view in listing["views"] for name in view.get("cut") or []}
    laid = {}
    for item in bpy.data.objects:
        segments = str(item.get(PRIM_PATH, "")).split("/")
        if len(segments) == 4 and segments[2] == "Objects":
            laid[segments[3]] = item
    for name in sorted(names):
        found = laid.get(name)
        if found is None:
            raise RuntimeError(f"blender_views: the cut names {name}, which the scene does not hold")
        CUT[name] = [found, *found.children_recursive]
    print("blender_views: cut", sorted(names), sum(len(items) for items in CUT.values()), "objects")
    return objects


def view_cut(place_camera):
    """usd_views' camera, the view's cut (its own `cut`, else the listing's) left out of its rays and every other
    object put back in them."""
    def placed(scene, view):
        cut = set(view.get("cut", LISTED_CUT))
        for name, items in CUT.items():
            for item in items:
                item.visible_camera = name not in cut
        print("blender_views: view", view["name"], "cut", sorted(cut))
        return place_camera(scene, view)
    return placed


def with_laid_ground(importer):
    def imported(stage):
        return camera_cut(joined_ground(importer(stage)))
    return imported


def with_thin_glass(haze):
    def drawn(objects):
        specs = recipe_specs(sys.argv[sys.argv.index("--") + 1])
        see_through(objects, specs)
        thin_glass(objects)
        every = list(bpy.data.objects)  # the laid ground too, which usd_views keeps out of `objects`
        tiled_maps(every)
        recipe_looks(every, specs)
        bpy.context.scene.view_settings.look = CONTRAST
        held_pictures(bpy.context.scene)
        ground = bpy.data.objects.get(GROUND)
        if ground is not None and ground.type == "MESH":
            displaced(ground)
        hazy(objects)
        return haze(objects)
    return drawn


def held_pictures(scene):
    """Every picture drawn at most HELD_TEXELS a side (Cycles' texture limit under simplify, its other limits left at
    what the scene draws: subdivision as deep as a displaced ground is cut, every particle, volumes whole)."""
    scene.render.use_simplify = True
    scene.render.simplify_subdivision_render = max(scene.render.simplify_subdivision_render, DISPLACEMENT_LEVELS)
    scene.render.simplify_child_particles_render = 1.0
    scene.render.simplify_volumes = 1.0
    scene.cycles.texture_limit_render = HELD_TEXELS
    scene.cycles.texture_limit = HELD_TEXELS


def hazy(objects):
    """A review picture of a place holding a haze body drawn at the films' samples (usd_views.CARD_SAMPLES), not the
    review's: a night street's haze lit by its many lamps came out as dark blotches over every wall and slab behind it
    once denoised at the review's 16 (#128, 2026-11-17, the street's cafe view: flat walls kept the blotches, the haze
    taken out lost them, the light tree off left them grainy, 64 samples drew them clean)."""
    if any(item.type == "MESH" and usd_views.score_value(item, "haze_density") is not None for item in objects):
        bpy.context.scene.cycles.samples = max(bpy.context.scene.cycles.samples, usd_views.CARD_SAMPLES)


bpy.utils.register_class(PrimPaths)
usd_views.import_stage = with_laid_ground(usd_views.import_stage)
usd_views.camera = view_cut(usd_views.camera)
usd_views.haze_volumes = with_thin_glass(usd_views.haze_volumes)  # the looks' pass, never in a plain view
usd_views.main()
