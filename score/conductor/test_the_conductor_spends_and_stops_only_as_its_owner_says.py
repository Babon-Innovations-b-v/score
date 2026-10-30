"""score.conductor's invariant: the conductor spends and stops only as its owner says. It grows only for the owner's
run that asks for more cores than it has (never an agent's, never under the kill switch's latch, never while a run is
live) and shrinks only after 30 idle minutes with nothing busy (a claim, a waiting run, a parked machine, a frozen copy
in use, a hold); its ask carries the token read by name and only grow or shrink, and a failed ask takes its resize
mark back. Its own bill never enters the batch's spend, and every paid point refuses while the batch project is the
conductor's. Only the owner's process pulls the kill switch, which stops every run (and the processes left in a gone
run's frozen copy), closes the pools before it releases every parked machine, and latches every `score` command free
only; Stop this batch does the same without the latch. A detached run is capped in score-runs.slice at the memory
less 6 GB, a step's own scope inherits it, and off a conductor nothing changes. Its health names what the Machine card
reads and its log tails carry no secret. The free end-to-end check (`dry`) passes every step in one line. No run
starts under the data disk's floor, the health warns there, and clean-frozen removes only the frozen copies no run
needs and no process works in, never what their homes link to, and nothing while it cannot tell; clean-cache
makes the checkouts' copies links to the stored blobs even with a run live; clean-kept drops only the kept jobs no
current key asks for; `disk` accounts for the whole data disk, store-gc removes only the blobs nothing names and only
with no run live, and the sweep frees room itself, asking the owner only for a bigger disk, priced.

Break that turns it red: in size.decide grow while a run is live (drop the claims/running wait); in kill.stop_everything
release the parked machines before closing the pools; or in logs drop the secret-shape test (an AIza key reaches the
tails); or in disk.kept drop the registered-run test (a waiting run's copy is removed).
"""
import datetime
import io
import json
import os
import pathlib
import subprocess
import sys
import time

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from score import conductor  # noqa: E402
from score.adapters import compute  # noqa: E402
from score.adapters.compute import guard  # noqa: E402
from score.conductor import disk, health, kill, logs, size, slices  # noqa: E402
from score.graph import frozen, runs  # noqa: E402
from score.store import Store, file_hash  # noqa: E402

RECORD = {"name": "conductor", "idle_type": "POP2-HM-2C-16G", "batch_type": "POP2-HM-16C-128G", "idle_cores": 2,
          "batch_cores": 16, "project": "score-conductor"}
IDLE = {"claims": 0, "running": 0, "waiting": 0, "wanted": 0, "parked": 0, "frozen": 0, "working": 0}
SLEEP = [sys.executable, "-c", "import time; time.sleep(60)"]


@pytest.fixture
def home(tmp_path, monkeypatch):
    """The conductor's own folder in the test's home."""
    monkeypatch.setattr(conductor, "HOME", tmp_path / "conductor")
    monkeypatch.setattr(conductor, "FREE_ONLY_LATCH", tmp_path / "conductor" / "free-only")
    monkeypatch.setattr(conductor, "RESIZING", tmp_path / "conductor" / "resizing.json")
    return tmp_path


@pytest.fixture
def as_conductor(tmp_path, monkeypatch):
    """A function making this process a fake conductor of `cores` cores (machine.json and the size function's url)."""
    def make(cores=2):
        (tmp_path / "machine.json").write_text(json.dumps(RECORD))
        monkeypatch.setattr(conductor, "MACHINE", tmp_path / "machine.json")
        monkeypatch.setattr(os, "cpu_count", lambda: cores)
        monkeypatch.setenv(conductor.SIZE_URL, "https://size.invalid/")
    return make


# --- size: grow for the owner's run, shrink when idle ------------------------------------------------------------------

def test_a_run_waits_for_size_only_on_a_conductor_for_the_owner_within_the_batch_cores(as_conductor):
    assert size.waits(16, False, agent=False) is None  # not a conductor: refused as on the PC
    assert conductor.default_jobs(8) == 8
    as_conductor(2)
    assert size.waits(16, False, agent=False).startswith("16 jobs on 2 cores: waiting")
    assert size.waits(2, False, agent=False) is None  # fits
    assert size.waits(16, True, agent=False) is None  # --oversubscribe runs as asked
    assert size.waits(16, False, agent=True) is None  # an agent's run never grows the machine
    assert size.waits(17, False, agent=False) is None  # more than the batch size has
    as_conductor(16)
    assert conductor.default_jobs(8) == 16


def test_a_grow_is_asked_for_a_waiting_run_once_no_run_is_live_and_no_latch_holds():
    waiting = {**IDLE, "waiting": 1, "wanted": 16}
    assert size.decide(waiting, 2, RECORD, 0, 100, False)[0] == size.GROW
    assert size.decide({**waiting, "claims": 1}, 2, RECORD, 0, 100, False)[0] is None
    assert size.decide({**waiting, "running": 1}, 2, RECORD, 0, 100, False)[0] is None
    assert "free-only latch" in size.decide(waiting, 2, RECORD, 0, 100, True)[1]


def test_a_shrink_comes_only_after_thirty_idle_minutes_at_the_batch_size():
    now = 10_000_000
    assert size.decide(IDLE, 16, RECORD, now - 29 * 60, now, False)[0] is None
    assert size.decide(IDLE, 16, RECORD, now - 31 * 60, now, False)[0] == size.SHRINK
    assert size.decide(IDLE, 2, RECORD, 0, now, False)[0] is None  # already at the idle size
    for busy in ("claims", "running", "waiting", "parked", "frozen", "working"):
        found = size.decide({**IDLE, busy: 1}, 16, RECORD, 0, now, False)
        assert found[0] is None and busy in found[1], (busy, found)


def test_the_idle_time_counts_from_the_last_busy_pass_and_marks_its_resize(home, as_conductor):
    asks = []
    start = max(time.time(), runs.boot_time()) + 3600

    def tick(view, now):
        return size.tick(say=lambda line: None, now=now, asker=asks.append, state_path=home / "size.json", view=view)
    as_conductor(16)
    found = [tick({**IDLE, "claims": 1}, start), tick(IDLE, start + 29 * 60), tick(IDLE, start + 31 * 60)]
    assert [each["action"] for each in found] == [None, None, size.SHRINK] and asks == [size.SHRINK]
    assert json.loads(conductor.RESIZING.read_text())["action"] == size.SHRINK  # its power-off is a resize's


def test_off_a_conductor_the_size_timer_asks_nothing(monkeypatch):
    monkeypatch.delenv(conductor.SIZE_URL, raising=False)
    assert size.tick(say=lambda line: None, asker=lambda action: 1 / 0)["action"] is None


def test_the_ask_carries_the_token_read_by_name_and_only_grow_or_shrink(tmp_path, monkeypatch):
    reader = tmp_path / "reader"
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
    monkeypatch.setenv(size.READER, str(reader))
    assert size.ask(size.GROW, url="https://size.invalid/", opener=opener) == "powering off"
    assert sent == [("https://size.invalid/", "the-token", {"action": "grow"})]
    with pytest.raises(ValueError):
        size.ask("delete", url="https://size.invalid/", opener=opener)


def test_a_failed_ask_takes_its_resize_mark_back(home):
    def refused(action):
        raise RuntimeError("the size function is down")
    with pytest.raises(RuntimeError):
        size.asked(size.GROW, refused)
    assert not conductor.RESIZING.exists()


def test_a_running_entry_is_live_only_while_its_own_process_is():
    """An out-of-memory kill leaves an entry `running`; a later process given its pid is not the run."""
    late = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=5)
    early = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=400)
    entry = {"pid": os.getpid(), "state": runs.RUNNING}
    assert size.entry_alive({**entry, "started": late.isoformat(timespec="seconds")})
    assert not size.entry_alive({**entry, "started": early.isoformat(timespec="seconds")})  # its pid, not its run
    assert not size.entry_alive(entry)  # registered when, unknown: not counted as its run


def test_busy_counts_claims_waiting_runs_parked_machines_and_frozen_copies_in_use(tmp_path, monkeypatch):
    (tmp_path / "runs").mkdir()
    (tmp_path / "parked").mkdir()
    (tmp_path / "frozen" / "live-copy").mkdir(parents=True)
    (tmp_path / "frozen" / "left-over").mkdir()
    runs.claim("c0ffee", ["a@b"], os.getpid(), folder=tmp_path / "runs")
    runs.register_waiting(["run", "world1", "--jobs", "16"], 16, folder=tmp_path / "runs")
    (tmp_path / "parked" / "machine.json").write_text("{}")
    monkeypatch.chdir(tmp_path / "frozen" / "live-copy")
    view = size.busy(tmp_path / "runs", tmp_path / "parked", tmp_path / "frozen", tmp_path / "holds")
    assert view == {"claims": 1, "running": 0, "waiting": 1, "wanted": 16, "parked": 1, "frozen": 1, "working": 0}


def test_a_hold_keeps_the_machine_busy_until_its_process_lets_go(tmp_path, monkeypatch):
    """2026-10-25: a shrink cut the first sync pass after a boot. A holder killed mid-way holds nothing."""
    with conductor.holding("sync-pass", tmp_path):
        assert conductor.holds(tmp_path) == [f"sync-pass-{os.getpid()}"]
        assert size.busy(tmp_path / "runs", tmp_path / "parked", tmp_path / "frozen", tmp_path)["working"] == 1
    assert conductor.holds(tmp_path) == [] and not list(tmp_path.glob("*.lock"))
    code = (f"import os, sys, pathlib; sys.path.insert(0, {str(REPO)!r}); from score import conductor; "
            f"h = conductor.holding('film-preview', pathlib.Path({str(tmp_path)!r})); h.__enter__(); "
            "print('held', flush=True); os.kill(os.getpid(), 9)")
    child = subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.PIPE, text=True)
    assert child.stdout.readline().strip() == "held"
    child.wait()
    assert conductor.holds(tmp_path) == [] and not list(tmp_path.glob("*.lock"))  # the dead holder's file is gone
    monkeypatch.setattr(conductor, "HOLDS", tmp_path / "holds")
    monkeypatch.delenv(conductor.SIZE_URL, raising=False)
    with conductor.holding("sync-pass"):
        assert not conductor.HOLDS.exists()  # off a conductor a hold writes nothing


# --- money: the conductor's bill stays out of the batch's ---------------------------------------------------------------

def test_the_bill_the_stop_line_counts_is_the_batch_projects_alone(monkeypatch):
    compute.ledger()  # puts tools/cloud on the path
    import provider
    projects = [{"id": "batch-id", "name": "farm-factory"}, {"id": "conductor-id", "name": "score-conductor"}]
    lines = [{"project_id": "batch-id", "product_name": "Instances", "value": {"units": 40, "nanos": 0}},
             {"project_id": "conductor-id", "product_name": "Instances", "value": {"units": 75, "nanos": 0}}]
    asked = []

    def scw(*arguments):
        asked.append(arguments)
        if arguments[:3] == ("account", "project", "list"):
            return [project for project in projects if project["name"] == arguments[3].partition("=")[2]]
        if arguments[:3] == ("billing", "consumption", "list"):
            return lines  # the API's answer may hold lines of other projects: each is checked to be the project's
        raise AssertionError(arguments)
    monkeypatch.setattr(provider.cloud, "scw", scw)
    monkeypatch.delenv("SCORE_SCALEWAY_PROJECT", raising=False)
    assert compute.cloud_bill() == 40.0
    assert not any("conductor-id" in word for arguments in asked for word in arguments)


def test_every_paid_point_refuses_while_the_batch_project_is_the_conductors(tmp_path, monkeypatch):
    line = {"world": "world1", "euros": 100.0, "at": "2026-10-22T09:00:00+00:00"}
    for name in ("SCORE_SCALEWAY_PROJECT", conductor.FREE_ONLY, conductor.SIZE_URL):
        monkeypatch.delenv(name, raising=False)
    assert guard.refusal(line, 0.0, {}, 1.0) is None
    monkeypatch.setenv("SCORE_SCALEWAY_PROJECT", conductor.CONDUCTOR_PROJECT)
    assert "the conductor's own project" in guard.refusal(line, 0.0, {}, 1.0)
    assert "the conductor's own project" in compute.books_refusal()
    with pytest.raises(compute.Refused, match="the conductor's own project"):
        compute.require_books("a card")  # every rent point, the owner's override included
    record = tmp_path / "machine.json"
    monkeypatch.setenv("SCORE_SCALEWAY_PROJECT", "batch-of-another-name")
    record.write_text(json.dumps({"project": "batch-of-another-name"}))
    assert conductor.machine(record) is None  # not a conductor by the size function's name...
    assert "the conductor's own project" in conductor.project_refusal(record)  # ...yet its own project
    record.write_text(json.dumps({"project": "score-conductor-elsewhere"}))
    assert conductor.project_refusal(record) is None


# --- the kill switch ---------------------------------------------------------------------------------------------------

def test_only_the_owners_process_pulls_the_switch_or_clears_the_latch(monkeypatch):
    monkeypatch.setattr(kill, "running_under_agent", lambda: True)
    for call in (lambda: kill.stop_all("owner", "stop"), lambda: kill.allow_paid("owner", "go on"),
                 lambda: kill.stop_batch("owner", "stop")):
        with pytest.raises(PermissionError, match="only the owner's click"):
            call()


def test_the_switch_stops_every_run_releases_every_parked_machine_and_latches_free_only(home):
    (home / "runs").mkdir()
    (home / "parked").mkdir()
    live, waiter = subprocess.Popen(SLEEP), subprocess.Popen(SLEEP)
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
    try:
        report = kill.stop_everything("owner", "stop it\nall", folder=home / "runs", parked=home / "parked",
                                      release=release, close_pools=lambda: order.append("pools") or ["run-1"])
        assert live.wait(10) == -15 and waiter.wait(10) == -15
    finally:
        for process in (live, waiter):
            process.kill()
            process.wait()
    assert order[0] == "pools" and report["pools"] == ["run-1"]  # no collector replaces the cards released next
    assert report["runs"] == [live.pid] and report["waiting"] == [entry["id"]]
    assert released == [("m1", "fr-par-2", "t1")] and report["errors"][0].startswith("parked m2: RuntimeError")
    assert json.loads(waiting.read_text())["state"] == runs.STOPPED
    assert conductor.FREE_ONLY_LATCH.read_text().splitlines()[-1] == "SCORE_FREE_ONLY=1"
    assert "stop it all" in conductor.FREE_ONLY_LATCH.read_text()  # his words on one line
    assert not conductor.RESIZING.exists()  # its SIGTERMs are his stop, never a resize's
    assert list(conductor.HOME.glob("kill-*.json"))  # his stop kept on record
    assert kill.unlatch("owner", "go on")["was_held"] and not conductor.free_only()
    assert list(conductor.HOME.glob("free-only-cleared-*.json"))


def test_stop_this_batch_stops_its_run_and_machines_and_leaves_paid_work_allowed(home):
    """Owner, 2026-10-25: the next Buy after a stopped batch needs no Allow paid work again."""
    (home / "runs").mkdir()
    (home / "parked").mkdir()
    live = subprocess.Popen(SLEEP)
    runs.claim("c0ffee", ["draw@hangar"], live.pid, folder=home / "runs")
    (home / "parked" / "m1.json").write_text(json.dumps({"id": "m1", "zone": "fr-par-2", "token": "t1"}))
    released = []
    try:
        report = kill.stop_everything("owner", "this batch", folder=home / "runs", parked=home / "parked",
                                      release=lambda *machine: released.append(machine),
                                      close_pools=lambda: ["run-1"], latched=False)
        live.wait(10)
    finally:
        live.kill()
        live.wait()
    assert report["runs"] == [live.pid] and released == [("m1", "fr-par-2", "t1")] and report["pools"] == ["run-1"]
    assert report["free_only"] is None and not conductor.free_only()
    assert list(conductor.HOME.glob("batch-stop-*.json")) and not list(conductor.HOME.glob("kill-*.json"))


def test_a_stop_ends_every_process_left_in_the_copy_of_a_run_gone_and_leaves_a_stopping_runs_to_it(home):
    """2026-10-26: after Stop this batch six processes of the stopped run worked on in its frozen copy for an hour and
    held the checkout; a second stop found no run and ended none."""
    (home / "runs").mkdir()
    gone, stopping = home / "frozen" / "20261026-081445-1", home / "frozen" / "20261026-091445-2"
    gone.mkdir(parents=True)
    (home / "frozen" / "20261026-081445-1.home").mkdir()
    stopping.mkdir()
    left = [subprocess.Popen(SLEEP, cwd=gone), subprocess.Popen(SLEEP, cwd=f"{gone}.home")]
    run, node = subprocess.Popen(SLEEP, cwd=stopping), subprocess.Popen(SLEEP, cwd=stopping)
    runs.claim("c0ffee", ["draw@hangar"], run.pid, folder=home / "runs")
    time.sleep(0.3)  # the children are in their folders before the stop looks
    try:
        report = kill.stop_everything("agent", "the batch", folder=home / "runs", parked=home / "empty",
                                      close_pools=lambda: [], latched=False, frozen_folder=home / "frozen")
        assert sorted(entry["pid"] for entry in report["leftovers"]) == sorted(process.pid for process in left)
        assert all(process.wait(5) == -15 for process in left)
        assert report["runs"] == [run.pid] and node.poll() is None  # the stopping run ends its own (remove_owned)
    finally:
        for process in (*left, run, node):
            process.kill()
            process.wait()


def test_every_score_command_runs_free_only_while_the_latch_holds(tmp_path):
    (tmp_path / "conductor").mkdir()
    (tmp_path / "conductor" / "free-only").write_text("SCORE_FREE_ONLY=1\n")
    done = subprocess.run([sys.executable, "-c", "import os\nfrom score import __main__ as command\n"
                           "command.main(['resume', '--dry'])\nprint(os.environ.get('SCORE_FREE_ONLY'))"],
                          cwd=REPO, capture_output=True, text=True,
                          env={**os.environ, "PROPS_HOME": str(tmp_path), "SCORE_FREE_ONLY": ""})
    assert done.stdout.strip().splitlines()[-1] == "1", done.stdout + done.stderr[-800:]


# --- slices: a run's memory capped, nothing changed off a conductor -----------------------------------------------------

def test_the_cap_is_the_memory_less_six_gigabytes_at_both_sizes_and_the_slice_file_no_more():
    assert slices.cap_bytes(16) == 10 * 1024 ** 3
    assert slices.cap_bytes(128) == 122 * 1024 ** 3
    assert slices.cap_bytes(4) == 1024 ** 3  # never below one
    lines = (REPO / "tools/cloud/conductor/units/score-runs.slice").read_text().splitlines()
    percent = int(next(line for line in lines if line.startswith("MemoryMax=")).partition("=")[2].rstrip("%"))
    assert 16 * percent / 100 <= 16 - slices.HEADROOM_GB  # the unit file's own cap within the idle size's


def test_a_detached_run_is_its_own_scope_in_the_slice_and_off_a_conductor_in_none():
    from score import __main__ as command
    prefix = slices.scope_prefix("score-run-x")
    assert prefix[:3] == ["systemd-run", "--user", "--scope"] and "--slice=score-runs.slice" in prefix
    assert "--unit=score-run-x" in prefix and prefix[-1] == "--"
    assert not slices.usable() and command.run_scope(pathlib.Path("/tmp/score-run-x.log")) == []


def test_the_shim_is_used_only_inside_the_slice(tmp_path):
    (tmp_path / "cgroup").write_text("0::/user.slice/user@1000.service/app.slice/run-p1.scope\n")
    assert not slices.in_slice(tmp_path / "cgroup")
    (tmp_path / "cgroup").write_text("0::/user.slice/user@1000.service/score.slice/score-runs.slice/run-p1.scope\n")
    assert slices.in_slice(tmp_path / "cgroup")
    kept = os.environ.get("PATH")
    assert not slices.apply_shim() and os.environ.get("PATH") == kept  # this test runs outside the slice


def test_the_shim_adds_slice_inherit_to_a_user_unit_without_a_slice_of_its_own(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    (real / "systemd-run").write_text("#!/bin/sh\necho \"$@\"\n")
    (real / "systemd-run").chmod(0o755)
    path = f"{slices.SHIM}:{real}:/usr/bin:/bin"

    def shimmed(*words):
        return subprocess.run(["systemd-run", *words], env={**os.environ, "PATH": path}, capture_output=True,
                              text=True, check=True).stdout.strip()
    assert shimmed("--user", "--scope", "-q", "-p", "MemoryMax=16G", "nice", "x") == \
        "--slice-inherit --user --scope -q -p MemoryMax=16G nice x"
    assert shimmed("--user", "--slice=other.slice", "x") == "--user --slice=other.slice x"
    assert shimmed("--scope", "x") == "--scope x"  # not a user unit: left alone
    assert shimmed("--user", "--", "x", "--slice") == "--slice-inherit --user -- x --slice"


# --- health and logs ---------------------------------------------------------------------------------------------------

SHOWN = {"score-sync.timer": ("active", ""), "score-sync.service": ("inactive", "success"),
         "score-listen.service": ("failed", "exit-code"), "score-resume.service": ("inactive", "success"),
         "score-backup.timer": ("inactive", ""), "score-backup.service": ("inactive", "")}


def properties(unit):
    state, result = SHOWN[unit]
    return {"ActiveState": state, "Result": result,
            "ExecMainExitTimestamp": "@1792656000" if unit == "score-sync.service" else ""}


def test_each_unit_family_reads_active_failed_or_inactive():
    assert {name: health.unit_state(units, properties) for name, units in health.UNITS.items()} == {
        "sync": "active", "listen": "failed", "resume": "inactive", "backup": "inactive"}
    assert health.last_sync(properties) == {"at": "2026-10-22T08:00:00+00:00", "ok": True}  # @1792656000


def test_the_health_has_every_field_the_machine_card_reads_and_is_written_whole(tmp_path, monkeypatch):
    monkeypatch.setattr(health, "BACKUPS", tmp_path)
    for stamp, kind, ok in (("0900", "backup", False), ("0930", "backup", True), ("0945", "check-data", False)):
        (tmp_path / f"backup-20261022T{stamp}.json").write_text(json.dumps(
            {"at": f"2026-10-22T{stamp[:2]}:{stamp[2:]}:00+00:00", "kind": kind, "ok": ok}))
    found = health.read(properties)
    assert set(found) == {"at", "machine", "size", "state", "cores", "memory_total", "memory_available", "memory",
                          "disk_free", "disk", "load", "units", "runs_active", "runs_waiting", "parked_machines",
                          "last_backup", "backup", "last_sync", "sync", "free_only", "notes", "code"}
    assert found["last_backup"] == found["backup"] == {"at": "2026-10-22T09:30:00+00:00", "ok": True}
    assert found["memory_total"] >= found["memory_available"] > 0 and len(found["load"]) == 3
    assert found["disk"]["total_gb"] >= found["disk"]["free_gb"] == found["disk_free"]
    (tmp_path / "secrets").mkdir()
    (tmp_path / "secrets" / "google-billing-reader.note").write_text("no google-billing-reader secret\n")
    assert health.notes(tmp_path / "secrets") == ["no google-billing-reader secret"]
    assert health.notes(tmp_path / "none") == []
    assert health.code(pin_path=tmp_path / "none.json")["matches"] is None  # no pin read yet
    here = found["code"]["checkout"]
    (tmp_path / "pin.json").write_text(json.dumps({"at": "2026-10-25T10:00:00+00:00", "pin": here[:12]}))
    assert health.code(pin_path=tmp_path / "pin.json")["matches"] is True
    said = "update: not now, 0000 changes uv.lock and a sync pass uses .venv (pid 7)"
    (tmp_path / "pin.json").write_text(json.dumps({"at": "2026-10-25T10:00:00+00:00", "pin": "0" * 40, "said": said}))
    lagging = health.code(pin_path=tmp_path / "pin.json")
    assert lagging["matches"] is False and lagging["why"] == said  # the checkout lags the pin, and why
    path = health.write(found, tmp_path / "health.json")
    assert json.loads(path.read_text()) == found and not list(tmp_path.glob("*.partial"))


def test_the_log_tails_leave_out_every_line_naming_or_holding_a_secret(tmp_path, monkeypatch):
    monkeypatch.setenv("SCORE_SYNC_TOKEN", "s3cr3t-sync-value")
    (tmp_path / "logs").mkdir()
    (tmp_path / "faults").mkdir()
    (tmp_path / "logs" / "score-run-1.log").write_text(
        "brief@north: made\nreading gemini-api-key by name\nsent s3cr3t-sync-value along\n"
        "header X-Auth-Token: abc\nGET /v1beta/models?key=AIzaSyA0123456789abcdefghijklmnopqrstuv\n"
        "token hf_abcdefghijklmnopqrstuvwxyz0123456789\n-----BEGIN OPENSSH PRIVATE KEY-----\n"
        "asked with X-Score-Size-Token set\nexit: ok\n")
    (tmp_path / "faults" / "brief@south.txt").write_text("cause: the brief is empty\n")
    (tmp_path / "score-boot-system.log").write_text("boot: node 24.21.0 installed\nsent s3cr3t-sync-value along\n")
    found = logs.tails(10, logs=tmp_path / "logs", faults=tmp_path / "faults",
                       read_journal=lambda unit, limit: [f"{unit}: fine"],
                       boot_logs=(tmp_path / "score-boot-system.log", tmp_path / "score-boot-user.log"))
    assert found["run score-run-1.log"] == ["brief@north: made", "exit: ok"]
    assert found["fault brief@south"] == ["cause: the brief is empty"]
    assert found["journal score-listen.service"] == ["score-listen.service: fine"]
    assert found["boot score-boot-system.log"] == ["boot: node 24.21.0 installed"]
    assert "boot score-boot-user.log" not in found  # a boot log not written is not listed
    assert logs.tail(tmp_path / "logs" / "score-run-1.log", 1) == ["exit: ok"]


# --- the free end-to-end check -----------------------------------------------------------------------------------------

def test_the_dry_check_passes_every_step_in_one_line():
    """Red when a step fails, e.g. the memory guard letting the second node start while the first, short of its
    stage's peak, still runs."""
    done = subprocess.run([sys.executable, "-m", "score.conductor", "dry"], cwd=REPO, capture_output=True, text=True,
                          timeout=90)
    lines = done.stdout.strip().splitlines()
    assert len(lines) == 1 and lines[0].startswith("conductor dry: 7 of 7 steps passed; detail "), \
        done.stdout + done.stderr[-2000:]
    results = json.loads(pathlib.Path(lines[0].rpartition("detail ")[2]).read_text())
    assert [result["step"] for result in results] == ["plan", "waiting for size", "resume", "memory guard",
                                                      "health and logs", "shrink", "kill switch"]
    assert all(result["ok"] for result in results) and done.returncode == 0


# --- disk: the floor, what fills it, the copies no run needs ---------------------------------------------------------

def test_no_run_starts_under_the_disk_floor_and_the_health_warns_there(tmp_path, monkeypatch):
    """2026-10-26: 0.24 GB free of 91 GB and Batch 1 died with "No space left on device"."""
    assert disk.launch_refusal(tmp_path, floor=0) is None
    refused = disk.launch_refusal(tmp_path / "not-yet", floor=10 ** 6)
    assert refused.startswith("refused: ") and "GB floor" in refused
    monkeypatch.setattr(disk, "FLOOR_GB", 10 ** 6)
    found = health.read(properties)
    assert found["disk"]["floor_gb"] == 10 ** 6 and any(note.startswith("disk: ") for note in found["notes"])
    monkeypatch.setattr(disk, "FLOOR_GB", 0)
    assert not any(note.startswith("disk: ") for note in health.read(properties)["notes"])


def test_disk_names_the_biggest_folders_in_one_line_and_a_file(tmp_path, monkeypatch):
    home = tmp_path / "home"
    monkeypatch.setattr(disk, "mount_of", lambda path: home)  # the home the disk's top, as on the conductor
    (home / "frozen" / "20261026-081445-1").mkdir(parents=True)
    (home / "frozen" / "20261026-081445-1" / "big").write_bytes(b"x" * 300_000)
    summary, biggest = disk.report(home, home / "conductor" / "disk.json")
    assert summary.startswith("disk: ") and "1 frozen copies" in summary and str(home / "conductor") in summary
    written = json.loads((home / "conductor" / "disk.json").read_text())
    copy = str(home / "frozen" / "20261026-081445-1")
    assert written["folders"] and any(line.endswith(f"  {copy}") for line in biggest)
    deep = home / "store" / "cache" / "checkouts" / "abc" / "inner"
    deep.mkdir(parents=True)
    (deep / "big").write_bytes(b"x" * 300_000)
    _, biggest = disk.report(home, home / "conductor" / "disk.json")
    assert any(line.endswith(f"  {deep}") for line in biggest[biggest.index(next(
        line for line in biggest if line.startswith("inside "))):]), biggest  # three levels inside store/cache


def test_disk_accounts_for_the_whole_data_disk(tmp_path, monkeypatch):
    """2026-10-30: 0.01 GB free of 91, about 25 GB of it not under PROPS_HOME's folders and out of the door's sight.
    Break: score/conductor/disk.py deleted_open: 'if not os.readlink(handle).endswith(" (deleted)"):' -> 'if True:'
    (a deleted file still open is never counted), or roots: '**({mount: 3} if mount != home.resolve() else {})}' ->
    '}' (the folders outside the home are never measured)."""
    home = tmp_path / "home"
    monkeypatch.setattr(disk, "mount_of", lambda path: tmp_path)  # the disk's top above the home
    (home / "store").mkdir(parents=True)
    (tmp_path / "var" / "cache" / "apt").mkdir(parents=True)
    (tmp_path / "var" / "cache" / "apt" / "big").write_bytes(b"x" * 12_000_000)
    (tmp_path / "closed").mkdir()
    (tmp_path / "closed" / "inner").mkdir()
    (tmp_path / "closed").chmod(0)
    held = open(home / "gone.log", "wb")
    try:
        held.write(b"x" * 2_000_000)
        held.flush()
        (home / "gone.log").unlink()
        summary, lines = disk.report(home, home / "conductor" / "disk.json")
    finally:
        held.close()
        (tmp_path / "closed").chmod(0o755)
    whole = json.loads((home / "conductor" / "disk.json").read_text())["whole"]
    assert whole["mount"] == str(tmp_path) and whole["outside_gb"] > 0 and "GB outside" in summary, summary
    outside = lines[lines.index(next(line for line in lines if line.startswith("outside "))):]
    assert any(line.endswith(f"  {tmp_path / 'var' / 'cache' / 'apt'}") for line in outside), outside
    assert any(process.endswith(f"(pid {os.getpid()})") for process in whole["deleted_open"]), whole
    assert any("deleted, still open in" in line for line in lines)
    if os.getuid() != 0:  # root reads every folder
        assert whole["unread"] and any(line.startswith("unreadable: ") for line in lines), whole


def gc_home(tmp_path):
    """A home whose store holds blobs an output, a record, a link, a listing blob and nothing name."""
    home = tmp_path / "home"
    store = Store.in_folder(home / "store")
    made = tmp_path / "made"
    made.mkdir()
    (made / "listed.bin").write_bytes(b"listed")
    store.put_tree(made)
    blobs = store.objects.path("blobs")
    named = {}
    for name in ("record", "linked", "inner", "orphan", "young", "pixal"):
        path = tmp_path / f"{name}.bin"
        path.write_bytes(name.encode() * 100)
        named[name] = file_hash(path)
        store.put_blob(path, named[name])
    index = tmp_path / "index.json"  # a listing kept as a blob, named by a record: what it names stays too
    index.write_text(json.dumps({"inner": named["inner"]}))
    named["index"] = file_hash(index)
    store.put_blob(index, named["index"])
    (home / "store" / "objects" / "concepts").mkdir(parents=True)
    (home / "store" / "objects" / "concepts" / "c.json").write_text(json.dumps(
        {"pick": named["record"], "index": named["index"]}))
    (home / "dashboard").mkdir()
    (home / "dashboard" / "view.glb").symlink_to(blobs / named["linked"])
    (home / "work" / "pixal").mkdir(parents=True)
    os.link(blobs / named["pixal"], home / "work" / "pixal" / "t.glb")
    (home / "runs").mkdir()
    old = time.time() - 2 * disk.GC_YOUNG_SECONDS
    for blob in blobs.iterdir():
        if blob.name != named["young"]:
            os.utime(blob, (old, old))
    return home, blobs, named


def test_store_gc_removes_only_blobs_nothing_names_and_only_with_no_run_live(tmp_path):
    """2026-10-30: store/objects 54.7 GB on a full disk, and nothing collected what no output, record or kept job names.
    Break: score/conductor/disk.py collectable_why: 'if blob.name in held:' -> 'if False:' (a blob a record names is
    removed), or store_gc: drop 'if refused:' and its return (blobs removed under a live run)."""
    home, blobs, named = gc_home(tmp_path)
    (home / "runs" / "w.json").write_text(json.dumps({"state": runs.WAITING, "worktree": str(tmp_path / "copy")}))
    assert "a registered run needs" in disk.store_gc(home, repo=tmp_path, say=lambda line: None)["refused"]
    (home / "runs" / "w.json").unlink()
    before = sorted(path.name for path in blobs.iterdir())
    dry = disk.store_gc(home, dry=True, repo=tmp_path, say=lambda line: None)
    assert dry["removed"] == 1 and sorted(path.name for path in blobs.iterdir()) == before, dry  # dry: nothing goes
    done = disk.store_gc(home, repo=tmp_path, say=lambda line: None)
    left = {path.name for path in blobs.iterdir()}
    assert done["removed"] == 1 and named["orphan"] not in left, done
    assert {named[name] for name in ("record", "linked", "inner", "index", "young", "pixal")} <= left, done
    assert done["kept"]["written in the last day"] == 1 and "linked elsewhere too" in " ".join(done["kept"]), done
    assert Store.in_folder(home / "store").checkout(next(iter(
        path.stem for path in (home / "store" / "objects" / "outputs").glob("*.json"))))  # the output reads whole


def test_sweep_frees_room_itself_and_asks_only_for_a_bigger_disk_priced(tmp_path, monkeypatch):
    """2026-10-30, the owner on the conductor's full disk needing him: "this should be routine".
    Break: score/conductor/disk.py sweep: 'escalated = force or (record is not None and start < WARN_GB)' ->
    'escalated = force' (under the warning line the sweep runs its routine only), or warning: drop
    '{last['bigger']}' (the owner is never told the price)."""
    home, blobs, named = gc_home(tmp_path)
    monkeypatch.setattr(disk, "REPO", tmp_path)
    monkeypatch.setattr(disk, "mount_of", lambda path: home)
    monkeypatch.setattr(disk, "clean_kept", lambda home, runs_folder, say: {"dropped": 0, "refused": None})
    monkeypatch.setattr(disk, "offload_pixal", lambda home, runs_folder: {"freed": 0, "refused": None, "kept": {}})
    monkeypatch.setattr(disk, "bigger", lambda more, zone: f"{more} GB more, EUR 4.00 a month in {zone}")
    (home / "logs").mkdir()
    for name, days in (("old.log", disk.LOG_DAYS + 1), ("new.log", 1)):
        (home / "logs" / name).write_text(name)
        os.utime(home / "logs" / name, (time.time() - days * 86400,) * 2)
    free = {"gb": 50.0}
    monkeypatch.setattr(disk, "free_gb", lambda path=None: free["gb"])
    said = []
    done = disk.sweep(home, say=said.append)  # no machine.json: off a conductor, the routine only
    assert not done["escalated"] and [step["step"] for step in done["steps"]] == [
        "clean-frozen", "clean-cache", "clean-kept"], done
    (home / "machine.json").write_text(json.dumps({"zone": "fr-par-2"}))
    free["gb"] = 5.0
    done = disk.sweep(home, say=said.append)
    assert done["escalated"] and [step["step"] for step in done["steps"]][3:] == [
        "relink-pixal", "old-logs", "store-gc", "offload-pixal"], done
    assert not (home / "logs" / "old.log").exists() and (home / "logs" / "new.log").exists()
    assert named["orphan"] not in {path.name for path in blobs.iterdir()} and named["record"] in {
        path.name for path in blobs.iterdir()}
    assert done["bigger"] == "50 GB more, EUR 4.00 a month in fr-par-2" and done["fills"], done
    assert sum(line.startswith("sweep ") for line in said) == 3 + 7, said  # a line a step, each with what it freed
    note = disk.warning(5.0, swept=home / "conductor" / "sweep.json")
    assert "could not reach it" in note and "50 GB more, EUR 4.00 a month" in note, note
    free["gb"] = 12.0  # it reached the floor: nothing is asked
    assert disk.sweep(home, say=said.append)["bigger"] is None
    assert "routine sweep" in disk.warning(5.0, swept=home / "conductor" / "sweep.json")


def a_cache(home):
    """A home whose store cache holds every kind of folder, all old, and one stored object."""
    cache = home / "store" / "cache"
    for name in ("making/k-1", "checkouts/o1", "evidence", "pages/n", "tmpab12", "drops/d", "convex-parts",
                 "concepts/asked"):
        (cache / name).mkdir(parents=True)
        (cache / name / "file").write_text(name)
    (cache / "checkouts" / "o1" / "file").chmod(0o444)
    (cache / "making" / "k-1").chmod(0o555)
    (home / "store" / "objects").mkdir()
    (home / "store" / "objects" / "blob").write_text("kept")
    (home / "runs").mkdir()
    old = time.time() - 2 * disk.YOUNG_SECONDS
    for path in [*cache.rglob("*")]:
        os.utime(path, (old, old), follow_symlinks=False)
    return cache


def test_clean_cache_removes_only_what_is_made_again_free_and_only_with_no_run_live(tmp_path):
    """2026-10-27: 0.2 GB free, store/cache 37.5 GB of checkouts and makes left behind.
    Break: score/conductor/disk.py: '    if need:\n        return f"a registered run needs' -> '    if False:\n        return f"a registered run needs'"""
    home = tmp_path / "home"
    cache = a_cache(home)
    (home / "runs" / "w.json").write_text(json.dumps({"state": runs.WAITING, "worktree": str(tmp_path / "copy")}))
    said = []
    done = disk.clean_cache(home, say=said.append)
    assert done["removed"] == [] and "a registered run needs" in done["refused"] and (cache / "making").exists()
    (home / "runs" / "w.json").unlink()
    (cache / "making" / "k-2").mkdir()  # a make started a minute ago
    assert "a make may be in progress" in disk.clean_cache(home, say=said.append)["refused"]
    (cache / "making" / "k-2").rmdir()
    os.utime(cache / "making", (time.time() - 2 * disk.YOUNG_SECONDS,) * 2)
    done = disk.clean_cache(home, names=("making",), say=said.append)
    assert done["removed"] == ["making"] and (cache / "checkouts" / "o1").exists(), done
    done = disk.clean_cache(home, say=said.append)
    assert sorted(done["removed"]) == ["checkouts", "evidence", "pages", "tmpab12"] and done["refused"] is None, said
    assert sorted(path.name for path in cache.iterdir()) == ["concepts", "convex-parts", "drops"]
    assert (home / "store" / "objects" / "blob").read_text() == "kept"
    assert any(line.startswith(f"kept {cache / 'drops'}: paid drops") for line in said), said


def test_clean_cache_makes_checkout_copies_links_even_with_a_run_live(tmp_path):
    """2026-10-27: checkouts grew 16 GB in an hour while a run walked its rows, and clean-cache refused while it ran.
    Break: score/conductor/disk.py: 'relinked = relink_checkouts(home, say) if "checkouts" in names else 0.0' ->
    'relinked = 0.0'"""
    home = tmp_path / "home"
    store = Store.in_folder(home / "store")
    made = tmp_path / "made"
    made.mkdir()
    (made / "big.bin").write_bytes(b"x" * 4096)
    output = store.put_tree(made)
    checked = store.checkout(output) / "big.bin"
    checked.unlink()  # a checkout an earlier commit made as a copy
    checked.write_bytes(b"x" * 4096)
    checked.chmod(0o444)
    (home / "runs").mkdir()
    (home / "runs" / "w.json").write_text(json.dumps({"state": runs.WAITING, "worktree": str(tmp_path / "copy")}))
    said = []
    done = disk.clean_cache(home, say=said.append)
    assert "a registered run needs" in done["refused"] and done["removed"] == [], done
    assert checked.samefile(store.objects.path(f"blobs/{store.listing(output)['big.bin']}")), said
    assert any(line.startswith("relinked 1 checkouts") for line in said), said


def test_relink_pixal_links_only_old_takes_the_store_holds_and_removes_nothing(tmp_path):
    """2026-10-28: 16 GB free of 91, work/pixal 20.5 GB, most of it kept nowhere else.
    Break: score/conductor/disk.py: '    if not blob.is_file():\n        return "not held in the store"' -> '    if False:
    \n        return "not held in the store"' (a take the store lacks is lost), or '    if now - status.st_mtime <
    YOUNG_SECONDS:' -> '    if False:' (a take a run is writing is linked)"""
    home = tmp_path / "home"
    store = Store.in_folder(home / "store")
    made = tmp_path / "made"
    made.mkdir()
    (made / "raw.glb").write_bytes(b"raw" * 1000)
    (made / "new.glb").write_bytes(b"new" * 1000)
    output = store.put_tree(made)
    pixal = home / "work" / "pixal"
    (pixal / "t.svviews").mkdir(parents=True)
    for name, data in (("t.glb", b"raw" * 1000), ("young.glb", b"new" * 1000), ("t-final.glb", b"only here"),
                       ("t.svviews/input.png", b"raw" * 1000)):
        (pixal / name).write_bytes(data)
    old = time.time() - 2 * disk.YOUNG_SECONDS
    for name in ("t.glb", "t-final.glb", "t.svviews/input.png"):
        os.utime(pixal / name, (old, old))
    for blob in store.objects.path("blobs").iterdir():  # a linked file shows its blob's time
        os.utime(blob, (old, old))
    done = disk.relink_pixal(home)
    blob = store.objects.path(f"blobs/{store.listing(output)['raw.glb']}")
    assert done["relinked"] == 2 and (pixal / "t.glb").samefile(blob) and (pixal / "t.svviews/input.png").samefile(blob)
    assert done["kept"] == {"not held in the store": 1, "changed in the last 15 minutes": 1}, done
    assert (pixal / "t-final.glb").read_bytes() == b"only here" and (pixal / "young.glb").stat().st_nlink == 1
    assert (pixal / "t.glb").read_bytes() == b"raw" * 1000 and not list(pixal.rglob("*.partial"))
    assert disk.relink_pixal(home)["kept"]["already a link to its blob"] == 2


def test_offload_pixal_frees_only_painted_takes_the_library_hands_back_whole(tmp_path, monkeypatch):
    """2026-10-28: work/pixal held the only copy of every paid take on one disk.
    Break: score/conductor/disk.py offload_pixal: 'why = held_whole_why(takes, take, folder, home, report, written)'
    -> 'why = None' (a take the library hands back changed is removed), or drop 'if refused:' and its return (takes
    freed under a live run)."""
    real = disk.pixal_takes()
    home = tmp_path / "home"
    pixal = home / "work" / "pixal"
    (home / "design" / "surfaces").mkdir(parents=True)
    (home / "design" / "surfaces" / "p.json").write_text(json.dumps({"takes": {"a-s1": {}, "b-s1": {}, "c-s1": {}}}))
    for take in ("a-s1", "b-s1", "c-s1", "d-s1"):
        (pixal / f"{take}.svviews").mkdir(parents=True)
        for name in (f"{take}.glb", f"{take}-final.glb", f"{take}.svviews/input.png"):
            (pixal / name).write_bytes(take.encode() * 100)
    old = time.time() - 2 * disk.YOUNG_SECONDS
    for path in pixal.rglob("*"):
        if not path.name.startswith("c-s1"):
            os.utime(path, (old, old))
    asked = []

    def taken_in(takes, folder, commit, scratch):
        asked.extend(takes)
        return {"new": [f"take/{real.take_id(take)}@1" for take in takes], "unchanged": [], "changed draft": [],
                "new version": [], "refused": [], "saved": {"committed": "x", "pushed": True, "why": ""}}
    stand_in = type(real)("pixal_takes")
    stand_in.__dict__.update({**real.__dict__, "taken_in": taken_in, "upstream_holds": lambda take: True,
                              "newest_record": lambda take: {"address": f"take/{real.take_id(take)}@1"},
                              "read_back": lambda take, folder, scratch:
                              "b-s1.svviews/input.png came back with other bytes" if take == "b-s1" else None})
    monkeypatch.setattr(disk, "pixal_takes", lambda: stand_in)
    (home / "runs").mkdir()
    (home / "runs" / "w.json").write_text(json.dumps({"state": runs.WAITING, "worktree": str(tmp_path / "copy")}))
    done = disk.offload_pixal(home, commit="0" * 40)
    assert "a registered run needs" in done["refused"] and (pixal / "a-s1.glb").exists() and not asked, done
    (home / "runs" / "w.json").unlink()
    done = disk.offload_pixal(home, commit="0" * 40)
    assert asked == ["a-s1", "b-s1"] and done["freed"] == 1, done
    kept = {why: takes for why, takes in done["kept"].items() if why != "not whole (no raw or final model)"}
    assert kept == {"changed in the last 15 minutes": ["c-s1"],  # the repository's people takes are not here: not whole
                    "read back: b-s1.svviews/input.png came back with other bytes": ["b-s1"]}, done
    assert not list(pixal.glob("a-s1*")), list(pixal.iterdir())
    assert all((pixal / name).exists() for name in ("b-s1.glb", "c-s1.glb", "d-s1.glb", "b-s1.svviews/input.png"))


def a_copy(repo, folder, name, home):
    """A frozen copy `name` of `repo` under `folder` with its home: the design copied read-only, the rest linked."""
    path = folder / name
    frozen.git(repo, "worktree", "add", "-q", "--detach", str(path), "HEAD")
    frozen.home_copy(path, home)
    (frozen.home_of(path) / "design" / "plan.json").chmod(0o444)
    (frozen.home_of(path) / "design").chmod(0o555)
    old = time.time() - 2 * disk.YOUNG_SECONDS
    os.utime(path, (old, old))
    os.utime(frozen.home_of(path), (old, old))
    return path


def test_clean_frozen_removes_only_the_copies_no_run_needs_and_never_what_they_link_to(tmp_path):
    repo, home = tmp_path / "checkout", tmp_path / "home"
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q",
                    "--allow-empty", "-m", "one"], check=True)
    (home / "store").mkdir(parents=True)
    (home / "store" / "object").write_text("kept")
    (home / "design").mkdir()
    (home / "design" / "plan.json").write_text("{}")
    (home / "runs").mkdir()
    folder = home / "frozen"
    folder.mkdir()
    dead, waiting, worked = (a_copy(repo, folder, name, home) for name in ("1-dead", "2-waiting", "3-worked"))
    young = folder / "4-young"
    young.mkdir()
    (home / "runs" / "w.json").write_text(json.dumps({"state": runs.WAITING, "worktree": str(waiting)}))
    (home / "runs" / "e.json").write_text(json.dumps({"state": "ended", "worktree": str(dead)}))
    process = subprocess.Popen(SLEEP, cwd=frozen.home_of(worked))
    try:
        time.sleep(0.3)
        said = []
        done = disk.clean(home, say=said.append)
        assert done["removed"] == ["1-dead"] and done["failed"] == [], said
        assert sorted(done["kept"]) == ["2-waiting", "3-worked", "4-young"]
        assert not dead.exists() and not frozen.home_of(dead).exists() and waiting.exists() and worked.exists()
        assert (home / "store" / "object").read_text() == "kept" and (home / "design" / "plan.json").exists()
        assert str(dead) not in frozen.git(repo, "worktree", "list")
        (home / "runs" / "broken.json").write_text("{")
        with pytest.raises(disk.Unprovable):
            disk.clean(home, say=said.append)
        assert waiting.exists()
    finally:
        process.kill()
        process.wait()
        for path in folder.rglob("*"):
            if path.is_dir() and not path.is_symlink():
                path.chmod(0o755)


def a_library_checkout(tmp_path):
    """The conductor's clone of a bare repository standing in for score_lib's origin, one push behind it (a second
    clone pushed past it)."""
    origin, checkout, other = tmp_path / "origin.git", tmp_path / "score_lib", tmp_path / "other"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(origin)], check=True)
    for clone in (checkout, other):
        subprocess.run(["git", "clone", "-q", str(origin), str(clone)], check=True, capture_output=True)
        for key, value in (("user.name", "t"), ("user.email", "t@t"), ("commit.gpgsign", "false")):
            frozen.git(clone, "config", key, value)
    (checkout / "index.json").write_text("{}")
    frozen.git(checkout, "add", "index.json")
    frozen.git(checkout, "commit", "-q", "-m", "first")
    frozen.git(checkout, "push", "-q", "-u", "origin", "HEAD:main")
    frozen.git(other, "pull", "-q", "origin", "main")
    (other / "entry.json").write_text("{}")
    frozen.git(other, "add", "entry.json")
    frozen.git(other, "commit", "-q", "-m", "pushed from elsewhere")
    frozen.git(other, "push", "-q", "origin", "HEAD:main")
    return checkout


def test_score_lib_pull_only_fast_forwards_and_status_counts_after_a_fetch(tmp_path):
    """2026-10-28: boot.sh clones score_lib once and nothing pulls it, so its pushes may fail non-fast-forward.
    Break: score/conductor/library_checkout.py: '    if found["changes"] or found["local_commits"]:' -> '    if False:'
    (a pull over local commits or changes goes on), or '    fetched = git(root, "fetch", "-q", "origin")' ->
    '    fetched = git(root, "status")' (behind reads 0 against a stale origin ref), or in push_check
    '    if tried.returncode == 0:' -> '    if True:' (a refused push reads accepted)"""
    from score.conductor import library_checkout
    checkout = a_library_checkout(tmp_path)
    found = library_checkout.status(checkout)
    assert (found["upstream"], found["ahead"], found["behind"], found["fetch"]) == ("origin/main", 0, 1, ""), found
    assert "update by push" in found["last_push"] and found["changes"] == [], found
    assert found["remote"] == str(tmp_path / "origin.git") and "rejected" in found["push"], found  # behind origin
    frozen.git(checkout, "remote", "set-url", "origin", f"https://u:secret@{tmp_path}/origin.git")
    assert library_checkout.remote(checkout) == f"https://{tmp_path}/origin.git"
    frozen.git(checkout, "remote", "set-url", "origin", str(tmp_path / "origin.git"))
    (checkout / "local.json").write_text("{}")
    frozen.git(checkout, "add", "local.json")
    frozen.git(checkout, "commit", "-q", "-m", "a local commit")
    held = frozen.git(checkout, "rev-parse", "HEAD")
    found, refusal = library_checkout.pull(checkout)
    assert "1 local commits" in refusal and found["local_commits"][0].endswith("a local commit"), (refusal, found)
    assert frozen.git(checkout, "rev-parse", "HEAD") == held
    frozen.git(checkout, "reset", "-q", "--hard", "HEAD~1")
    (checkout / "index.json").write_text('{"changed": 1}')
    assert "1 local changes" in library_checkout.pull(checkout)[1]
    assert (checkout / "index.json").read_text() == '{"changed": 1}'
    frozen.git(checkout, "checkout", "-q", "--", "index.json")
    found, refusal = library_checkout.pull(checkout)
    assert refusal == "" and found["behind"] == 1 and (checkout / "entry.json").is_file(), (refusal, found)
    assert library_checkout.status(checkout)["behind"] == 0
    assert library_checkout.status(checkout)["push"] == ""  # up to date with origin: a dry push is accepted


def take_views(source, folder):
    """A per-take call (the finish route's views, made one take a call): the take's views from its model."""
    folder.mkdir(parents=True)
    (folder / "views.npz").write_text(f"views of {pathlib.Path(source).read_text()}")
    return {"views": 3}


def test_clean_kept_drops_only_the_kept_no_current_key_asks_for(tmp_path, monkeypatch):
    """2026-10-29: kept jobs outlive their outputs, so they are swept once no current key could ask for them: never
    one still asked for, never by age.
    Break: score/conductor/disk.py asked_by: 'return code == entry["code"] and entry["system"]' -> 'return False and
    entry["system"]' (the crate's views, still asked for, are swept); or drop 'and \\\n            all(input_stands('
    (the lamp's views, made from its old model, stay)."""
    from score import checks, contracts, graph, stages
    kept = stages.kept_module()
    home, models = tmp_path / "home", tmp_path / "pixal"
    (home / "runs").mkdir(parents=True)
    models.mkdir()
    for take in ("crate", "lamp"):
        (models / f"{take}.glb").write_text(f"{take} model")
    for name in (kept.MAKING, kept.CODE):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("PROPS_HOME", str(home))
    monkeypatch.setenv(kept.STORE, str(home / "store"))

    def make_views(inputs, out, seed, params):
        (out / "views.json").write_text(json.dumps({take: take_views(inputs[f"model {take}"], out / take)
                                                    for take in ("crate", "lamp")}))

    def row(params):
        return graph.Stage("toy-views", "place", stages.per_take_kept(make_views, "take_views", lambda found: found[1]),
                           contracts.Contract("toy-views", 1, lambda folder: []),
                           (checks.Check("views", lambda output, inputs, evidence: checks.Verdict(
                               "views", checks.PASS, "made")),),
                           files={f"model {take}": str(models / f"{take}.glb") for take in ("crate", "lamp")},
                           params=params)

    def runner(params):
        return graph.Runner([row(params)], graph.Environment("toy", 1, {}), Store.in_folder(str(home / "store")))

    made = runner({})
    made.run_node(made.stages["toy-views"], "airlock")
    old = time.time() - 2 * disk.YOUNG_SECONDS
    os.utime(home / "store" / "cache" / "making", (old, old))  # no make in progress
    systems, said = {kept.digest(kept.python_system())}, []
    assert disk.clean_kept(home, runner=runner({}), systems=systems, say=said.append)["dropped"] == 0
    (models / "lamp.glb").write_text("lamp model, fixed")
    assert disk.clean_kept(home, runner=runner({}), systems=systems, say=said.append)["dropped"] == 1
    assert [entry["record"] for _, entry in kept.entries()] == [{"views": 3}]  # the crate's, still asked for
    done = disk.clean_kept(home, runner=runner({"views": "finer"}), systems=systems, say=said.append)
    assert done["dropped"] == 1 and done["refused"] is None and not list(kept.entries())  # the row's code moved
