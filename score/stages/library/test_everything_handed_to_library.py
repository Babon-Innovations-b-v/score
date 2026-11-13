"""The library rows' invariant: everything an environment holds is handed to the creator's library by its own command,
and every mismatch between the handover, the library and the store is named, never passed.

At the runner's seams, with a fake library command over a toy table (one environment row, one place row, one showcase
render that never passes) and a store of its own; the machine's score_lib checkout and the cloud are fakes:

    no library configured     library@garage says so, `configured` fails, the place is not complete
    library-free environment  the same environment named in library-free.json passes and is complete
    a configured library      the fake command runs once with the template's words; a second run reuses the record
    every accept handed       off by default; a run's automatic accept and the owner's start the handover (handed.py);
                              a failing command keeps the accept, writes failed.json and status counts what waits; the
                              retry covers it; an accept during a handover is taken by a second loop; an unpushed
                              report is not handed (owner, 2026-11-02, #40)
    the route                 on the toy runner, a route stage's code moves it, another stage's does not
    coverage                  an output the handover misses fails `handed` by name; a written exception covers it; an
                              output no entry holds is held through what it was made into
    copies                    a missing 3D copy is unknown, never a pass
    traced                    unknown with no library, pass on the good fixture, fail naming the photo on the bad one
    the report's shape        the shared example, as the library writes it, is on the contract field for field
                              (both repositories read it), and every report the node stores is; a covered row without
                              its keys leaves the node broken
    a slow library            a run past its timeout is a transient error (tried again by the runner)
    no frozen copy named      inside a run's frozen copy, the library's command (a library row's, the handover
                              process's) and handed.spawn's process name no copy in words or environment, and a child
                              the command left running ends with its row (2026-11-05: on the conductor they kept the
                              copy busy, so every carry, clean-cache and clean-frozen refused)
    the defaults              the environment wins over the defaults, a library the defaults alone name is found; the
                              cloud's store only when no blob folder is set (rows of the runner's seams)
    the real table            the two rows read every row of their grain but straight-masks, the showcase renders
                              optional, both free, and no row reads them (owner, 2026-10-22: no paid preview)
    pictures                  a lost picture never stops the others; a 404 is not asked again until the bytes change
    the invariant             each mismatch (not handed, not in library, moved on, shown nowhere, not pushed) gives
                              exactly its problem on small fixed sets, equal sets none; one row an environment through
                              the sweep's chain: the library folder read into rows, a library-free decision (dated, its
                              own environment) standing for a library, the cockpit's findings with the entry's picture
    demos                     a demo off the shape says what; one with no example or that fails is missing with why

Breaks that turn these red (each applied once, seen red, reverted, 2026-10-26):
- checks.uncovered: an output not in the handover left out of the findings (coverage).
- backend.settings: the defaults over the environment (the defaults).
- library.route: hash every stage, not only the route's (the route).
- handover.row_faults: skip the covered rows (the report's shape: the keyless report stored, 2026-11-13).
- invariant: `if now == row["output"]` -> `if True` (moved on never found).
- invariant.newest: keep the oldest version, not the newest (history is not counted).
- sweep.library_free: take a decision with no date (library free).
- pictures.held_or_why: ask a file marked lost again (pictures).
- demos.shape_problem: accept any shape kind (demos).
- library.rows: the place row reads straight-masks too (the real table).
- graph.Runner conclude: drop `self.hand_accepted()` after an automatic accept; hand_on_accept True by default;
  handed.hand_waiting: no record_failure; handed.drain: hand once (`while` -> `if` and no second look after the
  lock, together); handed.covered: count an unpushed report; web.hand_accept: say started without starting (every
  accept handed, 2026-11-02).
- backend.run: words or environment not through `outside`/`outside_frozen`; no `ended(process.pid)` after the command;
  handed.spawn: the environment only its SCORE_FROZEN marks dropped (the run's PYTHONPATH kept) (no frozen copy
  named, 2026-11-05).
- backend.passed_on: its `os.killpg(group, number)` dropped, or `return {}` always (a run's stop never reaches the command in
  its own session: review of 2026-11-05).
"""
import json
import os
import pathlib
import signal
import subprocess
import sys
import time

import pytest

from score import checks, contracts, graph
from score.conductor import disk
from score.stages import library
from score.review import web
from score.stages.library import backend, checks as library_checks, demos, handed, handover, invariant, pictures, sweep
from score.store import Store

REPO = pathlib.Path(__file__).resolve().parents[3]
HERE = pathlib.Path(__file__).resolve().parent
FAKE_STORE = {"endpoint": "https://store.example", "region": "region-1", "bucket": "a-bucket", "access_key": "AK",
              "secret_key": "SK"}
PLACE, WORLD = "garage", "toyworld"
TOY = contracts.Contract("toy-text", 1, lambda folder: [] if any(folder.glob("*.txt")) else ["no text file"])

# The fake library: writes handover.json from reads.json as its mode file says, and writes down each call's words and
# the blob store its environment names.
FAKE = '''import json, os, pathlib, sys
words = sys.argv[1:]
here = pathlib.Path(__file__).parent
seen = {name: os.environ.get(name) for name in ("SCORE_LIB_BLOBS_DIR", "SCORE_LIB_S3_BUCKET", "SCORE_LIB_S3_PREFIX",
                                               "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY")}
with (here / "calls.txt").open("a") as calls:
    calls.write(json.dumps({"words": words, "environment": seen}) + "\\n")
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
if mode == "example":  # the shared example as the library writes it, only this run's own words put in
    report = dict(json.loads((here / "example.json").read_text()), world=value("--world"), place=value("--place"),
                  commit=value("--commit"), command=words)
if mode == "keyless":
    report["covered"] = [{"node": "x"}]
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


GROUND = graph.Stage("surfaces-ground", "world", make_text, TOY, (checks.Check("ok", judge_always),),
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


def fake_library(root, monkeypatch, mode="full", found="environment", blobs=False):
    """The fake library's folder under `root`, its folder and command set where `found` says: in the environment over
    defaults naming another library, or in the defaults alone; with `blobs` a blob folder in the environment over a
    default one. Its calls file."""
    folder = root / "library"
    folder.mkdir(parents=True)
    (folder / "handover.py").write_text(FAKE)
    (folder / "mode.txt").write_text(mode)
    (folder / "example.json").write_text((HERE / "handover_example.json").read_text())
    ours = {"SCORE_LIB_ROOT": str(folder), "SCORE_LIB_COMMAND": f"{sys.executable} {folder / 'handover.py'}"}
    defaults = ours if found == "defaults" else {"SCORE_LIB_ROOT": "/a/library", "SCORE_LIB_COMMAND": "lib --x"}
    if found == "environment":
        for name, value in ours.items():
            monkeypatch.setenv(name, value)
    if blobs:
        defaults = {**defaults, "SCORE_LIB_BLOBS_DIR": "/the/default/blobs"}
        monkeypatch.setenv("SCORE_LIB_BLOBS_DIR", str(root / "blobs"))
    monkeypatch.setattr(backend.library_files, "defaults", lambda: defaults)
    return folder / "calls.txt"


def library_output(runner, place=PLACE):
    """The library node's newest output folder and its judgement's verdicts."""
    stage = runner.stages[library.WORLD_ROW if place is None else library.PLACE_ROW]
    record = runner.store.record(graph.node_name(stage, place), runner.key(stage, place)["key"])
    judgement = runner.store.judgements(record["node"], record["key"])[-1]
    return runner.store.checkout(record["output"]), judgement["verdicts"]


# --- the rows at the runner's seams ---------------------------------------------------------------------------------

EXCEPTION_E1 = {"id": "E1", "place": PLACE, "prim": "/garage/*", "what": "a toy", "why": "a test",
                "allowed_by": "@owner", "allowed_on": "2026-10-18"}


def seam(name, mode=None, free=False, exceptions=None, verdicts=None, accepted=True, calls=2, found="environment",
         blobs=False, broken=None):
    """One toy environment at the runner's seams: the fake library's mode (None: no library command), a library-free
    decision, the written exceptions; the library node's verdicts that do not pass (check: (answer, "is"/"has",
    reason text), every other verdict passes), whether its library nodes are accepted automatically, and how often
    the library's command ran (each node once; a failed output is made once more, an unknown one is not); where the
    library's settings are found (fake_library) and whether a blob folder is set; `broken`: why a report off the
    contract leaves both library nodes broken, with no output."""
    return pytest.param(mode, free, exceptions, verdicts or {}, accepted, calls, found, blobs, broken, id=name)


@pytest.mark.parametrize("mode, free, exceptions, verdicts, accepted, calls, found, blobs, broken", (
    seam("no library configured", verdicts={"configured": (checks.FAIL, "is", "no library configured"),
                                            "handed": (checks.FAIL, "has", f"made@{PLACE}"),
                                            "saved": (checks.FAIL, "has", "no library configured")}, accepted=False),
    seam("a library-free environment", free=True),
    seam("a configured library", mode="full"),
    seam("a library found by its defaults, the environment's blob folder over theirs", mode="full", found="defaults",
         blobs=True),
    seam("an output the handover misses", mode="miss-one",
         verdicts={"handed": (checks.FAIL, "has", f"made@{PLACE}")}, accepted=False, calls=4),
    seam("a written exception covers it", mode="exception", exceptions=[EXCEPTION_E1]),
    seam("an exception the data does not write covers nothing", mode="exception",
         verdicts={"handed": (checks.FAIL, "has", "E1")}, accepted=False, calls=4),
    seam("a missing copy is unknown, never a pass", mode="no-copy",
         verdicts={"copies": (checks.UNKNOWN, "has", "model/rover@1")}, accepted=False),
    seam("the shared example report is on the contract", mode="example",
         verdicts={"handed": (checks.FAIL, "has", f"made@{PLACE}"),
                   "refused": (checks.FAIL, "has", "model old_crate from pixal@garage: no take file in the output"),
                   "quality": (checks.UNKNOWN, "has", "surface/brushed_steel@1")}, accepted=False, calls=4),
    seam("a covered row without its keys is off the contract", mode="keyless",
         broken="covered row 1 lacks entries, exception, output, why"),
))
def test_the_library_node_hands_everything_by_the_librarys_command_once_and_names_what_it_misses(
        tmp_path, monkeypatch, mode, free, exceptions, verdicts, accepted, calls, found, blobs, broken):
    called = fake_library(tmp_path, monkeypatch, mode, found, blobs) if mode else None
    runner = toy_runner(tmp_path, free=free, exceptions=exceptions)
    asked = []
    monkeypatch.setattr(handed, "spawn", lambda store, job: asked.append(job))
    did = runner.run([PLACE])
    assert asked == [] and not (tmp_path / "store" / handed.FOLDER).exists()  # handing accepts is off unless asked
    if broken:
        stage = runner.stages[library.PLACE_ROW]
        assert runner.store.record(graph.node_name(stage, PLACE), runner.key(stage, PLACE)["key"]) is None
        assert did[f"library@{PLACE}"] == did["library-world"] == (
            f"broken: off its contract library-handover v1: {broken}"), did
        return
    output, found = library_output(runner)
    shared = handover.report(output)  # the library's report or score's own, on the contract field for field
    assert shared["backend"] == ("command" if mode else "none")
    assert sorted(shared) == sorted(handover.KEYS) and sorted(shared["saved"]) == sorted(handover.SAVED_KEYS), shared
    assert all(sorted(line) == sorted(keys) for area, keys in handover.ROWS.items() for line in shared[area]), shared
    assert set(verdicts) <= set(found), found
    for check, verdict in found.items():
        answer, how, text = verdicts.get(check, (checks.PASS, "has", ""))
        told = verdict["reason"]
        assert verdict["answer"] == answer and (told == text if how == "is" else text in told), (check, verdict)
    waiting = dict(library.world_completion(runner, [PLACE]))
    if accepted:
        assert did[f"library@{PLACE}"].endswith("accepted automatically"), did
        assert did["library-world"].endswith("accepted automatically"), did
        assert waiting == {}, waiting
    else:
        assert "accepted" not in did[f"library@{PLACE}"], did
        assert f"library@{PLACE}" in waiting, waiting
        assert "not complete" in library.completion_line(WORLD, list(waiting.items()))
    if mode is None:
        assert ("library-world" in waiting) is not free, waiting
        return
    # the library's own command with the template's words, for the place's node and for the environment's
    said = [json.loads(line) for line in called.read_text().splitlines()]
    words = [call["words"] for call in said]
    assert len(words) == calls, words
    place_words = next(said for said in words if "--place" in said)
    world_words = next(said for said in words if "--place" not in said)
    # the cloud's blob store only when no blob folder is set, and the environment's folder over the defaults'
    store = {"SCORE_LIB_BLOBS_DIR": str(tmp_path / "blobs"), "SCORE_LIB_S3_BUCKET": None, "SCORE_LIB_S3_PREFIX": None,
             "AWS_ACCESS_KEY_ID": None, "AWS_SECRET_ACCESS_KEY": None} if blobs else {
        "SCORE_LIB_BLOBS_DIR": None, "SCORE_LIB_S3_BUCKET": "a-bucket", "SCORE_LIB_S3_PREFIX": "score_lib",
        "AWS_ACCESS_KEY_ID": "AK", "AWS_SECRET_ACCESS_KEY": "SK"}
    assert all(call["environment"] == store for call in said), said

    def after(option):
        return place_words[place_words.index(option) + 1]
    assert after("--world") == WORLD and after("--place") == PLACE and after("--seed") == "7"
    route = library.runner_route(runner)
    assert after("--route") == route == world_words[world_words.index("--route") + 1]

    def moved(name):
        """The runner's route with row `name`'s code version moved."""
        return library.route(lambda stage: runner.code(stage) + ("-moved" if stage.name == name else ""),
                             runner.stages.values())
    assert moved(MADE.name) == route, "a stage off the route moved the route"
    assert moved(GROUND.name) != route, "a route stage's code did not move it"
    assert runner.key(runner.stages[library.PLACE_ROW], PLACE)["params"]["route"] == route  # in the key
    assert after("--store") == str((tmp_path / "store/objects").resolve())
    assert place_words[:3] == ["--root", str(tmp_path / "library"), "handover"], place_words  # the setting's own root
    assert "--world" in world_words, world_words
    # the showcase render that never passed is read without
    assert handover.handed(output) == [{"node": f"made@{PLACE}", "output": handover.handed(output)[0]["output"],
                                        "into": ["demo-film"], "beyond": []}]
    again = runner.run([PLACE])
    assert again[f"library@{PLACE}"] == "fresh", again
    assert len(called.read_text().splitlines()) == calls, "a second run called the library again"
    if not accepted:
        return
    # every accept handed the moment it is made: the run's automatic accept and the owner's start the handover; a
    # failing handover keeps the accept and the next one covers it
    store, nodes = runner.store, lambda: handed.nodes_of(runner.stages.values(), [PLACE])
    (tmp_path / f"data/briefs/{PLACE}.txt").write_text("the garage, again")
    runner.hand_on_accept = True
    assert runner.run([PLACE])[f"made@{PLACE}"].endswith("accepted automatically")
    made = store.accepted(f"made@{PLACE}")
    assert asked and {job["route"] for job in asked} == {route}, asked  # the run's accepts started the handover
    assert handed.waiting(store, WORLD, nodes()) == {None: [(GROUND.name, store.accepted(GROUND.name))],
                                                     PLACE: [(f"made@{PLACE}", made)]}
    job = {"world": WORLD, "seed": 7, "commit": asked[0]["commit"], "route": route, "repo": str(REPO)}
    library_command = backend.settings()["SCORE_LIB_COMMAND"]
    monkeypatch.setenv("SCORE_LIB_COMMAND", f"{sys.executable} -c 'import sys; sys.exit(3)'")
    handed.drain(store, WORLD, lambda: job, nodes, say=lambda line: None)
    assert store.accepted(f"made@{PLACE}") == made  # a failed handover never loses the accept
    assert "exited 3" in handed.failure(store, WORLD, PLACE)["error"]
    line = handed.status_line(store, WORLD, nodes())
    assert "2 accepted outputs not in the library yet (world 1, garage 1); failing: " in line, line
    monkeypatch.setenv("SCORE_LIB_COMMAND", library_command)
    loops, hand_waiting = [], handed.hand_waiting
    monkeypatch.setattr(handed, "hand_waiting", lambda *given: loops.append(
        "" if loops else handed.start(store, WORLD)) or hand_waiting(*given))  # an accept lands during the handover
    started = len(asked)
    assert web.hand_accept(store, WORLD) == "handover started" and len(asked) == started + 1  # the owner's accept
    handed.drain(store, WORLD, lambda: job, nodes, say=lambda line: None)
    assert loops == ["a handover is running: it hands this next", ""], loops  # taken by a second loop
    assert handed.failure(store, WORLD, PLACE) is None and handed.waiting(store, WORLD, nodes()) == {}
    assert handed.status_line(store, WORLD, nodes()).endswith("every accepted output is in the library")
    report = json.loads((handed.place_folder(store, WORLD, PLACE) / handover.REPORT).read_text())
    report["saved"]["pushed"] = False
    handover.write(handed.place_folder(store, WORLD, PLACE) / handover.REPORT, report)
    assert handed.waiting(store, WORLD, nodes()) == {PLACE: [(f"made@{PLACE}", made)]}  # not pushed: not handed


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


def test_a_slow_library_is_a_transient_error_and_no_handover_leaves_a_process_naming_a_frozen_copy(
        tmp_path, monkeypatch):
    # a run's frozen copy and its home, as graph/frozen.py lays them out, and the run's environment naming them
    home, copy = tmp_path / "home", tmp_path / "home/frozen/run-1"
    (home / "frozen/run-1.home/store/objects").mkdir(parents=True)
    copy.mkdir()
    monkeypatch.setenv("SCORE_FROZEN", str(copy))
    monkeypatch.setenv("PROPS_HOME", f"{copy}.home")
    monkeypatch.setenv("PYTHONPATH", f"{copy}/score/stages/props/ledger_tag{os.pathsep}/elsewhere")
    seen = tmp_path / "seen.json"
    (tmp_path / "lingers.py").write_text(  # the library's command leaving a child running, its words and environment
        "import json, os, subprocess, sys\n"
        "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])\n"
        f"open({str(seen)!r}, 'w').write(json.dumps({{'words': sys.argv, 'environment': dict(os.environ), "
        "'child': child.pid}))\n")
    backend.run([sys.executable, str(tmp_path / "lingers.py"), "--repo", str(copy), "--out",
                 f"{copy}.home/store/cache/making/k"], {"SCORE_LIB_ROOT": str(tmp_path)},
                f"{copy}.home/store/objects", str(copy))
    said = json.loads(seen.read_text())
    assert copies_named(home, said["words"], said["environment"]) == [], said  # neither words nor environment
    assert said["words"][said["words"].index("--repo") + 1] == str(backend.main_checkout())
    assert said["environment"]["PROPS_HOME"] == str(home)
    deadline = time.monotonic() + 5
    while running(said["child"]) and time.monotonic() < deadline:
        time.sleep(0.05)
    assert not running(said["child"]), "a child of the handover outlived its row"
    assert disk.working(home / "frozen") == {}  # the conductor's own count: nothing works in the copy

    (tmp_path / "slow.py").write_text("import time; time.sleep(5)")
    monkeypatch.setattr(backend, "TIMEOUT", 1)
    with pytest.raises(TimeoutError) as raised:
        backend.run([sys.executable, str(tmp_path / "slow.py")], {"SCORE_LIB_ROOT": str(tmp_path)}, tmp_path,
                    tmp_path)
    assert graph.transient(raised.value)

    # the run's stop reaches the command in its own session: passed on to its group, then handled as before
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"], start_new_session=True)
    heard = []
    before = signal.signal(signal.SIGTERM, lambda number, frame: heard.append(number))
    try:
        passed = backend.passed_on(child.pid)
        os.kill(os.getpid(), signal.SIGTERM)
        assert child.wait(5) == -signal.SIGTERM and heard == [signal.SIGTERM], (child.poll(), heard)
        for number, handler in passed.items():
            signal.signal(number, handler)
    finally:
        signal.signal(signal.SIGTERM, before)
        child.kill()


    # the detached handover process a run's accept starts (handed.spawn) names no frozen copy either
    started, checkout = [], backend.main_checkout()
    monkeypatch.setattr(backend, "main_checkout", lambda: checkout)
    monkeypatch.setattr(handed.subprocess, "Popen", lambda words, **given: started.append((words, given)))
    handed.spawn(Store.in_folder(home / "store"), {"world": WORLD, "commit": "c" * 40, "route": "r"})
    (words, given), = started
    assert copies_named(home, words, given["env"]) == [], given["env"]


def copies_named(home, words, environment):
    """The words and variables (NAME=value) that name a copy under `home`/frozen, as the conductor reads them
    (disk.working: a whole word, a variable's value, each path of a path list)."""
    found = []
    for word in words + [f"{name}={value}" for name, value in environment.items()]:
        value = word.partition("=")[2] if "=" in word and not word.startswith("/") else word
        if any(disk.copy_named(home / "frozen", part) for part in value.split(os.pathsep) if part):
            found.append(word)
    return found


def running(pid):
    """Whether the process `pid` still runs (a zombie waiting to be reaped has ended)."""
    stat = pathlib.Path(f"/proc/{pid}/stat")
    try:
        return stat.read_text().rsplit(") ", 1)[1][0] != "Z"
    except FileNotFoundError:
        return False


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
PICTURE, PICTURE_SHA = b"\x89PNG fake picture bytes", "ab" + "0" * 62
LIBRARY = ({"address": "model/rover@1"}, {"address": "model/rover@2"})  # the garage's one entry, two versions
DATED = {"why": "a test", "who": "@owner", "when": "2026-10-18"}
UNCONFIGURED = {"world": ["not handed"], "garage": ["not handed"]}
NOT_CONFIGURED_SAID = (("garage", 0, "sentence", "has", "no library is configured"),)


def row(address, node="pixal@garage", output="out-1", state="draft", place="garage", world=LIB_WORLD):
    """One library row as the invariant reads it (sweep.entry_row's shape, its picture left out)."""
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


def write_entry(root, blobs, spec):
    """One library entry's folder from a row spec, its picture's bytes in the blob folder."""
    entry = row(**spec)
    (blobs / "blobs" / PICTURE_SHA[:2]).mkdir(parents=True, exist_ok=True)
    (blobs / "blobs" / PICTURE_SHA[:2] / PICTURE_SHA).write_bytes(PICTURE)
    folder = root / "entries" / entry["kind"] / entry["id"] / str(entry["version"])
    folder.mkdir(parents=True)
    (folder / "entry.json").write_text(json.dumps({
        "schema": "score-lib-entry/1", "address": entry["address"], "kind": entry["kind"], "id": entry["id"],
        "version": entry["version"], "state": entry["state"], "picture": {"file": "picture.png"},
        "files": {"picture.png": {"sha256": PICTURE_SHA}},
        "provenance": {key: entry[key] for key in ("world", "place", "node", "output")}}))


def case(name, expect, said=(), library=LIBRARY, free=(), garage=("model/rover@2",), pushed=True, hangar=False,
         accepted=None):
    """One environment and library: the library's entries (None: no library folder), the library-free decisions,
    what the garage's handover names and whether it pushed, a hangar with no library node, the accepted outputs; the
    rules found where (empty places left out) and what the problems say: (where, index, field, "is"/"has", text)."""
    world = {"library": library, "free": free, "garage": garage, "pushed": pushed, "hangar": hangar,
             "accepted": {"pixal@garage": "out-1"} if accepted is None else accepted}
    return pytest.param(world, expect, said, id=name)


@pytest.mark.parametrize("world, expect, said", (
    case("agree", {}),
    case("no library", UNCONFIGURED, NOT_CONFIGURED_SAID, library=None),
    case("an undated free decision is no decision", UNCONFIGURED, NOT_CONFIGURED_SAID, library=None,
         free=({"world": LIB_WORLD, **DATED, "when": ""},)),
    case("another environment's free decision", UNCONFIGURED, NOT_CONFIGURED_SAID, library=None,
         free=({"world": "world2", **DATED},)),
    case("a dated free decision configures", {"garage": ["not in library"]},
         (("garage", 0, "address", "is", "model/rover@2"),), library=None, free=({"world": LIB_WORLD, **DATED},)),
    case("a place with no accepted library node", {"hangar": ["not handed"]},
         (("hangar", 0, "sentence", "is",
           "The hangar is not handed to the library yet (library@hangar: nothing stands accepted)."),), hangar=True),
    case("an address the library lacks or holds withdrawn", {"garage": ["not in library", "not in library"]},
         (("garage", 0, "address", "is", "model/crate@1"), ("garage", 1, "address", "is", "model/cart@1"),
          ("garage", 1, "sentence", "has", "withdrawn")),
         library=(*LIBRARY, {"address": "model/cart@1", "state": "withdrawn"}),
         garage=("model/rover@2", "model/crate@1", "model/cart@1")),
    case("moved on", {"garage": ["moved on"]},
         (("garage", 0, "sentence", "is",
           "model/rover@2 was made from an output the garage no longer holds (pixal@garage)."),),
         accepted={"pixal@garage": "out-2"}),
    case("no longer accepted", {"garage": ["moved on"]}, (("garage", 0, "sentence", "has", "no longer has accepted"),),
         accepted={"pixal@garage": None}),
    case("a repo-made entry never moves", {}, library=(*LIBRARY, {"address": "surface/steel@1", "node": None,
                                                                  "output": None}),
         garage=("model/rover@2", "surface/steel@1")),
    case("a newest entry no handover names", {"garage": ["shown nowhere"], "world": ["shown nowhere"]},
         (("garage", 0, "address", "is", "model/old_crate@1"),
          ("world", 0, "address", "is", "model/hut@1")),  # the hangar has no library node: shown on the environment
         library=(*LIBRARY, {"address": "model/old_crate@1"}, {"address": "model/tank@1", "world": "world2"},
                  {"address": "model/hut@1", "place": "hangar"})),
    case("history is not counted", {}, library=({"address": "model/rover@1", "output": "out-0"},
                                                {"address": "model/rover@2"})),
    case("not pushed", {"garage": ["not pushed"]},
         (("garage", 0, "sentence", "is", "The library's last handover of the garage did not push: no remote."),),
         pushed=False),
))
def test_every_mismatch_between_handover_library_and_store_is_named_where_the_cockpit_reads_it(
        tmp_path, world, expect, said):
    """The sweep's chain on one environment: the library folder read into rows, the library-free decision, the
    invariant's problems, each place's findings.json with the entry's picture beside it."""
    root, blobs, out, free = tmp_path / "library", tmp_path / "blobs", tmp_path / "out", tmp_path / "free.json"
    for spec in world["library"] or ():
        write_entry(root, blobs, spec)
    rows = sweep.library_rows(str(root) if world["library"] is not None else "")
    assert rows == [dict(row(**spec), picture=PICTURE_SHA) for spec in sorted(
        world["library"] or (), key=lambda spec: row(**spec)["address"].replace("@", "/"))], rows
    free.write_text(json.dumps({"worlds": list(world["free"])}))
    configured = world["library"] is not None or sweep.library_free(LIB_WORLD, free)
    handed = {"world": held("library-world", report()),
              "garage": held("library@garage", report(*world["garage"], pushed=world["pushed"]))}
    if world["hangar"]:
        handed["hangar"] = held("library@hangar")
    found = invariant.problems(LIB_WORLD, handed, rows, world["accepted"], configured)
    assert {where: [item["rule"] for item in items] for where, items in found.items() if items} == expect, found
    assert set(found) == set(handed), found
    for where, index, field, how, text in said:
        told = found[where][index][field]
        assert (told == text if how == "is" else text in told), (where, index, field, told)
    addresses = {entry["address"] for entry in rows}
    for where, node in handed.items():
        sweep.written(where, node, found[where], rows, str(blobs), out / where)
        on_disk = json.loads((out / where / "findings.json").read_text())
        assert on_disk["answer"] == ("fail" if expect.get(where) else "pass"), on_disk
        assert on_disk["outputs"] == ({node["node"]: "lib-out"} if node["report"] else {}), on_disk
        assert [finding["rule"] for finding in on_disk["findings"]] == expect.get(where, []), on_disk
        for finding in on_disk["findings"]:
            assert set(finding) == {"rule", "prim", "name", "sentence", "picture"}, finding
            if finding["name"] in addresses:  # the entry's picture copied beside its findings
                assert (out / where / finding["picture"]).read_bytes() == PICTURE, finding
            else:
                assert finding["picture"] is None, finding


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
