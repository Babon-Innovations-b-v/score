"""The library rows at the runner's seams, with a fake library: a toy table of one environment row, one place row and one
showcase render that never passes, the two library rows made from it by `library.rows`, a store of its own and a
PROPS_HOME of its own (the framework's store, the machine's score_lib checkout and the cloud are never read or
written: the defaults and the cloud backend are fakes).

    no library configured     library@garage says so, `configured` fails, the place is not complete
    library-free environment        the same environment named in library-free.json passes, and the environment is complete
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

# Fakes: no score_lib checkout beside score's, and a cloud backend whose object store is a fixed dict.
backend.library_files.defaults = lambda: {}
FAKE_STORE = {"endpoint": "https://store.example", "region": "region-1", "bucket": "a-bucket", "access_key": "AK",
              "secret_key": "SK"}
sys.modules["provider"] = type(sys)("provider")
sys.modules["provider"].cloud = type("Cloud", (), {"object_store": staticmethod(lambda: FAKE_STORE)})

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
    """The toy environment's data folder: its record, a kit for its one place, the briefs, the library-free decisions."""
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
    return graph.Runner((*table, *library.rows(table, data)), graph.Environment(WORLD, 7, {"data": str(data)}),
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
    assert len(words) == 2, words  # the place's node and the environment's, once each
    place_words = next(found for found in words if "--place" in found)
    world_words = next(found for found in words if "--place" not in found)
    value = place_words.__getitem__
    assert value(place_words.index("--world") + 1) == WORLD and value(place_words.index("--place") + 1) == PLACE
    assert value(place_words.index("--seed") + 1) == "7"
    route = library.runner_route(runner)
    assert value(place_words.index("--route") + 1) == route == world_words[world_words.index("--route") + 1]
    assert runner.key(runner.stages[library.PLACE_ROW], PLACE)["params"]["route"] == route  # in the key
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


def test_route():
    rows = [graph.Stage(name, "place", make_text, TOY) for name in ("pixal", "surfaces-bake", "made")]
    codes = {"pixal": "a", "surfaces-bake": "b", "made": "c"}
    before = library.route(lambda stage: codes[stage.name], rows)
    codes["made"] = "c2"
    assert library.route(lambda stage: codes[stage.name], rows) == before, "a stage off the route moved the route"
    codes["surfaces-bake"] = "b2"
    assert library.route(lambda stage: codes[stage.name], rows) != before, "a route stage's code did not move it"


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
        (folder / "entry.json").write_text(json.dumps({"schema": "score-lib-entry/1", "address": f"{kind}/{entry_id}@1", "kind": kind,
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


def test_defaults_and_the_cloud_store():
    no_library()
    kept = backend.library_files.defaults
    backend.library_files.defaults = lambda: {"SCORE_LIB_ROOT": "/a/library", "SCORE_LIB_COMMAND": "lib --x"}
    try:
        found = backend.settings()
        assert found == {"SCORE_LIB_ROOT": "/a/library", "SCORE_LIB_COMMAND": "lib --x"}, found
        assert backend.kind(found) == backend.COMMAND
        os.environ["SCORE_LIB_ROOT"] = "/the/environment"
        assert backend.settings()["SCORE_LIB_ROOT"] == "/the/environment", "the default won over the environment"
        words = backend.arguments(backend.settings(), {"world": "w", "place": None, "seed": 1, "commit": "c", "route": "r",
                                                       "store": "s", "repo": "r", "out": "o"})
        assert words[:4] == ["lib", "--x", "--root", "/the/environment"] and "--place" not in words, words
        environment = backend.command_environment(backend.settings(), "s", "r")
        assert environment["SCORE_LIB_S3_BUCKET"] == "a-bucket" and environment["SCORE_LIB_S3_PREFIX"] == "score_lib"
        assert environment["AWS_ACCESS_KEY_ID"] == "AK" and environment["AWS_SECRET_ACCESS_KEY"] == "SK"
        os.environ["SCORE_LIB_BLOBS_DIR"] = "/the/blobs"
        environment = backend.command_environment(backend.settings(), "s", "r")
        assert "SCORE_LIB_S3_BUCKET" not in environment, "the cloud store was read over a blob store that was set"
    finally:
        backend.library_files.defaults = kept
        no_library()


def test_real_table():
    from score import stages
    rows = {row.name: row for row in stages.STAGES}
    place, world = rows[library.PLACE_ROW], rows[library.WORLD_ROW]
    assert not place.paid and not world.paid
    from score.stages.library import clips
    assert set(place.after) == {row.name for row in stages.STAGES if row.grain == "place"} - {library.PLACE_ROW,
                                                                                              clips.ROW}
    assert set(world.after) == {row.name for row in stages.STAGES if row.grain == "world"} - {library.WORLD_ROW,
                                                                                              clips.SAMPLE_ROW}
    assert set(place.optional) | set(world.optional) == set(library.SHOWCASE), (place.optional, world.optional)
    assert world.optional == ("environment-film",), world.optional  # the environment's film never holds it up
    # Only the clips row reads a library node: its make renders only what the handover made new without a clip.
    assert [row.name for row in stages.STAGES if library.PLACE_ROW in row.after or library.WORLD_ROW in row.after] \
        == [clips.ROW]


def test_a_lost_picture_never_stops_the_others():
    from score.stages.library import backend, pictures

    def fetched(address, named):
        if address == "ground/lost@1":
            raise backend.library_files.LibraryUnreachable("fetch ground/lost@1 exited 1: 404 Not Found")
        return pathlib.Path(named)

    saved = (pictures.fetched, pictures.pictured, pictures.viewed, backend.settings)
    pictures.fetched, backend.settings = fetched, lambda: {"SCORE_LIB_ROOT": "lib"}
    pictures.pictured = lambda root, kinds: [("place/flat@1", "a.png"), ("ground/lost@1", "b.png")]
    pictures.viewed = lambda root, kinds: [("place/flat@1", "web3d/light.glb")]
    try:
        said = pictures.run()
    finally:
        pictures.fetched, pictures.pictured, pictures.viewed, backend.settings = saved
    assert said == ("library pictures (every kind) in the cache: 1 of 2 (1 not fetched, first: ground/lost@1: fetch "
                    "ground/lost@1 exited 1: 404 Not Found); viewer files: 1 of 1"), said


def test_an_item_pages_viewer_files_are_fetched_and_a_404_is_not_asked_again():
    from score.stages.library import backend, pictures
    files = {"web3d/light.glb": "web3d", "web3d/full.glb": "web3d", "material.usda": "usd", "print.png": "texture",
             "settings.json": "record", "a.ogg": "audio", "b.ogg": "audio", "c.ogg": "audio", "d.ogg": "audio",
             "e.ogg": "audio", "sky.usda": "usd", "closeup.png": "closeup"}
    record = {"files": {name: {"role": role, "sha256": "f" * 64} for name, role in files.items()},
              "web3d": {"file": "web3d/full.glb", "light": "web3d/light.glb"}}
    assert pictures.viewer_files({**record, "kind": "model"}) == ["web3d/light.glb", "closeup.png"]
    assert pictures.viewer_files({**record, "kind": "surface"}) == ["web3d/light.glb", "material.usda", "print.png"]
    assert pictures.viewer_files({**record, "kind": "sound"})[1:] == ["a.ogg", "b.ogg", "c.ogg", "d.ogg"]
    assert pictures.viewer_files({**record, "kind": "effect"})[1:] == ["settings.json"]
    root = pathlib.Path(tempfile.mkdtemp(dir=HOME)) / "lib"
    entry = root / "entries/model/crate/1/entry.json"
    entry.parent.mkdir(parents=True)
    entry.write_text(json.dumps({"files": {"web3d/light.glb": {"sha256": "a" * 64}}}))
    asked = []

    def lost(address, named):
        asked.append(named)
        raise backend.library_files.LibraryUnreachable("HeadObject: An error occurred (404) when calling it")

    saved = (backend.library_files.cache_folder, pictures.fetched)
    backend.library_files.cache_folder, pictures.fetched = (lambda: root.parent / "cache"), lost
    try:
        assert pictures.held_or_why("model/crate@1", "web3d/light.glb", root)[0] is False
        assert "404 before" in pictures.held_or_why("model/crate@1", "web3d/light.glb", root)[1] and len(asked) == 1
        entry.write_text(json.dumps({"files": {"web3d/light.glb": {"sha256": "b" * 64}}}))  # new bytes: asked again
        pictures.held_or_why("model/crate@1", "web3d/light.glb", root)
    finally:
        backend.library_files.cache_folder, pictures.fetched = saved
    assert len(asked) == 2


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[3] / "conftest.py"))["refuse_outside_sandbox"]()
    try:
        for name, test in list(globals().items()):
            if name.startswith("test_"):
                test()
                print(f"ok {name}")
    finally:
        shutil.rmtree(HOME)
