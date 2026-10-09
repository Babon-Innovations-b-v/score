"""Runs in Blender (blender_rig.py): a fish's rig and its three clips.

The rig is a spine of BONES bones along the body from the snout to the tail's tip, every vertex weighted by where it
lies along it (spine.py), so a fin follows the spine bone beside it.

The clips, each a loop at 30 frames a second, every bone keyed on every frame:
  swim   a bend that travels from the head to the tail, growing towards the tail (WAVE)
  turn   the swim with the body curving into a C to one side and back (the node's own turn is the game's)
  hover  a slow, small tail beat and a gentle rise and fall of the whole body
"""
import math

import bpy
import numpy as np
from mathutils import Quaternion, Vector

import spine

BONES = 8
UP = Vector((0.0, 0.0, 1.0))
# The swim: frames a beat, the largest bend of one bone (radians), how much of a wave the body holds.
SWIM = {"frames": 30, "bend": 0.16, "waves": 0.8}
TURN = {"frames": 30, "bend": 0.16, "waves": 0.8, "curve": 0.12}
HOVER = {"frames": 60, "bend": 0.05, "waves": 0.6, "rise": 0.02}


def spine_armature(meshes):
    """A new armature of BONES chained bones along the fish, and its joints as an array."""
    points = np.vstack([np.array([vertex.co for vertex in mesh.data.vertices]) for mesh in meshes])
    joints = spine.spine_joints(points, spine.body_axes(points), BONES)
    data = bpy.data.armatures.new("spine")
    armature = bpy.data.objects.new("fish", data)
    bpy.context.scene.collection.objects.link(armature)
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode="EDIT")
    parent = None
    for number in range(BONES):
        bone = data.edit_bones.new(f"spine_{number}")
        bone.head, bone.tail = Vector(joints[number]), Vector(joints[number + 1])
        bone.roll = 0.0
        bone.parent = parent
        bone.use_connect = parent is not None
        parent = bone
    bpy.ops.object.mode_set(mode="OBJECT")
    return armature, joints


def skin(meshes, armature, joints):
    """Each mesh weighted to the spine (spine.spine_weights) and bound to it."""
    for mesh in meshes:
        points = np.array([vertex.co for vertex in mesh.data.vertices])
        weights = spine.spine_weights(points, joints)
        for number in range(BONES):
            group = mesh.vertex_groups.new(name=f"spine_{number}")
            for vertex in np.nonzero(weights[:, number] > 0)[0]:
                group.add([int(vertex)], float(weights[vertex, number]), "REPLACE")
        bound = mesh.modifiers.new("skin", "ARMATURE")
        bound.object = armature
        mesh.parent = armature


def turn_about(bone, axis, angle):
    """A pose rotation of `angle` about a world `axis`, in the bone's own frame."""
    local = (bone.matrix_local.to_3x3().inverted() @ axis).normalized()
    return Quaternion(local, angle)


def wave_angle(settings, number, count, frame):
    """One bone's bend at a frame: a sine travelling tailwards, its size growing with the bone's place down the
    body."""
    place = number / max(count - 1, 1)
    size = settings["bend"] * (0.15 + place * place)
    beat = 2 * math.pi * frame / settings["frames"]
    return size * math.sin(beat - 2 * math.pi * settings["waves"] * place)


def key_clip(armature, chain, name, settings):
    """One clip as a new action of the armature, every chain bone keyed on every frame of one loop."""
    action = bpy.data.actions.new(name)
    action.use_fake_user = True
    armature.animation_data_create().action = action
    frames = settings["frames"]
    count = len(chain)
    length = (armature.data.bones[chain[0]].head_local - armature.data.bones[chain[-1]].tail_local).length
    for frame in range(frames + 1):
        phase = frame / frames
        curve = settings.get("curve", 0.0) * math.sin(math.pi * phase) ** 2
        for number, bone_name in enumerate(chain):
            pose = armature.pose.bones[bone_name]
            pose.rotation_mode = "QUATERNION"
            angle = wave_angle(settings, number, count, frame) + (curve if number else 0.0)
            pose.rotation_quaternion = turn_about(pose.bone, UP, angle)
            pose.keyframe_insert("rotation_quaternion", frame=frame)
            if number == 0:
                rise = settings.get("rise", 0.0) * length * math.sin(2 * math.pi * phase)
                pose.location = pose.bone.matrix_local.to_3x3().inverted() @ Vector((0.0, 0.0, rise))
                pose.keyframe_insert("location", frame=frame)
    action.use_frame_range = True
    action.frame_start, action.frame_end = 0, frames
    return action


def rig(meshes, job, report):
    """The fish rigged and keyed; returns its armature."""
    armature, joints = spine_armature(meshes)
    skin(meshes, armature, joints)
    chain = [f"spine_{number}" for number in range(BONES)]
    report["bones"] = len(armature.data.bones)
    report["driven_chain"] = chain
    clips = {"swim": SWIM, "turn": TURN, "hover": HOVER}
    report["clips"] = {}
    for name in job["clips"]:
        key_clip(armature, chain, name, clips[name])
        report["clips"][name] = {"frames": clips[name]["frames"], "loops": True}
    armature.animation_data.action = None
    return armature
