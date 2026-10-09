"""Runs in Blender (on a rented machine, blender_cloud.py): one animal from its model to its rigged, animated files.

    blender -b --python tools/characters/animals/blender_rig.py -- <job.json>

The job (written by route.py):
    {"name": "fish_tang", "body": "fish" | "quadruped", "model": "<finished or UniRig-rigged .glb>",
     "rig": "spine" | "unirig", "length_m": 0.2, "clips": ["swim", ...], "out": "<folder>",
     "lods": [["lod1", 0.15, 512], ["lod2", 400, 128]]}

The model is stood with its head towards glTF's +z (Blender's -y) and z up, scaled to `length_m` from snout to tail,
and set on its node: a fish centred on it, a land animal standing on it. Then it is rigged (rig_fish.py: a spine made
here, or the UniRig skeleton's root-to-tail chain; rig_quadruped.py: the UniRig skeleton), its clips are keyed at
30 frames a second, and it is written as <out>/<name>.glb with every clip, and its lighter copies as
<out>/lods/<name>-<lod>.glb (a share of the triangles, or a count when the number is above 1, and its pictures at
most the given pixels across). <out>/rig.json says
what was found and made.
"""
import json
import pathlib
import sys

import bpy
import numpy as np
from mathutils import Matrix, Vector

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import legs  # noqa: E402
import rig_fish  # noqa: E402
import rig_quadruped  # noqa: E402
import spine  # noqa: E402

RATE = 30
UP = (0.0, 0.0, 1.0)
# The way a character faces in its file: glTF's +z, which is Blender's -y.
FACING = Vector((0.0, -1.0, 0.0))


def clear_scene():
    """An empty scene at RATE frames a second."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = RATE


def import_model(path):
    """The model's mesh objects and its armature (None when it has none)."""
    bpy.ops.import_scene.gltf(filepath=str(path))
    armatures = [thing for thing in bpy.context.scene.objects if thing.type == "ARMATURE"]
    armature = armatures[0] if armatures else None
    # A rigged file brings a mesh of the importer's own to draw bones with; only the meshes the armature moves count.
    meshes = [thing for thing in bpy.context.scene.objects
              if thing.type == "MESH" and (armature is None or thing.find_armature() == armature)]
    if not meshes:
        raise RuntimeError(f"{path}: no mesh")
    return meshes, armature


def world_points(meshes):
    """Every vertex of the meshes in world space, as an array."""
    found = []
    for mesh in meshes:
        matrix = np.array(mesh.matrix_world)
        local = np.array([vertex.co for vertex in mesh.data.vertices])
        found.append(local @ matrix[:3, :3].T + matrix[:3, 3])
    return np.vstack(found)


def facing_of(body, points):
    """Which level way the animal's head points: a fish's thicker end, a land animal's higher one."""
    if body == "fish":
        return spine.body_axes(points, UP)["along"]
    return legs.forward_axis(points, UP)


def stand(things, body, length):
    """Turn the objects together so the head faces FACING, scale them to `length` along it, and set them on the node:
    a fish's middle on it, a land animal's lowest point on it; the transforms are applied, so the rest pose is the
    file's. Returns the scale used."""
    meshes = [thing for thing in things if thing.type == "MESH"]
    points = world_points(meshes)
    facing = Vector(facing_of(body, points))
    turn = facing.to_track_quat("-Y", "Z").to_matrix().to_4x4().inverted()
    turned = points @ np.array(turn)[:3, :3].T
    scale = length / (turned[:, 1].max() - turned[:, 1].min())
    turned *= scale
    middle = (turned.max(axis=0) + turned.min(axis=0)) / 2
    floor = middle[2] if body == "fish" else turned[:, 2].min()
    shift = Matrix.Translation(Vector((-middle[0], -middle[1], -floor)))
    whole = shift @ Matrix.Scale(scale, 4) @ turn
    roots = [thing for thing in things if thing.parent is None or thing.parent not in things]
    for root in roots:
        root.matrix_world = whole @ root.matrix_world
    bpy.ops.object.select_all(action="DESELECT")
    for thing in things:
        thing.select_set(True)
    bpy.context.view_layer.objects.active = things[0]
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    return scale


def triangles(meshes):
    """How many triangles the meshes have."""
    return sum(sum(len(polygon.vertices) - 2 for polygon in mesh.data.polygons) for mesh in meshes)


def export(path, armature, meshes):
    """The armature, its meshes and every clip as one glTF binary, each clip on its own frames from zero."""
    bpy.ops.object.select_all(action="DESELECT")
    for thing in [armature, *meshes]:
        thing.select_set(True)
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=str(path), export_format="GLB", use_selection=True,
                              export_animation_mode="ACTIONS", export_force_sampling=True,
                              export_optimize_animation_size=False, export_anim_slide_to_zero=True,
                              export_def_bones=True, export_skins=True, export_yup=True)


def decimated(meshes, target, total):
    """Copies of the meshes thinned by collapse to `target`: a share of the triangles when it is 1 or less, else a
    triangle count over all of them."""
    share = target if target <= 1 else min(1.0, target / max(total, 1))
    copies = []
    for mesh in meshes:
        copy = mesh.copy()
        copy.data = mesh.data.copy()
        bpy.context.scene.collection.objects.link(copy)
        thinning = copy.modifiers.new("thin", "DECIMATE")
        thinning.ratio = share
        bpy.context.view_layer.objects.active = copy
        bpy.ops.object.select_all(action="DESELECT")
        copy.select_set(True)
        bpy.ops.object.modifier_move_to_index(modifier="thin", index=0)
        bpy.ops.object.modifier_apply(modifier="thin")
        copies.append(copy)
    return copies


def smaller_pictures(copies, side):
    """Give the copies their own materials whose pictures are at most `side` pixels across: a far copy drawn a few
    pixels high needs no 2048 map, and a school of fish loads it hundreds of times."""
    for copy in copies:
        for slot in copy.material_slots:
            if slot.material is None or not slot.material.use_nodes:
                continue
            slot.material = slot.material.copy()
            for node in slot.material.node_tree.nodes:
                if node.type == "TEX_IMAGE" and node.image is not None and max(node.image.size) > side:
                    picture = node.image.copy()
                    picture.scale(*(max(1, round(length * side / max(node.image.size))) for length in node.image.size))
                    node.image = picture


def write_lods(job, armature, meshes, report):
    """The lighter copies, each exported with the same skeleton and clips, then dropped from the scene."""
    total = triangles(meshes)
    report["lods"] = {"lod0": total}
    for name, target, side in job.get("lods", []):
        for mesh in meshes:
            mesh.hide_set(True)
        copies = decimated(meshes, target, total)
        smaller_pictures(copies, side)
        export(pathlib.Path(job["out"]) / "lods" / f"{job['name']}-{name}.glb", armature, copies)
        report["lods"][name] = triangles(copies)
        for copy in copies:
            bpy.data.objects.remove(copy)
        for mesh in meshes:
            mesh.hide_set(False)


def main():
    job = json.loads(pathlib.Path(sys.argv[sys.argv.index("--") + 1]).read_text())
    out = pathlib.Path(job["out"])
    out.mkdir(parents=True, exist_ok=True)
    clear_scene()
    meshes, armature = import_model(job["model"])
    things = meshes + ([armature] if armature else [])
    report = {"name": job["name"], "body": job["body"], "rig": job["rig"],
              "scale": stand(things, job["body"], job["length_m"])}
    if job["body"] == "fish":
        armature = rig_fish.rig(meshes, armature, job, report)
    else:
        armature = rig_quadruped.rig(meshes, armature, job, report)
    export(out / f"{job['name']}.glb", armature, meshes)
    write_lods(job, armature, meshes, report)
    (out / "rig.json").write_text(json.dumps(report, indent=1))
    print(json.dumps(report))


if __name__ == "__main__":
    main()
