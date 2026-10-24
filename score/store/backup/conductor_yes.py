"""The owner's yes to the conductor's switch, asked in a Claude Code session with its question tool (owner, 2026-10-24:
"no you do all just gimme the confirm question like u do with the 20 eu benchmark ok"), kept like a benchmark grant
(score.adapters.compute.grant_benchmark): his answer and the question quoted, the time, what it allows. One yes lets
an agent's process run tools/cloud/conductor/prepare.sh, `machine.py up` and `machine.py move` (with the move's
migrate steps and the PC home's retirement) once each; a step is marked done only when it ended well, so a refused or
failed step may run again under the same yes. Without an open yes all of them refuse in an agent's process, as before.

    python3 -m score.store.backup.conductor_yes record --answer "<his words>" --question "<the question asked>"
    python3 -m score.store.backup.conductor_yes check <step>    # exit 0 in the owner's process or under an open yes
    python3 -m score.store.backup.conductor_yes done <step>     # in an agent's process: mark it done on that yes

Kept in the framework store: grants/conductor/<id>.json, and grants/conductor-done/<id>/<step>.json (write-once, so a
step is done once). The move passes the yes's id to its migrate steps as SCORE_CONDUCTOR_YES, and the store it lives
in as SCORE_CONDUCTOR_YES_HOME once the PC's home is set aside. A barrier, not a lock: every yes quotes who said it
and when.
"""
import argparse
import datetime
import os
import pathlib
import sys

from score.store import PROPS_HOME, Store, running_under_agent, stamp_key

STEPS = ("prepare", "up", "move")
MONTHLY_EUROS = 90  # `machine.py price`'s always-on figure, rounded, as the question tells him
YESES, DONE = "grants/conductor", "grants/conductor-done"
YES_ID, YES_HOME = "SCORE_CONDUCTOR_YES", "SCORE_CONDUCTOR_YES_HOME"


class Refused(RuntimeError):
    """No yes may be recorded with these arguments."""


def yes_store():
    """The store the yeses live in: the PC's framework store (SCORE_CONDUCTOR_YES_HOME's once the home is set aside)."""
    return Store.in_folder(pathlib.Path(os.environ.get(YES_HOME, PROPS_HOME)) / "store")


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def record(answer, question, store=None):
    """Write the owner's quoted yes {id, purpose, allows, monthly_euros, answer, question, at}; the yes."""
    if not str(answer or "").strip() or not str(question or "").strip():
        raise Refused("a conductor yes quotes the owner's answer and the question he answered, both")
    at = now()
    found = {"id": stamp_key(at), "purpose": "conductor", "allows": list(STEPS), "monthly_euros": MONTHLY_EUROS,
             "answer": str(answer), "question": str(question), "at": at}
    (store or yes_store()).write_once(f"{YESES}/{found['id']}.json", found)
    return found


def is_open(found, step, store):
    """True when the yes `found` is quoted, allows `step`, and that step is not done on it yet."""
    return bool(found and found.get("answer") and found.get("question") and step in found.get("allows", ())
                and not store.objects.exists(f"{DONE}/{found['id']}/{step}.json"))


def open_yes(step, store=None):
    """The newest yes open for `step`, or None."""
    store = store or yes_store()
    for key in sorted(store.objects.keys(f"{YESES}/"), reverse=True):
        found = store.read(key)
        if is_open(found, step, store):
            return found
    return None


def move_allowed(environ=os.environ, store=None):
    """True when SCORE_CONDUCTOR_YES names a yes open for the move (the migrate steps' check in an agent's process)."""
    named = environ.get(YES_ID, "").strip()
    if not named:
        return False
    store = store or yes_store()
    return is_open(store.read(f"{YESES}/{named}.json"), "move", store)


def mark_done(found, step, store=None):
    """Mark `step` done on the yes `found` (write-once: a step is done once)."""
    (store or yes_store()).write_once(f"{DONE}/{found['id']}/{step}.json", {"step": step, "at": now()})


def main(argv):
    made = argparse.ArgumentParser(prog="score.store.backup.conductor_yes", description=__doc__.splitlines()[0])
    commands = made.add_subparsers(dest="command", required=True)
    recording = commands.add_parser("record")
    recording.add_argument("--answer", required=True)
    recording.add_argument("--question", required=True)
    for name in ("check", "done"):
        commands.add_parser(name).add_argument("step", choices=STEPS)
    options = made.parse_args(argv)
    if options.command == "record":
        print(f"conductor yes {record(options.answer, options.question)['id']}: prepare, up and move once each")
        return 0
    if not running_under_agent():  # the owner's own process needs no yes
        return 0
    found = open_yes(options.step)
    if found is None:
        print(f"no open conductor yes for {options.step}: ask the owner first (conductor_yes record)", file=sys.stderr)
        return 1
    if options.command == "done":
        mark_done(found, options.step)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
