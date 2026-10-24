"""The store's machine as the cockpit shows it (the Machine card on Home and /machine/): which machine it is, its health
and the tails of its logs, read on the store's machine and carried in the export as machine.json.

    machine.json  {read_at, machine, health, tails}
      machine     $PROPS_HOME/machine.json as the conductor's machine code writes it ({name, size, state, booted, ...});
                  on a machine without one (the owner's PC) {name: its host name}
      health      score.conductor.health.read(): size, state (idle, growing, batch, shrinking), disk, memory, load,
                  units {unit: state}, backup {at, ok}, sync {at}, bill {euros, month, read_at} (the score-conductor
                  project's own bill, never a batch's spend), free_only (the kill switch's latch), notes [line] (an
                  optional secret the conductor skipped: the Machine link's hover text); on a machine
                  without score.conductor {missing: NOT_ON_CONDUCTOR}
      tails       score.conductor.logs.tails(TAIL_LINES): {name: [lines]} (run logs, faults, the unit journals), cut
                  from the oldest line to TAIL_BYTES in all

Read only: nothing here writes the store or the machine. A key the health does not give shows as unknown."""
import datetime
import json
import pathlib
import socket

MACHINE_FILE = "machine.json"  # in $PROPS_HOME (the conductor's own record) and in the export (this module's)
NOT_ON_CONDUCTOR = "not on a conductor"
TAIL_LINES = 200
TAIL_BYTES = 256 * 1024
BACKUP_LATE_MINUTES = 120  # the card's backup turns red past this
EXPORT_LATE_MINUTES = 15  # the card's export turns red past this: the store's machine is not reaching the cockpit
STATES = {"idle": "idle", "growing": "growing", "batch": "running a batch", "shrinking": "shrinking"}


def now_utc():
    return datetime.datetime.now(datetime.timezone.utc)


def identity(props_home):
    """The machine's own record ($PROPS_HOME/machine.json), always with a `name` (else this host's)."""
    path = pathlib.Path(props_home) / MACHINE_FILE
    found = json.loads(path.read_text()) if path.is_file() else {}
    return {**found, "name": found.get("name") or socket.gethostname()}


def conductor_part(name):
    """score.conductor.<name>, or None on a machine without it (the owner's PC before the move)."""
    import importlib
    try:
        return importlib.import_module(f"score.conductor.{name}")
    except ModuleNotFoundError as missing:
        if missing.name not in ("score.conductor", f"score.conductor.{name}"):
            raise
        return None


def health():
    """The conductor's health.read(), or {missing: NOT_ON_CONDUCTOR}; a read that fails is said as `failed`."""
    part = conductor_part("health")
    if part is None:
        return {"missing": NOT_ON_CONDUCTOR}
    try:
        return part.read()
    except Exception as failed:  # the card shows it red; the export still goes
        return {"failed": f"{type(failed).__name__}: {failed}"}


def tails(limit_lines=TAIL_LINES):
    """The conductor's logs.tails(limit_lines), or {} without it; a read that fails is one line saying so."""
    part = conductor_part("logs")
    if part is None:
        return {}
    try:
        return part.tails(limit_lines)
    except Exception as failed:  # shown on /machine/ in place of the tails
        return {"failed": [f"{type(failed).__name__}: {failed}"]}


def cut(found, budget=TAIL_BYTES):
    """`found` {name: [lines]} with the oldest lines of the largest tail dropped first until the whole is at most
    `budget` bytes, so a short tail (a fault) outlives a long log."""
    kept = {name: [str(line) for line in lines] for name, lines in found.items()}
    sizes = {name: sum(len(line.encode()) + 1 for line in lines) for name, lines in kept.items()}
    while sum(sizes.values()) > budget:
        largest = max(sizes, key=sizes.get)
        sizes[largest] -= len(kept[largest].pop(0).encode()) + 1
    return kept


def gathered(props_home, read_at=None):
    """machine.json's content on the store's machine, read now and stamped `read_at` (an ISO time; else now)."""
    return {"read_at": read_at or now_utc().isoformat(timespec="seconds"), "machine": identity(props_home),
            "health": health(), "tails": cut(tails())}


def name_of(found):
    return ((found or {}).get("machine") or {}).get("name")


def minutes_since(stamp, now=None):
    """Whole minutes from an ISO time to now, or None when there is none."""
    if not stamp:
        return None
    then = datetime.datetime.fromisoformat(str(stamp).replace("Z", "+00:00"))
    if then.tzinfo is None:
        then = then.replace(tzinfo=datetime.timezone.utc)
    return max(0, int(((now or now_utc()) - then).total_seconds() // 60))


def said(value):
    """A health value in one short line: a dict's `name value` pairs, a list's items, else the value."""
    if isinstance(value, dict):
        return ", ".join(f"{name} {item}" for name, item in value.items())
    if isinstance(value, (list, tuple)):
        return " / ".join(str(item) for item in value)
    return str(value)


def state_of(machine, found_health):
    """The machine's state in words (idle, growing, running a batch, shrinking), or None when nothing says."""
    raw = machine.get("state") or found_health.get("state")
    if raw is None and "runs_active" in found_health:  # the owner's PC: no conductor record, its runs say it
        runs = found_health["runs_active"]
        return f"running {runs} run{'s' if runs != 1 else ''}" if runs else "idle"
    return STATES.get(raw, raw)


def card(found, export_made_at=None, now=None):
    """The Machine card's numbers from machine.json's content (None: none arrived): name, size, state, backup and
    export ages with their red, the conductor's bill, the latch, the units, `missing` when not on a conductor.
    `export_made_at` is the hosted export's time (None in local mode, where the card is read live)."""
    found = found or {}
    machine, read = found.get("machine") or {}, found.get("health") or {}
    backup = read.get("backup") or {}
    backup_minutes = minutes_since(backup.get("at"), now)
    export_minutes = minutes_since(export_made_at, now) if export_made_at else None
    bill = read.get("bill") or {}
    return {"name": machine.get("name"), "size": read.get("size") or machine.get("size"),
            "state": state_of(machine, read), "booted": machine.get("booted"),
            "missing": read.get("missing"), "failed": read.get("failed"),
            "on_pc": not read.get("machine") and not machine.get("size"),  # no cloud machine: no backup, no bill
            "backup_minutes": backup_minutes, "backup_ok": backup.get("ok"),
            "backup_late": backup_minutes is None or backup_minutes > BACKUP_LATE_MINUTES or backup.get("ok") is False,
            "export_minutes": export_minutes,
            "export_late": export_minutes is not None and export_minutes > EXPORT_LATE_MINUTES,
            "bill": bill.get("euros"), "bill_month": bill.get("month"), "free_only": bool(read.get("free_only")),
            "units": sorted((read.get("units") or {}).items()), "notes": read.get("notes") or [],
            "numbers": [(label, said(read[label])) for label in ("disk", "memory", "load") if read.get(label)],
            "sync_minutes": minutes_since(
                (read.get("sync") or {}).get("at"), now), "read_at": found.get("read_at")}
