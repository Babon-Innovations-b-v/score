"""The ship-kit stage's commands, on world 1 and the framework's store ($PROPS_HOME/store).

    .venv/bin/python -m score.stages.ship_kits status <place> [<place> ...]
    .venv/bin/python -m score.stages.ship_kits run <place> [<place> ...]
    .venv/bin/python -m score.stages.ship_kits why ship_kit@<place>
"""
import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))

from score.stages import ship_kits  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(prog="score.stages.ship_kits", description=__doc__.split("\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("status", "run"):
        commands.add_parser(name).add_argument("places", nargs="+")
    commands.add_parser("why").add_argument("node")
    options = parser.parse_args(argv)
    runner = ship_kits.runner()
    if options.command == "why":
        print("\n".join(runner.why(options.node)))
        return
    found = runner.run(options.places) if options.command == "run" else runner.status(options.places)
    for node, state in found.items():
        print(f"{node}: {state}")


if __name__ == "__main__":
    main()
