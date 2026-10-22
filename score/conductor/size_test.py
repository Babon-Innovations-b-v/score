"""The conductor grows for a run that asks for more cores than it has, never for an agent's run or under the kill
switch's latch, waits for live runs before a grow, and shrinks only after 30 idle minutes.

Run: .venv/bin/python score/conductor/size_test.py
"""
import io
import json
import os
import pathlib
import shutil
import sys
import tempfile
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from score import conductor  # noqa: E402
from score.conductor import size  # noqa: E402
from score.graph import runs  # noqa: E402

RECORD = {"name": "conductor", "idle_type": "POP2-HM-2C-16G", "batch_type": "POP2-HM-16C-128G", "idle_cores": 2,
          "batch_cores": 16, "project": "score-conductor"}
IDLE = {"claims": 0, "running": 0, "waiting": 0, "wanted": 0, "parked": 0, "frozen": 0}


def as_conductor(call, cores=2):
    """Run `call` on a fake conductor of `cores` cores (machine.json and the size function's url set)."""
    folder = pathlib.Path(tempfile.mkdtemp())
    kept = conductor.MACHINE, os.cpu_count, os.environ.get(conductor.SIZE_URL)
    (folder / "machine.json").write_text(json.dumps(RECORD))
    conductor.MACHINE, os.cpu_count = folder / "machine.json", lambda: cores
    os.environ[conductor.SIZE_URL] = "https://size.invalid/"
    try:
        return call()
    finally:
        conductor.MACHINE, os.cpu_count = kept[0], kept[1]
        if kept[2] is None:
            os.environ.pop(conductor.SIZE_URL)
        else:
            os.environ[conductor.SIZE_URL] = kept[2]
        shutil.rmtree(folder)


def test_a_run_waits_for_size_only_on_a_conductor_for_the_owner_within_the_batch_cores():
    assert size.waits(16, False, agent=False) is None  # not a conductor: refused as on the PC
    assert as_conductor(lambda: size.waits(16, False, agent=False)).startswith("16 jobs on 2 cores: waiting")
    assert as_conductor(lambda: size.waits(2, False, agent=False)) is None  # fits
    assert as_conductor(lambda: size.waits(16, True, agent=False)) is None  # --oversubscribe runs as asked
    assert as_conductor(lambda: size.waits(16, False, agent=True)) is None  # an agent's run never grows the machine
    assert as_conductor(lambda: size.waits(17, False, agent=False)) is None  # more than the batch size has


def test_the_default_jobs_are_the_cores_on_a_conductor_and_eight_elsewhere():
    assert conductor.default_jobs(8) == 8
    assert as_conductor(lambda: conductor.default_jobs(8), cores=16) == 16


def test_a_grow_is_asked_for_a_waiting_run_once_no_run_is_live():
    waiting = {**IDLE, "waiting": 1, "wanted": 16}
    assert size.decide(waiting, 2, RECORD, 0, 100, False)[0] == size.GROW
    assert size.decide({**waiting, "claims": 1}, 2, RECORD, 0, 100, False) == (
        None, "a run waits for size; the grow waits for the live runs to end")
    assert size.decide({**waiting, "running": 1}, 2, RECORD, 0, 100, False)[0] is None
    assert "free-only latch" in size.decide(waiting, 2, RECORD, 0, 100, True)[1]


def test_a_shrink_comes_only_after_thirty_idle_minutes_at_the_batch_size():
    now = 10_000_000
    assert size.decide(IDLE, 16, RECORD, now - 29 * 60, now, False)[0] is None
    assert size.decide(IDLE, 16, RECORD, now - 31 * 60, now, False)[0] == size.SHRINK
    assert size.decide(IDLE, 2, RECORD, 0, now, False) == (None, "at the idle size")
    for busy in ("claims", "running", "waiting", "parked", "frozen"):
        found = size.decide({**IDLE, busy: 1}, 16, RECORD, 0, now, False)
        assert found[0] is None and busy in found[1], (busy, found)


def test_the_idle_time_counts_from_the_last_busy_pass():
    folder = pathlib.Path(tempfile.mkdtemp())
    kept = conductor.RESIZING
    conductor.RESIZING = folder / "resizing.json"
    asks = []
    start = max(time.time(), runs.boot_time()) + 3600
    try:
        def tick(view, now):
            return size.tick(say=lambda line: None, now=now, asker=asks.append, state_path=folder / "size.json",
                             view=view)
        found = as_conductor(lambda: [tick({**IDLE, "claims": 1}, start), tick(IDLE, start + 29 * 60),
                                      tick(IDLE, start + 31 * 60)], cores=16)
        assert [each["action"] for each in found] == [None, None, size.SHRINK], found
        assert asks == [size.SHRINK]
        assert json.loads(conductor.RESIZING.read_text())["action"] == size.SHRINK  # its power-off is a resize's
    finally:
        conductor.RESIZING = kept
        shutil.rmtree(folder)


def test_off_a_conductor_the_size_timer_does_nothing():
    said = []
    assert size.tick(say=said.append, asker=lambda action: 1 / 0)["action"] is None
    assert said == ["size: not a conductor (no machine.json or no SCORE_CONDUCTOR_SIZE_URL): nothing to do"]


def test_the_ask_carries_the_token_read_by_name_and_only_grow_or_shrink():
    folder = pathlib.Path(tempfile.mkdtemp())
    reader = folder / "reader"
    reader.write_text("#!/bin/sh\n[ \"$1\" = score-conductor-size-token ] && echo the-token\n")
    reader.chmod(0o700)
    sent = []

    class Answer(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def opener(request, timeout):
        sent.append((request.full_url, request.get_header("X-score-size-token"), json.loads(request.data)))
        return Answer(b"powering off")
    kept = os.environ.get(size.READER)
    os.environ[size.READER] = str(reader)
    try:
        assert size.ask(size.GROW, url="https://size.invalid/", opener=opener) == "powering off"
        assert sent == [("https://size.invalid/", "the-token", {"action": "grow"})]
        try:
            size.ask("delete", url="https://size.invalid/", opener=opener)
        except ValueError:
            pass
        else:
            raise AssertionError("an action other than grow or shrink was asked")
    finally:
        os.environ.pop(size.READER) if kept is None else os.environ.update({size.READER: kept})
        shutil.rmtree(folder)


def test_a_failed_ask_takes_its_resize_mark_back():
    folder = pathlib.Path(tempfile.mkdtemp())
    kept = conductor.RESIZING
    conductor.RESIZING = folder / "resizing.json"

    def refused(action):
        raise RuntimeError("the size function is down")
    try:
        size.asked(size.GROW, refused)
    except RuntimeError:
        assert not conductor.RESIZING.exists()
    else:
        raise AssertionError("the failed ask was not raised")
    finally:
        conductor.RESIZING = kept
        shutil.rmtree(folder)


def test_busy_counts_claims_waiting_runs_parked_machines_and_frozen_copies_in_use():
    home = pathlib.Path(tempfile.mkdtemp())
    try:
        (home / "runs").mkdir()
        (home / "parked").mkdir()
        (home / "frozen" / "live-copy").mkdir(parents=True)
        (home / "frozen" / "left-over").mkdir()
        runs.claim("c0ffee", ["a@b"], os.getpid(), folder=home / "runs")
        runs.register_waiting(["run", "world1", "--jobs", "16"], 16, folder=home / "runs")
        (home / "parked" / "machine.json").write_text("{}")
        os.chdir(home / "frozen" / "live-copy")
        view = size.busy(home / "runs", home / "parked", home / "frozen")
        assert view == {"claims": 1, "running": 0, "waiting": 1, "wanted": 16, "parked": 1, "frozen": 1}, view
    finally:
        os.chdir("/")
        shutil.rmtree(home)


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[2] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
