"""Runs inside Blender (bench.py's render, on this PC's card through the card queue): one SimReady asset drawn as the
prop route's close-up, from the camera bench.py framed on its true box.

    blender -b --python closeup.py -- <root.usd> <job.json> <out folder>

job.json: {"size": pixels square, "samples", "camera": {"eye", "aim", "up", "fov" (vertical, degrees)}, "floor": the
box's low z}. The asset is read as its USD composes (instances and payloads, its UsdPreviewSurface materials with
their own maps, metres by its stage's unit, Z up as Blender's own), its instances laid out as meshes of their own,
its render purpose only (no colliders or proxies).
Soft studio light (lit): a large key from the camera's left above, a fill from its right, a little grey sky light.

Writes <out>/rgba.png (the asset alone, its true alpha), <out>/shadow.png (the asset with its shadow on the floor
caught, transparent elsewhere, the asset itself drawn as in rgba.png; bench.py lays it on the grey backdrop) and
<out>/report.json (the box Blender drew, the meshes, and each material with the pictures it reads).
"""
import json
import math
import pathlib
import sys

import bpy
from mathutils import Matrix, Vector

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "library" / "inside"))
import scene_setup  # noqa: E402  (the library's renders' empty scene: Cycles, the card where FARM_CYCLES_GPU is set)

SKY = 0.35  # the grey sky light's strength: shadows soft, never black
KEY_WATTS_A_SQUARE_METRE = 300.0  # the key's power over the box's diagonal squared, so every size is lit alike
FILL_SHARE = 0.35
KEY_TURN, KEY_RISE = 50.0, 45.0  # degrees left of the camera's heading, and up
FILL_TURN, FILL_RISE = 70.0, 20.0  # degrees right of it, and up
LAMP_SPREAD = 3.0  # the lamps' size as a share of the box's diagonal: large lamps, soft shadows


def arguments():
    given = sys.argv[sys.argv.index("--") + 1:]
    if len(given) != 3:
        raise SystemExit(__doc__)
    return pathlib.Path(given[0]), json.loads(pathlib.Path(given[1]).read_text()), pathlib.Path(given[2])


def imported(root):
    """The asset brought in as it composes; its mesh objects."""
    before = set(bpy.data.objects)
    result = bpy.ops.wm.usd_import(filepath=str(root), import_guide=False, import_proxy=False, import_render=True,
                                   import_lights=False, import_cameras=False, create_world_material=False,
                                   import_textures_mode="IMPORT_NONE", apply_unit_conversion_scale=True,
                                   support_scene_instancing=False)  # instances as meshes of their own, as they draw
    if "FINISHED" not in result:
        raise RuntimeError(f"Blender did not import {root}: {result}")
    bpy.context.view_layer.update()
    return [item for item in bpy.data.objects if item not in before and item.type == "MESH"
            and item.visible_get()]


def drawn_box(meshes):
    """The low and high corners of every drawn mesh's evaluated points, in the scene (metres, Z up)."""
    graph = bpy.context.evaluated_depsgraph_get()
    points = []
    for item in meshes:
        evaluated = item.evaluated_get(graph)
        points.extend(evaluated.matrix_world @ vertex.co for vertex in evaluated.data.vertices)
    if not points:
        raise RuntimeError("the asset drew no mesh")
    return ([min(point[axis] for point in points) for axis in range(3)],
            [max(point[axis] for point in points) for axis in range(3)])


def materials_read(meshes):
    """{material: [the pictures its nodes read]} over every drawn mesh's slots; a slot with no material is ''."""
    found = {}
    for item in meshes:
        for slot in item.material_slots:
            material = slot.material
            if material is None:
                found[""] = []
                continue
            nodes = material.node_tree.nodes if material.use_nodes else []
            found[material.name] = sorted(pathlib.Path(node.image.filepath).name for node in nodes
                                          if node.type == "TEX_IMAGE" and node.image)
    return found


def camera(scene, view):
    """The scene's camera at the job's eye, aimed as framed, its vertical field `fov` degrees."""
    data = bpy.data.cameras.new("closeup")
    data.sensor_fit = "VERTICAL"
    data.angle = math.radians(view["fov"])
    data.clip_start, data.clip_end = 0.001, 1000.0
    item = bpy.data.objects.new("closeup", data)
    scene.collection.objects.link(item)
    eye, aim, up = Vector(view["eye"]), Vector(view["aim"]), Vector(view["up"])
    back = (eye - aim).normalized()
    right = up.cross(back).normalized()
    true_up = back.cross(right)
    rotation = Matrix((right, true_up, back)).transposed()
    item.matrix_world = Matrix.Translation(eye) @ rotation.to_4x4()
    scene.camera = item


def lamp(scene, name, at, aim, size, watts):
    """A square area lamp of `size` metres at `at`, facing `aim`."""
    data = bpy.data.lights.new(name, "AREA")
    data.size, data.energy = size, watts
    item = bpy.data.objects.new(name, data)
    scene.collection.objects.link(item)
    item.location = at
    item.rotation_euler = (Vector(aim) - Vector(at)).to_track_quat("-Z", "Y").to_euler()


def from_heading(heading, turn, rise):
    """A unit direction `turn` degrees left of the level `heading` about z, `rise` degrees above level."""
    angle = math.atan2(heading.y, heading.x) + math.radians(turn)
    return Vector((math.cos(angle) * math.cos(math.radians(rise)), math.sin(angle) * math.cos(math.radians(rise)),
                   math.sin(math.radians(rise))))


def lit(scene, low, high, view):
    """Soft studio light on the box, set by the camera's heading (straight above: the front, -y): a large key from its
    left KEY_RISE degrees up, a fill from its right FILL_RISE up, a grey sky; never from straight over the camera, so
    a top-down look sees no lamp's glare."""
    centre = (Vector(low) + Vector(high)) / 2
    diagonal = (Vector(high) - Vector(low)).length
    heading = Vector(view["eye"]) - centre
    heading.z = 0.0
    if heading.length < 1e-6 * diagonal:
        heading = Vector((0.0, -1.0, 0.0))
    reach = 2.5 * diagonal
    watts = KEY_WATTS_A_SQUARE_METRE * diagonal ** 2
    lamp(scene, "key", centre + from_heading(heading, KEY_TURN, KEY_RISE) * reach, centre, LAMP_SPREAD * diagonal,
         watts)
    lamp(scene, "fill", centre + from_heading(heading, -FILL_TURN, FILL_RISE) * reach, centre,
         LAMP_SPREAD * diagonal, FILL_SHARE * watts)
    nodes = scene.world.node_tree.nodes
    background = nodes.get("Background") or nodes.new("ShaderNodeBackground")
    background.inputs["Color"].default_value = (0.8, 0.8, 0.8, 1.0)
    background.inputs["Strength"].default_value = SKY
    output = nodes.get("World Output") or nodes.new("ShaderNodeOutputWorld")
    scene.world.node_tree.links.new(background.outputs["Background"], output.inputs["Surface"])


def floor(scene, low, high):
    """A shadow catcher under the box, wide enough to hold its shadow, seen by the camera alone: no light of the
    asset's bounces off it and no face of it mirrors it, so closeup.png draws the asset as rgba.png does (#202: lit
    from below by the catcher, tc6's stove walls and desk legs, light bare metal, read as white paint on the backdrop
    and steel in the route's input; the chair's plastic 4.8 dE apart, the stove's 13.6)."""
    diagonal = (Vector(high) - Vector(low)).length
    bpy.ops.mesh.primitive_plane_add(size=20 * diagonal, location=((low[0] + high[0]) / 2, (low[1] + high[1]) / 2,
                                                                   low[2]))
    plane = bpy.context.active_object
    plane.is_shadow_catcher = True
    plane.visible_diffuse = plane.visible_glossy = plane.visible_transmission = False
    return plane


def rendered(scene, path):
    scene.render.filepath = str(path)
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    bpy.ops.render.render(write_still=True)


def main():
    root, job, out = arguments()
    out.mkdir(parents=True, exist_ok=True)
    scene_setup.empty_scene(job["size"], job["samples"])
    scene = bpy.context.scene
    meshes = imported(root)
    low, high = drawn_box(meshes)
    camera(scene, job["camera"])
    lit(scene, low, high, job["camera"])
    rendered(scene, out / "rgba.png")
    floor(scene, low, high)
    rendered(scene, out / "shadow.png")
    report = {"box": [low, high], "meshes": len(meshes), "materials": materials_read(meshes),
              "engine": scene.cycles.device}
    (out / "report.json").write_text(json.dumps(report, indent=1))


if __name__ == "__main__":  # look.py imports `lit` to draw a made model under the same light
    main()
