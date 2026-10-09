"""Grey workbench stills of meshes stored as .npz (points in metres, y up, facing +z): the bald head the clay hair
picture is drawn over, and the hair's check views. Moved here from round three's npz_views.py (#100).

    blender -b -P blender_views.py -- <out prefix> <cx,cy,cz> <ortho size> <width>x<height> <azimuths> \
        <part.npz:grey> [<part.npz:grey> ...] [elev=<deg>]

Azimuth 0 looks at the front, 90 at the person's left side (+x), 180 the back. Writes
<prefix>_<azimuth>.png per azimuth. Studio light, black outline.
"""
import math
import sys

import bpy
import mathutils
import numpy as np

args = sys.argv[sys.argv.index("--") + 1:]
PREFIX = args[0]
CENTRE = [float(value) for value in args[1].split(",")]
SIZE = float(args[2])
WIDTH, HEIGHT = (int(value) for value in args[3].split("x"))
AZIMUTHS = [int(value) for value in args[4].split(",")]
ELEVATION = 0.0
PARTS = []
for item in args[5:]:
    if item.startswith("elev="):
        ELEVATION = float(item[5:])
    else:
        path, grey = item.rsplit(":", 1)
        PARTS.append((path, float(grey)))

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene


def to_blender(points):
    """y-up +z-forward metres to Blender's z-up: (x, y, z) -> (x, -z, y)."""
    return np.stack([points[:, 0], -points[:, 2], points[:, 1]], axis=1)


for index, (path, grey) in enumerate(PARTS):
    data = np.load(path, allow_pickle=True)
    mesh = bpy.data.meshes.new(f"m{index}")
    mesh.from_pydata(to_blender(data["points"]).tolist(), [], data["faces"].astype(int).tolist())
    mesh.update()
    for polygon in mesh.polygons:
        polygon.use_smooth = True
    material = bpy.data.materials.new(f"g{index}")
    material.diffuse_color = (grey, grey, grey, 1.0)
    mesh.materials.append(material)
    thing = bpy.data.objects.new(f"o{index}", mesh)
    scene.collection.objects.link(thing)

scene.render.engine = "BLENDER_WORKBENCH"
shading = scene.display.shading
shading.light = "STUDIO"
shading.color_type = "MATERIAL"
shading.show_object_outline = True
shading.object_outline_color = (0.0, 0.0, 0.0)
shading.show_backface_culling = False
scene.world = bpy.data.worlds.new("w")
scene.view_settings.view_transform = "Standard"

centre = mathutils.Vector(to_blender(np.array([CENTRE]))[0].tolist())
forward, left = mathutils.Vector((0, -1, 0)), mathutils.Vector((1, 0, 0))
for azimuth in AZIMUTHS:
    turn, lift = math.radians(azimuth), math.radians(ELEVATION)
    direction = (forward * math.cos(turn) + left * math.sin(turn)) * math.cos(lift)
    direction.z = math.sin(lift)
    data = bpy.data.cameras.new(f"c{azimuth}")
    data.type, data.ortho_scale, data.clip_start, data.clip_end = "ORTHO", SIZE, 0.05, 10.0
    cam = bpy.data.objects.new(f"c{azimuth}", data)
    scene.collection.objects.link(cam)
    cam.location = centre + direction * 3.0
    cam.rotation_euler = (-direction).to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam
    scene.render.resolution_x, scene.render.resolution_y = WIDTH, HEIGHT
    scene.render.filepath = f"{PREFIX}_{azimuth:03d}.png"
    bpy.ops.render.render(write_still=True)
print("VIEWS", PREFIX, AZIMUTHS)
