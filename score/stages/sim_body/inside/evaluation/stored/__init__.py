"""Level 1's pieces in SCORE's store (#70; owner, 2026-11-03, after `measured`'s cleared out folder wiped 501 seeds
built on a rented H100): each case's result at one point (a seed is the CPU result at level 1's start) and each
evaluation's per-case results, kept once in the store (score/store: content by hash, never overwritten) under the key
of what made them; a run on any machine finds what exists and makes only what is missing. Checkpoint lines too.

    store = stored.default_store()                     # SCORE_LEVEL1_STORE's folder, else the framework's store
    keys = stored.keys(store, "cpu", worker, bodies, (rows, weights, rest), seeds_root)  # {case: key}
    stored.found(store, "cpu", key)                    # its mark, or None
    stored.kept(store, "cpu", key, case_folder, made)  # kept once; a second make of the key leaves the first
    stored.placed(store, mark, path, "cpu")            # the kept files at `path`, read-only links to the blobs
    stored.aside(store, path, why)                     # whatever stands at `path` kept in the store, then moved off
    stored.lines_kept(store, run_key, checkpoint)      # the file's lines kept; the run's kept lines into the file
    stored.exported(store, slice, seeds_root)          # a rented batch's slice given the seeds' marks
    stored.merged(slice, store)                        # a slice brought back put into the store, the first standing

A key is the sha256 of what made the piece: its kind (`cpu`: `_case.py`, mink on the processors; `card`:
`_card_sets.py --same-seeds`; `block`: `_check_columns.py`'s exact block), the worker's code (`code`: every file of
inside/ the worker imports, followed import by import, docstrings out, plus the evaluation constants the worker reads,
`KEYED`; the evaluation runner `evaluation/__init__.py` and this package are left out: they decide how a job runs,
never what it makes), the case (its name and its job.json with every file it names written as that file's bytes'
hash, so another machine's paths key the same), its body (every case key of the body in the call: level 2 solves a
body once from all its clips), the point (the landmark rows, the weights, rest.json with the rig as its bytes' hash)
and, for `card` and `block`, the bytes of the body's seeds (each case's angles.npz in the seeds root). What the worker
ran on (host, Python) is in the mark, not the key.

Store keys: `level1/<kind>/<key>.json` the mark ({output, case, point, code, made: {host, python, at, ...}}, or
{unconverged: message} for a set a body's level 3 did not stop on), its files an output (`outputs/`, blobs once);
`level1/points/<point>.json` what a point is; `level1/checkpoints/<run>/<time>-<line>.json` one checkpoint line;
`level1/aside/<time>-<pid>-<output>.json` a file or folder that stood where a piece was to be written, kept before it
was moved off. Nothing here deletes from the store.

`python <this folder> import <seeds root> --src <the run's frozen src> --cases <cases.json>` keeps a seeds root
made before this (`measured` at level 1's start, a seed_run.py), keyed by what its own table.json, weights.json and
rest.json say and the src's code, each case only once it holds measures.json and m.json; its files are copied, never
moved. Standard library and the store only: it runs in any Python that holds the repository."""
import ast
import functools
import hashlib
import importlib.util
import json
import os
import pathlib
import shutil
import socket
import sys
import time

HERE = pathlib.Path(__file__).resolve()
INSIDE = HERE.parents[2]
REPO = HERE.parents[6]
if str(REPO) not in sys.path:
    sys.path.append(str(REPO))
from score.store import Store, file_hash, tree_hash, tree_listing  # noqa: E402

STORE = "SCORE_LEVEL1_STORE"  # a store folder of its own (a rented machine's slice), else the framework's
AREA = "level1"
LEFT_OUT = ("evaluation/__init__.py", "evaluation/stored")  # how a job runs, never what it makes
KEYED = ("SKIN_ROWS", "SEEDS", "SOLVED")  # evaluation constants the workers read
SEEDS = "angles.npz"
SOLVED = "measures.json"
CARD_FILES = (SOLVED, SEEDS)  # what a card piece keeps: m.json is `rounded`'s copy, the person's file made again


def default_store():
    """SCORE_LEVEL1_STORE's store when set (a folder), else the framework's ($PROPS_HOME/store)."""
    folder = os.environ.get(STORE)
    return Store.in_folder(folder) if folder else Store.default()


def digest(value):
    """The sha256 of a JSON value, keys sorted."""
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


@functools.cache
def code_tools(repo=REPO):
    """score/graph/_code.py of `repo` (standard library only), loaded from its file: its import reading and
    docstring stripping, the graph's own."""
    spec = importlib.util.spec_from_file_location("level1_code_version", repo / "score/graph/_code.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def left_out(path, inside):
    """True for a file of the evaluation runner or this package: they decide how a job runs."""
    relative = path.relative_to(inside).as_posix()
    return any(relative == name or relative.startswith(name + "/") for name in LEFT_OUT)


def module_paths(name, folders, inside):
    """The files of inside/ an import name could be found as, in each search folder."""
    parts = name.split(".")
    found = set()
    for folder in folders:
        for path in (folder.joinpath(*parts).with_suffix(".py"), folder.joinpath(*parts, "__init__.py")):
            if path.is_file() and path.resolve().is_relative_to(inside):
                found.add(path.resolve())
    return found


def worker_files(worker, inside=INSIDE):
    """Every file of inside/ the worker is or imports (its own folder and inside/ on its path, as it runs), followed
    import by import, the runner's files (LEFT_OUT) not followed."""
    tools, worker, inside = code_tools(), pathlib.Path(worker).resolve(), pathlib.Path(inside).resolve()
    folders = (worker.parent, inside)
    pending, found = [worker], set()
    while pending:
        path = pending.pop()
        if path in found or left_out(path, inside):
            continue
        found.add(path)
        for name in tools.imported_names(path.read_text(), path, tools.package_of(path)):
            pending += sorted(module_paths(name, folders, inside) - found)
    return sorted(found)


def meaning(path):
    """What a Python file does as text: its syntax unparsed, comments, layout and (unless the file reads another
    object's) docstrings out."""
    tools = code_tools()
    tree = ast.parse(path.read_text())
    if tools.doc_reads(tree) != "others":
        tree = tools.without_docstrings(tree)
    return ast.unparse(tree)


def constants(inside=INSIDE):
    """The KEYED evaluation constants, read from evaluation/__init__.py's text."""
    tree = ast.parse((pathlib.Path(inside) / "evaluation" / "__init__.py").read_text())
    found = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in KEYED:
                    found[target.id] = ast.literal_eval(node.value)
    return found


@functools.cache
def code(worker, inside=INSIDE):
    """{"hash", "files": {path under inside/: hash of its meaning}, "constants"} of what the worker runs."""
    inside = pathlib.Path(inside).resolve()
    files = {path.relative_to(inside).as_posix(): hashlib.sha256(meaning(path).encode()).hexdigest()
             for path in worker_files(worker, inside)}
    found = {"files": files, "constants": constants(inside)}
    return {"hash": digest(found), **found}


@functools.cache
def path_hash(path, size, modified):
    """A file's bytes' hash, or a folder's tree hash (once a file version)."""
    return file_hash(path) if os.path.isfile(path) else tree_hash(path)


def described(value):
    """A JSON value with every absolute path that exists written as {"bytes": its hash}: what it names, never where."""
    if isinstance(value, dict):
        return {str(name): described(item) for name, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [described(item) for item in value]
    if isinstance(value, str) and value.startswith("/") and os.path.exists(value):
        stat = os.stat(value)
        return {"bytes": path_hash(os.path.realpath(value), stat.st_size, stat.st_mtime_ns)}
    return value


def case_key(case, job):
    """A case: its name and its job.json described (a job that is no file: its text)."""
    path = pathlib.Path(job)
    content = described(json.loads(path.read_text())) if path.is_file() else str(job)
    return digest({"case": case, "job": content})


def point(store, rows, weights, rest):
    """The point's key; what it is written once to level1/points/ (the rig's bytes kept as a blob)."""
    value = {"rows": rows, "weights": weights, "rest": described(rest)}
    key = digest(value)
    if store.read(f"{AREA}/points/{key}.json") is None:
        rig = rest.get("rig") if isinstance(rest, dict) else None
        if isinstance(rig, str) and os.path.isfile(rig):
            store.put_blob(rig, file_hash(rig))
        written_once(store, f"{AREA}/points/{key}.json", value)
    return key


def seeds_of(seeds_root, cases):
    """{case: hash of its angles.npz in the seeds root, None when it has none}."""
    found = {}
    for case in cases:
        path = pathlib.Path(seeds_root) / case / SEEDS if seeds_root else None
        found[case] = file_hash(path) if path is not None and path.is_file() else None
    return found


def keys(store, kind, worker, bodies, at, seeds_root=None, inside=INSIDE):
    """{case: key} of every case of `bodies` ({body: {case: job}}) made by `kind`'s `worker` at the point `at`
    ((rows, weights, rest)); `card` and `block` keyed by the body's seeds in `seeds_root` too."""
    worked = code(pathlib.Path(worker).resolve(), pathlib.Path(inside).resolve())["hash"]
    at_key = point(store, *at)
    found = {}
    for body_cases in bodies.values():
        named = {case: case_key(case, job) for case, job in body_cases.items()}
        seeds = seeds_of(seeds_root, body_cases) if kind in ("card", "block") else None
        for case in body_cases:
            found[case] = digest({"kind": kind, "code": worked, "case": named[case], "body": sorted(named.values()),
                                  "point": at_key, "seeds": seeds})
    return found


def mark_key(kind, key):
    return f"{AREA}/{kind}/{key}.json"


def found(store, kind, key):
    """The piece's mark, or None."""
    return store.read(mark_key(kind, key))


def written_once(store, key, value):
    """`value` at `key` unless something stands there; the standing one is never overwritten."""
    try:
        store.write_once(key, value)
    except FileExistsError:
        pass


def made(**more):
    """Where and when a piece was made (the mark's `made`)."""
    return {"host": socket.gethostname(), "python": sys.version.split()[0], "executable": sys.executable,
            "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), **more}


def stored_files(store, kind, path):
    """The output holding a piece's files: a block's npz, a card case's CARD_FILES, a CPU case's whole folder."""
    path = pathlib.Path(path)
    if kind != "card":
        return store.put_tree(path)
    staging = store.making("level1-card")
    try:
        for name in CARD_FILES:
            if (path / name).is_file():
                shutil.copyfile(path / name, staging / name)
        return store.put_tree(staging)
    finally:
        shutil.rmtree(staging)


def kept(store, kind, key, path, made_by, unconverged=None, **record):
    """The piece kept once under its key: its files (`stored_files`) and its mark; {unconverged: message} when its
    set did not stop. A key already kept stays as it stands (the first make stands) and is given back."""
    if found(store, kind, key) is None:
        mark = {"unconverged": unconverged} if unconverged is not None else {"output": stored_files(store, kind, path)}
        written_once(store, mark_key(kind, key), {**mark, **record, "made": made_by})
    return found(store, kind, key)


def aside(store, path, why):
    """Whatever stands at `path` kept in the store (an output, and a level1/aside mark naming where it stood), then
    moved off it; nothing at `path`, nothing done."""
    path = pathlib.Path(path)
    if not path.exists() and not path.is_symlink():
        return None
    output = store.put_tree(path)
    written_once(store, f"{AREA}/aside/{time.strftime('%Y%m%dT%H%M%S')}-{os.getpid()}-{output[:16]}.json",
                 {"output": output, "path": str(path), "why": why, "made": made()})
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink()
    return output


def placed(store, mark, path, kind):
    """A kept piece's files at `path` (a block's npz there, a case's files in that folder), read-only links to the
    stored blobs; what stood there and differs is set `aside` first."""
    path = pathlib.Path(path)
    listing = store.listing(mark["output"])
    if kind == "block":
        (sha,) = listing.values()
        if path.is_file() and file_hash(path) == sha:
            return path
        aside(store, path, "a block placed over it")
        store.place_blob(sha, path)
        return path
    if path.is_dir() and tree_listing(path) == listing:
        return path
    aside(store, path, "a kept case placed over it")
    for name, sha in listing.items():
        store.place_blob(sha, path / name)
    return path


def measures(store, mark):
    """A kept case's unrounded measures (its SOLVED)."""
    return store.read_file(mark["output"], SOLVED)


# --- checkpoint lines --------------------------------------------------------------------------------------------


def run_key(level1, table, split, cases, rig, options, inside=INSIDE):
    """A level 1 run: its code (level1.py and every file of inside/ it imports, the runner included), its start
    table, split, cases (each by `case_key`), rig bytes and the options that change what it solves."""
    level1, inside = pathlib.Path(level1).resolve(), pathlib.Path(inside).resolve()
    files, pending = {}, [level1]
    tools = code_tools()
    while pending:
        path = pending.pop()
        name = path.relative_to(inside).as_posix()
        if name in files or name.startswith("evaluation/stored"):
            continue
        files[name] = hashlib.sha256(meaning(path).encode()).hexdigest()
        for imported in tools.imported_names(path.read_text(), path, tools.package_of(path)):
            pending += sorted(module_paths(imported, (level1.parent, inside), inside))
    rig = file_hash(rig) if pathlib.Path(rig).is_file() else None
    return digest({"code": files, "table": table, "split": split, "rig": rig,
                   "cases": sorted(case_key(case, job) for case, job in cases.items()), "options": options})


def checkpoint_lines(store, run):
    """Every checkpoint line kept for the run, oldest first."""
    prefix = f"{AREA}/checkpoints/{run}/"
    return [store.read(key) for key in sorted(store.objects.keys(prefix)) if key.endswith(".json")]


def lines_kept(store, run, path):
    """Every line of the checkpoint file at `path` kept in the store under the run (each once), and the file made to
    hold every line the store holds for the run (lines missing from it appended, ordered by time); the lines held."""
    path = pathlib.Path(path)
    here = [json.loads(line) for line in path.read_text().splitlines() if line.strip()] if path.exists() else []
    for line in here:
        written_once(store, f"{AREA}/checkpoints/{run}/{line['time']:014.1f}-{digest(line)[:16]}.json", line)
    known = {digest(line) for line in here}
    missing = sorted((line for line in checkpoint_lines(store, run) if digest(line) not in known),
                     key=lambda line: line["time"])
    if missing:
        with open(path, "a") as file:
            file.writelines(json.dumps(line) + "\n" for line in missing)
    return len(here) + len(missing)


# --- a rented machine's slice (tools/cloud/level1) ----------------------------------------------------------------


def copied(source, target, key):
    """One key of `source` written into `target` once, its output's files with it (same content, same hash); whether
    it was new there."""
    if target.read(key) is not None:
        return False
    value = source.read(key)
    if isinstance(value, dict) and "output" in value:
        target.put_tree(source.checkout(value["output"]))
    written_once(target, key, value)
    return True


def exported(source, target, seeds):
    """Into `target` (a rented batch's slice), each `cpu` mark of `source` whose output is the content of a case
    folder of the seeds root, so the machine finds the seeds it is given; how many were new there."""
    by_output = {}
    for key in source.objects.keys(f"{AREA}/cpu/"):
        mark = source.read(key)
        if mark and "output" in mark:
            by_output.setdefault(mark["output"], []).append(key)
    seeds = pathlib.Path(seeds)
    folders = sorted(path for path in seeds.iterdir() if path.is_dir()) if seeds.is_dir() else []
    return sum(copied(source, target, key) for folder in folders for key in by_output.get(tree_hash(folder), []))


def merged(source, target):
    """Every level1/ key of `source` (a slice brought back) put into `target`, a key it holds already standing; how
    many were new there."""
    return sum(copied(source, target, key) for key in source.objects.keys(f"{AREA}/"))
