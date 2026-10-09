"""From an Infinigen patch to what Godot draws, on the rented machine: a light ground with the full ground's look
baked onto it, one small model for each kind of scattered or placed thing, and where every copy stands.

- ground.glb: a grid at the spec's game cell laid on the full ground, its colour, roughness and normal baked from
  the full ground (Infinigen's procedural shaders do not run in Godot).
- <kind>-<n>.glb: each distinct mesh, thinned to the kind's triangle budget, baked from its full mesh.
- placements.json: for each model, every copy's transform in Godot's axes (y up), for one MultiMesh a model.
- stats.json: triangles, map sizes, copies, and what the full scene held, for the page and the paper.
"""
import json
import math

import bpy
import numpy as np
from mathutils import Matrix
from mathutils.bvhtree import BVHTree

import ground
import life

# Blender (z up) to glTF and Godot (y up): x stays, y becomes -z, z becomes y.
TO_GODOT = Matrix(((1, 0, 0, 0), (0, 0, 1, 0), (0, -1, 0, 0), (0, 0, 0, 1)))
MAX_COPIES = 20000


def triangles(obj):
    """Triangles in a mesh object's own data."""
    return sum(len(polygon.vertices) - 2 for polygon in obj.data.polygons)


def evaluated_bvh(obj):
    """A ray-cast tree of the object as drawn (its modifiers, displacement included), in world space."""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    return BVHTree.FromObject(obj, depsgraph, deform=True)


def godot_rows(matrix):
    """A Blender world matrix as Godot's 3 x 4 (basis rows then origin), for Transform3D."""
    converted = TO_GODOT @ matrix @ TO_GODOT.inverted()
    return [round(value, 5) for row in range(3) for value in converted[row][:4]]


def select_only(*objects):
    for obj in bpy.context.view_layer.objects:
        obj.select_set(False)
    for obj in objects:
        obj.hide_set(False)
        obj.hide_render = False
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[-1]


def unwrap(obj, margin=0.02):
    select_only(obj)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(island_margin=margin)
    bpy.ops.object.mode_set(mode="OBJECT")


def collapse(obj, budget):
    """Cut the mesh down to about `budget` triangles with Blender's collapse."""
    count = triangles(obj)
    if count > budget:
        decimate = obj.modifiers.new("thin", "DECIMATE")
        decimate.ratio = budget / count
        select_only(obj)
        bpy.ops.object.modifier_apply(modifier=decimate.name)


def thinned(source, budget, name):
    """A copy of `source` cut down to about `budget` triangles (Blender's collapse), unwrapped for baking."""
    obj = source.copy()
    obj.data = source.data.copy()
    obj.name = name
    bpy.context.scene.collection.objects.link(obj)
    obj.matrix_world = Matrix.Identity(4)
    collapse(obj, budget)
    if triangles(obj) > budget * 1.5:
        # Collapse stalls on meshes of many loose thin pieces (three of the reef's corals stayed at 66 k to
        # 188 k): make them one closed skin first, a voxel 1/80 of the model's size, then collapse that.
        obj.data = source.data.copy()
        remesh = obj.modifiers.new("skin", "REMESH")
        remesh.mode = "VOXEL"
        remesh.voxel_size = max(source.dimensions) / 80
        select_only(obj)
        bpy.ops.object.modifier_apply(modifier=remesh.name)
        collapse(obj, budget)
    obj.data.materials.clear()
    unwrap(obj)
    return obj


def baked_material(name, size, folder):
    """A material of three image maps (colour, roughness, normal) for a bake to fill; the images by pass."""
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    nodes, links = material.node_tree.nodes, material.node_tree.links
    shader = next(node for node in nodes if node.type == "BSDF_PRINCIPLED")
    images = {}
    for bake_pass in ("DIFFUSE", "ROUGHNESS", "NORMAL"):
        image = bpy.data.images.new(f"{name}-{bake_pass.lower()}", size, size, alpha=False,
                                    float_buffer=False, is_data=bake_pass != "DIFFUSE")
        image.filepath_raw = str(folder / f"{name}-{bake_pass.lower()}.png")
        image.file_format = "PNG"
        texture = nodes.new("ShaderNodeTexImage")
        texture.image = image
        if bake_pass != "DIFFUSE":
            texture.image.colorspace_settings.name = "Non-Color"
        images[bake_pass] = (image, texture)
    links.new(images["DIFFUSE"][1].outputs["Color"], shader.inputs["Base Color"])
    links.new(images["ROUGHNESS"][1].outputs["Color"], shader.inputs["Roughness"])
    normal_map = nodes.new("ShaderNodeNormalMap")
    links.new(images["NORMAL"][1].outputs["Color"], normal_map.inputs["Color"])
    links.new(normal_map.outputs["Normal"], shader.inputs["Normal"])
    return material, images


def bake_onto(low, high, size, folder, reach):
    """Bake `high`'s look (colour, roughness, normal) onto `low` through rays up to `reach` metres; the map paths."""
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 4
    material, images = baked_material(low.name, size, folder)
    low.data.materials.clear()
    low.data.materials.append(material)
    bake = scene.render.bake
    bake.use_selected_to_active = True
    bake.cage_extrusion = reach
    bake.max_ray_distance = reach * 2
    bake.margin = 4
    # Everything else out of the render while baking: Cycles otherwise loads the whole scene, millions of
    # scattered copies, for every bake (a minute and a half a model on the reef, 2026-10-05).
    others = [obj for obj in scene.objects if obj not in (low, high) and not obj.hide_render]
    for obj in others:
        obj.hide_render = True
    try:
        for bake_pass, (image, texture) in images.items():
            material.node_tree.nodes.active = texture
            select_only(high, low)
            if bake_pass == "DIFFUSE":
                bake.use_pass_direct, bake.use_pass_indirect, bake.use_pass_color = False, False, True
            bpy.ops.object.bake(type=bake_pass)
            image.save()
    finally:
        for obj in others:
            obj.hide_render = False
    return {bake_pass: image.filepath_raw for bake_pass, (image, _) in images.items()}


def export_glb(obj, path, animated=False, extra=()):
    select_only(*extra, obj)
    bpy.ops.export_scene.gltf(filepath=str(path), export_format="GLB", use_selection=True, export_yup=True,
                              export_apply=not animated, export_animations=animated, export_skins=animated,
                              export_image_format="AUTO")


def ground_model(high, side, cell, size, folder, cover=False):
    """The game's ground: a grid at `cell` metres laid on the full ground, the full ground's look baked onto it.
    With `cover`, its colour is instead the patch seen from straight above, grass and moss included, so the
    cover the game thins out still colours the ground (the meadow's 6.3 M moss clumps are kept as 60 k)."""
    tree = evaluated_bvh(high)

    def height_of(x, y):
        return np.array([life.ground_height(tree, px - side / 2, py - side / 2) for px, py in zip(x, y)])

    low = ground.grid_object("ground-game", side, cell, height_of)
    maps = bake_onto(low, high, size, folder, reach=0.6)
    if cover:
        low.hide_render = True
        from_above(side, size, maps["DIFFUSE"])
        bpy.data.images[f"{low.name}-diffuse"].reload()
    export_glb(low, folder / "ground.glb")
    return {"file": "ground.glb", "triangles": triangles(low), "texture_px": size, "maps": len(maps),
            "full_triangles": _drawn_triangles(high)}


def from_above(side, size, path):
    """The patch seen from straight above under an even white sky, written over `path`: the colour of whatever
    covers each spot of ground. Placed spots (shrubs, boulders) are left out; they stand as models of their own."""
    scene = bpy.context.scene
    hidden = [obj for obj in scene.objects if "-spot-" in obj.name and not obj.hide_render]
    lamps = [obj for obj in scene.objects if obj.type == "LIGHT" and not obj.hide_render]
    for obj in hidden + lamps:
        obj.hide_render = True
    world = bpy.data.worlds.new("even sky")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (1, 1, 1, 1)
    previous_world, previous_camera = scene.world, scene.camera
    scene.world = world
    camera = bpy.data.objects.new("above", bpy.data.cameras.new("above"))
    scene.collection.objects.link(camera)
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = side
    camera.data.clip_end = 1e4
    camera.location = (0, 0, 500)
    scene.camera = camera
    settings = scene.render
    before = (settings.resolution_x, settings.resolution_y, settings.filepath, scene.cycles.samples)
    settings.resolution_x = settings.resolution_y = size
    settings.filepath = path
    scene.cycles.samples = 32
    bpy.ops.render.render(write_still=True)
    settings.resolution_x, settings.resolution_y, settings.filepath, scene.cycles.samples = before
    scene.world, scene.camera = previous_world, previous_camera
    for obj in hidden + lamps:
        obj.hide_render = False


def _drawn_triangles(obj):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    mesh = obj.evaluated_get(depsgraph).to_mesh()
    count = sum(len(polygon.vertices) - 2 for polygon in mesh.polygons)
    obj.evaluated_get(depsgraph).to_mesh_clear()
    return count


def scatter_copies(scatter_objs):
    """Every copy each scatter object draws, in one walk of the scene's instances:
    {scatter object name: {source object name: [world matrices]}}."""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    wanted = {obj.name for obj in scatter_objs}
    copies = {name: {} for name in wanted}
    for instance in depsgraph.object_instances:
        if not instance.is_instance or instance.parent is None:
            continue
        owner = instance.parent.original.name
        if owner in wanted:
            copies[owner].setdefault(instance.instance_object.original.name, []).append(instance.matrix_world.copy())
    return copies


def realized_source(name):
    """A plain mesh copy of a scatter's source object, everything it draws realized; for baking from."""
    source = bpy.data.objects[name]
    copy = source.copy()
    copy.data = source.data.copy() if source.data else None
    bpy.context.scene.collection.objects.link(copy)
    copy.matrix_world = Matrix.Identity(4)
    copy.hide_render = False
    return life.realized(copy, f"{name}-full")


def baked_in_place(full, name, size, folder):
    """A copy of `full` at full detail, its procedural materials baked into one atlas of colour, roughness and
    normal maps by Infinigen's own exporter (tools/export.py: unwrap, bake each pass, swap in the images)."""
    from infinigen.tools import export
    obj = full.copy()
    obj.data = full.data.copy()
    obj.name = name
    bpy.context.scene.collection.objects.link(obj)
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 4
    # The ground's bake (bake_onto) leaves selected-to-active on, and Infinigen's exporter never sets it, so
    # with only this object selected every patch model's bake failed ("No valid selected objects") and fell
    # back to a copy that came back black (the reef's and the Moon's models, 2026-10-06).
    scene.render.bake.use_selected_to_active = False
    others = [item for item in scene.objects if item is not obj and not item.hide_render]
    for item in others:
        item.hide_render = True
    obj.hide_viewport = obj.hide_render = False
    try:
        select_only(obj)
        export.bake_object(obj, folder, size, False, export_name=name)
    finally:
        for item in others:
            item.hide_render = False
    return obj


def near_version(full, name, near_triangles, size, folder):
    """The game's close-up version of a full Infinigen mesh: the full mesh with Infinigen's own bake of its
    materials (colour, roughness, normal, from the full mesh), and only when it is over `near_triangles`,
    collapsed to that budget afterwards, keeping its UVs so the full mesh's maps stay on it. Godot makes the
    distance levels itself and they all wear the same maps. Never a 1% cut: the owner turned those down
    (2026-10-06). (A selected-to-active bake onto a separately unwrapped copy came back empty on the fern's
    1.5 M-triangle fronds, so the bake is always on the full mesh.)"""
    try:
        low = baked_in_place(full, name, size, folder)
    except RuntimeError as error:
        # Seen once (Moon rubble, 2026-10-06: "No valid selected objects"): bake onto a copy instead.
        print(f"[export] {name}: Infinigen's bake failed ({error}); baking onto a copy", flush=True)
        low = thinned(full, near_triangles, name)
        bake_onto(low, full, size, folder, reach=max(full.dimensions) * 0.02 + 0.002)
        return low
    one_material(low)
    collapse(low, near_triangles)
    return low


def one_material(obj):
    """After Infinigen's bake every slot wears the same baked atlas, but the slots stay: the shrub kept 285, one
    draw call each in the game (2026-10-06). Keep the first slot and put every face on it."""
    if len(obj.material_slots) < 2:
        return
    obj.data.polygons.foreach_set("material_index", [0] * len(obj.data.polygons))
    while len(obj.data.materials) > 1:
        obj.data.materials.pop(index=len(obj.data.materials) - 1)


def game_model(full, name, near_triangles, size, folder):
    """near_version written as <name>.glb; the object."""
    low = near_version(full, name, near_triangles, size, folder)
    export_glb(low, folder / f"{name}.glb")
    return low


def lod_chain(near, name, folder, shares=(0.25, 0.06), smallest=20000):
    """Lighter levels of a close-up model for distance, <name>-lod1.glb and -lod2.glb: the same mesh collapsed to
    `shares` of its triangles, keeping its UVs, so they wear the full mesh's baked maps (normals included).
    Godot's own LOD generation made no levels for the coral and boulder (their bake's UV seams block its
    simplifier, 2026-10-06), so the levels are made here. None for a model under `smallest` triangles."""
    levels = []
    count = triangles(near)
    if count < smallest:
        return levels
    for level, share in enumerate(shares, 1):
        lighter = near.copy()
        lighter.data = near.data.copy()
        lighter.name = f"{name}-lod{level}"
        bpy.context.scene.collection.objects.link(lighter)
        collapse(lighter, int(count * share))
        export_glb(lighter, folder / f"{lighter.name}.glb")
        levels.append({"file": f"{lighter.name}.glb", "triangles": triangles(lighter)})
    return levels


def model(source_full, kind, number, near_triangles, size, folder):
    """One game model from a full mesh (game_model), written as <kind>-<number>.glb."""
    name = f"{kind}-{number}"
    low = game_model(source_full, name, near_triangles, size, folder)
    return {"file": f"{name}.glb", "kind": kind, "triangles": triangles(low), "texture_px": size,
            "full_triangles": triangles(source_full), "lods": lod_chain(low, name, folder)}


def scattered(scatter_objs, game, folder):
    """Every scatter's distinct sources as game models, with their copies' transforms; (models, placements)."""
    models, placements = [], {}
    every = scatter_copies(list(scatter_objs.values()))
    for scatter_obj in scatter_objs.values():
        scatter_obj.hide_viewport = True  # so realizing each source walks only what it draws (life.realized)
    for kind, scatter_obj in scatter_objs.items():
        budget = game["near_triangles"].get(kind, 300000)
        for number, (name, matrices) in enumerate(sorted(every[scatter_obj.name].items())):
            full = realized_source(name)
            if not full.data.polygons:
                print(f"[export] {kind} source {name} realized empty; left out", flush=True)
                bpy.data.objects.remove(full, do_unlink=True)
                continue
            made = model(full, kind, number, budget, game["asset_texture_px"], folder)
            limit = game.get("max_copies", {}).get(kind, MAX_COPIES * len(every[scatter_obj.name]))
            step = max(1, math.ceil(len(matrices) * len(every[scatter_obj.name]) / limit))
            made.update(copies_full=len(matrices), copies=len(matrices[::step]))
            placements[made["file"]] = [godot_rows(matrix) for matrix in matrices[::step]]
            models.append(made)
            bpy.data.objects.remove(full, do_unlink=True)
    return models, placements


def placed(objects, game, folder):
    """The spots' linked copies as one game model per shared mesh, with every copy's transform."""
    models, placements, by_mesh = [], {}, {}
    for obj in objects:
        by_mesh.setdefault(obj.data.name, []).append(obj)
    for number, (mesh_name, users) in enumerate(sorted(by_mesh.items())):
        kind = users[0].name.split("-spot-")[0]
        budget = game["near_triangles"].get(kind.split("-")[-1], game["near_triangles"]["plant"])
        full = bpy.data.objects.new(f"{mesh_name}-full", bpy.data.meshes[mesh_name])
        bpy.context.scene.collection.objects.link(full)
        made = model(full, kind, number, budget, game["asset_texture_px"], folder)
        made.update(copies_full=len(users), copies=len(users))
        placements[made["file"]] = [godot_rows(obj.matrix_world) for obj in users]
        models.append(made)
    return models, placements


def write(folder, spec, ground_entry, models, placements, extra):
    """placements.json and stats.json beside the models."""
    drawn = ground_entry["triangles"] + sum(item["triangles"] * item["copies"] for item in models)
    full = ground_entry["full_triangles"] + sum(item["full_triangles"] * item["copies_full"] for item in models)
    stats = {"kind": spec["kind"], "side_m": spec.get("side_m"), "ground": ground_entry, "models": models,
             "game_triangles_all_copies": drawn, "full_triangles_all_copies": full, **extra}
    lods = {item["file"]: [level["file"] for level in item.get("lods", [])] for item in models}
    (folder / "placements.json").write_text(json.dumps({"ground": ground_entry["file"], "models": placements,
                                                        "lods": lods,
                                                        **{key: extra[key] for key in ("water", "camera", "views", "look")
                                                           if key in extra}}))
    (folder / "stats.json").write_text(json.dumps(stats, indent=1))
    return stats


def fish_model(armature, meshes, game, folder):
    """The fish for the game: its body at close-up detail (armature kept, weights carried), baked, with its swim."""
    for mesh in meshes:
        for modifier in mesh.modifiers:
            if modifier.type == "ARMATURE":
                modifier.show_viewport = False
    depsgraph = bpy.context.evaluated_depsgraph_get()
    rest = []
    for mesh in meshes:
        data = bpy.data.meshes.new_from_object(mesh.evaluated_get(depsgraph), preserve_all_data_layers=True,
                                               depsgraph=depsgraph)
        data.transform(mesh.matrix_world)
        rest.append(data)
    full = life.join_meshes(rest, "fish-full")
    low = near_version(full, "fish", game["near_triangles"]["fish"], game["asset_texture_px"], folder)
    _carry_weights(low, meshes)
    low.parent = armature
    low.matrix_parent_inverse = armature.matrix_world.inverted()
    skin = low.modifiers.new("skin", "ARMATURE")
    skin.object = armature
    export_glb(low, folder / "fish.glb", animated=True, extra=(armature,))
    return {"file": "fish.glb", "triangles": triangles(low), "texture_px": game["asset_texture_px"],
            "full_triangles": triangles(full), "bones": len(armature.data.bones)}


def _carry_weights(low, meshes):
    """Give the thinned body the bone weights of the full body (nearest surface), by Blender's data transfer."""
    for mesh in meshes:
        for group in mesh.vertex_groups:
            if group.name not in low.vertex_groups:
                low.vertex_groups.new(name=group.name)
        transfer = low.modifiers.new("weights", "DATA_TRANSFER")
        transfer.object = mesh
        transfer.use_vert_data = True
        transfer.data_types_verts = {"VGROUP_WEIGHTS"}
        transfer.vert_mapping = "POLYINTERP_NEAREST"
        transfer.layers_vgroup_select_src = "ALL"
        transfer.layers_vgroup_select_dst = "NAME"
        select_only(low)
        bpy.ops.object.modifier_apply(modifier=transfer.name)
