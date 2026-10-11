"""The review commands. `page` is anyone's; `accept` and `spend` are the owner's alone, typed in his own terminal.

    .venv/bin/python -m score.review page <node> [--key <key>]
    .venv/bin/python -m score.review accept <node> <output> [--reason "..."] [--worse "why it may be worse"]
    .venv/bin/python -m score.review spend <node> <key> <euros>

`accept` and `spend` refuse to run without a terminal at both ends, so a script or an agent's shell cannot give them;
the accept guard hook (.claude/hooks/accept_guard.py) also blocks agents from running them or writing the store's
accepts. On one machine under YOLO this is a barrier, not a lock: every accept names who gave it and when.
"""
import argparse
import getpass
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from score import review  # noqa: E402
from score.store import Store  # noqa: E402


def owner_at_terminal():
    """Refuse unless a person is at a terminal on both ends of this command."""
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        raise SystemExit("only the owner accepts or says yes to a spend, typed in his own terminal")


def parse(argv):
    parser = argparse.ArgumentParser(prog="score.review", description=__doc__.split("\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    shown = commands.add_parser("page")
    shown.add_argument("node")
    shown.add_argument("--key")
    accepting = commands.add_parser("accept")
    accepting.add_argument("node")
    accepting.add_argument("output")
    accepting.add_argument("--reason", default="")
    accepting.add_argument("--worse")
    spending = commands.add_parser("spend")
    spending.add_argument("node")
    spending.add_argument("key")
    spending.add_argument("euros", type=float)
    return parser.parse_args(argv)


def main(argv=None):
    options = parse(argv)
    store = Store.default()
    if options.command == "page":
        print(review.page(store, options.node, options.key))
        return
    owner_at_terminal()
    if options.command == "accept":
        try:
            written = review.accept(store, options.node, options.output, getpass.getuser(), options.reason,
                                    options.worse)
        except review.Refused as refusal:
            raise SystemExit(f"refused: {refusal}")
        print(f"accepted {written['node']} {written['output']}")
        return
    review.spend(store, options.node, options.key, options.euros, getpass.getuser())
    print(f"yes to {options.node} {options.key} at EUR {options.euros}")


if __name__ == "__main__":
    main()
