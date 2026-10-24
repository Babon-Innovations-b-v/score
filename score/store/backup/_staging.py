"""The cockpit's SQLite databases, copied whole and consistent before a backup, and put back in place after a restore.

A database under dashboard/ is copied with SQLite's online backup (the same `sqlite3_backup` the CLI's `.backup` runs,
here through Python's sqlite3, so no CLI is needed): a copy of one consistent state, written transactions in its WAL
included, while the cockpit keeps writing. The copies sit in STAGING inside the home, the backup holds them in place
of the live files (and the live files' -wal, -shm and -journal are left out), and a restore moves each back to its own
path. Copying the same state twice gives the same bytes, so a copy's hash names the database's state.
"""
import hashlib
import os
import pathlib
import shutil
import sqlite3

STAGING = "backup-staging"
DASHBOARD = "dashboard"
HEADER = b"SQLite format 3\x00"
SIDE_FILES = ("-wal", "-shm", "-journal")


def is_database(path):
    """True for a file that starts with SQLite's header."""
    try:
        with open(path, "rb") as source:
            return source.read(len(HEADER)) == HEADER
    except OSError:
        return False


def databases(home):
    """The relative paths (under the home) of every SQLite database under dashboard/, sorted."""
    folder = pathlib.Path(home) / DASHBOARD
    if not folder.is_dir():
        return []
    return sorted(path.relative_to(home).as_posix() for path in folder.rglob("*")
                  if path.is_file() and not path.is_symlink() and is_database(path))


def content_hash(database):
    """sha256 of a database's content (its SQL dump), the same for every copy of one state whatever its file bytes."""
    digest = hashlib.sha256()
    connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
    try:
        for line in connection.iterdump():
            digest.update(line.encode() + b"\n")
    finally:
        connection.close()
    return digest.hexdigest()


def side_files(database):
    """The relative paths of a database's side files (its WAL, shared memory, rollback journal)."""
    return [database + suffix for suffix in SIDE_FILES]


def copy_database(source, destination):
    """`source` copied whole and consistent to `destination` with SQLite's online backup, the source opened read-only."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    reading = sqlite3.connect(f"file:{source}?mode=ro", uri=True)
    writing = sqlite3.connect(destination)
    try:
        reading.backup(writing)
    finally:
        writing.close()
        reading.close()
    os.chmod(destination, os.stat(source).st_mode & 0o777)


def stage(home, folder):
    """Every dashboard database of `home` copied into `folder` at its relative path; {relative path: copy}."""
    folder = pathlib.Path(folder)
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True)
    copies = {}
    for database in databases(home):
        copies[database] = folder / database
        copy_database(pathlib.Path(home) / database, copies[database])
    return copies


def put_in_place(home):
    """Move every staged copy a restore brought back (STAGING/dashboard/...) to its own path in `home`; the relative
    paths moved. A file already at a copy's path is an error: the backup left the live database out."""
    staged = pathlib.Path(home) / STAGING / DASHBOARD
    if not staged.is_dir():
        return []
    moved = []
    for copy in sorted(path for path in staged.rglob("*") if path.is_file()):
        relative = copy.relative_to(pathlib.Path(home) / STAGING).as_posix()
        target = pathlib.Path(home) / relative
        if target.exists():
            raise FileExistsError(f"{relative} is both restored and staged: the backup should have left it out")
        target.parent.mkdir(parents=True, exist_ok=True)
        copy.rename(target)
        moved.append(relative)
    return moved
