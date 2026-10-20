"""The one reader of the creator's library on the score side (ADR-0007): score reads score_lib's files only here,
and runs it only through its `score-lib` command (score/stages/library/backend.py; tools/library/library_files.py
fetches its files).

    library.root_from_environment()       # SCORE_LIB_ROOT as a path, or None when it is not set
    library.entries(root)                 # every entry.json record, every version, in path order
    library.entry(root, kind, id, version)
    library.index(root, kind)             # index/<kind>.json

Every file is checked against the schema version this reader was written for (`ENTRY_SCHEMA`, `INDEX_SCHEMA`); a
file of another version is refused (`Unread`), never half read. A new score_lib schema is a change here first.
Pure: json and pathlib only, so the hosted cockpit may import it.
"""
import json
import os
import pathlib

ENTRY_SCHEMA = "score-lib-entry/1"
INDEX_SCHEMA = "score-lib-index/1"
ENTRY_FILES = "entries/*/*/*/entry.json"


class Unread(ValueError):
    """A library file of a schema version this reader does not know."""


def checked(record, schema, path):
    """The record, when it says `schema`; Unread naming the file and both versions otherwise."""
    if record.get("schema") != schema:
        raise Unread(f"{path}: schema {record.get('schema')!r}, this reader knows {schema!r}")
    return record


def read_json(path, schema):
    return checked(json.loads(pathlib.Path(path).read_text()), schema, path)


def root_from_environment():
    """The library folder SCORE_LIB_ROOT names, or None when it is not set."""
    root = os.environ.get("SCORE_LIB_ROOT", "").strip()
    return pathlib.Path(root).expanduser() if root else None


def entries(root):
    """Every entry.json record of the library folder, every version (withdrawn ones too), in path order."""
    return [read_json(path, ENTRY_SCHEMA) for path in sorted(pathlib.Path(root).expanduser().glob(ENTRY_FILES))]


def entry(root, kind, entry_id, version):
    """One entry's record (`<kind>/<id>@<version>`)."""
    return read_json(pathlib.Path(root).expanduser() / "entries" / kind / entry_id / str(version) / "entry.json",
                     ENTRY_SCHEMA)


def index(root, kind):
    """The library's index of one kind: {schema, kind, entries: [{address, digest, state, tags, ...}]}."""
    return read_json(pathlib.Path(root).expanduser() / "index" / f"{kind}.json", INDEX_SCHEMA)
