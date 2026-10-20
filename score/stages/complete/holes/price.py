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
     "totals": {likely_euros, high_euros, unpriced, nodes},
     "unfillable": [{"work", "holes"}],               (holes no stage fills: their code work and how many need it)
     "after_work": {place: {"work", "holes", "models", "nodes": {node: price}, "in_chains": [nodes]}},
                     (the prop route of the place's missing rows that wait on its prop data, priced as if the data
                      were written: each paid row of the route once a place, per model where its stage has a rule;
                      a row whose node is in a chain already is counted there, not again)
     "code_work": {work: {"holes", "models", "nodes": {label: price}}},
                     (the code work whose make is a Pixal3D one, priced at pixal's per unit as if it had landed: the
                      lost takes a model each)
     "outside": [{"node", "holes"}],                  (a node outside this runner's table and every own table)
     "eta": {jobs, run_cap, likely_minutes, high_minutes, at_least_minutes, path, high_path, unknown},
                     (the runner's ETA of every chain's and after-work row, schedule.py on measured minutes: likely
                      and high null while any row is untimed, at_least the walk with those as no time)
     "not_current": [places whose findings stood over an output no longer accepted: run the holes check again],
     "not_checked": [places (and WORLD) with no findings: the holes check never ran there],
     "lines": {place (and WORLD): [every node its line still needs to run to its end: chain.line_chain]},
                     (the remake: past each place's completion to its line's ends, the films and the hand-over, and
                      the environment's own nodes, people too; their paid nodes are priced in "nodes" and the totals)
     "milestones": [milestones.py's milestones: the remake's plan, shapes first, the owner's approval last]}

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
import re

from score import graph
from score.adapters import compute
from score.graph import chain
from score.stages.complete.holes import FINDINGS, PLACE, WORLD, fill, inputs, milestones, schedule

MISSING = "missing"
# The code work whose make, once it lands, is Pixal3D's, a model a hole: (its work line's pattern, its label), priced
# at pixal's measured per unit after that work (code_work).
PIXAL_WORK = ((r"^Pixal3D take lost", "pixal: the lost Pixal3D takes made again"),)
ROUTE_END = "likeness"  # the prop route's last row (score/stages/props): a model's route runs up to its likeness gate
# The provider's bill over the cloud ledger's sum for 2026-10 up to 2026-10-10 (EUR 627.74 against 547.31: disks,
# addresses, storage and registry the ledger misses; paper/evidence/cloud/cost-tables-2026-10.txt): what a card or
# processor layer's ledger euros come to on the bill (prepare's batch estimate; prop_batch.py prices its card steps
# with the same figure).
BILL_SHARE = 627.74 / 547.31


def own_tables():
    """{stage name: its row} of the tables of their own a hole's node may name (fill.SHIP_KIT: the ship kits')."""
    from score.stages import ship_kits
    return {fill.SHIP_KIT: ship_kits.STAGE}


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
    """The light passes' render jobs a place's make sends (passes.pass_jobs: its scene record's views, VIEWS_A_JOB a
    job), or None while its views are not known (a place whose record the scene-record row has still to write)."""
    from score.stages.light import passes
    scene = passes.REPO / f"data/scene/{place}.json"
    if not scene.is_file():
        return None
    return math.ceil(len(passes.scene_of(place).get("views") or []) / passes.VIEWS_A_JOB)


def sound_takes(data, place):
    """The MOSS takes the place's sound make is counted for: the environment's takes still to make, each once, at the
    first place that plays it (sound.environment_takes, #29)."""
    from score.stages import sound
    return sum(1 for _, places in sound.environment_takes(data, sound.moss_weights()).values() if places[0] == place)


def rule_units(rule, found, data, place):
    """The units a forecast rule counts at a place (PER_UNIT's `forecast` rule), before any per-model factor."""
    if rule == "one":
        return 1
    if not place:
        return None  # the other rules count a place's own models or views
    if rule == "prop_takes":
        return len(pixal_models(found, data, place))
    if rule == "models":
        return len(surface_takes(data, place) | pixal_models(found, data, place))
    if rule == "light_jobs":
        return light_jobs(place)
    if rule == "sound_takes":
        return sound_takes(data, place)
    raise ValueError(f"unknown forecast rule {rule!r} in {compute.PER_UNIT}")


def forecast_units(node, found, data):
    """The units a make of the node is forecast to make by its stage's rule (PER_UNIT's `forecast`, times its
    `per_model` where a model makes more than one unit), or None when its stage has no rule (an `also` stage has none
    of its own) or nothing is counted; `found` are the place's holes."""
    stage, _, place = node.partition("@")
    entry = compute.per_unit(stage)
    if entry is None or entry["stage"] != stage or not entry.get("forecast"):
        return None
    units = rule_units(entry["forecast"]["rule"], found, data, place)
    return round(units * entry["forecast"].get("per_model", 1), 2) if units else None


def node_price(node, found, data, store):
    """One paid node at compute.run_price with its forecast units, and the units and their source; with no measured
    price it is unknown, its stage's own estimate left out (a flat guess is no price, the owner 2026-10-20)."""
    units = forecast_units(node, found, data)
    price = compute.run_price(node, None, store, units=units)
    return {**price, "units": price.get("units", units)}


def totals(prices):
    """{likely_euros, high_euros, unpriced, nodes} of the priced nodes: likely and high the measured ones' sums,
    unpriced the nodes with no measured price (unknown, never a guess)."""
    priced = [price for price in prices.values() if price["likely_euros"] is not None]
    return {"likely_euros": round(sum(price["likely_euros"] for price in priced), 2),
            "high_euros": round(sum(price["high_euros"] for price in priced), 2),
            "unpriced": sorted(node for node, price in prices.items() if price["likely_euros"] is None),
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
    outside: {node outside every table: holes},
    route: {place: {"work", "holes", "rows"}}} of the places' holes (`found`), each lost input once."""
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


def route_units(stage, models):
    """The units a prop route row makes for `models` models by its stage's forecast rule: one for a once-a-place rule,
    else the models times the rule's `per_model`."""
    entry = compute.per_unit(stage)
    rule = (entry or {}).get("forecast") or {}
    return 1 if rule.get("rule") == "one" else round(models * rule.get("per_model", 1), 2)


def after_work(runner, route, priced, store):
    """{place: {work, holes, models, nodes, in_chains}} of the places whose missing rows wait on their prop data
    (`route`, chained's): each paid row of the prop route at compute.run_price with the rows as its forecast units,
    one model a row (route_units); a row with no forecast rule whose node is in a chain already (`priced`) is left
    to the chain."""
    found = {}
    for place, waiting in sorted(route.items()):
        models, nodes, in_chains = len(waiting["rows"]), {}, []
        for name in route_stages(runner):
            node = f"{name}@{place}"
            price = compute.run_price(node, None, store, units=route_units(name, models))
            if price["basis"] != "per unit × forecast" and node in priced:
                in_chains.append(node)
            else:
                nodes[node] = {**price, "units": price.get("units")}
        found[place] = {"work": waiting["work"], "holes": waiting["holes"], "models": models, "nodes": nodes,
                        "in_chains": in_chains}
    return found


def code_work(work):
    """{work: {holes, models, nodes: {label: price}}} of the code work whose make is a Pixal3D one (PIXAL_WORK), each
    line once: a lost take one model, at compute.run_price with pixal's forecast per unit
    (unknown while pixal has no measured unit)."""
    found = {}
    for line, holes in work.items():
        for pattern, label in PIXAL_WORK:
            if re.search(pattern, line):
                price = compute.run_price("pixal", None, units=holes)
                if price["basis"] == "per unit × forecast":
                    price["unit_source"] = "one Pixal3D model a hole of this work line"
                found[line] = {"holes": holes, "models": holes, "nodes": {label: {**price, "units": holes}}}
    return found


def run_cap():
    """The most cards one run holds at once (tools/props/cloud/capacity.py run_cap), as the runner sizes its runs."""
    compute.ledger()  # puts tools/props/cloud on the path
    import capacity  # beside ledger.py
    return capacity.run_cap()


def plan_rows(runner, every, places):
    """[node] of the plan's rows (`every`, {node: whether paid}) in the stage table's order (runner.nodes, the walk's
    tie-break), a row of a table of its own (own_tables) after them."""
    order = [graph.node_name(*node) for node in runner.nodes(places)]
    return [node for node in order if node in every] + sorted(node for node in every if node not in order)


def plan_edges(runner, rows):
    """[(before, after)] of the plan's rows: each row of the stage table after every row of the plan it reads."""
    wanted = set(rows)
    edges = []
    for node in rows:
        if node.partition("@")[0] not in runner.stages:
            continue
        stage, place = next(runner.nodes_named([node]))
        edges.extend((name, node) for name in (graph.node_name(*before) for before in runner.read_nodes(stage, place))
                     if name in wanted)
    return edges


def plan_eta(runner, every, prices, places):
    """The plan's ETA (schedule.schedule) over its rows `every` ({node: whether paid}) with their `prices`, at most
    graph.JOBS rows at once (the runner's default drive) and run_cap() cards held: {jobs, run_cap, likely_minutes,
    high_minutes, at_least_minutes, path, high_path, unknown}."""
    rows, made, cap = plan_rows(runner, every, places), compute.node_minutes(), run_cap()
    nodes = {node: schedule.timed_row(node, every[node], prices.get(node), made) for node in rows}
    return {"jobs": graph.JOBS, "run_cap": cap, **schedule.schedule(nodes, plan_edges(runner, rows), graph.JOBS, cap)}


def priced_on():
    """{commit, uncommitted, per_unit_sha256}: the code and the per-unit prices a record is made on, so the cockpit
    can tell an old record from a current one."""
    from score.graph import runs
    return {"commit": runs.commit_of(runs.REPO), "uncommitted": runs.tracked_changes(),
            "per_unit_sha256": hashlib.sha256(compute.PER_UNIT.read_bytes()).hexdigest()}


def line_chains(runner, places, reading):
    """{place (and WORLD): {node: whether paid}} of every place's line to its ends and the environment's own
    (chain.line_chain); a line with nothing left to run left out."""
    found = {place: chain.line_chain(runner, place, reading) for place in places}
    found[WORLD] = chain.line_chain(runner, None, reading)
    return {place: nodes for place, nodes in found.items() if nodes}


def lost_readers(runner, places):
    """{lost input hole id: the nodes that read it} of every place's line and the environment's own (inputs.py's
    declared files; the owner's pictures read by the concept views' node), so a milestone knows where it waits."""
    found, concept = {}, fill.FILLERS[fill.CONCEPT][0]
    for place in [*places, None]:
        for (kind, item), entry in inputs.declared_lost(runner, place).items():
            found.setdefault(f"{PLACE}:{inputs.lost_id(kind, item)}", set()).update(entry["nodes"])
        for path in (inputs.lost_pictures(runner, place) if place and concept in runner.stages else {}):
            found.setdefault(f"{PLACE}:{inputs.lost_id(inputs.PICTURE, pathlib.Path(path).name)}", set()).add(
                fill.node_of(concept, place))
    return found


def books_refused():
    """Why paid work is refused now (the month's books not known), or None."""
    return compute.ledger().books_refusal()


def holes_price(runner, world, root, places, store=None, made_at=None):
    """The holes record (this module's docstring) of every place's holes check under `root` and the environment's
    own (WORLD), priced on `store`, with every place's line to its end and the remake's milestones."""
    with runner.still():
        found, stale, unchecked = read_places(runner, root, [*places, WORLD])
        record = chained(runner, found, places)
        reading = chain.readers(runner, places)
        lines = line_chains(runner, places, reading)
        every = {name: is_paid for at in record["chains"].values() for nodes in at.values()
                 for name, is_paid in nodes.items()}
        every.update({name: is_paid for nodes in lines.values() for name, is_paid in nodes.items()})
        prices = {node: node_price(node, found.get(node.partition("@")[2], []), runner.world.roots["data"], store)
                  for node in sorted(name for name, is_paid in every.items() if is_paid)}
        route = after_work(runner, record["route"], prices, store)
        routed = {node: price for entry in route.values() for node, price in entry["nodes"].items()}
        eta = plan_eta(runner, {**every, **dict.fromkeys(routed, True)}, {**prices, **routed}, places)
        priced = {"world": world, "made_at": made_at or graph.now(), "priced_on": priced_on(), "nodes": prices,
                  "chains": {place: {node: sorted(nodes) for node, nodes in at.items()}
                             for place, at in record["chains"].items()},
                  "holes": record["holes"], "free": sorted(name for name, is_paid in every.items() if not is_paid),
                  "totals": totals(prices),
                  "unfillable": counted(({"work": text}, count) for text, count in record["work"].items()),
                  "after_work": route, "code_work": code_work(record["work"]),
                  "outside": counted(({"node": node}, count) for node, count in record["outside"].items()),
                  "eta": eta, "not_current": stale, "not_checked": unchecked,
                  "lines": {place: sorted(nodes) for place, nodes in lines.items()}}
        priced["milestones"] = milestones.milestones(runner, {**runner.stages, **own_tables()}, priced, found,
                                                     lost_readers(runner, places), books_refused())
    return priced
