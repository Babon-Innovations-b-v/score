"""The store keeps every output by its content's hash, overwrites nothing, and moves the accepted output only by an
accept.

Run: .venv/bin/python score/store/store_test.py
"""
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from score.store import Store, tree_hash  # noqa: E402


def a_store():
    return Store.in_folder(tempfile.mkdtemp())


def a_folder(files):
    folder = pathlib.Path(tempfile.mkdtemp())
    for name, text in files.items():
        (folder / name).parent.mkdir(parents=True, exist_ok=True)
        (folder / name).write_text(text)
    return folder


def test_an_output_is_named_by_its_content_and_stored_once():
    store = a_store()
    first = store.put_tree(a_folder({"stage.usda": "#usda 1.0", "layers/base.usda": "base"}))
    again = store.put_tree(a_folder({"stage.usda": "#usda 1.0", "layers/base.usda": "base"}))
    other = store.put_tree(a_folder({"stage.usda": "#usda 1.0", "layers/base.usda": "changed"}))
    assert first == again != other
    assert first == tree_hash(a_folder({"stage.usda": "#usda 1.0", "layers/base.usda": "base"}))
    blobs = store.objects.keys("blobs/")
    assert len(blobs) == 3, blobs  # the shared stage.usda is kept once


def test_a_checkout_gives_the_output_back_read_only():
    store = a_store()
    output = store.put_tree(a_folder({"a.txt": "a", "deep/b.txt": "b"}))
    folder = store.checkout(output)
    assert (folder / "deep/b.txt").read_text() == "b"
    try:
        (folder / "a.txt").write_text("changed")
    except PermissionError:
        return
    raise AssertionError("a stored output could be written over")


def test_nothing_in_the_store_is_overwritten():
    store = a_store()
    store.write_record("clean@hangar", "k1", {"finished": "1"})
    try:
        store.write_record("clean@hangar", "k1", {"finished": "2"})
    except FileExistsError:
        assert store.record("clean@hangar", "k1") == {"finished": "1"}
        return
    raise AssertionError("a finish record was written over")


def test_the_accepted_output_is_the_newest_accept_and_nothing_else_moves_it():
    store = a_store()
    first = store.put_tree(a_folder({"a": "1"}))
    assert store.accepted("clean@hangar") is None
    store.write_accept("clean@hangar", {"output": first, "at": "2026-10-11T10:00:00+00:00"})
    store.put_tree(a_folder({"a": "2"}))  # a newer output lands beside it
    assert store.accepted("clean@hangar") == first
    second = store.put_tree(a_folder({"a": "3"}))
    store.write_accept("clean@hangar", {"output": second, "at": "2026-10-11T11:00:00+00:00"})
    assert store.accepted("clean@hangar") == second
    assert [accept["output"] for accept in store.accepts("clean@hangar")] == [first, second]


def test_evidence_is_kept_by_check_and_output_and_missing_is_none():
    store = a_store()
    output = store.put_tree(a_folder({"a": "1"}))
    assert store.evidence_file("resting", output) is None and store.evidence_hash("resting", output) is None
    store.put_evidence("resting", output, a_folder({"drop.json": "{}"}) / "drop.json")
    assert store.evidence_file("resting", output).read_text() == "{}"


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
