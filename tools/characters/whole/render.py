"""Inside Blender (5.x, Cycles on the card): a whole person (`__main__`'s scene.npz) drawn as a photograph taken in a
real place, from every side, each piece in its score_lib finish.

    blender -b --python render.py -- <scene.npz> <library folder> <out folder>

scene.npz is face/blender_face.py's piece format (`pieces`, and per piece its points, triangles, surfaces, finish,
uv or strands' counts and radius; y up), with `views` (JSON: {name: degrees round the person from its front}),
`name` (the pose's), `cloth` (the garments' pieces), `subdivided` / `thick` (the pieces drawn subdivided once,
and the cloth pieces given their thickness, m) and `setting` ({"sky": a score_lib light entry's id}: a photographed
sky and setting, an unclipped high-range panorama). Each surface is the library entry's own material.usda through
Blender's USD reader (`blender_face.library_material`); hair, brows and lashes in the hair route's Principled Hair BSDF.

Made like a photograph (owner, 2026-11-26: "photorealism is the goal"; 2026-11-25: the white studio read flat and
overexposed, and the bare concrete wall and floor that followed read as a backdrop, not a place):
- **A real place.** The library sky lights the person and is the background, as the place it was photographed in;
  the ground under her is that photograph's own ground laid on a plane (projected from where the panorama was taken,
  CAPTURE behind her, so its tripod spot stays hidden) and lit by the same sky, so it takes her shadow and her
  contact shade and meets the panorama at the horizon with no seam. Its albedo is the photograph's ground radiance over
  the ground's own irradiance from that sky (`meter.py`), so lit again it is the photograph.
- **Exposed and balanced by an incident meter.** The sky's illuminance on a card facing the camera at the person
  (`meter.py`) sets the exposure (an 18% grey card reads 18%) and the white balance (that card reads neutral), as a
  photographer meters at the subject; nothing is set by eye.
- **A real lens.** 85 mm on a full-frame sensor; the whole person's sides at f/4 focused on her, the face close-ups
  at f/5.6, the hair's at f/8; the lens's own fall-off at the corners (more wide open) and a fine film-like grain
  (`developed`); AgX in its medium high contrast look.
- **The photograph** (`PHOTO`): three quarters, the camera at her eye height, 85 mm at f/2 focused on her eyes, the
  whole person and a waist-up portrait, so the place falls away behind her as in a portrait taken outside.

The person is turned on a turntable for each view, so the sky's light stays where it is to the camera and every side
is lit alike. Writes <out>/<name>-<view>.png, <out>/<name>-face-<view>.png, <out>/<name>-hair-<view>.png,
<out>/<name>-setting.png and <out>/<name>-photo.png, <out>/<name>-photo-portrait.png. WHOLE_RENDER_CHECK=1 draws at
half size and fewer samples, for a quick check only (never a picture that ships).
"""
import json
import math
import os
import pathlib
import sys
import zlib

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "face"))
import blender_face  # noqa: E402  (the face's pieces, strands and library finishes, one way of drawing them)

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import meter  # noqa: E402  (the incident meter: exposure and white balance from the sky)

SIZE = (1200, 1800)
SAMPLES = 512
CHECK = os.environ.get("WHOLE_RENDER_CHECK") == "1"  # a quick check's picture: half size, CHECK_SAMPLES
CHECK_SAMPLES = 96
LENS_MM = 85.0
SENSOR_MM = (24.0, 36.0)  # a full-frame sensor held upright (width, height)
EYE_HEIGHT = 1.15  # m: the sides' camera at the person's chest
MARGIN = 1.18  # the frame's height over the person's
LOOK = "AgX - Medium High Contrast"
# Apertures (f-numbers): the sides, the face's close-ups, the hair's close-ups and the setting's view.
STOPS = {"side": 4.0, "face": 5.6, "hair": 8.0, "setting": 4.0}
# The photograph: three quarters round, the camera at the eyes, wide open; the whole person and a waist-up portrait
# (frame height over the person's height, or in m).
PHOTO = {"degrees": 35.0, "fstop": 2.0, "margin": 1.12, "portrait_m": 0.95}
EYES_UNDER_TOP_M = 0.115  # the eyes this far under the top of the head (an adult's)
FACE_VIEWS = {"front": 0.0, "three_quarter": 35.0}  # the face's close-ups, degrees off its front
FACE_FRAME_M = 0.42  # the close-up's frame height: the head and the neck's top
# The hair's close-ups (#227): the parting and the hairline, each (degrees off the face's front, degrees the camera
# rises over the head's top front), framed HAIR_FRAME_M high round the top of the forehead.
HAIR_VIEWS = {"parting-above": (0.0, 70.0), "hairline-front": (0.0, 12.0), "hairline-three_quarter": (35.0, 20.0)}
HAIR_FRAME_M = 0.17
HAIR_AIM_M = (0.03, 0.035)  # the aim behind the head's front and under its top (m)
SETTING_VIEW = "three_quarter"
SETTING_MARGIN = 1.9  # the setting's frame: the person and the place round her
# The sky turned SKY_TURN degrees (the park's: the path curving away behind her under autumn trees, no near trunk
# for the ground to flatten); the panorama taken CAPTURE (m) behind the person's middle, at a photographer's eye height.
SKY_TURN = 180.0
CAPTURE = {"behind": 1.5, "height": 1.7}
GROUND_HALF_M = 400.0  # the ground plane's half width: its far edge under the horizon by less than a pixel
METER_SIZE = (512, 256)  # the panorama read at this size for the meter
# The lens's fall-off (stops at the frame's corner: a little at any aperture, more wide open) and the grain (its
# spread at a linear value of 1, falling as the square root of the light, one grain for all three colours).
VIGNETTE = {"floor": 0.1, "per_stop": 1.2}
GRAIN = 0.006


def arguments():
    return sys.argv[sys.argv.index("--") + 1:]


def sky_path(library, sky):
    """The library light entry's panorama (its newest fetched version)."""
    found = sorted((pathlib.Path(library) / "light" / sky).glob("*/sky.exr"))
    if not found:
        raise FileNotFoundError(f"score_lib light {sky} is not fetched under {library}")
    return found[-1]


def metered(path):
    """{front, ground}: the sky's irradiance (linear RGB) on a card at the person facing the camera and on the level
    ground (`meter.metered`, the panorama read at METER_SIZE)."""
    image = bpy.data.images.load(str(path))
    image.scale(*METER_SIZE)
    pixels = np.empty(METER_SIZE[0] * METER_SIZE[1] * 4, dtype=np.float32)
    image.pixels.foreach_get(pixels)
    bpy.data.images.remove(image)
    return meter.metered(pixels.reshape(METER_SIZE[1], METER_SIZE[0], 4), SKY_TURN)


def sky_lookup(tree, vector_socket):
    """An Environment Texture node reading the panorama in the direction at `vector_socket`, turned by SKY_TURN."""
    mapping = tree.nodes.new("ShaderNodeMapping")
    mapping.vector_type = "VECTOR"
    mapping.inputs["Rotation"].default_value = (0.0, 0.0, math.radians(SKY_TURN))
    tree.links.new(vector_socket, mapping.inputs["Vector"])
    texture = tree.nodes.new("ShaderNodeTexEnvironment")
    tree.links.new(mapping.outputs["Vector"], texture.inputs["Vector"])
    return texture


def multiplied(tree, colour_socket, gains, clamp=False):
    """`colour_socket` times the RGB `gains` (clamped to 1 when `clamp`), its output socket."""
    mix = tree.nodes.new("ShaderNodeMix")
    mix.data_type, mix.blend_type, mix.clamp_result = "RGBA", "MULTIPLY", clamp
    mix.inputs["Factor"].default_value = 1.0
    tree.links.new(colour_socket, mix.inputs["A"])
    mix.inputs["B"].default_value = (*gains, 1.0)
    return mix.outputs["Result"]


def sky_world(image, balance):
    """The panorama as the world: it lights the person and is what lies behind her, white balanced by `balance`."""
    world = bpy.data.worlds.new("sky")
    world.use_nodes = True
    tree = world.node_tree
    coordinates = tree.nodes.new("ShaderNodeTexCoord")
    texture = sky_lookup(tree, coordinates.outputs["Generated"])
    texture.image = image
    tree.links.new(multiplied(tree, texture.outputs["Color"], balance), tree.nodes["Background"].inputs["Color"])
    bpy.context.scene.world = world


def ground(middle, image, found):
    """The photograph's own ground on a level plane: each point the panorama's colour in its direction from where the
    panorama was taken (CAPTURE behind the person), as a diffuse albedo that the same sky lights back to the
    photograph (radiance times pi over the ground's irradiance), so it takes the person's shadow."""
    capture = Vector((middle.x, middle.y + CAPTURE["behind"], CAPTURE["height"]))
    mesh = bpy.data.meshes.new("ground")
    half = GROUND_HALF_M
    mesh.from_pydata([(capture.x - half, capture.y - half, 0.0), (capture.x + half, capture.y - half, 0.0),
                      (capture.x + half, capture.y + half, 0.0), (capture.x - half, capture.y + half, 0.0)], [],
                     [(0, 1, 2, 3)])
    material = bpy.data.materials.new("ground")
    material.use_nodes = True
    tree = material.node_tree
    geometry = tree.nodes.new("ShaderNodeNewGeometry")
    offset = tree.nodes.new("ShaderNodeVectorMath")
    offset.operation = "SUBTRACT"
    tree.links.new(geometry.outputs["Position"], offset.inputs[0])
    offset.inputs[1].default_value = tuple(capture)
    way = tree.nodes.new("ShaderNodeVectorMath")
    way.operation = "NORMALIZE"
    tree.links.new(offset.outputs["Vector"], way.inputs[0])
    texture = sky_lookup(tree, way.outputs["Vector"])
    texture.image = image
    albedo = multiplied(tree, texture.outputs["Color"], math.pi / found["ground"], clamp=True)
    diffuse = tree.nodes.new("ShaderNodeBsdfDiffuse")
    tree.links.new(albedo, diffuse.inputs["Color"])
    tree.links.new(diffuse.outputs["BSDF"], tree.nodes["Material Output"].inputs["Surface"])
    tree.nodes.remove(tree.nodes["Principled BSDF"])
    mesh.materials.append(material)
    item = bpy.data.objects.new("ground", mesh)
    bpy.context.scene.collection.objects.link(item)
    return item


def place(library, middle, setting):
    """The real place: the library sky as the world and its ground under the person; the meter's exposure (stops)."""
    path = sky_path(library, setting["sky"])
    image = bpy.data.images.load(str(path))
    found = metered(path)
    sky_world(image, meter.balance_of(found))
    ground(middle, image, found)
    print(f"metered: front {found['front'].round(3).tolist()} ground {found['ground'].round(3).tolist()} "
          f"exposure {meter.exposure_of(found):+.2f} balance {meter.balance_of(found).round(3).tolist()}", flush=True)
    return meter.exposure_of(found)


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


def aimed(camera, location, aim, fstop, focus):
    """The camera at `location` looking at `aim`, at `fstop`, focused on the point `focus`."""
    camera.location = location
    camera.rotation_euler = (aim - location).to_track_quat("-Z", "Y").to_euler()
    camera.data.dof.use_dof = True
    camera.data.dof.aperture_fstop = fstop
    camera.data.dof.focus_distance = (focus - location).length


def framed(camera, middle, high, margin, height, fstop):
    """The camera back from the person's middle so the frame holds `margin` of its height, at `height`, aimed at its
    half height and focused on her middle."""
    distance = high.z * margin / 2.0 / math.tan(camera.data.angle_y / 2.0)
    aim = Vector((middle.x, middle.y, high.z * 0.5))
    aimed(camera, Vector((middle.x, middle.y - distance, height)), aim, fstop, aim)


def photo_framed(camera, middle, high, frame_m, bottom):
    """The photograph's camera at the person's eye height, back so the frame holds `frame_m` from `bottom` up, focused
    on her eyes (just in front of the head's middle)."""
    eyes = Vector((middle.x, middle.y - 0.08, high.z - EYES_UNDER_TOP_M))
    distance = frame_m / 2.0 / math.tan(camera.data.angle_y / 2.0)
    aim = Vector((middle.x, middle.y, bottom + frame_m / 2.0))
    aimed(camera, Vector((middle.x, middle.y - distance, eyes.z)), aim, PHOTO["fstop"], eyes)


def hair_framed(camera, skin, high, rise):
    """The camera `rise` degrees over the head's top front, from in front of the face, framing HAIR_FRAME_M round
    it."""
    points = np.array([tuple(skin.matrix_world @ vertex.co) for vertex in skin.data.vertices])
    head = points[points[:, 2] > high.z - 0.12]
    aim = Vector((head[:, 0].mean(), head[:, 1].min() + HAIR_AIM_M[0], high.z - HAIR_AIM_M[1]))
    distance = HAIR_FRAME_M / 2.0 / math.tan(camera.data.angle_y / 2.0)
    lift = math.radians(rise)
    location = aim + Vector((0.0, -distance * math.cos(lift), distance * math.sin(lift)))
    aimed(camera, location, aim, STOPS["hair"], aim)


def developed(path, fstop):
    """The drawn picture given its lens's fall-off to the corners (VIGNETTE: stops at the corner, more wide open) and
    a fine grain (GRAIN), both in linear light, written back over itself."""
    image = bpy.data.images.load(str(path))
    image.colorspace_settings.name = "Non-Color"  # its stored values, not decoded
    width, height = image.size
    pixels = np.empty(width * height * 4, dtype=np.float32)
    image.pixels.foreach_get(pixels)
    shown = pixels.reshape(height, width, 4)
    linear = np.where(shown[..., :3] <= 0.04045, shown[..., :3] / 12.92, ((shown[..., :3] + 0.055) / 1.055) ** 2.4)
    across, up = np.meshgrid(np.linspace(-1.0, 1.0, width) * width / math.hypot(width, height),
                             np.linspace(-1.0, 1.0, height) * height / math.hypot(width, height))
    corner = (across ** 2 + up ** 2) / (max(across.max(), 1e-9) ** 2 + max(up.max(), 1e-9) ** 2)
    linear = linear * (2.0 ** (-(VIGNETTE["floor"] + VIGNETTE["per_stop"] / fstop) * corner))[..., None]
    noise = np.random.default_rng(zlib.crc32(str(path).encode())).normal(0.0, 1.0, (height, width))
    linear = np.clip(linear + (GRAIN * np.sqrt(np.clip(linear.mean(axis=-1), 0.0, None)) * noise)[..., None], 0.0, 1.0)
    shown[..., :3] = np.where(linear <= 0.0031308, linear * 12.92, 1.055 * linear ** (1.0 / 2.4) - 0.055)
    image.pixels.foreach_set(shown.ravel())
    image.filepath_raw, image.file_format = str(path), "PNG"
    image.save()
    bpy.data.images.remove(image)


def camera_made(render):
    """An 85 mm lens on an upright full-frame sensor, the scene's camera."""
    camera = bpy.data.objects.new("camera", bpy.data.cameras.new("camera"))
    camera.data.lens = LENS_MM
    camera.data.sensor_fit = "VERTICAL"
    camera.data.sensor_width, camera.data.sensor_height = SENSOR_MM
    render.collection.objects.link(camera)
    render.camera = camera
    return camera


def film(render, exposure):
    """Cycles at the picture's size and samples (half and fewer for a check), AgX, exposed by the meter."""
    blender_face.renderer()
    render.view_settings.look = LOOK
    render.view_settings.exposure = exposure
    render.cycles.samples = CHECK_SAMPLES if CHECK else SAMPLES
    render.render.resolution_x, render.render.resolution_y = SIZE
    render.render.resolution_percentage = 50 if CHECK else 100


def main(scene_path, library, out):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene_file = dict(np.load(scene_path, allow_pickle=False))
    items = [blender_face.strands_object(scene_file, str(piece), library) if f"{piece}.counts" in scene_file else
             blender_face.piece_object(scene_file, str(piece), library, []) for piece in scene_file["pieces"]]
    dressed(items, bool(scene_file["subdivided"]), float(scene_file["thick"]),
            {str(name) for name in scene_file["cloth"]})
    skin = next(item for item in items if item.name == "skin")
    low, high = bounds([skin])
    middle = (low + high) / 2.0
    exposure = place(library, middle, json.loads(str(scene_file["setting"])))
    render = bpy.context.scene
    film(render, exposure)
    camera = camera_made(render)
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
    name = str(scene_file["name"])
    views = json.loads(str(scene_file["views"]))
    framed(camera, middle, high, MARGIN, EYE_HEIGHT, STOPS["side"])
    for view, degrees in views.items():
        drawn(render, turntable, degrees, out, f"{name}-{view}")
    photo_framed(camera, middle, high, high.z * PHOTO["margin"], high.z * (1.0 - PHOTO["margin"]) / 2.0)
    drawn(render, turntable, PHOTO["degrees"], out, f"{name}-photo")
    photo_framed(camera, middle, high, PHOTO["portrait_m"], high.z + 0.06 - PHOTO["portrait_m"])
    drawn(render, turntable, PHOTO["degrees"], out, f"{name}-photo-portrait")
    face_middle = Vector((middle.x, middle.y, high.z - FACE_FRAME_M * 0.42))
    location = face_middle + Vector((0.0, -FACE_FRAME_M / 2.0 / math.tan(camera.data.angle_y / 2.0), 0.0))
    aimed(camera, location, face_middle, STOPS["face"], face_middle + Vector((0.0, -0.08, 0.0)))
    for view, degrees in FACE_VIEWS.items():
        drawn(render, turntable, degrees, out, f"{name}-face-{view}")
    for view, (degrees, rise) in HAIR_VIEWS.items():
        turntable.rotation_euler = (0.0, 0.0, 0.0)
        bpy.context.view_layer.update()
        hair_framed(camera, skin, high, rise)
        drawn(render, turntable, degrees, out, f"{name}-hair-{view}")
    if SETTING_VIEW in views:
        framed(camera, middle, high, SETTING_MARGIN, EYE_HEIGHT * 1.3, STOPS["setting"])
        drawn(render, turntable, views[SETTING_VIEW], out, f"{name}-setting")


def drawn(render, turntable, degrees, out, name):
    """The person turned `degrees` from the camera, drawn to <out>/<name>.png and developed as its lens shows it."""
    turntable.rotation_euler = (0.0, 0.0, -math.radians(degrees))
    path = pathlib.Path(out) / f"{name}.png"
    render.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    developed(path, render.camera.data.dof.aperture_fstop)
    print(f"drew {name}", flush=True)


if __name__ == "__main__":
    main(*arguments())
