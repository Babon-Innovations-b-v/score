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
and has not been measured below that, so it may run on any single card of at least 24 GB. A machine with two cards
runs a share on each card.

Every kind spreads a batch over many machines at once (`spread.py`, 2026-10-08, once the provider granted quotas
for 20 H100, 50 L4 and 10 L40S machines): `machines_for` sizes the fleet so each machine works about as long as its
setup takes (one machine for a small batch), and `next_offer` holds a run to its caps (`max_machines` a class,
`run_cap` in all; SCORE_MAX_MACHINES overrides the backend's quotas).

A big card runs several jobs of a kind at once where its memory allows (`runs_at_once`): Pixal3D runs three at once
on 24 GB (measured 2026-09-29), so a card runs three for every 24 GB it has.
"""
import argparse
import collections
import math
import os
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
    # SAM 2.1's automatic mask generator on clean close-ups (segment.py): 0.9 GB of weights, any card.
    "segment": SINGLE_CARD,
    # DINOv2 features for the render-and-compare (similar.py): 0.35 GB of weights, any card, or a processor machine
    # when no card is in stock (a few hundred pictures take minutes there).
    "similar": SINGLE_CARD + ("cpu-16c-64gb", "cpu-32c-64gb", "cpu-32c-128gb"),
    # UniRig's skeleton and skin models on a finished model (unirig.py): a 350M transformer, any card.
    "unirig": SINGLE_CARD,
    "scene": SINGLE_CARD,
    "closeups": SINGLE_CARD,
    "unlit": SINGLE_CARD,
    "pictures": SINGLE_CARD,
    # A 20B picture model (Qwen-Image-Edit, pictures.MODELS): 58 GB of weights, held whole on an 80 GB card and
    # moved on and off a 48 GB one part by part; one card of a two-card machine is used.
    "pictures-20b": ("gpu-48gb", "gpu-80gb", "gpu-80gb-x2"),
    # The close-up judge (judge.py): a 27B vision-language model in FP8, 30 GB of weights, through vLLM.
    "judge": ("gpu-48gb", "gpu-80gb", "gpu-80gb-x2"),
    "moss-sound": ("gpu-24gb", "gpu-48gb", "gpu-24gb-x2", "gpu-80gb"),
    # The character maker's person chain (characters.py): one person a card, each step's model loaded in turn
    # (Kimodo with its 8B text encoder holds about 17 GB, the largest).
    "characters": SINGLE_CARD,
}
# Kinds that take their offers in an order of their own. Pixal3D: the 80 GB cards first, which run ten takes at once
# (18 takes an hour against an L4's 6, measured 2026-10-08). Library bakes (Cycles): the cards with ray-tracing
# cores first; an H100 has none and baked the same job 2.6 times slower than an L4 (138 s against 360 s).
KIND_ORDER = {
    "pixal": ("gpu-80gb", "gpu-80gb-x2", "gpu-48gb", "gpu-24gb", "gpu-24gb-x2"),
    "library": ("gpu-24gb", "gpu-48gb", "gpu-24gb-x2", "gpu-80gb"),
    # A 20B picture model is held whole only on 80 GB; a 48 GB card moves it on and off part by part, far slower.
    "pictures-20b": ("gpu-80gb", "gpu-80gb-x2", "gpu-48gb"),
    # The judge on an L40S answered at about a third of an H100's pace (102 questions in 45 min, 2026-10-08).
    "judge": ("gpu-80gb", "gpu-80gb-x2", "gpu-48gb"),
}
# Classes a kind takes only after LATE_MINUTES with nothing else to be had: the cards without ray-tracing cores, for
# the bakes.
LATE = {"library": ("gpu-80gb", "gpu-80gb-x2")}
LATE_MINUTES = 5
# How many machines a run may hold: of a class, the backend's quota (provider QUOTAS) else OTHER_MACHINES; of every
# class together, RUN_MACHINES. SCORE_MAX_MACHINES overrides any of them, e.g. "gpu-80gb=20,gpu-24gb=50,all=30".
OTHER_MACHINES = 5
RUN_MACHINES = 20
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


def caps():
    """The machine caps: the backend's quotas by class, then SCORE_MAX_MACHINES's `class=N` pairs over them, with
    `all` for a whole run."""
    found = dict(getattr(provider.cloud, "QUOTAS", {}), all=RUN_MACHINES)
    for pair in filter(None, os.environ.get("SCORE_MAX_MACHINES", "").replace(" ", "").split(",")):
        name, _, number = pair.partition("=")
        if not number.isdigit():
            raise SystemExit(f"SCORE_MAX_MACHINES: '{pair}' is not <class>=<machines>")
        found[name] = int(number)
    return found


def max_machines(machine_class):
    """The most machines of `machine_class` one run holds at once."""
    return caps().get(machine_class, OTHER_MACHINES)


def run_cap():
    """The most machines one run holds at once, whatever their class."""
    return caps()["all"]


def slots_for(kind, classes=None):
    """Jobs of `kind` one machine of the first class it takes (of `classes`, else its own) runs at once: runs_at_once
    on each of its cards."""
    best = min(classes or classes_for(kind), key=lambda machine_class: speed_rank(machine_class, kind))
    return runs_at_once(kind, best) * max(1, provider.cards(best))


def machines_for(units, unit_minutes, setup_minutes, slots=1):
    """How many machines a batch of `units` jobs of about `unit_minutes` each is spread over, when a machine runs
    `slots` at once: enough that each works about as long as its setup takes, or one job's time when a job is longer,
    so the batch ends in about the setup and one job's time without renting machines that would spend most of their
    time setting up. One for a small batch; never more than there are jobs to share, nor than run_cap."""
    if units <= 0:
        return 1
    span = max(setup_minutes, unit_minutes)
    wanted = math.ceil(units * unit_minutes / (slots * span))
    return max(1, min(wanted, math.ceil(units / slots), run_cap()))


def spread_minutes(units, unit_minutes, setup_minutes, machines, slots=1):
    """How long a batch spread over `machines` keeps them: the setup, then each slot's share of the jobs."""
    return setup_minutes + math.ceil(units / (machines * slots)) * unit_minutes


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
    the cheapest; None when there is none, or the run holds its cap of machines (run_cap, max_machines for a class).
    `offers` are provider.Offer; `rented` the run's machines so far, and those being rented (each its class and
    zone)."""
    live = [machine for machine in rented if not machine.get("deleted")]
    held = collections.Counter(machine.get("class") for machine in live)
    offers = [offer for offer in offers if held[offer.machine_class] < max_machines(offer.machine_class)]
    if not offers or len(live) >= run_cap():
        return None
    in_zone = collections.Counter(machine["zone"] for machine in live)
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
