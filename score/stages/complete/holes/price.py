"""The holes priced by the runner: every hole's chain (score/graph/chain.py), each paid node in any chain priced once
by compute.run_price on the runner's own numbers, with the units its stage's forecast rule counts before the make
(PER_UNIT's `forecast`, over every hole at the place that needs it, each model once). The cockpit reads the record and
only sums it; nothing here buys, keys or judges anything. Free and local.

    .venv/bin/python -m score price world1 --holes --json      # writes WORK/checks/holes-price/world1.json

The record:

    {"world", "made_at",
     "priced_on": {commit, uncommitted, per_unit_sha256},  (the code and per-unit prices it was made on)
     "nodes": {node: run_price's price + "units" (the forecast's count, or null) + "unit_source"},  (paid nodes)
     "chains": {place: {node: [every node in the chain of the place's holes that node fills, paid and free]}},
     "holes": {place: {hole id: its node}},          (holes with a node in the stage table, at a current findings)
     "free": [the free nodes in any chain],
     "totals": {likely_euros, high_euros, guessed_euros, guessed, unpriced, nodes},
     "unfillable": [{"work", "holes"}],               (holes no stage fills: their code work and how many need it)
     "after_work": {place: {"work", "holes", "models", "nodes": {node: price}, "in_chains": [nodes]}},
                     (the prop route of the place's missing rows that wait on its prop data, priced as if the data
                      were written: each paid row of the route once a place, per model where its stage has a rule;
                      a row whose node is in a chain already is counted there, not again)
     "outside": [{"node", "holes"}],                  (a node outside this runner's table and every own table)
     "not_current": [places whose findings stood over an output no longer accepted: run the holes check again],
     "not_checked": [places (and WORLD) with no findings: the holes check never ran there]}

A node is priced once, however many holes share it. A Blocked node or a missing input is something to make, so it is
in the chain and priced; nothing is skipped. A lost input read by several places (its id names the thing) counts
once. A count of 0 or a rule whose source is missing is no count (a guess), never a free make. A node of a table of
its own (OWN_TABLES: the ship kits', `ship_kit@<place>`) is priced the same way on its own row, its chain the node
alone: no row of this table reads it, so what the place's completion reads after it is in the place's other chains.
"""
import hashlib
import json
import math
import pathlib

from score import graph
from score.adapters import compute
from score.graph import chain
from score.stages.complete.holes import FINDINGS, WORLD, fill, inputs

MISSING = "missing"
ROUTE_END = "likeness"  # the prop route's last row (score/stages/props): a model's route runs up to its likeness gate


def own_tables():
    """{stage name: its row} of the tables of their own a hole's node may name (fill.SHIP_KIT: the ship kits')."""
    from score.stages import ship_kits
    return {fill.SHIP_KIT: ship_kits.STAGE}


def stage_of(runner, name):
    """A stage's row: the runner's table's, else a table of its own's, else None (a node outside every table)."""
    return runner.stages.get(name) or own_tables().get(name)


def findings_of(root, place):
    """A place's holes check record, or None before it ran."""
    path = pathlib.Path(root) / place / FINDINGS
    return json.loads(path.read_text()) if path.is_file() else None


def current(written, store):
    """Whether every output a findings record stood over is still the accepted one."""
    return all(store.accepted(node) == output for node, output in written.get("outputs", {}).items())


def prop_objects(data, place):
    """{row: entry} of the place's prop objects (data/props/<place>.json); none without the file."""
    from score.stages.props import prop_data
    path = pathlib.Path(data) / "props" / f"{place}.json"
    return prop_data.prop_objects(prop_data.record_at(path)) if path.is_file() else {}


def take_of(objects, hole):
    """The model a missing row's hole asks for: its prop object's take, else its row (else its id)."""
    row = hole.get("row") or hole["id"]
    return (objects.get(row) or {}).get("take") or row


def pixal_models(found, data, place):
    """The models pixal is forecast to make at the place, each once (PER_UNIT's prop_takes): its prop objects' takes
    not made in WORK/pixal (pixal_row.made, as the make skips a made one), and the model of each missing row of
    `found` (the place's holes) whose node is pixal's there."""
    from score.stages.props import pixal_row
    objects = prop_objects(data, place)
    node = fill.node_of(fill.FILLERS[fill.ROUTE][0], place)
    unmade = {entry["take"] for entry in objects.values() if not pixal_row.made(entry["take"])}
    return unmade | {take_of(objects, hole) for hole in found if hole["rule"] == MISSING and hole.get("node") == node}


def surface_takes(data, place):
    """The takes the place's surface data lists (data/surfaces/<place>.json), by name."""
    path = pathlib.Path(data) / "surfaces" / f"{place}.json"
    return set(json.loads(path.read_text()).get("takes") or {}) if path.is_file() else set()


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
    if rule == "prop_takes":
        units = len(pixal_models(found, data, place))
    elif rule == "models":
        units = len(surface_takes(data, place) | pixal_models(found, data, place))
    elif rule == "light_jobs":
        units = light_jobs(place)
    elif rule == "one":
        units = 1
    else:
        raise ValueError(f"unknown forecast rule {rule!r} in {compute.PER_UNIT}")
    return units or None


def node_price(runner, node, found, data, store):
    """One paid node at compute.run_price with its forecast units, and the units and their source."""
    stage = stage_of(runner, node.partition("@")[0])
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
    """({place: its holes}, [places not current], [places with no findings]) of the places' holes checks."""
    found, stale, unchecked = {}, [], []
    for place in places:
        written = findings_of(root, place)
        if written is None:
            unchecked.append(place)
        elif current(written, runner.store):
            found[place] = written.get("findings", [])
        else:
            stale.append(place)
    return found, stale, unchecked


def node_chain(runner, node, place, places, reading):
    """{node: whether paid} of the chain of a hole whose node is `node`, found at `place`: a place node's at its
    own place; an environment node's at the place that found it, or at every place for the environment's own
    holes (WORLD)."""
    stage, _, at = node.partition("@")
    if at:
        return chain.hole_chain(runner, runner.stages[stage], at, reading)
    found = {}
    for each in places if place == WORLD else [place]:
        found.update(chain.hole_chain(runner, runner.stages[stage], each, reading))
    return found


def waits_on_prop_data(hole, place):
    """Whether a hole is a missing row whose prop route waits only on the place's prop data (fill.FILLERS' route)."""
    return hole["rule"] == MISSING and hole.get("work") == fill.FILLERS[fill.ROUTE][1].format(place=place)


def chained(runner, found, places):
    """{chains: {place: {node: its hole chain}}, holes: {place: {hole id: node}}, work: {work: holes},
    outside: {node outside every table: holes}, route: {place: {"work", "holes", "rows"}}} of the places' holes
    (`found`), each lost input once."""
    reading = chain.readers(runner, places)
    record = {"chains": {}, "holes": {}, "work": {}, "outside": {}, "route": {}}
    for hole in inputs.distinct([{**hole, "place": place} for place, listed in found.items() for hole in listed]):
        place, node = hole["place"], hole.get("node")
        if node is None:
            record["work"][hole["work"]] = record["work"].get(hole["work"], 0) + 1
            if waits_on_prop_data(hole, place):
                route = record["route"].setdefault(place, {"work": hole["work"], "holes": 0, "rows": set()})
                route["holes"] += 1
                route["rows"].add(hole.get("row") or hole["id"])
        elif node.partition("@")[0] in runner.stages:
            record["holes"].setdefault(place, {})[hole["id"]] = node
            at = record["chains"].setdefault(place, {})
            if node not in at:
                at[node] = node_chain(runner, node, place, places, reading)
        elif node.partition("@")[0] in own_tables():
            record["holes"].setdefault(place, {})[hole["id"]] = node
            record["chains"].setdefault(place, {})[node] = {node: bool(own_tables()[node.partition("@")[0]].paid)}
        else:
            record["outside"][node] = record["outside"].get(node, 0) + 1
    return record


def route_stages(runner):
    """The paid stages of the prop route, in table order: its last row (ROUTE_END) and every stage it reads,
    directly or through others."""
    wanted, todo = set(), [ROUTE_END]
    while todo:
        name = todo.pop()
        if name in runner.stages and name not in wanted:
            wanted.add(name)
            todo.extend(runner.stages[name].after)
    return [name for name in runner.stages if name in wanted and runner.stages[name].paid]


def after_work(runner, route, priced, store):
    """{place: {work, holes, models, nodes, in_chains}} of the places whose missing rows wait on their prop data
    (`route`, chained's): each paid row of the prop route at compute.run_price with the rows as its forecast units,
    one model a row; a row with no forecast rule whose node is in a chain already (`priced`) is left to the chain."""
    found = {}
    for place, waiting in sorted(route.items()):
        models, nodes, in_chains = len(waiting["rows"]), {}, []
        for name in route_stages(runner):
            node, stage = f"{name}@{place}", runner.stages[name]
            price = compute.run_price(node, stage.euros, store, units=models, guess_from=stage.euros_from)
            if price["basis"] != "per unit × forecast" and node in priced:
                in_chains.append(node)
            else:
                nodes[node] = {**price, "units": price.get("units")}
        found[place] = {"work": waiting["work"], "holes": waiting["holes"], "models": models, "nodes": nodes,
                        "in_chains": in_chains}
    return found


def priced_on():
    """{commit, uncommitted, per_unit_sha256}: the code and the per-unit prices a record is made on, so the cockpit
    can tell an old record from a current one."""
    from score.graph import runs
    return {"commit": runs.commit_of(runs.REPO), "uncommitted": runs.tracked_changes(),
            "per_unit_sha256": hashlib.sha256(compute.PER_UNIT.read_bytes()).hexdigest()}


def holes_price(runner, world, root, places, store=None, made_at=None):
    """The holes record (this module's docstring) of every place's holes check under `root` and the environment's
    own (WORLD), priced on `store`."""
    with runner.still():
        found, stale, unchecked = read_places(runner, root, [*places, WORLD])
        record = chained(runner, found, places)
        every = {name: is_paid for at in record["chains"].values() for nodes in at.values()
                 for name, is_paid in nodes.items()}
        prices = {node: node_price(runner, node, found.get(node.partition("@")[2], []), runner.world.roots["data"],
                                   store) for node in sorted(name for name, is_paid in every.items() if is_paid)}
        route = after_work(runner, record["route"], prices, store)
    return {"world": world, "made_at": made_at or graph.now(), "priced_on": priced_on(), "nodes": prices,
            "chains": {place: {node: sorted(nodes) for node, nodes in at.items()}
                       for place, at in record["chains"].items()},
            "holes": record["holes"], "free": sorted(name for name, is_paid in every.items() if not is_paid),
            "totals": totals(prices),
            "unfillable": counted(({"work": text}, count) for text, count in record["work"].items()),
            "after_work": route,
            "outside": counted(({"node": node}, count) for node, count in record["outside"].items()),
            "not_current": stale, "not_checked": unchecked}
