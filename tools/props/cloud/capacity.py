"""Which machine types each kind of cloud job may run on, the order a fleet takes them in, and what each run cost
and took per card type.

    python3 tools/props/cloud/capacity.py report [--since 2026-10-08]   # time and cost per job kind per card type
    python3 tools/props/cloud/capacity.py offers <kind>                 # where that kind can be rented right now

All day on 2026-10-08 the batches waited because the L4 cards in pl-waw-2 were out of stock and machines failed to
start. The owner's rule the same day: Scaleway's credits cover about EUR 3,000 a month and a world costs tens of
euros, so the card's price barely matters; take whatever is in stock, in the order that waits least, and never wait
minutes for an L4 when a bigger card is free. So every kind lists every Scaleway type whose card holds it, and
`batch.claim` walks them best stocked first, then in SPEED_ORDER, across the three zones that rent cards: a zone that
refuses the order, says "out of stock" for a minute, or gives a machine that does not answer within
`batch.START_MINUTES` is left for the next offer. A fleet spreads over the zones (`next_offer`), so one zone running
dry costs it one machine. The month's spend stays under `ledger.MONTH_EUROS`, checked before every rent.

Memory per kind decides which cards may run it. Pixal3D was measured: three runs at once peak at 10.6 GB on one card
(2026-09-29), so every card of 24 GB or more holds it. Every other kind was set up and measured on an L4 (24 GB) and
has not been measured below that, so it may run on any single card of at least 24 GB: the L40S (48 GB) and the H100
(80 GB) hold all of it. Machines with two cards only pay off where the runner spreads work over cards, which only
the Pixal3D fleet does. RENDER-S (a 16 GB Tesla P100) is not used: the GPU image's NVIDIA driver does not see its
card (2026-10-08, `nvidia-smi` failed on both machines rented).

A big card runs several jobs of a kind at once where its memory allows (`runs_at_once`): Pixal3D runs three at once
on an L4's 24 GB (measured 2026-09-29), so a card runs three for every 24 GB it has.
"""
import argparse
import collections
import pathlib
import statistics
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import ledger  # noqa: E402

# Each machine type's cards and the memory of one card in GB (Scaleway's server-type list, 2026-10-08).
CARDS = {"L4-1-24G": (1, 24), "L4-2-24G": (2, 24), "L40S-1-48G": (1, 48), "H100-1-80G": (1, 80),
         "H100-2-80G": (2, 80), "H100-SXM-2-80G": (2, 80)}
# The order offers are tried in among those as well stocked: the one that waits least first (owner, 2026-10-08).
SPEED_ORDER = ("L4-1-24G", "L40S-1-48G", "H100-1-80G", "H100-SXM-2-80G", "H100-2-80G", "L4-2-24G")
# Jobs of a kind one card runs at once for each 24 GB it has, where that was measured: Pixal3D, three on an L4.
RUNS_PER_24GB = {"pixal": 3}
SINGLE_CARD = ("L4-1-24G", "L40S-1-48G", "H100-1-80G")
# The types each kind may run on. Order does not matter: offers are sorted by price per card.
KINDS = {
    "pixal": ("L4-1-24G", "L4-2-24G", "L40S-1-48G", "H100-1-80G", "H100-2-80G", "H100-SXM-2-80G"),
    "library": SINGLE_CARD,
    "parts": SINGLE_CARD,
    "scene": SINGLE_CARD,
    "closeups": SINGLE_CARD,
    "unlit": SINGLE_CARD,
    "pictures": SINGLE_CARD,
    "moss-sound": ("L4-1-24G", "L40S-1-48G", "L4-2-24G", "H100-1-80G"),
}
# A ledger entry written before entries named their kind was a Pixal3D batch.
OLD_KIND = "pixal"


def cards(machine_type):
    """How many cards a machine type has; 0 for a processor machine."""
    return CARDS.get(machine_type, (0, 0))[0]


def types_for(kind):
    """The machine types a kind may run on."""
    if kind not in KINDS:
        raise SystemExit(f"no machine types are listed for the job kind '{kind}'; known: {', '.join(KINDS)}")
    return KINDS[kind]


def runs_at_once(kind, machine_type):
    """How many jobs of `kind` one card of `machine_type` runs at once: RUNS_PER_24GB for each 24 GB it has where
    that was measured, else one."""
    if kind not in RUNS_PER_24GB:
        return 1
    return max(1, RUNS_PER_24GB[kind] * CARDS[machine_type][1] // 24)


def speed_rank(machine_type):
    """Where a type stands in SPEED_ORDER; types not in it (processor machines) after every card."""
    return SPEED_ORDER.index(machine_type) if machine_type in SPEED_ORDER else len(SPEED_ORDER)


def next_offer(offers, rented):
    """The offer the next machine of a run is rented from: the best stocked first, then the type that waits least
    (SPEED_ORDER), then the zone holding fewest of the run's machines, then the cheapest. `offers` are
    batch.offers' tuples (euros a card a minute, stock rank, type, zone, euros a minute); `rented` the run's
    machines so far."""
    if not offers:
        return None
    in_zone = collections.Counter(machine["zone"] for machine in rented if not machine.get("deleted"))
    return min(offers, key=lambda offer: (offer[1], speed_rank(offer[2]), in_zone[offer[3]], offer[0]))


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
    import batch  # reads Scaleway's price list and stock, which the report does not need

    for offer in batch.offers(list(types_for(options.kind))):
        print(f"{offer[2]:>16} {offer[3]:>9}  stock rank {offer[1]}  €{offer[0] * 60:.2f} a card an hour")


if __name__ == "__main__":
    main()
