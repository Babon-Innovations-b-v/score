"""The people route's proof pictures (score #10), rendered on the PC at low resolution with Blender's CPU (Cycles,
`-t 4`): the same cameras for the body before and after, so the two can be set side by side.

    blender -b -t 4 -P blender_route_shots.py -- <body.glb> <out folder> stills [--size 640]
    blender -b -t 4 -P blender_route_shots.py -- <body.glb> <out folder> turntable [--size 480] [--frames 48]
    blender -b -t 4 -P blender_route_shots.py -- <body.glb> <out folder> clip --clip walking [--size 480]

`stills` writes STILLS: the head close up from the front and three quarters (bind pose), and the frames that
stretched before (sitting, walking and the worst clips' frames, from blender_shots.py's 35 degrees and from close in).
`turntable` and `clip` write an mp4 (Workbench, the textures flat-lit: a moving check, not a look). Only the outfit
node (`work`) is shown. A settled body's per-clip shape keys follow its clip (blender_shots.shape_keys_follow); the
route's corrective shapes are keyed in every clip the same way.
"""
import argparse
import math
import pathlib
import sys

import bpy
import mathutils

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import blender_review  # noqa: E402
import blender_shots  # noqa: E402

SAMPLES = 24
OUTFIT = "work"
# name: (clip or None for the bind pose, share of the clip, camera azimuth in degrees, aim height, distance, lens)
STILLS = {
    "head_front": (None, 0.0, 0, 1.6, 0.9, 85),
    "head_three_quarter": (None, 0.0, 35, 1.6, 0.9, 85),
    "head_side": (None, 0.0, 90, 1.6, 0.9, 85),
    "neck_front": (None, 0.0, 20, 1.46, 0.6, 85),
    "neck_back": (None, 0.0, 200, 1.48, 0.6, 85),
    "sitting_whole": ("sitting", 0.67, 35, 0.6, 3.2, 50),
    "sitting_close": ("sitting", 0.67, 300, 0.7, 1.6, 50),
    "walking_whole": ("walking", 0.25, 35, 0.95, 4.0, 50),
    "walking_close": ("walking", 0.25, 300, 1.2, 1.6, 50),
    "reaching_whole": ("reaching", 0.5, 35, 1.0, 4.0, 50),
    "cheering_whole": ("cheering", 0.5, 35, 1.0, 4.0, 50),
    "lifting_whole": ("lifting", 0.5, 35, 0.8, 4.0, 50),
}


def arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("glb")
    parser.add_argument("out")
    parser.add_argument("mode", choices=("stills", "turntable", "clip"))
    parser.add_argument("--size", type=int, default=640)
    parser.add_argument("--frames", type=int, default=48)
    parser.add_argument("--clip", default="walking")
    parser.add_argument("--only", nargs="*", help="stills: only these")
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1:])


def on_cpu(scene, size):
    """The review stage's Cycles moved to the CPU at a low sample count."""
    scene.cycles.device = "CPU"
    scene.cycles.samples = SAMPLES
    scene.render.resolution_x, scene.render.resolution_y = size, size
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 4


def perspective(scene, azimuth, aim, distance, lens):
    """A camera `distance` from a point `aim` metres up the figure's line, from `azimuth` degrees (0 the front)."""
    data = bpy.data.cameras.new(f"camera{azimuth}")
    data.lens = lens
    thing = bpy.data.objects.new(f"camera{azimuth}", data)
    scene.collection.objects.link(thing)
    turn = math.radians(azimuth)
    target = mathutils.Vector((0.0, 0.0, aim))
    thing.location = target + mathutils.Vector((math.sin(turn), math.cos(turn), 0.08)) * distance
    thing.rotation_euler = (target - thing.location).to_track_quat("-Z", "Y").to_euler()
    scene.camera = thing
    return thing


def posed(scene, armature, meshes, clip, share):
    """The figure in a clip at its share of its length, or at its bind pose (clip None): the frame shown."""
    if clip is None:
        armature.animation_data_create()
        armature.animation_data.action = None
        blender_shots.rest_shapes(meshes)
        armature.data.pose_position = "REST"
        scene.frame_set(1)
        return 1
    armature.data.pose_position = "POSE"
    start, end = blender_shots.play(armature, clip)
    blender_shots.shape_keys_follow(meshes, clip)
    frame = start + round((end - start) * share)
    scene.frame_set(frame)
    return frame


def figure(path):
    """The imported body with only its outfit shown: armature and meshes."""
    armature, meshes = blender_review.character(path)
    shown = OUTFIT if OUTFIT in meshes else next(name for name in meshes if name != "far")
    blender_review.show_only(meshes, shown)
    return armature, meshes


def stills(options):
    scene = blender_review.stage(options.size)
    on_cpu(scene, options.size)
    armature, meshes = figure(options.glb)
    for name, (clip, share, azimuth, aim, distance, lens) in STILLS.items():
        if options.only and name not in options.only:
            continue
        frame = posed(scene, armature, meshes, clip, share)
        perspective(scene, azimuth, aim, distance, lens)
        blender_review.render(scene, f"{options.out}/{name}.png")
        print("STILL", name, clip, frame, flush=True)


def flat_stage(size):
    """A Workbench scene: textures, studio light, a plain grey world, mp4 output."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "TEXTURE"
    scene.display.shading.show_shadows = True
    scene.render.resolution_x, scene.render.resolution_y = size, size
    world = bpy.data.worlds.new("sky")
    world.color = (0.62, 0.64, 0.68)
    scene.world = world
    if hasattr(scene.render.image_settings, "media_type"):  # Blender 5 picks video output first; 4.2 has no such step
        scene.render.image_settings.media_type = "VIDEO"
    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.fps = 30
    return scene


def turntable(options):
    scene = flat_stage(options.size)
    armature, meshes = figure(options.glb)
    posed(scene, armature, meshes, None, 0.0)
    holder = bpy.data.objects.new("turn", None)
    scene.collection.objects.link(holder)
    camera = perspective(scene, 0, 0.95, 4.2, 50)
    camera.parent = holder
    holder.rotation_euler = (0, 0, 0)
    holder.keyframe_insert("rotation_euler", frame=1)
    holder.rotation_euler = (0, 0, 2 * math.pi * (options.frames - 1) / options.frames)
    holder.keyframe_insert("rotation_euler", frame=options.frames)
    scene.frame_start, scene.frame_end = 1, options.frames
    armature.data.pose_position = "REST"
    scene.render.filepath = f"{options.out}/turntable.mp4"
    bpy.ops.render.render(animation=True)
    print("TURNTABLE", scene.render.filepath, flush=True)


def clip_film(options):
    scene = flat_stage(options.size)
    armature, meshes = figure(options.glb)
    start, end = blender_shots.play(armature, options.clip)
    blender_shots.shape_keys_follow(meshes, options.clip)
    armature.data.pose_position = "POSE"
    perspective(scene, 35, 0.95, 4.0, 50)
    scene.frame_start, scene.frame_end = start, end
    scene.render.filepath = f"{options.out}/{options.clip}.mp4"
    bpy.ops.render.render(animation=True)
    print("CLIP", scene.render.filepath, flush=True)


def main():
    options = arguments()
    pathlib.Path(options.out).mkdir(parents=True, exist_ok=True)
    {"stills": stills, "turntable": turntable, "clip": clip_film}[options.mode](options)


if __name__ == "__main__":
    main()
