"""Check the luminance per region on pictures made here: a matched object half as bright as the game's is dark, one as
bright is lit, the game's black sky is never judged, and the bands split the picture top to bottom. No Blender: the
render, the annotation and the game's shot are written by the test.

Breaks (each applied once, seen red, reverted), in tools/review/brightness.py:
- half as bright is dark: region calls dark only under a tenth of the game (`0.1 * game`).
- as bright is lit: region counts the whole picture's pixels (`pixels.size`).
- the game's black sky: region drops its LIT_FLOOR test.
- the bands: bands spreads the rows over twice the picture's height (the bottom bands come out empty).

Run: PROPS_HOME=$(mktemp -d) .venv/bin/python tools/review/test_a_region_is_judged_against_the_games_own_light.py
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


# Each row: its name, the scene's tower and the game's (linear luminance), the verdict and luminance ratio the tower
# must get.
ROWS = [
    ("half-as-bright-is-dark", 0.03, 0.08, "dark", 0.375),
    ("as-bright-is-lit", 0.08, 0.08, "lit", 1.0),
]


def test_a_region_is_judged_against_the_games_own_light():
    for name, scene_tower, game_tower, verdict, ratio in ROWS:
        with tempfile.TemporaryDirectory() as folder:
            found = measured(pathlib.Path(folder), scene_tower=scene_tower, game_tower=game_tower)
        matched, bands = found["matched"], found["bands"]
        assert matched["verdict"] == verdict, (name, matched)
        assert abs(matched["ratio"] - ratio) < 0.05, (name, matched)
        assert matched["pixels"] == (WIDE // 2) * (TALL // 2), (name, matched)
        assert [band["pixels"] for band in bands] == [WIDE * TALL // brightness.BANDS] * brightness.BANDS, (name, bands)
        assert all(band["verdict"] == "unjudged" for band in bands[: brightness.BANDS // 2]), (name, bands)
        assert all(band["verdict"] != "unjudged" for band in bands[brightness.BANDS // 2:]), (name, bands)


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[2] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in sorted(globals().items()):
        if name.startswith("test_") and callable(test):
            test()
            print("ok", name)
