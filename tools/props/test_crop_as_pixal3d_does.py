"""The camera folder the clean finish rebuilds for Pixel Match crops the picture exactly as pixal3d.cpp does, or every
photo pixel lands beside its surface; an unlit paint copy is cut from the same square; and welding merges the
corners a glTF file splits at its seams, or xatlas unwraps a heap of loose faces (clean_finish.py).

The rebuild was checked against a folder pixal3d.cpp staged itself (kit2-rover-4, 2026-10-01): identical to the pixel.
The case here pins the rule on one picture whose answer is worked out by hand in the comments: a subject whose square
reaches past the picture's left and bottom edges, a faint fringe beside it, the same picture at twice the size, and
its unlit copy; then the crop's own square as a model split at a seam the way a glTF file splits it, unwrapped (the
weld's real caller) at the picture's pixel scale and at a unit scale, beside two triangles that only come near and must
stay apart.

Breaks that turn test_crop_as_pixal3d_does red (each applied once and seen red, 2026-10-26; again 2026-11-13 merged):
- crop_box's `span * CROP_MARGIN` made `span`.
- crop_box's `alpha > SOLID_ALPHA` made `alpha > 0`.
- staged_views' `staged.paste(matte, (-left, -top))` made `staged.paste(matte, (left, top))`.
- staged_views' shrink made `if False:`.
- unlit_views' `square_crop(paint, *staged_offset(whole, staged), ...)` made `square_crop(paint, 0, 0, ...)`.
- square_crop's piece pasted at the canvas's corner (`canvas[0:piece.shape[0], 0:piece.shape[1]] = piece`).
- unlit_views' camera copy writes `"{}"` in place of the staged folder's transforms.json.
- welded returns `points, faces` unmerged.
"""
import json
import pathlib
import sys

import numpy as np
import trimesh
from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import clean_finish  # noqa: E402

SIDE = 1024  # pixal3d.cpp's long side: this picture is staged as it is, its double is shrunk to it first
SUBJECT_ROWS, SUBJECT_COLUMNS = slice(100, 1001), slice(50, 651)  # 901 tall, 601 wide: the span measured is 900
FRINGE_COLUMNS = slice(1000, SIDE)  # soft alpha below the solid threshold, all down the right edge
# floor(900 * 1.1) = 990, made even; centre (350, 550) less half the side: the square starts 145 columns left of the
# picture and ends 21 rows below it.
LEFT, TOP, CROP = -145, 55, 990
BELOW = SIDE - TOP  # the square's first row past the picture's bottom
# A unit square as two triangles, each with its own copy of the diagonal's corners: a glTF seam.
SEAM_QUAD = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]], dtype=float)
SEAM_FACES = np.array([[0, 1, 2], [3, 4, 5]])
# Each row: the crop square's model at the picture's pixel scale or at a unit scale; how far the second triangle is
# moved right, in squares; how many corners the unwrapped model keeps; whether its triangles share their diagonal.
WELD_CASES = [
    ("seam at the square's pixel scale", True, 0, 4, True),
    ("seam at unit scale", False, 0, 4, True),
    ("second triangle a hundredth of the square away", False, 0.01, 6, False),
]


def test_crop_as_pixal3d_does(tmp_path):
    noise = np.random.default_rng(3).integers(0, 255, (SIDE, SIDE, 3), dtype=np.uint8)
    alpha = np.zeros((SIDE, SIDE), dtype=np.uint8)
    alpha[SUBJECT_ROWS, SUBJECT_COLUMNS] = 255
    alpha[:, FRINGE_COLUMNS] = 150
    cut = np.dstack([noise, alpha])
    Image.fromarray(noise).save(tmp_path / "picture.png")
    Image.fromarray(cut).save(tmp_path / "cut.png")
    Image.fromarray(cut.repeat(2, axis=0).repeat(2, axis=1)).save(tmp_path / "cut-double.png")
    Image.fromarray(255 - noise).save(tmp_path / "unlit.png")  # a stand-in paint copy, aligned

    left, top, side = clean_finish.crop_box(alpha)  # the square the staged folder is cut from, in picture pixels
    assert (left, top, side) == (LEFT, TOP, CROP), (left, top, side)
    views = clean_finish.staged_views(tmp_path / "cut.png", tmp_path / "run.svviews")
    staged = np.asarray(Image.open(views / "input.png"))
    assert staged.shape == (CROP, CROP, 4), staged.shape
    moved = np.zeros((CROP, CROP, 4), dtype=np.uint8)  # the cut moved by (145, -55); padding stays see-through
    moved[:BELOW, -LEFT:] = cut[TOP:, :LEFT + CROP]
    assert (staged == moved).all(), "the staged picture is not the crop moved into its square"
    camera = json.loads((views / "transforms.json").read_text())
    assert len(camera["frames"]) == 1 and camera["frames"][0]["file_path"] == "input.png", camera["frames"]

    double = Image.open(clean_finish.staged_views(tmp_path / "cut-double.png", tmp_path / "v") / "input.png")
    assert abs(double.size[0] - CROP) <= 2, double.size  # halved first, as pixal3d.cpp sees it

    painted = clean_finish.unlit_views(views, tmp_path / "picture.png", tmp_path / "unlit.png",
                                       tmp_path / "run-unlit.svviews")
    assert (painted / "transforms.json").read_text() == (views / "transforms.json").read_text(), \
        "the unlit camera folder lost the staged folder's camera"
    image = np.asarray(Image.open(painted / "input.png"))
    assert clean_finish.staged_offset(noise, staged) == (LEFT, TOP), clean_finish.staged_offset(noise, staged)
    assert (image[..., 3] == staged[..., 3]).all(), "the unlit copy lost the camera folder's matte"
    solid = staged[..., 3] == 255
    assert (image[solid][:, :3] == 255 - staged[solid][:, :3]).all(), "the unlit copy is not cut where the folder was"
    paint = np.zeros((CROP, CROP, 3), dtype=np.uint8)  # black past the picture's left and bottom edges
    paint[:BELOW, -LEFT:] = 255 - noise[TOP:, :LEFT + CROP]
    assert (image[..., :3] == paint).all(), "the unlit square is not black past the picture's edge"

    # The crop's square as a raw model split at a seam, unwelded until unwrapped welds it.
    for name, in_pixels, apart, kept, shared in WELD_CASES:
        points = SEAM_QUAD * (side if in_pixels else 1) + ([left, top, 0] if in_pixels else 0)
        points[3:, 0] += apart * (side if in_pixels else 1)
        raw = tmp_path / f"{name}.ply"
        trimesh.Trimesh(points, SEAM_FACES, process=False).export(raw)
        model = trimesh.load(clean_finish.unwrapped(raw, tmp_path / f"{name}.glb"), force="mesh", process=False)
        assert len(model.vertices) == kept, (name, len(model.vertices))
        assert np.allclose(model.vertices[model.faces], points[SEAM_FACES]), (name, "a face moved off its corners")
        joined = set(model.faces[0, 1:]) == set(model.faces[0]) & set(model.faces[1])  # the diagonal, one corner pair
        assert joined == shared, (name, model.faces.tolist())
