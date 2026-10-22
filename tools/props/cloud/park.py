"""Park a finished machine for the next run of its kind: one billed by the started hour until its paid hour is nearly
up (job hours, 2026-10-10), a card for a short idle time measured from the ledger (parked cards, 2026-10-11).

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

A card (billed by the minute) stays parked, its set-up and weights on its disk, for idle_minutes of its kind: the
median minutes a fresh card of that kind took from its order to its first job (answering and set-up) over its last
IDLE_SAMPLE runs, at most IDLE_CAP_MINUTES. Idle that long it costs what one cold start of that kind costs, so a card
nobody takes loses at most one cold start and one that is taken saves one. A claim that is waiting for a machine of
its kind (`wanting`, the queue of WANTED per kind that every claim of a cleared run joins while it waits) takes it
within PARKED_POLL_SECONDS; a card parked while a claim waits stays at least LEAST_MINUTES. A card nobody took is
deleted at its time by the same three means (--expire, self_delete.py, its tags), and --expire writes its idle
minutes and euros to the ledger as their own entry, so no idle minute goes uncounted.

A runner opts its kind in by putting a function into CLEANUPS: the machine -> the shell command that removes its
run's own files (inputs, outputs, job files) and keeps the set-up; its set-up script skips a machine it already set
up (a mark it writes last). A kind without one is deleted as before, and so is a machine that failed and a run
stopped by a signal.

A run that takes a parked machine is charged in the ledger only for what it adds past what was already charged
(ledger.machine_row, `adopted` and `paid_minutes`): the run that parked an hourly machine was charged its whole hour,
the one that parked a card its minutes until then. Taking one is renting: it needs a cleared run like `batch.rent`.

Under a `score run` (SCORE_RUN_ID) a parked machine's record names its run, so it stays in the run's count for the
run-wide cap (capacity.reserve_run_slot) until it is taken or gone, and taking one counts it for the taker's run first.

A `score run` that ends with machines it parked still listed outlives them (`outlive`, from its releaser process): each
one still listed at its time is released then, so a dead or late --expire process never leaves it to the machine's own
self-delete (#45: three L4s of an ended run stayed parked until removed by hand, 2026-10-20).
"""
import contextlib
import fcntl
import json
import math
import os
import statistics
import subprocess
import sys
import time
import uuid

import batch
import capacity
import ledger
from provider import cloud

PARKED = batch.CLOUD / "parked"
LOCK = batch.CLOUD / "parked.lock"
# A parked machine is deleted this long before its paid hour ends: a delete takes up to a minute, and the provider's
# clock starts at the order, a few seconds before the runner's `created`.
MARGIN_MINUTES = 5
# A machine is parked only with at least this long left before it must go (a card CARD_LEAST_MINUTES), and taken only
# with TAKE_MINUTES left: time for the run that takes it to re-arm its self-delete (seconds) before that deadline.
LEAST_MINUTES = 3
CARD_LEAST_MINUTES = 1
TAKE_MINUTES = 0.5
# A record this long past its time lost its --expire process (the machine went by its self-delete and the sweeps).
STALE_MINUTES = 10
# kind -> function(machine) giving the shell command that removes the run's own files from the machine. Pixal3D's
# (batch.py imports this file) and meshparts' (meshparts.py is a declared input of the segvigen rows, so an edit there
# re-keys them) live here; the other runners register their own.
CLEANUPS = {
    "pixal": lambda _machine: ("pkill -f '[m]achine_run[.]py' || true; cd /root/batch && "
                               "rm -rf in out queue logs closed status.json run.log"),
    "meshparts": lambda _machine: "rm -rf /root/mp/in /root/mp/out",
}
# Run on a taken machine: every set-up mark but the newest goes, so a kind whose environment a later set-up of another
# kind replaced (most share /root/venv) sets up again, while the last set-up's own mark stays good.
STALE_MARKS = "cd /root && ls -t .*-setup-* 2>/dev/null | tail -n +2 | xargs -r rm -f"
# A card's idle time: the median cold start of its kind's last IDLE_SAMPLE fresh cards, at most IDLE_CAP_MINUTES
# (short: a card waits minutes, never an hour), IDLE_DEFAULT_MINUTES for a kind never measured.
IDLE_SAMPLE = 30
IDLE_CAP_MINUTES = 10
IDLE_DEFAULT_MINUTES = 3
# The claims waiting for a machine, a folder per kind; a waiting claim looks for a parked one this often.
WANTED = batch.CLOUD / "wanted"
PARKED_POLL_SECONDS = 10


def cold_start(row):
    """A fresh card's minutes from its order to its first job: its wait to answer and its set-up (the minutes it
    spent outside its jobs where no set-up was recorded); None when the row tells neither."""
    if row.get("setup_minutes") is not None:
        return row["start_wait_minutes"] + row["setup_minutes"]
    if row.get("unit_seconds"):
        return row["minutes"] - sum(row["unit_seconds"]) / 60
    return None


def idle_minutes(kind, entries=None):
    """How long a card of `kind` stays parked: its kind's median cold start, at most IDLE_CAP_MINUTES."""
    rows = [row for entry in (ledger.entries() if entries is None else entries) if entry.get("kind") == kind
            for row in entry.get("machines", []) if row.get("cards") and row.get("started") and "adopted" not in row
            and not row.get("parked_idle") and row.get("start_wait_minutes") is not None]
    starts = [minutes for minutes in map(cold_start, rows) if minutes is not None][-IDLE_SAMPLE:]
    return min(IDLE_CAP_MINUTES, statistics.median(starts)) if starts else IDLE_DEFAULT_MINUTES


@contextlib.contextmanager
def wanting(kind):
    """A claim of `kind` waiting for a machine, on the kind's queue while the block runs."""
    if kind is None:
        yield
        return
    folder = WANTED / kind
    folder.mkdir(parents=True, exist_ok=True)
    place = folder / f"{os.getpid()}-{uuid.uuid4().hex}"
    place.write_text(os.environ.get("SCORE_SPEND_TICKET", ""))
    try:
        yield
    finally:
        place.unlink(missing_ok=True)


def waiting(kind):
    """How many claims of `kind` wait for a machine now (those of a process that is gone are struck off)."""
    count = 0
    for place in (WANTED / kind).glob("*") if kind else ():
        if batch.process_alive(int(place.name.split("-")[0])):
            count += 1
        else:
            place.unlink(missing_ok=True)
    return count


def paid_until(machine, now):
    """When the hours the machine has been billed for so far end."""
    unit = machine["unit_minutes"] * 60
    return machine["created"] + max(1, math.ceil((now - machine["created"]) / unit)) * unit


def leaves_at(machine, now):
    """When a machine parked now must be gone: MARGIN_MINUTES before its paid hour ends; a card after its kind's idle
    time (at least LEAST_MINUTES while a claim of its kind waits)."""
    if machine.get("unit_minutes", 1) > 1:
        return paid_until(machine, now) - MARGIN_MINUTES * 60
    idle = idle_minutes(machine.get("kind"))
    return now + (max(idle, LEAST_MINUTES) if waiting(machine.get("kind")) else idle) * 60


def parkable(machine, now):
    """Whether the machine is worth parking: its run ended well, its kind cleans up, and it has LEAST_MINUTES (a card
    CARD_LEAST_MINUTES) or more before it must go."""
    least = LEAST_MINUTES if machine.get("unit_minutes", 1) > 1 else CARD_LEAST_MINUTES
    return (bool(machine.get("healthy")) and machine.get("kind") in CLEANUPS and machine.get("host") is not None
            and not batch.STOPPING.is_set() and leaves_at(machine, now) - now >= least * 60)


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
            "paid_minutes": (paid_until(machine, now) - machine["created"]) / 60,
            "run": os.environ.get(capacity.RUN_ID)}


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
    why = "its paid hour" if machine["unit_minutes"] > 1 else "its kind's cold start"
    batch.say(f"{folder.name} parked for the next {machine['kind']} run until {leaving} ({why})")
    return True


def take(kind, places, disk_gb, now):
    """The parked machine in one of `places` ((type, zone)) with a disk of at least `disk_gb`, struck off the list:
    one of `kind` first, else one another kind parked (the owner, 2026-10-12: no new machine while one is idle), the
    most time left first; None when there is none. Records past their time are struck off on the way. Another kind's
    machine fits: a type the claim's offers name runs the same system image whatever the kind, its run's files were
    removed when it was parked, and the claiming kind's set-up then runs on it as on a fresh one."""
    with locked():
        found = []
        for path in PARKED.glob("*.json"):
            record = json.loads(path.read_text())
            if record["until"] - now < TAKE_MINUTES * 60:
                if now - record["until"] > STALE_MINUTES * 60:  # its --expire process is long gone
                    path.unlink()
                continue  # left to its --expire process, which deletes the machine with the record
            if (record["type"], record["zone"]) in places and (record.get("disk_gb") or 0) >= disk_gb:
                found.append(((record["kind"] == kind, record["until"]), path, record))
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
    batch.compute.require_cleared(f"a parked machine of {kind}")
    places = {(offer.type, offer.zone) for offer in offers}
    while True:
        now = time.time()
        record = take(kind, places, disk_gb, now)
        if record is None:
            return None
        if not capacity.reserve_run_slot(len(live_of(run))):  # the run holds its cap: the record goes back
            put_back(record)
            return None
        machine = taken_machine(run, record, number, now)
        machine["kind"] = kind  # another kind's machine is this run's kind now: its clean-up and parking are this kind's
        try:
            deadline = run.deadline + batch.WATCHDOG_GRACE_MINUTES * 60
            cloud.retag(machine["id"], machine["zone"], batch.run_tags(os.getpid(), deadline))
            batch.remote(machine["folder"], machine["host"], STALE_MARKS, check=True, capture_output=True,
                         timeout=60)
        except Exception as error:  # noqa: BLE001 - a parked machine that does not answer is deleted, the next tried
            batch.say(f"the parked {record['type']} in {record['zone']} did not answer ({error}); deleting it")
            batch.delete_machine(machine)
            continue
        with getattr(run, "choosing", None) or contextlib.nullcontext():
            run.machines.append(machine)
        batch.say(f"took the parked {machine['type']} in {machine['zone']} ({machine['folder'].name}), "
                  f"{(record['until'] - now) / 60:.0f} min left before it had to go")
        return machine


def live_of(run):
    """The run's machines not deleted, and those it is renting now."""
    return [machine for machine in run.machines if not machine.get("deleted")] + list(getattr(run, "pending", []))


def put_back(record):
    """List a taken record as parked again."""
    with locked():
        (PARKED / f"{record['id']}.json").write_text(json.dumps(record))


def expire(server_id, zone, token, until):
    """Sleep until `until`, then release the machine if it is still parked under `token`."""
    time.sleep(max(0.0, until - time.time()))
    release(server_id, zone, token)


def parked_by(run_id):
    """The records of the machines `run_id` parked that are still listed."""
    with locked():
        records = [json.loads(path.read_text()) for path in PARKED.glob("*.json")]
    return [record for record in records if record.get("run") == run_id]


def outlive(run_id, poll=PARKED_POLL_SECONDS):
    """Wait until no machine `run_id` parked is listed: one another run took, or its --expire process deleted, is
    gone; one still listed at its time is released here (its --expire process is gone or late: 2026-10-20, three L4s
    of an ended run parked past their time until removed by hand), never left to the machine's own self-delete. The
    run's releaser calls it once the run has ended (score/__main__.py release_once_ended)."""
    while True:
        records = parked_by(run_id)
        if not records:
            return
        now = time.time()
        for record in records:
            if record["until"] <= now:
                release(record["id"], record["zone"], record["token"])
        soonest = min(record["until"] for record in records) - now
        time.sleep(min(poll, soonest) if soonest > 0 else poll)


def release(server_id, zone, token):
    """Delete the machine and strike its record if it is still parked under `token` (a card's idle minutes into the
    ledger); nothing when another run took it or another releaser was first."""
    path = PARKED / f"{server_id}.json"
    with locked():
        record = json.loads(path.read_text()) if path.exists() else {}
        mine = record.get("token") == token
        if mine:
            path.unlink()
    if not mine:
        return
    if cloud.delete(server_id, zone):
        print(f"{time.strftime('%H:%M:%S')} deleted parked {server_id} at the end of its time", flush=True)
    if record["unit_minutes"] == 1:  # its idle minutes were billed even if its self-delete was first
        ledger.record(idle_entry(record, time.time()))


def idle_entry(record, deleted):
    """The ledger's entry for a card parked until `deleted` that nobody took: its idle minutes and what they cost
    past what the run that parked it was charged."""
    minutes = (deleted - record["parked_at"]) / 60
    euros = max(0.0, ledger.cost((deleted - record["created"]) / 60, record["price"]) - record["paid_minutes"]
                * record["price"])
    row = {"type": record["type"], "zone": record["zone"], "cards": record["cards"], "started": True,
           "start_wait_minutes": 0.0, "work_minutes": 0.0, "minutes": minutes, "euros": euros, "parked_idle": True}
    return {"started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record["parked_at"])),
            "batch": f"parked-{record['id']}", "kind": record["kind"], "who": "park.py: a parked card nobody took",
            "machines": [row], "attempts": [], "machine_minutes": minutes, "euros": euros, "wall_minutes": minutes}


if __name__ == "__main__" and sys.argv[1:2] == ["--expire"]:
    expire(sys.argv[2], sys.argv[3], sys.argv[4], float(sys.argv[5]))
