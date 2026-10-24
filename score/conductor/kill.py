"""The owner's kill switch: one cockpit click stops every run, deletes every parked paid machine and latches the
conductor free only until his second click clears it.

    report = kill.stop_all(asked_by, words)      # the owner's process only
    kill.allow_paid(asked_by, words)             # his second click

stop_all writes the latch first (FREE_ONLY_LATCH holding SCORE_FREE_ONLY=1: every `score` command reads it at its
start, and a unit may read it as an EnvironmentFile), so nothing started meanwhile can spend, and takes back a resize's
mark (so no run reads its SIGTERM as the resize's and waits to be resumed); then SIGTERM to every
live run (each claim in runs/active.json, and every running entry whose process lives): with the machine up a run
registers itself `stopped` and is never resumed unasked, and passes the stop to its group, so each batch deletes its
own machines; then every waiting run is marked stopped and its process ended; then every open warm pool is closed and
its collector ended (pool.close_all), so none orders a card in place of the ones released next; then every parked
machine, a pool's idle cards with them, is deleted through park.py's release (its ledger line with it). Its report is kept in $PROPS_HOME/conductor/kill-<time>.json and
returned. Both are refused in an agent's process: the barrier the store's owner areas use.
"""
import datetime
import json
import os
import pathlib
import signal
import sys

from score import conductor
from score.conductor import size
from score.graph import runs
from score.store import running_under_agent

CLOUD_TOOLS = pathlib.Path(__file__).resolve().parents[2] / "tools/cloud"


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def one_line(text):
    """The owner's words on one line (they go into an environment file)."""
    return " ".join(str(text or "").split())


def refuse_agent(what):
    """PermissionError in a process an agent started."""
    if running_under_agent():
        raise PermissionError(f"{what}: only the owner's click does this; an agent's process cannot")


def latch(asked_by, words, at, path=None):
    """Write the free-only latch whole; its path."""
    path = pathlib.Path(path or conductor.FREE_ONLY_LATCH)
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(f"{path.name}.{os.getpid()}.partial")
    partial.write_text(f"# the kill switch of {at} by {one_line(asked_by)}: {one_line(words)}\n"
                       f"{conductor.FREE_ONLY}=1\n")
    os.replace(partial, path)
    return path


def live_runs(folder):
    """The pids of every live run: its claim, or its running entry whose process is there."""
    with runs.claims_locked(folder) as claims:
        pids = {int(pid) for pid in claims}
    pids |= {entry["pid"] for entry in runs.entries(folder).values()
             if entry.get("state") == runs.RUNNING and entry.get("boot") == runs.boot_id()
             and size.entry_alive(entry)}
    return sorted(pids - {os.getpid()})


def park_release():
    """park.py's release, imported from the cloud tools."""
    if str(CLOUD_TOOLS) not in sys.path:
        sys.path.insert(0, str(CLOUD_TOOLS))
    import park
    return park.release


def pools_closer():
    """pool.py's close_all, imported from the cloud tools."""
    if str(CLOUD_TOOLS) not in sys.path:
        sys.path.insert(0, str(CLOUD_TOOLS))
    import pool
    return pool.close_all


def open_pools(folder):
    """Whether any run's warm pool is still open (a plan and no closed mark)."""
    folder = pathlib.Path(folder)
    return folder.is_dir() and any(not (plan.parent / "closed").exists() for plan in folder.glob("*/plan.json"))


def parked_records(folder):
    """Every parked machine's record."""
    folder = pathlib.Path(folder)
    return [json.loads(path.read_text()) for path in sorted(folder.glob("*.json"))] if folder.is_dir() else []


def stop_all(asked_by, words):
    """The kill switch (the module's docstring), in the owner's process only; its report."""
    refuse_agent("the kill switch")
    return stop_everything(asked_by, words)


def stop_everything(asked_by, words, folder=None, parked=None, release=None, report_folder=None, pools=None,
                    close_pools=None):
    """The kill switch's work, with no barrier of its own (stop_all's is the agents' refusal): the latch, every live
    run, every waiting run, every open warm pool, every parked machine; its report."""
    folder = pathlib.Path(folder or runs.RUNS)
    at = now()
    report = {"at": at, "by": asked_by, "words": words, "free_only": str(latch(asked_by, words, at)),
              "runs": [], "waiting": [], "pools": [], "parked": [], "errors": []}
    conductor.RESIZING.unlink(missing_ok=True)  # the SIGTERMs below are the owner's stop, never a resize's
    for pid in live_runs(folder):
        try:
            os.kill(pid, signal.SIGTERM)
            report["runs"].append(pid)
        except ProcessLookupError:
            pass
    for path, entry in runs.waiting(folder).items():
        size.stop_waiting(path, say=lambda line: None)
        report["waiting"].append(entry["id"])
    close_pools = close_pools or (pools_closer() if open_pools(pools or size.POOLS) else None)
    if close_pools:
        try:
            report["pools"] = close_pools()
        except Exception as error:  # noqa: BLE001 - the parked machines are still released; the report names it
            report["errors"].append(f"pools: {type(error).__name__}: {error}")
    records = parked_records(parked or size.PARKED)
    release = release or (park_release() if records else None)
    for record in records:
        try:
            release(record["id"], record["zone"], record["token"])
            report["parked"].append(record["id"])
        except Exception as error:  # noqa: BLE001 - each machine is tried; the report names what failed
            report["errors"].append(f"parked {record['id']}: {type(error).__name__}: {error}")
    keep(report, f"kill-{at.replace(':', '')}.json", report_folder)
    return report


def allow_paid(asked_by, words):
    """The owner's second click (the cockpit's Allow paid work again), in his process only: unlatch; its record."""
    refuse_agent("clearing the free-only latch")
    return unlatch(asked_by, words)


def unlatch(asked_by, words, path=None, report_folder=None):
    """Remove the latch, kept as a record ({at, by, words, was_held}), with no barrier of its own (allow_paid's); the
    record."""
    path = pathlib.Path(path or conductor.FREE_ONLY_LATCH)
    held = path.is_file()
    path.unlink(missing_ok=True)
    at = now()
    record = {"at": at, "by": asked_by, "words": words, "was_held": held}
    keep(record, f"free-only-cleared-{at.replace(':', '')}.json", report_folder)
    return record


def keep(record, name, folder=None):
    """Write one record into the conductor's folder; its path."""
    path = pathlib.Path(folder or conductor.HOME) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=1))
    return path
