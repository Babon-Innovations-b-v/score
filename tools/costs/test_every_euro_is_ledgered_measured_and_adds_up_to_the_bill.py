"""tools/costs' invariant: every euro is ledgered before it is spent, measured before it prices, and adds up to the bill.

- costs.py (the paper's tables and the day's alarm): the ledgers add up to the bill. The paper's reconciliation is the
  ledger rows before the read plus every part of the bill the ledger misses (storage, unledgered compute), each figure
  worked out by hand from the ledger and bill written here (no cloud, no evidence files); an engine run is typed by its
  price, a processor machine priced again by the started hour, R&D and production cover the ledger, order lines change
  no table; the day's alarm (`reconcile-day`) fails when a ledgered line is over 5% off its bill and names the
  provider, fails on an empty or partial bill and on a missing ledger (faults of the review of C1, 2026-10-17), counts
  a run across midnight by its share and a machine still running at its price, and keeps storage and other lines out of
  the gap; `today` is the bill less the last read before the day; local roots never reach the paper's copy.
- per_unit.py: every per-unit price and time rests on measured lines only (owner, 2026-10-18 and 2026-10-20: never a
  flat guess). A batch is read once and priced over the units it finished (one that finished nothing left out); a line
  is the stage its ticket names; a Google unit is a finished call; likely the median, high the 90% quantile; a stage
  with no lines is left out, a time no line holds is a `why`, never a 0; a recorded stage is priced from its runs in
  git; the warm stages are their measured work at the bill's price plus the overhead, a batch stage half its standard
  calls; and the modes that write in place keep what they do not measure (`--times-only` leaves every euro of the
  repository's own file byte-identical, #14). Ledgers are written in the test, plus the paper's public ledger copy.
- Paid calls only through the clients that write a ledger line before the call (the owner's rule, tools/cloud/CLAUDE.md
  "Paid calls only through the ledgered clients"; 2026-10-17: a Google day billed about EUR 520 the ledger never held,
  and 21% of the bill was in no ledger row): a Gemini call through google_spend.generate, a Scaleway machine, disk,
  address or cluster pool through the backends that batch.rent and the cluster set-up drive; any other module that
  calls Gemini directly or orders one of those fails. A wording check by design, guarding that owner rule; the lint's
  own reading is pinned on fixtures whose paid lines are counted by hand. Read from each tracked Python file's syntax
  tree (its imports, by statement or by importlib.import_module or __import__ given a string; its strings joined with
  + and f-strings; and the scw words a call is given, read through variables, joined and starred lists, .append,
  .extend and .insert), and from the lines of every other runnable file (shell and other scripts, Makefiles,
  Dockerfiles, manifests, a #! file with no suffix), a line ending in a backslash joined with the next; vendor/ is
  third-party, and docs and data run nothing, so both are left out. A variable is read as the function it is in set it,
  in source order, and every setting or growing of one is checked too, so an order built in one branch counts. A word
  it cannot read (a function's parameter) between a product and "create" still counts as an order. It does not follow
  words across modules, through other functions' return values, through attributes (self.cmd), lists indexed or
  sliced, an .insert at an index it cannot read (read as the end), or built with % or .format.

No cloud, no machine; each file the tests write is in the run's own temp folder.

Breaks (each applied once, seen red, reverted, 2026-10-27), in costs.py (test_the_ledgers_add_up_to_the_bill[<check>]):
- `scrub` leaves the `$PROPS` root unreplaced -> local_roots_leave_the_copy.
- `untyped_kinds` reads every row as inferred -> a_row_without_kind_is_tagged_pixal.
- `month_rows` without `< before` (the late row counted) -> the_bill_is_the_ledger_and_what_it_misses,
  rnd_and_production_cover_the_ledger.
- `outside_compute` counts Storage as compute -> the_bill_is_the_ledger_and_what_it_misses.
- `engine_type` by the exact minute, not the started one -> an_engine_run_is_typed_by_its_price,
  an_engine_run_group_names_its_card_type, processor_machines_are_priced_again_by_the_started_hour.
- `per_product` prices processor types by the minute -> processor_machines_are_priced_again_by_the_started_hour.
- `is_rnd` without the `RND_WHO` rule -> rnd_and_production_cover_the_ledger.
- `types_before` drops the euros beyond the machines -> euros_beyond_the_machines_are_not_split.
- `today_line` does not subtract the baseline -> today_is_the_bill_less_the_last_read_before_the_day.
- `cloud_since` keeps rows from before `since`; `google_tracks` leaves out a started call never finished ->
  spend_since_splits_by_track.
- `DAY_TOLERANCE` 0.15 -> a_day_eleven_percent_off_its_bill_fails_and_names_the_provider; 0.03 ->
  a_day_within_five_percent_passes.
- `failed` lets a missing bill pass -> an_empty_or_partial_bill_fails, the_scaleway_day_comes_from_the_saved_reads.
- `bill_line_of` reads disks and addresses as other -> a_day_eleven_percent_off..., storage_and_other_lines_never_alarm.
- `snapshot_day_bill` takes the day's first read, or no read before the day as an empty start ->
  the_scaleway_day_comes_from_the_saved_reads.
- `cloud_window_lines` counts a run whole on its start day -> a_run_across_midnight_counts_its_share_of_the_day;
  leaves the open rents out -> a_machine_still_running_counts_at_its_price.
- `day_report_line` reports no unledgered lines -> storage_and_other_lines_never_alarm.
- `ledger_lines_of` reads a missing ledger as empty -> a_missing_ledger_fails_as_missing.
- `run_rows` without the order lines filter (`ledger.ORDER_LINES`) -> order_lines_stay_out_of_the_paper.

Breaks (each applied once, seen red, reverted, 2026-10-27), in per_unit.py:
- `ledger_lines` reads a batch in two ledgers twice -> test_a_batch_is_read_once_and_priced_over_the_units_it_finished.
- `cloud_measures` keeps a batch that finished no unit (its euros over one unit) -> that test, the ticketed-line test
  and test_the_file_holds_measured_stages_only_with_median_high_and_runs.
- `of_spec` reads a ticketed line by its fields; `line_units` without `SOUND_TAKES`; `warm_entry` ignores the stage's
  own jobs -> test_a_ticketed_line_is_the_stage_its_ticket_names_and_a_warm_stage_is_priced_on_its_own_timed_jobs.
- `google_measures` counts a started call -> test_google_units_are_finished_calls_of_the_stages_caller.
- `measure` keeps a stage with no lines; `per_model` inverted (models over units) -> test_the_file_holds_measured_...
- `recorded` leaves a run's euros not over its units -> test_a_recorded_stage_is_priced_from_its_runs_...
- `forecast` leaves the `one` rule's source empty -> test_every_stage_has_a_forecast_rule_with_its_source.
- `with_rules` rebuilds a measured stage bare -> test_rules_only_writes_the_rules_and_keeps_the_measured_numbers.
- `in_machine_setup` does not divide the jobs by the jobs at once -> test_a_cloud_stages_time_is_read_from_its_...
- `cloud_times` writes a set-up no line timed as 0 -> test_a_stage_whose_lines_time_no_set_up_says_so_...
- `unit_seconds` leaves the slots out -> test_a_line_without_machine_seconds_is_timed_by_its_working_minutes_...
- `kept_times` replaces a measured time with a why -> test_writing_times_in_place_keeps_a_measured_time_...
- `google_times` counts no failed call; `in_flight` counts a call twice; `batch_job_time` times a Batch API row as
  calls -> test_a_google_stages_time_is_its_calls_started_to_finished_and_how_many_ran_at_once.
- `spread`'s likely the max, not the median -> test_node_minutes_are_the_store_finish_records_minutes_by_stage (and
  the time tests).
- `warm_price` without `OVERHEAD` -> test_a_warm_stage_is_its_measured_work_..., and the byte-identical test.
- `batch_entry` at the full standard price -> test_a_batch_stage_is_half_its_measured_standard_calls_..., and the
  byte-identical test.
- `with_times` drops `likely_euros` -> test_writing_the_times_leaves_every_euro_of_the_per_unit_file_byte_identical.
(The old line "take the mean for `likely`" was tried and stays green: the fixtures' medians equal their means. It is
not claimed.)

Breaks (each applied once, seen red, reverted, 2026-10-27), in this file's lint:
- `PAID_TEXT` without Google's host -> test_a_module_calling_gemini_directly_fails.
- `paid_module` without `GEMINI_MODULES` -> test_a_module_loading_googles_client_fails.
- `SCW_PAID` without ("instance", "server") -> test_a_module_ordering_a_scaleway_machine_or_disk_fails (and the order
  tests).
- `sequence_words` reads no variable -> test_an_order_built_before_its_call_fails,
  test_a_name_two_functions_use_is_read_in_each_functions_own_words.
- `joined_text` reads no f-string -> test_an_address_joined_from_strings_fails; no `+` join -> that test and the
  two-functions test.
- `GROW_ARGUMENTS` without append and extend -> test_an_order_grown_by_append_or_extend_fails; without insert ->
  test_an_order_put_together_with_insert_fails.
- `scw_orders` does not check a setting's words -> test_an_order_grown_in_one_branch_fails.
- `DYNAMIC_IMPORTS` empty -> test_googles_client_loaded_by_name_fails.
- `logical_lines` joins no backslash line -> test_a_shell_order_broken_over_lines_fails.
- `runnable` Python and shell only -> test_runnable_files_beyond_python_and_shell_are_read.
- `orders_in` without the unread-word rule -> test_an_order_whose_resource_is_a_parameter_fails; reading delete as an
  order -> test_reading_and_deleting_are_not_paid_calls.
- `outside_allowed` allows every top-level part -> test_an_allowed_file_may_order_only_in_its_named_parts.
- `ALLOWED` without tools/cloud/google_spend.py -> test_the_repository_makes_paid_calls_only_through_the_ledgered_clients.
"""
import ast
import json
import pathlib
import re
import subprocess
import sys
import tempfile

import pytest

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
import costs  # noqa: E402
import per_unit  # noqa: E402


# --- costs.py: the ledgers add up to the bill ---

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


def local_roots_leave_the_copy():
    """A local path keeps only its part under the public roots; nothing of the home folder is left."""
    row = costs.scrub({"folder": costs.HOME + "/.claude/jobs/abc/tmp/x", "jobs": [costs.HOME + "/.farm-factory-props/w"],
                       "deep": {"path": costs.HOME + "/.cache/y"}})
    if row != {"folder": "tmp/x", "jobs": ["$PROPS/w"], "deep": {"path": "$HOME/.cache/y"}}:
        return [f"scrubbed to {row}"]
    return []


def a_row_without_kind_is_tagged_pixal():
    """Only the row with no kind is tagged, by its batch, and its exact fields say it is the runner's own."""
    tags = costs.untyped_kinds(ROWS)
    if list(tags) != ["pixal-1"] or tags["pixal-1"]["kind"] != "pixal" or tags["pixal-1"].get("inferred"):
        return [f"tags {tags}"]
    return []


def the_bill_is_the_ledger_and_what_it_misses():
    """Ledger rows before the read plus every part not in the ledger add up to the bill."""
    report = costs.reconcile(ROWS, BILL, READ)
    problems = []
    if report["ledger_month"] != 2.28:
        problems.append(f"ledger month {report['ledger_month']}, not 2.28 (the late row is after the read)")
    if report["not_in_ledger"] != {"storage": 1.0, "compute-not-in-ledger": 0.87}:
        problems.append(f"not in the ledger {report['not_in_ledger']}")
    if report["check"]["ledger_month + not_in_ledger"] != report["check"]["bill"]:
        problems.append(f"check {report['check']}")
    return problems


def an_engine_run_is_typed_by_its_price():
    """A row naming no machine takes the type whose price gives its euros by the started minute."""
    found = costs.engine_type(ROWS[1], costs.unit_prices(BILL))
    return [] if found == "L4-1-24G" else [f"typed {found}"]


def an_engine_run_group_names_its_card_type():
    """The kinds-of-batch table types an engine run by its price, as the machine-type table does."""
    rows = costs.month_rows(ROWS, "2026-10", READ)
    table = costs.per_group(rows, costs.untyped_kinds(ROWS), {}, costs.unit_prices(BILL))
    engine = [group for group in table if group["group"] == costs.group_of("game-gate")]
    return [] if engine and engine[0]["cards"] == "L4-1-24G 100%" else [f"engine runs {engine}"]


def processor_machines_are_priced_again_by_the_started_hour():
    """A processor machine the ledger priced by the minute costs its started hours at the bill's price."""
    rows = costs.month_rows(ROWS, "2026-10", READ)
    products = costs.per_product(rows, BILL, costs.unit_prices(BILL))
    pop = products["POP2-32C-128G"]
    if round(pop["ledger"], 2) != 1.29 or round(pop["at_billing_unit"], 2) != 2.36:
        return [f"POP2 {pop}, not ledger 1.29 and 2.36 at two started hours"]
    if abs(products["L4-1-24G"]["at_billing_unit"] - 0.39375) > 1e-9:
        return [f"L4 {products['L4-1-24G']}: the engine run is not priced again"]
    return []


def rnd_and_production_cover_the_ledger():
    """The engine run and the proof are R&D, the review render and the Pixal3D batch production, and both sum up."""
    rows = costs.month_rows(ROWS, "2026-10", READ)
    split = costs.split_rnd(rows, costs.untyped_kinds(ROWS))
    if round(split["R&D"], 4) != 1.3938 or round(split["production"], 2) != 0.89:
        return [f"split {split}"]
    return []


def euros_beyond_the_machines_are_not_split():
    """A row's euros that its machines do not hold read 'not split'; a row with no machines 'not recorded'."""
    euros = costs.types_before(ROWS, "2026-10-06")
    expected = {"POP2-32C-128G": 1.29, "not split": 0.1, "not recorded": 0.89375}
    if {key: round(value, 5) for key, value in euros.items() if round(value, 5)} != expected:
        return [f"types {euros}"]
    return []


def today_is_the_bill_less_the_last_read_before_the_day():
    """`today` takes the last snapshot read before 00:00 UTC as the day's start, and names L40S apart from L4."""
    import datetime
    import json
    import tempfile

    folder = pathlib.Path(tempfile.mkdtemp())
    line = lambda sku, euros: {"sku": sku, "euros": euros}  # noqa: E731
    (folder / "2026-10-11T2100Z.json").write_text(json.dumps({"lines": [line("/instance/server/l4_1_24g/x", 10.0)]}))
    (folder / "2026-10-12T0600Z.json").write_text(json.dumps({"lines": [line("/instance/server/l4_1_24g/x", 99.0)]}))
    now = datetime.datetime(2026, 10, 12, 18, 0, tzinfo=datetime.timezone.utc)
    baseline, since = costs.day_baseline(folder, now)
    lines = [line("/instance/server/l4_1_24g/x", 25.0), line("/instance/server/l40s_1_48g/x", 2.0),
             line("/network/ipam/ipv4/x", 1.0)]
    text = costs.today_line(lines, baseline, since, 7.0, "saved")
    problems = []
    if "today since 00:00 UTC EUR 18.00 (L4 15.00, L40S 2.00, addresses 1.00)" not in text:
        problems.append(text)
    first, since = costs.day_baseline(folder, datetime.datetime(2026, 10, 11, 23, 0, tzinfo=datetime.timezone.utc))
    if since != "2100" or first[0]["euros"] != 10.0:
        problems.append(f"the day's first read: {since} {first}")
    return problems


def spend_since_splits_by_track():
    """`today --since`: cloud rows by their worktree (older rows by who), Google calls by tag, a call started and never
    finished at its estimate, nothing from before the time."""
    since = costs.moment("2026-10-12T18:25Z")
    rows = [{"started": "2026-10-12T18:30:00Z", "worktree": "agent-a1", "euros": 2.0},
            {"started": "2026-10-12T18:40:00Z", "who": "surfaces", "euros": 1.0},
            {"started": "2026-10-12T18:00:00Z", "worktree": "agent-a1", "euros": 50.0}]
    google = [{"time": "2026-10-12T20:30:00+02:00", "call": "a", "state": "started", "model": "m", "estimate": 0.3,
               "tag": "people"},
              {"time": "2026-10-12T20:31:00+02:00", "call": "a", "state": "finished", "model": "m", "euros": 0.2,
               "tag": "people"},
              {"time": "2026-10-12T20:32:00+02:00", "call": "b", "state": "started", "model": "m", "estimate": 0.05,
               "caller": "finishmap-name"},
              {"time": "2026-10-12T20:00:00+02:00", "call": "c", "state": "finished", "model": "m", "euros": 9.0}]
    tracks = costs.cloud_since(rows, since) + costs.google_since(google, since, lambda model: 0.0)
    expected = {"agent-a1": 2.0, "who: surfaces": 1.0, "google: people": 0.2, "google: finishmap-name": 0.05}
    return [] if dict(tracks) == expected else [f"tracks {dict(tracks)}"]


def run_day_check(day_bill, cloud_rows, google_lines, snapshots=(), skip=()):
    """Run `reconcile-day 2026-10-11` on files written here: the day bill when given (else none), the ledgers (a
    ledger given as None is named but never written), and a bills folder holding `snapshots` ({"read", "lines"}
    each); (its exit code, its output)."""
    import json
    import subprocess
    import tempfile

    folder = pathlib.Path(tempfile.mkdtemp())
    bills = folder / "bills"
    bills.mkdir()
    for snapshot in snapshots:
        (bills / f"{snapshot['read'][:13]}{snapshot['read'][14:16]}Z.json").write_text(json.dumps(snapshot))
    if cloud_rows is not None:
        (folder / "ledger.jsonl").write_text("".join(json.dumps(row) + "\n" for row in cloud_rows))
    if google_lines is not None:
        (folder / "google.jsonl").write_text("".join(json.dumps(line) + "\n" for line in google_lines))
    command = [sys.executable, str(HERE / "costs.py"), "reconcile-day", "2026-10-11", "--ledger",
               str(folder / "ledger.jsonl"), "--google-ledger", str(folder / "google.jsonl"), "--bills", str(bills),
               *[part for provider in skip for part in ("--skip", provider)]]
    if day_bill is not None:
        (folder / "bill.json").write_text(json.dumps(day_bill))
        command.insert(4, str(folder / "bill.json"))
    done = subprocess.run(command, capture_output=True, text=True)
    return done.returncode, done.stdout + done.stderr


def a_day_eleven_percent_off_its_bill_fails_and_names_the_provider():
    """A Google day billed EUR 100 with EUR 89 in the ledger (11% off, over 5%) exits non-zero and says google; the
    Scaleway day beside it, within 5%, says within, its disks and addresses one line against the ledger's."""
    day_bill = {"google": [{"sku": "gemini-3-pro-image", "euros": 100.0}],
                "scaleway": [{"sku": "/instance/server/l4_1_24g/fr-par-2", "euros": 50.0},
                             {"sku": "/storage/block/volume-low-latency-5k/fr-par-2", "euros": 3.0},
                             {"sku": "/network/ipam/ipv4/fr-par-2", "euros": 2.0}]}
    cloud_rows = [{"started": "2026-10-11T09:00:00Z", "kind": "pixal", "euros": 51.0},
                  {"started": "2026-10-11T10:00:00Z", "kind": "disk-and-address", "euros": 4.5},
                  {"started": "2026-10-12T10:00:00Z", "kind": "pixal", "euros": 99.0}]
    google_lines = [{"time": "2026-10-11T10:00:00+02:00", "day": "2026-10-11", "call": "a", "state": "started",
                     "model": "m", "estimate": 0.15},
                    {"time": "2026-10-11T10:01:00+02:00", "day": "2026-10-11", "call": "a", "state": "finished",
                     "model": "m", "euros": 89.0},
                    {"time": "2026-10-12T10:01:00+02:00", "day": "2026-10-12", "call": "b", "state": "finished",
                     "model": "m", "euros": 11.0}]
    code, output = run_day_check(day_bill, cloud_rows, google_lines)
    problems = []
    if code == 0:
        problems.append(f"exit 0 on an 11% gap: {output}")
    google = [line for line in output.splitlines() if line.startswith("google:")]
    if not google or "calls: bill 100.00, ledgers 89.00, 11.0% apart; over" not in google[0]:
        problems.append(f"google not named as over: {output}")
    scaleway = [line for line in output.splitlines() if line.startswith("scaleway:")]
    if not scaleway or "within" not in scaleway[0] or "over" in scaleway[0] \
            or "disks and addresses: bill 5.00, ledgers 4.50" not in scaleway[0]:
        problems.append(f"scaleway line: {output}")
    return problems


def a_day_within_five_percent_passes():
    """A bill of EUR 100 against EUR 96 in the ledgers exits 0, Google left out on purpose."""
    code, output = run_day_check({"scaleway": [{"sku": "/instance/server/l4_1_24g/fr-par-2", "euros": 100.0}]},
                                 [{"started": "2026-10-11T09:00:00Z", "kind": "pixal", "euros": 96.0}], [],
                                 skip=["google"])
    return [] if code == 0 and "within" in output else [f"exit {code}: {output}"]


def an_empty_or_partial_bill_fails():
    """Fault (review of C1, 2026-10-17): a bill of {} or one without a provider exited 0, so an empty bill read as
    all clear. A provider with no bill fails and is named, unless left out with --skip."""
    problems = []
    code, output = run_day_check({}, [], [])
    if code == 0 or "google: no bill" not in output or "scaleway: no bill" not in output:
        problems.append(f"an empty bill: exit {code}: {output}")
    code, output = run_day_check({"google": [{"sku": "m", "euros": 1.0}]}, [],
                                 [{"day": "2026-10-11", "call": "a", "state": "finished", "model": "m", "euros": 1.0}])
    if code == 0 or "scaleway: no bill" not in output:
        problems.append(f"a bill without scaleway: exit {code}: {output}")
    return problems


def snapshot(read, machines, storage=0.0):
    """One saved read of the month's Scaleway bill: its machines and object storage so far."""
    return {"read": read, "lines": [{"sku": "/instance/server/l4_1_24g/fr-par-2", "euros": machines},
                                    {"sku": "/storage/obj/usage/fr-par", "euros": storage}]}


def the_scaleway_day_comes_from_the_saved_reads():
    """Fault (review of C1, 2026-10-17): nothing built the day's bill, so the alarm needed a hand-made file. With no
    file, the Scaleway day is the last read of the day less the last read before it, and the ledger is taken over
    the same window."""
    reads = [snapshot("2026-10-10T23:00:00+00:00", 100.0), snapshot("2026-10-11T12:00:00+00:00", 120.0),
             snapshot("2026-10-11T23:30:00+00:00", 150.0, storage=10.0)]
    rows = [{"started": "2026-10-11T09:00:00Z", "kind": "pixal", "wall_minutes": 60, "euros": 50.0}]
    code, output = run_day_check(None, rows, [], snapshots=reads, skip=["google"])
    problems = []
    if code != 0 or "machines: bill 50.00, ledgers 50.00" not in output:
        problems.append(f"exit {code}: {output}")
    if "not in any ledger: storage 10.00" not in output:
        problems.append(f"storage not reported apart: {output}")
    code, output = run_day_check(None, rows, [], snapshots=reads[1:], skip=["google"])
    if code == 0 or "scaleway: no bill" not in output:
        problems.append(f"no read before the day: exit {code}: {output}")
    return problems


def a_run_across_midnight_counts_its_share_of_the_day():
    """Fault (review of C1, 2026-10-17): a run was counted whole on the day it started, so one crossing midnight
    alarmed on both days. Its euros are spread over its hours: 3 of its 4 hours fall in the window."""
    reads = [snapshot("2026-10-10T23:00:00+00:00", 0.0), snapshot("2026-10-11T23:30:00+00:00", 30.0)]
    rows = [{"started": "2026-10-10T22:00:00Z", "kind": "pixal", "wall_minutes": 240, "euros": 40.0}]
    code, output = run_day_check(None, rows, [], snapshots=reads, skip=["google"])
    return [] if code == 0 and "machines: bill 30.00, ledgers 30.00" in output else [f"exit {code}: {output}"]


def storage_and_other_lines_never_alarm():
    """Fault (review of C1, 2026-10-17): storage, registry, secrets and cluster lines have no ledger rows, yet the
    totals were compared, so a heavy storage day alarmed. They are reported apart and kept out of the gap."""
    day_bill = {"scaleway": [{"sku": "/instance/server/l4_1_24g/fr-par-2", "euros": 20.0},
                             {"sku": "/storage/obj/usage/fr-par", "euros": 40.0},
                             {"sku": "/paas/secret_manager/access/fr-par", "euros": 5.0}]}
    code, output = run_day_check(day_bill, [{"started": "2026-10-11T09:00:00Z", "kind": "pixal", "euros": 20.0}],
                                 [], skip=["google"])
    if code != 0 or "not in any ledger: storage 40.00, other 5.00" not in output:
        return [f"exit {code}: {output}"]
    return []


def a_machine_still_running_counts_at_its_price():
    """Fault (review of C1, 2026-10-17): a run still going has no row yet, so its day alarmed. Its started line counts
    at its price up to its deadline: 60 minutes at EUR 0.10."""
    line = {"started": "2026-10-11T10:00:00Z", "batch": "rent-pixal-9-1", "kind": "rent-started", "run": "pixal-9",
            "name": "pixal-9-1", "price": 0.1, "deadline": costs.moment("2026-10-11T11:00:00Z"), "euros": 0.0}
    code, output = run_day_check({"scaleway": [{"sku": "/instance/server/l4_1_24g/fr-par-2", "euros": 6.0}]}, [line],
                                 [], skip=["google"])
    return [] if code == 0 and "machines: bill 6.00, ledgers 6.00" in output else [f"exit {code}: {output}"]


def a_missing_ledger_fails_as_missing():
    """Fault (review of C1, 2026-10-17): a ledger path that does not exist read as an empty ledger, so the day printed
    'ledgers 0.00', 84-94% apart, and blamed spend outside the ledger when the ledger file itself was missing. A
    missing ledger fails as missing and names its path."""
    problems = []
    day_bill = {"scaleway": [{"sku": "/instance/server/l4_1_24g/fr-par-2", "euros": 20.0}],
                "google": [{"sku": "m", "euros": 1.0}]}
    code, output = run_day_check(day_bill, None, [], skip=["google"])
    if code == 0 or "scaleway: no ledger at " not in output or "ledgers 0.00" in output:
        problems.append(f"no cloud ledger: exit {code}: {output}")
    code, output = run_day_check(day_bill, [{"started": "2026-10-11T09:00:00Z", "kind": "pixal", "euros": 20.0}],
                                 None)
    if code == 0 or "google: no ledger at " not in output or "scaleway: machines" not in output:
        problems.append(f"no Google ledger: exit {code}: {output}")
    return problems


ORDER_ROWS = [
    {"started": "2026-10-04T09:00:00Z", "batch": "rent-pixal-2-1", "kind": "rent-started", "state": "started",
     "run": "pixal-2", "name": "pixal-2-1", "type": "L4-1-24G", "price": 0.75, "deadline": None, "machines": [],
     "attempts": [], "machine_minutes": 0.0, "euros": 0.0},
    {"started": "2026-10-04T09:00:01Z", "batch": "rent-pixal-2-1", "kind": "rent-refused", "state": "refused",
     "name": "pixal-2-1", "reason": "out of stock", "machines": [], "attempts": [], "machine_minutes": 0.0,
     "euros": 0.0},
    {"started": "2026-10-11T09:00:00Z", "batch": "order-pool-p", "kind": "order-started", "state": "started",
     "what": "pool", "name": "p", "machines": [], "attempts": [], "machine_minutes": 0.0, "euros": 0.0}]


def order_lines_stay_out_of_the_paper():
    """Fault (review of C1, 2026-10-17): the started, refused and order lines are not batches, yet reconcile counted
    them in its rows, tables in its header and its per-kind table (a 0-euro rent-started group) and types_before as
    'not recorded'. The paper's commands give the same answer with them as without."""
    problems = []
    with_orders = ROWS + ORDER_ROWS
    if costs.reconcile(with_orders, BILL, READ) != costs.reconcile(ROWS, BILL, READ):
        problems.append("reconcile changed by order lines")
    reconciliation = costs.reconcile(ROWS, BILL, READ)
    if costs.tables(with_orders, reconciliation, BILL) != costs.tables(ROWS, reconciliation, BILL):
        problems.append("tables changed by order lines")
    if costs.types_before(with_orders, "2026-10-06") != costs.types_before(ROWS, "2026-10-06"):
        problems.append("types_before changed by order lines")
    return problems


CHECKS = [local_roots_leave_the_copy, a_row_without_kind_is_tagged_pixal, the_bill_is_the_ledger_and_what_it_misses,
          an_engine_run_is_typed_by_its_price, an_engine_run_group_names_its_card_type,
          processor_machines_are_priced_again_by_the_started_hour,
          rnd_and_production_cover_the_ledger, euros_beyond_the_machines_are_not_split,
          today_is_the_bill_less_the_last_read_before_the_day, spend_since_splits_by_track,
          a_day_eleven_percent_off_its_bill_fails_and_names_the_provider, a_day_within_five_percent_passes,
          an_empty_or_partial_bill_fails, the_scaleway_day_comes_from_the_saved_reads,
          a_run_across_midnight_counts_its_share_of_the_day, storage_and_other_lines_never_alarm,
          a_machine_still_running_counts_at_its_price, a_missing_ledger_fails_as_missing,
          order_lines_stay_out_of_the_paper]


@pytest.mark.parametrize("check", CHECKS, ids=[check.__name__ for check in CHECKS])
def test_the_ledgers_add_up_to_the_bill(check):
    """Each check gives the problems it found: none."""
    assert check() == []


# --- per_unit.py: every per-unit price and time rests on measured lines only ---

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


def written(rows):
    path = pathlib.Path(tempfile.mkdtemp()) / "ledger.jsonl"
    path.write_text("".join(json.dumps(row) + "\n" for row in rows) + "{torn\n")
    return path


def test_a_batch_is_read_once_and_priced_over_the_units_it_finished():
    """Each batch's euros over the units it finished; one finished nothing is left out; a batch in two ledgers once."""
    first, second = written(LINES), written(LINES[:1])
    lines = per_unit.ledger_lines([first, second])
    assert [line["batch"] for line, _ in lines] == [row["batch"] for row in LINES]
    each, batches = per_unit.cloud_measures(lines, per_unit.SPECS["pixal"])
    assert each == [0.1, 0.5] and batches == ["batch-1", "batch-2"]
    each, batches = per_unit.cloud_measures(lines, per_unit.SPECS["light-passes"])
    assert each == [0.1] and batches == ["blender-1"]
    each, batches = per_unit.cloud_measures(lines, per_unit.SPECS["settle"])
    assert each == [0.0] and batches == ["blender-2"]  # a free drop counts; another `who` is another job


def test_a_ticketed_line_is_the_stage_its_ticket_names_and_a_warm_stage_is_priced_on_its_own_timed_jobs():
    """A line whose ticket names another stage is no bake's, whatever its kind; sound's run is priced over the takes
    its line names (one here), an older line's over its takes recorded in SOUND_TAKES, a line naming none counts none;
    the bake's own jobs price it in place of every library job in the paper's copy, and the add mode keeps every
    other stage."""
    tiles = {"batch": "tiles-1", "kind": "library", "ticket": "surface-tiles@airlock abc", "jobs": ["a"], "euros": 0.2,
             "machines": []}
    kit = {"batch": "bake-1", "kind": "library", "ticket": "surfaces-bake@airlock abc", "jobs": ["a", "b"],
           "euros": 0.5,
           "machines": [{"type": "L4-1-24G", "started": True, "unit_seconds": [60.0, 120.0], "work_minutes": 4.0}]}
    take = {"batch": "prove-1", "kind": "prove", "who": "score runner, sound stage", "ticket": "sound@airlock abc",
            "euros": 0.23, "machines": [], "takes": 1}
    lines = per_unit.ledger_lines([written([tiles, take])])
    assert per_unit.cloud_measures(lines, per_unit.SPECS["surfaces-bake"]) == ([], [])
    assert per_unit.cloud_measures(lines, per_unit.SPECS["sound"]) == ([0.23], ["prove-1"])
    square = {**take, "batch": "prove-20261021-005847-4017578", "euros": 0.0525}
    del square["takes"]
    unnamed = {**square, "batch": "prove-2"}
    each, _ = per_unit.cloud_measures(per_unit.ledger_lines([written([square, unnamed])]), per_unit.SPECS["sound"])
    assert each == [0.0525 / 11], each
    out = pathlib.Path(tempfile.mkdtemp()) / "per-unit.json"
    settle = {"stage": "settle", "likely_euros": 0.59, "high_euros": 1.6, "runs": 3, "sources": {}}
    out.write_text(json.dumps({"read": [], "high_quantile": 0.9, "stages": {"settle": settle}}))
    per_unit.main(["--add", "--ledger", str(written([kit, take])), "--out", str(out)])
    found = json.loads(out.read_text())["stages"]
    assert found["settle"] == settle and found["sound"]["likely_euros"] == 0.23
    assert found["sound"]["forecast"]["rule"] == "sound_takes"
    bake = found["surfaces-bake"]
    assert bake["runs"] == 2 and bake["time"]["unit_seconds"]["likely"] == 90.0, bake
    assert "of its own jobs" in bake["sources"]["warm work"]


def test_google_units_are_finished_calls_of_the_stages_caller():
    """A call counts once it finished (or in the first format, written only then); started and failed do not."""
    each, days = per_unit.google_measures(CALLS, "pro")
    assert each == [0.14, 0.12] and days == ["2026-10-11", "2026-10-12"]


def test_the_file_holds_measured_stages_only_with_median_high_and_runs():
    """Likely the median, high the HIGH quantile, runs what they rest on; a stage with no lines is left out."""
    found = per_unit.measure(per_unit.ledger_lines([written(LINES)]), CALLS, "google-ledger.jsonl")
    assert found["pixal"]["likely_euros"] == 0.3 and found["pixal"]["runs"] == 2
    assert 0.3 < found["pixal"]["high_euros"] <= 0.5 and found["pixal"]["count"] == {"json_keys": "takes.json"}
    assert found["closeup"]["runs"] == 2 and "surfaces-maps" not in found and "surfaces-bake" not in found
    assert found["pixal"]["forecast"]["rule"] == "prop_takes" and "per_model" not in found["pixal"]["forecast"]
    assert found["closeup"]["forecast"]["per_model"] == round(297 / 217, 4)  # a picture a row, a retry a rejected one


def test_a_recorded_stage_is_priced_from_its_runs_with_their_sources_and_no_count_rule():
    """Each recorded run's euros over its units; likely their median; runs how many; the sources named."""
    found = per_unit.measure([], [], "google-ledger.jsonl")["surfaces-paint"]
    runs = per_unit.RECORDED["surfaces-paint"]["runs"]
    each = sorted(run["euros"] / run["units"] for run in runs)
    assert found["likely_euros"] == round((each[0] + each[1]) / 2, 5) and found["runs"] == len(runs)
    assert found["sources"]["recorded runs"] == [run["source"] for run in runs] and found["count"] is None
    assert found["forecast"]["rule"] == "models"


def test_every_stage_has_a_forecast_rule_with_its_source():
    for stage, spec in {**per_unit.SPECS, **per_unit.RECORDED}.items():
        found = per_unit.forecast(spec)["forecast"]
        assert found["rule"] and found["source"], stage


def test_rules_only_writes_the_rules_and_keeps_the_measured_numbers():
    measured = {"stage": "pixal", "unit": "model", "count": {"json_keys": "takes.json"}, "also": [],
                "likely_euros": 0.1, "high_euros": 0.4, "runs": 9, "sources": {"cloud batches": ["b1"]},
                "forecast": {"rule": "stale", "source": "old"}}
    out = pathlib.Path(tempfile.mkdtemp()) / "per-unit.json"
    out.write_text(json.dumps({"read": ["x"], "high_quantile": 0.9,
                               "stages": {"pixal": measured, "settle": {**measured, "stage": "settle"}}}))
    per_unit.main(["--rules-only", "--out", str(out)])
    found = json.loads(out.read_text())
    assert found["read"] == ["x"] and found["stages"]["settle"]["likely_euros"] == 0.1
    assert found["stages"]["pixal"]["forecast"]["rule"] == "prop_takes"
    assert found["stages"]["pixal"]["basis"] == "warm work time"  # a WARM stage priced by the owner's method
    assert found["stages"]["settle"]["forecast"]["rule"] == "one"
    assert set(per_unit.RECORDED) <= set(found["stages"])  # the recorded stages written again


PAPER = REPO / "paper/evidence/cloud/ledger.jsonl"


def paper_line(batch):
    """One real line of the paper's ledger copy, by its batch."""
    return next((line, source) for line, source in per_unit.ledger_lines([PAPER]) if line["batch"] == batch)


def test_a_cloud_stages_time_is_read_from_its_machines_own_job_seconds():
    """Real lines: a settle run's one job and its card's start wait; a Pixal3D batch of three at once on one card."""
    settle = per_unit.cloud_times([paper_line("blender-20261008-165605-2054366")], per_unit.SPECS["settle"])
    assert settle["unit_seconds"] == {"likely": 539.6, "high": 539.6} and settle["slots"] == 1, settle
    # set-up: the card's 0.37 min start wait and its 2.93 min in the machine before its 539.6 s job (11.93 working)
    assert settle["setup_minutes"] == {"likely": 3.304, "high": 3.304}, settle
    assert settle["failed_start_share"] == 0 and settle["holds"] == "machines"
    pixal = per_unit.cloud_times([paper_line("batch-20261008-134426-1833430")], per_unit.SPECS["pixal"])
    assert pixal["unit_seconds"]["likely"] == 629.98 and pixal["slots"] == 3, pixal
    # 0.60 start wait and 13.33 working minutes less three jobs' 1589 s run three at once
    assert pixal["setup_minutes"] == {"likely": 5.102, "high": 5.102}, pixal
    assert per_unit.cloud_times([], per_unit.SPECS["settle"])["why"].startswith("no ledger line")


def test_a_stage_whose_lines_time_no_set_up_says_so_and_never_writes_a_zero():
    line = {"batch": "b", "kind": "pixal", "models_done": 2, "machine_minutes": 20.0, "euros": 1.0}
    found = per_unit.cloud_times([(line, "here line 1")], per_unit.SPECS["pixal"])
    assert found["unit_seconds"]["likely"] == 600.0 and found["setup_minutes"] == {
        "why": "no line read here timed a machine's set-up"}, found


def test_a_line_without_machine_seconds_is_timed_by_its_working_minutes_and_slots_over_its_units():
    """A job's time, not the batch's throughput: the machines' working minutes times the jobs each ran at once."""
    line = {"batch": "b", "kind": "pixal", "models_done": 4, "machine_minutes": 20.0, "euros": 1.0}
    assert per_unit.unit_seconds(line, "models_done") == [300.0] * 4
    two = {**line, "per_card": 2, "machines": [{"cards": 1, "work_minutes": 10.0, "minutes": 11.0},
                                               {"cards": 1, "work_minutes": 10.0, "minutes": 11.0}]}
    assert per_unit.unit_seconds(two, "models_done") == [600.0] * 4
    assert per_unit.unit_seconds({**line, "machine_minutes": None}, "models_done") == []


def test_writing_times_in_place_keeps_a_measured_time_the_ledgers_read_here_do_not_hold():
    body = {"stages": {"closeup": {"time": {"unit_seconds": {"likely": 30.0, "high": 50.0}}},
                       "pixal": {"time": {"why": "none"}}}, "node_minutes": {"plan": {"likely": 2.0}}}
    stage_times, made = per_unit.kept_times(body, {"closeup": {"why": "no Google ledger read here"},
                                                   "pixal": {"unit_seconds": {"likely": 9.0, "high": 9.0}}}, {})
    assert stage_times["closeup"]["unit_seconds"]["likely"] == 30.0 and stage_times["pixal"]["unit_seconds"]
    assert made == {"plan": {"likely": 2.0}}


def test_a_google_stages_time_is_its_calls_started_to_finished_and_how_many_ran_at_once():
    calls = [{"call": "a", "caller": "pro", "state": "started", "time": "2026-10-12T10:00:00+02:00"},
             {"call": "b", "caller": "pro", "state": "started", "time": "2026-10-12T10:00:10+02:00"},
             {"call": "a", "caller": "pro", "state": "finished", "time": "2026-10-12T10:00:30+02:00", "euros": 0.1},
             {"call": "b", "caller": "pro", "state": "finished", "time": "2026-10-12T10:01:10+02:00", "euros": 0.1},
             {"call": "c", "caller": "pro", "state": "failed"}, {"caller": "pro", "euros": 0.1}]
    found = per_unit.google_times(calls, "pro", "google-ledger.jsonl")
    assert found["unit_seconds"]["likely"] == 45.0 and found["slots"] == 1 and found["holds"] == "calls"
    assert found["failed_start_share"] == round(1 / 3, 3) and found["lines"] == 2
    assert "why" in per_unit.google_times(calls, "pro", None) and "why" in per_unit.google_times([], "pro", "g")
    batch = per_unit.batch_job_time(calls, "pro", "google-ledger.jsonl")  # a Batch API row's whole job: unmeasured
    assert list(batch) == ["why"] and "1 request(s) at once timed only (2 calls, 45 s likely" in batch["why"]


def test_node_minutes_are_the_store_finish_records_minutes_by_stage():
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
    made = runs.node_times(store)  # a carried record is no make
    assert [row["node"] for row in made] == ["plan@hangar", "plan@lab", "concept@lab"]
    found = per_unit.node_minutes(made, root)
    assert found["plan"]["likely"] == 4.0 and found["plan"]["makes"] == 2 and found["concept"]["high"] == 1.0


def test_a_warm_stage_is_its_measured_work_over_the_cards_slots_at_the_bills_price_and_the_overhead():
    """Pixal3D: the L4 jobs' own seconds in the paper's ledger, three at once, the saved bill's L4 hour, plus 10%;
    a stage outside WARM and BATCH keeps every field."""
    other = {"stage": "settle", "likely_euros": 0.59, "high_euros": 1.6, "runs": 3, "sources": {}}
    found = per_unit.with_warm({"stages": {"pixal": {"stage": "pixal", "time": {}}, "settle": other}})["stages"]
    seconds = [value for row in per_unit.warm_rows(per_unit.WARM["pixal"]) for value in row["unit_seconds"]]
    assert len(seconds) == found["pixal"]["runs"] == 52 and round(per_unit.hourly("L4-1-24G"), 4) == 0.7875
    assert found["pixal"]["likely_euros"] == round(1358.404 / 3 * per_unit.hourly("L4-1-24G") / 3600 * 1.1, 5)
    assert found["pixal"]["time"]["slots"] == 3 and found["pixal"]["time"]["unit_seconds"]["likely"] == 1358.404
    setups = per_unit.row_setups(per_unit.warm_rows(per_unit.WARM["pixal"]))  # its timed machines' own set-ups
    assert found["pixal"]["time"]["setup_minutes"] == per_unit.spread(setups) and found["settle"] == other


def test_a_batch_stage_is_half_its_measured_standard_calls_and_a_route_ask_says_it_is_priced_from_the_lists():
    found = per_unit.with_warm({"stages": {}})["stages"]
    assert found["closeup"]["likely_euros"] == round(per_unit.PRO_PICTURES["likely"] / 2, 5)
    assert "google calls" in found["finish-route-list"]["sources"]  # no bill share on a Google stage
    assert found["finish-route-recheck"]["forecast"]["rule"] == "models" and found["finish-route-list"]["price_note"]
    assert found["finish-route-list"]["time"]["why"]  # no batch call timed: no ETA made up


def test_writing_the_times_leaves_every_euro_of_the_per_unit_file_byte_identical():
    """The repository's own per-unit file, its time written again from the paper's ledger copy: every field but the
    time fields is the same, byte for byte."""
    out = pathlib.Path(tempfile.mkdtemp()) / "per-unit.json"
    before = json.loads((REPO / "data/costs/per-unit.json").read_text())
    out.write_text(json.dumps(before, indent=1) + "\n")
    per_unit.main(["--times-only", "--ledger", str(PAPER), "--out", str(out)])
    after = json.loads(out.read_text())

    def without_time(body):
        return json.dumps({**{name: value for name, value in body.items() if name != "node_minutes"},
                           "stages": {stage: {name: value for name, value in found.items() if name != "time"}
                                      for stage, found in body["stages"].items()}}, indent=1)

    assert without_time(after) == without_time(before)
    assert set(after["stages"]) == set(before["stages"]) and all("time" in found for found in after["stages"].values())


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
                                         "before each billed order (address, data volume, server)",
                                         {"address", "data_volume", "make_server"}),
    "score/conductor/logs.py": ("the log scrubber names the Google key header to blank it, calls nothing",
                                {"SECRET_WORDS"}),
    str(pathlib.Path(__file__).resolve().relative_to(REPO)): (
        "this lint's pattern and its fixtures", {"PAID_TEXT", "test_a_module_calling_gemini_directly_fails",
                                        "test_a_module_ordering_a_scaleway_machine_or_disk_fails",
                                        "test_an_address_built_in_an_f_string_fails",
                                        "test_a_shell_order_broken_over_lines_fails",
                                        "test_runnable_files_beyond_python_and_shell_are_read"}),
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


def imported_paid_modules(tree):
    """(line, what) for each import of Google's Gemini clients or Scaleway's SDK, by an import statement or by
    importlib.import_module or __import__ given the module's name as a string."""
    found = []
    for node in ast.walk(tree):
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


def paid_strings(tree):
    """(line, what) for each string, f-string or joined string that names a paid host, key header or order."""
    states = variable_states(tree)
    found = []
    for node in ast.walk(tree):
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
    """(scope, the scope around it) for the module (None around it) and each function in it, outer before inner."""
    found, waiting = [], [(tree, None)]
    while waiting:
        scope, outer = waiting.pop(0)
        found.append((scope, outer))
        waiting += [(node, scope) for node in scope_members(scope) if isinstance(node, FUNCTIONS)]
    return found


def variable_states(tree):
    """{id(node): {variable: its words}} for each node, as the node's own function (or the module) had set its
    variables just before it in source order, starting from the words the scope around it left; a setting takes
    effect where it ends. So a name two functions both use is read from the function the node is in (review of C1,
    2026-10-17: one module-wide table read one function's call with another's words)."""
    states, left = {}, {None: {}}
    for scope, outer in scopes(tree):
        assigned = left[outer]
        events = []
        for node in scope_members(scope):
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


def scw_orders(tree):
    """(line, what) for each call given, list built with, or variable set or grown to scw words that order a billed
    resource: the words read through variables (as the node's own function set them), joined and starred lists,
    .append, .extend and .insert (sequence_words, setting)."""
    states = variable_states(tree)
    compared = {id(side) for node in ast.walk(tree) if isinstance(node, ast.Compare)
                for side in [node.left, *node.comparators]}
    found = set()
    for node in ast.walk(tree):
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
    return sorted(set(imported_paid_modules(tree) + paid_strings(tree) + scw_orders(tree)))


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


def fixture(source):
    """A module written to a fresh folder from `source`; its path."""
    path = pathlib.Path(tempfile.mkdtemp()) / "fixture.py"
    path.write_text(source)
    return path


def test_a_module_calling_gemini_directly_fails():
    path = fixture('import urllib.request\n'
                   'URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"\n'
                   'def ask(body):\n'
                   '    return urllib.request.urlopen(urllib.request.Request(URL, data=body))\n')
    assert [line for line, _ in paid_calls(path)] == [2], paid_calls(path)


def test_a_module_loading_googles_client_fails():
    path = fixture("from google import genai\nimport vertexai\n")
    assert [line for line, _ in paid_calls(path)] == [1, 2], paid_calls(path)


def test_a_module_ordering_a_scaleway_machine_or_disk_fails():
    path = fixture('import subprocess\n'
                   'subprocess.run(["scw", "instance", "server", "create", "type=L4-1-24G"])\n'
                   'scw("block", "volume", "create", "size=20GB")\n'
                   'subprocess.run("scw instance ip create zone=fr-par-2", shell=True)\n')
    assert [line for line, _ in paid_calls(path)] == [2, 3, 4], paid_calls(path)


def test_an_order_built_before_its_call_fails():
    """Fault (review, 2026-10-17): only words passed straight into one call were read, so an order put in a variable
    first, a list with more joined on, or a starred list came back clean."""
    path = fixture('import subprocess\n'
                   'cmd = ["scw", "instance", "server", "create"]\n'
                   'subprocess.run(cmd)\n'
                   'subprocess.run(["scw", "block", "volume", "create"] + extra)\n'
                   'subprocess.run([*["scw", "instance", "ip", "create"], "zone=fr-par-2"])\n'
                   'base = ["scw", "k8s", "pool"]\n'
                   'subprocess.run(base + ["create", "size=0"])\n')
    assert [line for line, _ in paid_calls(path)] == [2, 3, 4, 5, 7], paid_calls(path)


def test_an_address_built_in_an_f_string_fails():
    """Fault (review, 2026-10-17): an f-string splits into pieces, so the address was never seen whole; and the
    block API is v1alpha1, which a v1-only pattern missed."""
    path = fixture('zone = "fr-par-2"\n'
                   'SERVERS = f"https://api.scaleway.com/instance/v1/zones/{zone}/servers"\n'
                   'VOLUMES = "https://api.scaleway.com/block/v1alpha1/zones/fr-par-2/volumes"\n'
                   'ORDER = f"scw instance server create zone={zone}"\n')
    assert [line for line, _ in paid_calls(path)] == [2, 3, 4], paid_calls(path)


def test_an_order_grown_by_append_or_extend_fails():
    """Fault (review of C1, 2026-10-17): a list grown with .append or .extend was read only as first set, so an order
    finished by one came back clean."""
    path = fixture('import subprocess\n'
                   'cmd = ["scw", "instance", "server"]\n'
                   'cmd.append("create")\n'
                   'subprocess.run(cmd)\n'
                   'disk = ["scw", "block"]\n'
                   'disk.extend(["volume", "create"])\n'
                   'subprocess.run(disk)\n')
    assert [line for line, _ in paid_calls(path)] == [3, 4, 6, 7], paid_calls(path)


def test_a_name_two_functions_use_is_read_in_each_functions_own_words():
    """Fault (review of C1, 2026-10-17): variables were one module-wide table with only the last setting by line
    kept, so a call in an earlier function read a later function's words and its order came back clean."""
    path = fixture('import subprocess\n'
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
                   '    api = "https://example.org"\n')
    assert [line for line, _ in paid_calls(path)] == [4, 10], paid_calls(path)


def test_an_order_grown_in_one_branch_fails():
    """A list grown to an order in one branch and to something else after it still orders: the growing line itself
    is checked, not only the words left at the call."""
    path = fixture('import subprocess\n'
                   'def a(new):\n'
                   '    cmd = ["scw", "instance", "server"]\n'
                   '    if new:\n'
                   '        cmd.append("create")\n'
                   '    else:\n'
                   '        cmd = ["scw", "instance", "server", "list"]\n'
                   '    subprocess.run(cmd)\n')
    assert [line for line, _ in paid_calls(path)] == [5], paid_calls(path)


def test_an_order_put_together_with_insert_fails():
    """Fault (review of C1, 2026-10-17): .insert was not read, so `cmd.insert(1, "instance")` building an order passed."""
    path = fixture('import subprocess\n'
                   'cmd = ["scw", "server", "create"]\n'
                   'cmd.insert(1, "instance")\n'
                   'subprocess.run(cmd)\n')
    assert [line for line, _ in paid_calls(path)] == [3, 4], paid_calls(path)


def test_googles_client_loaded_by_name_fails():
    """Fault (review of C1, 2026-10-17): only import statements were read, so importlib.import_module("google.genai")
    passed."""
    path = fixture('import importlib\n'
                   'genai = importlib.import_module("google.genai")\n'
                   'scaleway = __import__("scaleway.instance")\n'
                   'json = importlib.import_module("json")\n')
    assert [line for line, _ in paid_calls(path)] == [2, 3], paid_calls(path)


def test_a_shell_order_broken_over_lines_fails():
    """Fault (review of C1, 2026-10-17): shell was matched one line at a time, so `scw instance server \\` with
    `create` on the next line passed."""
    path = pathlib.Path(tempfile.mkdtemp()) / "rent.sh"
    path.write_text('#!/bin/bash\nscw instance server \\\n  create type=L4-1-24G\nscw instance server list\n')
    assert [line for line, _ in paid_calls(path)] == [2], paid_calls(path)


def test_runnable_files_beyond_python_and_shell_are_read():
    """Fault (review of C1, 2026-10-17): only *.py and *.sh were scanned, so an order in a Makefile, Dockerfile,
    manifest or a #! script with no suffix passed. Docs and data are left out: they run nothing."""
    folder = pathlib.Path(tempfile.mkdtemp())
    names = {"Makefile": "rent:\n\tscw instance server create\n", "job.yaml": "args: [scw k8s pool create]\n",
             "hook": "#!/bin/sh\nscw block volume create\n", "notes.md": "scw instance server create\n"}
    for name, text in names.items():
        (folder / name).write_text(text)
    assert sorted(name for name in names if runnable(folder / name)) == ["Makefile", "hook", "job.yaml"]
    assert [line for line, _ in paid_calls(folder / "Makefile")] == [2]


def test_an_order_whose_resource_is_a_parameter_fails():
    """Fault (review of C1, 2026-10-17): a word given as a function's parameter cannot be read, so
    `scw("instance", what, "create")` came back clean. A product's create with an unread word between still orders."""
    path = fixture('def order(what):\n'
                   '    scw("instance", what, "create")\n'
                   'def look(what):\n'
                   '    scw("instance", what, "list")\n')
    assert [line for line, _ in paid_calls(path)] == [2], paid_calls(path)


def test_an_address_joined_from_strings_fails():
    """Fault (review of C1, 2026-10-17): only one string at a time was matched, so an order's address joined from a
    base and a path (with + or inside an f-string) came back clean."""
    path = fixture('import requests\n'
                   'API = "https://api.scaleway.com/instance/v1"\n'
                   'requests.post(API + f"/zones/{zone}/servers")\n'
                   'requests.post(f"{API}/zones/{zone}/ips")\n'
                   'requests.get(API + f"/zones/{zone}/servers/{server}/action")\n')
    assert [line for line, _ in paid_calls(path)] == [3, 4], paid_calls(path)


def test_an_allowed_file_may_order_only_in_its_named_parts():
    """Fault (review of C1, 2026-10-17): ALLOWED covered whole files, so a paid call added anywhere in the backend or
    in this file passed. A call in an allowed file passes only inside the top-level functions or constants named."""
    path = fixture('def create():\n'
                   '    scw("instance", "server", "create")\n'
                   'def later():\n'
                   '    scw("instance", "ip", "create")\n')
    assert [line for line, _ in outside_allowed(path, {"create"})] == [4], outside_allowed(path, {"create"})


def test_reading_and_deleting_are_not_paid_calls():
    path = fixture('scw("instance", "server", "get", "id")\nscw("instance", "server", "delete", "id")\n'
                   'assert command[:4] == ["scw", "instance", "server", "create"]\n'
                   'API = "https://api.scaleway.com/instance/v1/zones/{zone}/servers/{server}/action"\n'
                   'from score.adapters import compute\n')
    assert paid_calls(path) == []


def test_the_repository_makes_paid_calls_only_through_the_ledgered_clients():
    found = {path: calls for path in tracked_sources()
             for calls in [outside_allowed(REPO / path, ALLOWED.get(path, ("", set()))[1])] if calls}
    assert not found, ("call Gemini through google_spend.generate and rent through batch.rent, not directly: "
                       f"{found}")

