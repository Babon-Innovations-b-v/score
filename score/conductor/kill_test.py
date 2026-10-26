"""The kill switch stops every live and waiting run, deletes every parked machine and latches the conductor free only;
only the owner's process may pull it or clear it, and every `score` command runs free only while the latch holds.

Run: .venv/bin/python score/conductor/kill_test.py
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from score import conductor  # noqa: E402
from score.conductor import kill  # noqa: E402
from score.graph import runs  # noqa: E402

REPO = pathlib.Path(__file__).resolve().parents[2]


def in_home(call):
    """Run `call(home)` with the conductor's own folder in a temp home."""
    home = pathlib.Path(tempfile.mkdtemp())
    kept = conductor.HOME, conductor.FREE_ONLY_LATCH, conductor.RESIZING
    conductor.HOME, conductor.FREE_ONLY_LATCH = home / "conductor", home / "conductor" / "free-only"
    conductor.RESIZING = home / "conductor" / "resizing.json"
    try:
        return call(home)
    finally:
        conductor.HOME, conductor.FREE_ONLY_LATCH, conductor.RESIZING = kept
        shutil.rmtree(home)


def test_only_the_owners_process_pulls_the_switch_or_clears_the_latch():
    kept = kill.running_under_agent
    kill.running_under_agent = lambda: True
    try:
        for call in (lambda: kill.stop_all("owner", "stop"), lambda: kill.allow_paid("owner", "go on"),
                     lambda: kill.stop_batch("owner", "stop")):
            try:
                call()
            except PermissionError as refused:
                assert "only the owner's click" in str(refused)
            else:
                raise AssertionError("an agent's process pulled the kill switch")
    finally:
        kill.running_under_agent = kept


def test_the_switch_stops_every_run_releases_every_parked_machine_and_latches_free_only():
    def walk(home):
        (home / "runs").mkdir()
        (home / "parked").mkdir()
        live = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
        waiter = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
        runs.claim("c0ffee", ["draw@hangar"], live.pid, folder=home / "runs")
        waiting = runs.register_waiting(["run", "world1", "--jobs", "16"], 16, folder=home / "runs")
        entry = json.loads(waiting.read_text())
        waiting.write_text(json.dumps({**entry, "pid": waiter.pid}))
        for number in (1, 2):
            (home / "parked" / f"m{number}.json").write_text(json.dumps({"id": f"m{number}", "zone": "fr-par-2",
                                                                          "token": f"t{number}"}))
        conductor.RESIZING.parent.mkdir(parents=True)
        conductor.RESIZING.write_text(json.dumps({"action": "grow", "at": time.time()}))
        released, order = [], []

        def release(server, zone, token):
            order.append("parked")
            if server == "m2":
                raise RuntimeError("the provider said no")
            released.append((server, zone, token))
        report = kill.stop_everything("owner", "stop it\nall", folder=home / "runs", parked=home / "parked",
                                      release=release, close_pools=lambda: order.append("pools") or ["run-1"])
        assert order[0] == "pools" and report["pools"] == ["run-1"]  # no collector replaces the cards released next
        live.wait(10)
        waiter.wait(10)
        assert report["runs"] == [live.pid] and report["waiting"] == [entry["id"]], report
        assert released == [("m1", "fr-par-2", "t1")] and report["errors"][0].startswith("parked m2: RuntimeError")
        assert json.loads(waiting.read_text())["state"] == runs.STOPPED
        assert conductor.FREE_ONLY_LATCH.read_text().splitlines()[-1] == "SCORE_FREE_ONLY=1"
        assert "stop it all" in conductor.FREE_ONLY_LATCH.read_text()  # his words on one line
        assert not conductor.RESIZING.exists()  # its SIGTERMs are his stop, never a resize's
        assert list(conductor.HOME.glob("kill-*.json"))
        assert kill.unlatch("owner", "go on")["was_held"] and not conductor.free_only()
        assert list(conductor.HOME.glob("free-only-cleared-*.json"))
    in_home(walk)


def test_stop_this_batch_stops_its_run_and_machines_and_leaves_paid_work_allowed():
    """Owner, 2026-10-25: the next Buy after a stopped batch needs no Allow paid work again."""
    def walk(home):
        (home / "runs").mkdir()
        (home / "parked").mkdir()
        live = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
        runs.claim("c0ffee", ["draw@hangar"], live.pid, folder=home / "runs")
        (home / "parked" / "m1.json").write_text(json.dumps({"id": "m1", "zone": "fr-par-2", "token": "t1"}))
        released = []
        report = kill.stop_everything("owner", "this batch", folder=home / "runs", parked=home / "parked",
                                      release=lambda *machine: released.append(machine),
                                      close_pools=lambda: ["run-1"], latched=False)
        live.wait(10)
        assert report["runs"] == [live.pid] and released == [("m1", "fr-par-2", "t1")] and report["pools"] == ["run-1"]
        assert report["free_only"] is None and not conductor.free_only()
        assert list(conductor.HOME.glob("batch-stop-*.json")) and not list(conductor.HOME.glob("kill-*.json"))
    in_home(walk)


def test_a_stop_ends_every_process_left_in_the_copy_of_a_run_gone_and_leaves_a_stopping_runs_to_it():
    """2026-10-26: after Stop this batch six processes of the stopped run worked on in its frozen copy for an hour and
    held the checkout; a second stop found no run and ended none."""
    def walk(home):
        (home / "runs").mkdir()
        gone, stopping = home / "frozen" / "20261026-081445-1", home / "frozen" / "20261026-091445-2"
        gone.mkdir(parents=True)
        (home / "frozen" / "20261026-081445-1.home").mkdir()
        stopping.mkdir()
        sleep = [sys.executable, "-c", "import time; time.sleep(60)"]
        left = [subprocess.Popen(sleep, cwd=gone), subprocess.Popen(sleep, cwd=f"{gone}.home")]
        run = subprocess.Popen(sleep, cwd=stopping)
        node = subprocess.Popen(sleep, cwd=stopping)
        runs.claim("c0ffee", ["draw@hangar"], run.pid, folder=home / "runs")
        time.sleep(0.3)
        try:
            report = kill.stop_everything("agent", "the batch", folder=home / "runs", parked=home / "empty",
                                          close_pools=lambda: [], latched=False, frozen_folder=home / "frozen")
            assert sorted(entry["pid"] for entry in report["leftovers"]) == sorted(process.pid for process in left)
            assert all("time.sleep(60)" in entry["command"] for entry in report["leftovers"])
            assert all(process.wait(5) == -15 for process in left)
            assert report["runs"] == [run.pid] and node.poll() is None  # the stopping run ends its own (remove_owned)
        finally:
            for process in (*left, run, node):
                process.kill()
                process.wait()
    in_home(walk)


def test_every_score_command_runs_free_only_while_the_latch_holds():
    def walk(home):
        (home / "conductor").mkdir()
        (home / "conductor" / "free-only").write_text("SCORE_FREE_ONLY=1\n")
        done = subprocess.run([sys.executable, "-c", "import os\nfrom score import __main__ as command\n"
                               "command.main(['resume', '--dry'])\nprint(os.environ.get('SCORE_FREE_ONLY'))"],
                              cwd=REPO, capture_output=True, text=True,
                              env={**os.environ, "PROPS_HOME": str(home), "SCORE_FREE_ONLY": ""})
        assert done.stdout.strip().splitlines()[-1] == "1", done.stdout + done.stderr[-800:]
    in_home(walk)


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[2] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
