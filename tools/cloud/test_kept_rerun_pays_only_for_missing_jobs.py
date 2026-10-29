"""Invariant of kept.py: each job that ended well inside a make is kept by its own content (its JSON and input files
with the attempt's own folders written as stand-ins, the row's code, the system), and a later attempt, at the same
key or a new one, gets back exactly the jobs of the same content and runs only the rest; nothing kept is ever taken
for a changed input, script, row code or system, from a copy cut short, for an output outside the making folder, or
with another job's file made from other inputs (owner, 2026-10-18: a stopped film render threw its finished frames
away and the rerun bought them all again; 2026-10-29: a fix to 3 objects baked whole places again).

Fake film and bake jobs, no cloud: the answers are counted from the jobs the test lets finish. The break that turns
each red (applied once, seen red, reverted):

- test_a_rerun_runs_only_the_jobs_the_stopped_run_lacked: in `missing`, `if mark is None or not mark.exists() or
  any(` -> `if True or any(` (every job runs again).
- test_jobs_sharing_a_folder_get_back_each_ones_newest_file: in `merge`, drop the `if place.is_file() and ...
  st_mtime_ns ...: continue` (every kept copy replaces what is there) -> the barrel's half-written model comes back.
- test_a_new_key_bakes_again_only_the_take_whose_inputs_changed: in `identity`, `folders = stand_ins()` ->
  `folders = ()` (the attempt's own folders in the content: every take is baked again); or in `keep`, the loop
  `for other in (kept_root() / slot).iterdir()` removing nothing (`if False:`) -> the old crate stays beside the new.
- test_a_changed_input_script_code_or_system_runs_again: in `identity`, drop `input_files(job, folders)` from the
  content (a changed model is taken as kept); or drop `code`, or `system`, from it.
- test_the_rows_python_is_left_to_its_code_and_its_data_is_not: in `left_to_code`, `return path.suffix in
  LEFT_TO_CODE or ...` -> `return False` (a Python edit no row reads bakes again); or -> `return True` (a changed
  data table is taken as kept).
- test_a_job_whose_copy_carried_a_changed_peer_runs_again: in `missing`, drop the `any(present.get(slot) != content
  ...)` test -> the crate is put back with the barrel's old model.
- test_a_copy_cut_short_before_its_done_mark_is_not_taken: in `missing`, `if mark is None or not mark.exists()` ->
  `if mark is None` (a half-copied job is taken).
- test_outside_a_make_or_the_making_folder_nothing_is_kept: in `relative_outputs`, `return None` -> `continue` (a
  job writing outside the making folder is kept with no outputs); or in `identity`, `code is None or ` dropped.
- test_at_the_runner_a_failed_make_reruns_only_its_lacking_jobs_and_keeps_them_for_the_next_key: in
  score/graph/__init__.py `making_in`, `MAKING_CODE: code` dropped from the update (no job is kept under a runner).
"""
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import kept  # noqa: E402

FIRSTS = range(0, 96, 12)  # eight jobs of twelve frames
SYSTEM = "score-this-pc:1 sha256:0123"


def attempt(monkeypatch, root, name, code="row code 1", home=None):
    """A fresh make attempt, the env set as the runner sets it (its home under `home`); its making folder."""
    home = home or root / "home"
    folder = home / "making" / name
    folder.mkdir(parents=True)
    monkeypatch.setenv("PROPS_HOME", str(home))
    monkeypatch.setenv(kept.STORE, str(root / "store"))
    monkeypatch.setenv(kept.MAKING, str(folder))
    monkeypatch.setenv(kept.CODE, code)
    return folder


def frames(folder, first):
    """A film job of frames first..first+11 rendered into the making folder."""
    return {"script": "tools/blender/inside/usd_views.py", "args": [str(folder / "views.json"), str(first),
                                                                     str(first + 11)],
            "inputs": [], "outputs": [str(folder / "frames" / f"part{first}")], "minutes": 5}


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
        assert kept.keep(job, SYSTEM)
    again = attempt(monkeypatch, tmp_path, "again")
    rerun = [frames(again, first) for first in FIRSTS]
    assert kept.missing(rerun, SYSTEM) == rerun[5:]
    assert (again / "frames" / "part48" / "059.png").read_text() == "frame 59"  # put back where the job writes
    assert not (again / "frames" / "part60").exists()


def bake(folder, take, models):
    """A bake row's paint and bake job of one take: its listing (naming the making folder and the home, as
    route_bake.card_job's does) and its model as inputs, its models brought back into the row's one `made`."""
    listing = folder / f".bake-{take}.json"
    listing.write_text(f'{{"take": "{take}", "out": "{folder}", "home": "{os.environ["PROPS_HOME"]}"}}')
    return {"script": "score/stages/surfaces/inside/paint_bake.py", "args": [str(listing)],
            "inputs": [str(listing), str(models / f"{take}.glb")],
            "outputs": [str(folder / "labelled" / take), str(folder / "made")], "minutes": 5}


def baked(job, made_by):
    """What the machine brings back for a bake job: its labelled take and its model in `made`; the files written."""
    folder, take = pathlib.Path(job["outputs"][1]).parent, pathlib.Path(job["outputs"][0]).name
    (folder / "labelled" / take).mkdir(parents=True, exist_ok=True)
    (folder / "made").mkdir(exist_ok=True)
    (folder / "labelled" / take / "labels.json").write_text(f"{take} by {made_by}")
    (folder / "made" / f"{take}.gltf").write_text(f"{take} by {made_by}")
    return {(folder / "labelled" / take / "labels.json").resolve(), (folder / "made" / f"{take}.gltf").resolve()}


def models_of(root, takes):
    """Each take's model (a job input), holding its own text."""
    models = root / "pixal"
    models.mkdir(exist_ok=True)
    for take, text in takes.items():
        (models / f"{take}.glb").write_text(text)
    return models


def test_jobs_sharing_a_folder_get_back_each_ones_newest_file(monkeypatch, tmp_path):
    """Side by side on this PC, a bake row's takes bring back its one `made` folder: the crate's job kept the barrel's
    model caught mid-write, the barrel's job its finished one; the rerun gets back the finished one."""
    models = models_of(tmp_path, {"barrel": "barrel model", "crate": "crate model"})
    folder = attempt(monkeypatch, tmp_path, "first")
    barrel, crate = (bake(folder, name, models) for name in ("barrel", "crate"))
    made = folder / "made"
    baked(crate, "the first run")
    (made / "barrel.gltf").write_text("half")
    os.utime(made / "barrel.gltf", (1_000, 1_000))
    assert kept.keep(crate, SYSTEM, peers={kept.identity(barrel, SYSTEM)[0]: kept.identity(barrel, SYSTEM)[1]})
    baked(barrel, "the first run")
    assert kept.keep(barrel, SYSTEM)
    again = attempt(monkeypatch, tmp_path, "again")
    rerun = [bake(again, name, models) for name in ("barrel", "crate")]
    assert kept.missing(rerun, SYSTEM) == []
    assert {path.name: path.read_text() for path in (again / "made").iterdir()} == {
        "barrel.gltf": "barrel by the first run", "crate.gltf": "crate by the first run"}


def test_a_new_key_bakes_again_only_the_take_whose_inputs_changed(monkeypatch, tmp_path):
    """env1 (2026-10-29): a fix to one object re-keyed its place's bake row, and every take of it was baked again.
    The next run (its own home and making folder, as each run on this PC has) bakes only the changed take and gets
    the rest back byte for byte."""
    takes = ("barrel", "crate", "lamp")
    models = models_of(tmp_path, {take: f"{take} model" for take in takes})
    folder = attempt(monkeypatch, tmp_path, "key1-a", home=tmp_path / "run1.home")
    first = [bake(folder, take, models) for take in takes]
    for job in first:
        assert kept.keep(job, SYSTEM, brought=baked(job, "the first run"))
    (models / "crate.glb").write_text("crate model, fixed")
    again = attempt(monkeypatch, tmp_path, "key2-b", home=tmp_path / "run2.home")
    rerun = [bake(again, take, models) for take in takes]
    assert kept.missing(rerun, SYSTEM) == [rerun[1]]  # only the crate is baked again
    assert {path.name: path.read_text() for path in (again / "made").iterdir()} == {
        "barrel.gltf": "barrel by the first run", "lamp.gltf": "lamp by the first run"}
    assert (again / "labelled" / "lamp" / "labels.json").read_bytes() == \
        (folder / "labelled" / "lamp" / "labels.json").read_bytes()
    assert kept.keep(rerun[1], SYSTEM, brought=baked(rerun[1], "the second run"))
    assert len(list((tmp_path / "store" / "kept" / kept.identity(rerun[1], SYSTEM)[0]).iterdir())) == 1


def test_a_changed_input_script_code_or_system_runs_again(monkeypatch, tmp_path):
    script = tmp_path / "bake_it.py"
    script.write_text("print('bake')")
    models = models_of(tmp_path, {"crate": "crate model"})
    folder = attempt(monkeypatch, tmp_path, "first")
    job = {**bake(folder, "crate", models), "script": str(script)}
    assert kept.keep(job, SYSTEM, brought=baked(job, "the first run"))
    again = attempt(monkeypatch, tmp_path, "again")
    same = {**bake(again, "crate", models), "script": str(script)}
    assert kept.missing([same], SYSTEM) == []
    assert kept.missing([same], "score-this-pc:1 sha256:4567") == [same]  # another system
    (models / "crate.glb").write_text("crate model, fixed")
    assert kept.missing([same], SYSTEM) == [same]  # a changed input
    (models / "crate.glb").write_text("crate model")
    script.write_text("print('bake it otherwise')")
    assert kept.missing([same], SYSTEM) == [same]  # a changed script
    script.write_text("print('bake')")
    assert kept.missing([same], SYSTEM) == []
    third = attempt(monkeypatch, tmp_path, "third", code="row code 2")
    recoded = {**bake(third, "crate", models), "script": str(script)}
    assert kept.missing([recoded], SYSTEM) == [recoded]  # the row's code changed


def test_the_rows_python_is_left_to_its_code_and_its_data_is_not(monkeypatch, tmp_path):
    """A job ships whole repository folders (the bake's `score`): their Python is the row's code's to key, so an edit
    to a module no row reads moves no job, while a data table they hold is the job's own input."""
    repo = tmp_path / "repo"
    (repo / "score" / "dashboard").mkdir(parents=True)
    (repo / "score" / "people.py").write_text("PEOPLE = 1")
    (repo / "score" / "table.json").write_text("[1]")
    (repo / "score" / "dashboard" / "page.html").write_text("<p>")
    monkeypatch.setattr(kept, "REPO", repo)
    monkeypatch.setattr(kept, "framework", lambda: frozenset({repo / "score" / "dashboard"}))
    folder = attempt(monkeypatch, tmp_path, "first")
    job = {**frames(folder, 0), "inputs": [str(repo / "score")]}
    render(job)
    assert kept.keep(job, SYSTEM)
    again = attempt(monkeypatch, tmp_path, "again")
    rerun = {**frames(again, 0), "inputs": [str(repo / "score")]}
    (repo / "score" / "people.py").write_text("PEOPLE = 2")
    (repo / "score" / "dashboard" / "page.html").write_text("<p>new")
    assert kept.missing([rerun], SYSTEM) == []
    (repo / "score" / "table.json").write_text("[2]")
    assert kept.missing([rerun], SYSTEM) == [rerun]


def test_a_job_whose_copy_carried_a_changed_peer_runs_again(monkeypatch, tmp_path):
    """The crate's copy back carried the barrel's model (the barrel still running beside it, its peer); once the
    barrel's model changes, the crate is baked again too, never put back with the barrel's old model."""
    models = models_of(tmp_path, {"barrel": "barrel model", "crate": "crate model"})
    folder = attempt(monkeypatch, tmp_path, "first")
    barrel, crate = (bake(folder, name, models) for name in ("barrel", "crate"))
    carried = baked(crate, "the first run") | baked(barrel, "the first run")
    assert kept.keep(crate, SYSTEM, brought=carried, peers=kept.peers_of(crate, [barrel], SYSTEM))
    (models / "barrel.glb").write_text("barrel model, fixed")
    again = attempt(monkeypatch, tmp_path, "again")
    rerun = [bake(again, name, models) for name in ("barrel", "crate")]
    assert kept.missing(rerun, SYSTEM) == rerun
    assert not (again / "made").exists()


def test_a_copy_cut_short_before_its_done_mark_is_not_taken(monkeypatch, tmp_path):
    folder = attempt(monkeypatch, tmp_path, "first")
    job = frames(folder, 0)
    render(job)
    assert kept.keep(job, SYSTEM)
    [mark] = (tmp_path / "store" / "kept").rglob(kept.DONE)
    mark.unlink()  # the copy was cut before its mark
    again = attempt(monkeypatch, tmp_path, "again")
    assert kept.missing([frames(again, 0)], SYSTEM) == [frames(again, 0)]


def test_outside_a_make_or_the_making_folder_nothing_is_kept(monkeypatch, tmp_path):
    folder = attempt(monkeypatch, tmp_path, "first")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    outside = {**frames(folder, 0), "outputs": [str(elsewhere)]}
    assert not kept.keep(outside, SYSTEM) and kept.missing([outside], SYSTEM) == [outside]
    job = frames(folder, 0)
    render(job)
    monkeypatch.delenv(kept.CODE)
    assert not kept.keep(job, SYSTEM) and kept.missing([job], SYSTEM) == [job]
    assert not (tmp_path / "store" / "kept").exists()


def test_at_the_runner_a_failed_make_reruns_only_its_lacking_jobs_and_keeps_them_for_the_next_key(
        monkeypatch, tmp_path):
    """The runner names the make's folder and its row's code itself; a make that renders through kept and fails after
    five of eight jobs renders three on its rerun, and its jobs stay kept once the output is stored."""
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
    from score import checks, contracts, graph
    from score.adapters import compute
    from score.store import Store
    monkeypatch.setattr(compute, "cloud_bill", lambda: 0.0)  # no cloud: a fake bill
    monkeypatch.setattr(compute.ledger(), "BOOKS", compute.ledger().BOOKS)  # recorded: open_books_for_tests moves it
    compute.ledger().open_books_for_tests(str(tmp_path / "books"))  # this month's books known: paid paths open
    for name in (kept.STORE, kept.MAKING, kept.CODE):
        monkeypatch.delenv(name, raising=False)
    rendered, fail_after = [], [5]

    def make_film(inputs, out, seed, params):
        jobs = [frames(out, first) for first in FIRSTS]
        for number, job in enumerate(kept.missing(jobs, SYSTEM)):
            if number == fail_after[0]:
                raise RuntimeError("the run was stopped")
            render(job)  # a fake machine
            rendered.append(job["args"][1])
            kept.keep(job, SYSTEM)

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
    assert len(list((store.cache.parent / "kept").rglob(kept.DONE))) == 8
