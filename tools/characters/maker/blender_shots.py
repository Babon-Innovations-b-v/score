"""The prop route's comparison pictures of one body, one outfit: blender_review.py's stage and light, fixed orthographic
cameras (the views the review of #5 set side by side on 2026-10-10, so a body rendered here is seen as today's
bodies were), on a rented card, never on the owner's PC.

    blender -b -P blender_shots.py -- <body.glb> <out folder> --outfit work [--size 768]

Writes <out>/apose_front.png and apose_side.png (the bind pose, no clip), walk_a.png and walk_b.png (the walking clip
at a quarter and three quarters of its length) and sit.png (the sitting clip at two thirds), from 35 degrees for the
clips. A settled body's garments carry corrective shapes each clip keys (garment_bake.py): the importer puts them in
the clip's action under a slot of their own, which is given to the outfit's shape keys with the armature's.
"""
import argparse
import pathlib
import sys

import bpy

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import blender_review  # noqa: E402

HEIGHT = 1.8
SAMPLES = 64
SHOTS = (("walk_a", "walking", 0.25), ("walk_b", "walking", 0.75), ("sit", "sitting", 0.67))


def arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("glb")
    parser.add_argument("out")
    parser.add_argument("--outfit", required=True)
    parser.add_argument("--size", type=int, default=768)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1:])


def shape_keys_follow(meshes, clip):
    """The outfit's shape keys given the clip's action and its slot for them (none: no corrective shapes); how many
    meshes took one."""
    taken = 0
    actions = [action for action in bpy.data.actions if action.name.rsplit("_", 1)[0] == clip
               or action.name.startswith(f"{clip}_")]
    for thing in meshes.values():
        keys = getattr(thing.data, "shape_keys", None)
        if keys is None:
            continue
        keys.animation_data_create()
        for action in actions:
            slots = [slot for slot in getattr(action, "slots", []) if slot.target_id_type == "KEY"]
            if slots:
                keys.animation_data.action = action
                keys.animation_data.action_slot = slots[0]
                taken += 1
                break
    return taken


def rest_shapes(meshes):
    """Every shape key's action taken off, so the bind pose shows the mesh as built."""
    for thing in meshes.values():
        keys = getattr(thing.data, "shape_keys", None)
        if keys is not None and keys.animation_data is not None:
            keys.animation_data.action = None
            for block in keys.key_blocks[1:]:
                block.value = 0.0


def main():
    options = arguments()
    scene = blender_review.stage(options.size)
    scene.cycles.samples = SAMPLES
    armature, meshes = blender_review.character(options.glb)
    print("MESHES", sorted(meshes), "ACTIONS", sorted(action.name for action in bpy.data.actions), flush=True)
    blender_review.show_only(meshes, options.outfit)
    armature.animation_data_create()
    armature.animation_data.action = None
    for track in list(armature.animation_data.nla_tracks):
        armature.animation_data.nla_tracks.remove(track)
    rest_shapes(meshes)
    armature.data.pose_position = "REST"
    scene.frame_set(1)
    for name, azimuth in (("apose_front", 0), ("apose_side", 90)):
        blender_review.camera(scene, azimuth, HEIGHT)
        blender_review.render(scene, f"{options.out}/{name}.png")
    armature.data.pose_position = "POSE"
    blender_review.camera(scene, 35, HEIGHT)
    for name, clip, share in SHOTS:
        start, end = blender_review.play(armature, clip)
        shaped = shape_keys_follow(meshes, clip)
        frame = start + round((end - start) * share)
        scene.frame_set(frame)
        blender_review.render(scene, f"{options.out}/{name}.png")
        print("SHOT", name, clip, frame, "of", start, end, "shape keys on", shaped, "meshes", flush=True)
    print("SHOTS", options.out, flush=True)


if __name__ == "__main__":
    main()
