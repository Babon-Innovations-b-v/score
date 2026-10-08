"""Check the plan views (planview.py) look the way depth_pano.gd's cameras do, on a panorama whose
every pixel holds its own direction (pano.py's frame): a view cut from it must hold its own rays.

The checks need numpy, which only the prop environment has. Run by the gate with the system
python, this hands itself to the prop environment when the box has one, and says it skipped when
it does not. Run: python3 tools/props/scene/planview_test.py
"""
import os
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
PROPS_PYTHON = pathlib.Path(os.environ.get("PROPS_PYTHON", pathlib.Path.home() / ".farm-factory-props/env/bin/python"))

try:
    import numpy as np
except ImportError:
    if PROPS_PYTHON.exists() and os.environ.get("PLANVIEW_TEST_HANDED") != "1":
        os.environ["PLANVIEW_TEST_HANDED"] = "1"
        os.execv(str(PROPS_PYTHON), [str(PROPS_PYTHON), __file__])
    print("skipped: no prop environment on this box")
    sys.exit(0)

sys.path.insert(0, str(HERE))
from pano import directions  # noqa: E402
from planview import WAYS, cut_view, rays, vertical_fov  # noqa: E402


def middle_ray(way):
    """The direction through the middle of a small level view turned `way`."""
    return rays(WAYS[way], 90.0, 64, 36)[18, 32]


def test_the_ways_look_where_depth_pano_turns_its_cameras():
    assert np.allclose(middle_ray("north"), [0, 0, -1], atol=0.03)
    assert np.allclose(middle_ray("east"), [1, 0, 0], atol=0.03)
    assert np.allclose(middle_ray("south"), [0, 0, 1], atol=0.03)
    assert np.allclose(middle_ray("west"), [-1, 0, 0], atol=0.03)
    assert np.allclose(middle_ray("northeast"), [0.7071, 0, -0.7071], atol=0.03)


def test_a_view_cut_from_a_panorama_of_directions_holds_its_own_rays():
    pano = directions(512)
    for way in ("north", "southeast", "west"):
        view = cut_view(pano, WAYS[way], 90.0, 64, 36)
        view /= np.linalg.norm(view, axis=-1, keepdims=True)
        assert np.abs(view - rays(WAYS[way], 90.0, 64, 36)).max() < 0.02, way


def test_a_wide_view_keeps_ninety_degrees_across():
    assert abs(vertical_fov(90.0, 2048, 1152) - 58.7155) < 0.01
    left, right = rays(0.0, 90.0, 2048, 1152)[576, [0, -1]]
    assert abs(np.degrees(np.arccos(left @ right)) - 90.0) < 0.2


def main():
    tests = [value for name, value in globals().items() if name.startswith("test_")]
    for test in tests:
        test()
    print(f"{len(tests)} checks passed")


if __name__ == "__main__":
    main()
