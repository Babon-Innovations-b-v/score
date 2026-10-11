"""The runner's commands over the stage table, on world 1 and the framework's store ($PROPS_HOME/store).

    .venv/bin/python -m score.stages status <place> [<place> ...]   # each node: blocked, to run and why, or its answer
    .venv/bin/python -m score.stages run <place> [<place> ...]      # runs only nodes with no output for their key
    .venv/bin/python -m score.stages run                            # the world's own nodes only (terrain)
    .venv/bin/python -m score.stages why <node>                     # its records back through what it read

Terrain spends (its pictures and their depth in the cloud). A paid stage runs once the runner clears it (its inputs
passed, the month's ceiling has room for its estimate: score.adapters.compute); no one is asked. Passing outputs that
got no worse are accepted by the runner; the owner rejects any from his terminal (score.review reject).
"""
import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from score import stages  # noqa: E402


def parse(argv):
    parser = argparse.ArgumentParser(prog="score.stages", description=__doc__.split("\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("status", "run"):
        commands.add_parser(name).add_argument("places", nargs="*")
    commands.add_parser("why").add_argument("node")
    return parser.parse_args(argv)


def main(argv=None):
    options = parse(argv)
    runner = stages.runner()
    if options.command == "why":
        print("\n".join(runner.why(options.node)))
        return
    found = runner.run(options.places) if options.command == "run" else runner.status(options.places)
    for node, state in found.items():
        print(f"{node}: {state}")


if __name__ == "__main__":
    main()
