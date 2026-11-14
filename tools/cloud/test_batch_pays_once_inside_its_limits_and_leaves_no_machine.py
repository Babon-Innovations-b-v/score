"""Invariant of batch.py (with the ledger it writes): a batch rents only inside a cleared run and the owner's limits
(4 h and EUR 60), builds only approved rows and specs, orders nothing the stock read says is out, writes a machine's
started line before its order so the month counts it until it is closed, runs every job once (a failed, overdue,
unsent or broken-machine job is a gap with its reason; a job lost while this PC slept is not a gap), rents no machine
in the place of a billed one that failed, and leaves no machine running however its runner or node ends. The runners'
shared steps (batch.priced and spread.tended/tend, as every runner calls them): each runner says its estimate before
it rents, the euros it says are its machines at the dearest offer it may take for the minutes it says, it refuses a
batch past the owner's limits (4 h, EUR 60) and never on the month's total (owner, 2026-10-20: no month's ceiling);
and a machine a runner tends itself is armed to delete itself, hears the heartbeat and is deleted whatever happens, a
failed set-up included (#21: never held to mend).

One test, test_a_batch_pays_once_inside_its_limits_and_leaves_no_machine, judges a table of rows: a call (a judging
function on its inputs, or one world driven through its real entry point: a fleet, a claim, a rent, a tended machine,
a dying runner) and the outcome it must give. No machine is rented: the backend, ssh and the clock are stand-ins, and
the dying-runner rows run real processes. The estimates are each runner's on a fixed list, as recorded from the code
before the shared estimate (a separate implementation), and their euros are checked against count x minutes x price
worked out here; the other expected numbers are worked out by hand beside their rows. The break that turns each row
red (applied once, seen red, reverted):

- short-fleet-asks-again: in `keep_the_fleet`, `if short > 0 and not fleet.no_more_work() and` -> `if False and` (a
  short fleet never asks again).
- closed-pool-never-stretches-it: in `keep_the_fleet`, `if alive or not pool_open() or pool_closed():` -> `if alive or
  not pool_open():`.
- stock-wait-never-past-the-deadline: in `claim_rounds`, `min(stock_wait_minutes(rounds) * 60, max(0.0, run.deadline -
  time.time()))` -> `stock_wait_minutes(rounds) * 60`.
- stock-wait-marked-waiting: in `parked_within`, drop both `preflight.mark_waiting()` calls.
- failed-job-is-a-gap-never-sent-again: in `collect`, `fleet.gaps(failed, ...)` -> `fleet.again([{"name": name} for
  name in failed])`.
- overdue-job-stopped-once: in `stop_overdue`, `stopped.add(name)` -> `pass`.
- failed-billed-card-not-replaced: in `keep_the_fleet`, `short = cards - fleet.lost_cards - sum(` -> `short = cards -
  sum(`.
- leftovers-at-the-deadline-are-gaps: in `Fleet.gaps`, `self.why.setdefault(name, why)` -> `pass`.
- jobs-lost-to-sleep-are-no-gaps: in `Fleet.woke`, `QUIET_MINUTES * 60` -> `QUIET_MINUTES * 6000`.
- billed-boot-failed-is-a-gap: in `claim_from`, `if not isinstance(error, OutOfStock):` -> `if
  False:`.
- started-line-before-the-order: in backends/scaleway.py `create`, drop the `ledger.rent_started(...)` call before the
  order.
- dead-runner-batch-deletes: in score/graph's `watch_runner`, `os.killpg(runner_pid, signal.SIGTERM)` -> `pass` (the
  batch rents on).
- node-of-a-groupless-runner-outlives-it: the fault's two halves together (each alone is covered by the other): in
  score/graph's `watch_runner`, the node sends itself SIGTERM when its runner is gone, and in `say`, `except
  BrokenPipeError:` -> `except ZeroDivisionError:`.
- node-killed-alone: in `stop_on_signals`, `if os.environ.get("SCORE_RUN_ID"):` -> `if False:`.
- dead-runners-group-stopped-once: in score/graph's `watch_runner`, drop `and stopped.claim_stop(mark)`.
- the limits, the bill, the cards taken, the month's open machines, the classes, the fleet's size, the rate, leftovers
  and a job's deadline, the models a list names, the inventory rows and character specs a batch builds, a run's rent
  fees, its cluster groups, the orders it sends (none without stock, none outside a cleared run), the pool cards it
  replaces, and each runner priced inside, past the limits and on a dear month: in `rent`, `if offer.stock_word in
  NO_STOCK:` -> `if False:`, or drop `compute.require_cleared(f"a {machine_type} in {zone}")`; in `Fleet.replaces`,
  `return self.setup_deaths == 1` -> `return True`; in `read_list`, `if len(set(names)) != len(names):` -> `if
  False:`; in `from_the_inventory`, `if strays:` -> `if False:`; in `from_the_characters`, `if not
  spec.get("approved"):` -> `if False:`; in ledger.py `machines_record`, drop `names |= {row["name"] for row in
  attempts if row.get("name")}`; in `cluster_line`, `" || ".join(` -> `" && ".join(`; in ledger.py `refusal`,
  `estimated_minutes > BATCH_HOURS * 60` -> `estimated_minutes > BATCH_HOURS * 600`, or `if euros > cap:` -> `if
  False:`; in `month_total`, the `+ sum(open_euros(line, now) ...)` term -> `+ 0`; in `open_rents`,
  `("disk-and-address", RENT_REFUSED)` -> `("disk-and-address",)`; in batch.py `affordable`, `found = [offer for
  offer in found if offer.per_card < dearest]` -> `break`; in `check_classes`, the `provider.cards(name)` loop -> the
  old `set(classes) - set(cloud.CLASSES)` refusal (this PC's backend lists none); in `cards_needed`, `working = minutes
  - SETUP_MINUTES - per_model * per_card` -> `working = minutes - SETUP_MINUTES`; in `aimed_minutes`, `max(` ->
  `min(`; in `card_minutes_per_model`, `reverse=True` -> `reverse=False`; in `is_leftover`, `and not (pid and
  process_alive(int(pid)))` -> `and False`; in `job_deadline_seconds`, `["high"]` -> `["median"]`; in `priced`,
  `ledger.cost(minutes, dearest) * count` -> `ledger.cost(minutes, dearest)`, or `dearest = max(` -> `dearest =
  min(`, or `refused = ledger.refusal(minutes, dearest * count)` -> `refused = ledger.refusal(minutes, dearest *
  count) or (spent > 1000 and "the month")`.
- scene-machine-step-fails: in spread.py `tended`, move `batch.delete_machine(machine)` from the `finally` to after
  the `yield` (deleted only when the block ends well).
- held-character-machine: in spread.py `tended`, `run.deadline + batch.WATCHDOG_GRACE_MINUTES * 60` -> `run.deadline`.
- character-set-up-failed-not-held: in characters.py `held`, the set-up failure's `raise SystemExit(...)` -> `pass`.
- the card_need rows and encoder-on-this-pcs-processor-only: in characters.py `card_need`, `steps <=
  STEP_NEED.keys()` -> `True` (an unmeasured step asks a measured need), `max` -> `min` (a run asks less than its
  largest step), or `or HELD_STEPS` -> `or []` (a held machine asks the kind's 17 GB); or `encoder = ""` in
  `make_one` (Kimodo's encoder goes onto this PC's 16 GB card); or `if machine.get("here")` -> `if True` (a rented
  card's run is changed).
- served-blender-machine: in blender_cloud.py `serve`, `card = machine.get("class", "").startswith("gpu")` -> `card =
  False`.
- spread-machine: in spread.py `tend`, drop `batch.delete_machine(machine)` from its `finally`.
"""
import json
import os
import pathlib
import re
import signal
import socket
import subprocess
import sys
import threading
import time
import types

import pytest

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO))

import batch  # noqa: E402
import ledger  # noqa: E402
import provider  # noqa: E402
from score.adapters import compute  # noqa: E402
import blender_cloud  # noqa: E402
import box_masks_cloud  # noqa: E402
import characters  # noqa: E402
import closeups_cloud  # noqa: E402
import delight  # noqa: E402
import finish_masks  # noqa: E402
import judge  # noqa: E402
import local  # noqa: E402
import library_bake  # noqa: E402
import meshparts  # noqa: E402
import park  # noqa: E402
import parts  # noqa: E402
import pictures  # noqa: E402
import preflight  # noqa: E402
import scene  # noqa: E402
import segment  # noqa: E402
import similar  # noqa: E402
import spread  # noqa: E402
import unirig  # noqa: E402

L4 = 0.013125
NOW = 1_760_000_000.0  # a fixed now for the open-machine checks (2025-10-09 UTC)
MONTH = "2025-10"
REAL_SLEEP = time.sleep



@pytest.fixture(autouse=True)
def quiet(monkeypatch):
    """No line printed, no warm pool, no stop left over from another test."""
    monkeypatch.setattr(batch, "say", lambda line: None)
    monkeypatch.delenv("SCORE_RUN_ID", raising=False)
    batch.STOPPING.clear()
    yield
    batch.STOPPING.clear()


def l4(zone="zone-a", stock_word="available"):
    return provider.Offer(0.01, 0, "L4", zone, 0.01, "gpu-24gb", 0, stock_word)


def started_line(name, minutes_ago, deadline_in=None, price=0.02, run="pixal-7"):
    """A rent-started line for machine `name` of `run`, ordered `minutes_ago` before NOW."""
    line = {"started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(NOW - minutes_ago * 60)),
            "batch": f"rent-{name}", "kind": ledger.RENT_STARTED, "state": "started", "run": run, "name": name,
            "price": price, "euros": 0.0}
    if deadline_in is not None:
        line["deadline"] = NOW + deadline_in * 60
    return line




class FleetStub:
    """The parts of a Fleet keep_the_fleet reads."""

    def __init__(self, deadline, work=True):
        self.stop, self.renting, self.deadline = threading.Event(), threading.Lock(), deadline
        self.machines, self.offers, self.work, self.lost_cards = [], [], work, 0

    def no_more_work(self):
        return not self.work

    def woke(self, since):
        return False



def one_shot_fleet(names, tmp_path):
    models = [types.SimpleNamespace(name=name, picture="/pics/p.png", seed=1) for name in names]
    folder = tmp_path / f"fleet-{len(list(tmp_path.iterdir()))}"
    folder.mkdir()
    return batch.Fleet(models, folder, None, 0, "test", finish=False), models

def tended(names, looks, poll_seconds, deadline_in, tmp_path, monkeypatch, per_card=3):
    """batch.tend on one fake machine over a fake clock that each poll's sleep moves on by `poll_seconds`: its status
    at each look is the next of `looks` (the last one kept; None: the machine is gone); the fleet."""
    fleet, models = one_shot_fleet(names, tmp_path)
    clock = [1000.0]
    fleet.deadline, fleet.per_card = clock[0] + deadline_in, per_card
    batch.queue(fleet, models)
    machine = {"adopted": True, "host": "host", "folder": fleet.folder / "m-1", "cards": 1, "class": "gpu-24gb",
               "created": clock[0], "deleted": None}
    machine["folder"].mkdir()
    looks = list(looks)

    def status(folder, host):
        look = looks.pop(0) if len(looks) > 1 else looks[0]
        if look is None:
            raise ConnectionError("the machine is gone")
        return {"finished": False, "jobs": {name: {"state": state, "began": clock[0]} for name, state in look.items()}}
    nothing = lambda *arguments, **keywords: None  # noqa: E731
    for name in ("arm_self_delete", "prepare", "send", "remote", "heartbeat", "bring_back", "delete_machine"):
        monkeypatch.setattr(batch, name, nothing)
    monkeypatch.setattr(batch, "machine_status", status)
    monkeypatch.setattr(batch, "POLL_SECONDS", poll_seconds)
    with monkeypatch.context() as clocked:
        clocked.setattr(time, "time", lambda: clock[0])
        clocked.setattr(time, "sleep", lambda seconds: clock.__setitem__(0, clock[0] + seconds))
        batch.tend(fleet, machine)
    return fleet



# --- the worlds the rows drive: each returns what it saw, its row holds what it must be ---

def short_fleet(patch):
    """keep_the_fleet over a fleet whose first two rounds find no stock: the cards asked each round, and whether the
    fleet kept the offers it found."""
    fleet, rounds, found = FleetStub(time.time() + 60), [], [l4()]

    def rent_fleet(fleet, cards):
        rounds.append(cards)
        if len(rounds) < 3:
            return 0  # out of stock on the first rounds
        fleet.machines.append({"cards": cards, "deleted": time.time()})
        fleet.work = False
        return cards
    patch.setattr(batch, "rent_fleet", rent_fleet)
    patch.setattr(batch.cloud, "offers", lambda classes: list(found))
    batch.keep_the_fleet(fleet, found, 2)
    return {"rounds": rounds, "offers kept": fleet.offers == found}


def pool_wait(patch, closed, seconds):
    """keep_the_fleet with no card on its run's pool (`closed` or open) and `seconds` to its deadline, stopped at its
    sixth round: the rounds it asked, whether its deadline stayed as set and whether it ran out."""
    rounds = []

    def rent_fleet(fleet, cards):
        rounds.append(cards)
        if len(rounds) >= 6:  # a fleet left waiting is stopped here
            fleet.stop.set()
        return 0
    patch.setattr(batch, "rent_fleet", rent_fleet)
    patch.setattr(batch, "pool_closed", lambda: closed)
    patch.setattr(batch, "ask_every", lambda rounds: 3600 if closed else 0)
    fleet = FleetStub(time.time() + seconds)
    deadline = fleet.deadline
    batch.keep_the_fleet(fleet, [], 1)
    return {"rounds": len(rounds), "deadline kept": fleet.deadline == deadline, "ran out": time.time() >= deadline}


def stock_waits(patch):
    """claim_rounds with 20 min to its deadline, its fifth round claiming: what it claimed and the waits it took."""
    waits, rounds = [], []
    run = types.SimpleNamespace(deadline=time.time() + 20 * 60)
    patch.setattr(batch, "claim_round", lambda *arguments: rounds.append(1) or (
        None if len(rounds) < 5 else {"machine": 1}))
    patch.setattr(batch, "parked_within", lambda run, offers, number, kind, disk_gb, seconds: waits.append(seconds))
    claimed = batch.claim_rounds(run, "account", [], 1, "pixal", 60, None)
    return {"claimed": claimed, "first waits": [round(wait / 60) for wait in waits[:3]], "waits": len(waits),
            "fourth cut to the 20 min left": 19 * 60 < waits[3] <= 20 * 60}


def waiting_marks(patch):
    """parked_within for 0.05 s with nothing parked: what it took and the waiting marks it set, in order."""
    marks = []
    patch.setattr(preflight, "mark_waiting", lambda: marks.append("waiting"))
    patch.setattr(preflight, "unmark_waiting", lambda: marks.append("done"))
    run = types.SimpleNamespace(deadline=time.time() + 20 * 60)
    return {"taken": batch.parked_within(run, [], 1, "pixal", 60, 0.05), "first": marks[0], "last": marks[-1],
            "marked on every look": marks.count("waiting") >= 2}


def collected(here):
    """Two jobs sent, one failed and one running: what was sent, what collect gave back, the gaps, and what is next."""
    fleet, models = one_shot_fleet(["crate", "barrel"], here)
    batch.queue(fleet, models)
    sent = [fleet.next_job()["name"], fleet.next_job()["name"]]
    status = {"jobs": {"crate": {"state": "failed"}, "barrel": {"state": "running", "began": 0}}}
    back = batch.collect(fleet, fleet.folder, "host", status, set())
    return {"sent": sent, "collected": back, "failed": fleet.failed, "next": fleet.next_job()}


# at 1000 s: a job running 1000 s, one running 100 s, and one done
RUNNING_JOBS = {"jobs": {"slow": {"state": "running", "began": 0.0}, "quick": {"state": "running", "began": 900.0},
                         "made": {"state": "done", "began": 0.0}}}
PATTERN = batch.own_pattern("/root/batch/out/slow.glb")


def stopped_twice(here, patch):
    """stop_overdue called twice at 1000 s on RUNNING_JOBS with a 500 s job deadline: the commands sent, the jobs
    stopped and the gap's reason."""
    fleet, commands, stopped = one_shot_fleet(["slow"], here)[0], [], set()
    fleet.job_deadline = 500
    patch.setattr(batch, "remote", lambda folder, host, command, **keywords: commands.append(command))
    patch.setattr(batch.time, "time", lambda: 1000.0)
    batch.stop_overdue(fleet, fleet.folder, "host", RUNNING_JOBS, stopped)
    batch.stop_overdue(fleet, fleet.folder, "host", RUNNING_JOBS, stopped)
    return {"commands": commands, "stopped": stopped, "why": fleet.why["slow"]}


def lost_fleet(here, patch):
    """keep_the_fleet over two jobs whose one billed card failed: what it rented, the gaps, and what is next."""
    fleet, models = one_shot_fleet(["crate", "barrel"], here)
    fleet.deadline = time.time() + 60
    batch.queue(fleet, models)
    fleet.lose({"cards": 1})
    rented = []
    patch.setattr(batch, "rent_fleet", lambda fleet, cards: rented.append(cards) or 0)
    batch.keep_the_fleet(fleet, [], 1)
    return {"rented": rented, "failed": sorted(fleet.failed), "next": fleet.next_job()}


def tended_fleet(fleet, unsent=None):
    """What a tended fleet ended with: made, gaps, lost to sleep, its stops; then the jobs never sent (taken as gaps
    with the reason `unsent`), and its ledger entry's gaps."""
    failed = list(fleet.failed)
    never_sent = fleet.unsent_gaps(unsent) if unsent else None
    entry = batch.ledger_entry(fleet, list(fleet.models), 0.0)
    return {"done": fleet.done, "failed": failed, "asleep": fleet.asleep, "slept": fleet.slept.is_set(),
            "stopped": fleet.stop.is_set(), "why": fleet.why, "unsent": never_sent, "gaps": entry["gaps"],
            "gap_reasons": entry["gap_reasons"], "lost_to_sleep": entry["lost_to_sleep"]}


def claimed(here, patch, failures):
    """claim over two L4 offers whose boots fail with `failures` in turn: what it claimed and the zones it rented."""
    rented = []

    def rent(run, account, offer, number, disk_gb):
        rented.append(offer.zone)
        folder = here / f"m{len(list(here.iterdir()))}"
        folder.mkdir()
        return {"zone": offer.zone, "type": offer.type, "class": offer.machine_class, "cards": 1, "folder": folder,
                "deleted": None}

    def boot(machine):
        raise failures.pop(0)
    patch.setattr(batch, "rent", rent)
    patch.setattr(batch, "boot", boot)
    run = types.SimpleNamespace(machines=[], attempts=[], deadline=0)
    return batch.claim(run, None, [l4("zone-a"), l4("zone-b")], 1, "parts"), rented


def refused_order(here, patch):
    """rent of an L4 the provider refuses (out of quota), its machine number 3: the orders sent, the ledger as each
    went, and the ledger after."""
    seen = []

    def fake_scw(command, **options):
        """The backend's scw call: what the ledger held when the order went, then a refusal; the look for a machine
        the refused order made anyway finds none."""
        if command[:4] != ["scw", "instance", "server", "create"]:
            return types.SimpleNamespace(returncode=0, stdout="[]", stderr="")
        seen.append((command[:4], ledger.entries()))
        return types.SimpleNamespace(returncode=1, stdout="", stderr="out of quota")
    patch.setattr(batch.cloud, "subprocess", types.SimpleNamespace(run=fake_scw))
    keys = here / "keys"
    keys.mkdir()
    patch.setattr(batch, "KEY", keys / "ssh_key")
    patch.setattr(batch, "SELF_DELETE_KEY", keys / "self_delete.json")
    batch.KEY.write_text("private")
    batch.SELF_DELETE_KEY.write_text('{"secret_key": "works"}')
    fleet = types.SimpleNamespace(folder=here / "pixal-run-7", deadline=time.time() + 60, attempts=[])
    rented = batch.rent(fleet, None, l4(), 3)
    after = ledger.entries()
    command, held = seen[0] if seen else (None, [])
    line = held[0] if len(held) == 1 else {}
    return {"rented": rented, "orders": len(seen), "order": command, "held as it went": len(held),
            "line": {key: line.get(key) for key in ("kind", "state", "euros", "run", "name", "ticket", "type", "zone")},
            "deadline with grace": line.get("deadline") == round(fleet.deadline + batch.WATCHDOG_GRACE_MINUTES * 60),
            "after": [(entry["kind"], entry.get("name")) for entry in after],
            "reason": after[-1].get("reason", "") if after else ""}


def wait_for(path, seconds=30):
    deadline = time.time() + seconds
    while not path.exists() and time.time() < deadline:
        REAL_SLEEP(0.05)
    assert path.exists(), f"{path.name} never came"


def deleted(path, count, seconds=30):
    """The machine ids written to `path`, once `count` are there or `seconds` passed."""
    deadline = time.time() + seconds
    while len(path.read_text().split() if path.exists() else []) < count and time.time() < deadline:
        REAL_SLEEP(0.05)
    return path.read_text().split() if path.exists() else []


def a_home(tmp_path, run_id=None):
    environment = {**os.environ, "PROPS_HOME": str(tmp_path), "PROPS_WORK": str(tmp_path / "work")}
    environment.pop("SCORE_RUN_ID", None)
    if run_id:
        environment["SCORE_RUN_ID"] = run_id
    return environment


# A batch holding argv[4] fake machines that works for argv[5] seconds, says so, then deletes each through
# batch.delete_machine as batch.run's end does; it writes "ready" once its signals are handled.
WORKING_BATCH = """
import pathlib, sys, time
sys.path.insert(0, sys.argv[1])
import batch
from provider import cloud
deletes, folder = pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3])
cloud.delete = lambda server_id, zone: bool(deletes.open("a").write(server_id + "\\n"))
batch.stop_on_signals()
machines = [{"id": f"machine-{number}", "zone": "zone-a", "deleted": None, "watchdog": 999999999,
             "folder": folder / f"machine-{number}", "created": time.time(), "kind": None, "healthy": False}
            for number in range(int(sys.argv[4]))]
try:
    (folder / "ready").write_text("ready")
    time.sleep(float(sys.argv[5]))
    batch.say("working on")
finally:
    for machine in machines:
        batch.delete_machine(machine)
"""
# A runner (argv[2] "lead": it leads its process group, as `score run` does) with one node process (score.graph's
# watch_runner) running the batch, its output piped to the node as a stage's subprocess.run does.
RUNNER = """
import os, subprocess, sys, threading, time
sys.path.insert(0, sys.argv[1])
from score import graph
if sys.argv[2] == "lead":
    os.setpgid(0, 0)
runner = os.getpid()
if os.fork() == 0:
    threading.Thread(target=graph.watch_runner, args=(runner, 0.2), daemon=True).start()
    subprocess.run([sys.executable, "-c", sys.argv[3], *sys.argv[4:]], capture_output=True)
    os._exit(0)
time.sleep(120)
"""

# A run (SCORE_RUN_ID set) whose one node runs the batch, its output piped to the node; the node's pid in node.pid.
RUN_WITH_A_NODE = """
import os, pathlib, subprocess, sys, time
folder = pathlib.Path(sys.argv[4])
if os.fork() == 0:
    (folder / "node.pid").write_text(str(os.getpid()))
    subprocess.run([sys.executable, "-c", sys.argv[1], *sys.argv[2:]], capture_output=True)
    os._exit(0)
time.sleep(120)
"""

# A runner leading its process group, with four node processes (watch_runner, each its own poll) that take SIGTERM
# without ending, and a process that writes a line for every SIGTERM it gets; "ready" once all are in.
COUNTED_RUNNER = """
import os, pathlib, signal, subprocess, sys, threading, time
sys.path.insert(0, sys.argv[1])
from score import graph
folder = pathlib.Path(sys.argv[2])
os.setpgid(0, 0)
runner = os.getpid()
counter = subprocess.Popen([sys.executable, "-c", "import pathlib, signal, sys, time; "
                            "signal.signal(signal.SIGTERM, lambda *_: pathlib.Path(sys.argv[1]).open('a').write('x')); "
                            "pathlib.Path(sys.argv[2]).write_text('ready'); time.sleep(30)",
                            str(folder / "signals.txt"), str(folder / "counter-ready")])
for node in range(4):
    if os.fork() == 0:
        signal.signal(signal.SIGTERM, lambda *_: None)
        threading.Thread(target=graph.watch_runner, args=(runner, 0.05), daemon=True).start()
        time.sleep(10)
        os._exit(0)
while not (folder / "counter-ready").exists():
    time.sleep(0.05)
(folder / "ready").write_text("ready")
time.sleep(120)
"""



def runner_killed(here, lead, count, seconds):
    """A RUNNER (`lead` or "follow") whose batch holds `count` machines for `seconds`, killed outright: the machines
    its batch deleted."""
    runner = subprocess.Popen([sys.executable, "-c", RUNNER, str(REPO), lead, WORKING_BATCH, str(HERE),
                               str(here / "deletes.txt"), str(here), str(count), str(seconds)], env=a_home(here))
    wait_for(here / "ready")
    runner.send_signal(signal.SIGKILL)  # no stop handler runs: only the node's watch can end the batch
    runner.wait()
    return deleted(here / "deletes.txt", count)


def node_killed(here):
    """A run whose one node runs a batch of three machines, the node killed alone: the machines deleted, and whether
    the run lives on."""
    run = subprocess.Popen([sys.executable, "-c", RUN_WITH_A_NODE, WORKING_BATCH, str(HERE),
                            str(here / "deletes.txt"), str(here), "3", "90"],
                           env=a_home(here, "killed-node-test"), start_new_session=True)
    try:
        wait_for(here / "ready")
        os.kill(int((here / "node.pid").read_text()), signal.SIGKILL)  # the run lives on
        return {"deleted": deleted(here / "deletes.txt", 3), "run lives": run.poll() is None}
    finally:
        os.killpg(run.pid, signal.SIGKILL)
        run.wait(timeout=10)


def stops_sent(here):
    """The SIGTERMs a dead COUNTED_RUNNER's group got from its four nodes' watches, one "x" each."""
    runner = subprocess.Popen([sys.executable, "-c", COUNTED_RUNNER, str(REPO), str(here)])
    wait_for(here / "ready")
    runner.send_signal(signal.SIGKILL)
    runner.wait()
    REAL_SLEEP(2)  # every watch has seen its runner gone by now
    signals = (here / "signals.txt").read_text() if (here / "signals.txt").exists() else ""
    try:
        os.killpg(runner.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    return signals


class Tended:
    """batch's machine steps stubbed: what was armed, beaten and deleted, in order."""

    def __init__(self, monkeypatch):
        self.done = []
        monkeypatch.setattr(batch, "arm_self_delete", lambda folder, host, deadline: self.done.append(
            ("armed", host, deadline)))
        monkeypatch.setattr(spread, "off_zone_mirror", lambda folder, host: self.done.append(("off zone mirror", host)))
        monkeypatch.setattr(pictures, "keep_beating", lambda folder, host, stop: self.done.append(
            ("beating", host)) or stop.wait(5))
        monkeypatch.setattr(batch, "delete_machine", lambda machine: self.done.append(("deleted", machine["host"])))
        monkeypatch.setattr(batch, "say", lambda line: None)

    def armed_beaten_deleted(self, deadline):
        grace = deadline + batch.WATCHDOG_GRACE_MINUTES * 60
        return (self.done[0] == ("armed", "10.0.0.1", grace) and ("beating", "10.0.0.1") in self.done
                and self.done[-1] == ("deleted", "10.0.0.1") and self.done.count(("deleted", "10.0.0.1")) == 1)


def machine_and_run(tmp_path):
    folder = tmp_path / "machine"
    folder.mkdir()
    run = pictures.Run(folder, time.time() + 3600)
    run.started = time.time()
    return {"folder": folder, "host": "10.0.0.1", "created": 0.0, "class": "gpu-24gb", "type": "small",
            "zone": "zone-a"}, run



def tended_machine(here, patch, work):
    """`work`(here, patch, run, machine) on one machine with batch's machine steps recorded: what it saw, the error it
    ended with (None), and whether the machine was armed with the grace, beaten and deleted once, at the end."""
    machine, run = machine_and_run(here)
    tended = Tended(patch)
    try:
        seen, error = work(here, patch, run, machine) or {}, None
    except (Exception, SystemExit) as failed:  # what the machine's runner ended with, judged by the row
        seen, error = {}, f"{type(failed).__name__}: {failed}"
    return {**seen, "error": error, "armed, beaten, deleted": tended.armed_beaten_deleted(run.deadline),
            "steps": tended.done}


def fails(*arguments):
    raise RuntimeError("failed")


def set_up_fails(machine):
    raise subprocess.CalledProcessError(1, "characters_setup.sh")


def held_to_mend(run, host):
    raise AssertionError("a failed set-up was held to mend")


def held_host(here, patch, run, machine):
    characters.held(run, machine, [])
    return {"host": (run.folder / "host").read_text()}


def served(here, patch, run, machine):
    """blender_cloud.serve of a queue of one job, then closed: its steps and what it wrote."""
    queue = here / "queue"
    queue.mkdir()
    (queue / "1.json").write_text(json.dumps({"script": "tools/blender/inside/x.py", "minutes": 1}))
    (queue / "close").write_text("")
    ran = []
    patch.setattr(blender_cloud, "set_up", lambda log_folder, host, jobs: ran.append(("set up", jobs)))
    patch.setattr(blender_cloud, "run_job", lambda log_folder, host, number, job, card: ran.append(
        (number, card)) or (1.5, 1))
    patch.setattr(batch, "remote", lambda *arguments, **keywords: ran.append("remote"))
    patch.setattr(batch, "copy", lambda *arguments: ran.append("copy"))
    blender_cloud.serve(run, machine, queue, 1)
    return {"ran": ran, "done": (queue / "1.done").read_text(), "ready": (queue / "ready").read_text(),
            "unit_seconds": machine["unit_seconds"]}


def spread_shares(here, patch, run, machine):
    worked = []
    spread.tend(run, machine, "parts", spread.Shares([1, 2]), lambda machine: None,
                lambda machine, share, card: worked.append(share))
    return {"worked": sorted(worked)}


def steps_of(here, name, steps):
    """A character folder `name` whose spec asks `steps`."""
    (here / name / "in").mkdir(parents=True, exist_ok=True)
    (here / name / "in" / "spec.json").write_text(json.dumps({"steps": steps}))
    return here / name


def encoder_sent(here, patch):
    """make_one of a scene-clips character on this PC's card, then on a rented one: whether each run's command holds
    the encoder on the processor."""
    sent = []
    patch.setattr(batch, "remote", lambda folder, host, command, **_: sent.append(command))
    folder = steps_of(here, "scene", ["scene clips", "rig"])
    run = types.SimpleNamespace(deadline=time.time() + 60)
    for this_pc in (True, False):
        characters.make_one(run, {"folder": here, "host": "h", "here": this_pc}, folder, 0)
    return [characters.ENCODER in command for command in sent[1::2]]


class Like(str):
    """An expected text: one the pattern finds."""

    def __eq__(self, other):
        return isinstance(other, str) and re.search(self, other) is not None

    __hash__ = str.__hash__


class Observed(dict):
    """The expected outcome of a world: a dict holding these keys with these values (an Observed value in turn)."""

    def holds(self, outcome, said):
        return isinstance(outcome, dict) and all(
            key in outcome and (value.holds(outcome[key], said) if isinstance(value, Observed) else value == outcome[key])
            for key, value in self.items())


POOL_WAIT = ((batch, "pool_open", lambda: True), (batch, "fresh_offers", lambda run, found: []),
             (batch.time, "sleep", lambda seconds: REAL_SLEEP(0.02)))
CLAIMING = ((batch, "delete_machine", lambda machine: None), (batch.ledger, "machine_row", lambda machine: {}),
            (batch, "park_taken", lambda *arguments: None))


# --- the runners' shared steps: each says and keeps inside its estimate, and deletes every machine it tends ---

def offers(scale=1.0):
    """Three offers, EUR 0.02, 0.05 and 0.01 a minute (times `scale`), of three classes and stocks."""
    return [provider.Offer(0.02 * scale, 0, "small", "zone-a", 0.02 * scale, "gpu-24gb", 0, "available"),
            provider.Offer(0.05 * scale, 1, "big", "zone-b", 0.05 * scale, "gpu-80gb", 0, "scarce"),
            provider.Offer(0.01 * scale, 2, "short", "zone-c", 0.01 * scale, "cpu-32c-128gb", 0, "shortage")]


# Each runner's estimate on a fixed list, and the line it said on the code before the shared estimate.
ESTIMATES = {
    "blender_cloud": (lambda: blender_cloud.price([{"minutes": 5}, {"minutes": 20}], "acct", ["gpu-24gb"]),
                      "2 Blender jobs on 2 machines: about 28 min, €1.12"),
    "box_masks_cloud": (lambda: box_masks_cloud.price([{}] * 9, "acct"), "9 pictures on 1 card: about 13 min, €0.65"),
    "characters": (lambda: characters.price(["p1", "p2", "p3"], "acct", None),
                   "3 people on 3 machines: about 57 min, €8.55"),
    "closeups_cloud": (lambda: closeups_cloud.price(40, "acct", 20), "40 close-ups on 1 card: about 24 min, €1.20"),
    "delight": (lambda: delight.price(30, "acct"), "30 unlit copies on 2 cards: about 16 min, €1.60"),
    "finish_masks": (lambda: finish_masks.price([[]] * 7, "acct", 2),
                     "7 shares of pictures on 2 machines: about 26 min, €2.60"),
    "judge": (lambda: judge.price([{}] * 300, "acct", 1), "300 questions on 1 card: about 42 min, €2.10"),
    "library_bake": (lambda: library_bake.price([{"materials": [1] * 10}, {"chunky": [1] * 4}], "acct",
                                                ["gpu-24gb"]), "2 library jobs on 1 machine: about 17 min, €0.34"),
    "meshparts": (lambda: meshparts.price([["a"]] * 4, "acct", False),
                  "4 shares of takes on 4 machines: about 33 min, €6.60"),
    "parts": (lambda: parts.price(12, "acct"), "12 PartCrafter runs on 2 cards: about 32 min, €3.20"),
    "pictures": (lambda: pictures.price([{}] * 50, 2, "acct", "klein"), "50 pictures on 2 machines: about 12 min, €1.20"),
    "segment": (lambda: segment.price([[]] * 5, "acct"), "5 shares of pictures on 2 machines: about 22 min, €2.20"),
    "similar": (lambda: similar.price({f"p{n}": ["x", "y"] for n in range(100)}, "acct"),
                "100 pairs on one machine: about 10 min, €0.50"),
    "unirig": (lambda: unirig.price(9, "acct"), "9 models on 3 machines: about 27 min, €4.05"),
}
SAID = re.compile(r"on (\d+|one) (?:machine|card)s?: about (\d+) min, €([\d.]+); €([\d.]+) spent this month$")


class Stopped(str):
    """A call's SystemExit (or a run's compute.Refused), as its message; `by` the exception's class."""

    def __new__(cls, stop):
        stopped = super().__new__(cls, stop)
        stopped.by = type(stop)
        return stopped


class Refused:
    """The expected outcome of a refusal holding every one of `words` (with `either=True`, one of them): a stop
    (SystemExit), or with `raised=False` a refusal line returned."""

    def __init__(self, *words, raised=True, either=False, by=SystemExit):
        self.words, self.raised, self.either, self.by = words, raised, either, by

    def holds(self, outcome, said):
        if not isinstance(outcome, str) or isinstance(outcome, Stopped) != self.raised:
            return False
        return (not self.raised or issubclass(outcome.by, self.by)) and (any if self.either else all)(
            word in outcome for word in self.words)


class Including(frozenset):
    """The expected outcome of a call returning a set that holds at least these."""

    def holds(self, outcome, said):
        return not isinstance(outcome, Stopped) and isinstance(outcome, (set, frozenset)) and outcome >= self


class Estimate:
    """A runner's estimate said once as `recorded` with the month's `spent`, its euros its machines at the dearest offer
    it may take for the minutes it says, and the minutes the 4 h and EUR 60 limits allow returned last."""

    def __init__(self, recorded, spent):
        self.recorded, self.spent = recorded, spent

    def holds(self, outcome, said):
        if isinstance(outcome, Stopped) or said != [f"{self.recorded}; €{self.spent:.2f} spent this month"]:
            return False
        count, minutes, euros, _ = SAID.search(said[0]).groups()
        count = 1 if count == "one" else int(count)
        dearest = max(offer.per_card for offer in outcome[0])  # the dearest offer the runner may take
        # billed by the started minute: the said minutes are rounded, so the bill lies within a minute of them
        return ((int(minutes) - 0.5) * dearest * count - 0.005 <= float(euros) <= (int(minutes) + 1.5) * dearest * count
                and outcome[-1] == min(240.0, 60.0 / (dearest * count)))


def holds(expected, outcome, said):
    """Whether a call's `outcome` (and the lines it `said`) is the `expected` one: a matcher's, or equal."""
    if isinstance(expected, (Refused, Estimate, Including, Observed)):
        return expected.holds(outcome, said)
    return not isinstance(outcome, Stopped) and outcome == expected


def case(name, call, expected, stubs=(), env=None):
    """A row: `call` under the attributes `stubs` set ((target, attribute, value)) and the environment `env`."""
    return pytest.param(call, expected, stubs, env or {}, id=name)


# Each runner priced three ways: its month at EUR 100, offers 200 times dearer (EUR 2 to 10 a minute: every batch
# here passes EUR 60), and a month of EUR 10,000 (never a ceiling): (spent, price scale, refused past the limits).
PRICINGS = {"inside": (100.0, 1.0, False), "past-the-limits": (100.0, 200.0, True),
            "dear-month": (10_000.0, 1.0, False)}


def priced(runner, pricing):
    """The row of `runner` priced by `pricing`: its offers and month spend stubbed, its outcome expected."""
    estimate, recorded = ESTIMATES[runner]
    spent, scale, past = PRICINGS[pricing]
    stubs = ((batch, "offers", lambda classes: offers(scale)), (batch, "month_spent", lambda account: spent))
    expected = Refused("refused", "€60") if past else Estimate(recorded, spent)
    return case(f"{runner}-{pricing}", lambda here, patch: estimate(), expected, stubs)


# 20 H100s for 180 min is EUR 172, 20 L4s EUR 47: the H100 is left out
FOUND = [provider.Offer(L4, 1, "L4", "zone-a", L4, "gpu-24gb", 0, "scarce"),
         provider.Offer(0.047775, 2, "H100", "zone-b", 0.047775, "gpu-80gb", 0, "shortage")]
# under the owner's override with EUR 2.47 left (labval-motor-20261106) a batch may spend 2.47 less 10%
OVERRIDE = ((compute, "override_room", lambda store=None: {"name": "labval", "euros": 40.0, "spent": 37.53,
                                                           "left": 2.47}),)
OVERRIDE_TICKET = {compute.TICKET: "override labval"}
# Fault (review of C1, 2026-10-17): a started line held 0 euros and the month ignored it, so the guard did not count a
# machine running and not yet billed.
MONTHS = [{"started": "2026-09-29T10:00:00Z", "euros": 1.5}, {"started": "2026-08-31T23:00:00Z", "euros": 9.0}]
RUNNING = [started_line("pixal-7-1", 60, deadline_in=120)]  # an hour at EUR 0.02 a minute
DIED = [started_line("pixal-7-1", 600, deadline_in=-360)]  # its run died: counted to its deadline, 4 h
STARTED = [started_line("pixal-7-1", 60, 120), started_line("pixal-7-2", 60, 120),
           started_line("other-1", 60, 120, run="other")]
CLOSING = [{"started": STARTED[0]["started"], "batch": "pixal-7", "kind": "pixal", "euros": 1.5},
           {"started": STARTED[0]["started"], "batch": "disk-and-address-s1", "kind": "disk-and-address",
            "name": "other-1", "euros": 0.1},
           {"started": STARTED[0]["started"], "batch": "rent-pixal-7-2", "kind": ledger.RENT_REFUSED,
            "name": "pixal-7-2", "euros": 0.0}]
# 2026-10-28: every Pixal3D batch on this PC's card (SCORE_CLOUD=local, whose CLASSES is empty: its offers are parked)
# exited 1 at once, its classes checked against the backend's CLASSES; which it sells is its offers'.
THIS_PC = ((batch, "cloud", local),)
# a batch stopped part way is written after a later one; its slow rate must not set the estimate
ENTRIES = ((ledger, "entries", lambda: [{"started": "2026-09-30T17:56:47Z", "models_done": 5, "card_minutes": 25},
                                        {"started": "2026-09-30T17:35:47Z", "models_done": 3, "card_minutes": 380}]),)
LATER, HOST = 2e9, socket.gethostname()
# A list of models (its pictures in the row's folder), an inventory and a character spec, written where a row reads them.
LOCKERS = "habitat-locker {picture}\nlocker-b {picture}\nr2 {picture}\n"
ROWS = [{"id": "r1", "view": "v1", "box": [0, 0, 9, 9], "name": "locker", "kind": "generate", "anchor": "wall",
         "size": [0.6, 0.5, 1.9], "count": 1, "thing": "prop:locker"},
        {"id": "r2", "view": "v1", "box": [0, 0, 9, 9], "name": "desk", "kind": "mechanic", "anchor": "floor",
         "size": [1.6, 0.8, 0.75], "count": 1, "thing": "node:Workstation", "prop": "desk"},
        {"id": "keyboard", "view": "v1", "box": [0, 0, 9, 9], "name": "keyboard", "kind": "code", "anchor": "wall",
         "size": [0.4, 0.03, 0.15], "count": 1, "thing": "gear:keyboard"}]
INVENTORY = {"scene": "hub", "place": "habitat", "plan": {"views": [{"id": "v1"}]}, "approved": "", "migrated": "",
             "room": {"shell": "", "light": "place", "backdrop": "", "wall_fill": []}, "rows": ROWS}
APPROVED = {**INVENTORY, "approved": "2026-10-05"}
# a designed place's hand-in is approved by the creator's pick, its rows taken as they stand
DESIGNED = {**INVENTORY, "approved": {"by": batch.DESIGNED, "concept": "c" * 64}, "room": {},
            "rows": [{**ROWS[0], "anchor": "ground", "box": None}]}
TANG = {"name": "fish_tang", "kind": "animal", "picture": "tang.png", "body": "fish"}
# two disk-and-address lines of batch-1-1, one of batch-1-2 (no attempt of its) and one of batch-2-1
FEES = [("batch-1-1", 0.005), ("batch-1-1", 0.005), ("batch-1-2", 0.005), ("batch-2-1", 1.0)]
TAKES = [types.SimpleNamespace(name=f"crate-{number}", picture="/pics/crate.png", seed=number) for number in range(4)]


def a_list(here, text):
    """The models of list `text`, its pictures `{picture}` in `here`."""
    (here / "p.png").write_bytes(b"")
    (here / "list.txt").write_text(text.format(picture=here / "p.png"))
    return batch.read_list(here / "list.txt")


def written(here, name, content=None):
    """The path of `name` in `here`, holding `content` as JSON (nothing written for None)."""
    if content is not None:
        (here / name).write_text(json.dumps(content))
    return here / name


def a_character(here, **changes):
    """The path of the tang's spec in `here` with `changes`, its picture there (None: no picture)."""
    (here / "tang.png").write_bytes(b"")
    spec = {**TANG, **changes}
    if spec["picture"]:
        spec["picture"] = str(here / spec["picture"])
    return written(here, "fish_tang.json", spec)


def listed(models):
    return [model.name for model in models], models[0].faces, [model.feet for model in models]


def built(models, here):
    return [(model.name, pathlib.Path(model.picture).relative_to(here).as_posix()) for model in models]


def fees_of(attempts):
    """A run's rent fees and euros, with `FEES` in its ledger."""
    for name, euros in FEES:
        ledger.record({"started": "2026-10-22T10:00:00Z", "batch": f"disk-and-address-{euros}", "name": name,
                       "kind": "disk-and-address", "euros": euros})
    record = ledger.machines_record([], attempts, 0.0)
    return round(record["rent_fees"], 6), record["euros"]


def never_ordered(*arguments):
    raise AssertionError(f"a machine was ordered: {arguments}")


def a_fleet(here):
    return types.SimpleNamespace(folder=here, deadline=time.time() + 60, attempts=[])


def no_stock_rents(fleet):
    """What rent gives for an offer of each word the backend's stock read uses for none, and the attempts it wrote."""
    return [batch.rent(fleet, "account", l4(stock_word=word), 1) for word in batch.NO_STOCK], fleet.attempts


# Review of the warm pool (2026-10-23): every failure of a pool card put its jobs back and took the next card, so a
# set-up that always fails took card after card until the deadline. The cards that failed, in order: one that answers
# (the fault is the job's), one that died while working, the first that died in set-up, and a second (none taken).
POOL_FAILURES = [{"generating_began": 1.0, "answers": True}, {"generating_began": 1.0, "answers": False},
                 {"generating_began": None, "answers": False}, {"generating_began": None, "answers": False}]


def side_by_side(line):
    """How many takes a cluster line starts, how many in the background, and the test it ends on after `wait`."""
    return (line.count("pixal-run scripts/pixal3d_generate.py /work/in/crate-"), line.count(") &"),
            line.rsplit("wait; ", 1)[1])


HIGH = json.loads((REPO / "data" / "costs" / "per-unit.json").read_text())["stages"]["pixal"]["time"]["unit_seconds"]
CASES = [
    case("90-min-inside", lambda here, patch: ledger.refusal(90, L4), None),
    case("241-min-past-4h", lambda here, patch: ledger.refusal(241, L4), Refused("4 h", raised=False)),
    case("eur63-past-eur60", lambda here, patch: ledger.refusal(210, 0.3), Refused("€60", raised=False)),
    case("minutes-allowed-l4", lambda here, patch: ledger.minutes_allowed(L4), 240),
    case("minutes-allowed-dear", lambda here, patch: round(ledger.minutes_allowed(0.3)), 200),
    case("override-eur3-past", lambda here, patch: ledger.refusal(30, 0.1), Refused("override labval", raised=False), OVERRIDE,
         OVERRIDE_TICKET),
    case("override-eur2-inside", lambda here, patch: ledger.refusal(20, 0.1), None, OVERRIDE, OVERRIDE_TICKET),
    case("override-watchdog-minutes", lambda here, patch: round(ledger.minutes_allowed(0.1), 1), 22.5, OVERRIDE, OVERRIDE_TICKET),
    case("billed-by-started-minute", lambda here, patch: ledger.cost(1.2, L4), 2 * L4),
    case("dearest-left-out", lambda here, patch: [offer.machine_class for offer in batch.affordable(FOUND, minutes=180, cards=20)],
         ["gpu-24gb"]),
    case("all-affordable", lambda here, patch: batch.affordable(FOUND, minutes=30, cards=2), FOUND),
    case("month-of-batches", lambda here, patch: ledger.month_total("2026-09", MONTHS), 1.5),
    case("month-running", lambda here, patch: round(ledger.month_total(MONTH, RUNNING, now=NOW), 2), 1.2),
    case("open-running", lambda here, patch: ledger.open_rents(RUNNING, NOW), RUNNING),
    case("month-died-to-deadline", lambda here, patch: round(ledger.month_total(MONTH, DIED, now=NOW), 2), 4.8),
    case("open-all-closed", lambda here, patch: ledger.open_rents(STARTED + CLOSING, NOW), []),
    case("refusal-closes-its-own", lambda here, patch: ledger.open_rents(STARTED + CLOSING[2:], NOW), [STARTED[0], STARTED[2]]),
    case("month-closed", lambda here, patch: round(ledger.month_total(MONTH, STARTED + CLOSING, now=NOW), 2), 1.6),
    case("this-pcs-card-classes", lambda here, patch: batch.check_classes(batch.capacity.classes_for("pixal")), None, THIS_PC),
    case("misnamed-class", lambda here, patch: batch.check_classes(["gpu-24gb", "gpu24"]), Refused("not a capability class"),
         THIS_PC),
    # 229 models at 3.95 card minutes each, 3 at once, in an hour: 5 min set-up and an 11.85 min last run leave 43.15
    # min of work for 904.55 card minutes, 21 cards; 5 + 229 * 3.95 / 21 + 11.85 = 59.9 min
    case("fleet-of-21", lambda here, patch: batch.cards_needed(229, 3, 60, 3.95), 21),
    case("fleet-ends-in-its-hour", lambda here, patch: round(batch.expected_minutes(229, 21, 3, 3.95)), 60),
    case("fleet-of-1", lambda here, patch: batch.cards_needed(5, 3, 60, 3.95), 1),
    case("aim-too-short", lambda here, patch: batch.cards_needed(10, 6, 20, 3.95), Refused("too short")),  # 5 + 23.7: over 20
    # one card, 3 models at 18.7 card minutes, 3 at once: 5 + 56.1 + 56.1 = 117.2 min, aimed for, not refused
    case("capped-aims-for-what-it-can", lambda here, patch: round(batch.aimed_minutes(3, 1, 3, 18.7, 60), 1), 117.2),
    case("uncapped-keeps-its-aim", lambda here, patch: batch.aimed_minutes(5, 20, 3, 3.95, 60), 60),
    case("minutes-of-the-last-started", lambda here, patch: batch.card_minutes_per_model(), 5, ENTRIES),
    case("leftover-unlabelled", lambda here, patch: batch.is_leftover([], 1e9), True),
    case("leftover-past-deadline", lambda here, patch: batch.is_leftover([f"deadline={1e9 - 1:.0f}"], 1e9), True),
    case("not-leftover-process-alive", lambda here, patch: batch.is_leftover(
        [f"deadline={LATER:.0f}", f"host={HOST}", f"pid={os.getpid()}"], 1e9), False),
    case("leftover-process-gone", lambda here, patch: batch.is_leftover(
        [f"deadline={LATER:.0f}", f"host={HOST}", "pid=999999999"], 1e9), True),
    case("not-leftover-other-host", lambda here, patch: batch.is_leftover(
        [f"deadline={LATER:.0f}", "host=elsewhere", "pid=999999999"], 1e9), False),
    case("job-deadline-from-high", lambda here, patch: batch.job_deadline_seconds(), batch.DEADLINE_FACTOR * HIGH["high"]),
    case("list-names-once-with-options", lambda here, patch: listed(a_list(
        here, "# approved 2026-09-29\ncrate {picture} --faces 12000 --feet\n\nbarrel {picture}  # tall\n")),
        (["crate", "barrel"], 12000, [True, False])),
    case("list-names-a-model-twice", lambda here, patch: a_list(here, "crate {picture}\ncrate {picture}\n"), Refused("twice")),
    case("no-inventory", lambda here, patch: batch.from_the_inventory(a_list(here, LOCKERS), [written(here, "hub.json")]),
         Refused("no inventory")),
    case("inventory-not-approved", lambda here, patch: batch.from_the_inventory(
        a_list(here, LOCKERS), [written(here, "hub.json", INVENTORY)]), Refused("not approved")),
    # approved, a place named by no place.json entry too: Pixal3D is worded by nothing
    *(case(f"inventory-approved-{place}", lambda here, patch, place=place: batch.from_the_inventory(
        a_list(here, LOCKERS), [written(here, "hub.json", {**APPROVED, "place": place})]),
        Including({"r1", "locker", "r2", "desk"})) for place in ("habitat", "no_such_place")),
    case("list-model-on-no-row", lambda here, patch: batch.from_the_inventory(
        a_list(here, "no_such_row {picture}\n"), [written(here, "hub.json", APPROVED)]), Refused("on no row")),
    case("designed-inventory", lambda here, patch: batch.from_the_inventory(
        a_list(here, "habitat-locker {picture}\n"), [written(here, "hub.json", DESIGNED)]), Including({"r1"})),
    # a hand-in under another place's name: page A's rules
    case("designed-under-another-name", lambda here, patch: batch.from_the_inventory(
        a_list(here, "habitat-locker {picture}\n"), [written(here, "hub.json", {**DESIGNED, "scene": "lab"})]),
        Refused("not sound", "not approved", either=True)),
    case("character-not-approved", lambda here, patch: batch.from_the_characters([a_character(here)]), Refused("not approved")),
    case("character-no-picture", lambda here, patch: batch.from_the_characters([a_character(
        here, approved="owner", picture=None)]), Refused("no picture")),
    case("character-approved", lambda here, patch: built(batch.from_the_characters([a_character(
        here, approved="owner, 2026-10-09")]), here), [("fish_tang", "tang.png")]),
    case("characters-share-a-name", lambda here, patch: batch.from_the_characters(
        [a_character(here, approved="owner, 2026-10-09")] * 2), Refused("share a name")),
    # batch-1-1's two lines, not batch-1-2 nor batch-2-1; none in the run's own euros
    case("rent-fees-failed-rents-included", lambda here, patch: fees_of(
        [batch.refused_row(l4(), "out of stock", "batch-1-1"), batch.refused_row(l4(), "refused")]), (0.01, 0.0)),
    case("cluster-groups-of-three", lambda here, patch: [[take.name for take in group] for group in batch.groups_of(TAKES, 3)],
         [["crate-0", "crate-1", "crate-2"], ["crate-3"]]),
    # the takes side by side, and the job fails only when no take made its model
    case("cluster-takes-side-by-side", lambda here, patch: side_by_side(batch.cluster_line(batch.groups_of(TAKES, 3)[0])),
         (3, 3, "test -f /work/out/crate-0.glb || test -f /work/out/crate-1.glb || test -f /work/out/crate-2.glb")),
    case("cluster-job-files", lambda here, patch: (lambda job: ([entry["path"] for entry in job["inputs"]], job["outputs"]))(
        batch.cluster_job(batch.groups_of(TAKES, 3)[0], pathlib.Path("/w/group0/out"))),
        ([f"/work/in/crate-{number}.png" for number in range(3)], [{"path": "/work/out", "local": "/w/group0/out"}])),
    # a group of three asks three times the minutes of a group of one
    case("cluster-job-minutes-per-take", lambda here, patch: [batch.cluster_job(group, pathlib.Path("/w/out"))["minutes"]
                                                       for group in batch.groups_of(TAKES, 3)],
         [3 * batch.cluster_job(TAKES[3:], pathlib.Path("/w/out"))["minutes"],
          batch.cluster_job(TAKES[3:], pathlib.Path("/w/out"))["minutes"]]),
    # pixal@people, 2026-10-22: the fleet ordered at the provider's shortage every round for over an hour, each order
    # a machine that never started and billed its disk and address (EUR 2.19 in all)
    case("nothing-ordered-without-stock", lambda here, patch: no_stock_rents(a_fleet(here)), ([None] * len(batch.NO_STOCK), []),
         ((batch.cloud, "create", never_ordered), (compute, "require_cleared", lambda what: None))),
    # Fault (design of 2026-10-11): rent ordered a machine for any caller, without the runner's gate or the owner's yes
    case("nothing-rented-outside-a-cleared-run", lambda here, patch: batch.rent(a_fleet(here), None, l4(), 0),
         Refused("nothing rents outside a cleared run", by=compute.Refused),
         ((batch.cloud, "create", never_ordered), (batch, "month_spent", lambda account: 0.0))),
    case("pool-card-replaced-once-in-set-up", lambda here, patch: (lambda fleet: [
        fleet.replaces(machine) for machine in POOL_FAILURES])(one_shot_fleet(["crate"], here)[0]),
         [False, True, True, False], ((batch, "answers", lambda machine: machine["answers"]),)),
    *(priced(runner, pricing) for runner in ESTIMATES for pricing in PRICINGS),
    # --- a fleet rents only while it has work and a deadline, and never in a failed billed machine's place ---
    case("short-fleet-asks-again", lambda here, patch: short_fleet(patch), Observed(rounds=[2, 2, 2], **{
        "offers kept": True}), ((batch, "STOCK_RETRY_MINUTES", 0), (batch.time, "sleep", lambda seconds: None))),
    # Fault of 2026-10-26: a Pixal3D fleet with no card paused its deadline on its run's pool for as long as the pool
    # had ever been opened; a closed pool holds no card for it again, so the fleet runs out its own time.
    # six rounds of 0.02 s past its 0.05 s: its deadline held while the pool was open
    case("open-pool-holds-the-deadline", lambda here, patch: pool_wait(patch, False, 0.05), Observed(rounds=6),
         POOL_WAIT),
    case("closed-pool-never-stretches-it", lambda here, patch: pool_wait(patch, True, 0.1), Observed(**{
        "deadline kept": True, "ran out": True}), POOL_WAIT),
    case("stock-wait-doubles-to-half-an-hour", lambda here, patch: [batch.stock_wait_minutes(rounds)
                                                                     for rounds in range(6)], [3, 6, 12, 24, 30, 30]),
    case("stock-wait-never-past-the-deadline", lambda here, patch: stock_waits(patch), Observed(**{
        "claimed": {"machine": 1}, "first waits": [3, 6, 12], "fourth cut to the 20 min left": True, "waits": 4}),
         ((batch, "park_taken", lambda *arguments: None), (batch, "fresh_offers", lambda run, offers: offers))),
    # the wait for stock is marked as one, so the runaway watch leaves it out (2026-11-05, people-clips-made)
    case("stock-wait-marked-waiting", lambda here, patch: waiting_marks(patch), Observed(**{
        "taken": None, "first": "waiting", "last": "done", "marked on every look": True}),
         ((park, "PARKED_POLL_SECONDS", 0.01), (batch, "park_taken", lambda *arguments: None))),
    # A batch runs every job once (CONTEXT.md, owner 2026-10-20): a failed or out-of-memory job was sent back.
    case("failed-job-is-a-gap-never-sent-again", lambda here, patch: collected(here), Observed(
        sent=["crate", "barrel"], collected={"crate"}, failed=["crate"], next=None)),
    case("overdue-job", lambda here, patch: batch.overdue(RUNNING_JOBS, set(), 500, 1000.0), ["slow"]),
    case("overdue-job-already-stopped", lambda here, patch: batch.overdue(RUNNING_JOBS, {"slow"}, 500, 1000.0), []),
    case("overdue-job-stopped-once", lambda here, patch: stopped_twice(here, patch), Observed(
        commands=["pkill -f -- '[/]root/batch/out/slow\\.glb'"], stopped={"slow"},
        why="passed its 500 s deadline; stopped")),
    case("stop-finds-its-job", lambda here, patch: bool(re.search(
        PATTERN, "python scripts/pixal3d_generate.py in.png /root/batch/out/slow.glb --seed 1")), True),
    case("stop-never-the-shell-that-runs-pkill", lambda here, patch: bool(re.search(
        PATTERN, f"bash -c pkill -f -- {PATTERN}")), False),
    # A batch runs once: a billed machine that did not start or broke was replaced by a new rental, unpriced.
    case("failed-billed-card-not-replaced", lambda here, patch: lost_fleet(here, patch), Observed(
        rented=[], failed=["barrel", "crate"], next=None), ((batch.time, "sleep", lambda seconds: None),)),
    # Audit (2026-10-22): the jobs still running or never sent at a batch's deadline were left out of its gaps.
    case("leftovers-at-the-deadline-are-gaps", lambda here, patch: tended_fleet(tended(
        ["crate", "barrel", "lamp"], [{"crate": "done", "barrel": "running"}], 60, 30, here, patch, per_card=1),
        "not sent before the batch's deadline"), Observed(done=["crate"], failed=["barrel"], unsent=["lamp"],
                                                          gap_reasons={"barrel": "still running at the batch's deadline",
                                                                       "lamp": "not sent before the batch's deadline"})),
    case("broken-machine-jobs-are-gaps", lambda here, patch: tended_fleet(tended(
        ["crate", "barrel"], [{"crate": "running", "barrel": "running"}, None], 1, 600, here, patch)), Observed(
        failed=["barrel", "crate"], why=Observed(crate=Like("^its machine m-1 broke")))),
    # Audit (2026-10-22): the PC slept, the machines deleted themselves, and on waking their jobs were recorded as
    # gaps, never asked again. They are lost to sleep now, for a rerun; the model already back is not among them.
    case("jobs-lost-to-sleep-are-no-gaps", lambda here, patch: tended_fleet(tended(
        ["crate", "barrel", "lamp"], [{"crate": "done", "barrel": "running", "lamp": "running"}],
        (batch.QUIET_MINUTES + 5) * 60, 4 * 3600, here, patch)), Observed(
        done=["crate"], failed=[], asleep=["barrel", "lamp"], slept=True, stopped=True,
        lost_to_sleep=["barrel", "lamp"], gaps=[])),
    case("awake-broken-machine-is-a-gap", lambda here, patch: tended_fleet(tended(
        ["crate", "barrel"], [{"crate": "done", "barrel": "running"}, None], 60, 4 * 3600, here, patch)), Observed(
        asleep=[], failed=["barrel"], slept=False)),
    # claim moved to the next offer after a machine it rented (and was billed for) did not answer; only an
    # out-of-stock refusal, where no card ran, may move on.
    case("billed-boot-failed-is-a-gap", lambda here, patch: claimed(here, patch, [TimeoutError("did not answer")]),
         (None, ["zone-a"]), CLAIMING),
    case("out-of-stock-moves-on", lambda here, patch: claimed(here, patch, [
        batch.OutOfStock("out of stock"), TimeoutError("did not answer")]), (None, ["zone-a", "zone-b"]), CLAIMING),
    # Fault (2026-10-17, C1): a machine of a run that died first was on the bill and nowhere in the ledger. The
    # started line names the run and its ticket before the order goes.
    case("started-line-before-the-order", lambda here, patch: refused_order(here, patch), Observed(**{
        "rented": None, "orders": 1, "order": ["scw", "instance", "server", "create"], "held as it went": 1,
        "line": {"kind": ledger.RENT_STARTED, "state": "started", "euros": 0.0, "run": "pixal-run-7",
                 "name": "pixal-run-7-3", "ticket": "run-7 surfaces-paint", "type": "L4", "zone": "zone-a"},
        "deadline with grace": True, "reason": Like("out of quota"),
        "after": [(ledger.RENT_STARTED, "pixal-run-7-3"), (ledger.RENT_REFUSED, "pixal-run-7-3")]}),
         ((batch, "month_spent", lambda account: 0.0), (batch.compute, "require_cleared", lambda what: None),
          (batch.cloud, "self_delete_refusal", lambda secret, zone: None)), {compute.TICKET: "run-7 surfaces-paint"}),
    # --- no machine is left however a runner or its node ends (real processes) ---
    # Fault (2026-10-17): a `score run` killed outright left its batches renting with no one to stop them.
    case("dead-runner-batch-deletes", lambda here, patch: runner_killed(here, "lead", 1, 120), ["machine-0"]),
    # Review of C7 (2026-10-17): the node of a runner leading no group ended with it; the batch writing to it hit a
    # broken pipe and deleted one machine of three.
    case("node-of-a-groupless-runner-outlives-it", lambda here, patch: runner_killed(here, "follow", 3, 2),
         ["machine-0", "machine-1", "machine-2"]),
    # Audit (2026-10-22): a node killed alone (out of memory) while its run lived got no stop, so its batch rented on
    # until its deadline or the machines' self-delete.
    case("node-killed-alone", lambda here, patch: node_killed(here), Observed(
        deleted=["machine-0", "machine-1", "machine-2"], **{"run lives": True})),
    # Review of C7 (2026-10-17): every node's watch could send the group its own SIGTERM, and a batch already
    # deleting stops deleting at its second signal.
    case("dead-runners-group-stopped-once", lambda here, patch: stops_sent(here), "x"),
    # --- a machine a runner tends itself is armed with the grace, beaten and deleted once, whatever happens ---
    case("scene-machine-step-fails", lambda here, patch: tended_machine(
        here, patch, lambda here, patch, run, machine: scene.work_on(run, machine, {"room": "lab"})), Observed(**{
            "error": "RuntimeError: failed", "armed, beaten, deleted": True}),
         ((scene, "set_up", lambda folder, host, plan: None), (scene, "run_steps", fails),
          (scene, "local_room", lambda room: pathlib.Path("room")), (batch, "copy", lambda *arguments: None))),
    case("held-character-machine", lambda here, patch: tended_machine(here, patch, held_host), Observed(**{
        "error": None, "host": "10.0.0.1", "armed, beaten, deleted": True}),
         ((characters, "set_up", lambda machine: None), (characters, "hold", lambda run, host: None))),
    # #21: a set-up that fails ends the run with its people as gaps; the machine is never held to mend.
    case("character-set-up-failed-not-held", lambda here, patch: tended_machine(
        here, patch, lambda here, patch, run, machine: characters.held(run, machine, [pathlib.Path("/tmp/made/nev")])),
         Observed(**{"error": Like("^SystemExit: .*nev are gaps"), "armed, beaten, deleted": True}),
         ((characters, "set_up", set_up_fails), (characters, "hold", held_to_mend))),
    # its folders sent, then job 1 on the card
    case("served-blender-machine", lambda here, patch: tended_machine(here, patch, served), Observed(**{
        "error": None, "ran": [("set up", []), "remote", "copy", (1, True)], "done": "1.5", "ready": "gpu-24gb",
        "unit_seconds": [1.5], "armed, beaten, deleted": True})),
    case("spread-machine", lambda here, patch: tended_machine(here, patch, spread_shares), Observed(**{
        "error": None, "worked": [1, 2], "armed, beaten, deleted": True})),
    # --- a character run asks the card its steps need ---
    case("clips-only-run-asks-the-clip-need", lambda here, patch: characters.card_need(
        [steps_of(here, "clips", ["clips", "rig"]), steps_of(here, "scene", ["scene clips", "rig"])]),
         characters.CLIP_NEED),
    case("run-asks-its-largest-step", lambda here, patch: characters.card_need(
        [steps_of(here, "clips", ["clips", "rig"]), steps_of(here, "b", ["build"])]), {"card_gb": 4, "memory_gb": 17}),
    case("build-run-asks-the-build-need", lambda here, patch: characters.card_need([steps_of(here, "b", ["build"])]),
         characters.STEP_NEED["build"]),
    # held for identity's SAM 3D Body
    case("held-run-asks-4gb", lambda here, patch: characters.card_need([steps_of(here, "hold", [])])["card_gb"], 4),
    case("unmeasured-step-asks-the-kinds", lambda here, patch: characters.card_need(
        [steps_of(here, "b", ["build"]), steps_of(here, "new", ["build", "unmeasured"])]), None),
    case("encoder-on-this-pcs-processor-only", lambda here, patch: encoder_sent(here, patch), [True, False],
         ((batch, "copy", lambda *_, **__: None), (characters, "exit_code", lambda *_: 0),
          (characters, "bring_back", lambda *_: None))),
]


@pytest.mark.parametrize("call, expected, stubs, env", CASES)
def test_a_batch_pays_once_inside_its_limits_and_leaves_no_machine(monkeypatch, tmp_path, call, expected, stubs, env):
    """Every limit, price and clock a batch judges by gives its expected answer: the 4 h and EUR 60 limits (an
    override's room), the started-minute bill, the cards it may take, the month's open machines, the classes it checks,
    the fleet it sizes, the rate it estimates by, the machines left over and a job's deadline; and each runner says
    its estimate (its machines at the dearest offer it may take, for the minutes it says) and returns the minutes the
    limits allow, refuses a batch past EUR 60, and never refuses on the month's total; and every world a batch runs
    gives what it must: its fleet rents only while it has work and a deadline and never in a failed billed card's
    place, every job runs once (a failed, overdue, unsent or broken-machine job a gap with its reason, one lost to
    sleep none), a rent's started line goes before its order, and no machine is left however its runner, its node or
    its tending step ends."""
    said = []
    monkeypatch.setattr(batch, "say", said.append)
    monkeypatch.delenv(compute.TICKET, raising=False)  # no measured pre-flight, no override but a row's
    monkeypatch.setattr(ledger, "LEDGER", tmp_path / "ledger.jsonl")  # never the home's ledger
    for target, attribute, value in stubs:
        monkeypatch.setattr(target, attribute, value)
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    try:
        outcome = call(tmp_path, monkeypatch)
    except (SystemExit, compute.Refused) as stop:
        outcome = Stopped(stop)
    assert holds(expected, outcome, said), (outcome, said)
