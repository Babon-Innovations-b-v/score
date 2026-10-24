"""Runs inside Blender (`../blender/session.py batch`, or on a rented card through `../cloud/blender_cloud.py`):
demo K9's "Built in layers" in real geometry. One place's accepted assembly is imported as composed, and every layer of
its stack gets a copy of what it specifies (the prims it defines or authors values on, three or more deep: a layer
that only nests into others claims nothing; a claimed prim with nothing to draw, a lamp or a sound, is a small glowing
ball where it stands), on its own plate the room's size. Starting from the composed place, the layers lift apart one
after another, bottom first, to their own levels, while the camera orbits slowly and keeps the stack in view. The
room's roof (score:layer 2, the Structure's shell_roof) and the sky's haze are left out, so the stack is seen into, and
the ground layer's meshes are cut to the room and a margin round it.

    blender -b -P tools/review/layers_lift.py -- <stage.usda> <out folder> [--size 1280 720] [--seconds 12]
        [--frames <first> <last>] [--samples 16]

Writes <out>/frame_<nnnn>.png per frame and <out>/labels_<first>_<last>.json: the clip's rate and size, each layer's name, prim
count and colour, and per frame each layer's lift (0..1) and where its label goes on screen (pixels from top left),
for tools/review/ending.py's `layers3d` to draw the labels over.
"""
import argparse
import json
import math
import pathlib
import re
import sys

import bmesh
import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Matrix, Vector

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "blender" / "inside"))
import usd_views  # noqa: E402  (import_stage, renderer, the Y-up turn)

RATE = 24
LIFT_START = 0.8  # seconds of the composed place before the first layer lifts
HOLD = 2.4  # seconds of the whole stack apart at the end
GROUND_MARGIN = 1.0  # metres of the ground layer kept round the room
LAYER_GAP = 0.9  # metres between one layer's top and the next plate
BACK = (17 / 255, 18 / 255, 21 / 255)
DROPPED = ("/Sky", "/Outside/ball")  # under the place's root: the haze and the sky ball hide the stack
# The layer's colour, as ending.py's diagram draws it; a layer not named is grey.
COLOURS = {"ground": (122, 104, 84), "base": (150, 160, 172), "settle": (120, 170, 140), "machines": (210, 150, 90),
           "crops": (120, 190, 90), "light": (250, 214, 110), "motion": (120, 170, 240),
           "motion_keys": (150, 130, 230), "effects": (240, 120, 110), "sound": (110, 210, 210),
           "characters": (235, 150, 200), "edit": (200, 200, 200)}


def arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("stage")
    parser.add_argument("out")
    parser.add_argument("--size", type=int, nargs=2, default=(1280, 720))
    parser.add_argument("--seconds", type=float, default=12.0)
    parser.add_argument("--frames", type=int, nargs=2)
    parser.add_argument("--samples", type=int, default=16)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])


def layer_claims(stage_file):
    """The root layer's sublayers bottom first, as [(name, claimed prim paths, prim count)]."""
    from pxr import Sdf
    root = Sdf.Layer.FindOrOpen(str(stage_file))
    stack = []
    for path in reversed(root.subLayerPaths):
        layer = Sdf.Layer.FindOrOpen(root.ComputeAbsolutePath(path))
        specs = []
        layer.Traverse(Sdf.Path.absoluteRootPath,
                       lambda spec_path: specs.append(layer.GetPrimAtPath(spec_path)) if spec_path.IsPrimPath() else None)
        claimed = [str(spec.path) for spec in specs if spec.path.pathElementCount >= 3 and (
            spec.specifier == Sdf.SpecifierDef or len(spec.properties) or spec.referenceList.prependedItems
            or spec.referenceList.explicitItems)]
        stack.append((pathlib.Path(path).stem, claimed, len(specs)))
    return stack


def prim_path(item):
    """An imported object's prim path, from its parents' names (Blender adds .001 to a repeated name)."""
    names = []
    while item is not None:
        names.append(re.sub(r"\.\d{3}$", "", item.name))
        item = item.parent
    return "/" + "/".join(reversed(names))


def claims(path, claimed):
    return any(path == claim or path.startswith(claim + "/") for claim in claimed)


def dropped(path, root):
    return any(path == root + part or path.startswith(root + part + "/") for part in DROPPED)


def roof(item):
    """A room's roof: the kit's draw layer 2, or the Structure's shell_roof."""
    return usd_views.layer_of(item) == 2 or "/Structure/shell_roof" in prim_path(item)


def room_bounds(stage_file, root):
    """The place's own objects' box in Blender's frame (z up): (low, high) Vectors."""
    from pxr import Usd, UsdGeom
    stage = Usd.Stage.Open(str(stage_file))
    box = UsdGeom.BBoxCache(0, ["default", "render"]).ComputeWorldBound(
        stage.GetPrimAtPath(root + "/Objects")).ComputeAlignedRange()
    corners = [usd_views.stage_point((x, y, z)) for x in (box.GetMin()[0], box.GetMax()[0])
               for y in (box.GetMin()[1], box.GetMax()[1]) for z in (box.GetMin()[2], box.GetMax()[2])]
    return (Vector([min(corner[axis] for corner in corners) for axis in range(3)]),
            Vector([max(corner[axis] for corner in corners) for axis in range(3)]))


def marker_spots(stage_file, claimed):
    """Where each claimed prim with a transform stands (Blender's frame), for the claims nothing was drawn for."""
    from pxr import Usd, UsdGeom
    stage = Usd.Stage.Open(str(stage_file))
    cache = UsdGeom.XformCache(0)
    spots = []
    for claim in claimed:
        prim = stage.GetPrimAtPath(claim)
        if not prim:
            continue
        for found in Usd.PrimRange(prim):
            if found.IsA(UsdGeom.Xformable):
                spots.append(usd_views.stage_point(tuple(cache.GetLocalToWorldTransform(found).ExtractTranslation())))
    return spots[:200]


def glow_material(name, colour, strength):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    nodes.clear()
    emission = nodes.new("ShaderNodeEmission")
    emission.inputs["Color"].default_value = (*[channel / 255 for channel in colour], 1.0)
    emission.inputs["Strength"].default_value = strength
    output = nodes.new("ShaderNodeOutputMaterial")
    material.node_tree.links.new(emission.outputs[0], output.inputs[0])
    return material


def plate(name, low, high, colour, holder, collection):
    """A layer's plate: the room's outline as a glowing frame at the holder's level."""
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([(low.x, low.y, low.z), (high.x, low.y, low.z), (high.x, high.y, low.z), (low.x, high.y, low.z)],
                     [], [(0, 1, 2, 3)])
    mesh.materials.append(glow_material(name, colour, 2.0))
    item = bpy.data.objects.new(name, mesh)
    item.modifiers.new("frame", "WIREFRAME").thickness = 0.08
    item.parent = holder
    collection.objects.link(item)


def markers(name, spots, colour, holder, collection):
    material = glow_material(name + "_glow", colour, 6.0)
    for index, spot in enumerate(spots):
        mesh = bpy.data.meshes.new(f"{name}_{index}")
        sphere = bmesh.new()
        bmesh.ops.create_uvsphere(sphere, u_segments=12, v_segments=8, radius=0.22)
        sphere.to_mesh(mesh)
        sphere.free()
        mesh.materials.append(material)
        item = bpy.data.objects.new(f"{name}_{index}", mesh)
        item.matrix_basis = Matrix.Translation(spot)
        item.parent = holder
        collection.objects.link(item)


def crop(item, low, high):
    """Leave out the faces of a ground mesh outside the room and its margin."""
    if item.type != "MESH":
        return
    lower, upper = low - Vector((GROUND_MARGIN,) * 3), high + Vector((GROUND_MARGIN,) * 3)
    mesh = item.data.copy()
    item.data = mesh
    edit = bmesh.new()
    edit.from_mesh(mesh)
    world = item.matrix_world
    outside = [face for face in edit.faces
               if not all(lower.x <= (world @ vertex.co).x <= upper.x and lower.y <= (world @ vertex.co).y <= upper.y
                          for vertex in face.verts)]
    bmesh.ops.delete(edit, geom=outside, context="FACES")
    edit.to_mesh(mesh)
    edit.free()


def build_layers(stage_file, objects, low, high):
    """Per layer, bottom first: {name, holder (an empty its copies hang from), prims, colour, height}."""
    drawn = [item for item in objects if item.type in ("MESH", "POINTCLOUD", "CURVES")]
    root = "/" + prim_path(drawn[0]).split("/")[1]
    layers = []
    for name, claimed, prims in layer_claims(stage_file):
        colour = COLOURS.get(name, (170, 170, 170))
        collection = bpy.data.collections.new("layer_" + name)
        bpy.context.scene.collection.children.link(collection)
        holder = bpy.data.objects.new("holder_" + name, None)
        collection.objects.link(holder)
        tops, found = [], set()
        for item in drawn:
            path = prim_path(item)
            if not claims(path, claimed):
                continue
            # a claim whose drawing is left out (the roof) gets no ball either
            found.update(claim for claim in claimed if path == claim or path.startswith(claim + "/"))
            if dropped(path, root) or roof(item):
                continue
            copy = item.copy()
            copy.animation_data_clear()
            copy.parent = holder
            copy.matrix_parent_inverse = Matrix.Identity(4)
            copy.matrix_basis = item.matrix_world.copy()
            collection.objects.link(copy)
            if name == "ground":
                crop(copy, low, high)
            tops.append(max((copy.matrix_basis @ Vector(corner)).z for corner in copy.bound_box))
        bare = [claim for claim in claimed if claim not in found and not dropped(claim, root)]
        spots = [spot for spot in marker_spots(stage_file, bare)
                 if low.x - 1 <= spot.x <= high.x + 1 and low.y - 1 <= spot.y <= high.y + 1]
        markers(name, spots, colour, holder, collection)
        tops += [spot.z for spot in spots]
        plate("plate_" + name, low, high, colour, holder, collection)
        print(f"layers_lift: {name}: {len(tops) - len(spots)} drawn copies, {len(spots)} markers", flush=True)
        height = min(max(tops, default=0.0), high.z) - low.z
        layers.append({"name": name, "holder": holder, "prims": prims, "colour": colour,
                       "height": max(height, 0.0)})
    return layers


def eased(value):
    value = min(max(value, 0.0), 1.0)
    return value * value * (3 - 2 * value)


def levels(layers):
    """Each layer's height once lifted: on the one below it, its top plus the gap."""
    found, level = [], 0.0
    for index, layer in enumerate(layers):
        found.append(level)
        level += layer["height"] + LAYER_GAP
    return found


def lifts(moment, count, seconds):
    step = (seconds - LIFT_START - HOLD) / max(count - 1, 1)
    return [1.0 if index == 0 else eased((moment - LIFT_START - (index - 1) * step) / (step * 0.9))
            for index in range(count)]


def place_camera(camera, low, high, window, moment, seconds):
    """A slow orbit round the stack, from high over the composed place down to low beside the lifted stack, looking
    at the middle of `window` (the stack's heights now) from far enough to hold it and the room's width."""
    middle = Vector(((low.x + high.x) / 2, (low.y + high.y) / 2, sum(window) / 2))
    reach = max((high.xy - low.xy).length * 0.55, (window[1] - window[0]) * 0.5)
    distance = reach / math.tan(math.radians(36) / 2)
    progress = eased(moment / seconds)
    heading = math.radians(-120 + 38 * progress)
    elevation = math.radians(34 - 12 * progress)
    camera.location = middle + distance * Vector((math.cos(elevation) * math.cos(heading),
                                                  math.cos(elevation) * math.sin(heading), math.sin(elevation)))
    camera.rotation_euler = (middle - camera.location).to_track_quat("-Z", "Y").to_euler()


def lighting(scene):
    """A high sun with a weak fill and grey sky light; the camera sees the clip's background."""
    usd_views.sun(scene, "key", 3.0, 55, 30)
    usd_views.sun(scene, "fill", 0.6, 30, 210)
    world = bpy.data.worlds.new("sky")
    world.use_nodes = True
    nodes, links = world.node_tree.nodes, world.node_tree.links
    lit = next(node for node in nodes if node.type == "BACKGROUND")
    lit.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)
    lit.inputs["Strength"].default_value = 0.35
    seen = nodes.new("ShaderNodeBackground")
    seen.inputs["Color"].default_value = (*[channel ** 2.2 for channel in BACK], 1.0)
    path = nodes.new("ShaderNodeLightPath")
    mix = nodes.new("ShaderNodeMixShader")
    links.new(path.outputs["Is Camera Ray"], mix.inputs[0])
    links.new(lit.outputs[0], mix.inputs[1])
    links.new(seen.outputs[0], mix.inputs[2])
    links.new(mix.outputs[0], next(node for node in nodes if node.type == "OUTPUT_WORLD").inputs[0])
    scene.world = world


def label_spot(scene, camera, layer, low, high, size):
    """Where a layer's label goes: the screen point of its plate's corner furthest right, in pixels."""
    corners = [Vector((x, y, layer["holder"].location.z + low.z)) for x in (low.x, high.x) for y in (low.y, high.y)]
    seen = [world_to_camera_view(scene, camera, corner) for corner in corners]
    right = max(seen, key=lambda point: point.x)
    return [round(right.x * size[0]), round((1 - right.y) * size[1])]


def main():
    options = arguments()
    out = pathlib.Path(options.out)
    out.mkdir(parents=True, exist_ok=True)
    scene = usd_views.empty_scene()
    objects = usd_views.import_stage(options.stage)
    scene.frame_set(0)
    drawn = [item for item in objects if item.type in ("MESH", "POINTCLOUD", "CURVES")]
    root = "/" + prim_path(drawn[0]).split("/")[1]
    low, high = room_bounds(options.stage, root)
    layers = build_layers(options.stage, objects, low, high)
    for item in objects:
        item.hide_render = True
    lighting(scene)
    camera = bpy.data.objects.new("camera", bpy.data.cameras.new("camera"))
    camera.data.angle = math.radians(36 * options.size[0] / options.size[1])
    camera.data.clip_end = 2000
    scene.collection.objects.link(camera)
    scene.camera = camera
    usd_views.renderer(scene, options.size)
    if scene.render.engine == "CYCLES":
        scene.cycles.samples = options.samples
        scene.render.use_persistent_data = True
    scene.render.film_transparent = False
    scene.render.image_settings.color_mode = "RGB"
    count = round(options.seconds * RATE)
    first, last = options.frames or (0, count - 1)
    heights = levels(layers)
    frames = []
    for number in range(first, last + 1):
        moment = number / RATE
        lifted = lifts(moment, len(layers), options.seconds)
        for layer, level, lift in zip(layers, heights, lifted):
            layer["holder"].location.z = level * lift if layer is not layers[0] else 0.0
        top = max(layer["holder"].location.z + layer["height"] for layer in layers) + low.z
        place_camera(camera, low, high, (low.z, top), moment, options.seconds)
        bpy.context.view_layer.update()
        scene.render.filepath = str(out / f"frame_{number:04d}.png")
        bpy.ops.render.render(write_still=True)
        frames.append({"frame": number, "layers": [
            {"lift": round(lift, 4), "at": label_spot(scene, camera, layer, low, high, options.size)}
            for layer, lift in zip(layers, lifted)]})
        print(f"layers_lift: frame {number}", flush=True)
    labels = {"rate": RATE, "size": list(options.size), "seconds": options.seconds,
              "layers": [{"name": layer["name"], "prims": layer["prims"], "colour": layer["colour"]}
                         for layer in layers], "frames": frames}
    (out / f"labels_{first:04d}_{last:04d}.json").write_text(json.dumps(labels))
    print("layers_lift: wrote", out)


if __name__ == "__main__":
    main()
