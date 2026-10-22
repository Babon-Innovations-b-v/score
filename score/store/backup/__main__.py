"""`python -m score.store.backup <command>`: one summary line, the record in $PROPS_HOME/logs/backup-<stamp>.json
(the package docstring has the commands). Exits 1 when the command failed or was refused."""
import argparse
import sys
import time

from score.store import PROPS_HOME
from score.store import backup as backups
from score.store.backup import _core


def parse(argv):
    parser = argparse.ArgumentParser(prog="score.store.backup", description=__doc__.split("\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("backup", help="one snapshot of $PROPS_HOME")
    commands.add_parser("forget", help="drop snapshots past the policy, then prune")
    checking = commands.add_parser("check", help="restic check; a data read when one is due")
    checking.add_argument("--read-data", action="store_true", default=None, help="read a 5%% subset of the data now")
    restoring = commands.add_parser("restore", help="a restore drill into an empty folder")
    restoring.add_argument("--to", required=True, help="an empty scratch folder outside the home")
    restoring.add_argument("--snapshot", default="latest")
    listing = commands.add_parser("manifest", help="a home's manifest")
    listing.add_argument("home", nargs="?", default=str(PROPS_HOME))
    moving = commands.add_parser("migrate", help="the one-time move of the store from the PC (the owner's own)")
    mode = moving.add_mutually_exclusive_group(required=True)
    for name in backups.MIGRATIONS:
        mode.add_argument(f"--{name}", dest="mode", action="store_const", const=name)
    return parser.parse_args(argv)


def run(options):
    """Run one command; (its log kind, its outcome)."""
    if options.command == "backup":
        return "backup", backups.backup(PROPS_HOME)
    if options.command == "forget":
        return "forget", backups.forget()
    if options.command == "check":
        return backups.check(PROPS_HOME, read_data=options.read_data)
    if options.command == "restore":
        return "restore", backups.restore(options.to, home=PROPS_HOME, snapshot=options.snapshot)
    if options.command == "manifest":
        return "manifest", backups.manifest(options.home, log_home=PROPS_HOME)
    return f"migrate-{options.mode}", backups.migrate(options.mode, PROPS_HOME)


def summary(kind, record, path):
    """The one line a command prints."""
    said = "ok" if record["ok"] else f"FAILED: {record['error']}"
    counts = [f"{name} {record[name]}" for name in ("snapshot", "files", "bytes") if record[name] is not None]
    counts.append(f"{record['seconds']} s")
    return f"backup {kind}: {said}; {', '.join(counts)}; detail {path}"


def main(argv):
    options = parse(argv)
    start = time.monotonic()
    kind = options.command if options.command != "migrate" else f"migrate-{options.mode}"
    try:
        kind, outcome = run(options)
        error = None
    except (backups.Refused, backups.Mismatch, backups.ResticFailed) as failure:
        outcome = {"detail": {"differences": failure.differences}} if isinstance(failure, backups.Mismatch) else {}
        error = str(failure)
    record = _core.log_record(kind, outcome, time.monotonic() - start, error)
    path = _core.write_log(PROPS_HOME, record)
    print(summary(kind, record, path))
    return 0 if record["ok"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
