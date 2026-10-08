"""Runs inside Blender (`session.py batch`): render a place's made models and their labelled parts for the review page.

    python3 tools/blender/session.py batch tools/blender/inside/review_models.py -- <shots.json> <out folder>

shots.json: {"size": [wide, tall], "groups": [{"name", "members": [{"name", "files": [{"path", "colour"}], "up"}],
"heading"}]}.
A member is one take of one thing: a made model (one .gltf, drawn with its own baked colour map) or its labelled parts
(one .ply per library surface, each drawn flat in that surface's colour, `colour` linear RGB). `up` is the axis the
files stand on, "y" (glTF, and the labelled parts) or "z". Every member of a group is drawn from one camera, set from
all the members' bounds together, so two takes of a thing (before and after a stage was rerun) are seen the same way;
a group's `heading` (degrees, HEADING when absent) turns that camera round the model, 180 more to see its back.
Per member it writes <member name>.png, and shots-report.json with each member's triangles and size in its own units.
Workbench draws them (studio light, no shadows): it is fast on the processor and shows shape and colour plainly.
"""
import json
import math
import pathlib
import sys

import bpy
from mathutils import Matrix, Vector

BACKGROUND = (0.13, 0.13, 0.14)
# The camera looks down at this angle from the front-right, as a three-quarter product shot.
ELEVATION = 22.0
HEADING = 35.0
LENS_ANGLE = 30.0
MARGIN = 0.8
Y_UP_TO_Z_UP = Matrix.Rotation(math.radians(90.0), 4, "X")


def arguments():
    given = sys.argv[sys.argv.index("--") + 1:]
    if len(given) != 2:
        raise SystemExit(__doc__)
    return json.loads(pathlib.Path(given[0]).read_text()), pathlib.Path(given[1])


def empty_scene(size):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.show_shadows = False
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = "WORLD"
    scene.render.resolution_x, scene.render.resolution_y = size
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.view_settings.view_transform = "Standard"
    world = bpy.data.worlds.new("background")
    world.color = BACKGROUND
    scene.world = world
    return scene


def flat_material(name, colour):
    material = bpy.data.materials.new(name)
    material.diffuse_color = (*colour, 1.0)
    return material


def import_file(path):
    """One file brought in; the new objects it made."""
    before = set(bpy.data.objects)
    if path.suffix == ".ply":
        bpy.ops.wm.ply_import(filepath=str(path))
    elif path.suffix in (".gltf", ".glb"):
        bpy.ops.import_scene.gltf(filepath=str(path))
    else:
        raise SystemExit(f"review_models: no importer for {path}")
    return [item for item in bpy.data.objects if item not in before]


def import_member(member):
    """A member's files brought in, each part coloured when it names a colour, stood on z up."""
    objects = []
    for entry in member["files"]:
        made = import_file(pathlib.Path(entry["path"]))
        if entry.get("colour"):
            material = flat_material(pathlib.Path(entry["path"]).stem, entry["colour"])
            for item in made:
                if item.type == "MESH":
                    item.data.materials.clear()
                    item.data.materials.append(material)
        objects += made
    # The glTF importer turns y-up into z-up itself; a .ply comes in as written.
    if member.get("up", "y") == "y" and all(pathlib.Path(entry["path"]).suffix == ".ply" for entry in member["files"]):
        for item in objects:
            if item.parent is None:
                item.matrix_world = Y_UP_TO_Z_UP @ item.matrix_world
    bpy.context.view_layer.update()
    return objects


def corners(objects):
    return [item.matrix_world @ Vector(corner) for item in objects if item.type == "MESH" for corner in item.bound_box]


def bounds(points):
    return (Vector([min(point[axis] for point in points) for axis in range(3)]),
            Vector([max(point[axis] for point in points) for axis in range(3)]))


def camera_for(scene, low, high, heading_degrees=HEADING):
    """A camera from `heading_degrees` round (the front-right by default) and above that holds the whole box."""
    middle = (low + high) / 2
    radius = (high - low).length / 2 * MARGIN
    distance = radius / math.sin(math.radians(LENS_ANGLE) / 2)
    heading, elevation = math.radians(heading_degrees), math.radians(ELEVATION)
    eye = middle + distance * Vector((math.sin(heading) * math.cos(elevation), -math.cos(heading) * math.cos(elevation),
                                      math.sin(elevation)))
    data = bpy.data.cameras.new("shot")
    data.sensor_fit = "AUTO"
    data.angle = math.radians(LENS_ANGLE)
    data.clip_start, data.clip_end = distance / 100, distance * 4
    item = bpy.data.objects.new("shot", data)
    scene.collection.objects.link(item)
    item.location = eye
    item.rotation_euler = (middle - eye).to_track_quat("-Z", "Y").to_euler()
    scene.camera = item
    return item


def triangles(objects):
    return sum(sum(len(polygon.vertices) - 2 for polygon in item.data.polygons) for item in objects if item.type == "MESH")


def remove(objects):
    for item in objects:
        bpy.data.objects.remove(item, do_unlink=True)


def render_group(scene, group, out):
    """Every member of a group imported, one camera set from them all, each member rendered alone."""
    imported = {member["name"]: (member, import_member(member)) for member in group["members"]}
    everything = [item for _, objects in imported.values() for item in objects]
    low, high = bounds(corners(everything))
    camera = camera_for(scene, low, high, group.get("heading", HEADING))
    report = {}
    for name, (member, objects) in imported.items():
        for item in everything:
            item.hide_render = item not in objects
        textured = any(pathlib.Path(entry["path"]).suffix != ".ply" for entry in member["files"])
        scene.display.shading.color_type = "TEXTURE" if textured else "MATERIAL"
        scene.render.filepath = str(out / f"{name}.png")
        bpy.ops.render.render(write_still=True)
        own_low, own_high = bounds(corners(objects))
        report[name] = {"triangles": triangles(objects), "size": [round(value, 3) for value in own_high - own_low]}
    remove(everything + [camera])
    return report


def main():
    shots, out = arguments()
    out.mkdir(parents=True, exist_ok=True)
    scene = empty_scene(shots["size"])
    report = {}
    for group in shots["groups"]:
        report.update(render_group(scene, group, out))
    (out / "shots-report.json").write_text(json.dumps(report, indent=1))
    print("review_models: wrote", out)


main()
