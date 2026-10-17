"""The cost tables' sums (costs.py), on a ledger and a bill written in the test: no cloud, no evidence files.

    python3 tools/costs/costs_test.py
"""
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import costs  # noqa: E402

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


def run_day_check(day_bill, cloud_rows, google_lines):
    """Run `reconcile-day 2026-10-11` on files written here; (its exit code, its output)."""
    import json
    import subprocess
    import tempfile

    folder = pathlib.Path(tempfile.mkdtemp())
    (folder / "bill.json").write_text(json.dumps(day_bill))
    (folder / "ledger.jsonl").write_text("".join(json.dumps(row) + "\n" for row in cloud_rows))
    (folder / "google.jsonl").write_text("".join(json.dumps(line) + "\n" for line in google_lines))
    done = subprocess.run([sys.executable, str(HERE / "costs.py"), "reconcile-day", "2026-10-11",
                           str(folder / "bill.json"), "--ledger", str(folder / "ledger.jsonl"),
                           "--google-ledger", str(folder / "google.jsonl")], capture_output=True, text=True)
    return done.returncode, done.stdout + done.stderr


def a_day_eleven_percent_off_its_bill_fails_and_names_the_provider():
    """A Google day billed EUR 100 with EUR 89 in the ledger (11% off, over 5%) exits non-zero and says google; the
    Scaleway day beside it, within 5%, says within, its disks and addresses as their own lines."""
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
    if not google or "11.0% apart, over" not in google[0]:
        problems.append(f"google not named as over: {output}")
    scaleway = [line for line in output.splitlines() if line.startswith("scaleway:")]
    if not scaleway or "within" not in scaleway[0] or "disks 3.00" not in scaleway[0] \
            or "addresses 2.00" not in scaleway[0] or "disks and addresses 4.50" not in scaleway[0]:
        problems.append(f"scaleway line: {output}")
    return problems


def a_day_within_five_percent_passes():
    """A bill of EUR 100 against EUR 96 in the ledgers exits 0."""
    code, output = run_day_check({"scaleway": [{"sku": "/instance/server/l4_1_24g/fr-par-2", "euros": 100.0}]},
                                 [{"started": "2026-10-11T09:00:00Z", "kind": "pixal", "euros": 96.0}], [])
    return [] if code == 0 and "within" in output else [f"exit {code}: {output}"]


def main():
    """Run every check; exit 1 on any problem."""
    checks = [local_roots_leave_the_copy, a_row_without_kind_is_tagged_pixal, the_bill_is_the_ledger_and_what_it_misses,
              an_engine_run_is_typed_by_its_price, an_engine_run_group_names_its_card_type,
              processor_machines_are_priced_again_by_the_started_hour,
              rnd_and_production_cover_the_ledger, euros_beyond_the_machines_are_not_split,
              today_is_the_bill_less_the_last_read_before_the_day, spend_since_splits_by_track,
              a_day_eleven_percent_off_its_bill_fails_and_names_the_provider, a_day_within_five_percent_passes]
    problems = [f"{check.__name__}: {problem}" for check in checks for problem in check()]
    for problem in problems:
        print(problem)
    print(f"costs: {len(checks)} checks, {len(problems)} problems")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[2] / "conftest.py"))["refuse_outside_sandbox"]()
    main()
