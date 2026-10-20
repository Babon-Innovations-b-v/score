"""The remake's plan in milestones, worked out by the runner from the holes record and the stage table, never written
by hand: every node of the record's chains and lines (price.py) ordered by a dependency sort of the rows' reads,
shapes first (CONTEXT.md "shapes first"), the stage table's order only breaking ties, then grouped by the step of the
route each node is at. The cockpit only shows the list.

    found = milestones.milestones(runner, record, found, lost, books)   # [milestone], the last one the owner's

A node's step, first match:
    ground    its stage is GROUND's (the environment's ground)
    shapes    its stage is SHAPES' (concept, plan and its record, rough model) and no shell split comes before it
    split     its stage is SPLIT's (a shell's plan split into inside places)
    inside    its stage is SHAPES' and a shell split comes before it (an inside place's own concept, plan, rough model)
    complete  its stage is the completion gate (fill.COMPLETE)
    after     it reads a completion gate, directly or through others, or no node of the remake reads it (a line's
              end): the films, the showcase renders, the hand-over
    made      the rest: what each place holds (props, finishes, light, sound, people, its layers)
A route stage the table does not have yet makes no node; its holes' code work names it.

A milestone:

    {"key", "title", "stages": [{"stage", "nodes", "paid"}], "nodes", "places", "paid": [nodes],
     "likely_euros", "high_euros", "measured",                (the paid nodes with a measured price, summed)
     "set": {"euros", "nodes", "from": [{"at", "euros", "nodes"}]},  (the stage table's set budgets of the paid
                                       nodes with no measured price: set, never measured, never in the sums)
     "unknown": [{"node", "why"}],     (each paid node with no measured price, with its reason)
     "after_work": {"likely_euros", "high_euros", "unknown", "nodes"},  (what the record prices after code work
                                       whose holes wait at this step: the prop route, the Pixal3D code work)
     "work": [{"work", "holes"}],       (the holes' code work no stage does yet that waits at this step, raw lines;
                                       the cockpit folds them into its tasks and the owner's own)
     "owner": [words],                 (the owner's steps: the month's books before the first paid step)
     "reads": [keys of the earlier milestones its nodes read]}

then {"key": "environment-film", ...} (no row of the table makes it: unpriced, with why) and {"key": "approval",
"owner": [...]}: the owner approves the final video, the last step.
"""
import heapq

from score.graph import chain, node_name
from score.stages.complete.holes import fill, inputs

GROUND = ("terrain",)
SHAPES = ("concept-views", "plan", "scene-record", fill.ROUGH_MODEL)
SPLIT = ("shell-split",)
STEPS = (("ground", "The ground"),
         ("shapes", "Shapes first: concept, plan and rough model"),
         ("split", "Shells split into inside places"),
         ("inside", "Each inside place's concept, plan and rough model"),
         ("made", "What each place holds: props, finishes, light, sound, people, layers"),
         ("complete", "Each place's completion gate"),
         ("after", "Films, showcase renders and the hand-over"))
RANK = {key: rank for rank, (key, _) in enumerate(STEPS)}
MEASURED = ("measured runs", "per unit × counted", "per unit × forecast")
ENVIRONMENT_FILM = ("no row of the stage table cuts the environment's film from its places' films (the world video "
                    "is cut outside the runner today), so the runner cannot price or time it")
APPROVAL = "you approve the final video: nothing is accepted by hand, and the remake is done only then"


def remake_nodes(record):
    """Every node of the record's hole chains and line chains, each once."""
    return ({node for at in record["chains"].values() for nodes in at.values() for node in nodes}
            | {node for nodes in record["lines"].values() for node in nodes})


def read_edges(runner, names):
    """{node: [the nodes of `names` it reads]} (chain.reads: optional reads too); a node of a table of its own (the
    ship kits') reads none of this table's."""
    return {name: [node_name(*before) for before in chain.reads(runner, *next(runner.nodes_named([name])))
                   if node_name(*before) in names] if stage_of(name) in runner.stages else [] for name in names}


def reaching(edges, wanted):
    """{node: whether it reads a node `wanted` says yes to, directly or through others}."""
    found = {}

    def reaches(name):
        if name not in found:
            found[name] = False  # the table refuses a cycle; this only guards the walk
            found[name] = any(wanted(before) or reaches(before) for before in edges[name])
        return found[name]

    for name in edges:
        reaches(name)
    return found


def stage_of(name):
    return name.partition("@")[0]


def step_of(name, after_split, after_complete):
    """A node's step of the route (the module docstring); `after_complete` whether it reads a completion gate or ends
    its line."""
    stage = stage_of(name)
    if stage in GROUND:
        return "ground"
    if stage in SPLIT:
        return "split"
    if stage in SHAPES:
        return "inside" if after_split else "shapes"
    if stage == fill.COMPLETE:
        return "complete"
    return "after" if after_complete else "made"


def steps_of(edges):
    """{node: its step} of every node of `edges`."""
    after_split = reaching(edges, lambda name: stage_of(name) in SPLIT)
    after_complete = reaching(edges, lambda name: stage_of(name) == fill.COMPLETE)
    read = {before for reads in edges.values() for before in reads}
    return {name: step_of(name, after_split[name], after_complete[name] or name not in read) for name in edges}


def ordered(runner, edges, steps):
    """The nodes in dependency order (each after every node it reads), the earlier step of the route first, then the
    stage table's order, then the place: a sort, never an opinion."""
    order = {name: index for index, name in enumerate(runner.stages)}
    key = {name: (RANK[steps[name]], order.get(stage_of(name), len(order)), name) for name in edges}
    waiting = {name: len(set(reads)) for name, reads in edges.items()}
    readers = {}
    for name, reads in edges.items():
        for before in set(reads):
            readers.setdefault(before, []).append(name)
    ready = [key[name] for name, count in waiting.items() if count == 0]
    heapq.heapify(ready)
    found = []
    while ready:
        name = heapq.heappop(ready)[2]
        found.append(name)
        for later in readers.get(name, ()):
            waiting[later] -= 1
            if waiting[later] == 0:
                heapq.heappush(ready, key[later])
    return found


def unknown_why(node, price):
    """Why a paid node has no measured price, in words."""
    stage = stage_of(node)
    if price is None:
        return "not priced in this record"
    if price["basis"] == "not measured yet":
        return f"not measured yet: no run of {stage} in the cloud ledger and no per-unit price for it"
    return f"{price['basis']}: no measured price for {stage}"


def set_budgets(rows, nodes):
    """{euros, nodes, from} of the stage table's set budgets (Stage.euros, where its row names it; `rows` {stage:
    row}, the tables of their own too) of `nodes`: set, never measured."""
    sources = {}
    for node in nodes:
        row = rows[stage_of(node)]
        if row.euros:
            entry = sources.setdefault(row.euros_from or "not said", {"euros": 0.0, "nodes": 0})
            entry["euros"], entry["nodes"] = entry["euros"] + float(row.euros), entry["nodes"] + 1
    return {"euros": round(sum(entry["euros"] for entry in sources.values()), 2),
            "nodes": sum(entry["nodes"] for entry in sources.values()),
            "from": [{"at": at, "euros": round(entry["euros"], 2), "nodes": entry["nodes"]}
                     for at, entry in sorted(sources.items(), key=lambda pair: -pair[1]["euros"])]}


def priced(prices):
    """{likely_euros, high_euros, measured, unknown} of prices ({name: price}): the measured ones summed, the
    others named."""
    found = [price for price in prices.values() if price["basis"] in MEASURED and price["likely_euros"] is not None]
    return {"likely_euros": round(sum(price["likely_euros"] for price in found), 2),
            "high_euros": round(sum(price["high_euros"] for price in found), 2), "measured": len(found),
            "unknown": sorted(name for name, price in prices.items()
                              if price["basis"] not in MEASURED or price["likely_euros"] is None)}


def stage_rows(names, paid):
    """[{stage, nodes, paid}] of nodes in their order, a stage once, at its first node."""
    found = {}
    for name in names:
        entry = found.setdefault(stage_of(name), {"stage": stage_of(name), "nodes": 0, "paid": 0})
        entry["nodes"] += 1
        entry["paid"] += name in paid
    return list(found.values())


def work_step(hole, readers, steps):
    """The step of the route a hole no stage fills waits at: a lost input's at its earliest reader's (`readers`,
    lost_readers), a route step's at that step's stage, anything else at made."""
    if inputs.is_lost(hole["id"]):
        found = [steps[node] for node in readers.get(hole["id"], ()) if node in steps]
        return min(found, key=RANK.get) if found else "made"
    if hole["rule"] == "place":
        kind = hole["id"].partition(":")[2]
        stage = (fill.FILLERS.get(kind) or (None,))[0] or kind
        return step_of(stage, False, False)
    return "made"


def work_by_step(found, readers, steps):
    """{step: {work line: holes}} of every hole no stage fills (`found`, {place: holes}), a lost input once."""
    every = inputs.distinct([hole for listed in found.values() for hole in listed])
    by_step = {}
    for hole in every:
        if hole.get("node") is None and hole.get("work"):
            lines = by_step.setdefault(work_step(hole, readers, steps), {})
            lines[hole["work"]] = lines.get(hole["work"], 0) + 1
    return by_step


def after_work_by_step(record, work):
    """{step: {name: price}} of what the record prices after code work (its after_work and code_work), each at the
    step its work line waits at (`work`, work_by_step's)."""
    step_of_line = {line: step for step, lines in work.items() for line in lines}
    found = {}
    entries = [(entry["work"], entry["nodes"]) for entry in record["after_work"].values()]
    entries += [(line, entry["nodes"]) for line, entry in record["code_work"].items()]
    for line, nodes in entries:
        found.setdefault(step_of_line.get(line, "made"), {}).update(nodes)
    return found


def milestone(rows, key, names, record, extra):
    """One milestone of the route (the module docstring) of its nodes in order; `extra` its work, after-work prices
    and owner steps."""
    paid = [name for name in names if name in record["nodes"]]
    sums = priced({name: record["nodes"][name] for name in paid})
    after = priced(extra["after"])
    return {"key": key, "title": dict(STEPS)[key], "stages": stage_rows(names, set(paid)), "nodes": len(names),
            "places": len({name.partition("@")[2] for name in names if "@" in name}), "paid": paid,
            "likely_euros": sums["likely_euros"], "high_euros": sums["high_euros"], "measured": sums["measured"],
            "set": set_budgets(rows, sums["unknown"]),
            "unknown": [{"node": name, "why": unknown_why(name, record["nodes"].get(name))} for name in sums["unknown"]],
            "after_work": {"likely_euros": after["likely_euros"], "high_euros": after["high_euros"],
                           "unknown": len(after["unknown"]), "nodes": len(extra["after"])},
            "work": [{"work": line, "holes": holes} for line, holes in sorted(extra["work"].items(),
                                                                              key=lambda pair: -pair[1])],
            "owner": extra["owner"], "reads": extra["reads"]}


def milestones(runner, rows, record, found, readers, books):
    """[milestone] of the remake: each step of the route with nodes or code work, in the route's order, then the
    environment's film and the owner's approval. `rows` {stage: row} of the table and the tables of their own,
    `found` the places' current holes ({place: holes}), `readers` lost_readers' {lost hole id: reader nodes},
    `books` why paid work is refused now (None when it is not)."""
    edges = read_edges(runner, remake_nodes(record))
    steps = steps_of(edges)
    order = ordered(runner, edges, steps)
    work = work_by_step(found, readers, steps)
    after = after_work_by_step(record, work)
    first_paid = next((steps[name] for name in order if name in record["nodes"]), None)
    found_steps = []
    for key, _ in STEPS:
        names = [name for name in order if steps[name] == key]
        if not names and not work.get(key):
            continue
        reads = sorted({steps[before] for name in names for before in edges[name]} - {key}, key=RANK.get)
        owner = [f"the month's books before any paid step: {books}"] if books and key == first_paid else []
        found_steps.append(milestone(rows, key, names, record, {"work": work.get(key, {}),
                                                                   "after": after.get(key, {}), "owner": owner,
                                                                   "reads": reads}))
    return found_steps + [{"key": "environment-film", "title": "The environment's film", "unpriced": ENVIRONMENT_FILM,
                           "owner": []},
                          {"key": "approval", "title": "Your approval of the final video", "owner": [APPROVAL]}]
