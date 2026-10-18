"""The materials checks on real evidence (data/checks/materials/<place>.json.gz, measured from the store on
2026-10-18) and their measures on small meshes of known shape.

Known bad and known good, a pair each:
    texture detail   hangar: the ship seen from 0.5 m at 56 px/m against the room's kit at 617 fails;
                     cockpit: its consoles and seat, seen from under a metre, at 475 to 1084 against 568 pass
    finish borders   hangar's ship (1.24 to 1.43) and the cockpit's pilot seat fail; the garage's wheel stand (1.02)
                     passes, as a straight border between two finishes measures 1.00 and a 45 degree staircase 1.4
    kit bake age     hangar: its kit baked by 2026-10-09 is older than five commits to the kit bake code; the
                     cockpit's kit, baked by 2026-10-15, against the bake code as it stood before b6808d0d (the one
                     later commit) passes
"""
import gzip
import json
import pathlib

import numpy as np
from PIL import Image

from score.stages.complete.materials import borders, judge, kit_age, meshes, texel

REPO = pathlib.Path(__file__).resolve().parents[4]
FIXTURES = REPO / "data/checks/materials"


def evidence(place):
    """A place's real evidence as measured."""
    with gzip.open(FIXTURES / f"{place}.json.gz", "rt") as found:
        return json.load(found)


def models_of(found, rule):
    return {item["model"] for item in found if item["rule"] == rule}


def test_the_ship_seen_close_at_a_tenth_of_the_kit_is_soft():
    found = texel.findings(evidence("hangar"))
    ship = next(item for item in found if item["model"] == "ship_1")
    assert ship["px_per_m"] < 60 and ship["kit_px_per_m"] > 600 and ship["near"] < 1.0
    assert "blurred" in ship["sentence"]


def test_the_cockpit_consoles_hold_the_kit_detail():
    found = texel.findings(evidence("cockpit"))
    assert found == []
    near = [entry for entry in evidence("cockpit")["objects"]
            if entry["model"] in ("main_console_1", "pilot_seat_1") and entry["near"] is not None]
    assert near and all(entry["near"] < 1.0 for entry in near)


def test_a_place_with_no_kit_is_held_to_the_worlds_kit():
    place = evidence("cockpit")
    without_kit = dict(place, objects=[entry for entry in place["objects"] if not texel.is_kit(entry)])
    assert texel.findings(without_kit) == []
    held = texel.findings(without_kit, world=5000.0)
    assert held and "the world's kit" in held[0]["sentence"]


def test_the_ship_and_the_pilot_seat_have_ragged_borders_the_wheel_stand_does_not():
    assert "ship_1" in models_of(borders.findings(evidence("hangar")), borders.RULE)
    assert "pilot_seat_1" in models_of(borders.findings(evidence("cockpit")), borders.RULE)
    garage = models_of(borders.findings(evidence("garage")), borders.RULE)
    assert "wheel_stand_1" not in garage and "workbench_1" in garage


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


def test_the_hangar_kit_is_older_than_its_bake_code():
    found = kit_age.findings(evidence("hangar"))
    assert [item["route"] for item in found] == ["code"]
    assert len(found[0]["models"]) == 66 and len(found[0]["commits"]) == 5


def test_the_cockpit_kit_was_fresh_before_the_one_later_bake_code_commit():
    cockpit = evidence("cockpit")
    assert kit_age.findings(cockpit)[0]["commits"] == ["b6808d0d"]
    before = {route: [commit for commit in commits if commit["commit"] != "b6808d0d"]
              for route, commits in cockpit["bake_code"].items()}
    assert kit_age.findings(dict(cockpit, bake_code=before)) == []


def test_the_bake_code_is_the_route_and_its_bake_not_the_piece_builders():
    code = {path.name for path in kit_age.bake_files(kit_age.ROUTES["code"])}
    generated = {path.name for path in kit_age.bake_files(kit_age.ROUTES["generate"])}
    assert {"make_kit.py", "bake.py", "recipes.py"} <= code and "pieces.py" not in code
    assert {"make_chunky.py", "bake.py", "recipes.py"} <= generated and "shapes.py" not in generated


def test_a_place_fails_on_any_finding_and_names_kit_pieces_with_no_bake_time():
    cockpit = evidence("cockpit")
    found = judge.findings(cockpit)
    assert judge.verdict(found) == "fail" and judge.verdict([]) == "pass"
    assert "not from the seed" in judge.reason(cockpit, found)
