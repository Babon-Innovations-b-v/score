"""Check the luminance per region on pictures made here: a matched object half as bright as the game's is dark, one as
bright is lit, the game's black sky is never judged, and the bands split the picture top to bottom. No Blender: the
render, the annotation and the game's shot are written by the test.

Run: .venv/bin/python tools/review/brightness_test.py   (make tests runs it with the framework's environment)
"""
import json
import pathlib
import sys
import tempfile

import numpy as np
from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import brightness  # noqa: E402

WIDE, TALL = 64, 32


def srgb_grey(linear):
    """An 8-bit grey of the given linear luminance."""
    encoded = linear * 12.92 if linear <= 0.0031308 else 1.055 * linear ** (1 / 2.4) - 0.055
    return int(round(encoded * 255))


def picture(path, sky, tower, size=(WIDE, TALL)):
    """A picture whose top half is `sky` and whose middle columns of the bottom half (the tower) are `tower`."""
    values = np.full((size[1], size[0]), srgb_grey(sky), dtype=np.uint8)
    values[size[1] // 2:, size[0] // 4: 3 * size[0] // 4] = srgb_grey(tower)
    Image.fromarray(values, "L").convert("RGB").save(path)


def annotation(folder, view):
    """The view's object ids: the tower's pixels id 1 (a far city tower), the rest id 0 (the sky dome)."""
    ids = np.zeros((TALL, WIDE), dtype=np.int32)
    ids[TALL // 2:, WIDE // 4: 3 * WIDE // 4] = 1
    np.savez(folder / f"{view}-passes.npz", ids=ids, depth=np.zeros((TALL, WIDE)), normal=np.zeros((TALL, WIDE, 3)))
    (folder / "ids.json").write_text(json.dumps({"0": "/launch/Sky", "1": "/launch/Places/far_city/Towers/a_1"}))


def measured(root, scene_tower, game_tower, game_sky=0.002):
    for name in ("renders", "annotate", "shots"):
        (root / name).mkdir(exist_ok=True)
    picture(root / "renders/shore-look.png", 0.002, scene_tower)
    picture(root / "shots/game-shore.jpg", game_sky, game_tower, size=(WIDE * 2, TALL * 2))
    annotation(root / "annotate", "shore")
    return brightness.measure(root / "renders", root / "annotate", root / "shots", ["far_city", "Towers"])["shore"]


def test_a_tower_half_as_bright_as_the_game_is_dark():
    with tempfile.TemporaryDirectory() as folder:
        found = measured(pathlib.Path(folder), scene_tower=0.03, game_tower=0.08)
    assert found["matched"]["verdict"] == "dark", found["matched"]
    assert abs(found["matched"]["ratio"] - 0.375) < 0.05, found["matched"]


def test_a_tower_as_bright_as_the_game_is_lit():
    with tempfile.TemporaryDirectory() as folder:
        found = measured(pathlib.Path(folder), scene_tower=0.08, game_tower=0.08)
    assert found["matched"]["verdict"] == "lit", found["matched"]
    assert found["matched"]["pixels"] == (WIDE // 2) * (TALL // 2)


def test_the_games_black_sky_is_never_judged():
    with tempfile.TemporaryDirectory() as folder:
        found = measured(pathlib.Path(folder), scene_tower=0.08, game_tower=0.08)
    top = found["bands"][: brightness.BANDS // 2]
    assert all(band["verdict"] == "unjudged" for band in top), top


def test_the_bands_split_the_picture_top_to_bottom():
    masks = brightness.bands((TALL, WIDE))
    assert len(masks) == brightness.BANDS
    assert sum(mask.sum() for mask in masks) == TALL * WIDE
    assert masks[0][0].all() and masks[-1][-1].all()


if __name__ == "__main__":
    for name, test in sorted(globals().items()):
        if name.startswith("test_") and callable(test):
            test()
            print("ok", name)
