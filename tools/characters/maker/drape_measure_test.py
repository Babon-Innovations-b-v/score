"""Check drape_measure's plain pieces on cloth whose numbers are known: a flat sheet bends 0 degrees, a sheet folded
along one edge bends by the fold, and each leg's hem is its own lowest trouser point.

Run: .venv/bin/python tools/characters/maker/drape_measure_test.py   (make tests runs it with the framework's environment)
"""
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import drape_measure  # noqa: E402

# Two triangles sharing the edge from point 0 to point 1.
POINTS = np.array([[0.0, 0.0, 0.0], [0.0, 1.0, 0.0], [-1.0, 0.0, 0.0], [1.0, 0.0, 0.0]])
FACES = np.array([[0, 2, 1], [0, 1, 3]])


def test_flat_sheet_bends_nothing():
    bends, heights = drape_measure.edge_bends(POINTS, FACES)
    assert len(bends) == 1 and abs(bends[0]) < 1e-9 and abs(heights[0] - 0.5) < 1e-9


def test_fold_bends_by_its_angle():
    folded = POINTS.copy()
    folded[3] = [0.0, 0.0, 1.0]  # the right triangle turned 90 degrees about the shared edge
    bends, _ = drape_measure.edge_bends(folded, FACES)
    assert abs(bends[0] - 90.0) < 1e-6


def test_hem_is_each_legs_lowest_point():
    points = np.array([[0.1, 0.30, 0.0], [0.1, 0.20, 0.0], [-0.1, 0.25, 0.0], [0.0, 1.0, 0.0]])
    labels = np.array(["pant_f_l", "pant_l_cuff_b", "pant_b_r", "left_ftorso"])
    assert abs(drape_measure.hem_height(points, labels, 0.05) - 0.175) < 1e-9


if __name__ == "__main__":
    for name, check in sorted(globals().items()):
        if name.startswith("test_"):
            check()
            print("ok", name)
