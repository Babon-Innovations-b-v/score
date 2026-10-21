"""Gaps priced by the runner and only summed here: `score price <world> --gaps` prices every paid node in any gap's
chain once (WORK/checks/gaps-price/<world>.json, read as models.GapsPrice); this module adds them up and makes no
price and counts no unit. Each basis is kept in a bucket of its own, never mixed: measured runs, per unit times units
counted on an accepted output, per unit times units forecast before the make, and the stages' guesses (with the
file and line each is written on, never part of a price); a node with neither a price nor a guess is unknown. A
place whose gaps check never ran is named, never read as nothing to pay. A stale record shows no number. Plain
dicts and the models only, so a hosted process sums them too.

    rows = gaps.per_place(world.gaps_price, {place: [gap]})  # each place's gaps by kind and its chains' price
    plan = gaps.plan_of(world.gaps_price)                     # the runner's milestones and the remake's total
"""
import re
from collections import Counter

from score.dashboard.state.costs import hours
from score.dashboard.state.groups import label  # a stage in words
from score.dashboard.state.plain import LOST  # a lost input's id: place:lost:<kind>:<item>

BASES = (("measured runs", "measured runs"), ("per unit × counted", "per unit × the units its last make counted"),
         ("per unit × forecast", "per unit × the units forecast before the make"))
GUESS = "not measured yet"
NO_PRICE = "the runner has not priced the gaps yet (score price world1 --gaps)"


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


def said_of_price(price):
    """Why the runner's price gives no number, in words (no record, or a stale one), or None when it stands."""
    if price is None:
        return NO_PRICE
    if price.stale:
        return f"its price is stale: {price.stale}"
    return None


# --- the environment overview: each place's gaps and price, what unblocks most, the code work ------------------

# A gap's kind, worst first: an input its line reads is lost, a step of the route is not done, a scene inventory
# row has nothing made for it, a made object fails a check.
KINDS = (("lost", "Lost inputs"), ("route", "Steps of the route not done"), ("missing", "Not made yet"),
         ("gate", "Made, but failing a check"))
WORLD = "world"  # the gaps check's pseudo-place of the environment's own nodes' lost inputs, no place of its own


def kind_of(gap):
    """A gap's kind: lost, route, missing or gate."""
    if gap.rule == "place":
        return "lost" if (gap.id or "").startswith(LOST) else "route"
    return gap.rule


def place_nodes(found, price, place):
    """Every node in the chains of a place's gaps, each once."""
    chains = price.chains.get(place, {})
    return {node for gap in found if gap.node for node in chains.get(gap.node, [])}


def place_sum(found, price, place):
    """summed() of every paid node in a place's gaps' chains, each once; None with no current record."""
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
    """Whether a place's gaps are not known: the record names it never checked or not current, or there is no
    record and no gaps were read."""
    if price is not None:
        return place in price.not_checked or place in price.not_current
    return not found


def unpriced(found, price, place):
    """{no_stage, outside} of a place's gaps whose chain has no price: no stage fills them, or their node is not in
    the runner's chains for the place (a node outside the stage table)."""
    chains = price.chains.get(place, {}) if price is not None else {}
    return {"no_stage": sum(gap.node is None for gap in found),
            "outside": sum(gap.node is not None and gap.node not in chains for gap in found)}


def worst_rank(worst, unchecked):
    """A place's worst kind of gap as a number to sort by, worst first: its index in KINDS, then no gaps, then
    not checked."""
    if unchecked:
        return len(KINDS) + 1
    return [kind for kind, _ in KINDS].index(worst) if worst else len(KINDS)


def place_row(place, found, price, reach=None):
    """One place of the overview: its gaps by kind, the worst kind, its chains' price (None while its gaps are not
    known), the price of its paid steps no other place's chain has (`own`, from `reach` of node_reach; None without
    it), the gaps no price reaches, its next route step."""
    counts = {kind: sum(kind_of(gap) == kind for gap in found) for kind, _ in KINDS}
    route = next((gap for gap in found if kind_of(gap) == "route"), None)
    unchecked = not_checked(place, found, price)
    worst = next((kind for kind, _ in KINDS if counts[kind]), None)
    return {"place": place, "gaps": len(found), "counts": counts, "worst": worst,
            "rank": worst_rank(worst, unchecked),
            "money": None if unchecked else money_of(place_sum(found, price, place)),
            "own": None if unchecked or reach is None else money_of(own_sum(found, price, place, reach)),
            "unpriced": unpriced(found, price, place), "lost": bool(counts["lost"]),
            "not_checked": unchecked, "next": route.sentence if route else None}


def node_reach(price, details):
    """Counter {node: how many places' chains have it} of every paid node in the places' gaps' chains
    ({place: [gap]}); empty with no current record."""
    reach = Counter()
    if price is None or price.stale:
        return reach
    for place, found in details.items():
        reach.update(node for node in place_nodes(found, price, place) if node in price.nodes)
    return reach


def own_sum(found, price, place, reach):
    """summed() of the paid nodes in a place's gaps' chains that no other place's chain has (`reach`, node_reach);
    None with no current record."""
    if price is None or price.stale:
        return None
    return summed({node: price.nodes[node] for node in place_nodes(found, price, place)
                   if node in price.nodes and reach[node] == 1})


def per_place(price, details):
    """[place row] of every place ({place: [gap]}), in the order given, each with its own steps' price."""
    reach = node_reach(price, details)
    return [place_row(place, found, price, reach) for place, found in details.items()]


# --- the code work no stage does yet, one task each ----------------------------------------------------------

# Each unfillable work line folded into its code task: the first pattern it matches names the task; a line no
# pattern matches is its own task, said by its first clause.
WORK_TASKS = (
    (r"^prop data for ", "Prop data: a props file per scene, so the prop route can price and make its rows"),
    (r"^no props file |no likeness output holds", "Likeness of the props laid without a props file"),
    (r"^a code body \(", "Code bodies per kit (body parts)"),
    (r"^Pixal3D take lost", "Lost Pixal3D takes made again"),
    (r"^earth seed lost", "Earth seed lost: a seed row that exports each scene's base"),
    (r"^ship seed lost", "Ship seed lost: the ship kits made again and a ship-seed row"),
    (r"^views lost", "Views lost: read each scene's views from its own scene record"),
    (r"^an input under the work folder no row makes", "Inputs under the work folder no row makes"),
    (r"^an input the repository should hold", "Inputs the repository should hold"),
    (r"^no accepted body of their looks|no pilot look is made", "People: bodies for their looks"),
    (r"still take their numbers from the source game", "Layouts still taken from the source game"),
    (r"^a plain code piece against a concept", "Plain code pieces against a concept drawn before the plan"),
    (r"^no effect of the ", "Effects on the follow-up list"),
    (r"^the owner supplies ", "Your own reference pictures"),
    (r"^a concept view request for |^data/plans/\w+\.json with its leads", "A concept view and a plan"),
    (r"library surfaces", "Library surfaces held until next month"),
    (r"settle drops|paint level uses|^fix next week", "Settle and paint fixes"),
)
# A work line that is the owner's own action, not code to write: he supplies a file of his own.
OWNER = r"^the owner supplies "
# The paid work a piece of code work brings once it lands that no record prices yet, as the gaps check writes it:
# the first pattern a work line matches, said with its lines' gaps ({gaps}) and their places ({places}, in words).
# A line that names its paid node (the group) is left out while the runner's record prices that node.
def owners_own(work):
    """Whether a work line no stage fills is the owner's own action (OWNER), not code to write."""
    return bool(work and re.search(OWNER, work))


def work_task(work):
    """The code task an unfillable work line folds into."""
    for pattern, task in WORK_TASKS:
        if re.search(pattern, work):
            return task
    return re.split(r"[:;(]", work, maxsplit=1)[0].strip().rstrip(".") or work


# --- the remake's plan: the runner's milestones, only shown ------------------------------------------------------

def plan_code(work):
    """([{task, gaps}], [owner's lines]) of a milestone's code work lines ([{work, gaps}]): each folded into its
    task (work_task), the most gaps first; the owner's own actions (owners_own) apart, never code."""
    tasks, owners = {}, []
    for entry in work:
        if owners_own(entry["work"]):
            owners.append(entry["work"])
        else:
            task = work_task(entry["work"])
            tasks[task] = tasks.get(task, 0) + entry["gaps"]
    return ([{"task": task, "gaps": gaps} for task, gaps in sorted(tasks.items(), key=lambda pair: -pair[1])],
            owners)


def plan_step(entry, titles, running):
    """One milestone of the runner's plan for the page: its stages in words, its measured euros and the running
    subtotal (`running`, {likely, high} before it), the set budgets apart, the unknown steps with why, the code work
    folded into tasks, the route rows no row of the table does yet, the owner's steps and the earlier milestones it
    reads; the record's words, never new ones."""
    code, owners = plan_code(entry.get("work", []))
    likely, high = entry.get("likely_euros") or 0.0, entry.get("high_euros") or 0.0
    after = entry.get("after_work") or {}
    return {"title": entry["title"], "unpriced": entry.get("unpriced"),
            "stages": [{"label": label(stage["stage"]), "nodes": stage["nodes"], "paid": stage["paid"]}
                       for stage in entry.get("stages", [])],
            "nodes": entry.get("nodes", 0), "paid": len(entry.get("paid", [])),
            "measured": entry.get("measured", 0), "likely": likely, "high": high,
            "subtotal": {"likely": round(running["likely"] + likely, 2), "high": round(running["high"] + high, 2)},
            "set": entry.get("set") or {"euros": 0, "nodes": 0, "from": []}, "unknown": entry.get("unknown", []),
            "after": after if after.get("nodes") else None, "code": code,
            "missing": [label(stage) for stage in entry.get("missing", [])],
            "owner": [*entry.get("owner", []), *owners],
            "reads": [titles.get(key, key) for key in entry.get("reads", [])]}


def eta_of(eta):
    """{known, likely, high, at_least, unknown, why} of the runner's ETA (`eta`, the record's: gaps/schedule.py) in
    words: its range only when every row has measured minutes, else unknown with why (the rows without them, the
    walk with them as no time a floor); None-safe for a record made before the runner had one."""
    if eta is None:
        return {"known": False, "why": "this price record holds no ETA: run score price --gaps again"}
    untimed = eta.get("unknown") or []
    if eta.get("likely_minutes") is None or untimed:
        return {"known": False, "at_least": hours(eta.get("at_least_minutes")), "unknown": len(untimed),
                "why": f"{len(untimed)} step{'s' if len(untimed) != 1 else ''} with no measured run time",
                "steps": untimed}
    return {"known": True, "likely": hours(eta["likely_minutes"]), "high": hours(eta["high_minutes"]),
            "jobs": eta.get("jobs"), "run_cap": eta.get("run_cap")}


def plan_of(price):
    """{steps, total} of the runner's milestones (`price.milestones`, gaps/milestones.py), in its order, each with
    its running subtotal, and the whole: measured likely and high, the set budgets apart, the paid steps with no
    measured price, what is priced after code work, the runner's ETA (eta_of); None with no current record or one
    without milestones (said_of_price says why). Nothing is priced, ordered or judged here."""
    if price is None or price.stale or not price.milestones:
        return None
    titles = {entry["key"]: entry["title"] for entry in price.milestones}
    steps, running = [], {"likely": 0.0, "high": 0.0}
    for entry in price.milestones:
        step = plan_step(entry, titles, running)
        running = step["subtotal"]
        steps.append(step)
    after = [step["after"] for step in steps if step["after"]]
    return {"steps": steps, "eta": eta_of(price.eta),
            "total": {"likely": running["likely"], "high": running["high"],
                      "measured": sum(step["measured"] for step in steps), "paid": sum(step["paid"] for step in steps),
                      "set": round(sum(step["set"]["euros"] for step in steps), 2),
                      "set_nodes": sum(step["set"]["nodes"] for step in steps),
                      "unknown": sum(len(step["unknown"]) for step in steps),
                      "after_likely": round(sum(entry["likely_euros"] for entry in after), 2),
                      "after_high": round(sum(entry["high_euros"] for entry in after), 2),
                      "after_unknown": sum(entry["unknown"] for entry in after),
                      "after_counts": sorted({count for entry in after for count in entry.get("counts", [])})}}
