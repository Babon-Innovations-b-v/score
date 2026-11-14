"""The restore spends nothing and accepts nothing old by hand: a paid row comes back blocked, a paid gatherer's check
stays unknown, an old paid output stands again only on today's key and today's gates, and a Blender call blocks its
node with nothing written. A toy table in a store of its own, the bucket a folder, the ledgers temp files.

Fault (2026-10-19): the store, the spend ledgers and the runner's keys were lost with the old WSL disk; the prop
route and the method were hardened a lot since most outputs were made, so nothing old may look current.

The one test drives three worlds: the whole toy table once through the restore command, the old paid output offered
again one way per REATTACH row, and command.main started per STARTS row. Each break (applied once, seen red,
reverted), in score/store/restore/ (__init__.py unless named), and the part that goes red:
- paid row blocked (the toy run): FreeRunner.make sends a paid stage to the plain make (`if False:` for
  `if stage.paid:`).
- paid gatherer never called (the toy run): FreeRunner.gatherable keeps the paid gatherers.
- Blender blocks its node (the toy run's call-* rows): guard_free_only leaves subprocess.Popen as it is.
- re-attached, judged today (REATTACH "on today's key"): reattached_record keeps today's commit.
- older key stays blocked (REATTACH "older key"): paid_make takes the library's first output whatever its key.
- a checkout that does not rebuild (REATTACH "does not rebuild"): rebuilt's hash check becomes `if False:`.
- a second checkout tried (REATTACH "second checkout"): reattached tries only the first tar.
- past the run's budget (REATTACH "past the budget"): _bucket.Fetch.reserve never refuses.
- a disk without room (REATTACH "no room on the disk"): _bucket.Fetch.room_for never refuses.
- counting downloads nothing (REATTACH "counting"): paid_make's `if self.fetch is None:` becomes `if False:`.
- the index takes only outputs (every REATTACH row's "parts" tar): _bucket.index_checkouts drops the OUTPUT_NAME
  match.
- the run's summary (the toy run's line): __main__.category files a paid refusal under "other".
- a spend line says so (the toy run's sneak row): __main__.summary_line always says "EUR 0".
- an accept not by the runner (the toy run's owner accept): __main__.strays returns [].
- a free gatherer reaching Blender (the toy run's drop row): FreeRunner.gather_one catches KeyError instead of
  ledger.FreeOnly.
- library rows never made (the toy run): FreeRunner.make's library check becomes `if False:`.
- main guards first (STARTS "books shut"): __main__.main skips guard_free_only().
- main refuses while paid work is open (STARTS "books known"): __main__.main's `if refused:` becomes `if False:`.
- Blender however started (the toy run's call-shell row): heavy_program takes a shell string as one word.
- start refused while paid work is open (STARTS "books known"): __main__.start_refusal's books check becomes
  `if False:`.
- re-attach is the owner's (STARTS "reattach by an agent"): __main__.start_refusal's agent check becomes
  `if False:`.

Run: PROPS_HOME=$(mktemp -d) .venv/bin/python score/store/restore/test_the_restore_spends_nothing_and_accepts_nothing_old_by_hand.py
"""
import io
import json
import os
import pathlib
import subprocess
import sys
import tarfile
import tempfile

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))

from score import checks, contracts, graph  # noqa: E402
from score.adapters import compute  # noqa: E402
from score.store import AGENT_MARKERS, RUNNER, Store, runtime_store, tree_hash  # noqa: E402
from score.store import restore  # noqa: E402
from score.store.restore import __main__ as command  # noqa: E402
from score.store.restore import _bucket  # noqa: E402
from score.store.restore._bucket import Fetch, index_checkouts  # noqa: E402

import google_spend  # noqa: E402  (tools/cloud, on the path through the restore)

PLACES = ("hangar", "station", "garage")  # a line each: the paid row, the paid gatherer, Blender
REPO = pathlib.Path(__file__).resolve().parents[3]
ACCEPTED_THEN = "2026-10-15T22:15:48.546897+00:00"  # when the library says the old output stood accepted


def touched(name):
    """A paid point that fails the node that reaches it: the restore must never get there."""
    def refuse(*arguments, **options):
        raise AssertionError(f"touched {name}")
    return refuse


SCRATCH = pathlib.Path(tempfile.mkdtemp())


def every_paid_point_fails(monkeypatch):
    """Every paid point fails loudly here; each node's process is forked from this one, so it carries the same."""
    monkeypatch.setattr(compute, "clearance", touched("compute.clearance"))
    monkeypatch.setattr(compute.job_contract, "write_job", touched("submit.write_job"))
    monkeypatch.setattr(google_spend, "generate", touched("google_spend.generate"))
    monkeypatch.setattr(compute, "cloud_bill", touched("the cloud bill"))
    monkeypatch.setattr(restore.ledger, "LEDGER", SCRATCH / "ledger.jsonl")
    monkeypatch.setattr(google_spend, "LEDGER", SCRATCH / "google-ledger.jsonl")
    monkeypatch.setattr(subprocess, "Popen", subprocess.Popen)  # recorded, so the guard's Popen is undone after
    monkeypatch.setenv(restore.ledger.FREE_ONLY, os.environ.get(restore.ledger.FREE_ONLY, ""))  # likewise its env
    restore.guard_free_only()
    # The toy nodes take no memory, and graph/memory_test.py proves the gate: read as always room, so a drive never
    # sits out MEMORY_POLL behind this PC's real memory (as graph_test, 951bbd59; owner's budget 120 s).
    monkeypatch.setattr(graph, "AVAILABLE", lambda: 2**50)
    monkeypatch.setattr(_bucket, "DISK_MARGIN", 0)  # the test disk's free room is not what these tests are about


@pytest.fixture(autouse=True)
def paid_points_fail_for_each_test(monkeypatch):
    """Patched per test under pytest, so a later test file in the same process gets the real ones back."""
    every_paid_point_fails(monkeypatch)


def make_brief(inputs, out, seed, params):
    (out / "brief.txt").write_text(inputs["brief"].read_text())


def make_render(inputs, out, seed, params):
    raise AssertionError("touched the paid make")


def make_count(inputs, out, seed, params):
    (out / "count.txt").write_text(str(len((inputs["render"] / "render.txt").read_text())))


# How a free-only process might start a program: (stage, the call, its options, refused). Each is a stage at the
# garage, so the guard judges it inside a node; git is the one that runs.
CALLS = (("call-list", ["/opt/blender-5.0.1/blender", "-b", "--python", "bake.py"], {}, True),
         ("call-shell", "cd /work && blender -b x.blend", {"shell": True}, True),
         ("call-path", pathlib.Path("/opt/blender"), {}, True),
         ("call-bytes", [b"blender"], {}, True),
         ("call-executable", ["python3", "x.py"], {"executable": "/opt/blender/blender"}, True),
         ("call-git", ["git", "rev-parse", "HEAD"], {"cwd": REPO, "capture_output": True}, False))


def make_call(inputs, out, seed, params):
    _, call, options, _ = next(row for row in CALLS if row[0] == params["call"])
    subprocess.run(call, check=True, **options)
    (out / "called.txt").write_text("ran")


def gather_resting(output, inputs, folder):
    (folder / "gathered").write_text("a paid drop run")
    raise AssertionError("touched the paid gatherer")


def judge_written(output, inputs, evidence):
    return checks.Verdict("written", checks.PASS if any(output.glob("*.txt")) else checks.FAIL, "a text was written")


def judge_rests(output, inputs, evidence):
    return checks.Verdict("rests", checks.PASS, "it rests")


TEXT = contracts.Contract("toy-text", 1, lambda folder: [] if any(folder.glob("*.txt")) else ["no text file"])
WRITTEN = (checks.Check("written", judge_written),)
BRIEF = graph.Stage("brief", "place", make_brief, TEXT, WRITTEN, files={"brief": "{data}/{place}.txt"})
RENDER = graph.Stage("render", "place", make_render, TEXT, WRITTEN, after={"brief": ("toy-text", 1)}, paid=True,
                     euros=2.0, applies=lambda place: place == "hangar")
COUNT = graph.Stage("count", "place", make_count, TEXT, WRITTEN, after={"render": ("toy-text", 1)},
                    applies=lambda place: place == "hangar")
SETTLED = graph.Stage("settled", "place", make_brief, TEXT, (checks.Check("rests", judge_rests, evidence="a drop run"),),
                      files={"brief": "{data}/{place}.txt"}, gatherers={"rests": (gather_resting, 1.5)},
                      applies=lambda place: place == "station")
CALL_STAGES = tuple(graph.Stage(name, "place", make_call, TEXT, WRITTEN, params={"call": name},
                                applies=lambda place: place == "garage") for name, _, _, _ in CALLS)


def make_sneak(inputs, out, seed, params):
    with restore.ledger.LEDGER.open("a") as books:  # a spend the guards missed
        books.write(json.dumps({"started": graph.now(), "batch": "sneak", "euros": 0.5}) + "\n")
    (out / "sneak.txt").write_text("bought")


SNEAK = graph.Stage("sneak", "place", make_sneak, TEXT, WRITTEN, applies=lambda place: place == "hangar")


def gather_with_blender(output, inputs, folder):
    subprocess.run(["blender", "-b", "--python", "drop.py"], check=True)
    (folder / "rests.json").write_text("{}")


FREE_DROP = graph.Stage("drop", "place", make_brief, TEXT, (checks.Check("rests", judge_rests, evidence="a drop run"),),
                        files={"brief": "{data}/{place}.txt"}, gatherers={"rests": (gather_with_blender, 0)},
                        applies=lambda place: place == "station")


def make_library_handover(inputs, out, seed, params):
    raise AssertionError("touched the library handover")


def library_rows():
    """The library rows (the handover commits and pushes score_lib, puts blobs in the bucket, runs heavy hooks)."""
    from score.stages import library
    return (graph.Stage(library.PLACE_ROW, "place", make_library_handover, TEXT, WRITTEN,
                        files={"brief": "{data}/hangar.txt"}, applies=lambda place: place == "hangar"),
            graph.Stage(library.WORLD_ROW, "world", make_library_handover, TEXT, WRITTEN,
                        files={"brief": "{data}/hangar.txt"}))


def quiet(line):
    pass


def a_runner(stages, library=None, checkouts=None, fetch=None, store=None, data=None):
    """A free runner over `stages` on its own store; the same store and data when given."""
    if data is None:
        data = pathlib.Path(tempfile.mkdtemp())
        for place in PLACES:
            (data / f"{place}.txt").write_text(f"a {place}")
    store = store or Store.in_folder(tempfile.mkdtemp())
    return restore.FreeRunner(stages, graph.Environment("toy", 7, {"data": data}), store, store.cache.parent / "notes",
                              library or {}, checkouts, fetch, model_record=lambda kind: {"kind": kind})


def an_accept_by_someone_else(runner):
    """`runner` with its drive followed by an accept of brief@hangar's output written by another hand (the owner)."""
    drive = runner.drive

    def driven(*arguments, **options):
        found = drive(*arguments, **options)
        output = runner.store.accepted("brief@hangar")
        runner.store.write_accept("brief@hangar", {"node": "brief@hangar", "output": output, "at": graph.now(),
                                                   "by": "owner"})
        return found
    runner.drive = driven
    return runner


def todays_key(runner, stage):
    with runner.still():
        return runner.key(stage, "hangar")["key"]


def an_old_render(text="a render"):
    """An old paid output's folder, stamped as the runner stores it; (folder, its output hash)."""
    folder = pathlib.Path(tempfile.mkdtemp()) / "out"
    folder.mkdir()
    (folder / "render.txt").write_text(text)
    contracts.stamp(TEXT, folder)
    return folder, tree_hash(folder)


def tar_of(folder, named):
    """`folder` as a checkout tar's bytes, its first member named `named` (as inputs.py writes)."""
    data = io.BytesIO()
    with tarfile.open(fileobj=data, mode="w", format=tarfile.PAX_FORMAT) as archive:
        archive.add(folder, arcname=named)
    return data.getvalue()


def a_bucket(folder, named):
    """A folder bucket holding `folder` as a checkout tar named `named`, the same folder's tar named as no output
    ("parts"), and one object that is no tar at all."""
    bucket = runtime_store.FolderStore(tempfile.mkdtemp())
    bucket.write_bytes(f"inputs/{'a' * 64}.tar", tar_of(folder, named))
    bucket.write_bytes(f"inputs/{'b' * 64}.tar", b"not a tar at all")
    bucket.write_bytes(f"inputs/{'c' * 64}.tar", tar_of(folder, "parts"))
    return bucket


def held_by_library(old, key):
    """The library (library_outputs) holding `old` under `key`, as score_lib's provenance names it."""
    return {"render@hangar": [{"output": old, "record_key": key, "entry": "model/render.hangar@1", "code": "c" * 64,
                               "library_commit": "1" * 40, "accepted_at": ACCEPTED_THEN}]}


MAIN_CHILD = """
import json, os, pathlib, subprocess, sys, types
sys.path.insert(0, sys.argv[1])
from score.store import restore
from score.store.restore import __main__ as command
if sys.argv[3] == "open":
    restore.ledger.write_books({"month": restore.ledger.this_month(), "state": "known"})
def reached(*arguments, **options):
    raise AssertionError("free_runner reached")
command.free_runner = (lambda options, folder: types.SimpleNamespace(world=None)) if sys.argv[3] == "shut" else reached
command.claim_store = lambda runner, places, whole: None
def started(runner, places, whole, jobs, detail, say=print):
    print(json.dumps({"free_only": os.environ.get(restore.ledger.FREE_ONLY),
                      "guarded": subprocess.Popen is restore.FreeOnlyPopen}))
    return "line", 0
command.restore = started
command.main(["world1", "--library", sys.argv[2], "--place", "hangar", *sys.argv[4:]])
"""

# command.main in a fresh process (the guard not yet applied), an agent's, with a home of its own: (row, the month's
# books, extra arguments, exit code, what it says). It guards the process before the drive, and refuses before the
# runner is built while paid work is open or when an agent asks for --reattach.
STARTS = (("books shut", "shut", [], 0, '{"free_only": "1", "guarded": true}'),
          ("books known", "open", [], 1, "refused: the month's books are known, so paid work is open"),
          ("reattach by an agent", "shut", ["--reattach", "--max-gb", "1"], 1, "the owner runs it himself"))


def main_in_a_child(books, extra):
    """command.main started in a child process (see STARTS) marked as an agent's; the running Popen."""
    library = pathlib.Path(tempfile.mkdtemp())
    (library / "entries").mkdir()
    environment = {**os.environ, "PROPS_HOME": tempfile.mkdtemp(), **dict.fromkeys(AGENT_MARKERS[:1], "1")}
    environment.pop(restore.ledger.FREE_ONLY, None)
    return subprocess.Popen([sys.executable, "-c", MAIN_CHILD, str(REPO), str(library), books, *extra],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=environment)


# The old paid output render@hangar offered again through the library and the bucket, one way per row: (row, the
# library's key, the checkout changed since, a smaller other checkout of it in the bucket, the run's budget in bytes,
# the disk margin, downloads allowed (else counting), stored again, what the refusal says, the tars indexed for it
# (by key), downloaded).
REATTACH = (
    ("on today's key", "today", False, False, 10e9, 0, True, True, None, ["a"], True),
    ("older key", "older", False, False, 10e9, 0, True, False, "were made under older keys", ["a"], False),
    ("does not rebuild", "today", True, False, 10e9, 0, True, False,
     "rebuilds to its output hash (1 tried): nothing stored", ["a"], True),
    ("second checkout", "today", False, True, 10e9, 0, True, True, None, ["0", "a"], True),
    ("past the budget", "today", False, False, 1, 0, True, False, "would pass the run's", ["a"], False),
    ("no room on the disk", "today", False, False, 10e9, 1e18, True, False, "free on the disk", ["a"], False),
    ("counting", "today", False, False, 10e9, 0, False, False, "key matches today: would re-attach", ["a"], False),
)


def test_the_restore_spends_nothing_and_accepts_nothing_old_by_hand(monkeypatch):
    starts = {row: main_in_a_child(books, extra) for row, books, extra, _, _ in STARTS}  # side by side with the rest

    # One run of the whole toy table: a paid row, a paid gatherer, Blender started six ways, the library rows, a free
    # gatherer that reaches Blender, a make that writes a spend line, and an accept by another hand after the drive.
    runner = an_accept_by_someone_else(a_runner((BRIEF, RENDER, COUNT, SETTLED, *CALL_STAGES, SNEAK, FREE_DROP,
                                                 *library_rows())))
    detail = pathlib.Path(tempfile.mkdtemp()) / "restore.json"
    started = graph.now()
    line, status = command.restore(runner, PLACES, True, 2, detail, say=quiet)
    written = json.loads(detail.read_text())
    rows, store = written["nodes"], runner.store
    did = {node: row["did"] for node, row in rows.items()}
    assert not any("touched" in text for text in did.values()), did
    assert status == 1 and line.startswith(
        "restore toy: 16 nodes; accepted today 5 (made free 5, re-attached 0); unknown 9; paid refused 1 (key matches "
        "today 0); line stopped 1; failing today's gates 0; other 0; downloaded 0.00 GB; spend ledger lines added "
        "[1, 0]; books unknown; detail ") and "EUR 0" not in line, line
    assert did["brief@hangar"] == did["sneak@hangar"] == "made: pass, accepted automatically", did
    assert did["render@hangar"].startswith(f"blocked: {restore.PAID_REFUSED}; the library holds no output"), did
    assert rows["render@hangar"]["category"] == "paid refused" and rows["render@hangar"]["key_matches"] is False
    assert did["count@hangar"] == "not run: its line stopped at render@hangar", did
    assert did["settled@station"].startswith("made: unknown; fault report"), did
    assert store.accepted("settled@station") is None and store.accepted("drop@station") is None
    assert rows["drop@station"]["category"] == "unknown" and restore.HEAVY_REFUSED in did["drop@station"], rows
    assert "blender" in rows["drop@station"]["free_only"], rows
    assert store.objects.keys("evidence/") == []
    from score.stages import library
    for name, _, _, refused in CALLS:
        node = f"{name}@garage"
        if refused:
            assert did[node].startswith(f"blocked: {restore.HEAVY_REFUSED}"), (node, did[node])
            assert store.objects.keys(f"records/{node}/") == store.objects.keys(f"judgements/{node}/") == [], node
        else:
            assert did[node] == "made: pass, accepted automatically", (node, did[node])
    for node in (f"{library.PLACE_ROW}@hangar", library.WORLD_ROW):
        assert did[node].startswith(f"blocked: {restore.LIBRARY_REFUSED}"), (node, did[node])
        assert rows[node]["category"] == "unknown" and store.objects.keys(f"records/{node}/") == [], node
    assert store.objects.keys("records/render@hangar/") == []
    accepts = [runtime_store.read_json(store.objects, key) for key in store.objects.keys("accepts/")]
    assert [accept["by"] for accept in written["accepts_not_by_runner"]] == ["owner"], written
    assert [accept for accept in accepts if accept["by"] != RUNNER] == written["accepts_not_by_runner"], accepts
    judgements = [runtime_store.read_json(store.objects, key) for key in store.objects.keys("judgements/")]
    assert judgements and all(judgement["at"] >= started for judgement in judgements)

    # The same old paid output offered again, one way per row: it stands only on today's key, rebuilt to its exact
    # hash and accepted by the runner; otherwise nothing is downloaded past the guards and nothing is stored.
    for row, key, changed, other, max_bytes, margin, downloads, stored, says, tars, downloaded in REATTACH:
        base = a_runner((BRIEF, RENDER, COUNT))
        base.drive(("hangar",), say=quiet)
        folder, old = an_old_render()
        if changed:
            (folder / "render.txt").write_text("changed since")  # its bytes no longer hash to the library's output
        bucket = a_bucket(folder, old)
        if other:  # the same folder name, other bytes, a smaller tar: tried first
            smaller = pathlib.Path(tempfile.mkdtemp()) / "out"
            smaller.mkdir()
            (smaller / "render.txt").write_text("x")
            bucket.write_bytes(f"inputs/{'0' * 64}.tar", tar_of(smaller, old))
        checkouts = index_checkouts(bucket, say=quiet)
        if not downloaded:
            bucket.download = touched("a download")
        fetch = Fetch(bucket, pathlib.Path(tempfile.mkdtemp()), max_bytes) if downloads else None
        library_key = todays_key(base, RENDER) if key == "today" else "0" * 64
        again = a_runner((BRIEF, RENDER, COUNT), held_by_library(old, library_key), checkouts, fetch, base.store,
                         base.world.roots["data"])
        outputs = again.store.objects.keys("outputs/")
        detail = pathlib.Path(tempfile.mkdtemp()) / "restore.json"
        monkeypatch.setattr(_bucket, "DISK_MARGIN", margin)  # each node's process is forked with it
        line, status = command.restore(again, ("hangar",), True, 2, detail, say=quiet)
        monkeypatch.setattr(_bucket, "DISK_MARGIN", 0)
        found = json.loads(detail.read_text())["nodes"]
        render, note = found["render@hangar"]["did"], again.notes.read("render@hangar")
        assert status == 0 and "EUR 0" in line and "touched" not in render, (row, line, render)
        assert list(checkouts) == [old] and [tar["key"][7:8] for tar in checkouts[old]] == tars, (row, checkouts)
        assert note["key_matches"] is (key == "today"), (row, note)
        tried = sum(tar["bytes"] for tar in checkouts[old]) if downloaded else 0
        assert note.get("downloaded", 0) == tried, (row, note)
        assert note.get("would_reattach") == (None if downloads else checkouts[old][0]["bytes"]), (row, note)
        if fetch is not None:
            assert (fetch.folder / "downloaded.json").exists() is downloaded, row
        if not stored:
            assert render.startswith("blocked: ") and says in render, (row, render)
            assert again.store.objects.keys("records/render@hangar/") == [], row
            assert again.store.objects.keys("outputs/") == outputs, row
            continue
        assert render == found["count@hangar"]["did"] == "made: pass, accepted automatically", (row, found)
        assert "accepted today 3 (made free 2, re-attached 1)" in line and "key matches today 1" in line, (row, line)
        record = again.store.record("render@hangar", todays_key(again, RENDER))
        assert record["output"] == old and record["euros"] == 0, (row, record)
        assert record["restored"]["entry"] == "model/render.hangar@1", (row, record)
        # Nothing in its record dates or names it as made today (review of #13): its maker's commit is unknown, so no
        # carry or proof diffs from today's, and its time is the library's accept, today's download kept apart.
        assert graph.made_by(record)["commit"] is None and record["uncommitted"] is True, (row, record)
        assert (record["finished"], record["started"], record["machine"], record["minutes"]) == (
            ACCEPTED_THEN, None, None, None), (row, record)
        assert record["restored"]["library_commit"] == "1" * 40 and record["restored"]["at"] > ACCEPTED_THEN, row
        assert [accept["by"] for accept in again.store.accepts("render@hangar")] == [RUNNER], row

    for row, books, extra, code, says in STARTS:
        out, err = starts[row].communicate(timeout=300)
        assert starts[row].returncode == code and says in out + err and "reached" not in err, (row, code, out, err)


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[3] / "conftest.py"))["refuse_outside_sandbox"]()
    every_paid_point_fails(pytest.MonkeyPatch())  # this process only: never undone
    test_the_restore_spends_nothing_and_accepts_nothing_old_by_hand(pytest.MonkeyPatch())
    print("ok")
