"""Check the window mask on a wall whose right answer is obvious: small dark panes are windows, a
long dark seam is not.

The step needs numpy, scipy and Pillow, which only the prop environment has. Run by the gate with
the system python, this hands itself to the prop environment when the box has one, and says it
skipped when it does not.

Run: python3 tools/props/window_mask_test.py
"""
import os
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
PROPS_PYTHON = pathlib.Path(os.environ.get("PROPS_PYTHON", pathlib.Path.home() / ".farm-factory-props/env/bin/python"))

try:
    import numpy as np
    from PIL import Image
    import scipy  # noqa: F401
except ImportError:
    if PROPS_PYTHON.exists() and os.environ.get("WINDOW_MASK_TEST_HANDED") != "1":
        os.environ["WINDOW_MASK_TEST_HANDED"] = "1"
        os.execv(str(PROPS_PYTHON), [str(PROPS_PYTHON), __file__])
    print("skipped: no prop environment on this box")
    sys.exit(0)

sys.path.insert(0, str(HERE))
import window_mask  # noqa: E402

# A 2048 wall, like a finished model's texture, four times the mask's size.
TEXTURE_SIDE = 2048
SCALE = TEXTURE_SIDE // window_mask.SIDE


def a_wall():
    """A pale wall with one dark pane at (400, 400) and one long dark seam across row 1200."""
    wall = np.full((TEXTURE_SIDE, TEXTURE_SIDE), 200, dtype=np.uint8)
    wall[400:408, 400:406] = 60
    wall[1200:1203, 200:1800] = 60
    return Image.fromarray(wall)


def a_pane_is_a_window():
    mask = np.asarray(window_mask.window_mask(a_wall()))
    assert mask[404 // SCALE, 403 // SCALE] == 255, "the pane is not in the mask"


def a_seam_is_not_a_window():
    mask = np.asarray(window_mask.window_mask(a_wall()))
    assert not mask[1201 // SCALE, 1000 // SCALE], "the seam is in the mask"


def a_plain_wall_has_no_windows():
    plain = Image.fromarray(np.full((TEXTURE_SIDE, TEXTURE_SIDE), 200, dtype=np.uint8))
    assert not np.asarray(window_mask.window_mask(plain)).any(), "a plain wall has windows"


for check in (a_pane_is_a_window, a_seam_is_not_a_window, a_plain_wall_has_no_windows):
    check()
print("ok")
