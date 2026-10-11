"""The review commands. `page` is anyone's; `accept`, `waive` and `spend` are the owner's alone, typed in his own
terminal.

    .venv/bin/python -m score.review page <node> [--key <key>]
    .venv/bin/python -m score.review accept <node> <output> [--reason "..."] [--worse "why it may be worse"]
    .venv/bin/python -m score.review waive <node> <key> <check> --reason "why this check is wrong here"
    .venv/bin/python -m score.review spend <node> <key> <euros>

`accept`, `waive` and `spend` refuse to run without a terminal at both ends; the store refuses their writes in any
process an agent started (score/store), and the accept guard hook (.claude/hooks/accept_guard.py) blocks agents from
running them or writing the store's accepts by other routes. On one machine under YOLO this is a barrier, not a
lock: an agent set on getting round it can, and every accept names who gave it and when.
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
        raise SystemExit("only the owner accepts, waives or says yes to a spend, typed in his own terminal")


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
    waiving = commands.add_parser("waive")
    waiving.add_argument("node")
    waiving.add_argument("key")
    waiving.add_argument("check")
    waiving.add_argument("--reason", required=True)
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
    if options.command == "waive":
        try:
            review.waive(store, options.node, options.key, options.check, getpass.getuser(), options.reason)
        except review.Refused as refusal:
            raise SystemExit(f"refused: {refusal}")
        print(f"waived {options.check} on {options.node} {options.key}")
        return
    review.spend(store, options.node, options.key, options.euros, getpass.getuser())
    print(f"yes to {options.node} {options.key} at EUR {options.euros}")


if __name__ == "__main__":
    main()
