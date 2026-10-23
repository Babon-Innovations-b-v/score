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
    return pool.fill(run_id, plan, pool.shortfall(plan, pool.tidy(run_id)), "account")


def a_run(name):
    folder = _SANDBOX / "runs" / name
    folder.mkdir(parents=True, exist_ok=True)
    return pool.Run(folder, time.time() + 3600)


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
    tries = []

    def do(machine, share, card):
        tries.append((share, machine["id"]))
        if share == "dies-always" or (share == "dies-once" and [name for name, _ in tries].count(share) == 1):
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
    assert plan["sizes"] == {"gpu-24gb": 1, "gpu-48gb": 1} and plan["disk_gb"] == 100
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


def test_a_pool_is_sized_from_the_runs_planned_card_work():
    sizes = pool.size_for([("pixal", 400, 2.0, 3.0), ("library", 200, 2.0, 1.0), ("judge", 30, 1.0, 1.0)])
    assert sum(sizes.values()) == pool.MOST_CARDS and sizes["gpu-48gb"] >= 1 and sizes["gpu-24gb"] >= 1
    assert pool.size_for([("pixal", 2, 2.0, 3.0)]) == {"gpu-24gb": 1}


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[3] / "conftest.py"))["refuse_outside_sandbox"]()
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
    print(f"pool: {len(tests)} checks pass")
