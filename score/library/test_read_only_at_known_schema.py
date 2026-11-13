"""The library reader reads score_lib's files only at the schema version it was written for: every entry, every
version, in path order, one entry and one kind's index read whole; a file of another version is refused (Unread,
naming the version), never half read; the library it reads is the folder SCORE_LIB_ROOT names, or none.

Run: PROPS_HOME=$(mktemp -d) .venv/bin/python -m pytest -q score/library/test_read_only_at_known_schema.py

The test turns red under each break written here (each applied once and seen red, 2026-10-26; again after the fold,
2026-11-13):
- reading: in library.entries drop `sorted(...)`, or change ENTRY_FILES to "entries/*/*/1/entry.json".
- refusing: make library.checked return the record without comparing its schema.
- environment: make root_from_environment skip `.strip()`.
"""
import json
import pathlib

import pytest

from score import library

ALL_ENTRIES = ["model/crate@1", "model/crate@2", "model/lamp@1"]
INDEX_ENTRIES = [{"address": "model/lamp@1"}]


def write_library(root, lamp_schema, index_schema):
    """A library of three model entries (crate at versions 2 and 1, lamp at 1), written out of path order, and the
    model index; the lamp entry and the index carry the schemas given."""
    for entry_id, version in (("lamp", 1), ("crate", 2), ("crate", 1)):
        folder = root / "entries" / "model" / entry_id / str(version)
        folder.mkdir(parents=True)
        (folder / "entry.json").write_text(json.dumps({
            "schema": lamp_schema if entry_id == "lamp" else library.ENTRY_SCHEMA, "kind": "model",
            "id": entry_id, "version": version, "address": f"model/{entry_id}@{version}"}))
    (root / "index").mkdir()
    (root / "index" / "model.json").write_text(json.dumps({"schema": index_schema, "kind": "model",
                                                           "entries": INDEX_ENTRIES}))


def answer(read):
    """What one read gives: its value, or ("Unread", message) when it refuses."""
    try:
        return read()
    except library.Unread as refusal:
        return ("Unread", str(refusal))


def refused(version):
    """Matches a refusal whose message names `version`."""
    return lambda got: isinstance(got, tuple) and got[0] == "Unread" and version in got[1]


@pytest.mark.parametrize("environment, lamp_schema, index_schema, expected", [
    pytest.param(" {root} ", "score-lib-entry/1", "score-lib-index/1",
                 {"entries": ALL_ENTRIES, "crate@2": "model/crate@2", "lamp@1": "model/lamp@1",
                  "index": INDEX_ENTRIES}, id="known-schemas-padded-root"),
    pytest.param("{root}", "score-lib-entry/2", "score-lib-index/1",
                 {"entries": refused("score-lib-entry/2"), "crate@2": "model/crate@2",
                  "lamp@1": refused("score-lib-entry/2"), "index": INDEX_ENTRIES}, id="entry-of-another-version"),
    pytest.param("{root}", "score-lib-entry/1", "score-lib-index/2",
                 {"entries": ALL_ENTRIES, "crate@2": "model/crate@2", "lamp@1": "model/lamp@1",
                  "index": refused("score-lib-index/2")}, id="index-of-another-version"),
    pytest.param(None, "score-lib-entry/1", "score-lib-index/1", None, id="root-unset"),
    pytest.param("  ", "score-lib-entry/1", "score-lib-index/1", None, id="root-blank"),
])
def test_read_only_at_known_schema(tmp_path, monkeypatch, environment, lamp_schema, index_schema, expected):
    """The library SCORE_LIB_ROOT names is read through every reader; each read gives its records, in path order, or
    refuses naming the unknown version. A folder lists in whatever order its file system keeps; the listing is
    reversed here so path order cannot come by luck. `expected` None: no library is named."""
    write_library(tmp_path, lamp_schema, index_schema)
    if environment is None:
        monkeypatch.delenv("SCORE_LIB_ROOT", raising=False)
    else:
        monkeypatch.setenv("SCORE_LIB_ROOT", environment.format(root=tmp_path))
    listing = pathlib.Path.glob
    monkeypatch.setattr("pathlib.Path.glob", lambda self, pattern: reversed(sorted(listing(self, pattern))))
    found = library.root_from_environment()
    if expected is None:
        assert found is None, found
        return
    assert str(found) == str(tmp_path)
    got = {
        "entries": answer(lambda: [record["address"] for record in library.entries(found)]),
        "crate@2": answer(lambda: library.entry(found, "model", "crate", 2)["address"]),
        "lamp@1": answer(lambda: library.entry(found, "model", "lamp", 1)["address"]),
        "index": answer(lambda: library.index(found, "model")["entries"]),
    }
    for read, want in expected.items():
        assert want(got[read]) if callable(want) else got[read] == want, f"{read}: got {got[read]!r}, want {want!r}"
