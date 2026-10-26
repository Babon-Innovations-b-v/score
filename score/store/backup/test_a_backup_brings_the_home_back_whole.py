"""The store's backups and the move: a fixture home made with the real Store API, backed up to a local restic
repository (a folder, no cloud), restored and compared; the move's refusals. The restic tests skip only when restic is
not installed (bootstrap.sh reports it).

Each test's break (applied once, seen red, reverted), in score/store/backup/:
- restores every kept file: _core.excludes drops REBUILT from its patterns.
- passes over lost+found: _core.excludes drops EMPTY_ENOUGH.
- live database whole: _core.excludes leaves the live database and its side files in.
- refused before machine.json: backup's machine.json check becomes `if False:`.
- the move names the machine: _migrate.write_identity drops the sizes record.
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

from score.store import AGENT_MARKERS, Store
from score.store import backup as backups
from score.store.backup import __main__ as command
from score.store.backup import conductor_yes

needs_restic = pytest.mark.skipif(shutil.which("restic") is None,
                                  reason="restic is not installed (bootstrap.sh lists it as missing)")
UNITS_INACTIVE = "inactive\ninactive\ninactive\ninactive\n"
COMMITTED_ROWS = 300


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


@pytest.fixture
def setting(tmp_path, monkeypatch):
    """The owner's process (no agent markers), a folder repository, a secret reader printing its password, and a
    systemctl shim answering from tmp_path/states (every PC unit inactive unless a test says otherwise)."""
    for marker in AGENT_MARKERS:
        monkeypatch.delenv(marker, raising=False)
    tools = tmp_path / "tools"
    reader = write(tools / "reader", "#!/bin/sh\n[ \"$1\" = score-backup-restic-password ] && echo fixture-pass\n")
    shim = write(tools / "systemctl", f"#!/bin/sh\ncat {tmp_path / 'states'}\n")
    for script in (reader, shim):
        script.chmod(0o755)
    write(tmp_path / "states", UNITS_INACTIVE)
    monkeypatch.setenv("PATH", f"{tools}:{os.environ['PATH']}")
    monkeypatch.setenv("SCORE_SECRET_READER", str(reader))
    monkeypatch.setenv("SCORE_BACKUP_REPO", str(tmp_path / "repository"))
    return tmp_path


def make_home(home):
    """A home with an output and a record in a real store, design, ledgers, run entries, work, a live WAL database
    with COMMITTED_ROWS rows, and everything a backup leaves out; the live connection (a write left open)."""
    store = Store.in_folder(home / "store")
    output = write(home / "scratch-output" / "model.json", '{"vertices": 8}')
    store.write_record("surfaces@hangar", "key1", {"output": store.put_tree(output.parent)})
    shutil.rmtree(home / "scratch-output")
    write(home / "design" / "plans" / "hangar.json", '{"rooms": 3}')
    write(home / "cloud" / "ledger.jsonl", '{"euros": 1.5}\n')
    write(home / "runs" / "run-1.json", '{"state": "ended"}')
    write(home / "work" / "takes" / "a.txt", "take a")
    write(home / "dashboard" / "exports" / "state.json", "{}")
    for rebuilt in ("cache/lib.bin", "store/cache/checkouts/x/f", "tmp/t", "tmp.Ab12/t", "downloads/d", "frozen/f",
                    "env/bin/python", "store-tests/s", "blender-mcp/b", "design/plans/hangar.json.12-34.partial"):
        write(home / rebuilt, "rebuilt")
    database = sqlite3.connect(home / "dashboard" / "dashboard.sqlite3")
    database.execute("pragma journal_mode=wal")
    database.execute("pragma wal_autocheckpoint=0")  # committed rows stay in the WAL, as in a busy cockpit
    database.execute("create table requests (n)")
    database.executemany("insert into requests values (?)", [(n,) for n in range(COMMITTED_ROWS)])
    database.commit()
    database.execute("insert into requests values (-1)")  # a write still open: never in a backup
    return database


def rows(path):
    """The rows of a restored database's requests table."""
    with sqlite3.connect(path) as database:
        return database.execute("select count(*) from requests").fetchone()[0]


@needs_restic
def test_a_backup_restores_every_kept_file_and_leaves_out_what_can_be_rebuilt(setting):
    home = setting / "home"
    live = make_home(home)
    write(home / "machine.json", "{}")
    backups.backup(home)
    drill = setting / "drill"
    backups.restore(drill, home=home)
    live.close()
    for kept in ("design/plans/hangar.json", "cloud/ledger.jsonl", "runs/run-1.json", "work/takes/a.txt",
                 "dashboard/exports/state.json"):
        assert (drill / kept).read_bytes() == (home / kept).read_bytes(), kept
    objects = sorted(path.relative_to(home) for path in (home / "store" / "objects").rglob("*") if path.is_file())
    assert objects and all((drill / name).read_bytes() == (home / name).read_bytes() for name in objects)
    restored = sorted(path.relative_to(drill).as_posix() for path in drill.rglob("*") if path.is_file())
    assert not any(name.startswith(("cache/", "store/cache/", "tmp/", "tmp.", "downloads/", "frozen/", "env/",
                                    "store-tests/", "blender-mcp/")) or name.endswith(".partial")
                   for name in restored), restored
    assert "backup-staging" not in {path.split("/")[0] for path in restored}


@needs_restic
def test_a_backup_passes_over_the_volumes_unreadable_lost_and_found(setting):
    home = setting / "home"
    make_home(home).close()
    write(home / "machine.json", "{}")
    (home / "lost+found").mkdir(mode=0o000)  # unreadable to the backup's user, as the volume's root-owned folder is
    try:
        assert backups.backup(home)["snapshot"]
    finally:
        (home / "lost+found").chmod(0o700)


@needs_restic
def test_a_live_database_is_backed_up_whole_with_only_its_committed_rows(setting):
    home = setting / "home"
    live = make_home(home)
    write(home / "machine.json", "{}")
    assert (home / "dashboard" / "dashboard.sqlite3-wal").stat().st_size > 0  # the rows are in the WAL, not the file
    backups.backup(home)
    live.close()
    drill = setting / "drill"
    backups.restore(drill, home=home)
    assert not (drill / "dashboard" / "dashboard.sqlite3-wal").exists()
    assert rows(drill / "dashboard" / "dashboard.sqlite3") == COMMITTED_ROWS


def test_a_plain_backup_is_refused_before_the_move_wrote_the_machine_identity(setting):
    home = setting / "home"
    (home / "logs").mkdir(parents=True)
    with pytest.raises(backups.Refused, match="machine.json"):
        backups.backup(home)
    assert not (setting / "repository").exists()


@needs_restic
def test_the_move_lands_the_pc_home_whole_and_names_the_machine(setting, monkeypatch):
    pc, conductor = setting / "pc", setting / "conductor"
    make_home(pc).close()
    (conductor / "lost+found").mkdir(parents=True)  # a fresh volume's own folder
    sizes = {"zone": "fr-par-2", "idle_type": "POP2-HM-2C-16G", "batch_type": "POP2-HM-16C-128G", "idle_cores": 2,
             "batch_cores": 16, "project": "score-conductor"}
    write(setting / "conductor.json", json.dumps(sizes))
    monkeypatch.setenv("SCORE_CONDUCTOR_RECORD", str(setting / "conductor.json"))
    moved = backups.migrate("from-pc", pc)
    landed = backups.migrate("onto-conductor", conductor)
    assert landed["snapshot"] == moved["snapshot"]
    identity = json.loads((conductor / "machine.json").read_text())
    assert identity["from"] == f"pc-final {moved['snapshot']}"
    assert {name: identity[name] for name in sizes} == sizes  # what makes it a conductor (score.conductor.machine)
    assert backups.compare(backups.read_manifest(pc), backups.read_manifest(conductor)) == []
    assert rows(conductor / "dashboard" / "dashboard.sqlite3") == COMMITTED_ROWS


@needs_restic
def test_a_changed_byte_a_missing_file_and_a_changed_object_are_each_named(setting):
    pc, conductor = setting / "pc", setting / "conductor"
    make_home(pc).close()
    backups.migrate("from-pc", pc)
    backups.migrate("onto-conductor", conductor)
    expected = backups.read_manifest(pc)
    write(conductor / "work" / "takes" / "a.txt", "take b")
    (conductor / "design" / "plans" / "hangar.json").unlink()
    blob = next(path for path in (conductor / "store" / "objects" / "blobs").iterdir())
    blob.chmod(0o644)
    blob.write_bytes(blob.read_bytes() + b" ")
    found = backups.compare(expected, backups.read_manifest(conductor))
    assert found == ["missing: design/plans/hangar.json", "changed: work/takes/a.txt",
                     f"changed: store/objects/blobs/{blob.name}"]


@needs_restic
def test_a_file_that_does_not_come_back_stops_the_move(setting):
    pc, conductor = setting / "pc", setting / "conductor"
    make_home(pc).close()
    (pc / "work" / "takes" / "latest.txt").symlink_to(pc / "work" / "takes" / "a.txt")  # a link into the PC's home
    backups.migrate("from-pc", pc)
    shutil.rmtree(pc / "work")  # the PC's home is gone: the link restored on the conductor points at nothing
    with pytest.raises(backups.Mismatch) as stopped:
        backups.migrate("onto-conductor", conductor)
    assert stopped.value.differences == ["missing: work/takes/latest.txt"]
    assert not (conductor / "machine.json").exists()


def test_the_move_from_the_pc_is_refused_while_a_unit_is_active(setting):
    pc = setting / "pc"
    make_home(pc).close()
    write(setting / "states", "inactive\ninactive\nactive\ninactive\n")
    with pytest.raises(backups.Refused, match="score-listen.service"):
        backups.migrate("from-pc", pc)
    assert not (setting / "repository").exists()


def test_the_move_from_the_pc_is_refused_while_a_run_is_alive(setting):
    from score.graph import runs

    pc = setting / "pc"
    make_home(pc).close()
    claim = {"commit": "abc", "worktree": "/w", "nodes": [], "started": runs.start_time(os.getpid())}
    write(pc / "runs" / "active.json", json.dumps({str(os.getpid()): claim}))
    with pytest.raises(backups.Refused, match=f"pid {os.getpid()}"):
        backups.migrate("from-pc", pc)


def test_the_move_onto_the_conductor_is_refused_without_its_sizes_record(setting, monkeypatch):
    monkeypatch.setenv("SCORE_CONDUCTOR_RECORD", str(setting / "missing.json"))
    with pytest.raises(backups.Refused, match="sizes record"):
        backups.migrate("onto-conductor", setting / "conductor")
    assert not (setting / "conductor" / "machine.json").exists()


def test_the_move_onto_the_conductor_is_refused_into_a_home_not_empty(setting):
    conductor = setting / "conductor"
    write(conductor / "dashboard" / "dashboard.sqlite3", "")
    with pytest.raises(backups.Refused, match="not empty"):
        backups.migrate("onto-conductor", conductor)
    with pytest.raises(backups.Refused, match="not empty"):
        backups.migrate("pc-test-home", conductor)


@pytest.mark.parametrize("mode", ["from-pc", "onto-conductor", "pc-test-home"])
@pytest.mark.parametrize("marker", AGENT_MARKERS)
def test_an_agents_process_never_moves_the_store(setting, monkeypatch, mode, marker):
    monkeypatch.setenv(marker, "1")
    with pytest.raises(backups.Refused, match="agent"):
        backups.migrate(mode, setting / "empty")
    assert not (setting / "repository").exists()


@needs_restic
def test_the_pc_test_home_holds_only_the_linked_environment_data_read_only(setting):
    pc, test_home = setting / "pc", setting / "pc-again"
    make_home(pc).close()
    backups.migrate("from-pc", pc)
    backups.migrate("pc-test-home", test_home)
    assert sorted(entry.name for entry in test_home.iterdir()) == ["design", "work"]
    take = test_home / "work" / "takes" / "a.txt"
    assert take.read_text() == "take a"
    assert not take.stat().st_mode & stat.S_IWUSR and not take.parent.stat().st_mode & stat.S_IWUSR
    for path in test_home.rglob("*"):  # writable again, so the test's folder can be removed
        path.chmod(path.stat().st_mode | stat.S_IWUSR)
    for folder in ("design", "work"):
        (test_home / folder).chmod(0o755)


@needs_restic
def test_a_data_read_runs_when_none_passed_this_week_and_its_log_keeps_the_health_shape(setting, monkeypatch):
    home = setting / "logs-home"
    monkeypatch.setattr(command, "PROPS_HOME", home)
    pc = setting / "pc"
    make_home(pc).close()
    backups.migrate("from-pc", pc)
    assert command.main(["check"]) == 0
    assert command.main(["check"]) == 0
    logged = [json.loads(path.read_text()) for path in sorted((home / "logs").glob("backup-*.json"))][-2:]
    assert [record["kind"] for record in logged] == ["check-data", "check"]
    assert all({"at", "kind", "ok", "snapshot", "files", "bytes", "seconds", "error"} <= set(record)
               for record in logged)
    assert command.main(["forget"]) == 0  # the pc-final snapshot is kept whatever the policy drops
    assert backups.Restic().snapshots("pc-final")


def test_an_unforeseen_failure_still_leaves_a_failed_record_and_propagates(setting, monkeypatch):
    home = setting / "logs-home"
    monkeypatch.setattr(command, "PROPS_HOME", home)

    def locked_database(_home):
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(backups, "backup", locked_database)
    with pytest.raises(sqlite3.OperationalError):
        command.main(["backup"])
    record = json.loads(sorted((home / "logs").glob("backup-*.json"))[-1].read_text())
    assert (record["kind"], record["ok"]) == ("backup", False)
    assert record["error"] == "OperationalError: database is locked"


@needs_restic
def test_the_password_comes_from_the_reader_only_and_lands_in_no_file(setting, monkeypatch):
    home = setting / "home"
    make_home(home).close()
    write(home / "machine.json", "{}")
    wrong = write(setting / "elsewhere" / "password", "a-file-password\n")
    monkeypatch.setenv("RESTIC_PASSWORD_FILE", str(wrong))  # dropped: the reader is the only way in
    monkeypatch.setenv("RESTIC_PASSWORD_COMMAND", f"cat {wrong}")
    backups.backup(home)
    written = [path for path in setting.rglob("*") if path.is_file() and "tools" not in path.relative_to(setting).parts]
    assert written and not [path for path in written if b"fixture-pass" in path.read_bytes()]
    reader = write(setting / "tools" / "reader", "#!/bin/sh\necho a-file-password\n")
    reader.chmod(0o755)
    with pytest.raises(backups.ResticFailed):
        backups.Restic().snapshots()  # the repository opens with the reader's password, no other


def test_an_agents_process_moves_the_store_only_under_the_owners_open_yes(setting, monkeypatch):
    monkeypatch.setenv(AGENT_MARKERS[0], "1")
    monkeypatch.setenv(conductor_yes.YES_HOME, str(setting / "pc"))
    with pytest.raises(conductor_yes.Refused):
        conductor_yes.record("", "Switch the conductor on?")
    given = conductor_yes.record("yes", "Switch the conductor on, about EUR 90 a month?")
    assert conductor_yes.open_yes("prepare")["id"] == given["id"]
    monkeypatch.setenv(conductor_yes.YES_ID, given["id"])
    assert _migrate_refusal() is None
    conductor_yes.mark_done(given, "move")
    assert "agent" in _migrate_refusal() and conductor_yes.open_yes("move") is None
    assert conductor_yes.open_yes("up")["id"] == given["id"], "each step is done on its own"
    monkeypatch.setenv(conductor_yes.YES_ID, "no-such-yes")
    assert "agent" in _migrate_refusal()


def _migrate_refusal():
    from score.store.backup import _migrate
    return _migrate.agent_refusal()


def test_two_copies_of_one_database_have_one_content_hash(tmp_path):
    """The move's manifest compares a database by its content: a restored copy differs in header bytes (2026-10-24).
    A live file with a write history and its online-backup copy hold the same rows in different bytes."""
    from score.store.backup import _staging
    source = tmp_path / "live.sqlite3"
    connection = sqlite3.connect(source)
    connection.execute("create table t (x)")
    connection.executemany("insert into t values (?)", [(str(n) * 500,) for n in range(200)])
    connection.commit()
    connection.execute("delete from t where rowid > 1")
    connection.commit()
    connection.close()
    copy = tmp_path / "a" / "copy.sqlite3"
    _staging.copy_database(source, copy)
    assert source.read_bytes() != copy.read_bytes()  # the case the incident was: same rows, other bytes
    assert _staging.content_hash(source) == _staging.content_hash(copy)
    changed = sqlite3.connect(copy)
    changed.execute("insert into t values ('another')")
    changed.commit()
    changed.close()
    assert _staging.content_hash(source) != _staging.content_hash(copy)  # a changed row is a changed hash
