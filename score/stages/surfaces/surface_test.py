"""Check the g-texture method's own steps (multiview.py, measure.py, paint.py): a turntable camera lands the model where
it should; the part measures count finishes owned, pure area and parts mixing two finishes right; a finish's exemplar
box, core and main hue; within a class texture and gloss tell finishes apart; the texture decides the whole-model
reference; and one surface's neighbours join only where their colours agree.

It needs numpy, scipy, PIL and trimesh, which only the prop environment has. Run by the gate with the system python,
this hands itself to the prop environment when the box has one, and says it skipped when it does not.
Run: python3 score/stages/surfaces/surface_test.py
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
    if PROPS_PYTHON.exists() and os.environ.get("SURFACE_TEST_HANDED") != "1":
        os.environ["SURFACE_TEST_HANDED"] = "1"
        os.execv(str(PROPS_PYTHON), [str(PROPS_PYTHON), __file__])
    print("skipped: no prop environment on this box")
    sys.exit(0)

sys.path.insert(0, str(HERE))
import measure  # noqa: E402
import multiview  # noqa: E402
import paint  # noqa: E402


def test_a_turntable_camera_lands_the_middle_on_the_centre_and_right_on_the_right():
    tile = trimesh.Trimesh(vertices=[[-0.1, -0.1, 0.0], [0.1, -0.1, 0.0], [0.0, 0.1, 0.0], [0.4, 0.0, 0.0],
                                     [0.6, 0.0, 0.0], [0.5, 0.2, 0.0]], faces=[[0, 1, 2], [3, 4, 5]], process=False)
    camera = {"position": [0.0, 0.0, -2.0], "target": [0.0, 0.0, 0.0], "up": [0.0, 1.0, 0.0], "fov_x": np.pi / 2,
              "width": 100, "height": 100}
    row, column, depth = multiview.projected(tile, camera)
    assert abs(row[0] - 49) <= 1 and abs(column[0] - 50) <= 1 and np.allclose(depth, 2.0)
    # looking down +z with y up, +x is on the camera's left: x 0.5 at depth 2 lands 0.25 of the half-width left
    assert column[1] < column[0] and abs(column[1] - (50 - 12.5)) <= 1


def test_whole_finishes_number_each_surface_and_leave_unseen_faces_out():
    names = np.array(["steel", None, "vinyl", "steel"], dtype=object)
    assert measure.whole_finishes(names).tolist() == [0, -1, 1, 0]


def test_part_measures_count_owned_pure_and_mixing():
    areas = np.ones(10)
    finish = np.array([0, 0, 0, 0, 1, 1, 1, 1, 1, 1])
    part_of = np.array([0, 0, 0, 0, 1, 1, 1, 1, 1, 1])
    clean = measure.part_measures(areas, finish, part_of)
    assert clean["owned"] == 2 and clean["finishes"] == 2 and clean["pure"] == 1.0 and clean["mixing"] == 0
    mixed = measure.part_measures(areas, finish, np.zeros(10, dtype=int))  # one part over both finishes
    # 60% of one finish is under OWN_PURITY: neither is owned
    assert mixed["owned"] == 0 and mixed["mixing"] == 1 and mixed["pure"] == 0.0


def test_exemplar_box_is_the_largest_patch_or_none():
    mask = np.zeros((100, 100), dtype=bool)
    mask[10:30, 40:70] = True
    mask[80:83, 5:8] = True  # a speck
    assert multiview.exemplar_box(mask, 5000) == [40, 10, 70, 30]
    assert multiview.exemplar_box(mask[75:, :10], 100000) is None  # under BOX_LEAST of the object


def test_colour_merge_keeps_one_surface_of_two_colours_apart():
    strip = trimesh.creation.box(extents=(1.0, 1.0, 1.0))
    part_of = np.zeros(len(strip.faces), dtype=int)
    part_of[:2] = 1
    chosen = np.array([0, 0])  # both parts named one surface
    colours = np.full((len(strip.faces), 3), 50.0)
    saved = measure.labels.SEEN_LEAST
    measure.labels.SEEN_LEAST = 1
    try:
        assert len(np.unique(paint.colour_joined_parts(strip, part_of, chosen, colours))) == 1
        colours[:2] = [50.0, 40.0, 0.0]  # part 1 is red where part 0 is grey
        assert len(np.unique(paint.colour_joined_parts(strip, part_of, chosen, colours))) == 2
    finally:
        measure.labels.SEEN_LEAST = saved


def grid(side):
    """A flat square of side x side cells, two triangles each (cell (row, column) holds faces 2 * (row * side +
    column) and the next), and each face's column."""
    rows, columns = np.mgrid[:side + 1, :side + 1]
    vertices = np.column_stack([columns.ravel(), rows.ravel(), np.zeros(rows.size)]).astype(float)
    corner = (np.arange(side)[:, None] * (side + 1) + np.arange(side)[None, :]).ravel()
    faces = np.concatenate([np.column_stack([corner, corner + 1, corner + side + 2]),
                            np.column_stack([corner, corner + side + 2, corner + side + 1])], axis=1).reshape(-1, 3)
    mesh = trimesh.Trimesh(vertices, faces, process=False)
    return mesh, np.repeat(np.tile(np.arange(side), side), 2)


def test_a_region_s_core_leaves_its_border_out():
    mesh, column = grid(8)
    left = column < 4
    core = multiview.core_faces(mesh, left, 2)
    assert core.sum() < left.sum() and not (core & (column == 3)).any() and core[column == 1].all()


def test_the_main_hue_drops_the_neighbour_s_foil_and_keeps_one_paint_whole():
    silver, gold = [70.0, 0.0, 2.0], [60.0, 6.0, 22.0]
    mixed = np.array([silver] * 70 + [gold] * 30) + np.random.default_rng(0).normal(0, 0.5, (100, 3))
    kept = multiview.main_hue(mixed)
    assert kept[:70].all() and not kept[70:].any()
    one = np.array([silver] * 100) + np.random.default_rng(1).normal(0, 1.0, (100, 3))
    assert multiview.main_hue(one).all()


def test_within_a_class_a_fleck_takes_its_neighbours_finish_and_gloss_tells_one_colour_apart():
    mesh, column = grid(12)
    finish = np.zeros(len(mesh.faces), dtype=int)  # SAM 3 called it all one finish of the class
    seeds = np.where(column < 3, 0, np.where(column >= 9, 1, -1))
    silver, gold = np.array([70.0, 0.0, 2.0]), np.array([60.0, 6.0, 22.0])
    features = np.tile(np.r_[silver, 0.1, 0.6, -2.0], (len(finish), 1))
    features[column >= 6, :3] = gold
    features[seeds == 1, :3] = gold
    fleck = np.nonzero(column == 2)[0][10]
    features[fleck, :3] = gold  # one gold face inside the silver seed region
    found = multiview.within_class(mesh, finish, features, seeds, np.zeros(2, dtype=int), 2)
    assert (found[column < 6] == 0).all() and (found[column >= 6] == 1).all(), found.reshape(12, 24)
    shiny = np.tile(np.r_[silver, 0.07, 0.75, -2.3], (len(finish), 1))  # vinyl and steel of one colour
    shiny[column >= 6, 3:5] = [0.99, 0.58]
    shiny[seeds == 1, 3:5] = [0.99, 0.58]
    found = multiview.within_class(mesh, finish, shiny, seeds, np.zeros(2, dtype=int), 2)
    assert (found[column < 6] == 0).all() and (found[column >= 6] == 1).all()


def test_the_texture_decides_the_whole_reference():
    """Two names for one texture become one finish; a face named one thing whose texture is another's moves."""
    strip = trimesh.creation.box(extents=(4.0, 1.0, 1.0)).subdivide().subdivide()
    count = len(strip.faces)
    rng = np.random.default_rng(0)
    left = strip.triangles_center[:, 0] < 0
    grey = np.column_stack([np.full(count, 45.0), np.zeros(count), np.full(count, 5.0), np.full(count, 0.1),
                            np.full(count, 0.9)])
    gold = grey.copy()
    gold[:, 0], gold[:, 2], gold[:, 3], gold[:, 4] = 65.0, 40.0, 0.99, 0.6
    features = np.where(left[:, None], grey, gold) + rng.normal(0.0, 0.3, (count, 5)) * [1, 1, 1, 0.01, 0.01]
    named = np.where(left, np.where(strip.triangles_center[:, 1] < 0, "dark", "galvanized"), "foil").astype(object)
    named[~left & (strip.triangles_center[:, 0] > 1.5)] = "galvanized"  # the judge's word on gold texture
    found, record = measure.texture_reference(strip, named, features)
    assert set(record["groups"].values()) == {"galvanized", "foil"} or set(record["groups"].values()) == {"dark",
                                                                                                       "foil"}
    assert (found[~left] == "foil").all() and len(set(found[left].tolist())) == 1, record
    assert measure.separation((np.zeros(2), np.ones(2)), (np.full(2, 3.0), np.ones(2))) > measure.SEPARABLE


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
    print("surface_test: ok")
