"""Runs on the rented card in GEM-X's own environment (NVlabs/GEM-X, Apache-2.0, its unified release of 2026-10-21 and
after; weights under the NVIDIA Open Model License; SOMA-X 0.3.3, Apache-2.0): one `gem-infer motion-video` result
(`motion.pt`) turned into the SOMA body tools/labval reads, through GEM-X's own SOMA adapter exactly as its world
renderer evaluates it (gem.motion.geometry.MotionGeometry's settings: the fixed-GS1 adapter, procedural transforms,
bind-pose reposing, identity and scale prepared once for the clip), at the clips rig's mesh (LOD low, the
topology SCORE's landmark set is on).

    python tools/labval/on_gemx.py <motion.pt> <soma.npz> --soma-assets <assets/soma> [--start S] [--variant raw]
        [--device cuda]

Written: names and parents (SOMA's 78 public joints, its virtual Root first), bind (78 x 4 x 4, m: the person's bind,
its identity's), points, faces and weights (the person's rest mesh at that bind and its skin weights folded onto the
public joints), world (frames x 78 x 4 x 4, m, GEM-X's world frame, y up: every frame's joint transforms), fps (30:
GEM-X Motion's timeline), start (--start, the clip's start in the source video, s), variant ("raw": the network's own
prediction; "active": the result's main fields, Contact/IK corrected when it was run with --postprocess), and the
SOMA-X version. Nothing is smoothed, rescaled or fitted here."""
import argparse
import importlib.metadata

import numpy as np
import torch

FPS = 30.0  # GEM-X Motion normalises every clip to 30 Hz (docs/DEMO.md, motion-video)
FIELD = "pred_soma_params_global"
PARAMETERS = ("global_orient", "body_pose", "transl", "identity_coeffs", "scale_params")


def located(result, key):
    """Every mapping inside `result` (nested dicts and lists) holding `key`."""
    found = []
    if isinstance(result, dict):
        if key in result:
            found.append(result)
        for value in result.values():
            found.extend(located(value, key))
    elif isinstance(result, (list, tuple)):
        for value in result:
            found.extend(located(value, key))
    return found


def parameters(result, variant):
    """The result's world SOMA parameters, batched (1, frames, ...): the active fields, or the raw prediction's
    (`raw_predictions`, present when the result was postprocessed; else the active ones are the raw)."""
    source = result
    if variant == "raw" and located(result, "raw_predictions"):
        holders = located(result, "raw_predictions")
        if len(holders) != 1:
            raise ValueError(f"{len(holders)} raw_predictions in the result")
        source = holders[0]["raw_predictions"]
    holders = located(source, FIELD)
    if len(holders) != 1:
        raise ValueError(f"{len(holders)} {FIELD} fields in the result, not one")
    fields = holders[0][FIELD]
    batched = torch.as_tensor(fields["global_orient"]).ndim == 3  # (batch, frames, 3), else (frames, 3)
    return {name: torch.as_tensor(fields[name]).float() if batched else torch.as_tensor(fields[name]).float()[None]
            for name in PARAMETERS}


def body(given, assets, device):
    """(GEM-X's SOMA adapter after the clip, its output transforms frames x 78 x 4 x 4)."""
    from gem.common.soma import SomaFixedGs1BodyAdapter, SomaRuntimeConfig
    adapter = SomaFixedGs1BodyAdapter(SomaRuntimeConfig(data_root=assets, device=device, lod="low",
                                                        apply_correctives=True, enable_procedural_transforms=True,
                                                        procedural_reference="runtime"))
    adapter.to(device=device, dtype=torch.float32)
    with torch.inference_mode(), torch.autocast(device.split(":")[0], enabled=False):
        output = adapter(**{name: value.to(device) for name, value in given.items()}, pose2rot=True,
                         apply_correctives=True, return_joints_only=True, repose_to_bind_pose=True)
    return adapter, output["transforms"].reshape(-1, *output["transforms"].shape[-3:]).double().cpu().numpy()


def first(tensor):
    """A cached tensor's first item when it carries a batch."""
    return tensor[0] if tensor.ndim >= 3 else tensor


def rig_of(adapter):
    """The person's public rig after the clip: names, parents, bind, rest points, faces, weights."""
    runtime = adapter.runtime
    view = runtime.public_rig_view()
    bind = view.bind_transforms_world
    bind = bind.reshape(-1, *bind.shape[-3:])[0]
    return {"names": np.array(view.joint_names), "parents": view.joint_parent_ids.cpu().numpy().astype(int),
            "bind": bind.double().cpu().numpy(),
            "points": first(runtime._cached_rest_shape).double().cpu().numpy(),
            "faces": runtime.faces.cpu().numpy().astype(int),
            "weights": view.skinning_weights.double().cpu().numpy()}


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("motion")
    parser.add_argument("out")
    parser.add_argument("--soma-assets", required=True)
    parser.add_argument("--start", type=float, default=0.0, help="the clip's start in the source video (s)")
    parser.add_argument("--variant", choices=("raw", "active"), default="raw")
    parser.add_argument("--device", default="cuda")
    options = parser.parse_args()
    result = torch.load(options.motion, map_location="cpu", weights_only=False)
    adapter, world = body(parameters(result, options.variant), options.soma_assets, options.device)
    rig = rig_of(adapter)
    if world.shape[1] != len(rig["names"]):
        raise ValueError(f"{world.shape[1]} transforms a frame for {len(rig['names'])} public joints")
    np.savez_compressed(options.out, **rig, world=world, fps=FPS, start=options.start, variant=options.variant,
                        soma=importlib.metadata.version("py-soma-x"))
    print(f"{options.out}: {len(world)} frames, {len(rig['names'])} joints, {len(rig['points'])} points")


if __name__ == "__main__":
    main()
