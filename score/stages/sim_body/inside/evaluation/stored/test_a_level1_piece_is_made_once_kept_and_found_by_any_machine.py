"""Level 1's pieces in SCORE's store (#70, owner 2026-11-03): each case made once, kept under the key of what made it,
never overwritten or cleared, and found by any later call, so a run makes only what is missing. A toy worker, a
store of the test's own (`Store.in_folder`), two bodies of two clips.

Breaks that turn the test red (each seen red once, 2026-11-03):
- kept_run's lookup before `run` dropped (every body started): the second call launches again.
- `shutil.rmtree(out)` back at the top of `measured` (the 2026-11-03 wipe of 501 seeds): the sentinel beside the
  cases is gone.
- aside's `put_tree` dropped (what stood at a case's path deleted, not kept): the older case folder is not in the store.
- kept_run's `ended` callback not passed to run_all (cases kept only after every body, or never for a failed body):
  the failed body's finished clip is lost and the next call cannot tell it is made.
- kept's `if found(...) is None` dropped and write_once replaced by an overwrite: a second make of a key replaces
  the first.
- keys' "body" part dropped: adding a clip to a body leaves its other clips' keys where they were.
- described's path-to-bytes turn dropped: the rig at another path keys differently and a target file's new bytes
  key the same; KEYED emptied: SKIN_ROWS no longer moves the key; meaning's docstring strip dropped: a docstring
  edit moves it; LEFT_OUT emptied: an edit to measured() moves it.
- lines_kept's write of the store's lines into the file dropped: a fresh run folder resumes from zeros.
- the importer keying with this tree's worker and constants, not --src's: a seed made by other code is found here;
  or taking a case without its m.json: the seeds root's half-written case is kept.

Run: PROPS_HOME=$(mktemp -d) .venv/bin/python -m pytest <this file>
"""
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

import numpy as np

INSIDE = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(INSIDE))
import evaluation  # noqa: E402
import tuning  # noqa: E402
from evaluation import stored  # noqa: E402
from evaluation.stored import __main__ as importer  # noqa: E402
from score.store import Store  # noqa: E402


def jobs_in(folder, cases):
    """{case: job.json} for toy cases, each job naming its own targets file."""
    found = {}
    for case in cases:
        (folder / f"{case}.npz").write_bytes(case.encode())
        (folder / f"{case}.json").write_text(json.dumps({"people": [{"name": case,
                                                                    "targets": str(folder / f"{case}.npz")}]}))
        found[case] = str(folder / f"{case}.json")
    return found


def toy(out, calls, fail=()):
    """A launch writing each case's files into `out` as `_case.py` does; a body in `fail` writes its first clip only
    and fails."""
    def launch(body, cases):
        calls.append(body)
        for index, case in enumerate(cases):
            if body in fail and index:
                return subprocess.Popen(["false"])
            (out / case).mkdir(parents=True, exist_ok=True)
            np.savez(out / case / evaluation.SEEDS, qpos=np.full((2, 3), len(calls)))
            found = {"case": case, "table": json.loads((out / "table.json").read_text()), "made": len(calls)}
            (out / case / evaluation.SOLVED).write_text(json.dumps(found))
            (out / case / "m.json").write_text(json.dumps(found))
        return subprocess.Popen(["true"])
    return launch


def test_a_level1_piece_is_made_once_kept_and_found_by_any_machine():
    with tempfile.TemporaryDirectory() as folder:
        root = pathlib.Path(folder)
        store = Store.in_folder(root / "store")
        jobs = root / "jobs"
        jobs.mkdir()
        cases = jobs_in(jobs, ["tall_kimodo", "tall_squat", "slim_kimodo", "slim_squat"])
        (root / "rig.npz").write_bytes(b"rig")
        rest = {"centres": {}, "rig": str(root / "rig.npz")}
        out, calls = root / "seeds", []
        out.mkdir()
        (out / "sentinel.txt").write_text("kept")

        def measured(rows, given=cases, fail=(), where=None):
            return evaluation.measured(rows, {"w": 1}, rest, given, where or out, sys.executable, store=store,
                                       launch=toy(where or out, calls, fail), most=2, free_gb=0)

        # (a) made once, then found: no launch, the same measures
        first = measured({"row": 1})
        assert sorted(calls) == ["slim", "tall"]
        assert measured({"row": 1}) == first and sorted(calls) == ["slim", "tall"]
        # (b) nothing beside the cases cleared; an older folder where a case is placed kept in the store first
        assert (out / "sentinel.txt").read_text() == "kept"
        shutil.rmtree(out / "tall_kimodo")
        (out / "tall_kimodo").mkdir()
        (out / "tall_kimodo" / "old.txt").write_text("older")
        assert measured({"row": 1}) == first and len(calls) == 2
        asides = [store.read(key) for key in store.objects.keys("level1/aside/")]
        assert any("old.txt" in store.listing(aside["output"]) for aside in asides)
        assert (out / "tall_kimodo" / evaluation.SOLVED).is_file() and (out / "sentinel.txt").is_file()
        # (c) a body that fails after one clip keeps that clip; the next call launches that body only
        try:
            measured({"row": 2}, fail=("slim",))
        except RuntimeError as error:
            assert "slim_squat" in str(error)
        else:
            raise AssertionError("a failed body read as made")
        bodies = evaluation.by_body(cases)
        at2 = ({"row": 2}, {"w": 1}, rest)
        keys2 = stored.keys(store, "cpu", evaluation.WORKER, bodies, at2)
        assert stored.found(store, "cpu", keys2["slim_kimodo"]) is not None
        assert stored.found(store, "cpu", keys2["slim_squat"]) is None
        del calls[:]
        measured({"row": 2})
        assert calls == ["slim"]
        # (d) a second make of a key leaves the first standing
        mark = stored.found(store, "cpu", keys2["tall_kimodo"])
        other = root / "other"
        other.mkdir()
        (other / evaluation.SOLVED).write_text("{}")
        assert stored.kept(store, "cpu", keys2["tall_kimodo"], other, stored.made()) == mark
        # (e) a clip added to tall: tall alone made again, its clips keyed anew
        more = {**cases, **jobs_in(jobs, ["tall_reach"])}
        del calls[:]
        measured({"row": 2}, given=more)
        assert calls == ["tall"]
        moved = stored.keys(store, "cpu", evaluation.WORKER, evaluation.by_body(more), at2)
        assert moved["tall_kimodo"] != keys2["tall_kimodo"] and moved["slim_kimodo"] == keys2["slim_kimodo"]
        # (f) what moves a key and what does not
        copy = root / "inside"
        shutil.copytree(INSIDE, copy, ignore=shutil.ignore_patterns("__pycache__"))

        def key(rows=None, rig=None, inside=copy, seeds=None, kind="cpu"):
            at = (rows or {"row": 2}, {"w": 1}, {"centres": {}, "rig": str(rig or root / "rig.npz")})
            worker = inside / ("evaluation/_case.py" if kind == "cpu" else "evaluation/_card_sets.py")
            return stored.keys(store, kind, worker, bodies, at, seeds, inside=inside)["tall_kimodo"]
        base = key()
        shutil.copyfile(root / "rig.npz", root / "elsewhere.npz")
        assert key(rig=root / "elsewhere.npz") == base
        case_py = copy / "evaluation" / "_case.py"
        case_py.write_text(case_py.read_text().replace('"""', '"""Reworded. ', 1))
        runner = copy / "evaluation" / "__init__.py"
        edited = runner.read_text().replace("    return read_marks(store, marks, out)",
                                            "    return dict(read_marks(store, marks, out))")
        assert edited != runner.read_text()
        runner.write_text(edited)
        stored.code.cache_clear()
        assert key() == base
        runner.write_text(runner.read_text().replace("SKIN_ROWS = False", "SKIN_ROWS = True"))
        stored.code.cache_clear()
        assert key() != base
        runner.write_text(runner.read_text().replace("SKIN_ROWS = True", "SKIN_ROWS = False"))
        stored.code.cache_clear()
        (root / "rig.npz").write_bytes(b"another rig")
        assert key(rig=root / "elsewhere.npz") == base and key() != base
        assert key(rows={"row": 3}) != base
        (jobs / "tall_kimodo.npz").write_bytes(b"other targets")
        stored.path_hash.cache_clear()
        assert key(rig=root / "elsewhere.npz") != base
        seeds = root / "seeds_for_card"
        (seeds / "tall_kimodo").mkdir(parents=True)
        (seeds / "tall_kimodo" / evaluation.SEEDS).write_bytes(b"a")
        card = key(inside=INSIDE, seeds=seeds, kind="card")
        (seeds / "tall_kimodo" / evaluation.SEEDS).write_bytes(b"b")
        assert key(inside=INSIDE, seeds=seeds, kind="card") != card
        # (g) checkpoint lines in the store; a fresh run folder resumes from the best kept anywhere
        lines = [{"time": 1.0, "note": "evaluation", "cost": 2.0, "unknowns": [1.0]},
                 {"time": 2.0, "note": "evaluation", "cost": 1.0, "unknowns": [3.0]}]
        (root / "run1").mkdir()
        (root / "run1" / "checkpoint.jsonl").write_text("".join(json.dumps(line) + "\n" for line in lines))
        assert stored.lines_kept(store, "run", root / "run1" / "checkpoint.jsonl") == 2
        (root / "run2").mkdir()
        assert stored.lines_kept(store, "run", root / "run2" / "checkpoint.jsonl") == 2
        assert list(tuning.resumed(root / "run2" / "checkpoint.jsonl", 1)) == [3.0]
        # (h) a seed_run-shaped root imported under the keys measured finds; its half-written case left to make
        legacy = root / "legacy"
        evaluation.set_written(legacy, {"row": 9}, {"w": 1}, rest, store)
        for case in cases:
            (legacy / case).mkdir()
            np.savez(legacy / case / evaluation.SEEDS, qpos=np.zeros((2, 3)))
            (legacy / case / evaluation.SOLVED).write_text(json.dumps({"case": case, "legacy": True}))
            if case != "slim_squat":
                (legacy / case / "m.json").write_text("{}")
        runner.write_text(runner.read_text().replace("SKIN_ROWS = False", "SKIN_ROWS = True"))
        stored.code.cache_clear()
        elsewhere = importer.imported(store, legacy, copy, cases)  # made by other code: kept, not found here
        assert elsewhere["kept"] == 3 and elsewhere["found here"] == 0
        found = importer.imported(store, legacy, INSIDE, cases)
        assert found["kept"] == 3 and found["skipped"] == ["slim_squat"] and found["found here"] == 3
        del calls[:]
        after = measured({"row": 9}, where=root / "view")
        assert calls == ["slim"] and after["tall_kimodo"] == {"case": "tall_kimodo", "legacy": True}
        assert sorted(path.name for path in legacy.iterdir()) == sorted([*cases, "table.json", "weights.json",
                                                                         "rest.json"])
