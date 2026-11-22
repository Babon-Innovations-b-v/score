"""Runs inside Blender: render library entries as studio pictures, one picture per item.

    python3 tools/blender/session.py batch tools/blender/inside/library_demo.py -- <job.json> <out folder>

job.json: {"size": [wide, tall], "samples": n, "items": [item, ...]}. An item:
    {"name": "model",                      the picture's file name (<name>.png)
     "files": ["/abs/a.gltf", ...],        what it shows: .gltf/.glb, .usd/.usda/.usdc or .ply, laid together; a file
              may be {"path", "finish", "glass": true, "up": "y"} to give that file its own finish, a clear glass, or
              stand a Y-up file upright; "parts": {part: finish | "glass" | "drop"} finishes a
              kit piece part by part (its material slots), "drop" leaving that part's faces out
     "finish": {"colour", "roughness", "normal", "metalness", "metre"} or absent: a library surface's maps laid on every
              mesh by box projection in world metres (`metre` is how many metres one copy of the maps covers), so a
              finish never follows a piece's own texture coordinates
     "heading": 35, "elevation": 18,       the camera's turn round the item and its look down, degrees
     "lens": 50, "margin": 1.15,           focal length (mm) and how much room is left round the item
     "ground": "light" | "dark",           the studio's backdrop
     "frame": n, "action": "walking",      a rigged character's clip and the frame of it to show
     "points": [{"npz", "usd", "look": "puff", "colour"}],  an effect's particles at one clip time (npz: points in
                                           the picture's metres, widths, opacity; usd: the same points as a Points
                                           file), drawn as score's game draws them
     "hide": ["far", ...],                 objects of the files left out of the picture (another level of detail)
     (a file's "turn" (degrees about the up axis) then "at": [x, y, z] moves it, in metres, before the item is stood on the ground; lamps move with it)
     "lamps": [{"type": "POINT"|"SPOT"|"AREA", "at": [x,y,z], "aim": [x,y,z], "watts", "colour", "cone", "size"}],
                                           extra lights in the item's own metres (a light entry's lamps)
     "studio": 1.0}                        the studio lights' strength (0 for a scene lit only by its own lamps)
The studio is a curved backdrop with a key, fill and rim area light sized to the item, AgX; Cycles on the card where
FARM_CYCLES_GPU is set (the rented machines), else on 8 processor threads (session.py batch on this PC).
"""
import json
import math
import os
import pathlib
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector


def arguments():
    given = sys.argv[sys.argv.index("--") + 1:]
    if len(given) != 2:
        raise SystemExit(__doc__)
    return json.loads(pathlib.Path(given[0]).read_text()), pathlib.Path(given[1])


def empty_scene(size, samples):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.render.threads_mode, scene.render.threads = "FIXED", 8  # never every core of the owner's PC
    if os.environ.get("FARM_CYCLES_GPU"):  # set on the rented machines only: this PC's card is for game tests
        use_card(scene)
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 8
    scene.cycles.transparent_max_bounces = 64
    scene.render.resolution_x, scene.render.resolution_y = size
    scene.render.film_transparent = False
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
    world = bpy.data.worlds.new("world")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.0
    scene.world = world
    return scene


def use_card(scene):
    """Cycles on the machine's card, OptiX else CUDA (tools/props/library/inside/scene_setup.py's way)."""
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
            return kind
    raise RuntimeError("FARM_CYCLES_GPU is set but no OptiX or CUDA card was found")


def world_light(scene, colour, strength):
    background = scene.world.node_tree.nodes["Background"]
    background.inputs[0].default_value = (*colour, 1.0)
    background.inputs[1].default_value = strength


def import_file(path):
    before = set(bpy.data.objects)
    suffix = pathlib.Path(path).suffix.lower()
    if suffix in (".gltf", ".glb"):
        bpy.ops.import_scene.gltf(filepath=str(path))
    elif suffix in (".usd", ".usda", ".usdc"):
        bpy.ops.wm.usd_import(filepath=str(path))
    elif suffix == ".ply":
        bpy.ops.wm.ply_import(filepath=str(path))
        for obj in bpy.data.objects:
            if obj not in before and obj.type == "MESH":
                obj.data.shade_smooth()
                obj.data.set_sharp_from_angle(angle=math.radians(35.0))
    else:
        raise SystemExit(f"cannot read {path}")
    return [obj for obj in bpy.data.objects if obj not in before]


def evaluated_corners(objects):
    graph = bpy.context.evaluated_depsgraph_get()
    points = []
    for obj in objects:
        if obj.type == "POINTCLOUD":
            points.extend(obj.matrix_world @ point.co for point in obj.data.points)
            continue
        if obj.type != "MESH":
            continue
        evaluated = obj.evaluated_get(graph)
        mesh = evaluated.to_mesh()
        world = evaluated.matrix_world
        points.extend(world @ vertex.co for vertex in mesh.vertices)
        evaluated.to_mesh_clear()
    if not points:
        raise SystemExit("nothing to show: no mesh")
    low = Vector(min(point[axis] for point in points) for axis in range(3))
    high = Vector(max(point[axis] for point in points) for axis in range(3))
    return low, high


def stand_on_ground(objects):
    """Move the item's roots so it stands centred on the ground at the origin."""
    low, high = evaluated_corners(objects)
    shift = Vector((-(low.x + high.x) / 2, -(low.y + high.y) / 2, -low.z))
    for obj in objects:
        if obj.parent is None:
            obj.matrix_world = Matrix.Translation(shift) @ obj.matrix_world
    bpy.context.view_layer.update()
    return (*evaluated_corners(objects), shift)


def finish_material(finish):
    material = bpy.data.materials.new("finish")
    material.use_nodes = True
    nodes, links = material.node_tree.nodes, material.node_tree.links
    shader = nodes["Principled BSDF"]
    coordinates = nodes.new("ShaderNodeTexCoord")
    mapping = nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = [1.0 / finish["metre"]] * 3
    links.new(coordinates.outputs["Object"], mapping.inputs["Vector"])

    def texture(key, colour):
        node = nodes.new("ShaderNodeTexImage")
        node.image = bpy.data.images.load(finish[key])
        node.image.colorspace_settings.name = "sRGB" if colour else "Non-Color"
        node.projection = "BOX"
        node.projection_blend = 0.25
        links.new(mapping.outputs["Vector"], node.inputs["Vector"])
        return node

    links.new(texture("colour", True).outputs["Color"], shader.inputs["Base Color"])
    if finish.get("roughness"):
        links.new(texture("roughness", False).outputs["Color"], shader.inputs["Roughness"])
    if finish.get("metalness"):
        links.new(texture("metalness", False).outputs["Color"], shader.inputs["Metallic"])
    if finish.get("normal"):
        normal = nodes.new("ShaderNodeNormalMap")
        links.new(texture("normal", False).outputs["Color"], normal.inputs["Color"])
        links.new(normal.outputs["Normal"], shader.inputs["Normal"])
    return material


def glass_material():
    material = bpy.data.materials.new("glass")
    material.use_nodes = True
    shader = material.node_tree.nodes["Principled BSDF"]
    shader.inputs["Base Color"].default_value = (0.92, 0.97, 1.0, 1.0)
    shader.inputs["Roughness"].default_value = 0.03
    shader.inputs["IOR"].default_value = 1.45
    shader.inputs["Transmission Weight"].default_value = 1.0
    return material


def apply_finish(objects, finish):
    """Lay one surface on every mesh; each mesh's transform is applied first so Object space is world metres."""
    material = glass_material() if finish == "glass" else finish_material(finish)
    for obj in objects:
        if obj.type != "MESH":
            continue
        obj.data = obj.data.copy()
        obj.data.transform(obj.matrix_world)
        obj.matrix_world = Matrix.Identity(4)
        obj.data.materials.clear()
        obj.data.materials.append(material)


def apply_parts(objects, parts):
    """Give each named part (a material slot of the piece) its own finish, or drop its faces ("drop")."""
    made = {name: None if finish == "drop" else glass_material() if finish == "glass" else finish_material(finish)
            for name, finish in parts.items()}
    for obj in objects:
        if obj.type != "MESH":
            continue
        obj.data = obj.data.copy()
        obj.data.transform(obj.matrix_world)
        obj.matrix_world = Matrix.Identity(4)
        names = [slot.material.name.split(".")[0] if slot.material else "" for slot in obj.material_slots]
        unknown = [name for name in names if name not in made]
        if unknown:
            raise SystemExit(f"{obj.name}: parts {unknown} have no finish given")
        builder = bmesh.new()
        builder.from_mesh(obj.data)
        dropped = [face for face in builder.faces if made[names[face.material_index]] is None]
        bmesh.ops.delete(builder, geom=dropped, context="FACES")
        builder.to_mesh(obj.data)
        builder.free()
        for index, name in enumerate(names):
            if made[name] is not None:
                obj.data.materials[index] = made[name]


def effect_points(spec):
    """One effect's particles as a point cloud, each a sphere of its width, thick by its opacity (usd_views.py's way:
    the cloud comes from the reader's import of a Points file, which every Blender since 4.2 reads, and its attributes
    are then set in place)."""
    import numpy
    loaded = numpy.load(spec["npz"])
    obj = next(item for item in import_file(spec["usd"]) if item.type == "POINTCLOUD")
    cloud = obj.data
    if len(cloud.points) != len(loaded["points"]):
        raise RuntimeError(f"{spec['usd']} holds {len(cloud.points)} points, its npz {len(loaded['points'])}")
    obj.matrix_world = Matrix.Identity(4)
    cloud.attributes["position"].data.foreach_set("vector", loaded["points"].ravel())
    radius = cloud.attributes.get("radius") or cloud.attributes.new("radius", "FLOAT", "POINT")
    radius.data.foreach_set("value", loaded["widths"] / 2.0)
    thickness = cloud.attributes.get("opacity") or cloud.attributes.new("opacity", "FLOAT", "POINT")
    thickness.data.foreach_set("value", loaded["opacity"])
    cloud.update_tag()
    cloud.materials.clear()
    cloud.materials.append(effect_material(spec.get("look", "puff"), spec.get("colour", (0.9, 0.9, 0.89))))
    return obj


def effect_material(look, colour):
    """score's effect look (tools/blender/inside/usd_views.py effect_material): a puff is lit and thickest in its
    middle, the facing share cubed; a speck is unlit. See-through by each point's opacity."""
    material = bpy.data.materials.new("effect")
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
    shape.operation = "POWER"
    shape.inputs[1].default_value = 3.0
    links.new(straight.outputs["Value"], shape.inputs[0])
    surface = nodes.new("ShaderNodeBsdfDiffuse" if look == "puff" else "ShaderNodeEmission")
    surface.inputs["Color"].default_value = (*colour, 1.0)
    share = nodes.new("ShaderNodeMath")
    share.operation = "MULTIPLY"
    links.new(thickness.outputs["Fac"], share.inputs[0])
    links.new(shape.outputs[0], share.inputs[1])
    clear = nodes.new("ShaderNodeBsdfTransparent")
    mix = nodes.new("ShaderNodeMixShader")
    links.new(share.outputs["Value"], mix.inputs["Fac"])
    links.new(clear.outputs["BSDF"], mix.inputs[1])
    links.new(surface.outputs[0], mix.inputs[2])
    links.new(mix.outputs["Shader"], output.inputs["Surface"])
    return material


def backdrop(radius, ground):
    """A floor that bends up into a wall behind the item: no horizon line."""
    mesh = bpy.data.meshes.new("backdrop")
    builder = bmesh.new()
    width, depth, bend = radius * 12, radius * 8, radius * 2.5
    profile = [(-depth, 0.0)]
    for step in range(13):
        angle = math.radians(90 * step / 12)
        profile.append((depth * 0.5 + math.sin(angle) * bend, bend - math.cos(angle) * bend))
    profile.append((depth * 0.5 + bend, radius * 10))
    rows = []
    for along, height in profile:
        rows.append([builder.verts.new((side * width, along, height)) for side in (-1, 1)])
    for first, second in zip(rows, rows[1:]):
        builder.faces.new((first[0], first[1], second[1], second[0]))
    builder.to_mesh(mesh)
    builder.free()
    for polygon in mesh.polygons:
        polygon.use_smooth = True
    obj = bpy.data.objects.new("backdrop", mesh)
    bpy.context.scene.collection.objects.link(obj)
    material = bpy.data.materials.new("backdrop")
    material.use_nodes = True
    shader = material.node_tree.nodes["Principled BSDF"]
    tone = 0.16 if ground == "light" else 0.03
    shader.inputs["Base Color"].default_value = (tone, tone, tone * 1.02, 1.0)
    shader.inputs["Roughness"].default_value = 0.55
    mesh.materials.append(material)
    return obj


def area_light(name, at, aim, watts, size, colour=(1.0, 1.0, 1.0)):
    data = bpy.data.lights.new(name, "AREA")
    data.energy, data.size, data.color = watts, size, colour
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = at
    obj.rotation_euler = (Vector(aim) - Vector(at)).to_track_quat("-Z", "Y").to_euler()
    return obj


def studio_lights(radius, centre, strength):
    """Key from the front left, fill from the right, rim from behind; watts grow with the item's area."""
    scale = radius * radius
    area_light("key", centre + Vector((-2.2, -2.0, 2.4)) * radius, centre, 500 * scale * strength, radius * 2.2)
    area_light("fill", centre + Vector((2.6, -1.2, 1.0)) * radius, centre, 120 * scale * strength, radius * 3.0,
               (0.92, 0.96, 1.0))
    area_light("rim", centre + Vector((0.8, 2.6, 2.2)) * radius, centre, 700 * scale * strength, radius * 1.5,
               (1.0, 0.95, 0.88))


def item_lamps(lamps, shift):
    for index, lamp in enumerate(lamps):
        data = bpy.data.lights.new(f"lamp{index}", lamp["type"])
        data.energy = lamp["watts"]
        data.color = lamp.get("colour", (1.0, 1.0, 1.0))
        if lamp["type"] == "SPOT":
            data.spot_size = math.radians(lamp.get("cone", 45.0))
            data.spot_blend = lamp.get("blend", 0.3)
        if lamp["type"] in ("POINT", "SPOT"):
            data.shadow_soft_size = lamp.get("size", 0.05)
        if lamp["type"] == "AREA":
            data.size = lamp.get("size", 0.5)
        obj = bpy.data.objects.new(f"lamp{index}", data)
        bpy.context.scene.collection.objects.link(obj)
        obj.location = Vector(lamp["at"]) + shift
        if "aim" in lamp:
            obj.rotation_euler = (Vector(lamp["aim"]) - Vector(lamp["at"])).to_track_quat("-Z", "Y").to_euler()


def camera_for(scene, low, high, item):
    centre = (low + high) / 2
    radius = max((high - low).length / 2, 1e-3)
    lens = item.get("lens", 50.0)
    data = bpy.data.cameras.new("camera")
    data.lens = lens
    data.sensor_width = 36.0
    wide, tall = scene.render.resolution_x, scene.render.resolution_y
    half_angle = math.atan(min(1.0, tall / wide) * 18.0 / lens)
    distance = radius * item.get("margin", 0.9) / math.sin(half_angle)
    heading, elevation = math.radians(item.get("heading", 35.0)), math.radians(item.get("elevation", 18.0))
    direction = Vector((math.sin(heading) * math.cos(elevation), -math.cos(heading) * math.cos(elevation),
                        math.sin(elevation)))
    aim = centre + Vector(item.get("aim_shift", (0.0, 0.0, 0.0))) * radius
    camera = bpy.data.objects.new("camera", data)
    scene.collection.objects.link(camera)
    camera.location = aim + direction * distance
    camera.rotation_euler = (-direction).to_track_quat("-Z", "Y").to_euler()
    data.clip_start, data.clip_end = distance / 100, distance * 50
    scene.camera = camera
    return centre, radius


def render_item(job, item, out):
    scene = empty_scene(job["size"], job.get("samples", 128))
    objects = []
    for given in item["files"]:
        given = given if isinstance(given, dict) else {"path": given}
        imported = import_file(given["path"])
        if given.get("up", item.get("up")) == "y":
            for obj in imported:
                if obj.parent is None:
                    obj.matrix_world = Matrix.Rotation(math.radians(90.0), 4, "X") @ obj.matrix_world
            bpy.context.view_layer.update()
        if "at" in given or "turn" in given:
            place = Matrix.Translation(Vector(given.get("at", (0.0, 0.0, 0.0)))) @ Matrix.Rotation(
                math.radians(given.get("turn", 0.0)), 4, "Z")
            for obj in imported:
                if obj.parent is None:
                    obj.matrix_world = place @ obj.matrix_world
            bpy.context.view_layer.update()
        if given.get("glass"):
            apply_finish(imported, "glass")
        elif given.get("finish"):
            apply_finish(imported, given["finish"])
        elif given.get("parts"):
            apply_parts(imported, given["parts"])
        objects.extend(imported)
    for spec in item.get("points", []):
        objects.append(effect_points(spec))
    hidden = [obj for obj in objects if obj.name in item.get("hide", [])]
    for obj in hidden:
        bpy.data.objects.remove(obj)
    objects = [obj for obj in objects if obj not in hidden]
    if "action" in item:
        for obj in objects:
            if obj.type == "ARMATURE":
                obj.animation_data_create().action = bpy.data.actions[item["action"]]
                if obj.animation_data.action_slot is None and obj.animation_data.action_suitable_slots:
                    obj.animation_data.action_slot = obj.animation_data.action_suitable_slots[0]
    if "frame" in item:
        scene.frame_set(item["frame"])
    if item.get("finish"):
        apply_finish(objects, item["finish"])
    low, high, shift = stand_on_ground(objects)
    centre, radius = camera_for(scene, low, high, item)
    backdrop(radius, item.get("ground", "light"))
    studio_lights(radius, centre, item.get("studio", 1.0))
    world_light(scene, (0.6, 0.65, 0.72), 0.08 * item.get("studio", 1.0))
    item_lamps(item.get("lamps", []), shift)
    scene.render.filepath = str(out / f"{item['name']}.png")
    bpy.ops.render.render(write_still=True)
    print(f"library_demo: wrote {scene.render.filepath} size {list(high - low)}", flush=True)


def main():
    job, out = arguments()
    out.mkdir(parents=True, exist_ok=True)
    for item in job["items"]:
        try:
            render_item(job, item, out)
        except Exception as error:  # one broken entry is reported and the rest still render
            print(f"library_demo: FAILED {item['name']}: {error!r}", flush=True)


main()
