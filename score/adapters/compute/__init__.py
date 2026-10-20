"""The compute adapter: the only way a paid node reaches the cloud, over the job contract tools/cloud already has.

    ticket = compute.clearance(runner, node, euros)  # refused unless the runner keys the node and the month has room
    compute.submit(runner, node, job_store, run, job, spec)   # tools/cloud/runtime/submit.write_job, after clearance

Clearance comes from the framework, not from a typed yes (the owner's answer of 2026-10-11: his picks are made, from
concept and style on everything runs automatically, no spend limit, spend logically). A node is cleared when the
runner keys it, which it does only when every earlier node it reads passed its gates (unknown blocks) and stands
accepted (score.graph), and when the month's ceiling (tools/props/cloud/ledger.py, MONTH_EUROS) has room for the
run's estimate (the spec's `euros`) over what the ledger holds for the month. The clearance is written to the store
(`clearances/<node>/<key>/`); without it nothing is submitted, so a run that skips the runner cannot spend. The job
carries its node and key, so the finish record and the job can be matched. The machine path (tools/props/cloud) is
reached the same way, through the engine adapter (score.adapters.engines), which asks for clearance first.

Every place that spends (tools/props/cloud/batch.py's `rent`, tools/cloud/k8s/submitter.py's `submit` and
clusters/scaleway.py's `up`, tools/props/closeup/pro.py's `draw`, tools/props/scene/marble.py's `generate` and
`paint`) asks `require_cleared` first, so the old paid entry points (blender_cloud.py, detached.py, the runners,
demo.py, make_jobs.py, the close-up stage) refuse to spend unless they run inside a cleared run:

    with compute.spending(ticket):         # SCORE_SPEND_TICKET="<node> <key>" for this process and its children
        ...                                # anything here may rent
    compute.require_cleared("a batch")     # at a rent point: Refused unless the runner cleared that node and key

Clearing is serialised, as lines run side by side (score.graph's drive): the month's check and the clearance are
made under one lock (`clearing.lock` beside the store), and every clearance holds a reservation of its estimate
(`reservations.json` beside it) until its run ends (`spending` releases it, and holds it open while its process
lives), or, for one handed to a job store, until a batch's longest run (the ledger's BATCH_HOURS) or its runaway limit
has passed. A trial's own store inside the home (compare.py's) is covered by the framework store: its paid jobs are
checked against the world's stop line and reserved beside the framework store, so they count in flight. The month's
check counts the open reservations with the ledger, which records a batch only once it is done, so two lines can never
both spend the month's last euros.

The world's stop line (guard.py, owner 2026-10-18) is checked under the same lock: a paid job is refused before it
starts when its forecast, with the world's spend since its first line and every run in flight, would pass the line;
a started job is never stopped as the bill nears it, only a runaway past twice its forecast minutes.

The owner's override, an extra route he may use and never a requirement, is his yes for a run outside the runner:
he gives it from his own terminal for a name of his choosing (the review command's spend, node `override`, key
<name>, at his euros), and the run carries SCORE_SPEND_TICKET="override <name>"; an override yes counts in flight for
a batch's longest run. A rent point checks that the yes exists, or that the clearance's run still holds its
reservation; the ledger's own ceilings still apply there. A barrier, not a lock: an agent can name a
clearance given earlier, and every clearance names its node, key, estimate and time.
"""
import contextlib
import datetime
import fnmatch
import json
import os
import pathlib
import sys

from score import graph
from score.adapters.compute import guard
from score.store import PROPS_HOME, RUNNER, Store, locked, running_under_agent

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tools/cloud/runtime"))
import submit as job_contract  # noqa: E402

TICKET = "SCORE_SPEND_TICKET"
# Each paid stage's measured cost of one unit of its work, with the ledger lines it rests on (tools/costs/per_unit.py).
PER_UNIT = REPO / "data/costs/per-unit.json"
# The folder of the store the ticket's clearance is in, set beside the ticket (a trial store's, compare.py's).
STORE = "SCORE_SPEND_STORE"
# The `score run` a clearance was made under (score/__main__.py): its reservations end with it, even when stopped.
RUN_ID = "SCORE_RUN_ID"
OVERRIDE = "override"
# How long a paid API's judge is waited on before an ask counts as timed out (SCORE_JUDGE_TIMEOUT seconds): an
# operational setting like the card classes, outside every stage's key, since it decides only whether an answer
# comes back, never what it says. 120 s since 2026-10-14 17:00, when Gemini 3.1 Pro's answers rose from a 9 s median
# to about 50 s against the 60 s then kept in the keyed models adapter (49 read timeouts after 15:00).
JUDGE_TIMEOUT = "SCORE_JUDGE_TIMEOUT"
JUDGE_TIMEOUT_SECONDS = 120.0


def judge_timeout():
    """The seconds a judge's answer is waited on, read when the call is made."""
    return float(os.environ.get(JUDGE_TIMEOUT, JUDGE_TIMEOUT_SECONDS))


class Refused(Exception):
    """A paid run is refused: its node is blocked, or the month's ceiling has no room for it."""


def ledger():
    """tools/props/cloud/ledger.py, the month's ceiling and what the month has cost."""
    for folder in ("tools/props", "tools/props/cloud"):
        if str(REPO / folder) not in sys.path:
            sys.path.append(str(REPO / folder))  # appended: its modules must not shadow anyone else's
    import ledger as cloud_ledger
    return cloud_ledger


def cloud_bill():
    """What the cloud provider has billed this month so far (its own consumption, every product), in euros."""
    ledger()  # puts tools/props/cloud on the path
    import provider

    return provider.cloud.month_spend(provider.cloud.account())


def google_bill():
    """What Google has billed this month so far (cost plus credits, EUR), read from its billing export
    (tools/props/cloud/google_bill.py); google_bill.Unread when it cannot be read."""
    books = ledger()  # puts tools/props/cloud on the path
    import google_bill as export

    return export.month_euros(books.this_month())


def google_bill_set():
    """True when a Google billing export table is set (google_bill.table), so the books can read Google's bill."""
    ledger()
    import google_bill as export

    return export.table() is not None


def google_month():
    """What Google cost this month, in euros: with the owner's figure in the books (`google_before`, an override)
    that figure plus the Google ledger's month (tools/props/cloud/google_spend.py, calls still going or lost
    included), else the higher of the Google bill the books last read (`google_bill`, lagging by hours) and the
    Google ledger's month."""
    books = ledger()
    import google_spend  # beside ledger.py; its month counts a call started and never finished at its estimate
    logged = google_spend.month_euros(books.this_month())
    if books.this_months_books().get("google_before") is not None:
        return logged + books.google_before()
    return max(logged, books.this_months_books().get("google_bill") or 0.0)


def month_spent():
    """What this month has cost so far, in euros: the cloud's (the higher of its own bill, which lags by hours, and the
    cloud ledger, which counts a batch once it ends) plus Google's (google_month)."""
    books = ledger()
    cloud = max(cloud_bill(), books.month_total(books.this_month(), books.entries()))
    return cloud + google_month()


def month_refusal(euros, reserved=0.0):
    """Why a run estimated at `euros` would pass the month's ceiling, with `reserved` euros cleared for runs not yet
    in the ledger, or None when the month has room. The month's spend is the cloud's, the higher of its own bill
    (which lags by hours) and the cloud ledger (which counts a batch once it ends), plus the Google ledger's
    (tools/props/cloud/google_spend.py), calls still going or lost included. Fault (2026-10-12): the bill held EUR
    1,554 for October and the ledger EUR 1,387; disks, addresses and storage were never in the ledger. Refused
    outright, before the bill is read, in a process that runs free only (ledger.FreeOnly) and while the month's books
    are not known (ledger.books_refusal: both ledgers were lost on 2026-10-19, and a missing ledger read as EUR 0). With
    a Google billing export set, both bills are read back into the books first (read_back_books)."""
    books = ledger()
    books.refuse_free_only("a paid run")
    if google_bill_set():
        read_back_books()
    unknown = books.books_refusal()
    if unknown:
        return unknown
    spent = month_spent()
    if spent + reserved + euros > books.MONTH_EUROS:
        return (f"EUR {spent:.2f} spent this month and EUR {reserved:.2f} cleared for runs still going; EUR {euros} "
                f"more would pass the EUR {books.MONTH_EUROS:.0f} ceiling")
    return None


def per_unit(stage):
    """The measured per-unit numbers of `stage` (PER_UNIT, written by tools/costs/per_unit.py), or None."""
    for entry in json.loads(PER_UNIT.read_text())["stages"].values():
        if stage == entry["stage"] or stage in entry["also"]:
            return entry
    return None


def node_minutes():
    """{stage: {likely, high, makes, from}} of the makes the store's finish records timed (PER_UNIT's `node_minutes`,
    written by tools/costs/per_unit.py --store), read once for a whole plan."""
    return json.loads(PER_UNIT.read_text()).get("node_minutes", {})


def take_files(listing, ending):
    """The output's own files ending in `ending` at its top level, its contract left out (one a take)."""
    return [name for name in listing if "/" not in name and name.endswith(ending) and name != "contract.json"]


def map_attempts(record):
    """The map pictures drawn for one take: every attempt of its front and of each view."""
    return len(record["front"]["attempts"]) + sum(len(view["attempts"]) for view in record.get("views", {}).values())


def named_again(record):
    """The finishes of one take that were asked for their surface again (one call each)."""
    return sum(1 for finish in record["finishes"] if str(finish.get("by", "")).startswith("named again"))


def counted_units(store, output, count):
    """The units `output` made by its stage's count rule (PER_UNIT's `count`), or None when the rule finds nothing
    to count in it."""
    listing = store.listing(output)
    rule, value = next(iter(count.items()))
    if rule == "one":
        return 1
    if rule == "files":
        return sum(1 for name in listing if fnmatch.fnmatch(name, value))
    if rule == "take_files":
        return len(take_files(listing, value))
    if rule == "json_keys":
        return len(store.read_file(output, value)) if value in listing else None
    if rule == "json_field":
        return store.read_file(output, value[0]).get(value[1]) if value[0] in listing else None
    if rule == "map_attempts":
        return sum(map_attempts(store.read_file(output, name)) for name in listing if name.endswith("/" + value))
    if rule == "named_again":
        return sum(named_again(store.read_file(output, name)) for name in take_files(listing, value))
    raise ValueError(f"unknown count rule {rule!r} in {PER_UNIT}")


def unit_price(node, store):
    """A paid node priced per unit: its stage's measured per-unit euros (PER_UNIT) times the units its accepted
    output made ({likely_euros, high_euros, unit, units, unit_likely_euros, unit_high_euros, runs}), or None when the
    stage has no measured unit, the node has no accepted output to count, or the count finds nothing. The units are
    the last accepted make's: a fix that adds objects makes more. A stage priced from recorded runs has no count rule:
    None."""
    entry = per_unit(node.partition("@")[0])
    output = store.accepted(node) if entry and entry["count"] and store is not None else None
    units = counted_units(store, output, entry["count"]) if output else None
    if units is None:
        return None
    return {"likely_euros": round(entry["likely_euros"] * units, 4), "high_euros": round(entry["high_euros"] * units, 4),
            "unit": entry["unit"], "units": units, "unit_likely_euros": entry["likely_euros"],
            "unit_high_euros": entry["high_euros"], "runs": entry["runs"]}


def run_forecast(node, euros, store=None):
    """A paid node's run forecast ({euros, minutes, high_minutes, measured}): its stage's measured runs in the cloud
    ledger at their high euros, likely and high minutes (tools/props/cloud/preflight.py), else its measured per-unit
    high times its units (unit_price, on `store`) with no minutes, else the stage's own estimate `euros` with no
    minutes; Refused with none. The runner's numbers, never an agent's: the owner, 2026-10-18."""
    books = ledger()
    import preflight  # beside ledger.py
    run = preflight.node_run(books.entries(), node.partition("@")[0])
    if run:
        return {"euros": round(run["high_euros"], 4), "minutes": round(run["minutes"], 2),
                "high_minutes": round(run["high_minutes"], 2), "measured": run["runs"]}
    unit = unit_price(node, store)
    if unit:
        return {"euros": unit["high_euros"], "minutes": None, "high_minutes": None, "measured": unit["runs"]}
    if euros is None:
        raise Refused(f"{node}: a paid run needs its estimate in euros, or measured runs of its stage in the ledger, "
                      "before the runner can clear it")
    return {"euros": euros, "minutes": None, "high_minutes": None, "measured": 0}


def forecast_price(node, units):
    """A paid node priced per unit before it is made: its own stage's measured per-unit euros (PER_UNIT, never an
    `also` stage's) times the `units` its stage's forecast rule counted ({likely_euros, high_euros, unit, units,
    unit_likely_euros, unit_high_euros, runs, unit_source}), or None when the stage has no measured unit or no
    forecast rule, or no units were counted (none, or 0: nothing counted is unknown, never free)."""
    stage = node.partition("@")[0]
    entry = per_unit(stage)
    if not units or entry is None or entry["stage"] != stage or not entry.get("forecast"):
        return None
    return {"likely_euros": round(entry["likely_euros"] * units, 4), "high_euros": round(entry["high_euros"] * units, 4),
            "unit": entry["unit"], "units": units, "unit_likely_euros": entry["likely_euros"],
            "unit_high_euros": entry["high_euros"], "runs": entry["runs"], "unit_source": entry["forecast"]["source"]}


def unit_minutes(stage, units):
    """How long `units` units of `stage` keep the run, on its measured time (PER_UNIT's `time`, the same ledger lines
    as its euros) by the runner's own card rule (tools/props/cloud/preflight.py cards_for and minutes_for, capped at
    capacity.run_cap; the high minutes on the high job time and the high set-up): {likely_minutes, high_minutes,
    cards} (cards None for a stage of calls), or {minutes_why} when its time or set-up is unmeasured or no units were
    counted."""
    entry = per_unit(stage)
    time = (entry or {}).get("time") or {}
    if not units:
        return {"minutes_why": "no units counted"}
    if "unit_seconds" not in time:
        return {"minutes_why": time.get("why", f"{stage}: no measured time in {PER_UNIT.name}")}
    setup = time.get("setup_minutes") or {}
    if "likely" not in setup:
        return {"minutes_why": setup.get("why", f"{stage}: no measured set-up in {PER_UNIT.name}")}
    ledger()  # puts tools/props/cloud on the path
    import capacity  # beside ledger.py
    import preflight
    numbers = {"job_seconds": time["unit_seconds"]["likely"], "high_job_seconds": time["unit_seconds"]["high"],
               "setup_minutes": setup["likely"]}
    machines, slots = time["holds"] == "machines", max(1, time.get("slots") or 1)
    cards = preflight.cards_for(units, numbers, capacity.run_cap() if machines else 1, slots)
    return {"likely_minutes": round(preflight.minutes_for(units, cards, numbers["job_seconds"], setup["likely"],
                                                          slots), 2),
            "high_minutes": round(preflight.minutes_for(units, cards, numbers["high_job_seconds"], setup["high"],
                                                        slots), 2),
            "cards": cards if machines else None}


def per_unit_run(price, node, cards):
    """A per-unit price with its minutes (unit_minutes on its units) and the cards those minutes are worked out on;
    `cards` (the ledger's ticketed run sizing) where its time is unmeasured."""
    timed = unit_minutes(node.partition("@")[0], price["units"])
    if "minutes_why" in timed:
        return {**price, "likely_minutes": None, "high_minutes": None, "minutes_why": timed["minutes_why"],
                "cards": cards}
    return {**price, **timed}


def guess(euros, guess_from):
    """Not measured yet: no price, the stage's own estimate kept apart as `guess_euros` with where it is written."""
    return {"likely_euros": None, "high_euros": None, "guess_euros": euros,
            **({"guess_from": guess_from} if guess_from else {}), "likely_minutes": None, "high_minutes": None,
            "runs": 0, "basis": "not measured yet"}


def run_price(node, euros, store=None, units=None, guess_from=None):
    """A paid node's price as the creator cockpit shows it, on the runner's own numbers (tools/props/cloud/preflight.py):
    {likely_euros, high_euros, likely_minutes, high_minutes, cards, runs, basis}. When the caller counted `units` by
    its stage's forecast rule (the holes' price: a node in a hole's chain is made again, with what the hole adds),
    measured per unit times those first (forecast_price, basis "per unit × forecast"): neither a whole run of
    another make nor the units the last make counted says what this make makes. Else measured runs: its stage's
    runs in the cloud ledger, likely their median and high their HIGH quantile (high_euros is what its clearance
    reserves), and the cards a whole run of it is sized on. Else measured per unit times the units its accepted
    output made (unit_price on `store`, basis "per unit × counted"). A per-unit price's minutes and cards are its
    units on its stage's measured time by the runner's card rule (unit_minutes; `minutes_why` where it has none):
    the ledger's lines carry no ticket, so a stage's runs are found by its kind of batch, as its euros are. Else not
    measured yet: no price (likely and high
    None), the stage's own estimate kept apart as `guess_euros` (with `guess_from`, where the row names it, when
    given), runs 0; a guess is never shown as a price (the owner, 2026-10-18)."""
    books = ledger()
    import capacity  # beside ledger.py
    import preflight
    entries, stage = books.entries(), node.partition("@")[0]
    cards = preflight.run_cards(entries, stage, capacity.run_cap())
    forecast = forecast_price(node, units)
    if forecast is not None:
        return {**per_unit_run(forecast, node, cards), "basis": "per unit × forecast"}
    run = preflight.node_run(entries, stage)
    if run is not None:
        return {"likely_euros": round(run["euros"], 4), "high_euros": round(run["high_euros"], 4),
                "likely_minutes": round(run["minutes"], 2), "high_minutes": round(run["high_minutes"], 2),
                "cards": cards, "runs": run["runs"], "basis": "measured runs"}
    unit = unit_price(node, store)
    if unit is not None:
        return {**per_unit_run(unit, node, cards), "basis": "per unit × counted"}
    return {**guess(euros, guess_from), "cards": cards, "minutes_why": "not measured yet"}


def books_now():
    """The month's spend as it stands, each book apart: {month, bill, ledger, google}."""
    books = ledger()
    month = books.this_month()
    return {"month": month, "bill": cloud_bill(), "ledger": books.month_total(month, books.entries()),
            "google": google_month()}


def read_google_bill():
    """This month's Google bill as the books hold it: {google_bill, google_bill_at, google_unread: None}, or
    {google_unread: why} when its billing export cannot be read (google_bill.Unread)."""
    ledger()
    import google_bill as export

    try:
        euros = google_bill()
    except export.Unread as unread:
        return {"google_unread": str(unread)}
    return {"google_bill": round(euros, 2), "google_bill_at": graph.now(), "google_unread": None}


def read_back_books():
    """Read the month's cloud bill and Google bill back (read-only) into the books; the books. They are `known` when
    Google's bill was read (its billing export, read_google_bill); else they keep the state they had for this month,
    `lost` when none, which refuses paid work (ledger.books_refusal) with the reason it was not read. The owner's
    Google figure (`google_before`) stays and overrides the bill read (google_month). Whether the Scaleway bill holds
    VAT is not known (SCORE_BILL_FACTOR is unsettled)."""
    books = ledger()
    month = books.this_month()
    held = books.this_months_books()
    google = read_google_bill()
    state = "known" if google["google_unread"] is None else held.get("state", "lost")
    source = "scaleway consumption" + ("" if google["google_unread"] else " + google billing export (bigquery)")
    read = {**held, "month": month, "state": state, "bill": round(cloud_bill(), 2), "bill_at": graph.now(),
            "source": source, "vat_in_bill": "unknown", **google}
    books.write_books(read)
    return read


def owners_google_month(euros):
    """The owner's figure for what Google billed this month before the Google ledger began again, an override of the
    bill read from Google's billing export (read_back_books): the books' known state; the books. Refused in a process an agent started (only the owner knows the Google bill) and for a figure
    that is not finite and at least 0 (`nan` passed every ceiling, a negative one lowered the month)."""
    if running_under_agent():
        raise Refused("the Google month is the owner's figure: he enters it from his own terminal")
    books = ledger()
    figure = books.euro_figure(euros)
    if figure is None:
        raise Refused(f"the Google month must be a finite figure of at least EUR 0, not {euros!r}")
    known = {**books.this_months_books(), "month": books.this_month(), "state": "known", "google_before": figure,
             "google_at": graph.now()}
    books.write_books(known)
    return known


def months_since(baseline, now):
    """{month: {bill, ledger, google}} from the baseline's month to `now`'s (books_now): the bill read only for the
    current month (an earlier month's ledger stands for its bill)."""
    books = ledger()
    import google_spend
    return {month: now if month == now["month"] else
            {"bill": None, "ledger": books.month_total(month, books.entries()), "google": google_spend.month_euros(month)}
            for month in guard.months_from(baseline["month"], now["month"])}


def covering_store(store):
    """The store whose stop lines and reservations cover `store`'s paid jobs: the framework store for itself and for a
    trial's own store inside the home (compare.py's, whose paid rows spend world 1's money); a store outside the home
    (a test's) covers itself. Fault (2026-10-18 review): a trial's store had no stop line, so its paid rows were never
    checked against the world's stop, and its reservations were never counted in flight."""
    if store.is_framework_store() or not store.objects.root.resolve().is_relative_to(PROPS_HOME.resolve()):
        return store
    return Store.default()


def open_overrides(store):
    """{yes time: yes} of the owner's override yeses younger than a batch's longest run: runs outside the runner that
    may still be going, counted in flight."""
    oldest = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=ledger().BATCH_HOURS)
    yeses = (store.read(key) for key in store.objects.keys(f"spend-yes/{OVERRIDE}/"))
    return {yes["at"]: yes for yes in yeses if datetime.datetime.fromisoformat(yes["at"]) > oldest}


def stop_refusal(runner, node, forecast, held):
    """Why the world's stop line has no room for a job at `forecast` euros with every run in `held` still to come,
    or None when it has; the owner's outbox told once per line. Under the framework's store (a trial's own store
    too) a world with no line is refused: the owner sets its money figure before any paid job starts."""
    covering = covering_store(runner.store)
    line = guard.current(covering, runner.world.name)
    if line is None:
        if not covering.is_framework_store():
            return None  # a test's own store
        return (f"world {runner.world.name} has no stop line: the owner sets one before any paid job starts "
                f"(python -m score.review stop {runner.world.name} <euros> --reason \"...\")")
    spent = guard.spent_since(line["baseline"], months_since(line["baseline"], books_now()))
    flight = guard.in_flight({**open_overrides(covering), **held}, ledger().entries())
    why = guard.refusal(line, spent, flight, forecast)
    if why:
        guard.tell_owner(covering.cache.parent, f"{line['world']} stop of {line['at']}",
                         f"paid work held at EUR {spent:.2f} of the EUR {line['euros']:.2f} stop; {node} would have "
                         f"needed EUR {forecast:.2f} more. Free work goes on.")
    return why


def clearing(reservations):
    """One clearing at a time across every process: the lock beside the reservations file."""
    return locked(reservations.with_name("clearing.lock"))


def still_open(at, held, now):
    """True for a reservation not released whose run may still be going: its holder (the process in its `spending`
    block) is alive, or it is younger than a batch's longest run or its runaway limit (RUNAWAY times its high
    minutes), whichever is longer. Fault (2026-10-18 review): a run of several batches outlived its 4 h reservation
    and left the in-flight sum while it was still spending."""
    if held.get("holder") and guard.alive(held["holder"]):
        return True
    hours = max(ledger().BATCH_HOURS, guard.RUNAWAY * (held.get("high_minutes") or 0.0) / 60)
    return datetime.datetime.fromisoformat(at) > now - datetime.timedelta(hours=hours)


def open_reservations(reservations):
    """{clearance time: clearance} still open (still_open)."""
    found = json.loads(reservations.read_text()) if reservations.exists() else {}
    now = datetime.datetime.now(datetime.timezone.utc)
    return {at: held for at, held in found.items() if still_open(at, held, now)}


def keep_reservations(reservations, held):
    """Write the open reservations whole, so a reader never sees half a file."""
    partial = reservations.with_name(f"{reservations.name}.{os.getpid()}.partial")
    partial.write_text(json.dumps(held, indent=1))
    partial.replace(reservations)


def clearance(runner, node, euros):
    """Clear one paid run: the node's ticket ({node, key, after, clearance, reservations}) when the runner keys it (its
    inputs passed and stand accepted) and the month's ceiling has room for its forecast (run_forecast: measured, else
    the stage's estimate `euros`) over the ledger and every open reservation; the clearance kept in the store and its
    forecast reserved, under the clearing lock. Else Refused."""
    forecast = run_forecast(node, euros, runner.store)
    try:
        ticket = runner.ticket(node)
    except graph.Blocked as block:
        raise Refused(f"{node} is blocked: {block}") from block
    reservations = covering_store(runner.store).cache.parent / "reservations.json"
    with clearing(reservations):
        held = open_reservations(reservations)
        going = {**open_overrides(covering_store(runner.store)), **held}
        over = (month_refusal(forecast["euros"], sum(reserved["euros"] for reserved in going.values()))
                or stop_refusal(runner, node, forecast["euros"], held))
        if over:
            raise Refused(f"{node}: {over}")
        cleared = {"node": node, "key": ticket["key"], "euros": forecast["euros"], "minutes": forecast["minutes"],
                   "high_minutes": forecast["high_minutes"], "measured": forecast["measured"], "estimate": euros,
                   "by": RUNNER, "at": graph.now()}
        runner.store.write_clearance(node, ticket["key"], cleared)
        keep_reservations(reservations, {**held, cleared["at"]: {**cleared, "run": os.environ.get(RUN_ID)}})
    return {**ticket, "clearance": cleared, "reservations": str(reservations),
            "store": str(runner.store.cache.parent)}


def hold(ticket):
    """Mark a cleared run's reservation as held by this process, so it stays open while the process lives."""
    reservations = pathlib.Path(ticket["reservations"])
    with clearing(reservations):
        held = open_reservations(reservations)
        if ticket["clearance"]["at"] in held:
            held[ticket["clearance"]["at"]]["holder"] = guard.process_mark(os.getpid())
            keep_reservations(reservations, held)


def release(ticket):
    """End a cleared run's reservation: its cost is in the ledger now, or it never rented."""
    reservations = pathlib.Path(ticket["reservations"])
    with clearing(reservations):
        held = open_reservations(reservations)
        held.pop(ticket["clearance"]["at"], None)
        keep_reservations(reservations, held)


def release_run(reservations, run_id):
    """End every reservation a run's nodes still hold (`score run` stopped by a signal: its nodes never reached their
    own release); how many were ended. No run id ends none."""
    if not run_id:
        return 0
    with clearing(pathlib.Path(reservations)):
        held = open_reservations(pathlib.Path(reservations))
        kept = {at: reserved for at, reserved in held.items() if reserved.get("run") != run_id}
        keep_reservations(pathlib.Path(reservations), kept)
    return len(held) - len(kept)


def submit(runner, node, job_store, run, job, spec):
    """Put a cleared node's job in the job store (the existing contract); the job's key. The spec carries the run's
    estimate as `euros`. Refused while the month's books are unknown (require_books), before the job is written."""
    ticket = clearance(runner, node, spec.get("euros"))
    require_books(f"the job {run}/{job}")
    return job_contract.write_job(job_store, run, job, {**spec, "node": node, "node_key": ticket["key"]})


def batch_preflights(ticket):
    """The pre-flights the run's batches kept so far (tools/props/cloud/preflight.py)."""
    ledger()  # puts tools/props/cloud on the path
    import preflight
    return preflight.kept(ticket)


@contextlib.contextmanager
def spending(ticket):
    """Name a cleared ticket's run in this process and the processes it starts, for the rent points to find, its
    runaway watch beside it (guard.Watch, at its high forecast minutes); its reservation ends with the block."""
    before = {name: os.environ.get(name) for name in (TICKET, STORE)}
    os.environ[TICKET] = f"{ticket['node']} {ticket['key']}"
    if "reservations" in ticket:  # the store the clearance is in: a trial's own store (Store.in_folder) too
        os.environ[STORE] = ticket.get("store", str(pathlib.Path(ticket["reservations"]).parent))
        hold(ticket)
    folder = (pathlib.Path(ticket["reservations"]).parent if "reservations" in ticket else
              pathlib.Path(os.environ[STORE]) if os.environ.get(STORE) else Store.default().cache.parent)
    watch = guard.Watch(os.environ[TICKET], ticket.get("clearance", {}).get("high_minutes"), folder,
                        batches=lambda: batch_preflights(os.environ[TICKET]))
    try:
        with watch:
            yield
    finally:
        if "reservations" in ticket:
            release(ticket)
        for name, value in before.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def reservation_open(store, clearances):
    """True when one of a node and key's runner clearances still holds its reservation (its run is going)."""
    held = open_reservations(covering_store(store).cache.parent / "reservations.json")
    return any(cleared["at"] in held for cleared in clearances)


def require_books(what):
    """ledger.require_books with its refusal as Refused: nothing is ordered while the month's spend is unknown (both
    ledgers were lost on 2026-10-19); ledger.FreeOnly goes up as it is. Asked here rather than in google_spend.py or
    tools/cloud/runtime/submit.py: the first is in the surface rows' code version and the second in every job
    image's tag, so an edit there would buy those again."""
    books = ledger()
    try:
        books.require_books(what)
    except books.BooksUnknown as unknown:
        raise Refused(str(unknown)) from unknown


def require_cleared(what, store=None):
    """The runner's clearance (or the owner's override yes) for the run SCORE_SPEND_TICKET names; Refused when the
    variable is missing or names neither, or names a runner clearance whose run has ended (its reservation released
    or expired: an old ticket reused would start paid work no stop check and no in-flight sum ever saw). `what` says
    what was about to be rented. Every paid point asks this first (batch.rent, park, the cluster, the Google and World
    Labs callers), so it also refuses while the month's books are unknown, and raises ledger.FreeOnly in a process
    that runs free only (require_books)."""
    named = os.environ.get(TICKET, "").split()
    if len(named) != 2:
        raise Refused(f"{what}: nothing rents outside a cleared run. Run it through the runner (score.adapters "
                      f"compute or engines), or the owner's override (his yes under the node {OVERRIDE}, named "
                      f"here as {TICKET}=\"{OVERRIDE} <name>\")")
    node, key = named
    store = store or (Store.in_folder(os.environ[STORE]) if os.environ.get(STORE) else Store.default())
    cleared = store.clearances(node, key)
    found = cleared or [store.spend_yes(node, key)]
    if found[-1] is None:
        raise Refused(f"{what}: {TICKET} names {node} {key[:12]}, which the runner did not clear")
    if cleared and not reservation_open(store, cleared):
        raise Refused(f"{what}: {TICKET} names {node} {key[:12]}, whose cleared run has ended; a new run is cleared "
                      "by the runner afresh")
    require_books(what)
    return found[-1]
