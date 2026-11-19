"""Runs inside Blender: a film's frames drawn as layers, the place once and each person on its own over it (owner,
2026-11-19: "render a place's background once and the people on top"; ../layered.py plans, keeps and composes them).

    blender -b --python layered.py -- <scene.usda> <views.json> <out>   (a walk-through: usd_views.py's arguments,
                                                                        the laid place's look as blender_views.py's)
    walker_peel.py draws its peel's layers through drawn() when its job names `layered`.

Each view of the listing names the layers it draws (`layers`, {layer: frame key}): `background` (the place with every
person and peel layer hidden, as it is, the film opaque), or a layer (`walker:<name>`, a walker's own body under the
stage's Characters, or one a caller registers: walker_peel's `soma:<name>` and `sim:<name>`) drawn alone over the
place in the standard Blender way: every other drawn thing a shadow catcher (it holds the layer out where it stands in
front and catches the layer's shadows and light on it: Cycles' Shadow Catcher pass), the air (haze, dust, beams, stars,
effects) out of the camera's sight, the film transparent, with its depth; drawn only inside the picture's box round
the layer and the shadows its lights throw from it (`border`; the whole picture where the stage holds a water mirror),
a layer wholly outside the picture not drawn at all. Every render in linear light, before the look's compositor:
compose.py applies the glow and the view transform once, to the composite.

Out: <out>/<layer>/<view>.exr (half float, multilayer) and <view>.json ({"key", "border": [x0, y0, x1, y1] in shares
of the picture, Blender's, bottom row 0} or {"key", "empty": true}; the background's {"key", "look"}: the view
settings and the compositor's glare as the place's look sets them). Cycles only: the shadow catcher is Cycles'.
"""
import json
import pathlib
import sys

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[3]
for _folder in (HERE, REPO / "tools/blender/inside", REPO / "score/stages/place_build"):
    if str(_folder) not in sys.path:
        sys.path.insert(0, str(_folder))
import usd_views  # noqa: E402

BACKGROUND = "background"
WALKER = "walker:"
CHARACTERS = "Characters"
EFFECTS = "Effects"
AIR = ("haze", "stars", "sky", "dust", "beam")  # usd_views' air: never a catcher, left out of a layer's camera rays
DRAWN = ("MESH", "CURVE", "CURVES", "POINTCLOUD", "VOLUME", "META", "SURFACE", "FONT")
SHADOW_REACH = 8.0  # metres a shadow is followed along its light from a corner of the layer's box
SHADOW_DROP = 3.0  # metres below the layer's lowest point a shadow is followed down to (a stair's flights)
LIGHT_REACH = 20.0  # metres: a lamp farther than this from the layer's centre throws no shadow the border keeps
MARGIN = 0.04  # of the picture, round the layer's box and its shadows
REGISTERED = {}  # layer name -> a callable giving its objects (walker_peel's peel layers)
STATE = {}


def register(name, objects):
    """A layer of the caller's own (`objects` a callable giving its Blender objects), drawn by name."""
    REGISTERED[name] = objects


def walker_name(item):
    """The walker an imported object belongs to (its prim path under the stage's Characters), else None."""
    names = usd_views.prim_path(item).strip("/").split("/")
    return names[names.index(CHARACTERS) + 1] if CHARACTERS in names[:-1] else None


def universe():
    """{layer: its objects} and the background's objects, taken once, after the stage and every registered layer are
    in: only what the stage draws (a thing it made invisible stays so)."""
    if STATE:
        return STATE
    every = [item for item in bpy.context.scene.objects if item.type in DRAWN and not item.hide_render]
    layers = {name: [item for item in objects() if item.type in DRAWN] for name, objects in REGISTERED.items()}
    taken = {item.name for objects in layers.values() for item in objects}
    for item in every:
        walker = walker_name(item)
        if walker is not None and item.name not in taken:
            layers.setdefault(WALKER + walker, []).append(item)
    held = {item.name for objects in layers.values() for item in objects}
    STATE.update(layers=layers, background=[item for item in every if item.name not in held],
                 mirrored=any(usd_views.score_value(item, "mirror_along") is not None for item in every))
    return STATE


def air(item):
    """Whether an object is air, not the place's (usd_views' sky kinds, and the effects' particles under Effects)."""
    return usd_views.score_value(item, "kind") in AIR or EFFECTS in usd_views.prim_path(item).split("/")


def corners(objects):
    """The world corners of the layer's evaluated boxes (a skinned body as posed now)."""
    graph = bpy.context.evaluated_depsgraph_get()
    found = []
    for item in objects:
        evaluated = item.evaluated_get(graph)
        found += [evaluated.matrix_world @ Vector(corner) for corner in evaluated.bound_box]
    return found


def shadow_ends(points, lights):
    """Where each lamp's shadow of the box's corners may fall: each corner followed along its light, down to
    SHADOW_DROP under the box (SHADOW_REACH at most)."""
    lowest = min(point.z for point in points)
    centre = sum(points, Vector()) / len(points)
    ends = []
    for light in lights:
        if light.data.type == "SUN":
            ways = [light.matrix_world.to_quaternion() @ Vector((0.0, 0.0, -1.0))] * len(points)
        elif (light.matrix_world.translation - centre).length <= LIGHT_REACH:
            ways = [(point - light.matrix_world.translation).normalized() for point in points]
        else:
            continue
        for point, way in zip(points, ways):
            reach = SHADOW_REACH if way.z > -1e-3 else min(SHADOW_REACH, (point.z - lowest + SHADOW_DROP) / -way.z)
            ends.append(point + way * reach)
    return ends


def in_front(camera, points):
    """The points in front of the camera's near plane, and where each line between one in front and one behind
    crosses it: what of their hull the camera can see, so a layer or a shadow partly behind the camera keeps its
    box."""
    to_camera = camera.matrix_world.inverted()
    near = camera.data.clip_start
    depths = [-(to_camera @ point).z for point in points]
    kept = [point for point, depth in zip(points, depths) if depth >= near]
    for first, (point, depth) in enumerate(zip(points, depths)):
        for other, other_depth in zip(points[first + 1:], depths[first + 1:]):
            if (depth >= near) != (other_depth >= near):
                kept.append(point.lerp(other, (depth - near) / (depth - other_depth)))
    return kept


def border(scene, objects):
    """The picture's box ([x0, y0, x1, y1], shares, bottom row 0) round the layer and its shadows, MARGIN round it;
    the whole picture where the stage holds a water mirror; None when it is wholly outside the picture or behind the
    camera."""
    points = corners(objects)
    if not points:
        return None
    if universe()["mirrored"]:
        return [0.0, 0.0, 1.0, 1.0]
    lights = [item for item in scene.objects if item.type == "LIGHT" and not item.hide_render]
    seen = [world_to_camera_view(scene, scene.camera, point)
            for point in in_front(scene.camera, points + shadow_ends(points, lights))]
    if not seen:
        return None
    box = [max(0.0, min(point.x for point in seen) - MARGIN), max(0.0, min(point.y for point in seen) - MARGIN),
           min(1.0, max(point.x for point in seen) + MARGIN), min(1.0, max(point.y for point in seen) + MARGIN)]
    return box if box[0] < box[2] and box[1] < box[3] else None


def exr(scene, path, depth_and_catcher):
    """The render written to a half float multilayer EXR in linear light, the compositor off; with
    `depth_and_catcher`, its Depth and Shadow Catcher passes beside its Combined."""
    settings = scene.render.image_settings
    settings.media_type = "MULTI_LAYER_IMAGE"
    settings.file_format = "OPEN_EXR_MULTILAYER"
    settings.color_depth = "16"
    settings.exr_codec = "ZIP"
    layer = scene.view_layers[0]
    layer.use_pass_z = depth_and_catcher
    layer.cycles.use_pass_shadow_catcher = depth_and_catcher
    layer.cycles.denoising_store_passes = False
    scene.render.use_compositing = False
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def caught(scene, layer, path):
    """One layer over the place: the layer's objects alone shown, the place's a shadow catcher, the air out of the
    camera's sight; its sidecar's border, or empty and nothing drawn."""
    world = universe()
    shown = world["layers"].get(layer)
    if shown is None:
        raise RuntimeError(f"no layer {layer} in the stage (layers: {', '.join(sorted(world['layers']))})")
    for name, objects in world["layers"].items():
        for item in objects:
            item.hide_render = name != layer
    box = border(scene, shown)
    if box is None:
        return None
    kept = [(item, item.is_shadow_catcher, item.visible_camera) for item in world["background"]]
    for item in world["background"]:
        if air(item):
            item.visible_camera = False
        else:
            item.is_shadow_catcher = True
    scene.render.film_transparent = True
    scene.render.use_border, scene.render.use_crop_to_border = True, False
    (scene.render.border_min_x, scene.render.border_min_y, scene.render.border_max_x,
     scene.render.border_max_y) = box
    try:
        exr(scene, path, True)
    finally:
        scene.render.use_border = False
        for item, catcher, camera in kept:
            item.is_shadow_catcher, item.visible_camera = catcher, camera
    return box


def background(scene, path):
    """The place with every layer hidden, as it is: the film opaque."""
    for objects in universe()["layers"].values():
        for item in objects:
            item.hide_render = True
    scene.render.film_transparent = False
    exr(scene, path, False)


def look_of(scene):
    """The view settings and the compositor's glare as the place's look set them, for compose.py."""
    view = scene.view_settings
    glare = None
    tree = scene.compositing_node_group
    node = next((node for node in tree.nodes if node.type == "GLARE"), None) if tree is not None else None
    if node is not None:
        glare = {socket.name: (socket.default_value if isinstance(socket.default_value, (str, float, int, bool))
                               else list(socket.default_value))
                 for socket in node.inputs if socket.name != "Image" and hasattr(socket, "default_value")}
    return {"view_transform": view.view_transform, "look": view.look, "exposure": view.exposure, "gamma": view.gamma,
            "display": scene.display_settings.display_device, "glare": glare}


def drawn(scene, view, out):
    """The view's layers (its `layers`: {layer: frame key}) drawn into <out>/<layer>/<view>.exr with their sidecars;
    every object's visibility put back after."""
    world = universe()
    hidden = {item.name: item.hide_render for objects in world["layers"].values() for item in objects}
    compositing = scene.render.use_compositing
    try:
        for layer, key in view["layers"].items():
            folder = pathlib.Path(out) / layer.replace(":", "-")
            folder.mkdir(parents=True, exist_ok=True)
            if layer == BACKGROUND:
                background(scene, folder / f"{view['name']}.exr")
                record = {"key": key, "look": look_of(scene)}
            else:
                box = caught(scene, layer, folder / f"{view['name']}.exr")
                record = {"key": key, "empty": True} if box is None else {"key": key, "border": box}
            (folder / f"{view['name']}.json").write_text(json.dumps(record))
    finally:
        for objects in world["layers"].values():
            for item in objects:
                item.hide_render = hidden[item.name]
        scene.render.use_compositing = compositing
        scene.render.film_transparent = False


def with_layers(render):
    """usd_views' render, each view of the listing drawn as its layers (a walk-through)."""
    listing = json.loads(pathlib.Path(sys.argv[sys.argv.index("--") + 2]).read_text())
    views = {view["name"]: view for view in listing["views"]}

    def layered(scene, path, transparent):
        name = pathlib.Path(path).name.removesuffix("-look.png")
        if name not in views or "layers" not in views[name]:
            return render(scene, path, transparent)
        drawn(scene, views[name], listing["layered"])
    return layered


if __name__ == "__main__":
    usd_views.render = with_layers(usd_views.render)
    import blender_views  # noqa: E402,F401  (runs usd_views.main() with the laid place's look)
