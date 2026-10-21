"""The materials checks' measures on small meshes of known shape, and the kit bake code they hold a kit's bake to.
(Their fixtures of real evidence, data/checks/materials/<place>.json.gz from the old concepts' places, were retired
with those places on 2026-10-21; measure a place again with measure.gather when a rule needs a case.)

    finish borders   a straight border between two finishes measures 1.00, a 45 degree staircase 1.4
    texture detail   a metre square painted from a 512 picture holds 512 pixels a metre
    kit bake age     the bake code is the route and its bake, never the piece builders
"""
import numpy as np
from PIL import Image

from score.stages.complete.materials import borders, judge, kit_age, meshes, texel


def test_a_place_fails_on_any_finding_and_passes_with_none():
    assert judge.verdict([{"rule": borders.RULE}]) == "fail" and judge.verdict([]) == "pass"


def plane_mesh(border):
    """A flat 2 m square of 40 x 40 cells in the XZ plane, its cells left of `border(row)` (a column per row) one
    finish and the rest another."""
    cells = 40
    grid = np.array([(column * 0.05, 0.0, row * 0.05) for row in range(cells + 1) for column in range(cells + 1)])
    triangles, left = [], []
    for row in range(cells):
        for column in range(cells):
            corner = row * (cells + 1) + column
            triangles += [(corner, corner + 1, corner + cells + 1),
                          (corner + 1, corner + cells + 2, corner + cells + 1)]
            left += [column < border(row)] * 2
    left = np.array(left)
    return meshes.Drawn("plane", grid, np.array(triangles), None,
                        {"blue": np.nonzero(left)[0], "red": np.nonzero(~left)[0]}, {})


def test_a_straight_border_is_clean_and_a_staircase_is_ragged():
    straight = borders.measured_parts([plane_mesh(lambda row: 20)])
    stairs = borders.measured_parts([plane_mesh(lambda row: 5 + row // 2)])
    assert all(part["ragged"] == 1.0 for part in straight)
    assert all(part["ragged"] > 1.3 for part in stairs) and all(part["smooth_m"] > 1.5 for part in stairs)
    assert not borders.ragged_parts({"parts": straight}) and borders.ragged_parts({"parts": stairs})


def test_a_metre_square_painted_from_a_512_picture_holds_512_pixels_a_metre(tmp_path):
    picture = tmp_path / "base.png"
    Image.new("RGB", (512, 512), (90, 90, 90)).save(picture)
    points = np.array([(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 0.0, 1.0), (0.0, 0.0, 1.0)])
    triangles = np.array([(0, 1, 2), (0, 2, 3)])
    corners = np.array([[(0, 0), (1, 0), (1, 1)], [(0, 0), (1, 1), (0, 1)]], dtype=float)
    square = meshes.Drawn("square", points, triangles, corners, {}, {"": str(picture)})
    assert abs(texel.density([square]) - 512) < 1e-6
    assert abs(texel.density([square], area_scale=4.0) - 256) < 1e-6


def test_the_bake_code_is_the_route_and_its_bake_not_the_piece_builders():
    code = {path.name for path in kit_age.bake_files(kit_age.ROUTES["code"])}
    generated = {path.name for path in kit_age.bake_files(kit_age.ROUTES["generate"])}
    assert {"make_kit.py", "bake.py", "recipes.py"} <= code and "pieces.py" not in code
    assert {"make_chunky.py", "bake.py", "recipes.py"} <= generated and "shapes.py" not in generated


