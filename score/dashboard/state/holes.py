"""Holes priced from the basket, joined when a page is read: a hole whose node a basket item carries gets that item and
the runner's price for the node; one whose node no item carries is said as the runner buying nothing for it now; one
with only its code work goes on the list no stage can fill yet, with no price. Reads the basket's records only (plain
dicts), so a hosted process prices them too.

    found = holes.priced(detail.holes, records.items(root))       # [{hole, item, price, said}]
    whole = holes.environment(world.holes_total, records.items(root))   # the environment's total, in one line too
"""
from score.dashboard.checkout import pricing
from score.dashboard.state import groups


def carriers(items):
    """{node: (item id, the node's price)} of every node a basket item carries, the first item that does."""
    found = {}
    for item in items:
        for node, price in item["nodes"].items():
            found.setdefault(node, (item["id"], price))
    return found


def not_bought(node):
    """Why the runner buys nothing for a node now, in words (no node id)."""
    return (f"the runner buys nothing for it now: {groups.label(node.split('@', 1)[0])} is accepted or waits on an "
            "earlier step")


def priced_one(hole, carried):
    """{hole, item, price, said} of one hole: its item and price, why nothing buys it, or the work no stage does."""
    if hole.node is None:
        return {"hole": hole, "item": None, "price": None, "said": f"no stage can fill this yet: {hole.work}"}
    item, price = carried.get(hole.node, (None, None))
    return {"hole": hole, "item": item, "price": price, "said": None if item else not_bought(hole.node)}


def priced(holes, items):
    """Each hole with its item and price, or its words."""
    carried = carriers(items)
    return [priced_one(hole, carried) for hole in holes]


def environment(total, items):
    """{likely, high, guessed, holes, unfillable, nodes, words} of every place's holes: the runner's totals over the
    distinct nodes a basket item carries (each node once; measured, guessed and unpriced kept apart as
    pricing.totals keeps them) and the work no stage can fill yet; None without a holes total."""
    if total is None:
        return None
    carried = carriers(items)
    summed = pricing.totals({node: carried[node][1] for node in total.nodes if node in carried})
    measured = summed["nodes"] - len(summed["unmeasured"]) - len(summed["unpriced"])
    likely, high = (summed["likely_euros"], summed["high_euros"]) if measured else (None, None)
    guessed = len(summed["unmeasured"])
    words = f"likely EUR {likely:.2f}, high EUR {high:.2f}" if likely is not None else "no measured price yet"
    words += f"; {guessed} guessed; {total.unfillable_count} holes no stage can fill yet"
    return {"likely": likely, "high": high, "guessed": guessed, "holes": sum(total.counts.values()),
            "counts": total.counts, "unfillable": total.unfillable, "nodes": len(total.nodes), "words": words}
