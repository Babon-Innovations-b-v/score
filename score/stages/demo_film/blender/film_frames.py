"""Runs inside Blender (a demo-film frame job on a rented card, tools/cloud/blender_cloud.py): usd_views.py's
frames of a film, each with the camera's motion blur.

    blender -b -P film_frames.py -- <stage.usda> <views.json> <out folder>

A view may carry "blur": {"eye", "aim", "up", "shutter", "codes"}: the camera of the film's next frame, `codes` time
codes on, and the share of a frame the shutter stays open from the view's moment (score/stages/demo_film
motion_blurred). Its camera is keyed at the view's moment and at the next one, so Cycles blurs what moves while the
shutter is open: the camera, and the stage's moving things by their transforms; never a mesh's own deformation (a
skinned body's), which would make Cycles evaluate it twice a frame. A view without one is drawn as usd_views.py draws
it, with no blur.
"""
import pathlib
import sys

import bpy
from bpy_extras import anim_utils

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[4] / "tools/blender/inside"))
import usd_views  # noqa: E402  (tools/blender/inside, shipped with every job)

DRAWN = usd_views.camera


def keyed(item, frame):
    """The camera's place and turn keyed at `frame`."""
    item.keyframe_insert("location", frame=frame)
    item.keyframe_insert("rotation_quaternion", frame=frame)


def moving_camera(scene, view):
    """usd_views.camera, then for a view with "blur" the camera keyed from its own place now to the next frame's, in a
    straight line, and the scene's shutter open for its share of the frame."""
    DRAWN(scene, view)
    blur = view.get("blur")
    scene.render.use_motion_blur = bool(blur)
    if not blur:
        return
    item = scene.camera
    DRAWN(scene, dict(view, name=f"{view['name']}-next", eye=blur["eye"], aim=blur["aim"], up=blur["up"]))
    later = scene.camera
    there = later.matrix_world.to_quaternion(), later.matrix_world.translation.copy()
    bpy.data.objects.remove(later)
    scene.camera = item
    item.rotation_mode = "QUATERNION"
    now = scene.frame_current
    keyed(item, now)
    turn = there[0]
    if item.rotation_quaternion.dot(turn) < 0:  # the same turn the short way round
        turn.negate()
    item.rotation_quaternion, item.location = turn, there[1]
    keyed(item, now + blur["codes"])
    animation = item.animation_data
    for curve in anim_utils.action_get_channelbag_for_slot(animation.action, animation.action_slot).fcurves:
        for key in curve.keyframe_points:
            key.interpolation = "LINEAR"
    scene.frame_set(now)
    scene.render.motion_blur_position = "START"
    scene.render.motion_blur_shutter = blur["shutter"] * blur["codes"]


def without_deformation():
    """No object's deformation blurred: only the camera and moving transforms are."""
    for item in bpy.data.objects:
        item.cycles.use_deform_motion = False


if __name__ == "__main__":
    usd_views.camera = moving_camera
    bpy.app.handlers.render_init.append(lambda *_: without_deformation())
    usd_views.main()
