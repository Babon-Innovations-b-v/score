"""What cloud batches have cost, and whether the next one fits the owner's limits.

The owner's limits (2026-09-29): a batch runs at most four hours and spends at most €60 (raised
from €50 for the worldfill batches), and the month at most MONTH_EUROS (€3,000 by default since 2026-10-11, the
owner's monthly cloud credits). The
provider's own bill lags by hours, so the month's spend is whichever is higher, its bill or this ledger's sum. A batch that would pass any limit is refused before it starts.
"""
import datetime
import json
import math
import os
import pathlib
import time

from paths import HOME

LEDGER = HOME / "cloud" / "ledger.jsonl"
BATCH_HOURS = 4
BATCH_EUROS = 60.0
# The month's ceiling (owner, 2026-10-08: the cloud credits cover about €3,000 a month): SCORE_MONTH_EUROS, else
# €3,000 (owner, 2026-10-11). Checked before every machine is rented (batch.rent); a run stops rather than pass it.
MONTH_EUROS = float(os.environ.get("SCORE_MONTH_EUROS", "3000"))
# The kind of the line written before each machine is ordered (rent_started, from the backend's create under
# batch.rent); its run's own row comes at the end.
RENT_STARTED = "rent-started"
# The kind of the line written when an order is refused (rent_refused, from the backend's create): it closes its
# started line, so a refused order is told apart from a machine left running.
RENT_REFUSED = "rent-refused"
# The kinds of line that are not a run's own row.
ORDER_LINES = ("rent-started", "rent-refused", "order-started")
# The kind of the line written before a cluster or a node pool is ordered (order_started, from the cluster set-up).
ORDER_STARTED = "order-started"
# The month's books as read back after a loss (#13: the ledgers went with the old WSL disk on 2026-10-19):
# {month, state: "lost" or "known", bill, bill_at, source, google_before}, written by `score spend --read-back` (state
# lost) and the owner's `score spend --google-month` (state known). Paid work is refused while the month's books are
# not known (books_refusal).
BOOKS = HOME / "cloud" / "books.json"
# Set in a process that may spend nothing (the restore of #13): every paid point raises FreeOnly there.
FREE_ONLY = "SCORE_FREE_ONLY"


class FreeOnly(Exception):
    """A paid or heavy step was reached in a process that runs free only (FREE_ONLY)."""


class BooksUnknown(Exception):
    """Paid work was asked for while the month's books are not known (books_refusal)."""


def origin():
    """Who spent: the checkout this code runs from (an agent's worktree, or the main one) and the runner's spend ticket
    (its node), so spend splits by track (`tools/costs/costs.py today --since`)."""
    return {"worktree": pathlib.Path(__file__).resolve().parents[3].name,
            "ticket": os.environ.get("SCORE_SPEND_TICKET")}


def record(entry):
    """Add one finished batch to the ledger, with its origin."""
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a") as ledger:
        ledger.write(json.dumps({**origin(), **entry}) + "\n")


def rent_started(run, name, offer, deadline):
    """Write that machine `name` of `run` is about to be ordered from `offer` ({type, zone, class, price}), before the
    order is sent: a machine whose run dies before its end-of-run row still shows, with the run's ticket (origin).
    Nothing is billed yet, so it holds no euros; until it is closed it counts in month_total at its price up to
    `deadline` (epoch seconds; its watchdog deletes it then), or None when unknown."""
    record({"started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "batch": f"rent-{name}",
            "kind": RENT_STARTED, "state": "started", "run": run, "name": name, **offer, "deadline": deadline,
            "machines": [], "attempts": [], "machine_minutes": 0.0, "euros": 0.0})


def rent_refused(name, reason):
    """Write that the order of machine `name` was refused (`reason`, the provider's words), closing its started line."""
    record({"started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "batch": f"rent-{name}",
            "kind": RENT_REFUSED, "state": "refused", "name": name, "reason": reason,
            "machines": [], "attempts": [], "machine_minutes": 0.0, "euros": 0.0})


def open_rents(batches, now):
    """The started lines of machines still open at `now`: no row of their run, no disk-and-address row of their
    machine (written at its delete) and no refused line of their order."""
    runs = {batch.get("batch") for batch in batches if batch.get("kind") not in ORDER_LINES}
    closed = {batch.get("name") for batch in batches if batch.get("kind") in ("disk-and-address", RENT_REFUSED)}
    return [batch for batch in batches if batch.get("kind") == RENT_STARTED and batch.get("run") not in runs
            and batch.get("name") not in closed and moment(batch["started"]) <= now]


def open_euros(line, now):
    """What an open started line's machine has cost by `now`: its price from the order until now or its deadline
    (else BATCH_HOURS after the order, the longest a batch runs), billed by the minute."""
    began = moment(line["started"])
    ends = line.get("deadline") or began + BATCH_HOURS * 3600
    return cost(max(0.0, min(now, ends) - began) / 60, line.get("price") or 0.0)


def moment(text):
    """A ledger time (ISO 8601, Z) as epoch seconds."""
    return datetime.datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()


def order_started(what, name, details):
    """Write that `what` (a cluster, a node pool) named `name` is about to be ordered, with `details` ({type, zone}),
    before the order is sent. Its nodes are billed as machines and come to the ledger as their runs' rows; the line
    shows the order itself, so nothing is made outside the ledger. It holds no euros."""
    record({"started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "batch": f"order-{what}-{name}",
            "kind": ORDER_STARTED, "state": "started", "what": what, "name": name, **details,
            "machines": [], "attempts": [], "machine_minutes": 0.0, "euros": 0.0})


def entries():
    """Every batch the ledger holds, oldest first."""
    if not LEDGER.exists():
        return []
    return [json.loads(line) for line in LEDGER.read_text().splitlines() if line.strip()]


def month_total(month, batches, now=None):
    """What the batches started in `month` (YYYY-MM) cost, in euros, a machine still open (open_rents) at what it has
    cost by `now` (default: the time now): the guard counts machines running and not yet in a run's row."""
    now = time.time() if now is None else now
    return (sum(batch["euros"] for batch in batches if batch["started"].startswith(month))
            + sum(open_euros(line, now) for line in open_rents(batches, now) if line["started"].startswith(month)))


def this_month():
    """The current month as YYYY-MM, in UTC like the ledger's times."""
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m")


def read_books():
    """The month's books as read back (BOOKS), or {} when none were written."""
    return json.loads(BOOKS.read_text()) if BOOKS.exists() else {}


def write_books(books):
    """Write the month's books whole (a reader never sees half a file)."""
    BOOKS.parent.mkdir(parents=True, exist_ok=True)
    partial = BOOKS.with_name(f"{BOOKS.name}.{os.getpid()}.partial")
    partial.write_text(json.dumps(books, indent=1))
    partial.replace(BOOKS)


def written_before(lines, field, month):
    """True when one of the ledger `lines` is dated (its `field`, ISO) before `month` (YYYY-MM)."""
    return any(str(line[field])[:7] < month for line in lines if line.get(field))


def google_lines():
    """Every line of the Google call ledger (google_spend.py, beside this file), oldest first."""
    import google_spend
    if not google_spend.LEDGER.exists():
        return []
    return [json.loads(line) for line in google_spend.LEDGER.read_text().splitlines() if line.strip()]


def books_refusal():
    """Why the month's spend is not known, or None when it is. Known means the books for this month say so (the
    owner gave the Google month, `score spend --google-month`), or, with no books for this month, the cloud ledger
    and the Google ledger each hold a line from before the month began: each was written without a break since then.
    A ledger lost and begun again (a refusal line written after the loss) holds no such line, so it stays refused
    until the owner's figure or the next month (fault, 2026-10-19: both ledgers were lost with the disk, and a missing
    ledger read as EUR 0)."""
    month = this_month()
    books = read_books()
    if books.get("month") == month:
        if books.get("state") == "known":
            return None
        return (f"the month's books are {books.get('state', 'unknown')} ({BOOKS}): paid work is refused until the "
                f"owner gives the Google month (score spend --google-month EUR) or the month ends")
    if written_before(entries(), "started", month) and written_before(google_lines(), "time", month):
        return None
    return (f"the month's spend is unknown: the cloud ledger ({LEDGER}) and the Google ledger do not both run "
            f"from before {month}; paid work is refused until `score spend --read-back` and the owner's "
            f"`score spend --google-month EUR`, or the next month")


def google_before():
    """The euros Google billed this month before the Google ledger began again (the books' `google_before`, known
    from the owner), 0 when the books hold none for this month."""
    books = read_books()
    return float(books.get("google_before") or 0.0) if books.get("month") == this_month() else 0.0


def refuse_free_only(what):
    """Raise FreeOnly when this process runs free only; `what` says what was about to be paid or run."""
    if os.environ.get(FREE_ONLY) == "1":
        raise FreeOnly(f"{what}: refused, this process runs free only ({FREE_ONLY}=1)")


def require_books(what):
    """The gate at a paid point, before anything is ordered: FreeOnly in a process that runs free only, BooksUnknown
    while the month's spend is not known (books_refusal); `what` says what was about to be ordered."""
    refuse_free_only(what)
    refused = books_refusal()
    if refused:
        raise BooksUnknown(f"{what}: {refused}")


def cost(minutes, euros_per_minute, unit_minutes=1):
    """What a machine costs for `minutes`, billed by the started unit: a minute for the cards, an hour for the
    machines the provider prices by the hour."""
    return math.ceil(minutes / unit_minutes) * unit_minutes * euros_per_minute


def machine_row(machine):
    """The ledger's record of one rented machine: its type, zone and cards; whether it answered, how long that
    took, its set-up and how long it worked after; its whole time and cost; and what the runner counted of its work."""
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
    if ready and machine.get("set_up"):
        row["setup_minutes"] = (machine["set_up"] - ready) / 60
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
