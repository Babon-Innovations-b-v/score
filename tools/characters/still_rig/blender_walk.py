"""A rigged still's check frames: its glTF walking `--clip` for `--frames` frames from three sides (front, side, back
three-quarter), on Cycles on the processor at `--samples` (a check, never shipped), one PNG a view and frame in `--out`.

    blender -b --python tools/characters/still_rig/blender_walk.py -- <body.glb> --out <folder>
        [--clip walking] [--frames 24] [--step 1] [--samples 16] [--size 480]

--step takes every that many frames of the clip, so 12 frames at step 3 cover the whole 36-frame stride.
"""
import argparse
import math
import pathlib
import sys

import bpy
import mathutils

VIEWS = {"front": 0.0, "side": 90.0, "back": 215.0}  # degrees round the body from its front (+y after the import: the glTF stands it facing -z)
DISTANCE, AIM_HEIGHT, LENS = 4.2, 0.95, 50.0


def options():
    parser = argparse.ArgumentParser()
    parser.add_argument("body")
    parser.add_argument("--out", required=True)
    parser.add_argument("--clip", default="walking")
    parser.add_argument("--frames", type=int, default=24)
    parser.add_argument("--step", type=int, default=1)
    parser.add_argument("--samples", type=int, default=16)
    parser.add_argument("--size", type=int, default=480)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1:])


def imported(path, clip):
    """The body imported and its armature playing `clip` (the importer's action of that name)."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=path)
    armature = next(item for item in bpy.data.objects if item.type == "ARMATURE")
    action = next(action for action in bpy.data.actions if action.name.split("_")[0] == clip
                  or action.name.startswith(clip))
    armature.animation_data_create()
    armature.animation_data.action = action
    for item in bpy.data.objects:
        if item.type == "MESH" and item.name.startswith("far"):
            item.hide_render = True
    return armature, action


def staged(size, samples):
    """A floor, a sun and a sky light, Cycles on the processor."""
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.render.resolution_x = scene.render.resolution_y = size
    scene.render.film_transparent = False
    world = bpy.data.worlds.new("sky")
    world.color = (0.45, 0.47, 0.5)
    scene.world = world
    bpy.ops.mesh.primitive_plane_add(size=12)
    sun = bpy.data.lights.new("sun", "SUN")
    sun.energy = 3.0
    lamp = bpy.data.objects.new("sun", sun)
    lamp.rotation_euler = (math.radians(50), 0.0, math.radians(30))
    scene.collection.objects.link(lamp)
    camera = bpy.data.objects.new("camera", bpy.data.cameras.new("camera"))
    camera.data.lens = LENS
    scene.collection.objects.link(camera)
    scene.camera = camera
    return scene, camera


def aimed(camera, degrees):
    """The camera DISTANCE from the body's middle, `degrees` round from its front, a little above, looking at it."""
    turn = math.radians(degrees)
    eye = mathutils.Vector((math.sin(turn) * DISTANCE, math.cos(turn) * DISTANCE, AIM_HEIGHT + 0.5))
    camera.location = eye
    camera.rotation_euler = (mathutils.Vector((0.0, 0.0, AIM_HEIGHT)) - eye).to_track_quat("-Z", "Y").to_euler()


def main():
    found = options()
    armature, action = imported(found.body, found.clip)
    scene, camera = staged(found.size, found.samples)
    out = pathlib.Path(found.out)
    out.mkdir(parents=True, exist_ok=True)
    start = int(action.frame_range[0])
    for name, degrees in VIEWS.items():
        aimed(camera, degrees)
        for frame in range(found.frames):
            scene.frame_set(start + frame * found.step)
            scene.render.filepath = str(out / f"{name}_{frame:02d}.png")
            bpy.ops.render.render(write_still=True)
    print("blender_walk:", found.frames * len(VIEWS), "frames of", action.name, "in", out, flush=True)


if __name__ == "__main__":
    main()
