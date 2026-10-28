"""Invariant of spread.py and the claim its slots make (batch.claim): a batch spread over machines runs every share
once (a batch, CONTEXT.md, owner 2026-10-20): a share whose command failed, or whose machine broke under it, is a
gap and never handed to another machine; a broken machine takes nothing more; a machine that fails its set-up has
none rented in its place; each card runs its kind's measured runs at once; machines claimed side by side spread over
the zones; and a slot that finds no stock asks again until its work is gone, its deadline passes or a stop comes
(2026-10-09: six of seven slots gave up on their first round and one L4 did all the work).

Renting, arming, beating and deleting are stand-ins that rent nothing. The break that turns each red (applied once,
seen red, reverted):

- test_a_failed_share_is_a_gap_and_never_taken_again: in `Shares.failed_job`, `self.failed.append(item)` ->
  `self.waiting.append(item)`.
- test_an_open_queue_waits_for_work_until_closed: in `Shares.close`, `self.open = False` -> `pass` (the taker waits
  out its idle time).
- test_a_machine_runs_its_kinds_measured_runs_on_each_card: in `slots`, `range(capacity.runs_at_once(kind,
  machine["class"]))` -> `range(1)`.
- test_the_machines_share_the_work_and_a_broken_machines_share_is_a_gap: in `work_slot`, the broken machine's
  `shares.failed_job(share)` (before "its share is a gap") -> `shares.put(share)`; or drop `broken.set()`.
- test_a_machine_that_fails_its_set_up_is_not_replaced: in `one_machine`, `if not machine.get("pool") or
  shares.queued() <= 0:` -> `if shares.queued() <= 0:`.
- test_machines_claimed_side_by_side_spread_over_the_zones: in batch.py `claim_from`, `capacity.next_offer(remaining,
  run.machines + pending, kind)` -> `capacity.next_offer(remaining, run.machines, kind)`.
- test_a_slot_keeps_asking_until_stock_comes_up: in batch.py `claim_rounds`, `while machine is None and
  still_wanted(run, wanted):` -> `if machine is None and still_wanted(run, wanted):`.
- test_a_slot_stops_asking_when_its_work_is_gone: in batch.py `still_wanted`, `return wanted is None or
  bool(wanted())` -> `return True`.
- test_a_slot_stops_asking_at_its_deadline_and_on_a_signal: in batch.py `still_wanted`, drop `or time.time() >=
  run.deadline`.
- test_a_wait_for_this_pcs_machine_is_not_the_works_time: in `this_pc_waited`, drop `run.deadline += waited` (the
  share is never run); or `return waited >= THIS_PC_WAIT_SECONDS` -> `return False` (the slot gives up).
"""
import pathlib
import sys
import threading
import time

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import batch  # noqa: E402
import pictures  # noqa: E402
import provider  # noqa: E402
import spread  # noqa: E402


@pytest.fixture(autouse=True)
def cleared(monkeypatch):
    """The parts kind cleans up (park.CLEANUPS), so a claim first looks for a parked machine, which asks for a cleared
    run; renting is faked here and the sandbox has none parked. No warm pool, no stop."""
    monkeypatch.setattr(batch.compute, "require_cleared", lambda what, store=None: {"node": "test"})
    monkeypatch.delenv("SCORE_RUN_ID", raising=False)
    batch.STOPPING.clear()
    yield
    batch.STOPPING.clear()


def offer(machine_class, zone, stock=0):
    return provider.Offer(0.01, stock, f"{machine_class}-type", zone, 0.01, machine_class, 0, "available")


def test_a_failed_share_is_a_gap_and_never_taken_again():
    shares = spread.Shares(["a", "b"])
    assert shares.take() == "a"
    shares.failed_job("a")
    assert shares.take() == "b" and shares.take() is None and shares.failed == ["a"]


def test_an_open_queue_waits_for_work_until_closed():
    shares = spread.Shares(open_queue=True, idle=5)
    taken = []
    taker = threading.Thread(target=lambda: taken.append(shares.take()))
    taker.start()
    deadline = time.time() + 2
    while shares.queued() != -1 and time.time() < deadline:
        time.sleep(0.01)
    assert shares.queued() == -1  # one slot waiting for a share
    shares.put("job")
    taker.join(2)
    assert taken == ["job"]
    began = time.time()
    threading.Timer(0.2, shares.close).start()
    assert shares.take() is None and time.time() - began < 3


def test_a_machine_runs_its_kinds_measured_runs_on_each_card():
    assert spread.slots("pixal", {"class": "gpu-80gb"}) == [0] * 10  # three runs per 24 GB: ten on 80 GB
    assert spread.slots("judge", {"class": "gpu-80gb-x2"}) == [0, 1]
    assert spread.slots("blender", {"class": "cpu-32c-128gb"}) == [None]
    assert spread.slots(None, {"class": "cpu-32c-128gb"}, at_once=4) == [None] * 4


@pytest.fixture
def fake_machines(monkeypatch, tmp_path):
    """A run whose claims, arming, beating and deleting are stand-ins that rent nothing."""
    numbers = iter(range(1, 100))

    def claim(run, account, found, number, kind, disk_gb, wanted=None):
        machine = {"folder": run.folder / f"m{next(numbers)}", "host": "host", "class": "gpu-24gb", "type": "L4",
                   "zone": "zone-a", "created": time.time(), "ready": time.time(), "deleted": None}
        run.machines.append(machine)
        return machine
    monkeypatch.setattr(batch, "claim", claim)
    monkeypatch.setattr(batch, "arm_self_delete", lambda *arguments: None)
    monkeypatch.setattr(batch, "delete_machine", lambda machine: machine.update(deleted=time.time()))
    monkeypatch.setattr(batch, "say", lambda line: None)
    monkeypatch.setattr(pictures, "keep_beating", lambda folder, host, stop: None)
    return pictures.Run(tmp_path, time.time() + 60)


def test_the_machines_share_the_work_and_a_broken_machines_share_is_a_gap(fake_machines):
    run, done, broken = fake_machines, [], []

    def do(machine, share, card):
        if share == "bad":
            raise spread.JobFailed("its script failed")
        if machine["folder"].name == "m1" and not broken:
            broken.append(share)
            raise ConnectionError("lost")
        time.sleep(0.05)
        done.append((machine["folder"].name, share))
    shares = spread.Shares(["one", "two", "three", "four", "bad"])
    spread.on_machines(run, None, [], 3, "parts", shares, lambda machine: None, do)
    assert "m1" not in {name for name, _ in done}  # the broken machine took nothing after
    assert sorted(share for _, share in done) == sorted({"one", "two", "three", "four"} - set(broken))  # each once
    assert sorted(shares.failed) == sorted(["bad", *broken]) and not shares.waiting
    assert len(run.machines) == 3 and all(machine["deleted"] for machine in run.machines)


def test_a_machine_that_fails_its_set_up_is_not_replaced(fake_machines):
    run, done = fake_machines, []

    def prepare(machine):
        if machine["folder"].name == "m1":
            raise RuntimeError("a package mirror was mid-sync")
    shares = spread.Shares(["one", "two"])
    spread.on_machines(run, None, [], 1, "parts", shares, prepare,
                       lambda machine, share, card: done.append((machine["folder"].name, share)))
    # no machine rented in its place: its shares stay waiting, gaps for a new batch and a new ask
    assert done == [] and len(run.machines) == 1 and list(shares.waiting) == ["one", "two"]


def test_machines_claimed_side_by_side_spread_over_the_zones(tmp_path, monkeypatch):
    def rent(run, account, chosen, number, disk_gb):
        time.sleep(0.1)  # the three claims overlap while they rent
        return {"zone": chosen.zone, "class": chosen.machine_class, "deleted": None}
    monkeypatch.setattr(batch, "rent", rent)
    monkeypatch.setattr(batch, "boot", lambda machine: "host")
    run = pictures.Run(tmp_path, time.time() + 60)
    offers = [offer("gpu-24gb", zone) for zone in ("zone-a", "zone-b", "zone-c")]
    claims = [threading.Thread(target=batch.claim, args=(run, None, offers, number, "parts")) for number in range(3)]
    for claim in claims:
        claim.start()
    for claim in claims:
        claim.join()
    assert sorted(machine["zone"] for machine in run.machines) == ["zone-a", "zone-b", "zone-c"]


@pytest.fixture
def stock_after(monkeypatch, tmp_path):
    """Renting stubbed: every offer is out of stock until the backend's offers were read again `rounds[0]` times; no
    time is waited. Gives the run, the reads and the rounds to set."""
    reads, rounds = [], [0]

    def rent(run, account, chosen, number, disk_gb):
        return None if len(reads) < rounds[0] else {"zone": chosen.zone, "class": chosen.machine_class,
                                                    "deleted": None}

    def read(classes):
        reads.append(sorted(classes))
        return [offer(machine_class, zone) for machine_class in classes for zone in ("zone-a", "zone-b")]
    monkeypatch.setattr(batch, "rent", rent)
    monkeypatch.setattr(batch, "boot", lambda machine: "host")
    monkeypatch.setattr(batch.cloud, "offers", read)
    monkeypatch.setattr(batch, "STOCK_RETRY_MINUTES", 0)
    monkeypatch.setattr(batch, "say", lambda line: None)
    return pictures.Run(tmp_path, time.time() + 60), reads, rounds


def test_a_slot_keeps_asking_until_stock_comes_up(stock_after):
    run, reads, rounds = stock_after
    rounds[0] = 3
    machine = batch.claim(run, "account", [offer("gpu-24gb", "zone-a"), offer("gpu-80gb", "zone-b")], 1, "parts")
    assert machine is not None and len(reads) == 3
    assert reads[0] == ["gpu-24gb", "gpu-80gb"]  # every class the job fits, read again each round


def test_a_slot_stops_asking_when_its_work_is_gone(stock_after):
    run, reads, rounds = stock_after
    rounds[0] = 99
    left = [True, True, False]
    assert batch.claim(run, "account", [offer("gpu-24gb", "zone-a")], 1, "parts", wanted=lambda: left.pop(0)) is None
    assert len(reads) == 1


def test_a_slot_stops_asking_at_its_deadline_and_on_a_signal(stock_after):
    run, reads, rounds = stock_after
    rounds[0] = 99
    run.deadline = time.time() - 1
    assert batch.claim(run, "account", [offer("gpu-24gb", "zone-a")], 1, "parts") is None and not reads
    run.deadline = time.time() + 60
    batch.STOPPING.set()
    assert batch.claim(run, "account", [offer("gpu-24gb", "zone-a")], 1, "parts") is None



def test_a_wait_for_this_pcs_machine_is_not_the_works_time(fake_machines, monkeypatch):
    """On this PC's one machine, a claim that waited out the run's deadline behind the run's own jobs asks again,
    and the deadline moves on by the wait, so the share runs; on a rented backend nothing moves."""
    run, done, made = fake_machines, [], batch.claim
    run.deadline = time.time() + 0.3
    calls = []

    def claim(run, account, found, number, kind, disk_gb, wanted=None):
        calls.append(time.time())
        if len(calls) == 1:  # the machine busy with the run's other jobs until the deadline
            time.sleep(max(0.0, run.deadline - time.time()) + 0.05)
            return None
        return made(run, account, found, number, kind, disk_gb, wanted)
    monkeypatch.setattr(batch, "claim", claim)
    monkeypatch.setattr(spread, "THIS_PC_WAIT_SECONDS", 0.2)
    monkeypatch.setattr(spread.provider.cloud, "NAME", "local")
    shares = spread.Shares(["one"], deadline=run.deadline)
    spread.on_machines(run, None, [], 1, "blender", shares, lambda machine: None,
                       lambda machine, share, card: done.append(share))
    assert done == ["one"] and len(calls) == 2, (done, calls)
    assert shares.deadline > calls[1] and run.deadline > calls[1]
    monkeypatch.setattr(spread.provider.cloud, "NAME", "scaleway")
    calls.clear()
    before = run.deadline = time.time() + 0.3
    shares = spread.Shares(["two"], deadline=run.deadline)
    spread.on_machines(run, None, [], 1, "blender", shares, lambda machine: None,
                       lambda machine, share, card: done.append(share))
    assert done == ["one"] and len(calls) == 1 and run.deadline == before  # a rented backend gives up as before
