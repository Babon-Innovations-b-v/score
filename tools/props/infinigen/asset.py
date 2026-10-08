"""One Infinigen asset for the game, on the rented machine (patch.py runs it for a spec of kind "asset"): the asset
as Infinigen makes it, a Cycles picture of it from a framing camera the game's view uses too, its close-up model
with Infinigen's materials baked into maps, two picture cards for far away, and on request a plain picture to
give Pixal3D.

Writes into the out folder: infinigen.png, asset.glb, card-front.png and card-side.png (transparent), pixal-input.png
when asked, and stats.json (triangles made and kept, map size, bounds, the camera).
"""
import importlib
import json
import math

import bpy
from mathutils import Vector

import game_export
import life

# The framing camera: a 50 mm lens on a 36 mm-wide film, turned 35 degrees off the asset's front, 10 degrees up.
LENS_MM = 50.0
TURN_DEG, LIFT_DEG = 35.0, 10.0
FILL = 1.2
CARD_PX = 1024
GREY = (0.45, 0.46, 0.47)


def made(spec):
    """The asset as Infinigen makes it, realized into one mesh standing on its base at the origin; for the fish,
    (armature, meshes) too."""
    if spec["factory"] == "fish":
        root, armature, meshes = life.fish(spec["seed"])
        frames = 24
        bpy.context.scene.render.fps = 24
        life.looped_drivers(armature, frames)
        life.bake_swim(armature, frames)
        bpy.context.scene.frame_set(0)
        return root, armature, meshes
    module_name, class_name = spec["factory"].rsplit(".", 1)
    factory = getattr(importlib.import_module(module_name), class_name)(spec["seed"])
    spawned = factory.spawn_asset(spec.get("index", 0))
    # Some factories put their materials on in finalize_assets (the grass tuft), as Infinigen's own
    # generate_individual_assets calls it after spawn_asset.
    factory.finalize_assets(spawned)
    if spec.get("instanced"):
        return spawned, None, None
    obj = life.realized(spawned, spec["name"])
    life.centred_on_base(obj)
    return obj, None, None


def instanced_parts(spawned):
    """What an instanced asset (an Infinigen tree: 2.9 M-triangle trunk, 4,700 twigs of 23,000 triangles, 450 fruit
    of 165,000; 190 M triangles realized) draws, kept as instances: (one mesh object of everything drawn directly,
    {instanced object: [world matrices]})."""
    items = life.hierarchy(spawned)
    names = {item.name for item in items}
    depsgraph = bpy.context.evaluated_depsgraph_get()
    direct, copies = [], {}
    for instance in depsgraph.object_instances:
        source = instance.instance_object if instance.is_instance else instance.object
        owner = instance.parent.original.name if instance.is_instance and instance.parent else source.original.name
        if owner not in names or source.type != "MESH":
            continue
        if instance.is_instance:
            copies.setdefault(source.original, []).append(instance.matrix_world.copy())
        else:
            mesh = bpy.data.meshes.new_from_object(source.evaluated_get(depsgraph), depsgraph=depsgraph)
            mesh.transform(instance.matrix_world.copy())
            direct.append(mesh)
    return life.join_meshes(direct, "asset-direct"), copies


def part_object(source, name):
    """One instanced object as a plain mesh object at the origin, in its own coordinates."""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    mesh = bpy.data.meshes.new_from_object(source.evaluated_get(depsgraph), depsgraph=depsgraph)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def instanced_bounds(direct, copies):
    """(lowest, highest) corner over the direct mesh and every instance's box."""
    corners = [Vector(corner) for corner in direct.bound_box]
    for source, matrices in copies.items():
        box = [Vector(corner) for corner in source.bound_box]
        for matrix in matrices:
            corners += [matrix @ box[0], matrix @ box[6]]
    low = Vector((min(c.x for c in corners), min(c.y for c in corners), min(c.z for c in corners)))
    high = Vector((max(c.x for c in corners), max(c.y for c in corners), max(c.z for c in corners)))
    return low, high


def export_instanced(spawned, spec, folder):
    """An instanced asset for the game: asset.glb (what is drawn directly), part-<n>.glb for each instanced object,
    and parts.json (each part's copies as Godot transforms); each at close-up detail with Infinigen's own bake.
    Returns (triangles made, triangles kept, parts)."""
    direct, copies = instanced_parts(spawned)
    size = spec["game"]["asset_texture_px"]
    caps = spec["game"]["near_triangles"]
    made = game_export.triangles(direct)
    kept = game_export.triangles(game_export.game_model(direct, "asset", caps[spec["kind_of"]], size, folder))
    parts = []
    for number, (source, matrices) in enumerate(sorted(copies.items(), key=lambda item: item[0].name)):
        full = part_object(source, f"part-{number}-full")
        cap = caps["fruit"] if "Fruit" in source.name else caps["twig"]
        low = game_export.game_model(full, f"part-{number}", cap, size // 2, folder)
        each_full, each_kept = game_export.triangles(full), game_export.triangles(low)
        made += each_full * len(matrices)
        kept += each_kept * len(matrices)
        parts.append({"file": f"part-{number}.glb", "source": source.name, "copies": len(matrices),
                      "full_triangles": each_full, "triangles": each_kept,
                      "rows": [game_export.godot_rows(matrix) for matrix in matrices]})
    (folder / "parts.json").write_text(json.dumps(parts))
    return made, kept, len(parts)


def world_bounds(objects):
    """(lowest corner, highest corner) over the objects' evaluated meshes, in world space."""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    corners = []
    for obj in objects:
        evaluated = obj.evaluated_get(depsgraph)
        corners += [evaluated.matrix_world @ Vector(corner) for corner in evaluated.bound_box]
    low = Vector((min(c.x for c in corners), min(c.y for c in corners), min(c.z for c in corners)))
    high = Vector((max(c.x for c in corners), max(c.y for c in corners), max(c.z for c in corners)))
    return low, high


def framing(low, high, aspect=16 / 9, turn_deg=TURN_DEG, lift_deg=LIFT_DEG):
    """The camera that frames the box: its place, its target and lens, in Blender metres (z up)."""
    centre = (low + high) / 2
    radius = (high - low).length / 2
    half_width = math.atan(18.0 / LENS_MM)
    half_height = math.atan(math.tan(half_width) / aspect)
    distance = radius * FILL / math.sin(min(half_width, half_height))
    turn, lift = math.radians(turn_deg), math.radians(lift_deg)
    # The front faces -y in Blender, so the camera stands on the -y side, turned toward +x.
    offset = Vector((math.sin(turn) * math.cos(lift), -math.cos(turn) * math.cos(lift), math.sin(lift))) * distance
    place = centre + offset
    return {"x": place.x, "y": place.y, "z": place.z, "look_x": centre.x, "look_y": centre.y, "look_z": centre.z,
            "lens_mm": LENS_MM, "near": max(0.01, distance - radius * 2), "far": distance + radius * 3}


def camera_from(shot, name="camera", orthographic=None):
    obj = bpy.data.objects.new(name, bpy.data.cameras.new(name))
    bpy.context.scene.collection.objects.link(obj)
    obj.location = (shot["x"], shot["y"], shot["z"])
    target = Vector((shot["look_x"], shot["look_y"], shot["look_z"]))
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()
    obj.data.lens = shot.get("lens_mm", LENS_MM)
    obj.data.clip_start, obj.data.clip_end = 0.01, 1e4
    if orthographic:
        obj.data.type = "ORTHO"
        obj.data.ortho_scale = orthographic
    bpy.context.scene.camera = obj
    return obj


def studio(look):
    """A grey studio: a soft sky and one sun from the front-left, as the game's view lights it."""
    world = bpy.context.scene.world or bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    world.use_nodes = True
    background = next(node for node in world.node_tree.nodes if node.type == "BACKGROUND")
    background.inputs["Color"].default_value = (*GREY, 1)
    background.inputs["Strength"].default_value = 1.0
    lamp = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    bpy.context.scene.collection.objects.link(lamp)
    lamp.data.energy = 3.0
    lamp.data.angle = math.radians(3)
    lamp.rotation_euler = (math.radians(90 - look["sun_elevation_deg"]), 0, math.radians(look["sun_azimuth_deg"]))
    return lamp


def still(path, size, samples=96, transparent=False):
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.render.film_transparent = transparent
    scene.render.resolution_x, scene.render.resolution_y = size
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA" if transparent else "RGB"
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def albedo_output():
    """Make renders write the asset's own colour (Cycles' diffuse colour pass) with its alpha, so a card is lit by
    the game's light, not baked in Cycles'."""
    scene = bpy.context.scene
    bpy.context.view_layer.use_pass_diffuse_color = True
    scene.use_nodes = True
    tree = scene.node_tree
    tree.nodes.clear()
    layers = tree.nodes.new("CompositorNodeRLayers")
    alpha = tree.nodes.new("CompositorNodeSetAlpha")
    out = tree.nodes.new("CompositorNodeComposite")
    tree.links.new(layers.outputs["DiffCol"], alpha.inputs["Image"])
    tree.links.new(layers.outputs["Alpha"], alpha.inputs["Alpha"])
    tree.links.new(alpha.outputs["Image"], out.inputs["Image"])


def cards(low, high, folder):
    """Front and side pictures of the asset's own colour on a clear background, square, for the far-away cards;
    their sizes."""
    centre = (low + high) / 2
    size = high - low
    shots = {}
    albedo_output()
    for side, direction, across in (("front", Vector((0, -1, 0)), size.x), ("side", Vector((1, 0, 0)), size.y)):
        span = max(across, size.z) * 1.02
        place = centre + direction * (size.length + 5)
        camera_from({"x": place.x, "y": place.y, "z": place.z, "look_x": centre.x, "look_y": centre.y,
                     "look_z": centre.z}, f"card-{side}", orthographic=span)
        still(folder / f"card-{side}.png", (CARD_PX, CARD_PX), samples=48, transparent=True)
        shots[side] = {"span_m": span, "centre": [centre.x, centre.y, centre.z]}
    bpy.context.scene.use_nodes = False
    return shots


def asset(spec, folder, steps):
    """Make, picture, bake and export one asset; its stats."""
    obj, armature, meshes = made(spec)
    shown = meshes if armature else [obj]
    instanced = bool(spec.get("instanced"))
    full_triangles = None if armature or instanced else sum(game_export.triangles(item) for item in shown)
    steps("made")
    if instanced:
        direct, copies = instanced_parts(obj)
        low, high = instanced_bounds(direct, copies)
        bpy.data.objects.remove(direct, do_unlink=True)
    else:
        low, high = world_bounds(shown)
    shot = framing(low, high)
    studio(spec["look"])
    camera_from(shot)
    still(folder / "infinigen.png", (1280, 720))
    if spec.get("pixal_input"):
        # Straight on and square, as the prop chain's pictures are drawn.
        camera_from(framing(low, high, aspect=1.0, turn_deg=20, lift_deg=8))
        still(folder / "pixal-input.png", (1024, 1024))
    card_shots = cards(low, high, folder)
    steps("pictures")
    size = spec["game"]["asset_texture_px"]
    cap = spec["game"]["near_triangles"][spec["kind_of"]]
    parts, lods = 0, []
    if instanced:
        full_triangles, kept, parts = export_instanced(obj, spec, folder)
    elif armature:
        entry = game_export.fish_model(armature, meshes, spec["game"], folder)
        full_triangles = entry["full_triangles"]
        kept = entry["triangles"]
        (folder / "fish.glb").rename(folder / "asset.glb")
    else:
        near = game_export.game_model(obj, "asset", cap, size, folder)
        kept = game_export.triangles(near)
        lods = game_export.lod_chain(near, "asset", folder)
    steps("baked and exported")
    stats = {"kind": "asset", "name": spec["name"], "factory": spec["factory"], "seed": spec["seed"],
             "full_triangles": full_triangles, "triangles": kept, "near_cap": cap, "texture_px": size,
             "bounds": [list(low), list(high)], "camera": shot, "cards": card_shots,
             "animated": bool(armature), "instanced_parts": parts, "lods": lods, "look": spec["look"]}
    (folder / "stats.json").write_text(json.dumps(stats, indent=1))
    return stats
