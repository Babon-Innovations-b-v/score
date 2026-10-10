"""Park a finished machine that is billed by the started hour, for the next run of its kind, until its paid hour is
nearly up (job hours, 2026-10-10).

The processor machines are billed by the started hour, while a Blender run on one takes 9 to 33 minutes: in October
2026 they cost 1.6 to 3.2 times their hourly price for the time used, about €48 of €88. So a healthy machine whose
run is over is not deleted while its paid hour has LEAST_MINUTES or more left: its run's own files are removed, it is
written down in PARKED, and the next claim of the same kind on this PC (batch.claim) takes it instead of renting,
its set-up already done. Whatever happens, it is gone MARGIN_MINUTES before its paid hour ends and is never idle into
the next hour:

- this file's --expire process, started when the machine is parked, deletes it then unless a run has taken it;
- the machine's own watcher (self_delete.py) is re-armed with that time as its deadline, so it goes even if this PC
  dies;
- the machine's tags name the --expire process and that time, so any run's sweep leaves it alone until then and
  deletes it after (or as soon as that process is gone).

A runner opts its kind in by putting a function into CLEANUPS: the machine -> the shell command that removes its
run's own files (inputs, outputs, job files) and keeps the set-up. A kind without one is deleted as before, and so
is a machine that failed, a run stopped by a signal, and every machine billed by the minute (the cards).

A run that takes a parked machine is charged in the ledger only for what it adds past the hours already paid
(ledger.machine_row, `adopted` and `paid_minutes`); the run that parked it was charged its whole hour.
"""
import contextlib
import fcntl
import json
import math
import os
import subprocess
import sys
import time
import uuid

import batch
from provider import cloud

PARKED = batch.CLOUD / "parked"
LOCK = batch.CLOUD / "parked.lock"
# A parked machine is deleted this long before its paid hour ends: a delete takes up to a minute, and the provider's
# clock starts at the order, a few seconds before the runner's `created`.
MARGIN_MINUTES = 5
# A machine is parked, and a parked one taken, only with at least this long left before it must go.
LEAST_MINUTES = 3
# kind -> function(machine) giving the shell command that removes the run's own files from the machine.
CLEANUPS = {}


def paid_until(machine, now):
    """When the hours the machine has been billed for so far end."""
    unit = machine["unit_minutes"] * 60
    return machine["created"] + max(1, math.ceil((now - machine["created"]) / unit)) * unit


def leaves_at(machine, now):
    """When a machine parked now must be gone: MARGIN_MINUTES before its paid hour ends."""
    return paid_until(machine, now) - MARGIN_MINUTES * 60


def parkable(machine, now):
    """Whether the machine is worth parking: its run ended well, its kind cleans up, it is billed by the hour and its
    paid hour has LEAST_MINUTES or more left."""
    return (bool(machine.get("healthy")) and machine.get("kind") in CLEANUPS and machine.get("host") is not None
            and machine.get("unit_minutes", 1) > 1 and not batch.STOPPING.is_set()
            and leaves_at(machine, now) - now >= LEAST_MINUTES * 60)


@contextlib.contextmanager
def locked():
    """The parked list, held by this process alone (every runner on this PC shares it)."""
    PARKED.mkdir(parents=True, exist_ok=True)
    with LOCK.open("w") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def record_of(machine, until, token, now):
    """What the next run needs to take the machine: who it is, what it costs and has been paid, when it must go."""
    keys = ("id", "zone", "type", "class", "cards", "price", "unit_minutes", "created", "host", "kind", "disk_gb")
    return {**{key: machine.get(key) for key in keys}, "token": token, "until": until, "parked_at": now,
            "paid_minutes": (paid_until(machine, now) - machine["created"]) / 60}


def park(machine):
    """Park the machine instead of deleting it, when it is worth it; True if parked. Anything that goes wrong on the
    way leaves it to the caller's delete."""
    now = time.time()
    if not parkable(machine, now):
        return False
    until, token = leaves_at(machine, now), uuid.uuid4().hex
    folder, host = machine["folder"], machine["host"]
    try:
        batch.remote(folder, host, CLEANUPS[machine["kind"]](machine), check=True, capture_output=True, timeout=120)
        batch.arm_self_delete(folder, host, until, quiet_minutes=(until - now) / 60 + batch.QUIET_MINUTES)
        with (folder / "park.log").open("a") as log:
            expirer = subprocess.Popen([sys.executable, __file__, "--expire", machine["id"], machine["zone"], token,
                                        f"{until:.0f}"], start_new_session=True, stdout=log,
                                       stderr=subprocess.STDOUT)
        # Tagged before it is listed, so no run takes it and then has its own tags overwritten by these.
        cloud.retag(machine["id"], machine["zone"], batch.run_tags(expirer.pid, until))
        with locked():
            (PARKED / f"{machine['id']}.json").write_text(json.dumps(record_of(machine, until, token, now)))
    except Exception as error:  # noqa: BLE001 - a machine that cannot be parked is deleted as before
        batch.say(f"{folder.name} could not be parked ({error}); deleting it")
        return False
    machine["parked"] = True
    leaving = time.strftime("%H:%M", time.localtime(until))
    batch.say(f"{folder.name} parked for the next {machine['kind']} run until {leaving} (its paid hour)")
    return True


def take(kind, places, disk_gb, now):
    """The parked machine of `kind` in one of `places` ((type, zone)) with a disk of at least `disk_gb` and the most
    time left, struck off the list; None when there is none. Records past their time are struck off on the way."""
    with locked():
        found = []
        for path in PARKED.glob("*.json"):
            record = json.loads(path.read_text())
            if record["until"] - now < LEAST_MINUTES * 60:
                path.unlink()
                continue
            if (record["kind"] == kind and (record["type"], record["zone"]) in places
                    and (record.get("disk_gb") or 0) >= disk_gb):
                found.append((record["until"], path, record))
        if not found:
            return None
        _, path, record = max(found, key=lambda entry: entry[0])
        path.unlink()
        return record


def taken_machine(run, record, number, now):
    """The record as a machine of `run`, with its own watchdog."""
    folder = run.folder / f"{run.folder.name}-{number}"
    folder.mkdir(parents=True, exist_ok=True)
    machine = {key: record[key] for key in ("id", "zone", "type", "class", "cards", "price", "unit_minutes",
                                            "created", "host", "kind", "disk_gb", "paid_minutes")}
    machine.update({"folder": folder, "deleted": None, "ready": now, "adopted": now, "generating_began": None,
                    "status": {}})
    machine["watchdog"] = batch.start_watchdog(machine["id"], machine["zone"],
                                               run.deadline + batch.WATCHDOG_GRACE_MINUTES * 60, folder)
    return machine


def adopt(run, offers, number, kind, disk_gb):
    """A parked machine of `kind` for `run`, of a type and zone `offers` name, answering and tagged as the run's; None
    when there is none. One that does not answer is deleted and the next tried."""
    if kind not in CLEANUPS or not getattr(run, "deadline", None):
        return None
    places = {(offer.type, offer.zone) for offer in offers}
    while True:
        now = time.time()
        record = take(kind, places, disk_gb, now)
        if record is None:
            return None
        machine = taken_machine(run, record, number, now)
        try:
            deadline = run.deadline + batch.WATCHDOG_GRACE_MINUTES * 60
            cloud.retag(machine["id"], machine["zone"], batch.run_tags(os.getpid(), deadline))
            batch.remote(machine["folder"], machine["host"], "true", check=True, capture_output=True, timeout=60)
        except Exception as error:  # noqa: BLE001 - a parked machine that does not answer is deleted, the next tried
            batch.say(f"the parked {record['type']} in {record['zone']} did not answer ({error}); deleting it")
            batch.delete_machine(machine)
            continue
        with getattr(run, "choosing", None) or contextlib.nullcontext():
            run.machines.append(machine)
        batch.say(f"took the parked {machine['type']} in {machine['zone']} ({machine['folder'].name}), "
                  f"{(record['until'] - now) / 60:.0f} min of its paid hour left")
        return machine


def expire(server_id, zone, token, until):
    """Sleep until `until`, then delete the machine if it is still parked under `token`."""
    time.sleep(max(0.0, until - time.time()))
    path = PARKED / f"{server_id}.json"
    with locked():
        mine = path.exists() and json.loads(path.read_text()).get("token") == token
        if mine:
            path.unlink()
    if mine and cloud.delete(server_id, zone):
        print(f"{time.strftime('%H:%M:%S')} deleted parked {server_id} at the end of its paid hour", flush=True)


if __name__ == "__main__" and sys.argv[1:2] == ["--expire"]:
    expire(sys.argv[2], sys.argv[3], sys.argv[4], float(sys.argv[5]))
