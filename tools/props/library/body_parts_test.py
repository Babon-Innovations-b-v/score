"""Check body_parts.py: a re-made take's faces take the nearest accepted face's surface in the kit frame, whatever
the two models' own scale, and a take far from the accepted one is refused.

Needs numpy, scipy and trimesh: run with the system python it hands itself to the prop environment, and says it
skipped on a box without one. Run: python3 tools/props/library/body_parts_test.py
"""
import os
import pathlib
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
PROPS_PYTHON = pathlib.Path(os.environ.get("PROPS_PYTHON", pathlib.Path.home() / ".farm-factory-props/env/bin/python"))
try:
    import numpy as np
    import trimesh
except ImportError:
    if PROPS_PYTHON.exists() and os.environ.get("BODY_PARTS_TEST_HANDED") != "1":
        os.environ["BODY_PARTS_TEST_HANDED"] = "1"
        os.execv(str(PROPS_PYTHON), [str(PROPS_PYTHON), __file__])
    print("skipped: no prop environment on this box")
    sys.exit(0)

sys.path.insert(0, str(HERE))
import body_parts  # noqa: E402

SIZE = [2.0, 1.0, 0.5]
IDENTITY = [1, 0, 0, 0, 1, 0, 0, 0, 1]


def two_toned_box(scale):
    """A box whose top half's faces are `top` and bottom half's `bottom`: (middles, names)."""
    box = trimesh.creation.box(extents=[1.0, 1.0, 1.0]).subdivide().subdivide()
    middles = box.triangles_center * np.asarray(scale)
    return middles, np.where(box.triangles_center[:, 1] > 0, "top", "bottom")


def test_a_re_made_take_takes_the_nearest_accepted_surface_at_any_scale():
    old_middles, old_names = two_toned_box([1.0, 1.0, 1.0])
    new_middles, truth = two_toned_box([0.3, 0.7, 0.2])  # another take's own scale: both are fitted to SIZE
    names, gap = body_parts.surfaces_from(new_middles, old_middles, old_names, IDENTITY, SIZE)
    assert (names == truth).mean() > 0.95, (names == truth).mean()
    assert gap < 0.01, gap


def test_laid_stands_on_its_foot_at_the_laid_size():
    points = body_parts.laid(np.array([[3.0, 5.0, 1.0], [7.0, 9.0, 2.0]]), IDENTITY, SIZE)
    assert np.allclose(points.max(0) - points.min(0), SIZE) and np.isclose(points[:, 1].min(), 0.0)
    assert np.isclose(points[:, 0].mean(), 0.0) and np.isclose(points[:, 2].mean(), 0.0)


def test_surfaces_are_written_one_file_each_and_old_files_go():
    mesh = trimesh.creation.box(extents=[1.0, 1.0, 1.0])
    names = np.where(mesh.triangles_center[:, 1] > 0, "top", "bottom")
    with tempfile.TemporaryDirectory() as folder:
        out = pathlib.Path(folder)
        (out / "stale.ply").write_text("left from an earlier take")
        shares = body_parts.write_surfaces(mesh, names, out)
        assert sorted(path.stem for path in out.glob("*.ply")) == ["bottom", "top"]
        assert np.isclose(sum(shares.values()), 1.0, atol=0.01)


def test_a_take_with_no_body_is_refused():
    try:
        body_parts.write("any-b1", "/nowhere", "no-such-take", SIZE, IDENTITY, "/tmp/never")
    except SystemExit as refusal:
        assert "no body" in str(refusal)
    else:
        raise AssertionError("a take with no body was labelled")


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
