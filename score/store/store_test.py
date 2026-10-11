"""The store keeps every output by its content's hash, overwrites nothing, and moves the accepted output only by an
accept.

Run: .venv/bin/python score/store/store_test.py
"""
import multiprocessing
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from score.store import AGENT_MARKERS, RUNNER, Store, file_hash, tree_hash, tree_listing  # noqa: E402

REPO = pathlib.Path(__file__).resolve().parents[2]


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


def test_a_checked_out_file_made_writable_leaves_the_stored_bytes_alone():
    """Fault (review of step 0, 2026-10-11): a checkout was a hard link sharing the stored blob's inode, so a stage
    that chmod-ed a checked-out file and wrote it changed the stored output in place."""
    store = a_store()
    output = store.put_tree(a_folder({"a.txt": "a"}))
    checked = store.checkout(output) / "a.txt"
    checked.chmod(0o644)
    checked.write_text("changed")
    sha = store.listing(output)["a.txt"]
    assert file_hash(store.objects.path(f"blobs/{sha}")) == sha, "the stored bytes changed through a checkout"
    assert (store.checkout(output) / "a.txt").read_text() == "a", "a changed checkout was handed out again"


def owner_write(environment, area="acc" + "epts", by="owner"):
    """Write into an owner's area of the framework's own store from a fresh Python with this environment; its exit
    and error."""
    code = ("from score.store import Store; "
            f"Store.default().write_once('{area}/a@b/{by}.json', {{'output': 'o', 'at': '1', 'by': '{by}'}})")
    done = subprocess.run([sys.executable, "-c", code], cwd=REPO, env=environment, capture_output=True, text=True)
    return done.returncode, done.stderr


def test_an_agent_cannot_write_the_owners_areas_of_the_framework_store():
    """Fault (review of step 0): `Store.default().write_once("acc"+"epts/...")` from an agent's Python wrote an accept;
    only a hook's text match stood in the way."""
    home = tempfile.mkdtemp()
    owner = {name: value for name, value in os.environ.items() if name not in AGENT_MARKERS}
    agent = {**owner, "CLAUDECODE": "1"}
    status, error = owner_write({**agent, "PROPS_HOME": home})
    assert status != 0 and "only the owner" in error, (status, error)
    assert not list(pathlib.Path(home).rglob("*.json"))
    assert owner_write({**agent, "PROPS_HOME": home}, "rej" + "ects")[0] != 0
    assert owner_write({**agent, "PROPS_HOME": home}, "rej" + "ects", RUNNER)[0] != 0  # a reject is never the runner's
    assert owner_write({**agent, "PROPS_HOME": home}, by=RUNNER)[0] == 0  # the runner's automatic accept
    assert owner_write({**owner, "PROPS_HOME": home})[0] == 0
    test_store = Store.in_folder(tempfile.mkdtemp())  # a test's or trial's own store stays writable
    test_store.write_accept("a@b", {"output": "o", "at": "2026-10-11T10:00:00+00:00"})


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


def at_once(work, count=8):
    """Run `work(number)` in `count` forked processes released together; what each sent back, sorted."""
    fork = multiprocessing.get_context("fork")
    ready, pipes = fork.Event(), [fork.Pipe(duplex=False) for _ in range(count)]

    def one(number, sending):
        ready.wait()
        try:
            sending.send(work(number))
        except Exception as error:  # noqa: BLE001 - a process's error is its answer, so the test fails, never hangs
            sending.send(f"{type(error).__name__}: {error}")

    processes = [fork.Process(target=one, args=(number, sending)) for number, (_, sending) in enumerate(pipes)]
    for process in processes:
        process.start()
    for _, sending in pipes:
        sending.close()
    ready.set()
    found = sorted(receiving.recv() for receiving, _ in pipes)
    for process in processes:
        process.join()
    return found


def test_of_processes_writing_one_key_at_once_exactly_one_writes_it():
    """Fault (the coordinator, 2026-10-11): lines run side by side now; a check-then-write let two processes both
    write a write-once key, and a reader could read half a file."""
    store = a_store()

    def write(number):
        try:
            store.write_record("clean@hangar", "k1", {"number": number})
            return "written"
        except FileExistsError:
            return "refused"

    assert at_once(write) == ["refused"] * 7 + ["written"]
    assert store.record("clean@hangar", "k1")["number"] in range(8)
    assert not list(store.objects.root.rglob("*.partial"))


def test_processes_storing_and_checking_out_one_output_at_once_all_find_it_whole():
    store, folder = a_store(), a_folder({"a.txt": "one", "b/c.txt": "two" * 100000})
    output = tree_hash(folder)
    assert at_once(lambda number: store.put_tree(folder)) == [output] * 8
    listing = store.listing(output)
    assert at_once(lambda number: str(tree_listing(store.checkout(output)) == listing), 16) == ["True"] * 16
    assert not list(store.objects.root.rglob("*.partial")) and not list(store.cache.rglob("*.partial"))


def test_two_runs_of_one_node_never_share_a_scratch_folder():
    """Two runs making one key at once each get their own folder: a second run once wiped the first's work and the
    first's cleanup removed the second's input list (the surface test's arms, 2026-10-11)."""
    root = pathlib.Path(tempfile.mkdtemp())
    try:
        store = Store.in_folder(root)
        first = store.making("same-key")
        (first / "work.txt").write_text("the first run's work")
        second = store.making("same-key")
        assert second != first and (first / "work.txt").exists() and not any(second.iterdir())
    finally:
        shutil.rmtree(root)


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
