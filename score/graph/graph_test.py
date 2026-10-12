"""The runner reruns only what a change reaches, blocks on unknown, accepts by itself only what passed and got no
worse, goes back on the owner's reject, and keeps every finish record. A toy table of two stages, two places, in a
store of its own.

Run: .venv/bin/python score/graph/graph_test.py
"""
import dataclasses
import functools
import json
import os
import pathlib
import shutil
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from score import checks, contracts, graph, review  # noqa: E402
from score.adapters import compute  # noqa: E402
from score.graph import _code  # noqa: E402
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


def test_a_failed_gate_blocks_what_follows():
    world, store = a_world({"hangar": "a ship in a very long hall"}), Store.in_folder(tempfile.mkdtemp())
    runner = a_runner(world, store)
    runner.run(["hangar"])
    give_evidence(store, runner, "hangar", 2)
    found = a_runner(world, store).run(["hangar"])
    assert found["clean@hangar"] == "judged again, output kept: fail"
    assert found["count@hangar"] == "blocked: clean@hangar answered fail: words: 7 words, limit 2"


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


def test_seeds_differ_by_stage_and_place_and_hold_for_the_same_ones():
    assert graph.node_seed(7, "clean", "hangar") == graph.node_seed(7, "clean", "hangar")
    assert len({graph.node_seed(7, "clean", "hangar"), graph.node_seed(7, "clean", "station"),
                graph.node_seed(7, "count", "hangar"), graph.node_seed(8, "clean", "hangar")}) == 4


def test_the_code_version_follows_imports_into_functions_and_sys_path_folders():
    sys.path.insert(0, str(_code.REPO / "tools/usd"))
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
            sys.modules.pop("top_of_order", None)
            import top_of_order
            found.append(_code.source_files([top_of_order.work]))
            del sys.path[1:3]
        assert found[0] == found[1] and len(found[0]) == 3, found
    finally:
        sys.path[:] = saved
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


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
