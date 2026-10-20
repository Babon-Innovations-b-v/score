"""Prepare (this package): the free counts, the library match, the predicted outcome from the hub's measured table,
the input contract, the machines fixed from boot records and stock, the layers' one-shot units and prices, the ETA,
the benchmarks' guard, and the whole record over the repository's data with a sandbox work folder (no library, no
stock read, nothing bought).

Run: PROPS_HOME=$(mktemp -d) .venv/bin/python score/stages/complete/prepare/prepare_test.py
"""
import collections
import json
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[4]))

from score import stages  # noqa: E402
from score.adapters import compute  # noqa: E402
from score.stages.complete.holes import price  # noqa: E402
from score.stages.complete.prepare import (__main__ as prepare, benchmarks, contract, estimate, groups,  # noqa: E402
                                           library, machines, predict)

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


def test_a_library_model_matches_by_kind_and_ratio_and_code_built_ones_count_apart(tmp=None):
    root = pathlib.Path(tmp or tempfile.mkdtemp())
    entries = [("chair_1", "prop", "hub", "chair"), ("rack_1", "piece", "hub", "rack"), ("lost_1", "prop", "x", "y")]
    (root / "index").mkdir(parents=True)
    (root / "index" / "model.json").write_text(json.dumps({"entries": [
        {"address": f"model/{name}@1", "tags": {"model": [tag]}} for name, tag, _, _ in entries]}))
    for name, _, place, source in entries:
        folder = root / "entries" / "model" / name / "1"
        folder.mkdir(parents=True)
        (folder / "entry.json").write_text(json.dumps({"provenance": {"place": place, "source_name": source}}))
    inventories = {"hub": {"rows": [a_row("chair", [0.6, 0.6, 0.9]), a_row("rack", [0.6, 0.6, 1.9])]}}
    index = library.index(library.library_models(root), inventories)
    lab = {"rows": [a_row("chair", [0.62, 0.6, 0.95]), a_row("rack", [0.6, 0.6, 1.9])]}
    chair, rack = groups.place_groups("lab", lab)
    assert library.match(chair, index) == {"pipeline": ["model/chair_1@1"], "code": []}
    assert library.match(rack, index) == {"pipeline": [], "code": ["model/rack_1@1"]}
    assert len(index) == 2  # the model with no source row has no size and matches nothing


def test_the_hub_table_makes_every_rod_a_predicted_hole_and_a_lone_sheet_only_a_risk():
    rates = predict.hub_rates(REPO / "data")
    assert (rates["rod"]["failed"], rates["rod"]["of"]) == (5, 5), rates
    assert rates["sheet"]["of"] < predict.MIN_MEASURED
    rod = predict.predicted([0.1, 0.1, 1.0], rates)
    assert rod["outcome"] == "predicted hole" and rod["pass_share"] == 0.0 and "5 of 5" in rod["measured"], rod
    assert predict.predicted([1.4, 0.02, 0.9], rates)["outcome"] == "at risk"
    solid = predict.predicted([0.6, 0.6, 0.9], rates)
    assert solid["outcome"] == "pass" and 0 < solid["pass_share"] < 1, solid


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
    assert none_stocked["class"] is None and "holes" in none_stocked["why"]
    assert machines.fixed("closeup", records, cap) is None  # Google calls rent nothing


def test_layers_run_each_take_once_shells_skip_the_surface_line_and_cards_carry_the_bill_share():
    rules = estimate.one_shot()
    route = ["closeup", "pixal", "surfaces-maps", "surfaces-names", "surfaces-bake", "likeness-calibration"]
    bought = [{"shell": False}, {"shell": False}, {"shell": True}]
    found = estimate.layers(route, bought, rules, {})
    assert {stage: layer["takes"] for stage, layer in found.items()} == {
        "closeup": 3, "pixal": 3, "surfaces-maps": 2, "surfaces-names": 2, "surfaces-bake": 3,
        "likeness-calibration": 2}
    assert found["surfaces-maps"]["units"] == 2 * estimate.map_calls() and found["surfaces-names"]["units"] == 0
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
    assert ("closeup", "pixal") in edges and ("surfaces-paint", "surfaces-bake") in edges, edges
    found = estimate.layers(["pixal", "surfaces-names"], [{"shell": False}] * 30, estimate.one_shot(), {})
    walked = estimate.eta(found, [("pixal", "surfaces-names")], 8, 50)
    assert walked["unknown"] == [] and walked["likely_minutes"] == found["pixal"]["minutes"]["likely_minutes"], walked


def test_the_benchmarks_stay_under_their_cap_and_ask_the_months_guard():
    assert benchmarks.total() <= benchmarks.CAP_EUROS
    over = benchmarks.guard([{"euros": benchmarks.CAP_EUROS + 1}])
    assert "cap" in over["refusal"]
    assert all(each["command"] is None or each["command"].count("score run") == 1 for each in benchmarks.BENCHMARKS)


def test_the_remake_record_counts_every_row_once_and_says_its_one_line():
    runner = stages.runner(world=stages.WORLDS["world1"]())
    work = pathlib.Path(tempfile.mkdtemp())
    record = prepare.remake(runner, REPO / "data", None, work)
    counts = record["counts"]
    assert counts["groups"] == len(record["takes"])
    assert counts["library"] == 0 and record["library"]["root"] is None  # no library given: nothing matches
    assert counts["bought"] + counts["predicted_holes"] + counts["made"] == counts["groups"], counts
    assert counts["inputs_missing"] == counts["bought"]  # a sandbox work folder holds no view picture
    assert record["line"].startswith("remake batch (estimate): ") and "every job once" in record["line"]
    assert record["moved"] == {"not_run": "--moved not given"}
    assert record["across_places"]["takes"] <= counts["bought"]


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(REPO / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
