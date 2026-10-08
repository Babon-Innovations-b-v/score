"""Runs inside Blender (`session.py batch`): load a place's OpenUSD stage and render fixed views of it.

    python3 tools/blender/session.py batch tools/blender/inside/usd_views.py -- <stage.usda> <views.json> <out folder>

views.json: {"size": [wide, tall], "views": [{"name", "eye", "aim", "up", "fov"}]}, points in the stage's own frame
(metres, y up), `fov` the angle across the picture in degrees. Per view it writes <name>-look.png (the place on a
plain grey ground under a low sun, black sky), <name>-mask.png (the place's objects alone on a transparent
background: the alpha is where they are), <name>-ground.png (the ground alone, the same way), and report.json with what came in: objects, materials, each object's
score:* properties, and the stage's layers as Blender's own USD library composed them. A view with `"look_only": true`
(a walkthrough's frame) gets its look alone.
"""
import json
import math
import pathlib
import sys

import bpy
from mathutils import Matrix, Vector

GROUND_SIDE = 600.0
GROUND_COLOUR = (0.16, 0.15, 0.14, 1.0)
SUN_ELEVATION = 20.0
SUN_HEADING = 45.0
SUN_STRENGTH = 4.0
SAMPLES = 16
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


def sun(scene):
    data = bpy.data.lights.new("sun", type="SUN")
    data.energy = SUN_STRENGTH
    light = bpy.data.objects.new("sun", data)
    light.rotation_euler = (math.radians(90 - SUN_ELEVATION), 0.0, math.radians(SUN_HEADING))
    scene.collection.objects.link(light)


def black_sky(scene):
    world = bpy.data.worlds.new("sky")
    world.use_nodes = True
    background = next(node for node in world.node_tree.nodes if node.type == "BACKGROUND")
    background.inputs["Color"].default_value = (0.0, 0.0, 0.0, 1.0)
    scene.world = world


def renderer(scene, size):
    """Eevee on the processor's drawing, the picture's size, PNG with alpha."""
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
    scene.view_settings.view_transform = "Standard"


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
    sun(scene)
    plane = ground(scene)
    for view in views["views"]:
        camera(scene, view)
        plane.hide_render = False
        render(scene, out / f"{view['name']}-look.png", transparent=False)
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
