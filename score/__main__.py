"""SCORE's one command: the runner drives a world's lines to their end, with no agent in the loop.

    .venv/bin/python -m score run <world> [--place P ...] [--stage S ...] [--jobs N] [--detach]  # every line, or named
    .venv/bin/python -m score status [<world>] [--place P ...] [--stage S ...]                   # every line's state
    .venv/bin/python -m score images publish <kind>   # an accepted image proof's record into images.json

`run` drives the lines side by side (with --place, those places' lines and only the world nodes they read), each node in
a process of its own and at most --jobs at once (default score.graph.JOBS; --jobs 1 runs one node at a time); with
--stage, only those stages and the ones they read (a line's other rows, a paid surface row say, are left alone). It starts
each node the moment the nodes it reads stand accepted, gathers a gate's missing evidence itself (a paid step cleared by
the runner, waited on by the runner), and stops a line whose node fails, errors or is blocked, with a plain fault report
(faults/<node>.txt beside the store) to point an agent or the owner at; the other lines go on. It exits 1 when any line
stopped. --detach returns at once with the log's path: the run goes on in a session of its own
(tools/props/cloud/detached.py), its progress in that log and, when every line is done or stopped, one result line
(`detached: ok|failed exit=N minutes=M log=... outputs=<faults folder>`) as the log's last line. Wait for that line with
the Monitor tool, never a poll loop.
"""
import argparse
import pathlib
import subprocess
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
    images = commands.add_parser("images").add_subparsers(dest="images_command", required=True)
    images.add_parser("publish").add_argument("kind", choices=stages.images.proved_kinds())
    for command in (run, status):
        command.add_argument("--place", action="append", help="one place's line (repeat it); default: every place")
        command.add_argument("--stage", action="append", help="only this stage and what it reads (repeat it)")
    return parser.parse_args(argv)


def detach(argv):
    """Start this command (argv, less --detach) again in a session of its own under detached.py, its output and then
    its result line into a fresh log; print the log's path and return at once."""
    sys.path.insert(0, str(REPO / "tools/props/cloud"))
    import detached
    log = detached.log_path_for("score-run")
    command = [sys.executable, detached.__file__, "--log", str(log), "--outputs",
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


def main(argv=None):
    options = parse(argv)
    if options.command == "images":
        publish(options.kind)
        return
    if getattr(options, "detach", False):
        detach(sys.argv)
        return
    runner = stages.runner(world=stages.WORLDS[options.world]())
    places, whole = options.place or stages.places(runner.world), not options.place
    if options.command == "run":
        runner.drive(places, say=lambda line: print(line, flush=True), jobs=options.jobs, whole=whole,
                     only=options.stage)
    lines = runner.lines(places, whole, options.stage)
    for line, (state, nodes) in lines.items():
        print(f"{line}: {state}")
        if options.command == "status":
            print("\n".join(f"  {node}: {node_state}" for node, node_state in nodes.items()))
    if options.command == "run" and any(state != "done" for state, _ in lines.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
