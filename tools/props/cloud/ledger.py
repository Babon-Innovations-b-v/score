"""What cloud batches have cost, and whether the next one fits the owner's limits.

The owner's limits (2026-09-29): a batch runs at most four hours and spends at most €60 (raised
from €50 for the worldfill batches), and the month at most €700. Scaleway's own bill lags by hours, so the month's spend is whichever is higher,
its bill or this ledger's sum. A batch that would pass any limit is refused before it starts.
"""
import datetime
import json
import math

from paths import HOME

LEDGER = HOME / "cloud" / "ledger.jsonl"
BATCH_HOURS = 4
BATCH_EUROS = 60.0
MONTH_EUROS = 700.0


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


def cost(minutes, euros_per_minute):
    """What a machine costs for `minutes`, billed by the started minute."""
    return math.ceil(minutes) * euros_per_minute


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
