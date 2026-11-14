"""Invariant of pool.py, a run's warm card pool: the run rents its pool once and every claim of every kind takes its
cards (never a rent of its own), a render or bake its processor machines too; every minute of every card is booked to
the run once, as it accrues, and every rent fits the euros the pool's clearance reserved, a bigger card standing in
for a sold-out L4 only within them; a dead card is struck off and replaced and its unfinished share goes back once;
and however the run ends (its end, a stop, a kill switch, a hung or killed collector) every card is deleted (owner,
2026-10-23: "i would use like 10 gpus but warm for the entire batch"; faults of 2026-10-24 and 2026-10-25: 6 of 13
parked machines left billing, a pool held 11 h booked EUR 0).

The cloud, ssh and process calls are stand-ins that rent nothing (`stock` cards may be rented); the money expected is
worked out from the card price and minutes held. The break that turns each red (applied once, seen red, reverted;
park.py and spread.py are the pool's own call sites):

- test_a_pool_books_every_card_once_and_deletes_every_card: in park.py `pool_parkable`, `and
  pool.current(machine["pool"]) is not None` -> `and False` (a card back from its claim is deleted).
- test_a_pool_books_every_card_once_and_deletes_every_card (its collector's first warm card): in `collect`, `collect_round(run_id,
  plan, collecting)` -> `pass`.
- test_a_pool_books_every_card_once_and_deletes_every_card (its broken card): in park.py `park`, `pool.left(machine["pool"], machine["id"])` ->
  `pass`; (its idle card deleted under the pool) in `beat`, `if reads is not None and reads(record["id"],
  record["zone"]) is None:` -> `if False:`.
- test_a_pool_books_every_card_once_and_deletes_every_card (its taker died): in `tidy`, `if card["id"] not in parked and holder and not
  process_alive(holder):` -> `if False:`.
- test_a_dead_cards_share_goes_back_on_the_queue_once: in spread.py `work_slot`, `if machine.get("pool") and
  shares.again(share):` -> `if False:`.
- test_a_pool_books_every_card_once_and_deletes_every_card (its idle spell, its taker's row): in ledger.py
  `machine_row`, `row["card_euros"], row["euros"] = row["euros"], 0.0` -> `row["card_euros"] = row["euros"]` (the card's
  minutes charged twice).
- test_a_pool_books_every_card_once_and_deletes_every_card (its hold): in `charge`, `max(0.0, owed - card.get("booked",
  0.0))` -> `max(0.0, owed)`.
- test_a_pool_books_every_card_once_and_deletes_every_card (the run's end): in `release`, `[lambda record=record:
  release_idle(record) for record in park.pool_records(run_id)]` -> `[]`.
- test_a_pool_books_every_card_once_and_deletes_every_card (its stopped runner): in park.py `pool_parkable`, drop `and not
  batch.STOPPING.is_set()`.
- test_a_class_the_pool_lacks_is_asked_for_and_no_stock_never_empties_the_offers: in `want`, `if asks.get(key,
  {}).get("disk_gb") != disk:` -> `if False:`; or in `Collecting.asked_anew`, `if classes - self.short_before:` ->
  `if False:` (a new class's ask waits out the backoff other classes built; Buy 98, 2026-11-13); or in `claim`,
  drop `batch.say(closed_under(...))` (a claim the pool closed under ends naming nothing).
- test_a_pool_books_every_card_once_and_deletes_every_card (every buy kind cleaned): in park.py `CLEANUPS`, drop the
  `"similar"` entry.
- test_a_claim_waiting_on_the_pool_past_its_runs_deadline_still_gets_the_card_with_its_time_left: in `claim`,
  `paused(run, left)` -> `pass`.
- test_a_pool_books_every_card_once_and_deletes_every_card (its size from planned card work): in `size_for`, `while sum(sizes.values()) > MOST_CARDS:` ->
  `while False:`.
- test_a_pool_books_every_card_once_and_deletes_every_card (its shrinking one machine at a time): in `shrinking`,
  `fewer = max(sorted(current)` -> `fewer = min(sorted(current)`.
- test_a_pool_books_every_card_once_and_deletes_every_card (its holding cost): in `holding_euros`, `max(prices) * 60
  * hours` -> `max(prices) * hours`.
- test_a_bigger_disk_is_one_card_beside_the_pool_for_its_claim_alone: in `live_asks`, `if process_alive(ask["pid"])`
  -> `if True` (an ask outlives its asker).
- test_a_pool_books_every_card_once_and_deletes_every_card (its late clearance's asked card): in `fill`, `roomed = bool(crowded) and
  make_room(run_id, plan, alive, crowded[0])` -> `roomed = False`.
- test_a_pool_books_every_card_once_and_deletes_every_card (its pool held two hours): in `extend`,
  `plan.update({"deadline": deadline, "euros": euros})` -> `plan.update({"euros": euros})`.
- test_the_run_lowers_its_pool_and_the_idle_cards_past_it_go: in `resize`, `sizes = sized(plan["reserved"], cards,
  processors)` -> `sizes = dict(plan["reserved"])`. Or, the plan of 2026-11-09 B5, in `idle_down` drop the
  `lowered(...)` call (the idle card's place is rented again), or the `IDLE_MINUTES` test (no card is ever let go).
- test_a_pool_books_every_card_once_and_deletes_every_card (its stopped taker): in park.py `park`, the delete and
  `pool.left` swapped.
- test_a_pool_books_every_card_once_and_deletes_every_card (its release side by side): in `at_once`, the threads -> one call after another.
- test_a_pool_holds_what_its_jobs_can_run_at_once: in `counts_for`, `[:max(0, jobs)]` -> ``; or in `reach`,
  `[row for row in rows if not row[2]]` -> `rows`.
- test_a_pool_books_every_card_once_and_deletes_every_card (its collector's first stop): in `stop_on_signals`, `signal.signal(each,
  signal.SIG_IGN)` -> `pass`.
- test_a_pool_books_every_card_once_and_deletes_every_card (a zombie holds nothing): in `process_alive`, `!= "Z"` -> `!= "?"`.
- test_a_pool_books_every_card_once_and_deletes_every_card (its L40S standing in for a sold-out L4): in `rents`, `rented =
  stand_in(plan, machine_class, alive, chosen, found) or machine_class` -> `rented = machine_class`.
- test_a_pool_books_every_card_once_and_deletes_every_card (no second L40S past its clearance): the money checked nowhere (each alone is covered by the
  other): in `stand_in`, drop `and fits(plan, alive, chosen + [bigger], found)`, and in `rents`, `if "euros" in plan
  and not fits(plan, alive, chosen + [rented], found):` -> `if False:`.
- test_a_pool_books_every_card_once_and_deletes_every_card (its L4s back): in `slot_of`, `card.get("for") or
  card["class"]` -> `card["class"]` (a stand-in no longer fills its L4's place and is let go).
- test_a_share_that_fails_on_a_card_that_answers_is_a_gap_and_the_card_works_on: in spread.py `work_slot`, `if
  machine.get("pool") and batch.answers(machine):` -> `if False:`.
- test_a_set_up_that_keeps_failing_takes_no_card_after_card: in spread.py `one_machine`, `if setup_deaths > 1:` ->
  `if setup_deaths > 5:`.
- test_a_pool_books_every_card_once_and_deletes_every_card (its collector's failed round): in `collect`, `except Exception as error:` -> `except
  ZeroDivisionError as error:`.
- test_a_pool_books_every_card_once_and_deletes_every_card (its failed delete): in `gathered`, `errors.append(error)` -> `raise`.
- test_a_pool_books_every_card_once_and_deletes_every_card (the kill switch): in `close_all`, `if not (path.parent /
  "closed").exists() and close(path.parent.name)` -> `if False`.
- test_a_pool_books_every_card_once_and_deletes_every_card (a stop while it releases): in `stop_on_signals`, `if
  batch.STOPPING.is_set():` -> `if False:`.
- test_a_render_takes_the_pools_processor_machine_a_model_kind_never_does: in `takes`, `if kind in
  capacity.PROCESSOR_KINDS and any(` -> `if any(`.
- test_a_call_asked_on_smaller_processors_takes_the_pools_bigger_one_and_adds_none: in `takes`, `| no_smaller(classes)`
  -> ``.
- test_a_pool_books_every_card_once_and_deletes_every_card (its processor class): in `processor_class`, `iter(stocked +
  offered)` -> `iter(offered)`.
- test_a_render_stages_high_minutes_hold_on_a_processor_machine_under_the_pool: in preflight.py `processor_margin`,
  `return max([1] + [capacity.processor_times(name) for name in held])` -> `return 1`.
- test_a_render_takes_the_pools_processor_machine_before_its_card_and_a_card_when_none_is_free: in park.py
  `processor_first`, `return bool(record.get("pool")) and` -> `return False and`.
- test_a_pool_opens_with_no_processor_machine_and_rents_one_once_the_run_raises_it: in `sized`, `cards if
  provider.cards(name) else processors` -> `cards`.
- test_a_pool_books_every_card_once_and_deletes_every_card (its start-up lead): in `lead_minutes`, drop `+
  LEAD_MARGIN_MINUTES`.
- test_an_idle_machine_billed_by_the_hour_stays_till_its_paid_hour_ends: in `trim`, `if not paid_ahead(record, now)}`
  -> `if True}`.
- test_a_pool_books_every_card_once_and_deletes_every_card (its hung collector): in `end_collector`, `os.kill(collector,
  signal.SIGKILL)` -> `pass`.
- test_an_open_pool_whose_collector_is_gone_gets_a_new_one_and_a_closed_pool_none: in `revive`, `plan =
  current(run_id)` -> `plan = plan_of(run_id)`.
"""
import json
import os
import pathlib
import tempfile
import signal
import subprocess
import sys
import threading
import time

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import batch  # noqa: E402
import ledger  # noqa: E402
import park  # noqa: E402
import pool  # noqa: E402
import provider  # noqa: E402
import spread  # noqa: E402
from provider import cloud  # noqa: E402

PATCHES = []  # this test's monkeypatch (patched): every stand-in and setting goes back after it


@pytest.fixture(autouse=True)
def patched(monkeypatch):
    """Every change a test makes to the modules is undone after it; no run, no stop and nothing parked before it."""
    PATCHES[:] = [monkeypatch]
    monkeypatch.setattr(batch, "say", lambda line: None)
    for name in ("SCORE_RUN_ID", "SCORE_RUN_PID", "SCORE_MAX_MACHINES", "SCORE_SPEND_TICKET"):
        monkeypatch.delenv(name, raising=False)
    batch.STOPPING.clear()
    yield
    batch.STOPPING.clear()


def patch(owner, name, value):
    """Set `owner.name` to `value` for this test alone."""
    PATCHES[0].setattr(owner, name, value)


REAL_POPEN = subprocess.Popen  # Cloud.install fakes it for park's --expire processes and the pool's collector

CARD_PRICE = 0.8 / 60  # euros a minute
GONE_PID = 2 ** 22 + 4321  # no process: the fake collector's
KINDS = ("pool-test-a", "pool-test-b")


class Cloud:
    """The cloud, ssh and process calls the pool makes, recorded instead of made; `stock` cards may be rented."""

    def __init__(self, stock):
        self.stock, self.rented, self.deleted, self.beats = stock, [], [], []
        self.lock = threading.Lock()

    def rent(self, fleet, account, offer, number, disk_gb=batch.DISK_GB):
        with self.lock:
            if self.stock <= 0 or offer.stock_word in batch.NO_STOCK:
                return None
            self.stock -= 1
            server_id = f"card-{len(self.rented) + 1}"
            self.rented.append(server_id)
        folder = fleet.folder / f"{fleet.folder.name}-{number}"
        folder.mkdir(parents=True, exist_ok=True)
        return {"id": server_id, "zone": offer.zone, "type": offer.type, "class": offer.machine_class, "cards": 1,
                "price": offer.price, "unit_minutes": 1, "created": time.time(), "disk_gb": disk_gb,
                "folder": folder, "deleted": None, "ready": None, "generating_began": None, "status": {},
                "watchdog": GONE_PID}

    def delete(self, server_id, zone):
        """As the backend: True for a machine it deleted, False for one already gone."""
        if server_id in self.deleted:
            return False
        self.deleted.append(server_id)
        return True

    def install(self):
        patch(batch, "rent", self.rent)
        patch(batch, "boot", lambda machine: machine.update(host="192.0.2.1", ready=time.time()) or machine["host"])
        patch(batch, "remote", lambda folder, host, command, **_: None)
        patch(batch, "arm_self_delete", lambda folder, host, deadline, quiet_minutes=0: None)
        patch(batch, "heartbeat", lambda folder, host: self.beats.append(folder))
        patch(batch, "start_watchdog", lambda server_id, zone, deadline, folder: GONE_PID)
        patch(batch.compute, "require_cleared", lambda what, store=None: {"node": "test"})
        patch(cloud, "retag", lambda server_id, zone, tags: None)
        patch(cloud, "delete", self.delete)
        patch(cloud, "offers", lambda classes: [offer for offer in OFFERS if offer.machine_class in classes])
        patch(cloud, "account", lambda: "account")
        patch(cloud, "allow_key", lambda *_: None)
        patch(batch, "ssh_key", lambda: "ssh-ed25519 test")
        patch(park.subprocess, "Popen", lambda *_, **__: type("Process", (), {"pid": GONE_PID})())
        for kind in KINDS:
            PATCHES[0].setitem(park.CLEANUPS, kind, lambda _machine: "rm -rf /root/test/out")


OFFERS = [provider.Offer(CARD_PRICE, 1, "card-type", zone, CARD_PRICE, "gpu-24gb", 0, "available")
          for zone in ("zone-a", "zone-b")]


def fresh(stock, sizes=None, run_id=None, euros=None, reserved=None):
    """A sandbox with no parked cards, an empty ledger and a pool opened for a run of this process (`reserved`: the
    most it may be raised to, its `sizes` when not given)."""
    calls = Cloud(stock)
    calls.install()
    batch.STOPPING.clear()
    for path in park.PARKED.glob("*.json") if park.PARKED.exists() else ():
        path.unlink()
    ledger.LEDGER.unlink(missing_ok=True)
    run_id = run_id or f"run-{time.time_ns()}"
    PATCHES[0].setenv("SCORE_RUN_ID", run_id)
    PATCHES[0].setenv("SCORE_RUN_PID", str(os.getpid()))
    pool.start(run_id, sizes or {"gpu-24gb": 2}, time.time() + 3600, euros=euros, reserved=reserved)
    return calls, run_id


def grow(run_id):
    """One round of the collector: rent what the pool lacks; the cards that came up."""
    plan = pool.current(run_id)
    return pool.fill(run_id, plan, pool.shortfall(plan, pool.idle_down(run_id, plan, pool.trim(
        run_id, plan, pool.tidy(run_id)))), "account")


def a_run(name):
    folder = pathlib.Path(os.environ["PROPS_HOME"]) / "runs" / name
    folder.mkdir(parents=True, exist_ok=True)
    return pool.Run(folder, time.time() + 3600)


def dead_check(dead, folder):
    """A fake ssh call: a dead card's folder does not answer, once (the slot's next card has the same folder)."""
    if folder in dead:
        dead.discard(folder)
        raise ConnectionError("no answer")


def claimed(run, kind):
    return batch.claim(run, "account", OFFERS, len(run.machines) + 1, kind, wanted=lambda: False)


def test_a_dead_cards_share_goes_back_on_the_queue_once():
    calls, run_id = fresh(stock=10, sizes={"gpu-24gb": 3})
    grow(run_id)
    tries, dead = [], set()
    patch(batch, "remote", lambda folder, host, command, **_: dead_check(dead, folder))

    def do(machine, share, card):
        tries.append((share, machine["id"]))
        if share == "dies-always" or (share == "dies-once" and [name for name, _ in tries].count(share) == 1):
            dead.add(machine["folder"])
            raise ConnectionError("the machine stopped answering")

    shares = spread.Shares(["ok", "dies-once", "dies-always"], deadline=time.time() + 60)
    spread.on_machines(a_run("requeue"), "account", OFFERS, 1, KINDS[0], shares, lambda machine: None, do)
    assert shares.done == ["ok", "dies-once"] and shares.failed == ["dies-always"]
    assert [name for name, _ in tries].count("dies-always") == 2  # put back once, never a third time
    assert len(calls.deleted) == 3 and len(calls.rented) == 3  # three dead cards; the runner rented none


def rented_ago(run_id, minutes):
    """Make every card of the pool as if rented `minutes` ago and parked (paid to then) half that ago; their names."""
    names = []
    for member in (pool.folder_of(run_id) / "cards").glob("*.json"):
        member.write_text(json.dumps({**json.loads(member.read_text()), "created": time.time() - minutes * 60}))
        names.append(json.loads(member.read_text())["name"])
    for path in park.PARKED.glob("*.json"):
        record = json.loads(path.read_text())
        record.update(created=record["created"] - minutes * 60, parked_at=record["parked_at"] - minutes * 30,
                      paid_minutes=minutes / 2)
        path.write_text(json.dumps(record))
    return names


def pool_euros():
    """Every euro the sandbox's ledger holds: the run's pool's and its cards' takers'."""
    return sum(entry["euros"] for entry in ledger.entries())


def test_a_class_the_pool_lacks_is_asked_for_and_no_stock_never_empties_the_offers():
    calls, run_id = fresh(stock=0, sizes={"gpu-24gb": 1})
    big = [provider.Offer(CARD_PRICE * 2, 1, "big-type", "zone-a", CARD_PRICE * 2, "gpu-48gb", 0, "shortage")]
    pool.want(run_id, big, "judge", 100)
    plan = pool.current(run_id)
    assert plan["sizes"] == {"gpu-24gb": 1}  # the pool's own sizes never change: the claim's card is an ask
    assert pool.shortfall(plan, []) == [("gpu-48gb", 100, True), ("gpu-24gb", batch.DISK_GB, False)]
    patch(cloud, "offers", lambda classes: [offer for offer in OFFERS + big if offer.machine_class in classes])
    assert {offer.machine_class for offer in batch.one_class_in_stock(["gpu-48gb", "gpu-24gb"])} == {"gpu-24gb"}
    collecting = pool.Collecting()  # the collector's wait, built on the L4s' shortage, is not the new ask's
    collecting.asked_anew([("gpu-24gb", batch.DISK_GB, False)])
    collecting.rounds, collecting.next_ask = 4, time.time() + 24 * 60
    collecting.asked_anew([("gpu-24gb", batch.DISK_GB, False)])
    assert collecting.rounds == 4
    collecting.asked_anew([("gpu-48gb", 100, True), ("gpu-24gb", batch.DISK_GB, False)])
    assert (collecting.rounds, collecting.next_ask) == (0, 0.0)
    (pool.folder_of(run_id) / "collector.log").write_text("[cloud] pool: 1 card(s) short, none in stock; asking "
                                                          "again in 30 min\n[cloud] pool: a heartbeat failed\n")
    pool.release(run_id)
    said = []
    patch(batch, "say", said.append)
    assert pool.claim(a_run("closed-under"), big, 1, "judge", 100, wanted=lambda: True) is None
    assert any("no judge card: the run's warm pool closed" in line and "gpu-48gb" in line
               and "none in stock" in line for line in said), said
    shortage = [offer._replace(stock_word="shortage") for offer in OFFERS]
    patch(cloud, "offers", lambda classes: [offer for offer in shortage if offer.machine_class in classes])
    assert batch.one_class_in_stock(["gpu-24gb"])  # none in stock: still offered, its claims wait for stock


def test_a_claim_waiting_on_the_pool_past_its_runs_deadline_still_gets_the_card_with_its_time_left():
    """Fault, 2026-10-23: sound@hub's takes became gaps after its 15 min waiting for a pool card in a shortage. The
    run's time limit counts only its work: the wait keeps its deadline ahead, the card comes, nothing is a gap."""
    calls, run_id = fresh(stock=0, sizes={"gpu-24gb": 1})
    run = a_run("waits")
    run.deadline = time.time() + 0.3
    patch(pool, "POLL_SECONDS", 0.05)
    patch(pool, "WAITING", pathlib.Path(tempfile.mkdtemp()))
    patch(pool, "HOLDING", set())  # this process holds no card yet
    got = []
    waiting = threading.Thread(target=lambda: got.append(
        batch.claim(run, "account", OFFERS, 1, KINDS[0], wanted=lambda: True)))
    waiting.start()
    time.sleep(0.8)  # past the run's own deadline, no card yet
    assert waiting.is_alive() and not got
    # waiting, holding no card, its process is marked so its node holds no job slot (2026-11-06, checkout 36); with
    # its card, not. Break: in pool.claim, drop `mark_waiting(not HOLDING)`; or in held_by, drop `HOLDING.add(...)`
    assert (pool.WAITING / str(os.getpid())).exists()
    calls.stock = 1
    assert grow(run_id) == 1
    waiting.join(5)
    assert got and got[0] is not None and got[0]["pool"] == run_id
    assert not (pool.WAITING / str(os.getpid())).exists() and got[0]["id"] in pool.HOLDING
    assert run.deadline - time.time() > 0.15  # its time left when it began waiting, counted from the card
    pool.release(run_id)








def asker_gone(run_id):
    """The pool's asks as if their asking process had ended."""
    plan = pool.plan_of(run_id)
    for ask in plan.get("asks", {}).values():
        ask["pid"] = GONE_PID
    pool.write_plan(run_id, plan)


def test_a_bigger_disk_is_one_card_beside_the_pool_for_its_claim_alone():
    """Fault, 2026-10-24: a sound row's 200 GB disk raised the whole L4 class's disk for the rest of the run, a warm
    60 GB card was let go for it and every later L4 was rented at 200 GB."""
    calls, run_id = fresh(stock=10, sizes={"gpu-24gb": 2})
    assert grow(run_id) == 2
    pool.want(run_id, OFFERS, KINDS[0], 200)
    plan = pool.current(run_id)
    assert pool.shortfall(plan, pool.members(run_id)) == [("gpu-24gb", 200, True)]
    assert grow(run_id) == 1 and len(calls.rented) == 3 and not calls.deleted  # the warm smaller cards stay
    card = batch.claim(a_run("big-disk"), "account", OFFERS, 1, KINDS[0], 200, wanted=lambda: False)
    assert card["disk_gb"] == 200
    card["healthy"] = True
    batch.delete_machine(card)  # back to the pool while its asker lives
    assert grow(run_id) == 0 and not calls.deleted
    asker_gone(run_id)
    assert grow(run_id) == 0 and calls.deleted == [card["id"]]  # idle, its asker gone: it goes, nothing replaces it
    plan = pool.current(run_id)
    assert plan["sizes"] == {"gpu-24gb": 2} and plan["disk_gb"] == batch.DISK_GB and not pool.shortfall(
        plan, pool.members(run_id))
    pool.release(run_id)


def test_the_run_lowers_its_pool_and_the_idle_cards_past_it_go():
    """Second Buy of 2026-10-24: 10 L4s held to the end while the card rows were done by 14:38."""
    calls, run_id = fresh(stock=10, sizes={"gpu-24gb": 3})
    assert grow(run_id) == 3
    pool.resize(run_id, 1, 0)
    assert pool.current(run_id)["sizes"] == {"gpu-24gb": 1}
    assert grow(run_id) == 0 and len(calls.deleted) == 2
    pool.resize(run_id, 5, 0)  # never above its opening size
    assert pool.current(run_id)["sizes"] == {"gpu-24gb": 3}
    # no idle machine (the plan of 2026-11-09 B5): a card parked idle past IDLE_MINUTES goes with its place, so the
    # collector does not rent it again and the run's resize does not raise it back
    assert grow(run_id) == 2 and len(calls.deleted) == 2
    path = next(park.PARKED.glob("*.json"))
    path.write_text(json.dumps({**json.loads(path.read_text()),
                                "parked_at": time.time() - (pool.IDLE_MINUTES + 1) * 60}))
    assert grow(run_id) == 0 and len(calls.deleted) == 3
    pool.resize(run_id, 5, 0)
    assert pool.current(run_id)["sizes"] == pool.current(run_id)["reserved"] == {"gpu-24gb": 2}
    assert grow(run_id) == 0 and len(calls.deleted) == 3
    pool.release(run_id)


def test_a_pool_holds_what_its_jobs_can_run_at_once():
    """Second Buy of 2026-10-24: sized on every line at once, 10 L4s and 3 POP2s opened for 8 jobs."""
    rows = [(f"place-{number}", 3, False) for number in range(12)] + [("place-0", 1, True), ("place-1", 2, True)]
    assert pool.counts_for(rows, 8) == (pool.MOST_CARDS, 0)  # the eight lines holding most: cards
    assert pool.counts_for(rows, 2) == (6, 0)
    assert pool.counts_for([("hub", 2, False), ("hub", 5, False), ("hub", 1, True)], 8) == (5, 1)  # a line's most
    assert pool.counts_for([("hub", 2, False), ("lab", 3, True)], 1) == (0, 3)
    assert pool.counts_for([], 8) == (0, 0)
    # Fault of 2026-11-05 (Batch 1, checkout 29): opened with only processor rows due, its card rows later, the
    # pool's reserved size (and clearance) held no card, and each L4 asked for let a warm processor machine go.
    due_later = [("bake-0", 1, True), ("bake-1", 1, True), ("place-0", 1, False)]
    assert pool.counts_for(due_later, 2) == (0, 2) and pool.reach(due_later, 2) == (1, 2)
    reserved = {"gpu-24gb": 1, PROCESSOR: 2}
    patch(cloud, "offers", lambda classes: [offer for offer in OFFERS + PROCESSOR_OFFERS
                                            if offer.machine_class in classes])
    assert [sizes for sizes, _ in pool.shrinking(reserved, 1)] == [reserved, {"gpu-24gb": 1, PROCESSOR: 1},
                                                                   {"gpu-24gb": 1}]  # not fitting: shrunk as ever
    calls, run_id = fresh(stock=10, sizes=pool.sized(reserved, 0, 2), reserved=reserved,
                          euros=pool.holding_euros(reserved, 1))
    patch(cloud, "offers", lambda classes: [offer for offer in OFFERS + PROCESSOR_OFFERS
                                            if offer.machine_class in classes])
    assert grow(run_id) == 2
    pool.resize(run_id, 1, 2)  # the card row comes due
    assert grow(run_id) == 1 and not calls.deleted
    assert sorted(card["class"] for card in pool.members(run_id)) == sorted(["gpu-24gb", PROCESSOR, PROCESSOR])
    pool.release(run_id)




BIG = [provider.Offer(CARD_PRICE * 2, 1, "big-type", "zone-a", CARD_PRICE * 2, "gpu-48gb", 0, "available")]
L4_SHORT = [offer._replace(stock_word="shortage") for offer in OFFERS]
HOUR_OF_L4 = CARD_PRICE * 60  # what the pool's clearance reserves for one L4 held its whole hour


def offered(cards):
    patch(cloud, "offers", lambda classes: [offer for offer in cards if offer.machine_class in classes])


def test_a_share_that_fails_on_a_card_that_answers_is_a_gap_and_the_card_works_on():
    """Review (2026-10-23): any error but JobFailed broke a pool card, so a local fault (a copy-in that fails) deleted
    and rented two cards a share."""
    calls, run_id = fresh(stock=10, sizes={"gpu-24gb": 1})
    grow(run_id)

    def do(machine, share, card):
        if share == "bad-input":
            raise RuntimeError("rsync exited 23")

    shares = spread.Shares(["bad-input", "ok", "bad-input-2"], deadline=time.time() + 60)
    shares.waiting[2] = "bad-input"
    spread.on_machines(a_run("local-fault"), "account", OFFERS, 1, KINDS[0], shares, lambda machine: None, do)
    assert shares.done == ["ok"] and shares.failed == ["bad-input", "bad-input"]
    assert not calls.deleted and len(calls.rented) == 1 and len(park.pool_records(run_id)) == 1  # back in the pool
    pool.release(run_id)


def test_a_set_up_that_keeps_failing_takes_no_card_after_card():
    """Review (2026-10-23): a pool card that failed in set-up was deleted and the slot took the next, until the run's
    deadline (105 cards in 3 s with the fakes). A card that failed in set-up, answering or dead, is followed by one
    more, never a third (fault, 2026-10-25: a set-up that failed on an answering card ended the slot)."""
    for answering, cards_taken in ((True, 2), (False, 2)):
        calls, run_id = fresh(stock=10, sizes={"gpu-24gb": 3})
        grow(run_id)
        if not answering:
            patch(batch, "remote", lambda folder, host, command, **_: dead_check({folder} if command == "true" else (), folder))

        def prepare(machine):
            raise RuntimeError("setup.sh: a pin that no longer resolves")

        shares = spread.Shares(["one", "two"], deadline=time.time() + 60)
        spread.on_machines(a_run(f"setup-{answering}"), "account", OFFERS, 1, KINDS[0], shares, prepare,
                           lambda machine, share, card: None)
        assert len(calls.deleted) == cards_taken and len(calls.rented) == 3, (answering, calls.deleted)
        assert list(shares.waiting) == ["one", "two"]  # gaps, for the run to say
        pool.release(run_id)


PROCESSOR = "cpu-48c-96gb"
PROCESSOR_OFFERS = [provider.Offer(CARD_PRICE, 0, "cpu-type", "zone-c", CARD_PRICE, PROCESSOR, 0, "available")]


def processor_pool():
    """A pool of one processor machine, warm, and no card yet."""
    calls, run_id = fresh(stock=10, sizes={PROCESSOR: 1})
    patch(cloud, "offers", lambda classes: [offer for offer in OFFERS + PROCESSOR_OFFERS if offer.machine_class in classes])
    assert grow(run_id) == 1
    return calls, run_id


def test_a_render_takes_the_pools_processor_machine_a_model_kind_never_does():
    """The owner, 2026-10-23: bakes and small renders take whichever machine is free first, processor or card;
    anything that needs a card (Pixal3D and the other models) still takes a card."""
    calls, run_id = processor_pool()
    assert claimed(a_run("pixal-waits"), "pixal") is None  # a card only: none warm, and the pool is asked for one
    plan = pool.current(run_id)
    assert plan["sizes"] == {PROCESSOR: 1} and [ask["class"] for ask in pool.live_asks(plan)] == ["gpu-24gb"]
    machine = claimed(a_run("render"), "blender")  # asked on a card, takes the processor machine that is free
    assert machine["class"] == PROCESSOR and machine["pool"] == run_id
    assert spread.slots("blender", machine) == [None]  # so Cycles runs on its processor (FARM_CYCLES_CPU)
    settle = [provider.Offer(CARD_PRICE, 0, "cpu-type", "zone-c", CARD_PRICE, "cpu-32c-128gb", 0, "available")]
    # asked on processors alone: its own class and the pool's processors no smaller in cores and memory
    assert pool.takes("blender", settle) == {"cpu-32c-128gb", "cpu-48c-192gb", "cpu-64c-128gb", "cpu-64c-256gb"}
    checks = [provider.Offer(CARD_PRICE, 0, "cpu-type", "zone-c", CARD_PRICE, "cpu-16c-64gb", 0, "available")]
    assert PROCESSOR in pool.takes("blender", checks) and "cpu-16c-64gb" in pool.takes("blender", checks)
    assert pool.takes("library", OFFERS) == {"gpu-24gb", "gpu-48gb", *pool.capacity.PROCESSORS}  # never an H100
    assert pool.takes("judge", OFFERS) == {"gpu-24gb", "gpu-48gb", "gpu-80gb"}  # a model kind: cards only
    pool.release(run_id)


def test_a_call_asked_on_smaller_processors_takes_the_pools_bigger_one_and_adds_none():
    """Fault, 2026-10-23: a body's checks asked on 16 or 32 cores rented a 16-core machine beside the idle 48-core."""
    calls, run_id = processor_pool()
    checks = [provider.Offer(CARD_PRICE, 0, "cpu-type", "zone-c", CARD_PRICE, "cpu-16c-64gb", 0, "available")]
    run = a_run("checks")
    machine = batch.claim(run, "account", checks, 1, "blender", wanted=lambda: False)
    assert machine["class"] == PROCESSOR and pool.current(run_id)["sizes"] == {PROCESSOR: 1}
    assert len(calls.rented) == 1
    pool.release(run_id)




def ledger_line(stage, kind, number):
    return {"ticket": f"{stage}@place key{number}", "kind": kind, "wall_minutes": 10.0, "euros": 1.0,
            "machines": [{"unit_seconds": [60.0], "minutes": 10.0, "euros": 1.0, "cards": 1}]}


def test_a_render_stages_high_minutes_hold_on_a_processor_machine_under_the_pool():
    """A render measured on cards may land on the pool's processor machine: the runaway watch, at twice its high
    minutes, never stops it for that. A measured class (the 48-core, faster than an L4: capacity.PROCESSOR_TIMES) keeps
    the card's minutes; an unmeasured one is held at capacity.PROCESSOR_SLOWER, an upper bound."""
    import preflight
    entries = [ledger_line(stage, kind, n) for stage, kind in (("look", "blender"), ("model", "pixal")) for n in range(3)]
    assert pool.processor_able("look", entries) and not pool.processor_able("model", entries)
    assert not pool.processor_able("unbought", entries)
    # a stage whose kind goes to the cluster is sized on no pool machine (#76): by its measured kind, or its own name
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("SCORE_CLOUD", "k8s")
        patch.setenv("SCORE_CLOUD_KINDS", "pixal,settle")
        assert pool.on_cluster("model", entries) and pool.on_cluster("settle", entries)
        assert not pool.on_cluster("look", entries) and not pool.on_cluster("unbought", entries)
        patch.delenv("SCORE_CLOUD")
        assert not pool.on_cluster("model", entries)
    calls, run_id = fresh(stock=10, sizes={"gpu-24gb": 1})
    card_only = preflight.node_run(entries, "look")["high_minutes"]
    pool.release(run_id)
    calls, run_id = processor_pool()
    assert pool.capacity.processor_times(PROCESSOR) < 1
    assert preflight.node_run(entries, "look")["high_minutes"] == card_only  # the card is the slower one
    pool.release(run_id)
    calls, run_id = fresh(stock=10, sizes={"cpu-32c-64gb": 1, "gpu-24gb": 1})
    assert preflight.node_run(entries, "look")["high_minutes"] == card_only * pool.capacity.PROCESSOR_SLOWER
    assert preflight.node_run(entries, "model")["high_minutes"] == card_only  # a card kind keeps its own
    pool.release(run_id)


def test_a_render_takes_the_pools_processor_machine_before_its_card_and_a_card_when_none_is_free():
    """Measured 2026-10-23 (#26): the pool's 48-core machine beat its L4 on every Blender job, so renders and bakes
    take a free processor machine first and a card only when none is; a model kind takes the card."""
    import blender_cloud  # noqa: F401 - their clean-ups, so their machines go back to the pool
    import library_bake  # noqa: F401
    calls, run_id = fresh(stock=10, sizes={"gpu-24gb": 1, PROCESSOR: 1})
    patch(cloud, "offers", lambda classes: [offer for offer in OFFERS + PROCESSOR_OFFERS if offer.machine_class in classes])
    assert grow(run_id) == 2
    first = claimed(a_run("render-1"), "blender")
    assert first["class"] == PROCESSOR
    second = claimed(a_run("render-2"), "library")  # the processor is busy: the card
    assert second["class"] == "gpu-24gb"
    for machine in (first, second):
        machine["healthy"] = True
        batch.delete_machine(machine)
    assert claimed(a_run("model"), "pixal")["class"] == "gpu-24gb"
    assert claimed(a_run("render-3"), "blender")["class"] == PROCESSOR
    assert len(calls.rented) == 2
    pool.release(run_id)


def test_a_pool_opens_with_no_processor_machine_and_rents_one_once_the_run_raises_it():
    """Batch 1 of 2026-10-24: the pool rented its three processor machines at the start and they sat idle for an hour
    while only Pixal3D ran; they open at 0 and the run's heartbeat raises them (resize) when a render is near."""
    reserved = {"gpu-24gb": 1, PROCESSOR: 2}
    assert pool.sized(reserved, 10, 0) == {"gpu-24gb": 1, PROCESSOR: 0}
    calls, run_id = fresh(stock=10)  # the fakes installed; this run's own pool opened next
    pool.release(run_id)
    run_id = f"run-{time.time_ns()}"
    PATCHES[0].setenv("SCORE_RUN_ID", run_id)
    pool.start(run_id, pool.sized(reserved, 10, 0), time.time() + 3600, reserved=reserved)
    patch(cloud, "offers", lambda classes: [offer for offer in OFFERS + PROCESSOR_OFFERS if offer.machine_class in classes])
    assert grow(run_id) == 1 and len(calls.rented) == 1  # the card alone
    pool.resize(run_id, 1, 1)
    assert pool.current(run_id)["sizes"] == {"gpu-24gb": 1, PROCESSOR: 1}
    assert grow(run_id) == 1 and len(calls.rented) == 2
    pool.resize(run_id, 1, 5)  # never above what it reserved
    assert pool.current(run_id)["sizes"] == {"gpu-24gb": 1, PROCESSOR: 2}
    pool.resize(run_id, 1, 0)
    assert grow(run_id) == 0 and len(calls.deleted) == 1  # the idle processor goes once no render is near
    pool.release(run_id)




def test_an_idle_machine_billed_by_the_hour_stays_till_its_paid_hour_ends():
    """A processor machine is billed by the started hour: let go early, its paid minutes are lost and nothing saved."""
    calls, run_id = fresh(stock=10, sizes={"gpu-24gb": 1})
    grow(run_id)
    path = next(park.PARKED.glob("*.json"))
    record = json.loads(path.read_text())
    path.write_text(json.dumps({**record, "unit_minutes": 60, "created": time.time() - 20 * 60}))
    pool.resize(run_id, 0, 0)
    assert grow(run_id) == 0 and not calls.deleted  # 40 paid minutes left: kept
    path.write_text(json.dumps({**record, "unit_minutes": 60, "created": time.time() - 58 * 60}))
    assert grow(run_id) == 0 and len(calls.deleted) == 1  # its paid hour ends: it goes
    pool.release(run_id)


def test_an_open_pool_whose_collector_is_gone_gets_a_new_one_and_a_closed_pool_none():
    """Fault of 2026-10-26: with its collector gone and the pool open, nothing rents its places and every claim waits
    on it; the run's heartbeat starts a collector again (revive), never for a pool closed or one whose collector
    lives."""
    _, run_id = fresh(stock=1)
    patch(pool, "spawn_collector", lambda run_id, folder: os.getpid())
    assert pool.revive(run_id) and pool.plan_of(run_id)["collector"] == os.getpid()
    assert not pool.revive(run_id)  # it lives
    with pool.locked(run_id):
        pool.write_plan(run_id, {**pool.plan_of(run_id), "collector": GONE_PID})
    pool.close(run_id)
    assert not pool.revive(run_id) and pool.plan_of(run_id)["collector"] == GONE_PID


UNMARKED = ["similar", "unirig", "parts", "closeups", "moss-sound", "unlit"]  # kinds whose set-up writes no mark
# two cards each booked to its started minute, the hold rounding their sum to the micro-euro
BOOKED_WITHIN = 2 * CARD_PRICE + 1e-6
CLEANED = ("/root/make/*", "/root/pics/out", "/root/props/work/scene", "/root/similar", "/root/UniRig", "/root/smoke")


def ended_unreaped():
    """A child process that has ended and is not yet reaped: a zombie (the caller reaps it)."""
    child = os.fork()
    if child == 0:
        os._exit(0)
    stat = pathlib.Path(f"/proc/{child}/stat")
    deadline = time.time() + 5
    while time.time() < deadline and stat.read_text().rpartition(")")[2].split()[0] != "Z":
        time.sleep(0.01)
    return child


def started_after(machine_class, minutes):
    """A pool ledger row of one machine of `machine_class` answering `minutes` after its order."""
    return {"kind": pool.KIND, "machines": [{"class": machine_class, "started": True, "start_wait_minutes": minutes}]}


def refused(call):
    """What `call` refused with (a RuntimeError's message), or "" when it answered."""
    try:
        call()
    except RuntimeError as error:
        return str(error)
    return ""


def test_a_pool_books_every_card_once_and_deletes_every_card():
    """One run's pool of two cards, rented 30 min ago: claims of every kind take them and give them back cleaned, the
    pool books their minutes once (their idle spells, their rents and their takers' rows adding nothing), and the
    run's end deletes the idle card at once and the held one once it comes back. Faults: 2026-10-23 (the likeness threw its L4 away), 2026-10-25
    (Batch 1's pool of 10 L4s and 3 processor machines was held 11 h and booked EUR 0.00).

    Before it, a pool of three cards loses one of each way a card goes out of use: one broken under its job, one
    whose taker died, one deleted under the pool while idle (2026-11-05: its failing beat finds it gone); each is
    struck off and one collector round rents the three places again. A stopped runner's card is deleted, on the
    pool until its delete went through (review of 2026-10-24), and a claim while stopping rents nothing. Its release
    comes as its collector's process is stopped: the first stop ends the collector, a second is ignored (first Buy of
    2026-10-24: a card being rented was never deleted), and one that comes while it releases lets the release go on
    (2026-10-24: 6 of 13 parked machines left billing); a collector hung past its stop is killed once the release has
    waited its bound (Batch 1, 2026-10-25); the cards go side by side, one delete failing: every card is tried and
    the failure said (review of 2026-10-23).

    First, a pool run by its collector: the job starts on the first warm card while the collector, one round of it
    failing on the provider's API (review of 2026-10-23: that ended the collector), grows the pool beside it; the
    kill switch closes the pool so nothing replaces the cards it releases (review of 2026-10-23).

    Last, a pool whose clearance the run sets only later: with L4s sold out it rents no larger card until its
    clearance is known, then one L40S in an L4's place within it and never a second (owner, 2026-10-23: "yes" to a
    bigger card within the run's money), which a 24 GB claim takes; once L4s are back the working L40S stays and an
    L4 fills its place when it leaves; held two hours, a card a claim asks for is priced for both hours against the
    whole clearance and an idle card makes room for it (review of 2026-10-24: asked cards were rented with no money
    check), and a card too dear for the clearance is refused; released, the pool stays closed (Batch 1 of 2026-10-24:
    the pool closed at its cleared 4 h with ~550 rows queued).

    Before the cards, the pool's own judgements, one row each: its size from the run's planned card work (capped at
    MOST_CARDS); its shrinking one machine at a time, keeping a processor beside its cards while it can, each step
    cheaper; its holding cost, every card warm every hour at its dearest offer, and no price for a class not sold; its
    processor class, the biggest in stock or else the biggest offered, held to the cap and the class quota; a class's
    start-up lead, the median of its measured start-ups plus the margin (the margin alone unmeasured; owner,
    2026-10-25: "cant u just do the start up earlier then when u need them again"); and a taker killed and not yet
    reaped holds its card no longer (review of 2026-10-24).
    """
    import characters
    Cloud(0).install()
    dear = [provider.Offer(CARD_PRICE * 3, 0, "cpu-type", "zone-c", CARD_PRICE * 3, PROCESSOR, 0, "available")]
    offered(OFFERS + dear)
    planned = pool.size_for([("pixal", 400, 2.0, 3.0), ("library", 200, 2.0, 1.0), ("judge", 30, 1.0, 1.0)])
    shrunk = pool.shrinking({"gpu-24gb": 3, PROCESSOR: 2}, 1)
    found = [provider.Offer(1, 2, "t", "z", 1, "cpu-48c-96gb", 0, "shortage"),
             provider.Offer(1, 0, "t", "z", 1, "cpu-32c-64gb", 0, "available")]
    starts = [started_after("gpu-24gb", 4.0), started_after("gpu-24gb", 6.0), started_after("gpu-24gb", 30.0),
              started_after(PROCESSOR, 2.0), {"kind": pool.HOLD, "machines": [], "euros": 1.0}]
    zombie = ended_unreaped()
    try:
        judged = [  # (row, what the pool judged, what it should judge)
            ("much planned card work: capped, both card classes",
             (sum(planned.values()), planned["gpu-48gb"] >= 1, planned["gpu-24gb"] >= 1), (pool.MOST_CARDS, True, True)),
            ("little planned card work: one L4", pool.size_for([("pixal", 2, 2.0, 3.0)]), {"gpu-24gb": 1}),
            ("shrinking: one machine a step, a processor beside the cards while it can", [sizes for sizes, _ in shrunk],
             [{"gpu-24gb": 3, PROCESSOR: 2}, {"gpu-24gb": 2, PROCESSOR: 2}, {"gpu-24gb": 2, PROCESSOR: 1},
              {"gpu-24gb": 1, PROCESSOR: 1}, {"gpu-24gb": 1}]),
            ("shrinking: each step cheaper", [euros for _, euros in shrunk],
             sorted((euros for _, euros in shrunk), reverse=True)),
            ("shrinking: the last step is the card alone's holding cost", shrunk[-1][1],
             pool.holding_euros({"gpu-24gb": 1}, 1)),
            ("holding cost: every card warm every hour", pool.holding_euros({"gpu-24gb": 4}, 4),
             round(4 * CARD_PRICE * 60 * 4, 4)),
            ("holding cost: a class not sold is refused",
             "sells no gpu-80gb" in refused(lambda: pool.holding_euros({"gpu-80gb": 1}, 1)), True),
            ("processor class: the biggest in stock", pool.processor_class(found), "cpu-32c-64gb"),
            ("processor class: none in stock, the biggest offered", pool.processor_class(found[:1]), "cpu-48c-96gb"),
            ("processors added", pool.with_processors({"gpu-24gb": 4}, 5, found),
             {"gpu-24gb": 4, "cpu-32c-64gb": 5}),
            ("processors held to the cap and the class quota",
             pool.with_processors({"gpu-24gb": 4}, 50, found)["cpu-32c-64gb"],
             min(pool.MOST_PROCESSORS, pool.capacity.max_machines("cpu-32c-64gb"))),
            ("one processor", pool.with_processors({"gpu-24gb": 4}, 1, found), {"gpu-24gb": 4, "cpu-32c-64gb": 1}),
            ("no processor asked", pool.with_processors({"gpu-24gb": 4}, 0, found), {"gpu-24gb": 4}),
            ("no processor offered", pool.with_processors({"gpu-24gb": 4}, 2, []), {"gpu-24gb": 4}),
            ("lead: the median start-up plus the margin", pool.lead_minutes("gpu-24gb", starts),
             6.0 + pool.LEAD_MARGIN_MINUTES),
            ("leads: card and processor apart", pool.leads(["gpu-24gb", PROCESSOR], starts),
             {False: 6.0 + pool.LEAD_MARGIN_MINUTES, True: 2.0 + pool.LEAD_MARGIN_MINUTES}),
            ("leads: unmeasured, the margin alone", pool.leads(["gpu-48gb"], starts),
             {False: pool.LEAD_MARGIN_MINUTES, True: pool.LEAD_MARGIN_MINUTES}),
            ("a zombie holds nothing", pool.process_alive(zombie), False),
            ("a live process holds", pool.process_alive(os.getpid()), True),
        ]
    finally:
        os.waitpid(zombie, 0)
    for row, judgement, expected in judged:
        assert judgement == expected, (row, judgement, expected)
    calls, run_id = fresh(stock=1, sizes={"gpu-24gb": 3})
    patch(pool, "POLL_SECONDS", 0.05)
    patch(batch, "stock_wait_minutes", lambda rounds: 0.001)
    asked = []

    def offers(classes):  # the collector's first ask fails on the provider's API
        asked.append(classes)
        if threading.current_thread() is collector and len(asked) == 1:
            raise RuntimeError("scw: 503 Service Unavailable")
        return [offer for offer in OFFERS if offer.machine_class in classes]
    patch(cloud, "offers", offers)
    collector = threading.Thread(target=pool.collect, args=(run_id,))
    collector.start()
    try:
        card = batch.claim(a_run("first-warm"), "account", OFFERS, 1, KINDS[0], wanted=lambda: True)
        assert card["pool"] == run_id and len(calls.rented) == 1  # the job starts on the first card, the pool still short
        calls.stock = 5  # stock comes back: the collector grows the pool beside the run
        deadline = time.time() + 5
        while len(park.pool_records(run_id)) < 2 and time.time() < deadline:
            time.sleep(0.02)
        assert len(pool.members(run_id)) == 3 and len(calls.rented) == 3
        assert pool.state(run_id) == {"size": 3, "warm": 3, "idle": 2, "open": True}  # the cockpit's cards warm
        assert collector.is_alive() and pool.current(run_id) is not None and len(asked) >= 2  # its failed round
        card["healthy"] = True
        batch.delete_machine(card)
        assert run_id in pool.close_all() and pool.close_all() == []  # the kill switch, then its own release
        for record in park.pool_records(run_id):
            park.release(record["id"], record["zone"], record["token"])
    finally:
        pool.close(run_id)
        collector.join(5)
    assert not collector.is_alive() and len(calls.rented) == 3 and sorted(calls.deleted) == sorted(calls.rented)
    calls, run_id = fresh(stock=10, sizes={"gpu-24gb": 3})
    assert grow(run_id) == 3
    orphan, broken = claimed(a_run("orphan"), KINDS[0]), claimed(a_run("dead"), KINDS[0])
    pool.held_by(run_id, orphan["id"], GONE_PID)  # its taker died holding it
    broken["healthy"] = False  # it broke under its job
    batch.delete_machine(broken)
    assert calls.deleted == [broken["id"]] and len(pool.members(run_id)) == 2
    [idle] = park.pool_records(run_id)
    patch(batch, "heartbeat", lambda folder, host: (_ for _ in ()).throw(subprocess.CalledProcessError(255, ["ssh"])))
    PATCHES[0].setattr(cloud, "server_record", lambda server_id, zone: None, raising=False)
    pool.beat(run_id)
    assert idle["id"] not in {record["id"] for record in park.pool_records(run_id)}
    assert {member["id"] for member in pool.members(run_id)} == {orphan["id"]}
    assert grow(run_id) == 3 and orphan["id"] in calls.deleted and len(calls.rented) == 6
    assert len(pool.members(run_id)) == 3
    stopped, seen = claimed(a_run("stopped"), KINDS[0]), []
    patch(cloud, "delete", lambda server_id, zone: seen.append([found["id"] for found in pool.members(run_id)])
          or calls.deleted.append(server_id) or True)
    batch.STOPPING.set()
    try:
        stopped["healthy"] = True
        batch.delete_machine(stopped)
        assert claimed(a_run("stopped-again"), KINDS[0]) is None
    finally:
        batch.STOPPING.clear()
    assert calls.deleted[-1] == stopped["id"] and stopped["id"] in seen[0]  # on the pool while its delete ran
    assert stopped["id"] not in {found["id"] for found in pool.members(run_id)} and len(calls.rented) == 6
    left = {found["id"] for found in pool.members(run_id)}
    gate, tried, lock = threading.Barrier(len(left), timeout=5), [], threading.Lock()

    def slow_delete(server_id, zone):
        with lock:
            tried.append(server_id)
            first = len(tried) <= len(left)
            if len(tried) == 1:  # a stop signal while it releases (the run's group stop, then the pool's close)
                os.kill(os.getpid(), signal.SIGTERM)
        if first:
            gate.wait()  # each delete waits for the others: one after another this would time out
        if first and server_id == tried[0]:  # the first card's first delete fails
            raise RuntimeError("Failed to detach block volume")
        return True
    patch(cloud, "delete", slow_delete)
    hung = REAL_POPEN([sys.executable, "-c", "import signal, time; signal.signal(signal.SIGTERM, signal.SIG_IGN); "
                       "print('ready', flush=True); time.sleep(60)"], stdout=subprocess.PIPE, text=True)
    assert hung.stdout.readline().strip() == "ready"  # its SIGTERM is ignored from here
    with pool.locked(run_id):
        pool.write_plan(run_id, {**pool.plan_of(run_id), "collector": hung.pid})
    patch(pool, "COLLECTOR_STOP_SECONDS", 0.5)
    before = {number: signal.getsignal(number) for number in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)}
    pool.stop_on_signals()
    try:
        with pytest.raises(SystemExit):  # the first stop ends the collector
            os.kill(os.getpid(), signal.SIGTERM)
            time.sleep(1)
        assert batch.STOPPING.is_set() and signal.getsignal(signal.SIGTERM) == signal.SIG_IGN
        os.kill(os.getpid(), signal.SIGTERM)  # the second: ignored, the release goes on
        pool.stop_on_signals()  # a stop that finds the collector already releasing (collect's end set STOPPING)
        started = time.time()
        with pytest.raises(RuntimeError, match="detach"):
            pool.release(run_id)
        assert hung.wait(5) == -signal.SIGKILL and time.time() - started < 5
    finally:
        for number, handler in before.items():
            signal.signal(number, handler)
        batch.STOPPING.clear()
        hung.kill()
        hung.wait()
    assert set(tried) == left and tried.count(tried[0]) == 2  # the failed one tried again as a member
    assert pool.current(run_id) is None and not pool.members(run_id) and not park.pool_records(run_id)
    calls, run_id = fresh(stock=10, sizes={"gpu-24gb": 2})
    assert grow(run_id) == 2 and grow(run_id) == 0 and len(calls.rented) == 2  # rented once; full, nothing more
    for name in rented_ago(run_id, 30):
        ledger.rent_started("machines", name, {"type": "card-type", "zone": "zone-a", "price": CARD_PRICE}, None)
    assert ledger.open_rents(ledger.entries(), time.time())  # its rent counted as open until the pool books it
    commands = []
    patch(batch, "remote", lambda folder, host, command, **_: commands.append(command))
    kinds = [*KINDS, characters.KIND, "pictures", "pictures-20b", "scene", "prove", *UNMARKED]  # prove: sound takes
    for number, kind in enumerate(kinds):
        run = a_run(f"buy-{kind}")
        card = claimed(run, kind)
        assert card is not None and card["pool"] == run_id and card["id"] in calls.rented, kind
        if not number:  # the first take closes its card's 15 idle minutes since it parked, its rent cold before
            entries = ledger.entries()
            idle = [entry for entry in entries if entry["batch"].startswith("pool-idle-")]
            cold = [entry for entry in entries if entry["batch"] == f"pool-{run_id}-{card['id']}"]
            assert len(idle) == 1 and idle[0]["run"] == run_id and cold and cold[0]["run"] == run_id
            assert idle[0]["euros"] == 0.0 and cold[0]["euros"] == 0.0  # the pool's hold books them
            assert abs(idle[0]["machines"][0]["card_euros"] - 15 * CARD_PRICE) < CARD_PRICE + 1e-9
            assert card["paid_minutes"] >= 30
            row = ledger.machine_row(card)
            assert row["euros"] == 0.0 and row["card_euros"] < CARD_PRICE + 1e-9  # the taker's time, measured only
        card["healthy"] = True
        batch.delete_machine(card)  # back to the pool, not deleted
        assert len(park.pool_records(run_id)) == 2, kind
        if not number:
            ledger.record({"started": "2026-10-25T12:00:00Z", "batch": "job", "kind": kind,
                           **ledger.machines_record(run.machines, [], time.time())})  # the taker's own row
    assert len(calls.rented) == 2 and not calls.deleted
    assert not pool.shortfall(pool.current(run_id), pool.members(run_id))
    for removed in CLEANED:
        assert any(removed in command for command in commands), (removed, commands)
    assert all(park.ALL_MARKS in park.CLEANUPS[kind](card) for kind in UNMARKED)  # the next kind sets up again
    pool.hold(run_id)
    assert abs(pool_euros() - 2 * 30 * CARD_PRICE) <= BOOKED_WITHIN  # 30 min to the started minute, the job's included
    assert not ledger.open_rents(ledger.entries(), time.time())  # booked: its rent no longer counted beside
    pool.hold(run_id)
    assert abs(pool_euros() - 2 * 30 * CARD_PRICE) <= BOOKED_WITHIN  # booked once, not again
    card = claimed(a_run("end"), KINDS[0])
    pool.release(run_id)
    assert pool.current(run_id) is None and len(calls.deleted) == 1  # the idle card at once; the held one is its taker's
    card["healthy"] = True
    batch.delete_machine(card)  # comes back after the end: deleted, not parked
    assert sorted(calls.deleted) == sorted(calls.rented) and not park.pool_records(run_id)
    idle = [entry["run"] for entry in ledger.entries() if entry["batch"].startswith("pool-idle-")]
    assert idle == [run_id] * (len(kinds) + 2)  # each idle spell once: to its take, the last to its delete
    assert abs(pool_euros() - 2 * 30 * CARD_PRICE) <= BOOKED_WITHIN  # struck off: to its delete, still once
    assert claimed(a_run("after"), KINDS[0]) is None and len(calls.rented) == 2  # a claim after the end takes nothing
    calls, run_id = fresh(stock=10, sizes={"gpu-24gb": 2})  # last, a pool whose clearance the run sets late
    offered(L4_SHORT + BIG)
    assert grow(run_id) == 0 and not calls.rented  # L4s sold out, its clearance unknown: no larger card either
    plan = pool.current(run_id)
    pool.extend(run_id, plan["deadline"], 2 * HOUR_OF_L4)
    assert grow(run_id) == 1  # one L40S (two L4 hours) fits the two L4s' reservation; a second would not
    [card] = pool.members(run_id)
    assert card["class"] == "gpu-48gb" and card["for"] == "gpu-24gb"
    assert pool.shortfall(pool.current(run_id), pool.members(run_id)) == [("gpu-24gb", batch.DISK_GB, False)]
    assert grow(run_id) == 0 and len(calls.rented) == 1  # too little money for a second larger card
    taken = claimed(a_run("on-l40s"), KINDS[0])  # asked on L4 offers alone
    assert taken["class"] == "gpu-48gb" and "gpu-80gb" not in pool.takes("blender", OFFERS)  # never-classes out
    taken["healthy"] = True
    batch.delete_machine(taken)
    pool.extend(run_id, plan["deadline"], 3 * HOUR_OF_L4)
    offered(OFFERS + BIG)  # the L4s are back: an L4 in the other place, the working L40S kept
    assert grow(run_id) == 1 and not calls.deleted
    assert sorted(found["class"] for found in pool.members(run_id)) == ["gpu-24gb", "gpu-48gb"]
    pool.left(run_id, card["id"])  # the L40S leaves: its place goes back to an L4
    assert grow(run_id) == 1 and [found["class"] for found in pool.members(run_id)] == ["gpu-24gb"] * 2
    rented, deleted = len(calls.rented), len(calls.deleted)
    pool.extend(run_id, plan["started"] + 2 * 3600, 4 * HOUR_OF_L4)  # held two hours: priced for both
    assert pool.current(run_id)["deadline"] == plan["started"] + 2 * 3600
    pool.want(run_id, OFFERS, KINDS[0], 200)  # a third L4 two hours passes four L4 hours: room is made first
    assert grow(run_id) == 1 and len(calls.rented) == rented and len(calls.deleted) == deleted + 1
    assert grow(run_id) == 1 and len(calls.rented) == rented + 1  # the asked card in the room made
    assert grow(run_id) == 0 and len(calls.rented) == rented + 1  # its place not filled again while it is asked
    pool.extend(run_id, plan["started"] + 2 * 3600, 3 * HOUR_OF_L4)
    with pytest.raises(pool.TooDear):  # one L40S held two hours is four L4 hours (one hour: two, it would fit)
        pool.want(run_id, BIG, "judge", batch.DISK_GB)
    pool.extend(run_id, plan["started"] + 2 * 3600, 4 * HOUR_OF_L4)
    pool.want(run_id, BIG, "judge", batch.DISK_GB)  # fits now
    pool.release(run_id)
    pool.extend(run_id, plan["started"] + 3 * 3600, 6 * HOUR_OF_L4)  # released: stays closed
    assert pool.current(run_id) is None and sorted(calls.deleted) == sorted(calls.rented)
