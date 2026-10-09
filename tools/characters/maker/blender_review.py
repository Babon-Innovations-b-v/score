"""The review pictures of one made character, rendered with Cycles on the card the chain ran on: a turntable of each
outfit standing, and frames through each clip in the first outfit, seen from three quarters.

    blender -b -P blender_review.py -- <character.glb> <out folder> [--outfits work space] [--clips standing walking]
        [--angles 8] [--frames 6] [--size 512]

Writes <out>/turn_<outfit>_<angle>.png and <out>/clip_<clip>_<frame>.png. The glTF's mesh nodes are the outfits and
the bare far body (`far`), the skinned meshes; every one but the one shown is hidden. A clip is an action of the file's armature, picked
by its name (glTF animations import as actions named after them).
"""
import argparse
import math
import sys

import bpy
import mathutils


def arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("glb")
    parser.add_argument("out")
    parser.add_argument("--outfits", nargs="*", default=None)
    parser.add_argument("--clips", nargs="*", default=None)
    parser.add_argument("--angles", type=int, default=8)
    parser.add_argument("--frames", type=int, default=6)
    parser.add_argument("--size", type=int, default=512)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1:])


def stage(size):
    """An empty scene with Cycles on the card, a soft sky, a key light and a ground that only catches shadows."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    preferences = bpy.context.preferences.addons["cycles"].preferences
    for device_type in ("OPTIX", "CUDA"):
        try:
            preferences.compute_device_type = device_type
            preferences.get_devices()
            if any(device.type == device_type for device in preferences.devices):
                break
        except TypeError:
            continue
    for device in preferences.devices:
        device.use = device.type != "CPU"
    scene.cycles.device = "GPU"
    scene.cycles.samples = 32
    scene.cycles.use_denoising = True
    scene.render.resolution_x = scene.render.resolution_y = size
    scene.render.film_transparent = False
    scene.view_settings.view_transform = "Standard"
    world = bpy.data.worlds.new("sky")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.62, 0.64, 0.68, 1.0)
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.8
    scene.world = world
    sun = bpy.data.objects.new("key", bpy.data.lights.new("key", "SUN"))
    sun.data.energy = 3.0
    sun.rotation_euler = (math.radians(50), 0, math.radians(35))
    scene.collection.objects.link(sun)
    bpy.ops.mesh.primitive_plane_add(size=20)
    bpy.context.object.is_shadow_catcher = True
    return scene


def character(path):
    """The imported character: its armature and its mesh objects by node name."""
    bpy.ops.import_scene.gltf(filepath=path)
    armature = next(thing for thing in bpy.context.scene.objects if thing.type == "ARMATURE")
    meshes = {thing.name: thing for thing in bpy.context.scene.objects
              if thing.type == "MESH" and any(modifier.type == "ARMATURE" for modifier in thing.modifiers)}
    return armature, meshes


def clip_actions():
    """Each clip's action by the clip's name (the importer names them `<clip>_<armature>`)."""
    return {action.name.rsplit("_", 1)[0]: action for action in bpy.data.actions}


def show_only(meshes, wanted):
    for name, thing in meshes.items():
        hidden = name != wanted
        thing.hide_render = hidden
        thing.hide_viewport = hidden


def camera(scene, azimuth, height):
    """An orthographic camera looking at the standing figure from `azimuth` degrees (0 the front)."""
    data = bpy.data.cameras.new(f"camera{azimuth}")
    data.type = "ORTHO"
    data.ortho_scale = height * 1.25
    thing = bpy.data.objects.new(f"camera{azimuth}", data)
    scene.collection.objects.link(thing)
    turn = math.radians(azimuth)
    # Blender's glTF import stands y-up files z-up; the character faces +y in Blender (checked on a render).
    target = mathutils.Vector((0.0, 0.0, height * 0.5))
    thing.location = target + mathutils.Vector((math.sin(turn), math.cos(turn), 0.12)) * 6.0
    thing.rotation_euler = (target - thing.location).to_track_quat("-Z", "Y").to_euler()
    scene.camera = thing


def play(armature, clip):
    """The clip's action on the armature; its first and last frames."""
    action = clip_actions()[clip]
    armature.animation_data_create()
    armature.animation_data.action = action
    for track in list(armature.animation_data.nla_tracks):
        armature.animation_data.nla_tracks.remove(track)
    start, end = action.frame_range
    return int(start), int(end)


def render(scene, path):
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


def main():
    options = arguments()
    scene = stage(options.size)
    armature, meshes = character(options.glb)
    outfits = options.outfits or [name for name in meshes if name != "far"]
    clips = options.clips or sorted(clip_actions())
    height = 1.8
    play(armature, "standing" if "standing" in clip_actions() else clips[0])
    for outfit in outfits:
        show_only(meshes, outfit)
        for index in range(options.angles):
            azimuth = 360 * index // options.angles
            camera(scene, azimuth, height)
            scene.frame_set(1)
            render(scene, f"{options.out}/turn_{outfit}_{azimuth:03d}.png")
    show_only(meshes, outfits[0])
    camera(scene, 35, height)
    for clip in clips:
        start, end = play(armature, clip)
        for index in range(options.frames):
            frame = start + (end - start) * index // max(1, options.frames - 1)
            scene.frame_set(frame)
            render(scene, f"{options.out}/clip_{clip}_{index}.png")
    print("REVIEW", options.out, len(outfits), "outfits", len(clips), "clips", flush=True)


if __name__ == "__main__":
    main()
