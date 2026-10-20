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

from score.dashboard.state.plain import LOST, lost_item  # a lost input's id: place:lost:<kind>:<item>

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
    if after["places"] or after["code"]:
        done = [f"the prop data of {len(after['places'])} places" if after["places"] else "",
                f"{len(after['code'])} Pixal3D code tasks" if after["code"] else ""]
        words.append(f"after {' and '.join(word for word in done if word)}: {sum_words(after['sums'])}")
    unpriced = [f"{steps(len(price.outside), 'node')} outside the stage table" if price.outside else "",
                f"{steps(len(price.not_checked), 'place')} never checked" if price.not_checked else "",
                f"{steps(len(price.not_current), 'place')} not current" if price.not_current else ""]
    if any(unpriced):
        words.append("not priced: " + ", ".join(word for word in unpriced if word))
    return "; ".join(words)


def after_work(price):
    """{places: [{place, work, holes, models, words}], code: [{work, holes, models, words}], sums} of what the runner
    priced after code work: the prop route of the rows that wait on their place's prop data, every place's nodes
    summed once, and the code work whose make is a Pixal3D one (the lost takes, the rough models), each basis
    apart."""
    nodes = {node: found for entry in [*price.after_work.values(), *price.code_work.values()]
             for node, found in entry["nodes"].items()}
    places = [{"place": place, "work": entry["work"], "holes": entry["holes"], "models": entry["models"],
               "words": sum_words(summed(entry["nodes"]))} for place, entry in sorted(price.after_work.items())]
    code = [{"work": work, "holes": entry["holes"], "models": entry["models"],
             "words": sum_words(summed(entry["nodes"]))} for work, entry in sorted(price.code_work.items())]
    return {"places": places, "code": code, "sums": summed(nodes)}


def whole_of(sums):
    """{low, high, measured_likely, measured_high, measured_by, measured, guessed, guessed_steps, unknown, paid} of a
    sum as one figure: low the measured likely plus the guesses, high the measured high plus the guesses; the measured
    part (with the bases it is measured by) and the guessed part kept apart beside it, in euros and in paid steps;
    None for no sum."""
    money = money_of(sums)
    if money is None:
        return None
    return {"low": round(money["likely"] + money["guessed"], 2), "high": round(money["high"] + money["guessed"], 2),
            "measured_likely": money["likely"], "measured_high": money["high"],
            "measured_by": [entry["basis"] for entry in sums["bases"]], "measured": money["measured"],
            "guessed": money["guessed"], "guessed_steps": sums["guessed"]["nodes"], "unknown": money["unknown"],
            "paid": money["paid"]}


def whole_plus(first, second):
    """Two figures of whole_of added into one (the runner's price today and the prop route after its code work: each
    a make of its own), the bases of both named once; the first alone when there is no second."""
    if second is None:
        return first
    added = {key: round(first[key] + second[key], 2) for key in ("low", "high", "measured_likely", "measured_high",
                                                                 "guessed")}
    counted = {key: first[key] + second[key] for key in ("measured", "guessed_steps", "unknown", "paid")}
    return {**added, **counted,
            "measured_by": list(dict.fromkeys(first["measured_by"] + second["measured_by"]))}


def environment(total, price, items=()):
    """{holes, counts, made_at, stale, sums, whole, after_work, whole_after, whole_with_after, not_in_basket,
    unfillable, code_lines, outside, not_current, not_checked, words} of every place's holes, None without a holes
    total: the runner's price of every paid node in any hole's chain, each node once and each basis apart, as one
    figure too (`whole`), the prop route after its code work apart (`whole_after`) and both in one figure
    (`whole_with_after`; no sums while the record is missing or stale), how many chain nodes no basket item carries
    yet (`items`, the basket's), the work no stage can fill yet with its hole count (`code_lines` the code work of
    it, the owner's own actions left out), and what the record could not price."""
    if total is None:
        return None
    current = price is not None and not price.stale
    sums = summed(price.nodes) if current else None
    after = after_work(price) if current else None
    carried = carriers(items)
    whole_after = whole_of(after["sums"]) if after and (after["places"] or after["code"]) else None
    unfillable = price.unfillable if current else [{"work": work, "holes": None} for work in total.unfillable]
    return {"holes": sum(total.counts.values()), "counts": total.counts, "made_at": price.made_at if price else None,
            "stale": price.stale if price else None, "sums": sums, "whole": whole_of(sums), "after_work": after,
            "whole_after": whole_after,
            "whole_with_after": whole_plus(whole_of(sums), whole_after) if whole_after else None,
            "not_in_basket": sum(node not in carried for node in price.nodes) if current else None,
            "unfillable": unfillable,
            "code_lines": [entry for entry in unfillable if not owners_own(entry["work"])],
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


def unpriced(found, price, place):
    """{no_stage, outside} of a place's holes whose chain has no price: no stage fills them, or their node is not in
    the runner's chains for the place (a node outside the stage table)."""
    chains = price.chains.get(place, {}) if price is not None else {}
    return {"no_stage": sum(hole.node is None for hole in found),
            "outside": sum(hole.node is not None and hole.node not in chains for hole in found)}


def worst_rank(worst, unchecked):
    """A place's worst kind of hole as a number to sort by, worst first: its index in KINDS, then no holes, then
    not checked."""
    if unchecked:
        return len(KINDS) + 1
    return [kind for kind, _ in KINDS].index(worst) if worst else len(KINDS)


def place_row(place, found, price, reach=None):
    """One place of the overview: its holes by kind, the worst kind, its chains' price (None while its holes are not
    known), the price of its paid steps no other place's chain has (`own`, from `reach` of node_reach; None without
    it), the holes no price reaches, its next route step."""
    counts = {kind: sum(kind_of(hole) == kind for hole in found) for kind, _ in KINDS}
    route = next((hole for hole in found if kind_of(hole) == "route"), None)
    unchecked = not_checked(place, found, price)
    worst = next((kind for kind, _ in KINDS if counts[kind]), None)
    return {"place": place, "holes": len(found), "counts": counts, "worst": worst,
            "rank": worst_rank(worst, unchecked),
            "money": None if unchecked else money_of(place_sum(found, price, place)),
            "own": None if unchecked or reach is None else money_of(own_sum(found, price, place, reach)),
            "unpriced": unpriced(found, price, place), "lost": bool(counts["lost"]),
            "not_checked": unchecked, "next": route.sentence if route else None}


def node_reach(price, details):
    """Counter {node: how many places' chains have it} of every paid node in the places' holes' chains
    ({place: [hole]}); empty with no current record."""
    reach = Counter()
    if price is None or price.stale:
        return reach
    for place, found in details.items():
        reach.update(node for node in place_nodes(found, price, place) if node in price.nodes)
    return reach


def own_sum(found, price, place, reach):
    """summed() of the paid nodes in a place's holes' chains that no other place's chain has (`reach`, node_reach);
    None with no current record."""
    if price is None or price.stale:
        return None
    return summed({node: price.nodes[node] for node in place_nodes(found, price, place)
                   if node in price.nodes and reach[node] == 1})


def shared_money(price, details):
    """money_of() of the paid nodes two or more places' chains share, each once: what the overview's rows count in
    each of their places and the total once; None with no current record."""
    if price is None or price.stale:
        return None
    reach = node_reach(price, details)
    return money_of(summed({node: price.nodes[node] for node, count in reach.items() if count > 1}))


def per_place(price, details):
    """[place row] of every place ({place: [hole]}), in the order given, each with its own steps' price."""
    reach = node_reach(price, details)
    return [place_row(place, found, price, reach) for place, found in details.items()]


def waits_first(found):
    """Whether a place's holes include a lost input or a route step not done: every later step there waits on it."""
    return any(kind_of(hole) in ("lost", "route") for hole in found)


def in_chains(price, details):
    """{node: (holes, places, waiting)} of every paid node: how many holes have it in their chain, at how many
    places, and how many of those holes sit at a place with a lost input or a route step not done, so the node
    cannot run there before that is put right."""
    per_node = {}
    for place, found in details.items():
        chains = price.chains.get(place, {})
        waiting = waits_first(found)
        for node, count in Counter(hole.node for hole in found if hole.node).items():
            for step in chains.get(node, []):
                if step in price.nodes:
                    entry = per_node.setdefault(step, [0, set(), 0])
                    entry[0] += count
                    entry[1].add(place)
                    entry[2] += count if waiting else 0
    return {node: (holes, len(places), waiting) for node, (holes, places, waiting) in per_node.items()}


def node_price(found):
    """A node's own price in words: likely and high by its basis, a guess said as a guess, or neither."""
    if found["likely_euros"] is not None:
        return f"likely EUR {found['likely_euros']:.2f}, high EUR {found['high_euros']:.2f} ({found['basis']})"
    if found.get("guess_euros"):
        return f"EUR {found['guess_euros']:.2f} guessed, not a price"
    return "no price and no guess"


def buy_first(price, details, items=()):
    """[{node, holes, places, waiting, price, item}] of every paid node, the most holes with it in their chain first
    (a count, never an opinion), how many of them wait on a lost input or a route step first, with its own price by
    basis and the basket item that carries it; [] with no current record."""
    if price is None or price.stale:
        return []
    carried = carriers(items)
    return [{"node": node, "holes": holes, "places": places, "waiting": waiting,
             "price": node_price(price.nodes[node]), "item": carried.get(node)}
            for node, (holes, places, waiting) in sorted(in_chains(price, details).items(),
                                                         key=lambda pair: (-pair[1][0], pair[0]))]


def code_first(price, details):
    """[{task, places, holes, money, owner}] of the work the places wait on before a paid step fills a hole there:
    each lost input or route step no stage fills at a place, folded into its task (work_task), with how many places
    it is at, how many holes there have a paid chain (they wait on it) and those chains' paid steps' money (money_of,
    each node once), and whether it is the owner's own action rather than code (`owner`, owners_own); the most holes
    first, then the most euros. A place waits on every task listed at it, so a task frees its places only with the
    others there; [] with no current record."""
    if price is None or price.stale:
        return []
    found, owners = {}, set()
    for place, listed in details.items():
        for hole in listed:
            if place != WORLD and hole.node is None and hole.work and kind_of(hole) in ("lost", "route"):
                found.setdefault(work_task(hole.work), set()).add(place)
                if owners_own(hole.work):
                    owners.add(work_task(hole.work))
    rows = []
    for task, places in found.items():
        chained = sum(1 for place in places for hole in details[place]
                      if hole.node and hole.node in price.chains.get(place, {}))
        nodes = {node for place in places for node in place_nodes(details[place], price, place) if node in price.nodes}
        rows.append({"task": task, "places": len(places), "holes": chained, "owner": task in owners,
                     "money": money_of(summed({node: price.nodes[node] for node in nodes}))})
    return sorted(rows, key=lambda row: (-row["holes"], -(row["money"]["high"] + row["money"]["guessed"]),
                                         row["task"]))


LOST_KINDS = {"earth-seed": "The earth seed is lost", "ship-seed": "The ship seed is lost",
              "pixal": "Pixal3D takes are lost", "views": "Views copies are lost",
              "work": "Inputs under the work folder are lost", "reference": "Your reference pictures are missing",
              "data": "Inputs the repository should hold are missing"}


def lost_inputs(details):
    """[{kind, words, items, places, work, ids, coded, bought, owner, files}] of the lost inputs by kind
    (place:lost:<kind>:<item>): each input once however many places read it, how many places its kind blocks, split
    by what brings each back: no node, so code work (`coded`, its lines in `work`), or a paid node a run makes again
    (`bought`: [{node, inputs}]); `owner` when every line is the owner's own action, with the files he supplies; the
    most places first."""
    found = {}
    for place, holes in details.items():
        for hole in holes:
            if kind_of(hole) == "lost":
                kind = hole.id.removeprefix(LOST).split(":", 1)[0]
                entry = found.setdefault(kind, {"kind": kind, "words": LOST_KINDS.get(kind, f"Lost inputs ({kind})"),
                                                "ids": set(), "places": set(), "work": set(), "coded": set(),
                                                "bought": {}})
                entry["ids"].add(hole.id)
                entry["places"].add(place)
                if hole.node:
                    entry["bought"].setdefault(hole.node, set()).add(hole.id)
                else:
                    entry["coded"].add(hole.id)
                    entry["work"].add(hole.work)
    return sorted((lost_kind(entry) for entry in found.values()), key=lambda entry: (-entry["places"], entry["kind"]))


def lost_kind(entry):
    """One kind of lost_inputs, its sets counted and sorted."""
    owner = bool(entry["work"]) and all(owners_own(work) for work in entry["work"])
    return {**entry, "items": len(entry["ids"]), "places": len(entry["places"] - {WORLD}), "ids": sorted(entry["ids"]),
            "work": sorted(work for work in entry["work"] if work), "coded": len(entry["coded"]),
            "bought": [{"node": node, "inputs": len(ids)} for node, ids in sorted(entry["bought"].items())],
            "owner": owner, "files": sorted(lost_item(ident) for ident in entry["coded"]) if owner else []}


def headline(price):
    """What no figure of the total holds, in one line under it: the holes whose steps are outside the stage table and
    the holes that wait on code work no stage does yet; None with nothing to say, or while the record is missing or
    stale (the total says why it has no figure). The figures themselves lead (whole_of), never repeated here."""
    if price is None or price.stale:
        return None
    outside = sum(entry.get("holes") or 0 for entry in price.outside)
    waiting = (sum(entry.get("holes") or 0 for entry in price.unfillable)
               - sum(entry.get("holes") or 0 for entry in [*price.after_work.values(), *price.code_work.values()]))
    words = []
    if outside:
        words.append(f"{outside} holes have no price yet (their steps are outside the stage table)")
    if waiting > 0:
        words.append(f"{waiting} holes wait on code work no stage does yet, in no figure above")
    return "; ".join(words) or None


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
# A work line that is the owner's own action, not code to write: he supplies a file of his own.
OWNER = r"^the owner supplies "
# The paid work a piece of code work brings once it lands that no record prices yet, as the holes check writes it:
# the first pattern a work line matches, said with its lines' holes ({holes}) and their places ({places}, in words).
# A line that names its paid node (the group) is left out while the runner's record prices that node.
BRINGS = ((r"^Pixal3D take lost", "the lost Pixal3D takes made again ({holes})"),
          (r"^a rough-model stage", "the rough-model stage at {places}"),
          (r"^ship seed lost: (\S+@\S+) \(paid", "the ship kits made again at {places}"))


def owners_own(work):
    """Whether a work line no stage fills is the owner's own action (OWNER), not code to write."""
    return bool(work and re.search(OWNER, work))


def owner_work(details):
    """{files, places} of what only the owner can do: the files he supplies (each once, from the lost inputs whose
    work is his) and how many places read them (the environment's own pseudo-place not one); None when there is
    none."""
    files, places = set(), set()
    for place, found in details.items():
        for hole in found:
            if hole.node is None and owners_own(hole.work):
                files.add(lost_item(hole.id) if kind_of(hole) == "lost" else hole.work)
                if place != WORLD:
                    places.add(place)
    return {"files": sorted(files), "places": len(places)} if files else None


def brought(price):
    """{words: {holes, works}} of the paid work the code work brings that the record does not price (BRINGS, a line
    the record prices in its code work left out), each pattern's lines added up."""
    found = {}
    for entry in price.unfillable:
        if entry["work"] in price.code_work:
            continue
        for pattern, words in BRINGS:
            matched = re.search(pattern, entry["work"])
            if matched:
                if not (matched.groups() and matched.group(1) in price.nodes):
                    slot = found.setdefault(words, {"holes": 0, "works": set()})
                    slot["holes"] += entry.get("holes") or 0
                    slot["works"].add(entry["work"])
                break
    return found


def held_back(details, price, works):
    """(places, holes) the work lines `works` hold back: the places their holes are at (the environment's own
    pseudo-place not one), and their own holes with every hole that has a paid chain at those places, a lost input
    once."""
    places, held = set(), set()
    for place, listed in details.items():
        if not any(hole.node is None and hole.work in works for hole in listed):
            continue
        if place != WORLD:
            places.add(place)
        for hole in listed:
            if (hole.node is None and hole.work in works) or (hole.node and hole.node in price.chains.get(place, {})):
                held.add(hole.id if kind_of(hole) == "lost" else (place, hole.id))
    return places, held


def unpriced_work(price, details):
    """{lines, holes} of the paid work the code work brings that no record prices yet: a line each in words, and how
    many holes it holds back, each once (held_back); None with no such work or no current record."""
    if price is None or price.stale:
        return None
    lines, held = [], set()
    for words, slot in brought(price).items():
        places, holes = held_back(details, price, slot["works"])
        lines.append(words.format(holes=slot["holes"], places=steps(len(places), "place")))
        held |= holes
    return {"lines": lines, "holes": len(held)} if lines else None


def work_task(work):
    """The code task an unfillable work line folds into."""
    for pattern, task in WORK_TASKS:
        if re.search(pattern, work):
            return task
    return re.split(r"[:;(]", work, maxsplit=1)[0].strip().rstrip(".") or work


def work_holes(details):
    """{work: {holes, inputs, places}} of every hole no stage fills, from the holes check's findings: the holes that
    need it (a lost input once however many places read it, as the total counts it, in `inputs` as ids), and the
    places whose holes need it (the environment's own pseudo-place not one)."""
    found = {}
    for place, holes in details.items():
        for hole in holes:
            if hole.node is None and hole.work:
                entry = found.setdefault(hole.work, {"holes": set(), "inputs": set(), "places": set()})
                if kind_of(hole) == "lost":
                    entry["inputs"].add(hole.id)
                else:
                    entry["holes"].add((place, hole.id))
                if place != WORLD:
                    entry["places"].add(place)
    return found


def work_groups(unfillable, details, price=None):
    """[{task, holes, inputs, places, lines, after}] of the code work no stage does, one entry a code task, the most
    holes first: the holes that need it and the lost inputs (each once) it makes again, counted from the holes
    check's findings (`details`, the environment's own pseudo-place too), the places they are at, its raw lines and,
    once it is done, what the prop route the runner priced after it adds (`after`, words; None when it adds nothing
    priced). The owner's own actions (owners_own) are not code and not in it: owner_work says them."""
    counted = work_holes(details)
    current = price is not None and not price.stale
    after = {entry["work"]: entry["nodes"] for entry in (price.after_work.values() if current else [])}
    after.update({work: entry["nodes"] for work, entry in (price.code_work.items() if current else [])})
    found = {}
    for entry in unfillable:
        if owners_own(entry["work"]):
            continue
        task = found.setdefault(work_task(entry["work"]),
                                {"holes": set(), "inputs": set(), "places": set(), "lines": [], "nodes": {}})
        mine = counted.get(entry["work"], {"holes": set(), "inputs": set(), "places": set()})
        for part in ("holes", "inputs", "places"):
            task[part] |= mine[part]
        task["lines"].append(entry)
        task["nodes"].update(after.get(entry["work"], {}))
    return sorted(({"task": name, "holes": len(task["holes"]), "inputs": len(task["inputs"]),
                    "places": len(task["places"]), "lines": task["lines"],
                    "after": sum_words(summed(task["nodes"])) if task["nodes"] else None}
                   for name, task in found.items()),
                  key=lambda entry: (-(entry["holes"] + entry["inputs"]), entry["task"]))
