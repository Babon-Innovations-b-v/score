"""Check the depth panorama folding (pano.py) and the world placing (align.py) on a room whose
answer is obvious: a cube round the eye, and a floor straight under the camera.

The checks need numpy, which only the prop environment has. Run by the gate with the system
python, this hands itself to the prop environment when the box has one, and says it skipped when
it does not. Run: python3 tools/props/scene/pano_test.py
"""
import os
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
PROPS_PYTHON = pathlib.Path(os.environ.get("PROPS_PYTHON", pathlib.Path.home() / ".farm-factory-props/env/bin/python"))

try:
    import numpy as np
except ImportError:
    if PROPS_PYTHON.exists() and os.environ.get("PANO_TEST_HANDED") != "1":
        os.environ["PANO_TEST_HANDED"] = "1"
        os.execv(str(PROPS_PYTHON), [str(PROPS_PYTHON), __file__])
    print("skipped: no prop environment on this box")
    sys.exit(0)

sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
from align import placed, seat_transform  # noqa: E402
from pano import directions, encoded, folded  # noqa: E402

# depth_pano.gd's six ways, as the columns (right, up, back) of each camera's turn.
WAYS = {
    "north": [[1, 0, 0], [0, 1, 0], [0, 0, 1]],
    "east": [[0, 0, 1], [0, 1, 0], [-1, 0, 0]],
    "south": [[-1, 0, 0], [0, 1, 0], [0, 0, -1]],
    "west": [[0, 0, -1], [0, 1, 0], [1, 0, 0]],
    "up": [[1, 0, 0], [0, 0, 1], [0, -1, 0]],
    "down": [[1, 0, 0], [0, 0, -1], [0, 1, 0]],
}
HALF = 2.0
FACE = 64


def cube_face(columns):
    """What a 90-degree camera turned by `columns` sees inside a cube of half side HALF."""
    right, up, back = (np.array(column, float) for column in columns)
    coordinates = (np.arange(FACE) + 0.5) / FACE * 2 - 1
    x, y = np.meshgrid(coordinates, -coordinates)
    rays = x[..., None] * right + y[..., None] * up - back
    rays /= np.linalg.norm(rays, axis=-1, keepdims=True)
    return HALF / np.abs(rays).max(axis=-1)


def test_a_cube_folds_into_the_right_distance_every_way():
    pano = folded({way: cube_face(columns) for way, columns in WAYS.items()}, WAYS, FACE * 4)
    expected = HALF / np.abs(directions(FACE * 4)).max(axis=-1)
    assert not np.isnan(pano).any()
    assert np.median(np.abs(pano - expected) / expected) < 0.02


def test_the_middle_column_looks_north_and_the_top_row_up():
    rays = directions(400)
    assert np.allclose(rays[100, 200], [0.0, 0.0, -1.0], atol=0.01)
    assert np.allclose(rays[100, 300], [1.0, 0.0, 0.0], atol=0.01)
    assert rays[0, 0][1] > 0.99


def test_the_encoded_picture_is_white_near_and_black_where_nothing_was_hit():
    picture = np.asarray(encoded(np.array([[0.1, 10.0, np.inf]]), 100.0))
    assert picture[0, 0] == 255 and picture[0, 2] == 0 and 0 < picture[0, 1] < 255


def test_a_worlds_ground_lands_on_the_floor_under_its_spot():
    metric = {"metric_scale_factor": 2.0, "ground_plane_offset": 1.5}
    _, basis, origin = seat_transform(metric, 1.6, (3.0, -4.0))
    floor_under_camera = np.array([[0.0, 1.5 / 2.0, 0.0]])
    ahead = np.array([[0.0, 0.0, 1.0]])
    assert np.allclose(placed(floor_under_camera, basis, origin), [[3.0, 0.0, -4.0]])
    assert placed(ahead, basis, origin)[0, 2] < -4.0


def main():
    tests = [value for name, value in globals().items() if name.startswith("test_")]
    for test in tests:
        test()
    print(f"{len(tests)} checks passed")


if __name__ == "__main__":
    main()
