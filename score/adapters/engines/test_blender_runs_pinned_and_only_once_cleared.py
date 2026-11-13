"""A Blender job runs the pinned image headless and fails when its script fails, and the machine path never starts
for a node the compute adapter refuses; it starts named by the node's ticket once cleared. No machine is rented: the
machine runner's run_elsewhere is replaced by a recorder.

Breaks (each applied once, seen red, reverted), in score/adapters/engines/__init__.py:
- pinned and headless: blender_job's command drops "-b".
- only once cleared: blender_on_machines takes its ticket from runner.ticket instead of compute.clearance.

Run: PROPS_HOME=$(mktemp -d) .venv/bin/python score/adapters/engines/test_blender_runs_pinned_and_only_once_cleared.py
"""
import os
import pathlib
import sys
import tempfile

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))

from score import contracts, graph  # noqa: E402
from score.adapters import compute, engines  # noqa: E402
from score.store import Store  # noqa: E402

STARTED = []
BOOKS_FOLDER = tempfile.mkdtemp()


def no_cloud_and_books_open(monkeypatch):
    """No cloud: the provider's bill is never read here; this month's books known, so paid paths open."""
    monkeypatch.setattr(compute, "cloud_bill", lambda: 0.0)
    monkeypatch.setattr(compute.ledger(), "BOOKS", compute.ledger().BOOKS)  # recorded: open_books_for_tests moves it
    compute.ledger().open_books_for_tests(BOOKS_FOLDER)


@pytest.fixture(autouse=True)
def no_cloud_and_books_open_for_each_test(monkeypatch):
    """Patched per test under pytest, so the next test file gets the real ones back."""
    no_cloud_and_books_open(monkeypatch)


def make_nothing(inputs, out, seed, params):
    raise AssertionError("not made in this test")


RENDER = graph.Stage("render", "place", make_nothing, contracts.Contract("toy-render", 1, lambda folder: []),
                     paid=True)


SCRIPT = "tools/blender/inside/warm_kernels.py"
ARGUMENTS = ["/work/out.json"]
CLASSES = ["cpu-32c-128gb"]


def test_a_blender_job_runs_pinned_and_headless_only_once_cleared():
    """One node, one script: its job spec is the pinned image run headless, and its machine run starts only after
    the compute adapter clears it, named by the node's ticket."""
    spec = engines.blender_job(SCRIPT, ARGUMENTS, [], "code/x.tar.gz", 5, 0.4)
    assert spec["euros"] == 0.4
    assert "@sha256:" in spec["image"]  # pinned by digest, never a moving tag
    command = spec["command"]
    assert "-b" in command and command[command.index("--python-exit-code") + 1] == "1"  # headless; a failed script fails
    assert command[command.index("--python") + 1] == SCRIPT
    assert command[-2:] == ["--", *ARGUMENTS]

    runner = graph.Runner([RENDER], graph.Environment("toy", 1, {}), Store.in_folder(tempfile.mkdtemp()))
    blender_cloud = engines.machine_runner()
    real = blender_cloud.run_elsewhere
    blender_cloud.run_elsewhere = lambda *arguments: STARTED.append(arguments + (os.environ.get(compute.TICKET),))
    books = compute.ledger()
    try:
        kept_refusal, books.books_refusal = books.books_refusal, lambda: "the month's books are unknown"
        try:
            with pytest.raises(compute.Refused, match="unknown"):
                engines.blender_on_machines(runner, "render@hangar", SCRIPT, ARGUMENTS, [], [], CLASSES, 5, 0.5)
        finally:
            books.books_refusal = kept_refusal
        assert STARTED == []
        key = runner.ticket("render@hangar")["key"]
        books.entries = lambda: []
        engines.blender_on_machines(runner, "render@hangar", SCRIPT, ARGUMENTS, [], [], CLASSES, 5, 0.5)
        assert STARTED == [(SCRIPT, ARGUMENTS, [], [], CLASSES, f"render@hangar {key[:12]}", 5,
                            f"render@hangar {key}")], STARTED
        assert compute.TICKET not in os.environ
    finally:
        blender_cloud.run_elsewhere = real


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[3] / "conftest.py"))["refuse_outside_sandbox"]()
    no_cloud_and_books_open(pytest.MonkeyPatch())  # this process only: never undone
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
