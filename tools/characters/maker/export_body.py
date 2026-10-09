"""One identity's body at its bind pose, for the drapes and the head work: `ours.npz` (points, faces, weights and the
kept joints' names), `ours_cm.obj` (GarmentCode drapes in centimetres) and `joints.json` (every joint's place at rest,
the eyes too, which the build drops).

    MOTION_LOOK=<look folder> /root/envs/motion/bin/python export_body.py <identity.npz> <out folder>

The body is the people tools' own (tools/characters/people/body.py, the SOMA-X body through the MHR identity), so the
drapes hang on exactly the body the build skins. Moved here from the nev_mars job's export_body.py (#112).
"""
import json
import pathlib
import sys

PEOPLE = pathlib.Path(__file__).resolve().parents[1] / "people"


def export(identity, out):
    """Write the three files for the identity into `out`; the body's height in metres."""
    sys.argv = sys.argv[:1]
    sys.path.insert(0, str(PEOPLE))
    import numpy as np
    import body
    out.mkdir(parents=True, exist_ok=True)
    layer = body.build_layer("low", identity=str(identity))
    names = list(layer.public_joint_names)
    parents_all = layer.output_joint_parent_ids.detach().numpy().astype(int)
    kept, _, carries = body.joints_worth_keeping(names, parents_all)
    world, _ = body.bind_pose(layer)
    points, faces, weights = body.the_body_at(layer, carries, len(kept))
    with open(out / "ours_cm.obj", "w") as handle:
        for vertex in points * 100.0:
            handle.write(f"v {vertex[0]:.6f} {vertex[1]:.6f} {vertex[2]:.6f}\n")
        for face in faces:
            handle.write(f"f {face[0] + 1} {face[1] + 1} {face[2] + 1}\n")
    np.savez(out / "ours.npz", points=points, faces=faces, weights=weights,
             joint_names=np.array([names[old] for old in kept]))
    joints = {name: world[index][:3, 3].tolist() for index, name in enumerate(names)}
    (out / "joints.json").write_text(json.dumps(joints, indent=1))
    return float(points[:, 1].max() - points[:, 1].min())


def main():
    identity, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
    height = export(identity, out)
    print(f"body of {identity.name}: {height:.3f} m tall", flush=True)


if __name__ == "__main__":
    main()
