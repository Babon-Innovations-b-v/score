"""Check the material library's data (library.py, data/library/) and the sorter (sorter.py): plain python, no Blender.
Run: python3 tools/props/library/library_test.py
"""
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import library  # noqa: E402
import sorter  # noqa: E402

DETAIL_PARTS = ("label", "screw", "screen", "keypad")


def test_every_variant_resolves_to_a_known_recipe_in_token_colours():
    found = library.library_specs()
    recipes = library.theme_library()["recipes"]
    assert len(found) >= 60
    for name, spec in found.items():
        assert spec["recipe"] in recipes, name
        assert len(spec["colour"]) == 3 and all(0.0 <= value <= 1.0 for value in spec["colour"]), name
        assert all(setting in spec for setting in recipes[spec["recipe"]]), name


def test_every_picture_variant_has_its_picture_drawn():
    for name, spec in library.library_specs().items():
        if spec["recipe"] in ("screen", "printed"):
            assert pathlib.Path(spec["image"]).exists(), name


def test_a_variant_is_named_once_across_the_families():
    library_data = library.theme_library()
    names = [name for family in library_data["families"].values() for name in family["variants"]]
    assert len(names) == len(set(names)) == len(library.variants(library_data))


def test_the_hub_and_the_habitat_take_the_same_library_in_their_own_tokens():
    hub = library.resolved("hub")
    habitat = library.resolved("habitat")
    assert hub["painted_panel"]["recipe"] == habitat["painted_hull_panel"]["recipe"] == "painted_metal"
    assert hub["painted_panel"]["token"] == "hull-trim" and habitat["painted_hull_panel"]["token"] == "hull"
    assert habitat["orange_rib"]["library"] == "painted_panel" and habitat["orange_rib"]["token"] == "machine"


def test_a_code_piece_slot_finds_its_place_colour_by_library_name():
    assert library.by_library("habitat")["painted_panel"]["token"] == "hull"
    assert library.by_library("hub")["painted_panel"]["token"] == "hull-trim"
    assert library.by_library("hub")["quilted_white"]["token"] == "hull"


def test_the_wear_levels_rise_and_the_hub_is_worked():
    levels = library.theme_library()["wear_levels"]
    assert levels["new"] == 0.0 < levels["worked"] < levels["worn"] <= 1.0
    assert library.wear_of("hub")[0] == levels["worked"]


def test_a_token_colour_is_linear():
    assert library.linear("#ffffff") == [1.0, 1.0, 1.0] and library.linear("#000000") == [0.0, 0.0, 0.0]
    assert abs(library.linear("#808080")[0] - 0.2159) < 1e-3


def test_every_detail_names_a_known_part_and_a_library_variant():
    details = json.loads((library.REPO / "data/library/details.json").read_text())
    names = library.variants(library.theme_library())
    for kind, entry in details.items():
        if kind == "is":
            continue
        for detail in entry["details"]:
            assert detail["part"] in DETAIL_PARTS, kind
            assert detail.get("variant", "label_access") in names, kind
        assert all(screen["variant"] in names for screen in entry["screens"]), kind


def test_only_plain_plates_pipes_and_trims_go_to_code():
    assert sorter.route("hub_wall_upper_plain") == sorter.route("hub_pipe_straight") == "code"
    assert sorter.route("hub_wall_skirting") == sorter.route("hub_lattice_hip_rib") == "code"
    # Thin, open or small is no reason for code (the owner, 2026-10-07): a toolboard's box is flat, a hinge small.
    for kind in ("hub_toolboard", "hub_talllocker", "hub_hatch_hinge", "hub_hatch_wheel", "hub_notice_board",
                 "hub_floor_grating", "hub_wall_lower_vent", "hub_pipe_valve"):
        assert sorter.route(kind) == "model", kind
    assert sorter.shape_class("hub_lattice_hip_rib", (0.12, 4.6, 0.12)) == "slender"
    assert sorter.shape_class("hub_porthole_panel", (1.2, 1.2, 0.1)) == "opening"


def test_every_code_builder_is_on_the_allow_list():
    """pieces.py builds only plain kinds: a builder for anything else is a piece made by hand from a sentence."""
    text = (HERE / "inside/pieces.py").read_text()
    names = re.findall(r'"(\w+)"', text[text.index("BUILDERS = "):text.index("def build(")])
    off = sorted(name for name in names if name not in sorter.PLAIN)
    assert not off, f"code builders for kinds that are not plain plates, pipes or trims: {', '.join(off)}"


def test_every_model_the_hub_lays_was_made_on_its_kind_s_route():
    """Every model the hub lays (kit and furniture) says the route it was made on, and that is its kind's route: code
    only for a plain kind, the prop pipeline for every other."""
    layout = json.loads((library.REPO / "data/kit/hub.json").read_text())
    kinds = {found["model"]: found["kind"] for found in layout["pieces"] if "part" not in found}
    kinds.update({name: f"hub_{name.rsplit('_', 1)[0]}" for name, about in layout["models"].items() if "prop" in about})
    off = sorted({f"{kind} ({layout['models'][name].get('route', 'no route recorded')})" for name, kind in kinds.items()
                  if layout["models"][name].get("route") != sorter.route(kind)})
    assert not off, f"models not made on their kind's route: {', '.join(off)}"


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
