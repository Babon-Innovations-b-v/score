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

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))

from score import contracts, graph  # noqa: E402
from score.adapters import compute, engines  # noqa: E402
compute.cloud_bill = lambda: 0.0  # no cloud: the provider's bill is never read here
compute.ledger().open_books_for_tests(tempfile.mkdtemp())  # this month's books known: paid paths open
from score.store import Store  # noqa: E402

STARTED = []


def make_nothing(inputs, out, seed, params):
    raise AssertionError("not made in this test")


RENDER = graph.Stage("render", "place", make_nothing, contracts.Contract("toy-render", 1, lambda folder: []),
                     paid=True)


def test_a_blender_job_runs_the_pinned_image_headless():
    spec = engines.blender_job("tools/blender/inside/warm_kernels.py", ["/work/out.json"], [], "code/x.tar.gz", 5, 0.4)
    assert spec["euros"] == 0.4
    assert "@sha256:" in spec["image"]  # pinned by digest, never a moving tag
    command = spec["command"]
    assert "-b" in command and command[command.index("--python-exit-code") + 1] == "1"  # headless; a failed script fails
    assert command[command.index("--python") + 1] == "tools/blender/inside/warm_kernels.py"
    assert command[-2:] == ["--", "/work/out.json"]


def test_the_machine_path_starts_only_for_a_cleared_node():
    runner = graph.Runner([RENDER], graph.Environment("toy", 1, {}), Store.in_folder(tempfile.mkdtemp()))
    blender_cloud = engines.machine_runner()
    real = blender_cloud.run_elsewhere
    blender_cloud.run_elsewhere = lambda *arguments: STARTED.append(arguments + (os.environ.get(compute.TICKET),))
    try:
        books = compute.ledger()
        kept_refusal, books.books_refusal = books.books_refusal, lambda: "the month's books are unknown"
        try:
            engines.blender_on_machines(runner, "render@hangar", "s.py", [], [], [], ["cpu-32c-128gb"], 5, 0.5)
        except compute.Refused as refusal:
            assert "unknown" in str(refusal)
        finally:
            books.books_refusal = kept_refusal
        assert STARTED == []
        key = runner.ticket("render@hangar")["key"]
        books.entries = lambda: []
        engines.blender_on_machines(runner, "render@hangar", "s.py", [], [], [], ["cpu-32c-128gb"], 5, 0.5)
        assert STARTED == [("s.py", [], [], [], ["cpu-32c-128gb"], f"render@hangar {key[:12]}", 5,
                            f"render@hangar {key}")], STARTED
        assert compute.TICKET not in os.environ
    finally:
        blender_cloud.run_elsewhere = real


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[3] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
