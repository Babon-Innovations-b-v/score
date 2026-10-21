"""The surface stage's framework side: the finish registry keeps each proposed library surface as first proposed, the
per-place data names each take once world-wide and every model a place lays that another place claims is baked by
that place, every place's line is rows of world 1's table, the paint takes the method's surface and records its
proposal, and a gate that cannot read what it needs, or a model whose finish map never settled, blocks with a reason on
that model instead of crashing or passing. No cloud, no paid step.

Run: .venv/bin/python score/stages/surfaces/surfaces_test.py
"""
import inspect
import json
import os
import pathlib
import shutil
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from score import checks, graph, stages  # noqa: E402
from score.stages import shapes_first, surfaces  # noqa: E402
from score.stages.surfaces import registry, surface_data, surface_gates  # noqa: E402
from score.store import Store  # noqa: E402
import score.stages.props.prop_data as prop_data  # noqa: E402

# These tests hold the data/props and data/surfaces places; a designed place's hand-in (the home's design/, which
# the sandbox links) is prepare_test.py's, so none is read here.
import score.stages.surfaces  # noqa: E402
prop_data.DESIGN = surface_data.DESIGN = pathlib.Path(tempfile.mkdtemp()) / "no design"
score.stages.surfaces.data.DESIGN = surface_data.DESIGN  # the table's own import of it (bare `surface_data`)


def a_store():
    return Store.in_folder(tempfile.mkdtemp())


def test_a_proposed_library_surface_stands_as_first_proposed():
    store = a_store()
    first = registry.Registry(store).propose_surface("Aluminium tape, silver", {"stands_in": "galvanized_dull"},
                                                     {"take": "a"})
    second = registry.Registry(store).propose_surface("Aluminium tape, silver", {"stands_in": "bare_steel"},
                                                      {"take": "b"})
    assert first["spec"] == second["spec"] == {"stands_in": "galvanized_dull"}
    assert len(store.registry("surfaces")) == 1


def test_names_alike_but_for_case_stand_as_one_entry():
    store = a_store()
    first = registry.Registry(store).propose_surface("Polished Chrome", {"stands_in": "pipe_steel"}, {"take": "a"})
    second = registry.Registry(store).propose_surface("polished chrome", {"stands_in": "bare_steel"}, {"take": "b"})
    assert second == first and len(store.registry("surfaces")) == 1
    other = registry.Registry(store).propose_surface("Polished brass", {"stands_in": "brass"}, {"take": "c"})
    assert other["name"] == "Polished brass" and len(store.registry("surfaces")) == 2


def test_the_paint_takes_the_method_s_surface_and_records_its_proposal():
    store = a_store()
    rows = [{"part": 0, "judge": "dark_panel", "proposed": None},
            {"part": 1, "judge": "galvanized_dull", "proposed": {"name": "aluminium tape", "description": "shiny",
                                                                  "why": "thinner than steel"}}]
    found = surfaces.place_line.method_surfaces("power_unit-r3", "old_station", rows, registry.Registry(store))
    assert [record["surface"] for record in found] == ["dark_panel", "galvanized_dull"]
    assert found[1]["proposed"]["stands_in"] == "galvanized_dull" and found[1]["proposed"]["status"] == "proposed"
    assert [entry["name"] for entry in store.registry("surfaces")] == ["aluminium tape"]


def test_each_take_is_painted_by_one_place_and_every_claim_is_baked_by_its_place():
    owner = {}
    records = {path.stem: json.loads(path.read_text()) for path in sorted(surface_data.FOLDER.glob("*.json"))}
    for place, record in records.items():
        assert (REPO / "data/kit" / f"{place}.json").exists() or shapes_first.no_place(place), f"{place}: no such place"
        assert record["takes"] or record.get("nothing"), f"{place}: lists nothing to paint and says not why"
        assert surface_data.paints(place) == bool(record["takes"]), place
        for take, entry in record["takes"].items():
            assert take not in owner, f"{take}: painted by {owner.get(take)} and {place}"
            owner[take] = place
            assert {"place", "kind", "object", "library_places"} <= set(entry), f"{place} {take}"
        bake = record.get("bake")
        if bake:
            assert set(bake["models"].values()) <= set(record["takes"]), f"{place}: bakes a take it does not paint"
    for place, record in records.items():
        for model, claim in record.get("elsewhere", {}).items():
            other = records[claim["place"]]
            assert claim["take"] in other["takes"], f"{place} {model}: {claim['place']} does not paint {claim['take']}"
            assert claim["take"] in other["bake"]["models"].values(), f"{place} {model}: {claim['place']} bakes none"


def test_every_place_s_surface_line_is_rows_of_world_one():
    names = [stage.name for stage in stages.STAGES]
    assert {"finish-route-palette", "surface-library", "finish-route-views", "finish-route-list", "finish-route-split",
            "surfaces-parts", "surfaces-paint", "surfaces-bake", "finish-route-recheck", "surfaces-check"} <= set(names)
    rows = {stage.name: stage for stage in surfaces.ROWS}
    assert all(stage.grain == "place" for stage in surfaces.ROWS)
    # the scene's surfaces made fresh from its palette before anything is listed (owner, 2026-10-21)
    assert set(rows["surface-library"].after) == {"finish-route-palette"}
    for row in ("finish-route-list", "surfaces-parts", "finish-route-recheck", "surfaces-check"):
        assert "surface-library" in rows[row].after, row
    # the method's interface, painted in the bake at the scene palette's wear and dirt (read from its design)
    assert set(rows["surfaces-bake"].after) == {"finish-route-palette", "surface-library", "surfaces-parts"}
    assert set(rows["surfaces-paint"].after) == {"surfaces-bake"}  # the bake's painted takes, the paint's gates
    assert all(stage.euros for stage in surfaces.ROWS if stage.paid)


def test_a_method_change_moves_only_the_rows_that_read_the_library():
    """The surface-library row and the finish route's list, parts, paint, bake, recheck and check read the method's
    library (its recipes); its views and split never do, so a recipe's new default makes the scene's surfaces again
    and re-asks the list, and leaves the renders and their regions where they stood (the split reads the list's
    answers: identical answers keep its key, the graph's own test). The palette row reads its wear levels alone."""
    data, home = pathlib.Path(tempfile.mkdtemp()), pathlib.Path(tempfile.mkdtemp())
    for folder in ("library", "definitions"):
        shutil.copytree(REPO / "data" / folder, data / folder)
    (data / "surfaces").mkdir()
    shutil.copy(surface_data.path("greenhouse"), data / "surfaces")
    world = graph.Environment("world1", 1, {"data": str(data), "home": str(home), "repo": str(REPO), "seeds": str(home)})
    runner = graph.Runner(surfaces.ROWS, world, a_store(), model_record=lambda kind: {"kind": kind})
    for stage in surfaces.ROWS:  # each file a row names, written small in the test's own home
        for name in runner.files_of(stage, "greenhouse"):
            path = runner.file_path(stage, name, "greenhouse")
            if not path.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(name)
    before = {stage.name: runner.file_keys(stage, "greenhouse") for stage in surfaces.ROWS}
    library = json.loads((data / "library" / "materials.json").read_text())
    library["recipes"]["rubber"]["roughness"] = 0.8
    (data / "library" / "materials.json").write_text(json.dumps(library))
    moved = {stage.name for stage in surfaces.ROWS if runner.file_keys(stage, "greenhouse") != before[stage.name]}
    assert moved == {"surface-library", "finish-route-list", "surfaces-parts", "surfaces-paint", "surfaces-bake",
                     "finish-route-recheck", "surfaces-check"}, moved
    library["wear_levels"]["scarred"] = 1.0
    (data / "library" / "materials.json").write_text(json.dumps(library))
    palette = next(stage for stage in surfaces.ROWS if stage.name == "finish-route-palette")
    assert runner.file_keys(palette, "greenhouse") != before["finish-route-palette"]
    shutil.rmtree(data)
    shutil.rmtree(home)


def test_a_place_without_data_blocks_before_anything_is_spent_and_one_with_nothing_to_paint_has_no_rows():
    world = graph.Environment("world1", 1, {"data": str(REPO / "data"), "home": tempfile.mkdtemp(), "repo": str(REPO),
                                      "seeds": tempfile.mkdtemp()})
    runner = graph.Runner(surfaces.ROWS, world, a_store(), model_record=lambda kind: {"kind": kind})
    rows = {stage.name: stage for stage in surfaces.ROWS}
    assert "its input surfaces is missing" in runner.node_status(rows["finish-route-views"], "nowhere")
    assert not any(node.endswith("@tube") for node in runner.status(["tube"]))  # code-built pieces only
    try:
        runner.file_keys(rows["surfaces-bake"], "nowhere")
    except graph.Blocked as block:
        assert "nowhere.json" in str(block)
        return
    raise AssertionError("a place with no data did not block at its bake row")


def test_a_gate_that_cannot_read_its_evidence_answers_unknown():
    folder = pathlib.Path(tempfile.mkdtemp())
    def judge_takes(output, inputs, evidence):  # a gate that reads its output's takes.json, as the route's do
        return json.loads((pathlib.Path(output) / "takes.json").read_text())
    check = surface_gates.guarded("views cast", judge_takes)
    found = checks.judge(check, folder, {}, None)
    assert found.answer == checks.UNKNOWN and "takes.json" in found.reason
    shutil.rmtree(folder)


# The seed tray's paper label on black plastic, as baked (greenhouse bake output 439948bc): each of its 65 triangles'
# baked L*a*b*, area (to the largest), the surfaces within its reach (potting_soil, printed_paper, tray_plastic) and
# whether its corners straddle a part border. 19 of them bake the plastic's near black.
SEED_TRAY_PAPER = [
    (79.2, -0.7, 7.6, 0.1987, "011", False),
    (79.2, -0.7, 7.6, 0.8008, "011", False),
    (9.9, 0.7, -0.5, 0.2788, "011", True),
    (79.2, -0.7, 7.6, 0.534, "011", False),
    (9.3, 0.5, -1.4, 0.4221, "011", True),
    (9.9, 0.7, -0.5, 0.1251, "011", True),
    (9.9, 0.7, -0.5, 0.1117, "011", True),
    (9.9, 0.7, -0.5, 0.1437, "011", True),
    (9.9, 0.7, -0.5, 0.4054, "111", True),
    (79.2, -0.7, 7.6, 0.2535, "011", False),
    (9.9, 0.7, -0.5, 0.1022, "011", True),
    (78.8, -0.7, 7.7, 0.8483, "111", False),
    (10.0, 1.2, -0.3, 0.4276, "011", True),
    (77.7, -0.7, 7.7, 0.5298, "011", False),
    (79.2, -0.7, 7.6, 0.3602, "011", False),
    (79.2, -0.7, 7.6, 0.2877, "011", False),
    (78.5, -0.5, 7.2, 0.5201, "011", False),
    (77.0, -0.7, 7.7, 0.2867, "011", False),
    (75.1, -1.1, 7.6, 0.3235, "011", False),
    (79.2, -0.7, 7.6, 0.1694, "011", False),
    (79.2, -0.7, 7.6, 0.676, "011", False),
    (74.5, -0.5, 7.2, 0.0633, "011", False),
    (74.9, -0.5, 7.2, 0.1252, "011", True),
    (20.8, -0.0, 1.4, 0.105, "011", True),
    (72.3, -0.5, 7.3, 0.3978, "011", True),
    (79.2, -0.7, 7.6, 0.226, "011", False),
    (76.7, -0.7, 7.7, 0.608, "011", True),
    (79.2, -0.7, 7.6, 0.7381, "011", True),
    (10.0, 1.2, -0.3, 0.0822, "011", True),
    (74.1, -0.5, 7.2, 0.2326, "011", False),
    (74.1, -0.5, 7.2, 0.1202, "010", False),
    (79.2, -0.7, 7.6, 0.0853, "011", True),
    (79.2, -0.7, 7.6, 0.4938, "011", False),
    (78.1, -0.7, 7.7, 0.3396, "011", False),
    (10.7, 1.7, 1.4, 0.1247, "011", True),
    (75.6, -0.5, 7.2, 0.5145, "011", False),
    (79.2, -0.7, 7.6, 0.896, "011", False),
    (79.2, -0.7, 7.6, 0.1385, "011", False),
    (78.8, -0.7, 7.7, 0.6235, "111", False),
    (9.9, 0.7, -0.5, 0.3203, "111", True),
    (79.2, -0.7, 7.6, 0.1366, "011", False),
    (9.9, 0.7, -0.5, 0.757, "111", True),
    (65.5, -0.5, 6.3, 0.118, "011", False),
    (79.2, -0.7, 7.6, 0.0903, "011", False),
    (9.4, 1.0, -1.2, 0.0811, "011", False),
    (73.0, -0.5, 7.3, 0.4309, "011", True),
    (79.2, -0.7, 7.6, 0.5007, "011", False),
    (10.0, 1.2, -0.3, 0.125, "011", True),
    (9.3, 0.5, -1.4, 0.4311, "011", True),
    (75.6, -0.5, 7.2, 0.3532, "011", False),
    (77.7, -0.7, 7.7, 0.5297, "011", False),
    (78.8, -0.7, 7.7, 0.5839, "011", False),
    (79.2, -0.7, 7.6, 0.1448, "011", True),
    (79.2, -0.7, 7.6, 1.0, "011", False),
    (10.7, 1.7, 1.4, 0.4031, "011", True),
    (10.7, 1.7, 1.4, 0.2377, "011", True),
    (79.2, -0.7, 7.6, 0.098, "011", False),
    (79.2, -0.7, 7.6, 0.6058, "111", True),
    (10.0, 1.2, -0.3, 0.2574, "011", False),
    (74.5, -0.5, 7.2, 0.2059, "011", False),
    (79.2, -0.7, 7.6, 0.1615, "011", False),
    (9.4, 1.0, -1.2, 0.5341, "011", True),
    (77.7, -0.7, 7.7, 0.6325, "011", False),
    (76.3, -0.7, 7.7, 0.4506, "011", False),
    (71.5, -0.5, 7.3, 0.4865, "011", True),
]
SEED_TRAY_SURFACES = [(30.5, 7.6, 15.6), (79.2, -0.7, 7.6), (9.3, 0.5, -1.4)]


def paper_record(rows):
    import numpy as np
    from score.stages.surfaces import bake_check
    colour = np.array([row[:3] for row in rows])
    reach = np.array([[flag == "1" for flag in row[4]] for row in rows])
    share = bake_check.blotch_share(colour, np.array([row[3] for row in rows]), np.ones(len(rows), dtype=bool), reach,
                                    [[surface] for surface in SEED_TRAY_SURFACES])
    return {"surfaces": {"printed_paper": {"share": 0.0117, "baked_lab": [77.7, -0.7, 7.7],
                                           "surface_lab": list(SEED_TRAY_SURFACES[1]), "delta_e": 1.5,
                                           "near_black": share}}}


def test_a_clean_label_border_passes_and_a_black_smudge_along_it_fails():
    from score.stages.surfaces import bake_check
    assert bake_check.surface_faults("seed_tray_1", paper_record(SEED_TRAY_PAPER)) == []
    smudge, area = [], 0.0  # light triangles across the label's border turned black until a tenth of its area
    total = sum(row[3] for row in SEED_TRAY_PAPER)
    for row in SEED_TRAY_PAPER:
        if row[5] and row[0] > bake_check.BLOTCH_L and area < 0.1 * total:
            row, area = (0.0, 0.0, 0.0, *row[3:]), area + row[3]
        smudge.append(row)
    faults = bake_check.surface_faults("seed_tray_1", paper_record(smudge))
    assert len(faults) == 1 and "printed_paper" in faults[0] and "near black" in faults[0], faults
    # the table wraps the make (stages/gaps.py: an accepted gap moves a fault, the wrapper unwraps to the judge); the
    # finish route's check is bake_check's against the bake's specs (route_check.py)
    from score.stages.surfaces import route_check
    assert inspect.unwrap({stage.name: stage for stage in stages.STAGES}["surfaces-check"].make) \
        is route_check.make_check


# The flat's quilt_cotton as the library resolves it (linear RGB): red cotton, ink-line seams as its second.
QUILT_COTTON = {"colour": [0.2542, 0.0782, 0.0648], "second": [0.00304, 0.00273, 0.00243]}


def quilt_record(spec):
    """A quilt baked as its recipe draws it (6% of its area the seams' near black, 94% its red; flat bake of
    2026-10-13), its blotch share measured against `spec`'s colours."""
    import numpy as np
    from score.stages.surfaces import bake_check
    shades = bake_check.library_shades(spec)
    colour = np.array([shades[0]] * 94 + [bake_check.library_shades(QUILT_COTTON)[1]] * 6)
    share = bake_check.blotch_share(colour, np.ones(100), np.ones(100, dtype=bool), np.ones((100, 1), dtype=bool),
                                    [shades])
    return {"surfaces": {"quilt_cotton": {"share": 1.0, "baked_lab": [round(float(value), 1) for value in shades[0]],
                                          "surface_lab": [round(float(value), 1) for value in shades[0]],
                                          "delta_e": 0.0, "near_black": share}}}


def test_a_surfaces_own_drawn_seams_are_not_blotches():
    from score.stages.surfaces import bake_check
    assert bake_check.surface_faults("quilt_1", quilt_record(QUILT_COTTON)) == []
    faults = bake_check.surface_faults("quilt_1", quilt_record({"colour": QUILT_COTTON["colour"]}))
    assert len(faults) == 1 and "near black" in faults[0], faults


def test_a_finish_judged_by_its_own_colour_is_not_compared_with_its_close_up():
    """The garage beacon: its red transparent dome measured pale pink on its brighter half (its highlights and what
    lies behind it), so the paint keeps red_plastic by its own colour; the bake check leaves it out of the close-up
    too. The opaque knob of the same surface is still compared."""
    from score.stages.surfaces import bake_check
    dome = {"finish": "Red transparent plastic", "surface": "red_plastic", "measured_lab": [70.8, 21.2, 11.5],
            "by": "its own colour", "cover": True}
    label = {"finish": "Printed label", "surface": "printed_paper", "measured_lab": [30.0, 5.0, 5.0],
             "by": "its own colour"}  # print off its listed colour: judged by its own colour, still in the close-up
    knob = {"finish": "Red plastic", "surface": "red_plastic", "measured_lab": [40.0, 55.0, 40.0], "by": "the list"}
    with tempfile.TemporaryDirectory() as scratch:
        folder = pathlib.Path(scratch)
        (folder / "labels.json").write_text(json.dumps({"finishes": [dome]}))
        assert bake_check.close_up_colours(folder) == {}
        (folder / "labels.json").write_text(json.dumps({"finishes": [dome, label]}))
        assert bake_check.close_up_colours(folder) == {"printed_paper": [30.0, 5.0, 5.0]}
        (folder / "labels.json").write_text(json.dumps({"finishes": [dome, knob]}))
        assert bake_check.close_up_colours(folder) == {"red_plastic": [40.0, 55.0, 40.0]}
    red = [38.5, 57.0, 47.5]
    assert bake_check.close_up_faults("beacon_1", baked_record({"red_plastic": (1.0, red)}, {})) == []
    faults = bake_check.close_up_faults("beacon_1", baked_record({"red_plastic": (1.0, red)},
                                                                 {"red_plastic": dome["measured_lab"]}))
    assert len(faults) == 1 and "red_plastic" in faults[0], faults


WATER_TANK_CLOSE_UP = {"painted_panel": [80.3, -0.2, 6.0], "bare_steel": [67.3, -0.3, 1.0],
                       "tank_water": [53.2, -3.2, -2.3]}  # the finish-map method's measures, greenhouse, 2026-10-12


def baked_record(surfaces, close_up, degrees=None):
    """A checks.json record of a model baked exactly on its surfaces ({surface: (share, L*a*b*)})."""
    return {"surfaces": {name: {"share": share, "baked_lab": list(colour), "surface_lab": list(colour),
                                "delta_e": 0.0, "near_black": 0.0} for name, (share, colour) in surfaces.items()},
            "close_up": close_up, "seen_degrees": degrees}


# The water tank's surfaces as the greenhouse's library gave them when it was fixed (2026-10-12), L*a*b*: the
# check's measured case, kept as numbers since every old material was retired (2026-10-21).
TANK_SURFACES = {"bare_steel": [66.3, -1.1, -4.5], "tank_water": [41.5, -3.2, -6.9], "cream_paint": [79.2, -0.7, 7.6]}


def test_the_water_tank_s_reversed_greys_fail_and_its_cream_paint_passes():
    from score.stages.surfaces import bake_check
    before = baked_record({"painted_panel": (0.7253, [61.6, -1.5, -6.5]), "bare_steel": (0.1536, [66.3, -1.1, -4.5]),
                           "tank_water": (0.1212, [58.7, -1.7, 2.4])}, WATER_TANK_CLOSE_UP)  # its stored check
    before["seen_degrees"] = 23.83  # 1.4 m wide, 3.3 m from the greenhouse's nearest view
    faults = bake_check.surface_faults("water_tank_1", before)
    # its water bakes 8.9 b* off its paint, 1.9 noticeable differences at that size: told apart, not one look
    assert len(faults) == 1 and "painted_panel is 13.0 L* lighter than bare_steel" in faults[0], faults
    grey_body = baked_record({"painted_panel": (0.7253, [61.6, -1.5, -6.5]),
                              "bare_steel": (0.1536, TANK_SURFACES["bare_steel"]),
                              "tank_water": (0.1212, TANK_SURFACES["tank_water"])}, WATER_TANK_CLOSE_UP, 23.83)
    faults = bake_check.surface_faults("water_tank_1", grey_body)  # the water fixed, the body still grey
    assert len(faults) == 1 and "lighter than bare_steel" in faults[0], faults
    after = baked_record({"cream_paint": (0.7253, TANK_SURFACES["cream_paint"]),
                          "bare_steel": (0.1536, TANK_SURFACES["bare_steel"]),
                          "tank_water": (0.1212, TANK_SURFACES["tank_water"])},
                         {"cream_paint": WATER_TANK_CLOSE_UP["painted_panel"],
                          **{name: WATER_TANK_CLOSE_UP[name] for name in ("bare_steel", "tank_water")}}, 23.83)
    assert bake_check.surface_faults("water_tank_1", after) == [], bake_check.surface_faults("water_tank_1", after)
    one = baked_record({"painted_panel": (1.0, [61.6, -1.5, -6.5])}, {"painted_panel": [80.3, -0.2, 6.0]})
    assert bake_check.surface_faults("panel_1", one) == [], "one surface is one look by design"
    dark = baked_record({"painted_panel": (0.9, [61.6, -1.5, -6.5]), "rubber": (0.1, [9.3, 0.5, -1.4])},
                        {"painted_panel": [61.0, 0.0, 0.0], "rubber": [62.0, 0.0, 0.0]})
    faults = bake_check.surface_faults("cabinet_1", dark)
    assert len(faults) == 1 and "rubber" in faults[0] and "over 32" in faults[0], faults


def test_one_look_fails_only_what_a_viewer_cannot_tell_apart_at_the_place_s_view_distance():
    from score.stages.surfaces import bake_check
    cover = baked_record({"bare_steel": (0.2813, [66.3, -1.1, -4.5]), "hull_white_scorched": (0.7187, [75.6, -1.2, -1.0])},
                         {"hull_white_scorched": [92.7, -0.3, 0.0], "bare_steel": [65.4, 1.6, 5.6]})
    cover["seen_degrees"] = 11.29  # the wreck's access cover, 4.5 m from wreck-home
    assert bake_check.one_look_faults("access_cover", cover) == [], "9.3 L* at 6 degrees is seen"
    fragment = baked_record({"bare_steel": (0.4118, [64.1, -0.8, -3.2]), "galvanized_steel": (0.4758, [68.6, -1.2, -2.2]),
                             "roof_steel_paint": (0.1123, [63.7, -1.0, -2.7])},
                            {"bare_steel": [51.1, 1.9, 7.0], "galvanized_steel": [89.6, -0.2, 3.6],
                             "roof_steel_paint": [49.7, -1.0, 2.8]})
    fragment["seen_degrees"] = 4.71
    faults = bake_check.one_look_faults("fragment", fragment)
    assert len(faults) == 1 and "one grey look" in faults[0], faults
    del fragment["seen_degrees"]
    faults = bake_check.one_look_faults("fragment", fragment)
    assert len(faults) == 1 and "no view distance" in faults[0], "a gate never passes on what it cannot measure"
    assert abs(bake_check.noticed([50, 0, 0], [55.155, 0, 0], 10.0) - 1.0) < 0.01, "ND(50) of L* at 6 degrees"
    desk = [{"model": "models/hub_kit/comms_1.gltf", "at": [2.0, 0.0, 0.0], "yaw": 90.0,
             "children": [{"model": "models/hub_kit/headset_1.gltf", "at": [1.0, 0.5, 0.0]}]}]
    spots = list(bake_check.object_spots(desk, {"headset_1": {"size": [0.2, 0.2, 0.1]}}))
    assert [model for model, _, _ in spots] == ["headset_1"], "a model laid on a desk the kit does not size is found"
    assert [round(value, 6) for value in spots[0][1]] == [2.0, 0.5, -1.0], spots  # turned by the desk's yaw
    models = {"ship_1": {"on": "bay_plate_1"}, "engine_1": {"mounted": {"on": "ship_1", "at": [1, 2, 3]}},
              "engine_2": {"model": "engine_1", "mounted": {"on": "ship_1", "at": [-1, 2, 3]}}}
    spots = list(bake_check.model_spots(models, [{"model": "bay_plate_1", "at": [0.0, 0.0, 12.5]}],
                                        {"ship_1": [9, 5, 31], "engine_1": [1, 1, 2]}))
    assert [(model, spot) for model, spot, _ in spots] == [("ship_1", [0.0, 0.0, 12.5]), ("engine_1", [0.0, 0.0, 12.5]),
                                                          ("engine_1", [0.0, 0.0, 12.5])], spots


def tank_mesh(ends, height=1.6):
    """A tank's (vertices, faces), its own frame (+y up), on four corner legs ending `ends` up (the water tank's
    measured)."""
    import numpy as np
    import trimesh
    body = trimesh.creation.box(bounds=((-0.7, 0.3, -0.7), (0.7, height, 0.7)))
    legs = [trimesh.creation.box(bounds=((across - 0.05, end, along - 0.05), (across + 0.05, 0.3, along + 0.05)))
            for (across, along), end in zip(((-0.6, -0.6), (0.6, -0.6), (-0.6, 0.6), (0.6, 0.6)), ends)]
    mesh = trimesh.util.concatenate([body, *legs])
    return np.asarray(mesh.vertices), np.asarray(mesh.faces)


def test_a_tall_take_s_feet_are_found_in_the_resting_check_s_band():
    """The garage's fluid shelves (2026-10-15): a shelf unit 1.0 tall in its own frame, 2.0 m standing, its bottom
    shelf 0.06 up over four legs, one ending 0.02 up (4 cm). In 15% of its height the shelf joins the legs into one
    foot and nothing is levelled; capped at 10 cm through its standing height (0.05 here) the four legs are its feet and
    the short one is brought down."""
    from score.stages.surfaces import place_line
    vertices, faces = tank_mesh((0.0, 0.0, 0.0, 0.02), height=1.0)
    vertices[vertices[:, 1] == 0.3, 1] = 0.06  # the body (and the legs' tops) down to a bottom shelf 0.06 up
    _, wide = place_line.levelled_feet(vertices, faces)
    assert wide["feet"] == 1 and not wide["levelled"], wide
    _, capped = place_line.levelled_feet(vertices, faces, tall=2.0)
    assert capped["feet"] == 4 and len(capped["levelled"]) == 1 and not capped["refused"], capped


def test_a_take_on_two_feet_has_its_short_one_levelled():
    """The engine room's fuel tank (2026-10-15): an upright tank on two cradle feet, one 5.9 cm up, tipped onto it
    when dropped; two feet are levelled as three are."""
    import numpy as np
    import trimesh
    from score.stages.surfaces import place_line
    body = trimesh.creation.box(bounds=((-0.4, 0.3, -0.4), (0.4, 2.0, 0.4)))
    cradle = [trimesh.creation.box(bounds=((-0.5, end, along - 0.08), (0.5, 0.3, along + 0.08)))
              for along, end in ((-0.3, 0.0), (0.3, 0.059))]
    mesh = trimesh.util.concatenate([body, *cradle])
    points, record = place_line.levelled_feet(np.asarray(mesh.vertices), np.asarray(mesh.faces), tall=2.0)
    assert record["feet"] == 2 and len(record["levelled"]) == 1 and not record["refused"], record
    assert abs(points[:, 1][np.asarray(mesh.vertices)[:, 2] > 0.2].min()) < 1e-9, "the short foot down on the floor"
def test_a_tall_take_s_leg_ending_over_the_narrow_band_is_still_levelled():
    """The hangar's access stair (2026-10-15): two legs ending 29 and 33 cm up, outside the 10 cm band, were left as
    they were once the band was capped; levelled in the whole band after the narrow one, they come down."""
    from score.stages.surfaces import place_line
    vertices, faces = tank_mesh((0.0, 0.0, 0.12, 0.12), height=1.0)
    _, record = place_line.levelled_feet(vertices, faces, tall=2.0)
    assert len(record["levelled"]) == 2 and not record["refused"], record


def test_a_take_another_place_lays_standing_is_levelled_by_its_rows():
    """The hangar lays old_station's parts rack (its `elsewhere`, parts_rack_1 to parts_rack_4) on the floor; old
    station lays none of its kind, so the rack was never levelled (2026-10-15). Its paint now counts the hangar's
    standing rows: the claimed rack row, never another of the hangar's."""
    from score.stages.surfaces import place_line
    inputs = {"surfaces": surface_data.path("old_station"), "inventory hangar": REPO / "data/inventory/hangar.json",
              "resting rules": REPO / "data/checks/resting.json"}
    rows = place_line.claimed_rows("parts_rack-r1", inputs)
    assert rows and {row["id"] for row in rows} == {"parts_rack"}, rows
    assert place_line.claimed_rows("parts_rack-r1", dict(inputs, **{"inventory hangar": None})) == []


def test_a_take_s_short_legs_are_levelled_before_its_bake_and_a_missing_leg_fails_by_name():
    from score.stages.surfaces import place_line
    import feet
    vertices, faces = tank_mesh((0.0, 0.022, 0.052, 0.127))
    points, record = place_line.levelled_feet(vertices, faces)
    assert record["feet"] == 4 and len(record["levelled"]) == 3 and not record["refused"], record
    lows = [low for _, low in feet.feet(feet.surface_points(points, faces), 0.15 * 1.6, 0.05)]
    assert len(lows) == 4 and max(lows) - min(lows) < 1e-9, lows
    points, refused = place_line.levelled_feet(*tank_mesh((0.0, 0.0, 0.0, 0.22)))
    assert refused["refused"] == [round(0.22 / max(1.6, 1.4 * 2 ** 0.5), 4)] and not refused["levelled"], refused
    folder = pathlib.Path(tempfile.mkdtemp())
    for found, verdict in ((record, checks.PASS), (refused, checks.FAIL)):
        (folder / "painted.json").write_text(json.dumps({"takes": {"water_tank-r1": {"feet": found}}}))
        judged = place_line.judge_feet(folder, {}, None)
        assert judged.answer == verdict and (verdict == checks.PASS or "water_tank-r1" in judged.findings[0]), judged
    shutil.rmtree(folder)
    paint = {stage.name: stage for stage in stages.STAGES}["surfaces-paint"]
    assert "feet in one plane" in [check.name for check in paint.checks]
    rules = REPO / "data/checks/resting.json"
    tank = {"place": "greenhouse", "kind": "greenhouse_water_tank"}
    glove = {"place": "lab", "kind": "lab_hanging_glove"}  # held on its cabinet, but it hangs: no feet to level
    assert place_line.stands_on_feet(tank, REPO / "data/inventory/greenhouse.json", rules)
    assert not place_line.stands_on_feet(glove, REPO / "data/inventory/lab.json", rules)
    assert paint.files("greenhouse")["inventory greenhouse"] == "{data}/inventory/greenhouse.json"


def test_a_designed_place_s_paint_reads_its_hand_in_rows_for_feet_never_the_old_inventory():
    """A designed place's rows are its hand-in's ({home}/design/props/<place>.json, read from its locked concept): the
    paint declares and reads it to tell a take laid loose on the floor from one held, and keys on it, never on the old
    concept's data/inventory file. Its rows name their take (`prop:<take>`) and stand on the floor the reading made a
    row of (`on:<floor row>`)."""
    from score.stages.surfaces import place_line
    paint = {stage.name: stage for stage in stages.STAGES}["surfaces-paint"]
    kept, prop_data.DESIGN = prop_data.DESIGN, pathlib.Path(tempfile.mkdtemp())  # the hand-ins apart from surfaces'
    hand_in = prop_data.DESIGN / "greenhouse.json"
    floor = {"id": "floor_plates", "anchor": "ground", "size": [4.0, 5.0, 0.1], "thing": "prop:gh_floor_ab12"}
    rows = [floor,
            {"id": "crate", "name": "crop crate", "anchor": "on:floor_plates", "thing": "prop:gh_crate_ab12"},
            {"id": "jar", "name": "seed jar", "anchor": "on:table", "thing": "prop:gh_jar_ab12"},
            {"id": "table", "name": "work table", "anchor": "floor", "size": [1.5, 0.8, 0.8], "thing": "prop:x"},
            {"id": "wall", "name": "left wall", "anchor": "on:floor_plates", "route": "shell",
             "thing": "prop:gh_wall_ab12"},
            # the cockpit's floor is mounted on its hull, a landing on its stairs: still the floor
            {"id": "hull", "anchor": "ground", "size": [9.0, 9.0, 3.5], "thing": "prop:gh_hull_ab12"},
            {"id": "deck", "anchor": "on:hull", "group": "kit: floor", "size": [9.0, 9.0, 0.1], "route": "shell",
             "thing": "prop:gh_deck_ab12"},
            {"id": "seat", "name": "pilot seat", "anchor": "on:deck", "thing": "prop:gh_seat_ab12"},
            {"id": "lamp", "name": "desk lamp", "anchor": "on:hull", "thing": "prop:gh_lamp_ab12"},
            # a stage on the floor is a floor too; a tin on a box on the floor is held
            {"id": "stage", "anchor": "on:floor_plates", "size": [8.0, 6.0, 1.2], "thing": "prop:x"},
            {"id": "drum", "name": "drum kit", "anchor": "on:stage", "thing": "prop:gh_drum_ab12"},
            {"id": "box", "anchor": "floor", "size": [1.0, 1.0, 1.0], "thing": "prop:x"},
            {"id": "tin", "name": "tin", "anchor": "on:box", "thing": "prop:gh_tin_ab12"}]
    hand_in.write_text(json.dumps({"place": "greenhouse", "rows": rows}))
    try:
        assert stages.paint_inventory("greenhouse") == "{home}/design/props/greenhouse.json"
        assert paint.files("greenhouse")["inventory greenhouse"] == "{home}/design/props/greenhouse.json"
        rules = REPO / "data/checks/resting.json"
        entry = {"place": "greenhouse", "kind": "gh_crate"}  # a designed take's kind lacks its take's suffix
        assert [row["id"] for row in place_line.standing_rows(entry, hand_in, rules, "gh_crate_ab12")] == ["crate"]
        assert not place_line.stands_on_feet(entry, hand_in, rules)  # by kind alone no designed row names it
        assert not place_line.stands_on_feet({"place": "greenhouse", "kind": "gh_jar"}, hand_in, rules, "gh_jar_ab12")
        assert not place_line.stands_on_feet({"place": "greenhouse", "kind": "gh_wall"}, hand_in, rules,
                                             "gh_wall_ab12")
        assert place_line.stands_on_feet({"place": "greenhouse", "kind": "gh_floor"}, hand_in, rules, "gh_floor_ab12")
        for kind, standing in (("gh_seat", True), ("gh_lamp", False), ("gh_drum", True), ("gh_tin", False)):
            assert place_line.stands_on_feet({"place": "greenhouse", "kind": kind}, hand_in, rules,
                                             f"{kind}_ab12") is standing, kind
    finally:
        shutil.rmtree(prop_data.DESIGN)
        prop_data.DESIGN = kept
    assert stages.paint_inventory("greenhouse") == "{data}/inventory/greenhouse.json"


def test_the_kit_route_s_bake_answers_the_empty_library_by_name():
    """Every old material retired (owner, 2026-10-21): the kit route's bake, which takes the repository's library by
    place, names each painted surface no library holds before anything is rented, never a KeyError."""
    from score.stages.surfaces import place_line
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary) / "take"
        folder.mkdir()
        (folder / "dark_panel.ply").write_text("")
        try:
            place_line.baking_specs("hangar", {}, [folder])
        except RuntimeError as refused:
            assert "surfaces in no library: ['dark_panel']" in str(refused), refused
        else:
            raise AssertionError("a bake was specced from an empty library")


def test_a_killed_paint_on_the_machine_says_its_signal_and_peak():
    sys.path.insert(0, str(REPO / "score/stages/surfaces/inside"))
    import paint_take
    code, peak = paint_take.measured([sys.executable, "-c", "import os, signal; os.kill(os.getpid(), signal.SIGKILL)"],
                                     dict(os.environ))
    assert code == -9 and peak > 0, (code, peak)


def test_a_take_s_paint_job_sends_what_it_reads_and_brings_its_folder_back():
    from score.stages.surfaces import place_line
    with tempfile.TemporaryDirectory() as temporary:
        out, parts = pathlib.Path(temporary) / "out", pathlib.Path(temporary) / "parts"
        out.mkdir()
        inputs = {"surfaces": REPO / "data/surfaces/campgrounds.json", "surfaces-parts": parts,
                  "inventory campgrounds": REPO / "data/inventory/campgrounds.json",
                  "resting rules": REPO / "data/checks/resting.json"}
        job = json.loads(place_line.paint_job(inputs, place_line.prop_env.short(inputs), out, "crane-r1",
                                              [{"part": 0}]).read_text())
        assert job["script"] == "score/stages/surfaces/inside/paint_take.py" and job["outputs"] == [
            str(out / "labelled" / "crane-r1")]
        sent = set(job["inputs"])
        assert {str(parts / "crane-r1"), str(parts / "parts.json"), str(REPO / "score"), str(REPO / "tools/props"),
                str(REPO / "data/library")} <= sent, sent
        assert any(path.endswith("work/pixal/crane-r1-final.glb") for path in sent), sent
        listing = json.loads(pathlib.Path(job["args"][0]).read_text())
        assert listing["paint take"] == "crane-r1" and listing["paint repo"] == str(REPO)  # data may lie elsewhere
        assert json.loads(pathlib.Path(listing["paint records"]).read_text()) == [{"part": 0}]


def test_a_bake_is_held_against_its_surface_dirtied_as_far_as_its_place_s_dirt():
    """The wreck: dirt 0.6 in regolith (L* 56.8); its white hull (89.6) bakes to 69.0 and is on its surface; the same
    white at a clean place, or baked darker than its dirt reaches, is not; a wrong surface is not."""
    import numpy as np
    from score.stages.surfaces import bake_check
    white, regolith = np.array([89.6, -1.7, 1.6]), np.array([56.8, 0.2, 3.1])
    baked = np.array([69.0, -0.8, -3.2])
    assert bake_check.on_surface(baked, white, regolith, 0.6) < 6
    assert bake_check.on_surface(baked, white, regolith, 0.0) > bake_check.BAKE_DELTA_E
    assert bake_check.on_surface(np.array([40.0, 0, 0]), white, regolith, 0.6) > bake_check.BAKE_DELTA_E
    assert bake_check.on_surface(baked, white, None, 0.6) > bake_check.BAKE_DELTA_E


def test_a_bake_is_held_against_its_surface_worn_as_far_as_its_place_s_wear():
    """The engine room, worn 0.8, dirt 0.5: its power core's hazard trim baked a median [73.2, 2.2, 41.3], 20.1 off
    its clean yellow and part worn to bare steel; worn as far as the place's wear it lies on its surface. Unworn, or
    with no bare colour, it does not; a wrong surface (dark_panel) still fails."""
    import numpy as np
    from score.stages.surfaces import bake_check
    yellow, bare, soot = np.array([80.5, 3.5, 78.8]), np.array([66.3, -1.1, -4.5]), np.array([13.2, 3.7, 5.9])
    baked = np.array([73.2, 2.2, 41.3])
    assert bake_check.on_surface(baked, yellow, soot, 0.5, bare, 0.8) < 6
    assert bake_check.on_surface(baked, yellow, soot, 0.5, bare, 0.0) > bake_check.BAKE_DELTA_E
    assert bake_check.on_surface(baked, yellow, soot, 0.5) > bake_check.BAKE_DELTA_E
    assert bake_check.on_surface(baked, np.array([19.2, -0.7, -3.2]), soot, 0.5, bare, 0.8) > bake_check.BAKE_DELTA_E


def test_wear_passes_only_toward_the_surface_s_bare_colour_and_only_as_far_as_its_place_s_wear():
    """Wear has causes (the paper, Appendix D: the room's wear setting from its use, laid on edges and kicks) and the
    check allows only what those can lay: a yellow worn all the way to bare steel in a place worn 0.4 lies past its
    wear; a yellow darkened toward black (no recipe's bare colour) fails however worn its place; a surface with no
    bare colour has nothing to wear, and in a place with no wear nothing is worn."""
    import numpy as np
    from score.stages.surfaces import bake_check
    yellow, bare = np.array([80.5, 3.5, 78.8]), np.array([66.3, -1.1, -4.5])
    worn_through = bare.copy()
    darkened = np.array([50.0, 3.5, 78.8])
    assert bake_check.on_surface(worn_through, yellow, None, 0.0, bare, 0.4) > bake_check.BAKE_DELTA_E
    assert bake_check.on_surface(darkened, yellow, None, 0.0, bare, 0.8) > bake_check.BAKE_DELTA_E
    assert bake_check.on_surface(yellow + 0.6 * (bare - yellow), yellow, None, 0.0, None, 0.8) > bake_check.BAKE_DELTA_E
    assert bake_check.on_surface(yellow + 0.6 * (bare - yellow), yellow, None, 0.0, bare, 0.0) > bake_check.BAKE_DELTA_E
    assert bake_check.on_surface(yellow + 0.6 * (bare - yellow), yellow, None, 0.0, bare, 0.8) < 1


def test_a_part_s_baked_colour_is_its_area_s_median_on_each_channel():
    """Lab's junction_box_1, bake of 2026-10-14: 56% of its crane_yellow_paint's area baked yellow, 15% between, 29%
    the grey panel at the same L*; a triangle picked by its L* alone was a grey one (dE 37 off the yellow), each
    channel's own median is the yellow the bake wrote."""
    import numpy as np
    from score.stages.surfaces import bake_check
    darker, between, grey, lighter = [62.0, 2.0, 38.0], [62.9, 0.5, 17.0], [63.5, -0.7, -4.4], [65.0, 2.0, 38.0]
    colour = np.array([darker] * 28 + [between] * 15 + [grey] * 29 + [lighter] * 28)
    areas = np.ones(len(colour))
    order = np.argsort(colour[:, 0])  # the old pick: the triangle at the area's median L*
    assert colour[order][np.searchsorted(np.cumsum(areas[order]), areas.sum() / 2)].tolist() == grey
    middle = bake_check.area_median(colour, areas)
    assert middle.tolist() == [63.5, 2.0, 38.0], middle
    assert bake_check.area_median(colour, np.array([0.0] * 43 + [1.0] * 29 + [0.0] * 28)).tolist() == grey


def test_a_triangle_under_a_texel_is_named_by_where_the_bake_wrote_its_texel():
    """The flat's bowl stack, bake of 2026-10-13: its glass rims' triangles lie under a texel each, so the texel the
    check samples for one was baked from the centre's point on a neighbour (enamel), and its glass failed at dE 66.6
    while the bake was right. The check names the sampled texel by the ray from that point, as the bake did."""
    import numpy as np
    import trimesh
    from score.stages.surfaces import bake_check
    enamel = trimesh.creation.box(bounds=[[-1.0, 0.0, -0.05], [0.0, 1.0, 0.05]])
    glass = trimesh.creation.box(bounds=[[0.0, 0.0, -0.05], [1.0, 1.0, 0.05]])
    # one large triangle over the enamel covering texel (0, 0)'s centre in a 2 x 2 texture, one sliver over the glass
    # whose middle falls in that texel but not on its centre
    positions = np.array([[-0.9, 0.1, 0.05], [-0.1, 0.1, 0.05], [-0.5, 0.9, 0.05],
                          [0.4, 0.4, 0.05], [0.6, 0.4, 0.05], [0.5, 0.6, 0.05]])
    uvs = np.array([[0.2, 0.0], [0.5, 0.0], [0.2, 0.45], [0.05, 0.05], [0.12, 0.05], [0.05, 0.12]])
    geometry = {"positions": positions, "uvs": uvs, "triangles": np.array([[0, 1, 2], [3, 4, 5]]),
                "maps": np.array([0, 0])}
    entry = {"base": [1, 0, 0, 0, 1, 0, 0, 0, 1], "size": [2.0, 1.0, 0.1]}
    rows, columns = np.array([0, 0]), np.array([0, 0])
    points, owners = bake_check.sampled_points(geometry, rows, columns, np.array([[2, 2], [2, 2]]))
    assert owners.tolist() == [0, 0], owners
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        enamel.export(folder / "enamel_white.ply")
        glass.export(folder / "glass.ply")
        names, middle_named, _ = bake_check.baked_surfaces(geometry, folder, entry)
        names, texel_named, _ = bake_check.baked_surfaces(geometry, folder, entry, (points, owners))
    assert [names[index] for index in middle_named] == ["enamel_white", "glass"], middle_named
    assert [names[index] for index in texel_named] == ["enamel_white", "enamel_white"], texel_named


def test_a_baked_triangle_beside_a_thin_post_is_named_by_the_bake_s_ray_not_the_nearest_part():
    """far_city's pencil tower, 2026-10-13: the cut-down copy stands 0.6 m proud of the facade; beside a post, the
    post's side lies nearer than the facade the bake's ray meets, so the nearest part named the facade's colour
    post_dark (dE 45). The bake's ray from the triangle inward names the facade; a triangle over the post, the post.
    The check's reach constants are make_chunky's."""
    import ast
    import numpy as np
    import trimesh
    from score.stages.surfaces import bake_check
    facade = trimesh.creation.box(bounds=[[-5.0, 0.0, -1.0], [5.0, 2.0, 0.0]]).subdivide_to_size(0.1)
    post = trimesh.creation.box(bounds=[[-0.05, 0.0, 0.0], [0.05, 2.0, 1.0]]).subdivide_to_size(0.1)
    beside = [[0.3, 0.9, 0.6], [0.5, 0.9, 0.6], [0.4, 1.1, 0.6]]
    over = [[-0.1, 0.9, 1.6], [0.1, 0.9, 1.6], [0.0, 1.1, 1.6]]
    geometry = {"positions": np.array(beside + over), "triangles": np.array([[0, 1, 2], [3, 4, 5]])}
    entry = {"base": [1, 0, 0, 0, 1, 0, 0, 0, 1], "size": [10.0, 2.0, 2.0]}
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        facade.export(folder / "facade_paint.ply")
        post.export(folder / "post_dark.ply")
        names, surface, reach = bake_check.baked_surfaces(geometry, folder, entry)
        nearest = bake_check.laid_parts(folder, entry)[1].nearest.on_surface([[0.4, 1.0, 0.6]])[0][0]
    assert abs(nearest[0]) <= 0.05 + 1e-9, f"the post lies nearer than the facade behind: {nearest}"
    assert [names[index] for index in surface] == ["facade_paint", "post_dark"], surface
    assert reach[0].all(), "both parts lie within the triangle's reach"
    found = {node.targets[0].id: eval(compile(ast.Expression(node.value), "make_chunky", "eval")) for node in ast.parse(
        (REPO / "tools/props/library/inside/make_chunky.py").read_text()).body
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id in ("REACH_VOXELS", "REACH_LEAST", "VOXEL_SHARE", "VOXEL_FINEST")}
    assert (found["REACH_VOXELS"], found["REACH_LEAST"], found["VOXEL_SHARE"], found["VOXEL_FINEST"]) == (
        bake_check.BAKE_REACH_VOXELS, bake_check.BAKE_REACH_LEAST, bake_check.BAKE_VOXEL_SHARE,
        bake_check.BAKE_VOXEL_FINEST)


def test_a_standing_model_with_a_foot_off_the_floor_fails_and_lying_wreckage_is_left_out():
    """The hangar's parts rack stood on a middle part, its legs 22 cm up."""
    import numpy as np
    from score.stages.surfaces import bake_check
    feet = [(x, z) for x in (-0.5, 0.5) for z in (-0.3, 0.3)]
    level = np.array([[x, 0.0, z] for x, z in feet] + [[0, 1.0, 0]])
    rack = np.array([[x, 0.22 if x > 0 else 0.0, z] for x, z in feet] + [[0, 1.0, 0]])
    assert max(bake_check.stance_lows(level)) == 0.0
    assert abs(max(bake_check.stance_lows(rack)) - 0.22) < 1e-6
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        (folder / "labels.json").write_text(json.dumps({"feet": {"feet": 4}}))
        rows = [{"id": "parts_rack_1", "name": "steel parts rack"}, {"id": "leg_strut", "name": "torn-off landing leg"}]
        assert bake_check.stands("parts_rack_1", folder, rows, ["torn"])
        assert not bake_check.stands("leg_strut", folder, rows, ["torn"])
        (folder / "labels.json").write_text(json.dumps({"feet": {"skipped": "no floor or held row lays its kind"}}))
        assert not bake_check.stands("parts_rack_1", folder, rows, ["torn"])
        (folder / "checks.json").write_text(json.dumps({
            "parts_rack_1": {"stands": True, "stance_lows": [0.0, 0.221, 0.0, 0.24]},
            "leg_strut": {"stands": False, "stance_lows": [0.0, 0.3, 0.2, 0.0]},
            "crate": {"stands": True, "stance_lows": [0.0, 0.01, 0.0, 0.02]}}))
        verdict = bake_check.judge_stance(folder, {}, None)
    assert verdict.answer == "fail" and len(verdict.findings) == 1 and "parts_rack_1: a foot 24.0 cm" in verdict.findings[0]
    assert set(json.loads((REPO / "data/checks/stance.json").read_text())) == {"about", "lies"}

def test_a_base_that_slopes_as_one_piece_is_brought_down_level_and_a_far_gap_is_refused():
    """The hangar's parts rack: two legs ending 8% of its size over a middle part."""
    import numpy as np
    from score.stages.surfaces import place_line
    corners = [(x, z) for x in (-0.4, 0.4) for z in (-0.3, 0.3)]
    rack = np.array([[x, 0.08 if x > 0 else 0.0, z] for x, z in corners] + [[x, 0.5, z] for x, z in corners]
                    + [[0.0, 1.0, 0.0]])
    points, record = place_line.flattened_base(rack, 0.25, 0.01, 0.15)
    assert np.allclose(points[:4, 1], 0.0, atol=1e-9) and record["flattened"] == [0.08, 0.08], record
    assert np.allclose(points[4:, 1], rack[4:, 1]), "a point over the band does not move"
    points, record = place_line.flattened_base(rack + [0, 0, 0], 0.25, 0.01, 0.05)
    assert record["refused"] == [0.08, 0.08] and np.allclose(points, rack)
    level = rack.copy()
    level[:4, 1] = 0.0
    assert place_line.flattened_base(level, 0.25, 0.01, 0.15)[1]["flattened"] == []

def test_a_base_sloping_as_one_plane_through_its_middle_is_brought_down_level():
    """The square's guard hut: a slab base rising 8% of its size from one side to the other, each quadrant's lowest
    point by the middle (flattened_base finds nothing); a level slab and a round bottom are left as they are."""
    import numpy as np
    import trimesh
    from score.stages.surfaces import place_line
    slab = trimesh.creation.box(bounds=((-1.0, 0.0, -1.0), (1.0, 2.0, 1.0))).subdivide().subdivide().subdivide()
    slab.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 4, (0, 1, 0)))  # a diamond, as the hut's
    hut = np.asarray(slab.vertices).copy()
    bottom, over = hut[:, 1] < 1e-9, hut[:, 1] > 0.5
    hut[bottom, 1] += 0.08 * (hut[bottom, 0] + 2 ** 0.5) / 2 ** 1.5  # 8 cm up at its far corner, x = 1.41
    quadrants = place_line.flattened_base(hut, 0.5, 0.03, 0.4)[1]
    assert max(quadrants["quadrants"]) < 0.05, quadrants  # the blind spot: each quadrant's lowest lies at x = 0
    points, record = place_line.sloped_base(hut, 0.5, 0.17, 0.03, 0.4)
    assert abs(record["rise"] - 0.08) < 0.01 and not record["refused"], record
    assert np.abs(points[bottom, 1]).max() < 0.01 and np.allclose(points[over], hut[over]), "over the band: as made"
    assert points[:, 1].min() >= hut[:, 1].min() - 1e-12, "nothing comes down past the lowest point"
    assert place_line.sloped_base(hut, 0.5, 0.17, 0.03, 0.05)[1]["refused"] == [record["rise"]]
    level = np.asarray(slab.vertices)
    assert place_line.sloped_base(level, 0.5, 0.17, 0.03, 0.4)[1]["rise"] is None
    ball = np.asarray(trimesh.creation.icosphere(4).vertices)
    points, record = place_line.sloped_base(ball, 0.5, 0.17, 0.03, 0.4)
    assert record["rise"] is None and np.array_equal(points, ball), record


def test_a_tall_cabinet_s_base_step_is_levelled_against_its_footprint():
    """Both ways (the garage's control cabinet, 2026-10-15: 1.5 m tall on a plinth rim whose underside rises across
    its footprint under its floor's level cells, resting 2.1 degrees over; the quadrants and the cells' plane passed it): the
    face it rests on comes down level; a cabinet on a level rim is left as made. And its row, "cables running up from
    its top", stands it on the floor, while a stick mounted on a console and a cairn of stones do not."""
    import numpy as np
    import trimesh
    from score.stages.surfaces import place_line

    def cabinet(rise):
        body = trimesh.creation.box(bounds=((-0.3, 0.04, -0.25), (0.3, 1.5, 0.25)))  # its floor 4 cm up, level
        rim = [trimesh.creation.box(bounds=low_high) for low_high in (
            ((-0.3, 0.0, -0.25), (0.3, 0.08, -0.2)), ((-0.3, 0.0, 0.2), (0.3, 0.08, 0.25)),
            ((-0.3, 0.0, -0.25), (-0.25, 0.08, 0.25)), ((0.25, 0.0, -0.25), (0.3, 0.08, 0.25)))]
        body = body.subdivide().subdivide().subdivide().subdivide()  # its floor dense: cells off the rim's plane
        mesh = trimesh.util.concatenate([body, *rim])
        points = np.asarray(mesh.vertices).copy()
        bottom = points[:, 1] < 1e-9
        points[bottom, 1] = rise * (points[bottom, 0] + 0.3) / 0.6  # the rim's underside rises along x
        return points, np.asarray(mesh.faces)

    def resting_lean(points, faces):
        mesh = trimesh.Trimesh(points, faces, process=False)
        middle = (mesh.triangles_center * mesh.area_faces[:, None]).sum(axis=0) / mesh.area
        hull = mesh.convex_hull
        hits, _, struck = hull.ray.intersects_location([[middle[0], 3.0, middle[2]]], [[0.0, -1.0, 0.0]])
        return np.degrees(np.arccos(-hull.face_normals[struck[np.argmin(hits[:, 1])]][1]))

    points, faces = cabinet(0.012)  # 1.2 cm across 0.6 m: under the 1.5 cm a share of its height lets pass
    assert resting_lean(points, faces) > 1.0
    levelled, record = place_line.levelled_feet(points, faces)
    assert record.get("rests") and resting_lean(levelled, faces) < 0.1, record
    points, faces = cabinet(0.0)
    level, record = place_line.levelled_feet(points, faces)
    assert "rests" not in record and np.array_equal(level, points), record
    rules = REPO / "data/checks/resting.json"
    folder = pathlib.Path(tempfile.mkdtemp())
    rows = [{"id": "control_cabinet", "anchor": "floor", "thing": "prop:garage_control_cabinet",
             "name": "a standing steel control cabinet, cables running up from its top"},
            {"id": "control_stick", "anchor": "on:main_console", "thing": "prop:cockpit_control_stick",
             "name": "flight stick set in the console"},
            {"id": "cairn", "anchor": "floor", "thing": "prop:campgrounds_cairn",
             "name": "cairn of flat stones stacked into a narrow tower"},
            {"id": "small_panel", "anchor": "floor", "thing": "prop:wreck_small_panel", "name": "small torn hull panel",
             "leans": "debris lying tilted on purpose"}]
    (folder / "inventory.json").write_text(json.dumps({"rows": rows}))
    assert place_line.stands_on_feet({"kind": "garage_control_cabinet"}, folder / "inventory.json", rules)
    for lying in ("cockpit_control_stick", "campgrounds_cairn"):  # mounted on another object; a pile of stones
        assert not place_line.stands_on_feet({"kind": lying}, folder / "inventory.json", rules), lying
    assert not place_line.stands_on_feet({"kind": "wreck_small_panel"}, folder / "inventory.json", rules)
    shutil.rmtree(folder)

def test_only_a_place_nobody_walks_bakes_with_no_kick_wear():
    """The wreck's surface data says nobody walks it: its bake's specs say kicks 0. Every other place's data says
    nothing, so unwalked hands its specs back as given, the very same object (recipes.WALKED: kicked as before), and
    its bake is the same as before the change (2026-10-13)."""
    from score.stages.surfaces import place_line
    specs = {"dark_panel": {"recipe": "painted_metal"}, "bare_steel": {"recipe": "bare_metal"}}
    assert {spec["kicks"] for spec in place_line.unwalked(specs, surface_data.record("wreck")).values()} == {0.0}
    unwalked = sorted(path.stem for path in surface_data.FOLDER.glob("*.json")
                      if json.loads(path.read_text()).get("foot_traffic", True) is False)
    assert unwalked == ["wreck"], unwalked
    for path in surface_data.FOLDER.glob("*.json"):
        if path.stem != "wreck":
            assert place_line.unwalked(specs, surface_data.record(path.stem)) is specs, path.stem


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[3] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
