"""tools/costs' invariant: every euro is ledgered before it is spent, measured before it prices, and adds up to the bill.

One test asks it of small worlds written here, each driven once through the code's entry points, and compares every
measure taken on them with its expected value in `EXPECTED` (a failure names the measure):
- costs.py (`paper:` and `day:` measures, the paper's tables and the day's alarm): the ledgers add up to the bill. The
  paper's reconciliation is the ledger rows before the read plus every part of the bill the ledger misses (storage,
  unledgered compute), each figure worked out by hand from the ledger and bill written here (no cloud, no evidence
  files); an engine run is typed by its price, a processor machine priced again by the started hour, R&D and
  production cover the ledger, order lines change no table; the day's alarm (`reconcile-day`, run as a command on the
  rows of `DAYS`) fails when a ledgered line is over 5% off its bill and names the provider, fails on an empty or
  partial bill and on a missing ledger (faults of the review of C1, 2026-10-17), counts a run across midnight by its
  share and a machine still running at its price, and keeps storage and other lines out of the gap; `today` is the
  bill less the last read before the day; local roots never reach the paper's copy.
- per_unit.py (`unit:` measures): every per-unit price and time rests on measured lines only (owner, 2026-10-18 and
  2026-10-20: never a flat guess). A batch is read once and priced over the units it finished (one that finished
  nothing left out); a line is the stage its ticket names; a Google unit is a finished call; likely the median, high
  the 90% quantile; a stage with no lines is left out, a time no line holds is a `why`, never a 0; a recorded stage is
  priced from its runs in git; the warm stages are their measured work at the bill's price plus the overhead, a batch
  stage half its standard calls; and the modes that write in place keep what they do not measure (`--times-only`
  leaves every euro of the repository's own file byte-identical, #14). Ledgers are written in the test, plus the
  paper's public ledger copy.
- Paid calls only through the clients that write a ledger line before the call (`lint:` measures; the owner's rule,
  tools/cloud/CLAUDE.md "Paid calls only through the ledgered clients"; 2026-10-17: a Google day billed about EUR 520
  the ledger never held, and 21% of the bill was in no ledger row): a Gemini call through google_spend.generate, a
  Scaleway machine, disk, address or cluster pool through the backends that batch.rent and the cluster set-up drive;
  any other module that calls Gemini directly or orders one of those fails. A wording check by design, guarding that
  owner rule; the lint's own reading is pinned on the fixtures of `LINT_CASES`, whose paid lines are counted by hand.
  Read from each tracked Python file's syntax tree (its imports, by statement or by importlib.import_module or
  __import__ given a string; its strings joined with + and f-strings; and the scw words a call is given, read through
  variables, joined and starred lists, .append, .extend and .insert), and from the lines of every other runnable file
  (shell and other scripts, Makefiles, Dockerfiles, manifests, a #! file with no suffix), a line ending in a backslash
  joined with the next; vendor/ is third-party, and docs and data run nothing, so both are left out. A variable is
  read as the function it is in set it, in source order, and every setting or growing of one is checked too, so an
  order built in one branch counts. A word it cannot read (a function's parameter) between a product and "create"
  still counts as an order. It does not follow words across modules, through other functions' return values, through
  attributes (self.cmd), lists indexed or sliced, an .insert at an index it cannot read (read as the end), or built
  with % or .format.

No cloud, no machine; each file the test writes is in the run's own temp folder.

Breaks (each applied once, seen red, reverted, 2026-11-13; the measures named are those that went red), in costs.py:
- `scrub` leaves the `$PROPS` root unreplaced -> paper: scrub keeps only the public roots.
- `untyped_kinds` reads every row as inferred -> paper: a row without kind is tagged pixal.
- `month_rows` without `< before` (the late row counted) -> paper: the bill is the ledger and what it misses,
  paper: R&D and production cover the ledger.
- `outside_compute` counts Storage as compute -> paper: the bill is the ledger and what it misses.
- `engine_type` by the exact minute, not the started one -> paper: an engine run is typed by its price, paper: an
  engine run group names its card type, paper: processor machines priced again by the started hour.
- `per_product` prices processor types by the minute -> paper: processor machines priced again by the started hour.
- `is_rnd` without the `RND_WHO` rule -> paper: R&D and production cover the ledger.
- `types_before` drops the euros beyond the machines -> paper: euros beyond the machines are not split.
- `today_line` does not subtract the baseline -> paper: today is the bill less the last read before the day.
- `cloud_since` keeps rows from before `since`; `google_tracks` leaves out a started call never finished ->
  paper: spend since splits by track.
- `DAY_TOLERANCE` 0.15 -> day: eleven percent off fails and names the provider; 0.03 -> day: within five percent
  passes.
- `failed` lets a missing bill pass (its gaps read as none) -> day: an empty bill fails, day: a bill without
  scaleway fails, day: no read before the day is no bill.
- `bill_line_of` reads disks and addresses as other -> day: eleven percent off fails and names the provider.
- `snapshot_day_bill` takes the day's first read, or no read before the day as an empty start -> day: the scaleway
  day comes from the saved reads, day: no read before the day is no bill.
- `cloud_window_lines` counts a run whole on its start day -> day: a run across midnight counts its share; leaves the
  open rents out -> day: a machine still running counts at its price.
- `day_report_line` reports no unledgered lines -> day: storage and other lines never alarm.
- `ledger_lines_of` reads a missing ledger as empty -> day: no cloud ledger fails as missing, day: no google ledger
  fails as missing.
- `run_rows` without the order lines filter (`ledger.ORDER_LINES`) -> paper: order lines change no reconciliation,
  paper: order lines change no table.

Breaks (each applied once, seen red, reverted, 2026-11-13), in per_unit.py:
- `ledger_lines` reads a batch in two ledgers twice -> unit: a batch in two ledgers is read once, unit: pixal priced
  over the units each batch finished.
- `cloud_measures` keeps a batch that finished no unit (its euros over one unit) -> unit: pixal priced over the
  units each batch finished, unit: the measured file.
- `of_spec` reads a ticketed line by its fields -> unit: a line ticketed for tiles is no bake's; `line_units` without
  `SOUND_TAKES` -> unit: an older sound line over its recorded takes; `warm_entry` ignores the stage's own jobs ->
  unit: --add prices a warm stage on its own timed jobs.
- `google_measures` counts a started call -> unit: google units are finished calls.
- `measure` keeps a stage with no lines -> unit: stages with no lines are left out; `per_model` inverted (models over
  units) -> unit: the measured file.
- `recorded` leaves a run's euros not over its units -> unit: a recorded stage is priced from its runs.
- `forecast` leaves the `one` rule's source empty -> unit: stages without a forecast rule and source.
- `with_rules` rebuilds a measured stage bare -> the test errors (KeyError: 'settle') before its measures compare.
- `in_machine_setup` does not divide the jobs by the jobs at once -> unit: a pixal batch's time from the paper's line.
- `cloud_times` writes a set-up no line timed as 0 -> unit: a stage whose lines time no set-up says so.
- `unit_seconds` leaves the slots out -> unit: a line's seconds by its working minutes and slots.
- `kept_times` replaces a measured time with a why -> the test errors (KeyError: 'unit_seconds') at that measure.
- `google_times` counts no failed call; `in_flight` counts a call twice; `batch_job_time` times a Batch API row as
  calls -> unit: a google stage's time from its calls, unit: a Batch API row is unmeasured.
- `spread`'s likely the max, not the median -> unit: node minutes are the store's finish records (and the time
  measures).
- `warm_price` without `OVERHEAD` -> unit: a warm stage at the bill's price plus the overhead, and unit: --times-only
  keeps every euro.
- `batch_entry` at the full standard price -> unit: a batch stage is half its standard calls, and unit: --times-only
  keeps every euro.
- `with_times` drops `likely_euros` -> unit: --times-only keeps every euro.

Breaks (each applied once, seen red, reverted, 2026-11-13), in this file's lint:
- `PAID_TEXT` without Google's host -> lint: a module calling gemini directly.
- `paid_module` without `GEMINI_MODULES` -> lint: a module loading google's client.
- `SCW_PAID` without ("instance", "server") -> lint: a module ordering a scaleway machine or disk (and the order rows).
- `sequence_words` reads no variable -> lint: an order built before its call, lint: a name two functions use.
- `joined_text` reads no f-string -> lint: an address joined from strings; no `+` join -> that row and lint: a name
  two functions use.
- `GROW_ARGUMENTS` without append and extend -> lint: an order grown by append or extend; without insert -> lint: an
  order put together with insert.
- `scw_orders` does not check a setting's words -> lint: an order grown in one branch.
- `DYNAMIC_IMPORTS` empty -> lint: google's client loaded by name.
- `logical_lines` joins no backslash line -> lint: a shell order broken over lines.
- `runnable` Python and shell only -> lint: a Makefile, lint: a manifest, lint: a #! script.
- `orders_in` without the unread-word rule -> lint: an order whose resource is a parameter; reading delete as an
  order -> lint: reading and deleting.
- `outside_allowed` allows every top-level part -> lint: an allowed file orders only in its named parts.
- `ALLOWED` without tools/cloud/google_spend.py -> lint: the repository's paid calls outside the ledgered clients.
"""
import ast
import concurrent.futures
import datetime
import json
import multiprocessing
import pathlib
import re
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
import costs  # noqa: E402
import per_unit  # noqa: E402


class Text:
    """An expected text: it holds every one of `has`, none of `lacks`, and matches every pattern of `matches` (a line
    of it, re.M)."""

    def __init__(self, has=(), lacks=(), matches=()):
        self.has, self.lacks, self.matches = has, lacks, matches

    def holds(self, value):
        return (all(text in value for text in self.has) and not any(text in value for text in self.lacks)
                and all(re.search(pattern, value, re.M) for pattern in self.matches))

    def __repr__(self):
        return f"Text(has={self.has}, lacks={self.lacks}, matches={self.matches})"


class Between:
    """An expected number above `low` and at most `high`."""

    def __init__(self, low, high):
        self.low, self.high = low, high

    def holds(self, value):
        return self.low < value <= self.high

    def __repr__(self):
        return f"between {self.low} (out) and {self.high}"


class Near:
    """An expected number within `tolerance` of `target`."""

    def __init__(self, target, tolerance):
        self.target, self.tolerance = target, tolerance

    def holds(self, value):
        return abs(value - self.target) <= self.tolerance

    def __repr__(self):
        return f"{self.target} within {self.tolerance}"


def holds(expected, value):
    """Whether a measure's value is what its row expects: the matcher's own judgement, else equal."""
    return expected.holds(value) if hasattr(expected, "holds") else value == expected


# --- the paper's world: a month's ledger and its bill ---

READ = "2026-10-10T01:36Z"


BILL = [
    {"category_name": "Compute", "product_name": "L4", "sku": "/instance/server/l4_1_24g/fr-par-2",
     "unit": "minute", "billed_quantity": "60", "euros": 0.7875},
    {"category_name": "Compute", "product_name": "POP2-32C-128G", "sku": "/instance/server/pop2_32c_128g/pl-waw-2",
     "unit": "minute", "billed_quantity": "2", "euros": 2.36},
    {"category_name": "Storage", "product_name": "Block Storage Volume",
     "sku": "/storage/block/volume-low-latency-5k/fr-par-2", "unit": "gigabyte_hour", "billed_quantity": "9",
     "euros": 1.0},
]


ROWS = [
    {"started": "2026-10-02T10:00:00Z", "batch": "blender-1", "kind": "blender", "who": "review page",
     "machine_minutes": 20, "wall_minutes": 20, "euros": 0.39,
     "machines": [{"type": "POP2-32C-128G", "zone": "pl-waw-2", "minutes": 20, "euros": 0.39}]},
    {"started": "2026-10-03T10:00:00Z", "batch": "game-1", "kind": "game-gate", "machine_minutes": 29.4,
     "wall_minutes": 29.4, "euros": 0.39375, "machines": []},
    {"started": "2026-10-04T10:00:00Z", "batch": "pixal-1", "per_card": 3, "machines": [], "machine_minutes": 1,
     "euros": 0.5, "models": [], "models_done": 0, "card_minutes": 1, "wall_minutes": 1, "job_seconds": []},
    {"started": "2026-10-05T10:00:00Z", "batch": "library-1", "kind": "library", "who": "k8s-proof",
     "machine_minutes": 10, "wall_minutes": 10, "euros": 1.0,
     "machines": [{"type": "POP2-32C-128G", "zone": "pl-waw-2", "minutes": 10, "euros": 0.9}],
     "attempts": [{"type": "L4-1-24G", "zone": "fr-par-1", "minutes": 0, "euros": 0}]},
    {"started": "2026-10-10T02:00:00Z", "batch": "late-1", "kind": "blender", "machine_minutes": 1, "euros": 9.0,
     "machines": []},
]


# The started, refused and order lines: not batches, so the paper's commands answer the same with them (fault, review
# of C1, 2026-10-17: reconcile counted them, tables gave a 0-euro rent-started group, types_before 'not recorded').
ORDER_ROWS = [
    {"started": "2026-10-04T09:00:00Z", "batch": "rent-pixal-2-1", "kind": "rent-started", "state": "started",
     "run": "pixal-2", "name": "pixal-2-1", "type": "L4-1-24G", "price": 0.75, "deadline": None, "machines": [],
     "attempts": [], "machine_minutes": 0.0, "euros": 0.0},
    {"started": "2026-10-04T09:00:01Z", "batch": "rent-pixal-2-1", "kind": "rent-refused", "state": "refused",
     "name": "pixal-2-1", "reason": "out of stock", "machines": [], "attempts": [], "machine_minutes": 0.0,
     "euros": 0.0},
    {"started": "2026-10-11T09:00:00Z", "batch": "order-pool-p", "kind": "order-started", "state": "started",
     "what": "pool", "name": "p", "machines": [], "attempts": [], "machine_minutes": 0.0, "euros": 0.0}]


def bill_line(sku, euros):
    """One line of a saved bill read."""
    return {"sku": sku, "euros": euros}


def paper_measures():
    """The paper's commands driven once over ROWS and BILL (and once more with the order lines added), `today` over two
    saved reads and `today --since` over a few rows and calls: {measure: its value}."""
    prices = costs.unit_prices(BILL)
    rows = costs.month_rows(ROWS, "2026-10", READ)
    kinds = costs.untyped_kinds(ROWS)
    report = costs.reconcile(ROWS, BILL, READ)
    products = costs.per_product(rows, BILL, prices)
    split = costs.split_rnd(rows, kinds)
    engine = [group for group in costs.per_group(rows, kinds, {}, prices) if group["group"] == costs.group_of("game-gate")]
    with_orders = ROWS + ORDER_ROWS
    home = costs.HOME
    reads = pathlib.Path(tempfile.mkdtemp())
    (reads / "2026-10-11T2100Z.json").write_text(json.dumps({"lines": [bill_line("/instance/server/l4_1_24g/x", 10.0)]}))
    (reads / "2026-10-12T0600Z.json").write_text(json.dumps({"lines": [bill_line("/instance/server/l4_1_24g/x", 99.0)]}))
    baseline, since = costs.day_baseline(reads, datetime.datetime(2026, 10, 12, 18, 0, tzinfo=datetime.timezone.utc))
    first, first_since = costs.day_baseline(reads, datetime.datetime(2026, 10, 11, 23, 0, tzinfo=datetime.timezone.utc))
    today = [bill_line("/instance/server/l4_1_24g/x", 25.0), bill_line("/instance/server/l40s_1_48g/x", 2.0),
             bill_line("/network/ipam/ipv4/x", 1.0)]
    moment = costs.moment("2026-10-12T18:25Z")
    since_rows = [{"started": "2026-10-12T18:30:00Z", "worktree": "agent-a1", "euros": 2.0},
                  {"started": "2026-10-12T18:40:00Z", "who": "surfaces", "euros": 1.0},
                  {"started": "2026-10-12T18:00:00Z", "worktree": "agent-a1", "euros": 50.0}]
    since_calls = [{"time": "2026-10-12T20:30:00+02:00", "call": "a", "state": "started", "model": "m",
                    "estimate": 0.3, "tag": "people"},
                   {"time": "2026-10-12T20:31:00+02:00", "call": "a", "state": "finished", "model": "m", "euros": 0.2,
                    "tag": "people"},
                   {"time": "2026-10-12T20:32:00+02:00", "call": "b", "state": "started", "model": "m",
                    "estimate": 0.05, "caller": "finishmap-name"},
                   {"time": "2026-10-12T20:00:00+02:00", "call": "c", "state": "finished", "model": "m", "euros": 9.0}]
    return {
        "paper: scrub keeps only the public roots": costs.scrub(
            {"folder": home + "/.claude/jobs/abc/tmp/x", "jobs": [home + "/.farm-factory-props/w"],
             "deep": {"path": home + "/.cache/y"}}),
        "paper: a row without kind is tagged pixal": {
            batch: (tag["kind"], bool(tag.get("inferred"))) for batch, tag in kinds.items()},
        "paper: the bill is the ledger and what it misses": {
            "ledger month": report["ledger_month"], "not in ledger": report["not_in_ledger"],
            "adds up": report["check"]["ledger_month + not_in_ledger"] == report["check"]["bill"]},
        "paper: an engine run is typed by its price": costs.engine_type(ROWS[1], prices),
        "paper: an engine run group names its card type": [group["cards"] for group in engine][:1],
        "paper: processor machines priced again by the started hour": (
            round(products["POP2-32C-128G"]["ledger"], 2), round(products["POP2-32C-128G"]["at_billing_unit"], 2)),
        "paper: an engine run is not priced again": products["L4-1-24G"]["at_billing_unit"],
        "paper: R&D and production cover the ledger": (round(split["R&D"], 4), round(split["production"], 2)),
        "paper: euros beyond the machines are not split": {
            key: round(value, 5) for key, value in costs.types_before(ROWS, "2026-10-06").items() if round(value, 5)},
        "paper: order lines change no reconciliation": costs.reconcile(with_orders, BILL, READ) == report,
        "paper: order lines change no table": costs.tables(with_orders, report, BILL) == costs.tables(ROWS, report, BILL),
        "paper: order lines change no machine type": (
            costs.types_before(with_orders, "2026-10-06") == costs.types_before(ROWS, "2026-10-06")),
        "paper: today is the bill less the last read before the day": costs.today_line(today, baseline, since, 7.0,
                                                                                      "saved"),
        "paper: the day's first read is the last before it": (first_since, first[0]["euros"]),
        "paper: spend since splits by track": dict(
            costs.cloud_since(since_rows, moment) + costs.google_since(since_calls, moment, lambda model: 0.0)),
    }


# --- the day's alarm: `reconcile-day 2026-10-11` run as a command on each row's files ---

def snapshot(read, machines, storage=0.0):
    """One saved read of the month's Scaleway bill: its machines and object storage so far."""
    return {"read": read, "lines": [bill_line("/instance/server/l4_1_24g/fr-par-2", machines),
                                    bill_line("/storage/obj/usage/fr-par", storage)]}


SAVED_READS = [snapshot("2026-10-10T23:00:00+00:00", 100.0), snapshot("2026-10-11T12:00:00+00:00", 120.0),
               snapshot("2026-10-11T23:30:00+00:00", 150.0, storage=10.0)]


ONE_RUN = [{"started": "2026-10-11T09:00:00Z", "kind": "pixal", "wall_minutes": 60, "euros": 50.0}]


TWO_PROVIDERS = {"scaleway": [bill_line("/instance/server/l4_1_24g/fr-par-2", 20.0)], "google": [bill_line("m", 1.0)]}


# Each row: the day bill (None: no file, the Scaleway day built from the saved reads), the cloud and Google ledgers
# (None: named but never written), the saved reads, the providers skipped; and what the command's "exit N:" and output
# must say. Faults of the review of C1, 2026-10-17: an empty bill read as all clear, nothing built the day's bill, a
# run across midnight alarmed on both days, a heavy storage day alarmed, a running machine's day alarmed, a missing
# ledger read as empty and blamed spend outside it.
DAYS = {
    "day: eleven percent off fails and names the provider": (
        {"google": [bill_line("gemini-3-pro-image", 100.0)],
         "scaleway": [bill_line("/instance/server/l4_1_24g/fr-par-2", 50.0),
                      bill_line("/storage/block/volume-low-latency-5k/fr-par-2", 3.0),
                      bill_line("/network/ipam/ipv4/fr-par-2", 2.0)]},
        [{"started": "2026-10-11T09:00:00Z", "kind": "pixal", "euros": 51.0},
         {"started": "2026-10-11T10:00:00Z", "kind": "disk-and-address", "euros": 4.5},
         {"started": "2026-10-12T10:00:00Z", "kind": "pixal", "euros": 99.0}],
        [{"time": "2026-10-11T10:00:00+02:00", "day": "2026-10-11", "call": "a", "state": "started", "model": "m",
          "estimate": 0.15},
         {"time": "2026-10-11T10:01:00+02:00", "day": "2026-10-11", "call": "a", "state": "finished", "model": "m",
          "euros": 89.0},
         {"time": "2026-10-12T10:01:00+02:00", "day": "2026-10-12", "call": "b", "state": "finished", "model": "m",
          "euros": 11.0}], (), (),
        Text(lacks=("exit 0:",),
             matches=(r"^google:.*calls: bill 100\.00, ledgers 89\.00, 11\.0% apart; over",
                      r"^scaleway:(?!.*over)(?=.*within)(?=.*disks and addresses: bill 5\.00, ledgers 4\.50)"))),
    "day: within five percent passes": (
        {"scaleway": [bill_line("/instance/server/l4_1_24g/fr-par-2", 100.0)]},
        [{"started": "2026-10-11T09:00:00Z", "kind": "pixal", "euros": 96.0}], [], (), ("google",),
        Text(has=("exit 0:", "within"))),
    "day: an empty bill fails": ({}, [], [], (), (), Text(has=("google: no bill", "scaleway: no bill"),
                                                           lacks=("exit 0:",))),
    "day: a bill without scaleway fails": (
        {"google": [bill_line("m", 1.0)]}, [],
        [{"day": "2026-10-11", "call": "a", "state": "finished", "model": "m", "euros": 1.0}], (), (),
        Text(has=("scaleway: no bill",), lacks=("exit 0:",))),
    "day: the scaleway day comes from the saved reads": (
        None, ONE_RUN, [], SAVED_READS, ("google",),
        Text(has=("exit 0:", "machines: bill 50.00, ledgers 50.00", "not in any ledger: storage 10.00"))),
    "day: no read before the day is no bill": (
        None, ONE_RUN, [], SAVED_READS[1:], ("google",), Text(has=("scaleway: no bill",), lacks=("exit 0:",))),
    "day: a run across midnight counts its share": (
        None, [{"started": "2026-10-10T22:00:00Z", "kind": "pixal", "wall_minutes": 240, "euros": 40.0}], [],
        [snapshot("2026-10-10T23:00:00+00:00", 0.0), snapshot("2026-10-11T23:30:00+00:00", 30.0)], ("google",),
        Text(has=("exit 0:", "machines: bill 30.00, ledgers 30.00"))),
    "day: storage and other lines never alarm": (
        {"scaleway": [bill_line("/instance/server/l4_1_24g/fr-par-2", 20.0),
                      bill_line("/storage/obj/usage/fr-par", 40.0),
                      bill_line("/paas/secret_manager/access/fr-par", 5.0)]},
        [{"started": "2026-10-11T09:00:00Z", "kind": "pixal", "euros": 20.0}], [], (), ("google",),
        Text(has=("exit 0:", "not in any ledger: storage 40.00, other 5.00"))),
    "day: a machine still running counts at its price": (
        {"scaleway": [bill_line("/instance/server/l4_1_24g/fr-par-2", 6.0)]},
        [{"started": "2026-10-11T10:00:00Z", "batch": "rent-pixal-9-1", "kind": "rent-started", "run": "pixal-9",
          "name": "pixal-9-1", "price": 0.1, "deadline": costs.moment("2026-10-11T11:00:00Z"), "euros": 0.0}],
        [], (), ("google",), Text(has=("exit 0:", "machines: bill 6.00, ledgers 6.00"))),
    "day: no cloud ledger fails as missing": (
        TWO_PROVIDERS, None, [], (), ("google",),
        Text(has=("scaleway: no ledger at ",), lacks=("exit 0:", "ledgers 0.00"))),
    "day: no google ledger fails as missing": (
        TWO_PROVIDERS, [{"started": "2026-10-11T09:00:00Z", "kind": "pixal", "euros": 20.0}], None, (), (),
        Text(has=("google: no ledger at ", "scaleway: machines"), lacks=("exit 0:",))),
}


def day_check(row):
    """`reconcile-day 2026-10-11` on one DAYS row's files, written to a fresh folder: "exit N:", its output below."""
    day_bill, cloud_rows, google_lines, snapshots, skip, _ = row
    folder = pathlib.Path(tempfile.mkdtemp())
    bills = folder / "bills"
    bills.mkdir()
    for read in snapshots:
        (bills / f"{read['read'][:13]}{read['read'][14:16]}Z.json").write_text(json.dumps(read))
    for name, lines in (("ledger.jsonl", cloud_rows), ("google.jsonl", google_lines)):
        if lines is not None:
            (folder / name).write_text("".join(json.dumps(line) + "\n" for line in lines))
    command = [sys.executable, str(HERE / "costs.py"), "reconcile-day", "2026-10-11", "--ledger",
               str(folder / "ledger.jsonl"), "--google-ledger", str(folder / "google.jsonl"), "--bills", str(bills),
               *[part for provider in skip for part in ("--skip", provider)]]
    if day_bill is not None:
        (folder / "bill.json").write_text(json.dumps(day_bill))
        command.insert(4, str(folder / "bill.json"))
    done = subprocess.run(command, capture_output=True, text=True)
    return f"exit {done.returncode}:\n{done.stdout}{done.stderr}"


def day_measures():
    """Every DAYS row's command, run side by side: {row: "exit N: output"}."""
    with concurrent.futures.ThreadPoolExecutor(len(DAYS)) as pool:
        return dict(zip(DAYS, pool.map(day_check, DAYS.values())))


# --- per_unit.py's worlds: ledgers written here, Google calls, a store, and the paper's ledger copy ---

LINES = [
    {"batch": "batch-1", "kind": "pixal", "models_done": 10, "euros": 1.0},
    {"batch": "batch-2", "kind": "pixal", "models_done": 4, "euros": 2.0},
    {"batch": "batch-3", "kind": "pixal", "models_done": 0, "euros": 0.7},
    {"batch": "blender-1", "kind": "blender", "who": "score light stage", "jobs": ["a", "b", "c", "d"], "euros": 0.4},
    {"batch": "blender-2", "kind": "blender", "who": "settle", "jobs": ["settle_stage.py"], "euros": 0.0},
    {"batch": "blender-3", "kind": "blender", "who": "settle hangar", "jobs": ["settle_stage.py"], "euros": 9.0},
]


CALLS = [
    {"day": "2026-10-12", "caller": "pro", "state": "started", "estimate": 0.13},
    {"day": "2026-10-12", "caller": "pro", "state": "finished", "euros": 0.14},
    {"day": "2026-10-11", "caller": "pro", "euros": 0.12},
    {"day": "2026-10-12", "caller": "pro", "state": "failed"},
]


# Calls of one caller with their times: a and b overlap by 20 s, c failed, the last of the first format (no state).
TIMED_CALLS = [{"call": "a", "caller": "pro", "state": "started", "time": "2026-10-12T10:00:00+02:00"},
               {"call": "b", "caller": "pro", "state": "started", "time": "2026-10-12T10:00:10+02:00"},
               {"call": "a", "caller": "pro", "state": "finished", "time": "2026-10-12T10:00:30+02:00", "euros": 0.1},
               {"call": "b", "caller": "pro", "state": "finished", "time": "2026-10-12T10:01:10+02:00", "euros": 0.1},
               {"call": "c", "caller": "pro", "state": "failed"}, {"caller": "pro", "euros": 0.1}]


# Ticketed lines: the ticket names the stage, whatever the kind. Sound's own line names its takes; an older one does
# not (its takes recorded in SOUND_TAKES), and one named in neither counts none.
TILES = {"batch": "tiles-1", "kind": "library", "ticket": "surface-tiles@airlock abc", "jobs": ["a"], "euros": 0.2,
         "machines": []}
BAKE = {"batch": "bake-1", "kind": "library", "ticket": "surfaces-bake@airlock abc", "jobs": ["a", "b"], "euros": 0.5,
        "machines": [{"type": "L4-1-24G", "started": True, "unit_seconds": [60.0, 120.0], "work_minutes": 4.0}]}
TAKE = {"batch": "prove-1", "kind": "prove", "who": "score runner, sound stage", "ticket": "sound@airlock abc",
        "euros": 0.23, "machines": [], "takes": 1}
OLD_TAKE = {key: value for key, value in TAKE.items() if key != "takes"} | {
    "batch": "prove-20261021-005847-4017578", "euros": 0.0525}
UNNAMED_TAKE = {**OLD_TAKE, "batch": "prove-2"}


# A per-unit file's stage measured elsewhere, which the in-place modes must keep.
SETTLE = {"stage": "settle", "likely_euros": 0.59, "high_euros": 1.6, "runs": 3, "sources": {}}


MEASURED = {"stage": "pixal", "unit": "model", "count": {"json_keys": "takes.json"}, "also": [], "likely_euros": 0.1,
            "high_euros": 0.4, "runs": 9, "sources": {"cloud batches": ["b1"]},
            "forecast": {"rule": "stale", "source": "old"}}


# A pixal line with no machine seconds: 20 working minutes; with per_card 2 on two one-card machines.
UNTIMED = {"batch": "b", "kind": "pixal", "models_done": 4, "machine_minutes": 20.0, "euros": 1.0}


PAPER = REPO / "paper/evidence/cloud/ledger.jsonl"


def written(rows):
    """A ledger of `rows` in a fresh folder, a torn last line after them; its path."""
    path = pathlib.Path(tempfile.mkdtemp()) / "ledger.jsonl"
    path.write_text("".join(json.dumps(row) + "\n" for row in rows) + "{torn\n")
    return path


def per_unit_file(body, *arguments):
    """per_unit's main run on a per-unit file holding `body` with `arguments`; the file it leaves."""
    out = pathlib.Path(tempfile.mkdtemp()) / "per-unit.json"
    out.write_text(json.dumps(body, indent=1) + "\n")
    per_unit.main([*arguments, "--out", str(out)])
    return json.loads(out.read_text())


def without_time(body):
    """A per-unit file's text with every time field left out."""
    return json.dumps({**{name: value for name, value in body.items() if name != "node_minutes"},
                       "stages": {stage: {name: value for name, value in found.items() if name != "time"}
                                  for stage, found in body["stages"].items()}}, indent=1)


def finish_records():
    """The node times of a store whose finish records are three makes and one carried record (no make)."""
    sys.path.insert(0, str(REPO))
    from score.graph import runs
    from score.store import Store
    root = pathlib.Path(tempfile.mkdtemp())
    store = Store.in_folder(root)
    for number, (node, minutes) in enumerate((("plan@hangar", 3.0), ("plan@lab", 5.0), ("concept@lab", 1.0))):
        store.write_record(node, f"key{number}", {"node": node, "stage": node.partition("@")[0], "place": "p",
                                                   "key": f"key{number}", "started": f"2026-10-20T0{number}",
                                                   "finished": f"2026-10-20T1{number}", "minutes": minutes})
    store.write_record("plan@flat", "key9", {"node": "plan@flat", "stage": "plan", "finished": "2026-10-20T19",
                                             "minutes": 99.0, "carried": {"reason": "kept over a no-op"}})
    return runs.node_times(store), root


def unit_measures():
    """per_unit driven once over each world: {measure: its value}."""
    lines = per_unit.ledger_lines([written(LINES), written(LINES[:1])])
    ticketed = per_unit.ledger_lines([written([TILES, TAKE])])
    measured = per_unit.measure(per_unit.ledger_lines([written(LINES)]), CALLS, "google-ledger.jsonl")
    recorded = per_unit.measure([], [], "google-ledger.jsonl")["surfaces-paint"]
    added = per_unit_file({"read": [], "high_quantile": 0.9, "stages": {"settle": SETTLE}},
                          "--add", "--ledger", str(written([BAKE, TAKE])))["stages"]
    rules = per_unit_file({"read": ["x"], "high_quantile": 0.9,
                           "stages": {"pixal": MEASURED, "settle": {**MEASURED, "stage": "settle"}}}, "--rules-only")
    paper = {line["batch"]: (line, source) for line, source in per_unit.ledger_lines([PAPER])}
    settle = per_unit.cloud_times([paper["blender-20261008-165605-2054366"]], per_unit.SPECS["settle"])
    pixal = per_unit.cloud_times([paper["batch-20261008-134426-1833430"]], per_unit.SPECS["pixal"])
    untimed_setup = per_unit.cloud_times([({**UNTIMED, "models_done": 2}, "here line 1")], per_unit.SPECS["pixal"])
    two_cards = {**UNTIMED, "per_card": 2, "machines": [{"cards": 1, "work_minutes": 10.0, "minutes": 11.0},
                                                        {"cards": 1, "work_minutes": 10.0, "minutes": 11.0}]}
    kept, made = per_unit.kept_times(
        {"stages": {"closeup": {"time": {"unit_seconds": {"likely": 30.0, "high": 50.0}}},
                    "pixal": {"time": {"why": "none"}}}, "node_minutes": {"plan": {"likely": 2.0}}},
        {"closeup": {"why": "no Google ledger read here"}, "pixal": {"unit_seconds": {"likely": 9.0, "high": 9.0}}}, {})
    google = per_unit.google_times(TIMED_CALLS, "pro", "google-ledger.jsonl")
    batch_job = per_unit.batch_job_time(TIMED_CALLS, "pro", "google-ledger.jsonl")
    records, root = finish_records()
    node_minutes = per_unit.node_minutes(records, root)
    warm = per_unit.with_warm({"stages": {"pixal": {"stage": "pixal", "time": {}}, "settle": SETTLE}})["stages"]
    batch_stages = per_unit.with_warm({"stages": {}})["stages"]
    before = json.loads((REPO / "data/costs/per-unit.json").read_text())
    after = per_unit_file(before, "--times-only", "--ledger", str(PAPER))
    return {
        "unit: a batch in two ledgers is read once": [line["batch"] for line, _ in lines],
        "unit: pixal priced over the units each batch finished": per_unit.cloud_measures(lines, per_unit.SPECS["pixal"]),
        "unit: light passes are the light stage's jobs": per_unit.cloud_measures(lines, per_unit.SPECS["light-passes"]),
        "unit: settle is its own who's, a free drop counted": per_unit.cloud_measures(lines, per_unit.SPECS["settle"]),
        "unit: a line ticketed for tiles is no bake's": per_unit.cloud_measures(ticketed,
                                                                               per_unit.SPECS["surfaces-bake"]),
        "unit: sound priced over the takes its line names": per_unit.cloud_measures(ticketed, per_unit.SPECS["sound"]),
        "unit: an older sound line over its recorded takes": per_unit.cloud_measures(
            per_unit.ledger_lines([written([OLD_TAKE, UNNAMED_TAKE])]), per_unit.SPECS["sound"])[0],
        "unit: --add keeps every other stage and adds sound": (
            added["settle"], added["sound"]["likely_euros"], added["sound"]["forecast"]["rule"]),
        "unit: --add prices a warm stage on its own timed jobs": (
            added["surfaces-bake"]["runs"], added["surfaces-bake"]["time"]["unit_seconds"]["likely"],
            "of its own jobs" in added["surfaces-bake"]["sources"]["warm work"]),
        "unit: google units are finished calls": per_unit.google_measures(CALLS, "pro"),
        "unit: the measured file": {
            "pixal likely": measured["pixal"]["likely_euros"], "pixal runs": measured["pixal"]["runs"],
            "pixal count": measured["pixal"]["count"], "pixal forecast": measured["pixal"]["forecast"]["rule"],
            "pixal per model": "per_model" in measured["pixal"]["forecast"],
            "closeup runs": measured["closeup"]["runs"],
            "closeup per model": measured["closeup"]["forecast"]["per_model"]},
        "unit: pixal's high is the high quantile": measured["pixal"]["high_euros"],
        "unit: stages with no lines are left out": sorted({"surfaces-maps", "surfaces-bake"} & set(measured)),
        "unit: a recorded stage is priced from its runs": (
            recorded["likely_euros"], recorded["runs"], recorded["sources"]["recorded runs"], recorded["count"],
            recorded["forecast"]["rule"]),
        "unit: stages without a forecast rule and source": [
            stage for stage, spec in {**per_unit.SPECS, **per_unit.RECORDED}.items()
            if not (per_unit.forecast(spec)["forecast"]["rule"] and per_unit.forecast(spec)["forecast"]["source"])],
        "unit: --rules-only keeps the measured numbers": (
            rules["read"], rules["stages"]["settle"]["likely_euros"], rules["stages"]["pixal"]["forecast"]["rule"],
            rules["stages"]["pixal"]["basis"], rules["stages"]["settle"]["forecast"]["rule"],
            set(per_unit.RECORDED) <= set(rules["stages"])),
        "unit: a settle run's time from the paper's line": {
            key: settle[key] for key in ("unit_seconds", "slots", "setup_minutes", "failed_start_share", "holds")},
        "unit: a pixal batch's time from the paper's line": (
            pixal["unit_seconds"]["likely"], pixal["slots"], pixal["setup_minutes"]),
        "unit: a stage with no line says why": per_unit.cloud_times([], per_unit.SPECS["settle"])["why"],
        "unit: a stage whose lines time no set-up says so": (
            untimed_setup["unit_seconds"]["likely"], untimed_setup["setup_minutes"]),
        "unit: a line's seconds by its working minutes and slots": (
            per_unit.unit_seconds(UNTIMED, "models_done"), per_unit.unit_seconds(two_cards, "models_done"),
            per_unit.unit_seconds({**UNTIMED, "machine_minutes": None}, "models_done")),
        "unit: writing times in place keeps a measured time": (
            kept["closeup"]["unit_seconds"]["likely"], bool(kept["pixal"]["unit_seconds"]), made),
        "unit: a google stage's time from its calls": {
            key: google[key] for key in ("slots", "holds", "failed_start_share", "lines")}
        | {"likely": google["unit_seconds"]["likely"],
           "why with no ledger": "why" in per_unit.google_times(TIMED_CALLS, "pro", None),
           "why with no calls": "why" in per_unit.google_times([], "pro", "g")},
        "unit: a Batch API row is unmeasured": f"{list(batch_job)}: {batch_job.get('why')}",
        "unit: node minutes are the store's finish records": (
            [row["node"] for row in records], node_minutes["plan"]["likely"], node_minutes["plan"]["makes"],
            node_minutes["concept"]["high"]),
        "unit: a warm stage at the bill's price plus the overhead": (
            len([value for row in per_unit.warm_rows(per_unit.WARM["pixal"]) for value in row["unit_seconds"]]),
            warm["pixal"]["runs"], round(per_unit.hourly("L4-1-24G"), 4), warm["pixal"]["likely_euros"],
            warm["pixal"]["time"]["slots"], warm["pixal"]["time"]["unit_seconds"]["likely"],
            warm["pixal"]["time"]["setup_minutes"], warm["settle"]),
        "unit: a batch stage is half its standard calls": (
            batch_stages["closeup"]["likely_euros"], "google calls" in batch_stages["finish-route-list"]["sources"],
            batch_stages["finish-route-recheck"]["forecast"]["rule"],
            bool(batch_stages["finish-route-list"]["price_note"]),
            bool(batch_stages["finish-route-list"]["time"]["why"])),
        "unit: --times-only keeps every euro": (
            without_time(after) == without_time(before), set(after["stages"]) == set(before["stages"]),
            all("time" in found for found in after["stages"].values())),
    }


# --- paid calls only through the ledgered clients (a wording check guarding the owner rule) ---


# The files that may make a paid call: (why, the top-level functions and constants it may be in). A paid call
# anywhere else in the file fails as in any other. A new one is added only when it writes its ledger line first.
ALLOWED = {
    "tools/cloud/google_spend.py": ("the Gemini client: a started line before every call", {"URL", "post"}),
    "tools/cloud/google_batch.py": ("the Gemini Batch API client: a started line on google_spend's ledger for "
                                          "each request before its job is sent", {"API", "send", "status"}),
    "tools/cloud/test_google_spend_ledgers_every_call_before_it_is_sent.py": (
        "the Gemini client's own lint names Google's hosts and clients", {"test_no_module_calls_google_another_way"}),
    "tools/cloud/backends/scaleway.py": (
        "the machine backend: create writes the started line before its order, under batch.rent, and the machine's "
        "disks and addresses go to the ledger at its delete. Known gap: quarantine_bad_address's fresh address is "
        "the machine's and ledgered at its delete, but the bad address it detaches stays in the project for good, "
        "billed by the hour with no ledger line (reconcile-day shows it in disks and addresses)",
        {"create", "quarantine_bad_address"}),
    "tools/cloud/k8s/clusters/scaleway.py": ("the cluster set-up: ledger.order_started before each cluster and pool "
                                             "order; the nodes come to the ledger as the submitter's run rows",
                                             {"create_cluster", "ensure_pools"}),
    "tools/cloud/conductor/machine.py": ("the conductor's own set-up, run only by the owner: ledger.order_started "
                                         "before each billed order (address, data volume, its growth, server)",
                                         {"address", "data_volume", "grow_data", "make_server"}),
    "score/conductor/logs.py": ("the log scrubber names the Google key header to blank it, calls nothing",
                                {"SECRET_WORDS"}),
    str(pathlib.Path(__file__).resolve().relative_to(REPO)): (
        "this lint's pattern and its fixtures", {"PAID_TEXT", "LINT_CASES"}),
}


GEMINI_MODULES = ("google.genai", "google.generativeai", "google.cloud.aiplatform", "vertexai")


GEMINI_NAMES = {"genai", "generativeai"}


PAID_TEXT = re.compile(r"generativelanguage\.googleapis\.com|aiplatform\.googleapis\.com|x-goog-api-key|"
                       r"api\.scaleway\.com/(instance|block)/v1[a-z0-9]*/zones/[^/\s]+/(servers|volumes|ips)/?$|"
                       r"api\.scaleway\.com/k8s/v1[a-z0-9]*/regions/[^/\s]+/clusters(/[^/\s]+/pools)?/?$|"
                       r"scw\s+(instance\s+(server|volume|ip)|block\s+volume|k8s\s+(pool|cluster))\s+create")


SCALEWAY_SDK = ("scaleway.instance", "scaleway.block", "scaleway.k8s", "scaleway_core")


DYNAMIC_IMPORTS = {"import_module", "__import__"}


# scw's words that order something billed: (product, resource) followed by "create".
SCW_PAID = {("instance", "server"), ("instance", "volume"), ("instance", "ip"), ("block", "volume"),
            ("k8s", "pool"), ("k8s", "cluster")}


SCW_PRODUCTS = {product for product, _ in SCW_PAID}


FUNCTIONS = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)


# The list methods that grow a list of words, by how many arguments each takes.
GROW_ARGUMENTS = {"append": 1, "extend": 1, "insert": 2}


RUNNABLE_SUFFIXES = {".py", ".sh", ".bash", ".lua", ".yaml", ".yml", ".js", ".mjs", ".ts", ".toml"}


RUNNABLE_NAMES = {"Makefile", "Dockerfile"}


def paid_module(name):
    """Whether a module's dotted name is one of Google's Gemini clients or Scaleway's SDK."""
    return (name.startswith(GEMINI_MODULES + SCALEWAY_SDK)
            or (name.startswith("google.") and name.split(".")[-1] in GEMINI_NAMES))


def imported_paid_modules(nodes):
    """(line, what) for each import of Google's Gemini clients or Scaleway's SDK, by an import statement or by
    importlib.import_module or __import__ given the module's name as a string, in `nodes` (a tree's ast.walk)."""
    found = []
    for node in nodes:
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            names = [node.module] + [f"{node.module}.{alias.name}" for alias in node.names]
        elif isinstance(node, ast.Call) and called_name(node) in DYNAMIC_IMPORTS and node.args:
            names = [name for name in [string_text(node.args[0])] if name]
        else:
            continue
        found += [(node.lineno, f"imports {name}") for name in names if paid_module(name)]
    return found


def called_name(node):
    """The name a call calls: `f` for f(...) and for x.f(...); None for anything else."""
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return None


def string_text(node):
    """A string constant's text, or an f-string's with each value it fills in as "{}"; None for anything else."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return "".join(part.value if isinstance(part, ast.Constant) else "{}" for part in node.values)
    return None


def variable_string(assigned, name):
    """The one string a variable holds in `assigned`; None when it holds anything else."""
    words = assigned.get(name)
    return words[0] if words and len(words) == 1 and isinstance(words[0], str) else None


def joined_text(node, assigned):
    """The text a string expression stands for: strings joined with +, an f-string, a variable set to one string
    (in `assigned`), each part it cannot read as "{}"; None when no part of it is a string."""
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left, right = joined_text(node.left, assigned), joined_text(node.right, assigned)
        return None if left is None and right is None else (left or "{}") + (right or "{}")
    if isinstance(node, ast.JoinedStr):
        return "".join(part.value if isinstance(part, ast.Constant)
                       else variable_string(assigned, part.value.id) or "{}" if isinstance(part.value, ast.Name)
                       else "{}" for part in node.values)
    if isinstance(node, ast.Name):
        return variable_string(assigned, node.id)
    return string_text(node)


def paid_strings(nodes, states):
    """(line, what) for each string, f-string or joined string in `nodes` (a tree's ast.walk) that names a paid host,
    key header or order, its variables read from `states` (variable_states of the tree)."""
    found = []
    for node in nodes:
        if not isinstance(node, (ast.Constant, ast.JoinedStr, ast.BinOp)):
            continue
        text = joined_text(node, states.get(id(node), {}))
        if text is not None and PAID_TEXT.search(text):
            found.append((node.lineno, f"names {PAID_TEXT.search(text).group(0)!r}"))
    return found


def grown_list(node):
    """(variable, method, its arguments) when `node` is `variable.append(x)`, `variable.extend(x)` or
    `variable.insert(i, x)`; else None."""
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name)
            and len(node.args) == GROW_ARGUMENTS.get(node.func.attr)):
        return node.func.value.id, node.func.attr, node.args
    return None


def inserted(words, index_node, word):
    """`words` with `word` put in at the index `index_node` reads as (an int constant); at the end when it cannot be
    read."""
    index = index_node.value if isinstance(index_node, ast.Constant) and type(index_node.value) is int else len(words)
    return words[:index] + [word] + words[index:]


def setting(node, assigned):
    """(variable, its words after) when `node` sets, adds to or grows (.append, .extend, .insert) a variable, read
    from `assigned`, the words its variables hold just before; None for any other node."""
    if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
        return node.targets[0].id, sequence_words(node.value, assigned)
    if isinstance(node, ast.AnnAssign) and node.value is not None and isinstance(node.target, ast.Name):
        return node.target.id, sequence_words(node.value, assigned)
    if isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Add) and isinstance(node.target, ast.Name):
        return node.target.id, assigned.get(node.target.id, [None]) + sequence_words(node.value, assigned)
    grown = grown_list(node)
    if grown is None:
        return None
    name, method, arguments = grown
    before = assigned.get(name, [None])
    if method == "extend":
        return name, before + sequence_words(arguments[0], assigned)
    if method == "insert":
        return name, inserted(before, arguments[0], string_text(arguments[1]))
    return name, before + [string_text(arguments[0])]


def scope_members(scope):
    """The nodes a module or function holds itself; a function inside it is a scope of its own, so its body is left
    out (the function's own node stays in)."""
    members, stack = [], list(ast.iter_child_nodes(scope))
    while stack:
        node = stack.pop()
        members.append(node)
        if not isinstance(node, FUNCTIONS):
            stack.extend(ast.iter_child_nodes(node))
    return members


def scopes(tree):
    """(scope, the scope around it, its scope_members) for the module (None around it) and each function in it,
    outer before inner."""
    found, waiting = [], [(tree, None)]
    while waiting:
        scope, outer = waiting.pop(0)
        members = scope_members(scope)
        found.append((scope, outer, members))
        waiting += [(node, scope) for node in members if isinstance(node, FUNCTIONS)]
    return found


def variable_states(tree):
    """{id(node): {variable: its words}} for each node, as the node's own function (or the module) had set its
    variables just before it in source order, starting from the words the scope around it left; a setting takes
    effect where it ends. So a name two functions both use is read from the function the node is in (review of C1,
    2026-10-17: one module-wide table read one function's call with another's words)."""
    states, left = {}, {None: {}}
    for scope, outer, members in scopes(tree):
        assigned = left[outer]
        events = []
        for node in members:
            if not hasattr(node, "lineno"):
                continue
            events.append(((node.lineno, node.col_offset, 1), node))
            events.append(((node.end_lineno, node.end_col_offset, 0), node))
        for (_, _, reading), node in sorted(events, key=lambda event: event[0]):
            if reading:
                states[id(node)] = assigned
                continue
            changed = setting(node, states[id(node)])
            if changed is not None:
                assigned = {**assigned, changed[0]: changed[1]}
        left[scope] = assigned
    return states


def sequence_words(node, assigned):
    """The words an expression stands for, in order: a string, a list or tuple opened (starred lists too), lists
    joined with +, a variable set to words; None for each part it cannot read, so words never join across it."""
    if isinstance(node, (ast.List, ast.Tuple)):
        return [word for item in node.elts for word in sequence_words(item, assigned)]
    if isinstance(node, ast.Starred):
        return sequence_words(node.value, assigned)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return sequence_words(node.left, assigned) + sequence_words(node.right, assigned)
    if isinstance(node, ast.Name):
        return assigned.get(node.id, [None])
    return [string_text(node)]


def orders_in(words):
    """The scw orders of billed resources ("instance server create") in a run of words; a word that cannot be read
    (None, as a function's parameter) between a product and "create" counts as an order."""
    return [" ".join(str(word) for word in words[index:index + 3]) for index in range(len(words) - 2)
            if words[index + 2] == "create" and (tuple(words[index:index + 2]) in SCW_PAID
                                                 or (words[index] in SCW_PRODUCTS and words[index + 1] is None))]


def scw_orders(nodes, states):
    """(line, what) for each call given, list built with, or variable set or grown to scw words that order a billed
    resource, in `nodes` (a tree's ast.walk): the words read through variables (`states`, variable_states of the
    tree: as the node's own function set them), joined and starred lists, .append, .extend and .insert
    (sequence_words, setting)."""
    compared = {id(side) for node in nodes if isinstance(node, ast.Compare)
                for side in [node.left, *node.comparators]}
    found = set()
    for node in nodes:
        if id(node) in compared or id(node) not in states:  # a test's check (`command[:4] == [...]`) orders nothing
            continue
        assigned = states[id(node)]
        changed = setting(node, assigned)
        if isinstance(node, ast.Call):
            words = [word for argument in node.args for word in sequence_words(argument, assigned)]
        elif isinstance(node, (ast.List, ast.Tuple)) or (isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add)):
            words = sequence_words(node, assigned)
        else:
            words = []
        for run in (words, changed[1] if changed else []):
            found |= {(node.lineno, f"orders scw {order}") for order in orders_in(run)}
    return sorted(found)


def python_paid_calls(text):
    """(line, what) for each paid call a Python source makes outside the ledgered clients."""
    tree = ast.parse(text)
    nodes, states = list(ast.walk(tree)), variable_states(tree)
    return sorted(set(imported_paid_modules(nodes) + paid_strings(nodes, states) + scw_orders(nodes, states)))


def logical_lines(text):
    """(first line number, text) for each line of a script, a line ending in a backslash joined with the next."""
    lines, start, held = [], None, []
    for number, line in enumerate(text.splitlines(), 1):
        start = number if start is None else start
        if line.rstrip().endswith("\\"):
            held.append(line.rstrip()[:-1])
            continue
        lines.append((start, " ".join(held + [line])))
        start, held = None, []
    return lines + ([(start, " ".join(held))] if held else [])


def shell_paid_calls(text):
    """(line, what) for each line of a script (a shell script, Makefile, Dockerfile, manifest) that names a paid host
    or order, a command broken over lines with a backslash read as one."""
    return [(number, f"names {PAID_TEXT.search(line).group(0)!r}")
            for number, line in logical_lines(text) if PAID_TEXT.search(line)]


def paid_calls(path):
    """(line, what) for each paid call in one file."""
    text = path.read_text(errors="replace")
    return python_paid_calls(text) if path.suffix == ".py" else shell_paid_calls(text)


def top_level_spans(tree):
    """(name, first line, last line) of each top-level function, class and constant of a module."""
    spans = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            spans.append((node.name, node.lineno, node.end_lineno))
        elif isinstance(node, ast.Assign):
            spans += [(target.id, node.lineno, node.end_lineno) for target in node.targets
                      if isinstance(target, ast.Name)]
    return spans


def outside_allowed(path, names):
    """(line, what) for each paid call in one file outside its top-level functions and constants named in `names`."""
    found = paid_calls(path)
    if path.suffix != ".py" or not names:
        return found
    spans = [(first, last) for name, first, last in top_level_spans(ast.parse(path.read_text(errors="replace")))
             if name in names]
    return [(line, what) for line, what in found if not any(first <= line <= last for first, last in spans)]


def runnable(path):
    """Whether a tracked file is code that can run: Python, a shell or other script, a Makefile, a Dockerfile, a
    manifest, or a file with no suffix that starts with #!. Text that runs nothing (docs, data, json) is left out."""
    if path.suffix in RUNNABLE_SUFFIXES or path.name in RUNNABLE_NAMES:
        return True
    return path.suffix == "" and path.read_bytes()[:2] == b"#!"


def tracked_sources():
    """The repository's tracked runnable files outside vendor/, repository-relative."""
    listed = subprocess.run(["git", "-C", str(REPO), "ls-files"], capture_output=True, text=True,
                            check=True).stdout.splitlines()
    return [path for path in listed
            if not path.startswith("vendor/") and (REPO / path).is_file() and runnable(REPO / path)]


def repository_calls(path):
    """(line, what) for each paid call one tracked file (repository-relative) makes outside its ALLOWED parts."""
    return outside_allowed(REPO / path, ALLOWED.get(path, ("", set()))[1])


# The lint's own reading: (file name, its text, the top-level parts it may order in, its paid lines counted by hand,
# or "runs nothing"). Faults of the reviews of 2026-10-17 each left one row's order unread before it was fixed.
LINT_CASES = {
    "lint: a module calling gemini directly": (
        "fixture.py", 'import urllib.request\n'
                      'URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"\n'
                      'def ask(body):\n'
                      '    return urllib.request.urlopen(urllib.request.Request(URL, data=body))\n', set(), [2]),
    "lint: a module loading google's client": ("fixture.py", "from google import genai\nimport vertexai\n", set(),
                                               [1, 2]),
    "lint: a module ordering a scaleway machine or disk": (
        "fixture.py", 'import subprocess\n'
                      'subprocess.run(["scw", "instance", "server", "create", "type=L4-1-24G"])\n'
                      'scw("block", "volume", "create", "size=20GB")\n'
                      'subprocess.run("scw instance ip create zone=fr-par-2", shell=True)\n', set(), [2, 3, 4]),
    # an order put in a variable first, a list with more joined on, a starred list
    "lint: an order built before its call": (
        "fixture.py", 'import subprocess\n'
                      'cmd = ["scw", "instance", "server", "create"]\n'
                      'subprocess.run(cmd)\n'
                      'subprocess.run(["scw", "block", "volume", "create"] + extra)\n'
                      'subprocess.run([*["scw", "instance", "ip", "create"], "zone=fr-par-2"])\n'
                      'base = ["scw", "k8s", "pool"]\n'
                      'subprocess.run(base + ["create", "size=0"])\n', set(), [2, 3, 4, 5, 7]),
    # an f-string splits into pieces; the block API is v1alpha1
    "lint: an address built in an f-string": (
        "fixture.py", 'zone = "fr-par-2"\n'
                      'SERVERS = f"https://api.scaleway.com/instance/v1/zones/{zone}/servers"\n'
                      'VOLUMES = "https://api.scaleway.com/block/v1alpha1/zones/fr-par-2/volumes"\n'
                      'ORDER = f"scw instance server create zone={zone}"\n', set(), [2, 3, 4]),
    "lint: an order grown by append or extend": (
        "fixture.py", 'import subprocess\n'
                      'cmd = ["scw", "instance", "server"]\n'
                      'cmd.append("create")\n'
                      'subprocess.run(cmd)\n'
                      'disk = ["scw", "block"]\n'
                      'disk.extend(["volume", "create"])\n'
                      'subprocess.run(disk)\n', set(), [3, 4, 6, 7]),
    # one module-wide table of variables read an earlier function's call with a later function's words
    "lint: a name two functions use is read in each function's own words": (
        "fixture.py", 'import subprocess\n'
                      'def a():\n'
                      '    cmd = ["scw", "instance", "server"]\n'
                      '    subprocess.run(cmd + ["create"])\n'
                      'def b():\n'
                      '    cmd = ["ls"]\n'
                      '    subprocess.run(cmd)\n'
                      'def c():\n'
                      '    api = "https://api.scaleway.com/instance/v1/zones/fr-par-2"\n'
                      '    requests.post(api + "/servers")\n'
                      'def d():\n'
                      '    api = "https://example.org"\n', set(), [4, 10]),
    # the growing line itself orders, not only the words left at the call
    "lint: an order grown in one branch": (
        "fixture.py", 'import subprocess\n'
                      'def a(new):\n'
                      '    cmd = ["scw", "instance", "server"]\n'
                      '    if new:\n'
                      '        cmd.append("create")\n'
                      '    else:\n'
                      '        cmd = ["scw", "instance", "server", "list"]\n'
                      '    subprocess.run(cmd)\n', set(), [5]),
    "lint: an order put together with insert": (
        "fixture.py", 'import subprocess\n'
                      'cmd = ["scw", "server", "create"]\n'
                      'cmd.insert(1, "instance")\n'
                      'subprocess.run(cmd)\n', set(), [3, 4]),
    "lint: google's client loaded by name": (
        "fixture.py", 'import importlib\n'
                      'genai = importlib.import_module("google.genai")\n'
                      'scaleway = __import__("scaleway.instance")\n'
                      'json = importlib.import_module("json")\n', set(), [2, 3]),
    "lint: a shell order broken over lines": (
        "rent.sh", '#!/bin/bash\nscw instance server \\\n  create type=L4-1-24G\nscw instance server list\n', set(),
        [2]),
    # runnable files beyond Python and shell are read; docs and data run nothing
    "lint: a Makefile": ("Makefile", "rent:\n\tscw instance server create\n", set(), [2]),
    "lint: a manifest": ("job.yaml", "args: [scw k8s pool create]\n", set(), [1]),
    "lint: a #! script": ("hook", "#!/bin/sh\nscw block volume create\n", set(), [2]),
    "lint: a doc": ("notes.md", "scw instance server create\n", set(), "runs nothing"),
    "lint: an order whose resource is a parameter": (
        "fixture.py", 'def order(what):\n'
                      '    scw("instance", what, "create")\n'
                      'def look(what):\n'
                      '    scw("instance", what, "list")\n', set(), [2]),
    "lint: an address joined from strings": (
        "fixture.py", 'import requests\n'
                      'API = "https://api.scaleway.com/instance/v1"\n'
                      'requests.post(API + f"/zones/{zone}/servers")\n'
                      'requests.post(f"{API}/zones/{zone}/ips")\n'
                      'requests.get(API + f"/zones/{zone}/servers/{server}/action")\n', set(), [3, 4]),
    # ALLOWED covered whole files once; a call in an allowed file passes only inside the parts named
    "lint: an allowed file orders only in its named parts": (
        "fixture.py", 'def create():\n'
                      '    scw("instance", "server", "create")\n'
                      'def later():\n'
                      '    scw("instance", "ip", "create")\n', {"create"}, [4]),
    "lint: reading and deleting": (
        "fixture.py", 'scw("instance", "server", "get", "id")\nscw("instance", "server", "delete", "id")\n'
                      'assert command[:4] == ["scw", "instance", "server", "create"]\n'
                      'API = "https://api.scaleway.com/instance/v1/zones/{zone}/servers/{server}/action"\n'
                      'from score.adapters import compute\n', set(), []),
}


def lint_measures():
    """The lint over each LINT_CASES fixture, written to a fresh folder, and over every tracked runnable file, side by
    side: {measure: the paid lines it found, or "runs nothing"}."""
    found = {}
    for name, (file_name, text, parts, _) in LINT_CASES.items():
        path = pathlib.Path(tempfile.mkdtemp()) / file_name
        path.write_text(text)
        found[name] = [line for line, _ in outside_allowed(path, parts)] if runnable(path) else "runs nothing"
    paths = tracked_sources()
    with concurrent.futures.ProcessPoolExecutor(mp_context=multiprocessing.get_context("fork")) as pool:
        found["lint: the repository's paid calls outside the ledgered clients"] = {
            path: calls for path, calls in zip(paths, pool.map(repository_calls, paths, chunksize=16)) if calls}
    return found


def recorded_price():
    """surfaces-paint as its recorded runs price it: the median of two runs' euros over units, the runs, their
    sources, no count rule, forecast by models."""
    runs = per_unit.RECORDED["surfaces-paint"]["runs"]
    each = sorted(run["euros"] / run["units"] for run in runs)
    return round((each[0] + each[1]) / 2, 5), len(runs), [run["source"] for run in runs], None, "models"


def warm_price():
    """Pixal3D warm: 52 timed L4 jobs, the saved bill's L4 hour, the median job three at once plus 10%, and its timed
    machines' own set-ups; settle, outside WARM and BATCH, kept."""
    hourly = per_unit.hourly("L4-1-24G")
    setups = per_unit.row_setups(per_unit.warm_rows(per_unit.WARM["pixal"]))
    return (52, 52, 0.7875, round(1358.404 / 3 * hourly / 3600 * 1.1, 5), 3, 1358.404, per_unit.spread(setups), SETTLE)


EXPECTED = {
    "paper: scrub keeps only the public roots": {"folder": "tmp/x", "jobs": ["$PROPS/w"],
                                                 "deep": {"path": "$HOME/.cache/y"}},
    "paper: a row without kind is tagged pixal": {"pixal-1": ("pixal", False)},
    "paper: the bill is the ledger and what it misses": {  # the late row is after the read
        "ledger month": 2.28, "not in ledger": {"storage": 1.0, "compute-not-in-ledger": 0.87}, "adds up": True},
    "paper: an engine run is typed by its price": "L4-1-24G",
    "paper: an engine run group names its card type": ["L4-1-24G 100%"],
    "paper: processor machines priced again by the started hour": (1.29, 2.36),  # two started hours
    "paper: an engine run is not priced again": Near(0.39375, 1e-9),
    "paper: R&D and production cover the ledger": (1.3938, 0.89),  # engine run and proof; review render and Pixal3D
    "paper: euros beyond the machines are not split": {"POP2-32C-128G": 1.29, "not split": 0.1,
                                                       "not recorded": 0.89375},
    "paper: order lines change no reconciliation": True,
    "paper: order lines change no table": True,
    "paper: order lines change no machine type": True,
    "paper: today is the bill less the last read before the day": Text(
        has=("today since 00:00 UTC EUR 18.00 (L4 15.00, L40S 2.00, addresses 1.00)",)),
    "paper: the day's first read is the last before it": ("2100", 10.0),
    "paper: spend since splits by track": {"agent-a1": 2.0, "who: surfaces": 1.0, "google: people": 0.2,
                                           "google: finishmap-name": 0.05},
    **{name: row[-1] for name, row in DAYS.items()},
    "unit: a batch in two ledgers is read once": [row["batch"] for row in LINES],
    "unit: pixal priced over the units each batch finished": ([0.1, 0.5], ["batch-1", "batch-2"]),
    "unit: light passes are the light stage's jobs": ([0.1], ["blender-1"]),
    "unit: settle is its own who's, a free drop counted": ([0.0], ["blender-2"]),
    "unit: a line ticketed for tiles is no bake's": ([], []),
    "unit: sound priced over the takes its line names": ([0.23], ["prove-1"]),
    "unit: an older sound line over its recorded takes": [0.0525 / 11],
    "unit: --add keeps every other stage and adds sound": (SETTLE, 0.23, "sound_takes"),
    "unit: --add prices a warm stage on its own timed jobs": (2, 90.0, True),
    "unit: google units are finished calls": ([0.14, 0.12], ["2026-10-11", "2026-10-12"]),
    "unit: the measured file": {
        "pixal likely": 0.3, "pixal runs": 2, "pixal count": {"json_keys": "takes.json"},
        "pixal forecast": "pixal_takes", "pixal per model": False, "closeup runs": 2,
        "closeup per model": round(297 / 217, 4)},  # a picture a row, a retry a rejected one
    "unit: pixal's high is the high quantile": Between(0.3, 0.5),
    "unit: stages with no lines are left out": [],
    "unit: a recorded stage is priced from its runs": recorded_price(),
    "unit: stages without a forecast rule and source": [],
    "unit: --rules-only keeps the measured numbers": (["x"], 0.1, "pixal_takes", "warm work time", "one", True),
    # the card's 0.37 min start wait and its 2.93 min in the machine before its 539.6 s job (11.93 working)
    "unit: a settle run's time from the paper's line": {
        "unit_seconds": {"likely": 539.6, "high": 539.6}, "slots": 1, "setup_minutes": {"likely": 3.304, "high": 3.304},
        "failed_start_share": 0, "holds": "machines"},
    # 0.60 start wait and 13.33 working minutes less three jobs' 1589 s run three at once
    "unit: a pixal batch's time from the paper's line": (629.98, 3, {"likely": 5.102, "high": 5.102}),
    "unit: a stage with no line says why": Text(matches=(r"\Ano ledger line",)),
    "unit: a stage whose lines time no set-up says so": (600.0, {"why": "no line read here timed a machine's set-up"}),
    # a job's time, not the batch's throughput: the working minutes times the jobs each machine ran at once
    "unit: a line's seconds by its working minutes and slots": ([300.0] * 4, [600.0] * 4, []),
    "unit: writing times in place keeps a measured time": (30.0, True, {"plan": {"likely": 2.0}}),
    "unit: a google stage's time from its calls": {
        "slots": 1, "holds": "calls", "failed_start_share": round(1 / 3, 3), "lines": 2, "likely": 45.0,
        "why with no ledger": True, "why with no calls": True},
    "unit: a Batch API row is unmeasured": Text(  # a Batch API row's whole job, not its calls
        has=("['why']: ", "1 request(s) at once timed only (2 calls, 45 s likely")),
    "unit: node minutes are the store's finish records": (  # a carried record is no make
        ["plan@hangar", "plan@lab", "concept@lab"], 4.0, 2, 1.0),
    "unit: a warm stage at the bill's price plus the overhead": warm_price(),
    "unit: a batch stage is half its standard calls": (  # no bill share on a Google stage, no batch call timed
        round(per_unit.PRO_PICTURES["likely"] / 2, 5), True, "models", True, True),
    "unit: --times-only keeps every euro": (True, True, True),
    **{name: row[-1] for name, row in LINT_CASES.items()},
    "lint: the repository's paid calls outside the ledgered clients": {},
}


def test_every_euro_is_ledgered_measured_and_adds_up_to_the_bill():
    """Every measure of the worlds above is what EXPECTED says, and nothing is measured that it does not name."""
    found = {**paper_measures(), **day_measures(), **unit_measures(), **lint_measures()}
    wrong = [f"{name}: {found.get(name, 'not measured')!r}, expected {expected!r}"
             for name, expected in EXPECTED.items() if name not in found or not holds(expected, found[name])]
    wrong += [f"{name}: measured, but EXPECTED has no row for it" for name in set(found) - set(EXPECTED)]
    assert not wrong, "\n".join(wrong)
