"""What cloud batches have cost, and whether the next one fits the owner's limits.

The owner's limits (2026-09-29): a batch runs at most four hours and spends at most €60 (raised
from €50 for the worldfill batches), and the month at most MONTH_EUROS (€1,500 by default since 2026-10-08). The
provider's own bill lags by hours, so the month's spend is whichever is higher, its bill or this ledger's sum. A batch that would pass any limit is refused before it starts.
"""
import datetime
import json
import math
import os
import time

from paths import HOME

LEDGER = HOME / "cloud" / "ledger.jsonl"
BATCH_HOURS = 4
BATCH_EUROS = 60.0
# The month's ceiling (owner, 2026-10-08: the cloud credits cover about €3,000 a month): SCORE_MONTH_EUROS, else
# €1,500. Checked before every machine is rented (batch.rent); a run stops rather than pass it.
MONTH_EUROS = float(os.environ.get("SCORE_MONTH_EUROS", "1500"))


def record(entry):
    """Add one finished batch to the ledger."""
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a") as ledger:
        ledger.write(json.dumps(entry) + "\n")


def entries():
    """Every batch the ledger holds, oldest first."""
    if not LEDGER.exists():
        return []
    return [json.loads(line) for line in LEDGER.read_text().splitlines() if line.strip()]


def month_total(month, batches):
    """What the batches started in `month` (YYYY-MM) cost, in euros."""
    return sum(batch["euros"] for batch in batches if batch["started"].startswith(month))


def this_month():
    """The current month as YYYY-MM, in UTC like the ledger's times."""
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m")


def cost(minutes, euros_per_minute, unit_minutes=1):
    """What a machine costs for `minutes`, billed by the started unit: a minute for the cards, an hour for the
    machines the provider prices by the hour."""
    return math.ceil(minutes / unit_minutes) * unit_minutes * euros_per_minute


def machine_row(machine):
    """The ledger's record of one rented machine: its type, zone and cards; whether it answered, how long that
    took and how long it worked after; its whole time and cost; and what the runner counted of its work."""
    ended = machine.get("deleted") or time.time()
    ready = machine.get("ready")
    # A machine taken parked from another run (park.py) is this run's from when it was taken, and costs it only what
    # it adds past the hours that run already paid.
    began = machine.get("adopted") or machine["created"]
    minutes = (ended - began) / 60
    unit_minutes = machine.get("unit_minutes", 1)
    euros = (cost((ended - machine["created"]) / 60, machine["price"], unit_minutes)
             - machine.get("paid_minutes", 0.0) * machine["price"])
    row = {"type": machine["type"], "zone": machine["zone"], "cards": machine.get("cards"),
           "started": ready is not None,
           "start_wait_minutes": ((ready or ended) - began) / 60,
           "work_minutes": (ended - ready) / 60 if ready else 0.0, "minutes": minutes, "euros": max(0.0, euros)}
    row.update({key: machine[key] for key in ("peak_gb", "made", "unit_seconds", "adopted", "parked")
                if machine.get(key) is not None})
    return row


def machines_record(machines, attempts, started):
    """The part of a run's ledger entry about its machines: a row each, the starts that failed before them
    (offers refused or out of stock, machines that never answered), the run's wait for its first machine,
    and the minutes and euros of all of them."""
    rows = [machine_row(machine) for machine in machines]
    ready = [machine["ready"] for machine in machines if machine.get("ready")]
    return {"machines": rows, "attempts": list(attempts),
            "start_wait_minutes": (min(ready) - started) / 60 if ready else None,
            "machine_minutes": sum(row["minutes"] for row in rows + list(attempts)),
            "euros": sum(row["euros"] for row in rows + list(attempts))}


def minutes_allowed(euros_per_minute, spent_this_month):
    """The most minutes a batch may run: the time limit, the batch cap and the month's remainder."""
    by_money = min(BATCH_EUROS, MONTH_EUROS - spent_this_month) / euros_per_minute
    return max(0.0, min(BATCH_HOURS * 60.0, by_money))


def refusal(estimated_minutes, euros_per_minute, spent_this_month):
    """Why a batch estimated at `estimated_minutes` may not start, or None when it may."""
    if estimated_minutes > BATCH_HOURS * 60:
        return (f"the batch would take about {estimated_minutes:.0f} min, over the "
                f"{BATCH_HOURS} h limit; split it")
    euros = cost(estimated_minutes, euros_per_minute)
    if euros > BATCH_EUROS:
        return f"the batch would cost about €{euros:.2f}, over the €{BATCH_EUROS:.0f} cap"
    if spent_this_month + euros > MONTH_EUROS:
        return (f"€{spent_this_month:.2f} spent this month; €{euros:.2f} more would pass "
                f"the €{MONTH_EUROS:.0f} month cap")
    return None
