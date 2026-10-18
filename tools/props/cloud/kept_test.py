"""Checks for kept jobs (kept.py): a stopped or failed run keeps each finished job's outputs under its key, and its
rerun, in a fresh making folder, gets them back in place and runs only the rest; another key, another job, a copy
cut short or an output outside the making folder is never taken. Fake jobs, no cloud.

Run: .venv/bin/python tools/props/cloud/kept_test.py   (make tests runs it in a sandbox home)
"""
import json
import os
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import kept  # noqa: E402


def attempt(ticket="demo-film@airlock k1", store=None):
    """A fresh make attempt under `ticket`: its making folder (the env set as the runner sets it) and the store."""
    store = store or pathlib.Path(tempfile.mkdtemp())
    folder = pathlib.Path(tempfile.mkdtemp())
    os.environ.update({kept.TICKET: ticket, kept.STORE: str(store), kept.MAKING: str(folder)})
    return folder, store


def frames(folder, first, last):
    """A film job of frames first..last, rendered into the making folder."""
    return {"script": "tools/blender/inside/usd_views.py", "args": [str(folder / "views.json"), str(first), str(last)],
            "inputs": [str(folder / "stage")], "outputs": [str(folder / "frames" / f"part{first}")], "minutes": 5}


def render(job):
    """What a machine would bring back: the job's frames."""
    out = pathlib.Path(job["outputs"][0])
    out.mkdir(parents=True, exist_ok=True)
    for frame in range(int(job["args"][1]), int(job["args"][2]) + 1):
        (out / f"{frame:03d}.png").write_text(f"frame {frame}")


def test_a_rerun_pays_only_for_the_frames_the_stopped_run_lacked():
    folder, store = attempt()
    jobs = [frames(folder, first, first + 11) for first in range(0, 96, 12)]
    for job in jobs[:5]:  # five of eight jobs came back before the run stopped
        render(job)
        assert kept.keep(job)
    again, _ = attempt(store=store)
    rerun = [frames(again, first, first + 11) for first in range(0, 96, 12)]
    waiting = kept.missing(rerun)
    assert waiting == rerun[5:]
    assert (again / "frames" / "part48" / "059.png").read_text() == "frame 59"
    assert not (again / "frames" / "part60").exists()


def test_another_key_or_another_job_takes_nothing():
    folder, store = attempt()
    job = frames(folder, 0, 11)
    render(job)
    kept.keep(job)
    other_key, _ = attempt("demo-film@airlock k2", store)
    assert kept.missing([frames(other_key, 0, 11)]) == [frames(other_key, 0, 11)]
    same_key, _ = attempt(store=store)
    changed = {**frames(same_key, 0, 11), "minutes": 6}
    assert kept.missing([changed]) == [changed]


def test_a_copy_cut_short_is_not_taken():
    folder, store = attempt()
    job = frames(folder, 0, 11)
    render(job)
    kept.keep(job)
    (kept.key_folder() / kept.job_name(job, folder.resolve()) / kept.DONE).unlink()  # cut before its mark
    again, _ = attempt(store=store)
    assert kept.missing([frames(again, 0, 11)]) == [frames(again, 0, 11)]


def test_outside_a_ticket_or_the_making_folder_nothing_is_kept():
    folder, _ = attempt()
    outside = {**frames(folder, 0, 11), "outputs": [tempfile.mkdtemp()]}
    assert not kept.keep(outside) and kept.missing([outside]) == [outside]
    job = frames(folder, 0, 11)
    render(job)
    os.environ.pop(kept.TICKET)
    assert not kept.keep(job) and kept.missing([job]) == [job]
    assert json.dumps(job)


def test_at_the_runner_a_failed_paid_make_keeps_its_frames_and_the_rerun_renders_the_rest():
    """The runner names the make's folder and the ticket; a make that renders through kept (as the cloud runners do)
    and fails after five of eight jobs renders three on its rerun, and the kept jobs are dropped once stored."""
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
    from score import checks, contracts, graph
    from score.adapters import compute
    from score.store import Store
    compute.cloud_bill = lambda: 0.0  # no cloud: a fake bill
    for name in (kept.TICKET, kept.STORE, kept.MAKING):
        os.environ.pop(name, None)
    rendered, fail_after = [], [5]

    def make_film(inputs, out, seed, params):
        jobs = [frames(out, first, first + 11) for first in range(0, 96, 12)]
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
    store = Store.in_folder(tempfile.mkdtemp())
    runner = graph.Runner([film], graph.Environment("toy", 1, {}), store)
    try:
        runner.run_node(film, "airlock")
        raise AssertionError("the first try was to fail")
    except RuntimeError:
        pass
    assert len(rendered) == 5
    fail_after[0] = 99
    runner.run_node(film, "airlock")
    assert len(rendered) == 8 and sorted(rendered[5:]) == ["60", "72", "84"]
    assert "frames/part84/095.png" in store.listing(store.accepted("film@airlock"))
    assert not any((store.cache.parent / "kept").rglob(kept.DONE))  # dropped once the output is stored


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[3] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
