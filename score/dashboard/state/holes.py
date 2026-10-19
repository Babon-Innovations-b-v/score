"""Holes priced by the runner and only summed here: `score price <world> --holes` prices every paid node in any hole's
chain once (WORK/checks/holes-price/<world>.json, read as models.HolesPrice); this module adds them up and makes no
price and counts no unit. Each basis is kept in a bucket of its own, never mixed: measured runs, per unit times units
counted on an accepted output, per unit times units forecast before the make, and the stages' guesses (with the
file and line each is written on, never part of a price); a node with neither a price nor a guess is unknown. A
stale record shows no number. A basket item that carries a hole's node is still where it is bought. Plain dicts and
the models only, so a hosted process sums them too.

    found = holes.priced(detail.holes, records.items(root), world.holes_price, place)  # [{hole, item, chain, said}]
    whole = holes.environment(world.holes_total, world.holes_price)   # the environment's total, in one line too
"""
BASES = (("measured runs", "measured runs"), ("per unit × counted", "per unit × the units its last make counted"),
         ("per unit × forecast", "per unit × the units forecast before the make"))
GUESS = "not measured yet"
FREE = "a free step: the next run makes it at no cost"
NO_PRICE = "the runner has not priced the holes yet (score price world1 --holes)"


def carriers(items):
    """{node: item id} of every node a basket item carries, the first item that does."""
    found = {}
    for item in items:
        for node in item["nodes"]:
            found.setdefault(node, item["id"])
    return found


def summed(prices):
    """{bases: [{basis, label, likely, high, nodes}], guessed: {euros, nodes, sources: [{at, euros, nodes}]},
    unknown: [nodes]} of nodes' prices ({node: price}), each basis apart."""
    bases = []
    for basis, label in BASES:
        found = [price for price in prices.values() if price["basis"] == basis]
        if found:
            bases.append({"basis": basis, "label": label, "nodes": len(found),
                          "likely": round(sum(price["likely_euros"] for price in found), 2),
                          "high": round(sum(price["high_euros"] for price in found), 2)})
    guesses = {node: price for node, price in prices.items() if price["basis"] == GUESS and price.get("guess_euros")}
    sources = {}
    for price in guesses.values():
        entry = sources.setdefault(price.get("guess_from") or "not said", {"euros": 0.0, "nodes": 0})
        entry["euros"], entry["nodes"] = entry["euros"] + price["guess_euros"], entry["nodes"] + 1
    return {"bases": bases,
            "guessed": {"euros": round(sum(price["guess_euros"] for price in guesses.values()), 2),
                        "nodes": len(guesses),
                        "sources": [{"at": at, "euros": round(entry["euros"], 2), "nodes": entry["nodes"]}
                                    for at, entry in sorted(sources.items(), key=lambda pair: -pair[1]["euros"])]},
            "unknown": sorted(node for node, price in prices.items()
                              if price["basis"] not in dict(BASES) and not price.get("guess_euros"))}


def steps(count, word="step"):
    """`count` steps in words: "1 step", "3 steps"."""
    return f"{count} {word}{'' if count == 1 else 's'}"


def sum_words(sums):
    """A sum's buckets in one line: each basis's likely and high, the guesses apart, the unknown nodes."""
    words = [f"{entry['label']}: likely EUR {entry['likely']:.2f}, high EUR {entry['high']:.2f} "
             f"({steps(entry['nodes'])})" for entry in sums["bases"]]
    if sums["guessed"]["nodes"]:
        words.append(f"guessed, not a price: EUR {sums['guessed']['euros']:.2f} ({steps(sums['guessed']['nodes'])})")
    if sums["unknown"]:
        words.append(f"{steps(len(sums['unknown']))} with no price and no guess")
    return "; ".join(words) or "nothing paid"


def chain_rows(nodes, price):
    """[{node, basis, euros}] of a chain's nodes: each paid one's basis and euros in words, a free one as free."""
    rows = []
    for node in nodes:
        found = price.nodes.get(node)
        if found is None:
            rows.append({"node": node, "basis": "free", "euros": ""})
        elif found["likely_euros"] is not None:
            rows.append({"node": node, "basis": found["basis"],
                         "euros": f"likely EUR {found['likely_euros']:.2f}, high EUR {found['high_euros']:.2f}"})
        else:
            guess = found.get("guess_euros")
            rows.append({"node": node, "basis": found["basis"],
                         "euros": f"guess EUR {guess:.2f} ({found.get('guess_from') or 'not said'})" if guess
                         else "no price, no guess"})
    return rows


def hole_chain(hole, price, place):
    """{words, rows} of the chain a hole's node needs at the place, or None (no record, stale, or not in it)."""
    if price is None or price.stale or hole.node is None:
        return None
    nodes = price.chains.get(place, {}).get(hole.node)
    if nodes is None:
        return None
    paid = {node: price.nodes[node] for node in nodes if node in price.nodes}
    return {"words": f"{steps(len(paid), 'paid step')} in its chain: {sum_words(summed(paid))}",
            "rows": chain_rows(nodes, price)}


def said_of(hole, price, chain):
    """Why a hole has no chain to show, in words, or None when it has one."""
    if hole.node is None:
        return f"no stage can fill this yet: {hole.work}"
    if chain is not None:
        return None
    if price is None:
        return NO_PRICE
    if price.stale:
        return f"its price is stale: {price.stale}"
    return FREE if hole.paid is False else "its node is not in the runner's last price"


def priced(holes, items, price, place):
    """Each of the place's holes with the basket item that carries its node, its chain and its words."""
    carried = carriers(items)
    found = []
    for hole in holes:
        chain = hole_chain(hole, price, place)
        found.append({"hole": hole, "item": carried.get(hole.node) if hole.node else None, "chain": chain,
                      "said": said_of(hole, price, chain)})
    return found


def total_words(price, sums):
    """The environment's total in one line, or why there is none."""
    if price is None:
        return NO_PRICE
    if price.stale:
        return f"the runner's price is stale ({price.stale}): run score price world1 --holes again"
    return sum_words(sums)


def environment(total, price, items=()):
    """{holes, counts, made_at, stale, sums, not_in_basket, unfillable, words} of every place's holes, None without
    a holes total: the runner's price of every paid node in any hole's chain, each node once and each basis apart (no
    sums while the record is missing or stale), how many of those nodes no basket item carries yet (`items`, the
    basket's), and the work no stage can fill yet with its hole count."""
    if total is None:
        return None
    current = price is not None and not price.stale
    sums = summed(price.nodes) if current else None
    carried = carriers(items)
    return {"holes": sum(total.counts.values()), "counts": total.counts, "made_at": price.made_at if price else None,
            "stale": price.stale if price else None, "sums": sums,
            "not_in_basket": sum(node not in carried for node in price.nodes) if current else None,
            "unfillable": price.unfillable if current else [{"work": work, "holes": None} for work in total.unfillable],
            "not_current": price.not_current if current else [], "words": total_words(price, sums)}
