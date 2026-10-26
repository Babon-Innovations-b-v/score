"""The library reader reads score_lib's files only at the schema version it was written for: every entry, every
version, in path order, one entry and one kind's index read whole; a file of another version is refused (Unread,
naming the version), never half read.

Run: PROPS_HOME=$(mktemp -d) .venv/bin/python -m pytest -q score/library/test_read_only_at_known_schema.py

Each test turns red under the break written beside it (each applied once and seen red, 2026-10-26):
- reading: in library.entries drop `sorted(...)`, or change ENTRY_FILES to "entries/*/*/1/entry.json".
- refusing: make library.checked return the record without comparing its schema.
- environment: make root_from_environment skip `.strip()`.
"""
import json
import pathlib

import pytest

from score import library


@pytest.fixture
def root(tmp_path):
    """A library of three model entries (crate at versions 2 and 1, lamp at 1), written out of path order, and the
    model index."""
    for entry_id, version in (("lamp", 1), ("crate", 2), ("crate", 1)):
        folder = tmp_path / "entries" / "model" / entry_id / str(version)
        folder.mkdir(parents=True)
        (folder / "entry.json").write_text(json.dumps({"schema": "score-lib-entry/1", "kind": "model",
                                                       "id": entry_id, "version": version,
                                                       "address": f"model/{entry_id}@{version}"}))
    (tmp_path / "index").mkdir()
    (tmp_path / "index" / "model.json").write_text(json.dumps({"schema": "score-lib-index/1", "kind": "model",
                                                               "entries": [{"address": "model/lamp@1"}]}))
    return tmp_path


def test_every_entry_every_version_is_read_in_path_order(root, monkeypatch):
    """A folder lists in whatever order its file system keeps; the listing is reversed here so path order cannot come
    by luck."""
    listing = pathlib.Path.glob
    monkeypatch.setattr("pathlib.Path.glob", lambda self, pattern: reversed(sorted(listing(self, pattern))))
    assert [record["address"] for record in library.entries(root)] == [
        "model/crate@1", "model/crate@2", "model/lamp@1"]
    assert library.entry(root, "model", "crate", 2)["address"] == "model/crate@2"
    assert library.index(root, "model")["entries"] == [{"address": "model/lamp@1"}]


def test_an_entry_of_another_schema_version_is_refused_by_every_read(root):
    path = root / "entries" / "model" / "lamp" / "1" / "entry.json"
    path.write_text(json.dumps({**json.loads(path.read_text()), "schema": "score-lib-entry/2"}))
    for read in (lambda: library.entries(root), lambda: library.entry(root, "model", "lamp", 1)):
        with pytest.raises(library.Unread, match="score-lib-entry/2"):
            read()


def test_an_index_of_another_schema_version_is_refused(root):
    path = root / "index" / "model.json"
    path.write_text(json.dumps({**json.loads(path.read_text()), "schema": "score-lib-index/2"}))
    with pytest.raises(library.Unread, match="score-lib-index/2"):
        library.index(root, "model")


@pytest.mark.parametrize("value, expected", [(None, None), ("  ", None), (" /lib/x ", "/lib/x")])
def test_the_root_comes_from_score_lib_root_or_is_none(monkeypatch, value, expected):
    if value is None:
        monkeypatch.delenv("SCORE_LIB_ROOT", raising=False)
    else:
        monkeypatch.setenv("SCORE_LIB_ROOT", value)
    found = library.root_from_environment()
    assert (None if found is None else str(found)) == expected
