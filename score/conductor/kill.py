"""The owner's kill switch: one cockpit click stops every run, deletes every parked paid machine and latches the
conductor free only until his second click clears it.

    report = kill.stop_all(asked_by, words)      # the owner's process only
    kill.allow_paid(asked_by, words)             # his second click
    report = kill.stop_batch(asked_by, words)    # the run monitor's Stop this batch: the same, with no latch

stop_all writes the latch first (FREE_ONLY_LATCH holding SCORE_FREE_ONLY=1: every `score` command reads it at its
start, and a unit may read it as an EnvironmentFile), so nothing started meanwhile can spend, and takes back a resize's
mark (so no run reads its SIGTERM as the resize's and waits to be resumed); then SIGTERM to every
live run (each claim in runs/active.json, and every running entry whose process lives): with the machine up a run
registers itself `stopped` and is never resumed unasked, and passes the stop to its group, so each batch deletes its
own machines; then every waiting run is marked stopped and its process ended; then every open warm pool is closed and
its collector ended (pool.close_all), so none orders a card in place of the ones released next; then every parked
machine, a pool's idle cards with them, is deleted through park.py's release (its ledger line with it); then every
process still working in the frozen copy of a run that is no longer live is ended (leftovers: 2026-10-26, six
processes of a stopped benchmark run worked on in its copy for an hour, held the checkout from score-update, and a
second stop found no run to stop); a run just signalled ends its own copy's processes as it removes it
(frozen.remove_owned). Its report is kept in $PROPS_HOME/conductor/kill-<time>.json and returned. Both are refused in
an agent's process: the barrier the store's owner areas use.
"""
import datetime
import json
import os
import pathlib
import signal
import sys

from score import conductor
from score.conductor import size
from score.graph import frozen, runs
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


def stop_batch(asked_by, words):
    """The run monitor's Stop this batch, in the owner's process only: stop_everything's runs, pools and parked
    machines with no latch, so the next Buy needs no Allow paid work again (owner, 2026-10-25); its report."""
    refuse_agent("stopping the batch")
    return stop_everything(asked_by, words, latched=False)


def agent_stop_batch(words):
    """Stop this batch from an agent's process (owner, 2026-10-25: "this is also something u should just do urself"):
    stop_everything's runs, pools and parked machines with no latch, asked by an agent with its reason; stopping only
    ends spending, so it is the one money action an agent may take. Its report."""
    if not str(words or "").strip():
        raise ValueError("an agent's stop names its reason")
    return stop_everything("agent", words, latched=False)


def stop_everything(asked_by, words, folder=None, parked=None, release=None, report_folder=None, pools=None,
                    close_pools=None, latched=True, frozen_folder=None):
    """The kill switch's work, with no barrier of its own (stop_all's is the agents' refusal): the latch (unless not
    `latched`: Stop this batch), every live run, every waiting run, every open warm pool, every parked machine, every
    process left in the copy of a run gone; its report."""
    folder = pathlib.Path(folder or runs.RUNS)
    at = now()
    report = {"at": at, "by": asked_by, "words": words,
              "free_only": str(latch(asked_by, words, at)) if latched else None,
              "runs": [], "waiting": [], "pools": [], "parked": [], "errors": []}
    conductor.RESIZING.unlink(missing_ok=True)  # the SIGTERMs below are the owner's stop, never a resize's
    live, working = live_runs(folder), frozen.users(frozen_folder)
    stopping = {working[pid] for pid in live if pid in working}  # each ends its own copy's processes (remove_owned)
    for pid in live:
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
    report["leftovers"] = frozen.end(leftovers(frozen_folder, stopping))
    keep(report, f"{'kill' if latched else 'batch-stop'}-{at.replace(':', '')}.json", report_folder)
    return report


def leftovers(frozen_folder, stopping, holds_folder=None):
    """The pids still working in the copy of a run no longer live, found as clean-frozen and the carry find them
    (disk.working: a working folder in it, SCORE_FROZEN naming it, its path on the command line; frozen.users read
    only the first, 2026-11-05: two processes held a stopped free run's copy and every carry refused as 'a run is
    live' while stop-batch found none), never one of a run being stopped now (`stopping`: it ends its own), nor one a
    run is still starting in (starting: it has not registered yet), nor the process holding a sync pass
    (conductor.holding's sync-pass-<pid>, whose own steps are its to end)."""
    from score.conductor import disk
    folder = pathlib.Path(frozen_folder or frozen.FOLDER)
    passes = {int(name.rpartition("-")[2]) for name in conductor.holds(holds_folder)
              if name.startswith(size.PASS_HOLD) and name.rpartition("-")[2].isdigit()}
    busy = disk.working(folder)
    spared = set(stopping) | starting(folder, busy)
    return sorted({pid for copy, pids in busy.items() if copy not in spared for pid in pids if pid not in passes})


def starting(folder, busy):
    """The copies in `busy` ({copy name: [pid]}) a `score run` is still starting in, so in no registry yet: made under
    disk.YOUNG_SECONDS ago, and a process in it started with the owner's mark (SCORE_FROZEN_OWNER=1, SCORE_FROZEN naming
    it: frozen.enter's, or the detached run it hands the copy on to). 2026-11-05: stop-batch ended three detached free
    runs 2.1 minutes in, each still working out its claim. A run's own children start without the mark, so a gone
    run's are still left over."""
    from score.conductor import disk
    folder = pathlib.Path(folder)
    return {name for name, pids in busy.items()
            if young(folder, name, disk.YOUNG_SECONDS) and any(owns(folder, name, pid) for pid in pids)}


def young(folder, name, seconds):
    """Whether the copy `name` (or its home) under `folder` changed under `seconds` ago; False when neither is there."""
    from score.conductor import disk
    try:
        return disk.age(folder, name) < seconds
    except ValueError:  # neither the copy nor its home is there: a copy removed under its processes
        return False


def owns(folder, name, pid):
    """Whether the process `pid` started with the owner's mark for the copy `name` under `folder`."""
    from score.conductor import disk
    try:
        words = disk.said_by(pathlib.Path(f"/proc/{pid}")).decode(errors="replace").split("\0")
    except FileNotFoundError:
        return False  # it ended meanwhile
    named = {disk.copy_named(folder, word.partition("=")[2]) for word in words if word.startswith(f"{frozen.FROZEN}=")}
    return f"{frozen.OWNER}=1" in words and name in named


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
