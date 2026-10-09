"""An exact orthographic front depth view of the person's built head (skin, hair, brows, eyes, collar, cloth, glasses),
the picture the face is drawn on (drawings.py face): `face/depth.png` (near bright, far dark, as Depth Anything draws
it), `face/depth.npy` and `face/view.json` (the window in metres and the size in pixels). The window is take C's,
moved with the eyes.

    /root/envs/motion/bin/python face_depth.py <work folder>

The work folder holds `gc/body/joints.json` and `parts/` (the build's work suit shapes, DUMP_PARTS in
tools/characters/people/dress.py). Moved here from the paint round's head_depth.py and the nev_mars job's
face_depth.py (#112).
"""
import json
import pathlib
import sys

import numpy as np
from PIL import Image

PARTS = ("skin_head", "hair", "eyebrows", "eyes", "irises", "glasses", "work_collar", "work_cloth")
SIZE = 1024
TAKE_C_EYE_X, TAKE_C_EYE_Y, TAKE_C_TOP, TAKE_C_MIDDLE = 0.031, 1.649, 1.757, 1.64
HALF = 0.145


def window_for(joints):
    """The view's window (left, right, bottom, top in metres), take C's moved with the eyes and the crown."""
    eye = joints["LeftEye"]
    up = (joints["HeadEnd"][1] - eye[1]) / (TAKE_C_TOP - TAKE_C_EYE_Y)
    half = HALF * max(eye[0] / TAKE_C_EYE_X, up)
    middle = eye[1] + (TAKE_C_MIDDLE - TAKE_C_EYE_Y) * up
    return (-half, half, middle - half, middle + half)


def to_pixels(points, window):
    left, right, bottom, top = window
    return np.stack([(points[:, 0] - left) / (right - left) * SIZE - 0.5,
                     (top - points[:, 1]) / (top - bottom) * SIZE - 0.5], axis=1)


def rasterise(depth, points, faces, window):
    """Each triangle's nearest depth into `depth` (larger z is nearer)."""
    pixel = to_pixels(points, window)
    for triangle in faces:
        corners = pixel[triangle]
        low = np.clip(np.floor(corners.min(0)).astype(int), 0, SIZE - 1)
        high = np.clip(np.ceil(corners.max(0)).astype(int), 0, SIZE - 1)
        if (high < low).any():
            continue
        columns, rows = np.meshgrid(np.arange(low[0], high[0] + 1), np.arange(low[1], high[1] + 1))
        spots = np.stack([columns.ravel(), rows.ravel()], 1).astype(float)
        first, second = corners[1] - corners[0], corners[2] - corners[0]
        area = first[0] * second[1] - first[1] * second[0]
        if abs(area) < 1e-12:
            continue
        offset = spots - corners[0]
        weight_one = (offset[:, 0] * second[1] - offset[:, 1] * second[0]) / area
        weight_two = (first[0] * offset[:, 1] - first[1] * offset[:, 0]) / area
        weight_zero = 1 - weight_one - weight_two
        inside = (weight_zero >= 0) & (weight_one >= 0) & (weight_two >= 0)
        height = (weight_zero * points[triangle[0], 2] + weight_one * points[triangle[1], 2]
                  + weight_two * points[triangle[2], 2])[inside]
        row, column = spots[inside, 1].astype(int), spots[inside, 0].astype(int)
        nearer = height > depth[row, column]
        depth[row[nearer], column[nearer]] = height[nearer]


def depth_picture(depth):
    """The depth as a grey picture: near bright, far a quarter darker, the background black."""
    figure = np.isfinite(depth)
    near, far = depth[figure].max(), depth[figure].min()
    value = np.zeros(depth.shape)
    value[figure] = 1.0 - 0.75 * (near - depth[figure]) / (near - far)
    grey = (value * 255).round().astype(np.uint8)
    return Image.fromarray(np.stack([grey] * 3, 2))


def main():
    work = pathlib.Path(sys.argv[1])
    joints = json.loads((work / "gc/body/joints.json").read_text())
    window = window_for(joints)
    depth = np.full((SIZE, SIZE), -np.inf)
    parts = [name for name in PARTS if (work / "parts" / f"{name}.npz").exists()]
    for name in parts:
        data = np.load(work / "parts" / f"{name}.npz")
        rasterise(depth, data["points"], data["faces"], window)
    out = work / "face"
    out.mkdir(exist_ok=True)
    depth_picture(depth).save(out / "depth.png")
    np.save(out / "depth.npy", depth)
    (out / "view.json").write_text(json.dumps({"window": window, "size": SIZE, "parts": parts}))
    print("face depth over", ", ".join(parts), "window", np.round(window, 4).tolist(), flush=True)


if __name__ == "__main__":
    main()
