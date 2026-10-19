"""The restore spends nothing and accepts nothing old by hand: a paid row comes back blocked, a paid gatherer's check
stays unknown, an old paid output stands again only on today's key and today's gates, and a Blender call blocks its
node with nothing written. A toy table in a store of its own, the bucket a folder, the ledgers temp files.

Fault (2026-10-19): the store, the spend ledgers and the runner's keys were lost with the old WSL disk; the prop
route and the method were hardened a lot since most outputs were made, so nothing old may look current.

Run: .venv/bin/python score/store/restore/restore_test.py
"""
import io
import json
import os
import pathlib
import subprocess
import sys
import tarfile
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))

from score import checks, contracts, graph  # noqa: E402
from score.adapters import compute  # noqa: E402
from score.store import RUNNER, Store, runtime_store, tree_hash  # noqa: E402
from score.store import restore  # noqa: E402
from score.store.restore import __main__ as command  # noqa: E402
from score.store.restore._bucket import Fetch, index_checkouts  # noqa: E402

import google_spend  # noqa: E402  (tools/props/cloud, on the path through the restore)

PLACES = ("hangar", "station", "garage")  # a line each: the paid row, the paid gatherer, Blender


def touched(name):
    """A paid point that fails the node that reaches it: the restore must never get there."""
    def refuse(*arguments, **options):
        raise AssertionError(f"touched {name}")
    return refuse


# Every paid point fails loudly here; each node's process is forked from this one, so it carries the same.
compute.clearance = touched("compute.clearance")
compute.job_contract.write_job = touched("submit.write_job")
google_spend.generate = touched("google_spend.generate")
compute.cloud_bill = touched("the cloud bill")
SCRATCH = pathlib.Path(tempfile.mkdtemp())
restore.ledger.LEDGER, google_spend.LEDGER = SCRATCH / "ledger.jsonl", SCRATCH / "google-ledger.jsonl"
restore.guard_free_only()


def make_brief(inputs, out, seed, params):
    (out / "brief.txt").write_text(inputs["brief"].read_text())


def make_render(inputs, out, seed, params):
    raise AssertionError("touched the paid make")


def make_count(inputs, out, seed, params):
    (out / "count.txt").write_text(str(len((inputs["render"] / "render.txt").read_text())))


def make_heavy(inputs, out, seed, params):
    subprocess.run(["/opt/blender/blender", "-b", "--python", "bake.py"], check=True)
    (out / "heavy.txt").write_text("baked")


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
HEAVY = graph.Stage("heavy", "place", make_heavy, TEXT, WRITTEN, after={"brief": ("toy-text", 1)},
                    applies=lambda place: place == "garage")


def quiet(line):
    pass


def a_runner(library=None, checkouts=None, fetch=None, store=None, data=None):
    """A free runner over the toy table on its own store; the same store and data when given."""
    if data is None:
        data = pathlib.Path(tempfile.mkdtemp())
        for place in PLACES:
            (data / f"{place}.txt").write_text(f"a {place}")
    store = store or Store.in_folder(tempfile.mkdtemp())
    return restore.FreeRunner((BRIEF, RENDER, COUNT, SETTLED, HEAVY), graph.Environment("toy", 7, {"data": data}),
                              store, store.cache.parent / "notes", library or {}, checkouts, fetch,
                              model_record=lambda kind: {"kind": kind})


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


def a_bucket(folder, named):
    """A folder bucket holding `folder` as a checkout tar whose first member is named `named` (as inputs.py writes)."""
    bucket = runtime_store.FolderStore(tempfile.mkdtemp())
    data = io.BytesIO()
    with tarfile.open(fileobj=data, mode="w", format=tarfile.PAX_FORMAT) as archive:
        archive.add(folder, arcname=named)
    bucket.write_bytes(f"inputs/{'a' * 64}.tar", data.getvalue())
    bucket.write_bytes(f"inputs/{'b' * 64}.tar", b"not a tar at all")
    return bucket


def restored(runner, old, key, bucket):
    """The runner again on the same store, with the library holding `old` under `key` and the bucket indexed."""
    library = {"render@hangar": [{"output": old, "record_key": key, "entry": "model/render.hangar@1"}]}
    fetch = Fetch(bucket, pathlib.Path(tempfile.mkdtemp()), 10e9)
    return a_runner(library, index_checkouts(bucket, say=quiet), fetch, runner.store, runner.world.roots["data"])


def no_paid_point_touched(found):
    assert not any("touched" in did for did in found.values()), found


def test_a_paid_row_comes_back_blocked_with_no_record():
    runner = a_runner()
    found = runner.drive(PLACES, say=quiet)
    no_paid_point_touched(found)
    assert found["brief@hangar"] == "made: pass, accepted automatically", found
    assert found["render@hangar"].startswith(f"blocked: {restore.PAID_REFUSED}; the library holds no output"), found
    assert found["count@hangar"] == "not run: its line stopped at render@hangar", found
    assert runner.store.objects.keys("records/render@hangar/") == []


def test_a_paid_gatherer_is_never_called_and_its_check_stays_unknown():
    runner = a_runner()
    found = runner.drive(PLACES, say=quiet)
    no_paid_point_touched(found)
    assert found["settled@station"].startswith("made: unknown; fault report"), found
    assert runner.store.accepted("settled@station") is None
    assert runner.store.objects.keys("evidence/") == []


def test_a_blender_call_blocks_its_node_as_unknown_with_nothing_written():
    runner = a_runner()
    found = runner.drive(PLACES, say=quiet)
    assert found["heavy@garage"].startswith(f"blocked: {restore.HEAVY_REFUSED}"), found
    assert runner.store.objects.keys("records/heavy@garage/") == []
    assert runner.store.objects.keys("judgements/heavy@garage/") == []


def test_an_old_output_on_todays_key_is_reattached_judged_today_and_accepted_by_the_runner():
    runner = a_runner()
    runner.drive(PLACES, say=quiet)
    folder, old = an_old_render()
    again = restored(runner, old, todays_key(runner, RENDER), a_bucket(folder, old))
    found = again.drive(PLACES, say=quiet)
    no_paid_point_touched(found)
    assert found["render@hangar"] == "made: pass, accepted automatically", found
    assert found["count@hangar"] == "made: pass, accepted automatically", found  # the free row after it runs
    record = again.store.record("render@hangar", todays_key(again, RENDER))
    assert record["output"] == old and record["euros"] == 0
    assert record["restored"]["entry"] == "model/render.hangar@1"
    assert [accept["by"] for accept in again.store.accepts("render@hangar")] == [RUNNER]
    assert again.notes.read("render@hangar")["downloaded"] > 0


def test_an_old_output_under_an_older_key_stays_blocked():
    runner = a_runner()
    runner.drive(PLACES, say=quiet)
    folder, old = an_old_render()
    again = restored(runner, old, "0" * 64, a_bucket(folder, old))
    found = again.drive(PLACES, say=quiet)
    assert "were made under older keys" in found["render@hangar"], found
    assert again.notes.read("render@hangar")["key_matches"] is False
    assert again.store.objects.keys("records/render@hangar/") == []


def test_a_checkout_that_does_not_rebuild_to_its_hash_stores_nothing():
    runner = a_runner()
    runner.drive(PLACES, say=quiet)
    folder, old = an_old_render()
    (folder / "render.txt").write_text("changed since")  # the tar's bytes no longer hash to the library's output
    again = restored(runner, old, todays_key(runner, RENDER), a_bucket(folder, old))
    found = again.drive(PLACES, say=quiet)
    assert "does not rebuild to its output hash" in found["render@hangar"], found
    assert again.store.objects.keys("records/render@hangar/") == []
    assert not again.store.objects.exists(f"outputs/{tree_hash(folder)}.json")


def test_counting_downloads_nothing():
    runner = a_runner()
    runner.drive(PLACES, say=quiet)
    folder, old = an_old_render()
    bucket = a_bucket(folder, old)
    library = {"render@hangar": [{"output": old, "record_key": todays_key(runner, RENDER), "entry": "e"}]}
    checkouts = index_checkouts(bucket, say=quiet)
    bucket.download = touched("a download")
    counting = a_runner(library, checkouts, None, runner.store, runner.world.roots["data"])
    found = counting.drive(PLACES, say=quiet)
    no_paid_point_touched(found)
    assert "key matches today: would re-attach" in found["render@hangar"], found
    assert counting.notes.read("render@hangar")["would_reattach"] == checkouts[old]["bytes"]


def test_the_index_takes_only_tars_whose_first_member_is_an_output():
    folder, old = an_old_render()
    bucket = a_bucket(folder, old)
    bucket.write_bytes(f"inputs/{'c' * 64}.tar", a_bucket(folder, "parts").read_bytes(f"inputs/{'a' * 64}.tar"))
    assert list(index_checkouts(bucket, say=quiet)) == [old]


def test_a_run_adds_no_ledger_line_and_only_the_runners_accepts_and_todays_judgements():
    runner = a_runner()
    detail = pathlib.Path(tempfile.mkdtemp()) / "restore.json"
    started = graph.now()
    line, status = command.restore(runner, PLACES, True, 2, detail, say=quiet)
    assert status == 0, line
    assert line.startswith("restore toy: 7 nodes; accepted today 3 (made free 3, re-attached 0); unknown 2; "
                           "paid refused 1 (key matches today 0); line stopped 1; failing today's gates 0; other 0; "
                           "downloaded 0.00 GB; EUR 0; books unknown; detail "), line
    rows = json.loads(detail.read_text())["nodes"]
    assert rows["render@hangar"]["category"] == "paid refused" and rows["render@hangar"]["key_matches"] is False
    accepts = [runtime_store.read_json(runner.store.objects, key) for key in runner.store.objects.keys("accepts/")]
    assert accepts and all(accept["by"] == RUNNER for accept in accepts)
    judgements = [runtime_store.read_json(runner.store.objects, key) for key in runner.store.objects.keys("judgements/")]
    assert judgements and all(judgement["at"] >= started for judgement in judgements)


def make_sneak(inputs, out, seed, params):
    with restore.ledger.LEDGER.open("a") as books:  # a spend the guards missed
        books.write(json.dumps({"started": graph.now(), "batch": "sneak", "euros": 0.5}) + "\n")
    (out / "sneak.txt").write_text("bought")


def test_a_run_that_wrote_a_spend_line_says_so_and_fails():
    sneak = graph.Stage("sneak", "place", make_sneak, TEXT, WRITTEN)
    data = pathlib.Path(tempfile.mkdtemp())
    store = Store.in_folder(tempfile.mkdtemp())
    runner = restore.FreeRunner((sneak,), graph.Environment("toy", 7, {"data": data}), store,
                                store.cache.parent / "notes", {})
    line, status = command.restore(runner, ("hangar",), True, 1, data / "restore.json", say=quiet)
    assert status == 1 and "spend ledger lines added [1, 0]" in line and "EUR 0" not in line, line


def test_blender_is_refused_however_it_is_started():
    for call in (["/opt/blender-5.0.1/blender", "-b"], "cd /work && blender -b x.blend", pathlib.Path("/opt/blender"),
                 [b"blender"]):
        assert restore.heavy_program(call), call
    assert restore.heavy_program(["python3", "x.py"], executable="/opt/blender/blender")
    assert restore.heavy_program(["git", "rev-parse", "HEAD"]) is None


def test_the_restore_refuses_to_start_while_paid_work_is_open():
    kept = restore.ledger.BOOKS
    restore.ledger.BOOKS = SCRATCH / "books.json"
    restore.ledger.write_books({"month": restore.ledger.this_month(), "state": "known"})
    try:
        refused = command.start_refusal(command.parse(["world1", "--library", str(SCRATCH)]))
    finally:
        restore.ledger.BOOKS.unlink()
        restore.ledger.BOOKS = kept
    assert "paid work is open" in refused


def test_reattach_is_the_owners_own():
    library = pathlib.Path(tempfile.mkdtemp())
    (library / "entries").mkdir()
    os.environ["CLAUDECODE"] = os.environ.get("CLAUDECODE", "1")
    refused = command.start_refusal(command.parse(["world1", "--library", str(library), "--reattach", "--max-gb", "1"]))
    assert "owner" in refused, refused


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[3] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
