"""Invariant of park.py (and the batch steps that park and take): a healthy machine of a kind that cleans up is parked
instead of deleted only while that pays off (an hourly machine until 5 min before its paid hour ends; a card for its
kind's measured cold start, at most 10 min, and only while a claim waits for one); the next claim takes it within
its cleared run and its cap, pays only what it adds and runs on the newest set-up; one nobody took is deleted at its
time with its idle minutes in the ledger, by its --expire process or its ended run's releaser; and nothing parked is
ever deleted early by a sweep or an older expirer (owner, 2026-10-12: no new machine while one is idle; #45: three
L4s stayed parked past their time).

The cloud, ssh and process calls are recorded instead of made; the clean-up commands run in a scratch folder. The
break that turns each red (applied once, seen red, reverted):

- test_a_machine_is_parked_only_while_it_pays_off: in `parkable`, drop `bool(machine.get("healthy")) and ` (row
  unhealthy); or in `leaves_at`, `paid_until(machine, now) - MARGIN_MINUTES * 60` -> `paid_until(machine, now)` (the
  hour-machine rows); or in `parkable`, drop `not batch.STOPPING.is_set() and ` (its first occurrence; row
  its-run-stopping); or in `idle_minutes`, `min(IDLE_CAP_MINUTES, statistics.median(starts))` ->
  `statistics.median(starts)` (row card-cold-start-capped); or in `parkable`, drop `in_a_run() and` (row
  outside-a-run); or `(not card or queued())` -> `True` (the card-no-claim-waiting rows). Its claims: in ledger.py
  `machine_row`, drop `- machine.get("paid_minutes", 0.0) * machine["price"]` (row hour-machine-35-min-left); or in
  `take`, `(record.get("disk_gb") or 0) >= disk_gb` -> `True` (same row); or `record["kind"] == kind` -> `False` (row
  two-kinds-own-kind-first); or in `waiting`, `count += 1` -> `pass` (the card rows a claim waits for); or in
  batch.py `rent_fleet`, `machine = park_taken(fleet, fleet.offers, len(fleet.machines) + 1, "pixal", DISK_GB)` ->
  `machine = None` (row pixal-card-taken-by-its-fleet); or in `parked_within`, `if machine is not None or
  time.time() >= give_up:\n                return machine` -> `return machine` (it asks once; row
  card-its-kind-waits-never-measured); or in `adopt`, the failure's `batch.delete_machine(machine)\n            continue` ->
  `return machine` (row parked-one-not-answering); or the retag's own `except` dropped (row
  parked-one-whose-retag-fails: a card whose tag update failed is deleted as unanswering, card after card:
  2026-11-03); or in `taken_machine`, `"ready": now` -> `"ready": None` (row hour-machine-35-min-left); or in `adopt`,
  drop `batch.compute.require_cloud(f"a parked machine of {kind}")` (row card-never-measured); or `if not
  capacity.reserve_run_slot(len(live_of(run))):` -> `if False:` (row card-of-another-run-at-the-cap). Its expirers:
  the token checked nowhere (each alone is covered by the other): in `release`, `mine = record.get("token") == token`
  -> `mine = bool(record)`, and in `listed`, `path.exists() and json.loads(path.read_text()).get("token") == token`
  -> `path.exists()` (row hour-machine-nobody-took); or in `release`, `if record["unit_minutes"] == 1:` -> `if
  False:` (row card-nobody-took). Its sweep: in batch.py `run_tags`, `f"deadline={deadline:.0f}"` -> `"deadline=0"`
  (every parked row: the live machine is swept at once); or in batch.sweep, drop the `server_id in held` branch
  (every parked row: the parked one with its expirer gone is swept before its time). Its run's releaser: in
  `outlive`, `if record["until"] <= now or` -> `if True or` (row card-its-ended-run-releases: deleted before its
  time); or in `expire`, `while listed(server_id, token):` -> `while True:` (same row: its released card's expirer
  sleeps on); or in `expire`, `if left <= 0:` -> `if True:` (same row: its card's expirer, the card still parked,
  deletes it before its time). Its watchdog: in batch.py `watchdog`, drop `and os.getppid() == holder` (row
  renter-killed-before-its-delete: deleted only at its deadline). What a release and a take leave of the machine's
  /root: `CLEANUPS["pixal"]`'s `rm -rf in out queue logs closed status.json run.log` -> `rm -rf /root/batch`, or
  `STALE_MARKS`' `tail -n +2` -> `tail -n +1` (row pixal-card-taken-by-its-fleet); or `CLEANUPS["meshparts"]` ->
  `"rm -rf /root/mp"` (row second-paid-hour-45-min-left); or moss-sound's rented `rm -rf /root/sfx; {ALL_MARKS}` ->
  `rm -rf /root/sfx` (row moss-card-of-a-rented-card). This PC's card (the this-pc rows, claim after claim): in
  `own_set_up`, drop `if [ -e {KINDS}/{kind}/venv ]; then mv {KINDS}/{kind}/venv venv; fi && ` (a kind's venv never
  comes back), or drop `if [ \"$held\" = none ]; then rm -rf venv; rm -f .*-setup-*; fi && ` (the first claim keeps
  a venv nobody can name); or `ALL_MARKS` -> `"rm -f /root/.*-setup-*"` (similar's clean-up wipes this PC's marks); or
  in `adopt`, drop `if hasattr(cloud, "take"): return here(...)` -> the claim asks a clearance and finds nothing
  parked; or in `park`, drop the here branch's `return False` -> the PC's machine is listed as parked; or in `here`,
  `f"{own_set_up(kind)}; {cleanup_of(machine)}"` -> `own_set_up(kind)` (a last claim's `closed` ends the next worker
  at once); or in `park`, drop the `ends_with(...)` call -> the claim's files stay in the container (2026-11-03: 476 GB
  in their layers); or in `ended_cloud_only`, `os._exit(batch.compute.CLOUD_ONLY_EXIT)` -> `pass` (row this-pc-0-pixal:
  a tool ending on its judge claim's refusal, a job too big for this PC's card, ends as 1, not CLOUD_ONLY_EXIT); or in
  `here`, drop `queue_paused(run, kind)` (the queue's wait spends the deadline); or drop `run.queue_left = None` after a
  take (the next wait starts from the old room).
"""
import json
import os
import pathlib
import shlex
import subprocess
import sys
import threading
import time

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import batch  # noqa: E402
import finish_masks  # noqa: E402,F401  (registers its clean-up)
import ledger  # noqa: E402
import park  # noqa: E402
import pictures  # noqa: E402
import provider  # noqa: E402
import segment  # noqa: E402,F401  (registers its clean-up)
from provider import cloud  # noqa: E402

KIND = "park-test"
OTHER = "park-test-other"  # a kind whose claim waits, so cards of KIND park
HOUR_PRICE = 1.2 / 60  # euros a minute of a machine billed by the hour
CARD_PRICE = 0.8 / 60  # euros a minute of a card, billed by the minute
OFFERS = [provider.Offer(HOUR_PRICE, 0, "cpu-type", "zone-a", HOUR_PRICE, "cpu-32c-128gb", 0, "available")]
CARD_OFFERS = [provider.Offer(CARD_PRICE, 1, "card-type", "zone-a", CARD_PRICE, "gpu-24gb", 0, "available")]
CLEAN = "rm -rf /root/lib/out"
POPEN = subprocess.Popen  # the real one, for a test that runs a tool's process under `calls`
HOST = "192.0.2.1"  # every rented machine's address; this PC's container is PC_HOST
PC_HOST = "172.17.0.2"


class Calls:
    """The cloud, ssh and process calls park.py makes, recorded instead of made; a machine's shell command runs on its
    host's /root, a scratch folder under `roots`."""

    def __init__(self, monkeypatch, roots):
        self.remote, self.retagged, self.deleted, self.armed, self.roots = [], [], [], [], roots
        monkeypatch.setattr(batch, "remote", self.ran)
        monkeypatch.setattr(batch, "arm_self_delete", lambda folder, host, deadline, quiet_minutes=0: self.armed.append(
            deadline))
        monkeypatch.setattr(batch, "start_watchdog", lambda server_id, zone, deadline, folder: os.getpid() + 10 ** 6)
        monkeypatch.setattr(batch, "say", lambda line: None)
        monkeypatch.setattr(cloud, "retag", lambda server_id, zone, tags: self.retagged.append((server_id, tags)))
        monkeypatch.setattr(cloud, "delete", lambda server_id, zone: self.deleted.append(server_id) or True)
        monkeypatch.setattr(park.subprocess, "Popen", lambda *_, **__: type("Expirer", (), {"pid": os.getpid()})())
        monkeypatch.setattr(batch.compute, "require_cleared", lambda what, store=None: {"node": "test"})
        monkeypatch.setitem(park.CLEANUPS, KIND, lambda _machine: CLEAN)
        monkeypatch.setitem(park.CLEANUPS, OTHER, lambda _machine: CLEAN)

    def root_of(self, host):
        """The /root of the machine at `host`."""
        root = self.roots / host
        root.mkdir(parents=True, exist_ok=True)
        return root

    def ran(self, folder, host, command, **_):
        """batch.remote with check=True: the command recorded and run on its machine's /root; a failure raised."""
        self.remote.append(command)
        on_the_machine(command, self.root_of(host))


@pytest.fixture
def calls(monkeypatch, tmp_path):
    """A sandbox with nothing parked, an empty ledger, inside a run; the recorded calls."""
    for name in ("SCORE_MAX_MACHINES", "SCORE_SPEND_TICKET"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("SCORE_RUN_ID", "run-park")  # machines are parked only inside a run (in_a_run)
    found = Calls(monkeypatch, tmp_path / "machines")
    for path in park.PARKED.glob("*.json") if park.PARKED.exists() else ():
        path.unlink()
    ledger.LEDGER.unlink(missing_ok=True)
    batch.STOPPING.clear()
    return found


def machine(minutes_ago, unit_minutes=60, healthy=True, kind=KIND, server_id="m1"):
    folder = pathlib.Path(os.environ["PROPS_HOME"]) / "runs" / server_id
    folder.mkdir(parents=True, exist_ok=True)
    card = unit_minutes == 1
    return {"id": server_id, "zone": "zone-a", "type": "card-type" if card else "cpu-type",
            "class": "gpu-24gb" if card else "cpu-32c-128gb", "cards": 1 if card else 0,
            "price": CARD_PRICE if card else HOUR_PRICE, "unit_minutes": unit_minutes,
            "created": time.time() - minutes_ago * 60, "host": HOST, "kind": kind, "disk_gb": 60,
            "folder": folder, "deleted": None, "ready": time.time() - minutes_ago * 60 + 60, "healthy": healthy,
            "watchdog": os.getpid() + 10 ** 6}


def folders(*names):
    return {f"{name}/": None for name in names}


def card(server_id, minutes_ago=20, kind=KIND):
    return machine(minutes_ago, unit_minutes=1, kind=kind, server_id=server_id)


def run_of(name):
    folder = pathlib.Path(os.environ["PROPS_HOME"]) / "runs" / name
    folder.mkdir(parents=True, exist_ok=True)
    return pictures.Run(folder, time.time() + 3600)


def cold_card_runs(*cold_starts):
    """Ledger entries of KIND, one fresh card each, that took these minutes from order to first job."""
    for minutes in cold_starts:
        ledger.record({"started": "2026-10-11T10:00:00Z", "kind": KIND, "euros": 0.1, "machines": [
            {"type": "card-type", "zone": "zone-a", "cards": 1, "started": True, "start_wait_minutes": 0.5,
             "setup_minutes": minutes - 0.5, "work_minutes": 5.0, "minutes": minutes + 4.5, "euros": 0.1}]})


NOW = 1_800_000_000.0  # the frozen clock a row's machines are made, released and taken at
OTHER_KIND_ID = "m-other"  # with `two_kinds`, an hour machine of OTHER released after m1 with a minute more left


def claim(kind=KIND, expect=None, offers=OFFERS, disk_gb=60, upset=None, as_run=None, route="take", before=False,
          at=None, run=None, deadline=None, names=None, ends=None):
    """One claim: `kind` asks for a parked machine of `offers` and `disk_gb` (`upset`: no-answer, retag-refused,
    uncleared, busy, busy-ended, or on this PC queued (its card queue waits) or another-claim (another claim holds
    it); `as_run`: the claim's own run id) by its `route` ("take": once, batch.park_taken; "waiting": waiting on its
    kind's queue from before the release, batch.parked_within; "fleet": a Pixal3D fleet renting a card,
    batch.rent_fleet), `before` the release or after it, at `at` seconds past NOW (else the clock as it stands), for
    the shared run named `run` (else a run of its own), and takes the machine `expect`, none (None) or is refused
    ("refused", its refusal naming `names`, and a tool process ending on it ends with exit code `ends`); `deadline`:
    its run's deadline after it, in seconds past NOW."""
    return dict(kind=kind, expect=expect, offers=offers, disk_gb=disk_gb, upset=upset, as_run=as_run, route=route,
                before=before, at=at, run=run, deadline=deadline, names=names, ends=ends)


def held_row(name, minutes_ago, leaves_in, unit_minutes=60, wants=None, cold_starts=(), processor_row=False,
             claims=(), deleted=None, first_pays=None, taken_pays=(), expires=(), root=None, left=None, made=None,
             **condition):
    """One release, then its claims: a machine `minutes_ago` old ends its run (`condition`: healthy, kind, in_run,
    stopping, run_id, max_machines, two_kinds, here: this PC's container, the machine its `before` claim took)
    while a claim of `wants` waits and the ledger holds `cold_starts`; parked until `leaves_in` minutes from now, or
    deleted when None. Then each of `claims` in turn; `deleted` the machines deleted at the end (default: the
    released one when not parked, else none); `first_pays` the released machine's euros,
    `taken_pays` the last taken machine's euros (from its adoption or creation, after so many minutes, within a
    tolerance, None for exactly). Last, each of `expires` in turn: m1's expirer at its time, "older" under another
    token or "own" under the token it was parked with, and the machines deleted after it. `root`: the tree on the
    machine's /root before any claim (as `planted` takes it), `made` what a claim's set-up and jobs made there before
    its release, `left` what its clean-up and any take leave of it."""
    return pytest.param(dict(minutes_ago=minutes_ago, unit_minutes=unit_minutes, wants=wants, cold_starts=cold_starts,
                             processor_row=processor_row, claims=claims, deleted=deleted, first_pays=first_pays,
                             taken_pays=taken_pays, expires=expires, root=root, left=left, made=made, **condition),
                        leaves_in,
                        id=name)


def watched_to_its_end(each, patch):
    """The renter killed before its own delete: the machine's watchdog, its parent gone after two looks, on a clock
    its sleeps move; the seconds it slept before the delete."""
    clock, parents = [NOW], iter([4242, 4242, 1])
    patch.setattr(os, "getppid", lambda: next(parents, 1))
    patch.setattr(time, "time", lambda: clock[0])
    patch.setattr(time, "sleep", lambda seconds: clock.__setitem__(0, clock[0] + seconds))
    batch.watchdog(each["id"], each["zone"], NOW + 20 * 60, poll=1.0)
    return clock[0] - NOW


def no_answer(folder, host, command, **_):
    raise OSError("connection refused")


def refused_retag(server_id, zone, tags):
    raise subprocess.CalledProcessError(1, ["scw"], "", "permission denied: instance server update")


def refused_clearance(what, store=None):
    raise batch.compute.Refused(what)


def this_pc(calls, patch):
    """This PC's container (backends/local.py): free, one claim at a time, never cleared; a judge job too big for its
    card; at a claim's end the files its claim named go and the PC is free. What its claims handed to end with."""
    holder, ended = [], []

    def take(kind, public_key, need=None):
        if kind == "judge":
            raise ValueError("a judge job needs about 30 GB of card")
        if holder:
            return None  # another claim holds this PC
        holder.append(kind)
        return {"id": "score-this-pc:1", "zone": "this-pc", "type": "score-this-pc", "class": "gpu-16gb", "cards": 1,
                "price": 0.0, "unit_minutes": 1, "host": PC_HOST, "disk_gb": 500, "here": True}

    def deleted(server_id, zone):
        calls.deleted.append(server_id)
        on_the_machine(ended[-1][1], calls.root_of(PC_HOST))
        holder.clear()
        return True

    patch.setattr(cloud, "take", take, raising=False)
    patch.setattr(cloud, "queued", lambda kind: False, raising=False)
    patch.setattr(cloud, "ends_with", lambda *handed: ended.append(handed), raising=False)
    patch.setattr(cloud, "delete", deleted)
    patch.setattr(batch, "ssh_key", lambda: "ssh-ed25519 AAAA runner")
    patch.setattr(batch.compute, "require_cleared", lambda what, store=None: pytest.fail("cleared " + what))
    return ended


def claim_run(calls, patch, asked, runs):
    """The run a claim takes for (a Pixal3D fleet on the fleet route; the shared one it names), with the claim's
    upset applied."""
    run = runs.get(asked["run"]) or run_of(f"claim-{len(calls.retagged)}-{asked['kind']}-{asked['route']}")
    if asked["run"]:
        runs[asked["run"]] = run
    if asked["route"] == "fleet":
        run = batch.Fleet([], run.folder, 3, run.deadline, "park-test", False)
    if asked["as_run"]:
        patch.setenv("SCORE_RUN_ID", asked["as_run"])
    if asked["upset"] == "no-answer":
        patch.setattr(batch, "remote", no_answer)
    if asked["upset"] == "retag-refused":  # a failed tag update is bookkeeping, no dead machine: taken all the same
        patch.setattr(cloud, "retag", refused_retag)
    if asked["upset"] == "uncleared":
        patch.setattr(batch.compute, "require_cleared", refused_clearance)
    if asked["upset"] in ("queued", "another-claim"):  # this PC's card queue waits, or another claim holds it
        patch.setattr(cloud, "take", lambda *_, **__: None, raising=False)
        patch.setattr(cloud, "queued", lambda kind: asked["upset"] == "queued", raising=False)
    if asked["upset"] in ("busy", "busy-ended"):  # this run holds one machine, live or deleted, of its cap of one
        run.machines.append({"id": "busy", "zone": "zone-a", "class": "gpu-24gb",
                             "deleted": NOW if asked["upset"] == "busy-ended" else None})
    return run


def fleet_taken(fleet, asked, patch):
    """A fleet's rent of one card: the card it took, which it tends and rents nothing beside; None when it took none."""
    ordered, tended, tending = [], [], threading.Event()
    patch.setattr(batch, "rent", lambda *arguments, **_: ordered.append(arguments) or None)
    patch.setattr(batch, "tend", lambda fleet, taken: tended.append(taken["id"]) or tending.set())
    fleet.offers = list(asked["offers"])
    added = batch.rent_fleet(fleet, 1)
    if not fleet.machines:
        return None
    assert added == 1 and not ordered and len(fleet.machines) == 1, (added, ordered)  # listed once, none rented
    assert tending.wait(5) and tended == [fleet.machines[0]["id"]], tended
    return fleet.machines[0]


def taken_by(run, asked, patch):
    """Make the claim by its route; its machine, None, or its refusal."""
    try:
        if asked["route"] == "fleet":
            return fleet_taken(run, asked, patch)
        if asked["route"] == "waiting":
            return batch.parked_within(run, asked["offers"], 1, asked["kind"], asked["disk_gb"], 5.0)
        return batch.park_taken(run, asked["offers"], 1, asked["kind"], asked["disk_gb"])
    except batch.compute.Refused as refused:
        return refused


def waiter(calls, patch, asked, runs):
    """Start a claim waiting on its kind's queue before anything is parked: it asks once, finding nothing, and asks
    again only once let go (so the release is checked first). Returns its letting go: the run and what it took."""
    run, asked_once, let_go, outcome = claim_run(calls, patch, asked, runs), threading.Event(), threading.Event(), []
    real = batch.park_taken

    def asks(*given):
        if asked_once.is_set():
            let_go.wait(5)
        found = real(*given)
        asked_once.set()
        return found

    patch.setattr(park, "PARKED_POLL_SECONDS", 0.05)
    patch.setattr(batch, "park_taken", asks)
    thread = threading.Thread(target=lambda: outcome.append(taken_by(run, asked, patch)), daemon=True)
    thread.start()
    assert asked_once.wait(5)

    def go():
        let_go.set()
        thread.join(10)
        assert outcome, "the waiting claim never returned"
        return run, outcome[0]
    return go


def swept_at(clock, listed, patch):
    """A sweep of the account at `clock`, the cloud listing `listed` (id, tags): how many it deleted, and which."""
    swept = []
    patch.setattr(time, "time", lambda: clock)
    patch.setattr(batch.cloud, "ours", lambda account: [(server_id, "zone-a", server_id, tags)
                                                         for server_id, tags in listed])
    patch.setattr(batch.cloud, "delete", lambda server_id, zone: swept.append(server_id) or True)
    patch.setattr(batch, "sweep_what_machines_left", lambda account: None)
    return batch.sweep("account"), swept


def what_a_take_leaves(calls, run, asked, taken, sent):
    """What every take leaves: the machine in the claim's run, of its kind, answering and set up, retagged; this PC's
    by one command, its kind's own set-up back and a last claim's files gone."""
    assert taken in run.machines and taken["kind"] == asked["kind"]  # another kind's machine is this kind's now
    assert taken["ready"] == taken["adopted"]  # no wait to answer, no set-up again
    if taken.get("here"):
        assert calls.remote[sent:] == [f"{park.own_set_up(asked['kind'])}; {park.cleanup_of(taken)}"], asked
        return
    assert calls.remote[-1] == park.STALE_MARKS  # only the newest set-up mark stays on the taken machine
    if asked["upset"] != "retag-refused":
        assert calls.retagged[-1][1][2] == f"deadline={run.deadline + batch.WATCHDOG_GRACE_MINUTES * 60:.0f}"


def ended_as(refused, tmp_path):
    """The exit code of a cloud tool's own process ending on `refused`, raised there uncaught; its exit handlers ran
    and its trace names the refusal."""
    program = (f"import atexit, sys\nsys.path.insert(0, {str(pathlib.Path(__file__).resolve().parent)!r})\n"
               "import park\natexit.register(lambda: print('exit handlers ran', flush=True))\n"
               f"raise park.batch.compute.{type(refused).__name__}({str(refused)!r})\n")
    finished = POPEN([sys.executable, "-c", program], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                     cwd=tmp_path)
    out, err = finished.communicate(timeout=50)
    assert "exit handlers ran" in out and type(refused).__name__ in err, (out, err[-2000:])
    return finished.returncode


def claimed(calls, patch, asked, runs, waiting, clock, tmp_path):
    """Make one claim (`waiting`: its waiter's letting go) and check what it took against what it expects; the
    machine it took, else None."""
    listed, sent = {path.name for path in park.PARKED.glob("*.json")}, len(calls.remote)
    if asked["at"] is not None:
        clock[0] = NOW + asked["at"]
    if waiting:
        run, outcome = waiting()
    else:
        run = claim_run(calls, patch, asked, runs)
        outcome = taken_by(run, asked, patch)
    refused = isinstance(outcome, batch.compute.Refused)
    took = outcome is not None and not refused
    if took:
        what_a_take_leaves(calls, run, asked, outcome, sent)
    got = "refused" if refused else outcome["id"] if took else None
    assert got == asked["expect"], (asked, got)
    if refused:  # 2026-11-02, round 45: a tool ending on a job too big for this PC's card says so by its exit code
        assert asked["names"] in str(outcome) and ended_as(outcome, tmp_path) == asked["ends"], (asked, outcome)
    if not took and asked["upset"] != "no-answer":  # what is parked stays for the next
        assert {path.name for path in park.PARKED.glob("*.json")} == listed, asked
    if asked["deadline"] is not None:
        assert run.deadline == NOW + asked["deadline"], (asked, run.deadline - NOW)
    return outcome if took else None


# This PC's container claim after claim (2026-10-29: a characters claim set up from scratch while every Blender bake
# waited): each kind's claim, what its set-up made there, and its /root once the claim ended. Its first claim finds a
# venv nobody can name and marks that may lie, which go once, and a last claim's `closed` (2026-10-28: it ended the
# next worker at once); each kind's own venv is held aside under kinds/ and comes back at its next claim; moss' model
# stays for its next claim; similar's clean-up takes every set-up mark of a rented card, none of this PC's.
PC_SET_UP = {"pixal": {**folders("venv/pixal3d"), ".pixal-setup-aaaa": "", ".library-setup-done": ""},
             "moss-sound": folders("venv/moss", "sfx/model", "sfx/out"), "similar": folders("venv/sim", "similar/work")}
PC_KEPT = {".score-this-pc": "", "kinds/": None, ".pixal-setup-aaaa": "", ".library-setup-done": "", "batch/": None}
PC_CLAIMS = [
    ("pixal", {**PC_KEPT, "kinds/.venv": "pixal\n", **folders("venv", "venv/pixal3d")}),
    ("moss-sound", {**PC_KEPT, "kinds/.venv": "moss-sound\n", **folders(
        "kinds/pixal", "kinds/pixal/venv", "kinds/pixal/venv/pixal3d", "venv", "venv/moss", "sfx", "sfx/model")}),
    ("similar", {**PC_KEPT, "kinds/.venv": "similar\n", **folders(
        "kinds/pixal", "kinds/pixal/venv", "kinds/pixal/venv/pixal3d", "kinds/moss-sound", "kinds/moss-sound/venv",
        "kinds/moss-sound/venv/moss", "venv", "venv/sim", "sfx", "sfx/model")}),
    ("pixal", {**PC_KEPT, "kinds/.venv": "pixal\n", **folders(
        "kinds/pixal", "kinds/moss-sound", "kinds/moss-sound/venv", "kinds/moss-sound/venv/moss", "kinds/similar",
        "kinds/similar/venv", "kinds/similar/venv/sim", "venv", "venv/pixal3d", "sfx", "sfx/model")}),
    ("moss-sound", {**PC_KEPT, "kinds/.venv": "moss-sound\n", **folders(
        "kinds/pixal", "kinds/pixal/venv", "kinds/pixal/venv/pixal3d", "kinds/moss-sound", "kinds/similar",
        "kinds/similar/venv", "kinds/similar/venv/sim", "venv", "venv/moss", "sfx", "sfx/model")}),
]
PC_FIRST = {"venv/unknown": "", ".pixal-setup-old": "", "batch/closed": ""}  # what this PC held before any claim
PC_ID = "score-this-pc:1"
# Fault, 2026-10-31: likeness@base's similar claim waited in the card queue behind sim body's level 1 share until its
# own deadline ran out ("no machine could be rented"). While a claim waits in the queue its run's deadline is held as
# far ahead as when the wait began; a claim kept out by another claim of this PC keeps its deadline as it runs; after
# a take a later wait starts from what is left then, never past it
PC_WAITS = (claim(kind="pixal", offers=CARD_OFFERS, upset="queued", before=True, at=0, run="first", deadline=3600),
            claim(kind="pixal", offers=CARD_OFFERS, upset="queued", before=True, at=1000, run="first", deadline=4600),
            claim(kind="pixal", offers=CARD_OFFERS, upset="another-claim", before=True, at=1300, run="first",
                  deadline=4600))
PC_LATER = (claim(offers=CARD_OFFERS, upset="queued", at=1500, run="first", deadline=4600),
            claim(offers=CARD_OFFERS, upset="queued", at=2000, run="first", deadline=5100),
            claim(kind="judge", offers=CARD_OFFERS, expect="refused", names="30 GB",
                  ends=batch.compute.CLOUD_ONLY_EXIT))


def this_pc_rows():
    """This PC's card, claim after claim: each kind's claim taken free (its run named "first" for the first), one at
    a time, never parked though a claim waits; its /root before as the last claim left it."""
    rows, before = [], PC_FIRST
    for number, (kind, left) in enumerate(PC_CLAIMS):
        claims = (claim(kind=kind, offers=CARD_OFFERS, before=True, run="first" if number == 0 else None,
                        expect=PC_ID),
                  claim(kind=kind, offers=CARD_OFFERS, before=True))  # one claim at a time
        if number == 0:
            claims = PC_WAITS + claims + PC_LATER
        rows.append(held_row(f"this-pc-{number}-{kind}", 0, None, unit_minutes=1, wants=OTHER, here=True, kind=kind,
                             root=before, made=PC_SET_UP[kind], left=left, claims=claims, deleted=[PC_ID],
                             taken_pays=(("adopted", 10, 0.0, None),)))
        before = left
    return rows


@pytest.mark.parametrize("held, leaves_in", [
    # its clean-up leaves the rest of /root, and a take on a machine with no set-up mark at all still answers
    held_row("hour-machine-35-min-left", 20, 35, first_pays=(60 * HOUR_PRICE, 1e-9),
             root=folders("lib/out", "lib/keep"), left=folders("lib", "lib/keep"), claims=(
        claim("blender-other"),  # a kind without a clean-up never takes it
        claim(disk_gb=200),  # nor a run wanting a bigger disk
        claim(offers=[OFFERS[0]._replace(zone="zone-b")]),  # nor one elsewhere
        claim(expect="m1"), claim()),  # taken once
        # ten minutes of work inside the paid hour cost nothing; into a second hour, that hour is this run's
        taken_pays=(("adopted", 10, 0.0, None), ("created", 70, 60 * HOUR_PRICE, 1e-9)),
        expires=(("own", []),)),  # its expirer, come to its time after the take, spares it
    # nobody took it: an older expirer of the same machine spares it, its own deletes it at its time
    held_row("hour-machine-nobody-took", 20, 35, expires=(("older", []), ("own", ["m1"])), deleted=["m1"],
             kind="finish-masks", root=folders("finish/in", "finish/out", "finish/venv"),
             left=folders("finish", "finish/venv")),
    held_row("two-kinds-own-kind-first", 20, 35, two_kinds=True,
             claims=(claim(expect="m1"), claim(expect=OTHER_KIND_ID), claim())),
    held_row("parked-one-not-answering", 20, 35, claims=(claim(upset="no-answer"),), deleted=["m1"]),
    held_row("parked-one-whose-retag-fails", 20, 35, claims=(claim(upset="retag-refused", expect="m1"),)),
    # killed before its own delete, the renter left the machine billing and its watchdog asleep to the deadline
    held_row("renter-killed-before-its-delete", 20, None, renter_killed=True),
    held_row("outside-a-run", 20, None, in_run=False),  # the plan of 2026-11-09 B5
    held_row("unhealthy", 20, None, healthy=False),
    held_row("kind-without-a-clean-up", 20, None, kind="unregistered"),
    held_row("2-min-before-it-must-go", 53, None),
    held_row("1-min-before-it-must-go", 54, None),
    # #20: one warm queue per step: each kind's clean-up removes its run's inputs and outputs and keeps its set-up
    held_row("second-paid-hour-54-min-left", 61, 54, kind="segment", root=folders("seg/in", "seg/out", "seg/sam2"),
             left=folders("seg", "seg/sam2")),
    held_row("second-paid-hour-45-min-left", 70, 45, kind="meshparts", root=folders("mp/in", "mp/out", "mp/SegviGen"),
             left=folders("mp", "mp/SegviGen")),
    held_row("its-run-stopping", 10, None, stopping=True),
    held_row("card-no-claim-waiting", 20, None, unit_minutes=1),
    # 2026-10-22: an H100 sat parked for the next Pixal3D run after a one-model batch, and none came
    held_row("card-no-claim-waiting-measured", 20, None, unit_minutes=1, cold_starts=(4.0,)),
    # parked for its measured cold start; nobody took it: deleted at its time, its idle minutes charged
    held_row("card-nobody-took", 20, 4.0, unit_minutes=1, wants=OTHER, cold_starts=(4.0,),
             expires=(("own", ["m1"]),), deleted=["m1"]),
    # #45: three L4s of an ended run stayed parked past their time; its releaser deletes its own, each at its own
    # time, and leaves another run's card alone
    held_row("card-its-ended-run-releases", 20, 4.0, unit_minutes=1, wants=OTHER, cold_starts=(4.0,),
             beside="another-run", second_own=True, expires=(("releaser", ["m1", "m2"]),), deleted=["m1", "m2"]),
    # its claim waited on the kind's queue before the release, and takes it once parked
    held_row("card-its-kind-waits-never-measured", 20, park.LEAST_MINUTES, unit_minutes=1, wants=KIND,
             claims=(claim(offers=CARD_OFFERS, route="waiting", expect="m1"),)),
    # a Pixal3D fleet takes a parked card before it orders one. Its clean-up keeps its watcher and key; most kinds
    # install into /root/venv, so after depth set up on it pixal's own older mark would skip a set-up whose environment
    # is gone: the take leaves only the newest mark
    held_row("pixal-card-taken-by-its-fleet", 20, park.IDLE_DEFAULT_MINUTES, unit_minutes=1, wants=OTHER, kind="pixal",
             claims=(claim(kind="pixal", offers=CARD_OFFERS, route="fleet", expect="m1"),),
             root={**folders("batch/in", "batch/out", "batch/queue", "batch/logs", "batch/closed",
                             "batch/status.json", "batch/run.log", "batch/self_delete.py", "batch/heartbeat",
                             "batch/machine_run.py", "venv"),
                   ".pixal-setup-aaaa": 300, ".library-setup-done": 200, ".depth-setup-bbbb": 100},
             left={**folders("batch", "batch/self_delete.py", "batch/heartbeat", "batch/machine_run.py", "venv"),
                   ".depth-setup-bbbb": ""}),
    # a rented card's kinds share /root/venv: moss' clean-up takes its folder and every set-up mark
    held_row("moss-card-of-a-rented-card", 20, park.IDLE_DEFAULT_MINUTES, unit_minutes=1, wants=OTHER,
             kind="moss-sound", root={".pixal-setup-aaaa": "", **folders("sfx/model")}, left={}),
    # 20 min and a started one; taken only by a cleared run, skipping its cold start and paying its work
    held_row("card-never-measured", 20.5, park.IDLE_DEFAULT_MINUTES, unit_minutes=1, wants=OTHER,
             first_pays=(21 * CARD_PRICE, 1e-9), claims=(
                 claim(offers=CARD_OFFERS, upset="uncleared", expect="refused", names="", ends=1),
                 claim(offers=CARD_OFFERS, expect="m1")),
             taken_pays=(("adopted", 3, 3 * CARD_PRICE, 0.02 * CARD_PRICE + 1e-9),)),
    # parked by another run; this run holds its cap of one: none taken, until its machine is deleted
    held_row("card-of-another-run-at-the-cap", 20, park.IDLE_DEFAULT_MINUTES, unit_minutes=1, wants=OTHER,
             run_id="another-park-test-run", max_machines="all=1", claims=(
                 claim(offers=CARD_OFFERS, upset="busy", as_run="park-test-run"),
                 claim(offers=CARD_OFFERS, upset="busy-ended", as_run="park-test-run", expect="m1"))),
    held_row("card-median-cold-start-cards-only", 20, 5.0, unit_minutes=1, wants=OTHER, cold_starts=(4.0, 6.0, 5.0),
             processor_row=True),
    # median 30: never an hour, however long a set-up took
    held_row("card-cold-start-capped", 20, park.IDLE_CAP_MINUTES, unit_minutes=1, wants=OTHER,
             cold_starts=(4.0, 6.0, 5.0, 30.0, 40.0, 50.0, 60.0), processor_row=True),
    # a short cold start still parks the card LEAST_MINUTES for a claim of its kind
    held_row("card-short-cold-start-its-kind-waits", 20, park.LEAST_MINUTES, unit_minutes=1, wants=KIND,
             cold_starts=(0.6, 0.7, 0.8)),
    *this_pc_rows(),
])
def test_a_machine_is_parked_only_while_it_pays_off(calls, monkeypatch, tmp_path, held, leaves_in):
    host, ended = (PC_HOST, this_pc(calls, monkeypatch)) if held.get("here") else (HOST, None)
    if held["root"] is not None:
        planted(calls.root_of(host), held["root"])
    cold_card_runs(*held["cold_starts"])
    if held["processor_row"]:  # a processor machine: no card, no cold start of a card
        ledger.record({"started": "2026-10-11T10:00:00Z", "kind": KIND, "euros": 1.0, "machines": [
            {"cards": 0, "started": True, "start_wait_minutes": 0.5, "minutes": 50}]})
    if not held.get("in_run", True):
        monkeypatch.delenv("SCORE_RUN_ID")
    run_id = held.get("run_id", "run-park")
    if held.get("run_id"):
        monkeypatch.setenv("SCORE_RUN_ID", run_id)
    if held.get("max_machines"):
        monkeypatch.setenv("SCORE_MAX_MACHINES", held["max_machines"])
    frozen, runs, taken = [NOW], {}, None
    monkeypatch.setattr(time, "time", lambda: frozen[0])
    for asked in (asked for asked in held["claims"] if asked["before"]):  # this PC's: taken, never rented
        with monkeypatch.context() as patch:
            taken = claimed(calls, patch, asked, runs, None, frozen, tmp_path) or taken
    if held.get("here"):  # what its claim's set-up and jobs made, and they ran well
        planted(calls.root_of(host), held["made"])
        taken["healthy"] = True
        released = [taken]
    else:
        released = [machine(held["minutes_ago"], unit_minutes=held["unit_minutes"], healthy=held.get("healthy", True),
                            kind=held.get("kind", KIND))]
    if held.get("two_kinds"):  # its own kind's parked first, with less time left
        released.append(machine(held["minutes_ago"] - 1, kind=OTHER, server_id=OTHER_KIND_ID))
    if held.get("second_own"):  # a second card of its own run, released a minute later: its own later time
        released.append(card("m2", held["minutes_ago"]))
    if held.get("beside"):  # a card of another run, released beside it
        released.append(card("o1", held["minutes_ago"]))
    if held.get("stopping"):
        batch.STOPPING.set()
    waiters, slept = {}, None
    try:
        with park.wanting(held["wants"]):
            assert park.waiting(held["wants"]) == (held["wants"] is not None)
            for number, asked in enumerate(held["claims"]):
                if asked["route"] == "waiting":
                    waiters[number] = waiter(calls, monkeypatch, asked, runs)
            for each in released:
                with monkeypatch.context() as patch:
                    if each["id"] == "o1":
                        patch.setenv("SCORE_RUN_ID", held["beside"])
                    if each["id"] == "m2":
                        patch.setattr(time, "time", lambda: NOW + 60)
                    if held.get("renter_killed"):
                        slept = watched_to_its_end(each, patch)
                    else:
                        batch.delete_machine(each)
                if leaves_in is not None:  # its expirer's tags: who holds it, till when
                    assert calls.retagged[-1][1][0] == f"pid={os.getpid()}"
                    assert calls.retagged[-1][1][2].startswith("deadline=")
    finally:
        batch.STOPPING.clear()
    assert park.waiting(held["wants"]) == 0  # off the queue when its block ends
    record, gone_at_once = park.PARKED / "m1.json", [released[0]["id"]]
    if leaves_in is None:
        assert calls.deleted == gone_at_once and not released[0].get("parked") and not list(park.PARKED.glob("*.json"))
        assert slept is None or slept < 5, slept  # a renter gone: deleted at once, not at its deadline
        if ended is not None:  # this PC's claim ends: its run's files go at its end, never in its container's layers
            assert ended == [(gone_at_once[0], park.cleanup_of(released[0]))], ended
    else:
        token = parked_as_it_pays(calls, monkeypatch, held, released, NOW + leaves_in * 60, run_id)
    for number, asked in enumerate(held["claims"]):
        if not asked["before"]:
            with monkeypatch.context() as patch:
                taken = claimed(calls, patch, asked, runs, waiters.get(number), frozen, tmp_path) or taken
    if leaves_in is not None:
        expired_at_its_time(calls, monkeypatch, held, taken, NOW + leaves_in * 60, run_id, token)
    assert calls.deleted == (held["deleted"] or ([] if leaves_in is not None else gone_at_once)), calls.deleted
    for start, minutes, euros, within in held["taken_pays"]:
        taken["deleted"] = taken[start] + minutes * 60
        paid = ledger.machine_row(taken)["euros"]
        assert paid == euros if within is None else abs(paid - euros) < within, (start, minutes, paid)
    if held["left"] is not None:  # a run's own files gone from the machine, the set-up the next claim reuses kept
        assert tree_of(calls.root_of(host)) == as_left(held["left"])


def parked_as_it_pays(calls, monkeypatch, held, released, until, run_id):
    """Each released machine parked until `until`, its run's files gone first; a sweep spares it till then; its first
    run pays what it used. The token it was parked with, and the cold start measured then."""
    record = park.PARKED / "m1.json"
    assert all(each["parked"] for each in released) and not calls.deleted
    assert calls.remote == [park.cleanup_of(each) for each in released]  # its run's files gone first
    assert json.loads(record.read_text())["run"] == run_id
    assert abs(json.loads(record.read_text())["until"] - until) < 1e-6 and abs(calls.armed[0] - until) < 1e-6
    # 2026-11-05: a Blender call's sweep deleted Batch 1's three warm pool machines minutes after they were parked,
    # judged by their expirer's pid. The parked one stays until its time whatever its expirer's pid; beside it a live
    # run's machine (the release's own tags) stays, one whose process on this host is gone goes, and one of another
    # host (the owner's PC, which holds no parked record of the conductor's) stays by its deadline
    tags = calls.retagged[0][1]
    gone = [tag if not tag.startswith("pid=") else "pid=999999999" for tag in tags]
    elsewhere = [tag.replace(f"host={batch.socket.gethostname()}", "host=another-machine") for tag in gone]
    listed = [("m1", gone), ("live", tags), ("old", gone), ("elsewhere", elsewhere)]
    for clock, expect in ((NOW, ["old"]), (until + 1, ["m1", "live", "old", "elsewhere"])):  # past its time all go
        with monkeypatch.context() as patch:
            assert swept_at(clock, listed, patch) == (len(expect), expect), (clock - NOW, expect)
    if held["first_pays"]:  # its first run pays what it used, a started hour whole
        euros, within = held["first_pays"]
        assert abs(ledger.machine_row(released[0])["euros"] - euros) < within
    return json.loads(record.read_text())["token"], park.idle_minutes(KIND)


def expired_at_its_time(calls, monkeypatch, held, taken, until, run_id, parked_with):
    """Each of the row's expirers in turn (m1's own, an older one's, its ended run's releaser), and what each
    deleted; each deleted card's idle minutes charged once, never as a cold start."""
    record = park.PARKED / "m1.json"
    token, cold = parked_with
    for number, (whose, deleted) in enumerate(held["expires"]):
        if whose == "releaser":  # the ended run's releaser, on a clock its sleeps move on
            own = {each["id"]: each["until"] for each in park.parked_by(run_id)}
            assert len(own) == len(set(own.values())) == 2, own  # two of its cards, each with its own time
            others = {path.name for path in park.PARKED.glob("*.json")} - {f"{server_id}.json" for server_id in own}
            with monkeypatch.context() as patch:
                clock, at = [NOW], {}
                patch.setattr(time, "time", lambda: clock[0])
                patch.setattr(cloud, "delete", lambda server_id, zone: calls.deleted.append(server_id)
                              or at.__setitem__(server_id, clock[0]) or True)

                def woken_before_its_time(seconds):
                    clock[0] += seconds
                    if clock[0] >= until - 1:
                        raise TimeoutError("still asleep a second before its time")

                # m1's own expirer, while m1 is still parked under its token, sleeps toward its time deleting nothing
                patch.setattr(time, "sleep", woken_before_its_time)
                with pytest.raises(TimeoutError):
                    park.expire("m1", "zone-a", token, until, poll=1.0)
                assert not at and clock[0] >= until - 1 and park.listed("m1", token), (at, clock[0] - NOW)
                clock[0] = NOW
                patch.setattr(time, "sleep", lambda seconds: clock.__setitem__(0, clock[0] + seconds))
                park.outlive(run_id, poll=0.05)
                # each of its cards deleted at its own time, not before
                assert at.keys() == own.keys() and all(at[each] >= own[each] for each in own), (at, own)
                assert park.parked_by(run_id) == [] and {path.name for path in park.PARKED.glob("*.json")} == others
                ended = clock[0]
                park.outlive(run_id, poll=0.05)  # nothing of its own left: returns at once
                park.expire("m1", "zone-a", token, NOW + 3600)  # its released card's expirer ends, deleting nothing
                assert clock[0] == ended, (clock[0] - ended)
        else:
            park.expire("m1", "zone-a", token if whose == "own" else "another-parking", NOW)
        assert calls.deleted == deleted and record.exists() == (not deleted and not taken), (number, calls.deleted)
    idle = [entry for entry in ledger.entries() if str(entry.get("batch")).startswith("parked-")]
    charged = sorted(f"parked-{each}" for each in calls.deleted) if held["unit_minutes"] == 1 else []
    assert sorted(entry["batch"] for entry in idle) == charged, idle  # each deleted card's idle minutes, once
    assert all(entry["kind"] == KIND and entry["machines"][0]["parked_idle"] and entry["euros"] >= 0.0
               for entry in idle)
    assert park.idle_minutes(KIND) == cold  # an idle row is not a cold start


def on_the_machine(command, root):
    """Run a machine's shell command with /root as `root`, as the machine runs it; its failure raised as ssh's."""
    code = os.system(f"bash -c {shlex.quote(command.replace('/root', str(root)))}")
    if code:
        raise subprocess.CalledProcessError(code, command)


def planted(root, tree):
    """Make `tree` under `root`: "name/" a folder, else a file of that text, or an empty file so many seconds old."""
    root.mkdir(parents=True, exist_ok=True)
    for name, what in tree.items():
        path = root / name
        if name.endswith("/"):
            path.mkdir(parents=True, exist_ok=True)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(what if isinstance(what, str) else "")
        if isinstance(what, (int, float)):
            os.utime(path, (time.time() - what, time.time() - what))


def tree_of(root):
    """Everything under `root` as `planted` takes it: folders as "name/", files as their text."""
    return {f"{path.relative_to(root)}/" if path.is_dir() else str(path.relative_to(root)):
            None if path.is_dir() else path.read_text() for path in root.rglob("*")}


def as_left(tree):
    """`tree` as `tree_of` reads it back: a file's age is no text."""
    return {name: None if name.endswith("/") else what if isinstance(what, str) else "" for name, what in tree.items()}
