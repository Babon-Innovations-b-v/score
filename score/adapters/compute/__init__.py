"""The compute adapter: the only way a paid node reaches the cloud, over the job contract tools/cloud already has.

    ticket = compute.clearance(runner, node, euros)  # refused unless the runner keys the node and its stop has room
    compute.submit(runner, node, job_store, run, job, spec)   # tools/cloud/runtime/submit.write_job, after clearance

Clearance comes from the framework, not from a typed yes (the owner's answer of 2026-10-11: his picks are made, from
concept and style on everything runs automatically, no spend limit, spend logically). A node is cleared when the
runner keys it, which it does only when every earlier node it reads passed its gates (unknown blocks) and stands
accepted (score.graph), when the month's books are known (ledger.books_refusal), and when the world's stop line (or a
benchmark grant) has room for the run's forecast; there is no month's ceiling (owner, 2026-10-20: a batch's own stop
is its high estimate plus 10%, set by his yes). The clearance is written to the store
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

Clearing is serialised, as lines run side by side (score.graph's drive): the stop check and the clearance are
made under one lock (`clearing.lock` beside the store), and every clearance holds a reservation of its estimate
(`reservations.json` beside it) until its run ends (`spending` releases it, and holds it open while its process
lives), or, for one handed to a job store, until a batch's longest run (the ledger's BATCH_HOURS) or its runaway limit
has passed. A trial's own store inside the home (compare.py's) is covered by the framework store: its paid jobs are
checked against the world's stop line and reserved beside the framework store, so they count in flight. The stop
check counts the open reservations with what was spent, so two lines can never both spend the stop's last euros.

The world's stop line (guard.py, owner 2026-10-18) is checked under the same lock: a paid job is refused before it
starts when its forecast, with the world's spend since its first line and every run in flight, would pass the line;
a started job is never stopped as the bill nears it, only a runaway past twice its forecast minutes.

The owner's override, an extra route he may use and never a requirement, is his yes for a run outside the runner:
he gives it from his own terminal for a name of his choosing (the review command's spend, node `override`, key
<name>, at his euros), and the run carries SCORE_SPEND_TICKET="override <name>"; an override yes counts in flight for
a batch's longest run. A rent point checks that the yes exists, or that the clearance's run still holds its
reservation; the ledger's own batch limits still apply there. A barrier, not a lock: an agent can name a
clearance given earlier, and every clearance names its node, key, estimate and time.

A benchmark grant (the owner's standing rule of 2026-10-20, root CLAUDE.md) is his yes, in a Claude Code session, to
benchmark batches of at most GRANT_EUROS in all: the session asks him, and on his yes writes it with
`grant_benchmark` (his answer and the question quoted, the time, 24 h). A batch is a `score run` tagged with the grant
(SCORE_BENCHMARK_GRANT=<grant id>); its paid nodes are cleared by the runner as any other, their inputs passed and
the books asked as ever, with the grant's balance standing in for the world's stop line (owner, 2026-10-22: it holds
its euros until they are spent): each clearance holds its high plus 10% of the balance (`grants/holds/`), and when
its run ends, finished or failed, draws its real spend instead (`grants/draws/`, each with the balance after it). The
grant is done when its balance runs out or it expires, never because a run ended. Nothing else spends through a grant.
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
from score.store import PROPS_HOME, RUNNER, Store, locked, running_under_agent, stamp_key

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tools/cloud/runtime"))
import submit as job_contract  # noqa: E402

TICKET = "SCORE_SPEND_TICKET"
# Each paid stage's measured cost of one unit of its work, with the ledger lines it rests on (tools/costs/per_unit.py).
PER_UNIT = REPO / "data/costs/per-unit.json"
# The forecast rules whose 0 is a count, not an unknown: the sound takes still to make (every take a place plays
# stands made, or another place's line makes it first), so its make reads cached takes at EUR 0 (#10).
COUNTED_ZERO = ("sound_takes",)
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
BENCHMARK = "benchmark"
# A benchmark batch's tag, on its `score run`: the id of the owner's grant it spends under (grant_benchmark).
GRANT = "SCORE_BENCHMARK_GRANT"
GRANT_EUROS = 20.0  # the most one benchmark grant allows (owner, 2026-10-20); more needs his cockpit click
GRANT_HOURS = 24
GRANTS = "grants"  # grants/benchmark/<id>.json, grants/holds/<id>/<time>.json, grants/draws/<id>/<time>.json
GRANT_BUFFER = 1.10  # a job under a grant holds its high plus 10% of the balance (owner, 2026-10-22)
# A scene inventory reading (score/review/reading.py) is cleared under the owner's standing allowance, no yes asked.
READING = "inventory-read"
READING_RULE = "scene inventory readings run without asking (owner, 2026-10-21, root CLAUDE.md)"
READING_GEMINI_EUROS = 0.05  # google_spend's estimate of one Gemini 3.1 Pro ask, until a reading is measured
READING_EUROS = 1.0  # the most one place's reading is cleared at under the allowance; more is no reading
READING_MINUTES = 30.0  # its high minutes (a cold SAM 3 card's set-up and the asks), the runaway watch's base
# A plan writing (score/review/plan_writing.py) is cleared the same way, under the same allowance and limit a place.
PLAN_WRITING = "plan-write"
PLAN_RULE = "plan writing runs without asking (owner, 2026-10-21, root CLAUDE.md)"
ALLOWANCES = {READING: READING_RULE, PLAN_WRITING: PLAN_RULE}


def judge_timeout():
    """The seconds a judge's answer is waited on, read when the call is made."""
    return float(os.environ.get(JUDGE_TIMEOUT, JUDGE_TIMEOUT_SECONDS))


class Refused(Exception):
    """A paid run is refused: its node is blocked, the month's books are unknown, or its stop has no room for it."""


def ledger():
    """tools/props/cloud/ledger.py, the batch limits, the books and what the month has cost."""
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


def books_refusal():
    """Why no paid run may clear now, or None: refused outright in a process that runs free only (ledger.FreeOnly),
    and while the month's books are not known (ledger.books_refusal: both ledgers were lost on 2026-10-19, and a
    missing ledger read as EUR 0). With a Google billing export set, both bills are read back into the books first
    (read_back_books). There is no month's ceiling (owner, 2026-10-20)."""
    books = ledger()
    books.refuse_free_only("a paid run")
    if google_bill_set():
        read_back_books()
    return books.books_refusal()


# The provider's bill over the cloud ledger's sum for 2026-10 up to 2026-10-10 (EUR 627.74 against 547.31: disks,
# addresses, storage and registry the ledger misses; paper/evidence/cloud/cost-tables-2026-10.txt): what a card or
# processor stage's ledger euros come to on the bill. Applied here only (ADR-0006), to every per-unit price.
BILL_SHARE = 627.74 / 547.31
GOOGLE = "google calls"  # a per-unit entry's source of Google calls: billed as the ledger says, no bill share


def bill_share(entry):
    """The share a per-unit entry's ledger euros are billed at: 1 for Google calls, else BILL_SHARE."""
    return 1.0 if GOOGLE in (entry.get("sources") or {}) else BILL_SHARE


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
    share = bill_share(entry)
    return {"likely_euros": round(entry["likely_euros"] * units * share, 4),
            "high_euros": round(entry["high_euros"] * units * share, 4), "unit": entry["unit"], "units": units,
            "unit_likely_euros": entry["likely_euros"], "unit_high_euros": entry["high_euros"], "runs": entry["runs"],
            "bill_share": round(share, 4)}


def run_forecast(node, euros, store=None, units=None):
    """A paid node's run forecast ({euros, minutes, high_minutes, measured}): its stage's measured runs in the cloud
    ledger at their high euros, likely and high minutes (tools/props/cloud/preflight.py), else its measured per-unit
    high times its units (unit_price, on `store`) with no minutes, else its measured per-unit high times the `units`
    its forecast rule counted (forecast_price, as the run's plan prices it, so a stop line set on the plan rests on
    the same measured figures) with their unit minutes, else the stage's own estimate `euros` with no minutes;
    Refused with none. The runner's numbers, never an agent's: the owner, 2026-10-18."""
    books = ledger()
    import preflight  # beside ledger.py
    run = preflight.node_run(books.entries(), node.partition("@")[0])
    if run:
        return {"euros": round(run["high_euros"], 4), "minutes": round(run["minutes"], 2),
                "high_minutes": round(run["high_minutes"], 2), "measured": run["runs"]}
    unit = unit_price(node, store)
    if unit:
        return {"euros": unit["high_euros"], "minutes": None, "high_minutes": None, "measured": unit["runs"]}
    planned = forecast_price(node, units)
    if planned:
        timed = unit_minutes(node.partition("@")[0], units)
        return {"euros": planned["high_euros"], "minutes": timed.get("likely_minutes"),
                "high_minutes": timed.get("high_minutes"), "measured": planned["runs"]}
    if euros is None:
        raise Refused(f"{node}: a paid run needs its estimate in euros, or measured runs of its stage in the ledger, "
                      "before the runner can clear it")
    return {"euros": euros, "minutes": None, "high_minutes": None, "measured": 0}


def forecast_price(node, units):
    """A paid node priced per unit before it is made: its own stage's measured per-unit euros (PER_UNIT, never an
    `also` stage's) times the `units` its stage's forecast rule counted ({likely_euros, high_euros, unit, units,
    unit_likely_euros, unit_high_euros, runs, unit_source}), or None when the stage has no measured unit or no
    forecast rule, or no units were counted (none, or 0: nothing counted is unknown, never free; but a rule whose 0
    is a count, COUNTED_ZERO, prices its 0 at EUR 0)."""
    stage = node.partition("@")[0]
    entry = per_unit(stage)
    if entry is None or entry["stage"] != stage or not entry.get("forecast") or not counted(entry, units):
        return None
    share = bill_share(entry)
    return {"likely_euros": round(entry["likely_euros"] * units * share, 4),
            "high_euros": round(entry["high_euros"] * units * share, 4), "unit": entry["unit"], "units": units,
            "unit_likely_euros": entry["likely_euros"], "unit_high_euros": entry["high_euros"], "runs": entry["runs"],
            "unit_source": entry["forecast"]["source"], "bill_share": round(share, 4)}


def counted(entry, units):
    """Whether `units` are a count under the per-unit entry's forecast rule: any above 0, and 0 for a rule whose 0 is
    a count (COUNTED_ZERO)."""
    return bool(units) or (units == 0 and entry["forecast"]["rule"] in COUNTED_ZERO)


def unit_minutes(stage, units):
    """How long `units` units of `stage` keep the run, on its measured time (PER_UNIT's `time`, the same ledger lines
    as its euros) by the runner's own card rule (tools/props/cloud/preflight.py cards_for and minutes_for, capped at
    capacity.run_cap; the high minutes on the high job time and the high set-up): {likely_minutes, high_minutes,
    cards} (cards None for a stage of calls), or {minutes_why} when its time or set-up is unmeasured or no units were
    counted."""
    entry = per_unit(stage)
    time = (entry or {}).get("time") or {}
    if units == 0:
        return {"likely_minutes": 0.0, "high_minutes": 0.0, "cards": 0}  # nothing to make keeps no card
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
    its stage's forecast rule (the gaps' price: a node in a gap's chain is made again, with what the gap adds),
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
    VAT is not known (the bill factor is unsettled; once settled it is applied here, in the runner, and nowhere
    else: ADR-0006)."""
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


def owners_google_month(euros, by=None):
    """The owner's figure for what Google billed this month before the Google ledger began again, an override of the
    bill read from Google's billing export (read_back_books): the books' known state; the books, with who gave it
    (`by`, his signed-in name from the cockpit; None from his terminal) and when. Refused in a process an agent
    started (only the owner knows the Google bill) and for a figure that is not finite and at least 0 (`nan` passed
    every ceiling, a negative one lowered the month)."""
    if running_under_agent():
        raise Refused("the Google month is the owner's figure: he enters it on the cockpit's money card")
    return write_google_month(google_figure(euros), by)


def google_figure(euros):
    """`euros` as a Google month figure; Refused when it is not finite and at least 0."""
    figure = ledger().euro_figure(euros)
    if figure is None:
        raise Refused(f"the Google month must be a finite figure of at least EUR 0, not {euros!r}")
    return figure


def write_google_month(figure, by):
    """Write the owner's Google month `figure` into the books, their known state, with who gave it; the books."""
    books = ledger()
    known = {**books.this_months_books(), "month": books.this_month(), "state": "known", "google_before": figure,
             "google_at": graph.now(), "google_by": by}
    books.write_books(known)
    return known


def grant_benchmark(answer, question, euros, purpose=BENCHMARK, google_month=None, store=None):
    """Record the owner's yes, given in a Claude Code session, to one benchmark batch of at most GRANT_EUROS (his
    standing rule of 2026-10-20): the grant {id, purpose, euros, answer, question, at, expires, google_month}, kept once in the store (`grants/benchmark/<id>.json`). Refused for any purpose but a benchmark, a
    figure over GRANT_EUROS or not above 0, or the answer or the question not quoted. A Google month figure he gave in
    the same answer goes into the books as his own (owners_google_month's books)."""
    if purpose != BENCHMARK:
        raise Refused(f"a grant covers a benchmark only, not {purpose!r}: anything else needs the owner's cockpit click")
    figure = ledger().euro_figure(euros)
    if not figure or figure > GRANT_EUROS:
        raise Refused(f"a benchmark grant is above EUR 0 and at most EUR {GRANT_EUROS:.0f}, not {euros!r}: more needs "
                      "the owner's cockpit click")
    if not str(answer or "").strip() or not str(question or "").strip():
        raise Refused("a benchmark grant quotes the owner's answer and the question he answered, both")
    google = None if google_month is None else google_figure(google_month)
    at = graph.now()
    expires = datetime.datetime.fromisoformat(at) + datetime.timedelta(hours=GRANT_HOURS)
    grant = {"id": stamp_key(at), "purpose": BENCHMARK, "euros": figure, "answer": str(answer),
             "question": str(question), "at": at, "expires": expires.isoformat(timespec="microseconds"),
             "google_month": google}
    covering_store(store or Store.default()).write_once(f"{GRANTS}/{BENCHMARK}/{grant['id']}.json", grant)
    if google is not None:
        write_google_month(google, f"the owner's answer, benchmark grant {grant['id']}")
    return grant


def grant_balance(store, grant_id, held):
    """What grant `grant_id` has left: its euros less every draw written and every hold whose run is still open in
    `held` (the open reservations) and drew nothing yet."""
    grant = store.read(f"{GRANTS}/{BENCHMARK}/{grant_id}.json")
    drawn = grant_draws(store, grant_id)
    holding = sum(hold["reserved"] for hold in grant_holds(store, grant_id)
                  if hold["at"] in held and not any(draw["at"] == hold["at"] for draw in drawn))
    return round(grant["euros"] - sum(draw["euros"] for draw in drawn) - holding, 6)


def grant_holds(store, grant_id):
    """The holds clearances took on grant `grant_id`, oldest first."""
    return [store.read(key) for key in sorted(store.objects.keys(f"{GRANTS}/holds/{grant_id}/"))]


def grant_draws(store, grant_id):
    """The draws written on grant `grant_id` (each a run's real spend, or a late part of it), oldest first."""
    return [store.read(key) for key in sorted(store.objects.keys(f"{GRANTS}/draws/{grant_id}/"))]


def grant_refusal(store, grant_id, forecast, held):
    """Why a benchmark batch's paid job at a high `forecast` of euros may not spend under grant `grant_id`, or None:
    the grant must be a benchmark's, quoted, at most GRANT_EUROS, not expired, spent by a `score run`, not used up under
    the single-use rule of before 2026-10-22 unless the owner had it restored (restore_grant), and its high plus
    GRANT_BUFFER must fit in its balance (grant_balance, once the runs that ended drew: settle_grant)."""
    grant = store.read(f"{GRANTS}/{BENCHMARK}/{grant_id}.json")
    if grant is None:
        return f"{GRANT} names {grant_id}, which is no benchmark grant"
    if (grant.get("purpose") != BENCHMARK or not grant.get("answer") or not grant.get("question")
            or not 0 < grant.get("euros", 0) <= GRANT_EUROS):
        return f"grant {grant_id} is not a quoted benchmark grant of at most EUR {GRANT_EUROS:.0f}"
    if datetime.datetime.now(datetime.timezone.utc) >= datetime.datetime.fromisoformat(grant["expires"]):
        return f"grant {grant_id} expired at {grant['expires'][:16]}; the owner is asked again"
    if not os.environ.get(RUN_ID):
        return f"grant {grant_id}: a benchmark batch spends as one score run"
    if store.read(f"{GRANTS}/used/{grant_id}.json") and not store.read(f"{GRANTS}/restored/{grant_id}.json"):
        return f"grant {grant_id} was used up under the single-use rule of before 2026-10-22"
    settle_grant(store, grant_id, held)
    balance = grant_balance(store, grant_id, held)
    if forecast * GRANT_BUFFER > balance:
        return (f"grant {grant_id}: EUR {balance:.2f} left, and this job's high of EUR {forecast:.2f} plus 10% "
                "would pass it")
    return None


def hold_grant(store, grant_id, cleared, held):
    """Hold a clearance's high plus GRANT_BUFFER on its grant until its run ends and draws its real spend."""
    reserved = round(cleared["euros"] * GRANT_BUFFER, 6)
    store.write_once(f"{GRANTS}/holds/{grant_id}/{stamp_key(cleared['at'])}.json",
                     {"node": cleared["node"], "key": cleared["key"], "run": os.environ.get(RUN_ID),
                      "high": cleared["euros"], "reserved": reserved, "at": cleared["at"],
                      "balance": round(grant_balance(store, grant_id, held) - reserved, 6)})


def settle_grant(store, grant_id, held):
    """Write a draw for each hold on grant `grant_id` whose run has ended (not in `held`, the open reservations): its
    real spend (run_spend) less what it drew already, so a batch line ledgered after its run (a parked card, a disk)
    draws later. A run that failed draws what it spent, never the rest of its hold."""
    drawn = grant_draws(store, grant_id)
    for hold in grant_holds(store, grant_id):
        if hold["at"] in held:
            continue
        before = [draw for draw in drawn if draw["at"] == hold["at"]]
        until = before[0]["until"] if before else graph.now()
        spend = run_spend(store, hold, until)
        due = round(spend["euros"] - sum(draw["euros"] for draw in before), 6)
        if before and due <= 0.00005:
            continue
        draw = {"node": hold["node"], "key": hold["key"], "run": hold.get("run"), "at": hold["at"], "until": until,
                "spend": spend, "euros": due, "balance": round(grant_balance(store, grant_id, held) - due, 6)}
        store.write_once(f"{GRANTS}/draws/{grant_id}/{stamp_key(graph.now())}-{stamp_key(hold['at'])}.json", draw)
        drawn.append(draw)


# The Gemini callers of a stage whose ledger lines carry another name than the stage's (google_spend's `caller`).
GOOGLE_CALLERS = {"closeup": ("pro",), READING: ("inventory-reading",), PLAN_WRITING: ("plan-writing", "plan-drawing")}


def run_spend(store, hold, until):
    """A cleared run's real spend ({euros, cloud, google}): its cloud ledger lines by its ticket started from its
    clearance until the node and key's next clearance (a later run of it), and the Gemini calls its stage made from
    its clearance to `until` at google_spend's own count (a call never finished at its estimate). Google's ledger
    names no ticket, so its stage's calls in that time count as its own: two places of one stage under one grant at
    once each count the other's too (over, never under)."""
    books = ledger()
    import google_spend  # beside ledger.py
    later = [cleared["at"] for cleared in store.clearances(hold["node"], hold["key"]) if cleared["at"] > hold["at"]]
    ticket, since, before = f"{hold['node']} {hold['key']}", hold["at"][:19], min(later, default="9")[:19]
    cloud = sum(entry.get("euros", 0.0) for entry in books.entries()
                if entry.get("ticket") == ticket and since <= entry.get("started", "")[:19] < before)
    stage = hold["node"].partition("@")[0]
    callers = GOOGLE_CALLERS.get(stage, (stage,))
    start, end = (datetime.datetime.fromisoformat(moment) for moment in (hold["at"], until))
    lines = ([json.loads(line) for line in google_spend.LEDGER.read_text().splitlines() if line.strip()]
             if google_spend.LEDGER.exists() else [])
    lines = [line for line in lines if line.get("caller") in callers
             and start <= datetime.datetime.fromisoformat(line["time"]) <= end]
    finished = {line.get("call") for line in lines if line.get("state", "finished") == "finished"}
    google = (sum(google_spend.estimate(line["model"]) if line.get("euros") is None else line["euros"]
                  for line in lines if line.get("state", "finished") == "finished")
              + sum(line.get("estimate", 0.0) for line in lines
                    if line.get("state") == "started" and line.get("call") not in finished))
    return {"euros": round(cloud + google, 6), "cloud": round(cloud, 6), "google": round(google, 6)}


def restore_grant(grant_id, answer, question, store=None):
    """Apply the owner's yes of 2026-10-22 (a grant holds its euros until they are spent) to a grant used up under the
    single-use rule before it: each clearance it made then draws its real spend (run_spend, to now), and the restore
    {id, answer, question, at, balance} is kept beside the grant (`grants/restored/<id>.json`). Refused for no grant
    still standing, one not used up, or the answer or the question not quoted."""
    store = covering_store(store or Store.default())
    grant = store.read(f"{GRANTS}/{BENCHMARK}/{grant_id}.json")
    if grant is None or datetime.datetime.now(datetime.timezone.utc) >= datetime.datetime.fromisoformat(
            grant["expires"]):
        raise Refused(f"{grant_id} is no benchmark grant still standing")
    used = store.read(f"{GRANTS}/used/{grant_id}.json")
    if used is None:
        raise Refused(f"grant {grant_id} was not used up under the single-use rule: it holds its balance already")
    if not str(answer or "").strip() or not str(question or "").strip():
        raise Refused("a restore quotes the owner's answer and the question he answered, both")
    with clearing(store.cache.parent / "reservations.json"):
        for key in sorted(store.objects.keys(f"{GRANTS}/spent/{grant_id}/")):
            cleared = store.read(key)
            store.write_once(f"{GRANTS}/holds/{grant_id}/{stamp_key(cleared['at'])}.json",
                             {**cleared, "run": used["run"], "high": cleared["euros"], "reserved": cleared["euros"],
                              "balance": None})
        settle_grant(store, grant_id, {})
        restored = {"id": grant_id, "answer": str(answer), "question": str(question), "at": graph.now(),
                    "balance": grant_balance(store, grant_id, {})}
        store.write_once(f"{GRANTS}/restored/{grant_id}.json", restored)
    return restored


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
    inputs passed and stand accepted), the month's books are known (books_refusal) and the world's stop line has room
    for its forecast (run_forecast: measured, else the stage's estimate `euros`) with every open reservation; the
    clearance kept in the store and its
    forecast reserved, under the clearing lock. A benchmark batch (GRANT set) is checked against its grant instead of
    the world's stop line (grant_refusal), and its clearance counted against the grant. Else Refused."""
    from score.stages.complete.gaps import price  # the units the run's plan prices it by
    forecast = run_forecast(node, euros, runner.store,
                            price.planned_units(node, runner.world.roots.get("data"), runner.store))
    grant_id = os.environ.get(GRANT)
    try:
        ticket = runner.ticket(node)
    except graph.Blocked as block:
        raise Refused(f"{node} is blocked: {block}") from block
    reservations = covering_store(runner.store).cache.parent / "reservations.json"
    with clearing(reservations):
        held = open_reservations(reservations)
        over = (books_refusal()
                or (grant_refusal(covering_store(runner.store), grant_id, forecast["euros"], held) if grant_id else
                    stop_refusal(runner, node, forecast["euros"], held)))
        if over:
            raise Refused(f"{node}: {over}")
        cleared = {"node": node, "key": ticket["key"], "euros": forecast["euros"], "minutes": forecast["minutes"],
                   "high_minutes": forecast["high_minutes"], "measured": forecast["measured"], "estimate": euros,
                   "by": RUNNER, "at": graph.now(), **({"grant": grant_id} if grant_id else {})}
        if grant_id:
            hold_grant(covering_store(runner.store), grant_id, cleared, held)
        runner.store.write_clearance(node, ticket["key"], cleared)
        keep_reservations(reservations, {**held, cleared["at"]: {**cleared, "run": os.environ.get(RUN_ID)}})
    return {**ticket, "clearance": cleared, "reservations": str(reservations),
            "store": str(runner.store.cache.parent)}


def reading_clearance(store, places, euros, node=READING):
    """Clear one scene inventory reading run of `places` (score/review/reading.py), or with `node` PLAN_WRITING one
    plan writing run (score/review/plan_writing.py), at its forecast `euros`, under the owner's standing allowance
    (ALLOWANCES: they run with no separate yes) or, when GRANT names one, against that benchmark grant; the ticket
    ({node, key, clearance, reservations, store}), kept and reserved like the runner's, so require_cleared passes
    inside its `spending` block and the run counts in flight. The month's books are asked as ever. Refused for any
    node but those, above READING_EUROS a place, or what the grant refuses."""
    grant_id = os.environ.get(GRANT)
    if node not in ALLOWANCES:
        raise Refused(f"{node}: no standing allowance covers it")
    if not places or euros > READING_EUROS * len(places):
        raise Refused(f"{node}: a reading of {len(places)} places at EUR {euros:.2f} is outside the allowance of "
                      f"EUR {READING_EUROS:.2f} a place")
    covering = covering_store(store)
    reservations = covering.cache.parent / "reservations.json"
    with clearing(reservations):
        held = open_reservations(reservations)
        over = books_refusal() or (grant_refusal(covering, grant_id, euros, held) if grant_id else None)
        if over:
            raise Refused(f"{node}: {over}")
        at = graph.now()
        cleared = {"node": node, "key": stamp_key(at), "euros": euros, "minutes": READING_MINUTES,
                   "high_minutes": READING_MINUTES, "measured": False, "estimate": euros, "places": list(places),
                   "by": f"allowance: {ALLOWANCES[node]}", "at": at, **({"grant": grant_id} if grant_id else {})}
        if grant_id:
            hold_grant(covering, grant_id, cleared, held)
        store.write_clearance(node, cleared["key"], cleared)
        keep_reservations(reservations, {**held, at: {**cleared, "run": os.environ.get(RUN_ID)}})
    return {"node": node, "key": cleared["key"], "clearance": cleared, "reservations": str(reservations),
            "store": str(store.cache.parent)}


def hold(ticket):
    """Mark a cleared run's reservation as held by this process, so it stays open while the process lives."""
    reservations = pathlib.Path(ticket["reservations"])
    with clearing(reservations):
        held = open_reservations(reservations)
        if ticket["clearance"]["at"] in held:
            held[ticket["clearance"]["at"]]["holder"] = guard.process_mark(os.getpid())
            keep_reservations(reservations, held)


def release(ticket):
    """End a cleared run's reservation: its cost is in the ledger now, or it never rented. A run under a benchmark
    grant draws its real spend from the grant (settle_grant)."""
    reservations = pathlib.Path(ticket["reservations"])
    with clearing(reservations):
        held = open_reservations(reservations)
        held.pop(ticket["clearance"]["at"], None)
        keep_reservations(reservations, held)
        if ticket["clearance"].get("grant"):
            settle_grant(Store.in_folder(reservations.parent), ticket["clearance"]["grant"], held)


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
