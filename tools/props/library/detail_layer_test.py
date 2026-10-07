"""Check the picture's detail layer (inside/detail_layer.py) on a made-up piece whose answers are obvious.

It needs numpy, which only the prop environment has. Run by the gate with the system python, this hands itself to the
prop environment when the box has one, and says it skipped when it does not.
Run: python3 tools/props/library/detail_layer_test.py
"""
import os
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
PROPS_PYTHON = pathlib.Path(os.environ.get("PROPS_PYTHON", pathlib.Path.home() / ".farm-factory-props/env/bin/python"))

try:
    import numpy as np
except ImportError:
    if PROPS_PYTHON.exists() and os.environ.get("DETAIL_TEST_HANDED") != "1":
        os.environ["DETAIL_TEST_HANDED"] = "1"
        os.execv(str(PROPS_PYTHON), [str(PROPS_PYTHON), __file__])
    print("skipped: no prop environment on this box")
    sys.exit(0)

sys.path.insert(0, str(HERE / "inside"))
import detail_layer  # noqa: E402

SIDE = 64


def locker():
    """A grey steel front (left half, facing -y) and side (right half, facing +x, lit a fifth darker in the picture),
    a white label with black print and a rust streak on the front; the library paints it blue-grey."""
    picture = np.full((SIDE, SIDE, 3), 0.55)
    picture[:, SIDE // 2:] *= 0.8
    picture[10:20, 5:25] = 0.95
    picture[14:16, 8:22] = 0.05
    picture[40:44, 5:25] = (0.45, 0.25, 0.15)
    normals = np.zeros((SIDE, SIDE, 3))
    normals[:, :SIDE // 2, 1] = -1.0
    normals[:, SIDE // 2:, 0] = 1.0
    library_colour = np.full((SIDE, SIDE, 3), (0.4, 0.45, 0.5))
    return picture, normals, library_colour


def test_labels_and_rust_take_the_picture_and_plain_steel_keeps_the_library():
    picture, normals, library_colour = locker()
    covered = np.ones((SIDE, SIDE), dtype=bool)
    colour, rough, metal, share = detail_layer.laid(library_colour, np.full((SIDE, SIDE), 0.4), np.ones((SIDE, SIDE)),
                                                   picture, np.zeros((SIDE, SIDE), dtype=int), normals, covered)
    assert np.allclose(colour[12, 15], 0.95, atol=0.02) and np.allclose(colour[15, 15], 0.05, atol=0.05)
    assert np.allclose(colour[42, 15], (0.45, 0.25, 0.15), atol=0.02)
    assert rough[42, 15] >= detail_layer.DETAIL_ROUGHNESS and metal[42, 15] < 0.01
    # Plain steel on both faces, the darker-lit side too, keeps the library's colour and its metal.
    assert np.allclose(colour[30, 15], library_colour[30, 15], atol=0.01)
    assert np.allclose(colour[30, 50], library_colour[30, 50], atol=0.01) and metal[30, 50] == 1.0
    assert 0.05 < share < 0.2


def test_texels_off_the_piece_are_left_as_they_are():
    picture, normals, library_colour = locker()
    covered = np.zeros((SIDE, SIDE), dtype=bool)
    colour, _, _, share = detail_layer.laid(library_colour, np.zeros((SIDE, SIDE)), np.zeros((SIDE, SIDE)), picture,
                                            np.zeros((SIDE, SIDE), dtype=int), normals, covered)
    assert np.array_equal(colour, library_colour) and share == 0.0


def main():
    tests = [value for name, value in globals().items() if name.startswith("test_")]
    for test in tests:
        test()
    print(f"{len(tests)} checks passed")


if __name__ == "__main__":
    main()
