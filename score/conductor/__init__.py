"""The conductor: the one always-on cloud machine of our own that holds the store and drives every batch (owner,
2026-10-22: "if the goal is for all that to run the cloud, u have time to build it now so why wait"). This package is
its operations: what it does differently from the PC it replaces, and nothing else. Off a conductor every function
here answers "not a conductor" and the runner behaves exactly as on the PC.

    python -m score.conductor health --write   # $PROPS_HOME/health.json, the minute timer's (health.py)
    python -m score.conductor size             # grow for a waiting run, shrink when idle (size.py, score-size.timer)
    python -m score.conductor dry              # the free end-to-end check, one line, detail in a file (dry.py)

A machine is a conductor when $PROPS_HOME/machine.json is there (written by the store's move, score/store/backup
migrate --onto-conductor, over the sizes record tools/cloud/conductor/machine.py up piped: its name, zone, its two
sizes and their cores, its project) and SCORE_CONDUCTOR_SIZE_URL names its size
function. Its idle size runs sync, the listener and price passes; a run asking for more jobs than the machine has
cores registers as waiting for size (graph/runs.py WAITING), the size function grows the same machine (off, type
changed, on), and `score resume` starts the run at the boot on the batch size (size.py).

The kill switch's latch (kill.py) is a file, $PROPS_HOME/conductor/free-only, holding `SCORE_FREE_ONLY=1`: a unit can
read it as an EnvironmentFile, and every `score` command reads it at its start (apply_free_only), so a run and every
node and paid point under it run free only (tools/cloud/ledger.py FreeOnly) until the owner clears it.

The conductor bills in a Scaleway project of its own (CONDUCTOR_PROJECT, by name), never the batch project, so its
hourly bill never enters guard.spent_since (score/adapters/compute/guard.py refuses every paid run if the two names
are ever the same: project_refusal).
"""
import contextlib
import fcntl
import json
import os
import pathlib
import time

from score.store import PROPS_HOME

HOME = PROPS_HOME / "conductor"
MACHINE = PROPS_HOME / "machine.json"
HEALTH = PROPS_HOME / "health.json"
FREE_ONLY_LATCH = HOME / "free-only"
HOLDS = HOME / "holds"  # one locked file per piece of work the size timer must not cut (holding)
FREE_ONLY = "SCORE_FREE_ONLY"  # tools/cloud/ledger.py FREE_ONLY: every paid point raises FreeOnly under it
SIZE_URL = "SCORE_CONDUCTOR_SIZE_URL"
# The conductor's own Scaleway project, by name; the batch project is SCORE_SCALEWAY_PROJECT (backends/scaleway.py).
CONDUCTOR_PROJECT = os.environ.get("SCORE_CONDUCTOR_PROJECT", "score-conductor")
BATCH_PROJECT_DEFAULT = "farm-factory"  # backends/scaleway.py PROJECT_NAME's default


def machine(path=None):
    """The conductor's own record ({name, zone, idle_type, batch_type, idle_cores, batch_cores, project}), or None
    when this machine is not a conductor (no record, or no size function named)."""
    path = pathlib.Path(path or MACHINE)
    if not path.is_file() or not os.environ.get(SIZE_URL):
        return None
    return json.loads(path.read_text())


@contextlib.contextmanager
def holding(name, folder=None):
    """Hold the machine at its size while the block runs (a sync pass, a request the listener answers, a film
    preview, a reading, a free check): an exclusive lock on HOLDS/<name>-<pid>.lock, which the kernel lets go when
    the process ends however it ends. Nothing off a conductor."""
    if folder is None and machine() is None:
        yield
        return
    folder = pathlib.Path(folder or HOLDS)
    folder.mkdir(parents=True, exist_ok=True)
    path, partial = folder / f"{name}-{os.getpid()}.lock", folder / f"{name}-{os.getpid()}.partial"
    with partial.open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        os.replace(partial, path)  # locked before holds() can see it, so never taken for a dead holder's
        try:
            yield
        finally:
            path.unlink(missing_ok=True)


def holds(folder=None):
    """The names of the holds a live process keeps now; a file no process locks (its holder killed) is removed."""
    folder = pathlib.Path(folder or HOLDS)
    held = []
    for path in sorted(folder.glob("*.lock")) if folder.is_dir() else []:
        with path.open("a") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                held.append(path.stem)
                continue
            path.unlink(missing_ok=True)
    return held


def cores():
    """This machine's cores now."""
    return os.cpu_count() or 1


def meminfo_gb(field, meminfo=pathlib.Path("/proc/meminfo")):
    """One /proc/meminfo field (MemTotal, MemAvailable) in GB."""
    for line in meminfo.read_text().splitlines():
        name, _, value = line.partition(":")
        if name == field:
            return int(value.split()[0]) / 1024 ** 2
    raise KeyError(f"{field} is not in {meminfo}")


def default_jobs(fallback):
    """The nodes a run drives at once when --jobs is not given: every core on a conductor, else `fallback`."""
    return cores() if machine() else fallback


def free_only():
    """Whether the owner's kill switch latch holds (the file is there)."""
    return FREE_ONLY_LATCH.is_file()


def apply_free_only():
    """Make this process and everything it starts free only while the latch holds; whether it does."""
    if free_only():
        os.environ[FREE_ONLY] = "1"
        return True
    return False


RESIZING = HOME / "resizing.json"  # written by the size timer just before it asks for a grow or a shrink
RESIZE_WINDOW = 15 * 60  # seconds a resize's power-off may take to reach a run after the ask


def resizing(now=None, registered=None):
    """Whether the size timer asked for a resize within RESIZE_WINDOW: a SIGTERM now is the resize's shutdown, never
    the owner's stop (graph/runs.py stopped_by), even when systemd cannot say it is stopping. A run `registered`
    (seconds since the epoch) after the ask is not the resize's: the timer asks only while no run is live, so one
    started since (his Buy after a resize the function then refused) is stopped by its owner, never resumed unasked."""
    if not RESIZING.is_file():
        return False
    asked = json.loads(RESIZING.read_text()).get("at", 0)
    if registered is not None and registered > asked + 1:  # entries keep whole seconds
        return False
    return 0 <= (now if now is not None else time.time()) - asked <= RESIZE_WINDOW


def batch_project():
    """The name of the project the runner rents in and whose bill the stop line reads."""
    return os.environ.get("SCORE_SCALEWAY_PROJECT", BATCH_PROJECT_DEFAULT)


def project_refusal(path=None):
    """Why no paid run may clear while the batch project is the conductor's own (its hourly bill would count as
    batch spend and eat the stop line's buffer), or None. The machine's record is read whether or not the size
    function is named: a conductor whose env file lost SCORE_CONDUCTOR_SIZE_URL still bills in its own project."""
    path = pathlib.Path(path or MACHINE)
    record = json.loads(path.read_text()) if path.is_file() else {}
    if batch_project() in {CONDUCTOR_PROJECT, record.get("project")}:
        return (f"refused: SCORE_SCALEWAY_PROJECT is {batch_project()}, the conductor's own project; the batch "
                "project must be another, so the conductor's bill never counts as batch spend")
    return None
