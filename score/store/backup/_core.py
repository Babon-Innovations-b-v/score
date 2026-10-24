"""The steps every command shares: a snapshot of a home, a restore of one, the log line each command leaves."""
import datetime
import json
import pathlib
import shutil

from score.store import locked, whole_file
from score.store.backup import _manifest, _staging

# What can be rebuilt, left out of every backup (anchored at the home): the library cache the sync refills, the
# store's checkouts and making folders, scratch, downloads, the runs' frozen copies, the runtime interpreter
# (bootstrap.sh builds it from uv.lock), the tests' stores and the PC's Blender tooling.
REBUILT = ("cache", "store/cache", "tmp", "tmp.*", "downloads", "frozen", "env", "store-tests", "blender-mcp")
# Left out wherever they are: a write still landing.
NEVER = ("*.partial",)
MACHINE = "machine.json"
CARRIED_MANIFEST = f"{_staging.STAGING}/manifest.json"
LOGS = "logs"
LOCK = f"{LOGS}/backup.lock"
# What a home may hold and still count as empty for a restore into it: the volume's own folder, and this module's
# logs and lock (written by a refused backup before the move).
EMPTY_ENOUGH = ("lost+found",)


def utc_now():
    """Now, in UTC."""
    return datetime.datetime.now(datetime.timezone.utc)


def excludes(home, databases):
    """restic's --exclude arguments for `home`: what can be rebuilt, the volume's lost+found, partial writes, and each
    live database with its side files (their consistent copies are backed up instead)."""
    root = str(pathlib.Path(home).resolve())
    # The volume's lost+found is root's, mode 700: restic cannot open it and fails the whole backup (exit 3).
    patterns = [f"{root}/{name}" for name in REBUILT + EMPTY_ENOUGH] + list(NEVER)
    for database in databases:
        patterns += [f"{root}/{name}" for name in [database, *_staging.side_files(database)]]
    return [argument for pattern in patterns for argument in ("--exclude", pattern)]


def snapshot(restic, home, tags, carry_manifest):
    """Back `home` up as one snapshot with `tags`, its databases as consistent copies, and its manifest inside when
    `carry_manifest`; {snapshot, files, bytes, detail}."""
    home = pathlib.Path(home)
    with locked(home / LOCK):
        staging = home / _staging.STAGING
        copies = _staging.stage(home, staging)
        detail = {"databases": sorted(copies)}
        try:
            if carry_manifest:
                written = _manifest.manifest(home, copies)
                (home / CARRIED_MANIFEST).write_text(json.dumps(written, indent=1, sort_keys=True))
                detail["manifest"] = {"store": written["store"]["listing_hash"], "files": len(written["files"])}
            tag_args = [argument for tag in tags for argument in ("--tag", tag)]
            summary = restic.summary("backup", ".", *tag_args, *excludes(home, copies), cwd=home)
        finally:
            shutil.rmtree(staging)
    return {"snapshot": summary["snapshot_id"], "files": summary["total_files_processed"],
            "bytes": summary["total_bytes_processed"], "detail": detail}


def restore(restic, snapshot_id, target, includes=()):
    """Restore one snapshot into `target`, verified, its database copies moved to their own paths; (restic's summary,
    the manifest the snapshot carries or None)."""
    target = pathlib.Path(target)
    target.mkdir(parents=True, exist_ok=True)
    include_args = [argument for name in includes for argument in ("--include", f"/{name}")]
    summary = restic.summary("restore", snapshot_id, "--target", str(target), "--verify", *include_args)
    carried_path = target / CARRIED_MANIFEST
    carried = json.loads(carried_path.read_text()) if carried_path.exists() else None
    _staging.put_in_place(target)
    if (target / _staging.STAGING).exists():
        shutil.rmtree(target / _staging.STAGING)
    return summary, carried


def emptiness_refusal(home):
    """Why `home` is not empty enough to restore into, or None: it may hold only the volume's lost+found and this
    module's own logs and lock."""
    home = pathlib.Path(home)
    if not home.exists():
        return None
    held = []
    for entry in sorted(home.iterdir()):
        if entry.name in EMPTY_ENOUGH:
            continue
        if entry.name == LOGS and entry.is_dir() and all(path.name.startswith("backup") for path in entry.iterdir()):
            continue
        held.append(entry.name)
    if held:
        return f"{home} is not empty ({', '.join(held[:8])}{', ...' if len(held) > 8 else ''}): a restore goes only into an empty home"
    return None


def log_record(kind, outcome, seconds, error=None):
    """The log's record of one command: {at, kind, ok, snapshot, files, bytes, seconds, error, detail} (AREA 4's
    health reads the first eight)."""
    return {"at": utc_now().isoformat(timespec="seconds"), "kind": kind, "ok": error is None,
            "snapshot": outcome.get("snapshot"), "files": outcome.get("files"), "bytes": outcome.get("bytes"),
            "seconds": round(seconds, 1), "error": error, "detail": outcome.get("detail")}


def write_log(home, record):
    """Write one command's record to $PROPS_HOME/logs/backup-<UTC stamp>.json, whole; its path."""
    path = pathlib.Path(home) / LOGS / f"backup-{utc_now().strftime('%Y%m%dT%H%M%S%fZ')}.json"
    whole_file(path, json.dumps(record, indent=1).encode()).replace(path)
    return path


def logs(home, kind):
    """Every logged record of `kind` in `home`, oldest first."""
    folder = pathlib.Path(home) / LOGS
    records = [json.loads(path.read_text()) for path in sorted(folder.glob("backup-*.json"))] if folder.is_dir() else []
    return [record for record in records if record.get("kind") == kind]
