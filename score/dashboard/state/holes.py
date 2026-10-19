"""Holes priced by the runner and only summed here: `score price <world> --holes` prices every paid node in any hole's
chain once (WORK/checks/holes-price/<world>.json, read as models.HolesPrice); this module adds them up and makes no
price and counts no unit. Each basis is kept in a bucket of its own, never mixed: measured runs, per unit times units
counted on an accepted output, per unit times units forecast before the make, and the stages' guesses (with the
file and line each is written on, never part of a price); a node with neither a price nor a guess is unknown. The
prop route of the rows that wait on their place's prop data is summed apart, after that code work; a node outside
the runner's table and a place whose holes check never ran are named, never read as nothing to pay. A stale record
shows no number. A basket item that carries a hole's node is still where it is bought. Plain dicts and
the models only, so a hosted process sums them too.

    found = holes.priced(detail.holes, records.items(root), world.holes_price, place)  # [{hole, item, chain, said}]
    whole = holes.environment(world.holes_total, world.holes_price)   # the environment's total, in one line too
"""
import re
from collections import Counter

from score.dashboard.state.plain import LOST  # a lost input's id: place:lost:<kind>:<item>

BASES = (("measured runs", "measured runs"), ("per unit × counted", "per unit × the units its last make counted"),
         ("per unit × forecast", "per unit × the units forecast before the make"))
GUESS = "not measured yet"
FREE = "a free step: the next run makes it at no cost"
NO_STAGE = "no stage can fill this yet"
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
        return f"{NO_STAGE}: {hole.work}"
    if chain is not None:
        return None
    return said_of_price(price) or (FREE if hole.paid is False else "its node is not in the runner's last price")


def said_of_price(price):
    """Why the runner's price gives no number, in words (no record, or a stale one), or None when it stands."""
    if price is None:
        return NO_PRICE
    if price.stale:
        return f"its price is stale: {price.stale}"
    return None


def priced(holes, items, price, place):
    """Each of the place's holes with the basket item that carries its node, its chain and its words."""
    carried = carriers(items)
    found = []
    for hole in holes:
        chain = hole_chain(hole, price, place)
        found.append({"hole": hole, "item": carried.get(hole.node) if hole.node else None, "chain": chain,
                      "said": said_of(hole, price, chain)})
    return found


def total_words(price, sums, after):
    """The environment's total in one line, or why there is none: its sums, the prop route after the code work
    (`after`), and what is not priced at all."""
    if price is None:
        return NO_PRICE
    if price.stale:
        return f"the runner's price is stale ({price.stale}): run score price world1 --holes again"
    words = [sum_words(sums)]
    if after["places"]:
        words.append(f"after the prop data of {len(after['places'])} places: {sum_words(after['sums'])}")
    unpriced = [f"{steps(len(price.outside), 'node')} outside the stage table" if price.outside else "",
                f"{steps(len(price.not_checked), 'place')} never checked" if price.not_checked else "",
                f"{steps(len(price.not_current), 'place')} not current" if price.not_current else ""]
    if any(unpriced):
        words.append("not priced: " + ", ".join(word for word in unpriced if word))
    return "; ".join(words)


def after_work(price):
    """{places: [{place, work, holes, models, words}], sums} of the prop route the runner priced for the rows that
    wait on their place's prop data, every place's nodes summed once, each basis apart."""
    nodes = {node: found for entry in price.after_work.values() for node, found in entry["nodes"].items()}
    places = [{"place": place, "work": entry["work"], "holes": entry["holes"], "models": entry["models"],
               "words": sum_words(summed(entry["nodes"]))} for place, entry in sorted(price.after_work.items())]
    return {"places": places, "sums": summed(nodes)}


def environment(total, price, items=()):
    """{holes, counts, made_at, stale, sums, after_work, not_in_basket, unfillable, outside, not_current,
    not_checked, words} of every place's holes, None without a holes total: the runner's price of every paid node in
    any hole's chain, each node once and each basis apart, the prop route after its code work apart (no sums while
    the record is missing or stale), how many chain nodes no basket item carries yet (`items`, the basket's), the
    work no stage can fill yet with its hole count, and what the record could not price."""
    if total is None:
        return None
    current = price is not None and not price.stale
    sums = summed(price.nodes) if current else None
    after = after_work(price) if current else None
    carried = carriers(items)
    return {"holes": sum(total.counts.values()), "counts": total.counts, "made_at": price.made_at if price else None,
            "stale": price.stale if price else None, "sums": sums, "after_work": after,
            "not_in_basket": sum(node not in carried for node in price.nodes) if current else None,
            "unfillable": price.unfillable if current else [{"work": work, "holes": None} for work in total.unfillable],
            "outside": price.outside if current else [], "not_current": price.not_current if current else [],
            "not_checked": price.not_checked if current else [],
            "words": total_words(price, sums, after) if current else total_words(price, None, None)}


# --- the environment overview: each place's holes and price, what unblocks most, the code work ------------------

# A hole's kind, worst first: an input its line reads is lost, a step of the route is not done, a scene inventory
# row has nothing made for it, a made object fails a check.
KINDS = (("lost", "Lost inputs"), ("route", "Steps of the route not done"), ("missing", "Not made yet"),
         ("gate", "Made, but failing a check"))
WORLD = "world"  # the holes check's pseudo-place of the environment's own nodes' lost inputs, no place of its own


def kind_of(hole):
    """A hole's kind: lost, route, missing or gate."""
    if hole.rule == "place":
        return "lost" if (hole.id or "").startswith(LOST) else "route"
    return hole.rule


def place_nodes(found, price, place):
    """Every node in the chains of a place's holes, each once."""
    chains = price.chains.get(place, {})
    return {node for hole in found if hole.node for node in chains.get(hole.node, [])}


def place_sum(found, price, place):
    """summed() of every paid node in a place's holes' chains, each once; None with no current record."""
    if price is None or price.stale:
        return None
    return summed({node: price.nodes[node] for node in place_nodes(found, price, place) if node in price.nodes})


def money_of(sums):
    """{likely, high, guessed, measured, paid, unknown} of a sum: its bases added up, the guesses apart, how many of
    its paid steps have a price (`measured`) of how many (`paid`); None for no sum."""
    if sums is None:
        return None
    measured = sum(entry["nodes"] for entry in sums["bases"])
    return {"likely": round(sum(entry["likely"] for entry in sums["bases"]), 2),
            "high": round(sum(entry["high"] for entry in sums["bases"]), 2),
            "guessed": sums["guessed"]["euros"], "measured": measured,
            "paid": measured + sums["guessed"]["nodes"] + len(sums["unknown"]), "unknown": len(sums["unknown"])}


def not_checked(place, found, price):
    """Whether a place's holes are not known: the record names it never checked or not current, or there is no
    record and no holes were read."""
    if price is not None:
        return place in price.not_checked or place in price.not_current
    return not found


def place_row(place, found, price):
    """One place of the overview: its holes by kind, the worst kind, its chains' price, its next route step."""
    counts = {kind: sum(kind_of(hole) == kind for hole in found) for kind, _ in KINDS}
    route = next((hole for hole in found if kind_of(hole) == "route"), None)
    return {"place": place, "holes": len(found), "counts": counts,
            "worst": next((kind for kind, _ in KINDS if counts[kind]), None),
            "money": money_of(place_sum(found, price, place)), "lost": bool(counts["lost"]),
            "not_checked": not_checked(place, found, price), "next": route.sentence if route else None}


def per_place(price, details):
    """[place row] of every place ({place: [hole]}), in the order given."""
    return [place_row(place, found, price) for place, found in details.items()]


def unblocked(price, details):
    """{node: (holes, places)} of every paid node: how many holes have it in their chain, at how many places."""
    per_node = {}
    for place, found in details.items():
        chains = price.chains.get(place, {})
        for node, count in Counter(hole.node for hole in found if hole.node).items():
            for step in chains.get(node, []):
                if step in price.nodes:
                    entry = per_node.setdefault(step, [0, set()])
                    entry[0] += count
                    entry[1].add(place)
    return {node: (holes, len(places)) for node, (holes, places) in per_node.items()}


def node_price(found):
    """A node's own price in words: likely and high by its basis, a guess said as a guess, or neither."""
    if found["likely_euros"] is not None:
        return f"likely EUR {found['likely_euros']:.2f}, high EUR {found['high_euros']:.2f} ({found['basis']})"
    if found.get("guess_euros"):
        return f"EUR {found['guess_euros']:.2f} guessed, not a price"
    return "no price and no guess"


def buy_first(price, details, items=()):
    """[{node, holes, places, price, item}] of every paid node, the most holes unblocked first (a count, never an
    opinion), with its own price by basis and the basket item that carries it; [] with no current record."""
    if price is None or price.stale:
        return []
    carried = carriers(items)
    return [{"node": node, "holes": holes, "places": places, "price": node_price(price.nodes[node]),
             "item": carried.get(node)}
            for node, (holes, places) in sorted(unblocked(price, details).items(),
                                                key=lambda pair: (-pair[1][0], pair[0]))]


LOST_KINDS = {"earth-seed": "The earth seed is lost", "ship-seed": "The ship seed is lost",
              "pixal": "Pixal3D takes are lost", "views": "Views copies are lost",
              "work": "Inputs under the work folder are lost", "reference": "Your reference pictures are missing",
              "data": "Inputs the repository should hold are missing"}


def lost_inputs(details):
    """[{kind, words, items, places, work, ids}] of the lost inputs by kind (place:lost:<kind>:<item>): each input
    once however many places read it, how many places its kind blocks, the most places first."""
    found = {}
    for place, holes in details.items():
        for hole in holes:
            if kind_of(hole) == "lost":
                kind = hole.id.removeprefix(LOST).split(":", 1)[0]
                entry = found.setdefault(kind, {"kind": kind, "words": LOST_KINDS.get(kind, f"Lost inputs ({kind})"),
                                                "ids": set(), "places": set(), "work": set()})
                entry["ids"].add(hole.id)
                entry["places"].add(place)
                entry["work"].add(hole.work or hole.node)
    return sorted(({**entry, "items": len(entry["ids"]), "places": len(entry["places"] - {WORLD}),
                    "ids": sorted(entry["ids"]), "work": sorted(entry["work"])} for entry in found.values()),
                  key=lambda entry: (-entry["places"], entry["kind"]))


def money_words(sums):
    """A sum in the headline's words: measured likely and high by their bases, the guesses said as guesses."""
    money = money_of(sums)
    labels = " and ".join(entry["basis"] for entry in sums["bases"]) or "nothing measured"
    return (f"likely EUR {money['likely']:.0f}, high EUR {money['high']:.0f} measured by {labels}"
            + (f", plus EUR {money['guessed']:.0f} guessed, not a price" if money["guessed"] else ""))


def headline(price):
    """The money headline in one line: to complete, the measured likely and high with the guesses apart, then the
    prop route after its code work apart (a node it makes again with more units is a make of its own), and the holes
    with no price; why there is none when the record is missing or stale."""
    if price is None:
        return NO_PRICE
    if price.stale:
        return f"the runner's price is stale ({price.stale}): run score price world1 --holes again"
    words = ["To complete: " + money_words(summed(price.nodes))]
    after = after_work(price)
    if after["places"]:
        words.append(f"once the prop data of {len(after['places'])} places is written, more: "
                     + money_words(after["sums"]))
    outside = sum(entry.get("holes") or 0 for entry in price.outside)
    waiting = (sum(entry.get("holes") or 0 for entry in price.unfillable)
               - sum(entry.get("holes") or 0 for entry in price.after_work.values()))
    if outside:
        words.append(f"{outside} holes have no price yet (their steps are outside the stage table)")
    if waiting > 0:
        words.append(f"{waiting} more wait on code work no stage does yet")
    return "; ".join(words)


# --- the code work no stage does yet, one task each ----------------------------------------------------------

# Each unfillable work line folded into its code task: the first pattern it matches names the task; a line no
# pattern matches is its own task, said by its first clause.
WORK_TASKS = (
    (r"^prop data for ", "Prop data: a props file per place, so the prop route can price and make its rows"),
    (r"^no props file |no likeness output holds", "Likeness of the props laid without a props file"),
    (r"^a code body \(", "Code bodies per kit (body parts)"),
    (r"^Pixal3D take lost", "Lost Pixal3D takes made again"),
    (r"^earth seed lost", "Earth seed lost: a seed row that exports each place's base"),
    (r"^ship seed lost", "Ship seed lost: the ship kits made again and a ship-seed row"),
    (r"^views lost", "Views lost: read each place's views from its own scene record"),
    (r"^an input under the work folder no row makes", "Inputs under the work folder no row makes"),
    (r"^an input the repository should hold", "Inputs the repository should hold"),
    (r"^no accepted body of their looks|no pilot look is made", "People: bodies for their looks"),
    (r"^a rough-model stage", "A rough-model stage"),
    (r"still take their numbers from the source game", "Layouts still taken from the source game"),
    (r"^a plain code piece against a concept", "Plain code pieces against a concept drawn before the plan"),
    (r"^no effect of the ", "Effects on the follow-up list"),
    (r"^the owner supplies ", "Your own reference pictures"),
    (r"^a concept view request for |^data/plans/\w+\.json with its leads", "Door kits: a concept view and a plan"),
    (r"library surfaces", "Library surfaces held until next month"),
    (r"settle drops|paint level uses|^fix next week", "Settle and paint fixes"),
)


def work_task(work):
    """The code task an unfillable work line folds into."""
    for pattern, task in WORK_TASKS:
        if re.search(pattern, work):
            return task
    return re.split(r"[:;(]", work, maxsplit=1)[0].strip().rstrip(".") or work


def work_places(details):
    """{work: places} of every hole no stage fills: the places whose holes need it."""
    found = {}
    for place, holes in details.items():
        for hole in holes:
            if hole.node is None and hole.work:
                found.setdefault(hole.work, set()).add(place)
    return found


def work_groups(unfillable, details, price=None):
    """[{task, holes, places, lines, after}] of the code work no stage does, one entry a code task, the most holes
    first: the holes it unblocks, the places it touches, its raw lines and, once it is done, what the prop route the
    runner priced after it adds (`after`, words; None when it adds nothing priced)."""
    places = work_places(details)
    after = {entry["work"]: entry["nodes"] for entry in (price.after_work.values() if price and not price.stale
                                                          else [])}
    found = {}
    for entry in unfillable:
        task = found.setdefault(work_task(entry["work"]), {"holes": 0, "places": set(), "lines": [], "nodes": {}})
        task["holes"] += entry.get("holes") or 0
        task["places"] |= places.get(entry["work"], set())
        task["lines"].append(entry)
        task["nodes"].update(after.get(entry["work"], {}))
    return sorted(({"task": name, "holes": task["holes"], "places": len(task["places"]), "lines": task["lines"],
                    "after": sum_words(summed(task["nodes"])) if task["nodes"] else None}
                   for name, task in found.items()), key=lambda entry: (-entry["holes"], entry["task"]))
