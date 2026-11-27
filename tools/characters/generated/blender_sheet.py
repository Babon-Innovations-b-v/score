"""Inside Blender (Cycles on the CPU): a generated person's head drawn twice, the raw model as made and the model with
its hair regrown as strands (`__main__`'s outputs), the whole route's photo way (`../whole/render.py`: the CC0 park
sky as world and ground, the incident meter's exposure and balance, 85 mm, its fall-off and grain; developed in
plain sRGB as `blender_eyes.py` develops the face): front, three
quarters, side, back and a close-up of the forehead's hairline.

    blender -b --python blender_sheet.py -- <model.glb> <groom folder> <library> <lift m> <samples> <out folder>

The model stands with its lowest point <lift m> over the ground (0 for a whole person, a bust at a standing person's
height). Writes <out>/raw-<view>.png (kept when all are there already: the raw model does not change) and
<out>/hair-<view>.png. The scalp wears the model's own skin colour darkened at
the roots and the strands the library's strand finish fitted to the paint (`fibre.py`), under the player models'
written exception (data/checks/library-exceptions.json: a generated model keeps its own paint).
"""
import json
import math
import pathlib
import sys

import bpy
import numpy as np
from mathutils import Vector

MODEL, GROOM, LIBRARY, LIFT, SAMPLES, OUT = sys.argv[sys.argv.index("--") + 1:][:6]  # `blender_lids.py` passes more
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "whole"))
import render  # noqa: E402
import blender_face  # noqa: E402  (on the path render.py put it)
import blender_eyes  # noqa: E402  (reads the same first six arguments; its VIEW: the face developed in plain sRGB)

SETTING = {"sky": "polyhaven_cloudy_vondelpark"}
VIEWS = {"front": 0.0, "three_quarter": 35.0, "side": 90.0, "back": 180.0}
SIZE = (960, 1200)
THREADS = 6
HEAD_FRAME = {"over_top_m": 0.04, "under_eyes_m": 0.34}  # each side view's frame, round the head
HAIRLINE = {"frame_m": 0.17, "over_eyes_m": 0.06, "behind_front_m": 0.04, "rise_deg": 12.0}
SKIN_ROUGHNESS = 0.45
WHITE_MELANIN = 0.02  # a white strand's melanin: a little, a hair is never clear glass
SEED = 223


def imported(path, holder):
    """A glb's meshes, its top objects parented to `holder`."""
    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    items = [item for item in bpy.context.scene.objects if item not in before]
    for item in items:
        if item.parent is None:
            item.parent = holder
    return [item for item in items if item.type == "MESH"]


def mesh_of(name, points, triangles, holder):
    """A mesh object from y-up points and triangles, parented to `holder`."""
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(blender_face.z_up(points).tolist(), [], triangles.tolist())
    mesh.shade_smooth()
    item = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(item)
    item.parent = holder
    return item


def painted(item, colours):
    """The mesh painted by its points' colours (sRGB), a skin's roughness."""
    attribute = item.data.color_attributes.new("paint", "FLOAT_COLOR", "POINT")
    linear = np.where(colours <= 0.04045, colours / 12.92, ((colours + 0.055) / 1.055) ** 2.4)
    rgba = np.concatenate([linear, np.ones((len(linear), 1))], axis=1).astype(np.float32)
    attribute.data.foreach_set("color", rgba.ravel())
    material = bpy.data.materials.new(f"{item.name}.paint")
    material.use_nodes = True
    principled = material.node_tree.nodes["Principled BSDF"]
    reader = material.node_tree.nodes.new("ShaderNodeVertexColor")
    reader.layer_name = "paint"
    material.node_tree.links.new(reader.outputs["Color"], principled.inputs["Base Color"])
    principled.inputs["Roughness"].default_value = SKIN_ROUGHNESS
    item.data.materials.append(material)


def strands_of(name, counts, points, radius, fibre, holder):
    """One hair Curves object in the fibre's Principled Hair BSDF, parented to `holder`."""
    curves = bpy.data.hair_curves.new(name)
    curves.add_curves(counts.tolist())
    curves.attributes["position"].data.foreach_set("vector", blender_face.z_up(points).reshape(-1)
                                                   .astype(np.float32))
    if "radius" not in curves.attributes:
        curves.attributes.new("radius", "FLOAT", "POINT")
    curves.attributes["radius"].data.foreach_set("value", radius.astype(np.float32))
    material = bpy.data.materials.new(f"{name}.fibre")
    material.use_nodes = True
    nodes = material.node_tree.nodes
    nodes.remove(nodes["Principled BSDF"])
    blender_face.fibred_hair(material, nodes.new("ShaderNodeBsdfHairPrincipled"), fibre)
    curves.materials.append(material)
    item = bpy.data.objects.new(name, curves)
    bpy.context.scene.collection.objects.link(item)
    item.parent = holder
    return item


def strand_pieces(name, counts, points, radius, block, holder):
    """The strands as hair Curves objects: the pigmented ones and, for a grey head, its `white_share` of white ones."""
    counts = counts.astype(np.int64)
    points = points.reshape(len(counts), -1, 3)
    radius = radius.reshape(len(counts), -1)
    white = np.random.default_rng(SEED).random(len(counts)) < block.get("white_share", 0.0)
    items = []
    for piece, chosen, finish in ((name, ~white, block), (f"{name}_white", white, dict(block, melanin=WHITE_MELANIN))):
        if chosen.any():
            items.append(strands_of(piece, counts[chosen], points[chosen].reshape(-1, 3), radius[chosen].ravel(),
                                    finish, holder))
    return items


def groomed(groom, fibre, holder):
    """The model without its hair (and beard), its scalp (the neck's back, the skin under the beard) and its strands:
    the objects."""
    items = imported(pathlib.Path(GROOM) / "kept.glb", holder)
    scalp = mesh_of("scalp", groom["scalp_points"], groom["scalp_triangles"], holder)
    painted(scalp, groom["scalp_colours"])
    items.append(scalp)
    if len(groom["neck_points"]):
        neck = mesh_of("neck", groom["neck_points"], groom["neck_triangles"], holder)
        painted(neck, np.tile(groom["skin_colour"], (len(groom["neck_points"]), 1)))
        items.append(neck)
    items += strand_pieces("hair", groom["counts"], groom["points"], groom["radius"], fibre["hair"], holder)
    if len(groom["beard_skin_points"]):
        skin = mesh_of("beard_skin", groom["beard_skin_points"], groom["beard_skin_triangles"], holder)
        painted(skin, groom["beard_skin_colours"])
        items.append(skin)
        items += strand_pieces("beard", groom["beard_counts"], groom["beard_points"], groom["beard_radius"],
                               fibre["beard"], holder)
    return items


def raw_model(groom, holder):
    """The raw model, scaled as `__main__` read it (to its height), under its own empty in `holder`."""
    raw = bpy.data.objects.new("raw", None)
    bpy.context.scene.collection.objects.link(raw)
    raw.parent = holder
    items = imported(MODEL, raw)
    bpy.context.view_layer.update()
    low, high = render.bounds(items)
    raw.scale = (float(groom["height"]) / (high.z - low.z),) * 3
    return items


def shown(items, visible):
    for item in items:
        item.hide_render = not visible


def head_aims(groom):
    """(the side views' aim and focus, the hairline close-up's aim) in Blender's frame, before the lift."""
    eyes = blender_face.z_up(np.asarray(groom["eyes"]).mean(axis=0)[None])[0]
    top = float(groom["top"])
    middle = (top + HEAD_FRAME["over_top_m"] + eyes[2] - HEAD_FRAME["under_eyes_m"]) / 2.0
    aim = Vector((eyes[0], eyes[1] + 0.06, middle))
    focus = Vector((eyes[0], eyes[1], eyes[2]))
    hairline = Vector((eyes[0], eyes[1] + HAIRLINE["behind_front_m"], eyes[2] + HAIRLINE["over_eyes_m"]))
    return aim, focus, hairline


def drawn_all(scene, camera, turntable, groom, lift, prefix):
    """The four sides and the hairline close-up, each to <out>/<prefix>-<view>.png."""
    aim, focus, hairline = head_aims(groom)
    aim, focus, hairline = (vector + Vector((0.0, 0.0, lift)) for vector in (aim, focus, hairline))
    frame_m = float(groom["top"]) + HEAD_FRAME["over_top_m"] - (blender_face.z_up(
        np.asarray(groom["eyes"]).mean(axis=0)[None])[0][2] - HEAD_FRAME["under_eyes_m"])
    distance = frame_m / 2.0 / math.tan(camera.data.angle_y / 2.0)
    render.aimed(camera, aim + Vector((0.0, -distance, 0.0)), aim, render.STOPS["face"], focus)
    for view, degrees in VIEWS.items():
        render.drawn(scene, turntable, degrees, OUT, f"{prefix}-{view}")
    distance = HAIRLINE["frame_m"] / 2.0 / math.tan(camera.data.angle_y / 2.0)
    lifted = math.radians(HAIRLINE["rise_deg"])
    location = hairline + Vector((0.0, -distance * math.cos(lifted), distance * math.sin(lifted)))
    render.aimed(camera, location, hairline, render.STOPS["hair"], hairline)
    render.drawn(scene, turntable, 0.0, OUT, f"{prefix}-hairline")


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    groom = dict(np.load(pathlib.Path(GROOM) / "groom.npz"))
    fibre = json.loads((pathlib.Path(GROOM) / "fibre.json").read_text())
    lift = float(LIFT) - float(groom["low"])
    eyes = blender_face.z_up(np.asarray(groom["eyes"]).mean(axis=0)[None])[0]
    turntable = bpy.data.objects.new("turntable", None)
    bpy.context.scene.collection.objects.link(turntable)
    turntable.location = Vector((eyes[0], eyes[1] + 0.08, 0.0))
    holder = bpy.data.objects.new("holder", None)
    bpy.context.scene.collection.objects.link(holder)
    holder.location = Vector((0.0, 0.0, lift))
    raw_items = raw_model(groom, holder)
    groom_items = groomed(groom, fibre, holder)
    bpy.context.view_layer.update()
    holder.parent = turntable
    holder.matrix_parent_inverse = turntable.matrix_world.inverted()
    scene = bpy.context.scene
    exposure = render.place(LIBRARY, Vector((eyes[0], eyes[1], lift)), SETTING)
    render.film(scene, exposure)
    scene.view_settings.view_transform, scene.view_settings.look = blender_eyes.VIEW
    scene.cycles.device = "CPU"
    scene.cycles.samples = int(SAMPLES)
    scene.render.threads_mode = "FIXED"
    scene.render.threads = THREADS
    scene.render.resolution_x, scene.render.resolution_y = SIZE
    scene.render.resolution_percentage = 100
    camera = render.camera_made(scene)
    pathlib.Path(OUT).mkdir(parents=True, exist_ok=True)
    shown(groom_items, False)
    if not all((pathlib.Path(OUT) / f"raw-{view}.png").exists() for view in (*VIEWS, "hairline")):
        drawn_all(scene, camera, turntable, groom, lift, "raw")
    shown(groom_items, True)
    shown(raw_items, False)
    drawn_all(scene, camera, turntable, groom, lift, "hair")
    print("SHEET RENDER DONE", flush=True)


if __name__ == "__main__":  # imported by `blender_lids.py`
    main()
