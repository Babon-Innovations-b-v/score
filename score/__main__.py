"""SCORE's one command: the runner drives a world's lines to their end, with no agent in the loop.

    .venv/bin/python -m score run <world> [--place P ...] [--stage S ...] [--jobs N] [--detach] [--rebuy-reason R]
    .venv/bin/python -m score status [<world>] [--place P ...] [--stage S ...]                   # every line's state
    .venv/bin/python -m score images publish <kind>   # an accepted image proof's record into images.json
    .venv/bin/python -m score plan <world> [--place P ...] [--stage S ...] [--rebuy-reason R] --json
    .venv/bin/python -m score spend --json            # this month's spend, open reservations and the ceiling

`status --json` prints the same lines as one JSON object. `plan` works out what `run` would do with the same arguments,
running nothing: the missing inputs, the nodes it would make and why, the paid rows it would buy with their estimates
and the re-buy refusal (the dashboard's launch basket reads it, score/dashboard). `spend` reads the month's spend as
the runner's clearance counts it.

`run` drives the lines side by side (with --place, those places' lines and only the world nodes they read), each node in
a process of its own and at most --jobs at once (default score.graph.JOBS; --jobs 1 runs one node at a time); with
--stage, only those stages and the ones they read (a line's other rows, a paid surface row say, are left alone). It starts
each node the moment the nodes it reads stand accepted, gathers a gate's missing evidence itself (a paid step cleared by
the runner, waited on by the runner), and stops a line whose node fails, errors or is blocked, with a plain fault report
(faults/<node>.txt beside the store) to point an agent or the owner at; the other lines go on. It exits 1 when any line
stopped. --detach returns at once with the log's path: the run goes on in a session of its own
(tools/props/cloud/detached.py), its progress in that log and, when every line is done or stopped, one result line
(`detached: ok|failed exit=N minutes=M log=... outputs=<faults folder>`) as the log's last line; a run stopped by
SIGTERM, SIGINT or SIGHUP says `score run: stopped by signal N`, then `detached: stopped by signal N exit=128+N ...`.
Wait for that line with the Monitor tool, never a poll loop.

Before it starts, `run` lists every paid row it would buy with its estimate (score/graph/rebuy.py; a Google ask its
cache answers at EUR 0) and refuses, before detaching, when buying again rows that already have an accepted output
would cost over EUR 5, unless given --rebuy-reason, which goes into the run's log and the cloud ledger.
"""
import argparse
import datetime
import json
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from score import graph, stages  # noqa: E402
from score.graph import rebuy, stopped  # noqa: E402
from score.store import Store  # noqa: E402

DETACH = "--detach"


def parse(argv):
    parser = argparse.ArgumentParser(prog="score", description=__doc__.split("\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run")
    run.add_argument("world", choices=sorted(stages.WORLDS))
    run.add_argument(DETACH, action="store_true", help="progress to a log, one result line at the end")
    run.add_argument("--jobs", type=int, default=graph.JOBS, help="nodes at once (default %(default)s)")
    run.add_argument("--rebuy-reason", help="why outputs already standing are bought again (needed over EUR 5)")
    status = commands.add_parser("status")
    status.add_argument("world", nargs="?", default="world1", choices=sorted(stages.WORLDS))
    status.add_argument("--json", action="store_true", help="the lines as one JSON object")
    plan = commands.add_parser("plan")
    plan.add_argument("world", choices=sorted(stages.WORLDS))
    plan.add_argument("--rebuy-reason", help="the reason a run would be given")
    plan.add_argument("--json", action="store_true", help="the plan as one JSON object (the only form)")
    spend = commands.add_parser("spend")
    spend.add_argument("--json", action="store_true", help="the month's spend as one JSON object (the only form)")
    images = commands.add_parser("images").add_subparsers(dest="images_command", required=True)
    images.add_parser("publish").add_argument("kind", choices=stages.images.proved_kinds())
    for command in (run, status, plan):
        command.add_argument("--place", action="append", help="one place's line (repeat it); default: every place")
        command.add_argument("--stage", action="append", help="only this stage and what it reads (repeat it)")
    return parser.parse_args(argv)


def detach(argv):
    """Start this command (argv, less --detach) again in a session of its own under detached.py, its output and then
    its result line into a fresh log (graph/stopped.py: on a stopping signal too); print the log's path and return
    at once."""
    sys.path.insert(0, str(REPO / "tools/props/cloud"))
    import detached
    log = detached.log_path_for("score-run")
    command = [sys.executable, stopped.__file__, "--log", str(log), "--outputs",
               str(Store.default().cache.parent / "faults"), "--", sys.executable,
               *[word for word in argv if word != DETACH]]
    with open(log, "a") as result:  # detached.py prints its result line here, after the run's own output
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=result, stderr=subprocess.STDOUT,
                                   start_new_session=True)
    print(f"detached: started pid={process.pid} log={log}", flush=True)


def publish(kind):
    """Write the kind's accepted image proof into images.json; refused unless it passed and stands accepted."""
    try:
        record = stages.images.publish(stages.runner(world=stages.images.image_world()), kind)
    except graph.Blocked as block:
        sys.exit(f"not published: {block}")
    print(f"{kind}: {record['image']} into {stages.images.IMAGES_JSON}")


def buy_check(runner, places, whole, only, reason):
    """What a run of these lines would do before it starts, running nothing: {"missing": inputs it could never make
    itself, "buys": [Buy] in table order (none when inputs are missing: free checks before paid), "refusal": why the
    run is refused or None, "to_run": {node: why} of every node it would make, "blocked": {node: why} of every node
    it could not start}."""
    nodes = runner.line_nodes(places, whole, only)
    missing = runner.missing_inputs(nodes)
    if missing:
        return {"missing": missing, "buys": [], "to_run": {}, "blocked": {},
                "refusal": "refused: these inputs are missing, so the rows that read them would stop the run after it "
                           "paid for others:\n  " + "\n  ".join(missing)}
    with runner.still():
        bought = rebuy.buys(runner, nodes)
        states = {node: state for _, line_nodes in runner.lines(places, whole, only).values()
                  for node, state in line_nodes.items()}
    return {"missing": [], "buys": bought, "refusal": rebuy.refusal(bought, reason),
            "to_run": {node: state for node, state in states.items() if state.startswith("to run")},
            "blocked": {node: state for node, state in states.items() if state.startswith("blocked")}}


def checked_buys(runner, places, whole, options):
    """Print the paid rows the run would buy; exit when its re-buys pass the limit with no reason. The run itself (not
    the call that detaches it) writes a given reason to the cloud ledger. A run missing an input it could never make
    itself (Runner.missing_inputs) is refused first, each file named: free checks before paid."""
    missing = runner.missing_inputs(runner.line_nodes(places, whole, options.stage))
    if missing:
        sys.exit("refused: these inputs are missing, so the rows that read them would stop the run after it paid for "
                 "others:\n  " + "\n  ".join(missing))
    bought = rebuy.buys(runner, runner.line_nodes(places, whole, options.stage))
    print(rebuy.listing(bought), flush=True)
    refused = rebuy.refusal(bought, options.rebuy_reason)
    if refused:
        sys.exit(refused)
    if options.rebuy_reason and any(buy.again for buy in bought):
        print(f"re-buy reason: {options.rebuy_reason}", flush=True)
        if not options.detach:
            from score.adapters import compute
            compute.ledger().record(rebuy.ledger_entry(bought, options.rebuy_reason))


def plan_json(runner, places, whole, options):
    """The plan of a run (buy_check) as one JSON object: each buy as {node, euros, why, again}."""
    found = buy_check(runner, places, whole, options.stage, options.rebuy_reason)
    found["buys"] = [{"node": buy.node, "euros": buy.euros, "why": buy.why, "again": buy.again}
                     for buy in found["buys"]]
    return {"world": runner.world.name, "places": places, "stages": options.stage or [], **found}


def spend_json():
    """This month's spend as the clearance counts it: {spent, reserved (open reservations), ceiling, month, as_of}."""
    from score.adapters import compute
    reservations = Store.default().cache.parent / "reservations.json"
    held = compute.open_reservations(reservations)
    return {"spent": round(compute.month_spent(), 2), "reserved": round(sum(item["euros"] for item in held.values()), 2),
            "ceiling": compute.ledger().MONTH_EUROS, "month": compute.ledger().this_month(),
            "as_of": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")}


def status_json(world, lines):
    """The lines of `status` as one JSON object: {world, made_at, lines: {line: {state, nodes: {node: state}}}}."""
    return {"world": world, "made_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
            "lines": {line: {"state": state, "nodes": nodes} for line, (state, nodes) in lines.items()}}


def main(argv=None):
    options = parse(argv)
    if options.command == "images":
        publish(options.kind)
        return
    if options.command == "spend":
        print(json.dumps(spend_json()))
        return
    runner = stages.runner(world=stages.WORLDS[options.world]())
    places, whole = options.place or stages.places(runner.world), not options.place
    if options.command == "plan":
        print(json.dumps(plan_json(runner, places, whole, options)))
        return
    if options.command == "run":
        checked_buys(runner, places, whole, options)
    if getattr(options, "detach", False):
        detach(sys.argv)
        return
    if options.command == "run":
        stopped.stop_on_signals(lambda number: print(f"score run: stopped by signal {number}", flush=True))
        runner.drive(places, say=lambda line: print(line, flush=True), jobs=options.jobs, whole=whole,
                     only=options.stage)
    lines = runner.lines(places, whole, options.stage)
    if getattr(options, "json", False):
        print(json.dumps(status_json(options.world, lines)))
        return
    for line, (state, nodes) in lines.items():
        print(f"{line}: {state}")
        if options.command == "status":
            print("\n".join(f"  {node}: {node_state}" for node, node_state in nodes.items()))
    if options.command == "run" and any(state != "done" for state, _ in lines.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
