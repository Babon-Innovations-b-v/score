"""Runs inside Blender (on a rented card, tools/props/cloud/blender_cloud.py): a turntable of a raw Pixal3D model drawn
with its own texture and no light, for the finish-map method's view maps (../turntable_views.py, ../finish_parts.py).

    blender -b -P turntable.py -- <job.json>

job.json: {"out", "takes": [{"take", "model" (the raw .glb), "views": [{"name", "position", "target", "up", "fov_x",
"width", "height"}]}]}, the cameras in the glTF frame (y up) the raw model is written in. Per take and view it writes
<out>/<take>/<view>.png (the base colour as the model's texture holds it, unlit, on a clear ground),
<view>-mr.png (red: metalness, green: roughness, from the texture) and <view>-id.npy (each pixel's face, Blender's
polygon index, -1 off the model), and per take faces.npy (each Blender polygon's middle in the glTF frame), so
../multiview.py can lay every polygon on the welded model's face by its middle.
"""
import json
import math
import pathlib
import sys

import bpy
import numpy as np
from mathutils import Matrix, Vector

COLOUR_SAMPLES = 16
# A face index is drawn as one sample at the pixel's middle: the pixel filter this narrow.
ID_FILTER = 0.01


def to_blender(vector):
    """A glTF (y up) vector in Blender's frame (z up), as the glTF importer turns it."""
    x, y, z = vector
    return Vector((x, -z, y))


def to_gltf(points):
    return np.stack([points[:, 0], points[:, 2], -points[:, 1]], axis=1)


def cycles_on_card(scene):
    scene.render.engine = "CYCLES"
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
            return
    scene.cycles.device = "CPU"


def empty_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    cycles_on_card(scene)
    scene.cycles.use_denoising = False
    scene.cycles.max_bounces = 0
    scene.render.film_transparent = True
    scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    world = bpy.data.worlds.new("none")
    world.color = (0.0, 0.0, 0.0)
    scene.world = world
    return scene


def imported(path):
    """The raw model as one mesh object."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path), merge_vertices=False)
    meshes = [item for item in bpy.data.objects if item not in before and item.type == "MESH"]
    if len(meshes) != 1:
        raise SystemExit(f"{path}: {len(meshes)} meshes, expected the raw model's one")
    return meshes[0]


def principled_inputs(item):
    """The texture outputs feeding the model's base colour, metalness and roughness (or their plain values)."""
    material = item.material_slots[0].material
    principled = next(node for node in material.node_tree.nodes if node.type == "BSDF_PRINCIPLED")
    found = {}
    for name in ("Base Color", "Metallic", "Roughness"):
        socket = principled.inputs[name]
        found[name] = socket.links[0].from_socket if socket.links else socket.default_value
    return material, found


def emitting(material, feed):
    """`material` rebuilt to emit `feed(nodes, links)`'s colour socket, nothing else."""
    nodes, links = material.node_tree.nodes, material.node_tree.links
    output = next(node for node in nodes if node.type == "OUTPUT_MATERIAL")
    emission = nodes.new("ShaderNodeEmission")
    links.new(feed(nodes, links), emission.inputs["Color"])
    links.new(emission.outputs["Emission"], output.inputs["Surface"])


def plain(nodes, value):
    node = nodes.new("ShaderNodeValue")
    node.outputs[0].default_value = float(value if not hasattr(value, "__len__") else value[0])
    return node.outputs[0]


def materials_for(item):
    """Three copies of the model's material: its base colour, its metal and roughness, its face index (+1)."""
    material, feeds = principled_inputs(item)
    colour = material.copy()
    emitting(colour, lambda nodes, links: socket_in(colour, feeds["Base Color"]))
    metal_rough = material.copy()

    def metal_and_rough(nodes, links):
        combine = nodes.new("ShaderNodeCombineColor")
        for name, channel in (("Metallic", "Red"), ("Roughness", "Green")):
            fed = socket_in(metal_rough, feeds[name])
            links.new(fed if not isinstance(fed, float) else plain(nodes, fed), combine.inputs[channel])
        return combine.outputs["Color"]
    emitting(metal_rough, metal_and_rough)
    face = bpy.data.materials.new("face")
    face.use_nodes = True

    def face_index(nodes, links):
        attribute = nodes.new("ShaderNodeAttribute")
        attribute.attribute_type = "GEOMETRY"
        attribute.attribute_name = "face_id"
        return attribute.outputs["Fac"]
    for node in list(face.node_tree.nodes):
        if node.type != "OUTPUT_MATERIAL":
            face.node_tree.nodes.remove(node)
    emitting(face, face_index)
    return {"colour": colour, "mr": metal_rough, "id": face}


def socket_in(material, socket):
    """The same socket (by its node's name) in a copy of the material the socket came from."""
    if not hasattr(socket, "node"):
        return socket
    return material.node_tree.nodes[socket.node.name].outputs[socket.identifier]


def face_ids(item):
    mesh = item.data
    attribute = mesh.attributes.new("face_id", "FLOAT", "FACE")
    attribute.data.foreach_set("value", np.arange(1, len(mesh.polygons) + 1, dtype=np.float32))
    middles = np.zeros(len(mesh.polygons) * 3, dtype=np.float32)
    mesh.polygons.foreach_get("center", middles)
    world = np.array(item.matrix_world)
    points = middles.reshape(-1, 3) @ world[:3, :3].T + world[:3, 3]
    return to_gltf(points)


def camera_at(scene, view):
    """The view's camera: at `position` looking at `target`, `up` up, `fov_x` across, in Blender's frame."""
    position, target, up = (to_blender(view[key]) for key in ("position", "target", "up"))
    forward = (target - position).normalized()
    right = forward.cross(up).normalized()
    true_up = right.cross(forward)
    rotation = Matrix((right, true_up, -forward)).transposed()
    data = bpy.data.cameras.new(view["name"])
    data.sensor_fit = "HORIZONTAL"
    data.angle = view["fov_x"]
    data.clip_start, data.clip_end = 0.01, 100.0
    camera = bpy.data.objects.new(view["name"], data)
    camera.matrix_world = Matrix.Translation(position) @ rotation.to_4x4()
    scene.collection.objects.link(camera)
    scene.camera = camera
    scene.render.resolution_x, scene.render.resolution_y = view["width"], view["height"]


def render(scene, item, material, path, samples, filter_width, exr=False):
    item.material_slots[0].material = material
    scene.cycles.samples = samples
    scene.cycles.filter_width = filter_width
    settings = scene.render.image_settings
    settings.file_format = "OPEN_EXR" if exr else "PNG"
    settings.color_mode = "RGBA"
    settings.color_depth = "32" if exr else "8"
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def id_map(path):
    """The face index each pixel shows (Blender's polygon index, -1 off the model), from the rendered EXR."""
    image = bpy.data.images.load(str(path))
    width, height = image.size
    pixels = np.zeros(width * height * 4, dtype=np.float32)
    image.pixels.foreach_get(pixels)
    bpy.data.images.remove(image)
    pixels = pixels.reshape(height, width, 4)[::-1]
    return np.where(pixels[..., 3] > 0.5, np.rint(pixels[..., 0]).astype(np.int64) - 1, -1).astype(np.int32)


def one_take(entry, out):
    scene = empty_scene()
    item = imported(pathlib.Path(entry["model"]))
    folder = out / entry["take"]
    folder.mkdir(parents=True, exist_ok=True)
    np.save(folder / "faces.npy", face_ids(item))
    materials = materials_for(item)
    for view in entry["views"]:
        camera_at(scene, view)
        render(scene, item, materials["colour"], folder / f"{view['name']}.png", COLOUR_SAMPLES, 1.5)
        render(scene, item, materials["mr"], folder / f"{view['name']}-mr.png", COLOUR_SAMPLES, 1.5)
        exr = folder / f"{view['name']}-id.exr"
        render(scene, item, materials["id"], exr, 1, ID_FILTER, exr=True)
        np.save(folder / f"{view['name']}-id.npy", id_map(exr))
        exr.unlink()
        print(entry["take"], view["name"], flush=True)


def main():
    job = json.loads(pathlib.Path(sys.argv[sys.argv.index("--") + 1]).read_text())
    out = pathlib.Path(job["out"])
    for entry in job["takes"]:
        one_take(entry, out)


if __name__ == "__main__":
    main()
