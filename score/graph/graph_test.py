"""The runner reruns only what a change reaches, blocks on unknown, waits for the owner's accept, and keeps every
finish record. A toy table of two stages, two places, in a store of its own.

Run: .venv/bin/python score/graph/graph_test.py
"""
import json
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from score import checks, contracts, graph  # noqa: E402
from score.graph import _code  # noqa: E402
from score.store import Store, tree_hash  # noqa: E402

MADE = []


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


def accept(store, node, output):
    store.write_accept(node, {"output": output, "at": graph.now()})


def ready_world():
    """Both places made, given evidence and accepted; the world, store and clean outputs."""
    world, store = a_world({"hangar": "a ship in a hall", "station": "a hub"}), Store.in_folder(tempfile.mkdtemp())
    runner = a_runner(world, store)
    runner.run(PLACES)
    outputs = {place: give_evidence(store, runner, place, 10) for place in PLACES}
    runner.run(PLACES)
    for place, output in outputs.items():
        accept(store, f"clean@{place}", output)
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
    assert second["clean@hangar"] == "judged again, output kept: pass"
    assert second["count@hangar"] == f"blocked: clean@hangar's output {output[:12]} is not accepted by the owner"
    assert MADE == ["clean"]
    accept(store, "clean@hangar", output)
    assert a_runner(world, store).run(["hangar"]) == {"clean@hangar": "fresh", "count@hangar": "made: pass"}


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
    assert lines[0].startswith("count@hangar: output") and "pass, not accepted" in lines[0]
    assert lines[1].startswith("  clean@hangar: output") and "pass, accepted" in lines[1]
    assert f"brief {brief[:12]}" in lines[1]


def test_a_paid_stage_does_not_run_without_the_owners_yes():
    paid = graph.Stage("render", "place", make_count, TEXT, (checks.Check("counted", judge_count),),
                       after={"clean": ("toy-text", 1)}, paid=True)
    world, store, _ = ready_world()
    runner = a_runner(world, store, (CLEAN, COUNT, paid))
    found = runner.run(["hangar"])
    assert found["render@hangar"].startswith("blocked: render@hangar is paid and the owner has not said yes")
    ticket = runner.ticket("render@hangar")
    store.write_spend_yes("render@hangar", ticket["key"], {"euros": 0, "at": graph.now()})
    assert a_runner(world, store, (CLEAN, COUNT, paid)).run(["hangar"])["render@hangar"] == "made: pass"


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


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
