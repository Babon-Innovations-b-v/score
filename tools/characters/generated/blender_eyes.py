"""Inside Blender (Cycles on the CPU): a generated head drawn before and after its eyes are made real (`eyes.py`'s
eyes.npz), the whole route's photo way (`../whole/render.py`: the CC0 park sky as world and ground, the incident
meter's exposure and balance, 85 mm, its fall-off and grain), the bust stood at a person's height.

    blender -b --python blender_eyes.py -- <model.glb> <eyes.npz> <library> <height m> <samples> <out folder>

Writes <out>/before-face.png and before-eyes.png (the model as made), then pushes back and removes the painted eye's
floor, lays the
eyeballs, the cornea's shell and the lids' wet line, and writes after-face.png, after-eyes.png and
after-three_quarter.png. The eyes' close-up is EYES_FRAME_M tall at EYES_FSTOP, focused on the eyes' own surface (the
painted pupils before, the corneas after; gen2's focused on the face's front-most point near the eyes, the brow or the
nose's bridge, and blurred the man's eyes). The eyes wear the face module's score_lib eye finishes, the iris toned to
the photo's colour; the head keeps its own paint (data/checks/library-exceptions.json: a generated model keeps its
own paint).
"""
import math
import pathlib
import sys

import bpy
import numpy as np
from mathutils import Vector
from mathutils.kdtree import KDTree

MODEL, EYES, LIBRARY, HEIGHT, SAMPLES, OUT = sys.argv[sys.argv.index("--") + 1:]
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "whole"))
import render  # noqa: E402
import blender_face  # noqa: E402  (on the path render.py put it)

SETTING = {"sky": "polyhaven_cloudy_vondelpark"}
LIFT_M = 1.30  # the bust's bottom this high: its head at a standing person's height in the park's light
FACE_FRAME_M = 0.30
EYES_FRAME_M = 0.09
EYES_FSTOP = 11.0
THREE_QUARTER_DEGREES = 35.0
THREADS = 6
MATCH_M = 1e-6  # a removed triangle's centre found on the imported mesh within this (the model's units)
# Each piece's score_lib surfaces, by its `finish` index (face.py's own lists).
SURFACES = {"eyes": ["face_sclera", "face_iris_brown", "face_pupil"], "cornea": ["face_cornea", "face_eye_film"],
            "wet": ["face_tear_film"]}
IRIS_FIBRES = (0.24, 0.14, 0.07)  # the library iris's fibre colour (its record's `fibres.towards`), found by it


def imported():
    """The glb's one mesh, its holder scaled so the model is HEIGHT tall, centred, its bottom at LIFT_M."""
    bpy.ops.import_scene.gltf(filepath=MODEL)
    items = [item for item in bpy.context.scene.objects if item.type == "MESH"]
    if len(items) != 1:
        raise RuntimeError(f"{MODEL} imported {len(items)} meshes; a generated head is one")
    low, high = render.bounds(items)
    scale = float(HEIGHT) / (high.z - low.z)
    holder = bpy.data.objects.new("holder", None)
    bpy.context.scene.collection.objects.link(holder)
    for item in list(bpy.context.scene.objects):
        if item.parent is None and item is not holder:
            item.parent = holder
    holder.scale = (scale,) * 3
    holder.location = Vector((-(low.x + high.x) / 2 * scale, -(low.y + high.y) / 2 * scale, LIFT_M - low.z * scale))
    bpy.context.view_layer.update()
    return items[0], holder


def world_points(head, points):
    """Points of the model's own frame (glTF: y up, +z its front) in the scene, through the head's mesh frame."""
    local = blender_face.z_up(np.asarray(points, np.float64))
    return [head.matrix_world @ Vector(point.tolist()) for point in local]


def floor_pushed(head, moved_from, moved_to):
    """The painted eye's floor pushed back on the head: every mesh point at a `moved_from` point (the importer splits a
    point on a UV seam into several) moved to its `moved_to`; the count moved."""
    mesh = head.data
    tree = KDTree(len(mesh.vertices))
    for vertex in mesh.vertices:
        tree.insert(vertex.co, vertex.index)
    tree.balance()
    count = 0
    for start, end in zip(blender_face.z_up(np.asarray(moved_from, np.float64)),
                          blender_face.z_up(np.asarray(moved_to, np.float64))):
        found = tree.find_range(Vector(start.tolist()), MATCH_M)
        if not found:
            raise RuntimeError(f"a pushed point {start} is not on the mesh")
        for _, index, _ in found:
            mesh.vertices[index].co = Vector(end.tolist())
            count += 1
    mesh.update()
    return count


def floor_removed(head, centres):
    """The painted eye's floor inside the eyeballs taken off the head: its faces whose centres are the removed
    triangles' centres."""
    mesh = head.data
    tree = KDTree(len(mesh.polygons))
    for polygon in mesh.polygons:
        tree.insert(polygon.center, polygon.index)
    tree.balance()
    doomed = set()
    for centre in blender_face.z_up(np.asarray(centres, np.float64)):
        _, index, distance = tree.find(Vector(centre.tolist()))
        if distance < MATCH_M:
            doomed.add(index)
    if len(doomed) < len(centres):
        raise RuntimeError(f"{len(centres) - len(doomed)} of the {len(centres)} removed triangles are not on the mesh")
    import bmesh
    edit = bmesh.new()
    edit.from_mesh(mesh)
    edit.faces.ensure_lookup_table()
    bmesh.ops.delete(edit, geom=[edit.faces[index] for index in sorted(doomed)], context="FACES_ONLY")
    edit.to_mesh(mesh)
    edit.free()
    mesh.update()
    return len(doomed)


def iris_toned(material, colour):
    """A copy of the library iris toned to `colour` (linear): its fibres' mix starts at the colour and moves towards
    the colour scaled as the record's fibre colour is over its base colour."""
    toned = material.copy()
    toned.name = f"{material.name}_photo"
    principled = blender_face.principled_of(material)
    base = np.array(principled.inputs["Base Color"].default_value[:3])
    for node in toned.node_tree.nodes:
        if node.type != "MIX" or node.data_type != "RGBA":
            continue
        first, second = (next(socket for socket in node.inputs if socket.name == name and socket.type == "RGBA")
                         for name in ("A", "B"))
        if np.allclose(second.default_value[:3], IRIS_FIBRES, atol=1e-4):
            first.default_value = (*colour, 1.0)
            second.default_value = (*(np.asarray(colour) * np.asarray(IRIS_FIBRES) / np.maximum(base, 1e-6)), 1.0)
            return toned
    raise RuntimeError(f"{material.name} has no fibre mix towards {IRIS_FIBRES}; the iris record changed")


def laid(head, eyes):
    """The eyeballs, the cornea's shell and the wet line as pieces in the head's mesh frame, each in its library
    finishes, the iris toned to the photo's colour."""
    pieces = {}
    for name, surfaces in SURFACES.items():
        if not len(eyes[f"{name}.triangles"]):
            continue
        piece = {f"{name}.{field}": eyes[f"{name}.{field}"] for field in ("points", "triangles", "uv")
                 if f"{name}.{field}" in eyes}
        piece[f"{name}.finish"] = eyes.get(f"{name}.finish", np.zeros(len(eyes[f"{name}.triangles"]), np.int64))
        piece[f"{name}.surfaces"] = np.array(surfaces)
        item = blender_face.piece_object(piece, name, LIBRARY, [])
        item.parent = head
        pieces[name] = item
    eyeballs = pieces["eyes"].data.materials
    eyeballs[1] = iris_toned(eyeballs[1], np.asarray(eyes["iris"], np.float64))
    bpy.context.view_layer.update()
    return pieces


def shots(camera, turntable, aim, focus, prefix):
    """The face from the front and the eyes close up (landscape, focused on `focus`) into <OUT>/<prefix>-*.png."""
    scene = bpy.context.scene
    back = 1.0 / math.tan(camera.data.angle_y / 2.0) / 2.0
    render.aimed(camera, aim + Vector((0.0, -FACE_FRAME_M * back, 0.0)), aim, render.STOPS["face"], focus)
    render.drawn(scene, turntable, 0.0, OUT, f"{prefix}-face")
    if prefix == "after":
        render.drawn(scene, turntable, THREE_QUARTER_DEGREES, OUT, f"{prefix}-three_quarter")
    portrait = (scene.render.resolution_x, scene.render.resolution_y)
    scene.render.resolution_x, scene.render.resolution_y = portrait[1], portrait[0]
    render.aimed(camera, focus + Vector((0.0, -EYES_FRAME_M * back, 0.0)), focus, EYES_FSTOP, focus)
    render.drawn(scene, turntable, 0.0, OUT, f"{prefix}-eyes")
    scene.render.resolution_x, scene.render.resolution_y = portrait


def staged(holder, middle):
    """The park's light, the film, the camera and a turntable under the holder; (camera, turntable)."""
    scene = bpy.context.scene
    render.film(scene, render.place(LIBRARY, middle, SETTING))
    scene.cycles.device = "CPU"
    scene.cycles.samples = int(SAMPLES)
    scene.render.threads_mode = "FIXED"
    scene.render.threads = THREADS
    camera = render.camera_made(scene)
    turntable = bpy.data.objects.new("turntable", None)
    scene.collection.objects.link(turntable)
    turntable.location = Vector((middle.x, middle.y, 0.0))
    bpy.context.view_layer.update()
    holder.parent = turntable
    holder.matrix_parent_inverse = turntable.matrix_world.inverted()
    return camera, turntable


def mean_point(points):
    """The mean of scene points."""
    return sum(points, Vector()) / len(points)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    eyes = dict(np.load(EYES, allow_pickle=False))
    head, holder = imported()
    low, high = render.bounds([head])
    camera, turntable = staged(holder, (low + high) / 2.0)
    painted = mean_point(world_points(head, eyes["painted_pupils"]))
    aim = painted + Vector((0.0, 0.0, -0.03))
    pathlib.Path(OUT).mkdir(parents=True, exist_ok=True)
    shots(camera, turntable, aim, painted, "before")
    print(f"pushed {floor_pushed(head, eyes['moved_from'], eyes['moved_to'])} painted points back", flush=True)
    print(f"removed {floor_removed(head, eyes['removed'])} painted triangles", flush=True)
    laid(head, eyes)
    shots(camera, turntable, aim, mean_point(world_points(head, eyes["cornea_apex"])), "after")
    print("EYES RENDER DONE", flush=True)


main()
