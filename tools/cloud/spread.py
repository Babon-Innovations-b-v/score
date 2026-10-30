"""Spread one batch of a job kind over many rented machines at once: the machines are claimed side by side across
the zones (batch.claim), each is set up as soon as it answers and then takes the batch's shares from one queue until
none is left, so a late or failed machine never holds the rest up (2026-10-08, after the provider granted quotas for
20 H100, 50 L4 and 10 L40S machines; stock is still the real limit).

    count = capacity.machines_for(units, unit_minutes, setup_minutes, capacity.slots_for(kind))
    shares = spread.Shares(jobs)
    spread.on_machines(run, account, found, count, kind, shares, prepare, do)

`prepare(machine)` sets one machine up (its host is machine["host"]); `do(machine, share, card)` works one share on
it, `card` being the card it runs on (None on a processor machine), and raises JobFailed when the share's own command
fails. Every share runs once, on one machine (a batch, CONTEXT.md, owner 2026-10-20): a share whose command failed,
or whose machine broke under it (ssh, a copy), is a gap in `shares.failed`, never handed to another machine, and a
broken machine takes no more; a machine that fails while setting up ends with no machine rented in its place, its
shares left to the others or in `shares.waiting` as gaps. Under a run's card pool (pool.py, owner 2026-10-23) a share
whose pool card died (stopped answering, batch.answers) goes back on the queue once (`Shares.again`) and the slot takes
the pool's next card while shares wait; a second death makes it a gap. A share that failed on a pool card that still
answers is a gap and the card works on; a pool card that failed in set-up is followed by one more, never a third. A machine runs capacity.runs_at_once shares on
each card at once; a claim on this PC's shared machine one a turn it holds, each turn let go when its slot has no
share left (backends/local.py SHARED). Every machine is armed to delete itself if this PC goes quiet, hears this PC's heartbeat each
minute, and is deleted when it has no more work; the run's ledger rows are the runner's (run.machines and
run.attempts, as for one machine).
"""
import collections
import contextlib
import threading
import time

import batch
import capacity
import provider


# What ssh exits with when the connection, not the command, failed.
SSH_LOST = 255


class JobFailed(Exception):
    """A share's own command failed on a machine that still works."""


class MemoryKilled(JobFailed):
    """A share's command killed by signal 9 (the machine's memory cap): a fault of the run, not of the share's result,
    so its share goes back on the queue once (work_slot)."""


class CardLost(JobFailed):
    """A share's command whose card would not open (the driver's context lost: env1's settle@airlock, 2026-10-30,
    "CUDA error 999" beside a full card, the card fine again a minute later): a fault of the machine, not of the
    share's result, so its share goes back on the queue once (work_slot)."""


KILLED = 128 + 9  # a shell's exit for a command killed by signal 9


def raise_for(returncode, what, killed=False, card_lost=False):
    """Raise for a share's command that did not succeed: ConnectionError when ssh lost the machine, MemoryKilled when
    it (or, `killed`, a step inside it) was killed by signal 9, CardLost when its card would not open (`card_lost`),
    JobFailed when the command itself failed."""
    if returncode == SSH_LOST:
        raise ConnectionError(f"the machine stopped answering during {what}")
    if returncode and (returncode == KILLED or killed):
        raise MemoryKilled(f"{what} was killed by signal 9 (exit {returncode})")
    if returncode and card_lost:
        raise CardLost(f"{what}: its card would not open (exit {returncode})")
    if returncode:
        raise JobFailed(f"{what} exited with {returncode}")


class Shares:
    """The batch's work, handed out one share at a time. A closed queue (a batch) is empty once taken; an open one
    (a keeper, blender_cloud --keep) waits for more until it is closed or a machine has waited `idle` seconds."""

    def __init__(self, items=(), deadline=None, open_queue=False, idle=0.0):
        self.waiting = collections.deque(items)
        self.deadline = deadline
        self.open = open_queue
        self.idle = idle
        self.changed = threading.Condition()
        self.failed, self.done = [], []
        self.takers = 0
        self.put_back = []

    def take(self):
        """The next share, or None when there is no more (or the deadline has passed)."""
        with self.changed:
            began = time.time()
            self.takers += 1
            try:
                while not self.waiting and self.open and time.time() - began < self.idle:
                    self.changed.wait(min(5.0, self.idle))
                if not self.waiting or (self.deadline and time.time() > self.deadline):
                    return None
                return self.waiting.popleft()
            finally:
                self.takers -= 1

    def put(self, item):
        with self.changed:
            self.waiting.append(item)
            self.changed.notify()

    def again(self, item):
        """Put a share whose pool card died back on the queue, once; False when it was put back before."""
        with self.changed:
            if any(earlier is item for earlier in self.put_back):
                return False
            self.put_back.append(item)
            self.waiting.append(item)
            self.changed.notify()
            return True

    def close(self):
        with self.changed:
            self.open = False
            self.changed.notify_all()

    def finished(self, item):
        with self.changed:
            self.done.append(item)

    def failed_job(self, item):
        with self.changed:
            self.failed.append(item)

    def queued(self):
        """Shares no slot is waiting for: the waiting shares less the slots waiting to take one."""
        with self.changed:
            return len(self.waiting) - self.takers


def slots(kind, machine, at_once=None):
    """The cards a machine's shares run on, one entry a share at once: runs_at_once on each card; on a processor
    machine None, `at_once` times (one unless the runner says). A claim on a shared machine (this PC's, its
    `turns`: backends/local.py SHARED) runs one share a turn it holds, on its first card."""
    cards = provider.cards(machine["class"])
    if machine.get("turns"):
        return [0 if cards else None] * machine["turns"]
    if not cards:
        return [None] * (at_once or 1)
    return [card for card in range(cards) for _ in range(capacity.runs_at_once(kind, machine["class"]))]


def work_slot(machine, shares, do, card, broken):
    """Take and work shares on one slot of a machine until none is left or the machine is broken; on a shared
    machine (its `turns`) until another process waits for it alone, its shares then kept for the claim's next turn
    (env1, 2026-10-29: straight-masks@lab waited 20 min while base's bake kept taking all three turns)."""
    while not broken.is_set():
        if machine.get("turns") and provider.cloud.wanted_elsewhere():
            machine["yielded"] = True
            return
        share = shares.take()
        if share is None:
            return
        try:
            do(machine, share, card)
            shares.finished(share)
        except (MemoryKilled, CardLost) as error:  # the machine's fault, not the share's: run again once, then a gap
            if shares.again(share):
                batch.say(f"{machine['folder'].name}: a job was cut off ({error}); it goes back on the queue")
                continue
            batch.say(f"{machine['folder'].name}: a job was cut off again ({error}); its share is a gap")
            shares.failed_job(share)
        except JobFailed as error:
            batch.say(f"{machine['folder'].name}: a job failed ({error})")
            shares.failed_job(share)
        except Exception as error:  # noqa: BLE001 - the share is a gap (a dead pool card's goes back once)
            if machine.get("pool") and batch.answers(machine):  # the card is fine: the fault is the share's own
                batch.say(f"{machine['folder'].name}: a job failed ({error}); the card answers, so it is a gap")
                shares.failed_job(share)
                continue
            broken.set()
            if machine.get("pool") and shares.again(share):
                batch.say(f"{machine['folder'].name} failed ({error}); its share goes back on the queue")
                continue
            shares.failed_job(share)
            batch.say(f"{machine['folder'].name} failed ({error}); its share is a gap")


def work_turn(machine, shares, do, card, broken):
    """work_slot, then the slot's turn on a shared machine let go (backends/local.py let_go_turn), so another claim's
    job takes it as soon as this claim has no share left for it, not when its last share ends."""
    try:
        work_slot(machine, shares, do, card, broken)
    finally:
        if machine.get("turns"):
            provider.cloud.let_go_turn(machine["id"])


@contextlib.contextmanager
def tended(run, machine):
    """A machine a runner works itself, armed to delete itself if this PC goes quiet and hearing its heartbeat while
    the block runs (its host), deleted after whatever happens. Its jobs run one at a time, so a claim on a shared
    machine keeps one of its turns and lets the others go."""
    import pictures

    stop = threading.Event()
    try:
        for _ in range(machine.get("turns", 1) - 1):
            provider.cloud.let_go_turn(machine["id"])
        host = machine["host"]
        batch.arm_self_delete(machine["folder"], host, run.deadline + batch.WATCHDOG_GRACE_MINUTES * 60)
        threading.Thread(target=pictures.keep_beating, args=(machine["folder"], host, stop), daemon=True).start()
        yield host
        machine["healthy"] = True  # the block ended well: the machine may be parked (park.py)
    finally:
        stop.set()
        batch.delete_machine(machine)


def tend(run, machine, kind, shares, prepare, do, at_once=None):
    """One answered machine from set-up to delete: armed, beating, set up, its slots taking shares. Whether it was
    set up."""
    import pictures

    folder, stop, broken = machine["folder"], threading.Event(), threading.Event()
    ready = False
    try:
        host = machine["host"]
        batch.arm_self_delete(folder, host, run.deadline + batch.WATCHDOG_GRACE_MINUTES * 60)
        threading.Thread(target=pictures.keep_beating, args=(folder, host, stop), daemon=True).start()
        prepare(machine)
        machine["set_up"] = time.time()  # the ledger's setup_minutes, which park.idle_minutes measures
        machine["taking"] = ready = True
        cards = slots(kind, machine, at_once)
        batch.say(f"{folder.name} ({machine['type']}, {machine['zone']}) ready after "
                  f"{(time.time() - (machine.get('adopted') or machine['created'])) / 60:.1f} min, {len(cards)} at once")
        workers = [threading.Thread(target=work_turn, args=(machine, shares, do, card, broken)) for card in cards]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join()
        machine["healthy"] = not broken.is_set()  # may be parked for the next run of its kind (park.py)
    except Exception as error:  # noqa: BLE001 - one machine failing must not stop the others
        batch.say(f"{folder.name} failed while setting up: {error}")
    finally:
        stop.set()
        batch.delete_machine(machine)
    return ready


def one_machine(run, account, found, number, kind, shares, prepare, do, disk_gb, at_once=None):
    """Claim one machine and tend it, once: none in its place when it fails; nothing when no offer gives one that
    answers or the work is gone. A pool card is followed by the pool's next while shares wait (one put back from a
    card that died); a pool card that failed in set-up is followed by one other card, never a third: a set-up that
    fails twice would fail on every card (fault, 2026-10-25: a parked card that answered failed blender's set-up and
    the slot gave up while other cards stood ready)."""
    if shares.queued() <= 0 and not shares.open:
        return
    setup_deaths = 0
    while True:
        began = time.time()
        machine = batch.claim(run, account, found, number, kind, disk_gb,
                              wanted=lambda: shares.queued() > 0 or shares.open)
        if this_pc_waited(run, shares, time.time() - began) and machine is None and \
                (shares.queued() > 0 or shares.open) and not batch.STOPPING.is_set():
            continue
        if machine is None:
            return
        if shares.deadline and machine.get("pool"):  # the time waited on the pool is not the work's (pool.paused)
            shares.deadline = max(shares.deadline, run.deadline)
        if not tend(run, machine, kind, shares, prepare, do, at_once):
            setup_deaths += 1
            if setup_deaths > 1:
                batch.say(f"{machine['folder'].name}: {kind}'s set-up failed on two cards; this slot takes no other")
                return
            batch.say(f"{machine['folder'].name}: {kind}'s set-up failed; this slot takes another card")
        if not (machine.get("pool") or machine.get("yielded")) or shares.queued() <= 0:
            return


# A claim on this PC's one machine that waited at least this long waited for the run's own jobs on it.
THIS_PC_WAIT_SECONDS = 5


def this_pc_waited(run, shares, waited):
    """On this PC's machine (SCORE_CLOUD=local: one machine, one claim at a time) the time a claim waited is the
    run's other jobs', never a shortage's and never the work's: the run's and the shares' deadlines move on by it,
    as a warm pool's wait does (pool.paused). True when it waited THIS_PC_WAIT_SECONDS or more, so a claim that ran
    out of deadline while waiting asks again (env1, 2026-10-28: a dozen bakes queued behind each other ran out of
    their 4 h at the same minute, "no machine could be rented")."""
    if provider.cloud.NAME != "local":
        return False
    run.deadline += waited
    if shares.deadline:
        shares.deadline += waited
    return waited >= THIS_PC_WAIT_SECONDS


def start_machine(run, account, found, number, kind, shares, prepare, do, disk_gb=batch.DISK_GB, at_once=None):
    """One machine claimed and tended in a thread of its own; the thread."""
    thread = threading.Thread(target=one_machine, args=(run, account, found, number, kind, shares, prepare, do,
                                                        disk_gb, at_once))
    thread.start()
    return thread


def on_machines(run, account, found, count, kind, shares, prepare, do, disk_gb=batch.DISK_GB, at_once=None):
    """Claim `count` machines side by side and let each take shares as soon as it is set up; returns when every
    machine is deleted. What was never done stays in `shares.waiting`, what failed in `shares.failed`: both gaps."""
    threads = [start_machine(run, account, found, number, kind, shares, prepare, do, disk_gb, at_once)
               for number in range(1, count + 1)]
    for thread in threads:
        thread.join()
