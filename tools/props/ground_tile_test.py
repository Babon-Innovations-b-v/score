"""Check a ground tile repeats without a seam and softens as asked.

The step needs numpy and Pillow, which only the prop environment has. Run by the gate with the
system python, this hands itself to the prop environment when the box has one, and says it skipped
when it does not.

Run: python3 tools/props/ground_tile_test.py
"""
import os
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
PROPS_PYTHON = pathlib.Path(os.environ.get("PROPS_PYTHON", pathlib.Path.home() / ".farm-factory-props/env/bin/python"))

try:
    import numpy as np
    from PIL import Image
except ImportError:
    if PROPS_PYTHON.exists() and os.environ.get("GROUND_TILE_TEST_HANDED") != "1":
        os.environ["GROUND_TILE_TEST_HANDED"] = "1"
        os.execv(str(PROPS_PYTHON), [str(PROPS_PYTHON), __file__])
    print("skipped: no prop environment on this box")
    sys.exit(0)

sys.path.insert(0, str(HERE))
import ground_tile  # noqa: E402


def a_ramp():
    """A picture dark at its left edge and light at its right, the worst case for a seam."""
    row = np.linspace(0, 255, 512, dtype=np.float32)
    return Image.fromarray(np.tile(row, (512, 1)).astype(np.uint8)).convert("RGB")


def opposite_edges_meet():
    pixels = ground_tile.seamless(a_ramp())
    left, right = pixels[:, 0], pixels[:, -1]
    step_inside = np.abs(pixels[:, 1] - pixels[:, 0]).max()
    assert np.abs(left - right).max() <= step_inside * 2 + 1, "the tile has a seam where it repeats"


def softening_keeps_the_mean_and_narrows_the_spread():
    pixels = ground_tile.seamless(a_ramp())
    soft = ground_tile.softened(pixels, 0.5)
    assert np.allclose(soft.mean(axis=(0, 1)), pixels.mean(axis=(0, 1)), atol=0.5), "the colour moved"
    assert soft.std() < pixels.std() * 0.6, "the contrast did not come down"


def the_tile_is_square_at_its_size():
    assert ground_tile.ground_tile(a_ramp()).size == (ground_tile.SIDE, ground_tile.SIDE)


for check in (opposite_edges_meet, softening_keeps_the_mean_and_narrows_the_spread, the_tile_is_square_at_its_size):
    check()
print("ok")
