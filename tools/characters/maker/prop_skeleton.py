"""SOMA-X's rig for the prop route, exported on the rented card in the motion environment (people/body.py's own
functions, so the skeleton, its weights and the clips are exactly the shipped route's):

    /root/envs/motion/bin/python prop_skeleton.py <out.npz> [<clip> ...]

On this route SOMA-X gives only the skeleton and its skin weights (owner, 2026-10-10): the mesh is Pixal3D's. The file
holds the mean body's kept 27 joints (`names`, `parents`, `bind` world 4x4s in metres), its surface with its weights
on those joints (`points`, `faces`, `weights`: the source the weights are moved from, never drawn) and each clip's
joint transforms against their parents frame by frame (`clip_<name>`, with the clip names in `clips`). Bone lengths
do not enter a joint's rotation against its parent, so the clips play on any bone lengths the skeleton is fitted to
(prop_rig.py).

A clip is Kimodo's own movement carried onto the bind (`carried`): each joint's world turn off Kimodo's own rest
skeleton (its skin_standard bind, the frames its turns are against), laid on the bind's frame, with the bind's own
offsets and the Hips where Kimodo's root went. Until 2026-11-04 the clips were posed through SOMA's zero-identity layer
(the deleted body.posed_by_the_model), whose joint frames are not the template bind's they are played on: every clip carried a
fixed turn off Kimodo's per joint, 4.8 degrees at the knee, which the standing clip's lift hid on straight legs but
which lifted a floor sit's feet 15 mm off the floor Kimodo had them on (its own foot contacts all on).

Kimodo grounds a clip by its feet joints alone, so a clip nobody is on their feet in (people/clips.py OFF_THEIR_FEET)
is rested on its skin (`rested`): its Hips raised so the surface, played on the bind as every build plays its clips
(../played: the standing clip's lift), touches the floor at its lowest over the clip. Kimodo's floor sit put SOMA's
own skin 23 to 27 mm under its floor at the seat (2026-11-04, the owner's remake of the clip).
"""
import pathlib
import sys

import numpy as np

PEOPLE = pathlib.Path(__file__).resolve().parents[1] / "people"
sys.path.insert(0, str(PEOPLE))
sys.path.append(str(PEOPLE.parent))  # last: tools/characters' own folders (regions/ among them) never shadow the
# people tools' modules

import clips  # noqa: E402
import played  # noqa: E402

# Kimodo's own skeleton at rest, inside its package: the frames its global_rot_mats turn from.
KIMODO_REST = "assets/skeletons/somaskel77/skin_standard.npz"


def kimodo_rest():
    """Kimodo's rest skeleton: its joint names and their world 4x4s in metres."""
    import kimodo
    rest = np.load(pathlib.Path(kimodo.__file__).resolve().parent / KIMODO_REST)
    return [str(name) for name in rest["rig_joint_names"]], np.asarray(rest["bind_rig_transform"], dtype=float)


def offsets_of(bind, parents):
    """Each joint's place in its parent at the bind."""
    return np.array([bind[joint, :3, 3] if parent < 0 else (np.linalg.inv(bind[parent]) @ bind[joint])[:3, 3]
                     for joint, parent in enumerate(parents)])


def carried(motion, rest_names, rest, names, parents, bind):
    """One Kimodo clip on the bind, joint transforms against their parents frame by frame: each joint's world turn off
    Kimodo's rest laid on the bind's frame, the bind's offsets, the Hips (`played.TRAVELLING_JOINT`) where Kimodo's
    root went. A root of the rig Kimodo lacks (its Root) keeps its bind; any other joint Kimodo lacks is refused."""
    turns = np.asarray(motion["global_rot_mats"], dtype=float)
    frames = len(turns)
    world = np.tile(np.eye(4), (frames, len(names), 1, 1))
    for joint, name in enumerate(names):
        if name in rest_names:
            own = rest_names.index(name)
            world[:, joint, :3, :3] = turns[:, own] @ rest[own, :3, :3].T @ bind[joint, :3, :3]
        elif parents[joint] < 0:
            world[:, joint] = bind[joint]
        else:
            raise ValueError(f"{name} is no joint of Kimodo's skeleton")
    offsets = offsets_of(bind, parents)
    local = np.tile(np.eye(4), (frames, len(names), 1, 1))
    for joint, parent in enumerate(parents):
        if parent < 0:
            local[:, joint] = world[:, joint]
            continue
        local[:, joint, :3, :3] = np.swapaxes(world[:, parent, :3, :3], 1, 2) @ world[:, joint, :3, :3]
        local[:, joint, :3, 3] = offsets[joint]
    hips = played.TRAVELLING_JOINT
    above = world[:, parents[hips]]
    root = np.asarray(motion["root_positions"], dtype=float)
    local[:, hips, :3, 3] = np.einsum("fba,fb->fa", above[:, :3, :3], root - above[:, :3, 3])
    return local


def lowest_skin(arrays, name):
    """The surface's lowest height over the floor, frame by frame, the clip played on the bind as a build plays it (the
    standing clip's lift)."""
    names = [str(joint) for joint in arrays["names"]]
    bind = np.asarray(arrays["bind"], dtype=float)
    bones = {"offsets": offsets_of(bind, arrays["parents"]), "parents": arrays["parents"], "bind": bind}
    lift = played.floor_lift(arrays, bones, names, 1.0)
    world = played.clip_world(arrays, name, bones["offsets"], arrays["parents"], 1.0, lift)
    moves = np.einsum("fjb,jbc->fjc", world[:, :, 1, :], np.linalg.inv(bind))
    points = np.concatenate([arrays["points"], np.ones((len(arrays["points"]), 1))], axis=1)
    return np.einsum("fjb,pb,pj->fp", moves, points, np.asarray(arrays["weights"], dtype=float)).min(axis=1)


def rested(arrays, name):
    """How far an off-their-feet clip's Hips are raised so its surface touches the floor at its lowest over the clip."""
    if "clip_standing" not in arrays:
        raise ValueError(f"{name} is rested against the standing clip's lift: make standing with it")
    return -float(lowest_skin(arrays, name).min())


def rest_off_their_feet(arrays, made):
    """Every made clip nobody is on their feet in (clips.OFF_THEIR_FEET) rested on its skin, in place: {clip: metres
    raised}."""
    raised = {}
    for name in [name for name in made if name in clips.OFF_THEIR_FEET]:
        raised[name] = rested(arrays, name)
        arrays[f"clip_{name}"][:, played.TRAVELLING_JOINT, 1, 3] += raised[name]
    return raised


def export(out, wanted):
    """Write the rig file; the clips written."""
    sys.argv = sys.argv[:1]
    import body
    from paths import MOTIONS
    layer = body.build_layer("low")
    names = list(layer.public_joint_names)
    parents_all = layer.output_joint_parent_ids.detach().numpy().astype(int)
    kept, parents, carries = body.joints_worth_keeping(names, parents_all)
    world, _ = body.bind_pose(layer)
    points, faces, weights = body.the_body_at(layer, carries, len(kept))
    kept_names = [str(names[old]) for old in kept]
    arrays = {"names": np.array(kept_names), "parents": np.array(parents),
              "bind": world[kept], "points": points, "faces": faces, "weights": weights}
    rest_names, rest = kimodo_rest()
    made = []
    for name in wanted or [name for name in clips.SENTENCES if (MOTIONS / f"{name}.npz").exists()]:
        arrays[f"clip_{name}"] = carried(np.load(MOTIONS / f"{name}.npz"), rest_names, rest, kept_names,
                                         np.array(parents), world[kept])
        made.append(name)
    for name, raised in rest_off_their_feet(arrays, made).items():
        print(f"{name} rested on its skin: raised {raised * 1000:+.1f} mm", flush=True)
    arrays["clips"] = np.array(made)
    np.savez_compressed(out, **arrays)
    return made


def main():
    made = export(pathlib.Path(sys.argv[1]), sys.argv[2:])
    print(f"rig with {len(made)} clips: {', '.join(made)}", flush=True)


if __name__ == "__main__":
    main()
