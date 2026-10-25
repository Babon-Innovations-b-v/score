"""The library reader: entries and indexes read at the schema version it knows, another version refused.

Run: .venv/bin/python score/library/library_test.py
"""
import json
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from score import library  # noqa: E402


def a_library():
    root = pathlib.Path(tempfile.mkdtemp())
    for entry_id, version in (("crate", 1), ("crate", 2), ("lamp", 1)):
        folder = root / "entries" / "model" / entry_id / str(version)
        folder.mkdir(parents=True)
        (folder / "entry.json").write_text(json.dumps({"schema": library.ENTRY_SCHEMA, "kind": "model",
                                                       "id": entry_id, "version": version,
                                                       "address": f"model/{entry_id}@{version}"}))
    (root / "index").mkdir()
    (root / "index" / "model.json").write_text(json.dumps({"schema": library.INDEX_SCHEMA, "kind": "model",
                                                           "entries": [{"address": "model/lamp@1"}]}))
    return root


def test_entries_and_indexes_are_read_at_their_version():
    root = a_library()
    assert [record["address"] for record in library.entries(root)] == ["model/crate@1", "model/crate@2",
                                                                         "model/lamp@1"]
    assert library.entry(root, "model", "crate", 2)["version"] == 2
    assert library.index(root, "model")["entries"] == [{"address": "model/lamp@1"}]


def test_another_schema_version_is_refused():
    root = a_library()
    path = root / "entries" / "model" / "lamp" / "1" / "entry.json"
    path.write_text(json.dumps({**json.loads(path.read_text()), "schema": "score-lib-entry/2"}))
    for read in (lambda: library.entries(root), lambda: library.entry(root, "model", "lamp", 1)):
        try:
            read()
        except library.Unread as unread:
            assert "score-lib-entry/2" in str(unread), unread
        else:
            raise AssertionError("an entry of another schema version was read")


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[2] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
