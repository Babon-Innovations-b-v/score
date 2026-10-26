"""Invariant of kept.py: a stopped or failed paid run keeps each job that ended well under its node and key, and its
rerun (in a fresh making folder) gets exactly those back in place and runs only the rest; nothing kept is ever taken
by another key, by a changed job, from a copy cut short, or for an output outside the making folder (owner,
2026-10-18: a stopped film render threw its finished frames away and the rerun bought them all again).

Fake film jobs, no cloud: the answers are counted from the jobs the test lets finish. The break that turns each red
(applied once, seen red, reverted):

- test_a_rerun_runs_only_the_jobs_the_stopped_run_lacked: in `missing`, `if not put_back(job)` -> `if True` (every
  job runs again).
- test_another_key_or_a_changed_job_takes_nothing: in `key_folder`, `/ "kept" / node / key` -> `/ "kept" / node` (a
  rerun at another key takes the old key's jobs).
- test_a_copy_cut_short_before_its_done_mark_is_not_taken: in `put_back`, `if found is None or not (found[0] /
  DONE).exists()` -> `if found is None` (a half-copied job is taken).
- test_outside_a_ticket_or_the_making_folder_nothing_is_kept: in `relative_outputs`, `return None` -> `continue` (a
  job writing outside the making folder is kept with no outputs).
- test_at_the_runner_a_failed_paid_make_reruns_only_its_lacking_jobs_and_drops_the_kept_once_stored: in
  score/graph/__init__.py `drop_kept`, `if folder.exists():` -> `if False:` (the kept jobs outlive the stored output).
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import kept  # noqa: E402

FIRSTS = range(0, 96, 12)  # eight jobs of twelve frames


def attempt(monkeypatch, root, name, ticket="demo-film@airlock k1"):
    """A fresh make attempt under `ticket`, the env set as the runner sets it; its making folder."""
    folder = root / name
    folder.mkdir()
    monkeypatch.setenv(kept.TICKET, ticket)
    monkeypatch.setenv(kept.STORE, str(root / "store"))
    monkeypatch.setenv(kept.MAKING, str(folder))
    return folder


def frames(folder, first):
    """A film job of frames first..first+11 rendered into the making folder."""
    return {"script": "tools/blender/inside/usd_views.py", "args": [str(folder / "views.json"), str(first),
                                                                     str(first + 11)],
            "inputs": [str(folder / "stage")], "outputs": [str(folder / "frames" / f"part{first}")], "minutes": 5}


def render(job):
    """What a machine would bring back: the job's frames, each holding its own number."""
    out = pathlib.Path(job["outputs"][0])
    out.mkdir(parents=True, exist_ok=True)
    for frame in range(int(job["args"][1]), int(job["args"][2]) + 1):
        (out / f"{frame:03d}.png").write_text(f"frame {frame}")


def test_a_rerun_runs_only_the_jobs_the_stopped_run_lacked(monkeypatch, tmp_path):
    folder = attempt(monkeypatch, tmp_path, "first")
    for job in [frames(folder, first) for first in FIRSTS][:5]:  # five of eight came back before the stop
        render(job)
        assert kept.keep(job)
    again = attempt(monkeypatch, tmp_path, "again")
    rerun = [frames(again, first) for first in FIRSTS]
    assert kept.missing(rerun) == rerun[5:]
    assert (again / "frames" / "part48" / "059.png").read_text() == "frame 59"  # put back where the job writes
    assert not (again / "frames" / "part60").exists()


def test_another_key_or_a_changed_job_takes_nothing(monkeypatch, tmp_path):
    folder = attempt(monkeypatch, tmp_path, "first")
    job = frames(folder, 0)
    render(job)
    assert kept.keep(job)
    other_key = attempt(monkeypatch, tmp_path, "other-key", "demo-film@airlock k2")
    assert kept.missing([frames(other_key, 0)]) == [frames(other_key, 0)]
    same_key = attempt(monkeypatch, tmp_path, "same-key")
    changed = {**frames(same_key, 0), "minutes": 6}
    assert kept.missing([changed]) == [changed]


def test_a_copy_cut_short_before_its_done_mark_is_not_taken(monkeypatch, tmp_path):
    folder = attempt(monkeypatch, tmp_path, "first")
    job = frames(folder, 0)
    render(job)
    assert kept.keep(job)
    [mark] = (tmp_path / "store" / "kept").rglob(kept.DONE)
    mark.unlink()  # the copy was cut before its mark
    again = attempt(monkeypatch, tmp_path, "again")
    assert kept.missing([frames(again, 0)]) == [frames(again, 0)]


def test_outside_a_ticket_or_the_making_folder_nothing_is_kept(monkeypatch, tmp_path):
    folder = attempt(monkeypatch, tmp_path, "first")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    outside = {**frames(folder, 0), "outputs": [str(elsewhere)]}
    assert not kept.keep(outside) and kept.missing([outside]) == [outside]
    job = frames(folder, 0)
    render(job)
    monkeypatch.delenv(kept.TICKET)
    assert not kept.keep(job) and kept.missing([job]) == [job]
    assert not (tmp_path / "store" / "kept").exists()


def test_at_the_runner_a_failed_paid_make_reruns_only_its_lacking_jobs_and_drops_the_kept_once_stored(
        monkeypatch, tmp_path):
    """The runner names the make's folder and the ticket itself; a make that renders through kept and fails after
    five of eight jobs renders three on its rerun, and the kept jobs are gone once the output is stored."""
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
    from score import checks, contracts, graph
    from score.adapters import compute
    from score.store import Store
    monkeypatch.setattr(compute, "cloud_bill", lambda: 0.0)  # no cloud: a fake bill
    compute.ledger().open_books_for_tests(str(tmp_path / "books"))  # this month's books known: paid paths open
    for name in (kept.TICKET, kept.STORE, kept.MAKING):
        monkeypatch.delenv(name, raising=False)
    rendered, fail_after = [], [5]

    def make_film(inputs, out, seed, params):
        jobs = [frames(out, first) for first in FIRSTS]
        for number, job in enumerate(kept.missing(jobs)):
            if number == fail_after[0]:
                raise RuntimeError("the run was stopped")
            render(job)  # a fake machine
            rendered.append(job["args"][1])
            kept.keep(job)

    def judge_made(output, inputs, evidence):
        return checks.Verdict("made", checks.PASS, "the frames are there")

    film = graph.Stage("film", "place", make_film, contracts.Contract("toy-film", 1, lambda folder: []),
                       (checks.Check("made", judge_made),), paid=True, euros=0.5)
    store = Store.in_folder(str(tmp_path / "run-store"))
    runner = graph.Runner([film], graph.Environment("toy", 1, {}), store)
    try:
        runner.run_node(film, "airlock")
        raise AssertionError("the first try was to fail")
    except RuntimeError as stopped:
        assert "the run was stopped" in str(stopped)
    assert len(rendered) == 5
    fail_after[0] = 99
    runner.run_node(film, "airlock")
    assert sorted(rendered[5:], key=int) == ["60", "72", "84"]
    assert "frames/part84/095.png" in store.listing(store.accepted("film@airlock"))
    assert not any((store.cache.parent / "kept").rglob(kept.DONE))
