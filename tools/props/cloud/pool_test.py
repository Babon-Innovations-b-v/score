"""Checks for a run's warm card pool (pool.py), without renting anything: a run rents its pool once and claims of
every kind reuse its cards, the run's jobs start on the first warm card while the collector grows the pool, a dead
card is struck off and replaced, a dead card's job goes back on the queue once, the pool's idle time is charged to
its run, the release at the run's end (or its stop) deletes every card, and a stopped runner's card is deleted.

Run: .venv/bin/python tools/props/cloud/pool_test.py   (make tests runs it)
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
            if self.stock <= 0:
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

    def install(self):
        batch.rent = self.rent
        batch.boot = lambda machine: machine.update(host="192.0.2.1", ready=time.time()) or machine["host"]
        batch.remote = lambda folder, host, command, **_: None
        batch.arm_self_delete = lambda folder, host, deadline, quiet_minutes=0: None
        batch.heartbeat = lambda folder, host: self.beats.append(folder)
        batch.start_watchdog = lambda server_id, zone, deadline, folder: GONE_PID
        batch.compute.require_cleared = lambda what, store=None: {"node": "test"}
        cloud.retag = lambda server_id, zone, tags: None
        cloud.delete = lambda server_id, zone: self.deleted.append(server_id) or True
        cloud.offers = lambda classes: [offer for offer in OFFERS if offer.machine_class in classes]
        cloud.account = lambda: "account"
        cloud.allow_key = lambda *_: None
        batch.ssh_key = lambda: "ssh-ed25519 test"
        park.subprocess.Popen = lambda *_, **__: type("Process", (), {"pid": GONE_PID})()
        for kind in KINDS:
            park.CLEANUPS[kind] = lambda _machine: "rm -rf /root/test/out"


OFFERS = [provider.Offer(CARD_PRICE, 1, "card-type", zone, CARD_PRICE, "gpu-24gb", 0, "available")
          for zone in ("zone-a", "zone-b")]


def fresh(stock, sizes=None, run_id=None):
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
    pool.start(run_id, sizes or {"gpu-24gb": 2}, time.time() + 3600)
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


def test_the_pools_idle_time_is_charged_to_its_run():
    calls, run_id = fresh(stock=10, sizes={"gpu-24gb": 1})
    grow(run_id)
    path = next(park.PARKED.glob("*.json"))
    record = json.loads(path.read_text())
    # rented 20 min ago, parked (paid to then) 10 min ago, idle since
    record.update(created=record["created"] - 20 * 60, parked_at=record["parked_at"] - 10 * 60, paid_minutes=10.0)
    path.write_text(json.dumps(record))
    card = claimed(a_run("idle"), KINDS[0])
    entries = ledger.entries()
    idle = [entry for entry in entries if entry["batch"].startswith("pool-idle-")]
    cold = [entry for entry in entries if entry["batch"] == f"pool-{run_id}-{card['id']}"]
    assert len(idle) == 1 and idle[0]["run"] == run_id and cold and cold[0]["run"] == run_id
    assert abs(idle[0]["euros"] - 10 * CARD_PRICE) < CARD_PRICE + 1e-9  # its 10 idle minutes, to the started minute
    assert card["paid_minutes"] >= 20  # the taker pays only from when it took the card
    assert ledger.machine_row(card)["euros"] < CARD_PRICE + 1e-9


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


def test_a_class_the_pool_lacks_is_added_and_no_stock_never_empties_the_offers():
    calls, run_id = fresh(stock=0, sizes={"gpu-24gb": 1})
    big = [provider.Offer(CARD_PRICE * 2, 1, "big-type", "zone-a", CARD_PRICE * 2, "gpu-48gb", 0, "shortage")]
    pool.want(run_id, big, "judge", 100)
    plan = pool.current(run_id)
    assert plan["sizes"] == {"gpu-24gb": 1, "gpu-48gb": 1} and pool.disk_of(plan, "gpu-48gb") == 100
    assert pool.disk_of(plan, "gpu-24gb") == plan["disk_gb"] == batch.DISK_GB  # only the class the claim takes
    cloud.offers = lambda classes: [offer for offer in OFFERS + big if offer.machine_class in classes]
    assert {offer.machine_class for offer in batch.one_class_in_stock(["gpu-48gb", "gpu-24gb"])} == {"gpu-48gb"}
    pool.release(run_id)
    shortage = [offer._replace(stock_word="shortage") for offer in OFFERS]
    cloud.offers = lambda classes: [offer for offer in shortage if offer.machine_class in classes]
    assert batch.one_class_in_stock(["gpu-24gb"])  # none in stock: still offered, its claims wait for stock


def test_a_card_of_every_buy_kind_goes_back_to_the_pool_cleaned():
    """The people chain, both picture models and the scene's steps (its depth) register their clean-up, so a pool card
    they used goes back to the pool, its run's files removed, rather than being deleted and rented again."""
    import characters
    import pictures
    import scene
    calls, run_id = fresh(stock=10, sizes={"gpu-24gb": 1})
    grow(run_id)
    commands = []
    batch.remote = lambda folder, host, command, **_: commands.append(command)
    kinds = [characters.KIND, *sorted({settings["kind"] for settings in pictures.MODELS.values()}), scene.KIND]
    for kind in kinds:
        card = claimed(a_run(f"buy-{kind}"), kind)
        assert card is not None and card["pool"] == run_id, kind
        card["healthy"] = True
        batch.delete_machine(card)
        assert len(park.pool_records(run_id)) == 1, kind  # back in the pool
    assert len(kinds) == 4 and len(calls.rented) == 1 and not calls.deleted
    for removed in ("/root/make/*", "/root/pics/out", "/root/props/work/scene"):
        assert any(removed in command for command in commands), (removed, commands)
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


BIG = [provider.Offer(CARD_PRICE * 2, 1, "big-type", "zone-a", CARD_PRICE * 2, "gpu-48gb", 0, "available")]


def test_a_bigger_disk_rents_one_card_of_the_claims_class_and_lets_a_smaller_idle_one_go():
    """Review (2026-10-23): a claim's bigger disk was the whole pool's, so a card of every class was rented beside the
    pool, never let go, every replacement at the bigger disk."""
    calls, run_id = fresh(stock=10, sizes={"gpu-24gb": 2, "gpu-48gb": 1})
    cloud.offers = lambda classes: [offer for offer in OFFERS + BIG if offer.machine_class in classes]
    assert grow(run_id) == 3
    pool.want(run_id, OFFERS, KINDS[0], 200)
    plan = pool.current(run_id)
    assert pool.shortfall(plan, pool.members(run_id)) == [("gpu-24gb", 200)]  # one card, of the claim's class only
    assert grow(run_id) == 1 and len(calls.rented) == 4
    assert grow(run_id) == 0 and len(calls.deleted) == 1  # the next round lets one smaller idle card of it go
    disks = sorted((card["class"], card["disk_gb"]) for card in pool.members(run_id))
    assert disks == [("gpu-24gb", batch.DISK_GB), ("gpu-24gb", 200), ("gpu-48gb", batch.DISK_GB)]
    card = batch.claim(a_run("big-disk"), "account", OFFERS, 1, KINDS[0], 200, wanted=lambda: False)
    assert card["disk_gb"] == 200
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
    assert pool.current(run_id)["sizes"] == {PROCESSOR: 1, "gpu-24gb": 1}
    machine = claimed(a_run("render"), "blender")  # asked on a card, takes the processor machine that is free
    assert machine["class"] == PROCESSOR and machine["pool"] == run_id
    assert spread.slots("blender", machine) == [None]  # so Cycles runs on its processor (FARM_CYCLES_CPU)
    settle = [provider.Offer(CARD_PRICE, 0, "cpu-type", "zone-c", CARD_PRICE, "cpu-32c-128gb", 0, "available")]
    # asked on processors alone: its own class and the pool's processors no smaller in cores and memory
    assert pool.takes("blender", settle) == {"cpu-32c-128gb", "cpu-48c-192gb", "cpu-64c-128gb", "cpu-64c-256gb"}
    checks = [provider.Offer(CARD_PRICE, 0, "cpu-type", "zone-c", CARD_PRICE, "cpu-16c-64gb", 0, "available")]
    assert PROCESSOR in pool.takes("blender", checks) and "cpu-16c-64gb" in pool.takes("blender", checks)
    assert pool.takes("library", OFFERS) == {"gpu-24gb", *pool.capacity.PROCESSORS}
    assert pool.takes("judge", OFFERS) == {"gpu-24gb"}
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
    """A render measured on cards may land on the pool's processor machine (capacity.PROCESSOR_SLOWER times longer):
    the runaway watch, at twice its high minutes, never stops it for that."""
    import preflight
    entries = [ledger_line(stage, kind, n) for stage, kind in (("look", "blender"), ("model", "pixal")) for n in range(3)]
    assert pool.processor_able("look", entries) and not pool.processor_able("model", entries)
    assert not pool.processor_able("unbought", entries)
    calls, run_id = fresh(stock=10, sizes={"gpu-24gb": 1})
    card_only = preflight.node_run(entries, "look")["high_minutes"]
    pool.release(run_id)
    calls, run_id = processor_pool()
    assert preflight.node_run(entries, "look")["high_minutes"] == card_only * pool.capacity.PROCESSOR_SLOWER
    assert preflight.node_run(entries, "model")["high_minutes"] == card_only  # a card kind keeps its own
    pool.release(run_id)


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[3] / "conftest.py"))["refuse_outside_sandbox"]()
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
    print(f"pool: {len(tests)} checks pass")
