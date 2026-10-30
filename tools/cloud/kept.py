"""Finished jobs kept by their own content, so a rerun, or a row made again at a new key, pays only for the jobs whose
own inputs changed (owner, 2026-10-18: a stopped film render threw away its finished frames and the rerun bought them
all again; 2026-10-29: a fix to 3 objects baked whole places again, and a free run on this PC kept nothing at all).

    waiting = kept.missing(jobs, system)            # each job kept at its content put back in place; the jobs to run
    kept.keep(job, system, brought)                 # after a job ended well: the files it brought back, kept
    record = kept.call(function, arguments, output) # a row's per-take call (score/stages PER_TAKE): put back or made
    kept.sweep(asked, say)                          # every kept entry `asked` says no current key asks for, dropped

A job is a cloud runner's job ({"script", "args", "inputs", "outputs", ...}, blender_cloud.py's), run inside a node's
make: the runner names the make's folder (SCORE_MAKING) and the row's code (SCORE_MAKING_CODE, graph's making_code:
its code version, contract, params, seed, models and the files it declares inside the repository). A job's content is
the hash of its JSON and the bytes of every file of its inputs, its script and its env script, with the attempt's own
folders written as {making}, {repo} and {home} (each attempt makes into a fresh folder, each run on this PC has its own
frozen copy and home); the row's code; and `system`, what it runs on (blender_cloud.system: the machine image and the
Blender set-up). The repository's Python files and docs among its inputs, and the run machinery's files (_code.py's
FRAMEWORK), are left to the row's code: the graph's own rule of what code a row is, so an edit no row reads moves no
job. A job is the same job at the next key by its slot (its script, arguments, outputs and env, folders written as
above); each slot keeps one content, a newer keep replacing it. Kept at `kept/<slot>/<content>/done` beside the store
(SCORE_SPEND_STORE, else PROPS_HOME's store), its files in the store's own blobs (score/store: each content once,
read-only, linked back in place): the mark names each file's blob and the time it was written, and is written after
every blob, so a copy cut short is never taken. Outside a make, or for a job with an output outside the making folder,
nothing is kept and every job runs.

A job keeps only the files its own bring-back wrote (`brought`, rsync's list). Jobs never share an output folder
(blender_cloud.shared_outputs refuses them): a shared folder comes back with either job's copy, so a kept job had to
name the jobs beside it and was run again whenever one of them was (a bake row's one `made` folder baked a kept take
again beside each retaken take of its machine, #36 2026-10-30); each bake take brings back into its own
(route_bake.made_of).

A row's per-take call (`call`: a place row's function that makes one take into its own folder from its arguments, named
in the stage table's PER_TAKE) is kept the same way: its content is the function, its arguments (each file or folder
they name by its bytes), the row's code and this Python with its packages; its output folder and its record come back.

`sweep` drops each kept entry its `asked` says no current key could ask for (score/conductor/disk.py clean-kept: its
node gone, its row's code, system or inputs no longer the current ones), and each blob of it no output and no other
entry holds. Never by age.

Imported only from the renting code (outside every stage's code key), so a change here moves no row.
"""
import functools
import hashlib
import importlib.metadata
import importlib.util
import json
import os
import pathlib
import shutil
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.append(str(REPO))
from score.store import Store, file_hash as blob_hash  # noqa: E402  (the store's blobs; it imports no stage)

STORE = "SCORE_SPEND_STORE"
MAKING = "SCORE_MAKING"
CODE = "SCORE_MAKING_CODE"
DONE = "done"
LEFT_TO_CODE = (".py", ".pyc", ".md")
HASHES = {}  # (path, its stat, the stand-ins): the sha256 of its bytes with the stand-ins written in


def making():
    """The folder the running node makes into, or None outside a make."""
    folder = os.environ.get(MAKING)
    return pathlib.Path(folder).resolve() if folder else None


def kept_root():
    """Where finished jobs are kept: beside the store."""
    store = os.environ.get(STORE) or str(pathlib.Path(os.environ.get(
        "PROPS_HOME", pathlib.Path.home() / ".farm-factory-props")) / "store")
    return pathlib.Path(store) / "kept"


@functools.cache
def framework():
    """The run machinery's files and folders (_code.py's FRAMEWORK), read from that file alone: it imports only the
    standard library, and this process may not hold the score package."""
    spec = importlib.util.spec_from_file_location("kept_code_version", REPO / "score/graph/_code.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.FRAMEWORK


def stand_ins():
    """(this attempt's own folder, the stand-in written for it), longest first: the making folder lies in the home."""
    found = {}
    for path, stand_in in ((os.environ.get(MAKING), "{making}"), (str(REPO), "{repo}"),
                           (os.environ.get("PROPS_HOME"), "{home}")):
        if path:
            found.setdefault(path, stand_in)
            found.setdefault(str(pathlib.Path(path).resolve()), stand_in)
    return tuple(sorted(found.items(), key=lambda pair: -len(pair[0])))


def written(text, folders):
    """`text` (str or bytes) with each of the attempt's folders written as its stand-in."""
    for path, stand_in in folders:
        text = text.replace(path, stand_in) if isinstance(text, str) else text.replace(path.encode(), stand_in.encode())
    return text


def file_hash(path, folders):
    """The sha256 of a file's bytes with the attempt's folders written as their stand-ins, once a file version."""
    stat = path.stat()
    key = (path, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns, stat.st_ino, folders)
    if key not in HASHES:
        HASHES[key] = hashlib.sha256(written(path.read_bytes(), folders)).hexdigest()
    return HASHES[key]


def left_to_code(path):
    """True for a repository file the row's code stands for: Python, a doc, or a file of the run machinery."""
    if not path.is_relative_to(REPO):
        return False
    return path.suffix in LEFT_TO_CODE or "__pycache__" in path.parts or path in framework() or \
        not framework().isdisjoint(path.parents)


def files_under(local):
    """Every file at or under a path, sorted; [] for a path that is not there."""
    path = pathlib.Path(local).resolve()
    if path.is_file():
        return [path]
    return sorted(found for found in path.rglob("*") if found.is_file()) if path.is_dir() else []


def input_files(job, folders):
    """[[file, its hash]] of every file the job reads: its script and env script, and each input's files but those
    left to the row's code; an input that is not there named as missing."""
    found = [[written(str(REPO / job[field]), folders), file_hash(REPO / job[field], folders)]
             for field in ("script", "env") if job.get(field) and (REPO / job[field]).is_file()]
    for local in job.get("inputs", ()):
        files = files_under(local)
        if not files:
            found.append([written(str(local), folders), "missing"])
        found += [[written(str(path), folders), file_hash(path, folders)] for path in files if not left_to_code(path)]
    return found


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()[:32]


def relative_outputs(job, folder):
    """The job's outputs as paths inside the making folder, or None when one lies outside it."""
    found = []
    for output in job.get("outputs", ()):
        path = pathlib.Path(output).resolve()
        if not path.is_relative_to(folder):
            return None
        found.append(path.relative_to(folder))
    return found


def identity(job, system):
    """(the job's slot, its content, its input files), or None outside a make or for a job with an output outside the
    making folder."""
    folder, code = making(), os.environ.get(CODE)
    if folder is None or code is None or relative_outputs(job, folder) is None:
        return None
    folders = stand_ins()
    slot = digest(written(json.dumps({field: job.get(field) for field in ("script", "args", "outputs", "env")},
                                     sort_keys=True), folders))
    inputs = input_files(job, folders)
    return slot, digest(json.dumps([written(json.dumps(job, sort_keys=True), folders), code_hash(code), system,
                                    inputs])), inputs


def code_hash(code):
    """The row's code as a kept content holds it: its hash, without the node it names first (the sweep's), as kept
    before the node was named (5a46a96e), so those entries keep their keys."""
    return code.rsplit(" ", 1)[-1]


def store():
    """The store the kept entries lie beside, whose blobs hold their files."""
    return Store.in_folder(kept_root().parent)


def stored(files, folder):
    """{path in the making folder: [its blob, the time it was written]} of each file, its bytes put in the store's
    blobs (once, read-only)."""
    found, blobs = {}, store()
    for path in files:
        sha = blob_hash(path)
        blobs.put_blob(path, sha)
        found[str(path.relative_to(folder))] = [sha, path.stat().st_mtime_ns]
    return found


def written_mark(slot, content, entry):
    """The entry's `done` mark written at its slot and content after its blobs, any other content of the slot
    removed."""
    place = kept_root() / slot / content
    place.mkdir(parents=True, exist_ok=True)
    (place / DONE).write_text(json.dumps(entry, sort_keys=True))
    for other in (kept_root() / slot).iterdir():
        if other != place:
            shutil.rmtree(other)


def keep(job, system, brought=None):
    """Keep a job that ended well at its content, only the files of its outputs in `brought` (every one when None);
    True when kept."""
    named = identity(job, system)
    if named is None:
        return False
    folder = making()
    outputs = relative_outputs(job, folder)
    if not all((folder / output).exists() for output in outputs):
        return False
    files = [path for output in outputs for path in files_under(folder / output)]
    slot, content, inputs = named
    written_mark(slot, content, {"job": job, "code": os.environ[CODE],
                                 "system": digest(system), "inputs": inputs,
                                 "files": stored(files if brought is None else [path for path in files
                                                                                if path in brought], folder)})
    return True


def mark_of(slot, content, named=None):
    """The entry kept at a slot and content, or None. One kept as copies (5a46a96e, before its files went to the
    blobs) is turned first when `named` gives its code, system and inputs: its copies into the blobs and its mark
    rewritten at the same key, then the copies removed."""
    place = kept_root() / slot / content
    entry = json.loads((place / DONE).read_text()) if (place / DONE).exists() else None
    if entry is None or "files" in entry:
        return entry
    if named is None or not (place / "outputs").is_dir():
        return None
    outputs = (place / "outputs").resolve()  # as files_under gives them: a frozen run reaches the store by a link
    entry = {**entry, **named, "files": stored(files_under(outputs), outputs)}
    written_mark(slot, content, entry)
    shutil.rmtree(place / "outputs")
    return entry


def placed(entries):
    """Each file of the entries linked in place in the making folder from its blob, the one written last where two
    entries hold the same file, unless the file there is newer."""
    newest = {}
    for entry in entries:
        for name, (sha, written_at) in entry["files"].items():
            if name not in newest or written_at > newest[name][1]:
                newest[name] = (sha, written_at)
    blobs, folder = store(), making()
    for name, (sha, written_at) in sorted(newest.items()):
        place = folder / name
        if place.is_file():
            if place.stat().st_mtime_ns >= written_at:
                continue
            place.unlink()
        blobs.place_blob(sha, place)


def missing(jobs, system):
    """Every job kept at its content put back in place in this attempt's making folder; the jobs still to run, in
    their order."""
    waiting, back = [], []
    for job in jobs:
        found = identity(job, system)
        entry = mark_of(*found[:2], {"code": os.environ[CODE], "system": digest(system), "inputs": found[2]}) \
            if found else None
        if entry is None:
            waiting.append(job)
            continue
        back.append(entry)
    placed(back)
    return waiting


@functools.cache
def python_system():
    """What a per-take call runs on: this Python and every package it holds, with their versions."""
    packages = sorted(f"{found.metadata['Name']}=={found.version}" for found in importlib.metadata.distributions())
    return " ".join([sys.version, *packages])


def arguments_of(value, folders, inputs):
    """A call's arguments as JSON, each file or folder they name (a Path, or a text naming one) written as its
    stand-in path, its files and their hashes added to `inputs`."""
    if isinstance(value, dict):
        return {str(name): arguments_of(item, folders, inputs) for name, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [arguments_of(item, folders, inputs) for item in value]
    if isinstance(value, pathlib.PurePath) or isinstance(value, str) and value.startswith("/") and \
            os.path.exists(value):
        inputs += [[written(str(path), folders), file_hash(path, folders)] for path in files_under(value)
                   if not left_to_code(path)]
        return {"path": written(str(value), folders)}
    return value


def call(function, arguments, output):
    """A row's per-take call: `function(*arguments)`, which makes one take into the folder `output` and gives its
    record. Kept at its content (the function, its arguments with the files they name, the row's code, this Python):
    the same call again, at any key, gets its folder linked back in place and its record without running. Outside a
    make, for an output outside the making folder or a record JSON cannot hold, it runs and nothing is kept."""
    folder, code, output = making(), os.environ.get(CODE), pathlib.Path(output).resolve()
    if folder is None or code is None or not output.is_relative_to(folder):
        return function(*arguments)
    folders, inputs = stand_ins(), []
    named = f"{function.__module__}.{function.__qualname__}"
    described = arguments_of(list(arguments), folders, inputs)
    try:
        content = digest(json.dumps([named, code_hash(code), python_system(), described, inputs], sort_keys=True))
    except TypeError:  # an argument JSON cannot hold: its content cannot be told
        return function(*arguments)
    slot = digest(json.dumps([named, written(str(output), folders)]))
    entry = mark_of(slot, content)
    if entry is not None:
        placed([entry])
        return entry["record"]
    record = function(*arguments)
    try:
        text = json.dumps(record)
    except TypeError:
        return record
    written_mark(slot, content, {"record": json.loads(text), "code": code,
                                 "system": digest(python_system()), "inputs": inputs,
                                 "files": stored(files_under(output), folder)})
    return record


def entries():
    """(folder, entry) of every kept entry whose mark is written."""
    for mark in sorted(kept_root().glob(f"*/*/{DONE}")):
        yield mark.parent, json.loads(mark.read_text())


def output_blobs():
    """Every blob a stored output holds."""
    return {sha for listing in (store().objects.path("outputs")).glob("*.json")
            for sha in json.loads(listing.read_text()).values()}


def sweep(asked, say=print):
    """Drop every kept entry `asked` (its entry: True while a current key could ask for it) refuses, and each blob of
    it no stored output and no entry still kept holds; {"dropped", "freed_gb"}. Run with no run live (disk.py)."""
    dropped, held, freed = [], set(), 0
    for folder, entry in entries():
        if "files" not in entry:  # kept as copies (5a46a96e): never dropped before mark_of turns it
            continue
        if asked(entry):
            held |= {sha for sha, _ in entry["files"].values()}
            continue
        dropped.append(entry)
        shutil.rmtree(folder)
        if not any(folder.parent.iterdir()):
            folder.parent.rmdir()
        say(f"dropped kept {folder.parent.name}/{folder.name}: no current key asks for it")
    gone = {sha for entry in dropped for sha, _ in entry["files"].values()} - held - output_blobs()
    for sha in sorted(gone):
        blob = store().objects.path(f"blobs/{sha}")
        if blob.exists():
            freed += blob.stat().st_size
            blob.unlink()
    return {"dropped": len(dropped), "freed_gb": round(freed / 1e9, 3)}
