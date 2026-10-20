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
the sum of its batches' pre-flights once it has any (tools/props/cloud/preflight.py, sized on their jobs), else its
stage's measured runs. `Watch` ends it by signalling the make's own child processes (the cloud runners delete their
machines on a signal).

Imported only from score.adapters.compute, outside every stage's code key, so a change here moves no row.
"""
import datetime
import os
import pathlib
import signal
import threading
import time

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


def spent_since(baseline, months):
    """The euros spent since `baseline`, from `months` ({month: {bill (None for a month whose bill is not read),
    ledger, google}}): in each month the higher of the bill's and the ledger's growth, and Google's growth."""
    total = 0.0
    for month, books in months.items():
        start = baseline if month == baseline["month"] else NOTHING
        cloud = books["ledger"] - start["ledger"]
        if books["bill"] is not None:
            cloud = max(cloud, books["bill"] - start["bill"])
        total += cloud + books["google"] - start["google"]
    return total


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
    naming every part, or None when it fits."""
    if spent + sum(flight.values()) + forecast <= line["euros"]:
        return None
    return (f"world {line['world']}: EUR {spent:.2f} spent since its first stop line and EUR "
            f"{sum(flight.values()):.2f} in flight ({len(flight)} runs); this job's EUR {forecast:.2f} forecast would "
            f"pass the EUR {line['euros']:.2f} stop of {line['at'][:16]}. Nothing was started; the owner raises the "
            "stop with Move the stop on the cockpit's money card")


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


def children(pid):
    """The pids of the processes `pid` started (read from /proc)."""
    found = []
    for stat in pathlib.Path("/proc").glob("[0-9]*/stat"):
        try:
            fields = stat.read_text().rpartition(")")[2].split()
        except OSError:  # a process that ended while the table was read
            continue
        if int(fields[1]) == pid:
            found.append(int(stat.parent.name))
    return found


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


class Watch:
    """A cleared run's runaway watch, beside its make: every `every` seconds it compares the run's minutes with its
    high forecast's (`batches()`: its batches' pre-flights, whose high minutes add up; else `forecast_minutes`), and
    past RUNAWAY times them tells the owner once and calls `stop` (the make's children signalled)."""

    def __init__(self, ticket, forecast_minutes, folder, batches=no_batches, stop=stop_children, every=WATCH_SECONDS,
                 clock=time.monotonic):
        self.ticket, self.forecast, self.folder, self.batches = ticket, forecast_minutes, folder, batches
        self.stop, self.every, self.clock = stop, every, clock
        self.started, self.ended, self.ran_away = clock(), threading.Event(), False
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

    def check(self):
        """Stop the run once it is a runaway; True when it is one."""
        minutes, forecast = (self.clock() - self.started) / 60, self.forecast_minutes()
        if not self.ran_away and runaway(forecast, minutes):
            self.ran_away = True
            tell_owner(self.folder, f"runaway {self.ticket}", f"stopped after {minutes:.0f} min, over {RUNAWAY:g} "
                       f"times its {forecast:.0f} min forecast. The cloud runners do not keep finished work on a "
                       "stop yet, so a rerun starts over")
            self.stop()
        return self.ran_away

    def watch(self):
        while not self.ended.wait(self.every):
            if self.check():
                return
