"""Checks for a run's warm card pool (pool.py), without renting anything: a run rents its pool once and claims of
every kind reuse its cards, the run's jobs start on the first warm card while the collector grows the pool, a dead
card is struck off and replaced, a dead card's job goes back on the queue once, every minute of a card is booked to
its run once (a job on it adding none), the release at the run's end (or its stop) deletes every card, and a stopped
runner's card is deleted.

Run: .venv/bin/python tools/cloud/pool_test.py   (make tests runs it)
"""
import json
import os
import pathlib
import sys
import tempfile
import threading
import time

_SANDBOX = pathlib.Path(tempfile.mkdtemp(prefix="pool-test-"))
# paths.py reads these when it is imported, so they come first.
os.environ["PROPS_HOME"] = str(_SANDBOX)
os.environ["PROPS_WORK"] = str(_SANDBOX / "work")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import batch  # noqa: E402
import ledger  # noqa: E402
import park  # noqa: E402
import pool  # noqa: E402
import provider  # noqa: E402
import spread  # noqa: E402
from provider import cloud  # noqa: E402

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
        batch.rent = self.rent
        batch.boot = lambda machine: machine.update(host="192.0.2.1", ready=time.time()) or machine["host"]
        batch.remote = lambda folder, host, command, **_: None
        batch.arm_self_delete = lambda folder, host, deadline, quiet_minutes=0: None
        batch.heartbeat = lambda folder, host: self.beats.append(folder)
        batch.start_watchdog = lambda server_id, zone, deadline, folder: GONE_PID
        batch.compute.require_cleared = lambda what, store=None: {"node": "test"}
        cloud.retag = lambda server_id, zone, tags: None
        cloud.delete = self.delete
        cloud.offers = lambda classes: [offer for offer in OFFERS if offer.machine_class in classes]
        cloud.account = lambda: "account"
        cloud.allow_key = lambda *_: None
        batch.ssh_key = lambda: "ssh-ed25519 test"
        park.subprocess.Popen = lambda *_, **__: type("Process", (), {"pid": GONE_PID})()
        for kind in KINDS:
            park.CLEANUPS[kind] = lambda _machine: "rm -rf /root/test/out"


OFFERS = [provider.Offer(CARD_PRICE, 1, "card-type", zone, CARD_PRICE, "gpu-24gb", 0, "available")
          for zone in ("zone-a", "zone-b")]


def fresh(stock, sizes=None, run_id=None, euros=None):
    """A sandbox with no parked cards, an empty ledger and a pool opened for a run of this process."""
    calls = Cloud(stock)
    calls.install()
    batch.STOPPING.clear()
    for path in park.PARKED.glob("*.json") if park.PARKED.exists() else ():
        path.unlink()
    ledger.LEDGER.unlink(missing_ok=True)
    run_id = run_id or f"run-{time.time_ns()}"
    os.environ["SCORE_RUN_ID"] = run_id
    os.environ["SCORE_RUN_PID"] = str(os.getpid())
    pool.start(run_id, sizes or {"gpu-24gb": 2}, time.time() + 3600, euros=euros)
    return calls, run_id


def grow(run_id):
    """One round of the collector: rent what the pool lacks; the cards that came up."""
    plan = pool.current(run_id)
    return pool.fill(run_id, plan, pool.shortfall(plan, pool.trim(run_id, plan, pool.tidy(run_id))), "account")


def a_run(name):
    folder = _SANDBOX / "runs" / name
    folder.mkdir(parents=True, exist_ok=True)
    return pool.Run(folder, time.time() + 3600)


def dead_check(dead, folder):
    """A fake ssh call: a dead card's folder does not answer, once (the slot's next card has the same folder)."""
    if folder in dead:
        dead.discard(folder)
        raise ConnectionError("no answer")


def claimed(run, kind):
    return batch.claim(run, "account", OFFERS, len(run.machines) + 1, kind, wanted=lambda: False)


def test_a_run_rents_its_pool_once_and_claims_of_every_kind_reuse_its_cards():
    calls, run_id = fresh(stock=10)
    assert grow(run_id) == 2 and len(calls.rented) == 2
    assert grow(run_id) == 0 and len(calls.rented) == 2  # full: nothing more rented
    seen = set()
    for kind in KINDS * 2:
        run = a_run(kind)
        card = claimed(run, kind)
        assert card is not None and card["pool"] == run_id
        seen.add(card["id"])
        card["healthy"] = True
        batch.delete_machine(card)  # back to the pool, not deleted
    assert len(calls.rented) == 2 and seen <= set(calls.rented) and not calls.deleted
    assert len(park.pool_records(run_id)) == 2 and not pool.shortfall(pool.current(run_id), pool.members(run_id))


def test_jobs_start_on_the_first_warm_card_while_the_collector_grows_the_pool():
    calls, run_id = fresh(stock=1, sizes={"gpu-24gb": 3})
    pool.POLL_SECONDS, waits = 0.05, batch.stock_wait_minutes
    batch.stock_wait_minutes = lambda rounds: 0.001
    collector = threading.Thread(target=pool.collect, args=(run_id,))
    collector.start()
    try:
        run = a_run("first-warm")
        card = batch.claim(run, "account", OFFERS, 1, KINDS[0], wanted=lambda: True)
        assert card["pool"] == run_id and len(calls.rented) == 1  # the job starts on the first card, the pool still short
        calls.stock = 5  # stock comes back: the collector grows the pool beside the run
        deadline = time.time() + 5
        while len(park.pool_records(run_id)) < 2 and time.time() < deadline:
            time.sleep(0.02)
        assert len(pool.members(run_id)) == 3 and len(calls.rented) == 3
        assert pool.state(run_id) == {"size": 3, "warm": 3, "idle": 2, "open": True}  # the cockpit's cards warm
        card["healthy"] = True
        batch.delete_machine(card)
    finally:
        pool.release(run_id)
        collector.join(5)
        batch.stock_wait_minutes = waits
    assert not collector.is_alive() and sorted(calls.deleted) == sorted(calls.rented)  # every card gone at the end


def test_a_dead_card_is_struck_off_and_replaced():
    calls, run_id = fresh(stock=10)
    grow(run_id)
    card = claimed(a_run("dead"), KINDS[0])
    card["healthy"] = False  # it broke under its job
    batch.delete_machine(card)
    assert calls.deleted == [card["id"]] and len(pool.members(run_id)) == 1
    assert grow(run_id) == 1 and len(pool.members(run_id)) == 2 and len(calls.rented) == 3


def test_a_card_whose_taker_died_is_deleted_and_replaced():
    calls, run_id = fresh(stock=10)
    grow(run_id)
    card = claimed(a_run("orphan"), KINDS[0])
    pool.held_by(run_id, card["id"], GONE_PID)
    assert grow(run_id) == 1 and card["id"] in calls.deleted and len(pool.members(run_id)) == 2


def test_a_dead_cards_share_goes_back_on_the_queue_once():
    calls, run_id = fresh(stock=10, sizes={"gpu-24gb": 3})
    grow(run_id)
    tries, dead = [], set()
    batch.remote = lambda folder, host, command, **_: dead_check(dead, folder)

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
    """Make the pool's one card as if rented `minutes` ago and parked (paid to then) half that ago."""
    member = next((pool.folder_of(run_id) / "cards").glob("*.json"))
    member.write_text(json.dumps({**json.loads(member.read_text()), "created": time.time() - minutes * 60}))
    path = next(park.PARKED.glob("*.json"))
    record = json.loads(path.read_text())
    record.update(created=record["created"] - minutes * 60, parked_at=record["parked_at"] - minutes * 30,
                  paid_minutes=minutes / 2)
    path.write_text(json.dumps(record))
    return json.loads(member.read_text())["name"]


def pool_euros():
    """Every euro the sandbox's ledger holds: the run's pool's and its cards' takers'."""
    return sum(entry["euros"] for entry in ledger.entries())


def test_the_pools_idle_spell_and_rent_keep_their_minutes_and_book_no_euros_of_their_own():
    calls, run_id = fresh(stock=10, sizes={"gpu-24gb": 1})
    grow(run_id)
    rented_ago(run_id, 20)
    card = claimed(a_run("idle"), KINDS[0])
    entries = ledger.entries()
    idle = [entry for entry in entries if entry["batch"].startswith("pool-idle-")]
    cold = [entry for entry in entries if entry["batch"] == f"pool-{run_id}-{card['id']}"]
    assert len(idle) == 1 and idle[0]["run"] == run_id and cold and cold[0]["run"] == run_id
    assert idle[0]["euros"] == 0.0 and cold[0]["euros"] == 0.0  # the pool's hold books them (hold)
    assert abs(idle[0]["machines"][0]["card_euros"] - 10 * CARD_PRICE) < CARD_PRICE + 1e-9  # its 10 idle minutes
    assert card["paid_minutes"] >= 20
    row = ledger.machine_row(card)
    assert row["euros"] == 0.0 and row["card_euros"] < CARD_PRICE + 1e-9  # the taker's time, for the measurements


def test_a_pool_card_held_n_minutes_books_n_minutes_as_it_accrues():
    """Fault of 2026-10-25: Batch 1's pool of 10 L4s and 3 processor machines was held 11 h and booked EUR 0.00."""
    calls, run_id = fresh(stock=10, sizes={"gpu-24gb": 1})
    grow(run_id)
    name = rented_ago(run_id, 30)
    ledger.rent_started("machines", name, {"type": "card-type", "zone": "zone-a", "price": CARD_PRICE}, None)
    assert ledger.open_rents(ledger.entries(), time.time())  # its rent counted as open until the pool books it
    pool.hold(run_id)
    assert abs(pool_euros() - 30 * CARD_PRICE) <= CARD_PRICE + 1e-9  # 30 min, to the started minute
    assert not ledger.open_rents(ledger.entries(), time.time())  # booked: its rent is no longer counted beside
    pool.hold(run_id)
    assert abs(pool_euros() - 30 * CARD_PRICE) <= CARD_PRICE + 1e-9  # booked once, not again
    pool.release(run_id)
    assert calls.deleted and abs(pool_euros() - 30 * CARD_PRICE) <= CARD_PRICE + 1e-9  # struck off: to its delete


def test_a_job_on_a_pool_card_adds_no_second_charge():
    calls, run_id = fresh(stock=10, sizes={"gpu-24gb": 1})
    grow(run_id)
    rented_ago(run_id, 30)
    run = a_run("job")
    card = claimed(run, KINDS[0])
    card["healthy"] = True
    batch.delete_machine(card)  # the job done, the card back in the pool
    ledger.record({"started": "2026-10-25T12:00:00Z", "batch": "job", "kind": KINDS[0],
                   **ledger.machines_record(run.machines, [], time.time())})  # the taker's own row
    pool.hold(run_id)
    pool.release(run_id)
    assert abs(pool_euros() - 30 * CARD_PRICE) <= CARD_PRICE + 1e-9  # every minute once, the job's included


def test_the_runs_end_releases_the_pool_and_a_card_back_after_it_is_deleted():
    calls, run_id = fresh(stock=10)
    grow(run_id)
    card = claimed(a_run("end"), KINDS[0])
    pool.release(run_id)
    assert pool.current(run_id) is None and len(calls.deleted) == 1  # the idle card at once; the held one is its taker's
    idle = [entry["run"] for entry in ledger.entries() if entry["batch"].startswith("pool-idle-")]
    assert idle == [run_id, run_id]  # the taken card's spell parked, then the idle card's to its delete
    card["healthy"] = True
    batch.delete_machine(card)  # comes back after the end: deleted, not parked
    assert sorted(calls.deleted) == sorted(calls.rented) and not park.pool_records(run_id)
    assert claimed(a_run("after"), KINDS[0]) is None and len(calls.rented) == 2  # a claim after the end takes nothing


def test_a_stopped_runner_deletes_its_card_and_rents_nothing():
    calls, run_id = fresh(stock=10, sizes={"gpu-24gb": 1})
    grow(run_id)
    card = claimed(a_run("stopped"), KINDS[0])
    batch.STOPPING.set()
    try:
        card["healthy"] = True
        batch.delete_machine(card)
        assert claimed(a_run("stopped-again"), KINDS[0]) is None
    finally:
        batch.STOPPING.clear()
    assert calls.deleted == [card["id"]] and len(calls.rented) == 1 and not pool.members(run_id)


def test_a_class_the_pool_lacks_is_asked_for_and_no_stock_never_empties_the_offers():
    calls, run_id = fresh(stock=0, sizes={"gpu-24gb": 1})
    big = [provider.Offer(CARD_PRICE * 2, 1, "big-type", "zone-a", CARD_PRICE * 2, "gpu-48gb", 0, "shortage")]
    pool.want(run_id, big, "judge", 100)
    plan = pool.current(run_id)
    assert plan["sizes"] == {"gpu-24gb": 1}  # the pool's own sizes never change: the claim's card is an ask
    assert pool.shortfall(plan, []) == [("gpu-48gb", 100, True), ("gpu-24gb", batch.DISK_GB, False)]
    cloud.offers = lambda classes: [offer for offer in OFFERS + big if offer.machine_class in classes]
    assert {offer.machine_class for offer in batch.one_class_in_stock(["gpu-48gb", "gpu-24gb"])} == {"gpu-24gb"}
    pool.release(run_id)
    shortage = [offer._replace(stock_word="shortage") for offer in OFFERS]
    cloud.offers = lambda classes: [offer for offer in shortage if offer.machine_class in classes]
    assert batch.one_class_in_stock(["gpu-24gb"])  # none in stock: still offered, its claims wait for stock


def test_a_card_of_every_buy_kind_goes_back_to_the_pool_cleaned():
    """Every kind that runs on pool cards has its clean-up, so a card it used goes back to the pool, its run's files
    removed, rather than being deleted and rented again (fault, 2026-10-23: the likeness threw its L4 away). A kind
    whose set-up writes no mark also removes every set-up mark, so the next kind on the card sets up again."""
    import characters
    calls, run_id = fresh(stock=10, sizes={"gpu-24gb": 1})
    grow(run_id)
    commands = []
    batch.remote = lambda folder, host, command, **_: commands.append(command)
    unmarked = ["similar", "unirig", "parts", "closeups", "moss-sound", "unlit"]
    kinds = [characters.KIND, "pictures", "pictures-20b", "scene", "prove", *unmarked]  # prove: the sound takes
    for kind in kinds:
        card = claimed(a_run(f"buy-{kind}"), kind)
        assert card is not None and card["pool"] == run_id, kind
        card["healthy"] = True
        batch.delete_machine(card)
        assert len(park.pool_records(run_id)) == 1, kind  # back in the pool
    assert len(calls.rented) == 1 and not calls.deleted
    for removed in ("/root/make/*", "/root/pics/out", "/root/props/work/scene", "/root/similar", "/root/UniRig",
                    "/root/smoke"):
        assert any(removed in command for command in commands), (removed, commands)
    assert all(park.ALL_MARKS in park.CLEANUPS[kind](card) for kind in unmarked)
    pool.release(run_id)


def test_a_claim_waiting_on_the_pool_past_its_runs_deadline_still_gets_the_card_with_its_time_left():
    """Fault, 2026-10-23: sound@hub's takes became gaps after its 15 min waiting for a pool card in a shortage. The
    run's time limit counts only its work: the wait keeps its deadline ahead, the card comes, nothing is a gap."""
    calls, run_id = fresh(stock=0, sizes={"gpu-24gb": 1})
    run = a_run("waits")
    run.deadline = time.time() + 0.3
    pool.POLL_SECONDS = 0.05
    got = []
    waiting = threading.Thread(target=lambda: got.append(
        batch.claim(run, "account", OFFERS, 1, KINDS[0], wanted=lambda: True)))
    waiting.start()
    time.sleep(0.8)  # past the run's own deadline, no card yet
    assert waiting.is_alive() and not got
    calls.stock = 1
    assert grow(run_id) == 1
    waiting.join(5)
    assert got and got[0] is not None and got[0]["pool"] == run_id
    assert run.deadline - time.time() > 0.15  # its time left when it began waiting, counted from the card
    pool.release(run_id)


def test_a_pool_is_sized_from_the_runs_planned_card_work():
    sizes = pool.size_for([("pixal", 400, 2.0, 3.0), ("library", 200, 2.0, 1.0), ("judge", 30, 1.0, 1.0)])
    assert sum(sizes.values()) == pool.MOST_CARDS and sizes["gpu-48gb"] >= 1 and sizes["gpu-24gb"] >= 1
    assert pool.size_for([("pixal", 2, 2.0, 3.0)]) == {"gpu-24gb": 1}


def test_a_pool_shrinks_one_machine_at_a_time_keeping_a_processor_beside_its_cards_while_it_can():
    dear = [provider.Offer(CARD_PRICE * 3, 0, "cpu-type", "zone-c", CARD_PRICE * 3, PROCESSOR, 0, "available")]
    cloud.offers = lambda classes: [offer for offer in OFFERS + dear if offer.machine_class in classes]
    choices = pool.shrinking({"gpu-24gb": 3, PROCESSOR: 2}, 1)
    assert [sizes for sizes, _ in choices] == [{"gpu-24gb": 3, PROCESSOR: 2}, {"gpu-24gb": 2, PROCESSOR: 2},
                                               {"gpu-24gb": 2, PROCESSOR: 1}, {"gpu-24gb": 1, PROCESSOR: 1},
                                               {"gpu-24gb": 1}]
    assert [euros for _, euros in choices] == sorted((euros for _, euros in choices), reverse=True)
    assert choices[-1][1] == pool.holding_euros({"gpu-24gb": 1}, 1)


def test_a_pools_holding_cost_is_every_card_warm_every_hour_at_its_dearest_offer():
    Cloud(0).install()
    assert pool.holding_euros({"gpu-24gb": 4}, 4) == round(4 * CARD_PRICE * 60 * 4, 4)
    try:
        pool.holding_euros({"gpu-80gb": 1}, 1)
    except RuntimeError as error:
        assert "sells no gpu-80gb" in str(error)
    else:
        raise AssertionError("a class with no offer was priced")


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


def test_every_rent_fits_the_pools_clearance_and_an_asked_card_makes_room():
    """Review of 2026-10-24: a card a claim asked for (a bigger disk, a class the pool lacks) was rented beside the
    pool with no money check, so the pool could bill past its clearance."""
    calls, run_id = fresh(stock=10, sizes={"gpu-24gb": 2}, euros=2 * HOUR_OF_L4)
    offered(OFFERS + BIG)
    assert grow(run_id) == 2
    pool.want(run_id, OFFERS, KINDS[0], 200)
    assert grow(run_id) == 1 and len(calls.rented) == 2 and len(calls.deleted) == 1  # room made, nothing beside
    assert grow(run_id) == 1 and len(calls.rented) == 3  # the asked card in the room made
    assert grow(run_id) == 0 and len(calls.rented) == 3  # the place it took is not filled again while it is asked
    pool.release(run_id)
    calls, run_id = fresh(stock=10, sizes={"gpu-24gb": 1}, euros=HOUR_OF_L4)
    offered(OFFERS + BIG)
    try:
        pool.want(run_id, BIG, "judge", batch.DISK_GB)  # one L40S alone is two L4 hours
        raise AssertionError("a card no pool of this clearance can hold was asked for")
    except pool.TooDear:
        pass
    pool.release(run_id)


def test_a_pool_held_longer_stays_open_past_its_first_end_and_prices_its_whole_hours():
    """Batch 1 of 2026-10-24: the pool closed at its cleared 4 h with ~550 rows queued, and every finish after failed
    (a claim under a closed pool returns no card). Held longer, it is open past its first end, and its rents and
    asks are priced for its whole hours against its whole clearance."""
    calls, run_id = fresh(stock=10, sizes={"gpu-24gb": 1}, euros=HOUR_OF_L4)
    plan = pool.current(run_id)
    pool.extend(run_id, plan["started"] + 2 * 3600, 2 * HOUR_OF_L4)
    assert pool.current(run_id)["deadline"] == plan["started"] + 2 * 3600
    offered(OFFERS + BIG)
    assert grow(run_id) == 1  # one L4 its two hours fits two L4 hours
    try:
        pool.want(run_id, BIG, "judge", batch.DISK_GB)  # one L40S held two hours is four L4 hours
        raise AssertionError("an L40S held two hours passes a clearance of two L4 hours")
    except pool.TooDear:
        pass
    pool.extend(run_id, plan["started"] + 2 * 3600, 4 * HOUR_OF_L4)
    pool.want(run_id, BIG, "judge", batch.DISK_GB)  # fits now
    pool.release(run_id)
    pool.extend(run_id, plan["started"] + 3 * 3600, 6 * HOUR_OF_L4)  # released: stays closed
    assert pool.current(run_id) is None


def test_the_run_lowers_its_pool_and_the_idle_cards_past_it_go():
    """Second Buy of 2026-10-24: 10 L4s held to the end while the card rows were done by 14:38."""
    calls, run_id = fresh(stock=10, sizes={"gpu-24gb": 3})
    assert grow(run_id) == 3
    pool.resize(run_id, 1, 0)
    assert pool.current(run_id)["sizes"] == {"gpu-24gb": 1}
    assert grow(run_id) == 0 and len(calls.deleted) == 2
    pool.resize(run_id, 5, 0)  # never above its opening size
    assert pool.current(run_id)["sizes"] == {"gpu-24gb": 3}
    pool.release(run_id)


def test_a_stopped_takers_card_stays_on_the_pool_until_its_delete_went_through():
    """Review of 2026-10-24: a card struck off before its delete was out of every release's sight when the taker was
    killed between the two."""
    calls, run_id = fresh(stock=10, sizes={"gpu-24gb": 1})
    grow(run_id)
    card = claimed(a_run("stopped"), KINDS[0])
    seen = []
    cloud.delete = lambda server_id, zone: seen.append([found["id"] for found in pool.members(run_id)]) or True
    batch.STOPPING.set()
    try:
        batch.delete_machine(card)
    finally:
        batch.STOPPING.clear()
    assert seen[0] == [card["id"]] and not pool.members(run_id)  # on the pool while its delete ran
    pool.release(run_id)


def test_a_release_deletes_the_cards_side_by_side():
    calls, run_id = fresh(stock=10, sizes={"gpu-24gb": 4})
    assert grow(run_id) == 4
    gate, started = threading.Barrier(4, timeout=5), []

    def slow_delete(server_id, zone):
        started.append(server_id)
        gate.wait()  # each delete waits for the other three: one after another this would time out
        return True
    cloud.delete = slow_delete
    pool.release(run_id)
    assert len(started) == 4 and not pool.members(run_id)


def test_a_pool_holds_what_its_jobs_can_run_at_once():
    """Second Buy of 2026-10-24: sized on every line at once, 10 L4s and 3 POP2s opened for 8 jobs."""
    rows = [(f"place-{number}", 3, False) for number in range(12)] + [("place-0", 1, True), ("place-1", 2, True)]
    assert pool.counts_for(rows, 8) == (pool.MOST_CARDS, 0)  # the eight lines holding most: cards
    assert pool.counts_for(rows, 2) == (6, 0)
    assert pool.counts_for([("hub", 2, False), ("hub", 5, False), ("hub", 1, True)], 8) == (5, 1)  # a line's most
    assert pool.counts_for([("hub", 2, False), ("lab", 3, True)], 1) == (0, 3)
    assert pool.counts_for([], 8) == (0, 0)


def test_the_collector_stops_once_and_lets_its_release_finish():
    """First Buy of 2026-10-24: the run's release signalled the stopping collector again, and a card it was renting
    was never deleted."""
    import signal
    before = {number: signal.getsignal(number) for number in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)}
    pool.stop_on_signals()
    try:
        try:
            os.kill(os.getpid(), signal.SIGTERM)
            time.sleep(1)
            raise AssertionError("the first stop did not end the collector")
        except SystemExit:
            pass
        assert batch.STOPPING.is_set() and signal.getsignal(signal.SIGTERM) == signal.SIG_IGN
        os.kill(os.getpid(), signal.SIGTERM)  # the second: ignored, the release goes on
    finally:
        for number, handler in before.items():
            signal.signal(number, handler)
        batch.STOPPING.clear()


def test_a_zombie_holds_nothing():
    """A taker killed and not yet reaped holds its card no longer (review of 2026-10-24)."""
    child = os.fork()
    if child == 0:
        os._exit(0)
    stat = pathlib.Path(f"/proc/{child}/stat")
    deadline = time.time() + 5
    while time.time() < deadline and stat.read_text().rpartition(")")[2].split()[0] != "Z":
        time.sleep(0.01)
    assert not pool.process_alive(child)  # ended, not yet reaped
    os.waitpid(child, 0)
    assert pool.process_alive(os.getpid())


BIG = [provider.Offer(CARD_PRICE * 2, 1, "big-type", "zone-a", CARD_PRICE * 2, "gpu-48gb", 0, "available")]
L4_SHORT = [offer._replace(stock_word="shortage") for offer in OFFERS]
HOUR_OF_L4 = CARD_PRICE * 60  # what the pool's clearance reserves for one L4 held its whole hour


def offered(cards):
    cloud.offers = lambda classes: [offer for offer in cards if offer.machine_class in classes]


def test_with_l4s_sold_out_the_pool_rents_an_l40s_in_an_l4s_place_and_a_24gb_claim_takes_it():
    """Owner, 2026-10-23: "yes" to a bigger card when the L4s are sold out, within the run's money."""
    calls, run_id = fresh(stock=10, sizes={"gpu-24gb": 2}, euros=2 * HOUR_OF_L4)
    offered(L4_SHORT + BIG)
    assert grow(run_id) == 1  # one L40S (two L4 hours) fits the two L4s' reservation; a second would not
    [card] = pool.members(run_id)
    assert card["class"] == "gpu-48gb" and card["for"] == "gpu-24gb"
    assert pool.shortfall(pool.current(run_id), pool.members(run_id)) == [("gpu-24gb", batch.DISK_GB, False)]
    assert claimed(a_run("on-l40s"), KINDS[0])["class"] == "gpu-48gb"  # asked on L4 offers alone
    assert "gpu-80gb" not in pool.takes("blender", OFFERS)  # a kind's never-classes stay out
    pool.release(run_id)


def test_with_too_little_money_no_larger_card_is_rented():
    calls, run_id = fresh(stock=10, sizes={"gpu-24gb": 1}, euros=HOUR_OF_L4)
    offered(L4_SHORT + BIG)
    assert grow(run_id) == 0 and not calls.rented
    calls, run_id = fresh(stock=10, sizes={"gpu-24gb": 1})  # a clearance unknown: none either
    offered(L4_SHORT + BIG)
    assert grow(run_id) == 0 and not calls.rented
    pool.release(run_id)


def test_once_l4s_are_back_the_pool_rents_l4s_and_keeps_its_working_l40s():
    calls, run_id = fresh(stock=10, sizes={"gpu-24gb": 2}, euros=3 * HOUR_OF_L4)
    offered(L4_SHORT + BIG)
    assert grow(run_id) == 1  # the L40S stands in; a second L40S would pass the money, and no L4 is in stock
    offered(OFFERS + BIG)
    assert grow(run_id) == 1
    assert sorted(card["class"] for card in pool.members(run_id)) == ["gpu-24gb", "gpu-48gb"] and not calls.deleted
    stand_in = next(card for card in pool.members(run_id) if card["class"] == "gpu-48gb")
    pool.left(run_id, stand_in["id"])  # the L40S leaves: its place goes back to an L4
    assert grow(run_id) == 1
    assert [card["class"] for card in pool.members(run_id)] == ["gpu-24gb"] * 2
    pool.release(run_id)


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
    deadline (105 cards in 3 s with the fakes). A set-up failing on a card that answers ends the slot; a card that died
    in set-up is followed by one more, never a third."""
    for answering, cards_taken in ((True, 1), (False, 2)):
        calls, run_id = fresh(stock=10, sizes={"gpu-24gb": 3})
        grow(run_id)
        if not answering:
            batch.remote = lambda folder, host, command, **_: dead_check({folder} if command == "true" else (), folder)

        def prepare(machine):
            raise RuntimeError("setup.sh: a pin that no longer resolves")

        shares = spread.Shares(["one", "two"], deadline=time.time() + 60)
        spread.on_machines(a_run(f"setup-{answering}"), "account", OFFERS, 1, KINDS[0], shares, prepare,
                           lambda machine, share, card: None)
        assert len(calls.deleted) == cards_taken and len(calls.rented) == 3, (answering, calls.deleted)
        assert list(shares.waiting) == ["one", "two"]  # gaps, for the run to say
        pool.release(run_id)


def test_a_failed_round_never_ends_the_collector():
    """Review (2026-10-23): one API error in a round (scw's server-type list, a delete) ended the collector, which
    released the pool, and every later step of the run took no card."""
    calls, run_id = fresh(stock=10, sizes={"gpu-24gb": 2})
    pool.POLL_SECONDS, waits = 0.02, batch.stock_wait_minutes
    batch.stock_wait_minutes = lambda rounds: 0.001
    asked = []

    def offers(classes):
        asked.append(classes)
        if len(asked) == 1:
            raise RuntimeError("scw: 503 Service Unavailable")
        return [offer for offer in OFFERS if offer.machine_class in classes]
    cloud.offers = offers
    collector = threading.Thread(target=pool.collect, args=(run_id,))
    collector.start()
    try:
        deadline = time.time() + 5
        while len(pool.members(run_id)) < 2 and time.time() < deadline:
            time.sleep(0.02)
        assert len(pool.members(run_id)) == 2 and collector.is_alive() and pool.current(run_id) is not None
    finally:
        pool.release(run_id)
        collector.join(5)
        batch.stock_wait_minutes = waits
    assert not collector.is_alive() and len(asked) >= 2


def test_a_release_tries_every_card_and_then_says_what_failed():
    """Review (2026-10-23): one failed delete stopped the release, so the other idle cards stayed and the run's own
    release (its reservations) never ran."""
    calls, run_id = fresh(stock=10, sizes={"gpu-24gb": 3})
    grow(run_id)
    tried = []

    def delete(server_id, zone):
        tried.append(server_id)
        if len(tried) == 1:
            raise RuntimeError("Failed to detach block volume")
        return True
    cloud.delete = delete
    try:
        pool.release(run_id)
        raise AssertionError("the failed delete was not raised")
    except RuntimeError as error:
        assert "detach" in str(error)
    assert set(tried) == set(calls.rented) and pool.current(run_id) is None  # the failed one tried again as a member


def test_the_kill_switch_closes_every_open_pool_so_nothing_replaces_its_cards():
    """Review (2026-10-23): Stop everything released a pool's idle cards while its collector ran on and ordered their
    replacements."""
    calls, run_id = fresh(stock=10, sizes={"gpu-24gb": 2})
    pool.POLL_SECONDS = 0.02
    grow(run_id)
    collector = threading.Thread(target=pool.collect, args=(run_id,))
    collector.start()
    assert run_id in pool.close_all() and pool.close_all() == []
    for record in park.pool_records(run_id):  # the switch's own release of the parked cards, after the close
        park.release(record["id"], record["zone"], record["token"])
    collector.join(5)
    assert not collector.is_alive() and len(calls.rented) == 2 and sorted(calls.deleted) == sorted(calls.rented)


def test_a_stop_signal_during_the_collectors_release_lets_it_release_every_card():
    """Fault of 2026-10-24: the collector, releasing after its first SIGTERM, took a second one (its run's group stop,
    then the pool's close) and ended after 7 of 13 parked machines; the other 6 billed until deleted by hand."""
    import signal
    calls, run_id = fresh(stock=10, sizes={"gpu-24gb": 3})
    grow(run_id)
    assert len(park.pool_records(run_id)) == 3
    before = {number: signal.getsignal(number) for number in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)}
    delete = cloud.delete

    def signalled(server_id, zone):
        os.kill(os.getpid(), signal.SIGTERM)  # handled in this (the main) thread, between this card and the next
        return delete(server_id, zone)
    cloud.delete = signalled
    pool.stop_on_signals()
    try:
        batch.STOPPING.set()  # the collector's release (collect's end) runs stopping
        pool.release(run_id)
    finally:
        for number, handler in before.items():
            signal.signal(number, handler)
        batch.STOPPING.clear()
    assert park.pool_records(run_id) == [] and sorted(calls.deleted) == sorted(calls.rented), calls.deleted


PROCESSOR = "cpu-48c-96gb"
PROCESSOR_OFFERS = [provider.Offer(CARD_PRICE, 0, "cpu-type", "zone-c", CARD_PRICE, PROCESSOR, 0, "available")]


def processor_pool():
    """A pool of one processor machine, warm, and no card yet."""
    calls, run_id = fresh(stock=10, sizes={PROCESSOR: 1})
    cloud.offers = lambda classes: [offer for offer in OFFERS + PROCESSOR_OFFERS if offer.machine_class in classes]
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


def test_the_pool_holds_a_few_processor_machines_of_the_biggest_class_offered():
    found = [provider.Offer(1, 2, "t", "z", 1, "cpu-48c-96gb", 0, "shortage"),
             provider.Offer(1, 0, "t", "z", 1, "cpu-32c-64gb", 0, "available")]
    assert pool.processor_class(found) == "cpu-32c-64gb"  # the biggest in stock (no 64-core offer: no quota)
    assert pool.processor_class(found[:1]) == "cpu-48c-96gb"  # none in stock: the biggest offered, waited for
    assert pool.with_processors({"gpu-24gb": 4}, 5, found) == {"gpu-24gb": 4, "cpu-32c-64gb": pool.MOST_PROCESSORS}
    assert pool.with_processors({"gpu-24gb": 4}, 1, found) == {"gpu-24gb": 4, "cpu-32c-64gb": 1}
    assert pool.with_processors({"gpu-24gb": 4}, 0, found) == {"gpu-24gb": 4}
    assert pool.with_processors({"gpu-24gb": 4}, 2, []) == {"gpu-24gb": 4}


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
    cloud.offers = lambda classes: [offer for offer in OFFERS + PROCESSOR_OFFERS if offer.machine_class in classes]
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
    os.environ["SCORE_RUN_ID"] = run_id = f"run-{time.time_ns()}"
    pool.start(run_id, pool.sized(reserved, 10, 0), time.time() + 3600, reserved=reserved)
    cloud.offers = lambda classes: [offer for offer in OFFERS + PROCESSOR_OFFERS if offer.machine_class in classes]
    assert grow(run_id) == 1 and len(calls.rented) == 1  # the card alone
    pool.resize(run_id, 1, 1)
    assert pool.current(run_id)["sizes"] == {"gpu-24gb": 1, PROCESSOR: 1}
    assert grow(run_id) == 1 and len(calls.rented) == 2
    pool.resize(run_id, 1, 5)  # never above what it reserved
    assert pool.current(run_id)["sizes"] == {"gpu-24gb": 1, PROCESSOR: 2}
    pool.resize(run_id, 1, 0)
    assert grow(run_id) == 0 and len(calls.deleted) == 1  # the idle processor goes once no render is near
    pool.release(run_id)


def test_a_machine_is_rented_its_classes_measured_start_up_before_its_first_job():
    """The lead (owner, 2026-10-25: "cant u just do the start up earlier then when u need them again"): the median of
    its class's pool machines' minutes from order to answering, and the margin; the margin alone unmeasured."""
    def cold(machine_class, minutes):
        return {"kind": pool.KIND, "machines": [{"class": machine_class, "started": True,
                                                 "start_wait_minutes": minutes}]}
    entries = [cold("gpu-24gb", 4.0), cold("gpu-24gb", 6.0), cold("gpu-24gb", 30.0), cold(PROCESSOR, 2.0),
               {"kind": pool.HOLD, "machines": [], "euros": 1.0}]
    assert pool.lead_minutes("gpu-24gb", entries) == 6.0 + pool.LEAD_MARGIN_MINUTES
    assert pool.leads(["gpu-24gb", PROCESSOR], entries) == {False: 6.0 + pool.LEAD_MARGIN_MINUTES,
                                                            True: 2.0 + pool.LEAD_MARGIN_MINUTES}
    assert pool.leads(["gpu-48gb"], entries) == {False: pool.LEAD_MARGIN_MINUTES, True: pool.LEAD_MARGIN_MINUTES}


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


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[2] / "conftest.py"))["refuse_outside_sandbox"]()
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
    print(f"pool: {len(tests)} checks pass")
