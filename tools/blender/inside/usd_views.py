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
leaves out every object whose `score:layer` is one of them (a room's roof, for a cutaway look in), and one with
`"hide_over": {"above", "low", "high"}` every mesh wholly over that height standing over that floor (a room whose roof
has no layer of its own, and the building on top of it). A view with
`"frame": <n>` is drawn at that time code of the stage, so its characters (tools/characters/cast.py) stand in that
moment of their clips; a walkthrough's frames give consecutive ones, so they move. A view with `"eyes": [...]` in place
of one eye is seen from the first of them with a clear line to its aim (a character's views, where a wall may stand
in front of somebody). A view with `"hide_crowds": true` leaves out every instancer (a crowd, tools/characters/cast.py), so
one of a group standing among thousands is seen close. What the motion stage moves (tools/usd/motion.py) is drawn
where it stands at the view's `frame`: a moving prim through Blender's own reader, a switched light by its keyed
energy. Objects the stage makes invisible (the body parts a character does not wear) stay out of every picture.

The stage's effects (tools/usd/effects.py: UsdGeomPoints with score:kind "effect", looped from their clips) are drawn
here at each view's frame, since Blender's reader leaves their displayOpacity out: each particle a sphere, a speck flat
and unlit, a puff lit and soft as the game's dust puff, faded near the eye; they are air like the haze, so left out of
the masks, and never hidden as a crowd.

What the stage's sky holds is drawn as the game draws it: a haze body (score:kind "haze" with score:haze_*,
tools/usd/scene.py) filled with fog of its colour and thickness out to its reach from the eye, lit by the sun and
the lamps but not by the sky's ambient light, and a water surface with score:mirror_* given back
as the game's harbour mirrors it (more along it than down into it, its ripples breaking what it mirrors into streaks).
A view with `"ink": true` also gets <name>-ink.png: its look with the game's ink lines over it (ink_edges.gdshader's
rule, worked out on the depth Cycles gives in a second, one-sample render), an option beside the look and never
baked into the stage.
"""
import json
import math
import os
import pathlib
import sys

import bpy
from bpy_extras import anim_utils
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
# How many see-through particles a ray passes on its way through an effect (tools/usd/effects.py) before it stops.
EFFECT_BOUNCES = 256
SAMPLES = 16
CARD_SAMPLES = 64
# The game's ink lines (2099's ink_edges.gdshader and ink_edges.tres), its numbers as it has them: a pixel is inked
# where its neighbours `reach` pixels out average further away than it by DEPTH_BREAK (in one over the distance, so a
# flat floor at any angle is not), or where it turns from a nearer-or-level neighbour past CREASE_BREAK; the reach is
# LINE_PX on a 1080-tall picture (TEXTURED_PX on a textured model, whose creases count only where its shape turns a
# corner too), easing to a pixel from THIN_START to THIN_END metres; lines fade out from FADE_START to FADE_END.
INK_DEPTH_BREAK = 0.02
INK_CREASE_BREAK = 0.5
INK_LEVEL = 0.995
INK_FLAT_SIDE = 0.95
INK_SPAN = 2.0
INK_SPAN_PX = 3.0
INK_SHAPE_TURN = 0.25
INK_FADE = (60.0, 120.0)
INK_LINE_PX = 4.0
INK_TEXTURED_PX = 1.5
INK_THIN = (8.0, 35.0)
INK_SMALL_PART_SHARE = 0.35
INK_REACH = ((1.0, 0.0), (-1.0, 0.0), (0.0, 1.0), (0.0, -1.0), (0.7071, 0.7071), (-0.7071, -0.7071), (0.7071, -0.7071),
             (-0.7071, 0.7071))
INK_COLOUR = (0.039215688, 0.03529412, 0.03137255)
# The water's ripples: how far a ripple moves the surface for Blender's bump, as a share of its tip times its size,
# so the noise's slopes come out about as steep as the game's tip.
RIPPLE_BUMP_SHARE = 2.0
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
    leave_prototypes_out()
    return [item for item in bpy.data.objects if item not in before]


def leave_prototypes_out():
    """A point instancer's prototypes (the planned rocks' models, a crowd's bodies) drawn only where it copies them:
    Blender's reader gathers them in a `prototypes` collection that would otherwise draw each at the stage's origin,
    so that collection is left out of the view layer (its copies still draw)."""
    for layer_collection in bpy.context.view_layer.layer_collection.children:
        if layer_collection.collection.name.startswith("prototypes"):
            layer_collection.exclude = True


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
        "properties": {item.name: found for item in objects if (found := score_properties(item))},
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
        scene.render.engine = "BLENDER_EEVEE"
        scene.eevee.taa_render_samples = SAMPLES
    scene.render.resolution_x, scene.render.resolution_y = size
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.view_settings.view_transform = "AgX"  # the film's tone curve, as the game's tonemap


def stage_point(values):
    return Y_UP_TO_Z_UP @ Vector(values)


def camera(scene, view):
    """A camera at the view's eye looking at its aim, its up the view's up, its angle across the picture."""
    data = bpy.data.cameras.new(view["name"])
    data.sensor_fit = "HORIZONTAL"
    data.angle = math.radians(view["fov"])
    # Far enough for the far city's mountains (tools/usd/far_city_stage.py: up to about 5 km off).
    data.clip_start, data.clip_end = 0.05, 8000.0
    item = bpy.data.objects.new(view["name"], data)
    scene.collection.objects.link(item)
    eye, aim, up = stage_point(view["eye"]), stage_point(view["aim"]), stage_point(view["up"])
    back = (eye - aim).normalized()
    across = up.cross(back).normalized()
    item.matrix_world = Matrix.Translation(eye) @ Matrix((across, back.cross(across), back)).transposed().to_4x4()
    scene.camera = item


def clear_eye(scene, view):
    """The view's first eye from which nothing stands between it and the aim (from 0.6 m out of the aim, clear of the
    character there); the last if none is clear."""
    eyes = view.get("eyes") or [view["eye"]]
    aim = stage_point(view["aim"])
    depsgraph = bpy.context.evaluated_depsgraph_get()
    for eye in eyes:
        towards = stage_point(eye) - aim
        hit = scene.ray_cast(depsgraph, aim + towards.normalized() * 0.6, towards.normalized(),
                             distance=towards.length - 0.6)[0]
        if not hit:
            return eye
    return eyes[-1]


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
        # A mesh prim's own attributes (a built structure piece's) come in on its mesh data, an Xform's on the object.
        for holder in (item, item.data) if item.data is not None else (item,):
            for key, value in holder.items():
                if key.endswith("layer") and "score" in key:
                    return int(value)
        item = item.parent
    return None


def over_room(objects, over):
    """The meshes wholly over a room and standing over its floor, a cutaway's `hide_over` ({"above": y, "low": [x, z],
    "high": [x, z]} in the stage's frame): its ceiling and whatever is built on top of it, kit layer or not."""
    to_stage = Y_UP_TO_Z_UP.inverted()
    found = []
    for item in objects:
        if item.type != "MESH":
            continue
        corners = [to_stage @ (item.matrix_world @ Vector(corner)) for corner in item.bound_box]
        if min(corner.y for corner in corners) < over["above"]:
            continue
        if (max(corner.x for corner in corners) > over["low"][0] and min(corner.x for corner in corners) < over["high"][0]
                and max(corner.z for corner in corners) > over["low"][1]
                and min(corner.z for corner in corners) < over["high"][1]):
            found.append(item)
    return found


def set_hidden(objects, hidden):
    for item in objects:
        item.hide_render = hidden


def stage_lights(stage):
    """The stage's own lights and sky (UsdLux, tools/usd/scene.py), read with the pxr library inside Blender:
    ([{type, matrix, colour, intensity, radius, angle, softness, shadows}], environment or None)."""
    from pxr import Usd, UsdGeom, UsdLux
    opened = Usd.Stage.Open(str(stage))
    cache = UsdGeom.XformCache()
    found, environment = [], None
    own_sky = opened.GetDefaultPrim().GetPath().AppendChild("Environment")
    for prim in opened.Traverse():
        if prim.IsA(UsdLux.DomeLight):
            if prim.GetPath() != own_sky:
                continue
            dome = UsdLux.DomeLight(prim)
            attribute = prim.GetAttribute
            environment = {
                "ambient": [value * dome.GetIntensityAttr().Get() for value in dome.GetColorAttr().Get()],
                "background": list(attribute("score:background").Get() or (0.0, 0.0, 0.0)),
                "exposure": float(attribute("score:exposure").Get() or 1.0),
                "ground_plane": bool(attribute("score:ground_plane").Get())}
            continue
        if not (prim.IsA(UsdLux.SphereLight) or prim.IsA(UsdLux.DistantLight)):
            continue
        light = UsdLux.SphereLight(prim) if prim.IsA(UsdLux.SphereLight) else UsdLux.DistantLight(prim)
        entry = {"type": "sphere" if prim.IsA(UsdLux.SphereLight) else "distant",
                 "matrix": [list(row) for row in cache.GetLocalToWorldTransform(prim)],
                 "colour": list(light.GetColorAttr().Get() or (1.0, 1.0, 1.0)),
                 "intensity": float(light.GetIntensityAttr().Get() or 0.0),
                 # A light the motion stage switches (tools/usd/motion.py): its intensity at each sample's time code.
                 "intensity_at": [[code, float(light.GetIntensityAttr().Get(code))]
                                  for code in light.GetIntensityAttr().GetTimeSamples()],
                 "shadows": bool(prim.GetAttribute("score:game:shadows").Get()) if prim.HasAttribute(
                     "score:game:shadows") else True}
        if entry["type"] == "sphere":
            entry["radius"] = float(light.GetRadiusAttr().Get() or 0.05)
            shaping = UsdLux.ShapingAPI(prim)
            if prim.HasAPI(UsdLux.ShapingAPI):
                entry["angle"] = float(shaping.GetShapingConeAngleAttr().Get())
                entry["softness"] = float(shaping.GetShapingConeSoftnessAttr().Get() or 0.0)
        else:
            entry["size"] = float(light.GetAngleAttr().Get() or 0.5)
        found.append(entry)
    return found, environment


def lit(scene, stage, fill=False):
    """The stage's own lights and sky, or the fixed sun and fill when it has no lights (one exported before its scene
    record); `fill` adds the weak fill to one that has them. Returns the stage's environment, or None."""
    lights, environment = stage_lights(stage)
    for number, entry in enumerate(lights):
        place_light(scene, number, entry)
    if environment is not None:
        stage_sky(scene, environment)
    else:
        black_sky(scene)
    if not lights:
        sun(scene, "sun", SUN_STRENGTH, SUN_ELEVATION, SUN_HEADING)
    if not lights or fill:
        sun(scene, "fill", FILL_STRENGTH, FILL_ELEVATION, SUN_HEADING + 180.0)
    return environment


def place_light(scene, number, entry):
    """One stage light in Blender, as Blender's own USD reader turns UsdLux intensities into its units (a sphere
    light's watts its intensity times pi, a distant light's strength its intensity times 4), its shadows as the game
    casts them."""
    usd = Matrix(entry["matrix"]).transposed()  # USD's matrices are row by row with the translation in the last row
    # The light's own frame is kept as USD gives it (a UsdLux light and a Blender light both shine down their own -z),
    # and only the world is turned onto Blender's z up; turning its own frame too made it shine down its own -y.
    world = Y_UP_TO_Z_UP.to_4x4() @ usd
    if entry["type"] == "distant":
        data = bpy.data.lights.new(f"stage_light_{number}", type="SUN")
        data.energy = entry["intensity"] * 4.0
        data.angle = math.radians(entry["size"])
    elif "angle" in entry:
        data = bpy.data.lights.new(f"stage_light_{number}", type="SPOT")
        data.energy = entry["intensity"] * math.pi
        data.spot_size = math.radians(2.0 * entry["angle"])
        data.spot_blend = min(1.0, entry.get("softness", 0.0))
        data.shadow_soft_size = entry["radius"]
    else:
        data = bpy.data.lights.new(f"stage_light_{number}", type="POINT")
        data.energy = entry["intensity"] * math.pi
        data.shadow_soft_size = entry["radius"]
    data.color = entry["colour"][:3]
    data.use_shadow = entry["shadows"]
    switched(data, entry)
    item = bpy.data.objects.new(f"stage_light_{number}", data)
    item.matrix_world = world
    scene.collection.objects.link(item)


def switched(data, entry):
    """A light the stage switches over its time (tools/usd/motion.py): its energy keyed at each sample, in the units
    place_light gives it, each key held until the next."""
    if not entry.get("intensity_at"):
        return
    per_intensity = 4.0 if data.type == "SUN" else math.pi
    for code, intensity in entry["intensity_at"]:
        data.energy = intensity * per_intensity
        data.keyframe_insert("energy", frame=code)
    animation = data.animation_data
    for curve in anim_utils.action_get_channelbag_for_slot(animation.action, animation.action_slot).fcurves:
        for key in curve.keyframe_points:
            key.interpolation = "CONSTANT"


def stage_sky(scene, environment):
    """The stage's sky: the ambient light from every side (its dome), the background the camera sees, the exposure
    (the game's multiplier as stops). The ambient light does not light the haze (the game's environment leaves its
    fog's ambient inject at nought, so only the sun and the lamps light it): a ray scattered in a haze body sees
    black."""
    world = bpy.data.worlds.new("stage_sky")
    world.use_nodes = True
    nodes, links = world.node_tree.nodes, world.node_tree.links
    background = next(node for node in nodes if node.type == "BACKGROUND")
    background.inputs["Color"].default_value = (*environment["ambient"][:3], 1.0)
    background.inputs["Strength"].default_value = 1.0
    seen = nodes.new("ShaderNodeBackground")
    seen.inputs["Color"].default_value = (*environment["background"][:3], 1.0)
    path = nodes.new("ShaderNodeLightPath")
    mix = nodes.new("ShaderNodeMixShader")
    output = next(node for node in nodes if node.type == "OUTPUT_WORLD")
    links.new(path.outputs["Is Camera Ray"], mix.inputs["Fac"])
    links.new(background.outputs["Background"], mix.inputs[1])
    links.new(seen.outputs["Background"], mix.inputs[2])
    unlit = nodes.new("ShaderNodeMixShader")  # its second shader left empty: black
    links.new(path.outputs["Is Volume Scatter Ray"], unlit.inputs["Fac"])
    links.new(mix.outputs["Shader"], unlit.inputs[1])
    links.new(unlit.outputs["Shader"], output.inputs["Surface"])
    scene.world = world
    scene.view_settings.exposure = math.log2(max(environment["exposure"], 1e-3))


def score_value(item, name):
    """An imported object's score:<name> (a mesh prim's own attributes come in on its mesh data, an Xform's on the
    object), or None."""
    holders = (item, item.data) if getattr(item, "data", None) is not None else (item,)
    for holder in holders:
        for key, value in holder.items():
            if key == f"score:{name}" or key.endswith(f"score:{name}") or key == f"score_{name}":
                return value
    return None


def haze_volumes(objects):
    """Every haze body of the stage filled with the game's fog: its colour as what the fog scatters, its density as
    how thick it is a metre, its forward throw as the scatter's anisotropy, and only as far from the eye as its
    `reach` (the game works its fog out that far from the camera and no further: volumetric_fog_length); its shell
    itself is not drawn."""
    for item in objects:
        density = score_value(item, "haze_density") if item.type == "MESH" else None
        if density is None:
            continue
        material = bpy.data.materials.new(f"haze_{item.name}")
        material.use_nodes = True
        nodes, links = material.node_tree.nodes, material.node_tree.links
        for node in list(nodes):
            nodes.remove(node)
        volume = nodes.new("ShaderNodeVolumePrincipled")
        volume.inputs["Color"].default_value = (*list(score_value(item, "haze_colour"))[:3], 1.0)
        volume.inputs["Density"].default_value = float(density)
        reach = score_value(item, "haze_reach")
        if reach:
            seen = nodes.new("ShaderNodeCameraData")
            within = nodes.new("ShaderNodeMath")
            within.operation = "LESS_THAN"
            within.inputs[1].default_value = float(reach)
            thickness = nodes.new("ShaderNodeMath")
            thickness.operation = "MULTIPLY"
            thickness.inputs[1].default_value = float(density)
            links.new(seen.outputs["View Distance"], within.inputs[0])
            links.new(within.outputs["Value"], thickness.inputs[0])
            links.new(thickness.outputs["Value"], volume.inputs["Density"])
        volume.inputs["Anisotropy"].default_value = float(score_value(item, "haze_forward") or 0.0)
        output = nodes.new("ShaderNodeOutputMaterial")
        links.new(volume.outputs["Volume"], output.inputs["Volume"])
        item.data.materials.clear()
        item.data.materials.append(material)
        item.visible_shadow = False


def mirror_material(item, along, down, tip, size):
    """The game's harbour on Blender's nodes: its own colour lit as it is, and over it what stands round it mirrored,
    `along` of it looking along the water and `down` looking straight down (the share eased by the square root of how
    far down the eye looks), its ripples `tip` steep and `size` metres across."""
    old = item.data.materials[0] if item.data.materials else None
    base = (0.0, 0.0, 0.0, 1.0)
    if old is not None and old.use_nodes:
        shader = next((node for node in old.node_tree.nodes if node.type == "BSDF_PRINCIPLED"), None)
        if shader is not None:
            base = tuple(shader.inputs["Base Color"].default_value)
    material = bpy.data.materials.new(f"mirror_{item.name}")
    material.use_nodes = True
    nodes, links = material.node_tree.nodes, material.node_tree.links
    for node in list(nodes):
        nodes.remove(node)
    diffuse = nodes.new("ShaderNodeBsdfDiffuse")
    diffuse.inputs["Color"].default_value = base
    coordinates = nodes.new("ShaderNodeTexCoord")
    scale = nodes.new("ShaderNodeVectorMath")
    scale.operation = "SCALE"
    scale.inputs["Scale"].default_value = 1.0 / size
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 1.0
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 1.0
    bump.inputs["Distance"].default_value = tip * size * RIPPLE_BUMP_SHARE
    links.new(coordinates.outputs["Object"], scale.inputs[0])
    links.new(scale.outputs["Vector"], noise.inputs["Vector"])
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    weight = nodes.new("ShaderNodeLayerWeight")
    weight.inputs["Blend"].default_value = 0.5
    looking_down = nodes.new("ShaderNodeMath")
    looking_down.operation = "SUBTRACT"
    looking_down.inputs[0].default_value = 1.0
    links.new(weight.outputs["Facing"], looking_down.inputs[1])
    root = nodes.new("ShaderNodeMath")
    root.operation = "SQRT"
    links.new(looking_down.outputs["Value"], root.inputs[0])
    share = nodes.new("ShaderNodeMapRange")
    share.inputs["To Min"].default_value = along
    share.inputs["To Max"].default_value = down
    links.new(root.outputs["Value"], share.inputs["Value"])
    tint = nodes.new("ShaderNodeCombineColor")
    for channel in ("Red", "Green", "Blue"):
        links.new(share.outputs["Result"], tint.inputs[channel])
    glossy = nodes.new("ShaderNodeBsdfGlossy")
    glossy.inputs["Roughness"].default_value = 0.0
    links.new(tint.outputs["Color"], glossy.inputs["Color"])
    links.new(bump.outputs["Normal"], glossy.inputs["Normal"])
    added = nodes.new("ShaderNodeAddShader")
    links.new(diffuse.outputs["BSDF"], added.inputs[0])
    links.new(glossy.outputs["BSDF"], added.inputs[1])
    output = nodes.new("ShaderNodeOutputMaterial")
    links.new(added.outputs["Shader"], output.inputs["Surface"])
    item.data.materials.clear()
    item.data.materials.append(material)


def water_mirrors(objects):
    """Every water surface the stage gives a mirror (score:mirror_*) drawn as the game's harbour mirrors."""
    for item in objects:
        along = score_value(item, "mirror_along") if item.type == "MESH" else None
        if along is not None:
            mirror_material(item, float(along), float(score_value(item, "mirror_down")),
                            float(score_value(item, "mirror_ripple_tip")), float(score_value(item, "mirror_ripple_size")))


# --- the effects (tools/usd/effects.py) ---------------------------------------------------------------------------

def effect_points(stage, objects):
    """The stage's baked effects (UsdGeomPoints with score:kind "effect", looped from their clips), each with the
    point cloud Blender brought it in as: Blender's reader leaves displayOpacity out, so each is drawn here instead,
    frame by frame (draw_effects), its own reader taken off. Each comes as (point cloud, Points prim, its stage)."""
    from pxr import Usd, UsdGeom
    opened = Usd.Stage.Open(str(stage))
    clouds = {item.name: item for item in objects if item.type == "POINTCLOUD"}
    found = []
    for prim in opened.Traverse():
        if not prim.IsA(UsdGeom.Points) or prim.GetAttribute("score:kind").Get() != "effect":
            continue
        cloud = clouds.get(prim.GetName())
        if cloud is None:
            raise RuntimeError(f"Blender did not bring in the effect {prim.GetPath()}")
        for modifier in [modifier for modifier in cloud.modifiers if modifier.type == "MESH_SEQUENCE_CACHE"]:
            cloud.modifiers.remove(modifier)
        emitter = prim.GetParent()
        cloud.data.materials.clear()
        cloud.data.materials.append(effect_material(prim.GetName(), prim.GetAttribute("score:effect:look").Get(),
                                                    emitter.GetAttribute("score:effect:near_fade").Get(),
                                                    UsdGeom.PrimvarsAPI(prim).GetPrimvar("displayColor").Get()[0]))
        found.append((cloud, UsdGeom.Points(prim), opened))  # the stage kept open while its prims are read
    return found


def draw_effects(effects, frame):
    """Each effect's particles as its stage holds them at a frame: spots, sizes and thickness."""
    import numpy
    from pxr import UsdGeom
    for cloud, points, _ in effects:
        spots = numpy.asarray(points.GetPointsAttr().Get(frame), dtype=numpy.float32)
        if len(spots) != len(cloud.data.points):
            raise RuntimeError(f"{cloud.name} holds {len(cloud.data.points)} points, its stage {len(spots)} at {frame}")
        widths = numpy.asarray(points.GetWidthsAttr().Get(frame), dtype=numpy.float32)
        opacity = numpy.asarray(UsdGeom.PrimvarsAPI(points).GetPrimvar("displayOpacity").Get(frame), dtype=numpy.float32)
        cloud.data.attributes["position"].data.foreach_set("vector", spots.ravel())
        cloud.data.attributes["radius"].data.foreach_set("value", widths / 2.0)
        thickness = cloud.data.attributes.get("opacity") or cloud.data.attributes.new("opacity", "FLOAT", "POINT")
        thickness.data.foreach_set("value", opacity)
        cloud.data.update_tag()


def effect_material(name, look, near_fade, colour):
    """An effect's particles as the game draws them, each a sphere: a speck (flat, unlit, solid to 0.4 of its radius
    and fading to its edge) or a puff (lit, thickest in its middle as (1 - r^2)^1.5, which on a sphere seen from any
    side is the facing share cubed, gone within near_fade metres of the eye), see-through by its `opacity`."""
    material = bpy.data.materials.new(f"effect_{name}")
    material.use_nodes = True
    nodes, links = material.node_tree.nodes, material.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    thickness = nodes.new("ShaderNodeAttribute")
    thickness.attribute_type = "GEOMETRY"
    thickness.attribute_name = "opacity"
    geometry = nodes.new("ShaderNodeNewGeometry")
    facing = nodes.new("ShaderNodeVectorMath")
    facing.operation = "DOT_PRODUCT"
    links.new(geometry.outputs["Normal"], facing.inputs[0])
    links.new(geometry.outputs["Incoming"], facing.inputs[1])
    straight = nodes.new("ShaderNodeMath")
    straight.operation = "ABSOLUTE"
    links.new(facing.outputs["Value"], straight.inputs[0])
    shape = nodes.new("ShaderNodeMath")
    if look == "puff":
        shape.operation = "POWER"
        shape.inputs[1].default_value = 3.0
        links.new(straight.outputs["Value"], shape.inputs[0])
        surface = nodes.new("ShaderNodeBsdfDiffuse")
        surface.inputs["Color"].default_value = (*colour, 1.0)
    else:  # out from the middle r = sqrt(1 - f^2); solid to 0.4, then down to nothing at the edge
        across = nodes.new("ShaderNodeMath")
        across.operation = "MULTIPLY"
        links.new(straight.outputs["Value"], across.inputs[0])
        links.new(straight.outputs["Value"], across.inputs[1])
        out = nodes.new("ShaderNodeMath")
        out.operation = "SQRT"
        less = nodes.new("ShaderNodeMath")
        less.operation = "SUBTRACT"
        less.inputs[0].default_value = 1.0
        links.new(across.outputs["Value"], less.inputs[1])
        links.new(less.outputs["Value"], out.inputs[0])
        shape = nodes.new("ShaderNodeMapRange")
        shape.inputs["From Min"].default_value, shape.inputs["From Max"].default_value = 1.0, 0.4
        links.new(out.outputs["Value"], shape.inputs["Value"])
        surface = nodes.new("ShaderNodeEmission")
        surface.inputs["Color"].default_value = (*colour, 1.0)
    share = nodes.new("ShaderNodeMath")
    share.operation = "MULTIPLY"
    links.new(thickness.outputs["Fac"], share.inputs[0])
    links.new(shape.outputs[0], share.inputs[1])
    if look == "puff" and near_fade is not None and near_fade[1] > 0:
        eye = nodes.new("ShaderNodeCameraData")
        near = nodes.new("ShaderNodeMapRange")
        near.interpolation_type = "SMOOTHSTEP"
        near.inputs["From Min"].default_value, near.inputs["From Max"].default_value = near_fade[0], near_fade[1]
        links.new(eye.outputs["View Distance"], near.inputs["Value"])
        faded = nodes.new("ShaderNodeMath")
        faded.operation = "MULTIPLY"
        links.new(share.outputs["Value"], faded.inputs[0])
        links.new(near.outputs["Result"], faded.inputs[1])
        share = faded
    clear = nodes.new("ShaderNodeBsdfTransparent")
    mix = nodes.new("ShaderNodeMixShader")
    links.new(share.outputs["Value"], mix.inputs["Fac"])
    links.new(clear.outputs["BSDF"], mix.inputs[1])
    links.new(surface.outputs[0], mix.inputs[2])
    links.new(mix.outputs["Shader"], output.inputs["Surface"])
    return material


def textured(item):
    """Whether an object is drawn from a picture (a made model's baked maps): the game inks those thinner."""
    return item.type == "MESH" and any(
        slot.material is not None and slot.material.use_nodes
        and any(node.type == "TEX_IMAGE" for node in slot.material.node_tree.nodes) for slot in item.material_slots)


def pass_render(scene, path):
    """The view rendered once more in Cycles at one sample with its distance and object index kept, to a multilayer
    EXR; the render settings put back after."""
    settings = scene.render.image_settings
    engine, samples, denoise = scene.render.engine, scene.cycles.samples, scene.cycles.use_denoising
    kept = (settings.media_type, settings.file_format, settings.color_mode, settings.color_depth)
    if engine != "CYCLES":
        scene.render.engine = "CYCLES"
        scene.cycles.device = "CPU"
    scene.cycles.samples, scene.cycles.use_denoising = 1, False
    layer = scene.view_layers[0]
    layer.use_pass_z = layer.use_pass_object_index = layer.use_pass_normal = True
    settings.media_type = "MULTI_LAYER_IMAGE"  # Blender 5: a multilayer EXR is a media type of its own
    settings.file_format = "OPEN_EXR_MULTILAYER"
    settings.color_depth = "32"
    render(scene, path, transparent=False)
    scene.render.engine, scene.cycles.samples, scene.cycles.use_denoising = engine, samples, denoise
    settings.media_type, settings.file_format, settings.color_mode, settings.color_depth = kept


def exr_channels(path):
    """A multilayer EXR's distance, normal and object index (top row first) as numpy arrays, from whichever of its
    parts holds each."""
    import numpy
    import OpenImageIO
    found = {}
    parts = OpenImageIO.ImageBuf(str(path)).nsubimages
    for part in range(parts):
        held = OpenImageIO.ImageBuf(str(path), part, 0)
        pixels = numpy.asarray(held.get_pixels(OpenImageIO.FLOAT))
        for index, name in enumerate(held.spec().channelnames):
            found[name] = pixels[:, :, index]

    def channel(part, axis):
        return next(values for name, values in found.items() if part in name and name.endswith(axis))

    normal = numpy.dstack([channel("Normal", axis) for axis in (".X", ".Y", ".Z")])
    return channel("Depth", ".Z"), normal, channel("Index", ".X")


def smoothstep(low, high, value):
    import numpy
    share = numpy.clip((value - low) / (high - low), 0.0, 1.0)
    return share * share * (3.0 - 2.0 * share)


def shape_normals(depth, fov):
    """Which way the drawn shape faces at each pixel, from the depth alone (the game's shape_facing): each slope taken
    toward the nearer-level neighbour, turned to face the eye."""
    import numpy
    tall, wide = depth.shape
    focal = (wide / 2.0) / math.tan(math.radians(fov) / 2.0)
    across, down = numpy.meshgrid((numpy.arange(wide) + 0.5 - wide / 2.0) / focal,
                                  (numpy.arange(tall) + 0.5 - tall / 2.0) / focal)
    points = numpy.dstack([across * depth, down * depth, depth])
    padded = numpy.pad(points, ((1, 1), (1, 1), (0, 0)), mode="edge")
    right = padded[1:-1, 2:] - points
    left = points - padded[1:-1, :-2]
    below = padded[2:, 1:-1] - points
    above = points - padded[:-2, 1:-1]
    sideways = numpy.where((numpy.abs(right[..., 2]) < numpy.abs(left[..., 2]))[..., None], right, left)
    downward = numpy.where((numpy.abs(below[..., 2]) < numpy.abs(above[..., 2]))[..., None], below, above)
    normal = numpy.cross(downward, sideways)
    normal /= numpy.maximum(numpy.linalg.norm(normal, axis=2, keepdims=True), 1e-9)
    facing_away = (normal * points).sum(axis=2) > 0.0
    return numpy.where(facing_away[..., None], -normal, normal)


def at_offset(values, way, reach):
    """`values` read `reach` pixels (each pixel's own) along `way` (across, down) from every pixel, the nearest
    pixel's, held at the picture's edge."""
    import numpy
    tall, wide = values.shape[:2]
    rows, columns = numpy.mgrid[0:tall, 0:wide]
    rows = numpy.clip(numpy.rint(rows + way[1] * reach), 0, tall - 1).astype(int)
    columns = numpy.clip(numpy.rint(columns + way[0] * reach), 0, wide - 1).astype(int)
    return values[rows, columns]


def neighbours(depth, normal, reach):
    """What the neighbours `reach` pixels out on every side say about each pixel (the game's `neighbours`): how far it
    stands in front of them as a share of its closeness, how far it turns from the nearer-or-level ones, and whether
    some pair of them both fall away behind it."""
    import numpy
    near_side = numpy.zeros(depth.shape)
    crease = numpy.zeros(depth.shape)
    narrow = numpy.zeros(depth.shape, dtype=bool)
    closeness = 1.0 / depth
    for pair in range(0, 8, 2):
        out_depth, back_depth = (at_offset(depth, INK_REACH[pair + side], reach) for side in (0, 1))
        either_side = 0.5 * (1.0 / out_depth + 1.0 / back_depth)
        near_side = numpy.maximum(near_side, (closeness - either_side) / closeness)
        falls_away = depth * (1.0 + INK_DEPTH_BREAK)
        narrow |= (out_depth >= falls_away) & (back_depth >= falls_away)
        for side, other in ((0, out_depth), (1, back_depth)):
            turned = 1.0 - (normal * at_offset(normal, INK_REACH[pair + side], reach)).sum(axis=2)
            crease = numpy.maximum(crease, turned * (other >= depth * INK_LEVEL))
    return near_side, crease, narrow


def shape_corner(shapes, reach):
    """How surely the shape itself turns a corner at each pixel (the game's shape_corner): the faces a span out on
    either side turn apart by a corner's turn and each runs on flat as far again."""
    import numpy
    corner = numpy.zeros(shapes.shape[:2])
    span = numpy.maximum(reach * INK_SPAN, INK_SPAN_PX)
    for pair in range(0, 8, 2):
        way, back = INK_REACH[pair], INK_REACH[pair + 1]
        one, other = at_offset(shapes, way, span), at_offset(shapes, back, span)
        one_beyond, other_beyond = at_offset(shapes, way, span * 2.0), at_offset(shapes, back, span * 2.0)
        flat_sides = smoothstep(INK_FLAT_SIDE * 0.9, INK_FLAT_SIDE, numpy.minimum(
            (one * one_beyond).sum(axis=2), (other * other_beyond).sum(axis=2)))
        turn = smoothstep(INK_SHAPE_TURN * 0.75, INK_SHAPE_TURN, 1.0 - (one * other).sum(axis=2))
        corner = numpy.maximum(corner, turn * flat_sides)
    return corner


def ink_lines(depth, normal, index, fov):
    """How strongly each pixel is inked, 0 to 1, by the game's rule (ink_edges.gdshader's fragment): `index` 1 marks a
    textured model's pixels."""
    import numpy
    textured_here = index > 0.5
    to_pixels = depth.shape[0] / 1080.0
    thin = smoothstep(INK_THIN[0], INK_THIN[1], depth)
    full = numpy.where(textured_here, INK_TEXTURED_PX, INK_LINE_PX) * to_pixels
    reach = full * (1.0 - thin) + thin
    near_side, crease, narrow = neighbours(depth, normal, reach)
    small = numpy.maximum(reach * INK_SMALL_PART_SHARE, 1.0)
    again = narrow & (small < reach)
    if again.any():
        small_near, small_crease, _ = neighbours(depth, normal, numpy.where(again, small, reach))
        near_side = numpy.where(again, small_near, near_side)
        crease = numpy.where(again, small_crease, crease)
        reach = numpy.where(again, small, reach)
    depth_edge = smoothstep(INK_DEPTH_BREAK * 0.35, INK_DEPTH_BREAK * 0.5, near_side)
    crease_edge = smoothstep(INK_CREASE_BREAK * 0.75, INK_CREASE_BREAK, crease)
    if textured_here.any():
        crease_edge = numpy.where(textured_here, crease_edge * shape_corner(shape_normals(depth, fov), reach),
                                  crease_edge)
    return numpy.maximum(depth_edge, crease_edge) * (1.0 - smoothstep(INK_FADE[0], INK_FADE[1], depth))


def ink_view(scene, view, out, objects, sky):
    """The view's look with the game's ink lines laid over it: <name>-ink.png beside <name>-look.png. The haze is
    left out of the pass render, where it would scatter the distances (the game's ink reads the surfaces' depth)."""
    import numpy
    import OpenImageIO
    for item in objects:
        item.pass_index = 1 if textured(item) else 0
    passes = out / f"{view['name']}-passes.exr"
    set_hidden(sky, True)
    pass_render(scene, passes)
    set_hidden(sky, False)
    depth, normal, index = exr_channels(passes)
    passes.unlink()
    look = OpenImageIO.ImageBuf(str(out / f"{view['name']}-look.png"))
    pixels = numpy.asarray(look.get_pixels(OpenImageIO.FLOAT))
    share = ink_lines(depth, normal, index, float(view["fov"]))[..., None]
    pixels[..., :3] = pixels[..., :3] * (1.0 - share) + numpy.asarray(INK_COLOUR) * share
    inked = OpenImageIO.ImageBuf(OpenImageIO.ImageSpec(pixels.shape[1], pixels.shape[0], pixels.shape[2],
                                                       OpenImageIO.UINT8))
    inked.set_pixels(OpenImageIO.ROI(), numpy.ascontiguousarray(pixels, dtype=numpy.float32))
    if not inked.write(str(out / f"{view['name']}-ink.png")):
        raise RuntimeError(f"the ink view {view['name']} was not written: {inked.geterror()}")


def main():
    stage, views, out = arguments()
    out.mkdir(parents=True, exist_ok=True)
    scene = empty_scene()
    objects = import_stage(stage)
    (out / "report.json").write_text(json.dumps(import_report(stage, objects), indent=1))
    objects = [item for item in objects if not item.hide_render]  # what the stage makes invisible stays so
    effects = effect_points(stage, objects)
    renderer(scene, views["size"])
    if effects and scene.render.engine == "CYCLES":  # thin particles one behind another: Cycles stops at 8 by default
        scene.cycles.transparent_max_bounces = EFFECT_BOUNCES
    environment = lit(scene, stage, views.get("fill"))
    plane = stage_ground(objects)
    if plane is None and (environment is None or environment["ground_plane"]):
        plane = ground(scene)
    elif plane is not None:
        objects = [item for item in objects if item is not plane]
    if plane is None:  # a room: its own floor is its ground; the masks are drawn with nothing to hide
        plane = bpy.data.objects.new("no_ground", None)
    if views.get("plain"):
        plain(objects)
    else:
        haze_volumes(objects)
        water_mirrors(objects)
    lamps(scene, views.get("lights", []))
    layers = {item.name: layer_of(item) for item in objects}
    sky = [item for item in objects if score_value(item, "kind") in ("haze", "stars", "sky", "dust")]
    sky += [cloud for cloud, _, _ in effects]  # effects are air, as the dust is, not the place's objects
    for view in views["views"]:
        scene.frame_set(int(view.get("frame", scene.frame_current)))
        draw_effects(effects, scene.frame_current)
        drawn = {cloud.name for cloud, _, _ in effects}
        crowds = [item for item in objects if item.type == "POINTCLOUD" and item.name not in drawn] \
            if view.get("hide_crowds") else []
        for item in crowds:
            item.hide_render = item.hide_viewport = True
        if "eyes" in view:
            view = dict(view, eye=clear_eye(scene, view))
        camera(scene, view)
        plane.hide_render = False
        hidden = [item for item in objects if layers[item.name] in view.get("hide_layers", [])]
        hidden += over_room(objects, view["hide_over"]) if "hide_over" in view else []
        set_hidden(hidden, True)
        render(scene, out / f"{view['name']}-look.png", transparent=False)
        if view.get("ink"):
            ink_view(scene, view, out, objects, sky)
        set_hidden(hidden, False)
        for item in crowds:
            item.hide_render = item.hide_viewport = False
        if view.get("look_only"):
            continue
        plane.hide_render = True
        set_hidden(sky, True)  # the haze and the stars are air and sky, not the place's objects
        render(scene, out / f"{view['name']}-mask.png", transparent=True)
        set_hidden(sky, False)
        plane.hide_render = False
        set_hidden(objects, True)
        render(scene, out / f"{view['name']}-ground.png", transparent=True)
        set_hidden(objects, False)
    print("usd_views: wrote", out)


if __name__ == "__main__":  # annotate_stage.py imports these helpers
    main()
