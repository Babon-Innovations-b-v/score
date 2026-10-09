"""Runs inside Blender on a card (tools/cloud/images/warm.py): small Cycles renders that make the card compile every
kernel our jobs use, each render timed, so the first render's compile can be measured and kept.

    blender -b -setaudio None --python-exit-code 1 --python warm_kernels.py -- <out.json> [OPTIX|CUDA]

Three scenes in turn on the first card of the asked backend (OptiX by default, as the jobs take it): plain shading;
a material with ambient occlusion and bevel nodes (OptiX's shader-raytrace kernels); hair curves. Each is rendered
twice at a small size, so the second render of the first scene is the render without any compile. out.json holds
the seconds of each render and the card Blender used.
"""
import json
import sys
import time

import bpy


def arguments():
    after = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if not after:
        raise SystemExit("usage: ... warm_kernels.py -- <out.json> [OPTIX|CUDA]")
    return after[0], (after[1] if len(after) > 1 else "OPTIX")


def use_card(scene, backend):
    """Cycles on the backend's devices only; the names of the cards used."""
    preferences = bpy.context.preferences.addons["cycles"].preferences
    preferences.compute_device_type = backend
    preferences.get_devices()
    used = [device for device in preferences.devices if device.type == backend]
    if not used:
        raise SystemExit(f"no {backend} card for Cycles")
    for device in preferences.devices:
        device.use = device.type == backend
    scene.render.engine = "CYCLES"
    scene.cycles.device = "GPU"
    scene.cycles.samples = 16
    scene.cycles.use_denoising = False
    scene.render.resolution_x = scene.render.resolution_y = 128
    return sorted({device.name for device in used})


def plain_scene():
    bpy.ops.wm.read_factory_settings(use_empty=False)
    return bpy.context.scene


def raytrace_material(scene):
    """Every mesh gets a material with ambient occlusion and bevel nodes."""
    material = bpy.data.materials.new("warm-raytrace")
    material.use_nodes = True
    nodes, links = material.node_tree.nodes, material.node_tree.links
    shader = next(node for node in nodes if node.type == "BSDF_PRINCIPLED")
    occlusion, bevel = nodes.new("ShaderNodeAmbientOcclusion"), nodes.new("ShaderNodeBevel")
    links.new(occlusion.outputs["Color"], shader.inputs["Base Color"])
    links.new(bevel.outputs["Normal"], shader.inputs["Normal"])
    for item in scene.objects:
        if item.type == "MESH":
            item.data.materials.clear()
            item.data.materials.append(material)


def hair(scene):
    """A hair curves object grown on the default cube."""
    cube = next(item for item in scene.objects if item.type == "MESH")
    bpy.context.view_layer.objects.active = cube
    cube.select_set(True)
    bpy.ops.object.curves_empty_hair_add()
    curves = bpy.context.active_object
    points = curves.data
    points.add_curves([4] * 50)
    for index, point in enumerate(points.points):
        point.position = ((index // 4) * 0.02 - 0.5, 0.0, 1.0 + (index % 4) * 0.1)


def render(scene, path):
    """One still render; its seconds."""
    scene.render.filepath = path
    began = time.time()
    bpy.ops.render.render(write_still=True)
    return round(time.time() - began, 2)


def main():
    out, backend = arguments()
    record = {"backend": backend, "blender": bpy.app.version_string, "renders": []}
    for name, dress in (("plain", None), ("raytrace", raytrace_material), ("hair", hair)):
        scene = plain_scene()
        record["cards"] = use_card(scene, backend)
        if dress:
            dress(scene)
        for take in (1, 2):
            seconds = render(scene, f"/tmp/warm-{name}-{take}.png")
            record["renders"].append({"scene": name, "take": take, "seconds": seconds})
            print(f"warm_kernels: {name} take {take}: {seconds} s", flush=True)
    with open(out, "w") as written:
        json.dump(record, written, indent=1)


main()
