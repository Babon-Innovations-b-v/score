"""One LabValidation trial through GEM-X Body Motion on the rented card (cloud.py's job; runs in the Python
gemx_env.sh builds, whose folder also holds the weights and the SOMA assets): each camera's video once, in turn.

    <env>/bin/python tools/cloud/gemx/on_machine.py <trial folder> --video Cam1=<video> [--video Cam2=<video> ...] \
        [--fov-x Cam1=<deg> ...]

For each camera, into <trial folder>/<camera>/:
- motion.pt: GEM-X's whole prediction as upstream saves it (raw: no Contact/IK), so anything later is read from it
  again without running the model.
- raw.npz and contact_ik.npz: the raw prediction, and the same after upstream's Contact/IK postprocess, each with the
  person's SOMA shape (identity_coeffs 128, scale_params 57, the bind skeleton bind_world (78, 4, 4), joint_names,
  parents), per frame the world transform of each of SOMA's 78 public joints (world_transforms, the global rotations
  global_rotations its 3 x 3 blocks, joints the 77 joint positions), the Hips' translation in the world
  (root_translation) and the parameters themselves (global_orient, body_pose: axis-angle), the camera (K, R_w2c,
  the body in the camera: incam_global_orient, incam_transl), the frames (frame_index on GEM-X's 30 Hz timeline,
  frame_times in seconds from the video's start, fps 30, source_fps, source_frame: the video's own frame nearest each
  one) and the contact logits. World: Y up, metres (upstream's convention); camera: OpenCV, metres.
- done.json, written last: the seconds, the card's peak memory, the frames, the pins. A camera with it is skipped.

The camera is fixed (`camera.mode static`): LabValidation's cameras stand on tripods. A camera given `--fov-x` (its
horizontal field of view in degrees, as MoGe-2 estimates it from the video: tools/labval/moge_cluster.py) runs at
that pinhole, its principal point the image's middle (`camera.intrinsics`, upstream's override); without it GEM-X
takes its own estimate, the image diagonal as focal length (27.5 degrees across a 720 x 1280 video, where
LabValidation's calibration gives 43.0, #98). done.json records which. The forward kinematics are
upstream's own SOMA adapter (gem.common.soma), SOMA-X 0.3.3 at the mid level of detail without correctives (they move
the skin only), the identity averaged over the clip as SOMA's two-phase pose does.
"""
import argparse
import json
import os
import pathlib
import sys
import time

import numpy as np

ENV = pathlib.Path(sys.prefix)
WEIGHTS = ENV / "weights"
SOMA_ASSETS = ENV / "soma"
CONFIG = WEIGHTS / "body_video_native77.yaml"
# The pins gemx_env.sh installs, recorded in each done.json.
PINS = {"gemx_commit": "4aef1452e5df171deff4f293c08e643eb450981e",
        "gemx_weights_revision": "b111f2dcf3ebcf57965fd53499cb645dfa5ba25c",
        "soma_assets_revision": "3648707b69e1b1dcf14c473e30613266b786b9f1", "release": "native77 final775"}
FPS = 30.0


def array(value):
    """A tensor or array as a float or int numpy array on the processor."""
    if hasattr(value, "detach"):
        value = value.detach().cpu().numpy()
    return np.asarray(value)


def first(value):
    """The one sequence of a batch of one: its leading axis dropped."""
    found = array(value)
    if found.shape[0] != 1:
        raise ValueError(f"one sequence a result, got a batch of {found.shape[0]}")
    return found[0]


def frames(result):
    """The timeline: GEM-X's 30 Hz frame numbers, their seconds from the video's start and the video's own frame
    nearest each."""
    source = result["video"]["source"]
    times = first(result["conditions"]["frame_times"]).astype(np.float64) + float(source["requested_start"])
    source_fps = float(source["fps"])
    nearest = np.minimum(np.rint(times * source_fps).astype(np.int64), int(source["frame_count"]) - 1)
    return {"frame_index": np.arange(len(times)), "frame_times": times, "fps": np.float64(FPS),
            "source_fps": np.float64(source_fps), "source_frame": nearest,
            "source_frame_count": np.int64(source["frame_count"]),
            "image_size": np.array([source["width"], source["height"]])}


def shape(params):
    """The person's SOMA shape for the clip: identity and packed scales, averaged over its frames where per frame."""
    found = {}
    for name in ("identity_coeffs", "scale_params"):
        value = first(params[name])
        found[name] = value.mean(axis=0) if value.ndim == 2 else value
    return found


def extracted(result, posed):
    """A prediction's fields for the sim body: `posed(params)` gives the world transforms (T, 78, 4, 4), the joints
    (T, 77, 3) and the rig (joint_names, parents, bind_world) of its world parameters."""
    world, camera = result["pred_soma_params_global"], result["pred_soma_params_incam"]
    transforms, joints, rig = posed(world)
    length = len(transforms)
    body_pose = first(world["body_pose"]).reshape(length, -1, 3)
    return {**rig, **shape(world), **frames(result),
            "world_transforms": transforms, "global_rotations": transforms[:, :, :3, :3], "joints": joints,
            "root_translation": first(world["transl"]), "global_orient": first(world["global_orient"]),
            "body_pose": body_pose,
            "K": first(result["conditions"]["K_fullimg"]), "R_w2c": array(result["camera"]["R_w2c"]).reshape(-1, 3, 3),
            "incam_global_orient": first(camera["global_orient"]), "incam_transl": first(camera["transl"]),
            "static_conf_logits": first(result["static_conf_logits"])}


def soma_posed(device):
    """Upstream's SOMA adapter as a `posed` function: a world parameter set -> transforms, joints, rig."""
    import torch
    from gem.common.soma import SomaFixedGs1BodyAdapter, SomaRuntimeConfig

    adapter = SomaFixedGs1BodyAdapter(SomaRuntimeConfig(data_root=str(SOMA_ASSETS), device=device, lod="mid",
                                                        apply_correctives=False))

    def posed(params):
        values = {name: torch.as_tensor(params[name]).to(device=device, dtype=torch.float32)
                  for name in ("global_orient", "body_pose", "identity_coeffs", "scale_params", "transl")}
        with torch.inference_mode(), torch.autocast(torch.device(device).type, enabled=False):
            output = adapter(**values, pose2rot=True, return_joints_only=True, repose_to_bind_pose=True)
            runtime = adapter.runtime
            rig = runtime.public_rig_view()
            return first(output["transforms"]), first(output["joints"]), {
                "joint_names": np.array(rig.joint_names), "parents": array(rig.joint_parent_ids),
                "bind_world": array(rig.bind_transforms_world).reshape(-1, len(rig.joint_names), 4, 4)[0]}
    return posed


def pinhole(video, fov_x):
    """The 3 x 3 pinhole of `video` at horizontal field of view `fov_x` (deg), its principal point the middle."""
    import imageio_ffmpeg

    width, height = next(imageio_ffmpeg.read_frames(str(video)))["size"]
    focal = width / 2.0 / np.tan(np.radians(fov_x) / 2.0)
    return [[focal, 0.0, width / 2.0], [0.0, focal, height / 2.0], [0.0, 0.0, 1.0]]


def one_camera(video, folder, device, fov_x=None):
    """One camera's video: the prediction, both extractions, then done.json."""
    import torch
    from gem.inference.body_video import load_body_video_config, run_body_video
    from gem.inference.postprocess import postprocess_motion_result
    from gem.inference.serialization import save_predictions

    began = time.time()
    folder.mkdir(parents=True, exist_ok=True)
    config = load_body_video_config(CONFIG)
    config.setdefault("camera", {})["mode"] = "static"
    if fov_x is not None:
        config["camera"]["intrinsics"] = pinhole(video, fov_x)
    if device.startswith("cuda"):
        torch.cuda.reset_peak_memory_stats()
    result = run_body_video(str(video), config, device=device, progress=lambda line: print(line, flush=True))
    save_predictions(result, folder / "motion.pt")
    predicted = time.time()
    posed = soma_posed(device)
    np.savez_compressed(folder / "raw.npz", **extracted(result, posed))
    processed = postprocess_motion_result(result, soma_assets=str(SOMA_ASSETS), device=device)
    np.savez_compressed(folder / "contact_ik.npz", **extracted(processed, posed))
    peak = torch.cuda.max_memory_reserved() / 1e9 if device.startswith("cuda") else None
    done = {**PINS, "video": str(video), "frames": int(first(result["pred_soma_params_global"]["transl"]).shape[0]),
            "seconds": round(time.time() - began, 1), "predict_seconds": round(predicted - began, 1),
            "card_peak_gb": peak and round(peak, 2),
            "card": torch.cuda.get_device_name() if device.startswith("cuda") else None,
            "camera": {"fov_x": fov_x, "from": "given (MoGe-2)"} if fov_x is not None else {"from": "GEM-X's own"}}
    (folder / "done.json").write_text(json.dumps(done, indent=1))
    print(f"{video}: {done['frames']} frames in {done['seconds']} s, card peak {done['card_peak_gb']} GB", flush=True)


def videos(pairs):
    """`Cam1=<path>` arguments as {camera: path}."""
    found = {}
    for pair in pairs:
        camera, _, path = pair.partition("=")
        if not camera or not path:
            raise SystemExit(f"--video takes <camera>=<path>, got {pair!r}")
        found[camera] = pathlib.Path(path)
    return found


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("trial", type=pathlib.Path)
    parser.add_argument("--video", action="append", required=True)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--fov-x", action="append", default=[], help="<camera>=<horizontal field of view, deg>")
    given = parser.parse_args()
    fovs = {camera: float(value) for camera, value in (pair.split("=") for pair in given.fov_x)}
    os.environ["PATH"] = f"{ENV / 'bin'}{os.pathsep}{os.environ.get('PATH', '')}"
    failed = []
    for camera, video in videos(given.video).items():
        folder = given.trial / camera
        if (folder / "done.json").exists():
            print(f"{camera}: done already", flush=True)
            continue
        try:
            one_camera(video, folder, given.device, fovs.get(camera))
        except Exception as error:  # one camera's failure is said and the trial's next camera still runs
            print(f"{camera}: FAILED {type(error).__name__}: {error}", flush=True)
            failed.append(camera)
    if failed:
        raise SystemExit(f"failed: {', '.join(failed)}")


if __name__ == "__main__":
    main()
