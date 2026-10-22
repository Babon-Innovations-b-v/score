"""The conductor's health, read from the machine alone (no cloud call) and written where the sync's export takes it.

    python -m score.conductor health --write    # the minute timer's: $PROPS_HOME/health.json, one line said

read() is {at, machine, size, state, cores, memory_total, memory_available, disk_free (GB, the data volume under
PROPS_HOME), load (1, 5 and 15 minutes), units {sync, listen, resume, backup: active, failed or inactive}, runs_active
(live claims in runs/active.json), runs_waiting, parked_machines, last_backup (the newest backup's record in
logs/backup-*.json, score.store.backup's: {at, ok}), last_sync (score-sync.service's last end: {at, ok}), free_only
(the kill switch's latch)}, with the Machine card's own shapes beside them (score/dashboard/state/machine.py): state
(idle, growing, batch or shrinking), disk {free_gb, total_gb}, memory {available_gb, total_gb}, backup and sync (the
same as last_backup and last_sync). A unit is failed when any of its units failed or its service's last run did not
succeed, active when one of them is active. The conductor's own bill is not read here (a cloud call every minute).
"""
import datetime
import json
import os
import pathlib
import shutil
import subprocess

from score import conductor
from score.conductor import size
from score.store import PROPS_HOME

# Each unit family the cockpit's Machine card shows, its timer (when it has one) first.
UNITS = {"sync": ("score-sync.timer", "score-sync.service"), "listen": ("score-listen.service",),
         "resume": ("score-resume.service",), "backup": ("score-backup.timer", "score-backup.service")}
BACKUPS = PROPS_HOME / "logs"  # score.store.backup writes logs/backup-<time>.json: {at, ok, ...}
PROPERTIES = ("ActiveState", "Result", "ExecMainExitTimestamp")


def unit_properties(unit):
    """{ActiveState, Result, ExecMainExitTimestamp (`@<seconds since the epoch>`)} of one user unit; empty values when
    systemd cannot tell."""
    try:
        done = subprocess.run(["systemctl", "--user", "show", unit, "--timestamp=unix",
                               *[f"--property={name}" for name in PROPERTIES]], capture_output=True, text=True,
                              timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return dict.fromkeys(PROPERTIES, "")
    found = dict(line.partition("=")[::2] for line in done.stdout.splitlines() if "=" in line)
    return {name: found.get(name, "") for name in PROPERTIES}


def unit_state(units, properties=unit_properties):
    """One family's state: failed, active or inactive."""
    shown = [properties(unit) for unit in units]
    if any(shown_one["ActiveState"] == "failed" or shown_one["Result"] not in ("", "success") for shown_one in shown):
        return "failed"
    return "active" if any(shown_one["ActiveState"] in ("active", "activating", "reloading") for shown_one in shown) \
        else "inactive"


def last_sync(properties=unit_properties):
    """When score-sync.service last ended and whether it succeeded, or None when it never ran."""
    shown = properties("score-sync.service")
    if not shown["ExecMainExitTimestamp"].startswith("@"):
        return None
    ended = datetime.datetime.fromtimestamp(int(shown["ExecMainExitTimestamp"][1:]), datetime.timezone.utc)
    return {"at": ended.isoformat(timespec="seconds"), "ok": shown["Result"] == "success"}


def last_backup(folder=None):
    """The newest backup's record ({at, ok}; a check's or a move's are other kinds), or None when there is none."""
    reports = sorted(pathlib.Path(folder or BACKUPS).glob("backup-*.json"), reverse=True)
    for path in reports:
        report = json.loads(path.read_text())
        if report.get("kind", "backup") == "backup":
            return {"at": report.get("at"), "ok": bool(report.get("ok"))}
    return None


def machine_state(record, cores):
    """The Machine card's state: growing or shrinking while a resize the size timer asked for is under way, else
    batch or idle by the cores."""
    if conductor.resizing():
        return {"grow": "growing", "shrink": "shrinking"}.get(json.loads(conductor.RESIZING.read_text())["action"])
    if record is None:
        return None
    return "batch" if cores >= int(record.get("batch_cores", 0)) else "idle"


def machine_size(record):
    """This machine's commercial type, worked out from its cores against machine.json's two sizes."""
    if record is None:
        return None
    return record.get("batch_type") if conductor.cores() >= int(record.get("batch_cores", 0)) \
        else record.get("idle_type")


def read(properties=unit_properties):
    """The conductor's health now (the module's docstring has its fields)."""
    record = conductor.machine()
    view = size.busy()
    disk = shutil.disk_usage(PROPS_HOME if PROPS_HOME.exists() else "/")
    memory = {"available_gb": round(conductor.meminfo_gb("MemAvailable"), 2),
              "total_gb": round(conductor.meminfo_gb("MemTotal"), 2)}
    backup, sync = last_backup(), last_sync(properties)
    return {"at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
            "machine": (record or {}).get("name"), "size": machine_size(record),
            "state": machine_state(record, conductor.cores()), "cores": conductor.cores(),
            "memory_total": memory["total_gb"], "memory_available": memory["available_gb"], "memory": memory,
            "disk_free": round(disk.free / 1024 ** 3, 2),
            "disk": {"free_gb": round(disk.free / 1024 ** 3, 2), "total_gb": round(disk.total / 1024 ** 3, 2)},
            "load": [round(value, 2) for value in os.getloadavg()],
            "units": {name: unit_state(units, properties) for name, units in UNITS.items()},
            "runs_active": view["claims"], "runs_waiting": view["waiting"], "parked_machines": view["parked"],
            "last_backup": backup, "backup": backup, "last_sync": sync, "sync": sync,
            "free_only": conductor.free_only()}


def write(found=None, path=None):
    """Write the health whole to $PROPS_HOME/health.json; its path."""
    path = pathlib.Path(path or conductor.HEALTH)
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(f"{path.name}.{os.getpid()}.partial")
    partial.write_text(json.dumps(found or read(), indent=1))
    os.replace(partial, path)
    return path
