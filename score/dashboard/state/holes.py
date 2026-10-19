"""Holes priced from the basket, joined when a page is read: a hole whose node a basket item carries gets that item and
the runner's price for the node; one whose node no item carries says only what the cockpit can read (a free step,
or no item of the last basket make carries it); one with only its code work goes on the list no stage can fill yet,
with no price. Reads the basket's records only (plain dicts), so a hosted process prices them too.

    found = holes.priced(detail.holes, records.items(root))       # [{hole, item, price, said}]
    whole = holes.environment(world.holes_total, records.items(root))   # the environment's total, in one line too
"""
from score.dashboard.checkout import pricing

FREE = "a free step: the next run makes it at no cost"
NOT_CARRIED = "no item of the last basket make carries it"


def carriers(items):
    """{node: (item id, the node's price)} of every node a basket item carries, the first item that does."""
    found = {}
    for item in items:
        for node, price in item["nodes"].items():
            found.setdefault(node, (item["id"], price))
    return found


def not_bought(hole):
    """Why no basket item buys a hole's node, as far as the cockpit can read it (no node id)."""
    return FREE if hole.paid is False else NOT_CARRIED


def priced_one(hole, carried):
    """{hole, item, price, said} of one hole: its item and price, why nothing buys it, or the work no stage does."""
    if hole.node is None:
        return {"hole": hole, "item": None, "price": None, "said": f"no stage can fill this yet: {hole.work}"}
    item, price = carried.get(hole.node, (None, None))
    return {"hole": hole, "item": item, "price": price, "said": None if item else not_bought(hole)}


def priced(holes, items):
    """Each hole with its item and price, or its words."""
    carried = carriers(items)
    return [priced_one(hole, carried) for hole in holes]


def measured(summed):
    """How many of pricing.totals' nodes have a measured price."""
    return summed["nodes"] - len(summed["unmeasured"]) - len(summed["unpriced"])


def total_words(summed, uncarried, unfillable):
    """The environment's total in one line: the measured price (or none yet), the guessed nodes, the paid steps no
    item carries and the holes no stage can fill yet."""
    words = (f"likely EUR {summed['likely_euros']:.2f}, high EUR {summed['high_euros']:.2f}" if measured(summed)
             else "no measured price yet")
    words += f"; {len(summed['unmeasured'])} guessed"
    if uncarried:
        words += f"; {uncarried} paid steps not in the basket, unpriced"
    return words + f"; {unfillable} holes no stage can fill yet"


def environment(total, items):
    """{likely, holes, counts, unfillable, uncarried, words} of every place's holes, None without a holes total: the
    runner's totals over every node of the basket items that fill a hole (each node once, with the nodes the runner
    makes after it; measured, guessed and unpriced kept apart as pricing.totals keeps them), the paid nodes no item
    carries (`uncarried`, unpriced) and the work no stage can fill yet."""
    if total is None:
        return None
    holes = set(total.nodes)
    prices = pricing.basket_prices([item for item in items if holes & set(item["nodes"])])
    summed = pricing.totals(prices)
    uncarried = sum(node not in prices for node in total.paid_nodes)
    return {"likely": summed["likely_euros"] if measured(summed) else None, "holes": sum(total.counts.values()),
            "counts": total.counts, "unfillable": total.unfillable, "uncarried": uncarried,
            "words": total_words(summed, uncarried, total.unfillable_count)}
