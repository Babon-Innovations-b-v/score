"""The prop route's comparison pictures of one body, one outfit: blender_review.py's stage and light, fixed orthographic
cameras (the views the review of #5 set side by side on 2026-10-10, so a body rendered here is seen as today's
bodies were), on a rented card, never on the owner's PC.

    blender -b -P blender_shots.py -- <body.glb> <out folder> --outfit work [--size 768]

Writes <out>/apose_front.png, apose_side.png and apose_back.png (the bind pose, no clip) and, from 35 degrees, each
SHOTS clip at its share of its length (walk_a and walk_b, sit, wait, point, reach, clap, door, work), each skipped where
the body lacks its clip. A body whose garments carry corrective shapes each clip keys (the people route, route_build.py)
has them in
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
# The review page's clip strip (#5): walking, sitting and the clips whose hands came near the body.
SHOTS = (("walk_a", "walking", 0.25), ("walk_b", "walking", 0.75), ("sit", "sitting", 0.67), ("wait", "waiting", 0.5),
         ("point", "pointing", 0.5), ("reach", "reaching", 0.5), ("clap", "clapping", 0.5), ("door", "door", 0.5),
         ("work", "bench", 0.5))


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
            slots = list(getattr(action, "slots", []))
            keyed = [slot for slot in slots if slot.target_id_type == "KEY" or slot.identifier.startswith("KE")]
            if not any("key_blocks" in curve.data_path for curve in fcurves_of(action)):
                continue
            keys.animation_data.action = action
            if keyed or slots:
                keys.animation_data.action_slot = (keyed or slots)[0]
            taken += 1
            break
    return taken


def play(armature, clip):
    """The clip's action that turns bones, on the armature, in its object slot (blender_review.play keys clips by the
    action's name before its last "_", which a shape key action named after the outfit, "sitting_work", takes over;
    another importer names one merged action by the clip alone); its first and last frames."""
    action = next(action for action in bpy.data.actions
                  if (action.name == clip or action.name.startswith(f"{clip}_"))
                  and any("pose.bones" in curve.data_path for curve in fcurves_of(action)))
    armature.animation_data_create()
    armature.animation_data.action = action
    # An importer that merges a clip's armature and shape keys into one action gives each a slot of its own.
    objects = [slot for slot in getattr(action, "slots", []) if slot.target_id_type == "OBJECT"]
    if objects:
        armature.animation_data.action_slot = objects[0]
    for track in list(armature.animation_data.nla_tracks):
        armature.animation_data.nla_tracks.remove(track)
    start, end = action.frame_range
    return int(start), int(end)


def fcurves_of(action):
    """An action's curves, in Blender 5's layered actions (layers, strips, channel bags) or a legacy one."""
    found = list(getattr(action, "fcurves", []) or [])
    for layer in getattr(action, "layers", []):
        for strip in layer.strips:
            for bag in getattr(strip, "channelbags", []):
                found += list(bag.fcurves)
    return found


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
    # A body baked before its mesh was named for its outfit imports as "Mesh_1": the one mesh that is not the far body.
    shown = options.outfit if options.outfit in meshes else next(name for name in meshes if name != "far")
    blender_review.show_only(meshes, shown)
    armature.animation_data_create()
    armature.animation_data.action = None
    for track in list(armature.animation_data.nla_tracks):
        armature.animation_data.nla_tracks.remove(track)
    rest_shapes(meshes)
    armature.data.pose_position = "REST"
    scene.frame_set(1)
    for name, azimuth in (("apose_front", 0), ("apose_side", 90), ("apose_back", 180)):
        blender_review.camera(scene, azimuth, HEIGHT)
        blender_review.render(scene, f"{options.out}/{name}.png")
    armature.data.pose_position = "POSE"
    blender_review.camera(scene, 35, HEIGHT)
    for name, clip, share in SHOTS:
        try:
            start, end = play(armature, clip)
        except StopIteration:
            print("SHOT", name, "skipped: the body has no clip", clip, flush=True)
            continue
        shaped = shape_keys_follow(meshes, clip)
        frame = start + round((end - start) * share)
        scene.frame_set(frame)
        blender_review.render(scene, f"{options.out}/{name}.png")
        print("SHOT", name, clip, frame, "of", start, end, "shape keys on", shaped, "meshes", flush=True)
    print("SHOTS", options.out, flush=True)


if __name__ == "__main__":
    main()
