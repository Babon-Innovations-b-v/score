"""Inside Blender (#226): a fitted face's pieces drawn close up in their score_lib finishes, one still a shot and view.

    blender -b --python blender_face.py -- <face.npz> <library folder> <out folder>

`face.npz` (`face.py` writes it): `pieces` (names), and for each piece `<piece>.points`, `<piece>.triangles`,
`<piece>.surfaces` (score_lib surface ids, one a finish the piece wears), `<piece>.finish` (each triangle's index into
them), optionally `<piece>.uv` (each triangle's three UV corners) and `<piece>.shapes` (one offset set per name in
`shape_names`), or for strands `<piece>.counts` (points a strand) and `<piece>.radius` (per point) in place of
triangles; `shots` a JSON list of {name, weights: {shape name: weight}}; `aim` and `eye_distance`. Each surface is
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
    material = bpy.data.materials[surface]
    record_path = found[-1].with_name("surface.json")
    record = json.loads(record_path.read_text()) if record_path.is_file() else {}
    if "subsurface" in record:
        light_through(material, record["subsurface"])
    if "detail" in record:
        grained(material, record["detail"])
    return material


def light_through(material, subsurface):
    """The record's light under the surface on the imported Principled BSDF: its weight, mean free paths (mm, the
    scene in metres), anisotropy, index and method."""
    principled = next(node for node in material.node_tree.nodes if node.type == "BSDF_PRINCIPLED")
    principled.subsurface_method = subsurface["method"]
    principled.inputs["Subsurface Weight"].default_value = subsurface["weight"]
    principled.inputs["Subsurface Radius"].default_value = subsurface["radius_mm"]
    principled.inputs["Subsurface Scale"].default_value = 0.001
    principled.inputs["Subsurface Anisotropy"].default_value = subsurface["anisotropy"]
    principled.inputs["Subsurface IOR"].default_value = subsurface["ior"]


def grain_texture(tree, kind, spacing, coordinates):
    """A Voronoi (pores) or noise texture whose cells or features are `spacing` metres apart on the object."""
    texture = tree.nodes.new("ShaderNodeTexVoronoi" if kind == "cells" else "ShaderNodeTexNoise")
    texture.inputs["Scale"].default_value = 1.0 / spacing
    if kind != "cells":
        texture.inputs["Detail"].default_value = 4.0
    tree.links.new(coordinates.outputs["Object"], texture.inputs["Vector"])
    return texture


def toned(tree, colour_socket, texture_output, share, towards):
    """The colour reaching `colour_socket` moved towards `towards` by up to `share` where the texture is high."""
    scaled = tree.nodes.new("ShaderNodeMath")
    scaled.operation = "MULTIPLY"
    scaled.inputs[1].default_value = share
    tree.links.new(texture_output, scaled.inputs[0])
    mix = tree.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    first, second = (next(socket for socket in mix.inputs if socket.name == name and socket.type == "RGBA")
                     for name in ("A", "B"))
    result = next(socket for socket in mix.outputs if socket.type == "RGBA")
    tree.links.new(scaled.outputs[0], mix.inputs["Factor"])
    link = colour_socket.links[0] if colour_socket.is_linked else None
    if link:
        tree.links.new(link.from_socket, first)
    else:
        first.default_value = colour_socket.default_value
    second.default_value = (*towards, 1.0)
    tree.links.new(result, colour_socket)


def grained(material, detail):
    """The record's grain on the imported material, on the object's own coordinates (the skin has no UVs): pores
    (Voronoi cells, the pits their edges' distance) and a fine grain bumped into the normal, blotches and freckles
    toning the base colour, the gloss spread by the blotches."""
    tree = material.node_tree
    principled = next(node for node in tree.nodes if node.type == "BSDF_PRINCIPLED")
    coordinates = tree.nodes.new("ShaderNodeTexCoord")
    normal = None
    for name in ("pores", "fine"):
        texture = grain_texture(tree, "cells" if name == "pores" else "noise", detail[name]["spacing_m"], coordinates)
        bump = tree.nodes.new("ShaderNodeBump")
        bump.inputs["Distance"].default_value = detail[name]["depth_m"]
        tree.links.new(texture.outputs["Distance" if name == "pores" else "Fac"], bump.inputs["Height"])
        if normal is not None:
            tree.links.new(normal, bump.inputs["Normal"])
        normal = bump.outputs["Normal"]
    tree.links.new(normal, principled.inputs["Normal"])
    for name in ("mottle", "freckles"):
        texture = grain_texture(tree, "noise", detail[name]["spacing_m"], coordinates)
        ramp = tree.nodes.new("ShaderNodeMapRange")
        ramp.inputs["From Min"].default_value, ramp.inputs["From Max"].default_value = (0.45, 0.75)
        tree.links.new(texture.outputs["Fac"], ramp.inputs["Value"])
        toned(tree, principled.inputs["Base Color"], ramp.outputs["Result"], detail[name]["share"],
              detail[name]["towards"])
        if name == "mottle":
            spread = tree.nodes.new("ShaderNodeMapRange")
            base = principled.inputs["Roughness"].default_value
            spread.inputs["To Min"].default_value = base - detail["roughness_spread"]
            spread.inputs["To Max"].default_value = base + detail["roughness_spread"]
            tree.links.new(texture.outputs["Fac"], spread.inputs["Value"])
            tree.links.new(spread.outputs["Result"], principled.inputs["Roughness"])


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


def library_colour(material):
    """The linear base colour of a library material as Blender's USD reader made it (its Principled BSDF's)."""
    principled = next(node for node in material.node_tree.nodes if node.type == "BSDF_PRINCIPLED")
    return tuple(principled.inputs["Base Color"].default_value)[:3]


def strands_material(library, surface):
    """The hair route's finish (#227): Cycles' Principled Hair BSDF in direct colouring, its colour the library
    surface's own. score_lib holds no hair recipe yet, so its roughness and coat are Blender's defaults."""
    name = f"{surface}.strands"
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    hair = bpy.data.materials.new(name)
    hair.use_nodes = True
    nodes = hair.node_tree.nodes
    nodes.remove(nodes["Principled BSDF"])
    bsdf = nodes.new("ShaderNodeBsdfHairPrincipled")
    bsdf.parametrization = "COLOR"
    bsdf.inputs["Color"].default_value = (*library_colour(library_material(library, surface)), 1.0)
    hair.node_tree.links.new(bsdf.outputs[0], nodes["Material Output"].inputs["Surface"])
    return hair


def strands_object(face, piece, library):
    """One piece of strands (`<piece>.counts`, points, radius) as a hair Curves object in the hair route's finish."""
    counts = face[f"{piece}.counts"].astype(np.int64)
    curves = bpy.data.hair_curves.new(piece)
    curves.add_curves(counts.tolist())
    curves.attributes["position"].data.foreach_set("vector", z_up(face[f"{piece}.points"]).reshape(-1)
                                                   .astype(np.float32))
    if "radius" not in curves.attributes:
        curves.attributes.new("radius", "FLOAT", "POINT")
    curves.attributes["radius"].data.foreach_set("value", face[f"{piece}.radius"].astype(np.float32))
    curves.materials.append(strands_material(library, str(face[f"{piece}.surfaces"][0])))
    item = bpy.data.objects.new(piece, curves)
    bpy.context.scene.collection.objects.link(item)
    return item


def strands_posed(item, face, shape_names, weights):
    """A strands object's points moved by the shot's weights: each point by its own offsets per control (they carry
    the skin or the lash card they are bound to)."""
    piece = item.name
    points = face[f"{piece}.points"].astype(np.float64).copy()
    for index, name in enumerate(shape_names):
        if weights.get(name, 0.0):
            points += float(weights[name]) * face[f"{piece}.shapes"][index]
    item.data.attributes["position"].data.foreach_set("vector", z_up(points).reshape(-1).astype(np.float32))
    item.data.update_tag()


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
    scene.cycles_curves.shape = "THICK"
    scene.render.resolution_x, scene.render.resolution_y = SIZE
    scene.render.film_transparent = False
    scene.view_settings.view_transform = "AgX"


def main(face_path, library, out):
    """Draw every shot from every view into `out` as <shot>-<view>.png."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    face = dict(np.load(face_path, allow_pickle=False))
    shape_names = [str(name) for name in face.get("shape_names", [])]
    items = [strands_object(face, str(piece), library) if f"{piece}.counts" in face else
             piece_object(face, str(piece), library, shape_names) for piece in face["pieces"]]
    aim, distance = Vector(z_up(face["aim"]).tolist()), float(face["eye_distance"])
    lights(aim, distance)
    look = camera(aim, distance)
    renderer()
    pathlib.Path(out).mkdir(parents=True, exist_ok=True)
    for shot in json.loads(str(face["shots"])):
        for item in items:
            if item.type == "CURVES":
                strands_posed(item, face, shape_names, shot["weights"])
            elif item.data.shape_keys:
                for key in item.data.shape_keys.key_blocks[1:]:
                    key.value = float(shot["weights"].get(key.name, 0.0))
        for view, degrees in VIEWS.items():
            look(degrees)
            bpy.context.scene.render.filepath = str(pathlib.Path(out) / f"{shot['name']}-{view}.png")
            bpy.ops.render.render(write_still=True)
            print(f"drew {shot['name']}-{view}")


if __name__ == "__main__":
    main(*arguments())
