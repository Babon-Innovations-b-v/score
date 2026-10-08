"""Runs inside Blender (`session.py batch`): load a place's OpenUSD stage and render fixed views of it.

    python3 tools/blender/session.py batch tools/blender/inside/usd_views.py -- <stage.usda> <views.json> <out folder>

views.json: {"size": [wide, tall], "views": [{"name", "eye", "aim", "up", "fov"}], "plain": false}, points in the
stage's own frame (metres, y up), `fov` the angle across the picture in degrees. Per view it writes <name>-look.png
(the place in its baked materials on its own ground, the stage's `Ground` when it has one and a plain grey plane at
y = 0 when it has none, under a low sun with a weak fill from the other side and a little sky light, so a side away
from the sun is dark but never black; the sky itself is black), <name>-mask.png (the place's objects alone on a
transparent background: the alpha is where they are), <name>-ground.png (the ground alone, the same way), and
report.json with what came in: objects, materials, each object's score:* properties, and the stage's layers as
Blender's own USD library composed them. A view with `"look_only": true` (a walkthrough's frame) gets its look alone.
`"plain": true` draws every object in one plain grey instead of its materials: a debug view of shape alone.
`"lights": [{"at", "energy", "radius"}]` adds point lights (a room's lamps, watts); a view with `"hide_layers": [2]`
leaves out every object whose `score:layer` is one of them (a room's roof, for a cutaway look in).
"""
import json
import math
import os
import pathlib
import sys

import bpy
from mathutils import Matrix, Vector

GROUND_SIDE = 600.0
GROUND_COLOUR = (0.16, 0.15, 0.14, 1.0)
SUN_ELEVATION = 20.0
SUN_HEADING = 45.0
SUN_STRENGTH = 4.0
# The fill: a weak second sun from the other side, low, as earthshine and the ground's own bounce light the game's
# shadow sides, and the sky's light everywhere (the game's ambient 0.2).
FILL_STRENGTH = 0.5
FILL_ELEVATION = 25.0
SKY_LIGHT = 0.04
PLAIN_COLOUR = (0.6, 0.6, 0.6, 1.0)
SAMPLES = 16
CARD_SAMPLES = 64
# The stage's y-up frame onto Blender's z-up: (x, y, z) -> (x, -z, y), as Blender's importer turns a y-up stage.
Y_UP_TO_Z_UP = Matrix(((1, 0, 0), (0, 0, -1), (0, 1, 0)))


def arguments():
    given = sys.argv[sys.argv.index("--") + 1:]
    if len(given) != 3:
        raise SystemExit(__doc__)
    return pathlib.Path(given[0]), json.loads(pathlib.Path(given[1]).read_text()), pathlib.Path(given[2])


def empty_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    return bpy.context.scene


def import_stage(stage):
    """The stage composed and brought in: drawn meshes and their materials, no guides (the colliders), every
    attribute as a custom property, the maps read where they lie."""
    before = set(bpy.data.objects)
    result = bpy.ops.wm.usd_import(filepath=str(stage), import_guide=False, import_proxy=False,
                                   import_textures_mode="IMPORT_NONE", property_import_mode="ALL",
                                   import_lights=False, create_world_material=False)
    if "FINISHED" not in result:
        raise RuntimeError(f"Blender did not import {stage}: {result}")
    return [item for item in bpy.data.objects if item not in before]


def layer_stack(stage):
    """The stage's layers, strongest first, as the pxr library inside Blender composes them."""
    from pxr import Usd
    opened = Usd.Stage.Open(str(stage))
    return [pathlib.Path(layer.realPath).name for layer in opened.GetLayerStack(includeSessionLayers=False)]


def score_properties(item):
    """An imported object's score:* custom properties (Blender keeps the attribute's name)."""
    return {key: (list(value) if hasattr(value, "__len__") and not isinstance(value, str) else value)
            for key, value in item.items() if "score" in key}


def import_report(stage, objects):
    meshes = [item for item in objects if item.type == "MESH"]
    return {
        "stage": str(stage),
        "layers": layer_stack(stage),
        "objects": len(objects),
        "meshes": len(meshes),
        "triangles": sum(sum(len(polygon.vertices) - 2 for polygon in item.data.polygons) for item in meshes),
        "materials": sorted({slot.material.name for item in meshes for slot in item.material_slots if slot.material}),
        "properties": {item.name: score_properties(item) for item in objects if score_properties(item)},
        "slots": {item.name: [slot.material.name for slot in item.material_slots if slot.material] for item in meshes},
        "placed": {item.name: [round(value, 4) for value in item.matrix_world.translation] for item in objects},
    }


def ground(scene):
    """A plain grey plane under the place, where the stage's y is zero."""
    mesh = bpy.data.meshes.new("ground")
    half = GROUND_SIDE / 2
    mesh.from_pydata([(-half, -half, 0), (half, -half, 0), (half, half, 0), (-half, half, 0)], [], [(0, 1, 2, 3)])
    material = bpy.data.materials.new("ground")
    material.use_nodes = True
    shader = next(node for node in material.node_tree.nodes if node.type == "BSDF_PRINCIPLED")
    shader.inputs["Base Color"].default_value = GROUND_COLOUR
    shader.inputs["Roughness"].default_value = 1.0
    mesh.materials.append(material)
    plane = bpy.data.objects.new("ground", mesh)
    scene.collection.objects.link(plane)
    return plane


def sun(scene, name, strength, elevation, heading):
    data = bpy.data.lights.new(name, type="SUN")
    data.energy = strength
    light = bpy.data.objects.new(name, data)
    light.rotation_euler = (math.radians(90 - elevation), 0.0, math.radians(heading))
    scene.collection.objects.link(light)


def black_sky(scene):
    """A black sky that still lights the place a little (the game's ambient light), seen black by the camera."""
    world = bpy.data.worlds.new("sky")
    world.use_nodes = True
    nodes, links = world.node_tree.nodes, world.node_tree.links
    background = next(node for node in nodes if node.type == "BACKGROUND")
    background.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)
    background.inputs["Strength"].default_value = SKY_LIGHT
    seen = nodes.new("ShaderNodeBackground")
    seen.inputs["Color"].default_value = (0.0, 0.0, 0.0, 1.0)
    path = nodes.new("ShaderNodeLightPath")
    mix = nodes.new("ShaderNodeMixShader")
    output = next(node for node in nodes if node.type == "OUTPUT_WORLD")
    links.new(path.outputs["Is Camera Ray"], mix.inputs["Fac"])
    links.new(background.outputs["Background"], mix.inputs[1])
    links.new(seen.outputs["Background"], mix.inputs[2])
    links.new(mix.outputs["Shader"], output.inputs["Surface"])
    scene.world = world


def plain(objects):
    """Every object drawn in one plain grey: the debug view of shape alone."""
    material = bpy.data.materials.new("plain")
    material.use_nodes = True
    next(node for node in material.node_tree.nodes if node.type == "BSDF_PRINCIPLED").inputs[
        "Base Color"].default_value = PLAIN_COLOUR
    for item in objects:
        if item.type == "MESH":
            item.data.materials.clear()
            item.data.materials.append(material)


def stage_ground(objects):
    """The stage's own ground (its `Ground` prim), as Blender brought it in, or None."""
    return next((item for item in objects if item.type == "MESH" and item.name.split(".")[0] == "Ground"), None)


def cycles_on_card(scene):
    """Cycles on the machine's graphics card (OptiX, else CUDA), denoised: a rented card machine
    (tools/props/cloud/blender_cloud.py sets FARM_CYCLES_GPU)."""
    scene.render.engine = "CYCLES"
    preferences = bpy.context.preferences.addons["cycles"].preferences
    for kind in ("OPTIX", "CUDA"):
        try:
            preferences.compute_device_type = kind
        except TypeError:
            continue
        preferences.get_devices()
        if any(device.type == kind for device in preferences.devices):
            for device in preferences.devices:
                device.use = device.type == kind
            scene.cycles.device = "GPU"
            scene.cycles.samples = CARD_SAMPLES
            scene.cycles.use_denoising = True
            return
    raise RuntimeError("FARM_CYCLES_GPU is set but no OptiX or CUDA card was found")


def cycles_on_processor(scene):
    """Cycles on a rented processor machine, denoised: no screen there for Eevee (FARM_CYCLES_CPU)."""
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = CARD_SAMPLES
    scene.cycles.use_denoising = True


def renderer(scene, size):
    """Eevee on the processor's drawing (here), or Cycles on a rented card or processor machine, the picture's size,
    PNG with alpha."""
    if os.environ.get("FARM_CYCLES_GPU"):
        cycles_on_card(scene)
    elif os.environ.get("FARM_CYCLES_CPU"):
        cycles_on_processor(scene)
    else:
        for engine in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
            try:
                scene.render.engine = engine
                break
            except TypeError:
                continue
        scene.eevee.taa_render_samples = SAMPLES
    scene.render.resolution_x, scene.render.resolution_y = size
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    for transform in ("AgX", "Filmic", "Standard"):  # the film's tone curve, as the game's tonemap; the first known
        try:
            scene.view_settings.view_transform = transform
            break
        except TypeError:
            continue


def stage_point(values):
    return Y_UP_TO_Z_UP @ Vector(values)


def camera(scene, view):
    """A camera at the view's eye looking at its aim, its up the view's up, its angle across the picture."""
    data = bpy.data.cameras.new(view["name"])
    data.sensor_fit = "HORIZONTAL"
    data.angle = math.radians(view["fov"])
    data.clip_start, data.clip_end = 0.05, 2000.0
    item = bpy.data.objects.new(view["name"], data)
    scene.collection.objects.link(item)
    eye, aim, up = stage_point(view["eye"]), stage_point(view["aim"]), stage_point(view["up"])
    back = (eye - aim).normalized()
    across = up.cross(back).normalized()
    item.matrix_world = Matrix.Translation(eye) @ Matrix((across, back.cross(across), back)).transposed().to_4x4()
    scene.camera = item
    return item


def render(scene, path, transparent):
    scene.render.film_transparent = transparent
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def lamps(scene, lights):
    """Point lights where a room's lamps hang."""
    for number, light in enumerate(lights):
        data = bpy.data.lights.new(f"lamp_{number}", type="POINT")
        data.energy = float(light["energy"])
        data.shadow_soft_size = float(light.get("radius", 0.1))
        item = bpy.data.objects.new(f"lamp_{number}", data)
        item.location = stage_point(light["at"])
        scene.collection.objects.link(item)


def layer_of(item):
    """An imported object's kit layer: its own `score:layer` or the nearest parent's, None without one."""
    while item is not None:
        for key, value in item.items():
            if key.endswith("layer") and "score" in key:
                return int(value)
        item = item.parent
    return None


def set_hidden(objects, hidden):
    for item in objects:
        item.hide_render = hidden


def main():
    stage, views, out = arguments()
    out.mkdir(parents=True, exist_ok=True)
    scene = empty_scene()
    objects = import_stage(stage)
    (out / "report.json").write_text(json.dumps(import_report(stage, objects), indent=1))
    renderer(scene, views["size"])
    black_sky(scene)
    sun(scene, "sun", SUN_STRENGTH, SUN_ELEVATION, SUN_HEADING)
    sun(scene, "fill", FILL_STRENGTH, FILL_ELEVATION, SUN_HEADING + 180.0)
    plane = stage_ground(objects)
    if plane is None:
        plane = ground(scene)
    else:
        objects = [item for item in objects if item is not plane]
    if views.get("plain"):
        plain(objects)
    lamps(scene, views.get("lights", []))
    layers = {item.name: layer_of(item) for item in objects}
    for view in views["views"]:
        camera(scene, view)
        plane.hide_render = False
        hidden = [item for item in objects if layers[item.name] in view.get("hide_layers", [])]
        set_hidden(hidden, True)
        render(scene, out / f"{view['name']}-look.png", transparent=False)
        set_hidden(hidden, False)
        if view.get("look_only"):
            continue
        plane.hide_render = True
        render(scene, out / f"{view['name']}-mask.png", transparent=True)
        plane.hide_render = False
        set_hidden(objects, True)
        render(scene, out / f"{view['name']}-ground.png", transparent=True)
        set_hidden(objects, False)
    print("usd_views: wrote", out)


main()
