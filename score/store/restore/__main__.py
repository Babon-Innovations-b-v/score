"""Restore the lost store without buying anything (#13): the free-only runner over an environment's lines, one summary line.

    .venv/bin/python -m score.store.restore world1 --library <score_lib> [--place P ...] [--jobs 2]
    .venv/bin/python -m score.store.restore world1 --library <score_lib> --reattach --max-gb N   # the owner's own
    .venv/bin/python -m score.store.restore --index-checkouts       # the bucket's checkout tars, by their headers

Run it detached (tools/cloud/detached.py -- ...) under the Bash tool's run_in_background: it drives every line.
It refuses to start while paid work is open (the month's books known: ledger.books_refusal gives no reason), so a run
is proof that nothing could be bought; it takes the store's run claim (score/graph/runs.py), so a `score run` beside
it is refused. `--reattach` downloads checkouts of paid outputs whose key matches today (score/store/restore); it is
refused in an agent's process: the egress price is unknown and the yes is the owner's. `--library` defaults to
SCORE_LIB_ROOT.

Its one line: `restore world1: <n> nodes; accepted today A (made free F, re-attached R); unknown U; paid refused P
(key matches today M); line stopped S; failing today's gates X; other O; downloaded N GB; EUR 0; books <state>; detail
<path>`, the detail (each node: what it did, why it is not accepted, its key against the library's, bytes downloaded)
in $PROPS_WORK/restore/<utc>.json. It exits 1 when a spend ledger gained a line or an accept is not the runner's.
"""
import argparse
import atexit
import datetime
import json
import os
import pathlib
import sys

from score import graph
from score.graph import _code, runs
from score.store import RUNNER, Store, running_under_agent, whole_file
from score.store.restore import PAID_REFUSED, FreeRunner, guard_free_only, ledger, library_outputs
from score.store.restore._bucket import Fetch, index_checkouts, open_bucket

import google_spend  # noqa: E402  (tools/cloud, on the path through the restore's ledger import)
from paths import WORK  # noqa: E402

FOLDER = WORK / "restore"
CHECKOUTS = FOLDER / "checkouts.json"
# The order a node's outcome is told in: the first that fits names it (category).
OUTCOMES = ("accepted", "paid refused", "line stopped", "unknown", "failing", "other")


def parse(argv):
    parser = argparse.ArgumentParser(prog="score.store.restore", description=__doc__.split("\n")[0])
    parser.add_argument("world", nargs="?", default="world1", metavar="environment")
    parser.add_argument("--place", action="append", help="one place's line (repeat it); default: every place")
    parser.add_argument("--jobs", type=int, default=2, help="nodes at once (default %(default)s: memory stays modest)")
    parser.add_argument("--library", default=os.environ.get("SCORE_LIB_ROOT"), help="score_lib's checkout")
    parser.add_argument("--reattach", action="store_true", help="download matching checkouts (the owner's own)")
    parser.add_argument("--max-gb", type=float, help="the most a --reattach run downloads")
    parser.add_argument("--index-checkouts", action="store_true", help="index the bucket's checkout tars")
    return parser.parse_args(argv)


def start_refusal(options):
    """Why the restore may not start, or None."""
    if ledger.books_refusal() is None:
        return "the month's books are known, so paid work is open; the restore runs only while it is shut"
    if not options.library or not pathlib.Path(options.library, "entries").is_dir():
        return f"no library at {options.library!r}: give --library <score_lib checkout> or SCORE_LIB_ROOT"
    if options.reattach and running_under_agent():
        return "--reattach downloads from the bucket at an unknown egress price: the owner runs it himself"
    if options.reattach and not (options.max_gb and CHECKOUTS.exists()):
        return f"--reattach needs --max-gb and the checkouts index ({CHECKOUTS}: --index-checkouts)"
    return None


def ledger_lines():
    """The number of lines each spend ledger holds now (the cloud's, Google's)."""
    return [path.read_text().count("\n") if path.exists() else 0 for path in (ledger.LEDGER, google_spend.LEDGER)]


def books_state():
    """The month's books' state: `known` or `lost` as written for this month, else `unknown`."""
    return ledger.this_months_books().get("state", "unknown")


def category(did, stands):
    """Which of OUTCOMES a node's run fits: what it did, and why it does not stand (None when it does)."""
    if stands is None:
        return "accepted"
    if did.startswith(f"blocked: {PAID_REFUSED}"):
        return "paid refused"
    if did.startswith("not run: its line stopped"):
        return "line stopped"
    if did.startswith("blocked: needs Blender") or ": unknown" in did:
        return "unknown"
    if ": fail" in did:
        return "failing"
    return "other"


def described(runner, found):
    """{node: {did, category, not_accepted, and its process's note}} of a drive's outcome."""
    rows = {}
    with runner.still():
        for node, did in found.items():
            stage, place = next(runner.nodes_named([node]))
            stands = runner.standing(stage, place)
            rows[node] = {"did": did, "category": category(did, stands), "not_accepted": stands,
                          **runner.notes.read(node)}
    return rows


def strays(runner, nodes):
    """Every accept of the nodes not given by the runner: none may come from a restore."""
    return [accept for node in nodes for accept in runner.store.accepts(node) if accept.get("by") != RUNNER]


def summary_line(world, rows, added, detail):
    """The restore's one line (the module docstring's); `added`: the lines each spend ledger gained, which turn its
    EUR 0 into what was added."""
    count = {outcome: sum(1 for row in rows.values() if row["category"] == outcome) for outcome in OUTCOMES}
    reattached = sum(1 for row in rows.values() if row["category"] == "accepted" and row.get("reattached"))
    matches = sum(1 for row in rows.values() if row.get("key_matches"))
    downloaded = sum(row.get("downloaded", 0) for row in rows.values()) / 1e9
    spent = f"spend ledger lines added {added}" if any(added) else "EUR 0"
    return (f"restore {world}: {len(rows)} nodes; accepted today {count['accepted']} (made free "
            f"{count['accepted'] - reattached}, re-attached {reattached}); unknown {count['unknown']}; paid refused "
            f"{count['paid refused']} (key matches today {matches}); line stopped {count['line stopped']}; failing "
            f"today's gates {count['failing']}; other {count['other']}; downloaded {downloaded:.2f} GB; {spent}; books "
            f"{books_state()}; detail {detail}")


def restore(runner, places, whole, jobs, detail, say=print):
    """Drive the free runner over the places' lines (`whole`: the environment's every line), its detail in `detail`
    (write_detail); (the summary line, the exit status: 1 when a spend ledger gained a line or an accept is not the
    runner's)."""
    started, before = graph.now(), ledger_lines()
    found = runner.drive(places, say=say, jobs=jobs, whole=whole)
    rows = described(runner, found)
    added = [after - earlier for after, earlier in zip(ledger_lines(), before)]
    foreign = strays(runner, found)
    write_detail(detail, runner, started, rows, added, foreign)
    return summary_line(runner.world.name, rows, added, detail), int(any(added) or bool(foreign))


def write_detail(path, runner, started, rows, added, foreign):
    """The run's detail file: each node's row, the books, the ledger lines added and the accepts not the runner's."""
    written_whole(path, {"world": runner.world.name, "started": started, "finished": graph.now(),
                         "books": ledger.read_books(), "ledger_lines_added": added, "accepts_not_by_runner": foreign,
                         "nodes": rows})


def written_whole(path, data):
    """`data` as JSON at `path`, landed whole through a partial file of this process (a crash leaves no half file)."""
    whole_file(path, json.dumps(data, indent=1).encode()).replace(path)


def free_runner(options, folder):
    """The free runner over the environment's stage table on the framework's store, with the library's outputs, the
    checkouts index when there is one and, under --reattach, downloads within --max-gb."""
    from score import stages
    world = stages.WORLDS[options.world]()
    checkouts = json.loads(CHECKOUTS.read_text())["checkouts"] if CHECKOUTS.exists() else None
    fetch = Fetch(open_bucket(), folder / "downloads", options.max_gb * 1e9) if options.reattach else None
    return FreeRunner(stages.TABLES.get(world.name, stages.STAGES), world, Store.default(), folder / "notes",
                      library_outputs(options.library), checkouts, fetch)


def claim_store(runner, places, whole):
    """Take the store's run claim (graph/runs.py) for the nodes the restore would make; exit when refused."""
    commit = runs.identity(_code.git_commit()["commit"], runs.tracked_changes(), _code.REPO)
    refused = runs.claim(commit, runs.would_make(runner, runner.line_nodes(places, whole)), os.getpid())
    if refused:
        sys.exit(f"refused: {refused}")
    atexit.register(runs.unclaim, os.getpid())


def index_command():
    """Index the bucket's checkout tars into CHECKOUTS, the month's bill read before and after (request charges)."""
    from score.adapters import compute
    bill_before = compute.cloud_bill()
    found = index_checkouts(open_bucket())
    written_whole(CHECKOUTS, {"at": graph.now(), "bill_before": bill_before, "bill_after": compute.cloud_bill(),
                              "checkouts": found})
    tars = [tar for candidates in found.values() for tar in candidates]
    print(f"checkouts: {len(found)} outputs in {len(tars)} tars ({sum(tar['bytes'] for tar in tars) / 1e9:.1f} GB); "
          f"index {CHECKOUTS}")


def main(argv=None):
    options = parse(argv)
    if options.index_checkouts:
        index_command()
        return
    refused = start_refusal(options)
    if refused:
        sys.exit(f"refused: {refused}")
    guard_free_only()
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    runner = free_runner(options, FOLDER / stamp)
    from score import stages
    places, whole = options.place or stages.places(runner.world, runner.store), not options.place
    claim_store(runner, places, whole)
    line, status = restore(runner, places, whole, options.jobs, FOLDER / f"{stamp}.json",
                           say=lambda text: print(text, flush=True))
    print(line, flush=True)
    sys.exit(status)


if __name__ == "__main__":
    main()
