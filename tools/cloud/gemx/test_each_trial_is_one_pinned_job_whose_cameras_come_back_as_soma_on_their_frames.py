"""GEM-X on LabValidation (cloud.py, on_machine.py, gemx_env.sh): each asked trial is one blender_cloud job of kind
gemx in GEM-X's env, its videos carried up and its folder brought back, a done camera never asked again and the
checkerboard trials left out; on the machine a prediction comes out as the SOMA shape, world transforms and root
translation on GEM-X's 30 Hz frames with each one's frame in the video; every piece the env script fetches is pinned
by sha256. Nothing is rented and no model runs: blender_cloud.py is never called, and the SOMA pose is a stand-in.

Breaks, each applied once and seen red (2026-11-06):
- `trials`' LEFT_OUT check dropped -> the extrinsics checkerboard trial becomes a job with no person in it.
- `still_to_make`'s done.json test dropped -> a camera made already is bought again.
- `job`'s `env=ENV` dropped -> on_machine.py runs in Blender's Python, which has no GEM-X.
- `frames`' `* source_fps` made `* FPS` -> every 30 Hz frame names the 60 fps video's frame half as far in.
- `shape`'s mean over frames dropped -> identity_coeffs is (T, 128), not the clip's one person.
- a weight's sha256 in gemx_env.sh cut short -> the pin check names it.
- cluster.py's `ik` check dropped -> the static trial, with no lab IK to score against, is bought.
- cluster.py's `or standing` dropped -> --static asks no static trial: no subject's neutral pose is made (2026-11-08).
- cluster.py's soma.npz test dropped -> a video made already is bought again on the cluster.
- cluster.py's `made_from` test dropped -> a folder holding another video's result is kept as this video's.
- cluster.py's video input made a local path -> every video goes through this PC's upload.
- `trials`' store-copy glob dropped -> the machine path (the cluster's fallback) finds no fetched video.

Breaks, each applied once and seen red (2026-11-07, GEM-X at MoGe-2's field of view, #98):
- cluster.fov_of's `np.median` made `[0]` -> the job runs at the first frame's 43 degrees, not the median.
- on_machine.pinhole's `width / 2.0 / np.tan(...)` made `np.hypot(width, height)` (GEM-X's own diagonal) -> 1469.
"""
import json
import pathlib
import re
import subprocess
import sys
import types

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cloud  # noqa: E402
import cluster  # noqa: E402
import on_machine  # noqa: E402


def lab(root):
    """A LabValidation tree as SimTK's release unpacks: two subjects, two sessions, two cameras."""
    for subject, session, trial in (("subject2", "Session1", "walking1"), ("subject2", "Session0", "squats1"),
                                    ("subject2", "Session0", "extrinsics"), ("subject3", "Session1", "walking2")):
        for camera in ("Cam1", "Cam2"):
            folder = root / subject / "VideoData" / session / camera / trial
            folder.mkdir(parents=True)
            (folder / f"{trial}.avi").write_bytes(b"video")
        (root / subject / "VideoData" / session / "Cam1" / "cameraIntrinsicsExtrinsics.pickle").write_bytes(b"")


def prediction(length):
    """GEM-X's result fields the extraction reads, for one sequence of `length` frames of a 60 fps video."""
    world = {"global_orient": np.zeros((1, length, 3)), "body_pose": np.zeros((1, length, 76 * 3)),
             "transl": np.arange(length * 3, dtype=float).reshape(1, length, 3),
             "identity_coeffs": np.array([1.0, 3.0, 1.0, 3.0, 2.0])[None, :length, None].repeat(128, 2),
             "scale_params": np.ones((1, 57))}
    return {"pred_soma_params_global": world, "pred_soma_params_incam": dict(world),
            "static_conf_logits": np.zeros((1, length, 6)),
            "conditions": {"frame_times": (np.arange(length) / 30.0)[None], "K_fullimg": np.tile(np.eye(3), (1, length, 1, 1))},
            "camera": {"R_w2c": np.tile(np.eye(3), (length, 1, 1))},
            "video": {"source": {"fps": 60.0, "frame_count": 2 * length - 1, "requested_start": 0.0,
                                 "width": 720, "height": 1280}}}


def posed(params):
    length = params["transl"].shape[1]
    transforms = np.tile(np.eye(4), (length, 78, 1, 1))
    return transforms, np.zeros((length, 77, 3)), {"joint_names": np.array([f"j{n}" for n in range(78)]),
                                                     "parents": np.arange(78) - 1, "bind_world": transforms[0]}


def test_each_trial_is_one_pinned_job_whose_cameras_come_back_as_soma_on_their_frames(tmp_path):
    root, out = tmp_path / "LabValidation", tmp_path / "gemx"
    lab(root)
    found = cloud.trials(root, ["Cam1"])
    assert sorted(found) == [("subject2", "squats1"), ("subject2", "walking1"), ("subject3", "walking2")]
    assert sorted(cloud.trials(root, ["Cam1"], ["subject2"], ["walking*"])) == [("subject2", "walking1")]
    assert set(cloud.trials(root, ["Cam1", "Cam2"])[("subject3", "walking2")]) == {"Cam1", "Cam2"}

    copy = tmp_path / "copy" / "subject4" / "Cam2"
    copy.mkdir(parents=True)
    (copy / "STS1.mp4").write_bytes(b"video")
    assert cloud.trials(tmp_path / "copy", ["Cam2"]) == {("subject4", "STS1"): {"Cam2": copy / "STS1.mp4"}}

    (out / "subject2" / "squats1" / "Cam1").mkdir(parents=True)
    (out / "subject2" / "squats1" / "Cam1" / "done.json").write_text("{}")
    left = cloud.still_to_make(found, out)
    assert sorted(left) == [("subject2", "walking1"), ("subject3", "walking2")]

    paths = cloud.written(left, out)
    job = json.loads(paths[0].read_text())
    video = root / "subject2/VideoData/Session1/Cam1/walking1/walking1.avi"
    assert job == {"script": "tools/cloud/gemx/on_machine.py",
                   "args": [str(out / "subject2/walking1"), f"--video=Cam1={video}"],
                   "inputs": [str(video)], "outputs": [str(out / "subject2/walking1")],
                   "minutes": cloud.JOB_MINUTES + cloud.VIDEO_MINUTES, "env": "tools/cloud/gemx/gemx_env.sh"}
    options = types.SimpleNamespace(who="test", classes="gpu-24gb", dry_run=True, detach=False)
    line = cloud.command(paths, options)
    assert line[2:4] == [str(path) for path in paths] and line[-3:] == ["--kind", "gemx", "--dry-run"]

    manifest = {"subjects_detail": [{"subject": "subject2", "trials": [
        {"trial": "walking1", "files": {"Cam1": "subject2/Cam1/walking1.mp4", "Cam2": "subject2/Cam2/walking1.mp4",
                                        "ik": "subject2/ik/walking1.mot"}},
        {"trial": "static1", "files": {"Cam1": "subject2/Cam1/static1.mp4"}}]}]}
    asked = cluster.videos(manifest, [], ["*"], ["Cam1", "Cam2"])
    assert asked == [("subject2", "walking1", "Cam1", "labvalidation/subject2/Cam1/walking1.mp4"),
                     ("subject2", "walking1", "Cam2", "labvalidation/subject2/Cam2/walking1.mp4")]
    assert cluster.videos(manifest, [], ["static*"], ["Cam1"], static=True) == [
        ("subject2", "static1", "Cam1", "labvalidation/subject2/Cam1/static1.mp4")]  # asked only with --static
    (out / "subject2" / "walking1" / "Cam2").mkdir(parents=True)
    (out / "subject2" / "walking1" / "Cam2" / "soma.npz").write_bytes(b"")
    assert cluster.still_to_make(asked, out) == asked[:1]
    (out / "subject2" / "walking1" / "Cam2" / "done.json").write_text(
        json.dumps({"video": "/work/labvalidation/subject4/Cam0/DJ2.mp4"}))
    assert cluster.still_to_make(asked, out) == asked  # another video's result is made again
    pod = cluster.job(out, *asked[0])
    assert pod["inputs"] == [{"key": asked[0][3], "path": "/work/labvalidation/subject2/Cam1/walking1.mp4"}]
    assert pod["outputs"] == [str(out / "subject2/walking1/Cam1")] and "on_gemx.py" in pod["command"][-1]
    assert "--fov-x" not in pod["command"][-1]  # GEM-X's own camera unless MoGe-2's is given
    moge = tmp_path / "moge" / "subject2_walking1_Cam1"
    moge.mkdir(parents=True)
    np.savez(moge / "moge.npz", fov_x=np.array([43.0, 44.0, 45.0]))
    pod = cluster.job(out, *asked[0], moge=tmp_path / "moge")
    assert "--fov-x=Cam1=44.000000" in pod["command"][-1]  # its frames' median
    fake = types.ModuleType("imageio_ffmpeg")
    fake.read_frames = lambda path: iter([{"size": (720, 1280)}])
    sys.modules["imageio_ffmpeg"] = fake
    focal = on_machine.pinhole("/a/b.mp4", 2 * np.degrees(np.arctan(0.5)))  # tan(fov / 2) = 1/2: focal = width
    assert np.allclose(focal, [[720.0, 0.0, 360.0], [0.0, 720.0, 640.0], [0.0, 0.0, 1.0]])
    del sys.modules["imageio_ffmpeg"]

    made = on_machine.extracted(prediction(5), posed)
    assert made["identity_coeffs"].shape == (128,) and np.allclose(made["identity_coeffs"], 2.0)
    assert made["world_transforms"].shape == (5, 78, 4, 4) and made["global_rotations"].shape == (5, 78, 3, 3)
    assert made["root_translation"].shape == (5, 3) and made["body_pose"].shape == (5, 76, 3)
    assert list(made["source_frame"]) == [0, 2, 4, 6, 8] and float(made["fps"]) == 30.0
    assert made["K"].shape == (5, 3, 3) and made["R_w2c"].shape == (5, 3, 3)
    assert on_machine.videos(["Cam1=/a/b.avi"]) == {"Cam1": pathlib.Path("/a/b.avi")}

    trial = tmp_path / "trial"
    (trial / "Cam1").mkdir(parents=True)
    (trial / "Cam1" / "done.json").write_text("{}")
    ran = subprocess.run([sys.executable, str(HERE / "on_machine.py"), str(trial), "--video=Cam1=/none.avi"],
                         capture_output=True, text=True)
    assert ran.returncode == 0 and "done already" in ran.stdout  # a done camera never loads the model

    script = (HERE / "gemx_env.sh").read_text()
    pinned = re.findall(r"^(\S+\.(?:ckpt|pth|npz|yaml|usda|json)) (\S+)$", script, re.M)
    assert len(pinned) == 8 and all(re.fullmatch(r"[0-9a-f]{64}", sha) for _, sha in pinned), pinned
    assert all(re.fullmatch(r"[0-9a-f]{64}", sha) for sha in re.findall(r"_SHA256=(\S+)", script))
    requirements = (HERE / "requirements.txt").read_text()
    named = re.findall(r"^(\S+?)(?:==| @ )", requirements, re.M)
    assert "gem" in named and "torch" in named
    assert len(re.findall(r"^\S.* \\\n    --hash=sha256:", requirements, re.M)) == len(named)
    assert "4aef1452e5df171deff4f293c08e643eb450981e" in requirements and on_machine.PINS["gemx_commit"] in requirements
