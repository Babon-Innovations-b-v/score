"""Runs in Blender (blender_rig.py): a four-legged animal's clips on its UniRig skeleton.

UniRig names no bone, so the parts are found from the skeleton's shape (legs.py): the legs are the four chains that end
lowest, the head's chain the one that ends furthest forward, the tail's the one that ends furthest back. Each leg gets
an inverse-kinematics goal at its foot; the clips move the goals and the body, and each clip is baked into plain bone
keys (the goals and their constraints are gone from the file).

The clips, each a loop at 30 frames a second:
  idle  breathing (the chest rises and falls) and a slow look to one side and the other, the feet planted
  walk  the four-beat walk (legs.PHASES), the feet sliding back under the body at the walk's speed while on the
        ground (the travel is taken off: the game moves the node at `walk_speed` m/s, in rig.json)
  sit   the hind feet drawn forward, the hips lowered and tipped back, the hind legs folding under them, breathing
"""
import math

import bpy
import numpy as np
from mathutils import Quaternion, Vector

import legs

UP = Vector((0.0, 0.0, 1.0))
FORWARD = Vector((0.0, -1.0, 0.0))
SIDE = Vector((1.0, 0.0, 0.0))  # the animal's left, facing -y
# Bones of a leg the goal moves (from the foot up): the shoulder or hip above them holds still.
IK_BONES = 4
WALK = {"frames": 30, "stride": 0.6, "lift": 0.1, "bob": 0.015}
IDLE = {"frames": 90, "breath": 0.02, "look": 0.45}
SIT = {"frames": 60, "drop": 0.35, "tip": 0.6, "tuck": 0.3, "breath": 0.02}


def bone_table(armature):
    """The bones in order, each one's end point (its tail, world space) and its parent's index."""
    bones = list(armature.data.bones)
    index = {bone.name: number for number, bone in enumerate(bones)}
    ends = np.array([armature.matrix_world @ bone.tail_local for bone in bones])
    parents = [index[bone.parent.name] if bone.parent else -1 for bone in bones]
    return bones, ends, parents


def chain_ending(bones, parents, ends, direction, skip):
    """The chain of bone names from the first below a branch to the leaf that ends furthest along `direction`, the
    legs' joints left out."""
    below = legs.children(parents)
    leaves = [joint for joint in range(len(bones)) if not below[joint] and joint not in skip]
    leaf = max(leaves, key=lambda joint: ends[joint] @ np.array(direction))
    return [bones[joint].name for joint in legs.chain_to(leaf, parents, below)]


def find_parts(armature, report):
    """The legs by name, the head's chain and the tail's chain, as bone names; recorded in the report."""
    bones, ends, parents = bone_table(armature)
    chains = legs.leg_chains(ends, parents, tuple(UP))
    named = legs.name_legs(chains, ends, tuple(FORWARD), tuple(SIDE))
    in_legs = {joint for chain in chains for joint in chain}
    parts = {"legs": {name: [bones[joint].name for joint in chain] for name, chain in named.items()},
             "head": chain_ending(bones, parents, ends, FORWARD, in_legs),
             "tail": chain_ending(bones, parents, ends, -FORWARD, in_legs),
             "root": next(bone.name for bone in bones if bone.parent is None)}
    report["parts"] = parts
    return parts


def add_goals(armature, parts):
    """An IK goal bone at each foot, with its constraint on the leg's last bone; the goals' names by leg."""
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode="EDIT")
    goals = {}
    for leg, chain in parts["legs"].items():
        foot = armature.data.edit_bones[chain[-1]]
        goal = armature.data.edit_bones.new(f"goal_{leg}")
        goal.head = foot.tail
        goal.tail = foot.tail + Vector((0.0, 0.0, 0.05))
        goal.use_deform = False
        goals[leg] = goal.name
    bpy.ops.object.mode_set(mode="POSE")
    for leg, chain in parts["legs"].items():
        reach = armature.pose.bones[chain[-1]].constraints.new("IK")
        reach.target, reach.subtarget = armature, goals[leg]
        reach.chain_count = min(IK_BONES, len(chain))
        reach.use_tail = True
    bpy.ops.object.mode_set(mode="OBJECT")
    return goals


def leg_length(armature, chain):
    """A leg's height from its first joint to its foot."""
    bones = armature.data.bones
    return (bones[chain[0]].head_local - bones[chain[-1]].tail_local).length


def turn_bone(armature, name, axis, angle):
    """Turn a bone by `angle` about a world `axis`, in its own frame."""
    pose = armature.pose.bones[name]
    pose.rotation_mode = "QUATERNION"
    local = (pose.bone.matrix_local.to_3x3().inverted() @ axis).normalized()
    pose.rotation_quaternion = Quaternion(local, angle)


def move_bone(armature, name, offset):
    """Move a bone by a world offset from its rest place."""
    pose = armature.pose.bones[name]
    pose.location = pose.bone.matrix_local.to_3x3().inverted() @ offset


def key_all(armature, frame):
    """Key every bone's place and turn at a frame."""
    for pose in armature.pose.bones:
        pose.rotation_mode = "QUATERNION"
        pose.keyframe_insert("rotation_quaternion", frame=frame)
        pose.keyframe_insert("location", frame=frame)


def rest(armature):
    """Every bone back to its rest pose."""
    for pose in armature.pose.bones:
        pose.location = (0.0, 0.0, 0.0)
        pose.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)


def spread_turn(armature, chain, axis, angle):
    """A turn shared evenly along a chain (a neck or a tail), so it bends rather than kinks."""
    for name in chain:
        turn_bone(armature, name, axis, angle / len(chain))


def walk_pose(armature, parts, goals, phase, height):
    """The walk at `phase` of its cycle: the feet on their paths, the body bobbing twice a cycle, the tail swaying."""
    stride = WALK["stride"] * height
    for leg, goal in goals.items():
        ahead, lift = legs.foot_path(phase - legs.PHASES[leg], stride, WALK["lift"] * height)
        move_bone(armature, goal, FORWARD * ahead + UP * lift)
    move_bone(armature, parts["root"], UP * (WALK["bob"] * height * math.cos(4 * math.pi * phase)))
    spread_turn(armature, parts["tail"], UP, 0.25 * math.sin(2 * math.pi * phase))
    spread_turn(armature, parts["head"], SIDE, 0.06 * math.sin(4 * math.pi * phase))


def idle_pose(armature, parts, phase, height):
    """The idle at `phase`: three breaths and one slow look left and right a loop."""
    breath = IDLE["breath"] * height * (0.5 - 0.5 * math.cos(6 * math.pi * phase))
    move_bone(armature, parts["root"], UP * breath)
    spread_turn(armature, parts["head"], UP, IDLE["look"] * math.sin(2 * math.pi * phase))
    spread_turn(armature, parts["tail"], UP, 0.1 * math.sin(4 * math.pi * phase))


def sit_pose(armature, parts, goals, phase, height):
    """The sit at `phase`: the hind feet drawn forward under the hips, the hips down and tipped back (tail down, chest
    up), the head kept level, breathing."""
    for leg in ("back_left", "back_right"):
        move_bone(armature, goals[leg], FORWARD * SIT["tuck"] * height)
    breath = SIT["breath"] * height * (0.5 - 0.5 * math.cos(4 * math.pi * phase))
    move_bone(armature, parts["root"], UP * (breath - SIT["drop"] * height))
    turn_bone(armature, parts["root"], SIDE, -SIT["tip"])
    spread_turn(armature, parts["head"], SIDE, SIT["tip"])
    spread_turn(armature, parts["tail"], SIDE, 0.3)


def driving_action(armature, name, frames, pose_at):
    """A clip's driving keys (goals and body) as a new action, `pose_at(phase)` setting each frame's pose."""
    action = bpy.data.actions.new(f"{name}_driving")
    armature.animation_data_create().action = action
    for frame in range(frames + 1):
        rest(armature)
        pose_at(frame / frames)
        key_all(armature, frame)
    return action


def reach_miss(armature, parts, goals, frames):
    """The farthest any foot ends from its goal over a clip's frames, in metres: where a leg cannot reach, its foot
    lags its goal and slides on the ground once the game moves the node."""
    worst = 0.0
    for frame in range(frames + 1):
        bpy.context.scene.frame_set(frame)
        for leg, chain in parts["legs"].items():
            foot = armature.matrix_world @ armature.pose.bones[chain[-1]].tail
            goal = armature.matrix_world @ armature.pose.bones[goals[leg]].head
            worst = max(worst, (foot - goal).length)
    return worst


def bake(armature, name, frames):
    """The current action's visible pose, constraints and all, baked into plain keys of the deforming bones as the
    clip's action."""
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode="POSE")
    for pose in armature.pose.bones:
        # Blender 5 keeps a bone's selection on its pose bone; older releases on the bone.
        holder = pose if hasattr(pose, "select") else pose.bone
        holder.select = pose.bone.use_deform
    driving = armature.animation_data.action
    bpy.ops.nla.bake(frame_start=0, frame_end=frames, only_selected=True, visual_keying=True,
                     clear_constraints=False, use_current_action=False, bake_types={"POSE"})
    baked = armature.animation_data.action
    baked.name = name
    baked.use_fake_user = True
    baked.use_frame_range = True
    baked.frame_start, baked.frame_end = 0, frames
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.data.actions.remove(driving)
    return baked


def drop_goals(armature, goals, parts):
    """The goals and their constraints out of the rig, and out of every clip."""
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode="POSE")
    for chain in parts["legs"].values():
        pose = armature.pose.bones[chain[-1]]
        for constraint in list(pose.constraints):
            pose.constraints.remove(constraint)
    bpy.ops.object.mode_set(mode="EDIT")
    for goal in goals.values():
        armature.data.edit_bones.remove(armature.data.edit_bones[goal])
    bpy.ops.object.mode_set(mode="OBJECT")


def rig(meshes, armature, job, report):
    """The animal's clips on its UniRig skeleton; returns the armature."""
    if armature is None:
        raise RuntimeError("a four-legged animal needs its UniRig skeleton (route.py rigs it first)")
    parts = find_parts(armature, report)
    height = max(leg_length(armature, chain) for chain in parts["legs"].values())
    goals = add_goals(armature, parts)
    clips = {"walk": (WALK["frames"], lambda phase: walk_pose(armature, parts, goals, phase, height)),
             "idle": (IDLE["frames"], lambda phase: idle_pose(armature, parts, phase, height)),
             "sit": (SIT["frames"], lambda phase: sit_pose(armature, parts, goals, phase, height))}
    report["clips"] = {}
    for name in job["clips"]:
        frames, pose_at = clips[name]
        driving_action(armature, name, frames, pose_at)
        miss = reach_miss(armature, parts, goals, frames)
        bake(armature, name, frames)
        report["clips"][name] = {"frames": frames, "loops": True, "foot_miss_m": round(miss, 4)}
    drop_goals(armature, goals, parts)
    armature.animation_data.action = None
    rest(armature)
    stride = WALK["stride"] * height
    report["leg_length_m"] = round(height, 3)
    report["walk_speed"] = round(stride / (legs.DUTY * WALK["frames"] / 30), 3)
    report["bones"] = len(armature.data.bones)
    return armature
