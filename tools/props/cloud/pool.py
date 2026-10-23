"""A run's warm card pool: the cards one `score run` holds from its start to its end, every cloud step of the run
taking its jobs from them (owner, 2026-10-23: "i would use like 10 gpus but warm for the entire batch"; and "the buy
run can just start as soon as one is warm, in the background u just try collecting more till 10, so its sepperate").

    sizes = pool.size_for([("pixal", 120, 1.5, 3.0), ("library", 40, 2.0, 1.0)])  # {class: cards}, from planned rows
    pool.start(run_id, sizes, deadline)   # the collector, a process of its own; returns at once
    pool.release(run_id)                  # the run's end or stop: every card deleted, the collector ended

A runner changes nothing to use it: under SCORE_RUN_ID with a pool open, `batch.claim` (every spread runner) and
`batch.rent_fleet` (Pixal3D) take a pool card (`claim`) and never rent; `batch.delete_machine` gives a healthy one
back (`park.park`: its run's files removed, listed as parked until the pool's end) and deletes a broken one, which the
collector replaces. A claim waits for the next warm card, never on stock, while the run still wants one; a class the
pool does not hold yet is added to it (`want`), so no step rents on its own.

The collector (`collect`, `pool.py --collect <run>`) rents cards beside the run until the pool holds its size: each
round the classes short, side by side across the zones (batch.claim_from), asked again after batch.stock_wait_minutes
when no stock came (3, 6, 12, 24, then 30 min, never past the pool's end). A warm card is parked for the pool at
once, so the run's first claim starts on the first card while the others are still being collected. It beats every
idle card's heartbeat each BEAT_SECONDS (an idle card's self-delete keeps its 15-minute quiet limit, so a dead PC
leaves none behind), deletes a card whose taker died, and ends when the pool is released, its end passes or the run's
process is gone; however it ends it releases the pool.

Every minute of a card is charged once, under the pool's ticket and run: its rent to its first parking (`pool-<run>`
lines, written by the collector), each spell parked (`park.idle_entry`, written when it is taken or released), and
what each taker used (the taker's own row, from when it took the card). A card is billed by the minute, so its idle
time is the run's real cost of holding it warm.
"""
import contextlib
import fcntl
import json
import os
import pathlib
import signal
import subprocess
import sys
import threading
import time

import batch
import capacity
import ledger
import provider
from provider import cloud

POOLS = batch.CLOUD / "pools"
# The most cards a pool holds (owner, 2026-10-23: "like 10 gpus"), each class also held to its quota.
MOST_CARDS = 10
# What a fresh pool card's kind is until a claim of a real kind takes it: no set-up of any kind on it.
KIND = "pool"
# How often a waiting claim looks for a warm card, and the collector for work.
POLL_SECONDS = 10
# How often the collector touches every idle card's heartbeat (self_delete.py deletes a card 15 min quiet).
BEAT_SECONDS = 60
SPEND_TICKET = "SCORE_SPEND_TICKET"
RUN_PID = "SCORE_RUN_PID"


class Run:
    """What batch.claim_from needs of the collector's renting: a folder, a deadline, its machines and failed starts."""

    def __init__(self, folder, deadline):
        self.folder = folder
        self.deadline = deadline
        self.machines, self.attempts, self.pending = [], [], []
        self.choosing = threading.Lock()
        self.dropped = set()


def folder_of(run_id):
    return POOLS / run_id


@contextlib.contextmanager
def locked(run_id):
    """The pool's files, held by this process alone."""
    folder = folder_of(run_id)
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / "lock").open("w") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield folder
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def plan_of(run_id):
    """The pool's plan ({sizes, deadline, disk_gb, ticket, run_pid, collector}), or None for a run without one."""
    if not run_id:
        return None
    path = folder_of(run_id) / "plan.json"
    return json.loads(path.read_text()) if path.exists() else None


def write_plan(run_id, plan):
    (folder_of(run_id) / "plan.json").write_text(json.dumps(plan))


def current(run_id=None):
    """The open pool of `run_id` (default: this process's run, SCORE_RUN_ID): its plan, or None when the run has no
    pool, it was released or its end has passed."""
    run_id = run_id or os.environ.get(capacity.RUN_ID)
    plan = plan_of(run_id)
    if plan is None or (folder_of(run_id) / "closed").exists() or time.time() >= plan["deadline"]:
        return None
    return plan


def opened(run_id=None):
    """Whether `run_id` (default: this process's run) opened a pool: from then on its steps never rent, the pool
    released or not."""
    return plan_of(run_id or os.environ.get(capacity.RUN_ID)) is not None


def size_for(planned):
    """{class: cards} for a run's planned card work, `planned` as (kind, units, unit_minutes, setup_minutes) a step:
    each step's cards on the first class its kind takes (capacity.order_for, less capacity.NEVER) by
    capacity.machines_for, summed by class, each class held to its quota and all to MOST_CARDS, the most-wanted class
    giving way first so every class a step needs keeps one card."""
    sizes = {}
    for kind, units, unit_minutes, setup_minutes in planned:
        machine_class = first_class(kind)
        if machine_class is None or not units:
            continue
        cards = capacity.machines_for(units, unit_minutes, setup_minutes, capacity.slots_for(kind, [machine_class]))
        sizes[machine_class] = min(sizes.get(machine_class, 0) + cards, capacity.max_machines(machine_class))
    while sum(sizes.values()) > MOST_CARDS:
        biggest = max(sizes, key=lambda machine_class: sizes[machine_class])
        if sizes[biggest] <= 1:
            break
        sizes[biggest] -= 1
    return sizes


def first_class(kind, offered=None):
    """The first card class `kind` takes in its own order, of `offered` when given; None when it takes none."""
    never = capacity.NEVER.get(kind, ())
    allowed = capacity.KINDS.get(kind, capacity.SPEED_ORDER)
    return next((machine_class for machine_class in capacity.order_for(kind)
                 if machine_class in allowed and machine_class not in never and provider.cards(machine_class)
                 and (offered is None or machine_class in offered)), None)


def start(run_id, sizes, deadline, disk_gb=batch.DISK_GB):
    """Open the run's pool of `sizes` ({class: cards}) until `deadline` and start its collector in a process of its
    own; the plan. Renting is checked as for any rent (compute.require_cleared, here and in the collector): the
    pool's cards are charged to the ticket this process holds."""
    batch.compute.require_cleared(f"a pool of {sum(sizes.values())} cards")
    with locked(run_id) as folder:
        (folder / "closed").unlink(missing_ok=True)
        plan = {"sizes": dict(sizes), "deadline": deadline, "disk_gb": disk_gb,
                "ticket": os.environ.get(SPEND_TICKET), "run_pid": int(os.environ.get(RUN_PID) or os.getpid()),
                "started": time.time()}
        write_plan(run_id, plan)
        with (folder / "collector.log").open("a") as log:
            collector = subprocess.Popen([sys.executable, __file__, "--collect", run_id], start_new_session=True,
                                         stdout=log, stderr=subprocess.STDOUT)
        plan["collector"] = collector.pid
        write_plan(run_id, plan)
    batch.say(f"pool of {', '.join(f'{count} {name}' for name, count in sizes.items())} opened for run {run_id} "
              f"until {time.strftime('%H:%M', time.localtime(deadline))}; jobs start on the first warm card")
    return plan


def want(run_id, offers, kind, disk_gb):
    """Make sure the pool collects a card a claim of `kind` from `offers` can take: the kind's first class among them
    added at one card when the pool holds none of their classes, and the disk of that one class (the class the claim
    takes, never every class) raised to `disk_gb`."""
    offered = {offer.machine_class for offer in offers}
    with locked(run_id):
        plan = plan_of(run_id)
        if plan is None:
            return
        held = {name for name in offered if plan["sizes"].get(name)}
        machine_class = first_class(kind, held or offered) or sorted(held or offered)[0]
        if held and disk_gb <= disk_of(plan, machine_class):
            return
        plan["sizes"][machine_class] = plan["sizes"].get(machine_class) or 1
        plan.setdefault("disks", {})[machine_class] = max(disk_of(plan, machine_class), disk_gb)
        write_plan(run_id, plan)


def disk_of(plan, machine_class):
    """The disk the pool asks of a card of `machine_class`: the pool's own, or the bigger one a claim of that class
    asked for (want)."""
    return plan.get("disks", {}).get(machine_class, plan["disk_gb"])


def claim(run, offers, number, kind, disk_gb, wanted=None):
    """A warm pool card for `run`'s claim of `kind` (park.adopt: another kind's card is cleaned and set up for this
    one), waited for while the run still wants one and the pool is open; None otherwise. Never rents."""
    import park

    run_id = os.environ.get(capacity.RUN_ID)
    want(run_id, offers, kind, disk_gb)
    told = False
    while not batch.STOPPING.is_set():
        machine = park.adopt(run, offers, number, kind, disk_gb)
        if machine is not None:
            return machine
        if current(run_id) is None or not batch.still_wanted(run, wanted):
            return None
        if not told:
            batch.say(f"waiting for a warm pool card for {kind}")
            told = True
        batch.STOPPING.wait(POLL_SECONDS)
    return None


def members(run_id):
    """The pool's cards alive, as the collector wrote them when each first came up (holder: the process using it)."""
    found = folder_of(run_id) / "cards"
    return [json.loads(path.read_text()) for path in sorted(found.glob("*.json"))] if found.exists() else []


def state(run_id):
    """What the cockpit shows of a run's pool: {size, warm, idle, open}, or None for a run without one."""
    import park

    plan = plan_of(run_id)
    if plan is None:
        return None
    return {"size": sum(plan["sizes"].values()), "warm": len(members(run_id)),
            "idle": len(park.pool_records(run_id)), "open": current(run_id) is not None}


def joined(run_id, machine):
    """Write a card the collector rented as one of the pool's."""
    with locked(run_id) as folder:
        (folder / "cards").mkdir(exist_ok=True)
        keys = ("id", "zone", "type", "class", "disk_gb", "created", "price")
        (folder / "cards" / f"{machine['id']}.json").write_text(json.dumps(
            {**{key: machine[key] for key in keys}, "holder": None}))


def held_by(run_id, server_id, holder):
    """Write which process uses the card now (None: back in the pool)."""
    with locked(run_id) as folder:
        path = folder / "cards" / f"{server_id}.json"
        if path.exists():
            path.write_text(json.dumps({**json.loads(path.read_text()), "holder": holder}))


def left(run_id, server_id):
    """Strike a deleted card off the pool, so the collector replaces it while the pool is open."""
    with locked(run_id) as folder:
        (folder / "cards" / f"{server_id}.json").unlink(missing_ok=True)


def shortfall(plan, alive):
    """[(class, disk_gb)] of the cards the pool lacks: each class's size less its cards alive, and one more of a class
    whose every card has a smaller disk than that class asks now (disk_of; `trim` lets an idle smaller one go once the
    bigger one is warm, so the pool keeps its size)."""
    short = []
    for machine_class, size in plan["sizes"].items():
        disk_gb = disk_of(plan, machine_class)
        mine = [card for card in alive if card["class"] == machine_class]
        missing = size - len(mine)
        if missing <= 0 and size and not any(card["disk_gb"] >= disk_gb for card in mine):
            missing = 1
        short += [(machine_class, disk_gb)] * max(0, missing)
    return short


def trim(run_id, plan, alive):
    """Release the idle cards a class holds above its size whose disk is smaller than that class asks (the ones a
    bigger disk was rented beside); the cards still alive."""
    import park

    idle = {record["id"]: record for record in park.pool_records(run_id)}
    for machine_class, size in plan["sizes"].items():
        mine = [card for card in alive if card["class"] == machine_class]
        small = sorted((card for card in mine if card["id"] in idle and card["disk_gb"] < disk_of(plan, machine_class)),
                       key=lambda card: card["disk_gb"])
        for card in small[:max(0, len(mine) - size)]:
            batch.say(f"pool: {card['id']} ({card['disk_gb']} GB) goes; a {machine_class} with a bigger disk is in its "
                      "place")
            record = idle[card["id"]]
            park.release(record["id"], record["zone"], record["token"])
            alive = [kept for kept in alive if kept["id"] != card["id"]]
    return alive


def warm(run_id, machine):
    """A card the collector rented that answers: one of the pool's, parked for the next claim (park.park through
    batch.delete_machine, which also ends its rent's watchdog), its rent to now charged to the pool."""
    machine.update({"pool": run_id, "kind": KIND, "healthy": True})
    joined(run_id, machine)
    batch.delete_machine(machine)
    ledger.record(cold_entry(run_id, machine))


def cold_entry(run_id, machine):
    """The ledger's entry for one pool card from its order to its first parking."""
    row = ledger.machine_row(machine)
    return {"started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(machine["created"])),
            "batch": f"pool-{run_id}-{machine['id']}", "kind": KIND, "run": run_id,
            "who": "pool.py: a pool card's rent and wait to answer", "machines": [row], "attempts": [],
            "machine_minutes": row["minutes"], "euros": row["euros"], "wall_minutes": row["minutes"],
            **ticket_of(run_id)}


def ticket_of(run_id):
    """The ledger fields that charge a line to the pool's ticket (the clearance its run opened it under)."""
    plan = plan_of(run_id) or {}
    return {"ticket": plan["ticket"]} if plan.get("ticket") else {}


def fill(run_id, plan, short, account):
    """Rent the cards `short` names side by side (batch.claim_from, across every zone of each class); how many came
    up warm. A start that failed or found no stock is in the ledger's line as an attempt and tried again next round."""
    renting = Run(folder_of(run_id) / "machines", plan["deadline"] + batch.WATCHDOG_GRACE_MINUTES * 60)
    renting.folder.mkdir(parents=True, exist_ok=True)
    found = cloud.offers(sorted({machine_class for machine_class, _ in short})) or []
    came = []

    def one(number, machine_class, disk_gb):
        offers = [offer for offer in found if offer.machine_class == machine_class]
        try:
            machine = batch.claim_from(renting, account, offers, f"{int(time.time())}-{number}", KIND, disk_gb)
        except batch.BootFailed as error:
            batch.say(f"pool: {error}; another is asked for next round")
            return
        if machine is not None and current(run_id) is not None:
            warm(run_id, machine)
            came.append(machine["id"])
        elif machine is not None:
            batch.delete_machine(machine)

    threads = [threading.Thread(target=one, args=(number, *wanted)) for number, wanted in enumerate(short)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    if renting.attempts:
        ledger.record({"started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "batch": f"pool-{run_id}-starts",
                       "kind": KIND, "run": run_id, "who": "pool.py: starts that gave no card", "machines": [],
                       **ledger.machines_record([], renting.attempts, time.time()), **ticket_of(run_id)})
    return len(came)


def tidy(run_id):
    """Delete the cards whose taker died (nobody tends them now) and strike them off; the cards still alive."""
    import park

    parked = {record["id"] for record in park.pool_records(run_id)}
    alive = []
    for card in members(run_id):
        holder = card.get("holder")
        if card["id"] not in parked and holder and not batch.process_alive(holder):
            batch.say(f"pool: {card['id']}'s taker (pid {holder}) is gone; deleting the card")
            cloud.delete(card["id"], card["zone"])
            left(run_id, card["id"])
            continue
        alive.append(card)
    return alive


def beat(run_id):
    """Touch every idle pool card's heartbeat, so its self-delete keeps waiting while this PC lives."""
    import park

    for record in park.pool_records(run_id):
        try:
            batch.heartbeat(pathlib.Path(record["folder"]), record["host"])
        except subprocess.CalledProcessError as error:
            batch.say(f"pool: a heartbeat of {record['id']} failed ({error.returncode}); trying again")


def run_gone(plan):
    """Whether the run's own process has ended (crashed or killed past its own release)."""
    return not batch.process_alive(plan["run_pid"])


def collect(run_id):
    """The collector: each POLL_SECONDS strike off the cards whose taker died and rent what the pool lacks, asked
    again after stock_wait_minutes while no stock comes; each BEAT_SECONDS beat the idle cards; until the pool is
    released, its end passes or its run's process is gone; then release it. A round that fails (the provider's API, a
    delete) is said and tried again, its next ask backing off as for stock: one error never ends the pool."""
    try:
        collecting = Collecting()
        while not batch.STOPPING.is_set():
            plan = current(run_id)
            if plan is None or run_gone(plan):
                break
            try:
                collect_round(run_id, plan, collecting)
            except Exception as error:  # noqa: BLE001 - the pool stays open; the next round tries again
                collecting.wait_more()
                batch.say(f"pool: a round failed ({type(error).__name__}: {error}); asking again in "
                          f"{(collecting.next_ask - time.time()) / 60:.0f} min")
            batch.STOPPING.wait(POLL_SECONDS)
    finally:
        release(run_id)


class Collecting:
    """What the collector carries from round to round: its account, the rounds that gave no card, and when it next
    asks for cards and beats the idle ones."""

    def __init__(self):
        self.account, self.rounds, self.next_ask, self.next_beat = None, 0, 0.0, 0.0

    def wait_more(self):
        """One more round that gave no card: the next ask after stock_wait_minutes (3, 6, 12, 24, then 30 min)."""
        self.rounds += 1
        self.next_ask = time.time() + batch.stock_wait_minutes(self.rounds - 1) * 60


def collect_round(run_id, plan, collecting):
    """One round of the collector: the cards whose taker died struck off, the idle ones a bigger disk replaced let go,
    what the pool lacks rented when its ask is due, the idle cards beaten when their beat is due."""
    if collecting.account is None:
        collecting.account = cloud.account()
        cloud.allow_key(collecting.account, "farm-factory-batch", batch.ssh_key())
    short = shortfall(plan, trim(run_id, plan, tidy(run_id)))
    if short and time.time() >= collecting.next_ask:
        if fill(run_id, plan, short, collecting.account):
            collecting.rounds, collecting.next_ask = 0, 0.0
        else:
            collecting.wait_more()
            batch.say(f"pool: {len(short)} card(s) short, none in stock; asking again in "
                      f"{(collecting.next_ask - time.time()) / 60:.0f} min")
    if time.time() >= collecting.next_beat:
        beat(run_id)
        collecting.next_beat = time.time() + BEAT_SECONDS


def stop_on_signals():
    """Turn a stop of the collector's process into its release (collect's own end)."""
    def leave(number, _frame):
        batch.STOPPING.set()
        raise SystemExit(f"stopped by signal {number}")
    for number in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(number, leave)


def release(run_id):
    """Close the run's pool: no claim takes a card and no card goes back to it from now on; its collector is ended,
    every idle card deleted (its idle time charged, park.release) and every card whose taker is gone deleted. A card
    a live runner holds is deleted by that runner's own delete, the pool being closed. Every card is tried; the first
    error is raised once the last was tried."""
    import park

    if not close(run_id):
        return
    errors = []
    for record in park.pool_records(run_id):
        with gathered(errors):
            park.release(record["id"], record["zone"], record["token"])
    for card in members(run_id):
        if not card.get("holder") or not batch.process_alive(card["holder"]):
            with gathered(errors):
                cloud.delete(card["id"], card["zone"])
                left(run_id, card["id"])
    if errors:
        raise errors[0]


def close(run_id):
    """Close the run's pool and end its collector, so nothing more is rented for it; False for a run without one."""
    if plan_of(run_id) is None:  # a run that never opened a pool
        return False
    with locked(run_id) as folder:
        (folder / "closed").touch()
        plan = plan_of(run_id)
    collector = plan.get("collector")
    if collector and collector != os.getpid() and batch.process_alive(collector):
        os.kill(collector, signal.SIGTERM)
    return True


def close_all():
    """Close every pool still open (the kill switch, before it releases the parked cards, so no collector orders
    their replacements); the runs whose pool it closed."""
    plans = sorted(POOLS.glob("*/plan.json")) if POOLS.exists() else []
    return [path.parent.name for path in plans
            if not (path.parent / "closed").exists() and close(path.parent.name)]


@contextlib.contextmanager
def gathered(errors):
    """Keep the block's error in `errors` (said) instead of raising it, so the next card is still tried."""
    try:
        yield
    except Exception as error:  # noqa: BLE001 - release raises the first once every card was tried
        batch.say(f"pool: releasing a card failed ({type(error).__name__}: {error})")
        errors.append(error)


if __name__ == "__main__" and sys.argv[1:2] == ["--collect"]:
    stop_on_signals()
    collect(sys.argv[2])
