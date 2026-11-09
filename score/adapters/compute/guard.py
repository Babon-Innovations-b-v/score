"""The guard: an environment's stop line, the owner's own money figure, checked before any paid job starts, never by killing
one halfway (owner, 2026-10-18; environment 1's stop was raised 13 times, by hand-run watchers that killed paid work
midway and read lines an agent had typed after his yes).

    line = guard.set_line(store, "world1", 680.0, "the films", by, at, baseline)   # the owner's money yes, its line
    line = guard.current(store, "world1")                                           # the newest, or None
    why = guard.refusal(line, spent, flight, forecast)                              # before a paid job starts

A line is kept in the store under `stops/<world>/<time>.json`, written once; the newest is the environment's stop. The
owner's money yes is the only writer (`python -m score.review stop <world> <euros> --reason ...` from his own
terminal), and it writes the line itself in the same step, so no decision waits on someone to copy it and no old line
outlives it. `set_line` refuses in any process an agent started, whatever store it is given, and the accept guard hook
blocks the other routes. An environment's spend counts from its first line (`baseline`: the month and the cloud bill, cloud
ledger and Google month then); a raise keeps that start.

Against the stop count, at each paid job's start (`score.adapters.compute.clearance`):

- what was spent since the environment's first line: in each month the higher of the bill's and the ledger's growth (the
  bill lags by hours), and Google's;
- everything in flight: each cleared run not yet ended, at its forecast less what its own batches already ledgered;
- the job asked for, at its high forecast.

A job that would pass the stop is refused before it starts, with one line in the owner's outbox per stop line; free
work goes on, since only paid jobs are cleared. A job once started runs to its end: the only stop halfway is a runaway,
a run still going past RUNAWAY times its high forecast minutes (at its forecast's cards, its cost grows with its time):
the sum of its batches' pre-flights once it has any (tools/cloud/preflight.py, sized on their jobs), else its
stage's measured runs, and past the latest deadline its paid work declared (preflight.declare_deadline: a cluster
run's Jobs' own deadlines, a rented machine's self-delete). A forecast is an average and does not grow with the work
(2026-11-09: light-passes@campgrounds, a big outdoor place of many lamps, was stopped twice at 7 min over twice a
3 min forecast while its render ran inside its Jobs' own deadlines); the declared deadline is what the work itself
was given, and the cluster or the machine ends it there whatever the watch does, so it bounds the money as before. Its minutes are those of its paid work, as its forecast's are (a batch's wall minutes in the
ledger): a minute counts only while a cloud runner (a script of tools/cloud) runs below the make, never while the make
works free on its own or waits for a warm pool card. `Watch` ends it by signalling the make's own child processes (the
cloud runners delete their machines on a signal).

Imported only from score.adapters.compute, outside every stage's code key, so a change here moves no row.
"""
import datetime
import os
import pathlib
import signal
import threading
import time

from score import conductor
from score.store import locked, running_under_agent, stamp_key

AREA = "stops"
OUTBOX = "owner-outbox.txt"
RUNAWAY = 2.0  # a run past this many times its forecast minutes is a runaway, the one stop halfway
WATCH_SECONDS = 60.0
NOTHING = {"bill": 0.0, "ledger": 0.0, "google": 0.0}


def current(store, world):
    """The environment's newest stop line, or None when it has none."""
    keys = sorted(store.objects.keys(f"{AREA}/{world}/"))
    return store.read(keys[-1]) if keys else None


def writing(store, world):
    """An exclusive lock on the environment's stop lines across this machine's processes, held while a line is read
    and written in one step (score.review.web.stop), so a line meant to replace one never lands over a newer one."""
    return locked(store.cache / AREA / f"{world}.lock")


def set_line(store, world, euros, reason, by, at, baseline):
    """Write the owner's stop line for one environment at `euros`, his reason with it; the record. The environment's spend counts
    from its first line's `baseline` ({month, bill, ledger, google}), this `baseline` only for a first line.
    PermissionError in a process an agent started."""
    if running_under_agent():
        raise PermissionError(f"{AREA}/{world}: only the owner sets a world's stop line, from his own terminal; an "
                              "agent's process cannot write it")
    latest = current(store, world)  # carries the first line's baseline on
    if latest is None and baseline is None:
        raise ValueError(f"{world}: a world's first stop line needs the spend it counts from")
    record = {"world": world, "euros": float(euros), "reason": reason, "by": by, "at": at,
              "baseline": latest["baseline"] if latest else baseline, "before": latest["euros"] if latest else None}
    store.write_once(f"{AREA}/{world}/{stamp_key(at)}.json", record)
    return record


def months_from(first, last):
    """Every month (YYYY-MM) from `first` to `last`, both counted."""
    found, month = [], datetime.date.fromisoformat(f"{first}-01")
    while month.strftime("%Y-%m") <= last:
        found.append(month.strftime("%Y-%m"))
        month = (month + datetime.timedelta(days=32)).replace(day=1)
    return found


def spent_parts(baseline, months):
    """{cloud, ledger, google}: the euros spent since `baseline` by book, from `months` ({month: {bill (None for a
    month whose bill is not read), ledger, google}}): cloud in each month the higher of the bill's and the ledger's
    growth, ledger the cloud ledger's growth alone (cloud less it is what the bill holds and the ledger missed), google
    Google's growth. A book's growth in a month is never below 0: a bill lowered after the baseline (credits given
    back, a started call that never billed) lowers what is owed, never the spend, so it never widens the stop's room
    (2026-11-02: credits given back on October's Google bill read EUR -838.93 of spend and Batch 1 EUR -635.25 spent,
    EUR 1300.43 left of a EUR 665.18 budget; owner's rule through the coordinator: spend is what was charged, never
    less than 0, credits only lower the bill)."""
    parts = {"cloud": 0.0, "ledger": 0.0, "google": 0.0}
    for month, books in months.items():
        start = baseline if month == baseline["month"] else NOTHING
        ledger = max(0.0, books["ledger"] - start["ledger"])
        parts["ledger"] += ledger
        parts["cloud"] += ledger if books["bill"] is None else max(ledger, books["bill"] - start["bill"])
        parts["google"] += max(0.0, books["google"] - start["google"])
    return parts


def spent_since(baseline, months):
    """The euros spent since `baseline` (spent_parts): the cloud's, the higher of bill and ledger, and Google's."""
    parts = spent_parts(baseline, months)
    return parts["cloud"] + parts["google"]


def ledgered(entries, held):
    """What a cleared run's own batches have ledgered since it was cleared."""
    ticket = f"{held['node']} {held['key']}"
    since = held["at"][:19]
    return sum(entry.get("euros", 0.0) for entry in entries
               if entry.get("ticket") == ticket and entry.get("started", "")[:19] >= since)


def in_flight(held, entries):
    """{node: euros} still to come from each cleared run not yet ended: its forecast less what its own batches have
    already ledgered (those count as spent), never below nothing."""
    return {cleared["node"]: max(0.0, cleared["euros"] - ledgered(entries, cleared)) for cleared in held.values()}


def refusal(line, spent, flight, forecast):
    """Why a job at `forecast` euros would pass the environment's stop with `spent` and `flight` ({node: euros}) counted,
    naming every part, or None when it fits. Refused outright while the batch project is the conductor's own: `spent`
    would then hold the conductor's hourly bill (score.conductor.project_refusal)."""
    clash = conductor.project_refusal()
    if clash:
        return clash
    if spent + sum(flight.values()) + forecast <= line["euros"]:
        return None
    return (f"world {line['world']}: EUR {spent:.2f} spent since its first stop line and EUR "
            f"{sum(flight.values()):.2f} in flight ({len(flight)} runs); this job's EUR {forecast:.2f} forecast would "
            f"pass the EUR {line['euros']:.2f} stop of {line['at'][:16]}. Nothing was started; the owner raises the "
            "stop with Move the stop on the cockpit's money card")


# The env1 cap (the plan of 2026-11-09, B2/B3): the owner's euros for env1 to its film, counted on the whole bill of
# every project from his start, kept in the SCORE object store so both homes and the watcher read one record. The
# watcher (tools/cloud/cap_watch) writes a reading every 5 minutes; every rent point and every cluster poll reads the
# newest. Records, each written once: caps/<name>/lines/<time>.json (the cap: euros, the stop `line`, `start`, the
# `baseline` bill lines, the November `month_cap`, `standing_per_day` and `finish`, `open`), caps/<name>/readings/
# <time>.json (counter, bill, meter, whole, or `unread` with why), caps/<name>/holds/<time>.json (a clearance's high,
# from either home), caps/<name>/stops/<time>.json (each stop the watcher made).
CAPS = "caps"
CAP = "env1"
CAP_BOOK = "SCORE_CAP_BOOK"  # a folder standing in for the object store (tests, a dry pass)
CAP_STALE_SECONDS = 15 * 60  # a reading older than this is no reading: paid work is refused (fails closed)
CAP_BUFFER = 1.10  # a start holds its high plus 10% (C7)
CAP_HOLD_HOURS = 4.0  # a clearance's hold counts this long (the ledger's BATCH_HOURS)


class FolderBook:
    """The cap's records in a folder (tests; SCORE_CAP_BOOK)."""

    def __init__(self, root):
        self.root = pathlib.Path(root)

    def keys(self, prefix):
        folder = self.root / prefix
        return sorted(f"{prefix}{path.name}" for path in folder.iterdir()) if folder.is_dir() else []

    def read(self, key):
        import json
        return json.loads((self.root / key).read_text())

    def write_once(self, key, record):
        import json
        path = self.root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x") as written:
            json.dump(record, written, indent=1)


class BucketBook:
    """The cap's records in the SCORE object store (score.store.offload's bucket), reached from both homes and the
    watcher's pod alike."""

    def __init__(self, bucket):
        self.bucket = bucket

    def keys(self, prefix):
        found, token = [], None
        while True:
            page = self.bucket.client.list_objects_v2(Bucket=self.bucket.name, Prefix=prefix,
                                                      **({"ContinuationToken": token} if token else {}))
            found += [item["Key"] for item in page.get("Contents") or []]
            token = page.get("NextContinuationToken")
            if not token:
                return sorted(found)

    def read(self, key):
        import json
        return json.loads(self.bucket.client.get_object(Bucket=self.bucket.name, Key=key)["Body"].read())

    def write_once(self, key, record):
        import json
        self.bucket.client.put_object(Bucket=self.bucket.name, Key=key, Body=json.dumps(record, indent=1).encode(),
                                      IfNoneMatch="*", ContentType="application/json")


def cap_book():
    """Where the cap's records are: the folder SCORE_CAP_BOOK names, else the SCORE object store, the cloud's bucket
    reached with its runtime key whichever backend this process rents on (this PC's included)."""
    if os.environ.get(CAP_BOOK):
        return FolderBook(os.environ[CAP_BOOK])
    import json
    from score.adapters import compute
    from score.store import offload
    compute.ledger()  # puts tools/cloud on the path
    import provider

    backend = provider.billing()
    key = json.loads(backend.secret(backend.RUNTIME_KEY_SECRET))
    return BucketBook(offload.Bucket({"endpoint": f"https://s3.{backend.REGION}.scw.cloud", "region": backend.REGION,
                                      "bucket": backend.RUN_STORE_BUCKET, "access_key": key["access_key"],
                                      "secret_key": key["secret_key"]}))


def cap_newest(book, part, name=CAP):
    """The newest record under caps/<name>/<part>/, or None."""
    keys = book.keys(f"{CAPS}/{name}/{part}/")
    return book.read(keys[-1]) if keys else None


def cap_write(book, part, record, name=CAP):
    """Write one record under caps/<name>/<part>/<its time>; the record."""
    book.write_once(f"{CAPS}/{name}/{part}/{stamp_key(record['at'])}-{os.getpid()}.json", record)
    return record


def current_cap(book, name=CAP):
    """The newest cap record, or None when none was ever set."""
    return cap_newest(book, "lines", name)


def set_cap(book, record, name=CAP):
    """Write the owner's cap (his yes, chat_decisions' "cap" kind, applied as his click); the record. PermissionError
    in a process an agent started, as a stop line (set_line)."""
    if running_under_agent():
        raise PermissionError(f"{CAPS}/{name}: only the owner sets the cap; an agent's process cannot write it")
    for field in ("euros", "line", "start", "baseline", "at", "by"):
        if record.get(field) in (None, ""):
            raise ValueError(f"a cap names its {field}")
    if not 0 < float(record["line"]) <= float(record["euros"]):
        raise ValueError(f"a cap's stop line is above EUR 0 and within its EUR {record['euros']}")
    return cap_write(book, "lines", {"name": name, "open": True, **record}, name)


def open_holds(book, now, name=CAP, hours=CAP_HOLD_HOURS):
    """The holds written within `hours` of `now` (epoch seconds), each {at, node, key, euros, home}."""
    oldest = now - hours * 3600
    found = []
    for key in book.keys(f"{CAPS}/{name}/holds/"):
        hold = book.read(key)
        if datetime.datetime.fromisoformat(hold["at"]).timestamp() >= oldest:
            found.append(hold)
    return found


def standing_left(cap, now):
    """The standing cost still to come to the cap's finish at its high daily rate (C7's forward-looking line)."""
    finish = cap.get("finish")
    if not finish or not cap.get("standing_per_day"):
        return 0.0
    days = (datetime.datetime.fromisoformat(finish).timestamp() - now) / 86400
    return max(0.0, days) * float(cap["standing_per_day"])


def cap_refusal(cap, reading, now, high=0.0, held=0.0, env1=True):
    """Why paid work may not start or go on under the cap, or None: no open cap, nothing to say. A run that is not
    env1's while the cap is open (C10); no reading, an unread one or one older than CAP_STALE_SECONDS (fails closed:
    the bill or the meter could not be read); the counter at the line, or the November cap reached; or the counter,
    the other runs' holds (`held`), this start's `high` plus 10% and the standing to the finish past the line."""
    if not cap or not cap.get("open"):
        return None
    name = cap.get("name", CAP)
    if not env1:
        return f"the {name} cap is open: no other paid run (MOTOR, benchmarks, overrides) until its film (C10)"
    if reading is None:
        return f"the {name} cap has no reading: no paid work until its watcher has read the bill"
    good = reading.get("good_at") if reading.get("unread") else reading["at"]  # an unread pass carries the last
    # good read's time and counter, None before any
    if good is None or max(now - datetime.datetime.fromisoformat(stamp).timestamp()
                           for stamp in (reading["at"], good)) > CAP_STALE_SECONDS:
        return (f"the {name} cap's bill was last read at {(good or 'never')[:16]} "
                f"({reading.get('unread') or 'no pass since'}): paid work stops until it is read again (fails closed)")
    counter, line = float(reading["counter"]), float(cap["line"])
    if cap.get("month_cap") and float(reading.get("whole") or 0.0) >= float(cap["month_cap"]):
        return (f"the month's whole bill EUR {reading['whole']:.2f} has reached the November cap of EUR "
                f"{cap['month_cap']:.2f}")
    if counter >= line:
        return f"the {name} cap: EUR {counter:.2f} counted, at its EUR {line:.2f} stop line; every paid run stops"
    ahead = counter + held + high * CAP_BUFFER + standing_left(cap, now)
    if high and ahead > line:
        return (f"the {name} cap: EUR {counter:.2f} counted, EUR {held:.2f} held by other runs, this start's high EUR "
                f"{high:.2f} plus 10% and EUR {standing_left(cap, now):.2f} standing to its finish would pass its "
                f"EUR {line:.2f} stop line")
    return None


def tell_owner(folder, tag, text):
    """One line in the owner's outbox beside the store, once per `tag` (a stop line, a run)."""
    path = pathlib.Path(folder) / OUTBOX
    with locked(path.with_name(f"{OUTBOX}.lock")):
        if path.exists() and f"[{tag}]" in path.read_text():
            return
        with path.open("a") as outbox:
            outbox.write(f"[{tag}] {text}\n")


def runaway(forecast_minutes, elapsed_minutes):
    """True for a run past RUNAWAY times its forecast minutes (never for a run with no forecast)."""
    return bool(forecast_minutes) and elapsed_minutes > RUNAWAY * forecast_minutes


def process_parents():
    """{pid: parent pid} of every process (read from /proc once)."""
    found = {}
    for stat in pathlib.Path("/proc").glob("[0-9]*/stat"):
        try:
            found[int(stat.parent.name)] = int(stat.read_text().rpartition(")")[2].split()[1])
        except (OSError, IndexError, ValueError):  # a process that ended while the table was read
            continue
    return found


def children(pid):
    """The pids of the processes `pid` started (read from /proc)."""
    return [child for child, parent in process_parents().items() if parent == pid]


def started_at(pid):
    """When process `pid` started, in clock ticks since boot (/proc); None for a process that is gone."""
    try:
        return int(pathlib.Path(f"/proc/{pid}/stat").read_text().rpartition(")")[2].split()[19])
    except (OSError, IndexError, ValueError):
        return None


def process_mark(pid):
    """A process named so it is never mistaken for a later one given the same pid: "<pid> <start ticks>"."""
    return f"{pid} {started_at(pid)}"


def alive(mark):
    """True while the process `mark` (process_mark) names is still running."""
    pid, _, ticks = mark.partition(" ")
    return pid.isdigit() and str(started_at(int(pid))) == ticks


def runs_cloud_runner(pid):
    """Whether process `pid` runs a script of tools/cloud (its command line names one)."""
    try:
        arguments = pathlib.Path(f"/proc/{pid}/cmdline").read_bytes().decode(errors="replace").split("\0")
    except OSError:
        return False
    return any("/tools/cloud/" in argument and argument.endswith(".py") for argument in arguments)


def cloud_work_below(pid=None, parents=process_parents, runner=runs_cloud_runner):
    """Whether a cloud runner runs among the processes `pid` (this one) started, theirs too: the run's paid work is
    going. 2026-11-08: settle@garage worked 15 free minutes (its grounded seed, its convex parts) before its drop's
    one cluster job and was stopped a minute into that job as a runaway over twice its 8 measured minutes, which are
    its drops' alone."""
    below = {}
    for child, parent in parents().items():
        below.setdefault(parent, []).append(child)
    tree = list(below.get(pid or os.getpid(), ()))
    while tree:
        child = tree.pop()
        if runner(child):
            return True
        tree += below.get(child, ())
    return False


def stop_children(pid=None):
    """Signal every process this one started to stop (the cloud runners delete their machines on it)."""
    for child in children(pid or os.getpid()):
        try:
            os.kill(child, signal.SIGTERM)
        except ProcessLookupError:
            pass


def no_batches():
    """No batch pre-flights: a run that keeps none."""
    return []


def no_deadlines():
    """No declared deadlines: a run whose paid work declares none."""
    return []


class Watch:
    """A cleared run's runaway watch, beside its make: every `every` seconds it compares the run's minutes with its
    high forecast's (`batches()`: its batches' pre-flights, whose high minutes add up; else `forecast_minutes`), and
    past RUNAWAY times them and past the latest deadline its paid work declared (`deadlines()`, epoch seconds read on
    `wall`) tells the owner once and calls `stop` (the make's children signalled). The time between
    two checks at which `waiting()` said the run waits for a warm pool card is left out of its minutes (benchmark of
    2026-10-23: a rough model waiting on the pool's first card was a runaway at twice its 12 measured minutes), and so
    is the time at which `paying()` said no paid work was going (cloud_work_below, as spending gives it), since the
    forecast's minutes are its paid batches' alone."""

    def __init__(self, ticket, forecast_minutes, folder, batches=no_batches, stop=stop_children, every=WATCH_SECONDS,
                 clock=time.monotonic, waiting=lambda: False, paying=lambda: True, deadlines=no_deadlines,
                 wall=time.time):
        self.ticket, self.forecast, self.folder, self.batches = ticket, forecast_minutes, folder, batches
        self.deadlines, self.wall = deadlines, wall
        self.stop, self.every, self.clock, self.waiting, self.paying = stop, every, clock, waiting, paying
        self.started, self.ended, self.ran_away = clock(), threading.Event(), False
        self.looked, self.waited = self.started, 0.0
        self.thread = threading.Thread(target=self.watch, daemon=True)

    def __enter__(self):
        if self.forecast:
            self.thread.start()
        return self

    def __exit__(self, *_):
        self.ended.set()

    def forecast_minutes(self):
        """The run's high forecast in minutes: its batches' pre-flights added up, else its stage's measured runs (also
        when the pre-flights cannot be read, say a line half written as it is read, so the watch never dies)."""
        try:
            return sum(flight["high_minutes"] for flight in self.batches()) or self.forecast
        except (OSError, ValueError, KeyError, TypeError):
            return self.forecast

    def within_deadline(self):
        """Whether the run's paid work is still inside the latest deadline it declared (False when none was declared
        or the declarations cannot be read: the forecast alone judges then, so the watch never goes blind)."""
        try:
            return self.wall() < max(self.deadlines(), default=0.0)
        except (OSError, ValueError, TypeError):
            return False

    def waits(self):
        """Whether the run waits for a warm pool card now (False when that cannot be read, so the watch never dies)."""
        try:
            return bool(self.waiting())
        except (OSError, ValueError):
            return False

    def pays(self):
        """Whether the run's paid work is going now (True when that cannot be read, so the watch never goes blind)."""
        try:
            return bool(self.paying())
        except (OSError, ValueError):
            return True

    def check(self):
        """Stop the run once it is a runaway; True when it is one."""
        now = self.clock()
        if self.waits() or not self.pays():
            self.waited += now - self.looked
        self.looked = now
        minutes, forecast = (now - self.started - self.waited) / 60, self.forecast_minutes()
        if not self.ran_away and runaway(forecast, minutes) and not self.within_deadline():
            self.ran_away = True
            tell_owner(self.folder, f"runaway {self.ticket}", f"stopped after {minutes:.0f} min, over {RUNAWAY:g} "
                       f"times its {forecast:.0f} min forecast and past every deadline its jobs declared. The cloud "
                       "runners do not keep finished work on a stop yet, so a rerun starts over")
            self.stop()
        return self.ran_away

    def watch(self):
        while not self.ended.wait(self.every):
            if self.check():
                return
