"""The drive starts no node while this PC's memory is short: it waits until the available memory, less a floor for
each node started in the last RAMP_SECONDS, holds the floor for one more, and never starts more than --jobs. A fake
memory reading at the seam (graph.AVAILABLE).

Fault (the owner, 2026-10-22): this PC (43 GB) has run out of memory before; the Buy batch goes from 8 jobs to 16.

Run: .venv/bin/python score/graph/memory_test.py
"""
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from score import graph  # noqa: E402
from score.graph.drive_test import PLACES, a_runner  # noqa: E402

FLOOR = graph.MEMORY_FLOOR


def faked(readings):
    """graph.AVAILABLE replaced by `readings` in turn, its last one kept; the readings taken so far."""
    taken = []

    def reading():
        taken.append(readings[min(len(taken), len(readings) - 1)])
        return taken[-1]
    graph.AVAILABLE = reading
    return taken


def test_each_node_started_lately_holds_a_floor_until_it_has_ramped():
    faked([2.5 * FLOOR])
    now = time.monotonic()
    assert graph.memory_room([])
    assert graph.memory_room([now])  # 2.5 floors less one ramping: 1.5 left
    assert not graph.memory_room([now, now])  # 0.5 left
    assert graph.memory_room([now, now - graph.RAMP_SECONDS - 1])  # the older one's memory is in the reading


def test_the_drive_waits_while_memory_is_short_then_runs_every_node():
    runner = a_runner({"hangar": "a ship", "station": "a hub"})
    taken = faked([FLOOR - 1] * 3 + [100 * FLOOR])
    started = []
    start = runner.start
    runner.start = lambda stage, place, threads: started.append(taken[-1]) or start(stage, place, threads)
    graph.MEMORY_POLL, said = 0.01, []
    found = runner.drive(PLACES, say=said.append, jobs=4)
    assert set(found) == {"clean@hangar", "clean@station", "count@hangar", "count@station"}, found
    assert started and all(reading >= FLOOR for reading in started), started  # none started while short
    assert len(taken) > 3 and [line for line in said if line.startswith("memory: ")], said


def test_room_for_many_never_starts_more_than_jobs():
    runner = a_runner({place: "a ship" for place in PLACES})
    faked([100 * FLOOR])
    running, most = [], [0]
    start, wait = runner.start, graph.FORK_WAIT

    def counted_start(stage, place, threads):
        started = start(stage, place, threads)
        running.extend(started)
        most[0] = max(most[0], len(running))
        return started

    def counted_wait(connections, timeout=None):
        finished = wait(connections, timeout=timeout)
        for connection in finished:
            running.remove(connection)
        return finished
    runner.start, graph.FORK_WAIT = counted_start, counted_wait
    try:
        runner.drive(PLACES, say=lambda line: None, jobs=1)
    finally:
        graph.FORK_WAIT = wait
    assert most[0] == 1, most


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[2] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
