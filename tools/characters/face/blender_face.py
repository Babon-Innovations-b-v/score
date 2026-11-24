"""Inside Blender (#226): a fitted face's pieces drawn close up in their score_lib finishes, one still a shot and view.

    blender -b --python blender_face.py -- <face.npz> <library folder> <out folder>

`face.npz` (`face.py` writes it): `pieces` (names), and for each piece `<piece>.points`, `<piece>.triangles`,
`<piece>.surfaces` (score_lib surface ids, one a finish the piece wears), `<piece>.finish` (each triangle's index into
them), optionally `<piece>.uv` (each triangle's three UV corners) and `<piece>.shapes` (one offset set per name in
`shape_names`); `shots` a JSON list of {name, weights: {shape name: weight}}; `aim` and `eye_distance`. Each surface is
the library entry's own material.usda (`<library folder>/surface/<id>/<version>/material.usda`, as place_build's fetch
lays it), imported by Blender's USD reader with its maps, nothing set by hand. Cycles on the card (`FARM_CYCLES_GPU=1`).
"""
import json
import math
import os
import pathlib
import sys

import bpy
import numpy as np
from mathutils import Vector

VIEWS = {"front": 0.0, "three_quarter": 35.0}  # the camera's turn about the head's upright, degrees
LENS_MM = 85.0  # a portrait lens
SIZE = (1024, 1280)
SAMPLES = 256


def arguments():
    """The script's own arguments, after Blender's `--`."""
    return sys.argv[sys.argv.index("--") + 1:]


def library_material(library, surface):
    """The score_lib surface's own material, imported once from its material.usda."""
    if surface in bpy.data.materials:
        return bpy.data.materials[surface]
    found = sorted((pathlib.Path(library) / "surface" / surface).glob("*/material.usda"))
    if not found:
        raise FileNotFoundError(f"score_lib surface {surface} is not fetched under {library}")
    bpy.ops.wm.usd_import(filepath=str(found[-1]), import_all_materials=True)
    if surface not in bpy.data.materials:
        raise RuntimeError(f"{found[-1]} imported no material named {surface}")
    return bpy.data.materials[surface]


def z_up(points):
    """Points of the face's frame (y up, the face looking along +z) in Blender's (z up, the face looking along -y)."""
    return np.stack([points[..., 0], -points[..., 2], points[..., 1]], axis=-1)


def piece_object(face, piece, library, shape_names):
    """One piece as a smooth-shaded mesh with its finishes, its UVs (layer `st`, the library's) and its shapes."""
    points = z_up(face[f"{piece}.points"])
    triangles = face[f"{piece}.triangles"]
    mesh = bpy.data.meshes.new(piece)
    mesh.from_pydata([tuple(point) for point in points], [], [tuple(int(corner) for corner in triangle)
                                                             for triangle in triangles])
    for surface in face[f"{piece}.surfaces"]:
        mesh.materials.append(library_material(library, str(surface)))
    mesh.polygons.foreach_set("material_index", face[f"{piece}.finish"].astype(np.int32))
    mesh.polygons.foreach_set("use_smooth", np.ones(len(triangles), dtype=bool))
    if f"{piece}.uv" in face:
        layer = mesh.uv_layers.new(name="st")
        layer.data.foreach_set("uv", face[f"{piece}.uv"].reshape(-1).astype(np.float32))
    mesh.update()
    item = bpy.data.objects.new(piece, mesh)
    bpy.context.scene.collection.objects.link(item)
    if f"{piece}.shapes" in face:
        item.shape_key_add(name="rest")
        for name, offsets in zip(shape_names, face[f"{piece}.shapes"]):
            key = item.shape_key_add(name=str(name))
            key.data.foreach_set("co", (points + z_up(offsets)).reshape(-1).astype(np.float32))
    return item


def lights(aim, distance):
    """A plain portrait light: a large soft key above and to one side, a fill, a rim behind, a grey world."""
    world = bpy.data.worlds.new("grey")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.18, 0.18, 0.18, 1.0)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.35
    bpy.context.scene.world = world
    for name, (around, up, power, size) in {"key": (40.0, 25.0, 60.0, 0.8), "fill": (-50.0, 5.0, 18.0, 1.2),
                                            "rim": (160.0, 30.0, 40.0, 0.6)}.items():
        light = bpy.data.lights.new(name, "AREA")
        light.energy, light.size = power, size
        item = bpy.data.objects.new(name, light)
        bpy.context.scene.collection.objects.link(item)
        reach = distance * 2.0
        turn, lift = math.radians(around), math.radians(up)
        item.location = aim + Vector((reach * math.sin(turn) * math.cos(lift), -reach * math.cos(turn) * math.cos(lift),
                                      reach * math.sin(lift)))
        item.rotation_euler = (aim - item.location).to_track_quat("-Z", "Y").to_euler()


def camera(aim, distance):
    """The portrait camera, aimed at the face's middle; `look` turns it about the head's upright."""
    item = bpy.data.objects.new("camera", bpy.data.cameras.new("camera"))
    item.data.lens = LENS_MM
    item.data.clip_start = 0.01
    bpy.context.scene.collection.objects.link(item)
    bpy.context.scene.camera = item

    def look(degrees):
        turn = math.radians(degrees)
        item.location = aim + Vector((distance * math.sin(turn), -distance * math.cos(turn), 0.0))
        item.rotation_euler = (aim - item.location).to_track_quat("-Z", "Y").to_euler()

    return look


def on_card(scene):
    """Cycles on the card: OptiX, else CUDA (usd_views.cycles_on_card's order); refused when neither is there."""
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
    raise RuntimeError("FARM_CYCLES_GPU is set but Cycles finds no OptiX or CUDA card")


def renderer():
    """Cycles on the card when the run says so, the still's size and samples."""
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = SAMPLES
    scene.cycles.use_denoising = True
    if os.environ.get("FARM_CYCLES_GPU") == "1":
        on_card(scene)
    scene.render.resolution_x, scene.render.resolution_y = SIZE
    scene.render.film_transparent = False
    scene.view_settings.view_transform = "AgX"


def main(face_path, library, out):
    """Draw every shot from every view into `out` as <shot>-<view>.png."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    face = dict(np.load(face_path, allow_pickle=False))
    shape_names = [str(name) for name in face.get("shape_names", [])]
    items = [piece_object(face, str(piece), library, shape_names) for piece in face["pieces"]]
    aim, distance = Vector(z_up(face["aim"]).tolist()), float(face["eye_distance"])
    lights(aim, distance)
    look = camera(aim, distance)
    renderer()
    pathlib.Path(out).mkdir(parents=True, exist_ok=True)
    for shot in json.loads(str(face["shots"])):
        for item in items:
            if item.data.shape_keys:
                for key in item.data.shape_keys.key_blocks[1:]:
                    key.value = float(shot["weights"].get(key.name, 0.0))
        for view, degrees in VIEWS.items():
            look(degrees)
            bpy.context.scene.render.filepath = str(pathlib.Path(out) / f"{shot['name']}-{view}.png")
            bpy.ops.render.render(write_still=True)
            print(f"drew {shot['name']}-{view}")


if __name__ == "__main__":
    main(*arguments())
