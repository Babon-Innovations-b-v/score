"""Invariant of kept.py: each job that ended well inside a make, and each per-take call of a row the stage table names
(PER_TAKE), is kept by its own content (its JSON or arguments and the files they name with the attempt's own folders
written as stand-ins, the row's code, the system), its files once in the store's blobs; a later attempt, at the same
key or a new one, gets back exactly the jobs and takes of the same content, linked in read-only, and makes only the
rest; nothing kept is ever taken for a changed input, script, row code or system, from a copy cut short, or for an
output outside the making folder; and the sweep drops only what its
`asked` refuses (owner, 2026-10-18: a stopped film render threw its finished frames away and the rerun bought them all
again; 2026-10-29: a fix to 3 objects baked whole places again).

Two worlds, no cloud. At the runner: one film row (paid, fake machine) and one per-take views row in one store, made
twice, the film stopped after five of eight jobs the first time and the lamp's model fixed between. On kept's own
calls: one store reached through a link (as a frozen run's is: its home's store links the real one), one first
attempt keeping a job of every kind, the sweep, then a second attempt at a new key and in its own home (as each run on
this PC has) whose one `missing` call is judged against a table naming, per job, whether it comes back kept or is made
again. The break that turns the test red (each applied once, seen red, reverted):

- a rerun runs only the jobs the stopped run lacked: in `missing`, `if entry is None:` -> `if True:` (every job runs
  again).
- a new key bakes again only the take whose inputs changed: in `identity`, `folders = stand_ins()` -> `folders = ()`
  (the attempt's own folders in the content: every take is baked again); or in `written_mark`, `if other != place:` ->
  `if False:` (the old crate stays beside the new).
- a changed input, script, row code or system runs again: in `identity`, drop `inputs`, `code` or `system` from the
  content's list (a changed model, row code or system is taken as kept).
- another process hashes no file version again, its hash read from beside the kept jobs (2026-11-06: fifteen bake
  calls hashed their inputs whole for ten minutes): in `file_hash`, `facts = hashed_before(record)` -> `facts = None`.
- a file is read in chunks, never whole, and a word across two chunks is still found: in `read_through`, drop `tail +`
  (a word cut by a chunk's end is missed).
- the rows' Python is left to its code and its data is not: in `left_to_code`, `return path.suffix in LEFT_TO_CODE or
  ...` -> `return False` (a Python edit no row reads bakes again); or -> `return True` (a changed data table is taken
  as kept).
- a copy cut short before its done mark is not taken: in `mark_of`, `if mark.exists() else None` -> `if
  mark.parent.exists() else None` (an entry without its mark is read); in `entries`, drop the `except
  FileNotFoundError: continue` (a mark listed but gone when read, a dangling link, stops the whole make).
- outside a make or the making folder nothing is kept: in `relative_outputs`, `return None` -> `continue` (a job
  writing outside the making folder is kept with no outputs); or in `identity`, `code is None or ` dropped.
- at the runner a failed make reruns only its lacking jobs and keeps them for the next key: in score/graph/__init__.py
  `making_in`, `MAKING_CODE: code` dropped from the update (no job is kept under a runner).
- identical kept files are one blob linked back read-only: in `stored`, `sha = blob_hash(path)` -> `sha =
  hashlib.sha256(str(path).encode()).hexdigest()` (each file stored again under its path); or in `placed`,
  `blobs.place_blob(sha, place)` -> a copy of the blob (no link).
- an unchanged take of a rekeyed row is linked back, not made again: in `call`, `if entry is not None:` -> `if
  False:`; or in score/stages/__init__.py `per_take_kept`, the `namespace[name] = lambda ...` line -> `pass` (the
  crate's views made again); or in `call`, `json.dumps(record, sort_keys=True)` -> `json.dumps(record)` (a made
  take's record keeps its own key order, a kept one's comes back sorted: the row's output bytes depend on what was
  kept, finish-route-views@tube 2026-11-07).
- the sweep drops only what no current key asks for: in `sweep`, `if asked(entry):` -> `if True:` (nothing dropped);
  or `- held - output_blobs()` -> `- held` (a blob a stored output holds is freed).
- a job kept as copies before the blobs (env1 2026-10-29: this PC's run kept its jobs as copies under 5a46a96e) is
  put back and turned into blobs: in `mark_of`, `if named is None or not` -> `if True or not` (a copy left unread: the
  frame is made again); or in `sweep`, drop the `if "files" not in entry: continue` (the copy dropped before it is
  turned); or `stored(files_under(outputs), outputs)` -> `stored(files_under(outputs), place / "outputs")` (through
  the store's link: ValueError, not in the subpath).
"""
import hashlib
import json
import os
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import kept  # noqa: E402

FIRSTS = range(0, 96, 12)  # eight jobs of twelve frames
SYSTEM = "score-this-pc:1 sha256:0123"
TAKES = ("barrel", "crate", "lamp", "pail", "tub")
MADE = []  # the takes views_of made, in order
# Each job of the kept world's second attempt, and whether it comes back kept (True) or is made again (False).
COMES_BACK = {
    **{f"frames {first}": first < 60 for first in FIRSTS},  # five of eight came back before the stop
    "bake barrel": True,  # its script written again with the same bytes, its model's hash read from beside the kept
    "bake crate": False,  # its model fixed
    "bake lamp": True,
    "bake pail": False,  # its script changed
    "bake tub": False,  # its model now names the folders
    "python edited": True,  # a module and a page of a shipped repository folder edited: the row's code's to key
    "table edited": False,  # a data table in a shipped repository folder changed: the job's own input
    "cut short": False,  # its mark never written
    "mark gone": False,  # its mark a link to nothing
    "black 144": True, "black 156": True,  # the same bytes, one blob
    "swept": False,  # dropped by the sweep
    "asked": True,  # kept by the sweep
    "copies": True,  # kept as copies before the blobs, turned on its first read
    "outside": False,  # writes outside the making folder
    "no code": False,  # made outside a make
}


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


def bake(folder, take, models):
    """A bake row's paint and bake job of one take: its listing (naming the making folder and the home, as
    route_bake.card_job's does) and its model as inputs, its models brought back into its own folder
    (route_bake.made_of)."""
    listing = folder / f".bake-{take}.json"
    listing.write_text(f'{{"take": "{take}", "out": "{folder}", "home": "{os.environ["PROPS_HOME"]}"}}')
    return {"script": "score/stages/surfaces/inside/paint_bake.py", "args": [str(listing)],
            "inputs": [str(listing), str(models / f"{take}.glb")],
            "outputs": [str(folder / "labelled" / take), str(folder / f".bake-{take}-made")], "minutes": 5}


def baked(job, made_by):
    """What the machine brings back for a bake job: its labelled take and its model in its own folder; the files
    written."""
    labelled, made = (pathlib.Path(output) for output in job["outputs"])
    take = labelled.name
    labelled.mkdir(parents=True, exist_ok=True)
    made.mkdir(exist_ok=True)
    (labelled / "labels.json").write_text(f"{take} by {made_by}")
    (made / f"{take}.gltf").write_text(f"{take} by {made_by}")
    return {(labelled / "labels.json").resolve(), (made / f"{take}.gltf").resolve()}


def models_of(root, takes):
    """Each take's model (a job input), holding its own text."""
    models = root / "pixal"
    models.mkdir(parents=True, exist_ok=True)
    for take, text in takes.items():
        (models / f"{take}.glb").write_text(text)
    return models


def world_jobs(folder, root):
    """Every job of the kept world, by name (COMES_BACK's), at an attempt's making folder."""
    jobs = {f"frames {first}": frames(folder, first) for first in FIRSTS}
    for take in TAKES:
        jobs[f"bake {take}"] = bake(folder, take, root / "pixal")
    for take in ("barrel", "pail"):
        jobs[f"bake {take}"]["script"] = str(root / "scripts" / f"{take}.py")
    jobs["python edited"] = {**frames(folder, 96), "inputs": [str(root / "repo" / "score")]}
    jobs["table edited"] = {**frames(folder, 108), "inputs": [str(root / "repo" / "other")]}
    for name, first in (("cut short", 120), ("mark gone", 132), ("black 144", 144), ("black 156", 156),
                        ("swept", 168), ("asked", 180), ("copies", 192), ("no code", 216)):
        jobs[name] = frames(folder, first)
    jobs["outside"] = {**frames(folder, 204), "outputs": [str(root / "elsewhere")]}
    return jobs


def written_frame(job, name, text):
    """One frame file of a job's own text, brought back into its output folder."""
    out = pathlib.Path(job["outputs"][0])
    out.mkdir(parents=True, exist_ok=True)
    (out / name).write_text(text)
    return out / name


def mark(job):
    """The done mark a job is kept under at this attempt."""
    slot, content, _ = kept.identity(job, SYSTEM)
    return kept.kept_root() / slot / content / kept.DONE


def views_of(source, folder):
    """A per-take call as the finish route's views make one: the take's views written into its own folder from its
    model, its record given."""
    MADE.append(pathlib.Path(source).name)
    folder.mkdir(parents=True)
    (folder / "views.npz").write_text(f"views of {pathlib.Path(source).read_text()}")
    return {"views": 3, "model": pathlib.Path(source).name}  # keys unsorted, as a made record's may be


def test_kept_rerun_pays_only_for_missing_jobs(monkeypatch, tmp_path):
    from score import checks, contracts, graph, stages
    from score.adapters import compute
    from score.store import Store

    # --- at the runner: a film make that fails after five of eight jobs, and a per-take views row (env1 2026-10-29:
    # finish-route-views remade 537 takes whose views came out byte for byte the same), made twice in one store ---
    monkeypatch.setattr(compute, "cloud_bill", lambda: 0.0)  # no cloud: a fake bill
    monkeypatch.setattr(compute.ledger(), "BOOKS", compute.ledger().BOOKS)  # recorded: open_books_for_tests moves it
    compute.ledger().open_books_for_tests(str(tmp_path / "books"))  # this month's books known: paid paths open
    for name in (kept.STORE, kept.MAKING, kept.CODE):
        monkeypatch.delenv(name, raising=False)
    home = tmp_path / "runner" / "home"
    monkeypatch.setenv("PROPS_HOME", str(home))
    models = models_of(tmp_path / "runner", {"crate": "crate model", "lamp": "lamp model"})
    rendered, fail_after = [], [5]
    MADE.clear()

    def make_film(inputs, out, seed, params):
        jobs = [frames(out, first) for first in FIRSTS]
        for number, job in enumerate(kept.missing(jobs, SYSTEM)):
            if number == fail_after[0]:
                raise RuntimeError("the run was stopped")
            render(job)  # a fake machine
            rendered.append(job["args"][1])
            kept.keep(job, SYSTEM)

    def make_views(inputs, out, seed, params):
        found = {take: views_of(inputs[f"model {take}"], out / take) for take in ("crate", "lamp")}
        (out / "views.json").write_text(json.dumps(found))

    def judge_made(output, inputs, evidence):
        return checks.Verdict("made", checks.PASS, "the frames are there")

    film = graph.Stage("film", "place", make_film, contracts.Contract("toy-film", 1, lambda folder: []),
                       (checks.Check("made", judge_made),), paid=True, euros=0.5)
    views = graph.Stage("toy-views", "place",
                        stages.per_take_kept(make_views, "views_of", lambda arguments: arguments[1]),
                        contracts.Contract("toy-views", 1, lambda folder: []), (checks.Check("made", judge_made),),
                        files={f"model {take}": str(models / f"{take}.glb") for take in ("crate", "lamp")})

    def runner():
        return graph.Runner([film, views], graph.Environment("toy", 1, {}), Store.in_folder(str(home / "store")))

    first_run = runner()
    with pytest.raises(RuntimeError, match="the run was stopped"):
        first_run.run_node(film, "airlock")
    assert len(rendered) == 5
    first_run.run_node(views, "airlock")
    first_views = first_run.store.record("toy-views@airlock", first_run.key(views, "airlock")["key"])
    (models / "lamp.glb").write_text("lamp model, fixed")
    fail_after[0] = 99
    second_run = runner()
    second_run.run_node(film, "airlock")
    second_run.run_node(views, "airlock")
    second_views = second_run.store.record("toy-views@airlock", second_run.key(views, "airlock")["key"])
    store = second_run.store
    assert sorted(rendered[5:], key=int) == ["60", "72", "84"]
    assert "frames/part84/095.png" in store.listing(store.accepted("film@airlock"))
    film_marks = [found for found in (store.cache.parent / "kept").rglob(kept.DONE)
                  if "job" in json.loads(found.read_text())]
    assert len(film_marks) == 8  # kept beside the run's store, for the next key
    assert first_views["key"] != second_views["key"]
    assert MADE == ["crate.glb", "lamp.glb", "lamp.glb"]  # the crate's views linked back, not made again
    assert store.listing(second_views["output"])["crate/views.npz"] == \
        store.listing(first_views["output"])["crate/views.npz"]
    assert store.read_file(second_views["output"], "views.json")["crate"] == {"model": "crate.glb", "views": 3}
    written = json.loads((store.checkout(second_views["output"]) / "views.json").read_text())
    assert list(written["crate"]) == list(written["lamp"])  # a kept take's record and a made one's, the same bytes

    # --- on kept's own calls: one store through a link, a first attempt keeping a job of every kind ---
    (tmp_path / "real-store").mkdir()
    (tmp_path / "store").symlink_to(tmp_path / "real-store")
    repo = tmp_path / "repo"
    for name, text in (("repo/score/people.py", "PEOPLE = 1"), ("repo/score/table.json", "[1]"),
                       ("repo/score/dashboard/page.html", "<p>"), ("repo/other/helper.py", "HELP = 1"),
                       ("repo/other/table.json", "[1]"), ("scripts/barrel.py", "print('bake the barrel')"),
                       ("scripts/pail.py", "print('bake the pail')")):
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text(text)
    (tmp_path / "elsewhere").mkdir()
    monkeypatch.setattr(kept, "REPO", repo)
    monkeypatch.setattr(kept, "framework", lambda: frozenset({repo / "score" / "dashboard"}))
    models = models_of(tmp_path, {take: f"{take} model" for take in TAKES})
    folder = attempt(monkeypatch, tmp_path, "first", home=tmp_path / "run1.home")
    first = world_jobs(folder, tmp_path)
    for first_frame in FIRSTS[:5]:
        render(first[f"frames {first_frame}"])
        assert kept.keep(first[f"frames {first_frame}"], SYSTEM)
    for take in TAKES:
        assert kept.keep(first[f"bake {take}"], SYSTEM, brought=baked(first[f"bake {take}"], "the first run"))
    for name in ("python edited", "table edited", "cut short", "mark gone"):
        render(first[name])
        assert kept.keep(first[name], SYSTEM)
    for name, text in (("black 144", "the same black frame"), ("black 156", "the same black frame"),
                       ("swept", "only the swept job"), ("asked", "the asked job")):
        written_frame(first[name], "frame.png", text)
    shared = written_frame(first["swept"], "shared.png", "a frame a stored output holds")
    for name in ("black 144", "black 156", "swept", "asked"):
        assert kept.keep(first[name], SYSTEM)
    copies = mark(first["copies"]).parent  # kept as copies, as 5a46a96e did
    written_frame({"outputs": [str(copies / "outputs" / "frames" / "part192")]}, "192.png", "frame 192")
    (copies / kept.DONE).write_text(json.dumps({"job": first["copies"], "peers": {}}, sort_keys=True))
    assert not kept.keep(first["outside"], SYSTEM) and kept.missing([first["outside"]], SYSTEM) == [first["outside"]]
    render(first["no code"])
    monkeypatch.delenv(kept.CODE)
    assert not kept.keep(first["no code"], SYSTEM) and kept.missing([first["no code"]], SYSTEM) == [first["no code"]]
    monkeypatch.setenv(kept.CODE, "row code 1")
    cut = mark(first["cut short"])
    cut.unlink()  # the copy was cut before its mark
    gone = mark(first["mark gone"])
    gone.unlink()
    gone.symlink_to(tmp_path / "gone")  # a mark listed but gone when read
    kept.store().put_tree(shared)  # a stored output holding one of the swept job's files
    blobs = tmp_path / "store" / "objects" / "blobs"
    swept_blob, shared_blob, asked_blob = (blobs / kept.blob_hash(path) for path in (
        shared.with_name("frame.png"), shared, pathlib.Path(first["asked"]["outputs"][0]) / "frame.png"))
    swept_slot = mark(first["swept"]).parent.parent
    done = kept.sweep(lambda entry: entry["job"] not in (first["swept"], first["copies"]), say=lambda line: None)
    assert done["dropped"] == 1 and not swept_slot.exists() and (copies / "outputs").is_dir()
    assert not swept_blob.exists() and shared_blob.exists() and asked_blob.exists()
    left = [entry["job"] for _, entry in kept.entries()]
    assert first["outside"] not in left and first["no code"] not in left and first["cut short"] not in left and \
        first["mark gone"] not in left

    # --- the second attempt: a new key, its own home, the inputs changed as COMES_BACK says, one `missing` ---
    (models / "crate.glb").write_text("crate model, fixed")
    (models / "tub.glb").write_text(f"tub model naming {tmp_path}")  # one naming the folders is hashed with them
    (tmp_path / "scripts" / "pail.py").write_text("print('bake the pail otherwise')")
    (tmp_path / "scripts" / "barrel.py").write_text("print('bake the barrel')")  # the same bytes, a new file version
    (repo / "score" / "people.py").write_text("PEOPLE = 2")
    (repo / "score" / "dashboard" / "page.html").write_text("<p>new")
    (repo / "other" / "table.json").write_text("[2]")
    kept.HASHES.clear()  # another process: what it knows of a file version is read from beside the kept jobs
    through = kept.read_through
    monkeypatch.setattr(kept, "read_through", lambda path, word: (_ for _ in ()).throw(AssertionError(f"read {path}"))
                        if path.name == "barrel.glb" else through(path, word))
    again = attempt(monkeypatch, tmp_path, "second", home=tmp_path / "run2.home")
    rerun = world_jobs(again, tmp_path)
    waiting = kept.missing(list(rerun.values()), SYSTEM)
    assert {name: job not in waiting for name, job in rerun.items()} == COMES_BACK
    assert waiting == [job for name, job in rerun.items() if not COMES_BACK[name]]  # in their order
    monkeypatch.setattr(kept, "read_through", through)
    assert (again / "frames" / "part48" / "059.png").read_text() == "frame 59"  # put back where the job writes
    assert not (again / "frames" / "part60").exists()
    assert {path.name: path.read_text() for path in again.glob(".bake-*-made/*")} == {
        "barrel.gltf": "barrel by the first run", "lamp.gltf": "lamp by the first run"}
    assert (again / "labelled" / "lamp" / "labels.json").read_bytes() == \
        (folder / "labelled" / "lamp" / "labels.json").read_bytes()
    black = blobs / kept.blob_hash(pathlib.Path(first["black 144"]["outputs"][0]) / "frame.png")
    for name in ("black 144", "black 156"):
        back = pathlib.Path(rerun[name]["outputs"][0]) / "frame.png"
        assert back.read_text() == "the same black frame" and back.stat().st_ino == black.stat().st_ino
        assert not back.stat().st_mode & 0o222
    assert (again / "frames" / "part192" / "192.png").read_text() == "frame 192"
    assert not (copies / "outputs").exists() and "files" in json.loads((copies / kept.DONE).read_text())
    crate = rerun["bake crate"]
    assert kept.keep(crate, SYSTEM, brought=baked(crate, "the second run"))
    assert len(list(mark(crate).parent.parent.iterdir())) == 1  # the new crate replaces the old
    unchanged = [rerun["bake barrel"], rerun["bake lamp"]]
    assert kept.missing(unchanged, "score-this-pc:1 sha256:4567") == unchanged  # another system
    third = attempt(monkeypatch, tmp_path, "third", code="row code 2")
    recoded = bake(third, "lamp", models)
    assert kept.missing([recoded], SYSTEM) == [recoded]  # the row's code changed

    # --- a file is hashed CHUNK bytes at a time, a word across two chunks still found ---
    monkeypatch.setattr(kept, "CHUNK", 4)
    for data, word, found in ((b"abcdROOTxyz", b"ROOT", True), (b"abcROOTxyz", b"ROOT", True),  # abcR|OOTx
                              (b"abcROOTxyz", b"NOPE", False)):
        (tmp_path / "split.bin").write_bytes(data)
        assert kept.read_through(tmp_path / "split.bin", word) == (hashlib.sha256(data).hexdigest(), found), data
