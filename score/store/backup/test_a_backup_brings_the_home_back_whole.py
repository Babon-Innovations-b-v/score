"""A backup brings the home back whole: one fixture home made with the real Store API is backed up to a local restic
repository (a folder, no cloud), restored in a drill, moved from the PC onto the conductor and from the conductor into
the cluster, and compared; a table of refusals is driven through the same entry points, each leaving the repository and
its home untouched; the command line's records are a table of commands. restic is required (bootstrap.sh installs it):
the test skips only where it is missing.

Breaks (each applied once, seen red, reverted), in score/store/backup/:
- restores every kept file: _core.excludes drops REBUILT from its patterns.
- passes over lost+found: _core.excludes drops EMPTY_ENOUGH.
- live database whole: _core.excludes leaves the live database and its side files in.
- refused before machine.json: backup's machine.json check becomes `if False:`.
- the move names the machine: _migrate.write_identity drops the sizes record. Break: _migrate.vm_refusal's `if units:`
  becomes `if False:` (the VM's home copied while its sync runs); move_refusal's MOVE_WORDS check dropped;
  onto_cluster's record drops `**DRIVE` or image_refusal answers None (a cluster.json without the drive's image and
  size, filled in by hand at the cutover of 2026-11-08).
- each difference named: _manifest.differences never reports a changed file.
- a file not back stops the move: _migrate.onto_conductor's Mismatch check becomes `if False:`.
- a unit active: _migrate.pc_refusal's `if units:` becomes `if False:`.
- a run alive: _migrate.pc_refusal's `if alive:` becomes `if False:`.
- no sizes record: _migrate.onto_refusal's record check becomes `if False:`.
- home not empty: _core.emptiness_refusal's `if held:` becomes `if False:`.
- an agent never moves the store: _migrate.agent_refusal's check becomes `if False:`.
- test home read-only: _migrate.pc_test_home skips read_only.
- data read due: __init__.data_read_due answers False when none passed.
- unforeseen failure: __main__.main re-raises without log_failure.
- password from the reader only: _restic.environment keeps RESTIC_PASSWORD_FILE and _COMMAND.
- the owner's open yes: conductor_yes.move_allowed is true for any named yes.
- one content hash: _staging.content_hash hashes the file's bytes.
"""
import json
import os
import shutil
import sqlite3
import stat

import pytest

from score.graph import runs
from score.store import AGENT_MARKERS, Store
from score.store import backup as backups
from score.store.backup import __main__ as command
from score.store.backup import _migrate, _staging, conductor_yes

UNITS_INACTIVE = "inactive\n" * len(_migrate.PC_UNITS)
VM_INACTIVE = "inactive\n" * len(_migrate.VM_UNITS)
COMMITTED_ROWS = 300
SIZES = {"zone": "fr-par-2", "idle_type": "POP2-HM-2C-16G", "batch_type": "POP2-HM-16C-128G", "idle_cores": 2,
         "batch_cores": 16, "project": "score-conductor"}
IMAGE = "registry.example/score-conductor:1@sha256:" + "0" * 64
REBUILT = ("cache/lib.bin", "store/cache/checkouts/x/f", "tmp/t", "tmp.Ab12/t", "downloads/d", "frozen/f",
           "env/bin/python", "store-tests/s", "blender-mcp/b", "design/plans/hangar.json.12-34.partial")
KEPT = ("design/plans/hangar.json", "cloud/ledger.jsonl", "runs/run-1.json", "work/takes/a.txt",
        "dashboard/exports/state.json")
HEALTH_KEYS = {"at", "kind", "ok", "snapshot", "files", "bytes", "seconds", "error"}


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


@pytest.fixture
def setting(tmp_path, monkeypatch):
    """The owner's process (no agent markers), a folder repository, a secret reader printing its password while a
    password file and command name another (dropped: the reader is the only way in), the conductor's sizes record, the
    owner's yeses in their own store, and a systemctl shim answering from tmp_path/states."""
    for marker in AGENT_MARKERS:
        monkeypatch.delenv(marker, raising=False)
    for name in (_migrate.MOVE_WORDS, _migrate.IMAGE_VARIABLE, conductor_yes.YES_ID):
        monkeypatch.delenv(name, raising=False)
    tools = tmp_path / "tools"
    reader = write(tools / "reader", "#!/bin/sh\n[ \"$1\" = score-backup-restic-password ] && echo fixture-pass\n")
    shim = write(tools / "systemctl", f"#!/bin/sh\ncat {tmp_path / 'states'}\n")
    for script in (reader, shim):
        script.chmod(0o755)
    write(tmp_path / "states", UNITS_INACTIVE)
    wrong = write(tmp_path / "elsewhere" / "password", "a-file-password\n")
    monkeypatch.setenv("PATH", f"{tools}:{os.environ['PATH']}")
    monkeypatch.setenv("SCORE_SECRET_READER", str(reader))
    monkeypatch.setenv("SCORE_BACKUP_REPO", str(tmp_path / "repository"))
    monkeypatch.setenv("RESTIC_PASSWORD_FILE", str(wrong))
    monkeypatch.setenv("RESTIC_PASSWORD_COMMAND", f"cat {wrong}")
    monkeypatch.setenv("SCORE_CONDUCTOR_RECORD", str(write(tmp_path / "conductor.json", json.dumps(SIZES))))
    monkeypatch.setenv(conductor_yes.YES_HOME, str(tmp_path / "yes-home"))
    monkeypatch.setattr(command, "PROPS_HOME", tmp_path / "logs-home")
    return tmp_path


def make_home(home):
    """A home with an output and a record in a real store, design, ledgers, run entries, work and a link into it,
    everything a backup leaves out, an unreadable lost+found (root's on the volume), and a live WAL database with a
    write history and COMMITTED_ROWS rows; the live connection (a write left open)."""
    store = Store.in_folder(home / "store")
    output = write(home / "scratch-output" / "model.json", '{"vertices": 8}')
    store.write_record("surfaces@hangar", "key1", {"output": store.put_tree(output.parent)})
    shutil.rmtree(home / "scratch-output")
    write(home / "design" / "plans" / "hangar.json", '{"rooms": 3}')
    write(home / "cloud" / "ledger.jsonl", '{"euros": 1.5}\n')
    write(home / "runs" / "run-1.json", '{"state": "ended"}')
    write(home / "work" / "takes" / "a.txt", "take a")
    (home / "work" / "takes" / "latest.txt").symlink_to(home / "work" / "takes" / "a.txt")  # a link into this home
    write(home / "dashboard" / "exports" / "state.json", "{}")
    for rebuilt in REBUILT:
        write(home / rebuilt, "rebuilt")
    (home / "lost+found").mkdir(mode=0o000)
    database = sqlite3.connect(home / "dashboard" / "dashboard.sqlite3")
    database.execute("pragma journal_mode=wal")
    database.execute("pragma wal_autocheckpoint=0")  # committed rows stay in the WAL, as in a busy cockpit
    database.execute("create table requests (n)")
    database.executemany("insert into requests values (?)", [(str(n) * 500,) for n in range(200)])
    database.commit()
    database.execute("delete from requests")  # a write history: the live file's bytes are not its copy's
    database.executemany("insert into requests values (?)", [(n,) for n in range(COMMITTED_ROWS)])
    database.commit()
    database.execute("insert into requests values (-1)")  # a write still open: never in a backup
    return database


def rows(path):
    """The rows of a database's requests table."""
    with sqlite3.connect(path) as database:
        return database.execute("select count(*) from requests").fetchone()[0]


def tree(folder):
    """Every file and folder under `folder` with its size and change time (nothing where it does not exist)."""
    found = []
    for root, folders, files in os.walk(folder):
        for name in folders + files:
            path = os.path.join(root, name)
            facts = os.lstat(path)
            found.append((path, facts.st_size, facts.st_mtime_ns))
    return sorted(found)


def relative_files(folder):
    return sorted(path.relative_to(folder).as_posix() for path in folder.rglob("*") if path.is_file())


@pytest.mark.skipif(shutil.which("restic") is None, reason="restic is not installed (bootstrap.sh lists it as missing)")
def test_a_backup_brings_the_home_back_whole(setting, monkeypatch):
    pc, conductor, cluster = setting / "pc", setting / "conductor", setting / "cluster"
    drill, test_home, repository = setting / "drill", setting / "pc-again", setting / "repository"
    live = make_home(pc)
    assert (pc / "dashboard" / "dashboard.sqlite3-wal").stat().st_size > 0  # the rows are in the WAL, not the file

    # The PC's home moves in an agent's process under the owner's open yes, a yes that quotes him.
    with pytest.raises(conductor_yes.Refused):
        conductor_yes.record("", "Switch the conductor on?")
    given = conductor_yes.record("yes", "Switch the conductor on, about EUR 90 a month?")
    assert conductor_yes.open_yes("prepare")["id"] == given["id"]
    monkeypatch.setenv(AGENT_MARKERS[0], "1")
    monkeypatch.setenv(conductor_yes.YES_ID, given["id"])
    moved = backups.migrate("from-pc", pc)
    conductor_yes.mark_done(given, "move")
    assert conductor_yes.open_yes("move") is None
    assert conductor_yes.open_yes("up")["id"] == given["id"], "each step is done on its own"
    for name in (AGENT_MARKERS[0], conductor_yes.YES_ID):
        monkeypatch.delenv(name)

    # It lands on the conductor's fresh volume whole, named a conductor by its sizes record.
    (conductor / "lost+found").mkdir(parents=True)
    landed = backups.migrate("onto-conductor", conductor)
    assert landed["snapshot"] == moved["snapshot"]
    identity = json.loads((conductor / "machine.json").read_text())
    assert identity["from"] == f"pc-final {moved['snapshot']}"
    assert {name: identity[name] for name in SIZES} == SIZES  # what makes it a conductor (score.conductor.machine)
    assert backups.compare(backups.read_manifest(pc), backups.read_manifest(conductor)) == []
    assert rows(conductor / "dashboard" / "dashboard.sqlite3") == COMMITTED_ROWS

    # A plain backup of a store's machine, the database still being written, and its restore drill.
    write(pc / "machine.json", "{}")
    assert backups.backup(pc)["snapshot"]
    live.close()
    (pc / "lost+found").chmod(0o700)
    backups.restore(drill, home=pc)
    for kept in KEPT:
        assert (drill / kept).read_bytes() == (pc / kept).read_bytes(), kept
    objects = sorted(path.relative_to(pc) for path in (pc / "store" / "objects").rglob("*") if path.is_file())
    assert objects and all((drill / name).read_bytes() == (pc / name).read_bytes() for name in objects)
    restored = relative_files(drill)
    assert not any(name.startswith(("cache/", "store/cache/", "tmp/", "tmp.", "downloads/", "frozen/", "env/",
                                    "store-tests/", "blender-mcp/")) or name.endswith(".partial")
                   for name in restored), restored
    assert not {name.split("/")[0] for name in restored} & {"backup-staging", "lost+found"}, restored
    assert not (drill / "dashboard" / "dashboard.sqlite3-wal").exists()
    assert rows(drill / "dashboard" / "dashboard.sqlite3") == COMMITTED_ROWS
    live_file, copy = pc / "dashboard" / "dashboard.sqlite3", conductor / "dashboard" / "dashboard.sqlite3"
    assert live_file.read_bytes() != copy.read_bytes()  # the incident of 2026-10-24: same rows, other bytes
    assert _staging.content_hash(live_file) == _staging.content_hash(copy)

    # The PC's test home: only the linked environment data, read-only.
    backups.migrate("pc-test-home", test_home)
    assert sorted(entry.name for entry in test_home.iterdir()) == ["design", "work"]
    take = test_home / "work" / "takes" / "a.txt"
    assert take.read_text() == "take a"
    assert not take.stat().st_mode & stat.S_IWUSR and not take.parent.stat().st_mode & stat.S_IWUSR
    for path in [test_home / "design", test_home / "work", *test_home.rglob("*")]:  # writable, so it can be removed
        if not path.is_symlink():
            path.chmod(path.stat().st_mode | stat.S_IWUSR | stat.S_IXUSR)

    # The conductor's move into the cluster, in an agent's process with the owner's go quoted.
    write(setting / "states", VM_INACTIVE)
    monkeypatch.setenv(AGENT_MARKERS[0], "1")
    monkeypatch.setenv(_migrate.MOVE_WORDS, "no u can do the conductor move asap")
    out = backups.migrate("from-vm", conductor)
    for name in (AGENT_MARKERS[0], _migrate.MOVE_WORDS):
        monkeypatch.delenv(name)
    (cluster / "lost+found").mkdir(parents=True)
    monkeypatch.setenv(_migrate.IMAGE_VARIABLE, IMAGE)
    landed = backups.migrate("onto-cluster", cluster)
    monkeypatch.delenv(_migrate.IMAGE_VARIABLE)
    assert landed["snapshot"] == out["snapshot"] != moved["snapshot"]  # the newest vm-final, never the pc-final
    record = json.loads((cluster / _migrate.CLUSTER_RECORD).read_text())
    assert (record["namespace"], record["image"], record["jobs"], record["cpu_per_job"], record["max_memory_gb"]) == (
        "score", IMAGE, 16, 0.5, 64)  # the drive's size and image as the cluster runs them, never filled in by hand
    assert backups.compare(backups.read_manifest(conductor), backups.read_manifest(cluster)) == []

    # The command line: a data read when none passed this week, then a plain check; forget keeps pc-final; an
    # unforeseen failure leaves its failed record and propagates. Each leaves the record health reads.
    def locked_database(_home):
        raise sqlite3.OperationalError("database is locked")

    commands = [  # (argv, the backup put in its place or None, kind logged, ok, error logged)
        (["check"], None, "check-data", True, None),
        (["check"], None, "check", True, None),
        (["forget"], None, "forget", True, None),
        (["backup"], locked_database, "backup", False, "OperationalError: database is locked"),
    ]
    for argv, fault, kind, ok, error in commands:
        with monkeypatch.context() as patch:
            if fault:
                patch.setattr(backups, "backup", fault)
            try:
                assert command.main(argv) == 0, argv
            except sqlite3.OperationalError:
                assert fault, argv
            else:
                assert not fault, f"{argv}: the unforeseen failure was swallowed"
        logged = json.loads(sorted((setting / "logs-home" / "logs").glob("backup-*.json"))[-1].read_text())
        assert HEALTH_KEYS <= set(logged), (argv, logged)
        assert (logged["kind"], logged["ok"], logged["error"]) == (kind, ok, error), (argv, logged)
    assert backups.Restic().snapshots("pc-final")

    # Every refusal comes before anything is read or written: the repository and the home stay as they were.
    fresh, busy, empty = setting / "fresh", setting / "pc-busy", setting / "empty"
    (fresh / "logs").mkdir(parents=True)
    claim = {"commit": "abc", "worktree": "/w", "nodes": [], "started": runs.start_time(os.getpid())}
    write(busy / "runs" / "active.json", json.dumps({str(os.getpid()): claim}))
    agent = {AGENT_MARKERS[0]: "1"}
    refusals = [  # (case, mode or "backup", home, environment, systemctl's states or None, what the refusal names)
        ("backup before machine.json", "backup", fresh, {}, None, "machine.json"),
        ("a PC unit active", "from-pc", busy, {}, "inactive\ninactive\nactive\ninactive\n", "score-listen.service"),
        ("a run alive", "from-pc", busy, {}, None, f"pid {os.getpid()}"),
        ("no sizes record", "onto-conductor", empty,
         {"SCORE_CONDUCTOR_RECORD": str(setting / "missing.json")}, None, "sizes record"),
        ("conductor not empty", "onto-conductor", conductor, {}, None, "not empty"),
        ("test home not empty", "pc-test-home", conductor, {}, None, "not empty"),
        ("a VM unit active", "from-vm", conductor, {}, "active\n" + VM_INACTIVE[len("inactive\n"):],
         "score-sync.timer still active"),
        ("an agent's VM move without his go", "from-vm", conductor, agent, VM_INACTIVE, "owner's"),
        ("the cluster's home already", "from-vm", cluster, {}, VM_INACTIVE, "cluster's home already"),
        ("no image by digest", "onto-cluster", empty, {}, None, "by digest"),
        ("cluster not empty", "onto-cluster", pc, {_migrate.IMAGE_VARIABLE: IMAGE}, None, "not empty"),
        ("an agent under a yes done for the move", "from-pc", empty, {**agent, conductor_yes.YES_ID: given["id"]},
         None, "agent"),
        ("an agent naming no recorded yes", "from-pc", empty, {**agent, conductor_yes.YES_ID: "no-such-yes"}, None,
         "agent"),
    ] + [(f"an agent ({marker}) {mode}", mode, empty, {marker: "1"}, None, "agent")
         for marker in AGENT_MARKERS for mode in ("from-pc", "onto-conductor", "pc-test-home")]
    for case, mode, home, environment, states, names in refusals:
        write(setting / "states", states or UNITS_INACTIVE)
        before = (tree(repository), tree(home))
        with monkeypatch.context() as patch:
            for name, value in environment.items():
                patch.setenv(name, value)
            with pytest.raises(backups.Refused, match=names):
                backups.backup(home) if mode == "backup" else backups.migrate(mode, home)
        assert (tree(repository), tree(home)) == before, case

    # Each difference from a manifest is named: a changed row, a missing file, a changed byte, a changed object.
    (cluster / "design" / "plans" / "hangar.json").unlink()
    write(cluster / "work" / "takes" / "a.txt", "take b")
    blob = next(path for path in (cluster / "store" / "objects" / "blobs").iterdir())
    blob.chmod(0o644)
    blob.write_bytes(blob.read_bytes() + b" ")
    with sqlite3.connect(cluster / "dashboard" / "dashboard.sqlite3") as changed:
        changed.execute("insert into requests values ('another')")
    assert backups.compare(backups.read_manifest(conductor), backups.read_manifest(cluster)) == [
        "changed: dashboard/dashboard.sqlite3", "missing: design/plans/hangar.json", "changed: work/takes/a.txt",
        f"changed: store/objects/blobs/{blob.name}"]

    # A file that does not come back stops the move: with the PC's home gone, its link restores pointing at nothing.
    shutil.rmtree(pc / "work")
    with pytest.raises(backups.Mismatch) as stopped:
        backups.migrate("onto-conductor", setting / "conductor-again")
    assert stopped.value.differences == ["missing: work/takes/latest.txt"]
    assert not (setting / "conductor-again" / "machine.json").exists()

    # The password came from the reader only: it is in no file, and the repository opens with no other.
    written = [path for path in setting.rglob("*") if path.is_file() and "tools" not in path.relative_to(setting).parts]
    assert written and not [path for path in written if b"fixture-pass" in path.read_bytes()]
    reader = write(setting / "tools" / "reader", "#!/bin/sh\necho a-file-password\n")
    reader.chmod(0o755)
    with pytest.raises(backups.ResticFailed):
        backups.Restic().snapshots()
