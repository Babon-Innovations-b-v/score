"""Inside Blender (5.x, Cycles on the card): a whole person (`__main__`'s scene.npz) drawn as a studio photograph from
every side, each piece in its score_lib finish.

    blender -b --python render.py -- <scene.npz> <library folder> <out folder>

scene.npz is face/blender_face.py's piece format (`pieces`, and per piece its points, triangles, surfaces, finish,
uv or strands' counts and radius; y up), with `views` (JSON: {name: degrees round the person from its front}),
`name` (the pose's), `cloth` (the garments' pieces) and `subdivided` / `thick` (the pieces drawn subdivided once,
and the cloth pieces given their thickness, m). Each surface is the library entry's own material.usda through
Blender's USD reader (`blender_face.library_material`); hair, brows and lashes in the hair route's Principled Hair
BSDF.

The studio: a seamless backdrop (a floor curving up into a wall behind, the library's paper_white), a large soft key
from the camera's left above, a fill from its right, a rim from behind for the hair's edge, a dim grey sky; the
person turned on a turntable for each view, so every side is lit and backed alike. An 85 mm lens framing the whole
person, AgX. Then a close-up of the face (the head filling the frame, from FACE_TURN off its front) in the same
studio, and the person in one simple real setting (`setting`: {"floor", "wall"}, library surfaces: a concrete floor
running to a concrete wall behind) in daylight (a low sun, a pale sky) from SETTING_VIEW.
Writes <out>/<name>-<view>.png, <out>/<name>-face.png and <out>/<name>-setting.png.
"""
import json
import math
import pathlib
import sys

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "face"))
import blender_face  # noqa: E402  (the face's pieces, strands and library finishes, one way of drawing them)

SIZE = (1200, 1800)
SAMPLES = 512
LENS_MM = 85.0
EYE_HEIGHT = 1.15  # m: the camera at the person's chest, a fashion photograph's height
MARGIN = 1.18  # the frame's height over the person's
KEY = {"turn": 45.0, "rise": 40.0, "size": 2.2, "watts": 900.0}
FILL = {"turn": -60.0, "rise": 15.0, "size": 2.5, "watts": 250.0}
RIM = {"turn": 160.0, "rise": 35.0, "size": 1.2, "watts": 500.0}
SKY = (0.5, 0.5, 0.5)
SKY_STRENGTH = 0.25
BACKDROP = {"surface": "paper_white", "behind": 2.2, "width": 8.0, "height": 4.5, "bend": 0.8}
FACE_TURN = 20.0  # degrees: the close-up a little off the face's front, so the nose and an ear read in depth
FACE_FRAME_M = 0.42  # the close-up's frame height: the head and the neck's top
SETTING_VIEW = "three_quarter"
SUN = {"turn": 60.0, "rise": 35.0, "watts": 4.0, "angle": 1.5}  # W/m2, the sun's disc in degrees: soft-edged shade
DAY_SKY = (0.55, 0.68, 0.9)
DAY_STRENGTH = 1.2
SETTING = {"behind": 3.0, "width": 14.0, "height": 4.0, "tile_m": 1.5}


def arguments():
    return sys.argv[sys.argv.index("--") + 1:]


def backdrop(library, middle):
    """The seamless paper: a floor that curves up into a wall `behind` the person's middle (z up, the person facing
    -y), its st in metres over the paper's texture."""
    rows = []
    depth, bend = BACKDROP["behind"], BACKDROP["bend"]
    for step in range(40):
        angle = step / 39.0 * math.pi / 2.0
        rows.append((middle.y + depth - bend + bend * math.sin(angle), bend - bend * math.cos(angle)))
    rows = [(middle.y - 10.0, 0.0)] + rows + [(middle.y + depth, BACKDROP["height"])]
    half = BACKDROP["width"] / 2.0
    points, faces, along = [], [], 0.0
    lengths = [0.0]
    for (y0, z0), (y1, z1) in zip(rows, rows[1:]):
        along += math.hypot(y1 - y0, z1 - z0)
        lengths.append(along)
    for (y, z) in rows:
        points += [(middle.x - half, y, z), (middle.x + half, y, z)]
    for row in range(len(rows) - 1):
        here = row * 2
        faces.append((here, here + 1, here + 3, here + 2))
    mesh = bpy.data.meshes.new("backdrop")
    mesh.from_pydata(points, [], faces)
    layer = mesh.uv_layers.new(name="st")
    corners = []
    for row in range(len(rows) - 1):
        for column, length in ((0, lengths[row]), (1, lengths[row]), (1, lengths[row + 1]), (0, lengths[row + 1])):
            corners += [column * BACKDROP["width"] / 2.0, length / 2.0]
    layer.data.foreach_set("uv", np.asarray(corners, dtype=np.float32))
    mesh.polygons.foreach_set("use_smooth", np.ones(len(faces), dtype=bool))
    mesh.materials.append(blender_face.library_material(library, BACKDROP["surface"]))
    item = bpy.data.objects.new("backdrop", mesh)
    bpy.context.scene.collection.objects.link(item)
    return item


def setting(library, middle, surfaces):
    """The real setting: a concrete floor (its st one tile a SETTING tile_m) to a concrete wall SETTING behind the
    person's middle, each its library surface."""
    half, behind, tile = SETTING["width"] / 2.0, middle.y + SETTING["behind"], SETTING["tile_m"]
    found = []
    for name, corners in (("floor", [(-half, middle.y - 12.0, 0.0), (half, middle.y - 12.0, 0.0), (half, behind, 0.0),
                                     (-half, behind, 0.0)]),
                          ("wall", [(-half, behind, 0.0), (half, behind, 0.0), (half, behind, SETTING["height"]),
                                    (-half, behind, SETTING["height"])])):
        points = [(middle.x + x, y, z) for x, y, z in corners]
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(points, [], [(0, 1, 2, 3)])
        layer = mesh.uv_layers.new(name="st")
        flat = [(x, y) if name == "floor" else (x, z) for x, y, z in points]
        layer.data.foreach_set("uv", np.asarray(flat, dtype=np.float32).ravel() / tile)
        mesh.materials.append(blender_face.library_material(library, surfaces[name]))
        item = bpy.data.objects.new(name, mesh)
        bpy.context.scene.collection.objects.link(item)
        found.append(item)
    return found


def daylight(aim, heading):
    """The sun SUN off the camera's heading and a pale sky, in place of the studio's lamps and grey sky."""
    data = bpy.data.lights.new("sun", "SUN")
    data.energy, data.angle = SUN["watts"], math.radians(SUN["angle"])
    item = bpy.data.objects.new("sun", data)
    bpy.context.scene.collection.objects.link(item)
    placed(item, SUN, aim, heading, 10.0)
    background = bpy.context.scene.world.node_tree.nodes["Background"]
    background.inputs["Color"].default_value = (*DAY_SKY, 1.0)
    background.inputs["Strength"].default_value = DAY_STRENGTH


def lamp(name, spec):
    data = bpy.data.lights.new(name, "AREA")
    data.size, data.energy = spec["size"], spec["watts"]
    item = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(item)
    return item


def placed(item, spec, aim, heading, reach):
    """The lamp `spec` turn degrees off the camera's heading (radians round the person) and rise degrees up, aimed at
    `aim`."""
    angle = heading + math.radians(spec["turn"])
    rise = math.radians(spec["rise"])
    item.location = aim + Vector((math.sin(angle) * math.cos(rise), -math.cos(angle) * math.cos(rise),
                                  math.sin(rise))) * reach
    item.rotation_euler = (aim - item.location).to_track_quat("-Z", "Y").to_euler()


def sky():
    world = bpy.data.worlds.new("studio")
    world.use_nodes = True
    background = world.node_tree.nodes["Background"]
    background.inputs["Color"].default_value = (*SKY, 1.0)
    background.inputs["Strength"].default_value = SKY_STRENGTH
    bpy.context.scene.world = world


def dressed(items, subdivided, thick, cloth):
    """Every mesh piece subdivided once (smooth skin and cloth), the `cloth` pieces given their thickness."""
    for item in items:
        if item.type != "MESH":
            continue
        if item.name in cloth:
            solid = item.modifiers.new("thickness", "SOLIDIFY")
            solid.thickness, solid.offset = thick, 1.0
        if subdivided and len(item.data.polygons) > 200:
            surface = item.modifiers.new("smooth", "SUBSURF")
            surface.levels = surface.render_levels = 1


def bounds(items):
    low, high = Vector((1e9,) * 3), Vector((-1e9,) * 3)
    for item in items:
        if item.type != "MESH":
            continue
        for corner in item.bound_box:
            point = item.matrix_world @ Vector(corner)
            low = Vector(map(min, low, point))
            high = Vector(map(max, high, point))
    return low, high


def main(scene_path, library, out):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene_file = dict(np.load(scene_path, allow_pickle=False))
    items = [blender_face.strands_object(scene_file, str(piece), library) if f"{piece}.counts" in scene_file else
             blender_face.piece_object(scene_file, str(piece), library, []) for piece in scene_file["pieces"]]
    dressed(items, bool(scene_file["subdivided"]), float(scene_file["thick"]),
            {str(name) for name in scene_file["cloth"]})
    low, high = bounds([item for item in items if item.name == "skin"])
    middle = (low + high) / 2.0
    backdrop(library, middle)
    sky()
    blender_face.renderer()
    render = bpy.context.scene
    render.cycles.samples = SAMPLES
    render.render.resolution_x, render.render.resolution_y = SIZE
    camera = bpy.data.objects.new("camera", bpy.data.cameras.new("camera"))
    camera.data.lens = LENS_MM
    camera.data.sensor_fit = "VERTICAL"
    render.collection.objects.link(camera)
    render.camera = camera
    tall = (high.z - 0.0) * MARGIN
    distance = tall / 2.0 / math.tan(camera.data.angle_y / 2.0)
    lamps = []
    for name, spec in (("key", KEY), ("fill", FILL), ("rim", RIM)):
        lamps.append(lamp(name, spec))
        placed(lamps[-1], spec, Vector((middle.x, middle.y, high.z * 0.55)), 0.0, 3.5)
    camera.location = Vector((middle.x, middle.y - distance, EYE_HEIGHT))
    camera.rotation_euler = (Vector((middle.x, middle.y, high.z * 0.5)) - camera.location).to_track_quat(
        "-Z", "Y").to_euler()
    turntable = bpy.data.objects.new("turntable", None)
    render.collection.objects.link(turntable)
    turntable.location = Vector((middle.x, middle.y, 0.0))
    for item in items:
        item.parent = turntable
        item.matrix_parent_inverse = turntable.matrix_world.inverted()
    pathlib.Path(out).mkdir(parents=True, exist_ok=True)
    views = json.loads(str(scene_file["views"]))
    for view, degrees in views.items():
        drawn(render, turntable, degrees, out, f"{scene_file['name']}-{view}")
    face_middle = Vector((middle.x, middle.y, high.z - FACE_FRAME_M * 0.42))
    full = (camera.location.copy(), camera.rotation_euler.copy())
    camera.location = face_middle + Vector((0.0, -FACE_FRAME_M / 2.0 / math.tan(camera.data.angle_y / 2.0), 0.0))
    camera.rotation_euler = (face_middle - camera.location).to_track_quat("-Z", "Y").to_euler()
    drawn(render, turntable, FACE_TURN, out, f"{scene_file['name']}-face")
    camera.location, camera.rotation_euler = full
    surfaces = json.loads(str(scene_file["setting"]))
    for item in [*lamps, *[item for item in render.objects if item.name == "backdrop"]]:
        bpy.data.objects.remove(item)
    setting(library, middle, surfaces)
    daylight(Vector((middle.x, middle.y, high.z * 0.55)), 0.0)
    drawn(render, turntable, views[SETTING_VIEW], out, f"{scene_file['name']}-setting")


def drawn(render, turntable, degrees, out, name):
    """The person turned `degrees` from the camera, drawn to <out>/<name>.png."""
    turntable.rotation_euler = (0.0, 0.0, -math.radians(degrees))
    render.render.filepath = str(pathlib.Path(out) / f"{name}.png")
    bpy.ops.render.render(write_still=True)
    print(f"drew {name}", flush=True)


if __name__ == "__main__":
    main(*arguments())
