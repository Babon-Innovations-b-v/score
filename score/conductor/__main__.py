"""The conductor's commands (score/conductor/__init__.py has the package's map).

    python -m score.conductor health [--write]   # the health as JSON, or written to $PROPS_HOME/health.json
    python -m score.conductor size               # one pass of the size timer: grow, shrink or nothing
    python -m score.conductor dry                # the free end-to-end check: one line, its detail in a file
"""
import argparse
import json
import sys

from score import conductor


def main(argv=None):
    parser = argparse.ArgumentParser(prog="score.conductor", description=__doc__.split("\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("health").add_argument("--write", action="store_true", help=f"write {conductor.HEALTH}")
    commands.add_parser("size")
    commands.add_parser("dry")
    options = parser.parse_args(argv)
    conductor.apply_free_only()
    if options.command == "health":
        from score.conductor import health
        found = health.read()
        print(f"health: written {health.write(found)}" if options.write else json.dumps(found, indent=1))
    elif options.command == "size":
        from score.conductor import size
        size.tick()
    else:
        from score.conductor import dry
        line, code = dry.start()
        print(line, flush=True)
        sys.exit(code)


if __name__ == "__main__":
    main()
