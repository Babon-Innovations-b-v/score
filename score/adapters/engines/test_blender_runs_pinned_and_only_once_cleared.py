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


NODE = "render@hangar"
JOB = {"script": "tools/blender/inside/warm_kernels.py", "arguments": ["/work/out.json"], "inputs": [], "outputs": [],
       "classes": ["cpu-32c-128gb"], "minutes": 5, "euros": 0.5}

# One node's job asked to run twice: books state -> whether the compute adapter refuses it.
CASES = [
    ("books unknown", "the month's books are unknown", True),
    ("cleared", None, False),
]


def test_a_blender_job_runs_pinned_and_headless_only_once_cleared():
    """One node's job: its container spec and its machine run are the same script and arguments, the spec pinned and
    headless, and the machine run starts only once the compute adapter clears it, named by the node's ticket."""
    spec = engines.blender_job(JOB["script"], JOB["arguments"], JOB["outputs"], "code/x.tar.gz", JOB["minutes"],
                               JOB["euros"])
    command = spec["command"]
    runner = graph.Runner([RENDER], graph.Environment("toy", 1, {}), Store.in_folder(tempfile.mkdtemp()))
    key = runner.ticket(NODE)["key"]
    blender_cloud = engines.machine_runner()
    real = blender_cloud.run_elsewhere
    blender_cloud.run_elsewhere = lambda *arguments: STARTED.append(arguments + (os.environ.get(compute.TICKET),))
    books = compute.ledger()
    kept_refusal = books.books_refusal
    try:
        for name, refusal, refused in CASES:
            STARTED.clear()
            books.books_refusal = (lambda: refusal) if refusal else kept_refusal
            if refusal is None:
                books.entries = lambda: []
            try:
                engines.blender_on_machines(runner, NODE, JOB["script"], JOB["arguments"], JOB["inputs"],
                                            JOB["outputs"], JOB["classes"], JOB["minutes"], JOB["euros"])
                raised = None
            except compute.Refused as refusal_raised:
                raised = refusal_raised
            assert (raised is not None) == refused, (name, raised)
            if refused:
                assert "unknown" in str(raised), (name, raised)
                assert STARTED == [], (name, STARTED)
                continue
            assert len(STARTED) == 1, (name, STARTED)
            script, arguments, inputs, outputs, classes, label, minutes, ticket = STARTED[0]
            # the machine run is the spec's own job: same script, same arguments after "--"
            assert script == command[command.index("--python") + 1], (name, script, command)
            assert list(arguments) == command[command.index("--") + 1:], (name, arguments, command)
            assert (inputs, outputs, classes, minutes) == (JOB["inputs"], spec["outputs"], JOB["classes"],
                                                           spec["minutes"]), (name, STARTED)
            assert label == f"{NODE} {key[:12]}" and ticket == f"{NODE} {key}", (name, label, ticket)
            assert compute.TICKET not in os.environ, name
    finally:
        books.books_refusal = kept_refusal
        blender_cloud.run_elsewhere = real
    # that one job, as a container spec: pinned by digest, headless, a failed script fails, priced at its estimate
    assert "@sha256:" in spec["image"], spec["image"]
    assert "-b" in command and command[command.index("--python-exit-code") + 1] == "1", command
    assert command[command.index("--python") + 1] == JOB["script"] and command[-2:] == ["--", *JOB["arguments"]]
    assert spec["euros"] == JOB["euros"], spec


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[3] / "conftest.py"))["refuse_outside_sandbox"]()
    no_cloud_and_books_open(pytest.MonkeyPatch())  # this process only: never undone
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
