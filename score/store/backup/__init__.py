"""The store's backups: restic, encrypted and deduplicated, into the repository SCORE_BACKUP_REPO names (on the
conductor an s3: bucket in another region than the machine), and the one-time move of the store from the PC.

    python -m score.store.backup backup               # every 30 minutes (score-backup.timer)
    python -m score.store.backup forget               # keep 48 last, 30 daily, 12 weekly; prune (daily)
    python -m score.store.backup check                # restic check daily; a 5% data read when none in 7 days
    python -m score.store.backup restore --to <dir>   # a restore drill into an empty scratch folder
    python -m score.store.backup manifest [<home>]    # the home's manifest (_manifest.py)
    python -m score.store.backup migrate --from-pc | --onto-conductor | --pc-test-home   # the move (_migrate.py)
    python -m score.store.backup migrate --from-vm | --onto-cluster   # the conductor's move into the cluster

A backup holds $PROPS_HOME minus what can be rebuilt (_core.REBUILT) and partial writes, and beside it the people
routes' motion home (MOTION_HOME, ~/.farm-factory-motion: the candidates, 1.5 GB, on the same volume; its env left out)
as a snapshot of its own tagged `motion`, which a restore of the home never takes (#125); each SQLite database under
dashboard/ is held as its consistent copy (_staging). The password is the secret `score-backup-restic-password`, read
by name through SCORE_SECRET_READER into restic's environment only (_restic). A plain backup is refused until the
home holds machine.json (written by the move), so a fresh conductor's timer never backs up an empty home. Every
command prints one summary line and writes its record to $PROPS_HOME/logs/backup-<UTC stamp>.json:
{at, kind, ok, snapshot, files, bytes, seconds, error, detail}, kind one of backup, forget, check, check-data, restore,
manifest, migrate-from-pc, migrate-onto-conductor, migrate-pc-test-home, migrate-from-vm, migrate-onto-cluster.
"""
import datetime
import json
import os
import pathlib

from score.store import PROPS_HOME
from score.store.backup import _core, _manifest, _migrate
from score.store.backup._migrate import Mismatch, Refused
from score.store.backup._restic import Restic, ResticFailed

KEEP = ("--keep-last", "48", "--keep-daily", "30", "--keep-weekly", "12", "--keep-tag", _migrate.PC_FINAL,
        "--keep-tag", _migrate.VM_FINAL)
READ_SUBSET = "5%"
# The people routes' motion home (tools/characters/people/paths.py), beside the props home on the store's volume
# (tools/cloud/k8s/conductor MOUNTS), backed up as its own snapshot tagged MOTION_TAG; its env is rebuilt.
MOTION_HOME = pathlib.Path(os.environ.get("MOTION_HOME", pathlib.Path.home() / ".farm-factory-motion"))
MOTION_TAG = "motion"
MOTION_REBUILT = ("env",)
READ_EVERY = datetime.timedelta(days=7)

__all__ = ["Mismatch", "Refused", "ResticFailed", "backup", "check", "forget", "manifest", "migrate", "compare", "read_manifest", "restore"]


def backup(home=PROPS_HOME, restic=None):
    """One snapshot of the home; {snapshot, files, bytes, detail}. Refused before the move wrote machine.json."""
    if not (pathlib.Path(home) / _core.MACHINE).exists():
        raise Refused(f"{home} holds no {_core.MACHINE}: this is no store's machine yet (migrate --onto-conductor "
                      "writes it); nothing is backed up")
    restic = restic or Restic()
    restic.ensure()
    made = _core.snapshot(restic, home, ["half-hourly"], carry_manifest=False)
    made["detail"]["motion"] = motion_snapshot(restic, MOTION_HOME)
    return made


def motion_snapshot(restic, motion):
    """The motion home `motion` backed up as one snapshot tagged MOTION_TAG, MOTION_REBUILT left out; {snapshot, files,
    bytes}, or None where there is no motion home."""
    motion = pathlib.Path(motion)
    if not motion.is_dir():
        return None
    root = str(motion.resolve())
    left_out = [argument for name in MOTION_REBUILT for argument in ("--exclude", f"{root}/{name}")]
    summary = restic.summary("backup", ".", "--tag", MOTION_TAG, *left_out, cwd=motion)
    return {"snapshot": summary["snapshot_id"], "files": summary["total_files_processed"],
            "bytes": summary["total_bytes_processed"]}


def unlocked(restic):
    """restic's stale locks removed (`restic unlock`: a lock of this host whose process is gone, or any older than
    restic's 30 minutes without a refresh), a live one kept; what restic said. Fault of 2026-11-04 to 11-15 (#125): the
    old VM's lock stayed in the repository after it went off, and every nightly forget and check failed on it."""
    return restic.checked("unlock").strip().splitlines()[-1:]


def forget(restic=None):
    """Drop the snapshots past the policy (48 last, 30 daily, 12 weekly; pc-final and vm-final always kept) and prune,
    after the stale locks are removed; {detail: kept, removed, unlocked}."""
    restic = restic or Restic()
    cleared = unlocked(restic)
    said = restic.checked("forget", *KEEP, "--prune", "--json").splitlines()
    groups = next((json.loads(line) for line in said if line.startswith("[")), [])
    return {"detail": {"kept": sum(len(group.get("keep") or []) for group in groups),
                       "removed": sum(len(group.get("remove") or []) for group in groups), "unlocked": cleared}}


def data_read_due(home):
    """True when no data read (check-data) passed in the last READ_EVERY."""
    passed = [record for record in _core.logs(home, "check-data") if record["ok"]]
    if not passed:
        return True
    return _core.utc_now() - datetime.datetime.fromisoformat(passed[-1]["at"]) >= READ_EVERY


def check(home=PROPS_HOME, read_data=None, restic=None):
    """restic check, with a READ_SUBSET read of the data when `read_data` (default: when one is due); (kind,
    {detail})."""
    restic = restic or Restic()
    read_data = data_read_due(home) if read_data is None else read_data
    cleared = unlocked(restic)
    args = ["check"] + (["--read-data-subset", READ_SUBSET] if read_data else [])
    tail = restic.checked(*args).strip().splitlines()[-1:]
    return ("check-data" if read_data else "check"), {"detail": {"said": tail, "unlocked": cleared}}


def restore(to, home=PROPS_HOME, snapshot="latest", restic=None):
    """A restore drill: one snapshot into the empty folder `to`, outside the home, verified by restic and, when the
    snapshot carries one, against its manifest; {snapshot, files, bytes, detail}. Mismatch on any difference."""
    to = pathlib.Path(to).resolve()
    if to.is_relative_to(pathlib.Path(home).resolve()):
        raise Refused(f"{to} is inside the home: a drill restores outside it, where no backup reads it back")
    refused = _core.emptiness_refusal(to)
    if refused:
        raise Refused(refused)
    restic = restic or Restic()
    snapshot_id = newest_home(restic) if snapshot == "latest" else snapshot
    summary, expected = _core.restore(restic, snapshot_id, to)
    detail = {"to": str(to), "manifest": "none carried: restic's own verify only"}
    if expected is not None:
        differences = _manifest.differences(expected, _manifest.manifest(to))
        if differences:
            raise Mismatch(differences)
        detail["manifest"] = f"{len(expected['files'])} files and {expected['store']['objects']} store objects match"
    return {"snapshot": snapshot_id, "files": summary["total_files"], "bytes": summary["total_bytes"],
            "detail": detail}


def newest_home(restic):
    """The newest snapshot of the home, never the motion home's (MOTION_TAG); ResticFailed when there is none."""
    found = [snapshot for snapshot in restic.snapshots() if MOTION_TAG not in (snapshot.get("tags") or [])]
    if not found:
        raise ResticFailed("the repository holds no snapshot of the home")
    return found[-1]["id"]


def manifest(home=PROPS_HOME, log_home=PROPS_HOME):
    """The manifest of `home`, kept under log_home's logs; {files, detail}."""
    if not pathlib.Path(home).is_dir():
        raise Refused(f"no home at {home}")
    record = _manifest.manifest(home)
    path = _migrate.save_manifest(log_home, _core.utc_now().strftime("%Y%m%dT%H%M%SZ"), record)
    return {"files": len(record["files"]),
            "detail": {"path": str(path), "store": record["store"]["listing_hash"],
                       "store_objects": record["store"]["objects"]}}


# Each step of the move: (why it may not run now, or None; the step).
MIGRATIONS = {"from-pc": (_migrate.pc_refusal, _migrate.from_pc),
              "onto-conductor": (_migrate.onto_refusal, _migrate.onto_conductor),
              "pc-test-home": (_migrate.onto_refusal, _migrate.pc_test_home),
              "from-vm": (_migrate.vm_refusal, _migrate.from_vm),
              "onto-cluster": (_migrate.cluster_refusal, _migrate.onto_cluster)}


def migrate(mode, home=PROPS_HOME, restic=None):
    """One step of the move (MIGRATIONS' keys), refused before anything is read or written when it may not run (in an
    agent's process always); {snapshot, files, bytes, detail}."""
    refusal, step = MIGRATIONS[mode]
    refused = refusal(home)
    if refused:
        raise Refused(refused)
    return step(restic or Restic(), home)


def read_manifest(home):
    """The manifest of a home (_manifest.py), read now."""
    return _manifest.manifest(home)


def compare(expected, found):
    """Every difference of the manifest `found` from `expected`, one line each (missing, extra or changed)."""
    return _manifest.differences(expected, found)
