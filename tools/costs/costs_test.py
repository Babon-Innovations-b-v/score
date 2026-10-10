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


def main():
    """Run every check; exit 1 on any problem."""
    checks = [local_roots_leave_the_copy, a_row_without_kind_is_tagged_pixal, the_bill_is_the_ledger_and_what_it_misses,
              an_engine_run_is_typed_by_its_price, an_engine_run_group_names_its_card_type,
              processor_machines_are_priced_again_by_the_started_hour,
              rnd_and_production_cover_the_ledger, euros_beyond_the_machines_are_not_split]
    problems = [f"{check.__name__}: {problem}" for check in checks for problem in check()]
    for problem in problems:
        print(problem)
    print(f"costs: {len(checks)} checks, {len(problems)} problems")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
