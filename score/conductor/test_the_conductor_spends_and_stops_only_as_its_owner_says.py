"""score.conductor's invariant: the conductor spends and stops only as its owner says. It grows only for the owner's
run that asks for more cores than it has (never an agent's, never under the kill switch's latch, never while a run is
live), and for a Buy on the idle size before it prices (its command started again at the boot on the batch size, with
its launch settings; one recorded over two hours before is dropped) and shrinks only after 30 idle minutes with nothing busy (a claim, a waiting run, a parked machine, a frozen copy
in use, a hold); its ask carries the token read by name and only grow or shrink, and a failed ask takes its resize
mark back. Its own bill never enters the batch's spend, and every paid point refuses while the batch project is the
conductor's. Only the owner's process pulls the kill switch, which stops every run (and the processes left in a gone
run's frozen copy), closes the pools before it releases every parked machine, and latches every `score` command free
only; Stop this batch does the same without the latch. A detached run is capped in score-runs.slice at the memory
less 6 GB, a step's own scope inherits it, and off a conductor nothing changes; on the cluster's home it is a Job of
its own beside the conductor's pod, carrying no secret's value, and its health there is read from the pods. Its health names what the Machine card
reads and its log tails carry no secret. The free end-to-end check (`dry`) passes every step in one line. No run
starts under the data disk's floor, the health warns there, and clean-frozen removes only the frozen copies no run
needs and no process works in, never what their homes link to, and nothing while it cannot tell; clean-cache
makes the checkouts' copies links to the stored blobs even with a run live; clean-kept drops only the kept jobs no
current key asks for; `disk` accounts for the whole data disk, store-gc removes only the blobs nothing names and only
with no run live, and the sweep frees room itself, asking the owner only for a bigger disk, priced.

Break that turns it red: in size.decide grow while a run is live (drop the claims/running wait); in size.busy
leave out the commands ask_grow_for recorded (a Buy on the idle size never grows it); in kill.stop_everything
release the parked machines before closing the pools, or drop its `stop_cluster` call (score's cluster Jobs left
running), or pass no `every_box` to cluster_stopper (a cap stop leaves another box's Jobs running), or drop the
`every_box_stops` call (the runner's machines keep billing past the cap); or in logs drop the secret-shape test (an AIza key reaches the
tails); or in disk.kept drop the registered-run test (a waiting run's copy is removed); or in disk.said_by drop the
ProcessLookupError catch (a process ending mid-read crashes store-evict); or in cluster.carried_environment drop the
SECRET_NAME test (the sync token's value lands in a drive Job's spec), or drop its READER_NAMES (the drive pod reads no
secret by name: `claude` has no login, env1 2026-11-08); or in score/__main__.py default_jobs drop the cluster
record's jobs (a price on the cluster worked out on the node's cores); or in cluster.pod_view read an unanswered
cluster as no units (a dead cluster shows the conductor fine); or in cluster.pod_log drop `or own_namespace()` (a
home whose record names another namespace reads the logs of `score`'s pods); or in cluster.drive_job write `echo $$`
(Kubernetes hands the shell `echo $`, and a detached run on the cluster waits for a pid that never comes); or in
cluster.drive_job drop the cpu limit (the namespace's default limit of 1 under a request of 8 makes every drive pod
invalid), or drop its cap at drive_room, or raise DEFAULTS past it (a drive pod asking more than the conductor's
node leaves never schedules, every Buy failed 2026-11-10); or in cluster.detach drop the delete on TimeoutError (a Job whose pod never starts keeps making it again);
or in cluster.drive_job let the pods' PROPS_HOME win over the run's (the drive reads the live design, not its frozen
copy, and a sync pass's plan rewrite stops every line mid-run, env1 2026-11-08).
"""
import datetime
import io
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import time

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from score import conductor  # noqa: E402
from score.adapters import compute  # noqa: E402
from score.adapters.compute import guard  # noqa: E402
from score.conductor import cluster, disk, health, kill, logs, size, slices  # noqa: E402
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


# --- size: grow for the owner's run, shrink when idle ------------------------------------------------------------------

NOW = 10_000_000
WAITING = {**IDLE, "waiting": 1, "wanted": 16}
PASSING = {**IDLE, "passing": 1, "held": ["sync-pass-4242"]}

# size.decide's answers: (row, busy view, cores, idle since, now, latched) -> (action, a word its reason holds or None)
DECIDED = [
    ("grow for a waiting run", WAITING, 2, 0, 100, False, size.GROW, "waits for 16 cores"),
    ("no grow while a claim is live", {**WAITING, "claims": 1}, 2, 0, 100, False, None, "live runs"),
    ("no grow while a run is live", {**WAITING, "running": 1}, 2, 0, 100, False, None, "live runs"),
    ("no grow under the kill switch's latch", WAITING, 2, 0, 100, True, None, "free-only latch"),
    ("no shrink before thirty minutes", IDLE, 16, NOW - 29 * 60, NOW, False, None, "idle 29 of 30"),
    ("shrink after thirty idle minutes", IDLE, 16, NOW - 31 * 60, NOW, False, size.SHRINK, None),
    ("nothing at the idle size", IDLE, 2, 0, NOW, False, None, "idle size"),
    *[(f"no shrink while {busy}", {**IDLE, busy: 1}, 16, 0, NOW, False, None, busy)
      for busy in ("claims", "running", "waiting", "parked", "frozen", "working")],
    # 2026-11-04: sync passes back to back held the clock at 0 all morning; a pass waits the shrink, never the clock
    ("a pass drains the shrink", PASSING, 16, NOW - 31 * 60, NOW, False, size.DRAIN, "sync-pass-4242"),
    ("no drain before thirty minutes", PASSING, 16, NOW - 29 * 60, NOW, False, None, None),
    ("the pass ended: shrink", {**PASSING, "passing": 0, "held": []}, 16, NOW - 31 * 60, NOW, False, size.SHRINK,
     None),
]

# a run asking for size: (conductor's cores or None off one, jobs, --oversubscribe, an agent's) -> (waits' start, a
# Buy's wait's start, the default jobs of a run given none of 8)
ASKED_SIZE = [
    (None, 16, False, False, None, None, 8),  # not a conductor: refused as on the PC
    (2, 16, False, False, "16 jobs on 2 cores: waiting", "2 cores: a Buy prices on the batch size", 2),
    (2, 2, False, False, None, "2 cores: a Buy prices on the batch size", 2),  # fits
    (2, 16, True, False, None, "2 cores: a Buy prices on the batch size", 2),  # --oversubscribe runs as asked
    (2, 16, False, True, None, "2 cores: a Buy prices on the batch size", 2),  # an agent's run never grows it
    (2, 17, False, False, None, "2 cores: a Buy prices on the batch size", 2),  # more than the batch size has
    (16, 16, False, False, None, None, 16),  # at the batch size: fits, and a Buy prices at once
]

# a registered `running` entry with this process's pid, registered at an offset from now (None: when unknown); an
# out-of-memory kill leaves an entry `running`, and a later process given its pid is not the run
ENTRIES = [(datetime.timedelta(seconds=5), True), (-datetime.timedelta(days=400), False), (None, False)]


def test_the_conductor_spends_and_stops_only_as_its_owner_says(home, monkeypatch):
    for row, view, cores, idle_since, now, latched, action, word in DECIDED:
        found = size.decide(view, cores, RECORD, idle_since, now, latched)
        assert found[0] == action and (word is None or word in found[1]), (row, found)
    assert not size.is_busy(PASSING)  # a pass is no work that keeps the batch size
    tmp_path = home

    def become(cores):
        """This process a conductor of `cores` cores (machine.json and the size function's url), or none at None."""
        if cores is None:
            monkeypatch.delenv(conductor.SIZE_URL, raising=False)
            return
        monkeypatch.setattr(os, "cpu_count", lambda: cores)
        monkeypatch.setenv(conductor.SIZE_URL, "https://size.invalid/")
    (tmp_path / "machine.json").write_text(json.dumps(RECORD))
    monkeypatch.setattr(conductor, "MACHINE", tmp_path / "machine.json")
    monkeypatch.setattr(conductor, "DRAINING", tmp_path / "draining.json")
    for cores_now, jobs, oversubscribe, agent, waits, buy, default in ASKED_SIZE:
        become(cores_now)
        row = (cores_now, jobs, oversubscribe, agent)
        said = size.waits(jobs, oversubscribe, agent=agent)
        assert (said is None) if waits is None else said.startswith(waits), (row, said)
        said = size.buy_waits(None, cores_now)
        assert (said is None) if buy is None else said.startswith(buy), (row, said)
        assert conductor.default_jobs(8) == default, row
    for offset, live in ENTRIES:
        entry = {"pid": os.getpid(), "state": runs.RUNNING}
        if offset is not None:
            at = datetime.datetime.now(datetime.timezone.utc) + offset
            entry["started"] = at.isoformat(timespec="seconds")
        assert size.entry_alive(entry) is live, offset

    # one world: a Buy asks the grow on the idle size before it prices, and starts again at the boot on the batch size
    folders = [tmp_path / name for name in ("runs", "parked", "frozen", "holds", "asked")]
    asked, pokes = folders[4], []
    size.ask_grow_for(["buy", "y1", "--phase", "models"], {"SCORE_CLOUD": "k8s"}, tmp_path / "buy.log", 16, asked,
                      lambda: pokes.append(1))
    view = size.busy(*folders)
    assert pokes == [1] and (view["waiting"], view["wanted"]) == (1, 16)
    assert size.decide(view, 2, RECORD, 0, 100, False)[0] == size.GROW
    started, words = [], []
    assert size.started_asked(words.append, asked, cores=2, start=lambda *a, **k: started.append(a)) == 0
    assert not started and size.asked_grows(asked)  # still waits on the idle size
    assert size.started_asked(words.append, asked, cores=16,
                              start=lambda argv, **k: started.append((argv, k["env"]["SCORE_CLOUD"]))) == 1
    assert started == [(["buy", "y1", "--phase", "models"], "k8s")] and not size.asked_grows(asked)
    size.ask_grow_for(["buy", "y2"], {}, tmp_path / "buy.log", 16, asked, lambda: None)
    late = size.asked_grows(asked)[0][1]["at"] + size.ASKED_HOURS * 3600 + 1
    assert size.started_asked(words.append, asked, cores=16, now=late, start=lambda *a, **k: 1 / 0) == 0
    assert not size.asked_grows(asked) and "not started" in words[-1]
    # ...then a claim, a waiting run, a parked machine and a frozen copy in use, and the holds
    for folder in folders[:2]:
        folder.mkdir(exist_ok=True)
    (tmp_path / "frozen" / "live-copy").mkdir(parents=True)
    (tmp_path / "frozen" / "left-over").mkdir()
    runs.claim("c0ffee", ["a@b"], os.getpid(), folder=tmp_path / "runs")
    runs.register_waiting(["run", "world1", "--jobs", "16"], 16, folder=tmp_path / "runs")
    (tmp_path / "parked" / "machine.json").write_text("{}")
    monkeypatch.chdir(tmp_path / "frozen" / "live-copy")
    assert size.busy(*folders) == {"claims": 1, "running": 0, "waiting": 1, "wanted": 16, "parked": 1, "frozen": 1,
                                   "working": 0, "passing": 0, "held": []}
    # 2026-10-25: a shrink cut the first sync pass after a boot. A hold lasts while its process does; a holder killed
    # mid-way holds nothing
    holds = folders[3]
    with conductor.holding("sync-pass", holds), conductor.holding("reading", holds):
        assert conductor.holds(holds) == [f"reading-{os.getpid()}", f"sync-pass-{os.getpid()}"]
        view = size.busy(*folders)
    assert (view["working"], view["passing"]) == (1, 1) and len(view["held"]) == 2, view
    assert conductor.holds(holds) == [] and not list(holds.glob("*.lock"))
    code = (f"import os, sys, pathlib; sys.path.insert(0, {str(REPO)!r}); from score import conductor; "
            f"h = conductor.holding('film-preview', pathlib.Path({str(holds)!r})); h.__enter__(); "
            "print('held', flush=True); os.kill(os.getpid(), 9)")
    child = subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.PIPE, text=True)
    assert child.stdout.readline().strip() == "held"
    child.wait()
    assert conductor.holds(holds) == [] and not list(holds.glob("*.lock"))  # the dead holder's file is gone

    # the size timer, its asks sent through the real ask with the token read by name: the idle clock counts from the
    # last busy pass, a pass drains the shrink (no new pass while the mark is fresh), the shrink is asked once it ended
    # and marks its resize, the idle size takes the drain back, a failed grow takes its resize mark back, and an ask is
    # only grow or shrink
    become(16)
    monkeypatch.setattr(runs, "boot_time", lambda: 0)
    reader = tmp_path / "reader"
    reader.write_text("#!/bin/sh\n[ \"$1\" = score-conductor-size-token ] && echo the-token\n")
    reader.chmod(0o700)
    monkeypatch.setenv(size.READER, str(reader))
    sent, down, state = [], [], tmp_path / "size-state.json"

    class Answer(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def opener(request, timeout):
        if down:
            raise RuntimeError("the size function is down")
        sent.append((request.full_url, request.get_header("X-score-size-token"), json.loads(request.data)))
        return Answer(b"powering off")

    def asker(action):
        return size.ask(action, opener=opener)

    def tick(view, now):
        return size.tick(say=lambda line: None, now=now, asker=asker, state_path=state, view=view)["action"]
    assert [tick({**IDLE, "claims": 1}, NOW), tick(IDLE, NOW + 29 * 60), tick(PASSING, NOW + 31 * 60)] == [
        None, None, size.DRAIN] and sent == []
    assert size.draining(NOW + 32 * 60) and not size.draining(NOW + 31 * 60 + size.DRAIN_MINUTES * 60 + 1)
    assert tick({**PASSING, "passing": 0, "held": []}, NOW + 36 * 60) == size.SHRINK
    assert sent == [("https://size.invalid/", "the-token", {"action": "shrink"})]
    assert size.draining(NOW + 36 * 60)  # the mark stays until the machine is small
    assert json.loads(conductor.RESIZING.read_text())["action"] == size.SHRINK  # its power-off is a resize's
    become(2)  # booted at the idle size: passes go on again
    assert tick({**IDLE, "held": []}, NOW + 40 * 60) is None and not conductor.DRAINING.exists()
    down.append(1)  # a waiting run asks the grow while the size function is down: the mark is taken back
    with pytest.raises(RuntimeError):
        tick(WAITING, NOW + 41 * 60)
    assert not conductor.RESIZING.exists() and len(sent) == 1
    down.clear()
    assert tick(WAITING, NOW + 42 * 60) == size.GROW
    assert sent[1:] == [("https://size.invalid/", "the-token", {"action": "grow"})]
    assert json.loads(conductor.RESIZING.read_text())["action"] == size.GROW
    with pytest.raises(ValueError):
        asker("delete")
    assert len(sent) == 2

    # off a conductor the size timer asks nothing and a hold writes nothing
    become(None)
    assert size.tick(say=lambda line: None, asker=lambda action: 1 / 0)["action"] is None
    monkeypatch.setattr(conductor, "HOLDS", tmp_path / "off-holds")
    with conductor.holding("sync-pass"):
        assert not conductor.HOLDS.exists()


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
                                      close_pools=lambda: ["run-1"], latched=False,
                                      stop_cluster=lambda: 'job.batch "score-r-a-g0" deleted')
        live.wait(10)
    finally:
        live.kill()
        live.wait()
    assert report["runs"] == [live.pid] and released == [("m1", "fr-par-2", "t1")] and report["pools"] == ["run-1"]
    assert report["free_only"] is None and not conductor.free_only()
    assert list(conductor.HOME.glob("batch-stop-*.json")) and not list(conductor.HOME.glob("kill-*.json"))
    assert report["cluster_jobs"] == 'job.batch "score-r-a-g0" deleted'  # score's cluster Jobs too (#95)
    # the env1 cap's stop (plan B4): two boxes' Jobs, Stop this batch deletes its own box's, the cap's stop both, and
    # every runner machine and leftover with them
    jobs = {"score-r-a-g0": "conductor", "score-r-b-g0": "pc"}

    def stopper(every_box=False):
        def stop():
            gone = sorted(name for name, box in jobs.items() if every_box or box == "conductor")
            for name in gone:
                del jobs[name]
            return gone
        return stop

    class Cloud:
        def stop_runner_servers(self):
            return ["r-1"]

        def clean_leftovers(self):
            return {"machines": [("scw-score-l4", "a SCORE pool's machine that is no node")], "disks": []}
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(kill, "cluster_stopper", stopper)
        patch.setenv("SCORE_CLOUD", "k8s")
        kill.stop_everything("owner", "this batch", folder=home / "runs", parked=home / "empty", latched=False)
        assert jobs == {"score-r-b-g0": "pc"}  # another box's run is not this stop's
        with pytest.raises(ValueError):
            kill.cap_stop(" ")
        report = kill.cap_stop("past the stop line", folder=home / "runs", parked=home / "empty", cloud=Cloud())
    assert jobs == {} and report["cluster_jobs"] == ["score-r-b-g0"] and report["machines"] == ["r-1"]
    assert report["leftovers_cleaned"]["machines"] and report["free_only"] is None and not conductor.free_only()
    assert list(conductor.HOME.glob("cap-stop-*.json"))


def test_a_stop_ends_every_process_left_in_the_copy_of_a_run_gone_and_leaves_a_stopping_runs_to_it(home, monkeypatch):
    """2026-10-26: after Stop this batch six processes of the stopped run worked on in its frozen copy for an hour and
    held the checkout; a second stop found no run and ended none. 2026-11-05: two processes naming a stopped free run's copy
    by SCORE_FROZEN or command line, not their working folder, held every carry off; stop-batch found none.
    2026-11-05 too: stop-batch ended three detached free runs 2.1 minutes in, each still working out its claim, so in
    no registry yet.
    Break: kill.leftovers -> frozen.users only (the two by name stay), or drop its `pid not in passes` (the sync pass
    is ended), or drop kill.starting (the starting run is ended) or its young or owner test (the old copy's owner, or
    the gone copy's unmarked processes, stay), or drop `+ starting_runs(frozen_folder)` in stop_everything (a starting
    run goes on past the stop)."""
    (home / "runs").mkdir()
    gone, stopping = home / "frozen" / "20261026-081445-1", home / "frozen" / "20261026-091445-2"
    gone.mkdir(parents=True)
    (home / "frozen" / "20261026-081445-1.home").mkdir()
    stopping.mkdir()
    named = [*SLEEP, f"{gone}/score/run.py"]  # the copy as an argument of its own, as a run names it
    env = {**os.environ, "SCORE_FROZEN": str(gone)}
    begun, old = home / "frozen" / "20261105-101500-3", home / "frozen" / "20261105-081500-4"
    begun.mkdir(), old.mkdir()
    past = time.time() - disk.YOUNG_SECONDS - 60
    os.utime(old, (past, past))  # an owner past the grace: a run gone, not starting
    owner = {"SCORE_FROZEN_OWNER": "1"}
    left = [subprocess.Popen(SLEEP, cwd=gone), subprocess.Popen(SLEEP, cwd=f"{gone}.home"),
            subprocess.Popen(named, cwd=home), subprocess.Popen(SLEEP, cwd=home, env=env),  # 2026-11-05: by name only
            subprocess.Popen(SLEEP, cwd=old, env={**os.environ, **owner, "SCORE_FROZEN": str(old)})]
    begin = subprocess.Popen(SLEEP, cwd=home, env={**os.environ, **owner, "SCORE_FROZEN": str(begun)})
    # a `score run` still starting from the checkout, before any copy (2026-11-06: 54 min, the pin held). Break: in
    # kill.stop_everything, drop `+ checkout_starting(checkout)`
    checkout = home / "checkout"
    checkout.mkdir()
    starting_here = subprocess.Popen([*SLEEP, "-m", "score", "run", "world1"], cwd=checkout)
    monkeypatch.setattr(conductor, "HOLDS", home / "holds")
    passing = subprocess.Popen([sys.executable, "-c", f"import sys, time; sys.path.insert(0, {str(REPO)!r}); "
                                f"from score import conductor; h = conductor.holding('sync-pass', "
                                f"__import__('pathlib').Path({str(home / 'holds')!r})); h.__enter__(); "
                                f"print('held', flush=True); time.sleep(60)"], cwd=home, env=env, stdout=subprocess.PIPE,
                               text=True)
    assert passing.stdout.readline().strip() == "held"
    run, node = subprocess.Popen(SLEEP, cwd=stopping), subprocess.Popen(SLEEP, cwd=stopping)
    runs.claim("c0ffee", ["draw@hangar"], run.pid, folder=home / "runs")
    time.sleep(0.3)  # the children are in their folders before the stop looks
    try:
        report = kill.stop_everything("agent", "the batch", folder=home / "runs", parked=home / "empty",
                                      close_pools=lambda: [], latched=False, frozen_folder=home / "frozen",
                                      checkout=checkout)
        assert sorted(entry["pid"] for entry in report["leftovers"]) == sorted(process.pid for process in left)
        assert all(process.wait(5) == -15 for process in left)
        assert node.poll() is None  # the stopping run ends its own (remove_owned)
        # a run still starting in its new copy, not registered yet, is stopped as a run, never swept as a leftover
        # (2026-11-05: checkout 25, starting at a stop-batch, was spared and went on for hours)
        assert sorted(report["runs"]) == sorted([run.pid, begin.pid, starting_here.pid]) and begin.wait(5) == -15
        assert starting_here.wait(5) == -15
        assert begin.pid not in [entry["pid"] for entry in report["leftovers"]]
        assert passing.poll() is None  # a sync pass's own process is its own to end
        assert all(entry["command"] for entry in report["leftovers"])  # each named, so we learn what they were
    finally:
        for process in (*left, run, node, passing, begin, starting_here):
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
    # On the cluster's home (#76 step 3) the drive pod's memory is the guard's own reckoning: the floor beside the
    # largest kept stage peaks, one a job, each at least the floor, at most the record's cap; inside a pod the guard
    # reads the pod's limit, never the node's; the run's jobs (so its price) are the record's, not the node's cores.
    gib = 2 ** 30
    assert cluster.memory_request({"a": 10 * gib, "b": 2 * gib, "c": 1 * gib}, 2, 6 * gib, 64) == 22 * gib
    assert cluster.memory_request({}, 3, 6 * gib, 64) == 24 * gib  # never measured: the floor each
    assert cluster.memory_request({"a": 50 * gib}, 2, 6 * gib, 40) == 40 * gib
    cgroup = pathlib.Path(tempfile.mkdtemp())
    (cgroup / "memory.max").write_text(f"{8 * gib}\n")
    (cgroup / "memory.current").write_text(f"{5 * gib}\n")
    (cgroup / "memory.stat").write_text(f"anon 1\ninactive_file {gib}\n")
    assert cluster.pod_memory(cgroup) == (8 * gib, 4 * gib)
    fake = type("graph", (), {"AVAILABLE": staticmethod(lambda: 100 * gib), "TOTAL": staticmethod(lambda: 128 * gib)})
    assert not cluster.guard_pod_memory(fake, cgroup, environment={})  # outside a pod nothing changes
    assert fake.AVAILABLE() == 100 * gib
    assert cluster.guard_pod_memory(fake, cgroup, environment={"KUBERNETES_SERVICE_HOST": "10.0.0.1"})
    assert (fake.AVAILABLE(), fake.TOTAL()) == (4 * gib, 8 * gib)
    (cgroup / "memory.max").write_text("max\n")
    assert cluster.pod_memory(cgroup) is None
    from score import __main__ as command, graph
    record = cgroup / "cluster.json"
    record.write_text(json.dumps({"image": "x", "jobs": 12}))
    original = cluster.RECORD
    cluster.RECORD = record
    try:
        assert command.default_jobs() == 12
    finally:
        cluster.RECORD = original
    assert command.default_jobs() == graph.JOBS  # no record, no conductor here


def test_a_detached_run_is_its_own_scope_in_the_slice_and_off_a_conductor_in_none(tmp_path):
    from score import __main__ as command
    prefix = slices.scope_prefix("score-run-x")
    assert prefix[:3] == ["systemd-run", "--user", "--scope"] and "--slice=score-runs.slice" in prefix
    assert "--unit=score-run-x" in prefix and prefix[-1] == "--"
    assert not slices.usable() and command.run_scope(pathlib.Path("/tmp/score-run-x.log")) == []
    # On the cluster's home (#76) the run is a Job of its own, from its frozen copy, beside the conductor's pod, its
    # command the scope's, no retry, no secret's value in its spec; the pid its pod writes is the run's; off it, none.
    assert command.detached_as_pod(["true"], tmp_path / "x.log", {}) is False  # no cluster.json in this home
    found = cluster.record(_written(tmp_path / "cluster.json", {"image": "registry.example/score-conductor@sha256:0"}))
    assert found["jobs"] == 8 and found["namespace"] == "score"
    log, applied = tmp_path / "score-run-20261107T2000Z.log", []
    (tmp_path / "score-run-20261107T2000Z.log.pid").write_text("4242\n")
    environment = {"SCORE_FREE_ONLY": "1", "SCORE_SYNC_TOKEN": "s3cret", "SCORE_LIB_KEY": "k", "PATH": "/usr/bin",
                   "KUBERNETES_SERVICE_HOST": "10.0.0.1", "HOME": "/elsewhere",
                   "PROPS_HOME": "/home/score/.farm-factory-props/frozen/abc.home",
                   "SCORE_SECRET_READER": "/usr/local/bin/score-secret-reader", "SCORE_SECRETS_PROJECT": "a-project"}
    name, pid = cluster.detach(found, ["/py", "stopped.py", "--", "/py", "-m", "score", "run", "world1"], log,
                               "/home/score/.farm-factory-props/frozen/abc", environment, tmp_path,
                               apply=applied.append, wait=lambda log: cluster.started_pid(log, seconds=1))
    job, = applied
    assert (name, pid) == ("score-run-20261107t2000z", 4242) and job["spec"]["backoffLimit"] == 0
    pod = job["spec"]["template"]["spec"]
    assert pod["restartPolicy"] == "Never" and pod["hostPID"] is True
    assert pod["affinity"]["podAffinity"]["requiredDuringSchedulingIgnoredDuringExecution"][0][
        "topologyKey"] == "kubernetes.io/hostname"
    box, = pod["containers"]
    assert box["command"][-8:] == ["/py", "stopped.py", "--", "/py", "-m", "score", "run", "world1"]
    assert box["workingDir"] == "/home/score/.farm-factory-props/frozen/abc"
    assert box["command"][2].replace("$$", "$").startswith("echo $$ >")  # as Kubernetes expands it: the shell's pid
    carried = {variable["name"]: variable.get("value") for variable in box["env"]}
    assert carried["SCORE_FREE_ONLY"] == "1" and carried["PATH"] == "/usr/bin" and carried["HOME"] == "/home/score"
    assert not {"SCORE_SYNC_TOKEN", "SCORE_LIB_KEY", "KUBERNETES_SERVICE_HOST"} & set(carried)
    assert carried["SCORE_SECRET_READER"] == "/usr/local/bin/score-secret-reader"  # a secret read by name, in the pod
    assert carried["SCORE_SECRETS_PROJECT"] == "a-project"
    assert [variable["name"] for variable in box["env"]].count("HOME") == 1
    # its home is the run's frozen one (its design as it started), never the pods' live home a sync pass rewrites
    assert carried["PROPS_HOME"] == "/home/score/.farm-factory-props/frozen/abc.home"
    assert [variable["name"] for variable in box["env"]].count("PROPS_HOME") == 1
    # its processor limit is its request, so a namespace's default limit never makes the pod invalid
    assert box["resources"]["limits"]["cpu"] == box["resources"]["requests"]["cpu"] == "4000m"
    # DEFAULTS fit the conductor's node beside its own pods and CronJobs, and a record asking more is cut to that room,
    # never a pod that cannot schedule (2026-11-10: 16 x 0.5 CPU and 64 GB on the 8-core node, every Buy failed)
    from tools.cloud.k8s import conductor as pods
    room_cpu, room_memory = pods.drive_room()
    assert pods.NODE_TYPE == "POP2-HM-8C-64G" and 0 < room_cpu < pods.millicores(pods.NODE_ALLOCATABLE["cpu"])
    assert 1000 * cluster.DEFAULTS["jobs"] * cluster.DEFAULTS["cpu_per_job"] <= room_cpu
    assert cluster.DEFAULTS["max_memory_gb"] * cluster.GIB <= room_memory
    assert pods.memory_bytes(box["resources"]["requests"]["memory"]) <= room_memory
    greedy = {**found, "jobs": 16, "cpu_per_job": 0.5}
    asked = cluster.drive_job(greedy, ["true"], log, tmp_path, {}, 64 * cluster.GIB)
    wants, = asked["spec"]["template"]["spec"]["containers"]
    assert pods.millicores(wants["resources"]["requests"]["cpu"]) == room_cpu
    assert pods.memory_bytes(wants["resources"]["requests"]["memory"]) <= room_memory
    with pytest.raises(TimeoutError):
        cluster.started_pid(tmp_path / "never.log", seconds=0.01, sleep=lambda seconds: None)
    deleted = []  # a Job whose pod wrote no pid in time is deleted before the error goes on, never left retrying
    with pytest.raises(TimeoutError):
        cluster.detach(found, ["/py", "-m", "score", "run", "world1"], tmp_path / "score-run-stuck.log", tmp_path,
                       {}, tmp_path, apply=applied.append, delete=deleted.append,
                       wait=lambda log: cluster.started_pid(log, seconds=0.01, sleep=lambda seconds: None))
    assert [job["metadata"]["name"] for job in deleted] == ["score-run-stuck"]


def _written(path, found):
    path.write_text(json.dumps(found))
    return path


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
                          "disk_free", "disk", "load", "units", "runs_active", "runs_waiting", "parked_machines", "holds",
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
    # In the cluster's conductor pod (#76 step 5) the card's units come from the cluster's answer, never systemd, and
    # a cluster that does not answer is every unit failed; memory and cores are the pod's own limits.
    labels = {"app.kubernetes.io/name": "score-conductor"}

    def job(unit, stamp, **status):
        return {"kind": "Job", "metadata": {"name": f"{unit}-{stamp}", "creationTimestamp": f"2026-11-07T{stamp}Z",
                                            "labels": {**labels, "app.kubernetes.io/component": unit}},
                "status": status}
    answer = {"items": [
        {"kind": "Pod", "metadata": {"labels": {**labels, "app.kubernetes.io/component": "conductor"}},
         "status": {"containerStatuses": [{"ready": True}, {"ready": True}]}},
        job("sync", "20:00:00", succeeded=1, completionTime="2026-11-07T20:03:00Z"),
        job("sync", "20:05:00", active=1), job("backup", "20:00:00", failed=1)]}
    seen = cluster.pod_view(answer=answer)
    assert seen["units"] == {"sync": "active", "listen": "active", "resume": "active", "backup": "failed"}
    assert seen["last_sync"] == {"at": "2026-11-07T20:03:00Z", "ok": True}
    monkeypatch.setattr(cluster, "kubectl_json", lambda *words: None)
    assert set(cluster.pod_view()["units"].values()) == {"failed"}
    (tmp_path / "cpu.max").write_text("400000 100000\n")
    assert cluster.cores(tmp_path) == 4
    (tmp_path / "cpu.max").write_text("max 100000\n")
    assert cluster.cores(tmp_path) is None
    asked = []
    lines = cluster.pod_log("score-listen.service", 5, run=lambda argv, **_: asked.append(argv) or
                            subprocess.CompletedProcess(argv, 0, "[listen] up\n", ""))
    assert lines == ["[listen] up"] and asked[0][3:7] == ["logs", "pod/score-conductor-0", "-c", "conductor"]
    assert asked[0][1:3] == ["-n", "score"]  # no cluster record here: the default namespace
    record = tmp_path / "cluster.json"
    record.write_text('{"namespace": "score-rehearsal"}')
    monkeypatch.setattr(cluster, "RECORD", record)  # the record's namespace, never a fixed one (the 2026-11-07 rehearsal)
    cluster.pod_log("score-listen.service", 5, run=lambda argv, **_: asked.append(argv) or
                    subprocess.CompletedProcess(argv, 0, "", ""))
    assert asked[1][1:3] == ["-n", "score-rehearsal"]


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
    """2026-10-26: 0.24 GB free of 91 GB and Batch 1 died with "No space left on device"; 2026-11-04: checkout 17 began
    at 10.4 GB free, over the 10 GB floor, and ran out 7 min in.
    Break: disk.launch_refusal's `max(FLOOR_GB, round(written_most(runs_folder), 1))` -> `FLOOR_GB` (a run starts on
    less room than the last one took), or graph/runs.noted's `min(entry.get("disk_lowest", free), free)` -> `free`,
    or launch_refusal's `if evicting(...)` dropped (a run starts while store-evict evicts the blobs it reads, #74), or
    store_evict's `alone` dropped (a second store-evict runs beside the first)."""
    assert disk.launch_refusal(tmp_path, floor=0) is None
    with disk.alone(tmp_path, disk.EVICT_LOCK):
        assert "store-evict is running" in disk.launch_refusal(tmp_path, floor=0)
        assert disk.store_evict(tmp_path, say=lambda line: None)["refused"] == "another store-evict is running"
    assert disk.launch_refusal(tmp_path, floor=0) is None
    refused = disk.launch_refusal(tmp_path / "not-yet", floor=10 ** 6)
    assert refused.startswith("refused: ") and "GB floor" in refused
    folder = tmp_path / "runs"
    folder.mkdir()
    entry = folder / "r1.json"
    entry.write_text(json.dumps({"state": "running"}))
    runs.noted(entry, None)
    started = json.loads(entry.read_text())
    assert started["disk_lowest"] == started["disk_start"] > 0, started
    entry.write_text(json.dumps({**started, "disk_start": 30.0, "disk_lowest": 1.0}))
    runs.noted(entry, None)
    assert json.loads(entry.read_text())["disk_lowest"] == 1.0  # the lowest stays the lowest seen
    assert disk.written_most(folder) == 29.0 * disk.WRITTEN_MARGIN
    entry.unlink()
    (folder / "r2.json").write_text(json.dumps({"disk_start": 10.4, "disk_lowest": 0.1}))  # ran the disk out
    assert disk.written_most(folder) == (10.4 + disk.FLOOR_GB) * disk.WRITTEN_MARGIN
    monkeypatch.setattr(disk, "free_gb", lambda path=None: 20.0)
    assert "floor" in disk.launch_refusal(runs_folder=folder)  # 20 GB free, under the 25.5 measured
    assert disk.launch_refusal(runs_folder=folder, floor=10) is None
    monkeypatch.undo()
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

    class Gone:  # a process that ended between the /proc listing and its read
        name = "4242"

        def __truediv__(self, part):
            return self

        def read_bytes(self):
            raise ProcessLookupError(3, "No such process")

    with pytest.raises(FileNotFoundError):  # read as ended, so working() skips it (store-evict crashed, 2026-11-07)
        disk.said_by(Gone())


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
    '{last['bigger']}' (the owner is never told the price), or steps: drop the clean-scratch step (a killed make's
    work/motion-scratch copies stay, 2026-11-04), or clean_scratch: drop the score_commands refusal (a live `score
    plan`'s copies are cleared under it, 2026-11-11)."""
    home, blobs, named = gc_home(tmp_path)
    monkeypatch.setattr(disk, "REPO", tmp_path)
    monkeypatch.setattr(disk, "mount_of", lambda path: home)
    monkeypatch.setattr(disk, "clean_kept", lambda home, runs_folder, say: {"dropped": 0, "refused": None})
    monkeypatch.setattr(disk, "offload_pixal", lambda home, runs_folder: {"freed": 0, "refused": None, "kept": {}})
    monkeypatch.setattr(disk, "bigger", lambda more, zone: f"{more} GB more, EUR 4.00 a month in {zone}")
    monkeypatch.setattr(disk.offload, "open_bucket", lambda: disk.offload.FolderBucket(tmp_path / "bucket"))
    (home / "logs").mkdir()
    for name, days in (("old.log", disk.LOG_DAYS + 1), ("new.log", 1)):
        (home / "logs" / name).write_text(name)
        os.utime(home / "logs" / name, (time.time() - days * 86400,) * 2)
    free = {"gb": 50.0}
    monkeypatch.setattr(disk, "free_gb", lambda path=None: free["gb"])
    said = []
    (home / disk.MOTION_SCRATCH / "layer-camp-x1" / "camp").mkdir(parents=True)  # a killed make's seed copy
    plan = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)", "-m", "score", "plan"])
    try:  # a live `score plan` (no registered run) judging gates on its copies: they stay
        assert str(plan.pid) in disk.clean_scratch(home)["refused"] and plan.pid in disk.score_commands()
        assert (home / disk.MOTION_SCRATCH / "layer-camp-x1").is_dir()
    finally:
        plan.kill()
        plan.wait()
    monkeypatch.setattr(disk, "score_commands", lambda: [])  # this PC's own runs aside
    done = disk.sweep(home, say=said.append)  # no machine.json: off a conductor, the routine only
    assert not done["escalated"] and [step["step"] for step in done["steps"]] == [
        "clean-frozen", "clean-cache", "clean-kept", "laid-plain", "clean-scratch"], done
    assert list((home / disk.MOTION_SCRATCH).iterdir()) == []  # no run live: the scratch is cleared
    (home / "machine.json").write_text(json.dumps({"zone": "fr-par-2"}))
    free["gb"] = 5.0
    done = disk.sweep(home, say=said.append)
    assert done["escalated"] and [step["step"] for step in done["steps"]][5:] == [
        "relink-pixal", "old-logs", "store-gc", "offload-pixal"], done  # store-evict never: hours a pass waits
    assert not (home / "logs" / "old.log").exists() and (home / "logs" / "new.log").exists()
    assert named["orphan"] not in {path.name for path in blobs.iterdir()} and named["record"] in {
        path.name for path in blobs.iterdir()}
    assert done["bigger"] == "50 GB more, EUR 4.00 a month in fr-par-2" and done["fills"], done
    assert sum(line.startswith("sweep ") for line in said) == 5 + 9, said  # a line a step, each with what it freed
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
    YOUNG_SECONDS:' -> '    if False:' (a take a run is writing is linked), or 'if laid_by_a_row(path, pixal):' -> 'if
    False:' (a people look's take linked, so its row copies a file onto itself: 2026-11-03, SameFileError)"""
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
    # a people look's take file stays a plain copy, and one linked before is copied back
    (pixal / "officer-made-s1.svviews").mkdir()
    look = pixal / "officer-made-s1.svviews/input.png"
    os.link(blob, look)
    again = disk.relink_pixal(home)
    assert again["copied"] == 1 and look.stat().st_nlink == 1 and not look.samefile(blob), again
    assert look.read_bytes() == b"raw" * 1000 and os.access(look, os.W_OK)
    assert disk.relink_pixal(home)["copied"] == 0 and look.stat().st_nlink == 1
    look.unlink()
    os.link(blob, look)  # linked before the rule: every sweep pass copies it back, the disk low or not
    assert disk.laid_plain(home) == {"copied": 1} and look.stat().st_nlink == 1
    # a code build's take files too (2026-11-05: linked, every pixal row's rebuild was refused on input.png)
    # Break: in disk.py `laid_by_a_row`, drop "or code_built(path, pixal)".
    (pixal / "pipe_1.svviews").mkdir()
    (pixal / "pipe_1.svviews/code.json").write_text("{}")
    built = [pixal / "pipe_1.svviews/input.png", pixal / "pipe_1-final.glb", pixal / "pipe_1-2000.glb"]
    for path in built:
        os.link(blob, path)
    assert disk.laid_plain(home)["copied"] == 3 and all(os.access(path, os.W_OK) for path in built)
    assert disk.relink_pixal(home)["copied"] == 0 and (pixal / "pipe_1.svviews/input.png").stat().st_nlink == 1
    assert not disk.code_built(pixal / "t.glb", pixal)
    assert "laid-plain" in [name for name, _ in disk.steps(home, home / "runs", print, False)]


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


def test_offload_pixal_says_a_file_gone_and_one_sweep_or_offload_runs_at_a_time(tmp_path, monkeypatch):
    """2026-10-31: offload-pixal crashed with FileNotFoundError on work/pixal/crowd-made-s1-19000.glb (a link to
    nothing, or a file another offload removed under it), so the sweep never freed work/pixal and the disk filled.
    Break: score/conductor/disk.py take_kept_why: drop the 'gone' test (the link to nothing crashes the offload), or
    alone: 'yield True' for 'yield False' (a second offload or sweep runs beside the first)."""
    real = disk.pixal_takes()
    home = tmp_path / "home"
    pixal = home / "work" / "pixal"
    (home / "design" / "surfaces").mkdir(parents=True)
    (home / "design" / "surfaces" / "p.json").write_text(json.dumps({"takes": {"a-s1": {}, "b-s1": {}}}))
    pixal.mkdir(parents=True)
    for take in ("a-s1", "b-s1"):
        for name in (f"{take}.glb", f"{take}-final.glb"):
            (pixal / name).write_bytes(take.encode() * 100)
    (pixal / "a-s1-19000.glb").symlink_to(tmp_path / "gone.glb")
    old = time.time() - 2 * disk.YOUNG_SECONDS
    for path in pixal.iterdir():
        os.utime(path, (old, old), follow_symlinks=False)
    stand_in = type(real)("pixal_takes")
    stand_in.__dict__.update({**real.__dict__, "taken_in": lambda takes, folder, commit, scratch: {
        "new": [f"take/{real.take_id(take)}@1" for take in takes], "refused": [],
        "saved": {"committed": "x", "pushed": True, "why": ""}}, "upstream_holds": lambda take: True,
        "newest_record": lambda take: {"address": f"take/{real.take_id(take)}@1"},
        "read_back": lambda take, folder, scratch: None})
    monkeypatch.setattr(disk, "pixal_takes", lambda: stand_in)
    with disk.alone(home, "offload-pixal") as first:
        assert first
        done = disk.offload_pixal(home, commit="0" * 40)
    assert "another offload-pixal is running" in done["refused"] and (pixal / "b-s1.glb").exists(), done
    done = disk.offload_pixal(home, commit="0" * 40)
    kept = {why: takes for why, takes in done["kept"].items() if why != "not whole (no raw or final model)"}
    assert kept == {"a file is gone or a link to nothing: a-s1-19000.glb": ["a-s1"]} and done["freed"] == 1, done
    assert (pixal / "a-s1.glb").exists() and not (pixal / "b-s1.glb").exists(), done
    (home / "machine.json").write_text("{}")
    with disk.alone(home, "sweep"):
        said = []
        done = disk.sweep(home, say=said.append)
    assert "another sweep is running" in done["refused"] and not done["steps"], done
    assert not (home / "conductor" / "sweep.json").exists()


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
