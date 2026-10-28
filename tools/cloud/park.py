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

A card (billed by the minute) is parked only while a claim waits for a machine (queued: work for it; 2026-10-22, an
H100 sat parked unused after a one-model batch), and stays parked, its set-up and weights on its disk, for idle_minutes
of its kind: the median minutes a fresh card of that kind took from its order to its first job (answering and set-up)
over its last IDLE_SAMPLE runs, at most IDLE_CAP_MINUTES. Idle that long it costs what one cold start of that kind
costs, so a card nobody takes loses at most one cold start and one that is taken saves one. A claim that is waiting for a machine of
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

A run's pool card (pool.py, owner 2026-10-23) parks the same way with the pool's own rules: a healthy one goes back
to its pool whatever its kind (a kind with no clean-up only when it never ran one), listed until the pool's end, its
self-delete keeping its 15-minute quiet limit (the pool's collector beats it); it is taken only by a claim of its own
run, by class, whatever its type and zone; taking one charges its spell parked to the pool (idle_entry) and the taker
from then on. One that cannot go back is deleted and struck off the pool, which collects another.

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
import provider
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
# Every set-up mark on a machine (STALE_MARKS keeps the newest of these).
ALL_MARKS = "rm -f /root/.*-setup-*"
# kind -> function(machine) giving the shell command that removes the run's own files from the machine. They live here,
# not in the runners: a runner that sends a maker's scripts up is in its rows' code keys (score/graph/_code.py), so a
# registration there moves those rows (c3b60928). blender_cloud.py, library_bake.py, characters.py, judge.py,
# segment.py and finish_masks.py still register their own.
CLEANUPS = {
    "pixal": lambda _machine: ("pkill -f '[m]achine_run[.]py' || true; cd /root/batch && "
                               "rm -rf in out queue logs closed status.json run.log"),
    "meshparts": lambda _machine: "rm -rf /root/mp/in /root/mp/out",
    # pictures.py, both picture models: the reference photos, lists and pictures; the model and environment stay.
    "pictures": lambda _machine: "rm -rf /root/pics/refs /root/pics/out /root/pics/jobs-*.json",
    "pictures-20b": lambda _machine: "rm -rf /root/pics/refs /root/pics/out /root/pics/jobs-*.json",
    # scene.py: every room's folder and the inputs; the scripts, weights and environment stay.
    "scene": lambda _machine: "rm -rf /root/props/work/scene /root/props/inputs",
    # Kinds whose set-up writes no mark and so runs in full each time, rebuilding the shared /root/venv (fault,
    # 2026-10-23: the likeness threw its warm pool L4 away and the collector rented another): their whole folder goes
    # (a set-up that clones would fail on it) and every set-up mark, so the next kind on the card sets up again.
    "similar": lambda _machine: f"rm -rf /root/similar; {ALL_MARKS}",
    "unirig": lambda _machine: f"rm -rf /root/rig /root/UniRig; {ALL_MARKS}",
    "parts": lambda _machine: f"rm -rf /root/parts; {ALL_MARKS}",
    "closeups": lambda _machine: f"rm -rf /root/closeups; {ALL_MARKS}",
    "moss-sound": lambda _machine: f"rm -rf /root/sfx; {ALL_MARKS}",
    "unlit": lambda _machine: f"rm -rf /root/unlit; {ALL_MARKS}",
    # tools/cloud/images/prove.py (an image's proof, and every sound row's takes, score/stages/sound/takes.py): its
    # containers stopped, its store credentials and registry login gone; docker, the pulled images and the node
    # caches stay, outside /root/venv (fault, 2026-10-24: each sound row threw its warm pool card away).
    "prove": lambda _machine: ("docker ps -q | xargs -r docker kill >/dev/null 2>&1; "
                               "rm -rf /root/smoke /root/.docker/config.json"),
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
    """When a machine parked now must be gone: a pool card at its pool's end; else MARGIN_MINUTES before its paid hour
    ends; a card after its kind's idle time (at least LEAST_MINUTES while a claim of its kind waits)."""
    if machine.get("pool"):
        import pool
        return (pool.current(machine["pool"]) or {"deadline": now})["deadline"]
    if machine.get("unit_minutes", 1) > 1:
        return paid_until(machine, now) - MARGIN_MINUTES * 60
    idle = idle_minutes(machine.get("kind"))
    return now + (max(idle, LEAST_MINUTES) if waiting(machine.get("kind")) else idle) * 60


def queued():
    """Whether a claim of any kind that cleans up waits for a machine now (take lets one take another kind's)."""
    return any(waiting(kind) for kind in CLEANUPS)


def parkable(machine, now):
    """Whether the machine is worth parking: its run ended well, its kind cleans up, it has LEAST_MINUTES (a card
    CARD_LEAST_MINUTES) or more before it must go, and, for a card, a claim waits for it (queued): a card billed by
    the minute with no queued work is released (2026-10-22: an H100 sat parked unused after a one-model batch)."""
    if machine.get("pool"):
        return pool_parkable(machine, now)
    card = machine.get("unit_minutes", 1) == 1
    least = CARD_LEAST_MINUTES if card else LEAST_MINUTES
    return (bool(machine.get("healthy")) and machine.get("kind") in CLEANUPS and machine.get("host") is not None
            and not batch.STOPPING.is_set() and (not card or queued())
            and leaves_at(machine, now) - now >= least * 60)


def pool_parkable(machine, now):
    """Whether a pool card goes back to its pool: healthy, answering, its kind's run files removable (a fresh card's
    kind has none), not stopping, its pool open with CARD_LEAST_MINUTES or more before its end."""
    import pool
    return (bool(machine.get("healthy")) and machine.get("host") is not None and not batch.STOPPING.is_set()
            and (machine.get("kind") in CLEANUPS or machine.get("kind") == pool.KIND)
            and pool.current(machine["pool"]) is not None
            and leaves_at(machine, now) - now >= CARD_LEAST_MINUTES * 60)


def cleanup_of(machine):
    """The shell command that removes the machine's run files: its kind's, none for a fresh pool card."""
    return CLEANUPS[machine["kind"]](machine) if machine["kind"] in CLEANUPS else "true"


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
    record = {**{key: machine.get(key) for key in keys}, "token": token, "until": until, "parked_at": now,
              "paid_minutes": (paid_until(machine, now) - machine["created"]) / 60,
              "run": os.environ.get(capacity.RUN_ID)}
    if machine.get("pool"):  # the pool's run, and the folder its collector beats the card's heartbeat through
        record.update({"pool": machine["pool"], "run": machine["pool"], "folder": str(machine["folder"])})
    return record


def park(machine):
    """Park the machine instead of deleting it, when it is worth it; True if parked. Anything that goes wrong on the
    way leaves it to the caller's delete. A pool card parked is back in its pool (no process holds it); one not
    parked is deleted here and struck off its pool only once that delete went through, so a card mid-delete stays in
    sight of the release and the collector's tidy (review of 2026-10-24); the caller's own delete then finds it gone.
    Here, not in batch.delete_machine: the pixal and rough-model rows declare batch.py. This PC's machine
    (SCORE_CLOUD=local) is never parked: its claim ends with the caller's delete."""
    if machine.get("here"):
        return False
    parked = park_here(machine)
    if machine.get("pool"):
        import pool
        if not parked:
            cloud.delete(machine["id"], machine["zone"])
            pool.left(machine["pool"], machine["id"])
        else:
            pool.held_by(machine["pool"], machine["id"], None)
            if pool.current(machine["pool"]) is None:  # released while it was being parked: it goes now
                release(machine["id"], machine["zone"], machine["parked_token"])
                return False
    return parked


def park_here(machine):
    """park's own work: the machine cleaned, armed, given its --expire process, tagged and listed; True if parked."""
    now = time.time()
    if not parkable(machine, now):
        return False
    until, token = leaves_at(machine, now), uuid.uuid4().hex
    folder, host = machine["folder"], machine["host"]
    try:
        batch.remote(folder, host, cleanup_of(machine), check=True, capture_output=True, timeout=120)
        # A pool card's collector beats it, so it keeps the usual quiet limit; any other parked machine hears no one.
        quiet = batch.QUIET_MINUTES if machine.get("pool") else (until - now) / 60 + batch.QUIET_MINUTES
        batch.arm_self_delete(folder, host, until, quiet_minutes=quiet)
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
    machine["parked"], machine["parked_token"] = True, token
    leaving = time.strftime("%H:%M", time.localtime(until))
    why = ("its pool's end" if machine.get("pool") else
           "its paid hour" if machine["unit_minutes"] > 1 else "its kind's cold start")
    batch.say(f"{folder.name} parked for the next {machine['kind']} run until {leaving} ({why})")
    return True


def take(kind, places, disk_gb, now, pool_of=None, classes=()):
    """The parked machine in one of `places` ((type, zone)) with a disk of at least `disk_gb`, struck off the list:
    one of `kind` first, else one another kind parked (the owner, 2026-10-12: no new machine while one is idle), the
    most time left first; None when there is none. Records past their time are struck off on the way. Another kind's
    machine fits: a type the claim's offers name runs the same system image whatever the kind, its run's files were
    removed when it was parked, and the claiming kind's set-up then runs on it as on a fresh one. A pool card is taken
    only by a claim of its pool's run (`pool_of`), by its class (one of `classes`) in whatever type and zone; a render
    or bake takes the pool's processor machines before its cards (`processor_first`)."""
    with locked():
        found = []
        for path in PARKED.glob("*.json"):
            record = json.loads(path.read_text())
            if record["until"] - now < TAKE_MINUTES * 60:
                if now - record["until"] > STALE_MINUTES * 60:  # its --expire process is long gone
                    path.unlink()
                continue  # left to its --expire process, which deletes the machine with the record
            fits = (record["pool"] == pool_of and record["class"] in classes if record.get("pool")
                    else (record["type"], record["zone"]) in places)
            if fits and (record.get("disk_gb") or 0) >= disk_gb:
                found.append(((processor_first(kind, record), record["kind"] == kind, record["until"]), path, record))
        if not found:
            return None
        _, path, record = max(found, key=lambda entry: entry[0])
        path.unlink()
        return record


def processor_first(kind, record):
    """Whether a render or bake (capacity.PROCESSOR_KINDS) would take this pool record before a card: a pool's
    processor machine is faster than its L4 for these (capacity.PROCESSOR_TIMES, 2026-10-23) and never out of stock,
    so the cards are left for the kinds only a card runs."""
    return bool(record.get("pool")) and kind in capacity.PROCESSOR_KINDS and not provider.cards(record["class"])


def taken_machine(run, record, number, now):
    """The record as a machine of `run`, with its own watchdog."""
    folder = run.folder / f"{run.folder.name}-{number}"
    folder.mkdir(parents=True, exist_ok=True)
    machine = {key: record[key] for key in ("id", "zone", "type", "class", "cards", "price", "unit_minutes",
                                            "created", "host", "kind", "disk_gb", "paid_minutes")}
    machine.update({"folder": folder, "deleted": None, "ready": now, "adopted": now, "generating_began": None,
                    "status": {}})
    if record.get("pool"):  # its spell parked is the pool's (idle_entry); the taker pays from now on
        ledger.record(idle_entry(record, now))
        machine["pool"], machine["paid_minutes"] = record["pool"], (paid_until(record, now) - record["created"]) / 60
    machine["watchdog"] = batch.start_watchdog(machine["id"], machine["zone"],
                                               run.deadline + batch.WATCHDOG_GRACE_MINUTES * 60, folder)
    return machine


def adopt(run, offers, number, kind, disk_gb, classes=None):
    """A parked machine of `kind` for `run`, of a type and zone `offers` name (a pool machine: of one of `classes`,
    default the offers' own), answering and tagged as the run's; None when there is none. One that does not answer is
    deleted and the next tried. Under SCORE_CLOUD=local, this PC's machine while no other claim holds it (`here`)."""
    import pool
    if hasattr(cloud, "take"):
        return here(run, number, kind)
    pool_of = os.environ.get(capacity.RUN_ID) if pool.current() else None
    if (kind not in CLEANUPS and not pool_of) or not getattr(run, "deadline", None):
        return None
    batch.compute.require_cleared(f"a parked machine of {kind}")
    places = {(offer.type, offer.zone) for offer in offers}
    classes = set(classes or {offer.machine_class for offer in offers})
    while True:
        now = time.time()
        record = take(kind, places, disk_gb, now, pool_of, classes)
        if record is None:
            return None
        if not capacity.reserve_run_slot(len(live_of(run))):  # the run holds its cap: the record goes back
            put_back(record)
            return None
        machine = taken_machine(run, record, number, now)
        machine["kind"] = kind  # another kind's machine is this run's kind now: its clean-up and parking are this kind's
        if machine.get("pool"):
            pool.held_by(machine["pool"], machine["id"], os.getpid())
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


def here(run, number, kind):
    """This PC's machine (backends/local.py) for `run`, or None while another claim holds it, so the claim waits and
    asks again (batch.claim_rounds). Never rented, so no clearance is asked: it costs nothing. Its set-up stays from
    the last job but for the newest set-up mark (STALE_MARKS); the files a last claim of its kind left go first
    (`cleanup_of`: its container restart kills the job, not its files, so pixal's leftover `closed` ended the next
    worker at once, 2026-10-28); a kind too big for its card is refused (compute's
    Refused, naming the GB), never run into an out-of-memory; by the run's own measured need (`run.need`) when it
    has one."""
    if not getattr(run, "deadline", None):
        return None
    try:
        found = cloud.take(kind, batch.ssh_key(), getattr(run, "need", None))
    except ValueError as too_big:
        raise batch.compute.Refused(str(too_big)) from too_big
    if found is None:
        return None
    now = time.time()
    folder = run.folder / f"{run.folder.name}-{number}"
    folder.mkdir(parents=True, exist_ok=True)
    machine = {**found, "kind": kind, "created": now, "adopted": now, "ready": now, "paid_minutes": 0.0,
               "folder": folder, "deleted": None, "generating_began": None, "status": {}}
    machine["watchdog"] = batch.start_watchdog(machine["id"], machine["zone"],
                                               run.deadline + batch.WATCHDOG_GRACE_MINUTES * 60, folder)
    try:
        batch.remote(folder, machine["host"], f"{STALE_MARKS}; {cleanup_of(machine)}", check=True,
                     capture_output=True, timeout=60)
    except Exception:
        batch.delete_machine(machine)
        raise
    with getattr(run, "choosing", None) or contextlib.nullcontext():
        run.machines.append(machine)
    batch.say(f"took this PC's card ({machine['folder'].name}) for {kind}: EUR 0")
    return machine


def live_of(run):
    """The run's machines not deleted, and those it is renting now."""
    return [machine for machine in run.machines if not machine.get("deleted")] + list(getattr(run, "pending", []))


def put_back(record):
    """List a taken record as parked again."""
    with locked():
        (PARKED / f"{record['id']}.json").write_text(json.dumps(record))


def expire(server_id, zone, token, until, poll=PARKED_POLL_SECONDS):
    """Release the machine at `until` if it is still parked under `token`; end as soon as it is not (taken, or released
    by a pool's close or the kill switch): an expirer asleep to its time after that worked on in its run's frozen copy
    and held the checkout (2026-10-26: a pool card's sleeps to the pool's end, an hour after its run was stopped)."""
    while listed(server_id, token):
        left = until - time.time()
        if left <= 0:
            release(server_id, zone, token)
            return
        time.sleep(min(poll, left))


def listed(server_id, token):
    """Whether the machine is parked under `token` now."""
    path = PARKED / f"{server_id}.json"
    with locked():
        return path.exists() and json.loads(path.read_text()).get("token") == token


def pool_records(run_id):
    """The records of `run_id`'s pool cards parked now (idle in the pool)."""
    with locked():
        records = [json.loads(path.read_text()) for path in PARKED.glob("*.json")]
    return [record for record in records if record.get("pool") == run_id]


def parked_by(run_id):
    """The records of the machines `run_id` parked that are still listed."""
    with locked():
        records = [json.loads(path.read_text()) for path in PARKED.glob("*.json")]
    return [record for record in records if record.get("run") == run_id]


def outlive(run_id, poll=PARKED_POLL_SECONDS):
    """Wait until no machine `run_id` parked is listed: one another run took, or its --expire process deleted, is
    gone; one still listed at its time is released here (its --expire process is gone or late: 2026-10-20, three L4s
    of an ended run parked past their time until removed by hand), never left to the machine's own self-delete. The
    run's releaser calls it once the run has ended (score/__main__.py release_once_ended). A card of a pool closed
    goes at once: the run's own release of it was cut off (its end bounded, POOL_RELEASE_SECONDS)."""
    import pool
    while True:
        records = parked_by(run_id)
        if not records:
            return
        now = time.time()
        for record in records:
            if record["until"] <= now or (record.get("pool") and pool.current(record["pool"]) is None):
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
    if record.get("pool"):
        import pool
        pool.left(record["pool"], server_id)


def idle_entry(record, deleted):
    """The ledger's entry for a card parked until `deleted` that nobody took: its idle minutes and what they cost
    past what the run that parked it was charged."""
    minutes = (deleted - record["parked_at"]) / 60
    euros = max(0.0, ledger.cost((deleted - record["created"]) / 60, record["price"]) - record["paid_minutes"]
                * record["price"])
    row = {"type": record["type"], "zone": record["zone"], "cards": record["cards"], "started": True,
           "start_wait_minutes": 0.0, "work_minutes": 0.0, "minutes": minutes, "euros": euros, "parked_idle": True}
    entry = {"started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record["parked_at"])),
             "batch": f"parked-{record['id']}", "kind": record["kind"], "who": "park.py: a parked card nobody took",
             "machines": [row], "attempts": [], "machine_minutes": minutes, "euros": euros, "wall_minutes": minutes}
    if record.get("pool"):  # the pool's idle time, under the pool's ticket; its euros are the pool's booking (hold)
        import pool
        row["card_euros"], row["euros"] = euros, 0.0
        entry.update({"batch": f"pool-idle-{record['id']}-{record['parked_at']:.0f}", "kind": pool.KIND, "euros": 0.0,
                      "run": record["pool"], "who": "pool.py: a pool card's time idle",
                      **pool.ticket_of(record["pool"])})
    return entry


if __name__ == "__main__" and sys.argv[1:2] == ["--expire"]:
    expire(sys.argv[2], sys.argv[3], sys.argv[4], float(sys.argv[5]))
