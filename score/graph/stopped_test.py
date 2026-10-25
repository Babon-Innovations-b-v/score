"""A stopped detached Buy releases its warm pool before anything else, inside the time its wrapper gives it.

Fault, 2026-10-24 (second Buy): the detached wrapper (stopped.forward) waited 40 s, `score run` spent 30 s of them in
its stop grace before it reached its pool release, and was SIGKILLed 10 s into it; and in the first Buy the pool
stayed open through the grace, so the collector rented three cards in the place of those the stopping takers deleted.

Run: .venv/bin/python score/graph/stopped_test.py
"""
import contextlib
import io
import os
import pathlib
import signal
import sys
import threading
import time
import types

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


def test_a_hung_pool_release_is_left_after_its_bound_so_the_run_still_ends():
    """Batch 1 (2026-10-25): the run never wrote its exit line while its pool's machines stayed parked."""
    hung, said = threading.Event(), []
    tool, bound, printed = command.cloud_tool, command.POOL_RELEASE_SECONDS, io.StringIO()
    command.cloud_tool = lambda name: types.SimpleNamespace(release=lambda run_id: said.append(run_id) or hung.wait())
    command.POOL_RELEASE_SECONDS, started = 0.2, time.monotonic()
    try:
        with contextlib.redirect_stdout(printed):
            command.release_pool("run-hung-release")
    finally:
        command.cloud_tool, command.POOL_RELEASE_SECONDS = tool, bound
        hung.set()
    assert said == ["run-hung-release"] and time.monotonic() - started < 2
    assert "the pool's release did not end in 0.2 s" in printed.getvalue(), printed.getvalue()


def test_the_watchdog_stops_a_run_whose_drive_has_not_moved():
    """Batch 1 (2026-10-25): its drive sat in one pass over an hour after its last heartbeat."""
    stopped_by, moving = threading.Event(), types.SimpleNamespace(driving=(1, time.monotonic()))
    before = signal.signal(signal.SIGTERM, lambda number, frame: stopped_by.set())
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            with command.watching(moving, stall=5, every=0.05):  # a drive that moves is left alone
                assert not stopped_by.wait(0.3)
            stuck = types.SimpleNamespace(driving=(0, time.monotonic() - 10))
            with command.watching(stuck, stall=5, every=0.05):
                assert stopped_by.wait(5)
    finally:
        signal.signal(signal.SIGTERM, before)


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[2] / "conftest.py"))["refuse_outside_sandbox"]()
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
    print(f"stopped: {len(tests)} checks pass")
