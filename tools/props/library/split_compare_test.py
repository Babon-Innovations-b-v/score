"""Check the part splitter comparison (split_compare.py, job parts-test 2026-10-09): predicted voxel colours become
parts, voxel parts land on the right faces, and the three scores read a
split that follows the finishes as better than one that does not.

It needs numpy, scipy and trimesh, which only the prop environment has. Run by the gate with the system python, this
hands itself to the prop environment when the box has one, and says it skipped when it does not.
Run: python3 tools/props/library/split_compare_test.py
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
    if PROPS_PYTHON.exists() and os.environ.get("SPLIT_TEST_HANDED") != "1":
        os.environ["SPLIT_TEST_HANDED"] = "1"
        os.execv(str(PROPS_PYTHON), [str(PROPS_PYTHON), __file__])
    print("skipped: no prop environment on this box")
    sys.exit(0)

sys.path.insert(0, str(HERE))
import split_compare  # noqa: E402


def slab():
    """A flat slab, finely divided, its top half one finish and its bottom half another along x."""
    box = trimesh.creation.box(extents=(1.0, 0.1, 1.0))
    for _ in range(4):
        box = box.subdivide()
    finish = (box.triangles_center[:, 0] > 0).astype(int)
    return box, finish


def test_guide_palette_colours_are_far_apart():
    palette = split_compare.PALETTE[:40].astype(float)
    spacing = np.linalg.norm(palette[:, None] - palette[None], axis=2)
    spacing[spacing == 0] = np.inf
    assert spacing.min() > 60, spacing.min()


def test_predicted_colours_group_into_parts():
    rng = np.random.default_rng(1)
    centres = np.array([(200, 40, 40), (40, 200, 40)], dtype=float)
    truth = rng.integers(0, 2, 4000)
    found = split_compare.grouped_colours(np.clip(centres[truth] + rng.normal(0, 5, (4000, 3)), 0, 255))
    assert len(np.unique(found)) == 2 and abs(np.corrcoef(found, truth)[0, 1]) > 0.99


def test_voxel_parts_land_on_their_faces():
    mesh, finish = slab()
    centre, scale = (mesh.bounds[0] + mesh.bounds[1]) / 2, 0.99999 / float(np.ptp(mesh.bounds, axis=0).max())
    points = (mesh.sample(20000, seed=0) - centre) * scale
    coords = np.unique(np.floor((points + 0.5) * split_compare.GRID).astype(int), axis=0)
    voxel_part = ((coords[:, 0] + 0.5) / split_compare.GRID - 0.5 > 0).astype(int)
    found = split_compare.voxel_parts_on_faces(mesh, coords, voxel_part, centre, scale)
    assert (found == finish).mean() > 0.97


def test_a_split_along_the_finishes_owns_them_and_one_part_does_not():
    mesh, finish = slab()
    owned, missed = split_compare.finishes_owned(mesh.area_faces, finish, finish)
    assert owned == [0, 1] and not missed
    owned, missed = split_compare.finishes_owned(mesh.area_faces, finish, np.zeros(len(finish), dtype=int))
    assert missed == [0, 1]


def test_cutting_one_finish_in_two_on_a_smooth_face_is_needless():
    mesh, finish = slab()
    whole_finish = np.zeros(len(finish), dtype=int)
    wasted, cut = split_compare.needless_cuts(mesh, whole_finish, finish)
    assert wasted > 0.2 and cut >= 1
    wasted, cut = split_compare.needless_cuts(mesh, finish, finish)
    assert wasted == 0 and cut == 0


def test_region_agreement_prefers_the_split_that_follows_the_regions():
    pixels = np.repeat(np.array([[0, 0, 1, 1]]), 4, axis=0)
    region_finish = np.array([0, 1])
    following = split_compare.region_agreement(pixels.copy(), pixels, region_finish)
    one_part = split_compare.region_agreement(np.zeros_like(pixels), pixels, region_finish)
    assert following["agreement"] == 1.0 and one_part["pure"] == 0.5


def test_region_agreement_takes_a_region_the_drawn_split_misses():
    pixels = np.repeat(np.array([[0, 0, 1, 2]]), 4, axis=0)
    rendered = np.where(pixels == 2, -1, 0)  # the last region is never drawn (the hanging glove, 2026-10-10)
    found = split_compare.region_agreement(rendered, pixels, np.array([0, 0, 0]))
    assert found == {"whole": 1.0, "pure": 1.0, "agreement": 1.0}


if __name__ == "__main__":
    for name, test in sorted(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
