"""Invariant: the basket shows what a run on main would buy and writes nothing into the real store: a place's free
after assembled over the store's accepted outputs on main's code, each node taken as now, made or stood in for the
paid batch; a paid node's inputs are what it reads; the plan's buys grouped into items by place and what they change
(joined with what they wait for, a declared item taking its own); what changes read from the two stages; the records
read back by item and place, names with a path refused; the export carrying them in order; the API serving them
signed in only; the Benchmarks item only while one can run.

Breaks that turn this red (each applied once and seen red, then reverted):
- assemble.taken_output: `if stage.paid or stage.models:` -> `if stage.models:` -> test_a_change_on_main_is_made_free...
- assemble.unmade: `if self.reads_paid(...)` -> `if False:` -> test_a_free_node_that_cannot_be_made_before_...
- assemble.taken_output: another place's check -> `if False:` -> test_another_places_node_is_shown_as_it_stands
- assemble.taken_output: the made-by-a-run check -> `if False:` -> test_main_moving_nothing_here_shows_the_place_...
- assemble.target: `return NEIGHBOURS` -> test_the_place_is_shown_with_its_neighbours_only_when_...
- assemble.Overlay.write_bytes: into `self.under` -> test_the_overlay_reads_through_and_writes_only_its_own_root
- assemble.inputs_of: the files of every read dropped -> test_a_paid_nodes_inputs_are_the_pictures_and_short_texts_...
- records.file_path: the name check dropped -> test_the_basket_is_kept_and_read_by_item_and_place
- records.checked: the name check dropped -> test_a_name_with_a_path_in_it_is_refused
- exporting.files: LAST before THEN -> test_the_export_carries_the_index_and_details_first_and_whole_copies_last
- make.make: place details made with plan_only -> test_a_plan_only_basket_groups_the_buys_and_assembles_no_place
- make.joined: `for read in waits_for(...)` -> `for read in []` -> test_buys_group_by_place_and_layer_and_join_...
- make.declared_buys: a pattern compared whole -> test_a_declared_item_takes_the_nodes_its_patterns_name_...
- make.version: the reasons left out -> test_an_items_version_moves_with_its_nodes_and_reasons
- details.object_kind: never "refinished" -> test_what_changes_is_read_from_the_two_stages_fingerprints
- details.steady: the link's own name -> test_a_file_input_is_named_by_the_blob_it_links_to
- api/routes.basket_file: without `signed_in` -> test_the_api_serves_the_basket_signed_in
- make.quoted: a JSON file returned whole -> test_a_json_input_is_quoted_only_for_the_words_a_person_wrote
- details.thing_of: a shown place's part kept whole -> test_a_persons_or_a_fixtures_meshes_count_as_one_thing_...
- benchmarks.item: `if not listed:` -> test_no_benchmark_that_can_run_is_no_item
"""
import dataclasses
import pathlib

import pytest
from fastapi.testclient import TestClient

from score import checks, contracts, graph
from score.dashboard.proposals import assemble, details, exporting, make, records
from score.dashboard.site.asgi import app
from score.dashboard.tests.fixture import api
from score.store import Store, tree_listing


def make_clean(inputs, out, seed, params):
    (out / "clean.txt").write_text(inputs["brief"].read_text().upper())


def make_paint(inputs, out, seed, params):
    (out / "paint.txt").write_text("painted " + (inputs["clean"] / "clean.txt").read_text())


def make_assembly(inputs, out, seed, params):
    (out / "stage.txt").write_text((inputs["clean"] / "clean.txt").read_text() + " | " +
                                   (inputs["paint"] / "paint.txt").read_text())


def make_shows(inputs, out, seed, params):
    (out / "shows.txt").write_text((inputs["assembly"] / "stage.txt").read_text() + " | beside the station")


def judge_written(output, inputs, evidence):
    return checks.Verdict("written", checks.PASS, "a text was written")


def text_faults(folder):
    return [] if any(folder.glob("*.txt")) else ["no text file"]


TEXT = contracts.Contract("toy-text", 1, text_faults)
WRITTEN = (checks.Check("written", judge_written),)
CLEAN = graph.Stage("clean", "place", make_clean, TEXT, WRITTEN, files={"brief": "{data}/{place}/brief.txt"})
PAINT = graph.Stage("paint", "place", make_paint, TEXT, WRITTEN, after={"clean": ("toy-text", 1)})
ASSEMBLY = graph.Stage("assembly", "place", make_assembly, TEXT, WRITTEN,
                       after={"clean": ("toy-text", 1), "paint": ("toy-text", 1)})


def a_world(folder, brief):
    (folder / "hangar").mkdir(parents=True)
    (folder / "hangar" / "brief.txt").write_text(brief)
    return graph.Environment("toy", 7, {"data": str(folder)})


def standing_store(tmp_path):
    """A real store where every node of the toy table stands accepted on the brief "old hull"."""
    store = Store.in_folder(tmp_path / "real")
    runner = graph.Runner((CLEAN, PAINT, ASSEMBLY), a_world(tmp_path / "main", "old hull"), store,
                          model_record=lambda kind: {})
    runner.run(["hangar"])
    assert store.accepted("assembly@hangar")
    return store


def toy_runner(tmp_path, brief, table, place="hangar"):
    """A ProposalRunner over the toy table on main's data `brief`, the scratch store over the real one."""
    world = a_world(tmp_path / f"main-now-{brief.replace(' ', '-')}", brief)
    store = assemble.overlay_store(tmp_path / "real", tmp_path / "scratch")
    return assemble.ProposalRunner(table, world, store, Store.in_folder(tmp_path / "real"), place)


def basket_run(tmp_path, brief):
    """The toy assembly's free after on `brief`, the paint row paid: (its result, the runner)."""
    runner = toy_runner(tmp_path, brief, (CLEAN, dataclasses.replace(PAINT, paid=True, euros=1.0), ASSEMBLY))
    return assemble.assemble(runner, "hangar", tmp_path / "stage"), runner


def test_a_change_on_main_is_made_free_and_a_paid_row_waits_for_the_batch(tmp_path):
    standing_store(tmp_path)
    before = tree_listing(tmp_path / "real")
    result, _ = basket_run(tmp_path, "new hull")
    how = {item["node"]: item["how"] for item in result["taken"]}
    assert how == {"clean@hangar": records.MADE, "paint@hangar": records.PAID, "assembly@hangar": records.MADE}
    assert (tmp_path / "stage" / "stage.txt").read_text() == "NEW HULL | painted OLD HULL"
    assert tree_listing(tmp_path / "real") == before  # the real store is only read
    assert all(item["answer"] == checks.PASS for item in result["taken"] if item["how"] == records.MADE)


def make_failing_assembly(inputs, out, seed, params):
    raise KeyError("a part the old paint does not name")


def test_a_free_node_that_cannot_be_made_before_the_paid_batch_stands_in_for_it(tmp_path):
    standing_store(tmp_path)
    runner = toy_runner(tmp_path, "new hull", (CLEAN, dataclasses.replace(PAINT, paid=True, euros=1.0),
                                               dataclasses.replace(ASSEMBLY, make=make_failing_assembly)))
    result = assemble.assemble(runner, "hangar", tmp_path / "stage")
    store = runner.store
    taken = {item["node"]: item for item in result["taken"]}
    assert taken["assembly@hangar"]["how"] == records.PAID
    assert "KeyError" in taken["assembly@hangar"]["why"]
    assert result["assembly"] == store.accepted("assembly@hangar")


def test_another_places_node_is_shown_as_it_stands(tmp_path):
    standing_store(tmp_path)
    runner = toy_runner(tmp_path, "new hull", (CLEAN, PAINT, ASSEMBLY), place="station")
    assert runner.usable("clean", "hangar", None) == runner.store.accepted("clean@hangar")
    assert runner.taken["clean@hangar"]["how"] == records.AS_NOW


def test_main_moving_nothing_here_shows_the_place_as_it_stands(tmp_path):
    store = standing_store(tmp_path)
    result, _ = basket_run(tmp_path, "old hull")
    assert {item["how"] for item in result["taken"]} == {records.AS_NOW}
    assert result["assembly"] == store.accepted("assembly@hangar")
    assert not (tmp_path / "scratch" / "objects" / "records").exists()


def test_the_place_is_shown_with_its_neighbours_only_when_a_run_would_make_them_again(tmp_path):
    shows = graph.Stage("neighbours", "place", make_shows, TEXT, WRITTEN, after={"assembly": ("toy-text", 1)})
    store = Store.in_folder(tmp_path / "real")
    graph.Runner((CLEAN, PAINT, ASSEMBLY, shows), a_world(tmp_path / "main", "old hull"), store,
                 model_record=lambda kind: {}).run(["hangar"])
    assert assemble.target(toy_runner(tmp_path, "old hull", (CLEAN, PAINT, ASSEMBLY, shows)), "hangar") == \
        assemble.ASSEMBLY
    assert assemble.target(toy_runner(tmp_path, "new hull", (CLEAN, PAINT, ASSEMBLY, shows)), "hangar") == \
        assemble.NEIGHBOURS


def test_the_overlay_reads_through_and_writes_only_its_own_root(tmp_path):
    real = tmp_path / "real" / "objects"
    (real / "blobs").mkdir(parents=True)
    (real / "blobs" / "abc").write_text("real")
    overlay = assemble.Overlay(tmp_path / "scratch", real)
    assert overlay.read_bytes("blobs/abc") == b"real"
    overlay.write_bytes("records/x.json", b"{}")
    assert (tmp_path / "scratch" / "records" / "x.json").is_file() and not (real / "records").exists()
    assert overlay.keys("") == ["blobs/abc", "records/x.json"]


def test_a_paid_nodes_inputs_are_the_pictures_and_short_texts_it_reads(tmp_path):
    standing_store(tmp_path)
    _, runner = basket_run(tmp_path, "new hull")
    found = assemble.inputs_of(runner, "paint@hangar")
    assert found["reads"] == [{"node": "clean@hangar", "how": records.MADE}]
    assert [(item["from"], item["name"], item["kind"]) for item in found["files"]] == [
        ("clean@hangar", "clean.txt", "text")]
    assert assemble.inputs_of(runner, "clean@hangar")["files"][0]["name"] == "brief: brief.txt"


def a_basket(root, place="hangar"):
    """A made basket: one item at `place` with its details, its after's 3D copy and an input picture."""
    partial = root / f".{place}-partial"
    (partial / "web3d").mkdir(parents=True)
    (partial / "web3d" / f"{place}.glb").write_bytes(b"whole")
    (partial / "web3d" / f"{place}-light.glb").write_bytes(b"light")
    (partial / "web3d" / f"{place}.json").write_text("{}")
    (partial / "inputs").mkdir()
    (partial / "inputs" / "1.jpg").write_bytes(b"jpeg")
    records.put_place(root, partial, place, {"place": place, "copy": {"triangles": 3}, "changes": None,
                                              "inputs": {}})
    item = make.finished(f"{place}-pieces", make.entry_of(
        [{"node": f"surfaces-bake@{place}", "why": "code changed", "again": True, "price": PRICE}], {}))
    records.put_index(root, {"made_at": "2026-10-19T08:00:00Z", "items": [item]})
    return item


PRICE = {"likely_euros": 2.0, "high_euros": 3.0, "likely_minutes": 10.0, "high_minutes": 20.0, "runs": 4,
         "guess_euros": None, "cards": 1}


def test_the_basket_is_kept_and_read_by_item_and_place(tmp_path):
    item = a_basket(tmp_path)
    assert records.item(tmp_path, "hangar-pieces")["version"] == item["version"]
    assert records.details(tmp_path, "hangar")["copy"] == {"triangles": 3}
    assert records.file_path(tmp_path, "hangar", "inputs/1.jpg").read_bytes() == b"jpeg"
    assert records.file_path(tmp_path, "hangar", "details.json") is None
    assert records.file_path(tmp_path, "hangar", "inputs/../../index.json") is None


def test_a_name_with_a_path_in_it_is_refused(tmp_path):
    for bad in ("..", "../x", "a/b", ".hidden"):
        try:
            records.folder(tmp_path, bad)
        except records.BadName:
            continue
        raise AssertionError(f"{bad!r} was taken as a name")


def test_the_export_carries_the_index_and_details_first_and_whole_copies_last(tmp_path):
    a_basket(tmp_path)
    records.put_declared(tmp_path, "ship-room-concepts", {"title": "Ship room concepts"})
    order = [target for _, target in exporting.files(tmp_path)]
    assert order[:3] == ["proposals/index.json", "proposals/declared.json", "proposals/hangar/details.json"]
    assert order[-1] == "proposals/hangar/web3d/hangar.glb"
    assert len(order) == len(set(order)) == 7
    assert exporting.files(tmp_path / "none") == []


LAYERS = {"pixal": "pieces", "surfaces-bake": "pieces", "light-passes": "light"}


def buy(node, why="code changed", again=True):
    return {"node": node, "why": why, "again": again, "price": PRICE}


def test_a_plan_only_basket_groups_the_buys_and_assembles_no_place(tmp_path, monkeypatch):
    """The plan's buys and its missing inputs make the items; no place is assembled (no free row runs here)."""
    import types

    class Planned:
        def plan(self, group):
            return types.SimpleNamespace(buys=[buy("pixal@hangar"), buy("light-passes@garage")],
                                         missing=["cast@cockpit: scene (data/scene/cockpit.json)"],
                                         refusal="refused: these inputs are missing")

    def assembling(*given):
        raise AssertionError("a plan-only basket assembles no place")
    monkeypatch.setattr(make, "place_details", assembling)
    index = make.make(tmp_path, tmp_path / "store", chosen=Planned(), layer_of=LAYERS, plan_only=True)
    assert index["plan_only"] is True and index["missing"] == ["cast@cockpit: scene (data/scene/cockpit.json)"]
    assert sorted(node for item in index["items"] for node in item["nodes"]) == ["light-passes@garage",
                                                                                "pixal@hangar"]
    assert records.items(tmp_path / "proposals") == index["items"]


def test_buys_group_by_place_and_layer_and_join_what_they_wait_for():
    found = make.grouped([buy("pixal@hangar"), buy("surfaces-bake@hangar", "reads pixal@hangar"),
                          buy("light-passes@hangar"), buy("light-passes@garage"),
                          buy("people-body-bram-work"), buy("people-body-nev-work"), buy("people-lists")], LAYERS,
                         ["surfaces-bake@hangar: bake job (/x/job.json)"])
    named = {item["id"]: sorted(item["nodes"]) for item in found}
    assert named == {"hangar-pieces": ["pixal@hangar", "surfaces-bake@hangar"], "hangar-light": ["light-passes@hangar"],
                     "garage-light": ["light-passes@garage"],
                     "environment-people-body": ["people-body-bram-work", "people-body-nev-work"],
                     "environment-people-lists": ["people-lists"]}
    pieces = found[0]
    assert pieces["place"] == "hangar" and pieces["places"] == ["hangar"] and pieces["missing"]
    assert pieces["totals"]["likely_euros"] == 4.0 and pieces["totals"]["high_euros"] == 6.0
    assert found[3]["place"] is None and found[3]["places"] == []
    # a buy that reads another layer's buy at its place waits for it: one item, never bought apart
    (waiting,) = make.grouped([buy("pixal@hangar"), buy("light-passes@hangar", "reads pixal@hangar")], LAYERS)
    assert sorted(waiting["nodes"]) == ["light-passes@hangar", "pixal@hangar"]


def test_a_declared_item_takes_the_nodes_its_patterns_name_at_any_place():
    declared = {"ship-room-concepts": {"title": "Ship room concepts", "nodes": ["concept-views", "pixal@ship-*"]},
                "waiting-trial": {"title": "The prop trial", "nodes": ["prop-trial*"]}}
    found = make.grouped([buy("concept-views"), buy("pixal@ship-cockpit"), buy("pixal@ship-galley"),
                          buy("pixal@hangar")], LAYERS, declared=declared)
    ship, waiting, rest = found
    assert ship["id"] == "ship-room-concepts" and ship["title"] == "Ship room concepts" and ship["declared"]
    assert sorted(ship["nodes"]) == ["concept-views", "pixal@ship-cockpit", "pixal@ship-galley"]
    assert ship["places"] == ["ship-cockpit", "ship-galley"] and ship["place"] is None
    assert waiting["nodes"] == {} and waiting["totals"]["nodes"] == 0
    assert rest["id"] == "hangar-pieces"


def test_an_items_version_moves_with_its_nodes_and_reasons():
    first = make.grouped([buy("pixal@hangar")], LAYERS)[0]["version"]
    assert make.grouped([buy("pixal@hangar")], LAYERS)[0]["version"] == first
    assert make.grouped([buy("pixal@hangar", "never ran")], LAYERS)[0]["version"] != first


def an_object(low, high, surface="steel", shape=8, layer="base"):
    return {"layer": layer, "low": low, "high": high, "surface": [["geo", surface, []]], "shape": shape}


def test_what_changes_is_read_from_the_two_stages_fingerprints():
    before = {"objects": {"Objects/crate_1": an_object([0, 0, 0], [1, 1, 1]),
                          "Objects/door": an_object([2, 0, 0], [3, 2, 0.1]),
                          "Objects/lamp_post": an_object([5, 0, 0], [5.2, 3, 0.2]),
                          "Objects/bench": an_object([7, 0, 0], [8, 0.5, 0.5])},
              "lamps": {"light_1": {"name": "light_1", "at": [0, 3, 0], "intensity": 1.0, "colour": [1, 1, 1]}},
              "sounds": {"/hangar/Sound/hum": {"at": [0, 0, 0], "file": "abc"}},
              "cameras": {"door": {"eye": [0, 1, 0]}}}
    after = {"objects": {"Objects/crate_1": an_object([0, 0, 0], [1, 1, 1], surface="painted"),
                         "Objects/door": an_object([2.5, 0, 0], [3.5, 2, 0.1]),
                         "Objects/bench": an_object([7, 0, 0], [8, 0.5, 0.5], shape=12),
                         "Objects/crate_2": an_object([4, 0, 0], [5, 1, 1], layer="settle")},
             "lamps": {"light_1": {"name": "light_1", "at": [0, 3, 0], "intensity": 2.0, "colour": [1, 1, 1]}},
             "sounds": {"/hangar/Sound/hum": {"at": [0, 0, 0], "file": "abc"}},
             "cameras": {"door": {"eye": [0, 1.6, 0]}}}
    found = details.difference(before, after)
    names = {kind: [entry["name"] for entry in given["listed"]] for kind, given in found["objects"].items()}
    assert names == {"added": ["Objects/crate_2"], "removed": ["Objects/lamp_post"], "moved": ["Objects/door"],
                     "reshaped": ["Objects/bench"], "refinished": ["Objects/crate_1"]}
    assert found["objects"]["added"]["listed"][0]["layer"] == "settle"
    assert found["objects"]["removed"]["listed"][0]["low"] == [5, 0, 0]  # the before's box for what is taken out
    assert found["lamps"]["changed"]["count"] == 1 and found["lamps"]["changed"]["listed"][0]["low"][1] == 2.85
    assert found["sounds"] == {"added": [], "removed": [], "changed": []}
    assert found["cameras"]["changed"] == ["door"]


def test_a_file_input_is_named_by_the_blob_it_links_to(tmp_path):
    blob = tmp_path / "blobs" / "f00d"
    blob.parent.mkdir()
    blob.write_bytes(b"png")
    (tmp_path / "linked.png").symlink_to(blob)
    assert details.steady(["texture", str(tmp_path / "linked.png")]) == ["texture", "f00d"]
    assert details.steady(["value", [0.5, 0.5, 0.5]]) == ["value", [0.5, 0.5, 0.5]]


@pytest.mark.django_db(transaction=True)
def test_the_api_serves_the_basket_signed_in(world, settings):
    a_basket(pathlib.Path(settings.SCORE_HOME) / "proposals")
    client = api()
    assert client.get("/api/basket").json()["items"][0]["id"] == "hangar-pieces"
    assert client.get("/api/basket/hangar").json()["copy"] == {"triangles": 3}
    assert client.get("/api/basket/nowhere").status_code == 404
    assert client.get("/basket-file/hangar/web3d/hangar-light.glb").content == b"light"
    assert client.get("/basket-file/hangar/details.json").status_code == 404
    assert client.get("/basket-file/hangar/inputs/..%2F..%2Findex.json").status_code == 404
    unsigned = TestClient(app, base_url="http://127.0.0.1:8780", client=("127.0.0.1", 50000))
    assert unsigned.get("/api/basket").status_code == 401
    assert unsigned.get("/basket-file/hangar/inputs/1.jpg").status_code == 401


def test_a_json_input_is_quoted_only_for_the_words_a_person_wrote(tmp_path):
    (tmp_path / "views.json").write_text('{"views": [{"id": "ship46_cockpit", "wording": "The cockpit, 7.8 m wide."}]}')
    (tmp_path / "boxes.json").write_text('{"boxes": [[0, 0, 1]]}')
    (tmp_path / "brief.txt").write_text("A crate of tools.")
    assert make.quoted(tmp_path / "views.json") == "The cockpit, 7.8 m wide."
    assert make.quoted(tmp_path / "boxes.json") is None and make.quoted(tmp_path / "brief.txt") == "A crate of tools."


def test_a_persons_or_a_fixtures_meshes_count_as_one_thing_with_one_box():
    before = {"objects": {}, "lamps": {}, "sounds": {}, "cameras": {}}
    after = {**before, "objects": {"Characters/bram/Turned/Body/work/boot_l_0": an_object([0, 0, 0], [0.3, 0.2, 0.3]),
                                   "Characters/bram/Turned/Body/work/cloth_10": an_object([0, 0.2, 0], [0.5, 1.8, 0.4]),
                                   "Places/camp/Outside/ball": an_object([9, 0, 9], [10, 1, 10]),
                                   "Objects/crate_1": an_object([4, 0, 0], [5, 1, 1])}}
    added = details.difference(before, after)["objects"]["added"]
    assert added["count"] == 3
    assert [(entry["name"], entry["parts"]) for entry in added["listed"]] == [
        ("Characters/bram", 2), ("Objects/crate_1", 1), ("Places/camp/Outside", 1)]
    assert added["listed"][0]["low"] == [0, 0, 0] and added["listed"][0]["high"] == [0.5, 1.8, 0.4]


BENCHMARK_GAP = {"id": "batch-direct", "what": "batch against direct", "gap": "no paid path asks a finish list direct"}


@pytest.mark.django_db
def test_no_benchmark_that_can_run_is_no_item(settings):
    """prepare listed only a benchmark it cannot run (a gap): the basket gets no Benchmarks item."""
    import json
    from score.dashboard.proposals import benchmarks
    path = settings.SCORE_PROPS_HOME / benchmarks.RECORD
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"benchmarks": {"listed": [BENCHMARK_GAP]}}))
    assert benchmarks.put(settings.SCORE_HOME / "proposals", settings.SCORE_PROPS_HOME) == "benchmarks: none listed"
    assert records.item(settings.SCORE_HOME / "proposals", "benchmarks") is None
