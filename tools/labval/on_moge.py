"""Runs on a cluster card, in GEM-X's Python with MoGe-2 beside it (moge_env.sh): MoGe-2's metric point map of a few
frames of each LabValidation video, the floor's evidence for `_floor` (the floor seen, not assumed: GEM-X's world up is
its own per-frame estimate). MoGe-2 is microsoft/MoGe (MIT), weights Ruicheng/moge-2-vitl-normal (MIT).

    python tools/labval/on_moge.py <moge folder> --video=<out.npz>=<video.mp4>=<GEM-X's fov_x deg> ... [--frames 5]

Written per video: frames (the video frame numbers read), points (frames x H/4 x W/4 x 3, m, OpenCV camera axes: x
right, y down, z forward, GEM-X's camera axes too), normal and mask the same size, each frame's own horizontal field
of view as MoGe-2 estimates it (`fov_x`, deg, frames; the camera's own, which GEM-X does not know: its motion-video
takes the image diagonal as the focal length, 27.5 deg across a 720 x 1280 video, where the lab's calibration gives
43.0 and MoGe-2 44.5 on subject2's squats, Cam1), and GEM-X's (`fov_x gemx`); then done.json beside it, written
last."""
import argparse
import json
import pathlib
import sys

import numpy as np

STRIDE = 4  # the point map kept at a quarter of the frame's resolution: a floor plane needs no more


def frames_of(video, count):
    """(the frame numbers, the frames as H x W x 3 uint8) of `count` frames spread evenly over the video."""
    import imageio_ffmpeg

    total = imageio_ffmpeg.count_frames_and_secs(video)[0]
    if not total:
        raise ValueError(f"{video}: no frames")
    chosen = np.unique(np.linspace(0, total - 1, count).round().astype(int))
    reader = imageio_ffmpeg.read_frames(video)
    width, height = next(reader)["size"]
    frames = {number: np.frombuffer(raw, dtype=np.uint8).reshape(height, width, 3)
              for number, raw in enumerate(reader) if number in set(chosen.tolist())}
    missing = [int(number) for number in chosen if number not in frames]
    if missing:
        raise ValueError(f"{video}: frames {missing} of {total} not read")
    return chosen, [frames[number] for number in chosen]


def inferred(model, image, fov_x):
    """MoGe-2's output on one frame (H x W x 3 uint8) at `fov_x` (deg; None leaves it free), as numpy."""
    import torch

    tensor = torch.tensor(image / 255.0, dtype=torch.float32, device="cuda").permute(2, 0, 1)
    with torch.inference_mode():
        output = model.infer(tensor, fov_x=fov_x)
    return {key: value.float().cpu().numpy() for key, value in output.items() if value is not None}


def fov_of(intrinsics):
    """The horizontal field of view (deg) of MoGe's normalised intrinsics."""
    return float(np.degrees(2.0 * np.arctan(0.5 / intrinsics[0, 0])))


def one(model, out, video, fov_x, count):
    """One video's frames through MoGe-2, its npz and done.json."""
    numbers, images = frames_of(video, count)
    kept = {"points": [], "normal": [], "mask": []}
    fovs = []
    for image in images:
        result = inferred(model, image, None)
        fovs.append(fov_of(result["intrinsics"]))
        for key in kept:
            kept[key].append(result[key][::STRIDE, ::STRIDE])
    out.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out, frames=numbers, fov_x=np.array(fovs), **{"fov_x gemx": fov_x}, stride=STRIDE,
                        **{key: np.array(value, dtype=np.float32 if key != "mask" else bool)
                           for key, value in kept.items()})
    (out.parent / f"{out.stem}.done.json").write_text(json.dumps({"video": video, "frames": numbers.tolist()}))


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("folder", type=pathlib.Path)
    parser.add_argument("--video", action="append", required=True, help="<out.npz>=<video.mp4>=<fov_x deg>")
    parser.add_argument("--frames", type=int, default=5)
    options = parser.parse_args()
    sys.path.insert(0, str(options.folder / "pkgs"))
    from moge.model.v2 import MoGeModel

    model = MoGeModel.from_pretrained(str(options.folder / "model.pt")).cuda().eval()
    failed = 0
    for given in options.video:
        out, video, fov_x = given.split("=")
        out = pathlib.Path(out)
        if (out.parent / f"{out.stem}.done.json").exists():
            continue
        try:
            one(model, out, video, float(fov_x), options.frames)
            print(f"{out}: done", flush=True)
        except Exception as error:  # one video's fault is said and the next still runs; the run ends failed
            failed += 1
            print(f"{out}: failed: {error!r}", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
