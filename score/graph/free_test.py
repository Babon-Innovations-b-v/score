"""A free-only run (`score run --free`, every run under SCORE_FREE_ONLY=1): every free node whose inputs stand runs for
real, a paid node is left for the Buy (its line waits there, not an error) and nothing is cleared, and a free node after
it waits on it. A toy table of three stages, one place, in a store of its own.

Fault (2026-10-25): the agents' door's free run refused as a whole at its start (the warm pool's clearance raised
FreeOnly), so no free step was tried before the owner's Buy.

Run: .venv/bin/python -m pytest score/graph/free_test.py
"""
import argparse
import contextlib
import io
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from score import checks, contracts, graph  # noqa: E402
from score.adapters import compute  # noqa: E402

graph.AVAILABLE = lambda: 2**50  # toy nodes take no memory (memory_test.py proves the gate)
from score.store import Store  # noqa: E402

TEXT = contracts.Contract("toy-text", 1, lambda folder: [] if any(folder.glob("*.txt")) else ["no text file"])
WRITTEN = (checks.Check("written", lambda output, inputs, evidence: checks.Verdict("written", checks.PASS, "written")),)


def make_clean(inputs, out, seed, params):
    (out / "clean.txt").write_text(inputs["brief"].read_text().upper())


def make_paint(inputs, out, seed, params):
    raise AssertionError("a paid make ran in a free-only run")


def make_count(inputs, out, seed, params):
    (out / "count.txt").write_text("1")


def free_runner():
    data = pathlib.Path(tempfile.mkdtemp())
    (data / "hangar").mkdir()
    (data / "hangar" / "brief.txt").write_text("a ship")
    table = (graph.Stage("clean", "place", make_clean, TEXT, WRITTEN, files={"brief": "{data}/{place}/brief.txt"}),
             graph.Stage("paint", "place", make_paint, TEXT, WRITTEN, after={"clean": ("toy-text", 1)}, paid=True,
                         euros=0.5),
             graph.Stage("count", "place", make_count, TEXT, WRITTEN, after={"paint": ("toy-text", 1)}))
    runner = graph.Runner(table, graph.Environment("toy", 7, {"data": data}), Store.in_folder(tempfile.mkdtemp()),
                          model_record=lambda kind: {"kind": kind})
    runner.free_only = True
    return runner


def refused_clearance(*arguments, **options):
    raise AssertionError("a clearance was asked in a free-only run")


def test_a_free_node_runs_a_paid_one_is_left_and_the_node_after_it_waits(monkeypatch):
    monkeypatch.setattr(compute, "clearance", refused_clearance)
    runner = free_runner()
    found = runner.drive(["hangar"], say=lambda line: None)
    assert found["clean@hangar"].endswith("pass, accepted automatically"), found
    assert found["paint@hangar"] == graph.PAID_LEFT, found
    assert found["count@hangar"] == "not run: waits on paint@hangar, paid, left for the Buy", found
    assert not (runner.store.cache.parent / "faults" / "paint@hangar.txt").exists()
    assert runner.lines(["hangar"], whole=False)["hangar"][0] == "waits at paint@hangar"


def test_a_free_only_run_ends_ok_with_its_list_and_opens_no_pool(monkeypatch):
    from score import __main__ as command
    monkeypatch.setattr(compute, "clearance", refused_clearance)
    monkeypatch.setattr(command, "opened_pool", refused_clearance)
    printed = io.StringIO()
    options = argparse.Namespace(jobs=graph.JOBS, stage=None, command="run", free=True)
    with contextlib.redirect_stdout(printed):
        _, status = command.run_with_exit_line(free_runner(), ["hangar"], False, options, ["run", "world1", "--free"])
    said = printed.getvalue().splitlines()
    assert status.startswith("ok, free-only, 1 free rows stand, 0 failed, 1 paid rows left for the Buy"), said
    assert "  left for the Buy: paint@hangar" in said and "  waits on a paid row: count@hangar" in said, said


def test_a_paid_step_is_never_cleared_in_a_free_only_run(monkeypatch):
    monkeypatch.setattr(compute, "clearance", refused_clearance)
    try:
        free_runner().cleared("paint@hangar", 0.5)
        raise AssertionError("cleared")
    except graph.Blocked as block:
        assert "left for the Buy" in str(block)

