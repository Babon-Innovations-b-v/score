"""The runner (score/graph) makes each node's key once, only from inputs that passed and stand accepted, and a node that
does not end accepted stops only the nodes that read it; around it, a run claims its store and its frozen code,
says what it would buy, ends with one line and stops everything it started. Toy stage tables in stores, homes and
git repositories of their own; every answer is worked out by hand from the toy data (the words in a brief, the nodes
a table reads), never by the code under test.

Each test's docstring names a break in the code (`Break: <file>: '<old>' -> '<new>'`, one exact replacement) that
turns it red; each was applied once and seen red, then put back.

Tests of `score/__main__.py`'s run machinery (detach, the exit line, gauges, the pool's timing, stop handling) sit
here because they drive the runner and graph/stopped.py, graph/runs.py and graph/frozen.py through it.

Run: PROPS_HOME=$(mktemp -d) .venv/bin/python -m pytest -q score/graph/test_a_key_is_made_once_from_accepted_inputs.py
"""
import argparse
import contextlib
import dataclasses
import datetime
import functools
import importlib
import io
import json
import os
import pathlib
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import types
import urllib.error

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from score import checks, contracts, graph, review  # noqa: E402
from score.adapters import compute  # noqa: E402

compute.cloud_bill = lambda: 0.0  # no cloud: the provider's bill is never read here
compute.ledger().open_books_for_tests(tempfile.mkdtemp())  # this month's books known: paid paths open
from score.graph import _code, chain, frozen, rebuy, runs, stopped  # noqa: E402
from score.store import Store, partial_of, tree_hash  # noqa: E402

graph.AVAILABLE = lambda: 2**50  # toy nodes take no memory; the memory tests fake their own readings
REPO = pathlib.Path(__file__).resolve().parents[2]
PLACES = ("hangar", "station")
READS = ("toy-text", 1)


def quiet(line):
    pass


@pytest.fixture(autouse=True)
def nodes_print_to_their_file_descriptors(monkeypatch):
    """A node's process prints and writes tracebacks on file descriptors 1 and 2, as in a run, where its log takes
    them over (graph.logged); under pytest its streams would be pytest's own and the log would stay empty."""
    node_process = graph.Runner.node_process

    def on_descriptors(self, *arguments):
        sys.stdout, sys.stderr = sys.__stdout__, sys.__stderr__
        node_process(self, *arguments)
    monkeypatch.setattr(graph.Runner, "node_process", on_descriptors)


# --- a toy table: clean (a place's brief upper-cased, gated on a word limit given as evidence), count after it -------

def make_clean(inputs, out, seed, params):
    print("cleaning", inputs["brief"])
    text = inputs["brief"].read_text()
    if "explode" in text:
        raise RuntimeError("the cleaner fell over")
    if "quit" in text:
        raise SystemExit("the cleaner quit: no such material")
    (out / "clean.txt").write_text(text.upper())


def judge_words(output, inputs, evidence):
    words = len((output / "clean.txt").read_text().split())
    limit = json.loads(evidence.read_text())["limit"]
    return checks.Verdict("words", checks.PASS if words <= limit else checks.FAIL, f"{words} words, limit {limit}",
                          {"words": words}, {"words": "lower"},
                          (f"{words - limit} words too many",) if words > limit else ())


def judge_shout(output, inputs, evidence):
    shouted = "!" in (output / "clean.txt").read_text()
    return checks.Verdict("shout", checks.FAIL if shouted else checks.PASS, "shouts" if shouted else "no shouting")


def make_count(inputs, out, seed, params):
    (out / "count.txt").write_text(str(len((inputs["clean"] / "clean.txt").read_text())))


def judge_passes(output, inputs, evidence):
    return checks.Verdict("counted", checks.PASS, "written")


def text_faults(folder):
    return [] if any(folder.glob("*.txt")) else ["no text file"]


TEXT = contracts.Contract("toy-text", 1, text_faults)
WORDS = checks.Check("words", judge_words, evidence="a word limit")
PASSES = (checks.Check("counted", judge_passes),)
CLEAN = graph.Stage("clean", "place", make_clean, TEXT, (WORDS,), files={"brief": "{data}/{place}/brief.txt"})
COUNT = graph.Stage("count", "place", make_count, TEXT, PASSES, after={"clean": READS})


def a_world(briefs):
    data = pathlib.Path(tempfile.mkdtemp())
    for place, text in briefs.items():
        (data / place).mkdir()
        if text is not None:
            (data / place / "brief.txt").write_text(text)
    return graph.Environment("toy", 7, {"data": data})


def a_store():
    return Store.in_folder(tempfile.mkdtemp())


def a_runner(world, store, stages=(CLEAN, COUNT)):
    return graph.Runner(stages, world, store, model_record=lambda kind: {"kind": kind})


def brief(world, place, text):
    (world.roots["data"] / place / "brief.txt").write_text(text)


def give_evidence(store, runner, place, limit):
    """A word limit as clean@place's evidence; its output."""
    output = store.record(f"clean@{place}", runner.key(CLEAN, place)["key"])["output"]
    path = pathlib.Path(tempfile.mkdtemp()) / "limit.json"
    path.write_text(json.dumps({"limit": limit}))
    store.put_evidence("words", output, path)
    return output


def ready_world():
    """Both places made, given a limit of 10 words and accepted; the world, store and clean outputs."""
    world, store = a_world({"hangar": "a ship in a hall", "station": "a hub"}), a_store()
    runner = a_runner(world, store)
    runner.run(PLACES)
    outputs = {place: give_evidence(store, runner, place, 10) for place in PLACES}
    runner.run(PLACES)
    return world, store, outputs


def accepted_text(store, node, name):
    return (store.checkout(store.accepted(node)) / name).read_text()


MADE = []


def make_logged_clean(inputs, out, seed, params):
    MADE.append("clean")
    make_clean(inputs, out, seed, params)


def make_logged_count(inputs, out, seed, params):
    MADE.append("count")
    make_count(inputs, out, seed, params)


LOGGED = (dataclasses.replace(CLEAN, make=make_logged_clean), dataclasses.replace(COUNT, make=make_logged_count))


# --- keys: made once, judged again on new evidence, made again only where a change reaches ----------------------------

def test_a_key_is_made_once_and_a_change_remakes_only_what_it_reaches():
    """Nothing changed makes nothing; a brief changed remakes its clean alone (the station's line stays fresh, the
    accepted output stays until the new one passes); a brief that cleans to the same text makes nothing after it.
    Break: score/graph/__init__.py: '"files": self.file_keys(stage, place),' -> '"files": {},'"""
    world, store = a_world({"hangar": "a ship in a hall", "station": "a hub"}), a_store()
    runner = a_runner(world, store, LOGGED)
    runner.run(PLACES)
    outputs = {place: give_evidence(store, runner, place, 10) for place in PLACES}
    runner.run(PLACES)
    MADE.clear()
    assert set(a_runner(world, store, LOGGED).run(PLACES).values()) == {"fresh"} and MADE == []
    brief(world, "hangar", "a ship in a dark hall")
    runner = a_runner(world, store, LOGGED)
    assert runner.status(PLACES)["clean@hangar"] == "to run: brief changed"
    found = runner.run(PLACES)
    assert found["clean@hangar"] == "made: unknown", found  # its new output has no word limit yet
    assert found["count@hangar"].startswith("blocked: clean@hangar answered unknown: words: no evidence"), found
    assert found["clean@station"] == found["count@station"] == "fresh" and MADE == ["clean"]
    assert store.accepted("clean@hangar") == outputs["hangar"]
    MADE.clear()
    brief(world, "station", "A HUB")  # the same text once cleaned
    found = a_runner(world, store, LOGGED).run(PLACES)
    assert found["clean@station"] == "made: pass" and found["count@station"] == "fresh" and MADE == ["clean"]
    assert len(store.records("clean@station")) == 2  # both finish records kept


def test_new_evidence_judges_an_output_again_without_remaking_it():
    """Break: score/graph/__init__.py: '(self.store.evidence_hash(check.name, output) or "missing") if check.evidence else "none"' -> '"none"'"""
    world, store = a_world({"hangar": "a ship in a hall"}), a_store()
    MADE.clear()
    a_runner(world, store, LOGGED).run(["hangar"])
    output = give_evidence(store, a_runner(world, store, LOGGED), "hangar", 10)
    found = a_runner(world, store, LOGGED).run(["hangar"])
    assert found == {"clean@hangar": "judged again, output kept: pass, accepted automatically",
                     "count@hangar": "made: pass, accepted automatically"}, found
    assert MADE == ["clean", "count"]
    assert store.accepts("clean@hangar")[-1]["by"] == "runner" and store.accepted("clean@hangar") == output


def test_seeds_differ_by_environment_stage_and_place_and_hold_for_the_same_ones():
    """Break: score/graph/__init__.py: 'text_hash(f"{world_seed}/{stage}/{place}")' -> 'text_hash(f"{world_seed}/{stage}")'"""
    assert graph.node_seed(7, "clean", "hangar") == graph.node_seed(7, "clean", "hangar")
    assert len({graph.node_seed(7, "clean", "hangar"), graph.node_seed(7, "clean", "station"),
                graph.node_seed(7, "count", "hangar"), graph.node_seed(8, "clean", "hangar")}) == 4


def test_the_runner_accepts_by_itself_only_what_passed_and_got_no_worse():
    """Fault (owner, 2026-10-11, 'why are you asking this?'): every output waited for his typed accept. A brief of 6
    words passes a limit of 10 but is worse than the accepted 5: not accepted, what reads it blocked; one of 2 words
    is better: accepted; the owner's reject of it moves the accept back, never taken again by the runner, and leaves
    what read it stale.
    Break: score/graph/__init__.py: 'against = self.rejudged_accepted(stage, place) if judged' -> 'against = {} if judged'"""
    world, store, outputs = ready_world()
    brief(world, "hangar", "a ship in a long dark hall")
    runner = a_runner(world, store)
    runner.run(PLACES)
    worse = give_evidence(store, runner, "hangar", 10)
    found = a_runner(world, store).run(PLACES)
    assert found["clean@hangar"] == "judged again, output kept: pass", found
    assert found["count@hangar"] == (f"blocked: clean@hangar's output {worse[:12]} is not accepted "
                                     f"(accepted: {outputs['hangar'][:12]})"), found
    brief(world, "hangar", "a ship")
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
    assert found["clean@hangar"] == "fresh" and found["count@hangar"].startswith("blocked: clean@hangar's output")


def test_a_bought_batch_accepts_a_passing_worse_output_and_writes_the_drop_down_for_review():
    """Owner, 2026-10-27: inside a bought batch a result that passes every check is accepted though a measure is worse,
    the drop written down for him to review after the batch, never a wait. The brief of 6 words that waits outside a
    batch (above) is accepted in one, its accept quoting his rule with the worse measure in its status.
    Break: score/graph/__init__.py: 'against, self.bought)' -> 'against)'"""
    world, store, outputs = ready_world()
    brief(world, "hangar", "a ship in a long dark hall")
    a_runner(world, store).run(PLACES)
    worse = give_evidence(store, a_runner(world, store), "hangar", 10)
    assert a_runner(world, store).run(PLACES)["clean@hangar"] == "judged again, output kept: pass"
    assert store.accepted("clean@hangar") == outputs["hangar"]
    runner = a_runner(world, store)
    runner.bought = True
    found = runner.run(PLACES)
    assert found["clean@hangar"] == "fresh, accepted automatically" and store.accepted("clean@hangar") == worse, found
    given = store.accepts("clean@hangar")[-1]
    assert given["worse_reason"] == review.IN_BATCH and given["worse"], given
    assert given["status"].startswith("to review after the batch, worse: "), given


def test_a_record_naming_a_stage_the_table_lacks_is_stale_not_a_crash():
    """Fault (2026-10-12): an accepted record named a stage another runner wrote into the store; status crashed.
    Break: score/graph/__init__.py: '                   if before in self.stages}' -> '                   }'"""
    world, store, _ = ready_world()
    lone = a_runner(world, store, (dataclasses.replace(COUNT, after={}),))  # count's records name clean
    assert lone.stale("count@hangar") == ["clean (a stage this table does not hold)"]
    assert lone.status(["hangar"])["count@hangar"].endswith("clean (a stage this table does not hold) moved")


def test_a_failed_gate_blocks_what_follows_and_a_waiver_passes_it_for_its_key_only():
    """7 words against a limit of 2 fail; the owner's waiver for that key lets it through and is shown; a new key
    (8 words) fails again.
    Break: score/graph/__init__.py: 'if checks.blocks(checks.standing(judgement["verdicts"], waived)) and not on_gaps:' -> 'if checks.blocks(checks.standing(judgement["verdicts"], set())) and not on_gaps:'"""
    world, store = a_world({"hangar": "a ship in a very long hall"}), a_store()
    runner = a_runner(world, store)
    runner.run(["hangar"])
    output = give_evidence(store, runner, "hangar", 2)
    found = a_runner(world, store).run(["hangar"])
    assert found == {"clean@hangar": "judged again, output kept: fail",
                     "count@hangar": "blocked: clean@hangar answered fail: words: 7 words, limit 2"}, found
    key = runner.key(CLEAN, "hangar")["key"]
    store.write_waiver("clean@hangar", key, "words", {"by": "owner", "reason": "a long name", "at": graph.now()})
    found = a_runner(world, store).run(["hangar"])
    assert found == {"clean@hangar": "fresh, accepted automatically",
                     "count@hangar": "made: pass, accepted automatically"}, found
    assert store.accepted("clean@hangar") == output
    assert a_runner(world, store).status(["hangar"])["clean@hangar"] == "fail, waived: words, accepted"
    brief(world, "hangar", "a ship in a very long dark hall")
    runner = a_runner(world, store)
    runner.run(["hangar"])
    give_evidence(store, runner, "hangar", 2)
    found = a_runner(world, store).run(["hangar"])
    assert found["count@hangar"] == "blocked: clean@hangar answered fail: words: 8 words, limit 2", found


def make_maybe(inputs, out, seed, params):
    (out / "maybe.txt").write_text("read clean" if "clean" in inputs else "clean not usable: left out")


def test_an_optional_read_is_left_out_while_not_usable_and_taken_once_it_is():
    """Break: score/graph/__init__.py: 'if every or before not in stage.optional or self.usable_now(before, place, wanted)}' -> 'if True}'"""
    maybe = graph.Stage("maybe", "place", make_maybe, TEXT, PASSES, after={"clean": READS}, optional=("clean",))
    world, store = a_world({"hangar": "a ship in a very long hall"}), a_store()
    found = a_runner(world, store, (CLEAN, maybe)).run(["hangar"])  # clean unknown: no word limit yet
    assert found["maybe@hangar"].startswith("made: pass"), found
    give_evidence(store, a_runner(world, store, (CLEAN, maybe)), "hangar", 2)  # 7 words: clean fails
    found = a_runner(world, store, (CLEAN, maybe)).run(["hangar"])
    assert found == {"clean@hangar": "judged again, output kept: fail", "maybe@hangar": "fresh"}, found
    assert accepted_text(store, "maybe@hangar", "maybe.txt") == "clean not usable: left out"
    brief(world, "hangar", "a hall")
    a_runner(world, store, (CLEAN, maybe)).run(["hangar"])
    give_evidence(store, a_runner(world, store, (CLEAN, maybe)), "hangar", 2)
    found = a_runner(world, store, (CLEAN, maybe)).run(["hangar"])
    assert found["maybe@hangar"].startswith("made: pass"), found
    assert accepted_text(store, "maybe@hangar", "maybe.txt") == "read clean"


def make_tally(inputs, out, seed, params):
    (out / "tally.txt").write_text("read clean" if "clean" in inputs else "read without clean")


def test_a_place_stage_that_does_not_apply_has_no_node_and_its_readers_read_without_it():
    """Break: score/graph/__init__.py: '                if place is None or stage.applies is None or stage.applies(place):' -> '                if True:'"""
    world, store = a_world({"hangar": "a ship in a hall", "station": "a hub"}), a_store()
    only_hangar = dataclasses.replace(CLEAN, applies=lambda place: place == "hangar")
    tally = graph.Stage("tally", "place", make_tally, TEXT, PASSES, after={"clean": READS})
    assert list(a_runner(world, store, (only_hangar,)).status(PLACES)) == ["clean@hangar"]
    runner = a_runner(world, store, (only_hangar, tally))
    first = runner.run(PLACES)
    assert first["tally@station"] == "made: pass, accepted automatically", first
    assert first["tally@hangar"].startswith("blocked: clean@hangar answered unknown"), first
    assert runner.earlier(tally, "station") == [] and runner.earlier(tally, "hangar") == ["clean@hangar"]
    assert accepted_text(store, "tally@station", "tally.txt") == "read without clean"


def make_while_the_checkout_moves(inputs, out, seed, params):
    """Another agent's pull writing a file outside the node's key, then (`brief` in params) its own brief."""
    (inputs["brief"].parent / "notes.txt").write_text("pulled in mid-run")
    if params.get("brief"):
        inputs["brief"].write_text("pulled in mid-run")
    (out / "clean.txt").write_text("made")


def test_a_make_is_dropped_only_when_an_input_in_its_key_moved_under_it():
    """#45: earth-kit@airlock's 14 paid bake jobs were thrown away when the checkout moved under its run.
    Break: score/graph/__init__.py: 'if self.file_keys(stage, place) != keyed["files"]:' -> 'if False:'"""
    files = {"brief": "{data}/{place}/brief.txt"}
    world = a_world({"hangar": "a ship"})
    elsewhere = graph.Stage("clean", "place", make_while_the_checkout_moves, TEXT, PASSES, files=files)
    assert a_runner(world, a_store(), (elsewhere,)).run(["hangar"])["clean@hangar"].startswith("made: pass")
    own = dataclasses.replace(elsewhere, params={"brief": True})
    store = a_store()
    with pytest.raises(RuntimeError, match="an input changed while it ran"):
        a_runner(world, store, (own,)).run(["hangar"])
    assert store.records("clean@hangar") == []


def test_why_walks_a_node_back_to_its_environment_file():
    """Break: score/graph/__init__.py: '            lines += self.why(node_name(*before), depth + 1)' -> '            pass'"""
    world, store, _ = ready_world()
    lines = a_runner(world, store).why("count@hangar")
    assert lines[0].startswith("count@hangar: output") and "pass, accepted" in lines[0]
    assert lines[1].startswith("  clean@hangar: output") and "pass, accepted" in lines[1]
    assert f"brief {tree_hash(world.roots['data'] / 'hangar' / 'brief.txt')[:12]}" in lines[1]


TICKETS = []


def make_paid(inputs, out, seed, params):
    TICKETS.append(os.environ.get(compute.TICKET))
    make_count(inputs, out, seed, params)


def test_a_paid_stage_runs_inside_the_runners_clearance_and_one_with_no_estimate_is_refused(monkeypatch):
    """Break: score/graph/__init__.py: '        if not stage.paid:\n            return contextlib.nullcontext()' -> '        if True:\n            return contextlib.nullcontext()'"""
    world, store, _ = ready_world()
    monkeypatch.setattr(compute.ledger(), "entries", lambda: [])
    TICKETS.clear()
    unpriced = graph.Stage("render", "place", make_paid, TEXT, PASSES, after={"clean": READS}, paid=True)
    found = a_runner(world, store, (CLEAN, COUNT, unpriced)).run(["hangar"])
    assert "needs its estimate" in found["render@hangar"] and TICKETS == [], found
    paid = dataclasses.replace(unpriced, euros=0.5)
    runner = a_runner(world, store, (CLEAN, COUNT, paid))
    assert runner.run(["hangar"])["render@hangar"] == "made: pass, accepted automatically"
    key = runner.ticket("render@hangar")["key"]
    assert TICKETS == [f"render@hangar {key}"] and store.spend_yes("render@hangar", key) is None


def make_nothing_written(inputs, out, seed, params):
    (out / "notes.md").write_text("no text file")


def test_every_output_carries_its_contract_and_a_reader_takes_only_the_version_it_was_written_for():
    """Fault (review of step 0, 2026-10-11): no output carried a schema or version, and nothing checked one.
    Break: score/graph/__init__.py: '        contracts.stamp(stage.contract, out)\n' -> '\n'"""
    world, store, outputs = ready_world()
    stamp = json.loads((store.checkout(outputs["hangar"]) / contracts.STAMP).read_text())
    assert stamp == {"schema": "toy-text", "version": 1, "units": {}}
    assert store.records("clean@hangar")[-1]["contract"] == stamp
    newer = dataclasses.replace(COUNT, after={"clean": ("toy-text", 2)})
    found = a_runner(world, store, (CLEAN, newer)).run(["hangar"])
    assert found["count@hangar"] == "blocked: clean@hangar's output is toy-text v1; expected toy-text v2", found
    off = graph.Stage("clean", "place", make_nothing_written, TEXT, files={"brief": "{data}/{place}/brief.txt"})
    fresh = a_store()
    found = a_runner(world, fresh, (off,)).run(["hangar"])
    assert found["clean@hangar"] == "broken: off its contract toy-text v1: no text file", found
    assert fresh.records("clean@hangar") == []
    with pytest.raises(TypeError, match="contract"):
        graph.Stage("clean", "place", make_clean, None)


def place_briefs(place):
    """The hangar reads a second file only it has."""
    return {"brief": "{data}/{place}/brief.txt", **({"notes": "{data}/hangar/notes.txt"} if place == "hangar" else {})}


def test_a_missing_input_blocks_and_a_place_is_keyed_on_its_own_files():
    """Break: score/graph/__init__.py: '            if not path.exists():\n                raise Blocked(f"{node_name(stage, place)}: its input' -> '            if False:\n                raise Blocked(f"{node_name(stage, place)}: its input'"""
    assert a_runner(a_world({}), a_store()).run(["hangar"])["clean@hangar"].startswith(
        "blocked: clean@hangar: its input brief is missing")
    world, store = a_world({"hangar": "a ship in a hall", "station": "a hub"}), a_store()
    stage = dataclasses.replace(CLEAN, files=place_briefs)
    runner = a_runner(world, store, (stage,))
    assert runner.run(PLACES)["clean@hangar"].startswith("blocked: clean@hangar: its input notes")
    (world.roots["data"] / "hangar" / "notes.txt").write_text("notes")
    assert set(runner.key(stage, "hangar")["files"]) == {"brief", "notes"}
    assert set(runner.key(stage, "station")["files"]) == {"brief"}


def make_with_code(inputs, out, seed, params):
    """A make importing a module from its declared code folder, in its own process and in a child's."""
    sys.path.insert(0, str(inputs["code"]))
    try:
        import made_here
    finally:
        sys.path.remove(str(inputs["code"]))
        sys.modules.pop("made_here", None)
    subprocess.run([sys.executable, "-c", "import made_here"], cwd=inputs["code"], check=True)
    (out / "made.txt").write_text(made_here.WORD)


def test_bytecode_is_neither_written_into_nor_keyed_from_a_declared_folder():
    """#67: each checkout writes its own __pycache__, and keys hashed it.
    Break: score/graph/__init__.py: 'for name, found in tree_files(path).items() if not bytecode(name)})' -> 'for name, found in tree_files(path).items()})'"""
    world = a_world({"hangar": "a ship in a hall"})
    code = world.roots["data"] / "code"
    code.mkdir()
    (code / "made_here.py").write_text("WORD = 'made'\n")
    before = tree_hash(code)
    stage = graph.Stage("coded", "place", make_with_code, TEXT, PASSES, files={"code": "{data}/code"})
    assert a_runner(world, a_store(), (stage,)).run(["hangar"])["coded@hangar"].startswith("made: pass")
    assert tree_hash(code) == before and not (code / "__pycache__").exists()
    folder_read = dataclasses.replace(CLEAN, files={"place": "{data}/{place}"})
    runner = a_runner(world, a_store(), (folder_read,))
    keys = runner.file_keys(folder_read, "hangar")
    folder = world.roots["data"] / "hangar"
    (folder / "__pycache__").mkdir()
    (folder / "__pycache__" / "brief.cpython-312.pyc").write_bytes(b"bytecode")
    (folder / "stray.pyc").write_bytes(b"bytecode")
    assert runner.file_keys(folder_read, "hangar") == keys
    (folder / "notes.txt").write_text("a source file")  # a source in the folder still moves it
    assert runner.file_keys(folder_read, "hangar") != keys


# --- the code version: every repository file a stage's functions import, however the path is ordered ----------------

@contextlib.contextmanager
def modules_of_its_own(prefix, files):
    """{relative path: text} written under a folder of the repository's own (the code version follows repository files
    only), each top folder put first on the path while the block runs; yields the folder."""
    root = pathlib.Path(tempfile.mkdtemp(prefix=prefix, dir=REPO / "score/graph"))
    saved = list(sys.path)
    for name, text in files.items():
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).write_text(text)
    try:
        yield root
    finally:
        sys.path[:] = saved
        for name in files:
            sys.modules.pop(pathlib.Path(name).stem, None)
        _code.search_folders.cache_clear()
        shutil.rmtree(root)


def test_the_code_version_follows_imports_inside_functions_through_path_folders_and_wrapped_judges():
    """A function importing inside its body a module from another path folder; a judge wrapped elsewhere
    (functools.wraps) is hashed from its own module too (the surface stage's guarded checks); the venv never.
    Break: score/graph/_code.py: 'for node in ast.walk(ast.parse(source, str(path))):' -> 'for node in ast.parse(source, str(path)).body:'"""
    files = {"start/follow_start.py": "def work():\n    import follow_inner\n    return follow_inner.VALUE\n",
             "inner/follow_inner.py": "import numpy\nVALUE = 1\n",
             "start/follow_judge.py": "def judge(output, inputs, evidence):\n    return None\n"}
    with modules_of_its_own("_code_follow_", files) as root:
        sys.path[:0] = [str(root / "start"), str(root / "inner")]
        _code.search_folders.cache_clear()
        import follow_judge
        import follow_start
        found = {path.relative_to(root).as_posix() for path in _code.source_files([follow_start.work])}
        assert found == {"start/follow_start.py", "inner/follow_inner.py"}, found
        wrapped = functools.wraps(follow_judge.judge)(lambda output, inputs, evidence: None)
        assert "follow_judge.py" in {path.name for path in _code.source_files([wrapped])}


def test_a_file_edited_in_one_process_gives_a_new_code_version():
    """The import walk is cached a process (#49); an import added to a file is followed at the next read.
    Break: score/graph/_code.py: 'if known is None or known[0] != stamp or not all(module.is_file() for module in known[1]):' -> 'if known is None:'"""
    files = {"edited_start.py": "def work():\n    return 1\n", "edited_added.py": "VALUE = 1\n"}
    with modules_of_its_own("_code_edited_", files) as root:
        sys.path.insert(0, str(root))
        _code.search_folders.cache_clear()
        import edited_start
        before = _code.code_version([edited_start.work], lambda path: "same")
        assert before == _code.code_version([edited_start.work], lambda path: "same")
        (root / "edited_start.py").write_text("import edited_added\n\n\ndef work():\n    return 1\n")
        after = _code.code_version([edited_start.work], lambda path: "same")
        assert after != before and any("edited_added.py" in part for part in after), after


SHARED = {"first/top_of_order.py": "import shared_name\n\n\ndef work():\n    return shared_name\n",
          "one/shared_name.py": "VALUE = 1\n", "other/shared_name.py": "VALUE = 2\n"}


def test_the_code_version_holds_whatever_the_paths_order_and_whatever_folder_comes_on_it_later():
    """A name two path folders hold is hashed from both, in either order (a row's key moved between two runs with no
    file changed, 2026-10-11); a folder put on the path after the first code version gives no stage another
    same-named module (stages_test's earlier tests gave effects-layer triage.py, 2026-10-13).
    Break: score/graph/_code.py: '                found.add(path.resolve())' -> '                return {path.resolve()}'"""
    with modules_of_its_own("_code_order_", SHARED) as root:
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
    with modules_of_its_own("_code_later_", {name.replace("other/", "later/"): text
                                            for name, text in SHARED.items()}) as root:
        sys.path[:0] = [str(root / "first"), str(root / "one")]
        _code.search_folders.cache_clear()
        sys.modules.pop("top_of_order", None)
        import top_of_order
        before = _code.source_files([top_of_order.work])
        sys.path.insert(0, str(root / "later"))
        assert _code.source_files([top_of_order.work]) == before and len(before) == 2, before


# --- reads beside: other places' outputs, an environment's, up to a shell and down to child scenes -----------------

def make_show(inputs, out, seed, params):
    """Its own clean text, and every other place's read beside, in order."""
    others = sorted(name for name in inputs if name.startswith("clean@"))
    own = ["clean"] if "clean" in inputs else []
    (out / "show.txt").write_text(" ".join((inputs[name] / "clean.txt").read_text() for name in [*own, *others]))


SHOW = graph.Stage("show", "place", make_show, TEXT, PASSES, after={"clean": READS}, beside={"clean": READS},
                   neighbours=lambda place: [other for other in PLACES if other != place])


def test_a_stage_reads_other_places_beside_versioned_and_waited_on_without_a_cycle():
    """Fault (2026-10-12): a place's references to the places it shows pointed at old seed files. The hangar's show
    reads the station's accepted clean beside its own: "A SHIP IN A HALL A HUB"; the station's brief rewritten the
    same keeps its key, one rewritten otherwise stales it; a stage reading itself beside is refused, a chain read
    beside with no loop stands.
    Break: score/graph/__init__.py: '        if beside:  # only a stage that reads beside' -> '        if False:  # only a stage that reads beside'"""
    world, store, outputs = ready_world()
    runner = a_runner(world, store, (CLEAN, COUNT, SHOW))
    assert runner.earlier(SHOW, "hangar") == ["clean@hangar", "clean@station"]
    assert [graph.node_name(*node) for node in runner.line_nodes(["hangar"], whole=False)] == [
        "clean@hangar", "clean@station", "count@hangar", "show@hangar"]
    found = runner.drive(["hangar"], say=quiet, jobs=1, whole=False)
    assert found["show@hangar"] == "made: pass, accepted automatically", found
    assert accepted_text(store, "show@hangar", "show.txt") == "A SHIP IN A HALL A HUB"
    assert runner.key(SHOW, "hangar")["beside"] == {"clean@station": outputs["station"]}
    brief(world, "station", "a hub")
    assert runner.status(["hangar"])["show@hangar"] == "pass, accepted"
    brief(world, "station", "a ring")
    runner.run(["station"])
    give_evidence(store, runner, "station", 10)
    runner.run(["station"])
    assert runner.status(["hangar"])["show@hangar"] == ("to run: clean@station changed, its accepted output is stale: "
                                                      "clean@station moved")
    with pytest.raises(ValueError, match="cycle"):
        a_runner(world, store, (CLEAN, dataclasses.replace(SHOW, name="loop", beside={"loop": READS})))
    a_runner(world, store, (CLEAN, COUNT, SHOW, dataclasses.replace(SHOW, name="show again", after={"show": READS},
                                                                    beside={"show": READS})))


def test_an_environment_stage_reads_the_places_it_names_beside_where_each_row_applies():
    """#28: the environment's film reads every place film its script shows, a row only where it applies.
    Break: score/graph/__init__.py: 'if place is not None or self.stages[before].applies is None or self.stages[before].applies(other)}' -> '}'"""
    world, store, outputs = ready_world()
    hangar_only = dataclasses.replace(COUNT, name="hangar only", applies=lambda place: place == "hangar")
    whole = graph.Stage("whole", "world", make_show, TEXT, PASSES, beside={"clean": READS, "hangar only": READS},
                        neighbours=lambda place: list(PLACES))
    runner = a_runner(world, store, (CLEAN, COUNT, hangar_only, whole))
    assert runner.earlier(whole, None) == ["clean@hangar", "hangar only@hangar", "clean@station"]
    found = runner.drive(list(PLACES), say=quiet, jobs=1)
    assert found["whole"] == "made: pass, accepted automatically", found
    assert accepted_text(store, "whole", "show.txt") == "A SHIP IN A HALL A HUB"
    assert runner.key(whole, None)["beside"]["clean@station"] == outputs["station"]


def make_outlined(inputs, out, seed, params):
    """Its own clean text, after its shell's split where it has one."""
    shells = [(inputs[name] / "split.txt").read_text() for name in sorted(inputs) if name.startswith("split@")]
    (out / "outlined.txt").write_text(" ".join([*shells, (inputs["clean"] / "clean.txt").read_text()]))


def make_split(inputs, out, seed, params):
    (out / "split.txt").write_text("SPLIT " + (inputs["outlined"] / "outlined.txt").read_text())


def make_tree(inputs, out, seed, params):
    """Its own clean text, then each child scene's tree in brackets."""
    held = [(inputs[name] / "tree.txt").read_text() for name in sorted(inputs) if name.startswith("tree@")]
    (out / "tree.txt").write_text((inputs["clean"] / "clean.txt").read_text() + "".join(f"[{tree}]" for tree in held))


OUTLINED = graph.Stage("outlined", "place", make_outlined, TEXT, PASSES, after={"clean": READS},
                       beside={"split": READS}, upward=True,
                       neighbours=lambda place: ["station"] if place == "hangar" else [])
SPLIT = graph.Stage("split", "place", make_split, TEXT, PASSES, after={"outlined": READS})
HOLDS = {"base": ["hangar"], "hangar": ["station"]}
TREE = graph.Stage("tree", "place", make_tree, TEXT, PASSES, after={"clean": READS}, beside={"tree": READS},
                   downward=True, neighbours=lambda place: HOLDS.get(place, []))


def test_a_loop_through_reads_beside_is_one_scale_up_or_down_only_when_declared():
    """Shapes first (CONTEXT.md): an inside place reads its outside shell's split, which reads the shell's own node of
    that stage; a parent scene's tree reads each child scene's tree, the grandchild's made first. A loop in the table,
    none in the nodes; the same stages not declared upward or downward are refused.
    Break: score/graph/__init__.py: '        return [*stage.after, *(() if stage.upward or stage.downward else stage.beside)]' -> '        return [*stage.after]'"""
    world, store, _ = ready_world()
    runner = a_runner(world, store, (CLEAN, COUNT, OUTLINED, SPLIT))
    assert runner.drive(["hangar"], say=quiet, jobs=1, whole=False)["outlined@hangar"] == (
        "made: pass, accepted automatically")
    assert runner.key(OUTLINED, "hangar")["beside"] == {"split@station": store.accepted("split@station")}
    assert accepted_text(store, "outlined@hangar", "outlined.txt") == "SPLIT A HUB A SHIP IN A HALL"
    with pytest.raises(ValueError, match="cycle"):
        a_runner(world, store, (CLEAN, COUNT, dataclasses.replace(OUTLINED, upward=False), SPLIT))
    world = a_world({"base": "a moon base", "hangar": "a ship in a hall", "station": "a hub"})
    store, scenes = a_store(), ("base", "hangar", "station")
    runner = a_runner(world, store)
    runner.run(scenes)
    for place in scenes:
        give_evidence(store, runner, place, 10)
    runner = a_runner(world, store, (CLEAN, COUNT, TREE))
    assert runner.drive(["base"], say=quiet, jobs=1, whole=False)["tree@base"] == "made: pass, accepted automatically"
    assert runner.key(TREE, "base")["beside"] == {"tree@hangar": store.accepted("tree@hangar")}
    assert accepted_text(store, "tree@base", "tree.txt") == "A MOON BASE[A SHIP IN A HALL[A HUB]]"
    with pytest.raises(ValueError, match="cycle"):
        a_runner(world, store, (CLEAN, COUNT, dataclasses.replace(TREE, downward=False)))


GATHER = graph.Stage("gather", "world", make_show, TEXT, PASSES, beside={"clean": READS},
                     neighbours=lambda place: ["hangar"])


def test_a_run_holds_the_nodes_it_names_and_what_they_read_place_by_place():
    """#26: `--place people --stage <body>` keeps an environment row named with the place, where before it was left
    out; an environment stage not named stays out; one node named by itself is a run of its own.
    Break: score/graph/__init__.py: '                                      if stage.grain == "place" or node_name(stage, place) in named]' -> '                                      if stage.grain == "place"]'"""
    world, store, _ = ready_world()
    runner = a_runner(world, store, (CLEAN, COUNT, GATHER))
    names = {graph.node_name(*node) for node in runner.line_nodes(["hangar"], whole=False, only=["gather"])}
    assert names == {"clean@hangar", "gather"}, names
    names = {graph.node_name(*node) for node in runner.line_nodes(["hangar"], whole=False, only=["count"])}
    assert names == {"clean@hangar", "count@hangar"}, names
    names = {graph.node_name(*node) for node in runner.line_nodes(list(PLACES), whole=False, only=["count@station"])}
    assert names == {"clean@station", "count@station"}, names


# --- an accepted output kept under a moved key: bytecode alone, a no-op proof, a narrower key, words only ----------

def judge_seen(output, inputs, evidence):
    return checks.Verdict("seen", checks.PASS, "it was made")


def make_seen(inputs, out, seed, params):
    (out / "seen.txt").write_text("seen")


SEEN = (checks.Check("seen", judge_seen),)
SOURCES = graph.Stage("seen", "place", make_seen, TEXT, SEEN, files={"code": "{repo}/score/checks"})
NOTED = graph.Stage("noted", "place", make_seen, TEXT, SEEN, files={"notes": "{repo}/CLAUDE.md"})


def git_out(*command):
    return subprocess.run(["git", "-C", str(_code.REPO), *command], capture_output=True, text=True,
                          check=True).stdout.split()


def test_an_output_whose_key_moved_only_by_bytecode_is_kept_and_a_source_change_is_not(monkeypatch):
    """#67: seen@hangar made by a runner that still hashed score/checks' __pycache__, at HEAD (sources as now: kept,
    the proof in its record) and at the first commit (no score/checks then: made again).
    Break: score/graph/__init__.py: '        proved = self.bytecode_proof(stage, place, keyed)\n        if proved is None:' -> '        proved = None\n        if proved is None:'"""
    cache = _code.REPO / "score/checks/__pycache__"
    if not any(cache.glob("*.pyc")):
        import py_compile
        py_compile.compile(str(_code.REPO / "score/checks/__init__.py"))
    world = graph.Environment("toy", 7, {"data": str(tempfile.mkdtemp()), "repo": str(_code.REPO)})
    head, first = git_out("rev-parse", "HEAD")[-1], git_out("rev-list", "--max-parents=0", "HEAD")[-1]
    for commit, kept in ((head, True), (first, False)):
        store = a_store()
        with monkeypatch.context() as patched:
            patched.setattr(graph, "source_hash", tree_hash)
            patched.setattr(_code, "git_commit", lambda: {"commit": commit, "uncommitted": False})
            assert a_runner(world, store, (SOURCES,)).run(["hangar"])["seen@hangar"].endswith("accepted automatically")
        runner = a_runner(world, store, (SOURCES,))
        keyed = runner.key(SOURCES, "hangar")
        assert store.record("seen@hangar", keyed["key"]) is None  # the bytecode moved its key
        done = runner.run(["hangar"])["seen@hangar"]
        assert done == ("fresh" if kept else "made: pass"), (commit, done)
        if kept:
            carried = store.record("seen@hangar", keyed["key"])["carried"]
            assert carried["reason"] == graph.BYTECODE_REASON and carried["made by"]["commit"] == head
            assert carried["sources"]["code"]["at its commit"] == keyed["files"]["code"]


def test_an_output_is_kept_over_a_change_only_with_a_proof_naming_every_changed_file(monkeypatch):
    """noted@hangar made at the first commit, when CLAUDE.md read otherwise: made again with no proof or one that
    leaves CLAUDE.md out; kept, the proof in its record, when the proof names it.
    Break: score/graph/__init__.py: 'if any(not str(proof.get("no-ops", {}).get(name, "")).strip() for name in changed):' -> 'if False:'"""
    world = graph.Environment("toy", 7, {"data": str(tempfile.mkdtemp()), "repo": str(_code.REPO)})
    first = git_out("rev-list", "--max-parents=0", "HEAD")[0]
    for no_ops, kept in (({}, False), ({"README.md": "not read"}, False),
                         ({"CLAUDE.md": "only its wording changed"}, True)):
        store = a_store()
        with monkeypatch.context() as patched:
            patched.setattr(graph, "source_hash", lambda path: "the file as it read then")
            patched.setattr(_code, "git_commit", lambda: {"commit": first, "uncommitted": False})
            assert a_runner(world, store, (NOTED,)).run(["hangar"])["noted@hangar"].endswith("automatically")
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
    return STAGE_SOURCE.format(helper=f"narrow_h{case}", other=f"narrow_g{case}")


@contextlib.contextmanager
def a_repo_of_its_own(case):
    """A committed git repository taken as the repository while the block runs: `narrow_a<case>` imports
    `narrow_h<case>` (which imports `narrow_j<case>`) and `narrow_g<case>`; `narrow_b<case>` has a make of its own; a
    FRAMEWORK of none. Yields (its folder, the stage module)."""
    repo = pathlib.Path(tempfile.mkdtemp(prefix="narrow_repo_")).resolve()
    (repo / f"narrow_h{case}.py").write_text(f'import narrow_j{case}\nWORD = "kept " + narrow_j{case}.WORD\n')
    (repo / f"narrow_j{case}.py").write_text('WORD = "joined "\n')
    (repo / f"narrow_g{case}.py").write_text('WORD = "also "\n')
    (repo / f"narrow_a{case}.py").write_text(stage_source(case))
    (repo / f"narrow_b{case}.py").write_text(OTHER_SOURCE)
    (repo / "score" / "graph").mkdir(parents=True)
    (repo / "score" / "graph" / "_code.py").write_text("FRAMEWORK = {REPO / name for name in ()}\n")
    (repo / ".gitignore").write_text("__pycache__/\n")
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


def test_an_output_whose_key_only_got_narrower_or_reworded_is_kept_and_a_changed_read_is_made_again():
    """A stage A importing helper H, made and accepted: H moved into FRAMEWORK moves A's key and the runner keeps A's
    output, no proof file and no make (rebuy counts no buy); A's own file edited, its {seeds} file changed, its make
    wired to another function (B), another Python, H edited, a file read only through H (J) edited or deleted make A
    again. A second narrowing (G moved too) is kept as well, still naming what made it. Nothing moved, A and G
    reworded only (comments, blank lines, layout, docstrings) keep it, the record naming them; a docstring changed in
    a file that reads `__doc__`, or a type hint, makes A again.
    Break: score/graph/__init__.py: '        return (record, reworded) if _code.unchanged(dropped, file_hash) else None' -> '        return (record, reworded)'"""
    for case, change, kept in ((0, None, True), (1, "own file", False), (2, "seeds", False),
                               (3, "make swapped", False), (4, "python", False), (5, "helper edited", False),
                               (6, "read through helper edited", False), (7, "second narrowing", True),
                               (8, "read through helper deleted", False), (9, "words only", True),
                               (10, "read docstring changed", False), (11, "type hint", False)):
        seeds = pathlib.Path(tempfile.mkdtemp())
        (seeds / "hangar.txt").write_text("a seed")
        world = graph.Environment("toy", 7, {"seeds": str(seeds)})
        store = a_store()
        with a_repo_of_its_own(case) as (repo, module):
            stage = graph.Stage("narrow", "place", module.make, TEXT, SEEN, files={"seeds": "{seeds}/{place}.txt"})
            if change == "read docstring changed":
                (repo / f"narrow_g{case}.py").write_text('"""also """\nWORD = __doc__\n')
                subprocess.run(["git", "-C", str(repo), "commit", "-qam", "a usage text"], check=True)
            first = a_runner(world, store, (stage,)).run(["hangar"])["narrow@hangar"]
            assert first == "made: pass, accepted automatically", first
            old = store.records("narrow@hangar")[0]
            if change not in ("words only", "read docstring changed", "type hint"):
                _code.FRAMEWORK.add(repo / f"narrow_h{case}.py")
            edits = {"own file": (f"narrow_a{case}.py", stage_source(case) + "EXTRA = 1\n"),
                     "words only": (f"narrow_a{case}.py", '"""A stage."""\n\n# made here\n' + stage_source(
                         case).replace("    (out", '    """It makes made.txt."""\n    (out')),
                     "read docstring changed": (f"narrow_g{case}.py", '"""other """\nWORD = __doc__\n'),
                     "type hint": (f"narrow_g{case}.py", 'WORD: str = "also "\n'),
                     "helper edited": (f"narrow_h{case}.py", 'WORD = "another word "\n'),
                     "read through helper edited": (f"narrow_j{case}.py", 'WORD = "another word "\n')}
            if change in edits:
                (repo / edits[change][0]).write_text(edits[change][1])
            if change == "words only":
                (repo / f"narrow_g{case}.py").write_text('WORD = (\n    "also "  # a word\n)\n')
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
                assert (rebuy.to_make(runner, stage, "hangar", [], {}) is rebuy.KEPT) == kept, change
                done = runner.run(["hangar"])["narrow@hangar"]
            finally:
                _code.sys = python
            assert done.startswith("fresh" if kept else "made: pass"), (change, done)
            record = store.record("narrow@hangar", keyed["key"])
            made_by = {"commit": old["commit"], "code": old["code"]}
            if change == "words only":
                assert record["output"] == old["output"] and record["carried"] == {
                    "reason": graph.WORDS_REASON, "from key": old["key"], "to key": keyed["key"], "made by": made_by,
                    "words only": [f"narrow_a{case}.py", f"narrow_g{case}.py"]}
            elif kept:
                assert record["output"] == old["output"] and record["code"] == keyed["code"]
                assert record["carried"] == {"reason": graph.NARROWING_REASON, "from key": old["key"],
                                             "to key": keyed["key"], "made by": made_by}
                assert store.judgement("narrow@hangar", keyed["key"], runner.evidence_state(stage, old["output"]))
                if change == "second narrowing":
                    _code.FRAMEWORK.add(repo / f"narrow_g{case}.py")
                    runner = a_runner(world, store, (stage,))
                    again = runner.key(stage, "hangar")
                    assert again["key"] != keyed["key"] and runner.run(["hangar"])["narrow@hangar"].startswith("fresh")
                    assert store.record("narrow@hangar", again["key"])["carried"] == {
                        "reason": graph.NARROWING_REASON, "from key": keyed["key"], "to key": again["key"],
                        "made by": made_by}
            else:
                assert "carried" not in record


# --- reading the store: the prefix's own folder, nothing missed ----------------------------------------------------

def test_the_runners_store_lists_the_same_keys_walking_only_the_prefixs_folder():
    """2026-10-14: the store's whole walk on each call held a run at one core for hours. scoped_keys answers every
    prefix as the whole walk does, its .partial files left out, and a runner puts it on every folder store.
    Break: score/graph/__init__.py: '             if path.is_file() and not path.name.endswith(".partial"))' -> '             if path.is_file())'"""
    root = pathlib.Path(tempfile.mkdtemp())
    for key in ("accepts/clean@hangar/1.json", "accepts/clean@hangar/2.json", "accepts/clean@station/1.json",
                "records/clean@hangar/k.json", "blobs/ab", "top.json", "accepts/clean@hangar/3.json.9.partial"):
        (root / key).parent.mkdir(parents=True, exist_ok=True)
        (root / key).write_text("{}")
    store = graph.score_store.runtime_store.FolderStore(root)
    expected = {"accepts/clean@hangar/": ["accepts/clean@hangar/1.json", "accepts/clean@hangar/2.json"],
                "accepts/clean@": ["accepts/clean@hangar/1.json", "accepts/clean@hangar/2.json",
                                   "accepts/clean@station/1.json"],
                "records/clean@hangar/k": ["records/clean@hangar/k.json"], "rejects/x/": [], "top": ["top.json"],
                "nothing/here/": []}
    for prefix, keys in expected.items():
        assert graph.scoped_keys(store, prefix) == keys == graph.WHOLE_WALK(store, prefix), prefix
    for prefix in ("accepts/", ""):
        assert graph.scoped_keys(store, prefix) == graph.WHOLE_WALK(store, prefix), prefix
    a_runner(a_world({"hangar": "a ship"}), a_store())
    assert graph.score_store.runtime_store.FolderStore.keys is graph.scoped_keys


def test_a_run_names_every_environment_file_it_could_never_make_before_it_starts():
    """The ship run of 2026-10-14 spent EUR 13.58, then stopped on missing seed records. A missing {data} file is
    named (node, input, path); one the run makes (under {home}) is left to its row.
    Break: score/graph/__init__.py: '                if not pattern.startswith(("{data}", "{repo}")):' -> '                if False:'"""
    world = a_world({"hangar": "a ship in a hall"})
    made = graph.Stage("made", "place", make_seen, TEXT, SEEN, files={"take": "{home}/takes/{place}.glb"})
    world = graph.Environment("toy", 7, {**world.roots, "home": str(tempfile.mkdtemp())})
    runner = a_runner(world, a_store(), (CLEAN, made))
    assert runner.missing_inputs([(CLEAN, "station"), (made, "hangar")]) == [
        f"clean@station: brief ({world.roots['data'] / 'station/brief.txt'})"]
    assert runner.missing_inputs([(CLEAN, "hangar")]) == []


STRICT = {"on": False, "old schema": False}  # the toy gate's code before (off) and after (on) it saw a fault


def judge_marks(output, inputs, evidence):
    if STRICT["old schema"] and (output / "clean.txt").read_text().startswith("A "):
        raise KeyError("layers")  # today's gate reading a field the old output never wrote
    marks = (output / "clean.txt").read_text().split().count("X") if STRICT["on"] else 0
    return checks.Verdict("marks", checks.PASS, f"{marks} marks", {"marks": marks}, {"marks": "lower"})


MARKS = graph.Stage("clean", "place", make_clean, TEXT, (checks.Check("marks", judge_marks),),
                    files={"brief": "{data}/{place}/brief.txt"})


def test_the_accepted_output_is_judged_again_by_todays_gates_before_comparing():
    """assembly@lab, 2026-10-15: its accepted output was judged before the triage asked each foot, so the chairs'
    caster read as two new faults. "a x" accepted with 0 marks seen; today's gate sees its 1 mark, so "b x" (1 mark)
    is no worse and accepted, "c x x" (2) is worse and waits. A gate that cannot judge the accepted output again
    compares its stored verdict (0 marks against 1: worse, waits).
    Break: score/graph/__init__.py: 'against = self.rejudged_accepted(stage, place) if judged' -> 'against = None if judged'"""
    world, store = a_world({"hangar": "a x"}), a_store()
    try:
        assert a_runner(world, store, (MARKS,)).run(["hangar"])["clean@hangar"] == "made: pass, accepted automatically"
        STRICT["on"] = True
        brief(world, "hangar", "b x")
        assert a_runner(world, store, (MARKS,)).run(["hangar"])["clean@hangar"] == (
            "made: pass, accepted automatically")
        accepted = store.accepted("clean@hangar")
        brief(world, "hangar", "c x x")
        assert a_runner(world, store, (MARKS,)).run(["hangar"])["clean@hangar"] == "made: pass"
        assert store.accepted("clean@hangar") == accepted
        world, store = a_world({"hangar": "a x"}), a_store()
        STRICT.update({"on": False})
        a_runner(world, store, (MARKS,)).run(["hangar"])
        STRICT.update({"on": True, "old schema": True})
        brief(world, "hangar", "b x")
        assert a_runner(world, store, (MARKS,)).run(["hangar"])["clean@hangar"] == "made: pass"
    finally:
        STRICT.update({"on": False, "old schema": False})


# --- the drive: every line to its end, no agent in the loop; a node that does not stand stops only what reads it ----
# Fault (owner, 2026-10-11): agents walked every job through its steps by hand, polling each cloud step.

def gather_limit(output, inputs, folder):
    """A word limit of 5, written down for the test (each node runs in a process of its own)."""
    with (inputs["brief"].parents[1] / "gathered.txt").open("a") as gathered:
        gathered.write(f"{output.name} {os.environ.get(compute.TICKET)}\n")
    path = folder / "limit.json"
    path.write_text(json.dumps({"limit": 5}))
    return path


def a_driven_runner(briefs, euros=None, more=()):
    """clean (gated on a gathered limit of 5 words and on shouting) and count, with `more` stages after them."""
    clean = graph.Stage("clean", "place", make_clean, TEXT, (WORDS, checks.Check("shout", judge_shout)),
                        files={"brief": "{data}/{place}/brief.txt"}, gatherers={"words": (gather_limit, euros)})
    return a_runner(a_world(briefs), a_store(), (clean, COUNT, *more))


def gathered(runner):
    """Each gather's (output, spend ticket), as the nodes' processes wrote them."""
    path = runner.world.roots["data"] / "gathered.txt"
    return [tuple(line.split(" ", 1)) for line in path.read_text().splitlines()] if path.exists() else []


def report_of(runner, node):
    return runner.store.cache.parent / "faults" / f"{node}.txt"


ACCEPTED = "made: pass, accepted automatically"


def test_a_line_runs_to_its_end_gathering_its_evidence_itself():
    """Break: score/graph/__init__.py: '                wanted = [] if did.startswith(("blocked", "broken")) else self.gatherable(stage, place)' -> '                wanted = []'"""
    runner = a_driven_runner({"hangar": "a ship", "station": "a hub"})
    found = runner.drive(PLACES, say=quiet)
    assert found["clean@hangar"] == ("made: unknown; gathered words: judged again, output kept: pass, accepted "
                                     "automatically"), found
    assert found["count@hangar"] == found["count@station"] == ACCEPTED, found
    assert len(gathered(runner)) == 2
    assert {state for state, _ in runner.lines(PLACES).values()} == {"done"}
    assert not (runner.store.cache.parent / "faults").exists()
    assert set(runner.drive(PLACES, say=quiet).values()) == {"fresh"} and len(gathered(runner)) == 2


def test_a_failing_gate_stops_its_own_line_only_with_a_plain_fault_report_removed_once_put_right():
    """8 words against the gathered 5.
    Break: score/graph/__init__.py: '        if report.exists():\n            report.unlink()\n        return did, True' -> '        return did, True'"""
    runner = a_driven_runner({"hangar": "a ship in a very long dark hall", "station": "a hub"})
    found = runner.drive(PLACES, say=quiet)
    assert found["count@hangar"] == "not run: its line stopped at clean@hangar", found
    assert found["count@station"] == ACCEPTED, found
    report = report_of(runner, "clean@hangar").read_text()
    assert "why its line stopped: clean@hangar answered fail: words: 8 words, limit 5" in report, report
    assert '  words: fail: 8 words, limit 5\n    measures: {"words": 8}\n    - 3 words too many' in report, report
    assert "cleaning" in report and "python -m score run toy --place hangar" in report, report
    lines = runner.lines(PLACES)
    assert lines["hangar"][0] == f"stopped at clean@hangar: fault report {report_of(runner, 'clean@hangar')}", lines
    assert lines["station"][0] == "done", lines
    brief(runner.world, "hangar", "a ship")
    assert runner.drive(PLACES, say=quiet)["count@hangar"] == ACCEPTED
    assert not report_of(runner, "clean@hangar").exists()


def test_a_fault_on_an_input_moved_under_the_run_names_what_moved():
    """Batch 1 try 4, 2026-10-25: twenty lines stopped on "has not run on its current inputs", nothing said why.
    Break: score/graph/__init__.py: '        if not cause.endswith(NOT_RUN):' -> '        if True:'"""
    runner = a_driven_runner({"hangar": "a hub"})
    runner.drive(["hangar"], say=quiet)
    brief(runner.world, "hangar", "a ship")
    cause = runner.standing(COUNT, "hangar")
    assert cause == "clean@hangar has not run on its current inputs", cause
    report = runner.fault_report(COUNT, "hangar", f"blocked: {cause}", cause).read_text()
    assert "what moved its key since its last record: brief changed" in report, report


def test_nothing_is_gathered_for_an_output_another_gate_fails():
    """Break: score/graph/__init__.py: '        return sorted(blocking) if blocking and blocking <= missing else []' -> '        return sorted(missing)'"""
    runner = a_driven_runner({"hangar": "a ship!"})
    assert runner.drive(["hangar"], say=quiet)["clean@hangar"].startswith("made: fail; fault report")
    assert gathered(runner) == []
    assert "shout: fail: shouts" in report_of(runner, "clean@hangar").read_text()


def test_an_error_an_exit_or_a_missing_input_stops_its_line_with_its_cause_in_the_report():
    """surfaces-lists@lab, 2026-10-12: a SystemExit in a make ended its process with exit code 1 and nothing said.
    Break: score/graph/__init__.py: '            except (Exception, SystemExit) as error:  # noqa: BLE001 - a SystemExit too' -> '            except Exception as error:  # noqa: BLE001 - a SystemExit too'"""
    for text, said in (("explode", "error: RuntimeError: the cleaner fell over"),
                       ("quit", "error: SystemExit: the cleaner quit: no such material"),
                       (None, "blocked: clean@hangar: its input brief is missing")):
        runner = a_driven_runner({"hangar": text, "station": "a hub"})
        found = runner.drive(PLACES, say=quiet)
        assert found["clean@hangar"].startswith(said) and "; fault report " in found["clean@hangar"], found
        assert found["count@hangar"] == "not run: its line stopped at clean@hangar", found
        assert found["count@station"] == ACCEPTED, found
        report = report_of(runner, "clean@hangar").read_text()
        assert said.split(": ", 2)[-1] in report and (text is None or "Traceback" in report), report


def test_a_make_leaves_no_folder_in_making_however_it_ends():
    """2026-10-27: the folders of makes that failed stayed in store/cache/making and helped fill the conductor's disk.
    Break: score/graph/__init__.py: '        finally:\n            gone(out)' -> '        finally:\n            pass'"""
    runner = a_driven_runner({"hangar": "explode", "station": "a hub"})
    found = runner.drive(PLACES, say=quiet)
    assert found["clean@hangar"].startswith("error: RuntimeError") and found["count@station"] == ACCEPTED, found
    making = runner.store.cache / "making"
    assert not making.exists() or not list(making.iterdir()), list(making.iterdir())


def make_echo(inputs, out, seed, params):
    (out / "echo.txt").write_text(inputs["brief"].read_text())


def make_failing(inputs, out, seed, params):
    raise RuntimeError("names failed")


def test_a_stopped_node_stops_only_the_nodes_that_read_it():
    """sound@square, 2026-10-20: one failed sound stopped every later row of the square's line, though none read it.
    echo reads nothing of clean and runs; tally reads both and does not; a node already running finishes.
    Break: score/graph/__init__.py: '                    waits = [stopped[before] for before in earlier if before in stopped and before not in passes]' -> '                    waits = list(stopped.values())'"""
    echo = graph.Stage("echo", "place", make_echo, TEXT, PASSES, files={"brief": "{data}/{place}/brief.txt"})
    tally = graph.Stage("tally", "place", make_count, TEXT, PASSES, after={"clean": READS, "echo": READS})
    names = graph.Stage("names", "place", make_failing, TEXT, PASSES)
    runner = a_driven_runner({"hangar": "a ship in a very long dark hall", "station": "a hub"},
                             more=(echo, tally, names))
    found = runner.drive(PLACES, say=quiet)
    assert found["clean@hangar"].startswith("made: unknown; gathered words: judged again, output kept: fail"), found
    assert found["echo@hangar"] == ACCEPTED and found["tally@station"] == ACCEPTED, found
    assert found["count@hangar"] == found["tally@hangar"] == "not run: its line stopped at clean@hangar", found
    assert found["names@station"].startswith("error: RuntimeError: names failed"), found
    assert found["count@station"] == ACCEPTED, found


def test_a_paid_gather_runs_inside_the_runners_clearance(monkeypatch):
    """Break: score/graph/__init__.py: '        with self.cleared(node_name(stage, place), euros) if euros else contextlib.nullcontext():' -> '        with contextlib.nullcontext():'"""
    monkeypatch.setattr(compute.ledger(), "entries", lambda: [])
    runner = a_driven_runner({"hangar": "a ship"}, euros=0.2)
    assert runner.drive(["hangar"], say=quiet)["count@hangar"] == ACCEPTED
    key = runner.key(runner.stages["clean"], "hangar")["key"]
    assert [ticket for _, ticket in gathered(runner)] == [f"clean@hangar {key}"]
    assert runner.store.clearances("clean@hangar", key)[0]["euros"] == 0.2


# --- lines side by side ----------------------------------------------------------------------------------------------

MEETING_SECONDS = 15
def judge_met(output, inputs, evidence):
    return checks.Verdict("met", checks.PASS, "it ran")


MET = (checks.Check("met", judge_met),)


def meeting(data, me, others):
    """A make that says it started, then waits until every other named make started too: run one at a time, the
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


def made_once(data):
    def make(inputs, out, seed, params):
        with (data / "ground-made.txt").open("a") as made:
            made.write("made\n")
        (out / "ground.txt").write_text("ground")
    return make


def make_on_ground(inputs, out, seed, params):
    (out / "built.txt").write_text((inputs["ground"] / "ground.txt").read_text())


def a_world_of(places):
    world = a_world({place: None for place in places})
    return world.roots["data"], world


def meet_the_other_places(data):
    """A place's make meeting every other place's (its place is its declared input's folder name)."""
    def make(inputs, out, seed, params):
        place = inputs["place"].name
        meeting(data, place, [other for other in PLACES if other != place])(inputs, out, seed, params)
    return make


def test_lines_and_nodes_that_read_nothing_of_each_other_run_side_by_side():
    """Fault (owner, 2026-10-11: nothing waits for the slowest): the drive ran one node at a time. Each place's meet
    and a line's first and second each wait until the others started.
    Break: score/graph/__init__.py: 'JOBS = 8' -> 'JOBS = 1'"""
    data, world = a_world_of(PLACES)
    meet = graph.Stage("meet", "place", meet_the_other_places(data), TEXT, MET, files={"place": "{data}/{place}"})
    first = graph.Stage("first", "place", meeting(data, "first", ["second"]), TEXT, MET, applies=lambda p: p == "hangar")
    second = graph.Stage("second", "place", meeting(data, "second", ["first"]), TEXT, MET,
                         applies=lambda p: p == "hangar")
    started = time.monotonic()
    found = a_runner(world, a_store(), (meet, first, second)).drive(PLACES, say=quiet)
    assert set(found.values()) == {ACCEPTED} and len(found) == 4, found
    assert time.monotonic() - started < MEETING_SECONDS


def test_an_environment_node_is_made_once_and_a_places_own_lines_run_only_what_they_read():
    """Break: score/graph/__init__.py: '        chosen = found if whole else' -> '        chosen = found if True else'"""
    data, world = a_world_of(PLACES)
    ground = graph.Stage("ground", "world", made_once(data), TEXT, MET)
    build = graph.Stage("build", "place", make_on_ground, TEXT, MET, after={"ground": READS})
    found = a_runner(world, a_store(), (ground, build)).drive(PLACES, say=quiet)
    assert list(found.items()) == [("ground", ACCEPTED), ("build@hangar", ACCEPTED), ("build@station", ACCEPTED)]
    assert (data / "ground-made.txt").read_text() == "made\n"
    data, world = a_world_of(PLACES)
    sky = graph.Stage("sky", "world", meeting(data, "sky", ["never"]), TEXT, MET)  # no place reads it
    other = graph.Stage("other", "place", meeting(data, "other", ["never"]), TEXT, MET)  # a row the run leaves
    runner = a_runner(world, a_store(), (graph.Stage("ground", "world", made_once(data), TEXT, MET), sky, build, other))
    assert runner.drive(["hangar"], say=quiet, whole=False, only=["build"]) == {"ground": ACCEPTED,
                                                                                "build@hangar": ACCEPTED}
    assert set(runner.lines(["hangar"], whole=False)) == {"world", "hangar"}
    assert list(runner.lines(["hangar"], whole=False)["world"][1]) == ["ground"]
    assert set(runner.lines(["hangar"], whole=False, only=["build"])["hangar"][1]) == {"build@hangar"}


def failing_with(code, times):
    """A make raising an HTTP `code` error on its first `times` tries in its process, then writing."""
    tries = []

    def make(inputs, out, seed, params):
        tries.append(1)
        if len(tries) <= times:
            raise urllib.error.HTTPError("https://images.example", code, "server", {}, None)
        (out / "made.txt").write_text(f"made on try {len(tries)}")
    return make


def test_a_free_node_runs_again_on_a_transient_error_and_a_paid_one_never(monkeypatch):
    """Eight places' maps on the image model's HTTP 500s, 2026-10-12; a paid node's failure is a gap (ADR-0005).
    Break: score/graph/__init__.py: '                if stage.paid or attempt == RETRIES or not transient(error):' -> '                if attempt == RETRIES or not transient(error):'"""
    monkeypatch.setattr(graph, "RETRY_WAIT", 0)

    def driven(code, times, paid=False):
        runner = a_runner(a_world_of(["hangar"])[1], a_store(),
                          (graph.Stage("maps", "place", failing_with(code, times), TEXT, MET, paid=paid, euros=0.1),))
        runner.cleared = lambda node, euros, forecast=None: contextlib.nullcontext()  # no clearance to buy here
        return runner.drive(["hangar"], say=quiet)["maps@hangar"], runner.desk("logs", "maps@hangar", ".log").read_text()
    did, log = driven(500, 2)
    assert did == ACCEPTED and "try 2 of 5 in 0 s" in log and "try 3 of 5" in log and "try 4 of 5" not in log, log
    did, log = driven(500, 1, paid=True)
    assert did.startswith("error: HTTPError: HTTP Error 500") and "transient error" not in log, (did, log)
    for code, times in ((503, graph.RETRIES + 1), (404, 1)):
        did, log = driven(code, times)
        assert did.startswith(f"error: HTTPError: HTTP Error {code}") and log.count("transient error") == times - 1
    assert graph.transient(TimeoutError()) and graph.transient(ConnectionResetError())
    assert graph.transient(urllib.error.URLError(ConnectionRefusedError())) and not graph.transient(ValueError())


def make_leaving_a_thread(inputs, out, seed, params):
    threading.Thread(target=threading.Event().wait).start()  # never ends, and not a daemon
    (out / "made.txt").write_text("made")


def hung(signal_number, frame):
    raise RuntimeError("the drive did not end")  # not an OSError: a wait swallows those


def test_a_node_that_leaves_a_thread_running_does_not_hold_up_the_drive():
    """Fault (2026-10-12): two `score run`s did all their work and never exited.
    Break: score/graph/__init__.py: '        sys.stderr.flush()\n        os._exit(0)' -> '        sys.stderr.flush()\n        sys.exit(0)'"""
    runner = a_runner(a_world_of(["hangar"])[1], a_store(), (graph.Stage("maps", "place", make_leaving_a_thread,
                                                                         TEXT, MET),))
    signal.signal(signal.SIGALRM, hung)
    signal.alarm(20)
    try:
        assert runner.drive(["hangar"], say=quiet) == {"maps@hangar": ACCEPTED}
    finally:
        signal.alarm(0)


CHILD_THREADS = "import os; print(os.environ['OMP_NUM_THREADS'], os.environ['NUMBA_NUM_THREADS'])"


def live_openblas_threads():
    """The pool size each OpenBLAS loaded in this process runs on now (not what its variable says)."""
    import ctypes
    sizes = []
    for library in graph.loaded_openblas():
        handle = ctypes.CDLL(library)
        getter = next(getattr(handle, name.replace("_set_", "_get_")) for name in graph.OPENBLAS_SETTERS
                      if hasattr(handle, name))
        sizes.append(getter())
    return sizes


def make_thread_note(inputs, out, seed, params):
    own = f"{os.environ['OMP_NUM_THREADS']} {os.environ['NUMBA_NUM_THREADS']}"
    child = subprocess.run([sys.executable, "-c", CHILD_THREADS], capture_output=True, text=True, check=True)
    pools = " ".join(str(size) for size in live_openblas_threads())
    (out / "threads.txt").write_text(f"{own}\n{child.stdout.strip()}\n{pools}")


def thread_note(jobs, monkeypatch, cores=24):
    """The thread note one node writes when `jobs` nodes share `cores`, numpy's and scipy's OpenBLAS loaded before the
    drive forks (as score.stages loads them); and the runner."""
    import numpy  # noqa: F401
    import scipy.linalg  # noqa: F401
    runner = a_runner(a_world_of(["hangar"])[1], a_store(), (graph.Stage("threads", "place", make_thread_note, TEXT,
                                                                         MET),))
    with monkeypatch.context() as patched:
        patched.setattr(os, "cpu_count", lambda: cores)
        did = runner.drive(["hangar"], say=quiet, jobs=jobs)["threads@hangar"]
    if did != ACCEPTED:
        return did, runner
    return accepted_text(runner.store, "threads@hangar", "threads.txt").splitlines(), runner


def test_each_node_and_its_children_share_the_cores_and_a_smaller_count_the_owner_set_stands(monkeypatch):
    """C11, 2026-10-17: six local nodes each sized their pools to every core. 24 cores over 6 jobs: 4 threads each,
    the OpenBLAS loaded before the fork resized too; the owner's OMP_NUM_THREADS=1 stands, an empty one is unset.
    Break: score/graph/__init__.py: 'os.environ[variable] = str(threads if own is None else min(own, threads))' -> 'os.environ[variable] = str(threads)'"""
    lines, _ = thread_note(6, monkeypatch)
    assert lines[:2] == ["4 4", "4 4"] and lines[2].split() and set(lines[2].split()) == {"4"}, lines
    monkeypatch.setenv("OMP_NUM_THREADS", "1")
    assert thread_note(6, monkeypatch)[0][:2] == ["1 4", "1 4"]
    monkeypatch.setenv("OMP_NUM_THREADS", "")
    assert thread_note(6, monkeypatch)[0][:2] == ["4 4", "4 4"]
    with monkeypatch.context() as patched:
        patched.setattr(os, "cpu_count", lambda: 24)
        assert graph.oversubscribed(6) is None and "--oversubscribe" in graph.oversubscribed(30)


def test_a_cap_that_fails_shows_its_cause_in_the_nodes_fault_report(monkeypatch):
    """Review (C11): a cap that raised before the node's log opened ended it 'without saying what it did'.
    Break: score/graph/__init__.py: '        with logged(log):\n            try:\n                cap_threads(threads)' -> '        cap_threads(threads)\n        with logged(log):\n            try:'"""
    monkeypatch.setattr(graph, "OPENBLAS_SETTERS", ("no_such_setter",))
    did, runner = thread_note(6, monkeypatch)
    assert "pool cannot be capped" in did and "without saying" not in did, did
    report = runner.desk("faults", "threads@hangar", ".txt").read_text()
    assert "RuntimeError" in report and "  | " in report and "pool cannot be capped" in report, report


def test_a_node_whose_log_cannot_be_written_still_says_why_it_ended(monkeypatch):
    """Batch 1, 2026-10-26: the conductor's disk full, surfaces-parts@engineroom ended 'without saying what it did'
    and an empty log; the error comes back through the pipe, which needs no disk.
    Break: score/graph/__init__.py: '        except BaseException as error:  # noqa: BLE001 - raised where' -> '        except KeyError as error:  # noqa: BLE001 - raised where'"""
    @contextlib.contextmanager
    def full_disk(path):
        raise OSError(28, "No space left on device")
        yield

    monkeypatch.setattr(graph, "logged", full_disk)
    did, _ = thread_note(6, monkeypatch)
    assert "OSError: [Errno 28] No space left on device" in did and "without saying" not in did, did
    assert "raised outside its log" in did and "Traceback" in did, did


def test_score_run_refuses_a_thread_count_that_is_not_one_and_more_jobs_than_cores(monkeypatch):
    """Review (C11): OMP_NUM_THREADS '4,2', 'auto' and '0' crashed every node; --jobs 0 ended in a ZeroDivisionError.
    Break: score/graph/__init__.py: '        if own and not (own.isdigit() and int(own) > 0):' -> '        if own and not own.isdigit():'"""
    from score import __main__ as command
    for value in ("4,2", "auto", "0"):
        monkeypatch.setenv("OMP_NUM_THREADS", value)
        with pytest.raises(SystemExit) as refusal:
            command.checked_thread_variables()
        assert str(refusal.value) == (f"refused: OMP_NUM_THREADS={value!r} is not a thread count (a whole number "
                                      "above 0); unset it or set one")
    monkeypatch.setattr(os, "cpu_count", lambda: 24)
    for argv in (["--jobs", "8"], ["--jobs", "24"], ["--jobs", "25", "--oversubscribe"]):
        command.checked_threads(command.parse(["run", "world1", *argv]))
    with pytest.raises(SystemExit) as refusal:
        command.checked_threads(command.parse(["run", "world1", "--jobs", "25"]))
    assert str(refusal.value).startswith("refused: 25 jobs") and "--oversubscribe" in str(refusal.value)
    for jobs in ("0", "-2"):
        printed = io.StringIO()
        with contextlib.redirect_stderr(printed), pytest.raises(SystemExit) as refusal:
            command.parse(["run", "world1", "--jobs", jobs])
        assert refusal.value.code == 2 and "at least 1" in printed.getvalue(), printed.getvalue()


def test_a_pass_lists_each_prefix_once_works_out_each_key_once_and_only_the_runs_own_nodes(monkeypatch):
    """2026-10-12: `score status` walked the whole store for every lookup, over five minutes; 2026-10-16: then once a
    finished node, holding runs at their end. Two passes (lines, status) list each prefix once each and work out
    each of the 4 keys once each; a finished node's verdict in a store of 15,000 unrelated keys lists only its run's.
    Break: score/graph/__init__.py: '        self.store.objects.keys = listed_once(self.store.objects.keys)' -> '        self.store.objects.keys = self.store.objects.keys'"""
    runner = a_driven_runner({"hangar": "a ship", "station": "a hub"})
    runner.drive(PLACES, say=quiet)
    walks, keys = [], []
    store_class = type(runner.store.objects)
    walk, work_out = store_class.keys, graph.Runner.worked_out_key
    monkeypatch.setattr(store_class, "keys", lambda self, prefix: walks.append(prefix) or walk(self, prefix))
    monkeypatch.setattr(graph.Runner, "worked_out_key",
                        lambda self, stage, place: keys.append((stage.name, place)) or work_out(self, stage, place))
    assert {state for state, _ in runner.lines(PLACES).values()} == {"done"}
    assert "accepted" in runner.status(PLACES)["count@hangar"]
    assert walks and "" not in walks and len(walks) == 2 * len(set(walks)), walks
    assert sorted(keys) == sorted(2 * [(stage, place) for stage in ("clean", "count") for place in PLACES]), keys
    assert runner.remembered is None and "keys" not in vars(runner.store.objects)
    root = runner.store.objects.root
    for area in ("records", "judgements", "accepts"):
        for folder in range(100):
            unrelated = root / area / f"elsewhere{folder}@far"
            unrelated.mkdir(parents=True)
            for index in range(50):
                (unrelated / f"{index}.json").write_text("{}")
    walks.clear()
    started = time.monotonic()
    assert runner.conclude(runner.stages["count"], "hangar", "made") == ("made", True)
    assert time.monotonic() - started < 1.0
    nodes = {f"{stage}@{place}" for stage in ("clean", "count") for place in PLACES}
    assert walks and all(prefix.split("/")[1] in nodes for prefix in walks), walks


# --- runs side by side on one store ----------------------------------------------------------------------------------

def made_slowly(data):
    """A make counting its makes in a file and taking a second: two runs of it at once would overlap."""
    def make(inputs, out, seed, params):
        with (data / "made.txt").open("a") as made:
            made.write("made\n")
        time.sleep(1)
        (out / "made.txt").write_text("made")
    return make


def drive_in_a_process(runner, places):
    receiving, sending = graph.FORK.Pipe(duplex=False)
    process = graph.FORK.Process(target=lambda: sending.send(runner.drive(places, say=quiet)))
    process.start()
    return process, receiving


def test_two_runs_of_one_key_at_once_make_it_once_and_a_lock_held_too_long_makes_nothing(monkeypatch):
    """2026-10-12: two runs made people-segvigen at once; the second paid again, then failed on the first's record.
    A record or judgement another run stored first is taken as made; a lock held past its wait blocks.
    Break: score/graph/__init__.py: '            with self.held(node_name(stage, place), keyed["key"]):' -> '            with contextlib.nullcontext():'"""
    data, world = a_world_of(["hangar"])
    store = tempfile.mkdtemp()
    slow = graph.Stage("slow", "place", made_slowly(data), TEXT, MET)
    runners = [graph.Runner((slow,), world, Store.in_folder(store), model_record=lambda kind: {}) for _ in range(2)]
    started = [drive_in_a_process(runner, ["hangar"]) for runner in runners]
    found = [receiving.recv() for _, receiving in started]
    for process, _ in started:
        process.join()
    assert (data / "made.txt").read_text() == "made\n", found
    assert sorted(result["slow@hangar"] for result in found) == ["fresh", ACCEPTED], found
    data, world = a_world_of(["hangar"])
    slow = graph.Stage("slow", "place", made_slowly(data), TEXT, MET)
    shared = tempfile.mkdtemp()
    runners = [graph.Runner((slow,), world, Store.in_folder(shared), model_record=lambda kind: {}) for _ in range(2)]
    keyed = runners[0].key(slow, "hangar")
    first = runners[0].make(slow, "hangar", keyed)
    assert runners[1].make(slow, "hangar", keyed) == first
    judged = runners[0].judge(slow, "hangar", first)
    assert runners[1].judge(slow, "hangar", first) == judged
    data, world = a_world_of(["hangar"])
    runner = graph.Runner((graph.Stage("slow", "place", made_slowly(data), TEXT, MET),), world, a_store(),
                          model_record=lambda kind: {})
    monkeypatch.setattr(graph, "LOCK_WAIT", 0.2)
    monkeypatch.setattr(graph, "LOCK_POLL", 0.05)
    with runner.held("slow@hangar", runner.key(runner.stages["slow"], "hangar")["key"]):  # another run holds it
        did = runner.run_node(runner.stages["slow"], "hangar")
    assert did.startswith("blocked: slow@hangar: another run has held its lock") and "pid" in did, did
    assert not (data / "made.txt").exists()
    assert runner.run_node(runner.stages["slow"], "hangar") == ACCEPTED


def make_note(inputs, out, seed, params):
    (out / "note.txt").write_text(inputs["note"].read_text())


def test_a_run_never_accepts_over_an_output_a_newer_commit_made_under_another_key(monkeypatch):
    """2026-10-12: a runner in an older worktree accepted terrain's old output over the newer accepted one.
    Break: score/graph/__init__.py: '        if not records or any(record["key"] == key for record in records):' -> '        if True:'"""
    data, world = a_world_of(["hangar"])
    (data / "hangar" / "note.txt").write_text("new")
    note = graph.Stage("note", "place", make_note, TEXT, MET, files={"note": "{data}/{place}/note.txt"})
    runner = a_runner(world, a_store(), (note,))
    assert runner.run_node(note, "hangar") == ACCEPTED
    newer = runner.store.accepted("note@hangar")
    (data / "hangar" / "note.txt").write_text("old")  # the older checkout's input: another key
    with monkeypatch.context() as patched:
        patched.setattr(graph._code, "holds", lambda commit: False)  # a commit this checkout lacks
        did = runner.run_node(note, "hangar")
    assert did.startswith("made: pass, not accepted: key differs from the accepted one") and "pull main" in did, did
    assert runner.store.accepted("note@hangar") == newer
    (data / "hangar" / "note.txt").write_text("newest")  # this checkout holds the accepted one's commit
    assert runner.run_node(note, "hangar") == ACCEPTED and runner.store.accepted("note@hangar") != newer


def make_writing_into_its_input(inputs, out, seed, params):
    (inputs["slow"] / "saved-over.txt").write_text("a save into the input")
    (out / "count.txt").write_text("counted")


def test_a_make_that_writes_into_its_input_fails_and_stores_nothing():
    """light@camp, 2026-10-12: its make saved over its read-only input.
    Break: score/graph/__init__.py: '        if changed:\n            raise RuntimeError(f"{node}: its make wrote' -> '        if False:\n            raise RuntimeError(f"{node}: its make wrote'"""
    data, world = a_world_of(["hangar"])
    slow = graph.Stage("slow", "place", made_slowly(data), TEXT, MET)
    writer = graph.Stage("writer", "place", make_writing_into_its_input, TEXT, MET, after={"slow": READS})
    runner = a_runner(world, a_store(), (slow, writer))
    found = runner.drive(["hangar"], say=quiet)
    assert found["writer@hangar"].startswith("error: RuntimeError: writer@hangar: its make wrote into its read-only "
                                             "input slow"), found
    assert runner.store.records("writer@hangar") == []


def judge_gapped(output, inputs, evidence):
    return checks.Verdict(graph.GAPPED, checks.FAIL, "hangar: an accepted gap", findings=("hangar: no made model",))


def judge_brief_fault(output, inputs, evidence):
    faulty = "fault" in inputs["brief"].read_text()
    return checks.Verdict("other", checks.FAIL if faulty else checks.PASS, "a fault no gap names" if faulty else "ok")


def make_film(inputs, out, seed, params):
    (out / "film.txt").write_text((inputs["complete"] / "clean.txt").read_text())


def gapped_runner(text):
    """A completion gate failing its accepted gap (and an ungapped fault when the brief says so); a film reading it
    gapped, a count that does not."""
    data, world = a_world_of(["hangar"])
    (data / "hangar" / "brief.txt").write_text(text)
    complete = graph.Stage("complete", "place", make_clean, TEXT,
                           (checks.Check(graph.GAPPED, judge_gapped), checks.Check("other", judge_brief_fault)),
                           files={"brief": "{data}/{place}/brief.txt"})
    film = graph.Stage("film", "place", make_film, TEXT, MET, after={"complete": READS}, gapped=("complete",))
    count = graph.Stage("count", "place", make_film, TEXT, MET, after={"complete": READS})
    return a_runner(world, a_store(), (complete, film, count))


def test_a_gapped_reader_runs_past_a_gate_failing_only_on_its_accepted_gaps_and_stops_on_any_other_fault():
    """The overseer, 2026-10-15: demo-film runs on a place whose complete fails only on its accepted gaps; the gate
    still fails by name, a reader not reading it gapped stops, and a fault no gap names stops both.
    Break: score/graph/__init__.py: '                    passes = {before for before in on_gaps if before.partition("@")[0] in stage.gapped}' -> '                    passes = set()'"""
    runner = gapped_runner("a ship")
    found = runner.drive(["hangar"], say=quiet)
    assert found["complete@hangar"].startswith("made: fail, accepted automatically; fault report"), found
    assert found["film@hangar"] == ACCEPTED, found
    assert found["count@hangar"] == "not run: its line stopped at complete@hangar", found
    assert runner.store.accepts("complete@hangar")[-1]["status"] == "complete apart from accepted gaps (1)"
    assert runner.status(["hangar"])["complete@hangar"] == "complete apart from accepted gaps (1), accepted"
    assert "stale" not in runner.status(["hangar"])["film@hangar"]
    runner = gapped_runner("a ship with a fault")
    assert runner.drive(["hangar"], say=quiet)["film@hangar"] == "not run: its line stopped at complete@hangar"
    assert runner.run_node(runner.stages["film"], "hangar").startswith("blocked: complete@hangar answered fail")
    assert runner.store.accepted("complete@hangar") is None


# --- memory: no node starts while this PC's memory is short --------------------------------------------------------
# Fault (owner, 2026-10-22): this PC (43 GB) has run out of memory before; the Buy batch goes from 8 jobs to 16.

FLOOR = graph.MEMORY_FLOOR


def faked(monkeypatch, readings):
    """graph.AVAILABLE replaced by `readings` in turn, its last one kept; the readings taken so far."""
    taken = []

    def reading():
        taken.append(readings[min(len(taken), len(readings) - 1)])
        return taken[-1]
    monkeypatch.setattr(graph, "AVAILABLE", reading)
    return taken


def test_each_node_started_lately_holds_a_floor_and_a_machine_names_its_own(monkeypatch):
    """2.5 floors available: room with none or one ramping, none with two, room once the older has ramped; a 4 GB
    floor named by SCORE_MIN_FREE_GB on 5 GB: room for one, none while one ramps.
    Break: score/graph/__init__.py: '    return AVAILABLE() - ramping * memory_floor() >= memory_floor()' -> '    return AVAILABLE() >= memory_floor()'"""
    faked(monkeypatch, [2.5 * FLOOR])
    now = time.monotonic()
    assert graph.memory_room([]) and graph.memory_room([now]) and not graph.memory_room([now, now])
    assert graph.memory_room([now, now - graph.RAMP_SECONDS - 1])
    faked(monkeypatch, [5 * 2**30])
    monkeypatch.setenv(graph.FLOOR_VARIABLE, "4")
    assert graph.memory_floor() == 4 * 2**30 and graph.memory_room([])
    assert not graph.memory_room([time.monotonic()])
    monkeypatch.setenv(graph.FLOOR_VARIABLE, "")
    assert graph.memory_floor() == FLOOR and not graph.memory_room([])


def test_the_drive_waits_while_memory_is_short_and_never_starts_more_than_its_jobs(monkeypatch):
    """Break: score/graph/__init__.py: '                        held = held or not memory_room(starts)' -> '                        held = False'"""
    runner = a_driven_runner({"hangar": "a ship", "station": "a hub"})
    taken = faked(monkeypatch, [FLOOR - 1] * 3 + [100 * FLOOR])
    started, start = [], runner.start
    runner.start = lambda stage, place, threads: started.append(taken[-1]) or start(stage, place, threads)
    monkeypatch.setattr(graph, "MEMORY_POLL", 0.01)
    said = []
    found = runner.drive(PLACES, say=said.append, jobs=4)
    assert set(found) == {"clean@hangar", "clean@station", "count@hangar", "count@station"}, found
    assert started and all(reading >= FLOOR for reading in started), started
    assert len(taken) > 3 and [line for line in said if line.startswith("memory: ")], said
    runner = a_driven_runner({place: "a ship" for place in PLACES})
    faked(monkeypatch, [100 * FLOOR])
    running, most, start, wait = [], [0], runner.start, graph.FORK_WAIT

    def counted_start(stage, place, threads):
        begun = start(stage, place, threads)
        running.extend(begun)
        most[0] = max(most[0], len(running))
        return begun

    def counted_wait(connections, timeout=None):
        finished = wait(connections, timeout=timeout)
        for connection in finished:
            running.remove(connection)
        return finished
    runner.start = counted_start
    monkeypatch.setattr(graph, "FORK_WAIT", counted_wait)
    runner.drive(PLACES, say=quiet, jobs=1)
    assert most[0] == 1, most



def test_a_node_that_ended_holds_no_memory_so_light_nodes_start_as_fast_as_they_end(monkeypatch):
    """Room for one floor only, a ramp far longer than the nodes: each next node starts once the one before ended,
    never after the ramp (env1 on the PC, 2026-10-27: light rows of seconds ran 5 a minute, 31 GB free).
    Break: score/graph/__init__.py: drop '                starts.pop(node, None)' -> the drive waits out the ramp."""
    runner = a_driven_runner({"hangar": "a ship", "station": "a hub"})
    faked(monkeypatch, [1.5 * FLOOR])
    monkeypatch.setattr(graph, "RAMP_SECONDS", 3)
    monkeypatch.setattr(graph, "MEMORY_POLL", 0.01)
    begun = time.monotonic()
    found = runner.drive(PLACES, say=quiet, jobs=4)
    assert set(found) == {"clean@hangar", "clean@station", "count@hangar", "count@station"}, found
    assert time.monotonic() - begun < graph.RAMP_SECONDS, time.monotonic() - begun


def test_an_input_is_hashed_again_once_it_changed_and_never_kept_while_it_just_changed(tmp_path, monkeypatch):
    """A settled file's hash is kept and read once; the same size rewritten is hashed anew; a file changed within
    SETTLED_NS is never kept. Break: score/graph/__init__.py: 'found.st_size, found.st_mtime_ns, found.st_ctime_ns)'
    -> 'found.st_size)' -> the rewritten file keeps its old hash."""
    monkeypatch.setattr(graph, "HASHED", {})
    read, hashed = [], graph.file_hash
    monkeypatch.setattr(graph, "file_hash", lambda path: read.append(path) or hashed(path))
    folder = tmp_path / "inputs"
    folder.mkdir()
    (folder / "a.json").write_text("aaaa")
    settled = time.time_ns() - 10 * graph.SETTLED_NS
    os.utime(folder / "a.json", ns=(settled, settled))
    later = time.time_ns() + 10 * graph.SETTLED_NS
    monkeypatch.setattr(graph.time, "time_ns", lambda: later)  # its ctime (now) settled too
    first = graph.source_hash(folder)
    assert graph.source_hash(folder) == first and len(read) == 1, read
    (folder / "a.json").write_text("bbbb")
    os.utime(folder / "a.json", ns=(settled, settled))  # the same size and mtime: only its ctime moved
    second = graph.source_hash(folder)
    assert second != first and second == graph.listing_hash({"a.json": hashed(folder / "a.json")})
    monkeypatch.undo()
    monkeypatch.setattr(graph, "HASHED", {})
    monkeypatch.setattr(graph, "file_hash", lambda path: read.append(path) or hashed(path))
    (folder / "a.json").write_text("cccc")  # changed just now: read every time, never kept
    graph.source_hash(folder), graph.source_hash(folder)
    assert len(read) == 4 and not graph.HASHED, read

# --- a run's end: one result line, every process it started ended, what it held released (score/__main__.py) -------

@contextlib.contextmanager
def logs_in_tmp():
    """A detached run's logs in a folder of the test's own, never $PROPS_HOME/logs; that folder."""
    kept, runs.LOGS = runs.LOGS, pathlib.Path(tempfile.mkdtemp())
    try:
        yield runs.LOGS
    finally:
        runs.LOGS = kept


def detached(argv):
    """`score run --detach` of a Python command: (what it printed, its log), once the log has its result line."""
    from score import __main__ as command
    printed = io.StringIO()
    started = time.time()
    with contextlib.redirect_stdout(printed), logs_in_tmp() as logs:
        command.detach(["-c", *argv, command.DETACH])
    assert time.time() - started < 2.5, time.time() - started  # returns at once
    log = pathlib.Path(printed.getvalue().strip().rpartition("log=")[2])
    assert log.parent == logs and printed.getvalue().splitlines()[-1].startswith("detached: started pid="), log
    return printed.getvalue(), log


def wait_for(path, text, within=60):
    deadline = time.time() + within
    while text not in (path.read_text() if path.exists() else "") and time.time() < deadline:
        time.sleep(0.1)
    return path.read_text().splitlines() if path.exists() else []


def test_a_detached_run_returns_at_once_and_its_log_always_ends_with_its_result_line():
    """Fault (2026-10-12): a run whose group was sent SIGTERM ended its log with no line; review of C10: a run another
    run's registration refused after detaching ends with the refusal as its line.
    Break: score/graph/stopped.py: '    if code != REFUSED:\n        return line' -> '    if True:\n        return line'"""
    _, log = detached(["import time; time.sleep(1); print('the run went on')"])
    lines = wait_for(log, "detached:")
    assert lines[0] == "the run went on" and lines[-1].startswith("detached: ok exit=0 "), lines
    printed, log = detached(["import sys; print('refused: run pid 7 holds the store', file=sys.stderr); "
                             f"sys.exit({stopped.REFUSED})"])
    assert "may still be refused" in printed, printed
    lines = wait_for(log, "detached:")
    assert lines[-1].startswith(f"detached: refused: run pid 7 holds the store exit={stopped.REFUSED} "), lines
    printed, log = detached(["import time; print('working', flush=True); time.sleep(60)"])
    wait_for(log, "working", 30)
    os.killpg(int(printed.split("pid=")[1].split()[0]), signal.SIGTERM)  # the session detach started
    lines = wait_for(log, "detached:", 30)
    assert lines[-1].startswith("detached: stopped by signal 15 exit=143 ") and f"log={log}" in lines[-1], lines


def test_a_run_started_as_a_script_imports_the_tools_library():
    """Benchmark 2026-10-22: `python score/__main__.py` put score/ first on the path, so `import library` found
    score/library and earth-seed failed on it.
    Break: score/__main__.py: 'sys.path[:] = [entry for entry in sys.path if pathlib.Path(entry or ".").resolve() != REPO / "score"]' -> 'pass'"""
    probe = ("import runpy, sys; runpy.run_path(sys.argv[1], run_name='probe'); import library; "
             "print(library.__file__)")
    done = subprocess.run([sys.executable, "-c", probe, str(REPO / "score/__main__.py")], cwd=REPO / "score",
                          capture_output=True, text=True, timeout=110)
    assert done.stdout.strip().endswith("tools/props/library/library.py"), done.stdout + done.stderr[-2000:]


# A `score run` in miniature: it becomes a run with score/__main__'s stop handling, forks a node that waits, and
# starts a batch that stops on SIGTERM and one that ignores it; it writes its run id and every pid.
STOPPED_RUN = """
import json, os, pathlib, signal, subprocess, sys, time, types
sys.path.insert(0, sys.argv[1])
from score import __main__ as command
from score.adapters import compute
folder = pathlib.Path(sys.argv[2])
command.STOP_GRACE_SECONDS = 2
runner = types.SimpleNamespace(store=types.SimpleNamespace(cache=folder / "cache", is_framework_store=lambda: True))


def drive():
    run_id = os.environ[command.RUN_ID]
    (folder / "reservations.json").write_text(json.dumps({
        compute.graph.now(): {"euros": 2.0, "run": run_id},
        "2099-01-01T00:00:00+00:00": {"euros": 1.0, "run": "other"}}))
    if sys.argv[3] == "fails":
        raise RuntimeError("the drive fell over")
    pids = []
    node = os.fork()
    if node == 0:
        time.sleep(120)
        os._exit(0)
    pids.append(node)
    batch = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"])
    stubborn = subprocess.Popen([sys.executable, "-c", "import signal, time; signal.signal(signal.SIGTERM, "
                                 "signal.SIG_IGN); open(__import__('sys').argv[1], 'w').write('ready'); time.sleep(120)",
                                 str(folder / "stubborn-ready")])
    pids += [batch.pid, stubborn.pid]
    while not (folder / "stubborn-ready").exists():
        time.sleep(0.05)
    (folder / "pids.json").write_text(json.dumps({"run": run_id, "pids": pids}))
    time.sleep(120)


command.as_run(runner, drive)
"""


def alive(pid):
    """Whether a process is there and not a zombie."""
    try:
        return pathlib.Path(f"/proc/{pid}/stat").read_text().rpartition(")")[2].split()[0] != "Z"
    except OSError:
        return False


def a_run_home(prefix):
    folder = pathlib.Path(tempfile.mkdtemp(prefix=prefix))
    return folder, {**os.environ, "PROPS_HOME": str(folder), "PROPS_WORK": str(folder / "work")}


def test_a_stopped_or_failed_run_ends_every_process_it_started_and_releases_only_its_reservations():
    """Fault (2026-10-17): runs stopped from outside left their nodes and batches running, renting on; review of C7:
    a drive that raised left its reservations held. The one process deaf to SIGTERM gets SIGKILL after the grace.
    Break: score/__main__.py: '        release_once_ended(runner, run_id, mark, pool_ticket[0] if pool_ticket else None)' -> '        pass'"""
    folder, environment = a_run_home("stopped-run-")
    run = subprocess.Popen([sys.executable, "-c", STOPPED_RUN, str(REPO), str(folder), "waits"], env=environment,
                           stdout=subprocess.PIPE, text=True, start_new_session=True)
    wait_for(folder / "pids.json", "pids")
    started = json.loads((folder / "pids.json").read_text())
    assert all(map(alive, started["pids"])), started
    stopped_at = time.time()
    run.send_signal(signal.SIGTERM)  # to the run's pid alone, not its group
    output, _ = run.communicate(timeout=60)
    while any(map(alive, started["pids"])) and time.time() < stopped_at + 35:
        time.sleep(0.2)
    assert not any(map(alive, started["pids"])), [pid for pid in started["pids"] if alive(pid)]
    assert run.returncode == 143 and "score run: stopped by signal 15" in output, (run.returncode, output)
    assert "SIGKILL to 1 processes" in output, output
    assert [held["run"] for held in json.loads((folder / "reservations.json").read_text()).values()] == ["other"]
    folder, environment = a_run_home("failed-run-")
    run = subprocess.run([sys.executable, "-c", STOPPED_RUN, str(REPO), str(folder), "fails"], env=environment,
                         capture_output=True, text=True, timeout=60, start_new_session=True)
    assert run.returncode == 1 and "the drive fell over" in run.stderr, (run.returncode, run.stderr)
    assert [held["run"] for held in json.loads((folder / "reservations.json").read_text()).values()] == ["other"]


# A cloud batch holding three machines, each deleted through batch.delete_machine taking argv[3] seconds; it writes
# "ready" once its stop handler is in.
SLOW_BATCH = """
import pathlib, sys, time
sys.path.insert(0, sys.argv[1])
import batch
from provider import cloud
folder, seconds = pathlib.Path(sys.argv[2]), float(sys.argv[3])


def delete(server_id, zone):
    time.sleep(seconds)
    with (folder / "deletes.txt").open("a") as deletes:
        deletes.write(server_id + chr(10))
    return True


cloud.delete = delete
batch.stop_on_signals()
machines = [{"id": f"machine-{number}", "zone": "zone-a", "deleted": None, "watchdog": 999999999,
             "folder": folder / f"machine-{number}", "created": time.time(), "kind": None, "healthy": False}
            for number in range(3)]
try:
    (folder / "ready").write_text("ready")
    time.sleep(120)
finally:
    for machine in machines:
        batch.delete_machine(machine)
"""
# A `score run` in miniature whose one node runs SLOW_BATCH (argv[5]) from tools/cloud, its output piped to the node
# as a stage's subprocess.run does; the run's grace is argv[3] seconds, each delete argv[4]; with argv[6], the node's
# main thread runs no handler for that many seconds after the batch starts (long C code: its signals wait).
GROUP_RUN = """
import json, os, pathlib, signal, subprocess, sys, threading, time, types
sys.path.insert(0, sys.argv[1])
from score import __main__ as command, graph
from score.adapters import compute
folder, cloud = pathlib.Path(sys.argv[2]), str(pathlib.Path(sys.argv[1]) / "tools/cloud")
command.STOP_GRACE_SECONDS = float(sys.argv[3])
runner = types.SimpleNamespace(store=types.SimpleNamespace(cache=folder / "cache", is_framework_store=lambda: True))


def drive():
    leader = os.getpid()
    (folder / "reservations.json").write_text(json.dumps({compute.graph.now(): {"euros": 2.0,
                                                                                 "run": os.environ[command.RUN_ID]}}))
    if os.fork() == 0:  # a node, as Runner.start forks one
        threading.Thread(target=graph.watch_runner, args=(leader, 0.2), daemon=True).start()
        batch = subprocess.Popen([sys.executable, "-c", sys.argv[5], cloud, str(folder), sys.argv[4]],
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        if len(sys.argv) > 6:
            while not (folder / "ready").exists():
                time.sleep(0.05)
            every = set(signal.Signals)
            signal.pthread_sigmask(signal.SIG_BLOCK, every)
            time.sleep(float(sys.argv[6]))
            signal.pthread_sigmask(signal.SIG_UNBLOCK, every)
        output, _ = batch.communicate()
        (folder / "batch.log").write_text(output)
        os._exit(0)
    time.sleep(120)


command.as_run(runner, drive)
"""


def group_run(grace, delete_seconds, *busy):
    """A GROUP_RUN in a session of its own, once its batch is ready; the process and its folder."""
    folder, environment = a_run_home("group-run-")
    run = subprocess.Popen([sys.executable, "-c", GROUP_RUN, str(REPO), str(folder), str(grace), str(delete_seconds),
                            SLOW_BATCH, *busy], env=environment, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           text=True, start_new_session=True)
    wait_for(folder / "ready", "ready")
    assert (folder / "ready").exists(), "the fake batch never started"
    return run, folder


def deleted_by(folder, run, within=60):
    """The machine ids the run's batch deleted once the run and its batch ended; and the run's output."""
    output, _ = run.communicate(timeout=within)
    wait_for(folder / "batch.log", "", within)
    deletes = folder / "deletes.txt"
    return (deletes.read_text().split() if deletes.exists() else []), output


THREE = ["machine-0", "machine-1", "machine-2"]


def test_a_stopped_runs_cloud_batch_gets_one_stop_and_deletes_every_machine():
    """Review of C7 (2026-10-17): Ctrl-C, a closed terminal or `kill -- -<pgid>` gives every batch the signal, and the
    run's own SIGTERM moments later, a batch's second signal, broke its delete loop (0 of 3 deleted); a node whose
    main thread was busy in long code showed no stop and got the second signal too; the SIGKILL after the grace cut a
    batch's deletes short.
    Break: score/__main__.py: '    spared = cloud_side(group)' -> '    spared = set()'"""
    for number in (signal.SIGINT, signal.SIGHUP, signal.SIGTERM):
        run, folder = group_run(30, 0.3)
        os.killpg(run.pid, number)
        assert deleted_by(folder, run)[0] == THREE, number
    run, folder = group_run(30, 0.8, "3")
    time.sleep(0.5)  # the node's main thread is in its stretch now
    os.killpg(run.pid, signal.SIGTERM)
    assert deleted_by(folder, run)[0] == THREE
    run, folder = group_run(1, 0.8)
    run.send_signal(signal.SIGTERM)  # the run alone: it passes its stop on itself
    deleted, output = deleted_by(folder, run)
    assert deleted == THREE and "SIGKILL" not in output, (deleted, output)


def test_a_stopped_run_holds_its_reservations_until_its_cloud_tools_have_ended():
    """Review of C7 (2026-10-17): a stopped run released its reservations as it exited, while the cloud tools it
    spared were still deleting machines that billed.
    Break: score/__main__.py: '    if not ending and not cloud_tool("park").parked_by(run_id):' -> '    if True:'"""
    run, folder = group_run(1, 1.5)
    run.send_signal(signal.SIGTERM)
    run.wait(timeout=60)
    deletes = folder / "deletes.txt"
    assert len(deletes.read_text().split() if deletes.exists() else []) < 3  # the run ended first
    assert len(json.loads((folder / "reservations.json").read_text())) == 1
    deadline = time.time() + 30
    while time.time() < deadline and json.loads((folder / "reservations.json").read_text()):
        time.sleep(0.1)
    assert deletes.read_text().split() == THREE
    assert json.loads((folder / "reservations.json").read_text()) == {}
    assert not list(folder.rglob("runs/*")), list(folder.rglob("runs/*"))


# A shell pipeline's later stage (`... | score run`) in a session of its own, a pseudo-terminal its controlling
# terminal: argv[2] "becomes" checks it holds the terminal as a run; "ends" checks a whole run gives it back.
PIPELINE_RUN = """
import fcntl, os, pathlib, signal, sys, tempfile, termios, time, types
sys.path.insert(0, sys.argv[1])
from score import __main__ as command
_, terminal = os.openpty()
fcntl.ioctl(terminal, termios.TIOCSCTTY, 0)
first = os.fork()
if first == 0:
    time.sleep(30)
    os._exit(0)
os.setpgid(first, first)
signal.signal(signal.SIGTTOU, signal.SIG_IGN)
os.tcsetpgrp(terminal, first)
later = os.fork()
if later == 0:
    while os.getpgrp() != first:
        time.sleep(0.01)
    if sys.argv[2] == "becomes":
        command.become_run()
        os._exit(0 if os.tcgetpgrp(terminal) == os.getpid() else 3)
    folder = pathlib.Path(tempfile.mkdtemp(prefix="pipeline-run-"))
    runner = types.SimpleNamespace(store=types.SimpleNamespace(cache=folder / "cache", is_framework_store=lambda: True))
    held = []
    command.as_run(runner, lambda: held.append(os.tcgetpgrp(terminal) == os.getpid()))
    os._exit(0 if held == [True] and os.tcgetpgrp(terminal) == first else 3)
os.setpgid(later, first)
_, status = os.waitpid(later, 0)
os.kill(first, signal.SIGKILL)
sys.exit(os.waitstatus_to_exitcode(status))
"""


def test_a_run_late_in_a_shell_pipeline_keeps_the_terminal_and_gives_it_back_when_it_ends():
    """Review of C7 (2026-10-17): leading a group of its own took a pipeline's later stage out of the terminal's
    foreground group (Ctrl-C no longer reached it), and the terminal was never given back.
    Break: score/__main__.py: '    if held_before is not None:\n        hand_terminal(terminal, os.getpgrp())' -> '    if False:\n        hand_terminal(terminal, os.getpgrp())'"""
    for case in ("becomes", "ends"):
        folder, environment = a_run_home("pipeline-")
        done = subprocess.run([sys.executable, "-c", PIPELINE_RUN, str(REPO), case], capture_output=True, text=True,
                              timeout=60, start_new_session=True, env=environment)
        assert done.returncode == 0, (case, done.returncode, done.stderr)


def slow_runner(seconds):
    """A one-node run whose make takes `seconds`."""
    def make_slowly(inputs, out, seed, params):
        time.sleep(seconds)
        (out / "made.txt").write_text("made")
    return a_runner(a_world_of(["hangar"])[1], a_store(), (graph.Stage("slow", "place", make_slowly, TEXT, MET),))


def test_a_long_node_has_heartbeats_and_a_gauge_that_fails_is_said_without_ending_the_drive(monkeypatch):
    """Fault (2026-10-16): runs failed or sat idle quietly. Review (C8): a gauge that raised ended the drive; a stage's
    own drive (no gauges) says no beat. The 2-minute beat and 3-minute node scaled to 0.3 s and 1.5 s.
    Break: score/graph/__init__.py: '            beat_in = max(0.0, beat_at - time.monotonic()) if gauges else None' -> '            beat_in = None'"""
    monkeypatch.setattr(graph, "HEARTBEAT", 0.3)
    said = []
    assert slow_runner(1.5).drive(["hangar"], say=said.append, gauges=lambda: "EUR 0.00 so far") == {
        "slow@hangar": ACCEPTED}
    beats = [line for line in said[:said.index(f"slow@hangar: {ACCEPTED}")] if line.startswith("heartbeat ")]
    assert len(beats) >= 3 and beats[0].endswith(": rows done 0, running 1, queued 0; EUR 0.00 so far"), said
    said = []
    assert slow_runner(1).drive(["hangar"], say=said.append, gauges=lambda: 1 / 0) == {"slow@hangar": ACCEPTED}
    beats = [line for line in said if line.startswith("heartbeat ")]
    assert beats and beats[0].endswith("; gauges unreadable: ZeroDivisionError: division by zero"), said
    said = []
    slow_runner(0.6).drive(["hangar"], say=said.append)
    assert not [line for line in said if line.startswith(("heartbeat ", "exit:"))], said


def run_options(**more):
    return argparse.Namespace(jobs=graph.JOBS, stage=None, command="run", **more)


def run_printing(runner, places, whole=False, **options):
    """score run's drive, closing status and exit line on `runner`; (its printed lines, the lines, the status)."""
    from score import __main__ as command
    printed = io.StringIO()
    with contextlib.redirect_stdout(printed):
        lines, status = command.run_with_exit_line(runner, places, whole, run_options(**options), ["run", "world1"])
    return printed.getvalue().splitlines(), lines, status


@pytest.fixture
def run_registry(monkeypatch):
    """The run registry in a folder of the test's own."""
    folder = pathlib.Path(tempfile.mkdtemp())
    monkeypatch.setattr(runs, "RUNS", folder)
    return folder


def test_a_run_ends_with_one_exit_line_after_its_line_states_whatever_ends_it(monkeypatch, run_registry):
    """Review (C8): the exit line came before the closing status; `exit: ok` was said for a run that ended with 1;
    a run that raised said none. Batch 1 (2026-10-25): a run past its last node never released its pool. One node
    stopped of 2 lines, 3 rows ran, 1 not run.
    Break: score/__main__.py: '        print(f"exit: {status}", flush=True)' -> '        pass'"""
    from score import __main__ as command
    released = []
    monkeypatch.setattr(command, "release_pool", lambda run_id: released.append(run_id))
    printed, lines, _ = run_printing(slow_runner(0.2), ["hangar"])
    assert printed[-2:] == ["hangar: done", "exit: ok, 1 of 1 lines done, 1 rows ran"], printed
    assert lines["hangar"][0] == "done" and released == [os.environ[command.RUN_ID]], released
    printed, lines, _ = run_printing(a_driven_runner({"hangar": "explode", "station": "a hub"}), list(PLACES))
    assert printed[-1] == "exit: stopped, 1 of 2 lines done, 1 stopped, 3 rows ran, 1 not run", printed
    assert lines["hangar"][0].startswith("stopped at clean@hangar")
    runner = slow_runner(0.2)

    def broken(*arguments, **options):
        raise RuntimeError("the store is unreadable")
    runner.lines = broken
    printed = io.StringIO()
    with contextlib.redirect_stdout(printed), pytest.raises(RuntimeError):
        command.run_with_exit_line(runner, ["hangar"], False, run_options(), ["run", "world1"])
    assert printed.getvalue().splitlines()[-1] == "exit: error: RuntimeError: the store is unreadable"


def test_a_run_stopped_by_sigterm_ends_with_its_exit_line(run_registry):
    """Break: score/__main__.py: '        print(f"exit: {status}", flush=True)' -> '        pass'"""
    from score import __main__ as command
    said = pathlib.Path(tempfile.mkdtemp()) / "said.txt"

    def driving():
        sys.stdout = said.open("a", buffering=1)
        stopped.stop_on_signals(lambda number: print(f"score run: stopped by signal {number}", flush=True))
        command.run_with_exit_line(slow_runner(5), ["hangar"], False, run_options(), ["run", "world1"])
    process = graph.FORK.Process(target=driving)
    process.start()
    time.sleep(1)
    os.kill(process.pid, signal.SIGTERM)
    process.join(30)
    lines = said.read_text().splitlines()
    assert process.exitcode == 143, process.exitcode
    assert lines[-2:] == ["score run: stopped by signal 15", "exit: stopped by signal 15, exit 143"], lines


def test_the_run_gauges_count_only_this_runs_rows_its_pool_and_its_google_calls(monkeypatch):
    """Review (C8): the gauges summed every worktree's batches and every open paid run. Fault of 2026-10-24: the
    heartbeat said EUR 2.31 while the pool and Pro close-ups cost ten times that; 2026-10-25: the gauges were made
    before the run took its id. This run's rows: 2.50 (k1; k3 is another worktree's, k4 before the run); its pool
    3.00 + 0.50 (a frozen copy's line of its pool); its calls 2.00 + the unfinished one's estimate 0.15.
    Break: score/__main__.py: '        euros = spent_by_run(compute.ledger(), nodes, started, os.environ.get(RUN_ID))' -> '        euros = spent_by_run(compute.ledger(), nodes, started, None)'"""
    from score import __main__ as command
    books = compute.ledger()
    runner = slow_runner(0)
    here = books.origin()["worktree"]
    rows = [{"worktree": here, "ticket": "slow@hangar k1", "started": "2026-10-17T10:00:00Z", "euros": 2.5},
            {"worktree": here, "ticket": "other@far k2", "started": "2026-10-17T10:00:00Z", "euros": 7.0},
            {"worktree": "elsewhere", "ticket": "slow@hangar k3", "started": "2026-10-17T10:00:00Z", "euros": 9.0},
            {"worktree": here, "ticket": "slow@hangar k4", "started": "2026-10-17T08:00:00Z", "euros": 4.0},
            {"worktree": here, "ticket": "gpu-pool run-g", "started": "2026-10-17T10:01:00Z", "euros": 3.0,
             "run": "run-g", "kind": "pool-hold"},
            {"worktree": "frozen-other", "ticket": "gpu-pool run-g", "started": "2026-10-17T10:02:00Z", "euros": 0.5},
            {"worktree": here, "ticket": "gpu-pool other-run", "started": "2026-10-17T10:02:00Z", "euros": 9.0}]
    monkeypatch.setattr(books, "entries", lambda: rows)
    held = {graph.now(): {"node": "slow@hangar"}}
    held[graph.now()] = {"node": "other@far"}
    (runner.store.cache.parent / "reservations.json").write_text(json.dumps(held))
    google_spend = command.cloud_tool("google_spend")
    monkeypatch.setattr(google_spend, "write", google_spend.write)
    monkeypatch.setattr(books, "record", books.record)
    google_spend.LEDGER.unlink(missing_ok=True)  # the sandbox's
    google_spend.started("gemini-3-pro-image", "another run's")  # untagged: not this run's
    for name in (command.RUN_ID, command.LEDGER_TAG, "PYTHONPATH"):
        monkeypatch.delenv(name, raising=False)
    try:
        gauges = command.run_gauges(runner, ["hangar"], False, None, "2026-10-17T09:00:00Z")  # before the run's id
        monkeypatch.setenv(command.RUN_ID, "run-g")
        command.tag_ledgers()
        assert os.environ[command.LEDGER_TAG] == "run-g" and "ledger_tag" in os.environ["PYTHONPATH"]
        google_spend.started("gemini-3-pro-image", "pro")  # never finished: its estimate, 0.15
        google_spend.record("gemini-3-pro-image", "pro", {"usageMetadata": {"promptTokenCount": 1000000}},
                            google_spend.started("gemini-3-pro-image", "pro"))  # EUR 2.00
        said = gauges()
    finally:
        sys.meta_path[:] = [finder for finder in sys.meta_path if type(finder).__name__ != "Tagging"]
    assert said.startswith("this run's rows: paid runs open 1, "), said
    parts = {part: float(value) for part, value in re.findall(r"(rows|pool|model calls) ([\d.]+)", said)}
    assert parts == {"rows": 2.5, "pool": 3.5, "model calls": 2.15}, said
    assert "EUR 8.15 in the ledger" in said, said


def test_a_stopped_run_closes_its_pool_first_and_a_hung_release_is_left_so_the_run_ends(monkeypatch):
    """2026-10-24 (second Buy): the detached wrapper waited 40 s, the run spent 30 of them in its grace before its
    pool release and was SIGKILLed into it, and the pool rented cards at the stop; Batch 1 (2026-10-25): a hung
    release kept the run from its exit line. The wrapper's wait holds the release and the grace.
    Break: score/__main__.py: '    release.join(POOL_RELEASE_SECONDS)' -> '    release.join()'"""
    from score import __main__ as command
    assert command.POOL_RELEASE_SECONDS + command.STOP_GRACE_SECONDS < stopped.FORWARD_WAIT_SECONDS
    said = []
    with monkeypatch.context() as patched:
        patched.setattr(command, "release_pool", lambda run_id: said.append(("pool released", run_id)))
        patched.setattr(command, "end_group", lambda: said.append(("group ended",)) or ([], []))
        patched.setenv(command.RUN_ID, "run-stopped-test")
        with contextlib.redirect_stdout(io.StringIO()):
            command.stop_run(15)
    assert said == [("pool released", "run-stopped-test"), ("group ended",)]
    hung, asked, printed = threading.Event(), [], io.StringIO()
    monkeypatch.setattr(command, "cloud_tool", lambda name: types.SimpleNamespace(
        release=lambda run_id: asked.append(run_id) or hung.wait(20)))
    monkeypatch.setattr(command, "POOL_RELEASE_SECONDS", 0.2)
    started = time.monotonic()
    try:
        with contextlib.redirect_stdout(printed):
            command.release_pool("run-hung-release")
    finally:
        hung.set()
    assert asked == ["run-hung-release"] and time.monotonic() - started < 2
    assert "the pool's release did not end in 0.2 s" in printed.getvalue(), printed.getvalue()


def test_the_watchdog_stops_a_run_whose_drive_has_not_moved():
    """Batch 1 (2026-10-25): its drive sat in one pass over an hour after its last heartbeat.
    Break: score/__main__.py: '                os.kill(os.getpid(), signal.SIGTERM)\n                return' -> '                return'"""
    from score import __main__ as command
    stopped_by = threading.Event()
    before = signal.signal(signal.SIGTERM, lambda number, frame: stopped_by.set())
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            with command.watching(types.SimpleNamespace(driving=(1, time.monotonic())), stall=5, every=0.05):
                assert not stopped_by.wait(0.3)
            with command.watching(types.SimpleNamespace(driving=(0, time.monotonic() - 10)), stall=5, every=0.05):
                assert stopped_by.wait(5)
    finally:
        signal.signal(signal.SIGTERM, before)


def test_a_row_running_past_its_minutes_keeps_its_readers_off_the_pool(monkeypatch):
    """Batch 1 try 5 (2026-10-26): finish lists forecast at 3.7 min waited 18 to 43 min on Google's Batch API queue,
    and counted at their whole 3.7 min kept every bake reading them due: 13 machines parked idle 30 min. The list's
    likely 4 min, the bake's lead 8: started 1 min ago it has 3 left, the bake due; run 20 min it has overrun 16, as
    long again is past the lead, the bake not due; not started it counts its whole 4.
    Break: score/__main__.py: '    return abs(likely - ran)' -> '    return likely'"""
    from score import __main__ as command
    reads = {"list@a": [], "bake@a": ["list@a"]}
    runner = types.SimpleNamespace(
        store=types.SimpleNamespace(current_accept=lambda node: None),
        nodes_named=lambda names: iter([(name, None) for name in names]),
        earlier=lambda node, _place: reads[node],
        desk=lambda area, node, ending: pathlib.Path(tempfile.gettempdir()) / "no-such-fault" / f"{node}{ending}",
        began={})
    leads = {False: 8.0, True: 8.0}
    monkeypatch.setattr(command, "POOLED_ROWS", [("bake@a", "a", 1, False)])
    monkeypatch.setattr(command, "PAID_MINUTES", {"list@a": 4.0, "bake@a": 7.0})
    started = time.time() - 3600
    assert command.due_rows(runner, started, leads) == [("a", 1, False)]
    runner.began["list@a"] = time.time() - 60
    assert command.due_rows(runner, started, leads) == [("a", 1, False)]
    runner.began["list@a"] = time.time() - 20 * 60
    assert command.due_rows(runner, started, leads) == []


def test_the_pool_rents_each_machine_its_start_up_before_its_first_job_and_says_an_empty_one(monkeypatch):
    """Owner, 2026-10-25: "cant u just do the start up earlier then when u need them again" (Batch 1: machines idle an
    hour). Close-ups 150 min ahead: nothing due; ended: Pixal3D due now, the bake 30 min on (model 30) is not within
    its 8 min lead, at model 6 it is; the judge 40 min away (finish 40) waits, at finish 5 it is held; a row reading a
    stopped one is never due. Fault of 2026-10-26: rows waited an hour on a pool with no machine, said nowhere: said
    after 10 min, again only 10 min on, why it is empty, quiet once a machine is in.
    Break: score/__main__.py: '        if not ended_since(runner, node, started) and due(node) <= leads[on]:' -> '        if not ended_since(runner, node, started):'"""
    from score import __main__ as command
    reads = {"close@a": [], "model@a": ["close@a"], "bake@a": ["model@a"], "pixal@a": ["close@a"],
             "finish@a": ["pixal@a"], "judge@a": ["finish@a"]}
    started, standing = time.time() - 60, {}

    def ends(node):
        standing[node] = {"at": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    runner = types.SimpleNamespace(
        store=types.SimpleNamespace(current_accept=standing.get),
        nodes_named=lambda names: iter([(name, None) for name in names]),
        earlier=lambda node, _place: reads[node],
        desk=lambda area, node, ending: pathlib.Path(tempfile.gettempdir()) / "no-such-fault" / f"{node}{ending}",
        began={})
    leads = {False: 8.0, True: 8.0}
    monkeypatch.setattr(command, "POOLED_ROWS", [("bake@a", "a", 2, True), ("pixal@a", "a", 3, False),
                                                 ("judge@a", "j", 1, False)])
    monkeypatch.setattr(command, "PAID_MINUTES", {"close@a": 150.0, "model@a": 30.0, "bake@a": 20.0, "pixal@a": 60.0,
                                                  "finish@a": 40.0, "judge@a": 10.0})
    assert command.due_rows(runner, started, leads) == []
    ends("close@a")
    assert command.due_rows(runner, started, leads) == [("a", 3, False)]
    command.PAID_MINUTES["model@a"] = 6.0
    assert ("a", 2, True) in command.due_rows(runner, started, leads)
    for node in ("pixal@a", "model@a", "bake@a"):
        ends(node)
    assert command.due_rows(runner, started, leads) == []
    command.PAID_MINUTES["finish@a"] = 5.0
    assert command.due_rows(runner, started, leads) == [("j", 1, False)]
    chain_of = {"c": ["b"], "b": ["a"], "a": []}
    assert command.due_in("c", chain_of.get, lambda node: 10.0, lambda node: "stopped" if node == "a" else "todo",
                          {}) == float("inf")
    state = {"members": [], "plan": {"collector": os.getpid()}}
    pool = types.SimpleNamespace(members=lambda run_id: state["members"], current=lambda run_id: state["plan"],
                                 collector_alive=lambda plan: True,
                                 collector_said=lambda run_id: "[cloud] pool: 1 card(s) short, none in stock")
    step = command.POOL_EMPTY_SAY_SECONDS

    def said(now):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            command.said_empty_pool(pool, "run", [("a", 3, False)], now)
        return out.getvalue()
    monkeypatch.setattr(command, "POOL_EMPTY", {})
    assert said(1000.0) == "" and said(1000.0 + step - 1) == ""
    line = said(1000.0 + step)
    assert "no machine for 10 min while 1 row is due" in line and "none in stock" in line, line
    assert said(1000.0 + step + 60) == ""
    state["plan"] = None
    assert "it is closed" in said(1000.0 + 2 * step)
    state["members"] = [{"id": "card-1"}]
    assert said(1000.0 + 3 * step) == "" and command.POOL_EMPTY == {}


# --- the run registry: a run a reboot cut off is started again from its own code, and nothing else (C9) ------------

EARLIER_BOOT = "00000000-0000-0000-0000-000000000000"


@pytest.fixture(autouse=True)
def no_live_store_sweep(monkeypatch):
    """C9 review: a resume with no `swept` deleted .partial files in the real store; a test passes swept=()."""
    def refused():
        raise AssertionError("a test swept the live store's .partial files: pass swept=()")
    monkeypatch.setattr(runs, "store_roots", refused)


def a_worktree(python=None):
    """A clean committed git worktree of the test's own (its .venv ignored), `python` as its .venv/bin/python when
    given; the folder and its commit."""
    worktree = pathlib.Path(tempfile.mkdtemp())
    (worktree / ".gitignore").write_text(".venv/\nstarts\n")
    if python is not None:
        (worktree / ".venv/bin").mkdir(parents=True)
        (worktree / ".venv/bin/python").write_text(python)
        (worktree / ".venv/bin/python").chmod(0o755)
    git = ["git", "-C", str(worktree), "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false"]
    for command in (["init", "-q"], ["add", "-A"], ["commit", "-q", "-m", "the run's code"]):
        subprocess.run([*git, *command], check=True)
    return worktree, runs.commit_of(worktree)


def an_entry(folder, name, **fields):
    entry = {"id": name, "argv": ["run", "world1", "--place", "hangar"], "commit": "c0ffee", "worktree": str(REPO),
             "pid": 1, "boot": EARLIER_BOOT, "started": "2026-10-17T08:00:00+00:00", "state": runs.RUNNING, **fields}
    (folder / f"{name}.json").write_text(json.dumps(entry))
    return entry


STARTS = '#!/bin/sh\necho "detached: started in $(pwd) with $*"; echo started >> "$PWD/starts"\n'


def test_resume_starts_only_a_run_an_earlier_boot_cut_off_from_its_own_unchanged_worktree():
    """C9: PC reboots lost runs; review: resume ran whatever a worktree had checked out days later, a run the owner
    stopped, one OOM-killed long before. Listed by `score resume --dry` (marking none): the cut-off run; skipped: one
    whose worktree moved on. Started detached from its own worktree and marked resumed, never twice; one moved on,
    changed, gone, silent over 12 h before the boot or whose restart fails is marked unresumable with why.
    Break: score/graph/runs.py: '    if not entry.get("commit") or head != entry["commit"]:' -> '    if not entry.get("commit"):'"""
    home = pathlib.Path(tempfile.mkdtemp())
    worktree, commit = a_worktree()
    (home / "runs").mkdir()
    an_entry(home / "runs", "cut-off", worktree=str(worktree), commit=commit)
    an_entry(home / "runs", "other-commit", worktree=str(worktree), commit="c0ffee")
    an_entry(home / "runs", "finished", state=runs.ENDED)
    an_entry(home / "runs", "stopped-by-the-owner", state=runs.STOPPED)
    an_entry(home / "runs", "this-boot", boot=runs.boot_id())
    an_entry(home / "runs", "before-boots-were-kept", boot=None)
    done = subprocess.run([sys.executable, "-m", "score", "resume", "--dry"], cwd=REPO, capture_output=True,
                          text=True, env={**os.environ, "PROPS_HOME": str(home)})
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip().splitlines() == [
        f"would resume cut-off: worktree={worktree} commit={commit[:12]} argv=run world1 --place hangar",
        f"would skip other-commit: worktree={worktree} commit=c0ffee argv=run world1 --place hangar: "
        f"its worktree is at {commit[:12]}, not the commit that registered it"], done.stdout
    assert {entry["state"] for entry in runs.entries(home / "runs").values()} == {runs.RUNNING, runs.ENDED,
                                                                                   runs.STOPPED}
    folder = pathlib.Path(tempfile.mkdtemp())
    worktree, commit = a_worktree(STARTS)
    entry = an_entry(folder, "cut-off", worktree=str(worktree), commit=commit)
    assert runs.restart_command(entry) == [str(worktree / ".venv/bin/python"), "-m", "score", *entry["argv"],
                                           "--detach"]
    said = []
    assert runs.resume(False, said.append, folder=folder, swept=()) == 1
    assert said[0].startswith("resumed cut-off") and f"started in {worktree} with -m score run" in said[0], said
    assert runs.entries(folder)[folder / "cut-off.json"]["state"] == runs.RESUMED and runs.stranded(folder) == {}
    (worktree / "starts").unlink()
    an_entry(folder, "moved-on", worktree=str(worktree), commit="c0ffee")
    an_entry(folder, "orphan", worktree=str(folder / "gone"))
    an_entry(folder, "killed-days-ago", worktree=str(worktree), commit=commit)
    silent = runs.boot_time() - runs.RESUME_WINDOW - 60
    os.utime(folder / "killed-days-ago.json", (silent, silent))
    runs.resume(False, said.append, folder=folder, swept=())
    (worktree / "stage.py").write_text("changed = True\n")
    an_entry(folder, "changed", worktree=str(worktree), commit=commit)
    runs.resume(False, said.append, folder=folder, swept=())
    refusing, refused_commit = a_worktree('#!/bin/sh\necho "refused: re-buys over EUR 5" >&2; exit 1\n')
    an_entry(folder, "refused", worktree=str(refusing), commit=refused_commit)
    runs.resume(False, said.append, folder=folder, swept=())
    assert not (worktree / "starts").exists(), said
    whys = {path.stem: entry.get("why", "") for path, entry in runs.entries(folder).items()
            if entry["state"] == runs.UNRESUMABLE}
    assert set(whys) == {"moved-on", "orphan", "killed-days-ago", "changed", "refused"}, whys
    for name, why in (("moved-on", "not the commit that registered it"), ("orphan", "worktree is gone"),
                      ("killed-days-ago", "last sign of life"), ("changed", "changes not committed"),
                      ("refused", "refused: re-buys")):
        assert why in whys[name], (name, whys[name])
    assert runs.stranded(folder) == {}  # never tried again
    assert sorted(line.split(":")[0] for line in runs.unresumable(folder)) == sorted(whys)


def test_two_resumes_at_once_start_a_run_once_and_a_resume_clears_an_earlier_boots_partial_writes():
    """C9 review: a write cut by a reboot leaves its .partial file, and nothing removed it; one of this boot is a
    write going on now.
    Break: score/graph/runs.py: '    with locked(folder / ".resume.lock"):' -> '    with contextlib.nullcontext():'"""
    folder = pathlib.Path(tempfile.mkdtemp())
    worktree, commit = a_worktree('#!/bin/sh\nsleep 0.3; echo started >> "$PWD/starts"\n')
    an_entry(folder, "cut-off", worktree=str(worktree), commit=commit)
    both = [threading.Thread(target=runs.resume, args=(False, quiet), kwargs={"folder": folder, "swept": ()})
            for _ in range(2)]
    for each in both:
        each.start()
    for each in both:
        each.join()
    assert (worktree / "starts").read_text().splitlines() == ["started"]
    objects = pathlib.Path(tempfile.mkdtemp())
    old = partial_of(objects / "records/clean@hangar/k1.json")
    old.write_text("{")
    os.utime(old, (runs.boot_time() - 60, runs.boot_time() - 60))
    new = partial_of(objects / "records/clean@hangar/k2.json")
    new.write_text("{")
    said = []
    runs.resume(False, said.append, folder=pathlib.Path(tempfile.mkdtemp()), swept=(objects,))
    assert not old.exists() and new.exists() and any(str(old) in line for line in said), said


def test_a_registered_run_is_stopped_by_its_owner_and_left_running_by_a_shutdown_or_a_resize(monkeypatch):
    """C9 review: Ctrl-C, a kill or a closed session left a run `running`, for resume to buy again what the owner
    stopped. A SIGTERM while the machine shuts down, or in a resize the size timer asked for, leaves it as it was;
    the owner's SIGTERM outside one, or to a run registered after the ask, stops it.
    Break: score/graph/runs.py: '    if number == signal.SIGTERM and (shutting_down() or conductor.resizing(registered=registered_at(path))):' -> '    if shutting_down() or conductor.resizing(registered=registered_at(path)):'"""
    from score import conductor
    folder = pathlib.Path(tempfile.mkdtemp())
    path = runs.register(["run", "world1", "--detach", "--jobs", "2"], folder=folder)
    entry = json.loads(path.read_text())
    assert entry["argv"] == ["run", "world1", "--jobs", "2"] and entry["pid"] == os.getpid()
    assert entry["worktree"] == str(REPO) and entry["commit"] == git_out("rev-parse", "HEAD")[0] and entry["state"] == runs.RUNNING
    assert entry["boot"] == runs.boot_id() and runs.stranded(folder) == {}
    path.unlink()
    for number, down, state in ((signal.SIGINT, True, runs.STOPPED), (signal.SIGHUP, True, runs.STOPPED),
                                (signal.SIGTERM, False, runs.STOPPED), (signal.SIGTERM, True, runs.RUNNING)):
        monkeypatch.setattr(runs, "shutting_down", lambda: down)
        path = runs.register(["run", "world1"], folder=folder)
        runs.stopped_by(path, number)
        assert runs.entries(folder)[path]["state"] == state, (number, down)
        path.unlink()
    monkeypatch.setattr(runs, "shutting_down", lambda: False)
    monkeypatch.setattr(conductor, "RESIZING", folder / "resizing.json")
    for marked, state in ((0, runs.WAITING), (-conductor.RESIZE_WINDOW - 60, runs.STOPPED), (None, runs.STOPPED),
                          (60, runs.STOPPED)):
        path = runs.register_waiting(["run", "world1", "--jobs", "16"], 16, folder=folder)
        if marked is not None:
            asked = runs.registered_at(path) - 60 if marked == 60 else time.time() + marked
            conductor.RESIZING.write_text(json.dumps({"action": "grow", "at": asked}))
        runs.stopped_by(path, signal.SIGTERM)
        assert runs.entries(folder)[path]["state"] == state, (marked, state)
        path.unlink()
        conductor.RESIZING.unlink(missing_ok=True)


def test_score_run_stopped_as_it_registers_or_while_it_drives_registers_as_stopped(monkeypatch, run_registry):
    """C9 review: the entry was written before the stopping signals were handled, so a Ctrl-C in between left it
    `running`, for a later boot to buy again.
    Break: score/__main__.py: '        if code > 128 and path.exists():' -> '        if False:'"""
    from score import __main__ as command
    handlers = {number: signal.getsignal(number) for number in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP)}
    written = runs.written

    class Driving:
        def drive(self, *arguments, **options):
            os.kill(os.getpid(), signal.SIGINT)

    def written_then_stopped(path, entry):
        written(path, entry)
        os.kill(os.getpid(), signal.SIGINT)
        return path
    try:
        for runner, as_written in ((Driving(), written), (object(), written_then_stopped)):
            monkeypatch.setattr(runs, "written", as_written)
            for path in run_registry.glob("*.json"):
                path.unlink()
            stopped.stop_on_signals(lambda number: None)  # as_run's handlers, installed before driven
            with pytest.raises(SystemExit) as stop:
                command.driven(runner, [], True, argparse.Namespace(jobs=1, stage=None), ["run", "world1"])
            assert stop.value.code == 128 + signal.SIGINT
            assert [entry["state"] for entry in runs.entries(run_registry).values()] == [runs.STOPPED]
    finally:
        for number, handler in handlers.items():
            signal.signal(number, handler)


def test_a_run_waiting_for_size_is_left_on_too_few_cores_and_resumed_on_the_batch_size(monkeypatch):
    """The conductor: a run asking for 16 jobs waits for the grow; a boot on 2 cores leaves it, one on 16 starts it
    and keeps the resumed run's pid and log on the entry, so the cockpit follows its launch to the resumed run's end.
    Break: score/graph/runs.py: '    if entry.get("state") == WAITING and entry.get("jobs", 0) > (os.cpu_count() or 1):' -> '    if False:'
    Break: score/graph/runs.py: '    started = STARTED.search(done.stdout)' -> '    started = None'"""
    folder = pathlib.Path(tempfile.mkdtemp())
    worktree, commit = a_worktree('#!/bin/sh\necho "detached: started pid=4242 log=/logs/$*"\n')
    an_entry(folder, "waiting", worktree=str(worktree), commit=commit, state=runs.WAITING, jobs=16,
             argv=["run", "world1", "--jobs", "16"])
    an_entry(folder, "waiting-this-boot", state=runs.WAITING, jobs=16, boot=runs.boot_id())
    assert list(runs.stranded(folder)) == [folder / "waiting.json"]
    said = []
    monkeypatch.setattr(os, "cpu_count", lambda: 2)
    assert runs.resume(False, said.append, folder=folder, swept=()) == 1
    assert said[0].startswith("left waiting") and "still waiting for size: it asks for 16 jobs" in said[0], said
    assert runs.entries(folder)[folder / "waiting.json"]["state"] == runs.WAITING
    monkeypatch.setattr(os, "cpu_count", lambda: 16)
    said.clear()
    runs.resume(False, said.append, folder=folder, swept=())
    assert said[0].startswith("resumed waiting") and "--jobs 16 --detach" in said[0], said
    resumed = runs.entries(folder)[folder / "waiting.json"]
    assert resumed["state"] == runs.RESUMED and resumed["jobs"] == 16, resumed
    assert resumed["resumed"] == {"pid": 4242, "log": "/logs/-m score run world1 --jobs 16 --detach"}, resumed
    assert [entry["id"] for entry in runs.waiting(folder).values()] == ["waiting-this-boot"]


def test_a_driving_run_touches_its_entry_so_resume_knows_it_was_alive(monkeypatch):
    """Break: score/graph/runs.py: '                os.utime(path)' -> '                pass'"""
    folder = pathlib.Path(tempfile.mkdtemp())
    path = runs.register(["run", "world1"], folder=folder)
    os.utime(path, (1, 1))
    monkeypatch.setattr(runs, "HEARTBEAT", 0.05)
    with runs.beating(path):
        time.sleep(0.3)
    assert path.stat().st_mtime > 1


# --- one commit per store (C10): a live run of another commit, or of the same commit making the same nodes, refuses

@pytest.fixture
def other():
    """A live process standing for another run (this test's own pid is the registering run's)."""
    process = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    yield process
    process.kill()
    process.wait()


def a_dead_pid():
    process = subprocess.Popen([sys.executable, "-c", "pass"])
    process.wait()
    return process.pid


def test_one_commit_holds_a_store_and_a_run_at_it_joins_only_with_other_nodes(other):
    """Fault (2026-10-17): two runs at different code over one store re-made each other's rows for 6 hours. A dead
    pid, a reused one (another start time) or a released run frees the store; the claims are never read as a run.
    Break: score/graph/runs.py: '            if entry.get("started") is not None and start_time(int(pid)) == entry["started"]}' -> '            }'"""
    folder = pathlib.Path(tempfile.mkdtemp()) / "runs"
    assert runs.claim("aaa111", ["draw@hangar"], other.pid, worktree="/work/one", folder=folder) is None
    refused = runs.claim("bbb222", ["bake@garage"], os.getpid(), worktree="/work/two", folder=folder)
    assert refused == (f"refused: run pid {other.pid} from commit aaa111 in /work/one is live on this store; this run "
                       "is at bbb222. Wait for it to end or stop it.")
    assert runs.claim_refusal("bbb222", ["bake@garage"], folder=folder) == refused
    assert runs.claim("aaa111", ["draw@garage"], os.getpid(), worktree="/work/two", folder=folder) is None
    runs.unclaim(os.getpid(), folder=folder)
    refused = runs.claim("aaa111", ["draw@hangar", "draw@garage"], os.getpid(), worktree="/work/two", folder=folder)
    assert refused == (f"refused: run pid {other.pid} at the same commit in /work/one would also make 1 of these "
                       "nodes (draw@hangar)"), refused
    entries = json.loads((folder / runs.ACTIVE).read_text())
    entries[str(other.pid)]["started"] = "1"  # its pid now another process's
    (folder / runs.ACTIVE).write_text(json.dumps(entries))
    assert runs.claim("bbb222", ["draw@hangar"], os.getpid(), worktree="/work/two", folder=folder) is None
    runs.unclaim(os.getpid(), folder=folder)
    assert runs.claim("aaa111", ["draw@hangar"], a_dead_pid(), worktree="/work/one", folder=folder) is None
    assert runs.claim("bbb222", ["draw@hangar"], os.getpid(), worktree="/work/two", folder=folder) is None
    runs.unclaim(os.getpid(), folder=folder)
    assert runs.claim("aaa111", ["draw@hangar"], other.pid, worktree="/work/one", folder=folder) is None
    runs.unclaim(other.pid, folder=folder)
    assert runs.claim("bbb222", ["draw@hangar"], os.getpid(), worktree="/work/two", folder=folder) is None
    entry = an_entry(folder, "20261017T080000-1")
    assert (folder / runs.ACTIVE).exists() and list(runs.entries(folder).values()) == [entry]


def test_two_places_at_one_commit_both_run_once_the_nodes_they_share_stand(other):
    """Review of C10: every place reads environment nodes (terrain), so comparing every planned node refused the
    second `score run --place` always; only nodes a run would make count. A toy table: terrain read by each place.
    Break: score/graph/runs.py: '        return [node_name(stage, place) for stage, place in nodes if runner.standing(stage, place) is not None]' -> '        return [node_name(stage, place) for stage, place in nodes]'"""
    data, world = a_world_of(["airlock", "camp"])
    terrain = graph.Stage("terrain", "world", made_once(data), TEXT, MET)
    build = graph.Stage("build", "place", make_seen, TEXT, MET, after={"terrain": READS})
    runner = a_runner(world, a_store(), (terrain, build))
    airlock, camp = (runner.line_nodes([place], False) for place in ("airlock", "camp"))
    folder = pathlib.Path(tempfile.mkdtemp()) / "runs"
    assert runs.would_make(runner, airlock) == ["terrain", "build@airlock"]
    assert runs.claim("aaa111", runs.would_make(runner, airlock), other.pid, worktree="/work/one", folder=folder) is None
    refused = runs.claim("aaa111", runs.would_make(runner, camp), os.getpid(), worktree="/work/two", folder=folder)
    assert refused and "terrain" in refused, refused
    runs.unclaim(other.pid, folder=folder)
    assert runner.run_node(terrain, None) == ACCEPTED
    assert runs.claim("aaa111", runs.would_make(runner, airlock), other.pid, worktree="/work/one", folder=folder) is None
    assert runs.claim("aaa111", runs.would_make(runner, camp), os.getpid(), worktree="/work/two", folder=folder) is None
    runs.unclaim(os.getpid(), folder=folder)


def test_a_worktree_with_tracked_changes_is_refused_only_when_it_would_buy_and_registers_as_its_own_commit():
    """An untracked scratch file is not a change; a free run goes on as it is.
    Break: score/graph/runs.py: '    found = subprocess.run(["git", "-C", str(repo), "status", "--porcelain", "--untracked-files=no"],' -> '    found = subprocess.run(["git", "-C", str(repo), "status", "--porcelain"],'"""
    assert runs.dirty_refusal(True, uncommitted=False, paid=True)
    assert runs.dirty_refusal(True, uncommitted=True, paid=True) is None
    assert runs.dirty_refusal(True, uncommitted=False, paid=False) is None
    assert runs.dirty_refusal(False, uncommitted=False, paid=True) is None
    assert runs.identity("aaa111", True, "/work/one") != runs.identity("aaa111", True, "/work/two") != "aaa111"
    assert runs.identity("aaa111", False, "/work/one") == "aaa111"
    repo = pathlib.Path(tempfile.mkdtemp())
    for command in (["init", "-q"], ["commit", "-q", "--allow-empty", "-m", "one"]):
        subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t", *command], check=True)
    (repo / "scratch.txt").write_text("notes")
    assert not runs.tracked_changes(repo)
    (repo / "kept.txt").write_text("a")
    subprocess.run(["git", "-C", str(repo), "add", "kept.txt"], check=True)
    assert runs.tracked_changes(repo)


# --- a run's frozen copy of the code and its design (#45) -----------------------------------------------------------

GIT_ENV = {"GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "test@example.invalid", "GIT_COMMITTER_NAME": "test",
           "GIT_COMMITTER_EMAIL": "test@example.invalid"}


def a_repo():
    """A repository with one commit: a tracked stage.py and a .gitignore leaving out .venv."""
    repo = pathlib.Path(tempfile.mkdtemp())
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    (repo / "stage.py").write_text("SIZE = 1\n")
    (repo / ".gitignore").write_text(".venv\n")
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "one"], check=True, env={**os.environ, **GIT_ENV})
    return repo


def test_a_run_is_frozen_at_its_tree_as_it_started_and_a_pull_after_never_reaches_it(monkeypatch):
    """2026-10-20: earth-kit@airlock's 14 bake jobs thrown away when the main checkout was pulled under its run. A
    clean tree is frozen at HEAD; one with changes (an untracked file too) at one commit of the whole tree, HEAD its
    parent, neither index nor stash moved; the copy is clean, links the running venv, and is removed with its entry.
    Break: score/graph/frozen.py: '    if not git(repo, "status", "--porcelain"):' -> '    if True:'"""
    for env, value in GIT_ENV.items():
        monkeypatch.setenv(env, value)
    repo = a_repo()
    head = frozen.git(repo, "rev-parse", "HEAD")
    assert frozen.snapshot(repo) == (head, False)
    copy = frozen.make(repo, head, tempfile.mkdtemp())
    (repo / "stage.py").write_text("SIZE = 3\n")
    (repo / "new.py").write_text("NEW = True\n")
    assert (copy / "stage.py").read_text() == "SIZE = 1\n" and frozen.git(copy, "rev-parse", "HEAD") == head
    frozen.remove(copy)
    assert not copy.exists() and str(copy) not in frozen.git(repo, "worktree", "list")
    commit, changes = frozen.snapshot(repo)
    assert changes and commit != head and frozen.git(repo, "rev-parse", f"{commit}^") == head
    assert frozen.git(repo, "diff", "--cached", "--name-only") == "" and frozen.git(repo, "stash", "list") == ""
    copy = frozen.make(repo, commit, tempfile.mkdtemp())
    assert (copy / "stage.py").read_text() == "SIZE = 3\n" and (copy / "new.py").exists()
    if sys.prefix != sys.base_prefix:
        assert (copy / ".venv").resolve() == pathlib.Path(sys.prefix).resolve()
    assert frozen.git(copy, "status", "--porcelain") == ""
    frozen.remove(copy)
    copy = frozen.make(repo, head, tempfile.mkdtemp())  # 2026-10-26: a copy git cannot remove still goes (disk full)
    (copy / ".git").write_text("gitdir: /nowhere\n")
    frozen.remove(copy)
    assert not copy.exists()
    frozen.git(repo, "worktree", "prune")


def test_only_the_owner_removes_the_copy_ending_every_process_left_in_it_and_resume_gives_it_back(monkeypatch):
    """2026-10-26: six processes of a stopped run worked on in its copy for an hour and held the checkout. A node or
    nested command is frozen but not the owner; the owner's mark is not inherited; after handing on it removes
    nothing; it removes once; one process deaf to SIGTERM in the copy gets SIGKILL, another copy's is left.
    Break: score/graph/frozen.py: '    end([pid for pid, name in users(path.parent).items() if name == path.name])' -> '    end([])'"""
    repo = a_repo()
    copy = frozen.make(repo, frozen.git(repo, "rev-parse", "HEAD"), tempfile.mkdtemp())
    monkeypatch.setenv(frozen.FROZEN, str(copy))
    monkeypatch.setattr(frozen, "OWNED", {"path": None, "handed_on": False})
    monkeypatch.setattr(frozen, "END_GRACE_SECONDS", 0.5)
    assert frozen.inside() and frozen.claim() is None
    monkeypatch.setenv(frozen.OWNER, "1")
    assert frozen.claim() == copy and frozen.OWNER not in os.environ and frozen.owner_env()[frozen.OWNER] == "1"
    frozen.hand_on()
    frozen.remove_owned()
    assert copy.exists()
    other_copy = copy.parent / "another-run"
    other_copy.mkdir()
    sleep = [sys.executable, "-c", "import signal, time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(60)"]
    left, elsewhere = subprocess.Popen(sleep, cwd=copy), subprocess.Popen(sleep, cwd=other_copy)
    try:
        time.sleep(0.3)
        assert frozen.users(copy.parent) == {left.pid: copy.name, elsewhere.pid: other_copy.name}
        frozen.OWNED["handed_on"] = False
        frozen.remove_owned()
        assert left.wait(5) == -9 and not copy.exists() and elsewhere.poll() is None
        frozen.remove_owned()  # once only
    finally:
        elsewhere.kill()
        left.kill()
    copy = frozen.FOLDER / "20261020-181654-1"
    assert frozen.resumed_env(copy)[frozen.FROZEN] == str(copy) and frozen.resumed_env(copy)[frozen.OWNER] == "1"
    assert frozen.OWNER not in frozen.resumed_env(tempfile.mkdtemp())
    frozen.home_of(copy).mkdir(parents=True)
    assert frozen.resumed_env(copy)["PROPS_HOME"] == str(frozen.home_of(copy))


def a_home():
    """A home with a read-only design (one place's surface data, 58 takes) and a store folder."""
    home = pathlib.Path(tempfile.mkdtemp())
    (home / "design" / "surfaces").mkdir(parents=True)
    (home / "design" / "surfaces" / "hangar.json").write_text('{"takes": 58}')
    (home / "store").mkdir()
    for folder in (home / "design" / "surfaces", home / "design"):
        folder.chmod(0o555)
    return home


def sync_pass_rewrites(home):
    """A sync pass's prepare mid-run: the surface data rewritten in the real design, 62 takes."""
    folder = home / "design" / "surfaces"
    folder.chmod(0o755)
    (folder / "hangar.json").chmod(0o644)
    (folder / "hangar.json").write_text('{"takes": 62}')


def make_while_the_sync_pass_writes(inputs, out, seed, params):
    sync_pass_rewrites(pathlib.Path(params["home"]))
    (out / "palette.txt").write_text(inputs["surfaces"].read_text())


def test_a_runs_home_holds_its_design_as_it_started_and_shares_the_rest():
    """Batch 1, 2026-10-25: prepare rewrote every place's surface data mid-run; finish-route-list@street had "an input
    changed while it ran". The run's home keeps 58 takes while the real design says 62; its store is the shared one;
    the node made mid-rewrite keeps its key, the next run's home reads 62; once closed, the run's design is a link to
    the real one and what it made at its top level is moved into the real home.
    Break: score/graph/frozen.py: '            shutil.copytree(entry, own / "design", symlinks=True)' -> '            (own / entry.name).symlink_to(entry.resolve())'"""
    home = a_home()
    copy = pathlib.Path(tempfile.mkdtemp()) / "20261025-161109-1"
    own = frozen.home_copy(copy, home)
    stage = graph.Stage("palette", "place", make_while_the_sync_pass_writes, TEXT, PASSES,
                        files={"surfaces": "{home}/design/surfaces/{place}.json"}, params={"home": str(home)})
    store = a_store()

    def runner(root):
        return graph.Runner((stage,), graph.Environment("toy", 7, {"home": str(root)}), store,
                            model_record=lambda kind: {"kind": kind})
    before = runner(own).key(stage, "hangar")["key"]
    assert runner(own).run(["hangar"])["palette@hangar"].startswith("made: pass")
    assert (own / "design/surfaces/hangar.json").read_text() == '{"takes": 58}'
    assert runner(own).key(stage, "hangar")["key"] == before != runner(home).key(stage, "hangar")["key"]
    (own / "store" / "record.json").write_text("{}")
    assert (home / "store" / "record.json").exists()
    (own / "made").mkdir()
    frozen.home_closed(copy, home)
    assert (home / "made").is_dir() and (own / "made").is_symlink()
    assert (own / "design").is_symlink() and (own / "design/surfaces/hangar.json").read_text() == '{"takes": 62}'


# --- a free-only run: every free node runs, a paid one is left for the Buy, nothing is cleared ---------------------
# Fault (2026-10-25): the agents' door's free run refused as a whole at its start, so no free step was tried.

def make_paint(inputs, out, seed, params):
    raise AssertionError("a paid make ran in a free-only run")


def refused_clearance(*arguments, **options):
    raise AssertionError("a clearance was asked in a free-only run")


def free_runner():
    data, world = a_world_of(["hangar"])
    (data / "hangar" / "brief.txt").write_text("a ship")
    table = (graph.Stage("clean", "place", make_clean, TEXT, PASSES, files={"brief": "{data}/{place}/brief.txt"}),
             graph.Stage("paint", "place", make_paint, TEXT, PASSES, after={"clean": READS}, paid=True, euros=0.5),
             graph.Stage("count", "place", make_count, TEXT, PASSES, after={"paint": READS}))
    runner = a_runner(world, a_store(), table)
    runner.free_only = True
    return runner


def test_a_free_only_run_runs_its_free_nodes_leaves_its_paid_ones_and_ends_ok_with_its_list(monkeypatch,
                                                                                           run_registry):
    """Break: score/graph/__init__.py: '        if not (self.free_only and stage.paid) or on_this_pc():\n            return False' -> '        if True:\n            return False'"""
    from score import __main__ as command
    monkeypatch.setattr(compute, "clearance", refused_clearance)
    monkeypatch.setattr(command, "opened_pool", refused_clearance)
    runner = free_runner()
    found = runner.drive(["hangar"], say=quiet)
    assert found == {"clean@hangar": ACCEPTED, "paint@hangar": graph.PAID_LEFT,
                     "count@hangar": "not run: waits on paint@hangar, paid, left for the Buy"}, found
    assert not report_of(runner, "paint@hangar").exists()
    assert runner.lines(["hangar"], whole=False)["hangar"][0] == "waits at paint@hangar"
    with pytest.raises(graph.Blocked, match="left for the Buy"):
        free_runner().cleared("paint@hangar", 0.5)
    said, _, status = run_printing(free_runner(), ["hangar"], free=True)
    assert status.startswith("ok, free-only, 1 free rows stand, 0 failed, 1 paid rows left for the Buy"), said
    assert "  left for the Buy: paint@hangar" in said and "  waits on a paid row: count@hangar" in said, said


def test_a_free_only_run_on_this_pcs_card_makes_its_paid_nodes_with_no_ticket(monkeypatch, run_registry):
    """Break: score/graph/__init__.py: '        if self.free_only and on_this_pc():\n            return contextlib.nullcontext()' -> '        if False:\n            return contextlib.nullcontext()'"""
    monkeypatch.setattr(compute, "clearance", refused_clearance)
    monkeypatch.setenv("SCORE_CLOUD", "local")
    monkeypatch.delenv(compute.TICKET, raising=False)

    def make_paint_here(inputs, out, seed, params):
        (out / "paint.txt").write_text(f"ticket {os.environ.get(compute.TICKET)}")

    runner = free_runner()
    runner.stages["paint"] = dataclasses.replace(runner.stages["paint"], make=make_paint_here)
    found = runner.drive(["hangar"], say=quiet)
    assert found["paint@hangar"] == ACCEPTED, found  # made, not left for the Buy
    painted = runner.store.checkout(runner.store.accepted("paint@hangar")) / "paint.txt"
    assert painted.read_text() == "ticket None"  # no clearance: a real paid point inside it would refuse


# --- an optional read the run makes: the people line a place's cast reads ------------------------------------------
# Fault (Buy of 2026-10-24): no Buy held a people-* node, since the cast read the dress rows only as optional and an
# optional read not usable now was left out of the run's line; the people were never made.

def make_look(inputs, out, seed, params):
    if "explode" in inputs["brief"].read_text():
        raise RuntimeError("the look fell over")
    (out / "look.txt").write_text(inputs["brief"].read_text())


def make_dress(inputs, out, seed, params):
    (out / "dress.txt").write_text((inputs["look@people"] / "look.txt").read_text())


def make_cast(inputs, out, seed, params):
    (out / "cast.txt").write_text("dressed" if "dress" in inputs else "undressed")


def people_runner(text):
    """A look on the people line, a paid dress row of the environment reading it beside, a cast at each place reading
    the dress as optional."""
    data, world = a_world_of(["people"])
    (data / "people" / "brief.txt").write_text(text)
    look = graph.Stage("look", "place", make_look, TEXT, PASSES, files={"brief": "{data}/{place}/brief.txt"},
                       applies=lambda place: place == "people")
    dress = graph.Stage("dress", "world", make_dress, TEXT, PASSES, paid=True, euros=0.0, beside={"look": READS},
                        neighbours=lambda place: ["people"])
    cast = graph.Stage("cast", "place", make_cast, TEXT, PASSES, after={"dress": READS}, optional=("dress",),
                       applies=lambda place: place != "people")
    return a_runner(world, a_store(), (look, dress, cast))


def test_a_run_holds_prices_and_waits_on_the_optional_reads_it_makes_and_runs_without_one_that_stopped():
    """The people line's nodes are in the run whole or not, priced, and held for each place that reads them; the cast
    waits on its dress and takes it, and runs without it once its line stopped.
    Break: score/graph/__init__.py: '            for before in self.read_nodes(*reading.pop(), every=True):\n                if node_name(*before) not in names:\n                    names.add(node_name(*before))\n                    reading.append(before)\n        others' -> '            for before in self.read_nodes(*reading.pop(), every=False):\n                if node_name(*before) not in names:\n                    names.add(node_name(*before))\n                    reading.append(before)\n        others'"""
    runner = people_runner("a suit")
    for whole in (True, False):
        names = {graph.node_name(*node) for node in runner.line_nodes(PLACES, whole)}
        assert {"look@people", "dress", "cast@hangar", "cast@station"} <= names, (whole, names)
    assert [buy.node for buy in rebuy.buys(runner, runner.line_nodes(PLACES, False))] == ["dress"]
    held = rebuy.held_for(runner, runner.line_nodes(PLACES, True), set(PLACES))
    assert held["dress"] == held["look@people"] == set(PLACES) and held["cast@hangar"] == {"hangar"}, held
    found = runner.drive(PLACES, say=quiet, whole=False)
    assert found["dress"].startswith("made: pass"), found
    assert accepted_text(runner.store, "cast@hangar", "cast.txt") == "dressed"
    assert accepted_text(runner.store, "cast@station", "cast.txt") == "dressed"
    runner = people_runner("explode")
    found = runner.drive(PLACES, say=quiet, whole=False)
    assert found["dress"] == "not run: its line stopped at look@people", found
    assert accepted_text(runner.store, "cast@hangar", "cast.txt") == "undressed"


def make_rung(inputs, out, seed, params):
    (out / "rung.txt").write_text(str(len(inputs)))


def test_a_pass_of_the_drive_works_out_each_key_once():
    """Batch 1 (2026-10-25): each pass worked out its waiting nodes' optional reads' keys outside a `still` pass,
    once a path through every node they read; passes took over an hour and the pool billed. A ladder (each rung reads
    the two below) read as optional by a top row: no key in the drive's process worked out outside a pass, nor twice
    in one.
    Break: score/graph/__init__.py: '            with self.still():  # each key worked out once a pass' -> '            with contextlib.nullcontext():  # each key worked out once a pass'"""
    data, world = a_world_of(["hangar"])
    (data / "hangar" / "brief.txt").write_text("a rung")
    rungs = [graph.Stage("rung0", "place", make_look, TEXT, PASSES, files={"brief": "{data}/{place}/brief.txt"})]
    for number in range(1, 12):
        rungs.append(graph.Stage(f"rung{number}", "place", make_rung, TEXT, PASSES,
                                 after={f"rung{below}": READS for below in (number - 1, number - 2) if below >= 0}))
    top = graph.Stage("top", "place", make_cast, TEXT, PASSES, after={"rung11": READS}, optional=("rung11",))
    runner = a_runner(world, a_store(), (*rungs, top))
    drive_pid, worked, passes = os.getpid(), [], []
    work = runner.worked_out_key

    def counted(stage, place):
        if os.getpid() == drive_pid:
            if runner.remembered is not None and not any(seen is runner.remembered for seen in passes):
                passes.append(runner.remembered)
            worked.append((len(passes) if runner.remembered is not None else None, graph.node_name(stage, place)))
        return work(stage, place)
    runner.worked_out_key = counted
    found = runner.drive(("hangar",), say=quiet, whole=False)
    assert found["top@hangar"].startswith("made: pass"), found
    assert None not in {each for each, _ in worked}, worked
    assert len(worked) == len(set(worked)), sorted(worked)


# --- a gap's chain: every node its place still needs, for pricing ---------------------------------------------------
#     draw -> shape -> gap <- part (its input missing)
#     gap -> finish -> complete -> film,  gap -> aside (an end: nothing reads it)
#     people (optional to complete, not made), alone (an end of its own)

def make_copy(inputs, out, seed, params):
    source = inputs.get("brief") or next(path for name, path in inputs.items() if name != "brief")
    found = source if source.is_file() else next(source.glob("*.txt"))
    (out / "text.txt").write_text(found.read_text())


def chain_stage(name, after=(), paid=False, **more):
    return graph.Stage(name, "place", make_copy, TEXT, PASSES, after={before: READS for before in after}, paid=paid,
                       euros=1.0 if paid else None, **more)


CHAIN_TABLE = [chain_stage("draw", files={"brief": "{data}/{place}.txt"}), chain_stage("shape", ("draw",)),
               chain_stage("part", paid=True, files={"brief": "{data}/{place}-part.txt"}),
               chain_stage("gap", ("shape", "part"), paid=True), chain_stage("finish", ("gap",), paid=True),
               chain_stage("aside", ("gap",), paid=True), chain_stage("people", paid=True),
               chain_stage("complete", ("finish", "people"), optional=("people",)),
               chain_stage("film", ("complete",), paid=True), chain_stage("alone", paid=True)]


def chain_runner():
    """The chain table with draw and shape made and standing at the hangar; part's input is missing."""
    data = pathlib.Path(tempfile.mkdtemp())
    (data / "hangar.txt").write_text("a hall")
    runner = a_runner(graph.Environment("toy", 1, {"data": data}), a_store(), CHAIN_TABLE)
    for name in ("draw", "shape"):
        assert runner.run_node(runner.stages[name], "hangar").endswith("accepted automatically"), name
    return runner


def chained(runner, name):
    with runner.still():
        return chain.gap_chain(runner, runner.stages[name], "hangar", chain.readers(runner, ["hangar"]))


def test_a_gaps_chain_is_every_node_its_place_still_needs_up_to_its_lines_ends():
    """A node that stands is left out and ends its branch; one that cannot be keyed (part: no input) is in; later
    nodes are in up to the line's ends past the completion (film), an optional read too (people); an end not reading
    the gap's node (alone) is the line's, not the gap's.
    Break: score/graph/chain.py: '            if runner.standing(*before) is not None:' -> '            if True:'"""
    found = chained(chain_runner(), "gap")
    assert found == {"aside@hangar": True, "complete@hangar": False, "film@hangar": True, "finish@hangar": True,
                     "gap@hangar": True, "part@hangar": True, "people@hangar": True}, found
    runner = chain_runner()
    with runner.still():
        reading = chain.readers(runner, ["hangar"])
        assert sorted(end.name for end, _ in chain.ends(runner, "hangar", reading)) == ["alone", "aside", "film"]
        found = chain.line_chain(runner, "hangar", reading)
    assert found == {"aside@hangar": True, "alone@hangar": True, "film@hangar": True, "complete@hangar": False,
                     "finish@hangar": True, "gap@hangar": True, "part@hangar": True, "people@hangar": True}, found


def test_a_node_that_does_not_stand_is_walked_through_and_no_pass_holds_a_reading_over_to_the_next():
    """Break: score/graph/__init__.py: '            del self.store.objects.keys\n            self.remembered = None' -> '            del self.store.objects.keys'"""
    runner = chain_runner()
    with runner.still():
        files = runner.files_of(runner.stages["draw"], "hangar")
        assert "draw@hangar" not in chained(runner, "gap")
    assert files == {"brief": "{data}/{place}.txt"}
    (runner.world.roots["data"] / "hangar.txt").write_text("a bigger hall")  # draw's key moves: nothing stands
    found = chained(runner, "gap")
    assert {"draw@hangar", "shape@hangar", "part@hangar"} <= set(found) and found["draw@hangar"] is False, found


# --- what a run would buy, and the refusal of a dear re-buy without its reason --------------------------------------
# Fault (2026-10-12): one library change re-rendered every place and re-drew every view map, about EUR 50, unsaid.

DRAW = graph.Stage("draw", "place", make_copy, TEXT, PASSES, files={"brief": "{data}/{place}.txt"})
RENDER = graph.Stage("render", "place", make_copy, TEXT, PASSES, after={"draw": READS}, paid=True, euros=4.0)
BAKE = graph.Stage("bake", "place", make_copy, TEXT, PASSES, after={"render": READS}, paid=True, euros=3.0)


def a_buying_runner(render=RENDER):
    data = pathlib.Path(tempfile.mkdtemp())
    (data / "hangar.txt").write_text("a hall")
    return a_runner(graph.Environment("toy", 1, {"data": data}), a_store(), [DRAW, render, BAKE])


@pytest.fixture
def committed(monkeypatch):
    """Records made at a committed tree (same_requests reads their commit), the month's books open."""
    monkeypatch.setattr(_code, "git_commit", lambda: {"commit": "c0ffee", "uncommitted": False})
    monkeypatch.setattr(compute, "books_refusal", lambda: None)


def made(runner):
    for stage in runner.stages.values():
        assert runner.run_node(stage, "hangar").endswith("accepted automatically"), stage.name
    return runner


def bought(runner):
    return [(buy.node, buy.euros, buy.again) for buy in rebuy.buys(runner, list(runner.nodes(["hangar"])))]


def test_a_run_buys_each_paid_node_it_would_make_and_refuses_re_buys_over_five_euros_without_a_reason(committed):
    """Rows never made are buys (EUR 4 + 3) and never refuse; nothing changed buys nothing; a changed brief re-buys
    both (EUR 7: refused without a reason); a bake's code changed re-buys it alone (EUR 3: no reason needed); rows
    after a node kept by a proof are still buys (fault 2026-10-24: the greenhouse's kept plan hid its prop route).
    Break: score/graph/rebuy.py: '    if again > LIMIT and not (reason or "").strip():' -> '    if again > 2 * LIMIT and not (reason or "").strip():'"""
    runner = a_buying_runner()
    assert bought(runner) == [("render@hangar", 4.0, False), ("bake@hangar", 3.0, False)]
    assert rebuy.refusal(rebuy.buys(runner, list(runner.nodes(["hangar"]))), None) is None
    assert bought(made(runner)) == []
    (runner.world.roots["data"] / "hangar.txt").write_text("a bigger hall")
    found = rebuy.buys(runner, list(runner.nodes(["hangar"])))
    assert [(buy.node, buy.euros, buy.again) for buy in found] == [("render@hangar", 4.0, True),
                                                                   ("bake@hangar", 3.0, True)]
    assert "reads draw@hangar" in found[0].why and "EUR 7.00" in rebuy.refusal(found, None)
    assert rebuy.refusal(found, "the owner changed the hall's brief") is None
    entry = rebuy.ledger_entry(found, "the owner changed the hall's brief")
    assert (entry["kind"], entry["euros"], entry["estimate"]) == ("rebuy", 0, 7.0)
    runner = made(a_buying_runner())
    runner.code_versions["bake"] = "a bake changed"
    found = rebuy.buys(runner, list(runner.nodes(["hangar"])))
    assert [(buy.node, buy.euros) for buy in found] == [("bake@hangar", 3.0)] and "code changed" in found[0].why
    assert rebuy.refusal(found, None) is None
    runner = a_buying_runner()
    runner.run_node(DRAW, "hangar")
    runner.code_versions["draw"] = "only narrowed"
    runner.narrowing_proof = lambda stage, place, keyed: stage is DRAW
    assert [node for node, _, _ in bought(runner)] == ["render@hangar", "bake@hangar"]


def judge_dropped(output, inputs, evidence):
    if evidence is None:
        return checks.Verdict("dropped", checks.UNKNOWN, "no drop run")
    return checks.Verdict("dropped", checks.PASS, "dropped")


def gather_drop(output, inputs, folder):
    (folder / "drop.txt").write_text("still")
    return folder / "drop.txt"


def test_a_free_rows_paid_evidence_gather_is_a_buy_until_it_is_gathered(committed):
    """Buy of 2026-10-24: the likeness's DINOv2 and the assembly's drop run were spent at run time in no price. At its
    estimate (EUR 1.50) while the row will be made, and while its output waits on that evidence alone; then nothing.
    Break: score/graph/rebuy.py: '    paid = {name: euros for name, (_, euros) in stage.gatherers.items() if euros}' -> '    paid = {}'"""
    place = graph.Stage("place", "place", make_copy, TEXT, (checks.Check("dropped", judge_dropped,
                                                                         evidence="a drop run"),),
                        after={"draw": READS}, gatherers={"dropped": (gather_drop, 1.5)})
    data = pathlib.Path(tempfile.mkdtemp())
    (data / "hangar.txt").write_text("a hall")
    runner = a_runner(graph.Environment("toy", 1, {"data": data}), a_store(), [DRAW, place])
    found = rebuy.buys(runner, list(runner.nodes(["hangar"])))
    assert [(buy.node, buy.euros, buy.evidence) for buy in found] == [("place@hangar", 1.5, "dropped")], found
    assert "buy place@hangar evidence dropped: EUR 1.50" in rebuy.listing(found)
    runner.run_node(DRAW, "hangar")
    runner.run_node(place, "hangar")
    found = rebuy.buys(runner, list(runner.nodes(["hangar"])))
    assert [(buy.node, buy.why) for buy in found] == [("place@hangar", "evidence missing: dropped")], found
    runner.gather(place, "hangar", ["dropped"])
    assert rebuy.buys(runner, list(runner.nodes(["hangar"]))) == []


def make_with_rejects(inputs, out, seed, params):
    make_copy(inputs, out, seed, params)
    (out / rebuy.UNCACHED).write_text(json.dumps({"asks": 2, "euros": 0.134}))


def test_a_google_row_asking_the_same_is_cached_unless_its_wording_changed_or_it_dropped_answers(committed,
                                                                                                monkeypatch):
    """A render asking Google what it asked before is EUR 0 and moves nothing after it; a bake changed behind it is
    still bought; its wording changed, both are bought at their estimates. Owner, 2026-10-24: a close-up the shape
    check rejected leaves Google's cache, so the re-ask is priced at what the output names (EUR 0.134), never 0, and
    what reads it is bought too.
    Break: score/graph/rebuy.py: '            cached = stage.paid and same_requests(runner, stage, node, parts)' -> '            cached = False'"""
    runner = made(a_buying_runner())
    runner.code_versions["render"] = "a render changed"
    monkeypatch.setattr(rebuy, "asks_google", lambda stage: stage.name == "render")
    monkeypatch.setattr(rebuy, "builders_changed", lambda commit: False)
    found = rebuy.buys(runner, list(runner.nodes(["hangar"])))
    assert [(buy.node, buy.euros) for buy in found] == [("render@hangar", 0.0)] and "cached" in found[0].why
    runner.code_versions["bake"], runner.remembered = "a bake changed too", None
    assert [(node, euros) for node, euros, _ in bought(runner)] == [("render@hangar", 0.0), ("bake@hangar", 3.0)]
    del runner.code_versions["bake"]
    monkeypatch.setattr(rebuy, "builders_changed", lambda commit: True)
    assert [(node, euros) for node, euros, _ in bought(runner)] == [("render@hangar", 4.0), ("bake@hangar", 3.0)]
    monkeypatch.setattr(rebuy, "builders_changed", lambda commit: False)
    runner = made(a_buying_runner(dataclasses.replace(RENDER, make=make_with_rejects)))
    runner.code_versions["render"] = "a render changed"
    assert [(node, euros) for node, euros, _ in bought(runner)] == [("render@hangar", 0.134), ("bake@hangar", 3.0)]


def test_every_file_that_words_a_google_request_is_a_request_builder():
    """Audit (2026-10-22): the finish route's list, recheck, palette and library wordings were left out, so an edit
    there was priced as a cached ask at EUR 0 while the run paid again. A code walk, not a shape test of an output: a
    file that builds a request body (`def ..._body(`) and reaches Google through google_spend, google_batch or
    finish_ask is a builder, and so is the batch client.
    Break: score/graph/rebuy.py: '                    "score/stages/surfaces/body_faces.py")' -> '                    )'"""
    reaches = re.compile(r"^\s*(import|from)\s+(\S+\.)?(google_spend|google_batch|finish_ask)\b", re.MULTILINE)
    wording = re.compile(r"^\s*def \w+_body\(", re.MULTILINE)
    found = set()
    for path in [*(_code.REPO / "score/stages").rglob("*.py"), *(_code.REPO / "tools/props").rglob("*.py")]:
        text = path.read_text(errors="replace")
        if not path.name.endswith("_test.py") and not path.name.startswith("test_") and wording.search(text) and \
                reaches.search(text):
            found.add(str(path.relative_to(_code.REPO)))
    assert found and found <= set(rebuy.REQUEST_BUILDERS), sorted(found - set(rebuy.REQUEST_BUILDERS))
    assert "tools/cloud/google_batch.py" in rebuy.REQUEST_BUILDERS
    assert all((_code.REPO / builder).is_file() for builder in rebuy.REQUEST_BUILDERS)


def test_score_run_refuses_before_it_starts_records_a_given_reason_and_plans_on_the_runners_numbers(committed,
                                                                                                   monkeypatch):
    """`score run` lists and refuses a EUR 7 re-buy with no reason, writing nothing; given one, the ledger holds it.
    `score plan --json` keeps each estimate as the guess when unmeasured; with every row's minutes measured, the run's
    time is its longest row or its minutes over --jobs, whichever is longer (C3): 10+20+30 over 2 jobs is 30, over 1
    is 60.
    Break: score/__main__.py: '    refused = rebuy.refusal(bought, options.rebuy_reason)' -> '    refused = None'"""
    from score import __main__ as command
    books = compute.ledger()
    monkeypatch.setattr(books, "LEDGER", pathlib.Path(tempfile.mkdtemp()) / "ledger.jsonl")
    runner = made(a_buying_runner())
    (runner.world.roots["data"] / "hangar.txt").write_text("a bigger hall")
    options = argparse.Namespace(stage=None, rebuy_reason=None, detach=False, jobs=2)
    with contextlib.redirect_stdout(io.StringIO()) as printed, pytest.raises(SystemExit) as refusal:
        command.checked_buys(runner, ["hangar"], True, options)
    assert "refused" in str(refusal.value.code) and "re-buy render@hangar: EUR 4.00" in printed.getvalue()
    assert not books.LEDGER.exists()
    planned = command.plan_json(runner, ["hangar"], True, options)
    assert [(buy["node"], buy["euros"], buy["price"]["likely_euros"], buy["price"]["guess_euros"])
            for buy in planned["buys"]] == [("render@hangar", 4.0, None, 4.0), ("bake@hangar", 3.0, None, 3.0)]
    assert planned["price"] == {"likely_euros": 0.0, "high_euros": 0.0, "guessed_euros": 7.0, "guessed": 2,
                                "likely_minutes": None, "high_minutes": None, "measured": 0, "rows": 2, "jobs": 2}
    options.rebuy_reason = "the owner changed the hall's brief"
    with contextlib.redirect_stdout(io.StringIO()) as printed:
        command.checked_buys(runner, ["hangar"], True, options)
    assert "re-buy reason: the owner changed the hall's brief" in printed.getvalue()
    line = json.loads(books.LEDGER.read_text())
    assert line["reason"] == options.rebuy_reason and line["rebuys"] == {"render@hangar": 4.0, "bake@hangar": 3.0}
    timed = [{"likely_euros": 1.0, "high_euros": 2.0, "likely_minutes": minutes, "high_minutes": 2 * minutes,
              "runs": 3} for minutes in (10.0, 20.0, 30.0)]
    assert command.plan_price(timed, 2) == {"likely_euros": 3.0, "high_euros": 6.0, "guessed_euros": 0, "guessed": 0,
                                            "likely_minutes": 30.0, "high_minutes": 60.0, "measured": 3, "rows": 3,
                                            "jobs": 2}
    assert command.plan_price(timed, 1)["likely_minutes"] == 60.0
