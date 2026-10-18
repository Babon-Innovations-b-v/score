"""The library rows at the runner's seams, with a fake library: a toy table of one world row, one place row and one
showcase render that never passes, the two library rows made from it by `library.rows`, a store of its own and a
PROPS_HOME of its own (the framework's store and the machine's library.env are never read or written).

    no library configured     library@garage says so, `configured` fails, the place is not complete
    library-free world        the same world named in library-free.json passes, and the world is complete
    a configured library      the fake command runs once with the template's words; a second run reuses the record
    coverage                  an output the handover misses fails `handed` by name; a written exception covers it
    copies, quality           a missing 3D copy is unknown, never a pass
    traced                    unknown while the library-finish check is not in the repository
    the report's shape        the shared example is on the contract, field for field
    a slow library            a run past its timeout is a transient error (tried again by the runner)
    the real table            the two rows read every row of their grain, the showcase renders optional, both free

Run: .venv/bin/python score/stages/library/library_test.py
"""
import json
import os
import pathlib
import shutil
import sys
import tempfile

HOME = pathlib.Path(tempfile.mkdtemp(prefix="library-test-"))
os.environ["PROPS_HOME"] = str(HOME / "props")  # before score.store reads it
for variable in ("SCORE_LIB_BACKEND", "SCORE_LIB_ROOT", "SCORE_LIB_COMMAND", "SCORE_LIB_BLOBS_DIR",
                 "SCORE_LIB_HANDOVER"):
    os.environ.pop(variable, None)
REPO = pathlib.Path(__file__).resolve().parents[3]
HERE = pathlib.Path(__file__).resolve().parent
sys.path[:] = [entry for entry in sys.path if pathlib.Path(entry or ".").resolve() != HERE]
sys.path.insert(0, str(REPO))

from score import checks, contracts, graph  # noqa: E402
from score.stages import library  # noqa: E402
from score.stages.library import backend, checks as library_checks, handover  # noqa: E402
from score.store import Store  # noqa: E402

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
    """The toy world's data folder: its record, a kit for its one place, the briefs, the library-free decisions."""
    data = root / "data"
    for path, content in {"definitions/world.json": {"name": WORLD, "seed": 7}, f"kit/{PLACE}.json": {"pieces": []},
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


def toy_runner(name, free=False, exceptions=None):
    """A runner over the toy table and its library rows, in a folder and store of its own."""
    root = HOME / name
    data = world_data(root, free, exceptions)
    table = (GROUND, MADE, FILM)
    return graph.Runner((*table, *library.rows(table, data)), graph.World(WORLD, 7, {"data": str(data)}),
                        Store.in_folder(root / "store"))


def fake_library(name, mode="full"):
    """The fake library's folder, its command set in the environment; its calls file."""
    root = HOME / name / "library"
    root.mkdir(parents=True)
    (root / "handover.py").write_text(FAKE)
    (root / "mode.txt").write_text(mode)
    os.environ.update({"SCORE_LIB_ROOT": str(root), "SCORE_LIB_COMMAND": f"{sys.executable} {root / 'handover.py'}"})
    return root / "calls.txt"


def no_library():
    for variable in backend.VARIABLES:
        os.environ.pop(variable, None)


def library_output(runner, place=PLACE):
    """The library node's newest output folder and its judgement's verdicts."""
    stage = runner.stages[library.WORLD_ROW if place is None else library.PLACE_ROW]
    record = runner.store.record(graph.node_name(stage, place), runner.key(stage, place)["key"])
    judgement = runner.store.judgements(record["node"], record["key"])[-1]
    return runner.store.checkout(record["output"]), judgement["verdicts"]


def test_no_library_configured():
    no_library()
    runner = toy_runner("none")
    did = runner.run([PLACE])
    output, verdicts = library_output(runner)
    assert handover.report(output)["backend"] == "none", handover.report(output)
    assert verdicts["configured"]["answer"] == checks.FAIL, verdicts["configured"]
    assert verdicts["configured"]["reason"] == "no library configured", verdicts["configured"]
    assert "accepted" not in did[f"library@{PLACE}"], did
    waiting = dict(library.world_completion(runner, [PLACE]))
    assert f"library@{PLACE}" in waiting and "library-world" in waiting, waiting
    assert "not complete" in library.completion_line(WORLD, list(waiting.items()))


def test_library_free_world():
    no_library()
    runner = toy_runner("free", free=True)
    did = runner.run([PLACE])
    _, verdicts = library_output(runner)
    assert all(verdict["answer"] == checks.PASS for verdict in verdicts.values()), verdicts
    assert did[f"library@{PLACE}"].endswith("accepted automatically"), did
    assert library.world_completion(runner, [PLACE]) == [], library.world_completion(runner, [PLACE])


def test_configured_library_runs_once():
    calls = fake_library("configured")
    runner = toy_runner("configured")
    did = runner.run([PLACE])
    assert did[f"library@{PLACE}"].endswith("accepted automatically"), did
    assert did["library-world"].endswith("accepted automatically"), did
    words = [json.loads(line) for line in calls.read_text().splitlines()]
    assert len(words) == 2, words  # the place's node and the world's, once each
    place_words = next(found for found in words if "--place" in found)
    world_words = next(found for found in words if "--place" not in found)
    value = place_words.__getitem__
    assert value(place_words.index("--world") + 1) == WORLD and value(place_words.index("--place") + 1) == PLACE
    assert value(place_words.index("--seed") + 1) == "7"
    assert value(place_words.index("--store") + 1) == str((HOME / "configured/store/objects").resolve())
    assert value(place_words.index("handover") - 1) == str(HOME / "configured/library")  # --root
    assert "--world" in world_words, world_words
    output, _ = library_output(runner)
    assert handover.handed(output) == [{"node": f"made@{PLACE}", "output": handover.handed(output)[0]["output"]}], \
        handover.handed(output)  # the showcase render that never passed is read without
    again = runner.run([PLACE])
    assert again[f"library@{PLACE}"] == "fresh", again
    assert len(calls.read_text().splitlines()) == 2, "a second run called the library again"
    assert library.world_completion(runner, [PLACE]) == []


def test_coverage():
    fake_library("miss-one", "miss-one")
    runner = toy_runner("miss-one")
    runner.run([PLACE])
    _, verdicts = library_output(runner)
    assert verdicts["handed"]["answer"] == checks.FAIL, verdicts["handed"]
    assert f"made@{PLACE}" in verdicts["handed"]["reason"], verdicts["handed"]
    fake_library("exception", "exception")
    runner = toy_runner("exception", exceptions=[{"id": "E1", "place": PLACE, "prim": "/garage/*", "what": "a toy",
                                                  "why": "a test", "allowed_by": "@owner",
                                                  "allowed_on": "2026-10-18"}])
    runner.run([PLACE])
    _, verdicts = library_output(runner)
    assert verdicts["handed"]["answer"] == checks.PASS, verdicts["handed"]
    fake_library("unwritten", "exception")
    runner = toy_runner("unwritten")
    runner.run([PLACE])
    _, verdicts = library_output(runner)
    assert verdicts["handed"]["answer"] == checks.FAIL and "E1" in verdicts["handed"]["reason"], verdicts["handed"]


def test_missing_copy_is_unknown():
    fake_library("no-copy", "no-copy")
    runner = toy_runner("no-copy")
    did = runner.run([PLACE])
    _, verdicts = library_output(runner)
    assert verdicts["copies"]["answer"] == checks.UNKNOWN, verdicts["copies"]
    assert "model/rover@1" in verdicts["copies"]["reason"], verdicts["copies"]
    assert "accepted" not in did[f"library@{PLACE}"], did


def fixture_inputs(name, fixture):
    """The traced check's inputs over the library-finish check's fixture stage (data/checks/library/<fixture>), laid
    as a place named "fixture" with an assembly of that one stage."""
    root = HOME / name
    data = world_data(root)
    (data / "kit/fixture.json").write_text("{}")
    assembled = root / "assembly"
    assembled.mkdir()
    (assembled / "fixture.usda").write_text((REPO / "data/checks/library" / fixture).read_text())
    output = root / "output"
    output.mkdir()
    handover.write(output / handover.REPORT, json.loads((HERE / "handover_example.json").read_text()))
    return output, {"world record": data / "definitions/world.json", "library free": data / "checks/library-free.json",
                    "place record": data / "kit/fixture.json", "assembly": assembled}


def fixture_library(name):
    """A library folder holding the entries the good fixture names (the library-finish check's own test's)."""
    root = HOME / name / "library"
    for kind, entry_id in (("surface", "bare_steel"), ("surface", "deck"), ("model", "crate_1"), ("kit", "fixture"),
                           ("light", "lamp"), ("sound", "hum")):
        folder = root / "entries" / kind / entry_id / "1"
        folder.mkdir(parents=True)
        (folder / "entry.json").write_text(json.dumps({"address": f"{kind}/{entry_id}@1", "kind": kind,
                                                       "id": entry_id, "version": 1, "state": "draft", "files": {},
                                                       "provenance": {}}))
    os.environ["SCORE_LIB_ROOT"] = str(root)


def test_traced():
    no_library()
    output, inputs = fixture_inputs("traced-none", "good.usda")
    found = library_checks.judge_traced(output, inputs, None)
    assert found.answer == checks.UNKNOWN and "SCORE_LIB_ROOT" in found.reason, found
    fixture_library("traced-good")
    found = library_checks.judge_traced(output, inputs, None)
    assert found.answer == checks.PASS, found
    output, inputs = fixture_inputs("traced-bad", "bad.usda")
    found = library_checks.judge_traced(output, inputs, None)
    assert found.answer == checks.FAIL and "photo_of_a_crate.png" in found.reason, found
    no_library()


def test_example_is_on_the_contract():
    example = json.loads((HERE / "handover_example.json").read_text())
    assert handover.report_faults(example) == [], handover.report_faults(example)
    assert sorted(example) == sorted(handover.KEYS), sorted(example)
    for area, keys in handover.ROWS.items():
        assert all(sorted(row) == sorted(keys) for row in example[area]), area
    assert sorted(example["saved"]) == sorted(handover.SAVED_KEYS)
    broken = dict(example, covered=[{"node": "x"}])
    assert handover.report_faults(broken), "a covered row without its keys passed"


def test_slow_library_is_transient():
    root = HOME / "slow"
    root.mkdir()
    (root / "slow.py").write_text("import time; time.sleep(5)")
    kept = backend.TIMEOUT
    backend.TIMEOUT = 1
    try:
        backend.run([sys.executable, str(root / "slow.py")], {"SCORE_LIB_ROOT": str(root)}, root, root)
    except TimeoutError as error:
        assert graph.transient(error), error
    else:
        raise AssertionError("a run past its timeout did not raise")
    finally:
        backend.TIMEOUT = kept


def test_settings_file():
    no_library()
    path = backend.settings_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# the machine's library\nSCORE_LIB_ROOT=/a/library\nSCORE_LIB_COMMAND='lib --x'\n")
    try:
        found = backend.settings()
        assert found == {"SCORE_LIB_ROOT": "/a/library", "SCORE_LIB_COMMAND": "lib --x"}, found
        assert backend.kind(found) == backend.COMMAND
        os.environ["SCORE_LIB_ROOT"] = "/the/environment"
        assert backend.settings()["SCORE_LIB_ROOT"] == "/the/environment", "the file won over the environment"
        words = backend.arguments(backend.settings(), {"world": "w", "place": None, "seed": 1, "commit": "c",
                                                       "store": "s", "repo": "r", "out": "o"})
        assert words[:4] == ["lib", "--x", "--root", "/the/environment"] and "--place" not in words, words
    finally:
        path.unlink()
        no_library()


def test_real_table():
    from score import stages
    rows = {row.name: row for row in stages.STAGES}
    place, world = rows[library.PLACE_ROW], rows[library.WORLD_ROW]
    assert not place.paid and not world.paid
    assert set(place.after) == {row.name for row in stages.STAGES if row.grain == "place"} - {library.PLACE_ROW}
    assert set(world.after) == {row.name for row in stages.STAGES if row.grain == "world"} - {library.WORLD_ROW}
    assert set(place.optional) == set(library.SHOWCASE), place.optional
    assert not any(library.PLACE_ROW in row.after or library.WORLD_ROW in row.after for row in stages.STAGES)


if __name__ == "__main__":
    try:
        for name, test in list(globals().items()):
            if name.startswith("test_"):
                test()
                print(f"ok {name}")
    finally:
        shutil.rmtree(HOME)
