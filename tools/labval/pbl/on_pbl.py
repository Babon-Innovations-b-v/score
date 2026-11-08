"""Runs on a cluster card, in PBL's own Python (pbl_env.sh): the Portable Biomechanics Laboratory's released monocular
pipeline (MonocularBiomechanics, Peiffer, Cotton et al., arXiv:2507.08268) on each LabValidation video, as its demo
runs it (main.py's process_videos_with_metrabs, then process_videos_with_biomechanics), with the video's camera given:

1. MeTRAbs (its load_metrabs model, the bml_movi_87 skeleton, detect_poses_batched's defaults) on every frame, given
   the camera's intrinsic matrix (the demo gives none: MeTRAbs then takes a 55 degree field of view);
2. PBL's biomechanical fit (get_model on humanoid_torque.xml with its joint_names, fit_model at main.py's settings:
   lr_init_value 1e-3, max_iters 10000, the rest its defaults) of a static camera (no phone attitude, so its world is
   the camera's frame), its camera_params the same intrinsics;
3. the fitted trajectory read at every frame (main.py's call), and the pelvis body's turn in the camera's frame from
   MuJoCo's kinematics of the same model at each frame's qpos (body scale moves no turn).

    python tools/labval/pbl/on_pbl.py <env folder> --video=<out folder>=<video.mp4>=<fx>=<fy>=<cx>=<cy> ...

Two choices the demo leaves open, made here: each frame's person is MeTRAbs' largest detection (the demo takes the
first; LabValidation's subject is the nearest person), and a frame with no detection has confidence 0 (the demo's
fit gives every frame confidence 1). Written per video: <out folder>/pbl.npz (times s, qpos frames x nq, joint
names, pelvis turn frames x 3 x 3 in OpenCV camera axes, the body scale, the keypoints, confidences and boxes, K, the
fit's last metrics) and pbl.done.json, last."""
import argparse
import json
import os
import pathlib
import sys
import time
import traceback

import numpy as np

SKELETON = "bml_movi_87"
JOINTS = 87
MAX_ITERS = 10000  # main.py's process_videos_with_biomechanics
LR_INIT = 1e-3
BATCH = 8  # frames a MeTRAbs call: each frame is detected on its own, so the batch changes no result


def keypoints(model, video, intrinsics):
    """(keypoints3d frames x 87 x 3 mm, keypoints2d frames x 87 x 2 px, confidences frames x 87, boxes frames x 5,
    fps) of MeTRAbs on every frame of `video`, its largest detection a frame."""
    import cv2
    import tensorflow as tf

    capture = cv2.VideoCapture(video)
    fps = capture.get(cv2.CAP_PROP_FPS)
    frames = []
    while True:
        ok, frame = capture.read()
        if not ok:
            break
        frames.append(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    capture.release()
    if not frames or not fps:
        raise ValueError(f"{video}: no frames read")
    matrix = tf.constant(intrinsics[None], dtype=tf.float32)
    found3d, found2d, confidences, boxes = [], [], [], []
    for start in range(0, len(frames), BATCH):
        prediction = model.detect_poses_batched(np.stack(frames[start:start + BATCH]), intrinsic_matrix=matrix,
                                                skeleton=SKELETON)
        for index in range(len(frames[start:start + BATCH])):
            detected = prediction["boxes"][index].numpy()
            if len(detected) == 0:
                found3d.append(np.zeros((JOINTS, 3)))
                found2d.append(np.zeros((JOINTS, 2)))
                confidences.append(np.zeros(JOINTS))
                boxes.append(np.zeros(5))
                continue
            largest = int(np.argmax(detected[:, 2] * detected[:, 3]))
            found3d.append(prediction["poses3d"][index][largest].numpy())
            found2d.append(prediction["poses2d"][index][largest].numpy())
            confidences.append(np.ones(JOINTS))
            boxes.append(detected[largest])
    return np.array(found3d), np.array(found2d), np.array(confidences), np.array(boxes), float(fps)


def fitted(source, kp3d, kp2d, confidences, fps, intrinsics):
    """(times, qpos frames x nq, body scale, the fit's last metrics) of PBL's fit of one static-camera video."""
    import equinox as eqx
    import jax
    import jax.numpy as jnp
    from monocular_demos.biomechanics_mjx.monocular_trajectory import fit_model, get_model
    from monocular_demos.dataset import MonocularDataset
    from monocular_demos.utils import joint_names

    # main.py's own first step of each fit: a cached step of the previous video's model refuses this one (its static
    # fields hold arrays; 2026-11-08: 28 of a lane's later videos failed on "metadata fields of pytree").
    jax.clear_caches()
    eqx.clear_caches()
    times = np.arange(len(kp3d)) / fps
    mtx = np.array([[intrinsics[0, 0], intrinsics[1, 1], intrinsics[0, 2], intrinsics[1, 2]]]) / 1000.0
    camera = dict(mtx=mtx, dist=np.zeros((1, 5)), rvec=np.zeros((1, 3)), tvec=np.zeros((1, 3)))
    dataset = MonocularDataset(timestamps=[times], keypoints_2d=[kp2d[np.newaxis]], keypoints_3d=[kp3d[np.newaxis]],
                               keypoint_confidence=[jnp.asarray(confidences)[np.newaxis]], camera_params=camera,
                               phone_attitude=None)
    model = get_model(dataset, xml_path=str(xml_of(source)), joint_names=joint_names)
    model, metrics = fit_model(model, dataset, lr_init_value=LR_INIT, max_iters=MAX_ITERS)
    stamps = dataset.get_all_timestamps(0)
    _, (qpos, _, _), _ = model(stamps, trajectory_selection=0, steps=0, skip_action=True, fast_inference=True,
                               check_constraints=False)
    last = {key: float(np.mean(np.asarray(value))) for key, value in metrics.items()}
    return np.asarray(stamps), np.asarray(qpos), np.asarray(model.body_scale), last


def xml_of(source):
    return pathlib.Path(source) / "monocular_demos/biomechanics_mjx/data/humanoid/humanoid_torque.xml"


def pelvis_turns(source, qpos):
    """(the model's joint names in qpos order, the pelvis body's turn in the world, the camera's frame, frames x 3 x
    3) by MuJoCo's kinematics of humanoid_torque.xml at each frame's qpos."""
    import mujoco

    model = mujoco.MjModel.from_xml_path(str(xml_of(source)))
    if qpos.shape[1] != model.nq:
        raise ValueError(f"the fit's qpos has {qpos.shape[1]} columns, the model {model.nq}")
    names = [""] * model.nq
    for joint in range(model.njnt):
        names[model.jnt_qposadr[joint]] = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, joint)
    data = mujoco.MjData(model)
    pelvis = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "pelvis")
    turns = []
    for row in qpos:
        data.qpos[:] = row
        mujoco.mj_kinematics(model, data)
        turns.append(data.xmat[pelvis].reshape(3, 3).copy())
    return names, np.array(turns)


def one(metrabs, source, out, video, intrinsics):
    """One video through MeTRAbs and PBL's fit; its npz, then its done file."""
    began = time.time()
    kp3d, kp2d, confidences, boxes, fps = keypoints(metrabs, video, intrinsics)
    detected = time.time()
    times, qpos, scale, metrics = fitted(source, kp3d, kp2d, confidences, fps, intrinsics)
    names, turns = pelvis_turns(source, qpos)
    out.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out / "pbl.npz", times=times, qpos=qpos, joint_names=np.array(names), pelvis_turns=turns,
                        body_scale=scale, keypoints3d=kp3d, keypoints2d=kp2d, confidences=confidences, boxes=boxes,
                        K=intrinsics, fps=fps)
    (out / "pbl.done.json").write_text(json.dumps({
        "video": video, "frames": int(len(kp3d)), "frames without a person": int((confidences[:, 0] == 0).sum()),
        "fps": fps, "metrabs seconds": round(detected - began, 1), "fit seconds": round(time.time() - detected, 1),
        "metrics": metrics}, indent=1))


def with_cuda():
    """This process again with the lock's CUDA libraries (site-packages/nvidia/*/lib) on LD_LIBRARY_PATH, unless they
    are on it: TensorFlow 2.21 finds most of them by its own path but not libcusolver.so.11, and without it registers
    no card at all (2026-11-08: MeTRAbs ran on the processor)."""
    import site

    folders = sorted(str(path) for root in site.getsitepackages() for path in pathlib.Path(root).glob("nvidia/*/lib"))
    present = os.environ.get("LD_LIBRARY_PATH", "").split(":")
    if folders and not set(folders) <= set(present):
        os.environ["LD_LIBRARY_PATH"] = ":".join([*folders, *[entry for entry in present if entry]])
        os.execv(sys.executable, [sys.executable, *sys.argv])


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("env", type=pathlib.Path, help="pbl_env.sh's folder")
    parser.add_argument("--video", action="append", required=True,
                        help="<out folder>=<video.mp4>=<fx>=<fy>=<cx>=<cy> (px)")
    options = parser.parse_args()
    with_cuda()
    source = options.env / "src"
    sys.path.insert(0, str(source))
    os.environ["MUJOCO_GL"] = "disable"  # nothing is drawn; the base image has no EGL (MuJoCo's gl_context)
    from monocular_demos.utils import jax_memory_limit, tensorflow_memory_limit

    tensorflow_memory_limit()
    jax_memory_limit()
    import jax
    import tensorflow as tf
    import tensorflow_hub

    if not tf.config.list_physical_devices("GPU") or jax.default_backend() != "gpu":
        raise SystemExit(f"no card: TensorFlow sees {tf.config.list_physical_devices()}, JAX {jax.devices()}")

    jax.config.update("jax_compilation_cache_dir", str(options.env.parent / "pbl-jax-cache"))
    jax.config.update("jax_persistent_cache_min_entry_size_bytes", -1)
    jax.config.update("jax_persistent_cache_min_compile_time_secs", 0)
    jax.config.update("jax_enable_x64", True)  # main.py's
    metrabs = tensorflow_hub.load(str(options.env / "metrabs"))
    failed = 0
    for given in options.video:
        out, video, *numbers = given.split("=")
        out = pathlib.Path(out)
        if (out / "pbl.done.json").exists():
            continue
        fx, fy, cx, cy = (float(number) for number in numbers)
        try:
            one(metrabs, source, out, video, np.array([[fx, 0.0, cx], [0.0, fy, cy], [0.0, 0.0, 1.0]]))
            print(f"{out}: done", flush=True)
        except Exception as error:  # one video's fault is said and the next still runs; the run ends failed
            failed += 1
            traceback.print_exc()
            print(f"{out}: failed: {error!r}", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
