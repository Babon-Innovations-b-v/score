"""Check the material library's data (library.py, data/library/) and the sorter (sorter.py): plain python, no Blender.
Run: python3 tools/props/library/library_test.py
"""
import ast
import contextlib
import io
import json
import pathlib
import re
import sys
import tempfile

import pytest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import library  # noqa: E402
import sorter  # noqa: E402
import stored  # noqa: E402

sys.path.insert(0, str(library.REPO / "tools/library"))
import library_files  # noqa: E402


def scene_library(folder, families):
    """A scene's surface library as the surface-library row writes it (the method's recipes, its own tokens), with
    `families` ({family: {variant: entry}}), at `folder`/materials.json."""
    method = library.theme_library()
    found = {**method, "tokens": {"panel-grey": "#8c96a0", "bolt-steel": "#9ba2a9", "dust": "#8b8883"},
             "dirt": "dust", "families": {family: {"variants": variants} for family, variants in families.items()}}
    path = pathlib.Path(folder) / "materials.json"
    path.write_text(json.dumps(found))
    return path


def test_the_method_library_holds_no_old_material():
    """Every old material retired (owner, 2026-10-21): the repository's library is the method alone, its recipes'
    defaults naming no token; a scene's surfaces are made fresh by the surface-library row."""
    method = library.theme_library()
    assert method["families"] == {} and method["tokens"] == {} and method["pictures"] == {}
    assert not list(library.PICTURES.glob("*.png"))
    assert not [name for defaults in method["recipes"].values() for name, value in defaults.items()
                if isinstance(value, str)]
    assert set(method["colour_settings"]) <= set(method["recipes"])


def test_every_variant_resolves_to_a_known_recipe_in_its_library_s_token_colours():
    with tempfile.TemporaryDirectory() as folder:
        path = scene_library(folder, {"paint": {"panel": {"recipe": "painted_metal", "token": "panel-grey",
                                                          "bare": "bolt-steel", "roughness": 0.4}},
                                      "steel": {"bolt": {"recipe": "bare_metal", "token": "bolt-steel"}}})
        found = library.library_specs(path)
        recipes = library.theme_library(path)["recipes"]
        assert set(found) == {"panel", "bolt"}
        for name, spec in found.items():
            assert spec["recipe"] in recipes, name
            assert len(spec["colour"]) == 3 and all(0.0 <= value <= 1.0 for value in spec["colour"]), name
            assert all(setting in spec for setting in recipes[spec["recipe"]]), name
        assert found["panel"]["bare"] == library.linear("#9ba2a9") and found["panel"]["roughness"] == 0.4
        assert found["bolt"]["dirt_colour"] == library.linear("#8b8883")  # the library's dirt token


def test_a_variant_is_named_once_across_the_families():
    with tempfile.TemporaryDirectory() as folder:
        path = scene_library(folder, {"paint": {"panel": {"recipe": "painted_metal", "token": "panel-grey"}},
                                      "steel": {"panel": {"recipe": "bare_metal", "token": "bolt-steel"}}})
        with pytest.raises(SystemExit, match="names 'panel' twice"):
            library.variants(library.theme_library(path))


def test_the_empty_library_names_the_missing_input():
    assert library.library_specs() == {} and library.variants(library.theme_library()) == {}  # a lookup finds none
    with pytest.raises(library.LibraryEmpty, match="surface panel .*run surface-library first"):
        library.spec(library.theme_library(), "panel", "grey", {})
    with tempfile.TemporaryDirectory() as folder:
        path = scene_library(folder, {"paint": {"panel": {"recipe": "painted_metal", "token": "panel-grey"}}})
        with pytest.raises(library.LibraryEmpty, match="surface rubber_mat"):
            library.spec(library.theme_library(path), "rubber_mat", "panel-grey", {"panel-grey": [0, 0, 0]})


def test_the_wear_levels_rise_and_a_place_s_own_wear_is_retired():
    levels = library.theme_library()["wear_levels"]
    assert levels["new"] == 0.0 < levels["worked"] < levels["worn"] <= 1.0
    # a place's own wear and materials in place.json were retired (2026-10-21): a scene's are its scene palette's
    with pytest.raises(library.LibraryEmpty, match="hub: no wear"):
        library.wear_of("hub")
    assert library.resolved("hub") == {}


def test_a_token_colour_is_linear():
    assert library.linear("#ffffff") == [1.0, 1.0, 1.0] and library.linear("#000000") == [0.0, 0.0, 0.0]
    assert abs(library.linear("#808080")[0] - 0.2159) < 1e-3


def test_nothing_goes_to_code_without_a_named_pipeline_failure():
    """#19 (the owner, 2026-10-20): every kind goes through the prop pipeline; neither plainness nor a fitting's
    parts check sends one to code. Only a kind the pipeline-failure record names is code-built; the old record
    retired with the old models (2026-10-21), so with none on file every kind goes to the pipeline."""
    for kind in ("hub_wall_upper_plain", "hub_toolboard", "hub_pipe_straight", "cockpit_thrust_indicator"):
        assert sorter.route(kind, {}) == "model", kind
        assert sorter.route(kind, {kind: {"failure": "every take failed"}}) == "code", kind
    assert sorter.failures(HERE / "no-such-record.json") == {} and sorter.fittings(HERE / "no-such-record.json") == {}
    assert sorter.shape_class("hub_lattice_hip_rib", (0.12, 4.6, 0.12)) == "slender"
    assert sorter.shape_class("hub_porthole_panel", (1.2, 1.2, 0.1)) == "opening"


def test_every_named_failure_says_what_failed_where_and_when():
    for kind, entry in sorter.failures().items():
        assert entry["failure"] and entry["evidence"] and re.fullmatch(r"\d{4}-\d\d-\d\d", entry["on"]), kind


def test_a_fitting_s_parts_check_holds_its_code_fallback_but_never_routes_it():
    """Method B's parts check (hub round five) stays the check a code fallback's build must pass (route.py layout):
    every part its close-up has seen at least SEEN_AT_LEAST from in front, no print over a part. It no longer sends
    a fitting to code: a fitting whose build shows every part still goes through the pipeline unless its failure is
    named."""
    parts = ["slab", "slat", "vent_back"]
    shown = {"parts": parts, "built": {"slab": 0.86, "slat": 1.0, "vent_back": 0.85}}
    buried = {"parts": parts, "built": {"slab": 0.33, "slat": 0.0, "vent_back": 0.0}}
    assert sorter.missing_parts(shown) == []
    assert sorter.missing_parts(buried) == ["slat", "vent_back"]
    assert sorter.missing_parts({"parts": parts, "built": {"slab": 0.9, "slat": 1.0}}) == ["vent_back"]
    assert sorter.missing_parts({"parts": parts}) == parts
    # A print over a part (round six: a locker's label over its vent) fails the fallback too.
    assert sorter.missing_parts(dict(shown, prints_off=["wall_lower_vent_1: label#52"])) == [
        "print off a clear area: wall_lower_vent_1: label#52"]
    assert sorter.route("hub_wall_lower_vent", {}) == "model"
    assert sorter.route("hub_wall_lower_vent", {"hub_wall_lower_vent": {"failure": "every take failed"}}) == "code"


def test_no_generated_piece_keeps_its_picture_s_colours():
    """Method B: the pipeline gives shape only; a generated piece's job never carries its picture model, so no piece
    brings its own rust, stains or streaks (round four's picture layer). Read from route.py's text: this check runs
    with the system python, which has no numpy to import the route with."""
    text = (HERE / "route.py").read_text()
    jobs = text[text.index("def jobs("):text.index("def middle_high(")]
    assert '"picture"' not in jobs and "picture.obj" not in jobs


def chunky_default_wall():
    """make_chunky's default_wall with the constants it reads, taken from its text (make_chunky needs Blender)."""
    tree = ast.parse((HERE / "inside/make_chunky.py").read_text())
    names = {"WALL", "WALL_VOXELS", "VOXEL_SHARE", "VOXEL_FINEST"}
    kept = [node for node in tree.body if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id in names
            or isinstance(node, ast.FunctionDef) and node.name in ("default_wall", "voxel_of")]
    space = {}
    exec(compile(ast.Module(body=kept, type_ignores=[]), "make_chunky", "exec"), space)
    return space["default_wall"]


def test_a_job_naming_no_wall_takes_two_voxels_but_never_under_5_mm():
    default_wall = chunky_default_wall()
    assert default_wall([0.4, 0.3, 0.2]) == 0.005  # a prop: its two voxels are under 5 mm
    assert abs(default_wall([8.0, 8.0, 60.0]) - 0.4) < 1e-9  # the launch rocket: two 0.2 m voxels, not lace


def test_every_room_job_names_its_wall():
    """route.py's room pieces keep the 5 mm wall hub round six was accepted at: each job names it, so make_chunky's
    two-voxel default never thickens a room piece into a slab."""
    text = (HERE / "route.py").read_text()
    jobs = text[text.index("def jobs("):text.index("def density_of(")]
    assert '"wall": own.get("wall", ROOM_WALL)' in jobs
    assert re.search(r"^ROOM_WALL = 0\.005$", text, re.M)


# Earth's builder modules beside pieces.py: the flat and stairwell, and the outdoor places (world 1).
EARTH_MODULES = ("earth_flat", "earth_stairwell", "pieces_earth")


def builder_texts():
    """pieces.py and the builder modules beside it: Earth's rooms' (the prologue build), the ship rooms', the hangar
    ship's and the bodies of big objects seen up close."""
    return [(HERE / "inside/pieces.py").read_text()] + [(HERE / f"inside/{name}.py").read_text()
                                                       for name in EARTH_MODULES + ("pieces_ship", "pieces_hull",
                                                                                    "pieces_bodies")]


def test_every_fitting_lists_its_close_up_and_parts_and_has_a_builder():
    text = "\n".join(builder_texts())
    for name, entry in sorter.fittings().items():
        assert entry["closeup"] and entry["parts"], name
        assert f"def {name}(size, laid):" in text, name


@pytest.mark.xfail(strict=True, reason="the old fittings' builders (pieces*.py) stay until they are deleted; the "
                                       "fittings record that allowed them retired with the old models (2026-10-21)")
def test_every_code_builder_is_on_the_allow_list():
    """pieces.py builds only plain kinds and method B's room fittings: a builder for anything else is a piece made
    by hand from a sentence."""
    texts = builder_texts()
    names = re.findall(r'"(\w+)"', texts[0][texts[0].index("BUILDERS = "):texts[0].index("EARTH_ROOMS")])
    for text in texts[1:]:
        names += re.findall(r'"(\w+)"', text[text.index("BUILDERS = "):])
    # A body builder (pieces_bodies) builds a big object's main shapes under its take's details, the owner's rule
    # for big objects seen up close (2026-10-18, PRD #10); bodies.BODIES names each take it is used for.
    bodies_text = texts[-1]
    body_builders = set(re.findall(r'"(\w+)"', bodies_text[bodies_text.index("BUILDERS = "):]))
    off = sorted(name for name in names
                 if name not in sorter.PLAIN and name not in sorter.fittings() and name not in body_builders)
    assert not off, f"code builders for kinds that are not plain plates, pipes, trims or fittings: {', '.join(off)}"


@pytest.mark.xfail(strict=True, reason="#41: every kit room installed before #19 is made again through the loop; "
                                       "the mark goes when the last room is remade")
def test_every_model_a_kit_room_lays_was_made_on_its_kind_s_route():
    """Every model a kit room lays (data/kit/<room>.json: kit and furniture) says the route it was made on, and that is
    its kind's route: code only for a kind the pipeline-failure record names, the prop pipeline for every other (#41's
    acceptance: a test fails when a model layer reaches a model without going through the loop). Every kit installed
    before #19 fails it until its room is made again through the loop."""
    off = {}
    for path in sorted((library.REPO / "data/kit").glob("*.json")):
        layout = json.loads(path.read_text())
        kinds = {found["model"]: found["kind"] for found in layout["pieces"] if "part" not in found}
        kinds.update({name: f"{path.stem}_{name.rsplit('_', 1)[0]}" for name, about in layout["models"].items()
                      if "prop" in about})
        wrong = sorted({kind for name, kind in kinds.items()
                        if layout["models"][name].get("route") != sorter.route(kind)})
        if wrong:
            off[path.stem] = wrong
    assert not off, (f"{sum(map(len, off.values()))} kinds in {len(off)} kit rooms not made on their kind's route: "
                     + "; ".join(f"{room} {len(wrong)} ({', '.join(wrong[:3])}...)" for room, wrong in off.items()))


def test_every_kind_of_every_kit_room_gets_a_route():
    for path in sorted((library.REPO / "data/kit").glob("*.json")):
        layout = json.loads(path.read_text())
        found = sorter.sorted_kinds(layout)
        # A room of props alone (the expedition camp's grounds) lays no kit pieces; its props' routes are held above.
        props = any("prop" in about for about in layout["models"].values())
        assert (found or props) and all(entry["route"] in ("code", "model", "decal") for entry in found.values()), \
            path.stem


def test_a_room_s_baked_pictures_are_stored_as_webp_and_its_models_point_at_them():
    """stored.py: no baked PNG left in a kit room's installed models (route.py install, the made folder), every glTF
    picture a WebP through EXT_texture_webp (stored as PNG the hub's alone were 414 MB). Read where a room is
    installed on this machine."""
    for folder in sorted((library_files.made_folder() / "models").glob("*_kit")):
        assert not [name for name in folder.rglob("*.png") if name.parent.name == "textures"
                    and stored.kind_of(name.name)], folder.name
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


def command_output(arguments, folder):
    """What `library.py <arguments>` prints, its whole output written under `folder`."""
    saved = (sys.argv, library.OUTPUT)
    sys.argv, library.OUTPUT = ["library.py", *arguments], pathlib.Path(folder)
    try:
        with contextlib.redirect_stdout(io.StringIO()) as printed:
            library.main()
    finally:
        sys.argv, library.OUTPUT = saved
    return printed.getvalue()


def test_the_list_prints_one_line_and_writes_every_family():
    with tempfile.TemporaryDirectory() as folder:
        library_path = scene_library(folder, {"paint": {"panel": {"recipe": "painted_metal", "token": "panel-grey"}},
                                              "steel": {"bolt": {"recipe": "bare_metal", "token": "bolt-steel"}}})
        saved = library.LIBRARY
        library.theme_library.__defaults__ = (library_path,)
        try:
            printed = command_output(["--list"], folder)
            path = pathlib.Path(folder) / "library-list.txt"
            assert printed == f"library: 2 families, 2 variants; list: {path}\n", printed
            assert path.read_text() == "paint: panel\nsteel: bolt\n2 variants\n"
            assert command_output(["--list", "--verbose"], folder) == path.read_text()
        finally:
            library.theme_library.__defaults__ = (saved,)


def test_the_command_line_says_the_empty_library():
    with tempfile.TemporaryDirectory() as folder:
        listed = pathlib.Path(folder) / "library-list.txt"
        assert command_output(["--list"], folder) == f"library: 0 families, 0 variants; list: {listed}\n"
        with pytest.raises(SystemExit, match="library: hub: no wear"):  # a place's own wear, retired: refused by name
            command_output(["hub"], folder)


def main():
    tests = [value for name, value in globals().items()
             if name.startswith("test_") and not any(mark.name == "xfail" for mark in getattr(value, "pytestmark", []))]
    for test in tests:
        test()
    print(f"{len(tests)} checks passed")


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[3] / "conftest.py"))["refuse_outside_sandbox"]()
    main()
