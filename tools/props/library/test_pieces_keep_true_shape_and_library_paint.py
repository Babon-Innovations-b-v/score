"""The library's invariant: a made piece keeps a true shape and takes only library paint. Its finishes are library
surfaces in the library's own token colours (an unknown one is a named missing input, never a guess); a big object's
body keeps only the take's faces it names and stands in its laid box; paint goes by whole parts, one material a part,
and the checks fail patchy, stripped or wrongly coloured paint; a piece is packaged only when it matches its
inventory and passed its model check; a splitter is scored by the finishes it owns; a square kind comes out straight.

Every answer below is worked out by hand from the fixture (a box's halves, a box's faces, a patch's pixels, the
sRGB formula, the console's numbers), never by the code under test.

Breaks that turn these red (each applied once, seen red, reverted, 2026-10-26):
- data/library/materials.json: `"families": {"paint": {"variants": {}}}` ->
  test_the_method_library_holds_no_old_material.
- library `spec`: `dirt_colour=colours[token]` -> test_a_variant_takes_its_recipe_in_its_library_s_own_token_colours.
- library `variants`: `if False:` for the twice-named refusal -> test_a_surface_named_twice_is_refused.
- library `spec`: `if False:` for the `missing` refusal ->
  test_an_unknown_surface_or_a_place_s_own_wear_is_a_named_missing_input.
- library `linear`: `value / 12.92 if True` -> test_a_token_colour_is_linear.
- recipes.py `cloth`: drop its `thread` argument -> test_every_recipe_s_settings_are_in_the_method.
- library `main`: `if True:` print the whole list -> test_the_command_line_prints_one_summary_line.
- make_chunky `default_wall`: `return WALL_VOXELS * voxel_of(size)` ->
  test_a_job_naming_no_wall_takes_two_voxels_not_under_5_mm.
- make_chunky `full_model`: `bpy.ops.wm.ply_import` again; and, apart, `kept_triangles`: `once[:] = True` ->
  test_a_part_reads_the_same_every_run (2026-10-28).
- make_chunky `system_refusal`: `return None` -> test_a_bake_refuses_a_machine_of_another_system (2026-10-29).
- make_chunky `lining`: `reach = ... if front is None else front` -> `reach = ends[...][axis]` (front unread); and,
  apart, `max(ends[0][axis], low[axis] - wall)` -> `low[axis]` -> test_a_recess_is_lined_behind_the_model_s_front_and_
  never_stands_proud_of_it (2026-10-29).
- make_chunky `kit_points`: `-points[:, 1]` -> `points[:, 1]` -> test_a_shape_s_points_are_read_as_its_gltf_holds_them
  (2026-10-29).
- stored `pointed_at_webp`: drop `texture.pop("source", None)` -> test_stored_pictures_are_webp_and_a_room_has_a_budget.
- bodies `kept`: drop the detail boxes' `found |= ...` -> test_a_body_keeps_only_the_take_faces_it_names.
- bodies `console_outline`: `top = CONSOLE_TOP * tall + 0.1` -> test_every_body_stands_in_its_laid_box.
- bodies.BODIES: `first_module-r1`'s builder `station_hull` -> test_every_code_builder_is_a_body_a_take_names.
- body_parts `laid`: `return turned * (...)` (no `- middle`) ->
  test_a_re_made_take_takes_the_nearest_accepted_surface_at_any_scale.
- body_parts `write_surfaces`: no `old.unlink()`; and, apart, `write`: `if False:` for the no-body refusal ->
  test_a_re_made_take_s_surfaces_replace_the_old_and_a_take_with_no_body_is_refused.
- package `turned`: `math.radians(facing)` -> test_a_copy_lands_on_its_spot_facing_its_way.
- package `problems`: the count comparison `False` -> test_a_package_that_does_not_match_its_inventory_is_refused.
- package `made_reports`: `if False:` for the job filter -> test_a_report_no_current_job_names_is_not_read.
- place_route `yaw_of`: `np.arctan2(-turn[2], turn[0])` ->
  test_place_route_reads_a_turn_as_its_yaw_and_splits_a_long_take.
- patchy `score`: drop `whole_piece |= whole_parts(island, regions)` ->
  test_patchy_paint_fails_and_paint_by_part_or_region_passes.
- labels `by_regions`: `return scores.argmax(1), ...`; and, apart, `without_crumbs`: `range(0)` ->
  test_a_noisy_vote_settles_into_whole_parts.
- labels `paint_parts`: `if False:` for the judged pick -> test_a_part_takes_one_material_by_its_lit_colour_or_the_judge.
- feet `linked`: `range(-2, 3)` -> `range(-1, 2)` (both loops) ->
  test_feet_are_the_clusters_every_pair_within_reach_gives_without_listing_the_pairs (2026-10-28).
- labels `region_materials`: `if False:` for the set-aside ->
  test_the_judge_may_not_put_a_saturated_finish_on_a_colourless_region.
- part_judge `vote`: `if False:` for the majority -> test_repeated_asks_decide_by_majority.
- patchy `stripped`: `"pass": True`; and, apart, `twins_left_out`: `return []` first ->
  test_a_lost_main_colour_or_flat_or_bare_paint_is_stripped.
- patchy `worn_as_around`: drop the `labels = np.where(worn...)` -> test_a_worn_edge_is_wear_not_a_second_material.
- regions `region_map`: `np.argsort(area)` (largest laid last) -> test_a_patch_on_a_panel_is_its_own_region.
- surface_check `verdict`: a neutral region `return "pass"` ->
  test_the_surface_check_sees_gold_on_white_and_two_finishes_as_one.
- bake.py `smoothed_normals`: `weight = np.ones_like(agree)` (no crease) ->
  test_a_lumpy_face_is_smoothed_and_a_real_edge_kept.
- split_compare `finishes_owned`: `owned.append(number)` always ->
  test_a_split_along_the_finishes_scores_above_one_part.
- split_compare `region_agreement`: the table as wide as the drawn regions ->
  test_region_agreement_takes_a_region_the_split_misses.
- split_compare `voxel_parts_on_faces`: `return 1 - ...` ->
  test_predicted_colours_and_voxels_become_face_parts.
- split_spread `same_regions`: drop `len(painted) == len(shares)` ->
  test_the_spread_matches_regions_and_counts_only_counted_finishes.
- straight `side_fit`: `tilt = 0.0` -> test_a_square_piece_must_come_out_straight.
- labels `finish_turn`: `return best[0]` (no `@ raw_facing(take)`) ->
  test_the_finish_turn_lays_a_raw_still_facing_plus_z_as_its_final_stands (2026-10-29).

The Blender build (test_every_body_builds_with_walls_the_model_check_passes) runs only where Blender and Xvfb are; on
a box without them it skips, and its break (a body wall 2 mm thick) is unproven there.

    PROPS_HOME=$(mktemp -d) .venv/bin/python -m pytest \
        tools/props/library/test_pieces_keep_true_shape_and_library_paint.py
"""
import ast
import contextlib
import io
import json
import math
import os
import pathlib
import re
import shutil
import subprocess
import sys
import types

import numpy as np
import pytest
import trimesh

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.append(str(HERE / "inside"))
sys.path.append(str(HERE.parent / "gates"))
import bodies  # noqa: E402
import body_parts  # noqa: E402
import labels  # noqa: E402
import library  # noqa: E402
import model as model_check  # noqa: E402
import package  # noqa: E402
import part_judge  # noqa: E402
import patchy  # noqa: E402
import place_route  # noqa: E402
import regions  # noqa: E402
import split_compare  # noqa: E402
import split_spread  # noqa: E402
import stored  # noqa: E402
import straight  # noqa: E402
import surface_check  # noqa: E402


def srgb_to_linear(hex_colour):
    """The sRGB transfer function (IEC 61966-2-1), written here apart from library.linear."""
    found = []
    for at in (1, 3, 5):
        value = int(hex_colour[at:at + 2], 16) / 255
        found.append(value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4)
    return found


# ---- the surface library -------------------------------------------------------------------------------------------

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
    defaults naming no token, and a lookup of every variant finds none."""
    method = library.theme_library()
    assert method["families"] == {} and method["tokens"] == {} and method["pictures"] == {}
    assert not list(library.PICTURES.glob("*.png"))
    assert not [name for defaults in method["recipes"].values() for name, value in defaults.items()
                if isinstance(value, str)]
    assert set(method["colour_settings"]) <= set(method["recipes"])
    assert library.library_specs() == {} and library.variants(method) == {}


def test_a_variant_takes_its_recipe_in_its_library_s_own_token_colours(tmp_path):
    path = scene_library(tmp_path, {"paint": {"panel": {"recipe": "painted_metal", "token": "panel-grey",
                                                        "bare": "bolt-steel", "roughness": 0.4}},
                                    "steel": {"bolt": {"recipe": "bare_metal", "token": "bolt-steel"}}})
    found = library.library_specs(path)
    recipes = library.theme_library(path)["recipes"]
    assert set(found) == {"panel", "bolt"}
    for name, spec in found.items():
        assert spec["recipe"] in recipes and all(setting in spec for setting in recipes[spec["recipe"]]), name
    assert found["panel"]["colour"] == pytest.approx(srgb_to_linear("#8c96a0"))
    assert found["panel"]["bare"] == pytest.approx(srgb_to_linear("#9ba2a9")) and found["panel"]["roughness"] == 0.4
    assert found["bolt"]["dirt_colour"] == pytest.approx(srgb_to_linear("#8b8883"))  # the library's dirt token


def test_a_surface_named_twice_is_refused(tmp_path):
    path = scene_library(tmp_path, {"paint": {"panel": {"recipe": "painted_metal", "token": "panel-grey"}},
                                    "steel": {"panel": {"recipe": "bare_metal", "token": "bolt-steel"}}})
    with pytest.raises(SystemExit, match="names 'panel' twice"):
        library.variants(library.theme_library(path))


def test_an_unknown_surface_or_a_place_s_own_wear_is_a_named_missing_input(tmp_path):
    with pytest.raises(library.LibraryEmpty, match="surface panel .*run surface-library first"):
        library.spec(library.theme_library(), "panel", "grey", {})
    path = scene_library(tmp_path, {"paint": {"panel": {"recipe": "painted_metal", "token": "panel-grey"}}})
    with pytest.raises(library.LibraryEmpty, match="surface rubber_mat"):
        library.spec(library.theme_library(path), "rubber_mat", "panel-grey", {"panel-grey": [0, 0, 0]})
    levels = library.theme_library()["wear_levels"]
    assert levels["new"] == 0.0 < levels["worked"] < levels["worn"] <= 1.0
    with pytest.raises(library.LibraryEmpty, match="hub: no wear"):  # a place's own wear: retired 2026-10-21
        library.wear_of("hub")
    assert library.resolved("hub") == {}


def test_a_token_colour_is_linear():
    assert library.linear("#ffffff") == [1.0, 1.0, 1.0] and library.linear("#000000") == [0.0, 0.0, 0.0]
    assert abs(library.linear("#808080")[0] - 0.2159) < 1e-3  # sRGB 128 is linear 0.2159 (IEC 61966-2-1)
    assert abs(library.linear("#050505")[0] - 5 / 255 / 12.92) < 1e-9  # the straight part of the curve


def test_every_recipe_s_settings_are_in_the_method():
    """The method's defaults name each recipe's settings (recipes.py needs Blender, so its functions' arguments are
    read from its syntax tree). The people's library had only `quilted` to make a fabric of, and the astronaut's plain
    overalls were drawn as a quilt (2026-10-23): plain cloth is a recipe of its own."""
    tree = ast.parse((HERE / "recipes.py").read_text())
    arguments = {node.name: {arg.arg for arg in node.args.args} for node in tree.body
                 if isinstance(node, ast.FunctionDef)}
    table = next(node.value for node in tree.body if isinstance(node, ast.Assign)
                 and getattr(node.targets[0], "id", None) == "RECIPES")
    recipes = {key.value: value.id for key, value in zip(table.keys, table.values)}
    given = {"colour", "bare", "second", "dirt_colour", "wear", "dirt", "seed", "foot", "kicks", "image"}
    method = library.theme_library()["recipes"]
    assert set(recipes) == set(method)
    assert {name: arguments[function] - given - set(method[name]) for name, function in recipes.items()
            if arguments[function] - given - set(method[name])} == {}
    assert arguments[recipes["cloth"]] - given == {"roughness", "thread", "bump", "dirt_reach"}


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


def test_the_command_line_prints_one_summary_line(tmp_path):
    """A wording check guarding the owner's output rule (CLAUDE.md, "summaries, not dumps"): one summary line naming
    the file that holds the whole list; --verbose prints the list itself; a retired place is refused by name."""
    listed = tmp_path / "library-list.txt"
    assert command_output(["--list"], tmp_path) == f"library: 0 families, 0 variants; list: {listed}\n"
    with pytest.raises(SystemExit, match="library: hub: no wear"):
        command_output(["hub"], tmp_path)
    library_path = scene_library(tmp_path, {"paint": {"panel": {"recipe": "painted_metal", "token": "panel-grey"}},
                                            "steel": {"bolt": {"recipe": "bare_metal", "token": "bolt-steel"}}})
    saved = library.theme_library.__defaults__
    library.theme_library.__defaults__ = (library_path,)
    try:
        assert command_output(["--list"], tmp_path) == f"library: 2 families, 2 variants; list: {listed}\n"
        assert listed.read_text() == "paint: panel\nsteel: bolt\n2 variants\n"
        assert command_output(["--list", "--verbose"], tmp_path) == "paint: panel\nsteel: bolt\n2 variants\n"
    finally:
        library.theme_library.__defaults__ = saved


def chunky_functions(functions, constants=()):
    """make_chunky's named functions with the constants they read, taken from its text (make_chunky needs Blender)."""
    tree = ast.parse((HERE / "inside/make_chunky.py").read_text())
    kept = [node for node in tree.body if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id in constants
            or isinstance(node, ast.FunctionDef) and node.name in functions]
    space = {}
    exec(compile(ast.Module(body=kept, type_ignores=[]), "make_chunky", "exec"), space)
    return space


def chunky_default_wall():
    """make_chunky's default_wall with the constants it reads."""
    return chunky_functions(("default_wall", "voxel_of"),
                            {"WALL", "WALL_VOXELS", "VOXEL_SHARE", "VOXEL_FINEST"})["default_wall"]


def test_a_job_naming_no_wall_takes_two_voxels_not_under_5_mm():
    default_wall = chunky_default_wall()
    assert default_wall([0.4, 0.3, 0.2]) == 0.005  # a prop: its two voxels are under 5 mm
    assert abs(default_wall([8.0, 8.0, 60.0]) - 0.4) < 1e-9  # the launch rocket: two 0.2 m voxels, not lace


def test_a_bake_refuses_a_machine_of_another_system(monkeypatch):
    # glibc 2.43 laid the solid copy a few vertices apart from the container's 2.39 and every picture followed
    # (2026-10-29, #36): a bake runs only on the system its file names, so the file's key names the system
    space = chunky_functions(("system_refusal",), {"SYSTEM"})
    blender = types.SimpleNamespace(app=types.SimpleNamespace(version_string="5.0.1"))
    space.update(bpy=blender, os=os)
    monkeypatch.setattr(os, "confstr", lambda name: "glibc 2.39")
    assert space["system_refusal"]() is None
    monkeypatch.setattr(os, "confstr", lambda name: "glibc 2.43")
    assert "glibc 2.43" in space["system_refusal"]()
    blender.app.version_string = "5.1.0"
    monkeypatch.setattr(os, "confstr", lambda name: "glibc 2.39")
    assert "5.1.0" in space["system_refusal"]()



def test_a_recess_is_lined_behind_the_model_s_front_and_never_stands_proud_of_it():
    # base's module (#72, 2026-10-29) is a hollow box of walls: its recess cut opened into its inside, rays meeting
    # its far wall 4.4 m behind the recess's back. The recess (x -5.321 to 1.229, y 0 to 6, z -0.05 to 6.07 in a
    # 10.742 by 6 by 12.04 m model) is lined first, a wall (0.08 m) on its back, its sides and its top, never below
    # its foot nor past the model's laid box, and out on its open face only to where the model's front stands (its S
    # wall at z 5.1 under a roof reaching 6.02), else to the laid box's side.
    space = chunky_functions(("lining", "open_face"))
    recess = [[-5.321, 0.0, -0.05], [1.229, 6.0, 6.07]]
    size = [10.742, 6.0, 12.04]
    assert space["open_face"](recess, size) == (2, 1)
    low, high = space["lining"](recess, size, 0.08, 5.1)
    assert np.allclose(low, [-5.371, 0.0, -0.13]) and np.allclose(high, [1.309, 6.0, 5.1]), (low, high)
    low, high = space["lining"](recess, size, 0.08)
    assert np.allclose(high, [1.309, 6.0, 6.02]), high  # no front found: the laid box's side
    low, high = space["lining"]([[-1.0, 1.0, -4.05], [1.0, 2.0, 0.5]], [4.0, 4.0, 8.0], 0.1, -3.9)
    assert np.allclose(low, [-1.1, 1.0, -3.9]) and np.allclose(high, [1.1, 2.1, 0.6]), (low, high)  # the -z face


def test_a_shape_s_points_are_read_as_its_gltf_holds_them():
    # the bake measures a copy as surfaces-check measures the made glTF (route_bake.squared_again): Blender's x, z
    # and -y, the kit frame (y up)
    kit_points = chunky_functions(("kit_points",))["kit_points"]
    assert kit_points([1.0, 2.0, 3.0, 4.0, 5.0, 6.0]).tolist() == [[1.0, 3.0, -2.0], [4.0, 6.0, -5.0]]


def test_a_part_reads_the_same_every_run():
    # Blender's PLY importer runs Mesh.validate, which reordered a 923k-face part's faces differently each run, so
    # two bakes of one take differed (garage_door_1, 2026-10-28); the part is read in file order instead.
    source = (HERE / "inside/make_chunky.py").read_text()
    assert "ply_import" not in source and ".validate(" not in source
    kept_triangles = chunky_functions(("kept_triangles",))["kept_triangles"]
    corners = np.array([[0, 1, 2], [2, 2, 3], [3, 4, 5], [1, 2, 0], [5, 4, 3], [6, 7, 8]])
    assert kept_triangles(corners).tolist() == [[0, 1, 2], [3, 4, 5], [6, 7, 8]]  # file order, firsts only

def test_stored_pictures_are_webp_and_a_room_has_a_budget(tmp_path):
    gltf = tmp_path / "piece_1.gltf"
    gltf.write_text(json.dumps({"images": [{"uri": "textures/piece_1_normal.png", "mimeType": "image/png"},
                                           {"uri": "piece_1_screen.png"}],
                                "textures": [{"sampler": 0, "source": 0}, {"sampler": 0, "source": 1}]}))
    assert stored.pointed_at_webp(gltf) == 1
    found = json.loads(gltf.read_text())
    assert found["images"][0] == {"uri": "textures/piece_1_normal.webp", "mimeType": "image/webp"}
    assert found["textures"][0] == {"sampler": 0, "extensions": {"EXT_texture_webp": {"source": 0}}}
    assert found["textures"][1] == {"sampler": 0, "source": 1}  # a screen's picture is not a baked map
    assert "EXT_texture_webp" in found["extensionsUsed"] and "EXT_texture_webp" in found["extensionsRequired"]
    assert stored.over_budget({"disk_mb": 10.0, "card_mb": 10.0}) == []
    assert stored.over_budget({"disk_mb": stored.BUDGET["disk_mb"] + 1, "card_mb": 1.0})


# ---- big objects' code bodies --------------------------------------------------------------------------------------

CONSOLE = [3.6, 1.0, 0.65]
MODULE = [6.5, 4.308, 3.783]
CORE = [1.4, 2.3, 1.4]
FUEL = [0.9, 1.8, 0.9]
WATER = [1.6, 1.6, 1.6]
LANDER = [8.649, 19.0, 10.597]
ROVER = [1.72, 1.66, 3.03]
CRANE = [1.811, 3.2, 1.065]
# Each built body's laid size, by the first word of its builder.
SIZES = {"console": CONSOLE, "station": MODULE, "power": CORE, "fuel": FUEL, "water": WATER, "lander": LANDER,
         "rover": ROVER, "crane": CRANE}
# The plan's kind for each builder (build_only builds the kind's part after its first underscore).
KINDS = {"console_body": "cockpit_console_body", "station_module": "station_station_module",
         "power_core": "engineroom_power_core", "fuel_tank": "engineroom_fuel_tank",
         "water_tank": "greenhouse_water_tank", "lander_body": "campgrounds_lander_body",
         "rover_body": "garage_rover_body", "crane_body": "campgrounds_crane_body"}


def test_a_body_keeps_only_the_take_faces_it_names():
    """The console keeps its controls (an led anywhere) and its bays' details only inside a bay; the module, the core,
    the water tank, the lander and the crane keep nothing; the fuel tank and the rover keep their fittings by place."""
    bay_low, bay_high = bodies.console_bays(CONSOLE)["middle_bay"]
    in_bay = [0.0, (bay_low[1] + bay_high[1]) / 2, bay_high[2] - 0.01]
    behind_bay = [0.0, in_bay[1], bay_high[2] + 0.05]
    on_the_back = [0.0, 0.5, CONSOLE[2] / 2 - 0.01]
    found = bodies.kept("console_body", CONSOLE, [in_bay, behind_bay, on_the_back, on_the_back],
                        ["dark_panel", "dark_panel", "dark_panel", "led_red"], ["led_red"])
    assert found.tolist() == [True, False, False, True], found
    x0, x1, y0, y1, front = bodies.CONSOLE_CROWN_BLOCK
    strip = [0.0, (y0 + y1) / 2 * CONSOLE[1], front * CONSOLE[2] - 0.01]
    assert bodies.kept("console_body", CONSOLE, [strip], ["dark_panel"], []).tolist() == [True]
    nothing = np.zeros((3, 3))
    for builder, size, surfaces in (("station_module", MODULE, ["mli_gold", "mli_silver", "galvanized_dull"]),
                                    ("power_core", CORE, ["clear_glass", "led_white", "led_white"]),
                                    ("water_tank", WATER, ["dark_panel", "bare_steel", "bare_steel"]),
                                    ("lander_body", LANDER, ["stainless"] * 3),
                                    ("crane_body", CRANE, ["cream_paint", "stainless", "stainless"])):
        assert not bodies.kept(builder, size, nothing, surfaces, []).any(), builder
    boxes = bodies.detail_boxes("fuel_tank", FUEL)
    assert len(boxes) == len(bodies.FUEL_DETAILS)
    inside = [[(low[axis] + high[axis]) / 2 for axis in range(3)] for low, high in boxes]
    found = bodies.kept("fuel_tank", FUEL, inside + [[0.0, -1.0, 0.0]], ["dark_panel"] * (len(boxes) + 1), [])
    assert found.tolist() == [True] * len(boxes) + [False], found
    wide, tall, deep = ROVER
    x0, x1, y0, y1, z0, z1 = bodies.ROVER_DETAILS["seats"]
    on_a_seat = [0.0, (y0 + y1) / 2 * tall, (z0 + z1) / 2 * deep]
    tyre = [bodies.ROVER_TYRE[0] * wide - 0.05, bodies.ROVER_WHEEL[0] * tall, bodies.ROVER_AXLES[1] * deep]
    floor = [0.0, bodies.ROVER_FLOOR[0] * tall, 0.0]
    found = bodies.kept("rover_body", ROVER, [on_a_seat, tyre, floor], ["plastic_grey", "plastic_grey", "screen"], [])
    assert found.tolist() == [True, False, False], found
    assert set(bodies.ROVER_DETAIL_SURFACES) == set(bodies.ROVER_DETAILS)


def test_every_body_stands_in_its_laid_box():
    """A body drops the take's lumps and never grows past its laid box: the console's outline and bays, the core's
    lamps and pipes, the lander's hull (closed at its top, its decal's panel flat: the decal is 1.2 x 0.3 m at
    [0, 7.5], campgrounds_lander's), the module's blankets on its grid and the rover's detail boxes."""
    points = np.array(bodies.console_outline(CONSOLE))
    assert np.isclose(points[:, 0].min(), -CONSOLE[0] / 2) and np.isclose(points[:, 0].max(), CONSOLE[0] / 2)
    assert points[:, 1].min() == 0.0 and points[:, 1].max() <= CONSOLE[1]
    for low, high in bodies.console_bays(CONSOLE).values():
        assert -CONSOLE[0] / 2 < low[0] < high[0] < CONSOLE[0] / 2 and 0 < low[1] < high[1] < CONSOLE[1]
    for low, high in bodies.CORE_LAMPS:
        assert bodies.CORE_PLINTH[0] < low < high <= bodies.CORE_HOOD[2]
    reach = max(abs(x) for run in bodies.CORE_PIPES for x, _ in run) + bodies.CORE_PIPE[0]
    assert reach < 0.5 and bodies.CORE_CANISTER["at"] + bodies.CORE_CANISTER["radius"] < 0.5
    profile = np.array(bodies.lander_profile(LANDER))
    assert profile[0].tolist() == [0.0, bodies.LANDER_FOOT * LANDER[1]] and profile[-1].tolist() == [0.0, LANDER[1]]
    assert np.all(np.diff(profile[2:, 0]) < 0) and np.all(np.diff(profile[1:, 1]) >= 0)
    assert profile[:, 0].max() < LANDER[0] / 2 and bodies.LANDER_AXIS * LANDER[2] + profile[:, 0].max() < LANDER[2] / 2
    across, low, high = bodies.LANDER_PANEL
    assert across * LANDER[0] >= 0.6 and low * LANDER[1] <= 7.5 - 0.15 and high * LANDER[1] >= 7.5 + 0.15
    first, last, count = bodies.LANDER_SEAMS
    seams = [(first + (last - first) * step / (count - 1)) * LANDER[1] for step in range(count)]
    assert not any(low * LANDER[1] - 0.05 < seam < high * LANDER[1] + 0.05 for seam in seams), seams
    blankets = bodies.module_foil(MODULE)
    letters = sum(cells.count("S") + cells.count("G") for cells in bodies.MODULE_FOIL)
    step = (bodies.MODULE_HULL[1] - bodies.MODULE_HULL[0]) * MODULE[0] / len(bodies.MODULE_FOIL[0])
    assert round(sum(end - start for _, _, _, start, end in blankets) / step) == letters
    assert {surface for surface, *_ in blankets} == {"mli_silver", "mli_gold"}
    holes = bodies.module_holes(MODULE)
    assert len(holes) == 1 and holes[0][:2] == (30.0, 60.0), holes
    for low, high in bodies.detail_boxes("rover_body", ROVER):
        assert all(low[axis] < high[axis] for axis in range(3))
        assert -ROVER[0] / 2 <= low[0] and high[0] <= ROVER[0] / 2 and 0 <= low[1] and high[1] <= ROVER[1] + 1e-9
        assert -ROVER[2] / 2 <= low[2] and high[2] <= ROVER[2] / 2


def test_every_code_builder_is_a_body_a_take_names():
    """pieces.py builds only the bodies of big objects seen up close (the owner's rule of 2026-10-18, PRD #10), each
    one bodies.BODIES names for a take, with its details and a turn that is a turn. pieces_bodies needs Blender, so
    its BUILDERS table is read from its text: a wording check guarding that owner rule."""
    pieces = (HERE / "inside/pieces.py").read_text()
    bodies_text = (HERE / "inside/pieces_bodies.py").read_text()
    assert "BUILDERS = dict(pieces_bodies.BUILDERS)" in pieces
    builders = set(re.findall(r'"(\w+)"', bodies_text[bodies_text.index("BUILDERS = "):]))
    named = {body["builder"] for body in bodies.BODIES.values()}
    assert builders == named, builders ^ named
    for take, body in bodies.BODIES.items():
        assert bodies.body_of(take) is body and body["builder"] in bodies.DETAILS, take
        turn = np.array(bodies.laid_turn(take, np.eye(3).flatten().tolist())).reshape(3, 3)
        assert np.allclose(turn @ turn.T, np.eye(3)) and np.isclose(np.linalg.det(turn), 1.0), (take, turn)
    assert set(KINDS) <= named


@pytest.mark.skipif(not (REPO / "tools/blender/session.py").exists() or shutil.which("Xvfb") is None,
                    reason="no Blender launcher or no private screen for it (Xvfb, tools/blender/launch.sh)")
def test_every_body_builds_with_walls_the_model_check_passes(tmp_path):
    """Each body built at its laid size as geometry alone (inside/build_only.py, headless Blender, no bake) fills
    most of its laid box, never grows past it, and has walls the model check passes."""
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps({"models": {
        f"{builder}_1": {"route": "code", "kind": kind, "size": SIZES[builder.split("_")[0]], "laid": {}}
        for builder, kind in KINDS.items()}}))
    out = tmp_path / "built"
    done = subprocess.run([sys.executable, str(REPO / "tools/blender/session.py"), "batch",
                           str(HERE / "inside/build_only.py"), "--", str(REPO), str(plan), str(out)],
                          capture_output=True, text=True)
    assert done.returncode == 0, done.stdout[-2000:] + done.stderr[-2000:]
    built = {path.stem: trimesh.load(path, force="mesh") for path in out.glob("*.glb")}
    assert sorted(built) == sorted(f"{builder}_1" for builder in KINDS), sorted(built)
    for name, mesh in built.items():
        size = SIZES[name.split("_")[0]]
        assert np.all(mesh.extents <= np.array(size) + 0.01), (name, mesh.extents)
        assert np.all(mesh.extents >= np.array(size) * 0.85), (name, mesh.extents)
        assert model_check.thinnest(mesh, mesh.extents) >= model_check.THINNEST_LIMIT, name


# ---- a re-made take's parts ----------------------------------------------------------------------------------------

LAID_SIZE = [2.0, 1.0, 0.5]
IDENTITY = [1, 0, 0, 0, 1, 0, 0, 0, 1]


def two_toned_box(scale):
    """A box whose top half's faces are `top` and bottom half's `bottom`: (middles, names)."""
    box = trimesh.creation.box(extents=[1.0, 1.0, 1.0]).subdivide().subdivide()
    middles = box.triangles_center * np.asarray(scale)
    return middles, np.where(box.triangles_center[:, 1] > 0, "top", "bottom")


def test_a_re_made_take_takes_the_nearest_accepted_surface_at_any_scale():
    old_middles, old_names = two_toned_box([1.0, 1.0, 1.0])
    new_middles, truth = two_toned_box([0.3, 0.7, 0.2])  # another take's own scale: both are fitted to LAID_SIZE
    names, gap = body_parts.surfaces_from(new_middles, old_middles, old_names, IDENTITY, LAID_SIZE)
    assert (names == truth).mean() > 0.95, (names == truth).mean()
    assert gap < 0.01, gap
    points = body_parts.laid(np.array([[3.0, 5.0, 1.0], [7.0, 9.0, 2.0]]), IDENTITY, LAID_SIZE)
    assert np.allclose(points, [[-1.0, 0.0, -0.25], [1.0, 1.0, 0.25]])  # on its foot's middle at the laid size


def test_a_re_made_take_s_surfaces_replace_the_old_and_a_take_with_no_body_is_refused(tmp_path):
    mesh = trimesh.creation.box(extents=[1.0, 1.0, 1.0])
    names = np.where(mesh.triangles_center[:, 1] > 0, "top", "bottom")
    (tmp_path / "stale.ply").write_text("left from an earlier take")
    shares = body_parts.write_surfaces(mesh, names, tmp_path)
    assert sorted(path.stem for path in tmp_path.glob("*.ply")) == ["bottom", "top"]
    assert shares == {"bottom": 0.5, "top": 0.5}  # a cube's six faces split three and three by height
    with pytest.raises(SystemExit, match="no body"):
        body_parts.write("any-b1", "/nowhere", "no-such-take", LAID_SIZE, IDENTITY, tmp_path / "never")


# ---- the scene package and the outdoor route -----------------------------------------------------------------------

INVENTORY = {"rows": [{"id": "crate", "count": 2}, {"id": "cable_run", "count": 1}]}


def a_run(folder):
    """A finished route run of two models: a generated crate laid twice, a code cable laid once, front up."""
    made = folder / "work" / "made"
    made.mkdir(parents=True)
    for name, size in (("crate", (1.0, 1.0, 1.0)), ("cable_run_2", (2.0, 0.1, 0.06))):
        box = trimesh.creation.box(extents=size)
        box.visual = trimesh.visual.TextureVisuals(uv=np.zeros((len(box.vertices), 2)),
                                                   material=trimesh.visual.material.SimpleMaterial())
        files = box.export(file_type="gltf")
        gltf = json.loads(files.pop("model.gltf"))
        for index, buffer in enumerate(gltf["buffers"]):
            (made / f"{name}_{index}.bin").write_bytes(files[buffer["uri"]])
            buffer["uri"] = f"{name}_{index}.bin"
        (made / f"{name}.gltf").write_text(json.dumps(gltf))
    planned = {"scene": "yard", "take": "r1", "frame": "x across, z along, y up", "on_seat": [0.0, 0.0],
               "children": [],
               "models": {"crate": {"kind": "yard_crate", "route": "model", "size": [1.0, 1.0, 1.0]},
                          "cable_run_2": {"kind": "yard_cable_run", "route": "code", "size": [2.0, 0.1, 0.06],
                                          "tilt": 90.0}},
               "pieces": [{"model": "crate", "row": "crate", "spot": {"x": 1.0, "z": 2.0, "facing": 90}},
                          {"model": "crate", "row": "crate", "spot": {"x": -1.0, "z": 0.0, "scale": 0.5}},
                          {"model": "cable_run_2", "row": "cable_run", "spot": {"x": 0.0, "z": 0.0, "facing": 0}}]}
    work = folder / "work"
    (work / "plan-route.json").write_text(json.dumps(planned))
    (work / "checks.json").write_text(json.dumps({"crate": {"pass": True}, "cable_run_2": {"pass": True}}))
    (made / "report-chunky1.json").write_text(json.dumps({"crate": {"triangles": 12}}))
    return work


def test_a_copy_lands_on_its_spot_facing_its_way(tmp_path):
    """A facing of 90 turns the front (-z) to +x; a cable tilted 90 degrees lands its middle on its spot (its 0.06 m
    side up, so half of it over the ground, its 0.1 m side along z); a sound package matches its inventory."""
    front = package.turned(90.0, 0.0, 1.0) @ np.array([0.0, 0.0, -1.0])
    assert np.allclose(front, [1.0, 0.0, 0.0]), front
    at = package.standing_at({"size": [2.0, 0.1, 0.06], "tilt": 90.0}, {"x": 0.0, "z": 0.0, "facing": 0.0})
    assert np.allclose(at, [0.0, 0.03, -0.05]), at
    out = tmp_path / "out"
    scene = package.write("yard", a_run(tmp_path), out)
    assert package.problems(out, INVENTORY) == []
    assert len(scene["instances"]) == 3 and (out / "objects/crate.gltf").is_file()
    matrix = np.array(scene["instances"][0]["matrix"]).reshape(4, 4).T
    assert np.allclose(matrix[:3, 3], [1.0, 0.0, 2.0])


def test_a_package_that_does_not_match_its_inventory_is_refused(tmp_path):
    out = tmp_path / "out"
    package.write("yard", a_run(tmp_path), out)
    (out / "objects" / package.model_files(out / "objects/crate.gltf")[0]).unlink()
    scene = json.loads((out / "scene.json").read_text())
    scene["objects"]["cable_run_2"]["check"]["pass"] = False
    (out / "scene.json").write_text(json.dumps(scene))
    found = package.problems(out, {"rows": [{"id": "crate", "count": 3}, {"id": "cable_run", "count": 1}]})
    assert any("crate" in line and "missing" in line for line in found), found
    assert any("failed its model check" in line for line in found), found
    assert any("row crate" in line for line in found), found
    work = a_run(tmp_path / "second")
    (work / "checks.json").write_text(json.dumps({"crate": {"pass": False}, "cable_run_2": {"pass": True}}))
    with pytest.raises(SystemExit, match="crate"):
        package.write("yard", work, tmp_path / "second" / "out")


def test_a_report_no_current_job_names_is_not_read(tmp_path):
    (tmp_path / "made").mkdir()
    (tmp_path / "job-kit-shell_1.json").write_text(json.dumps({"report": "report-shell_1.json"}))
    (tmp_path / "made/report-shell_1.json").write_text(json.dumps({"pieces": {"ring_3": {"bounds": [[-1.3], [1.3]]}}}))
    (tmp_path / "made/report-shell_3.json").write_text(json.dumps({"pieces": {"ring_3": {"bounds": [[-1.2], [1.2]]}}}))
    assert package.made_reports(tmp_path) == {"ring_3": {"bounds": [[-1.3], [1.3]]}}
    (tmp_path / "job-kit-shell_1.json").unlink()
    assert set(package.made_reports(tmp_path)) == {"ring_3"}, "with no jobs, every report is read"


def test_the_finish_turn_lays_a_raw_still_facing_plus_z_as_its_final_stands(tmp_path, monkeypatch):
    """A raw model image-to-3dlab left facing +Z (its stamp) is turned back half round by the finish on its own
    machine; only the slimmed and final files come back. The finish's turn, replayed here, lays the raw as it lies
    here on its final model: a tilted stool laid on its side otherwise (garage's, 2026-10-29)."""
    monkeypatch.setattr(labels, "PIXAL", tmp_path)
    import glb_file
    tilt = trimesh.transformations.rotation_matrix(math.radians(27), [1, 0, 0])[:3, :3]
    upright = trimesh.creation.box([0.5, 0.87, 0.3])
    upright.vertices = upright.vertices + [0.1, 0.0, 0.0]  # off its middle, so a half turn shows
    raw = upright.copy()
    raw.vertices = (raw.vertices @ tilt.T) @ labels.HALF_TURN.T  # as image-to-3dlab left it: tilted, facing +Z
    raw.export(tmp_path / "stool_1.glb")
    document, views = glb_file.read(tmp_path / "stool_1.glb")
    document["asset"]["extras"] = {labels.FACING_KEY: "+Z"}
    glb_file.write(document, views, tmp_path / "stool_1.glb")
    slimmed = raw.copy()
    slimmed.vertices = slimmed.vertices @ labels.HALF_TURN.T  # turned back before the finish slimmed it
    slimmed.export(tmp_path / "stool_1-5000.glb")
    document, views = glb_file.read(tmp_path / "stool_1-5000.glb")
    turn = glb_file.upright_turn(glb_file.positions(document, views))
    glb_file.turned(document, views, turn)
    whole = glb_file.level_turn(*glb_file.faces(document, views)) @ turn
    final = slimmed.copy()
    final.vertices = final.vertices @ whole.T
    final.export(tmp_path / "stool_1-final.glb")
    laid = np.asarray(raw.vertices) @ labels.finish_turn("stool_1").T
    assert np.allclose([laid.min(0), laid.max(0)], final.bounds, atol=1e-3), (laid.min(0), laid.max(0), final.bounds)


def test_place_route_reads_a_turn_as_its_yaw_and_splits_a_long_take(tmp_path):
    for yaw in (0.0, 90.0, 115.0, 270.0):
        angle = math.radians(yaw)
        turn = [math.cos(angle), 0.0, math.sin(angle), 0.0, 1.0, 0.0, -math.sin(angle), 0.0, math.cos(angle)]
        assert abs(place_route.yaw_of(turn) - yaw) < 1e-6, yaw
    source = tmp_path / "leg"
    source.mkdir()
    trimesh.creation.box(extents=(0.2, 0.2, 2.4)).subdivide().subdivide().subdivide().export(source / "steel.ply")
    (source / "labels.json").write_text("{}")
    axis, middle = place_route.split(source, tmp_path / "a", tmp_path / "b")
    assert axis == 2 and abs(middle) < 1e-6
    for half in ("a", "b"):
        bounds = trimesh.load(tmp_path / half / "steel.ply").bounds
        assert bounds[1][2] - bounds[0][2] < 1.3, half
    assert place_route.styled_as("wreck") == "wreck"  # the old inventories are retired (2026-10-21)


# ---- painting by parts ---------------------------------------------------------------------------------------------

def seat():
    """A seat-sized box, finely divided (about 12,000 faces)."""
    box = trimesh.creation.box(extents=(0.5, 0.1, 0.5))
    for _ in range(5):
        box = box.subdivide()
    return box


def blotched(mesh):
    """Forty 2 cm blotches of a second paint scattered over the mesh (the greenhouse chair's seat, round two)."""
    painted = np.zeros(len(mesh.faces), dtype=int)
    rng = np.random.default_rng(1)
    for middle in mesh.triangles_center[rng.choice(len(mesh.faces), 40, replace=False)]:
        painted[np.linalg.norm(mesh.triangles_center - middle, axis=1) < 0.02] = 1
    return painted


def patched_panel():
    """A panel with tape patches on it, as the power unit's side: each patch a finish region of the close-up."""
    mesh = seat()
    middles = mesh.triangles_center
    found = np.zeros(len(mesh.faces), dtype=int)
    corners = [(x, z) for x in (-0.18, -0.06, 0.06, 0.18) for z in (-0.18, -0.06, 0.06, 0.18)]
    for number, (x, z) in enumerate(corners, start=1):
        patch = (np.abs(middles[:, 0] - x) < 0.035) & (np.abs(middles[:, 2] - z) < 0.025) & (middles[:, 1] > 0.04)
        found[patch] = number
    return mesh, found


def test_patchy_paint_fails_and_paint_by_part_or_region_passes():
    mesh = seat()
    assert patchy.score(mesh, np.zeros(len(mesh.faces), dtype=int))["pass"]  # one material
    found = patchy.score(mesh, blotched(mesh))
    assert not found["pass"] and found["stray"] > patchy.STRAY_LIMIT, found
    knob = trimesh.creation.icosphere(subdivisions=2, radius=0.01)
    knob.apply_translation((0.0, 0.07, 0.0))  # a piece of its own in another material is a part, not a blotch
    joined = trimesh.util.concatenate([mesh, knob])
    painted = np.r_[np.zeros(len(mesh.faces), dtype=int), np.ones(len(knob.faces), dtype=int)]
    assert patchy.score(joined, painted)["stray"] == 0.0
    panel, patches = patched_panel()
    taped = (patches > 0).astype(int)
    assert not patchy.score(panel, taped)["pass"]  # without the regions, small patches read as stray paint
    assert patchy.score(panel, taped, regions=patches)["pass"]
    assert not patchy.score(panel, blotched(panel), regions=np.zeros(len(panel.faces), dtype=int))["pass"]


def two_blocks():
    """Two blocks standing on each other, joined into one surface: a base and a smaller lid on it."""
    base = trimesh.creation.box(extents=(0.4, 0.2, 0.4))
    lid = trimesh.creation.box(extents=(0.3, 0.05, 0.3))
    lid.apply_translation((0.0, 0.125, 0.0))
    mesh = trimesh.util.concatenate([base, lid])
    for _ in range(4):
        mesh = mesh.subdivide()
    return labels.welded(mesh)


def test_a_noisy_vote_settles_into_whole_parts():
    """The splitter's vote, wrong on a fifth of the faces at random, settles to the true parts (the lid over y 0.1)
    on the model's own surfaces; a crumb of one part inside another is taken into the part round it."""
    mesh = two_blocks()
    truth = (mesh.triangles_center[:, 1] > 0.1).astype(int)
    noisy = np.where(np.random.default_rng(2).random(len(truth)) < 0.2, 1 - truth, truth)
    scores = np.eye(2)[noisy]
    part_of, clear = labels.by_regions(mesh, scores, labels.smoothed_parts(scores, labels.neighbour_matrix(mesh)))
    assert clear > labels.CLEAR_LEAST
    assert mesh.area_faces[part_of != truth].sum() / mesh.area < 0.02
    crumb = truth.copy()
    crumb[np.argsort(np.linalg.norm(mesh.triangles_center - [0.0, -0.1, 0.0], axis=1))[:6]] = 1  # under the base
    settled = labels.without_crumbs(mesh, crumb)
    assert (settled == truth).all() and patchy.score(mesh, settled)["stray"] == 0.0


def test_a_part_takes_one_material_by_its_lit_colour_or_the_judge():
    """A part half in deep shade takes the material its lit side shows; a part the judge named takes that one."""
    mesh = two_blocks()
    part_of = (mesh.triangles_center[:, 1] > 0.1).astype(int)
    blue, grey = labels.lab(np.array([0.2, 0.3, 0.6])), labels.lab(np.array([0.55, 0.55, 0.55]))
    colours = np.where(part_of[:, None] == 1, blue, grey).astype(float)
    colours[np.random.default_rng(3).random(len(colours)) < 0.5, 0] *= 0.35
    materials = {"seat": {"colour": [0.03, 0.06, 0.32]}, "steel": {"colour": [0.27, 0.27, 0.27]},
                 "rubber": {"colour": [0.01, 0.01, 0.01]}}
    chosen, _, names = labels.paint_parts(mesh, colours, part_of, materials)
    assert [names[index] for index in chosen] == ["steel", "seat"]
    flat = seat()
    colours = np.tile(grey, (len(flat.faces), 1))
    materials = {"vinyl": {"colour": [0.02, 0.03, 0.12]}, "steel": {"colour": [0.3, 0.3, 0.3]}}
    one_part = np.zeros(len(flat.faces), dtype=int)
    chosen, _, names = labels.paint_parts(flat, colours, one_part, materials)
    assert names[chosen[0]] == "steel"
    chosen, about, names = labels.paint_parts(flat, colours, one_part, materials, {0: ("vinyl", "seat cushion")})
    assert names[chosen[0]] == "vinyl" and about[0]["judged"] == "seat cushion"


def test_the_judge_may_not_put_a_saturated_finish_on_a_colourless_region():
    """The aft section's white band, called a thermal blanket, may not take the gold one; a gold region may."""
    materials = {"white": {"colour": [0.8, 0.8, 0.8]}, "gold": {"colour": [0.6, 0.35, 0.05]}}
    centres = np.array([[70.0, 0.0, 2.0], [60.0, 5.0, 40.0]])
    found, set_aside = labels.region_materials(centres, np.array([3.0, 40.0]),
                                               {0: ("gold", "blanket"), 1: ("gold", "foil")}, materials)
    assert found.tolist() == [0, 1] and set_aside == [0]


def test_repeated_asks_decide_by_majority(tmp_path):
    """Three asks of a part: two naming M1 win; one each for M1 and M2 and a reply cut in its thinking is unknown; a
    single old ask is taken as before; a material's colour is put in plain words."""
    names = ["vinyl", "steel"]

    def reply(code):
        return f"<think>...</think>{{\"part\": \"seat\", \"material\": \"{code}\"}}" if code else "<think> and on"
    for part, codes in enumerate((["M1", "M2", "M1"], ["M1", "M2", None], ["M2"])):
        for number, code in enumerate(codes):
            (tmp_path / f"t-part{part:02d}{'.r%d' % number if number else ''}.txt").write_text(reply(code))
    (tmp_path / "t-part010.txt").write_text(reply("M2"))  # another part's file, not a repeat of part 01
    assert part_judge.judged(tmp_path, "t", 3, names) == {0: ("vinyl", "seat"), 2: ("steel", "seat")}
    assert part_judge.unknown(tmp_path, "t", 3, names) == [1]
    assert part_judge.colour_words([0.03, 0.012, 0.004]) == "dark brown"
    assert part_judge.colour_words([0.2, 0.2, 0.2]) == "grey"
    assert part_judge.colour_words([0.9, 0.9, 0.9]) == "white"


def test_a_lost_main_colour_or_flat_or_bare_paint_is_stripped():
    """Half the close-up gold, half white: painted all white it is stripped, gold where gold it passes; a grey seat
    the judge named vinyl (blue here) passes; gold paint drawn as bare steel fails; of two materials whose baked
    colours meet, the one the labels hardly use is left out."""
    mesh = seat()
    gold, white = np.array([60.0, 5.0, 40.0]), np.array([78.0, 0.0, 1.0])
    grey, blue = np.array([55.0, 0.0, 0.0]), np.array([45.0, -2.0, -20.0])
    half = mesh.triangles_center[:, 0] < 0
    colours = np.where(half[:, None], gold, white)
    one = patchy.stripped(colours, np.zeros(len(mesh.faces), dtype=int), [white[None], gold[None]], ["white", "gold"])
    two = patchy.stripped(colours, half.astype(int), [white[None], gold[None]], ["white", "gold"])
    assert not one["pass"] and one["lost"][0]["painted"] == "white", one
    assert two["pass"] and two["materials_seen"] == 2, two
    every = np.ones(len(mesh.faces), dtype=bool)
    seat_and_base = patchy.stripped(np.where(half[:, None], grey, white), half.astype(int), [blue[None], white[None]],
                                    ["vinyl", "steel"], judged=half)
    assert seat_and_base["pass"], seat_and_base
    flat = patchy.stripped(colours, np.zeros(len(mesh.faces), dtype=int), [white[None], gold[None]],
                           ["white", "gold"], judged=every)
    assert flat["flat"] and not flat["pass"], flat
    bare = patchy.stripped(colours, half.astype(int), [white[None], grey[None]], ["white", "bare_steel"],
                           judged=every, bare=["bare_steel"])
    assert not bare["pass"] and bare["lost"][0]["why"] == "bare where the close-up shows paint", bare
    steel, other = np.array([[60.0, 0.0, 0.0]]), np.array([[30.0, 20.0, 20.0]])
    palettes, twins = [steel, steel + 1.0, other], ["bare_steel", "painted_panel", "rubber"]
    assert patchy.twins_left_out(palettes, twins, {"bare_steel": 0.001, "painted_panel": 0.99, "rubber": 0.01}) == [0]
    assert patchy.twins_left_out(palettes, twins, None) == []


def test_a_worn_edge_is_wear_not_a_second_material():
    """Faces whose colour the material round them explains (a worn edge showing bare metal) are that material."""
    mesh = seat()
    distances = np.zeros((len(mesh.faces), 2))
    distances[:, 1] = 30.0
    edge = (np.abs(mesh.triangles_center[:, 0]) > 0.235) & (np.abs(mesh.face_normals[:, 0]) < 0.5)
    distances[edge] = [6.0, 2.0]  # nearer the second material, yet within the first's reach
    assert (patchy.worn_as_around(mesh, distances) == 0).all()


def test_a_patch_on_a_panel_is_its_own_region():
    """The smallest mask over a pixel wins (a patch on a panel is the patch); a mask over most of the object is not a
    region; an object pixel no mask covers takes the nearest region."""
    inside = np.zeros((40, 40), dtype=bool)
    inside[5:35, 5:35] = True
    panel = inside.copy()
    panel[5:35, 20:35] = False  # the left half
    patch = np.zeros_like(inside)
    patch[8:14, 8:14] = True
    found = regions.region_map(np.array([inside, panel, patch]), inside)
    assert len(np.unique(found[inside])) == 2 and (found[~inside] == -1).all()
    assert found[10, 10] != found[20, 20] and found[20, 30] == found[20, 20]
    colours = np.zeros((40, 40, 3))
    colours[patch] = [55.0, 5.0, 30.0]
    assert regions.medians(found, colours)[found[10, 10]].tolist() == [55.0, 5.0, 30.0]


def test_the_surface_check_sees_gold_on_white_and_two_finishes_as_one():
    """Gold over a white band fails; soft blue vinyl over a grey seat passes; a gold and a white region given one
    surface collapse; a shaded interior takes a dark surface, not a light one; an undrawn region is unknown."""
    regions_map = np.zeros((20, 20), dtype=int)
    regions_map[:, 10:] = 1
    landed = np.ones((20, 20), dtype=bool)
    white, gold, grey = np.array([80.0, 0.0, 2.0]), np.array([60.0, 6.0, 35.0]), np.array([55.0, 0.0, 1.0])
    soft_blue, dark = np.array([45.0, -2.0, -15.0]), np.array([20.0, 1.0, 1.0])
    names = ["white", "gold", "blue"]
    surfaces = np.array([white, gold, soft_blue])
    drawn = np.ones((20, 20), dtype=int)  # gold everywhere
    found = surface_check.check(drawn, landed, regions_map, np.array([white, gold]), surfaces, names)
    assert not found["pass"] and [entry["verdict"] for entry in found["regions"]] == ["fail", "pass"], found
    assert found["collapsed"] and found["collapsed"][0]["families"] == ["neutral", "warm"]
    drawn[:] = 2
    assert surface_check.check(drawn, landed, regions_map, np.array([grey, grey]), surfaces, names)["pass"]
    all_first = np.zeros((20, 20), dtype=int)
    assert surface_check.check(all_first, landed, regions_map, np.array([dark, white]), surfaces,
                               names)["regions"][0]["verdict"] == "fail"
    assert surface_check.check(all_first, landed, regions_map, np.array([dark, white]),
                               np.array([dark, gold, soft_blue]), names)["regions"][0]["verdict"] == "pass"
    landed[:, 10:] = False
    unknown = surface_check.check(drawn, landed, regions_map, np.array([grey, grey]), surfaces, names)
    assert not unknown["pass"] and unknown["regions"][1]["verdict"] == "unknown", unknown


def bake_smoothing():
    """bake.py's normal smoothing (smoothing_rounds, smoothed_normals and their settings), taken from its text: bake.py
    runs inside Blender."""
    tree = ast.parse((HERE / "inside/bake.py").read_text())
    names = {"SMOOTH_REACH", "SMOOTH_CREASE", "SMOOTH_ROUNDS_MOST"}
    kept = [node for node in tree.body if isinstance(node, ast.Assign) and node.targets[0].id in names
            or isinstance(node, ast.FunctionDef) and node.name in ("smoothing_rounds", "smoothed_normals")]
    space = {"math": math, "np": np}
    exec(compile(ast.Module(body=kept, type_ignores=[]), "bake", "exec"), space)
    return space


def test_a_lumpy_face_is_smoothed_and_a_real_edge_kept():
    """The materials fix (2026-10-18): a 0.5 m box's faces tilted at random up to 15 degrees settle back within 5
    degrees of their side, and no face beside the box's edges bends toward the other side."""
    smoothing = bake_smoothing()
    box = trimesh.creation.box(extents=(0.5, 0.5, 0.5))
    for _ in range(5):
        box = box.subdivide()
    true = box.face_normals.copy()
    tilt = np.random.default_rng(3).normal(size=true.shape) * math.radians(15.0) / 2
    lumpy = true + tilt - (tilt * true).sum(1, keepdims=True) * true
    lumpy /= np.linalg.norm(lumpy, axis=1, keepdims=True)
    rounds = smoothing["smoothing_rounds"](box.area_faces)
    smoothed = smoothing["smoothed_normals"](lumpy, box.area_faces, box.face_adjacency.T, rounds)
    off = np.degrees(np.arccos(np.clip((smoothed * true).sum(1), -1.0, 1.0)))
    before = np.degrees(np.arccos(np.clip((lumpy * true).sum(1), -1.0, 1.0)))
    assert np.percentile(before, 90) > 10.0, "the lumps are there to smooth"
    assert np.percentile(off, 90) < 5.0, f"lumps left: 90% within {np.percentile(off, 90):.1f} degrees"
    assert off.max() < 20.0, f"a face beside an edge bent {off.max():.1f} degrees toward the other side"


# ---- the part splitters' scores ------------------------------------------------------------------------------------

def slab():
    """A flat slab, finely divided, one finish on x < 0 and another on x > 0."""
    box = trimesh.creation.box(extents=(1.0, 0.1, 1.0))
    for _ in range(4):
        box = box.subdivide()
    return box, (box.triangles_center[:, 0] > 0).astype(int)


def test_predicted_colours_and_voxels_become_face_parts():
    palette = split_compare.PALETTE[:40].astype(float)
    spacing = np.linalg.norm(palette[:, None] - palette[None], axis=2)
    spacing[spacing == 0] = np.inf
    assert spacing.min() > 60, spacing.min()
    rng = np.random.default_rng(1)
    centres = np.array([(200, 40, 40), (40, 200, 40)], dtype=float)
    truth = rng.integers(0, 2, 4000)
    found = split_compare.grouped_colours(np.clip(centres[truth] + rng.normal(0, 5, (4000, 3)), 0, 255))
    assert len(np.unique(found)) == 2 and abs(np.corrcoef(found, truth)[0, 1]) > 0.99
    mesh, finish = slab()
    centre, scale = (mesh.bounds[0] + mesh.bounds[1]) / 2, 0.99999 / float(np.ptp(mesh.bounds, axis=0).max())
    points = (mesh.sample(20000, seed=0) - centre) * scale
    coords = np.unique(np.floor((points + 0.5) * split_compare.GRID).astype(int), axis=0)
    voxel_part = ((coords[:, 0] + 0.5) / split_compare.GRID - 0.5 > 0).astype(int)
    assert (split_compare.voxel_parts_on_faces(mesh, coords, voxel_part, centre, scale) == finish).mean() > 0.97


def test_a_split_along_the_finishes_scores_above_one_part():
    mesh, finish = slab()
    owned, missed = split_compare.finishes_owned(mesh.area_faces, finish, finish)
    assert owned == [0, 1] and not missed
    owned, missed = split_compare.finishes_owned(mesh.area_faces, finish, np.zeros(len(finish), dtype=int))
    assert missed == [0, 1]
    wasted, cut = split_compare.needless_cuts(mesh, np.zeros(len(finish), dtype=int), finish)
    assert wasted > 0.2 and cut >= 1  # one finish cut in two on a smooth face
    assert split_compare.needless_cuts(mesh, finish, finish) == (0, 0)
    pixels = np.repeat(np.array([[0, 0, 1, 1]]), 4, axis=0)
    following = split_compare.region_agreement(pixels.copy(), pixels, np.array([0, 1]))
    one_part = split_compare.region_agreement(np.zeros_like(pixels), pixels, np.array([0, 1]))
    assert following["agreement"] == 1.0 and one_part["pure"] == 0.5


def test_region_agreement_takes_a_region_the_split_misses():
    pixels = np.repeat(np.array([[0, 0, 1, 2]]), 4, axis=0)
    rendered = np.where(pixels == 2, -1, 0)  # the last region is never drawn (the hanging glove, 2026-10-10)
    found = split_compare.region_agreement(rendered, pixels, np.array([0, 0, 0]))
    assert found == {"whole": 1.0, "pure": 1.0, "agreement": 1.0}


def test_the_spread_matches_regions_and_counts_only_counted_finishes(tmp_path):
    """A 10 x 10 close-up, region 0 on 60 object pixels and region 1 on 4: shares 60/64 and 4/64; a painting matches
    only with that count and those shares; the owned share counts owned and missed finishes only."""
    pixels = np.full((10, 10), -1)
    pixels[1:9, 1:9] = 0
    pixels[1:3, 1:3] = 1
    assert np.allclose(split_spread.region_shares(pixels), [60 / 64, 4 / 64])
    painted = [{"share": round(60 / 64, 3)}, {"share": round(4 / 64, 3)}]
    assert split_spread.same_regions(painted, pixels)
    assert not split_spread.same_regions(painted[:1], pixels)
    assert not split_spread.same_regions([{"share": 0.9}, {"share": 0.1}], pixels)
    assert split_spread.owned_share({"owned": [0, 2], "missed": [1]}) == 2 / 3
    assert split_spread.owned_share({"owned": [], "missed": []}) is None
    (tmp_path / "take").mkdir()
    split_spread.write_finishes(tmp_path, "take", ["steel", "paint", "steel"], "test")
    indices, names = split_spread.finish_indices(tmp_path, "take")
    assert names == ["paint", "steel"] and indices.tolist() == [1, 0, 1]
    line = split_spread.spread_line("owned", [0.0, 0.5, 1.0, None])
    assert "n=3" in line and "mean 0.500" in line and "min 0.000" in line and "max 1.000" in line
    assert split_spread.spread_line("owned", [None]).endswith("none")


# ---- straightness --------------------------------------------------------------------------------------------------

def locker():
    """A tall locker's box, 1.2 x 2.0 x 0.55, finely divided so it can bend."""
    box = trimesh.creation.box(extents=(1.2, 2.0, 0.55))
    for _ in range(4):
        box = box.subdivide()
    return box


def test_a_square_piece_must_come_out_straight():
    """A square box passes; leant atan(0.12) = 6.84 degrees over (round four's locker leant 13) its sides read that
    tilt and it fails; with its front bowed 10 cm it fails."""
    assert straight.straightness(locker())["pass"]
    leaning = locker()
    leaning.vertices[:, 0] += leaning.vertices[:, 1] * 0.12
    found = straight.straightness(leaning)
    assert not found["pass"] and abs(found["sides"]["right"]["tilt"] - math.degrees(math.atan(0.12))) < 0.1
    bowed = locker()
    front = bowed.vertices[:, 2] < -0.27
    bowed.vertices[front, 2] -= 0.1 * np.cos(bowed.vertices[front, 1] * np.pi / 2.0)
    assert not straight.straightness(bowed)["pass"]



def test_feet_are_the_clusters_every_pair_within_reach_gives_without_listing_the_pairs():
    """feet.linked numbers clusters exactly as connected_components over every pair within reach (query_pairs) does,
    on scattered points with near-misses at the reach itself, without building those pairs (the vehicle lift's wide
    base: 28 GB of pairs)."""
    from scipy import sparse
    from scipy.sparse.csgraph import connected_components
    from scipy.spatial import cKDTree
    import feet
    generator = np.random.default_rng(3)
    for scale, count in ((1.0, 400), (0.2, 900), (5.0, 300)):
        flat = generator.uniform(0, scale, (count, 2))
        flat[1] = flat[0] + [0.05, 0.0]  # a pair exactly at the reach joins, as query_pairs joins it
        pairs = cKDTree(flat).query_pairs(0.05, output_type="ndarray")
        _, expected = connected_components(sparse.coo_matrix((np.ones(len(pairs)), (pairs[:, 0], pairs[:, 1])),
                                                             shape=(count, count)), directed=False)
        assert np.array_equal(feet.linked(flat, 0.05), expected), scale
