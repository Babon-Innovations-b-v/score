"""Inside Blender (5.x, Cycles on the card): a whole person's head and hair (`../whole`'s scene.npz) drawn close from
every side, in the whole person's own setting, lens and meter (`../whole/render.py`): the hair's check pictures.

    blender -b --python heads.py -- <scene.npz> <library folder> <out folder>

Writes <out>/<name>-head-<view>.png for each of VIEWS: the front, three quarters, the side and the back at the
head's height, and from above (the parting, the whorl and the crown, where round 1 showed bald strips; 2026-11-26).
A check picture, never one that ships: SIZE and SAMPLES are a check's.
"""
import json
import math
import pathlib
import sys

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "whole"))
import render  # noqa: E402  (the whole person's setting, lens, meter and pieces, one way of drawing them)

# Each view: (degrees the person turns from the camera, degrees the camera rises over the head's middle).
VIEWS = {"front": (0.0, 5.0), "three_quarter": (35.0, 8.0), "side": (90.0, 5.0), "back": (180.0, 8.0),
         "above": (20.0, 75.0)}
FRAME_M = 0.34  # the frame's height: the head, the bob's ends and the neck's top
SIZE = (1200, 1200)
SAMPLES = 256
FSTOP = 8.0


def head_middle(skin, high):
    """The head's middle: the mean of the skin's points in the top 0.22 m (x, y), its height half way down them."""
    points = np.array([tuple(skin.matrix_world @ vertex.co) for vertex in skin.data.vertices])
    head = points[points[:, 2] > high.z - 0.22]
    return Vector((head[:, 0].mean(), head[:, 1].mean(), high.z - 0.11))


def main(scene_path, library, out):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene_file = dict(np.load(scene_path, allow_pickle=False))
    face = render.blender_face
    items = [face.strands_object(scene_file, str(piece), library) if f"{piece}.counts" in scene_file
             else face.piece_object(scene_file, str(piece), library, []) for piece in scene_file["pieces"]]
    render.dressed(items, bool(scene_file["subdivided"]), float(scene_file["thick"]),
                   {str(name) for name in scene_file["cloth"]})
    skin = next(item for item in items if item.name == "skin")
    low, high = render.bounds([skin])
    middle = (low + high) / 2.0
    exposure = render.place(library, middle, json.loads(str(scene_file["setting"])))
    scene = bpy.context.scene
    render.film(scene, exposure)
    scene.cycles.samples = SAMPLES
    scene.render.resolution_x, scene.render.resolution_y = SIZE
    scene.render.resolution_percentage = 100
    camera = render.camera_made(scene)
    head = head_middle(skin, high)
    turntable = bpy.data.objects.new("turntable", None)
    scene.collection.objects.link(turntable)
    turntable.location = Vector((head.x, head.y, 0.0))
    bpy.context.view_layer.update()
    for item in items:
        item.parent = turntable
        item.matrix_parent_inverse = turntable.matrix_world.inverted()
    pathlib.Path(out).mkdir(parents=True, exist_ok=True)
    distance = FRAME_M / 2.0 / math.tan(camera.data.angle_y / 2.0)
    for view, (degrees, rise) in VIEWS.items():
        lift = math.radians(rise)
        location = head + Vector((0.0, -distance * math.cos(lift), distance * math.sin(lift)))
        render.aimed(camera, location, head, FSTOP, head)
        render.drawn(scene, turntable, degrees, out, f"{scene_file['name']}-head-{view}")


if __name__ == "__main__":
    main(*render.arguments())
