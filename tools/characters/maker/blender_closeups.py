"""Close-up pictures of a body file at its joins: a wrist or an ankle, in one outfit, at one moment of one clip, framed
on that joint, so a before and an after can be laid side by side with the very same cameras.

    blender -b -P blender_closeups.py -- <character.glb> <shots.json> <out folder> [--size 640]

shots.json is a list of {"name", "outfit", "clip", "at" (0 to 1 through the clip), "joint", "azimuth" (degrees round
the body, 0 its front), "height" (metres above or below the joint), "span" (metres the picture is across)}. Writes
<out>/<name>.png for each. Rendered with Workbench in each part's own colour against a plain light grey, so whatever is
seen through a gap is the background: the pictures are for joins, not for the look (the review renders are).
"""
import argparse
import json
import math
import pathlib
import sys

import bpy
import mathutils


def arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("glb")
    parser.add_argument("shots")
    parser.add_argument("out")
    parser.add_argument("--size", type=int, default=640)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1:])


def stage(size):
    """An empty scene drawn by Workbench in the parts' own colours on a light grey world."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.world = bpy.data.worlds.new("plain")
    scene.world.color = (0.82, 0.82, 0.84)
    scene.render.resolution_x = scene.render.resolution_y = size
    scene.render.film_transparent = False
    return scene


def colour_materials():
    """Each material's viewport colour from its base colour, where it has one, so Workbench draws it."""
    for material in bpy.data.materials:
        if not material.use_nodes:
            continue
        shader = next((node for node in material.node_tree.nodes if node.type == "BSDF_PRINCIPLED"), None)
        if shader is None:
            continue
        base = shader.inputs["Base Color"]
        colour = list(base.default_value)
        if base.is_linked:
            image = next((node.image for node in material.node_tree.nodes if node.type == "TEX_IMAGE" and node.image),
                         None)
            if image is not None and image.pixels:
                pixels = image.pixels[:]
                count = len(pixels) // 4
                colour = [sum(pixels[channel::4]) / count for channel in range(3)] + [1.0]
        material.diffuse_color = colour


def show_only(meshes, outfit):
    """Only the outfit's skinned mesh drawn (the review's way: mesh objects by node name)."""
    for name, thing in meshes.items():
        thing.hide_render = name != outfit


def pose(armature, clip, at):
    """The armature at `at` (0 to 1) through the named clip (the importer names its action `<clip>_<armature>`)."""
    action = {action.name.rsplit("_", 1)[0]: action for action in bpy.data.actions}[clip]
    armature.animation_data_create()
    armature.animation_data.action = action
    for track in list(armature.animation_data.nla_tracks):
        armature.animation_data.nla_tracks.remove(track)
    start, end = action.frame_range
    frame = int(round(start + (end - start) * at))
    bpy.context.scene.frame_set(frame)
    bpy.context.view_layer.update()


def aim(scene, target, azimuth, height, span):
    """An orthographic camera `span` across, looking level-ish at `target` from `azimuth` degrees."""
    data = bpy.data.cameras.new("closeup")
    data.type = "ORTHO"
    data.ortho_scale = span
    thing = bpy.data.objects.new("closeup", data)
    scene.collection.objects.link(thing)
    turn = math.radians(azimuth)
    # Blender stands the y-up file z-up with the person facing +y (the review renders' finding).
    eye = target + mathutils.Vector((math.sin(turn) * 2.0, math.cos(turn) * 2.0, height))
    thing.location = eye
    thing.rotation_euler = (target - eye).to_track_quat("-Z", "Y").to_euler()
    scene.camera = thing
    return thing


def main():
    wanted = arguments()
    scene = stage(wanted.size)
    bpy.ops.import_scene.gltf(filepath=wanted.glb)
    colour_materials()
    armature = next(thing for thing in scene.objects if thing.type == "ARMATURE")
    meshes = {thing.name: thing for thing in scene.objects
              if thing.type == "MESH" and any(modifier.type == "ARMATURE" for modifier in thing.modifiers)}
    out = pathlib.Path(wanted.out)
    out.mkdir(parents=True, exist_ok=True)
    for shot in json.loads(pathlib.Path(wanted.shots).read_text()):
        show_only(meshes, shot["outfit"])
        pose(armature, shot["clip"], shot["at"])
        bone = armature.pose.bones[shot["joint"]]
        target = armature.matrix_world @ bone.head
        camera = aim(scene, target, shot["azimuth"], shot["height"], shot["span"])
        scene.render.filepath = str(out / f"{shot['name']}.png")
        bpy.ops.render.render(write_still=True)
        bpy.data.objects.remove(camera)


main()
