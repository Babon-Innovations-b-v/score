"""Check the straightness check (straight.py): a square box passes, the same box sheared or bowed fails.

It needs numpy and trimesh, which only the prop environment has. Run by the gate with the system python, this hands
itself to the prop environment when the box has one, and says it skipped when it does not.
Run: python3 tools/props/library/straight_test.py
"""
import os
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
PROPS_PYTHON = pathlib.Path(os.environ.get("PROPS_PYTHON", pathlib.Path.home() / ".farm-factory-props/env/bin/python"))

try:
    import numpy as np
    import trimesh
except ImportError:
    if PROPS_PYTHON.exists() and os.environ.get("STRAIGHT_TEST_HANDED") != "1":
        os.environ["STRAIGHT_TEST_HANDED"] = "1"
        os.execv(str(PROPS_PYTHON), [str(PROPS_PYTHON), __file__])
    print("skipped: no prop environment on this box")
    sys.exit(0)

sys.path.insert(0, str(HERE))
import straight  # noqa: E402


def locker():
    """A tall locker's box, 1.2 x 2.0 x 0.55, finely divided so it can bend."""
    box = trimesh.creation.box(extents=(1.2, 2.0, 0.55))
    for _ in range(4):
        box = box.subdivide()
    return box


def test_a_square_box_passes():
    assert straight.straightness(locker())["pass"]


def test_a_box_leaning_over_fails():
    leaning = locker()
    leaning.vertices[:, 0] += leaning.vertices[:, 1] * 0.12  # 7 degrees over, as round four's locker leant
    found = straight.straightness(leaning)
    assert not found["pass"] and found["sides"]["right"]["tilt"] > straight.TILT_DEGREES


def test_a_bowed_front_fails():
    bowed = locker()
    front = bowed.vertices[:, 2] < -0.27
    bowed.vertices[front, 2] -= 0.1 * np.cos(bowed.vertices[front, 1] * np.pi / 2.0)
    assert not straight.straightness(bowed)["pass"]


def main():
    tests = [value for name, value in globals().items() if name.startswith("test_")]
    for test in tests:
        test()
    print(f"{len(tests)} checks passed")


if __name__ == "__main__":
    main()
