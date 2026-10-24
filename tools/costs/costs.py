"""The cloud's cost and time from the ledger and the provider's bill, as the paper's cost tables give them.

    python3 tools/costs/costs.py scrub <ledger.jsonl> <rows> <out.jsonl>      # the ledger's first rows, no local paths
    python3 tools/costs/costs.py reconcile <ledger.jsonl> <bill.json> <read> <out.json>
    python3 tools/costs/costs.py tables <ledger.jsonl> <reconciliation.json> <bill.json> <out.txt>
    python3 tools/costs/costs.py types <ledger.jsonl> <rows> <before>         # cost by machine type, an earlier window
    python3 tools/costs/costs.py today          # the provider's own bill: today (UTC) and month to date, by product
    python3 tools/costs/costs.py today --since 2026-10-12T18:25Z   # and spend since then split by track
    python3 tools/costs/costs.py reconcile-day <YYYY-MM-DD> [<day-bill.json>] [--skip google] [--ledger L] [--google-ledger G]

`today` reads the provider's consumption (Scaleway's month-to-date bill of the project, lagging by hours), keeps it as
a snapshot (`~/.farm-factory-props/cloud/bills/<read>.json`) and takes today as the month so far less the last
snapshot read before 00:00 UTC (or, on a box with none, the day's first snapshot, said so). For the 09:00, 15:00 and
21:00 reports; the ledger's own day is printed beside it. With `--since` it also splits the spend since then by track:
each cloud ledger row by the worktree that wrote it (ledger.origin, rows since 2026-10-12 ~20:40), an older row by its
`who` or batch name; each Google call by its tag, else its caller; and the bill's growth since the last snapshot read
at or before that time, less what the ledgers hold, as "not in the ledgers" (disks, addresses, storage, batches still
running).

Every runner writes one ledger row per batch (paper/evidence/cloud/ledger.jsonl is a scrubbed copy); the rows are never
rewritten. `reconcile` tags the rows written before a runner named its kind and sets the month's bill (one
bill-<read>.json, the provider's consumption lines) against the ledger. `tables` writes the paper's tables for that
month: cost and time per kind of batch and per card type, R&D against production, and the bill's compute per product
against the ledger's. Each command prints one line; the tables go to the file.

`reconcile-day` is the alarm for spend outside the ledgers (2026-10-17: a Google day billed about EUR 520 the ledger
never held, and 21% of Scaleway's bill was in no ledger row). It sets one day's bill, per provider, against what the
ledgers hold for it, line by line, and exits 1 when a line the ledgers hold is further from its bill than
DAY_TOLERANCE of the provider's ledgered bill, naming the provider. Scaleway's day is built from the snapshots `today`
saves (the last read of the day less the last read before it, so `today` must have run on both days), its ledger rows
taken over the same window, each run's euros spread over its hours and a machine still running (an open
`rent-started` line) at its price; a day bill file {"scaleway": [{"sku", "euros"}], "google": [{"sku", "euros"}]}
overrides that with the calendar day (UTC). Google's day comes only from that file (no Google bill reader yet), set
against its ledger's lines of that Amsterdam day. A provider with no bill fails unless `--skip` leaves it out,
and so does one whose ledger file is missing (never read as an empty ledger).
Machines are compared with the run rows and the disks and addresses with the rows the backend writes at delete;
storage and the rest (registry, secrets, clusters) have no ledger rows and are reported apart, never in the gap. The
bill lags by hours, so check a day once the next day's reads are in.
"""
import argparse
import collections
import datetime
import json
import math
import pathlib
import re
import statistics
import sys
import time

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
# The provider bills these types by the started hour and the cards by the minute (tools/cloud/backends/
# scaleway.py, price()).
HOURLY_PREFIXES = ("POP2-", "RENDER-")
CLOUD_TOOLS = pathlib.Path(__file__).resolve().parents[1] / "props"
# How far a provider's day in the ledgers may sit from its bill, as a share of the bill, before reconcile-day fails.
DAY_TOLERANCE = 0.05
# reconcile-day's lines of a Scaleway bill, by the start of their sku; the rest are "other" (clusters, secrets).
BILL_LINES = (("/instance/server/", "machines"), ("/storage/block", "disks and addresses"),
              ("/instance/volume", "disks and addresses"), ("/network/ipam", "disks and addresses"),
              ("/storage/obj", "storage"), ("/offer/deducted/storage", "storage"), ("/tools/registry", "storage"))
# The lines of each provider's bill that the ledgers hold; the others are reported apart and never in the gap.
LEDGERED = {"scaleway": ("machines", "disks and addresses"), "google": ("calls",)}
# Which products of the bill `today` names apart, by the start of their sku; the rest are "other".
PRODUCTS = (("/instance/server/l40s", "L40S"), ("/instance/server/l4", "L4"), ("/instance/server/h100", "H100"),
            ("/instance/server/pop2", "POP2"), ("/instance/server/", "machines"), ("/storage/block", "disks"),
            ("/instance/volume", "disks"), ("/network/ipam", "addresses"))


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


def run_rows(rows):
    """The rows that are batches: the order lines (ledger.ORDER_LINES: a machine or a pool about to be ordered, an
    order refused) hold no euros and no machine time, so the paper's commands leave them out."""
    order_lines = cloud_ledger().ORDER_LINES
    return [row for row in rows if row.get("kind") not in order_lines]


def month_rows(rows, month, before):
    """The batch rows (run_rows) that started in `month` (YYYY-MM) before the time `before`."""
    return [row for row in run_rows(rows) if row["started"].startswith(month) and row["started"] < before]


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
    rows = run_rows(rows)
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


def per_group(rows, tags, not_in_ledger, prices):
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
        group["cards"].update(typed_euros(row, prices))
    ledger = sum(group["euros"] for group in groups.values())
    rest = sum(not_in_ledger.values())
    table = []
    for name, group in sorted(groups.items(), key=lambda item: -item[1]["euros"]):
        share = group["euros"] / ledger
        cards = ", ".join(f"{card or 'not recorded'} {euros / group['euros']:.0%}"
                          for card, euros in group["cards"].most_common(2))
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
    text += group_table(per_group(month, tags, rest, prices)) + [""]
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
    for row in run_rows(rows):
        if row["started"] >= before:
            continue
        machines = [entry for entry in row.get("machines") or [] if isinstance(entry, dict)]
        for entry in machines:
            euros[entry.get("type")] += entry.get("euros", 0)
        euros["not recorded" if not machines else "not split"] += row["euros"] - sum(
            entry.get("euros", 0) for entry in machines)
    return dict(euros)


def product_of(sku):
    """The name `today` gives a bill line's product."""
    return next((name for start, name in PRODUCTS if sku.startswith(start)), "other")


def by_product(lines):
    """A bill's euros per product name (product_of)."""
    euros = collections.Counter()
    for line in lines:
        euros[product_of(line["sku"] or "")] += line["euros"]
    return euros


def read_bill():
    """The provider's month-to-date bill of the project, its lines (provider.cloud.consumption)."""
    for folder in (CLOUD_TOOLS, CLOUD_TOOLS.parent / "cloud"):
        if str(folder) not in sys.path:
            sys.path.append(str(folder))
    import provider

    return provider.cloud.consumption(provider.cloud.account())


def bills_folder():
    """Where `today` keeps its snapshots of the bill."""
    from paths import HOME as props_home  # on the path read_bill set

    return props_home / "cloud" / "bills"


def save_snapshot(folder, lines, now):
    """Keep one read of the bill, named for its time; its path."""
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{now.strftime('%Y-%m-%dT%H%MZ')}.json"
    path.write_text(json.dumps({"read": now.isoformat(), "lines": lines}))
    return path


def day_baseline(folder, now):
    """The bill as it stood when today began: (the lines of the last read before 00:00 UTC this month, None),
    ([], None) on the month's first day, else (the day's first read's lines, its HHMM) as the next best, else
    (None, None)."""
    if now.day == 1:
        return [], None
    day = now.strftime("%Y-%m-%d")
    reads = sorted(folder.glob(f"{now.strftime('%Y-%m')}-*.json"))
    before = [path for path in reads if path.stem[:10] < day]
    if before:
        return json.loads(before[-1].read_text())["lines"], None
    first = [path for path in reads if path.stem[:10] == day]
    if first:
        return json.loads(first[0].read_text())["lines"], first[0].stem[11:15]
    return None, None


def moment(text):
    """A time written as ISO 8601 (Z, an offset, or none for UTC), as epoch seconds."""
    when = datetime.datetime.fromisoformat(text.replace("Z", "+00:00"))
    return (when if when.tzinfo else when.replace(tzinfo=datetime.timezone.utc)).timestamp()


def cloud_track(row):
    """The track a cloud ledger row is charged to: its worktree, else (rows from before ledger.origin) its `who` or
    its batch name's first word."""
    if row.get("worktree"):
        return row["worktree"]
    return f"who: {row.get('who') or row.get('batch', '?').split('-')[0]}"


def cloud_since(rows, since):
    """Cloud ledger euros per track for rows started at or after `since` (epoch seconds)."""
    euros = collections.Counter()
    for row in rows:
        if row.get("started") and moment(row["started"]) >= since:
            euros[cloud_track(row)] += row.get("euros", 0)
    return euros


def google_since(lines, since, price_of):
    """Google ledger euros per tag (else caller) for calls at or after `since` (google_tracks)."""
    return google_tracks([line for line in lines if moment(line["time"]) >= since], price_of)


def google_tracks(lines, price_of):
    """Google ledger euros per tag (else caller) of `lines`: finished calls at their price, one started and never
    finished at its estimate (as google_spend.month_euros counts them). `price_of(model)` is the estimate for an
    unpriced finished call."""
    finished = {line.get("call") for line in lines if line.get("state", "finished") == "finished"}
    euros = collections.Counter()
    for line in lines:
        track = f"google: {line.get('tag') or line.get('caller') or '?'}"
        if line.get("state", "finished") == "finished":
            euros[track] += price_of(line["model"]) if line.get("euros") is None else line["euros"]
        elif line.get("state") == "started" and line.get("call") not in finished:
            euros[track] += line.get("estimate") or 0.0
    return euros


def bill_at(folder, since):
    """The lines of the last snapshot read at or before `since`, and its read time; (None, None) without one."""
    reads = [path for path in sorted(folder.glob("*.json"))
             if moment(json.loads(path.read_text())["read"]) <= since]
    if not reads:
        return None, None
    record = json.loads(reads[-1].read_text())
    return record["lines"], record["read"]


def since_text(lines, folder, since, tracks):
    """The split since `since`: the bill's growth from the snapshot before it, each track's euros, and the rest."""
    start, read = bill_at(folder, since)
    total = sum(tracks.values())
    parts = ", ".join(f"{name} {euros:.2f}" for name, euros in tracks.most_common() if round(euros, 2))
    text = f"since {datetime.datetime.fromtimestamp(since, datetime.timezone.utc):%Y-%m-%d %H:%MZ}: ledgers EUR " \
           f"{total:.2f} ({parts or 'nothing'})"
    if start is None:
        return text + "; the bill's growth: no snapshot read before then"
    grown = sum(line["euros"] for line in lines) - sum(line["euros"] for line in start)
    cloud = sum(euros for name, euros in tracks.items() if not name.startswith("google: "))
    return (text + f"; Scaleway's bill grew EUR {grown:.2f} since its read at {read[:16]}, "
            f"EUR {grown - cloud:.2f} of it not in the ledgers (lags by hours)")


def ledger_day(ledger_path, day):
    """What the cloud ledger holds for batches started on `day` (YYYY-MM-DD)."""
    if not pathlib.Path(ledger_path).exists():
        return 0.0
    return sum(row.get("euros", 0) for row in read_rows(ledger_path) if row.get("started", "").startswith(day))


def products_text(euros):
    """Products and euros, largest first, as one phrase."""
    return ", ".join(f"{name} {value:.2f}" for name, value in euros.most_common() if round(value, 2))


def today_line(lines, baseline, since, ledger_euros, saved):
    """The `today` report in one line."""
    month = by_product(lines)
    text = f"Scaleway, month to date EUR {sum(month.values()):.2f} ({products_text(month)})"
    if baseline is None:
        text += "; today: no earlier read yet, the next `today` gives it"
    else:
        day = by_product(lines)
        day.subtract(by_product(baseline))
        start = f"since {since[:2]}:{since[2:]} UTC" if since else "since 00:00 UTC"
        text += f"; today {start} EUR {sum(day.values()):.2f} ({products_text(day)})"
    return text + f"; the cloud ledger's today EUR {ledger_euros:.2f}; the bill lags by hours; saved {saved}"


def today(since=None):
    """Read the bill, keep it, and print today and the month to date; with `since` (ISO time) also the split by track
    since then."""
    now = datetime.datetime.now(datetime.timezone.utc)
    lines = read_bill()
    folder = bills_folder()
    baseline, started = day_baseline(folder, now)
    saved = save_snapshot(folder, lines, now)
    import google_spend  # on the path read_bill set
    import ledger

    print(today_line(lines, baseline, started, ledger_day(ledger.LEDGER, now.strftime("%Y-%m-%d")), saved))
    if since:
        moment_since = moment(since)
        google_lines = [json.loads(line) for line in google_spend.LEDGER.read_text().splitlines() if line.strip()] \
            if google_spend.LEDGER.exists() else []
        tracks = cloud_since(ledger.entries(), moment_since) + \
            google_since(google_lines, moment_since, google_spend.estimate)
        print(since_text(lines, folder, moment_since, tracks))


class NoBill(Exception):
    """A provider's day bill cannot be had; its message says why."""


def bill_line_of(sku):
    """The reconcile-day line a Scaleway bill line's sku falls in."""
    return next((name for start, name in BILL_LINES if sku.startswith(start)), "other")


def scaleway_bill_lines(lines):
    """A Scaleway day bill's euros per reconcile-day line."""
    euros = collections.Counter()
    for line in lines:
        euros[bill_line_of(line.get("sku") or "")] += line["euros"]
    return euros


def google_bill_lines(lines):
    """A Google day bill's euros, as one line of calls."""
    return collections.Counter({"calls": sum(line["euros"] for line in lines)})


def saved_reads(folder, month):
    """The snapshots `today` saved in `folder` for `month` (YYYY-MM): (their read time, their lines), oldest first."""
    reads = [json.loads(path.read_text()) for path in sorted(pathlib.Path(folder).glob(f"{month}-*.json"))]
    return sorted((moment(read["read"]), read["lines"]) for read in reads)


def lines_grown(start_lines, end_lines):
    """The bill lines of what grew from one read to a later one, per sku."""
    euros = collections.Counter()
    for line in end_lines:
        euros[line.get("sku") or ""] += line["euros"]
    for line in start_lines:
        euros[line.get("sku") or ""] -= line["euros"]
    return [{"sku": sku, "euros": value} for sku, value in euros.items()]


def snapshot_day_bill(folder, day):
    """Scaleway's bill of `day` (YYYY-MM-DD, UTC) from the saved reads: (its lines, the window's start and end, epoch
    seconds): the last read of the day less the last read before it (none on the month's first day). NoBill without
    those reads."""
    day_start = moment(day)
    reads = saved_reads(folder, day[:7])
    before = [read for read in reads if read[0] < day_start]
    during = [read for read in reads if day_start <= read[0] < day_start + 86400]
    if not during:
        raise NoBill(f"no read of the bill saved on {day} (`costs.py today` saves one)")
    if before:
        start, start_lines = before[-1]
    elif day.endswith("-01"):
        start, start_lines = day_start, []
    else:
        raise NoBill(f"no read of the bill saved before {day} began, so its day cannot be told from the month")
    end, end_lines = during[-1]
    return lines_grown(start_lines, end_lines), start, end


def overlap_share(began, ended, start, end):
    """The share of the span [began, ended] inside [start, end); a span of no length is wholly in or out."""
    if ended <= began:
        return 1.0 if start <= began < end else 0.0
    return max(0.0, min(ended, end) - max(began, start)) / (ended - began)


def row_span(row):
    """A run row's hours as (began, ended), epoch seconds: from its start for its wall minutes (else its longest
    machine's)."""
    began = moment(row["started"])
    minutes = row.get("wall_minutes") or max((machine.get("minutes", 0) for machine in row.get("machines") or []),
                                             default=0)
    return began, began + minutes * 60


def cloud_ledger():
    """The cloud ledger module (tools/cloud/ledger.py), its folders put on the path."""
    for folder in (CLOUD_TOOLS, CLOUD_TOOLS.parent / "cloud"):
        if str(folder) not in sys.path:
            sys.path.append(str(folder))
    import ledger

    return ledger


def cloud_window_lines(rows, start, end, now):
    """The cloud ledger's euros inside [start, end): each run row's euros by the share of its hours inside, a
    disk-and-address row (written at delete) at its time, and a machine still open (ledger.open_rents) at its price
    over its hours inside, up to `now`."""
    ledger = cloud_ledger()
    euros = collections.Counter()
    for row in rows:
        if row.get("kind") in ledger.ORDER_LINES or not row.get("started"):
            continue
        line = "disks and addresses" if row.get("kind") == "disk-and-address" else "machines"
        euros[line] += row.get("euros", 0) * overlap_share(*row_span(row), start, end)
    for line in ledger.open_rents(rows, min(now, end)):
        euros["machines"] += ledger.open_euros(line, min(now, end)) - ledger.open_euros(line, start)
    return euros


def google_day_lines(lines, day, price_of):
    """The Google ledger's euros for calls of `day` (YYYY-MM-DD, Amsterdam), as one line."""
    tracks = google_tracks([line for line in lines if line.get("day") == day], price_of)
    return collections.Counter({"calls": sum(tracks.values())})


def provider_report(provider_name, bill, ledger_lines):
    """One provider's day: its bill and ledger lines, the gap of each line the ledgers hold (as a share of the
    provider's ledgered bill) and the bill's lines no ledger holds."""
    ledgered = LEDGERED[provider_name]
    ledgered_bill = sum(bill[name] for name in ledgered)
    gaps = {name: gap_share(bill[name], ledger_lines[name], ledgered_bill) for name in ledgered}
    unledgered = collections.Counter({name: euros for name, euros in bill.items() if name not in ledgered})
    return {"provider": provider_name, "bill": bill, "ledger": ledger_lines, "gaps": gaps, "unledgered": unledgered}


def gap_share(bill_euros, ledger_euros, scale):
    """How far a line's ledgers sit from its bill, as a share of `scale` (any gap against a scale of none: 1)."""
    if scale == 0:
        return 0.0 if round(abs(bill_euros - ledger_euros), 2) == 0 else 1.0
    return abs(bill_euros - ledger_euros) / scale


def day_report_line(report):
    """One provider's reconcile-day result as one line, its provider named first."""
    if "missing" in report:
        return f"{report['provider']}: no bill ({report['missing']}); --skip {report['provider']} leaves it out"
    if "no_ledger" in report:
        option = "--ledger" if report["provider"] == "scaleway" else "--google-ledger"
        return f"{report['provider']}: {report['no_ledger']}; {option} names another"
    over = any(share > DAY_TOLERANCE for share in report["gaps"].values())
    compared = "; ".join(f"{name}: bill {report['bill'][name]:.2f}, ledgers {report['ledger'][name]:.2f}, "
                         f"{share:.1%} apart" for name, share in report["gaps"].items())
    verdict = f"over the {DAY_TOLERANCE:.0%} allowed" if over else "within"
    apart = products_text(report["unledgered"])
    return (f"{report['provider']}: {compared}; {verdict}"
            + (f"; not in any ledger: {apart}" if apart else ""))


def failed(report):
    """True when a provider's day has no bill or no ledger, or a ledgered line is over DAY_TOLERANCE."""
    return "missing" in report or "no_ledger" in report or any(share > DAY_TOLERANCE for share in report["gaps"].values())


class NoLedger(Exception):
    """A provider's ledger file does not exist; its message names the path."""


def ledger_lines_of(path):
    """A jsonl ledger's lines; NoLedger when the file does not exist (a missing ledger is not an empty one)."""
    path = pathlib.Path(path)
    if not path.exists():
        raise NoLedger(f"no ledger at {path}")
    return read_rows(path)


def scaleway_day(day_bill, day, bills, cloud_rows, now):
    """Scaleway's report of `day`: from the day bill file when it has Scaleway (the calendar day, UTC), else from
    the saved reads in `bills`; NoBill when neither has it."""
    if "scaleway" in day_bill:
        lines, start, end = day_bill["scaleway"], moment(day), moment(day) + 86400
    else:
        lines, start, end = snapshot_day_bill(bills, day)
    return provider_report("scaleway", scaleway_bill_lines(lines), cloud_window_lines(cloud_rows, start, end, now))


def google_day(day_bill, day, google_lines, price_of):
    """Google's report of `day`: from the day bill file only; NoBill without it."""
    if "google" not in day_bill:
        raise NoBill("no Google bill reader yet; give its day in the bill file")
    return provider_report("google", google_bill_lines(day_bill["google"]), google_day_lines(google_lines, day, price_of))


def day_check(day, bill_path, skip, paths):
    """Print reconcile-day's line per provider not in `skip`; the exit code: 1 when a provider has no bill or no ledger
    file, or is over DAY_TOLERANCE. `paths`: the cloud ledger, the Google ledger and the bills folder, each None for its default."""
    ledger = cloud_ledger()
    import google_spend  # on the path cloud_ledger set

    ledger_path, google_path, bills = paths
    day_bill = json.loads(pathlib.Path(bill_path).read_text()) if bill_path else {}
    reports = []
    for provider_name, report_of in (
            ("scaleway", lambda: scaleway_day(day_bill, day, bills or bills_folder(),
                                              ledger_lines_of(ledger_path or ledger.LEDGER), time.time())),
            ("google", lambda: google_day(day_bill, day, ledger_lines_of(google_path or google_spend.LEDGER),
                                          google_spend.estimate))):
        if provider_name in skip:
            continue
        try:
            reports.append(report_of())
        except NoBill as missing:
            reports.append({"provider": provider_name, "missing": str(missing)})
        except NoLedger as no_ledger:
            reports.append({"provider": provider_name, "no_ledger": str(no_ledger)})
    for report in reports:
        print(day_report_line(report))
    return 1 if any(failed(report) for report in reports) else 0


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
    today_command = commands.add_parser("today")
    today_command.add_argument("--since", help="also split the spend since this time (ISO 8601, UTC) by track")
    day_command = commands.add_parser("reconcile-day")
    day_command.add_argument("day")
    day_command.add_argument("bill", nargs="?", help="the day's bill per provider; Scaleway's defaults to the reads")
    day_command.add_argument("--skip", action="append", default=[], choices=sorted(LEDGERED),
                             help="leave a provider out on purpose (else one with no bill fails)")
    day_command.add_argument("--ledger", help="the cloud ledger, by default the runner's")
    day_command.add_argument("--google-ledger", help="the Google ledger, by default google_spend's")
    day_command.add_argument("--bills", help="the saved reads of the bill, by default today's folder")
    args = parser.parse_args()
    if args.command == "reconcile-day":
        sys.exit(day_check(args.day, args.bill, set(args.skip), (args.ledger, args.google_ledger, args.bills)))
    if args.command == "today":
        today(args.since)
        return
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
