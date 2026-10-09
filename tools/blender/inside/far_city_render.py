"""Draw the far city's strips (tools/usd/far_city.py) at night: its made towers laid as the plan lays them, the code-built
mountains and quay behind and under them, each backdrop arc's strip from the ring's middle by a central cylindrical
camera, the sky left clear (alpha) for the stage's own.

    blender -b --python far_city_render.py -- <city.json> <out folder> <samples>

Night: the towers' own baked colour under a faint moon and sky, each window (the model's window mask,
tools/props/window_mask.py, in its colour texture's uvs) lit or dark by a seeded draw per window and tower, warm or
cool; some office crowns lit in a colour; the quay's lamps along the shore; a few lights on the mountains' lower
slopes; everything fading into the harbour's night haze with distance. Blender's frame: x east (the city's x), y north
(the city's -z), z up.
"""
import json
import math
import pathlib
import sys

import bpy
import numpy as np

# The night's light: the sky's ambient and the moon's, and the haze's colour and how far one fades it two thirds.
SKY = (0.010, 0.013, 0.025)
MOON = (0.55, 0.62, 0.8)
MOON_STRENGTH = 0.06
HAZE = (0.018, 0.020, 0.035)
HAZE_REACH = 4200.0
# Windows: how bright a lit one glows, the share lit for each use, and their colours (warm tungsten, cool tube).
WINDOW_GLOW = 6.0
LIT_SHARE = {"office": 0.45, "residential": 0.6, "front": 0.55}
WARM = (1.0, 0.72, 0.42)
COOL = (0.78, 0.9, 1.0)
# The office towers' crowns: the share lit, how far down from the top, their colours and glow.
CROWN_SHARE = 0.55
CROWN_DEPTH = 0.035
CROWNS = ((0.9, 0.95, 1.0), (0.3, 0.85, 1.0), (1.0, 0.25, 0.55), (1.0, 0.2, 0.15), (0.55, 1.0, 0.6))
CROWN_GLOW = 9.0
# The towers' bodies at night: their baked colour this dark.
BODY = 0.35
# The quay along the shore: how high it stands, how deep, and its lamps' spacing, height and glow.
QUAY_HIGH = 3.0
QUAY_DEEP = 24.0
LAMP_EVERY = 14.0
LAMP_HIGH = 6.0
LAMP_GLOW = 30.0
# The mountains' lights: how many per square kilometre of slope under the height they stop at.
SLOPE_LIGHTS = 0.0008
SLOPE_LIGHTS_UNDER = 260.0


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def set_render(samples):
    """Cycles on the card when the machine has one, a transparent film, the standard view."""
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.render.film_transparent = True
    scene.view_settings.view_transform = "Standard"
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    import os
    if os.environ.get("FARM_CYCLES_GPU"):
        preferences = bpy.context.preferences.addons["cycles"].preferences
        for backend in ("OPTIX", "CUDA"):
            try:
                preferences.compute_device_type = backend
                preferences.get_devices()
                if any(device.type == backend for device in preferences.devices):
                    break
            except TypeError:
                continue
        for device in preferences.devices:
            device.use = device.type != "CPU"
        scene.cycles.device = "GPU"


def set_world():
    """The night sky's faint light (seen only by the towers: the film is clear) and the moon."""
    world = bpy.data.worlds.new("night")
    world.use_nodes = True
    background = next(node for node in world.node_tree.nodes if node.type == "BACKGROUND")
    background.inputs[0].default_value = (*SKY, 1.0)
    bpy.context.scene.world = world
    moon = bpy.data.lights.new("moon", "SUN")
    moon.energy = MOON_STRENGTH
    moon.color = MOON
    holder = bpy.data.objects.new("moon", moon)
    holder.rotation_euler = (math.radians(60.0), 0.0, math.radians(200.0))
    bpy.context.scene.collection.objects.link(holder)


def hazed(tree, surface):
    """A shader faded into the night haze with the distance from the camera."""
    nodes, links = tree.nodes, tree.links
    camera = nodes.new("ShaderNodeCameraData")
    fade = nodes.new("ShaderNodeMath")
    fade.operation = "MULTIPLY"
    fade.inputs[1].default_value = -1.0 / HAZE_REACH
    links.new(camera.outputs["View Distance"], fade.inputs[0])
    power = nodes.new("ShaderNodeMath")
    power.operation = "EXPONENT"
    links.new(fade.outputs[0], power.inputs[0])
    keep = nodes.new("ShaderNodeMath")
    keep.operation = "SUBTRACT"
    keep.inputs[0].default_value = 1.0
    links.new(power.outputs[0], keep.inputs[1])
    haze = nodes.new("ShaderNodeEmission")
    haze.inputs["Color"].default_value = (*HAZE, 1.0)
    mix = nodes.new("ShaderNodeMixShader")
    links.new(keep.outputs[0], mix.inputs[0])
    links.new(surface, mix.inputs[1])
    links.new(haze.outputs[0], mix.inputs[2])
    return mix.outputs[0]


def random_by(tree, vector, offset):
    """A white noise draw (0..1) for a vector, shifted by the object's own random number times `offset`."""
    nodes, links = tree.nodes, tree.links
    info = nodes.new("ShaderNodeObjectInfo")
    shift = nodes.new("ShaderNodeVectorMath")
    shift.operation = "SCALE"
    links.new(info.outputs["Random"], shift.inputs["Scale"])
    shift.inputs[0].default_value = (offset, offset * 1.7, offset * 2.3)
    moved = nodes.new("ShaderNodeVectorMath")
    moved.operation = "ADD"
    links.new(vector, moved.inputs[0])
    links.new(shift.outputs[0], moved.inputs[1])
    noise = nodes.new("ShaderNodeTexWhiteNoise")
    noise.noise_dimensions = "3D"
    links.new(moved.outputs[0], noise.inputs["Vector"])
    return noise.outputs["Value"]


def compare(tree, value, limit, operation="LESS_THAN"):
    node = tree.nodes.new("ShaderNodeMath")
    node.operation = operation
    tree.links.new(value, node.inputs[0])
    node.inputs[1].default_value = limit
    return node.outputs[0]


def multiply(tree, first, second):
    node = tree.nodes.new("ShaderNodeMath")
    node.operation = "MULTIPLY"
    tree.links.new(first, node.inputs[0])
    if isinstance(second, float):
        node.inputs[1].default_value = second
    else:
        tree.links.new(second, node.inputs[1])
    return node.outputs[0]


def tower_material(name, colour_image, window_image, use, top):
    """A tower kind's night look: its baked colour dimmed, its windows lit by draw, an office crown lit by draw."""
    material = bpy.data.materials.new(f"{name}_night")
    material.use_nodes = True
    tree = material.node_tree
    nodes, links = tree.nodes, tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    uv = nodes.new("ShaderNodeTexCoord")
    colour = nodes.new("ShaderNodeTexImage")
    colour.image = colour_image
    dim = nodes.new("ShaderNodeMixRGB")
    dim.blend_type = "MULTIPLY"
    dim.inputs[0].default_value = 1.0
    links.new(colour.outputs["Color"], dim.inputs[1])
    dim.inputs[2].default_value = (BODY, BODY, BODY, 1.0)
    body = nodes.new("ShaderNodeBsdfDiffuse")
    links.new(dim.outputs[0], body.inputs["Color"])
    # A window lit or dark: the window mask, times a draw per small cell of the uvs and per tower.
    mask = nodes.new("ShaderNodeTexImage")
    mask.image = window_image
    mask.image.colorspace_settings.name = "Non-Color"
    snap = nodes.new("ShaderNodeVectorMath")
    snap.operation = "SNAP"
    snap.inputs[1].default_value = (1 / 320, 1 / 320, 1.0)
    links.new(uv.outputs["UV"], snap.inputs[0])
    lit = compare(tree, random_by(tree, snap.outputs[0], 37.0), LIT_SHARE[use])
    warmth = compare(tree, random_by(tree, snap.outputs[0], 91.0), 0.3)
    tint = nodes.new("ShaderNodeMixRGB")
    links.new(warmth, tint.inputs[0])
    tint.inputs[1].default_value = (*WARM, 1.0)
    tint.inputs[2].default_value = (*COOL, 1.0)
    window = multiply(tree, multiply(tree, mask.outputs["Color"], lit), WINDOW_GLOW)
    glow = nodes.new("ShaderNodeEmission")
    links.new(tint.outputs[0], glow.inputs["Color"])
    links.new(window, glow.inputs["Strength"])
    # An office crown: the top CROWN_DEPTH of the tower, lit on some towers in one of the colours.
    if use == "office":
        place = nodes.new("ShaderNodeTexCoord")
        height = nodes.new("ShaderNodeSeparateXYZ")
        links.new(place.outputs["Object"], height.inputs[0])
        near_top = compare(tree, height.outputs["Z"], top * (1.0 - CROWN_DEPTH), "GREATER_THAN")
        info = nodes.new("ShaderNodeObjectInfo")
        crowned = compare(tree, info.outputs["Random"], CROWN_SHARE)
        ramp = nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.interpolation = "CONSTANT"
        while len(ramp.color_ramp.elements) < len(CROWNS):
            ramp.color_ramp.elements.new(0.5)
        for index, crown in enumerate(CROWNS):
            ramp.color_ramp.elements[index].position = index / len(CROWNS)
            ramp.color_ramp.elements[index].color = (*crown, 1.0)
        pick = nodes.new("ShaderNodeMath")
        pick.operation = "FRACT"
        links.new(multiply(tree, info.outputs["Random"], 7.31), pick.inputs[0])
        links.new(pick.outputs[0], ramp.inputs[0])
        crown = nodes.new("ShaderNodeEmission")
        links.new(ramp.outputs[0], crown.inputs["Color"])
        links.new(multiply(tree, multiply(tree, near_top, crowned), CROWN_GLOW), crown.inputs["Strength"])
        both = nodes.new("ShaderNodeAddShader")
        links.new(glow.outputs[0], both.inputs[0])
        links.new(crown.outputs[0], both.inputs[1])
        glow_out = both.outputs[0]
    else:
        glow_out = glow.outputs[0]
    surface = nodes.new("ShaderNodeAddShader")
    links.new(body.outputs[0], surface.inputs[0])
    links.new(glow_out, surface.inputs[1])
    links.new(hazed(tree, surface.outputs[0]), output.inputs["Surface"])
    return material


def load_kind(name, path, use):
    """One tower kind's model as a hidden collection, its foot's middle at the origin, one unit tall, with its night
    material; returns the collection."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    meshes = [found for found in bpy.data.objects if found not in before and found.type == "MESH"]
    bpy.ops.object.select_all(action="DESELECT")
    for found in meshes:
        found.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    if len(meshes) > 1:
        bpy.ops.object.join()
    model = bpy.context.view_layer.objects.active
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    corners = np.array([model.matrix_world @ vertex.co for vertex in model.data.vertices])
    low, high = corners.min(axis=0), corners.max(axis=0)
    tall = high[2] - low[2]
    for vertex in model.data.vertices:
        vertex.co.x = (vertex.co.x - (low[0] + high[0]) / 2) / tall
        vertex.co.y = (vertex.co.y - (low[1] + high[1]) / 2) / tall
        vertex.co.z = (vertex.co.z - low[2]) / tall
    colour = next((node.image for slot in model.material_slots if slot.material and slot.material.use_nodes
                   for node in slot.material.node_tree.nodes if node.type == "TEX_IMAGE"), None)
    window = bpy.data.images.load(str(pathlib.Path(path).with_name(f"{pathlib.Path(path).stem}_windows.png")))
    model.data.materials.clear()
    model.data.materials.append(tower_material(name, colour, window, use, 1.0))
    for found in [found for found in bpy.data.objects if found not in before and found is not model]:
        bpy.data.objects.remove(found)
    collection = bpy.data.collections.new(name)
    for owner in list(model.users_collection):
        owner.objects.unlink(model)
    collection.objects.link(model)
    return collection


def lay_towers(towers, collections):
    """Every tower an instance of its kind's collection: at its spot, turned to its facing, scaled to its height."""
    group = bpy.data.collections.new("towers")
    bpy.context.scene.collection.children.link(group)
    for index, tower in enumerate(towers):
        holder = bpy.data.objects.new(f"tower_{index}", None)
        holder.instance_type = "COLLECTION"
        holder.instance_collection = collections[tower["kind"]]
        holder.location = (tower["at"][0], -tower["at"][1], 0.0)
        holder.rotation_euler = (0.0, 0.0, -math.radians(tower["facing"]))
        holder.scale = (tower["height"],) * 3
        group.objects.link(holder)


def plain_material(name, colour, glow=None):
    """A plain diffuse colour, hazed, glowing in `glow` (colour, strength) when given."""
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    tree = material.node_tree
    nodes, links = tree.nodes, tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    diffuse = nodes.new("ShaderNodeBsdfDiffuse")
    diffuse.inputs["Color"].default_value = (*colour, 1.0)
    surface = diffuse.outputs[0]
    if glow:
        light = nodes.new("ShaderNodeEmission")
        light.inputs["Color"].default_value = (*glow[0], 1.0)
        light.inputs["Strength"].default_value = glow[1]
        surface = light.outputs[0]
    links.new(hazed(tree, surface), output.inputs["Surface"])
    return material


def mesh_object(name, points, faces, material):
    data = bpy.data.meshes.new(name)
    data.from_pydata([tuple(point) for point in points], [], [tuple(face) for face in faces])
    data.materials.append(material)
    holder = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(holder)
    return holder


def at_bearing(bearing, reach, height):
    """A point in Blender's frame at a bearing (degrees clockwise from north) and reach from the middle."""
    return (reach * math.sin(math.radians(bearing)), reach * math.cos(math.radians(bearing)), height)


def build_mountains(mountains):
    """The mountains as one polar ground: each bearing's heights at reaches behind its shore."""
    bearings, reaches, heights = mountains["bearings"], mountains["reaches"], mountains["heights"]
    points = [at_bearing(bearing, mountains["shore"][column] + reach, heights[row][column])
              for row, reach in enumerate(reaches) for column, bearing in enumerate(bearings)]
    count = len(bearings)
    faces = [(row * count + column, row * count + column + 1, (row + 1) * count + column + 1, (row + 1) * count + column)
             for row in range(len(reaches) - 1) for column in range(count - 1)]
    mesh_object("mountains", points, faces, plain_material("mountain", (0.025, 0.028, 0.035)))
    return points


def build_quay(mountains):
    """The quay along the far shore, a low dark wall facing the harbour, and its lamps (small glowing cubes)."""
    bearings, shore = mountains["bearings"], mountains["shore"]
    points = []
    for bearing, reach in zip(bearings, shore):
        points += [at_bearing(bearing, reach, 0.0), at_bearing(bearing, reach, QUAY_HIGH),
                   at_bearing(bearing, reach + QUAY_DEEP, QUAY_HIGH)]
    faces = [(3 * index + step, 3 * index + 3 + step, 3 * index + 4 + step, 3 * index + 1 + step)
             for index in range(len(bearings) - 1) for step in (0, 1)]
    mesh_object("quay", points, faces, plain_material("quay", (0.04, 0.04, 0.045)))
    lamps, lamp_faces = [], []
    for index in range(len(bearings) - 1):
        start, end = np.array(at_bearing(bearings[index], shore[index] + 3.0, 0.0)), np.array(
            at_bearing(bearings[index + 1], shore[index + 1] + 3.0, 0.0))
        steps = max(1, int(np.linalg.norm(end - start) // LAMP_EVERY))
        for step in range(steps):
            middle = start + (end - start) * step / steps + np.array([0.0, 0.0, LAMP_HIGH])
            first = len(lamps)
            lamps += [tuple(middle + np.array(corner) * 0.9) for corner in
                      ((-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1), (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1))]
            lamp_faces += [tuple(first + corner for corner in face) for face in
                           ((0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7))]
    mesh_object("quay_lamps", lamps, lamp_faces, plain_material("lamp", (1.0, 0.8, 0.5), ((1.0, 0.78, 0.5), LAMP_GLOW)))


def build_slope_lights(mountain_points, seed):
    """A few lights on the mountains' lower slopes (roads and houses), seeded: small glowing cubes."""
    choose = np.random.default_rng(seed)
    points = np.array(mountain_points)
    low = points[(points[:, 2] > 15.0) & (points[:, 2] < SLOPE_LIGHTS_UNDER)]
    count = int(len(low) * SLOPE_LIGHTS * 1e4 / 4)
    picked = low[choose.choice(len(low), size=min(count, len(low)), replace=False)] if len(low) else low
    corners, faces = [], []
    for point in picked:
        first = len(corners)
        corners += [tuple(point + np.array(corner) * 2.0) for corner in
                    ((-1, -1, 0), (1, -1, 0), (1, 1, 0), (-1, 1, 0), (-1, -1, 2), (1, -1, 2), (1, 1, 2), (-1, 1, 2))]
        faces += [tuple(first + corner for corner in face) for face in
                  ((0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7))]
    if corners:
        mesh_object("slope_lights", corners, faces,
                    plain_material("slope_light", (1.0, 0.85, 0.6), ((1.0, 0.85, 0.6), LAMP_GLOW)))


def render_strips(strips, eye, out):
    """Each arc's strip from the ring's middle: a central cylindrical camera turned to the arc's middle bearing."""
    scene = bpy.context.scene
    data = bpy.data.cameras.new("ring")
    data.type = "PANO"
    data.panorama_type = "CENTRAL_CYLINDRICAL"
    data.clip_end = 20000.0
    camera = bpy.data.objects.new("ring", data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.location = (0.0, 0.0, eye)
    out.mkdir(parents=True, exist_ok=True)
    for strip in strips:
        data.central_cylindrical_range_u_min = -strip["half"]
        data.central_cylindrical_range_u_max = strip["half"]
        data.central_cylindrical_range_v_min = strip["v_low"]
        data.central_cylindrical_range_v_max = strip["v_high"]
        camera.rotation_euler = (math.radians(90.0), 0.0, -math.radians(strip["middle"]))
        scene.render.resolution_x, scene.render.resolution_y = strip["width"], strip["height"]
        scene.render.filepath = str(out / f"{strip['name']}.png")
        bpy.ops.render.render(write_still=True)
        print("far city strip", strip["name"], flush=True)


def main():
    city_path, out, samples = sys.argv[sys.argv.index("--") + 1:][:3]
    city = json.loads(pathlib.Path(city_path).read_text())
    clear_scene()
    set_render(int(samples))
    set_world()
    uses = {kind: use for kind, use in city.get("uses", {}).items()}
    collections = {name: load_kind(name, path, uses.get(name, "residential")) for name, path in city["kinds"].items()}
    lay_towers(city["towers"], collections)
    mountain_points = build_mountains(city["mountains"])
    build_quay(city["mountains"])
    build_slope_lights(mountain_points, city["seed"])
    render_strips(city["strips"], city["eye"], pathlib.Path(out))


main()
