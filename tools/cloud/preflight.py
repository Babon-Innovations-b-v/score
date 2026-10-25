"""Pre-flight for paid work: card counts, minutes and euros from measured per-unit numbers in the cloud ledger, never
from an agent's guess (owner, 2026-10-18: no agent picks card counts; environment 1's films were sized by hand and one ran
EUR 16 on 8 cards against a EUR 0.7 estimate).

    numbers = preflight.measured(ledger.entries(), "demo-film")   # None until MEASURED_MACHINES machines worked
    flight = preflight.batch(8, numbers, cap=20)                   # {cards, minutes, euros, high_minutes, high_euros}
    run = preflight.node_run(ledger.entries(), "demo-film")       # a node's whole run: likely and high euros, minutes
    cards = preflight.run_cards(ledger.entries(), "demo-film", 20)  # the cards a whole run of it is sized on

A batch's numbers are its stage's own (the ledger line's `ticket`, "<stage>@<place> <key>", names the node that paid
for it), from every machine that worked a job for that stage: the seconds a job took (`unit_seconds`, the median and
the HIGH quantile), the set-up a fresh card took from order to its first job (`start_wait_minutes` + `setup_minutes`,
the median; a card taken parked had none) and the euros a card-minute cost (every euro over every card-minute those
machines were held). The card count is the runner's rule (capacity.machines_for's: each card works about as long as
its set-up takes, or one job's time when a job is longer, never more cards than jobs, nor than the run's cap), worked
out on those numbers. A unit is one job of the stage as its runner splits them: the ledger names jobs, not frames.

Under a runner's ticket (SCORE_SPEND_TICKET) `for_ticket` is what capacity.machines_for asks first, and each batch's
pre-flight is kept beside the store (`forecasts/<node>/<key>.jsonl`), where the runaway watch reads it. A stage with
too few measured machines keeps its runner's own estimate, said as unmeasured.

Imported only from the renting code (capacity.py) and the runner's clearance (score.adapters.compute), both outside
every stage's code key, so a change here moves no row.
"""
import json
import math
import os
import pathlib
import statistics
import threading
import time

TICKET = "SCORE_SPEND_TICKET"
STORE = "SCORE_SPEND_STORE"
MEASURED_MACHINES = 3  # machines that worked a stage's jobs before its numbers count as measured
MEASURED_RUNS = 3  # paid runs of a stage before its run forecast counts as measured
HIGH = 0.9  # the high forecast's quantile
# How long a waiting mark counts after its last touch (a waiting claim touches it each pool.POLL_SECONDS).
WAIT_FRESH_SECONDS = 120


def stage_of(ticket):
    """The stage a ticket names ("demo-film@garage <key>": demo-film), or None for no ticket."""
    if not ticket:
        return None
    return ticket.split()[0].partition("@")[0]


def stage_entries(entries, stage):
    """The ledger lines paid under a ticket of `stage`."""
    return [entry for entry in entries if stage_of(entry.get("ticket")) == stage]


def quantile(values, share):
    """The `share` quantile of `values` (inclusive), the value itself for one."""
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    return statistics.quantiles(ordered, n=100, method="inclusive")[round(share * 100) - 1]


def worked_machines(entries):
    """Every machine row of these lines that ran at least one job (a card parked and never taken ran none)."""
    return [row for entry in entries for row in entry.get("machines", ())
            if row.get("unit_seconds") and not row.get("parked_idle")]


def setup_minutes(machines):
    """The median minutes a fresh card took from its order to its first job, set-up included (0 with none fresh)."""
    fresh = [row.get("start_wait_minutes", 0.0) + row.get("setup_minutes", 0.0) for row in machines
             if not row.get("adopted")]
    return statistics.median(fresh) if fresh else 0.0


def euros_per_card_minute(machines):
    """Every euro the machines cost over every card-minute they were held (a pool machine's booked by its pool)."""
    card_minutes = sum(row["minutes"] * max(1, row.get("cards") or 1) for row in machines)
    return sum(row["euros"] + row.get("card_euros", 0.0) for row in machines) / card_minutes if card_minutes else 0.0


def batch_kinds(entries):
    """The kinds of batch (blender, pixal, ...) whose machines worked in these lines."""
    return {entry.get("kind") for entry in entries if worked_machines([entry])}


def measured(entries, stage):
    """A stage's measured per-unit numbers from the ledger lines, or None with fewer than MEASURED_MACHINES machines
    that worked its jobs, or when its batches were of more than one kind (the renting code is not told which kind a
    batch is, so one kind's numbers could size another's): {stage, kind, machines, jobs, job_seconds,
    high_job_seconds, setup_minutes, euros_per_card_minute}."""
    lines = stage_entries(entries, stage)
    machines, kinds = worked_machines(lines), batch_kinds(lines)
    if len(machines) < MEASURED_MACHINES or len(kinds) != 1:
        return None
    jobs = [seconds for row in machines for seconds in row["unit_seconds"]]
    return {"stage": stage, "kind": kinds.pop(), "machines": len(machines), "jobs": len(jobs), "job_seconds": statistics.median(jobs),
            "high_job_seconds": quantile(jobs, HIGH), "setup_minutes": setup_minutes(machines),
            "euros_per_card_minute": euros_per_card_minute(machines)}


def cards_for(jobs, numbers, cap, slots=1):
    """The card count for `jobs` jobs on the measured numbers, a card running `slots` at once: enough that each card
    works about as long as its set-up takes (one job's time when a job is longer), never more than the jobs need nor
    than `cap`."""
    if jobs <= 0:
        return 1
    job_minutes = numbers["job_seconds"] / 60
    span = max(numbers["setup_minutes"], job_minutes)
    wanted = math.ceil(jobs * job_minutes / (slots * span))
    return max(1, min(wanted, math.ceil(jobs / slots), cap))


def minutes_for(jobs, cards, job_seconds, set_up, slots=1):
    """How long `cards` cards are held for `jobs` jobs of `job_seconds` each: the set-up, then each card's share."""
    return set_up + math.ceil(jobs / (cards * slots)) * job_seconds / 60


def batch(jobs, numbers, cap, slots=1):
    """A batch's pre-flight on measured numbers: {cards, minutes, euros, high_minutes, high_euros, measured}."""
    cards = cards_for(jobs, numbers, cap, slots)
    minutes = minutes_for(jobs, cards, numbers["job_seconds"], numbers["setup_minutes"], slots)
    high = minutes_for(jobs, cards, numbers["high_job_seconds"], numbers["setup_minutes"], slots)
    rate = numbers["euros_per_card_minute"] * cards
    return {"jobs": jobs, "cards": cards, "minutes": round(minutes, 2), "euros": round(minutes * rate, 4),
            "high_minutes": round(high, 2), "high_euros": round(high * rate, 4), "measured": numbers}


def batch_minutes(entry):
    """The minutes a ledger line's batch took end to end; 0 for a line that is a charge, not a batch (a machine's
    disk and address, a parked card's idle time)."""
    if entry.get("kind") == "disk-and-address" or entry.get("batch", "").startswith("parked-"):
        return 0.0
    return entry.get("wall_minutes", 0.0)


def run_costs(entries):
    """{ticket: (euros, minutes)} of each paid run in these lines: every euro it paid (machines, disks, a parked
    card's idle) and the minutes its batches took."""
    found = {}
    for entry in entries:
        euros, minutes = found.get(entry["ticket"], (0.0, 0.0))
        pooled = sum(row.get("card_euros", 0.0) for row in entry.get("machines", ()))  # its pool's booking
        found[entry["ticket"]] = (euros + entry.get("euros", 0.0) + pooled, minutes + batch_minutes(entry))
    return found


def processor_margin(kinds):
    """How many times longer a batch of `kinds` may run under this process's warm pool: for renders and bakes
    (capacity.PROCESSOR_KINDS) the slowest of the pool's processor classes they may land on (capacity.processor_times,
    measured or the unmeasured three times), never under the card's 1; else 1. Its
    high minutes, at twice which the runaway watch stops a run, so hold whichever machine a job takes. Its euros need
    none: a pool machine's every minute is in the pool's own clearance at its class's dearest price (holding_euros)."""
    import capacity
    import pool
    import provider

    plan = pool.current()
    if not plan or not kinds or not set(kinds) <= set(capacity.PROCESSOR_KINDS):
        return 1
    # reserved: the processor machines the pool may be raised to while the batch runs (pool.resize)
    held = [name for name, count in plan.get("reserved", plan["sizes"]).items() if count and not provider.cards(name)]
    return max([1] + [capacity.processor_times(name) for name in held])


def node_run(entries, stage):
    """A paid node's whole run from its stage's measured runs ({euros, high_euros, minutes, high_minutes, runs}), or
    None with fewer than MEASURED_RUNS of them; its high minutes stretched by processor_margin."""
    lines = stage_entries(entries, stage)
    runs = list(run_costs(lines).values())
    if len(runs) < MEASURED_RUNS:
        return None
    euros, minutes = [euros for euros, _ in runs], [minutes for _, minutes in runs]
    return {"stage": stage, "runs": len(runs), "euros": statistics.median(euros), "high_euros": quantile(euros, HIGH),
            "minutes": statistics.median(minutes),
            "high_minutes": quantile(minutes, HIGH) * processor_margin(batch_kinds(lines))}


def run_jobs(entries, stage):
    """The median jobs one paid run of `stage` worked (its worked machines' jobs added up per ticket), or None with
    fewer than MEASURED_RUNS runs that worked any."""
    found = {}
    for entry in stage_entries(entries, stage):
        jobs = sum(len(row["unit_seconds"]) for row in worked_machines([entry]))
        if jobs:
            found[entry["ticket"]] = found.get(entry["ticket"], 0) + jobs
    return statistics.median(found.values()) if len(found) >= MEASURED_RUNS else None


def run_cards(entries, stage, cap, slots=1):
    """The cards a whole run of `stage` is sized on: the card rule (cards_for) for its median jobs a run, on its
    measured numbers; None while either is unmeasured."""
    numbers, jobs = measured(entries, stage), run_jobs(entries, stage)
    if numbers is None or jobs is None:
        return None
    return cards_for(math.ceil(jobs), numbers, cap, slots)


def forecasts_folder():
    """Where batch pre-flights are kept: beside the store the running ticket's clearance is in."""
    store = os.environ.get(STORE) or str(pathlib.Path(os.environ.get(
        "PROPS_HOME", pathlib.Path.home() / ".farm-factory-props")) / "store")
    return pathlib.Path(store) / "forecasts"


def keep(ticket, flight):
    """Add one batch's pre-flight to its run's file beside the store; the file."""
    node, key = ticket.split()
    path = forecasts_folder() / node / f"{key}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as kept:
        kept.write(json.dumps({**flight, "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}) + "\n")
    return path


def waiting_mark():
    """This thread's mark that the running ticket's run waits for a warm pool card (`forecasts/<node>/<key>.waiting/
    <pid>-<thread>`); None outside a ticket."""
    ticket = os.environ.get(TICKET, "")
    if len(ticket.split()) != 2:
        return None
    node, key = ticket.split()
    return forecasts_folder() / node / f"{key}.waiting" / f"{os.getpid()}-{threading.get_ident()}"


def mark_waiting():
    """Mark (again) that this thread's run waits for a warm pool card now, so its runaway watch does not count the
    wait as the run's work (is_waiting; benchmark of 2026-10-23: a rough model waiting on the pool's first card would
    have been stopped at twice its 12 measured minutes). A mark not touched for WAIT_FRESH_SECONDS no longer counts."""
    mark = waiting_mark()
    if mark is not None:
        mark.parent.mkdir(parents=True, exist_ok=True)
        mark.touch()


def unmark_waiting():
    """This thread's run waits for a pool card no longer."""
    mark = waiting_mark()
    if mark is not None:
        mark.unlink(missing_ok=True)


def is_waiting(ticket, fresh_seconds=WAIT_FRESH_SECONDS):
    """Whether a process of the ticket's run marked itself waiting for a pool card (waiting) within
    `fresh_seconds`: a mark its process left behind on a kill goes stale and no longer counts."""
    node, key = ticket.split()
    folder = forecasts_folder() / node / f"{key}.waiting"
    now = time.time()
    return folder.exists() and any(now - mark.stat().st_mtime < fresh_seconds for mark in folder.iterdir())


def kept(ticket):
    """Every batch pre-flight kept for a run, oldest first."""
    node, key = ticket.split()
    path = forecasts_folder() / node / f"{key}.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()] if path.exists() else []


def said(flight):
    """One line for the run's log."""
    numbers = flight["measured"]
    return (f"pre-flight: {flight['jobs']} jobs on {flight['cards']} cards, about {flight['minutes']:.0f} min and "
            f"EUR {flight['euros']:.2f} (high {flight['high_minutes']:.0f} min, EUR {flight['high_euros']:.2f}), "
            f"from {numbers['machines']} measured {numbers['stage']} machines: {numbers['job_seconds']:.0f} s a job, "
            f"{numbers['setup_minutes']:.1f} min set-up, EUR {numbers['euros_per_card_minute']:.4f} a card-minute")


def for_ticket(jobs, entries, cap, slots=1):
    """Under a runner's ticket, the batch's pre-flight from its stage's measured numbers (`entries`: a call that reads
    the ledger, made only then), kept and said; None outside a ticket or while the stage is unmeasured."""
    ticket = os.environ.get(TICKET, "")
    if len(ticket.split()) != 2:
        return None
    numbers = measured(entries(), stage_of(ticket))
    if numbers is None:
        return None
    flight = batch(jobs, numbers, cap, slots)
    flight["high_minutes"] = round(flight["high_minutes"] * processor_margin([numbers["kind"]]), 2)
    keep(ticket, flight)
    print(said(flight), flush=True)
    return flight
