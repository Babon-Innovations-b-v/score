"""The camera folder the clean finish rebuilds for Pixel Match crops the picture exactly as pixal3d.cpp does, or every
photo pixel lands beside its surface; an unlit paint copy is cut from the same square; and welding merges the
corners a glTF file splits at its seams, or xatlas unwraps a heap of loose faces (clean_finish.py).

The rebuild was checked against a folder pixal3d.cpp staged itself (kit2-rover-4, 2026-10-01): identical to the pixel.
The cases here pin the rule on shapes whose answer is worked out by hand in each comment.

Breaks that turn each test red (each applied once and seen red, 2026-10-26):
- test_the_crop_is_a_tenth_wider_than_the_solid_box_and_centred_on_it: crop_box's `span * CROP_MARGIN` made `span`.
- test_faint_matte_edges_do_not_widen_the_crop: crop_box's `alpha > SOLID_ALPHA` made `alpha > 0`.
- test_the_staged_picture_is_the_crop_moved_into_its_square: staged_views' `staged.paste(matte, (-left, -top))` made
  `staged.paste(matte, (left, top))`.
- test_a_picture_over_1024_is_cropped_as_pixal3d_cpp_sees_it: staged_views' shrink made `if False:`.
- test_the_unlit_copy_is_cut_where_the_camera_folder_was_and_keeps_its_matte: unlit_views'
  `square_crop(paint, *staged_offset(whole, staged), ...)` made `square_crop(paint, 0, 0, ...)`.
- test_a_square_crop_past_the_edge_is_black_there: square_crop's piece pasted at the canvas's corner
  (`canvas[0:piece.shape[0], 0:piece.shape[1]] = piece`).
- test_welding_merges_corners_split_at_a_seam: welded returns `points, faces` unmerged.
"""
import json
import pathlib
import sys

import numpy as np
from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import clean_finish  # noqa: E402


def test_the_crop_is_a_tenth_wider_than_the_solid_box_and_centred_on_it():
    alpha = np.zeros((1024, 1024), dtype=np.uint8)
    alpha[200:601, 300:501] = 255  # 401 tall, 201 wide: the span pixal3d.cpp measures is 400
    left, top, side = clean_finish.crop_box(alpha)
    assert side == 440, side  # floor(400 * 1.1), made even
    assert (left, top) == (180, 180), (left, top)  # centre (400, 400) less half the side


def test_faint_matte_edges_do_not_widen_the_crop():
    alpha = np.zeros((100, 100), dtype=np.uint8)
    alpha[10:91, 10:91] = 255  # span 80: side 88, centre 50
    alpha[0:100, 0:3] = 150  # soft fringe below the solid threshold
    assert clean_finish.crop_box(alpha) == (6, 6, 88), clean_finish.crop_box(alpha)


def test_the_staged_picture_is_the_crop_moved_into_its_square(tmp_path):
    picture = np.zeros((1024, 1024, 4), dtype=np.uint8)
    picture[200:601, 300:501] = (200, 30, 30, 255)
    Image.fromarray(picture).save(tmp_path / "cut.png")
    staged = clean_finish.staged_views(tmp_path / "cut.png", tmp_path / "run.svviews")
    image = np.asarray(Image.open(staged / "input.png"))
    assert image.shape == (440, 440, 4), image.shape
    assert image[20:421, 120:321, 3].min() == 255  # the subject, moved by (-180, -180)
    assert image[:, :100, 3].max() == 0  # padding stays see-through
    camera = json.loads((staged / "transforms.json").read_text())
    assert len(camera["frames"]) == 1 and camera["frames"][0]["file_path"] == "input.png"


def test_a_picture_over_1024_is_cropped_as_pixal3d_cpp_sees_it(tmp_path):
    picture = np.zeros((2048, 2048, 4), dtype=np.uint8)
    picture[400:1202, 600:1002] = (10, 200, 10, 255)  # the case above at twice the size: halved first, so 440 again
    Image.fromarray(picture).save(tmp_path / "cut.png")
    image = Image.open(clean_finish.staged_views(tmp_path / "cut.png", tmp_path / "v") / "input.png")
    assert abs(image.size[0] - 440) <= 2, image.size


def test_the_unlit_copy_is_cut_where_the_camera_folder_was_and_keeps_its_matte(tmp_path):
    noise = np.random.default_rng(3).integers(0, 255, (300, 300, 3), dtype=np.uint8)
    Image.fromarray(noise).save(tmp_path / "picture.png")
    cut = np.dstack([noise, np.zeros((300, 300), dtype=np.uint8)])
    cut[40:201, 90:171, 3] = 255  # span 160: side 176, centre (130, 120), so the square starts at (42, 32)
    Image.fromarray(cut).save(tmp_path / "cut.png")
    views = clean_finish.staged_views(tmp_path / "cut.png", tmp_path / "run.svviews")
    unlit = 255 - noise  # a stand-in paint copy, aligned
    Image.fromarray(unlit).save(tmp_path / "unlit.png")
    painted = clean_finish.unlit_views(views, tmp_path / "picture.png", tmp_path / "unlit.png",
                                       tmp_path / "run-unlit.svviews")
    staged = np.asarray(Image.open(views / "input.png"))
    image = np.asarray(Image.open(painted / "input.png"))
    assert clean_finish.staged_offset(noise, staged) == (42, 32)
    solid = staged[..., 3] == 255
    assert (image[..., 3] == staged[..., 3]).all()
    assert (image[solid][:, :3] == 255 - staged[solid][:, :3]).all()
    assert (painted / "transforms.json").read_text() == (views / "transforms.json").read_text()


def test_a_square_crop_past_the_edge_is_black_there():
    image = np.full((10, 10, 3), 7, dtype=np.uint8)
    crop = clean_finish.square_crop(image, -2, 5, 6)  # columns -2..3, rows 5..10: two columns left, one row below
    assert crop.shape == (6, 6, 3)
    assert crop[:, :2].max() == 0 and crop[5:, :].max() == 0
    assert crop[:5, 2:].min() == 7


def test_welding_merges_corners_split_at_a_seam():
    points = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]], dtype=float)
    faces = np.array([[0, 1, 2], [3, 4, 5]])
    merged, renumbered = clean_finish.welded(points, faces)
    assert len(merged) == 4, len(merged)
    assert renumbered[0, 1] == renumbered[1, 0] and renumbered[0, 2] == renumbered[1, 2]
