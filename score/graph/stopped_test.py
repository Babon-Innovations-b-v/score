"""A stopped detached Buy releases its warm pool before anything else, inside the time its wrapper gives it.

Fault, 2026-10-24 (second Buy): the detached wrapper (stopped.forward) waited 40 s, `score run` spent 30 s of them in
its stop grace before it reached its pool release, and was SIGKILLed 10 s into it; and in the first Buy the pool
stayed open through the grace, so the collector rented three cards in the place of those the stopping takers deleted.

Run: .venv/bin/python score/graph/stopped_test.py
"""
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from score import __main__ as command  # noqa: E402
from score.graph import stopped  # noqa: E402


def test_the_wrapper_waits_out_the_pool_release_and_the_grace():
    assert command.POOL_RELEASE_SECONDS + command.STOP_GRACE_SECONDS < stopped.FORWARD_WAIT_SECONDS


def test_a_stopped_run_closes_its_pool_before_its_grace():
    said = []
    released, ended = command.release_pool, command.end_group
    command.release_pool = lambda run_id: said.append(("pool released", run_id))
    command.end_group = lambda: said.append(("group ended",)) or ([], [])
    os.environ[command.RUN_ID] = "run-stopped-test"
    try:
        command.stop_run(15)
    finally:
        command.release_pool, command.end_group = released, ended
    assert said == [("pool released", "run-stopped-test"), ("group ended",)]


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[2] / "conftest.py"))["refuse_outside_sandbox"]()
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
    print(f"stopped: {len(tests)} checks pass")
