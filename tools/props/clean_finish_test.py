"""Check the clean finish's own arithmetic: the camera folder rebuilt for Pixel Match must crop the
picture exactly as pixal3d.cpp does, or every photo pixel lands beside its surface; and welding
must merge the corners a glTF file splits at its seams, or xatlas unwraps a heap of loose faces.

The rebuild was checked against a folder pixal3d.cpp staged itself (kit2-rover-4, 2026-10-01):
identical to the pixel. The cases here pin the rule down on shapes whose answer is plain.

Needs numpy and Pillow, which only the prop environment has; hands itself over like the others.

Run: python3 tools/props/clean_finish_test.py
"""
import json
import os
import pathlib
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
PROPS_PYTHON = pathlib.Path(os.environ.get("PROPS_PYTHON", pathlib.Path.home() / ".farm-factory-props/env/bin/python"))

try:
    import numpy as np
    from PIL import Image
except ImportError:
    if PROPS_PYTHON.exists() and os.environ.get("CLEAN_FINISH_TEST_HANDED") != "1":
        os.environ["CLEAN_FINISH_TEST_HANDED"] = "1"
        os.execv(str(PROPS_PYTHON), [str(PROPS_PYTHON), __file__])
    print("skipped: no prop environment on this box")
    sys.exit(0)

sys.path.insert(0, str(HERE))
import clean_finish  # noqa: E402


def test_crop_is_a_tenth_wider_than_the_solid_box_and_centred_on_it():
    alpha = np.zeros((1024, 1024), dtype=np.uint8)
    alpha[200:601, 300:501] = 255          # 401 tall, 201 wide: the span pixal3d.cpp measures is 400
    left, top, side = clean_finish.crop_box(alpha)
    assert side == 440, side               # floor(400 * 1.1), made even
    assert (left, top) == (180, 180), (left, top)   # centre (400, 400) less half the side


def test_faint_matte_edges_do_not_widen_the_crop():
    alpha = np.zeros((100, 100), dtype=np.uint8)
    alpha[10:91, 10:91] = 255
    alpha[0:100, 0:3] = 150                # soft fringe below the solid threshold
    assert clean_finish.crop_box(alpha) == (6, 6, 88), clean_finish.crop_box(alpha)


def test_staged_views_hold_the_crop_and_the_front_camera():
    with tempfile.TemporaryDirectory() as folder:
        folder = pathlib.Path(folder)
        picture = np.zeros((1024, 1024, 4), dtype=np.uint8)
        picture[200:601, 300:501] = (200, 30, 30, 255)
        Image.fromarray(picture).save(folder / "cut.png")
        staged = clean_finish.staged_views(folder / "cut.png", folder / "run.svviews")
        image = np.asarray(Image.open(staged / "input.png"))
        assert image.shape == (440, 440, 4), image.shape
        assert image[20:421, 120:321, 3].min() == 255      # the subject, moved by (-180, -180)
        assert image[:, :100, 3].max() == 0                 # padding stays see-through
        camera = json.loads((staged / "transforms.json").read_text())
        assert camera["mesh_scale"] == 1 and len(camera["frames"]) == 1
        assert abs(camera["camera_angle_x"] - 0.34906584) < 1e-7


def test_a_picture_over_1024_is_cropped_as_pixal3d_cpp_sees_it():
    with tempfile.TemporaryDirectory() as folder:
        folder = pathlib.Path(folder)
        picture = np.zeros((2048, 2048, 4), dtype=np.uint8)
        picture[400:1202, 600:1002] = (10, 200, 10, 255)
        Image.fromarray(picture).save(folder / "cut.png")
        image = Image.open(clean_finish.staged_views(folder / "cut.png", folder / "v") / "input.png")
        assert image.size[0] < 1024 and abs(image.size[0] - 440) <= 2, image.size


def test_welding_merges_corners_split_at_a_seam():
    points = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]], dtype=float)
    faces = np.array([[0, 1, 2], [3, 4, 5]])
    merged, renumbered = clean_finish.welded(points, faces)
    assert len(merged) == 4, len(merged)
    assert renumbered[0, 1] == renumbered[1, 0] and renumbered[0, 2] == renumbered[1, 2]


if __name__ == "__main__":
    for name, check in sorted(globals().items()):
        if name.startswith("test_") and callable(check):
            check()
            print(f"ok  {name}")
