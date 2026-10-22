"""Check the people route's pieces on small made-up meshes: a region by its neighbours' majority, a web found by its
binds' jump and by the underarm rule, a cut closed by a fan that faces as its part, the weights kept to their limb,
the collar line filled round the neck, the neck tuck listed last, the old head's neck appended in plain skin, the
hair drawn over the scalp, the correctives' main shapes, and the stretch measure's longest edges.

Run: .venv/bin/python -m pytest tools/characters/maker/route_test.py   (PROPS_HOME is a temporary folder: nothing
here reads or writes the store)
"""
import pathlib
import sys

import numpy as np
import pytest

HERE = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / "people")]
import route_bind  # noqa: E402
import route_build  # noqa: E402
import route_head  # noqa: E402
import route_stretch  # noqa: E402

NAMES = ["Root", "Hips", "Chest", "Neck1", "LeftShoulder", "LeftArm", "LeftForeArm", "LeftHand"]
TRUNK = route_bind.REGIONS.index(route_bind.TRUNK)
ARM = route_bind.REGIONS.index("LeftArm")


@pytest.fixture(autouse=True)
def props_home(tmp_path, monkeypatch):
    monkeypatch.setenv("PROPS_HOME", str(tmp_path))


def facing(points, faces):
    corners = points[faces]
    return np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0])[:, 2]


def test_a_lone_point_takes_its_neighbours_region():
    _, faces = grid(5, 2)
    labels = np.full(10, TRUNK)
    labels[4] = ARM
    assert (route_bind.majority(labels, route_bind.edges_of(faces)) == TRUNK).all()


def test_an_edge_whose_binds_jump_is_web_and_a_touching_seam_is_not():
    points = np.array([[0.0, 0, 0], [0.01, 0, 0], [0.02, 0, 0]])
    edges = np.array([[0, 1], [1, 2]])
    regions = np.array([TRUNK, ARM, ARM])
    places = np.array([[0.0, 0, 0], [0.05, 0, 0], [0.06, 0, 0]])
    assert route_bind.web_edges(points, edges, regions, places).tolist() == [True, False]
    touching = np.array([[0.0, 0, 0], [0.01, 0, 0], [0.02, 0, 0]])
    assert not route_bind.web_edges(points, edges, regions, touching).any()


def test_the_underarm_and_the_crotch_are_cut_but_the_shoulder_top_is_not():
    points = np.array([[0.0, 1.20, 0], [0.01, 1.20, 0], [0.0, 1.40, 0], [0.01, 1.40, 0], [0.0, 0.6, 0],
                       [0.01, 0.6, 0]])
    regions = np.array([TRUNK, ARM, TRUNK, ARM, route_bind.REGIONS.index("LeftLeg"),
                        route_bind.REGIONS.index("RightLeg")])
    edges = np.array([[0, 1], [2, 3], [4, 5]])
    found = route_bind.underarm_edges(points, edges, regions, {ARM: 1.40})
    assert found.tolist() == [True, False, True]


def grid(columns, rows):
    """A grid of points in the z = 0 plane, x along columns, its triangles wound to face +z."""
    points = np.array([[column * 0.01, row * 0.01, 0.0] for column in range(columns) for row in range(rows)])
    faces = []
    for column in range(columns - 1):
        for row in range(rows - 1):
            low, high = column * rows + row, column * rows + row + 1
            faces += [[low, low + rows, high], [high, low + rows, high + rows]]
    return points, np.array(faces)


def test_a_cut_is_closed_on_each_side_by_its_own_fan():
    points, faces = grid(6, 3)
    labels = np.where(points[:, 0] < 0.025, TRUNK, ARM)
    middle = (points[faces, 0].min(1) > 0.015) & (points[faces, 0].max(1) < 0.035)
    closed, middles = route_bind.closed(faces, labels, middle, len(points))
    assert sorted(len(ends) for ends in middles) == [3, 3]
    assert {labels[ends[0]] for ends in middles} == {TRUNK, ARM}
    kept = closed[:len(faces) - middle.sum()]
    assert (facing(points, kept) > 0).all()
    fans = closed[len(kept):]
    assert len(fans) == 2 * 3 and ((fans == len(points)) | (fans == len(points) + 1)).any(axis=1).all()
    grown = route_bind.with_middles(points, middles)
    assert np.allclose(grown[len(points):, 0], [0.02, 0.03]) or np.allclose(grown[len(points):, 0], [0.03, 0.02])


def test_a_limb_point_keeps_only_its_chain_and_its_shoulder():
    weights = np.full((2, len(NAMES)), 1.0 / len(NAMES))
    kept = route_bind.kept_to_limb(weights, np.array([ARM, TRUNK]), NAMES)
    allowed = [NAMES.index(name) for name in ("LeftShoulder", "LeftArm", "LeftForeArm", "LeftHand")]
    assert np.allclose(kept[0].sum(), 1.0)
    assert np.allclose(np.delete(kept[0], allowed), 0.0)
    assert np.allclose(kept[1], weights[1])


def test_the_face_is_one_setting_and_keeps_the_made_face_by_default():
    """#26: until the owner decides, the body keeps the face Pixal3D made (its print from the close-up) and reads no
    old body; `drawn` drops the made face for the old drawn head, and refuses without the old body."""
    import argparse
    assert route_head.FACE == "made" and set(route_head.FACES) == {"made", "drawn"}
    document = {"materials": [{"name": "skin_head", "extras": {"role": "skin"}}, {"name": "hair", "extras": {"role": "hair"}},
                              {"name": "suit", "extras": {"role": route_build.pokes.GARMENT}}]}
    surfaces = [route_build.Surface(number, None, None, None, None) for number in range(3)]
    named = lambda face: [document["materials"][surface.material]["name"]  # noqa: E731
                          for surface in route_build.kept_surfaces(document, surfaces, face)]
    assert named("made") == ["skin_head", "hair"] and named("drawn") == ["hair"]
    with pytest.raises(SystemExit, match="--old"):
        route_build.drawn_head(argparse.Namespace(old=None), document, surfaces, None, None, [], None)


def test_the_collar_line_is_filled_round_the_neck():
    turns = np.linspace(-np.pi, np.pi, 8, endpoint=False) + 0.01
    border = np.stack([np.cos(turns) * 0.06, 1.45 + 0.01 * np.sin(turns), np.sin(turns) * 0.06], 1)
    line = route_head.collar_line(border, np.zeros(3), 1.5)
    assert len(line) == route_head.DIRECTIONS
    assert not np.isnan(line).any()
    assert line.min() >= 1.44 - 1e-9 and line.max() <= 1.46 + 1e-9


def test_points_under_the_collar_are_listed_last():
    points = np.array([[0.05, 1.50, 0.0], [0.05, 1.40, 0.0], [0.05, 1.55, 0.0]])
    order, tuck_from = route_head.tuck_order(points, np.full(route_head.DIRECTIONS, 1.45), np.zeros(3))
    assert order.tolist() == [0, 2, 1] and tuck_from == 2
    renumbered = route_head.reordered(order, np.array([[0, 1, 2]]))
    assert renumbered.tolist() == [[0, 2, 1]]


def test_the_neck_is_appended_under_the_old_head():
    old_points = np.array([[0.0, 1.5, 0.0], [0.01, 1.5, 0.0], [0.02, 1.5, 0.0], [0.01, 1.52, 0.0]])
    old_faces = np.array([[0, 1, 3], [1, 2, 3]])
    old_uv = np.array([[0.1, 0.1], [0.2, 0.2], [0.9, 0.9], [0.5, 0.5]])
    piece_points = np.r_[old_points, [[0.012, 1.45, 0.0]]]
    piece_faces = np.array([[0, 1, 3], [1, 2, 3], [4, 1, 0]])
    neck = route_head.Extension(piece_points, piece_faces, np.eye(5), old_points, old_faces, old_uv, np.eye(5)[:4])
    assert neck.found == 4 and len(neck.points) == 3
    assert neck.faces.tolist() == [[4, 5, 6]]
    assert np.allclose(neck.points, piece_points[[4, 1, 0]])
    assert neck.uv.tolist() == [[0.2, 0.2]] * 3


def test_the_lowest_band_of_the_drawing_is_painted_skin():
    picture = np.full((20, 20, 3), (200, 150, 120), np.uint8)
    picture[2:4, :] = 0
    points = np.array([[0.0, 1.50, 0.0], [0.01, 1.50, 0.0], [0.0, 1.51, 0.0], [0.0, 1.60, 0.0], [0.01, 1.60, 0.0]])
    faces = np.array([[0, 1, 2], [2, 3, 4]])
    uv = np.array([[0.0, 0.0], [0.5, 0.0], [0.0, 0.25], [0.6, 0.6], [0.9, 0.9]])
    painted = route_head.painted_neck(picture, points, faces, uv)
    assert (painted[2:4, :4] == (200, 150, 120)).all()
    assert (painted[2:4, 15:] == 0).all()


def test_the_scalp_is_drawn_under_the_hair():
    import trimesh
    hair = trimesh.creation.icosphere(subdivisions=2, radius=0.1)
    points = np.array([[0.0, 0.12, 0.0], [0.0, 0.05, 0.0]])
    moved, count = route_head.under_hair(points, hair.vertices, hair.faces, np.zeros(3), np.array([True, True]))
    assert count == 1
    assert np.linalg.norm(moved[0]) < 0.1 and np.allclose(moved[1], points[1])


def test_the_main_shapes_keep_offsets_made_of_few_directions():
    rng = np.random.default_rng(0)
    directions = rng.normal(size=(2, 30))
    stacked = (rng.normal(size=(40, 2)) @ directions).astype(np.float32)
    shapes, weights, kept = route_build.principal_shapes(stacked, 2)
    assert kept > 0.999
    assert np.allclose(weights @ shapes, stacked, atol=1e-4)


def test_the_longest_edge_of_each_triangle():
    points = np.array([[0.0, 0, 0], [3.0, 0, 0], [0.0, 4.0, 0]])
    assert route_stretch.longest_edges(points, np.array([[0, 1, 2]])).tolist() == [5.0]


def test_the_body_under_a_cut_web_is_drawn_inside_in_the_cut_garments_cloth():
    base_points, base_faces = grid(20, 3)
    base_weights = np.tile(np.eye(len(NAMES))[2], (len(base_points), 1))
    sleeve = route_build.Surface(7, np.full((2, 3), 5.0), None, None, np.zeros((0, 3), int))
    torso = route_build.Surface(3, np.full((3, 3), 5.0), None, None, np.zeros((0, 3), int))
    bound = route_bind.Bound(np.zeros((5, 3), int), np.tile([1.0, 0.0, 0.0], (5, 1)), base_points)
    welded = {"numbers": np.array([0, 1, 2, 3, 4]), "starts": [0, 2], "web": {(2, 3)}, "bound": bound}
    correctives = {"clip_walking": np.ones((4, len(base_points), 3), np.float32)}
    over = route_build.Surface(9, base_points + [0.0, 0.0, 0.01], None, None, base_faces)  # the cloth 1 cm out
    layer = route_build.under_layer([sleeve, torso, over], welded, base_points, base_faces, base_weights,
                                    correctives, ["walking"])
    assert layer.material == 3
    inside = int(np.sum(base_points[::3, 0] < route_build.UNDER_REACH))  # grid columns (1 cm apart) under the reach
    assert len(layer.faces) == (inside - 1) * 2 * 2
    assert np.allclose(layer.points[:, 2], -route_build.UNDER_INSET)
    assert layer.points[:, 0].max() <= route_build.UNDER_REACH + 1e-9
    assert layer.offsets["walking"].shape == (4, len(layer.points), 3)
    assert route_build.under_layer([sleeve, torso, over], {**welded, "web": set()}, base_points, base_faces,
                                   base_weights, correctives, ["walking"]) is None


def test_cloth_next_to_a_skin_part_rides_its_weights_and_takes_no_correctives():
    """2026-10-22: the astronaut's made face went 10 mm through the helmet bent with the neck, and the base's
    correctives moved the trouser hem riding the boot into the boot."""
    parents = np.array([-1, 0, 1, 2, 1, 4, 5, 6])  # NAMES: Root, Hips, Chest, Neck1, LeftShoulder, LeftArm, ...
    face = np.zeros((1, len(NAMES)))
    face[0, [2, 3]] = [0.2, 0.8]
    neck, arm = (np.eye(len(NAMES))[number] for number in (3, 5))
    places = np.array([[0.0, 0, 0.02], [0.0, 0, 0.5], [0.0, 0, 0.03]])
    target, share = route_build.skin_share(places, np.stack([neck, neck, arm]), (np.zeros((1, 3)), face), parents)
    assert share[:, 0].tolist() == [1.0, 0.0, 0.0]  # held; out of reach; on an arm, not the face's family
    assert np.allclose(target[0], face[0])
    bound = route_bind.Bound(np.zeros((3, 3), int), np.tile([1.0, 0.0, 0.0], (3, 1)), np.zeros((1, 3)))
    moves = route_build.clip_offsets({"clip_walking": np.ones((2, 1, 3), np.float32)}, ["walking"],
                                     {"bound": bound, "eased": share[:, 0]})["walking"]
    assert np.allclose(moves[:, 0], 0.0) and np.allclose(moves[:, 1:], 1.0)
    _, none = route_build.skin_share(places, np.stack([neck] * 3), (np.zeros((0, 3)), np.zeros((0, len(NAMES)))),
                                     parents)
    assert not none.any()


def test_the_body_under_a_cut_web_is_not_drawn_where_it_would_show_through_the_cloth():
    """2026-10-22: the base stood out of the astronaut's slim suit and its under layer showed as white patches."""
    base_points, base_faces = grid(20, 3)
    base_weights = np.tile(np.eye(len(NAMES))[2], (len(base_points), 1))
    torso = route_build.Surface(3, np.zeros((2, 3)), None, None, np.zeros((0, 3), int))
    bound = route_bind.Bound(np.zeros((2, 3), int), np.tile([1.0, 0.0, 0.0], (2, 1)), base_points)
    welded = {"numbers": np.array([0, 1]), "starts": [0], "web": {(0, 1)}, "bound": bound}
    tight = route_build.Surface(9, base_points - [0.0, 0.0, 0.002], None, None, base_faces)  # 2 mm inside the base
    assert route_build.under_layer([torso, tight], welded, base_points, base_faces, base_weights, None, []) is None


def test_the_route_reads_the_body_node_its_outfit_named():
    """2026-10-22: one body a look, its outfit `made`; the route looked for a node named `work` and found none."""
    document = {"nodes": [{"name": "Person"}, {"name": "far", "mesh": 0, "skin": 0},
                          {"name": "made", "mesh": 1, "skin": 0}]}
    assert route_build.body_node(document) == "made"
    with pytest.raises(SystemExit):
        route_build.body_node({"nodes": [{"name": "far", "mesh": 0, "skin": 0}]})
