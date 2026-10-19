"""The holes priced by the runner: every hole's chain (score/graph/chain.py), each paid node in any chain priced once
by compute.run_price on the runner's own numbers, with the units its stage's forecast rule counts before the make
(PER_UNIT's `forecast`, summed over every hole at the place that needs it). The cockpit reads the record and only
sums it; nothing here buys, keys or judges anything. Free and local.

    .venv/bin/python -m score price world1 --holes --json      # writes WORK/checks/holes-price/world1.json

The record:

    {"world", "made_at",
     "nodes": {node: run_price's price + "units" (the forecast's count, or null) + "unit_source"},  (paid nodes)
     "chains": {place: {node: [every node in the chain of the place's holes that node fills, paid and free]}},
     "holes": {place: {hole id: its node}},          (holes with a node in the stage table, at a current findings)
     "free": [the free nodes in any chain],
     "totals": {likely_euros, high_euros, guessed_euros, guessed, unpriced, nodes},
     "unfillable": [{"work", "holes"}],               (holes no stage fills: their code work and how many need it)
     "outside": [{"node", "holes"}],                  (a node outside this runner's table: the ship kits')
     "not_current": [places whose findings stood over an output no longer accepted: run the holes check again]}

A node is priced once, however many holes share it. A Blocked node or a missing input is something to make, so it is
in the chain and priced; nothing is skipped. A count of 0 or a rule whose source is missing is no count (a guess),
never a free make.
"""
import json
import math
import pathlib

from score import graph
from score.adapters import compute
from score.graph import chain
from score.stages.complete.holes import fill

FINDINGS = "findings.json"
MISSING = "missing"


def findings_of(root, place):
    """A place's holes check record, or None before it ran."""
    path = pathlib.Path(root) / place / FINDINGS
    return json.loads(path.read_text()) if path.is_file() else None


def current(written, store):
    """Whether every output a findings record stood over is still the accepted one."""
    return all(store.accepted(node) == output for node, output in written.get("outputs", {}).items())


def missing_rows(found, node):
    """How many of a place's holes are missing rows the node makes."""
    return sum(1 for hole in found if hole["rule"] == MISSING and hole.get("node") == node)


def surface_takes(data, place):
    """How many takes the place's surface data lists (data/surfaces/<place>.json)."""
    path = pathlib.Path(data) / "surfaces" / f"{place}.json"
    return len(json.loads(path.read_text()).get("takes") or {}) if path.is_file() else 0


def light_jobs(place):
    """The light passes' render jobs a place's make sends (passes.pass_jobs), or None while a views file is
    missing."""
    from score.stages.light import passes
    jobs = 0
    for name in passes.shown(place):
        if not (passes.DEMO / f"views/{name}.json").is_file():
            return None
        jobs += math.ceil(len(passes.demo_views(name)[1]) / passes.VIEWS_A_JOB)
    return jobs


def forecast_units(node, found, data):
    """The units a make of the node is forecast to make by its stage's rule (PER_UNIT's `forecast`), or None when
    its stage has no rule (an `also` stage has none of its own) or nothing is counted; `found` are the place's
    holes."""
    stage, _, place = node.partition("@")
    entry = compute.per_unit(stage)
    if entry is None or entry["stage"] != stage or not entry.get("forecast") or not place:
        return None
    rule = entry["forecast"]["rule"]
    if rule == "missing_rows":
        units = missing_rows(found, node)
    elif rule == "models":
        units = surface_takes(data, place) + missing_rows(found, fill.node_of(fill.FILLERS[fill.ROUTE][0], place))
    elif rule == "light_jobs":
        units = light_jobs(place)
    elif rule == "one":
        units = 1
    else:
        raise ValueError(f"unknown forecast rule {rule!r} in {compute.PER_UNIT}")
    return units or None


def node_price(runner, node, found, data, store):
    """One paid node at compute.run_price with its forecast units, and the units and their source."""
    stage = runner.stages[node.partition("@")[0]]
    units = forecast_units(node, found, data)
    price = compute.run_price(node, stage.euros, store, units=units, guess_from=stage.euros_from)
    return {**price, "units": price.get("units", units)}


def totals(prices):
    """{likely_euros, high_euros, guessed_euros, guessed, unpriced, nodes} of the priced nodes: likely and high the
    priced ones' sums, guessed the stage estimates of those not priced (never in the price), unpriced the nodes with
    neither."""
    priced = [price for price in prices.values() if price["likely_euros"] is not None]
    guessed = [price for price in prices.values() if price["likely_euros"] is None and price.get("guess_euros")]
    return {"likely_euros": round(sum(price["likely_euros"] for price in priced), 2),
            "high_euros": round(sum(price["high_euros"] for price in priced), 2),
            "guessed_euros": round(sum(price["guess_euros"] for price in guessed), 2), "guessed": len(guessed),
            "unpriced": sorted(node for node, price in prices.items()
                               if price["likely_euros"] is None and not price.get("guess_euros")),
            "nodes": len(prices)}


def counted(pairs):
    """[{key: value, "holes": count}] of (value, count) pairs, most holes first."""
    return [{**value, "holes": count} for value, count in sorted(pairs, key=lambda pair: -pair[1])]


def read_places(runner, root, places):
    """({place: its holes}, [places not current]) of the places whose holes check ran."""
    found, stale = {}, []
    for place in places:
        written = findings_of(root, place)
        if written is None:
            continue
        if current(written, runner.store):
            found[place] = written.get("findings", [])
        else:
            stale.append(place)
    return found, stale


def chained(runner, found, places):
    """({place: {node: its hole chain}}, {place: {hole id: node}}, {work: holes}, {node outside the table: holes})
    of the places' holes (`found`)."""
    reading = chain.readers(runner, places)
    chains, holes, work, outside = {}, {}, {}, {}
    for place, listed in found.items():
        for hole in listed:
            node = hole.get("node")
            if node is None:
                work[hole["work"]] = work.get(hole["work"], 0) + 1
            elif node.partition("@")[0] not in runner.stages:
                outside[node] = outside.get(node, 0) + 1
            else:
                holes.setdefault(place, {})[hole["id"]] = node
                at = chains.setdefault(place, {})
                if node not in at:
                    at[node] = chain.hole_chain(runner, runner.stages[node.partition("@")[0]], place, reading)
    return chains, holes, work, outside


def holes_price(runner, world, root, places, store=None, made_at=None):
    """The holes record (this module's docstring) of every place's holes check under `root`, priced on `store`."""
    with runner.still():
        found, stale = read_places(runner, root, places)
        chains, holes, work, outside = chained(runner, found, places)
        every = {name: is_paid for at in chains.values() for nodes in at.values() for name, is_paid in nodes.items()}
        prices = {node: node_price(runner, node, found.get(node.partition("@")[2], []), runner.world.roots["data"],
                                   store) for node in sorted(name for name, is_paid in every.items() if is_paid)}
    return {"world": world, "made_at": made_at or graph.now(), "nodes": prices,
            "chains": {place: {node: sorted(nodes) for node, nodes in at.items()} for place, at in chains.items()},
            "holes": holes, "free": sorted(name for name, is_paid in every.items() if not is_paid),
            "totals": totals(prices),
            "unfillable": counted(({"work": text}, count) for text, count in work.items()),
            "outside": counted(({"node": node}, count) for node, count in outside.items()),
            "not_current": stale}
