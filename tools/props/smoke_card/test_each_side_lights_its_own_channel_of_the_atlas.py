"""Invariant: the smoke flipbook's pack (card.py) lays each rendered frame in its cell of the 4 x 4 atlas in reading
order, smoke_a's red, green and blue the frame lit from the right, top and back, smoke_b's from the left, bottom and
front, both alphas the smoke's cover, and refuses a render that took a different number of frames.

Breaks that turn it red:
- card.ATLAS: smoke_a's sides swapped (top in red) -> the right-lit grey is not in red
- card.atlas: the row and column of a frame swapped -> frame 1 lands in the second row
- card.atlas: the alpha the lit grey -> the cover is not the alpha
- card.packed: no check of the frames taken -> a 15-frame render packs a blank cell
"""
import json
import pathlib
import sys

import numpy as np
import pytest
from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import card  # noqa: E402

PIXELS = 8
LEVELS = {"right": 10, "left": 20, "top": 30, "bottom": 40, "back": 50, "front": 60}


def rendered(work, taken):
    """Frames as billow.py writes them: frame i lit from a side at its level plus i, its cover 100 plus i."""
    (work / "frames").mkdir(parents=True)
    for index in range(card.FRAMES):
        for side, level in LEVELS.items():
            pixels = np.zeros((PIXELS, PIXELS, 4), dtype=np.uint8)
            pixels[..., :3] = level + index
            pixels[..., 3] = 100 + index
            Image.fromarray(pixels).save(work / "frames" / f"{index:02d}_{side}.png")
    (work / "sim.json").write_text(json.dumps({"taken": list(range(taken)), "pixels": PIXELS, "domain_m": 3.0}))
    return work


@pytest.mark.parametrize("taken, refused", [(16, False), (15, True)])
def test_each_side_lights_its_own_channel_of_the_atlas(tmp_path, taken, refused):
    work = rendered(tmp_path / "work", taken)
    if refused:
        with pytest.raises(ValueError, match="frames rendered"):
            card.packed(work, tmp_path / "out")
        return
    written = card.packed(work, tmp_path / "out")
    for name, sides in card.ATLAS.items():
        atlas = np.asarray(Image.open(written[name]))
        assert atlas.shape == (4 * PIXELS, 4 * PIXELS, 4)
        for index in (0, 1, 5, 15):
            row, column = divmod(index, 4)
            cell = atlas[row * PIXELS, column * PIXELS]
            assert list(cell) == [LEVELS[side] + index for side in sides] + [100 + index], (name, index)
    record = json.loads(written["surface.json"].read_text())
    assert record["family"] == "flipbook" and record["atlas"]["channels"]["smoke_b.png"]["rgb"] == ["left", "bottom",
                                                                                                    "front"]
