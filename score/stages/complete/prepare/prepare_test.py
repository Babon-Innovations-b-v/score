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
               ("box_1", "prop", "hub", "box", {"route": "r-today"}, "draft")]
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
    rates = predict.hub_rates(REPO / "data")
    assert (rates["rod"]["failed"], rates["rod"]["of"]) == (5, 5), rates
    assert rates["sheet"]["of"] < predict.MIN_MEASURED
    rod = predict.predicted([0.1, 0.1, 1.0], rates)
    assert rod["outcome"] == "predicted gap" and rod["pass_share"] == 0.0 and "5 of 5" in rod["measured"], rod
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
    assert none_stocked["class"] is None and "gaps" in none_stocked["why"]
    assert machines.fixed("closeup", records, cap) is None  # Google calls rent nothing


def test_layers_run_each_take_once_shells_skip_the_surface_line_and_cards_carry_the_bill_share():
    rules = estimate.one_shot()
    route = ["closeup", "pixal", "finish-route-list", "surfaces-bake", "likeness-calibration"]
    bought = [{"shell": False}, {"shell": False}, {"shell": True}]
    found = estimate.layers(route, bought, rules, {})
    assert {stage: layer["takes"] for stage, layer in found.items()} == {
        "closeup": 3, "pixal": 3, "finish-route-list": 2, "surfaces-bake": 3, "likeness-calibration": 2}
    assert found["finish-route-list"]["units"] == 2  # one list ask a take
    unmeasured = found["likeness-calibration"]
    assert unmeasured["units"] is None and unmeasured["price"]["likely_euros"] is None
    pixal = compute.per_unit("pixal")
    assert found["pixal"]["price"]["likely_euros"] == round(pixal["likely_euros"] * 3 * price.BILL_SHARE, 2)
    assert found["closeup"]["price"]["bill_share"] == 1.0  # Google calls are billed as the ledger says
    assert found["pixal"]["settings"]["deadline_seconds"] is not None or found["pixal"]["settings"]["deadline_why"]
    assert estimate.totals(found)["unpriced"] == ["likeness-calibration"]


def test_the_clips_layer_is_priced_from_its_measured_per_unit_once_it_has_one():
    from score.stages.library import clips
    found = estimate.clip_layer({"hub": 9, "lab": 1, "flat": 0}, 50)
    measured = compute.per_unit(clips.ROW)
    assert measured is not None  # library-clips-sample, 2026-10-21 (tools/costs/per_unit.py RECORDED)
    assert found["units"] == 10 and "estimated_from" not in found["price"]
    assert found["price"]["likely_euros"] == round(measured["likely_euros"] * 10 * price.BILL_SHARE, 2)
    # the hub's 9 clips on two cards (7 and 2), the lab's on one: the minutes are a card's 7 clips and one set-up
    time = measured["time"]
    one_card = round(time["setup_minutes"]["likely"] + 7 * time["unit_seconds"]["likely"] / 60, 1)
    assert found["minutes"] == {"likely_minutes": one_card, "high_minutes": one_card, "cards": 3}, found["minutes"]
    squeezed = estimate.clip_minutes({"hub": 9, "lab": 1}, 2)  # three cards' shares on two: a second round
    assert squeezed["cards"] == 2 and squeezed["likely_minutes"] > one_card + 80, squeezed


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
    assert len(listed) == 8 and benchmarks.high_with_guesses(listed) < benchmarks.CAP_EUROS
    running = [each for each in listed if not each["gap"]]
    assert [each["id"] for each in listed if each["gap"]] == ["gemini-batch-direct"]
    assert all(each["command"].count("score run") == 1 for each in running)
    assert all((each["high_euros"] is None) == (each["guess_euros"] is not None) for each in running)
    assert all(each["likely_minutes"] and each["high_minutes"] >= each["likely_minutes"] for each in running)
    over = benchmarks.guard([{"likely_euros": 1.0, "high_euros": 1.0, "guess_euros": benchmarks.CAP_EUROS}])
    assert "cap" in over["refusal"] and over["total_euros"] == 1.0  # the guesses count against the cap


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
    assert found["pixal-l4"]["exit"] == 0 and calls.count("run") == 6 and calls.count("plan") == 7


def a_read_row(row_id, kind, noun, count=1, terrain=False):
    """A scene inventory reading's row (score/review/reading.py's shape: no metres, SAM 3's boxes)."""
    boxes = [[10.0 * number, 0.0, 10.0 * number + 8, 8.0] for number in range(count)]
    return {"id": row_id, "name": row_id, "noun": noun, "kind": kind, "terrain": terrain, "count": count,
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
    return store


def test_a_take_is_sized_by_its_reading_and_routed_by_its_noun():
    rows = [{**a_read_row("fuel_drum", "generate", "drum", 2), "size": [0.6, 0.6, 0.9]},
            a_read_row("astronaut", "generate", "astronaut"),
            {**a_read_row("wall_lamp", "code", "wall lamp"), "anchor": "wall", "size": [0.3, 0.2, 0.4]},
            {**a_read_row("night_sky", "generate", "sky"), "anchor": "sky"}]
    store = a_read_store("wreck", "a" * 64, rows, picture=[100, 100])
    found, _ = groups.current(store, ["wreck"])
    by_id = {row["id"]: row for row in found["wreck"]["rows"]}
    assert by_id["fuel_drum"]["size"] == [0.6, 0.6, 0.9], by_id["fuel_drum"]  # its plan item, laid at its metres
    assert by_id["wall_lamp"]["size"] == [0.3, 0.2, 0.4]  # no item of its own: its reading's metres
    assert by_id["astronaut"]["size"] is None and by_id["night_sky"]["size"] is None  # none read: a gap
    assert [by_id[name]["route"] for name in ("fuel_drum", "astronaut", "wall_lamp", "night_sky")] == [
        "prop", "people", "prop", "sky"]
    runner = stages.runner(store=store, world=stages.WORLDS["world1"]())
    record = prepare.remake(runner, REPO / "data", None, pathlib.Path(tempfile.mkdtemp()))
    takes = {take["rows"][0]: take for take in record["takes"]}
    assert "no size of three sides" not in takes["fuel_drum"]["inputs"] and takes["night_sky"]["inputs"] == []
    assert "no size of three sides" not in takes["wall_lamp"]["inputs"]
    assert "no size of three sides" in takes["astronaut"]["inputs"]  # the reading's gap stays the take's
    assert record["layers"]["motion"]["takes"] == 1 and record["layers"]["sky"]["takes"] == 1
    assert record["layers"]["pixal"]["takes"] == 3 and "sky" in record["totals"]["unpriced"]  # the sky: no prop route


def test_a_places_current_reading_is_its_inventory_and_a_place_with_none_waits():
    rows = [a_read_row("wooden_crate", "generate", "crate", 3), a_read_row("crate_2", "generate", "crate"),
            a_read_row("floor_plate", "code", "floor plate"), a_read_row("wall_lamp", "code", "wall lamp"),
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
                                              a_read_row("wall_panel", "code", "wall")])
    runner = stages.runner(store=store, world=stages.WORLDS["world1"]())
    record = prepare.remake(runner, REPO / "data", None, pathlib.Path(tempfile.mkdtemp()))
    assert record["inventory"]["read"] == ["wreck"] and "base" in record["inventory"]["waiting"]
    assert "launch" not in record["inventory"]["waiting"] + record["inventory"]["read"]  # a part: no concept
    assert {take["place"] for take in record["takes"]} == {"wreck"} and record["counts"]["shell_groups"] == 1
    assert record["counts"]["groups"] == 2 and record["counts"]["instances"] == 7
    assert record["line"].startswith("remake batch (estimate) of the 1 places with a scene inventory (")


def test_the_remake_record_counts_every_row_once_and_says_its_one_line():
    store = a_read_store("wreck", "a" * 64, [a_read_row("fuel_drum", "generate", "drum", 6),
                                              a_read_row("wall_panel", "code", "wall")])
    runner = stages.runner(store=store, world=stages.WORLDS["world1"]())
    work = pathlib.Path(tempfile.mkdtemp())
    record = prepare.remake(runner, REPO / "data", None, work)
    counts = record["counts"]
    assert counts["groups"] == len(record["takes"])
    assert counts["library"] == 0 and record["library"]["root"] is None  # no library given: nothing matches
    assert counts["bought"] + counts["predicted_gaps"] + counts["made"] == counts["groups"], counts
    assert counts["inputs_missing"] == counts["bought"]  # a reading measures no size
    assert all(take["inputs"] == ["no size of three sides"] for take in record["takes"])  # its picture is the blob
    assert "every job once" in record["line"]
    assert record["moved"] == {"not_run": "--moved not given"}
    assert record["across_places"]["takes"] <= counts["bought"]
    assert record["design"]["places"]["garage"]["hint"] == "K04"  # the old plan's pick, a hint only
    assert set(record["design"]["places"]) == set(stages.places(runner.world))


def test_the_runner_lists_and_prices_a_designed_places_takes_as_prepare_prices_them():
    from score.stages.props import prop_data
    from score.stages.surfaces import surface_data
    sha = "d" * 64
    rows = [{**a_read_row("fuel_drum", "generate", "drum", 2), "size": [0.6, 0.6, 0.9]},
            {**a_read_row("crate", "generate", "crate"), "size": [0.5, 0.4, 0.4]},
            {**a_read_row("wall_panel", "code", "wall"), "anchor": "wall", "size": [1.2, 0.06, 1.1]},
            {**a_read_row("astronaut", "generate", "astronaut"), "size": [0.5, 0.4, 1.8]},
            {**a_read_row("night_sky", "generate", "sky"), "anchor": "sky"}]
    store = a_read_store("wreck", sha, rows, picture=[100, 100])
    runner = stages.runner(store=store, world=stages.WORLDS["world1"]())
    record = prepare.remake(runner, REPO / "data", None, pathlib.Path(tempfile.mkdtemp()))
    route = price.route_stages(runner)
    home = pathlib.Path(tempfile.mkdtemp())
    prop_data.DESIGN = home / "props"
    surface_data.DESIGN = stages.surfaces.data.DESIGN = home / "surfaces"  # the table's own import too
    try:
        assert handin.kept(store, record, route, ["wreck"]) == (["wreck"], ["wreck"])
        assert handin.kept(store, record, route, ["wreck"]) == (["wreck"], [])  # unchanged: no key moves
        assert prop_data.applies("wreck") and prop_data.pattern("wreck") == "{home}/design/props/wreck.json"
        assert prop_data.pixal_files("wreck")["inventory"] == prop_data.pattern("wreck")
        assert surface_data.pattern("wreck") == "{home}/design/surfaces/wreck.json"
        bought = [take for take in record["takes"] if take["status"] == "bought"]
        assert all(sha[:8] in take["take"] for take in bought)  # a re-pick names new takes: their keys move
        models = sorted(take["take"] for take in bought if take["route"] in groups.MODEL_ROUTES)
        assert price.design_takes("pixal@wreck") == models and price.design_takes("sound@wreck") is None
        assert sorted(surface_data.takes("wreck")) == sorted(take["take"] for take in bought if not take["shell"]
                                                             and take["route"] in groups.MODEL_ROUTES)
        for stage, layer in record["layers"].items():  # every layer prepare priced, the runner's node priced the same
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


class NoKeys:
    def keys(self, prefix):
        return []


class Accepts:
    """A store's current accepts, {node: accept}, and no concept review records."""
    def __init__(self, accepts):
        self.accepts = accepts
        self.objects = NoKeys()

    def current_accept(self, node):
        return self.accepts.get(node)


def test_a_concept_review_draw_is_drawn_and_its_pick_picked_until_unlocked():
    from score.review import concepts
    from score.store import Store
    data, store = pathlib.Path(tempfile.mkdtemp()), Store.in_folder(tempfile.mkdtemp())
    (data / "places").mkdir()
    (data / "places" / "concepts.json").write_text(json.dumps({"concepts": {"a": {"sha256": "1"}}}))
    store.write_once("concepts/a/draws/1.json", {"place": "a", "sha": "f" * 64, "at": "2026-10-21T09:00"})
    assert design.designs(store, data, ["a"])["places"]["a"]["concept"] == "drawn"
    concepts.pick(store, "a", "f" * 64, "joey")
    assert design.designs(store, data, ["a"])["places"]["a"]["concept"] == "picked"
    assert design.designs(store, data, ["a"])["places"]["a"]["inventory"] == "to read"
    (data / "inventory").mkdir()
    (data / "inventory" / "a.json").write_text(json.dumps({"concept_pick": {"sha256": "f" * 64}, "rows": []}))
    assert design.designs(store, data, ["a"])["places"]["a"]["inventory"] == "made"
    concepts.pick(store, "a", None, "joey")  # an unlock: its inventory is out of date again
    assert design.designs(store, data, ["a"])["places"]["a"]["concept"] == "drawn"
    assert design.designs(store, data, ["a"])["places"]["a"]["inventory"] is None


def test_a_design_is_approved_once_its_pick_has_its_inventory_and_so_its_plan():
    data = pathlib.Path(tempfile.mkdtemp())
    (data / "places").mkdir()
    (data / "places" / "concepts.json").write_text(json.dumps({"concepts": {
        "a": {"sha256": "1", "picked": "2026-10-21T09:00"}, "b": {"sha256": "2", "picked": "2026-10-21T09:00"},
        "c": {"sha256": "3", "picked": "2026-10-21T09:00"}, "d": {"sha256": "4"},
        "f": {"sha256": "6", "picked": "2026-10-21T09:00"}}}))
    (data / "inventory").mkdir()
    for place, sha in {"a": "1", "b": "2", "c": "3", "f": "an older concept's"}.items():
        (data / "inventory" / f"{place}.json").write_text(json.dumps({"concept_pick": {"sha256": sha}, "rows": []}))
    plan = {"output": "p" * 64}
    store = Accepts({"plan@a": {**plan, "by": "joey", "at": "2026-10-21T10:00"},
                     "plan@b": {**plan, "by": "runner", "at": "2026-10-21T10:00"},
                     "plan@c": {**plan, "by": "joey", "at": "2026-10-20T10:00"},  # before the pick: an old plan
                     "plan@d": {**plan, "by": "joey", "at": "2026-10-21T10:00"},
                     "plan@f": {**plan, "by": "joey", "at": "2026-10-21T10:00"}})  # read from an older inventory
    found = design.designs(store, data, ["a", "b", "c", "d", "e", "f"])
    states = {place: (row["concept"], row["inventory"], row["plan"]) for place, row in found["places"].items()}
    # the pick is the approval (owner, 2026-10-21): its inventory and plan made from it, the design stands approved
    assert states == {"a": ("picked", "made", "approved"), "b": ("picked", "made", "approved"),
                      "c": ("picked", "made", "approved"), "d": ("drawn", None, "remake"),
                      "e": ("missing", None, "remake"), "f": ("picked", "to read", "remake")}, states
    assert found["approved"] == ["a", "b", "c"] and found["places"]["b"]["output"] == "p" * 64
    assert found["places"]["d"]["output"] is None and found["places"]["e"]["hint"] is None


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(REPO / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
