"""Inside Blender (Cycles on the CPU): a generated head with its real eyes (`blender_eyes.py`) drawn before and after
its face is re-painted from the close-up photo and its skin made skin (`skin.py`'s face.png and skin.npz).

    blender -b --python blender_skin.py -- <model.glb> <eyes.npz> <library> <height m> <samples> <out folder> \
        <skin folder>

Before: the model's own paint in the glTF's own material. After, on the painted skin's faces: the face texture on its
own planar UV (`face`) mixed into the model's paint by the photo's share (the texture's alpha), in the library's skin
(`SKIN`, score_lib's face skin: its random-walk light under the surface, its oil coat, its photographed pores' colour
and relief on the head's metric coordinates, its T-zone a little glossier by the `sheen` region's roughness); hair,
brows and clothes keep the glTF's material. The head keeps its own paint where the photo does not reach
(data/checks/library-exceptions.json: a generated model keeps its own paint). Shots per side: the face from the front
and three quarters, the eyes in a 9 cm frame, and the cheek and nose close up (CLOSE_FRAME_M), the whole route's photo
way (`../whole/render.py`); <out>/frames.json says how each is framed.
"""
import json
import math
import pathlib
import sys

import bpy
import numpy as np
from mathutils import Vector
from mathutils.kdtree import KDTree

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import blender_eyes  # noqa: E402  (reads its six arguments; the skin folder is the seventh)
from blender_eyes import blender_face, render  # noqa: E402

SKIN_FOLDER = sys.argv[sys.argv.index("--") + 1:][6]
SKIN = "face_skin_light"
FACE_DROP_M = 0.03  # the face's shots aimed this far under the eyes
CLOSE_FRAME_M = 0.06
CLOSE_FSTOP = 11.0
FACE_UV = "face"
MATCH_M = 1e-5  # a painted skin triangle's middle found on the imported mesh within this (the model's units)
UNDER_DARK = 0.3  # skin.PAINT_SHADE's `under`: the light under the surface where uncovered paint was dark


def attributes(head, skin):
    """Whether each mesh point is the front the photo saw, its paint's gain and how dark it was (`skin.paint_shade`),
    and its T-zone, from its nearest skin.npz point (the importer splits points on seams; every copy gets the same),
    as the point attributes `photo_front`, `paint_gain` and `thin_dark` and the face module's `tones` colours (the
    T-zone the `sheen` region, the whole head `face`)."""
    mesh = head.data
    found = blender_face.z_up(np.asarray(skin["points"], np.float64))
    tree = KDTree(len(found))
    for index, point in enumerate(found):
        tree.insert(Vector(point.tolist()), index)
    tree.balance()
    nearest = np.array([tree.find(vertex.co)[1] for vertex in mesh.vertices])
    front = mesh.attributes.new("photo_front", "FLOAT", "POINT")
    front.data.foreach_set("value", np.asarray(skin["front"], np.float32)[nearest])
    thin = mesh.attributes.new("thin_dark", "FLOAT", "POINT")
    thin.data.foreach_set("value", np.asarray(skin["thin_dark"], np.float32)[nearest])
    gain = np.ones((len(nearest), 4), np.float32)
    gain[:, :3] = np.asarray(skin["paint_gain"], np.float32)[nearest]
    mesh.color_attributes.new("paint_gain", "FLOAT_COLOR", "POINT").data.foreach_set("color", gain.ravel())
    channels = {name: np.zeros(len(nearest), np.float32) for name in blender_face.TONES}
    channels["sheen"] = np.asarray(skin["tzone"], np.float32)[nearest]
    channels["face"][:] = 1.0
    for group in range(0, len(blender_face.TONES), 3):
        names = blender_face.TONES[group:group + 3]
        colour = np.ones((len(nearest), 4), np.float32)
        colour[:, :3] = 0.0
        for column, name in enumerate(names):
            colour[:, column] = channels[name]
        layer = mesh.color_attributes.new("tones" + (str(group // 3) if group else ""), "FLOAT_COLOR", "POINT")
        layer.data.foreach_set("color", colour.ravel())


def skin_marked(head, centres):
    """The painted skin's faces marked (the face attribute `painted_skin`) by their middles, before the eyes step moves
    any point (the mark rides through its removal)."""
    mesh = head.data
    tree = KDTree(len(mesh.polygons))
    for polygon in mesh.polygons:
        tree.insert(polygon.center, polygon.index)
    tree.balance()
    marked = np.zeros(len(mesh.polygons), np.int32)
    for centre in blender_face.z_up(np.asarray(centres, np.float64)):
        _, index, distance = tree.find(Vector(centre.tolist()))
        if distance < MATCH_M:
            marked[index] = 1
    if marked.sum() < 0.99 * len(centres):
        raise RuntimeError(f"only {marked.sum()} of the {len(centres)} painted skin triangles are on the mesh")
    mesh.attributes.new("painted_skin", "INT", "FACE").data.foreach_set("value", marked)


def face_uv(head, box):
    """The face texture's own UV map: the model's front (glTF x, y) over the face's box."""
    mesh = head.data
    layer = mesh.uv_layers.new(name=FACE_UV)
    x0, x1, y0, y1 = box
    points = np.array([vertex.co[:] for vertex in mesh.vertices])
    loops = np.zeros(len(mesh.loops), np.int64)
    mesh.loops.foreach_get("vertex_index", loops)
    uv = np.stack([(points[loops, 0] - x0) / (x1 - x0), (points[loops, 2] - y0) / (y1 - y0)], axis=1)
    layer.data.foreach_set("uv", uv.astype(np.float32).ravel())


def own_image(head):
    """The model's own base colour image (the glTF material's)."""
    material = head.data.materials[0]
    principled = blender_face.principled_of(material)
    link = principled.inputs["Base Color"].links[0]
    return link.from_node.image


def metric_space(turntable):
    """An empty under the turntable at the scene's scale: the skin's pores laid on coordinates in metres that turn
    with the head (the head's own coordinates are the model's units)."""
    space = bpy.data.objects.new("skin_space", None)
    bpy.context.scene.collection.objects.link(space)
    space.parent = turntable
    space.matrix_world = turntable.matrix_world.copy()
    return space


def textured(tree, image, uv_name, colour_space):
    """An image node on the UV map `uv_name`."""
    node = tree.nodes.new("ShaderNodeTexImage")
    node.image = image
    node.image.colorspace_settings.name = colour_space
    node.interpolation = "Cubic"
    node.extension = "EXTEND"
    uv = tree.nodes.new("ShaderNodeUVMap")
    uv.uv_map = uv_name
    tree.links.new(uv.outputs["UV"], node.inputs["Vector"])
    return node


def skin_material(head, library, folder, space):
    """The library skin with the face texture mixed into the model's paint (its dark baked shading lifted by
    `paint_gain`) as its base colour, by the texture's alpha (the photo's share) where the point is the front the photo
    saw (`photo_front`), on the skin's faces; the light under the surface down to UNDER_DARK of the library's where
    the paint the photo does not cover was dark (`thin_dark`); the rest (hair, clothes) keeps the glTF's own
    material."""
    record = blender_face.library_record(library, SKIN)
    entry = sorted((pathlib.Path(library) / "surface" / SKIN).glob("*/surface.json"))[-1].parent
    material = bpy.data.materials.new("generated_skin")
    material.use_nodes = True
    tree = material.node_tree
    principled = blender_face.principled_of(material)
    principled.inputs["Roughness"].default_value = record["constants"]["roughness"]
    principled.inputs["IOR"].default_value = record["constants"]["ior"]
    blender_face.light_through(material, record["subsurface"])
    blender_face.coated(material, record["coat"])
    own_uv = head.data.uv_layers[0].name
    own = textured(tree, own_image(head), own_uv, "sRGB")
    image = bpy.data.images.load(str(pathlib.Path(folder) / "face.png"))
    image.alpha_mode = "CHANNEL_PACKED"
    photo = textured(tree, image, FACE_UV, "sRGB")
    front = tree.nodes.new("ShaderNodeAttribute")
    front.attribute_name = "photo_front"
    mix = tree.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    first, second = (next(socket for socket in mix.inputs if socket.name == name and socket.type == "RGBA")
                     for name in ("A", "B"))
    tree.links.new(blender_face.times(tree, front.outputs["Fac"], photo.outputs["Alpha"]), mix.inputs["Factor"])
    gain = tree.nodes.new("ShaderNodeAttribute")
    gain.attribute_name = "paint_gain"
    lifted = tree.nodes.new("ShaderNodeMix")
    lifted.data_type = "RGBA"
    lifted.blend_type = "MULTIPLY"
    lifted.inputs["Factor"].default_value = 1.0
    lifted_a, lifted_b = (next(socket for socket in lifted.inputs if socket.name == name and socket.type == "RGBA")
                          for name in ("A", "B"))
    tree.links.new(own.outputs["Color"], lifted_a)
    tree.links.new(gain.outputs["Color"], lifted_b)
    tree.links.new(next(socket for socket in lifted.outputs if socket.type == "RGBA"), first)
    thin = tree.nodes.new("ShaderNodeAttribute")
    thin.attribute_name = "thin_dark"
    under = tree.nodes.new("ShaderNodeMapRange")
    under.inputs["To Min"].default_value = principled.inputs["Subsurface Scale"].default_value
    under.inputs["To Max"].default_value = principled.inputs["Subsurface Scale"].default_value * UNDER_DARK
    tree.links.new(thin.outputs["Fac"], under.inputs["Value"])
    tree.links.new(under.outputs["Result"], principled.inputs["Subsurface Scale"])
    tree.links.new(photo.outputs["Color"], second)
    tree.links.new(next(socket for socket in mix.outputs if socket.type == "RGBA"), principled.inputs["Base Color"])
    coordinates = tree.nodes.new("ShaderNodeTexCoord")
    coordinates.object = space
    blender_face.scanned(tree, principled, record["detail"]["scan"], entry, coordinates)
    glossier = tree.nodes.new("ShaderNodeMath")
    glossier.operation = "ADD"
    glossier.use_clamp = True
    rough = principled.inputs["Roughness"]
    tree.links.new(rough.links[0].from_socket, glossier.inputs[0])
    sheen = blender_face.scaled_by(tree, blender_face.tone(tree, "sheen"), record["regions"]["sheen"]["roughness"])
    tree.links.new(sheen, glossier.inputs[1])
    tree.links.new(glossier.outputs[0], rough)
    mesh = head.data
    mesh.materials.append(material)
    marked = np.zeros(len(mesh.polygons), np.int32)
    mesh.attributes["painted_skin"].data.foreach_get("value", marked)
    mesh.polygons.foreach_set("material_index", marked * (len(mesh.materials) - 1))
    mesh.update()


def shots(camera, turntable, aim, eyes_focus, close_focus, prefix):
    """The face from the front and three quarters, the eyes 9 cm and the cheek and nose CLOSE_FRAME_M close up into
    <OUT>/<prefix>-*.png."""
    scene = bpy.context.scene
    out = blender_eyes.OUT
    back = 1.0 / math.tan(camera.data.angle_y / 2.0) / 2.0
    render.aimed(camera, aim + Vector((0.0, -blender_eyes.FACE_FRAME_M * back, 0.0)), aim, render.STOPS["face"],
                 eyes_focus)
    render.drawn(scene, turntable, 0.0, out, f"{prefix}-face")
    render.drawn(scene, turntable, blender_eyes.THREE_QUARTER_DEGREES, out, f"{prefix}-three_quarter")
    portrait = (scene.render.resolution_x, scene.render.resolution_y)
    scene.render.resolution_x, scene.render.resolution_y = portrait[1], portrait[0]
    for name, focus, frame, fstop in (("eyes", eyes_focus, blender_eyes.EYES_FRAME_M, blender_eyes.EYES_FSTOP),
                                      ("close", close_focus, CLOSE_FRAME_M, CLOSE_FSTOP)):
        render.aimed(camera, focus + Vector((0.0, -frame * back, 0.0)), focus, fstop, focus)
        render.drawn(scene, turntable, 0.0, out, f"{prefix}-{name}")
    scene.render.resolution_x, scene.render.resolution_y = portrait


def frames(scene):
    """<OUT>/frames.json: each shot's frame height (m), the face's aim under the eyes and the portrait's width over
    its height, for the sheet to crop the photo the same way."""
    size = {"face": blender_eyes.FACE_FRAME_M, "face_drop": FACE_DROP_M, "eyes": blender_eyes.EYES_FRAME_M,
            "close": CLOSE_FRAME_M, "portrait": scene.render.resolution_x / scene.render.resolution_y}
    (pathlib.Path(blender_eyes.OUT) / "frames.json").write_text(json.dumps(size))


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    eyes = dict(np.load(blender_eyes.EYES, allow_pickle=False))
    skin = dict(np.load(pathlib.Path(SKIN_FOLDER) / "skin.npz", allow_pickle=False))
    head, holder = blender_eyes.imported()
    low, high = render.bounds([head])
    camera, turntable = blender_eyes.staged(holder, (low + high) / 2.0)
    pathlib.Path(blender_eyes.OUT).mkdir(parents=True, exist_ok=True)
    attributes(head, skin)
    face_uv(head, skin["box"])
    skin_marked(head, skin["skin_centres"])
    blender_eyes.floor_pushed(head, eyes["moved_from"], eyes["moved_to"])
    blender_eyes.floor_removed(head, eyes["removed"])
    blender_eyes.laid(head, eyes)
    corneas = blender_eyes.mean_point(blender_eyes.world_points(head, eyes["cornea_apex"]))
    aim = corneas + Vector((0.0, 0.0, -FACE_DROP_M))
    close = blender_eyes.world_points(head, [skin["close_point"]])[0]
    frames(bpy.context.scene)
    shots(camera, turntable, aim, corneas, close, "before")
    skin_material(head, blender_eyes.LIBRARY, SKIN_FOLDER, metric_space(turntable))
    shots(camera, turntable, aim, corneas, close, "after")
    print("SKIN RENDER DONE", flush=True)


if __name__ == "__main__":
    main()
