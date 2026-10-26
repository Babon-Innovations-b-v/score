"""The conductor's commands (score/conductor/__init__.py has the package's map).

    python -m score.conductor health [--write]   # the health as JSON, or written to $PROPS_HOME/health.json
    python -m score.conductor size               # one pass of the size timer: grow, shrink or nothing
    python -m score.conductor dry                # the free end-to-end check: one line, its detail in a file
    python -m score.conductor logs [--lines N]   # logs.tails: run logs, fault reports, unit journals, boot logs, as text
    python -m score.conductor disk               # disk.report: free room and the biggest folders, the rest in a file
    python -m score.conductor clean-frozen       # disk.clean: remove the frozen copies no run needs, what it freed
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
    commands.add_parser("logs").add_argument("--lines", type=int, default=40, help="the last lines of each")
    commands.add_parser("disk")
    commands.add_parser("clean-frozen")
    options = parser.parse_args(argv)
    conductor.apply_free_only()
    if options.command == "health":
        from score.conductor import health
        found = health.read()
        print(f"health: written {health.write(found)}" if options.write else json.dumps(found, indent=1))
    elif options.command == "logs":
        from score.conductor import logs
        for name, lines in logs.tails(options.lines).items():
            print("\n".join([f"== {name}", *lines]))
    elif options.command == "disk":
        from score.conductor import disk
        summary, biggest = disk.report()
        print("\n".join([summary, *biggest]))
    elif options.command == "clean-frozen":
        clean_frozen()
    elif options.command == "size":
        from score.conductor import size
        size.tick()
    else:
        from score.conductor import dry
        with conductor.holding("dry"):
            line, code = dry.start()
        print(line, flush=True)
        sys.exit(code)


def clean_frozen():
    """disk.clean, its summary line last; exit 1 when it cannot tell which copies are dead or one failed."""
    from score.conductor import disk
    try:
        done = disk.clean()
    except disk.Unprovable as why:
        print(f"clean-frozen: refused, nothing removed: {why}", flush=True)
        sys.exit(1)
    print(f"clean-frozen: removed {len(done['removed'])}, kept {len(done['kept'])}, failed {len(done['failed'])}; "
          f"freed {done['freed_gb']} GB, {disk.free_gb():.1f} GB free", flush=True)
    sys.exit(1 if done["failed"] else 0)


if __name__ == "__main__":
    main()
