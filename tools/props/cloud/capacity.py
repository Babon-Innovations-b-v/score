"""Which capability classes each kind of cloud job may run on, the order a run takes offers in, and what each run
cost and took per card type.

    python3 tools/props/cloud/capacity.py report [--since 2026-10-08]   # time and cost per job kind per card type
    python3 tools/props/cloud/capacity.py offers <kind>                 # where that kind can be rented right now

All day on 2026-10-08 the batches waited because one zone's cheapest cards were out of stock and machines failed to
start. The owner's rule the same day: the cloud credits cover about EUR 3,000 a month and a world costs tens of
euros, so the card's price barely matters; take whatever is in stock, in the order that waits least, and never wait
minutes for the smallest card when a bigger one is free. So every kind lists every capability class that holds it
(provider.py), and `batch.claim` walks the backend's offers best stocked first, then in SPEED_ORDER, across every
zone the backend rents in: an offer that is refused, says "out of stock" for a minute, or gives a machine that does
not answer within `batch.START_MINUTES` is left for the next. A run spreads over the zones (`next_offer`), so one
zone running dry costs it one machine. The month's spend stays under `ledger.MONTH_EUROS`, checked before every rent.

Memory per kind decides which classes may run it. Pixal3D was measured: three runs at once peak at 10.6 GB on one
card (2026-09-29), so every card of 24 GB or more holds it. Every other kind was set up and measured on a 24 GB card
and has not been measured below that, so it may run on any single card of at least 24 GB. Machines with two cards
only pay off where the runner spreads work over cards, which only the Pixal3D fleet does.

A big card runs several jobs of a kind at once where its memory allows (`runs_at_once`): Pixal3D runs three at once
on 24 GB (measured 2026-09-29), so a card runs three for every 24 GB it has.
"""
import argparse
import collections
import pathlib
import statistics
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import ledger  # noqa: E402
import provider  # noqa: E402

# The order offers are tried in among those as well stocked: the class that waits least first (owner, 2026-10-08).
SPEED_ORDER = ("gpu-24gb", "gpu-48gb", "gpu-80gb", "gpu-80gb-x2", "gpu-24gb-x2")
# Jobs of a kind one card runs at once for each 24 GB it has, where that was measured: Pixal3D, three on 24 GB.
RUNS_PER_24GB = {"pixal": 3}
SINGLE_CARD = ("gpu-24gb", "gpu-48gb", "gpu-80gb")
# The classes each kind may run on. Order does not matter: offers are taken in the kind's order (order_for).
KINDS = {
    "pixal": ("gpu-24gb", "gpu-48gb", "gpu-80gb", "gpu-24gb-x2", "gpu-80gb-x2"),
    "library": ("gpu-24gb", "gpu-48gb", "gpu-24gb-x2", "gpu-80gb"),
    "parts": SINGLE_CARD,
    "scene": SINGLE_CARD,
    "closeups": SINGLE_CARD,
    "unlit": SINGLE_CARD,
    "pictures": SINGLE_CARD,
    "moss-sound": ("gpu-24gb", "gpu-48gb", "gpu-24gb-x2", "gpu-80gb"),
}
# Kinds that take their offers in an order of their own. Pixal3D: the 80 GB cards first, which run ten takes at once
# (18 takes an hour against an L4's 6, measured 2026-10-08). Library bakes (Cycles): the cards with ray-tracing
# cores first; an H100 has none and baked the same job 2.6 times slower than an L4 (138 s against 360 s).
KIND_ORDER = {
    "pixal": ("gpu-80gb", "gpu-80gb-x2", "gpu-48gb", "gpu-24gb", "gpu-24gb-x2"),
    "library": ("gpu-24gb", "gpu-48gb", "gpu-24gb-x2", "gpu-80gb"),
}
# Classes a kind takes only after LATE_MINUTES with nothing else to be had: the cards without ray-tracing cores, for
# the bakes.
LATE = {"library": ("gpu-80gb", "gpu-80gb-x2")}
LATE_MINUTES = 5
# A ledger entry written before entries named their kind was a Pixal3D batch.
OLD_KIND = "pixal"


def classes_for(kind):
    """The capability classes a kind may run on."""
    if kind not in KINDS:
        raise SystemExit(f"no capability classes are listed for the job kind '{kind}'; known: {', '.join(KINDS)}")
    return KINDS[kind]


def runs_at_once(kind, machine_class):
    """How many jobs of `kind` one card of `machine_class` runs at once: RUNS_PER_24GB for each 24 GB it has where
    that was measured, else one."""
    if kind not in RUNS_PER_24GB:
        return 1
    return max(1, RUNS_PER_24GB[kind] * provider.card_gb(machine_class) // 24)


def order_for(kind):
    """The order a kind takes capability classes in: its own (KIND_ORDER), else SPEED_ORDER."""
    return KIND_ORDER.get(kind, SPEED_ORDER)


def late_for(kind):
    """The classes a kind takes only after LATE_MINUTES with nothing else to be had."""
    return LATE.get(kind, ())


def speed_rank(machine_class, kind=None):
    """Where a class stands in the kind's order; classes not in it (processor machines) after every card."""
    order = order_for(kind)
    return order.index(machine_class) if machine_class in order else len(order)


def next_offer(offers, rented, kind=None):
    """The offer the next machine of a run is rented from: the best stocked first, then the kind's order of classes
    (order_for) and the backend's own order within a class, then the zone holding fewest of the run's machines, then
    the cheapest. `offers` are provider.Offer; `rented` the run's machines so far."""
    if not offers:
        return None
    in_zone = collections.Counter(machine["zone"] for machine in rented if not machine.get("deleted"))
    return min(offers, key=lambda offer: (offer.stock, speed_rank(offer.machine_class, kind), offer.order,
                                          in_zone[offer.zone], offer.per_card))


# The report.

def machine_rows(entries, since=""):
    """Every machine row in the ledger's entries started on or after `since`, with its entry's kind; failed starts
    are rows too, marked by `started: False`."""
    rows = []
    for entry in entries:
        if entry.get("started", "") < since:
            continue
        kind = entry.get("kind", OLD_KIND)
        for row in entry.get("machines", []) + entry.get("attempts", []):
            rows.append(dict(row, kind=kind))
    return rows


def median(values):
    """The median of the values that were recorded, or None."""
    known = [value for value in values if value is not None]
    return statistics.median(known) if known else None


def summarise(rows):
    """Time and cost per (job kind, card type): machines that ran, starts that failed, the median wait for a
    machine to answer, the median minutes a machine was rented and worked after it answered, the total euros
    (failed starts included), the units of work done, and the seconds and euros per unit where the runner counted
    units. Rows written before 2026-10-08 have no start wait, work minutes or units."""
    groups = collections.defaultdict(list)
    for row in rows:
        groups[(row["kind"], row["type"])].append(row)
    table = []
    for (kind, machine_type), group in sorted(groups.items()):
        ran = [row for row in group if row.get("started", True)]
        units = [seconds for row in ran for seconds in row.get("unit_seconds") or []]
        euros = sum(row.get("euros", 0.0) for row in group)
        counted = sum(row.get("euros", 0.0) for row in ran if row.get("unit_seconds"))
        table.append({"kind": kind, "type": machine_type, "machines": len(ran),
                      "failed_starts": len(group) - len(ran),
                      "start_wait_minutes": median(row.get("start_wait_minutes") for row in ran),
                      "minutes": median(row.get("minutes") for row in ran),
                      "work_minutes": median(row.get("work_minutes") for row in ran),
                      "euros": euros, "units": len(units), "seconds_a_unit": median(units),
                      "euros_a_unit": counted / len(units) if units else None})
    return table


def shown(value, digits):
    return "-" if value is None else f"{value:.{digits}f}"


def print_table(table):
    columns = ("type", "machines", "failed", "wait min", "min", "work min", "euros", "units", "s/unit", "€/unit")
    print(f"{'kind':<24}" + "".join(f"{name:>15}" if number == 0 else f"{name:>9}"
                                    for number, name in enumerate(columns)))
    for row in table:
        cells = (row["machines"], row["failed_starts"], shown(row["start_wait_minutes"], 1), shown(row["minutes"], 1),
                 shown(row["work_minutes"], 1), f"{row['euros']:.2f}", row["units"], shown(row["seconds_a_unit"], 0),
                 shown(row["euros_a_unit"], 3))
        print(f"{row['kind'][:23]:<24}{row['type']:>15}" + "".join(f"{cell:>9}" for cell in cells))


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    report = commands.add_parser("report", help="time and cost per job kind per card type, from the ledger")
    report.add_argument("--since", default="", help="only entries started on or after this date (YYYY-MM-DD)")
    offers = commands.add_parser("offers", help="where a job kind can be rented right now")
    offers.add_argument("kind")
    options = parser.parse_args()
    if options.command == "report":
        print_table(summarise(machine_rows(ledger.entries(), options.since)))
        return
    for offer in sorted(provider.cloud.offers(classes_for(options.kind)),
                        key=lambda offer: (offer.stock, speed_rank(offer.machine_class), offer.order, offer.zone)):
        print(f"{offer.machine_class:>12} {offer.type:>16} {offer.zone:>9}  {offer.stock_word:>9}  "
              f"€{offer.per_card * 60:.2f} a card an hour")


if __name__ == "__main__":
    main()
