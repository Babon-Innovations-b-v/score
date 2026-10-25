"""The library rows: every accepted output of a world handed to the creator's library, so everything that is in a
world shows up in the library by construction, never by an agent's hand.

    library@<place>   (place, free) runs last on its place's line: it reads every place row of the table (a row whose
                      `applies` leaves the place out is read without, Runner.reads), the showcase renders optional
                      (SHOWCASE: a place's handover never waits on a paid film, and hands it once it stands)
    library-world     (world, free) reads every world row: the world's own outputs (ground, algorithms)

    rows = library.rows(table, data)                    # the two rows for a stage table whose world data is `data`
    library.world_completion(runner, places)            # [(node, why it does not stand)]: empty when the world is complete

The route (`route`): the hash of the route stages' code versions (make and gates, Runner.code) and contracts, the
prop pipeline and the finish route. It is a key part of both rows (a callable param the runner works out), handed to
the library's command (`--route`), which stamps it into each entry's provenance; prepare reuses a library model only
under today's route (score/stages/complete/prepare/library.py).

The make (`make`) writes `reads.json`, every accepted output the node read as {node, output, into, beyond}: `into`
the rows of its own grain made from it, row by row (the table's `after`, the `made into` param), `beyond` those of the
other grain (a world row a place's rows are made from); then it runs the library's
handover command once (backend.py: SCORE_LIB_* from the environment, else the checkout beside score), which writes
`handover.json` (contract library-handover v1, handover.py) into the node's output folder. With no library configured
it writes a report that says so, and the gate fails unless the world is library-free (data/checks/library-free.json,
an owner's dated decision). The node never locks, withdraws or deletes an entry: drafts only; locking is the owner's.

Completion: a place is complete when library@<place> stands accepted (complete@<place> keeps its meaning, "the place
holds what it should", and its key). The world is complete when library-world and every place's library node stand
accepted (`world_completion`, printed by `python -m score status`).

Why two rows of their own and not part of complete: demo-film (paid) reads complete, so any change to complete's code
or checks would re-key it; the library rows are read by nothing, so a change here re-keys only them.
"""
import json
import pathlib
import subprocess

from score import graph
from score.stages.library import backend, checks, handover

REPO = pathlib.Path(__file__).resolve().parents[3]
PLACE_ROW, WORLD_ROW = "library", "library-world"
# The showcase renders: read once they stand, never waited on.
SHOWCASE = ("demo-film", "demo-film-extra", "environment-film")
WORLD_RECORD, PLACE_RECORD = "world record", "place record"
FREE, EXCEPTIONS = "library free", "exceptions"
DECLARED = (WORLD_RECORD, PLACE_RECORD, FREE, EXCEPTIONS)
# The route a library model is made under: the prop pipeline and the finish route (stage-name prefixes).
ROUTE_STAGES = ("props-inputs", "closeup", "pixal", "finish-route-", "surfaces-", "likeness")


def route(code_of, table):
    """The route the table's route stages make under: the hash of each one's code version (`code_of(stage)`: its
    make's and gates' code) and contract stamp. A change to any of them is a new route."""
    found = {stage.name: [code_of(stage), stage.contract.stamp_of()] for stage in table
             if stage.name.startswith(ROUTE_STAGES)}
    return graph.text_hash(json.dumps(found, sort_keys=True))


def runner_route(runner):
    """The route under this runner's own code versions (the library rows' `route` param)."""
    return route(runner.code, runner.stages.values())


def declared_files(data):
    """The library rows' world files for a world whose data folder is `data`: the world record (its name and seed),
    the library-free decisions, the written exceptions once the file is there, and for a place node the place's
    record (its kept plan, the design's), whose name is the place the node hands."""
    data = pathlib.Path(data)

    def files(place):
        found = {WORLD_RECORD: "{data}/definitions/world.json", FREE: "{data}/checks/library-free.json"}
        if (data / "checks/library-exceptions.json").exists():
            found[EXCEPTIONS] = "{data}/checks/library-exceptions.json"
        if place is not None:
            found[PLACE_RECORD] = "{home}/design/plans/{place}.json"
        return found
    return files


def place_of(inputs):
    """The place a node hands (its place record's name), or None for the world's own node."""
    return pathlib.Path(inputs[PLACE_RECORD]).stem if PLACE_RECORD in inputs else None


def made_into(table):
    """{"readers": {row: the rows that read it, sorted}, "world": the world rows, sorted} of a stage table, the library
    rows left out: what each row's output is made into (reads_of)."""
    rows = [row for row in table if row.name not in (PLACE_ROW, WORLD_ROW)]
    readers = {}
    for row in rows:
        for before in row.after:
            readers.setdefault(before, set()).add(row.name)
    return {"readers": {name: sorted(found) for name, found in sorted(readers.items())},
            "world": sorted(row.name for row in rows if row.grain == "world")}


def runner_made_into(runner):
    """made_into of this runner's table (the library rows' `made into` param)."""
    return made_into(runner.stages.values())


def made_from(name, relation):
    """Every row made from row `name`'s output, row by row through the readers of `relation` (made_into), sorted."""
    found, waiting = set(), [name]
    while waiting:
        for reader in relation["readers"].get(waiting.pop(), []):
            if reader not in found:
                found.add(reader)
                waiting.append(reader)
    return sorted(found)


def reads_of(inputs, relation):
    """[{node, output, into, beyond}] of every accepted output the node read, sorted: each earlier row's checkout is
    named by its output's hash; `into` the rows of the node's grain made from it, `beyond` those of the other grain
    (made_from over `relation`, made_into's answer)."""
    place = place_of(inputs)
    world = set(relation["world"])
    found = []
    for name, path in inputs.items():
        if name in DECLARED:
            continue
        made = made_from(name, relation)
        own = [row for row in made if (row in world) == (place is None)]
        found.append({"node": f"{name}@{place}" if place else name, "output": pathlib.Path(path).name, "into": own,
                      "beyond": [row for row in made if row not in own]})
    return sorted(found, key=lambda row: row["node"])


def score_commit():
    """The commit of the score repository the outputs are read at."""
    return subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True,
                          check=True).stdout.strip()


def store_objects(out):
    """The runner's store objects folder, beside the cache the node makes into (Store: <root>/cache/making/<key>-...,
    <root>/objects)."""
    return pathlib.Path(out).resolve().parents[2] / "objects"


def run_of(inputs, out, params):
    """What the handover command is told: {world, place, seed, commit, route, store, repo, out}."""
    world = json.loads(pathlib.Path(inputs[WORLD_RECORD]).read_text())
    return {"world": world["name"], "place": place_of(inputs), "seed": world["seed"], "commit": score_commit(),
            "route": params["route"], "store": str(store_objects(out)), "repo": str(REPO), "out": str(out)}


def make(inputs, out, seed, params):
    """Write reads.json, then hand the node's outputs to the configured library, whose command writes handover.json;
    with none configured, a report saying so."""
    handover.write(out / handover.READS, reads_of(inputs, params["made into"]))
    run, values = run_of(inputs, out, params), backend.settings()
    if backend.kind(values) == backend.NONE:
        handover.write(out / handover.REPORT, handover.none_report(run))
        return
    backend.run(backend.arguments(values, run), values, run["store"], run["repo"])
    if not (out / handover.REPORT).is_file():
        raise RuntimeError(f"the library's handover command wrote no {handover.REPORT} into {out}")


def rows(table, data, identity=None):
    """(library, library-world) for a stage table: the place row reading every place row, the world row every world
    row; their params the library's identity (backend.identity), so a new library re-keys these two alone, the
    route (`runner_route`), so a new route hands every entry again under it, and what each row is made into
    (`runner_made_into`), which the gate holds an output through."""
    params = {"library": backend.identity() if identity is None else identity, "route": runner_route,
              "made into": runner_made_into}
    place_rows = {row.name: (row.contract.schema, row.contract.version) for row in table if row.grain == "place"}
    world_rows = {row.name: (row.contract.schema, row.contract.version) for row in table if row.grain == "world"}
    files = declared_files(data)
    place = graph.Stage(PLACE_ROW, "place", make, handover.LIBRARY_HANDOVER, checks.CHECKS, files=files,
                        after=place_rows, optional=tuple(name for name in SHOWCASE if name in place_rows),
                        params=params)
    world = graph.Stage(WORLD_ROW, "world", make, handover.LIBRARY_HANDOVER, checks.CHECKS, files=files,
                        after=world_rows, optional=tuple(name for name in SHOWCASE if name in world_rows),
                        params=params)
    return place, world


def world_completion(runner, places):
    """[(node, why it does not stand)] of the world's library nodes: library-world and each place's library node.
    Empty when the world is complete."""
    nodes = [(runner.stages[WORLD_ROW], None), *((runner.stages[PLACE_ROW], place) for place in places)]
    with runner.still():
        found = [(graph.node_name(stage, place), runner.standing(stage, place)) for stage, place in nodes]
    return [(node, why) for node, why in found if why]


def completion_line(world, waiting):
    """The world's completion in one line, from world_completion's answer."""
    if not waiting:
        return f"{world}: complete: library-world and every place's library node stand accepted"
    shown = "; ".join(f"{node}: {why}" for node, why in waiting[:3])
    more = f" (and {len(waiting) - 3} more)" if len(waiting) > 3 else ""
    return f"{world}: not complete, {len(waiting)} library nodes do not stand: {shown}{more}"
