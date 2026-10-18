"""The late-bake stage's commands, on environment 1 and the framework's store ($PROPS_HOME/store).

    .venv/bin/python -m score.stages.late_bake status <room> [<room> ...]
    .venv/bin/python -m score.stages.late_bake run <room> [<room> ...]
    .venv/bin/python -m score.stages.late_bake why late_bake@<room>
"""
import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))

from score.stages import late_bake  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(prog="score.stages.late_bake", description=__doc__.split("\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("status", "run"):
        commands.add_parser(name).add_argument("rooms", nargs="+")
    commands.add_parser("why").add_argument("node")
    options = parser.parse_args(argv)
    runner = late_bake.runner()
    if options.command == "why":
        print("\n".join(runner.why(options.node)))
        return
    found = runner.run(options.rooms) if options.command == "run" else runner.status(options.rooms)
    for node, state in found.items():
        print(f"{node}: {state}")


if __name__ == "__main__":
    main()
