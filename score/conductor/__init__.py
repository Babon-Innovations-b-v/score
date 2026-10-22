"""The conductor: the one always-on cloud machine of our own that holds the store and drives every batch (owner,
2026-10-22: "if the goal is for all that to run the cloud, u have time to build it now so why wait"). This package is
its operations: what it does differently from the PC it replaces, and nothing else. Off a conductor every function
here answers "not a conductor" and the runner behaves exactly as on the PC.

    python -m score.conductor health --write   # $PROPS_HOME/health.json, the minute timer's (health.py)
    python -m score.conductor size             # grow for a waiting run, shrink when idle (size.py, score-size.timer)
    python -m score.conductor dry              # the free end-to-end check, one line, detail in a file (dry.py)

A machine is a conductor when $PROPS_HOME/machine.json is there (written by tools/cloud/conductor/machine.py at its
boot: its name, zone, its two sizes and their cores, its project) and SCORE_CONDUCTOR_SIZE_URL names its size
function. Its idle size runs sync, the listener and price passes; a run asking for more jobs than the machine has
cores registers as waiting for size (graph/runs.py WAITING), the size function grows the same machine (off, type
changed, on), and `score resume` starts the run at the boot on the batch size (size.py).

The kill switch's latch (kill.py) is a file, $PROPS_HOME/conductor/free-only, holding `SCORE_FREE_ONLY=1`: a unit can
read it as an EnvironmentFile, and every `score` command reads it at its start (apply_free_only), so a run and every
node and paid point under it run free only (tools/props/cloud/ledger.py FreeOnly) until the owner clears it.

The conductor bills in a Scaleway project of its own (CONDUCTOR_PROJECT, by name), never the batch project, so its
hourly bill never enters guard.spent_since (score/adapters/compute/guard.py refuses every paid run if the two names
are ever the same: project_refusal).
"""
import json
import os
import pathlib
import time

from score.store import PROPS_HOME

HOME = PROPS_HOME / "conductor"
MACHINE = PROPS_HOME / "machine.json"
HEALTH = PROPS_HOME / "health.json"
FREE_ONLY_LATCH = HOME / "free-only"
FREE_ONLY = "SCORE_FREE_ONLY"  # tools/props/cloud/ledger.py FREE_ONLY: every paid point raises FreeOnly under it
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


def resizing(now=None):
    """Whether the size timer asked for a resize within RESIZE_WINDOW: a SIGTERM now is the resize's shutdown, never
    the owner's stop (graph/runs.py stopped_by), even when systemd cannot say it is stopping."""
    if not RESIZING.is_file():
        return False
    asked = json.loads(RESIZING.read_text()).get("at", 0)
    return 0 <= (now if now is not None else time.time()) - asked <= RESIZE_WINDOW


def batch_project():
    """The name of the project the runner rents in and whose bill the stop line reads."""
    return os.environ.get("SCORE_SCALEWAY_PROJECT", BATCH_PROJECT_DEFAULT)


def project_refusal():
    """Why no paid run may clear while the batch project is the conductor's own (its hourly bill would count as
    batch spend and eat the stop line's buffer), or None."""
    record = machine() or {}
    if batch_project() in {CONDUCTOR_PROJECT, record.get("project")}:
        return (f"refused: SCORE_SCALEWAY_PROJECT is {batch_project()}, the conductor's own project; the batch "
                "project must be another, so the conductor's bill never counts as batch spend")
    return None
