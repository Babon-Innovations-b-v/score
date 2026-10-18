"""The runner reruns only what a change reaches, blocks on unknown, accepts by itself only what passed and got no
worse, goes back on the owner's reject, and keeps every finish record. A toy table of two stages, two places, in a
store of its own.

Run: .venv/bin/python score/graph/graph_test.py
"""
import contextlib
import dataclasses
import functools
import importlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import types

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from score import checks, contracts, graph, review  # noqa: E402
from score.adapters import compute  # noqa: E402
compute.cloud_bill = lambda: 0.0  # no cloud: the provider's bill is never read here
from score.graph import _code, rebuy  # noqa: E402
from score.store import Store, tree_hash  # noqa: E402

MADE = []
TICKETS = []


def make_clean(inputs, out, seed, params):
    MADE.append("clean")
    (out / "clean.txt").write_text(inputs["brief"].read_text().upper())


def judge_words(output, inputs, evidence):
    words = len((output / "clean.txt").read_text().split())
    limit = json.loads(evidence.read_text())["limit"]
    return checks.Verdict("words", checks.PASS if words <= limit else checks.FAIL, f"{words} words, limit {limit}",
                          {"words": words}, {"words": "lower"})


def make_count(inputs, out, seed, params):
    MADE.append("count")
    (out / "count.txt").write_text(str(len((inputs["clean"] / "clean.txt").read_text())))


def judge_count(output, inputs, evidence):
    return checks.Verdict("counted", checks.PASS, "a count was written")


def text_faults(folder):
    return [] if any(folder.glob("*.txt")) else ["no text file"]


TEXT = contracts.Contract("toy-text", 1, text_faults)
CLEAN = graph.Stage("clean", "place", make_clean, TEXT, (checks.Check("words", judge_words, evidence="a word limit"),),
                    files={"brief": "{data}/{place}/brief.txt"})
COUNT = graph.Stage("count", "place", make_count, TEXT, (checks.Check("counted", judge_count),),
                    after={"clean": ("toy-text", 1)})
PLACES = ("hangar", "station")


def a_world(briefs):
    data = pathlib.Path(tempfile.mkdtemp())
    for place, brief in briefs.items():
        (data / place).mkdir()
        (data / place / "brief.txt").write_text(brief)
    return graph.World("toy", 7, {"data": data})


def a_runner(world, store, stages=(CLEAN, COUNT)):
    return graph.Runner(stages, world, store, model_record=lambda kind: {"kind": kind})


def give_evidence(store, runner, place, limit):
    output = store.record(f"clean@{place}", runner.key(CLEAN, place)["key"])["output"]
    path = pathlib.Path(tempfile.mkdtemp()) / "limit.json"
    path.write_text(json.dumps({"limit": limit}))
    store.put_evidence("words", output, path)
    return output


def ready_world():
    """Both places made, given evidence and accepted by the runner; the world, store and clean outputs."""
    world, store = a_world({"hangar": "a ship in a hall", "station": "a hub"}), Store.in_folder(tempfile.mkdtemp())
    runner = a_runner(world, store)
    runner.run(PLACES)
    outputs = {place: give_evidence(store, runner, place, 10) for place in PLACES}
    runner.run(PLACES)
    return world, store, outputs


def test_missing_evidence_blocks_what_follows_and_new_evidence_judges_again_without_remaking():
    world, store = a_world({"hangar": "a ship in a hall"}), Store.in_folder(tempfile.mkdtemp())
    MADE.clear()
    first = a_runner(world, store).run(["hangar"])
    assert first["clean@hangar"] == "made: unknown"
    assert first["count@hangar"].startswith("blocked: clean@hangar answered unknown: words: no evidence")
    output = give_evidence(store, a_runner(world, store), "hangar", 10)
    second = a_runner(world, store).run(["hangar"])
    assert second == {"clean@hangar": "judged again, output kept: pass, accepted automatically",
                      "count@hangar": "made: pass, accepted automatically"}, second
    assert MADE == ["clean", "count"]
    assert store.accepts("clean@hangar")[-1]["by"] == "runner" and store.accepted("clean@hangar") == output
    assert a_runner(world, store).run(["hangar"]) == {"clean@hangar": "fresh", "count@hangar": "fresh"}


def test_the_runner_accepts_only_what_passed_and_got_no_worse():
    """Fault (the owner, 2026-10-11, 'why are you asking this?'): step 0 waited for his typed accept on every output,
    so work stalled asking him. The runner accepts by the gates now, and never what got worse."""
    world, store, outputs = ready_world()
    (world.roots["data"] / "hangar" / "brief.txt").write_text("a ship in a long dark hall")  # 4 words become 6
    runner = a_runner(world, store)
    runner.run(PLACES)
    give_evidence(store, runner, "hangar", 10)
    found = a_runner(world, store).run(PLACES)
    assert found["clean@hangar"] == "judged again, output kept: pass", found  # passed, but worse: not accepted
    assert found["count@hangar"].startswith("blocked: clean@hangar's output") and "is not accepted" in found[
        "count@hangar"]
    assert store.accepted("clean@hangar") == outputs["hangar"]


def test_an_owners_reject_moves_the_accepted_output_back_and_marks_what_read_it_stale():
    world, store, outputs = ready_world()
    (world.roots["data"] / "hangar" / "brief.txt").write_text("a ship")  # fewer words: better, accepted
    runner = a_runner(world, store)
    runner.run(PLACES)
    better = give_evidence(store, runner, "hangar", 10)
    found = a_runner(world, store).run(PLACES)
    assert found["clean@hangar"].endswith("accepted automatically") and store.accepted("clean@hangar") == better
    assert found["count@hangar"] == "made: pass, accepted automatically", found
    review.reject(store, "clean@hangar", better, "owner", "the hall is gone")
    assert store.accepted("clean@hangar") == outputs["hangar"]
    runner = a_runner(world, store)
    assert runner.stale("count@hangar") == ["clean@hangar"] and runner.stale("count@station") == []
    assert runner.status(PLACES)["count@hangar"].endswith("its accepted output is stale: clean@hangar moved")
    found = runner.run(PLACES)
    assert found["clean@hangar"] == "fresh", found  # the rejected output is not accepted again by the runner
    assert found["count@hangar"].startswith("blocked: clean@hangar's output")


def test_a_record_naming_a_stage_the_table_lacks_is_stale_not_a_crash():
    """Fault (2026-10-12): a node's accepted record named an earlier stage another runner wrote into the same store
    (the old light runner's lightkit under light@camp), and status crashed with a KeyError for every line."""
    world, store, _ = ready_world()
    lone = a_runner(world, store, (dataclasses.replace(COUNT, after={}),))  # count's records name clean
    assert lone.stale("count@hangar") == ["clean (a stage this table does not hold)"], lone.stale("count@hangar")
    assert lone.status(["hangar"])["count@hangar"].endswith("clean (a stage this table does not hold) moved")


def test_a_failed_gate_blocks_what_follows():
    world, store = a_world({"hangar": "a ship in a very long hall"}), Store.in_folder(tempfile.mkdtemp())
    runner = a_runner(world, store)
    runner.run(["hangar"])
    give_evidence(store, runner, "hangar", 2)
    found = a_runner(world, store).run(["hangar"])
    assert found["clean@hangar"] == "judged again, output kept: fail"
    assert found["count@hangar"] == "blocked: clean@hangar answered fail: words: 7 words, limit 2"


def make_maybe(inputs, out, seed, params):
    (out / "maybe.txt").write_text("read clean" if "clean" in inputs else "clean not usable: left out")


def test_an_optional_read_is_left_out_while_not_usable_and_taken_once_it_is():
    """A failed optional read does not block: the node runs without it, and again with it once it passes."""
    maybe = graph.Stage("maybe", "place", make_maybe, TEXT, (checks.Check("counted", judge_count),),
                        after={"clean": ("toy-text", 1)}, optional=("clean",))
    world, store = a_world({"hangar": "a ship in a very long hall"}), Store.in_folder(tempfile.mkdtemp())
    found = a_runner(world, store, (CLEAN, maybe)).run(["hangar"])  # clean unknown: no word limit yet
    assert found["maybe@hangar"].startswith("made: pass"), found
    give_evidence(store, a_runner(world, store, (CLEAN, maybe)), "hangar", 2)
    found = a_runner(world, store, (CLEAN, maybe)).run(["hangar"])
    assert found == {"clean@hangar": "judged again, output kept: fail", "maybe@hangar": "fresh"}, found
    assert (store.checkout(store.accepted("maybe@hangar")) / "maybe.txt").read_text() == "clean not usable: left out"
    (world.roots["data"] / "hangar" / "brief.txt").write_text("a hall")  # clean made again, then passes
    a_runner(world, store, (CLEAN, maybe)).run(["hangar"])
    give_evidence(store, a_runner(world, store, (CLEAN, maybe)), "hangar", 2)
    found = a_runner(world, store, (CLEAN, maybe)).run(["hangar"])
    assert found["maybe@hangar"].startswith("made: pass"), found
    assert (store.checkout(store.accepted("maybe@hangar")) / "maybe.txt").read_text() == "read clean"


def test_nothing_changed_runs_nothing():
    world, store, _ = ready_world()
    MADE.clear()
    assert set(a_runner(world, store).run(PLACES).values()) == {"fresh"}
    assert MADE == []


def test_a_place_stage_that_does_not_apply_has_no_node_for_that_place():
    world, store = a_world({"hangar": "a ship in a hall"}), Store.in_folder(tempfile.mkdtemp())
    only_hangar = dataclasses.replace(CLEAN, applies=lambda place: place == "hangar")
    found = a_runner(world, store, (only_hangar,)).status(PLACES)
    assert list(found) == ["clean@hangar"], found


def make_tally(inputs, out, seed, params):
    (out / "tally.txt").write_text(json.dumps("read clean" if "clean" in inputs else "read without clean"))


TALLY = graph.Stage("tally", "place", make_tally, TEXT, (checks.Check("counted", judge_count),),
                    after={"clean": ("toy-text", 1)})


def test_a_stage_reads_without_an_earlier_one_that_does_not_apply_to_its_place():
    world, store = a_world({"hangar": "a ship in a hall", "station": "a hub"}), Store.in_folder(tempfile.mkdtemp())
    only_hangar = dataclasses.replace(CLEAN, applies=lambda place: place == "hangar")
    runner = a_runner(world, store, (only_hangar, TALLY))
    first = runner.run(PLACES)
    assert first["tally@station"] == "made: pass, accepted automatically", first
    assert first["tally@hangar"].startswith("blocked: clean@hangar answered unknown"), first
    assert runner.earlier(TALLY, "station") == [] and runner.earlier(TALLY, "hangar") == ["clean@hangar"]
    output = store.accepted("tally@station")
    assert store.read_file(output, "tally.txt") == "read without clean"


def test_a_changed_input_reruns_only_what_it_reaches_and_the_accepted_output_stays():
    world, store, outputs = ready_world()
    (world.roots["data"] / "hangar" / "brief.txt").write_text("a ship in a dark hall")
    runner = a_runner(world, store)
    assert runner.status(PLACES)["clean@hangar"] == "to run: brief changed"
    MADE.clear()
    found = runner.run(PLACES)
    assert found["clean@hangar"].startswith("made: unknown")  # its new output has no evidence yet
    assert found["count@hangar"].startswith("blocked: clean@hangar answered unknown")
    assert found["clean@station"] == found["count@station"] == "fresh"
    assert MADE == ["clean"]
    assert store.accepted("clean@hangar") == outputs["hangar"]  # the newest output did not replace the accepted one


def test_an_output_that_comes_out_the_same_reruns_nothing_after_it():
    world, store, outputs = ready_world()
    (world.roots["data"] / "station" / "brief.txt").write_text("A HUB")  # the same once cleaned
    MADE.clear()
    found = a_runner(world, store).run(PLACES)
    assert found["clean@station"] == "made: pass" and found["count@station"] == "fresh"
    assert MADE == ["clean"]
    assert len(store.records("clean@station")) == 2  # both finish records kept


def test_why_walks_back_to_the_world_file():
    world, store, _ = ready_world()
    brief = tree_hash(world.roots["data"] / "hangar" / "brief.txt")
    lines = a_runner(world, store).why("count@hangar")
    assert lines[0].startswith("count@hangar: output") and "pass, accepted" in lines[0]
    assert lines[1].startswith("  clean@hangar: output") and "pass, accepted" in lines[1]
    assert f"brief {brief[:12]}" in lines[1]


def make_paid(inputs, out, seed, params):
    TICKETS.append(os.environ.get(compute.TICKET))
    make_count(inputs, out, seed, params)


def test_a_paid_stage_runs_cleared_by_the_runner_without_a_typed_yes():
    world, store, _ = ready_world()
    books = compute.ledger()
    books.entries = lambda: []
    unpriced = graph.Stage("render", "place", make_paid, TEXT, (checks.Check("counted", judge_count),),
                           after={"clean": ("toy-text", 1)}, paid=True)
    found = a_runner(world, store, (CLEAN, COUNT, unpriced)).run(["hangar"])
    assert "needs its estimate" in found["render@hangar"] and TICKETS == []
    paid = graph.Stage("render", "place", make_paid, TEXT, (checks.Check("counted", judge_count),),
                       after={"clean": ("toy-text", 1)}, paid=True, euros=0.5)
    runner = a_runner(world, store, (CLEAN, COUNT, paid))
    assert runner.run(["hangar"])["render@hangar"] == "made: pass, accepted automatically"
    key = runner.ticket("render@hangar")["key"]
    assert TICKETS == [f"render@hangar {key}"] and store.spend_yes("render@hangar", key) is None


def test_a_waiver_lets_a_failed_gate_through_for_its_key_only():
    world, store = a_world({"hangar": "a ship in a very long hall"}), Store.in_folder(tempfile.mkdtemp())
    runner = a_runner(world, store)
    runner.run(["hangar"])
    output = give_evidence(store, runner, "hangar", 2)
    key = runner.key(CLEAN, "hangar")["key"]
    store.write_waiver("clean@hangar", key, "words", {"by": "owner", "reason": "a long name", "at": graph.now()})
    found = a_runner(world, store).run(["hangar"])
    assert found["clean@hangar"] == "judged again, output kept: fail, accepted automatically", found
    assert store.accepted("clean@hangar") == output
    assert found["count@hangar"] == "made: pass, accepted automatically", found
    assert a_runner(world, store).status(["hangar"])["clean@hangar"] == "fail, waived: words, accepted"
    (world.roots["data"] / "hangar" / "brief.txt").write_text("a ship in a very long dark hall")
    runner = a_runner(world, store)
    runner.run(["hangar"])
    give_evidence(store, runner, "hangar", 2)
    found = a_runner(world, store).run(["hangar"])
    assert found["count@hangar"] == "blocked: clean@hangar answered fail: words: 8 words, limit 2", found

def make_nothing_written(inputs, out, seed, params):
    (out / "notes.md").write_text("no text file")


def test_every_output_carries_its_stamp_and_one_off_its_contract_is_not_stored():
    """Fault (review of step 0, 2026-10-11): no output carried a schema or version, and nothing checked one."""
    world, store, outputs = ready_world()
    stamp = json.loads((store.checkout(outputs["hangar"]) / contracts.STAMP).read_text())
    assert stamp == {"schema": "toy-text", "version": 1, "units": {}}
    assert store.records("clean@hangar")[-1]["contract"] == stamp
    off = graph.Stage("clean", "place", make_nothing_written, TEXT, files={"brief": "{data}/{place}/brief.txt"})
    fresh_store = Store.in_folder(tempfile.mkdtemp())
    found = a_runner(world, fresh_store, (off,)).run(["hangar"])
    assert found["clean@hangar"] == "broken: off its contract toy-text v1: no text file", found
    assert fresh_store.records("clean@hangar") == []


def test_a_reader_written_for_another_schema_version_is_blocked():
    world, store, _ = ready_world()
    newer = graph.Stage("count", "place", make_count, TEXT, (checks.Check("counted", judge_count),),
                        after={"clean": ("toy-text", 2)})
    found = a_runner(world, store, (CLEAN, newer)).run(["hangar"])
    assert found["count@hangar"] == "blocked: clean@hangar's output is toy-text v1; expected toy-text v2", found


def test_a_stage_without_a_contract_cannot_be_declared():
    try:
        graph.Stage("clean", "place", make_clean, None)
    except TypeError as refusal:
        assert "contract" in str(refusal)
        return
    raise AssertionError("a stage without a contract was declared")

def test_a_missing_input_blocks():
    world, store = a_world({}), Store.in_folder(tempfile.mkdtemp())
    assert a_runner(world, store).run(["hangar"])["clean@hangar"].startswith("blocked: clean@hangar: its input brief")


def place_briefs(place):
    """A stage's world files as a function of the place: the hangar reads a second file only it has."""
    return {"brief": "{data}/{place}/brief.txt", **({"notes": "{data}/hangar/notes.txt"} if place == "hangar" else {})}


def test_a_stage_whose_files_differ_by_place_keys_each_place_on_its_own_files():
    world, store = a_world({"hangar": "a ship in a hall", "station": "a hub"}), Store.in_folder(tempfile.mkdtemp())
    stage = graph.Stage("clean", "place", make_clean, TEXT, (checks.Check("words", judge_words, evidence="a limit"),),
                        files=place_briefs)
    runner = a_runner(world, store, (stage,))
    assert runner.run(PLACES)["clean@hangar"].startswith("blocked: clean@hangar: its input notes")
    (pathlib.Path(world.roots["data"]) / "hangar" / "notes.txt").write_text("notes")
    assert set(runner.key(stage, "hangar")["files"]) == {"brief", "notes"}
    assert set(runner.key(stage, "station")["files"]) == {"brief"}


def make_with_code(inputs, out, seed, params):
    """A make that imports a module from its declared code folder, in its own process and in a child's."""
    sys.path.insert(0, str(inputs["code"]))
    try:
        import made_here
    finally:
        sys.path.remove(str(inputs["code"]))
        sys.modules.pop("made_here", None)
    subprocess.run([sys.executable, "-c", "import made_here"], cwd=inputs["code"], check=True)
    (out / "made.txt").write_text(made_here.WORD)


def test_a_make_importing_from_a_declared_folder_leaves_its_hash_unchanged():
    world = a_world({"hangar": "a ship in a hall"})
    code = pathlib.Path(world.roots["data"]) / "code"
    code.mkdir()
    (code / "made_here.py").write_text("WORD = 'made'\n")
    before = tree_hash(code)
    stage = graph.Stage("coded", "place", make_with_code, TEXT, (checks.Check("counted", judge_count),),
                        files={"code": "{data}/code"})
    result = a_runner(world, Store.in_folder(tempfile.mkdtemp()), (stage,)).run(["hangar"])
    assert result["coded@hangar"].startswith("made: pass"), result
    assert tree_hash(code) == before and not (code / "__pycache__").exists()


def test_seeds_differ_by_stage_and_place_and_hold_for_the_same_ones():
    assert graph.node_seed(7, "clean", "hangar") == graph.node_seed(7, "clean", "hangar")
    assert len({graph.node_seed(7, "clean", "hangar"), graph.node_seed(7, "clean", "station"),
                graph.node_seed(7, "count", "hangar"), graph.node_seed(8, "clean", "hangar")}) == 4


def test_the_code_version_follows_imports_into_functions_and_sys_path_folders():
    sys.path.insert(0, str(_code.REPO / "tools/usd"))
    _code.search_folders.cache_clear()
    import complete
    found = {path.relative_to(_code.REPO).as_posix() for path in _code.source_files([complete.resting_check])}
    assert {"tools/usd/complete.py", "tools/usd/triage.py", "tools/usd/resting.py"} <= found, found
    assert not any(path.startswith(".venv") for path in found)


def test_a_wrapped_judge_s_own_module_is_in_the_code_version():
    """A check's judge wrapped by a helper elsewhere (functools.wraps) is hashed from its own module too, so a change
    to it reruns the node (the surface stage's guarded checks)."""
    root = pathlib.Path(tempfile.mkdtemp(prefix="_code_wrapped_", dir=_code.REPO / "score/graph"))
    saved = list(sys.path)
    try:
        (root / "own_judge.py").write_text("def judge(output, inputs, evidence):\n    return None\n")
        sys.path.insert(0, str(root))
        import own_judge
        wrapped = functools.wraps(own_judge.judge)(lambda output, inputs, evidence: None)
        assert "own_judge.py" in {path.name for path in _code.source_files([wrapped])}
    finally:
        sys.path[:] = saved
        sys.modules.pop("own_judge", None)
        shutil.rmtree(root)


def test_the_code_version_does_not_depend_on_the_order_of_the_path():
    """A name two path folders both hold is hashed from both, whichever one a process happened to put first (judge.py
    puts tools/props first when imported: a row's key moved between two runs with no file changed, 2026-10-11)."""
    root = pathlib.Path(tempfile.mkdtemp(prefix="_code_order_", dir=_code.REPO / "score/graph"))
    saved = list(sys.path)
    try:
        for name, text in (("first", "import shared_name\n\n\ndef work():\n    return shared_name\n"),
                           ("one", "VALUE = 1\n"), ("other", "VALUE = 2\n")):
            (root / name).mkdir()
            (root / name / ("top_of_order.py" if name == "first" else "shared_name.py")).write_text(text)
        sys.path[:0] = [str(root / "first")]
        found = []
        for order in (("one", "other"), ("other", "one")):
            sys.path[1:1] = [str(root / name) for name in order]
            _code.search_folders.cache_clear()
            sys.modules.pop("top_of_order", None)
            import top_of_order
            found.append(_code.source_files([top_of_order.work]))
            del sys.path[1:3]
        assert found[0] == found[1] and len(found[0]) == 3, found
    finally:
        sys.path[:] = saved
        _code.search_folders.cache_clear()
        sys.modules.pop("top_of_order", None)
        sys.modules.pop("shared_name", None)
        shutil.rmtree(root)


def test_a_folder_put_on_the_path_later_moves_no_code_version():
    """A folder a make or an import puts on the path after the process's first code version gives no stage another
    same-named module (stages_test's earlier tests gave effects-layer triage.py and feet.py, 2026-10-13)."""
    root = pathlib.Path(tempfile.mkdtemp(prefix="_code_later_", dir=_code.REPO / "score/graph"))
    saved = list(sys.path)
    try:
        for name, text in (("first", "import shared_name\n\n\ndef work():\n    return shared_name\n"),
                           ("one", "VALUE = 1\n"), ("later", "VALUE = 2\n")):
            (root / name).mkdir()
            (root / name / ("top_of_order.py" if name == "first" else "shared_name.py")).write_text(text)
        sys.path[:0] = [str(root / "first"), str(root / "one")]
        _code.search_folders.cache_clear()
        import top_of_order
        before = _code.source_files([top_of_order.work])
        sys.path.insert(0, str(root / "later"))
        assert _code.source_files([top_of_order.work]) == before and len(before) == 2, before
    finally:
        sys.path[:] = saved
        _code.search_folders.cache_clear()
        sys.modules.pop("top_of_order", None)
        sys.modules.pop("shared_name", None)
        shutil.rmtree(root)



def make_show(inputs, out, seed, params):
    """Its own clean text, and the other place's beside it."""
    others = sorted(name for name in inputs if name.startswith("clean@"))
    (out / "show.txt").write_text(" ".join((inputs[name] / "clean.txt").read_text() for name in ["clean", *others]))


SHOW = graph.Stage("show", "place", make_show, TEXT, (checks.Check("counted", judge_count),),
                   after={"clean": ("toy-text", 1)}, beside={"clean": ("toy-text", 1)},
                   neighbours=lambda place: [other for other in PLACES if other != place])


def test_a_stage_reads_other_places_beside_without_a_cycle():
    """Fault (2026-10-12): a place's references to the places it shows pointed at old seed files, so its views looked
    onto empty space. Each place reads the other's accepted output beside its own, versioned and waited on."""
    world, store, outputs = ready_world()
    runner = a_runner(world, store, (CLEAN, COUNT, SHOW))
    assert runner.earlier(SHOW, "hangar") == ["clean@hangar", "clean@station"]
    assert [graph.node_name(*node) for node in runner.line_nodes(["hangar"], whole=False)] == [
        "clean@hangar", "clean@station", "count@hangar", "show@hangar"]
    found = runner.drive(["hangar"], say=lambda line: None, jobs=1, whole=False)
    assert found["show@hangar"] == "made: pass, accepted automatically", found
    shown = store.checkout(store.accepted("show@hangar"))
    assert (shown / "show.txt").read_text() == "A SHIP IN A HALL A HUB"
    assert runner.key(SHOW, "hangar")["beside"] == {"clean@station": outputs["station"]}
    (world.roots["data"] / "station" / "brief.txt").write_text("a hub")  # the same words: the key holds
    assert runner.status(["hangar"])["show@hangar"] == "pass, accepted"
    (world.roots["data"] / "station" / "brief.txt").write_text("a ring")
    runner.run(["station"])
    give_evidence(store, runner, "station", 10)
    runner.run(["station"])
    assert runner.status(["hangar"])["show@hangar"] == ("to run: clean@station changed, its accepted output is stale: "
                                                      "clean@station moved")
    looping = dataclasses.replace(SHOW, name="loop", beside={"loop": ("toy-text", 1)})
    try:
        a_runner(world, store, (CLEAN, looping))
    except ValueError as refused:
        assert "cycle" in str(refused)
    else:
        raise AssertionError("a stage reading itself beside was declared")
    # A chain read beside with no loop (neighbours reads the assembly, which reads the claiming place's bake) stands.
    shown_again = dataclasses.replace(SHOW, name="show again", after={"show": ("toy-text", 1)},
                                      beside={"show": ("toy-text", 1)})
    a_runner(world, store, (CLEAN, COUNT, SHOW, shown_again))


def judge_seen(output, inputs, evidence):
    return checks.Verdict("seen", checks.PASS, "it was made")


def make_seen(inputs, out, seed, params):
    (out / "seen.txt").write_text("seen")


SOURCES = graph.Stage("seen", "place", make_seen, TEXT, (checks.Check("seen", judge_seen),),
                      files={"code": "{repo}/score/checks"})


def test_bytecode_in_a_declared_folder_is_left_out_of_its_key():
    world = a_world({"hangar": "a ship in a hall"})
    folder = pathlib.Path(world.roots["data"]) / "hangar"
    runner = a_runner(world, Store.in_folder(tempfile.mkdtemp()), (CLEAN,))
    before = runner.file_keys(CLEAN, "hangar")
    (folder / "__pycache__").mkdir()
    (folder / "__pycache__" / "brief.cpython-312.pyc").write_bytes(b"bytecode")
    (folder / "stray.pyc").write_bytes(b"bytecode")
    assert a_runner(world, runner.store, (CLEAN,)).file_keys(CLEAN, "hangar") == before


def made_with_bytecode_in_its_key(world, store, commit):
    """seen@hangar made and accepted by a runner that still hashed bytecode (before #67), as a committed tree at
    `commit` in a checkout whose score/checks held its own __pycache__."""
    saved = graph.source_hash, _code.git_commit
    graph.source_hash = tree_hash
    _code.git_commit = lambda: {"commit": commit, "uncommitted": False}
    try:
        assert a_runner(world, store, (SOURCES,)).run(["hangar"])["seen@hangar"].endswith("accepted automatically")
    finally:
        graph.source_hash, _code.git_commit = saved


def test_an_output_whose_key_moved_only_by_bytecode_is_kept_and_a_source_change_is_not():
    cache = _code.REPO / "score/checks/__pycache__"
    if not any(cache.glob("*.pyc")):
        import py_compile
        py_compile.compile(str(_code.REPO / "score/checks/__init__.py"))
    world = graph.World("toy", 7, {"data": str(pathlib.Path(tempfile.mkdtemp())), "repo": str(_code.REPO)})
    head, first = (subprocess.run(["git", "-C", str(_code.REPO), *command], capture_output=True, text=True,
                                  check=True).stdout.split()[-1]
                   for command in (["rev-parse", "HEAD"], ["rev-list", "--max-parents=0", "HEAD"]))
    for commit, kept in ((head, True), (first, False)):  # score/checks is as at HEAD; it was not there at first
        store = Store.in_folder(tempfile.mkdtemp())
        made_with_bytecode_in_its_key(world, store, commit)
        runner = a_runner(world, store, (SOURCES,))
        keyed = runner.key(SOURCES, "hangar")
        assert store.record("seen@hangar", keyed["key"]) is None  # the bytecode moved its key
        done = runner.run(["hangar"])["seen@hangar"]
        assert done == ("fresh" if kept else "made: pass"), (commit, done)
        if kept:
            carried = store.record("seen@hangar", keyed["key"])["carried"]
            assert carried["reason"] == graph.BYTECODE_REASON and carried["made by"]["commit"] == head
            assert carried["sources"]["code"]["at its commit"] == keyed["files"]["code"]


NOTED = graph.Stage("noted", "place", make_seen, TEXT, (checks.Check("seen", judge_seen),),
                    files={"notes": "{repo}/CLAUDE.md"})


def test_an_output_is_kept_over_a_change_only_with_a_proof_naming_every_changed_file():
    """noted@hangar made at the repository's first commit, when CLAUDE.md read otherwise: made again with no proof
    or one that leaves CLAUDE.md out; kept, with the proof in its record, when the proof names it."""
    world = graph.World("toy", 7, {"data": str(pathlib.Path(tempfile.mkdtemp())), "repo": str(_code.REPO)})
    first = subprocess.run(["git", "-C", str(_code.REPO), "rev-list", "--max-parents=0", "HEAD"],
                           capture_output=True, text=True, check=True).stdout.split()[0]
    for no_ops, kept in (({}, False), ({"README.md": "not read"}, False),
                         ({"CLAUDE.md": "only its wording changed"}, True)):
        store = Store.in_folder(tempfile.mkdtemp())
        saved = graph.source_hash, _code.git_commit
        graph.source_hash, _code.git_commit = (lambda path: "the file as it read then",
                                               lambda: {"commit": first, "uncommitted": False})
        try:
            assert a_runner(world, store, (NOTED,)).run(["hangar"])["noted@hangar"].endswith("automatically")
        finally:
            graph.source_hash, _code.git_commit = saved
        runner = a_runner(world, store, (NOTED,))
        keyed = runner.key(NOTED, "hangar")
        old = store.records("noted@hangar")[0]
        if no_ops:
            proof = pathlib.Path(tempfile.mkdtemp()) / "proof.json"
            proof.write_text(json.dumps({"from key": old["key"], "to key": keyed["key"], "no-ops": no_ops}))
            store.put_evidence(f"no-op-{keyed['key']}", old["output"], proof)
        done = runner.run(["hangar"])["noted@hangar"]
        assert done == ("fresh" if kept else "made: pass"), (no_ops, done)
        if kept:
            carried = store.record("noted@hangar", keyed["key"])["carried"]
            assert carried["reason"] == graph.NO_OP_REASON and carried["no-ops"] == no_ops
            assert carried["made by"]["commit"] == first and carried["from key"] == old["key"]


STAGE_SOURCE = """import {helper}
import {other}


def make(inputs, out, seed, params):
    (out / "made.txt").write_text({helper}.WORD + {other}.WORD + inputs["seeds"].read_text())
"""


OTHER_SOURCE = """def make(inputs, out, seed, params):
    (out / "made.txt").write_text("TOTALLY DIFFERENT " + inputs["seeds"].read_text())
"""


def stage_source(case):
    """narrow_a<case>'s source: a make reading both helpers."""
    return STAGE_SOURCE.format(helper=f"narrow_h{case}", other=f"narrow_g{case}")


@contextlib.contextmanager
def a_repo_of_its_own(case):
    """A temporary git repository, committed, holding a stage module that imports two helpers (`narrow_a<case>`
    imports `narrow_h<case>`, which imports `narrow_j<case>`, and `narrow_g<case>`), another module with a make of its
    own (`narrow_b<case>`) and a FRAMEWORK of none, taken as the repository while the block runs; yields (its folder,
    the stage module)."""
    repo = pathlib.Path(tempfile.mkdtemp(prefix="narrow_repo_")).resolve()
    (repo / f"narrow_h{case}.py").write_text(f'import narrow_j{case}\nWORD = "kept " + narrow_j{case}.WORD\n')
    (repo / f"narrow_j{case}.py").write_text('WORD = "joined "\n')
    (repo / f"narrow_g{case}.py").write_text('WORD = "also "\n')
    (repo / f"narrow_a{case}.py").write_text(stage_source(case))
    (repo / f"narrow_b{case}.py").write_text(OTHER_SOURCE)
    (repo / "score" / "graph").mkdir(parents=True)  # where the repository declares its FRAMEWORK, none at first
    (repo / "score" / "graph" / "_code.py").write_text("FRAMEWORK = {REPO / name for name in ()}\n")
    (repo / ".gitignore").write_text("__pycache__/\n")  # as this repository's: an import's bytecode is no change
    for command in (["init", "-q"], ["add", "."], ["-c", "user.name=test", "-c", "user.email=test@test", "commit",
                                                   "-qm", "a stage and its helper"]):
        subprocess.run(["git", "-C", str(repo), *command], check=True)
    saved = _code.REPO, _code.OUTSIDE, _code.FRAMEWORK, _code.search_folders
    _code.REPO, _code.OUTSIDE, _code.FRAMEWORK = repo, (repo / ".git",), set(_code.FRAMEWORK)
    _code.search_folders = lambda: (repo,)
    sys.path.insert(0, str(repo))
    try:
        yield repo, importlib.import_module(f"narrow_a{case}")
    finally:
        sys.path.remove(str(repo))
        _code.REPO, _code.OUTSIDE, _code.FRAMEWORK, _code.search_folders = saved


def test_an_output_whose_key_only_got_narrower_is_kept_and_a_changed_read_is_made_again():
    """A stage A that imports a helper H, made and accepted: H moved into FRAMEWORK moves A's key and the runner
    keeps A's accepted output, no proof file and no make (rebuy counts no buy); with A's own file also edited, its
    declared {seeds} file outside the repository changed, its make wired to another function in a file unchanged
    since (B), another Python, H itself edited or a file read only through H (J) edited or deleted, it makes A again.
    A second narrowing after the first (the other helper G moved too) is kept as well, still naming what made it."""
    for case, change, kept in ((0, None, True), (1, "own file", False), (2, "seeds", False),
                               (3, "make swapped", False), (4, "python", False), (5, "helper edited", False),
                               (6, "read through helper edited", False), (7, "second narrowing", True),
                               (8, "read through helper deleted", False)):
        seeds = pathlib.Path(tempfile.mkdtemp())
        (seeds / "hangar.txt").write_text("a seed")
        world = graph.World("toy", 7, {"seeds": str(seeds)})
        store = Store.in_folder(tempfile.mkdtemp())
        with a_repo_of_its_own(case) as (repo, module):
            stage = graph.Stage("narrow", "place", module.make, TEXT, (checks.Check("seen", judge_seen),),
                                files={"seeds": "{seeds}/{place}.txt"})
            first = a_runner(world, store, (stage,)).run(["hangar"])["narrow@hangar"]
            assert first == "made: pass, accepted automatically", first
            old = store.records("narrow@hangar")[0]
            _code.FRAMEWORK.add(repo / f"narrow_h{case}.py")
            if change == "own file":
                (repo / f"narrow_a{case}.py").write_text(stage_source(case) + "# read\n")
            if change == "helper edited":
                (repo / f"narrow_h{case}.py").write_text('WORD = "another word "\n')
            if change == "read through helper edited":
                (repo / f"narrow_j{case}.py").write_text('WORD = "another word "\n')
            if change == "read through helper deleted":
                (repo / f"narrow_j{case}.py").unlink()
            if change == "seeds":
                (seeds / "hangar.txt").write_text("another seed")
            if change == "make swapped":
                stage = dataclasses.replace(stage, make=importlib.import_module(f"narrow_b{case}").make)
            python = _code.sys
            if change == "python":
                _code.sys = types.SimpleNamespace(version_info=types.SimpleNamespace(major=3, minor=99), path=sys.path)
            try:
                runner = a_runner(world, store, (stage,))
                keyed = runner.key(stage, "hangar")
                assert keyed["key"] != old["key"] and store.record("narrow@hangar", keyed["key"]) is None
                assert (rebuy.to_make(runner, stage, "hangar", [], {}) is None) == kept, change
                done = runner.run(["hangar"])["narrow@hangar"]
            finally:
                _code.sys = python
            assert done.startswith("fresh" if kept else "made: pass"), (change, done)
            record = store.record("narrow@hangar", keyed["key"])
            if kept:
                assert record["output"] == old["output"] and record["code"] == keyed["code"]
                assert record["carried"] == {"reason": graph.NARROWING_REASON, "from key": old["key"],
                                             "to key": keyed["key"],
                                             "made by": {"commit": old["commit"], "code": old["code"]}}
                assert store.judgement("narrow@hangar", keyed["key"], runner.evidence_state(stage, old["output"]))
                if change == "second narrowing":
                    _code.FRAMEWORK.add(repo / f"narrow_g{case}.py")
                    runner = a_runner(world, store, (stage,))
                    again = runner.key(stage, "hangar")
                    assert again["key"] != keyed["key"]
                    assert runner.run(["hangar"])["narrow@hangar"].startswith("fresh")
                    assert store.record("narrow@hangar", again["key"])["carried"] == {
                        "reason": graph.NARROWING_REASON, "from key": keyed["key"], "to key": again["key"],
                        "made by": {"commit": old["commit"], "code": old["code"]}}
            else:
                assert "carried" not in record


def test_the_runners_store_lists_the_same_keys_walking_only_the_prefixs_folder():
    """scoped_keys answers every prefix as the store's whole walk does (a whole area, a node's folder, a name begun but
    not ended, one that is not there), its .partial files left out, and a runner puts it on every folder store."""
    root = pathlib.Path(tempfile.mkdtemp())
    for key in ("accepts/clean@hangar/1.json", "accepts/clean@hangar/2.json", "accepts/clean@station/1.json",
                "records/clean@hangar/k.json", "blobs/ab", "top.json", "accepts/clean@hangar/3.json.9.partial"):
        (root / key).parent.mkdir(parents=True, exist_ok=True)
        (root / key).write_text("{}")
    store = graph.score_store.runtime_store.FolderStore(root)
    for prefix in ("accepts/clean@hangar/", "accepts/", "accepts/clean@", "records/clean@hangar/k", "rejects/x/",
                   "", "top", "nothing/here/"):
        assert graph.scoped_keys(store, prefix) == graph.WHOLE_WALK(store, prefix), prefix
    a_runner(a_world({"hangar": "a ship"}), Store.in_folder(tempfile.mkdtemp()))
    assert graph.score_store.runtime_store.FolderStore.keys is graph.scoped_keys

def test_a_run_names_every_world_file_it_could_never_make_before_it_starts():
    """A planned row's missing {data} file is named (node, input, path) before anything runs; one made by the run
    (under {home}) is left to its row; with every file there, nothing is named."""
    world = a_world({"hangar": "a ship in a hall"})
    made = graph.Stage("made", "place", make_seen, TEXT, (checks.Check("seen", judge_seen),),
                       files={"take": "{home}/takes/{place}.glb"})
    world = graph.World("toy", 7, {**world.roots, "home": str(pathlib.Path(tempfile.mkdtemp()))})
    runner = a_runner(world, Store.in_folder(tempfile.mkdtemp()), (CLEAN, made))
    assert runner.missing_inputs([(CLEAN, "station"), (made, "hangar")]) == \
        [f"clean@station: brief ({pathlib.Path(world.roots['data']) / 'station/brief.txt'})"]
    assert runner.missing_inputs([(CLEAN, "hangar")]) == []


STRICT = {"on": False}  # the toy gate's code before (off) and after (on) it learned to see a fault


def judge_marks(output, inputs, evidence):
    if STRICT.get("old schema") and (output / "clean.txt").read_text().startswith("A "):
        raise KeyError("layers")  # today's gate reading a field the old output never wrote
    marks =(output / "clean.txt").read_text().split().count("X") if STRICT["on"] else 0
    return checks.Verdict("marks", checks.PASS, f"{marks} marks", {"marks": marks}, {"marks": "lower"})


MARKS = graph.Stage("clean", "place", make_clean, TEXT, (checks.Check("marks", judge_marks),),
                    files={"brief": "{data}/{place}/brief.txt"})


def test_the_accepted_output_is_judged_again_by_todays_gates_before_comparing():
    """Both ways (assembly@lab, 2026-10-15: its accepted output was judged before the triage asked each foot, so the
    chairs' caster read as two new faults): a fault the old gate could not see, on both outputs alike, does not block
    the runner's accept; a real new fault still does."""
    world, store = a_world({"hangar": "a x"}), Store.in_folder(tempfile.mkdtemp())
    STRICT["on"] = False
    first = a_runner(world, store, (MARKS,)).run(["hangar"])
    assert first["clean@hangar"] == "made: pass, accepted automatically", first
    STRICT["on"] = True  # today's gate sees the mark the accepted output had all along
    (world.roots["data"] / "hangar" / "brief.txt").write_text("b x")
    seen = a_runner(world, store, (MARKS,)).run(["hangar"])
    assert seen["clean@hangar"] == "made: pass, accepted automatically", seen
    (world.roots["data"] / "hangar" / "brief.txt").write_text("c x x")
    accepted = store.accepted("clean@hangar")
    worse = a_runner(world, store, (MARKS,)).run(["hangar"])
    STRICT["on"] = False
    assert worse["clean@hangar"] == "made: pass", worse  # one more mark, measured alike: worse, not accepted
    assert store.accepted("clean@hangar") == accepted


def test_a_gate_that_cannot_judge_the_accepted_output_again_compares_its_stored_verdict():
    """assembly@lab's accepted output of 10-11 has no `layers` in its origin, which today's layers gate reads: the
    runner compares that check's stored verdict instead of stopping."""
    world, store = a_world({"hangar": "a x"}), Store.in_folder(tempfile.mkdtemp())
    STRICT.update({"on": False, "old schema": False})
    a_runner(world, store, (MARKS,)).run(["hangar"])
    STRICT.update({"on": True, "old schema": True})
    (world.roots["data"] / "hangar" / "brief.txt").write_text("b x")
    found = a_runner(world, store, (MARKS,)).run(["hangar"])
    STRICT.update({"on": False, "old schema": False})
    assert found["clean@hangar"] == "made: pass", found  # its stored 0 marks against 1: worse, waits


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[2] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
