"""The store's reboot safety: a write cut by a reboot leaves the whole object or none, an unreadable object is
quarantined and read as absent (an owner's decision excepted), and none of it is in any row's key.

Run: .venv/bin/python score/store/durable_test.py
"""
import multiprocessing
import os
import pathlib
import signal
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from score.store import Store, durable  # noqa: E402

REPO = pathlib.Path(__file__).resolve().parents[2]
PLAIN = {name: vars(Store).get(name) for name in durable.METHODS}  # Store as score/store/__init__.py writes it
durable.install()


def a_store():
    return Store.in_folder(tempfile.mkdtemp())


def test_the_reboot_safety_is_in_no_rows_key():
    """C9 review: the durability edits sat in score/store/__init__.py, which every stage that calls the store hashes,
    and moving that file into FRAMEWORK instead dropped it and the runtime store from 44 paid rows' keys; no carry
    kept them. Here neither file changes, and no stage's code version reads durable.py."""
    from score import graph, stages
    from score.graph import _code
    assert REPO / "score/store/__init__.py" not in _code.FRAMEWORK
    reached = [row.name for row in stages.STAGES
               if REPO / "score/store/durable.py" in _code.source_files(graph.code_functions(row))]
    assert reached == [], reached
    calls_the_store = [row.name for row in stages.STAGES
                       if REPO / "score/store/__init__.py" in _code.source_files(graph.code_functions(row))]
    assert calls_the_store, "no stage reads score/store/__init__.py: this check would prove nothing"


def plain_store():
    """Store's methods as score/store/__init__.py has them, before any install."""
    for name, method in PLAIN.items():
        if method is None:
            delattr(Store, name)
        else:
            setattr(Store, name, method)


def test_the_runner_and_the_owners_commands_install_the_reboot_safety():
    from score import graph
    from score.review import __main__ as owner
    default = vars(Store)["default"]
    try:
        plain_store()
        graph.Runner((), None, a_store())
        assert all(vars(Store)[name] is method for name, method in durable.METHODS.items())
        plain_store()
        Store.default = classmethod(lambda cls: a_store())  # never the live store
        try:
            owner.main(["page", "clean@hangar"])
        except Exception:  # a node this empty store lacks: only the install before the page counts here
            pass
        assert all(vars(Store)[name] is method for name, method in durable.METHODS.items())
    finally:
        Store.default = default
        durable.install()


def test_a_write_killed_between_its_partial_file_and_its_link_leaves_no_object():
    """C9: a machine that goes down mid-write leaves the whole object or none, never a cut one a later run reads."""
    store = a_store()

    def killed_at_the_link():
        os.link = lambda source, target: os.kill(os.getpid(), signal.SIGKILL)
        store.write_record("clean@hangar", "k1", {"finished": "1"})

    process = multiprocessing.get_context("fork").Process(target=killed_at_the_link)
    process.start()
    process.join()
    assert process.exitcode == -signal.SIGKILL
    assert store.record("clean@hangar", "k1") is None and store.objects.keys("records/") == []
    store.write_record("clean@hangar", "k1", {"finished": "2"})  # the key is free for the run made again
    assert store.record("clean@hangar", "k1") == {"finished": "2"}


def test_an_empty_or_unparsable_object_is_quarantined_and_read_as_absent():
    """C9: a 0-byte record after a WSL restart made every later run fail on reading it."""
    store = a_store()
    empty = store.objects.path("records/clean@hangar/k1.json")
    cut = store.objects.path("judgements/clean@hangar/k1/t.json")
    empty.parent.mkdir(parents=True)
    empty.write_bytes(b"")
    cut.parent.mkdir(parents=True)
    cut.write_text('{"at": "ab')
    assert store.record("clean@hangar", "k1") is None and store.record("clean@hangar", "k1") is None
    assert store.judgements("clean@hangar", "k1") == []
    assert not empty.exists() and not cut.exists()
    quarantined = sorted(path.name for path in (store.cache.parent / "quarantine").rglob("*") if path.is_file())
    assert [name.split(".json")[0] for name in quarantined] == ["k1", "t"], quarantined
    store.write_record("clean@hangar", "k1", {"finished": "1"})
    assert store.record("clean@hangar", "k1") == {"finished": "1"}


def test_an_unreadable_owner_decision_stops_the_read_and_stays_where_it_is():
    """C9 review: a cut reject read as absent let the accept it undid stand again, and a cut accept read as absent
    let a paid row be bought again as a fresh buy; an owner's decision is never moved or read as absent."""
    store = a_store()
    store.write_accept("clean@hangar", {"output": "o1", "at": "1", "by": "owner"})
    readers = {"rejects/clean@hangar/t.json": (lambda: store.accepted("clean@hangar"),
                                              lambda: store.rejected("clean@hangar", "o1")),
               "accepts/clean@hangar/t.json": (lambda: store.accepted("clean@hangar"),
                                              lambda: store.rejected("clean@hangar", "o1")),
               "waivers/clean@hangar/k/c.json": (lambda: store.waivers("clean@hangar", "k"),),
               "spend-yes/clean@hangar/k.json": (lambda: store.spend_yes("clean@hangar", "k"),)}
    for key, reads in readers.items():
        for text in ("", '{"output": "o1", "at": "2"'):
            path = store.objects.path(key)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
            for read in reads:
                try:
                    read()
                except durable.UnreadableOwnerObject as refused:
                    assert key in str(refused), refused
                else:
                    raise AssertionError(f"a cut {key} was read as absent")
            assert path.read_text() == text  # never moved
            path.unlink()
    assert not (store.cache.parent / "quarantine").exists()
    assert store.accepted("clean@hangar") == "o1"


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[2] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
