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
import stored  # noqa: E402

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
    assert library.by_library("habitat")["painted_panel"]["token"] == "hull-trim"  # its worn grey walls (style v2)
    assert library.by_library("hub")["painted_panel"]["token"] == "hull-trim"
    assert library.by_library("hub")["quilted_white"]["token"] == "hull"


def test_the_wear_levels_rise_and_the_hub_is_worked():
    levels = library.theme_library()["wear_levels"]
    assert levels["new"] == 0.0 < levels["worked"] < levels["worn"] <= 1.0
    assert library.wear_of("hub")[0] == levels["worked"]


def test_a_token_colour_is_linear():
    assert library.linear("#ffffff") == [1.0, 1.0, 1.0] and library.linear("#000000") == [0.0, 0.0, 0.0]
    assert abs(library.linear("#808080")[0] - 0.2159) < 1e-3


def test_every_generated_kind_has_a_turn_and_its_screens_and_cuts_are_sound():
    """details.json: a proper turn (a rotation), screens naming a library variant, cuts as boxes or circles."""
    details = json.loads((library.REPO / "data/library/details.json").read_text())
    names = library.variants(library.theme_library())
    for kind, entry in details.items():
        if kind == "is":
            continue
        turn = [entry["turn"][row * 3:row * 3 + 3] for row in range(3)]
        determinant = (turn[0][0] * (turn[1][1] * turn[2][2] - turn[1][2] * turn[2][1])
                       - turn[0][1] * (turn[1][0] * turn[2][2] - turn[1][2] * turn[2][0])
                       + turn[0][2] * (turn[1][0] * turn[2][1] - turn[1][1] * turn[2][0]))
        assert abs(determinant - 1.0) < 1e-3, kind
        assert all(screen["variant"] in names for screen in entry["screens"]), kind
        assert all(len(cut.get("box", cut.get("circle", []))) in (3, 4) for cut in entry["cuts"]), kind


def test_plain_pieces_go_to_code_and_objects_in_the_room_to_the_pipeline():
    assert sorter.route("hub_wall_upper_plain") == sorter.route("hub_pipe_straight") == "code"
    assert sorter.route("hub_wall_skirting") == sorter.route("hub_lattice_hip_rib") == "code"
    # A box's shape is no reason for code (the owner, 2026-10-07). Objects with no code build that shows their parts
    # (round six: a chair, a desk lamp, the hand tools) go through the pipeline; holders and plain manufactured
    # objects whose build shows every close-up part (a tool board, the lockers) are code.
    for kind in ("hub_chair", "hub_desklamp", "hub_telephone", "hub_microscope", "hub_wrench", "hub_pliers"):
        assert sorter.route(kind) == "model", kind
    for kind in ("hub_toolboard", "hub_talllocker", "hub_comms", "hub_console"):
        assert sorter.route(kind) == "code", kind
    assert sorter.shape_class("hub_lattice_hip_rib", (0.12, 4.6, 0.12)) == "slender"
    assert sorter.shape_class("hub_porthole_panel", (1.2, 1.2, 0.1)) == "opening"


def test_a_fitting_goes_to_code_only_when_its_build_shows_every_close_up_part():
    """Method B's rule (hub round five): a room fitting is built in code only when its last code build shows every
    part its close-up has, each seen at least SEEN_AT_LEAST from in front; a part buried in its plate (round three's
    vent slats, seen 0.0) or missing sends the fitting to the pipeline, and so does a fitting never built."""
    parts = ["slab", "slat", "vent_back"]
    shown = {"wall_lower_vent": {"parts": parts, "built": {"slab": 0.86, "slat": 1.0, "vent_back": 0.85}}}
    buried = {"wall_lower_vent": {"parts": parts, "built": {"slab": 0.33, "slat": 0.0, "vent_back": 0.0}}}
    missing = {"wall_lower_vent": {"parts": parts, "built": {"slab": 0.9, "slat": 1.0}}}
    unbuilt = {"wall_lower_vent": {"parts": parts}}
    assert sorter.route("hub_wall_lower_vent", shown) == "code"
    for found in (buried, missing, unbuilt):
        assert sorter.route("hub_wall_lower_vent", found) == "model"
    assert sorter.missing_parts(buried["wall_lower_vent"]) == ["slat", "vent_back"]
    # A print over a part (round six: a locker's label over its vent) fails the fitting too.
    over = {"wall_lower_vent": dict(shown["wall_lower_vent"], prints_off=["wall_lower_vent_1: label#52"])}
    assert sorter.route("hub_wall_lower_vent", over) == "model"
    # Only a fitting may pass: furniture listed by mistake still has no close-up parts to pass on.
    assert sorter.route("hub_toolboard", {}) == "model"


def test_no_generated_piece_keeps_its_picture_s_colours():
    """Method B: the pipeline gives shape only; a generated piece's job never carries its picture model, so no piece
    brings its own rust, stains or streaks (round four's picture layer). Read from route.py's text: this check runs
    with the system python, which has no numpy to import the route with."""
    text = (HERE / "route.py").read_text()
    jobs = text[text.index("def jobs("):text.index("def middle_high(")]
    assert '"picture"' not in jobs and "picture.obj" not in jobs


# Earth's builder modules beside pieces.py: the flat and stairwell, and the outdoor places (world 1).
EARTH_MODULES = ("earth_flat", "earth_stairwell", "pieces_earth")


def builder_texts():
    """pieces.py and Earth's rooms' builder modules beside it (the prologue build)."""
    return [(HERE / "inside/pieces.py").read_text()] + [(HERE / f"inside/{name}.py").read_text() for name in EARTH_MODULES]


def test_every_fitting_lists_its_close_up_and_parts_and_has_a_builder():
    text = "\n".join(builder_texts())
    for name, entry in sorter.fittings().items():
        assert entry["closeup"] and entry["parts"], name
        assert f"def {name}(size, laid):" in text, name


def test_every_code_builder_is_on_the_allow_list():
    """pieces.py builds only plain kinds and method B's room fittings: a builder for anything else is a piece made
    by hand from a sentence."""
    texts = builder_texts()
    names = re.findall(r'"(\w+)"', texts[0][texts[0].index("BUILDERS = "):texts[0].index("EARTH_ROOMS")])
    for text in texts[1:]:
        names += re.findall(r'"(\w+)"', text[text.index("BUILDERS = "):])
    off = sorted(name for name in names if name not in sorter.PLAIN and name not in sorter.fittings())
    assert not off, f"code builders for kinds that are not plain plates, pipes, trims or fittings: {', '.join(off)}"


def test_every_model_a_kit_room_lays_was_made_on_its_kind_s_route():
    """Every model a kit room lays (data/kit/<room>.json: kit and furniture) says the route it was made on, and that is
    its kind's route: code only for a plain kind, the prop pipeline for every other."""
    for path in sorted((library.REPO / "data/kit").glob("*.json")):
        layout = json.loads(path.read_text())
        kinds = {found["model"]: found["kind"] for found in layout["pieces"] if "part" not in found}
        kinds.update({name: f"{path.stem}_{name.rsplit('_', 1)[0]}" for name, about in layout["models"].items()
                      if "prop" in about})
        off = sorted({f"{kind} ({layout['models'][name].get('route', 'no route recorded')})"
                      for name, kind in kinds.items() if layout["models"][name].get("route") != sorter.route(kind)})
        assert not off, f"{path.stem}: models not made on their kind's route: {', '.join(off)}"


def test_every_kind_of_every_kit_room_gets_a_route():
    for path in sorted((library.REPO / "data/kit").glob("*.json")):
        layout = json.loads(path.read_text())
        found = sorter.sorted_kinds(layout)
        # A room of props alone (the expedition camp's grounds) lays no kit pieces; its props' routes are held above.
        props = any("prop" in about for about in layout["models"].values())
        assert (found or props) and all(entry["route"] in ("code", "model", "decal") for entry in found.values()), \
            path.stem


def test_a_room_s_baked_pictures_are_stored_as_webp_and_its_models_point_at_them():
    """stored.py: no baked PNG left in a kit room's models folder, every glTF picture a WebP through
    EXT_texture_webp (stored as PNG the hub's alone were 414 MB)."""
    for folder in sorted((library.REPO / "game/base/models").glob("*_kit")):
        assert not [path for path in (folder / "textures").glob("*.png") if stored.kind_of(path.name)], folder.name
        for gltf in folder.glob("*.gltf"):
            found = json.loads(gltf.read_text())
            for image in found.get("images", []):
                if stored.kind_of(image.get("uri", "")):
                    assert image["uri"].endswith(".webp") and image["mimeType"] == "image/webp", gltf.name
            assert all("source" not in texture for texture in found.get("textures", [])
                       if "EXT_texture_webp" in texture.get("extensions", {})), gltf.name


def test_a_gltf_is_pointed_at_its_webp_pictures():
    import tempfile
    with tempfile.TemporaryDirectory() as folder:
        gltf = pathlib.Path(folder) / "piece_1.gltf"
        gltf.write_text(json.dumps({"images": [{"uri": "textures/piece_1_normal.png", "mimeType": "image/png"},
                                               {"uri": "piece_1_screen.png"}],
                                    "textures": [{"sampler": 0, "source": 0}, {"sampler": 0, "source": 1}]}))
        assert stored.pointed_at_webp(gltf) == 1
        found = json.loads(gltf.read_text())
        assert found["images"][0] == {"uri": "textures/piece_1_normal.webp", "mimeType": "image/webp"}
        assert found["textures"][0] == {"sampler": 0, "extensions": {"EXT_texture_webp": {"source": 0}}}
        assert found["textures"][1] == {"sampler": 0, "source": 1}  # a screen's picture is not a baked map
        assert "EXT_texture_webp" in found["extensionsUsed"] and "EXT_texture_webp" in found["extensionsRequired"]


def test_a_room_past_its_budget_is_named():
    assert stored.over_budget({"disk_mb": 10.0, "card_mb": 10.0}) == []
    assert stored.over_budget({"disk_mb": stored.BUDGET["disk_mb"] + 1, "card_mb": 1.0})


def main():
    tests = [value for name, value in globals().items() if name.startswith("test_")]
    for test in tests:
        test()
    print(f"{len(tests)} checks passed")


if __name__ == "__main__":
    main()
