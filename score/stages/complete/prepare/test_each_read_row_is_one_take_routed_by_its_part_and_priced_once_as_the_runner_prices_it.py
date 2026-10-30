"""Invariant: each row of a place's current scene inventory reading is one take, routed by its part and sized by its
own metres, and the figure prices every take's layers once, as the runner prices them. Rows of one model share a
take; a library model is reused only under today's route or the owner's lock; a take's outcome is predicted only from
a measured failure (the hub's table, else this environment's own accepted outputs and free code builds); a take with
no box, the whole picture, no size or no part read is an input gap, priced apart and never handed to the loop; a
backdrop row is shown from the place of its scene that makes it, else made here far off at the size its box shows; a
place with no reading waits; a design is approved only once it stands whole on its lock; the benchmarks keep to
their EUR 20 cap. Expected answers are worked by hand, read from the repository's measured data (the hub's table,
per-unit.json, the ledgers), or are owner rules; "every job once" in the record's line is a wording check guarding
the owner's one-shot rule (2026-10-20).

Breaks that turn this red (each applied once and seen red, then reverted):
- groups.place_groups: `instances += 1` for the row's count -> test_rows_of_one_model_in_a_place_are_one_take_...
- groups.sides: `side >= 0` -> test_a_size_that_is_not_three_positive_sides_has_no_ratio
- library.reusable: the runner's accept not asked -> test_a_library_model_matches_by_kind_and_ratio_and_only_...
- predict.predicted: `counted["of"] >= 1` for MIN_MEASURED -> test_the_hub_table_makes_every_rod_a_predicted_gap_...
- predict.own_outcome: the LATER_TAKES_SINCE check -> `if False:` -> test_a_take_its_environment_measured_is_...
- predict.sheet_outcome: no row a sheet (`or True`) -> test_a_flat_sheet_pixal3d_made_no_model_of_is_predicted_...
- predict.straight_outcome: the `asked` check -> `if False:` -> test_a_thin_straight_row_is_predicted_by_its_code_...
- predict.straight_outcome: no `views is None` gap (thin_straight.drawn_thin -> `return True`) -> test_a_thin_straight_row_...
- predict.own_outcome: `coded = False` (no thin_straight.coded) -> test_a_pipe_whose_close_up_passed_is_predicted_...
- contract.faults: the picture check -> `elif False:` -> test_inputs_break_their_contract_on_an_unknown_view_...
- machines.best_zone: `min` for `max` -> test_the_first_class_in_the_kinds_order_is_fixed_in_its_zone_with_the_best_...
- estimate.layer_price: the likely euros without the bill share -> test_layers_run_each_take_once_a_shell_piece_...
- estimate.layer_cost: the no-units check -> `if False:` -> test_the_eta_walks_the_layers_in_the_routes_order_...
- benchmarks.high_with_guesses: the guesses left out -> test_the_benchmarks_stay_under_their_cap_and_ask_the_...
- benchmarks.guard: the free-only refusal raised -> test_the_benchmarks_guard_under_the_kill_latch_is_a_refusal_...
- benchmarks.plan_gap: the missing check -> `if False:` -> test_a_benchmark_whose_inputs_do_not_stand_is_a_gap_...
- groups.row_size: `if laid:` (the plan's item sizes the model), or `if laid and laid != made:` (his edited item
  sizes it, 2026-10-29) -> test_a_take_is_sized_by_its_reading_and_routed_...
- groups.shown_from: `source = None` -> test_a_backdrop_row_a_place_of_its_scene_makes_is_shown_from_there_...
- groups.far_made: no seen_size for a single piece -> test_a_far_row_of_one_piece_is_as_wide_as_its_box_shows_it
- groups.structure_of: the taller-than check dropped -> test_a_backdrop_part_of_a_structure_is_shown_by_a_...
- groups.beyond_of: the reading's afar rows dropped -> test_a_row_the_reading_names_far_off_is_beyond_and_shown_...
- groups.beyond_of: `- at_foot(...)` dropped -> test_a_row_at_the_picture_s_foot_is_never_beyond
- groups.plan_parts: no "opening" for a written opening -> test_a_row_is_routed_by_its_part_and_the_plan_lays_only_...
- groups.route_of: an unread part routed "prop" -> test_a_row_whose_part_is_not_read_is_an_input_gap_until_its_...
- groups.boxed_by: the Gemini region check -> `if False:` -> test_a_row_sam_3_missed_is_framed_by_gemini_and_one_...
- groups.current: no place waiting (`[]`) -> test_a_places_current_reading_is_its_inventory_and_a_place_with_none_waits
- __main__.remake: `"waiting": []` -> test_the_remake_record_prices_the_read_places_and_counts_the_rest_as_waiting
- __main__.take_counts: `"input_gaps": 0` -> test_the_remake_record_counts_every_row_once_and_says_its_one_line
- estimate.layer_units: one unit more a layer -> test_the_runner_lists_and_prices_a_designed_places_takes_as_...
- handin.surface_record: a take's kind its row id -> test_a_design_row_s_bake_entry_and_kind_come_from_its_row_...
- design.concept_state: always "picked" -> test_a_concept_review_draw_is_drawn_and_its_pick_picked_until_unlocked
- design.waits: the room-moved check -> `if False:` -> test_a_design_is_approved_only_once_it_stands_whole_on_its_...

Run: make tests TESTS="score/stages/complete/prepare/<this file>", or PROPS_HOME=$(mktemp -d) .venv/bin/python <it>.
"""
import collections
import json
import math
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[4]))

from score import stages  # noqa: E402
from score.adapters import compute  # noqa: E402
from score.stages.complete.gaps import price  # noqa: E402
from score.stages.complete.prepare import (__main__ as prepare, benchmarks, contract, design,  # noqa: E402
                                           estimate, groups, handin, library, machines, predict)

REPO = pathlib.Path(__file__).resolve().parents[4]


def a_row(row_id, size, **more):
    return {"id": row_id, "size": size, "thing": f"prop:p_{row_id}", "view": "v1", "box": [0, 0, 100, 50], **more}


def test_rows_of_one_model_in_a_place_are_one_take_and_shell_pieces_and_reuses_are_marked():
    record = {"concept_pick": {"sha256": "c"}, "rows": [
        a_row("stool", [0.4, 0.4, 0.5]), a_row("stool_2", [0.42, 0.4, 0.52], count=3),
        a_row("stool_3", [0.1, 0.1, 0.9]), a_row("wall_plain", [1.2, 0.06, 1.1], group="kit: wall"),
        a_row("jar", [0.1, 0.1, 0.2], reuse="lab:sample_jar")]}
    found = groups.place_groups("p", record)
    assert [group["rows"] for group in found] == [["stool", "stool_2"], ["stool_3"], ["wall_plain"], ["jar"]], found
    assert found[0]["instances"] == 4 and found[0]["take"] == "p_stool" and found[2]["shell"]
    counted = groups.counts({"p": found})
    assert (counted["rows"], counted["groups"], counted["reused"], counted["shell_groups"]) == (5, 3, 1, 1), counted


def test_a_size_that_is_not_three_positive_sides_has_no_ratio():
    assert groups.size_ratio([1, 0, 1]) is None and groups.size_ratio("big") is None
    assert groups.object_kind("ac_unit_2.square") == "ac_unit" and groups.object_kind("lamp_1_2") == "lamp"


def test_a_library_model_matches_by_kind_and_ratio_and_only_todays_route_or_locked_is_reused(tmp=None):
    root = pathlib.Path(tmp or tempfile.mkdtemp())
    today = {"route": "r-today", "accept": {"by": "runner"}}
    older = {"route": "r-older", "accept": {"by": "runner"}}
    entries = [("chair_1", "prop", "hub", "chair", today, "draft"), ("rack_1", "piece", "hub", "rack", {}, "draft"),
               ("lost_1", "prop", "x", "y", today, "draft"), ("lamp_1", "prop", "hub", "lamp", older, "draft"),
               ("bin_1", "piece", "hub", "bin", {}, "locked"),
               ("box_1", "prop", "hub", "box", {"route": "r-today"}, "draft"),
               ("chair_0", "prop", "hub", "chair", today, "withdrawn")]
    (root / "index").mkdir(parents=True)
    (root / "index" / "model.json").write_text(json.dumps({"schema": "score-lib-index/1", "entries": [
        {"address": f"model/{name}@1", "tags": {"model": [tag]}, "state": state}
        for name, tag, _, _, _, state in entries]}))
    for name, _, place, source, route, _ in entries:
        folder = root / "entries" / "model" / name / "1"
        folder.mkdir(parents=True)
        (folder / "entry.json").write_text(json.dumps({"schema": "score-lib-entry/1",
                                                       "provenance": {"place": place, "source_name": source,
                                                                      **route}}))
    sizes = {"chair": [0.6, 0.6, 0.9], "rack": [0.6, 0.6, 1.9], "lamp": [0.2, 0.2, 1.5], "bin": [0.4, 0.4, 0.6],
             "box": [0.5, 0.5, 0.5]}
    inventories = {"hub": {"rows": [a_row(name, size) for name, size in sizes.items()]}}
    index = library.index(library.library_models(root, "r-today"), inventories)
    others = [a_row(name, size) for name, size in sizes.items() if name != "chair"]
    lab = {"rows": [a_row("chair", [0.62, 0.6, 0.95])] + others}
    chair, rack, lamp, bin_group, box = groups.place_groups("lab", lab)
    assert library.match(chair, index) == {"pipeline": ["model/chair_1@1"], "old": [], "code": []}
    assert library.match(rack, index) == {"pipeline": [], "old": [], "code": ["model/rack_1@1"]}
    assert library.match(lamp, index) == {"pipeline": [], "old": ["model/lamp_1@1"], "code": []}  # older route
    assert library.match(bin_group, index)["pipeline"] == ["model/bin_1@1"]  # the owner locked it
    assert library.match(box, index)["old"] == ["model/box_1@1"]  # today's route named, never accepted there
    assert len(index) == 10  # each by its ratio and by kind alone; the model with no source row matches nothing
    read = groups.place_groups("lab", {"rows": [a_row("chair", None)]})[0]  # a reading's row: no size
    assert library.match(read, index)["pipeline"] == ["model/chair_1@1"]


def test_the_hub_table_makes_every_rod_a_predicted_gap_and_a_lone_sheet_only_a_risk():
    rates = predict.hub_rates()
    assert (rates["rod"]["failed"], rates["rod"]["of"]) == (5, 5), rates
    assert rates["sheet"]["of"] < predict.MIN_MEASURED
    rod = predict.predicted([0.1, 0.1, 1.0], rates)
    assert rod["outcome"] == "predicted gap" and rod["pass_share"] == 0.0 and "5 of 5" in rod["measured"], rod
    assert predict.predicted([1.4, 0.02, 0.9], rates)["outcome"] == "at risk"
    solid = predict.predicted([0.6, 0.6, 0.9], rates)
    assert solid["outcome"] == "pass" and 0 < solid["pass_share"] < 1, solid
    palm = predict.predicted([0.399, 1.16, 8.0], rates)  # street's distant palm: a "rod" by its sides alone
    assert palm["outcome"] == "predicted gap" and prepare.status_of({"pipeline": None}, False, []) == "bought"
    conduit = predict.predicted([0.05, 0.05, 3.0], rates, {"name": "conduit", "noun": "conduit"})
    assert conduit["outcome"] == "at risk" and conduit["pass_share"] is None, conduit  # built in code after
    assert predict.predicted([0.399, 1.16, 8.0], rates, {"name": "palm tree", "noun": "tree"})["outcome"] == \
        "predicted gap"


def a_stored_output(store, files):
    folder = pathlib.Path(tempfile.mkdtemp())
    for name, value in files.items():
        (folder / name).write_text(json.dumps(value))
    return store.put_tree(folder)


def test_a_take_its_environment_measured_is_predicted_by_that_not_by_its_shape():
    from score.store import Store
    store = Store.in_folder(tempfile.mkdtemp())
    pipe, door, rug, tile = [0.1, 0.1, 3.0], [1.0, 0.1, 2.1], [2.0, 3.0, 0.02], [0.5, 0.5, 0.4]
    closeups = {"pipe": {"size": pipe, "drawn_by": None, "takes": {"pro": ["x"], "retry": ["x"]}},
                "door": {"size": door, "drawn_by": "retry", "takes": {"pro": ["x"], "retry": []}},
                "rug": {"size": rug, "drawn_by": None, "takes": {"pro": ["x"]}},
                "crate": {"size": tile, "drawn_by": "pro", "takes": {"pro": []}},
                "tile": {"size": tile, "drawn_by": None, "takes": {"pro": ["x"]}}}
    at = "2026-10-25T18:00:00+00:00"
    store.write_accept("closeup@lab", {"output": a_stored_output(store, {"closeups.json": {"objects": closeups}}),
                                       "at": at})
    store.write_accept("pixal@lab", {"output": a_stored_output(store, {"batch-gaps.json": {"gaps": [
        {"row": "pixal", "objects": ["crate", "lab_crate"]}, {"row": "closeup", "objects": ["tile"]}]}}), "at": at})
    store.write_accept("likeness@lab", {"output": a_stored_output(store, {
        "likeness.json": {"objects": {"pipe": {"made": "code"}, "door": {}}}, "batch-gaps.json": {"gaps": []}}),
        "at": at})
    measures = predict.environment_measures(store, ["lab", "hub"])
    assert set(measures) == {"lab"} and measures["lab"]["built"] == {"pipe": True}, measures

    def own(name, size, read_size=None):
        take = {"place": "lab", "rows": [name], "take": f"lab_{name}", "size": size}
        return predict.own_outcome(take, {"id": name, "name": name, "noun": name, "size": size,
                                          "read_size": read_size}, measures["lab"])
    assert own("pipe", pipe)["outcome"] == "pass"  # its close-up failed, its code build passed the likeness
    assert own("door", door)["outcome"] == "pass" and "closeup@lab" in own("door", door)["measured"]
    assert own("door", [1.0, 0.1, 2.4]) is None  # asked at another size today: not measured
    assert own("door", [1.0, 0.1, 2.4], read_size=door)["outcome"] == "pass"  # its own metres as measured
    assert own("rug", rug) is None  # a flat row drawn before the view from above: another request
    assert own("crate", tile)["outcome"] == "at risk"  # passed, but Pixal3D made no model of it
    assert own("tile", tile) is None  # every take failed before its next takes' request (LATER_TAKES_SINCE)
    measures["lab"]["at"] = predict.LATER_TAKES_SINCE
    assert own("tile", tile)["outcome"] == "predicted gap"  # no route builds it after
    far = {"id": "tile", "name": "tile", "noun": "tile", "size": tile, "far": {"pieces": 1, "length": 0.0}}
    assert predict.own_outcome({"place": "lab", "rows": ["tile"], "take": "lab_tile", "size": tile}, far,
                               measures["lab"]) is None  # laid far off: drawn from the whole painting before
    rocket = {**far, "id": "crate", "name": "crate", "noun": "crate"}  # passed from the whole painting, now far
    assert predict.own_outcome({"place": "lab", "rows": ["crate"], "take": "lab_crate", "size": tile}, rocket,
                               measures["lab"])["outcome"] == "at risk"
    measures["lab"]["at"] = predict.FAR_CROP_SINCE
    tile_take = {"place": "lab", "rows": ["tile"], "take": "lab_tile", "size": tile}
    assert predict.own_outcome(tile_take, far, measures["lab"])["outcome"] == "predicted gap"  # far, crop alone then
    assert predict.own_outcome(tile_take, {**far, "anchor": "sky"}, measures["lab"]) is None  # beyond only since
    measures["lab"]["at"] = predict.LATER_TAKES_SINCE
    assert own("lamp", tile) is None
    measures["lab"]["built"] = {}
    assert own("pipe", pipe)["outcome"] == "at risk"  # built in code, its likeness not judged yet
    measures["lab"]["built"] = {"pipe": False}
    assert own("pipe", pipe)["outcome"] == "predicted gap"


def a_closeup_picture(folder, name, box):
    """A close-up of one brown object (`box`, pixels left, top, right, bottom) on a white studio backdrop."""
    from PIL import Image, ImageDraw
    picture = Image.new("RGB", (512, 512), (255, 255, 255))
    ImageDraw.Draw(picture).rectangle(box, fill=(90, 70, 60))
    (folder / "closeups").mkdir(parents=True, exist_ok=True)
    picture.save(folder / "closeups" / f"{name}.png")


def test_a_flat_sheet_pixal3d_made_no_model_of_is_predicted_by_its_code_build_measured_free():
    from score.store import Store
    store = Store.in_folder(tempfile.mkdtemp())
    rug, note, crate = [2.0, 3.0, 0.02], [0.08, 0.08, 0.001], [0.5, 0.5, 0.4]
    closeups = {name: {"size": size, "drawn_by": "pro", "takes": {"pro": []}}
                for name, size in (("rug", rug), ("note", note), ("crate", crate))}
    folder = pathlib.Path(tempfile.mkdtemp())
    (folder / "closeups.json").write_text(json.dumps({"objects": closeups}))
    a_closeup_picture(folder, "rug", (156, 56, 356, 456))  # 2 by 3, seen from straight above
    a_closeup_picture(folder, "note", (156, 156, 356, 356))
    at = predict.LATER_TAKES_SINCE
    store.write_accept("closeup@lab", {"output": store.put_tree(folder), "at": at})
    store.write_accept("pixal@lab", {"output": a_stored_output(store, {"batch-gaps.json": {"gaps": [
        {"row": "pixal", "objects": [name, f"lab_{name}"]} for name in ("rug", "note", "crate")]}}), "at": at})
    measures = predict.environment_measures(store, ["lab"])["lab"]

    def own(name, size):
        take = {"place": "lab", "rows": [name], "take": f"lab_{name}", "size": size}
        return predict.own_outcome(take, {"id": name, "name": name, "noun": name, "size": size}, measures)
    assert own("rug", rug)["outcome"] == "pass", own("rug", rug)  # built from its close-up, its outline matches
    # 1 mm: under the model gate's 3 mm wall, held as a solid of its own thickness (gates/model.py least_wall)
    assert own("note", note)["outcome"] == "pass", own("note", note)
    assert own("crate", crate)["outcome"] == "at risk"  # no sheet: no code build after Pixal3D


def test_a_thin_straight_row_is_predicted_by_its_code_build_against_its_stored_mask():
    import numpy as np
    from PIL import Image
    from score.store import Store
    store = Store.in_folder(tempfile.mkdtemp())
    folder = pathlib.Path(tempfile.mkdtemp())
    (folder / "cuts").mkdir()
    pixels = np.zeros((300, 300, 4), dtype=np.uint8)
    pixels[20:280, 140:160] = (90, 90, 90, 255)  # a post upright in its crop, cut out by its mask
    Image.fromarray(pixels).save(folder / "cuts" / "post.png")
    pixels[:] = 0
    pixels[100:200, 100:200] = (90, 90, 90, 255)  # the mask found a box, no rod: no thin thing, no build
    Image.fromarray(pixels).save(folder / "cuts" / "rod.png")
    pixels[:] = 0
    pixels[140:160, 20:280] = (90, 90, 90, 255)  # a lying beam where the reading's box stands it upright
    Image.fromarray(pixels).save(folder / "cuts" / "beam.png")
    (folder / "masks.json").write_text(json.dumps({"asked": ["post", "rod", "pipe", "beam"],
                                                   "cut": ["post", "rod", "beam"]}))
    store.write_accept("straight-masks@lab", {"output": store.put_tree(folder), "at": predict.LATER_TAKES_SINCE})
    measures = predict.environment_measures(store, ["lab", "hub"])
    assert set(measures) == {"lab"}, measures  # a place with masks and no close-up is measured
    rates, size = predict.hub_rates(), [0.1, 0.1, 2.0]

    def guess(name):
        take = {"place": "lab", "rows": [name], "take": f"lab_{name}", "size": size}
        row = {"id": name, "name": name, "noun": "post", "size": size}
        return predict.own_outcome(take, row, measures["lab"]) or predict.predicted(size, rates, row, take,
                                                                                    measures["lab"])
    assert guess("post")["outcome"] == "pass", guess("post")
    assert guess("rod")["outcome"] == "predicted gap" and "no thin thing" in guess("rod")["mode"], guess("rod")
    assert guess("pipe")["outcome"] == "predicted gap" and "SAM 3" in guess("pipe")["mode"]
    assert guess("beam")["outcome"] == "pass", guess("beam")  # built lying: the direction is the picture's
    assert guess("strut")["outcome"] == "at risk"  # not asked: its likeness is not measured yet


def test_a_pipe_whose_close_up_passed_is_predicted_by_its_code_build():
    """The qualifying check decides (thin_straight.coded): a pipe whose close-up passed is predicted by its code build,
    with or without another pipe failing its own, as the Pixal3D row builds it; a crate is not."""
    import numpy as np
    from PIL import Image
    from score.store import Store
    store = Store.in_folder(tempfile.mkdtemp())
    at, pipe = predict.LATER_TAKES_SINCE, [3.0, 0.1, 0.1]
    store.write_accept("closeup@lab", {"output": a_stored_output(store, {"closeups.json": {"objects": {
        "pipe": {"size": pipe, "drawn_by": None, "takes": {"pro": ["x"]}},
        "pipe_2": {"size": pipe, "drawn_by": "pro", "takes": {"pro": []}},
        "crate": {"size": [0.5, 0.5, 0.4], "drawn_by": "pro", "takes": {"pro": []}}}}}), "at": at})
    folder = pathlib.Path(tempfile.mkdtemp())
    (folder / "cuts").mkdir()
    pixels = np.zeros((300, 300, 4), dtype=np.uint8)
    pixels[146:155, 20:280] = (90, 90, 90, 255)  # a 3 m pipe 0.1 m thick, lying
    for name in ("pipe", "pipe_2"):
        Image.fromarray(pixels).save(folder / "cuts" / f"{name}.png")
    (folder / "masks.json").write_text(json.dumps({"asked": ["pipe", "pipe_2"], "cut": ["pipe", "pipe_2"]}))
    store.write_accept("straight-masks@lab", {"output": store.put_tree(folder), "at": at})
    measures = predict.environment_measures(store, ["lab"])["lab"]
    rows = {name: {"id": name, "name": "wall pipe", "noun": "pipe", "size": pipe, "box": [0, 0, 300, 20]}
            for name in ("pipe", "pipe_2")}
    rows["crate"] = {"id": "crate", "name": "crate", "noun": "crate", "size": [0.5, 0.5, 0.4], "box": [0, 0, 9, 9]}

    def own(name, place_rows):
        take = {"place": "lab", "rows": [name], "take": f"lab_{name}", "size": rows[name]["size"]}
        return predict.own_outcome(take, rows[name], measures, place_rows)
    found = own("pipe_2", rows)
    assert found["outcome"] == "pass" and "thin_straight.coded" in found["measured"], found
    alone = own("pipe_2", {name: rows[name] for name in ("pipe_2", "crate")})
    assert "thin_straight.coded" in alone["measured"], alone  # no failed pipe beside it: built in code all the same
    assert "thin_straight.coded" not in own("pipe_2", {})["measured"]  # no inventory row: no route known
    assert own("pipe", rows)["outcome"] == "pass" and "coded" not in own("pipe", rows)["measured"]
    assert "coded" not in own("crate", rows)["measured"]


def test_inputs_break_their_contract_on_an_unknown_view_a_missing_picture_or_no_box():
    work = pathlib.Path(tempfile.mkdtemp())
    (work / "scene").mkdir()
    (work / "scene" / "v1.png").write_bytes(b"x")
    record = {"plan": {"views": [{"id": "v1", "picture": "WORK/scene/v1.png"}, {"id": "v2", "picture": "WORK/x.png"}]}}
    good = {"view": "v1", "box": [0, 0, 10, 10], "size": [1, 1, 1]}
    assert contract.faults(record, good, work) == []
    assert "not in the work folder" in contract.faults(record, {**good, "view": "v2"}, work)[0]
    assert "not one of the plan's views" in contract.faults(record, {**good, "view": "v9"}, work)[0]
    assert contract.faults(record, {**good, "box": [5, 5, 5, 9]}, work) == ["box [5, 5, 5, 9] has no area"]
    assert contract.upscale([0, 0, 100, 50]) == 3.66 and contract.upscale([0, 0, 1000, 500]) == 1.0


def test_the_first_class_in_the_kinds_order_is_fixed_in_its_zone_with_the_best_boot_record():
    entries = [{"kind": "pixal", "machines": [{"type": "L4", "zone": "a"}, {"type": "L4", "zone": "b"}],
                "attempts": [{"type": "L4", "zone": "a", "started": False, "why": "no answer"},
                             {"type": "L4", "zone": "b", "started": False, "why": machines.OUT_OF_STOCK}]}]
    records = machines.boot_records(entries, {"L4": "gpu-24gb"})
    assert records[("pixal", "gpu-24gb", "b")] == {"up": 1, "failed": 0, "out_of_stock": 1}, records
    cap = machines.capacity()
    chosen = machines.fixed("pixal", records, cap)
    assert (chosen["class"], chosen["zone"]) == ("gpu-24gb", "b"), chosen
    Offer = collections.namedtuple("Offer", "machine_class zone stock_word")
    short = [Offer("gpu-24gb", "b", machines.SHORTAGE), Offer("gpu-24gb", "a", "available")]
    assert machines.fixed("pixal", records, cap, short)["zone"] == "a"
    none_stocked = machines.fixed("pixal", records, cap, [Offer("cpu-4c-32gb", "a", "available")])
    assert none_stocked["class"] == "gpu-24gb" and "never gaps" in none_stocked["why"], none_stocked
    assert machines.fixed("closeup", records, cap) is None  # Google calls rent nothing


def test_layers_run_each_take_once_a_shell_piece_through_the_whole_route_and_cards_carry_the_bill_share():
    rules = estimate.one_shot()
    route = ["closeup", "pixal", "finish-route-list", "surfaces-bake", "likeness-calibration"]
    bought = [{"shell": False}, {"shell": False}, {"shell": True}]
    found = estimate.layers(route, bought, rules, {})
    # a shell piece too: the finish route lists its library surface, so the bake that bakes listed takes bakes it
    assert {stage: layer["takes"] for stage, layer in found.items()} == dict.fromkeys(route, 3)
    assert found["finish-route-list"]["units"] == 3  # one list ask a take
    unmeasured = found["likeness-calibration"]
    assert unmeasured["units"] is None and unmeasured["price"]["likely_euros"] is None
    pixal = compute.per_unit("pixal")
    assert found["pixal"]["price"]["likely_euros"] == round(pixal["likely_euros"] * 3 * price.BILL_SHARE, 2)
    assert found["closeup"]["price"]["bill_share"] == 1.0  # Google calls are billed as the ledger says
    assert found["pixal"]["settings"]["deadline_seconds"] is not None or found["pixal"]["settings"]["deadline_why"]
    assert estimate.totals(found)["unpriced"] == ["likeness-calibration"]


def test_the_eta_walks_the_layers_in_the_routes_order_and_a_layer_of_no_units_takes_no_time():
    runner = stages.runner(world=stages.WORLDS["world1"]())
    route = price.route_stages(runner)
    edges = estimate.route_edges(runner.stages, route)
    assert ("closeup", "pixal") in edges and ("finish-route-list", "surfaces-bake") in edges, edges
    none_asked = {**estimate.one_shot(), "surfaces-parts": (0, "a layer that makes no units")}
    found = estimate.layers(["pixal", "surfaces-parts"], [{"shell": False}] * 30, none_asked, {})
    walked = estimate.eta(found, [("pixal", "surfaces-parts")], 8, 50)
    assert walked["unknown"] == [] and walked["likely_minutes"] == found["pixal"]["minutes"]["likely_minutes"], walked


def test_the_benchmarks_stay_under_their_cap_and_ask_the_months_guard():
    listed = benchmarks.listed()
    assert len(listed) == 7 and benchmarks.high_with_guesses(listed) < benchmarks.CAP_EUROS
    rows = {row.name for row in stages.STAGES}  # a retired row (earth-kit, 2026-10-21) is no benchmark's buy
    assert all(set(each.get("buys", ())) <= rows for each in benchmarks.BENCHMARKS), benchmarks.BENCHMARKS
    running = [each for each in listed if not each["gap"]]
    assert [each["id"] for each in listed if each["gap"]] == ["gemini-batch-direct"]
    assert all(each["command"].count("score run") == 1 for each in running)
    assert all((each["high_euros"] is None) == (each["guess_euros"] is not None) for each in running)
    assert all(each["likely_minutes"] and each["high_minutes"] >= each["likely_minutes"] for each in running)
    over = benchmarks.guard([{"likely_euros": 1.0, "high_euros": 1.0, "guess_euros": benchmarks.CAP_EUROS}])
    assert "cap" in over["refusal"] and over["total_euros"] == 1.0  # the guesses count against the cap


def test_the_benchmarks_guard_under_the_kill_latch_is_a_refusal_and_the_figure_stands():
    import os
    name = compute.ledger().FREE_ONLY
    before = os.environ.get(name)
    os.environ[name] = "1"  # the sync pass runs free only while the latch holds
    try:
        found = benchmarks.guard([{"likely_euros": 1.0, "high_euros": 1.0}])
    finally:
        if before is None:
            del os.environ[name]
        else:
            os.environ[name] = before
    assert "free only" in found["refusal"] and found["total_euros"] == 1.0


def test_a_benchmark_whose_inputs_do_not_stand_is_a_gap_and_the_rest_run_once():
    import types
    pixal = benchmarks.BENCHMARKS[0]
    plan = {"missing": [], "blocked": {}, "refusal": None, "buys": [{"node": "pixal@cockpit"}]}
    assert benchmarks.plan_gap(pixal, plan) is None
    assert "not standing" in benchmarks.plan_gap(pixal, {**plan, "missing": ["closeup@cockpit: no picture"]})
    assert "also buy closeup@cockpit" in benchmarks.plan_gap(pixal, {**plan, "buys": [{"node": "closeup@cockpit"}]})
    assert "buys nothing" in benchmarks.plan_gap(pixal, {**plan, "buys": []})
    calls = []

    def call(command, **_):
        calls.append(command[3])
        lost = command[3] == "plan" and "sound" in command
        stood = {**plan, "missing": ["sound@square: lost"] if lost else [],
                 "buys": [{"node": f"{word}@x"} for flag, word in zip(command, command[1:]) if flag == "--stage"]}
        return types.SimpleNamespace(returncode=0, stdout=json.dumps(stood), stderr="")
    records = pathlib.Path(tempfile.mkdtemp())
    assert benchmarks.batch(call, records) == 0
    (record,) = [json.loads(path.read_text()) for path in records.glob("*.json")]
    found = {each["id"]: each for each in record["benchmarks"]}
    assert "sound@square: lost" in found["sound"]["gap"] and found["gemini-batch-direct"]["gap"]
    assert found["pixal-l4"]["exit"] == 0 and calls.count("run") == 5 and calls.count("plan") == 6


def a_read_row(row_id, kind, noun, count=1, terrain=False, part="object"):
    """A scene inventory reading's row (score/review/reading.py's shape: no metres, SAM 3's boxes, its part)."""
    boxes = [[10.0 * number, 0.0, 10.0 * number + 8, 8.0] for number in range(count)]
    return {"id": row_id, "name": row_id, "noun": noun, "kind": kind, "terrain": terrain, "count": count, "part": part,
            "anchor": "floor", "where": "here", "region": [0, 0, 100, 100], "view": "v1", "box": boxes[0],
            "boxes": boxes, "size": None, "size_words": "waist high", "thing": ""}


def a_read_store(place, sha, rows, concept=None, picture=None):
    """A store with `place`'s draw `sha` picked and one reading of `concept` (else of the pick) by today's method,
    its picture `picture` pixels wide and high (None: not said)."""
    from score.review import concepts, reading
    from score.store import Store
    store = Store.in_folder(tempfile.mkdtemp())
    store.write_once(f"concepts/{place}/draws/1.json", {"place": place, "sha": sha, "at": "2026-10-21T09:00"})
    concepts.pick(store, place, sha, "joey")
    store.objects.path(f"blobs/{sha}").parent.mkdir(parents=True, exist_ok=True)
    store.objects.path(f"blobs/{sha}").write_bytes(b"the picked draw")
    read = concept or sha
    reading.kept(store, {"place": place, "concept": read, "at": "2026-10-21T10:00:00Z", "method": reading.METHOD,
                         "inventory": {"scene": place, "place": place, "concept_pick": {"sha256": read},
                                       "rows": rows},
                         "gaps": [], "euros": {"rows": 0.03, "boxes": 0.01, "total": 0.04},
                         **({"size": picture} if picture else {})})
    written(store, place)
    return store


def written(store, place):
    """The place's plan written from its reading (plan_writing's record): its design done, so it is a place of the
    build (stages.places: no plan is filed in the data since 2026-10-21)."""
    from score.review import concepts, plan_writing, plans
    shown = plans.current(store, place)
    if shown is None:
        return
    plan = shown["plan"]  # the rough plan, less the items of rows its reading gave no size (no size of its own)
    unsized = {gap["row"] for gap in plan.get("gaps", []) if gap["kind"] == "size"}
    plan = {**plan, "items": [item for item in plan["items"] if not set(plan["rows"].get(item[0], [])) & unsized]}
    plan_writing.kept(store, {"place": place, "concept": concepts.picked(store, place),
                              "reading": plan_writing.reading_at(store, place), "method": plan_writing.METHOD,
                              "by": "test", "at": concepts.now(), "plan": plan})


def test_a_take_is_sized_by_its_reading_and_routed_by_its_part():
    rows = [{**a_read_row("fuel_drum", "generate", "drum", 2), "size": [0.6, 0.6, 0.9]},
            a_read_row("astronaut", "generate", "astronaut"),
            {**a_read_row("wall_lamp", "code", "wall lamp"), "anchor": "wall", "size": [0.3, 0.2, 0.4]},
            {**a_read_row("night_sky", "generate", "sky", part="sky"), "anchor": "sky"}]
    store = a_read_store("wreck", "a" * 64, rows, picture=[100, 100])
    found, _ = groups.current(store, ["wreck"])
    by_id = {row["id"]: row for row in found["wreck"]["rows"]}
    assert by_id["fuel_drum"]["size"] == [0.6, 0.6, 0.9], by_id["fuel_drum"]  # its plan item, laid at its metres
    assert by_id["wall_lamp"]["size"] == [0.3, 0.2, 0.4]  # no item of its own: its reading's metres
    assert by_id["astronaut"]["size"] is None and by_id["night_sky"]["size"] is None  # none read: a gap
    post, footprint, edited = [0.1, 0.1, 2.5], [0.484, 1.699, 2.5], [0.3, 0.3, 2.5]
    assert groups.row_size(post, footprint) == post  # a plan's item only places the object
    assert groups.row_size(post, edited) == post  # an edited item too: the assembly fits the object to it
    assert groups.row_size(None, footprint) == footprint and groups.row_size(None, None) is None
    pipes, floor = [12.0, 0.1, 0.1], [7.421, 4.058, 0.1]  # a run's whole length, laid along the stairwell's walls
    assert groups.row_size(pipes, floor, 4) == [3.0, 0.1, 0.1]  # one of its four pieces, laid along the item
    railing, ring = [50.0, 0.1, 1.0], [8.837, 9.435, 1.0]  # round a floor's edge: each piece held to the item laid
    assert groups.row_size(railing, ring, 5) == [9.435, 0.1, 1.0]
    assert groups.own_size(railing, ring, 5) == [9.435, 0.1, 1.0]  # its close-up draws the piece, not the 50 m run
    assert groups.own_size(post, footprint, 3) == post and groups.own_size(None, footprint) is None
    lamp = {"id": "street_lamp", "route": "prop", "part": "object"}
    assert groups.routed(lamp, set(), {"street_lamp"})["route"] == "skyline"  # beyond the place: the backdrop's
    sea = {"id": "sea", "name": "sea", "noun": "sea", "terrain": True, "part": "backdrop", "route": "skyline"}
    assert groups.routed(sea, set(), set())["route"] == "ground"  # 2026-10-26: no maker; the terrain's water now
    assert groups.routed(lamp, set(), set()) == lamp
    assert groups.routed({**lamp, "route": "sky"}, set(), {"street_lamp"})["route"] == "sky"
    hills = {"id": "distant_hills", "part": "ground", "terrain": True, "route": "ground"}  # 2026-10-26: no maker
    far = {**hills, "part": "backdrop", "route": "skyline"}
    assert groups.routed(far, set(), {"distant_hills"})["route"] == "ground"  # the terrain's far ground raises it
    assert groups.routed(hills, set(), set()) == hills  # not beyond: the ground row itself
    beam = [9.0, 0.3, 0.3]  # one object longer than its item: kept at its own size, so `fits the plan` still rejects it
    assert groups.row_size(beam, [3.0, 0.3, 0.3], None) == beam
    assert groups.row_size(post, footprint, 3) == post  # a run's piece that fits its item is its own size
    plan = {"items": [["PIPES 1", 0, 0, 7.4, 4.0, None, "item"], ["RAIL 1", 0, 0, 9, 9, None, "item"]],
            "rows": {"PIPES 1": ["pipes"], "RAIL 1": ["rail"]}, "shapes": {"RAIL 1": {"shape": "polygon"}}}
    assert groups.run_pieces(plan, {"id": "pipes", "count": 4}) == 4 and groups.run_pieces(plan, {"id": "rail"}) == 1
    assert groups.run_pieces(plan, {"id": "pipes", "count": 1}) is None  # one item of one: a single object
    rugs = {"items": [[f"RUG {n}", 0, 0, 1.433, 1.444, None, "item"] for n in (1, 2, 3)],
            "rows": {f"RUG {n}": ["rug"] for n in (1, 2, 3)}}
    rug = {"id": "rug", "count": 3, "size": [2.0, 1.5, 0.02]}  # one rug an item, a little over it: one of it, no run
    assert groups.run_pieces(rugs, rug) is None and groups.row_size(rug["size"], [1.433, 1.444, 0.02]) == rug["size"]
    assert groups.run_pieces(rugs, {**rug, "size": [9.0, 0.1, 0.1]}) == 3  # longer than its items end to end: a run
    door = [1.2, 0.2, 2.1]  # four doors read, one 1.16 m item laid: the door a little wider than its footprint
    assert groups.row_size(door, [1.159, 0.706, 2.1], 4) == door
    assert groups.own_size(door, [1.159, 0.706, 2.1], 4) == door
    rug = [2.0, 1.5, 0.02]  # ten rugs read on a smaller item: no line along the ground, so no run
    assert groups.own_size(rug, [1.433, 0.4, 0.02], 10) == rug
    shell = {"structure": ["building_shell", "sky"]}
    assert groups.plan_structure(shell, {"floor", "wall", "roof"}) == {"building_shell", "sky"}
    assert groups.plan_structure(shell, {"floor"}) == set()  # an open place's plan lays no walls: none is laid
    building = {"id": "building_shell", "route": "shell", "part": "structure"}
    assert groups.routed(building, {"wall"}, set(), {"building_shell"})["route"] == "plan"  # never a close-up
    assert groups.routed(building, {"wall"}, set(), set()) == building
    ribs = {"id": "ribs", "name": "arched structural ribs", "noun": "ribs", "part": "structure", "route": "shell",
            "size": [3.2, 0.2, 3.2]}  # the tube's: its box the whole picture, laid by the shell at its plan items
    tube = {"items": [["RIBS 1", 0, 0, 9.3, 0.22, None, "item"]], "rows": {"RIBS 1": ["ribs"]}}
    assert groups.plan_arches(tube, [ribs]) == {"ribs"} and groups.plan_arches({}, [ribs]) == set()
    assert groups.routed(ribs, set(), set(), groups.plan_arches(tube, [ribs]))["route"] == "plan"
    assert [by_id[name]["route"] for name in ("fuel_drum", "astronaut", "wall_lamp", "night_sky")] == [
        "prop", "people", "prop", "sky"]
    runner = stages.runner(store=store, world=stages.WORLDS["world1"]())
    record = prepare.remake(runner, REPO / "data", None, pathlib.Path(tempfile.mkdtemp()))
    takes = {take["rows"][0]: take for take in record["takes"]}
    assert "no size of three sides" not in takes["fuel_drum"]["inputs"] and takes["night_sky"]["inputs"] == []
    assert "no size of three sides" not in takes["wall_lamp"]["inputs"]
    assert "no size of three sides" in takes["astronaut"]["inputs"]  # the reading's gap stays the take's
    assert takes["astronaut"]["status"] == "input gap"  # so it is not bought: priced apart, never a stopped line
    assert "motion" not in record["layers"] and record["layers"]["sky"]["takes"] == 1
    assert record["layers"]["pixal"]["takes"] == 2 and "sky" in record["totals"]["unpriced"]  # the sky: no prop route
    assert record["counts"]["input_gaps"] == 1 and record["input_gaps_if_bought"]["likely_euros"] > 0


def test_a_backdrop_row_a_place_of_its_scene_makes_is_shown_from_there_with_no_take_or_euros(tmp=None):
    """Batch 1 try 4: the stairwell's palms, lamps and lanterns seen through its window and the street's far rocket
    are the square's and the street's own objects; the skyline shows them from there, never a second take."""
    folder = pathlib.Path(tmp or tempfile.mkdtemp())
    (folder / "square.json").write_text(json.dumps({"holds": [{"place": "stairwell"}, {"place": "street"}]}))
    assert groups.scene_places("stairwell", folder) == ["square", "street"] and groups.scene_places("square", folder) == []
    sky = "skyline"
    read = {"square": {"rows": [{"id": "palm_tree", "route": "prop"}, {"id": "rocket", "route": "prop"},
                                {"id": "city_skyline", "route": sky}]},
            "street": {"rows": [{"id": "red_paper_lantern", "route": "prop"}, {"id": "palm_tree_2", "route": sky}]}}
    rows = [{"id": "palm_tree", "route": sky}, {"id": "distant_rocket", "route": sky},
            {"id": "red_lanterns", "route": sky}, {"id": "person_man", "route": sky}, {"id": "city_skyline", "route": sky},
            {"id": "stage", "route": "prop"}]
    shown = {row["id"]: row for row in groups.shown_from("stairwell", rows, read, folder)}
    found = {name: row.get("shown") for name, row in shown.items()}
    assert found == {"palm_tree": {"place": "square", "row": "palm_tree"},
                     "distant_rocket": {"place": "square", "row": "rocket"},
                     "red_lanterns": {"place": "street", "row": "red_paper_lantern"},
                     "person_man": None, "city_skyline": {"place": "square", "row": "city_skyline"},
                     "stage": None}  # the square, a top scene, makes its own skyline: the stairwell shows it
    assert shown["person_man"]["route"] == "prop" and shown["person_man"]["far"] == {"pieces": 1, "length": 0.0}
    group = groups.group_of("stairwell", {"rows": rows}, {**rows[0], "shown": found["palm_tree"]}, ("palm_tree", None, None))
    take = prepare.take_entry(group, {"rows": rows}, {}, predict.hub_rates(), folder)
    assert take["status"] == prepare.SHOWN  # bought and priced in the square: never bought here, so no skyline euros
    assert prepare.take_counts([take])["shown_from_its_place"] == 1 and prepare.take_counts([take])["bought"] == 0
    skyline = {"id": "city_skyline", "route": sky, "size": [1000.0, 100.0, 100.0]}  # the square's: no scene there
    made = groups.shown_from("square", [skyline], read, folder)[0]  # 2026-10-26: no maker; now ordinary objects
    assert made["route"] == "prop" and "shown" not in made and made["far"] == {"pieces": 10, "length": 1000.0}
    assert made["size"] == made["read_size"] == [100.0, 100.0, 100.0]  # its close-up: one piece of the run
    assert predict.predicted(made["size"], predict.hub_rates())["outcome"] == "pass"  # a solid, no longer a rod


def test_a_far_row_of_one_piece_is_as_wide_as_its_box_shows_it():
    """2026-10-26: the square's 60 m rocket read 5 m wide (12:1), its SAM 3 box (boosters and fins) 3.8:1, and its one
    clean close-up failed the proportions on that alone. A far row keeps its read tall (its distance) and is as wide
    as its box shows at that distance; a loose Gemini region or a run of pieces keeps its size."""
    rocket = {"id": "rocket", "route": "skyline", "anchor": "sky", "size": [5.0, 5.0, 60.0],
              "box": [1978, 33, 2007, 143], "boxed_by": "SAM 3"}
    made = groups.far_made(rocket)
    assert made["size"] == made["read_size"] == [15.818, 15.818, 60.0] and made["far"]["pieces"] == 1
    assert groups.far_made({**rocket, "boxed_by": "Gemini"})["size"] == [5.0, 5.0, 60.0]
    assert groups.far_made({**rocket, "size": [30.0, 10.0, 20.0]})["size"] == [5.273, 1.758, 20.0]  # footprint kept
    assert groups.far_made({**rocket, "size": [1000.0, 100.0, 100.0]})["size"] == [100.0, 100.0, 100.0]  # a run
    assert predict.shape_of(made["size"]) == "solid"  # its outline no rod: the hub's solid rate
    with predict.prop_data.tools("props/closeup"):
        import check
    assert abs(math.log(3.82 / check.expected_proportion(made["size"]))) < check.PROPORTION_LIMIT  # its clean take


def test_a_backdrop_part_of_a_structure_is_shown_by_a_neighbours_structure_else_made_far_here(tmp=None):
    """Batch 1: the stairwell's lit and dark windows, on the walls of the buildings seen through its window, are the
    square's buildings' (their finish lights them); a part no neighbour's structure holds is made here, far off."""
    folder = pathlib.Path(tmp or tempfile.mkdtemp())
    (folder / "square.json").write_text(json.dumps({"holds": [{"place": "stairwell"}]}))
    read = {"square": {"rows": [{"id": "floodlight_tower", "route": "prop", "anchor": "on:plaza", "size": [2, 2, 18]},
                                {"id": "kiosk", "route": "shell", "anchor": "ground", "size": [2, 2, 1]},
                                {"id": "left_building", "route": "shell", "anchor": "ground", "size": [6, 2, 24]}]}}
    window = {"id": "window_lit", "route": "skyline", "anchor": "wall", "size": [1.5, 0.1, 2.0]}
    rocket = {"id": "rocket_launch", "route": "skyline", "anchor": "ground", "size": [5, 5, 60]}
    found = {row["id"]: row.get("shown") for row in groups.shown_from("stairwell", [window, rocket], read, folder)}
    assert found == {"window_lit": {"place": "square", "row": "left_building"}, "rocket_launch": None}
    alone = groups.shown_from("stairwell", [window], {"square": {"rows": read["square"]["rows"][:2]}}, folder)[0]
    assert alone.get("shown") is None and alone["route"] == "prop"  # no structure taller: made far off here
    wall = {"id": "exterior_wall", "route": "skyline", "part": "structure", "anchor": "on:lunar_surface",
            "size": [20.0, 1.0, 3.0]}  # a building's wall seen through the tube's glass: the base's building's
    assert groups.shown_from("tube", [wall], read, folder)[0].get("shown") is None  # the tube is no place of it
    (folder / "base.json").write_text(json.dumps({"holds": [{"place": "tube"}]}))
    assert groups.shown_from("tube", [wall], {"base": read["square"]}, folder)[0]["shown"] == {
        "place": "base", "row": "left_building"}


def test_a_row_the_reading_names_far_off_is_beyond_and_shown_by_its_kind():
    """Batch 1 try 4: the street's distant floodlights, flags and palms stand in the square past its end; its plan laid
    them in the street, not beyond, and their close-ups were drawn from a speck (the room behind, proportions off).
    The rows the plan checks leave outside on purpose (plan_checks.afar) are beyond, shown by the square's own."""
    rows = [{"id": "distant_floodlight", "box": [2055, 117, 2137, 319]}, {"id": "police_car", "box": [10, 900, 300, 1100]},
            {"id": "distant_crowd", "box": [1841, 407, 2303, 1536]}, {"id": "pram", "anchor": "on:police_car"}]
    assert groups.beyond_of({"beyond": ["pram"]}, rows, [2752, 1536]) == {"distant_floodlight"}  # at the foot: here
    assert groups.beyond_of(None, rows[:2], None) == {"distant_floodlight"}
    rocket = {"id": "rocket", "anchor": "sky", "box": [1978, 33, 2007, 143]}  # the square's, over the sea
    assert groups.beyond_of({"beyond": []}, [rocket, rows[1]], [2752, 1536]) == {"rocket"}  # in the sky: beyond
    folder = pathlib.Path(tempfile.mkdtemp())
    (folder / "square.json").write_text(json.dumps({"holds": [{"place": "street"}]}))
    read = {"square": {"rows": [{"id": "floodlight_tower_left", "route": "shell"}, {"id": "red_flag", "route": "prop"}]}}
    sky = [{"id": "distant_floodlight", "route": "skyline"}, {"id": "distant_red_flag", "route": "skyline"},
           {"id": "distant", "route": "skyline", "size": [1.0, 1.0, 1.0]}]
    found = {row["id"]: row.get("shown") for row in groups.shown_from("street", sky, read, folder)}
    assert found == {"distant_floodlight": {"place": "square", "row": "floodlight_tower_left"},
                     "distant_red_flag": {"place": "square", "row": "red_flag"}, "distant": None}  # no kind: no match


def test_a_row_at_the_picture_s_foot_is_never_beyond():
    """2026-10-26: the airlock's sandbags, piled at its picture's bottom edges, were listed beyond and nothing made
    them: a row a SAM 3 box of which reaches the picture's foot stands before the viewer, on the place's own ground."""
    sandbags = {"id": "sandbags", "box": [185, 1163, 392, 1264], "boxes": [[185, 1163, 392, 1264], [1968, 1499, 2110, 1536]]}
    far = {"id": "rocket", "box": [10, 20, 40, 300]}
    plan = {"beyond": ["sandbags", "rocket"]}  # the airlock's plan listed both beyond
    assert groups.beyond_of(plan, [sandbags, far], [2752, 1536]) == {"rocket"}  # one box at the foot: here
    assert groups.beyond_of(plan, [sandbags, far], None) == {"sandbags", "rocket"}  # no picture size: as the plan says


def test_a_row_is_routed_by_its_part_and_the_plan_lays_only_the_shell_it_draws():
    """Owner, 2026-10-25 ("no hax tho ... framework remember"): a person row goes to the people line by the row-kind
    rules, every other row by the part of the place its reading says it is, whatever its noun; a floor, wall, roof or
    opening is the plan's own only where the place's plan lays that piece (an enclosed place's decks, walls, roofs and
    written openings; an open place's raised levels), else a shell piece's model, whatever its size."""
    def route(noun, part):
        return groups.route_of({"noun": noun, "part": part})
    assert [route("man", "object"), route("lantern", "object"), route("regolith", "ground"), route("plaza", "object"),
            route("haze", "effect"), route("towers", "backdrop"), route("dome", "roof"), route("stairs", "structure")] \
        == ["people", "prop", "ground", "prop", "effects", "skyline", "shell", "shell"]
    room = {"w": 6.0, "d": 4.0, "walls": [{"from": [0, 0], "to": [6, 0]}], "openings": [{"kind": "door", "at": [3, 0], "wide": 1.0}]}
    raised = {"w": 30.0, "d": 30.0, "levels": [{"name": "deck", "height": 2.0,
                                                 "points": [[0, 0], [10, 0], [10, 10], [0, 10]]}]}
    assert groups.plan_parts(room) == {"floor", "wall", "roof", "opening"}
    assert groups.plan_parts({**room, "openings": []}) == {"floor", "wall", "roof"}
    assert groups.plan_parts(raised) == {"floor"} and groups.plan_parts({"w": 30.0, "d": 30.0}) == set()
    assert groups.plan_parts(None) == set()
    assert groups.read_row({"place": "p", "concept": "c" * 64}, a_read_row("plates", "generate", "plates",
                                                                           part="floor"))["group"] == "kit: floor"
    rows = [{**a_read_row("way_in", "code", "doorway", part="opening"), "size": [1.0, 0.2, 2.1]},
            {**a_read_row("big_floor", "code", "floor", part="floor"), "size": [40.0, 30.0, 0.2]},
            {**a_read_row("crate", "generate", "crate"), "size": [0.5, 0.4, 0.4]}]
    store = a_read_store("wreck", "f" * 64, rows, picture=[100, 100])
    runner = stages.runner(store=store, world=stages.WORLDS["world1"]())
    record = prepare.remake(runner, REPO / "data", None, pathlib.Path(tempfile.mkdtemp()))
    takes = {take["rows"][0]: take for take in record["takes"]}
    # an open place whose plan lays no shell: its doorway and its big floor stay shell models, never dropped
    assert takes["way_in"]["route"] == takes["big_floor"]["route"] == "shell", takes["big_floor"]
    assert takes["crate"]["status"] == "bought" and record["counts"]["laid_from_the_plan"] == 0
    found, _ = groups.current(store, ["wreck"])
    assert {row["id"]: row["route"] for row in found["wreck"]["rows"]}["big_floor"] == "shell"


def test_a_row_whose_part_is_not_read_is_an_input_gap_until_its_parts_are_asked():
    """A reading answered before `part` was asked: each row with no part has no route and its take is an input gap
    (never bought, never guessed a prop) until reading.parted asks them; its rows, boxes and plan stay as they were."""
    from score.review import reading
    store = a_read_store("wreck", "d" * 64, [{**a_read_row("crate", "generate", "crate"), "size": [0.5, 0.4, 0.4]}])
    record = reading.reading_of(store, "wreck")
    del record["inventory"]["rows"][0]["part"]
    store.objects.path(next(iter(store.objects.keys("inventory-readings/wreck/")))).write_text(json.dumps(record))
    found, waiting = groups.current(store, ["wreck"])
    assert waiting == [] and found["wreck"]["rows"][0]["route"] is None
    assert reading.unparted(store, ["wreck"]) == ["wreck"]
    runner = stages.runner(store=store, world=stages.WORLDS["world1"]())
    made = prepare.remake(runner, REPO / "data", None, pathlib.Path(tempfile.mkdtemp()))
    [take] = [take for take in made["takes"] if take["place"] == "wreck"]
    assert take["status"] == "input gap" and contract.PART_UNREAD in take["inputs"], take
    store.write_once("inventory-parts/wreck/1.json", {"place": "wreck", "reading": record["at"],
                                                       "parts": {"crate": "object"}})  # as reading.parted keeps it
    found, waiting = groups.current(store, ["wreck"])
    assert waiting == [] and found["wreck"]["rows"][0]["route"] == "prop"


def test_a_row_sam_3_missed_is_framed_by_gemini_and_one_with_neither_or_the_whole_picture_is_an_input_gap():
    unboxed = {"box": None, "boxes": []}
    rows = [{**a_read_row("crate", "generate", "crate"), **unboxed, "size": [0.5, 0.4, 0.4],
             "region": [500, 250, 750, 500]},
            {**a_read_row("drum", "generate", "drum"), **unboxed, "size": [0.6, 0.6, 0.9], "region": None},
            {**a_read_row("hall", "generate", "building"), "size": [12.0, 8.0, 12.0], "box": [0, 0, 100, 95]},
            {**a_read_row("chair", "generate", "chair"), "size": [0.5, 0.5, 0.9]},
            {**a_read_row("martian_ground", "generate", "ground", terrain=True, part="ground"), "box": [0, 0, 100, 100]}]
    store = a_read_store("wreck", "e" * 64, rows, picture=[100, 100])
    found, _ = groups.current(store, ["wreck"])
    by_id = {row["id"]: row for row in found["wreck"]["rows"]}
    assert (by_id["crate"]["box"], by_id["crate"]["boxed_by"]) == ([25, 50, 50, 75], "Gemini"), by_id["crate"]
    assert by_id["chair"]["boxed_by"] == "SAM 3" and "boxed_by" not in by_id["drum"]
    runner = stages.runner(store=store, world=stages.WORLDS["world1"]())
    record = prepare.remake(runner, REPO / "data", None, pathlib.Path(tempfile.mkdtemp()))
    takes = {take["rows"][0]: take for take in record["takes"]}
    assert takes["crate"]["status"] == takes["chair"]["status"] == "bought"
    assert (takes["drum"]["status"], takes["drum"]["inputs"]) == ("input gap", ["no box of four numbers"])
    assert takes["hall"]["status"] == "input gap" and "whole picture" in takes["hall"]["inputs"][0]
    assert takes["martian_ground"]["status"] == prepare.TERRAIN  # the terrain node's: no close-up, no take bought
    assert record["layers"]["pixal"]["takes"] == 2 and record["counts"]["input_gaps"] == 2
    handed = handin.hand_in("wreck", found["wreck"], record["takes"], prepare.design_route(runner))
    marks = {row["id"]: row.get("grounded") for row in handed["rows"]}
    assert marks["crate"] == handin.BOXED["Gemini"] and marks["chair"] == handin.GROUNDED and marks["drum"] is None
    assert set(handed["objects"]) == {"crate", "chair"}  # the gaps are listed, never handed to the loop
    assert handed["takes"][takes["drum"]["take"]]["stages"] == []  # so the runner counts none of them


def test_a_places_current_reading_is_its_inventory_and_a_place_with_none_waits():
    rows = [a_read_row("wooden_crate", "generate", "crate", 3), a_read_row("crate_2", "generate", "crate"),
            a_read_row("floor_plate", "code", "floor plate", part="floor"), a_read_row("wall_lamp", "code", "wall lamp"),
            a_read_row("boulder", "generate", "boulder", 2, terrain=True)]
    store = a_read_store("wreck", "a" * 64, rows)
    found, waiting = groups.current(store, ["wreck", "lab"])
    assert waiting == ["lab"] and list(found) == ["wreck"]
    taken = {group["rows"][0]: group for group in groups.place_groups("wreck", found["wreck"])}
    assert set(taken) == {"wooden_crate", "crate_2", "floor_plate", "wall_lamp", "boulder"}  # no size: a row a take
    assert taken["floor_plate"]["shell"] and not taken["wall_lamp"]["shell"] and not taken["boulder"]["shell"]
    assert taken["wooden_crate"]["take"] == "wreck_wooden_crate_aaaaaaaa" and taken["wooden_crate"]["instances"] == 3
    old = a_read_store("wreck", "a" * 64, rows, concept="b" * 64)  # read from an older concept: counts for nothing
    assert groups.current(old, ["wreck"]) == ({}, ["wreck"])


def test_the_remake_record_prices_the_read_places_and_counts_the_rest_as_waiting():
    store = a_read_store("wreck", "a" * 64, [a_read_row("fuel_drum", "generate", "drum", 6),
                                              a_read_row("wall_panel", "code", "wall", part="wall")])
    runner = stages.runner(store=store, world=stages.WORLDS["world1"]())
    record = prepare.remake(runner, REPO / "data", None, pathlib.Path(tempfile.mkdtemp()))
    assert record["inventory"]["read"] == ["wreck"] and "base" in record["inventory"]["waiting"]
    assert "launch" not in record["inventory"]["waiting"] + record["inventory"]["read"]  # a part: no concept
    assert {take["place"] for take in record["takes"]} == {"wreck"} and record["counts"]["shell_groups"] == 1
    assert record["counts"]["groups"] == 2 and record["counts"]["instances"] == 7
    assert record["line"].startswith("remake batch (estimate) of the 1 places with a scene inventory (")


def test_the_remake_record_counts_every_row_once_and_says_its_one_line():
    store = a_read_store("wreck", "a" * 64, [a_read_row("fuel_drum", "generate", "drum", 6),
                                              a_read_row("wall_panel", "code", "wall", part="wall")])
    runner = stages.runner(store=store, world=stages.WORLDS["world1"]())
    work = pathlib.Path(tempfile.mkdtemp())
    record = prepare.remake(runner, REPO / "data", None, work)
    counts = record["counts"]
    assert counts["groups"] == len(record["takes"])
    assert counts["library"] == 0 and record["library"]["root"] is None  # no library given: nothing matches
    assert counts["bought"] + counts["made"] + counts["input_gaps"] == counts["groups"]  # a predicted gap is bought
    assert counts["input_gaps"] == counts["groups"]  # this reading measures no size: every take an input gap
    assert all(take["inputs"] == ["no size of three sides"] for take in record["takes"])  # its picture is the blob
    assert "every job once" in record["line"]
    assert record["moved"] == {"not_run": "--moved not given"}
    assert record["across_places"]["takes"] <= counts["bought"]
    assert set(record["design"]["places"]) == set(stages.places(runner.world, runner.store)) == {"wreck"}


def test_the_runner_lists_and_prices_a_designed_places_takes_as_prepare_prices_them():
    from score.stages.props import prop_data
    from score.stages.surfaces import surface_data
    sha = "d" * 64
    rows = [{**a_read_row("fuel_drum", "generate", "drum", 2), "size": [0.6, 0.6, 0.9]},
            {**a_read_row("crate", "generate", "crate"), "size": [0.5, 0.4, 0.4]},
            {**a_read_row("wall_panel", "code", "wall", part="wall"), "anchor": "wall", "size": [1.2, 0.06, 1.1]},
            {**a_read_row("astronaut", "generate", "astronaut"), "size": [0.5, 0.4, 1.8]},
            {**a_read_row("night_sky", "generate", "sky", part="sky"), "anchor": "sky"}]
    store = a_read_store("wreck", sha, rows, picture=[100, 100])
    runner = stages.runner(store=store, world=stages.WORLDS["world1"]())
    record = prepare.remake(runner, REPO / "data", None, pathlib.Path(tempfile.mkdtemp()))
    route = prepare.design_route(runner)
    assert "likeness-calibration" not in route and "likeness-calibration" not in record["layers"]
    home = pathlib.Path(tempfile.mkdtemp())
    prop_data.DESIGN = home / "props"
    surface_data.DESIGN = stages.surfaces.data.DESIGN = home / "surfaces"  # the table's own import too
    try:
        assert handin.kept(store, record, route, ["wreck"]) == (["wreck"], ["wreck"])
        assert handin.kept(store, record, route, ["wreck"]) == (["wreck"], [])  # unchanged: no key moves
        assert prop_data.applies("wreck") and prop_data.pattern("wreck") == "{home}/design/props/wreck.json"
        assert prop_data.pixal_files("wreck")["inventory"] == prop_data.keyed("wreck")
        written = prop_data.path_of("wreck")
        before = prop_data.handin_part(written)
        handed = json.loads(written.read_text())
        for take in handed["takes"].values():
            take.update(status="made", stages=[])
        kept_text = written.read_text()
        written.write_text(json.dumps(handed))
        assert prop_data.handin_part(written) == before  # a pass marking takes made moves no row's key
        written.write_text(kept_text)
        assert surface_data.pattern("wreck") == "{home}/design/surfaces/wreck.json"
        bought = [take for take in record["takes"] if take["status"] == "bought"]
        assert all(sha[:8] in take["take"] for take in bought)  # a re-pick names new takes: their keys move
        models = sorted(take["take"] for take in bought if take["route"] in groups.MODEL_ROUTES)
        person = estimate.take_stages(route, next(take for take in bought if take["route"] == "people"))
        assert "people-body" in person and "motion" not in person, person  # its body after the model, not rigid motion
        assert price.design_takes("pixal@wreck") == models and price.design_takes("sound@wreck") is None
        assert sorted(surface_data.takes("wreck")) == models  # a shell piece's too: the bake bakes what is listed
        for stage in estimate.SCENE_ROWS:  # once a scene, priced from the measured Gemini answer until measured
            assert record["layers"][stage]["units"] == 1, record["layers"][stage]
            own = compute.per_unit(stage)
            measured = own is not None and own["stage"] == stage
            assert record["layers"][stage]["price"].get("estimated_from") == (None if measured else estimate.ASK_PRICED_AS)
        assert estimate.once_a_scene("rough-model") and record["layers"]["rough-model"]["units"] == 1  # not a take
        for stage, layer in record["layers"].items():  # every layer prepare priced, the runner's node priced the same
            if stage in estimate.SCENE_ROWS:
                continue
            units = price.forecast_units(f"{stage}@wreck", [], REPO / "data")
            assert units == layer["units"], (stage, units, layer["units"])
            if layer["price"]["likely_euros"] is not None:
                runner_price = compute.forecast_price(f"{stage}@wreck", units)
                assert round(runner_price["likely_euros"], 2) == layer["price"]["likely_euros"], stage
                assert round(runner_price["high_euros"], 2) == layer["price"]["high_euros"], stage
        handin.kept(store, record, route, [])  # a place no longer designed: its hand-in goes, its rows with it
        assert not prop_data.applies("wreck") and not surface_data.designed("wreck")
    finally:
        prop_data.DESIGN = surface_data.DESIGN = stages.surfaces.data.DESIGN = home / "none"


def test_a_design_row_s_bake_entry_and_kind_come_from_its_row_never_an_old_concept_s_details():
    """The hub's new console row shares its id with the old concept's console (its details, a quarter turn and two
    hand-set labels, retired with the old models on 2026-10-21). Its take is the design's: its kind its noun, so its
    materials are the place's palette; its entry no turn (the bake measures it over the take), no screens, cuts or
    decals."""
    row = {"id": "console", "name": "control console", "noun": "control console", "size": [1.6, 0.8, 1.1]}
    record = {"place": "hub", "rows": [row], "objects": {"console": {"route": "prop", "take": "console_ab12cd34"}}}
    found = handin.surface_record("hub", record)
    assert found["takes"]["console_ab12cd34"]["kind"] == "control_console"
    entry = found["bake"]["entries"]["console_1"]
    assert "base" not in entry and entry["screens"] == entry["cuts"] == entry["decals"] == [], entry
    assert entry["size"] == [1.6, 1.1, 0.8]  # x wide, y tall, z deep


def test_a_concept_review_draw_is_drawn_and_its_pick_picked_until_unlocked():
    from score.review import concepts
    from score.store import Store
    from score.review import reading
    data, store = pathlib.Path(tempfile.mkdtemp()), Store.in_folder(tempfile.mkdtemp())
    assert design.designs(store, data, ["a"])["places"]["a"]["concept"] == "missing"
    store.write_once("concepts/a/draws/1.json", {"place": "a", "sha": "f" * 64, "at": "2026-10-21T09:00"})
    assert design.designs(store, data, ["a"])["places"]["a"]["concept"] == "drawn"
    concepts.pick(store, "a", "f" * 64, "joey")
    assert design.designs(store, data, ["a"])["places"]["a"]["concept"] == "picked"
    assert design.designs(store, data, ["a"])["places"]["a"]["inventory"] == "to read"
    reading.kept(store, {"place": "a", "concept": "f" * 64, "at": "2026-10-21T10:00", "method": reading.METHOD,
                         "inventory": {"concept_pick": {"sha256": "f" * 64}, "rows": []}})  # read from the pick
    assert design.designs(store, data, ["a"])["places"]["a"]["inventory"] == "made"
    concepts.pick(store, "a", None, "joey")  # an unlock: its inventory is out of date again
    assert design.designs(store, data, ["a"])["places"]["a"]["concept"] == "drawn"
    assert design.designs(store, data, ["a"])["places"]["a"]["inventory"] is None


class Locked:
    """A test store of one locked place per name, with the accepts of the plan rows given ({node: accept}): the
    store's own records, its accepts handed in so the test writes no owner record."""
    SHA = "f" * 64

    def __init__(self, accepts=None):
        from score.store import Store
        self.store = Store.in_folder(tempfile.mkdtemp())
        self.accepts = accepts or {}
        self.store.current_accept = self.accepts.get

    def locked(self, place, room=None):
        """`place` drawn (on `room` of the plan above when given) and locked on that draw."""
        from score.review import concepts
        self.store.write_once(f"concepts/{place}/draws/1.json", {"place": place, "sha": self.SHA, "at": "2026-10-21T09:00",
                                                                 **({"room": room} if room else {})})
        concepts.pick(self.store, place, self.SHA, "joey")
        return concepts.records(self.store, place, "picks")[-1]["at"]

    def read(self, place, at, method=None):
        """A reading of `place`'s lock made at `at` (by today's reading METHOD unless `method`)."""
        from score.review import reading
        self.store.write_once(f"inventory-readings/{place}/{at}.json", {
            "place": place, "concept": self.SHA, "at": at, "by": "runner", "method": method or reading.METHOD,
            "inventory": {"rows": []}})

    def written(self, place, at, reading_at, method=None):
        """A plan of `place` written at `at` from its reading made at `reading_at` (today's METHOD unless `method`)."""
        from score.review import plan_writing
        self.store.write_once(f"plan-writings/{place}/{at}.json", {
            "place": place, "concept": self.SHA, "reading": reading_at, "at": at, "by": "runner",
            "method": method or plan_writing.METHOD, "plan": {"w": 4, "d": 3, "items": []}})

    def edited(self, place, at):
        """His edit of `place`'s plan made at `at` on its lock."""
        self.store.write_once(f"plans/{place}/edits/{at}.json", {
            "place": place, "plan": {"w": 4, "d": 3, "items": []}, "concept": self.SHA, "by": "joey", "at": at, "how": "edited"})


def test_a_design_is_approved_only_once_it_stands_whole_on_its_lock_else_it_waits_with_why():
    from score.review import plans
    data = pathlib.Path(tempfile.mkdtemp())
    (data / "places").mkdir()
    (data / "places" / "within.json").write_text(json.dumps({"within": {}, "shells": {}}))
    was = plans.DATA  # where within.json is read
    plans.DATA = data
    try:
        made = Locked()
        for place in ("done", "edited", "moved", "unread", "old_reading", "derived", "old_method", "read_again"):
            made.locked(place, room="the room it had" if place == "moved" else None)
            if place != "unread":
                made.read(place, "2026-10-21T10:00", method=-1 if place == "old_reading" else None)
        for place in ("done", "moved"):
            made.written(place, "2026-10-21T11:00", "2026-10-21T10:00")
        made.written("old_method", "2026-10-21T11:00", "2026-10-21T10:00", method=-1)
        made.edited("edited", "2026-10-21T11:00")
        made.edited("read_again", "2026-10-21T09:30")  # his edit before the reading in force: his edit wins
        places = sorted(["done", "edited", "moved", "unread", "old_reading", "derived", "old_method", "read_again",
                         "never"])
        found = design.designs(made.store, data, places)
    finally:
        plans.DATA = was
    why = {place: row["waits"] for place, row in found["places"].items()}
    assert why == {
        "done": None, "edited": None, "read_again": None,
        "moved": "room moved since its draw",
        "unread": "concept not locked, or its inventory not read from it",
        "old_reading": "concept not locked, or its inventory not read from it",  # no inventory file stands in now
        "derived": "plan not written by today's method", "old_method": "plan not written by today's method",
        "never": "concept not locked, or its inventory not read from it"}, why
    assert found["approved"] == ["done", "edited", "read_again"], found["approved"]
    assert {place for place, row in found["places"].items() if row["plan"] == "approved"} == set(found["approved"])


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(REPO / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
