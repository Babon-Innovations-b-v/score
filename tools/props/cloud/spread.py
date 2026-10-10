"""Spread one batch of a job kind over many rented machines at once: the machines are claimed side by side across
the zones (batch.claim), each is set up as soon as it answers and then takes the batch's shares from one queue until
none is left, so a late or failed machine never holds the rest up (2026-10-08, after the provider granted quotas for
20 H100, 50 L4 and 10 L40S machines; stock is still the real limit).

    count = capacity.machines_for(units, unit_minutes, setup_minutes, capacity.slots_for(kind))
    shares = spread.Shares(jobs)
    spread.on_machines(run, account, found, count, kind, shares, prepare, do)

`prepare(machine)` sets one machine up (its host is machine["host"]); `do(machine, share, card)` works one share on
it, `card` being the card it runs on (None on a processor machine), and raises JobFailed when the share's own command
fails, which is recorded and not tried again. Anything else that goes wrong with a machine (ssh, a copy) hands its
share back for one more try on another machine and ends that machine. A machine runs capacity.runs_at_once shares on
each card at once. Every machine is armed to delete itself if this PC goes quiet, hears this PC's heartbeat each
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


# Machines rented in turn in place of one that failed while setting up (a package mirror mid-sync failed an L4's
# Blender setup, 2026-10-08).
REPLACEMENTS = 2
# What ssh exits with when the connection, not the command, failed.
SSH_LOST = 255


class JobFailed(Exception):
    """A share's own command failed on a machine that still works."""


def raise_for(returncode, what):
    """Raise for a share's command that did not succeed: ConnectionError when ssh lost the machine, JobFailed when
    the command itself failed."""
    if returncode == SSH_LOST:
        raise ConnectionError(f"the machine stopped answering during {what}")
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
        self.retried, self.failed, self.done = set(), [], []
        self.takers = 0

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

    def give_back(self, item):
        """A share a machine could not finish goes back for another machine, once; True if it went back."""
        key = repr(item)
        with self.changed:
            if key in self.retried:
                self.failed.append(item)
                return False
            self.retried.add(key)
            self.waiting.append(item)
            self.changed.notify()
            return True

    def queued(self):
        """Shares no slot is waiting for: the waiting shares less the slots waiting to take one."""
        with self.changed:
            return len(self.waiting) - self.takers


def slots(kind, machine, at_once=None):
    """The cards a machine's shares run on, one entry a share at once: runs_at_once on each card; on a processor
    machine None, `at_once` times (one unless the runner says)."""
    cards = provider.cards(machine["class"])
    if not cards:
        return [None] * (at_once or 1)
    return [card for card in range(cards) for _ in range(capacity.runs_at_once(kind, machine["class"]))]


def work_slot(machine, shares, do, card, broken):
    """Take and work shares on one slot of a machine until none is left or the machine is broken."""
    while not broken.is_set():
        share = shares.take()
        if share is None:
            return
        try:
            do(machine, share, card)
            shares.finished(share)
        except JobFailed as error:
            batch.say(f"{machine['folder'].name}: a job failed ({error})")
            shares.failed_job(share)
        except Exception as error:  # noqa: BLE001 - the share goes to another machine, this one stops
            broken.set()
            again = shares.give_back(share)
            batch.say(f"{machine['folder'].name} failed ({error}); its share "
                      f"{'goes to another machine' if again else 'failed twice and is given up'}")


@contextlib.contextmanager
def tended(run, machine):
    """A machine a runner works itself, armed to delete itself if this PC goes quiet and hearing its heartbeat while
    the block runs (its host), deleted after whatever happens."""
    import pictures

    stop = threading.Event()
    try:
        host = machine["host"]
        batch.arm_self_delete(machine["folder"], host, run.deadline + batch.WATCHDOG_GRACE_MINUTES * 60)
        threading.Thread(target=pictures.keep_beating, args=(machine["folder"], host, stop), daemon=True).start()
        yield host
    finally:
        stop.set()
        batch.delete_machine(machine)


def tend(run, machine, kind, shares, prepare, do, at_once=None):
    """One answered machine from set-up to delete: armed, beating, set up, its slots taking shares; False when it
    failed before taking any."""
    import pictures

    folder, stop, broken = machine["folder"], threading.Event(), threading.Event()
    try:
        host = machine["host"]
        batch.arm_self_delete(folder, host, run.deadline + batch.WATCHDOG_GRACE_MINUTES * 60)
        threading.Thread(target=pictures.keep_beating, args=(folder, host, stop), daemon=True).start()
        prepare(machine)
        machine["taking"] = True
        cards = slots(kind, machine, at_once)
        batch.say(f"{folder.name} ({machine['type']}, {machine['zone']}) ready after "
                  f"{(time.time() - machine['created']) / 60:.1f} min, {len(cards)} at once")
        workers = [threading.Thread(target=work_slot, args=(machine, shares, do, card, broken)) for card in cards]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join()
        return True
    except Exception as error:  # noqa: BLE001 - one machine failing must not stop the others
        batch.say(f"{folder.name} failed while setting up: {error}")
        return False
    finally:
        stop.set()
        batch.delete_machine(machine)


def one_machine(run, account, found, number, kind, shares, prepare, do, disk_gb, at_once=None):
    """Claim one machine and tend it; another in its place (REPLACEMENTS at most) when it failed while setting up
    and work is left; nothing when no offer gives one that answers or the work is gone."""
    for attempt in range(REPLACEMENTS + 1):
        if shares.queued() <= 0 and not shares.open:
            return
        machine = batch.claim(run, account, found, f"{number}{'abcdefgh'[attempt - 1] if attempt else ''}", kind,
                              disk_gb, wanted=lambda: shares.queued() > 0 or shares.open)
        if machine is None or tend(run, machine, kind, shares, prepare, do, at_once):
            return


def start_machine(run, account, found, number, kind, shares, prepare, do, disk_gb=batch.DISK_GB, at_once=None):
    """One machine claimed and tended in a thread of its own; the thread."""
    thread = threading.Thread(target=one_machine, args=(run, account, found, number, kind, shares, prepare, do,
                                                        disk_gb, at_once))
    thread.start()
    return thread


def on_machines(run, account, found, count, kind, shares, prepare, do, disk_gb=batch.DISK_GB, at_once=None):
    """Claim `count` machines side by side and let each take shares as soon as it is set up; returns when every
    machine is deleted. What was never done stays in `shares.waiting`, what failed in `shares.failed`."""
    threads = [start_machine(run, account, found, number, kind, shares, prepare, do, disk_gb, at_once)
               for number in range(1, count + 1)]
    for thread in threads:
        thread.join()
