"""Inside Blender (5.x, Cycles on the card): a whole person (`__main__`'s scene.npz) drawn as a daylight photograph
from every side, each piece in its score_lib finish.

    blender -b --python render.py -- <scene.npz> <library folder> <out folder>

scene.npz is face/blender_face.py's piece format (`pieces`, and per piece its points, triangles, surfaces, finish,
uv or strands' counts and radius; y up), with `views` (JSON: {name: degrees round the person from its front}),
`name` (the pose's), `cloth` (the garments' pieces), `subdivided` / `thick` (the pieces drawn subdivided once,
and the cloth pieces given their thickness, m) and `setting` ({"floor", "wall"}: library surfaces). Each surface is
the library entry's own material.usda through Blender's USD reader (`blender_face.library_material`); hair, brows
and lashes in the hair route's Principled Hair BSDF.

The light (owner, 2026-11-25: the white studio read flat and overexposed): one real setting, a concrete floor running
to a concrete wall behind, under Blender's physical sky (multiple scattering): the sun's disc, its direct light and
the blue sky it lights all from one sun, as outdoors in late morning; nothing else lights the person. The person is
turned on a turntable for each view, so the sun stays on the camera's left above and every side is lit alike. An
85 mm lens framing the whole person at chest height, AgX in its medium high contrast look, exposed by EXPOSURE.
Then close-ups of the face (the head filling the frame, from its front and three quarters, FACE_VIEWS) and the setting from further
back (SETTING_VIEW turned, the frame SETTING_MARGIN of the person's height). Writes <out>/<name>-<view>.png,
<out>/<name>-face-<view>.png and <out>/<name>-setting.png.
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
LOOK = "AgX - Medium High Contrast"
# The sun 40 degrees up, 50 degrees round to the camera's left from straight behind it: the face and the front lit,
# the shade side and the wall's cast shadow on the right. Blender's sky at strength 1 is the real sun's and sky's
# radiance, so the film is exposed down as a camera in daylight is (EXPOSURE stops).
SUN = {"turn": 50.0, "rise": 40.0, "strength": 1.0, "air": 1.0, "haze": 1.0}
EXPOSURE = -4.0
FACE_VIEWS = {"front": 0.0, "three_quarter": 35.0}  # the face's close-ups, degrees off its front
FACE_FRAME_M = 0.42  # the close-up's frame height: the head and the neck's top
SETTING_VIEW = "three_quarter"
SETTING_MARGIN = 1.9  # the setting's frame: the person and the floor and wall round her
SETTING = {"behind": 2.5, "width": 14.0, "height": 4.0, "tile_m": 1.5}


def arguments():
    return sys.argv[sys.argv.index("--") + 1:]


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


def daylight():
    """Blender's physical sky (multiple scattering: the sun's disc and the sky that sun lights) as the world, the sun
    SUN turn degrees round from behind the camera to its left and rise degrees up."""
    world = bpy.data.worlds.new("daylight")
    world.use_nodes = True
    nodes = world.node_tree.nodes
    sky = nodes.new("ShaderNodeTexSky")
    sky.sky_type = "MULTIPLE_SCATTERING"
    sky.sun_disc = True
    sky.sun_elevation = math.radians(SUN["rise"])
    # Blender's sun_rotation turns from +y anticlockwise seen from above; the camera looks along +y from -y.
    sky.sun_rotation = math.radians(180.0 - SUN["turn"])
    sky.air_density, sky.aerosol_density = SUN["air"], SUN["haze"]
    background = nodes["Background"]
    world.node_tree.links.new(sky.outputs["Color"], background.inputs["Color"])
    background.inputs["Strength"].default_value = SUN["strength"]
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


def framed(camera, middle, high, margin, height):
    """The camera back from the person's middle so the frame holds `margin` of its height, at `height`, aimed at its
    half height."""
    distance = high.z * margin / 2.0 / math.tan(camera.data.angle_y / 2.0)
    camera.location = Vector((middle.x, middle.y - distance, height))
    camera.rotation_euler = (Vector((middle.x, middle.y, high.z * 0.5)) - camera.location).to_track_quat(
        "-Z", "Y").to_euler()


def main(scene_path, library, out):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene_file = dict(np.load(scene_path, allow_pickle=False))
    items = [blender_face.strands_object(scene_file, str(piece), library) if f"{piece}.counts" in scene_file else
             blender_face.piece_object(scene_file, str(piece), library, []) for piece in scene_file["pieces"]]
    dressed(items, bool(scene_file["subdivided"]), float(scene_file["thick"]),
            {str(name) for name in scene_file["cloth"]})
    low, high = bounds([item for item in items if item.name == "skin"])
    middle = (low + high) / 2.0
    setting(library, middle, json.loads(str(scene_file["setting"])))
    daylight()
    blender_face.renderer()
    render = bpy.context.scene
    render.view_settings.look = LOOK
    render.view_settings.exposure = EXPOSURE
    render.cycles.samples = SAMPLES
    render.render.resolution_x, render.render.resolution_y = SIZE
    camera = bpy.data.objects.new("camera", bpy.data.cameras.new("camera"))
    camera.data.lens = LENS_MM
    camera.data.sensor_fit = "VERTICAL"
    render.collection.objects.link(camera)
    render.camera = camera
    framed(camera, middle, high, MARGIN, EYE_HEIGHT)
    turntable = bpy.data.objects.new("turntable", None)
    render.collection.objects.link(turntable)
    turntable.location = Vector((middle.x, middle.y, 0.0))
    # Its matrix_world is only its location once the scene is updated: read before, it was the identity and every
    # piece stood twice its distance off the turntable's middle, a walking person turned out of the side views.
    bpy.context.view_layer.update()
    for item in items:
        item.parent = turntable
        item.matrix_parent_inverse = turntable.matrix_world.inverted()
    pathlib.Path(out).mkdir(parents=True, exist_ok=True)
    views = json.loads(str(scene_file["views"]))
    for view, degrees in views.items():
        drawn(render, turntable, degrees, out, f"{scene_file['name']}-{view}")
    face_middle = Vector((middle.x, middle.y, high.z - FACE_FRAME_M * 0.42))
    camera.location = face_middle + Vector((0.0, -FACE_FRAME_M / 2.0 / math.tan(camera.data.angle_y / 2.0), 0.0))
    camera.rotation_euler = (face_middle - camera.location).to_track_quat("-Z", "Y").to_euler()
    for view, degrees in FACE_VIEWS.items():
        drawn(render, turntable, degrees, out, f"{scene_file['name']}-face-{view}")
    framed(camera, middle, high, SETTING_MARGIN, EYE_HEIGHT * 1.3)
    drawn(render, turntable, views[SETTING_VIEW], out, f"{scene_file['name']}-setting")


def drawn(render, turntable, degrees, out, name):
    """The person turned `degrees` from the camera, drawn to <out>/<name>.png."""
    turntable.rotation_euler = (0.0, 0.0, -math.radians(degrees))
    render.render.filepath = str(pathlib.Path(out) / f"{name}.png")
    bpy.ops.render.render(write_still=True)
    print(f"drew {name}", flush=True)


if __name__ == "__main__":
    main(*arguments())
