"""The store keeps every output by its content's hash, once, whole and read-only, overwrites nothing (of processes
writing one key at once exactly one lands), moves the accepted output only by an accept, keeps an agent out of the
owner's areas, and survives a reboot: a cut write leaves the whole object or none, an unreadable object is quarantined
and read as absent except an owner's decision, which stops the read and stays put. The reboot safety is in no row's
key. One store in the temp folder, installed by the runner and the owner's commands, carries every check; the owner's
areas are tried on a framework store of its own in a fresh Python.

Each break (applied once, seen red, reverted), in score/store/__init__.py unless named:
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
import signal
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from score.store import AGENT_MARKERS, RUNNER, Store, durable, file_hash, tree_hash, tree_listing  # noqa: E402

REPO = pathlib.Path(__file__).resolve().parents[2]
PLAIN = {name: vars(Store).get(name) for name in durable.METHODS}  # Store as score/store/__init__.py writes it
durable.install()  # as the runner and the owner's commands run the store

TREE = {"stage.usda": "#usda 1.0", "layers/base.usda": "base" * 100000}  # stage.usda's bytes shared with OTHER
OTHER = {"stage.usda": "#usda 1.0", "layers/base.usda": "changed"}
WRITES_THROUGH_A_CHECKOUT = {"open r+b": lambda path: open(path, "r+b"), "open ab": lambda path: open(path, "ab"),
                             "write_text": lambda path: path.write_text("changed")}
OWNER_WRITES = [  # (who runs the Python, area, by, written)
    ("agent", "acc" + "epts", "owner", False),
    ("agent", "rej" + "ects", "owner", False),
    ("agent", "rej" + "ects", RUNNER, False),  # a reject is never the runner's
    ("agent", "acc" + "epts", RUNNER, True),  # the runner's automatic accept
    ("owner", "acc" + "epts", "owner", True),
]
OWNER_READS = {"accepted": lambda store: store.accepted("clean@hangar"),
               "rejected": lambda store: store.rejected("clean@hangar", "o1"),
               "waivers": lambda store: store.waivers("clean@hangar", "k"),
               "spend_yes": lambda store: store.spend_yes("clean@hangar", "k")}
CUT_OWNER_DECISIONS = [  # (key, the reads that must stop on it); each written empty and cut half way
    ("rejects/clean@hangar/t.json", ("accepted", "rejected")),
    ("acc" + "epts/clean@hangar/t.json", ("accepted", "rejected")),
    ("waivers/clean@hangar/k/c.json", ("waivers",)),
    ("spend-yes/clean@hangar/k.json", ("spend_yes",)),
]


def a_folder(files):
    folder = pathlib.Path(tempfile.mkdtemp())
    for name, text in files.items():
        (folder / name).parent.mkdir(parents=True, exist_ok=True)
        (folder / name).write_text(text)
    return folder


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


def plain_store():
    """Store's methods as score/store/__init__.py has them, before any install."""
    for name, method in PLAIN.items():
        if method is None:
            delattr(Store, name)
        else:
            setattr(Store, name, method)


def installed():
    """Whether every Store method durable replaces is durable's, under offload's write wrap of put_blob."""
    return all(getattr(vars(Store)[name], "__wrapped__", vars(Store)[name]) is method
               for name, method in durable.METHODS.items())


def installed_by_the_framework(store):
    """`store`, its reboot safety installed once by the runner and once by the owner's commands (each from a plain
    Store), with `store` as the framework's store meanwhile so the live one is never touched."""
    from score import graph
    from score.review import __main__ as owner
    default = vars(Store)["default"]
    try:
        plain_store()
        graph.Runner((), None, store)
        assert installed(), "the runner left the store without its reboot safety"
        plain_store()
        Store.default = classmethod(lambda cls: store)
        try:
            owner.main(["page", "clean@hangar"])
        except Exception:  # noqa: BLE001 - a node this empty store lacks: only the install before the page counts
            pass
        assert installed(), "the owner's commands left the store without its reboot safety"
    finally:
        Store.default = default
        durable.install()
    return store


def owner_write(home, who, area, by):
    """Write `area`/a@b/`by`.json into the framework store at `home` from a fresh Python run by `who`; exit, error."""
    owner = {name: value for name, value in os.environ.items() if name not in AGENT_MARKERS}
    environment = {**owner, "PROPS_HOME": home, **({"CLAUDECODE": "1"} if who == "agent" else {})}
    code = ("from score.store import Store; "
            f"Store.default().write_once('{area}/a@b/{by}.json', {{'output': 'o', 'at': '1', 'by': '{by}'}})")
    done = subprocess.run([sys.executable, "-c", code], cwd=REPO, env=environment, capture_output=True, text=True)
    return done.returncode, done.stderr


def quarantined(store):
    return sorted(path.name for path in (store.cache.parent / "quarantine").rglob("*") if path.is_file())


def written(store, key, value):
    """Write a record; 'written', or 'refused' when the key is already in the store."""
    try:
        store.write_record("clean@hangar", key, value)
        return "written"
    except FileExistsError:
        return "refused"


def test_an_output_is_kept_whole_once_and_never_overwritten():
    store = installed_by_the_framework(Store.in_folder(tempfile.mkdtemp()))

    # Named by its content and stored once, whole, by eight processes storing it at once.
    folder = a_folder(TREE)
    output = tree_hash(folder)
    assert at_once(lambda number: store.put_tree(folder)) == [output] * 8
    assert store.put_tree(a_folder(TREE)) == output != store.put_tree(a_folder(OTHER))
    other = tree_hash(a_folder(OTHER))
    assert len(store.objects.keys("blobs/")) == 3, store.objects.keys("blobs/")  # the shared stage.usda kept once

    # Sixteen processes checking it out at once all find it whole; no half object or checkout is left.
    listing = store.listing(output)
    assert at_once(lambda number: str(tree_listing(store.checkout(output)) == listing), 16) == ["True"] * 16
    assert not list(store.objects.root.rglob("*.partial")) and not list(store.cache.rglob("*.partial"))

    # 2026-10-27: checkouts copied every output (16 GB in an hour beside a 22 GB store on the conductor). A checkout
    # is a hard link to the read-only blob: no second copy, no write through it, and a save that replaces a file
    # changes the checkout only, which is then made again.
    checkout = store.checkout(output)
    blob = store.objects.path(f"blobs/{listing['layers/base.usda']}")
    assert (checkout / "layers/base.usda").samefile(blob) and blob.stat().st_nlink == 2, "a checkout copied the bytes"
    for name, write in WRITES_THROUGH_A_CHECKOUT.items():
        try:
            write(checkout / "layers/base.usda")
        except PermissionError:
            continue
        raise AssertionError(f"{name}: a stored file could be written through its checkout")
    (checkout / "saved.txt").write_text("a save beside it")
    (checkout / "saved.txt").replace(checkout / "layers/base.usda")  # a save that writes new and renames over
    assert file_hash(blob) == listing["layers/base.usda"], "the stored bytes changed"
    assert (store.checkout(output) / "layers/base.usda").samefile(blob), "a changed checkout was handed out again"

    # Relink (disk.clean-cache, with a run live): a whole copy becomes a link, a changed one is left for checkout.
    for name, text in (("layers/base.usda", TREE["layers/base.usda"]), ("stage.usda", "changed")):
        (checkout / name).unlink()
        (checkout / name).write_text(text)
        (checkout / name).chmod(0o444)
    with open(checkout / "layers/base.usda", "rb") as reader:  # a node reading the copy while it is relinked
        assert store.relink(output) == len(TREE["layers/base.usda"])
        assert (checkout / "layers/base.usda").samefile(blob)
        assert reader.read() == TREE["layers/base.usda"].encode() and (checkout / "stage.usda").read_text() == "changed"
    assert sorted(path.name for path in checkout.rglob("*")) == ["base.usda", "layers", "stage.usda"]
    assert not list(store.cache.rglob("*.partial")) and store.relink(output) == 0

    # A blob found writable (a restore, a hand copy) is copied read-only, never linked.
    changed_blob = store.objects.path(f"blobs/{store.listing(other)['layers/base.usda']}")
    changed_blob.chmod(0o644)
    copied = store.checkout(other) / "layers/base.usda"
    assert not copied.samefile(changed_blob) and copied.read_text() == "changed" and not copied.stat().st_mode & 0o222

    # Two runs making one key get a scratch folder each (a second run once wiped the first's work, 2026-10-11).
    first_making = store.making("same-key")
    (first_making / "work.txt").write_text("the first run's work")
    second_making = store.making("same-key")
    assert second_making != first_making and (first_making / "work.txt").exists() and not any(second_making.iterdir())

    # 2026-10-11: of eight processes writing one key at once exactly one writes it; nothing writes over it after.
    assert at_once(lambda number: written(store, "k1", {"number": number})) == ["refused"] * 7 + ["written"]
    first_record = store.record("clean@hangar", "k1")
    assert first_record["number"] in range(8)
    assert written(store, "k1", {"number": 9}) == "refused" and store.record("clean@hangar", "k1") == first_record
    assert not list(store.objects.root.rglob("*.partial"))

    # C9: a machine down between the write's partial file and its link leaves no object; the key stays free.
    records = store.objects.keys("records/")

    def killed_at_the_link():
        os.link = lambda source, target: os.kill(os.getpid(), signal.SIGKILL)
        store.write_record("clean@hangar", "k2", {"finished": "1"})

    process = multiprocessing.get_context("fork").Process(target=killed_at_the_link)
    process.start()
    process.join()
    assert process.exitcode == -signal.SIGKILL
    assert store.record("clean@hangar", "k2") is None and store.objects.keys("records/") == records
    assert written(store, "k2", {"finished": "2"}) == "written"
    assert store.record("clean@hangar", "k2") == {"finished": "2"}

    # C9: an empty or cut object (a 0-byte record after a WSL restart) is quarantined and read as absent.
    empty = store.objects.path("records/clean@hangar/k3.json")
    cut = store.objects.path("judgements/clean@hangar/k3/t.json")
    empty.write_bytes(b"")
    cut.parent.mkdir(parents=True)
    cut.write_text('{"at": "ab')
    assert store.record("clean@hangar", "k3") is None and store.record("clean@hangar", "k3") is None
    assert store.judgements("clean@hangar", "k3") == []
    assert not empty.exists() and not cut.exists()
    assert [name.split(".json")[0] for name in quarantined(store)] == ["k3", "t"], quarantined(store)
    assert written(store, "k3", {"finished": "1"}) == "written"
    assert store.record("clean@hangar", "k3") == {"finished": "1"}

    # The accepted output is the newest accept; a newer output stored beside it moves nothing.
    assert store.accepted("clean@hangar") is None
    store.write_accept("clean@hangar", {"output": output, "at": "2026-10-11T10:00:00+00:00"})
    store.put_tree(a_folder({"stage.usda": "newer"}))
    assert store.accepted("clean@hangar") == output
    store.write_accept("clean@hangar", {"output": other, "at": "2026-10-11T11:00:00+00:00"})
    assert store.accepted("clean@hangar") == other
    assert [accept["output"] for accept in store.accepts("clean@hangar")] == [output, other]

    # C9 review: a cut owner's decision read as absent would undo a reject or buy a paid row again: it stops the
    # read and stays where it is, out of quarantine.
    before = quarantined(store)
    for key, reads in CUT_OWNER_DECISIONS:
        for text in ("", '{"output": "o1", "at": "2"'):
            path = store.objects.path(key)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
            for read in reads:
                try:
                    OWNER_READS[read](store)
                except durable.UnreadableOwnerObject as refused:
                    assert key in str(refused), (key, read, refused)
                else:
                    raise AssertionError(f"a cut {key} was read as absent by {read}")
            assert path.read_text() == text, f"{key} was moved"
            path.unlink()
    assert quarantined(store) == before and store.accepted("clean@hangar") == other

    # Evidence is kept per check and output; a missing one is None.
    assert store.evidence_file("resting", output) is None and store.evidence_hash("resting", output) is None
    store.put_evidence("resting", output, a_folder({"drop.json": "{}"}) / "drop.json")
    store.put_evidence("resting", other, a_folder({"drop.json": '{"fell": 1}'}) / "drop.json")
    assert store.evidence_file("resting", output).read_text() == "{}"
    assert store.evidence_file("resting", other).read_text() == '{"fell": 1}'

    # Review of step 0: an agent's Python wrote an accept into the framework store; only a hook's text match stood in
    # the way. Now the store itself refuses every owner write of an agent but the runner's automatic accept.
    home = tempfile.mkdtemp()
    for who, area, by, lands in OWNER_WRITES:
        kept = len(list(pathlib.Path(home).rglob("*.json")))
        status, error = owner_write(home, who, area, by)
        found = len(list(pathlib.Path(home).rglob("*.json")))
        if lands:
            assert status == 0 and found == kept + 1, (who, area, by, status, error)
        else:
            assert status != 0 and "only the owner" in error and found == kept, (who, area, by, status, error)

    # C9 review: the reboot safety sat in score/store/__init__.py, which every stage calling the store hashes, and an
    # edit there re-keyed 44 paid rows. No stage's code version reads durable.py, and the store's module stays a
    # stage file rather than a framework one.
    from score import graph, stages
    from score.graph import _code
    assert REPO / "score/store/__init__.py" not in _code.FRAMEWORK
    reads = {row.name: _code.source_files(graph.code_functions(row)) for row in stages.STAGES}
    assert [name for name, files in reads.items() if REPO / "score/store/durable.py" in files] == []
    assert [name for name, files in reads.items() if REPO / "score/store/__init__.py" in files], \
        "no stage reads score/store/__init__.py: this check would prove nothing"


if __name__ == "__main__":
    runpy.run_path(str(REPO / "conftest.py"))["refuse_outside_sandbox"]()
    test_an_output_is_kept_whole_once_and_never_overwritten()
    print("ok")
