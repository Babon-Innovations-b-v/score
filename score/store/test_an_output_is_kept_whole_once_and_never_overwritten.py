"""The store keeps every output by its content's hash, once, whole and read-only, overwrites nothing (of processes
writing one key at once exactly one lands), moves the accepted output only by an accept, keeps an agent out of the
owner's areas, and survives a reboot: a cut write leaves the whole object or none, an unreadable object is quarantined
and read as absent except an owner's decision, which stops the read and stays put. The reboot safety is in no row's
key. Every case runs on a store of its own in the temp folder.

Each test's break (applied once, seen red, reverted), in score/store/__init__.py unless named:
- named by content: durable.put_tree names the output with a random field added to its listing.
- checkout read-only: place_blob chmods the copy 0o644.
- checkout links the blob: linked_read_only returns False at its start.
- writable blob never linked: linked_read_only drops its write-bit check.
- relink only whole copies: relink drops `or file_hash(path) != sha`.
- agent kept out of owner areas: write_once's agent check ends `and False`.
- nothing overwritten: durable.write_once drops its exists check and copies over the target instead of linking.
- newest accept: current_accept returns `standing[0]`.
- evidence per check and output: evidence_key drops the output.
- one key at once: durable.write_once copies over the target instead of linking it.
- store and check out at once: checkout's lock is per process (`{output}.{pid}.lock`).
- scratch folders: making returns one folder per key.
- in no row's key: making imports score.store.durable.
- runner installs it: score/graph/__init__.py's Runner skips durable.install().
- killed between partial and link: durable.write_once writes a cut object at the target first.
- quarantined: durable.read reads an unreadable object as absent without quarantining it.
- owner decision: durable.read's owner-area check becomes `if False:`.

Run: PROPS_HOME=$(mktemp -d) .venv/bin/python score/store/test_an_output_is_kept_whole_once_and_never_overwritten.py
"""
import multiprocessing
import os
import pathlib
import runpy
import shutil
import signal
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from score.store import AGENT_MARKERS, RUNNER, Store, durable, file_hash, tree_hash, tree_listing  # noqa: E402

REPO = pathlib.Path(__file__).resolve().parents[2]
PLAIN = {name: vars(Store).get(name) for name in durable.METHODS}  # Store as score/store/__init__.py writes it
durable.install()  # as the runner and the owner's commands run the store


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


def test_a_checkout_links_the_stored_bytes_and_no_write_through_it_reaches_them():
    """2026-10-27: checkouts copied every output they gave out (16 GB in an hour beside a 22 GB store on the conductor).
    A checkout is a hard link to the read-only blob: no second copy, a write through it is refused, and a save that
    replaces the file or adds one changes the checkout's entries only, never the blob."""
    store = a_store()
    output = store.put_tree(a_folder({"a.txt": "a", "b.txt": "b"}))
    blob = store.objects.path(f"blobs/{store.listing(output)['a.txt']}")
    folder = store.checkout(output)
    assert (folder / "a.txt").samefile(blob) and blob.stat().st_nlink == 2, "a checkout copied the stored bytes"
    for write in (lambda: open(folder / "a.txt", "r+b"), lambda: open(folder / "a.txt", "ab"),
                  lambda: (folder / "a.txt").write_text("changed")):
        try:
            write()
        except PermissionError:
            continue
        raise AssertionError("a stored file could be written through its checkout")
    (folder / "saved.txt").write_text("a save beside it")
    (folder / "saved.txt").replace(folder / "a.txt")  # a save that writes new and renames over its input
    assert blob.read_text() == "a" and file_hash(blob) == store.listing(output)["a.txt"], "the stored bytes changed"
    assert (store.checkout(output) / "a.txt").samefile(blob), "a changed checkout was handed out again"


def test_a_writable_blob_is_copied_never_linked():
    store = a_store()
    output = store.put_tree(a_folder({"a.txt": "a"}))
    blob = store.objects.path(f"blobs/{store.listing(output)['a.txt']}")
    blob.chmod(0o644)  # a blob not stored by put_blob (a restore, a hand copy)
    checked = store.checkout(output) / "a.txt"
    assert not checked.samefile(blob) and checked.read_text() == "a" and not checked.stat().st_mode & 0o222


def test_relink_makes_a_checkouts_whole_copies_links_and_leaves_a_changed_one():
    """The conductor's checkouts made as copies before this, freed with a run live (disk.clean-cache)."""
    store = a_store()
    output = store.put_tree(a_folder({"a.txt": "a" * 5000, "b.txt": "b"}))
    folder = store.checkout(output)
    for name, text in (("a.txt", "a" * 5000), ("b.txt", "changed")):  # an old copy, and a copy a make wrote over
        (folder / name).unlink()
        (folder / name).write_text(text)
        (folder / name).chmod(0o444)
    reader = open(folder / "a.txt", "rb")  # a node reading the copy while it is relinked
    assert store.relink(output) == 5000
    assert (folder / "a.txt").samefile(store.objects.path(f"blobs/{store.listing(output)['a.txt']}"))
    assert reader.read() == b"a" * 5000 and (folder / "b.txt").read_text() == "changed"
    reader.close()
    assert sorted(path.name for path in folder.iterdir()) == ["a.txt", "b.txt"]
    assert not list(store.cache.rglob("*.partial")) and store.relink(output) == 0


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
    other = store.put_tree(a_folder({"a": "2"}))
    store.put_evidence("resting", other, a_folder({"drop.json": '{"fell": 1}'}) / "drop.json")
    assert store.evidence_file("resting", output).read_text() == "{}"
    assert store.evidence_file("resting", other).read_text() == '{"fell": 1}'  # each output its own


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
    runpy.run_path(str(REPO / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
