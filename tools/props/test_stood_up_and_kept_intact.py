"""A finished model file edited on its own bytes (glb_file.py) is stood up the way its shape says, and keeps everything
else: its shape, its normals turned with it, its kept triangles' corners and UVs, its maps padded from the nearest
piece and shrunk only as far as each map's role allows.

Every case is a shape whose right answer is plain (a crate 0.6 tall stands 0.6 tall; a 7 degree lean is taken out; a
20 degree one is not trusted), built here as points, normals or a one-square model file.

Breaks that turn each test red (each applied once and seen red, 2026-10-26):
- test_a_leaning_building_is_stood_straight: level_turn's wall `up = np.linalg.eigh(spread)[1][:, 0]` made `[:, 2]`.
- test_a_tilted_pad_is_laid_level: level_turn's flat branch `if floor_share >= FLOOR_SHARE and ...` made `if False:`.
- test_a_steep_lean_is_not_trusted: level_turn's `> most:` made `> 90:`.
- test_a_tilted_crate_stands_back_up: upright_turn's default `sides[np.argmax(np.abs(sides[:, 1]))]` made `sides[0]`.
- test_a_tall_rocket_stands_on_its_long_side: upright_turn's `sides[0] if long` made `sides[2] if long`.
- test_a_flat_take_is_laid_on_its_face: upright_turn's `sides[2] if flat` made `sides[1] if flat`.
- test_a_sheet_square_to_the_picture_is_laid_its_picture_side_up: upright_turn's `up = -np.sign(side[2]) if flat
  else np.sign(side[1])` made `up = np.sign(side[1])` and `(up or 1.0)` made `up` (the code before f47fd1ca: a zero
  pick and a NaN turn, 2026-10-26), and, apart, `-np.sign(side[2])` made `np.sign(side[2])` (laid picture side down).
- test_a_model_on_legs_is_levelled_on_its_feet: upright_turn's `if feet:` made `if False:`.
- test_a_long_model_faces_along_an_axis: upright_turn's `return squared(points @ turn.T) @ turn` made `return turn`.
- test_a_square_sheet_lines_its_edges_up_with_the_axes: squared's `if max(sides) >= SQUARE_ASPECT * min(sides):` made
  `if True:` (the long-side way only, as before 2026-10-26: the sheet stays about 45 degrees off).
- test_a_long_plank_lies_along_z: squared's `>= SQUARE_ASPECT * min(sides)` made `>= 1e9 * min(sides)` (the tightest
  rectangle's way only: a plank 60 degrees off is squared the short way, its long side along X).
- test_a_round_footprint_is_left_as_it_is: squared's `angle = 0.0` made `pass`.
- test_a_rocket_section_stands_on_its_own_axis: upright_turn's `if tube:` made `if False:`.
- test_the_file_keeps_its_shape_and_turns_its_normals: turned's `("POSITION", "NORMAL", "TANGENT")` made
  `("POSITION", "TANGENT")`.
- test_cutting_a_triangle_keeps_the_rest_as_it_was: without_triangles' `[~np.asarray(dropped)]` made
  `[np.asarray(dropped)]`.
- test_padding_fills_the_black_from_the_nearest_piece: padded's `[rows, columns]` lookup made the picture as it is
  (`pixels = np.asarray(picture.convert("RGB"))`).
- test_shrinking_halves_every_map_but_the_base_colour: shrunk's `wanted = side if number in base_images else ...`
  made `wanted = side`.
"""
import io
import pathlib
import sys

import numpy as np
from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import glb_file  # noqa: E402


def tilted(points, degrees, axis=(1.0, 0.0, 0.0)):
    """The points turned `degrees` about `axis`, the way a picture's camera leaves a model."""
    axis = np.array(axis) / np.linalg.norm(axis)
    angle = np.radians(degrees)
    skew = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    turn = np.eye(3) + np.sin(angle) * skew + (1 - np.cos(angle)) * skew @ skew
    return points @ turn.T


def box(width, height, depth, count=4000, seed=0):
    """Points filling a box standing on the ground, centred over the origin."""
    return (np.random.default_rng(seed).random((count, 3)) - [0.5, 0.0, 0.5]) * [width, height, depth]


def square_picture(size, left_colour):
    """A PNG `size` texels a side, `left_colour` on its left half and black elsewhere, as a bake leaves it."""
    pixels = np.zeros((size, size, 3), dtype=np.uint8)
    pixels[:, : size // 2] = left_colour
    picture = io.BytesIO()
    Image.fromarray(pixels).save(picture, "PNG")
    return picture.getvalue()


def one_quad_file(size=16):
    """A model file holding one square facing up, whose UVs cover the left half of a picture that is red there and
    black elsewhere."""
    positions = np.array([[0, 0, 0], [1, 0, 0], [1, 0, 1], [0, 0, 1]], dtype=np.float32)
    normals = np.tile(np.array([0, 1, 0], dtype=np.float32), (4, 1))
    uv = np.array([[0, 0], [0.5, 0], [0.5, 1], [0, 1]], dtype=np.float32)
    indices = np.array([0, 1, 2, 0, 2, 3], dtype=np.uint16)
    picture = square_picture(size, [200, 30, 30])
    views = [positions.tobytes(), normals.tobytes(), uv.tobytes(), indices.tobytes(), picture]
    document = {
        "asset": {"version": "2.0"},
        "meshes": [{"primitives": [{"attributes": {"POSITION": 0, "NORMAL": 1, "TEXCOORD_0": 2}, "indices": 3}]}],
        "accessors": [
            {"bufferView": 0, "componentType": 5126, "type": "VEC3", "count": 4,
             "min": positions.min(0).tolist(), "max": positions.max(0).tolist()},
            {"bufferView": 1, "componentType": 5126, "type": "VEC3", "count": 4},
            {"bufferView": 2, "componentType": 5126, "type": "VEC2", "count": 4},
            {"bufferView": 3, "componentType": 5123, "type": "SCALAR", "count": 6},
        ],
        "bufferViews": [{"buffer": 0, "byteLength": len(view)} for view in views],
        "images": [{"bufferView": 4, "mimeType": "image/png"}],
    }
    return document, views


def written_and_read(document, views, folder):
    path = folder / "quad.glb"
    glb_file.write(document, views, path)
    return glb_file.read(path)


def box_faces(tilt_degrees):
    """The normals and areas of a 2 x 3 x 2 box's six sides, leaning `tilt_degrees` about x."""
    normals = np.array([[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1]], float)
    areas = np.array([6.0, 6.0, 4.0, 4.0, 6.0, 6.0])
    return tilted(normals, tilt_degrees), areas


def test_a_leaning_building_is_stood_straight():
    normals, areas = box_faces(7.0)
    stood = normals @ glb_file.level_turn(normals, areas).T
    worst = np.degrees(np.arccos(np.clip(np.abs(stood[:, 1]).max(), -1, 1)))
    assert worst < 0.01, f"a side still leans {worst:.2f} degrees off vertical or level"


def test_a_tilted_pad_is_laid_level():
    normals = tilted(np.array([[0, 1, 0], [0, -1, 0], [1, 0, 0], [0, 0, 1]], float), 8.0)
    areas = np.array([100.0, 100.0, 1.0, 1.0])
    top = (normals @ glb_file.level_turn(normals, areas).T)[0]
    assert top[1] > 0.9999, top


def test_a_steep_lean_is_not_trusted():
    """20 degrees: its sides still read as walls (sin 20 = 0.34, under WALL_SLOPE), so a lean is found, and it is past
    the 15 degrees a generated model's crookedness is trusted to."""
    normals, areas = box_faces(20.0)
    assert np.allclose(glb_file.level_turn(normals, areas), np.eye(3))


def test_a_tilted_crate_stands_back_up():
    points = tilted(box(1.0, 0.6, 0.8), 35)
    height = np.ptp(points @ glb_file.upright_turn(points).T, axis=0)[1]
    assert abs(height - 0.6) < 0.03, height


def test_a_tall_rocket_stands_on_its_long_side():
    points = tilted(box(0.5, 2.0, 0.5), 50, (1.0, 0.0, 1.0))
    height = np.ptp(points @ glb_file.upright_turn(points, long=True).T, axis=0)[1]
    assert abs(height - 2.0) < 0.1, height


def test_a_flat_take_is_laid_on_its_face():
    """A rug drawn from straight above comes out standing in the picture's plane; `flat` lays it, its thin side up."""
    points = tilted(box(2.0, 3.0, 0.02), 10)
    height = np.ptp(points @ glb_file.upright_turn(points, flat=True).T, axis=0)[1]
    assert abs(height - 0.02) < 0.01, height


def test_a_sheet_square_to_the_picture_is_laid_its_picture_side_up():
    """A sheet whose faces are exact planes square to Z (the finish's remesh of a rug standing in the picture's plane)
    is laid, the face toward the picture's camera (-Z) on top; its side had no up at all (2026-10-26)."""
    points = box(0.13, 0.28, 0.002)
    points[:, 2] = np.where(points[:, 2] < 0, -0.001, 0.001)
    points[:, 2][:4] = -0.001  # its picture face, marked
    turned = points @ glb_file.upright_turn(points, flat=True).T
    assert np.isfinite(turned).all(), "a sheet square to the picture was given no turn"
    assert abs(np.ptp(turned, axis=0)[1] - 0.002) < 0.001
    assert turned[0, 1] > turned[:, 1].mean(), "laid picture side down"


def test_a_model_on_legs_is_levelled_on_its_feet():
    """Four thin legs under a tall body leaning 25 degrees over them: the body's box would stand it on the lean, the
    feet decide level."""
    rng = np.random.default_rng(1)
    body = tilted(box(1.0, 2.5, 1.0, 3000), 25, (0.0, 0.0, 1.0)) + [0.0, 0.4, 0.0]
    corners = [(x, z) for x in (-0.8, 0.8) for z in (-0.8, 0.8)]
    feet = [rng.normal([x, 0.0, z], 0.005, (200, 3)) for x, z in corners]
    points = tilted(np.vstack([body, *feet]), 20)
    turn = glb_file.upright_turn(points, feet=True)
    heights = [float((tilted(foot, 20) @ turn.T)[:, 1].mean()) for foot in feet]
    assert max(heights) - min(heights) < 0.02, heights


def test_a_long_model_faces_along_an_axis():
    points = tilted(box(0.4, 0.3, 2.0), 40, (0.0, 1.0, 0.0))
    extents = np.ptp(points @ glb_file.upright_turn(points).T, axis=0)
    assert extents[2] > 1.9, extents


def test_a_square_sheet_lines_its_edges_up_with_the_axes():
    """An 8 cm square note lying flat, turned 45 degrees about up: squared, it spans 8 cm along X and Z (11.3 cm turned)."""
    points = tilted(box(0.08, 0.001, 0.08), 45, (0.0, 1.0, 0.0))
    extents = np.ptp(points @ glb_file.upright_turn(points, flat=True).T, axis=0)
    assert np.allclose(extents[[0, 2]], 0.08, atol=0.002), extents


def test_a_long_plank_lies_along_z():
    points = tilted(box(0.2, 0.05, 2.0), 60, (0.0, 1.0, 0.0))
    extents = np.ptp(points @ glb_file.squared(points).T, axis=0)
    assert extents[2] > 1.98 and extents[0] < 0.22, extents


def test_a_round_footprint_is_left_as_it_is():
    rng = np.random.default_rng(1)
    angle, radius = rng.random(4000) * 2 * np.pi, 0.5 * np.sqrt(rng.random(4000))
    points = np.c_[radius * np.cos(angle), rng.random(4000) * 0.4, radius * np.sin(angle)]
    assert np.allclose(glb_file.squared(points), np.eye(3))


def test_a_rocket_section_stands_on_its_own_axis():
    """A tube with fins at its foot and a box on its side, tilted: fins and box fool the other ways of standing it up,
    the tube's axis does not."""
    rng = np.random.default_rng(2)
    angle = rng.random(6000) * 2 * np.pi
    height = rng.random(6000) * 2.0
    tube = np.c_[0.3 * np.cos(angle), height, 0.3 * np.sin(angle)]
    fins = np.vstack([box(0.05, 0.5, 1.4, 800, seed) for seed in (3, 4)])
    fins[800:] = fins[800:, [2, 1, 0]]
    side_box = box(0.3, 0.4, 0.3, 600, 5) + [0.4, 1.2, 0.0]
    points = tilted(np.vstack([tube, fins, side_box]), 12, (1.0, 0.0, 0.5))
    turn = glb_file.upright_turn(points, long=True, tube=True)
    axis = glb_file.tube_axis(points @ turn.T)
    assert np.degrees(np.arccos(min(1.0, axis[1]))) < 1.5


def test_the_file_keeps_its_shape_and_turns_its_normals(tmp_path):
    document, views = one_quad_file()
    turn = glb_file.rotation_between(np.array([0.0, 1.0, 0.0]), np.array([1.0, 0.0, 0.0]))
    glb_file.turned(document, views, turn)
    document, views = written_and_read(document, views, tmp_path)
    assert np.allclose(glb_file.accessor_array(document, views, 1), [1, 0, 0], atol=1e-5)
    # up turned onto x: the square's corners, all at height 0, now all sit at x 0
    assert np.allclose(document["accessors"][0]["max"][0], 0.0, atol=1e-5)
    assert np.allclose(glb_file.accessor_array(document, views, 0)[:, 0], 0.0, atol=1e-5)


def test_cutting_a_triangle_keeps_the_rest_as_it_was(tmp_path):
    document, views = one_quad_file()
    glb_file.without_triangles(document, views, [False, True])
    document, views = written_and_read(document, views, tmp_path)
    order = glb_file.accessor_array(document, views, 3)
    assert np.allclose(glb_file.accessor_array(document, views, 0)[order], [[0, 0, 0], [1, 0, 0], [1, 0, 1]])
    assert np.allclose(glb_file.accessor_array(document, views, 2)[order], [[0, 0], [0.5, 0], [0.5, 1]])
    assert document["accessors"][0]["count"] == 3


def test_padding_fills_the_black_from_the_nearest_piece():
    document, views = one_quad_file()
    glb_file.padded(document, views)
    pixels = np.asarray(Image.open(io.BytesIO(views[4])).convert("RGB")).astype(int)
    assert pixels.sum(-1).min() > 150, "a texel is still near black after padding"


def test_shrinking_halves_every_map_but_the_base_colour():
    """A room of hundreds of pieces cannot carry 2K maps on each (the hub kit, 2026-10-06): the base colour is held to
    the side asked for, every other map to half of it."""
    document, views = one_quad_file(size=256)
    views.append(square_picture(256, [90, 90, 90]))
    document["images"].append({"bufferView": 5, "mimeType": "image/png"})
    document["materials"] = [{"pbrMetallicRoughness": {"baseColorTexture": {"index": 0},
                                                        "metallicRoughnessTexture": {"index": 1}}}]
    document["textures"] = [{"source": 0}, {"source": 1}]
    glb_file.shrunk(document, views, 128)
    sizes = [Image.open(io.BytesIO(views[image["bufferView"]])).size for image in document["images"]]
    assert sizes == [(128, 128), (64, 64)], sizes
