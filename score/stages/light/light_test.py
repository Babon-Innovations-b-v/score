"""Check the light stage's measures on pictures made here: a floodlight bank drawn as a grid of lit panes in a dark
frame has no halo and a low fill, the same bank glowing into the air round it has both; a flat-palette disc covers
most of itself with its eight commonest colours and a noisy one does not; a sky's colour, its blue to red and its rise
to the horizon are read on the pixels the flat sky held before; haze over the picture's lower part reads as a veil; a point straight ahead falls in the picture's middle.

Run: .venv/bin/python score/stages/light/light_test.py   (make tests runs it)
"""
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
from score.stages.light import measure  # noqa: E402

SIZE = 200
WIDE = 480


def grid_bank():
    picture = np.full((WIDE, WIDE, 3), 20.0)
    picture[210:270, 200:280] = 5.0
    for row in range(2):
        for column in range(3):
            picture[215 + row * 28:237 + row * 28, 205 + column * 25:225 + column * 25] = 250.0
    return picture


def glowing_bank():
    rows, columns = np.mgrid[0:WIDE, 0:WIDE]
    distance = np.hypot(columns - 240, rows - 240)
    picture = np.full((WIDE, WIDE, 3), 20.0) + (230.0 * np.exp(-distance / 45.0))[..., None]
    return np.clip(picture, 0, 255)


def check_heads():
    grid, glow = measure.head(grid_bank(), 240, 240, 40), measure.head(glowing_bank(), 240, 240, 40)
    assert grid["halo"] < 0.02 and grid["fill"] < 0.1, grid
    assert glow["halo"] > 0.08 and glow["fill"] > 0.28, glow


def check_discs():
    rng = np.random.default_rng(1)
    flat = np.zeros((SIZE, SIZE, 3))
    flat[:, :100] = [40, 90, 160]
    flat[:, 100:] = [60, 140, 60]
    noisy = np.clip(flat + rng.normal(0, 30, flat.shape), 0, 255)
    assert measure.disc(flat, 100, 100, 80)["flat_share"] > 0.9
    assert measure.disc(noisy, 100, 100, 80)["flat_share"] < 0.2


def check_sky():
    before = np.zeros((SIZE, SIZE, 3))
    before[:] = [70, 42, 16]
    before[120:] = [120, 60, 30]
    after = before.copy()
    after[:90] = np.linspace(170, 195, 90)[:, None, None] * np.array([1.0, 0.78, 0.6])
    concept = {"mean_rgb": [188.1, 145.2, 112.1]}
    found = measure.sky(before, after, concept)
    assert found["before"]["gap_to_concept"] > 80 and found["after"]["gap_to_concept"] < 20, found
    assert found["after"]["rise_to_horizon"] > 0 and abs(found["after"]["blue_to_red"] - 0.6) < 0.01


def check_veil():
    before = np.full((100, 100, 3), 40.0)
    after = before.copy()
    after[:50] += 100.0  # a lamp's glow up in the sky leaves the place below as it was
    assert measure.veil(before, after) == 0.0
    after[60:] += 30.0  # haze laid over the place's lower part
    assert abs(measure.veil(before, after) - 30.0 / 255.0) < 1e-3


def check_where():
    view = {"eye": [0, 0, 0], "aim": [0, 0, -10], "up": [0, 1, 0], "fov": 90}
    x, y, depth, focal = measure.where(view, (200, 100), [0, 0, -5])
    assert (round(x), round(y), round(depth, 6), round(focal, 6)) == (100, 50, 5.0, 100.0)
    assert measure.where(view, (200, 100), [0, 0, 5])[0] is None


def main():
    check_heads()
    check_discs()
    check_sky()
    check_veil()
    check_where()
    print("light_test: ok")


if __name__ == "__main__":
    main()
