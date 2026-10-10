"""SOMA-X's rig for the prop route, exported on the rented card in the motion environment (people/body.py's own
functions, so the skeleton, its weights and the clips are exactly the shipped route's):

    /root/envs/motion/bin/python prop_skeleton.py <out.npz> [<clip> ...]

On this route SOMA-X gives only the skeleton and its skin weights (owner, 2026-10-10): the mesh is Pixal3D's. The file
holds the mean body's kept 27 joints (`names`, `parents`, `bind` world 4x4s in metres), its surface with its weights
on those joints (`points`, `faces`, `weights`: the source the weights are moved from, never drawn) and each clip's
joint transforms against their parents frame by frame (`clip_<name>`, from the mean body's own pose, with the clip
names in `clips`). Bone lengths do not enter a joint's rotation against its parent, so the clips play on any bone
lengths the skeleton is fitted to (prop_rig.py).
"""
import pathlib
import sys

import numpy as np

PEOPLE = pathlib.Path(__file__).resolve().parents[1] / "people"


def export(out, wanted):
    """Write the rig file; the clips written."""
    sys.argv = sys.argv[:1]
    sys.path.insert(0, str(PEOPLE))
    import body
    import clips
    from paths import MOTIONS
    layer = body.build_layer("low")
    names = list(layer.public_joint_names)
    parents_all = layer.output_joint_parent_ids.detach().numpy().astype(int)
    kept, parents, carries = body.joints_worth_keeping(names, parents_all)
    world, _ = body.bind_pose(layer)
    points, faces, weights = body.the_body_at(layer, carries, len(kept))
    arrays = {"names": np.array([names[old] for old in kept]), "parents": np.array(parents),
              "bind": world[kept], "points": points, "faces": faces, "weights": weights}
    made = []
    for name in wanted or [name for name in clips.SENTENCES if (MOTIONS / f"{name}.npz").exists()]:
        clip_world, _ = body.posed_by_the_model(layer, MOTIONS / f"{name}.npz")
        arrays[f"clip_{name}"] = np.stack([body.against_parent(frame, np.array(parents))
                                          for frame in clip_world[:, kept]])
        made.append(name)
    arrays["clips"] = np.array(made)
    np.savez_compressed(out, **arrays)
    return made


def main():
    made = export(pathlib.Path(sys.argv[1]), sys.argv[2:])
    print(f"rig with {len(made)} clips: {', '.join(made)}", flush=True)


if __name__ == "__main__":
    main()
