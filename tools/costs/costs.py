"""The cloud's cost and time from the ledger and the provider's bill, as the paper's cost tables give them.

    python3 tools/costs/costs.py scrub <ledger.jsonl> <rows> <out.jsonl>      # the ledger's first rows, no local paths
    python3 tools/costs/costs.py reconcile <ledger.jsonl> <bill.json> <read> <out.json>
    python3 tools/costs/costs.py tables <ledger.jsonl> <reconciliation.json> <bill.json> <out.txt>
    python3 tools/costs/costs.py types <ledger.jsonl> <rows> <before>         # cost by machine type, an earlier window

Every runner writes one ledger row per batch (paper/evidence/cloud/ledger.jsonl is a scrubbed copy); the rows are never
rewritten. `reconcile` tags the rows written before a runner named its kind and sets the month's bill (one
bill-<read>.json, the provider's consumption lines) against the ledger. `tables` writes the paper's tables for that
month: cost and time per kind of batch and per card type, R&D against production, and the bill's compute per product
against the ledger's. Each command prints one line; the tables go to the file.
"""
import argparse
import collections
import json
import math
import pathlib
import re
import statistics

HOME = str(pathlib.Path.home())
# Local roots in the ledger's folders and jobs, and what the public copy writes instead.
LOCAL_ROOTS = [
    (re.escape(HOME) + r"/\.claude/jobs/[^/]+/", ""),
    (re.escape(HOME) + r"/projects/score/\.claude/worktrees/[^/]+/", ""),
    (re.escape(HOME) + r"/projects/score/", ""),
    (re.escape(HOME) + r"/\.farm-factory-props", "$PROPS"),
    (re.escape(HOME) + r"/\.farm-factory-motion", "$MOTION"),
    (re.escape(HOME) + r"/", "$HOME/"),
]
# The exact fields of batch.py's Pixal3D row before commit 423c229 (2026-10-08 11:41Z) added "kind": "pixal".
PIXAL_FIELDS = {"started", "batch", "per_card", "machines", "machine_minutes", "euros", "models", "models_done",
                "card_minutes", "wall_minutes", "job_seconds"}
NOT_COMPUTE = {"Storage": "storage", "Network": "ip-addresses", "Containers": "registry-and-clusters",
               "Object Storage": "object-storage", "Security and Identity": "secrets"}
# Kinds of batch, as the paper groups them. A kind in none of them reads "Other: <kind>".
GROUPS = [
    ("Blender: settling, renders, review pages, close-ups", {"blender", "closeups"}),
    ("Pixal3D models", {"pixal"}),
    ("Open judge", {"judge"}),
    ("Library bake", {"library"}),
    ("Characters: chain, rigging, drapes", {"characters", "unirig", "drapes-sim", "drapes-setup-lens"}),
    ("Parts and segments", {"parts", "meshparts", "segment", "finish-masks", "similar"}),
    ("Engine runs: tests, shots, benchmarks, warm pool", {"game-gate", "game-shots", "game-bench", "game-idle",
                                                          "game-image"}),
    ("Container images, proofs, kernel warm-up", {"images", "images-prove", "images-proof", "prove", "base", "warm",
                                                  "hold"}),
    ("Open picture models: FLUX.2 klein, Qwen-Image-Edit", {"pictures", "pictures-20b", "unlit"}),
    ("Method experiments: terrain, plants, clay, Infinigen", {"infinigen"}),
    ("Sound", {"moss-sound", "sfx-trial"}),
]
EXPERIMENT_PREFIXES = ("experiment", "mars-build")
# R&D: work on the framework rather than on a world. Whole groups, single kinds, and rows whose `who` names a
# benchmark, a proof or a before-and-after comparison.
RND_GROUPS = {"Engine runs: tests, shots, benchmarks, warm pool", "Container images, proofs, kernel warm-up",
              "Method experiments: terrain, plants, clay, Infinigen"}
RND_KINDS = {"drapes-sim", "sfx-trial"}
RND_WHO = re.compile(r"^(agent-tools|bench|fleet|fw-|k8s-|rw |bl-blocks)|proof|variants|\bdev\b|test|before|after")
# The provider bills these types by the started hour and the cards by the minute (tools/props/cloud/backends/
# scaleway.py, price()).
HOURLY_PREFIXES = ("POP2-", "RENDER-")


def read_rows(path, rows=None):
    """The ledger's rows in file order, the first `rows` of them when given."""
    lines = [line for line in pathlib.Path(path).read_text().splitlines() if line.strip()]
    return [json.loads(line) for line in lines[:rows]]


def scrub(value):
    """`value` with every local root in its strings replaced by its public name."""
    if isinstance(value, str):
        for pattern, public in LOCAL_ROOTS:
            value = re.sub(pattern, lambda _match, public=public: public, value)
        return value
    if isinstance(value, list):
        return [scrub(item) for item in value]
    if isinstance(value, dict):
        return {key: scrub(item) for key, item in value.items()}
    return value


def month_rows(rows, month, before):
    """The rows that started in `month` (YYYY-MM) before the time `before`."""
    return [row for row in rows if row["started"].startswith(month) and row["started"] < before]


def untyped_kinds(rows):
    """A kind for every row that carries none, by batch: all are Pixal3D rows from before the runner named its kind."""
    tags = {}
    for row in rows:
        if row.get("kind"):
            continue
        tag = {"kind": "pixal", "euros": row["euros"], "started": row["started"]}
        if set(row) == PIXAL_FIELDS:
            tag["evidence"] = ("the exact fields of batch.py's Pixal3D ledger entry before commit 423c229 "
                               "(2026-10-08 11:41Z) added \"kind\": \"pixal\"; the first tagged pixal row is 11:42:44Z")
        else:
            tag["inferred"] = True
            tag["evidence"] = ("an earlier Pixal3D batch entry (models, models_done, at_once, generate_minutes, "
                               "peak_gb); inferred from its fields, no commit found")
        tags[row["batch"]] = tag
    return tags


def bill_lines(bill):
    """The bill's euros per (category, product), largest first."""
    lines = collections.defaultdict(float)
    for line in bill:
        lines[(line["category_name"], line["product_name"])] += line["euros"]
    return [{"category": category, "product": product, "euros": round(euros, 2)}
            for (category, product), euros in sorted(lines.items(), key=lambda item: -item[1])]


def outside_compute(bill):
    """The bill's euros that are not machines, by what they pay for, largest first."""
    outside = collections.defaultdict(float)
    for line in bill:
        if line["category_name"] != "Compute":
            outside[NOT_COMPUTE.get(line["category_name"], line["category_name"])] += line["euros"]
    return {name: round(euros, 2) for name, euros in sorted(outside.items(), key=lambda item: -item[1])}


def reconcile(rows, bill, read):
    """The reconciliation of the ledger's month of `read` with the bill read at `read` (YYYY-MM-DDTHH:MMZ)."""
    month = read[:7]
    tags = untyped_kinds(rows)
    total = round(sum(line["euros"] for line in bill), 2)
    compute = round(sum(line["euros"] for line in bill if line["category_name"] == "Compute"), 2)
    ledger_month = round(sum(row["euros"] for row in month_rows(rows, month, read)), 2)
    not_in_ledger = outside_compute(bill)
    not_in_ledger["compute-not-in-ledger"] = round(compute - ledger_month, 2)
    return {
        "about": "Reconciliation of ledger.jsonl with the provider's bill. ledger.jsonl is never rewritten: 'kinds' "
                 "tags rows that carry no kind (by batch name), 'bill' is the provider's month bill as read, "
                 "'not_in_ledger' its euros that no ledger row holds (storage, IP addresses, registry, clusters, "
                 "object storage, secrets, and compute the ledger misses).",
        "made": read, "ledger_rows": len(rows), "ledger_last_started": max(row["started"] for row in rows),
        "kinds": tags,
        "kinds_euros": {"all": round(sum(tag["euros"] for tag in tags.values()), 2),
                        month: round(sum(tag["euros"] for tag in tags.values() if tag["started"].startswith(month)),
                                     2)},
        "bill": {"month": month, "read": read, "total": total, "compute": compute, "lines": bill_lines(bill),
                 "note": "the bill lags by hours; ledger rows that started after its last hour make the compute gap "
                         "look smaller than it is"},
        "ledger_month": ledger_month,
        "not_in_ledger": not_in_ledger,
        "check": {"ledger_month + not_in_ledger": round(ledger_month + sum(not_in_ledger.values()), 2),
                  "bill": total},
    }


def kind_of(row, tags):
    """The row's kind, or the reconciliation's tag for it."""
    return row.get("kind") or tags.get(row["batch"], {}).get("kind") or "(none)"


def group_of(kind):
    """The paper's group for a kind of batch."""
    for name, kinds in GROUPS:
        if kind in kinds:
            return name
    if kind.startswith(EXPERIMENT_PREFIXES):
        return "Method experiments: terrain, plants, clay, Infinigen"
    return "Other: " + kind


def is_rnd(row, tags):
    """Whether the row is work on the framework (R&D) rather than on a world."""
    kind = kind_of(row, tags)
    return group_of(kind) in RND_GROUPS or kind in RND_KINDS or bool(RND_WHO.search(row.get("who") or ""))


def unit_prices(bill):
    """Euros an hour per (machine type, zone), read off the bill's compute lines."""
    prices = {}
    for line in bill:
        if line["category_name"] != "Compute" or not float(line["billed_quantity"]):
            continue
        _, _, _, sku, zone = line["sku"].split("/")
        machine_type = sku.upper().replace("_", "-")
        per_unit = line["euros"] / float(line["billed_quantity"])
        prices[(machine_type, zone)] = per_unit if machine_type.startswith(HOURLY_PREFIXES) else per_unit * 60
    return prices


def hourly_price(prices, machine_type):
    """The type's lowest euros an hour over the zones the bill names, None when it names none."""
    found = [price for (other, _), price in prices.items() if other == machine_type]
    return min(found) if found else None


def rentals(row):
    """Every machine the row paid for, those that worked and the failed starts that existed, as dicts with a type."""
    return [entry for key in ("machines", "attempts") for entry in row.get(key) or []
            if isinstance(entry, dict) and entry.get("type") and (entry.get("minutes") or entry.get("euros"))]


def engine_type(row, prices):
    """The machine type of an engine run, whose row names none: the type whose price gives its euros by the minute."""
    minutes = math.ceil(row["machine_minutes"])
    for machine_type in sorted({machine_type for machine_type, _ in prices}):
        hourly = hourly_price(prices, machine_type)
        if abs(minutes * hourly / 60 - row["euros"]) < 0.0005:
            return machine_type
    return None


def typed_euros(row, prices):
    """The row's euros by machine type: its rentals, an engine run by its price, anything left as None."""
    euros = collections.defaultdict(float)
    for entry in rentals(row):
        euros[entry["type"]] += entry.get("euros", 0)
    rest = row["euros"] - sum(euros.values())
    if rest > 0.005:
        euros[engine_type(row, prices) if not rentals(row) else None] += rest
    return euros


def per_group(rows, tags, not_in_ledger):
    """Per kind of batch: batches, machine hours, ledger euros, share, with the bill's rest, median wall, main cards."""
    groups = collections.defaultdict(lambda: {"rows": 0, "minutes": 0.0, "euros": 0.0, "walls": [],
                                              "cards": collections.Counter()})
    for row in rows:
        group = groups[group_of(kind_of(row, tags))]
        group["rows"] += 1
        group["minutes"] += row.get("machine_minutes") or 0
        group["euros"] += row["euros"]
        if row.get("wall_minutes") is not None and row["euros"] > 0:
            group["walls"].append(row["wall_minutes"])
        for entry in rentals(row):
            group["cards"][entry["type"]] += entry.get("euros", 0)
    ledger = sum(group["euros"] for group in groups.values())
    rest = sum(not_in_ledger.values())
    table = []
    for name, group in sorted(groups.items(), key=lambda item: -item[1]["euros"]):
        share = group["euros"] / ledger
        cards = ", ".join(f"{card} {euros / group['euros']:.0%}" for card, euros in group["cards"].most_common(2))
        table.append({"group": name, "batches": group["rows"], "hours": group["minutes"] / 60,
                      "euros": group["euros"], "share": share, "with_rest": group["euros"] + rest * share,
                      "median_wall": statistics.median(group["walls"]) if group["walls"] else None,
                      "cards": cards or "not recorded"})
    return table


def per_type(rows, prices):
    """Per machine type: rentals, machine hours and euros, the engine runs typed by their price."""
    types = collections.defaultdict(lambda: {"rentals": 0, "minutes": 0.0, "euros": 0.0})
    for row in rows:
        for entry in rentals(row):
            types[entry["type"]]["rentals"] += 1
            types[entry["type"]]["minutes"] += entry.get("minutes", 0)
        if not rentals(row) and row["euros"] > 0.005:
            machine_type = engine_type(row, prices)
            types[machine_type]["rentals"] += 1
            types[machine_type]["minutes"] += row.get("machine_minutes") or 0
        for machine_type, euros in typed_euros(row, prices).items():
            types[machine_type]["euros"] += euros
    return dict(sorted(types.items(), key=lambda item: -item[1]["euros"]))


def per_product(rows, bill, prices):
    """Per machine type: the bill's euros against the ledger's, and the ledger's rentals priced again at the
    provider's billing unit (a started hour for the processor types). An engine run's row names no machine, so several
    rows may share one and it is not priced again."""
    products = collections.defaultdict(lambda: {"bill": 0.0, "ledger": 0.0, "at_billing_unit": 0.0})
    for line in bill:
        if line["category_name"] == "Compute":
            products[line["sku"].split("/")[3].upper().replace("_", "-")]["bill"] += line["euros"]
    for row in rows:
        for entry in rentals(row):
            product = products[entry["type"]]
            product["ledger"] += entry.get("euros", 0)
            hourly = hourly_price(prices, entry["type"])
            if hourly and entry["type"].startswith(HOURLY_PREFIXES):
                product["at_billing_unit"] += math.ceil(entry.get("minutes", 0) / 60) * hourly
            else:
                product["at_billing_unit"] += entry.get("euros", 0)
        if not rentals(row) and row["euros"] > 0.005:
            product = products[engine_type(row, prices)]
            product["ledger"] += row["euros"]
            product["at_billing_unit"] += row["euros"]
    return dict(sorted(products.items(), key=lambda item: -item[1]["bill"]))


def split_rnd(rows, tags):
    """The ledger's euros for R&D and for production."""
    split = {"R&D": 0.0, "production": 0.0}
    for row in rows:
        split["R&D" if is_rnd(row, tags) else "production"] += row["euros"]
    return split


def euro(value):
    """A euro figure as the paper writes it, a minus sign before the euro sign."""
    return f"{'−' if round(value, 2) < 0 else ''}€{abs(value):,.2f}"


def group_table(table):
    """Markdown for per_group."""
    lines = ["| Kind of batch | Batches | Machine time | Ledger | Share | With the rest of the bill | Median batch "
             "| Main card types |", "|---|---|---|---|---|---|---|---|"]
    for group in table:
        wall = f"{group['median_wall']:.0f} min" if group["median_wall"] is not None else ""
        lines.append(f"| {group['group']} | {group['batches']:,} | {group['hours']:.1f} h | {euro(group['euros'])} | "
                     f"{group['share']:.1%} | {euro(group['with_rest'])} | {wall} | {group['cards']} |")
    return lines


def type_table(types, prices):
    """Markdown for per_type, with the bill's price an hour beside the ledger's."""
    lines = ["| Machine type | Rentals | Machine time | Ledger | Per hour used | Billed an hour |",
             "|---|---|---|---|---|---|"]
    for machine_type, numbers in types.items():
        hours = numbers["minutes"] / 60
        used = euro(numbers["euros"] / hours) if hours else ""
        listed = hourly_price(prices, machine_type)
        lines.append(f"| {machine_type or 'not recorded'} | {numbers['rentals']:,} | {hours:.1f} h | "
                     f"{euro(numbers['euros'])} | {used} | {euro(listed) if listed else ''} |")
    return lines


def product_table(products):
    """Markdown for per_product, with the gap that is left once the ledger is priced at the billing unit."""
    lines = ["| Machine type | Bill | Ledger | Ledger at the billing unit | Bill less that |", "|---|---|---|---|---|"]
    for machine_type, numbers in products.items():
        lines.append(f"| {machine_type} | {euro(numbers['bill'])} | {euro(numbers['ledger'])} | {euro(numbers['at_billing_unit'])} | "
                     f"{euro(numbers['bill'] - numbers['at_billing_unit'])} |")
    total = {key: sum(numbers[key] for numbers in products.values()) for key in ("bill", "ledger", "at_billing_unit")}
    lines.append(f"| all | {euro(total['bill'])} | {euro(total['ledger'])} | {euro(total['at_billing_unit'])} | "
                 f"{euro(total['bill'] - total['at_billing_unit'])} |")
    return lines


def tables(rows, reconciliation, bill):
    """The month's tables as text: per kind of batch, per machine type, R&D and production, per product."""
    read = reconciliation["made"]
    month = month_rows(rows, read[:7], read)
    tags = reconciliation["kinds"]
    prices = unit_prices(bill)
    rest = reconciliation["not_in_ledger"]
    split = split_rnd(month, tags)
    text = [f"Ledger {read[:7]} up to the bill read {read}: {len(month):,} rows, {euro(sum(r['euros'] for r in month))};"
            f" bill {euro(reconciliation['bill']['total'])}; not in the ledger {euro(sum(rest.values()))}.", ""]
    text += group_table(per_group(month, tags, rest)) + [""]
    text += type_table(per_type(month, prices), prices) + [""]
    text += ["| Ledger part | Cost |", "|---|---|"]
    text += [f"| {name} | {euro(euros)} |" for name, euros in split.items()] + [""]
    text += product_table(per_product(month, bill, prices)) + [""]
    text += ["| Not in the ledger | Cost |", "|---|---|"] + [f"| {name} | {euro(euros)} |" for name, euros in rest.items()]
    return "\n".join(text) + "\n"


def types_before(rows, before):
    """Euros by machine type over the rows started before `before`, rows without machines as 'not recorded' and the
    euros a row holds beyond its machines as 'not split'."""
    euros = collections.defaultdict(float)
    for row in rows:
        if row["started"] >= before:
            continue
        machines = [entry for entry in row.get("machines") or [] if isinstance(entry, dict)]
        for entry in machines:
            euros[entry.get("type")] += entry.get("euros", 0)
        euros["not recorded" if not machines else "not split"] += row["euros"] - sum(
            entry.get("euros", 0) for entry in machines)
    return dict(euros)


def main():
    """Run one command; print one line."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    scrub_command = commands.add_parser("scrub")
    scrub_command.add_argument("ledger")
    scrub_command.add_argument("rows", type=int)
    scrub_command.add_argument("out")
    reconcile_command = commands.add_parser("reconcile")
    reconcile_command.add_argument("ledger")
    reconcile_command.add_argument("bill")
    reconcile_command.add_argument("read")
    reconcile_command.add_argument("out")
    tables_command = commands.add_parser("tables")
    tables_command.add_argument("ledger")
    tables_command.add_argument("reconciliation")
    tables_command.add_argument("bill")
    tables_command.add_argument("out")
    types_command = commands.add_parser("types")
    types_command.add_argument("ledger")
    types_command.add_argument("rows", type=int)
    types_command.add_argument("before")
    args = parser.parse_args()
    if args.command == "scrub":
        rows = [scrub(row) for row in read_rows(args.ledger, args.rows)]
        pathlib.Path(args.out).write_text("".join(json.dumps(row) + "\n" for row in rows))
        print(f"wrote {args.out}: {len(rows)} rows")
    elif args.command == "reconcile":
        report = reconcile(read_rows(args.ledger), json.loads(pathlib.Path(args.bill).read_text()), args.read)
        pathlib.Path(args.out).write_text(json.dumps(report, indent=1) + "\n")
        print(f"wrote {args.out}: bill {report['bill']['total']}, ledger {report['ledger_month']}, "
              f"not in the ledger {round(sum(report['not_in_ledger'].values()), 2)}")
    elif args.command == "tables":
        text = tables(read_rows(args.ledger), json.loads(pathlib.Path(args.reconciliation).read_text()),
                      json.loads(pathlib.Path(args.bill).read_text()))
        pathlib.Path(args.out).write_text(text)
        print(f"wrote {args.out}: {text.splitlines()[0]}")
    else:
        euros = types_before(read_rows(args.ledger, args.rows), args.before)
        print(json.dumps({str(key): round(value, 2) for key, value in sorted(euros.items(), key=lambda i: -i[1])}
                         | {"total": round(sum(euros.values()), 2)}))


if __name__ == "__main__":
    main()
