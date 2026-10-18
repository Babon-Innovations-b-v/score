"""The review commands. `page` is anyone's; `reject`, `accept`, `waive`, `spend` and `stop` are the owner's alone, typed
in his own terminal. The runner accepts a passing output that got no worse by itself; none of these is needed for a
run.

    .venv/bin/python -m score.review page <node> [--key <key>]
    .venv/bin/python -m score.review reject <node> <output> --reason "what is wrong with it"
    .venv/bin/python -m score.review accept <node> <output> [--reason "..."] [--worse "why it may be worse"]
    .venv/bin/python -m score.review waive <node> <key> <check> --reason "why this check is wrong here"
    .venv/bin/python -m score.review spend <node> <key> <euros>   # the override, for a run outside the runner
    .venv/bin/python -m score.review stop <world> <euros> --reason "what it is for"   # his money yes: the stop line

`stop` is the owner's money yes for a world: it writes the world's new stop line itself, in the same step, so no
decision waits on anyone to copy it into a guard and no older line outlives it (score/adapters/compute/guard.py; the
runner refuses a paid job that would pass it before it starts). A world's first line counts its spend from now.

`reject`, `accept`, `waive`, `spend` and `stop` refuse to run without a terminal at both ends; the store refuses their
writes in any process an agent started (score/store; a stop line, guard.set_line), and the accept guard hook (.claude/hooks/accept_guard.py) blocks
agents from running them or writing those areas of the store by other routes. On one machine under YOLO this is a
barrier, not a lock: an agent set on getting round it can, and every accept names who gave it and when.
"""
import argparse
import getpass
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from score import graph, review  # noqa: E402
from score.adapters import compute  # noqa: E402
from score.adapters.compute import guard  # noqa: E402
from score.store import Store  # noqa: E402


def owner_at_terminal():
    """Refuse unless a person is at a terminal on both ends of this command."""
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        raise SystemExit("only the owner rejects, accepts, waives or says yes to a spend or a stop line, typed in his "
                         "own terminal")


def parse(argv):
    parser = argparse.ArgumentParser(prog="score.review", description=__doc__.split("\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    shown = commands.add_parser("page")
    shown.add_argument("node")
    shown.add_argument("--key")
    rejecting = commands.add_parser("reject")
    rejecting.add_argument("node")
    rejecting.add_argument("output")
    rejecting.add_argument("--reason", required=True)
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
    stopping = commands.add_parser("stop")
    stopping.add_argument("world")
    stopping.add_argument("euros", type=float)
    stopping.add_argument("--reason", required=True)
    return parser.parse_args(argv)


def set_stop(store, world, euros, reason):
    """The owner's money yes: the world's new stop line, written now; the record. A first line counts the world's
    spend from the books as they stand (the bill read only then)."""
    baseline = None if guard.current(store, world) else compute.books_now()
    try:
        return guard.set_line(store, world, euros, reason, getpass.getuser(), graph.now(), baseline)
    except PermissionError as refusal:
        raise SystemExit(f"refused: {refusal}")


def main(argv=None):
    options = parse(argv)
    store = Store.default()
    if options.command == "page":
        print(review.page(store, options.node, options.key))
        return
    owner_at_terminal()
    if options.command == "reject":
        try:
            review.reject(store, options.node, options.output, getpass.getuser(), options.reason)
        except review.Refused as refusal:
            raise SystemExit(f"refused: {refusal}")
        print(f"rejected {options.node} {options.output}; accepted now: {store.accepted(options.node) or 'none'}")
        return
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
    if options.command == "stop":
        line = set_stop(store, options.world, options.euros, options.reason)
        was = f", was EUR {line['before']:.2f}" if line["before"] is not None else ", the world's first"
        print(f"stop line of {line['world']}: EUR {line['euros']:.2f}{was}; spend counted from "
              f"{line['baseline']['month']}'s bill of EUR {line['baseline']['bill']:.2f}")
        return
    review.spend(store, options.node, options.key, options.euros, getpass.getuser())
    print(f"yes to {options.node} {options.key} at EUR {options.euros}")


if __name__ == "__main__":
    main()
