"""The basket's prices: each paid node at the runner's own numbers (its plan's price, C19), and the totals of an item
and of the basket. Never per-piece prices alone: the pages show the basket's total against the stop.
"""
# The runner jobs at once a batch's time is reckoned on (the launch guard's default too). 16 (owner, 2026-10-22: the
# full world1 batch about 8 h at 8, 4 h at 16): most nodes wait on rented machines, and the local ones measured
# 0.21-0.28 GB peak each (score.graph MEMORY_FLOOR), while the runner holds back every start while this 43 GB PC
# has under its 6 GB floor free; 16 on 24 cores leaves each node one thread.
DEFAULT_JOBS = 16


def line_of(node):
    return node.split("@")[1] if "@" in node else "world"


def span(prices, field, jobs):
    """The minutes a batch of these nodes takes at `field`: the longer of the longest line's sum and the total over
    `jobs` at once (an unmeasured node counts nothing; it is listed apart)."""
    lines = {}
    for node, price in prices.items():
        lines[line_of(node)] = lines.get(line_of(node), 0.0) + (price.get(field) or 0.0)
    return round(max(max(lines.values(), default=0.0), sum(lines.values()) / max(1, jobs)), 1)


def totals(prices, jobs=DEFAULT_JOBS):
    """{likely_euros, high_euros, guessed_euros, likely_minutes, high_minutes, cards, nodes, unmeasured, unpriced} of
    nodes priced ({node: price}): likely and high the measured nodes' sums; `guessed_euros` the stage estimates of
    the nodes not measured yet (`unmeasured`), never part of the price; `unpriced` the nodes the runner could not
    price (each counts nothing)."""
    priced = {node: price for node, price in prices.items() if "error" not in price}
    measured = [price for price in priced.values() if price["likely_euros"] is not None]
    return {"likely_euros": round(sum(price["likely_euros"] for price in measured), 2),
            "high_euros": round(sum(price["high_euros"] for price in measured), 2),
            "guessed_euros": round(sum(price.get("guess_euros") or 0.0 for price in priced.values()
                                       if price["likely_euros"] is None), 2),
            "likely_minutes": span(priced, "likely_minutes", jobs), "high_minutes": span(priced, "high_minutes", jobs),
            "cards": sum(price.get("cards") or 0 for price in priced.values()), "nodes": len(prices),
            "unmeasured": sorted(node for node, price in priced.items() if not price.get("runs")),
            "unpriced": sorted(node for node in prices if node not in priced)}


def cleared_high(totals):
    """What the runner clears these nodes at: their measured high and, for every node not measured yet, its stage's
    estimate (the runner's clearance reserves that guess, so the stop line must hold it)."""
    return round(totals["high_euros"] + totals.get("guessed_euros", 0.0), 2)


def basket_prices(items):
    """{node: price} of every item's nodes, each node once."""
    found = {}
    for item in items:
        found.update(item["nodes"])
    return found
