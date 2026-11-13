"""Invariant: the basket shows what a run on main would buy and writes nothing into the real store: a place's free
after assembled over the store's accepted outputs on main's code, each node taken as now, made or stood in for the
paid batch; a paid node's inputs are what it reads; the plan's buys grouped into items by place and what they change
(joined with what they wait for, a declared item taking its own); what changes read from the two stages; the records
read back by item and place, names with a path refused; the export carrying them in order; the API serving them
signed in only; the Benchmarks item only while one can run.

Breaks that turn this red (each applied once and seen red, then reverted); all in the one test, by its part:
- assemble.taken_output: `if stage.paid or stage.models:` -> `if stage.models:` -> the free after's "new hull" row
- assemble.unmade: `if self.reads_paid(...)` -> `if False:` -> the free after's "the after fails" row
- assemble.taken_output: another place's check -> `if False:` -> the free after's "another place" row
- assemble.taken_output: the made-by-a-run check -> `if False:` -> the free after's "main moves nothing" row
- assemble.target: `return NEIGHBOURS` -> the free after's target column ("main moves nothing")
- assemble.Overlay.write_bytes: into `self.under` -> the free after: the real store is only read
- assemble.inputs_of: the files of every read dropped -> the free after: a paid node's inputs
- records.file_path: the name check dropped -> the kept basket's file rows
- records.checked: the name check dropped -> the kept basket's refused names
- exporting.files: LAST before THEN -> the kept basket's export order
- make.make: place details made with plan_only -> the plan-only make (place_details refuses)
- make.joined: `for read in waits_for(...)` -> `for read in []` -> the plan's items ("dock-pieces" joined)
- make.declared_buys: a pattern compared whole -> the plan's items ("ship-room-concepts")
- make.version: the reasons left out -> the remade plan's versions
- details.object_kind: never "refinished" -> what changes between the two stages
- details.steady: the link's own name -> the steady surface inputs
- api/routes.basket_file: without `signed_in` -> the API rows
- make.quoted: a JSON file returned whole -> the declared item's quoted files
- details.thing_of: a shown place's part kept whole -> what changes: a person's and a fixture's meshes
- benchmarks.item: `if not listed:` -> the plan's items (no "benchmarks") and benchmarks.put's words
"""
import dataclasses
import json
import pathlib
import types

import pytest
from fastapi.testclient import TestClient

from score import checks, contracts, graph
from score.dashboard.proposals import assemble, benchmarks, details, exporting, make, records
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


SHOWS = graph.Stage("neighbours", "place", make_shows, TEXT, WRITTEN, after={"assembly": ("toy-text", 1)})


def standing_store(root):
    """A real store where every node of the toy table, the neighbours too, stands accepted on the brief "old hull"."""
    store = Store.in_folder(root / "real")
    graph.Runner((CLEAN, PAINT, ASSEMBLY, SHOWS), a_world(root / "main", "old hull"), store,
                 model_record=lambda kind: {}).run(["hangar"])
    assert store.accepted("assembly@hangar")
    return store


def make_failing_assembly(inputs, out, seed, params):
    raise KeyError("a part the old paint does not name")


def toy_runner(root, row, table):
    """A ProposalRunner over `table` on main's data `row["brief"]` at the row's place, its scratch store over the real
    one."""
    world = a_world(root / f"main-{row['id']}-{len(table)}", row["brief"])
    store = assemble.overlay_store(root / "real", root / f"scratch-{row['id']}-{len(table)}")
    return assemble.ProposalRunner(table, world, store, Store.in_folder(root / "real"), row["place"])


def files_under(folder):
    return {str(path.relative_to(folder)) for path in folder.rglob("*") if path.is_file()}


M, P, N = records.MADE, records.PAID, records.AS_NOW
# A run on main over the standing store, the paint row paid: how each node is taken, why, the after shown (its text;
# None: the accepted assembly stands) and the stage the item shows over the table with neighbours, nothing paid
# (None: not asked of another place's runner).
FREE_AFTER = [
    {"id": "new hull", "brief": "new hull", "place": "hangar", "assembly": make_assembly,
     "how": {"clean@hangar": M, "paint@hangar": P, "assembly@hangar": M}, "why": {},
     "after": "NEW HULL | painted OLD HULL", "target": assemble.NEIGHBOURS},
    {"id": "the after fails", "brief": "new hull", "place": "hangar", "assembly": make_failing_assembly,
     "how": {"clean@hangar": M, "paint@hangar": P, "assembly@hangar": P}, "why": {"assembly@hangar": "KeyError"},
     "after": None, "target": assemble.NEIGHBOURS},
    {"id": "another place", "brief": "new hull", "place": "station", "assembly": make_assembly,
     "how": {"clean@hangar": N, "assembly@hangar": N}, "why": {}, "after": None, "target": None},
    {"id": "main moves nothing", "brief": "old hull", "place": "hangar", "assembly": make_assembly,
     "how": {"clean@hangar": N, "paint@hangar": N, "assembly@hangar": N}, "why": {}, "after": None,
     "target": assemble.ASSEMBLY},
]


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
LAYERS = {"pixal": "pieces", "surfaces-bake": "pieces", "light-passes": "light"}


def buy(node, why="code changed", again=True):
    return {"node": node, "why": why, "again": again, "price": PRICE}


def planner(buys, missing):
    """The runner's plan stand-in: these buys, these missing inputs, its refusal."""
    class Planned:
        def plan(self, group):
            return types.SimpleNamespace(buys=buys, missing=missing, refusal="refused: these inputs are missing")
    return Planned()


def an_object(low, high, surface="steel", shape=8, layer="base"):
    return {"layer": layer, "low": low, "high": high, "surface": [["geo", surface, []]], "shape": shape}


BENCHMARK_GAP = {"id": "batch-direct", "what": "batch against direct", "gap": "no paid path asks a finish list direct"}


@pytest.mark.django_db(transaction=True)
def test_a_basket_shows_what_a_run_on_main_would_buy(tmp_path, world, settings, monkeypatch):
    # The free after: each node taken as now, made or stood in for the paid batch; the real store only read.
    toy = tmp_path / "toy"
    store = standing_store(toy)
    real_objects = toy / "real" / "objects"
    before = tree_listing(toy / "real")
    for row in FREE_AFTER:
        table = (CLEAN, dataclasses.replace(PAINT, paid=True, euros=1.0),
                 dataclasses.replace(ASSEMBLY, make=row["assembly"]))
        runner = toy_runner(toy, row, table)
        result = assemble.assemble(runner, "hangar", toy / f"stage-{row['id']}")
        # a paid node's inputs: the nodes it reads, taken as below, and their pictures and short texts
        found = assemble.inputs_of(runner, "paint@hangar")
        assert found["reads"] == [{"node": "clean@hangar", "how": row["how"]["clean@hangar"]}], row["id"]
        assert [(item["from"], item["name"], item["kind"]) for item in found["files"]] == [
            ("clean@hangar", "clean.txt", "text")], row["id"]
        assert assemble.inputs_of(runner, "clean@hangar")["files"][0]["name"] == "brief: brief.txt", row["id"]
        taken = runner.taken  # every node the after and those inputs took
        assert {node: item["how"] for node, item in taken.items()} == row["how"], row["id"]
        for node, words in row["why"].items():
            assert words in taken[node]["why"], row["id"]
        assert all(item["answer"] == checks.PASS for item in taken.values() if item["how"] == M), row["id"]
        if row["after"] is None:
            assert result["assembly"] == store.accepted("assembly@hangar"), row["id"]
        else:
            assert (toy / f"stage-{row['id']}" / "stage.txt").read_text() == row["after"], row["id"]
        scratch_objects = runner.store.objects.root
        assert (scratch_objects / "records").exists() == (M in row["how"].values()), row["id"]
        runner.store.objects.write_bytes("records/noted.json", b"{}")  # every write lands in the scratch root
        assert (scratch_objects / "records" / "noted.json").is_file(), row["id"]
        assert tree_listing(toy / "real") == before, row["id"]  # the real store is only read
        assert runner.store.objects.keys("") == sorted(files_under(real_objects) | files_under(scratch_objects))
        blob = next(iter(sorted(files_under(real_objects / "blobs"))))
        assert runner.store.objects.read_bytes(f"blobs/{blob}") == (real_objects / "blobs" / blob).read_bytes()
        if row["target"] is not None:  # the place with its neighbours only when a run would make them again
            shown = toy_runner(toy, row, (CLEAN, PAINT, ASSEMBLY, SHOWS))
            assert assemble.target(shown, "hangar") == row["target"], row["id"]

    # The kept basket: read back by item and place, names with a path refused, exported in order, served signed in.
    root = pathlib.Path(settings.SCORE_HOME) / "proposals"
    item = a_basket(root)
    assert records.item(root, "hangar-pieces")["version"] == item["version"]
    assert records.details(root, "hangar")["copy"] == {"triangles": 3}
    for name, held in (("inputs/1.jpg", b"jpeg"), ("details.json", None), ("inputs/../../index.json", None)):
        path = records.file_path(root, "hangar", name)
        assert (path and path.read_bytes()) == held, name
    for bad in ("..", "../x", "a/b", ".hidden"):
        with pytest.raises(records.BadName):
            records.folder(root, bad)
    records.put_declared(root, "ship-room-concepts", {"title": "Ship room concepts"})
    order = [target for _, target in exporting.files(root)]
    assert order[:3] == ["proposals/index.json", "proposals/declared.json", "proposals/hangar/details.json"]
    assert order[-1] == "proposals/hangar/web3d/hangar.glb"
    assert len(order) == len(set(order)) == 7
    assert exporting.files(tmp_path / "none") == []
    client = api()
    unsigned = TestClient(app, base_url="http://127.0.0.1:8780", client=("127.0.0.1", 50000))
    assert client.get("/api/basket").json()["items"][0]["id"] == "hangar-pieces"
    assert client.get("/api/basket/hangar").json()["copy"] == {"triangles": 3}
    assert client.get("/basket-file/hangar/web3d/hangar-light.glb").content == b"light"
    for url, signed, status in (("/api/basket/nowhere", 404, 404), ("/basket-file/hangar/details.json", 404, 404),
                                ("/basket-file/hangar/inputs/..%2F..%2Findex.json", 404, 404),
                                ("/api/basket", 200, 401), ("/basket-file/hangar/inputs/1.jpg", 200, 401)):
        assert client.get(url).status_code == signed, url
        if status == 401:
            assert unsigned.get(url).status_code == status, url

    # The plan's buys made into items (plan only: no place assembled): declared items first, the rest by place and
    # what they change, joined with what they wait for; the benchmarks item only while one can run.
    home = tmp_path / "plan"
    (home / "data").mkdir(parents=True)
    (home / "data" / "views.json").write_text(
        '{"views": [{"id": "ship46_cockpit", "wording": "The cockpit, 7.8 m wide."}]}')
    (home / "data" / "boxes.json").write_text('{"boxes": [[0, 0, 1]]}')
    (home / "data" / "brief.txt").write_text("A crate of tools.")
    records.put_declared(home / "proposals", "ship-room-concepts", {
        "title": "Ship room concepts", "nodes": ["concept-views", "pixal@ship-*"],
        "files": [str(home / "data" / name) for name in ("views.json", "boxes.json", "brief.txt")]})
    records.put_declared(home / "proposals", "waiting-trial", {"title": "The prop trial", "nodes": ["prop-trial*"]})
    (home / benchmarks.RECORD).parent.mkdir(parents=True)
    (home / benchmarks.RECORD).write_text(json.dumps({"benchmarks": {"listed": [BENCHMARK_GAP]}}))
    buys = [buy("concept-views"), buy("pixal@ship-cockpit"), buy("pixal@ship-galley"), buy("pixal@hangar"),
            buy("surfaces-bake@hangar", "reads pixal@hangar"), buy("light-passes@hangar"), buy("light-passes@garage"),
            buy("pixal@dock"), buy("light-passes@dock", "reads pixal@dock"),
            buy("people-body-bram-work"), buy("people-body-nev-work"), buy("people-lists")]
    missing = ["surfaces-bake@hangar: bake job (/x/job.json)", "cast@cockpit: scene (data/scene/cockpit.json)"]

    def assembling(*given):
        raise AssertionError("a plan-only basket assembles no place")
    monkeypatch.setattr(make, "place_details", assembling)
    index = make.make(home, home / "store", chosen=planner(buys, missing), layer_of=LAYERS, plan_only=True)
    assert index["plan_only"] is True and index["missing"] == missing
    found = {item["id"]: item for item in index["items"]}
    assert {ident: sorted(item["nodes"]) for ident, item in found.items()} == {
        "ship-room-concepts": ["concept-views", "pixal@ship-cockpit", "pixal@ship-galley"], "waiting-trial": [],
        "hangar-pieces": ["pixal@hangar", "surfaces-bake@hangar"], "hangar-light": ["light-passes@hangar"],
        "garage-light": ["light-passes@garage"], "dock-pieces": ["light-passes@dock", "pixal@dock"],
        "environment-people-body": ["people-body-bram-work", "people-body-nev-work"],
        "environment-people-lists": ["people-lists"]}
    assert list(found)[:2] == ["ship-room-concepts", "waiting-trial"]
    assert records.items(home / "proposals") == index["items"]
    ship, waiting, pieces = found["ship-room-concepts"], found["waiting-trial"], found["hangar-pieces"]
    assert ship["title"] == "Ship room concepts" and ship["declared"]
    assert ship["places"] == ["ship-cockpit", "ship-galley"] and ship["place"] is None
    assert waiting["nodes"] == {} and waiting["totals"]["nodes"] == 0
    assert pieces["place"] == "hangar" and pieces["places"] == ["hangar"] and pieces["missing"] == missing[:1]
    assert pieces["totals"]["likely_euros"] == 4.0 and pieces["totals"]["high_euros"] == 6.0
    assert found["environment-people-body"]["place"] is None and found["environment-people-body"]["places"] == []
    assert not any(item["missing"] for ident, item in found.items() if ident != "hangar-pieces")
    # a declared item's own files: a JSON file quoted only for the words a person wrote, a plain text whole
    shown = records.details(home / "proposals", records.declared_folder("ship-room-concepts"))
    assert [(each["name"], each["text"]) for each in shown["inputs"]["declared"]["files"]] == [
        ("views.json", "The cockpit, 7.8 m wide."), ("brief.txt", "A crate of tools.")]
    assert benchmarks.put(home / "proposals", home) == "benchmarks: none listed"
    assert records.item(home / "proposals", "benchmarks") is None
    # an item's version moves with its nodes and reasons only
    again = make.make(home, home / "store", chosen=planner([*buys[:3], buy("pixal@hangar", "never ran"), *buys[4:]],
                                                            missing), layer_of=LAYERS, plan_only=True)
    moved = {item["id"]: item["version"] != found[item["id"]]["version"] for item in again["items"]}
    assert moved == {ident: ident == "hangar-pieces" for ident in found}

    # What changes, read from the two stages' fingerprints; a person's or a fixture's meshes count as one thing.
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
                         "Objects/crate_2": an_object([4, 0, 0], [5, 1, 1], layer="settle"),
                         "Characters/bram/Turned/Body/work/boot_l_0": an_object([0, 0, 0], [0.3, 0.2, 0.3]),
                         "Characters/bram/Turned/Body/work/cloth_10": an_object([0, 0.2, 0], [0.5, 1.8, 0.4]),
                         "Places/camp/Outside/ball": an_object([9, 0, 9], [10, 1, 10])},
             "lamps": {"light_1": {"name": "light_1", "at": [0, 3, 0], "intensity": 2.0, "colour": [1, 1, 1]}},
             "sounds": {"/hangar/Sound/hum": {"at": [0, 0, 0], "file": "abc"}},
             "cameras": {"door": {"eye": [0, 1.6, 0]}}}
    changes = details.difference(before, after)
    names = {kind: [entry["name"] for entry in given["listed"]] for kind, given in changes["objects"].items()}
    assert names == {"added": ["Characters/bram", "Objects/crate_2", "Places/camp/Outside"],
                     "removed": ["Objects/lamp_post"], "moved": ["Objects/door"], "reshaped": ["Objects/bench"],
                     "refinished": ["Objects/crate_1"]}
    added = changes["objects"]["added"]
    assert added["count"] == 3 and [entry["parts"] for entry in added["listed"]] == [2, 1, 1]
    assert added["listed"][0]["low"] == [0, 0, 0] and added["listed"][0]["high"] == [0.5, 1.8, 0.4]
    assert added["listed"][1]["layer"] == "settle"
    assert changes["objects"]["removed"]["listed"][0]["low"] == [5, 0, 0]  # the before's box for what is taken out
    assert changes["lamps"]["changed"]["count"] == 1 and changes["lamps"]["changed"]["listed"][0]["low"][1] == 2.85
    assert changes["sounds"] == {"added": [], "removed": [], "changed": []}
    assert changes["cameras"]["changed"] == ["door"]
    # a surface's file input is named by the blob it links to, so the two sides compare
    blob = toy / "blobs" / "f00d"
    blob.parent.mkdir()
    blob.write_bytes(b"png")
    (toy / "linked.png").symlink_to(blob)
    for value, steady in ((["texture", str(toy / "linked.png")], ["texture", "f00d"]),
                          (["value", [0.5, 0.5, 0.5]], ["value", [0.5, 0.5, 0.5]])):
        assert details.steady(value) == steady, value
