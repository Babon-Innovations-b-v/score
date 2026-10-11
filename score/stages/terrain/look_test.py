"""The terrain look's measure: the horizon's row from a view, and the share under it where a mask draws nothing.

Run: .venv/bin/python score/stages/terrain/look_test.py
"""
import pathlib
import sys
import tempfile

import numpy as np
from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))

from score.stages.terrain import look  # noqa: E402

SIZE = (200, 100)


def test_the_horizon_lies_mid_picture_on_a_level_view_and_low_on_one_looking_up():
    level = {"eye": [0, 10, 0], "aim": [-100, 10, 0], "fov": 90}
    up = {"eye": [0, 10, 0], "aim": [-100, 30, 0], "fov": 90}
    assert abs(look.horizon_row(level, SIZE) - 50) < 1e-9
    assert look.horizon_row(up, SIZE) > 50


def test_a_mask_open_under_the_horizon_is_measured_and_a_closed_one_is_not():
    level = {"eye": [0, 10, 0], "aim": [-100, 10, 0], "fov": 90}
    with tempfile.TemporaryDirectory() as folder:
        alpha = np.zeros((SIZE[1], SIZE[0]), dtype=np.uint8)
        alpha[60:, :] = 255
        open_mask = pathlib.Path(folder) / "open.png"
        Image.fromarray(np.dstack([alpha] * 4)).save(open_mask)
        alpha[:, :] = 255
        closed_mask = pathlib.Path(folder) / "closed.png"
        Image.fromarray(np.dstack([alpha] * 4)).save(closed_mask)
        assert look.holes_under_horizon(open_mask, level, SIZE) > 0.1
        assert look.holes_under_horizon(closed_mask, level, SIZE) == 0.0


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
