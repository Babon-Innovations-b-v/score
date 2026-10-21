"""The basket command: what a run on main would buy, grouped into items the owner understands, each with its free
details, made on the store's machine for free.

    .venv/bin/python -m score.dashboard basket [--place P ...]

The paid nodes come from the runner's own plan of the whole environment (`score plan`, through the compute backend):
every paid node a run would make, its reason and its price on the runner's measured numbers (C19). A department's
declared item (`basket-item`, records.declared) takes the nodes its patterns name, whatever their places (the ship's
eight room concepts are one item); the rest are grouped (`grouped`) by place and by what they change: a place's nodes
by the OpenUSD layer their output feeds (state/groups.py), the environment's own rows by their family, and a node
joins the item of a node it waits for. Then each place with an item gets its free after (assemble.py in a subprocess
over a scratch store in the dashboard's home, proposals-work/store, kept across makes, so a second make on the same
code makes nothing again), its 3D web copy and what changes (details.py), and the inputs each paid node would be made
from (pictures as small JPEGs, short texts quoted); a declared item's own pictures and files beside. Nothing is bought;
nothing in the store is written. `--place` makes those places' details again and keeps the rest. `--plan-only`
makes the plan and its items and assembles no place: for a store whose free rows before a place's first paid one
would run heavy local work (the lost store of 2026-10-19), or when only the buys are wanted.
"""
import fnmatch
import hashlib
import itertools
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time

from PIL import Image

from score.dashboard.checkout import pricing
from score.dashboard.launch import guard
from score.dashboard.launch.backend import RunGroup
from score.dashboard.proposals import assemble, benchmarks, details, records

REPO = pathlib.Path(__file__).resolve().parents[3]
WORK = "proposals-work"
THREADS = "4"
INPUT_SIDE = 960  # px, an input picture's longest side as the details show it
QUOTED = 600  # characters of a short text input quoted
# The fields of a JSON input that hold words for a person (a brief, a request's wording): the first one found is quoted.
WORD_KEYS = ("wording", "brief", "said", "words", "description", "prompt")


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
    """An item's fields from its buys: {title, layers, nodes: {node: price}, why, again, missing}."""
    entry = {"title": title, "layers": [], "nodes": {}, "why": {}, "again": [], "missing": [], "declared": bool(title)}
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


def assembled(place, nodes, real_store, work):
    """assemble.py's result for the place (None: the environment's own rows, inputs only), in a subprocess on this
    checkout's code over the scratch store in `work`, its log beside it."""
    job = work / "jobs" / (place or records.ENVIRONMENT)
    shutil.rmtree(job / "stage", ignore_errors=True)
    job.mkdir(parents=True, exist_ok=True)
    (job / "nodes.json").write_text(json.dumps(sorted(nodes)))
    command = [sys.executable, "-m", "score.dashboard.proposals.assemble", *(["--place", place] if place else []),
               "--store", str(real_store), "--scratch", str(work / "store"), "--nodes", str(job / "nodes.json"),
               "--out", str(job / "result.json"), "--folder", str(job / "stage")]
    environment = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "OMP_NUM_THREADS": THREADS}
    with open(job / "assemble.log", "w") as log:
        done = subprocess.run(command, cwd=REPO, stdout=log, stderr=subprocess.STDOUT, env=environment)
    if done.returncode != 0:
        raise RuntimeError(f"the free after of {place or 'the environment'} failed; its log: {job / 'assemble.log'}")
    return json.loads((job / "result.json").read_text())


def words_in(value):
    """The first words a person wrote in a JSON value (under a WORD_KEYS field, depth first), or None."""
    if isinstance(value, dict):
        for key in WORD_KEYS:
            if isinstance(value.get(key), str) and value[key].strip():
                return value[key]
        value = list(value.values())
    if isinstance(value, list):
        return next((found for found in (words_in(each) for each in value) if found), None)
    return None


def quoted(path):
    """A text input's words: a plain text whole, a JSON file's words (words_in), None when it holds none."""
    text = pathlib.Path(path).read_text(errors="replace")
    if not str(path).lower().endswith(".json"):
        return text
    try:
        return words_in(json.loads(text))
    except ValueError:
        return None


def shown_input(found, number, out):
    """One input as the details show it: a picture as a small JPEG in out/inputs/, a short text quoted; None for a
    text with no words in it."""
    shown = {"from": found["from"], "how": found["how"], "name": found["name"], "kind": found["kind"]}
    if found["kind"] == "text":
        words = quoted(found["path"])
        return {**shown, "text": words[:QUOTED]} if words else None
    target = out / "inputs" / f"{number}.jpg"
    target.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(found["path"]) as picture:
        picture.thumbnail((INPUT_SIDE, INPUT_SIDE))
        picture.convert("RGB").save(target, quality=85)
    return {**shown, "file": f"inputs/{target.name}"}


def shown_files(given, out, numbers):
    """[shown_input] of an input list, each numbered from the `numbers` counter; a file that cannot be read is
    said."""
    files = []
    for each in given:
        try:
            shown = shown_input(each, next(numbers), out)
        except OSError as failed:
            shown = {"from": each["from"], "name": each["name"], "kind": "unread", "why": str(failed)[:200]}
        if shown:
            files.append(shown)
    return files


def shown_inputs(inputs, out):
    """{node: {reads, files} or {blocked}} with each file as shown_input."""
    numbers = itertools.count(1)
    return {node: {**given, "files": shown_files(given["files"], out, numbers)} if "files" in given else given
            for node, given in inputs.items()}


def made_stages(taken, place):
    """The rows the free after made at this place."""
    return sorted({item["stage"] for item in taken if item["how"] == records.MADE and
                   item["node"].endswith(f"@{place}")})


def place_details(place, nodes, real_store, root, work):
    """Make one place's details (or the environment's own rows', place None) and swap them in; its details."""
    started = time.monotonic()
    partial = pathlib.Path(tempfile.mkdtemp(prefix=f".{place or records.ENVIRONMENT}-", dir=root))
    try:
        result = assembled(place, nodes, real_store, work)
        after = (details.place_after(place, result, [work / "store", real_store], real_store, partial, work)
                 if place else {})
        found = {"place": place, "made_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **after,
                 "blocked": result.get("blocked"), "made": made_stages(result.get("taken", []), place),
                 "inputs": shown_inputs(result.get("inputs", {}), partial),
                 "seconds": round(time.monotonic() - started, 1)}
        records.put_place(root, partial, place, found)
    finally:
        shutil.rmtree(partial, ignore_errors=True)
    return found


def declared_details(ident, given, root):
    """A declared item's own pictures and files (its plan, its drawing, its brief) as its details' inputs."""
    partial = pathlib.Path(tempfile.mkdtemp(prefix=f".item-{ident}-", dir=root))
    try:
        listed = [{"from": "data", "how": None, "name": pathlib.Path(path).name, "path": path,
                   "kind": "picture" if path.lower().endswith(assemble.PICTURES) else "text"}
                  for path in [*given.get("pictures", []), *given.get("files", [])]]
        found = {"item": ident, "made_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                 "inputs": {"declared": {"files": shown_files(listed, partial, itertools.count(1))}}}
        records.put_place(root, partial, records.declared_folder(ident), found)
    finally:
        shutil.rmtree(partial, ignore_errors=True)


def failed_details(place, why):
    return {"place": place, "made_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "error": why[-1000:]}


def layer_map():
    """{stage: OpenUSD layer} of every place stage (state/groups.py over the stage table)."""
    from score import stages
    from score.dashboard.state import groups
    return groups.layers(stages.STAGES)


def commit():
    return subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()


def nodes_by_place(found):
    """{place or None: the paid nodes of every item at it}."""
    by_place = {}
    for item in found:
        for node in item["nodes"]:
            by_place.setdefault(node.partition("@")[2] or None, set()).add(node)
    return by_place


def make(home, real_store, only=(), chosen=None, layer_of=None, say=lambda line: None, plan_only=False):
    """Make the basket into home/proposals/: the plan, its items, each place's details (none with `plan_only`: no
    place is assembled), prepare's benchmarks item last (proposals/benchmarks.py); the index, with when, on which
    commit and in which checkout it was made (the checkout refuses one made elsewhere or before the design last
    changed). `say` gets one line a place."""
    root, work = pathlib.Path(home) / "proposals", pathlib.Path(home) / WORK
    root.mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)
    declared = records.declared(root)
    planned = (chosen or guard.backend()).plan(RunGroup(places=(), stages=()))
    found = grouped(planned.buys, layer_of or layer_map(), planned.missing, declared)
    for place, nodes in ({} if plan_only else nodes_by_place(found)).items():
        if only and place not in only:
            continue
        try:
            made = place_details(place, nodes, real_store, root, work)
            say(f"{place or records.ENVIRONMENT}: {made['seconds']} s, after {'made' if made.get('copy') else 'as now'}")
        except (RuntimeError, OSError) as failed:  # said on the item's details; the other places go on
            partial = pathlib.Path(tempfile.mkdtemp(prefix=".failed-", dir=root))
            records.put_place(root, partial, place, failed_details(place, str(failed)))
            say(f"{place or records.ENVIRONMENT}: failed: {str(failed)[-200:]}")
    for ident, given in declared.items():
        declared_details(ident, given, root)
    found = benchmarks.with_item(found, benchmarks.from_record(pathlib.Path(real_store).parent))
    index = {"made_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "commit": commit(), "checkout": str(REPO),
             "refusal": planned.refusal, "missing": planned.missing, "items": found, "plan_only": plan_only}
    records.put_index(root, index)
    return index
