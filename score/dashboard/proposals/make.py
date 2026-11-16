"""The basket command: what a run on main would buy, grouped into items the owner understands, made on the store's
machine for free.

    .venv/bin/python -m score.dashboard basket

The paid nodes come from the runner's own plan of the whole environment (`score plan`, through the compute backend):
every paid node a run would make, its reason and its price on the runner's measured numbers (C19). A department's
declared item (`basket-item`, records.declared) takes the nodes its patterns name, whatever their places (the ship's
eight room concepts are one item); the rest are grouped (`grouped`) by place and by what they change: a place's nodes
by the OpenUSD layer their output feeds (state/groups.py), the environment's own rows by their family, and a node
joins the item of a node it waits for. Nothing is bought; nothing in the store is written. The cockpit's free
details of each place (its free after, 3D web copy and inputs) went with the cockpit (owner, 2026-11-16).
"""
import fnmatch
import hashlib
import json
import pathlib
import subprocess
import time

from score.dashboard.checkout import pricing
from score.dashboard.launch import guard
from score.dashboard.launch.backend import RunGroup
from score.dashboard.proposals import benchmarks, records

REPO = pathlib.Path(__file__).resolve().parents[3]


def family(stage, place, layer_of):
    """What a paid node changes, in the owner's grouping: a place's OpenUSD layer, else the row's family (its name to
    its second word: people-body-<who> is people-body)."""
    if place:
        return layer_of.get(stage) or "stage and films"
    words = stage.split("-")
    return "-".join(words[:2]) if len(words) > 2 else stage


def waits_for(why):
    """The nodes a buy's reason says it reads and that are made first ("reads a@p, b@p")."""
    if not why.startswith("reads "):
        return []
    return [name.strip() for name in why[len("reads "):].split(";")[0].split(",") if name.strip()]


def joined(buys, layer_of):
    """{node: the node naming its item}: union of the nodes with one place and family, and of a node with each
    node it waits for."""
    parent = {buy["node"]: buy["node"] for buy in buys}

    def root(node):
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node
    first = {}
    for buy in buys:
        stage, _, place = buy["node"].partition("@")
        group = (place, family(stage, place, layer_of))
        parent[root(buy["node"])] = root(first.setdefault(group, buy["node"]))
        for read in waits_for(buy["why"]):
            if read in parent:
                parent[root(buy["node"])] = root(read)
    return {node: root(node) for node in parent}


def version(nodes, why):
    return hashlib.sha256(json.dumps([nodes, why], sort_keys=True).encode()).hexdigest()[:16]


def finished(ident, entry):
    """An item as kept: its id, places, totals and version beside what was gathered."""
    places = sorted({node.partition("@")[2] for node in entry["nodes"]} - {""})
    return {"id": records.checked(ident), **entry, "places": places, "place": places[0] if len(places) == 1 else None,
            "totals": pricing.totals(entry["nodes"]), "version": version(entry["nodes"], entry["why"])}


def gathered(buys, layer_of):
    """{entry: [buy]} of buys not taken by a declared item, grouped by place and what they change."""
    roots = joined(buys, layer_of)
    found = {}
    for buy in buys:
        found.setdefault(roots[buy["node"]], []).append(buy)
    return found


def entry_of(buys, layer_of, title=None):
    """An item's fields from its buys: {title, layers, nodes: {node: price}, why, again, missing, for (the places whose
    line holds any of its nodes, the plan's)}."""
    entry = {"title": title, "layers": [], "nodes": {}, "why": {}, "again": [], "missing": [], "declared": bool(title),
             "for": sorted({place for buy in buys for place in buy.get("for", [])})}
    for buy in buys:
        stage, _, place = buy["node"].partition("@")
        layer = family(stage, place, layer_of)
        if layer not in entry["layers"]:
            entry["layers"].append(layer)
        entry["nodes"][buy["node"]] = buy.get("price") or {"error": "not priced"}
        entry["why"][buy["node"]] = buy["why"]
        if buy["again"]:
            entry["again"].append(buy["node"])
    return entry


def declared_buys(buys, declared):
    """({item id: [buy]}, the buys left): each buy to the first declared item whose node patterns name it."""
    taken, rest = {ident: [] for ident in declared}, []
    for buy in buys:
        owner = next((ident for ident, given in declared.items()
                      if any(fnmatch.fnmatchcase(buy["node"], pattern) for pattern in given.get("nodes", []))), None)
        (taken[owner] if owner else rest).append(buy)
    return taken, rest


def auto_id(entry):
    """An item's id from its first node's place and its first layer (stable across makes)."""
    first = next(iter(entry["nodes"])).partition("@")[2]
    return f"{first or records.ENVIRONMENT}-{entry['layers'][0]}".replace(" ", "-")


def grouped(buys, layer_of, missing=(), declared=None):
    """The basket's items from the plan's buys, in table order: each declared item first (with whatever buys its
    patterns name, none yet included), then the rest by place and what they change: {id, title, places, place,
    layers, nodes: {node: price}, why, again, missing, declared, totals, version}. `missing` the plan's missing inputs
    ("<node>: what"), each said on its node's item."""
    declared = declared or {}
    taken, rest = declared_buys(buys, declared)
    found = [finished(ident, entry_of(taken[ident], layer_of, given.get("title") or ident))
             for ident, given in declared.items()]
    found += [finished(auto_id(entry), entry) for entry in
              (entry_of(group, layer_of) for group in gathered(rest, layer_of).values())]
    for words in missing:
        node = words.split(":")[0].strip()
        owner = next((item for item in found if node in item["nodes"]), None)
        if owner is not None:
            owner["missing"].append(words)
    return found


def layer_map():
    """{stage: OpenUSD layer} of every place stage (state/groups.py over the stage table)."""
    from score import stages
    from score.dashboard.state import groups
    return groups.layers(stages.STAGES)


def commit():
    return subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()


def make(home, real_store, chosen=None, layer_of=None, group=None):
    """Make the basket into home/proposals/: the plan, its items, prepare's benchmarks item last
    (proposals/benchmarks.py); the index, with when, on which commit and in which checkout it was made (the checkout
    refuses one made elsewhere or before the design last changed) and the plan's selection (`group`, a RunGroup: a Buy
    by phase or place plans only those; None, the whole environment)."""
    root = pathlib.Path(home) / "proposals"
    root.mkdir(parents=True, exist_ok=True)
    declared = records.declared(root)
    group = group or RunGroup(places=(), stages=())
    planned = (chosen or guard.backend()).plan(group)
    found = grouped(planned.buys, layer_of or layer_map(), planned.missing, declared)
    found = benchmarks.with_item(found, benchmarks.from_record(pathlib.Path(real_store).parent))
    index = {"made_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "commit": commit(), "checkout": str(REPO),
             "refusal": planned.refusal, "missing": planned.missing, "items": found,
             "selection": {"places": list(group.places), "phases": list(group.phases)}}
    records.put_index(root, index)
    return index
