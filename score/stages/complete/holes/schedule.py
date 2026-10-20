"""The runner's ETA for a plan: its rows walked in dependency order on their measured minutes, at most `jobs` rows
at once (paid and free, as the runner's drive) and never more than the run's cap of cards held. Free and local; it
buys, keys and judges nothing.

    nodes = {node: schedule.timed_row(node, paid, price)}         # in the stage table's order (the tie-break)
    eta = schedule.schedule(nodes, [(before, after), ...], jobs=4, run_cap=20)

A row's minutes are measured or absent, never guessed: a paid row's are compute.run_price's (its units on its stage's
measured time, by the runner's card rule), a free row's its stage's makes as the store's finish records time them
(`node_minutes` in data/costs/per-unit.json, score/graph/runs.py node_times). A row without minutes is listed with
why and counted as no time, so the walk gives only a lower bound (`at_least_minutes`); the range (likely, high) is
given only when every row of the plan has its minutes, as an untimed row anywhere could be the longest.
"""
import heapq
import json

from score.adapters import compute


def local_minutes(stage):
    """{likely_minutes, high_minutes} of a free row from its stage's measured makes (PER_UNIT's `node_minutes`), or
    {why} with none."""
    made = json.loads(compute.PER_UNIT.read_text()).get("node_minutes", {}).get(stage)
    if made is None:
        return {"why": f"no make of {stage} timed in the store's finish records"}
    return {"likely_minutes": made["likely"], "high_minutes": made["high"]}


def timed_row(node, paid, price=None):
    """A plan's row as schedule() takes it: {paid, likely_minutes, high_minutes, cards, why}; a paid row's from its
    price (compute.run_price), a free row's from its stage's measured makes."""
    if paid:
        price = price or {"minutes_why": "no price given"}
        timed = {"likely_minutes": price.get("likely_minutes"), "high_minutes": price.get("high_minutes"),
                 "why": price.get("minutes_why")}
        return {"paid": True, "cards": price.get("cards"), **timed}
    return {"paid": False, "cards": None, "likely_minutes": None, "high_minutes": None, "why": None,
            **local_minutes(node.partition("@")[0])}


def has_time(row):
    return row.get("likely_minutes") is not None and row.get("high_minutes") is not None


def links(nodes, edges):
    """({node: [rows after it]}, {node: rows before it}) of the edges between the plan's rows (an edge to a row
    outside the plan stands made, so it waits on nothing)."""
    after, before = {node: [] for node in nodes}, {node: 0 for node in nodes}
    for first, then in edges:
        if first in nodes and then in nodes:
            after[first].append(then)
            before[then] += 1
    return after, before


def fits(row, running, held, jobs, run_cap):
    """Whether a ready row can start now: while fewer than `jobs` rows run (the runner's drive counts every node,
    free and paid), and for a paid row while its cards fit under `run_cap` with those held."""
    if running >= jobs:
        return False
    return not row["paid"] or held + min(row.get("cards") or 0, run_cap) <= run_cap


def walk(nodes, edges, jobs, run_cap, field):
    """The rows driven in dependency order on their `field` minutes (an untimed row none), the stage table's order
    breaking ties: ({node: (start, end)}, {node: the row whose end let it start, or None}). Raises ValueError on a
    cycle."""
    names = list(nodes)
    order = {node: index for index, node in enumerate(names)}
    after, waiting = links(nodes, edges)
    ready = [order[node] for node, count in waiting.items() if count == 0]
    heapq.heapify(ready)
    ready_at, last_before = {node: 0.0 for node, count in waiting.items() if count == 0}, {}
    running, times, cause = [], {}, {}
    now, held, freed_by = 0.0, 0, None
    while ready or running:
        blocked = []
        while ready:
            node = names[heapq.heappop(ready)]
            row = nodes[node]
            if not fits(row, len(running), held, jobs, run_cap):
                blocked.append(order[node])
                continue
            cards = min(row.get("cards") or 0, run_cap) if row["paid"] else 0
            held += cards
            times[node] = (now, now + (row[field] if has_time(row) else 0.0))
            cause[node] = last_before.get(node) if ready_at[node] == now else freed_by
            heapq.heappush(running, (times[node][1], order[node], node, cards))
        for index in blocked:
            heapq.heappush(ready, index)
        if not running:
            break
        now, _, done, cards = heapq.heappop(running)
        held, freed_by = held - cards, done
        for then in after[done]:
            waiting[then] -= 1
            if waiting[then] == 0:
                ready_at[then], last_before[then] = now, done
                heapq.heappush(ready, order[then])
    stuck = [node for node in names if node not in times]
    if stuck:
        raise ValueError(f"the plan's edges make a cycle through {', '.join(stuck)}")
    return times, cause


def path(times, cause):
    """The longest path: the row that ends last, back through the row whose end let each start, first row first."""
    if not times:
        return []
    node = max(times, key=lambda name: times[name][1])
    found = [node]
    while cause.get(node) is not None:
        node = cause[node]
        found.append(node)
    return found[::-1]


def schedule(nodes, edges, jobs, run_cap):
    """The plan's ETA: `nodes` {node: {paid, likely_minutes, high_minutes, cards, why}} in the stage table's order
    (timed_row), `edges` [(before, after)], at most `jobs` rows at once and `run_cap` cards held. Returns
    {likely_minutes, high_minutes (both None unless every row has its minutes), at_least_minutes (the walk with each
    untimed row as no time), path (the longest path's rows, first first), high_path, unknown [{node, paid, why}]}."""
    if jobs < 1 or run_cap < 1:
        raise ValueError(f"jobs ({jobs}) and run_cap ({run_cap}) must be at least 1, or no row ever starts")
    likely_times, likely_cause = walk(nodes, edges, jobs, run_cap, "likely_minutes")
    high_times, high_cause = walk(nodes, edges, jobs, run_cap, "high_minutes")
    unknown = [{"node": node, "paid": row["paid"], "why": row.get("why") or "no minutes"}
               for node, row in nodes.items() if not has_time(row)]
    at_least = max((end for _, end in likely_times.values()), default=0.0)
    high = max((end for _, end in high_times.values()), default=0.0)
    return {"likely_minutes": None if unknown else round(at_least, 2),
            "high_minutes": None if unknown else round(high, 2), "at_least_minutes": round(at_least, 2), "path": path(likely_times, likely_cause),
            "high_path": path(high_times, high_cause), "unknown": unknown}
