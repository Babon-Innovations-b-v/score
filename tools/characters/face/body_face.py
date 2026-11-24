"""The SOMA body's own face (#226): a kept person's body at rest with MHR's 72 face expressions carried onto it.

    <motion python> body_face.py <identity.npz> <out.npz>

Runs in the motion environment (SOMA-X, py-soma-x at the image's SOMA_COMMIT, Apache-2.0; MHR's TorchScript model in
nvidia/soma-x, Apache-2.0). The body is built as `../people/body.py` builds a person (MHR's identity read by SAM 3D Body,
its 68 part scales and six bone lengths, SOMA-X's dense mesh); each expression is MHR asked for that one expression at
1 and the shape carried onto SOMA's topology by SOMA-X's own MHR transfer, so the body and its face are one mesh.
Writes, in metres with the soles on the floor: the rest points, the triangles, the 72 expressions' offsets (MHR's
order, `expressions.MHR_EXPRESSIONS`), the points SOMA-X fills in itself (`filled`), the head's, eyes' and jaw's joints
and the same body at the low level of detail (`low_points`, `low_triangles`).
"""
import sys

import numpy as np
import torch

import soma.assets
from soma.body import SOMALayer

EXPRESSIONS = 72  # MHR v1's face expression count, facebookresearch/MHR docs/face-expressions.md
FACE_JOINTS = ("Head", "LeftEye", "RightEye", "Jaw")


def person_layer(identity, lod="mid"):
    """SOMA-X's dense body at `lod` for the identity SAM 3D Body read (body.py build_layer's MHR branch, global scale
    1)."""
    read = np.load(identity)
    numbers = torch.from_numpy(read["mhr_model_params"]).float()[None]
    layer = SOMALayer(data_root=soma.assets.get_assets_dir(), device="cpu", identity_model_type="mhr", lod=lod,
                      mode="dense")
    arguments = {"identity_coeffs": torch.from_numpy(read["shape_params"]).float()[None],
                 "scale_params": numbers[:, -68:], "kwargs": {"bone_length_flexibles": numbers[:, 130:136]}}
    layer.prepare_identity(**arguments)
    return layer, arguments


def rest_with_expression(layer, arguments, expression):
    """The body's rest points (metres, SOMA-X's output unit; SOMA's topology) with MHR's face expressions set to `expression`."""
    model = layer.identity_model
    jit = model.identity_model

    def get_rest_shape(identity_coeffs, scale_params=None, kwargs=None):
        pose = torch.zeros(identity_coeffs.shape[0], 136)
        pose[:, 130:136] = kwargs["bone_length_flexibles"]
        shape, _ = jit(identity_coeffs, torch.cat([pose, scale_params], dim=1), expression[None])
        return shape

    model.get_rest_shape = get_rest_shape
    try:
        points = model(arguments["identity_coeffs"], arguments["scale_params"], kwargs=arguments["kwargs"],
                       global_scale=1.0)
    finally:
        del model.get_rest_shape
    if layer.identity_lod_transfer is not None:
        points = layer.identity_lod_transfer(points)
    return points[0].detach().numpy().astype(np.float64)


def face_joints(layer):
    """The face joints' rest positions (metres) by name."""
    names = list(layer._public_joint_names)
    world = layer.public_bind_transforms_world()
    world = (world[0] if world.ndim == 4 else world).detach().numpy()
    return {name: world[names.index(name), :3, 3].astype(np.float64) for name in FACE_JOINTS}


def filled(layer):
    """Which body points SOMA-X fills in itself (its eye and mouth bags, which MHR's mesh lacks): solved by a Laplacian
    from the points round them, so MHR's expressions throw them far (20 cm at jawDrop on the officer)."""
    points = np.zeros(layer.identity_model._laplacian_mesh.V.shape[0], dtype=bool)
    points[layer.identity_model._laplacian_mesh.vid_unknown.numpy()] = True
    return points


def triangles_of(layer):
    """The layer's triangles as a numpy array."""
    faces = layer.faces if hasattr(layer, "faces") else layer.mesh_faces
    return np.asarray(faces.detach().numpy() if hasattr(faces, "detach") else faces)


def low_body(identity):
    """The same body at SOMA's low level of detail at rest, its points and triangles: the clips rig's own topology
    (people-clips rig.npz `points` and `faces`, 4505 points), so the whole person (`../whole`) carries this body's skin
    by the clips rig's weights."""
    layer, arguments = person_layer(identity, lod="low")
    with torch.no_grad():
        rest = rest_with_expression(layer, arguments, torch.zeros(EXPRESSIONS))
    return rest, triangles_of(layer)


def main(identity, out):
    """Write the body, its 72 expression offsets, its face joints and its low body to `out`, in metres on the
    floor (the low body lifted with it)."""
    layer, arguments = person_layer(identity)
    with torch.no_grad():
        rest = rest_with_expression(layer, arguments, torch.zeros(EXPRESSIONS))
        offsets = np.stack([rest_with_expression(layer, arguments, torch.eye(EXPRESSIONS)[index]) - rest
                            for index in range(EXPRESSIONS)])
    lift = -rest[:, 1].min()
    joints = face_joints(layer)
    low_points, low_triangles = low_body(identity)
    np.savez_compressed(out, points=rest + [0, lift, 0], triangles=triangles_of(layer),
                        low_points=low_points + [0, lift, 0], low_triangles=low_triangles,
                        offsets=offsets.astype(np.float32), filled=filled(layer),
                        **{f"joint_{name}": joints[name] + [0, lift, 0] for name in joints})
    print(f"body face: {rest.shape[0]} points, {EXPRESSIONS} expressions, largest offset "
          f"{np.abs(offsets).max() * 1000:.1f} mm -> {out}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
