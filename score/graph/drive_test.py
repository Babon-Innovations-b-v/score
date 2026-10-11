"""The runner drives every line to its end with no agent in the loop: it gathers a gate's missing evidence itself,
starts each node the moment the nodes it reads stand accepted, and a node that fails, errors or is blocked stops its
own line only, with a plain fault report. A toy table of two stages, two places, in a store of its own.

Fault (the owner, 2026-10-11): agents walked every job through its steps by hand, starting each cloud step, polling
it with sleep loops and starting the next, each holding hundreds of thousands of tokens of context.

Run: .venv/bin/python score/graph/drive_test.py
"""
import json
import os
import pathlib
import sys
import tempfile
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from score import checks, contracts, graph  # noqa: E402
from score.adapters import compute  # noqa: E402
from score.store import Store  # noqa: E402

PLACES = ("hangar", "station")


def make_clean(inputs, out, seed, params):
    print("cleaning", inputs["brief"])
    if "explode" in inputs["brief"].read_text():
        raise RuntimeError("the cleaner fell over")
    (out / "clean.txt").write_text(inputs["brief"].read_text().upper())


def gather_limit(output, inputs, folder):
    with (data_of(inputs) / "gathered.txt").open("a") as gathered:  # each node runs in a process of its own
        gathered.write(f"{output.name} {os.environ.get(compute.TICKET)}\n")
    path = folder / "limit.json"
    path.write_text(json.dumps({"limit": 5}))
    return path


def judge_words(output, inputs, evidence):
    words = len((output / "clean.txt").read_text().split())
    limit = json.loads(evidence.read_text())["limit"]
    return checks.Verdict("words", checks.PASS if words <= limit else checks.FAIL, f"{words} words, limit {limit}",
                          {"words": words}, {"words": "lower"}, (f"{words - limit} words too many",) if words > limit
                          else ())


def judge_shout(output, inputs, evidence):
    shouted = "!" in (output / "clean.txt").read_text()
    return checks.Verdict("shout", checks.FAIL if shouted else checks.PASS, "shouts" if shouted else "no shouting")


def make_count(inputs, out, seed, params):
    (out / "count.txt").write_text(str(len((inputs["clean"] / "clean.txt").read_text())))


def judge_count(output, inputs, evidence):
    return checks.Verdict("counted", checks.PASS, "a count was written")


def text_faults(folder):
    return [] if any(folder.glob("*.txt")) else ["no text file"]


TEXT = contracts.Contract("toy-text", 1, text_faults)
WORDS = checks.Check("words", judge_words, evidence="a word limit")
COUNT = graph.Stage("count", "place", make_count, TEXT, (checks.Check("counted", judge_count),),
                    after={"clean": ("toy-text", 1)})


def a_runner(briefs, euros=None):
    data = pathlib.Path(tempfile.mkdtemp())
    for place, brief in briefs.items():
        (data / place).mkdir()
        (data / place / "brief.txt").write_text(brief)
    clean = graph.Stage("clean", "place", make_clean, TEXT, (WORDS, checks.Check("shout", judge_shout)),
                        files={"brief": "{data}/{place}/brief.txt"}, gatherers={"words": (gather_limit, euros)})
    return graph.Runner((clean, COUNT), graph.World("toy", 7, {"data": data}), Store.in_folder(tempfile.mkdtemp()),
                        model_record=lambda kind: {"kind": kind})


def data_of(inputs):
    return inputs["brief"].parents[1]


def gathered(runner):
    """Each gather's (output, spend ticket), as the nodes' processes wrote them."""
    path = runner.world.roots["data"] / "gathered.txt"
    return [tuple(line.split(" ", 1)) for line in path.read_text().splitlines()] if path.exists() else []


def quiet(line):
    pass


def report_of(runner, node):
    return runner.store.cache.parent / "faults" / f"{node}.txt"


def test_a_line_runs_to_its_end_its_evidence_gathered_by_the_runner():
    runner = a_runner({"hangar": "a ship", "station": "a hub"})
    found = runner.drive(PLACES, say=quiet)
    assert found["clean@hangar"] == ("made: unknown; gathered words: judged again, output kept: pass, accepted "
                                     "automatically"), found
    assert found["count@hangar"] == found["count@station"] == "made: pass, accepted automatically", found
    assert len(gathered(runner)) == 2
    assert all(state == "done" for state, _ in runner.lines(PLACES).values()), runner.lines(PLACES)
    assert not (runner.store.cache.parent / "faults").exists()
    assert set(runner.drive(PLACES, say=quiet).values()) == {"fresh"} and len(gathered(runner)) == 2


def test_a_failing_gate_stops_its_own_line_only_with_a_fault_report():
    runner = a_runner({"hangar": "a ship in a very long dark hall", "station": "a hub"})
    found = runner.drive(PLACES, say=quiet)
    assert found["count@hangar"] == "not run: its line stopped at clean@hangar", found
    assert found["count@station"] == "made: pass, accepted automatically", found
    report = report_of(runner, "clean@hangar").read_text()
    assert "why its line stopped: clean@hangar answered fail: words: 8 words, limit 5" in report, report
    assert '  words: fail: 8 words, limit 5\n    measures: {"words": 8}\n    - 3 words too many' in report, report
    assert "cleaning" in report and "python -m score run toy --place hangar" in report, report
    lines = runner.lines(PLACES)
    assert lines["hangar"][0] == f"stopped at clean@hangar: fault report {report_of(runner, 'clean@hangar')}", lines
    assert lines["station"][0] == "done", lines

    (runner.world.roots["data"] / "hangar" / "brief.txt").write_text("a ship")  # put right: the line goes on
    found = runner.drive(PLACES, say=quiet)
    assert found["count@hangar"] == "made: pass, accepted automatically", found
    assert not report_of(runner, "clean@hangar").exists()


def test_nothing_is_gathered_for_an_output_another_gate_fails():
    runner = a_runner({"hangar": "a ship!"})
    found = runner.drive(["hangar"], say=quiet)
    assert found["clean@hangar"].startswith("made: fail; fault report"), found
    assert gathered(runner) == []
    assert "shout: fail: shouts" in report_of(runner, "clean@hangar").read_text()


def test_an_error_stops_its_line_with_its_traceback_in_the_report():
    runner = a_runner({"hangar": "explode", "station": "a hub"})
    found = runner.drive(PLACES, say=quiet)
    assert found["clean@hangar"].startswith("error: RuntimeError: the cleaner fell over; fault report"), found
    assert found["count@hangar"] == "not run: its line stopped at clean@hangar"
    assert found["count@station"] == "made: pass, accepted automatically", found
    report = report_of(runner, "clean@hangar").read_text()
    assert "Traceback" in report and "the cleaner fell over" in report, report


def test_a_missing_input_stops_its_line_with_a_fault_report():
    runner = a_runner({"station": "a hub"})
    found = runner.drive(PLACES, say=quiet)
    assert found["clean@hangar"].startswith("blocked: clean@hangar: its input brief is missing"), found
    assert "its input brief is missing" in report_of(runner, "clean@hangar").read_text()
    assert found["count@station"] == "made: pass, accepted automatically", found


def test_a_paid_gather_runs_inside_the_runners_clearance():
    books = compute.ledger()
    books.entries = lambda: []
    runner = a_runner({"hangar": "a ship"}, euros=0.2)
    assert runner.drive(["hangar"], say=quiet)["count@hangar"] == "made: pass, accepted automatically"
    key = runner.key(runner.stages["clean"], "hangar")["key"]
    assert [ticket for _, ticket in gathered(runner)] == [f"clean@hangar {key}"]
    assert runner.store.clearances("clean@hangar", key)[0]["euros"] == 0.2


# --- lines side by side ----------------------------------------------------------------------------------------------

MEETING_SECONDS = 20


def meeting(data, me, others):
    """A make that says it started, then waits until every other named make started too: done one at a time, the
    first waits alone and fails."""
    def make(inputs, out, seed, params):
        (data / f"{me}.started").touch()
        deadline = time.monotonic() + MEETING_SECONDS
        while not all((data / f"{other}.started").exists() for other in others):
            if time.monotonic() > deadline:
                raise RuntimeError(f"{me} waited alone: {', '.join(others)} never started beside it")
            time.sleep(0.05)
        (out / "met.txt").write_text(me)
    return make


def meet_the_other_places(data):
    """A place's make that meets every other place's (its place is its declared input's folder name)."""
    def make(inputs, out, seed, params):
        place = inputs["place"].name
        meeting(data, place, [other for other in PLACES if other != place])(inputs, out, seed, params)
    return make


def made_once(data):
    def make(inputs, out, seed, params):
        with (data / "ground-made.txt").open("a") as made:
            made.write("made\n")
        (out / "ground.txt").write_text("ground")
    return make


def judge_met(output, inputs, evidence):
    return checks.Verdict("met", checks.PASS, "it ran")


MET = (checks.Check("met", judge_met),)


def a_world_of(places):
    data = pathlib.Path(tempfile.mkdtemp())
    for place in places:
        (data / place).mkdir()
    return data, graph.World("toy", 7, {"data": data})


def test_lines_run_side_by_side_and_one_line_waiting_holds_up_no_other():
    """Fault (the owner, 2026-10-11: nothing waits for the slowest): the drive ran one node at a time, so while one
    place waited on the cloud every other place waited too."""
    data, world = a_world_of(PLACES)
    meet = graph.Stage("meet", "place", meet_the_other_places(data), TEXT, MET, files={"place": "{data}/{place}"})
    runner = graph.Runner((meet,), world, Store.in_folder(tempfile.mkdtemp()), model_record=lambda kind: {})
    started = time.monotonic()
    found = runner.drive(PLACES, say=quiet)
    assert set(found.values()) == {"made: pass, accepted automatically"}, found
    assert time.monotonic() - started < MEETING_SECONDS


def test_nodes_of_one_line_that_read_nothing_of_each_other_run_side_by_side():
    data, world = a_world_of(["hangar"])
    first = graph.Stage("first", "place", meeting(data, "first", ["second"]), TEXT, MET)
    second = graph.Stage("second", "place", meeting(data, "second", ["first"]), TEXT, MET)
    runner = graph.Runner((first, second), world, Store.in_folder(tempfile.mkdtemp()), model_record=lambda kind: {})
    found = runner.drive(["hangar"], say=quiet)
    assert set(found.values()) == {"made: pass, accepted automatically"}, found


def test_a_world_node_every_line_reads_is_made_once_and_each_line_waits_on_it_alone():
    data, world = a_world_of(PLACES)
    ground = graph.Stage("ground", "world", made_once(data), TEXT, MET)
    build = graph.Stage("build", "place", make_count_of_ground, TEXT, MET, after={"ground": ("toy-text", 1)})
    runner = graph.Runner((ground, build), world, Store.in_folder(tempfile.mkdtemp()), model_record=lambda kind: {})
    found = runner.drive(PLACES, say=quiet)
    assert set(found.values()) == {"made: pass, accepted automatically"}, found
    assert list(found) == ["ground", "build@hangar", "build@station"], found
    assert (data / "ground-made.txt").read_text() == "made\n"


def test_a_places_own_lines_run_only_the_world_nodes_they_read():
    data, world = a_world_of(PLACES)
    ground = graph.Stage("ground", "world", made_once(data), TEXT, MET)
    sky = graph.Stage("sky", "world", meeting(data, "sky", ["never"]), TEXT, MET)  # no place reads it
    build = graph.Stage("build", "place", make_count_of_ground, TEXT, MET, after={"ground": ("toy-text", 1)})
    runner = graph.Runner((ground, sky, build), world, Store.in_folder(tempfile.mkdtemp()),
                          model_record=lambda kind: {})
    found = runner.drive(["hangar"], say=quiet, whole=False)
    assert found == {"ground": "made: pass, accepted automatically",
                     "build@hangar": "made: pass, accepted automatically"}, found
    assert set(runner.lines(["hangar"], whole=False)) == {"world", "hangar"}
    assert list(runner.lines(["hangar"], whole=False)["world"][1]) == ["ground"]


def test_a_line_run_for_one_stage_runs_it_and_what_it_reads_alone():
    data, world = a_world_of(PLACES)
    ground = graph.Stage("ground", "world", made_once(data), TEXT, MET)
    build = graph.Stage("build", "place", make_count_of_ground, TEXT, MET, after={"ground": ("toy-text", 1)})
    other = graph.Stage("other", "place", meeting(data, "other", ["never"]), TEXT, MET)  # a row the run leaves alone
    runner = graph.Runner((ground, build, other), world, Store.in_folder(tempfile.mkdtemp()),
                          model_record=lambda kind: {})
    found = runner.drive(["hangar"], say=quiet, whole=False, only=["build"])
    assert set(found) == {"ground", "build@hangar"}, found
    assert set(runner.lines(["hangar"], whole=False, only=["build"])["hangar"][1]) == {"build@hangar"}


def make_count_of_ground(inputs, out, seed, params):
    (out / "built.txt").write_text((inputs["ground"] / "ground.txt").read_text())


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
