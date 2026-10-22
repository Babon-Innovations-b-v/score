"""The one-time move of the store's machine from the owner's PC to the conductor, through the backup repository.

    PC:        migrate --from-pc         refuses while a sync, listener or resume unit is active or a run is alive;
                                         writes the PC's manifest and backs the home up tagged pc-final, the manifest
                                         inside the snapshot
    conductor: migrate --onto-conductor  refuses a home that is not empty; restores the newest pc-final snapshot,
                                         compares the conductor's manifest with the PC's and stops on any difference;
                                         writes machine.json, the store's machine identity
    PC:        migrate --pc-test-home    restores only the environment data the test sandbox links (work/, design/)
                                         into an empty PC home, read-only, so `make tests` keeps working on the PC

Every mode is the owner's own: refused in an agent's process (the store's AGENT_MARKERS).
"""
import json
import os
import pathlib
import shutil
import socket
import stat
import subprocess

from score.store import running_under_agent, whole_file
from score.store.backup import _core, _manifest

PC_FINAL = "pc-final"
# The PC's units that act as the store's machine: none may run while its home is copied.
PC_UNITS = ("score-sync.service", "score-sync.timer", "score-listen.service", "score-resume.service")
RUNNING_STATES = ("active", "activating", "reloading", "deactivating")
# What the PC's test sandbox links from the home once the store has moved (.claude/scripts/sandbox-home.py links every
# entry not in its STATE; of those the backup holds these, and env/ is rebuilt by bootstrap.sh from uv.lock).
PC_TEST_FOLDERS = ("work", "design")


class Refused(RuntimeError):
    """The move may not run now; the message says why."""


class Mismatch(RuntimeError):
    """The restored home differs from the PC's manifest; `differences` lists every file."""

    def __init__(self, differences):
        self.differences = differences
        shown = "; ".join(differences[:10])
        super().__init__(f"{len(differences)} files differ from the PC's manifest ({shown}"
                         f"{'; ...' if len(differences) > 10 else ''}): the move stops; nothing is put back by hand")


def agent_refusal():
    """Why this process may not move the store, or None."""
    if running_under_agent():
        return "the move is the owner's own: refused in an agent's process"
    return None


def active_units(units=PC_UNITS):
    """The units of `units` systemd's user manager runs now (none where there is no systemctl)."""
    systemctl = shutil.which("systemctl")
    if not systemctl:
        return []
    done = subprocess.run([systemctl, "--user", "is-active", *units], capture_output=True, text=True)
    states = done.stdout.split()
    if len(states) != len(units):
        raise Refused(f"systemctl --user is-active gave {len(states)} states for {len(units)} units: "
                      f"{done.stderr.strip()}")
    return [unit for unit, state in zip(units, states) if state in RUNNING_STATES]


def live_runs(home):
    """{pid: claim} of the runs in the home's runs/active.json whose process still runs."""
    from score.graph import runs  # the runner's own reading of a claim's liveness (pid and its start time)

    path = pathlib.Path(home) / "runs" / runs.ACTIVE
    return runs.live(json.loads(path.read_text())) if path.exists() else {}


def pc_refusal(home):
    """Why the PC's home may not be moved now, or None."""
    refused = agent_refusal()
    if refused:
        return refused
    if (pathlib.Path(home) / _core.MACHINE).exists():
        return f"{home} holds {_core.MACHINE}: it is the conductor's home, not the PC's"
    units = active_units()
    if units:
        return f"{', '.join(units)} still active: stop them first (systemctl --user stop ...)"
    alive = live_runs(home)
    if alive:
        return f"runs still alive (pid {', '.join(sorted(alive))}): let them end or stop them first"
    return None


def from_pc(restic, home):
    """Back the PC's home up tagged pc-final with its manifest inside (once pc_refusal gave none); {snapshot, files,
    bytes, detail}."""
    restic.ensure()
    return _core.snapshot(restic, home, [PC_FINAL], carry_manifest=True)


def onto_refusal(home):
    """Why the move may not land in `home`, or None."""
    return agent_refusal() or _core.emptiness_refusal(home)


def save_manifest(home, name, record):
    """Keep one manifest under the home's logs; its path."""
    path = pathlib.Path(home) / _core.LOGS / f"manifest-{name}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    whole_file(path, json.dumps(record, indent=1, sort_keys=True).encode()).replace(path)
    return path


def write_identity(home, snapshot_id):
    """Write $PROPS_HOME/machine.json, the store's machine identity: {name, since, from}."""
    identity = {"name": socket.gethostname(), "since": _core.utc_now().isoformat(timespec="seconds"),
                "from": f"{PC_FINAL} {snapshot_id}"}
    path = pathlib.Path(home) / _core.MACHINE
    whole_file(path, json.dumps(identity, indent=1).encode()).replace(path)
    return identity


def onto_conductor(restic, home):
    """Restore the newest pc-final snapshot into the conductor's empty home, check it against the PC's manifest and
    write the machine identity; {snapshot, files, bytes, detail}. Mismatch on any difference."""
    snapshot_id = restic.newest(PC_FINAL)
    summary, expected = _core.restore(restic, snapshot_id, home)
    if expected is None:
        raise Refused(f"snapshot {snapshot_id} carries no manifest: it is no pc-final made by migrate --from-pc")
    found = _manifest.manifest(home)
    save_manifest(home, PC_FINAL, expected)
    save_manifest(home, "conductor", found)
    differences = _manifest.differences(expected, found)
    if differences:
        raise Mismatch(differences)
    identity = write_identity(home, snapshot_id)
    return {"snapshot": snapshot_id, "files": summary["total_files"], "bytes": summary["total_bytes"],
            "detail": {"identity": identity, "files_checked": len(found["files"]),
                       "store_objects": found["store"]["objects"]}}


def read_only(folder):
    """`folder` and everything under it made read-only (no one may write); links are left as they are."""
    writes = stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH
    for root, folders, files in os.walk(folder, topdown=False):
        for path in [os.path.join(root, name) for name in folders + files]:
            if not os.path.islink(path):
                os.chmod(path, os.stat(path).st_mode & ~writes)
    os.chmod(folder, os.stat(folder).st_mode & ~writes)


def pc_test_home(restic, home):
    """Restore the test sandbox's environment data (PC_TEST_FOLDERS) from the newest pc-final snapshot into the PC's
    empty home, read-only; {snapshot, files, bytes, detail}."""
    snapshot_id = restic.newest(PC_FINAL)
    summary, _carried = _core.restore(restic, snapshot_id, home, includes=PC_TEST_FOLDERS)
    for folder in PC_TEST_FOLDERS:
        if (pathlib.Path(home) / folder).is_dir():
            read_only(pathlib.Path(home) / folder)
    return {"snapshot": snapshot_id, "files": summary["total_files"], "bytes": summary["total_bytes"],
            "detail": {"folders": list(PC_TEST_FOLDERS), "env": "rebuilt by .claude/scripts/bootstrap.sh"}}
