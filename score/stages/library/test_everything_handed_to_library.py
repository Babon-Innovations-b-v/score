"""The library rows' invariant: everything an environment holds is handed to the creator's library by its own command,
and every mismatch between the handover, the library and the store is named, never passed.

At the runner's seams, with a fake library command over a toy table (one environment row, one place row, one showcase
render that never passes) and a store of its own; the machine's score_lib checkout and the cloud are fakes:

    no library configured     library@garage says so, `configured` fails, the place is not complete
    library-free environment  the same environment named in library-free.json passes and is complete
    a configured library      the fake command runs once with the template's words; a second run reuses the record
    the route                 a route stage's code moves it, another stage's does not
    coverage                  an output the handover misses fails `handed` by name; a written exception covers it; an
                              output no entry holds is held through what it was made into
    copies                    a missing 3D copy is unknown, never a pass
    traced                    unknown with no library, pass on the good fixture, fail naming the photo on the bad one
    the report's shape        the shared example is on the contract, field for field (both repositories read it)
    a slow library            a run past its timeout is a transient error (tried again by the runner)
    the defaults              the environment wins over the defaults; the cloud's store only when no blob folder is set
    the real table            the two rows read every row of their grain but straight-masks, the showcase renders
                              optional, both free, and no row reads them (owner, 2026-10-22: no paid preview)
    pictures                  a lost picture never stops the others; a 404 is not asked again until the bytes change
    the invariant             each mismatch (not handed, not in library, moved on, shown nowhere, not pushed) gives
                              exactly its problem on small fixed sets, equal sets none; the sweep reads a library
                              folder and writes the cockpit's findings with the entry's picture
    demos                     a demo off the shape says what; one with no example or that fails is missing with why

Breaks that turn these red (each applied once, seen red, reverted, 2026-10-26):
- checks.uncovered: an output not in the handover left out of the findings (coverage).
- backend.settings: the defaults over the environment (the defaults).
- library.route: hash every stage, not only the route's (the route).
- invariant: `if now == row["output"]` -> `if True` (moved on never found).
- invariant.newest: keep the oldest version, not the newest (history is not counted).
- sweep.library_free: take a decision with no date (library free).
- pictures.held_or_why: ask a file marked lost again (pictures).
- demos.shape_problem: accept any shape kind (demos).
- library.rows: the place row reads straight-masks too (the real table).
"""
import json
import os
import pathlib
import sys

import pytest

from score import checks, contracts, graph
from score.stages import library
from score.stages.library import backend, checks as library_checks, demos, handover, invariant, pictures, sweep
from score.store import Store

REPO = pathlib.Path(__file__).resolve().parents[3]
HERE = pathlib.Path(__file__).resolve().parent
FAKE_STORE = {"endpoint": "https://store.example", "region": "region-1", "bucket": "a-bucket", "access_key": "AK",
              "secret_key": "SK"}
PLACE, WORLD = "garage", "toyworld"
TOY = contracts.Contract("toy-text", 1, lambda folder: [] if any(folder.glob("*.txt")) else ["no text file"])

# The fake library: writes handover.json from reads.json as its mode file says, and counts its calls.
FAKE = '''import json, pathlib, sys
words = sys.argv[1:]
here = pathlib.Path(__file__).parent
with (here / "calls.txt").open("a") as calls:
    calls.write(json.dumps(words) + "\\n")
value = lambda option: words[words.index(option) + 1] if option in words else None
out = pathlib.Path(value("--out"))
mode = (here / "mode.txt").read_text().strip()
reads = json.loads((out / "reads.json").read_text())
covered = [{"node": row["node"], "output": row["output"], "entries": [f"layer/{row['node']}@1"], "exception": None,
            "why": ""} for row in reads]
if mode == "miss-one":
    covered = covered[1:]
if mode == "exception":
    covered = [dict(row, entries=[], exception="E1") for row in covered]
copy = None if mode == "no-copy" else {"sha256": "0" * 64, "role": "gltf"}
entries = [{"address": "model/rover@1", "kind": "model", "state": "draft", "status": "new", "node": "made@garage",
            "output": "1" * 64, "source": "", "copy": copy, "copy_why": "no copies command in this library yet",
            "quality": {"score": 0.8, "measures": {}}, "quality_why": ""}]
report = {"schema": "library-handover", "version": 1, "backend": "command", "library": "fake", "world": value("--world"),
          "place": value("--place"), "commit": value("--commit"), "command": words, "covered": covered,
          "entries": entries, "refused": [], "saved": {"committed": "c" * 40, "pushed": True, "why": ""}}
(out / "handover.json").write_text(json.dumps(report, indent=1, sort_keys=True))
'''


@pytest.fixture(autouse=True)
def no_real_library(monkeypatch):
    """No score_lib checkout beside score's, no library setting, and a cloud backend whose store is a fixed dict."""
    for variable in backend.VARIABLES:
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.setattr(backend.library_files, "defaults", lambda: {})
    provider = type(sys)("provider")
    provider.cloud = type("Cloud", (), {"object_store": staticmethod(lambda: FAKE_STORE)})
    monkeypatch.setitem(sys.modules, "provider", provider)


# --- the toy table --------------------------------------------------------------------------------------------------

def make_text(inputs, out, seed, params):
    (out / "made.txt").write_text(pathlib.Path(inputs["brief"]).read_text())


def judge_always(output, inputs, evidence):
    return checks.Verdict("ok", checks.PASS, "always")


def judge_never(output, inputs, evidence):
    return checks.Verdict("ok", checks.FAIL, "a showcase render that never passes here")


GROUND = graph.Stage("ground", "world", make_text, TOY, (checks.Check("ok", judge_always),),
                     files={"brief": "{data}/briefs/ground.txt"})
MADE = graph.Stage("made", "place", make_text, TOY, (checks.Check("ok", judge_always),),
                   files={"brief": "{data}/briefs/{place}.txt"})
FILM = graph.Stage("demo-film", "place", make_text, TOY, (checks.Check("ok", judge_never),),
                   files={"brief": "{data}/briefs/{place}.txt"}, after={"made": ("toy-text", 1)})


def world_data(root, free=False, exceptions=None):
    """The toy environment's data folder: its record, the briefs, the library-free decisions; and beside it the home
    with its one place's kept plan."""
    data = root / "data"
    (root / "home/design/plans").mkdir(parents=True, exist_ok=True)
    (root / f"home/design/plans/{PLACE}.json").write_text(json.dumps({"leads": {}}))
    for path, content in {"definitions/world.json": {"name": WORLD, "seed": 7},
                          "checks/library-free.json": {"worlds": [{"world": WORLD, "why": "a toy", "who": "@owner",
                                                                   "when": "2026-10-18"}] if free else []}}.items():
        (data / path).parent.mkdir(parents=True, exist_ok=True)
        (data / path).write_text(json.dumps(content))
    if exceptions is not None:
        (data / "checks/library-exceptions.json").write_text(json.dumps({"exceptions": exceptions}))
    (data / "briefs").mkdir()
    (data / "briefs/ground.txt").write_text("the ground")
    (data / f"briefs/{PLACE}.txt").write_text("the garage")
    return data


def toy_runner(root, free=False, exceptions=None):
    """A runner over the toy table and its library rows, in a folder and store of its own."""
    data = world_data(root, free, exceptions)
    table = (GROUND, MADE, FILM)
    return graph.Runner((*table, *library.rows(table, data)),
                        graph.Environment(WORLD, 7, {"data": str(data), "home": str(root / "home")}),
                        Store.in_folder(root / "store"))


def fake_library(root, monkeypatch, mode="full"):
    """The fake library's folder under `root`, its command set in the environment; its calls file."""
    folder = root / "library"
    folder.mkdir(parents=True)
    (folder / "handover.py").write_text(FAKE)
    (folder / "mode.txt").write_text(mode)
    monkeypatch.setenv("SCORE_LIB_ROOT", str(folder))
    monkeypatch.setenv("SCORE_LIB_COMMAND", f"{sys.executable} {folder / 'handover.py'}")
    return folder / "calls.txt"


def library_output(runner, place=PLACE):
    """The library node's newest output folder and its judgement's verdicts."""
    stage = runner.stages[library.WORLD_ROW if place is None else library.PLACE_ROW]
    record = runner.store.record(graph.node_name(stage, place), runner.key(stage, place)["key"])
    judgement = runner.store.judgements(record["node"], record["key"])[-1]
    return runner.store.checkout(record["output"]), judgement["verdicts"]


# --- the rows at the runner's seams ---------------------------------------------------------------------------------

def test_no_library_configured_fails_and_the_place_is_not_complete(tmp_path):
    runner = toy_runner(tmp_path)
    did = runner.run([PLACE])
    output, verdicts = library_output(runner)
    assert handover.report(output)["backend"] == "none"
    assert verdicts["configured"]["answer"] == checks.FAIL
    assert verdicts["configured"]["reason"] == "no library configured"
    assert "accepted" not in did[f"library@{PLACE}"], did
    waiting = dict(library.world_completion(runner, [PLACE]))
    assert f"library@{PLACE}" in waiting and "library-world" in waiting, waiting
    assert "not complete" in library.completion_line(WORLD, list(waiting.items()))


def test_a_library_free_environment_passes_and_is_complete(tmp_path):
    runner = toy_runner(tmp_path, free=True)
    did = runner.run([PLACE])
    _, verdicts = library_output(runner)
    assert all(verdict["answer"] == checks.PASS for verdict in verdicts.values()), verdicts
    assert did[f"library@{PLACE}"].endswith("accepted automatically"), did
    assert library.world_completion(runner, [PLACE]) == []


def test_a_configured_library_runs_once_with_the_templates_words(tmp_path, monkeypatch):
    calls = fake_library(tmp_path, monkeypatch)
    runner = toy_runner(tmp_path)
    did = runner.run([PLACE])
    assert did[f"library@{PLACE}"].endswith("accepted automatically"), did
    assert did["library-world"].endswith("accepted automatically"), did
    words = [json.loads(line) for line in calls.read_text().splitlines()]
    assert len(words) == 2, words  # the place's node and the environment's, once each
    place_words = next(found for found in words if "--place" in found)
    world_words = next(found for found in words if "--place" not in found)

    def after(option):
        return place_words[place_words.index(option) + 1]
    assert after("--world") == WORLD and after("--place") == PLACE and after("--seed") == "7"
    route = library.runner_route(runner)
    assert after("--route") == route == world_words[world_words.index("--route") + 1]
    assert runner.key(runner.stages[library.PLACE_ROW], PLACE)["params"]["route"] == route  # in the key
    assert after("--store") == str((tmp_path / "store/objects").resolve())
    assert place_words[place_words.index("handover") - 1] == str(tmp_path / "library")  # --root
    assert "--world" in world_words, world_words
    output, _ = library_output(runner)
    # the showcase render that never passed is read without
    assert handover.handed(output) == [{"node": f"made@{PLACE}", "output": handover.handed(output)[0]["output"],
                                        "into": ["demo-film"], "beyond": []}]
    again = runner.run([PLACE])
    assert again[f"library@{PLACE}"] == "fresh", again
    assert len(calls.read_text().splitlines()) == 2, "a second run called the library again"
    assert library.world_completion(runner, [PLACE]) == []


def test_the_route_moves_with_a_route_stages_code_only():
    rows = [graph.Stage(name, "place", make_text, TOY) for name in ("pixal", "surfaces-bake", "made")]
    codes = {"pixal": "a", "surfaces-bake": "b", "made": "c"}
    before = library.route(lambda stage: codes[stage.name], rows)
    codes["made"] = "c2"
    assert library.route(lambda stage: codes[stage.name], rows) == before, "a stage off the route moved the route"
    codes["surfaces-bake"] = "b2"
    assert library.route(lambda stage: codes[stage.name], rows) != before, "a route stage's code did not move it"


@pytest.mark.parametrize("mode, exceptions, answer", (
    ("miss-one", None, checks.FAIL),
    ("exception", [{"id": "E1", "place": PLACE, "prim": "/garage/*", "what": "a toy", "why": "a test",
                    "allowed_by": "@owner", "allowed_on": "2026-10-18"}], checks.PASS),
    ("exception", None, checks.FAIL)))  # an exception the data does not write covers nothing
def test_an_output_the_handover_misses_fails_handed_by_name_unless_a_written_exception_covers_it(
        tmp_path, monkeypatch, mode, exceptions, answer):
    fake_library(tmp_path, monkeypatch, mode)
    runner = toy_runner(tmp_path, exceptions=exceptions)
    runner.run([PLACE])
    _, verdicts = library_output(runner)
    assert verdicts["handed"]["answer"] == answer, verdicts["handed"]
    if answer == checks.FAIL:
        assert (f"made@{PLACE}" if mode == "miss-one" else "E1") in verdicts["handed"]["reason"]


def test_an_output_no_entry_holds_is_held_through_what_it_was_made_into(tmp_path):
    table = [graph.Stage("terrain", "world", make_text, TOY), graph.Stage("list", "place", make_text, TOY),
             graph.Stage("bake", "place", make_text, TOY, after={"list": ("toy-text", 1)}),
             graph.Stage("seed", "place", make_text, TOY, after={"terrain": ("toy-text", 1)}),
             graph.Stage("film", "place", make_text, TOY)]
    relation = library.made_into(table)
    place = {"place record": str(tmp_path / f"{PLACE}.json")}
    reads = library.reads_of({**place, **{name: str(tmp_path / (name[0] * 3)) for name in ("list", "bake", "film")}},
                             relation)
    assert {read["node"]: (read["into"], read["beyond"]) for read in reads} == {
        f"list@{PLACE}": (["bake"], []), f"bake@{PLACE}": ([], []), f"film@{PLACE}": ([], [])}, reads
    assert library.reads_of({"terrain": str(tmp_path / "ttt")}, relation)[0]["beyond"] == ["seed"]

    def judged(held):
        """`handed` over the reads, an entry holding each row in `held` and none the rest."""
        handover.write(tmp_path / handover.READS, reads)
        handover.write(tmp_path / handover.REPORT, {"covered": [
            {"node": read["node"], "output": read["output"], "exception": None, "why": "no exporter takes it",
             "entries": [f"layer/{read['node']}@1"] if read["node"].split("@")[0] in held else []}
            for read in reads]})
        return library_checks.judge_handed(tmp_path, {}, None)
    verdict = judged({"bake", "film"})  # the list is held through the bake made from it
    assert verdict.answer == checks.PASS and "(1 held through" in verdict.reason, verdict
    verdict = judged({"film"})  # neither the list nor the bake it was made into is held
    assert verdict.answer == checks.FAIL and {f"list@{PLACE}", f"bake@{PLACE}"} == {
        finding.split(" ")[0] for finding in verdict.findings}, verdict
    verdict = judged({"bake"})  # an output made into nothing held is held by no entry
    assert verdict.answer == checks.FAIL and verdict.findings[0].startswith(f"film@{PLACE}"), verdict


def test_a_missing_copy_is_unknown_never_a_pass(tmp_path, monkeypatch):
    fake_library(tmp_path, monkeypatch, "no-copy")
    runner = toy_runner(tmp_path)
    did = runner.run([PLACE])
    _, verdicts = library_output(runner)
    assert verdicts["copies"]["answer"] == checks.UNKNOWN
    assert "model/rover@1" in verdicts["copies"]["reason"]
    assert "accepted" not in did[f"library@{PLACE}"], did


def fixture_inputs(root, fixture):
    """The traced check's inputs over the library-finish check's fixture stage (data/checks/library/<fixture>), laid
    as a place named "fixture" with an assembly of that one stage."""
    data = world_data(root)
    (root / "home/design/plans/fixture.json").write_text("{}")
    assembled = root / "assembly"
    assembled.mkdir()
    (assembled / "fixture.usda").write_text((REPO / "data/checks/library" / fixture).read_text())
    output = root / "output"
    output.mkdir()
    handover.write(output / handover.REPORT, json.loads((HERE / "handover_example.json").read_text()))
    return output, {"world record": data / "definitions/world.json", "library free": data / "checks/library-free.json",
                    "place record": root / "home/design/plans/fixture.json", "assembly": assembled}


def fixture_library(root):
    """A library folder holding the entries the good fixture names (the library-finish check's own test's)."""
    for kind, entry_id in (("surface", "bare_steel"), ("surface", "deck"), ("model", "crate_1"), ("kit", "fixture"),
                           ("light", "lamp"), ("sound", "hum")):
        folder = root / "entries" / kind / entry_id / "1"
        folder.mkdir(parents=True)
        (folder / "entry.json").write_text(json.dumps({"schema": "score-lib-entry/1", "address": f"{kind}/{entry_id}@1",
                                                       "kind": kind, "id": entry_id, "version": 1, "state": "draft",
                                                       "files": {}, "provenance": {}}))
    return root


def test_traced_is_unknown_without_a_library_and_names_a_photo_finish(tmp_path, monkeypatch):
    output, inputs = fixture_inputs(tmp_path / "good", "good.usda")
    found = library_checks.judge_traced(output, inputs, None)
    assert found.answer == checks.UNKNOWN and "SCORE_LIB_ROOT" in found.reason, found
    monkeypatch.setenv("SCORE_LIB_ROOT", str(fixture_library(tmp_path / "library")))
    assert library_checks.judge_traced(output, inputs, None).answer == checks.PASS
    output, inputs = fixture_inputs(tmp_path / "bad", "bad.usda")
    found = library_checks.judge_traced(output, inputs, None)
    assert found.answer == checks.FAIL and "photo_of_a_crate.png" in found.reason, found


def test_the_shared_example_report_is_on_the_contract():
    """The report's shape is a contract both ways: the library repository keeps its own copy of this example."""
    example = json.loads((HERE / "handover_example.json").read_text())
    assert handover.report_faults(example) == []
    assert sorted(example) == sorted(handover.KEYS)
    for area, keys in handover.ROWS.items():
        assert all(sorted(row) == sorted(keys) for row in example[area]), area
    assert sorted(example["saved"]) == sorted(handover.SAVED_KEYS)
    assert handover.report_faults(dict(example, covered=[{"node": "x"}])), "a covered row without its keys passed"


def test_a_slow_library_is_a_transient_error(tmp_path, monkeypatch):
    (tmp_path / "slow.py").write_text("import time; time.sleep(5)")
    monkeypatch.setattr(backend, "TIMEOUT", 1)
    with pytest.raises(TimeoutError) as raised:
        backend.run([sys.executable, str(tmp_path / "slow.py")], {"SCORE_LIB_ROOT": str(tmp_path)}, tmp_path,
                    tmp_path)
    assert graph.transient(raised.value)


def test_the_environment_wins_over_the_defaults_and_the_cloud_store_only_without_a_blob_folder(monkeypatch):
    monkeypatch.setattr(backend.library_files, "defaults",
                        lambda: {"SCORE_LIB_ROOT": "/a/library", "SCORE_LIB_COMMAND": "lib --x"})
    found = backend.settings()
    assert found == {"SCORE_LIB_ROOT": "/a/library", "SCORE_LIB_COMMAND": "lib --x"}
    assert backend.kind(found) == backend.COMMAND
    monkeypatch.setenv("SCORE_LIB_ROOT", "/the/environment")
    assert backend.settings()["SCORE_LIB_ROOT"] == "/the/environment", "the default won over the environment"
    words = backend.arguments(backend.settings(), {"world": "w", "place": None, "seed": 1, "commit": "c", "route": "r",
                                                   "store": "s", "repo": "r", "out": "o"})
    assert words[:4] == ["lib", "--x", "--root", "/the/environment"] and "--place" not in words, words
    environment = backend.command_environment(backend.settings(), "s", "r")
    assert environment["SCORE_LIB_S3_BUCKET"] == "a-bucket" and environment["SCORE_LIB_S3_PREFIX"] == "score_lib"
    assert environment["AWS_ACCESS_KEY_ID"] == "AK" and environment["AWS_SECRET_ACCESS_KEY"] == "SK"
    monkeypatch.setenv("SCORE_LIB_BLOBS_DIR", "/the/blobs")
    environment = backend.command_environment(backend.settings(), "s", "r")
    assert "SCORE_LIB_S3_BUCKET" not in environment, "the cloud store was read over a blob store that was set"


def test_the_real_tables_library_rows_read_every_row_free_and_nothing_reads_them():
    from score import stages
    rows = {row.name: row for row in stages.STAGES}
    place, world = rows[library.PLACE_ROW], rows[library.WORLD_ROW]
    assert not place.paid and not world.paid
    # straight-masks is added after the library rows: only prepare's prediction reads it (score/stages/__init__.py)
    assert set(place.after) == {row.name for row in stages.STAGES if row.grain == "place"} - {
        library.PLACE_ROW, stages.masks_row.STAGE.name}
    assert set(world.after) == {row.name for row in stages.STAGES if row.grain == "world"} - {library.WORLD_ROW}
    assert set(place.optional) | set(world.optional) == set(library.SHOWCASE), (place.optional, world.optional)
    assert world.optional == ("environment-film",)  # the environment's film never holds it up
    assert not [row.name for row in stages.STAGES if library.PLACE_ROW in row.after or library.WORLD_ROW in row.after]


# --- the pictures ---------------------------------------------------------------------------------------------------

def test_a_lost_picture_never_stops_the_others(monkeypatch):
    def fetched(address, named):
        if address == "ground/lost@1":
            raise backend.library_files.LibraryUnreachable("fetch ground/lost@1 exited 1: 404 Not Found")
        return pathlib.Path(named)

    monkeypatch.setattr(pictures, "fetched", fetched)
    monkeypatch.setattr(backend, "settings", lambda: {"SCORE_LIB_ROOT": "lib"})
    monkeypatch.setattr(pictures, "pictured", lambda root, kinds: [("place/flat@1", "a.png"),
                                                                   ("ground/lost@1", "b.png")])
    monkeypatch.setattr(pictures, "viewed", lambda root, kinds: [("place/flat@1", "web3d/light.glb")])
    assert pictures.run() == ("library pictures (every kind) in the cache: 1 of 2 (1 not fetched, first: "
                              "ground/lost@1: fetch ground/lost@1 exited 1: 404 Not Found); viewer files: 1 of 1")


def test_an_item_pages_viewer_files_are_fetched_and_a_404_is_not_asked_again(tmp_path, monkeypatch):
    files = {"web3d/light.glb": "web3d", "web3d/full.glb": "web3d", "material.usda": "usd", "print.png": "texture",
             "settings.json": "record", "a.ogg": "audio", "b.ogg": "audio", "c.ogg": "audio", "d.ogg": "audio",
             "e.ogg": "audio", "sky.usda": "usd", "closeup.png": "closeup"}
    record = {"files": {name: {"role": role, "sha256": "f" * 64} for name, role in files.items()},
              "web3d": {"file": "web3d/full.glb", "light": "web3d/light.glb"}}
    assert pictures.viewer_files({**record, "kind": "model"}) == ["web3d/light.glb", "closeup.png"]
    assert pictures.viewer_files({**record, "kind": "surface"}) == ["web3d/light.glb", "material.usda", "print.png"]
    assert pictures.viewer_files({**record, "kind": "sound"})[1:] == ["a.ogg", "b.ogg", "c.ogg", "d.ogg"]
    assert pictures.viewer_files({**record, "kind": "effect"})[1:] == ["settings.json"]
    root = tmp_path / "lib"
    entry = root / "entries/model/crate/1/entry.json"
    entry.parent.mkdir(parents=True)
    entry.write_text(json.dumps({"files": {"web3d/light.glb": {"sha256": "a" * 64}}}))
    asked = []

    def lost(address, named):
        asked.append(named)
        raise backend.library_files.LibraryUnreachable("HeadObject: An error occurred (404) when calling it")

    monkeypatch.setattr(backend.library_files, "cache_folder", lambda: tmp_path / "cache")
    monkeypatch.setattr(pictures, "fetched", lost)
    assert pictures.held_or_why("model/crate@1", "web3d/light.glb", root)[0] is False
    assert "404 before" in pictures.held_or_why("model/crate@1", "web3d/light.glb", root)[1] and len(asked) == 1
    entry.write_text(json.dumps({"files": {"web3d/light.glb": {"sha256": "b" * 64}}}))  # new bytes: asked again
    pictures.held_or_why("model/crate@1", "web3d/light.glb", root)
    assert len(asked) == 2


# --- the invariant on small fixed sets ------------------------------------------------------------------------------

LIB_WORLD = "world1"


def row(address, node="pixal@garage", output="out-1", state="draft", place="garage", world=LIB_WORLD):
    kind, rest = address.split("/")
    entry_id, version = rest.split("@")
    return {"address": address, "kind": kind, "id": entry_id, "version": int(version), "state": state,
            "world": world, "place": place, "node": node, "output": output}


def report(*addresses, pushed=True):
    return {"entries": [{"address": address, "node": "pixal@garage"} for address in addresses],
            "saved": {"committed": "abc", "pushed": pushed, "why": "" if pushed else "no remote"}}


def held(node, report_of=None):
    return {"node": node, "output": "lib-out" if report_of else None,
            "why": "" if report_of else "nothing stands accepted", "report": report_of}


def agreeing():
    """An environment and a library that agree: the garage handed, its one entry held at its output."""
    handed = {"world": held("library-world", report()), "garage": held("library@garage", report("model/rover@2"))}
    return handed, [row("model/rover@1"), row("model/rover@2")], {"pixal@garage": "out-1"}


def rules(found):
    return {where: [item["rule"] for item in items] for where, items in found.items() if items}


def test_an_environment_and_a_library_that_agree_have_no_problem():
    handed, rows, accepted = agreeing()
    assert invariant.problems(LIB_WORLD, handed, rows, accepted, True) == {"world": [], "garage": []}


def test_no_library_leaves_every_node_not_handed():
    handed, rows, accepted = agreeing()
    found = invariant.problems(LIB_WORLD, handed, rows, accepted, False)
    assert rules(found) == {"world": ["not handed"], "garage": ["not handed"]}
    assert "no library is configured" in found["garage"][0]["sentence"]


def test_a_place_with_no_accepted_library_node_is_not_handed_by_name():
    handed, rows, accepted = agreeing()
    handed["hangar"] = held("library@hangar")
    found = invariant.problems(LIB_WORLD, handed, rows, accepted, True)
    assert rules(found) == {"hangar": ["not handed"]}
    assert found["hangar"][0]["sentence"] == ("The hangar is not handed to the library yet (library@hangar: nothing "
                                              "stands accepted).")


def test_an_address_the_library_lacks_or_holds_withdrawn_is_not_in_library():
    handed, rows, accepted = agreeing()
    handed["garage"]["report"] = report("model/rover@2", "model/crate@1", "model/cart@1")
    rows.append(row("model/cart@1", state="withdrawn"))
    found = invariant.problems(LIB_WORLD, handed, rows, accepted, True)
    assert rules(found) == {"garage": ["not in library", "not in library"]}
    assert [item["address"] for item in found["garage"]] == ["model/crate@1", "model/cart@1"]
    assert "withdrawn" in found["garage"][1]["sentence"]


def test_an_entry_whose_output_moved_on_is_named_and_a_repo_made_one_never_moves():
    handed, rows, _ = agreeing()
    found = invariant.problems(LIB_WORLD, handed, rows, {"pixal@garage": "out-2"}, True)
    assert rules(found) == {"garage": ["moved on"]}
    assert found["garage"][0]["sentence"] == ("model/rover@2 was made from an output the garage no longer holds "
                                              "(pixal@garage).")
    gone = invariant.problems(LIB_WORLD, handed, rows, {"pixal@garage": None}, True)
    assert "no longer has accepted" in gone["garage"][0]["sentence"]
    handed, rows, accepted = agreeing()
    rows.append(row("surface/steel@1", node=None, output=None))
    handed["garage"]["report"] = report("model/rover@2", "surface/steel@1")
    assert rules(invariant.problems(LIB_WORLD, handed, rows, accepted, True)) == {}


def test_a_newest_entry_no_handover_names_is_shown_nowhere_and_history_is_not_counted():
    handed, rows, accepted = agreeing()
    rows += [row("model/old_crate@1"), row("model/tank@1", world="world2"), row("model/hut@1", place="hangar")]
    found = invariant.problems(LIB_WORLD, handed, rows, accepted, True)
    assert rules(found) == {"garage": ["shown nowhere"], "world": ["shown nowhere"]}
    assert found["garage"][0]["address"] == "model/old_crate@1"
    assert found["world"][0]["address"] == "model/hut@1"  # the hangar has no library node: shown on the environment
    handed, rows, accepted = agreeing()
    rows[0]["output"] = "out-0"  # rover@1 made from an older output: history, not a problem
    assert rules(invariant.problems(LIB_WORLD, handed, rows, accepted, True)) == {}


def test_a_handover_that_did_not_push_is_not_pushed():
    handed, rows, accepted = agreeing()
    handed["garage"]["report"] = report("model/rover@2", pushed=False)
    found = invariant.problems(LIB_WORLD, handed, rows, accepted, True)
    assert rules(found) == {"garage": ["not pushed"]}
    assert found["garage"][0]["sentence"] == "The library's last handover of the garage did not push: no remote."


def write_entry(root, blobs, address, picture=b"\x89PNG fake picture bytes"):
    kind, rest = address.split("/")
    entry_id, version = rest.split("@")
    sha = "ab" + "0" * 62
    (blobs / "blobs" / sha[:2]).mkdir(parents=True, exist_ok=True)
    (blobs / "blobs" / sha[:2] / sha).write_bytes(picture)
    folder = root / "entries" / kind / entry_id / version
    folder.mkdir(parents=True)
    (folder / "entry.json").write_text(json.dumps({
        "schema": "score-lib-entry/1", "address": address, "kind": kind, "id": entry_id, "version": int(version),
        "state": "draft", "picture": {"file": "picture.png"}, "files": {"picture.png": {"sha256": sha}},
        "provenance": {"world": LIB_WORLD, "place": "garage", "node": "pixal@garage", "output": "out-1"}}))


def test_the_sweep_reads_a_library_folder_and_writes_the_cockpits_findings_with_the_entrys_picture(tmp_path):
    root, blobs, out = tmp_path / "library", tmp_path / "blobs", tmp_path / "out"
    write_entry(root, blobs, "model/rover@2")
    rows = sweep.library_rows(str(root))
    assert rows == [dict(row("model/rover@2"), picture="ab" + "0" * 62)]
    handed = {"garage": held("library@garage", report("model/rover@2"))}
    found = invariant.problems(LIB_WORLD, handed, rows, {"pixal@garage": "out-2"}, True)
    sweep.written("garage", handed["garage"], found["garage"], rows, str(blobs), out / "garage")
    on_disk = json.loads((out / "garage" / "findings.json").read_text())
    assert on_disk["answer"] == "fail" and on_disk["outputs"] == {"library@garage": "lib-out"}
    finding = on_disk["findings"][0]
    assert finding["rule"] == "moved on" and set(finding) == {"rule", "prim", "name", "sentence", "picture"}
    assert (out / "garage" / finding["picture"]).read_bytes() == b"\x89PNG fake picture bytes"
    assert sweep.library_rows("") == []


def test_a_library_free_environment_is_a_dated_decision(tmp_path):
    path = tmp_path / "free.json"
    path.write_text(json.dumps({"worlds": [{"world": LIB_WORLD, "why": "a test world", "who": "@owner", "when": ""}]}))
    assert not sweep.library_free(LIB_WORLD, path)  # an undated decision is no decision
    path.write_text(json.dumps({"worlds": [{"world": LIB_WORLD, "why": "a test", "who": "@owner",
                                            "when": "2026-10-18"}]}))
    assert sweep.library_free(LIB_WORLD, path) and not sweep.library_free("world2", path)


# --- the demos ------------------------------------------------------------------------------------------------------

GOOD = {"example": "the greenhouse's beds", "view": "plan", "bounds": [0, 0, 1, 1],
        "steps": [{"label": "The beds", "shapes": [{"kind": "area", "points": [[0, 0], [1, 0], [1, 1]], "tone": "c1"}]}]}


def test_a_demo_on_the_shape_has_no_problems_and_one_off_it_says_what():
    assert demos.problems(GOOD) == []
    off = {**GOOD, "view": "film", "steps": [{"label": "x", "shapes": [{"kind": "blob", "points": [[0, 0]]},
                                                                       {"kind": "dots", "points": [], "tone": "pink"}]}]}
    assert demos.problems(off) == ["view 'film'", "shape kind 'blob'", "tone 'pink'"]
    assert demos.problems({**GOOD, "view": "relief"}) == ["relief without heights"]


def test_a_demo_module_without_an_example_or_that_fails_is_missing_with_why_and_each_names_its_algorithm():
    class Without:
        @staticmethod
        def made(inputs):
            raise demos.NoExample("nothing kept")

    class Broken:
        @staticmethod
        def made(inputs):
            raise KeyError("beds")

    assert demos.made(Without) == {"missing": "nothing kept"}
    assert demos.made(Broken)["missing"].startswith("its demo failed: KeyError")
    found = demos.modules()
    assert "surface_recipes" in found and all(module.ALGORITHM == name for name, module in found.items())
