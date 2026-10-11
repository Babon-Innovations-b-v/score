"""SCORE's one command: the runner drives a world's lines to their end, with no agent in the loop.

    .venv/bin/python -m score run <world> [--place P ...] [--jobs N] [--detach]  # every line, or those named
    .venv/bin/python -m score status [<world>] [--place P ...]                   # every line's state

`run` drives the lines side by side (with --place, those places' lines and only the world nodes they read), each node in
a process of its own and at most --jobs at once (default score.graph.JOBS; --jobs 1 runs one node at a time). It starts
each node the moment the nodes it reads stand accepted, gathers a gate's missing evidence itself (a paid step cleared by
the runner, waited on by the runner), and stops a line whose node fails, errors or is blocked, with a plain fault report
(faults/<node>.txt beside the store) to point an agent or the owner at; the other lines go on. It exits 1 when any line
stopped. --detach (tools/props/cloud/detached.py) sends its progress to a log and prints one result line at the end:
start it with the Bash tool's run_in_background and never poll it.
"""
import argparse
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from score import graph, stages  # noqa: E402
from score.store import Store  # noqa: E402

DETACH = "--detach"


def parse(argv):
    parser = argparse.ArgumentParser(prog="score", description=__doc__.split("\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run")
    run.add_argument("world", choices=sorted(stages.WORLDS))
    run.add_argument(DETACH, action="store_true", help="progress to a log, one result line at the end")
    run.add_argument("--jobs", type=int, default=graph.JOBS, help="nodes at once (default %(default)s)")
    status = commands.add_parser("status")
    status.add_argument("world", nargs="?", default="world1", choices=sorted(stages.WORLDS))
    for command in (run, status):
        command.add_argument("--place", action="append", help="one place's line (repeat it); default: every place")
    return parser.parse_args(argv)


def detach():
    """Run this command again detached: its progress in a log, one result line at the end."""
    sys.path.insert(0, str(REPO / "tools/props/cloud"))
    import detached
    detached.relaunch(sys.argv, "score-run", [Store.default().cache.parent / "faults"])


def main(argv=None):
    options = parse(argv)
    if getattr(options, "detach", False):
        detach()
    runner = stages.runner(world=stages.WORLDS[options.world]())
    places, whole = options.place or stages.places(runner.world), not options.place
    if options.command == "run":
        runner.drive(places, say=lambda line: print(line, flush=True), jobs=options.jobs, whole=whole)
    lines = runner.lines(places, whole)
    for line, (state, nodes) in lines.items():
        print(f"{line}: {state}")
        if options.command == "status":
            print("\n".join(f"  {node}: {node_state}" for node, node_state in nodes.items()))
    if options.command == "run" and any(state != "done" for state, _ in lines.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
