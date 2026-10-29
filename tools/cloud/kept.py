"""Finished jobs kept by their own content, so a rerun, or a row made again at a new key, pays only for the jobs whose
own inputs changed (owner, 2026-10-18: a stopped film render threw away its finished frames and the rerun bought them
all again; 2026-10-29: a fix to 3 objects baked whole places again, and a free run on this PC kept nothing at all).

    waiting = kept.missing(jobs, system)            # each job kept at its content put back in place; the jobs to run
    kept.keep(job, system, brought, peers)          # after a job ended well: the files it brought back, kept

A job is a cloud runner's job ({"script", "args", "inputs", "outputs", ...}, blender_cloud.py's), run inside a node's
make: the runner names the make's folder (SCORE_MAKING) and the row's code (SCORE_MAKING_CODE, graph's making_code:
its code version, contract, params, seed, models and the files it declares inside the repository). A job's content is
the hash of its JSON and the bytes of every file of its inputs, its script and its env script, with the attempt's own
folders written as {making}, {repo} and {home} (each attempt makes into a fresh folder, each run on this PC has its own
frozen copy and home); the row's code; and `system`, what it runs on (blender_cloud.system: the machine image and the
Blender set-up). The repository's Python files and docs among its inputs, and the run machinery's files (_code.py's
FRAMEWORK), are left to the row's code: the graph's own rule of what code a row is, so an edit no row reads moves no
job. A job is the same job at the next key by its slot (its script, arguments, outputs and env, folders written as
above); each slot keeps one content, a newer keep replacing it. Kept at `kept/<slot>/<content>/` beside the store
(SCORE_SPEND_STORE, else PROPS_HOME's store); it counts as kept only once its `done` mark is written, after every
file, so a copy cut short is never taken. Outside a make, or for a job with an output outside the making folder,
nothing is kept and every job runs.

Jobs sharing an output folder (a bake row's `made`) each keep only the files their own bring-back wrote (`brought`,
rsync's list); one bring-back can carry another job's files from the same machine, so each keep names its `peers`
({slot: content} of the jobs sharing a folder still to come back from that machine then), and a kept job is put back
only while every peer is in the call at that content: never another job's file made from other inputs.

Imported only from the renting code (outside every stage's code key), so a change here moves no row.
"""
import functools
import hashlib
import importlib.util
import json
import os
import pathlib
import shutil

STORE = "SCORE_SPEND_STORE"
MAKING = "SCORE_MAKING"
CODE = "SCORE_MAKING_CODE"
DONE = "done"
REPO = pathlib.Path(__file__).resolve().parents[2]
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
    """(the job's slot, its content), or None outside a make or for a job with an output outside the making folder."""
    folder, code = making(), os.environ.get(CODE)
    if folder is None or code is None or relative_outputs(job, folder) is None:
        return None
    folders = stand_ins()
    slot = digest(written(json.dumps({field: job.get(field) for field in ("script", "args", "outputs", "env")},
                                     sort_keys=True), folders))
    return slot, digest(json.dumps([written(json.dumps(job, sort_keys=True), folders), code, system,
                                    input_files(job, folders)]))


def peers_of(job, others, system):
    """{slot: content} of the jobs of `others` with an output in, or holding, one of the job's own."""
    mine = [pathlib.Path(output).resolve() for output in job.get("outputs", ())]
    found = {}
    for other in others:
        theirs = [pathlib.Path(output).resolve() for output in other.get("outputs", ())]
        if any(one == two or one.is_relative_to(two) or two.is_relative_to(one) for one in mine for two in theirs):
            named = identity(other, system)
            if named:
                found[named[0]] = named[1]
    return found


def copy(source, target):
    """A file copied to `target`, its folders made."""
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def keep(job, system, brought=None, peers=None):
    """Keep a job that ended well at its content, only the files of its outputs in `brought` (every one when None),
    its `done` mark last, any other content of its slot removed; True when kept."""
    named = identity(job, system)
    if named is None:
        return False
    folder = making()
    outputs = relative_outputs(job, folder)
    if not all((folder / output).exists() for output in outputs):
        return False
    slot, content = named
    place = kept_root() / slot / content
    if place.exists():
        shutil.rmtree(place)
    files = [path for output in outputs for path in files_under(folder / output)]
    for path in files if brought is None else [path for path in files if path in brought]:
        copy(path, place / "outputs" / path.relative_to(folder))
    (place / DONE).write_text(json.dumps({"job": job, "peers": peers or {}}, sort_keys=True))
    for other in (kept_root() / slot).iterdir():
        if other != place:
            shutil.rmtree(other)
    return True


def merge(source, target):
    """Each file of a kept folder put at its place under `target` unless the one there is newer: jobs side by side on
    one machine share an output folder (a bake row's `made`, blender_cloud.py on this PC), so one job's kept copy can
    hold another's file caught mid-write, older than that job's own kept file."""
    for path in sorted(found for found in source.rglob("*") if found.is_file()):
        place = target / path.relative_to(source)
        if place.is_file() and place.stat().st_mtime_ns >= path.stat().st_mtime_ns:
            continue
        copy(path, place)


def missing(jobs, system):
    """Every job kept at its content, whose peers are all in the call at theirs, put back in place in this attempt's
    making folder; the jobs still to run, in their order."""
    named = [identity(job, system) for job in jobs]
    present = dict(found for found in named if found)
    waiting = []
    for job, found in zip(jobs, named):
        mark = kept_root() / found[0] / found[1] / DONE if found else None
        if mark is None or not mark.exists() or any(present.get(slot) != content for slot, content in
                                                    json.loads(mark.read_text())["peers"].items()):
            waiting.append(job)
            continue
        if (mark.parent / "outputs").is_dir():
            merge(mark.parent / "outputs", making())
    return waiting
