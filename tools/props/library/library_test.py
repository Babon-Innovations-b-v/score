"""Check the material library's data (library.py) and the sorter (sorter.py): plain python, no Blender.
Run: python3 tools/props/library/library_test.py
"""
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import library  # noqa: E402
import sorter  # noqa: E402

RECIPES = ("painted_metal", "bare_metal", "rubber", "glass", "glowing")


def test_every_library_material_names_a_recipe_a_token_and_every_setting():
    for name, spec in library.library_specs().items():
        assert spec["recipe"] in RECIPES, name
        assert len(spec["colour"]) == 3 and all(0.0 <= value <= 1.0 for value in spec["colour"]), name
        assert all(setting in spec for setting in library.SETTINGS), name


def test_the_hub_and_the_habitat_take_the_same_library_in_their_own_tokens():
    hub = library.resolved("hub")
    habitat = library.resolved("habitat")
    assert hub["painted_panel"]["recipe"] == habitat["painted_hull_panel"]["recipe"] == "painted_metal"
    assert hub["painted_panel"]["token"] == "hull-trim" and habitat["painted_hull_panel"]["token"] == "hull"
    assert habitat["orange_rib"]["library"] == "painted_panel" and habitat["orange_rib"]["token"] == "machine"


def test_a_code_piece_slot_finds_its_place_colour_by_library_name():
    assert library.by_library("habitat")["painted_panel"]["token"] == "hull"
    assert library.by_library("hub")["painted_panel"]["token"] == "hull-trim"
    assert library.by_library("hub")["glass"]["token"] == "glass"


def test_the_wear_levels_rise_and_the_hub_is_worked():
    levels = library.theme_library()["wear_levels"]
    assert levels["new"] == 0.0 < levels["worked"] < levels["worn"] <= 1.0
    assert library.wear_of("hub")[0] == levels["worked"]


def test_a_token_colour_is_linear():
    white, black = library.linear("#ffffff"), library.linear("#000000")
    assert white == [1.0, 1.0, 1.0] and black == [0.0, 0.0, 0.0]
    assert abs(library.linear("#808080")[0] - 0.2159) < 1e-3


def test_flat_slender_and_open_shapes_go_to_code_and_solids_to_the_model():
    assert sorter.route("hub_wall_upper_plain", (1.2, 2.0, 0.06)) == "code"
    assert sorter.shape_class("hub_lattice_hip_rib", (0.12, 4.6, 0.12)) == "slender"
    assert sorter.shape_class("hub_porthole_panel", (1.2, 1.2, 0.1)) == "opening"
    assert sorter.shape_class("hub_floor_grating", (1.0, 1.0, 0.05)) == "repeat"
    assert sorter.route("hub_pipe_valve", (0.3, 0.3, 0.2)) == "model"
    assert sorter.route("hub_hatch_hinge", (0.12, 0.4, 0.15)) == "code"
    assert sorter.route("hub_notice_board", (0.8, 0.6, 0.05)) == "decal"


def test_every_kind_of_the_hub_kit_gets_a_route():
    layout = json.loads((library.REPO / "data/kit/hub.json").read_text())
    found = sorter.sorted_kinds(layout)
    assert found and all(entry["route"] in ("code", "model", "decal") for entry in found.values())


def main():
    tests = [value for name, value in globals().items() if name.startswith("test_")]
    for test in tests:
        test()
    print(f"{len(tests)} checks passed")


if __name__ == "__main__":
    main()
