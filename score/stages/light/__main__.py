"""The lightkit row's commands (kit.py: the square's proscenium and floodlight towers), on world 1 and the
framework's store ($PROPS_HOME/store). The place rows (light-layer, light-passes, light) are the stage table's:
`python -m score run world1 --place <place> --stage light --detach`.

    .venv/bin/python -m score.stages.light status lightkit
    .venv/bin/python -m score.stages.light run lightkit
    .venv/bin/python -m score.stages.light why lightkit
"""
import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))

from score import graph  # noqa: E402
from score.stages.light.kit import KIT  # noqa: E402
from score.store import Store  # noqa: E402


def run_nodes(runner, nodes, command):
    """Run or report each named node alone (`stage` or `stage@place`), in the order given."""
    for node in nodes:
        name, _, place = node.partition("@")
        stage = runner.stages[name]
        found = runner.run_node(stage, place or None) if command == "run" else runner.node_status(stage, place or None)
        print(f"{node}: {found}", flush=True)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="score.stages.light", description=__doc__.split("\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("status", "run"):
        commands.add_parser(name).add_argument("nodes", nargs="+")
    commands.add_parser("why").add_argument("node")
    options = parser.parse_args(argv)
    from score.stages import world1
    runner = graph.Runner((KIT,), world1(), Store.default())
    if options.command == "why":
        print("\n".join(runner.why(options.node)))
        return
    run_nodes(runner, options.nodes, options.command)


if __name__ == "__main__":
    main()
