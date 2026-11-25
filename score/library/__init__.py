"""The one reader of the creator's library on the score side (ADR-0007): score reads score_lib's files only here,
and runs it only through its `score-lib` command (score/stages/library/backend.py; tools/library/library_files.py
fetches its files).

    library.root_from_environment()       # SCORE_LIB_ROOT as a path, or None when it is not set
    library.entries(root)                 # every entry.json record, every version, in path order
    library.entry(root, kind, id, version)
    library.index(root, kind)             # index/<kind>.json
    library.replacement(record)           # the address a withdrawn entry names as its replacement, or None
    library.replaced_end(root, address)   # the address at the end of an entry's replacement chain
    library.command(values)               # the library's own command as words (SCORE_LIB_COMMAND, else score-lib)

An entry is MIT unless it carries a `licence` block ({id, source, credit, url}: an adopted set's CC-BY-4.0 part, its
credit kept with it), and a withdrawn entry may name the entry that replaces it (`replaced_by`,
`<kind>/<id>@<version>`), so a place laid again takes the replacement (#155).

Every file is checked against the schema version this reader was written for (`ENTRY_SCHEMA`, `INDEX_SCHEMA`); a
file of another version is refused (`Unread`), never half read. A new score_lib schema is a change here first.
Pure: json, os, pathlib and shlex only, so the hosted cockpit may import it.
"""
import json
import os
import pathlib
import shlex

ENTRY_SCHEMA = "score-lib-entry/1"
INDEX_SCHEMA = "score-lib-index/1"
ENTRY_FILES = "entries/*/*/*/entry.json"
COMMAND = "score-lib"  # the library's command when SCORE_LIB_COMMAND names none


class Unread(ValueError):
    """A library file of a schema version this reader does not know."""


def checked(record, schema, path):
    """The record, when it says `schema`; Unread naming the file and both versions otherwise."""
    if record.get("schema") != schema:
        raise Unread(f"{path}: schema {record.get('schema')!r}, this reader knows {schema!r}")
    return record


def read_json(path, schema):
    return checked(json.loads(pathlib.Path(path).read_text()), schema, path)


def command(values):
    """The library's own command as words: `values`' SCORE_LIB_COMMAND split as a shell splits it, else COMMAND. Every
    score-side run of the library builds its command here (#38)."""
    return shlex.split(values.get("SCORE_LIB_COMMAND") or COMMAND)


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


def replacement(record):
    """The address a withdrawn entry names as its replacement (`replaced_by`), or None: an entry in force, or one
    withdrawn with nothing in its place."""
    return record.get("replaced_by") or None if record.get("state") == "withdrawn" else None


def replaced_end(root, address):
    """The address at the end of `address`'s replacement chain: itself when its entry is in force, names no
    replacement or is not held, else each replacement followed in turn (the end may still be withdrawn, with nothing
    in its place). ValueError on a chain that comes back on itself."""
    seen = [address]
    while True:
        kind, _, rest = address.partition("/")
        entry_id, _, version = rest.partition("@")
        path = pathlib.Path(root).expanduser() / "entries" / kind / entry_id / version / "entry.json"
        following = replacement(read_json(path, ENTRY_SCHEMA)) if version and path.is_file() else None
        if not following:
            return address
        if following in seen:
            raise ValueError(f"{seen[0]}: its replacements come back on themselves ({' -> '.join(seen + [following])})")
        seen.append(following)
        address = following
